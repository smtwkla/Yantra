"""PM scheduling core — the pure rules (docs/steps/S095-pm-schedule-core/1-brief.md § 5, § 8.1; R03.1): when a
plan's next job is due (calendar, meter, whichever first), how an open job stands today, and whether a done job was
on time.  Each worked example of § 5.6 is a test (E1-E22), plus T1-T10 of § 8.1.  No database, no clock."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from pm_schedule_core import (
    BEFORE_USE, BOTH, CALENDAR, CALENDAR_UNITS, DAY, DUE, KINDS, LATE, METER, MIN_WINDOW_DAYS, MONTH, NOT_YET,
    ON_TIME, OVERDUE, UPCOMING, UPCOMING_MAX_DAYS, WEEK, WINDOW_DIVISOR, YEAR, Due, Standing, add_interval,
    job_state, next_due, timeliness, upcoming_days, window_days,
)

CREATED = date(2026, 10, 1)


def _d(text):
    """A DD-MM-YYYY date."""
    day, month, year = (int(part) for part in text.split("-"))
    return date(year, month, day)


def _plan(trigger_kind, **fields):
    plan = {"trigger_kind": trigger_kind, "calendar_every": None, "calendar_unit": None, "meter_type_id": None,
            "meter_every": None, "last_done_on": None, "last_done_meter": None, "created_on": CREATED}
    plan.update(fields)
    return plan


def _cal(every, unit, **fields):
    return _plan(CALENDAR, calendar_every=every, calendar_unit=unit, **fields)


def _met(every, **fields):
    return _plan(METER, meter_type_id=7, meter_every=Decimal(every), **fields)


def _both(every, unit, meter_every, **fields):
    return _plan(BOTH, calendar_every=every, calendar_unit=unit, meter_type_id=7, meter_every=Decimal(meter_every),
                 **fields)


def _job(done_on, done_meter=None):
    return {"done_on": _d(done_on), "done_meter": None if done_meter is None else Decimal(done_meter)}


def _state(due, reading, today):
    """``job_state`` -> ``(state, trigger)``."""
    standing = job_state(due, None if reading is None else Decimal(reading), _d(today))
    return standing.state, standing.trigger


class TestConstants:
    def test_the_vocabulary_of_s096(self):
        """D7, Q5: S096's ENUM and validation import these strings."""
        assert KINDS == ("calendar", "meter", "both", "before_use")
        assert CALENDAR_UNITS == ("day", "week", "month", "year")
        assert (NOT_YET, UPCOMING, DUE, OVERDUE) == ("not_yet", "upcoming", "due", "overdue")
        assert (ON_TIME, LATE) == ("on_time", "late")
        assert (WINDOW_DIVISOR, MIN_WINDOW_DAYS, UPCOMING_MAX_DAYS) == (10, 1, 7)


# ---------------------------------------------------------------------------------------------------------------
# § 5.6 worked examples, calendar plans: E1-E9.
# Each row: plan, last job done on, the due date, the interval in days, grace, up, [(today, state)],
# [(done on, timeliness)].
CALENDAR_EXAMPLES = [
    pytest.param(
        (1, MONTH), "31-01-2027", "28-02-2027", 28, 2, 2,
        [("25-02-2027", NOT_YET), ("26-02-2027", UPCOMING), ("28-02-2027", DUE), ("02-03-2027", DUE),
         ("03-03-2027", OVERDUE)],
        [("02-03-2027", ON_TIME), ("03-03-2027", LATE)], id="E1"),
    pytest.param(
        (1, MONTH), "31-01-2028", "29-02-2028", 29, 2, 2,
        [("02-03-2028", DUE), ("03-03-2028", OVERDUE)], [], id="E2"),
    pytest.param(
        (1, MONTH), "15-03-2027", "15-04-2027", 31, 3, 3,
        [("11-04-2027", NOT_YET), ("12-04-2027", UPCOMING), ("18-04-2027", DUE), ("19-04-2027", OVERDUE)], [],
        id="E3"),
    pytest.param(
        (3, MONTH), "30-11-2026", "28-02-2027", 90, 9, 7,
        [("21-02-2027", UPCOMING), ("09-03-2027", DUE), ("10-03-2027", OVERDUE)], [], id="E4"),
    pytest.param((1, MONTH), "28-02-2027", "28-03-2027", 28, 2, 2, [], [], id="E5"),
    pytest.param(
        (1, WEEK), "02-11-2026", "09-11-2026", 7, 1, 1,
        [("07-11-2026", NOT_YET), ("08-11-2026", UPCOMING), ("10-11-2026", DUE), ("11-11-2026", OVERDUE)], [],
        id="E6"),
    pytest.param(
        (1, DAY), "01-11-2026", "02-11-2026", 1, 1, 1,
        [("01-11-2026", UPCOMING), ("03-11-2026", DUE), ("04-11-2026", OVERDUE)], [], id="E7"),
    pytest.param(
        (1, YEAR), "10-01-2027", "10-01-2028", 365, 36, 7,
        [("02-01-2028", NOT_YET), ("03-01-2028", UPCOMING), ("15-02-2028", DUE), ("16-02-2028", OVERDUE)], [],
        id="E8"),
    pytest.param((1, YEAR), "29-02-2028", "28-02-2029", 365, 36, 7, [], [], id="E9"),
]


@pytest.mark.parametrize("every_unit, done_on, due_on, interval, grace, up, states, judged", CALENDAR_EXAMPLES)
def test_calendar_examples(every_unit, done_on, due_on, interval, grace, up, states, judged):
    base = _d(done_on)
    due = next_due(_cal(*every_unit), last_job=_job(done_on))
    assert due == Due(due_on=_d(due_on), due_meter=None, grace_days=grace, upcoming_days=up, meter_window=None,
                      rescheduled=False, before_use=False)
    assert (due.due_on - base).days == interval
    for today, state in states:
        expected_trigger = None if state == NOT_YET else CALENDAR
        assert job_state(due, None, _d(today)) == Standing(state, expected_trigger, False), today
    for done, result in judged:
        assert timeliness(due, _d(done), None) == result, done


# § 5.6 worked examples, meter plans: E10, E11.
def test_e10_meter_every_250_hours():
    due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
    assert due == Due(due_on=None, due_meter=Decimal("12290"), grace_days=None, upcoming_days=None,
                      meter_window=Decimal("25"), rescheduled=False, before_use=False)
    today = "05-11-2026"
    assert _state(due, "12264.9", today) == (NOT_YET, None)
    assert _state(due, "12265", today) == (UPCOMING, METER)
    assert _state(due, "12290", today) == (DUE, METER)
    assert _state(due, "12315", today) == (DUE, METER)
    assert _state(due, "12315.1", today) == (OVERDUE, METER)
    assert timeliness(due, _d(today), Decimal("12315")) == ON_TIME
    assert timeliness(due, _d(today), Decimal("12316")) == LATE


def test_e11_oil_change_every_5000_hours():
    """Q1.2: done at 5,040 h, every 5,000 h -> next due at 10,040 h."""
    due = next_due(_met(5000), last_job=_job("01-11-2026", "5040"))
    assert due.due_meter == Decimal("10040")
    assert due.meter_window == Decimal("500")


# § 5.6 E12: the standby genset, 1 month and 250 h, whichever first.
@pytest.fixture
def genset_due():
    return next_due(_both(1, MONTH, 250), last_job=_job("01-11-2026", "3000"))


def test_e12_next_due(genset_due):
    assert genset_due == Due(due_on=_d("01-12-2026"), due_meter=Decimal("3250"), grace_days=3, upcoming_days=3,
                             meter_window=Decimal("25"), rescheduled=False, before_use=False)


@pytest.mark.parametrize("today, reading, expected", [
    ("20-11-2026", "3260", (DUE, METER)),
    ("05-12-2026", "3100", (OVERDUE, CALENDAR)),
    ("01-12-2026", "3250", (DUE, CALENDAR)),
    ("28-11-2026", "3100", (UPCOMING, CALENDAR)),
])
def test_e12_job_state(genset_due, today, reading, expected):
    assert _state(genset_due, reading, today) == expected


def test_e12_timeliness(genset_due):
    assert timeliness(genset_due, _d("03-12-2026"), Decimal("3120")) == ON_TIME
    assert timeliness(genset_due, _d("03-12-2026"), Decimal("3280")) == LATE


# § 5.6 E13-E15: the first job, from the seed or the plan's creation.
def test_e13_first_job_from_the_seed_date():
    due = next_due(_cal(1, MONTH, last_done_on=_d("20-10-2026"), created_on=_d("01-11-2026")))
    assert due.due_on == _d("20-11-2026")


def test_e14_first_job_from_the_seed_value():
    due = next_due(_met(250, last_done_meter=Decimal("11800")))
    assert due.due_meter == Decimal("12050")


def test_e15_first_job_from_creation_and_start_meter():
    due = next_due(_both(1, MONTH, 250, created_on=_d("01-11-2026")), start_meter=Decimal("12000"))
    assert (due.due_on, due.due_meter) == (_d("01-12-2026"), Decimal("12250"))


# § 5.6 E16-E18: no reading yet.
def test_e16_meter_plan_without_any_reading():
    due = next_due(_met(250))
    assert due.due_meter is None
    assert due.meter_window == Decimal("25")
    assert job_state(due, None, _d("01-12-2026")) == Standing(NOT_YET, None, True)


def test_e17_calendar_works_without_a_reading():
    due = next_due(_both(1, MONTH, 250, created_on=_d("01-11-2026")))
    assert (due.due_on, due.due_meter) == (_d("01-12-2026"), None)
    assert job_state(due, None, _d("02-12-2026")) == Standing(DUE, CALENDAR, True)
    assert job_state(due, None, _d("20-11-2026")) == Standing(NOT_YET, None, True)


def test_e18_base_value_but_no_reading():
    due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
    assert due.due_meter == Decimal("12290")
    assert job_state(due, None, _d("01-12-2026")) == Standing(NOT_YET, None, True)


# § 5.6 E19: before use (R03.13).
def test_e19_before_use():
    due = next_due(_plan(BEFORE_USE))
    assert due == Due(due_on=None, due_meter=None, grace_days=None, upcoming_days=None, meter_window=None,
                      rescheduled=False, before_use=True)
    assert job_state(due, Decimal("99999"), _d("01-01-2030")) == Standing(NOT_YET, None, False)
    assert timeliness(due, _d("01-01-2030"), Decimal("99999")) is None


# § 5.6 E20: E1 rescheduled (R03.9, Q9.1, D5).
def test_e20_override_keeps_the_computed_windows():
    due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"), override={"due_on": _d("10-03-2027"),
                                                                         "due_meter": None})
    assert due == Due(due_on=_d("10-03-2027"), due_meter=None, grace_days=2, upcoming_days=2, meter_window=None,
                      rescheduled=True, before_use=False)
    assert job_state(due, None, _d("12-03-2027")).state == DUE
    assert job_state(due, None, _d("13-03-2027")).state == OVERDUE
    assert timeliness(due, _d("12-03-2027"), None) == ON_TIME


# § 5.6 E21, E22.
def test_e21_a_done_job_wins_over_the_seed():
    due = next_due(_cal(1, MONTH, last_done_on=_d("05-01-2027")), last_job=_job("20-02-2027"))
    assert due.due_on == _d("20-03-2027")


def test_e22_done_early_is_on_time():
    due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"))
    assert timeliness(due, _d("20-02-2027"), None) == ON_TIME


# ---------------------------------------------------------------------------------------------------------------
class TestAddInterval:
    """T1."""

    @pytest.mark.parametrize("day, every, unit, expected", [
        ("01-11-2026", 3, DAY, "04-11-2026"),
        ("28-12-2026", 5, DAY, "02-01-2027"),
        ("01-11-2026", 2, WEEK, "15-11-2026"),
        ("31-01-2027", 1, MONTH, "28-02-2027"),
        ("31-01-2028", 1, MONTH, "29-02-2028"),
        ("31-03-2027", 1, MONTH, "30-04-2027"),
        ("15-11-2026", 3, MONTH, "15-02-2027"),
        ("10-01-2027", 1, YEAR, "10-01-2028"),
        ("29-02-2028", 1, YEAR, "28-02-2029"),
        ("29-02-2028", 4, YEAR, "29-02-2032"),
    ])
    def test_units(self, day, every, unit, expected):
        assert add_interval(_d(day), every, unit) == _d(expected)

    def test_twelve_months_is_one_year(self):
        for day in ("29-02-2028", "31-12-2026", "15-06-2027"):
            assert add_interval(_d(day), 12, MONTH) == add_interval(_d(day), 1, YEAR)

    def test_no_snap_back(self):
        """Floating months: done 28-02 -> due 28-03, not 31-03 (E5)."""
        assert add_interval(_d("28-02-2027"), 1, MONTH) == _d("28-03-2027")

    @pytest.mark.parametrize("every, unit", [(0, MONTH), (-1, DAY), (1, "fortnight"), (1, None)])
    def test_refusals(self, every, unit):
        with pytest.raises(ValueError):
            add_interval(_d("01-11-2026"), every, unit)


class TestWindows:
    """T2, D3: 10 % rounded down, at least 1 day; upcoming the shorter of 7 days and that."""

    @pytest.mark.parametrize("interval, grace, up", [
        (1, 1, 1), (7, 1, 1), (9, 1, 1), (10, 1, 1), (28, 2, 2), (30, 3, 3), (31, 3, 3), (69, 6, 6),
        (70, 7, 7), (90, 9, 7), (365, 36, 7), (366, 36, 7),
    ])
    def test_values(self, interval, grace, up):
        assert window_days(interval) == grace
        assert upcoming_days(interval) == up

    @pytest.mark.parametrize("function", [window_days, upcoming_days])
    def test_zero_days(self, function):
        with pytest.raises(ValueError):
            function(0)


class TestBase:
    """T3, § 5.2."""

    def test_job_over_seed(self):
        plan = _both(1, MONTH, 250, last_done_on=_d("05-01-2027"), last_done_meter=Decimal("1000"))
        due = next_due(plan, last_job=_job("20-02-2027", "1500"), start_meter=Decimal("900"))
        assert (due.due_on, due.due_meter) == (_d("20-03-2027"), Decimal("1750"))

    def test_seed_date_without_value_takes_start_meter(self):
        plan = _both(1, MONTH, 250, last_done_on=_d("20-10-2026"), created_on=_d("01-11-2026"))
        due = next_due(plan, start_meter=Decimal("11900"))
        assert (due.due_on, due.due_meter) == (_d("20-11-2026"), Decimal("12150"))

    def test_seed_value_without_date_takes_created_on(self):
        plan = _both(1, MONTH, 250, last_done_meter=Decimal("11800"), created_on=_d("01-11-2026"))
        due = next_due(plan, start_meter=Decimal("11900"))
        assert (due.due_on, due.due_meter) == (_d("01-12-2026"), Decimal("12050"))

    def test_job_without_meter_value_gives_no_due_meter(self):
        """The job wins also over a seed value and the start meter."""
        plan = _both(1, MONTH, 250, last_done_meter=Decimal("11800"))
        due = next_due(plan, last_job=_job("01-11-2026"), start_meter=Decimal("11900"))
        assert (due.due_on, due.due_meter) == (_d("01-12-2026"), None)

    def test_int_meter_values_give_decimal(self):
        plan = _plan(METER, meter_type_id=7, meter_every=250, last_done_meter=11800)
        due = next_due(plan)
        assert (due.due_meter, due.meter_window) == (Decimal("12050"), Decimal("25"))
        assert isinstance(due.due_meter, Decimal) and isinstance(due.meter_window, Decimal)

    def test_meter_window_is_exact(self):
        assert next_due(_met("0.5")).meter_window == Decimal("0.05")


class TestBoundaries:
    """T4: every boundary of § 5.4 on both sides.  E4's due point (U 7, G 9 differ) and E10's."""

    def test_calendar(self):
        due = next_due(_cal(3, MONTH), last_job=_job("30-11-2026"))
        d, u, g = due.due_on, timedelta(days=due.upcoming_days), timedelta(days=due.grace_days)
        one = timedelta(days=1)
        cases = [(d - u - one, NOT_YET), (d - u, UPCOMING), (d - one, UPCOMING), (d, DUE), (d + g, DUE),
                 (d + g + one, OVERDUE)]
        for today, state in cases:
            assert job_state(due, None, today).state == state, today

    def test_meter(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
        m, w, tick = due.due_meter, due.meter_window, Decimal("0.1")
        cases = [(m - w - tick, NOT_YET), (m - w, UPCOMING), (m - tick, UPCOMING), (m, DUE), (m + w, DUE),
                 (m + w + tick, OVERDUE)]
        for reading, state in cases:
            assert job_state(due, reading, _d("01-11-2026")).state == state, reading


class TestWhicheverFirst:
    """T5, D2: the furthest trigger's state; a tie goes to the calendar."""

    @pytest.mark.parametrize("today, reading, expected", [
        ("05-12-2026", "3260", (OVERDUE, CALENDAR)),    # calendar overdue, meter due
        ("02-12-2026", "3300", (OVERDUE, METER)),       # calendar due, meter overdue
        ("28-11-2026", "3240", (UPCOMING, CALENDAR)),   # both upcoming: tie
        ("03-12-2026", "3270", (DUE, CALENDAR)),        # both due: tie
        ("05-12-2026", "3300", (OVERDUE, CALENDAR)),    # both overdue: tie
        ("10-11-2026", "3100", (NOT_YET, None)),        # both not yet: no trigger
        ("10-11-2026", "3230", (UPCOMING, METER)),      # only the meter moved
    ])
    def test_furthest(self, genset_due, today, reading, expected):
        assert _state(genset_due, reading, today) == expected

    def test_reading_without_meter_trigger_is_ignored(self):
        due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"))
        assert job_state(due, Decimal("99999"), _d("01-02-2027")) == Standing(NOT_YET, None, False)


class TestTimeliness:
    """T6, D2, § 5.5."""

    def test_calendar_window_edges(self):
        due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"))
        last_day = due.due_on + timedelta(days=due.grace_days)
        assert timeliness(due, last_day, None) == ON_TIME
        assert timeliness(due, last_day + timedelta(days=1), None) == LATE

    def test_meter_window_edges(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
        last_value = due.due_meter + due.meter_window
        assert timeliness(due, _d("01-01-2030"), last_value) == ON_TIME
        assert timeliness(due, _d("01-01-2030"), last_value + Decimal("0.1")) == LATE

    def test_no_done_meter_judges_by_calendar_only(self, genset_due):
        assert timeliness(genset_due, _d("04-12-2026"), None) == ON_TIME
        assert timeliness(genset_due, _d("05-12-2026"), None) == LATE

    def test_no_due_meter_cannot_make_late(self):
        due = next_due(_met(250))
        assert timeliness(due, _d("01-01-2030"), Decimal("99999")) == ON_TIME

    def test_calendar_late_with_meter_on_time(self, genset_due):
        assert timeliness(genset_due, _d("05-12-2026"), Decimal("3100")) == LATE

    def test_before_use_is_not_judged(self):
        assert timeliness(next_due(_plan(BEFORE_USE)), _d("01-11-2026"), None) is None


class TestOverride:
    """T7, § 5.3, D5."""

    def test_meter_only(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"),
                       override={"due_on": None, "due_meter": Decimal("12400")})
        assert (due.due_meter, due.meter_window, due.rescheduled) == (Decimal("12400"), Decimal("25"), True)

    def test_both_values(self):
        due = next_due(_both(1, MONTH, 250), last_job=_job("01-11-2026", "3000"),
                       override={"due_on": _d("10-12-2026"), "due_meter": Decimal("3400")})
        assert due == Due(due_on=_d("10-12-2026"), due_meter=Decimal("3400"), grace_days=3, upcoming_days=3,
                          meter_window=Decimal("25"), rescheduled=True, before_use=False)

    def test_one_value_keeps_the_other_computed(self):
        due = next_due(_both(1, MONTH, 250), last_job=_job("01-11-2026", "3000"),
                       override={"due_on": _d("10-12-2026"), "due_meter": None})
        assert (due.due_on, due.due_meter, due.rescheduled) == (_d("10-12-2026"), Decimal("3250"), True)

    def test_nothing_set_is_not_rescheduled(self):
        due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"), override={"due_on": None, "due_meter": None})
        assert (due.due_on, due.rescheduled) == (_d("28-02-2027"), False)

    def test_meter_override_without_a_base_value(self):
        """BR1-09: the trigger exists, so the override is allowed and judged once a reading exists."""
        due = next_due(_met(250), override={"due_on": None, "due_meter": Decimal("12290")})
        assert (due.due_meter, due.rescheduled) == (Decimal("12290"), True)
        assert job_state(due, None, _d("01-11-2026")) == Standing(NOT_YET, None, True)
        assert job_state(due, Decimal("12300"), _d("01-11-2026")) == Standing(DUE, METER, False)

    def test_meter_override_on_a_calendar_plan(self):
        with pytest.raises(ValueError, match="due_meter"):
            next_due(_cal(1, MONTH), override={"due_on": None, "due_meter": Decimal("100")})

    def test_date_override_on_a_meter_plan(self):
        with pytest.raises(ValueError, match="due_on"):
            next_due(_met(250), override={"due_on": _d("01-12-2026"), "due_meter": None})

    @pytest.mark.parametrize("override", [{"due_on": _d("01-12-2026"), "due_meter": None}, {}])
    def test_override_on_before_use(self, override):
        with pytest.raises(ValueError, match="override"):
            next_due(_plan(BEFORE_USE), override=override)


class TestBadInput:
    """T8, D8: a shell bug raises, naming the key."""

    @pytest.mark.parametrize("plan, key", [
        (_plan("fortnightly", calendar_every=1, calendar_unit=MONTH), "trigger_kind"),
        ({"kind": "pm", "calendar_every": 1, "calendar_unit": MONTH, "created_on": CREATED}, "trigger_kind"),
        (_plan(CALENDAR, calendar_unit=MONTH), "calendar_every"),
        (_plan(CALENDAR, calendar_every=1), "calendar_unit"),
        (_cal(1, "fortnight"), "calendar_unit"),
        (_plan(METER, meter_type_id=7, meter_every=Decimal(250), calendar_unit=MONTH), "calendar_unit"),
        (_plan(METER, meter_type_id=7, meter_every=Decimal(250), calendar_every=1), "calendar_every"),
        (_plan(METER, meter_type_id=7), "meter_every"),
        (_plan(METER, meter_every=Decimal(250)), "meter_type_id"),
        (_plan(CALENDAR, calendar_every=1, calendar_unit=MONTH, meter_every=Decimal(250)), "meter_every"),
        (_plan(CALENDAR, calendar_every=1, calendar_unit=MONTH, meter_type_id=7), "meter_type_id"),
        (_met(0), "meter_every"),
        (_met(-250), "meter_every"),
        (_cal(0, MONTH), "calendar_every"),
        (_cal(-1, MONTH), "calendar_every"),
        (_cal(1, MONTH, created_on=None), "created_on"),
        (_met(250, last_done_meter=Decimal("-1")), "last_done_meter"),
    ])
    def test_value_errors(self, plan, key):
        with pytest.raises(ValueError, match=key):
            next_due(plan)

    def test_missing_created_on(self):
        plan = _cal(1, MONTH)
        del plan["created_on"]
        with pytest.raises(ValueError, match="created_on"):
            next_due(plan)

    def test_last_job_without_done_on(self):
        with pytest.raises(ValueError, match="done_on"):
            next_due(_cal(1, MONTH), last_job={"done_on": None, "done_meter": None})

    @pytest.mark.parametrize("every", [Decimal(1), 1.0, True])
    def test_calendar_every_type(self, every):
        with pytest.raises(TypeError, match="calendar_every"):
            next_due(_cal(every, MONTH))

    MOMENT = datetime(2026, 11, 1, 18, 30)

    def test_datetime_created_on(self):
        with pytest.raises(TypeError, match="created_on"):
            next_due(_cal(1, MONTH, created_on=self.MOMENT))

    def test_datetime_last_done_on(self):
        with pytest.raises(TypeError, match="last_done_on"):
            next_due(_cal(1, MONTH, last_done_on=self.MOMENT))

    def test_datetime_last_job_done_on(self):
        with pytest.raises(TypeError, match="done_on"):
            next_due(_cal(1, MONTH), last_job={"done_on": self.MOMENT, "done_meter": None})

    def test_datetime_override_due_on(self):
        with pytest.raises(TypeError, match="due_on"):
            next_due(_cal(1, MONTH), override={"due_on": self.MOMENT, "due_meter": None})

    def test_datetime_today(self):
        due = next_due(_cal(1, MONTH))
        with pytest.raises(TypeError, match="today"):
            job_state(due, None, self.MOMENT)

    def test_datetime_timeliness_done_on(self):
        due = next_due(_cal(1, MONTH))
        with pytest.raises(TypeError, match="done_on"):
            timeliness(due, self.MOMENT, None)

    def test_timeliness_done_on_required(self):
        due = next_due(_cal(1, MONTH))
        with pytest.raises(ValueError, match="done_on"):
            timeliness(due, None, None)

    @pytest.mark.parametrize("bad", [250.0, True, "250"])
    def test_meter_every_type(self, bad):
        with pytest.raises(TypeError, match="meter_every"):
            next_due(_plan(METER, meter_type_id=7, meter_every=bad))

    @pytest.mark.parametrize("bad", [11800.0, True])
    def test_last_done_meter_type(self, bad):
        with pytest.raises(TypeError, match="last_done_meter"):
            next_due(_met(250, last_done_meter=bad))

    @pytest.mark.parametrize("bad", [12000.0, False])
    def test_start_meter_type(self, bad):
        with pytest.raises(TypeError, match="start_meter"):
            next_due(_met(250), start_meter=bad)

    def test_last_job_done_meter_type(self):
        with pytest.raises(TypeError, match="done_meter"):
            next_due(_met(250), last_job={"done_on": _d("01-11-2026"), "done_meter": 12040.0})

    def test_override_due_meter_type(self):
        with pytest.raises(TypeError, match="due_meter"):
            next_due(_met(250), override={"due_on": None, "due_meter": 12290.0})

    def test_reading_value_type(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
        with pytest.raises(TypeError, match="reading_value"):
            job_state(due, 12290.0, _d("01-11-2026"))

    def test_timeliness_done_meter_type(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
        with pytest.raises(TypeError, match="done_meter"):
            timeliness(due, _d("01-11-2026"), 12290.0)

    def test_extra_keys_are_ignored(self):
        plan = _cal(1, MONTH, id=12, kind="pm", title="Monthly greasing", node_id=4)
        assert next_due(plan, last_job=_job("31-01-2027")).due_on == _d("28-02-2027")

    def test_no_meter_plan_ignores_its_meter_values(self):
        """§ 5.1: ``last_done_meter`` is ignored for a plan with no meter."""
        due = next_due(_cal(1, MONTH, last_done_meter=11800.0), last_job=_job("31-01-2027"), start_meter=5.5)
        assert (due.due_on, due.due_meter) == (_d("28-02-2027"), None)


class TestAgreement:
    """T9, § 5.5: at the same date and meter value, LATE exactly when the state is OVERDUE."""

    @staticmethod
    def _check(due, days, readings):
        for day in days:
            for reading in readings:
                late = timeliness(due, day, reading) == LATE
                overdue = job_state(due, reading, day).state == OVERDUE
                assert late == overdue, (day, reading)

    @staticmethod
    def _days_around(due):
        start = due.due_on - timedelta(days=due.upcoming_days + 2)
        end = due.due_on + timedelta(days=due.grace_days + 2)
        return [start + timedelta(days=n) for n in range((end - start).days + 1)]

    @staticmethod
    def _readings_around(due):
        low = due.due_meter - due.meter_window - 2
        steps = int((2 * due.meter_window + 4) / Decimal("0.5")) + 1
        return [low + Decimal("0.5") * n for n in range(steps)]

    def test_e1(self):
        due = next_due(_cal(1, MONTH), last_job=_job("31-01-2027"))
        self._check(due, self._days_around(due), [None])

    def test_e10(self):
        due = next_due(_met(250), last_job=_job("01-11-2026", "12040"))
        self._check(due, [_d("01-11-2026")], self._readings_around(due) + [None])

    def test_e12(self, genset_due):
        self._check(genset_due, self._days_around(genset_due), self._readings_around(genset_due) + [None])


class TestBeforeUse:
    """T10: a before-use plan ignores the four trigger keys, set or not, valid or not."""

    @pytest.mark.parametrize("fields", [
        {},
        {"calendar_every": 1, "calendar_unit": MONTH, "meter_type_id": 7, "meter_every": Decimal(250)},
        {"calendar_every": 0, "calendar_unit": "fortnight", "meter_every": 250.0, "last_done_meter": 1.5},
    ])
    def test_ignores_trigger_keys(self, fields):
        due = next_due(_plan(BEFORE_USE, **fields), last_job=_job("01-11-2026", "3000"), start_meter=Decimal(5))
        assert due == Due(due_on=None, due_meter=None, grace_days=None, upcoming_days=None, meter_window=None,
                          rescheduled=False, before_use=True)
        assert job_state(due, Decimal("1"), _d("01-11-2030")) == Standing(NOT_YET, None, False)
        assert timeliness(due, _d("01-11-2030"), None) is None
