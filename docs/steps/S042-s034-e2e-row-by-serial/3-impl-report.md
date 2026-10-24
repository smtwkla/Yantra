```
Step: S042 — S034's quick-pick e2e test finds its row by serial
Doc: impl report
Author: Coder
Date: 24-10-2026
Track: fix
```

# S042 — Impl report

Result: the S034 "In 14 days" test now finds its row by `ticket.serial`. It passes on all three projects with `E2E_LANES=1`. No app code changed.

## What was built
`frontend/e2e/tickets-work.spec.js`, test "S034: In 14 days fills the date …":
- The list URL is now `/tickets?q=S034 test: quick pick` (was `/tickets`), so other tests' tickets stay off the page.
- The last assertion filters rows by `ticket.serial` (was the shared description), as the S036 test's `rowOf` does.

## Why
The test leaves its ticket deferred. Each later project on the same database added one more row with the same description, so the count was 2 or 3. The serial is unique.

## Tests
- Red, before the fix: `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "In 14 days"`: 1 passed, 2 failed (phone-webkit, desktop-chromium; failing line 515, the count assertion).
- Green, after the fix: the same command: 3 passed.
- Targeted `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js` (default lanes, 3 lanes): 66 passed.
- Full `YANTRA_TEST_RUN=s042c1 tooling/run-tests.bat`: backend 2520 passed, frontend 143 passed, deps 42 passed, tooling 106 passed. ALL SUITES PASSED.
- `vite build` not run: no frontend source changed.

## Files touched
1 file: `frontend/e2e/tickets-work.spec.js` (plus this step's two files). The working copy of the spec also holds S036's uncommitted changes; this step did not touch them.

## Decisions taken
None. The `q=` text equals the description the test raises.

## Not done / deferred / assumed
Nothing. The state filter still changes through the select; the test ends with the URL `state=scheduled` and the one row for the ticket's serial.

## Docs updated
None, because this is a test-only fix.

## Manual checks
None.
