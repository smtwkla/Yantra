"""PM jobs — the pure rules (docs/steps/S097-pm-jobs-due/1-brief.md § 5.1; R03.3).  No DB, no clock, no Flask.

A plan has at most one open job.  The shell (pm_jobs.py) reads the plan, its open job and its meter, asks
pm_schedule_core for the plan's next due point and standing, and asks ``decide`` what to do: make the job, refresh
the open job's copies of the due point, cancel it, or nothing.  The job stores its due point and windows as copies
(``due_copies``), so the list judges its standing live from them (``due_from_job`` and pm_schedule_core.job_state)
without reading the plan's history again (D4).

A bad input is a shell bug, never user input: it raises ``ValueError`` / ``TypeError`` naming it (S095 D8).  Dates
are ``date``, never ``datetime``; meter values ``Decimal`` (or ``int``), never ``float``.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from config_rbac import ASSIGNABLE_ROLES
from pm_schedule_core import BEFORE_USE, BOTH, CALENDAR, DUE, KINDS, METER, NOT_YET, OVERDUE, UPCOMING, Due, job_state
from tickets_core import format_serial

READ_KEY = "pm_job:read"   # one copy: pm_jobs.py, pm_work.py and alerts_core (S102) take it from here
DUE_STATE, IN_PROGRESS, DONE, VERIFIED, SKIPPED, CANCELLED = (
    "due", "in_progress", "done", "verified", "skipped", "cancelled")
JOB_STATES = (DUE_STATE, IN_PROGRESS, DONE, VERIFIED, SKIPPED, CANCELLED)   # the ENUM's order
OPEN_STATES = (DUE_STATE, IN_PROGRESS)    # open_plan_id is set; one per plan
BASE_STATES = (DONE, VERIFIED, SKIPPED)   # the next job counts from the latest of these (S101, R03 Q9.2 a)
# S101 D4: the due_changed line of a refresh that clears the job's reschedule
RESCHEDULE_DROPPED = "The plan's schedule was changed, so the job's reschedule no longer applies."
CREATE_STANDINGS = (UPCOMING, DUE, OVERDUE)   # S095's states that make a job
SERIAL_PREFIX = "PM"
RUN_ACTOR = "pm_generate"                 # created_by of the daily run's rows
CREATED, DUE_CHANGED, ASSIGNEE_CHANGED, CANCELLED_EVENT = "created", "due_changed", "assignee_changed", "cancelled"
# S104 § 5.4: why a plan stops; pm_links_core.stop_remark picks one, in this order, and decide cancels with it
TEMPLATE_INACTIVE_REMARK = "The template was deactivated."
UNLINKED_REMARK = "The template was removed from this machine."
NODE_SCRAPPED_REMARK = "The equipment was scrapped."
TAB_DUE, TAB_UPCOMING, TAB_TO_VERIFY, TAB_DONE = "due", "upcoming", "to_verify", "done"
TABS = (TAB_DUE, TAB_UPCOMING, TAB_TO_VERIFY, TAB_DONE)   # S099: To verify between Upcoming and Done
CREATE, REFRESH, CANCEL = "create", "refresh", "cancel"
# S104 § 5.3, BR1-01: where a meter-trigger plan's base value comes from (meter_base_source)
JOB_BASE, SEED_BASE, READING_BASE = "job", "seed", "reading"

_STANDINGS = (NOT_YET, UPCOMING, DUE, OVERDUE)
# The list's order: the furthest standing first (§ 5.9)
_LIST_RANK = {OVERDUE: 0, DUE: 1, UPCOMING: 2, NOT_YET: 3}
# The columns a job copies from pm_schedule_core.Due, and the offset beside them (§ 4.1)
_DUE_FIELDS = ("due_on", "due_meter", "grace_days", "upcoming_days", "meter_window")
_METER_FIELDS = ("due_meter", "meter_window", "meter_offset", "rescheduled_meter")   # DECIMAL(14,3) on pm_jobs
_SCALE = Decimal("0.001")


def _column_scale(value):
    return None if value is None else Decimal(value).quantize(_SCALE, rounding=ROUND_HALF_UP)


def _flag(value, key):
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a bool, not {type(value).__name__}")
    return value


def _date(value, key):
    """``value`` as a date or None; a ``datetime`` is a ``date`` subclass, so the type is checked exactly."""
    if value is not None and type(value) is not date:
        raise TypeError(f"{key} must be a date, not {type(value).__name__}")
    return value


def _number(value, key):
    """``value`` as a Decimal or None; ``int`` is exact and allowed, ``bool`` and ``float`` are not."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise TypeError(f"{key} must be a Decimal or an int, not {type(value).__name__}")
    return Decimal(value)


def _standing(value, key, required):
    if value is None and not required:
        return None
    if value not in _STANDINGS:
        raise ValueError(f"{key} must be one of {_STANDINGS}, not {value!r}")
    return value


def decide(stop, before_use, node_scrapped, open_state, standing_state):
    """What to do with one plan's job (§ 5.5's table) -> ``(action, remark)`` or None.

    ``stop``: why the plan makes no job (pm_links_core.stop_remark: the template deactivated, the plan unlinked,
    not for this machine, a meter missing), or None while it is in force (S104 § 5.4); a remark cancels a due job
    with it.  ``open_state``: the open job's state (DUE_STATE, IN_PROGRESS) or None without one.
    ``standing_state``: the plan's standing today (pm_schedule_core), needed only when a job may be made; None
    otherwise."""
    if stop is not None and (not isinstance(stop, str) or not stop):
        raise TypeError(f"stop must be None or a remark, not {stop!r}")
    _flag(before_use, "before_use")
    _flag(node_scrapped, "node_scrapped")
    if open_state not in (None, *OPEN_STATES):
        raise ValueError(f"open_state must be None or one of {OPEN_STATES}, not {open_state!r}")
    _standing(standing_state, "standing_state", required=False)

    if open_state == IN_PROGRESS:
        return None   # R03.4 decides what a started job does
    if open_state == DUE_STATE:
        if stop is not None:
            return CANCEL, stop
        if node_scrapped:
            return CANCEL, NODE_SCRAPPED_REMARK
        if before_use:
            return None   # its Due has no field to copy (R03.13)
        return REFRESH, None
    if stop is not None or node_scrapped or before_use:
        return None
    if _standing(standing_state, "standing_state", required=True) in CREATE_STANDINGS:
        return CREATE, None
    return None


def not_for_machine_remark(reason):
    """R03.19's *Not for this machine*, with the engineer's reason."""
    return f"Not for this machine: {reason}"


def does_not_apply_remark(missing):
    """``missing``: pm_links_core.missing_text's "no Run hours meter on HP003"."""
    return f"Does not apply: {missing}."


def seed_matches(plan, meter):
    """The plan's *Last done* meter value was entered for ``meter`` (``(node_id, meter_type_id)``, or None; BR1-01).
    ``plan`` has ``last_done_meter`` and the seed's ``seed_meter_equipment_id`` and ``seed_meter_type_id``."""
    return (plan["last_done_meter"] is not None and meter is not None
            and (plan["seed_meter_equipment_id"], plan["seed_meter_type_id"]) == tuple(meter))


def meter_base_source(last, plan, meter):
    """Where a meter-trigger plan's base value comes from on ``meter`` (S104 § 5.3, BR1-01) -> JOB_BASE, SEED_BASE or
    READING_BASE.  The base follows the meter: the last base job's done_meter counts only when that job's copied
    meter (``last``'s ``meter_equipment_id`` and ``meter_type_id``; None without a base job) is ``meter``, and the
    seed only without a base job and when it was entered for ``meter``; every other case reads the meter's own
    readings, so a value of another meter (a parent's, a removed one) is never the base."""
    if last is not None:
        same = (last["meter_equipment_id"], last["meter_type_id"]) == tuple(meter)
        return JOB_BASE if same else READING_BASE
    return SEED_BASE if seed_matches(plan, meter) else READING_BASE


def due_copies(due, offset, override=None):
    """The job's stored copies of ``due`` (a pm_schedule_core.Due) and the reset ``offset`` (§ 4.1, § 5.4), and of
    ``override`` (S101: next_due's ``{due_on, due_meter}`` the job was moved to, or None) in rescheduled_on and
    rescheduled_meter."""
    if due.before_use:
        raise ValueError("a before_use Due has no due point to copy")
    offset = _number(offset, "offset")
    if offset is None or offset < 0:
        raise ValueError(f"offset must be 0 or more, not {offset}")
    override = override or {}
    copies = {**{field: getattr(due, field) for field in _DUE_FIELDS}, "meter_offset": offset,
              "rescheduled_on": _date(override.get("due_on"), "override['due_on']"),
              "rescheduled_meter": _number(override.get("due_meter"), "override['due_meter']")}
    # The meter columns are DECIMAL(14,3): 10 % of a 3-decimal interval has 4 decimals, which MariaDB rounds on
    # insert.  Rounded here the same way (half away from zero), so job_changes compares like with like (CR1-01).
    return {field: (_column_scale(value) if field in _METER_FIELDS else value) for field, value in copies.items()}


def due_from_job(job):
    """A pm_jobs row's copies back as a ``Due``; ``rescheduled`` when either reschedule column is set (S101)."""
    rescheduled = job["rescheduled_on"] is not None or job["rescheduled_meter"] is not None
    return Due(_date(job["due_on"], "due_on"), _number(job["due_meter"], "due_meter"), job["grace_days"],
               job["upcoming_days"], _number(job["meter_window"], "meter_window"), rescheduled=rescheduled,
               before_use=False)


def job_standing(job, latest_value, today):
    """How a job stands on ``today`` (S102 § 5.3) -> pm_schedule_core's ``Standing``.  ``job``: a full pm_jobs row;
    ``latest_value``: the value of the plan meter's latest active reading, or None.  The job's meter_offset is added,
    so the value counts across a counter reset.  One copy: the list (pm_jobs.jobs_out) and the alert scan."""
    value = None if latest_value is None else latest_value + job["meter_offset"]
    return job_state(due_from_job(job), value, today)


def job_override(job, trigger_kind):
    """The reschedule a job keeps under its plan's ``trigger_kind`` (S101 § 5.1) -> next_due's ``{due_on,
    due_meter}``, or None.  A trigger the plan no longer has drops its value; a before-use plan keeps none."""
    if trigger_kind not in KINDS:
        raise ValueError(f"trigger_kind must be one of {KINDS}, not {trigger_kind!r}")
    if trigger_kind == BEFORE_USE:
        return None
    due_on = job["rescheduled_on"] if trigger_kind in (CALENDAR, BOTH) else None
    due_meter = job["rescheduled_meter"] if trigger_kind in (METER, BOTH) else None
    if due_on is None and due_meter is None:
        return None
    return {"due_on": _date(due_on, "rescheduled_on"), "due_meter": _number(due_meter, "rescheduled_meter")}


def job_changes(job, copies, assignee_id):
    """The columns of ``job`` (a pm_jobs row) that differ from ``copies`` (``due_copies``) and ``assignee_id``
    -> ``{column: new value}``; ``{}`` when nothing changed.  Decimals compare by value (3.000 equals 3)."""
    wanted = {**copies, "assignee_id": assignee_id}
    return {column: value for column, value in wanted.items() if job[column] != value}


def meter_offset(base_value, readings):
    """The usage carried across counter resets after the base (§ 5.4, D8) -> a Decimal.

    ``readings``: the meter's active readings after the base, in time order, as ``[{value, is_reset}]``.  A reset
    adds the value before it (the base for the first) to the offset; the value passed to the core is then
    ``latest + offset``.  0 without a base value."""
    before = _number(base_value, "base_value")
    if before is None:
        return Decimal(0)
    offset = Decimal(0)
    for reading in readings:
        value = _number(reading["value"], "value")
        if reading["is_reset"]:
            offset += before
        before = value
    return offset


def days_past(due_on, today):
    """Whole days since ``due_on`` -> ``int`` when 1 or more, else None (today, the future, no due date)."""
    _date(today, "today")
    if _date(due_on, "due_on") is None:
        return None
    days = (today - due_on).days
    return days if days >= 1 else None


def _open_state(state):
    if state not in OPEN_STATES:
        raise ValueError(f"state must be one of {OPEN_STATES}, not {state!r}")
    return state


def tab_of(state, standing_state):
    """The list's tab of an open job: *Due* for a started job whatever its standing (work begun belongs to now;
    S098 § 5.9), else *Due* for DUE and OVERDUE, *Upcoming* for NOT_YET and UPCOMING."""
    standing = _standing(standing_state, "standing_state", required=True)
    if _open_state(state) == IN_PROGRESS:
        return TAB_DUE
    return TAB_DUE if standing in (DUE, OVERDUE) else TAB_UPCOMING


def list_order(item):
    """The list's sort key of ``item`` (``{state, standing: {state}, due_on: date | None, serial}``): the started jobs
    first (S098 § 5.9), then the furthest standing, then the oldest due date (a job without one after those with
    one), then the serial."""
    due_on = _date(item["due_on"], "due_on")
    return (_open_state(item["state"]) != IN_PROGRESS,
            _LIST_RANK[_standing(item["standing"]["state"], "standing_state", required=True)],
            due_on is None, due_on or date.min, item["serial"])


def pm_serial(year, month, number):
    """2026, 11, 1 -> PM-2026-11-001."""
    return format_serial(SERIAL_PREFIX, year, month, number)


def assignable_id(assignee_id, person):
    """The job's assignee (§ 5.2, D12): the plan's ``assignee_id`` when ``person`` (tickets.person_at_site's row at
    the node's site, or None) holds a role in ASSIGNABLE_ROLES there; else None."""
    if assignee_id is None or person is None or person["role"] not in ASSIGNABLE_ROLES:
        return None
    return assignee_id
