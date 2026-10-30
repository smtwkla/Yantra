"""One-point lessons — pure rules (docs/steps/S075-one-point-lessons/1-brief.md § 5; no DB).

A one-point lesson (TPM, the training pillar) is one title, one short text and a few photos about
one point, written on a machine and, when ticked, shown on every machine of its class (TPM
yokoten).  It is the first kind of the Procedures master (Plan § 4.3a).  This module holds the
kind, the key, the serial, the field bounds and messages, the countermeasure link's rules and the
flags the screens follow.  procedures.py (the shell) feeds it the rows it has locked or read.
"""

from improvements_core import ACTION_CANCELLED, WAS_CANCELLED, is_id, text_field

KIND_ONE_POINT_LESSON = "one_point_lesson"

# Written by the engineer (so the manager), held per site (S075 § 5.7, D4); read with equipment:read
EDIT_KEY = "procedure:edit"
READ_KEY = "equipment:read"

# One plant-wide series, OPL-001, OPL-002, … (D3): the serial_counters scope has no colon, so it
# meets no EQ:, TK: or IM: scope
SERIAL_PREFIX = "OPL"
SERIAL_SCOPE = "OPL"
SERIAL_DIGITS = 3

# The countermeasure kind a lesson may be written for (S070's ENUM value)
LESSON_ACTION_KIND = "lesson"

TITLE_MAX = 80
BODY_MAX = 1000

MACHINE_NEEDED = "Choose the machine"
TITLE_NEEDED = "Enter a title"
TITLE_TOO_LONG = f"Title: up to {TITLE_MAX} characters"
TITLE_NOT_TEXT = "Title must be text"
BODY_NEEDED = "Enter the lesson text"
BODY_TOO_LONG = f"Lesson text: up to {BODY_MAX} characters"
BODY_NOT_TEXT = "Lesson text must be text"
FOR_CLASS_NOT_BOOL = "For the class must be true or false"
ACTION_NEEDED = "Choose a countermeasure"
ACTIVE_NOT_BOOL = "Active must be true or false"

NOT_A_LESSON_ACTION = "Only a countermeasure of kind Lesson links a lesson"
LINK_KEPT = "A lesson keeps the countermeasure it was written for"
# The race past the plain check, caught by uq_procedures_action (no serial known there)
LINK_RACE = "This countermeasure already has a lesson"


def format_lesson_serial(number):
    """OPL-001 … OPL-999, then OPL-1000: the number grows past three digits (D3)."""
    return f"{SERIAL_PREFIX}-{number:0{SERIAL_DIGITS}d}"


def lesson_machine_message(machine_code):
    """§ 5.3 (3): a lesson for a countermeasure sits on its improvement's machine."""
    return f"A lesson for this countermeasure goes on {machine_code}, the improvement's machine"


def already_has_lesson(serial):
    """§ 5.3 (4): one lesson per countermeasure."""
    return f"This countermeasure already has its lesson, {serial}"


def _bool(body, field, message, clean, errors):
    value = body[field]
    if isinstance(value, bool):
        clean[field] = value
    else:
        errors.append({"field": field, "message": message})


def validate_lesson(body, creating):
    """The create (``creating``) or change body -> ``(clean, errors)`` for clean_body (§ 5.2).

    On a create: equipment_id, title and body are required; for_class defaults to False and
    action_id to None; active is ignored (a new lesson is active).  On a change: equipment_id is
    ignored (the machine never changes, D2), an absent field stays as it is (not in ``clean``),
    title and body may not be null.  The title's inner runs of spaces and line breaks become one
    space (a title is one line on a card and on paper); the body keeps its line breaks.  kind is
    never read: the server writes it.  Unknown fields are ignored."""
    clean, errors = {}, []
    if creating:
        if is_id(body.get("equipment_id")):
            clean["equipment_id"] = body["equipment_id"]
        else:
            errors.append({"field": "equipment_id", "message": MACHINE_NEEDED})
    for field, maximum, needed, too_long, not_text in (
            ("title", TITLE_MAX, TITLE_NEEDED, TITLE_TOO_LONG, TITLE_NOT_TEXT),
            ("body", BODY_MAX, BODY_NEEDED, BODY_TOO_LONG, BODY_NOT_TEXT)):
        if field in body and body[field] is not None:
            source = body
            if field == "title" and isinstance(body[field], str):
                source = {field: " ".join(body[field].split())}
            text_field(source, field, maximum, needed, too_long, not_text, clean, errors)
        elif creating or field in body:
            errors.append({"field": field, "message": needed})
    if "for_class" in body:
        _bool(body, "for_class", FOR_CLASS_NOT_BOOL, clean, errors)
    elif creating:
        clean["for_class"] = False
    if "action_id" in body:
        if body["action_id"] is None or is_id(body["action_id"]):
            clean["action_id"] = body["action_id"]
        else:
            errors.append({"field": "action_id", "message": ACTION_NEEDED})
    elif creating:
        clean["action_id"] = None
    if not creating and "active" in body:
        _bool(body, "active", ACTIVE_NOT_BOOL, clean, errors)
    return clean, errors


def lesson_link_error(kind, state):
    """§ 5.3 (2), from the countermeasure's row: only a Lesson countermeasure that is not
    cancelled links a lesson -> the message, or None.  Open and done are allowed, in any state of
    the improvement: linking writes only the lesson row (D8)."""
    if kind != LESSON_ACTION_KIND:
        return NOT_A_LESSON_ACTION
    if state == ACTION_CANCELLED:
        return WAS_CANCELLED
    return None


def link_kept_error(stored_action_id, sent_action_id):
    """§ 5.3, on a change: a stored link is set once (ISO 9001 § 7.5.2, the lesson's identity).
    The same id is no change; another id or null when one is stored -> the message, else None."""
    if stored_action_id is not None and sent_action_id != stored_action_id:
        return LINK_KEPT
    return None


def lesson_flags(for_class, edit_here, edit_anywhere):
    """What the user may do on one lesson (§ 5.7), so no control ends in a 403 (S070 D10).
    ``edit_here``: procedure:edit at the machine's site; ``edit_anywhere``: held at any site.  A
    class lesson is changed with the key held anywhere, a machine lesson with it at the machine's
    site; ticking or unticking the class always needs the machine's site (§ 5.5)."""
    return {"can_edit": edit_anywhere if for_class else edit_here, "can_change_class": edit_here}


def may_write_lesson(kind, state, has_lesson, may_create):
    """The countermeasure's *Write lesson* (§ 5.7): a Lesson countermeasure, not cancelled, with
    no lesson yet, and ``may_create``: the create's own checks (the machine's current unit
    among the user's units and procedure:edit at its site), so the button never ends in a 404
    or a 403."""
    return lesson_link_error(kind, state) is None and not has_lesson and may_create
