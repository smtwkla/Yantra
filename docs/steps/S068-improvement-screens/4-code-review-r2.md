```
Step: S068 — Improvement record: screens
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S068 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01 and the nits
CR1-02…05 and CR1-07, and keeps CR1-06 as a reported departure (D-9). It brings in one new nit
(CR2-01).

## Test runs (mine)

- **Frontend unit suite** (`YANTRA_TEST_RUN=s068cr2 tooling/run-frontend-tests.bat`): 298 passed.
  No backend or tooling file changed in the fix round, so I did not run those suites.
- **Browser, targeted** (`tooling/run-e2e-tests.bat e2e/tickets-work.spec.js`): 36 passed,
  1 skipped (67 s). The fix changed `TicketDetailView.vue` after the coder's last `tickets-work`
  run, so this run was due.
- **Browser, WebKit** (`tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`):
  9 passed (1.2 min). The fix changed `e2e/support/improvements.js`, so the *Shared code* setting
  asks for this run.
- The coder's runs: the operator test alone, red before the fix and green after, and
  `improvements` with `screens` (24 passed, 1 skipped). `npx vite build` clean. These are the right
  specs for the fix.

## Findings of round 1

| ID | Severity | Status |
|---|---|---|
| CR1-01 | major | Fixed. The button shows on `canEdit && t.removable` (`ImprovementDetailView.vue:173`). The operator test adds a second ticket by API, checks both rows show, and records the red result (Expected 0, Received 2). |
| CR1-02 | nit | Fixed. The allowed 409 names `/api/improvements/${improvement.id}/tickets`, set after the improvement exists. |
| CR1-03 | nit | Fixed, with a side effect: CR2-01. |
| CR1-04 | nit | Fixed. `loadingLeads` is exposed; the *Start improvement* button is disabled and shows a spinner until the dialog opens. The `finally` resets it when the load throws. |
| CR1-05 | nit | Fixed. D-1 and § 5 record the WebKit run. |
| CR1-06 | nit | Kept as departure D-9, as suggested. |
| CR1-07 | nit | Fixed. Both *Add ticket* tests wait for the first radio, then call `expectDialogFits`. |

## Nits

- **CR2-01** (nit) `frontend/src/views/improvements/ImprovementDialog.vue:47`: while `leadsError` is
  set in an edit, the current lead now has no option, so the *Lead* select shows blank although
  `form.lead_id` still holds the lead and a save keeps them. Show the current lead's plain name
  (no "(not a lead now)" mark) in that case, so the select shows what will be saved.

## Manual browser checks for the user

- None important. Row 49 of `docs/steps/device-checks.md` (the Tamil problem text) stays a plain
  real-device check.

## Checked and found consistent

- **Files re-read:** the fix round's diff (`step_snapshot.py diff S068 --from-round 1`) and
  `ImprovementDialog.vue` in full. The `docs/roadmap/`, `INDEX.md` and S070/S071 changes in that diff
  belong to other steps.
- **Exposed ref:** `improvementDialog?.loadingLeads` reads the unwrapped value through the
  component's expose proxy. The `?.` covers the first render, before the ref is set.
- **New helper:** `addTicketByApi` follows `startImprovementByApi` (one API context as the engineer,
  status asserted, disposed in `finally`). It is not a copy of an existing helper.
- **Red, then green:** CR1-01's changed test carries its red result. CR1-02 and CR1-07 change only
  test set-up and need none.
- **Docs pass:** the fix changes no behaviour a listed doc describes; "Docs updated: none" is right.
- **Feedback section:** the fix round has its own `### Feedback (round 1)`.

## Feedback

- waste: the fix round's report named no `tickets-work` run after it changed `TicketDetailView.vue`,
  so the reviewer made it (1 run, about 1 min). A fix-round line in the coder's rules ("re-run the
  spec of every screen file you touch") would move it to the coder.
- none else.
