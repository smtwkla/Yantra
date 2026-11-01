```
Step: S090 — Contracts filters fit the phone's width
Doc: impl report
Author: Coder (Sonnet)
Date: 01-11-2026
```

# S090 — Implementation report

## What was built
The four filter selects on Masters › Contracts (Site, Type, Status, Vendor) can no longer be wider than their row, so a long vendor name no longer makes the list scroll sideways on an iPhone.

## How it works
`ContractsPanel.vue`: `mw-100` (`max-width: 100%`) was added to the four `form-select form-select-sm w-auto` selects. `w-auto` still sizes a select to its longest option, but the cap cuts it at the row width; the browser clips the text in the closed select.

## Red, then green
- Test change: the S080 list test's vendor is now `E2E Vendor with a long name for the phone list to fit ${tag}` (more than 60 characters). Its later assertions use `vendor.name` through `toHaveText` on the DOM text, which CSS clipping does not change, so they hold.
- Red (fix not applied): `tooling/run-e2e-tests.bat e2e/contracts.spec.js:247 --project=phone-webkit` failed: "the screen scrolls sideways", received 153 px, expected <= 1.
- Green (fix applied): same command, 1 passed.

## Files touched (2)
- `frontend/src/views/masters/ContractsPanel.vue`: `mw-100` on four selects.
- `frontend/e2e/contracts.spec.js`: longer vendor name in the S080 list test.
Line endings kept (both files `i/lf w/lf`).

## Decisions taken
None beyond the brief.

## Not done
The same `w-auto` pattern in `EquipmentView.vue` stays out (brief: queued as an idea).

## Tests run
- Targeted `e2e/contracts.spec.js e2e/screens.spec.js` (Normal): 69 passed, 1 skipped.
- `npx vite build` in `frontend/`: built (chunk-size warning only, as before).
- `YANTRA_TEST_RUN=s090c1 tooling/run-tests.bat`: backend 4467 passed, frontend 412 passed, tooling 231 passed.
- No whole-suite browser run: the change touches one view and one spec, no shared frontend file.

## Docs updated
None, because no migration, module behaviour, invariant, secret or role changed.

## Manual checks
- [auto] The Contracts list fits a phone with a long vendor name, no sideways scroll — frontend/e2e/contracts.spec.js::S080: the Contracts list fits a phone with no sideways scroll (passed on phone-webkit alone, and in the targeted run on phone-chromium and desktop-chromium)

## Feedback
- none
