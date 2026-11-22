"""Tasks on a ticket — pure rules (docs/steps/S106-ticket-tasks/1-brief.md § 5; no DB).

A task is one piece of a ticket's corrective work (EN 13306 fault diagnosis and correction; ISO 9001
§ 10.2.1 a), given to one person with a due date: open, then done (with what was done) or cancelled (with a
reason); done and cancelled are final.  This module holds the bounds and messages, the add and change body,
the state refusals, the timeline's lines and the close block.  The rules a task shares with a countermeasure
(the done and cancel bodies, the due date and done time, overdue, counts and flags) are imported from
improvements_core and used as they are (§ 7 D8); tickets.py (the shell) feeds them the rows it has locked or
read.  Import direction: ticket_tasks_core -> improvements_core -> tickets_core, so no cycle (D9).
"""

from contracts_core import iso_date
from improvements_core import (
    ACTION_CANCELLED, ACTION_DONE, ACTION_OPEN, ACTION_STATES, OWNER_NEEDED, is_id, required_field, text_field,
)
from tickets_core import LABOUR_DATE_FORMAT, edit_lines

# The states: a countermeasure's values under the task's own names (§ 5.5)
TASK_OPEN = ACTION_OPEN
TASK_DONE = ACTION_DONE
TASK_CANCELLED = ACTION_CANCELLED
TASK_STATES = ACTION_STATES

# The timeline's four events (§ 5.5).  None is in tickets_core.ORDERED_EVENTS, so they set no bound for a
# later move's time and ticket_times skips them.
TASK_ADDED = "task_added"
TASK_CHANGED = "task_changed"
TASK_DONE_EVENT = "task_done"
TASK_CANCELLED_EVENT = "task_cancelled"
TASK_EVENTS = (TASK_ADDED, TASK_CHANGED, TASK_DONE_EVENT, TASK_CANCELLED_EVENT)

# Cancelled ones counted (§ 5.2)
TASKS_MAX = 30
# Not a countermeasure's 500: a change's "old → new" line must fit ticket_events.remark (D11)
TASK_TEXT_MAX = 300

TEXT_NEEDED = "Enter what to do"
TEXT_TOO_LONG = f"What to do: up to {TASK_TEXT_MAX} characters"
TEXT_NOT_TEXT = "What to do must be text"
TASKS_FULL = f"A ticket holds up to {TASKS_MAX} tasks. Change an open one instead."
OWNER_OR_ASSIGNER = "Only the owner, or an engineer or manager of this site, can mark this task done"
ONLY_OPEN_CHANGES = "Only an open task can be changed"
ALREADY_DONE = "This task is already done"
WAS_CANCELLED = "This task was cancelled"
DONE_NOT_CANCELLED = "A done task cannot be cancelled"
ALREADY_CANCELLED = "This task is already cancelled"

# What a task in each state refuses, per operation (§ 5.5): None = allowed
_STATE_REFUSALS = {
    "change": {TASK_DONE: ONLY_OPEN_CHANGES, TASK_CANCELLED: ONLY_OPEN_CHANGES},
    "done": {TASK_DONE: ALREADY_DONE, TASK_CANCELLED: WAS_CANCELLED},
    "cancel": {TASK_DONE: DONE_NOT_CANCELLED, TASK_CANCELLED: ALREADY_CANCELLED},
}

# A change's line: the fields and their labels, in this order (tickets_core.edit_lines)
EDIT_LABELS = {"text": "What to do", "owner": "Owner", "due": "Due"}


def validate_task(body, creating):
    """The add (``creating``) or change body -> ``(clean, errors)`` for clean_body (§ 5.2).  On an add every
    field is required; on a change an absent field stays as it is and none may be null.  Whether the owner may
    own it (the shell's person_at_site) and the due date's range (improvements_core.due_date_error) are checked
    after, with the database.  Unknown fields, the state and the done and cancel fields are ignored."""
    clean, errors = {}, []
    read, missing = required_field(body, "text", creating)
    if read:
        text_field(body, "text", TASK_TEXT_MAX, TEXT_NEEDED, TEXT_TOO_LONG, TEXT_NOT_TEXT, clean, errors)
    elif missing:
        errors.append({"field": "text", "message": TEXT_NEEDED})
    read, missing = required_field(body, "owner_id", creating)
    if read and is_id(body["owner_id"]):
        clean["owner_id"] = body["owner_id"]
    elif read or missing:
        errors.append({"field": "owner_id", "message": OWNER_NEEDED})
    read, missing = required_field(body, "due_date", creating)
    due = iso_date(body["due_date"]) if read else None
    if due is not None:
        clean["due_date"] = due
    elif read or missing:
        errors.append({"field": "due_date", "message": LABOUR_DATE_FORMAT})
    return clean, errors


def task_state_error(operation, state):
    """May ``operation`` (change, done, cancel) act on a task in ``state`` (§ 5.5)?  None, or the refusal
    (a 409)."""
    return _STATE_REFUSALS[operation].get(state)


def task_line(text, owner_name, due):
    """The *task_added* line: the text, then "Owner: <name>. Due DD-MM-YYYY." on a line of its own."""
    return f"{text}\nOwner: {owner_name}. Due {due:%d-%m-%Y}."


def task_change_line(old, new):
    """The *task_changed* line: "Label: old → new" per changed field (tickets_core.edit_lines).  ``old`` and
    ``new`` hold ``text``, ``owner`` (the name) and ``due`` (a date), ``new`` only the fields that changed.
    Both also hold ``owner_id`` when the owner changes: two people may share a name, and then each name is
    shown with its person id, so the line still keeps the old and the new owner (CR1-03; ticket_tasks keeps
    only the current one).  At most 855 characters (§ 5.5), 895 with the ids, inside the remark's 1000."""
    def shown(values, same_name):
        out = {key: values[key] for key in ("text", "owner") if key in values}
        if same_name:
            out["owner"] = f"{values['owner']} (person {values['owner_id']})"
        if "due" in values:
            out["due"] = f"{values['due']:%d-%m-%Y}"
        return out
    same_name = "owner" in new and new["owner"] == old.get("owner") and "owner_id" in new and "owner_id" in old
    return edit_lines(shown(old, same_name), shown(new, same_name), EDIT_LABELS)


def close_block(open_count):
    """Why *Close* and *Not a fault* are refused (§ 5.5, D4): None when no task is open, else the message (a
    409, and the moves' ``blocked_reason``)."""
    if open_count == 0:
        return None
    if open_count == 1:
        return "This ticket has 1 open task. Mark it done or cancel it first."
    return f"This ticket has {open_count} open tasks. Mark them done or cancel them first."
