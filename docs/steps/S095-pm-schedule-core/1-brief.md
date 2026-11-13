```
Step: S095 — PM scheduling core
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 01-11-2026
Track: full
Baseline: c9cd091
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 01-11-2026 (code review r1: 2 nits, CR1-01 and CR1-02, fixed by the orchestrator; no device check); approved 01-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 1 major, 5 minor, 6 nits, all accepted; the decisions of § 7 and § 9 flagged for KLA at gate B)
From: R03.1
```

# S095 — PM scheduling core

## 1. What will be built

PM (R03) needs one place that decides **when a plan's next job is due** and **how a job stands**.
S095 builds it as one pure Python module, `backend/pm_schedule_core.py`, with its unit tests
first. No DB, no clock, no Flask (CLAUDE-COMMON *Pure core, thin shell*): the shell passes in
today's IST date, the plan's fields, the last job's done date and meter value, and the latest
reading of the plan's meter.

The module answers three questions:

1. **When is the next job due?** (`next_due`, § 5.3) A calendar date, a meter value, or both.
   - Calendar: every N days, weeks, months or years, **from the last job's done date** (floating,
     Plan.MD § 4.3). One month after 31-01-2027 is 28-02-2027; after 31-01-2028 it is 29-02-2028.
   - Meter: every N units of one counter meter, from the meter value at the last done time (Q1.2).
     An oil change done at 5,040 h, every 5,000 h, is next due at 10,040 h.
   - Both: whichever comes first; a done job restarts both.
   - The first job: from the engineer's *Last done* seed (date, meter value), or from the plan's
     creation date when nothing was done before.
   - A rescheduled due date or meter value (R03.9, later) replaces the computed one: an optional
     `override` input now.
2. **How does an open job stand today?** (`job_state`, § 5.4) *Not yet*, *Upcoming*, *Due* or
   *Overdue*, and which trigger put it there. A meter plan whose meter has no reading reads
   "No reading yet" and is never due by meter; a calendar trigger on the same plan still works.
3. **Was a done job on time?** (`timeliness`, § 5.5) *On time* or *Late*, by the window of Q1.1:
   10 % of the interval after the due point, at least 1 day.

A plan with the trigger kind `before_use` (R03.13) is never due by date or meter, never overdue,
and is not judged on time or late.

**After S095:** nothing changes on screen. R03.2 (S096, the plans table) imports the module's
constants for its trigger fields; R03.3 (jobs come due) calls the three functions.

### Out of scope

- Any table, migration, route, task or screen. S096 adds `pm_plans`; R03.3 adds `pm_jobs`, the
  daily run and the *PM* list.
- The shell queries that find "the meter value at a time" (§ 5.2 states the rule R03.3 follows).
- A counter reset between the last done time and today (§ 9 A3): R03.3's shell decides.
- Forecasts by usage rate (a meter's average per day to guess a date) and a fixed-rhythm option
  (R03.1 *Leaves for later*; Plan decided floating).
- Reschedule and skip themselves (R03.9): S095 only takes the override.
- CIL's "one before-use job per machine per IST day" (R03.13): the shell's rule.
- A gauge crossing its limit is not a PM trigger (BR1-06): it raises a ticket (condition-based,
  Plan.MD § 4.5; R03.10). `KINDS` has no kind for it. Plan § 4.3 *Triggers* still names it; the
  coder's Plan.MD note says so (§ 3 Docs).

## 2. Standards and practice

- **EN 13306 — maintenance terms** (term numbers *to verify*). In plain words:
  - *Preventive maintenance* is done before a failure, to lower its chance.
  - *Predetermined maintenance* is preventive work done at set intervals of **time or use**,
    without first measuring the condition. A PM plan with a calendar or a meter trigger is this.
  - *Scheduled maintenance* is done to a timetable. The core makes the timetable: one due point
    per plan, known once the last job is done.
  - S095 follows it: the trigger kinds are the two forms of predetermined maintenance (time,
    use) and their combination. It uses EN 13306's *interval* and *due* words, not local ones.
- **SMRP — PM compliance** (metric number *to verify*). In plain words: of the PM jobs that fell
  due in a period, the share done on time. "On time" needs a window, or a job one day late counts
  the same as one a month late. Common practice is the **10 % rule**: a job is compliant when it is
  done within 10 % of its interval after the due point. S095 follows it (Q1.1 (a)), with a floor of
  1 day so a weekly job gets a day's grace. R03.14 counts with `timeliness`; S095 gives the rule.
- **TPM — planned maintenance pillar.** In plain words: the team decides in advance what each
  machine needs and when. The core is the "when".
- **Departure, stated (§ 7 D4):** the roadmap's R03.1 says "Overdue: past due". S095 calls a job
  *Due* through its on-time window and *Overdue* after it, so *Overdue* means "it will count as
  late now". The reason is in D4.

## 3. Where

### Backend

- `backend/pm_schedule_core.py` (new): the constants, the dataclasses `Due` and `Standing`, and
  the functions `add_interval`, `window_days`, `upcoming_days`, `next_due`, `job_state`,
  `timeliness` (§ 5). It imports `datetime`, `decimal`, `dataclasses` and `add_months` from
  `contracts_core` (pure to pure, D6), nothing else.
- `backend/contracts_core.py`: rename `_add_months` (`backend/contracts_core.py:357`) to the
  public `add_months`; its one call, inside `renewal_period` (`backend/contracts_core.py:371`),
  follows. No change of behaviour. No other code file uses `_add_months` (facts run).

### Tests

- `backend/tests/test_pm_schedule_core.py` (new): § 8.1, written and green before anything else.
- `backend/tests/test_contracts_core.py`: the import (line 19) and
  `test_add_months_keeps_the_month_end` (line 387) use `add_months`.

### Docs (housekeeping, by the coder)

- `docs/Maintenance-Philosophy.md` § 7: the last paragraph's "TBD — how late a PM job may be before
  it is 'overdue' … **Proposed**" becomes **Decided** (R03 Q1.1 (a), S095): the 10 % window, at
  least 1 day, the *Due* / *Overdue* rule of D4. Shutdown planning stays TBD.
- `docs/Plan.MD` § 4.3, *Triggers*: edit the *Calendar* bullet itself to read "every N days /
  weeks / months / years" (A2, BR1-12); say in the *Meter* bullet that a reading crossing a limit
  raises a ticket, not a PM job (BR1-06); then one line "**Built (S095, …):** the scheduling rules",
  naming month arithmetic, the seed, whichever first, the windows, and D4's departure from R03.1's
  wording with its two consequences for R03.3 and R03.7 (BR1-02), so their briefs pick them up.
- `.claude/CLAUDE.md` § SMTW-Review: the point proposed in § 9 Q4.
- No schema docs (no migration), no `docs/steps/device-checks.md` row (no device check).

## 4. Data model

None. The core takes plain values; the column names of S096's `pm_plans` are the input names of
§ 5.1, so the shell passes a row with the IST dates added.

## 5. Rules

### 5.1 Constants and inputs

```python
CALENDAR, METER, BOTH, BEFORE_USE = "calendar", "meter", "both", "before_use"
KINDS = (CALENDAR, METER, BOTH, BEFORE_USE)
DAY, WEEK, MONTH, YEAR = "day", "week", "month", "year"
CALENDAR_UNITS = (DAY, WEEK, MONTH, YEAR)
NOT_YET, UPCOMING, DUE, OVERDUE = "not_yet", "upcoming", "due", "overdue"
ON_TIME, LATE = "on_time", "late"
WINDOW_DIVISOR = 10       # 10 % of the interval (Q1.1, Q3.1)
MIN_WINDOW_DAYS = 1       # Q1.1: at least 1 day
UPCOMING_MAX_DAYS = 7     # Q3.1: 7 days or 10 %, the shorter
```

`plan` is a mapping with these keys (the shared names with S096):

| Key | Type | Rule |
|---|---|---|
| `trigger_kind` | str | One of `KINDS`. Not `kind`: `pm_plans` keeps `kind` for PM / CIL (`docs/schema/notes.json`, BR1-01). |
| `calendar_every` | `int` ≥ 1 (not `bool`), or None | Set for `calendar` and `both`; None for `meter` and `before_use`. |
| `calendar_unit` | one of `CALENDAR_UNITS`, or None | Set exactly when `calendar_every` is set. |
| `meter_type_id` | int, or None | Set for `meter` and `both`; the core only checks it is set. |
| `meter_every` | `Decimal` > 0, or None | Set exactly when `meter_type_id` is set. |
| `last_done_on` | `date`, or None | The engineer's seed date. |
| `last_done_meter` | `Decimal` ≥ 0, or None | The engineer's seed meter value. Ignored for a plan with no meter. |
| `created_on` | `date` | The IST date of the plan's creation. Required. |

A plan that breaks a rule of this table raises `ValueError` naming the key: it is a shell or S096
bug, never user input (S096 validates the form). Extra keys are ignored, so the shell may pass the
whole row. A `before_use` plan ignores the four trigger keys. **Every date input must be a `date`, not a
`datetime`** (`type(x) is date`, else `TypeError`): a `datetime` is a `date` subclass, and passing
a UTC time would shift the IST date (CLAUDE-COMMON *Timezone*). **Number checks** (BR1-04):
`calendar_every` must be an `int` and not a `bool`, else `TypeError`. Every meter value
(`meter_every`, `last_done_meter`, `start_meter`, `last_job["done_meter"]`, the override's
`due_meter`, `reading_value` and `done_meter`) must be a `Decimal` or an `int` (not a `bool`); a
`float` or any other type raises `TypeError` naming the key. Reason: `Decimal("3000") < 3001.5`
passes silently, so a float would give a state with no error (checked by the reviewer,
01-11-2026). The shell reads `DECIMAL` columns as `Decimal`, so no conversion is needed.

### 5.2 The base: where the next interval counts from

| Case | Base date | Base meter value |
|---|---|---|
| A last job exists | `last_job["done_on"]` | `last_job["done_meter"]` (may be None) |
| No job, a seed | `last_done_on`, or `created_on` when the seed has no date | `last_done_meter`, or `start_meter` when the seed has no value |
| No job, no seed | `created_on` | `start_meter` |

- `last_job` is None or a mapping with `done_on` (`date`, the IST date of the done time) and
  `done_meter` (`Decimal` or None). A done job always wins over the seed: the seed is only the
  first job's base.
- `start_meter` is the meter value at the plan's start (the seed date, else `created_on`), or None.
- **The shell's rule for "the meter value at a time T"** (R03.3 follows it for `done_meter` and
  `start_meter`): the latest active reading of the plan's meter on the plan's node taken at or
  before T; when there is none, the earliest one after T; None when the meter has no reading.
  The fallback means a plan made before the first reading starts counting from that reading.

### 5.3 `next_due`

```python
def next_due(plan, last_job=None, start_meter=None, override=None) -> Due
```

```python
@dataclass(frozen=True)
class Due:
    due_on: date | None           # the calendar trigger's due date; None without a calendar trigger
    due_meter: Decimal | None     # the meter trigger's due value; None without one, or without a base value
    grace_days: int | None        # the on-time window after due_on; None without a calendar trigger
    upcoming_days: int | None     # the window before due_on; None without a calendar trigger
    meter_window: Decimal | None  # 10 % of meter_every, before and after due_meter; None without a meter trigger
    rescheduled: bool             # an override replaced a computed value
    before_use: bool
```

- `trigger_kind` `before_use` → every field None, `rescheduled` False, `before_use` True. `override` must be None
  (else `ValueError`).
- **Calendar** (`calendar` and `both`): `computed = add_interval(base_date, calendar_every,
  calendar_unit)`; `interval_days = (computed - base_date).days`; `grace_days =
  window_days(interval_days)`; `upcoming_days = upcoming_days(interval_days)`; `due_on = computed`.
- **Meter** (`meter` and `both`): `meter_window = meter_every / WINDOW_DIVISOR` (exact in
  `Decimal`: 250 → 25, 0.5 → 0.05); `due_meter = base_meter + meter_every`, or None when the base
  meter value is None.
- **Override** (R03.9): None, or a mapping with `due_on` (`date` or None) and `due_meter`
  (`Decimal` or None). A value that is set replaces that trigger's computed value; the windows stay
  those of the computed interval (D5). An override for a trigger the plan does not have raises
  `ValueError`. `rescheduled` is True when either value was set. An override `due_meter` on a meter
  plan with no base value is allowed (the trigger exists): `job_state` then judges it, and
  `no_reading` is False, once a reading exists (BR1-09).

```python
def add_interval(day, every, unit) -> date
```

- `DAY`: `day + every` days. `WEEK`: `day + 7 × every` days.
- `MONTH`: `add_months(day, every)`: the same day of the month, or the month's last day when the
  month is shorter. `YEAR`: `add_months(day, 12 × every)` (29-02-2028 + 1 year = 28-02-2029).
- `every` < 1 or an unknown unit → `ValueError`. A result past 31-12-9999 raises Python's own
  `OverflowError` / `ValueError`; S096 bounds the interval.
- Floating months do not snap back: done 28-02-2027 on a monthly plan → due 28-03-2027, not 31-03.

```python
def window_days(interval_days) -> int      # max(MIN_WINDOW_DAYS, interval_days // WINDOW_DIVISOR)
def upcoming_days(interval_days) -> int    # min(UPCOMING_MAX_DAYS, window_days(interval_days))
```

- 10 % is **rounded down** to whole days, at least 1 (D3). The interval is the actual number of
  days from the base date to the computed due date, so a month is 28 to 31 days.
- Results: 1 day → 1 / 1; 7 days → 1 / 1; 28 → 2 / 2; 30 or 31 → 3 / 3; 90 → 9 / 7; 365 or
  366 → 36 / 7 (grace / upcoming). This matches Q1.1's text: "a monthly job is on time up to 3 days
  late; a yearly one up to 36 days".
- `interval_days` < 1 → `ValueError` (it cannot happen from `add_interval`).

### 5.4 `job_state`

```python
def job_state(due, reading_value, today) -> Standing
```

```python
@dataclass(frozen=True)
class Standing:
    state: str            # NOT_YET, UPCOMING, DUE or OVERDUE
    trigger: str | None   # CALENDAR or METER: the trigger that gave the state; always None for NOT_YET
    no_reading: bool      # the plan has a meter trigger, and no reading or no base value: "No reading yet"
```

- `reading_value` is the value (`Decimal` or `int`) of the latest active reading of the plan's
  meter on the plan's node, or None when it has none (BR1-05: the reading's time is not an input;
  the screen shows it from its own query). `today` is the IST date.
- **The calendar trigger's state** (`due_on` set; D = `due_on`, U = `upcoming_days`,
  G = `grace_days`):
  - `today < D − U` → NOT_YET; `D − U ≤ today < D` → UPCOMING;
  - `D ≤ today ≤ D + G` → DUE (the due day itself is *Due*); `today > D + G` → OVERDUE.
- **The meter trigger's state** (`due_meter` and `reading_value` set; M = `due_meter`,
  W = `meter_window`, r = `reading_value`):
  - `r < M − W` → NOT_YET; `M − W ≤ r < M` → UPCOMING; `M ≤ r ≤ M + W` → DUE; `r > M + W` →
    OVERDUE.
  - A meter trigger (`meter_window` set) with `due_meter` None or `reading_value` None gives no
    state, and `no_reading` is True.
- **Whichever first:** the plan's state is the furthest of its triggers' states (OVERDUE > DUE >
  UPCOMING > NOT_YET), and `trigger` names that trigger. A tie goes to CALENDAR (a date reads more
  plainly on the list). A plan whose only trigger gives no state is NOT_YET. `trigger` is None
  whenever the state is NOT_YET, also when a calendar trigger gave it (E16, E17 at 20-11, E18;
  BR1-07).
- A `before_use` plan → NOT_YET, `trigger` None, `no_reading` False.
- The state never looks at whether a job exists: the shell (R03.3) keeps one open job per plan
  (Q3.1) and asks the state of that job's `Due`. A job nobody does stays OVERDUE (Q3.3): the
  state only moves forward while `today` and `reading_value` grow.

### 5.5 `timeliness`

```python
def timeliness(due, done_on, done_meter) -> str | None
```

- `done_on` is the IST date of the done time (`date`, required); `done_meter` is the meter value
  at the done time (§ 5.2 rule) or None.
- LATE when **any** trigger was past its window: `due_on` set and `done_on > due_on + grace_days`,
  or `due_meter` set, `done_meter` not None and `done_meter > due_meter + meter_window`. Otherwise
  ON_TIME (D2). A job done early is ON_TIME.
- `done_meter` None, or `due_meter` None: the meter trigger cannot make the job late (no evidence).
- A `before_use` plan → None: not judged (R03.13 leaves before-use jobs out of compliance).
- So a job is on time exactly when it would not have shown OVERDUE on the day and at the meter
  value it was done: at the same date and meter value, `job_state` and `timeliness` never disagree
  (tested, § 8.1 T9; BR1-10).

### 5.6 Worked examples (they become the tests)

Dates are DD-MM-YYYY. "Grace" and "Up" are `grace_days` and `upcoming_days`.

| # | Plan and base | `next_due` | `job_state` / `timeliness` |
|---|---|---|---|
| E1 | 1 month; last job done 31-01-2027 | 28-02-2027; 28 days; grace 2, up 2 | 25-02 not yet; 26-02 upcoming; 28-02 due; 02-03 due; 03-03 overdue. Done 02-03 on time; done 03-03 late. |
| E2 | 1 month; done 31-01-2028 (leap year) | 29-02-2028; 29 days; grace 2, up 2 | 02-03-2028 due; 03-03-2028 overdue. |
| E3 | 1 month; done 15-03-2027 | 15-04-2027; 31 days; grace 3, up 3 | 11-04 not yet; 12-04 upcoming; 18-04 due; 19-04 overdue. |
| E4 | 3 months; done 30-11-2026 | 28-02-2027; 90 days; grace 9, up 7 | 21-02 upcoming; 09-03 due; 10-03 overdue. |
| E5 | 1 month; done 28-02-2027 | 28-03-2027 (no snap back to 31-03) | — |
| E6 | 1 week; done 02-11-2026 | 09-11-2026; grace 1, up 1 | 07-11 not yet; 08-11 upcoming; 10-11 due; 11-11 overdue. |
| E7 | 1 day; done 01-11-2026 | 02-11-2026; grace 1, up 1 | 01-11 upcoming; 03-11 due; 04-11 overdue. |
| E8 | 1 year; done 10-01-2027 | 10-01-2028; 365 days; grace 36, up 7 | 02-01-2028 not yet; 03-01 upcoming; 15-02-2028 due; 16-02 overdue. |
| E9 | 1 year; done 29-02-2028 | 28-02-2029; 365 days; grace 36 | — |
| E10 | 250 h; last job at 12,040 h | 12,290 h; window 25 | 12,264.9 not yet; 12,265 upcoming; 12,290 due; 12,315 due; 12,315.1 overdue. Done at 12,315 on time; at 12,316 late. |
| E11 | 5,000 h; done at 5,040 h (Q1.2) | 10,040 h; window 500 | — |
| E12 | 1 month and 250 h; done 01-11-2026 at 3,000 h (standby genset) | 01-12-2026 (grace 3, up 3) and 3,250 h (window 25) | 20-11 at 3,260 → due, meter. 05-12 at 3,100 → overdue, calendar. 01-12 at 3,250 → due, calendar (tie). 28-11 at 3,100 → upcoming, calendar. Done 03-12 at 3,120 on time; done 03-12 at 3,280 late (meter). |
| E13 | 1 month; no job; seed 20-10-2026; created 01-11-2026 | 20-11-2026 | — |
| E14 | 250 h; no job; seed 11,800 h, no seed date | 12,050 h | — |
| E15 | 1 month and 250 h; no job, no seed; created 01-11-2026; `start_meter` 12,000 | 01-12-2026 and 12,250 h | — |
| E16 | 250 h; no job, no seed; `start_meter` None; no reading | `due_meter` None | not yet; `no_reading` True; no trigger. |
| E17 | 1 month and 250 h; as E16 for the meter; created 01-11-2026 | 01-12-2026; `due_meter` None | 02-12 → due, calendar, `no_reading` True. |
| E18 | 250 h; base 12,040 h; `reading_value` None | 12,290 h | not yet; `no_reading` True. |
| E19 | `before_use` | every field None | not yet, no trigger; `timeliness` None. |
| E20 | E1 with override `due_on` 10-03-2027 | 10-03-2027; grace 2 (of the computed 28 days); rescheduled | 12-03 due; 13-03 overdue. Done 12-03 on time (Q9.1). |
| E21 | A job done 20-02-2027 after the seed 05-01-2027, monthly | the job wins: 20-03-2027 | — |
| E22 | E1, done 20-02-2027 (early) | — | on time. |

## 6. API

None.

## 7. Design decisions

- **D1. Three functions over two small frozen dataclasses.** `next_due` gives the plan's due point
  once; `job_state` and `timeliness` judge it against today or a done job. `job_state` needs the
  whole `Due` (the windows too), so R03.3 recomputes it from the plan, the last job and the stored
  override each time (§ 9 N1); R03.14 reads the judgement stored on each done job. Rejected: one function returning everything (it would need today
  and the done values at once, though the list, the daily run and the report each need one part);
  plain dicts (a typo in a key is silent; the cores use dicts for DB rows, dataclasses fit a result
  with fixed fields).
- **D2. Whichever first, judged on every trigger.** The state is the furthest trigger's; a done job
  is late if **either** trigger was past its window. So *on time* is exactly "not overdue when
  done". Rejected: on time against the trigger that fired only (a genset due by calendar but done
  after its meter window would count on time while the list showed *Overdue*).
- **D3. 10 % rounded down to whole days, at least 1; the interval in actual days.** Floor matches
  Q1.1's own figures (monthly 3 days, yearly 36). A monthly plan from 31-01 gets 2 days, as its
  interval is 28 days. Rejected: a month counted as 30 days (a rule the user cannot see); rounding
  to the nearest (365 → 37, against Q1.1's 36). The meter window is exact in `Decimal`, with no
  floor: a meter has no "day" to round to. A consequence of the floor (BR1-11): a daily plan's
  grace is its whole interval: done 01-11, due 02-11, on time through 03-11 (E7).
- **D4. *Due* through the on-time window, *Overdue* after it** (departure from R03.1's "Overdue:
  past due"; flagged in § 9 Q1). With readings taken once a day, a 250 h counter can jump past the
  due value in one reading: if *Overdue* began just past the due point, a meter job would skip *Due*
  and count late at once. And a calendar job shown *Overdue* the day after due could still count
  *on time*: two words in conflict. Under D4 *Overdue* means "done now, it counts late". Rejected:
  *Overdue* from the day after due (the roadmap's literal text). **Two consequences** (BR1-02):
  (1) on R03.3's list a job past its due date still reads *Due* for up to its grace (3 days on a
  monthly plan, 36 on a yearly one), so the row must show the due date and the days past it, or a
  reader cannot tell "due today" from "due 20 days ago"; (2) R03.7's *PM job overdue* alert, if it
  follows the state, fires only when the job already counts late: R03.7 decides knowingly whether to
  alert at the due point instead (with *Due* in the text) or at the grace end.
- **D5. An override keeps the computed interval's windows.** Q9.1: "a rescheduled job is on time
  against the new date". The grace is 10 % of the plan's interval, not of the delay: a monthly job
  pushed 10 days still gets 2 or 3 days' grace. Rejected: windows from the override's distance (a
  long push would also widen the grace).
- **D6. Month arithmetic reuses `contracts_core._add_months`, made public as `add_months`.** It
  already does the rule ("the same day of the month, or the month's last day", tested at
  `backend/tests/test_contracts_core.py:387`). The cores do not import each other's private
  helpers (`backend/contracts_core.py:5`, the module docstring), so the rename is the DRY way. Rejected: a copy in the new
  module (CLAUDE-COMMON *DRY*); a new dates module for 4 lines.
- **D7. The core owns the trigger vocabulary.** `KINDS` and `CALENDAR_UNITS` live here; S096
  imports them for its validation and ENUM, so the column values and the core's strings cannot
  drift. Rejected: each step defining its own strings.
- **D8. A bad plan input raises; it is never user input.** S096 validates the form; the core raises
  `ValueError` / `TypeError` with the key's name, so a shell bug fails loudly in a test instead of
  scheduling wrongly. Rejected: returning a "not scheduled" state (it would hide the bug).
- **D9. A missing meter base starts from the first reading** (§ 5.2's shell rule). A plan made
  before its meter's first reading counts from that reading, so it does not stay "No reading yet"
  for ever. Rejected: no meter trigger until the engineer types a seed (a plan nobody re-edits
  would never come due by meter).

## 8. Tests and acceptance

### 8.1 Pure core (`backend/tests/test_pm_schedule_core.py`, new; written first)

Each worked example of § 5.6 is a test (parametrised where it fits), plus:

- T1 `add_interval`: every unit; month ends (31-01 → 28-02 / 29-02; 31-03 + 1 month → 30-04);
  12 months = 1 year; `every` 0 and an unknown unit → `ValueError`.
- T2 `window_days` / `upcoming_days`: 1, 7, 9, 10, 28, 30, 31, 69, 70, 90, 365, 366 days; 0 →
  `ValueError`.
- T3 the base (§ 5.2): job over seed; seed date without value (meter from `start_meter`); seed
  value without date (calendar from `created_on`); a job with `done_meter` None → `due_meter` None.
- T4 every boundary of § 5.4 on both sides (D − U − 1, D − U, D − 1, D, D + G, D + G + 1; and
  M − W, M, M + W just under and over).
- T5 whichever first: each trigger furthest in turn; the tie → CALENDAR.
- T6 `timeliness`: on the last day of the window → ON_TIME, the day after → LATE; the meter
  likewise; `done_meter` None → judged by the calendar only; `before_use` → None.
- T7 override: date only, meter only, both; a meter override on a calendar plan → `ValueError`;
  an override on `before_use` → `ValueError`; windows unchanged.
- T8 bad input (`ValueError` naming the key): an unknown `trigger_kind`, and a row with only `kind`;
  `calendar` without
  `calendar_every`; `calendar_unit` without `calendar_every`; `meter` without `meter_every`;
  `meter_every` 0 or negative; `calendar_every` 0; `created_on` None; and `TypeError` naming the
  key for a `datetime` as `created_on`, `done_on` or `today`, a `float` as each meter value of
  § 5.1 (`meter_every`, `last_done_meter`, `start_meter`, `done_meter`, the override's `due_meter`,
  `reading_value`), a `Decimal` or `float` or `bool` as `calendar_every`.
- T9 agreement: for E1, E10 and E12, over every day of the window ± 2 (and readings in steps),
  `timeliness(due, d, r) == LATE` exactly when `job_state(due, r, d).state == OVERDUE`.
- T10 a `before_use` plan ignores the trigger keys (set or not).

### 8.2 Existing tests that change or run again

- `backend/tests/test_contracts_core.py`: the import and `test_add_months_keeps_the_month_end`
  (rename, D6); `test_renewal_period_whole_months`, `test_renewal_period_not_whole_months` and
  `test_renewal_period_past_2099` run again unchanged.
- The always-check tests (`test_role_matrix`, `conftest.py` `_TABLES`, `db_down`, the
  `test_migration_*` tests) are not touched: no key, table, route or migration.
- `tooling/tests/test_line_width.py`: the new files keep every line at 120 characters or fewer.

### 8.3 Runs

- While coding: `tooling/run-backend-tests.bat tests/test_pm_schedule_core.py tests/test_contracts_core.py`.
- Once when done: `tooling/run-tests.bat` (all three suites; the tooling suite has the line width).
- No browser test, no frontend build, no schema docs check: nothing on screen, no migration.

### 8.4 On a real device

None.

### 8.5 Acceptance

- `test_pm_schedule_core.py` covers every row of § 5.6 and T1–T10; all unit suites green.
- `backend/pm_schedule_core.py` imports no Flask, no DB module and no clock (`datetime.now`,
  `date.today`): a grep in the code review.

## 9. Open questions and assumptions

All decided by the orchestrator under KLA's go-ahead (01-11-2026, "do those steps … stop only for
real show stoppers"), **to confirm at gate B**:

- **Q1. When does a job turn *Overdue*?** Decided **(a)**.
  - **(a) After the on-time window (D4) — recommended.** *Overdue* = "it counts late now".
    Its cost: a job past due reads *Due* for up to its grace (36 days on a yearly plan), so R03.3's
    row shows the due date and the days past it; R03.7 chooses when the overdue alert fires (D4).
  - (b) The day after due, as R03.1's text reads. Meter jobs read once a day would skip *Due*, and
    a job could read *Overdue* while counting on time.
- **Q2. Rounding of 10 %.** Decided **(a)**: down to whole days, at least 1, from the actual days
  (D3). (b) Nearest: a yearly plan gets 37 days, against Q1.1's 36.
- **Q3. On time on a two-trigger plan.** Decided **(a)**: late if either trigger was past its window
  (D2). (b) Only the trigger that fired: the list and the report could disagree.
- **Q4. Proposed point for `.claude/CLAUDE.md` § SMTW-Review** (the coder adds it): "PM schedule
  (S095): every due date, due meter value, state (*Not yet*, *Upcoming*, *Due*, *Overdue*) and
  on-time judgement comes from `pm_schedule_core` (`next_due`, `job_state`, `timeliness`); no
  route, report, SQL or screen computes them itself, and the shell passes IST dates."
- **Q5. Trigger strings for S096.** Decided: the plan's key and column is `trigger_kind`
  (BR1-01), S096's `trigger_kind ENUM('calendar','meter','both','before_use')`, with `KINDS` =
  `calendar`, `meter`, `both`, `before_use` and `CALENDAR_UNITS` = `day`, `week`, `month`, `year`
  (D7). The orchestrator has told S096's drafter.
- **A1.** The month helper's behaviour is checked: `add_months` of 31-01-2027 + 1 is 28-02-2027,
  of 31-01-2028 + 1 is 29-02-2028, of 30-11-2026 + 3 is 28-02-2027 (90 days), of 10-01-2027 + 12 is
  10-01-2028 (365 days); `Decimal("250") / 10` is `25`, `Decimal("0.5") / 10` is `0.05`; comparing a
  `datetime` with a `date` raises `TypeError` (run 01-11-2026, `uv run python`).
- **A2.** Years are a calendar unit, though Plan.MD § 4.3 names days, weeks and months: a yearly
  plan as "12 months" reads poorly on the card, and the statutory and calibration plans (R04) are
  yearly.
- **A3.** A counter reset (Plan § 4.5) between the base and today makes the latest value lower
  than the base; the meter trigger then reads NOT_YET until the counter passes the due value again.
  R03.3's shell decides how to carry the usage across a reset (e.g. a new base at the reset). Noted
  for R03.3's brief.
- **A4.** `done_on` is the IST date of the job's done time; a job done at 23:50 IST on 31-01 is
  done on 31-01 (the shell converts; the core never sees a time).
- **N1. For R03.3's brief** (BR1-03; recommended, R03.3 decides):
  - The shell recomputes `next_due` for an open job each time from the plan, the last done job,
    `start_meter` and the job's stored override; it stores nothing on the open job it cannot
    recompute. `due_on` and `due_meter` on `pm_jobs` are copies for sorting and the list; they are
    rewritten when the recomputed values differ (a plan edit changes its open job's due point and
    windows: the engineer's edit is the new rhythm).
  - So a job with `due_meter` None (E16, E17) gains a due value in the next daily run after the
    meter's first reading, as D9 needs, and `no_reading` never reads "No reading yet" while a
    reading exists.
  - At *Mark job done* the shell stores the job's final `due_on`, `due_meter` and `timeliness`
    result on the job: a done job's record does not change with a later plan edit (ISO 9001
    § 7.5.3), and R03.14 counts the stored results.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 01-11-2026

| Finding | Answer |
|---|---|
| BR1-01 (major) | Accepted. The input key is `trigger_kind` (§ 5.1 table, T8, Q5); S096 uses `trigger_kind ENUM('calendar','meter','both','before_use')` with the core's `KINDS` and `CALENDAR_UNITS`. `kind` stays free for PM / CIL. |
| BR1-02 | Accepted. D4 and Q1 name both consequences (the list shows the due date and days past; R03.7 chooses the alert's moment); the Plan.MD note in § 3 Docs carries them to R03.3 and R03.7. |
| BR1-03 | Accepted. D1 revised; § 9 N1 for R03.3: recompute `next_due` for an open job each time, store copies only, store the final due point and `timeliness` at done. |
| BR1-04 | Accepted. § 5.1 *Number checks*: `calendar_every` an `int`, not `bool`; every meter value `Decimal` or `int`, a `float` raises `TypeError` naming the key; T8 tests them. |
| BR1-05 | Accepted. `job_state(due, reading_value, today)`; `taken_on` removed (§ 5.4, T9). |
| BR1-06 | Accepted. Out of scope line; the Plan.MD *Meter* bullet edit in § 3 Docs. |
| BR1-07…BR1-12 | Accepted: `trigger` always None for NOT_YET (§ 5.4); `meter_window` None without a meter trigger (§ 5.3); the override on a meter plan with no base (§ 5.3); "at the same date and meter value" (§ 5.5); the daily plan's grace (D3); the coder edits Plan § 4.3's *Calendar* bullet itself (§ 3 Docs). |
