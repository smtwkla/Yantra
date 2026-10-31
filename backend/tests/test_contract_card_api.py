"""The Under contract card's route (S082 § 5.1, § 5.2, § 5.6, § 8.2) — GET /api/contracts/for-equipment/<node_id>,
against the test DB.  Needs the dev MariaDB container (tooling/dev/dev-db-up.bat).  Each test makes its own site,
unit, vendor, contract and machine, so no other test's contract shows.  The readers are user_at_sites clients at
the test's site: an X-Test-Role engineer holds no unit, and load_node_for_user answers 404 for it (BS1-02).
Phone values are obviously fake.  S087: a contract has no site, so the card shows every contract on the node,
wherever the contract's other machines stand."""

from datetime import datetime, timedelta

import pytest

import config_rbac
from equipment import IST

CONTRACTS = "/api/contracts"
EQUIPMENT = "/api/equipment"
TODAY = datetime.now(IST).date()
CALLOUT = "+91 00000 00000"

# Never in a card item, for any reader (§ 5.2)
NEVER = ("price", "price_total", "priced_count", "cost_note", "machine_count", "can_edit", "can_read_cost")


def _day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def unit(make_unit, site):
    return make_unit(site=site)


@pytest.fixture
def machine(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def reader(user_at_sites, site):
    """reader(role) -> a client holding ``role`` at the test's site, with all its units."""
    return lambda role: user_at_sites([(site, role, "all")])[0]


@pytest.fixture
def engineer_here(reader):
    return reader("maint_engineer")


@pytest.fixture
def manager_here(reader):
    return reader("maint_manager")


@pytest.fixture
def add_contract(manager_here, make_vendor, site, uniq):
    """add_contract(**fields) -> a contract (201), by default an AMC in force with a call-out number."""
    vendor = make_vendor()

    def make(**overrides):
        body = {"vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "from_date": _day(-30), "to_date": _day(300),
                "callout_number": CALLOUT, **overrides}
        res = manager_here.post(CONTRACTS, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def cover(manager_here):
    """cover(contract, node, **fields) -> the node added to the contract by the manager (201)."""
    def add(contract, node, **fields):
        res = manager_here.post(f"{CONTRACTS}/{contract['id']}/equipment", json={"equipment_id": node["id"], **fields})
        assert res.status_code == 201, res.get_json()
    return add


def _card(client, node):
    res = client.get(f"{CONTRACTS}/for-equipment/{node['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()["items"]


def _ids(client, node):
    return [item["contract_id"] for item in _card(client, node)]


class TestItem:

    def test_the_technician_gets_no_number_and_the_engineer_does(self, reader, engineer_here, add_contract, cover,
                                                               machine):
        contract = add_contract(only_vendor_repairs=True, response_hours=24, covers_labour=True,
                                covers_breakdown_calls=True, breakdown_calls_per_year=4)
        cover(contract, machine)
        [item] = _card(reader("maint_technician"), machine)
        assert item == {
            "contract_id": contract["id"], "title": contract["title"], "contract_type": "amc",
            "vendor_name": contract["vendor_name"], "from_date": _day(-30), "to_date": _day(300),
            "status": {"kind": "in_force", "label": "In force", "days": None}, "response_hours": 24,
            "covers_labour": 1, "covers_parts": 0, "covers_consumables": 0, "covers_breakdown_calls": 1,
            "breakdown_calls_per_year": 4, "only_vendor_repairs": 1, "can_read_callout": False, "via": None,
        }
        [item] = _card(engineer_here, machine)
        assert (item["can_read_callout"], item["callout_number"]) == (True, CALLOUT)

    def test_no_price_total_or_cost_note_for_anyone(self, reader, engineer_here, manager_here, add_contract, cover,
                                                     machine):
        contract = add_contract(cost_note="Rs 1,00,000 a year")
        cover(contract, machine, price="9809")
        detail = manager_here.get(f"{CONTRACTS}/{contract['id']}").get_json()
        assert (detail["price_total"], detail["cost_note"]) == ("9809.00", "Rs 1,00,000 a year")
        for client in (reader("maint_technician"), engineer_here, manager_here):
            [item] = _card(client, machine)
            for key in NEVER:
                assert key not in item

    def test_an_ending_contract(self, engineer_here, add_contract, cover, machine):
        cover(add_contract(to_date=_day(10)), machine)
        [item] = _card(engineer_here, machine)
        assert item["status"] == {"kind": "ending", "label": "Ends in 10 days", "days": 10}


class TestWhichContracts:

    def test_the_machine_s_contract_shows_on_its_parts(self, engineer_here, add_contract, cover, machine,
                                                         make_equipment):
        part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        contract = add_contract()
        cover(contract, machine)
        via = {"id": machine["id"], "code": machine["code"], "name": machine["name"], "level": "equipment"}
        assert [(i["contract_id"], i["via"]) for i in _card(engineer_here, part)] == [(contract["id"], via)]
        assert [(i["contract_id"], i["via"]) for i in _card(engineer_here, component)] == [(contract["id"], via)]

    def test_a_part_s_contract_names_the_component_unit(self, engineer_here, add_contract, cover, machine,
                                                          make_equipment):
        part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        contract = add_contract(contract_type="warranty")
        cover(contract, part)
        [item] = _card(engineer_here, component)
        assert item["via"] == {"id": part["id"], "code": part["code"], "name": part["name"],
                               "level": "component_unit"}
        # A part's contract is not on its machine's card (B4)
        assert _card(engineer_here, machine) == []

    def test_the_same_contract_on_the_node_and_its_parent_is_one_item(self, engineer_here, add_contract, cover,
                                                                         machine, make_equipment):
        part = make_equipment(parent=machine)
        contract = add_contract()
        cover(contract, machine)
        cover(contract, part)
        assert [(i["contract_id"], i["via"]) for i in _card(engineer_here, part)] == [(contract["id"], None)]

    def test_the_dates_and_the_active_flag(self, engineer_here, manager_here, add_contract, cover, machine):
        ended_lately = add_contract(from_date=_day(-400), to_date=_day(-10))
        ended_long_ago = add_contract(from_date=_day(-400), to_date=_day(-100))
        upcoming = add_contract(from_date=_day(1), to_date=_day(300))
        inactive = add_contract()
        in_force = add_contract(to_date=_day(200))
        for contract in (ended_lately, ended_long_ago, upcoming, inactive, in_force):
            cover(contract, machine)
        assert manager_here.put(f"{CONTRACTS}/{inactive['id']}", json={"active": False}).status_code == 200
        items = _card(engineer_here, machine)
        assert [i["contract_id"] for i in items] == [in_force["id"], ended_lately["id"]]
        assert items[1]["status"]["kind"] == "ended"

    def test_a_removed_line_leaves_the_card(self, engineer_here, add_contract, cover, machine):
        contract = add_contract()
        cover(contract, machine)
        res = engineer_here.delete(f"{CONTRACTS}/{contract['id']}/equipment/{machine['id']}")
        assert res.status_code == 200, res.get_json()
        assert _card(engineer_here, machine) == []

    def test_a_moved_machine_keeps_its_contract_on_the_card(self, admin, user_at_sites, make_site, make_unit,
                                                            add_contract, cover, machine):
        """A machine of B moved to A keeps its line (S081 § 9 Q5); since S087 A's technician sees the contract on it:
        read_basic is global."""
        contract = add_contract()
        cover(contract, machine)
        site_a = make_site()
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": make_unit(site=site_a)["id"]}).status_code \
            == 200
        technician_a, _ = user_at_sites([(site_a, "maint_technician", "all")])
        assert _ids(technician_a, machine) == [contract["id"]]
        assert _ids(admin, machine) == [contract["id"]]

    def test_a_contract_with_machines_elsewhere_shows_on_this_machine(self, user_at_sites, make_site, make_unit,
                                                                      make_equipment, add_contract, cover, machine):
        """S087 § 5.4: one contract over machines of two sites; the technician of the second site, who holds no role
        at the first, sees it on their machine."""
        site_b = make_site()
        machine_b = make_equipment(unit=make_unit(site=site_b))
        contract = add_contract()
        cover(contract, machine)
        technician_b, _ = user_at_sites([(site_b, "maint_technician", "all")])
        # B's manager adds B's machine to the contract (inside their units)
        manager_b, _ = user_at_sites([(site_b, "maint_manager", "all")])
        res = manager_b.post(f"{CONTRACTS}/{contract['id']}/equipment", json={"equipment_id": machine_b["id"]})
        assert res.status_code == 201, res.get_json()
        [item] = _card(technician_b, machine_b)
        assert (item["contract_id"], item["via"]) == (contract["id"], None)


class TestRefusals:

    def test_a_node_outside_the_reader_s_units_is_404(self, user_at_sites, make_site, machine):
        stranger, _ = user_at_sites([(make_site(), "maint_engineer", "all")])
        assert stranger.get(f"{CONTRACTS}/for-equipment/{machine['id']}").status_code == 404
        assert stranger.get(f"{CONTRACTS}/for-equipment/999999999").status_code == 404

    def test_no_read_basic_anywhere_is_403(self, monkeypatch, reader, machine):
        monkeypatch.setitem(config_rbac.PERMISSIONS, "contract:read_basic", ("maint_engineer",))
        assert reader("maint_operator").get(f"{CONTRACTS}/for-equipment/{machine['id']}").status_code == 403

    def test_no_identity_is_401(self, client, machine):
        assert client.get(f"{CONTRACTS}/for-equipment/{machine['id']}").status_code == 401

    def test_the_database_down_is_503(self, engineer_here, machine, db_down):
        assert engineer_here.get(f"{CONTRACTS}/for-equipment/{machine['id']}").status_code == 503
