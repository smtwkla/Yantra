```
Step: S095 — PM scheduling core
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
```

# S095 — code review, round 1

**Verdict: no blocker or major finding is open.** The module does what § 5 of the brief says, and my own cases
agree with the rules. There are 2 nits.

## Test runs

- `YANTRA_TEST_RUN=s095cr1 tooling/run-backend-tests.bat tests/test_pm_schedule_core.py tests/test_contracts_core.py`:
  **PASSED, 238 passed** in 13 s (137 new and 101 contracts), log `scratch/backend-tests-s095cr1.log`.
- I did not run all suites again. The diff touches only `backend/` code and docs, and the step's two test files
  cover the changed code. The coder's full run is in the impl report: backend 4607 passed and 1 failed (an S092
  search test, outside this step, green on re-run), frontend 412, tooling 239.
- The line width (`tooling/tests/test_line_width.py`): I measured the two new files. The longest lines are 117
  and 115 characters.
- No browser run, frontend build or schema docs check is due: no screen, API, migration or `docs/schema/`
  change.

## My own cases (a scratch script, read-only)

All of these agree with § 5:

- **Month ends.** 29-01 and 30-01 + 1 month give 28-02-2027. 31-12-2027 + 2 months gives 29-02-2028.
  31-08-2026 + 6 months gives 28-02-2027. 31-01-2100 + 1 month gives 28-02-2100 (2100 is not a leap year).
- **Leap years.** 29-02-2028 + 12 months gives 28-02-2029, the same as + 1 year.
- **Windows.** 2 weeks: 14 days, grace 1, up 1. 6 months from 01-03-2027: 184 days, grace 18, up 7. 2 years:
  731 days, grace 73. 10 years (S096's maximum): 3653 days, grace 365.
- **Whichever first, agreement.** I checked 60 `both` plans (units day to year, every 1 to 12, bases 31-01,
  29-02 and 31-12) over 120 days around the due date and four readings each. `timeliness` gives LATE exactly
  when `job_state` gives OVERDUE: 0 mismatches.
- **DB-style decimals.** `meter_every` `Decimal("5000.000")` and a done value `5040.000` (S096's
  `DECIMAL(14,3)`) give `due_meter` 10040.000 and `meter_window` 500.000.
- **A counter reset** (A3): a reading below the base reads *Not yet*, with `no_reading` False, as A3 says.
- **An override earlier than the computed date** keeps the computed windows (D5): a yearly plan moved to 01-06
  reads *Due* on 07-07 and *Overdue* on 08-07.
- **Purity.** `pm_schedule_core.py` imports only `dataclasses`, `datetime` (`date`, `timedelta`), `decimal` and
  `contracts_core.add_months`. It has no Flask, no DB module, no `now()` and no `today()` (§ 8.5 grep).

## The later steps can call it

- **S096** imports only the constants (`docs/steps/S096-pm-plans/1-brief.md` § 3). Its ENUMs
  `trigger_kind ENUM('calendar','meter','both','before_use')` and `calendar_unit ENUM('day','week','month','year')`
  equal `KINDS` and `CALENDAR_UNITS` in their order. The test `TestConstants` pins the strings.
- **S096's columns fit the input table** (§ 5.1): `SMALLINT` gives an `int`, `DECIMAL(14,3)` a `Decimal`, `DATE`
  a `date`. `pm_plans` has `created_at DATETIME`, not `created_on`. The shell must add the IST date
  `created_on` (brief § 4 says so). R03.3's brief must state it, or `next_due` raises `created_on is required`.
- **S096's checks are stricter than the core's** (`chk_pm_plans_seed` forbids a seed on a plan with no meter, or on
  `before_use`). The core ignores those keys, so any row S096 can store passes `_check_plan`.
- **S097 (R03.3)** has no brief yet (the folder `docs/steps/S097-pm-jobs-due/` does not exist). R03.3's roadmap
  item needs the state, the trigger for "created why: calendar / meter", one due point per plan and the latest
  reading. `next_due`, `job_state` (`trigger`) and N1 give all of them.

## Nits

- **CR1-01** (nit) `backend/tests/test_pm_schedule_core.py:26`: add the missing space after the comma in
  `"trigger_kind": trigger_kind,"calendar_every"`.
- **CR1-02** (nit) `docs/steps/S095-pm-schedule-core/3-impl-report.md:97`: the report says `meter_every` 5,000 gives
  `Decimal('5E+2')`. It gives `Decimal('500')` (from `Decimal(5000)`, an `int` or a DB value `5000.000` alike;
  checked with my script). Correct the line or remove it.

## Docs pass

The impl report's `## Docs updated` matches the diff and § Docs to keep current:

- `docs/Maintenance-Philosophy.md` § 7: the overdue rule is **Decided**, shutdown planning stays TBD (brief § 3).
- `docs/Plan.MD` § 4.3 *Triggers*: the *Calendar* bullet names years, the *Meter* bullet sends a crossed limit to a
  ticket, and the *Built (S095)* line names D4's two consequences for R03.3 and R03.7.
- `.claude/CLAUDE.md` § SMTW-Review: the *PM schedule (S095)* point, in Q4's words.
- No migration, so no schema docs. No device check, so no `docs/steps/device-checks.md` row.

## Manual checks for the user

None. The step has no screen (brief § 8.4), and the impl report's `## Manual checks` says so.

## Checked and found consistent

- Every rule of § 5.1: the key checks with their names, `ValueError` for a wrong value and `TypeError` for a wrong
  type, `type(x) is date`, `bool` refused as a number, `float` refused for every meter value, extra keys ignored,
  `before_use` ignoring the four trigger keys.
- § 5.2 the base: a done job wins over the seed; the seed date else `created_on`; the seed value else
  `start_meter`; a job's `done_meter` None gives `due_meter` None.
- § 5.3 `next_due`, `add_interval`, `window_days` and `upcoming_days`, the override rules (a trigger the plan
  lacks, `before_use`, BR1-09), and `rescheduled`.
- § 5.4 `job_state`: every boundary, the tie to CALENDAR (the meter wins only when strictly further), `trigger`
  None for *Not yet*, `no_reading`.
- § 5.5 `timeliness`, and the brief's T9 agreement.
- Every row E1–E22 of § 5.6 and T1–T10 of § 8.1 has a test that asserts the value, not only that a call
  returned.
- The `add_months` rename (D6): no other user of `_add_months` remains (`git grep`); the contracts tests run
  unchanged and green.
- Design: one pure module, no layer or flag with one use, no copy of an existing helper. Comments say why (the
  `datetime` subclass, the float comparison).
- Scope: nothing built outside the brief. The coder's decisions in § 4 of the report stay inside the brief's
  rules, and the report states them.
- Security, concurrency, a dead connection and the 503 path do not apply: no route, query or table.
- Track: full, as the brief says.
- The impl report keeps to scope A.

## Feedback

- none
