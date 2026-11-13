"""The PM list, the card's schedule and the plan save's job (S097 § 5.5, § 5.8, § 6, § 8.2), against the test DB.
Needs the dev MariaDB container.

Each test makes its own site, unit, model and machine.  A plan saved inside its window gets its job at the save
(D5); day intervals keep the dates plain: every 30 days (upcoming 3, grace 3), last done 40 days ago -> due 10 days
ago, *Overdue*; last done 28 days ago -> due in 2 days, *Upcoming*.  Each test finds its own rows by plan id (the
worker database holds other tests' jobs).
"""

from datetime import datetime, timedelta

import pytest

from pm_jobs_core import CANCELLED_EVENT, TEMPLATE_INACTIVE_REMARK
from tests.test_pm_generate import (
    _today, add_reading, db_now, events_of, fix_now, jobs_of, overdue, upcoming,
)
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, _ok, add_model_meter, at_site, change, create, eng, engineer_a, hours, item_body, meter_of, oil,
    other_site, other_unit, press, site,
)
from tests.test_pm_work_api import done, fill, minute, start

JOBS = "/api/pm/jobs"
PLANS = "/api/pm/plans"


def listed(client, plan, **query):
    """The list's item of ``plan``'s job, or None."""
    body = _ok(client.get(JOBS, query_string=query))
    return next((item for item in body["items"] if item["plan"]["id"] == plan["id"]), None)


@pytest.fixture
def tech(user_at_sites, site):
    """(client, person): a technician with a login at every unit of the machine's site."""
    return user_at_sites([(site, "maint_technician", "all")])


# ---------------------------------------------------------------------------
# GET /api/pm/jobs
# ---------------------------------------------------------------------------

class TestList:

    def test_the_operator_sees_the_overdue_job(self, engineer_a, press, at_site, tech, db_rows, unit):
        _, person = tech
        plan = create(engineer_a, press, assignee_id=person["id"], **overdue(db_rows))
        item = listed(at_site("maint_operator"), plan)
        (job,) = jobs_of(db_rows, plan["id"])
        today = _today(db_rows)
        assert item == {
            "id": job["id"], "serial": job["serial"], "state": "due",
            "standing": {"state": "overdue", "trigger": "calendar", "no_reading": False},
            "due_on": (today - timedelta(days=10)).isoformat(), "due_meter": None, "days_past": 10,
            "created_why": "calendar",
            "equipment": {"id": press["id"], "code": press["code"], "name": press["name"]},
            "plan": {"id": plan["id"], "title": plan["title"], "item_count": 2, "performer": "maintenance",
                     "template_id": plan["template"]["id"]},
            "unit": {"id": unit["id"], "full_code": f"{unit['site_code']}.{unit['code']}"},
            "site_code": unit["site_code"], "assignee": {"id": person["id"], "name": person["name"]},
            "performed_by": None, "started_at": None, "done_at": None, "timeliness": None,   # S098
            "meter": None, "created_at": item["created_at"],
            "needs_verification": None, "awaits_verification": False,                      # S099
            "findings": None, "verification": None, "sent_back": None,
            "rescheduled": False, "skipped": None,                                          # S101
        }

    def test_another_site_s_technician_does_not_see_it(self, engineer_a, press, user_at_sites, other_site, db_rows):
        plan = create(engineer_a, press, **overdue(db_rows))
        client, _ = user_at_sites([(other_site, "maint_technician", "all")])
        assert listed(client, plan) is None

    def test_the_storekeeper_is_refused(self, at_site):
        assert at_site("maint_storekeeper").get(JOBS).status_code == 403

    def test_it_admin_reads_every_unit(self, engineer_a, press, role_client, db_rows):
        plan = create(engineer_a, press, **overdue(db_rows))
        assert listed(role_client("it_admin"), plan) is not None

    def test_the_unit_filter(self, engineer_a, press, unit, other_unit, db_rows):
        plan = create(engineer_a, press, **overdue(db_rows))
        assert listed(engineer_a, plan, unit_id=unit["id"]) is not None
        assert listed(engineer_a, plan, unit_id=other_unit["id"]) is None

    def test_assigned_to_me(self, engineer_a, press, tech, user_at_sites, site, role_client, db_rows):
        client, person = tech
        plan = create(engineer_a, press, assignee_id=person["id"], **overdue(db_rows))
        assert listed(client, plan, assigned="me") is not None
        other, _ = user_at_sites([(site, "maint_technician", "all")])
        assert listed(other, plan, assigned="me") is None
        assert listed(other, plan) is not None
        no_team_record = role_client("maint_technician")
        assert _ok(no_team_record.get(JOBS, query_string={"assigned": "me"}))["items"] == []

    def test_the_upcoming_tab_and_the_counts(self, engineer_a, make_equipment, unit, db_rows, alone_here):
        soon = create(engineer_a, make_equipment(unit=unit), **upcoming(db_rows))
        pushed = create(engineer_a, make_equipment(unit=unit), **upcoming(db_rows))
        change(engineer_a, pushed, calendar_every=60)                    # D17: stays open, *Not yet due*
        late = create(engineer_a, make_equipment(unit=unit), **overdue(db_rows))
        alone_here(soon, pushed, late)
        upcoming_items = _ok(engineer_a.get(JOBS, query_string={"tab": "upcoming"}))
        assert [i["standing"]["state"] for i in upcoming_items["items"]] == ["upcoming", "not_yet"]
        assert [i["plan"]["id"] for i in upcoming_items["items"]] == [soon["id"], pushed["id"]]
        due_items = _ok(engineer_a.get(JOBS))
        assert [i["plan"]["id"] for i in due_items["items"]] == [late["id"]]
        assert due_items["counts"] == upcoming_items["counts"] == {"overdue": 1, "due": 0, "upcoming": 2,
                                                                         "in_progress": 0, "to_verify": 0}

    def test_an_unknown_tab_is_refused(self, engineer_a):
        res = engineer_a.get(JOBS, query_string={"tab": "nonsense"})
        assert res.status_code == 400 and res.get_json()["error"] == (
            "tab must be one of: due, upcoming, to_verify, done")

    def test_the_database_down(self, engineer_a, db_down):
        assert engineer_a.get(JOBS).status_code == 503


@pytest.fixture
def alone_here(db_rows):
    """Only these plans' jobs open: the others' due jobs cancelled straight (the counts are over every unit the
    engineer reads, which holds only this test's site)."""
    def keep(*plans):
        ids = [plan["id"] for plan in plans]
        db_rows(f"UPDATE pm_jobs SET state = 'cancelled' WHERE state = 'due'"
                f" AND plan_id NOT IN ({', '.join(['%s'] * len(ids))})", ids)
    return keep


class TestStartedAndDone:
    """S098 § 5.9, § 6.3: a started job sits on *Due*, first; the *Done* tab; *Assigned to me* takes the performer."""

    def _start(self, client, plan, person, db_rows):
        (job,) = jobs_of(db_rows, plan["id"])
        return start(client, job["id"], person)

    def test_a_started_upcoming_job_is_on_due_and_counted_apart(self, engineer_a, make_equipment, unit, tech,
                                                                 db_rows, alone_here):
        client, person = tech
        soon = create(engineer_a, make_equipment(unit=unit), **upcoming(db_rows))
        late = create(engineer_a, make_equipment(unit=unit), **overdue(db_rows))
        alone_here(soon, late)
        self._start(client, soon, person, db_rows)
        due_items = _ok(engineer_a.get(JOBS))
        assert [(i["plan"]["id"], i["state"]) for i in due_items["items"]] == [
            (soon["id"], "in_progress"), (late["id"], "due")]                   # started first
        assert due_items["items"][0]["performed_by"] == {"id": person["id"], "name": person["name"]}
        assert due_items["items"][0]["started_at"] is not None
        assert listed(engineer_a, soon, tab="upcoming") is None
        assert due_items["counts"] == {"overdue": 1, "due": 0, "upcoming": 0, "in_progress": 1, "to_verify": 0}

    def test_a_started_job_counts_its_own_items(self, engineer_a, press, tech, db_rows):
        """CR1-03: an item added to the plan after Start is not the started job's."""
        client, person = tech
        plan = create(engineer_a, press, **overdue(db_rows))
        self._start(client, plan, person, db_rows)
        items = [item_body(item) for item in plan["items"]] + [{"item_type": "task", "text": "Check the filter"}]
        change(engineer_a, plan, items=items)
        assert listed(engineer_a, plan)["plan"]["item_count"] == 2

    def test_assigned_to_me_takes_the_performer(self, engineer_a, press, tech, user_at_sites, site, db_rows):
        client, person = tech
        assignee_client, assignee = user_at_sites([(site, "maint_technician", "all")])
        plan = create(engineer_a, press, assignee_id=assignee["id"], **overdue(db_rows))
        assert listed(client, plan, assigned="me") is None
        self._start(client, plan, person, db_rows)
        assert listed(client, plan, assigned="me") is not None                 # performed by me
        assert listed(assignee_client, plan, assigned="me") is not None        # still assigned to him

    def test_the_done_tab_newest_first_and_paged(self, engineer_a, make_equipment, unit, tech, db_rows):
        client, person = tech
        # S099 BS1-06: final at done (no verification), so the jobs stay on *Done*
        plans = [create(engineer_a, make_equipment(unit=unit), items=[CHECK], needs_verification=False,
                        **overdue(db_rows)) for _ in range(2)]
        for plan in plans:
            job = self._start(client, plan, person, db_rows)
            fill(client, job["id"], job["items"][0]["id"], outcome="ok")
            done(client, job["id"])
        body = _ok(engineer_a.get(JOBS, query_string={"tab": "done"}))
        assert [i["plan"]["id"] for i in body["items"]] == [plans[1]["id"], plans[0]["id"]]
        assert (body["total"], body["page"], body["per_page"]) == (2, 1, 50)
        item = body["items"][0]
        assert (item["state"], item["standing"], item["days_past"], item["timeliness"]) == ("done", None, None, "late")
        assert item["performed_by"]["id"] == person["id"] and item["done_at"] is not None
        assert body["counts"]["in_progress"] == 0
        page_two = _ok(engineer_a.get(JOBS, query_string={"tab": "done", "per_page": 1, "page": 2}))
        assert (page_two["total"], [i["plan"]["id"] for i in page_two["items"]]) == (2, [plans[0]["id"]])
        assert _ok(engineer_a.get(JOBS, query_string={"tab": "done", "unit_id": unit["id"] + 100000}))["total"] == 0


class TestToVerify:
    """S099 § 5.7, § 6.3: *To verify* lists the jobs waiting for verification, the oldest done first; *Done* only the
    finished ones (verified, or final at done); ``counts.to_verify`` on every tab."""

    def _done_at(self, client, person, engineer, node, db_rows, hours_ago, **plan_fields):
        """A Check-only plan's job started 3 hours ago and done ``hours_ago`` -> (plan, the job's page answer)."""
        plan = create(engineer, node, items=[CHECK], **overdue(db_rows), **plan_fields)
        (job,) = jobs_of(db_rows, plan["id"])
        now = db_now(db_rows).replace(second=0, microsecond=0)
        body = start(client, job["id"], person, started_at=minute(now - timedelta(hours=3)))
        fill(client, job["id"], body["items"][0]["id"], outcome="ok")
        return plan, done(client, job["id"], done_at=minute(now - timedelta(hours=hours_ago)))

    def test_the_waiting_jobs_oldest_done_first_and_paged(self, engineer_a, make_equipment, unit, tech, db_rows):
        client, person = tech
        newer, _ = self._done_at(client, person, engineer_a, make_equipment(unit=unit), db_rows, 1)
        older, _ = self._done_at(client, person, engineer_a, make_equipment(unit=unit), db_rows, 2)
        final, _ = self._done_at(client, person, engineer_a, make_equipment(unit=unit), db_rows, 1,
                                 needs_verification=False)
        body = _ok(engineer_a.get(JOBS, query_string={"tab": "to_verify"}))
        assert [i["plan"]["id"] for i in body["items"]] == [older["id"], newer["id"]]
        assert (body["total"], body["counts"]["to_verify"]) == (2, 2)
        item = body["items"][0]
        assert (item["awaits_verification"], item["needs_verification"], item["verification"]) == (True, True, None)
        assert item["findings"] == {"not_ok": 0, "not_done": 0, "out_of_limits": 0}
        one = _ok(engineer_a.get(JOBS, query_string={"tab": "to_verify", "per_page": 1}))
        assert (one["total"], [i["plan"]["id"] for i in one["items"]]) == (2, [older["id"]])
        assert _ok(engineer_a.get(JOBS))["counts"]["to_verify"] == 2                   # on the Due tab too
        done_tab = _ok(engineer_a.get(JOBS, query_string={"tab": "done"}))
        assert [i["plan"]["id"] for i in done_tab["items"]] == [final["id"]]

    def test_a_verified_job_and_one_done_before_s099_are_on_done(self, eng, make_equipment, unit, tech, db_rows):
        engineer_a, engineer = eng
        client, person = tech
        _, verified = self._done_at(client, person, engineer_a, make_equipment(unit=unit), db_rows, 2)
        _, old = self._done_at(client, person, engineer_a, make_equipment(unit=unit), db_rows, 1)
        _ok(engineer_a.post(f"{JOBS}/{verified['id']}/verify", json={}))
        db_rows("UPDATE pm_jobs SET needs_verification = NULL WHERE id = %s", (old["id"],))
        assert _ok(engineer_a.get(JOBS, query_string={"tab": "to_verify"}))["items"] == []
        done_tab = _ok(engineer_a.get(JOBS, query_string={"tab": "done"}))
        assert [i["id"] for i in done_tab["items"]] == [old["id"], verified["id"]]
        mine = done_tab["items"][1]
        assert (mine["state"], mine["verification"]["by_name"]) == ("verified", engineer["name"])
        assert (done_tab["items"][0]["needs_verification"], done_tab["items"][0]["verification"]) == (None, None)

    def test_a_sent_back_job_carries_sent_back_on_due(self, engineer_a, press, tech, db_rows):
        client, person = tech
        plan, job = self._done_at(client, person, engineer_a, press, db_rows, 1)
        _ok(engineer_a.post(f"{JOBS}/{job['id']}/send-back", json={"remark": "Re-tighten the left rod seal"}))
        item = listed(engineer_a, plan)
        assert (item["state"], item["sent_back"]["remark"], item["findings"]) == (
            "in_progress", "Re-tighten the left rod seal", None)
        assert listed(client, plan, assigned="me")["sent_back"] is not None             # Me › Open work


class TestMeterOnTheList:

    def _meter_plan(self, engineer_a, press, hours):
        return create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250", last_done_meter="1000")

    def test_a_reading_turns_the_upcoming_job_due_at_once(self, engineer_a, press, hours, at_site, db_rows):
        add_reading(db_rows, press, hours, "1230", db_now(db_rows) - timedelta(hours=2))
        plan = self._meter_plan(engineer_a, press, hours)
        item = listed(engineer_a, plan, tab="upcoming")
        assert item["standing"]["state"] == "upcoming" and item["due_meter"] == "1250"
        assert item["meter"]["value_now"] == "1230" and item["meter"]["value_counted"] == "1230"
        _ok(at_site("maint_operator").post(f"/api/equipment/{press['id']}/readings",
                                           json={"meter_type_id": hours["id"], "value": "1255"}), 201)
        item = listed(engineer_a, plan)                                  # no run: judged live (D4)
        assert item["standing"] == {"state": "due", "trigger": "meter", "no_reading": False}
        assert item["meter"]["value_now"] == "1255"

    def test_the_counted_value_adds_the_offset(self, engineer_a, press, hours, db_rows):
        add_reading(db_rows, press, hours, "1230", db_now(db_rows) - timedelta(hours=2))
        plan = self._meter_plan(engineer_a, press, hours)
        db_rows("UPDATE pm_jobs SET meter_offset = 100 WHERE plan_id = %s", (plan["id"],))
        item = listed(engineer_a, plan)
        assert (item["meter"]["value_now"], item["meter"]["offset"], item["meter"]["value_counted"]) == (
            "1230", "100", "1330")
        assert item["standing"]["state"] == "overdue"                    # 1,330 is past 1,250 + 25


# ---------------------------------------------------------------------------
# The plan save (D5)
# ---------------------------------------------------------------------------

class TestSave:

    def _username(self, db_rows, person):
        return db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"]

    def test_a_plan_saved_past_due_gets_its_job(self, eng, press, db_rows):
        client, person = eng
        plan = create(client, press, **overdue(db_rows))
        (job,) = jobs_of(db_rows, plan["id"])
        (line,) = events_of(db_rows, job["id"])
        assert (job["state"], line["event"], line["created_by"]) == ("due", "created", self._username(db_rows, person))

    def test_a_plan_far_from_due_gets_none(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press)
        assert jobs_of(db_rows, plan["id"]) == []

    def test_deactivate_cancels_and_reactivate_makes_a_new_job(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, **overdue(db_rows))
        change(engineer_a, plan, active=False)
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["state"] == "cancelled"
        assert [(e["event"], e["remark"]) for e in events_of(db_rows, job["id"])] == [
            ("created", None), (CANCELLED_EVENT, TEMPLATE_INACTIVE_REMARK)]
        change(engineer_a, plan, active=True)
        first, second = jobs_of(db_rows, plan["id"])
        assert second["state"] == "due" and second["serial"] != first["serial"]

    def test_a_shorter_interval_moves_the_due_date(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, **upcoming(db_rows))
        change(engineer_a, plan, calendar_every=29)
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["due_on"] == _today(db_rows) + timedelta(days=1)
        assert [(e["event"], e["due_on"]) for e in events_of(db_rows, job["id"])][1:] == [
            ("due_changed", _today(db_rows) + timedelta(days=1))]

    def test_a_new_assignee_follows_to_the_job(self, engineer_a, press, tech, db_rows):
        _, person = tech
        plan = create(engineer_a, press, **upcoming(db_rows))
        change(engineer_a, plan, assignee_id=person["id"])
        (job,) = jobs_of(db_rows, plan["id"])
        assert job["assignee_id"] == person["id"]
        assert [(e["event"], e["person_id"]) for e in events_of(db_rows, job["id"])][1:] == [
            ("assignee_changed", person["id"])]

    def test_a_change_of_nothing_writes_no_job_line(self, engineer_a, press, db_rows):
        plan = create(engineer_a, press, **upcoming(db_rows))
        change(engineer_a, plan, title=plan["title"])
        (job,) = jobs_of(db_rows, plan["id"])
        assert len(events_of(db_rows, job["id"])) == 1 and job["updated_at"] is None

    def test_a_refused_save_takes_no_serial(self, engineer_a, make_equipment, unit, db_rows, monkeypatch):
        node = make_equipment(unit=unit)
        first = create(engineer_a, node)                                  # under the real clock: no job
        fix_now(monkeypatch, datetime(2091, 8, 2, 9, 0))
        create(engineer_a, node, status=409, title=first["title"])        # S104: the template's name is taken
        # S104: a new plan counts from its link (now, the fixed clock), so its seed brings it past due
        second = create(engineer_a, node, title="Weekly lubrication", last_done_on=overdue(db_rows)["last_done_on"])
        assert jobs_of(db_rows, second["id"])[0]["serial"] == "PM-2091-08-001"


# ---------------------------------------------------------------------------
# The card's schedule (§ 6.3)
# ---------------------------------------------------------------------------

class TestCard:

    def test_the_open_job_and_the_next_due(self, engineer_a, press, at_site, db_rows):
        with_job = create(engineer_a, press, **overdue(db_rows))
        far = create(engineer_a, press, title="Quarterly check", calendar_every=3, calendar_unit="month")
        stopped = create(engineer_a, press, title="Old check")
        change(engineer_a, stopped, active=False)
        body = _ok(at_site("maint_technician").get(PLANS, query_string={"equipment_id": press["id"]}))
        items = {item["id"]: item for item in body["items"]}
        (job,) = jobs_of(db_rows, with_job["id"])
        open_job = items[with_job["id"]]["schedule"]["open_job"]
        assert open_job == {"id": job["id"], "serial": job["serial"], "state": "due",
                            "standing": {"state": "overdue", "trigger": "calendar", "no_reading": False},
                            "due_on": (_today(db_rows) - timedelta(days=10)).isoformat(), "due_meter": None,
                            "days_past": 10}
        assert items[with_job["id"]]["schedule"]["next_due"] is None
        schedule = items[far["id"]]["schedule"]
        assert schedule["open_job"] is None and schedule["meter"] is None
        assert schedule["next_due"]["due_on"] > _today(db_rows).isoformat()
        # S104: a deactivated template stops the plan; it stays on the card with its remark, no schedule line
        assert items[stopped["id"]]["schedule"] == {"open_job": None, "next_due": None, "meter": None}
        assert items[stopped["id"]]["stop_remark"] == TEMPLATE_INACTIVE_REMARK

    def test_the_storekeeper_gets_no_schedule(self, engineer_a, press, at_site, db_rows):
        create(engineer_a, press, **overdue(db_rows))
        body = _ok(at_site("maint_storekeeper").get(PLANS, query_string={"equipment_id": press["id"]}))
        assert [item["schedule"] for item in body["items"]] == [None]

    def test_a_meter_plan_with_no_base_says_no_reading(self, engineer_a, press, hours, db_rows):
        plan = create(engineer_a, press, trigger_kind="meter", calendar_every=None, calendar_unit=None,
                      **meter_of(press, hours), meter_every="250")
        body = _ok(engineer_a.get(PLANS, query_string={"equipment_id": press["id"]}))
        (item,) = [item for item in body["items"] if item["id"] == plan["id"]]
        assert item["schedule"]["next_due"] == {"due_on": None, "due_meter": None, "no_reading": True}
        assert item["schedule"]["meter"]["value_now"] is None
