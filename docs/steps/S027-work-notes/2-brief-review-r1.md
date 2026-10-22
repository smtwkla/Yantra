```
Step: S027 — Work notes
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: bbaed12 (S025, S019 and S020 are committed in b6b8dfb; no step is uncommitted in the working tree)

# S027 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** The design holds: a `note`
event outside `ORDERED_EVENTS` disturbs none of the code that reads
`ticket_events`, the locks follow `tickets.py`'s order, the key fits the RBAC
pattern, and v23 needs no precondition. The findings are seven `minor` (two of
them decisions for the user: who may add a note, and where the button sits on a
phone) and eight `nit`.

## Findings

### BR1-01 (minor) — § 1.1 names the supervisor as a `ticket:work` holder; and who records a phoneless technician's findings is not decided

**Problem.** § 1.1 says *Add note* is shown to holders of `ticket:work`
"(technician, supervisor, engineer, manager, IT admin)". The supervisor does
not hold `ticket:work` (`config_rbac.PERMISSIONS`, `ROLE_INCLUDES`; Plan.MD § 3:
"a supervisor does not work tickets"). § 5.1 and § 1 *Out of scope* say the
opposite of § 1.1, so the brief contradicts itself.

Behind the slip is a real gap. Plan.MD § 3 and `Maintenance-Philosophy.md` § 11
say a technician without a phone (the fitter on the genset round,
`Plant-Facts.md` § 5) is paired with a supervisor or engineer who records for
him, and the supervisor already records *back in service* with the technician's
name (`ticket:restore`). With the brief as written, the supervisor cannot record
what the fitter found while the work goes on ("no amps, to lift and check");
only an engineer can.

**Why it matters.** The coder would ship the § 5.1 rule, and the user would
approve the § 1.1 list. The floor case decides which is right.

**Options.**
- (a) Keep `ticket:work`. Fix § 1.1. A phoneless technician's finding goes in
  the back-in-service remark, or the engineer types it. Simplest; the genset
  case waits.
- (b) *Add note* by `ticket:restore` holders (operator and up: whoever may
  confirm the restoration may write what they see). The supervisor can record
  for the fitter; an operator can add "the noise is back". § 9 Q2's "no later
  notes by operators" changes, so this is a question for the user at gate A.

**Recommendation.** Fix § 1.1 now. Put (a) / (b) to the user as a question in
§ 9, with (b) recommended for the genset and sorting-line cases. Either way,
the edit stays with `ticket:edit_notes`.

### BR1-02 (minor) — on a phone, *Add note* sits at the bottom of a long page

**Problem.** The button goes in the Timeline card's header. On a phone the
page is: the action bar, then Times, Assigned, Labour and Parts used (four
stacked cards, shown to every `ticket:work` holder even when empty), the
repeat box, Details, and only then Timeline (`TicketDetailView.vue` § 2–3).
The technician mid-diagnosis, gloves on, scrolls past six cards to write one
line. § 9 Q4 asks the user; the brief should carry a recommendation.

**Options.**
- (a) The Timeline header only (as written). The note appears where it is
  written; one long scroll on a phone.
- (b) The action bar: an outline button *Add note* after the chain move,
  before *Change severity* (the same style as *Schedule*). It is not a move,
  but the action bar is "what you can do now". The note still lands in the
  timeline. On a wide screen the button sits in the same row.
- (c) Both. Two buttons for one action; clutter.

**Recommendation.** (b). Say so in § 7.6 and answer Q4 with it; the user can
override at gate A.

### BR1-03 (minor) — v23's idempotence text does not match v20–v22, and the SQL block lacks it

**Problem.** § 4 says the `ADD COLUMN` statements follow "a check of
`information_schema` before each". v21 does not do that: it uses
`ADD COLUMN IF NOT EXISTS` (MariaDB; base § Local DB Migration Pattern), and
`information_schema` is read only by v20's precondition. The SQL block in § 4
has plain `ADD COLUMN`, so a retried v23 would fail with "duplicate column".

Also, the reason no precondition is needed is stated as "both columns are
NULLable and the table is new". CLAUDE.md's SMTW-Review rule is about rows
that exist in production: production runs v0.1.3 with masters only (Plan.MD
§ 1, *Schema and releases*), so `ticket_events` has no rows there. State that
fact; it is the stronger reason and the one the audit checks.

**Fix.** In § 4: `ADD COLUMN IF NOT EXISTS updated_at …`, `ADD COLUMN IF NOT
EXISTS updated_by …`; `CREATE TABLE IF NOT EXISTS` is already there. Replace
the `information_schema` sentence with "as v21". Add "production holds no
`ticket_events` rows (v0.1.3, masters only)". Add the migration's comment block
(the v21 / v22 style: the step, why no precondition). For
`test_migration_v23.py`, name the helpers of `test_migration_v22.py`
(`_recreate`, `_migrate`, `_schema`, the re-run assertion).

### BR1-04 (minor) — the tests this change breaks are not named

**Problem.** § 3 says "Existing e2e specs that look for the *Description* card
(if any)". There is one, and two more suites break:

- `frontend/e2e/tickets-work.spec.js`, test "engineer: assign, edit and change
  severity; IT admin with no Team record acknowledges as nobody", line 217:
  `await expect(card(page, "Description")).toContainText(…)` — it must look at
  the Raised line.
- `backend/tests/test_rbac.py::TestComputePermissions::test_role_matrix`:
  exact key sets per role; engineer, manager and IT admin gain
  `ticket:edit_notes`. Add the key to
  `test_ticket_assign_and_close_holders`'s parametrize too (same holders, same
  `SITE_SCOPED` check).
- `frontend/tests/ticketLabels.test.js` "names every S018 event": add `note`
  to its list.

**Fix.** Name the three in § 3 *Tests* and § 8.

### BR1-05 (minor) — the lock note in `tickets.py` changes; the brief says it is unchanged

**Problem.** § 5.2 says "The lock order of the `tickets.py` note is unchanged
… and no new deadlock is added". The order is unchanged, but the note's text
is not: it says working a ticket "locks (7) explicitly, and nothing else
explicitly". The note edit locks a second row explicitly: the event row
`FOR UPDATE` after (7). Nothing else locks event rows, and the
`ticket_note_edits` insert's foreign key takes a shared lock on a row the
transaction already holds, so the claim "no new deadlock" holds. The docstring
must say so, or the next step reads a note that is false.

**Fix.** In § 3 `backend/tickets.py`: "the LOCK ORDER note gains the note
edit: (7), then the note's event row `FOR UPDATE` (only the edit takes it;
nothing locks event rows first)". Keep § 5.2 as it is otherwise.

### BR1-06 (minor) — the dialog's two behaviours have no pattern in the code

**Problem.** § 1.2 says the text area "grows with the text" and "the cursor
starts in the field". Neither exists today:

- every remark field is a fixed `rows` textarea (`EventFields.vue` rows 2,
  `EditTicketDialog.vue` rows 3); auto-grow needs JavaScript on `input`;
- no dialog focuses a field on open. Bootstrap ignores the `autofocus`
  attribute in modals, and its focus trap focuses the modal element itself
  when the open transition ends, so a `nextTick` focus after `openCreate()`
  is undone. The focus must be set on `shown.bs.modal`, which `FormModal.vue`
  does not expose.

The coder would decide both alone, in shared code.

**Options.**
- (a) Drop "grows with the text": `rows="4"` with `maxlength`; a long note
  scrolls inside the field. For the cursor, `FormModal.vue` listens to
  `shown.bs.modal` and focuses the first element marked `autofocus` in its
  body — one line, usable by every later dialog. Recommended.
- (b) Keep auto-grow with a small `input` handler in `NoteDialog.vue`. More
  code for a field of four rows.

Also say that `NoteDialog.vue` marks its field `is-invalid` and its message
`invalid-feedback d-block`, so S026's `revealError` covers it with no change
whichever step lands first. That makes the ordering note in § 1 sound in both
orders.

### BR1-07 (minor) — Plan.MD § 3's permission table is not updated

**Problem.** § 3 *Docs* updates Plan.MD § 4.2 only. Plan.MD § 3 lists every
ticket key in its matrix and names the `SITE_SCOPED` keys in prose; S018 added
its four keys there. Without a row for `ticket:edit_notes` the matrix is wrong.

**Fix.** Add to § 3 *Docs*: Plan.MD § 3, a row `ticket:edit_notes` (engineer,
manager, it_admin) and one sentence in the paragraph after the table.

### BR1-08 (nit) — the Baseline line is stale

The header says `Baseline: 3df667c + uncommitted S025, S019, S020`. Those
three steps are committed in b6b8dfb; HEAD is bbaed12 and `git status` shows
no step's code uncommitted. The planner copies the line above into the header
at approval. "v23 after S020's v22" holds (`local_db.LATEST_VERSION` is 22).

### BR1-09 (nit) — standards wording

- **EN 13306.** In the standard, *fault diagnosis* covers fault recognition,
  fault localisation and cause identification together; the brief gives
  "fault diagnosis (finding its cause)". Say "fault diagnosis (recognising
  the fault, locating it and finding its cause)". The last step is *function
  check-out*, not "function check". Plain meaning for the owner: the
  corrective sequence is find where, find why, repair, then prove it works.
- **ISO 14224.** Name where the free text sits: the *Remarks* row of Table 6
  (failure data) and Table 8 (maintenance data). The point that codes stay
  the source for the figures is right.
- **ISO 9001 § 7.5.3** and **ISO 27001 A.5.15** are cited correctly.

### BR1-10 (nit) — two names for one thing in the API

- `edited_at` / `edited_by` rename the columns `updated_at` / `updated_by`.
  Send the column names, as `ticket_parts` sends `created_at` / `created_by`
  (CLAUDE-COMMON: one term for one thing).
- `can_edit_notes` repeats what the detail already sends: `permissions` (the
  keys at the ticket's site) and `state`. `canWork` and `canAssign` are
  computed in `TicketDetailView.vue` from those. `canEditNotes = isOpen &&
  can("ticket:edit_notes")` needs no new field or test. (`can_add_documents`
  is the other precedent; pick one and say why.)

### BR1-11 (nit) — the edits query belongs in the detail path only

`_event_rows` also serves `_check_repeat`, `_recheck_repeat` and
`latest_restoration`, which need only `event` and `occurred_at`. Put the
`ticket_note_edits` query where the detail is shaped (`_detail`, or an
`_events_out(cur, rows)`), not in `_event_rows`, so a repeat check does not
run it.

### BR1-12 (nit) — one API test is worded for the wrong status

"A technician of another site → 403" answers 404: with no membership at the
ticket's site the ticket is not visible (`read_ticket`). The 403 case is a
person who is an operator at this site and a technician at another
(`user_at_sites` in `test_ticket_work_api.py`). Word both the add and the
edit tests that way.

### BR1-13 (nit) — the device check's row

- *Where*: the dev server does as well (no account needed), so "Either".
- Add the convention of `device-checks.md`: on production, close the ticket
  as *Not a fault* afterwards.
- Add the row's "what you should see": the Tamil text shows on the timeline
  as typed (utf8mb4).

### BR1-14 (nit) — small gaps the coder would fill alone

- Where `EDIT_NOTES_KEY` is defined: `tickets_core.py`, beside `WORK_KEY`.
- The pencil's tap target: a full-size `btn btn-outline-secondary` with
  `title="Edit note"` and an `aria-label`, as the unassign button; not
  `btn-sm`.
- The empty state of *Show earlier text* needs none (the link shows only when
  `earlier` is not empty); say so.

### BR1-15 (nit) — scope A wording

- § 1.4, first sentence: 37 words; split at "and the separate".
- § 5.2 *Edit*: "Every other writer of a ticket's events holds the ticket row
  first, so two edits of one note, or an edit and a new note, wait for each
  other and both land in order" — two sentences.
- § 7.1 *Rejected*: the bracketed clause is a sentence of its own.

## Checked and found consistent

- **`note` outside `ORDERED_EVENTS`.** `_last_ordered_event` filters on
  `ORDERED_EVENTS`, so a note never sets a move's lower bound.
  `ticket_times` skips any event not in `ORDERED_EVENTS` (`continue`), so
  response, repair, downtime, waiting, the split by reason and planned
  downtime are unchanged. `latest_restoration` reads `BACK_IN_SERVICE_EVENT`
  only, so the repeat rules and S025's send-back refusal are unchanged.
  `_not_a_fault` counts `ticket_parts`, not events. The timeline's
  `ORDER BY occurred_at, id` places a note by its time. In the frontend,
  `intensityChanges` returns "" for an event with no intensity and
  `planChanges` for any event not scheduled / rescheduled; `EVENT_LABELS`
  gets `note`. No other reader of `ticket_events` exists (`documents.py`
  reads none).
- **Locks (§ 5.2).** Add: (7) `FOR UPDATE`, then the insert; its foreign keys
  lock the ticket row (held) and no person. Edit: (7), the event row, the
  `ticket_note_edits` insert; every other writer takes (7) first. No edge is
  added to the four accepted deadlocks.
- **RBAC.** `"ticket:edit_notes": ("maint_engineer", "it_admin")` with the
  manager inheriting, in `SITE_SCOPED`; route code names the key only;
  `require_perm` early, `_lock_open_ticket` at the ticket's site; admin
  bypasses in `has_perm_at`. The pattern of `ticket:close`.
- **v23.** New nullable columns and a new table; no precondition; see BR1-03
  for the wording.
- **First note (§ 1.4, § 7.3).** Nothing copied; `tickets.description` stays
  the one text; the *Edit* dialog and its *Edited* line
  (`edit_lines`, `_EDIT_LABELS`) are unchanged; the list's search on
  `t.description` is unchanged. The Raised line is the timeline's first line,
  so on a phone the operator's words sit higher than today's card below the
  timeline.
- **Validation.** `validate_note` on `_optional_text` then the required
  check: the pattern of `validate_part`; the messages match the moves'
  remark; 400 through `clean_body`.
- **Edit history.** Two engineers editing the same note from stale pages both
  land, each `earlier` row keeps the text it replaced; nothing is lost.
  Accepted at this size.
- **UI text (scope B).** *Add note*, *Save note*, *Edit note*, *Save
  changes*, *Show earlier text*, "Enter a note", "Nothing to change", the
  hint: verbs first, one line, no codes.
- **Manual checks.** The automated list covers what a browser can judge; the
  device row is voice typing, which a browser cannot; it is marked plain,
  rightly.
- **Track.** Full: a migration, a new key, a lock. Right.
- **Ordering after S026.** Sound in both orders once BR1-06's markup note is
  in the brief.
