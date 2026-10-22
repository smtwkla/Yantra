"""Tickets — raise and see (S017 § 8), against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).

Isolation: the test DB is emptied once per session and IT admin sees every unit, so list
assertions filter by a fresh unit (or machine) of their own.
"""

from datetime import datetime, timedelta

import pytest

import tickets
from tests.conftest import EQUIPMENT, MASTERS, SERVER_ERROR, TICKETS, server_error
from tests.ticket_helpers import api_time as _api_time
from tests.ticket_helpers import local as _local
from tests.ticket_helpers import now_ist as _now_ist
from tests.ticket_helpers import refusal as _refusal


def _list(client, **params):
    res = client.get(TICKETS, query_string=params)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _serials(page):
    return [t["serial"] for t in page["items"]]


def _number(serial):
    return int(serial.rsplit("-", 1)[1])


class TestRaise:

    def test_on_a_machine(self, operator, machine, unit, db_rows):
        before = _now_ist().replace(microsecond=0)
        res = operator.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                           "description": "  Stopped with a bang  "})
        assert res.status_code == 201, res.get_json()
        ticket = res.get_json()
        now = _now_ist()
        assert ticket["serial"].startswith(f"TK-{now:%Y-%m}-")
        assert (ticket["state"], ticket["intensity"], ticket["is_breakdown"]) == ("raised", "critical", True)
        assert ticket["machine"] == {"id": machine["id"], "code": machine["code"], "name": machine["name"],
                                     "class_code": machine["class_code"]}
        assert ticket["component"] is None and ticket["failure_mode"] is None and ticket["reported_by"] is None
        assert ticket["unit"] == {"id": unit["id"], "code": unit["code"], "site_code": machine["unit"].split(".")[0]}
        assert ticket["description"] == "Stopped with a bang"
        assert ticket["created_by"] == operator._headers["X-Test-User"]
        # No occurred_at sent: the server's clock (BR2-05)
        occurred = datetime.strptime(ticket["occurred_at"], "%Y-%m-%dT%H:%M:%S+05:30")
        assert before - timedelta(seconds=1) <= occurred <= now + timedelta(seconds=1)
        assert ticket["can_add_photos"] is True
        assert [(e["event"], e["from_state"], e["to_state"], e["occurred_at"], e["intensity"], e["person"])
                for e in ticket["events"]] == [("raised", None, "raised", ticket["occurred_at"], "critical", None)]
        stored = db_rows("SELECT equipment_id, component_id, unit_id, source FROM tickets WHERE id = %s",
                         (ticket["id"],))[0]
        assert stored == {"equipment_id": machine["id"], "component_id": None, "unit_id": unit["id"],
                          "source": "manual"}

    def test_on_a_component_unit_and_components(self, make_equipment, make_ticket, machine):
        unit_node = make_equipment(parent=machine)
        component = make_equipment(parent=unit_node, level="component")
        direct = make_equipment(parent=machine, level="component")
        for node in (unit_node, component, direct):
            ticket = make_ticket(node, intensity="degraded")
            assert ticket["machine"]["id"] == machine["id"]
            assert ticket["component"] == {"id": node["id"], "code": node["code"], "name": node["name"]}
            assert ticket["is_breakdown"] is False

    def test_event_time_entered(self, make_ticket, machine):
        when = (_now_ist() - timedelta(days=2)).replace(second=0, microsecond=0)
        ticket = make_ticket(machine, occurred_at=_local(when), intensity="initial")
        assert ticket["occurred_at"] == _api_time(when)
        assert ticket["events"][0]["occurred_at"] == _api_time(when)
        # The serial says when it was written, not when it happened
        assert ticket["serial"].startswith(f"TK-{_now_ist():%Y-%m}-")

    def test_consecutive_serials(self, make_ticket, machine):
        first, second = make_ticket(machine), make_ticket(machine)
        assert _number(second["serial"]) == _number(first["serial"]) + 1

    def test_a_failed_raise_leaves_no_gap(self, monkeypatch, make_ticket, admin, machine):
        first = make_ticket(machine)
        real_insert = tickets.insert_row

        def failing_insert(cur, table, clean, actor):
            if table == "tickets":
                raise RuntimeError("insert failed after the counter bump")
            return real_insert(cur, table, clean, actor)

        monkeypatch.setattr(tickets, "insert_row", failing_insert)
        # The 500 is JSON (S025 § 1.3); the rollback after it is what this tests
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical", "description": "x"})
        assert server_error(res) == SERVER_ERROR
        monkeypatch.undo()
        assert _number(make_ticket(machine)["serial"]) == _number(first["serial"]) + 1

    def test_a_general_mode_on_any_machine_and_a_class_mode_on_its_class(self, make_ticket, make_mode,
                                                                          make_equipment, db_rows):
        noise = db_rows("SELECT id FROM failure_modes WHERE code = 'NOI'")[0]["id"]
        ticket = make_ticket(make_equipment(), failure_mode_id=noise, description=None)
        assert ticket["failure_mode"] == {"id": noise, "code": "NOI", "label": "Abnormal noise"}
        machine = make_equipment()
        mode = make_mode(cls={"id": machine["class_id"]})
        part = make_equipment(parent=machine)
        # On a part, the machine's class counts (S016 § 5.4)
        assert make_ticket(part, failure_mode_id=mode["id"])["failure_mode"]["id"] == mode["id"]

    def test_an_operator_without_a_login_as_reporter(self, make_ticket, make_person, give_site_role, machine, unit):
        person = make_person(name="Murugan")
        give_site_role(person, {"id": unit["site_id"]})
        ticket = make_ticket(machine, reported_by_id=person["id"])
        assert ticket["reported_by"] == {"id": person["id"], "name": "Murugan"}


class TestRaiseRefusals:

    def test_scrapped_node_is_409(self, admin, make_equipment, machine):
        part = make_equipment(parent=machine)
        assert admin.put(f"{EQUIPMENT}/{part['id']}", json={"status": "scrapped"}).status_code == 200
        res = admin.post(TICKETS, json={"equipment_id": part["id"], "intensity": "critical", "description": "x"})
        assert _refusal(res) == (409, None, "Scrapped equipment takes no tickets")

    def test_a_part_of_a_scrapped_machine_is_409(self, admin, make_equipment, machine, db_rows):
        part = make_equipment(parent=machine)
        db_rows("UPDATE equipment SET status = 'scrapped' WHERE id = %s", (machine["id"],))
        res = admin.post(TICKETS, json={"equipment_id": part["id"], "intensity": "critical", "description": "x"})
        assert _refusal(res) == (409, None, "Scrapped equipment takes no tickets")

    def test_a_node_outside_the_users_units_is_404(self, user_with_units, make_unit, machine):
        other = user_with_units("maint_operator", [make_unit()])
        res = other.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical", "description": "x"})
        assert res.status_code == 404

    def test_unknown_node_is_404(self, admin):
        res = admin.post(TICKETS, json={"equipment_id": 999999999, "intensity": "critical", "description": "x"})
        assert res.status_code == 404

    def test_raise_not_held_at_the_site_is_403(self, user_at_sites, make_site, make_unit, make_equipment):
        site_a, site_b = make_site(), make_site()
        unit_a, unit_b = make_unit(site_a), make_unit(site_b)
        # An operator at A who is a storekeeper at B: reads B's equipment, may not raise there
        client, _ = user_at_sites([(site_a, "maint_operator", [unit_a]), (site_b, "maint_storekeeper", "all")])
        machine_b = make_equipment(unit=unit_b)
        res = client.post(TICKETS, json={"equipment_id": machine_b["id"], "intensity": "critical",
                                         "description": "x"})
        assert _refusal(res) == (403, None, f"You can't do this at {site_b['code']}")

    def test_storekeeper_is_403(self, role_client, machine):
        res = role_client("maint_storekeeper").post(TICKETS, json={"equipment_id": machine["id"],
                                                                   "intensity": "critical", "description": "x"})
        assert res.status_code == 403

    def test_mode_of_another_class_and_inactive_mode_are_400(self, admin, engineer, make_mode, make_class, machine):
        other = make_mode(cls=make_class())
        inactive = make_mode()
        assert engineer.put(f"{MASTERS}/failure-modes/{inactive['id']}", json={"active": False}).status_code == 200
        for mode in (other, inactive):
            res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                            "failure_mode_id": mode["id"]})
            assert _refusal(res) == (400, "failure_mode_id", "Choose a symptom from the list")
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "failure_mode_id": 999999999})
        assert _refusal(res)[:2] == (400, "failure_mode_id")

    def test_reporter_from_another_site_is_400(self, admin, make_person, make_site, give_site_role, machine):
        person = make_person()
        give_site_role(person, make_site())
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical", "description": "x",
                                        "reported_by_id": person["id"]})
        assert _refusal(res) == (400, "reported_by_id", "Choose a person from this site")

    def test_description_needed_without_a_symptom_or_with_other(self, admin, db_rows, machine):
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "degraded"})
        assert _refusal(res) == (400, "description", "Description is needed when no symptom is picked")
        other = db_rows("SELECT id FROM failure_modes WHERE code = 'OTH'")[0]["id"]
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "degraded",
                                        "failure_mode_id": other, "description": "  "})
        assert _refusal(res) == (400, "description", "Describe the problem when the symptom is Other")

    @pytest.mark.parametrize("body, field", [
        ({"occurred_at": "2026-10-20T10:00:00+05:30"}, "occurred_at"),
        ({"occurred_at": "2026-10-20T10:00Z"}, "occurred_at"),
        ({"intensity": "breakdown"}, "intensity"),
        ({"equipment_id": None}, "equipment_id"),
    ])
    def test_bad_body_is_400(self, admin, machine, body, field):
        res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                        "description": "x", **body})
        assert _refusal(res)[:2] == (400, field)

    def test_event_time_out_of_the_window_is_400(self, admin, machine):
        for when in (_now_ist() + timedelta(minutes=10), _now_ist() - timedelta(days=8)):
            res = admin.post(TICKETS, json={"equipment_id": machine["id"], "intensity": "critical",
                                            "description": "x", "occurred_at": _local(when)})
            assert _refusal(res)[:2] == (400, "occurred_at")


class TestList:

    def test_only_the_users_units_open_by_default(self, operator, make_ticket, make_equipment, make_unit, machine,
                                                  unit, set_ticket_state):
        mine = make_ticket(machine)
        closed = make_ticket(machine)
        set_ticket_state(closed, "closed")
        theirs = make_ticket(make_equipment(unit=make_unit()))
        page = _list(operator)
        ids = [t["id"] for t in page["items"]]
        assert mine["id"] in ids and closed["id"] not in ids and theirs["id"] not in ids
        assert all(t["unit"]["id"] == unit["id"] for t in page["items"])
        assert [t["id"] for t in _list(operator, state="closed")["items"]] == [closed["id"]]
        assert {t["id"] for t in _list(operator, state="all")["items"]} >= {mine["id"], closed["id"]}

    def test_order_open_by_intensity_then_oldest_closed_newest_first(self, admin, make_ticket, machine, unit,
                                                                    set_ticket_state):
        now = _now_ist().replace(second=0, microsecond=0)
        old_initial = make_ticket(machine, intensity="initial", occurred_at=_local(now - timedelta(hours=5)))
        new_critical = make_ticket(machine, intensity="critical", occurred_at=_local(now - timedelta(hours=1)))
        old_degraded = make_ticket(machine, intensity="degraded", occurred_at=_local(now - timedelta(hours=4)))
        old_critical = make_ticket(machine, intensity="critical", occurred_at=_local(now - timedelta(hours=3)))
        page = _list(admin, unit_id=unit["id"])
        assert [t["id"] for t in page["items"]] == [old_critical["id"], new_critical["id"], old_degraded["id"],
                                                    old_initial["id"]]
        for ticket in (old_initial, new_critical):
            set_ticket_state(ticket, "closed")
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], state="closed")["items"]] == [
            new_critical["id"], old_initial["id"]]
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], state="all")["items"]] == [
            new_critical["id"], old_critical["id"], old_degraded["id"], old_initial["id"]]

    def test_filters(self, admin, make_ticket, make_equipment, machine, unit):
        critical = make_ticket(machine, intensity="critical", description="Hydraulic hose burst")
        degraded = make_ticket(machine, intensity="degraded", description="Slow cycle")
        initial = make_ticket(machine, intensity="initial", description="Faint smell")
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], intensity="breakdown")["items"]] == [critical["id"]]
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], intensity="defect")["items"]] == [
            degraded["id"], initial["id"]]
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], intensity="initial")["items"]] == [initial["id"]]
        assert [t["id"] for t in _list(admin, unit_id=unit["id"], q="hose")["items"]] == [critical["id"]]
        assert [t["id"] for t in _list(admin, q=critical["serial"])["items"]] == [critical["id"]]
        assert _list(admin, unit_id=unit["id"], per_page=1, page=2)["items"][0]["id"] == degraded["id"]
        assert _list(admin, unit_id=unit["id"])["total"] == 3

    def test_site_filter(self, admin, make_site, make_unit, make_equipment, make_ticket):
        site = make_site()
        ticket = make_ticket(make_equipment(unit=make_unit(site)))
        other = make_ticket(make_equipment())
        ids = [t["id"] for t in _list(admin, site_id=site["id"])["items"]]
        assert ids == [ticket["id"]] and other["id"] not in ids

    def test_equipment_filter_machine_and_component(self, admin, make_ticket, make_equipment, machine):
        part = make_equipment(parent=machine)
        on_machine = make_ticket(machine)
        on_part = make_ticket(part)
        assert [t["id"] for t in _list(admin, equipment_id=machine["id"])["items"]] == [on_machine["id"],
                                                                                       on_part["id"]]
        assert [t["id"] for t in _list(admin, equipment_id=part["id"])["items"]] == [on_part["id"]]
        assert _list(admin, equipment_id=999999999)["items"] == []

    def test_bad_arguments_are_400(self, admin):
        for params, field in (({"state": "done"}, "state"), ({"intensity": "x"}, "intensity"),
                              ({"unit_id": "a"}, "unit_id"), ({"page": 0}, "page")):
            assert _refusal(admin.get(TICKETS, query_string=params))[:2] == (400, field)

    def test_a_user_with_no_units_gets_an_empty_list(self, user_with_units, make_ticket, machine):
        make_ticket(machine)
        assert _list(user_with_units("maint_operator", [])) == {"items": [], "total": 0, "page": 1, "per_page": 50}

    def test_admin_and_it_admin_see_every_unit(self, role_client, make_ticket, make_equipment, make_unit):
        ticket = make_ticket(make_equipment(unit=make_unit()))
        for role in ("admin", "it_admin"):
            assert ticket["id"] in [t["id"] for t in _list(role_client(role), unit_id=ticket["unit"]["id"])["items"]]

    def test_storekeeper_is_403(self, role_client):
        assert role_client("maint_storekeeper").get(TICKETS).status_code == 403


class TestDetailAndAccess:

    def test_detail(self, operator, make_ticket, machine):
        ticket = make_ticket(machine)
        res = operator.get(f"{TICKETS}/{ticket['id']}")
        assert res.status_code == 200
        # What this user may do differs from the raiser's (S018: keys at the ticket's site); the
        # ticket itself is the same
        per_user = {"permissions", "moves", "regrade_to", "can_add_documents", "can_add_photos", "can_raise_repeat"}
        shown = res.get_json()
        assert {k: v for k, v in shown.items() if k not in per_user} == {
            k: v for k, v in ticket.items() if k not in per_user}
        assert shown["can_add_photos"] is True

    def test_another_units_ticket_is_404(self, user_with_units, make_unit, make_ticket, machine):
        ticket = make_ticket(machine)
        assert user_with_units("maint_operator", [make_unit()]).get(f"{TICKETS}/{ticket['id']}").status_code == 404
        assert user_with_units("maint_operator", []).get(f"{TICKETS}/{ticket['id']}").status_code == 404

    def test_a_moved_machine_shows_to_the_old_and_the_new_unit(self, admin, user_with_units, make_unit, make_ticket,
                                                               machine, unit):
        ticket = make_ticket(machine)
        new_unit = make_unit()
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": new_unit["id"]}).status_code == 200
        old_team = user_with_units("maint_operator", [unit])
        new_team = user_with_units("maint_operator", [new_unit])
        neither = user_with_units("maint_operator", [make_unit()])
        for client in (old_team, new_team):
            assert client.get(f"{TICKETS}/{ticket['id']}").status_code == 200
            assert ticket["id"] in [t["id"] for t in _list(client)["items"]]
        assert neither.get(f"{TICKETS}/{ticket['id']}").status_code == 404
        assert ticket["id"] not in [t["id"] for t in _list(neither)["items"]]
        # The ticket keeps the unit where it happened
        assert admin.get(f"{TICKETS}/{ticket['id']}").get_json()["unit"]["id"] == unit["id"]

    def test_can_add_photos_false_when_closed(self, admin, make_ticket, machine, set_ticket_state):
        ticket = make_ticket(machine)
        set_ticket_state(ticket, "closed")
        assert admin.get(f"{TICKETS}/{ticket['id']}").get_json()["can_add_photos"] is False


class TestPickers:

    def test_modes_are_the_machines_class_then_general(self, admin, make_equipment, make_mode, make_class,
                                                       machine):
        mine = make_mode(cls={"id": machine["class_id"]}, label="Zz class mode")
        other = make_mode(cls=make_class())
        part = make_equipment(parent=machine)
        for node in (machine, part):
            res = admin.get(f"{TICKETS}/modes", query_string={"equipment_id": node["id"]})
            assert res.status_code == 200
            items = res.get_json()["items"]
            ids = [m["id"] for m in items]
            assert ids[0] == mine["id"] and other["id"] not in ids
            assert "NOI" in [m["code"] for m in items]
            # The class's modes first, then the General ones
            assert all(m["class_id"] is None for m in items[1:])

    def test_modes_refusals(self, admin, user_with_units, make_unit, machine):
        assert _refusal(admin.get(f"{TICKETS}/modes"))[:2] == (400, "equipment_id")
        other = user_with_units("maint_operator", [make_unit()])
        assert other.get(f"{TICKETS}/modes", query_string={"equipment_id": machine["id"]}).status_code == 404

    def test_people_of_the_site_with_trades_and_role(self, admin, make_person, make_trade, make_site,
                                                     give_site_role, machine, unit):
        unit_site = unit["site_id"]
        trade = make_trade()
        here = make_person(name="Aa operator here", trades=[trade])
        give_site_role(here, {"id": unit_site})
        there = make_person(name="Aa operator there")
        give_site_role(there, make_site())
        inactive = make_person(name="Aa inactive")
        give_site_role(inactive, {"id": unit_site})
        assert admin.put(f"{MASTERS}/people/{inactive['id']}", json={"active": False}).status_code == 200
        res = admin.get(f"{TICKETS}/people", query_string={"equipment_id": machine["id"]})
        assert res.status_code == 200
        people = res.get_json()["items"]
        assert [p["id"] for p in people] == [here["id"]]
        assert people[0] == {"id": here["id"], "name": "Aa operator here", "role": "maint_operator",
                             "assignable": False, "trades": [{"id": trade["id"], "name": trade["name"]}]}
