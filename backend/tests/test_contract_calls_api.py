"""The contract's breakdown calls (S086 § 5.1-§ 5.5, § 6, § 8.2) — GET /api/contracts/<id>/calls, against the
test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Each test makes its own site, units, vendor,
contract and machines, so no other test's ticket is a call of its contract.  The vendor's people are Team records
made by IT admin and linked to the vendor (S079); their tickets are raised by IT admin, who may back-date them."""

from datetime import datetime, timedelta

import pytest

from equipment import IST
from tests.conftest import EQUIPMENT, MASTERS, TICKETS
from tests.ticket_helpers import local

CONTRACTS = "/api/contracts"
TODAY = datetime.now(IST).date()
NOW = datetime.now(IST).replace(tzinfo=None)

# The answer's keys (§ 6): no price, cost note or call-out number
ANSWER_KEYS = {"calls", "total", "complete", "used", "warning", "vendor_name", "site_code"}
CALL_KEYS = {"id", "serial", "state", "intensity", "is_breakdown", "overdue", "not_a_fault", "occurred_at",
             "back_in_service_at", "machine", "component", "downtime_minutes", "vendor_waiting_minutes",
             "vendor_people"}


def _day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def unit(make_unit, site):
    return make_unit(site=site)


@pytest.fixture
def unit2(make_unit, site):
    return make_unit(site=site)


@pytest.fixture
def machine(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def manager_here(user_at_sites, site):
    return user_at_sites([(site, "maint_manager", "all")])[0]


@pytest.fixture
def vendor(make_vendor):
    return make_vendor()


@pytest.fixture
def add_contract(manager_here, site, vendor, uniq):
    """add_contract(**fields) -> an AMC at ``site`` with ``vendor`` (201), in force from 30 days ago."""
    def make(**overrides):
        body = {"site_id": site["id"], "vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "from_date": _day(-30), "to_date": _day(300), **overrides}
        res = manager_here.post(CONTRACTS, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def cover(manager_here):
    def add(contract, node):
        res = manager_here.post(f"{CONTRACTS}/{contract['id']}/equipment", json={"equipment_id": node["id"]})
        assert res.status_code == 201, res.get_json()
    return add


@pytest.fixture
def vendor_person(make_person, give_site_role, site, vendor):
    """vendor_person(role="maint_technician", of=vendor, name=...) -> a contractor's Team record linked to the
    vendor, with ``role`` at the site (all units); role None gives no site row."""
    def make(role="maint_technician", of=None, name="Ravi of the vendor"):
        person = make_person(name=name, employment="contractor", vendor_id=(of or vendor)["id"])
        if role:
            give_site_role(person, site, role)
        return person
    return make


@pytest.fixture
def call(admin, make_ticket):
    """call(node, person, minutes_ago=60, **raise_fields) -> a ticket on ``node`` with ``person`` assigned."""
    def make(node, person, minutes_ago=60, **fields):
        ticket = make_ticket(node, occurred_at=local(NOW - timedelta(minutes=minutes_ago)), **fields)
        assign(admin, ticket, person)
        return ticket
    return make


def assign(client, ticket, person):
    res = client.post(f"{TICKETS}/{ticket['id']}/assignees", json={"person_id": person["id"]})
    assert res.status_code == 200, res.get_json()


def log_labour(client, ticket, person):
    res = client.post(f"{TICKETS}/{ticket['id']}/labour",
                      json={"person_id": person["id"], "work_date": TODAY.isoformat(), "minutes": 60})
    assert res.status_code == 201, res.get_json()


def calls_of(client, contract):
    res = client.get(f"{CONTRACTS}/{contract['id']}/calls")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def call_ids(client, contract):
    return [c["id"] for c in calls_of(client, contract)["calls"]]


class TestWhichTickets:

    def test_an_assignee_of_the_vendor_makes_a_call(self, admin, manager_here, add_contract, cover, machine,
                                                    vendor_person, call, vendor):
        contract = add_contract()
        cover(contract, machine)
        person = vendor_person()
        ticket = call(machine, person, minutes_ago=90)
        answer = calls_of(manager_here, contract)
        [row] = answer["calls"]
        assert row["id"] == ticket["id"] and row["serial"] == ticket["serial"]
        assert (row["state"], row["intensity"], row["is_breakdown"], row["overdue"], row["not_a_fault"]) == (
            "raised", "critical", True, False, False)
        assert row["machine"] == {"id": machine["id"], "code": machine["code"], "name": machine["name"]}
        assert row["component"] is None
        assert row["back_in_service_at"] is None
        assert 89 <= row["downtime_minutes"] <= 92   # an open breakdown runs to now
        assert row["vendor_waiting_minutes"] is None
        assert row["vendor_people"] == [{"id": person["id"], "name": person["name"]}]
        assert answer["total"]["count"] == 1
        assert (answer["vendor_name"], answer["complete"]) == (vendor["name"], True)

    def test_the_wait_on_the_vendor_and_back_in_service(self, admin, manager_here, add_contract, cover, machine,
                                                        vendor_person, call):
        """The figures are the ticket page's (§ 5.2): on hold for the vendor 120 min, then 20 min of work."""
        contract = add_contract()
        cover(contract, machine)
        person = vendor_person()
        ticket = call(machine, person, minutes_ago=200)
        url = f"{TICKETS}/{ticket['id']}/moves"
        for move, minutes_ago, body in (
                ("schedule", 150, {"planned_date": _day(1), "waiting_reason": "vendor"}),
                ("start", 30, {}), ("restore", 10, {"person_id": person["id"]})):
            res = admin.post(f"{url}/{move}", json={"occurred_at": local(NOW - timedelta(minutes=minutes_ago)), **body})
            assert res.status_code == 200, res.get_json()
        [row] = calls_of(manager_here, contract)["calls"]
        assert (row["downtime_minutes"], row["vendor_waiting_minutes"]) == (190, 120)
        assert row["back_in_service_at"] == (NOW - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:00+05:30")
        assert row["state"] == "back_in_service"

    def test_a_labour_row_alone_makes_a_call(self, admin, manager_here, add_contract, cover, machine, vendor_person,
                                             make_ticket):
        contract = add_contract()
        cover(contract, machine)
        operator = vendor_person("maint_operator")
        ticket = make_ticket(machine)
        log_labour(admin, ticket, operator)
        [row] = calls_of(manager_here, contract)["calls"]
        assert row["id"] == ticket["id"] and row["vendor_people"] == [{"id": operator["id"], "name": operator["name"]}]

    def test_an_in_house_ticket_is_not_a_call(self, admin, manager_here, add_contract, cover, machine, make_person,
                                              give_site_role, site, make_ticket):
        contract = add_contract()
        cover(contract, machine)
        own = make_person(name="In-house technician")
        give_site_role(own, site, "maint_technician")
        assign(admin, make_ticket(machine), own)
        assert call_ids(manager_here, contract) == []

    def test_another_vendors_person_is_not_a_call(self, manager_here, add_contract, cover, machine, vendor_person,
                                                  make_vendor, call):
        contract = add_contract()
        cover(contract, machine)
        call(machine, vendor_person(of=make_vendor()))
        assert call_ids(manager_here, contract) == []

    def test_one_row_for_assignee_and_labour_and_two_people(self, admin, manager_here, add_contract, cover, machine,
                                                             vendor_person, call):
        contract = add_contract()
        cover(contract, machine)
        first, second = vendor_person(name="Aa vendor one"), vendor_person(name="Ab vendor two")
        ticket = call(machine, first)
        log_labour(admin, ticket, first)
        log_labour(admin, ticket, second)
        [row] = calls_of(manager_here, contract)["calls"]
        assert row["vendor_people"] == [{"id": first["id"], "name": first["name"]},
                                        {"id": second["id"], "name": second["name"]}]

    def test_tickets_on_parts_of_a_covered_machine_count(self, manager_here, add_contract, cover, machine,
                                                         make_equipment, vendor_person, call):
        contract = add_contract()
        cover(contract, machine)
        part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        person = vendor_person()
        on_part, on_component = call(part, person, 30), call(component, person, 20)
        answer = calls_of(manager_here, contract)
        assert [c["id"] for c in answer["calls"]] == [on_component["id"], on_part["id"]]
        assert answer["calls"][0]["component"] == {"id": component["id"], "code": component["code"],
                                                   "name": component["name"]}
        assert answer["calls"][0]["machine"]["id"] == machine["id"]

    def test_a_line_on_a_component_unit_counts_its_components_not_the_machine(
            self, manager_here, add_contract, cover, machine, make_equipment, vendor_person, call):
        contract = add_contract()
        part = make_equipment(parent=machine)
        other_part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        cover(contract, part)
        person = vendor_person()
        on_part, on_component = call(part, person, 40), call(component, person, 30)
        call(machine, person, 20)
        call(other_part, person, 10)
        assert call_ids(manager_here, contract) == [on_component["id"], on_part["id"]]

    def test_the_period_edges(self, manager_here, add_contract, cover, machine, vendor_person, call):
        """BR1-07: the contract ends yesterday, as a raise refuses a future time."""
        from_day, to_day = TODAY - timedelta(days=20), TODAY - timedelta(days=1)
        contract = add_contract(from_date=from_day.isoformat(), to_date=to_day.isoformat())
        cover(contract, machine)
        person = vendor_person()

        def at(day, hour, minute):
            moment = datetime(day.year, day.month, day.day, hour, minute)
            return call(machine, person, minutes_ago=(NOW - moment).total_seconds() / 60)

        first, last = at(from_day, 0, 0), at(to_day, 23, 59)
        at(from_day - timedelta(days=1), 23, 59)
        at(TODAY, 0, 0)
        assert call_ids(manager_here, contract) == [last["id"], first["id"]]

    def test_newest_first(self, manager_here, add_contract, cover, machine, vendor_person, call):
        contract = add_contract()
        cover(contract, machine)
        person = vendor_person()
        old, new = call(machine, person, 300), call(machine, person, 10)
        assert call_ids(manager_here, contract) == [new["id"], old["id"]]


class TestMovedParts:
    """BR1-03: a covered part's tickets count wherever the part stood when raised; the tree is read as it is now."""

    def move(self, admin, node, parent):
        res = admin.put(f"{EQUIPMENT}/{node['id']}", json={"parent_id": parent["id"]})
        assert res.status_code == 200, res.get_json()

    def test_a_covered_part_moved_after_its_ticket_still_counts(self, admin, manager_here, add_contract, cover,
                                                                machine, make_equipment, unit, vendor_person,
                                                                call):
        contract = add_contract()
        part = make_equipment(parent=machine)
        cover(contract, part)
        person = vendor_person()
        before = call(part, person, 60)
        self.move(admin, part, make_equipment(unit=unit))
        after = call(part, person, 10)
        assert call_ids(manager_here, contract) == [after["id"], before["id"]]

    def test_a_covered_machine_keeps_the_ticket_of_a_part_that_left(self, admin, manager_here, add_contract, cover,
                                                                    machine, make_equipment, unit, vendor_person,
                                                                    call):
        contract = add_contract()
        cover(contract, machine)
        part = make_equipment(parent=machine)
        ticket = call(part, vendor_person(), 60)
        self.move(admin, part, make_equipment(unit=unit))
        assert call_ids(manager_here, contract) == [ticket["id"]]

    def test_a_component_that_left_a_covered_component_unit_drops_out(self, admin, manager_here, add_contract, cover,
                                                                      machine, make_equipment, vendor_person, call):
        """The accepted residual (§ 5.1): a component's tickets follow its current parent."""
        contract = add_contract()
        part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        cover(contract, part)
        ticket = call(component, vendor_person(), 60)
        assert call_ids(manager_here, contract) == [ticket["id"]]
        self.move(admin, component, make_equipment(parent=machine))
        assert call_ids(manager_here, contract) == []


class TestTheVendorLink:

    def test_the_current_link_counts(self, admin, manager_here, add_contract, cover, machine, vendor_person,
                                     make_vendor, call, manager_of):
        contract = add_contract()
        cover(contract, machine)
        other_vendor = make_vendor()
        other = manager_of(other_vendor, machine)
        person = vendor_person()
        ticket = call(machine, person)
        assert call_ids(manager_here, contract) == [ticket["id"]]
        res = admin.put(f"{MASTERS}/people/{person['id']}", json={"vendor_id": other_vendor["id"]})
        assert res.status_code == 200, res.get_json()
        assert call_ids(manager_here, contract) == []
        assert call_ids(manager_here, other) == [ticket["id"]]

    def test_an_inactive_linked_person_still_counts(self, admin, manager_here, add_contract, cover, machine,
                                                    vendor_person, make_ticket):
        contract = add_contract()
        cover(contract, machine)
        person = vendor_person("maint_operator")
        ticket = make_ticket(machine)
        log_labour(admin, ticket, person)
        assert admin.put(f"{MASTERS}/people/{person['id']}", json={"active": False}).status_code == 200
        assert call_ids(manager_here, contract) == [ticket["id"]]

    def test_an_unassigned_vendor_person_no_longer_counts(self, admin, manager_here, add_contract, cover, machine,
                                                          vendor_person, call):
        contract = add_contract()
        cover(contract, machine)
        person = vendor_person()
        ticket = call(machine, person)
        assert admin.delete(f"{TICKETS}/{ticket['id']}/assignees/{person['id']}").status_code == 200
        assert call_ids(manager_here, contract) == []


@pytest.fixture
def manager_of(add_contract, cover):
    """manager_of(vendor, node) -> a second contract of ``vendor`` at the site covering ``node``."""
    def make(other_vendor, node):
        contract = add_contract(vendor_id=other_vendor["id"])
        cover(contract, node)
        return contract
    return make


class TestAccess:

    def test_rows_follow_ticket_access(self, user_at_sites, manager_here, add_contract, cover, machine,
                                       make_equipment, site, unit, unit2, vendor_person, call):
        contract = add_contract(covers_breakdown_calls=True, breakdown_calls_per_year=4)
        other_machine = make_equipment(unit=unit2)
        cover(contract, machine)
        cover(contract, other_machine)
        person = vendor_person()
        here, there = call(machine, person, 30), call(other_machine, person, 20)
        technician = user_at_sites([(site, "maint_technician", [unit])])[0]
        answer = calls_of(technician, contract)
        assert [c["id"] for c in answer["calls"]] == [here["id"]]
        assert (answer["complete"], answer["used"], answer["total"]["count"]) == (False, None, 1)
        answer = calls_of(manager_here, contract)
        assert [c["id"] for c in answer["calls"]] == [there["id"], here["id"]]
        assert answer["complete"] is True and answer["used"]["count"] == 2

    def test_used_when_the_number_is_agreed(self, manager_here, add_contract, cover, machine, vendor_person, call):
        agreed = add_contract(covers_breakdown_calls=True, breakdown_calls_per_year=4)
        plain = add_contract()
        cover(agreed, machine)
        cover(plain, machine)
        call(machine, vendor_person())
        assert calls_of(manager_here, agreed)["used"] == {"count": 1, "agreed": 4, "over": False,
                                                          "per_year_only": False}
        assert calls_of(manager_here, plain)["used"] is None

    def test_the_storekeeper_gets_403(self, user_at_sites, add_contract, site):
        contract = add_contract()
        storekeeper = user_at_sites([(site, "maint_storekeeper", "all")])[0]
        assert storekeeper.get(f"{CONTRACTS}/{contract['id']}").status_code == 200
        assert storekeeper.get(f"{CONTRACTS}/{contract['id']}/calls").status_code == 403

    def test_a_contract_of_another_site_is_404(self, user_at_sites, make_site, add_contract):
        contract = add_contract()
        elsewhere = user_at_sites([(make_site(), "maint_manager", "all")])[0]
        assert elsewhere.get(f"{CONTRACTS}/{contract['id']}/calls").status_code == 404

    def test_unknown_is_404(self, manager_here):
        assert manager_here.get(f"{CONTRACTS}/999999999/calls").status_code == 404

    def test_no_price_or_callout_in_the_answer(self, manager_here, add_contract, cover, machine, vendor_person,
                                               call):
        contract = add_contract(callout_number="+91 00000 00000", cost_note="Rs 1,00,000 a year")
        cover(contract, machine)
        call(machine, vendor_person())
        answer = calls_of(manager_here, contract)
        assert set(answer) == ANSWER_KEYS
        assert set(answer["calls"][0]) == CALL_KEYS
        assert set(answer["total"]) == {"count", "downtime_minutes", "vendor_waiting_minutes"}

    def test_database_down_is_503(self, manager_here, add_contract, db_down):
        assert manager_here.get(f"{CONTRACTS}/1/calls").status_code == 503


class TestWarnings:

    def test_warnings(self, admin, manager_here, add_contract, vendor_person, make_vendor, give_site_role, site):
        contract = add_contract()
        assert calls_of(manager_here, contract)["warning"] == "no_linked"
        person = vendor_person("maint_operator")
        assert calls_of(manager_here, contract)["warning"] == "no_assignable"
        give_site_role(person, site, "maint_technician")
        assert calls_of(manager_here, contract)["warning"] is None
        assert admin.put(f"{MASTERS}/people/{person['id']}", json={"active": False}).status_code == 200
        assert calls_of(manager_here, contract)["warning"] == "no_linked"

    def test_no_warning_on_an_ended_or_inactive_contract(self, manager_here, add_contract):
        ended = add_contract(from_date=_day(-400), to_date=_day(-40))
        assert calls_of(manager_here, ended)["warning"] is None
        inactive = add_contract()
        res = manager_here.put(f"{CONTRACTS}/{inactive['id']}", json={"active": False})
        assert res.status_code == 200, res.get_json()
        assert calls_of(manager_here, inactive)["warning"] is None

    def test_an_inactive_contract_still_lists_its_calls(self, manager_here, add_contract, cover, machine,
                                                        vendor_person, call):
        contract = add_contract()
        cover(contract, machine)
        ticket = call(machine, vendor_person())
        res = manager_here.put(f"{CONTRACTS}/{contract['id']}", json={"active": False})
        assert res.status_code == 200, res.get_json()
        assert call_ids(manager_here, contract) == [ticket["id"]]

    def test_no_machines_no_calls(self, manager_here, add_contract):
        answer = calls_of(manager_here, add_contract())
        assert answer["calls"] == []
        assert answer["total"] == {"count": 0, "downtime_minutes": 0, "vendor_waiting_minutes": 0}
