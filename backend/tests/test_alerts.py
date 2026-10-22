"""Alerts end to end, short of the push service (S021 § 5.1–5.3, § 8 API and tasks, § 10 A1): what
each ticket change enqueues, the fan-out to the right people's devices, the escalation check, the
send outcomes with a fake sender, and the sender's call to pywebpush.

The recipients are real people, memberships and person_units rows: the harness's site role is a
wildcard in g.user, not a row (BR2-10).  The handlers run here on a connection of their own, in a
transaction as the worker runs them; the worker itself runs only where its retry rules are the
point.
"""

import hashlib
import json
import uuid
from datetime import timedelta

import pytest
import requests
from pywebpush import WebPushException

import config
import push_sender
import task_handlers
from db_helpers import transaction
from local_db import get_local_db
from task_handlers import NoRetry, RetryLater, push_send, ticket_alert, ticket_escalate
from tests.conftest import TICKETS
from worker import Worker

TEST_LOCK = "yantra_worker_test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(handler, payload, **kwargs):
    """Run a handler as the worker does: one transaction on its own connection."""
    conn = get_local_db(config.DB_CONFIG)
    try:
        with transaction(conn):
            handler(conn, payload, lambda: False, **kwargs)
    finally:
        conn.close()


def tasks(db_rows, task_type, ticket_id):
    rows = db_rows("SELECT id, payload, scheduled_for, created_at, max_attempts FROM task_queue"
                   " WHERE task_type = %s AND JSON_EXTRACT(payload, '$.ticket_id') = %s ORDER BY id",
                   (task_type, ticket_id))
    return [{**row, "payload": json.loads(row["payload"])} for row in rows]


def sends(db_rows, ticket_id):
    """The push_send tasks of one ticket's alerts -> their payloads, by subscription id."""
    rows = db_rows("SELECT payload FROM task_queue WHERE task_type = 'push_send'"
                   " AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.path')) = %s ORDER BY id", (f"/tickets/{ticket_id}",))
    return [json.loads(row["payload"]) for row in rows]


def event_id(ticket_detail, event):
    return [e["id"] for e in ticket_detail["events"] if e["event"] == event][-1]


@pytest.fixture
def add_device(db_rows):
    """add_device(person) -> the id of a new push_subscriptions row for the person."""
    def add(person):
        endpoint = f"https://fcm.googleapis.com/fcm/send/test-{uuid.uuid4().hex}"
        digest = hashlib.sha256(endpoint.encode()).hexdigest()
        db_rows("INSERT INTO push_subscriptions (person_id, endpoint, endpoint_hash, p256dh, auth, label)"
                " VALUES (%s, %s, %s, 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQ', 'tBHItJI5svbpez7KI4CCXg',"
                " 'Android · Chrome')", (person["id"], endpoint, digest))
        return db_rows("SELECT id FROM push_subscriptions WHERE endpoint_hash = %s", (digest,))[0]["id"]
    return add


@pytest.fixture
def plant(make_site, make_unit, make_equipment, user_at_sites, add_device, db_rows):
    """A site with a unit (the machine's) and a second unit; people around it, each with one
    device: who should and who should not get the unit's alerts."""
    site, other_site = make_site(), make_site()
    unit, other_unit = make_unit(site=site), make_unit(site=site)
    machine = make_equipment(unit=unit, criticality="C")
    people = {}
    for key, spec in {
        "operator": [(site, "maint_operator", [unit])],
        "engineer": [(site, "maint_engineer", "all")],
        "supervisor": [(site, "maint_supervisor", [unit])],
        "supervisor_elsewhere": [(site, "maint_supervisor", [other_unit])],
        "manager": [(site, "maint_manager", "all")],
        "technician": [(site, "maint_technician", "all")],
        "engineer_other_site": [(other_site, "maint_engineer", "all")],
        "engineer_inactive": [(site, "maint_engineer", "all")],
    }.items():
        client, person = user_at_sites(spec)
        people[key] = {"client": client, "person": person, "device": add_device(person)}
    db_rows("UPDATE people SET active = 0 WHERE id = %s", (people["engineer_inactive"]["person"]["id"],))
    return {"site": site, "unit": unit, "machine": machine, "people": people}


def raise_on(plant, node=None, **body):
    """A ticket raised by the plant's operator (default critical) -> its detail."""
    client = plant["people"]["operator"]["client"]
    res = client.post(TICKETS, json={"equipment_id": (node or plant["machine"])["id"], "intensity": "critical",
                                     "description": "Stopped", **body})
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def devices_of(plant, *keys):
    return sorted(plant["people"][key]["device"] for key in keys)


def person_id(plant, key):
    return plant["people"][key]["person"]["id"]


def restore(plant, ticket):
    res = plant["people"]["operator"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/restore",
                                                     json={"person_id": person_id(plant, "operator")})
    assert res.status_code == 200, res.get_json()
    return res.get_json()


# ---------------------------------------------------------------------------
# What a ticket change enqueues (§ 5.3)
# ---------------------------------------------------------------------------

class TestRaise:

    def test_a_breakdown_alerts_and_escalates_at_the_grades_minutes(self, plant, db_rows):
        ticket = raise_on(plant)
        raised = event_id(ticket, "raised")
        (alert,) = tasks(db_rows, "ticket_alert", ticket["id"])
        assert alert["payload"] == {"ticket_id": ticket["id"], "kind": "breakdown", "event_id": raised,
                                    "exclude_person_ids": [person_id(plant, "operator")]}
        (escalate,) = tasks(db_rows, "ticket_escalate", ticket["id"])
        assert escalate["payload"] == {"ticket_id": ticket["id"], "trigger_event_id": raised, "minutes": 60}
        delay = escalate["scheduled_for"] - escalate["created_at"]
        assert timedelta(minutes=59) <= delay <= timedelta(minutes=61)

    def test_the_components_own_grade_wins(self, plant, make_equipment, db_rows):
        door = make_equipment(parent=plant["machine"], criticality="A")   # a safety door on a C press
        ticket = raise_on(plant, node=door)
        (escalate,) = tasks(db_rows, "ticket_escalate", ticket["id"])
        assert escalate["payload"]["minutes"] == 10

    def test_a_changed_setting_applies_to_new_breakdowns(self, plant, admin, db_rows):
        try:
            assert admin.put("/api/settings/notifications",
                             json={"escalate_minutes": {"A": 10, "B": 30, "C": 45}}).status_code == 200
            ticket = raise_on(plant)
            assert tasks(db_rows, "ticket_escalate", ticket["id"])[0]["payload"]["minutes"] == 45
        finally:
            admin.put("/api/settings/notifications", json={"escalate_minutes": {"A": 10, "B": 30, "C": 60}})

    def test_the_reported_by_person_is_left_out_too(self, plant, db_rows):
        ticket = raise_on(plant, reported_by_id=person_id(plant, "supervisor"))
        (alert,) = tasks(db_rows, "ticket_alert", ticket["id"])
        assert alert["payload"]["exclude_person_ids"] == sorted([person_id(plant, "operator"),
                                                                 person_id(plant, "supervisor")])

    @pytest.mark.parametrize("intensity", ["degraded", "initial"])
    def test_a_defect_alerts_only(self, plant, db_rows, intensity):
        ticket = raise_on(plant, intensity=intensity)
        (alert,) = tasks(db_rows, "ticket_alert", ticket["id"])
        assert alert["payload"]["kind"] == "defect"
        assert tasks(db_rows, "ticket_escalate", ticket["id"]) == []

    def test_already_fixed_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant, restore={"person_id": person_id(plant, "operator")})
        assert ticket["state"] == "back_in_service"
        assert tasks(db_rows, "ticket_alert", ticket["id"]) == []
        assert tasks(db_rows, "ticket_escalate", ticket["id"]) == []

    def test_a_refused_raise_leaves_no_task(self, plant, db_rows):
        before = db_rows("SELECT COUNT(*) AS n FROM task_queue")[0]["n"]
        res = plant["people"]["operator"]["client"].post(TICKETS, json={
            "equipment_id": plant["machine"]["id"], "intensity": "critical", "description": "Stopped",
            "restore": {"person_id": 999_999}})
        assert res.status_code == 400
        assert db_rows("SELECT COUNT(*) AS n FROM task_queue")[0]["n"] == before


class TestRegrade:

    def _regrade(self, plant, ticket, key="operator", **body):
        res = plant["people"][key]["client"].post(f"{TICKETS}/{ticket['id']}/regrade", json=body)
        assert res.status_code == 200, res.get_json()
        return res.get_json()

    def test_to_critical_while_raised_alerts_and_escalates(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        regraded = self._regrade(plant, ticket, intensity="critical")
        alerts = tasks(db_rows, "ticket_alert", ticket["id"])
        assert [a["payload"]["kind"] for a in alerts] == ["defect", "breakdown"]
        assert alerts[1]["payload"]["event_id"] == event_id(regraded, "regraded")
        (escalate,) = tasks(db_rows, "ticket_escalate", ticket["id"])
        assert escalate["payload"]["trigger_event_id"] == event_id(regraded, "regraded")

    def test_to_critical_while_in_progress_alerts_only(self, plant, db_rows, set_ticket_state):
        ticket = raise_on(plant, intensity="degraded")
        set_ticket_state(ticket, "in_progress")
        self._regrade(plant, ticket, intensity="critical")
        assert [a["payload"]["kind"] for a in tasks(db_rows, "ticket_alert", ticket["id"])] == ["defect", "breakdown"]
        assert tasks(db_rows, "ticket_escalate", ticket["id"]) == []

    def test_lowering_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant)
        self._regrade(plant, ticket, key="engineer", intensity="degraded", remark="Runs slowly")
        assert len(tasks(db_rows, "ticket_alert", ticket["id"])) == 1   # the raise's only


class TestSendBack:

    @pytest.mark.parametrize("intensity", ["critical", "degraded"])
    def test_machine_down_again_alerts_without_escalation(self, plant, db_rows, intensity):
        """Tested on a critical ticket (its sent_back event carries no intensity) and a degraded
        one (its event carries critical): the move's answer decides (BR2-01)."""
        ticket = raise_on(plant, intensity=intensity)
        restore(plant, ticket)
        res = plant["people"]["engineer"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/send-back",
                                                         json={"machine_down": True, "remark": "Still leaking"})
        assert res.status_code == 200, res.get_json()
        alerts = tasks(db_rows, "ticket_alert", ticket["id"])
        assert alerts[-1]["payload"] == {"ticket_id": ticket["id"], "kind": "breakdown",
                                         "event_id": event_id(res.get_json(), "sent_back"),
                                         "exclude_person_ids": [person_id(plant, "engineer")]}
        assert len(alerts) == 2
        assert len(tasks(db_rows, "ticket_escalate", ticket["id"])) == (1 if intensity == "critical" else 0)

    def test_machine_running_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant)
        restore(plant, ticket)
        res = plant["people"]["engineer"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/send-back",
                                                         json={"machine_down": False, "remark": "Check again"})
        assert res.status_code == 200, res.get_json()
        assert len(tasks(db_rows, "ticket_alert", ticket["id"])) == 1


class TestAssigned:

    def _assign(self, plant, ticket, key="technician"):
        res = plant["people"]["engineer"]["client"].post(f"{TICKETS}/{ticket['id']}/assignees",
                                                         json={"person_id": person_id(plant, key)})
        assert res.status_code == 200, res.get_json()
        return res.get_json()

    def _assigned(self, db_rows, ticket):
        return [t for t in tasks(db_rows, "ticket_alert", ticket["id"]) if t["payload"]["kind"] == "assigned"]

    def test_an_engineer_assigns_a_technician(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        shown = self._assign(plant, ticket)
        (alert,) = self._assigned(db_rows, ticket)
        assert alert["payload"] == {"ticket_id": ticket["id"], "kind": "assigned", "event_id": event_id(shown, "assigned"),
                                    "exclude_person_ids": [person_id(plant, "engineer")],
                                    "person_id": person_id(plant, "technician")}

    def test_the_same_person_again_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        self._assign(plant, ticket)
        self._assign(plant, ticket)
        assert len(self._assigned(db_rows, ticket)) == 1

    @pytest.mark.parametrize("move", ["acknowledge", "start"])
    def test_the_auto_assign_sends_nothing(self, plant, db_rows, move):
        ticket = raise_on(plant, intensity="degraded")
        res = plant["people"]["technician"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/{move}", json={})
        assert res.status_code == 200, res.get_json()
        assert [a["name"] for a in res.get_json()["assignees"]] == [plant["people"]["technician"]["person"]["name"]]
        assert self._assigned(db_rows, ticket) == []

    def test_fan_out_to_the_assignee_only(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        self._assign(plant, ticket)
        (alert,) = self._assigned(db_rows, ticket)
        run(ticket_alert, alert["payload"])
        (send,) = [s for s in sends(db_rows, ticket["id"]) if s["title"].startswith("Assigned to you")]
        assert send["subscription_id"] == plant["people"]["technician"]["device"]
        engineer_name = plant["people"]["engineer"]["person"]["name"].split()[0]
        assert send["body"] == f"{ticket['serial']} · Stopped — by {engineer_name}"
        assert send["urgency"] == "high" and send["silent"] is False

    def test_unassigned_before_sending_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        self._assign(plant, ticket)
        (alert,) = self._assigned(db_rows, ticket)
        res = plant["people"]["engineer"]["client"].delete(
            f"{TICKETS}/{ticket['id']}/assignees/{person_id(plant, 'technician')}")
        assert res.status_code == 200
        run(ticket_alert, alert["payload"])
        assert [s for s in sends(db_rows, ticket["id"]) if s["title"].startswith("Assigned")] == []

    def test_closed_before_sending_sends_nothing(self, plant, db_rows, set_ticket_state):
        ticket = raise_on(plant, intensity="degraded")
        self._assign(plant, ticket)
        (alert,) = self._assigned(db_rows, ticket)
        set_ticket_state(ticket, "closed")
        run(ticket_alert, alert["payload"])
        assert sends(db_rows, ticket["id"]) == []


# ---------------------------------------------------------------------------
# The fan-out (§ 5.2)
# ---------------------------------------------------------------------------

class TestFanOut:

    def _drain_first_alert(self, plant, db_rows, ticket):
        (alert,) = tasks(db_rows, "ticket_alert", ticket["id"])
        run(ticket_alert, alert["payload"])
        return sends(db_rows, ticket["id"])

    def test_a_breakdown_reaches_engineers_the_units_supervisors_and_managers(self, plant, db_rows):
        ticket = raise_on(plant)
        sent = self._drain_first_alert(plant, db_rows, ticket)
        assert sorted(s["subscription_id"] for s in sent) == devices_of(plant, "engineer", "supervisor", "manager")
        unit = plant["unit"]
        assert {s["title"] for s in sent} == {f"Breakdown · {plant['site']['code']}.{unit['code']} · "
                                              f"{plant['machine']['code']}"}
        operator = plant["people"]["operator"]["person"]["name"].split()[0]
        assert {s["body"] for s in sent} == {f"{ticket['serial']} · Stopped — raised by {operator}"}
        assert {(s["urgency"], s["silent"], s["ttl"], s["tag"]) for s in sent} == {
            ("high", False, 3600, f"ticket-{ticket['id']}")}

    def test_the_raiser_with_an_audience_role_is_left_out(self, plant, db_rows):
        res = plant["people"]["engineer"]["client"].post(TICKETS, json={
            "equipment_id": plant["machine"]["id"], "intensity": "critical", "description": "Stopped"})
        ticket = res.get_json()
        sent = self._drain_first_alert(plant, db_rows, ticket)
        assert sorted(s["subscription_id"] for s in sent) == devices_of(plant, "supervisor", "manager")

    def test_a_defect_reaches_engineers_quietly(self, plant, db_rows):
        ticket = raise_on(plant, intensity="degraded")
        sent = self._drain_first_alert(plant, db_rows, ticket)
        assert [s["subscription_id"] for s in sent] == devices_of(plant, "engineer")
        assert sent[0]["urgency"] == "low" and sent[0]["silent"] is True
        assert sent[0]["title"].startswith("Defect · ")

    def test_every_device_of_a_recipient(self, plant, db_rows, add_device):
        second = add_device(plant["people"]["engineer"]["person"])
        ticket = raise_on(plant, intensity="degraded")
        sent = self._drain_first_alert(plant, db_rows, ticket)
        assert sorted(s["subscription_id"] for s in sent) == sorted([plant["people"]["engineer"]["device"], second])

    def test_drained_after_back_in_service_sends_nothing(self, plant, db_rows):
        ticket = raise_on(plant)
        restore(plant, ticket)
        assert self._drain_first_alert(plant, db_rows, ticket) == []

    def test_push_off_finds_no_channel(self, plant, db_rows, push_off):
        ticket = raise_on(plant)
        assert self._drain_first_alert(plant, db_rows, ticket) == []

    def test_a_malformed_task_is_a_bad_task(self):
        with pytest.raises(task_handlers.BadTask):
            run(ticket_alert, {"ticket_id": 1, "kind": "nonsense", "event_id": 1})
        with pytest.raises(task_handlers.BadTask):
            run(ticket_alert, {"ticket_id": 999_999_999, "kind": "breakdown", "event_id": 1})


# ---------------------------------------------------------------------------
# Escalation (§ 5.1)
# ---------------------------------------------------------------------------

class TestEscalation:

    def _escalate(self, db_rows, ticket):
        (escalate,) = tasks(db_rows, "ticket_escalate", ticket["id"])
        run(ticket_escalate, escalate["payload"])
        return [t for t in tasks(db_rows, "ticket_alert", ticket["id"]) if t["payload"]["kind"] == "escalation"]

    def test_still_raised_escalates_to_engineers_and_managers(self, plant, db_rows):
        ticket = raise_on(plant)
        (alert,) = self._escalate(db_rows, ticket)
        assert alert["payload"] == {"ticket_id": ticket["id"], "kind": "escalation",
                                    "event_id": event_id(ticket, "raised"), "exclude_person_ids": [], "minutes": 60}
        run(ticket_alert, alert["payload"])
        sent = [s for s in sends(db_rows, ticket["id"]) if s["title"].startswith("Not acknowledged")]
        assert sorted(s["subscription_id"] for s in sent) == devices_of(plant, "engineer", "manager")
        assert sent[0]["title"].startswith("Not acknowledged after 60 min · ")

    @pytest.mark.parametrize("state", ["acknowledged", "scheduled", "in_progress", "back_in_service", "closed"])
    def test_skipped_once_acknowledged_in_any_way(self, plant, db_rows, set_ticket_state, state):
        ticket = raise_on(plant)
        if state == "scheduled":
            db_rows("UPDATE tickets SET state = 'scheduled', planned_date = CURDATE(), waiting_reason = 'parts'"
                    " WHERE id = %s", (ticket["id"],))
        else:
            set_ticket_state(ticket, state)
        assert self._escalate(db_rows, ticket) == []

    def test_skipped_after_an_acknowledge_move(self, plant, db_rows):
        ticket = raise_on(plant)
        res = plant["people"]["technician"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/acknowledge", json={})
        assert res.status_code == 200
        assert self._escalate(db_rows, ticket) == []

    def test_skipped_after_not_a_fault(self, plant, db_rows):
        ticket = raise_on(plant)
        cause = db_rows("SELECT id FROM failure_causes WHERE code = '3.4'")[0]["id"]
        res = plant["people"]["engineer"]["client"].post(f"{TICKETS}/{ticket['id']}/moves/not-a-fault",
                                                         json={"cause_id": cause, "remark": "Operator error"})
        assert res.status_code == 200, res.get_json()
        assert self._escalate(db_rows, ticket) == []

    def test_skipped_after_a_regrade_down_and_a_newer_trigger(self, plant, db_rows):
        ticket = raise_on(plant)
        engineer, operator = plant["people"]["engineer"]["client"], plant["people"]["operator"]["client"]
        assert engineer.post(f"{TICKETS}/{ticket['id']}/regrade",
                             json={"intensity": "degraded", "remark": "Runs slowly"}).status_code == 200
        first = tasks(db_rows, "ticket_escalate", ticket["id"])[0]["payload"]
        run(ticket_escalate, first)    # regraded down: no escalation
        assert operator.post(f"{TICKETS}/{ticket['id']}/regrade", json={"intensity": "critical"}).status_code == 200
        run(ticket_escalate, first)    # critical again, but the trigger is now the later regrade
        assert [t for t in tasks(db_rows, "ticket_alert", ticket["id"]) if t["payload"]["kind"] == "escalation"] == []
        second = tasks(db_rows, "ticket_escalate", ticket["id"])[1]["payload"]
        run(ticket_escalate, second)   # the latest trigger escalates, once
        assert len([t for t in tasks(db_rows, "ticket_alert", ticket["id"])
                    if t["payload"]["kind"] == "escalation"]) == 1


# ---------------------------------------------------------------------------
# push_send: the push service's answers (§ 5.1), with a fake sender
# ---------------------------------------------------------------------------

def _payload(subscription_id):
    return {"subscription_id": subscription_id, "title": "Breakdown · S.U · M", "body": "b", "path": "/tickets/1",
            "tag": "ticket-1", "urgency": "high", "silent": False, "ttl": 3600}


def fake_send(status, retry_after=None, calls=None):
    def send(subscription, data, urgency, ttl):
        if calls is not None:
            calls.append((subscription["id"], data, urgency, ttl))
        return status, retry_after
    return send


@pytest.fixture
def device(make_person, add_device):
    return add_device(make_person())


def _device_row(db_rows, subscription_id):
    rows = db_rows("SELECT last_sent_at, last_error FROM push_subscriptions WHERE id = %s", (subscription_id,))
    return rows[0] if rows else None


class TestSendOutcomes:

    def test_201_sets_last_sent_at(self, device, db_rows):
        calls = []
        db_rows("UPDATE push_subscriptions SET last_error = 'old' WHERE id = %s", (device,))
        run(push_send, _payload(device), send=fake_send(201, calls=calls))
        row = _device_row(db_rows, device)
        assert row["last_sent_at"] is not None and row["last_error"] is None
        assert calls == [(device, {"title": "Breakdown · S.U · M", "body": "b", "path": "/tickets/1",
                                   "tag": "ticket-1", "silent": False}, "high", 3600)]

    @pytest.mark.parametrize("status", [404, 410])
    def test_gone_deletes_the_device(self, device, db_rows, status):
        run(push_send, _payload(device), send=fake_send(status))
        assert _device_row(db_rows, device) is None

    @pytest.mark.parametrize("status", [400, 403, 413])
    def test_our_fault_keeps_the_error_and_does_not_retry(self, device, db_rows, status):
        with pytest.raises(NoRetry):
            run(push_send, _payload(device), send=fake_send(status))
        # Still there after the rollback: committed before the raise
        assert _device_row(db_rows, device)["last_error"] == f"Push service answered {status}"

    def test_429_with_retry_after_retries_later(self, device, db_rows):
        with pytest.raises(RetryLater) as raised:
            run(push_send, _payload(device), send=fake_send(429, "120"))
        assert raised.value.after_seconds == 120
        assert _device_row(db_rows, device)["last_error"] == "Push service answered 429"

    @pytest.mark.parametrize("status, retry_after", [(429, None), (429, "Wed, 21 Oct 2026 07:28:00 GMT"), (503, None)])
    def test_others_retry_with_the_back_off(self, device, db_rows, status, retry_after):
        with pytest.raises(RuntimeError, match=f"Push service answered {status}"):
            run(push_send, _payload(device), send=fake_send(status, retry_after))

    def test_a_timeout_is_recorded_without_the_address(self, device, db_rows):
        def timing_out(*_args):
            raise requests.exceptions.ConnectTimeout("HTTPSConnectionPool(host='fcm.googleapis.com'): /fcm/send/secret")
        with pytest.raises(RuntimeError) as raised:
            run(push_send, _payload(device), send=timing_out)
        assert "secret" not in str(raised.value)
        assert _device_row(db_rows, device)["last_error"] == "Could not reach the push service (ConnectTimeout)"

    def test_a_removed_device_is_done(self, device, db_rows):
        db_rows("DELETE FROM push_subscriptions WHERE id = %s", (device,))
        calls = []
        run(push_send, _payload(device), send=fake_send(201, calls=calls))
        assert calls == []

    def test_an_address_no_longer_allowed_is_not_posted(self, device, db_rows):
        db_rows("UPDATE push_subscriptions SET endpoint = 'https://evil.example/x' WHERE id = %s", (device,))
        calls = []
        with pytest.raises(NoRetry):
            run(push_send, _payload(device), send=fake_send(201, calls=calls))
        assert calls == []

    def test_through_the_worker_429_is_pending_about_120_s_later(self, device, db_rows, monkeypatch):
        """The whole path: handler -> RetryLater -> mark_failed's delay (BR2-03)."""
        monkeypatch.setattr(push_sender, "send", fake_send(429, "120"))
        db_rows("DELETE FROM task_queue")
        conn = get_local_db(config.DB_CONFIG)
        worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK)
        try:
            with conn.cursor() as cur:
                task_id = task_handlers.enqueue(cur, "push_send", _payload(device), max_attempts=3)
            worker.connect()
            assert worker.run_one() == task_id
            row = db_rows("SELECT status, last_error, TIMESTAMPDIFF(SECOND, NOW(), scheduled_for) AS wait"
                          " FROM task_queue WHERE id = %s", (task_id,))[0]
            assert row["status"] == "pending" and row["last_error"] == "RetryLater: Push service answered 429"
            assert 110 <= row["wait"] <= 120
            assert _device_row(db_rows, device)["last_error"] == "Push service answered 429"
        finally:
            worker.close()
            conn.close()
            db_rows("DELETE FROM task_queue")

    def test_through_the_worker_400_fails_without_retry(self, device, db_rows, monkeypatch):
        monkeypatch.setattr(push_sender, "send", fake_send(400))
        db_rows("DELETE FROM task_queue")
        conn = get_local_db(config.DB_CONFIG)
        worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK)
        try:
            with conn.cursor() as cur:
                task_id = task_handlers.enqueue(cur, "push_send", _payload(device), max_attempts=3)
            worker.connect()
            worker.run_one()
            row = db_rows("SELECT status, attempts FROM task_queue WHERE id = %s", (task_id,))[0]
            assert row == {"status": "failed", "attempts": 1}
            assert _device_row(db_rows, device)["last_error"] == "Push service answered 400"
        finally:
            worker.close()
            conn.close()
            db_rows("DELETE FROM task_queue")


# ---------------------------------------------------------------------------
# push_sender: the one call to pywebpush
# ---------------------------------------------------------------------------

class _Response:
    def __init__(self, status_code, headers=None):
        self.status_code = status_code
        self.headers = headers or {}


class TestSender:

    SUBSCRIPTION = {"endpoint": "https://fcm.googleapis.com/fcm/send/x", "p256dh": "BNc", "auth": "tB4"}

    def test_passes_the_timeout_and_reads_the_keys_at_call_time(self, monkeypatch):
        calls = []

        def fake_webpush(**kwargs):
            calls.append(kwargs)
            return _Response(201)
        monkeypatch.setattr(push_sender, "webpush", fake_webpush)
        monkeypatch.setattr(config, "VAPID_PRIVATE_KEY", "set-after-import")
        monkeypatch.setattr(config, "VAPID_SUBJECT", "mailto:later@example.invalid")
        assert push_sender.send(self.SUBSCRIPTION, {"title": "t"}, "low", 300) == (201, None)
        (call,) = calls
        assert call["timeout"] == 10
        assert call["vapid_private_key"] == "set-after-import"
        assert call["vapid_claims"] == {"sub": "mailto:later@example.invalid"}
        assert call["headers"] == {"Urgency": "low"} and call["ttl"] == 300
        assert call["subscription_info"] == {"endpoint": self.SUBSCRIPTION["endpoint"],
                                             "keys": {"p256dh": "BNc", "auth": "tB4"}}
        assert json.loads(call["data"]) == {"title": "t"}

    def test_an_error_answer_gives_its_status_and_retry_after(self, monkeypatch):
        def refusing(**_kwargs):
            raise WebPushException("Push failed: 429", response=_Response(429, {"Retry-After": "30"}))
        monkeypatch.setattr(push_sender, "webpush", refusing)
        assert push_sender.send(self.SUBSCRIPTION, {}, "high", 3600) == (429, "30")

    def test_an_error_without_an_answer_raises(self, monkeypatch):
        def broken(**_kwargs):
            raise WebPushException("VAPID dict missing 'private_key'")
        monkeypatch.setattr(push_sender, "webpush", broken)
        with pytest.raises(WebPushException):
            push_sender.send(self.SUBSCRIPTION, {}, "high", 3600)

    def test_enabled_needs_all_three_values(self, monkeypatch):
        assert push_sender.enabled()
        monkeypatch.setattr(config, "VAPID_SUBJECT", "")
        assert not push_sender.enabled()
