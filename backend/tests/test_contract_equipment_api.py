"""The machines a contract covers (S081 § 5, § 6, § 8.2) — the API, against the test DB.  Needs the dev MariaDB
container (tooling/dev/dev-db-up.bat).  Each test makes its own site, unit, vendor and contract, so nothing it reads
belongs to another test.  The price follows contract:read_senior (the manager; admin by the bypass); the machine's
history never holds it."""

from datetime import datetime, timedelta

import pytest

from contracts_core import PRICE_FORMAT
from equipment import IST

CONTRACTS = "/api/contracts"
EQUIPMENT = "/api/equipment"
TODAY = datetime.now(IST).date()

# The detail's keys a reader without contract:read_senior never gets (absent, not null)
COST_KEYS = ("price_total", "priced_count", "cost_note")


def _day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


def _dmy(offset):
    return (TODAY + timedelta(days=offset)).strftime("%d-%m-%Y")


@pytest.fixture
def manager(role_client):
    return role_client("maint_manager")


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def site_engineer(user_at_sites, site):
    """An engineer of ``site`` with all its units (the X-Test-Role engineer holds no unit), as ENGINEER."""
    client, _person = user_at_sites([(site, "maint_engineer", "all")])
    return client


@pytest.fixture
def engineer_login(site_engineer):
    return site_engineer._headers["X-Test-User"]


@pytest.fixture
def unit(make_unit, site):
    return make_unit(site=site)


@pytest.fixture
def machine(make_equipment, unit):
    return make_equipment(unit=unit)


@pytest.fixture
def add_contract(manager, make_vendor, site, uniq):
    """add_contract(**fields) -> a contract at ``site`` made by the manager (201): an AMC in force."""
    vendor = make_vendor()

    def make(**overrides):
        body = {"site_id": site["id"], "vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "from_date": _day(-30), "to_date": _day(300), **overrides}
        res = manager.post(CONTRACTS, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def contract(add_contract):
    return add_contract()


def _lines(contract_id):
    return f"{CONTRACTS}/{contract_id}/equipment"


def _add(client, contract, node, **fields):
    return client.post(_lines(contract["id"]), json={"equipment_id": node["id"], **fields})


def _added(client, contract, node, **fields):
    res = _add(client, contract, node, **fields)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _line(detail, node):
    return next(line for line in detail["machines"] if line["equipment_id"] == node["id"])


def _refusal(res):
    return res.status_code, res.get_json()


def _events(db_rows, node, kind):
    return list(db_rows("SELECT old_value, new_value, created_by FROM equipment_events WHERE equipment_id = %s"
                        " AND event = %s ORDER BY id", (node["id"], kind)))


def _event_text(contract, short="AMC"):
    return f"{contract['title']} ({short}, {_dmy(-30)} to {_dmy(300)})"


class TestAdd:

    def test_engineer_adds_a_machine_and_its_history_shows_it(self, site_engineer, engineer_login, contract, machine,
                                                              db_rows):
        detail = _added(site_engineer, contract, machine)
        assert detail["machine_count"] == 1
        line = _line(detail, machine)
        assert (line["code"], line["name"], line["level"], line["lifecycle"]) == (
            machine["code"], machine["name"], "equipment", "in_service")
        assert line["full_path"] == machine["full_path"]
        assert (line["at_contract_site"], line["can_open"], line["overlaps"]) == (True, True, [])
        assert line["created_by"] == engineer_login
        assert "price" not in line
        for key in COST_KEYS:
            assert key not in detail
        assert _events(db_rows, machine, "contract_added") == [
            {"old_value": None, "new_value": _event_text(contract), "created_by": engineer_login}]

    def test_any_level(self, site_engineer, contract, machine, make_equipment):
        part = make_equipment(parent=machine)
        component = make_equipment(parent=part, level="component")
        _added(site_engineer, contract, part)
        detail = _added(site_engineer, contract, component)
        assert [line["level"] for line in detail["machines"]].count("equipment") == 0
        assert {line["equipment_id"] for line in detail["machines"]} == {part["id"], component["id"]}

    def test_manager_adds_with_a_price(self, manager, contract, machine, db_rows):
        detail = _added(manager, contract, machine, price="9809")
        assert _line(detail, machine)["price"] == "9809.00"
        assert (detail["price_total"], detail["priced_count"], detail["machine_count"]) == ("9809.00", 1, 1)
        assert all("9809" not in (e["new_value"] or "") for e in _events(db_rows, machine, "contract_added"))

    @pytest.mark.parametrize("who", ["site_engineer", "admin"])
    def test_a_price_without_the_cost_key_is_dropped(self, request, who, contract, machine, db_rows):
        detail = _added(request.getfixturevalue(who), contract, machine, price="9809")
        assert "price" not in _line(detail, machine)
        assert db_rows("SELECT price FROM contract_equipment WHERE equipment_id = %s", (machine["id"],)) == [
            {"price": None}]

    def test_the_same_node_twice_is_409(self, site_engineer, contract, machine):
        _added(site_engineer, contract, machine)
        assert _refusal(_add(site_engineer, contract, machine)) == (
            409, {"error": "This machine is already on the contract.", "field": "equipment_id"})

    def test_a_node_of_another_site_names_the_contract_s_site(self, user_at_sites, make_site, make_unit, contract,
                                                              site, make_equipment):
        other_site = make_site()
        other = make_equipment(unit=make_unit(site=other_site))
        both, _ = user_at_sites([(site, "maint_engineer", "all"), (other_site, "maint_engineer", "all")])
        assert _refusal(_add(both, contract, other)) == (
            400, {"error": f"Choose a machine of {site['code']}, the contract's site.", "field": "equipment_id"})

    def test_a_scrapped_node_is_409(self, admin, site_engineer, contract, machine):
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"lifecycle": "scrapped"}).status_code == 200
        assert _refusal(_add(site_engineer, contract, machine)) == (
            409, {"error": "A scrapped machine cannot be added to a contract.", "field": "equipment_id"})

    def test_an_unknown_node_or_one_outside_the_user_s_units_is_400(self, site_engineer, user_with_units, contract,
                                                                    machine, make_unit, make_equipment, site):
        choose = (400, {"error": "Choose a machine.", "field": "equipment_id"})
        assert _refusal(site_engineer.post(_lines(contract["id"]), json={"equipment_id": 999999})) == choose
        elsewhere = make_equipment(unit=make_unit(site=site))
        limited = user_with_units("maint_engineer", [make_unit(site=site)])
        assert _refusal(_add(limited, contract, elsewhere)) == choose
        assert _refusal(_add(limited, contract, machine)) == choose

    def test_an_inactive_contract_takes_no_add(self, manager, site_engineer, contract, machine):
        assert manager.put(f"{CONTRACTS}/{contract['id']}", json={"active": False}).status_code == 200
        assert _refusal(_add(site_engineer, contract, machine)) == (
            409, {"error": "This contract is inactive. Set it active in Masters › Contracts, then add machines."})

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_roles_without_edit_get_403(self, role_client, role, contract, machine):
        assert _add(role_client(role), contract, machine).status_code == 403

    def test_an_engineer_of_another_site(self, user_at_sites, make_site, site, contract, machine):
        b = make_site()
        stranger, _ = user_at_sites([(b, "maint_engineer", "all")])
        assert _refusal(_add(stranger, contract, machine)) == (404, {"error": "Not found"})
        operator_here, _ = user_at_sites([(b, "maint_engineer", "all"), (site, "maint_operator", "all")])
        assert _refusal(_add(operator_here, contract, machine)) == (
            403, {"error": f"You can't do this at {site['code']}"})

    def test_a_missing_contract_is_404(self, site_engineer, machine):
        assert site_engineer.post(_lines(999999), json={"equipment_id": machine["id"]}).status_code == 404

    def test_a_bad_price_is_400(self, manager, contract, machine):
        assert _refusal(_add(manager, contract, machine, price="9,809")) == (
            400, {"error": PRICE_FORMAT, "field": "price"})
        assert _refusal(_add(manager, contract, machine, price=9809.5)) == (
            400, {"error": PRICE_FORMAT, "field": "price"})

    def test_no_machine_is_400(self, site_engineer, contract):
        assert _refusal(site_engineer.post(_lines(contract["id"]), json={})) == (
            400, {"error": "Choose a machine.", "field": "equipment_id"})


class TestPrice:

    def test_manager_sets_changes_and_clears_a_price(self, manager, site_engineer, contract, machine, db_rows):
        _added(site_engineer, contract, machine)
        path = f"{_lines(contract['id'])}/{machine['id']}"
        detail = manager.put(path, json={"price": "28028"}).get_json()
        assert (_line(detail, machine)["price"], detail["price_total"]) == ("28028.00", "28028.00")
        assert _line(detail, machine)["updated_by"] == "test_maint_manager"
        res = manager.put(path, json={"price": 9809})
        assert res.status_code == 200
        assert res.get_json()["price_total"] == "9809.00"
        detail = manager.put(path, json={"price": ""}).get_json()
        assert _line(detail, machine)["price"] is None
        assert (detail["price_total"], detail["priced_count"]) == (None, 0)
        assert db_rows("SELECT price FROM contract_equipment WHERE equipment_id = %s", (machine["id"],)) == [
            {"price": None}]
        assert _events(db_rows, machine, "contract_removed") == []   # a price change writes no history line

    @pytest.mark.parametrize("who", ["site_engineer", "admin"])
    def test_without_the_cost_key_is_403_naming_the_site(self, request, who, site_engineer, site, contract, machine):
        _added(site_engineer, contract, machine)
        res = request.getfixturevalue(who).put(f"{_lines(contract['id'])}/{machine['id']}", json={"price": "1"})
        assert _refusal(res) == (403, {"error": f"You can't do this at {site['code']}"})

    def test_a_node_not_on_the_contract_is_404(self, manager, contract, machine):
        res = manager.put(f"{_lines(contract['id'])}/{machine['id']}", json={"price": "1"})
        assert _refusal(res) == (404, {"error": "This machine is not on the contract."})

    def test_a_put_without_price_changes_nothing(self, manager, contract, machine, db_rows):
        _added(manager, contract, machine, price="100")
        res = manager.put(f"{_lines(contract['id'])}/{machine['id']}", json={"equipment_id": 5})
        assert res.status_code == 200
        assert _line(res.get_json(), machine)["price"] == "100.00"
        assert db_rows("SELECT updated_by FROM contract_equipment WHERE equipment_id = %s", (machine["id"],)) == [
            {"updated_by": None}]

    def test_price_change_on_an_inactive_contract(self, manager, contract, machine):
        _added(manager, contract, machine)
        assert manager.put(f"{CONTRACTS}/{contract['id']}", json={"active": False}).status_code == 200
        res = manager.put(f"{_lines(contract['id'])}/{machine['id']}", json={"price": "500"})
        assert res.status_code == 200
        assert res.get_json()["price_total"] == "500.00"


class TestRemove:

    def test_engineer_removes_a_priced_line(self, manager, site_engineer, engineer_login, contract, machine, db_rows):
        _added(manager, contract, machine, price="9809")
        res = site_engineer.delete(f"{_lines(contract['id'])}/{machine['id']}")
        assert res.status_code == 200
        assert (res.get_json()["machines"], res.get_json()["machine_count"]) == ([], 0)
        assert not db_rows("SELECT id FROM contract_equipment WHERE contract_id = %s", (contract["id"],))
        assert _events(db_rows, machine, "contract_removed") == [
            {"old_value": _event_text(contract), "new_value": None, "created_by": engineer_login}]

    def test_a_node_not_on_the_contract_is_404(self, site_engineer, contract, machine):
        assert _refusal(site_engineer.delete(f"{_lines(contract['id'])}/{machine['id']}")) == (
            404, {"error": "This machine is not on the contract."})

    def test_the_operator_gets_403(self, role_client, site_engineer, contract, machine):
        _added(site_engineer, contract, machine)
        assert role_client("maint_operator").delete(f"{_lines(contract['id'])}/{machine['id']}").status_code == 403

    def test_removal_on_an_inactive_contract(self, manager, site_engineer, contract, machine, db_rows):
        _added(site_engineer, contract, machine)
        assert manager.put(f"{CONTRACTS}/{contract['id']}", json={"active": False}).status_code == 200
        assert site_engineer.delete(f"{_lines(contract['id'])}/{machine['id']}").status_code == 200
        assert len(_events(db_rows, machine, "contract_removed")) == 1


class TestDetail:

    def test_machines_by_code_and_the_price_only_for_the_manager(self, manager, site_engineer, contract, unit,
                                                                 make_equipment):
        first, second = make_equipment(unit=unit), make_equipment(unit=unit)
        _added(manager, contract, second, price="28028")
        _added(manager, contract, first, price="9809")
        path = f"{CONTRACTS}/{contract['id']}"
        detail = manager.get(path).get_json()
        assert [line["code"] for line in detail["machines"]] == sorted([first["code"], second["code"]])
        assert (detail["price_total"], detail["priced_count"], detail["machine_count"]) == ("37837.00", 2, 2)
        seen = site_engineer.get(path).get_json()
        assert seen["machine_count"] == 2
        assert all("price" not in line for line in seen["machines"])
        for key in COST_KEYS:
            assert key not in seen

    def test_can_open_follows_the_reader_s_units(self, site_engineer, user_with_units, contract, site, machine,
                                                 make_unit):
        _added(site_engineer, contract, machine)
        limited = user_with_units("maint_engineer", [make_unit(site=site)])
        line = _line(limited.get(f"{CONTRACTS}/{contract['id']}").get_json(), machine)
        assert line["can_open"] is False   # listed all the same (B7)

    def test_a_moved_machine_is_marked(self, admin, site_engineer, contract, machine, make_site, make_unit):
        _added(site_engineer, contract, machine)
        other = make_site()
        assert admin.put(f"{EQUIPMENT}/{machine['id']}",
                         json={"unit_id": make_unit(site=other)["id"]}).status_code == 200
        line = _line(site_engineer.get(f"{CONTRACTS}/{contract['id']}").get_json(), machine)
        assert (line["at_contract_site"], line["site_code"]) == (False, other["code"])

    def test_overlaps(self, site_engineer, add_contract, unit, machine, make_equipment):
        part = make_equipment(parent=machine)
        main = add_contract()
        _added(site_engineer, main, machine)
        second = add_contract(from_date=_day(100), to_date=_day(500))
        _added(site_engineer, second, machine)
        on_part = add_contract()
        _added(site_engineer, on_part, part)
        warranty = add_contract(contract_type="warranty")
        _added(site_engineer, warranty, machine)
        ended = add_contract(from_date=_day(-400), to_date=_day(-31))
        _added(site_engineer, ended, machine)
        inactive = add_contract()
        _added(site_engineer, inactive, machine)
        assert site_engineer.put(f"{CONTRACTS}/{inactive['id']}", json={"active": False}).status_code == 200

        overlaps = _line(site_engineer.get(f"{CONTRACTS}/{main['id']}").get_json(), machine)["overlaps"]
        assert [(o["contract_id"], o["on_code"]) for o in overlaps] == [(on_part["id"], part["code"]),
                                                                        (second["id"], None)]
        assert overlaps[1] == {"contract_id": second["id"], "title": second["title"], "contract_type": "amc",
                               "from_date": _day(100), "to_date": _day(500), "on_code": None}
        # Both contracts show it; the part's contract sees the machine above it
        back = _line(site_engineer.get(f"{CONTRACTS}/{second['id']}").get_json(), machine)["overlaps"]
        assert (main["id"], None) in [(o["contract_id"], o["on_code"]) for o in back]
        up = _line(site_engineer.get(f"{CONTRACTS}/{on_part['id']}").get_json(), part)["overlaps"]
        assert (main["id"], machine["code"]) in [(o["contract_id"], o["on_code"]) for o in up]
        # A warranty, an ended contract and an inactive one show none; an inactive contract shows none itself
        assert _line(site_engineer.get(f"{CONTRACTS}/{warranty['id']}").get_json(), machine)["overlaps"] == []
        assert _line(site_engineer.get(f"{CONTRACTS}/{ended['id']}").get_json(), machine)["overlaps"] == []
        assert _line(site_engineer.get(f"{CONTRACTS}/{inactive['id']}").get_json(), machine)["overlaps"] == []

    def test_overlaps_at_a_site_the_reader_does_not_hold_stay_hidden(self, admin, site_engineer, add_contract,
                                                                     machine, make_site, make_unit, uniq):
        main = add_contract()
        _added(site_engineer, main, machine)
        other = make_site()
        # The machine stands at the other site while its line on that site's contract is added, then returns
        assert admin.put(f"{EQUIPMENT}/{machine['id']}",
                         json={"unit_id": make_unit(site=other)["id"]}).status_code == 200
        elsewhere = add_contract(site_id=other["id"])
        _added(admin, elsewhere, machine)
        assert admin.put(f"{EQUIPMENT}/{machine['id']}", json={"unit_id": machine["unit_id"]}).status_code == 200
        assert _line(admin.get(f"{CONTRACTS}/{main['id']}").get_json(), machine)["overlaps"][0][
            "contract_id"] == elsewhere["id"]   # the admin holds both sites
        seen = _line(site_engineer.get(f"{CONTRACTS}/{main['id']}").get_json(), machine)["overlaps"]
        assert seen == []

    def test_a_period_that_only_touches_on_one_day_overlaps(self, site_engineer, add_contract, machine):
        main = add_contract(from_date=_day(0), to_date=_day(300))
        _added(site_engineer, main, machine)
        touching = add_contract(from_date=_day(-200), to_date=_day(0))   # ends on the day this one starts
        _added(site_engineer, touching, machine)
        before = add_contract(from_date=_day(-200), to_date=_day(-1))    # ends the day before
        _added(site_engineer, before, machine)
        overlaps = _line(site_engineer.get(f"{CONTRACTS}/{main['id']}").get_json(), machine)["overlaps"]
        assert [o["contract_id"] for o in overlaps] == [touching["id"]]

    def test_the_contract_put_answers_with_the_machines(self, site_engineer, contract, machine):
        _added(site_engineer, contract, machine)
        res = site_engineer.put(f"{CONTRACTS}/{contract['id']}", json={"notes": "Two compressors"})
        assert res.status_code == 200
        assert [line["equipment_id"] for line in res.get_json()["machines"]] == [machine["id"]]


class TestList:

    def test_price_total_only_on_the_manager_s_rows(self, manager, site_engineer, contract, machine, site):
        _added(manager, contract, machine, price="9809")
        query = f"{CONTRACTS}?site_id={site['id']}"
        mine = manager.get(query).get_json()["items"]
        assert [(c["id"], c["price_total"], c["machine_count"]) for c in mine] == [(contract["id"], "9809.00", 1)]
        theirs = site_engineer.get(query).get_json()["items"]
        assert [c["id"] for c in theirs] == [contract["id"]]
        assert "price_total" not in theirs[0] and "priced_count" not in theirs[0]


class TestDatabaseDown:

    def test_the_line_and_detail_routes_answer_503(self, site_engineer, contract, machine, db_down):
        assert _add(site_engineer, contract, machine).status_code == 503
        assert site_engineer.get(f"{CONTRACTS}/{contract['id']}").status_code == 503
