```
Step: S063 — Equipment category above the class
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 27-10-2026
```

# S063 — Code review, round 2 (verify fix round 1)

**Verdict: no `blocker` or `major` finding is open.** Fix round 1 answers every round-1 nit, and
it fixes the whole-suite failure. It brings in no new fault. CR1-03 stays open as a nit, held for
KLA at gate B. This round has no new finding.

## Scope of this review

- **Diff read:** `step_snapshot.py diff S063 --from-round 1` (the change since round 1). The
  status lines in `1-brief.md` and `docs/steps/INDEX.md` are the orchestrator's. I did not
  review them.
- **Files re-read:** `EquipmentCategoriesPanel.vue` (script and empty states, lines 1–75),
  the fix-round hunks of `equipmentFilters.js`, `EquipmentView.vue`, `masters.py`,
  `equipment.spec.js` and `equipmentFilters.test.js`, and `3-impl-report.md` § 4, § Tests and
  § Fix rounds.

## Tests

- **Unit suites** (`YANTRA_TEST_RUN=s063cr2 tooling\run-tests.bat`): **all PASSED**. Backend 3315
  passed, frontend 244 passed (one more than round 1: the new `activeFirstBy` test), tooling
  185 passed.
- **Build check** (`npx vite build` in `frontend/`): built. Only the known chunk-size warning.
- **Browser tests:** I ran none, because no finding of mine needs one. The fix round's targeted
  run names the right specs: `equipment` (the S012 test and `EquipmentView.vue`), `masters`
  (the categories panel), `asset-list`, and `screens`. It records 93 passed and 1 skipped (the
  existing skip). The orchestrator's targeted run after the fix gives the same counts.
- **Red, then green:** the whole-suite run in § Tests is the red result for the S012 fix. The test
  failed there, and the impl report names the cause. The `activeFirstBy` test covers a refactor,
  not a fault, so it needs no red result.

## Findings of round 1

| Finding | Status | Check |
|---|---|---|
| CR1-01 nit | Fixed | § 4 *Decisions taken* records the 409 and its reason. |
| CR1-02 nit | Fixed | The panel now shows three empty texts. "No active categories. Turn on Show inactive to see the others." shows when only inactive categories exist. The "Add one" text shows only with `equipment:edit`, and a plain line shows otherwise. The branches cannot reach `equipmentCategories.length` while the store is `null`, because the *Loading…* branch and the `!loadError` guard come first. |
| CR1-03 nit | Open, held for KLA at gate B | The text is the brief's (§ 5.2). The impl report proposes a new text. |
| CR1-04 nit | Fixed | The docstring is re-wrapped. The code is unchanged. |
| CR1-05 nit | Fixed | `activeFirstBy(records, key)` serves `classChoicesFor` and `categoryChoices`. It sorts a copy and returns `[]` for `null`. The new unit test asserts the order, that the input is not changed, and the `null` case. |
| Whole-suite failure | Fixed | The S012 test now finds the row by a cell whose name is exactly the maker's. So `propertySetup`'s makers, whose names start with the same text, no longer match. |

## Nits

None new.

## Checked and found consistent

- `activeFirstBy` gives the same order as the two blocks it replaces. Both blocks sorted
  active first, then by `code` (classes) or `name` (categories), with `localeCompare`.
- The new empty texts follow scope B. Each is short and plain, and it says what the user can do.
  "Show inactive" is the switch's own label.
- The impl report's § Tests now gives the whole-suite result (234 passed, 7 skipped, 1 failed),
  and it names the failure's cause and its fix. This closes the open item of round 1.
- The fix round's section lists its own test runs with real counts.

## Manual browser check

None new. The brief has no *On a real device* check (§ 8.5). KLA's choice on the CR1-03 text is
the only item left for gate B.

## Feedback

- waste: the first `diff --from-round 1` with a `--` path list printed the tool's help text instead of the diff, so I made one more full run of the diff and filtered it myself (1 run).
