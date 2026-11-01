```
Step: S090 — Contracts filters fit the phone's width
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: fix
Baseline: a6e3778
Status: Done (committed at adoption, 01-11-2026; no device check); was: Gate B 01-11-2026 (code review r1: no findings)
```

# S090 — Contracts filters fit the phone's width

Found by the pre-flight of `a6e3778` (`scratch/preflight/a6e3778.md`, bug 1). KLA, 01-11-2026: fix the code.

## The bug

On an iPhone, the Contracts list (Masters › Contracts) scrolls sideways when a vendor has a long name. S080 says
the list fits a phone with no sideways scroll (`frontend/e2e/contracts.spec.js:247`); the full run's
`[phone-webkit]` run of that test failed with "the screen scrolls sideways", 122 px.

## Steps to see it

1. Make a vendor with a long name (e.g. "E2E Vendor with a long name for the phone …", as `contracts.spec.js:655` does).
2. Open Masters › Contracts on `phone-webkit`. The page scrolls sideways.

## Cause

`frontend/src/views/masters/ContractsPanel.vue:133-144`: the four filters are
`form-select form-select-sm w-auto` in a `d-flex flex-wrap` row. `w-auto` sizes a select to its longest option,
and nothing caps it at the row's width, so the Vendor select grows past the screen edge on WebKit. In the failed
run the long-name vendor came from the S082 test in the same lane database; alone, S080 runs before it exists and
passes.

## The fix

- `ContractsPanel.vue`: add `mw-100` (Bootstrap: `max-width: 100%`) to the four filter selects, so a select is
  never wider than its row; the browser cuts a long option's text in the closed select.
- `contracts.spec.js` S080 list test (line 247): make its vendor's name long (at least 60 characters), so the
  test covers the case on every run and every device, not only after S082.

Not in this step: the same `w-auto` pattern on the Equipment list's filters (`EquipmentView.vue:355-389`); their
options are short codes and names today. Queued as an idea.

## Files

- `frontend/src/views/masters/ContractsPanel.vue`
- `frontend/e2e/contracts.spec.js`

## The test that fails on the bug

The S080 list test with the long vendor name fails on `phone-webkit` before the fix (sideways scroll) and passes
after it. Runs: `tooling/run-e2e-tests.bat e2e/contracts.spec.js:247 --project=phone-webkit` (Docker Desktop) red
then green; then the targeted run `tooling/run-e2e-tests.bat e2e/contracts.spec.js e2e/screens.spec.js`; unit
suites `YANTRA_TEST_RUN=s090c1 tooling/run-tests.bat`; build check `npx vite build` in `frontend/`.

## Review log

| ID | Finding | Answer |
|---|---|---|
