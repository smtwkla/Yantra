```
Step: S096 — PM plans on a machine
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 02-11-2026
```

# S096 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All four round-1 findings are fixed. The fix
round brings in no new fault; one nit on a test's set-up.

## Tests run

- `YANTRA_TEST_RUN=s096cr2 tooling/run-backend-tests.bat tests/test_pm_plans_api.py`: **48 passed**
  (the new CR1-02 test included).
- `tooling/run-frontend-tests.bat`: **429 passed**.
- The round changed no code outside `PmPlanView.vue` and two test files, so the full
  `run-tests.bat` is not needed. I did not repeat `npx vite build`: the coder's build passed, and
  the working tree now holds S097's files too.
- Browser: none re-run. No finding of mine needs a run. The coder ran the right targeted specs
  (`pm-plans.spec.js`, `screens.spec.js`, Normal): 29 passed, 1 skipped, 0 failed.

## Round-1 findings

| ID | Status | Verified |
|---|---|---|
| CR1-01 (minor) | Fixed | `load()` sets `forbidden` and returns on a scrapped node, before `loadEditing`. The page shows "You can't add PM plans here." with *Back to the equipment*, so the read-only branches never render with `plan` null. `canEdit` is now always true on a new plan, which is right after the guard. The test asserts the text and the link; red without the fix is reported. |
| CR1-02 (nit) | Fixed | `TestChange::test_a_meter_removed_from_the_node_is_refused_when_sent_again` removes the plan's own meter, gets 400 on `meter_type_id` with `METER_FROM_LIST`, and `{active: false}` alone still passes. No red run is possible, because the test pins a rule the code already had; the report says so. |
| CR1-03 (nit) | Fixed | The label is *Meter reading then*. |
| CR1-04 (nit) | Fixed | `lostItemNumbers` marks each reading item whose meter is not among `choices`, for editors only. The page shows one warning above the list ("Item 1: the meter is no longer on this machine. Open the item and choose another meter.") and outlines the row in the table and the list (`isMarkedRow`). The mark clears after the engineer picks a new meter: the dialog emits the item the API answers, with its new `meter`. The test asserts the warning text; red without the fix is reported. |

## Nits

- **CR2-01** (nit) `frontend/e2e/pm-plans.spec.js` (test *CR1-04*): `apiAs("admin")` is used for the
  meter-types `GET` and never disposed. Use a `try … finally api.dispose()` as `adminPut` does, or
  read the types inside `adminPut`'s pattern.

## Checked and found consistent

- The fix round's diff (`step_snapshot.py diff S096 --from-round 1`): `PmPlanView.vue`,
  `pm-plans.spec.js` and `test_pm_plans_api.py`, read in full where they changed.
- `isMarkedRow` reads `refusedItem`, which is declared after it; this is safe, because it is
  called only at render time.
- The new screen texts follow scope B: one short line, what is wrong and what to do. The item
  warning uses the same words as the plan's meter warning ("is no longer on this machine").
- The new tests are logic tests and carry no `@device` tag, as the rule asks.
- Docs: none due. The round changes one page's texts and guards only.
- Files re-read: `frontend/src/views/PmPlanView.vue` (the load, the computed values and the items
  card), `frontend/src/views/equipment/PmItemDialog.vue` (the save path) and
  `frontend/src/utils/pmLabels.js` (`itemForm`, `itemBody`).

## Manual browser check for the user

None required: every check is automated. At gate B, KLA may open one plan on a phone (brief § 8.6).

## Feedback

- none
