# S091 — Implementation report

## What was built

The worker test `TestThroughTheWorker::test_scan_alert_and_sends_all_done` now counts only its own contract's push and email. No production code changed.

## How it works

- The test first makes a second contract with no machine (`other = contract(60, at=[])`). It is due for a reminder and reminds every site (S087), so the worker sends it to the same engineer and manager. This reproduces the pre-flight failure on purpose.
- `mine` keeps the engineer's pushes whose `data["path"]` is `/contracts/<made id>`.
- `to_manager` keeps the manager's emails whose subject names `made["title"]`; the test asserts exactly one.

## Red and green

- Red (second contract added, old filters): `assert (2 == 1)`, `len(mine)` was 2 (pushes for `/contracts/1` and `/contracts/2`). Run: `tests/test_contract_alerts.py`, 1 failed, 31 passed.
- Green (new filters): `tests/test_contract_alerts.py`, 32 passed.
- Full run, `YANTRA_TEST_RUN=s091c1 tooling/run-tests.bat`: backend 4467 passed, frontend 412 passed, tooling 231 passed. ALL SUITES PASSED.
- No browser run: no screen changed.

## Other tests checked

Only this test runs the real worker. Every other test in the file calls the handlers directly and reads rows by contract id (`push_sends(db_rows, made["id"])`, `alert_tasks`). Their `email_sends` calls filter by person ids and sit in tests where the contract is the only one the handler runs, so none has the same flaw. Nothing else changed.

## Files touched (1)

- `backend/tests/test_contract_alerts.py`: the test above.

## Decisions taken


## Not done

Nothing deferred.

## Fix rounds

### Fix round 1 (orchestrator, 01-11-2026)

- **CR1-01: Fixed.** Dropped the assert `other["title"] not in to_manager[0][1]`: once the filter matches `made["title"]` it can never fail, so it proved nothing. The orchestrator made this one-line, test-only edit itself instead of spawning a coder. `tests/test_contract_alerts.py`: 32 passed (`YANTRA_TEST_RUN=s091c1`).

## Docs updated

None, because only a test changed; no row of `.claude/CLAUDE.md` § Docs to keep current is due.

## Manual checks

None.

## Feedback

- none
