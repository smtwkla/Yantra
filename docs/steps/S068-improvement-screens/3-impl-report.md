```
Step: S068 — Improvement record: screens
Doc: impl-report
Author: Coder (Sonnet)
Date: 30-10-2026
```

# S068 — Implementation report

The screens of the improvement record are built on S067's API as it stands. No backend file changed.
All unit suites are green (backend 3461, frontend 298, tooling 185). The whole browser suite at
Normal is green (270 passed, 13 skipped, the existing skips). There are no questions for the user.

## 1. What was built

- **Ticket page:** `"Start improvement"` in the action bar (shown on `can_start_improvement`), and the
  line "Analysed in IM-… · Analysing" in the repeats box, one `div` per entry of `improvements`.
- **Dialog *Start improvement* / *Edit improvement*:** one dialog, fields Title, Problem, Lead.
- **Improvement page** `/tickets/improvements/<id>`: header, card *The problem* with `"Edit"`, card
  *Tickets (n)* with `"Add ticket"` and a remove button on each row the server marks `removable`.
- **Dialog *Add ticket*:** search box and a radio list.
- **Remove ticket:** inline confirmation on the row.
- **Tab *Improvements* on Tickets:** two tabs, the list `/tickets/improvements` with the *State* and
  *Unit* filters.

## 2. How it works

- **Routes** (`router/index.js`): `improvements` and `improvement-detail`, both under `/tickets/`, so the
  *Tickets* nav item stays lit. Neither is a nav item; the API's 403 / 404 is the gate.
- **`TicketsTabs.vue`:** shown only with `improvement:read`; the active tab follows the route name
  (`aria-current="page"`), not `router-link-active`.
- **`ImprovementDialog.vue`:** `openStart(ticket)` loads `GET /api/improvements/leads?ticket_id=` first,
  then opens with the title and problem from `defaultTitle` / `defaultProblem` and the user as lead when
  the user is in the list. `openChange(improvement)` loads the leads by `improvement_id`; a current
  lead who is no lead now stays in the select, last, marked "(not a lead now)". A refusal for a field
  the dialog does not show (`ticket_id`) appears at the top; a lead-list error also appears at the top.
  After a start, the ticket page goes to the new improvement's page; after an edit, the page takes the answer.
- **`AddTicketDialog.vue`:** no search lists the newest 10 tickets of the improvement's machine; text
  searches the site (`unit.site_id`). Tickets already in the improvement and not-a-fault tickets are left
  out. The refusal of the API ("TK-… is already in IM-…") shows under the list.
- **`ImprovementDetailView.vue`:** every write (edit, add, remove) answers with the whole detail, which
  replaces the page's copy. `"Edit"` and `"Add ticket"` show on `is_open` and `improvement:edit`; the
  remove button on `removable`. A ticket of another machine shows its machine code before the symptom.
- **`ImprovementsView.vue`:** the list on the pattern of `TicketsView` (filters and page in the URL
  query, `PagerBar`); a 403 shows "You can't see improvements." with no `"Retry"`.
- **`improvementLabels.js`:** `improvementStateLabel`, `lossText`, `defaultTitle`, `defaultProblem`,
  `IMPROVEMENT_STATE_FILTERS`. `lossText` uses `minutesText`'s default, so days count from 24 h.

## 3. Files touched

Code (9):
- `frontend/src/router/index.js` — the two routes.
- `frontend/src/components/TicketsTabs.vue` (new) — the two tabs.
- `frontend/src/views/TicketsView.vue` — `TicketsTabs` above the filter row.
- `frontend/src/views/ImprovementsView.vue` (new) — the list.
- `frontend/src/views/ImprovementDetailView.vue` (new) — the page.
- `frontend/src/views/improvements/ImprovementDialog.vue` (new) — start and edit.
- `frontend/src/views/improvements/AddTicketDialog.vue` (new) — the picker.
- `frontend/src/views/TicketDetailView.vue` — the button, the "Analysed in" line, the dialog. S066's `TicketShare` lines are untouched.
- `frontend/src/utils/improvementLabels.js` (new) — the pure helpers.

Tests (4 + 1 support):
- `frontend/tests/improvementLabels.test.js` (new) — 13 tests.
- `frontend/e2e/improvements.spec.js` (new) — 7 tests.
- `frontend/e2e/screens.spec.js` — the two routes; `beforeAll` starts an improvement.
- `frontend/e2e/support/improvements.js` (new) — `raiseFixed`, `startImprovementByApi` (see D-1).
- `frontend/e2e/tickets-work.spec.js` — unchanged; it ran again.

Docs (3): see *Docs updated*. Step files: this report, the brief's `Status`, the INDEX row.

## 4. Decisions taken

- **D-1. A support file `e2e/support/improvements.js`.** The brief says "the same body sets up the tickets
  of `improvements.spec.js`" and `screens.spec.js`. Two copies of the `restore` body would be a
  near-copy, so one helper serves both. It is a new file in `e2e/support/`, which is shared code (the
  whole suite ran anyway, § 8.4), so the WebKit run of *Shared code* was due; the code reviewer made it
  (`screens.spec.js --project=phone-webkit`: 9 passed, CR1-05). No existing support file changed.
- **D-2. The raise body of `raiseFixed`** is a degraded ticket by default (no downtime), or a breakdown
  stopped 60 min ago and fixed 10 min ago (50 min down), so the loss line changes in the add test.
- **D-3. `AddTicketDialog` uses `useFormModal` with `path: null` and `send`,** as `AssignDialog` does,
  because the post path holds the improvement's id and the composable's `path` is fixed at set-up. The
  brief said `path` and `toBody`; the request and the refusal field (`ticket_id`) are the same.
- **D-4. "Choose a ticket"** shows beside the list when `"Add ticket"` is pressed with no row chosen
  (the server's wording for the same case; AssignDialog does the same with "Choose a person").
- **D-5. A ticket row with no symptom** reads "No symptom" on the improvement page; the downtime part
  is left out when it is 0.
- **D-6. The empty list texts:** a Unit filter set gives "No improvements match these filters."; with no
  unit filter, *Closed* gives "No closed improvements yet." and *Open* "No open improvements." (a State
  choice is not a filter).
- **D-7. The Add ticket dialog** carries one help line under the search box ("Without a search, the newest
  tickets of HP003 show. A search looks at every ticket of the site."). The brief did not write the
  words; they explain the two modes for the floor.
- **D-8. The `"Start improvement"` dialog opens after the lead list has loaded,** so the lead is set before
  the dialog snapshot (no false "dirty"). Opening takes one request longer.
- **D-9. The machine code on each *Add ticket* row** (`HP003 · problem`). The brief § 5.3 lists none. It stays
  (CR1-06): the search covers every ticket of the site, so tickets of other machines can be added, and the
  code tells them apart.

## 5. Not done, deferred or assumed

- Everything in the brief's *Out of scope* (why-why, countermeasures, states, close, alerts, lessons,
  register, *Suggested*; the yellow hint; counts on the *Open* / *Closed* choice).
- `.claude/CLAUDE.md` is not edited (orchestrator's instruction); the text is under *Proposed CLAUDE.md changes*.
- Browser runs were on `phone-chromium` (every test) and `desktop-chromium` (the `@device` tests). No
  `phone-webkit` run by the coder. A new file in `e2e/support/` counts as a change there, so the run was
  due; the code reviewer made it (`screens.spec.js --project=phone-webkit`, 9 passed).
- Assumed: `ticket.improvements` is always an array (S067 `_improvement_fields` gives `[]`).

## Tests

- **Frontend unit, alone:** `tests/improvementLabels.test.js` — 13 passed.
- **Build:** `npx vite build` in `frontend/` — clean (the usual chunk-size warning only).
- **New browser tests alone** (`E2E_LANES=1`, `phone-chromium`, `-g S068`): 7 passed. The first run
  showed two failures: the 409 and the 403 are the tests' expected refusals, so each test now names its
  request with `consoleWatch.allowFailedRequest` (the S024 convention).
- **Targeted** (`improvements`, `tickets-work`, `screens`, Normal): 60 passed, 2 skipped.
- **All unit suites once** (`YANTRA_TEST_RUN=s068c1 tooling/run-tests.bat`): backend 3461 passed,
  frontend 298 passed, tooling 185 passed. ALL SUITES PASSED.
- **Whole browser suite at Normal, once** (router is shared code): 270 passed, 13 skipped, 0 failed;
  "All lanes done in 158 s".

## Fix rounds

### Round 1

- **CR1-01 (major) — Fixed.** `ImprovementDetailView.vue`: the remove button shows on
  `canEdit && t.removable && confirmingRemoveId !== t.id`. The operator test now adds a second ticket of
  the machine by API (new helper `addTicketByApi` in `e2e/support/improvements.js`), so both rows are
  `removable` and `removeButtons` count 0 is a real check; it also checks the second row is visible.
  Fails without the fix: `expect(removeButtons).toHaveCount(0)` Expected 0, Received 2 (improvements.spec.js:140);
  passes with it.
- **CR1-02 — Fixed.** `allowFailedRequest` names `/api/improvements/${improvement.id}/tickets` (set after the improvement exists).
- **CR1-03 — Fixed.** `ImprovementDialog.vue`: the "(not a lead now)" row is left out while `leadsError` is set.
- **CR1-04 — Fixed.** `ImprovementDialog` exposes `loadingLeads`; the *Start improvement* button on the ticket page is
  disabled and shows a spinner until the dialog opens.
- **CR1-05 — Fixed.** D-1 and § 5 corrected; the reviewer's WebKit run is recorded.
- **CR1-06 — Kept, as a departure.** D-9 above.
- **CR1-07 — Fixed.** Both *Add ticket* tests wait for the first radio, then call `expectDialogFits`.
- No unit test file changed, so no unit suite was run. No backend file changed.
- **Runs:** operator test alone (`phone-chromium`): red before the fix, green after. `npx vite build`: clean.
  `tooling/run-e2e-tests.bat e2e/improvements.spec.js e2e/screens.spec.js`: 24 passed, 1 skipped.
  (An earlier run of these plus `tickets-work` had one failure, my CR1-02 edit used `improvement` before its
  declaration; fixed and re-run.)
- **Docs updated:** none, because no behaviour the docs describe changed.

### Feedback (round 1)

- none

## Manual checks

- [auto] Start an improvement from a back-in-service ticket (filled fields, lands on the page, "Analysed in", button gone) — `frontend/e2e/improvements.spec.js::S068: the engineer starts an improvement from a back-in-service ticket and lands on its page`
- [auto] Add a second ticket, loss changes, remove it, the last ticket has no remove button, no sideways scroll — `frontend/e2e/improvements.spec.js::S068: the engineer adds a ticket and removes it again; the machine's last ticket stays`
- [auto] The Improvements tab lists it, the Unit filter hides it, Closed is empty — `frontend/e2e/improvements.spec.js::S068: the Improvements tab lists the improvement, the Unit filter narrows, Closed is empty`
- [auto] The operator sees no change buttons; the ticket page shows "Analysed in" and no Start button — `frontend/e2e/improvements.spec.js::S068: the operator sees the improvement but no button to change it`
- [auto] A ticket in another open improvement is refused beside the list — `frontend/e2e/improvements.spec.js::S068: a ticket that is in another open improvement is refused beside the list`
- [auto] The storekeeper sees "You can't see improvements." and no Retry — `frontend/e2e/improvements.spec.js::S068: the storekeeper typing the list address sees a plain line and no Retry`
- [auto] Both routes open for every ticket role — `frontend/e2e/screens.spec.js::every screen opens as <role>`
- [auto] Edit the problem text (extra, not in the brief) — `frontend/e2e/improvements.spec.js::S068: the engineer edits the problem text`
- Real device (not important): a Tamil problem text typed on an Android phone shows the same on a desktop.
  Added as row 49 of `docs/steps/device-checks.md`.

## Docs updated

- `docs/Plan.MD` § 6 *Screens*, Phone list: one bullet for the *Improvements* tab and the improvement page.
- `docs/steps/device-checks.md` — row 49 (S068, the Tamil text).
- `.claude/CLAUDE.md` — not edited; see below.
- `docs/schema.md`, `docs/schema.html`: none, because no migration.
- Step files: the brief's `Status` is `In code review`; the INDEX row of S068 too.

## Proposed CLAUDE.md changes

In `.claude/CLAUDE.md` § SMTW-Review, bullet **Browser tests**, in the list of spec files and steps, insert
after `` `tickets-notes` S027, `` :

> `improvements` S067/S068,

(`screens` keeps "every route and S064"; S068 adds two routes to it.) Also in the same list, `tickets-work`
needs no change.

## Feedback

- idea: a Bash tool call with a quoted heredoc that held an apostrophe inside a JS string failed with
  "unexpected EOF" and wrote nothing (2 calls, about 3 min); the Write tool worked. The step skill could
  say "write files with Write, not heredocs".
- hindrance: `tooling/run-e2e-tests.bat` printed 60 lines of test progress on each run; with `tail` it was
  fine, but the failing test's message was in the middle (2 runs).

### Round 2 (orchestrator, 30-10-2026)

- **CR2-01 (nit), fixed** in `frontend/src/views/improvements/ImprovementDialog.vue`: when the lead list fails to load in an edit, the current lead stays in the select by plain name (no "(not a lead now)" mark), so the select is never empty. A three-line change; made by the orchestrator, not a coder.
- **Runs:** `npx vite build` clean; `tooling/run-e2e-tests.bat e2e/improvements.spec.js` 7 passed.
