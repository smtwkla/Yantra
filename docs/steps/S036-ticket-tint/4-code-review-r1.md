Step: S036 — Ticket tint by intensity
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026

# S036 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open. One `minor` finding and two nits.**
The code does what the brief asks, on the three screens it names, with the classes and
the one CSS rule of § 3. The contrast claims hold for the CSS as written. The tests are
green.

## Test results (my runs, `YANTRA_TEST_RUN=s036cr1`)

- `tooling/run-tests.bat`: all suites passed. Backend 2520, frontend 142, deps 42,
  tooling 106.
- `npx vite build` in `frontend/`: built (only the old chunk-size warning).
- `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/me.spec.js
  e2e/equipment.spec.js e2e/screens.spec.js`: **147 passed**, 0 failed, in 2.3 min.
  These are the specs of the screens the step changed (Tickets list and ticket page:
  `tickets-work`; Me page: `me`; equipment page: `equipment`) plus `screens`. The step
  changes no shared frontend code, so the full suite is not needed.

## Contrast check against the CSS written

I checked the claims of brief § 2 against Bootstrap 5.3.8 (`node_modules/bootstrap`,
version 5.3.8) and computed the ratios again with the WCAG formula.

| Text | pink `#f8d7da` | yellow `#fff3cd` | grey `#e2e3e5` | pink hover `#f1aeb5` | yellow hover `#ffe69c` | grey hover `#c4c8cb` |
|---|---|---|---|---|---|---|
| `.text-secondary` in a tinted row: `--bs-secondary-text-emphasis` = `#2b2f32` | 10.11 | 12.19 | 10.51 | 7.37 | 10.96 | 8.02 |
| row text at rest: `rgba(33,37,41,.75)` blended | 5.73 | 6.37 | 5.86 | — | — | — |
| row text on hover and press: `--bs-emphasis-color` `#000` | — | — | — | 11.46 | 17.05 | 12.47 |
| `#6c757d` without the S036 rule (for reference) | 3.51 | 4.23 | 3.65 | 2.56 | 3.81 | 2.78 |

- Fact: every text on a tint passes 4.5:1 (SC 1.4.3).
- Fact: the variant sets `--bs-list-group-action-hover-color` to `--bs-emphasis-color`.
  So on hover and press the row text is black, not the 75 % grey. The brief's hover figures
  (4.79, 6.06, 4.98) are the worst case; the real ones are higher.
- Fact: the brief's table names "darker grey `#343a40`", but § 1.4 and the code use
  `--bs-secondary-text-emphasis`, which is `#2b2f32` in 5.3.8. It is darker, so the
  ratios are higher than the table says. This is a brief wording slip, not a code fault.
- Fact: `.ticket-tinted .text-secondary` (two classes, `!important`) beats Bootstrap's
  `.text-secondary` (one class, `!important`) by specificity, whatever the load order.
  `main.css` also loads after Bootstrap (`main.js:2,5`).
- Fact: the badges keep their own colours on a tint. White on the `Overdue since` badge
  (`#dc3545`) is 4.53; white on the grey intensity badge (`#6c757d`) is 4.69.

## E2E colour assertions

- `rgb(248, 215, 218)`, `rgb(255, 243, 205)` and `rgb(255, 255, 255)` are
  `--bs-danger-bg-subtle`, `--bs-warning-bg-subtle` and `--bs-body-bg`. They match
  what the user sees on a row at rest.
- The title panel is `rgb(248, 215, 218)` on the breakdown, and `rgba(0, 0, 0, 0)`
  (no background) on the closed ticket. Both are right for `bg-danger-subtle` and for a
  plain `div`.
- The test asserts the computed background, not only class names (BR1-02 met).

## Findings

### CR1-01 (minor) — the list rows are found by a description that is not unique per run

`frontend/e2e/tickets-work.spec.js:529-532`

**Problem.** `rowOf` finds the row by its description text ("S036 tint: breakdown").
The Tickets list (filter *All*) is sorted newest first and shows 50 rows a page
(`tickets.py:589`, `TicketsView.vue:30`). The breakdown is raised 5 minutes in the past.

**Failure scenarios.**
1. With `E2E_LANES=1`, or a shard that runs `tickets-work.spec.js` for two projects on one
   database, the second project's run finds two "S036 tint: breakdown" rows. `toHaveCSS`
   then fails on Playwright's strict mode (the locator resolves to two elements).
   Today's split (6 lanes, 4 specs) put each project in its own lane, so the run passed.
2. In a full run, a lane where more than 50 tickets with a later `occurred_at` were raised
   pushes the breakdown off page 1, and the row is not found.

The S034 test at line 513 has the same first weakness (`toHaveCount(1)`); it is older and
not part of this finding.

**Suggested fix.** Find each row by its serial, which is unique: `rowOf(breakdown.serial)`,
and keep the returned tickets of the defect and the closed one. Open the list as
`/tickets?state=all&q=S036 tint`, so only this test's tickets are on the page.

## Nits

- **CR1-02** (nit) `frontend/e2e/tickets-work.spec.js:534`: `div:has(> h4)` plus
  `.first()` depends on the title row being the first `div` with an `h4` child; a test id
  on the title row (`data-testid="ticket-title"`) would say what it finds.
- **CR1-03** (nit) `frontend/src/components/TicketRow.vue:19` and
  `frontend/src/views/EquipmentDetailView.vue:206`: the same class expression is in two
  places; a small `ticketRowClass(ticket)` in `ticketLabels.js` would keep the two rows in
  step. Brief decision 4 asked only for the colour name helper, so this is optional.

## Scope and decisions

- Fact: everything in brief § 3 is built, and nothing else: the helper and map, the two
  row screens, the title panel without `ticket-tinted` (BR1-04), the one CSS rule, the unit
  cases, the e2e test, and device-checks row 31.
- Fact: the Me page's *Activity* tab (`MeView.vue:163-178`) is not tinted. That is right:
  its rows are events, and the brief names only the two ticket tabs.
- Fact: "Decisions taken" says none outside the brief. I found no unreported departure.
- Fact: the step meets every light-track criterion (frontend only, 7 code files, no
  migration, RBAC, endpoint or dependency).

## Use on the floor (UX)

- No new dialog, button, message or confirmation. No screen text changed.
- The tint uses Bootstrap's list-group variants, so the hover and press colours still show
  that a row is a link.
- No fixed widths. The title panel only adds padding (`px-2 py-1`), and it wraps as before
  (`flex-wrap`).
- Colour is never the only sign: the intensity badge keeps its words (SC 1.4.1).

## Manual checks

The impl report's `## Manual checks` carries both checks of the brief:

- `[auto]` the important check, with a passing run behind it (my run: 3 projects, green).
- Row 31 of `docs/steps/device-checks.md`, not important: on a phone on the shop floor,
  the three tints can be told apart in daylight and under the hall lights.

**Still for the user, in a browser:** none beyond row 31. Optionally, look at the Tickets
list once with an *Early signs* ticket open, because the e2e test does not assert the grey
tint (the unit test covers its colour name).

## Checked and found consistent

- `ticketTint`: `null` for `closed` and for an unknown intensity; *back in service* is
  tinted (unit tests cover all three cases of brief § 5).
- `:class="ticketTint(t) && [...]"` gives `null` on a closed ticket, which Vue ignores.
- The equipment page's rows come from `state=open`, so they are always tinted.
- The ticket page's title panel holds no `.text-secondary`, so it needs no `ticket-tinted`.
- No dark theme exists in `frontend/src`; the tokens follow Bootstrap's dark values if one
  comes.
- The impl report is in scope A; the CSS comment says why.
- Files read: `ticketLabels.js`, `TicketRow.vue`, `EquipmentDetailView.vue` (Open tickets
  card), `TicketDetailView.vue` (title row), `IntensityBadge.vue`, `MeView.vue` (lists),
  `main.css`, `main.js`, the test diffs, `device-checks.md` row 31, Bootstrap 5.3.8's
  list-group and colour tokens, and the Tickets list query in `tickets.py`.
