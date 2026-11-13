"""A machine's PM plans (S104 § 5.3–§ 5.5, § 6, § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test makes its own site, unit, model and machine (the conftest factories) and its templates through
tests/pm_helpers.py, so the kept worker database is the starting state.  The engineers have real memberships
(user_at_sites), since the site checks read memberships, never the token.  "Another site" is a person with no
membership at the machine's site (404 by the machine's units); "a key missing here" is a person who is engineer at
one site and operator at the other (403 naming the site).
"""

from datetime import timedelta

import pytest

import equipment
from pm_jobs_core import UNLINKED_REMARK
from pm_plans_core import CHANGE_ON_TEMPLATE, LAST_DONE_DATE, NO_METER_TRIGGER, OPERATOR_NO_ASSIGNEE, PLAN_FIXED
from tests.documents_helpers import scrap
from tests.pm_helpers import (  # noqa: F401 — fixtures
    CHECK, EQUIPMENT, PLANS, SCRAPPED, TASK, _ok, add_model_meter, add_own_meter, at_site, attach, change_template,
    eng, engineer_a, hours, link_meter, make_template, oil, other_site, other_unit, press, site, tech, technician,
    unlink_meter,
)
from tests.test_pm_generate import add_reading, db_now, events_of, jobs_of, overdue
from tickets import ASSIGNEE_AT_SITE

METER = {"trigger_kind": "meter", "calendar_every": None, "calendar_unit": None, "meter_every": "250"}
SEED_COLUMNS = ("last_done_meter", "seed_meter_equipment_id", "seed_meter_type_id")


def settings(client, plan, status=200, **fields):
    return _ok(client.put(f"{PLANS}/{plan['id']}", json=fields), status)


def refused(res):
    body = res.get_json()
    return res.status_code, body.get("field"), body["error"]


def card(client, node):
    return _ok(client.get(PLANS, query_string={"equipment_id": node["id"]}))


def next_due_meter(client, node):
    """The due meter value the card shows for the node's only plan."""
    (item,) = card(client, node)["items"]
    return item["schedule"]["next_due"]["due_meter"]


def meter_template(client, meter_type, **fields):
    return make_template(client, **METER, meter_type_id=meter_type["id"], **fields)


# ---------------------------------------------------------------------------
# Attach (§ 5.5)
# ---------------------------------------------------------------------------

class TestAttach:

    def test_the_engineer_attaches_a_template(self, engineer_a, press, db_rows):
        template = make_template(engineer_a)
        plan = attach(engineer_a, press, template)
        assert (plan["template"]["id"], plan["template"]["name"], plan["source"]) == (
            template["id"], template["name"], {"kind": "equipment", "label": "This machine"})
        assert (plan["linked"], plan["applies"], plan["stop_remark"], plan["assignee"]) == (True, True, None, None)
        assert [i["text"] for i in plan["template"]["items"]] == [CHECK["text"], TASK["text"]]
        assert plan["can_edit"] is True and plan["can_remove"] is True
        (row,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert (row["equipment_id"], row["template_id"], row["linked"], row["last_done_on"]) == (
            press["id"], template["id"], 1, None)
        (link,) = db_rows("SELECT * FROM pm_template_links WHERE template_id = %s", (template["id"],))
        assert (link["target_kind"], link["equipment_id"], link["active"]) == ("equipment", press["id"], 1)

    def test_the_refusals(self, engineer_a, press, admin, make_equipment, unit):
        template = make_template(engineer_a)
        attach(engineer_a, press, template)
        assert refused(engineer_a.post(PLANS, json={"equipment_id": press["id"], "template_id": template["id"]})) == (
            409, "template_id", "This template is already attached to this machine.")
        inactive = make_template(engineer_a)
        change_template(engineer_a, inactive, active=False)
        assert refused(engineer_a.post(PLANS, json={"equipment_id": press["id"], "template_id": inactive["id"]})) == (
            409, "template_id", "This template is inactive. Reactivate it in Masters › PM templates first.")
        gone = make_equipment(unit=unit)
        scrap(admin, gone)
        assert refused(engineer_a.post(PLANS, json={"equipment_id": gone["id"], "template_id": template["id"]})) == (
            409, None, SCRAPPED)
        assert engineer_a.post(PLANS, json={"equipment_id": press["id"]}).status_code == 400

    def test_another_site_and_a_key_missing_here(self, engineer_a, press, user_at_sites, other_site, site):
        template = make_template(engineer_a)
        elsewhere, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        body = {"equipment_id": press["id"], "template_id": template["id"]}
        assert elsewhere.post(PLANS, json=body).status_code == 404
        mixed, _ = user_at_sites([(other_site, "maint_engineer", "all"), (site, "maint_operator", "all")])
        res = mixed.post(PLANS, json={"equipment_id": press["id"], "template_id": template["id"]})
        assert res.status_code == 403

    def test_a_template_that_does_not_apply_is_attached_and_makes_no_job(self, engineer_a, machine, hours, db_rows):
        template = meter_template(engineer_a, hours)
        plan = attach(engineer_a, machine, template)
        missing = f"no {hours['name']} meter on {machine['code']}"
        assert (plan["applies"], plan["missing_text"]) == (False, missing)
        assert plan["stop_remark"] == f"Does not apply: {missing}."
        assert plan["meters"] == [{"meter_type": {key: hours[key] for key in ("id", "name", "unit", "kind",
                                                                              "decimals")},
                                   "equipment": None, "from_link": False}]
        assert jobs_of(db_rows, plan["id"]) == []
        (item,) = card(engineer_a, machine)["items"]
        assert (item["applies"], item["schedule"]) == (False, {"open_job": None, "next_due": None, "meter": None})
        preview = _ok(engineer_a.get(f"{PLANS}/attach-preview",
                                     query_string={"equipment_id": machine["id"], "template_id": template["id"]}))
        assert (preview["applies"], preview["missing"]) == (False, missing)


# ---------------------------------------------------------------------------
# The meter match (§ 5.3)
# ---------------------------------------------------------------------------

class TestMeterMatch:

    def test_the_model_s_meter(self, engineer_a, press, hours):
        plan = attach(engineer_a, press, meter_template(engineer_a, hours))
        assert [(m["equipment"]["id"], m["from_link"]) for m in plan["meters"]] == [(press["id"], False)]
        assert plan["applies"] is True

    def test_the_node_s_own_meter(self, engineer_a, machine, hours, add_own_meter):
        add_own_meter(machine, hours)
        plan = attach(engineer_a, machine, meter_template(engineer_a, hours))
        assert plan["meters"][0]["equipment"] == {"id": machine["id"], "code": machine["code"]}

    def test_a_part_without_the_meter_does_not_apply(self, engineer_a, press, hours, make_equipment):
        part = make_equipment(parent=press)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        assert plan["applies"] is False

    def test_a_part_without_a_link_does_not_use_the_press_s_meter(self, engineer_a, press, hours, make_equipment):
        # A1.6.2: nothing walks up the tree without a link
        part = make_equipment(parent=press)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        assert plan["meters"][0]["equipment"] is None and plan["applies"] is False

    def test_a_link_uses_the_press_s_meter(self, engineer_a, press, hours, make_equipment, db_rows):
        part = make_equipment(parent=press)
        link_meter(engineer_a, part, press, hours)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        assert plan["meters"][0]["equipment"]["id"] == press["id"] and plan["meters"][0]["from_link"] is True
        add_reading(db_rows, press, hours, "1230", db_now(db_rows) - timedelta(hours=1))
        settings(engineer_a, plan, last_done_meter="1000")
        (job,) = jobs_of(db_rows, plan["id"])
        assert (job["equipment_id"], job["meter_equipment_id"], job["due_meter"]) == (part["id"], press["id"], 1250)

    def test_a_grandchild_links_the_machine(self, engineer_a, press, hours, make_equipment):
        unit_node = make_equipment(parent=press)
        part = make_equipment(parent=unit_node, level="component")
        link_meter(engineer_a, part, press, hours)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        assert plan["meters"][0]["equipment"] == {"id": press["id"], "code": press["code"]}

    def test_a_link_not_in_use_counts_for_nothing(self, engineer_a, machine, hours, make_equipment, add_own_meter):
        # the source's meter goes: the link stays, not in use, and the plan does not apply (A1.6.1)
        add_own_meter(machine, hours)
        part = make_equipment(parent=machine)
        link_meter(engineer_a, part, machine, hours)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        assert plan["applies"] is True
        _ok(engineer_a.put(f"{EQUIPMENT}/{machine['id']}/meters/{hours['id']}", json={"active": False}))
        assert _ok(engineer_a.get(f"{PLANS}/{plan['id']}"))["applies"] is False
        add_own_meter(machine, hours)                                   # back: the link is in use again
        assert _ok(engineer_a.get(f"{PLANS}/{plan['id']}"))["applies"] is True

    def test_the_seed_follows_the_meter(self, engineer_a, press, hours, make_equipment, add_own_meter, db_rows,
                                        technician):
        """BR1-01, CR1-04, CR1-05, A1.6.3: a *Last done* meter value entered for the press's meter through a link is
        answered only while the plan uses that meter: null once the link goes and the part has its own meter (the
        next due counts from the part's reading), kept by an assignee save, back when the same link is set again,
        and a typed value is stored for the meter the plan uses now."""
        part = make_equipment(parent=press)
        link_meter(engineer_a, part, press, hours)
        plan = attach(engineer_a, part, meter_template(engineer_a, hours))
        plan = settings(engineer_a, plan, last_done_meter="1000")
        assert plan["last_done_meter"] == "1000" and "seed_note" not in plan
        unlink_meter(engineer_a, part, hours)
        add_own_meter(part, hours)
        add_reading(db_rows, part, hours, "40", db_now(db_rows) - timedelta(minutes=1))
        assert _ok(engineer_a.get(f"{PLANS}/{plan['id']}"))["last_done_meter"] is None
        assert next_due_meter(engineer_a, part) == "290"             # the part's reading 40 + 250, not the seed
        # an assignee save (the page sends no meter value it did not change) keeps the hidden value
        (before,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        changed = settings(engineer_a, plan, assignee_id=technician["id"])
        assert changed["assignee"]["id"] == technician["id"] and changed["last_done_meter"] is None
        (after,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert [after[c] for c in SEED_COLUMNS] == [before[c] for c in SEED_COLUMNS]
        # the same link again: the plan uses the press's meter again and the value counts again
        _ok(engineer_a.put(f"{EQUIPMENT}/{part['id']}/meters/{hours['id']}", json={"active": False}))
        link_meter(engineer_a, part, press, hours)
        assert _ok(engineer_a.get(f"{PLANS}/{plan['id']}"))["last_done_meter"] == "1000"
        # a typed value is stored for the meter the plan uses now (the part's own again)
        unlink_meter(engineer_a, part, hours)
        add_own_meter(part, hours)
        plan = settings(engineer_a, plan, last_done_meter="1000")     # the same number, now for the part's meter
        assert plan["last_done_meter"] == "1000"
        (row,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert (row["seed_meter_equipment_id"], row["seed_meter_type_id"]) == (part["id"], hours["id"])
        assert next_due_meter(engineer_a, part) == "1250"            # the seed 1000 + 250

    def test_clearing_the_unused_seed_keeps_the_open_job_s_reschedule(self, engineer_a, press, hours, make_equipment,
                                                                      add_own_meter, db_rows):
        """CR4-01: the base of the next due comes from the meter's readings, with or without the unused seed, so a
        clear sent by the API does not move the due and a supervisor's move of the open job holds (S101 D4 stays for
        a real change)."""
        part = make_equipment(parent=press)
        link_meter(engineer_a, part, press, hours)
        template = make_template(engineer_a, trigger_kind="both", calendar_every=30, calendar_unit="day",
                                 meter_type_id=hours["id"], meter_every="250")
        plan = attach(engineer_a, part, template)
        settings(engineer_a, plan, last_done_on=overdue(db_rows)["last_done_on"], last_done_meter="1000")
        unlink_meter(engineer_a, part, hours)
        add_own_meter(part, hours)
        add_reading(db_rows, part, hours, "40", db_now(db_rows) - timedelta(minutes=1))
        (job,) = jobs_of(db_rows, plan["id"])
        moved_to = (db_now(db_rows).date() + timedelta(days=5)).isoformat()
        _ok(engineer_a.post(f"/api/pm/jobs/{job['id']}/reschedule", json={"due_on": moved_to, "remark": "Shutdown"}))
        cleared = settings(engineer_a, plan, last_done_meter=None)
        assert cleared["last_done_meter"] is None
        (row,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert [row[c] for c in SEED_COLUMNS] == [None, None, None]
        (after,) = jobs_of(db_rows, plan["id"])
        assert (after["id"], after["rescheduled_on"].isoformat()) == (job["id"], moved_to)

    def test_the_card_resolves_every_plan_in_one_pass(self, engineer_a, press, hours, oil, make_equipment,
                                                      monkeypatch):
        part = make_equipment(parent=press)
        link_meter(engineer_a, part, press, hours)
        for node in (press, press, part):
            attach(engineer_a, node, meter_template(engineer_a, hours))
        calls, link_calls = [], []
        # the two reads live in equipment.py since CR8-01 (meters_on_paths is there); keep the real ones to call
        real_in_force, real_links = equipment.meters_in_force, equipment.read_meter_links

        def counted(cur, nodes):
            calls.append(len(nodes))
            return real_in_force(cur, nodes)

        def counted_links(cur, node_ids):
            link_calls.append(len(node_ids))
            return real_links(cur, node_ids)

        monkeypatch.setattr("equipment.meters_in_force", counted)
        monkeypatch.setattr("equipment.read_meter_links", counted_links)
        items = card(engineer_a, press)["items"]
        assert len(items) == 3 and all(item["applies"] for item in items)
        assert (len(calls), len(link_calls)) == (1, 1)


# ---------------------------------------------------------------------------
# The plan settings (§ 5.5)
# ---------------------------------------------------------------------------

class TestSettings:

    def test_assignee_and_last_done(self, eng, press, hours, technician, db_rows):
        client, _ = eng
        plan = attach(client, press, make_template(client, trigger_kind="both", **{
            "meter_type_id": hours["id"], "meter_every": "250"}))
        today = db_now(db_rows).date()
        plan = settings(client, plan, assignee_id=technician["id"], last_done_on=today.isoformat(),
                        last_done_meter="1840.5")
        assert (plan["assignee"]["id"], plan["last_done_on"], plan["last_done_meter"]) == (
            technician["id"], today.isoformat(), "1840.5")
        (row,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert (row["seed_meter_equipment_id"], row["seed_meter_type_id"]) == (press["id"], hours["id"])
        plan = settings(client, plan, last_done_meter=None)
        (row,) = db_rows("SELECT * FROM pm_plans WHERE id = %s", (plan["id"],))
        assert (row["last_done_meter"], row["seed_meter_equipment_id"], row["seed_meter_type_id"]) == (None,) * 3

    def test_the_refusals(self, engineer_a, press, hours, make_person, other_site, give_site_role, db_rows,
                          make_equipment, unit):
        plan = attach(engineer_a, press, make_template(engineer_a))
        url = f"{PLANS}/{plan['id']}"
        stranger = make_person(name="Elsewhere")
        give_site_role(stranger, other_site, "maint_technician")
        assert refused(engineer_a.put(url, json={"assignee_id": stranger["id"]})) == (
            400, "assignee_id", ASSIGNEE_AT_SITE)
        tomorrow = (db_now(db_rows).date() + timedelta(days=1)).isoformat()
        assert refused(engineer_a.put(url, json={"last_done_on": tomorrow})) == (400, "last_done_on", LAST_DONE_DATE)
        assert refused(engineer_a.put(url, json={"last_done_meter": "10"})) == (
            400, "last_done_meter", NO_METER_TRIGGER)
        assert refused(engineer_a.put(url, json={"items": []})) == (400, "items", CHANGE_ON_TEMPLATE)
        assert refused(engineer_a.put(url, json={"template_id": 1})) == (400, "template_id", PLAN_FIXED)
        assert refused(engineer_a.put(url, json={"active": False})) == (400, "active", "Unknown field: active.")
        bare = make_equipment(unit=unit)       # a fresh model: the press fixture's meters are on the press only
        lacking = attach(engineer_a, bare, meter_template(engineer_a, hours))
        assert refused(engineer_a.put(f"{PLANS}/{lacking['id']}", json={"last_done_meter": "10"})) == (
            400, "last_done_meter", f"This machine has no {hours['name']} meter. Add the meter first.")

    def test_an_operator_template_has_no_assignee(self, engineer_a, press, technician):
        plan = attach(engineer_a, press, make_template(engineer_a, performer="operator"))
        assert refused(engineer_a.put(f"{PLANS}/{plan['id']}", json={"assignee_id": technician["id"]})) == (
            400, "assignee_id", OPERATOR_NO_ASSIGNEE)

    def test_a_seed_change_drops_a_reschedule(self, engineer_a, press, db_rows):
        plan = attach(engineer_a, press, make_template(engineer_a, calendar_every=30, calendar_unit="day"))
        plan = settings(engineer_a, plan, last_done_on=overdue(db_rows)["last_done_on"])
        (job,) = jobs_of(db_rows, plan["id"])
        moved_to = (db_now(db_rows).date() + timedelta(days=5)).isoformat()
        _ok(engineer_a.post(f"/api/pm/jobs/{job['id']}/reschedule", json={"due_on": moved_to, "remark": "Shutdown"}))
        settings(engineer_a, plan, last_done_on=(db_now(db_rows).date() - timedelta(days=35)).isoformat())
        assert jobs_of(db_rows, plan["id"])[0]["rescheduled_on"] is None

    def test_scrapped_is_read_only(self, engineer_a, admin, press):
        plan = attach(engineer_a, press, make_template(engineer_a))
        scrap(admin, press)
        assert refused(engineer_a.put(f"{PLANS}/{plan['id']}", json={"assignee_id": None})) == (409, None, SCRAPPED)


# ---------------------------------------------------------------------------
# Remove and attach again (§ 5.5)
# ---------------------------------------------------------------------------

class TestRemove:

    def test_remove_unlinks_and_cancels_the_due_job(self, engineer_a, press, technician, db_rows):
        template = make_template(engineer_a, calendar_every=30, calendar_unit="day")
        plan = attach(engineer_a, press, template)
        settings(engineer_a, plan, assignee_id=technician["id"], last_done_on=overdue(db_rows)["last_done_on"])
        (job,) = jobs_of(db_rows, plan["id"])
        body = _ok(engineer_a.post(f"{PLANS}/{plan['id']}/remove"))
        assert (body["linked"], body["stop_remark"], body["can_remove"]) == (False, UNLINKED_REMARK, False)
        (link,) = db_rows("SELECT * FROM pm_template_links WHERE template_id = %s", (template["id"],))
        assert (link["active"], link["removed_by"] is not None) == (0, True)
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "cancelled"
        assert events_of(db_rows, job["id"])[-1]["remark"] == UNLINKED_REMARK
        listed = card(engineer_a, press)
        assert listed["items"] == [] and [p["id"] for p in listed["unlinked"]] == [plan["id"]]
        assert refused(engineer_a.post(f"{PLANS}/{plan['id']}/remove")) == (
            409, None, "This plan does not come from a link to this machine.")

        again = attach(engineer_a, press, template)                          # the same row, its history kept
        assert (again["id"], again["linked"], again["assignee"]["id"]) == (plan["id"], True, technician["id"])
        assert len(db_rows("SELECT id FROM pm_template_links WHERE template_id = %s", (template["id"],))) == 2

    def test_a_started_job_is_left_to_finish(self, engineer_a, press, tech, db_rows):
        client, person = tech
        plan = attach(engineer_a, press, make_template(engineer_a, calendar_every=30, calendar_unit="day"))
        settings(engineer_a, plan, last_done_on=overdue(db_rows)["last_done_on"])
        (job,) = jobs_of(db_rows, plan["id"])
        _ok(client.post(f"/api/pm/jobs/{job['id']}/start", json={"performed_by_id": person["id"]}))
        _ok(engineer_a.post(f"{PLANS}/{plan['id']}/remove"))
        assert jobs_of(db_rows, plan["id"])[0]["state"] == "in_progress"


# ---------------------------------------------------------------------------
# Reads (§ 6)
# ---------------------------------------------------------------------------

class TestReads:

    def test_the_card_lists_own_plans_first_and_names_the_part(self, engineer_a, press, make_equipment, at_site):
        part = make_equipment(parent=press)
        own = attach(engineer_a, press, make_template(engineer_a))
        parts = attach(engineer_a, part, make_template(engineer_a))
        body = card(at_site("maint_technician"), press)
        assert [(p["id"], p["own"], p["equipment"]["code"]) for p in body["items"]] == [
            (own["id"], True, press["code"]), (parts["id"], False, part["code"])]
        assert body["can_add"] is False and body["unlinked"] == []
        assert card(engineer_a, press)["can_add"] is True

    def test_it_admin_reads_and_cannot_write(self, engineer_a, press, role_client):
        plan = attach(engineer_a, press, make_template(engineer_a))
        reader = role_client("it_admin")
        assert _ok(reader.get(f"{PLANS}/{plan['id']}"))["can_edit"] is False
        assert reader.put(f"{PLANS}/{plan['id']}", json={"assignee_id": None}).status_code == 403

    def test_another_site_and_a_missing_plan(self, engineer_a, press, user_at_sites, other_site):
        plan = attach(engineer_a, press, make_template(engineer_a))
        elsewhere, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert elsewhere.get(f"{PLANS}/{plan['id']}").status_code == 404
        assert engineer_a.get(f"{PLANS}/99999999").status_code == 404


def test_the_database_down(db_down, engineer):
    assert engineer.get(PLANS, query_string={"equipment_id": 1}).status_code == 503
    assert engineer.post(PLANS, json={"equipment_id": 1, "template_id": 1}).status_code == 503


@pytest.mark.parametrize("path", [f"{PLANS}/1/remove"])
def test_writes_need_the_key(at_site, path):
    assert at_site("maint_technician").post(path).status_code == 403
