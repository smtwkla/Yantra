"""Parts used on a ticket (S020 § 8 / § 3 Tests), against the test DB.  Needs the dev MariaDB
container (tooling/dev/dev-db-up.bat).

The lines follow labour's routes and rules: ticket:work at the ticket's site, the ticket locked
first, refusals 404 → 403 → 409 → 400.  The node is the ticket's machine or a part below it,
checked on an add and when it changes.
"""

import pytest

import tickets
from tests.conftest import EQUIPMENT
from tests.ticket_helpers import refusal
from tests.test_ticket_work_api import detail, move, move_names, moved, plan_day, url
from tickets_core import PARTS_NOT_A_FAULT, PART_NODE_NEEDED


@pytest.fixture
def site(unit):
    return {"id": unit["site_id"]}


@pytest.fixture
def tech(user_at_sites, site, unit):
    return user_at_sites([(site, "maint_technician", [unit])])


@pytest.fixture
def eng(user_at_sites, site, unit):
    return user_at_sites([(site, "maint_engineer", [unit])])


@pytest.fixture
def ticket(make_ticket, machine):
    return make_ticket(machine)


@pytest.fixture
def part(make_equipment, machine):
    """A component-unit of the machine (one level down)."""
    return make_equipment(parent=machine)


@pytest.fixture
def no_cause(db_rows):
    return db_rows("SELECT id FROM failure_causes WHERE code = '5.1'")[0]["id"]


def line(node, **overrides):
    """The short way of § 8: a description, a standard number, quantity 1 (unit nos by default)."""
    return {"description": "Deep-groove ball bearing", "part_number": "6205-2RS", "number_kind": "generic",
            "quantity": "1", "node_id": node["id"], **overrides}


def add(client, ticket, node, **overrides):
    return client.post(url(ticket, "parts"), json=line(node, **overrides))


def added(client, ticket, node, **overrides):
    res = add(client, ticket, node, **overrides)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def suggestions(client, ticket):
    res = client.get(url(ticket, "part-suggestions"))
    assert res.status_code == 200, res.get_json()
    return res.get_json()


class TestLines:

    def test_add_change_remove(self, tech, ticket, part):
        client, _ = tech
        done = added(client, ticket, part, quantity="1.5", qty_unit="m", maker="SKF")
        row = done["parts"][0]
        assert {k: row[k] for k in ("description", "part_number", "number_kind", "maker", "quantity", "qty_unit")} == {
            "description": "Deep-groove ball bearing", "part_number": "6205-2RS", "number_kind": "generic",
            "maker": "SKF", "quantity": "1.50", "qty_unit": "m"}
        assert row["node"] == {"id": part["id"], "code": part["code"], "name": part["name"]}
        assert row["created_by"]
        changed = client.put(url(ticket, "parts", str(row["id"])), json=line(part, quantity="2"))
        assert changed.status_code == 200, changed.get_json()
        assert (changed.get_json()["parts"][0]["quantity"], changed.get_json()["parts"][0]["qty_unit"]) == ("2.00", "nos")
        removed = client.delete(url(ticket, "parts", str(row["id"])))
        assert removed.status_code == 200 and removed.get_json()["parts"] == []
        assert client.delete(url(ticket, "parts", str(row["id"]))).status_code == 404

    def test_no_timeline_line(self, admin, ticket, part):
        assert [e["event"] for e in added(admin, ticket, part)["events"]] == ["raised"]

    def test_the_detail_lists_lines_in_entry_order(self, admin, ticket, machine, part):
        added(admin, ticket, part, description="First")
        added(admin, ticket, machine, description="Second", part_number=None)
        shown = detail(admin, ticket)
        assert [p["description"] for p in shown["parts"]] == ["First", "Second"]
        assert shown["parts"][1]["node"]["id"] == machine["id"]
        assert (shown["parts"][1]["part_number"], shown["parts"][1]["number_kind"]) == (None, None)

    def test_a_ticket_without_lines_shows_an_empty_list(self, admin, ticket):
        assert detail(admin, ticket)["parts"] == []

    def test_a_kind_sent_without_a_number_is_stored_null(self, admin, ticket, part):
        row = added(admin, ticket, part, part_number="  ", number_kind="maker")["parts"][0]
        assert (row["part_number"], row["number_kind"]) == (None, None)

    def test_the_field_refusals_name_the_body_field(self, admin, ticket, part):
        assert refusal(add(admin, ticket, part, number_kind="maker"))[:2] == (400, "maker")
        assert refusal(add(admin, ticket, part, quantity="0")) == (400, "quantity", "Enter a quantity, e.g. 2 or 1.5")
        assert refusal(add(admin, ticket, part, quantity="1.505"))[:2] == (400, "quantity")
        assert refusal(add(admin, ticket, part, qty_unit="mtr"))[:2] == (400, "qty_unit")
        assert refusal(add(admin, ticket, part, description=""))[:2] == (400, "description")


class TestFittedTo:

    def test_the_machine_and_two_levels_below_it(self, admin, make_equipment, machine, part, ticket):
        below = make_equipment(parent=part, level="component")
        for node in (machine, part, below):
            assert added(admin, ticket, node)["parts"][-1]["node"]["id"] == node["id"]

    def test_outside_the_machine_is_400(self, admin, make_equipment, ticket):
        other_machine = make_equipment()
        other_part = make_equipment(parent=other_machine)
        for node in (other_machine, other_part, {"id": 999999999}):
            assert refusal(add(admin, ticket, node)) == (400, "node_id", PART_NODE_NEEDED)

    def test_a_scrapped_part_is_400(self, admin, ticket, part):
        assert admin.put(f"{EQUIPMENT}/{part['id']}", json={"lifecycle": "scrapped"}).status_code == 200
        assert refusal(add(admin, ticket, part)) == (400, "node_id", PART_NODE_NEEDED)

    def test_an_edit_keeping_a_node_scrapped_since_succeeds(self, admin, ticket, machine, part, make_equipment):
        """BR1-03: the line is history; only a changed node is checked."""
        row = added(admin, ticket, part)["parts"][0]
        assert admin.put(f"{EQUIPMENT}/{part['id']}", json={"lifecycle": "scrapped"}).status_code == 200
        kept = admin.put(url(ticket, "parts", str(row["id"])), json=line(part, quantity="3"))
        assert kept.status_code == 200, kept.get_json()
        assert kept.get_json()["parts"][0]["quantity"] == "3.00"
        # Back to the scrapped node after a change: refused
        other = make_equipment(parent=machine)
        assert admin.put(url(ticket, "parts", str(row["id"])), json=line(other)).status_code == 200
        assert refusal(admin.put(url(ticket, "parts", str(row["id"])), json=line(part))) == (
            400, "node_id", PART_NODE_NEEDED)

    def test_a_scrap_committed_during_the_add_is_seen(self, admin, ticket, part, db_rows, monkeypatch):
        """§ 5.2 step 3: the node is read with a locking read, which sees the latest committed row;
        a plain read would see the snapshot the ticket's read took before the scrap committed."""
        real_lock = tickets._lock_open_ticket

        def lock_then_scrap_elsewhere(cur, ticket_id, key):
            locked = real_lock(cur, ticket_id, key)   # its plain read has taken the snapshot
            db_rows("UPDATE equipment SET lifecycle = 'scrapped' WHERE id = %s", (part["id"],))
            return locked
        monkeypatch.setattr(tickets, "_lock_open_ticket", lock_then_scrap_elsewhere)
        assert refusal(add(admin, ticket, part)) == (400, "node_id", PART_NODE_NEEDED)

    def test_the_ticket_edit_still_refuses_the_machine_itself(self, admin, machine, ticket):
        """The shared helper admits the machine only for a parts line (machine_counts)."""
        assert refusal(admin.put(url(ticket), json={"component_id": machine["id"]}))[:2] == (400, "component_id")


class TestAccess:

    def test_a_closed_ticket_is_409(self, admin, ticket, part, set_ticket_state):
        row = added(admin, ticket, part)["parts"][0]
        set_ticket_state(ticket, "closed")
        assert refusal(add(admin, ticket, part)) == (409, None, "This ticket is closed")
        assert refusal(admin.put(url(ticket, "parts", str(row["id"])), json=line(part)))[0] == 409
        assert refusal(admin.delete(url(ticket, "parts", str(row["id"]))))[0] == 409
        assert len(detail(admin, ticket)["parts"]) == 1

    def test_without_ticket_work_is_403(self, operator, admin, ticket, part):
        row = added(admin, ticket, part)["parts"][0]
        assert add(operator, ticket, part).status_code == 403
        assert operator.put(url(ticket, "parts", str(row["id"])), json=line(part)).status_code == 403
        assert operator.delete(url(ticket, "parts", str(row["id"]))).status_code == 403
        assert operator.get(url(ticket, "part-suggestions")).status_code == 403
        # ...and the operator still reads the lines on the detail (ticket:read)
        assert len(detail(operator, ticket)["parts"]) == 1

    def test_the_key_is_checked_at_the_tickets_site(self, admin, user_at_sites, make_unit, make_site, machine,
                                                     ticket, part):
        """A technician at the machine's new site reads the ticket but may not record parts on it."""
        new_site = make_site()
        new_unit = make_unit(new_site)
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": new_unit["id"]}).status_code == 200
        client, _ = user_at_sites([(new_site, "maint_technician", [new_unit])])
        assert client.get(url(ticket)).status_code == 200
        assert add(client, ticket, part).status_code == 403
        assert client.get(url(ticket, "part-suggestions")).status_code == 403

    def test_outside_the_users_units_is_404(self, user_with_units, make_unit, admin, ticket, part):
        row = added(admin, ticket, part)["parts"][0]
        other = user_with_units("maint_engineer", [make_unit()])
        for res in (add(other, ticket, part),
                    other.put(url(ticket, "parts", str(row["id"])), json=line(part)),
                    other.delete(url(ticket, "parts", str(row["id"]))),
                    other.get(url(ticket, "part-suggestions"))):
            assert res.status_code == 404, res.get_json()

    def test_a_line_of_another_ticket_is_404(self, admin, make_ticket, machine, ticket, part):
        other = make_ticket(machine, description="Another")
        row = added(admin, other, part)["parts"][0]
        assert admin.put(url(ticket, "parts", str(row["id"])), json=line(part)).status_code == 404
        assert admin.delete(url(ticket, "parts", str(row["id"]))).status_code == 404
        assert len(detail(admin, other)["parts"]) == 1

    def test_a_scheduled_ticket_takes_lines(self, eng, ticket, part):
        client, _ = eng
        moved(client, ticket, "schedule", planned_date=plan_day(2), waiting_reason="parts")
        assert len(added(client, ticket, part)["parts"]) == 1


class TestNotAFault:

    def test_refused_with_lines_from_every_open_state_then_allowed(self, admin, eng, make_ticket, machine, part,
                                                                   no_cause):
        eng_client, _ = eng
        raised = make_ticket(machine, description="Raised")
        acknowledged = make_ticket(machine, description="Acknowledged")
        moved(admin, acknowledged, "acknowledge")
        scheduled = make_ticket(machine, description="Scheduled")
        moved(eng_client, scheduled, "schedule", planned_date=plan_day(2), waiting_reason="parts")
        in_progress = make_ticket(machine, description="In progress")
        moved(admin, in_progress, "start")
        for ticket in (raised, acknowledged, scheduled, in_progress):
            row = added(admin, ticket, part)["parts"][0]
            assert refusal(move(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Nothing wrong")) == (
                409, None, PARTS_NOT_A_FAULT), ticket["description"]
            assert admin.delete(url(ticket, "parts", str(row["id"]))).status_code == 200
            done = moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Nothing wrong")
            assert (done["state"], done["not_a_fault"]) == ("closed", True)


class TestCloseHint:

    def test_the_close_entry_carries_replace_modify_and_overhaul(self, admin, ticket, db_rows):
        ids = {r["code"]: r["id"] for r in db_rows("SELECT id, code FROM maintenance_actions")}
        db_rows("UPDATE tickets SET state = 'back_in_service' WHERE id = %s", (ticket["id"],))
        shown = detail(admin, ticket)
        close = next(m for m in shown["moves"] if m["name"] == "close")
        assert close["parts_hint_actions"] == sorted([ids["1"], ids["3"], ids["10"]])
        assert all("parts_hint_actions" not in m for m in shown["moves"] if m["name"] != "close")

    def test_a_deactivated_action_keeps_its_hint(self, admin, ticket, db_rows):
        ids = {r["code"]: r["id"] for r in db_rows("SELECT id, code FROM maintenance_actions")}
        db_rows("UPDATE tickets SET state = 'back_in_service' WHERE id = %s", (ticket["id"],))
        db_rows("UPDATE maintenance_actions SET active = 0 WHERE code = '3'")
        try:
            close = next(m for m in detail(admin, ticket)["moves"] if m["name"] == "close")
            assert ids["3"] in close["parts_hint_actions"]
        finally:
            db_rows("UPDATE maintenance_actions SET active = 1 WHERE code = '3'")

    def test_no_close_entry_no_hint(self, admin, ticket):
        assert "close" not in move_names(detail(admin, ticket))


class TestSuggestions:

    def test_lines_of_the_same_machine_on_any_ticket_newest_first_distinct(self, admin, make_ticket, machine, part,
                                                                            make_equipment, ticket):
        below = make_equipment(parent=part, level="component")
        earlier = make_ticket(machine, description="Earlier")
        added(admin, earlier, part, description="Seal kit", part_number="SK-100", number_kind="maker",
              maker="Rexroth")
        added(admin, earlier, below, description="Coupling insert", part_number=None)
        added(admin, earlier, machine, description="Seal kit", part_number="SK-100", number_kind="maker",
              maker="Rexroth", quantity="2")      # the same four fields: one suggestion
        # Another machine's line is never offered
        other_machine = make_equipment()
        added(admin, make_ticket(other_machine, description="Elsewhere"), other_machine, description="Not here")

        shown = suggestions(admin, ticket)
        assert shown["items"] == [
            {"part_number": "SK-100", "number_kind": "maker", "maker": "Rexroth", "description": "Seal kit"},
            {"part_number": None, "number_kind": None, "maker": None, "description": "Coupling insert"},
        ]
        assert shown["total"] == 2

    def test_another_sites_machine_is_not_offered(self, admin, make_ticket, make_site, make_unit, make_equipment,
                                                  machine, ticket):
        far_machine = make_equipment(unit=make_unit(make_site()))
        added(admin, make_ticket(far_machine, description="Far"), far_machine, description="Far part")
        assert all(s["description"] != "Far part" for s in suggestions(admin, ticket)["items"])

    def test_at_most_twenty(self, admin, make_ticket, machine, ticket, db_rows):
        earlier = make_ticket(machine, description="Earlier")
        for n in range(22):
            db_rows("INSERT INTO ticket_parts (ticket_id, node_id, description, quantity, created_by)"
                    " VALUES (%s, %s, %s, 1, 'test')", (earlier["id"], machine["id"], f"Part {n:02d}"))
        shown = suggestions(admin, ticket)
        assert shown["total"] == len(shown["items"]) == tickets.PART_SUGGESTIONS_MAX == 20
        assert shown["items"][0]["description"] == "Part 21"     # newest first
        assert shown["items"][-1]["description"] == "Part 02"

    def test_a_technician_at_the_site_may_read_them(self, tech, ticket):
        client, _ = tech
        assert suggestions(client, ticket) == {"items": [], "total": 0}
