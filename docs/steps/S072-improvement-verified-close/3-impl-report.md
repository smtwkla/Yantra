```
Step: S072 — States, timeline and the verified close
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S072 — implementation report

**Result:** the backend of R05.4 is built as the brief says, with amendment A1. All unit suites,
the build and the browser runs are green (numbers in § 7). One small departure: `close_error`
takes no `action` argument (§ 4, D-1). No question for the user.

## 1. What was built

- **The states.** An improvement now moves by itself: *Analysing* → *Actions open* (the root
  cause is set) → *Watching* (no countermeasure open and at least one done). A *Lesson* or
  *Spread* added during the watch does not end it; a *Correction*, *Corrective*, *Preventive* or
  *Design-out* does. *Ready to verify* is computed from the clock when the watch has ended. The
  closes are *closed_effective*, *closed_not_effective* and *dropped*.
- **The watch.** 90 days by default, 30–365 through S067's `PUT` (`watch_days`). The detail's
  `watch` gives the start, the end, whether it ended, and the figures: breakdowns, breakdowns with
  the same symptom and downtime in the watch against the same days before it, and every repeat.
- **The closes.** `POST …/verify/effective` (remark optional) and `POST …/verify/not-effective`
  (remark required; answers 201 with the follow-up's detail). Key `improvement:verify`.
- **Drop.** `POST …/drop` with a reason (`improvement:edit`); it cancels the open
  countermeasures, each with its own line.
- **Notes.** `POST …/notes` (`improvement:note`: operator and up, not IT admin).
- **The timeline.** Table `improvement_events`; every write of `improvements.py` writes its line
  in the same transaction (D8). The detail's `timeline` is newest first, with the computed
  *Watch ended* line.
- **Read-only.** Every write on a closed or dropped improvement answers 409 "This improvement is
  closed".
- **The ticket page** and the list show the display state.
- **Migration v39**: the ENUM, six columns, the unique key and the foreign key, the table, the
  backfill, the earned states, four CHECKs.
- **The state words** in `improvementLabels.js` (D13).
- **A1**: a removed countermeasure photo's item carries `improvement_open`; Settings › Removed
  documents disables *Restore* with "Closed improvements cannot be changed".

## 2. How it works

- **Pure core** (`improvements_core.py`): `working_state(stored, root_cause_set, actions)` decides
  the working state in the brief's four rules; `watch_start(actions)` takes the latest done time
  of a machine kind, else of any done one; `watch_until`, `display_state`, `close_error`;
  `validate_close(body, needed, field)` and `validate_note`; `validate_improvement` takes
  `watch_days` on an edit; `watch_figures` splits the machines' tickets at the watch's start and
  lists the repeats; the line builders `why_line`, `root_cause_line`, `action_line`,
  `with_watch_ended`; `ACTION_KIND_LABELS`, `WATCH_KINDS`, the event names and both keys.
- **The shell** (`improvements.py`):
  - `_add_event` inserts one line (`created_by` = the actor).
  - `_settle_state(cur, id, locked, root_cause_set)` runs after the root-cause write and after
    every countermeasure add, change, done and cancel: it reads the countermeasures' kind, state
    and done time (a plain read under (6b)), asks `working_state` and `watch_start`, and when
    they differ from the stored values writes `state` and `watch_from` with a plain `UPDATE` (no
    `updated_*`, D16) and a `state_changed` line when the state moved.
  - Every S067, S069 and S070 route writes its line (§ 5.6's table). An edit's line is
    `tickets_core.edit_lines` with display values (the leads' names, "90 days"); a change of a
    countermeasure the same with its kind word, owner name and DD-MM-YYYY due date.
  - The close routes lock (6b), check 404 then 403, then `close_error` from the locked row and
    `_now()` (D1); they close the row, set the links' `open_link` NULL and write the line. *Not
    effective* takes the `IM:` counter first (6), then (6b), and inserts the follow-up with the
    old title, problem, lead, watch length and tickets; the follow-up's lines are `started`
    ("Follow-up of IM-…") and one `ticket_linked` per ticket, through the same helper as a start
    (`_link_tickets`, BR1-05).
  - The drop locks the open countermeasures `FOR UPDATE` in one statement by id, cancels each
    with "Dropped with the improvement: <reason>" (cut to 500) and its line, then drops the row.
  - The detail computes `is_open` from the stored state before it shows the display state
    (BR1-03); it adds `watch`, `closed`, `follow_up_of`, `follow_up`, `timeline` and the four
    `can_*` flags. The figures take one query for the machines' tickets in the window and one
    for their events (`ticket_times` to `end`: now, or `closed_at`).
- **`tickets.py`**: `_IMPROVEMENT_LINKS` also selects `watch_from` and `watch_days`;
  `_improvement_fields` answers `improvements_core.display_state(…)`. The start rule still reads
  `open_link` only.
- **`documents.py` (A1)**: every branch of the removed-documents union gains
  `improvement_state` (NULL but in the countermeasure branch); `_removed_item` turns it into
  `improvement_open` for a countermeasure item.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | migration v39 |
| `backend/improvements_core.py` | the states, the watch, the closes, the figures, the lines, the two keys |
| `backend/improvements.py` | `_add_event`, `_settle_state`, the lines of every write, the four new routes, the detail's new fields, the list's display state, `_require_open` on the edit, LOCK ORDER note |
| `backend/tickets.py` | the ticket detail's `improvements[].state` is the display state |
| `backend/config_rbac.py` | `improvement:verify`, `improvement:note` in `PERMISSIONS` and `SITE_SCOPED` |
| `backend/documents.py` | A1: `improvement_open` on a countermeasure's removed item |
| `backend/equipment.py` | docstring: the improvements bullet of the global LOCK ORDER |
| `frontend/src/utils/improvementLabels.js` | the six new state words (D13) |
| `frontend/src/views/settings/RemovedDocuments.vue` | A1: *Restore* disabled for a closed improvement's photo |
| `backend/tests/test_migration_v39.py` | new: fresh schema, a v38 database with rows, the CHECKs, the follow-up key, the re-run |
| `backend/tests/test_improvements_core.py` | `TestStates` rewritten; new classes for § 8.2's core list |
| `backend/tests/test_improvement_close_api.py` | new: states, ready, the closes, the follow-up, drop, read-only, figures, database down |
| `backend/tests/test_improvement_timeline_api.py` | new: the line of every route, notes, order, *Watch ended* |
| `backend/tests/test_rbac.py` | `test_role_matrix` and a new `test_improvement_verify_and_note` |
| `backend/tests/test_documents_api.py` | A1: `test_the_removed_list_says_when_the_improvement_is_closed` |
| `backend/tests/conftest.py` | `improvement_events` first in `_TABLES` |
| `frontend/tests/improvementLabels.test.js` | the seven state words |
| `docs/schema.md`, `docs/schema.html`, `docs/Plan.MD`, `docs/Maintenance-Philosophy.md` | docs pass (§ 9) |

## 4. Decisions taken

- **D-1 (departure, small): `close_error(shown_state, until)` has no `action` argument.** The
  brief names `close_error(action, display_state, watch_until)`, but both closes refuse the same
  cells (§ 5.1's table), so the argument would be unused.
- **D-2: the `state_changed` line's `from_state` is the display state**, as the drop's line
  (§ 5.6). A *Corrective* added after the watch ended reads "Ready to verify → Actions open",
  which is what the team saw.
- **D-3: a change of `watch_from` alone writes no line.** It can only happen when the start moves
  without a state change (only lessons done, and a later lesson done); the done line shows it.
- **D-4: `watch_start` follows the brief's definition in the lessons-only case.** When only
  *Lesson* or *Spread* countermeasures are done, a later done one moves the watch's start. § 5.1
  defines `watch_start` so; "a Lesson done during the watch does not move it" holds whenever a
  machine kind is done.
- **D-5: `watch_days` is read only on an edit.** On a start it is ignored, as unknown fields are;
  S068's start dialog does not send it.
- **D-6: the edit now refuses a closed improvement (409).** S067's edit had no open check (every
  improvement was open); § 1 item 7 and § 8.2 *Read-only* require it.
- **D-7: line wording.** The countermeasure change's labels are "Kind", "What will be done",
  "Owner", "Due" (the dialog's field names). The add line's role word is the site role without
  `maint_` ("technician"). `why_removed` has `remark` NULL and the removed line in `earlier`.
- **D-8: helpers.** `_link_tickets` (start and follow-up, one shape), `_cancel` (cancel route and
  drop), `_close` (the three closes), `_names` (the people of an edit line), `_stamp` (now to the
  second). `_lock_for_analysis` now also returns the visible row (the root-cause line needs the
  old cause's code), and `_check_owner` returns the person (the add line needs the role).
- **D-9: the backfill's root-cause line has no "Other causes"** (§ 4.1's table, as written); the
  route's line has it.
- **D-10: the figures' order.** Machines and symptoms by code; repeats oldest first (the query's
  order).
- **D-11: A1 on screen.** The disabled *Restore* says "Closed improvements cannot be changed",
  as the closed ticket's "Closed tickets cannot be changed". The field is only on countermeasure
  items.

## 5. Stale brief check (§ 9)

Checked against S069–S071's code in the tree. No difference changes the design; the code was
followed where a detail differed.

| Brief says | Code now | Done |
|---|---|---|
| D8: every write of `improvements.py` writes its line | Routes: start, edit, add and remove ticket, add, edit and remove why, root cause, add, change, done and cancel countermeasure; the document routes are in `documents.py` | Every route writes its line; the documents write none (§ 5.6) |
| § 5.1 settle on the countermeasure routes | `mark_action_done` is keyed `improvement:read` (owner by data, S070) | Settles there too; no key change |
| § 1 item 7: `_require_open` on every write | S067's edit had none | Added (D-6) |
| § 5.7 not effective reads `title`, `problem`, `lead_id`, `equipment_id` from (6b) | `_LOCK_IMPROVEMENT` had no `serial`, `watch_days`, `watch_from` | Added the three |
| `IMPROVEMENT_OPEN_STATES`, `is_open` | One place each; `my_actions`, the list filter and the document lock functions use them | Widening covers them: a dropped improvement's countermeasures leave *Mine*, a closed one refuses photos |
| v39's FK and backfill columns on `improvement_actions` | v38 has `kind`, `state`, `done_text`, `done_at`, `done_by`, `cancel_reason`, `cancelled_at`, `cancelled_by` | Match |
| § 8.3: S069's and S070's tests that assert states | `test_improvement_whys_api.py`, `test_improvement_actions_api.py`: no improvement-state assertion; both monkeypatch `IMPROVEMENT_OPEN_STATES` to `()`, still valid | No change |
| § 8.4: e2e state assertions | `improvements.spec.js` asserts "Analysing" only in S068's tests (no root cause); S069's and S071's tests assert no state; `me.spec.js` none | No change |
| Line anchors | `_improvement_fields` at `tickets.py:438` (brief `:437`), `_IMPROVEMENT_LINKS` `:458` (`:457`) | Names were the anchors |
| The lock notes | improvements.py LOCK ORDER and equipment.py's improvements bullet | Both extended (§ 5.7) |

## 6. Not done, deferred or assumed

- No browser test is new (§ 8.4: the screens are S073's). A1's disabled *Restore* has no
  browser test; its backend field has a unit test.
- The SQL of the figures is not limited by the reader's units (S067 D8, as briefed).
- **Assumption (brief § 9):** v36–v39 reach production in one release; v39 has no
  `_PRECONDITIONS` entry.

## 7. Tests

Run name `s072c1`.

- **While coding** (targeted): `test_improvements_core.py` (233 green first), the four
  `test_migration_v36`–`v39` files (25), the S067/S069/S070 API files with `test_rbac.py`,
  `test_documents_api.py` and `test_auth.py` (574, unchanged tests green against the new shell),
  the two new API files (29), `improvementLabels.test.js` (36). One of my own new tests was wrong
  on the first run (it expected an open *Lesson* to give *Watching* from *Actions open*; the
  brief says it stays *Actions open*); the test was rewritten to change a *Lesson* into a
  *Design-out* during the watch.
- **Full unit suites, once** (`tooling/run-tests.bat`): backend **3774 passed**, frontend **322
  passed**, tooling **185 passed**; ALL SUITES PASSED.
- **Build**: `npx vite build` clean (the chunk-size warning was there before).
- **Browser, targeted** (Normal with spec files): `e2e/improvements.spec.js` (the improvement
  specs assert states), `e2e/me.spec.js` (*Mine*), `e2e/settings.spec.js` (A1's Removed
  documents), `e2e/screens.spec.js`: **48 passed, 1 skipped** (73 s).
- **Browser, whole suite at Normal, once**: **282 passed, 13 skipped** (164 s). The skips are
  the existing ones (no S072 test is skipped or new).

## Manual checks

None in this step (§ 8.5: S073 holds them). No row added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/schema.md`: the "migration v39" line; `improvements` (states, watch, close, follow-up
  columns and CHECKs), the new `improvement_events` row, `improvement_whys` and
  `improvement_tickets` notes; the Mermaid overview (the new table, `follow_up_of_id`, four
  links).
- `docs/schema.html` (by hand, no generator): the meta line (v39, 44 tables, 71 links); the
  Overview and Tickets tabs (the table, the six columns, four links, the tab's note).
- `docs/Plan.MD`: § 3 key table rows `improvement:verify` and `improvement:note` and a paragraph;
  § 4.2 the paragraph on the states, the timeline and the verified close; the countermeasure
  paragraph's "until R05.4 brings undo" corrected (no undo, § 9 Q2).
- `docs/Maintenance-Philosophy.md` § 12: *Watch period* and *Verified close*.
- `.claude/CLAUDE.md`: not edited (the orchestrator's rule); the text is under § Proposed
  CLAUDE.md changes.

## Proposed CLAUDE.md changes

In `## SMTW-Review`, after the *Meter readings (S039)* bullet, add:

```
- **Improvement timeline (S072)**: every write of `improvements.py` writes its timeline line (`_add_event`, table `improvement_events`) in the same transaction as the change, after it, under the improvement's lock (6b); the routes that change the root cause or a countermeasure also call `_settle_state`. A new write route without its line leaves the history incomplete (ISO 9001 § 7.5.3). `is_open` takes the stored state only; the display state (`ready_to_verify`) is for output.
```

In `## Step workflow`, *Browser tests*, no change. In `## SMTW-Review`, the spec-to-step map:
no new spec file in this step.

## Feedback

- hindrance: two Bash calls broke § Shell on Windows (a heredoc and a bare `cat >`); the second
  waited on stdin for 2 minutes until stopped (`cat > "$TMP/x.py"`, 1 run, 2 min).
- idea: `docs/schema.html` has no generator, and its tabs are one JSON line; a small
  `tooling/` script that adds a table or columns to a tab would make each migration's docs pass
  shorter (this step: a one-off patch script in `scratch/`).
- waste: the brief's § 3 line anchors (`tickets.py:437`, `:457`) had moved by one line; the
  names were enough, so the anchors cost a grep each and gave nothing (2 greps).

## Fix rounds

### Round 1

Source: `4-code-review-r1.md` (1 minor, 4 nits). The round also fixes S071's CR2-01 (answered in
S071's report, `### Round 2 (in S072's fix round)`). Run name `s072f1`.

- **CR1-01 Fixed.** *Not effective* now reads the old links with `SELECT ticket_id FROM
  improvement_tickets WHERE improvement_id = %s ORDER BY ticket_id FOR UPDATE`, after (6b), with a
  code comment that gives the reason. The LOCK ORDER note's *Not effective* line now says: the old
  links by a locking read, because the counter's SELECT fixed the snapshot.
  - **Lock order:** no new edge. Every write of `improvement_tickets` (add, remove, start, the
    closes) takes (6b) first, and `_close`'s UPDATE already locks these same rows. `tickets.py`
    reads the links plain (its LOCK ORDER note), and `equipment.py` and `documents.py` never touch
    the table. The order stays (6) → (6b) → the link rows → (7) shared.
  - **Test:** `test_improvement_close_api.py::TestNotEffective::test_a_link_committed_while_it_waited_goes_to_the_follow_up`.
    It wraps `improvements.next_counter`: right after the real counter, a second connection
    (`db_rows`, autocommit) commits a link of a new ticket. That plays an add that held (6b) while
    the close waited. Fails without the fix: `assert [1] == [1, 2]` (the follow-up has only the
    first ticket); passes with it.
- **CR1-02 Fixed.** The database-down test now posts the note as `operator_at_site` (a holder of
  `improvement:note`) on a real improvement, made by a class fixture before `db_down` applies.
  No red run: the test proves code that already answers 503; a red run would need the route's
  `get_db()` broken on purpose.
- **CR1-03 Fixed.** The drop test now has three countermeasures: two open (corrective, lesson) and
  one done (preventive). It asserts that both open ones are cancelled with the drop reason, that
  their two `action_cancelled` lines come in id order ((6c) by id), and that the done one is
  unchanged apart from its `can_*` flags (they follow the closed improvement). No red run: the
  test covers code that is already right, so there is no fix to undo.
- **CR1-04 Fixed.** `mark_action_done` uses `_stamp()`. No test change: the value is the same.
- **CR1-05 Fixed.** The header comment of `RemovedDocuments.vue` now says that *Restore* is also
  disabled when the countermeasure's improvement is closed or dropped (S072 A1), as on a closed
  ticket.

**Runs (targeted):**
- Backend (`YANTRA_TEST_RUN=s072f1`): `test_improvement_close_api.py`,
  `test_improvement_actions_api.py`, `test_improvement_timeline_api.py`,
  `test_improvements_api.py`: **146 passed**.
- `npx vite build`: clean (the chunk-size warning was there before).
- Browser: the new S071 test alone on `phone-chromium` (red, then green, see S071's report); then
  `tooling/run-e2e-tests.bat e2e/improvements.spec.js e2e/settings.spec.js` (the changed screen,
  and Settings for the Removed documents comment): **22 passed**.

**Files touched (4 + S071's 2):** `backend/improvements.py` (the locking read, the LOCK ORDER
line, `_stamp()`), `backend/tests/test_improvement_close_api.py` (CR1-01 test, CR1-02, CR1-03),
`frontend/src/views/settings/RemovedDocuments.vue` (comment), this report. For S071's CR2-01:
`frontend/src/views/ImprovementDetailView.vue`, `frontend/e2e/improvements.spec.js`, and S071's
report.

### Docs updated (Round 1)

none, because the round changes no behaviour a doc describes. The lock note is in the code
(`improvements.py` LOCK ORDER).

### Feedback (Round 1)

- idea: the S067 "hide a step" pattern was not needed here; wrapping `next_counter` and
  committing on a `db_rows` connection made a real snapshot race in one test (1 run red, 1 green).
  A shared `commit_meanwhile(module, fn, sql)` fixture could serve the next lock review.
- hindrance: `-k late_link` selected nothing because the test name differs from its helper's
  name; the wrapper exited 5 (1 run, under 1 min).
