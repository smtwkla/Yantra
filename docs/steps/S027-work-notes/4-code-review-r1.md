```
Step: S027 — Work notes
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S027 — Code review r1

**Verdict: no blocker or major finding is open.** 1 minor, 3 nit. Every suite is green, and the full e2e suite passes on the three projects.

Scope: the 17 files of the impl report, plus `FormModal.vue` where S027 meets S026. S026's own changes in the working tree are not reviewed here.

## Test results (run by the reviewer, 22-10-2026)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | backend **2043 passed**; frontend (vitest) **110 passed** (13 files); tooling **42 + 68 passed**. Exit 0. |
| `npx vite build` (`frontend/`) | built in 3.7 s, no errors |
| `tooling/run-e2e-tests.bat`, the **full** suite, in lanes | **204 passed** (Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium), 195 s. Exit 0. |

Why the full suite: S027 changes `FormModal.vue`, which is shared frontend code (README § Manual checks; brief § 8 Acceptance, BS1-01). It includes the new `tickets-notes.spec.js` and the changed `tickets-work.spec.js`.

## Findings

### CR1-01 — minor — the *Show earlier text* button is a shrunk tap target

- **Where:** `frontend/src/views/TicketDetailView.vue:446`.
- **Problem:** the button is `btn btn-link btn-sm p-0`. The ticket page is a floor screen. The UX checklist says tap targets are not shrunk with `btn-sm`. With `p-0` the target is only as tall as one small line of text.
- **Failure scenario:** an engineer on a phone checks what a note said before a correction. The thumb hits the note text or the *Edit note* pencil above it, not the link. The pencil opens the edit dialog by mistake.
- **Fix:** drop `btn-sm` and `p-0` (for example `btn btn-link px-0`), so the button has the normal height. The pencil already follows this rule (a full-size `btn btn-outline-secondary`).

### CR1-02 — nit — a note written just after a move stamped ahead of the clock shows above that move

- **Where:** `backend/tickets.py:1208` (`_add_event(cur, ticket_id, NOTE_EVENT, _now(), …)`).
- **Problem:** a move with an entered time may lie up to `FUTURE_SKEW` (5 minutes) ahead of the server clock, and a later move without a time is stamped at `max(now, last)`. A note is always stamped at `_now()`. The timeline sorts by `occurred_at, id`.
- **Failure scenario:** a technician's phone clock is 3 minutes fast. The technician records *Back in service* at 10:33 by the phone, then writes "Tightened the belt" at 10:30 server time. The note shows above *Back in service*, although it was written after it.
- **Fix:** none needed now; the brief (§ 7.2) wants the time the note was written. If the user wants the written order kept, stamp the note at `max(_now(), last event's occurred_at)`. Recorded so the choice is visible.

### CR1-03 — nit — the edit of a note on a ticket that came back as a repeat is not tested

- **Where:** `backend/tests/test_ticket_work_api.py:1294`.
- **Problem:** brief § 5.1 says a ticket that came back as a repeat "accepts notes and edits". The test covers the note only. § 8 lists only the note, so the test meets § 8, but not the whole rule.
- **Failure scenario:** a later change adds a repeat check to the shared lock path (as S025 did for Send back). The edit route then refuses a correction on the earlier ticket, and no test fails.
- **Fix:** in the same test, edit the note through `PUT …/notes/<id>` as admin and expect 200.

### CR1-04 — nit — the impl report calls every decision "small, forced"

- **Where:** `docs/steps/S027-work-notes/3-impl-report.md:78`.
- **Problem:** the line says "These are small, forced choices the brief does not cover". Decisions 5 to 10 are judgement calls, not forced moves. Decision 1 departs from § 6's words ("the detail gains no other field"). Scope A rule 7 asks to label each item.
- **Fix:** write, for example: "Decisions the brief does not cover. 1 and 5 depart from its words; 3, 4 and 12 follow existing code; the rest are wording and layout."

## The departures in "Decisions taken"

Each departure is reported, and each is sound:

| # | Decision | Judgement |
|---|---|---|
| 1 | Every event carries `id` | Accepted. The PUT needs the event id, and `_event_rows` is the one reader. The field is on the events, not a new detail field. |
| 3 | Hand-written insert and update for `ticket_note_edits` | Accepted. `insert_row` adds `created_by`, and the brief's table has `replaced_by`. `update_row` stamps `NOW()`, so "Edited by" and "Replaced by" could differ. One `_now()` value for both rows is right, and a test checks `replaced_at == updated_at`. |
| 4 | The body is checked before the lock (an empty note on a closed ticket is 400) | Accepted. `edit_ticket` does the same. The 409 still comes from the locked row for every valid body. |
| 5 | *Add note* after *Machine stopped* | Accepted. *Machine stopped* already sits between the chain moves and *Change severity*, so "after the next move, before *Change severity*" is met. The style matches *Schedule* (`btn-outline-primary btn-lg`). |
| 8, 9 | "Hide earlier text"; "Replaced by `<login>`, `<time>`" | Accepted. Both follow scope B: a verb first, plain words, the same "by `<login>`, `<time>`" form as "Edited by". |
| 11 | The earlier texts as `div`s | Accepted. The timeline counts its `li` elements, one per event. |
| 12 | A 409 with no field reloads the page | Accepted. The same watch as `MoveDialog` and `RegradeDialog`; the buttons of a ticket closed meanwhile go away. |
| 14 | `conftest.py` empties `ticket_note_edits` | Accepted. Forced by the new foreign key to `ticket_events`; it sits before `ticket_events` in the list. |

## Checked and found consistent

- **RBAC.**
  - `ticket:edit_notes` is `("maint_engineer", "it_admin")`, so the manager inherits it; it is in `SITE_SCOPED`. `config_rbac.py` stays the one source.
  - `add_note` is `@require_perm(RESTORE_KEY)`, `edit_note` is `@require_perm(EDIT_NOTES_KEY)`. Both then call `_lock_open_ticket` with the same key, so the key is checked at the ticket's site on the locked row: 404, then 403, then 409.
  - No role name is in route code. The actor comes from `actor()` (the token), never from the body.
  - Tests cover: technician 403 on edit (own note too), technician here and engineer elsewhere 403, the role at each ticket's site decides, IT admin 200, operator at another site 403, outside the units 404, storekeeper 403, and `permissions` holding the key only where it applies.
- **No 403 behind a button.** `canAddNote` follows `ticket:restore` in the detail's `permissions` and the open state; `canEditNotes` follows `ticket:edit_notes`. The e2e test checks the operator and the technician see no pencil, and nobody sees *Add note* or the pencil on a closed ticket.
- **Locks.** Add: the ticket row `FOR UPDATE`, then the insert (its foreign keys lock the held ticket row; `person_id` is `NULL`). Edit: the ticket row, then the note's event row `FOR UPDATE` by `id`, `ticket_id` and `event = 'note'`, then the `ticket_note_edits` insert (its foreign key needs the held event row). No other code locks an event row. The LOCK ORDER note in the `tickets.py` docstring says this.
- **A note moves nothing.** `NOTE_EVENT` is not in `ORDERED_EVENTS`. `ticket_times` skips any event outside `ORDERED_EVENTS`; `_last_ordered_event` filters on them; `latest_restoration` reads only `back_in_service`. Tests prove the figures are equal with and without notes in four event sequences, the times and state stay unchanged through the API, and a move may be entered before a later note.
- **The earlier-texts query** (`_note_edits`) runs only in `_detail`, in one query for the ticket. The repeat checks still call `_event_rows` alone (BR1-11). Only notes carry `earlier`, and a test checks that.
- **Migration v23.** `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`, so a half-applied v23 re-runs. No precondition is needed: both columns are `NULL`able and the table is new. The comment block gives the step and that reason. `test_migration_v23.py` starts from a v22 database with a ticket and two events, checks every existing row is unchanged with `updated_*` `NULL`, checks the table's columns, foreign key, index and utf8mb4 collation, and re-runs v23 with no schema change. v20–v22 are not touched.
- **Validation.** `validate_note` reuses `_optional_text`, so the messages match a move's remark; then "Enter a note" for missing, `null`, empty or blank. Line breaks inside are kept, the ends trimmed. The same text after trimming is 400 "Nothing to change" on `remark`.
- **SQL.** Every statement is parameterised. No SQL is built from client input.
- **DB unavailable.** Both routes go through `get_db()`, so a dead or missing DB answers 503 as every route.
- **FormModal focus and S026.** The `shown.bs.modal` listener is added in `onMounted` with `addEventListener`, as `hide.bs.modal`. Bootstrap's focus trap focuses the modal and fires `shown.bs.modal` in the same task, so the field holds the focus when the e2e `openDialog` wait sees focus inside the modal: no race. `revealError` runs only on a refusal. Only `NoteDialog.vue` has an `autofocus` field (grep), so the other dialogs are unchanged. The full suite confirms it.
- **The note dialog.** The field is marked `is-invalid` and its message `invalid-feedback d-block`, so S026 scrolls a refusal into view; the e2e test checks "Enter a note" is in the viewport and the field has the focus. `dirty` comes from `useFormModal`, so Cancel with typed text asks "Discard your changes?". The body scrolls and the footer stays (`modal-dialog-scrollable`, from `FormModal`). `expectDialogFits` runs on every dialog the spec opens.
- **The timeline.** A note shows the label **Note**, the time, the login name, then the text in normal size with `pre-wrap`. The Raised line shows the description in the same style, and the *Description* card is gone. A move's remark stays small. "Edited by `<login>`, `<DD-MM-YYYY HH:MM>`" and the earlier texts, newest first, show as the brief says. The pencil is a full-size button with `title` and `aria-label` "Edit note".
- **Screen text (scope B).** "Add note", "Save note", "Save changes", "Cancel", "Edit note", the hint, "Enter a note", "Too long (max 1000)", "Nothing to change", "This ticket is closed": short, plain, buttons start with a verb, no blame.
- **E2E tests assert what the user sees.** Each of the five § 8 *Automated* checks has a test that reads the screen: the focus, both lines of the note via `innerText`, the label and the author, the hint, the new text, "Edited by", the old text and "Replaced by", the Raised line text and no *Description* card, the message in view and no added line, and the missing buttons. Each `[auto]` row of the report's `## Manual checks` has a passing run behind it.
- **The changed test in `tickets-work.spec.js`** reads the edited description on the Raised line, not the removed card. No other spec referred to the *Description* card (grep).
- **Manual checks.** The report's `## Manual checks` carries both **Important** checks as `[auto]` with their tests, and the device check as row 13 of `docs/steps/device-checks.md`, in plain words with account, network and place.
- **Scope.** Everything in § 1 and § 3 is built. Nothing beyond the brief is built. The planner's docs (`Plan.MD` § 3 and § 4.2, the `.claude/CLAUDE.md` spec map with `tickets-notes` S027) are in place.
- **Layers.** The rules (`validate_note`, `NOTE_EVENT` outside `ORDERED_EVENTS`) are in `tickets_core.py`; the routes are a thin shell; the Vue files only show what the detail sends and follow its `permissions`.
- **Reuse.** `_lock_open_ticket`, `_add_event`, `_ticket_response`, `clean_body`, `_optional_text`, `NOTHING_TO_CHANGE` and `TICKET_CLOSED` are reused. `NoteDialog.vue` follows `MoveDialog.vue`'s pattern on `useFormModal`.

## Manual browser checks for the user

1. Row 13 of `docs/steps/device-checks.md`: voice typing in English and Tamil on a Samsung Galaxy.
2. Suggested, while doing row 13: say whether the keyboard opens by itself when the *Add note* dialog opens. The focus moves at the end of the open fade, outside the tap, and some phones (iPhone in particular) then show the cursor without the keyboard. The e2e tests prove only that the field has the focus.
