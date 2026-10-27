Step: S061 — Properties for every class, and a GPS location
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 27-10-2026

# S061 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All six findings of round 1 are fixed, and
I found no new finding. All three unit suites pass and the build check passes.

## Test run

- `YANTRA_TEST_RUN=s061cr2 tooling/run-tests.bat`: backend PASSED, 3171 passed; frontend PASSED,
  192 passed; tooling PASSED, 185 passed (ALL SUITES: PASSED). The backend count is round 1's
  3169 plus the two new `test_refusals` cases.
- `npx vite build` in `frontend/`: built, with only the existing chunk-size warning.
- Browser tests: I ran none, because no finding of mine needs a run. The fix round's targeted run
  (`equipment.spec.js`, `masters.spec.js`, `screens.spec.js`: 77 passed, 1 skipped, 0 failed)
  names the right specs: `PropertyInput.vue` is used by the equipment dialogs, and
  `PropertiesPanel.vue` is a Masters screen. No whole-suite run, as a fix round should.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `_parse_geo` (`backend/properties_core.py:333-339`) checks both ranges on the unrounded `Decimal`s, then rounds. The 25-digit inputs now get `LATITUDE_RANGE` and `LONGITUDE_RANGE`. Two cases in `test_refusals` (`test_properties_core.py:425`); the report gives their red result (`InvalidOperation`, 2 failed). |
| CR1-02 | minor | Fixed | `PropertyInput.vue:123`: the button has no `btn-sm`. |
| CR1-03 | nit | Fixed | `PropertyInput.vue:121-128`: the `error` line comes right after the input; the button, its error and the accuracy line follow it. |
| CR1-04 | nit | Fixed | `PropertiesPanel.vue:283` reads "Each machine gets its own value, for example where it stands. Models do not hold it." No e2e test matched the old text. |
| CR1-05 | nit | Fixed | The button reads "Finding the location…" while `locating` is true. `accuracyShown` shows the line only while the input holds `locatedText`, so a typed value hides it. The report says why no red test exists (no component test harness for `PropertyInput`); that reason is acceptable for two display details. |
| CR1-06 | nit | Fixed | `docs/schema.html` has no escaped empty line (`\n\n`) inside the `TABS` JSON any more; the four location columns and the two flags are still in the Equipment tab. |

## Findings

None.

## Checked and found consistent

- The fix round's own diff: the range check before `quantize` keeps the same messages and the
  same rounding for every valid input; the regex still refuses signs other than `-`, exponents
  and three numbers, so no `NaN` or `Infinity` reaches `Decimal`.
- `PropertyInput.vue`: the location's error line under the button keeps `invalid-feedback
  d-block`, as the field's own error does. The `hint` line still comes last for every type.
- Docs: the fix round changed only `schema.html` (CR1-06) and lists it under its own
  `### Docs updated (round 1)`. No other doc is due.
- Files I re-read: `backend/properties_core.py` (`_parse_geo` and `parse_value`),
  `backend/tests/test_properties_core.py` (the geo refusals), `frontend/src/components/PropertyInput.vue`
  (whole file), `frontend/src/views/masters/PropertiesPanel.vue` (line 283), and the `TABS` text
  of `docs/schema.html`. The snapshot `refs/steps/S061` already holds the fix round, so I read the
  fixed files rather than a diff.

## Manual browser check (for the user)

- None beyond the device checks: rows 41–43 of `docs/steps/device-checks.md`, done by IT Admin on
  production after the deploy. The bigger button and the "Finding the location…" text are part of
  what those rows look at on a real phone.

## Feedback

- hindrance: the snapshot `refs/steps/S061` was taken after the fix round, so no ref holds the round-1 state, and the fix round's own diff could not be shown with `git diff` (read the five files instead, about 2 min).
- idea: the step snapshot could keep one ref per round (e.g. `refs/steps/S061-r1`), so a verify round diffs exactly the fix round's change.
