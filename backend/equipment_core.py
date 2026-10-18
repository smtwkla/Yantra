"""Equipment register — pure rules (no DB, no Flask, no clock).

docs/steps/S002-equipment-register/1-brief.md.  The shell (equipment.py) fetches
and locks rows, passes plain values in, and acts on what comes back.

The tree has three fixed levels (ISO 14224 levels 6-8): equipment, component
unit, component.  Only equipment has a unit; a part sits under a parent.

Every node has a model (S012); its class and type come from the model and are never
set apart from it.
"""

from masters_core import RESERVED_TYPE_NAME, optional_text_parser, parse_name

LEVELS = ("equipment", "component_unit", "component")
STATUSES = ("in_service", "standby", "out_of_use", "scrapped")
CRITICALITIES = ("A", "B", "C")
SCRAPPED = "scrapped"

# New equipment starts at the lowest grade until someone ranks it (decision § 3.1)
DEFAULT_CRITICALITY = "C"

# How an own criticality of NULL (a part inheriting its equipment's grade) shows in events
INHERIT = "inherit"

# How a node without a type shows in events; masters refuses it as a type name
NO_TYPE = RESERVED_TYPE_NAME

YEAR_MIN = 1900
TEXT_MAX = 100
NOTES_MAX = 2000

# level -> the levels its parent may have; equipment has no parent
_ALLOWED_PARENTS = {
    "equipment": (),
    "component_unit": ("equipment",),
    "component": ("component_unit", "equipment"),
}

# Messages for a parent of the wrong level (or a missing one)
_PARENT_ERRORS = {
    "equipment": "Equipment cannot have a parent",
    "component_unit": "A component unit must sit under an equipment",
    "component": "A component must sit under a component unit or an equipment",
}


# ---------------------------------------------------------------------------
# Small parsers — each returns the clean value or raises ValueError(message)
# ---------------------------------------------------------------------------

def _enum_parser(label, allowed):
    def parse(raw):
        if raw not in allowed:
            raise ValueError(f"{label} must be one of: {', '.join(allowed)}")
        return raw
    return parse


def _is_id(raw):
    return isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1


def _id_parser(label, nullable):
    def parse(raw):
        if raw is None and nullable:
            return None
        if not _is_id(raw):
            raise ValueError(f"{label} must be a record id")
        return raw
    return parse


def _year_parser(this_year):
    def parse(raw):
        if raw is None:
            return None
        if not isinstance(raw, int) or isinstance(raw, bool) or not YEAR_MIN <= raw <= this_year + 1:
            raise ValueError(f"Year must be between {YEAR_MIN} and {this_year + 1}")
        return raw
    return parse


def _parse_criticality(raw):
    if raw is None:
        return None
    return _enum_parser("Criticality", CRITICALITIES)(raw)


# ---------------------------------------------------------------------------
# Public rules
# ---------------------------------------------------------------------------

def format_equipment_code(prefix, number):
    """VBM + 1 -> VBM001; past 999 the number simply grows (VBM1000)."""
    return prefix + str(number).zfill(3)


def check_parent(child_level, parent_level):
    """Return an error message if a node of child_level may not sit under parent_level
    (None = no parent), else None."""
    allowed = _ALLOWED_PARENTS[child_level]
    if parent_level in allowed or (not allowed and parent_level is None):
        return None
    return _PARENT_ERRORS[child_level]


def effective_criticality(own, equipment_grade):
    """A part's own grade wins; NULL means it inherits its root equipment's grade."""
    return own if own is not None else equipment_grade


def full_path(site_code, unit_code, codes_root_to_node):
    """SITE.UNIT.EQUIP[.COMPUNIT][.COMPONENT] — derived for display and events, never stored."""
    return ".".join([site_code, unit_code, *codes_root_to_node])


def check_status_change(old, new):
    """Return an error message if the status may not go from old to new (old None = on create).

    Whether a node's parts allow scrapping needs the database; the shell checks that.
    """
    if old is None:
        return "A new record cannot be scrapped" if new == SCRAPPED else None
    if old == SCRAPPED and new != SCRAPPED:
        return "Scrapped is final; the status cannot change"
    return None


def check_type_class(type_class_id, owner_class_id):
    """Return an error message if a type of type_class_id may not be given to a record of
    owner_class_id (ISO 14224: a type belongs to one class), else None.  Since S012 the
    record is an equipment model; equipment takes its type from the model."""
    if type_class_id != owner_class_id:
        return "This type belongs to another class"
    return None


MODEL_INACTIVE = "This model is inactive"


def derive_from_model(stored_model_id, model):
    """The class and type a node gets from the model a write picks (S012 § 5.3) ->
    ``(class_id, type_id, message)``.

    ``stored_model_id`` is the locked node's model (None on create); ``model`` is the locked
    row ``{id, class_id, type_id, active}``.  A newly picked model must be active; an
    unchanged inactive one is kept.  The type is taken as it is (None when the model has
    none), never checked for active: the model's own flag governs what can be picked.
    ``message`` is None or MODEL_INACTIVE; the shell picks the status (409)."""
    newly_picked = model["id"] != stored_model_id
    message = MODEL_INACTIVE if newly_picked and not model["active"] else None
    return model["class_id"], model["type_id"], message


# Tracked display value -> event name.  The move is named by the node's level:
# equipment moves between units, a part moves between parents.
_TRACKED = (
    ("full_path", None),
    ("model_label", "model"),
    ("class_code", "class"),
    ("type_name", "type"),
    ("criticality", "criticality"),
    ("status", "status"),
)


def _display(key, value):
    if key == "criticality" and value is None:
        return INHERIT
    if key == "type_name" and value is None:
        return NO_TYPE
    return value


def tracked_changes(before, after):
    """Compare two dicts of display values; return ``[(event, old, new)]`` for each tracked change.

    Keys read: ``level``, ``full_path``, ``model_label``, ``class_code``, ``type_name``
    (None = no type), ``criticality`` (own value, None = inherit) and ``status``.  Any other
    key (name, serial number, notes, ...) is not tracked.  Types are compared by name, so a reclassification
    between two types of the same name gives no type event (S004 § 5.2).
    """
    changes = []
    for key, event in _TRACKED:
        old, new = _display(key, before.get(key)), _display(key, after.get(key))
        if old == new:
            continue
        if event is None:
            event = "moved_unit" if after["level"] == "equipment" else "moved_parent"
        changes.append((event, old, new))
    return changes


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

PICK_A_MODEL = "Pick a model"

# Keys an old open tab may still send (S012 § 5.4): refused, even as null or unchanged, so
# such a tab fails loudly instead of having its make, model, class or type ignored
_REFUSED_FIELDS = {
    "make": "Make and model are now picked from Models",
    "model": "Make and model are now picked from Models",
    "class_id": "Class and type come from the model",
    "type_id": "Class and type come from the model",
}


def _parse_model_id(raw):
    """Required on create and never cleared: missing and null get the same message."""
    if not _is_id(raw):
        raise ValueError(PICK_A_MODEL)
    return raw


def _fields(this_year):
    """field -> (parser, required when creating).  level/code are handled separately;
    model_id has its own message when missing (validate_equipment)."""
    return {
        "parent_id": (_id_parser("Parent", nullable=True), False),
        "unit_id": (_id_parser("Unit", nullable=True), False),
        "model_id": (_parse_model_id, True),
        "name": (parse_name, True),
        "serial_no": (optional_text_parser("Serial number", TEXT_MAX), False),
        "year": (_year_parser(this_year), False),
        "criticality": (_parse_criticality, False),
        "status": (_enum_parser("Status", STATUSES), False),
        "notes": (optional_text_parser("Notes", NOTES_MAX), False),
    }


def _check_immutable(data, stored, errors):
    """On an update, code and level may be sent back unchanged but never changed."""
    if "code" in data:
        sent = data["code"].strip().upper() if isinstance(data["code"], str) else data["code"]
        if sent != stored["code"]:
            errors.append({"field": "code", "message": "Code cannot be changed"})
    if "level" in data and data["level"] != stored["level"]:
        errors.append({"field": "level", "message": "Level cannot be changed"})


def _check_place(level, clean, creating, errors):
    """Equipment has a unit and no parent; parts have a parent and no unit.  On an update an
    absent field is unchanged, so only what was sent is checked.  A field that already
    failed its own parsing is not reported twice."""
    failed = {e["field"] for e in errors}
    if level == "equipment":
        if clean.get("parent_id") is not None:
            errors.append({"field": "parent_id", "message": check_parent(level, "equipment")})
        if ("unit_id" in clean or creating) and clean.get("unit_id") is None and "unit_id" not in failed:
            errors.append({"field": "unit_id", "message": "Unit is required for equipment"})
        if "criticality" in clean and clean["criticality"] is None:
            errors.append({"field": "criticality", "message": "Criticality is required for equipment"})
    else:
        if clean.get("unit_id") is not None:
            errors.append({"field": "unit_id",
                           "message": "A part takes its equipment's unit; give its parent instead"})
        if ("parent_id" in clean or creating) and clean.get("parent_id") is None and "parent_id" not in failed:
            errors.append({"field": "parent_id", "message": check_parent(level, None)})


def validate_equipment(data, creating, this_year, stored=None):
    """Return ``(clean, errors)`` in the masters_core shape (errors: list of {field, message}).

    ``this_year`` is the current IST year, passed in by the shell.  ``make``, ``model``,
    ``class_id`` and ``type_id`` are refused (S012 § 5.4); the class and type come from the
    model (derive_from_model).  On an update,
    ``stored`` is the node's current ``{code, level}``: code and level may be sent
    back unchanged (they are then dropped) but not changed, and the place rules are
    checked against the stored level.  On create the code is issued by the shell,
    so a ``code`` in the body is ignored like any other unknown field.
    """
    clean, errors = {}, []

    for field, message in _REFUSED_FIELDS.items():
        if field in data:
            errors.append({"field": field, "message": message})

    if creating:
        try:
            level = _enum_parser("Level", LEVELS)(data.get("level"))
            clean["level"] = level
        except ValueError as exc:
            errors.append({"field": "level", "message": str(exc)})
            level = None
    else:
        _check_immutable(data, stored, errors)
        level = stored["level"]

    for field, (parse, required) in _fields(this_year).items():
        if field not in data:
            if creating and required:
                message = PICK_A_MODEL if field == "model_id" else f"{field.replace('_', ' ').capitalize()} is required"
                errors.append({"field": field, "message": message})
            continue
        try:
            clean[field] = parse(data[field])
        except ValueError as exc:
            errors.append({"field": field, "message": str(exc)})

    if level is not None:
        _check_place(level, clean, creating, errors)
        if creating:
            if level == "equipment" and "criticality" not in clean:
                clean["criticality"] = DEFAULT_CRITICALITY
            # Absent keys are not written: a part's NULL parent_id/unit_id are the column defaults
            clean = {k: v for k, v in clean.items() if not (k in ("parent_id", "unit_id") and v is None)}

    if creating and "status" in clean:
        message = check_status_change(None, clean["status"])
        if message:
            errors.append({"field": "status", "message": message})

    return clean, errors
