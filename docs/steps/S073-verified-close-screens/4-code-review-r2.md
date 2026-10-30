```
Step: S073 — Verified close: screens
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S073 — code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All four round-1 nits are fixed, and the fix
round brings in no new fault. This round has no new finding.

## Test results (my runs)

- Frontend suite, `tooling/run-frontend-tests.bat`: PASSED, 346 passed (344 in round 1, plus the two
  new tests of CR1-02). The fix round changed only `frontend/src` and `frontend/tests`, so the
  backend and tooling suites are not due.
- `npx vite build` in `frontend/`: built in 4 s, only the known chunk-size warning.
- Browser tests: none re-run. No finding of mine needs a run. The coder's targeted run is the right
  one: `e2e/improvements.spec.js` + `e2e/screens.spec.js`, 41 passed, 1 skipped. No shared frontend
  file changed (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, `e2e/support/`), so no
  whole-suite or WebKit run is due.

## Round-1 findings

| ID | Severity | Status | Check |
|---|---|---|---|
| CR1-01 | nit | Fixed | `.remark-text` is now in the `.problem-text, .analysis-text` selector list (`ImprovementDetailView.vue:469-475`); the repeated rule is gone. |
| CR1-02 | nit | Fixed | `machinesText` and `symptomsText` are in `improvementLabels.js:206-210`. `WatchCard.vue`, `WatchSummary.vue` and `figureRows` use them. No other join of machines or symptoms is left in `frontend/src`. Two new unit tests cover the join and the empty list. |
| CR1-03 | nit | Fixed | § 4 D-4 now states the real behaviour (`watch.from` is null outside *Watching*). |
| CR1-04 | nit | Fixed | `blank` is `() => ({ remark: "" })` / `() => ({ reason: "" })` in the three dialogs. Each `open()` calls `openCreate()` with no seed, so no caller loses a value. |

**Red, then green.** No test was added for a fault. The two new tests cover new helpers from a
refactor (CR1-02), so no red result is due. The fix round says so.

## Checked and found consistent

- The fix round's diff (`step_snapshot.py diff S073 --from-round 1`) matches the files its section
  lists. It also changes the S073 and S074 rows of `docs/steps/INDEX.md` (the orchestrator's status
  text).
- The helpers return the same text as the inline code they replace, so the rendered watch card,
  summary and table do not change.
- The impl report's Round 1 section is in scope A writing style. "Docs updated: none" is right: the
  round changes no behaviour, route, secret or schema.
- Files I re-read: `ImprovementDetailView.vue` (the style block), `VerifyDialog.vue`,
  `DropDialog.vue`, `ImprovementNoteDialog.vue` (the `blank` and `open`), `improvementLabels.js`
  (the new helpers), `3-impl-report.md` § 4 D-4 and § Fix rounds › Round 1.

## Manual browser check

Unchanged from round 1: the brief's real-device rows in `docs/steps/device-checks.md`.

## Feedback

- none
