Step: S036 — Ticket tint by intensity
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026

# S036 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixed CR1-01, CR1-02
and CR1-03. It brings in no new fault. One new nit is about the report's account of the
S034 test.

This round verifies the fix round only (README § round 2 and later).

## Test results (my runs, `YANTRA_TEST_RUN=s036cr2`)

- `tooling/run-tests.bat`: all suites passed. Backend 2520, frontend 143, deps 42,
  tooling 106.
- `npx vite build` in `frontend/`: built (only the old chunk-size warning).
- `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/equipment.spec.js
  e2e/me.spec.js e2e/screens.spec.js` (six lanes, three projects): **147 passed**,
  0 failed, in 2.3 min. Why these specs: the fix round changed `TicketRow.vue` (Tickets
  list: `tickets-work`; Me page: `me`), `EquipmentDetailView.vue` (`equipment`),
  `TicketDetailView.vue` (`tickets-work`), plus `screens`. It changed no shared
  frontend code and nothing in `e2e/support/`, so the full suite is not needed.
- `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "S034: In 14 days"`:
  **1 passed, 2 failed** (phone-webkit, desktop-chromium; `toHaveCount(1)` received 3).
  I ran this to judge the S034 fault the report names (see § S034 test below).

## Findings of round 1

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `tickets-work.spec.js:518-541`: the list opens with `state=all&q=S036 tint`, and `rowOf(ticket)` finds each row by its serial. `q` is a server filter (`tickets.py:522`), so only this test's tickets are on the page. A serial (`TK-YYYY-MM-NNN`) is unique, so a second project on the same database finds one row per serial. |
| CR1-02 | nit | Fixed | `TicketDetailView.vue:213` has `data-testid="ticket-title"`; the test uses `page.getByTestId("ticket-title")`. |
| CR1-03 | nit | Fixed | `ticketRowClass(ticket)` in `ticketLabels.js` returns the two classes or `null`. `TicketRow.vue` and `EquipmentDetailView.vue` both use it. The new vitest case covers a tinted, a grey and a closed ticket. |

**Red results.** The report gives a reason for each missing red run. CR1-01: the old
test passed in the six-lane split, and the fault shows only with two projects on one
database. CR1-03: a new helper, not a fault fix. Both reasons hold, so there is no
finding.

**Brief.** Brief § 2 now names `#2b2f32` (`--bs-secondary-text-emphasis`) with the
ratios of my round 1 table (10.11 … 8.02). The brief matches the code.

## Nits

- **CR2-01** (nit) `docs/steps/S036-ticket-tint/3-impl-report.md` (Fix rounds › Round 1,
  Tests): the report says the S034 test was "flaky" and "passed on retry". Playwright runs
  with `retries: 0` (`playwright.config.js:19`), and my one-lane run of that test failed
  on two of three projects. State it as a failure of an older test, not a flake.

## The S034 test: does it need a fix-lane step?

**Recommendation: yes, a small fix-lane step, test code only.** The fault is
deterministic, not a flake.

- Fact: `tickets-work.spec.js:515` counts the rows that contain "S034 test: quick pick"
  on `state=scheduled` and expects 1. The test leaves its ticket deferred. So each later
  project on the same database adds one more row: the second project sees 2, the third 3.
- Fact: on one lane (`E2E_LANES=1`) the test fails on the second and third projects, every
  time (my run above).
- Fact: in a six-lane run, a lane is a spec file in one project (`run_lanes.py:45`). The
  full suite has 11 spec files × 3 projects = 33 groups on 6 lanes. A lane can then get
  `tickets-work.spec.js` for two projects, and the test fails in that lane. Today's
  targeted run (4 specs × 3 projects = 12 groups) kept them apart, so it passed.
- Assumption: the user's full run before a release can therefore go red on this test,
  depending on the shard split.
- The fix is the same as CR1-01: keep the ticket that `raiseByApi` returns, and filter
  the row by its serial (or add `q` to the list URL). It is of the same class as S041 (a
  test that reads data other runs add). S041 is at Gate B, so a new step is cleaner than
  widening it.

## Fix round's own diff

I re-read the hunks of the six files of the round: `ticketLabels.js`, `TicketRow.vue`,
`EquipmentDetailView.vue`, `TicketDetailView.vue`, `frontend/tests/ticketLabels.test.js`,
`frontend/e2e/tickets-work.spec.js`.

- `ticketRowClass` returns `tint && [...]`, so `null` for a closed ticket or an unknown
  intensity. Vue ignores a `null` class binding.
- The static `class` and the bound `:class` merge on both `router-link` rows, as before.
- The test id adds no screen text. No dialog, button or message changed.

## Manual checks

The impl report's `## Manual checks` is unchanged and still complete:

- `[auto]` the important check, with a passing run behind it (my run: green on 3 projects).
- Row 31 of `docs/steps/device-checks.md` (phone on the shop floor, the three tints in
  daylight and under the hall lights).

**Still for the user, in a browser:** row 31 only.

## Checked and found consistent

- The S036 e2e test asserts computed background colours of the rows and the title panel,
  not only class names.
- `rowOf` and `titleOf` find one element each, so Playwright's strict mode holds.
- The light track still holds: the fix round changed frontend and test code only.
- Files re-read: the six files above (round 1 hunks), `tickets.py:518-540` (the `q`
  filter), `tickets_core.py:82` (serial format), `playwright.config.js`,
  `run_lanes.py:45-52`, and brief § 2.
