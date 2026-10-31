"""Vendor contracts (S080 § 5, § 6, § 8.2; S087 § 8.2, § 8.3) — the API, against the test DB.  Needs the dev MariaDB
container (tooling/dev/dev-db-up.bat).  Each test makes its own sites, machines and vendors; a contract has no site
(S087), so ``add`` puts each contract on the test's machine, and a list filtered by the test's site (the contracts
with a machine there) holds only its own contracts.  The four contract keys are global (S087 § 5.1).  The call-out
number is obviously fake, never a real number (D10)."""

from datetime import datetime, timedelta

import pytest

import contracts
from auth_utils import FORBIDDEN_TEXT
from config_rbac import LOGIN_ROLE
from contracts_core import CALLS_WITHOUT_TICK, FROM_AFTER_TO, TO_BEFORE_FROM, VENDOR_MISSING
from equipment import IST

CONTRACTS = "/api/contracts"
VENDORS = "/api/masters/vendors"
SITES = "/api/masters/sites"
CALLOUT = "+91 00000 00000"
TODAY = datetime.now(IST).date()


def _day(offset):
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture
def manager(role_client):
    return role_client("maint_manager")


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def vendor(make_vendor):
    return make_vendor()


@pytest.fixture
def body(vendor, uniq):
    def make(**overrides):
        return {"vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "from_date": _day(-30), "to_date": _day(300), **overrides}
    return make


@pytest.fixture
def machine_at(make_equipment, make_unit):
    """machine_at(site) -> a machine in a new unit of ``site``."""
    return lambda site: make_equipment(unit=make_unit(site=site))


@pytest.fixture
def machine(machine_at, site):
    return machine_at(site)


def _put_on(admin, contract, node, price=None):
    """The node on the contract, by ``admin`` (IT admin: every unit; keycloak_admin to keep a price) -> the
    detail."""
    payload = {"equipment_id": node["id"]} if price is None else {"equipment_id": node["id"], "price": price}
    res = admin.post(f"{CONTRACTS}/{contract['id']}/equipment", json=payload)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


@pytest.fixture
def add(manager, admin, body, machine):
    """add(client=manager, on=machine, **fields) -> a contract made through the API (201), with a line on ``on``
    (the test's machine at its site; None for no line)."""
    def make(client=None, on=machine, **overrides):
        res = (client or manager).post(CONTRACTS, json=body(**overrides))
        assert res.status_code == 201, res.get_json()
        contract = res.get_json()
        if on is not None:
            _put_on(admin, contract, on)
        return contract
    return make


def _refusal(res):
    return res.status_code, res.get_json()


def _stored(db_rows, contract_id):
    return db_rows("SELECT * FROM contracts WHERE id = %s", (contract_id,))[0]


def _listed(client, query):
    res = client.get(f"{CONTRACTS}?{query}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _ids(client, query):
    return [c["id"] for c in _listed(client, query)["items"]]


class TestCreate:

    def test_engineer_creates_with_the_callout_number_but_no_cost_note(self, engineer, body, db_rows):
        res = engineer.post(CONTRACTS, json=body(callout_number=CALLOUT, cost_note="Rs 1,20,000 a year",
                                                 covers_labour=True, pm_visits_per_year=4, response_hours=24))
        assert res.status_code == 201, res.get_json()
        item = res.get_json()
        assert item["status"] == {"kind": "in_force", "label": "In force", "days": None}
        assert (item["can_edit"], item["can_read_callout"], item["can_read_cost"]) == (True, True, False)
        assert item["callout_number"] == CALLOUT
        assert "cost_note" not in item and "renewal_of_id" not in item
        assert (item["covers_labour"], item["pm_visits_per_year"], item["response_hours"], item["active"]) == (
            1, 4, 24, 1)
        assert item["created_by"] == "test_maint_engineer"
        row = _stored(db_rows, item["id"])
        assert (row["callout_number"], row["cost_note"]) == (CALLOUT, None)

    def test_manager_reads_both_gated_fields(self, manager, body):
        res = manager.post(CONTRACTS, json=body(callout_number=CALLOUT, cost_note="Rs 1,20,000"))
        assert res.status_code == 201
        item = res.get_json()
        assert (item["callout_number"], item["cost_note"]) == (CALLOUT, "Rs 1,20,000")
        assert (item["can_read_callout"], item["can_read_cost"]) == (True, True)

    def test_it_admin_creates_but_neither_gated_field_is_stored(self, admin, body, db_rows):
        res = admin.post(CONTRACTS, json=body(callout_number=CALLOUT, cost_note="Rs 1"))
        assert res.status_code == 201
        item = res.get_json()
        assert "callout_number" not in item and "cost_note" not in item
        assert (item["can_edit"], item["can_read_callout"], item["can_read_cost"]) == (True, False, False)
        row = _stored(db_rows, item["id"])
        assert (row["callout_number"], row["cost_note"]) == (None, None)

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_roles_without_edit_get_403(self, role_client, role, body):
        assert role_client(role).post(CONTRACTS, json=body()).status_code == 403

    def test_a_site_id_sent_is_ignored(self, manager, admin, make_site, body, db_rows):
        """S087 § 5.5, F5: an old tab's site_id is an unknown field, on a POST and a PUT; no site is stored."""
        closed = make_site()
        assert admin.put(f"{SITES}/{closed['id']}", json={"active": False}).status_code == 200
        for site_id in (999999, closed["id"]):
            res = manager.post(CONTRACTS, json=body(site_id=site_id))
            assert res.status_code == 201, res.get_json()
            item = res.get_json()
            assert "site_id" not in item and "site_code" not in item and item["site_codes"] == []
        assert "site_id" not in _stored(db_rows, item["id"])
        res = manager.put(f"{CONTRACTS}/{item['id']}", json={"site_id": 999999, "title": "Same contract"})
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["title"] == "Same contract"

    def test_the_403_text_is_the_global_one(self, role_client, body):
        """S087 § 5.1: a contract check names no site."""
        assert _refusal(role_client("maint_operator").post(CONTRACTS, json=body())) == (
            403, {"error": FORBIDDEN_TEXT})

    def test_an_unknown_inactive_or_missing_vendor_is_refused(self, manager, engineer, make_vendor, body):
        assert _refusal(manager.post(CONTRACTS, json=body(vendor_id=999999))) == (
            400, {"error": "That vendor no longer exists. Reload and try again.", "field": "vendor_id"})
        old = make_vendor()
        assert engineer.put(f"{VENDORS}/{old['id']}", json={"active": False}).status_code == 200
        assert _refusal(manager.post(CONTRACTS, json=body(vendor_id=old["id"]))) == (
            400, {"error": f"Vendor {old['name']} is inactive. Choose another vendor or reactivate it.",
                  "field": "vendor_id"})
        assert _refusal(manager.post(CONTRACTS, json=body(vendor_id=None))) == (
            400, {"error": VENDOR_MISSING, "field": "vendor_id"})

    def test_the_period_and_calls_rules(self, manager, body):
        assert _refusal(manager.post(CONTRACTS, json=body(from_date=_day(10), to_date=_day(9)))) == (
            400, {"error": TO_BEFORE_FROM, "field": "to_date"})
        assert _refusal(manager.post(CONTRACTS, json=body(breakdown_calls_per_year=4))) == (
            400, {"error": CALLS_WITHOUT_TICK, "field": "breakdown_calls_per_year"})
        ok = manager.post(CONTRACTS, json=body(covers_breakdown_calls=True, breakdown_calls_per_year=4))
        assert ok.status_code == 201 and ok.get_json()["breakdown_calls_per_year"] == 4

    def test_a_missing_title_says_what_to_do(self, manager, body):
        payload = body()
        del payload["title"]
        assert _refusal(manager.post(CONTRACTS, json=payload)) == (400, {"error": "Enter a title.", "field": "title"})


class TestChange:

    def test_each_field_is_written(self, manager, add, make_vendor, db_rows):
        contract = add()
        other = make_vendor()
        change = {"contract_type": "cmc", "title": "Atlas Copco CMC", "contract_number": "AMC-0000-R",
                  "from_date": _day(-60), "to_date": _day(200), "covers_labour": True, "covers_parts": True,
                  "covers_consumables": True, "covers_breakdown_calls": True, "breakdown_calls_per_year": 6,
                  "covered_text": "Labour and parts", "not_covered_text": "Oil", "pm_visits_per_year": 4,
                  "response_hours": 24, "only_vendor_repairs": True, "callout_number": CALLOUT,
                  "cost_note": "Rs 2", "notes": "Two visits a year", "vendor_id": other["id"]}
        res = manager.put(f"{CONTRACTS}/{contract['id']}", json=change)
        assert res.status_code == 200, res.get_json()
        item = res.get_json()
        flags = ("covers_labour", "covers_parts", "covers_consumables", "covers_breakdown_calls", "only_vendor_repairs")
        assert {k: item[k] for k in change} == {**change, **{k: 1 for k in flags}}
        assert (item["vendor_name"], item["updated_by"]) == (other["name"], "test_maint_manager")
        assert item["updated_at"]

    def test_the_period_on_the_merged_values(self, manager, add):
        contract = add(from_date=_day(-30), to_date=_day(300))
        url = f"{CONTRACTS}/{contract['id']}"
        assert _refusal(manager.put(url, json={"to_date": _day(-31)})) == (
            400, {"error": TO_BEFORE_FROM, "field": "to_date"})
        assert _refusal(manager.put(url, json={"from_date": _day(301)})) == (
            400, {"error": FROM_AFTER_TO, "field": "from_date"})

    def test_the_tick_off_clears_the_calls(self, manager, add, db_rows):
        contract = add(covers_breakdown_calls=True, breakdown_calls_per_year=4)
        res = manager.put(f"{CONTRACTS}/{contract['id']}", json={"covers_breakdown_calls": False})
        assert res.status_code == 200
        row = _stored(db_rows, contract["id"])
        assert (row["covers_breakdown_calls"], row["breakdown_calls_per_year"]) == (0, None)

    def test_the_vendor_change(self, manager, engineer, add, make_vendor):
        contract = add()
        url = f"{CONTRACTS}/{contract['id']}"
        active, inactive = make_vendor(), make_vendor()
        assert engineer.put(f"{VENDORS}/{inactive['id']}", json={"active": False}).status_code == 200
        assert manager.put(url, json={"vendor_id": active["id"]}).status_code == 200
        res = manager.put(url, json={"vendor_id": inactive["id"]})
        assert res.status_code == 400 and res.get_json()["field"] == "vendor_id"

    def test_a_contract_whose_vendor_became_inactive_still_saves(self, manager, engineer, add, vendor):
        contract = add()
        assert engineer.put(f"{VENDORS}/{vendor['id']}", json={"active": False}).status_code == 200
        res = manager.put(f"{CONTRACTS}/{contract['id']}", json={"vendor_id": vendor["id"], "title": "New title"})
        assert res.status_code == 200
        assert (res.get_json()["title"], res.get_json()["vendor_active"]) == ("New title", 0)

    def test_deactivate_and_reactivate(self, manager, add):
        contract = add()
        url = f"{CONTRACTS}/{contract['id']}"
        assert manager.put(url, json={"active": False}).get_json()["active"] == 0
        assert manager.put(url, json={"active": True}).get_json()["active"] == 1

    def test_an_engineer_leaves_the_managers_cost_note(self, manager, engineer, add, db_rows):
        contract = add(cost_note="Rs 1,20,000")
        res = engineer.put(f"{CONTRACTS}/{contract['id']}", json={"cost_note": "changed", "title": "Edited"})
        assert res.status_code == 200 and "cost_note" not in res.get_json()
        row = _stored(db_rows, contract["id"])
        assert (row["cost_note"], row["title"]) == ("Rs 1,20,000", "Edited")

    def test_it_admin_leaves_the_callout_number(self, admin, add, db_rows):
        contract = add(callout_number=CALLOUT)
        assert admin.put(f"{CONTRACTS}/{contract['id']}", json={"callout_number": "+91 11111 11111"}).status_code == 200
        assert _stored(db_rows, contract["id"])["callout_number"] == CALLOUT

    def test_an_engineer_of_one_site_reads_and_edits_every_contract(self, user_at_sites, make_site, site, add):
        """S087 § 5.1, F1: an engineer of B reads the call-out number of, and edits, a contract whose machines are
        all at A."""
        contract = add(callout_number=CALLOUT)
        other, _ = user_at_sites([(make_site(), "maint_engineer", "all")])
        url = f"{CONTRACTS}/{contract['id']}"
        detail = other.get(url).get_json()
        assert detail["callout_number"] == CALLOUT and detail["site_codes"] == [site["code"]]
        assert (detail["can_edit"], detail["can_read_callout"], detail["can_read_cost"]) == (True, True, False)
        res = other.put(url, json={"title": "Edited at B"})
        assert res.status_code == 200, res.get_json()
        assert res.get_json()["title"] == "Edited at B"

    def test_an_operator_of_the_machines_site_may_not_edit(self, user_at_sites, site, add):
        operator, _ = user_at_sites([(site, "maint_operator", "all")])
        assert _refusal(operator.put(f"{CONTRACTS}/{add()['id']}", json={"title": "x"})) == (
            403, {"error": FORBIDDEN_TEXT})

    def test_a_missing_id_is_404(self, manager):
        assert manager.put(f"{CONTRACTS}/999999", json={"title": "x"}).status_code == 404


class TestRead:

    def test_an_engineer_of_one_site_lists_every_contract(self, user_at_sites, make_site, machine_at, admin, add):
        """S087 § 5.10: the list is company-wide; was "the list holds only the sites held"."""
        a, b = make_site(), make_site()
        in_a, in_b = add(on=machine_at(a)), add(on=machine_at(b))
        at_a, _ = user_at_sites([(a, "maint_engineer", "all")])
        for client in (at_a, admin):
            listed = _ids(client, "")
            assert in_a["id"] in listed and in_b["id"] in listed

    def test_the_site_filter_follows_the_machines(self, manager, make_site, machine_at, add):
        """S087 § 5.10, F7: site_id keeps the contracts with a machine at that site; one with no line shows only
        unfiltered; an unknown site gives an empty list."""
        a, b = make_site(), make_site()
        at_a, no_line = add(on=machine_at(a)), add(on=None)
        assert _ids(manager, f"site_id={a['id']}") == [at_a["id"]]
        assert _ids(manager, f"site_id={b['id']}") == []
        assert {at_a["id"], no_line["id"]} <= set(_ids(manager, ""))
        assert _ids(manager, "site_id=999999") == []

    def test_a_contract_with_machines_of_two_sites(self, user_at_sites, make_site, machine_at, body):
        """S087 § 5.2: the manager of both adds a machine of each; the sites are the machines' sites, by code."""
        a, b = make_site(), make_site()
        both, _ = user_at_sites([(a, "maint_manager", "all"), (b, "maint_manager", "all")])
        res = both.post(CONTRACTS, json=body())
        assert res.status_code == 201, res.get_json()
        contract = res.get_json()
        assert contract["site_codes"] == []
        for site in (b, a):
            res = both.post(f"{CONTRACTS}/{contract['id']}/equipment", json={"equipment_id": machine_at(site)["id"]})
            assert res.status_code == 201, res.get_json()
        detail = both.get(f"{CONTRACTS}/{contract['id']}").get_json()
        codes = sorted([a["code"], b["code"]])
        assert detail["site_codes"] == codes
        assert sorted(line["site_code"] for line in detail["machines"]) == codes
        assert all("at_contract_site" not in line for line in detail["machines"])
        assert "site_id" not in detail and "site_code" not in detail and "site_active" not in detail
        item = next(c for c in _listed(both, f"site_id={a['id']}")["items"] if c["id"] == contract["id"])
        assert item["site_codes"] == codes and "site_id" not in item

    def test_a_manager_of_one_site_reads_every_price(self, user_at_sites, make_site, machine, keycloak_admin, add):
        """S087 § 5.1, F1 (KLA accepted it): a manager of B reads the price total and cost note of an A-only
        contract."""
        contract = add(on=None, cost_note="Rs 1,20,000")
        _put_on(keycloak_admin, contract, machine, price="9809")   # IT admin's price would be dropped
        other, _ = user_at_sites([(make_site(), "maint_manager", "all")])
        detail = other.get(f"{CONTRACTS}/{contract['id']}").get_json()
        assert (detail["cost_note"], detail["price_total"], detail["priced_count"]) == ("Rs 1,20,000", "9809.00", 1)
        assert detail["machines"][0]["price"] == "9809.00"

    def test_filters(self, manager, add, make_vendor, site):
        other = make_vendor()
        amc = add()
        cmc = add(contract_type="cmc", vendor_id=other["id"])
        base = f"site_id={site['id']}"
        assert _ids(manager, f"{base}&contract_type=cmc") == [cmc["id"]]
        assert _ids(manager, f"{base}&vendor_id={other['id']}") == [cmc["id"]]
        assert manager.put(f"{CONTRACTS}/{amc['id']}", json={"active": False}).status_code == 200
        assert _ids(manager, base) == [cmc["id"]]
        assert set(_ids(manager, f"{base}&include_inactive=1")) == {amc["id"], cmc["id"]}

    def test_status_filters_and_order(self, manager, add, site):
        ended_long = add(from_date=_day(-400), to_date=_day(-40))
        ended = add(from_date=_day(-400), to_date=_day(-10))
        ending = add(from_date=_day(-300), to_date=_day(20))
        in_force = add(from_date=_day(-30), to_date=_day(300))
        upcoming = add(from_date=_day(100), to_date=_day(400))
        base = f"site_id={site['id']}"
        assert _ids(manager, base) == [ending["id"], in_force["id"], upcoming["id"]]
        assert _ids(manager, f"{base}&status=") == [ending["id"], in_force["id"], upcoming["id"]]
        assert _ids(manager, f"{base}&status=in_force") == [ending["id"], in_force["id"]]
        assert _ids(manager, f"{base}&status=ending") == [ending["id"]]
        assert _ids(manager, f"{base}&status=upcoming") == [upcoming["id"]]
        assert _ids(manager, f"{base}&status=ended") == [ended["id"], ended_long["id"]]
        assert _ids(manager, f"{base}&status=all") == [
            ended_long["id"], ended["id"], ending["id"], in_force["id"], upcoming["id"]]
        listed = {c["id"]: c["status"] for c in _listed(manager, f"{base}&status=all")["items"]}
        assert listed[ending["id"]] == {"kind": "ending", "label": "Ends in 20 days", "days": 20}
        assert listed[ended["id"]]["kind"] == "ended"
        assert listed[upcoming["id"]]["label"] == f"Starts on {(TODAY + timedelta(days=100)).strftime('%d-%m-%Y')}"

    def test_total_and_the_cap(self, manager, add, site, monkeypatch):
        for _ in range(3):
            add()
        monkeypatch.setattr(contracts, "MAX_PER_PAGE", 2)
        answer = _listed(manager, f"site_id={site['id']}")
        assert (len(answer["items"]), answer["total"]) == (2, 3)

    def test_the_list_flags_are_global(self, role_client, admin, engineer, manager, user_at_sites, make_site,
                                       site):
        """S087 § 5.10: top-level can_add, can_read_callout, can_read_cost per role; ``sites`` every site, inactive
        ones too, without flags."""
        closed = make_site()
        assert admin.put(f"{SITES}/{closed['id']}", json={"active": False}).status_code == 200
        one_site_engineer, _ = user_at_sites([(make_site(), "maint_engineer", "all")])

        def flags(client):
            answer = _listed(client, f"site_id={site['id']}")
            listed = {s["id"]: s for s in answer["sites"]}
            assert listed[site["id"]] == {"id": site["id"], "code": site["code"], "name": site["name"], "active": 1}
            assert listed[closed["id"]]["active"] == 0
            return answer["can_add"], answer["can_read_callout"], answer["can_read_cost"]
        assert flags(engineer) == (True, True, False)
        assert flags(one_site_engineer) == (True, True, False)
        assert flags(manager) == (True, True, True)
        assert flags(admin) == (True, False, False)
        assert flags(role_client("maint_operator")) == (False, False, False)

    def test_query_errors(self, manager):
        assert _refusal(manager.get(f"{CONTRACTS}?site_id=x")) == (
            400, {"error": "site_id must be a whole number at least 1", "field": "site_id"})
        assert manager.get(f"{CONTRACTS}?status=soon").status_code == 400
        assert manager.get(f"{CONTRACTS}?contract_type=lease").status_code == 400

    def test_the_detail(self, role_client, engineer, manager, user_at_sites, make_site, site, add):
        contract = add(callout_number=CALLOUT, cost_note="Rs 1")
        url = f"{CONTRACTS}/{contract['id']}"
        operator = role_client("maint_operator").get(url).get_json()
        assert "callout_number" not in operator and "cost_note" not in operator
        as_engineer = engineer.get(url).get_json()
        assert as_engineer["callout_number"] == CALLOUT and "cost_note" not in as_engineer
        as_manager = manager.get(url).get_json()
        assert (as_manager["callout_number"], as_manager["cost_note"]) == (CALLOUT, "Rs 1")
        assert as_manager["site_codes"] == [site["code"]] and "site_code" not in as_manager
        # S087: the 404 means missing; a reader of another site reads it
        other_site, _ = user_at_sites([(make_site(), "maint_manager", "all")])
        assert other_site.get(url).status_code == 200
        assert _refusal(manager.get(f"{CONTRACTS}/999999")) == (404, {"error": "Not found"})

    def test_the_list_without_a_slash_is_not_a_redirect(self, manager):
        assert manager.get(CONTRACTS).status_code == 200

    def test_the_document_flags_follow_the_keys(self, role_client, admin, keycloak_admin, engineer, manager, site,
                                                add):
        """S083 § 6.1: documents are read with contract:read_senior, written with contract:edit and read_senior."""
        contract = add()
        assert (contract["can_read_documents"], contract["can_edit_documents"]) == (True, True)

        def flags(client):
            detail = client.get(f"{CONTRACTS}/{contract['id']}").get_json()
            item = next(c for c in _listed(client, f"site_id={site['id']}")["items"] if c["id"] == contract["id"])
            assert (item["can_read_documents"], item["can_edit_documents"]) == (
                detail["can_read_documents"], detail["can_edit_documents"])
            return detail["can_read_documents"], detail["can_edit_documents"]
        assert flags(manager) == (True, True)
        assert flags(engineer) == (False, False)
        assert flags(admin) == (False, False)
        assert flags(keycloak_admin) == (True, True)
        assert flags(role_client("maint_operator")) == (False, False)


class TestRoles:

    def test_a_login_without_a_site_role_is_refused(self, role_client):
        assert role_client(LOGIN_ROLE).get(CONTRACTS).status_code == 403


class TestDatabaseDown:

    def test_list_and_create_answer_503(self, body, manager, db_down):
        assert manager.get(CONTRACTS).status_code == 503
        assert manager.post(CONTRACTS, json=body()).status_code == 503
