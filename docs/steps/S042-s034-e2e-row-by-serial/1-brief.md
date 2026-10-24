```
Step: S042 — S034's quick-pick e2e test finds its row by serial
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: fix
Status: Gate B (CR r1: 0 blocker, 0 major, 1 nit — fixed: index row)
Baseline: e451c33 + uncommitted S035, S036, S041
```

# S042 — S034's quick-pick e2e test finds its row by serial

**The bug (found by S036 CR2, 24-10-2026; the user accepted D13).** The test
`S034: In 14 days fills the date …` in `frontend/e2e/tickets-work.spec.js`
ends at line 515 with
`expect(page.locator(".list-group-item").filter({ hasText: "S034 test: quick pick" })).toHaveCount(1)`
on the list filtered `state=scheduled`. The test leaves its ticket deferred, so
every later project that runs it on the same database adds one more matching
row. With `E2E_LANES=1`, or when one lane gets `tickets-work` for two projects,
the count is 2 or 3 and the test fails every time (`retries: 0`). A full run
before a release can go red, depending on how the tests are split.

**How to see it.** `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "In 14 days"`:
1 passed, 2 failed (S036 CR2).

**The cause.** The row is found by its description, which every project
shares, and not by the ticket's serial.

**The fix.** Keep the ticket the test raises (the `raiseByApi` or
`raiseBreakdown` result), and find its row by `ticket.serial`, as the S036
test does (`rowOf`). Add `q=` with the description to the list URL as well, so
other tests' tickets stay off the first page. Nothing else changes. No app code.

**Files.** `frontend/e2e/tickets-work.spec.js` only, plus this step's files.

**The failing test.** Red: the command above (1 passed, 2 failed). Green: the
same command passes on all three projects, and the targeted `tickets-work.spec.js`
run (six lanes) passes.

## Docs updated

None expected (a test-only fix).

## Manual checks

None.

## Review log

None (fix lane).
