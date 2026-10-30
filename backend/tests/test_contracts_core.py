"""Vendor contracts — the pure rules (S080 § 5.1, § 5.3, § 8.2): the fields, the period, breakdown calls, the
status from the dates and the Status filter.  No database.  Phone values are obviously fake, never a real number."""

from datetime import date, timedelta

import pytest

from contracts_core import (
    CALLS_WITHOUT_TICK, ENDING_SOON_DAYS, FROM_AFTER_TO, STATUS_FILTERS, TO_BEFORE_FROM, VENDOR_MISSING,
    breakdown_calls_error, contract_status, newest_end_first, period_error, status_bounds, validate_contract,
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
