"""Improvement alerts (S074 § 8.2), against the test DB, short of the push service.  Needs the dev MariaDB
container.

*Countermeasure for you* is queued by the countermeasure routes; *Countermeasure overdue* and *Ready to verify*
by the daily scan (improvement_alert_scan), which marks what it alerted (v40).  The handlers run here on a
connection of their own, in a transaction as the worker runs them (test_alerts.run); the worker itself runs
only where draining every task is the point, with the sender faked, so no test reaches a push service.

Each test starts its own improvement on its own ticket at its own site (S067's fixtures), so the kept worker
database is the starting state.  The scan reads every improvement of the database: a test asserts only on its
own improvement's tasks and rows, and the all-or-nothing test runs one scan first so only its own rows are
candidates.  Overdue is made by moving the due date back (db_rows, as S070 § 8.2); a watch that has ended by
S072's helpers (a corrective done 31 days back, a 30-day watch).
"""

import json
from datetime import timedelta

import pytest

import alerts
import config
import push_sender
import worker as worker_module
from task_handlers import BadTask, improvement_alert, improvement_alert_scan
from tests.db_names import TEST_WORKER_LOCK as TEST_LOCK
from tests.test_alerts import add_device, fake_send, run  # noqa: F401  (add_device: a fixture used by name)
from tests.test_improvement_close_api import (  # noqa: F401  (fixtures used by name)
    add_action, aged, cancel, make_ready, manager, modes, set_watch,
)
from tests.test_improvements_api import (  # noqa: F401  (fixtures used by name)
    IMPROVEMENTS, eng, no_cause, other_site, restored_ticket, site, started,
)
from tests.ticket_helpers import now_ist
from worker import Worker

GIVEN, OVERDUE, READY = "action_given", "action_overdue", "verify_ready"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def improvement(eng, restored_ticket):
    """A new improvement led by the engineer (analysing: open)."""
    client, person = eng
    return started(client, restored_ticket(), person)


@pytest.fixture
def at_site(user_at_sites, site, add_device):
    """at_site(role, units="all", devices=1) -> (client, person, [device ids]) of a person at the site."""
    def make(role, units="all", devices=1):
        client, person = user_at_sites([(site, role, units)])
        return client, person, [add_device(person) for _ in range(devices)]
    return make


def alert_tasks(db_rows, improvement_id):
    rows = db_rows("SELECT id, status, payload FROM task_queue WHERE task_type = 'improvement_alert'"
                   " AND JSON_EXTRACT(payload, '$.improvement_id') = %s ORDER BY id", (improvement_id,))
    return [{**row, "payload": json.loads(row["payload"])} for row in rows]


def sends(db_rows, improvement_id):
    """The push_send tasks of one improvement's alerts -> their payloads with their status."""
    rows = db_rows("SELECT status, payload FROM task_queue WHERE task_type = 'push_send'"
                   " AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.path')) = %s ORDER BY id",
                   (f"/tickets/improvements/{improvement_id}",))
    return [{**json.loads(row["payload"]), "status": row["status"]} for row in rows]


def devices_sent(db_rows, improvement_id):
    return sorted(s["subscription_id"] for s in sends(db_rows, improvement_id))


def username(db_rows, person):
    return db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"]


def first(person):
    return person["name"].split()[0]


def give(client, improvement, owner):
    """A countermeasure owned by ``owner``, due today -> the countermeasure."""
    _detail, action = add_action(client, improvement, owner)
    return action


def change(client, improvement, action, **fields):
    res = client.put(f"{IMPROVEMENTS}/{improvement['id']}/actions/{action['id']}", json=fields)
    assert res.status_code == 200, res.get_json()


def make_overdue(db_rows, action, days=1):
    db_rows("UPDATE improvement_actions SET due_date = CURDATE() - INTERVAL %s DAY WHERE id = %s", (days, action["id"]))


def action_row(db_rows, action):
    return db_rows("SELECT due_date, overdue_alert_for FROM improvement_actions WHERE id = %s", (action["id"],))[0]


def improvement_row(db_rows, improvement):
    return db_rows("SELECT watch_from, watch_days, ready_alert_for FROM improvements WHERE id = %s",
                   (improvement["id"],))[0]


def scan():
    run(improvement_alert_scan, None)


def drain(db_rows, improvement_id):
    """Run every pending improvement_alert of the improvement, as the worker would."""
    for task in alert_tasks(db_rows, improvement_id):
        if task["status"] == "pending":
            run(improvement_alert, task["payload"])
            db_rows("UPDATE task_queue SET status = 'done' WHERE id = %s", (task["id"],))


# ---------------------------------------------------------------------------
# Countermeasure for you: the request side (§ 5.5)
# ---------------------------------------------------------------------------

class TestGivenQueued:

    def test_an_engineer_gives_it_to_a_technician(self, eng, improvement, at_site, db_rows):
        client, person = eng
        _, technician, _ = at_site("maint_technician")
        action = give(client, improvement, technician)
        (task,) = alert_tasks(db_rows, improvement["id"])
        assert task["payload"] == {"kind": GIVEN, "improvement_id": improvement["id"], "action_id": action["id"],
                                   "person_id": technician["id"], "given_by": username(db_rows, person)}

    def test_given_to_themselves_queues_nothing(self, eng, improvement, db_rows):
        client, person = eng
        give(client, improvement, person)
        assert alert_tasks(db_rows, improvement["id"]) == []

    def test_a_change_of_the_due_date_only_queues_nothing(self, eng, improvement, at_site, db_rows):
        client, _ = eng
        _, technician, _ = at_site("maint_technician")
        action = give(client, improvement, technician)
        change(client, improvement, action, due_date=(now_ist().date() + timedelta(days=1)).isoformat())
        assert len(alert_tasks(db_rows, improvement["id"])) == 1

    def test_a_change_to_another_owner_queues_one(self, eng, improvement, at_site, db_rows):
        client, person = eng
        _, technician, _ = at_site("maint_technician")
        action = give(client, improvement, person)
        change(client, improvement, action, owner_id=technician["id"])
        (task,) = alert_tasks(db_rows, improvement["id"])
        assert (task["payload"]["kind"], task["payload"]["person_id"]) == (GIVEN, technician["id"])

    def test_a_refused_add_queues_nothing(self, eng, improvement, user_at_sites, other_site, db_rows):
        client, _ = eng
        _, stranger = user_at_sites([(other_site, "maint_technician", "all")])
        res = client.post(f"{IMPROVEMENTS}/{improvement['id']}/actions", json={
            "kind": "corrective", "text": "Fit a sealed contact block", "owner_id": stranger["id"],
            "due_date": "2026-11-30"})
        assert res.status_code == 400
        assert alert_tasks(db_rows, improvement["id"]) == []


# ---------------------------------------------------------------------------
# Countermeasure for you: the handler (§ 5.3, § 5.6)
# ---------------------------------------------------------------------------

class TestGivenSent:

    def test_the_owners_devices_get_it_quietly(self, eng, improvement, at_site, db_rows):
        client, person = eng
        _, technician, devices = at_site("maint_technician", devices=2)
        action = give(client, improvement, technician)
        drain(db_rows, improvement["id"])
        sent = sends(db_rows, improvement["id"])
        assert sorted(s["subscription_id"] for s in sent) == sorted(devices)
        detail = improvement
        assert {s["title"] for s in sent} == {
            f"Countermeasure for you · {detail['unit']['site_code']}.{detail['unit']['code']} · "
            f"{detail['machine']['code']}"}
        due = "-".join(reversed(action["due_date"].split("-")))
        assert {s["body"] for s in sent} == {
            f"{detail['serial']} · Fit a sealed contact block — due {due}, from {first(person)}"}
        assert {(s["urgency"], s["silent"], s["ttl"], s["tag"]) for s in sent} == {
            ("low", True, 86400, f"improvement-action-{action['id']}")}

    def test_an_owner_without_a_device_gets_nothing(self, eng, improvement, make_person, give_site_role, site,
                                                    db_rows):
        client, _ = eng
        fitter = make_person(name="Fitter Murugan")
        give_site_role(fitter, site, "maint_technician")
        give(client, improvement, fitter)
        drain(db_rows, improvement["id"])
        assert sends(db_rows, improvement["id"]) == []

    def test_a_storekeeper_owner_gets_nothing(self, eng, improvement, at_site, db_rows):
        """No improvement:read: the page would refuse them (A.8.3)."""
        client, _ = eng
        _, storekeeper, _ = at_site("maint_storekeeper")
        give(client, improvement, storekeeper)
        drain(db_rows, improvement["id"])
        assert sends(db_rows, improvement["id"]) == []

    def test_the_owner_changed_again_before_the_run(self, eng, improvement, at_site, db_rows):
        client, _ = eng
        _, first_owner, first_devices = at_site("maint_technician")
        _, second_owner, second_devices = at_site("maint_technician")
        action = give(client, improvement, first_owner)
        change(client, improvement, action, owner_id=second_owner["id"])
        drain(db_rows, improvement["id"])
        assert devices_sent(db_rows, improvement["id"]) == second_devices

    def test_cancelled_before_the_run(self, eng, improvement, at_site, db_rows):
        client, _ = eng
        _, technician, _ = at_site("maint_technician")
        action = give(client, improvement, technician)
        cancel(client, improvement, action)
        drain(db_rows, improvement["id"])
        assert sends(db_rows, improvement["id"]) == []

    def test_push_off_is_done_with_nothing(self, eng, improvement, at_site, db_rows, push_off):
        client, _ = eng
        _, technician, _ = at_site("maint_technician")
        give(client, improvement, technician)
        drain(db_rows, improvement["id"])
        assert sends(db_rows, improvement["id"]) == []


# ---------------------------------------------------------------------------
# The scan: Countermeasure overdue (§ 5.2)
# ---------------------------------------------------------------------------

class TestOverdue:

    def test_one_alert_per_due_date(self, eng, improvement, at_site, db_rows):
        client, person = eng
        action = give(client, improvement, person)
        make_overdue(db_rows, action)
        scan()
        row = action_row(db_rows, action)
        (task,) = alert_tasks(db_rows, improvement["id"])
        assert task["payload"] == {"kind": OVERDUE, "improvement_id": improvement["id"], "action_id": action["id"],
                                   "due_date": row["due_date"].isoformat()}
        assert row["overdue_alert_for"] == row["due_date"]
        scan()
        assert len(alert_tasks(db_rows, improvement["id"])) == 1

    def test_a_due_date_moved_later_and_past_again_alerts_again(self, eng, improvement, db_rows):
        client, person = eng
        action = give(client, improvement, person)
        make_overdue(db_rows, action, days=3)
        scan()
        make_overdue(db_rows, action, days=1)
        scan()
        tasks = alert_tasks(db_rows, improvement["id"])
        assert [t["payload"]["kind"] for t in tasks] == [OVERDUE, OVERDUE]
        assert tasks[0]["payload"]["due_date"] != tasks[1]["payload"]["due_date"]

    def test_a_done_countermeasure_is_not_overdue(self, eng, improvement, db_rows):
        client, person = eng
        action = give(client, improvement, person)
        make_overdue(db_rows, action)
        res = client.post(f"{IMPROVEMENTS}/{improvement['id']}/actions/{action['id']}/done",
                          json={"done_text": "Done"})
        assert res.status_code == 200, res.get_json()
        scan()
        assert alert_tasks(db_rows, improvement["id"]) == []
        assert action_row(db_rows, action)["overdue_alert_for"] is None

    def test_the_owner_and_the_lead_each_get_it(self, eng, improvement, at_site, add_device, db_rows):
        client, person = eng
        lead_device = add_device(person)
        _, technician, devices = at_site("maint_technician")
        action = give(client, improvement, technician)
        drain(db_rows, improvement["id"])   # the given alert, to the technician
        make_overdue(db_rows, action)
        scan()
        drain(db_rows, improvement["id"])
        overdue = [s for s in sends(db_rows, improvement["id"]) if s["title"].startswith("Countermeasure overdue")]
        assert sorted(s["subscription_id"] for s in overdue) == sorted([lead_device, *devices])
        assert {s["body"].split(", owner ")[1] for s in overdue} == {first(technician)}
        assert {s["tag"] for s in overdue} == {f"improvement-action-{action['id']}"}

    def test_the_lead_as_owner_gets_it_once(self, eng, improvement, add_device, db_rows):
        client, person = eng
        device = add_device(person)
        action = give(client, improvement, person)
        make_overdue(db_rows, action)
        scan()
        drain(db_rows, improvement["id"])
        assert devices_sent(db_rows, improvement["id"]) == [device]

    def test_an_owner_without_a_device_leaves_the_lead(self, eng, improvement, add_device, make_person,
                                                       give_site_role, site, db_rows):
        client, person = eng
        lead_device = add_device(person)
        fitter = make_person(name="Fitter Murugan")
        give_site_role(fitter, site, "maint_technician")
        action = give(client, improvement, fitter)
        make_overdue(db_rows, action)
        scan()
        drain(db_rows, improvement["id"])
        assert devices_sent(db_rows, improvement["id"]) == [lead_device]


# ---------------------------------------------------------------------------
# The scan: Ready to verify (§ 5.2, § 5.6)
# ---------------------------------------------------------------------------

class TestReady:

    def test_one_alert_per_watch_end(self, eng, aged, no_cause, db_rows):
        client, person = eng
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause, done_days=40)
        scan()
        row = improvement_row(db_rows, improvement)
        assert row["ready_alert_for"] == row["watch_from"] + timedelta(days=30)
        (task,) = [t for t in alert_tasks(db_rows, improvement["id"]) if t["payload"]["kind"] == READY]
        assert task["payload"] == {"kind": READY, "improvement_id": improvement["id"],
                                   "watch_until": row["ready_alert_for"].strftime("%Y-%m-%d %H:%M:%S")}
        scan()
        assert len([t for t in alert_tasks(db_rows, improvement["id"]) if t["payload"]["kind"] == READY]) == 1

    def test_a_watch_extended_and_ended_again_alerts_again(self, eng, aged, no_cause, db_rows):
        client, person = eng
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause, done_days=40)
        scan()
        set_watch(client, improvement, 35)   # the end moves 5 days later, still past
        scan()
        ready = [t for t in alert_tasks(db_rows, improvement["id"]) if t["payload"]["kind"] == READY]
        assert len(ready) == 2
        assert (improvement_row(db_rows, improvement)["ready_alert_for"]
                - improvement_row(db_rows, improvement)["watch_from"]).days == 35

    def test_it_reaches_the_sites_verifiers_who_cover_the_unit(self, eng, aged, no_cause, at_site, add_device,
                                                               make_unit, site, db_rows):
        client, person = eng
        lead_device = add_device(person)
        _, _, manager_devices = at_site("maint_manager")
        at_site("maint_technician")
        at_site("maint_engineer", units=[make_unit(site=site)])   # another unit of the site
        improvement, _ = aged()
        make_ready(client, person, improvement, no_cause)
        scan()
        drain(db_rows, improvement["id"])
        sent = sends(db_rows, improvement["id"])
        assert sorted(s["subscription_id"] for s in sent) == sorted([lead_device, *manager_devices])
        assert {s["title"].split(" · ")[0] for s in sent} == {"Ready to verify"}
        assert {(s["tag"], s["silent"], s["ttl"]) for s in sent} == {(f"improvement-{improvement['id']}", True, 86400)}


# ---------------------------------------------------------------------------
# The scan's transaction, the worker, bad tasks
# ---------------------------------------------------------------------------

class TestScanTransaction:

    def test_a_fault_leaves_no_marker_and_no_task(self, eng, improvement, db_rows, monkeypatch):
        client, person = eng
        scan()   # every earlier candidate of the database is marked now
        actions = [give(client, improvement, person) for _ in range(2)]
        for action in actions:
            make_overdue(db_rows, action)
        calls = []
        real = alerts.enqueue_improvement_alert

        def failing_second(*args, **kwargs):
            calls.append(args)
            if len(calls) == 2:
                raise RuntimeError("fault after the first marker")
            return real(*args, **kwargs)
        monkeypatch.setattr(alerts, "enqueue_improvement_alert", failing_second)
        with pytest.raises(RuntimeError):
            scan()
        assert [action_row(db_rows, a)["overdue_alert_for"] for a in actions] == [None, None]
        assert alert_tasks(db_rows, improvement["id"]) == []


@pytest.fixture
def queue_emptied(db_rows):
    """The worker drains every due task: start and end with an empty queue (as test_worker.py)."""
    db_rows("DELETE FROM task_queue")
    yield
    db_rows("DELETE FROM task_queue")


def _run_worker(db_rows, monkeypatch):
    monkeypatch.setattr(worker_module, "SCHEDULE", [("improvement_alert_scan", "00:00")])
    worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK, clock=lambda: db_rows("SELECT NOW() AS now")[0]["now"])
    try:
        assert worker.run_once() is True
    finally:
        worker.close()


class TestThroughTheWorker:
    """BR1-04: Worker.run_once drains the scan, its alert tasks and their push_send tasks."""

    def test_scan_alerts_and_sends_all_done(self, eng, improvement, add_device, db_rows, monkeypatch,
                                            queue_emptied):
        client, person = eng
        device = add_device(person)
        action = give(client, improvement, person)
        make_overdue(db_rows, action)
        calls = []
        monkeypatch.setattr(push_sender, "send", fake_send(201, calls=calls))
        _run_worker(db_rows, monkeypatch)
        assert [r["status"] for r in db_rows("SELECT status FROM task_queue"
                                              " WHERE task_type = 'improvement_alert_scan'")] == ["done"]
        assert [t["status"] for t in alert_tasks(db_rows, improvement["id"])] == ["done"]
        sent = sends(db_rows, improvement["id"])
        assert [(s["subscription_id"], s["status"]) for s in sent] == [(device, "done")]
        mine = [c for c in calls if c[0] == device]
        assert len(mine) == 1 and mine[0][1]["title"].startswith("Countermeasure overdue") and mine[0][2:] == (
            "low", 86400)

    def test_push_off_still_marks_and_queues_once(self, eng, improvement, add_device, db_rows, monkeypatch,
                                                  queue_emptied, push_off):
        """D8: the markers are about the event, so turning push on later sends no backlog."""
        client, person = eng
        add_device(person)
        action = give(client, improvement, person)
        make_overdue(db_rows, action)
        _run_worker(db_rows, monkeypatch)
        row = action_row(db_rows, action)
        assert row["overdue_alert_for"] == row["due_date"]
        assert [t["status"] for t in alert_tasks(db_rows, improvement["id"])] == ["done"]
        assert sends(db_rows, improvement["id"]) == []
        scan()
        assert len(alert_tasks(db_rows, improvement["id"])) == 1


class TestBadTasks:

    def test_the_scan_takes_no_payload(self):
        with pytest.raises(BadTask):
            run(improvement_alert_scan, {"x": 1})

    def test_an_unknown_kind(self, improvement):
        with pytest.raises(BadTask):
            run(improvement_alert, {"kind": "breakdown", "improvement_id": improvement["id"], "action_id": 1,
                                    "person_id": 1, "given_by": "x"})

    def test_a_missing_action_id(self, improvement):
        with pytest.raises(BadTask):
            run(improvement_alert, {"kind": OVERDUE, "improvement_id": improvement["id"], "due_date": "2026-11-08"})

    def test_a_bad_date(self, improvement):
        with pytest.raises(BadTask):
            run(improvement_alert, {"kind": READY, "improvement_id": improvement["id"], "watch_until": "18-02-2027"})

    def test_an_action_of_another_improvement(self, eng, improvement, restored_ticket, db_rows):
        client, person = eng
        other = started(client, restored_ticket(), person)
        action = give(client, other, person)
        with pytest.raises(BadTask):
            run(improvement_alert, {"kind": GIVEN, "improvement_id": improvement["id"], "action_id": action["id"],
                                    "person_id": person["id"], "given_by": "x"})

    def test_an_unknown_improvement(self):
        with pytest.raises(BadTask):
            run(improvement_alert, {"kind": READY, "improvement_id": 999_999_999,
                                    "watch_until": "2027-02-18 15:30:00"})
