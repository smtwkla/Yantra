```
Step: S074 — Improvement alerts
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S074 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01 to CR1-04. It
brings in no new fault. One nit remains: the new push guard stops a real post, but a post made
inside a worker task does not turn the test red.

Files re-read: the fix round's diff in `backend/alerts.py`, `backend/db_helpers.py`,
`backend/improvements.py`, `backend/meters.py`, `backend/task_handlers.py`,
`backend/tests/conftest.py`, `backend/tests/test_worker.py` and `frontend/e2e/settings.spec.js`.
I also read `backend/push_sender.py` (`send`, the only `webpush` call) and
`task_handlers.push_send` to judge the guard.

## Test results (my runs)

- Backend suite, `YANTRA_TEST_RUN=s074cr2 tooling/run-backend-tests.bat`: 3865 passed (166 s).
  PASSED.
- The fix round changed backend code and one browser spec, and no frontend or tooling unit code.
  So the backend suite is the suite to run, not all three.
- Browser tests: none re-run. The coder ran the right targeted spec, `e2e/settings.spec.js`
  (5 passed): the only spec the fix round changed. No shared frontend file changed.

## Status of the round 1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed |
| CR1-02 | nit | Fixed |
| CR1-03 | nit | Fixed |
| CR1-04 | nit | Fixed |

- **CR1-01.**
  - `test_retaken_after_a_dropped_connection` patches `worker_module.SCHEDULE` to `[]`. No daily
    task becomes due in it at any hour, and the reconnect check is unchanged.
  - The autouse `no_real_push` fixture wraps `push_sender.webpush`. `send` is the only caller, and
    it passes `subscription_info` as a keyword, so `kwargs["subscription_info"]["endpoint"]` is
    always there.
  - It allows only the host `127.0.0.1`. `localhost`, `::1` and every push service are refused.
    That is loopback only, and stricter than needed. The redirect test of `test_alerts.py:530`
    serves on `127.0.0.1`, so it still passes.
  - Tests that fake `webpush` or `send` set their fake after the autouse fixture, so their fake
    wins, as the report says.
  - Red result: the report says why there is none. The test patch fails only after 08:00 IST
    with a left-over candidate, so it is time dependent. I accept the reason.
- **CR1-02.** One `marks(values)` in `db_helpers.py`. `alerts._marks`, `improvements._in` and
  `meters._marks` are gone, and every call now uses `marks`. The function body is the same, so
  the SQL is the same. `meters._nodes_rows` passes a dict, and `len` of a dict is its key count,
  as before. No local name shadows `marks` in the three modules. `db_helpers` imports neither
  module, so there is no cycle.
- **CR1-03.** The "not sent" line now says "no longer true" and names the improvement state, the
  countermeasure state, the owner id, the due date, the watch end and the payload's expected
  values. It logs person ids only, no address.
- **CR1-04.** The test finds each task's text inside the Background tasks card with `getByText`.
  It uses no Bootstrap classes. It no longer checks that the card lists exactly these two tasks
  in this order. The brief's check is that the morning task is listed, so this is enough.

## Nits

- **CR2-01** (nit) `backend/tests/conftest.py:124-127`: inside a worker task, `push_send`'s
  `except Exception` (`task_handlers.py:337`) catches the guard's `AssertionError`, marks the task
  failed and the test stays green. To make such a test fail, record the refused host in a list
  and assert it is empty in the fixture's teardown.

## Checked and found consistent

- The guard covers the only network path for push. `pywebpush` is imported only in
  `push_sender.py`, and no other module calls `requests.post` for push.
- `push_send` checks `refused_host` before it calls `send`. So in a worker path, a loopback
  endpoint never reaches the guard. Only a direct `push_sender.send` call, as in the redirect
  test, uses the loopback exception.
- The other inline `", ".join(["%s"] * …)` lines in `equipment.py`, `masters.py`,
  `properties.py` and `tickets.py` were there before S074. They are outside this fix round, so
  they are not a finding.
- `docs/steps/INDEX.md` changed only in S074's own status row.
- Docs updated: none. That is right, because the fix round changes no behaviour, schema or
  setting.

## Manual checks still for the user (real device)

Unchanged from round 1:

- [ ] **Important** (device row 53): *Countermeasure for you* reaches the technician's phone
  quietly, and a tap opens the improvement page.
- Row 54: *Countermeasure overdue* after 08:00 the next day on both phones. On the technician's
  phone it replaces the earlier alert.

## Feedback

- hindrance: the S075 coder writes in the same tree, so a green backend run here also depends on
  that step's state at the moment of the run (my run was green, 166 s; a red one would have
  needed sorting by hand).
