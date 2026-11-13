"""PM plans — the pure rules of a machine's plan row (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.5; R03.18).
No DB, no Flask, no clock: the shell passes in today's IST date, the plan's template and the meter its trigger
resolves to on the machine.

Since S104 the work of a plan (its items, trigger, performer, verification) lives on its PM template
(pm_templates_core).  A plan row holds only the machine's own facts: who the jobs are assigned to, and when the work
was last done before Yantra (*Last done*: a date, and a value of the trigger's meter on this machine).  The plan
settings route takes only these three fields; any other is refused by name (D12), so an old screen cannot think it
saved the work on a plan.
"""

from datetime import date

from contracts_core import iso_date
from masters_core import validate_fields
from meters_core import BELOW_ZERO, COUNTER
from pm_jobs_core import seed_matches
from pm_schedule_core import BOTH, METER
from pm_templates_core import MAINTENANCE, changes_of, optional_id, stored_number, type_decimals_error

DATE_MIN = date(2000, 1, 1)

# The columns of a plan row the settings route writes; a change of a Last done field drops the open job's reschedule
# (S101 D4, schedule_changed), an assignee change does not
PLAN_FIELDS = ("assignee_id", "last_done_on", "last_done_meter")

# The fields a plan settings body may not hold, by why (§ 5.5's table)
WORK_FIELDS = ("items", "title", "name", "performer", "needs_verification", "trigger_kind", "calendar_every",
               "calendar_unit", "meter_type_id", "meter_every")
FIXED_FIELDS = ("template_id", "equipment_id")

ASSIGNEE_FROM_LIST = "Choose a person from the list."
LAST_DONE_DATE = "Enter a date from 01-01-2000 to today."
OPERATOR_NO_ASSIGNEE = "Operator plans have no assignee. Choose No one yet."
NO_METER_TRIGGER = "This template has no meter trigger. Clear the meter value."
CHANGE_ON_TEMPLATE = "Change the work on the template."
PLAN_FIXED = "A plan stays on its machine and template. Remove it and attach another."
EQUIPMENT_NEEDED = "Choose the equipment."
TEMPLATE_NEEDED = "Choose a PM template."


def unknown_field(name):
    return f"Unknown field: {name}."


def no_meter_here(type_name):
    """The seed's refusal when the trigger's meter type does not resolve on the machine."""
    return f"This machine has no {type_name} meter. Add the meter first."


def _parse_last_done_meter(raw):
    value = stored_number(raw)
    if value is not None and value < 0:
        raise ValueError(BELOW_ZERO[COUNTER])
    return value


def _parse_last_done_on(raw):
    if raw is None:
        return None
    value = iso_date(raw)
    if value is None or value < DATE_MIN:
        raise ValueError(LAST_DONE_DATE)
    return value


_SETTINGS = {
    "assignee_id": (optional_id(ASSIGNEE_FROM_LIST), False),
    "last_done_on": (_parse_last_done_on, False),
    "last_done_meter": (_parse_last_done_meter, False),
}


def _refused_field(body):
    """The first field the body may not hold -> ``(field, message)`` or None (§ 5.5's table, D12)."""
    for field in body:
        if field in _SETTINGS:
            continue
        if field in WORK_FIELDS:
            return field, CHANGE_ON_TEMPLATE
        if field in FIXED_FIELDS:
            return field, PLAN_FIXED
        return field, unknown_field(field)
    return None


def validate_plan_settings(body, _creating):
    """The plan settings body (§ 5.5) -> ``(clean, errors)`` for clean_body: any subset of the three fields; any
    other field is refused by name first (D12)."""
    refused = _refused_field(body)
    if refused:
        return {}, [{"field": refused[0], "message": refused[1]}]
    return validate_fields(body, _SETTINGS, False)


def validate_attach(body, _creating):
    """*Attach PM template*'s body ``{equipment_id, template_id}`` -> ``(clean, errors)``; nothing else is read."""
    data = {"equipment_id": body.get("equipment_id"), "template_id": body.get("template_id")}
    parsers = {"equipment_id": (optional_id(EQUIPMENT_NEEDED), False),
               "template_id": (optional_id(TEMPLATE_NEEDED), False)}
    clean, errors = validate_fields(data, parsers, False)
    for field, message in (("equipment_id", EQUIPMENT_NEEDED), ("template_id", TEMPLATE_NEEDED)):
        if not errors and clean.get(field) is None:
            errors = [{"field": field, "message": message}]
    return clean, errors


def plan_settings_error(clean, template, trigger_meter_type, trigger_meter_found, today):
    """The sent settings against the plan's template and machine (§ 5.5) -> ``(field, message)`` or None.  Only
    the fields sent are judged, so a stored value a template change made unused never blocks another save.
    ``template``: {performer, trigger_kind}; ``trigger_meter_type``: the trigger's meter type ({name, decimals}),
    None without a meter trigger; ``trigger_meter_found``: the type resolves to a meter on this machine;
    ``today``: the IST date."""
    if clean.get("last_done_on") is not None and clean["last_done_on"] > today:
        return "last_done_on", LAST_DONE_DATE
    if clean.get("assignee_id") is not None and template["performer"] != MAINTENANCE:
        return "assignee_id", OPERATOR_NO_ASSIGNEE
    value = clean.get("last_done_meter")
    if value is not None:
        if template["trigger_kind"] not in (METER, BOTH) or trigger_meter_type is None:
            return "last_done_meter", NO_METER_TRIGGER
        if not trigger_meter_found:
            return "last_done_meter", no_meter_here(trigger_meter_type["name"])
        message = type_decimals_error(value, trigger_meter_type)
        if message:
            return "last_done_meter", message
    return None


def plan_changes(stored, clean, trigger=None):
    """The plan columns of ``clean`` that differ from the stored row -> ``{column: value}``; empty when nothing
    changed, so a PUT of nothing new writes nothing (no updated_at).  CR1-05: a *Last done* meter value equal to the
    stored one still counts as a change when the stored seed was entered for another meter than ``trigger`` (the
    meter the trigger resolves to now, ``(node_id, meter_type_id)``, or None): typing the same number again is how
    the engineer ties it to the meter the plan uses now (BR1-01)."""
    changes = changes_of(stored, clean, PLAN_FIELDS)
    value = clean.get("last_done_meter")
    if (value is not None and "last_done_meter" not in changes and trigger is not None
            and (stored.get("seed_meter_equipment_id"), stored.get("seed_meter_type_id")) != tuple(trigger)):
        changes["last_done_meter"] = value
    return changes


def schedule_changed(stored, changes, trigger=None):
    """Whether ``changes`` (plan_changes' answer) can move the base of the plan's next due, so the open job's
    reschedule is dropped (S101 D4); an assignee change does not.  CR4-01: clearing a seed the plan does not use (one
    entered for another meter than ``trigger``, or with no meter resolving now) is not a schedule change: the base
    already comes from the meter's readings or a base job, so the due stays and a supervisor's move holds."""
    if "last_done_on" in changes:
        return True
    if "last_done_meter" not in changes:
        return False
    cleared = changes["last_done_meter"] is None
    return not cleared or seed_matches(stored, trigger)
