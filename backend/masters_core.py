"""Masters — pure input validation and normalisation (no DB, no Flask).

Each validator takes the request body and returns ``(clean, errors)``:
``clean`` holds only the fields that were present and valid, ``errors`` is a
list of ``{field, message}``.  With ``creating=True`` the required fields must
be present; for an update (``creating=False``) an absent field means
"unchanged" and is simply left out of ``clean``.
"""

import re

SITE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9-]{1,19}$")
UNIT_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,19}$")
CLASS_CODE_RE = re.compile(r"^[A-Z]{2,4}$")
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._@-]{0,99}$")

NAME_MAX = 100
# History shows "no type" as this word, so no type may be called it (S004 § 5.1)
RESERVED_TYPE_NAME = "none"
ADDRESS_MAX = 255
WAREHOUSE_MAX = 140


def _code_parser(pattern, label, rule):
    def parse(raw):
        code = raw.strip().upper() if isinstance(raw, str) else ""
        if not pattern.match(code):
            raise ValueError(f"{label} code must be {rule}")
        return code
    return parse


def parse_name(raw):
    name = raw.strip() if isinstance(raw, str) else ""
    if not name:
        raise ValueError("Name is required")
    if len(name) > NAME_MAX:
        raise ValueError(f"Name must be at most {NAME_MAX} characters")
    return name


def _parse_type_name(raw):
    name = parse_name(raw)
    if name.lower() == RESERVED_TYPE_NAME:
        raise ValueError(f'The name "{RESERVED_TYPE_NAME}" is reserved; history uses it for no type')
    return name


def optional_text_parser(label, max_len, upper=False):
    """Stripped text; empty becomes None.  Not upper-cased unless asked."""
    def parse(raw):
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError(f"{label} must be text")
        text = raw.strip()
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


def _parse_id(label):
    def parse(raw):
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
            raise ValueError(f"{label} is required")
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
    "active": (_parse_active, False),
}

# class_id is parsed on update too: the shell refuses a different one (it is fixed after create)
_TYPE_FIELDS = {
    "class_id": (_parse_id("Class"), True),
    "name": (_parse_type_name, True),
    "active": (_parse_active, False),
}


def _validate(data, fields, creating):
    clean, errors = {}, []
    for field, (parse, required) in fields.items():
        if field not in data:
            if creating and required:
                errors.append({"field": field, "message": f"{field.replace('_', ' ').capitalize()} is required"})
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


def validate_equipment_type(data, creating):
    return _validate(data, _TYPE_FIELDS, creating)


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
