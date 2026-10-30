```
Step: S076 — Improvement register
Doc: code-review
Round: 2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S076 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All five round-1 nits are fixed, and the fix round brings in no new finding.

## Test runs

- Unit suites, `YANTRA_TEST_RUN=s076cr2 tooling/run-tests.bat`: all green: backend 4051 passed (217 s), frontend
  368 passed, tooling 185 passed. (The frontend count includes tests the S077 coder is adding in the same tree.)
- `npx vite build` in `frontend/`: built; only the existing chunk-size warning.
- Browser: not re-run. No finding of mine needs a run. The coder's targeted run is the right one for this round:
  `e2e/improvement-register.spec.js` and `e2e/screens.spec.js`, 26 passed and 3 skipped (the device skips). The
  round did not touch `e2e/support/` or another shared file.

## Round-1 findings

| ID | Status | Verified |
|---|---|---|
| CR1-01 | Fixed | The month buttons are no longer disabled. `showMonth` uses `result.today`, and falls back to `istToday()` when no register has loaded. `istToday()` is UTC plus 5:30, sliced to `YYYY-MM-DD`, which is the shape `monthPeriod` reads. No IST-today helper exists in `frontend/src` to reuse. The new test opens a refused period, sees the 400 line and no sheet, then clicks *Show this month* and sees the month. The report gives the red result. |
| CR1-02 | Fixed | The controls block shows only when `!forbidden && !noUnits`. The operator test asserts no From field, no *Show this month* and no print help, and the report gives the red result. Keeping the controls on the 404 line is a reasoned choice, stated in the report. |
| CR1-03 | Fixed | The change is behaviour-neutral. `_register_closed` now selects `clp.id AS closed_by_person_id, clp.name AS closed_by_name`, the names `_closed` reads. `_closed` returns `None` only when `closed_at` is null, and the query filters `i.closed_at >= %s`, so it never returns `None` here. Each field equals the old expression: `at` is `plain["closed_at"]`; `by_name` is `closed_by_name or closed_by`; `by_lead` is the same person-id-equals-lead test; `remark` is `close_remark`. The Dropped rule (`by_lead` is `None`) stays in the register. No other column is renamed (`fu_id` and `fu_serial` are unchanged). |
| CR1-04 | Fixed | The test asserts `printed_by == "Test maintenance_team"`, the token's name. The report explains why it is not `world.person["name"]`: the route uses the login's name. |
| CR1-05 | Fixed | `test_a_bad_period_is_a_400_before_a_site_404` sends from after to with an unknown `site_id` and gets a 400 on `from`. The report gives the reason there is no red result: the test pins the existing order, and seeing it fail would need a change to the route. I accept that reason. |

## Checked and found consistent

The files I re-read for this round: the fix diff (`step_snapshot.py diff S076 --from-round 1`), `_closed` and
`_IMPROVEMENT_FROM` in `backend/improvements.py`, `load()` and the template states in
`frontend/src/views/ImprovementRegisterView.vue`, and `monthPeriod` in `frontend/src/utils/improvementRegister.js`.
The fix round's impl-report section is in scope A. It needs no docs change, because no documented behaviour
changed. The new e2e test is untagged and that is correct: it is a logic test. It allows its expected 400 through
`consoleWatch.allowFailedRequest`. The INDEX change is the orchestrator's status line.

## Manual browser check for the user

- Device-checks row 55 (important, IT Admin), unchanged from round 1: print one month's register on A4 portrait at
  100 % and check the columns, the wrapping, the repeated header row and the review lines on paper.

## Feedback

- none
