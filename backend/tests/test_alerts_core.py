"""alerts_core — audiences, what each ticket change enqueues, escalation, the texts and *What
you will get* (S021 § 5.1–5.3, § 8 Pure, § 10 A1)."""

from datetime import datetime

import pytest

from alerts_core import (
    ASSIGNED, ASSIGNED_ALERT, AUDIENCE, BREAKDOWN, DEFECT, ESCALATION, Alert, alert_text, display_name,
    escalation_minutes, excluded_people, message, raise_alert, regrade_alert, send_back_alert, should_escalate,
    should_send, message_for_test, ticket_facts, you_get,
)

MINUTES = {"A": 10, "B": 30, "C": 60}
TIME = datetime(2026, 10, 21, 14, 5)


def _facts(**overrides):
    ticket = {"id": 12, "serial": "TK-2026-10-012", "site_code": "SMTW", "unit_code": "MCC2", "machine_code": "VBM001",
              "machine_name": "Vibro mill", "component_code": None, "intensity": "critical", "state": "raised",
              "symptom": "Not building pressure", "description": "Pressure low since morning", "occurred_at": TIME}
    event = {"event": "raised", "occurred_at": TIME, "remark": None}
    for key in list(overrides):
        if key in event:
            event[key] = overrides.pop(key)
    ticket.update(overrides)
    return ticket_facts(ticket, event, "Ravi", "Priya", "https://vel-yantra.mspv.app")


class TestAudience:

    def test_by_exact_role(self):
        assert AUDIENCE[BREAKDOWN] == ("maint_engineer", "maint_supervisor", "maint_manager")
        assert AUDIENCE[DEFECT] == ("maint_engineer",)        # managers get no quiet defects (§ 9 Q4)
        assert AUDIENCE[ESCALATION] == ("maint_engineer", "maint_manager")
        assert "maint_technician" not in {role for roles in AUDIENCE.values() for role in roles}

    def test_left_out_people(self):
        assert excluded_people(BREAKDOWN, 3, 5) == [3, 5]
        assert excluded_people(DEFECT, 3, None) == [3]
        assert excluded_people(BREAKDOWN, None, None) == []
        assert excluded_people(ESCALATION, 3, 5) == []
        assert excluded_people(ASSIGNED, 3, 5) == [3]       # A1: the actor only


class TestWhatEnqueues:

    def test_raise(self):
        assert raise_alert("critical") == Alert(BREAKDOWN, True)
        assert raise_alert("degraded") == Alert(DEFECT, False)
        assert raise_alert("initial") == Alert(DEFECT, False)

    @pytest.mark.parametrize("state, escalate", [("raised", True), ("acknowledged", False), ("scheduled", False),
                                                 ("in_progress", False)])
    def test_regrade_to_critical(self, state, escalate):
        assert regrade_alert(state, "critical") == Alert(BREAKDOWN, escalate)

    def test_other_regrades_send_nothing(self):
        assert regrade_alert("raised", "degraded") is None
        assert regrade_alert("raised", "initial") is None

    def test_send_back(self):
        assert send_back_alert(True) == Alert(BREAKDOWN, False)
        assert send_back_alert(False) is None

    def test_assigned(self):
        assert ASSIGNED_ALERT == Alert(ASSIGNED, False)


class TestShouldSend:

    @pytest.mark.parametrize("kind", [BREAKDOWN, DEFECT])
    def test_breakdown_and_defect_while_the_machine_waits(self, kind):
        for state in ("raised", "acknowledged", "scheduled", "in_progress"):
            assert should_send(kind, state)
        for state in ("back_in_service", "closed"):
            assert not should_send(kind, state)

    @pytest.mark.parametrize("kind", [ESCALATION, ASSIGNED])
    def test_escalation_and_assigned_until_closed(self, kind):
        for state in ("raised", "acknowledged", "scheduled", "in_progress", "back_in_service"):
            assert should_send(kind, state)
        assert not should_send(kind, "closed")


class TestEscalation:

    def test_still_raised_critical_same_trigger(self):
        assert should_escalate("raised", "critical", 40, 40)

    @pytest.mark.parametrize("state", ["acknowledged", "scheduled", "in_progress", "back_in_service", "closed"])
    def test_acknowledged_in_any_way(self, state):
        assert not should_escalate(state, "critical", 40, 40)

    def test_regraded_down(self):
        assert not should_escalate("raised", "degraded", 40, 40)

    def test_a_later_trigger(self):
        assert not should_escalate("raised", "critical", 41, 40)

    def test_minutes_per_grade(self):
        assert escalation_minutes(None, "A", MINUTES) == 10
        assert escalation_minutes(None, "B", MINUTES) == 30
        assert escalation_minutes(None, "C", MINUTES) == 60

    def test_the_components_grade_wins_null_inherits(self):
        assert escalation_minutes("A", "C", MINUTES) == 10   # a safety door on a C press
        assert escalation_minutes(None, "B", MINUTES) == 30

    def test_an_ungraded_item_counts_as_c(self):
        assert escalation_minutes(None, None, MINUTES) == 60


class TestNames:

    def test_reported_by_first(self):
        assert display_name("Ravi Kumar", "Muthu S", "e2e_operator") == "Ravi"

    def test_then_the_raisers_team_name(self):
        assert display_name(None, "Muthu S", "e2e_operator") == "Muthu"

    def test_then_the_login(self):
        assert display_name(None, None, "kla") == "kla"
        assert display_name("  ", "", "kla") == "kla"


class TestTexts:

    def test_breakdown(self):
        assert alert_text(BREAKDOWN, _facts()) == (
            "Breakdown · SMTW.MCC2 · VBM001", "TK-2026-10-012 · Not building pressure — raised by Ravi")

    def test_description_when_no_symptom_cut_at_80(self):
        title, body = alert_text(DEFECT, _facts(symptom=None, description="x" * 120))
        assert title == "Defect · SMTW.MCC2 · VBM001"
        assert body == f"TK-2026-10-012 · {'x' * 80} — raised by Ravi"

    def test_neither_symptom_nor_description(self):
        _title, body = alert_text(BREAKDOWN, _facts(symptom=None, description=None))
        assert body == "TK-2026-10-012 — raised by Ravi"

    def test_down_again_gives_the_send_back_time(self):
        title, body = alert_text(BREAKDOWN, _facts(event="sent_back"))
        assert title == "Down again · SMTW.MCC2 · VBM001"
        assert body == "TK-2026-10-012 · Not building pressure — sent back at 14:05"

    def test_escalation_with_its_minutes(self):
        title, _body = alert_text(ESCALATION, _facts(), minutes=10)
        assert title == "Not acknowledged after 10 min · SMTW.MCC2 · VBM001"

    def test_assigned_names_the_assigner(self):
        assert alert_text(ASSIGNED, _facts(event="assigned")) == (
            "Assigned to you · SMTW.MCC2 · VBM001", "TK-2026-10-012 · Not building pressure — by Priya")

    def test_path_and_url(self):
        facts = _facts()
        assert facts["path"] == "/tickets/12"
        assert facts["url"] == "https://vel-yantra.mspv.app/tickets/12"

    def test_message_tag_and_quiet(self):
        assert message(DEFECT, _facts())["quiet"] is True
        loud = message(BREAKDOWN, _facts())
        assert loud["quiet"] is False and loud["tag"] == "ticket-12" and loud["path"] == "/tickets/12"
        assert message_for_test()["path"] == "/notifications"


def _membership(site, role, units="all"):
    return {"site_code": site, "role": role, "all_units": units == "all", "unit_codes": [] if units == "all" else units}


class TestYouGet:

    def test_engineer_all_units(self):
        assert you_get([_membership("SMTW", "maint_engineer")]) == [
            "Breakdowns and defects at SMTW, escalations", "Jobs assigned to you"]

    def test_supervisor_at_two_units(self):
        assert you_get([_membership("SMTW", "maint_supervisor", ["MCC2", "MCC1"])]) == [
            "Breakdowns at SMTW.MCC1, SMTW.MCC2"]

    def test_manager_at_two_sites(self):
        assert you_get([_membership("SMTW", "maint_manager"), _membership("BRICKS", "maint_manager")]) == [
            "Breakdowns at BRICKS, escalations", "Breakdowns at SMTW, escalations", "Jobs assigned to you"]

    def test_technician_gets_assigned_jobs(self):
        assert you_get([_membership("SMTW", "maint_technician")]) == ["Jobs assigned to you"]

    @pytest.mark.parametrize("role", ["maint_operator", "maint_storekeeper"])
    def test_nothing_for_other_roles(self, role):
        assert you_get([_membership("SMTW", role)]) == []

    def test_no_memberships_it_admin(self):
        assert you_get([]) == []

    def test_a_membership_without_units(self):
        assert you_get([_membership("SMTW", "maint_supervisor", [])]) == []
