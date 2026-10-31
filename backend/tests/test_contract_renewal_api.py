"""Contract renewal (S085 § 5, § 6, § 8.2) — the API, against the test DB.  Needs the dev MariaDB container
(tooling/dev/dev-db-up.bat).  Each test makes its own site, unit, vendor, contract and machines, so nothing it reads
belongs to another test.  A renewal is a new contract at the old one's site with renewal_of_id the old one (one per
contract, v47); it copies the terms sent and the in-service machines of the site, never a price, the cost note or a
document, and never changes the old contract.  Phone values are obviously fake, never a real number."""

from datetime import datetime, timedelta

import pytest

import alerts
import config
from api_common import UNIQUE_KEY_ERRORS
from contracts_core import renewal_period
from equipment import IST
from local_db import get_local_db

CONTRACTS = "/api/contracts"
EQUIPMENT = "/api/equipment"
SITES = "/api/masters/sites"
TODAY = datetime.now(IST).date()
CALLOUT = "+91 00000 00000"
OTHER_CALLOUT = "+91 00000 00001"

# The old contract's period (§ 8.4): from 300 days ago to 65 days ahead
OLD_FROM, OLD_TO = TODAY - timedelta(days=300), TODAY + timedelta(days=65)
NEW_FROM, NEW_TO = renewal_period(OLD_FROM, OLD_TO)

# The terms the dialog copies (§ 5.4), apart from the gated fields and the dates
_TERMS = ("vendor_id", "contract_type", "title", "contract_number", "covers_labour", "covers_parts",
          "covers_consumables", "covers_breakdown_calls", "breakdown_calls_per_year", "covered_text",
          "not_covered_text", "pm_visits_per_year", "response_hours", "only_vendor_repairs", "notes")


@pytest.fixture
def manager(role_client):
    return role_client("maint_manager")


@pytest.fixture
def site(make_site):
    return make_site()


@pytest.fixture
def site_engineer(user_at_sites, site):
    """An engineer of ``site`` with all its units."""
    client, _person = user_at_sites([(site, "maint_engineer", "all")])
    return client


@pytest.fixture
def unit(make_unit, site):
    return make_unit(site=site)


@pytest.fixture
def vendor(make_vendor):
    return make_vendor()


@pytest.fixture
def add_contract(manager, vendor, site, uniq):
    """add_contract(**fields) -> a contract at ``site`` made by the manager (201), with a call-out number and a cost
    note, from 300 days ago to 65 days ahead."""
    def make(**overrides):
        body = {"site_id": site["id"], "vendor_id": vendor["id"], "contract_type": "amc",
                "title": f"AMC {uniq.vendor_name()}", "contract_number": "AC/2026/17", "covers_labour": 1,
                "covers_parts": 1, "covers_breakdown_calls": 1, "breakdown_calls_per_year": 4,
                "covered_text": "Air end, motor", "not_covered_text": "Filters", "pm_visits_per_year": 4,
                "response_hours": 24, "only_vendor_repairs": 1, "notes": "Quote 17", "callout_number": CALLOUT,
                "cost_note": "Rs 37,837 a year", "from_date": OLD_FROM.isoformat(), "to_date": OLD_TO.isoformat(),
                **overrides}
        res = manager.post(CONTRACTS, json=body)
        assert res.status_code == 201, res.get_json()
        return res.get_json()
    return make


@pytest.fixture
def old(add_contract):
    return add_contract()


def _path(contract):
    return f"{CONTRACTS}/{contract['id']}/renew"


def _body(detail, **overrides):
    """The dialog's form (§ 5.7 renewalForm): the old terms, the proposed dates, the call-out number when the
    reader has it, no cost note."""
    body = {key: detail[key] for key in _TERMS}
    body.update(from_date=NEW_FROM.isoformat(), to_date=NEW_TO.isoformat(), title=f"{detail['title']} next")
    if "callout_number" in detail:
        body["callout_number"] = detail["callout_number"]
    return {**body, **overrides}


def _renew(client, contract, **overrides):
    return client.post(_path(contract), json=_body(contract, **overrides))


def _renewed(client, contract, **overrides):
    res = _renew(client, contract, **overrides)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _refusal(res):
    return res.status_code, res.get_json()


def _row(db_rows, contract_id):
    return db_rows("SELECT * FROM contracts WHERE id = %s", (contract_id,))[0]


def _lines(db_rows, contract_id):
    return list(db_rows("SELECT equipment_id, price, created_by FROM contract_equipment WHERE contract_id = %s"
                        " ORDER BY equipment_id", (contract_id,)))


def _events(db_rows, node):
    return list(db_rows("SELECT old_value, new_value FROM equipment_events WHERE equipment_id = %s"
                        " AND event = 'contract_added' ORDER BY id", (node["id"],)))


def _add_line(client, contract, node, **fields):
    res = client.post(f"{CONTRACTS}/{contract['id']}/equipment", json={"equipment_id": node["id"], **fields})
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _set_contract(client, contract, **fields):
    res = client.put(f"{CONTRACTS}/{contract['id']}", json=fields)
    assert res.status_code == 200, res.get_json()


def _detail(client, contract):
    res = client.get(f"{CONTRACTS}/{contract['id']}")
    assert res.status_code == 200, res.get_json()
    return res.get_json()


def _dmy(day):
    return day.strftime("%d-%m-%Y")


class TestRenew:

    def test_engineer_renews_a_contract(self, site_engineer, site, old, db_rows):
        before = _row(db_rows, old["id"])
        new = _renewed(site_engineer, old)
        row = _row(db_rows, new["id"])
        for key in _TERMS:
            expected = f"{old['title']} next" if key == "title" else old[key]
            assert row[key] == expected, key
        assert (row["from_date"], row["to_date"]) == (NEW_FROM, NEW_TO)
        assert (row["site_id"], row["renewal_of_id"], row["active"]) == (site["id"], old["id"], 1)
        assert (row["first_reminder_for"], row["second_reminder_for"]) == (None, None)
        assert row["created_by"] == site_engineer._headers["X-Test-User"]
        assert (row["updated_at"], row["updated_by"]) == (None, None)
        assert row["callout_number"] == CALLOUT and row["cost_note"] is None
        assert _row(db_rows, old["id"]) == before   # the old contract unchanged, every column
        assert new["skipped"] == [] and new["machines"] == []

    def test_renewal_copies_the_machines_without_prices(self, manager, site_engineer, old, unit, make_equipment,
                                                        db_rows):
        first, second = make_equipment(unit=unit), make_equipment(unit=unit)
        _add_line(manager, old, first, price="9809")
        _add_line(manager, old, second, price="28028")
        new = _renewed(site_engineer, old)
        assert [line["equipment_id"] for line in _lines(db_rows, new["id"])] == sorted([first["id"], second["id"]])
        assert all(line["price"] is None for line in _lines(db_rows, new["id"]))
        added = f"{old['title']} next (AMC, {_dmy(NEW_FROM)} to {_dmy(NEW_TO)})"
        for node in (first, second):
            assert _events(db_rows, node)[-1] == {"old_value": None, "new_value": added}
        assert [str(line["price"]) for line in _lines(db_rows, old["id"])] == ["9809.00", "28028.00"]

    def test_manager_renewal_copies_no_price(self, manager, old, unit, make_equipment, db_rows):
        _add_line(manager, old, make_equipment(unit=unit), price="9809")
        new = _renewed(manager, old)
        assert [line["price"] for line in _lines(db_rows, new["id"])] == [None]
        assert (new["price_total"], new["priced_count"], new["machine_count"]) == (None, 0, 1)

    def test_renewal_skips_scrapped_and_moved_machines(self, admin, site_engineer, old, unit, make_equipment,
                                                       make_site, make_unit, db_rows):
        kept, scrapped, moved = (make_equipment(unit=unit) for _ in range(3))
        for node in (kept, scrapped, moved):
            _add_line(site_engineer, old, node)
        assert admin.put(f"{EQUIPMENT}/{scrapped['id']}", json={"lifecycle": "scrapped"}).status_code == 200
        other = make_site()
        assert admin.put(f"{EQUIPMENT}/{moved['id']}",
                         json={"unit_id": make_unit(site=other)["id"]}).status_code == 200
        offer = _detail(site_engineer, old)["renewal"]
        assert offer["machines"] == [{"equipment_id": kept["id"], "code": kept["code"]}]
        new = _renewed(site_engineer, old)
        assert sorted(new["skipped"], key=lambda s: s["equipment_id"]) == sorted([
            {"equipment_id": scrapped["id"], "code": scrapped["code"], "reason": "scrapped"},
            {"equipment_id": moved["id"], "code": moved["code"], "reason": f"now at {other['code']}"},
        ], key=lambda s: s["equipment_id"])
        assert [line["equipment_id"] for line in _lines(db_rows, new["id"])] == [kept["id"]]
        assert len(_events(db_rows, scrapped)) == 1 and len(_events(db_rows, moved)) == 1   # only the old add

    def test_renewal_copies_lines_outside_the_renewers_units(self, user_at_sites, manager, site, old, unit,
                                                             make_unit, make_equipment, db_rows):
        elsewhere = make_equipment(unit=make_unit(site=site))
        _add_line(manager, old, elsewhere)
        one_unit, _ = user_at_sites([(site, "maint_engineer", [unit])])
        new = _renewed(one_unit, old)
        assert [line["equipment_id"] for line in _lines(db_rows, new["id"])] == [elsewhere["id"]]

    def test_cost_note_comes_from_the_body_only(self, manager, site_engineer, add_contract, db_rows):
        by_manager = _renewed(manager, add_contract(), cost_note="Rs 40,000 a year")
        assert _row(db_rows, by_manager["id"])["cost_note"] == "Rs 40,000 a year"
        by_engineer = _renewed(site_engineer, add_contract(), cost_note="Rs 40,000 a year")
        assert _row(db_rows, by_engineer["id"])["cost_note"] is None
        not_sent = _renewed(manager, add_contract())
        assert _row(db_rows, not_sent["id"])["cost_note"] is None   # the old note is never copied

    def test_it_admin_renewal_copies_the_callout_number(self, admin, old, db_rows):
        detail = _detail(admin, old)
        assert "callout_number" not in detail
        new = _renewed(admin, detail)
        assert _row(db_rows, new["id"])["callout_number"] == CALLOUT
        assert "callout_number" not in new

    def test_it_admin_cannot_change_the_callout_number(self, admin, old, db_rows):
        # A gated field the writer may not read is ignored (_drop_gated): the old number stays
        new = _renewed(admin, _detail(admin, old), callout_number=OTHER_CALLOUT)
        assert _row(db_rows, new["id"])["callout_number"] == CALLOUT

    def test_engineer_may_change_the_callout_number(self, site_engineer, add_contract, db_rows):
        cleared = _renewed(site_engineer, add_contract(), callout_number="")
        assert _row(db_rows, cleared["id"])["callout_number"] is None
        changed = _renewed(site_engineer, add_contract(), callout_number=OTHER_CALLOUT)
        assert _row(db_rows, changed["id"])["callout_number"] == OTHER_CALLOUT

    def test_an_inactive_vendor_is_refused(self, admin, site_engineer, old, vendor, make_vendor):
        assert admin.put(f"/api/masters/vendors/{vendor['id']}", json={"active": 0}).status_code == 200
        assert _refusal(_renew(site_engineer, old)) == (400, {
            "error": f"Vendor {vendor['name']} is inactive. Choose another vendor or reactivate it.",
            "field": "vendor_id"})
        assert _renew(site_engineer, old, vendor_id=make_vendor()["id"]).status_code == 201

    def test_a_missing_vendor_is_refused(self, site_engineer, old):
        assert _refusal(_renew(site_engineer, old, vendor_id=999999999)) == (400, {
            "error": "That vendor no longer exists. Reload and try again.", "field": "vendor_id"})

    def test_an_inactive_contract_is_refused(self, site_engineer, old):
        _set_contract(site_engineer, old, active=0)
        assert _refusal(_renew(site_engineer, old)) == (409, {
            "error": "This contract is inactive. Set it active in Masters › Contracts, then renew it."})

    def test_an_inactive_site_is_refused(self, admin, site_engineer, site, old):
        # The site has no unit, so Masters lets it go inactive with its contract
        res = admin.put(f"{SITES}/{site['id']}", json={"active": 0})
        assert res.status_code == 200, res.get_json()
        assert _refusal(_renew(site_engineer, old)) == (409, {
            "error": f"{site['code']} is inactive. Set it active in Masters › Sites, then renew the contract."})

    def test_a_second_renewal_is_refused(self, site_engineer, old):
        first = _renewed(site_engineer, old)
        refused = (409, {"error": f"This contract is already renewed: {first['title']}. Open that contract to change"
                                  " it."})
        assert _refusal(_renew(site_engineer, old)) == refused
        _set_contract(site_engineer, first, active=0)
        assert _refusal(_renew(site_engineer, old)) == refused

    def test_the_body_is_checked(self, site_engineer, site, old, make_site, add_contract, db_rows):
        assert _refusal(_renew(site_engineer, old, to_date=(NEW_FROM - timedelta(days=1)).isoformat())) == (
            400, {"error": "Enter a To date on or after the From date.", "field": "to_date"})
        assert _refusal(_renew(site_engineer, old, title="")) == (400, {"error": "Enter a title.", "field": "title"})
        other = add_contract()
        new = _renewed(site_engineer, old, site_id=make_site()["id"], renewal_of_id=other["id"], active=0)
        row = _row(db_rows, new["id"])
        assert (row["site_id"], row["renewal_of_id"], row["active"]) == (site["id"], old["id"], 1)

    @pytest.mark.parametrize("role", ["maint_operator", "maint_technician", "maint_supervisor", "maint_storekeeper"])
    def test_renew_needs_edit(self, role_client, role, old):
        assert _renew(role_client(role), old).status_code == 403

    def test_renew_needs_edit_at_the_site(self, user_at_sites, make_site, site, site_engineer, old):
        b = make_site()
        stranger, _ = user_at_sites([(b, "maint_engineer", "all")])
        assert _refusal(_renew(stranger, old)) == (404, {"error": "Not found"})
        operator_here, _ = user_at_sites([(b, "maint_engineer", "all"), (site, "maint_operator", "all")])
        assert _refusal(_renew(operator_here, old)) == (403, {"error": f"You can't do this at {site['code']}"})
        assert site_engineer.post(f"{CONTRACTS}/999999999/renew", json=_body(old)).status_code == 404


class TestDetail:

    def test_detail_shows_the_chain(self, site_engineer, old, add_contract):
        new = _renewed(site_engineer, old)
        assert new["renewal_of"] == {"id": old["id"], "title": old["title"], "from_date": OLD_FROM.isoformat(),
                                     "to_date": OLD_TO.isoformat(), "active": True}
        assert new["renewed_by"] is None
        assert _detail(site_engineer, old)["renewed_by"] == {
            "id": new["id"], "title": new["title"], "from_date": NEW_FROM.isoformat(), "to_date": NEW_TO.isoformat(),
            "active": True}
        _set_contract(site_engineer, new, active=0)
        assert _detail(site_engineer, old)["renewed_by"]["active"] is False
        plain = _detail(site_engineer, add_contract())
        assert (plain["renewal_of"], plain["renewed_by"]) == (None, None)

    def test_detail_offers_the_renewal(self, role_client, site_engineer, old, unit, make_equipment):
        node = make_equipment(unit=unit)
        _add_line(site_engineer, old, node)
        detail = _detail(site_engineer, old)
        assert detail["can_renew"] is True
        assert detail["renewal"] == {"from_date": NEW_FROM.isoformat(), "to_date": NEW_TO.isoformat(),
                                     "machines": [{"equipment_id": node["id"], "code": node["code"]}],
                                     "skipped": []}
        assert "site_active" not in detail
        operator = _detail(role_client("maint_operator"), old)
        assert operator["can_renew"] is False and "renewal" not in operator
        _renewed(site_engineer, old)
        renewed = _detail(site_engineer, old)
        assert renewed["can_renew"] is False and "renewal" not in renewed

    def test_no_renewal_offered_when_inactive(self, admin, site_engineer, site, add_contract):
        inactive = add_contract()
        _set_contract(site_engineer, inactive, active=0)
        assert _detail(site_engineer, inactive)["can_renew"] is False
        active = add_contract()
        assert admin.put(f"{SITES}/{site['id']}", json={"active": 0}).status_code == 200
        assert _detail(site_engineer, active)["can_renew"] is False

    def test_the_offer_has_no_dates_past_2099(self, site_engineer, add_contract):
        late = add_contract(from_date="2099-01-01", to_date="2099-12-31")
        assert _detail(site_engineer, late)["renewal"]["from_date"] is None
        assert _detail(site_engineer, late)["renewal"]["to_date"] is None

    def test_a_write_answer_carries_the_chain(self, site_engineer, old, unit, make_equipment):
        answer = _add_line(site_engineer, old, make_equipment(unit=unit))
        assert answer["can_renew"] is True and answer["renewal"]["machines"]
        assert (answer["renewal_of"], answer["renewed_by"]) == (None, None)


class TestReminders:

    def test_a_renewed_contract_is_not_reminded(self, site_engineer, old):
        def renewed():
            conn = get_local_db(config.DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    return alerts.contract_renewed(cur, old["id"])
            finally:
                conn.close()
        assert renewed() is False
        new = _renewed(site_engineer, old)
        assert renewed() is True
        _set_contract(site_engineer, new, active=0)
        assert renewed() is False


def test_the_unique_key_message():
    assert UNIQUE_KEY_ERRORS["uq_contracts_renewal_of"] == (
        None, "This contract is already renewed. Reload the page to see the renewal.")


def test_renew_with_the_database_down(site_engineer, old, db_down):
    assert _renew(site_engineer, old).status_code == 503
