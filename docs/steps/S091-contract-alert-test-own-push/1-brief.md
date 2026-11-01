```
Step: S091 — The contract reminder worker test counts only its own contract
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: fix
Baseline: c3f8bbf
Status: Done (committed f58370d at adoption, released in v0.1.15, 01-11-2026; no device check); was: Gate B 01-11-2026 (code review r1: 1 nit, CR1-01, fixed)
```

# S091 — The contract reminder worker test counts only its own contract

Found by the pre-flight of `c3f8bbf` (`scratch/preflight/c3f8bbf.md`, bug 1). KLA, 01-11-2026: fix the test.

## The bug

`backend/tests/test_contract_alerts.py::TestThroughTheWorker::test_scan_alert_and_sends_all_done` (S084) failed
once in the release tests and passed on re-run: `assert len(mine) == 1` got 2. The app is right; the test is not.

## Steps to see it

1. Leave in the kept worker database a contract with no machine whose reminder is due today (another test did:
   contract 106, title "x", ends 01-11-2026).
2. Run the test. The worker drains every due task, so the scan sends that contract's reminder too. A contract with
   no machine reminds every site (S087), so the test's engineer gets two pushes and the manager two emails.

## Cause

`backend/tests/test_contract_alerts.py:461`: `mine` filters the pushes by the engineer's device only, not by the
test's own contract; line 464 filters the emails by the manager's address only. The file's header
(lines 12–14) says a test asserts only on its own contract's rows; these two lines do not. The test runs the real
worker on purpose (it drains every due task), so it cannot stop other contracts from being sent.

## The fix

- Line 461: keep only the pushes of the test's own contract: `data["path"] == f"/contracts/{made['id']}"` (the
  push's `path`, as `push_sends` at line 109 already reads it), besides the engineer's device.
- Line 464: keep only the emails to the manager that name the test's own contract (`made["title"]` in the text,
  which the test already checks), then assert exactly one.
- No production code changes.

## Files

- `backend/tests/test_contract_alerts.py`

## The test that fails on the bug

In the same test, before the worker runs, make a second contract with no machine that is due for a reminder
(`contract(0, at=[])` or the fixture's equivalent; its title is unique by `uniq`). With the old filters the test
fails (two pushes to the engineer, two emails to the manager); with the new ones it passes, and it no longer
depends on what other tests left. Runs: `YANTRA_TEST_RUN=s091c1 tooling/run-backend-tests.bat
tests/test_contract_alerts.py` red (with the second contract, old filters) then green; then the unit suites
`YANTRA_TEST_RUN=s091c1 tooling/run-tests.bat`. No browser run (no screen changes).

## Review log

| ID | Finding | Answer |
|---|---|---|
