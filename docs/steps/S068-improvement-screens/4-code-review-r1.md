```
Step: S068 — Improvement record: screens
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S068 — Code review, round 1

**Verdict: one `major` finding is open (CR1-01).** A user without `improvement:edit` sees a
remove button that the API refuses. Everything else is minor polish (6 nits).

## Test runs (mine)

- **All unit suites** (`YANTRA_TEST_RUN=s068cr1 tooling/run-tests.bat`): backend 3461 passed,
  frontend 298 passed, tooling 185 passed. ALL SUITES PASSED.
- **Build** (`npx vite build` in `frontend/`): clean; only the usual chunk-size warning.
- **Browser, for CR1-05** (`tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`,
  the WebKit container): 9 passed (1.3 min). The two new routes open on the iPhone for every
  ticket role.
- I did not run the whole browser suite. The coder's runs are named in the report: the new tests
  alone (7 passed), the targeted run `improvements`, `tickets-work`, `screens` (60 passed,
  2 skipped), and the whole suite at Normal once (270 passed, 13 skipped). The router is
  shared code, so that whole-suite run was due. The specs are the right ones.

## Findings

### CR1-01 (major) — the remove button shows to users who may not remove

- **Where:** `frontend/src/views/ImprovementDetailView.vue:173`
  (`v-if="t.removable && confirmingRemoveId !== t.id"`). The flag comes from
  `backend/improvements.py:239`: `removable = open_now and removal_error(...) is None`. It holds
  only the machine rule and the open state, and no permission (S067 § 5.3 defines it so).
- **Problem:** the page shows the remove button on `removable` alone. The *Edit* and *Add ticket*
  buttons check `canEdit` (line 38: `is_open` and `improvement:edit` in `permissions`), but the
  remove button does not. Brief § 2 says "no button ends in a refusal", § 8.1 says the operator
  sees no remove button, and D6 names `permissions` among the flags the controls follow.
- **Failure scenario:** an engineer adds a second ticket of HP003 to IM-2026-10-001. Both rows are
  now `removable`. An operator, technician or supervisor opens the page from the "Analysed in"
  line. They see a red unlink button on both rows, tap it, confirm "Remove ticket", and get a 403
  under the row. The same happens to an engineer who holds `improvement:edit` only at another
  site.
- **Why the tests did not catch it:** the operator test (`frontend/e2e/improvements.spec.js:126`)
  starts an improvement with one ticket. One ticket of the machine is never `removable`, so
  `removeButtons(page)` has count 0 for every user, and that assertion proves nothing.
- **Fix:**
  1. Show the button on `canEdit && t.removable`.
  2. In the operator test, add a second ticket of the same machine by API before the operator opens
     the page, so two rows are `removable` and the count of 0 is a real check. Record the test red
     before the fix and green after it.

## Nits

- **CR1-02** (nit) `frontend/e2e/improvements.spec.js:143`: `allowFailedRequest("/tickets", 409)`
  allows every 409 whose URL holds `/tickets`, `/api/tickets/…` included. Name the request after
  the set-up instead: `` `/api/improvements/${improvement.id}/tickets` ``.
- **CR1-03** (nit) `frontend/src/views/improvements/ImprovementDialog.vue:46`: when the lead list
  fails to load in an edit, `leads` is empty, so the current lead is marked "(not a lead now)"
  although nobody knows that. Leave the mark out while `leadsError` is set.
- **CR1-04** (nit) `frontend/src/views/improvements/ImprovementDialog.vue:61`: `openStart` waits
  for the lead list before the dialog opens (D-8). On slow plant Wi-Fi the tap on
  `"Start improvement"` shows nothing for a moment, and a second tap starts a second load. Disable
  the button, or show its spinner, until the dialog opens.
- **CR1-05** (nit) `3-impl-report.md` § 5 and D-1: the report says no WebKit run was due because
  "neither `api.js` nor an existing `e2e/support/` file changed". The setting (*Shared code*) says
  "a change to `api.js` or `e2e/support/`", and a new file there is such a change. My run settles
  it (9 passed, above). Record that run in the report instead of the narrowed rule.
- **CR1-06** (nit) `frontend/src/views/improvements/AddTicketDialog.vue:112`: each row shows the
  machine code before the problem. Brief § 5.3 lists no machine code for the rows. It helps in a
  site search, so keep it, and add it to the report's *Decisions taken*.
- **CR1-07** (nit) `frontend/e2e/improvements.spec.js:59` and `:151`: `expectDialogFits` on
  *Add ticket* runs right after the tap, so it can measure the dialog in its "Loading…" state.
  Wait for the first radio, then check the fit, so the check measures the filled list.

## Manual browser checks for the user

- None important. Row 49 of `docs/steps/device-checks.md` (a Tamil problem text typed on an
  Android phone reads the same on a desktop) is a plain real-device check, as the brief says.
- After CR1-01: open an improvement with two tickets of its machine as the operator and see no
  remove button. The fixed test covers this; a look by hand is optional.

## Checked and found consistent

- **Scope:** every item of brief § 1 is built: the button, the dialog, the page, *Add ticket*,
  *Remove ticket*, the "Analysed in" line and the tab. Nothing beyond the brief, apart from the
  departures D-1…D-8, which the report lists, and CR1-06.
- **D-1** (`e2e/support/improvements.js`): one helper for the `restore` body, used by two specs,
  is the right call (DRY). No existing support file changed.
- **D-3** (`path: null` and `send`, as `AssignDialog`) and **D-4** ("Choose a ticket" instead of a
  disabled button) are sound. D-4 also follows hidden-or-explained over disabled.
- **Router:** the two routes sit under `/tickets/`, so `isActivePath` keeps *Tickets* lit. Neither
  is a nav item, so `canOpenRoute` lets them through, and the API's 403 and 404 are the gate. The
  `(\d+)` constraint and the static `/tickets/improvements` path do not clash with
  `/tickets/:id(\d+)` or `/tickets/new`. No nav item was added.
- **Tabs:** `TicketsTabs.vue` shows only with `improvement:read`, and the active tab follows the
  route name with `aria-current="page"`. The storekeeper sees no tabs.
- **Hidden, not disabled:** `"Start improvement"` shows on `can_start_improvement`, and *Edit* and
  *Add ticket* show on `canEdit`. The remove button is the exception (CR1-01).
- **States:** the list's 403 shows "You can't see improvements." with no `"Retry"`. The page's 404
  shows "Improvement not found, or not at your units." with *Back to the list*, and its 403 shows
  "You can't see this improvement.". Other errors (503 included) show the message with
  `"Retry"`. A user with no units sees `NO_UNITS_TEXT`. A login with no Team record holds no
  `improvement:read`, so it sees no tab, and a typed address gives the 403 line, not a blank page.
- **One answer, one page copy:** edit, add and remove replace the page's copy with the API's
  detail (`onSaved`). The ticket page's writes all come from one `_detail`, so
  `ticket.improvements` is always an array.
- **Dialogs:** `FormModal` is `modal-dialog-scrollable modal-fullscreen-sm-down`, so the footer
  stays on a phone screen while the list of up to 10 rows scrolls. Every dialog the specs open
  calls `expectDialogFits`: start, edit and *Add ticket* (twice). Remove is inline, as the brief
  says, with `"Remove ticket"` (`btn-danger`) and `"Cancel"` and the consequence in the line.
- **Phone layout:** no fixed widths and no `btn-sm`. The page buttons are `btn btn-outline-primary`
  as on the ticket page, the filters wrap, and the test checks `expectNoSidewaysScroll`.
- **Screen text (scope B):** the labels, help lines and empty texts are short and plain, and every
  button starts with a verb. "Choose a ticket" and "Choose a lead" match the app's other pickers.
- **Pure helpers:** `improvementLabels.js` has no state or framework imports. `lossText` uses
  `minutesText`'s default (days from 24 h), so it reads as the ticket rows on the same page. The
  13 unit tests cover § 8.2's list, the cuts at 120 and 2000 characters included.
- **Backend heavy:** the screens decide no rule. The not-a-fault and already-linked rows are left
  out of the picker as the brief says, and the API judges the rest.
- **Tests:** each *Automated* check of § 8.1 has a test that asserts what the user sees (fields,
  badge, rows, loss line, counts, the refusal beside the list, the 403 line). The exception is the
  operator's remove button (CR1-01). No new test is `@device`, which is right: none checks a
  layout. `screens.spec.js` has the two rows, and its `improvement` is set in `beforeAll` before
  `screens()` reads it.
- **Docs pass:** `docs/Plan.MD` § 6 has the new bullet, and `docs/steps/device-checks.md` has
  row 49. No migration, so no schema docs. `.claude/CLAUDE.md` was left out on the orchestrator's
  instruction, and the report proposes the spec-map line.
- **Manual checks:** the report's `## Manual checks` carries both important checks of the brief as
  `[auto]` with their tests, and the real-device check as a plain line.
- **Security:** no route, key or SQL changed. No actor comes from the client: the lead is a choice
  that the API checks (`_check_lead`).

## Feedback

- rule: *Shared code* says "a change to `api.js` or `e2e/support/`" and the coder read it as
  "an existing file in `e2e/support/`". The rule could say whether a new support file counts,
  and why: the WebKit fault was about `api.js` and the console watch (D-1; one extra 1.3 min run).
- idea: the brief reviewer and the brief took S067's `removable` as the whole condition for the
  remove button. A one-line note in an API's flag ("no permission inside") would have caught
  CR1-01 at gate A (`backend/improvements.py:239`, brief § 5.4).
- hindrance: the Bash tool blocks `sleep`, and the e2e wrapper piped to `tail` prints nothing
  until it ends. I waited with an until-loop on the output file (one extra call).
