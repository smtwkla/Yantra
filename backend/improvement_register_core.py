"""The improvement register — pure figures (docs/steps/S076-improvement-register/1-brief.md § 5; no DB).

The register is the maintenance input to the management review (ISO 9001 § 9.3.2 c 4, § 10.3):
what was started, what is open and how old, what is late, what worked.  This module holds the
period rules, the age bands, the state-by-age table and the share that worked.  improvements.py
(the shell) reads the rows, parses the dates and stores nothing.
"""

import calendar
from datetime import date, datetime, time, timedelta

from improvements_core import (
    ACTIONS_OPEN, ANALYSING, CLOSED_EFFECTIVE, CLOSED_NOT_EFFECTIVE, DROPPED, READY_TO_VERIFY, WATCHING,
)

REPORT_KEY = "report:read"

# The open rows of the count table, in the order of the page: the display states (S072 D1)
OPEN_DISPLAY_STATES = (ANALYSING, ACTIONS_OPEN, WATCHING, READY_TO_VERIFY)

# The age columns (D7): key, first and last day; the last band has no end
AGE_BANDS = ("0_30", "31_90", "91_180", "over_180")
_BAND_STARTS = (("over_180", 181), ("91_180", 91), ("31_90", 31))

PERIOD_MAX_DAYS = 366

PERIOD_BACKWARDS = "The start must be on or before the end"
PERIOD_TOO_LONG = "Choose a period of up to one year"


def _month_end(day):
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def default_period(from_date, to_date, today):
    """Fill the missing end (BR1-02): both absent -> today's month; only ``from`` -> the rest of
    its month; only ``to`` -> from the first of its month.  -> ``(from, to)``."""
    if from_date is None and to_date is None:
        return today.replace(day=1), _month_end(today)
    if to_date is None:
        return from_date, _month_end(from_date)
    if from_date is None:
        return to_date.replace(day=1), to_date
    return from_date, to_date


def parse_period(from_date, to_date, today):
    """The dates (or None) of the query -> ``((from, to), None)`` or ``(None, {field, message})``,
    after the defaults.  A future ``to`` is allowed (the default ends on the month's last day)."""
    start, end = default_period(from_date, to_date, today)
    if start > end:
        return None, {"field": "from", "message": PERIOD_BACKWARDS}
    if (end - start).days + 1 > PERIOD_MAX_DAYS:
        return None, {"field": "to", "message": PERIOD_TOO_LONG}
    return (start, end), None


def period_bounds(period):
    """``(from, to)`` dates -> ``(start, end)`` datetimes with ``start <= t < end``: ``to`` is
    included to the end of its day."""
    start, end = period
    return datetime.combine(start, time.min), datetime.combine(end + timedelta(days=1), time.min)


def age_days(created_at, today):
    """Days since the improvement started: started today is 0."""
    return (today - created_at.date()).days


def age_band(days):
    """The band key of an age; a negative age (a clock set back) counts as the youngest band."""
    for key, first_day in _BAND_STARTS:
        if days >= first_day:
            return key
    return AGE_BANDS[0]


def open_summary(rows):
    """``rows``, each with ``display_state`` and ``age_days`` -> ``{count, by_state, band_totals}``;
    every state and every band is present, with 0 when empty, so the table never loses a row."""
    by_state = {state: dict.fromkeys(AGE_BANDS, 0) for state in OPEN_DISPLAY_STATES}
    for row in rows:
        by_state[row["display_state"]][age_band(row["age_days"])] += 1
    band_totals = {band: sum(counts[band] for counts in by_state.values()) for band in AGE_BANDS}
    return {
        "count": len(rows),
        "by_state": [{"state": state, "bands": by_state[state], "total": sum(by_state[state].values())}
                     for state in OPEN_DISPLAY_STATES],
        "band_totals": band_totals,
    }


def worked_share(it_worked, did_not_work):
    """The share of the verified closes that worked: a whole percent, half rounded up; None when
    none was verified.  Dropped ones are not verified, so they are not in it (D6).  A local
    measure, not an SMRP KPI."""
    verified = it_worked + did_not_work
    if verified == 0:
        return None
    return (200 * it_worked + verified) // (2 * verified)


def closed_summary(rows):
    """``rows``, each with ``state`` (a closed state) -> the three counts and the share."""
    it_worked = sum(1 for row in rows if row["state"] == CLOSED_EFFECTIVE)
    did_not_work = sum(1 for row in rows if row["state"] == CLOSED_NOT_EFFECTIVE)
    dropped = sum(1 for row in rows if row["state"] == DROPPED)
    return {"it_worked": it_worked, "did_not_work": did_not_work, "dropped": dropped,
            "worked_share": worked_share(it_worked, did_not_work)}
