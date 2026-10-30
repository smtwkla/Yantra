"""alerts_core — audiences, channels, what each ticket change enqueues, escalation, the texts and
*What you will get* (S021 § 5.1–5.3, § 8 Pure, § 10 A1; S032 *ticket closed*)."""

from datetime import date, datetime, timedelta

import pytest

from alerts_core import (
    ACTION_GIVEN, ACTION_OVERDUE, ASSIGNED, ASSIGNED_ALERT, AUDIENCE, BREAKDOWN, CHANNELS, CLOSED, DEFECT, ESCALATION,
    IMPROVEMENT_KINDS, KINDS, TICKET_KINDS, VERIFY_READY, Alert, alert_text, close_alert, display_name,
    escalation_minutes, excluded_people, given_alert, improvement_facts, improvement_message, improvement_text,
    message, overdue_alert_due, raise_alert, ready_alert_due, regrade_alert, send_back_alert, should_escalate,
    should_send, should_send_improvement, message_for_test, ticket_facts, you_get,
)

OWNER_LINE = "Countermeasures given to you, and when they are overdue"
LEAD_LINE = "Overdue countermeasures of improvements you lead"

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
        assert excluded_people(CLOSED, 3, 5) == [3]         # S032: the closer only, never the reporter
        assert excluded_people(CLOSED, None, None) == []

    def test_closed_goes_to_managers_only(self):
        assert AUDIENCE[CLOSED] == ("maint_manager",)


class TestChannels:

    def test_closed_by_email_the_others_by_push(self):
        assert CHANNELS[CLOSED] == ("email",)
        for kind in (BREAKDOWN, DEFECT, ESCALATION, ASSIGNED):
            assert CHANNELS[kind] == ("push",)

    def test_every_kind_has_channels_and_the_improvement_kinds_are_push_only(self):
        assert KINDS == TICKET_KINDS + IMPROVEMENT_KINDS
        assert set(CHANNELS) == set(KINDS)
        for kind in IMPROVEMENT_KINDS:
            assert CHANNELS[kind] == ("push",)


class TestWhatEnqueues:

    def test_raise(self):
        assert raise_alert("critical", timedelta(0)) == Alert(BREAKDOWN, True)
        assert raise_alert("degraded", timedelta(0)) == Alert(DEFECT, False)
        assert raise_alert("initial", timedelta(0)) == Alert(DEFECT, False)

    def test_raise_for_history_sends_nothing(self):
        """S028 § 4.6: more than 7 days back is history; exactly 7 days still alerts."""
        assert raise_alert("critical", timedelta(days=7)) == Alert(BREAKDOWN, True)
        assert raise_alert("critical", timedelta(days=7, minutes=1)) is None
        assert raise_alert("degraded", timedelta(days=8)) is None

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

    def test_close_within_7_days(self):
        assert close_alert(timedelta(0)) == Alert(CLOSED, False)
        assert close_alert(timedelta(days=7)) == Alert(CLOSED, False)

    def test_close_of_history_sends_nothing(self):
        """S032 § 1.3: back-entered history (S028), as for the raise."""
        assert close_alert(timedelta(days=7, minutes=1)) is None
        assert close_alert(timedelta(days=8)) is None


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

    def test_closed_only_while_still_closed(self):
        assert should_send(CLOSED, "closed")
        for state in ("raised", "in_progress", "back_in_service"):
            assert not should_send(CLOSED, state)


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
            "Breakdowns and defects at SMTW, escalations", "Improvements ready to verify at SMTW",
            "Jobs assigned to you", OWNER_LINE, LEAD_LINE]

    def test_supervisor_at_two_units(self):
        assert you_get([_membership("SMTW", "maint_supervisor", ["MCC2", "MCC1"])]) == [
            "Breakdowns at SMTW.MCC1, SMTW.MCC2", OWNER_LINE]

    def test_manager_at_two_sites(self):
        """S032: each manager membership adds its closed-ticket email line; S074: and its verify line."""
        assert you_get([_membership("SMTW", "maint_manager"), _membership("BRICKS", "maint_manager")]) == [
            "Breakdowns at BRICKS, escalations", "Improvements ready to verify at BRICKS",
            "Closed tickets at BRICKS, by email",
            "Breakdowns at SMTW, escalations", "Improvements ready to verify at SMTW", "Closed tickets at SMTW, by email",
            "Jobs assigned to you", OWNER_LINE, LEAD_LINE]

    def test_manager_at_one_unit(self):
        assert you_get([_membership("SMTW", "maint_manager", ["MCC2"])]) == [
            "Breakdowns at SMTW.MCC2, escalations", "Improvements ready to verify at SMTW.MCC2",
            "Closed tickets at SMTW.MCC2, by email", "Jobs assigned to you", OWNER_LINE, LEAD_LINE]

    def test_engineer_gets_no_email_line(self):
        assert not [line for line in you_get([_membership("SMTW", "maint_engineer")]) if "email" in line]

    def test_technician_gets_assigned_jobs(self):
        assert you_get([_membership("SMTW", "maint_technician")]) == ["Jobs assigned to you", OWNER_LINE]

    def test_operator_gets_the_countermeasure_line(self):
        """S074: an operator can own a countermeasure (S070 D3), so the dot now shows for them."""
        assert you_get([_membership("SMTW", "maint_operator")]) == [OWNER_LINE]

    def test_nothing_for_other_roles(self):
        assert you_get([_membership("SMTW", "maint_storekeeper")]) == []

    def test_no_memberships_it_admin(self):
        assert you_get([]) == []

    def test_a_membership_without_units(self):
        assert you_get([_membership("SMTW", "maint_supervisor", [])]) == []


# ---------------------------------------------------------------------------
# Improvements (S074 § 5, § 8.1)
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 9)
DUE = date(2026, 11, 8)
WATCH_FROM = datetime(2026, 11, 20, 15, 30)
WATCH_END = datetime(2027, 2, 18, 15, 30)    # 90 days later
MINUTE = timedelta(minutes=1)


class TestGivenAlert:

    def test_to_another_person(self):
        assert given_alert(7, 3) is True

    def test_given_to_themselves(self):
        assert given_alert(7, 7) is False

    def test_an_actor_without_a_team_record(self):
        assert given_alert(7, None) is True

    def test_a_change_to_the_same_owner(self):
        assert given_alert(7, 3, old_owner_id=7) is False

    def test_a_change_to_another_owner(self):
        assert given_alert(8, 3, old_owner_id=7) is True


class TestOverdueAlertDue:

    def test_due_yesterday_open_never_alerted(self):
        assert overdue_alert_due("open", DUE, None, "actions_open", TODAY) is True

    def test_due_today(self):
        assert overdue_alert_due("open", TODAY, None, "actions_open", TODAY) is False

    @pytest.mark.parametrize("state", ["done", "cancelled"])
    def test_done_or_cancelled(self, state):
        assert overdue_alert_due(state, DUE, None, "actions_open", TODAY) is False

    @pytest.mark.parametrize("state", ["closed_effective", "closed_not_effective", "dropped"])
    def test_the_improvement_closed_or_dropped(self, state):
        assert overdue_alert_due("open", DUE, None, state, TODAY) is False

    @pytest.mark.parametrize("state", ["analysing", "actions_open", "watching"])
    def test_every_open_state(self, state):
        assert overdue_alert_due("open", DUE, None, state, TODAY) is True

    def test_alerted_for_this_due_date(self):
        assert overdue_alert_due("open", DUE, DUE, "actions_open", TODAY) is False

    def test_moved_later_and_passed_again(self):
        assert overdue_alert_due("open", DUE, DUE - timedelta(days=5), "actions_open", TODAY) is True

    def test_moved_earlier_still_past(self):
        """BR1-01: once per due date, either way."""
        assert overdue_alert_due("open", DUE - timedelta(days=3), DUE, "actions_open", TODAY) is True


class TestReadyAlertDue:

    def test_a_minute_before_the_end(self):
        assert ready_alert_due("watching", WATCH_FROM, 90, None, WATCH_END - MINUTE) is False

    def test_at_the_end(self):
        assert ready_alert_due("watching", WATCH_FROM, 90, None, WATCH_END) is True

    def test_alerted_for_this_end(self):
        assert ready_alert_due("watching", WATCH_FROM, 90, WATCH_END, WATCH_END + MINUTE) is False

    def test_extended_and_passed(self):
        assert ready_alert_due("watching", WATCH_FROM, 120, WATCH_END,
                               WATCH_FROM + timedelta(days=120)) is True

    def test_cut_and_passed(self):
        """BR1-01: a watch end moved earlier alerts again at its new end."""
        assert ready_alert_due("watching", WATCH_FROM, 60, WATCH_END, WATCH_END) is True

    def test_actions_open_with_an_old_watch_from(self):
        assert ready_alert_due("actions_open", WATCH_FROM, 90, None, WATCH_END) is False

    @pytest.mark.parametrize("state", ["closed_effective", "closed_not_effective", "dropped"])
    def test_a_closed_state(self, state):
        assert ready_alert_due(state, WATCH_FROM, 90, None, WATCH_END) is False

    def test_no_watch_yet(self):
        assert ready_alert_due("watching", None, 90, None, WATCH_END) is False


def _action(**overrides):
    return {"id": 5, "state": "open", "owner_id": 7, "due_date": DUE, "text": "Clean the panel contactors",
            "owner_name": "Kannan Selvam", **overrides}


class TestShouldSendImprovement:
    """§ 5.3's change table: the record as it is when the task runs decides."""

    def test_given_still_true(self):
        assert should_send_improvement(ACTION_GIVEN, "actions_open", None, _action(), {"person_id": 7}) is True

    def test_given_owner_changed_again(self):
        assert should_send_improvement(ACTION_GIVEN, "actions_open", None, _action(owner_id=8), {"person_id": 7}) is False

    @pytest.mark.parametrize("kind", [ACTION_GIVEN, ACTION_OVERDUE])
    @pytest.mark.parametrize("state", ["done", "cancelled"])
    def test_countermeasure_done_or_cancelled(self, kind, state):
        expected = {"person_id": 7, "due_date": DUE}
        assert should_send_improvement(kind, "actions_open", None, _action(state=state), expected) is False

    @pytest.mark.parametrize("kind", [ACTION_GIVEN, ACTION_OVERDUE])
    @pytest.mark.parametrize("state", ["closed_effective", "dropped"])
    def test_improvement_closed_or_dropped(self, kind, state):
        expected = {"person_id": 7, "due_date": DUE}
        assert should_send_improvement(kind, state, None, _action(), expected) is False

    def test_overdue_still_true(self):
        assert should_send_improvement(ACTION_OVERDUE, "watching", None, _action(), {"due_date": DUE}) is True

    def test_overdue_due_date_moved(self):
        assert should_send_improvement(ACTION_OVERDUE, "actions_open", None, _action(due_date=TODAY),
                                       {"due_date": DUE}) is False

    def test_ready_still_true(self):
        assert should_send_improvement(VERIFY_READY, "watching", WATCH_END, None, {"watch_until": WATCH_END}) is True

    def test_ready_watch_extended_or_restarted(self):
        assert should_send_improvement(VERIFY_READY, "watching", WATCH_END + timedelta(days=10), None,
                                       {"watch_until": WATCH_END}) is False

    @pytest.mark.parametrize("state", ["actions_open", "closed_effective", "dropped"])
    def test_ready_no_longer_watching(self, state):
        assert should_send_improvement(VERIFY_READY, state, WATCH_END, None, {"watch_until": WATCH_END}) is False


def _improvement(**overrides):
    return {"id": 12, "serial": "IM-2026-10-001", "title": "Press does not start", "site_code": "SMTW",
            "unit_code": "MCC2", "machine_code": "HP003", "watch_from": WATCH_FROM, "watch_days": 90, **overrides}


def _improvement_facts(action=None, giver="Ravi", **overrides):
    return improvement_facts(_improvement(**overrides), action, giver, "https://vel-yantra.mspv.app")


class TestImprovementTexts:

    def test_given(self):
        assert improvement_text(ACTION_GIVEN, _improvement_facts(_action())) == (
            "Countermeasure for you · SMTW.MCC2 · HP003",
            "IM-2026-10-001 · Clean the panel contactors — due 08-11-2026, from Ravi")

    def test_given_without_a_giver_name(self):
        assert improvement_text(ACTION_GIVEN, _improvement_facts(_action(), giver=None))[1] == (
            "IM-2026-10-001 · Clean the panel contactors — due 08-11-2026")

    def test_overdue_names_the_owner(self):
        assert improvement_text(ACTION_OVERDUE, _improvement_facts(_action())) == (
            "Countermeasure overdue · SMTW.MCC2 · HP003",
            "IM-2026-10-001 · Clean the panel contactors — was due 08-11-2026, owner Kannan")

    def test_ready(self):
        assert improvement_text(VERIFY_READY, _improvement_facts()) == (
            "Ready to verify · SMTW.MCC2 · HP003",
            "IM-2026-10-001 · Press does not start — the watch ended on 18-02-2027. Check if the fix worked.")

    def test_the_action_text_and_the_title_cut_at_80(self):
        facts = _improvement_facts(_action(text="x" * 120), title="y" * 120)
        assert facts["action_text"] == "x" * 80 and facts["title"] == "y" * 80

    def test_path_and_url(self):
        facts = _improvement_facts()
        assert facts["path"] == "/tickets/improvements/12"
        assert facts["url"] == "https://vel-yantra.mspv.app/tickets/improvements/12"

    def test_message_path_tags_and_quiet(self):
        given = improvement_message(ACTION_GIVEN, _improvement_facts(_action()))
        overdue = improvement_message(ACTION_OVERDUE, _improvement_facts(_action()))
        ready = improvement_message(VERIFY_READY, _improvement_facts())
        assert given["path"] == overdue["path"] == ready["path"] == "/tickets/improvements/12"
        assert given["tag"] == overdue["tag"] == "improvement-action-5"
        assert ready["tag"] == "improvement-12"
        assert given["quiet"] is overdue["quiet"] is ready["quiet"] is True
