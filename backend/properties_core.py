"""Equipment properties — pure rules (no DB, no Flask) (docs/steps/S043-equipment-properties/1-brief.md § 5).

A property is a technical datum of a class of equipment (ISO 14224 Annex A equipment-specific
data), defined once with a data type and, for a number, a unit (IEC 61360: one definition,
reused across classes).  Its value sits on the model (the maker's design value), and an item may
hold its own where its nameplate differs (S044): the item's wins on that item only.  Validators return ``(clean, errors)`` like masters_core; value parsers return
``(value, message)``, where ``(None, None)`` means "clear the value".

S061 (docs/steps/S061-global-properties-gps/1-brief.md): a *Location* data type (``geo``, a
latitude and a longitude), and two flags on a property: ``all_classes`` (on every class, no link
needed) and ``per_item_only`` (installation data, set on each machine, never on the model: ISO
14224 separates installation data, which differ per unit, from design data).
"""

import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

NUMBER = "number"
CHOICE = "choice"
TEXT = "text"
YES_NO = "yes_no"
GEO = "geo"                 # a map position: latitude, longitude (S061)
DATA_TYPES = (NUMBER, CHOICE, TEXT, YES_NO, GEO)

NAME_MAX = 80               # property_definitions.name
UNIT_MAX = 20               # property_definitions.unit
DESCRIPTION_MAX = 300       # property_definitions.description
OPTION_LABEL_MAX = 60       # property_options.label
TEXT_VALUE_MAX = 100        # model_property_values.value_text
NUMBER_DECIMALS = 4         # DECIMAL(16,4)
NUMBER_LIMIT = Decimal(10) ** 12   # DECIMAL(16,4) holds 12 digits before the point
GEO_DECIMALS = Decimal("0.000001")  # DECIMAL(8,6) / DECIMAL(9,6): 6 decimals, about 10 cm
LATITUDE_LIMIT = 90
LONGITUDE_LIMIT = 180

# The level a Location property shows on (S061 D5): equipment_core.LEVELS' top level.  A part is
# where its machine is.
GEO_LEVEL = "equipment"

# Who a values save is for (S061 § 5.4): a per-machine property is refused on a model
OWNER_MODEL = "model"
OWNER_ITEM = "item"

# Messages (scope B, § 5.1, § 5.2)
ENTER_NAME = "Enter a name"
NAME_TOO_LONG = f"Use {NAME_MAX} characters or fewer"
CHOOSE_DATA_TYPE = "Choose a data type"
UNIT_TOO_LONG = f"Use {UNIT_MAX} characters or fewer"
UNIT_ONLY_NUMBER = "Only a number has a unit"
DESCRIPTION_TOO_LONG = f"Use {DESCRIPTION_MAX} characters or fewer"
ACTIVE_FLAG = "Active must be true or false"
CHOOSE_YES_OR_NO = "Choose yes or no"      # all_classes, per_item_only (S061 § 5.1)
PER_ITEM_HAS_MODEL_VALUES = ("Models have values of this property. Clear them in each model first, "
                             "or make a new property.")
# A model's value or an item's own (S044 § 1.6) fixes both
DATA_TYPE_FIXED = ("The data type cannot be changed: the property has options or values. "
                   "Make a new property instead.")
UNIT_FIXED = "The unit cannot be changed: the property has values. Make a new property instead."
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
ENTER_LOCATION = "Enter the location as latitude, longitude, for example 11.016823, 76.955812"
LATITUDE_RANGE = f"The latitude must be between -{LATITUDE_LIMIT} and {LATITUDE_LIMIT}"
LONGITUDE_RANGE = f"The longitude must be between -{LONGITUDE_LIMIT} and {LONGITUDE_LIMIT}"
SET_ON_EACH_MACHINE = "Set this property on each machine, not on the model"

VALUES_NOT_OBJECT = "Send the values as an object"
NOT_ON_CLASS = "This property is not on the class"
CHOOSE_ACTIVE_PROPERTIES = "Choose active properties"
CHOOSE_A_PROPERTY = "Choose at least one property"

# Plain digits only (§ 5.2, § 9.8): an optional minus, digits, optionally a point and digits.
# No plus, exponent, inner space or thousands separator; the decimals are counted afterwards,
# so "0.00001" is told "Use up to 4 decimals", not "Enter a number".
_NUMBER_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?")
# A location (S061 § 5.2): two numbers by the rule above, separated by a comma, by spaces, or both
_GEO_NUMBER = r"(-?[0-9]+(?:\.[0-9]+)?)"
_GEO_RE = re.compile(_GEO_NUMBER + r"(?:\s*,\s*|\s+)" + _GEO_NUMBER)
# A key of the values object is a property id: a positive whole number, as a string
_ID_KEY_RE = re.compile(r"[1-9][0-9]*")

# The typed column each data type's value is stored in (model_property_values, § 4.2; an item's
# own in equipment_property_values, S044 § 4: the same columns)
VALUE_COLUMNS = {NUMBER: "value_number", TEXT: "value_text", YES_NO: "value_bool", CHOICE: "option_id"}
# A location takes two columns (v34), beside the one-column types
GEO_COLUMNS = ("value_lat", "value_lng")
ALL_VALUE_COLUMNS = (*VALUE_COLUMNS.values(), *GEO_COLUMNS)
# The columns compared as numbers (DECIMAL in the database)
_DECIMAL_COLUMNS = (VALUE_COLUMNS[NUMBER], *GEO_COLUMNS)

# The hint on a machine that moves (S061 § 5.5, D7): by the names KLA gave the property and its
# options on production; a rename turns the hint off quietly
MOBILITY = "Mobility"
MOVING_LABELS = ("Portable", "Mobile")
MOVING_HINT = "This machine moves. The location may be out of date."


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


def _flag(message):
    """A yes / no field: true, false, 0 or 1 -> 0 or 1; anything else gets ``message``."""
    def parse(raw):
        if isinstance(raw, bool) or raw in (0, 1):
            return int(raw)
        raise ValueError(message)
    return parse


_parse_active = _flag(ACTIVE_FLAG)


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
    "all_classes": (_flag(CHOOSE_YES_OR_NO), False),
    "per_item_only": (_flag(CHOOSE_YES_OR_NO), False),
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


def property_changes(stored, clean, has_options=False, has_values=False, model_has_values=False):
    """The columns to write for a create (``stored`` None) or an edit of ``stored`` with the
    validated ``clean`` fields -> ``(changes, None)`` or ``(None, (field, message, status))``.

    The record as it will be is checked whole (BR1-03): a unit only on a number; a type
    leaving *number* drops its unit in the same write.  The data type is fixed once the
    property has any option or value, the unit once it has a value (409).  *Value set on each
    machine* cannot be turned on while a model holds a value (``model_has_values``, S061 § 5.1):
    those values would be stranded.  Turning it off is always allowed."""
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
    if changes.get("per_item_only") and not stored["per_item_only"] and model_has_values:
        return None, ("per_item_only", PER_ITEM_HAS_MODEL_VALUES, 409)
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


def _parse_geo(raw):
    """"11.016823, 76.955812" (a comma, spaces, or both between) -> ``((lat, lng), None)``, two
    Decimals rounded to 6 decimals (S061 § 5.2: a paste from Google Maps carries up to 15)."""
    if not isinstance(raw, str):
        return None, ENTER_LOCATION
    match = _GEO_RE.fullmatch(raw.strip())
    if not match:
        return None, ENTER_LOCATION
    lat, lng = (Decimal(text) for text in match.groups())
    # Range first, on the unrounded numbers: quantize() raises InvalidOperation for a huge one.
    if abs(lat) > LATITUDE_LIMIT:
        return None, LATITUDE_RANGE
    if abs(lng) > LONGITUDE_LIMIT:
        return None, LONGITUDE_RANGE
    return tuple(n.quantize(GEO_DECIMALS, rounding=ROUND_HALF_UP) for n in (lat, lng)), None


def parse_value(data_type, raw, options=(), stored_option_id=None):
    """A value as sent -> ``(value, None)``, ``(None, None)`` to clear, or ``(None, message)``.
    ``options`` (``[{id, active}]``) and ``stored_option_id`` are the property's, for a choice.
    A location's value is ``(lat, lng)``."""
    if _is_blank(raw):
        return None, None
    if data_type == NUMBER:
        return _parse_number(raw)
    if data_type == GEO:
        return _parse_geo(raw)
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


def _stored_raw(data_type, row):
    """The stored value of a value row (or a change's columns): its one column, or a location's
    ``(lat, lng)``; None without a row or a value."""
    if row is None:
        return None
    if data_type == GEO:
        lat, lng = (row[column] for column in GEO_COLUMNS)
        return None if lat is None else (lat, lng)
    return row[VALUE_COLUMNS[data_type]]


def geo_text(lat, lng):
    """A location as the API sends it and the card shows it: "11.016823, 76.955812", each number
    without trailing zeros ("11.0168, 76.9558")."""
    return f"{number_text(Decimal(str(lat)))}, {number_text(Decimal(str(lng)))}"


def map_url(data_type, row):
    """The Google Maps link of a location's value row (S061 § 5.2, D4), else None.  Built from
    the stored numbers only, so no outside text enters the URL."""
    raw = _stored_raw(data_type, row) if data_type == GEO else None
    if raw is None:
        return None
    lat, lng = (number_text(Decimal(str(n))) for n in raw)
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def stored_value(data_type, row):
    """The value of a stored model_property_values row as the API sends it: a number as its
    normalised string, yes/no as a bool, a choice as its option id, text as text, a location as
    "lat, lng"; None without a row."""
    raw = _stored_raw(data_type, row)
    if raw is None:
        return None
    if data_type == NUMBER:
        return number_text(Decimal(str(raw)))
    if data_type == YES_NO:
        return bool(raw)
    if data_type == GEO:
        return geo_text(*raw)
    return raw


def format_value(data_type, value, unit=None, option_label=None):
    """A value for reading: "62.5 kVA", "3", "Yes", "Internal", "11.0168, 76.9558" — or None for
    no value.  ``value`` is the stored one (a Decimal, 0/1, an option id, a string, a location's
    ``(lat, lng)``)."""
    if value is None:
        return None
    if data_type == GEO:
        return geo_text(*value)
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


def _by_name(prop):
    """The order of the values checks, the card's rows and the history lines: by name, then id."""
    return prop["name"].casefold(), prop["id"]


def parse_value_keys(values):
    """The ``values`` object of a model save -> ``(ids ascending, None)`` or ``(None, (field, message))``.
    A key that is not a positive whole number names no property of the class."""
    if not isinstance(values, dict):
        return None, ("values", VALUES_NOT_OBJECT)
    for key in values:
        if not (isinstance(key, str) and _ID_KEY_RE.fullmatch(key)):
            return None, (f"values.{key}", NOT_ON_CLASS)
    return sorted(int(key) for key in values), None


def check_values(values, properties, options, stored, *, owner):
    """The changes a values save makes, a model's or an item's (S044 § 5.1) -> ``(changes, None)``
    or ``(None, (field, message))``.

    ``values``: the body's ``{"<property_id>": raw}`` (keys already checked by parse_value_keys);
    ``properties``: ``{id: {id, name, data_type, active, linked, per_item_only}}`` for the ids
    found (``linked``: shown on the model's or the item's node, S061 § 5.3; a property without
    ``per_item_only`` is not per-machine); ``owner``: OWNER_MODEL or OWNER_ITEM, since a model
    may not hold a per-machine property (S061 § 5.4); ``options``: ``{property_id: [{id, active}]}``; ``stored``:
    ``{property_id: row}`` of the owner's current values.  The values are checked by property name and the first refusal
    answers, so nothing is saved (§ 5.3).  An unknown id has no name, so the unknown ones are
    refused first, by id; an inactive or unlinked property is refused in its name's place (CR1-05).
    ``changes`` is ``[(property_id, columns or None to clear)]``."""
    unknown = sorted(int(key) for key in values if int(key) not in properties)
    if unknown:
        return None, (f"values.{unknown[0]}", NOT_ON_CLASS)
    changes = []
    for key in sorted(values, key=lambda k: _by_name(properties[int(k)])):
        prop = properties[int(key)]
        if not prop["active"] or not prop["linked"]:
            return None, (f"values.{key}", NOT_ON_CLASS)
        if owner == OWNER_MODEL and prop.get("per_item_only"):
            return None, (f"values.{key}", SET_ON_EACH_MACHINE)
        stored_row = stored.get(prop["id"])
        value, message = parse_value(prop["data_type"], values[key], options.get(prop["id"], ()),
                                     stored_row["option_id"] if stored_row else None)
        if message:
            return None, (f"values.{key}", message)
        if value is None:
            changes.append((prop["id"], None))
        else:
            columns = dict.fromkeys(ALL_VALUE_COLUMNS)
            if prop["data_type"] == GEO:
                columns.update(zip(GEO_COLUMNS, value))
            else:
                columns[VALUE_COLUMNS[prop["data_type"]]] = value
            changes.append((prop["id"], columns))
    return changes, None


def value_display(prop, row, option_labels):
    """A stored value row of ``prop`` ({data_type, unit}) for reading, by format_value; None
    without a row.  ``option_labels``: ``{option_id: label}``."""
    raw = _stored_raw(prop["data_type"], row)
    return format_value(prop["data_type"], raw, prop["unit"], option_labels.get(raw))


def property_view(properties, model_values, option_labels, item_values=None):
    """The Properties card's rows (§ 5.5, § 6.3), by name: each property given (the active ones
    linked to the item's class, or on every class) with the value in force -> ``{property_id,
    name, data_type, per_item_only, value, unit, display, source, map_url}``.  The item's own value wins (``source`` "item", S044 § 5.5), else the
    model's ("model"); ``display`` and ``source`` are None without a value.  An own value of a
    property not given (not on the class now) is not shown.  ``model_values`` and
    ``item_values``: ``{property_id: row}``; ``option_labels``: ``{option_id: label}``."""
    item_values = item_values or {}
    rows = []
    for prop in sorted(properties, key=_by_name):
        own = item_values.get(prop["id"])
        row = own if own is not None else model_values.get(prop["id"])
        display = value_display(prop, row, option_labels)
        rows.append({
            "property_id": prop["id"],
            "name": prop["name"],
            "data_type": prop["data_type"],
            "per_item_only": bool(prop.get("per_item_only")),
            "value": stored_value(prop["data_type"], row),
            "unit": prop["unit"],
            "display": display,
            "source": None if display is None else ("item" if own is not None else "model"),
            "map_url": map_url(prop["data_type"], row),
        })
    return rows


def on_level(properties, level):
    """The properties a node of ``level`` shows (S061 § 5.3, D5): a location only on top-level
    equipment, since a part is where its machine is.  The same rule lives in
    properties.linked_properties, properties.lock_value_properties and the list's property filter
    (property_filter_core._applies, S062): a change to one is made in all four."""
    return [prop for prop in properties if prop["data_type"] != GEO or level == GEO_LEVEL]


# ---------------------------------------------------------------------------
# The value in force by name, and the hint on a machine that moves (S061 § 5.5)
# ---------------------------------------------------------------------------

def value_in_force(rows, name):
    """From property_view's rows, the row of the property named ``name`` (any case) when it has
    a value, else None."""
    wanted = name.casefold()
    row = next((r for r in rows if r["name"].casefold() == wanted), None)
    return row if row is not None and row["display"] is not None else None


def moving_hint(rows):
    """MOVING_HINT when a location has a value and the Mobility in force is Portable or Mobile
    (any case), else None (S061 D7: the value is still allowed)."""
    if not any(r["data_type"] == GEO and r["display"] is not None for r in rows):
        return None
    mobility = value_in_force(rows, MOBILITY)
    moving = {label.casefold() for label in MOVING_LABELS}
    return MOVING_HINT if mobility is not None and mobility["display"].casefold() in moving else None


# ---------------------------------------------------------------------------
# An item's own values (S044 § 5.1, § 5.4)
# ---------------------------------------------------------------------------

PROPERTY_EVENT = "property"      # equipment_events.event (v33)
NO_VALUE = "no value"
MODEL_MARK = "(model)"


def _same_value(columns, row):
    """A change's columns hold what the stored row holds: a number, or a location's latitude and
    longitude, as a Decimal against the stored DECIMAL (5.5 equals 5.5000), text exactly, yes/no
    as 0/1, a choice by option id."""
    for column in ALL_VALUE_COLUMNS:
        new, old = columns[column], row[column]
        if new is None or old is None:
            if (new is None) != (old is None):
                return False
        elif column in _DECIMAL_COLUMNS:
            if Decimal(str(old)) != new:
                return False
        elif new != old:
            return False
    return True


def item_changes(changes, stored):
    """The real changes of an item's save (S044 § 5.1, BR1-02): check_values' ``changes``
    without a clear of a property with no own row and without a value equal to the own one.
    ``stored``: ``{property_id: row}`` of the item's own values.  The write and item_events take
    this list, so a row that did not change writes nothing and logs nothing."""
    kept = []
    for property_id, columns in changes:
        row = stored.get(property_id)
        if columns is None and row is None:
            continue
        if columns is not None and row is not None and _same_value(columns, row):
            continue
        kept.append((property_id, columns))
    return kept


def item_events(properties, changes, before, model_displays, option_labels, has_model):
    """The ``property`` history lines of an item's save (S044 § 5.4) -> ``[(event, old, new)]``,
    one per change, by property name.  Each side reads "<name>: <display>"; the side with no own
    value shows the value then in force from the model, marked: "Rated power: 7.5 kW (model)",
    "Rated power: no value (model)", or "Rated power: no value" on an item without a model, and
    for a per-machine property, which has no model value (S061 § 5.6).

    ``properties``: ``{id: {id, name, data_type, unit, per_item_only}}`` (without
    ``per_item_only``: not per-machine); ``changes``: item_changes' output;
    ``before``: ``{property_id: row}`` of the own values before the save; ``model_displays``:
    ``{property_id: display or None}`` of the model's values; ``option_labels``: ``{option_id: label}``."""
    def own(prop, row):
        return f"{prop['name']}: {value_display(prop, row, option_labels)}"

    def in_force_from_model(prop):
        if not has_model or prop.get("per_item_only"):
            return f"{prop['name']}: {NO_VALUE}"
        display = model_displays.get(prop["id"])
        return f"{prop['name']}: {NO_VALUE if display is None else display} {MODEL_MARK}"

    events = []
    for property_id, columns in sorted(changes, key=lambda change: _by_name(properties[change[0]])):
        prop = properties[property_id]
        old_row = before.get(property_id)
        old = own(prop, old_row) if old_row is not None else in_force_from_model(prop)
        new = own(prop, columns) if columns is not None else in_force_from_model(prop)
        events.append((PROPERTY_EVENT, old, new))
    return events
