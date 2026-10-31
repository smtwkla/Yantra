```
Step: S085 — Contract renewal
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S085 — code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** CR1-01, CR1-02 and CR1-03 are fixed, and S084's CR2-01 is
fixed too. The fix round brings in no new finding. The named tests are green.

## Tests run

- `YANTRA_TEST_RUN=s085cr2 tooling/run-backend-tests.bat tests/test_alerts_core.py tests/test_email_core.py
  tests/test_contract_alerts.py tests/test_contract_renewal_api.py`: PASSED, 246 passed (27 s).
- `YANTRA_TEST_RUN=s085cr2 tooling/run-frontend-tests.bat tests/contractLabels.test.js`: PASSED, 24 passed.
- Not run: all suites. The fix round touched backend and frontend, but each change is small and named by the
  orchestrator's test list. `status_label` has no reader left in `backend/` (grep over `.py`, `.html`, `.txt`), so
  the removed key cannot break another suite.
- Schema docs check: not run. The fix round has no migration and no `docs/schema/` change.
- Browser: none re-run. No finding of mine needs a run. The coder's targeted run is the right one:
  `e2e/contracts.spec.js e2e/screens.spec.js` at Normal, 54 passed, 1 skipped. No shared frontend file changed.
- Line endings: all six files in the fix-round diff hold LF only (0 CRLF, counted by bytes). The diff is
  24 insertions and 8 deletions, every line a real change; no line-ending noise.

## Findings carried from round 1

| ID | Severity | Status | Check |
|---|---|---|---|
| CR1-01 | minor | Fixed | `ContractRenewDialog.vue` `open()` clears `loadError`, calls `openCreate`, then awaits `ensureVendors()` in a `try`/`catch`. A failure sets one plain line, shown at the top through `topError` (`modalError` first), as `RootCauseDialog.vue` does. The new browser test fulfils the vendors request with 503, allows that failed request in `consoleWatch`, opens the dialog through `openRenew` (which calls `expectDialogFits`) and asserts the line. The fix round states its red result: without the fix the dialog never opens. |
| CR1-02 | nit | Fixed | `renewalNotice` says "No machine is copied: CMP004 (scrapped), CMP005 (now at BRICKS)." when every machine is skipped. "Not copied: …" now shows only when some machines are copied. `skippedText` holds the one copy of the list. The unit test expects the new text. |
| CR1-03 | nit | Fixed | `contracts.py:633` now says "in id order, before any line insert". |
| S084 CR2-01 | nit | Fixed | `alerts_core.contract_facts` no longer returns `status_label`; `ends_words` still reads `label`. No reader of the key is left. |

## Nits

None.

## Checked and found consistent

- The vendor field after a failed load: `ContractFields` still gets `storedVendor`, so the old vendor stays in the
  list, and the user is told to close and try again. Saving with the old vendor stays possible; the API checks the
  vendor (`check_active_vendor`).
- `topError` puts a save error before the load error, so a refusal from the route is never hidden.
- The error text follows scope B: what happened, and what to do next.
- Files re-read: the six files of the fix-round diff (`ContractRenewDialog.vue` lines 1–90 in full; the hunks of
  the other five), `RootCauseDialog.vue` `open()` for the pattern, and the `openRenew` helper in
  `e2e/contracts.spec.js`.

## Manual browser checks for the user

None from this step: every important check is `[auto]`, and § 8.5 lists no real-device check.

## Feedback

- hindrance: `grep -c $'\r'` in Git Bash counted every line of LF files as a match, so a CRLF check needed a
  small byte-count script (`scratchpad/crlf.py`, about 2 min).
