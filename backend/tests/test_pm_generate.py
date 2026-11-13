"""The daily PM run, pm_generate (S097 § 5.5, § 5.6, § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test makes its own site, unit, model, machine and meter type (the conftest factories) and its plans as an
engineer through tests/pm_helpers.py (S104: a template of its own, attached to the machine, then the plan's
settings).  A save settles its plan too (D5), so a plan is saved while not yet in its window
(no job), and is then brought into it by a straight row change (``set_plan``) or a fixed clock (``fix_now``), before
the run.  Rows a state the API cannot reach yet (a cancelled or started job) are inserted straight.

The run settles every plan in the worker's database, so a test that counts serials first deactivates the plans of
earlier tests (``alone``).  ``serial_counters`` is emptied once per session (BR1-02), so each such test fixes the
clock to a month of its own, far in the future.
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

import config
import pm_jobs
import worker as worker_module
from local_db import get_local_db
from pm_jobs_core import NODE_SCRAPPED_REMARK, RUN_ACTOR, TEMPLATE_INACTIVE_REMARK
from pm_schedule_core import next_due
from task_handlers import BadTask, RetryLater, pm_generate
from tests.db_names import TEST_WORKER_LOCK
from tests.documents_helpers import scrap
from tests.pm_helpers import (  # noqa: F401 — fixtures
    add_model_meter, add_own_meter, create, eng, engineer_a, hours, meter_of, oil, press, site, unlink_meter,
)
from tests.test_alerts import run
from worker import Worker

SERIAL = re.compile(r"^PM-\d{4}-\d{2}-\d{3,}$")


# ---------------------------------------------------------------------------
# Helpers, shared with test_pm_jobs_api.py
# ---------------------------------------------------------------------------

def db_now(db_rows):
    return db_rows("SELECT NOW() AS now")[0]["now"]


def fix_now(monkeypatch, moment):
    """pm_jobs._now (the run, the save and the list read it) answers ``moment``."""
    monkeypatch.setattr(pm_jobs, "_now", lambda cur: moment)


def jobs_of(db_rows, plan_id):
    return list(db_rows("SELECT * FROM pm_jobs WHERE plan_id = %s ORDER BY id", (plan_id,)))


def events_of(db_rows, job_id):
    return list(db_rows("SELECT * FROM pm_job_events WHERE job_id = %s ORDER BY id", (job_id,)))


def set_plan(db_rows, plan_id, **columns):
    """A straight change of the plan (no save, so no job is settled).  S104: ``active`` is the plan's template's
    (each test's plan has a template of its own), the other columns the plan row's."""
    template = {c: columns.pop(c) for c in ("active",) if c in columns}
    if template:
        db_rows(f"UPDATE pm_templates SET {', '.join(f'{c} = %s' for c in template)}"
                " WHERE id = (SELECT template_id FROM pm_plans WHERE id = %s)", (*template.values(), plan_id))
    if columns:
        db_rows(f"UPDATE pm_plans SET {', '.join(f'{c} = %s' for c in columns)} WHERE id = %s",
                (*columns.values(), plan_id))


def alone(db_rows, *plan_ids):
    """Unlink every other plan and cancel its due job straight, so the run's candidates are only these."""
    others = f"NOT IN ({', '.join(['%s'] * len(plan_ids))})"
    db_rows(f"UPDATE pm_plans SET linked = 0 WHERE id {others}", plan_ids)
    db_rows(f"UPDATE pm_jobs SET state = 'cancelled' WHERE state = 'due' AND plan_id {others}", plan_ids)


def insert_job(db_rows, plan, state="due", serial=None, performed_by=None):
    """A calendar job of ``plan`` (an API answer), inserted straight -> its id.  ``performed_by`` (a person) starts
    it now: a started job has a performer and a start time (v53's chk_pm_jobs_started, S098)."""
    serial = serial or f"PM-2099-12-{db_rows('SELECT COUNT(*) AS n FROM pm_jobs')[0]['n'] + 1:03d}"
    db_rows("INSERT INTO pm_jobs (serial, plan_id, equipment_id, state, created_why, due_on, grace_days,"
            " upcoming_days, performed_by_id, started_at, created_by)"
            " VALUES (%s, %s, %s, %s, 'calendar', CURDATE(), 3, 3, %s, IF(%s IS NULL, NULL, NOW()), 'kla')",
            (serial, plan["id"], plan["equipment"]["id"], state, performed_by and performed_by["id"],
             performed_by and performed_by["id"]))
    return db_rows("SELECT id FROM pm_jobs WHERE serial = %s", (serial,))[0]["id"]


def add_reading(db_rows, node, meter_type, value, taken_at, reset=False):
    db_rows("INSERT INTO meter_readings (equipment_id, meter_type_id, value, taken_at, is_reset, created_by)"
            " VALUES (%s, %s, %s, %s, %s, 'kla')", (node["id"], meter_type["id"], value, taken_at, int(reset)))


def expected_due(db_rows, plan_id, start_meter=None):
    """S095's next_due for the plan's row as stored, the way the shell calls it."""
    plan = db_rows(pm_jobs.PLAN_SELECT + " WHERE pl.id = %s", (plan_id,))[0]   # S104: with its template
    return next_due(dict(plan, created_on=plan["linked_at"].date()), None, start_meter)


def daily(**fields):
    """A plan every 30 days (upcoming 3 days, grace 3): no seed, so due 30 days after today."""
    return {"calendar_every": 30, "calendar_unit": "day", **fields}


def _today(db_rows):
    return db_now(db_rows).date()


def overdue(db_rows, **fields):
    """A plan due 10 days ago (grace 3): saved past due, so *Overdue* at once (test_pm_jobs_api, test_pm_work_api)."""
    return daily(last_done_on=(_today(db_rows) - timedelta(days=40)).isoformat(), **fields)


def upcoming(db_rows, **fields):
    """A plan due in 2 days (upcoming 3): saved in its window, so *Upcoming* at once."""
    return daily(last_done_on=(_today(db_rows) - timedelta(days=28)).isoformat(), **fields)


def generate():
    run(pm_generate, None)


@pytest.fixture
def technician(make_person, give_site_role, site):
    """A technician at every unit of the machine's site (an assignable person, no login)."""
    person = make_person(name="Ravi")
    give_site_role(person, site, "maint_technician")
    return person


# ---------------------------------------------------------------------------
# Making the job
# ---------------------------------------------------------------------------

class TestCreate:

    def test_a_due_plan_gets_one_job(self, engineer_a, press, technician, db_rows, monkeypatch):
        plan = create(engineer_a, press, assignee_id=technician["id"])
        assert jobs_of(db_rows, plan["id"]) == []                      # a month from due at the save
        alone(db_rows, plan["id"])
        fix_now(monkeypatch, datetime(2091, 3, 15, 5, 0))
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        due = expected_due(db_rows, plan["id"])
        assert job["serial"] == "PM-2091-03-001"
        assert (job["state"], job["created_why"], job["equipment_id"], job["assignee_id"]) == (
            "due", "calendar", press["id"], technician["id"])
        assert (job["due_on"], job["due_meter"], job["grace_days"], job["upcoming_days"], job["meter_window"],
                job["meter_offset"]) == (due.due_on, None, due.grace_days, due.upcoming_days, None, 0)
        (line,) = events_of(db_rows, job["id"])
        assert (line["event"], line["to_state"], line["due_on"], line["created_by"], line["occurred_at"]) == (
            "created", "due", due.due_on, RUN_ACTOR, datetime(2091, 3, 15, 5, 0))

        generate()                                                      # idempotent
        assert [j["id"] for j in jobs_of(db_rows, plan["id"])] == [job["id"]]
        assert len(events_of(db_rows, job["id"])) == 1

    def test_two_jobs_in_one_month_number_one_and_two_and_the_next_month_restarts(
            self, engineer_a, make_equipment, unit, db_rows, monkeypatch):
        plans = [create(engineer_a, make_equipment(unit=unit)) for _ in range(3)]
        alone(db_rows, plans[0]["id"], plans[1]["id"])
        fix_now(monkeypatch, datetime(2091, 4, 2, 5, 0))
        generate()
        alone(db_rows, plans[2]["id"])
        set_plan(db_rows, plans[2]["id"], linked=1)
        fix_now(monkeypatch, datetime(2091, 5, 2, 5, 0))
        generate()
        assert [jobs_of(db_rows, p["id"])[0]["serial"] for p in plans] == [
            "PM-2091-04-001", "PM-2091-04-002", "PM-2091-05-001"]

    def test_a_plan_far_from_due_makes_no_job(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, calendar_every=3, calendar_unit="month")
        generate()
        assert jobs_of(db_rows, plan["id"]) == []

    def test_a_plan_two_days_before_due_makes_a_job(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, **daily())
        today = db_now(db_rows).date()
        set_plan(db_rows, plan["id"], last_done_on=today - timedelta(days=28))   # due in 2 days, upcoming 3
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert SERIAL.match(job["serial"]) and job["due_on"] == today + timedelta(days=2)
        assert job["created_why"] == "calendar"


class TestMeter:

    def test_a_reading_past_the_due_value_makes_a_meter_job(self, engineer_a, press, hours, db_rows):
        plan = create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250", last_done_meter="1000")
        assert jobs_of(db_rows, plan["id"]) == []                      # no reading yet
        add_reading(db_rows, press, hours, "1260", db_now(db_rows) - timedelta(hours=1))
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert (job["created_why"], job["due_on"], job["due_meter"], job["meter_window"], job["meter_offset"]) == (
            "meter", None, Decimal("1250"), Decimal("25"), 0)

    def test_a_reading_below_the_window_makes_no_job(self, engineer_a, press, hours, db_rows):
        plan = create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250", last_done_meter="1000")
        add_reading(db_rows, press, hours, "1100", db_now(db_rows) - timedelta(hours=1))
        generate()
        assert jobs_of(db_rows, plan["id"]) == []

    def test_a_both_plan_gets_its_due_meter_after_the_first_reading(self, engineer_a, press, hours, db_rows):
        """S095 D9 through the run: a calendar job with no due meter, set once the meter has a reading."""
        plan = create(engineer_a, press, trigger_kind="both", **daily(), **meter_of(press, hours),
                      meter_every="250")
        today = db_now(db_rows).date()
        set_plan(db_rows, plan["id"], last_done_on=today - timedelta(days=29))   # due tomorrow
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert (job["created_why"], job["due_meter"], job["meter_window"]) == ("calendar", None, Decimal("25"))

        add_reading(db_rows, press, hours, "1000", db_now(db_rows) - timedelta(minutes=5))
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["due_meter"] == Decimal("1250")
        assert [(e["event"], e["due_meter"]) for e in events_of(db_rows, job["id"])] == [
            ("created", None), ("due_changed", Decimal("1250"))]

    def test_a_reset_after_the_base_carries_the_usage(self, engineer_a, press, hours, db_rows):
        """§ 5.4's first example: base 1,000; 1,100, 1,200, a reset at 50, then 80 -> counted 1,280."""
        plan = create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250", last_done_meter="1000")
        created = db_rows("SELECT linked_at FROM pm_plans WHERE id = %s", (plan["id"],))[0]["linked_at"]
        for minutes, value, reset in ((1, "1100", False), (2, "1200", False), (3, "50", True), (4, "80", False)):
            add_reading(db_rows, press, hours, value, created + timedelta(minutes=minutes), reset)
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert (job["created_why"], job["due_meter"], job["meter_offset"]) == ("meter", Decimal("1250"),
                                                                               Decimal("1200"))


class TestCancel:

    def test_an_inactive_plan_s_due_job_is_cancelled(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press)
        job_id = insert_job(db_rows, plan)
        set_plan(db_rows, plan["id"], active=0)
        generate()
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "cancelled"
        (line,) = events_of(db_rows, job_id)
        assert (line["event"], line["from_state"], line["to_state"], line["remark"], line["created_by"]) == (
            "cancelled", "due", "cancelled", TEMPLATE_INACTIVE_REMARK, RUN_ACTOR)

    def test_a_scrapped_machine_s_due_job_is_cancelled(self, engineer_a, admin, press, db_rows):
        plan = create(engineer_a, press)
        job_id = insert_job(db_rows, plan)
        scrap(admin, press)
        generate()
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "cancelled"
        assert events_of(db_rows, job_id)[0]["remark"] == NODE_SCRAPPED_REMARK

    def test_a_started_job_is_left(self, engineer_a, press, technician, db_rows):
        plan = create(engineer_a, press)
        job_id = insert_job(db_rows, plan, state="in_progress", performed_by=technician)
        set_plan(db_rows, plan["id"], active=0)
        generate()
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "in_progress"
        assert events_of(db_rows, job_id) == []


class TestMeterMatch:
    """S104 § 5.3, § 8.2: a template names a meter type; the run matches it on the machine's own meters each time."""

    def test_a_meter_added_to_the_node_makes_the_not_applying_plan_s_job(self, engineer_a, machine, hours,
                                                                          add_own_meter, db_rows):
        plan = create(engineer_a, machine, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      meter_type_id=hours["id"], meter_every="250")
        assert plan["applies"] is False and jobs_of(db_rows, plan["id"]) == []
        add_own_meter(machine, hours)
        add_reading(db_rows, machine, hours, "1300", db_now(db_rows) - timedelta(minutes=1))
        set_plan(db_rows, plan["id"], last_done_meter="1000", seed_meter_equipment_id=machine["id"],
                 seed_meter_type_id=hours["id"])
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert (job["due_meter"], job["meter_equipment_id"], job["meter_type_id"]) == (
            Decimal("1250"), machine["id"], hours["id"])

    def test_a_base_job_of_the_parent_s_meter_is_not_the_base_of_the_part_s_own_meter(
            self, engineer_a, press, hours, make_equipment, add_own_meter, db_rows):
        """BR1-01, CR1-04: the last done job counted on the press's hours (done at 1,000); the part then gets an
        hour meter of its own.  The next due counts from the part's own reading after that job (40), not from the
        press's 1,000: due 290, not 1,250, and the part's reading of 300 makes the job.  S104 A1: the part used the
        press's hours through a meter link, removed before its own meter is added (one meter per type, A1.6.1)."""
        part = make_equipment(parent=press)
        plan = create(engineer_a, part, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250")
        now = db_now(db_rows)
        db_rows("INSERT INTO pm_jobs (serial, plan_id, equipment_id, state, created_why, due_on, grace_days,"
                " upcoming_days, meter_equipment_id, meter_type_id, done_at, done_meter, created_by)"
                " VALUES (%s, %s, %s, 'skipped', 'meter', CURDATE(), 3, 3, %s, %s, %s, 1000, 'kla')",
                (f"PM-2097-02-{plan['id']:03d}", plan["id"], part["id"], press["id"], hours["id"],
                 now - timedelta(days=10)))
        unlink_meter(engineer_a, part, hours)
        add_own_meter(part, hours)
        add_reading(db_rows, part, hours, "40", now - timedelta(days=5))
        add_reading(db_rows, part, hours, "300", now - timedelta(hours=1))
        generate()
        (job,) = [row for row in jobs_of(db_rows, plan["id"]) if row["state"] == "due"]
        assert (job["created_why"], job["due_meter"], job["meter_equipment_id"]) == (
            "meter", Decimal("290"), part["id"])

    def test_a_meter_removed_cancels_the_due_job(self, engineer_a, admin, machine, hours, add_own_meter, db_rows):
        add_own_meter(machine, hours)
        plan = create(engineer_a, machine, trigger_kind="both", **overdue(db_rows), **meter_of(machine, hours),
                      meter_every="250")
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["meter_equipment_id"] == machine["id"]
        res = admin.put(f"/api/equipment/{machine['id']}/meters/{hours['id']}", json={"active": False})
        assert res.status_code == 200, res.get_json()
        generate()
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "cancelled"
        assert events_of(db_rows, job["id"])[-1]["remark"] == (
            f"Does not apply: no {hours['name']} meter on {machine['code']}.")


class TestAssignee:

    def test_an_assignee_who_left_leaves_the_job_unassigned(self, engineer_a, press, technician, db_rows):
        plan = create(engineer_a, press, assignee_id=technician["id"], **daily())
        set_plan(db_rows, plan["id"], last_done_on=db_now(db_rows).date() - timedelta(days=29))
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["assignee_id"] == technician["id"]
        db_rows("UPDATE people SET active = 0 WHERE id = %s", (technician["id"],))
        generate()
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["assignee_id"] is None
        assert [(e["event"], e["person_id"]) for e in events_of(db_rows, job["id"])] == [
            ("created", None), ("assignee_changed", None)]


# ---------------------------------------------------------------------------
# Faults, stops and the worker
# ---------------------------------------------------------------------------

class TestRun:

    def test_a_failing_plan_does_not_stop_the_others(self, engineer_a, make_equipment, unit, db_rows, monkeypatch):
        bad, good = (create(engineer_a, make_equipment(unit=unit)) for _ in range(2))
        alone(db_rows, bad["id"], good["id"])
        fix_now(monkeypatch, datetime(2091, 6, 2, 5, 0))
        real = pm_jobs.settle_plan_job

        def settle(cur, plan_id, *args, **kwargs):
            if plan_id == bad["id"]:
                raise ValueError("test: this plan fails")
            return real(cur, plan_id, *args, **kwargs)
        monkeypatch.setattr(pm_jobs, "settle_plan_job", settle)
        with pytest.raises(RuntimeError, match=f"plans {bad['id']} failed"):
            generate()
        assert jobs_of(db_rows, bad["id"]) == [] and len(jobs_of(db_rows, good["id"])) == 1

        monkeypatch.setattr(pm_jobs, "settle_plan_job", real)
        generate()                                                      # the retry settles nothing twice
        assert len(jobs_of(db_rows, bad["id"])) == 1
        (job,) = jobs_of(db_rows, good["id"])
        assert job["serial"] == "PM-2091-06-001" and len(events_of(db_rows, job["id"])) == 1

    def test_a_stop_after_the_first_plan_leaves_the_rest_for_the_retry(
            self, engineer_a, make_equipment, unit, db_rows, monkeypatch):
        first, second = (create(engineer_a, make_equipment(unit=unit)) for _ in range(2))
        alone(db_rows, first["id"], second["id"])
        fix_now(monkeypatch, datetime(2091, 7, 2, 5, 0))
        conn = get_local_db(config.DB_CONFIG)
        try:
            with pytest.raises(RetryLater):
                pm_generate(conn, None, lambda: True)
        finally:
            conn.close()
        assert len(jobs_of(db_rows, first["id"])) == 1                  # committed
        assert jobs_of(db_rows, second["id"]) == []

    def test_the_counts_name_only_real_writes(self, engineer_a, press, db_rows, monkeypatch):
        """CR1-02: an open job whose copies did not change is not counted as refreshed (nothing was written)."""
        plan = create(engineer_a, press)
        alone(db_rows, plan["id"])
        fix_now(monkeypatch, datetime(2091, 9, 2, 5, 0))
        conn = get_local_db(config.DB_CONFIG)
        try:
            first = pm_jobs.generate(conn, lambda: False)
            again = pm_jobs.generate(conn, lambda: False)
        finally:
            conn.close()
        assert (first["created"], first["refreshed"]) == (1, 0)
        assert (again["created"], again["refreshed"], again["cancelled"]) == (0, 0, 0)
        assert jobs_of(db_rows, plan["id"])[0]["updated_at"] is None

    def test_a_payload_is_a_bad_task(self):
        with pytest.raises(BadTask):
            generate_with({"plan_id": 1})

    def test_through_the_worker(self, engineer_a, press, db_rows, monkeypatch):
        plan = create(engineer_a, press, **daily())
        set_plan(db_rows, plan["id"], last_done_on=db_now(db_rows).date() - timedelta(days=29))
        db_rows("DELETE FROM task_queue")
        monkeypatch.setattr(worker_module, "SCHEDULE", [("pm_generate", "00:00")])
        worker = Worker(config.DB_CONFIG, lock_name=TEST_WORKER_LOCK, clock=lambda: db_now(db_rows))
        try:
            assert worker.run_once() is True
        finally:
            worker.close()
            statuses = [r["status"] for r in db_rows("SELECT status FROM task_queue WHERE task_type = 'pm_generate'")]
            db_rows("DELETE FROM task_queue")
        assert statuses == ["done"]
        assert len(jobs_of(db_rows, plan["id"])) == 1


def generate_with(payload):
    run(pm_generate, payload)
