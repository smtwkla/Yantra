```
Step: S045 — The known flaky tests made steady
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: fix
Status: Done (committed 67a4b57, 25-10-2026; CR1-04 closed by KLA 25-10-2026: S046's full run shows the guard lets phone-webkit through at 390 px; #2 and #3 stay open flakes, cause unknown)
Baseline: refs/steps/S039 + S040 (working tree, gate B pending)
```

# S045 — The known flaky tests made steady

**The request (KLA, 25-10-2026).** "Fix the known flaky tests." Each one cost a
re-run, and some cost a review round, during S035–S040. Test code only; no app
code changes. If a cause turns out to be in the app, stop and report it
(QUESTIONS FOR THE USER): the step then leaves the fix lane.

## The tests, the cause seen, and the fix

| # | Test | Seen | Cause (from the reviews; the coder confirms it in the code) | Fix |
|---|---|---|---|---|
| 1 | `frontend/e2e/masters.spec.js:62`, "engineer: a deactivated mode is hidden unless Show inactive, and comes back on reactivate" (S016) | Pixel 7, S038 CR r2 | A click on *Deactivate* / *Reactivate* / *Yes* lands before the dialog or its inline confirm is open and steady; the test calls no `openDialog` before the click | Wait for the dialog with `openDialog(page)` (S024 open-dialog wait) and click inside it; the same for the reactivate leg |
| 2 | `frontend/e2e/tickets-raise.spec.js:141`, "S018 A1: Already fixed with a start time …" | phone-webkit, S039 coder run | `scrollIntoViewIfNeeded` timed out waiting for the element to be stable, under load | Find what moves the element (a transition, a late re-render) and wait for its end state with a web-first assertion before the action; no fixed sleeps |
| 3 | `frontend/e2e/tickets-parts.spec.js:129`, "S020: technician adds a part line the short way…" | phone-webkit, S041 full run | The inline "Remove?" *Yes* button was detached from the DOM while Playwright retried: the line re-rendered | Locate the button afresh inside the line after the confirm shows (`expect(...).toBeVisible()` then click), or wait for the re-render's end state |
| 4 | `frontend/e2e/tickets-work.spec.js:420`, "S019: the Overdue filter shows a ticket planned in the past, with the red badge" | the S040 review run that crossed midnight | The seed writes the planned date as *yesterday* (`istDay(-1)`) when the e2e database is built; a test that runs after midnight expects the new *yesterday* | Read the seeded ticket's planned date (API) and expect the badge from it, or make the seed write a date far enough back (e.g. 3 days) and assert from that |
| 5 | `backend/tests/test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed` | S041, S043, S039 runs (Windows) | `ConnectionAbortedError` (WinError 10053): the test server's `do_POST` answers 307 without reading the request body, so Windows aborts the socket while the client still sends | Read `Content-Length` bytes from `self.rfile` before `send_response(307)`; the test still asserts `TooManyRedirects` |
| 6 | Every phone-webkit e2e test (a guard, not a flake fix) | S040 CR r2, 25-10-2026 | With Windows display scaling above 100 % (seen: 125 %, `devicePixelRatio` 3.75), WebKit's iPhone 14 window is 312 px wide instead of 390, so a dialog focus scrolls *Yes* off screen; a real iPhone cannot do this | A check in `frontend/e2e/support/` (the `test.js` fixture) that stops a phone-webkit run at once with a clear message when `innerWidth` is not the device's width: "The phone-webkit window is 312 px wide, not 390. Set Windows display scale to 100 % and sign in again." |

## Files

The five test files above and `frontend/e2e/support/test.js` (#6), plus this
step's files. No app code. `e2e/support/` changes, so the full e2e suite runs
(on a host at 100 % scale, or with phone-webkit named as skipped by the guard).

## The failing test

A flake has no reliable red run. For each test: name the cause found in the
code, and prove the fix by repeat runs — the e2e test 10 times on the project
it failed on (`--repeat-each=10`, one lane), the backend test 20 times
(`pytest --count` is not installed: a loop of 20 runs of the one test). For #4,
a red run is possible: set the expected day one further back to show the old
assertion's failure mode, then restore.

## Docs updated

None expected (test-only).

## Manual checks

None.

## Review log

No brief review (fix lane). Code review r1 answers, decided by KLA on 25-10-2026:

| Finding | Answer |
|---|---|
| CR1-01 major: #2's cause is wrong, the fix is a no-op | Accepted: undo the change, mark #2 not fixed, cause unknown (assumed: WebKit draws no frames under the 6-lane load) |
| CR1-02 major: #3's fresh locator is the same locator | Accepted: undo the change, mark #3 not fixed, with the same assumption |
| CR1-03 major: the guard fails every phone-webkit test | Accepted: the guard skips with its message (the user's answer to S046 Q3) |
| CR1-04 minor: the guard never seen to pass at 100 % | Accepted, option A: an open box in the impl report's Manual checks, for KLA at 100 % display scale; the step does not wait for it |
| CR1-05…CR1-07 nits | Accepted |
