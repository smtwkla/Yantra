```
Step: S073 — Verified close: screens
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066, S067, S068 (gate B), S069 (fix round); S070–S072 coded before S073
Status: Gate B 30-10-2026 (snapshot c2b8569; verify review r2 clean) — approved 30-10-2026 by KLA (delegated)
From: R05.4 (second half; backend in S072)
```

# S073 — Verified close: screens

## 1. What will be built

R05.4 was split at the API (S072 § 9, *The split*). **S072** builds the states, the timeline, the
watch and the closes (`docs/steps/S072-improvement-verified-close/1-brief.md`). **This step builds
the screens** on S072 § 6, exactly as written there. It adds no route, table or key.

On the improvement page (`ImprovementDetailView.vue`, S068):

1. **The header** shows every state's badge (the words S072 D13 added) and one line under the title:
   - before the watch: "Watch: 90 days after the last countermeasure is done", with `"Change
     watch"` (BR1-04);
   - *Watching*: "Watching since 20-11-2026 · until 18-02-2027";
   - *Ready to verify*: "Watched 90 days, until 18-02-2027 · ready to verify";
   - closed: "Closed 18-02-2027 by Arun (manager): it worked" / "…: did not work" / "Dropped
     18-02-2027 by …", with ", the lead" after the name when `closed.by_lead` ("Closed 18-02-2027
     by Priya (engineer), the lead: did not work"), then the remark;
   - "Follow-up of IM-2026-10-001" and "Analysed again in IM-2026-11-004", linked.
2. **The card *Did it come back?*** (mock-up `docs/roadmap/R05-mockups/05-verify.html`), once the
   watch has started: the watch and its figures, the repeats with a warning (Q4.3 a), and, when
   ready, the two decisions.
3. **The dialog *Verify*** (one dialog, two modes): *Close: it worked* and *Did not work — analyse
   again*, with the remark (needed for *did not work*) and the consequence. The screen's words are
   plain (BR1-06 b); ISO's *effective* stays in the API codes, § 2 and the help text.
4. **The dialog *Watch*:** the watch's length, 30–365 days.
5. **The dialog *Drop improvement*:** the reason and the consequence.
6. **The card *Timeline*** (mock-up 05, below): newest first, the newest 10 and *Show all*, each
   line with time, person, what happened and its text; a changed why's or root cause's earlier
   text as "Was: …".
   `"Add note"` for every reader at the site who may (`can_add_note`).
7. **The dialog *Add note*.**

A closed improvement shows no write control: every button follows S072's flags and S067's
`is_open` (S068 D6).

**After it:** the manager opens IM-2026-10-001 after its watch, sees that *Won't start* did not
come back on HP003, and taps `"Close: it worked"`.

### Out of scope

- Everything S072 builds and leaves out (alerts R05.5, the register R05.10, undo of a done
  countermeasure, note corrections, per-machine figures).
- A *Ready to verify* filter or count on the list (the list shows the badge; R05.10's register
  counts states).
- A change to the shared `FormModal.vue`, `useFormModal.js`, `api.js`, the router or
  `e2e/support/` (settings: *Shared code*): the new set-up helper lives in the spec (§ 8.1).

## 2. Standards and practice

The standards behind the close are S072 § 2 (ISO 9001 § 10.2.1 (d), § 10.2.2, § 7.5.3; ISO 55001
§ 10; SMRP MTBF data only; ISO 27001 A.5.3 with its recorded departure, A.5.15). On the screens:

- **ISO 9001 § 10.2.1 (d), "Yantra counts, a person decides".** In plain words: the verifier sees
  the facts (failures and downtime before and after, each repeat) beside the buttons, and writes
  why. The card never decides for them (Q4.1 a, Q4.3 a).
- **ISO 9001 § 7.5.3 on screen.** In plain words: the record shows who did what and when. The
  timeline shows every line with its person and time, and an edit's earlier text.
- **ISO 9001's *effective*, in plain words** (BR1-06 b). The standard asks whether the action was
  *effective*. The floor reads "it worked" and "did not work" on the badges and buttons; the API
  codes (`closed_effective`, `closed_not_effective`), this brief's § 2 and the dialog's help text
  keep the standard's term, so the register (R05.10) and an auditor can map one to the other.
- **ISO 27001 A.5.3, recorded.** The close line says ", the lead" when the lead verified their own
  improvement, so the review sees it.

## 3. Where

S073 is coded after S072. Files marked **(S068)** are new in S068; S069 and S071 change
`ImprovementDetailView.vue` and `improvementLabels.js` first, and S072 changes
`improvementLabels.js` (the state words).

### Frontend

- `frontend/src/views/ImprovementDetailView.vue` **(S068)**: the header line (§ 5.1); the card
  *Did it come back?* after S071's *Countermeasures*, full width; the card *Timeline* last, full
  width; `"Drop improvement"` at the page's foot (§ 5.5); the five dialogs.
- `frontend/src/views/improvements/WatchCard.vue` (new): the card *Did it come back?* (§ 5.2).
- `frontend/src/views/improvements/VerifyDialog.vue` (new): § 5.3.
- `frontend/src/views/improvements/WatchDialog.vue` (new): § 5.4.
- `frontend/src/views/improvements/DropDialog.vue` (new): § 5.5.
- `frontend/src/views/improvements/ImprovementTimeline.vue` (new): the card *Timeline* (§ 5.6).
- `frontend/src/views/improvements/ImprovementNoteDialog.vue` (new): § 5.6.
- `frontend/src/utils/improvementLabels.js` **(S068)**: `IMPROVEMENT_EVENT_LABELS` and `eventLabel(event)`,
  `watchLine(improvement)`, `closedLine(closed, state)`, `figureRows(figures, closed)`,
  `repeatText(repeat)`, `watchEndDate(from, days)` (adds days to the date part of the IST string,
  no browser time zone; BR1-02), `WATCH_DAYS_MIN` 30, `WATCH_DAYS_MAX` 365, `NOTE_MAX` 1000,
  `CLOSE_REMARK_MAX` 1000 (not `REMARK_MAX`: `ticketLabels.REMARK_MAX` is 120, BR1-11).
- `frontend/src/utils/datetime.js`: `formatDate(value)`, the date part only, DD-MM-YYYY (BR1-02;
  `formatDateTime`, `frontend/src/utils/datetime.js:11`, adds the time). Not shared code in the
  settings' list.

### Tests

- `frontend/tests/improvementLabels.test.js` **(S068)**: § 8.2.
- `frontend/tests/datetime.test.js`: `formatDate` (§ 8.2).
- `frontend/e2e/improvements.spec.js` **(S068)**: the S073 tests (§ 8.1).
- `frontend/e2e/screens.spec.js`: runs again; no new route (§ 8.2).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 6 *Screens*: the improvement page gains *Did it come back?*, the timeline, the
  verify, watch, drop and note dialogs (`docs/Plan.MD:834`).
- `.claude/CLAUDE.md` § SMTW-Review: the spec map's `improvements` entry gains S072/S073.

**File count:** 12 code and test files (9 code, 3 tests; 1 more spec runs again), 2 docs.

## 4. Data model

None. The screens read and write only through S072 § 6 and S067 § 6.

## 5. Rules

### 5.1 The header

- The state badge reads `improvementStateLabel(state)` (S072 D13): *Analysing*, *Actions open*,
  *Watching*, *Ready to verify* (`text-bg-warning`), *Closed: it worked* (`text-bg-success`),
  *Closed: did not work* (`text-bg-danger`), *Dropped* (`text-bg-secondary`); the open ones keep
  S068's look.
- S068's line "Started … by … · lead …" stays as it is (`improvements.spec.js` asserts "lead Priya
  (engineer)"); the state line follows it (BR1-07): `watchLine` or `closedLine` (§ 1 item 1),
  dates through `formatDate` (date only, DD-MM-YYYY, BR1-02). The remark shows below,
  `text-secondary`, `overflow-wrap: anywhere`.
- `watch.from` is S072's `watch_start` (the last machine-kind countermeasure done first; S072
  § 5.1, D3). The screen shows it and computes no start of its own (BR2-02).
- **Before the watch** the line "Watch: 90 days after the last countermeasure is done" carries
  `"Change watch"` (`btn btn-outline-primary`, the ticket page's size as S068 BR1-11) when
  `can_edit_watch`; once the watch has started, the button moves to the card (§ 5.2). One button
  at a time.
- `follow_up_of` and `follow_up` as links "Follow-up of IM-…" and "Analysed again in IM-…".

### 5.2 The card *Did it come back?* (`WatchCard.vue`)

Props: the detail. **Shown only once the watch has started** (`watch.from` set), open or closed
  (BR1-04 a): before it, and on a record dropped before any countermeasure was done, nothing is
  fixed yet, and the header line says the state. The header "Did it come back?" and, when
  `can_edit_watch`, `"Change watch"` (`btn btn-outline-primary`, the ticket page's size as S068
  BR1-11).

- **During and after the watch:**
  - The summary line, from the repeats in the watch: none → "No ticket with the symptom Won't start
    on HP003 since 20-11-2026." (`text-success`); some → a warning (`alert alert-warning`, icon
    `fa-solid fa-triangle-exclamation`): "Came back 1 time: TK-2027-01-014 on 05-01-2027 (Won't
    start, breakdown). Check whether it has the same cause." each serial linked to its ticket. A
    repeat after the watch's end is listed with "after the watch". With no symptoms
    (`figures.symptoms` empty): "The linked tickets have no symptom yet, so repeats cannot be
    counted."
  - The small line "Checked on HP003 and its parts, every severity." (the machines' codes).
  - The table (`table table-sm`, as the mock-up): columns "", "90 days before" (`before.days`),
    then the third built from `after.days` in every case (BR2-01): "<after.days> days after" when
    `closed` is set or `watch.ended`, else "<after.days> days so far". A closed-effective record
    reads "90 days after", one dropped 20 days into its watch "20 days after", a running watch
    "41 days so far", a ready one "90 days after"; rows "Breakdowns", "Of them: Won't start"
    (the symptoms' labels joined with " or "; the row is left out when there are none),
    "Downtime" (`minutesText`, `frontend/src/utils/ticketLabels.js:272`). `figureRows(figures,
    closed)` builds the rows and the third column's header.
- **When `can_verify`:** two buttons under the table: `"Did not work — analyse again"`
  (`btn btn-outline-danger btn-lg`) and `"Close: it worked"` (`btn btn-success btn-lg`), each
  opening `VerifyDialog` in its mode; under them the line "*Did not work* closes this
  improvement and starts a new one with the same tickets." (the italics mark the button; BR2-09) On a phone they stack, full width.
- **Ready but no key** (an operator): the table and the line "Ready to verify. An engineer or
  manager of the site decides." No buttons.
- Words: "severity", not "intensity" (the ticket page's word).

### 5.3 The dialog *Verify* (`VerifyDialog.vue`)

`useFormModal` with `path: null` and `send(() => apiPost(...))`, the pattern of S069's
`RootCauseDialog.vue` (new in S069) and `MoveDialog.vue` (`frontend/src/views/tickets/MoveDialog.vue:66`).

- **Call contract** (self-check 13): `blank(seed = {})` gives `{remark: ""}` with or without a
  seed, since `useFormModal` calls `blank()` at set-up (`frontend/src/composables/useFormModal.js:22`).
  The mode is not a form field: `open(mode)` sets a `mode` ref (`"effective"` or
  `"not_effective"`) and then calls `openCreate()`, as `MoveDialog.vue` keeps its `move`
  ref and sets it in its `open(entry)` (BR1-08; names, not line numbers, BR2-08); `send` picks the route from it, so `toBody` sends only `{remark}`.
- **Title and submit:** effective: "Close: it worked" / `"Close: it worked"`; not effective:
  "Did not work — analyse again" / `"Close and analyse again"`. `"Cancel"`.
- **Above the field:** the summary line of § 5.2 (the same words), so the verifier decides with
  the fact in view; then the consequence: effective: "IM-2026-10-001 closes and cannot be changed
  after."; not effective: "IM-2026-10-001 closes: it did not work. A new improvement starts with
  its tickets, and you go there."
- **Field:** the remark (textarea, 3 rows, `maxlength` `CLOSE_REMARK_MAX`): effective: label
  `"Remark (optional)"`, help "What you checked, for example the panels on three presses. This
  records the fix as effective (ISO 9001 § 10.2)."; not effective: label `"Why did it not work?"`,
  required (the server's "Say why it did not work").
- **After the save:** effective: the page takes the detail; not effective: the router goes to the
  new improvement (`/tickets/improvements/<id>` of the answer). A 409 with no field shows at the
  top and emits `reload`, as `MoveDialog.vue`'s 409 watch does.
- **The destructive guard:** the dialog itself; closing is final, so the consequence is always on
  screen.

### 5.4 The dialog *Watch* (`WatchDialog.vue`)

`useFormModal` with `path: null`, `send(() => apiPut("/api/improvements/<id>", {watch_days}))`.
`blank(seed = {})` gives `{watch_days: seed.improvement?.watch.days ?? 90}`.

- Field `"Watch for (days)"` (`type="number"`, `min` 30, `max` 365, `inputmode="numeric"`), help
  "How long Yantra watches for the failure after the last fix on the machine is done. A lesson or
  a spread does not move the start. 30 to 365 days; dust builds up over months, so 90 is the
  default." (BR2-02) Under it, once the watch has started (`watch.from` set, a *Ready to verify*
  page too; BR2-07), the end date
  the new length gives: "Ends on 18-02-2027" (computed from `watch.from`).
- Submit `"Save watch"`; `"Cancel"`. The page takes the detail.

### 5.5 Drop (`DropDialog.vue`)

- `"Drop improvement"` (`btn btn-outline-danger`) at the foot of the page, shown when `can_drop`.
  At the foot, away from the work buttons, so a thumb does not hit it by mistake.
- The dialog: title "Drop improvement"; the line "Drop IM-2026-10-001? Its open countermeasures are
  cancelled. You cannot undo this."; field `"Why drop it?"` (textarea, 3 rows, `maxlength` 1000,
  help "For example: started by mistake, or the same problem is analysed in IM-…"); submit `"Drop
  improvement"`, FormModal's standard `btn-primary` (S071 BR1-01 keeps `FormModal.vue` unchanged;
  the red is on the page button and in the consequence line; BR1-16); `"Cancel"`.
  `blank(seed = {})` gives `{reason: ""}`.

### 5.6 The timeline (`ImprovementTimeline.vue`) and *Add note*

- Card header "Timeline" and, when `can_add_note`, `"Add note"` (`btn btn-outline-primary`, icon
  `fa-regular fa-comment`, as the ticket page, `frontend/src/views/TicketDetailView.vue:252-253`).
- Rows: `timeline` in the server's order (newest first), the newest 10 and `useShowMore`'s *Show
  all n* (`frontend/src/composables/useShowMore.js:10`), as the ticket timeline
  (`TicketDetailView.vue:127-128`). Rows are keyed by their index, as the ticket timeline
  (`TicketDetailView.vue:445`): the computed row's `id` is null (BR1-12). Each row: "18-02-2027
  15:30 · Arun (manager)" (small), then the bold `eventLabel(event)`, then (BR1-03):
  - the ticket's serial, linked, on `ticket_linked` and `ticket_removed` only (S072 writes
    `started` with no ticket);
  - the countermeasure's kind and text on `action_done` and `action_cancelled` only (on
    `action_added` and `action_changed` the remark already names them);
  - then `remark` (pre-wrapped, `overflow-wrap: anywhere`);
  - then, when `earlier` is set and `remark` too (a changed why or root cause), "Was: …" (`small
    text-secondary`); when only `earlier` is set (`why_removed`), the removed text is the row's
    content, with no "Was:" (BR1-13). Edits and countermeasure changes carry "old → new" in the
    remark (S072 BR1-04).
  A `state_changed` line reads "Now Watching" from `to_state`'s label. The computed `watch_ended`
  row shows its time alone, no person ("18-02-2027 15:30"), then "Watch ended — ready to verify".
- `IMPROVEMENT_EVENT_LABELS` (not `EVENT_LABELS`: `ticketLabels.js:76` has that name; BR2-03):
  `started` "Started", `edited` "Changed", `ticket_linked` "Ticket added",
  `ticket_removed` "Ticket removed", `why_added` "Why added", `why_changed` "Why changed",
  `why_removed` "Why removed", `root_cause_set` "Root cause set", `root_cause_changed` "Root cause
  changed", `action_added` "Countermeasure added", `action_changed` "Countermeasure changed",
  `action_done` "Countermeasure done", `action_cancelled` "Countermeasure cancelled",
  `state_changed` "State changed", `note` "Note", `closed_effective` "Closed: it worked",
  `closed_not_effective` "Closed: did not work", `dropped` "Dropped", `watch_ended` "Watch ended —
  ready to verify". An unknown event shows as it came.
- **Add note** (`ImprovementNoteDialog.vue`): `useFormModal({ path: "/api/improvements/<id>/notes" })`,
  `blank(seed = {})` → `{remark: ""}`; field `"Note"` (textarea, 4 rows, `maxlength` 1000, help
  "What you saw or know, for example the same dust on another panel."); submit `"Save note"`;
  `"Cancel"`. The page takes the detail. A closed improvement's 409 shows at the top and emits
  `reload`.
- Empty (an improvement before v39 has backfilled lines; a new one has *Started*): never empty.

### 5.7 Words for the floor

"Did it come back?", "it worked", "did not work", "analyse again", "watch", "drop", "note"; no
"verify" or "effective" on a button or badge (BR1-06 b; the help text names the standard's term),
no "nonconformity", no "MTBF". The state words are S072 D13's.

### 5.8 The database down

The calls go to S072's routes, which answer 503 while the database is down. The page shows its
load error with `"Retry"` (S068 § 5.8); a dialog shows the error at the top.

## 6. API

None new. S072 § 6 as it stands: the detail's `watch`, `closed`, `follow_up_of`, `follow_up`,
`timeline`, `can_verify`, `can_drop`, `can_add_note`, `can_edit_watch`; the routes `…/notes`,
`…/verify/effective`, `…/verify/not-effective`, `…/drop`, and `watch_days` on S067's `PUT`. If
S072's review rounds change § 6, this brief follows before it is coded.

## 7. Design decisions

- **D1. One *Verify* dialog for both decisions, in plain words** ("Close: it worked", "Did not
  work — analyse again"; BR1-06 b). The fields and the guard are the same; the mode
  sets the title, the label, the need for a remark and the consequence. Rejected: the mock-up's
  inline remark and buttons on the card (a final decision with no confirming step, and an empty
  remark field on every visit); two dialogs.
- **D2. The facts in the dialog too.** The summary line repeats above the remark, so on a phone the
  verifier does not decide from memory of a card scrolled away.
- **D3. *Drop* at the page's foot, in outline red, through a dialog.** Final and rare. Rejected: in
  the header beside *Edit* (a mis-tap risk on a phone).
- **D4. The watch length in a dialog of its own.** It belongs to the watch card. Rejected: a field in
  S068's *Edit improvement* dialog (the field would sit far from the dates it changes).
- **D5. The timeline is a card of its own at the bottom, as on the ticket page**, with the ticket's
  *Show all* pattern. Rejected: the mock-up's side column on a desktop only (two layouts).
- **D6. A new note dialog, not the ticket's `NoteDialog.vue`.** That dialog is bound to a ticket and
  its correction (`frontend/src/views/tickets/NoteDialog.vue:15-30`). Rejected: widening it with a
  path prop (a change to a working ticket screen for a 30-line dialog).
- **D7. The *not effective* save goes to the new improvement.** The team works there next; the old
  one is one link away. Rejected: staying on the closed record.

## 8. Tests and acceptance

### 8.1 Automated (e2e, targeted: `improvements.spec.js`, `screens.spec.js`)

**Set-up by API, in the spec** (not in `e2e/support/`, shared code): `readyImprovement(api)`
raises a ticket on the seed extruder **as admin** (`apiAs("admin")`, who holds `ticket:backdate`)
with `occurred_at` 40 days back and *Already fixed* (S068 § 8.1's `restore` body, its time
back-dated too); reads its symptom choices (`GET /api/tickets/modes?ticket_id=`) and closes it with
the first one, as S069's close helper in the spec does (`improvements.spec.js:196`; BR1-10); starts
an improvement with Priya as lead; sets the root cause
(S069's route); adds one *Corrective* countermeasure (a machine kind, so `watch_start` takes its `done_at` by S072
§ 5.1's first rule; BR2-05) and marks it done with `done_at` 35 days back (S070 allows
any time from the problem on); sets `watch_days` 30. The improvement is then *Ready to verify*
(S072 § 5.2). Seed people as S071 § 8.1.

- **important** S073: the manager "Arun (manager)" opens the ready improvement: badge "Ready to
  verify", the card shows "No ticket with the symptom … since …" and the table rows "Breakdowns"
  and "Downtime"; `expectNoSidewaysScroll(page)` (`frontend/e2e/support/dialogs.js:49`; BR1-05);
  taps `"Close: it worked"`, types a remark, presses the submit (`saveDialog(page, "Close: it
  worked")`, `frontend/e2e/support/tickets.js:99`): badge "Closed: it worked", the line "Closed …
  by Arun (manager): it worked", no `"Edit"`, `"Add ticket"`, `"Add why"`, `"Add countermeasure"`,
  `"Add note"`, `"Drop improvement"`, `"Change watch"`, `"Close: it worked"` or `"Did not work —
  analyse again"` (BR2-04); the timeline's first line reads "Closed: it worked".
  `expectDialogFits` on the dialog.
- **important** S073: Priya (the lead) taps `"Did not work — analyse again"`, presses
  `"Close and analyse again"` with no remark (the test first calls
  `consoleWatch.allowFailedRequest("/verify/not-effective", 400)`, as `improvements.spec.js:152`;
  BR1-09): "Say why it did not work" under the field; types it, saves: the page is a new
  improvement, badge "Analysing", "Follow-up of IM-…" and *Tickets (1)* with the same ticket; the
  old page shows "Closed … by Priya (engineer), the lead: did not work" and "Analysed again in
  IM-…".
- S073: a repeat: after `readyImprovement`, a second ticket raised as admin 10 days back on the
  same machine and closed with the same symptom through the modes route, as `readyImprovement`
  does (a closed ticket counts as a repeat, S072 § 5.4; BR2-05); the manager opens the page (BR1-15): the card's warning names
  its serial; `expectNoSidewaysScroll(page)`.
- S073: the operator "Muthu (operator)" adds a note through `"Add note"`: the timeline's first line
  is "Note" with the text; IT admin opens the page: no `"Add note"`. `expectDialogFits`.
- S073: Priya changes the watch on a watching improvement (its countermeasure done today) through
  `"Change watch"` to 120: the header's end date moves and the timeline shows "Changed" with
  "Watch: 90 days → 120 days" (S072 BR1-04). `expectDialogFits`.
- S073: Priya drops an improvement with an open countermeasure through `"Drop improvement"`: badge
  "Dropped", the countermeasure row *Cancelled*. `expectDialogFits`.
- `screens.spec.js`: no new route; it runs again because the page changed.
- No test is `@device`: none checks a layout (a fit helper in a flow test does not tag it).

### 8.2 Existing tests that run again, and locators

- **`frontend/e2e/improvements.spec.js:43` breaks and is changed** (BR1-01): the S068 start test
  clicks `page.getByRole("link", { name: ticket.serial })` on the improvement page; the timeline's
  `ticket_linked` line adds a second link of that name (a repeat in the watch card can add a
  third), and Playwright's strict mode refuses the click. The line becomes
  `ticketRow(page, ticket.serial).getByRole("link", { name: ticket.serial }).click()` (the helper
  at `:17`). The coder checks every `getByRole("link", { name: <serial> })` on the improvement
  page in S069's and S071's tests the same way and lists each in the impl report.
- `frontend/e2e/improvements.spec.js` (S068, S069, S071 tests): the page gains buttons named
  `"Change watch"`, `"Close: it worked"`, `"Did not work — analyse again"`, `"Drop improvement"`
  and `"Add note"`. Playwright matches a role name as a substring unless `exact: true`: S068's
  `"Edit"` locators already use it (the S068 edit tests' `exact: true` locators; BR2-08); the coder checks
  S069's and S071's (`"Add why"`, `"Edit root cause"`, `"Add countermeasure"`, `"Cancel
  countermeasure"`) against the new names. `"Add note"` and `"Save note"` exist on the ticket page; the lines that
  click them (`tickets-notes.spec.js:62`, `:66`, `:108`, `:113`, `:125`, `:127`, `:135`, `:142`;
  `journeys.spec.js:146`, `:148`) open tickets, not improvements, so no line changes.
- `frontend/e2e/tickets-work.spec.js`: the "Analysed in" line's state words come from the same
  label map; its tests start no improvement; no line changes.

**Frontend unit** (`frontend/tests/improvementLabels.test.js`): `eventLabel` (each event, an
unknown one); `watchLine` (watching, ready, before the watch); `closedLine` (each closed state,
with and without the lead mark); `figureRows` (with and without symptoms; "41 days so far"
while watching; "90 days after" when ended or closed effective; "20 days after" for a record
dropped 20 days into its watch, BR2-01); `repeatText`; `watchEndDate` (90 days across a year end; the date part of
"2026-11-20T15:30:00" whatever the test's time zone). `frontend/tests/datetime.test.js`:
`formatDate` (a datetime, a date, empty).

### 8.3 On a real device

None: the dialogs are forms a browser fits (`expectDialogFits`), and no camera, print or keyboard
check is new. (The iPhone keyboard over a dialog is S069's row in `docs/steps/device-checks.md`.)

### 8.4 Acceptance

- The frontend unit suite green; `npx vite build` clean; the targeted specs green; the whole browser
  suite at Normal once at the end (the improvement page and every improvement flow changed).
- On a phone (`phone-chromium`) every new dialog fits.
- IM-2026-10-001's verified close can be done on a phone.

## 9. Open questions and assumptions

- **The split** (S072 § 9): R05.4 was cut at the API; this step holds the screens. S072 is coded
  first, and this brief builds on S072 § 6 as written.
- **Departure from the mock-up** (D1): the remark and the decision are in a dialog, not inline on
  the card; the words are "it worked" / "did not work", not "effective" (BR1-06 b).
- **A staleness review is due** once S069–S072 are coded (the spec's line numbers drift while S069
  is coded; S072 § 6 is read as text).
- **Assumption:** the admin back-dated raise of § 8.1 is accepted as set-up by API (S024: tests set
  up by API; admin set-up is used by `frontend/e2e/support/meters.js:11`).
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Baseline), § 1 (items 1, 2, 3, 6; *After it*), § 2 (plain words), § 3
(`improvementLabels.js` names, `datetime.js`, `datetime.test.js`, file count), § 5.1, § 5.2, § 5.3,
§ 5.5, § 5.6, § 5.7, § 7 D1, § 8.1, § 8.2, § 9.

| Finding | Answer |
|---|---|
| BR1-01 major | Accepted (a): `improvements.spec.js:43` is scoped to `ticketRow(…)`; the coder checks S069's and S071's serial-link locators the same way; listed in § 8.2. |
| BR1-02 minor | Accepted (a): `formatDate` in `datetime.js` (date only, unit-tested) for the header and repeat lines; `watchEndDate` in `improvementLabels.js` adds days to the IST date string, no browser zone. § 3, § 5.1, § 8.2. |
| BR1-03 minor | Accepted (a): the serial on `ticket_linked` / `ticket_removed`; the countermeasure's kind and text on `action_done` / `action_cancelled` only. § 5.6. |
| BR1-04 minor | Accepted (a): the card shows only once `watch.from` is set; before it, the header line "Watch: 90 days after the last countermeasure is done" carries `"Change watch"`. § 1, § 5.1, § 5.2. |
| BR1-05 minor | Accepted (a): `expectNoSidewaysScroll` in the first important test and the repeat test, no `@device`. § 8.1. |
| BR1-06 minor | Accepted (b), the orchestrator for KLA: badges "Closed: it worked" / "Closed: did not work"; buttons "Close: it worked" / "Did not work — analyse again"; submit "Close and analyse again"; ISO's *effective* stays in the API codes, § 2 and the help text. S072 D13 changed to match. § 1, § 2, § 5.1–§ 5.3, § 5.6, § 5.7, D1, § 8.1, § 8.2. |
| BR1-07…BR1-16 nits | Accepted: BR1-07 S068's started line stays (§ 5.1); BR1-08 the mode is a ref set by `open(mode)` (§ 5.3); BR1-09 `allowFailedRequest` for the 400 (§ 8.1); BR1-10 the symptom set by closing through the modes route (§ 8.1); BR1-11 `CLOSE_REMARK_MAX` (§ 3); BR1-12 rows keyed by index, the computed row's time alone (§ 5.6); BR1-13 a removed why's text as the row's content (§ 5.6); BR1-14 the column switch is `watch.ended` (§ 5.2); BR1-15 the manager opens the repeat test's page (§ 8.1); BR1-16 the Drop submit is FormModal's `btn-primary` (§ 5.5). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 1 (item 1), § 2 (the lead mark), § 3
(`IMPROVEMENT_EVENT_LABELS`, `figureRows`), § 5.1, § 5.2, § 5.3, § 5.4, § 5.6, § 8.1, § 8.2.

| Finding | Answer |
|---|---|
| BR2-01 minor | Accepted (a): the third column is built from `after.days` in every case, "… days after" when closed or ended, else "… days so far"; `figureRows(figures, closed)`; the unit test adds the dropped case. § 3, § 5.2, § 8.2. |
| BR2-02 minor | Accepted (a): the header line stays; the *Watch* dialog's help states S072 D3's rule ("after the last fix on the machine … A lesson or a spread does not move the start"); § 5.1 says `watch.from` is S072's `watch_start`. § 5.1, § 5.4. |
| BR2-03…BR2-09 nits | Accepted: BR2-03 `IMPROVEMENT_EVENT_LABELS` (§ 3, § 5.6); BR2-04 the watch and verify buttons asserted absent after the close (§ 8.1); BR2-05 a *Corrective* countermeasure, and the repeat ticket closed with its symptom (§ 8.1); BR2-06 ", the lead" (§ 1, § 2, § 8.1); BR2-07 the end date shown once the watch has started (§ 5.4); BR2-08 names instead of drifting line numbers (§ 5.3, § 8.2); BR2-09 "*Did not work* closes …" (§ 5.2). |
