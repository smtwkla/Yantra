```
Step: S027 — Work notes
Doc: brief
Author: Planner (Opus)
Date: 22-10-2026 (revised 22-10-2026: user answers U1; brief-review r1)
Track: full
Status: Gate B — code review r1 clean; fix round 1 (CR1-01, CR1-03, asked by the user) done; 2 nit open; awaiting the user's check and commit (approved 22-10-2026 by KLA; Q2b (b); staleness check s1 done)
Baseline: 79fc61d + uncommitted S026 (staleness check s1, 22-10-2026)
```

# S027 — Work notes

**The gap (KLA, 22-10-2026).** A ticket can be assigned, worked, given labour,
parts, photos and documents, scheduled and closed, but it has **no place for
what the technician found and tried**. Text goes in only as a move's remark,
so a finding that does not change the state has nowhere to go. KLA's examples:

- "Found the fan belt loose. Tightened, now working" — fits *Back in service*'s
  remark today, but only at that moment;
- "Pressure not reached in Pilot line. Reason not known yet" — no move fits;
  the work goes on;
- "Borewell pump not running, no amps, no movement. To lift and check" — the
  same.

This step adds **work notes**:
- an *Add note* button on an open ticket; each note is a line on the
  timeline with its text, who wrote it and when;
- the operator's *What is wrong?* text from the raise becomes the **first
  note** (U1);
- an engineer, IT admin or admin can **edit** a note to fix a typo or wrong
  information; new findings are added as new notes, not edits (U1). Each edit
  keeps the earlier text.

Order: coded **on top of S026** ("A refusal is always in view", uncommitted at
gate B), so the note dialog follows its rule that a refused save shows its
message in view (BS1-03). What the coder relies on: `revealError.js` finds the
first `.is-invalid, .invalid-feedback.d-block, .alert-danger` in the dialog
body; the note field is marked `is-invalid` and its message
`invalid-feedback d-block` (BR1-06); a 409 "This ticket is closed" reaches the
top bar through `FormModal`'s `error` prop, which S026 scrolls into view.

## 1. What will be built

1. **Add note** — on the ticket page, an outline button *Add note* in the
   action bar, after the next move and before *Change severity* (the style of
   *Schedule*; BR1-02, § 7.6, § 9 Q4). Shown to holders of `ticket:restore`
   at the ticket's site (operator, supervisor, technician, engineer, manager,
   IT admin: whoever may confirm the machine is back may write what they see;
   § 9 Q2b (b), U2) while the ticket is open, in every open state (raised,
   acknowledged, in progress, scheduled, back in service). The storekeeper
   holds no ticket key and adds no note.
2. **The note dialog** — one field, *Note*, a text area of four rows
   (`rows="4"`, `maxlength="1000"`; a longer text scrolls inside the field),
   line breaks kept. Buttons *Save note* and *Cancel*. The cursor starts in
   the field: `FormModal.vue` focuses the first element marked `autofocus` in
   its body on Bootstrap's `shown.bs.modal` (Bootstrap ignores `autofocus` in
   a modal and focuses the modal itself when it opens; BR1-06). Any later
   dialog can use it. An empty note is
   refused beside the field: "Enter a note". Over the limit: the existing
   "Too long (max 1000)".
3. **On the timeline** — a note is a line like the others, in time order
   between the moves: the label **Note**, the time, the author (the login
   name, as every line shows), and the text below in the normal text size,
   line breaks kept (`pre-wrap`). A move's remark stays small as today,
   because a note's text *is* the content of its line.
4. **The first note is the raise's *What is wrong?*** (U1). The ticket's
   description (`tickets.description`, the raise screen's *What is wrong?*
   field) is shown on the timeline's **Raised** line, in the note style. The
   separate *Description* card under the timeline goes away. Nothing is
   copied: the description stays where it is, and the existing *Edit* dialog
   (§ 9 Q6) still changes it, with its *Edited* line old → new. A ticket
   raised without a description (a symptom was picked, so the text was
   optional) has no first note.
5. **Edit a note** (U1) — a pencil button on a note's line (a full-size
   `btn btn-outline-secondary`, `title` and `aria-label` "Edit note", as the
   unassign button; not `btn-sm`), for holders of the
   new key `ticket:edit_notes` at the ticket's site (engineer, manager, IT
   admin; admin bypasses as always), while the ticket is open. The same
   dialog, filled with the text, titled *Edit note*, with the hint above the
   field: "Fix a typo or wrong information here. To record new findings, add
   a note." Button *Save changes*. Saving the same text → "Nothing to
   change".
6. **The edit is traceable** — an edited note shows "Edited by `<login>`,
   `<DD-MM-YYYY HH:MM>`" under its text, and a link *Show earlier text* that
   lists each earlier text with who replaced it and when, newest first (the
   link shows only when there is an earlier text). The
   note keeps its place and its time in the timeline: the time it was first
   written.
7. **The API** — `POST /api/tickets/<id>/notes` `{"remark": "<text>"}` → 201;
   `PUT /api/tickets/<id>/notes/<event_id>` `{"remark": "<text>"}` → 200. Both
   answer with the ticket's detail. Notes come in `events` (`event: "note"`,
   the text in `remark`), each with `updated_at`, `updated_by` (the column
   names, as `ticket_parts` sends `created_*`; BR1-10) and `earlier` (the list
   of earlier texts, empty when never edited).

### Out of scope

- Removing a note. A wrong note is corrected by an edit; nothing is deleted.
- Editing a move's remark, or any line other than a note.
- Notes by people without `ticket:restore` (the storekeeper).
- Notes or edits on a closed ticket (§ 9 Q3).
- A photo attached to a particular note. Photos stay in the Photos card; a
  note can say "see photo". Linking a document to an event needs its own
  column — later, if wanted.
- An entered time for a note ("found at 10:30"): a note carries the time it
  was written (§ 7.2).
- Showing the latest note in the ticket list, searching notes, or a push
  alert on a new note (S021 is approved without it).
- Diagnostic procedures (the queued *Procedure master*): a note records what
  was found on this ticket; a procedure records how to diagnose a symptom on
  any machine of the class.

## 2. Standards and practice

- **EN 13306 (maintenance terminology)** describes corrective maintenance as a
  sequence: **fault diagnosis** (recognising the fault, locating it and
  finding its cause), repair, then a **function check-out** (proving it
  works). In plain terms: find where, find why, repair, prove it. Yantra
  records the result today (the cause and action codes at close, the times),
  not the path. Work notes record the path: "no amps, no movement" is fault
  localisation; "to lift and check" is the next diagnostic action. The
  operator's *What is wrong?* is the **fault recognition** that starts the
  diagnosis, so it is the first note.
- **ISO 14224 (reliability and maintenance data)** codes each failure and each
  maintenance action, so failures can be counted and compared. Beside the
  codes, its records keep **free-text remarks** for what a code cannot say
  (the *Remarks* row of Table 6, failure data, and Table 8, maintenance
  data).
  The codes stay the source for the figures; notes add the detail and never
  replace a code.
- **TPM, focused improvement and training pillars**: why-why analysis of a
  repeated breakdown starts from what was observed each time. The note trail
  on the earlier ticket (reached through *Repeat of*) tells the next
  technician what was already tried. Good notes later become one-point
  lessons (Plan § 4.3a).
- **ISO 9001 § 7.5.3 (control of documented information)**: a record is
  protected from unintended change, and a change is identified. Here: a note
  is fixed for its author; a correction by a senior role keeps the earlier
  text, who changed it and when (§ 1.6); and the hint steers new findings
  into new notes, so the record shows what was known at each time.
- **ISO/IEC 27001 A.5.15 (access control)**: editing someone else's record is a
  separate, narrower permission than writing one (`ticket:edit_notes` vs
  `ticket:restore`).

## 3. Where

### Backend

- `backend/config_rbac.py`: `"ticket:edit_notes": ("maint_engineer",
  "it_admin")` (engineer and the roles above, as `ticket:close`), added to
  `SITE_SCOPED`.
- `backend/local_db.py`: migration **v23** (§ 4), with a comment block in the
  v21 / v22 style (the step; why no precondition).
- `backend/tickets_core.py`:
  - `NOTE_EVENT = "note"`, not in `ORDERED_EVENTS`: a note does not move the
    state or the intensity, so it sets no lower bound for a later move's time
    (`_last_ordered_event` reads only `ORDERED_EVENTS`), and the order rule is
    unchanged;
  - `EDIT_NOTES_KEY = "ticket:edit_notes"`, beside `WORK_KEY` (BR1-14);
  - `NOTE_NEEDED = "Enter a note"`;
  - `validate_note(body)` → `(clean, errors)`: `remark` required, a string,
    trimmed, 1–`REMARK_MAX` characters. Missing, `null`, empty or blank →
    "Enter a note"; not a string → "Must be text"; too long → "Too long (max
    1000)". It uses `_optional_text` and then the required check, so the
    messages match the moves' remark;
  - `ticket_times`: no change. A test proves notes leave every figure as it
    was.
- `backend/tickets.py`:
  - `POST /<id>/notes`, `@require_perm(RESTORE_KEY)`: in one transaction,
    `_lock_open_ticket(cur, ticket_id, RESTORE_KEY)` (404, 403 at the ticket's
    site, closed 409, decided from the locked row), then `_add_event(cur,
    ticket_id, NOTE_EVENT, _now(), remark=…)`; 201 with `_ticket_response`;
  - `PUT /<id>/notes/<event_id>`, `@require_perm(EDIT_NOTES_KEY)`:
    `_lock_open_ticket(cur, ticket_id, EDIT_NOTES_KEY)`; then the event row
    `FOR UPDATE` by `id`, `ticket_id` and `event = 'note'` (absent → 404); same
    text → 400 "Nothing to change" on `remark`; otherwise insert the earlier
    text into `ticket_note_edits` and update the event's `remark`,
    `updated_at`, `updated_by`; 200 with `_ticket_response`;
  - `_event_rows` reads `updated_at`, `updated_by` too. The detail path
    (`_detail`, or `_events_out` given the cursor), not `_event_rows`, adds
    `earlier` to each note: its `ticket_note_edits` rows, newest first
    (`remark`, `replaced_at`, `replaced_by`), in one query for the ticket's
    notes. `_event_rows` also serves the repeat checks and
    `latest_restoration`, which need none of it (BR1-11);
  - the LOCK ORDER note gains the note edit: (7), then the note's event row
    `FOR UPDATE`. Only the edit takes that lock, and nothing locks an event
    row first (BR1-05);
  - no new detail field: the page reads the key from the detail's
    `permissions` and the state, as `canWork` (BR1-10). Add note follows
    `ticket:restore` in `permissions` the same way.

### Frontend

- `frontend/src/components/FormModal.vue`: on `shown.bs.modal`, focus the
  first `[autofocus]` element in the body (§ 1.2). The order (BS1-04): at the
  end of the open fade Bootstrap's focus trap focuses the modal element, then
  fires `shown.bs.modal` in the same task; the handler then moves focus to the
  `[autofocus]` field, which is inside the trap, so the trap leaves it. Register
  the handler with `addEventListener` in `onMounted`, as `hide.bs.modal` is.
  S026's `revealError` runs only on a refusal, never at open, so the two never
  meet. No other dialog has an `autofocus` field, so the other 20 are
  unchanged.
- `frontend/src/views/tickets/NoteDialog.vue` (new, beside `MoveDialog.vue`):
  `FormModal` with the one field (`autofocus`, `is-invalid`, message
  `invalid-feedback d-block`); *Add note* / *Save note*, or *Edit note* /
  *Save changes* with the hint; the field message from the 400.
- `frontend/src/views/TicketDetailView.vue`:
  - *Add note* in the action bar (§ 1.1) when `ticket:restore` is in
    `permissions` and the ticket is open;
  - the note line: text in normal size, `pre-wrap`; the pencil when
    `canEditNotes` (open and `ticket:edit_notes` in `permissions`); "Edited by
    …" and *Show earlier text* (a collapsed list under the note);
  - the **Raised** line shows the description in the note style; the
    *Description* card is removed;
  - the header comment names S027.
- `frontend/src/utils/ticketLabels.js`: `EVENT_LABELS.note = "Note"`.

### Tests

- `backend/tests/test_tickets_core.py`: `validate_note`; `ticket_times` with
  notes.
- `backend/tests/test_ticket_work_api.py`: the routes (§ 8).
- `backend/tests/test_migration_v23.py`: the helpers of
  `test_migration_v22.py` (`_recreate`, `_migrate`, `_schema`, the re-run
  assertion); the table and columns on a fresh database and on a v22 database
  with tickets and events.
- `backend/tests/test_rbac.py`: `test_role_matrix` (engineer, manager and IT
  admin gain `ticket:edit_notes`), and the key in
  `test_ticket_assign_and_close_holders`'s parametrize (BR1-04).
- `frontend/tests/ticketLabels.test.js`: "names every S018 event" gains
  `note`.
- `frontend/e2e/tickets-notes.spec.js` (new): § 8 *Automated*. The spec
  closes its own tickets in `afterEach` (S017's 50-ticket list, S020's
  lesson).
- `frontend/e2e/tickets-work.spec.js`, the engineer test "engineer: assign,
  edit and change severity; IT admin with no Team record acknowledges as
  nobody" (BS1-02: named by title, its lines move): `card(page,
  "Description")` becomes the Raised line of the timeline.
- `docs/steps/device-checks.md`: the row of § 8 *On a real device*.

### Docs (at approval, by the planner)

- `docs/Plan.MD` § 4.2: "Photos and remarks at any step" becomes "Photos and
  **work notes** (what was found and tried; the raise's *What is wrong?* is
  the first note) on an open ticket; a remark with each move; an engineer
  corrects a note, keeping the earlier text" (S027).
- `docs/Plan.MD` § 3: a row `ticket:edit_notes` (engineer, manager,
  it_admin) in the permission table, and the key named with the other
  `SITE_SCOPED` keys after it (BR1-07).
- `.claude/CLAUDE.md` SMTW-Review: the spec map gains `tickets-notes` S027.

## 4. Data model (migration v23)

**A note is a row of `ticket_events`**: `event = 'note'`, `remark` the text
(VARCHAR(1000), utf8mb4, so Tamil works), `occurred_at` = the server's clock
when written, `created_by` the author; `from_state`, `to_state`,
`intensity`, `person_id` and S019's columns `NULL`. `event` is a
`VARCHAR(30)` with no list of allowed values, so the new value needs no
change. The timeline's `ORDER BY occurred_at, id` puts each note in place.

**v23** adds what the edit needs:

```sql
ALTER TABLE ticket_events
  ADD COLUMN IF NOT EXISTS updated_at DATETIME NULL,
  ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100) NULL;

CREATE TABLE IF NOT EXISTS ticket_note_edits (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  event_id    INT NOT NULL,
  remark      VARCHAR(1000) NOT NULL,   -- the text before this edit
  replaced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  replaced_by VARCHAR(100) NOT NULL,
  KEY ix_ticket_note_edits_event (event_id, id),
  CONSTRAINT fk_ticket_note_edits_event FOREIGN KEY (event_id) REFERENCES ticket_events (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **No precondition** (CLAUDE.md, Migrations): production holds no
  `ticket_events` rows (v0.1.3, masters only), and in any case both columns
  are `NULL`able and the table is new, so no existing row needs a value.
- `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`, as v21, so a
  retried migration does not fail (BR1-03).
- `updated_*` is set only on a note; other events stay unchanged forever.

## 5. Rules

### 5.1 Who and when

| Action | Key at the ticket's site | Ticket |
|---|---|---|
| Add a note | `ticket:restore` (operator and up, IT admin; § 9 Q2b (b)) | open |
| Edit a note | `ticket:edit_notes` (engineer and up, IT admin) | open |
| Edit the description (the first note) | `ticket:work`, as today (§ 9 Q6) | open |

- Both checked on the locked row, as every ticket write. The buttons follow
  the detail's `permissions` and state, so nobody sees a button that ends in
  a 403.
- Closed → 409 "This ticket is closed" (the existing message). Closed is final
  and read-only (S018).
- A note or an edit never changes the state, the intensity, the assignees or
  the times.
- An engineer may edit anyone's note, their own included. A technician cannot
  edit even their own: they add a correcting note (§ 9 Q1).
- A ticket that came back as a repeat accepts notes and edits: they record
  what was found on this ticket, unlike a move, which the repeat refuses.

### 5.2 Transactions and locks

- **Add:** the ticket row `FOR UPDATE` first (as every ticket write), then the
  event insert. The insert's foreign keys lock the ticket row (already held)
  and no person (`person_id` is `NULL`).
- **Edit:** the ticket row `FOR UPDATE`, then the note's event row `FOR
  UPDATE`, then the `ticket_note_edits` insert (its foreign key locks the
  event row, already held). Every other writer of a ticket's events holds the
  ticket row first. So two edits of one note, or an edit and a new note, wait
  for each other, and both land in order.
- The lock order of the `tickets.py` note is unchanged (the ticket row
  first), and no new deadlock is added. The note's text gains the event-row
  lock of the edit (§ 3, BR1-05).

### 5.3 Messages (UI text, CLAUDE-COMMON Scope B)

| Case | Where | Text |
|---|---|---|
| Empty or blank | under *Note* | Enter a note |
| Over 1000 | under *Note* | Too long (max 1000) |
| Edit with the same text | under *Note* | Nothing to change |
| Edit hint | above *Note*, in *Edit note* | Fix a typo or wrong information here. To record new findings, add a note. |
| Closed meanwhile | the dialog's top bar | This ticket is closed |
| No access at the site | the dialog's top bar | (the existing 403 text) |

## 6. API

| Method | Path | Key at the ticket's site | Body | Answer |
|---|---|---|---|---|
| POST | `/api/tickets/<id>/notes` | `ticket:restore` | `{"remark": "…"}` | 201, the detail |
| PUT | `/api/tickets/<id>/notes/<event_id>` | `ticket:edit_notes` | `{"remark": "…"}` | 200, the detail |

Refusals: 400 (field `remark`), 403, 404 (ticket not visible; the event not a
note of this ticket), 409 (closed). The detail's events gain `updated_at`
and `updated_by`, and notes gain `earlier`; the detail gains no other field.

## 7. Design decisions

1. **Append by default; edit only for corrections, by senior roles, keeping
   the earlier text** (U1). *Why:* new findings belong in new notes, so the
   trail shows how the diagnosis went; a typo or wrong fact still needs a
   fix. Keeping the earlier text makes the change identifiable (ISO 9001
   § 7.5.3). *Rejected:* an edit in place with only "edited by, when" (the
   wrong text is lost, so nobody can see what was corrected); an *Edited*
   timeline line old → new, like the ticket's edit. Two 1000-character texts
   do not fit one remark, and the change would sit far from the note.
2. **A note carries the time it was written, and keeps it when edited.**
   *Why:* it is a record of what was known when; an entered time would need
   the order rule and the backdating window of the moves. *Rejected:* an
   optional "when found" time like the moves' (more fields on a phone, for a
   gain the text gives: "at 10:30 found …").
3. **The first note is shown, not copied** (U1). *Why:* the description
   already exists, has its edit with an *Edited* line, and is read by the
   symptom rules (`description_error`); a copy in `ticket_events` could drift
   from it. *Rejected:* writing a note event at the raise (two copies of one
   text, and the *Edit* dialog would have to change both).
4. **Notes are rows of `ticket_events`, not a new table.** *Why:* the
   timeline already reads, orders and shows these rows with their author and
   time. *Rejected:* a `ticket_notes` table (a second list to merge into the
   timeline, for no field the event row lacks). Only the edit history gets
   its own table, because an event has one text.
5. **A new key `ticket:edit_notes`.** *Why:* RBAC keys name actions, and route
   code names only keys (CLAUDE-COMMON RBAC pattern); the edit's holders
   happen to equal `ticket:close`'s today, but the two can drift. *Rejected:*
   reusing `ticket:close` (a close permission that also edits notes is a
   hidden side effect).
6. **The button in the action bar** (BR1-02). *Why:* on a phone the Timeline
   card sits below six cards (Times, Assigned, Labour, Parts used, the repeat
   box, Details); a technician mid-diagnosis should not scroll past them to
   write one line. The action bar is "what you can do now", and *Schedule*
   already sits there in outline without being the next move. *Rejected:* the
   Timeline card's header (one long scroll on a phone); both places (two
   buttons for one action).
7. **The text in `remark`.** *Why:* the column and the API field already mean
   "the free text of this line". *Rejected:* a new field name `text` (a
   second name for the same thing).

## 8. Tests and acceptance

### Pure (`test_tickets_core.py`)

- `validate_note`: missing, null, empty, blank, a number, a list, 1000 and
  1001 characters, trimmed, line breaks kept; the messages of § 5.3.
- `ticket_times`: a ticket's figures with notes in every state equal the
  figures without them (response, repair, downtime, waiting, planned).

### API (`test_ticket_work_api.py`)

- Add:
  - a technician adds a note → 201; the event is in `events` with `event`
    `note`, the trimmed text, the author, `occurred_at` now, `earlier` empty;
    the state and the times are unchanged;
  - notes in raised, acknowledged, in progress, scheduled and back in service
    are accepted;
  - an operator and a supervisor add a note → 201 (Q2b (b)); a person who
    sees the ticket but holds `ticket:restore` only at another site → 403
    (`user_at_sites`); a ticket outside the user's units → 404; a closed ticket → 409; an empty body, blank text,
    a list → 400 on `remark`;
  - a note does not move the lower bound of a move's time: a move entered
    between the last move and a later note is accepted;
  - a ticket that came back as a repeat accepts a note.
- Edit:
  - an engineer edits a technician's note → 200; `remark` is the new text,
    `updated_by` the engineer, `earlier` holds the old text with who and when;
    a second edit → `earlier` has two rows, newest first; the note's
    `occurred_at` and place are unchanged;
  - a technician (own note or not) → 403; a person who is a technician at
    this site and an engineer at another → 403; IT admin → 200;
  - the event id of a move, or of a note on another ticket → 404;
  - the same text → 400 "Nothing to change"; a closed ticket → 409;
  - the detail's `permissions` hold `ticket:edit_notes` for an engineer at
    the ticket's site, not for a technician.
- The new key is in `SITE_SCOPED`, and an engineer whose role differs per site
  can edit at one site and not at the other.

### Migration (`test_migration_v23.py`)

- From v22 with tickets and events: the columns and the table exist, every
  existing event has `updated_*` `NULL`; running v23 again changes nothing.

### Automated (e2e, `tickets-notes.spec.js`)

- **Important** — a technician opens a ticket, presses *Add note* in the
  action bar; the cursor is in the field (`openAction`, then
  `toBeFocused()` on *Note*, as S026's labour test: `openDialog` returns only
  once focus is inside the dialog, so this is no race; BS1-04); the
  technician enters a
  two-line note, *Save note*; the timeline shows **Note**, the author and both
  lines. Phone and desktop.
- **Important** — an engineer edits that note: the dialog shows the hint;
  after *Save changes* the note shows the new text and "Edited by …"; *Show
  earlier text* shows the old text.
- The Raised line shows the raise's *What is wrong?* text; the page has no
  *Description* card.
- *Save note* with an empty field → "Enter a note" under the field, in view;
  nothing is added.
- An operator adds a note (Q2b (b)) and sees no pencil; a technician sees no
  pencil either; nobody sees *Add note* or the pencil on a closed ticket.

### On a real device

- **Plain** — on a Samsung Galaxy, use voice typing (the microphone on the
  Samsung keyboard) in the *Note* field, in English and in Tamil; the text
  lands in the field and saves, and the Tamil text shows on the timeline as
  spoken. Account: a technician; network: plant Wi-Fi or mobile data; where:
  either (the dev server needs no account). On production, close the ticket
  as *Not a fault* afterwards. A gloved or busy technician will talk rather
  than type.

### Acceptance

Green suites; the **full** e2e suite passes on the three projects, because
S027 changes `FormModal.vue`, shared frontend code (BS1-01; README § Manual
checks, decided 22-10-2026); a note shows on the
timeline in place; an edit keeps the earlier text; no figure changes because
of a note.

## 9. Open questions and assumptions

1. ~~Can a note be edited or removed?~~ **Settled (U1):** engineer, IT admin
   and admin edit, to fix a typo or wrong information; new findings are new
   notes. *Proposed detail:* no removal; the earlier text is kept (§ 7.1); a
   technician corrects their own note with a new note.
2. ~~Can the operator who raised the ticket add notes?~~ **Settled (U1):** the
   operator writes at the raise, in *What is wrong?*, and that text is the
   first note.
   **Q2b (BR1-01) — who may add a later note?** A technician without a phone
   (the fitter on the genset round, Plant-Facts § 5) is paired with a
   supervisor, who records *back in service* for him (`ticket:restore`). With
   `ticket:work` only, the supervisor cannot write what the fitter found
   while the work goes on; only an engineer can.
   - **(a)** `ticket:work` only (technician, engineer, manager, IT admin). The
     fitter's finding goes in the back-in-service remark, or an engineer types
     it. An operator's later word is a new ticket or a repeat.
   - **(b) Recommended:** `ticket:restore` holders too (operator, supervisor
     and up: whoever may confirm the machine is back may write what they
     see). The supervisor records for the fitter; an operator can add "the
     noise is back at 3 pm". The edit stays with `ticket:edit_notes`.
3. **Notes after close?** *Proposed:* no; closing ends the record (S018).
   *Alternative:* engineers add a note or an edit after close, which breaks
   "closed is read-only".
4. ~~Is the Timeline card close enough on a phone?~~ **Proposed (BR1-02):**
   no; *Add note* goes in the action bar (§ 1.1, § 7.6). *Alternative:* the
   Timeline card's header.
5. **Does an engineer's first note on a raised ticket acknowledge it?**
   *Proposed:* no; *Acknowledge* stays its own tap, and a note sets no
   response time.
6. **Who may edit the first note?** Today a technician may change the
   description in the ticket's *Edit* dialog (`ticket:work`, S018), with an
   *Edited* line old → new. *Proposed:* keep that. A technician often
   corrects the symptom and the part in the same dialog, and the old text
   stays on the *Edited* line. *Alternative:* the description, too, only by
   `ticket:edit_notes` holders, like the other notes — the same rule for
   every note, but the *Edit* dialog splits by field.
7. *Assumption:* 1000 characters is enough for one note; a longer story is
   two notes.
8. *Assumption:* the timeline shows the login name as the author, as every
   line does today.

## 10. Amendments

None.

## Review log

### U1 — user answers, 22-10-2026 (before review r1)

"note edit - possible for Admin, IT Admin, Engineer. but suggest not to edit,
to append. use edit to fix typo / wrong info. not developments." → § 1.5,
§ 1.6, § 2, § 3, § 4 (migration v23), § 5, § 7.1, § 7.5, § 9 Q1.

"operator who raised the ticket needs a text input to describe what he sees.
there is a 'what is wrong?' field for it. it must be the first note." →
§ 1.4, § 7.3, § 9 Q2, Q6.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 22-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 supervisor named as a `ticket:work` holder; who records for a phoneless technician | minor | **Accepted**: § 1.1 corrected; the choice is **§ 9 Q2b for the user**, (b) `ticket:restore` holders recommended |
| BR1-02 *Add note* at the bottom of a long page on a phone | minor | **Accepted** (b): an outline *Add note* in the action bar (§ 1.1, § 3, § 7.6, § 8); Q4 answered with it, the user may override |
| BR1-03 v23 idempotence wording; the SQL lacks it | minor | **Accepted**: `ADD COLUMN IF NOT EXISTS` as v21; the no-precondition reason is that production has no `ticket_events` rows; the comment block and the v22 test helpers named (§ 3, § 4) |
| BR1-04 the tests that break are not named | minor | **Accepted**: `tickets-work.spec.js` line 217, `test_rbac.py` (matrix and holders), `ticketLabels.test.js` named in § 3 |
| BR1-05 the LOCK ORDER note's text changes | minor | **Accepted**: § 3 and § 5.2 say the note gains the event-row lock of the edit |
| BR1-06 grow and focus have no pattern | minor | **Accepted** (a): fixed `rows="4"`; `FormModal.vue` focuses `[autofocus]` on `shown.bs.modal`; the markup S026 finds, so the order holds both ways (§ 1, § 1.2, § 3) |
| BR1-07 Plan.MD § 3 permission table | minor | **Accepted** (§ 3 Docs) |
| BR1-08 stale Baseline | nit | **Accepted**: bbaed12 |
| BR1-09 standards wording | nit | **Accepted** (§ 2) |
| BR1-10 `edited_*` vs `updated_*`; `can_edit_notes` | nit | **Accepted**: the column names; no new detail field, the page reads `permissions` and the state as `canWork` (§ 1.7, § 3, § 6) |
| BR1-11 the edits query in `_event_rows` | nit | **Accepted**: in the detail path only (§ 3) |
| BR1-12 "another site → 403" answers 404 | nit | **Accepted**: the tests use a person with a role at this site and another role at another site (§ 8) |
| BR1-13 the device-check row | nit | **Accepted**: where either; close as *Not a fault* on production; what you see (§ 8) |
| BR1-14 key location, pencil target, empty state | nit | **Accepted** (§ 1.5, § 1.6, § 3) |
| BR1-15 scope A wording | nit | **Accepted** (§ 1.4, § 5.2, § 7.1) |

### Gate A — approved 22-10-2026 by KLA ("S027 Work notes: gate A - approved")

U2: the user approved the brief as shown, with § 9 as proposed and recommended:
- Q2b **(b)**: `ticket:restore` holders add notes (operator, supervisor and up)
  → § 1.1, § 1 Out of scope, § 2, § 3, § 5.1, § 6, § 8;
- Q3 no notes or edits after close; Q4 *Add note* in the action bar; Q5 a note
  does not acknowledge; Q6 the description stays editable in the *Edit* dialog
  by `ticket:work`.

### Staleness check s1 — `2-brief-review-s1.md` (Fable), answered 22-10-2026

Reviewed against 79fc61d + uncommitted S026. No blocker or major.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 the full suite is needed (FormModal.vue is shared code) | minor | **Accepted** (§ 8 Acceptance) |
| BS1-02 "line 217" is stale | nit | **Accepted**: the test named by title (§ 3) |
| BS1-03 the either-order hedge is moot | nit | **Accepted**: the facts the coder relies on; Baseline 79fc61d + uncommitted S026 (§ 1 Order, header) |
| BS1-04 the focus sequence and how to test it | nit | **Accepted** (§ 3 FormModal, § 8 Automated) |
