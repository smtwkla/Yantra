```
Step: S027 — Work notes
Doc: impl-report
Author: Coder (Opus)
Date: 22-10-2026
```

# S027 — Impl report

Built on 79fc61d + uncommitted S026 (at gate B). S026's behaviour is unchanged.

## 1. What was built

- **Add note.** An open ticket's action bar has an outline *Add note* button for holders of `ticket:restore` at the ticket's site: operator, supervisor, technician, engineer, manager, IT admin. It shows in every open state.
- **The note dialog.** One field, *Note* (four rows, at most 1000 characters, line breaks kept). The cursor starts in the field. Buttons *Save note* and *Cancel*. An empty note is refused under the field with "Enter a note".
- **On the timeline.** A note is a line labelled **Note**, with the time, the login name of the author and the text in the normal size, line breaks kept.
- **The first note.** The raise's *What is wrong?* (the ticket's description) shows on the **Raised** line in the note style. The *Description* card is gone. Nothing is copied: the *Edit* dialog still changes the description.
- **Edit a note.** Holders of the new key `ticket:edit_notes` (engineer, manager, IT admin; admin bypasses) get a pencil on each note while the ticket is open. The dialog is titled *Edit note*, shows the hint "Fix a typo or wrong information here. To record new findings, add a note.", and saves with *Save changes*. The same text is refused: "Nothing to change".
- **Traceable edits.** A corrected note shows "Edited by `<login>`, `<DD-MM-YYYY HH:MM>`" and a *Show earlier text* button. It lists each earlier text with "Replaced by `<login>`, `<time>`", newest first. The note keeps its time, its place and its author.
- **The API.** `POST /api/tickets/<id>/notes` → 201 and `PUT /api/tickets/<id>/notes/<event_id>` → 200, both with the ticket's detail.
- **Migration v23.** `ticket_events.updated_at` / `updated_by`, and the new table `ticket_note_edits`.
- **`FormModal.vue`** focuses the first `[autofocus]` field of a dialog once Bootstrap has shown it. Only the note field uses it today.

## 2. How it works

**Backend**

- `tickets_core.py`:
  - `NOTE_EVENT = "note"` is not in `ORDERED_EVENTS`. So `ticket_times` skips notes, and `_last_ordered_event` never reads one: a note sets no lower bound for a later move's time;
  - `EDIT_NOTES_KEY` sits beside `WORK_KEY`; `NOTE_NEEDED = "Enter a note"`;
  - `validate_note(body)` runs the moves' `_optional_text` on `remark` (not text → "Must be text", over 1000 → "Too long (max 1000)", trimmed), then refuses a missing or blank text with "Enter a note".
- `tickets.py`:
  - `add_note` (`@require_perm(RESTORE_KEY)`): the body first (as `edit_ticket`), then in one transaction `_lock_open_ticket(cur, id, RESTORE_KEY)` (404, 403 at the ticket's site, closed 409, from the locked row), then `_add_event(…, NOTE_EVENT, _now(), remark=…)`. 201 with the detail;
  - `edit_note` (`@require_perm(EDIT_NOTES_KEY)`): the body, then `_lock_open_ticket(cur, id, EDIT_NOTES_KEY)`, then the event row `FOR UPDATE` by `id`, `ticket_id` and `event = 'note'` (none → 404). The same text → 400 "Nothing to change" on `remark`. Otherwise the old text goes into `ticket_note_edits` and the event's `remark`, `updated_at`, `updated_by` change. Both rows get one clock value. 200 with the detail;
  - `_event_rows` now reads `e.id`, `e.updated_at`, `e.updated_by`;
  - the detail path only: `_note_edits(cur, ticket_id)` reads every earlier text of the ticket's notes in one query, newest first. `_events_out(rows, note_edits)` puts `earlier` on each note (empty when never corrected). The repeat checks and `latest_restoration` still call `_event_rows` alone (BR1-11);
  - the module docstring's LOCK ORDER note names the new note with the other writes that lock (7) only, and adds the correction's event-row lock after (7). Nothing else locks an event row, so there is no new lock-order edge.
- `config_rbac.py`: `"ticket:edit_notes": ("maint_engineer", "it_admin")`, with a comment, and the key in `SITE_SCOPED`.
- `local_db.py`: v23 in the v21 / v22 style: a comment block (the step, why no precondition), `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`, so a half-applied v23 re-runs.

**Frontend**

- `FormModal.vue`: a `shown.bs.modal` listener (added with `addEventListener` in `onMounted`, as `hide.bs.modal`) focuses `.modal-body [autofocus]`. Bootstrap has already focused the modal element at that moment, and the field is inside its focus trap, so the focus stays. S026's `revealError` runs only on a refusal, never at open.
- `NoteDialog.vue` (new, beside `MoveDialog.vue`): `FormModal` + `useFormModal`, `openAdd()` and `openEdit(note)`. The field has `autofocus`, `is-invalid` and an `invalid-feedback d-block` message, so S026 scrolls a refusal into view. A 409 with no field (closed meanwhile) shows in the top bar and asks the page to reload, as `MoveDialog` does.
- `TicketDetailView.vue`:
  - `canAddNote` = open and `ticket:restore` in `permissions`; `canEditNotes` = open and `ticket:edit_notes` in `permissions` (no new detail field, BR1-10);
  - *Add note* sits after the chain moves and *Machine stopped*, before *Change severity*;
  - the timeline line: the author row has the pencil on the right (`btn btn-outline-secondary`, `title` and `aria-label` "Edit note"); the Raised line shows the description and a note its text in `.note-text` (normal size, `pre-wrap`); "Edited by …"; the *Show earlier text* button opens the earlier texts under the note;
  - the *Description* card is removed; the header comment names S027.
- `ticketLabels.js`: `EVENT_LABELS.note = "Note"`.

## 3. Files touched (17)

| File | Change |
|---|---|
| `backend/config_rbac.py` | `ticket:edit_notes` and its comment; the key in `SITE_SCOPED` |
| `backend/local_db.py` | migration v23 with its comment block |
| `backend/tickets_core.py` | `EDIT_NOTES_KEY`, `NOTE_EVENT`, `NOTE_NEEDED`, `validate_note` |
| `backend/tickets.py` | the two routes; `_event_rows` columns; `_note_edits`; `_events_out` adds `earlier`; the docstring (S027, LOCK ORDER) |
| `backend/tests/conftest.py` | `ticket_note_edits` in the session clean-up list, before `ticket_events` |
| `backend/tests/test_tickets_core.py` | `TestValidateNote`, `TestTicketTimesWithNotes` |
| `backend/tests/test_ticket_work_api.py` | `TestAddNote` (15 with parameters), `TestEditNote` (9) |
| `backend/tests/test_migration_v23.py` (new) | a fresh database; a v22 database with a ticket and events; the re-run |
| `backend/tests/test_rbac.py` | the matrix (engineer, manager, IT admin gain the key); the key in `test_ticket_assign_and_close_holders` |
| `frontend/src/components/FormModal.vue` | the `[autofocus]` focus on `shown.bs.modal`; the header comment |
| `frontend/src/views/tickets/NoteDialog.vue` (new) | the add / edit dialog |
| `frontend/src/views/TicketDetailView.vue` | Add note, the note line, the pencil, Edited by, Show earlier text, the Raised line; the Description card removed |
| `frontend/src/utils/ticketLabels.js` | `note: "Note"` |
| `frontend/tests/ticketLabels.test.js` | "names every S018 event" also names `note` |
| `frontend/e2e/tickets-notes.spec.js` (new) | the five § 8 *Automated* checks |
| `frontend/e2e/tickets-work.spec.js` | the engineer test reads the description on the Raised line, not the Description card |
| `docs/steps/device-checks.md` | row 13 (voice typing on a Samsung Galaxy) |

The brief's status and the README index row are updated too (Implementing → In code review).

## 4. Decisions taken

These are small, forced choices the brief does not cover:

1. **The events carry `id`.** The detail's events had no id, and the PUT needs one. `_event_rows` now reads `e.id`, so every event carries it. This is one more field than § 6 lists ("the detail gains no other field").
2. **`earlier` is on notes only.** Other events have no `earlier` key. § 1.7 says "notes gain `earlier`". A test checks this.
3. **The note edit's insert is written out**, not through `insert_row`. `insert_row` adds a `created_by` column, and `ticket_note_edits` has `replaced_by` (the brief's SQL). The update is written out too, not through `update_row`, so that `replaced_at` and the event's `updated_at` share one clock value (`_now()`). With `NOW()` in two statements, "Edited by …" and "Replaced by …" could show different minutes.
4. **The body is checked before the lock**, as `edit_ticket` does. So an empty note on a closed ticket answers 400, not 409.
5. **Where *Add note* sits:** after *Machine stopped* and before *Change severity*. The brief says "after the next move and before *Change severity*"; *Machine stopped* is the operator's urgent move on a defect, so I kept it next to the chain.
6. **The icon** is `fa-regular fa-comment`, in the style of *Schedule*'s calendar.
7. **The pencil sits in the author row**, at the right, so the label and time row stay as on every line.
8. **"Hide earlier text".** The *Show earlier text* button reads "Hide earlier text" while the list is open. The brief names only the first text.
9. **"Replaced by `<login>`, `<time>`"** under each earlier text. The brief says "with who replaced it and when" but gives no words.
10. **The hint is a `text-secondary` paragraph** above the field.
11. **The earlier texts are divs, not a nested list.** The e2e helper `timeline(page)` counts the Timeline card's `li` elements, one per event.
12. **A 409 with no field reloads the page**, as `MoveDialog` and `RegradeDialog` do. Then the buttons of a ticket closed meanwhile go away.
13. **The migration test** reuses `_fill_one_ticket` from `test_migration_v22.py` and checks the new table's columns, foreign key, index and utf8mb4 collation (Tamil text).
14. **`conftest.py`** empties `ticket_note_edits` at session start (it references `ticket_events`). The brief does not list this file.

## 5. Not done, deferred or assumed

- Nothing in the brief is left out.
- The docs the planner already did (Plan.MD § 3 and § 4.2, the CLAUDE.md spec map) were not touched.
- The browser keeps a typed note at 1000 characters (`maxlength`), so "Too long (max 1000)" comes only from the API (tested there).
- *Assumption:* "Edited by" shows the latest correction only; each earlier one is in *Show earlier text*.

## 6. Tests

Every run below passed (22-10-2026, after the last code change):

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | backend 2043 passed; frontend (vitest) 110 passed; tooling 42 + 68 passed |
| `npx vite build` (`frontend/`) | built, no errors |
| `tooling/run-e2e-tests.bat`, the **full** suite | **204 passed** (3 projects: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium), 188 s in lanes |

The full suite ran, not only the targeted specs, because S027 changes `FormModal.vue`: shared frontend code that every dialog uses (README § Manual checks; brief § 8 Acceptance, BS1-01). It included the new `tickets-notes.spec.js` and the changed `tickets-work.spec.js`.

The new backend tests: `test_tickets_core.py` `TestValidateNote` (8) and `TestTicketTimesWithNotes` (4); `test_ticket_work_api.py` `TestAddNote` (15 with parameters) and `TestEditNote` (9); `test_migration_v23.py` (2); `test_rbac.py` (the matrix and one more holders case).

## Manual checks

- [auto] **Important** — a technician presses *Add note* in the action bar; the cursor is in the field; a two-line note saved shows on the timeline as **Note**, the author and both lines (phone and desktop) — `frontend/e2e/tickets-notes.spec.js`::"S027: technician adds a two-line note from the action bar; the cursor starts in the field; the timeline shows it"
- [auto] **Important** — an engineer edits the note: the hint shows; after *Save changes* the note shows the new text and "Edited by …"; *Show earlier text* shows the old text — `frontend/e2e/tickets-notes.spec.js`::"S027: engineer corrects a note: the hint shows; then Edited by, and Show earlier text gives the old text"
- [auto] The Raised line shows the raise's *What is wrong?* text; the page has no *Description* card — `frontend/e2e/tickets-notes.spec.js`::"S027: the Raised line shows the raise's What is wrong? text, and the page has no Description card"
- [auto] *Save note* with an empty field → "Enter a note" under the field, in view; nothing is added — `frontend/e2e/tickets-notes.spec.js`::"S027: Save note with an empty field shows Enter a note under the field, in view; nothing is added"
- [auto] An operator adds a note and sees no pencil; a technician sees no pencil; nobody sees *Add note* or the pencil on a closed ticket — `frontend/e2e/tickets-notes.spec.js`::"S027: an operator adds a note and sees no pencil; a technician sees none either; on a closed ticket nobody adds or edits"

On a real device (plain, not important; appended as row 13 of `docs/steps/device-checks.md`):

- On a Samsung Galaxy, voice typing in the *Note* field, in English and in Tamil: the text lands in the field, saves, and the Tamil text shows on the timeline as spoken. Technician; plant Wi-Fi or mobile data; either place; on production, close the ticket as *Not a fault* afterwards.

## Fix rounds

### Round 1

The user chose to fix CR1-01 and CR1-03 only.

- **CR1-01 — Fixed.** In `frontend/src/views/TicketDetailView.vue` the *Show earlier text* / *Hide earlier text* button is now `btn btn-link px-0` (no `btn-sm`, no `p-0`). It keeps the link look and the normal button height; `px-0` keeps the text aligned with the note above it.
- **CR1-02 — Deferred by the user.** Not changed; the choice stays recorded in the review.
- **CR1-03 — Fixed.** In `backend/tests/test_ticket_work_api.py` the repeat test is now `test_a_ticket_that_came_back_as_a_repeat_accepts_a_note_and_its_edit`. After the note, an engineer edits it with `PUT …/notes/<id>` on the earlier ticket and the test expects 200 and the new text.
- **CR1-04 — Deferred by the user.** Not changed.

Tests run (22-10-2026): `tooling/run-tests.bat` green: backend 2043 passed, frontend 110 passed, tooling 42 + 68 passed. Targeted e2e `e2e/tickets-notes.spec.js` and `e2e/screens.spec.js` (the screen changed; no shared frontend code): 39 passed on the three projects. The e2e tests do not check the button size; the size is not re-checked on a phone by a test.
