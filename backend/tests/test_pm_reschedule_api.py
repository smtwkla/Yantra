"""Reschedule and skip a PM job (S101 § 5, § 6, § 8.2): the move by date and by meter, the run and a plan save that
keep it or drop it, on time against the new date, the refusals, the before-use guard, the skip and the next job,
the Done tab, the lock and the identity.  Needs the dev MariaDB container.

Each test makes its own site, unit, model and machine (test_pm_plans_api's press: a run hours counter, 1 decimal)
and its plan through POST /api/pm/plans as an engineer, saved past due or inside its window, so the save makes the
job (S099's pattern).  The run (``generate``) settles every plan of the worker's database, so a test that runs it
first deactivates the others (``alone``).
"""

import threading
import time
from datetime import timedelta

import config
from local_db import get_local_db
from pm_jobs_core import RESCHEDULE_DROPPED
from pm_schedule_core import add_interval
from pm_work_core import (
    BEFORE_USE_NO_MOVE, JOB_DONE, JOB_SKIPPED, MOVE_REASON, NO_CALENDAR, NO_METER, NO_READING_YET, NOTHING_MOVED,
    REMARK_TOO_LONG, SKIP_REASON, STARTED_NO_MOVE, meter_not_above, meter_too_far,
)
from tests.test_pm_generate import add_reading, alone, db_now, events_of, generate, jobs_of, overdue, upcoming
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, SCRAPPED, _ok, add_model_meter, at_site, change, create, eng, engineer_a, hours, item_body, meter_of, oil,
    other_site, press, site,
)
from tests.test_pm_verify_api import job_row, line_of
from tests.test_pm_work_api import (  # noqa: F401 — the tech fixture
    JOBS, done, fill, page, plan_with, refusal, start, tech,
)
from tickets_core import LABOUR_DATE_FORMAT, PLANNED_DATE_PAST, PLANNED_DATE_TOO_FAR

REASON = "Planned shutdown next week"
SKIP = "Machine idle all month"


def today(db_rows):
    return db_now(db_rows).date()


def day(db_rows, days):
    return (today(db_rows) + timedelta(days=days)).isoformat()


def reschedule(client, job_id, status=200, remark=REASON, **body):
    return _ok(client.post(f"{JOBS}/{job_id}/reschedule", json={"remark": remark, **body}), status)


def skip(client, job_id, status=200, remark=SKIP):
    return _ok(client.post(f"{JOBS}/{job_id}/skip", json={"remark": remark}), status)


def moved(client, job_id, **body):
    """The reschedule's refusal -> (status, field, message)."""
    return refusal(client.post(f"{JOBS}/{job_id}/reschedule", json={"remark": REASON, **body}))


def listed(client, job_id, **query):
    body = _ok(client.get(JOBS, query_string=query))
    return next((item for item in body["items"] if item["id"] == job_id), None)


def meter_plan(engineer, node, hours, db_rows, value="1230", **fields):
    """A meter plan every 250 h from 1000 h, with a reading of ``value`` 2 hours ago: in its window (1225–1250), so
    the save makes the job, due at 1250 h -> (plan, job row)."""
    add_reading(db_rows, node, hours, value, db_now(db_rows) - timedelta(hours=2))
    plan = create(engineer, node, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                  **meter_of(node, hours), meter_every="250", last_done_meter="1000", **fields)
    (job,) = jobs_of(db_rows, plan["id"])
    return plan, job


def both_plan(engineer, node, hours, db_rows, reading="1230"):
    """A plan every 30 days or 250 h, due 10 days ago (Overdue) and at 1250 h -> (plan, job row).  ``reading`` None:
    the meter has no reading, so the job has no due meter value (S095 D9)."""
    if reading is not None:
        add_reading(db_rows, node, hours, reading, db_now(db_rows) - timedelta(hours=2))
    plan = create(engineer, node, trigger_kind="both", **overdue(db_rows), **meter_of(node, hours),
                  meter_every="250", **({"last_done_meter": "1000"} if reading is not None else {}))
    (job,) = jobs_of(db_rows, plan["id"])
    return plan, job


# ---------------------------------------------------------------------------
# Reschedule (§ 5.3)
# ---------------------------------------------------------------------------

class TestReschedule:

    def test_a_calendar_move_and_a_second_one(self, eng, press, db_rows):
        engineer, person = eng
        plan, job = plan_with(engineer, press, db_rows, items=[CHECK])
        old = job["due_on"].isoformat()
        body = reschedule(engineer, job["id"], due_on=day(db_rows, 10), remark=" Planned shutdown next week ")
        row = job_row(db_rows, job["id"])
        assert (row["due_on"].isoformat(), row["rescheduled_on"].isoformat()) == (day(db_rows, 10), day(db_rows, 10))
        assert (row["grace_days"], row["upcoming_days"], row["rescheduled_meter"]) == (
            job["grace_days"], job["upcoming_days"], None)
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["due_on"].isoformat(), line["remark"], line["person_id"]) == (
            "rescheduled", day(db_rows, 10), REASON, person["id"])
        assert (line["from_state"], line["to_state"]) == (None, None)
        assert (body["state"], body["rescheduled"], body["due_on"]) == ("due", True, day(db_rows, 10))
        assert body["standing"]["state"] == "not_yet"
        assert body["reschedule"] == {"count": 1, "was_due_on": old, "was_due_meter": None}
        assert line_of(body, "rescheduled")["person"] == {"id": person["id"], "name": person["name"]}
        assert listed(engineer, job["id"], tab="upcoming")["rescheduled"] is True
        again = reschedule(engineer, job["id"], due_on=day(db_rows, 20))
        assert again["reschedule"] == {"count": 2, "was_due_on": old, "was_due_meter": None}
        assert job_row(db_rows, job["id"])["rescheduled_on"].isoformat() == day(db_rows, 20)

    def test_earlier_is_allowed(self, engineer_a, press, db_rows):
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        later = reschedule(engineer_a, job["id"], due_on=day(db_rows, 20))
        assert reschedule(engineer_a, later["id"], due_on=day(db_rows, 0))["due_on"] == day(db_rows, 0)

    def test_a_meter_move(self, engineer_a, press, hours, db_rows):
        _, job = meter_plan(engineer_a, press, hours, db_rows)
        body = reschedule(engineer_a, job["id"], due_meter="1300")
        row = job_row(db_rows, job["id"])
        assert (str(row["due_meter"]), str(row["rescheduled_meter"]), row["rescheduled_on"]) == (
            "1300.000", "1300.000", None)
        assert (body["due_meter"], body["rescheduled"]) == ("1300", True)
        assert body["reschedule"] == {"count": 1, "was_due_on": None, "was_due_meter": "1250"}
        assert line_of(body, "rescheduled")["due_meter"] == "1300"

    def test_a_both_plan_moves_one_trigger_then_the_other(self, engineer_a, press, hours, db_rows):
        _, job = both_plan(engineer_a, press, hours, db_rows)
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 5))
        row = job_row(db_rows, job["id"])
        assert (row["rescheduled_on"].isoformat(), row["rescheduled_meter"], str(row["due_meter"])) == (
            day(db_rows, 5), None, "1250.000")                         # the meter stays computed
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 5), due_meter="1400")
        row = job_row(db_rows, job["id"])
        assert (row["due_on"].isoformat(), row["rescheduled_on"].isoformat(), str(row["rescheduled_meter"])) == (
            day(db_rows, 5), day(db_rows, 5), "1400.000")              # the earlier date move stays

    def test_the_run_keeps_it(self, engineer_a, press, db_rows):
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 10))
        alone(db_rows, plan["id"])
        lines = len(events_of(db_rows, job["id"]))
        generate()
        assert len(events_of(db_rows, job["id"])) == lines
        assert job_row(db_rows, job["id"])["due_on"].isoformat() == day(db_rows, 10)

    def test_a_title_change_keeps_it_and_a_schedule_change_drops_it(self, engineer_a, press, db_rows):
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 10))
        lines = len(events_of(db_rows, job["id"]))
        change(engineer_a, plan, title="Monthly hydraulic check, moved")
        assert job_row(db_rows, job["id"])["rescheduled_on"].isoformat() == day(db_rows, 10)
        assert len(events_of(db_rows, job["id"])) == lines
        change(engineer_a, plan, calendar_every=20)
        row = job_row(db_rows, job["id"])
        last_done = today(db_rows) - timedelta(days=40)                   # overdue()'s seed
        assert (row["rescheduled_on"], row["due_on"]) == (None, last_done + timedelta(days=20))
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["due_on"], line["remark"]) == ("due_changed", row["due_on"], RESCHEDULE_DROPPED)
        body = page(engineer_a, job["id"])
        assert (body["rescheduled"], body["reschedule"]["count"]) == (False, 1)   # the count is the history

    def test_a_schedule_change_that_keeps_the_due_point_still_drops_it(self, engineer_a, press, hours, db_rows):
        """§ 5.4: the due_changed line is written when only the reschedule columns change.  The job is moved away
        and back to its computed date, then the plan gains a meter with no reading: the date stays."""
        plan = create(engineer_a, press, items=[CHECK], **upcoming(db_rows))   # due in 2 days
        (job,) = jobs_of(db_rows, plan["id"])
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 5))
        reschedule(engineer_a, job["id"], due_on=job["due_on"].isoformat())
        assert job_row(db_rows, job["id"])["rescheduled_on"] == job["due_on"]
        change(engineer_a, plan, trigger_kind="both", **meter_of(press, hours), meter_every="250")
        row = job_row(db_rows, job["id"])
        assert (row["rescheduled_on"], row["due_on"], row["due_meter"]) == (None, job["due_on"], None)
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["due_on"], line["remark"]) == ("due_changed", job["due_on"], RESCHEDULE_DROPPED)

    def test_a_schedule_change_saved_with_an_item_edit_still_drops_it(self, engineer_a, press, db_rows):
        """CR1-01: the item's changes must not stand in for the plan's own."""
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 10))
        item = {**item_body(plan["items"][0]), "text": "Oil level is above min, checked cold"}
        change(engineer_a, plan, calendar_every=20, items=[item])
        row = job_row(db_rows, job["id"])
        assert row["rescheduled_on"] is None
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["remark"]) == ("due_changed", RESCHEDULE_DROPPED)

    def test_an_item_only_edit_keeps_it_also_a_reading_items_meter(self, engineer_a, press, oil, db_rows):
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK, {"item_type": "reading", "text": "Oil temp",
                                                                          "unit": "°C"}])
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 10))
        lines = len(events_of(db_rows, job["id"]))
        check, reading = (item_body(item) for item in plan["items"])
        change(engineer_a, plan, items=[{**check, "text": "Oil level is above min, checked cold"},
                                        {**reading, "reading_kind": "meter", "meter_type_id": oil["id"],
                                         "unit": None}])
        assert job_row(db_rows, job["id"])["rescheduled_on"].isoformat() == day(db_rows, 10)
        assert len(events_of(db_rows, job["id"])) == lines

    def test_on_time_against_the_new_date(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])      # due 10 days ago: late if done now
        reschedule(engineer_a, job["id"], due_on=day(db_rows, 5))
        body = start(client, job["id"], person)
        fill(client, job["id"], body["items"][0]["id"], outcome="ok")
        assert done(client, job["id"])["timeliness"] == "on_time"


class TestRescheduleRefusals:

    def test_the_value_refusals(self, engineer_a, press, hours, make_equipment, unit, add_model_meter, db_rows):
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 10), remark="  ") == (400, "remark", MOVE_REASON)
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 10), remark="x" * 501) == (
            400, "remark", REMARK_TOO_LONG)
        assert moved(engineer_a, job["id"], due_on=day(db_rows, -1)) == (400, "due_on", PLANNED_DATE_PAST)
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 366)) == (400, "due_on", PLANNED_DATE_TOO_FAR)
        assert moved(engineer_a, job["id"], due_on="12-11-2026") == (400, "due_on", LABOUR_DATE_FORMAT)
        assert moved(engineer_a, job["id"], due_meter="1300") == (400, "due_meter", NO_METER)
        assert moved(engineer_a, job["id"]) == (400, "due_on", NOTHING_MOVED)
        assert moved(engineer_a, job["id"], due_on=job["due_on"].isoformat()) == (400, "due_on", NOTHING_MOVED)
        meter_node = make_equipment(unit=unit)
        add_model_meter(meter_node, hours)
        _, meter_job = meter_plan(engineer_a, meter_node, hours, db_rows)
        assert moved(engineer_a, meter_job["id"], due_on=day(db_rows, 5)) == (400, "due_on", NO_CALENDAR)
        assert moved(engineer_a, meter_job["id"], due_meter="1230") == (
            400, "due_meter", meter_not_above("1,230 h"))
        assert moved(engineer_a, meter_job["id"], due_meter="1480.1") == (400, "due_meter", meter_too_far("1,480 h"))
        assert moved(engineer_a, meter_job["id"], due_meter="1250") == (400, "due_meter", NOTHING_MOVED)
        for job_id in (job["id"], meter_job["id"]):
            assert [e["event"] for e in events_of(db_rows, job_id)] == ["created"]
            assert job_row(db_rows, job_id)["rescheduled_on"] is None

    def test_no_reading_yet(self, engineer_a, press, hours, db_rows):
        _, job = both_plan(engineer_a, press, hours, db_rows, reading=None)
        assert job["due_meter"] is None
        assert moved(engineer_a, job["id"], due_meter="300") == (400, "due_meter", NO_READING_YET)
        assert reschedule(engineer_a, job["id"], due_on=day(db_rows, 4))["rescheduled"] is True

    def test_the_state_refusals(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, started = plan_with(engineer_a, press, db_rows, items=[CHECK], title="Started check")
        body = start(client, started["id"], person)
        assert moved(engineer_a, started["id"], due_on=day(db_rows, 5)) == (409, None, STARTED_NO_MOVE)
        fill(client, started["id"], body["items"][0]["id"], outcome="ok")
        done(client, started["id"])
        assert moved(engineer_a, started["id"], due_on=day(db_rows, 5)) == (409, None, JOB_DONE)
        assert refusal(engineer_a.post(f"{JOBS}/{started['id']}/skip", json={"remark": SKIP})) == (
            409, None, JOB_DONE)
        _, skipped = plan_with(engineer_a, press, db_rows, items=[CHECK], title="Skipped check")
        skip(engineer_a, skipped["id"])
        assert moved(engineer_a, skipped["id"], due_on=day(db_rows, 5)) == (409, None, JOB_SKIPPED)

    def test_a_scrapped_machine(self, engineer_a, press, db_rows):
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (press["id"],))
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 5)) == (409, None, SCRAPPED)
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/skip", json={"remark": SKIP})) == (409, None, SCRAPPED)
        body = page(engineer_a, job["id"])
        assert (body["can_reschedule"], body["can_skip"]) == (False, False)

    def test_who(self, engineer_a, press, tech, at_site, role_client, user_at_sites, other_site, db_rows):
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        for client in (tech[0], role_client("it_admin")):
            assert client.post(f"{JOBS}/{job['id']}/reschedule", json={"due_on": day(db_rows, 5),
                                                                       "remark": REASON}).status_code == 403
            assert client.post(f"{JOBS}/{job['id']}/skip", json={"remark": SKIP}).status_code == 403
            assert (page(client, job["id"])["can_reschedule"], page(client, job["id"])["can_skip"]) == (False, False)
        stranger, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert stranger.post(f"{JOBS}/{job['id']}/skip", json={"remark": SKIP}).status_code == 404
        assert engineer_a.post(f"{JOBS}/999999999/reschedule", json={"remark": REASON}).status_code == 404
        manager = at_site("maint_manager")
        assert reschedule(manager, job["id"], due_on=day(db_rows, 5))["rescheduled"] is True
        assert (page(engineer_a, job["id"])["can_reschedule"], page(engineer_a, job["id"])["can_skip"]) == (
            True, True)
        assert job_row(db_rows, job["id"])["state"] == "due"

    def test_the_before_use_guard(self, engineer_a, press, db_rows):
        """BR1-03: the plan routes refuse before_use until R03.13, so the plan's row is written straight."""
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        # S104: the trigger is the template's, the seed the plan row's
        db_rows("UPDATE pm_templates SET trigger_kind = 'before_use', calendar_every = NULL, calendar_unit = NULL"
                " WHERE id = %s", (plan["template"]["id"],))
        db_rows("UPDATE pm_plans SET last_done_on = NULL WHERE id = %s", (plan["id"],))
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 5)) == (409, None, BEFORE_USE_NO_MOVE)
        body = page(engineer_a, job["id"])
        assert (body["can_reschedule"], body["can_skip"]) == (False, True)
        assert skip(engineer_a, job["id"])["state"] == "skipped"
        assert len(jobs_of(db_rows, plan["id"])) == 1                     # a before-use plan makes no job


# ---------------------------------------------------------------------------
# Skip (§ 5.3)
# ---------------------------------------------------------------------------

class TestSkip:

    def test_a_skip_and_its_record(self, eng, press, hours, db_rows):
        engineer, person = eng
        plan, job = meter_plan(engineer, press, hours, db_rows)
        body = skip(engineer, job["id"], remark=" Machine idle all month ")
        row = job_row(db_rows, job["id"])
        assert (row["state"], row["open_plan_id"], row["timeliness"], row["needs_verification"]) == (
            "skipped", None, None, None)
        assert (row["done_at"].second, str(row["done_meter"])) == (0, "1230.000")
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["remark"], line["person_id"]) == (
            "skipped", "due", "skipped", SKIP, person["id"])
        assert line["occurred_at"] == row["done_at"]
        assert (body["state"], body["can_skip"], body["can_reschedule"], body["can_start"], body["items"]) == (
            "skipped", False, False, False, [])
        assert body["skipped"] == {"at": body["skipped"]["at"], "by_name": person["name"], "remark": SKIP}
        # The next job counts from the skip by meter: due at 1480 h, not in its window at 1230 h: no job yet
        assert len(jobs_of(db_rows, plan["id"])) == 1
        cards = _ok(engineer.get("/api/pm/plans", query_string={"equipment_id": press["id"]}))["items"]
        (card,) = [item for item in cards if item["id"] == plan["id"]]
        assert card["schedule"]["next_due"]["due_meter"] == "1480"

    def test_a_daily_plan_gets_its_next_job_at_once(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, items=[CHECK], calendar_every=1, calendar_unit="day",
                      last_done_on=day(db_rows, -3))
        (job,) = jobs_of(db_rows, plan["id"])
        skip(engineer_a, job["id"])
        jobs = jobs_of(db_rows, plan["id"])
        assert [j["state"] for j in jobs] == ["skipped", "due"]
        assert jobs[1]["due_on"].isoformat() == day(db_rows, 1)

    def test_a_monthly_plan_counts_a_month_from_the_skip(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, items=[CHECK], calendar_every=1, calendar_unit="month",
                      last_done_on=day(db_rows, -40))
        (job,) = jobs_of(db_rows, plan["id"])
        skip(engineer_a, job["id"])
        assert len(jobs_of(db_rows, plan["id"])) == 1
        skipped_on = job_row(db_rows, job["id"])["done_at"].date()
        cards = _ok(engineer_a.get("/api/pm/plans", query_string={"equipment_id": press["id"]}))["items"]
        (card,) = [item for item in cards if item["id"] == plan["id"]]
        assert card["schedule"]["next_due"]["due_on"] == add_interval(skipped_on, 1, "month").isoformat()

    def test_the_done_tab(self, engineer_a, make_equipment, unit, tech, db_rows):
        client, person = tech
        final = create(engineer_a, make_equipment(unit=unit), items=[CHECK], needs_verification=False,
                       **overdue(db_rows))
        (done_job,) = jobs_of(db_rows, final["id"])
        body = start(client, done_job["id"], person)
        fill(client, done_job["id"], body["items"][0]["id"], outcome="ok")
        done(client, done_job["id"])
        _, job = plan_with(engineer_a, make_equipment(unit=unit), db_rows, items=[CHECK])
        skip(engineer_a, job["id"])
        tab = _ok(engineer_a.get(JOBS, query_string={"tab": "done"}))
        assert [item["id"] for item in tab["items"]] == [job["id"], done_job["id"]]   # newest first
        assert (tab["total"], tab["total_skipped"]) == (2, 1)
        item = tab["items"][0]
        assert (item["state"], item["timeliness"], item["skipped"]["remark"]) == ("skipped", None, SKIP)
        assert tab["items"][1]["skipped"] is None
        mine = _ok(engineer_a.get(JOBS, query_string={"tab": "done", "unit_id": unit["id"]}))
        assert (mine["total"], mine["total_skipped"]) == (2, 1)
        other = _ok(engineer_a.get(JOBS, query_string={"tab": "done", "unit_id": unit["id"] + 100000}))
        assert (other["total"], other["total_skipped"]) == (0, 0)
        assert "total_skipped" not in _ok(engineer_a.get(JOBS, query_string={"tab": "to_verify"}))

    def test_the_refusals(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        for remark in (None, "", "   "):
            assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/skip", json={"remark": remark})) == (
                400, "remark", SKIP_REASON)
        assert job_row(db_rows, job["id"])["state"] == "due"
        skip(engineer_a, job["id"])
        assert refusal(engineer_a.post(f"{JOBS}/{job['id']}/skip", json={"remark": SKIP})) == (409, None, JOB_SKIPPED)
        assert refusal(client.post(f"{JOBS}/{job['id']}/start", json={"performed_by_id": person["id"]})) == (
            409, None, JOB_SKIPPED)
        _, started = plan_with(engineer_a, press, db_rows, items=[CHECK], title="Started check")
        start(client, started["id"], person)
        assert refusal(engineer_a.post(f"{JOBS}/{started['id']}/skip", json={"remark": SKIP})) == (
            409, None, STARTED_NO_MOVE)

    def test_a_login_with_no_person(self, engineer_a, press, keycloak_admin, db_rows):
        """S098 § 6.2: the line has no person; created_by holds the login, and the page names it."""
        _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        body = skip(keycloak_admin, job["id"])
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["person_id"]) == ("skipped", None)
        assert body["skipped"]["by_name"] == line["created_by"]
        assert line_of(body, "skipped")["created_by_name"] == line["created_by"]


# ---------------------------------------------------------------------------
# The lock (§ 5.6), the database down
# ---------------------------------------------------------------------------

class TestLock:

    def test_the_skip_waits_for_the_plan_lock(self, engineer_a, press, db_rows):
        """BR1-09: (6e) is taken first: with the plan's row held by another connection, the skip waits; a reschedule
        after it reads the skipped job."""
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        conn = get_local_db(config.DB_CONFIG)
        result = {}
        try:
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM pm_plans WHERE id = %s FOR UPDATE", (plan["id"],))
                worker = threading.Thread(
                    target=lambda: result.update(res=engineer_a.post(f"{JOBS}/{job['id']}/skip",
                                                                     json={"remark": SKIP})))
                worker.start()
                time.sleep(1)
                assert worker.is_alive(), "the skip did not wait for the plan lock"
                cur.execute("COMMIT")
            worker.join(timeout=30)
        finally:
            conn.close()
        assert result["res"].status_code == 200
        assert job_row(db_rows, job["id"])["state"] == "skipped"
        assert moved(engineer_a, job["id"], due_on=day(db_rows, 5)) == (409, None, JOB_SKIPPED)

    def test_the_database_down(self, engineer_a, db_down):
        assert engineer_a.post(f"{JOBS}/1/reschedule", json={"remark": REASON}).status_code == 503
        assert engineer_a.post(f"{JOBS}/1/skip", json={"remark": SKIP}).status_code == 503
