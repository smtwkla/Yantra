```
Step: S073 — Verified close: screens
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069 (in progress; `improvements.spec.js` is already longer than the facts file's 169 lines)

**Verdict: one `major` is open (BR1-01, an S068 browser test the new timeline breaks); no blocker.** Six
`minor` findings, one of them a judgement call for KLA (BR1-06, the state words; not defining). Full
track, round 1. Facts file read: `scratch/brief-facts-S073.md`. S070–S072 are not coded, so every field
the brief uses was checked against S072 § 6 as text; a staleness review is due once S072's code lands
(the brief says so in § 6).

## Findings

### BR1-01 — major — `improvements.spec.js:43` breaks: two links named the ticket's serial

**Problem.** § 8.2 says no S068 line changes. The S068 start test ends with
`page.getByRole("link", { name: ticket.serial }).click()` on the improvement page
(`frontend/e2e/improvements.spec.js:43`). After S073 the page has a second link with that name: the
timeline's `started` line links the ticket's serial (§ 5.6: "the ticket's serial (linked)"), and the
`ticket_linked` line too. Playwright's strict mode refuses a `click()` on a locator that resolves to
two elements, so the test fails. A repeat in the watch card (§ 5.2, "each serial linked") can be a
linked ticket as well (S072 § 5.4), a third link on some pages.

**Why it matters.** The whole browser suite runs at Normal at the end (§ 8.4); a red S068 test costs a
fix round, and the brief states the opposite.

**Options.**
- (a) **Recommended.** § 8.2 names line 43 and the fix: scope the click to the *Tickets* card,
  `ticketRow(page, ticket.serial).getByRole("link", { name: ticket.serial })` (the helper exists at
  `:17`). Add to the coder's check list: every `getByRole("link", { name: <serial> })` in S069's and
  S071's tests on the improvement page (they are being written now and may use the same shape).
- (b) Render the timeline's serials as plain text, not links. Loses the tap to the ticket the
  mock-up shows.

### BR1-02 — minor — the date lines use `formatDateTime`, which shows the time too

**Problem.** § 5.1 says the header's dates go "through `formatDateTime` (DD-MM-YYYY)". That function
gives `DD-MM-YYYY HH:MM` for a datetime (`frontend/src/utils/datetime.js:11-18`), and `watch.from`,
`watch.until` and `closed.at` are datetimes (S072 § 5.2: "a datetime; the screens show its date").
So "Watching since 20-11-2026 · until 18-02-2027" would render as "… since 20-11-2026 15:30 · until
18-02-2027 15:30", and the test's text matches drift. The repo has no date-only helper
(`overdueBadge` slices the string, `ticketLabels.js:419`). The *Watch* dialog's "Ends on 18-02-2027"
(§ 5.4) also needs date arithmetic on an IST string; done with `new Date()` in the browser's zone it
is off by a day near midnight on a phone set to another zone.

**Why it matters.** The coder has to choose a format and a date routine; two places could differ.

**Options.**
- (a) **Recommended.** Add `formatDate(value)` to `datetime.js` (the date part only, a unit test in
  `datetime.test.js`) and use it in `watchLine`, `closedLine` and the repeat line; add a pure
  `watchEndDate(from, days)` to `improvementLabels.js` that adds days to the date part of the IST
  string (no browser zone), unit-tested. `datetime.js` is not in the settings' shared list.
- (b) Show the time everywhere, as the ticket page does. Longer lines on a phone; the brief's texts
  change.

### BR1-03 — minor — the timeline line doubles a countermeasure's text

**Problem.** § 5.6 shows, after the label, "the countermeasure's kind and text when set", then
`remark`. S072 § 5.6 writes `action_added`'s remark as "Corrective: <text>. Owner …, due …" and
`action_changed`'s as the changed fields. On those lines the kind and the text would appear twice.
The join (`action{kind, text}`) is needed on `action_done` and `action_cancelled`, where the remark is
the done text or the reason and does not say which countermeasure.

**Why it matters.** Longer lines on a phone, and the coder has to decide the rule alone.

**Options.**
- (a) **Recommended.** The ticket's serial on `started`, `ticket_linked`, `ticket_removed`; the
  countermeasure's kind and text on `action_done` and `action_cancelled` only; nothing extra on
  the others.
- (b) Drop the remark on `action_added` and show the join instead. Loses the owner and due date.

### BR1-04 — minor — *Did it come back?* on a record with no watch

**Problem.** § 5.2 shows the card on every improvement; before the watch it says "The watch starts
when the root cause is set and every countermeasure is done or cancelled. Yantra then watches for
90 days." Two cases read wrong: a **dropped** improvement with `watch.figures` null gets the same
"The watch starts when…" line on a dead record; and an *Analysing* record carries a card titled
"Did it come back?" when nothing is fixed yet. The sentence also misstates S072 § 5.1: all
countermeasures cancelled stays *Actions open*; the watch needs at least one done.

**Why it matters.** A closed page must read as closed; an operator reading an open one should not
meet a question nobody can answer yet.

**Options.**
- (a) **Recommended.** Hide the card while `watch.from` is null, open or closed; `"Change watch"`
  then sits in the header beside S068's `"Edit"` until the watch starts, or the length is set in the
  *Watch* dialog opened from the header line. The header line already says the state.
- (b) Keep the card, with one line per case: open "Yantra watches for 90 days after the last
  countermeasure is done." (the rule stated right); dropped "No watch: dropped before a
  countermeasure was done."

### BR1-05 — minor — no sideways-scroll check on the ready page

**Problem.** The ready page is the widest content S073 adds on a phone: a three-column table
("Of them: Won't start or Overheats" in the first column), the warning line with one or more
serials, two `btn-lg` buttons. § 8.1 calls `expectDialogFits` but never `expectNoSidewaysScroll`
(S068 did, `improvements.spec.js:69`).

**Why it matters.** A table that overflows at 412 px is the one layout fault a flow test on
`phone-chromium` can catch for free.

**Options.**
- (a) **Recommended.** Add `expectNoSidewaysScroll(page)` to the first important test (after the
  card is visible) and to the repeat test (the warning line). No `@device` tag: the test's purpose
  stays the flow.
- (b) A `@device` layout test of the card on all three projects. More runs for one table.

### BR1-06 — minor — "effective" on the badge and buttons, for the floor (KLA's decision; not defining)

**Problem.** The orchestrator asked for the state words to be judged for a low-literacy or
Tamil-reading floor. "Closed: effective" / "Closed: not effective" and the button "Close as effective"
use an office word. The brief's own server text is plainer: "Say why it did not work" (§ 5.3), and
the ticket page's repeat button says "Not fixed — raise again". Operators read the badge in the
list and on the page (S068 D6: every reader at the site); they never verify.

**Why it matters.** The badge is the one word the floor sees about the outcome. The words are S072
D13's (`IMPROVEMENT_STATE_LABELS`), so the answer applies to both briefs.

**Options.**
- (a) Keep ISO's term: "Closed: effective" / "Closed: not effective", "Close as effective". One
  term for one thing with the docs and the register (R05.10); the verifiers are engineers.
- (b) **Recommended.** Plain words on screen, the standard's term in the docs: badge "Closed: it
  worked" / "Closed: did not work"; buttons "Close: it worked" / "Did not work — analyse again",
  submit "Close and analyse again" unchanged; the header line "Closed 18-02-2027 by Arun (manager):
  it worked". The timeline labels follow the badge.
- (c) As (a) on the buttons (the verifiers' words) and (b) on the badge. Two words for one state.

## Nits

- **BR1-07** (nit) § 5.1: say that S068's line "Started … by … · lead …" stays and the new state line
  follows it; `improvements.spec.js:38` asserts "lead Priya (engineer)".
- **BR1-08** (nit) § 5.3: `blank(seed)` "reads `seed.mode`" but returns `{remark: ""}`. Say where
  `mode` lives: a `ref` set by `open(mode)`, as `MoveDialog.vue`'s `move` (`:63`, `:103`), not a form
  field (else `toBody` must strip it).
- **BR1-09** (nit) § 8.1, second test: the empty-remark 400 needs
  `consoleWatch.allowFailedRequest("/verify/not-effective", 400)` (as `improvements.spec.js:152`),
  or the console watch fails the test.
- **BR1-10** (nit) § 8.1 `readyImprovement`: "the symptom set" needs a mode id before the ticket
  exists, and `/api/tickets/modes?ticket_id=` needs the ticket (`improvements.spec.js:196`, S069's
  new helper). Say how: raise, read the modes, then set it through the ticket's edit, as that helper
  does; or read `/api/masters/failure-modes` as admin.
- **BR1-11** (nit) § 3: `REMARK_MAX` 1000 in `improvementLabels.js` shares its name with
  `ticketLabels.REMARK_MAX` = 120 (`:517`). Name it `CLOSE_REMARK_MAX`.
- **BR1-12** (nit) § 5.6: the computed `watch_ended` row has `id: null`; key the rows by index or
  `id ?? event`, as the ticket timeline keys by index (`TicketDetailView.vue:445`). And say whether
  its first line reads "18-02-2027 15:30 · Yantra" (mock-up 05) or the time alone.
- **BR1-13** (nit) § 5.6: a `why_removed` line has `earlier` and no `remark`; "Was: 3. Why …" reads
  as an edit. Show the removed text as the line's content.
- **BR1-14** (nit) § 5.2: the third column reads "90 days after" or "41 days so far"; say the switch
  is `watch.ended` (false → "so far" with `after.days`).
- **BR1-15** (nit) § 8.1, the repeat test: name who opens the page (the manager, as the first test).
- **BR1-16** (nit) § 5.5: say the *Drop* submit is FormModal's standard `btn-primary` (S071 BR1-01
  keeps `FormModal.vue` unchanged); the red is on the page button and the consequence line.

## Checked and found consistent

- **S072 § 6 fields.** Every field the brief reads exists there: `watch.{days, from, until, ended,
  figures}` with `figures.{machines[].code, symptoms[].label, before, after.days, repeats[]}`;
  `closed.{at, by_name, by_lead, remark}`; `follow_up_of`, `follow_up`; `timeline[].{id, event,
  occurred_at, by_name, to_state, ticket, action, remark, earlier}`; `can_verify`, `can_drop`,
  `can_add_note`, `can_edit_watch`; `watch_days` on S067's `PUT` (absent fields stay, S067 § 5.2).
  The 19 event names of § 5.6 match S072 § 5.6's table plus `watch_ended`.
- **Flags on a closed page.** `is_open` false after a close (S072 § 5.1); S070's `can_mark_done` and
  `can_change` need the improvement open (S070 § 5.7); S068's and S069's buttons use `is_open`. A
  closed page shows no write control, as § 1 says.
- **The Verify dialog (D1, D2).** One dialog with a confirming step, the facts and the consequence
  in view, replaces the mock-up's inline buttons; a final action is never one tap. The remark is
  required only for *not effective*, as S072 § 5.3. The 409 reload is `MoveDialog.vue:95-98` and
  `NoteDialog.vue:33-35` as cited.
- **Navigation after *not effective* (D7).** The pattern exists: the ticket page's `ImprovementDialog`
  pushes the new route after its save (`TicketDetailView.vue:527`); `FormModal` disposes its modal
  only once hidden (`FormModal.vue:128-142`), so the unmount on the route change is safe.
- **Drop (D3).** At the foot, outline red, through a dialog that names the consequence; `can_drop`
  = open and `improvement:edit` (S072 § 5.8).
- **Call contracts (self-check 13).** `useFormModal` calls `blank()` with no seed at set-up
  (`useFormModal.js:22`); the three `blank(seed = {})` shapes survive it. `saveDialog`
  (`tickets.js:99`) and `expectDialogFits` need a footer `button[type=submit]` and a "Cancel":
  FormModal gives both.
- **Locators.** `"Add note"` / `"Save note"` lines in `tickets-notes.spec.js` and `journeys.spec.js`
  run on ticket pages (`openAction` is scoped to the open page's action bar); no clash. S068's
  `"Edit"` and `"Add ticket"` locators use `exact: true` (`:25, :58, :86, :138, :139, :155, :160`).
  `"Cancel"` in `expectDialogFits` is scoped to `.modal-footer`. `screens.spec.js` asserts only the
  heading on the improvement route.
- **Set-up by API.** Admin bypasses `ticket:backdate` (holders `()`, `config_rbac.py:111`;
  `backdate_days`, `tickets_core.py:117-123`), so a raise 40 days back is accepted, and
  `apiAs("admin")` exists. 35 days back + 30 days → ready; the 40-day ticket falls in *before*
  (65–35 days back); a repeat 10 days back is in the watch. The seed people are as named
  (`seed_e2e.py:36-46`); Muthu's unit is MCC2, the extruder's.
- **Standards.** § 2 names ISO 9001 § 10.2.1 (d) and § 7.5.3 and ISO 27001 A.5.3 with plain words and
  shows where each lands on the screen; the rest is S072 § 2 by reference, right for a screens step.
- **Track and tests.** Full track; titles `S073:`; no `@device` test (none asserts a layout); no
  device check, with the reason stated; the two important checks are the two closes.
- **Shared code.** No change to the settings' shared files; the set-up helper stays in the spec.
- **Docs.** Plan.MD § 6 and the spec-to-step map are listed.

## Feedback

- waste: the facts file lists 30 S072 names as "not found" because S072 is not coded; expected, but
  40 lines to skim with nothing to verify (`scratch/brief-facts-S073.md` § Code names). Idea: the
  facts tool could mark names the brief attributes to another step's brief ("S072 § 6").
- hindrance: `frontend/e2e/improvements.spec.js` grew from 169 lines (facts file) to 196+ during the
  review (S069 being coded in parallel), so the brief's line numbers for that spec drift before the
  coder starts; a staleness review of this brief is due after S069–S072 land.
