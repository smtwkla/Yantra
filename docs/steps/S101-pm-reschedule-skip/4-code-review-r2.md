```
Step: S101 — Reschedule and skip a PM job
Doc: code-review r2
Author: code reviewer (Opus)
Date: 02-11-2026
```

# S101 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-01 and CR1-02 are fixed. The fix round's diff brings in
no new fault. The four PM backend test files are green.

## Tests run

- `YANTRA_TEST_RUN=s101cr2 tooling/run-backend-tests.bat tests/test_pm_reschedule_api.py tests/test_pm_plans_api.py
  tests/test_pm_generate.py tests/test_pm_jobs_api.py`: PASSED, 117 passed (13 s).
- The full `run-tests.bat` was not run. The fix round changed only `backend/pm_plans.py`, one backend test file
  and one browser spec, so the backend files above cover it. The 120-character line limit holds in both changed
  `.py` files (checked by line length).
- Browser: none re-run. The coder's targeted run (`e2e/pm-reschedule.spec.js e2e/pm-plans.spec.js`: 15 passed)
  covers the changed spec and the plan screen, whose save route changed. No shared frontend file changed.
- Schema docs check: not due. The diff touches neither `backend/local_db.py` nor `docs/schema/`.

## Findings from earlier rounds

| ID | Severity | Status |
|---|---|---|
| CR1-01 | major | Fixed (verified) |
| CR1-02 | nit | Fixed (verified) |

**CR1-01.** `change_plan` now computes `schedule_changed` from the plan's own `changes` right after
`plan_changes`, before the item loop. The loop variable is `item_changes`, and `settle_plan_job` gets
`keep_reschedule=not schedule_changed`. I read the whole function for other effects of the rename. `changes` is
read only by `update_row(cur, "pm_plans", …)` and the flag, both before the loop. `item_changes` is read only in
the loop. Nothing after the loop read the rebound name besides the old flag expression, so the rename changes no
other behaviour.

The two new tests match both failure scenarios of round 1:
- `test_a_schedule_change_saved_with_an_item_edit_still_drops_it` saves `calendar_every` and an item's text
  together, and asserts the reschedule is gone and the last line is `due_changed` with `RESCHEDULE_DROPPED`.
- `test_an_item_only_edit_keeps_it_also_a_reading_items_meter` edits a check item's text and a reading item's
  meter (the reading item is last, so the old code would have read its meter fields). It asserts the reschedule
  stays and no line is added.

The report gives a red result for each, run before the fix: a kept reschedule for the first
(`assert datetime.date(2026, 11, 12) is None`), a dropped one for the second (`'NoneType' … isoformat`). Both
match what the old code does.

**CR1-02.** The skip test asserts `toContainText(/\b[1-9]\d* skipped\b/)` on `pm-counts`. The empty text "No PM
jobs are done or skipped yet." has no number before "skipped", so it no longer passes.

## Nits

- none

## Manual checks

No change from round 1. The impl report's `## Manual checks` still carries the three `[auto]` checks of § 8.4.
The optional manual browser check is unchanged: on a phone, check that the two buttons of *Reschedule or skip* fit
in one row, and that the phone's date picker opens from *New due date*.

## Checked and found consistent

- Files re-read: `backend/pm_plans.py` (`change_plan` in full), the two new tests in
  `backend/tests/test_pm_reschedule_api.py` with the helpers they import (`item_body`, `meter_of`, `change` in
  `test_pm_plans_api.py`), `frontend/e2e/pm-reschedule.spec.js` (the changed line), and `pm_plans_core.py`'s
  `SCHEDULE_FIELDS` and `METER_FIELDS`.
- The fix round's import change (`item_body` added) keeps the fixture import list intact.
- The report's fix-round section is in scope A and lists every changed file and the runs.

## Feedback

- none
