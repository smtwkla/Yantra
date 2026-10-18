```
Step: S013 — Network gate, access log and job queue
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S013 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** This round: 0 blocker, 0 major, 1 minor,
2 nit. CR1-01 and CR1-02 are fixed. CR1-03 and CR1-04 (nits) stay open: the user chose to leave
them.

Reviewed: fix round 1 (`backend/worker.py`, `backend/task_queue.py`,
`backend/tests/test_task_queue.py`, `backend/tests/test_worker.py`), read in full, on top of the
round-1 tree (baseline c2c45d2), plus a regression pass over the rest of the S013 diff
(`git diff -w --ignore-cr-at-eol`). The unrelated uncommitted changes and `docs/steps/S014-qr-labels/`
are out of scope.

## Tests run

- `tooling/run-tests.bat`: backend **1168 passed** (149.5 s), frontend **51 passed** (9 files).
  Exit code 0. Green.
- `npx vite build` in `frontend/`: built cleanly. The fix round touched no frontend file.

## Earlier findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | **Fixed** (one gap: CR2-01) | See below |
| CR1-02 | minor | **Fixed** | See below |
| CR1-03 | nit | Open: left by the user | Unchanged, `worker.py:116-119` |
| CR1-04 | nit | Open: left by the user | Unchanged, `worker.py:42` |

**CR1-01, part 1: which `OperationalError` is a connection loss.** `run_one`
(`worker.py:135-139`) now re-raises only when `_connection_lost` says so. Every other
`OperationalError` goes to `_task_failed`, which runs `mark_failed` after the rollback, as
§ 5.5 (3) asks.
- I checked deadlock (1213) and lock wait timeout (1205) against the installed PyMySQL.
  `err.py` maps 1213 to `OperationalError` explicitly. 1205 is unmapped, and an unmapped error
  ≥ 1000 falls back to `OperationalError`. Both are now task failures, which store
  `last_error` and count the attempt. The parametrised test covers both.
- The coder added two server codes (`SERVER_DROPPED_CONNECTION_CODES`). Both are correct:
  - **1053** `ER_SERVER_SHUTDOWN` is the error the server sends while it shuts down. The
    session ends with it. It appears in PyMySQL's `constants/ER.py` as `SERVER_SHUTDOWN`.
  - **1927** `ER_CONNECTION_KILLED` is MariaDB-only, the error a `KILL`ed session gets.
    PyMySQL has no constant for it, so the literal with its comment is the right choice.
  - **1317** `ER_QUERY_INTERRUPTED` (`KILL QUERY`) is rightly left out: the connection
    survives it, so it is a task failure.
- One gap: the client-range test `code >= 2000` is open at the top. See CR2-01.

**CR1-01, part 2: stale claims.** `requeue_stale` (`task_queue.py:74-84`) first sets expired
`running` tasks whose `attempts >= max_attempts` to `failed`. Each gets `completed_at`, a fixed
`last_error`, and `locked_until = NULL`. Then it sets the rest back to `pending`.
- The order is right: the second `UPDATE` can no longer match the rows the first one failed.
- The two statements autocommit separately. In theory a claim could expire between them and
  slip into `pending` with its attempts used up. Under the singleton lock, though, a stale
  claim belongs to a dead worker, and that window is microseconds. If it happened, the
  claim would get one more run and `mark_failed` would then fail it. Not a finding.
- A failed row counts in the card's `failed_count`, and the purge keeps failed rows. So a
  task that kills the worker every time now shows on Settings › Background tasks.
- Tests: `test_a_stale_claim_with_attempts_used_up_fails` checks the status, `completed_at`,
  `locked_until`, the error, and that the task is not claimed again. The existing
  `test_a_stale_claim_is_requeued` still passes.

**CR1-02: the main loop.** `main()` (`worker.py:193-195`) catches `Exception` after
`MySQLError`. It logs with `logger.exception`, so nothing is swallowed, closes the connection
and carries on after the poll interval.
- `SIGTERM` and `SIGINT` still stop the loop. `KeyboardInterrupt` is a `BaseException`, so
  the new branch doesn't catch it, and SIGINT has its own handler anyway.
- `test_an_unexpected_error_does_not_end_the_worker` covers it. The test restores the signal
  handlers it changes, so it doesn't leak into later tests.

## Findings

### CR2-01 — minor — `backend/worker.py:151`

**Problem.** `_connection_lost` treats any code `>= 2000` as a connection loss. The client
errors (`CR_*`: 2006 gone away, 2013 lost, …) are 2000-2999. But the server also sends codes
above 2999, and PyMySQL raises them as `OperationalError`:
- **4025** `ER_CONSTRAINT_FAILED`, a `CHECK` violation. PyMySQL maps it to
  `OperationalError` explicitly (`err.py`, the last `_map_error` block), and the schema has
  `CHECK` constraints (`local_db.py:137`, `:334`).
- Any other MariaDB 4xxx error, which is unmapped and so falls back to `OperationalError`.

On these errors the connection is fine. Yet the worker re-raises, `main()` closes the
connection, which drops the lock, and the task stays `running`.

**Scenario.** A later handler, for example a document or equipment clean-up job, writes a row
that breaks `chk_equipment_level_place`.
1. The worker logs "database error … reconnecting" and drops and retakes its lock.
2. The task waits `TASK_LOCK_MINUTES` before `requeue_stale` picks it up, not the 5-minute ×
   attempts backoff.
3. After three such rounds it ends `failed` with `last_error = 'worker lost the task;
   attempts used up'`. The real error, the CHECK violation, is never stored. It appears only
   in the worker log.

The task is now bounded, thanks to the CR1-01 fix, but the stored reason misleads whoever
reads the Background tasks card. § 5.5 (3) asks for rollback, then `mark_failed` with the
error.

**Fix.** Limit the client range: `2000 <= code < 3000 or code in
SERVER_DROPPED_CONNECTION_CODES` (with `not self.conn.open` as now). Add 4025 to the
parametrised "task failure" test.

### CR2-02 — nit — `backend/worker.py:135-142`, `:190-191`

**Problem.** When the socket really drops in the middle of a handler, the `raise` branch is
rarely what runs. PyMySQL force-closes the socket on 2013 or 2006. `transaction()`'s
`conn.rollback()` then raises `InterfaceError(0, "")`, which replaces the original error.
That is not an `OperationalError`, so `run_one` goes to the `except Exception` branch.
`_task_failed` → `mark_failed` → `conn.begin()` raises `InterfaceError(0, "")` again, and
`main()` catches it as a `MySQLError`.

The outcome is still right: the task stays `running` for `requeue_stale`, and the worker
reconnects. But the log line reads `Worker: database error ( (error 0)); reconnecting next
loop`. The real cause (2013) survives only as the exception's `__context__`, and that is not
logged. `test_a_lost_connection_is_re_raised` raises a synthetic 2013 on a live connection,
so it tests the classification but not this path.

**Scenario.** After an overnight network blip mid-purge, the log shows "(error 0)", and
nothing says the connection was lost.

**Fix.** Log the `MySQLError` branch of `main()` with `exc_info=True`, or describe
`exc.__context__` when the code is 0. Either way the 2013 shows in the log. No behaviour
change is needed.

### CR2-03 — nit — `backend/task_queue.py:7`

The module docstring still says `requeue_stale` makes stale running tasks "become pending". It
now also fails them when their attempts are used up. The function's own docstring
(`:75-77`) is correct. Update line 7 to match.

## Coder's stated departures (fix round 1)

- **Connection loss detected by error code or a closed connection, with 1053 and 1927
  added: accepted.** It is the suggested approach, and both added codes are right (see
  above). The range bound is CR2-01.
- **The failure handling folded into `_task_failed`: accepted.** It is DRY: one helper for
  the two branches.

## Checked and found consistent

- **No regressions.** The rest of the S013 diff is as reviewed in round 1. The fix round
  touched only the four files listed above.
- **Three-transaction model unchanged.** The claim is committed, then the handler and
  `mark_done` run together, then `mark_failed` runs after the rollback. `_task_failed`
  still passes `retry=False` for `BadTask`, and the unknown-type and bad-payload tests pass.
- **The deadlock and lock-timeout path reuses the live connection.** `transaction()` has
  already rolled back by the time the `except` runs, so `mark_failed`'s own transaction
  starts clean. The test checks the status (`pending`) and the stored code.
- **`self.conn.open` is a sound check.** It is PyMySQL's `_sock is not None`, which
  `_force_close` clears on any socket error.
- **Error handling.** No exception is swallowed. Both `main()` branches log, and the bare
  `pass` in `close()` is the existing, commented "already gone" case.
- **No deprecated API.** The reconnect is still a new connection, not
  `ping(reconnect=True)`.
- **Tests.** The five new tests are meaningful, and none is happy-path only: the stale claim
  with attempts used up, 1213 and 1205, the lost connection, and the main loop surviving a
  `ValueError`.
- **Manual checks.** The impl report's `## Manual checks` still carries all four
  **important** checks of brief § 8 as unticked boxes, plus the two plain ones.
- **Track.** Full, as the brief says.

## For the user's manual check

Unchanged from round 1: the four **important** boxes in the impl report's `## Manual checks`.
- IT admin from the plant, from mobile data and over the VPN; a manager on mobile data.
- Settings › Network shows your address, and the lock-out guard refuses a bad list.
- The access log shows real, varied client addresses, which also confirms the Nginx
  `set_real_ip_from` setting.
- Production: MariaDB ≥ 10.6, the worker starts and takes its lock, and the 02:30 purge is
  done the next morning.

Still recommended before the release: check that the devops compose gives the worker
container `secrets_app.py`, DB access and a restart policy.
