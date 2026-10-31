"""Vendor contracts — the pure rules (S080 § 5.1, § 5.3, § 8.2): the fields, the period, breakdown calls, the
status from the dates and the Status filter; S081's machine line, its price and the history text (S081 § 5.1,
§ 5.3); S082's card items and the list's Contract filter (S082 § 5.1, § 5.4); S085's renewal: the proposed period,
the machines copied and skipped, the body and the refusals' texts (S085 § 5.2-§ 5.5).  No database.  Phone values are
obviously fake, never a real number."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from contracts_core import (
    CALLS_WITHOUT_TICK, CARD_ENDED_DAYS, CONTRACT_TYPES, COVERAGE_FILTERS, ENDING_SOON_DAYS, FROM_AFTER_TO,
    LINE_GATED_FIELDS, PRICE_FORMAT, PRICE_MAX, PRICE_TOO_LARGE, RENEW_INACTIVE, RENEWAL_RACE, STATUS_FILTERS,
    TITLE_MAX, TO_BEFORE_FROM, TYPE_SHORT, VENDOR_MISSING, _add_months, already_renewed, breakdown_calls_error,
    card_items, contract_status, covered_sql, event_text, newest_end_first, parse_price, period_error,
    renew_site_inactive, renewal_lines, renewal_period, status_bounds, validate_contract, validate_line,
    validate_renewal,
)
from masters_core import PHONE_RULE

TODAY = date(2026, 10, 30)
VALID = {"site_id": 1, "vendor_id": 2, "contract_type": "amc", "title": "Atlas Copco AMC 2026–27",
         "from_date": "2026-04-01", "to_date": "2027-03-31"}


def _errors(body, creating=True):
    return validate_contract(body, creating)[1]


def _error_of(field, value, creating=False):
    """The one error a PUT with only ``field`` gives -> its message, or None when it passes."""
    clean, errors = validate_contract({field: value}, creating)
    assert len(errors) <= 1
    return errors[0]["message"] if errors else None


def _clean(field, value):
    clean, errors = validate_contract({field: value}, False)
    assert errors == [], errors
    return clean[field]


class TestFields:

    def test_a_full_post_is_clean(self):
        clean, errors = validate_contract(VALID, True)
        assert errors == []
        assert clean == {**VALID, "from_date": date(2026, 4, 1), "to_date": date(2027, 3, 31)}

    def test_every_required_field_missing_on_a_post_says_what_to_do(self):
        assert _errors({}) == [
            {"field": "site_id", "message": "Choose a site."},
            {"field": "vendor_id", "message": VENDOR_MISSING},
            {"field": "contract_type", "message": "Choose a type."},
            {"field": "title", "message": "Enter a title."},
            {"field": "from_date", "message": "Enter a From date."},
            {"field": "to_date", "message": "Enter a To date."},
        ]

    def test_nothing_is_required_on_a_put(self):
        assert validate_contract({}, False) == ({}, [])

    def test_the_title_is_collapsed_and_bounded(self):
        assert _clean("title", "  Atlas  Copco\nAMC ") == "Atlas Copco AMC"
        assert _clean("title", "x" * 100) == "x" * 100
        assert _error_of("title", "x" * 101) == "Title must be at most 100 characters"
        assert _error_of("title", 42) == "Title must be text"
        assert _error_of("title", "   ") == "Enter a title."

    def test_the_type_is_one_of_four(self):
        for kind in ("warranty", "amc", "cmc", "on_call"):
            assert _clean("contract_type", kind) == kind
        assert _error_of("contract_type", "AMC") == "Choose a type."
        assert _error_of("contract_type", "lease") == "Choose a type."

    def test_ids_are_whole_numbers(self):
        assert _error_of("site_id", True) == "Choose a site."
        assert _error_of("site_id", "1") == "Choose a site."
        assert _error_of("vendor_id", 0) == VENDOR_MISSING
        assert _clean("vendor_id", 7) == 7

    def test_the_contract_number_is_optional_and_collapsed(self):
        assert _clean("contract_number", " AMC  14 ") == "AMC 14"
        assert _clean("contract_number", "") is None
        assert _error_of("contract_number", "x" * 61) == "Contract number must be at most 60 characters"
        assert _error_of("contract_number", 5) == "Contract number must be text"

    @pytest.mark.parametrize("value", ["31-03-2027", "2027-02-30", "1999-12-31", "2100-01-01", "", None, 20270331, "20270331", "2027-W13-3", "2027-3-31"])
    def test_dates_out_of_form_or_range_are_refused(self, value):
        assert _error_of("from_date", value) == "Enter a From date."
        assert _error_of("to_date", value) == "Enter a To date."

    def test_the_date_bounds_pass(self):
        assert _clean("from_date", "2000-01-01") == date(2000, 1, 1)
        assert _clean("to_date", " 2099-12-31 ") == date(2099, 12, 31)

    def test_ticks(self):
        for field, label in (("covers_labour", "Labour"), ("covers_parts", "Spare parts"),
                             ("covers_consumables", "Consumables"), ("covers_breakdown_calls", "Breakdown calls"),
                             ("only_vendor_repairs", "Only the vendor may repair")):
            assert _clean(field, True) == 1
            assert _clean(field, 0) == 0
            assert _error_of(field, "yes") == f"{label} must be true or false"

    def test_calls_per_year(self):
        message = "Calls per year: a whole number from 1 to 365, or empty for no limit."
        for value in (0, 366, "4", True, 4.5):
            assert _error_of("breakdown_calls_per_year", value) == message
        assert _clean("breakdown_calls_per_year", None) is None
        assert _clean("breakdown_calls_per_year", 1) == 1
        assert _clean("breakdown_calls_per_year", 365) == 365

    def test_pm_visits_and_response_time(self):
        visits = "PM visits per year: a whole number from 0 to 52, or empty."
        assert _error_of("pm_visits_per_year", -1) == visits
        assert _error_of("pm_visits_per_year", 53) == visits
        assert _clean("pm_visits_per_year", 0) == 0
        assert _clean("pm_visits_per_year", 52) == 52
        hours = "Response time: a whole number of hours from 1 to 720, or empty."
        assert _error_of("response_hours", 0) == hours
        assert _error_of("response_hours", 721) == hours
        assert _clean("response_hours", 720) == 720

    def test_texts(self):
        for field, label, limit in (("covered_text", "Covered", 1000), ("not_covered_text", "Not covered", 1000),
                                    ("notes", "Notes", 1000), ("cost_note", "Cost note", 255)):
            assert _clean(field, "x" * limit) == "x" * limit
            assert _error_of(field, "x" * (limit + 1)) == f"{label} must be at most {limit} characters"
            assert _error_of(field, 3) == f"{label} must be text"
            assert _clean(field, "  ") is None
        assert _clean("notes", " line one\nline two ") == "line one\nline two"

    def test_the_callout_number_takes_the_phone_rule(self):
        assert _clean("callout_number", "+91 00000 00000") == "+91 00000 00000"
        assert _clean("callout_number", "(044) 0000-0000") == "(044) 0000-0000"
        assert _clean("callout_number", "") is None
        assert _error_of("callout_number", "call 000000") == PHONE_RULE
        assert _error_of("callout_number", "00000") == PHONE_RULE
        assert _error_of("callout_number", "0" * 21) == "Call-out number must be at most 20 characters"
        assert _error_of("callout_number", 91) == "Call-out number must be text"

    def test_active_is_ignored_on_a_post(self):
        clean, errors = validate_contract({**VALID, "active": False}, True)
        assert errors == [] and "active" not in clean
        assert _clean("active", False) == 0

    def test_unknown_fields_are_ignored(self):
        clean, errors = validate_contract({"renewal_of_id": 4, "price": 100}, False)
        assert (clean, errors) == ({}, [])

    def test_the_tick_off_with_no_number_clears_it(self):
        assert validate_contract({"covers_breakdown_calls": False}, False)[0] == {
            "covers_breakdown_calls": 0, "breakdown_calls_per_year": None}
        assert validate_contract({"covers_breakdown_calls": False, "breakdown_calls_per_year": 4}, False)[0] == {
            "covers_breakdown_calls": 0, "breakdown_calls_per_year": 4}
        assert validate_contract({"covers_breakdown_calls": True}, False)[0] == {"covers_breakdown_calls": 1}


class TestPeriodAndCalls:

    def test_equal_dates_pass(self):
        assert period_error(TODAY, TODAY, True) is None

    def test_to_before_from(self):
        assert period_error(TODAY, TODAY - timedelta(days=1), True) == ("to_date", TO_BEFORE_FROM)
        assert period_error(TODAY, TODAY - timedelta(days=1), False) == ("from_date", FROM_AFTER_TO)

    def test_calls_need_the_tick(self):
        assert breakdown_calls_error(0, 4) == CALLS_WITHOUT_TICK
        assert breakdown_calls_error(1, 4) is None
        assert breakdown_calls_error(0, None) is None


class TestStatus:

    def _status(self, from_offset, to_offset):
        return contract_status(TODAY + timedelta(days=from_offset), TODAY + timedelta(days=to_offset), TODAY)

    def test_kinds(self):
        assert self._status(1, 400) == {"kind": "upcoming", "label": "Starts on 31-10-2026", "days": None}
        assert self._status(0, 400) == {"kind": "in_force", "label": "In force", "days": None}
        assert self._status(-10, 0) == {"kind": "ending", "label": "Ends today", "days": 0}
        assert self._status(-10, 1) == {"kind": "ending", "label": "Ends in 1 day", "days": 1}
        assert self._status(-10, 60) == {"kind": "ending", "label": "Ends in 60 days", "days": 60}
        assert self._status(-10, 61) == {"kind": "in_force", "label": "In force", "days": None}
        assert self._status(-10, -1) == {"kind": "ended", "label": "Ended", "days": None}

    def test_the_window_is_60_days(self):
        assert ENDING_SOON_DAYS == 60

    def test_each_filter_matches_its_kinds(self):
        kinds = {"not_ended": {"upcoming", "in_force", "ending"}, "in_force": {"in_force", "ending"},
                 "ending": {"ending"}, "upcoming": {"upcoming"}, "ended": {"ended"},
                 "all": {"upcoming", "in_force", "ending", "ended"}}
        assert set(kinds) == set(STATUS_FILTERS)
        offsets = (-400, -61, -60, -2, -1, 0, 1, 2, 59, 60, 61, 62, 400)
        periods = [(TODAY + timedelta(days=a), TODAY + timedelta(days=b)) for a in offsets for b in offsets if b >= a]
        ops = {"<=": lambda x, y: x <= y, ">=": lambda x, y: x >= y, "<": lambda x, y: x < y,
               ">": lambda x, y: x > y}
        for status in STATUS_FILTERS:
            bounds = status_bounds(status, TODAY)
            for from_date, to_date in periods:
                row = {"from_date": from_date, "to_date": to_date}
                matched = all(ops[op](row[column], value) for column, op, value in bounds)
                assert matched == (contract_status(from_date, to_date, TODAY)["kind"] in kinds[status]), (
                    status, from_date, to_date)

    def test_order(self):
        assert newest_end_first("ended") is True
        assert newest_end_first("not_ended") is False
        assert newest_end_first("all") is False


# ---------------------------------------------------------------------------
# The machines a contract covers (S081 § 5.1, § 5.3, § 8.2)
# ---------------------------------------------------------------------------

class TestLine:

    def test_the_machine_is_required_on_a_create(self):
        assert validate_line({}, True)[1] == [{"field": "equipment_id", "message": "Choose a machine."}]
        for bad in (True, "5", 0, -1, None, 1.0):
            assert validate_line({"equipment_id": bad}, True)[1] == [
                {"field": "equipment_id", "message": "Choose a machine."}], bad
        assert validate_line({"equipment_id": 5, "other": 1}, True) == ({"equipment_id": 5}, [])

    def test_the_machine_is_ignored_on_a_put(self):
        assert validate_line({"equipment_id": "x", "price": "10"}, False) == ({"price": Decimal("10")}, [])
        assert validate_line({}, False) == ({}, [])

    def test_a_price_error_names_the_price(self):
        assert validate_line({"equipment_id": 5, "price": "9,809"}, True)[1] == [
            {"field": "price", "message": PRICE_FORMAT}]


class TestPrice:

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_empty_is_not_entered(self, raw):
        assert parse_price(raw) is None

    @pytest.mark.parametrize("raw, value", [
        (9809, "9809"), ("9809", "9809"), (" 9809.5 ", "9809.5"), ("9809.50", "9809.50"), (0, "0"),
        ("0", "0"), ("99999999.99", "99999999.99"),
    ])
    def test_valid_prices(self, raw, value):
        parsed = parse_price(raw)
        assert isinstance(parsed, Decimal) and parsed == Decimal(value)

    @pytest.mark.parametrize("raw", [9809.5, True, False, -1, "-1", "9809.505", "9,809", "₹9809", "9809.",
                                     ".5", "1e3", "٣", [], {}])
    def test_refused_with_the_format_text(self, raw):
        with pytest.raises(ValueError, match="^Enter the price in rupees, before GST, e.g. 9809 or 9809.50.$"):
            parse_price(raw)

    @pytest.mark.parametrize("raw", ["100000000", 100000000, "99999999.999"])
    def test_too_large(self, raw):
        message = PRICE_TOO_LARGE if raw != "99999999.999" else PRICE_FORMAT
        with pytest.raises(ValueError) as refused:
            parse_price(raw)
        assert str(refused.value) == message

    def test_the_limit_is_the_column_s(self):
        assert PRICE_MAX == Decimal("99999999.99")
        assert PRICE_TOO_LARGE == "Price: at most 9,99,99,999.99."


class TestEventText:

    @pytest.mark.parametrize("contract_type, short", [
        ("amc", "AMC"), ("cmc", "CMC"), ("warranty", "Warranty"), ("on_call", "On call")])
    def test_each_type(self, contract_type, short):
        contract = {"title": "Atlas Copco AMC 2026–27", "contract_type": contract_type,
                    "from_date": date(2026, 4, 1), "to_date": date(2027, 3, 31)}
        assert event_text(contract) == f"Atlas Copco AMC 2026–27 ({short}, 01-04-2026 to 31-03-2027)"

    def test_every_type_has_a_short_name(self):
        assert set(TYPE_SHORT) == set(CONTRACT_TYPES)

    def test_the_longest_fits_the_history_column(self):
        contract = {"title": "T" * TITLE_MAX, "contract_type": "warranty",
                    "from_date": date(2026, 4, 1), "to_date": date(2027, 3, 31)}
        assert len(event_text(contract)) == 137 <= 200   # equipment_events.new_value VARCHAR(200)

    def test_the_line_gate_is_the_cost_key(self):
        assert LINE_GATED_FIELDS == {"price": "contract:read_senior"}


# ---------------------------------------------------------------------------
# S082: the Under contract card and the list's Contract filter (S082 § 5.1, § 5.4, § 8.2)
# ---------------------------------------------------------------------------

NODE = {"id": 30, "parent_id": 20, "gp_id": 10}


def _row(contract_id, on_id, from_offset=-30, to_offset=300):
    return {"id": contract_id, "equipment_id": on_id,
            "from_date": TODAY + timedelta(days=from_offset), "to_date": TODAY + timedelta(days=to_offset)}


def _shown(rows, node=NODE):
    return [(item["row"]["id"], item["via_id"]) for item in card_items(rows, node, TODAY)]


class TestCardItems:

    def test_the_line_nearest_the_node_wins(self):
        assert _shown([_row(1, 20), _row(1, 30), _row(1, 10)]) == [(1, None)]
        assert _shown([_row(1, 10), _row(1, 20)]) == [(1, 20)]

    def test_on_the_grandparent_only(self):
        assert _shown([_row(1, 10)]) == [(1, 10)]

    def test_a_machine_has_no_ancestors(self):
        assert _shown([_row(1, 10)], {"id": 10, "parent_id": None, "gp_id": None}) == [(1, None)]

    def test_a_row_on_another_node_is_ignored(self):
        assert _shown([_row(1, 99)]) == []

    def test_the_ended_window(self):
        assert CARD_ENDED_DAYS == 90
        assert _shown([_row(1, 30, -400, -CARD_ENDED_DAYS)]) == [(1, None)]
        assert _shown([_row(1, 30, -400, -CARD_ENDED_DAYS - 1)]) == []

    def test_a_contract_that_starts_later_is_not_shown(self):
        assert _shown([_row(1, 30, 1, 300)]) == []
        assert _shown([_row(1, 30, 0, 300)]) == [(1, None)]

    def test_the_order(self):
        rows = [_row(5, 30, -400, -10), _row(4, 30, to_offset=200), _row(3, 30, to_offset=100),
                _row(2, 30, to_offset=100), _row(6, 30, -400, -50), _row(7, 30, -400, -10), _row(8, 30, to_offset=0)]
        assert [contract_id for contract_id, _ in _shown(rows)] == [8, 2, 3, 4, 5, 7, 6]


class TestCoveredSql:

    @pytest.mark.parametrize("site_ids", [[7], [7, 8, 9]])
    def test_under_and_not_under(self, site_ids):
        marks_ = ", ".join(["%s"] * len(site_ids))
        exists = ("EXISTS (SELECT 1 FROM contract_equipment ce JOIN contracts ct ON ct.id = ce.contract_id"
                  " WHERE ce.equipment_id IN (e.id, e.parent_id, p.parent_id) AND ct.active = 1"
                  f" AND ct.from_date <= %s AND ct.to_date >= %s AND ct.site_id IN ({marks_}))")
        assert covered_sql("under", site_ids, TODAY) == (exists, [TODAY, TODAY, *site_ids])
        assert covered_sql("not_under", site_ids, TODAY) == (f"NOT {exists}", [TODAY, TODAY, *site_ids])

    def test_no_site(self):
        assert covered_sql("under", [], TODAY) == ("0 = 1", [])
        assert covered_sql("not_under", [], TODAY) == ("1 = 1", [])

    def test_the_filters(self):
        assert COVERAGE_FILTERS == ("under", "not_under")


# ---------------------------------------------------------------------------
# Renewal (S085 § 5.2-§ 5.5, § 8.2)
# ---------------------------------------------------------------------------

def _d(text):
    """DD-MM-YYYY -> date, so the examples read as the brief writes them."""
    day, month, year = (int(part) for part in text.split("-"))
    return date(year, month, day)


class TestRenewal:

    @pytest.mark.parametrize("old, new", [
        (("01-04-2026", "31-03-2027"), ("01-04-2027", "31-03-2028")),   # one year
        (("15-01-2026", "14-07-2026"), ("15-07-2026", "14-01-2027")),   # six months
        (("01-03-2027", "29-02-2028"), ("01-03-2028", "28-02-2029")),   # a leap year ends
        (("01-04-2024", "31-03-2029"), ("01-04-2029", "31-03-2034")),   # five years
    ])
    def test_renewal_period_whole_months(self, old, new):
        assert renewal_period(_d(old[0]), _d(old[1])) == (_d(new[0]), _d(new[1]))

    @pytest.mark.parametrize("old, new", [
        (("10-04-2026", "31-03-2027"), ("01-04-2027", "21-03-2028")),
        (("05-05-2026", "05-05-2026"), ("06-05-2026", "06-05-2026")),   # one day
        # A leap-day start is not whole months: day 1 of 01-03-2025 is not 29 (BR1-07), so 366 days
        (("29-02-2024", "28-02-2025"), ("01-03-2025", "01-03-2026")),
    ])
    def test_renewal_period_not_whole_months(self, old, new):
        assert renewal_period(_d(old[0]), _d(old[1])) == (_d(new[0]), _d(new[1]))

    def test_renewal_period_past_2099(self):
        assert renewal_period(_d("01-01-2099"), _d("31-12-2099")) == (None, None)
        assert renewal_period(_d("01-01-2098"), _d("31-12-2098")) == (_d("01-01-2099"), _d("31-12-2099"))

    def test_add_months_keeps_the_month_end(self):
        assert _add_months(_d("31-01-2027"), 1) == _d("28-02-2027")
        assert _add_months(_d("31-01-2028"), 1) == _d("29-02-2028")
        assert _add_months(_d("15-11-2027"), 3) == _d("15-02-2028")

    def test_renewal_lines(self):
        def line(equipment_id, code, lifecycle="in_service", at_site=True, site_code="SMTW"):
            return {"equipment_id": equipment_id, "code": code, "lifecycle": lifecycle,
                    "at_contract_site": at_site, "site_code": site_code}
        copied, skipped = renewal_lines([
            line(1, "CMP001"), line(2, "CMP002", "standby"), line(3, "CMP003", "out_of_use"),
            line(4, "CMP004", "scrapped"), line(5, "CMP005", at_site=False, site_code="BRICKS"),
            line(6, "CMP006", "scrapped", at_site=False, site_code="BRICKS"),
        ])
        assert copied == [{"equipment_id": 1, "code": "CMP001"}, {"equipment_id": 2, "code": "CMP002"},
                          {"equipment_id": 3, "code": "CMP003"}]
        assert skipped == [{"equipment_id": 4, "code": "CMP004", "reason": "scrapped"},
                           {"equipment_id": 5, "code": "CMP005", "reason": "now at BRICKS"},
                           {"equipment_id": 6, "code": "CMP006", "reason": "scrapped"}]
        assert renewal_lines([]) == ([], [])

    def test_validate_renewal(self):
        body = {key: value for key, value in VALID.items() if key != "site_id"}
        clean, errors = validate_renewal(body, False)   # creating is ignored: always a create
        assert errors == [] and "site_id" not in clean and clean["title"] == VALID["title"]
        clean, errors = validate_renewal({**body, "site_id": 99}, True)
        assert errors == [] and "site_id" not in clean
        assert validate_renewal({**body, "title": ""}, True)[1] == [{"field": "title", "message": "Enter a title."}]
        clean, errors = validate_renewal({**body, "active": 0, "renewal_of_id": 5}, True)
        assert errors == [] and "active" not in clean and "renewal_of_id" not in clean
        # A create's required fields stay required
        assert [e["field"] for e in validate_renewal({}, True)[1]] == [
            "vendor_id", "contract_type", "title", "from_date", "to_date"]

    def test_the_messages(self):
        assert RENEW_INACTIVE == "This contract is inactive. Set it active in Masters › Contracts, then renew it."
        assert renew_site_inactive("SMTW") == (
            "SMTW is inactive. Set it active in Masters › Sites, then renew the contract.")
        assert already_renewed("Atlas Copco AMC 2027–28") == (
            "This contract is already renewed: Atlas Copco AMC 2027–28. Open that contract to change it.")
        assert RENEWAL_RACE == "This contract is already renewed. Reload the page to see the renewal."
