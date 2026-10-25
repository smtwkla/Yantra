```
Step: S050 — Meter reading register
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S050 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All six findings of round 1 are fixed. The fix round brings in one nit (a misplaced template comment). The suites are green.

Code read from the snapshot `refs/steps/S050` (2e0e28f), not the working tree. Files re-read in full: `frontend/src/views/readings/ReadingsRegister.vue`, `frontend/src/components/EquipmentPicker.vue`. Files re-read in the fix round's parts: `frontend/src/views/RaiseTicketView.vue` (script head and template), `frontend/src/views/equipment/MetersCard.vue`, `frontend/src/views/equipment/ReadingHistoryModal.vue`, `frontend/src/utils/meterLabels.js`, `frontend/tests/meterLabels.test.js`, `frontend/e2e/readings.spec.js` (the S050 block), `frontend/e2e/tickets-raise.spec.js` (the new test), and the impl report's `## Fix rounds`.

## Tests run

- `YANTRA_TEST_RUN=s050cr2 tooling/run-tests.bat`, on a temporary worktree of `refs/steps/S050`: backend 3054 passed, frontend 175 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- `npx vite build` in the worktree's `frontend/`: built; only the existing chunk-size warning.
- Browser tests: not re-run (standing rule). The coder's targeted run at Normal covers `readings`, `tickets-raise`, `equipment` and `screens`: 111 passed, 1 skipped (S040's bottom-bar guard on desktop). These are the right specs. The register changed (`readings`), the raise screen changed (`tickets-raise`), and the Meters card is on the equipment page (`equipment`). No shared frontend code changed, so no whole-suite run is due. No finding of mine needs a browser run.

## Round 1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | The picker stays mounted and hides with `v-show`: `RaiseTicketView.vue:284` (`!ticket && !nodeId`), `ReadingsRegister.vue:150` (`nodeId === null \|\| notFound`). The raise screen's branches stay in step: the node branch is now `v-else-if="nodeId"` (`:316`), and *Pick other equipment* and *Change* both call `chooseEquipment(null)`, so the search comes back with its text. The register now has one picker; a pick from the not-found state reloads and clears `notFound` in `load()`. Both e2e tests assert the text and the match after *Change*. The red result is given (`Expected: "E2E extruder"  Received: ""`). |
| CR1-02 | minor | Fixed | `failedPage` keeps the page that failed. Page 1's alert stays at the top (`:157`). A later page's alert and *Try again* sit under the table in place of *Show more* (`:239-245`). *Try again* asks for the failed page, and a tick or node change starts from page 1 and clears the error. The test answers page 2 with 503, asserts the line is in the viewport and *Show more* is gone, then loads all 32 rows. The red result is given. |
| CR1-03 | minor | Fixed | One `readingBadgeClass` in `meterLabels.js:88`, used at `ReadingHistoryModal.vue:118` and `ReadingsRegister.vue:231`. The local copies and the now-unused `RESET_LABEL` import are gone. It has a unit test. No red result, with a reason (the export did not exist before): accepted. |
| CR1-04 | nit | Fixed | *Open register* is `btn touch-target` (`MetersCard.vue:119`), the scoped class *Log reading* uses on the same card. |
| CR1-05 | nit | Fixed | `:aria-controls` is set only while the panel exists (`ReadingsRegister.vue:185`). |
| CR1-06 | nit | Fixed | `readings.spec.js`, the test "a link to a machine that does not exist…", asserts the § 1.7 text word for word, the visible search and no empty-state line. It passed at once, with a reason (existing behaviour): accepted. |

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR2-01** (nit) `frontend/src/views/RaiseTicketView.vue:281`: the comment `<!-- Step 2: saved; add photos -->` now sits above the picker's *Step 1* comment, not above `<template v-if="ticket">`. Move it down one element.

## Manual checks (for the user)

- None on a real device (§ 8.5), unchanged from round 1.
- At gate B, if KLA wants to, on the raise screen: pick a machine, tap *Change*, and see the earlier search and its matches. The `tickets-raise` test covers this.

The impl report's `## Manual checks` still carries every important check of § 8.4 as `[auto]`. The fix round added tests but no new check of the brief, so no new row is due.

## Checked and found consistent

- **The fix round's scope.** It touches only the eight files the report lists. It changes no route, no API shape and no wording the brief gives. The one decision (one picker on the register) is stated in the report.
- **The register's states after the change.** No node: the picker and the empty line. Not found: the alert, then the picker, with no empty line; Back to no node hides the stale alert (`notFound && nodeId !== null`). A node: the picker hidden, its text kept. A page-1 failure: the top alert and *Loading…* on *Try again*. A later-page failure: the rows kept, the line under the table.
- **The raise screen.** A QR arrival (`?equipment=`) mounts the hidden picker with empty text, so no search runs. After Save the picker stays hidden (`!ticket`). The input id `equipment-search` is used once per page.
- **The e2e tests.** The 503 route pattern `?*page=2*` matches `?page=2&…`, and `consoleWatch.allowFailedRequest` names the expected 503 and 404. Each new test asserts what the user sees.
- **The docs pass.** The fix round changes no behaviour a doc describes; "Docs updated: none" is right.
- **Writing style.** The fix round adds no new screen text. The report's fix section follows scope A.

## Summary for the orchestrator

- Wrote `docs/steps/S050-reading-register/4-code-review-r2.md`.
- Tests: `run-tests.bat` (s050cr2, on the snapshot worktree) all four suites PASSED (3054 / 175 / 42 / 168); `vite build` OK; e2e not re-run.
- Findings: 0 blocker, 0 major, 0 minor, 1 nit (CR2-01). CR1-01…CR1-06 are all fixed.
- No blocker or major finding is open.
