"""Doing a PM job (S098 § 5, § 6, § 8.2): the job page, Start, an item's result, a reading that logs its meter, the
performer, Mark job done, and what S097's run and plan save do to a started job.  Needs the dev MariaDB container.

Each test makes its own site, unit, model and machine (the press of test_pm_plans_api: a run hours counter and an
oil temperature gauge 20–70 °C on its model) and its plan through POST /api/pm/plans as an engineer, saved past
due, so the save makes the job at once (S097 D5): every 30 days, last done 40 days ago, *Overdue*.
"""

import threading
import time
from datetime import timedelta
from decimal import Decimal

import pytest

import config
import pm_jobs
from local_db import get_local_db
from tests.test_pm_generate import add_reading, db_now, events_of, fix_now, generate, jobs_of, overdue
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, SCRAPPED, TASK, _ok, add_model_meter, add_own_meter, at_site, change, create, eng, engineer_a, hours,
    item_body, link_meter, meter_of, oil, other_site, other_unit, press, site,
)

JOBS = "/api/pm/jobs"
READING = {"item_type": "reading", "text": "Power-pack oil temperature", "unit": "°C", "min_value": "30",
           "max_value": "200"}


@pytest.fixture
def tech(user_at_sites, site):
    """(client, person): a technician with a login at every unit of the machine's site."""
    return user_at_sites([(site, "maint_technician", "all")])


@pytest.fixture
def ramesh(make_person, give_site_role, site):
    """An operator at the site without a login: recorded on behalf."""
    person = make_person(name="Ramesh")
    give_site_role(person, site, "maint_operator")
    return person


def plan_with(engineer, node, db_rows, items=None, **fields):
    """A plan saved past due (its job made at the save) with ``items`` -> (plan, job row)."""
    plan = create(engineer, node, items=items or [CHECK, TASK, READING], **overdue(db_rows), **fields)
    (job,) = jobs_of(db_rows, plan["id"])
    return plan, job


def page(client, job_id, status=200):
    return _ok(client.get(f"{JOBS}/{job_id}"), status)


def start(client, job_id, person, status=200, **fields):
    return _ok(client.post(f"{JOBS}/{job_id}/start", json={"performed_by_id": person["id"], "started_at": None,
                                                           **fields}), status)


def fill(client, job_id, result_id, status=200, **body):
    return _ok(client.put(f"{JOBS}/{job_id}/results/{result_id}", json=body), status)


def done(client, job_id, status=200, **body):
    return _ok(client.post(f"{JOBS}/{job_id}/done", json=body), status)


def refusal(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def results_of(db_rows, job_id):
    return list(db_rows("SELECT * FROM pm_job_results WHERE job_id = %s ORDER BY position", (job_id,)))


def readings_of(db_rows, node, meter_type):
    return list(db_rows("SELECT * FROM meter_readings WHERE equipment_id = %s AND meter_type_id = %s ORDER BY id",
                        (node["id"], meter_type["id"])))


def minute(moment):
    return moment.strftime("%Y-%m-%dT%H:%M")


def fill_all(client, job):
    """Fill every item of a started job's page answer (``job``): OK, Done, a reading of 45."""
    for item in job["items"]:
        body = {"check": {"outcome": "ok"}, "task": {"outcome": "done"}, "reading": {"value": "45"}}[item["item_type"]]
        fill(client, job["id"], item["id"], **body)


# ---------------------------------------------------------------------------
# The page (GET /api/pm/jobs/<id>)
# ---------------------------------------------------------------------------

class TestPage:

    def test_a_technician_reads_a_due_job_with_the_plan_s_items(self, engineer_a, press, tech, db_rows):
        client, _ = tech
        plan, job = plan_with(engineer_a, press, db_rows)
        body = page(client, job["id"])
        assert (body["serial"], body["state"], body["standing"]["state"]) == (job["serial"], "due", "overdue")
        assert (body["can_start"], body["can_work"], body["performed_by"], body["started_at"]) == (
            True, False, None, None)
        assert body["equipment"]["lifecycle"] == press["lifecycle"]
        assert body["plan"] == {"id": plan["id"], "title": plan["title"], "item_count": 3, "performer": "maintenance",
                                "template_id": plan["template"]["id"],
                                "active": True,
                                "needs_verification": plan["template"]["needs_verification"]}
        assert [(i["id"], i["template_item_id"], i["item_type"], i["outcome"]) for i in body["items"]] == [
            (None, plan["items"][0]["id"], "check", None), (None, plan["items"][1]["id"], "task", None),
            (None, plan["items"][2]["id"], "reading", None)]
        assert body["items"][2]["limits_text"] == "Measurement · 30–200 °C"
        assert (body["filled_count"], body["item_count"]) == (0, 3)
        assert [e["event"] for e in body["events"]] == ["created"]

    def test_the_operator_and_it_admin_read_it_and_cannot_start(self, engineer_a, press, at_site, role_client,
                                                                db_rows):
        _, job = plan_with(engineer_a, press, db_rows)
        assert page(at_site("maint_operator"), job["id"])["can_start"] is False
        assert page(role_client("it_admin"), job["id"])["can_start"] is False

    def test_another_site_the_storekeeper_and_a_missing_id(self, engineer_a, press, user_at_sites, other_site,
                                                           at_site, db_rows):
        _, job = plan_with(engineer_a, press, db_rows)
        elsewhere, _ = user_at_sites([(other_site, "maint_technician", "all")])
        assert elsewhere.get(f"{JOBS}/{job['id']}").status_code == 404
        assert at_site("maint_storekeeper").get(f"{JOBS}/{job['id']}").status_code == 403
        assert engineer_a.get(f"{JOBS}/99999999").status_code == 404


# ---------------------------------------------------------------------------
# Start (§ 5.3)
# ---------------------------------------------------------------------------

class TestStart:

    def test_start_copies_the_active_items_and_writes_the_event(self, engineer_a, press, tech, db_rows):
        client, person = tech
        plan = create(engineer_a, press, items=[CHECK, TASK, {**CHECK, "text": "Hose clamps tight"}],
                      assignee_id=person["id"], **overdue(db_rows))
        dropped = plan["items"][2]
        plan = change(engineer_a, plan, items=[item_body(item) for item in plan["items"][:2]])
        (job,) = jobs_of(db_rows, plan["id"])
        now = db_now(db_rows)
        body = start(client, job["id"], person)
        assert (body["state"], body["can_start"], body["can_work"]) == ("in_progress", False, True)
        assert body["performed_by"] == {"id": person["id"], "name": person["name"]}
        stored = jobs_of(db_rows, plan["id"])[0]
        assert stored["started_at"].second == 0 and abs(stored["started_at"] - now) < timedelta(minutes=2)
        assert stored["assignee_id"] == person["id"]                        # the job keeps its assignee
        results = results_of(db_rows, job["id"])
        assert [(r["template_item_id"], r["position"], r["text"]) for r in results] == [
            (plan["items"][0]["id"], 1, CHECK["text"]), (plan["items"][1]["id"], 2, TASK["text"])]
        assert dropped["id"] not in [r["template_item_id"] for r in results]   # an inactive item is left out
        assert all(r["outcome"] is None and r["filled_at"] is None for r in results)
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["person_id"], line["occurred_at"]) == (
            "started", "due", "in_progress", person["id"], stored["started_at"])

    def test_recorded_on_behalf_two_days_back(self, engineer_a, press, tech, ramesh, db_rows):
        client, _ = tech
        _, job = plan_with(engineer_a, press, db_rows)
        when = db_now(db_rows).replace(second=0, microsecond=0) - timedelta(days=2)
        body = start(client, job["id"], ramesh, started_at=minute(when))
        assert body["performed_by"] == {"id": ramesh["id"], "name": "Ramesh"}
        stored = db_rows("SELECT performed_by_id, started_at FROM pm_jobs WHERE id = %s", (job["id"],))[0]
        assert (stored["performed_by_id"], stored["started_at"]) == (ramesh["id"], when)

    def test_the_refusals(self, engineer_a, press, tech, make_person, give_site_role, other_site, db_rows):
        client, person = tech
        _, job = plan_with(engineer_a, press, db_rows)
        url = f"{JOBS}/{job['id']}/start"
        assert refusal(client.post(url, json={})) == (400, "performed_by_id", "Choose who did the work.")
        for bad in (True, "7", 0, None):
            assert refusal(client.post(url, json={"performed_by_id": bad}))[2] == "Choose who did the work."
        stranger = make_person(name="Elsewhere")
        give_site_role(stranger, other_site)
        assert refusal(client.post(url, json={"performed_by_id": stranger["id"]})) == (
            400, "performed_by_id", "Choose a person from this site")
        now = db_now(db_rows)
        assert refusal(client.post(url, json={"performed_by_id": person["id"],
                                              "started_at": minute(now - timedelta(days=8))})) == (
            400, "started_at", "Enter a time up to 7 days back.")
        assert refusal(client.post(url, json={"performed_by_id": person["id"],
                                              "started_at": minute(now + timedelta(minutes=10))})) == (
            400, "started_at", "That time is in the future")
        assert refusal(client.post(url, json={"performed_by_id": person["id"], "started_at": "27-10-2026"}))[0] == 400
        assert results_of(db_rows, job["id"]) == []
        start(client, job["id"], person)
        assert refusal(client.post(url, json={"performed_by_id": person["id"]})) == (
            409, None, "This job has been started. Reload the page.")
        assert len(results_of(db_rows, job["id"])) == 3

    def test_it_admin_and_the_operator_are_refused(self, engineer_a, press, at_site, role_client, ramesh, db_rows):
        _, job = plan_with(engineer_a, press, db_rows)
        for client in (role_client("it_admin"), at_site("maint_operator")):
            assert client.post(f"{JOBS}/{job['id']}/start", json={"performed_by_id": ramesh["id"]}).status_code == 403

    def test_a_node_scrapped_after_the_job_was_made(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, job = plan_with(engineer_a, press, db_rows)
        db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (press["id"],))
        assert page(client, job["id"])["can_start"] is False
        assert refusal(client.post(f"{JOBS}/{job['id']}/start", json={"performed_by_id": person["id"]})) == (
            409, None, SCRAPPED)

    def test_start_first(self, engineer_a, press, tech, db_rows):
        client, person = tech
        _, job = plan_with(engineer_a, press, db_rows)
        assert refusal(client.put(f"{JOBS}/{job['id']}", json={"performed_by_id": person["id"]})) == (
            409, None, "Start the job first.")
        assert refusal(client.post(f"{JOBS}/{job['id']}/done", json={})) == (409, None, "Start the job first.")
        # An item of a due job: it has no result row yet (BR1-01)
        assert client.put(f"{JOBS}/{job['id']}/results/1", json={"outcome": "ok"}).status_code == 404


# ---------------------------------------------------------------------------
# Items (§ 5.4)
# ---------------------------------------------------------------------------

@pytest.fixture
def started(engineer_a, press, tech, db_rows):
    """A started job of a check, a task and a free reading (30–200 °C) -> (client, page answer)."""
    client, person = tech
    _, job = plan_with(engineer_a, press, db_rows)
    return client, start(client, job["id"], person)


class TestItems:

    def test_a_check_ok_is_saved_and_idempotent(self, started, tech, db_rows):
        client, job = started
        check = job["items"][0]
        body = fill(client, job["id"], check["id"], outcome="ok", remark=None)
        assert (body["filled_count"], body["item_count"], body["meter_note"]) == (1, 3, None)
        assert (body["item"]["outcome"], body["item"]["filled_by_name"]) == ("ok", tech[1]["name"])
        (row,) = db_rows("SELECT filled_at, filled_by FROM pm_job_results WHERE id = %s", (check["id"],))
        time.sleep(1.1)
        fill(client, job["id"], check["id"], outcome="ok", remark=None)
        assert db_rows("SELECT filled_at FROM pm_job_results WHERE id = %s", (check["id"],))[0]["filled_at"] == (
            row["filled_at"])

    def test_not_ok_and_not_done_need_a_remark(self, started):
        client, job = started
        check, task, _ = job["items"]
        url = f"{JOBS}/{job['id']}/results"
        assert refusal(client.put(f"{url}/{check['id']}", json={"outcome": "not_ok"})) == (
            400, "remark", "Say what is wrong.")
        assert fill(client, job["id"], check["id"], outcome="not_ok", remark="Oil seeping")["item"]["remark"] == (
            "Oil seeping")
        assert refusal(client.put(f"{url}/{task['id']}", json={"outcome": "not_done"})) == (
            400, "remark", "Say why it was not done.")
        assert fill(client, job["id"], task["id"], outcome="not_done", remark="No grease")["filled_count"] == 2

    def test_a_reading_over_its_limit_and_na(self, started):
        client, job = started
        reading = job["items"][2]
        body = fill(client, job["id"], reading["id"], value="212")
        assert (body["item"]["value"], body["item"]["limit_state"]) == ("212", "high")
        assert refusal(client.put(f"{JOBS}/{job['id']}/results/{reading['id']}", json={"outcome": "na"})) == (
            400, "remark", "Say why there is no reading.")
        body = fill(client, job["id"], reading["id"], outcome="na", remark="Gauge broken")
        assert (body["item"]["value"], body["item"]["limit_state"], body["item"]["outcome"]) == (None, None, "na")

    def test_a_value_on_a_check_and_another_job_s_result(self, started, engineer_a, make_equipment, unit, tech,
                                                         db_rows):
        client, job = started
        assert refusal(client.put(f"{JOBS}/{job['id']}/results/{job['items'][0]['id']}",
                                  json={"outcome": "ok", "value": "3"})) == (400, "outcome", "Choose OK, Not OK or NA.")
        _, other = plan_with(engineer_a, make_equipment(unit=unit), db_rows)
        other_page = start(client, other["id"], tech[1])
        assert client.put(f"{JOBS}/{job['id']}/results/{other_page['items'][0]['id']}",
                          json={"outcome": "ok"}).status_code == 404

    def test_the_operator_is_refused_and_a_done_job_cannot_change(self, started, at_site):
        client, job = started
        check = job["items"][0]
        assert at_site("maint_operator").put(f"{JOBS}/{job['id']}/results/{check['id']}",
                                             json={"outcome": "ok"}).status_code == 403
        fill_all(client, job)
        done(client, job["id"])
        assert refusal(client.put(f"{JOBS}/{job['id']}/results/{check['id']}", json={"outcome": "not_ok",
                                                                                    "remark": "x"})) == (
            409, None, "This job is done and cannot be changed.")


# ---------------------------------------------------------------------------
# A reading that names a meter (§ 5.5)
# ---------------------------------------------------------------------------

def _meter_job(engineer_a, client, person, press, meter_type, db_rows, **limits):
    """A started job with one reading item that logs ``meter_type`` of the press -> (page answer, started_at)."""
    item = {"item_type": "reading", "text": meter_type["name"], **meter_of(press, meter_type), **limits}
    _, job = plan_with(engineer_a, press, db_rows, items=[item])
    body = start(client, job["id"], person)
    started_at = db_rows("SELECT started_at FROM pm_jobs WHERE id = %s", (job["id"],))[0]["started_at"]
    return body, started_at


class TestMeterReadings:

    def test_a_counter_value_logs_a_pm_reading_and_a_lower_one_saves_nothing(self, engineer_a, tech, press, hours,
                                                                           db_rows):
        client, person = tech
        add_reading(db_rows, press, hours, "1260", db_now(db_rows) - timedelta(hours=1))
        job, started_at = _meter_job(engineer_a, client, person, press, hours, db_rows)
        result = job["items"][0]
        assert result["limits_text"] == f"Meter reading · {press['code']}'s {hours['name']}"
        body = fill(client, job["id"], result["id"], value="1270")
        assert body["item"]["logged"] is True
        logged = readings_of(db_rows, press, hours)[-1]
        assert (logged["value"], logged["source"], logged["taken_at"], logged["removed_at"]) == (
            Decimal(1270), "pm", started_at, None)
        listing = _ok(client.get(f"/api/equipment/{press['id']}/readings", query_string={"meter_type_id": hours["id"]}))
        assert listing["items"][0]["value"] == "1270"
        res = client.put(f"{JOBS}/{job['id']}/results/{result['id']}", json={"value": "1200"})
        assert (res.status_code, res.get_json()["field"], res.get_json()["code"]) == (400, "value", "counter_lower")
        assert results_of(db_rows, job["id"])[0]["value"] == Decimal(1270)       # not saved
        assert [r["value"] for r in readings_of(db_rows, press, hours) if r["removed_at"] is None] == [
            Decimal(1260), Decimal(1270)]                                          # nothing written or removed

    def test_a_reset_is_logged_as_a_reset(self, engineer_a, tech, press, hours, db_rows):
        client, person = tech
        add_reading(db_rows, press, hours, "1260", db_now(db_rows) - timedelta(hours=1))
        job, _ = _meter_job(engineer_a, client, person, press, hours, db_rows)
        fill(client, job["id"], job["items"][0]["id"], value="1200", is_reset=True)
        logged = readings_of(db_rows, press, hours)[-1]
        assert (logged["value"], logged["is_reset"], logged["source"]) == (Decimal(1200), 1, "pm")

    def test_a_change_replaces_the_job_s_reading_and_na_removes_it(self, engineer_a, tech, press, hours, db_rows):
        client, person = tech
        add_reading(db_rows, press, hours, "1260", db_now(db_rows) - timedelta(hours=1))
        job, _ = _meter_job(engineer_a, client, person, press, hours, db_rows)
        result_id = job["items"][0]["id"]
        fill(client, job["id"], result_id, value="1270")
        fill(client, job["id"], result_id, value="1275")
        first, second = readings_of(db_rows, press, hours)[-2:]
        username = db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"]
        assert (first["value"], first["removed_by"]) == (Decimal(1270), username)
        assert (second["value"], second["removed_at"]) == (Decimal(1275), None)
        assert results_of(db_rows, job["id"])[0]["reading_id"] == second["id"]
        body = fill(client, job["id"], result_id, outcome="na", remark="Meter glass misted")
        assert body["item"]["logged"] is False
        assert readings_of(db_rows, press, hours)[-1]["removed_at"] is not None
        assert results_of(db_rows, job["id"])[0]["reading_id"] is None

    def test_a_gauge_judged_by_the_meter_s_own_limits(self, engineer_a, tech, press, oil, db_rows):
        """S104 D6: a Meter reading item has no limits of its own; Start copies the machine's meter's in force."""
        client, person = tech
        job, _ = _meter_job(engineer_a, client, person, press, oil, db_rows)
        item = job["items"][0]
        assert (item["min_value"], item["max_value"]) == ("20", "70")
        assert item["limits_text"] == f"Meter reading · {press['code']}'s {oil['name']} · 20–70 °C"
        assert fill(client, job["id"], item["id"], value="75")["item"]["limit_state"] == "high"
        assert fill(client, job["id"], item["id"], value="65")["item"]["limit_state"] is None

    def test_the_same_minute_same_value_links_and_a_change_leaves_the_operator_s(self, engineer_a, tech, press, oil,
                                                                                at_site, db_rows):
        client, person = tech
        job, started_at = _meter_job(engineer_a, client, person, press, oil, db_rows)
        operator = at_site("maint_operator")
        theirs = _ok(operator.post(f"/api/equipment/{press['id']}/readings",
                                   json={"meter_type_id": oil["id"], "value": "50", "taken_at": minute(started_at)}),
                     201)
        result_id = job["items"][0]["id"]
        fill(client, job["id"], result_id, value="50")
        assert results_of(db_rows, job["id"])[0]["reading_id"] == theirs["id"]
        assert len(readings_of(db_rows, press, oil)) == 1
        res = client.put(f"{JOBS}/{job['id']}/results/{result_id}", json={"value": "55"})
        assert refusal(res) == (409, "value", "The meter already has a different reading at this job's start time"
                                f" ({started_at.strftime('%d-%m-%Y %H:%M')}). Ask an engineer to check the meter's"
                                " readings.")
        assert readings_of(db_rows, press, oil)[0]["removed_at"] is None          # the manual reading is kept

    def test_a_same_minute_reading_with_another_value(self, engineer_a, tech, press, oil, at_site, db_rows):
        client, person = tech
        job, started_at = _meter_job(engineer_a, client, person, press, oil, db_rows)
        _ok(at_site("maint_operator").post(f"/api/equipment/{press['id']}/readings",
                                           json={"meter_type_id": oil["id"], "value": "50",
                                                 "taken_at": minute(started_at)}), 201)
        assert client.put(f"{JOBS}/{job['id']}/results/{job['items'][0]['id']}", json={"value": "48"}
                          ).status_code == 409
        assert results_of(db_rows, job["id"])[0]["value"] is None

    def test_a_meter_removed_after_start_keeps_the_value_on_the_job(self, engineer_a, tech, press, make_meter_type,
                                                                    add_own_meter, admin, db_rows):
        client, person = tech
        own = make_meter_type()
        add_own_meter(press, own)
        job, _ = _meter_job(engineer_a, client, person, press, own, db_rows)
        _ok(admin.put(f"/api/equipment/{press['id']}/meters/{own['id']}", json={"active": False}))
        body = fill(client, job["id"], job["items"][0]["id"], value="40")
        assert body["meter_note"] == (f"Saved on the job only: this machine no longer has the meter"
                                      f" {press['code']}'s {own['name']}.")
        assert (body["item"]["value"], body["item"]["logged"]) == ("40", False)
        assert readings_of(db_rows, press, own) == []

    def test_a_meter_removed_after_a_logged_value_lets_go_of_the_reading(self, engineer_a, tech, press,
                                                                           make_meter_type, add_own_meter, admin,
                                                                           db_rows):
        """CR1-01: the job's own reading is removed before the meter check, and the link let go, so NA keeps the
        CHECK (no 500) and a new value is never shown as logged."""
        client, person = tech
        own = make_meter_type()
        add_own_meter(press, own)
        job, _ = _meter_job(engineer_a, client, person, press, own, db_rows)
        result_id = job["items"][0]["id"]
        fill(client, job["id"], result_id, value="40")
        (logged,) = readings_of(db_rows, press, own)
        _ok(admin.put(f"/api/equipment/{press['id']}/meters/{own['id']}", json={"active": False}))
        body = fill(client, job["id"], result_id, outcome="na", remark="Meter taken off")
        assert (body["item"]["outcome"], body["item"]["logged"]) == ("na", False)
        assert results_of(db_rows, job["id"])[0]["reading_id"] is None
        assert readings_of(db_rows, press, own)[0]["removed_at"] is not None
        assert db_rows("SELECT id FROM meter_readings WHERE id = %s", (logged["id"],))
        body = fill(client, job["id"], result_id, value="42")
        assert (body["item"]["value"], body["item"]["logged"]) == ("42", False)
        assert body["meter_note"].startswith("Saved on the job only")

    def test_a_late_save_on_a_done_job_of_a_scrapped_machine_says_done(self, engineer_a, tech, press, hours,
                                                                      db_rows):
        """CR1-02: the state is judged before the meter's node lock and its scrapped refusal."""
        client, person = tech
        job, _ = _meter_job(engineer_a, client, person, press, hours, db_rows)
        result_id = job["items"][0]["id"]
        fill(client, job["id"], result_id, value="10")
        done(client, job["id"])
        db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (press["id"],))
        assert refusal(client.put(f"{JOBS}/{job['id']}/results/{result_id}", json={"value": "11"})) == (
            409, None, "This job is done and cannot be changed.")

    def test_the_save_waits_for_the_node_lock_and_sees_the_reading_before_it(self, engineer_a, tech, press, hours,
                                                                           db_rows):
        """BR1-18: a connection holds the machine FOR UPDATE and inserts 1,300 a minute before Started; the PM save
        of 1,280 waits on (1), then sees that row (its snapshot starts after the lock) and is refused."""
        client, person = tech
        job, started_at = _meter_job(engineer_a, client, person, press, hours, db_rows)
        url = f"{JOBS}/{job['id']}/results/{job['items'][0]['id']}"
        conn = get_local_db(config.DB_CONFIG)
        result = {}
        try:
            with conn.cursor() as cur:
                cur.execute("START TRANSACTION")
                cur.execute("SELECT id FROM equipment WHERE id = %s FOR UPDATE", (press["id"],))
                worker = threading.Thread(target=lambda: result.update(res=client.put(url, json={"value": "1280"})))
                worker.start()
                time.sleep(1)
                assert worker.is_alive(), "the PM save did not wait for the node lock"
                cur.execute("INSERT INTO meter_readings (equipment_id, meter_type_id, value, taken_at, created_by)"
                            " VALUES (%s, %s, 1300, %s, 'other')",
                            (press["id"], hours["id"], started_at - timedelta(minutes=1)))
                cur.execute("COMMIT")
            worker.join(timeout=30)
        finally:
            conn.close()
        assert (result["res"].status_code, result["res"].get_json()["code"]) == (400, "counter_lower")


# ---------------------------------------------------------------------------
# The performer (§ 6.1) and the clock
# ---------------------------------------------------------------------------

class TestPerformer:

    def test_a_change_writes_the_event_and_the_same_person_none(self, started, ramesh, tech, db_rows):
        client, job = started
        body = _ok(client.put(f"{JOBS}/{job['id']}", json={"performed_by_id": ramesh["id"]}))
        assert body["performed_by"] == {"id": ramesh["id"], "name": "Ramesh"}
        assert [(e["event"], e["person_id"]) for e in events_of(db_rows, job["id"])][-1] == (
            "performer_changed", ramesh["id"])
        count = len(events_of(db_rows, job["id"]))
        _ok(client.put(f"{JOBS}/{job['id']}", json={"performed_by_id": ramesh["id"]}))
        _ok(client.put(f"{JOBS}/{job['id']}", json={}))
        assert len(events_of(db_rows, job["id"])) == count

    def test_the_refusals(self, started, make_person, give_site_role, other_site):
        client, job = started
        for bad in (True, "7", None, 0):
            assert refusal(client.put(f"{JOBS}/{job['id']}", json={"performed_by_id": bad})) == (
                400, "performed_by_id", "Choose who did the work.")
        stranger = make_person(name="Elsewhere")
        give_site_role(stranger, other_site)
        assert refusal(client.put(f"{JOBS}/{job['id']}", json={"performed_by_id": stranger["id"]})) == (
            400, "performed_by_id", "Choose a person from this site")


def test_a_fixed_clock_fixes_start_and_done(engineer_a, press, tech, db_rows, monkeypatch):
    """BR1-08: pm_work.py reads pm_jobs._now through the module."""
    client, person = tech
    _, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
    moment = db_now(db_rows).replace(second=42, microsecond=0) - timedelta(hours=3)
    fix_now(monkeypatch, moment)
    body = start(client, job["id"], person)
    fill(client, job["id"], body["items"][0]["id"], outcome="ok")
    done(client, job["id"])
    stored = db_rows("SELECT started_at, done_at FROM pm_jobs WHERE id = %s", (job["id"],))[0]
    assert stored["started_at"] == stored["done_at"] == moment.replace(second=0)
    assert pm_jobs._now(None) == moment


# ---------------------------------------------------------------------------
# Mark job done (§ 5.6)
# ---------------------------------------------------------------------------

class TestDone:

    def test_all_items_filled_first_then_done(self, started, db_rows):
        client, job = started
        check, task, _ = job["items"]
        fill(client, job["id"], check["id"], outcome="ok")
        fill(client, job["id"], task["id"], outcome="done")
        assert refusal(client.post(f"{JOBS}/{job['id']}/done", json={})) == (
            409, None, "Fill every item first: 1 of 3 are not filled.")
        fill(client, job["id"], job["items"][2]["id"], value="45")
        now = db_now(db_rows)
        body = done(client, job["id"])
        assert (body["state"], body["can_work"], body["standing"], body["timeliness"]) == ("done", False, None, "late")
        stored = db_rows("SELECT * FROM pm_jobs WHERE id = %s", (job["id"],))[0]
        assert stored["open_plan_id"] is None and abs(stored["done_at"] - now) < timedelta(minutes=2)
        line = events_of(db_rows, job["id"])[-1]
        assert (line["event"], line["from_state"], line["to_state"], line["occurred_at"]) == (
            "done", "in_progress", "done", stored["done_at"])
        assert refusal(client.post(f"{JOBS}/{job['id']}/done", json={})) == (
            409, None, "This job is done and cannot be changed.")

    def test_done_before_started_is_refused(self, started, db_rows):
        client, job = started
        fill_all(client, job)
        started_at = db_rows("SELECT started_at FROM pm_jobs WHERE id = %s", (job["id"],))[0]["started_at"]
        assert refusal(client.post(f"{JOBS}/{job['id']}/done",
                                   json={"done_at": minute(started_at - timedelta(minutes=1))})) == (
            400, "done_at", f"Done must be at or after Started, {started_at.strftime('%d-%m-%Y %H:%M')}.")

    @pytest.mark.parametrize("value, judged", [("1270", "on_time"), ("1280", "late")])
    def test_a_meter_plan_stores_done_meter_and_timeliness(self, engineer_a, tech, press, hours, db_rows, value,
                                                           judged):
        """Due at 1,250 h, window 25 (S095's 10 %): 1,270 is on time, 1,280 late."""
        client, person = tech
        add_reading(db_rows, press, hours, "1260", db_now(db_rows) - timedelta(hours=1))
        item = {"item_type": "reading", "text": "Run hours", **meter_of(press, hours)}
        plan = create(engineer_a, press, items=[item], trigger_kind="meter", calendar_every=None,
                      calendar_unit=None, **meter_of(press, hours), meter_every="250", last_done_meter="1000")
        (job,) = jobs_of(db_rows, plan["id"])
        body = start(client, job["id"], person)
        fill(client, job["id"], body["items"][0]["id"], value=value)
        body = done(client, job["id"])
        stored = db_rows("SELECT done_meter, timeliness, due_meter FROM pm_jobs WHERE id = %s", (job["id"],))[0]
        assert (stored["due_meter"], stored["done_meter"], stored["timeliness"]) == (Decimal(1250), Decimal(value),
                                                                                    judged)
        assert body["done_meter"] == value

    def test_the_next_job_comes_with_the_daily_run(self, started, db_rows, monkeypatch):
        client, job = started
        fill_all(client, job)
        plan_id = page(client, job["id"])["plan"]["id"]
        done(client, job["id"])
        assert [j["state"] for j in jobs_of(db_rows, plan_id)] == ["done"]   # every 30 days: not in its window
        fix_now(monkeypatch, db_now(db_rows) + timedelta(days=28))
        generate()
        assert [j["state"] for j in jobs_of(db_rows, plan_id)] == ["done", "due"]


# ---------------------------------------------------------------------------
# A started job and S097 (D2)
# ---------------------------------------------------------------------------

class TestStartedJobAndThePlan:

    def test_a_plan_edit_leaves_a_started_job_as_it_is(self, engineer_a, press, tech, ramesh, db_rows):
        client, person = tech
        plan, job = plan_with(engineer_a, press, db_rows)
        start(client, job["id"], person)
        before = jobs_of(db_rows, plan["id"])[0]
        lines = len(events_of(db_rows, job["id"]))
        items = [item_body(item) for item in plan["items"]] + [{"item_type": "task", "text": "Check the filter"}]
        change(engineer_a, plan, calendar_every=10, assignee_id=person["id"], items=items)
        after = jobs_of(db_rows, plan["id"])[0]
        assert (after["due_on"], after["assignee_id"], after["state"]) == (before["due_on"], before["assignee_id"],
                                                                          "in_progress")
        assert len(results_of(db_rows, job["id"])) == 3
        assert len(events_of(db_rows, job["id"])) == lines
        assert page(client, job["id"])["item_count"] == 3

    def test_a_deactivated_plan_keeps_its_started_job_open_to_finish(self, engineer_a, press, tech, db_rows):
        client, person = tech
        plan, job = plan_with(engineer_a, press, db_rows)
        body = start(client, job["id"], person)
        change(engineer_a, plan, active=False)
        generate()
        generate()
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "in_progress"
        fill_all(client, body)
        assert done(client, job["id"])["state"] == "done"


# ---------------------------------------------------------------------------
# S104: the job reads the template (§ 5.7, § 8.2)
# ---------------------------------------------------------------------------

def _gauge_item(meter_type):
    return {"item_type": "reading", "reading_kind": "meter", "text": meter_type["name"],
            "meter_type_id": meter_type["id"]}


class TestTemplateWork:

    def test_start_copies_the_kind_the_resolved_meter_and_the_name(self, engineer_a, press, oil, tech, db_rows):
        client, person = tech
        measure = {"item_type": "reading", "reading_kind": "measurement", "text": "Main pressure", "unit": "bar",
                   "min_value": "180", "max_value": "200"}
        plan, job = plan_with(engineer_a, press, db_rows, items=[measure, _gauge_item(oil)])
        start(client, job["id"], person)
        rows = results_of(db_rows, job["id"])
        assert [(r["template_item_id"], r["reading_kind"], r["meter_equipment_id"]) for r in rows] == [
            (plan["items"][0]["id"], "measurement", None), (plan["items"][1]["id"], "meter", press["id"])]
        assert jobs_of(db_rows, plan["id"])[0]["title"] == plan["template"]["name"]

    def test_a_measurement_logs_no_meter_reading_and_a_meter_reading_logs_one(self, engineer_a, press, oil, tech,
                                                                              db_rows):
        client, person = tech
        measure = {"item_type": "reading", "reading_kind": "measurement", "text": "Oil temperature by hand",
                   "unit": "°C"}
        _, job = plan_with(engineer_a, press, db_rows, items=[measure, _gauge_item(oil)])
        body = start(client, job["id"], person)
        before = len(readings_of(db_rows, press, oil))
        fill(client, job["id"], body["items"][0]["id"], value="48")
        assert len(readings_of(db_rows, press, oil)) == before
        fill(client, job["id"], body["items"][1]["id"], value="49")
        assert readings_of(db_rows, press, oil)[-1]["value"] == Decimal("49")

    def test_a_linked_meter_logs_on_the_press_s_meter(self, engineer_a, press, oil, tech, make_equipment, db_rows):
        # S104 A1: the part uses the press's oil temperature through a meter link; the reading is saved there (D7)
        client, person = tech
        part = make_equipment(parent=press)
        link_meter(engineer_a, part, press, oil)
        _, job = plan_with(engineer_a, part, db_rows, items=[_gauge_item(oil)])
        body = start(client, job["id"], person)
        assert body["items"][0]["meter"]["equipment_id"] == press["id"]
        fill(client, job["id"], body["items"][0]["id"], value="51")
        assert readings_of(db_rows, press, oil)[-1]["value"] == Decimal("51")
        assert readings_of(db_rows, part, oil) == []

    def test_a_meter_gone_since_the_settle_refuses_start(self, engineer_a, machine, oil, tech, add_own_meter,
                                                        admin, db_rows):
        client, person = tech
        add_own_meter(machine, oil)
        _, job = plan_with(engineer_a, machine, db_rows, items=[_gauge_item(oil)])
        removed = admin.put(f"/api/equipment/{machine['id']}/meters/{oil['id']}", json={"active": False})
        assert removed.status_code == 200, removed.get_json()
        assert refusal(client.post(f"{JOBS}/{job['id']}/start", json={"performed_by_id": person["id"]})) == (
            409, None, f"This job cannot start: no {oil['name']} meter on {machine['code']}. Ask an engineer.")
        assert results_of(db_rows, job["id"]) == []

    def test_a_template_renamed_after_start_leaves_the_job_s_title(self, engineer_a, press, tech, db_rows):
        client, person = tech
        plan, job = plan_with(engineer_a, press, db_rows, items=[CHECK])
        start(client, job["id"], person)
        change(engineer_a, plan, title="Press — monthly check, renamed")
        assert page(client, job["id"])["plan"]["title"] == plan["template"]["name"]


# ---------------------------------------------------------------------------
# The database down (§ 5.12)
# ---------------------------------------------------------------------------

def test_the_database_down(db_down, engineer):
    assert engineer.get(f"{JOBS}/1").status_code == 503
    assert engineer.post(f"{JOBS}/1/start", json={"performed_by_id": 1}).status_code == 503
