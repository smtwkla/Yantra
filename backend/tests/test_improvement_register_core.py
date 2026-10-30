"""The improvement register — pure figures (S076 § 8.1; no DB)."""

from datetime import date, datetime

import pytest

from improvement_register_core import (
    AGE_BANDS, OPEN_DISPLAY_STATES, PERIOD_BACKWARDS, PERIOD_TOO_LONG, age_band, age_days, closed_summary,
    default_period, open_summary, parse_period, period_bounds, worked_share,
)


class TestDefaultPeriod:

    @pytest.mark.parametrize("today, expected", [
        (date(2026, 10, 30), (date(2026, 10, 1), date(2026, 10, 31))),
        (date(2028, 2, 15), (date(2028, 2, 1), date(2028, 2, 29))),   # leap year
        (date(2026, 12, 31), (date(2026, 12, 1), date(2026, 12, 31))),
    ])
    def test_both_absent_is_today_s_month(self, today, expected):
        assert default_period(None, None, today) == expected

    def test_only_from_ends_with_its_month(self):
        assert default_period(date(2026, 3, 15), None, date(2026, 10, 30)) == (date(2026, 3, 15), date(2026, 3, 31))

    def test_only_to_starts_with_its_month(self):
        assert default_period(None, date(2026, 3, 15), date(2026, 10, 30)) == (date(2026, 3, 1), date(2026, 3, 15))

    def test_both_given_are_kept(self):
        assert default_period(date(2026, 1, 5), date(2026, 2, 6), date(2026, 10, 30)) == (
            date(2026, 1, 5), date(2026, 2, 6))


class TestParsePeriod:
    TODAY = date(2026, 10, 30)

    def test_from_after_to_is_refused_on_from(self):
        period, error = parse_period(date(2026, 10, 5), date(2026, 10, 4), self.TODAY)
        assert period is None and error == {"field": "from", "message": PERIOD_BACKWARDS}

    def test_366_days_both_counted_passes(self):
        period, error = parse_period(date(2028, 1, 1), date(2028, 12, 31), self.TODAY)   # a leap year: 366 days
        assert error is None and period == (date(2028, 1, 1), date(2028, 12, 31))

    def test_367_days_is_refused_on_to(self):
        period, error = parse_period(date(2027, 12, 31), date(2028, 12, 31), self.TODAY)
        assert period is None and error == {"field": "to", "message": PERIOD_TOO_LONG}

    def test_one_day_passes(self):
        period, error = parse_period(date(2026, 10, 5), date(2026, 10, 5), self.TODAY)
        assert error is None and period == (date(2026, 10, 5), date(2026, 10, 5))

    def test_a_future_period_passes(self):
        period, error = parse_period(date(2027, 1, 1), date(2027, 1, 31), self.TODAY)
        assert error is None and period == (date(2027, 1, 1), date(2027, 1, 31))

    def test_defaults_come_first(self):
        period, error = parse_period(None, None, self.TODAY)
        assert error is None and period == (date(2026, 10, 1), date(2026, 10, 31))


def test_period_bounds_october():
    assert period_bounds((date(2026, 10, 1), date(2026, 10, 31))) == (
        datetime(2026, 10, 1, 0, 0), datetime(2026, 11, 1, 0, 0))


class TestAge:
    TODAY = date(2026, 10, 30)

    def test_started_today_is_zero(self):
        assert age_days(datetime(2026, 10, 30, 8, 0), self.TODAY) == 0

    def test_counts_calendar_days(self):
        assert age_days(datetime(2026, 10, 29, 23, 59), self.TODAY) == 1

    @pytest.mark.parametrize("days, band", [
        (0, "0_30"), (30, "0_30"), (31, "31_90"), (90, "31_90"), (91, "91_180"), (180, "91_180"),
        (181, "over_180"), (400, "over_180"), (-3, "0_30"),
    ])
    def test_band_edges(self, days, band):
        assert age_band(days) == band


class TestOpenSummary:

    def test_empty_has_every_state_and_band(self):
        out = open_summary([])
        assert out["count"] == 0
        assert [row["state"] for row in out["by_state"]] == list(OPEN_DISPLAY_STATES)
        assert all(row["total"] == 0 and list(row["bands"]) == list(AGE_BANDS) and not any(row["bands"].values())
                   for row in out["by_state"])
        assert out["band_totals"] == dict.fromkeys(AGE_BANDS, 0)

    def test_several_states_and_bands(self):
        rows = [
            {"display_state": "analysing", "age_days": 2},
            {"display_state": "analysing", "age_days": 31},
            {"display_state": "watching", "age_days": 120},
            {"display_state": "ready_to_verify", "age_days": 200},
            {"display_state": "ready_to_verify", "age_days": 181},
        ]
        out = open_summary(rows)
        by_state = {row["state"]: row for row in out["by_state"]}
        assert out["count"] == 5
        assert by_state["analysing"]["bands"] == {"0_30": 1, "31_90": 1, "91_180": 0, "over_180": 0}
        assert by_state["analysing"]["total"] == 2
        assert by_state["actions_open"]["total"] == 0
        assert by_state["watching"]["bands"]["91_180"] == 1
        assert by_state["ready_to_verify"]["bands"]["over_180"] == 2   # its own row
        assert out["band_totals"] == {"0_30": 1, "31_90": 1, "91_180": 1, "over_180": 2}


class TestClosedSummary:

    @pytest.mark.parametrize("worked, not_worked, share", [(3, 1, 75), (1, 7, 13), (0, 0, None), (0, 2, 0), (2, 0, 100)])
    def test_worked_share(self, worked, not_worked, share):
        assert worked_share(worked, not_worked) == share

    def test_drops_are_counted_and_stay_out_of_the_share(self):
        rows = ([{"state": "closed_effective"}] * 3 + [{"state": "closed_not_effective"}]
                + [{"state": "dropped"}] * 4)
        assert closed_summary(rows) == {"it_worked": 3, "did_not_work": 1, "dropped": 4, "worked_share": 75}

    def test_only_drops_has_no_share(self):
        assert closed_summary([{"state": "dropped"}])["worked_share"] is None

    def test_empty(self):
        assert closed_summary([]) == {"it_worked": 0, "did_not_work": 0, "dropped": 0, "worked_share": None}
