"""Masters — pure input validation and normalisation (no DB, no Flask).

Each validator takes the request body and returns ``(clean, errors)``:
``clean`` holds only the fields that were present and valid, ``errors`` is a
list of ``{field, message}``.  With ``creating=True`` the required fields must
be present; for an update (``creating=False``) an absent field means
"unchanged" and is simply left out of ``clean``.
"""

import re

from config_rbac import NO_LOGIN_ROLES, SITE_ROLES, TECHNICIAN_ROLE

SITE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9-]{1,19}$")
UNIT_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,19}$")
CLASS_CODE_RE = re.compile(r"^[A-Z]{2,4}$")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._@-]{0,99}$")

NAME_MAX = 100
TRADE_NAME_MAX = 50
# An equipment category's name (S063 § 5.1); the column is VARCHAR(50)
CATEGORY_NAME_MAX = 50
# A class reactivated in an inactive category (S063 § 5.2, text by KLA at gate B, CR1-03)
CLASS_CATEGORY_INACTIVE = ("This class's category is inactive. Pick another category or No category, "
                           "then reactivate.")
# A model's designation (S012 § 4.1): "<manufacturer> <designation>" then fits the events'
# VARCHAR(200) (100 + 1 + 80)
DESIGNATION_MAX = 80
# A person in the Team register is a direct employee or comes through a contractor (S010 A1)
EMPLOYMENT = ("direct", "contractor")
# History shows "no type" as this word, so no type may be called it (S004 § 5.1)
RESERVED_TYPE_NAME = "none"
ADDRESS_MAX = 255
WAREHOUSE_MAX = 140

# Failure codes (S016 § 5.1): ISO 14224 Annex B codes such as NOI, 3.4 or 12 — letters and
# digits in parts joined by single dots, so a typo like "3." or "1..2" is refused
FAILURE_CODE_RE = re.compile(r"^[A-Z0-9]+(\.[A-Z0-9]+)*$")
FAILURE_CODE_MAX = 8
# A label fits one line of a phone picker
FAILURE_LABEL_MAX = 60
FAILURE_DESCRIPTION_MAX = 255
# ISO 14224 Table B.3's five cause groups, in the order of failure_causes.cause_group's ENUM
CAUSE_GROUPS = ("design", "fabrication", "operation", "management", "misc")


def _code_parser(pattern, label, rule):
    def parse(raw):
        code = raw.strip().upper() if isinstance(raw, str) else ""
        if not pattern.match(code):
            raise ValueError(f"{label} code must be {rule}")
        return code
    return parse


def _parse_bounded_name(raw, max_len):
    name = raw.strip() if isinstance(raw, str) else ""
    if not name:
        raise ValueError("Name is required")
    if len(name) > max_len:
        raise ValueError(f"Name must be at most {max_len} characters")
    return name


def parse_name(raw):
    return _parse_bounded_name(raw, NAME_MAX)


def _collapsed(raw):
    """Trimmed, with every run of inner spaces as one space (S012 § 5.1, ISO 8000: one
    spelling per real thing); the case-insensitive collation does the rest."""
    return " ".join(raw.split()) if isinstance(raw, str) else ""


def _parse_manufacturer_name(raw):
    return _parse_bounded_name(_collapsed(raw), NAME_MAX)


def _parse_designation(raw):
    designation = _collapsed(raw)
    if not designation:
        raise ValueError("Designation is required")
    if len(designation) > DESIGNATION_MAX:
        raise ValueError(f"Designation must be at most {DESIGNATION_MAX} characters")
    return designation


def model_label(manufacturer_name, designation):
    """How a model is named everywhere (lists, pickers, events): "Atlas Copco GA37".  None for
    a node without a model (S033), whose model columns read NULL."""
    if manufacturer_name is None and designation is None:
        return None
    return f"{manufacturer_name} {designation}"


def _parse_trade_name(raw):
    return _parse_bounded_name(raw, TRADE_NAME_MAX)


def _parse_category_name(raw):
    return _parse_bounded_name(raw, CATEGORY_NAME_MAX)


def _parse_type_name(raw):
    name = parse_name(raw)
    if name.lower() == RESERVED_TYPE_NAME:
        raise ValueError(f'Choose another name; "{RESERVED_TYPE_NAME}" is reserved.')
    return name


def optional_text_parser(label, max_len, upper=False, collapse=False):
    """Stripped text; empty becomes None.  Not upper-cased unless asked; inner runs of spaces
    become one space when `collapse` is set."""
    def parse(raw):
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(f"{label} must be text")
        text = _collapsed(raw) if collapse else raw.strip()
        if upper:
            text = text.upper()
        if len(text) > max_len:
            raise ValueError(f"{label} must be at most {max_len} characters")
        return text or None
    return parse


def _flag_parser(label):
    """true/false/1/0 -> 1 or 0."""
    def parse(raw):
        if isinstance(raw, bool) or raw in (0, 1):
            return int(raw)
        raise ValueError(f"{label} must be true or false")
    return parse


_parse_active = _flag_parser("Active")


def _choose_text(label):
    """The refusal of a missing record select (S064 UX-13 row 20): what to do, not what is wrong."""
    return f"Choose a {label.lower()}."


def _parse_id(label):
    def parse(raw):
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            raise ValueError(_choose_text(label))
        return raw
    return parse


def _parse_optional_id(label):
    """A record id, or None for "none"."""
    def parse(raw):
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            raise ValueError(f"{label} must be a record id")
        return raw
    return parse


# field -> (parser, required when creating)
_SITE_FIELDS = {
    "code": (_code_parser(SITE_CODE_RE, "Site", "2–20 characters: capital letters, digits and hyphen, "
                                              "starting with a letter"), True),
    "name": (parse_name, True),
    "address": (optional_text_parser("Address", ADDRESS_MAX), False),
    "active": (_parse_active, False),
    "is_default": (_flag_parser("Default"), False),
}
_UNIT_FIELDS = {
    "site_id": (_parse_id("Site"), True),
    "code": (_code_parser(UNIT_CODE_RE, "Unit", "2–20 characters: capital letters, digits and hyphen"), True),
    "name": (parse_name, True),
    "oneerp_warehouse": (optional_text_parser("OneERP warehouse", WAREHOUSE_MAX), False),
    "active": (_parse_active, False),
}
_CLASS_FIELDS = {
    "code": (_code_parser(CLASS_CODE_RE, "Class", "2–4 capital letters"), True),
    "name": (parse_name, True),
    # Optional: null is "no category" (S063 § 5.2)
    "category_id": (_parse_optional_id("Category"), False),
    "active": (_parse_active, False),
}

# An equipment category groups classes (S063 § 5.1): a name only, no code
_CATEGORY_FIELDS = {
    "name": (_parse_category_name, True),
    "active": (_parse_active, False),
}

# class_id is parsed on update too: the shell refuses a different one (it is fixed after create)
_TYPE_FIELDS = {
    "class_id": (_parse_id("Class"), True),
    "name": (_parse_type_name, True),
    "active": (_parse_active, False),
}

_MANUFACTURER_FIELDS = {
    "name": (_parse_manufacturer_name, True),
    "active": (_parse_active, False),
}

# manufacturer_id, class_id and type_id are parsed on update too: the shell refuses a
# different one (they are fixed after create, S012 § 5.2)
_MODEL_FIELDS = {
    "manufacturer_id": (_parse_id("Manufacturer"), True),
    "designation": (_parse_designation, True),
    "class_id": (_parse_id("Class"), True),
    "type_id": (_parse_optional_id("Type"), False),
    "active": (_parse_active, False),
}


def _parse_failure_code(raw):
    code = raw.strip().upper() if isinstance(raw, str) else ""
    if not (len(code) <= FAILURE_CODE_MAX and FAILURE_CODE_RE.match(code)):
        raise ValueError(f"Use up to {FAILURE_CODE_MAX} letters or digits, parts joined by a dot, e.g. NOI or 3.4.")
    return code


def _parse_failure_label(raw):
    label = _collapsed(raw)
    if not label:
        raise ValueError("Label is required")
    if len(label) > FAILURE_LABEL_MAX:
        raise ValueError(f"Label must be at most {FAILURE_LABEL_MAX} characters")
    return label


def _parse_cause_group(raw):
    if raw not in CAUSE_GROUPS:
        raise ValueError(f"Cause group must be one of: {', '.join(CAUSE_GROUPS)}")
    return raw


_parse_failure_description = optional_text_parser("Description", FAILURE_DESCRIPTION_MAX)

# class_id is parsed on update too: the shell refuses a different one (fixed after create,
# S016 § 5.2).  Absent or null on create = General (every class).
_FAILURE_MODE_FIELDS = {
    "code": (_parse_failure_code, True),
    "label": (_parse_failure_label, True),
    "description": (_parse_failure_description, False),
    "class_id": (_parse_optional_id("Class"), False),
    "active": (_parse_active, False),
}
_FAILURE_CAUSE_FIELDS = {
    "code": (_parse_failure_code, True),
    "label": (_parse_failure_label, True),
    "description": (_parse_failure_description, False),
    "cause_group": (_parse_cause_group, True),
    "active": (_parse_active, False),
}
_MAINTENANCE_ACTION_FIELDS = {
    "code": (_parse_failure_code, True),
    "label": (_parse_failure_label, True),
    "description": (_parse_failure_description, False),
    "active": (_parse_active, False),
}


def _parse_employment(raw):
    if raw not in EMPLOYMENT:
        raise ValueError("Employment must be direct or contractor")
    return raw


def _parse_trade_ids(raw):
    """A list of trade ids, possibly empty (engineers and operators usually have none);
    de-duplicated, order kept."""
    if not isinstance(raw, list) or any(isinstance(i, bool) or not isinstance(i, int) or i < 1 for i in raw):
        raise ValueError("trade_ids must be a list of trade ids")
    return list(dict.fromkeys(raw))


def _parse_login(raw):
    """None or "" clears the login; anything else is a Keycloak username (not checked against Keycloak)."""
    if raw is None or raw == "":
        return None
    username, errors = validate_username(raw)
    if errors:
        raise ValueError(errors[0]["message"])
    return username


_TRADE_FIELDS = {
    "name": (_parse_trade_name, True),
    "active": (_parse_active, False),
}
_PERSON_FIELDS = {
    "name": (parse_name, True),
    "employment": (_parse_employment, True),
    "trade_ids": (_parse_trade_ids, False),
    "username": (_parse_login, False),
    "active": (_parse_active, False),
}


def _missing_text(field):
    """A required field not sent: a record select (``*_id``) reads as a choice, as _parse_id."""
    if field.endswith("_id"):
        return _choose_text(field.removesuffix("_id").replace("_", " "))
    return f"{field.replace('_', ' ').capitalize()} is required"


def _validate(data, fields, creating):
    clean, errors = {}, []
    for field, (parse, required) in fields.items():
        if field not in data:
            if creating and required:
                errors.append({"field": field, "message": _missing_text(field)})
            continue
        try:
            clean[field] = parse(data[field])
        except ValueError as exc:
            errors.append({"field": field, "message": str(exc)})
    return clean, errors


def validate_site(data, creating):
    return _validate(data, _SITE_FIELDS, creating)


def validate_unit(data, creating):
    return _validate(data, _UNIT_FIELDS, creating)


def validate_equipment_class(data, creating):
    return _validate(data, _CLASS_FIELDS, creating)


def validate_equipment_category(data, creating):
    return _validate(data, _CATEGORY_FIELDS, creating)


def category_in_use(active_classes):
    """The refusal of a category deactivation while active classes are in it (S063 § 5.1)."""
    if active_classes == 1:
        return "1 active class is in this category. Move it to another category first."
    return f"{active_classes} active classes are in this category. Move them to another category first."


def validate_equipment_type(data, creating):
    return _validate(data, _TYPE_FIELDS, creating)


def validate_manufacturer(data, creating):
    return _validate(data, _MANUFACTURER_FIELDS, creating)


def validate_equipment_model(data, creating):
    return _validate(data, _MODEL_FIELDS, creating)


def validate_trade(data, creating):
    return _validate(data, _TRADE_FIELDS, creating)


# Meter types (S037 § 5.1).  Kind and unit are what the catalogue is for; Yes / No types have
# no unit and no decimals but an expected answer, the answer that means all is well.
METER_KINDS = ("counter", "gauge", "amount", "yes_no")
MAX_DECIMALS = 3
METER_NAME_MAX = 60
METER_UNIT_MAX = 20
EXPECTED_ANSWERS = ("yes", "no")


def _parse_meter_name(raw):
    return _parse_bounded_name(_collapsed(raw), METER_NAME_MAX)


_parse_meter_unit = optional_text_parser("Unit", METER_UNIT_MAX, collapse=True)


def _parse_meter_kind(raw):
    if raw not in METER_KINDS:
        raise ValueError(f"Kind must be one of: {', '.join(METER_KINDS)}")
    return raw


def _parse_expected_answer(raw):
    """yes or no; empty or null is None (the kind rules decide whether that is allowed)."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    if raw not in EXPECTED_ANSWERS:
        raise ValueError(f"Expected answer must be one of: {', '.join(EXPECTED_ANSWERS)}")
    return raw


def _parse_decimals(raw):
    # bool is an int in Python: refuse it first, as _parse_id does
    if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= MAX_DECIMALS:
        raise ValueError(f"Decimals must be a whole number from 0 to {MAX_DECIMALS}")
    return raw


_METER_TYPE_FIELDS = {
    "name": (_parse_meter_name, True),
    "unit": (_parse_meter_unit, False),
    "kind": (_parse_meter_kind, True),
    "expected_answer": (_parse_expected_answer, False),
    "decimals": (_parse_decimals, False),
    "active": (_parse_active, False),
}
_METER_TYPE_DEFAULTS = {"unit": None, "expected_answer": None, "decimals": 0}


def validate_meter_type(data, creating, stored=None):
    """Two passes (S037 BR2-01): each field alone, then the kind rules on the merged row
    (defaults, then the stored row, then the body), so a PUT that changes the kind is judged
    as the row it would make.  ``stored`` is the locked row on a PUT, nothing on a POST."""
    clean, errors = _validate(data, _METER_TYPE_FIELDS, creating)
    if errors:
        return clean, errors
    row = {**_METER_TYPE_DEFAULTS, **(stored or {}), **clean}
    if row["kind"] == "yes_no":
        if row["unit"] is not None:
            errors.append({"field": "unit", "message": "A Yes / No meter type has no unit"})
        if row["expected_answer"] is None:
            errors.append({"field": "expected_answer", "message": "Expected answer is required"})
        if row["decimals"] != 0:
            errors.append({"field": "decimals", "message": "A Yes / No meter type has no decimals"})
    else:
        if row["unit"] is None:
            errors.append({"field": "unit", "message": "Unit is required"})
        if row["expected_answer"] is not None:
            errors.append({"field": "expected_answer",
                           "message": "Only a Yes / No meter type has an expected answer"})
    return clean, errors


def validate_person(data, creating):
    return _validate(data, _PERSON_FIELDS, creating)


def validate_failure_mode(data, creating):
    return _validate(data, _FAILURE_MODE_FIELDS, creating)


def validate_failure_cause(data, creating):
    return _validate(data, _FAILURE_CAUSE_FIELDS, creating)


def validate_maintenance_action(data, creating):
    return _validate(data, _MAINTENANCE_ACTION_FIELDS, creating)


def normalise_username(raw):
    """Keycloak ``preferred_username``: stripped and lower-cased."""
    return raw.strip().lower() if isinstance(raw, str) else ""


def validate_username(raw):
    """Return ``(username, errors)``."""
    username = normalise_username(raw)
    if not USERNAME_RE.match(username):
        return username, [{"field": "username", "message":
                           "Username must be 1–100 characters: lower-case letters, digits and . _ @ -"}]
    return username, []


def validate_unit_ids(raw):
    """Return ``(unit_ids, errors)``; ids are de-duplicated, order kept."""
    if not isinstance(raw, list) or any(isinstance(i, bool) or not isinstance(i, int) or i < 1 for i in raw):
        return [], [{"field": "unit_ids", "message": "unit_ids must be a list of unit ids"}]
    return list(dict.fromkeys(raw)), []


# ---------------------------------------------------------------------------
# Site roles of a person (S011 A1): one role per site, all units or chosen units
# ---------------------------------------------------------------------------

NO_LOGIN_ROLE_MESSAGE = "Without a login, a person can only be a technician or an operator"


def validate_site_row(body):
    """One site row ``{role, all_units, unit_ids}`` -> ``(clean, errors)``; ``clean`` has all
    three, ``unit_ids`` de-duplicated.  A row has a role (a legacy row without one must get
    one first) and either all units or at least one unit, never both."""
    if not isinstance(body, dict):
        return {}, [{"field": "sites", "message": "Each site must be an object"}]
    role = body.get("role")
    if role is None or role == "":
        return {}, [{"field": "role", "message": "Choose a role"}]
    if role not in SITE_ROLES:
        return {}, [{"field": "role", "message": f"Unknown role {role}"}]
    try:
        all_units = bool(_flag_parser("All units")(body.get("all_units", False)))
    except ValueError as exc:
        return {}, [{"field": "all_units", "message": str(exc)}]
    unit_ids, errors = validate_unit_ids(body.get("unit_ids", []))
    if errors:
        return {}, errors
    if all_units and unit_ids:
        return {}, [{"field": "unit_ids", "message": "With all units, choose no single units"}]
    if not all_units and not unit_ids:
        return {}, [{"field": "unit_ids", "message": "Choose units or all units"}]
    return {"role": role, "all_units": all_units, "unit_ids": unit_ids}, []


def validate_site_rows(raw):
    """The whole set of a person's sites (``sites`` of a login save) -> ``(rows, errors)``;
    each row is validate_site_row's plus ``site_id``.  An empty list removes every site."""
    if not isinstance(raw, list):
        return [], [{"field": "sites", "message": "sites must be a list"}]
    rows, seen = [], set()
    for entry in raw:
        if not isinstance(entry, dict):
            return [], [{"field": "sites", "message": "Each site must be an object"}]
        site_id = entry.get("site_id")
        if isinstance(site_id, bool) or not isinstance(site_id, int) or site_id < 1:
            return [], [{"field": "site_id", "message": "site_id must be a site id"}]
        if site_id in seen:
            return [], [{"field": "sites", "message": "A site can appear only once"}]
        seen.add(site_id)
        clean, errors = validate_site_row(entry)
        if errors:
            return [], errors
        rows.append({"site_id": site_id, **clean})
    return rows, []


def no_login_role_error(roles):
    """A person without a login can only be a technician or an operator (config_rbac.
    NO_LOGIN_ROLES; S011 A1, widened by S017 user decision 5 so the phone-less operator who
    found a fault can be named on the ticket): their site roles describe them for pick-lists;
    everyone else logs in.  The message, or None."""
    return NO_LOGIN_ROLE_MESSAGE if any(role not in NO_LOGIN_ROLES for role in roles) else None


def technician_only(stored_role, new_role):
    """True when a site-row change stays within what an engineer may do (S011 A1, gate A):
    the stored and the new role are each Technician or absent (None)."""
    return stored_role in (None, TECHNICIAN_ROLE) and new_role in (None, TECHNICIAN_ROLE)
