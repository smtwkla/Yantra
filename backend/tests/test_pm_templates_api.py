"""PM templates (S104 § 5.1, § 5.2, § 5.6, § 6, § 8.2), against the test DB.  Needs the dev MariaDB container.

A template is written once and reaches every machine it is attached to: a save settles each plan of the template
after its commit, one transaction per plan, as the daily run does, with the engineer named on the job's timeline.
"""

from datetime import timedelta

import pymysql

import pm_jobs
from pm_jobs_core import RESCHEDULE_DROPPED, TEMPLATE_INACTIVE_REMARK
from pm_templates_core import DUPLICATE_NAME, ITEM_METER_TYPE_NEEDED, METER_LIMITS, READING_KIND_NEEDED
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, PLANS, TASK, TEMPLATES, _ok, add_model_meter, at_site, attach, change_template, eng, engineer_a, hours,
    item_body, make_template, oil, press, site, tech, template_body, unique,
)
from tests.test_pm_generate import db_now, events_of, jobs_of, overdue, upcoming

GAUGE_ITEM = {"item_type": "reading", "reading_kind": "meter", "text": "Oil temperature"}
MEASURE = {"item_type": "reading", "reading_kind": "measurement", "text": "Main pressure", "unit": "bar",
           "min_value": "180", "max_value": "200"}


def refused(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def due_on_two(engineer, nodes, db_rows, **fields):
    """A template every 30 days on each node, each plan seeded 40 days back (overdue, its job made) -> (template,
    plans)."""
    template = make_template(engineer, calendar_every=30, calendar_unit="day", **fields)
    plans = []
    for node in nodes:
        plan = attach(engineer, node, template)
        _ok(engineer.put(f"{PLANS}/{plan['id']}", json={"last_done_on": overdue(db_rows)["last_done_on"]}))
        plans.append(plan)
    return template, plans


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

class TestReads:

    def test_the_list_and_the_detail_for_each_role(self, engineer_a, press, at_site, role_client, hours):
        template = make_template(engineer_a, trigger_kind="both", meter_type_id=hours["id"], meter_every="250",
                                 items=[CHECK, TASK, MEASURE])
        attach(engineer_a, press, template)
        gone = make_template(engineer_a)
        change_template(engineer_a, gone, active=False)
        for client in (at_site("maint_technician"), role_client("it_admin"), engineer_a):
            body = _ok(client.get(TEMPLATES))
            mine = next(t for t in body["items"] if t["id"] == template["id"])
            assert mine == {"id": template["id"], "name": template["name"],
                            "trigger_text": "Every month or 250 h, whichever comes first", "item_count": 3,
                            "plan_count": 1, "active": True}
            assert gone["id"] in [t["id"] for t in body["inactive"]]
        assert _ok(at_site("maint_technician").get(TEMPLATES))["can_add"] is False
        assert _ok(role_client("it_admin").get(f"{TEMPLATES}/{template['id']}"))["can_edit"] is False
        detail = _ok(engineer_a.get(f"{TEMPLATES}/{template['id']}"))
        assert (detail["can_edit"], detail["plan_count"], detail["meter_type"]["id"]) == (True, 1, hours["id"])
        assert [i["limits_text"] for i in detail["items"]] == [None, None, "Measurement · 180–200 bar"]

    def test_it_admin_and_the_technician_cannot_write(self, role_client, at_site):
        for client in (role_client("it_admin"), at_site("maint_technician")):
            assert client.post(TEMPLATES, json=template_body()).status_code == 403

    def test_a_missing_template(self, engineer_a):
        assert engineer_a.get(f"{TEMPLATES}/99999999").status_code == 404
        assert engineer_a.put(f"{TEMPLATES}/99999999", json={"name": "x"}).status_code == 404


# ---------------------------------------------------------------------------
# Create and change
# ---------------------------------------------------------------------------

class TestWrite:

    def test_create_and_a_name_taken(self, engineer_a, oil):
        template = make_template(engineer_a, items=[CHECK, MEASURE, {**GAUGE_ITEM, "meter_type_id": oil["id"]}])
        assert [(i["position"], i["reading_kind"]) for i in template["items"]] == [
            (1, None), (2, "measurement"), (3, "meter")]
        assert template["items"][2]["limits_text"] == f"Meter reading · {oil['name']}"
        assert (template["plans_settled"], template["plans_failed"]) == (0, 0)
        assert refused(engineer_a.post(TEMPLATES, json=template_body(name=template["name"]))) == (
            409, "name", DUPLICATE_NAME)

    def test_the_reading_kind_refusals(self, engineer_a, oil):
        def item_refused(item):
            return refused(engineer_a.post(TEMPLATES, json=template_body(items=[item])))
        assert item_refused({**GAUGE_ITEM, "reading_kind": None}) == (
            400, "items", f"Item 1: {READING_KIND_NEEDED}")
        assert item_refused(GAUGE_ITEM) == (400, "items", f"Item 1: {ITEM_METER_TYPE_NEEDED}")
        assert item_refused({**GAUGE_ITEM, "meter_type_id": oil["id"], "max_value": "60"}) == (
            400, "items", f"Item 1: {METER_LIMITS}")

    def test_the_item_check(self, engineer_a, oil):
        url = "/api/pm/template-item-check"
        item = _ok(engineer_a.post(url, json={"item": {**GAUGE_ITEM, "meter_type_id": oil["id"],
                                                       "meter_from_parent": True}}))
        # S104 A1: the old tick is ignored, and the answer has no such field
        assert item["meter_type"]["id"] == oil["id"] and "meter_from_parent" not in item
        assert refused(engineer_a.post(url, json={"item": {**MEASURE, "meter_type_id": oil["id"]}})) == (
            400, "meter_type_id", "Only a meter reading names a meter type.")

    def test_a_body_with_the_old_tick_saves_and_the_answer_has_none(self, engineer_a, hours):
        # S104 A1.3: the field is ignored, as any unknown field of a template body
        saved = _ok(engineer_a.post(TEMPLATES, json=template_body(
            trigger_kind="meter", calendar_every=None, calendar_unit=None, meter_type_id=hours["id"],
            meter_every="250", meter_from_parent=True)), 201)
        assert "meter_from_parent" not in saved
        assert all("meter_from_parent" not in item for item in saved["items"])

    def test_the_trigger_rules(self, engineer_a, oil):
        assert refused(engineer_a.post(TEMPLATES, json=template_body(
            trigger_kind="meter", calendar_every=None, calendar_unit=None, meter_type_id=oil["id"],
            meter_every="5"))) == (400, "meter_type_id", "Choose a counter meter type, such as Run hours.")

    def test_a_change_syncs_the_items(self, engineer_a, db_rows):
        template = make_template(engineer_a, items=[CHECK, TASK])
        first, second = (item_body(item) for item in template["items"])
        body = change_template(engineer_a, template, items=[{**second, "text": "Grease both bearings"}])
        assert [(i["id"], i["text"]) for i in body["items"]] == [(second["id"], "Grease both bearings")]
        (row,) = db_rows("SELECT active FROM pm_template_items WHERE id = %s", (first["id"],))
        assert row["active"] == 0


# ---------------------------------------------------------------------------
# A template change reaches the plans (§ 5.6)
# ---------------------------------------------------------------------------

class TestSettle:

    def test_a_new_interval_moves_the_open_job_of_each_plan(self, eng, make_equipment, unit, db_rows):
        client, person = eng
        nodes = [make_equipment(unit=unit) for _ in range(2)]
        template, plans = due_on_two(client, nodes, db_rows)
        body = change_template(client, template, calendar_every=35)
        assert (body["plans_settled"], body["plans_failed"]) == (2, 0)
        last_done = db_now(db_rows).date() - timedelta(days=40)
        username = db_rows("SELECT username FROM people WHERE id = %s", (person["id"],))[0]["username"]
        for plan in plans:
            (job,) = jobs_of(db_rows, plan["id"])
            assert job["due_on"] == last_done + timedelta(days=35)
            line = events_of(db_rows, job["id"])[-1]
            assert (line["event"], line["created_by"]) == ("due_changed", username)   # BR1-03: the engineer

    def test_a_schedule_change_drops_a_reschedule_and_a_name_change_keeps_it(self, engineer_a, press, db_rows):
        template, (plan,) = due_on_two(engineer_a, [press], db_rows)
        (job,) = jobs_of(db_rows, plan["id"])
        moved_to = db_now(db_rows).date() + timedelta(days=6)
        _ok(engineer_a.post(f"/api/pm/jobs/{job['id']}/reschedule",
                            json={"due_on": moved_to.isoformat(), "remark": "Shutdown"}))
        change_template(engineer_a, template, name=unique("Press — monthly check"))
        assert jobs_of(db_rows, plan["id"])[0]["rescheduled_on"] == moved_to
        change_template(engineer_a, template, calendar_every=20)
        assert jobs_of(db_rows, plan["id"])[0]["rescheduled_on"] is None
        assert events_of(db_rows, job["id"])[-1]["remark"] == RESCHEDULE_DROPPED

    def test_deactivate_cancels_and_reactivate_makes_the_jobs_again(self, engineer_a, press, make_equipment, unit,
                                                                     tech, db_rows):
        client, person = tech
        other = make_equipment(unit=unit)
        template, (due_plan, started_plan) = due_on_two(engineer_a, [press, other], db_rows)
        (started,) = jobs_of(db_rows, started_plan["id"])
        _ok(client.post(f"/api/pm/jobs/{started['id']}/start", json={"performed_by_id": person["id"]}))
        change_template(engineer_a, template, active=False)
        (cancelled,) = jobs_of(db_rows, due_plan["id"])
        assert cancelled["state"] == "cancelled"
        assert events_of(db_rows, cancelled["id"])[-1]["remark"] == TEMPLATE_INACTIVE_REMARK
        assert jobs_of(db_rows, started_plan["id"])[0]["state"] == "in_progress"
        change_template(engineer_a, template, active=True)
        assert [j["state"] for j in jobs_of(db_rows, due_plan["id"])] == ["cancelled", "due"]

    def test_one_plan_failing_leaves_the_template_saved(self, engineer_a, make_equipment, unit, db_rows,
                                                        monkeypatch):
        nodes = [make_equipment(unit=unit) for _ in range(2)]
        template, plans = due_on_two(engineer_a, nodes, db_rows)
        real = pm_jobs.settle_one

        def failing(conn, plan_id, actor, *, keep_reschedule=True):
            if plan_id == plans[0]["id"]:
                raise RuntimeError("test: one plan fails")
            return real(conn, plan_id, actor, keep_reschedule=keep_reschedule)

        monkeypatch.setattr(pm_jobs, "settle_one", failing)
        body = change_template(engineer_a, template, calendar_every=35)
        assert (body["plans_settled"], body["plans_failed"], body["calendar_every"]) == (1, 1, 35)

    def test_a_lost_connection_while_settling_answers_503_and_the_template_stands(
            self, engineer_a, make_equipment, unit, db_rows, monkeypatch):
        """CR5-01: the pool's rollback on a dead socket raises InterfaceError(0, ""), not the 2013; the loop stops at
        the first plan and the save answers BR1-12's 503 (the template is committed before the plans settle)."""
        nodes = [make_equipment(unit=unit) for _ in range(2)]
        template, _plans = due_on_two(engineer_a, nodes, db_rows)
        calls = []

        def lost(conn, plan_id, actor, *, keep_reschedule=True):
            calls.append(plan_id)
            raise pymysql.err.InterfaceError(0, "")

        monkeypatch.setattr(pm_jobs, "settle_one", lost)
        res = engineer_a.put(f"{TEMPLATES}/{template['id']}", json={"calendar_every": 35})
        assert res.status_code == 503
        assert len(calls) == 1
        (row,) = db_rows("SELECT calendar_every FROM pm_templates WHERE id = %s", (template["id"],))
        assert row["calendar_every"] == 35

    def test_a_relinked_plan_with_no_base_counts_from_the_relink(self, engineer_a, press, db_rows):
        """BR1-05: a plan removed for months does not come back overdue at once."""
        template = make_template(engineer_a, calendar_every=30, calendar_unit="day")
        plan = attach(engineer_a, press, template)
        _ok(engineer_a.post(f"{PLANS}/{plan['id']}/remove"))
        db_rows("UPDATE pm_plans SET linked_at = linked_at - INTERVAL 200 DAY WHERE id = %s", (plan["id"],))
        attach(engineer_a, press, template)
        (row,) = db_rows("SELECT linked_at FROM pm_plans WHERE id = %s", (plan["id"],))
        assert abs(row["linked_at"] - db_now(db_rows)) < timedelta(minutes=2)
        assert jobs_of(db_rows, plan["id"]) == []


def test_a_seed_inside_the_window_makes_the_job_at_once(engineer_a, press, db_rows):
    template = make_template(engineer_a, calendar_every=30, calendar_unit="day")
    plan = attach(engineer_a, press, template)
    _ok(engineer_a.put(f"{PLANS}/{plan['id']}", json={"last_done_on": upcoming(db_rows)["last_done_on"]}))
    assert [j["state"] for j in jobs_of(db_rows, plan["id"])] == ["due"]


def test_the_database_down(db_down, engineer):
    assert engineer.get(TEMPLATES).status_code == 503
    assert engineer.post(TEMPLATES, json=template_body()).status_code == 503
