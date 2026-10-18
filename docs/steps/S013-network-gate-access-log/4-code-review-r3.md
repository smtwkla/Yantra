```
Step: S013 — Network gate, access log and job queue
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S013 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** This round: 0 blocker, 0 major, 0 minor,
1 nit. CR2-01, CR2-02 and CR2-03 are fixed. CR1-03 and CR1-04 (nits) stay open: the user chose
to leave them.

Reviewed: fix round 2 (`backend/worker.py`, `backend/task_queue.py`,
`backend/tests/test_task_queue.py`), read in full, on top of the round-2 tree (baseline
c2c45d2), plus a regression pass over the changed code. The unrelated uncommitted changes and
`docs/steps/S014-qr-labels/` are out of scope.

## Tests run

- `tooling/run-tests.bat`: backend **1170 passed** (156.4 s), frontend **51 passed** (9 files).
  Exit code 0. Green. This matches the impl report's Round 2 count.
- `npx vite build`: not run. The fix round touched no frontend file, and round 2 built it
  cleanly.

## Earlier findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed (round 2) | The CR2-01 gap is now closed too |
| CR1-02 | minor | Fixed (round 2) | Unchanged, `worker.py:206-208` |
| CR1-03 | nit | Open: left by the user | Unchanged, `worker.py:184-185` |
| CR1-04 | nit | Open: left by the user | Unchanged, `worker.py:40-42` |
| CR2-01 | minor | **Fixed** | See below |
| CR2-02 | nit | **Fixed** | See below |
| CR2-03 | nit | **Fixed** | `task_queue.py:7-8` now says "become pending, or failed when their attempts are used up" |

**CR2-01: the client-code range.** `_connection_lost` (`worker.py:151-157`) now treats only
`2000 <= code < 3000` (`CLIENT_ERROR_CODES`), 1053, 1927 or a closed connection as a loss.
- 4025 `ER_CONSTRAINT_FAILED` and any other unmapped 4xxx server error now go to
  `_task_failed`. They are rolled back, `mark_failed` stores the real error, and the backoff
  applies, as § 5.5 (3) asks.
- `test_a_server_constraint_error_is_a_task_failure` checks 4025 → `pending` with "4025" in
  `last_error`.
- The 1213/1205 parametrised test and `test_a_lost_connection_is_re_raised` (2013) still
  pass, so both sides of the boundary are covered.

**CR2-02: the real cause of a dropped connection.** There are two parts:
- `_log_lost` (`worker.py:159-164`) logs with `exc_info=exc`. Python's traceback printing
  follows `__context__`, so when the rollback's own error hides the first one, the log still
  shows the original 2013 under "During handling of the above exception…".
- `run_one`'s generic branch (`:142-145`) now checks `not self.conn.open` first. This is the
  path I described in round 2: the 2013 closes the socket, `transaction()`'s `rollback()`
  raises `InterfaceError(0, "")`, and that error is not an `OperationalError`. The worker
  now logs the original cause, re-raises, and leaves the claim `running` for
  `requeue_stale`. Before, it called `mark_failed` on a dead connection, which failed anyway.
  The outcome is the same as before, but the code is clearer and the log is useful.
- I checked that `__context__` is really set. `db_helpers.transaction` (`:48-54`) calls
  `conn.rollback()` inside `except BaseException:`, so a raise from the rollback chains the
  handler's error.
- `test_a_failed_rollback_logs_the_original_cause` closes the connection inside a patched
  `rollback` and raises. It checks that the original message is in the log, that the error
  propagates, and that the task is still `running`. The test raises the base
  `pymysql.err.Error` rather than `InterfaceError`. Both go through the same generic branch,
  so the test is valid.
- `main()`'s `MySQLError` branch still logs "database error ( (error 0))" after this. That is
  fine now: the line before it, from `_log_lost`, names the cause.

## Findings

### CR3-01 — nit — `backend/worker.py:47-49`, `:156`

**Problem.** There are two small readability issues:
- The comment on line 47 ("Server-side errors … 1053 server shutdown, 1927 connection
  killed") describes `SERVER_DROPPED_CONNECTION_CODES` on line 49. But it sits above
  `CLIENT_ERROR_CODES` on line 48, which has its own trailing comment.
- Line 156 spells the range test out as `CLIENT_ERROR_CODES.start <= code <
  CLIENT_ERROR_CODES.stop`. Plain `code in CLIENT_ERROR_CODES` says the same thing.

**Scenario.** A reader takes the line-47 comment as the description of the 2xxx range and
puzzles over the mismatch. There is no behaviour impact.

**Fix.** Move the comment line down so it sits just above line 49, and write `code in
CLIENT_ERROR_CODES` on line 156. This is optional.

## Coder's stated departures (fix round 2)

- **Range as a named `range` constant: accepted.** It names the CR_* band once.
- **The `not self.conn.open` check in the generic branch: accepted.** It goes a little
  beyond the logging fix that CR2-02 asked for, but it is listed in the report's Round 2,
  and it removes a doomed `mark_failed` call on a dead connection. It does not change the
  task's outcome, which is still `running` until `requeue_stale`.

## Checked and found consistent

- **No regressions.** Fix round 2 touched only `worker.py`, `task_queue.py` (docstring) and
  `test_task_queue.py`. The rest of the S013 diff is as reviewed in rounds 1 and 2.
- **Three-transaction model unchanged.** The claim is committed, then the handler and
  `mark_done` run together, then `mark_failed` runs after the rollback on a live connection.
  `BadTask` still gets `retry=False`, and the unknown-type and bad-payload tests pass.
- **Live connection and non-DB error.** A handler's `ValueError` or similar with the
  connection open still goes to `_task_failed`, because `conn.open` is True after a
  successful rollback.
- **Rollback raises `OperationalError` on a broken socket.** The `OperationalError` branch
  handles this: the connection is closed, so `_connection_lost` returns True and the worker
  logs and re-raises.
- **Error handling.** No exception is swallowed. Every branch either stores the error or
  logs it with its traceback and re-raises.
- **No deprecated API.** The worker still opens a new connection rather than calling
  `ping(reconnect=True)`.
- **Manual checks.** The impl report's `## Manual checks` still carries all four
  **important** checks of brief § 8 as unticked boxes, plus the two plain ones.
- **Track.** Full, as the brief says.

## For the user's manual check

Unchanged from rounds 1 and 2: the four **important** boxes in the impl report's
`## Manual checks`.
- An IT admin from the plant, from mobile data and over the VPN; a manager on mobile data.
- Settings › Network shows your address, and the lock-out guard refuses a bad list.
- The access log shows real, varied client addresses, which also confirms the Nginx
  `set_real_ip_from` setting.
- Production: MariaDB ≥ 10.6, the worker starts and takes its lock, and the 02:30 purge is
  done the next morning.

Still recommended before the release: check that the devops compose gives the worker
container `secrets_app.py`, DB access and a restart policy.
