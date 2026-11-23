"""Tasks on a ticket — pure rules (S106 § 8.2; no DB)."""

from datetime import date

import pytest

import improvements_core
from improvements_core import ACTION_STATES, OWNER_NEEDED
from ticket_tasks_core import (
    ALREADY_CANCELLED, ALREADY_DONE, DONE_NOT_CANCELLED, DUE_NEEDED, ONLY_OPEN_CHANGES, TASK_CANCELLED, TASK_DONE,
    TASK_EVENTS, TASK_OPEN, TASK_STATES, TASK_TEXT_MAX, TASKS_FULL, TASKS_MAX, TEXT_NEEDED, TEXT_NOT_TEXT,
    TEXT_TOO_LONG, WAS_CANCELLED, close_block, task_change_line, task_line, task_state_error, validate_task,
)
from tickets_core import LABOUR_DATE_FORMAT, ORDERED_EVENTS

GOOD = {"text": "Check the space heater circuit and find any fuse", "owner_id": 4, "due_date": "2026-11-25"}
DATE_FORMAT = LABOUR_DATE_FORMAT


def _errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_task(body, creating)[1]]


class TestValidateTask:

    def test_a_good_add(self):
        clean, errors = validate_task({**GOOD, "text": "  Check the heater  "}, True)
        assert errors == []
        assert clean == {"text": "Check the heater", "owner_id": 4, "due_date": date(2026, 11, 25)}

    def test_a_missing_field_on_an_add_gives_its_first_message(self):
        assert _errors({}) == [("text", TEXT_NEEDED), ("owner_id", OWNER_NEEDED), ("due_date", DUE_NEEDED)]

    @pytest.mark.parametrize("creating", [True, False])
    def test_null_is_refused_on_add_and_change(self, creating):
        assert _errors({"text": None, "owner_id": None, "due_date": None}, creating) == [
            ("text", TEXT_NEEDED), ("owner_id", OWNER_NEEDED), ("due_date", DUE_NEEDED)]

    @pytest.mark.parametrize("creating", [True, False])
    @pytest.mark.parametrize("due", ["", "   ", None])
    def test_an_empty_due_date_asks_to_choose_one(self, due, creating):
        """S107 § 5.3: the dialog's words, not the API's format words (D13)."""
        assert _errors({**GOOD, "due_date": due}, creating) == [("due_date", DUE_NEEDED)]
        assert DUE_NEEDED == "Choose the due date"

    def test_a_missing_due_date_asks_on_an_add_and_stays_on_a_change(self):
        body = {key: value for key, value in GOOD.items() if key != "due_date"}
        assert _errors(body) == [("due_date", DUE_NEEDED)]
        assert _errors(body, creating=False) == []

    def test_the_text(self):
        assert _errors({**GOOD, "text": "   "}) == [("text", TEXT_NEEDED)]
        assert _errors({**GOOD, "text": "x" * TASK_TEXT_MAX}) == []
        assert _errors({**GOOD, "text": "x" * (TASK_TEXT_MAX + 1)}) == [("text", TEXT_TOO_LONG)]
        assert _errors({**GOOD, "text": 42}) == [("text", TEXT_NOT_TEXT)]
        assert TEXT_TOO_LONG == "What to do: up to 300 characters"

    @pytest.mark.parametrize("owner", [True, False, 0, -1, "4", 4.0])
    def test_the_owner_must_be_an_id(self, owner):
        assert _errors({**GOOD, "owner_id": owner}) == [("owner_id", OWNER_NEEDED)]

    @pytest.mark.parametrize("due", ["22-11-2026", "2026-02-30", "20261122", "2026-W47-7", 20261122])
    def test_the_due_date_is_yyyy_mm_dd(self, due):
        assert _errors({**GOOD, "due_date": due}) == [("due_date", DATE_FORMAT)]

    def test_the_due_date_is_trimmed(self):
        assert validate_task({**GOOD, "due_date": " 2026-11-25 "}, True)[0]["due_date"] == date(2026, 11, 25)

    def test_a_change_with_no_field_is_empty(self):
        assert validate_task({}, False) == ({}, [])

    def test_a_change_takes_only_what_is_sent(self):
        assert validate_task({"due_date": "2026-12-01"}, False) == ({"due_date": date(2026, 12, 1)}, [])

    def test_unknown_and_state_fields_are_ignored(self):
        clean, errors = validate_task({**GOOD, "state": "done", "done_text": "x", "cancel_reason": "y", "kind": 1},
                                      True)
        assert errors == [] and set(clean) == {"text", "owner_id", "due_date"}


class TestStates:

    @pytest.mark.parametrize("operation, state, message", [
        ("change", TASK_OPEN, None), ("change", TASK_DONE, ONLY_OPEN_CHANGES),
        ("change", TASK_CANCELLED, ONLY_OPEN_CHANGES),
        ("done", TASK_OPEN, None), ("done", TASK_DONE, ALREADY_DONE), ("done", TASK_CANCELLED, WAS_CANCELLED),
        ("cancel", TASK_OPEN, None), ("cancel", TASK_DONE, DONE_NOT_CANCELLED),
        ("cancel", TASK_CANCELLED, ALREADY_CANCELLED),
    ])
    def test_the_nine_cells(self, operation, state, message):
        assert task_state_error(operation, state) == message

    def test_the_states_are_a_countermeasures(self):
        assert TASK_STATES == ACTION_STATES == (TASK_OPEN, TASK_DONE, TASK_CANCELLED)

    def test_required_field_is_the_function_behind_required(self):
        assert improvements_core.required_field is improvements_core._required

    def test_the_events_are_not_ordered(self):
        assert not set(TASK_EVENTS) & set(ORDERED_EVENTS)
        assert all(len(event) <= 30 for event in TASK_EVENTS)     # ticket_events.event is VARCHAR(30)


class TestLines:

    def test_close_block(self):
        assert close_block(0) is None
        assert close_block(1) == "This ticket has 1 open task. Mark it done or cancel it first."
        assert close_block(3) == "This ticket has 3 open tasks. Mark them done or cancel them first."

    def test_task_line(self):
        assert task_line("Check the heater", "Ravi K", date(2026, 11, 25)) == (
            "Check the heater\nOwner: Ravi K. Due 25-11-2026.")

    def test_a_change_line_names_only_what_changed(self):
        old = {"text": "Check the heater", "owner": "Ravi K", "due": date(2026, 11, 25)}
        assert task_change_line(old, {"due": date(2026, 11, 28)}) == "Due: 25-11-2026 → 28-11-2026"
        assert task_change_line(old, {}) == ""
        assert task_change_line(old, {"text": "Check the fuse", "owner": "Mani S", "due": date(2026, 12, 1)}) == (
            "What to do: Check the heater → Check the fuse\nOwner: Ravi K → Mani S\nDue: 25-11-2026 → 01-12-2026")

    def test_an_owner_of_the_same_name_is_told_apart_by_the_person_id(self):
        old = {"text": "Heat", "owner": "Ravi K", "owner_id": 12, "due": date(2026, 11, 25)}
        assert task_change_line(old, {"owner": "Ravi K", "owner_id": 15}) == (
            "Owner: Ravi K (person 12) → Ravi K (person 15)")
        # Different names: no ids; the id is only for a name that would hide the change
        assert task_change_line(old, {"owner": "Mani S", "owner_id": 15}) == "Owner: Ravi K → Mani S"
        # A change of the text alone shows no owner line
        assert task_change_line(old, {"text": "Check"}) == "What to do: Heat → Check"

    def test_the_longest_change_line_with_ids_fits_the_remark(self):
        old = {"text": "a" * TASK_TEXT_MAX, "owner": "o" * 100, "owner_id": 4294967295, "due": date(2026, 11, 25)}
        new = {"text": "b" * TASK_TEXT_MAX, "owner": "o" * 100, "owner_id": 4294967294, "due": date(2027, 11, 25)}
        assert len(task_change_line(old, new)) <= 1000

    def test_the_longest_change_line_fits_the_remark(self):
        old = {"text": "a" * TASK_TEXT_MAX, "owner": "o" * 100, "due": date(2026, 11, 25)}
        new = {"text": "b" * TASK_TEXT_MAX, "owner": "p" * 100, "due": date(2027, 11, 25)}
        line = task_change_line(old, new)
        assert len(line) == 855
        assert len(line) <= 1000        # ticket_events.remark is VARCHAR(1000)

    def test_tasks_full(self):
        assert TASKS_MAX == 30
        assert TASKS_FULL == "A ticket holds up to 30 tasks. Change an open one instead."
