"""Improvements — pure rules (S067 § 8.2; no DB)."""

import pytest

from config_rbac import SITE_ROLES
from improvements_core import (
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
