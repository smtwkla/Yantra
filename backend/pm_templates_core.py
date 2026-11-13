"""PM templates — the pure rules (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.1, § 5.2; R03.18).  No DB, no
Flask, no clock.

A template is the standard work of a PM plan, written once (TPM: the planned-maintenance standard): its name, who
does it, whether an engineer verifies each job, its trigger (calendar, a meter type, or whichever comes first) and
its items (Task, Check, Reading).  A machine gets it through a link (pm_links_core); the machine's own facts (who is
assigned, when it was last done) live on its plan row (pm_plans_core).  The rules moved here from S096's
pm_plans_core with S104's changes: the trigger names a meter **type**, never a meter (each machine uses its own
meter of that type, or the meter of a node above that its Meters card links: S104 A1, which removed the template's
parent tick); a *Reading* item is a *Measurement* (its own unit and limits) or a *Meter reading* (a meter type; the
machine's meter's unit and limits, D6).  A body that still sends ``meter_from_parent`` has it ignored, as any
unknown field.

A template is checked in two phases, as S096's plan was (BR1-02 there): ``validate_template`` judges each field
alone for clean_body, before any read; ``template_rules_error`` judges the merged row (the stored template with the
clean body over it) once the shell has read the trigger's meter type.  Items are checked one by one
(``validate_item``, also the dialog's check route) and as a list (``validate_items``); ``sync_items`` turns a sent
list into the inserts, updates and deactivations of a save, by id (a removed item is set inactive, never deleted).

The field rules reuse masters_core's public parsers and meters_core's number rules, so no rule has a second copy.
"""

from decimal import Decimal

from masters_core import collapsed, flag_parser, optional_text_parser, validate_fields
from meters_core import COUNTER, GAUGE, MIN_ABOVE_MAX, format_number, grouped_number, parse_number
from pm_schedule_core import BEFORE_USE, BOTH, CALENDAR, CALENDAR_UNITS, DAY, KINDS, METER, MONTH, WEEK, YEAR

NAME_MAX = 100
ITEM_TEXT_MAX = 200
HELP_TEXT_MAX = 500
UNIT_MAX = 20
MAX_ITEMS = 50
STORED_DECIMALS = 3          # DECIMAL(14,3): meter_every and a measurement's limits

MAINTENANCE, OPERATOR = "maintenance", "operator"
PERFORMERS = (MAINTENANCE, OPERATOR)
TASK, CHECK, READING = "task", "check", "reading"
ITEM_TYPES = (TASK, CHECK, READING)
MEASUREMENT, METER_READING = "measurement", "meter"
READING_KINDS = (MEASUREMENT, METER_READING)   # pm_template_items.reading_kind's ENUM order
PHOTO_SETTINGS = ("none", "optional", "required")
DEFAULT_PHOTO = "optional"
ITEM_METER_KINDS = (COUNTER, GAUGE)             # a meter reading item's meter type

# The per-unit bounds of calendar_every (S096 § 5.1, D8: at most 10 years); the database's own bound is 1–3650
CALENDAR_MAX = {DAY: 3650, WEEK: 520, MONTH: 120, YEAR: 10}

# The trigger kinds by the fields they need (as the CHECKs of v57)
_CALENDAR_KINDS = (CALENDAR, BOTH)
_METER_KINDS = (METER, BOTH)
CALENDAR_FIELDS = ("calendar_every", "calendar_unit")
METER_FIELDS = ("meter_type_id", "meter_every")

# The columns of a template and of an item that a save writes (the item's position is the sync's)
TEMPLATE_FIELDS = ("name", "performer", "needs_verification", "trigger_kind", *CALENDAR_FIELDS, *METER_FIELDS,
                   "active")
# S101 D4, § 5.1: the template's schedule; a save that changes one drops the reschedule of every plan's open job
SCHEDULE_FIELDS = ("trigger_kind", *CALENDAR_FIELDS, *METER_FIELDS)
ITEM_FIELDS = ("item_type", "text", "help_text", "photo", "reading_kind", "unit", "min_value", "max_value",
               "meter_type_id")
_READING_FIELDS = ("reading_kind", "unit", "min_value", "max_value", "meter_type_id")

NAME_NEEDED = "Enter a name."
DUPLICATE_NAME = ("A PM template with this name already exists, active or inactive. Choose another name, or "
                  "reactivate that template.")
PERFORMER_NEEDED = "Choose who does the jobs."
TRIGGER_NEEDED = "Tick By calendar or By meter, or both."
BEFORE_USE_NOT_YET = "Before-use plans are not available yet. Choose a calendar or meter interval."
UNIT_NEEDED = "Choose days, weeks, months or years."
METER_TYPE_FROM_LIST = "Choose a meter type from the list."
COUNTER_NEEDED = "Choose a counter meter type, such as Run hours."
ABOVE_ZERO = "Enter a number above 0."
ITEMS_NEEDED = "Add at least one item."
ITEMS_NOT_LIST = "Items must be a list"
TOO_MANY_ITEMS = f"A template holds at most {MAX_ITEMS} items."
RELOAD = "Reload the page."
CLEAR_METER = "Clear the meter fields for a calendar template."
CLEAR_CALENDAR = "Clear the calendar fields for a meter template."
ITEM_TYPE_NEEDED = "Choose Task, Check or Reading."
ITEM_TEXT_NEEDED = "Enter what to do or check."
PHOTO_NEEDED = "Choose a photo setting."
ONLY_READING = "Only a reading has a unit, limits or a meter."
READING_KIND_NEEDED = "Choose Measurement or Meter reading."
ONLY_METER_READING = "Only a meter reading names a meter type."
ITEM_METER_TYPE_NEEDED = "Choose a counter or gauge meter type."
METER_UNIT = "A meter reading uses the meter's unit. Clear Unit."
METER_LIMITS = "A meter reading uses the machine's meter limits. Clear Min and Max."

# The words of a calendar interval: (singular, plural)
_UNIT_WORDS = {DAY: ("day", "days"), WEEK: ("week", "weeks"), MONTH: ("month", "months"), YEAR: ("year", "years")}


def calendar_message(unit):
    """The refusal of calendar_every, naming the chosen unit's maximum."""
    return f"Enter a whole number from 1 to {CALENDAR_MAX.get(unit, CALENDAR_MAX[MONTH])}."


def item_removed(number):
    return f"Item {number} was removed or changed by someone else. Reload the page."


def item_twice(number):
    return f"Item {number} appears twice. Reload the page."


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def required_id(message):
    """An id the body must name: an integer ≥ 1, never a boolean (bool is an int in Python)."""
    def parse(raw):
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            raise ValueError(message)
        return raw
    return parse


def optional_id(message):
    """An id, or None for none."""
    required = required_id(message)

    def parse(raw):
        return None if raw is None else required(raw)
    return parse


def _text_parser(label, max_len, needed):
    """Required text, inner spaces collapsed: "Enter …" when empty, the masters form when too long or not text."""
    def parse(raw):
        if raw is not None and not isinstance(raw, str):
            raise ValueError(f"{label} must be text")
        text = collapsed(raw)
        if not text:
            raise ValueError(needed)
        if len(text) > max_len:
            raise ValueError(f"{label} must be at most {max_len} characters")
        return text
    return parse


def _choice_parser(allowed, message, nullable=False):
    def parse(raw):
        if raw is None and nullable:
            return None
        if raw not in allowed:
            raise ValueError(message)
        return raw
    return parse


def _parse_trigger_kind(raw):
    if raw == BEFORE_USE:
        raise ValueError(BEFORE_USE_NOT_YET)   # S096 D6: in the column, refused until R03.13
    if raw not in KINDS:
        raise ValueError(TRIGGER_NEEDED)
    return raw


def stored_number(raw):
    """A number of a DECIMAL(14,3) column, or None; the type's own decimals are judged on the merged row."""
    return parse_number(raw, STORED_DECIMALS)


def _parse_items(raw):
    """The list as sent: its entries need the meter types, so validate_items judges them in the shell."""
    if raw is None:
        raise ValueError(ITEMS_NEEDED)
    if not isinstance(raw, list):
        raise ValueError(ITEMS_NOT_LIST)
    return raw


def _calendar_every_parser(unit):
    """calendar_every alone: a whole number ≥ 1.  The message names the sent unit's maximum, or the month's when
    no unit was sent (a hand-made PUT); the maximum itself is judged on the merged pair (template_rules_error)."""
    def parse(raw):
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            raise ValueError(calendar_message(unit))
        return raw
    return parse


# field -> (parser, required when creating).  validate_template gives an absent required field the value None on a
# POST, so its own parser's text shows; the table therefore marks nothing required (contracts_core's way).
_TEMPLATE_FIELDS = {
    "name": (_text_parser("Name", NAME_MAX, NAME_NEEDED), False),
    "performer": (_choice_parser(PERFORMERS, PERFORMER_NEEDED), False),
    "needs_verification": (flag_parser("Verification"), False),
    "trigger_kind": (_parse_trigger_kind, False),
    "calendar_unit": (_choice_parser(CALENDAR_UNITS, UNIT_NEEDED, nullable=True), False),
    "meter_type_id": (optional_id(METER_TYPE_FROM_LIST), False),
    "meter_every": (stored_number, False),
    "active": (flag_parser("Active"), False),
    "items": (_parse_items, False),
}
_TEMPLATE_REQUIRED = ("name", "trigger_kind", "items")


def default_verification(performer):
    """R03 Q5.1 a: an engineer verifies a maintenance job by default, not an operator's routine check."""
    return performer == MAINTENANCE


def validate_template(body, creating):
    """The body -> ``(clean, errors)`` for clean_body (§ 5.1, phase 1).  On a POST every required field must be
    there (an absent one is parsed as None, so its own text shows), ``active`` is ignored (a new template is
    active), ``performer`` defaults to maintenance and ``needs_verification`` to the performer's default; on a PUT an
    absent field stays as it is.  Unknown fields are ignored (the old ``meter_from_parent`` too, S104 A1)."""
    data = dict(body)
    if creating:
        data.pop("active", None)
        for field in _TEMPLATE_REQUIRED:
            data.setdefault(field, None)
    fields = {**_TEMPLATE_FIELDS, "calendar_every": (_calendar_every_parser(data.get("calendar_unit")), False)}
    clean, errors = validate_fields(data, fields, creating)
    if creating and not errors:
        clean.setdefault("performer", MAINTENANCE)
        clean.setdefault("needs_verification", int(default_verification(clean["performer"])))
    return clean, errors


# ---------------------------------------------------------------------------
# The merged template (phase 2)
# ---------------------------------------------------------------------------

def _first_set(merged, fields):
    return next((field for field in fields if merged.get(field) is not None), None)


def type_decimals_error(value, meter_type):
    """``value`` (a Decimal) with more places than the meter type has -> parse_number's text, else None."""
    try:
        parse_number(format_number(value), meter_type["decimals"])
    except ValueError as exc:
        return str(exc)
    return None


def _calendar_error(merged):
    kind = merged["trigger_kind"]
    if kind not in _CALENDAR_KINDS:
        field = _first_set(merged, CALENDAR_FIELDS)
        return (field, CLEAR_CALENDAR) if field else None
    unit, every = merged.get("calendar_unit"), merged.get("calendar_every")
    if every is None:
        return "calendar_every", calendar_message(unit)
    if unit is None:
        return "calendar_unit", UNIT_NEEDED
    if not 1 <= every <= CALENDAR_MAX[unit]:
        return "calendar_every", calendar_message(unit)
    return None


def _meter_error(merged, meter_type):
    kind = merged["trigger_kind"]
    if kind not in _METER_KINDS:
        field = _first_set(merged, METER_FIELDS)
        return (field, CLEAR_METER) if field else None
    if merged.get("meter_type_id") is None or meter_type is None:
        return "meter_type_id", METER_TYPE_FROM_LIST
    if meter_type["kind"] != COUNTER:
        return "meter_type_id", COUNTER_NEEDED
    every = merged.get("meter_every")
    if every is None or every <= 0:
        return "meter_every", ABOVE_ZERO
    message = type_decimals_error(every, meter_type)
    return ("meter_every", message) if message else None


def template_rules_error(merged, meter_type):
    """The merged template (§ 5.1, phase 2) -> ``(field, message)`` or None.  ``merged`` is the stored row with the
    clean body over it (a POST: the clean body); ``meter_type`` the trigger's meter type ``{kind, decimals, …}``, or
    None without one (or an unknown id).  The null-ness of the trigger fields follows v57's CHECKs."""
    return _calendar_error(merged) or _meter_error(merged, meter_type)


def same_value(a, b):
    """Two stored values equal by value: Decimal("250.000") equals Decimal("250"), a flag 1 equals True."""
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        return a is not None and b is not None and Decimal(a) == Decimal(b)
    return a == b


def changes_of(stored, clean, fields):
    """The ``fields`` of ``clean`` that differ from the stored row -> ``{column: value}``; empty when nothing
    changed, so a PUT of nothing new writes nothing (no updated_at)."""
    return {field: clean[field] for field in fields if field in clean and not same_value(stored[field], clean[field])}


def template_changes(stored, clean):
    """The template columns of ``clean`` that differ from the stored row; ``items`` are synced, never written."""
    return changes_of(stored, clean, TEMPLATE_FIELDS)


# ---------------------------------------------------------------------------
# Items (§ 5.2)
# ---------------------------------------------------------------------------

_ITEM_FIELDS = {
    "id": (optional_id(RELOAD), False),
    "item_type": (_choice_parser(ITEM_TYPES, ITEM_TYPE_NEEDED), False),
    "text": (_text_parser("Item", ITEM_TEXT_MAX, ITEM_TEXT_NEEDED), False),
    "help_text": (optional_text_parser("Help text", HELP_TEXT_MAX), False),
    "photo": (_choice_parser(PHOTO_SETTINGS, PHOTO_NEEDED), False),
    "reading_kind": (_choice_parser(READING_KINDS, READING_KIND_NEEDED, nullable=True), False),
    "unit": (optional_text_parser("Unit", UNIT_MAX, collapse=True), False),
    "meter_type_id": (optional_id(ITEM_METER_TYPE_NEEDED), False),
}


def _error(field, message):
    return [{"field": field, "message": message}]


def _limits(body):
    """A measurement's Min and Max at the stored decimals -> ``((min, max), errors)``; Min above Max refuses on Max."""
    pair = {}
    for field in ("min_value", "max_value"):
        try:
            pair[field] = stored_number(body.get(field))
        except ValueError as exc:
            return None, _error(field, str(exc))
    low, high = pair["min_value"], pair["max_value"]
    if low is not None and high is not None and low > high:
        return None, _error("max_value", MIN_ABOVE_MAX)
    return (low, high), []


def _sent(body, field):
    return body.get(field) is not None


def validate_item(body, meter_types):
    """One item -> ``(clean, errors)`` (§ 5.2), the errors in the masters_core shape, the first one decides.
    ``meter_types`` maps a meter type id to its row ``{id, name, unit, kind, decimals}`` (the shell reads the ones
    the body names).  ``clean`` has ``id`` and every field of ITEM_FIELDS; a Task or Check has no reading field."""
    data = {"item_type": None, "text": None, **body}
    clean, errors = validate_fields(data, _ITEM_FIELDS, False)
    if errors:
        return {}, errors
    clean = {"id": clean.get("id"), "item_type": clean["item_type"], "text": clean["text"],
             "help_text": clean.get("help_text"), "photo": clean.get("photo", DEFAULT_PHOTO),
             "reading_kind": clean.get("reading_kind"), "unit": clean.get("unit"), "min_value": None,
             "max_value": None, "meter_type_id": clean.get("meter_type_id")}
    if clean["item_type"] != READING:
        field = next((f for f in _READING_FIELDS if _sent(body, f)), None)
        return (clean, []) if field is None else ({}, _error(field, ONLY_READING))
    if clean["reading_kind"] is None:
        return {}, _error("reading_kind", READING_KIND_NEEDED)
    if clean["reading_kind"] == MEASUREMENT:
        if _sent(body, "meter_type_id"):
            return {}, _error("meter_type_id", ONLY_METER_READING)
        pair, errors = _limits(body)
        if errors:
            return {}, errors
        clean["min_value"], clean["max_value"] = pair
        return clean, []
    meter_type = meter_types.get(clean["meter_type_id"]) if clean["meter_type_id"] is not None else None
    if meter_type is None or meter_type["kind"] not in ITEM_METER_KINDS:
        return {}, _error("meter_type_id", ITEM_METER_TYPE_NEEDED)
    if clean["unit"] is not None:
        return {}, _error("unit", METER_UNIT)
    field = next((f for f in ("min_value", "max_value") if body.get(f) is not None), None)
    return (clean, []) if field is None else ({}, _error(field, METER_LIMITS))


def validate_items(raw, meter_types):
    """A template's item list -> ``(clean list, None)`` or ``([], ("items", message))``; an item's own refusal is
    led by its number: "Item 3: Enter what to do or check."."""
    if not isinstance(raw, list):
        return [], ("items", ITEMS_NOT_LIST)
    if not raw:
        return [], ("items", ITEMS_NEEDED)
    if len(raw) > MAX_ITEMS:
        return [], ("items", TOO_MANY_ITEMS)
    out = []
    for number, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            return [], ("items", f"Item {number}: {RELOAD}")
        clean, errors = validate_item(entry, meter_types)
        if errors:
            return [], ("items", f"Item {number}: {errors[0]['message']}")
        out.append(clean)
    return out, None


def sent_meter_type_ids(body):
    """The meter type ids a template body names (its trigger's and its items'), for the shell's one read."""
    ids = {body.get("meter_type_id")}
    items = body.get("items")
    if isinstance(items, list):
        ids.update(entry.get("meter_type_id") for entry in items if isinstance(entry, dict))
    return sorted(i for i in ids if isinstance(i, int) and not isinstance(i, bool))


def sync_items(stored, sent):
    """A save's item list against the template's active items (§ 5.2) -> ``({insert, update, deactivate}, None)``
    or ``(None, message)``.  ``stored`` are the active rows (with ``id`` and ``position``), ``sent`` the clean list
    in its new order.  Positions are 1..n in the sent order; an update holds only the fields that differ; a stored
    item not sent is deactivated and keeps its position.  A change of an item's kind is a change of that item."""
    by_id = {row["id"]: row for row in stored}
    seen = set()
    ops = {"insert": [], "update": [], "deactivate": []}
    for position, item in enumerate(sent, start=1):
        item_id = item.get("id")
        if item_id is None:
            ops["insert"].append({**{field: item[field] for field in ITEM_FIELDS}, "position": position})
            continue
        if item_id in seen:
            return None, item_twice(position)
        if item_id not in by_id:
            return None, item_removed(position)
        seen.add(item_id)
        row = by_id[item_id]
        changes = {field: item[field] for field in ITEM_FIELDS if not same_value(row[field], item[field])}
        if row["position"] != position:
            changes["position"] = position
        if changes:
            ops["update"].append((item_id, changes))
    ops["deactivate"] = [row["id"] for row in stored if row["id"] not in seen]
    return ops, None


# ---------------------------------------------------------------------------
# Words (§ 5.10)
# ---------------------------------------------------------------------------

def interval_number(value, decimals):
    """A number with the places it really has, at most ``decimals``, Indian grouping (S096 BR1-03): "250" on a
    1-decimal type reads "250", not "250.0"; 5000 reads "5,000"."""
    places = min(len(format_number(value).partition(".")[2]), decimals)
    return grouped_number(value, places)


def _calendar_words(every, unit):
    singular, plural = _UNIT_WORDS[unit]
    return singular if every == 1 else f"{every} {plural}"


def _meter_words(every, meter_type):
    return f"{interval_number(every, meter_type['decimals'])} {meter_type['unit']}"


def trigger_text(template, meter_type):
    """The trigger in words: "Every month", "Every 250 h", "Every month or 250 h, whichever comes first", "Before
    each use".  ``meter_type`` is the trigger's ({unit, decimals}), None without a meter trigger."""
    kind = template["trigger_kind"]
    if kind == BEFORE_USE:
        return "Before each use"
    if kind == CALENDAR:
        return f"Every {_calendar_words(template['calendar_every'], template['calendar_unit'])}"
    if kind == METER:
        return f"Every {_meter_words(template['meter_every'], meter_type)}"
    return (f"Every {_calendar_words(template['calendar_every'], template['calendar_unit'])} or "
            f"{_meter_words(template['meter_every'], meter_type)}, whichever comes first")


def meter_label(code, meter_type):
    """"HP003's Run hours": the node that carries the meter, then the meter type's name."""
    return f"{code}'s {meter_type['name']}"


def range_text(low, high, unit, decimals):
    """"30–60 °C", "up to 60 °C", "from 30 °C", the numbers alone without a unit; None without either limit."""
    low, high = (None if v is None else interval_number(v, decimals) for v in (low, high))
    suffix = f" {unit}" if unit else ""
    if low is not None and high is not None:
        return f"{low}–{high}{suffix}"
    if high is not None:
        return f"up to {high}{suffix}"
    if low is not None:
        return f"from {low}{suffix}"
    return None


def item_limits_text(item, meter_type=None, meter_code=None):
    """A reading's kind and limits in words (§ 5.10), None for a Task or Check:
    - a measurement: "Measurement · 180–200 bar", or "Measurement" without limits;
    - a meter reading on a template (``meter_code`` None): "Meter reading · Run hours";
    - a meter reading on a job (``meter_code`` the node whose meter it logs): "Meter reading · HP003's Run hours",
      then the meter's limits in force when the job copied any (" · 20–70 °C").
    ``meter_type`` is the meter reading's type ({name, unit, decimals})."""
    if item.get("item_type") != READING:
        return None
    if item.get("reading_kind") != METER_READING or meter_type is None:
        limits = range_text(item.get("min_value"), item.get("max_value"), item.get("unit"), STORED_DECIMALS)
        return " · ".join(part for part in ("Measurement", limits) if part)
    if meter_code is None:
        return f"Meter reading · {meter_type['name']}"
    limits = range_text(item.get("min_value"), item.get("max_value"), meter_type["unit"], meter_type["decimals"])
    return " · ".join(part for part in ("Meter reading", meter_label(meter_code, meter_type), limits) if part)
