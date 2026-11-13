"""PM scheduling — the pure rules (docs/steps/S095-pm-schedule-core/1-brief.md § 5; R03.1).  No DB, no Flask, no
clock: the shell passes in today's IST date, the plan's fields, the last job's done date and meter value, and the
latest reading of the plan's meter.

Three questions, three functions over two small frozen dataclasses (D1):

- ``next_due``: when is the plan's next job due (a date, a meter value, or both: whichever first)?
- ``job_state``: how does the open job stand today (*Not yet*, *Upcoming*, *Due*, *Overdue*)?
- ``timeliness``: was a done job on time (the 10 % window of R03 Q1.1)?

The intervals float from the last done job (Plan.MD § 4.3).  A bad input is a shell or S096 bug, never user input:
it raises ``ValueError`` / ``TypeError`` naming the key (D8).  Every date is a ``date``, never a ``datetime`` (a UTC
time would shift the IST date); every meter value is a ``Decimal`` or an ``int``, never a ``float`` (a float
compares with a Decimal without an error, and would give a wrong state silently).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from contracts_core import add_months

# The trigger vocabulary (D7): S096's ``pm_plans.trigger_kind`` ENUM and ``calendar_unit`` take these strings.
CALENDAR, METER, BOTH, BEFORE_USE = "calendar", "meter", "both", "before_use"
KINDS = (CALENDAR, METER, BOTH, BEFORE_USE)
DAY, WEEK, MONTH, YEAR = "day", "week", "month", "year"
CALENDAR_UNITS = (DAY, WEEK, MONTH, YEAR)
NOT_YET, UPCOMING, DUE, OVERDUE = "not_yet", "upcoming", "due", "overdue"
ON_TIME, LATE = "on_time", "late"
WINDOW_DIVISOR = 10       # 10 % of the interval (R03 Q1.1, Q3.1)
MIN_WINDOW_DAYS = 1       # Q1.1: at least 1 day, so a weekly job gets a day's grace
UPCOMING_MAX_DAYS = 7     # Q3.1: 7 days or 10 %, the shorter

_CALENDAR_KINDS = (CALENDAR, BOTH)
_METER_KINDS = (METER, BOTH)
_ORDER = (NOT_YET, UPCOMING, DUE, OVERDUE)   # "the furthest state" of § 5.4


@dataclass(frozen=True)
class Due:
    """A plan's next due point and its windows (§ 5.3)."""
    due_on: date | None           # the calendar trigger's due date; None without a calendar trigger
    due_meter: Decimal | None     # the meter trigger's due value; None without one, or without a base value
    grace_days: int | None        # the on-time window after due_on; None without a calendar trigger
    upcoming_days: int | None     # the window before due_on; None without a calendar trigger
    meter_window: Decimal | None  # 10 % of meter_every, before and after due_meter; None without a meter trigger
    rescheduled: bool             # an override replaced a computed value
    before_use: bool


@dataclass(frozen=True)
class Standing:
    """How an open job stands today (§ 5.4)."""
    state: str            # NOT_YET, UPCOMING, DUE or OVERDUE
    trigger: str | None   # CALENDAR or METER: the trigger that gave the state; always None for NOT_YET
    no_reading: bool      # the plan has a meter trigger, and no reading or no base value: "No reading yet"


def _date(value, key, required=False):
    """``value`` as an IST date, or None.  A ``datetime`` is a ``date`` subclass, so the type is checked exactly."""
    if value is None:
        if required:
            raise ValueError(f"{key} is required")
        return None
    if type(value) is not date:
        raise TypeError(f"{key} must be a date, not {type(value).__name__}")
    return value


def _meter_value(value, key):
    """``value`` as a ``Decimal``, or None.  ``int`` is allowed (exact); ``bool`` and ``float`` are not."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise TypeError(f"{key} must be a Decimal or an int, not {type(value).__name__}")
    return Decimal(value)


def add_interval(day, every, unit):
    """``day`` plus ``every`` days, weeks, months or years (§ 5.3).  A month is the same day of the month, or the
    month's last day when the month is shorter; it does not snap back (28-02 + 1 month = 28-03)."""
    if every < 1:
        raise ValueError(f"every must be at least 1, not {every}")
    if unit == DAY:
        return day + timedelta(days=every)
    if unit == WEEK:
        return day + timedelta(days=7 * every)
    if unit == MONTH:
        return add_months(day, every)
    if unit == YEAR:
        return add_months(day, 12 * every)
    raise ValueError(f"unknown calendar unit {unit!r}")


def window_days(interval_days):
    """The on-time window after the due date: 10 % of the interval, rounded down, at least 1 day (D3)."""
    if interval_days < 1:
        raise ValueError(f"interval_days must be at least 1, not {interval_days}")
    return max(MIN_WINDOW_DAYS, interval_days // WINDOW_DIVISOR)


def upcoming_days(interval_days):
    """The window before the due date: 7 days or 10 %, the shorter (Q3.1)."""
    return min(UPCOMING_MAX_DAYS, window_days(interval_days))


def _check_plan(plan):
    """§ 5.1: the plan's rules -> its trigger kind.  Raises naming the key; extra keys are ignored."""
    kind = plan.get("trigger_kind")
    if kind not in KINDS:
        raise ValueError(f"trigger_kind must be one of {KINDS}, not {kind!r}")
    _date(plan.get("created_on"), "created_on", required=True)
    _date(plan.get("last_done_on"), "last_done_on")
    if kind == BEFORE_USE:
        return kind

    every, unit = plan.get("calendar_every"), plan.get("calendar_unit")
    if kind in _CALENDAR_KINDS:
        if every is None:
            raise ValueError(f"calendar_every is required for trigger_kind {kind!r}")
        if isinstance(every, bool) or not isinstance(every, int):
            raise TypeError(f"calendar_every must be an int, not {type(every).__name__}")
        if every < 1:
            raise ValueError(f"calendar_every must be at least 1, not {every}")
        if unit not in CALENDAR_UNITS:
            raise ValueError(f"calendar_unit must be one of {CALENDAR_UNITS}, not {unit!r}")
    else:
        if every is not None:
            raise ValueError(f"calendar_every must be None for trigger_kind {kind!r}")
        if unit is not None:
            raise ValueError(f"calendar_unit must be None for trigger_kind {kind!r}")

    meter_type_id, meter_every = plan.get("meter_type_id"), plan.get("meter_every")
    if kind in _METER_KINDS:
        if meter_type_id is None:
            raise ValueError(f"meter_type_id is required for trigger_kind {kind!r}")
        if meter_every is None:
            raise ValueError(f"meter_every is required for trigger_kind {kind!r}")
        if _meter_value(meter_every, "meter_every") <= 0:
            raise ValueError(f"meter_every must be more than 0, not {meter_every}")
        last_done_meter = _meter_value(plan.get("last_done_meter"), "last_done_meter")
        if last_done_meter is not None and last_done_meter < 0:
            raise ValueError(f"last_done_meter must be 0 or more, not {last_done_meter}")
    else:
        if meter_type_id is not None:
            raise ValueError(f"meter_type_id must be None for trigger_kind {kind!r}")
        if meter_every is not None:
            raise ValueError(f"meter_every must be None for trigger_kind {kind!r}")
    return kind


def _base(plan, last_job, start_meter, has_meter):
    """§ 5.2: where the next interval counts from -> ``(base_date, base_meter)``.  A done job always wins over the
    seed; the seed (or the plan's creation) is only the first job's base."""
    if last_job is not None:
        base_date = _date(last_job.get("done_on"), "last_job['done_on']", required=True)
        base_meter = _meter_value(last_job.get("done_meter"), "last_job['done_meter']") if has_meter else None
        return base_date, base_meter
    base_date = plan.get("last_done_on") or plan["created_on"]
    if not has_meter:
        return base_date, None
    seed_meter = _meter_value(plan.get("last_done_meter"), "last_done_meter")
    start = _meter_value(start_meter, "start_meter")
    return base_date, seed_meter if seed_meter is not None else start


def next_due(plan, last_job=None, start_meter=None, override=None):
    """The plan's next due point (§ 5.3) -> ``Due``.

    ``last_job``: None or ``{"done_on": date, "done_meter": Decimal | None}``, the last done job.
    ``start_meter``: the meter value at the plan's start (the seed date, else ``created_on``), or None.
    ``override``: None or ``{"due_on": date | None, "due_meter": Decimal | None}`` (R03.9's reschedule): a value
    that is set replaces that trigger's computed value; the windows stay those of the computed interval (D5)."""
    kind = _check_plan(plan)
    if kind == BEFORE_USE:
        if override is not None:
            raise ValueError("override must be None for trigger_kind 'before_use'")
        return Due(None, None, None, None, None, rescheduled=False, before_use=True)

    has_calendar, has_meter = kind in _CALENDAR_KINDS, kind in _METER_KINDS
    override = override or {}
    override_on = _date(override.get("due_on"), "override['due_on']")
    override_meter = _meter_value(override.get("due_meter"), "override['due_meter']")
    if override_on is not None and not has_calendar:
        raise ValueError(f"override['due_on'] is set, but trigger_kind {kind!r} has no calendar trigger")
    if override_meter is not None and not has_meter:
        raise ValueError(f"override['due_meter'] is set, but trigger_kind {kind!r} has no meter trigger")

    base_date, base_meter = _base(plan, last_job, start_meter, has_meter)

    due_on = grace = upcoming = None
    if has_calendar:
        computed = add_interval(base_date, plan["calendar_every"], plan["calendar_unit"])
        interval_days = (computed - base_date).days
        grace, upcoming = window_days(interval_days), upcoming_days(interval_days)
        due_on = override_on if override_on is not None else computed

    due_meter = meter_window = None
    if has_meter:
        meter_every = Decimal(plan["meter_every"])
        meter_window = meter_every / WINDOW_DIVISOR
        computed_meter = None if base_meter is None else base_meter + meter_every
        due_meter = override_meter if override_meter is not None else computed_meter

    rescheduled = override_on is not None or override_meter is not None
    return Due(due_on, due_meter, grace, upcoming, meter_window, rescheduled=rescheduled, before_use=False)


def _calendar_state(due, today):
    start_upcoming = due.due_on - timedelta(days=due.upcoming_days)
    last_on_time = due.due_on + timedelta(days=due.grace_days)
    if today < start_upcoming:
        return NOT_YET
    if today < due.due_on:
        return UPCOMING
    return DUE if today <= last_on_time else OVERDUE


def _meter_state(due, reading):
    if reading < due.due_meter - due.meter_window:
        return NOT_YET
    if reading < due.due_meter:
        return UPCOMING
    return DUE if reading <= due.due_meter + due.meter_window else OVERDUE


def job_state(due, reading_value, today):
    """How the open job of ``due`` stands on ``today`` (an IST date) at ``reading_value`` (the latest active reading
    of the plan's meter, or None) -> ``Standing`` (§ 5.4).  The plan's state is the furthest of its triggers'
    states; a tie goes to the calendar (D2).  *Due* lasts through the on-time window, *Overdue* comes after (D4)."""
    today = _date(today, "today", required=True)
    reading = _meter_value(reading_value, "reading_value")
    if due.before_use:
        return Standing(NOT_YET, None, False)

    state, trigger, no_reading = NOT_YET, None, False
    if due.due_on is not None:
        state, trigger = _calendar_state(due, today), CALENDAR
    if due.meter_window is not None:
        if due.due_meter is None or reading is None:
            no_reading = True
        else:
            meter_state = _meter_state(due, reading)
            if _ORDER.index(meter_state) > _ORDER.index(state):
                state, trigger = meter_state, METER
    if state == NOT_YET:
        trigger = None
    return Standing(state, trigger, no_reading)


def timeliness(due, done_on, done_meter):
    """Was a job of ``due`` done on ``done_on`` (IST date) at ``done_meter`` (the meter value then, or None) on time?
    -> ON_TIME, LATE, or None for a before-use plan (not judged, R03.13).  LATE when any trigger was past its window
    (D2), so a job is on time exactly when ``job_state`` would not have shown OVERDUE then (§ 5.5)."""
    done_on = _date(done_on, "done_on", required=True)
    done_meter = _meter_value(done_meter, "done_meter")
    if due.before_use:
        return None
    if due.due_on is not None and done_on > due.due_on + timedelta(days=due.grace_days):
        return LATE
    if due.due_meter is not None and done_meter is not None and done_meter > due.due_meter + due.meter_window:
        return LATE
    return ON_TIME
