"""Meters on models and nodes — the pure rules (docs/steps/S038-meters-on-models-equipment/
1-brief.md § 5).  Plain data in, plain data out: no database, no clock, no Flask.

- validate_limits: a gauge's min / max from a request body, merged over the pair in force;
- effective_meters: a node's meters = its model's active meters (with the node's override of
  their limits) plus its own;
- limits_text and tracked_meter_change: the one source of the limits wording, for the card
  and for the history line.

Readings (S039, docs/steps/S039-meter-reading-entry/1-brief.md § 5): validate_reading, the
time window (parse_taken_at, reading_time_error), the counter order against both neighbours
(counter_error), a gauge's limits and a Yes / No meter's answer (limit_state, answer_state),
and who may remove a reading (may_remove, reset_removal_error).

The reading register (S050, docs/steps/S050-reading-register/1-brief.md § 5): its columns
(register_columns, shown_meter_ids), its rows by minute (register_rows) and the query's id list
(parse_meter_type_ids).

Meter readings on the ticket (S052, docs/steps/S052-ticket-meters/1-brief.md § 5.2): the 7-day
window for the marked readings (mark_window) and the card's lines (readings_at_ticket).

Limits and readings are numbers of the meter type's decimals, parsed with Decimal (never
float) and returned as strings without trailing zeros.  Only a gauge has limits: a counter triggers PM
every N units, an amount is a quantity produced, and a Yes / No meter's good answer is fixed
on its type (S037 decision 7).
"""

import re
from datetime import timedelta
from decimal import Decimal

# Pure to pure: tickets_core never imports this module (S039 BR1-10)
from tickets_core import EVENT_TIME_FORMAT, EVENT_TIME_FUTURE, FUTURE_SKEW, parse_event_time

COUNTER = "counter"
GAUGE = "gauge"
AMOUNT = "amount"
YES_NO = "yes_no"
LIMIT_FIELDS = ("min_value", "max_value")
NO_LIMITS = (None, None)

# DECIMAL(14,3): 11 digits before the point, MAX_DECIMALS after it
LIMIT_MAX = Decimal("99999999999.999")
_DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")

PICK_A_METER_TYPE = "Pick a meter type"
NO_LIMITS_FOR_KIND = {
    "counter": "A counter has no limits",
    "amount": "An amount per period has no limits",
    "yes_no": "A Yes / No meter has no limits",
}
MIN_ABOVE_MAX = "Min must not be above Max"
TOO_LARGE = "Enter a smaller number"

SOURCE_MODEL = "model"
SOURCE_NODE = "node"

# The three ways a PUT may change a meter
ACTION_LIMITS = "limits"
ACTION_USE_MODEL = "use_model_limits"
ACTION_REMOVE = "remove"


def _decimals_message(decimals):
    if decimals == 0:
        return "Enter a whole number"
    return f"Enter a number with up to {decimals} decimal{'s' if decimals > 1 else ''}"


def parse_number(raw, decimals):
    """One number of a meter type (a limit, a reading): None, an int, or a decimal string →
    Decimal or None; ValueError with the user's message otherwise.  A bool and a float are
    refused (a float is already rounded)."""
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        raise ValueError(_decimals_message(decimals))
    text = str(raw).strip()
    if not _DECIMAL_RE.match(text):
        raise ValueError(_decimals_message(decimals))
    value = Decimal(text)
    # Trailing zeros are not decimals: "62.50" is 62.5
    places = max(0, -value.normalize().as_tuple().exponent)
    if places > decimals:
        raise ValueError(_decimals_message(decimals))
    if abs(value) > LIMIT_MAX:
        raise ValueError(TOO_LARGE)
    return value


def validate_limits(body, kind, decimals, stored):
    """The limits pair after a write → ``((min, max), errors)``, errors in the masters_core
    shape.  ``stored`` is the pair in force before the write (a row's own pair; a node's first
    override starts from the model's; a create from NO_LIMITS).  An absent field keeps its
    stored value; an explicit null clears it.  The kind check comes first, so a counter with
    "abc" reads "A counter has no limits"; an explicit null on a non-gauge is not a limit sent
    (a form that posts every field passes)."""
    if kind != GAUGE:
        for field in LIMIT_FIELDS:
            if body.get(field) is not None:
                return NO_LIMITS, [{"field": field, "message": NO_LIMITS_FOR_KIND[kind]}]
        return NO_LIMITS, []
    merged = dict(zip(LIMIT_FIELDS, stored))
    for field in LIMIT_FIELDS:
        if field in body:
            try:
                merged[field] = parse_number(body[field], decimals)
            except ValueError as exc:
                return stored, [{"field": field, "message": str(exc)}]
    low, high = merged["min_value"], merged["max_value"]
    if low is not None and high is not None and low > high:
        return stored, [{"field": "max_value", "message": MIN_ABOVE_MAX}]
    return (low, high), []


def parse_meter_type_id(body, message=PICK_A_METER_TYPE):
    """The meter type of an add (or of a reading, S039: "Pick a meter") → ``(id, errors)``."""
    raw = body.get("meter_type_id")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        return None, [{"field": "meter_type_id", "message": message}]
    return raw, []


def parse_change_action(body, allow_use_model):
    """What a PUT asks → ``(action, errors)``: ``active: false`` removes, ``use_model_limits:
    true`` (a node only) clears the override, anything else sets limits.  A PUT never
    reactivates: an add brings a removed meter back (BR1-18).  The texts are for API callers;
    the screens never send these mixes."""
    keys = {"active", "use_model_limits", *LIMIT_FIELDS} & set(body)
    if "active" in body:
        if body["active"] is not False:
            return None, [{"field": "active", "message": "Add the meter again to bring it back"}]
        if keys != {"active"}:
            return None, [{"field": "active", "message": "Send the removal alone"}]
        return ACTION_REMOVE, []
    if "use_model_limits" in body:
        if not allow_use_model or body["use_model_limits"] is not True:
            return None, [{"field": "use_model_limits", "message": "Only true is accepted here"}]
        if keys != {"use_model_limits"}:
            return None, [{"field": "use_model_limits", "message": "Send the model's limits alone"}]
        return ACTION_USE_MODEL, []
    return ACTION_LIMITS, []


# ---------------------------------------------------------------------------
# Wording — the card's limits line and the history text
# ---------------------------------------------------------------------------

def format_number(value):
    """A stored DECIMAL as the user writes it: no trailing zeros, no exponent ("10", "62.5")."""
    if value is None:
        return None
    text = f"{Decimal(value).normalize():f}"
    return "0" if text == "-0" else text


def _range(unit, pair):
    """"10–60 °C", "up to 60 °C", "from 10 °C", or None when neither limit is set."""
    low, high = (format_number(v) for v in pair)
    if low is not None and high is not None:
        return f"{low}–{high} {unit}"
    if high is not None:
        return f"up to {high} {unit}"
    if low is not None:
        return f"from {low} {unit}"
    return None


def limits_text(meter_type, pair):
    """The card's line for a gauge: "Limits: 10–60 °C" … "No limits"; None for a counter, an
    amount and a Yes / No meter, which show no limits line (BR3-01)."""
    if meter_type["kind"] != GAUGE:
        return None
    text = _range(meter_type["unit"], pair)
    return f"Limits: {text}" if text else "No limits"


def _history_side(meter_type, pair):
    return f"{meter_type['name']}: {_range(meter_type['unit'], pair) or 'no limits'}"


def tracked_meter_change(meter_type, old_pair, new_pair):
    """The history line of a limits write → ``[("meter_limits", old, new)]``, both sides the
    limits in force (BR1-06); none when the limits in force did not change."""
    if same_limits(old_pair, new_pair):
        return []
    return [("meter_limits", _history_side(meter_type, old_pair), _history_side(meter_type, new_pair))]


def same_limits(a, b):
    """Two limit pairs equal by value (Decimal("10.000") equals Decimal("10"))."""
    return all((x is None and y is None) or (x is not None and y is not None and Decimal(x) == Decimal(y))
               for x, y in zip(a, b))



# ---------------------------------------------------------------------------
# A node's meters
# ---------------------------------------------------------------------------

def _pair(row):
    return (row["min_value"], row["max_value"])


def override_of(node_row):
    """The pair a node row sets over its model's meter, or None when it sets none.  An own = 0
    row exists only while it differs from the model (a both-NULL one means "no limits here").
    An own = 1 row of a type the model gained later (active or not, BR2-02) overrides only
    while it holds a limit: *Use the model's limits* clears its pair and keeps the row."""
    if node_row is None:
        return None
    if not node_row["own"]:
        return _pair(node_row) if node_row["active"] else None
    if node_row["min_value"] is None and node_row["max_value"] is None:
        return None
    return _pair(node_row)


def _out_limits(pair):
    return {"min_value": format_number(pair[0]), "max_value": format_number(pair[1])}


def effective_meters(model_meters, node_rows):
    """A node's meters (§ 5.2), ordered by meter type name.  ``model_meters`` are the rows of
    the node's model (none without a model, S033) and ``node_rows`` the node's own rows, each
    with ``meter_type`` ({id, name, unit, kind, decimals, expected_answer}), ``min_value``,
    ``max_value``, ``active``; a node row also has ``own``.

    - an active model meter: the node's override when there is one, else the model's limits;
    - an active own meter whose type is not an active model meter: its own limits;
    - an override of a type no longer on the model, and a removed own meter: left out."""
    node_by_type = {row["meter_type"]["id"]: row for row in node_rows}
    out = []
    model_type_ids = set()
    for row in model_meters:
        if not row["active"]:
            continue
        meter_type = row["meter_type"]
        model_type_ids.add(meter_type["id"])
        model_pair = _pair(row)
        override = override_of(node_by_type.get(meter_type["id"]))
        in_force = override if override is not None else model_pair
        out.append({
            "meter_type": meter_type, "source": SOURCE_MODEL, **_out_limits(in_force),
            "model_min": format_number(model_pair[0]), "model_max": format_number(model_pair[1]),
            "overridden": override is not None,
            "limits_text": limits_text(meter_type, in_force),
            "model_limits_text": limits_text(meter_type, model_pair),
        })
    for row in node_rows:
        meter_type = row["meter_type"]
        if not row["own"] or not row["active"] or meter_type["id"] in model_type_ids:
            continue
        out.append({
            "meter_type": meter_type, "source": SOURCE_NODE, **_out_limits(_pair(row)),
            "model_min": None, "model_max": None, "overridden": False,
            "limits_text": limits_text(meter_type, _pair(row)), "model_limits_text": None,
        })
    out.sort(key=lambda m: (m["meter_type"]["name"].casefold(), m["meter_type"]["id"]))
    return out


def in_force_pair(model_meter, node_row):
    """The limits in force on a node for one meter type: the override, else the model meter's
    (``model_meter`` an active row or None), else the node's own row's."""
    if model_meter is not None:
        override = override_of(node_row)
        return override if override is not None else _pair(model_meter)
    return _pair(node_row) if node_row is not None else NO_LIMITS


def meter_type_of(row, prefix="t_"):
    """The ``meter_type`` dict from a joined row whose meter type columns carry ``prefix``."""
    return {field: row[f"{prefix}{field}"] for field in ("id", "name", "unit", "kind", "decimals", "expected_answer")}


# ---------------------------------------------------------------------------
# Readings (S039)
# ---------------------------------------------------------------------------

# A fixed window for every role, admin included: a departure from S028's backdate_days for
# readings only (S039 decision 8, U2)
READING_BACKDATE_DAYS = 7
READING_TOO_OLD = f"When was it read? Up to {READING_BACKDATE_DAYS} days back"
NOTE_MAX = 200

PICK_A_METER = "Pick a meter"
ENTER_THE_READING = "Enter the reading"
PICK_YES_OR_NO = "Pick Yes or No"
BELOW_ZERO = {
    COUNTER: "A counter cannot be below zero",
    AMOUNT: "An amount cannot be below zero",
}
ONLY_A_COUNTER_RESETS = "Only a counter can be reset"
RESET_NOT_BOOL = "Meter reset must be true or false"
NOTE_NOT_TEXT = "Note must be text"
NOTE_TOO_LONG = f"Note must be at most {NOTE_MAX} characters"
RESET_ABOVE_BEFORE = "A reset reads lower than the reading before it. Untick Meter reset."
RESET_HAS_LATER = "This reading marks a meter reset. Remove the later readings first."

# The refusal code by which a screen offers the Meter reset tick (S040; BR2-02)
COUNTER_LOWER = "counter_lower"

# A Yes / No reading is stored as 1 / 0, so one value column serves every kind (§ 4); the API
# reads and writes the words.  This and answer_word are the one mapping (BR3-04).
YES_NO_VALUES = {"yes": Decimal(1), "no": Decimal(0)}

LOW, HIGH, NOT_OK = "low", "high", "not_ok"


def answer_word(value):
    """A stored Yes / No reading (1 / 0) → "yes" / "no"."""
    return "yes" if Decimal(value) == YES_NO_VALUES["yes"] else "no"


def _parse_value(raw, kind, decimals):
    """``(Decimal, None)`` or ``(None, message)`` for the value of one reading (§ 5.1).  The
    kind decides the rules: a Yes / No meter has "Pick Yes or No" alone (BR3-05)."""
    if kind == YES_NO:
        if isinstance(raw, str) and raw in YES_NO_VALUES:
            return YES_NO_VALUES[raw], None
        return None, PICK_YES_OR_NO
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None, ENTER_THE_READING
    try:
        value = parse_number(raw, decimals)
    except ValueError as exc:
        return None, str(exc)
    if value < 0 and kind in BELOW_ZERO:
        return None, BELOW_ZERO[kind]
    return value, None


def validate_reading(value, kind, decimals, reset, note):
    """One reading's value, Meter reset mark and note → ``(clean, errors)``, errors in the
    masters_core shape, in the order of § 5.1.  ``clean`` holds ``value`` (a Decimal: 1 / 0 for
    a Yes / No answer), ``is_reset`` (bool) and ``note`` (trimmed, None when empty)."""
    clean, errors = {}, []
    clean["value"], message = _parse_value(value, kind, decimals)
    if message:
        errors.append({"field": "value", "message": message})

    if not isinstance(reset, bool):
        errors.append({"field": "is_reset", "message": RESET_NOT_BOOL})
    elif reset and kind != COUNTER:
        errors.append({"field": "is_reset", "message": ONLY_A_COUNTER_RESETS})
    else:
        clean["is_reset"] = reset

    if note is None:
        clean["note"] = None
    elif not isinstance(note, str):
        errors.append({"field": "note", "message": NOTE_NOT_TEXT})
    elif len(note.strip()) > NOTE_MAX:
        errors.append({"field": "note", "message": NOTE_TOO_LONG})
    else:
        clean["note"] = note.strip() or None
    return clean, errors


def to_minute(moment):
    """Readings are kept to the minute, as ticket event times (§ 4)."""
    return moment.replace(second=0, microsecond=0)


def reading_time_error(taken_at, now):
    """The window a reading's time must fall in → the message, or None: at most FUTURE_SKEW
    ahead of ``now``, at most READING_BACKDATE_DAYS back (exactly 7 days is allowed)."""
    if taken_at > now + FUTURE_SKEW:
        return EVENT_TIME_FUTURE
    if taken_at < now - timedelta(days=READING_BACKDATE_DAYS):
        return READING_TOO_OLD
    return None


def parse_taken_at(raw, now):
    """``taken_at`` of a reading → ``(datetime, None)`` or ``(None, message)``.  Absent: ``now``
    (the server's clock decides, so a phone a few minutes off is never refused, S040 BR1-09).
    ``now`` is the IST wall clock to the minute; a time sent with seconds keeps its minute."""
    if raw is None:
        return now, None
    taken_at, message = parse_event_time(raw)
    if message:
        return None, EVENT_TIME_FORMAT
    taken_at = to_minute(taken_at)
    message = reading_time_error(taken_at, now)
    return (None, message) if message else (taken_at, None)


def grouped_number(value, decimals):
    """A number with the type's decimals and Indian grouping, as the screens show it
    (``toLocaleString("en-IN")``, U4): 1234567.8 with 1 decimal → "12,34,567.8"."""
    text = f"{Decimal(value):.{decimals}f}"
    sign, text = ("-", text[1:]) if text.startswith("-") else ("", text)
    whole, _, fraction = text.partition(".")
    if len(whole) > 3:
        head, groups = whole[:-3], [whole[-3:]]
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(groups)
    return sign + whole + (f".{fraction}" if fraction else "")


def reading_text(value, meter_type):
    """A reading as the screens show it: "12,345.6 h", "420 pcs", "Yes"."""
    if meter_type["kind"] == YES_NO:
        return answer_word(value).capitalize()
    return f"{grouped_number(value, meter_type['decimals'])} {meter_type['unit']}"


def _when(moment):
    return moment.strftime("%d-%m-%Y %H:%M")


def counter_error(value, is_reset, before, after, meter_type):
    """A counter reading against the nearest active readings before and after its time (§ 5.2.4)
    → ``(field, message, code)`` or None.  ``before`` / ``after`` are ``{value, taken_at,
    is_reset}`` or None; ``meter_type`` gives the unit and decimals of the message.  Equal
    values pass (a machine that did not run); a reset with no earlier reading passes, and so
    does a reset equal to the one before (BR2-13).

    Known gap (CR1-08, for the phase 5 usage sums): a back-dated reset placed before an existing
    later reset is not checked against it ("unless that one is a reset"), and removing the reading
    before a reset is not checked either, so a reset may end up higher than the reading before it."""
    if before is not None:
        if not is_reset and value < before["value"]:
            shown = reading_text(before["value"], meter_type)
            return ("value", f"Lower than the reading of {_when(before['taken_at'])} ({shown})."
                             " Check the value, or tick Meter reset if the meter was reset.", COUNTER_LOWER)
        if is_reset and value > before["value"]:
            return "is_reset", RESET_ABOVE_BEFORE, None
    if after is not None and not after["is_reset"] and value > after["value"]:
        shown = reading_text(after["value"], meter_type)
        return ("value", f"Higher than the later reading of {_when(after['taken_at'])} ({shown})."
                         " Check the value and the time.", None)
    return None


def limit_state(value, low, high):
    """A gauge reading against the limits in force → "low", "high" or None (a value equal to a
    limit is inside).  Either limit may be None: no limit on that side."""
    if low is not None and value < Decimal(low):
        return LOW
    if high is not None and value > Decimal(high):
        return HIGH
    return None


def answer_state(answer, expected):
    """A Yes / No answer ("yes" / "no") against the type's expected one → "not_ok" or None."""
    return NOT_OK if answer != expected else None


def may_remove(reading, can_edit):
    """Who may remove a reading (U3): a holder of equipment:edit at the node's site (``can_edit``),
    and only while the reading is active.  No author rule."""
    return bool(can_edit) and reading["removed_at"] is None


def reset_removal_error(reading, has_later):
    """A reset reading with an active later reading cannot be removed (BR1-04): the later, lower
    readings would be left with no reset, and no back-dated reading could fit between them."""
    return RESET_HAS_LATER if reading["is_reset"] and has_later else None


def parse_reading_request(body, now):
    """What a reading POST names before its meter is known → ``({meter_type_id, taken_at},
    errors)``.  The value, the reset mark and the note need the meter's kind: validate_reading,
    once the meter is read."""
    meter_type_id, errors = parse_meter_type_id(body, PICK_A_METER)
    taken_at, message = parse_taken_at(body.get("taken_at"), now)
    if message:
        errors = [*errors, {"field": "taken_at", "message": message}]
    return {"meter_type_id": meter_type_id, "taken_at": taken_at}, errors


# ---------------------------------------------------------------------------
# The reading register (S050, docs/steps/S050-reading-register/1-brief.md § 5)
# ---------------------------------------------------------------------------

def parse_meter_type_ids(raw):
    """The register's ``meter_type_ids`` query (§ 5.5) → ``(ids, errors)``: ``ids`` None for all
    (absent or empty), else the ids in the order first named, duplicates dropped.  Spaces around
    an id are trimmed; anything but a comma list of positive integers is refused."""
    if raw is None or raw.strip() == "":
        return None, []
    ids = []
    for part in raw.split(","):
        text = part.strip()
        if not (text.isascii() and text.isdigit()) or int(text) < 1:
            return None, [{"field": "meter_type_ids", "message": PICK_A_METER}]
        if int(text) not in ids:
            ids.append(int(text))
    return ids, []


def register_columns(meters_in_force, read_types):
    """The register's columns (§ 5.1): the node's meters in force (``effective_meters``' list, in
    its order), then every meter type of ``read_types`` (the types with an active reading on the
    node) that is not in force, by name, with ``in_force`` False and no limits."""
    in_force_ids = {meter["meter_type"]["id"] for meter in meters_in_force}
    columns = [{"meter_type": meter["meter_type"], "in_force": True,
                "min_value": meter["min_value"], "max_value": meter["max_value"]} for meter in meters_in_force]
    gone = sorted((t for t in read_types if t["id"] not in in_force_ids), key=lambda t: (t["name"].casefold(), t["id"]))
    columns.extend({"meter_type": t, "in_force": False, "min_value": None, "max_value": None} for t in gone)
    return columns


def shown_meter_ids(columns, wanted):
    """The columns the rows are built for (§ 5.5): the ``wanted`` ids that are columns, in column
    order; all columns when ``wanted`` is None or names none of them (a stale bookmark, BR1-03)."""
    column_ids = [column["meter_type"]["id"] for column in columns]
    shown = [i for i in column_ids if wanted is not None and i in wanted]
    return shown or column_ids


def register_rows(readings, columns):
    """The register's rows (§ 5.2): one per distinct ``taken_at``, newest first, each
    ``{taken_at, cells: {meter_type_id: {id, value, limit_state, is_reset}}}``.  ``readings`` are
    active reading rows (id, meter_type_id, value, taken_at, is_reset, limit_state); a column gives
    its meter's kind, so a Yes / No value is worded "yes" / "no" and any other as format_number.
    A reading of a meter that is not a column is left out."""
    kinds = {column["meter_type"]["id"]: column["meter_type"]["kind"] for column in columns}
    by_minute = {}
    # S039 refuses a second active reading of one meter at one minute (SAME_MINUTE); should the data
    # ever hold two, the higher id is the later write and wins: readings are taken in id order
    for reading in sorted(readings, key=lambda r: r["id"]):
        kind = kinds.get(reading["meter_type_id"])
        if kind is None:
            continue
        value = answer_word(reading["value"]) if kind == YES_NO else format_number(reading["value"])
        by_minute.setdefault(reading["taken_at"], {})[reading["meter_type_id"]] = {
            "id": reading["id"], "value": value, "limit_state": reading["limit_state"],
            "is_reset": bool(reading["is_reset"])}
    return [{"taken_at": minute, "cells": by_minute[minute]} for minute in sorted(by_minute, reverse=True)]


# ---------------------------------------------------------------------------
# Meter readings on the ticket (S052, docs/steps/S052-ticket-meters/1-brief.md § 5)
# ---------------------------------------------------------------------------

# The marked readings counted before the ticket's time; the same week as READING_BACKDATE_DAYS
MARK_WINDOW_DAYS = 7


def mark_window(at):
    """The start of the marked-readings window before the ticket's time ``at``: the window is
    (``since``, ``at``], so a reading exactly MARK_WINDOW_DAYS before is outside it."""
    return at - timedelta(days=MARK_WINDOW_DAYS)


def readings_at_ticket(meters, at_readings, mark_counts, node_id):
    """The ticket card's lines for one node (§ 5.2), in the meters' order: each
    ``{meter_type, at_ticket, marked_count}``.  ``meters`` are the node's meters in force
    (``effective_meters``); ``at_readings`` and ``mark_counts`` are keyed by (node_id,
    meter_type_id): the reading the shell picked (already worded by reading_out) and the number
    of marked readings in the window.  A meter with no reading has ``at_ticket`` None; with no
    count, 0 (a counter and an amount store no mark)."""
    lines = []
    for meter in meters:
        key = (node_id, meter["meter_type"]["id"])
        lines.append({"meter_type": meter["meter_type"], "at_ticket": at_readings.get(key),
                      "marked_count": mark_counts.get(key, 0)})
    return lines


# ---------------------------------------------------------------------------
# Meter links (S104 A1, docs/steps/S104-pm-templates-one-path/1-brief.md § 10 A1.6)
# ---------------------------------------------------------------------------
# A part (a component unit or a component) with no meter of its own uses the meter of its parent or its parent's
# parent through a node_meter_links row.  The readings and the limits stay on that source node; the link only says
# which count the part runs with (ISO 14224: operating time is recorded on the item it is measured on).

SOURCE_LINKED = "linked"          # a card entry's ``source`` for a linked meter, beside SOURCE_MODEL / SOURCE_NODE
# Why a link is not in use, in the order they are judged (A1.6.1)
OWN, NOT_ABOVE, NO_SOURCE_METER = "own", "not_above", "no_source_meter"

MACHINE_HAS_NONE_ABOVE = "A machine has no node above it. Add the meter on the machine itself."
PICK_A_NODE_ABOVE = "Pick a node above this part."
LINK_FIELDS = ("meter_type_id", "source_equipment_id")
MOVE_NAMED_MAX = 5                # the move's refusal names the first 5 links and plans, then "and N more"


def no_source_meter(source_code, type_name):
    return f"{source_code} has no {type_name} meter. Reload the page."


def already_links(source_code, type_name):
    return f"This part already uses {source_code}'s {type_name}. Remove that link first."


def uses_link(source_code, type_name):
    return f"This part uses {source_code}'s {type_name}. Remove that link first."


def linked_limits(source_code):
    return f"This is {source_code}'s meter. Set its limits on {source_code}."


def link_text(type_name, source_code):
    """"Run hours from PR-07": the history line's value and the move's list."""
    return f"{type_name} from {source_code}"


def parse_link_body(body):
    """A link's body -> ``(clean, errors)``: ``meter_type_id`` and ``source_equipment_id``, each an integer of 1 or
    more (never a boolean); the first bad or missing field gives "Pick a meter" on it."""
    clean = {}
    for field in LINK_FIELDS:
        raw = body.get(field)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            return {}, [{"field": field, "message": PICK_A_METER}]
        clean[field] = raw
    return clean, []


def link_states(own_type_ids, links, above_ids, types_by_node):
    """Whether each of a part's links is in use, judged live (A1.6.1) -> ``{meter_type_id: None or reason}``.
    ``own_type_ids`` are the types in force on the part itself; ``links`` its rows (meter_type_id,
    source_equipment_id); ``above_ids`` the part's parent and grandparent ids; ``types_by_node`` the types in force
    on each node (a source missing from it has none).  A link is in use unless, in this order: the part has the type
    itself (OWN), the source is not above the part (NOT_ABOVE), the source has no meter of the type now
    (NO_SOURCE_METER)."""
    above = set(above_ids)
    states = {}
    for link in links:
        type_id, source = link["meter_type_id"], link["source_equipment_id"]
        if type_id in own_type_ids:
            states[type_id] = OWN
        elif source not in above:
            states[type_id] = NOT_ABOVE
        elif type_id not in types_by_node.get(source, ()):
            states[type_id] = NO_SOURCE_METER
        else:
            states[type_id] = None
    return states


def broken_links(links, kept_ids):
    """The links a move breaks (A1.6.4): those whose source is not among ``kept_ids`` (the moved node, its new
    parent and the new parent's parent).  ``links`` are the moved node's and its parts'."""
    return [link for link in links if link["source_equipment_id"] not in kept_ids]


def _named(texts, separator):
    """The first MOVE_NAMED_MAX texts, then "and N more"."""
    shown = list(texts[:MOVE_NAMED_MAX])
    if len(texts) > MOVE_NAMED_MAX:
        shown.append(f"and {len(texts) - MOVE_NAMED_MAX} more")
    return separator.join(shown)


def move_warning(broken, plans):
    """The move's refusal (A1.6.4): the links it removes (rows with part_code, type_name, source_code) and the PM
    plans that use them (rows with name and the part's code).  The plans' sentences are left out when no plan uses
    the links."""
    one = len(broken) == 1
    links = _named([f"{link['part_code']} — {link_text(link['type_name'], link['source_code'])}" for link in broken],
                   "; ")
    text = f"This move removes {len(broken)} meter link{'' if one else 's'}: {links}."
    if plans:
        names = _named([f"{plan['name']} ({plan['code']})" for plan in plans], ", ")
        text += (f" PM plans that use {'it' if one else 'them'} make no job until the part has the meter again: "
                 f"{names}. A Last done meter value entered for {'this meter' if one else 'these meters'} is no "
                 "longer used.")
    return text
