# S100 — Implementation report

## What was built
Three tests now check only the state they make themselves. No code outside tests changed.

## How it works
1. `backend/tests/test_equipment_api.py::test_search_words_in_any_order`: the "finds nothing" word is `nomatch` instead of `999`, as `test_search_uses_at_most_eight_words` already does.
2. `frontend/e2e/improvements.spec.js`: the S068 test is now titled "…Closed leaves it out". After choosing *Closed improvements* it checks the State box shows that choice and that this test's own row (`row`) has count 0. It no longer expects the text "No closed improvements yet.".
3. `frontend/e2e/labels.spec.js`: the labels test opens `/equipment?q=${encodeURIComponent(seed.extruder.code)}`, so the extruder row is on page 1 whatever machines other tests made.

## Files touched (3)
- `backend/tests/test_equipment_api.py` — one word.
- `frontend/e2e/improvements.spec.js` — title and the Closed assertion.
- `frontend/e2e/labels.spec.js` — the start URL.

## Decisions taken
- In the S068 test I added one line that checks the State filter really shows "Closed improvements" before the row count, so the count-0 check cannot pass on the wrong list.
- Brief status and INDEX row set to `In code review`.

## Red evidence
- Bug 1: I temporarily added a node named "THROWAWAY press 999" to the test. With the old word: `assert [3] == []` (fails). With `nomatch` and the same node: passes. Then I removed the throwaway node.
- Bugs 2 and 3: red only in a whole run (order dependent); not made red locally. Evidence is the brief's runs (S097 lane 5, S098 72 machines). Green runs below.

## Tests run (`YANTRA_TEST_RUN=s100c1`)
- `tooling/run-backend-tests.bat tests/test_equipment_api.py`: 215 passed.
- `e2e/improvements.spec.js e2e/labels.spec.js` (Normal): 31 passed, 1 skipped.
- One lane, `e2e/improvement-register.spec.js e2e/improvements.spec.js --project=phone-chromium`: 33 passed, 1 skipped (S076's drop ran before S068's test; S068 passed).
- `e2e/labels.spec.js --project=desktop-chromium`: 6 passed.
- Full unit suites (`tooling/run-tests.bat`): see the summary line below.

Full run: backend 5165 passed (178 s), frontend 451 passed, tooling 239 passed; all suites passed.

## Docs updated
None, because only three tests changed (no migration, no rule, no screen).

## Manual checks
None in the brief.

## Feedback
- none

## Fix round 1 (by the orchestrator, 02-11-2026)

- CR1-01 (minor): the S068 test also checks the Closed list loaded: its empty text or a row shows, and no `.alert-danger`. `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/improvement-register.spec.js e2e/improvements.spec.js --project=phone-chromium`: 33 passed, 1 skipped (S076's drop runs first).
- CR1-02 (nit): noted; no change (the brief allowed the whole-run evidence).
- Only a test file changed, so no new review is due.
