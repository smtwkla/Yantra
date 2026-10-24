"""Equipment properties — pure rules (no DB, no Flask) (docs/steps/S043-equipment-properties/1-brief.md § 5).

A property is a technical datum of a class of equipment (ISO 14224 Annex A equipment-specific
data), defined once with a data type and, for a number, a unit (IEC 61360: one definition,
reused across classes).  Its value sits on the model (the maker's design value); S044 adds the
item's own.  Validators return ``(clean, errors)`` like masters_core; value parsers return
``(value, message)``, where ``(None, None)`` means "clear the value".
"""

import math
import re
from decimal import Decimal, InvalidOperation

NUMBER = "number"
CHOICE = "choice"
TEXT = "text"
YES_NO = "yes_no"
DATA_TYPES = (NUMBER, CHOICE, TEXT, YES_NO)

NAME_MAX = 80               # property_definitions.name
UNIT_MAX = 20               # property_definitions.unit
DESCRIPTION_MAX = 300       # property_definitions.description
OPTION_LABEL_MAX = 60       # property_options.label
TEXT_VALUE_MAX = 100        # model_property_values.value_text
NUMBER_DECIMALS = 4         # DECIMAL(16,4)
NUMBER_LIMIT = Decimal(10) ** 12   # DECIMAL(16,4) holds 12 digits before the point

# Messages (scope B, § 5.1, § 5.2)
ENTER_NAME = "Enter a name"
NAME_TOO_LONG = f"Use {NAME_MAX} characters or fewer"
CHOOSE_DATA_TYPE = "Choose a data type"
UNIT_TOO_LONG = f"Use {UNIT_MAX} characters or fewer"
UNIT_ONLY_NUMBER = "Only a number has a unit"
DESCRIPTION_TOO_LONG = f"Use {DESCRIPTION_MAX} characters or fewer"
ACTIVE_FLAG = "Active must be true or false"
DATA_TYPE_FIXED = ("The data type cannot be changed: the property has options or models hold values of it. "
                   "Make a new property instead.")
UNIT_FIXED = "The unit cannot be changed: models hold values of this property. Make a new property instead."
ENTER_LABEL = "Enter a label"
LABEL_TOO_LONG = f"Use {OPTION_LABEL_MAX} characters or fewer"
OPTION_EXISTS = "An option with this label exists"
ONLY_CHOICE_HAS_OPTIONS = "Only a choice has options"

ENTER_NUMBER = "Enter a number"
TOO_MANY_DECIMALS = f"Use up to {NUMBER_DECIMALS} decimals"
NUMBER_TOO_BIG = "Enter a smaller number"
TEXT_TOO_LONG = f"Use {TEXT_VALUE_MAX} characters or fewer"
ENTER_TEXT = "Enter text"
CHOOSE_YES_NO = "Choose Yes or No"
CHOOSE_OPTION = "Choose an option from the list"

VALUES_NOT_OBJECT = "Send the values as an object"
NOT_ON_CLASS = "This property is not on the class"
CHOOSE_ACTIVE_PROPERTIES = "Choose active properties"
CHOOSE_A_PROPERTY = "Choose at least one property"

# Plain digits only (§ 5.2, § 9.8): an optional minus, digits, optionally a point and digits.
# No plus, exponent, inner space or thousands separator; the decimals are counted afterwards,
# so "0.00001" is told "Use up to 4 decimals", not "Enter a number".
_NUMBER_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?")
# A key of the values object is a property id: a positive whole number, as a string
_ID_KEY_RE = re.compile(r"[1-9][0-9]*")

# The typed column each data type's value is stored in (model_property_values, § 4.2)
VALUE_COLUMNS = {NUMBER: "value_number", TEXT: "value_text", YES_NO: "value_bool", CHOICE: "option_id"}


# ---------------------------------------------------------------------------
# A property and its options (§ 5.1)
# ---------------------------------------------------------------------------

def _collapsed(raw):
    """Trimmed, with every run of inner spaces as one (as masters_core: one spelling per thing)."""
    return " ".join(raw.split())


def _parse_name(raw):
    if not isinstance(raw, str) or not _collapsed(raw):
        raise ValueError(ENTER_NAME)
    name = _collapsed(raw)
    if len(name) > NAME_MAX:
        raise ValueError(NAME_TOO_LONG)
    return name


def _parse_data_type(raw):
    if raw not in DATA_TYPES:
        raise ValueError(CHOOSE_DATA_TYPE)
    return raw


def _optional_text(max_len, message):
    """Trimmed text, empty -> None; a non-string gets the field's own message (§ 5.1)."""
    def parse(raw):
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(message)
        text = raw.strip()
        if len(text) > max_len:
            raise ValueError(message)
        return text or None
    return parse


def _parse_active(raw):
    if isinstance(raw, bool) or raw in (0, 1):
        return int(raw)
    raise ValueError(ACTIVE_FLAG)


def _parse_label(raw):
    if not isinstance(raw, str) or not _collapsed(raw):
        raise ValueError(ENTER_LABEL)
    label = _collapsed(raw)
    if len(label) > OPTION_LABEL_MAX:
        raise ValueError(LABEL_TOO_LONG)
    return label


def _parse_option_labels(raw):
    """The options sent with a new choice: a list of labels, each by the option rule; a label
    twice in the list (case-insensitive, as the column's collation) is refused here, before the
    UNIQUE index would refuse it on a field the create dialog does not show."""
    if not isinstance(raw, list):
        raise ValueError(ENTER_LABEL)
    labels, seen = [], set()
    for entry in raw:
        label = _parse_label(entry)
        if label.casefold() in seen:
            raise ValueError(OPTION_EXISTS)
        seen.add(label.casefold())
        labels.append(label)
    return labels


# field -> (parser, required when creating)
_PROPERTY_FIELDS = {
    "name": (_parse_name, True),
    "data_type": (_parse_data_type, True),
    "unit": (_optional_text(UNIT_MAX, UNIT_TOO_LONG), False),
    "description": (_optional_text(DESCRIPTION_MAX, DESCRIPTION_TOO_LONG), False),
    "active": (_parse_active, False),
}
_REQUIRED_MESSAGES = {"name": ENTER_NAME, "data_type": CHOOSE_DATA_TYPE, "label": ENTER_LABEL}

_OPTION_FIELDS = {
    "label": (_parse_label, True),
    "active": (_parse_active, False),
}


def _validate(data, fields, creating):
    clean, errors = {}, []
    for field, (parse, required) in fields.items():
        if field not in data:
            if creating and required:
                errors.append({"field": field, "message": _REQUIRED_MESSAGES[field]})
            continue
        try:
            clean[field] = parse(data[field])
        except ValueError as exc:
            errors.append({"field": field, "message": str(exc)})
    return clean, errors


def validate_property(data, creating):
    """The fields sent -> ``(clean, errors)``.  On create, ``options`` (a choice's first
    labels) is accepted too and comes back as a list.  The combined record (a unit on a
    non-number) is property_changes' job, since an update sees only the fields sent."""
    clean, errors = _validate(data, _PROPERTY_FIELDS, creating)
    if creating and "options" in data:
        try:
            clean["options"] = _parse_option_labels(data["options"])
        except ValueError as exc:
            errors.append({"field": "options", "message": str(exc)})
        else:
            if clean["options"] and clean.get("data_type", CHOICE) != CHOICE:
                errors.append({"field": "options", "message": ONLY_CHOICE_HAS_OPTIONS})
    return clean, errors


def validate_option(data, creating):
    return _validate(data, _OPTION_FIELDS, creating)


def property_changes(stored, clean, has_options=False, has_values=False):
    """The columns to write for a create (``stored`` None) or an edit of ``stored`` with the
    validated ``clean`` fields -> ``(changes, None)`` or ``(None, (field, message, status))``.

    The record as it will be is checked whole (BR1-03): a unit only on a number; a type
    leaving *number* drops its unit in the same write.  The data type is fixed once the
    property has any option or value, the unit once it has a value (409)."""
    changes = {k: v for k, v in clean.items() if k != "options"}
    old_type = stored["data_type"] if stored else None
    old_unit = stored["unit"] if stored else None
    new_type = changes.get("data_type", old_type)
    if new_type != NUMBER:
        if changes.get("unit") is not None:
            return None, ("unit", UNIT_ONLY_NUMBER, 400)
        if old_unit is not None:
            changes["unit"] = None
    if stored is None:
        return changes, None
    if new_type != old_type and (has_options or has_values):
        return None, ("data_type", DATA_TYPE_FIXED, 409)
    if changes.get("unit", old_unit) != old_unit and has_values:
        return None, ("unit", UNIT_FIXED, 409)
    for field in ("data_type", "unit"):
        if field in changes and changes[field] == stored[field]:
            del changes[field]
    return changes, None


# ---------------------------------------------------------------------------
# A value (§ 5.2)
# ---------------------------------------------------------------------------

def _is_blank(raw):
    return raw is None or (isinstance(raw, str) and not raw.strip())


def _parse_number(raw):
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        return None, ENTER_NUMBER
    if isinstance(raw, float) and not math.isfinite(raw):
        return None, ENTER_NUMBER
    if isinstance(raw, str):
        text = raw.strip()
        if not _NUMBER_RE.fullmatch(text):
            return None, ENTER_NUMBER
    else:
        text = str(raw)     # never Decimal(float): 62.1 would gain binary digits
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None, ENTER_NUMBER
    if not number.is_finite():
        return None, ENTER_NUMBER
    # Judged on the value, so 62.50 has two decimals and 1e-05 (a JSON number) has five
    if number != 0 and number.normalize().as_tuple().exponent < -NUMBER_DECIMALS:
        return None, TOO_MANY_DECIMALS
    if abs(number) >= NUMBER_LIMIT:
        return None, NUMBER_TOO_BIG
    return number, None


def _parse_text(raw):
    if not isinstance(raw, str):
        return None, ENTER_TEXT
    text = raw.strip()
    if len(text) > TEXT_VALUE_MAX:
        return None, TEXT_TOO_LONG
    return text, None


def _parse_yes_no(raw):
    if isinstance(raw, bool):
        return int(raw), None
    return None, CHOOSE_YES_NO


def _parse_choice(raw, options, stored_option_id):
    """An option id of this property, active; an inactive one only as the stored value, unchanged."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None, CHOOSE_OPTION
    option = next((o for o in options if o["id"] == raw), None)
    if option is None or not (option["active"] or raw == stored_option_id):
        return None, CHOOSE_OPTION
    return raw, None


def parse_value(data_type, raw, options=(), stored_option_id=None):
    """A value as sent -> ``(value, None)``, ``(None, None)`` to clear, or ``(None, message)``.
    ``options`` (``[{id, active}]``) and ``stored_option_id`` are the property's, for a choice."""
    if _is_blank(raw):
        return None, None
    if data_type == NUMBER:
        return _parse_number(raw)
    if data_type == TEXT:
        return _parse_text(raw)
    if data_type == YES_NO:
        return _parse_yes_no(raw)
    return _parse_choice(raw, options, stored_option_id)


def number_text(value):
    """A stored number as the API sends it and the card shows it: no trailing zeros ("62.5",
    not "62.5000"), never exponent form (a plain normalize() gives "1E+2" for 100)."""
    normal = value.normalize()
    return "0" if normal == 0 else format(normal, "f")


def stored_value(data_type, row):
    """The value of a stored model_property_values row as the API sends it: a number as its
    normalised string, yes/no as a bool, a choice as its option id, text as text; None
    without a row."""
    if row is None:
        return None
    raw = row[VALUE_COLUMNS[data_type]]
    if raw is None:
        return None
    if data_type == NUMBER:
        return number_text(Decimal(str(raw)))
    if data_type == YES_NO:
        return bool(raw)
    return raw


def format_value(data_type, value, unit=None, option_label=None):
    """A value for reading: "62.5 kVA", "3", "Yes", "Internal" — or None for no value.
    ``value`` is the stored one (a Decimal, 0/1, an option id, a string)."""
    if value is None:
        return None
    if data_type == NUMBER:
        text = number_text(Decimal(str(value)))
        return f"{text} {unit}" if unit else text
    if data_type == YES_NO:
        return "Yes" if value else "No"
    if data_type == CHOICE:
        return option_label
    return value


# ---------------------------------------------------------------------------
# Class links (§ 6.2) and a model's values (§ 5.3)
# ---------------------------------------------------------------------------

def parse_property_ids(raw):
    """``property_ids`` of an add -> ``(ids ascending, None)`` or ``(None, message)``; read as a set."""
    if not isinstance(raw, list) or not raw or any(
            isinstance(i, bool) or not isinstance(i, int) or i < 1 for i in raw):
        return None, CHOOSE_A_PROPERTY
    return sorted(set(raw)), None


def can_link(prop, active_option_count):
    """A property may be added to a class when it is active and, for a choice, has an active option."""
    return bool(prop["active"]) and (prop["data_type"] != CHOICE or active_option_count > 0)


def parse_value_keys(values):
    """The ``values`` object of a model save -> ``(ids ascending, None)`` or ``(None, (field, message))``.
    A key that is not a positive whole number names no property of the class."""
    if not isinstance(values, dict):
        return None, ("values", VALUES_NOT_OBJECT)
    for key in values:
        if not (isinstance(key, str) and _ID_KEY_RE.fullmatch(key)):
            return None, (f"values.{key}", NOT_ON_CLASS)
    return sorted(int(key) for key in values), None


def check_model_values(values, properties, options, stored):
    """The changes a model save makes -> ``(changes, None)`` or ``(None, (field, message))``.

    ``values``: the body's ``{"<property_id>": raw}`` (keys already checked by parse_value_keys);
    ``properties``: ``{id: {id, name, data_type, active, linked}}`` for the ids found;
    ``options``: ``{property_id: [{id, active}]}``; ``stored``: ``{property_id: row}`` of the
    model's current values.  The values are checked by property name and the first refusal
    answers, so nothing is saved (§ 5.3).  An unknown id has no name, so the unknown ones are
    refused first, by id; an inactive or unlinked property is refused in its name's place (CR1-05).
    ``changes`` is ``[(property_id, columns or None to clear)]``."""
    unknown = sorted(int(key) for key in values if int(key) not in properties)
    if unknown:
        return None, (f"values.{unknown[0]}", NOT_ON_CLASS)
    changes = []
    for key in sorted(values, key=lambda k: (properties[int(k)]["name"].casefold(), int(k))):
        prop = properties[int(key)]
        if not prop["active"] or not prop["linked"]:
            return None, (f"values.{key}", NOT_ON_CLASS)
        stored_row = stored.get(prop["id"])
        value, message = parse_value(prop["data_type"], values[key], options.get(prop["id"], ()),
                                     stored_row["option_id"] if stored_row else None)
        if message:
            return None, (f"values.{key}", message)
        if value is None:
            changes.append((prop["id"], None))
        else:
            columns = dict.fromkeys(VALUE_COLUMNS.values())
            columns[VALUE_COLUMNS[prop["data_type"]]] = value
            changes.append((prop["id"], columns))
    return changes, None


def property_view(properties, model_values, option_labels):
    """The Properties card's rows (§ 5.5, § 6.3), by name: each property given (the active ones
    linked to the item's class) with the model's value -> ``{property_id, name, value, unit,
    display, source}``; ``display`` and ``source`` are None without a value.
    ``model_values``: ``{property_id: row}``; ``option_labels``: ``{option_id: label}``."""
    rows = []
    for prop in sorted(properties, key=lambda p: (p["name"].casefold(), p["id"])):
        row = model_values.get(prop["id"])
        raw = row[VALUE_COLUMNS[prop["data_type"]]] if row else None
        display = format_value(prop["data_type"], raw, prop["unit"], option_labels.get(raw))
        rows.append({
            "property_id": prop["id"],
            "name": prop["name"],
            "value": stored_value(prop["data_type"], row),
            "unit": prop["unit"],
            "display": display,
            "source": "model" if display is not None else None,
        })
    return rows
