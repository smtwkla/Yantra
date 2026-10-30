"""Vendor contracts (S080 § 5, § 6, § 8.2) — the API, against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).  Each test makes its own sites and vendors, so a list filtered by its site holds only
its own contracts.  The call-out number is obviously fake, never a real number (D10)."""

from datetime import datetime, timedelta

import pytest

import contracts
from config_rbac import LOGIN_ROLE
from contracts_core import CALLS_WITHOUT_TICK, FROM_AFTER_TO, SITE_KEPT, TO_BEFORE_FROM, VENDOR_MISSING
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
def body(site, vendor, uniq):
    def make(**overrides):
        return {"site_id": site["id"], "vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "from_date": _day(-30), "to_date": _day(300), **overrides}
    return make


@pytest.fixture
def add(manager, body):
    """add(client=manager, **fields) -> a contract made through the API (201)."""
    def make(client=None, **overrides):
        res = (client or manager).post(CONTRACTS, json=body(**overrides))
        assert res.status_code == 201, res.get_json()
        return res.get_json()
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

    def test_an_engineer_of_a_creating_at_b_is_refused_naming_b(self, user_at_sites, make_site, body):
        a, b = make_site(), make_site()
        client, _ = user_at_sites([(a, "maint_engineer", "all"), (b, "maint_operator", "all")])
        assert client.post(CONTRACTS, json=body(site_id=a["id"])).status_code == 201
        assert _refusal(client.post(CONTRACTS, json=body(site_id=b["id"]))) == (
            403, {"error": f"You can't do this at {b['code']}", "field": "site_id"})

    def test_an_unknown_or_inactive_site_is_refused(self, manager, admin, make_site, body):
        assert _refusal(manager.post(CONTRACTS, json=body(site_id=999999))) == (
            400, {"error": "Choose a site.", "field": "site_id"})
        closed = make_site()
        assert admin.put(f"{SITES}/{closed['id']}", json={"active": False}).status_code == 200
        assert _refusal(manager.post(CONTRACTS, json=body(site_id=closed["id"]))) == (
            400, {"error": "Choose an active site.", "field": "site_id"})

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

    def test_the_site_is_kept(self, manager, add, make_site):
        contract = add()
        url = f"{CONTRACTS}/{contract['id']}"
        assert manager.put(url, json={"site_id": contract["site_id"], "title": "Same site"}).status_code == 200
        assert _refusal(manager.put(url, json={"site_id": make_site()["id"]})) == (
            400, {"error": SITE_KEPT, "field": "site_id"})

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

    def test_another_sites_engineer(self, user_at_sites, make_site, add):
        a, b = make_site(), make_site()
        contract = add(site_id=a["id"])
        stranger, _ = user_at_sites([(b, "maint_engineer", "all")])
        assert _refusal(stranger.put(f"{CONTRACTS}/{contract['id']}", json={"title": "x"})) == (
            404, {"error": "Not found"})
        reader, _ = user_at_sites([(b, "maint_engineer", "all"), (a, "maint_operator", "all")])
        assert _refusal(reader.put(f"{CONTRACTS}/{contract['id']}", json={"title": "x"})) == (
            403, {"error": f"You can't do this at {a['code']}"})

    def test_a_missing_id_is_404(self, manager):
        assert manager.put(f"{CONTRACTS}/999999", json={"title": "x"}).status_code == 404


class TestRead:

    def test_the_list_holds_only_the_sites_held(self, user_at_sites, make_site, admin, add):
        a, b = make_site(), make_site()
        in_a, in_b = add(site_id=a["id"]), add(site_id=b["id"])
        at_a, _ = user_at_sites([(a, "maint_engineer", "all")])
        both, _ = user_at_sites([(a, "maint_manager", "all"), (b, "maint_manager", "all")])
        assert in_a["id"] in _ids(at_a, "") and in_b["id"] not in _ids(at_a, "")
        assert _ids(at_a, f"site_id={b['id']}") == []
        for client in (admin, both):
            listed = _ids(client, "")
            assert in_a["id"] in listed and in_b["id"] in listed

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

    def test_sites_and_their_flags_per_role(self, role_client, admin, engineer, manager, site):
        def flags(client):
            answer = _listed(client, f"site_id={site['id']}")
            row = next(s for s in answer["sites"] if s["id"] == site["id"])
            return row["can_add"], row["can_read_callout"], row["can_read_cost"]
        assert flags(engineer) == (True, True, False)
        assert flags(manager) == (True, True, True)
        assert flags(admin) == (True, False, False)
        assert flags(role_client("maint_operator")) == (False, False, False)

    def test_query_errors(self, manager):
        assert _refusal(manager.get(f"{CONTRACTS}?site_id=x")) == (
            400, {"error": "site_id must be a whole number at least 1", "field": "site_id"})
        assert manager.get(f"{CONTRACTS}?status=soon").status_code == 400
        assert manager.get(f"{CONTRACTS}?contract_type=lease").status_code == 400

    def test_the_detail(self, role_client, engineer, manager, user_at_sites, make_site, add):
        contract = add(callout_number=CALLOUT, cost_note="Rs 1")
        url = f"{CONTRACTS}/{contract['id']}"
        operator = role_client("maint_operator").get(url).get_json()
        assert "callout_number" not in operator and "cost_note" not in operator
        as_engineer = engineer.get(url).get_json()
        assert as_engineer["callout_number"] == CALLOUT and "cost_note" not in as_engineer
        as_manager = manager.get(url).get_json()
        assert (as_manager["callout_number"], as_manager["cost_note"]) == (CALLOUT, "Rs 1")
        stranger, _ = user_at_sites([(make_site(), "maint_manager", "all")])
        assert _refusal(stranger.get(url)) == (404, {"error": "Not found"})
        assert manager.get(f"{CONTRACTS}/999999").status_code == 404

    def test_the_list_without_a_slash_is_not_a_redirect(self, manager):
        assert manager.get(CONTRACTS).status_code == 200


class TestRoles:

    def test_a_login_without_a_site_role_is_refused(self, role_client):
        assert role_client(LOGIN_ROLE).get(CONTRACTS).status_code == 403


class TestDatabaseDown:

    def test_list_and_create_answer_503(self, body, manager, db_down):
        assert manager.get(CONTRACTS).status_code == 503
        assert manager.post(CONTRACTS, json=body()).status_code == 503
