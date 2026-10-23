```
Step: S032 — Email to managers when a ticket is closed
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 23-10-2026
```

# S032 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** CR1-04 is fixed and its tests have a
red result. The fix round brings in no new finding. All four suites are green in my own run.
The other round 1 findings stay open for the user at gate B, by the user's choice.

Files I re-read: `backend/mail_sender.py` (in full), `backend/tests/test_closed_email.py`
(`TestSender`), and the impl report's "Fix rounds › Round 1".

## Test runs

- `YANTRA_TEST_RUN=s032cr2 tooling/run-tests.bat`: **ALL SUITES PASSED.** Backend 2459
  passed, frontend 126 passed, deps 42 passed, tooling 106 passed. The backend count is 6
  more than in round 1 (2453): the 4 QUIT cases, the `email_send` case and the login case.
- e2e: **not run.** The fix round changed only the backend sender and its tests. No screen
  and no API the screens use changed.

## Round 1 findings

| ID | Severity | Status |
|----|----------|--------|
| CR1-01 | minor | Open — not in this round (user's choice), for gate B |
| CR1-02 | nit | Open — not in this round (user's choice), for gate B |
| CR1-03 | nit | Open — not in this round (user's choice), for gate B |
| CR1-04 | nit | **Fixed** — verified below |
| CR1-05 | nit | Open — not in this round (user's choice), for gate B |
| CR1-06 | nit | Open — not in this round (user's choice), for gate B |
| CR1-07 | nit | Open — not in this round (user's choice), for gate B |

## CR1-04 verification

- **QUIT after acceptance does not reach the handler.** `send` now opens the connection
  without `with`. STARTTLS, login and `send_message` run in one `try`. After `send_message`
  returns, `quit()` runs in its own `try`. An `SMTPException` or `OSError` there is logged
  and swallowed, and `close()` runs in `finally`. A 421 on QUIT therefore no longer resends
  the email, and a 5xx no longer marks a sent email as failed.
- **The § 5.5 table is unchanged for errors before and during `send_message`.** These
  errors close the socket and re-raise the same exception. `email_core.smtp_outcome` still
  sees the original `smtplib` or `OSError` exception, so rows 1–6 still apply.
- **No address reaches the log (U5, ISO 27001 A.5.34).** The warning logs only
  `type(exc).__name__`. It logs neither the exception text (a server reply can quote the
  recipient) nor `to`.
- **Double close is safe.** `smtplib.SMTP.quit()` already calls `close()`, and the
  `finally` calls it again. `close()` sets `file` and `sock` to `None` after the first call,
  so the second call does nothing.
- **Tests and red result.** The tests cover QUIT failing with 421, 554,
  `SMTPServerDisconnected` and `OSError`; the `email_send` path with a 421 on QUIT (task
  done, sent once); and a login error (raised, socket closed, no QUIT). The existing test now
  asserts that QUIT and close ran. The report gives the red result: 5 tests failed with the
  `except` made to catch nothing real, with the raised exceptions named.

## Judgement on the coder's decision: `except BaseException` then re-raise

The decision is sound. The block only closes the socket and re-raises, so it swallows
nothing. It is the same cleanup that `with` gave before, and the same as a `finally` that
runs only on error. Catching `BaseException` (not `Exception`) is right here: a
`KeyboardInterrupt` or the worker's shutdown signal during a slow `send_message` should also
release the socket. The narrower catch on QUIT (`SMTPException`, `OSError`) is also right:
any other exception there is a code fault and should be raised, not logged as a warning.

Fact: real `smtplib.quit()` does not check the reply code, so a 421 or 554 on QUIT does not
raise in practice; only a dropped connection (`SMTPServerDisconnected`) or a socket error
does. The 421 and 554 test cases are synthetic but harmless, and they guard against a future
change of `quit()`.

## Findings

None new in this round.

## Checked and found consistent

- `mail_sender.send` keeps its contract: settings read at call time, STARTTLS with
  `ssl.create_default_context()` (certificate checked), login, one message to one recipient.
- The module docstring and `send`'s docstring still match the behaviour. The QUIT comment
  says *why* (a resend or a false failure), not *what*.
- The test fakes lost `__enter__` / `__exit__`, so a return to `with` would fail the tests.
- The impl report's fix-round section is in scope A, names the files touched, lists the
  decision taken, and gives the red and green results.

## Manual browser checks for the user

Unchanged from round 1: rows 27–30 of `docs/steps/device-checks.md` (rows 27 and 28 are
**important**). This round adds no manual check.
