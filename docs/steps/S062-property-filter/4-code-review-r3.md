```
Step: S062 — Filter the equipment list by property
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 27-10-2026
```

# S062 — Code review, round 3 (verify)

**Verdict: no blocker or major finding is open.** CR2-01 is fixed. The fix brings in no new
fault, and moving `ruleOf` to `ruleOfLine` changes no behaviour of *Apply filter*. D-1
(`router.push`) stays with the user; I did not reopen it.

Re-read: the fix round's diff of the three files it lists, against round 2's snapshot (12d87c9):
`frontend/src/views/equipment/PropertyFilterModal.vue`, `frontend/src/utils/propertyFilter.js` and
`frontend/tests/propertyFilter.test.js`. I also read the script of `PropertyFilterModal.vue` from
`lineOf` to `apply()` in full. The working tree matches the current snapshot `refs/steps/S062`
(d56175b) for these three files.

## Tests

- **Frontend unit suite** (`YANTRA_TEST_RUN=s062cr3 tooling/run-frontend-tests.bat`): PASSED,
  234 passed (21 s). The targeted file `tests/propertyFilter.test.js`: 39 passed.
- I did not run the backend and tooling suites. The fix round changed only frontend files, and
  the coder's all-suites run (`s062c3`) was green: backend 3262, frontend 234, tooling 185.
- **Browser tests:** I did not re-run them, because no finding of mine needs a run. The coder's
  targeted run names the right specs for a dialog change (`equipment.spec.js` and
  `screens.spec.js` at Normal): 61 passed, 1 skipped (an existing skip).

## Earlier findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 … CR1-06 | minor / nit | Fixed (round 2) | Not re-checked. |
| CR2-01 | minor | Fixed | See below. |

**CR2-01, how I checked it.**

- **No change gives `dirty` false, whatever the load order.** `open()` stores `initialMatch` and a
  deep copy of the lines (`PropertyFilterModal.vue:133-134`). `dirty` (lines 65-67) builds both
  sides with `filterSnapshot(…, dataTypeOf)` each time it is read. Both sides then use the same
  `byId` map: before the property read, after it, and when the read fails (`properties` stays
  `null`, so every data type is `undefined` on both sides). The JSON copy keeps the number types
  of `property_id` and `optionIds`, and every line field is defined, so the copy builds the same
  rule text as the live lines.
- **A real change gives `dirty` true.** A changed operator, value, low or high, option list,
  property, match, or a line added or removed changes the rule list of the live side only. One
  edge stays blind: before the property list arrives, a choice line's `optionIds` do not show in
  the rule (the data type is unknown). The user cannot change them then, because the dialog lists
  a choice's options from the same property list. So this edge is not reachable.
- **Apply is unchanged.** `ruleOfLine(line, dataType)` (`propertyFilter.js:107-115`) is the old
  `ruleOf` body line for line, with `dataTypeOf(line)` passed in. `ruleOf` in the component
  (line 61) passes `dataTypeOf(line)`, so `apply()`, `incomplete` and the check request build the
  same rules as before.
- **Red, then green.** The fix round gives the red result: the three new tests failed because
  `filterSnapshot` did not exist. The first test pins the fault itself (the same lines give
  different text with and without the data types). The wiring in the component (both sides
  through `filterSnapshot` at read time) has no test of its own; the fix round says why a browser
  test cannot reach the late load. I accept that for a minor fault.

## Findings

None.

## Nits

None.

## Checked and found consistent

- **The test file.** The three `filterSnapshot` tests cover the fault, the equal copy with and
  without data types, and a changed value and match.
- **Docs.** The fix round says "Docs updated: none". That is right: the fix changes how a dialog
  compares its state; no rule, API, secret or schema changed.
- **Manual checks.** No change since round 1.

## Manual browser check for the user

None.

## Feedback

- hindrance: `git diff refs/steps/S062` showed the step's untracked files as deleted, and the snapshot had moved to the fix round's state, so I diffed against round 2's commit 12d87c9 through `git show` copies (2 commands).
