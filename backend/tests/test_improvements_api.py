"""Improvements (S067 § 8.2), against the test DB.  Needs the dev MariaDB container.

Each test makes its own site, unit, machine and tickets, so the kept worker database is the
starting state.  The engineers and managers have real memberships (user_at_sites), since the
lead rule and the site checks read memberships, never the token.  "Another site" is a person
with no membership at the record's site (404 by the predicate); "a key missing here" is a person
who is operator at this site and engineer at another (the predicate passes, the key does not:
403), BR1-03.
"""

import re
from datetime import timedelta

import pytest

import config_rbac
import improvements
from tests.conftest import EQUIPMENT, MASTERS, TICKETS
from tests.ticket_helpers import local, now_ist, refusal

IMPROVEMENTS = "/api/improvements"
SERIAL = re.compile(r"^IM-(\d{4})-(\d{2})-(\d{3,})$")


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def site(unit):
    return {"id": unit["site_id"]}


@pytest.fixture
def other_site(make_site):
    return make_site()


@pytest.fixture
def eng(user_at_sites, site):
    """(client, person): an engineer with all units of the ticket's site."""
    return user_at_sites([(site, "maint_engineer", "all")])


@pytest.fixture
def restored_ticket(make_ticket, set_ticket_state, machine):
    """make_ticket on the machine, written back in service: what a state allows, not how."""
    def make(state="back_in_service", node=None, **overrides):
        ticket = make_ticket(node or machine, **overrides)
        set_ticket_state(ticket, state)
        return ticket
    return make


@pytest.fixture
def no_cause(db_rows):
    return db_rows("SELECT id FROM failure_causes WHERE code = '5.1'")[0]["id"]


def body(ticket, lead, **overrides):
    return {"ticket_id": ticket["id"], "title": "Contactor trips", "problem": "Dust in the panel",
            "lead_id": lead["id"], **overrides}


def start(client, ticket, lead, **overrides):
    return client.post(IMPROVEMENTS, json=body(ticket, lead, **overrides))


def started(client, ticket, lead, **overrides):
    res = start(client, ticket, lead, **overrides)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def get(client, improvement):
    res = client.get(f"{IMPROVEMENTS}/{improvement['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def add(client, improvement, ticket):
    return client.post(f"{IMPROVEMENTS}/{improvement['id']}/tickets", json={"ticket_id": ticket["id"]})


def remove(client, improvement, ticket):
    return client.delete(f"{IMPROVEMENTS}/{improvement['id']}/tickets/{ticket['id']}")


def ticket_detail(client, ticket):
    res = client.get(f"{TICKETS}/{ticket['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def number(serial):
    return int(SERIAL.match(serial).group(3))


def moved(client, ticket, name, **move_body):
    res = client.post(f"{TICKETS}/{ticket['id']}/moves/{name}", json=move_body)
    assert res.status_code == 200, res.get_json()
    return res.get_json()


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

class TestStart:

    @pytest.mark.parametrize("state", ["back_in_service", "closed"])
    def test_from_back_in_service_and_closed(self, eng, restored_ticket, machine, unit, state):
        client, person = eng
        ticket = restored_ticket(state)
        made = started(client, ticket, person)
        now = now_ist()
        assert SERIAL.match(made["serial"]).groups()[:2] == (f"{now:%Y}", f"{now:%m}")
        assert (made["state"], made["is_open"], made["title"], made["problem"]) == (
            "analysing", True, "Contactor trips", "Dust in the panel")
        assert made["machine"] == {"id": machine["id"], "code": machine["code"], "name": machine["name"]}
        assert made["unit"]["id"] == unit["id"] and made["unit"]["site_id"] == unit["site_id"]
        assert made["lead"] == {"id": person["id"], "name": person["name"], "active": True, "may_lead": True}
        assert made["created_by_name"] == person["name"]
        assert [t["id"] for t in made["tickets"]] == [ticket["id"]]

    def test_the_next_start_takes_the_next_number(self, eng, restored_ticket):
        client, person = eng
        first = started(client, restored_ticket(), person)
        second = started(client, restored_ticket(), person)
        assert number(second["serial"]) == number(first["serial"]) + 1

    def test_a_refused_start_leaves_no_gap(self, eng, restored_ticket):
        client, person = eng
        first = started(client, restored_ticket(), person)
        assert start(client, restored_ticket("raised"), person).status_code == 409
        assert number(started(client, restored_ticket(), person)["serial"]) == number(first["serial"]) + 1

    def test_a_scrapped_machines_closed_ticket(self, admin, eng, restored_ticket, make_equipment, unit):
        """BR1-06: the analysis is about the plant and the class, not the one machine."""
        client, person = eng
        other = make_equipment(unit=unit)
        ticket = restored_ticket("closed", node=other)
        assert admin.put(f"{EQUIPMENT}/{other['id']}", json={"lifecycle": "scrapped"}).status_code == 200
        assert start(client, ticket, person).status_code == 201

    @pytest.mark.parametrize("state", ["raised", "acknowledged", "in_progress", "scheduled"])
    def test_an_open_ticket_is_409(self, admin, eng, make_ticket, restored_ticket, machine, state):
        client, person = eng
        if state == "scheduled":
            # A scheduled row needs its plan (chk_tickets_plan), so through the move
            ticket = make_ticket(machine)
            moved(admin, ticket, "schedule", planned_date=(now_ist().date() + timedelta(days=3)).isoformat(),
                  waiting_reason="parts")
        else:
            ticket = restored_ticket(state)
        assert refusal(start(client, ticket, person)) == (
            409, "ticket_id", "Start an improvement when the ticket is back in service or closed")

    def test_a_not_a_fault_ticket_is_409(self, admin, eng, make_ticket, machine, no_cause):
        client, person = eng
        ticket = make_ticket(machine)
        moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Ran fine")
        assert refusal(start(client, ticket, person)) == (
            409, "ticket_id", "This ticket was closed as not a fault. There is nothing to analyse.")

    def test_a_ticket_already_in_an_open_improvement(self, eng, restored_ticket):
        client, person = eng
        ticket = restored_ticket()
        first = started(client, ticket, person)
        tk = ticket_detail(client, ticket)["serial"]
        assert refusal(start(client, ticket, person)) == (409, "ticket_id", f"{tk} is already in {first['serial']}")

    def test_an_unknown_ticket_is_404(self, eng):
        client, person = eng
        assert start(client, {"id": 99999999}, person).status_code == 404

    def test_an_engineer_of_another_site_is_404(self, user_at_sites, other_site, eng, restored_ticket):
        _, lead = eng
        client, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert start(client, restored_ticket(), lead).status_code == 404

    def test_an_operator_here_who_is_engineer_elsewhere_is_403(self, user_at_sites, site, other_site, eng,
                                                               restored_ticket):
        _, lead = eng
        client, _ = user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])
        assert start(client, restored_ticket(), lead).status_code == 403

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "it_admin"])
    def test_without_the_key_is_403(self, role_client, eng, restored_ticket, role):
        _, lead = eng
        assert start(role_client(role), restored_ticket(), lead).status_code == 403

    def test_the_lead_must_lead_at_this_site(self, admin, user_at_sites, site, other_site, eng, restored_ticket):
        client, _ = eng
        ticket = restored_ticket()
        _, technician = user_at_sites([(site, "maint_technician", "all")])
        _, elsewhere = user_at_sites([(other_site, "maint_engineer", "all")])
        _, inactive = user_at_sites([(site, "maint_engineer", "all")])
        assert admin.put(f"{MASTERS}/people/{inactive['id']}", json={"active": False}).status_code == 200
        for lead in (technician, elsewhere, inactive):
            assert refusal(start(client, ticket, lead)) == (400, "lead_id", "Choose an engineer or manager of this site")
        assert refusal(client.post(IMPROVEMENTS, json={**body(ticket, technician), "lead_id": None}))[:2] == (
            400, "lead_id")

    def test_a_manager_may_lead(self, user_at_sites, site, eng, restored_ticket):
        client, _ = eng
        _, manager = user_at_sites([(site, "maint_manager", "all")])
        assert started(client, restored_ticket(), manager)["lead"]["may_lead"] is True

    @pytest.mark.parametrize("field, value, message", [
        ("title", "x" * 121, "Title: up to 120 characters"),
        ("title", " ", "Enter a title"),
        ("problem", "x" * 2001, "Problem: up to 2000 characters"),
        ("problem", 5, "Problem must be text"),
    ])
    def test_the_text_bounds(self, eng, restored_ticket, field, value, message):
        client, person = eng
        assert refusal(start(client, restored_ticket(), person, **{field: value})) == (400, field, message)

    def test_the_longest_texts_and_tamil_fit(self, eng, restored_ticket):
        client, person = eng
        made = started(client, restored_ticket(), person, title="தூசி" * 30, problem="x" * 2000)
        assert (made["title"], len(made["problem"])) == ("தூசி" * 30, 2000)

    def test_the_ticket_row_is_not_written(self, eng, restored_ticket, db_rows):
        client, person = eng
        ticket = restored_ticket("closed")
        before = db_rows("SELECT * FROM tickets WHERE id = %s", (ticket["id"],))
        started(client, ticket, person)
        assert db_rows("SELECT * FROM tickets WHERE id = %s", (ticket["id"],)) == before


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class TestDetail:

    def test_the_tickets_and_the_loss(self, admin, eng, make_ticket, machine, db_rows):
        """A breakdown down from T-180 to T-60 (120 minutes), an open breakdown since T-30
        (counted to now), and a defect (0)."""
        client, person = eng
        t = now_ist().replace(second=0, microsecond=0)
        mode = db_rows("SELECT id, code, label FROM failure_modes WHERE code = 'NOI'")[0]
        first = make_ticket(machine, occurred_at=local(t - timedelta(minutes=180)), failure_mode_id=mode["id"])
        moved(admin, first, "start", occurred_at=local(t - timedelta(minutes=150)))
        moved(admin, first, "restore", occurred_at=local(t - timedelta(minutes=60)), person_id=person["id"])
        made = started(client, first, person)
        down = make_ticket(machine, occurred_at=local(t - timedelta(minutes=30)))
        defect = make_ticket(machine, intensity="degraded", occurred_at=local(t - timedelta(minutes=20)))
        assert add(client, made, down).status_code == 201
        shown = add(client, made, defect).get_json()

        assert [x["id"] for x in shown["tickets"]] == [defect["id"], down["id"], first["id"]]   # newest first
        by_id = {x["id"]: x for x in shown["tickets"]}
        assert by_id[first["id"]]["downtime_minutes"] == 120
        assert by_id[first["id"]]["failure_mode"] == {"id": mode["id"], "code": mode["code"], "label": mode["label"]}
        assert by_id[first["id"]]["cause"] is None
        assert by_id[first["id"]]["state"] == "back_in_service"
        assert 30 <= by_id[down["id"]]["downtime_minutes"] <= 32
        assert by_id[defect["id"]]["downtime_minutes"] == 0
        assert (by_id[down["id"]]["is_breakdown"], by_id[defect["id"]]["is_breakdown"]) == (True, False)
        assert shown["loss"]["tickets"] == 3 and shown["loss"]["breakdowns"] == 2
        assert shown["loss"]["downtime_minutes"] == 120 + by_id[down["id"]]["downtime_minutes"]
        # Three tickets of the improvement's machine: any one may go, two of it remain
        assert all(x["removable"] for x in shown["tickets"])

    def test_who_reads_it(self, role_client, user_at_sites, user_with_units, make_unit, site, eng, restored_ticket,
                          unit):
        client, person = eng
        made = started(client, restored_ticket(), person)
        assert get(user_with_units("maint_operator", [unit]), made)["id"] == made["id"]
        other_unit = make_unit(site={"id": site["id"]})
        reader, _ = user_at_sites([(site, "maint_operator", [other_unit])])
        assert reader.get(f"{IMPROVEMENTS}/{made['id']}").status_code == 404
        assert role_client("maint_storekeeper").get(f"{IMPROVEMENTS}/{made['id']}").status_code == 403
        assert get(role_client("it_admin"), made)["id"] == made["id"]

    def test_permissions_carry_the_keys_at_the_site(self, user_at_sites, site, eng, restored_ticket):
        client, person = eng
        made = started(client, restored_ticket(), person)
        assert {"improvement:read", "improvement:edit"} <= set(made["permissions"])
        operator, _ = user_at_sites([(site, "maint_operator", "all")])
        keys = set(get(operator, made)["permissions"])
        assert "improvement:read" in keys and "improvement:edit" not in keys

    def test_may_lead_turns_false_when_the_lead_leaves_the_site(self, admin, user_at_sites, site, eng,
                                                                 restored_ticket):
        client, _ = eng
        _, lead = user_at_sites([(site, "maint_engineer", "all")])
        made = started(client, restored_ticket(), lead)
        assert admin.delete(f"{MASTERS}/people/{lead['id']}/sites/{site['id']}").status_code == 200
        assert get(client, made)["lead"] == {"id": lead["id"], "name": lead["name"], "active": True, "may_lead": False}

    def test_a_ticket_of_another_machine_shows_its_machine(self, eng, restored_ticket, make_equipment, unit):
        client, person = eng
        made = started(client, restored_ticket(), person)
        other = make_equipment(unit=unit)
        shown = add(client, made, restored_ticket("raised", node=other)).get_json()
        assert [x["machine"]["code"] for x in shown["tickets"]] == [other["code"], made["machine"]["code"]]
        # The machine's only ticket stays; the other machine's may go (§ 5.3 removable)
        assert [x["removable"] for x in shown["tickets"]] == [True, False]

    def test_an_unknown_or_non_numeric_id_is_404(self, eng):
        client, _ = eng
        assert client.get(f"{IMPROVEMENTS}/99999999").status_code == 404
        assert client.get(f"{IMPROVEMENTS}/abc").status_code == 404


# ---------------------------------------------------------------------------
# Add ticket
# ---------------------------------------------------------------------------

class TestAddTicket:

    @pytest.fixture
    def made(self, eng, restored_ticket):
        client, person = eng
        return started(client, restored_ticket(), person)

    def test_a_raised_ticket_of_the_site(self, eng, made, restored_ticket, db_rows):
        client, _ = eng
        ticket = restored_ticket("raised")
        before = db_rows("SELECT * FROM tickets WHERE id = %s", (ticket["id"],))
        res = add(client, made, ticket)
        assert res.status_code == 201
        assert ticket["id"] in [x["id"] for x in res.get_json()["tickets"]]
        assert db_rows("SELECT * FROM tickets WHERE id = %s", (ticket["id"],)) == before

    def test_a_visible_ticket_of_another_site_is_400(self, user_at_sites, site, other_site, make_unit, make_equipment,
                                                     restored_ticket, made):
        client, _ = user_at_sites([(site, "maint_engineer", "all"), (other_site, "maint_engineer", "all")])
        there = restored_ticket(node=make_equipment(unit=make_unit(site=other_site)))
        assert refusal(add(client, made, there)) == (400, "ticket_id", "Choose a ticket from this site")

    def test_an_invisible_ticket_reads_as_unknown(self, user_at_sites, site, unit, make_unit, make_equipment,
                                                  restored_ticket, made):
        client, _ = user_at_sites([(site, "maint_engineer", [unit])])
        hidden = restored_ticket(node=make_equipment(unit=make_unit(site={"id": site["id"]})))
        expected = (400, "ticket_id", "Choose a ticket from the list")
        assert refusal(add(client, made, hidden)) == expected
        assert refusal(add(client, made, {"id": 99999999})) == expected

    def test_already_here_is_409(self, eng, made):
        client, _ = eng
        assert refusal(add(client, made, made["tickets"][0])) == (
            409, "ticket_id", "This ticket is already in this improvement")

    def test_in_another_open_improvement_is_409(self, eng, made, restored_ticket):
        client, person = eng
        ticket = restored_ticket()
        other = started(client, ticket, person)
        serial = ticket_detail(client, ticket)["serial"]
        assert refusal(add(client, made, ticket)) == (409, "ticket_id", f"{serial} is already in {other['serial']}")

    def test_not_a_fault_is_409(self, admin, eng, made, make_ticket, machine, no_cause):
        client, _ = eng
        ticket = make_ticket(machine)
        moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Ran fine")
        assert refusal(add(client, made, ticket)) == (
            409, "ticket_id", "This ticket was closed as not a fault. There is nothing to analyse.")

    def test_an_engineer_of_another_site_is_404(self, user_at_sites, other_site, made, restored_ticket):
        client, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        assert add(client, made, restored_ticket()).status_code == 404

    def test_an_operator_here_who_is_engineer_elsewhere_is_403(self, user_at_sites, site, other_site, made,
                                                               restored_ticket):
        client, _ = user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])
        assert add(client, made, restored_ticket()).status_code == 403

    def test_a_race_meets_the_unique_key(self, monkeypatch, eng, made, restored_ticket):
        """§ 5.4: two writers may both pass the plain check; the second insert then fails on
        uq_improvement_tickets_open.  The plain check is blinded here to play the second one."""
        client, person = eng
        ticket = restored_ticket()
        started(client, ticket, person)
        monkeypatch.setattr(improvements, "improvement_links", lambda _cur, _ticket_id: [])
        assert refusal(add(client, made, ticket)) == (
            409, "ticket_id", "This ticket is already in an open improvement. Reload the page.")

    def test_a_bad_body_is_400(self, eng, made):
        client, _ = eng
        res = client.post(f"{IMPROVEMENTS}/{made['id']}/tickets", json={"ticket_id": "x"})
        assert refusal(res) == (400, "ticket_id", "Choose a ticket")


# ---------------------------------------------------------------------------
# Remove ticket
# ---------------------------------------------------------------------------

class TestRemoveTicket:

    def test_a_ticket_of_another_machine(self, eng, restored_ticket, make_equipment, unit, db_rows):
        client, person = eng
        made = started(client, restored_ticket(), person)
        other = restored_ticket("raised", node=make_equipment(unit=unit))
        add(client, made, other)
        before = db_rows("SELECT * FROM tickets WHERE id = %s", (other["id"],))
        res = remove(client, made, other)
        assert res.status_code == 200
        assert other["id"] not in [x["id"] for x in res.get_json()["tickets"]]
        assert db_rows("SELECT * FROM tickets WHERE id = %s", (other["id"],)) == before

    def test_the_machines_second_ticket(self, eng, restored_ticket):
        client, person = eng
        first = restored_ticket()
        made = started(client, first, person)
        add(client, made, restored_ticket("raised"))
        res = remove(client, made, first)
        assert res.status_code == 200 and len(res.get_json()["tickets"]) == 1

    def test_the_machines_last_ticket_stays(self, eng, restored_ticket, make_equipment, unit):
        client, person = eng
        first = restored_ticket()
        made = started(client, first, person)
        expected = (409, None, f"An improvement keeps a ticket of {made['machine']['code']}.")
        assert refusal(remove(client, made, first)) == expected
        add(client, made, restored_ticket("raised", node=make_equipment(unit=unit)))
        assert refusal(remove(client, made, first)) == expected

    def test_a_ticket_not_linked_is_404(self, eng, restored_ticket):
        client, person = eng
        made = started(client, restored_ticket(), person)
        assert remove(client, made, restored_ticket()).status_code == 404

    def test_the_removed_ticket_can_start_a_new_improvement(self, eng, restored_ticket):
        client, person = eng
        made = started(client, restored_ticket(), person)
        second = restored_ticket()
        add(client, made, second)
        assert remove(client, made, second).status_code == 200
        assert start(client, second, person).status_code == 201

    def test_another_site_is_404_and_a_key_missing_here_403(self, user_at_sites, site, other_site, eng,
                                                            restored_ticket):
        client, person = eng
        first = restored_ticket()
        made = started(client, first, person)
        stranger, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        operator, _ = user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])
        assert remove(stranger, made, first).status_code == 404
        assert remove(operator, made, first).status_code == 403


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

class TestEdit:

    @pytest.fixture
    def made(self, eng, restored_ticket):
        client, person = eng
        return started(client, restored_ticket(), person)

    def put(self, client, made, **fields):
        return client.put(f"{IMPROVEMENTS}/{made['id']}", json=fields)

    def test_each_field(self, user_at_sites, site, eng, made):
        client, person = eng
        _, other = user_at_sites([(site, "maint_manager", "all")])
        res = self.put(client, made, title=" New title ", problem="Loose lug", lead_id=other["id"])
        assert res.status_code == 200
        shown = res.get_json()
        assert (shown["title"], shown["problem"], shown["lead"]["id"]) == ("New title", "Loose lug", other["id"])
        assert shown["updated_by"] is not None and shown["updated_at"] is not None

    def test_no_change_writes_nothing(self, eng, made, db_rows):
        client, person = eng
        res = self.put(client, made, title=made["title"], problem=made["problem"], lead_id=person["id"])
        assert res.status_code == 200 and res.get_json()["updated_at"] is None
        assert self.put(client, made).status_code == 200
        assert db_rows("SELECT updated_at FROM improvements WHERE id = %s", (made["id"],)) == [{"updated_at": None}]

    def test_a_null_lead_is_400(self, eng, made):
        client, _ = eng
        assert refusal(self.put(client, made, lead_id=None)) == (400, "lead_id", "Choose a lead")

    def test_a_lead_no_longer_at_the_site(self, admin, user_at_sites, site, eng, restored_ticket):
        client, _ = eng
        _, lead = user_at_sites([(site, "maint_engineer", "all")])
        made = started(client, restored_ticket(), lead)
        assert admin.delete(f"{MASTERS}/people/{lead['id']}/sites/{site['id']}").status_code == 200
        assert self.put(client, made, lead_id=lead["id"], title="Kept").status_code == 200
        _, person = eng
        self.put(client, made, lead_id=person["id"])
        assert refusal(self.put(client, made, lead_id=lead["id"])) == (
            400, "lead_id", "Choose an engineer or manager of this site")

    def test_another_site_is_404_and_a_key_missing_here_403(self, user_at_sites, site, other_site, made):
        stranger, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        operator, _ = user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])
        assert self.put(stranger, made, title="x").status_code == 404
        assert self.put(operator, made, title="x").status_code == 403


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class TestList:

    def test_open_newest_first_with_the_loss(self, eng, restored_ticket, unit):
        client, person = eng
        first = started(client, restored_ticket(), person)
        second = started(client, restored_ticket(), person)
        res = client.get(IMPROVEMENTS, query_string={"unit_id": unit["id"]})
        assert res.status_code == 200
        listed = res.get_json()
        assert [x["id"] for x in listed["items"]] == [second["id"], first["id"]]
        assert listed["total"] == 2 and listed["page"] == 1 and listed["per_page"] == 50
        item = listed["items"][0]
        assert set(item) == {"id", "serial", "state", "title", "machine", "unit", "lead", "loss", "created_at"}
        assert item["unit"] == second["unit"] and item["unit"]["site_id"] == unit["site_id"]
        assert item["lead"] == {"id": person["id"], "name": person["name"]}
        assert item["loss"] == second["loss"]

    def test_closed_is_empty_and_another_state_is_400(self, eng, restored_ticket, unit):
        client, person = eng
        started(client, restored_ticket(), person)
        res = client.get(IMPROVEMENTS, query_string={"state": "closed", "unit_id": unit["id"]})
        assert res.get_json()["items"] == [] and res.get_json()["total"] == 0
        assert refusal(client.get(IMPROVEMENTS, query_string={"state": "x"}))[:2] == (400, "state")

    def test_the_unit_filter_and_an_operators_units(self, user_at_sites, site, eng, restored_ticket, make_unit,
                                                    make_equipment, unit):
        client, person = eng
        here = started(client, restored_ticket(), person)
        other_unit = make_unit(site={"id": site["id"]})
        there = started(client, restored_ticket(node=make_equipment(unit=other_unit)), person)
        assert [x["id"] for x in client.get(IMPROVEMENTS, query_string={"unit_id": other_unit["id"]})
                .get_json()["items"]] == [there["id"]]
        operator, _ = user_at_sites([(site, "maint_operator", [unit])])
        seen = [x["id"] for x in operator.get(IMPROVEMENTS, query_string={"per_page": 200}).get_json()["items"]]
        assert here["id"] in seen and there["id"] not in seen

    def test_paging(self, eng, restored_ticket, unit):
        client, person = eng
        made = [started(client, restored_ticket(), person) for _ in range(3)]
        res = client.get(IMPROVEMENTS, query_string={"unit_id": unit["id"], "per_page": 2, "page": 2}).get_json()
        assert res["total"] == 3 and [x["id"] for x in res["items"]] == [made[0]["id"]]

    def test_the_storekeeper_is_403(self, role_client):
        assert role_client("maint_storekeeper").get(IMPROVEMENTS).status_code == 403

    def test_the_database_down_is_503(self, role_client, db_down):
        assert role_client("it_admin").get(IMPROVEMENTS).status_code == 503


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------

class TestLeads:

    def test_the_active_engineers_and_managers_of_the_site_by_name(self, admin, user_at_sites, site, other_site,
                                                                   restored_ticket):
        client, _ = user_at_sites([(site, "maint_engineer", "all")])
        _, manager = user_at_sites([(site, "maint_manager", "all")])
        user_at_sites([(site, "maint_technician", "all")])
        user_at_sites([(other_site, "maint_engineer", "all")])
        _, inactive = user_at_sites([(site, "maint_engineer", "all")])
        assert admin.put(f"{MASTERS}/people/{inactive['id']}", json={"active": False}).status_code == 200
        ticket = restored_ticket()
        res = client.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": ticket["id"]})
        assert res.status_code == 200
        items = res.get_json()["items"]
        assert all(set(item) == {"id", "name"} for item in items)
        assert len(items) == 2 and manager["id"] in [i["id"] for i in items]
        assert [i["name"] for i in items] == sorted(i["name"] for i in items)
        made = started(client, ticket, manager)
        by_improvement = client.get(f"{IMPROVEMENTS}/leads", query_string={"improvement_id": made["id"]})
        assert by_improvement.get_json()["items"] == items

    def test_needs_an_anchor(self, eng):
        client, _ = eng
        assert refusal(client.get(f"{IMPROVEMENTS}/leads")) == (400, "ticket_id", "ticket_id or improvement_id is required")

    def test_an_unknown_or_invisible_anchor_is_404(self, user_at_sites, site, unit, make_unit, make_equipment,
                                                   restored_ticket, eng):
        client, _ = user_at_sites([(site, "maint_engineer", [unit])])
        hidden = restored_ticket(node=make_equipment(unit=make_unit(site={"id": site["id"]})))
        assert client.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": hidden["id"]}).status_code == 404
        assert client.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": 99999999}).status_code == 404
        assert client.get(f"{IMPROVEMENTS}/leads", query_string={"improvement_id": 99999999}).status_code == 404

    def test_another_site_is_404_and_a_key_missing_here_403(self, user_at_sites, site, other_site, restored_ticket):
        ticket = restored_ticket()
        stranger, _ = user_at_sites([(other_site, "maint_engineer", "all")])
        operator, _ = user_at_sites([(site, "maint_operator", "all"), (other_site, "maint_engineer", "all")])
        assert stranger.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": ticket["id"]}).status_code == 404
        assert operator.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": ticket["id"]}).status_code == 403

    def test_the_route_is_not_a_detail(self, eng, restored_ticket):
        client, _ = eng
        res = client.get(f"{IMPROVEMENTS}/leads", query_string={"ticket_id": restored_ticket()["id"]})
        assert res.status_code == 200 and "items" in res.get_json() and "serial" not in res.get_json()


# ---------------------------------------------------------------------------
# The ticket detail (S067 § 5.3)
# ---------------------------------------------------------------------------

class TestTicketDetail:

    def test_improvements_empty_then_the_link(self, eng, restored_ticket):
        client, person = eng
        ticket = restored_ticket()
        before = ticket_detail(client, ticket)
        assert (before["improvements"], before["can_start_improvement"]) == ([], True)
        made = started(client, ticket, person)
        after = ticket_detail(client, ticket)
        assert after["improvements"] == [{"id": made["id"], "serial": made["serial"], "state": "analysing"}]
        assert after["can_start_improvement"] is False

    def test_two_improvements_newest_first(self, eng, restored_ticket, db_rows):
        """A closed link (open_link NULL) is what R05.4 writes on close; written here by hand,
        since S067 has no close.  It does not hold the ticket back from a new start."""
        client, person = eng
        ticket = restored_ticket()
        first = started(client, ticket, person)
        db_rows("UPDATE improvement_tickets SET open_link = NULL WHERE improvement_id = %s", (first["id"],))
        assert ticket_detail(client, ticket)["can_start_improvement"] is True
        second = started(client, ticket, person)
        assert [x["id"] for x in ticket_detail(client, ticket)["improvements"]] == [second["id"], first["id"]]

    @pytest.mark.parametrize("state", ["raised", "in_progress"])
    def test_cannot_start_from_an_open_ticket(self, eng, restored_ticket, state):
        client, _ = eng
        assert ticket_detail(client, restored_ticket(state))["can_start_improvement"] is False

    def test_cannot_start_from_a_not_a_fault_ticket(self, admin, eng, make_ticket, machine, no_cause):
        client, _ = eng
        ticket = make_ticket(machine)
        moved(admin, ticket, "not-a-fault", cause_id=no_cause, remark="Ran fine")
        assert ticket_detail(client, ticket)["can_start_improvement"] is False

    @pytest.mark.parametrize("role", ["maint_operator", "it_admin"])
    def test_cannot_start_without_the_key(self, user_at_sites, role_client, site, restored_ticket, role):
        client = role_client(role) if role == "it_admin" else user_at_sites([(site, role, "all")])[0]
        shown = ticket_detail(client, restored_ticket())
        assert shown["can_start_improvement"] is False and shown["improvements"] == []

    def test_a_reader_without_the_read_key_sees_no_links(self, monkeypatch, user_at_sites, site, eng,
                                                         restored_ticket):
        """No role holds ticket:read without improvement:read today, so the key is taken from the
        operator for this test."""
        client, person = eng
        ticket = restored_ticket()
        started(client, ticket, person)
        operator, _ = user_at_sites([(site, "maint_operator", "all")])
        assert len(ticket_detail(operator, ticket)["improvements"]) == 1
        monkeypatch.setitem(config_rbac.PERMISSIONS, "improvement:read", ("it_admin",))
        assert ticket_detail(operator, ticket)["improvements"] == []

    def test_only_the_improvements_the_reader_can_open(self, user_at_sites, site, unit, eng, restored_ticket,
                                                         make_unit, make_equipment):
        """A1 (CR1-01): an improvement started on this unit's machine, joined by a ticket of a
        second unit's machine.  A reader of the second unit alone sees the ticket but not the
        improvement (its unit and machine are the first unit's), so the link is left out; a
        reader of both units opens it, so it is listed."""
        client, person = eng
        made = started(client, restored_ticket(), person)
        other_unit = make_unit(site={"id": site["id"]})
        there = restored_ticket(node=make_equipment(unit=other_unit))
        assert add(client, made, there).status_code == 201
        only_there, _ = user_at_sites([(site, "maint_operator", [other_unit])])
        assert only_there.get(f"{IMPROVEMENTS}/{made['id']}").status_code == 404
        assert ticket_detail(only_there, there)["improvements"] == []
        both, _ = user_at_sites([(site, "maint_operator", [unit, other_unit])])
        assert [x["id"] for x in ticket_detail(both, there)["improvements"]] == [made["id"]]
