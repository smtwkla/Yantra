"""Improvements — pure rules (S067 § 8.2, S069 § 8.2, S070 § 8.2; no DB)."""

from datetime import date, datetime, timedelta

import pytest

from config_rbac import SITE_ROLES
from improvements_core import (
    ACTION_KINDS, ACTIONS_FULL, action_counts, action_flags, action_state_error, done_time_error, due_date_error,
    overdue_days, validate_action, validate_cancel, validate_done,
    ANSWER_NEEDED, ANSWER_NOT_TEXT, ANSWER_TOO_LONG, CAUSE_NEEDED, CONTRIBUTING_NOT_TEXT, CONTRIBUTING_TOO_LONG,
    EVIDENCE_NOT_TEXT, EVIDENCE_TOO_LONG, QUESTION_NEEDED, QUESTION_NOT_TEXT, QUESTION_TOO_LONG, ROOT_CAUSE_NEEDED,
    POSITION_NOT_NUMBER, ROOT_CAUSE_NOT_TEXT, ROOT_CAUSE_TOO_LONG, WHYS_FULL, WHYS_MAX, position_error, renumber, reorder,
    validate_root_cause, validate_why,
    ALREADY_HERE, IMPROVEMENT_OPEN_STATES, LEAD_NEEDED, NOT_A_FAULT, PROBLEM_NEEDED, PROBLEM_NOT_TEXT,
    PROBLEM_TOO_LONG, START_FROM_STATES, START_STATE, TICKET_NEEDED, TITLE_NEEDED, TITLE_NOT_TEXT, TITLE_TOO_LONG,
    already_in, is_open, keeps_a_ticket, link_error, loss, may_lead, removal_error, start_error,
    validate_improvement, validate_link,
)
from tickets_core import STATES

GOOD = {"ticket_id": 7, "title": "Contactor trips on dust", "problem": "Dust in the panel", "lead_id": 3}


def _errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_improvement(body, creating)[1]]


class TestValidate:

    def test_a_good_start(self):
        assert validate_improvement(GOOD, True) == (GOOD, [])

    def test_trims_and_ignores_unknown_fields(self):
        clean, errors = validate_improvement({**GOOD, "title": "  Dust  ", "state": "closed"}, True)
        assert errors == [] and clean["title"] == "Dust" and "state" not in clean

    @pytest.mark.parametrize("field, message", [
        ("ticket_id", TICKET_NEEDED), ("title", TITLE_NEEDED), ("problem", PROBLEM_NEEDED), ("lead_id", LEAD_NEEDED),
    ])
    def test_each_field_is_required_on_a_start(self, field, message):
        body = {k: v for k, v in GOOD.items() if k != field}
        assert _errors(body) == [(field, message)]

    @pytest.mark.parametrize("field, message", [("title", TITLE_NEEDED), ("problem", PROBLEM_NEEDED)])
    def test_empty_after_trim(self, field, message):
        assert _errors({**GOOD, field: "   "}) == [(field, message)]

    @pytest.mark.parametrize("field, maximum, message", [("title", 120, TITLE_TOO_LONG),
                                                         ("problem", 2000, PROBLEM_TOO_LONG)])
    def test_the_bounds(self, field, maximum, message):
        assert _errors({**GOOD, field: "x" * maximum}) == []
        assert _errors({**GOOD, field: "x" * (maximum + 1)}) == [(field, message)]

    def test_tamil_counts_characters(self):
        assert _errors({**GOOD, "title": "தூசி" * 30}) == []   # 120 characters, more bytes

    @pytest.mark.parametrize("field, message", [("title", TITLE_NOT_TEXT), ("problem", PROBLEM_NOT_TEXT)])
    def test_a_number_is_not_text(self, field, message):
        assert _errors({**GOOD, field: 5}) == [(field, message)]

    @pytest.mark.parametrize("value", [True, 0, -1, "3", 1.5, None])
    def test_a_bad_lead_id(self, value):
        assert _errors({**GOOD, "lead_id": value}) == [("lead_id", LEAD_NEEDED)]

    @pytest.mark.parametrize("value", [True, 0, "7"])
    def test_a_bad_ticket_id(self, value):
        assert _errors({**GOOD, "ticket_id": value}) == [("ticket_id", TICKET_NEEDED)]

    def test_an_edit_takes_only_what_is_sent(self):
        assert validate_improvement({}, False) == ({}, [])
        assert validate_improvement({"title": " New "}, False) == ({"title": "New"}, [])
        assert validate_improvement({"ticket_id": 9, "lead_id": 4}, False) == ({"lead_id": 4}, [])

    def test_an_edit_refuses_null_and_empty(self):
        assert _errors({"lead_id": None}, creating=False) == [("lead_id", LEAD_NEEDED)]
        assert _errors({"title": None}, creating=False) == [("title", TITLE_NEEDED)]
        assert _errors({"problem": ""}, creating=False) == [("problem", PROBLEM_NEEDED)]


class TestValidateLink:

    def test_a_ticket_id(self):
        assert validate_link({"ticket_id": 7}) == ({"ticket_id": 7}, [])

    @pytest.mark.parametrize("body", [{}, {"ticket_id": None}, {"ticket_id": True}, {"ticket_id": "7"}])
    def test_a_bad_one(self, body):
        assert validate_link(body)[1] == [{"field": "ticket_id", "message": TICKET_NEEDED}]


class TestStates:

    def test_only_analysing_and_it_is_open(self):
        assert IMPROVEMENT_OPEN_STATES == ("analysing",)
        assert is_open("analysing") and not is_open("closed")


class TestStart:

    @pytest.mark.parametrize("state", STATES)
    def test_each_ticket_state(self, state):
        expected = None if state in ("back_in_service", "closed") else START_STATE
        assert start_error(state, False) == expected

    def test_from_states(self):
        assert START_FROM_STATES == ("back_in_service", "closed")

    def test_not_a_fault(self):
        assert start_error("closed", True) == NOT_A_FAULT


class TestLinks:

    def test_no_links(self):
        assert link_error("TK-2026-10-002", []) is None

    def test_an_open_link_names_both_serials(self):
        links = [{"improvement_id": 4, "serial": "IM-2026-10-001", "open_link": 1}]
        assert link_error("TK-2026-10-002", links) == "TK-2026-10-002 is already in IM-2026-10-001"
        assert link_error("TK-2026-10-002", links, improvement_id=5) == already_in("TK-2026-10-002", "IM-2026-10-001")

    def test_already_in_this_one(self):
        links = [{"improvement_id": 4, "serial": "IM-2026-10-001", "open_link": 1}]
        assert link_error("TK-2026-10-002", links, improvement_id=4) == ALREADY_HERE

    def test_a_closed_link_does_not_count(self):
        """R05.4 sets open_link to NULL when an improvement closes."""
        assert link_error("TK-2026-10-002", [{"improvement_id": 4, "serial": "IM-2026-10-001", "open_link": None}]) is None


HP003 = {"id": 30, "code": "HP003"}


class TestRemoval:

    def test_the_machines_only_ticket_stays(self):
        links = [{"id": 1, "equipment_id": 30}]
        assert removal_error(links[0], links, HP003) == keeps_a_ticket("HP003") == "An improvement keeps a ticket of HP003."

    def test_also_when_tickets_of_other_machines_remain(self):
        links = [{"id": 1, "equipment_id": 30}, {"id": 2, "equipment_id": 31}]
        assert removal_error(links[0], links, HP003) == keeps_a_ticket("HP003")

    def test_the_machines_second_ticket_may_go(self):
        links = [{"id": 1, "equipment_id": 30}, {"id": 2, "equipment_id": 30}]
        assert removal_error(links[1], links, HP003) is None

    def test_a_ticket_of_another_machine_may_go(self):
        links = [{"id": 1, "equipment_id": 30}, {"id": 2, "equipment_id": 31}]
        assert removal_error(links[1], links, HP003) is None


class TestMayLead:

    @pytest.mark.parametrize("role", SITE_ROLES)
    def test_every_site_role(self, role):
        assert may_lead(role) is (role in ("maint_engineer", "maint_manager"))


class TestLoss:

    def test_no_tickets(self):
        assert loss([]) == {"tickets": 0, "breakdowns": 0, "downtime_minutes": 0}

    def test_defects_only(self):
        tickets = [{"intensity": "degraded", "downtime_minutes": 0}, {"intensity": "initial", "downtime_minutes": 0}]
        assert loss(tickets) == {"tickets": 2, "breakdowns": 0, "downtime_minutes": 0}

    def test_a_mix(self):
        tickets = [{"intensity": "critical", "downtime_minutes": 90}, {"intensity": "critical", "downtime_minutes": 30},
                   {"intensity": "degraded", "downtime_minutes": 0}, {"intensity": "critical", "downtime_minutes": None}]
        assert loss(tickets) == {"tickets": 4, "breakdowns": 3, "downtime_minutes": 120}


# ---------------------------------------------------------------------------
# S069: the why-why chain and the root cause (§ 5.2, § 5.3, § 8.2)
# ---------------------------------------------------------------------------

WHY = {"question": "Why did the press not start?", "answer": "The contactor did not close."}
ROOT = {"root_cause": "The presses have no PM plan", "root_cause_id": 12}


def _why_errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_why(body, creating)[1]]


def _root_errors(body):
    return [(e["field"], e["message"]) for e in validate_root_cause(body, True)[1]]


class TestValidateWhy:

    def test_a_good_add_has_no_evidence(self):
        assert validate_why(WHY, True) == ({**WHY, "evidence": None}, [])

    def test_trims_and_ignores_position_and_unknown_fields_on_an_add(self):
        clean, errors = validate_why({**WHY, "question": "  Why?  ", "position": 1, "id": 4}, True)
        assert errors == [] and clean["question"] == "Why?" and "position" not in clean and "id" not in clean

    @pytest.mark.parametrize("field, message", [("question", QUESTION_NEEDED), ("answer", ANSWER_NEEDED)])
    def test_missing_and_empty_on_an_add(self, field, message):
        assert _why_errors({k: v for k, v in WHY.items() if k != field}) == [(field, message)]
        assert _why_errors({**WHY, field: "   "}) == [(field, message)]

    @pytest.mark.parametrize("field, maximum, too_long, not_text", [
        ("question", 300, QUESTION_TOO_LONG, QUESTION_NOT_TEXT),
        ("answer", 1000, ANSWER_TOO_LONG, ANSWER_NOT_TEXT),
        ("evidence", 500, EVIDENCE_TOO_LONG, EVIDENCE_NOT_TEXT),
    ])
    def test_bounds_and_types(self, field, maximum, too_long, not_text):
        assert _why_errors({**WHY, field: "x" * maximum}) == []
        assert _why_errors({**WHY, field: "x" * (maximum + 1)}) == [(field, too_long)]
        assert _why_errors({**WHY, field: 5}) == [(field, not_text)]

    def test_messages(self):
        assert (QUESTION_TOO_LONG, ANSWER_TOO_LONG, EVIDENCE_TOO_LONG) == (
            "Question: up to 300 characters", "Answer: up to 1000 characters", "Evidence: up to 500 characters")
        assert WHYS_MAX == 20 and WHYS_FULL == "An analysis holds up to 20 whys. Change a why instead."

    @pytest.mark.parametrize("field, message", [("question", QUESTION_NEEDED), ("answer", ANSWER_NEEDED)])
    def test_null_text_on_an_edit(self, field, message):
        assert _why_errors({field: None}, creating=False) == [(field, message)]

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_null_or_empty_evidence_is_none(self, value):
        assert validate_why({**WHY, "evidence": value}, True)[0]["evidence"] is None
        assert validate_why({"evidence": value}, False) == ({"evidence": None}, [])

    def test_an_edit_keeps_absent_fields(self):
        assert validate_why({}, False) == ({}, [])
        assert validate_why({"position": 2}, False) == ({"position": 2}, [])

    @pytest.mark.parametrize("value", [True, "2", 1.5, None])
    def test_position_must_be_an_integer(self, value):
        assert _why_errors({"position": value}, creating=False) == [("position", POSITION_NOT_NUMBER)]


class TestPositions:

    def test_position_error(self):
        assert position_error(3, 0) == "Choose a place from 1 to 3"
        assert position_error(3, 4) == "Choose a place from 1 to 3"
        assert position_error(3, 1) is None and position_error(3, 3) is None

    CHAIN = [(10, 1), (20, 2), (30, 3)]

    def test_to_the_front(self):
        assert reorder(self.CHAIN, 30, 1) == [(30, 1), (10, 2), (20, 3)]

    def test_to_the_end(self):
        assert reorder(self.CHAIN, 10, 3) == [(20, 1), (30, 2), (10, 3)]

    def test_one_step_down(self):
        assert reorder(self.CHAIN, 10, 2) == [(20, 1), (10, 2)]

    def test_to_its_own_place(self):
        assert reorder(self.CHAIN, 20, 2) == []

    def test_renumber_after_the_first_a_middle_and_the_last(self):
        assert renumber([(20, 2), (30, 3)]) == [(20, 1), (30, 2)]
        assert renumber([(10, 1), (30, 3)]) == [(30, 2)]
        assert renumber([(10, 1), (20, 2)]) == []


class TestValidateRootCause:

    def test_good(self):
        assert validate_root_cause({**ROOT, "root_cause": "  No PM plan  "}, True) == (
            {"root_cause": "No PM plan", "root_cause_id": 12}, [])

    def test_missing_both(self):
        assert _root_errors({}) == [("root_cause", ROOT_CAUSE_NEEDED), ("root_cause_id", CAUSE_NEEDED)]
        assert _root_errors({"root_cause": "  ", "root_cause_id": None}) == [
            ("root_cause", ROOT_CAUSE_NEEDED), ("root_cause_id", CAUSE_NEEDED)]

    def test_bounds_and_types(self):
        assert _root_errors({**ROOT, "root_cause": "x" * 500}) == []
        assert _root_errors({**ROOT, "root_cause": "x" * 501}) == [("root_cause", ROOT_CAUSE_TOO_LONG)]
        assert _root_errors({**ROOT, "root_cause": 4}) == [("root_cause", ROOT_CAUSE_NOT_TEXT)]
        assert _root_errors({**ROOT, "contributing_causes": "x" * 2000}) == []
        assert _root_errors({**ROOT, "contributing_causes": "x" * 2001}) == [
            ("contributing_causes", CONTRIBUTING_TOO_LONG)]
        assert _root_errors({**ROOT, "contributing_causes": 4}) == [("contributing_causes", CONTRIBUTING_NOT_TEXT)]
        assert (ROOT_CAUSE_TOO_LONG, CONTRIBUTING_TOO_LONG) == (
            "Root cause: up to 500 characters", "Other causes: up to 2000 characters")

    @pytest.mark.parametrize("value", [True, 0, "12"])
    def test_cause_must_be_an_id(self, value):
        assert _root_errors({**ROOT, "root_cause_id": value}) == [("root_cause_id", CAUSE_NEEDED)]

    @pytest.mark.parametrize("value", [None, "", "  "])
    def test_contributing_causes_cleared(self, value):
        assert validate_root_cause({**ROOT, "contributing_causes": value}, True)[0]["contributing_causes"] is None

    def test_contributing_causes_absent_stays(self):
        assert "contributing_causes" not in validate_root_cause(ROOT, True)[0]


# ---------------------------------------------------------------------------
# Countermeasures (S070 § 8.2)
# ---------------------------------------------------------------------------

ACTION = {"kind": "corrective", "text": "Fit a sealed contact block", "owner_id": 5, "due_date": "2026-11-15"}
TODAY = date(2026, 10, 30)
NOW = datetime(2026, 10, 30, 10, 0)
PROBLEM_AT = datetime(2026, 10, 28, 15, 15)


def _action_errors(body, creating=True):
    return [(e["field"], e["message"]) for e in validate_action(body, creating)[1]]


class TestValidateAction:

    def test_a_good_add(self):
        assert validate_action(ACTION, True) == ({**ACTION, "due_date": date(2026, 11, 15)}, [])

    @pytest.mark.parametrize("kind", ACTION_KINDS)
    def test_each_kind(self, kind):
        assert _action_errors({**ACTION, "kind": kind}) == []

    def test_trims_and_ignores_unknown_fields(self):
        clean, errors = validate_action({**ACTION, "text": "  Seal it  ", "due_date": " 2026-11-15 ",
                                         "state": "done", "done_text": "x", "reason": "y"}, True)
        assert errors == [] and clean["text"] == "Seal it" and clean["due_date"] == date(2026, 11, 15)
        assert set(clean) == {"kind", "text", "owner_id", "due_date"}

    @pytest.mark.parametrize("field, message", [
        ("kind", "Choose the kind"), ("text", "Enter what will be done"), ("owner_id", "Choose the owner"),
        ("due_date", "Enter the date as YYYY-MM-DD"),
    ])
    def test_each_field_is_required_on_an_add(self, field, message):
        assert _action_errors({k: v for k, v in ACTION.items() if k != field}) == [(field, message)]

    @pytest.mark.parametrize("field", ["kind", "text", "owner_id", "due_date"])
    def test_null_on_a_change_is_refused(self, field):
        assert [f for f, _ in _action_errors({field: None}, creating=False)] == [field]

    def test_a_change_takes_only_what_is_sent(self):
        assert validate_action({"text": "New"}, False) == ({"text": "New"}, [])
        assert validate_action({}, False) == ({}, [])

    def test_text_bounds(self):
        assert _action_errors({**ACTION, "text": "x" * 500}) == []
        assert _action_errors({**ACTION, "text": "x" * 501}) == [("text", "What will be done: up to 500 characters")]
        assert _action_errors({**ACTION, "text": "   "}) == [("text", "Enter what will be done")]
        assert _action_errors({**ACTION, "text": 4}) == [("text", "What will be done must be text")]

    @pytest.mark.parametrize("kind", ["Corrective", "kaizen", 3])
    def test_an_unknown_kind(self, kind):
        assert _action_errors({**ACTION, "kind": kind}) == [("kind", "Choose the kind")]

    @pytest.mark.parametrize("owner", [True, 0, "5", 1.5])
    def test_owner_must_be_an_id(self, owner):
        assert _action_errors({**ACTION, "owner_id": owner}) == [("owner_id", "Choose the owner")]

    @pytest.mark.parametrize("due", ["31-10-2026", "2026-02-30", "", 20261031])
    def test_a_bad_due_date(self, due):
        assert _action_errors({**ACTION, "due_date": due}) == [("due_date", "Enter the date as YYYY-MM-DD")]


class TestValidateDone:

    def test_now_is_not_given(self):
        assert validate_done({"done_text": " Fitted "}) == ({"done_text": "Fitted", "done_at": None}, [])
        assert validate_done({"done_text": "Fitted", "done_at": None}) == ({"done_text": "Fitted", "done_at": None}, [])

    def test_a_time_is_parsed(self):
        assert validate_done({"done_text": "Fitted", "done_at": "2026-10-29 14:30"})[0]["done_at"] == (
            datetime(2026, 10, 29, 14, 30))

    def test_a_bad_time(self):
        assert validate_done({"done_text": "Fitted", "done_at": "29-10-2026 14:30"})[1] == [
            {"field": "done_at", "message": "Enter the time as YYYY-MM-DD HH:MM"}]

    def test_done_text_bounds(self):
        assert validate_done({"done_text": "x" * 1000})[1] == []
        assert validate_done({"done_text": "x" * 1001})[1] == [
            {"field": "done_text", "message": "What you did: up to 1000 characters"}]
        assert validate_done({})[1] == [{"field": "done_text", "message": "Say what you did"}]
        assert validate_done({"done_text": "  "})[1] == [{"field": "done_text", "message": "Say what you did"}]
        assert validate_done({"done_text": 4})[1] == [{"field": "done_text", "message": "What you did must be text"}]


class TestValidateCancel:

    def test_reason(self):
        assert validate_cancel({"reason": " Duplicate "}) == ({"reason": "Duplicate"}, [])
        assert validate_cancel({})[1] == [{"field": "reason", "message": "Say why it is cancelled"}]
        assert validate_cancel({"reason": "x" * 500})[1] == []
        assert validate_cancel({"reason": "x" * 501})[1] == [
            {"field": "reason", "message": "Reason: up to 500 characters"}]
        assert validate_cancel({"reason": 4})[1] == [{"field": "reason", "message": "Reason must be text"}]


class TestDates:

    def test_due_date_from_the_problem_to_a_year_ahead(self):
        problem = PROBLEM_AT.date()
        assert due_date_error(problem, problem, TODAY) is None
        assert due_date_error(problem - timedelta(days=1), problem, TODAY) == (
            "Choose a date from 28-10-2026, the day the problem happened")
        assert due_date_error(TODAY + timedelta(days=365), problem, TODAY) is None
        assert due_date_error(TODAY + timedelta(days=366), problem, TODAY) == "Choose a date within a year"
        assert due_date_error(date(2020, 1, 1), None, TODAY) is None

    def test_done_time(self):
        assert done_time_error(NOW + timedelta(minutes=5), NOW, PROBLEM_AT) is None
        assert done_time_error(NOW + timedelta(minutes=6), NOW, PROBLEM_AT) == "That time is in the future"
        assert done_time_error(PROBLEM_AT, NOW, PROBLEM_AT) is None
        assert done_time_error(PROBLEM_AT - timedelta(minutes=1), NOW, PROBLEM_AT) == (
            "Not before the problem happened, 28-10-2026 15:15")
        assert done_time_error(NOW - timedelta(days=60), NOW, None) is None

    def test_done_time_in_the_minute_of_a_problem_with_seconds_passes(self):
        # CR1-03: a ticket raised with Now stores seconds; the message shows only the minute
        problem = PROBLEM_AT.replace(second=42)
        assert done_time_error(PROBLEM_AT, NOW, problem) is None
        assert done_time_error(PROBLEM_AT - timedelta(minutes=1), NOW, problem) == (
            "Not before the problem happened, 28-10-2026 15:15")


class TestActionStates:

    @pytest.mark.parametrize("operation, state, message", [
        ("change", "open", None),
        ("change", "done", "Only an open countermeasure can be changed"),
        ("change", "cancelled", "Only an open countermeasure can be changed"),
        ("done", "open", None),
        ("done", "done", "This countermeasure is already done"),
        ("done", "cancelled", "This countermeasure was cancelled"),
        ("cancel", "open", None),
        ("cancel", "done", "A done countermeasure cannot be cancelled"),
        ("cancel", "cancelled", "This countermeasure is already cancelled"),
        ("photo", "open", None),
        ("photo", "done", None),
        ("photo", "cancelled", "This countermeasure was cancelled"),
    ])
    def test_the_table(self, operation, state, message):
        assert action_state_error(operation, state) == message

    def test_overdue_days(self):
        assert overdue_days("open", TODAY - timedelta(days=1), TODAY) == 1
        assert overdue_days("open", TODAY, TODAY) == 0
        assert overdue_days("open", TODAY + timedelta(days=3), TODAY) == 0
        assert overdue_days("done", TODAY - timedelta(days=4), TODAY) == 0
        assert overdue_days("cancelled", TODAY - timedelta(days=4), TODAY) == 0

    def test_counts(self):
        actions = [{"state": "open", "overdue_days": 2}, {"state": "open", "overdue_days": 0},
                   {"state": "done", "overdue_days": 0}, {"state": "cancelled", "overdue_days": 0}]
        assert action_counts(actions) == {"open": 2, "done": 1, "cancelled": 1, "overdue": 1}
        assert action_counts([]) == {"open": 0, "done": 0, "cancelled": 0, "overdue": 0}

    def test_the_bound_message(self):
        assert ACTIONS_FULL == "An improvement holds up to 30 countermeasures. Change an open one instead."


class TestActionFlags:

    @pytest.mark.parametrize("improvement_open", [True, False])
    @pytest.mark.parametrize("state", ["open", "done", "cancelled"])
    @pytest.mark.parametrize("may_edit", [True, False])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_every_combination(self, improvement_open, state, may_edit, is_owner):
        flags = action_flags(improvement_open, state, may_edit, is_owner)
        acts = may_edit or is_owner
        assert flags == {
            "can_change": improvement_open and state == "open" and may_edit,
            "can_mark_done": improvement_open and state == "open" and acts,
            "can_add_photo": improvement_open and state != "cancelled" and acts,
        }

    def test_the_owner_without_the_key(self):
        assert action_flags(True, "open", False, True) == {
            "can_change": False, "can_mark_done": True, "can_add_photo": True}
        assert action_flags(True, "done", False, True) == {
            "can_change": False, "can_mark_done": False, "can_add_photo": True}
