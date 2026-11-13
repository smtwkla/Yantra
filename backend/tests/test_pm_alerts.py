"""PM alerts (S102 § 5.4–5.6, § 8.2): the daily pm_job_alert_scan, the pm_job_alert task and their recipients, against
the test DB.  Needs the dev MariaDB container.

Each plan is saved through POST /api/pm/plans as the engineer, with the technician as assignee.  The scan reads every
due job of the worker's database, so each test first leaves only its own plans (``alone``, as S097's tests).  A
person's device is a push_subscriptions row (``add_device``, no login needed); a person without one stands for a
contractor, who cannot sign in and so has no device.
"""

import json
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

import alerts
import config
import push_sender
import worker as worker_module
from task_handlers import BadTask, pm_generate, pm_job_alert, pm_job_alert_scan
from tests.db_names import TEST_WORKER_LOCK as TEST_LOCK
from tests.documents_helpers import scrap
from tests.test_alerts import add_device, fake_send, run  # noqa: F401 — add_device is a fixture
from tests.test_pm_generate import (  # noqa: F401 — technician is a fixture
    add_reading, alone, db_now, fix_now, jobs_of, overdue, set_plan, technician, upcoming,
)
from tests.pm_helpers import (  # noqa: F401 — fixtures
    add_model_meter, create, eng, engineer_a, hours, meter_of, oil, press, site,
)
from tests.test_pm_reschedule_api import day, reschedule
from worker import Worker

MARKERS = ("due_alert_on", "due_alert_meter", "overdue_alert_on", "overdue_alert_meter")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def scan():
    run(pm_job_alert_scan, None)


def alert_tasks(db_rows, job_id):
    """The pm_job_alert tasks of one job -> ``[{id, status, payload}]`` in id order."""
    rows = db_rows("SELECT id, status, payload FROM task_queue WHERE task_type = 'pm_job_alert'"
                   " AND JSON_EXTRACT(payload, '$.job_id') = %s ORDER BY id", (job_id,))
    return [{**row, "payload": json.loads(row["payload"])} for row in rows]


def kinds(db_rows, job_id):
    return [task["payload"]["kind"] for task in alert_tasks(db_rows, job_id)]


def sends(db_rows, job_id):
    """The push_send tasks of one job's alerts -> their payloads, in id order."""
    rows = db_rows("SELECT payload FROM task_queue WHERE task_type = 'push_send'"
                   " AND JSON_UNQUOTE(JSON_EXTRACT(payload, '$.path')) = %s ORDER BY id", (f"/pm/jobs/{job_id}",))
    return [json.loads(row["payload"]) for row in rows]


def deliver(db_rows, job_id):
    """Run each pending pm_job_alert task of the job once, as the worker would, and mark it done."""
    for task in alert_tasks(db_rows, job_id):
        if task["status"] == "pending":
            run(pm_job_alert, task["payload"])
            db_rows("UPDATE task_queue SET status = 'done' WHERE id = %s", (task["id"],))


def job_of(db_rows, plan):
    (job,) = jobs_of(db_rows, plan["id"])
    return job


def at(day, hour=8):
    return datetime.combine(day, time(hour, 0))


def overdue_day(job):
    """The first morning after the on-time window (§ 5.1): due_on + grace + 1."""
    return job["due_on"] + timedelta(days=job["grace_days"] + 1)


@pytest.fixture
def due_plan(engineer_a, press, technician, db_rows):
    """A plan saved *Upcoming* (due in 2 days), the technician its assignee; alone in the scan -> (plan, job)."""
    plan = create(engineer_a, press, assignee_id=technician["id"], **upcoming(db_rows))
    alone(db_rows, plan["id"])
    return plan, job_of(db_rows, plan)


@pytest.fixture
def people(eng, user_at_sites, site, make_unit, add_device, technician):
    """Who should and who should not hear about the machine's jobs, each with one device."""
    other_unit = make_unit(site=site)
    out = {"engineer": eng[1], "technician": technician}
    for key, spec in {
        "manager": [(site, "maint_manager", "all")],
        "engineer_elsewhere": [(site, "maint_engineer", [other_unit])],
        "supervisor": [(site, "maint_supervisor", "all")],
        "operator": [(site, "maint_operator", "all")],
    }.items():
        out[key] = user_at_sites(spec)[1]
    devices = {key: add_device(person) for key, person in out.items()}
    return {"person": out, "device": devices, "other_unit": other_unit}


def devices_of(people, *keys):
    return sorted(people["device"][key] for key in keys)


# ---------------------------------------------------------------------------
# The scan (§ 5.4)
# ---------------------------------------------------------------------------

class TestDueByDate:

    def test_due_then_overdue_each_once(self, due_plan, db_rows, monkeypatch):
        plan, job = due_plan
        scan()                                                     # Upcoming: nothing
        assert kinds(db_rows, job["id"]) == []
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        (task,) = alert_tasks(db_rows, job["id"])
        assert task["payload"] == {"kind": "pm_job_due", "job_id": job["id"]}
        row = job_of(db_rows, plan)
        assert (row["due_alert_on"], row["due_alert_meter"]) == (job["due_on"], None)
        assert (row["overdue_alert_on"], row["overdue_alert_meter"]) == (None, None)
        assert (row["updated_at"], row["updated_by"]) == (job["updated_at"], job["updated_by"])   # not a change
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]

        fix_now(monkeypatch, at(job["due_on"] + timedelta(days=job["grace_days"])))   # the window's last day
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        fix_now(monkeypatch, at(overdue_day(job)))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_overdue"]
        row = job_of(db_rows, plan)
        assert [row[column] for column in MARKERS] == [job["due_on"], None, job["due_on"], None]
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_overdue"]

    def test_straight_to_overdue_sends_only_overdue(self, engineer_a, press, technician, db_rows):
        plan = create(engineer_a, press, assignee_id=technician["id"], **overdue(db_rows))
        alone(db_rows, plan["id"])
        scan()
        job = job_of(db_rows, plan)
        assert kinds(db_rows, job["id"]) == ["pm_job_overdue"]
        assert [job[column] for column in MARKERS] == [job["due_on"], None, job["due_on"], None]

    def test_a_moved_due_point_alerts_again(self, due_plan, db_rows, monkeypatch):
        """§ 5.2: a plan change moves the job's due date; the markers then differ, so *due* comes again."""
        plan, job = due_plan
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        seed = db_rows("SELECT last_done_on FROM pm_plans WHERE id = %s", (plan["id"],))[0]["last_done_on"]
        set_plan(db_rows, plan["id"], last_done_on=seed + timedelta(days=7))
        run(pm_generate, None)                                     # the refresh: due_on 7 days later
        moved = job_of(db_rows, plan)
        assert moved["due_on"] == job["due_on"] + timedelta(days=7)
        scan()                                                     # not yet due at the new date
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        fix_now(monkeypatch, at(moved["due_on"]))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_due"]
        assert job_of(db_rows, plan)["due_alert_on"] == moved["due_on"]

    def test_a_reschedule_leaves_the_markers_and_alerts_again(self, due_plan, engineer_a, db_rows, monkeypatch):
        """§ 5.2 (CR1-02): S101's reschedule never writes the markers; the moved point differs from them, so *due*
        comes again when the new point is due."""
        plan, job = due_plan
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        before = job_of(db_rows, plan)
        new_day = day(db_rows, 10)
        reschedule(engineer_a, job["id"], due_on=new_day)
        row = job_of(db_rows, plan)
        assert row["due_on"].isoformat() == new_day
        assert [row[column] for column in MARKERS] == [before[column] for column in MARKERS]
        assert row["due_alert_on"] == job["due_on"]
        scan()                                                     # the moved point is not due yet
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        fix_now(monkeypatch, at(row["due_on"]))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_due"]
        assert job_of(db_rows, plan)["due_alert_on"] == row["due_on"]


class TestDueByMeter:

    def test_below_at_and_past_the_due_value(self, engineer_a, press, hours, technician, db_rows):
        plan = create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250", last_done_meter="1000",
                      assignee_id=technician["id"])
        now = db_now(db_rows)
        add_reading(db_rows, press, hours, "1230", now - timedelta(hours=3))   # Upcoming (1225 … 1250)
        run(pm_generate, None)
        alone(db_rows, plan["id"])
        job = job_of(db_rows, plan)
        assert (job["due_meter"], job["meter_window"]) == (Decimal("1250"), Decimal("25"))
        scan()
        assert kinds(db_rows, job["id"]) == []
        add_reading(db_rows, press, hours, "1250", now - timedelta(hours=2))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        row = job_of(db_rows, plan)
        assert (row["due_alert_on"], row["due_alert_meter"]) == (None, Decimal("1250"))
        add_reading(db_rows, press, hours, "1276", now - timedelta(hours=1))   # past 1250 + 25
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_overdue"]
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due", "pm_job_overdue"]


class TestNoAlert:

    @pytest.fixture
    def late(self, engineer_a, press, technician, db_rows):
        """An *Overdue* job, alone in the scan -> (plan, job)."""
        plan = create(engineer_a, press, assignee_id=technician["id"], **overdue(db_rows))
        alone(db_rows, plan["id"])
        return plan, job_of(db_rows, plan)

    def test_a_started_job(self, late, technician, db_rows):
        _plan, job = late
        db_rows("UPDATE pm_jobs SET state = 'in_progress', performed_by_id = %s, started_at = NOW() WHERE id = %s",
                (technician["id"], job["id"]))
        scan()
        assert kinds(db_rows, job["id"]) == []

    def test_a_done_job(self, late, technician, db_rows):
        _plan, job = late
        db_rows("UPDATE pm_jobs SET state = 'done', performed_by_id = %s, started_at = NOW() - INTERVAL 1 HOUR,"
                " done_at = NOW(), timeliness = 'late' WHERE id = %s", (technician["id"], job["id"]))
        scan()
        assert kinds(db_rows, job["id"]) == []

    def test_a_cancelled_job(self, late, db_rows):
        _plan, job = late
        db_rows("UPDATE pm_jobs SET state = 'cancelled' WHERE id = %s", (job["id"],))
        scan()
        assert kinds(db_rows, job["id"]) == []

    def test_an_inactive_plan(self, late, db_rows):
        plan, job = late
        set_plan(db_rows, plan["id"], active=0)                    # the job still due till the next pm_generate
        scan()
        assert kinds(db_rows, job["id"]) == []
        assert [job_of(db_rows, plan)[column] for column in MARKERS] == [None] * 4

    def test_a_scrapped_node(self, late, admin, press, db_rows):
        plan, job = late
        scrap(admin, press)
        db_rows("UPDATE pm_jobs SET state = 'due' WHERE id = %s", (job["id"],))   # as before the next pm_generate
        scan()
        assert kinds(db_rows, job["id"]) == []


class TestAllOrNothingPerJob:

    def test_one_failed_job_keeps_the_others(self, engineer_a, press, make_equipment, unit, technician, db_rows,
                                             monkeypatch):
        plans = [create(engineer_a, node, assignee_id=technician["id"], **overdue(db_rows))
                 for node in (press, make_equipment(unit=unit))]
        alone(db_rows, *(plan["id"] for plan in plans))
        good, bad = (job_of(db_rows, plan) for plan in plans)
        real = alerts.enqueue_pm_alert

        def enqueue(cur, kind, job_id):
            if job_id == bad["id"]:
                raise RuntimeError("the queue refused it")
            return real(cur, kind, job_id)

        monkeypatch.setattr(alerts, "enqueue_pm_alert", enqueue)
        with pytest.raises(RuntimeError, match=f"pm_job_alert_scan: jobs {bad['id']} failed"):
            scan()
        assert kinds(db_rows, good["id"]) == ["pm_job_overdue"]
        assert job_of(db_rows, plans[0])["overdue_alert_on"] == good["due_on"]
        assert kinds(db_rows, bad["id"]) == []
        assert [job_of(db_rows, plans[1])[column] for column in MARKERS] == [None] * 4
        monkeypatch.setattr(alerts, "enqueue_pm_alert", real)
        scan()                                                     # the retry: only the failed job
        assert kinds(db_rows, good["id"]) == ["pm_job_overdue"]
        assert kinds(db_rows, bad["id"]) == ["pm_job_overdue"]


# ---------------------------------------------------------------------------
# The alert task and its recipients (§ 5.6)
# ---------------------------------------------------------------------------

class TestRecipients:

    def test_due_goes_to_the_assignee_only(self, due_plan, people, db_rows, monkeypatch):
        plan, job = due_plan
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        deliver(db_rows, job["id"])
        (sent,) = sends(db_rows, job["id"])
        assert sent["subscription_id"] == people["device"]["technician"]
        assert (sent["urgency"], sent["silent"], sent["ttl"], sent["path"], sent["tag"]) == (
            "low", True, 86400, f"/pm/jobs/{job['id']}", f"pm-job-{job['id']}")
        place = db_rows("SELECT CONCAT(s.code, '.', u.code, ' · ', e.code) AS place FROM equipment e"
                        " JOIN units u ON u.id = e.unit_id JOIN sites s ON s.id = u.site_id WHERE e.id = %s",
                        (job["equipment_id"],))[0]["place"]
        assert sent["title"] == f"PM job due · {place}"
        assert sent["body"] == (f"{job['serial']} · {plan['template']['name']} — due on {job['due_on']:%d-%m-%Y},"
                                f" on time until {job['due_on'] + timedelta(days=job['grace_days']):%d-%m-%Y}.")

    def test_overdue_goes_to_the_assignee_and_the_verify_holders(self, due_plan, people, db_rows, monkeypatch):
        plan, job = due_plan
        fix_now(monkeypatch, at(overdue_day(job)))
        scan()
        deliver(db_rows, job["id"])
        assert sorted(s["subscription_id"] for s in sends(db_rows, job["id"])) == devices_of(
            people, "technician", "engineer", "manager")
        assert {s["body"] for s in sends(db_rows, job["id"])} == {
            f"{job['serial']} · {plan['template']['name']} — was due on {job['due_on']:%d-%m-%Y}, assigned to Ravi."}

    def test_no_assignee(self, engineer_a, press, people, db_rows, monkeypatch):
        plan = create(engineer_a, press, **upcoming(db_rows))
        alone(db_rows, plan["id"])
        job = job_of(db_rows, plan)
        assert job["assignee_id"] is None
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        deliver(db_rows, job["id"])
        assert sends(db_rows, job["id"]) == []                     # *due* reaches nobody
        fix_now(monkeypatch, at(overdue_day(job)))
        scan()
        deliver(db_rows, job["id"])
        assert sorted(s["subscription_id"] for s in sends(db_rows, job["id"])) == devices_of(
            people, "engineer", "manager")
        assert sends(db_rows, job["id"])[0]["body"].endswith(", not assigned.")

    def test_a_contractor_assignee_has_no_device(self, engineer_a, press, people, make_person, give_site_role,
                                                 site, db_rows, monkeypatch):
        contractor = make_person(name="Murugan", employment="contractor")
        give_site_role(contractor, site, "maint_technician")
        plan = create(engineer_a, press, assignee_id=contractor["id"], **overdue(db_rows))
        alone(db_rows, plan["id"])
        job = job_of(db_rows, plan)
        assert job["assignee_id"] == contractor["id"]
        scan()
        deliver(db_rows, job["id"])
        assert sorted(s["subscription_id"] for s in sends(db_rows, job["id"])) == devices_of(
            people, "engineer", "manager")
        assert sends(db_rows, job["id"])[0]["body"].endswith(", assigned to Murugan.")

    def test_an_assignee_who_no_longer_covers_the_unit_is_left_out(self, due_plan, people, admin, site, db_rows,
                                                                   monkeypatch):
        _plan, job = due_plan
        technician = people["person"]["technician"]
        res = admin.put(f"/api/masters/people/{technician['id']}/sites/{site['id']}",
                        json={"role": "maint_technician", "all_units": False,
                              "unit_ids": [people["other_unit"]["id"]]})
        assert res.status_code == 200, res.get_json()
        fix_now(monkeypatch, at(overdue_day(job)))
        scan()
        deliver(db_rows, job["id"])
        assert sorted(s["subscription_id"] for s in sends(db_rows, job["id"])) == devices_of(
            people, "engineer", "manager")


class TestNoLongerTrue:

    @pytest.fixture
    def queued(self, due_plan, people, db_rows, monkeypatch):
        """A *due* alert queued, not yet sent -> the job."""
        _plan, job = due_plan
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]
        return job

    def test_started(self, queued, technician, db_rows):
        db_rows("UPDATE pm_jobs SET state = 'in_progress', performed_by_id = %s, started_at = NOW() WHERE id = %s",
                (technician["id"], queued["id"]))
        deliver(db_rows, queued["id"])
        assert sends(db_rows, queued["id"]) == []

    def test_plan_inactive(self, queued, db_rows):
        set_plan(db_rows, queued["plan_id"], active=0)
        deliver(db_rows, queued["id"])
        assert sends(db_rows, queued["id"]) == []

    def test_node_scrapped(self, queued, admin, press, db_rows):
        scrap(admin, press)
        db_rows("UPDATE pm_jobs SET state = 'due' WHERE id = %s", (queued["id"],))   # as before the next pm_generate
        deliver(db_rows, queued["id"])
        assert sends(db_rows, queued["id"]) == []

    def test_due_point_moved_after_the_scan(self, queued, db_rows):
        db_rows("UPDATE pm_jobs SET due_on = due_on + INTERVAL 7 DAY WHERE id = %s", (queued["id"],))
        deliver(db_rows, queued["id"])
        assert sends(db_rows, queued["id"]) == []

    def test_push_off_sends_nothing_and_the_scan_still_marks(self, due_plan, people, db_rows, monkeypatch, push_off):
        plan, job = due_plan
        fix_now(monkeypatch, at(job["due_on"]))
        scan()
        assert job_of(db_rows, plan)["due_alert_on"] == job["due_on"]
        deliver(db_rows, job["id"])
        assert sends(db_rows, job["id"]) == []
        scan()
        assert kinds(db_rows, job["id"]) == ["pm_job_due"]


# ---------------------------------------------------------------------------
# Through the worker, and bad tasks
# ---------------------------------------------------------------------------

@pytest.fixture
def queue_emptied(db_rows):
    """The worker drains every due task: start and end with an empty queue (as test_worker.py)."""
    db_rows("DELETE FROM task_queue")
    yield
    db_rows("DELETE FROM task_queue")


class TestThroughTheWorker:

    def test_scan_alert_and_send_all_done(self, engineer_a, press, technician, add_device, db_rows, monkeypatch,
                                          queue_emptied):
        plan = create(engineer_a, press, assignee_id=technician["id"], **overdue(db_rows))
        alone(db_rows, plan["id"])
        job = job_of(db_rows, plan)
        device = add_device(technician)
        calls = []
        monkeypatch.setattr(push_sender, "send", fake_send(201, calls=calls))
        monkeypatch.setattr(worker_module, "SCHEDULE", [("pm_job_alert_scan", "00:00")])
        worker = Worker(config.DB_CONFIG, lock_name=TEST_LOCK, clock=lambda: db_rows("SELECT NOW() AS now")[0]["now"])
        try:
            assert worker.run_once() is True
        finally:
            worker.close()
        assert [r["status"] for r in db_rows("SELECT status FROM task_queue"
                                              " WHERE task_type = 'pm_job_alert_scan'")] == ["done"]
        assert [t["status"] for t in alert_tasks(db_rows, job["id"])] == ["done"]
        mine = [c for c in calls if c[0] == device]
        assert len(mine) == 1 and mine[0][2:] == ("low", 86400)
        assert mine[0][1]["title"].startswith("PM job overdue · ") and job["serial"] in mine[0][1]["body"]


class TestBadTasks:

    def test_the_scan_takes_no_payload(self):
        with pytest.raises(BadTask):
            run(pm_job_alert_scan, {"x": 1})

    def test_an_unknown_kind(self, due_plan):
        _plan, job = due_plan
        with pytest.raises(BadTask, match="unknown kind"):
            run(pm_job_alert, {"kind": "breakdown", "job_id": job["id"]})

    def test_no_job_id(self):
        with pytest.raises(BadTask):
            run(pm_job_alert, {"kind": "pm_job_due"})

    def test_a_missing_job(self):
        with pytest.raises(BadTask, match="no PM job"):
            run(pm_job_alert, {"kind": "pm_job_due", "job_id": 999999999})
