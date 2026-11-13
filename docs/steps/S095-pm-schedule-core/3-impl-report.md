```
Step: S095 — PM scheduling core
Doc: impl-report
Author: Coder (Opus)
Date: 01-11-2026
```

# S095 — implementation report

**Result:** `backend/pm_schedule_core.py` is built as the brief's § 5 says, with 137 unit tests (every row of
§ 5.6, T1–T10). The tests were written first and shown red. The unit suites have one failure, which is not
S095's: an S092 equipment-search test that fails when a generated node code holds `999` (§ 5 below). It
passed when run again.

## 1. What was built

- One pure module, `backend/pm_schedule_core.py`, that answers three questions for R03:
  - `next_due(plan, last_job=None, start_meter=None, override=None) -> Due`: the next due date, the next due
    meter value, or both, with the windows;
  - `job_state(due, reading_value, today) -> Standing`: *Not yet*, *Upcoming*, *Due* or *Overdue*, the trigger
    that gave it, and "No reading yet";
  - `timeliness(due, done_on, done_meter) -> "on_time" | "late" | None`.
- The helpers `add_interval`, `window_days` and `upcoming_days`, and the constants of § 5.1 (`KINDS`,
  `CALENDAR_UNITS`, the states, the window numbers). S096 imports `KINDS` and `CALENDAR_UNITS`.
- `contracts_core._add_months` is now the public `add_months` (D6). Its behaviour is unchanged.
- No screen, route, table or task changes.

## 2. How it works

- **Checking the plan** (`_check_plan`). First `trigger_kind` must be in `KINDS`. A row with only `kind` fails
  here. `created_on` is required and `last_done_on` is optional, and both must be a plain `date`
  (`type(x) is date`). For `calendar` and `both`, `calendar_every` must be an `int` ≥ 1 (not a `bool`) and
  `calendar_unit` must be in `CALENDAR_UNITS`. For `meter` and `both`, `meter_type_id` must be set,
  `meter_every` must be > 0 and `last_done_meter` must be ≥ 0. A trigger key that is set on a plan without that
  trigger raises an error. A `before_use` plan stops after the dates, so it ignores the four trigger keys, set
  or not, valid or not (T10). Each error names its key: `ValueError` for a wrong value, `TypeError` for a wrong
  type.
- **Meter values** go through `_meter_value`. It accepts a `Decimal` or an `int`, which it turns into a
  `Decimal`. A `bool`, a `float` or anything else raises `TypeError` naming the key. So an int input still
  gives `Decimal` results.
- **The base** (`_base`, § 5.2):
  - when a last job exists, the base is its done date and its meter value;
  - otherwise the base date is the seed date, else `created_on`;
  - otherwise the base meter value is the seed value, else `start_meter`.
  - A plan with no meter trigger ignores every meter input: `last_done_meter`, `start_meter` and the job's
    `done_meter`.
- **Calendar.** `add_interval` adds the interval:
  - days and weeks with `timedelta`;
  - months with `add_months`, and years as 12 months.
  - The interval in actual days gives `grace_days = max(1, days // 10)` and `upcoming_days = min(7, grace)`.
- **Meter.** `meter_window = meter_every / 10`, exact in `Decimal`. `due_meter = base + meter_every`, or None
  when the base value is None.
- **Override.** A `due_on` or `due_meter` that is set replaces the computed value. The windows stay those of
  the computed interval (D5). An override for a trigger the plan lacks raises an error, and so does any
  override on `before_use`, also `{}`. `rescheduled` is True when either value is set.
- **`job_state`.**
  - The calendar state comes from `D − U`, `D` and `D + G`, and the meter state from `M − W`, `M` and `M + W`
    (§ 5.4).
  - The meter state replaces the calendar state only when it is strictly further, so a tie goes to the
    calendar.
  - A meter trigger with no due value or no reading gives no state and sets `no_reading`.
  - `trigger` is None whenever the state is *Not yet*.
- **`timeliness`** returns LATE when the done date is past `due_on + grace`, or when the done meter value is
  past `due_meter + window`. Otherwise it returns ON_TIME, and for `before_use` it returns None. T9 tests over
  the windows of E1, E10 and E12 that LATE comes exactly when the state is OVERDUE.

## 3. Files touched

| File | Change |
|---|---|
| `backend/pm_schedule_core.py` | New: constants, `Due`, `Standing`, `add_interval`, `window_days`, `upcoming_days`, `next_due`, `job_state`, `timeliness`. |
| `backend/tests/test_pm_schedule_core.py` | New: 137 tests, E1–E22 and T1–T10. |
| `backend/contracts_core.py` | `_add_months` renamed to `add_months`; its one call in `renewal_period` follows; the docstring names its second user. |
| `backend/tests/test_contracts_core.py` | The import and `test_add_months_keeps_the_month_end` use `add_months`. |
| `docs/Maintenance-Philosophy.md` | § 7: the overdue TBD is now **Decided** (Docs updated). |
| `docs/Plan.MD` | § 4.3 *Triggers*: the *Calendar* and *Meter* bullets, and the *Built (S095)* line. |
| `.claude/CLAUDE.md` | § SMTW-Review: the *PM schedule (S095)* point (Q4). |
| `docs/steps/S095-pm-schedule-core/1-brief.md`, `docs/steps/INDEX.md` | Status `In code review`. |

## 4. Decisions taken

- **Base date "or".** The seed date falls back with `plan.get("last_done_on") or plan["created_on"]`. A `date`
  is never false, so the `or` is safe.
- **Meter inputs on a plan with no meter are ignored, not type-checked.** This covers `last_done_meter`
  (§ 5.1 says it is ignored), `start_meter` and `last_job["done_meter"]`. A calendar plan's shell may pass a
  leftover value. `reading_value` and `timeliness`'s `done_meter` are always type-checked, because they are
  inputs of the call itself.
- **`last_job["done_on"]` None raises `ValueError`, and `timeliness(done_on=None)` does too.** Both are
  required dates. Their key names in the messages are `last_job['done_on']` and `done_on`.
- **The before-use path checks only `trigger_kind`, `created_on` and `last_done_on`.** It does not check
  `last_job` or `start_meter`, since it never uses them.
- **An override `{}`, or one with both values None, on a calendar or meter plan** is not a reschedule:
  `rescheduled` is False. An override `{}` on `before_use` still raises, because § 5.3 says "must be None".
- **The *Meter* bullet of Plan.MD § 4.3** lost "or when a reading crosses a limit". It now reads "Reaching the
  due value creates a PM job". The limit sentence moved to a ticket (BR1-06). This is the brief's § 3 edit; I
  chose the words.
- **`meter_window` comes from `meter_every / WINDOW_DIVISOR`** as the brief writes it. For 5,000 it is
  `Decimal('500')` (CR1-02: the earlier text said `Decimal('5E+2')`, which was wrong). A screen that prints it should format it, which is the shell's job and
  not S095's.
- No departure from the brief.

## 5. Not done, deferred or assumed

- **Outside S095, for the orchestrator:** `tests/test_equipment_api.py::TestTypeFilterAndSearch::test_search_words_in_any_order`
  (S092) failed once in the full run with `assert [137] == []` on `q="press 999"`. The likely cause, an
  assumption:
  - a node's code ends with a database serial;
  - the worker databases are kept between runs, so the serial keeps growing;
  - so a node code that holds `999` matches the "no match" word.
  - The test passed when run again (214 passed). It will fail again whenever the serial passes a `…999…` value.
  - A fix (a word no code can hold, e.g. `press zzzq`) belongs to a fix-lane step. I did not change it,
    because it is out of scope.
- The § 5.2 shell rule (the meter value at a time), the counter reset (A3) and N1 are for R03.3, as the brief
  says.
- The acceptance grep: `pm_schedule_core.py` imports only `dataclasses`, `datetime` (`date`, `timedelta`),
  `decimal` and `contracts_core.add_months`. It has no Flask, no DB, no `now()` and no `today()`.

## Tests

- Red first: `tooling/run-backend-tests.bat tests/test_pm_schedule_core.py tests/test_contracts_core.py` gave
  `ModuleNotFoundError: No module named 'pm_schedule_core'`, with the contracts tests at 101 passed.
- Green: the same command gave 238 passed (137 new and 101 contracts).
- Full run, `YANTRA_TEST_RUN=s095c1 tooling/run-tests.bat`:
  - backend: 4607 passed, 1 failed (the S092 test of § 5);
  - frontend: 412 passed;
  - tooling: 239 passed, with the line width included.
- Re-run: `tooling/run-backend-tests.bat tests/test_equipment_api.py` gave 214 passed.
- No browser run, frontend build or schema docs check: the step changes no screen, API or migration (§ 8.3).

## Manual checks

None: the step has no screen (§ 8.4). There is no device-check row.

## Docs updated

- `docs/Maintenance-Philosophy.md` § 7: the overdue rule is **Decided**. It holds the 10 % window rounded down,
  at least 1 day, the meter window, late on either trigger, and *Due* through the window with *Overdue* after
  it. Shutdown planning stays TBD.
- `docs/Plan.MD` § 4.3 *Triggers*:
  - *Calendar*: "days / weeks / months / years";
  - *Meter*: a crossed limit raises a ticket, not a PM job;
  - a new *Built (S095, 01-11-2026)* line: month arithmetic, the seed, whichever first, the windows, and D4's
    departure with its two consequences for R03.3 and R03.7.
- `.claude/CLAUDE.md` § SMTW-Review: the *PM schedule (S095)* point, with the brief's Q4 words.
- No schema docs (no migration). No `docs/steps/device-checks.md` row.

## Fix round 1 (by the orchestrator, 01-11-2026)

- CR1-01: the missing space after the comma in `backend/tests/test_pm_schedule_core.py:26`.
- CR1-02: § 4 now says `Decimal('500')`.
- Only a test file and this report changed, so no new review is due (step skill § Phase 2 step 3).

## Feedback

- waste: the full backend run went red on an S092 test that has nothing to do with this step, and finding that
  out took a log read, a re-run and a fixture read (`test_equipment_api.py::test_search_words_in_any_order`,
  about 3 min).
- idea: the always-red risk of tests that search for digits against growing DB serials could be a line in the
  test conventions. A "no match" search word should be one that no generated code can hold
  (`backend/tests/conftest.py` `Uniq`, node serials).
