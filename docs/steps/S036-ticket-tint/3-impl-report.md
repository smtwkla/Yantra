Step: S036 — Ticket tint by intensity
Doc: impl report
Author: Coder (Sonnet)
Date: 24-10-2026

# S036 — Implementation report

## 1. What was built

An open ticket now has a mild background by intensity: Breakdown pink, Defect yellow, Defect · initial grey. A closed ticket stays plain. The tint shows on the Tickets list rows, the Me page's ticket tabs, the Open tickets rows on the equipment page, and the title row of the ticket page. The intensity badge is unchanged, so colour is never the only sign.

## 2. How it works

- `ticketTint(ticket)` in `ticketLabels.js` returns the Bootstrap colour name (`danger`, `warning`, `secondary`) from `INTENSITY_TINT`, or `null` for a closed ticket or an unknown intensity.
- Rows (`TicketRow.vue`, equipment Open tickets) add `list-group-item-<name>` and `ticket-tinted`. Bootstrap's variant sets the background, border and hover colours, so a row still shows it is a link.
- The ticket page title row adds `bg-<name>-subtle border border-<name>-subtle rounded px-2 py-1`.
- One CSS rule in `main.css` draws `.text-secondary` inside `.ticket-tinted` in `--bs-secondary-text-emphasis`, because `#6c757d` is below 4.5:1 on the tints (brief § 2).

## 3. Files touched (8; round 1 adds no new file)

- `frontend/src/utils/ticketLabels.js`: `INTENSITY_TINT`, `ticketTint`.
- `frontend/src/components/TicketRow.vue`: tint classes on the row.
- `frontend/src/views/EquipmentDetailView.vue`: tint classes on the Open tickets rows.
- `frontend/src/views/TicketDetailView.vue`: tint classes on the title row.
- `frontend/src/assets/main.css`: the `.ticket-tinted .text-secondary` rule.
- `frontend/tests/ticketLabels.test.js`: three `ticketTint` cases.
- `frontend/e2e/tickets-work.spec.js`: the S036 e2e test (plus `causeId` in its import).
- `docs/steps/device-checks.md`: row 31.
- The brief's Status is set to In code review. I did not touch `docs/steps/README.md` (the index row still says Approved).

## 4. Decisions taken

- None outside the brief. The title row is found in the test as `div:has(> h4)`; I added no test id because the app has none.

## 5. Not done, deferred or assumed

- Nothing deferred. No red-run of the new e2e test on the old code: this is a feature, not a fix round.

## 6. Tests

- Full run `YANTRA_TEST_RUN=s036c1 tooling/run-tests.bat`: backend 2520 passed, frontend 142 passed, deps 42 passed, tooling 106 passed. `npx vite build` built.
- Targeted e2e (`tickets-work`, `me`, `equipment`, `screens`; six lanes, three projects): **147 passed, 0 failed, 0 skipped, 0 flaky, 147 total**. No failure from S041's S033 test appeared in this run.

## Fix rounds

### Round 1

All three findings fixed.

- **CR1-01 (minor): Fixed.** The e2e test now opens `/tickets?state=all&q=S036 tint` and finds each row by the ticket's serial (`rowOf(ticket)`, with the tickets `raiseByApi` returns). Only this test's tickets are on the page, and a second project on the same database finds one row per serial. Red run: not possible without a failing scenario. The fault shows only with two projects on one database (`E2E_LANES=1`) or past 50 newer tickets, and the old test passes in the six-lane split. Green: `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "S036"` passed on all 3 projects, and the full `tickets-work.spec.js` on one lane passed the S036 test on all 3 projects.
- **CR1-02 (nit): Fixed.** `TicketDetailView.vue` has `data-testid="ticket-title"` on the title row. The test uses `page.getByTestId("ticket-title")`.
- **CR1-03 (nit): Fixed.** New `ticketRowClass(ticket)` in `ticketLabels.js` returns `["list-group-item-<tint>", "ticket-tinted"]` or `null`. `TicketRow.vue` and `EquipmentDetailView.vue` use it. New vitest case "builds the row class from the tint, and none for a closed ticket". It is a new helper, not a fix to a fault, so no red run.

**Brief slip (for the planner).** Brief § 2's table names the darker grey `#343a40`. The code uses `--bs-secondary-text-emphasis`, which is `#2b2f32` in Bootstrap 5.3.8. Ratios are higher than the table says. I did not edit the brief.

Files touched in this round (6): `ticketLabels.js`, `TicketRow.vue`, `EquipmentDetailView.vue`, `TicketDetailView.vue` (test id), `frontend/tests/ticketLabels.test.js`, `frontend/e2e/tickets-work.spec.js`.

Tests of this round:
- `YANTRA_TEST_RUN=s036c2 tooling/run-tests.bat`: backend 2520, frontend 143, deps 42, tooling 106, all passed. `npx vite build` built.
- e2e `tickets-work`, `equipment`, `me` (six lanes, three projects): **123 passed**.
- e2e `tickets-work` with `E2E_LANES=1`: **64 passed, 2 failed**: the older `S034: In 14 days …` test (phone-webkit, desktop-chromium; `toHaveCount(1)` received 2). Playwright runs with `retries: 0`, and it fails every time when two projects share one database, so it is a fault of that older test, not a flake (S036 CR2-01). It is not part of this step; a fix-lane step is proposed.

## Manual checks

- [auto] Important. Open breakdown pink, open defect yellow, closed ticket white on the Tickets list (filter All); the breakdown's ticket page title panel pink, a closed ticket's panel plain — `frontend/e2e/tickets-work.spec.js`::`S036: open tickets are tinted by intensity (pink, yellow); a closed ticket and its page are plain`
- On a phone on the shop floor, the three tints can be told apart in daylight and under the hall lights (any login with Tickets). Row 31 of `docs/steps/device-checks.md`.

### Round 2

- CR2-01 (nit): Fixed — the S034 line above no longer says "flaky" (by the orchestrator; a docs-only fix, no new review).
