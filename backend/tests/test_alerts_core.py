"""alerts_core — audiences, channels, what each ticket change enqueues, escalation, the texts and
*What you will get* (S021 § 5.1–5.3, § 8 Pure, § 10 A1; S032 *ticket closed*)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from contracts_core import ENDING_SOON_DAYS
from alerts_core import (
    ACTION_GIVEN, ACTION_OVERDUE, ASSIGNED, ASSIGNED_ALERT, AUDIENCE, BREAKDOWN, CHANNELS, CLOSED,
    CONTRACT_AUDIENCE_KEY,
    CONTRACT_ENDING, CONTRACT_KINDS, DEFECT, ESCALATION, FIRST, FIRST_REMINDER_DAYS, SECOND, SECOND_REMINDER_DAYS,
    IMPROVEMENT_KINDS, KINDS, TICKET_KINDS, VERIFY_READY, Alert, alert_text, close_alert, contract_facts,
    contract_message, contract_reminder_due, contract_text, display_name, should_send_contract,
    escalation_minutes, excluded_people, given_alert, improvement_facts, improvement_message, improvement_text,
    message, overdue_alert_due, raise_alert, ready_alert_due, regrade_alert, send_back_alert, should_escalate,
    should_send, should_send_improvement, message_for_test, ticket_facts, you_get,
    PM_JOB_DUE, PM_JOB_OVERDUE, PM_KINDS, due_point_alerted, pm_alert_due, pm_job_facts, pm_job_message,
    pm_job_text, pm_markers, should_send_pm,
)

OWNER_LINE = "Countermeasures given to you, and when they are overdue"
PM_LINE = "PM jobs assigned to you, when due and when overdue"   # S102
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
        assert KINDS == TICKET_KINDS + IMPROVEMENT_KINDS + CONTRACT_KINDS + PM_KINDS
        assert set(CHANNELS) == set(KINDS)
        for kind in IMPROVEMENT_KINDS:
            assert CHANNELS[kind] == ("push",)

    def test_the_contract_reminder_by_push_and_email(self):
        """S084 § 3: push to who reads the contract, email to who reads its price."""
        assert CONTRACT_KINDS == (CONTRACT_ENDING,)
        assert CHANNELS[CONTRACT_ENDING] == ("push", "email")
        assert CONTRACT_AUDIENCE_KEY == {"push": "contract:read", "email": "contract:read_senior"}

    def test_the_pm_kinds_push_only(self):
        """S102 § 3: both PM kinds by push only."""
        assert PM_KINDS == (PM_JOB_DUE, PM_JOB_OVERDUE)
        assert CHANNELS[PM_JOB_DUE] == CHANNELS[PM_JOB_OVERDUE] == ("push",)

    def test_the_reminder_days(self):
        """S084 § 5.1: the first reminder starts with S080's *Ends in N days* badge."""
        assert FIRST_REMINDER_DAYS == ENDING_SOON_DAYS == 60
        assert SECOND_REMINDER_DAYS == 15


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
            "Overdue PM jobs at SMTW", "Contracts ending for machines at SMTW", "Jobs assigned to you", PM_LINE,
            OWNER_LINE, LEAD_LINE]

    def test_supervisor_at_two_units(self):
        assert you_get([_membership("SMTW", "maint_supervisor", ["MCC2", "MCC1"])]) == [
            "Breakdowns at SMTW.MCC1, SMTW.MCC2", OWNER_LINE]

    def test_manager_at_two_sites(self):
        """S032: each manager membership adds its closed-ticket email line; S074: and its verify line."""
        assert you_get([_membership("SMTW", "maint_manager"), _membership("BRICKS", "maint_manager")]) == [
            "Breakdowns at BRICKS, escalations", "Improvements ready to verify at BRICKS",
            "Overdue PM jobs at BRICKS",
            "Contracts ending for machines at BRICKS", "Closed tickets at BRICKS, by email",
            "Contracts ending for machines at BRICKS, by email",
            "Breakdowns at SMTW, escalations", "Improvements ready to verify at SMTW", "Overdue PM jobs at SMTW",
            "Contracts ending for machines at SMTW",
            "Closed tickets at SMTW, by email", "Contracts ending for machines at SMTW, by email",
            "Jobs assigned to you", PM_LINE, OWNER_LINE, LEAD_LINE]

    def test_manager_at_one_unit(self):
        """S084 § 5.7: the contract lines name the site, not the unit."""
        assert you_get([_membership("SMTW", "maint_manager", ["MCC2"])]) == [
            "Breakdowns at SMTW.MCC2, escalations", "Improvements ready to verify at SMTW.MCC2",
            "Overdue PM jobs at SMTW.MCC2",
            "Contracts ending for machines at SMTW", "Closed tickets at SMTW.MCC2, by email",
            "Contracts ending for machines at SMTW, by email",
            "Jobs assigned to you", PM_LINE, OWNER_LINE, LEAD_LINE]

    def test_a_manager_without_units_gets_the_contract_lines(self):
        """S084 § 5.7, BR1-07: the reminders reach a site member whatever their units; no
        countermeasure lines come from a membership without units."""
        assert you_get([_membership("SMTW", "maint_manager", [])]) == [
            "Contracts ending for machines at SMTW", "Contracts ending for machines at SMTW, by email",
            "Jobs assigned to you"]

    def test_engineer_gets_no_email_line(self):
        assert not [line for line in you_get([_membership("SMTW", "maint_engineer")]) if "email" in line]

    def test_technician_gets_assigned_jobs(self):
        assert you_get([_membership("SMTW", "maint_technician")]) == ["Jobs assigned to you", PM_LINE, OWNER_LINE]

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
        assert should_send_improvement(ACTION_GIVEN, "actions_open", None, _action(owner_id=8),
                                       {"person_id": 7}) is False

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


# ---------------------------------------------------------------------------
# Contracts (S084 § 5.1, § 5.4, § 8.1)
# ---------------------------------------------------------------------------

C_TODAY = date(2027, 1, 30)
C_FROM = date(2026, 4, 1)
C_TO = date(2027, 3, 31)          # 60 days after C_TODAY
DAY = timedelta(days=1)


def _due(to_date=C_TO, first_for=None, second_for=None, active=True, renewed=False, from_date=C_FROM):
    return contract_reminder_due(active, renewed, from_date, to_date, first_for, second_for, C_TODAY)


class TestContractReminderDue:

    def test_60_days_never_sent(self):
        assert _due() == FIRST

    def test_61_days(self):
        assert _due(to_date=C_TO + DAY) is None

    def test_first_sent_for_this_date(self):
        assert _due(first_for=C_TO) is None

    def test_first_sent_for_an_older_date(self):
        assert _due(first_for=C_TO - timedelta(days=30)) == FIRST

    def test_15_days_nothing_sent(self):
        assert _due(to_date=C_TODAY + timedelta(days=15)) == SECOND

    def test_15_days_first_sent(self):
        to_date = C_TODAY + timedelta(days=15)
        assert _due(to_date=to_date, first_for=to_date) == SECOND

    def test_16_days_first_sent(self):
        to_date = C_TODAY + timedelta(days=16)
        assert _due(to_date=to_date, first_for=to_date) is None

    def test_ends_today_second_not_sent(self):
        assert _due(to_date=C_TODAY) == SECOND

    def test_ended_yesterday(self):
        assert _due(to_date=C_TODAY - DAY, from_date=C_TODAY - timedelta(days=100)) is None

    def test_not_started(self):
        assert _due(to_date=C_TODAY + timedelta(days=30), from_date=C_TODAY + DAY) is None

    def test_inactive(self):
        assert _due(active=False) is None

    def test_renewed(self):
        assert _due(renewed=True) is None

    def test_second_sent_for_this_date(self):
        to_date = C_TODAY + timedelta(days=10)
        assert _due(to_date=to_date, second_for=to_date) is None

    def test_second_sent_for_an_older_date(self):
        to_date = C_TODAY + timedelta(days=10)
        assert _due(to_date=to_date, second_for=to_date + timedelta(days=30)) == SECOND


class TestShouldSendContract:

    def _send(self, active=True, renewed=False, from_date=C_FROM, to_date=C_TO, expected=C_TO):
        return should_send_contract(active, renewed, from_date, to_date, expected, C_TODAY)

    def test_as_queued(self):
        assert self._send() is True

    def test_no_longer_true(self):
        assert self._send(active=False) is False
        assert self._send(renewed=True) is False
        assert self._send(from_date=C_TODAY + DAY, to_date=C_TO) is False
        assert self._send(to_date=C_TO + timedelta(days=30)) is False
        assert self._send(to_date=C_TODAY - DAY, expected=C_TODAY - DAY) is False

    def test_ends_today(self):
        assert self._send(to_date=C_TODAY, expected=C_TODAY) is True


def _contract(**overrides):
    contract = {"id": 12, "title": "Atlas Copco AMC 2026–27", "contract_number": "TEST/AMC/0001",
                "contract_type": "amc", "vendor_name": "Atlas Copco", "site_codes": ["SMTW"], "from_date": C_FROM,
                "to_date": C_TO}
    contract.update(overrides)
    return contract


def _contract_facts(today=C_TODAY, **overrides):
    return contract_facts(_contract(**overrides), today, "https://vel-yantra.mspv.app")


class TestContractTexts:

    def test_60_days(self):
        assert contract_text(_contract_facts()) == (
            "Contract ends in 60 days · SMTW",
            "Atlas Copco AMC 2026–27 · Atlas Copco — ends on 31-03-2027. Renew it, or let it end.")

    def test_ends_today(self):
        assert contract_text(_contract_facts(today=C_TO))[0] == "Contract ends today · SMTW"

    def test_one_day(self):
        assert contract_text(_contract_facts(today=C_TO - DAY))[0] == "Contract ends in 1 day · SMTW"

    def test_the_title_names_the_machine_sites(self):
        """S087 § 5.6: the sites of the contract's machines, by code; none with no machine."""
        assert contract_text(_contract_facts(site_codes=["BRICKS", "SMTW"]))[0] == (
            "Contract ends in 60 days · BRICKS, SMTW")
        assert contract_text(_contract_facts(site_codes=[]))[0] == "Contract ends in 60 days"

    def test_the_title_cut_at_80(self):
        assert _contract_facts(title="x" * 100)["title"] == "x" * 80

    def test_the_type_word(self):
        assert _contract_facts()["type_word"] == "AMC"
        assert _contract_facts(contract_type="on_call")["type_word"] == "On call"

    def test_message_path_tag_and_quiet(self):
        assert contract_message(_contract_facts()) == {
            "title": "Contract ends in 60 days · SMTW",
            "body": "Atlas Copco AMC 2026–27 · Atlas Copco — ends on 31-03-2027. Renew it, or let it end.",
            "path": "/contracts/12", "tag": "contract-12", "quiet": True}

    def test_the_url(self):
        assert _contract_facts()["url"] == "https://vel-yantra.mspv.app/contracts/12"

    def test_no_callout_number_or_cost_note(self):
        """D8: even a row that holds them gives facts without them."""
        facts = _contract_facts(callout_number="1800-000", cost_note="9809")
        assert "callout_number" not in facts and "cost_note" not in facts


# ---------------------------------------------------------------------------
# PM jobs (S102 § 5.1, § 5.6, § 8.1)
# ---------------------------------------------------------------------------

PM_DUE_ON = date(2026, 11, 20)    # a monthly job, grace 3: on time until 23-11-2026, overdue from the 24th


def _pm_job(**overrides):
    job = {"id": 12, "state": "due", "due_on": PM_DUE_ON, "due_meter": None, "due_alert_on": None,
           "due_alert_meter": None, "overdue_alert_on": None, "overdue_alert_meter": None}
    job.update(overrides)
    return job


def _pm_row(**overrides):
    row = {**_pm_job(), "serial": "PM-2026-11-004", "pl_title": "Monthly press check", "pl_active": 1,
           "e_lifecycle": "in_service", "site_code": "SMTW", "unit_code": "MCC2", "e_code": "HP003", "t_unit": None,
           "grace_days": 3, "meter_window": None, "a_name": "Ravi Kumar"}
    row.update(overrides)
    return row


def _pm_facts(**overrides):
    return pm_job_facts(_pm_row(**overrides), "https://vel-yantra.mspv.app")


class TestDuePointAlerted:

    def test_never_sent(self):
        assert not due_point_alerted(None, None, PM_DUE_ON, None)

    def test_the_same_date(self):
        assert due_point_alerted(PM_DUE_ON, None, PM_DUE_ON, None)

    def test_the_same_date_another_meter(self):
        assert not due_point_alerted(PM_DUE_ON, Decimal("1500"), PM_DUE_ON, Decimal("1600"))

    def test_decimals_compare_by_value(self):
        assert due_point_alerted(None, Decimal("1500.000"), None, Decimal("1500"))

    def test_a_moved_date(self):
        assert not due_point_alerted(PM_DUE_ON, None, PM_DUE_ON + timedelta(days=7), None)


class TestPmAlertDue:

    def test_due_never_sent(self):
        assert pm_alert_due(_pm_job(), "due", True, False) == PM_JOB_DUE

    def test_due_sent_for_this_point(self):
        assert pm_alert_due(_pm_job(due_alert_on=PM_DUE_ON), "due", True, False) is None

    def test_due_sent_for_an_older_date(self):
        job = _pm_job(due_alert_on=PM_DUE_ON - timedelta(days=30))
        assert pm_alert_due(job, "due", True, False) == PM_JOB_DUE

    def test_overdue_nothing_sent(self):
        assert pm_alert_due(_pm_job(), "overdue", True, False) == PM_JOB_OVERDUE

    def test_overdue_after_due(self):
        assert pm_alert_due(_pm_job(due_alert_on=PM_DUE_ON), "overdue", True, False) == PM_JOB_OVERDUE

    def test_overdue_sent(self):
        job = _pm_job(due_alert_on=PM_DUE_ON, overdue_alert_on=PM_DUE_ON)
        assert pm_alert_due(job, "overdue", True, False) is None

    @pytest.mark.parametrize("standing", ["upcoming", "not_yet"])
    def test_not_yet_due(self, standing):
        assert pm_alert_due(_pm_job(), standing, True, False) is None

    @pytest.mark.parametrize("state", ["in_progress", "done", "verified", "skipped", "cancelled"])
    def test_not_a_due_job(self, state):
        assert pm_alert_due(_pm_job(state=state), "overdue", True, False) is None

    def test_plan_inactive(self):
        assert pm_alert_due(_pm_job(), "overdue", False, False) is None

    def test_node_scrapped(self):
        assert pm_alert_due(_pm_job(), "due", True, True) is None

    def test_the_markers(self):
        """§ 5.4 step 6: *overdue* marks both, so a standing that falls back sends no late *due*."""
        job = _pm_job(due_meter=Decimal("1500"))
        assert pm_markers(PM_JOB_DUE, job) == {"due_alert_on": PM_DUE_ON, "due_alert_meter": Decimal("1500")}
        assert pm_markers(PM_JOB_OVERDUE, job) == {
            "due_alert_on": PM_DUE_ON, "due_alert_meter": Decimal("1500"),
            "overdue_alert_on": PM_DUE_ON, "overdue_alert_meter": Decimal("1500")}


class TestShouldSendPm:

    def test_as_queued(self):
        assert should_send_pm(PM_JOB_DUE, _pm_row(due_alert_on=PM_DUE_ON))
        assert should_send_pm(PM_JOB_OVERDUE, _pm_row(due_alert_on=PM_DUE_ON, overdue_alert_on=PM_DUE_ON))

    def test_started(self):
        assert not should_send_pm(PM_JOB_DUE, _pm_row(state="in_progress", due_alert_on=PM_DUE_ON))

    def test_plan_inactive(self):
        assert not should_send_pm(PM_JOB_DUE, _pm_row(pl_active=0, due_alert_on=PM_DUE_ON))

    def test_node_scrapped(self):
        assert not should_send_pm(PM_JOB_DUE, _pm_row(e_lifecycle="scrapped", due_alert_on=PM_DUE_ON))

    def test_due_point_moved_since(self):
        row = _pm_row(due_on=PM_DUE_ON + timedelta(days=7), due_alert_on=PM_DUE_ON)
        assert not should_send_pm(PM_JOB_DUE, row)


class TestPmTexts:

    def test_due(self):
        assert pm_job_text(PM_JOB_DUE, _pm_facts()) == (
            "PM job due · SMTW.MCC2 · HP003",
            "PM-2026-11-004 · Monthly press check — due on 20-11-2026, on time until 23-11-2026.")

    def test_overdue(self):
        assert pm_job_text(PM_JOB_OVERDUE, _pm_facts()) == (
            "PM job overdue · SMTW.MCC2 · HP003",
            "PM-2026-11-004 · Monthly press check — was due on 20-11-2026, assigned to Ravi.")

    def test_a_meter_job(self):
        facts = _pm_facts(due_on=None, grace_days=None, due_meter=Decimal("1500.000"), meter_window=Decimal("150"),
                          t_unit="h")
        assert pm_job_text(PM_JOB_DUE, facts)[1] == (
            "PM-2026-11-004 · Monthly press check — due at 1500 h, on time until 1650 h.")
        assert pm_job_text(PM_JOB_OVERDUE, facts)[1] == (
            "PM-2026-11-004 · Monthly press check — was due at 1500 h, assigned to Ravi.")

    def test_a_both_job(self):
        facts = _pm_facts(due_meter=Decimal("1500"), meter_window=Decimal("150"), t_unit="h")
        assert pm_job_text(PM_JOB_DUE, facts)[1] == (
            "PM-2026-11-004 · Monthly press check — due on 20-11-2026 or at 1500 h,"
            " on time until 23-11-2026 or 1650 h.")

    def test_a_both_job_with_no_reading_reads_as_a_date_job(self):
        """BR1-06: the values decide, not the plan's kind."""
        facts = _pm_facts(due_meter=None, meter_window=Decimal("150"), t_unit="h")
        assert pm_job_text(PM_JOB_DUE, facts)[1] == (
            "PM-2026-11-004 · Monthly press check — due on 20-11-2026, on time until 23-11-2026.")

    def test_overdue_not_assigned(self):
        assert pm_job_text(PM_JOB_OVERDUE, _pm_facts(a_name=None))[1] == (
            "PM-2026-11-004 · Monthly press check — was due on 20-11-2026, not assigned.")

    def test_the_title_cut_at_80(self):
        assert _pm_facts(pl_title="x" * 100)["title"] == "x" * 80

    @pytest.mark.parametrize("kind", [PM_JOB_DUE, PM_JOB_OVERDUE])
    def test_message_one_tag_per_job_quiet(self, kind):
        """BR1-09: one tag for both kinds, so *overdue* replaces *due* on the phone."""
        sent = pm_job_message(kind, _pm_facts())
        assert sent["path"] == "/pm/jobs/12" and sent["tag"] == "pm-job-12" and sent["quiet"] is True
        assert _pm_facts()["url"] == "https://vel-yantra.mspv.app/pm/jobs/12"
