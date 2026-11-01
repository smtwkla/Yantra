```
Step: S091 — The contract reminder worker test counts only its own contract
Doc: code review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
Track: fix
Baseline: c3f8bbf
Status: Done
```

# S091 — Code review, round 1

**Verdict: no blocker or major finding is open.** The new filters isolate the test from leftover contracts. One nit.

## Test run

- `YANTRA_TEST_RUN=s091cr1 tooling/run-backend-tests.bat tests/test_contract_alerts.py`: PASSED, 32 passed in 33 s
  (log `scratch/backend-tests-s091cr1.log`).
- The full unit run is the coder's (`s091c1`: backend 4467, frontend 412, tooling 231, all passed), as the
  orchestrator asked. No browser run: no screen or API changed.

## Nits

- **CR1-01** (nit) `backend/tests/test_contract_alerts.py:468`: the assert `other["title"] not in to_manager[0][1]`
  cannot fail once line 466 matched `made["title"]`, because a subject names one contract only
  (`email_core.contract_ending_email`). It does not show "the filter works on the title", as the report says; the red
  run does that. Drop it, or keep it and leave the report's reason out.

## Checked and found consistent

- **Push filter (line 462).** It keeps the engineer's pushes whose `path` is `/contracts/<made id>`. The path holds
  the contract id, which is unique, so no leftover contract can match it. `push_sends` (line 107) reads the same
  key.
- **Email filter (line 466).** It keeps the manager's emails whose subject holds `made["title"]`. The subject is
  `Contract ends on <date>: <title> (<sites>)`. The title is `AMC Vendor NNNN` from the session-scoped `uniq`
  (`tests/conftest.py:371`), and `_clean_tables` empties `contracts` at the start of each session, so every contract
  in the worker database came from the same counter. A leftover title holds `made["title"]` only if it has more
  digits, which means a later number; a leftover is always earlier. Titles from other files (such as "x") never
  hold `AMC Vendor `. The isolation holds.
- **The red result is real.** `other = contract(60, at=[])` is due on the same day and has no machine, so it reminds
  every site (S087) and reaches the same engineer and manager. With the old filters `len(mine)` is 2 (the report
  names both paths); the email assert would also have counted 2.
- **Other asserts in the test.**
  - The `contract_reminder_scan` status list (line 458): `queue_emptied` deletes every task first, and each worker
    database belongs to one xdist worker, so only the scan the patched `SCHEDULE` queues can be there. Exactly one
    row.
  - `alert_tasks` and `push_sends` (lines 460–461) filter by the contract id or path. `other`'s tasks do not
    count.
- **Other tests in the file.** Only this test runs the worker. The others call the handlers for one contract and
  read rows by contract id, as the report says; `email_sends` by person id sits in tests where one handler runs for
  one contract.
- **Scope.** One test file, as the brief says. No production code. The one departure (the extra assert) is listed
  in "Decisions taken".
- **Docs.** None due: a test-only change meets no row of `.claude/CLAUDE.md` § Docs to keep current.
- **Manual checks.** None in the brief; the report says none.

## Manual browser checks for the user

None.

## Feedback

- none
