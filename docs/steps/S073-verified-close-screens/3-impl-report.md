```
Step: S073 — Verified close: screens
Doc: impl-report
Author: Coder (Sonnet)
Date: 30-10-2026
```

# S073 — implementation report

**Result:** the screens of R05.4 are built as the brief says. No route, table or key was added and no
backend file changed. All unit suites, the build and the whole browser suite are green (§ 7). No
question for the user. Departures from the brief are in § 4.

## 1. What was built

On the improvement page (`ImprovementDetailView.vue`):

- **The header.** The badge shows every state in the plain words (colours: *Ready to verify* yellow,
  *Closed: it worked* green, *Closed: did not work* red, *Dropped* grey). A line under S068's
  "Started …" line says the watch: before it starts "Watch: 90 days after the last countermeasure
  is done" with `Change watch`; "Watching since 20-11-2026 · until 18-02-2027"; "Watched 90 days,
  until 18-02-2027 · ready to verify"; or "Closed 18-02-2027 by Arun (manager): it worked" (", the
  lead" after the name when the lead closed it), with the remark under it. Links "Follow-up of
  IM-…" and "Analysed again in IM-…".
- **The card *Did it come back?*** once the watch has started: the one-line fact (no repeat in green;
  repeats in a warning with each ticket linked and "after the watch" where it applies; or "The
  linked tickets have no symptom yet …"), the machines checked, the table (breakdowns, those with
  the symptom, downtime; before against after, the third header "N days so far" or "N days
  after"), and for a holder of `can_verify` the two buttons. An operator sees "Ready to verify. An
  engineer or manager of the site decides." and no buttons.
- **The dialog *Verify*** (both modes): the fact line, the consequence, the remark. *Close: it
  worked* has an optional remark; *Did not work — analyse again* needs one and goes to the new
  improvement.
- **The dialog *Watch*** (30–365 days, the end date it gives), **the dialog *Drop improvement***
  (reason and consequence; the button is at the page's foot) and **the card *Timeline*** (newest
  first, 10 and *Show all*, "Was: …" for a replaced text, the computed *Watch ended* line without
  a person) with **the dialog *Add note***.
- A closed or dropped improvement shows no write control: every button follows S072's `can_*` flags
  and S067's `is_open`.

## 2. How it works

- `improvementLabels.js` holds the words and the small builders: `IMPROVEMENT_EVENT_LABELS` /
  `eventLabel`, `watchLine`, `closedLine`, `figureRows`, `repeatText`, `watchEndDate` (calendar
  arithmetic on the date part in UTC, so no browser zone), the bounds, and
  `improvementStateBadgeClass`. `datetime.js` gains `formatDate` (the date part of `formatDateTime`).
- The page decides only what to show: the watch card when `watch.from` is set; `Change watch` in the
  header when it is not (one button at a time). Every write answers with the whole detail, which
  replaces the page's copy (`onSaved`), as the other dialogs do.
- The three close-type dialogs follow `MoveDialog`: `useFormModal` with `path: null`, `blank(seed =
  {})`, a refusal beside its field (`remark`, `reason`, `watch_days`), a 409 with no field at the top
  plus `reload`. `VerifyDialog` keeps the mode in a ref set by `open(mode)`; after a *did not work*
  save the router goes to the follow-up's page.
- The watch's figures, start and end are S072's; the screen computes only the end date the *Watch*
  dialog previews from `watch.from`.

## 3. Files touched (12 code and test files, 2 docs, plus the index and the brief's status)

| File | Change |
|---|---|
| `frontend/src/views/ImprovementDetailView.vue` | the state line and badge colour, the follow-up links, the watch card, the timeline, *Drop improvement* at the foot, three dialogs |
| `frontend/src/views/improvements/WatchCard.vue` | new: the card *Did it come back?* |
| `frontend/src/views/improvements/WatchSummary.vue` | new: the one-line fact, shared by the card and the Verify dialog (§ 4, D-1) |
| `frontend/src/views/improvements/VerifyDialog.vue` | new |
| `frontend/src/views/improvements/WatchDialog.vue` | new |
| `frontend/src/views/improvements/DropDialog.vue` | new |
| `frontend/src/views/improvements/ImprovementTimeline.vue` | new: the card *Timeline* |
| `frontend/src/views/improvements/ImprovementNoteDialog.vue` | new |
| `frontend/src/utils/improvementLabels.js` | the builders and words of § 2 |
| `frontend/src/utils/datetime.js` | `formatDate` |
| `frontend/tests/improvementLabels.test.js`, `frontend/tests/datetime.test.js` | unit tests (§ 8.2) |
| `frontend/e2e/improvements.spec.js` | six S073 tests, `readyImprovement`, two locator fixes, `closeByApi` takes an optional symptom |
| `docs/Plan.MD`, `docs/steps/INDEX.md`, brief `Status` | docs pass and hand-over |

## 4. Decisions taken

- **D-1: `WatchSummary.vue`, a shared component** (not in the brief's file list). The brief wants the
  same summary words in the card and in the Verify dialog (D2); one component avoids pasting the
  block twice. Seventeen lines of template.
- **D-2: `figureRows(figures, closed, ended = false)`** has a third argument. The brief's two-argument
  form cannot tell a ready (ended, not closed) watch from a running one; BR2-01 asks "after" for
  both `closed` and `watch.ended`.
- **D-3: `repeatText(repeat)` returns the text after the serial** ("on 05-01-2027 (Won't start,
  breakdown)"), because each serial is a link in the component.
- **D-4: the header line while the state is *Analysing* or *Actions open* is the "Watch: N days after
  …" line** when `watch.from` is set, and the card is hidden when it is null. (Corrected in fix round 1:
  the first text said `watch.from` stays set after a *Corrective* sends the state back to *Actions
  open*. It does not: `_settle_state`, `backend/improvements.py:280`, sets `watch_from` to NULL when the
  state is not *Watching*, so on an *Actions open* page `watch.from` is null, the card is hidden and the
  header carries `Change watch`. The code handles both cases; no code change.)
- **D-5: the e2e set-up uses the MCC1 mill, not the seed extruder.** The first run showed that other
  specs close tickets on the extruder with the same first symptom, so the card correctly listed them
  as repeats ("after the watch") and "No ticket with the symptom …" failed. The mill has no closed
  ticket with a symptom in any spec. The repeat test uses the extruder gearbox and asserts the
  warning and the link to its own ticket, not the count.
- **D-6: two locator changes.** Besides `improvements.spec.js:43` (the brief, BR1-01), the S068 edit
  test `getByText("S068 edit: the contactor chatters …")` met a second element, the timeline's
  "Changed" line; it now reads `.problem-text`. Not in the brief's list.
- **D-7:** `closeByApi` (spec) takes an optional symptom id, so the repeat ticket is closed with the
  same symptom as the first. S069's CR1-06 asked for `closeByApi` to move to `e2e/support/` when
  this step needs it: it does not (same file), so it stays. `e2e/support/` and `api.js` are
  unchanged, so no WebKit run was needed.
- **D-8: the state line of a *Ready to verify* page reads "Watched 90 days, until …"** from
  `watch.days`, which is the length set, as the brief's example.

## 5. Stale brief check (yours, first)

Checked the brief's fields, routes and files against S072's `improvements.py` / `improvements_core.py`
and the S068–S071 screens in the tree. No difference changes the design.

| Brief says | Code now | Done |
|---|---|---|
| Detail fields `watch {days, from, until, ended, figures}`, `closed {at, by_name, by_lead, remark}`, `follow_up_of`, `follow_up` `{id, serial}`, `timeline`, the four `can_*` | All as written (`_detail`, `improvements.py:639-648`) | Used as they are |
| `figures` with `before`/`after` `{days, breakdowns, symptom_breakdowns, downtime_minutes}`, `symptoms`, `machines`, `repeats` | Same; a repeat has `id, serial, occurred_at, intensity, machine_code, symptom, in_watch` | Used as they are |
| Timeline row `by_name`, `ticket {id, serial}`, `action {id, kind, text}`, `remark`, `earlier`, `from_state`, `to_state`; the computed row has `id` null and no person | Same | Used as they are |
| Routes `…/notes`, `…/verify/effective`, `…/verify/not-effective` (201, follow-up detail), `…/drop` with `reason`, `watch_days` on `PUT` | Same; the drop's required field is `reason`, the closes' `remark` | Used as they are |
| `improvementLabels.js` already holds S072's state words | Yes (`IMPROVEMENT_STATE_LABELS`) | Added the rest beside |
| `closeByApi` at `improvements.spec.js:196` | at `:181`; a name was the anchor | The same helper |
| `MoveDialog.vue:66`, `useFormModal.js:22`, `TicketDetailView.vue:252-253 / 127-128 / 445`, `ticketLabels.js:272` | Lines drifted; every named thing exists (`minutesText` at `:272` is exact) | Followed the names |
| `improvements.spec.js:43` clicks the serial link | Same line; now ambiguous with the timeline | Scoped to `ticketRow` (BR1-01). The other `getByRole("link", { name: <serial> })` on an improvement page: none in S069's or S071's tests (`:105` is the list page) |
| S069's and S071's button locators vs the new names | All use `exact: true`; none matches `Change watch`, `Close: it worked`, `Did not work — analyse again`, `Drop improvement`, `Add note` | No change |
| `tickets-notes.spec.js` / `journeys.spec.js` click `Add note` on tickets | Unchanged, ticket pages | No change |
| S068 edit test `getByText(<new problem text>)` | The timeline's "Changed" line now holds the text | Not in the brief: fixed (D-6) |
| Seed extruder for the set-up (§ 8.1) | Other specs' symptom tickets on the extruder are repeats | MCC1 mill (D-5) |

## 6. Not done, deferred or assumed

- No `@device` test (brief § 8.1). The fits are checked in flow tests with `expectDialogFits` and
  `expectNoSidewaysScroll`, on the Android phone.
- The *Ready to verify* filter or count on the list: out of scope (R05.10).
- Assumption: the admin back-dated raise as set-up by API (brief § 9) works; the tests pass with it.
- A repeat on the same machine that has nothing to do with the improvement (another cause) is listed
  as S072 designs it; the card says "Check whether it has the same cause."

## 7. Tests

- Frontend unit, changed files: `improvementLabels.test.js`, `datetime.test.js`: 61 passed.
- `npx vite build` in `frontend/`: clean (the known chunk-size warning).
- The new browser tests alone (`E2E_LANES=1`, `phone-chromium`, `-g "S073"`): 6 passed.
- Targeted: `e2e/improvements.spec.js`, `e2e/screens.spec.js`, `e2e/tickets-work.spec.js`: 74 passed
  and 2 skipped on the first run, with 3 failures that were the two causes of D-5 and D-6; after the
  fix `improvements.spec.js` and `screens.spec.js`: 41 passed, 1 skipped.
- All unit suites, `YANTRA_TEST_RUN=s073c1 tooling/run-tests.bat`: backend 3775 passed (137 s),
  frontend 344 passed, tooling 185 passed.
- The whole browser suite at Normal, once at the end: 289 passed, 13 skipped, 0 failed (182 s).
- Red-then-green: not applicable (no fix round).

## Manual checks

- [auto] The manager opens the ready improvement, sees the watch card and taps Close: it worked; the page reads closed — `frontend/e2e/improvements.spec.js::S073: the manager sees the watch after 30 days, taps Close: it worked, and the page reads closed`
- [auto] The lead taps Did not work, is asked why, and lands on the new improvement; the old page links back — `frontend/e2e/improvements.spec.js::S073: the lead taps Did not work, is asked why, and lands on the new improvement with the same ticket`
- [auto] A repeat of the symptom in the watch is shown with its ticket and no sideways scroll — `frontend/e2e/improvements.spec.js::S073: a repeat of the symptom in the watch is shown with its ticket`
- [auto] The operator adds a note; IT admin sees no Add note — `frontend/e2e/improvements.spec.js::S073: the operator adds a note to the timeline; IT admin sees no Add note`
- [auto] The lead changes the watch to 120 days; the end date moves and the timeline says so — `frontend/e2e/improvements.spec.js::S073: the lead changes the watch to 120 days; the end date moves and the timeline says so`
- [auto] The lead drops an improvement; its open countermeasure is cancelled — `frontend/e2e/improvements.spec.js::S073: the lead drops an improvement with an open countermeasure; the countermeasure is cancelled`
- [auto] No new route; the screens still open — `frontend/e2e/screens.spec.js` (ran again, passed)

On a real device: none (brief § 8.3). No row was added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/Plan.MD`: § 6 *Screens*, the improvements paragraph gains the state line, the card *Did it
  come back?*, the dialogs, the timeline and *Drop improvement*; § S072's paragraph notes the screens
  are built.
- `docs/steps/INDEX.md`: the S073 row is *In code review*; the brief's `Status` likewise.
- `.claude/CLAUDE.md`: not edited (the orchestrator's instruction); text below.
- `docs/schema.md`, `docs/schema.html`: none, because no migration. `docs/Maintenance-Philosophy.md`,
  `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`: none, because nothing
  they describe changed.

## Proposed CLAUDE.md changes

In `.claude/CLAUDE.md` § SMTW-Review › *Browser tests*, the spec-to-step map has no `improvements`
entry. Add, in the list after `asset-list …`:

`improvements` S068/S069/S071/S073 (S072 is backend only)

## Feedback

- hindrance: a Bash call with a heredoc holding an apostrophe (`Won't`) or a `§` failed with
  "unexpected EOF while looking for matching" and wrote nothing, twice (2 calls, about 3 min); the
  Write and Edit tools worked at once.
- waste: the brief's set-up on the seed extruder could not be right: other specs close extruder
  tickets with the same first symptom, which the card correctly shows as repeats. One targeted run
  (about 2 min) found it; the brief could name a machine no other spec closes tickets on.
- idea: the brief's line numbers (`useFormModal.js:22`, `TicketDetailView.vue:445`, spec `:196`)
  all drifted while S069–S071 were coded; BR2-08's rule of "names, not line numbers" would have saved
  the stale check for these.

## Fix rounds

### Round 1

Source: `4-code-review-r1.md` (4 nits). All four fixed; no test was added for a fault, so no red run
applies (CR1-02's helpers have their own new unit tests; CR1-01, -03 and -04 are style, text and
contract, with no behaviour change).

- **CR1-01: Fixed.** `.remark-text` joined the `.problem-text, .analysis-text` selector list in
  `ImprovementDetailView.vue`; the repeated rule is gone.
- **CR1-02: Fixed.** `machinesText(figures)` and `symptomsText(figures)` are new in
  `frontend/src/utils/improvementLabels.js`. `WatchCard.vue` and `WatchSummary.vue` use them, and
  `figureRows` uses `symptomsText`. Two new unit tests in `frontend/tests/improvementLabels.test.js`
  cover the join and the empty list.
- **CR1-03: Fixed.** § 4 D-4 now says the real behaviour: `watch.from` is null outside *Watching*
  (`_settle_state`), so the card is hidden on an *Actions open* page and the header carries
  `Change watch`. No code change.
- **CR1-04: Fixed.** `blank` of `VerifyDialog`, `DropDialog` and `ImprovementNoteDialog` is now
  `() => ({ remark: "" })` / `() => ({ reason: "" })`, with no seed copy, as the brief's call contract.

Runs: `tooling/run-frontend-tests.bat tests/improvementLabels.test.js` 57 passed;
`npx vite build` built (only the known chunk-size warning);
`tooling/run-e2e-tests.bat e2e/improvements.spec.js e2e/screens.spec.js` 41 passed, 1 skipped.
No shared frontend file changed, so no whole-suite or WebKit run.

Docs updated: none, because the round changes no behaviour, route, secret or schema.

#### Feedback

- none
