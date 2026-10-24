```
Step: S041 — S033's e2e test isolated from the seed extruder
Doc: impl report
Author: Coder
Date: 24-10-2026
Track: fix
```

# S041 — Impl report

Result: the S033 test now adds its part under its own machine. The full e2e suite shows the 10 S035 failures gone. One unrelated phone-webkit test failed once and passed on rerun.

## What was built
`frontend/e2e/equipment.spec.js`, test "S033: engineer adds a component-unit with No model …": it calls `createEquipment("E2E no-model parent <project>")` (the helper the spec already uses) and opens that machine's page, not the seed extruder's. Nothing else in the test changed. The unused `seedIds` import was removed. No app code changed.

## Why
The old test added a part under the shared seed extruder. `labels.spec.js` and `screens.spec.js` expect "2 labels on 1 sheet" for the extruder and its gearbox. After the part was added there were 3.

## Other tests that add nodes under a seed node
None. Greps of `frontend/e2e/` for `seedIds` / `seed.extruder`, "Add part" and `POST /api/equipment`:
- `equipment.spec.js` (S033): the one found, fixed.
- `labels.spec.js:23` posts equipment at the spare unit, not under a seed node.
- `tickets-parts.spec.js` "Add part" is the ticket's parts-used line, not a node.
- The other uses of `seed.extruder` only raise tickets or read.

## Tests
- Full e2e, `tooling/run-e2e-tests.bat`, 6 lanes: 296 passed, 1 failed, 6 skipped, 303 total (4.1 min). Includes S035's router, App.vue, navigation and me.spec.js changes.
  - Failed: `tickets-parts.spec.js:129` "S020: technician adds a part line the short way …", phone-webkit. Timeout at line 167: the "Yes" button "was detached from the DOM, retrying". Not this test, not the labels or screens specs. Rerun of `tickets-parts.spec.js` and `equipment.spec.js` on phone-webkit (`E2E_LANES=1`): 18 passed. Judged a webkit flake; not fixed, as instructed.
  - `labels.spec.js:69` and the `/labels?ids=1&parts=1` screen checks: green on all projects.
  - Red before the fix: S035 CR2-01's run (10 failed). I did not re-run the old code.
- `YANTRA_TEST_RUN=s041c1 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 139, deps 42, tooling 106.

## Files touched
1 file: `frontend/e2e/equipment.spec.js` (plus this report and the brief's Status).

## Decisions taken
- Used the existing `createEquipment` (admin API, unit SMTW.MCC1, Atlas Copco GA37). The parent name carries the project name, as the other tests do.

## Not done / assumed
- The 6 skipped tests are in the suite's existing skips; I did not look into them.
- The webkit flake at `tickets-parts.spec.js:167` is for the orchestrator to judge.

## Manual checks
None.

## Fix rounds

### Round 1

- CR1-01 (minor): Fixed — the header block added (by the orchestrator; a docs-only fix, no new review).
