```
Step: S070 — Countermeasures
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S070 — Countermeasures: implementation report

The backend of countermeasures is built as the brief says. Migration v38 adds the table and a
fourth owner in the documents store. The six routes of § 6 work, and the improvement detail has
three new fields. All unit suites are green. The browser runs are listed in § Tests. Nothing
departs from the brief's design. The decisions I had to take are listed under § 4.

## 1. What was built

- **Migration v38** (`improvement_actions`; `equipment_documents.action_id` with its key, its
  foreign key and the owner CHECK widened to four owners), word for word as § 4.1.
- **The pure rules** in `improvements_core.py`: the six kinds, the three states, the bounds and
  the messages, and `validate_action`, `validate_done`, `validate_cancel`, `due_date_error`,
  `done_time_error`, `overdue_days`, `action_counts`, `action_flags`, plus `action_state_error`
  (the § 5.5 table; see Decisions).
- **The routes** under `/api/improvements` (§ 6):
  - `POST /<id>/actions` (add), `PUT /<id>/actions/<action_id>` (change),
    `POST /<id>/actions/<action_id>/done` (mark done), `POST /<id>/actions/<action_id>/cancel`;
  - `GET /actions/mine` (the user's open countermeasures, for *Me › Open work*);
  - `GET /owners?improvement_id=` (the owner choices).
- **The detail** (`GET /api/improvements/<id>`) gains `actions`, `action_counts` and `problem_at`.
- **The documents store's fourth owner**, the countermeasure: list, upload, file, thumb, retitle,
  remove, restore and purge at `/api/improvements/actions/<action_id>/documents…`; files in
  `DATA_DIR/improvement-actions/<action_id>/`; a fourth branch in the removed-documents list.

## 2. How it works

- **Add.** The route locks the improvement (6b). Then it makes plain reads in the order of § 5.1:
  the predicate (404), `improvement:edit` at the site (403), the improvement open (409), the count
  of 30 (409), the owner (400), and the due date against the problem's date (400). Then it inserts
  the row and answers the detail.
- **Change, mark done, cancel.** Each route locks the improvement (6b), then the countermeasure
  (6c, `_lock_action`, 404 when it belongs to another improvement). Then it checks the predicate,
  the right, the open improvement and the countermeasure's own state (from the locked row).
  - Change writes only the fields that differ. It checks the owner and the due date only when
    they change, so an owner who has left the site stays until someone picks another.
  - Mark done takes the right **by data**: `improvement:edit` at the site, or the user's own
    Team record is the owner (`_require_owner_or_editor`); else 403 "Only the owner, or an
    engineer or manager of this site, can do this". With no `done_at`, the server's IST clock
    is the time. It writes `done_text`, `done_at`, `done_by` and leaves `updated_*` alone (D8).
  - Cancel writes the reason, the time and who; the row stays.
- **The problem's time** (`_problem_at`) is the earliest linked ticket's `occurred_at`. It is the
  floor of the due date and of the done time. Writes read it under (6b), so the links cannot
  change meanwhile.
- **The detail's `actions`** come from three queries for any number of countermeasures: the rows
  with the names, the owners' memberships at the site (`may_own`), and the documents. Each item
  carries `overdue_days` and the three flags from `action_flags`.
- **Mine** joins the countermeasure to its improvement, machine and unit, filters by the owner,
  the open states and the improvement predicate, and sorts by due date (limit 200, with `total`).
  A user with no Team record gets an empty list.
- **Owners** answers every active person with a membership at the improvement's site, any role,
  by name, as `{id, name}`.
- **The documents owner.** `OWNERS["action"]` names `improvement:read` as the write key (D4), so
  a technician owner passes `_owner_key`. The four functions in `improvements.py` then apply the
  narrow rule at the improvement's site. They branch on the key that `documents.py` passes:
  - the write key: the owner, or `improvement:edit` at the site, else 403;
  - the purge key (restore and purge): `equipment:purge_documents` at the site.
  `lock_action_for_change` reads the countermeasure's `improvement_id` with a plain read, locks
  (6b) then (6c), and decides 404, 403 and 409 (closed improvement, cancelled countermeasure) from
  the locked rows. `lock_action_for_purge` makes no state check.
- **The removed list** has a fourth UNION branch, scoped by the improvement's unit to the units
  where the purge key is held. Its `name` is the improvement's serial, `state` the
  countermeasure's state, and `action_kind` its kind. The shared alias `ticket_state` is now
  `owner_state` in every branch; the item key stays `state`.

## 3. Files touched

Code (6):

- `backend/local_db.py`: migration v38 with its comment.
- `backend/improvements_core.py`: the countermeasure constants, messages and pure functions.
- `backend/improvements.py`: the detail's new fields and their reads, the six routes, the four
  documents-owner functions, and the module docstring (scope, LOCK ORDER, no-cycle notes).
- `backend/documents.py`: `OWNERS["action"]`, `_ACTION_DOCS` / `_FOR_ACTION` stacked on all eight
  routes, the fourth removed branch, `owner_state` and `action_kind`, and the docstring (owners,
  locks, purge).
- `backend/file_store.py`: `_OWNER_FOLDERS["action"] = "improvement-actions"` and its docstring.
- `backend/equipment.py`: docstring only: (6c) in the global LOCK ORDER, and the documents.py
  bullet.

Tests (5):

- `backend/tests/test_migration_v38.py` (new, 6 tests): a fresh database, a v37 database with
  documents of all three owners, the CHECKs, the four-owner CHECK, a re-run, a half-applied v38.
- `backend/tests/test_improvements_core.py`: 76 new cases (§ 8.2's core list).
- `backend/tests/test_improvement_actions_api.py` (new, 43 tests): every route of § 6 and the
  detail's new fields.
- `backend/tests/test_documents_api.py`: `TestActionDocuments` (9 tests) and the CHECK case with
  `ticket_id` and `action_id`.
- `backend/tests/conftest.py`: `improvement_actions` in `_TABLES`.

Docs (4): see § Docs updated.

## 4. Decisions taken

None departs from the brief's design.

1. **`action_state_error(operation, state)` in the core**, with the table `_STATE_REFUSALS`. The
   brief lists the 409 messages in § 5.5 but names no function for them. A table in the pure
   core keeps the rule out of the shell and is tested case by case.
2. **`_lock_for_actions`, not S069's `_lock_for_analysis`.** S069's helper also checks
   `improvement:edit`, which mark done must not do (the owner holds only `improvement:read`).
   The new helper takes only the locks; each route then makes its checks in § 5.1's order.
3. **The owner rule's 403 is a plain `ApiError`**, not `require_perm_at`. No key is missing, so
   there is no key to name. The access log classifies a bare 403 as `denied_perm` with the
   message (network_core.classify_outcome).
4. **The done and cancel times come from `_now()` (IST, seconds kept, microseconds dropped)**,
   not SQL `NOW()`. The done time must be the same value that `done_time_error` checked. The
   session time zone is +05:30, so both clocks agree.
5. **A missing `due_date` on an add says "Enter the date as YYYY-MM-DD"**: the brief gives one
   message for the field.
6. **`owner.may_own` is "active and a member of the site"**, the same test as `person_at_site`,
   so a flag of false means the add or change of that owner would be refused.
7. **`problem_at` in the detail** is one more query (`_problem_at`), shared with the writes, and
   formatted as every other time (`row_to_dict`).
8. **`read_action`** returns the countermeasure's row with its improvement's `site_id` and
   state, so `read_action_for_change` needs no second read.
9. **Tests:** the API tests move the ticket two days back (`db_rows`), so a due date in the past
   and a done time an hour ago are tried by the API itself; the overdue test then adds a
   countermeasure due two days ago through the API instead of moving its `due_date` with
   `db_rows` (§ 8.2 allows either).

### Stale brief check

The brief was written before S069's code. I compared every name, route and line it cites with
the tree. All names exist and mean what the brief says. Only line numbers moved:

| Brief cites | In the tree (before S070's edits) |
|---|---|
| `improvements_core._text` `:60`, `_is_id` `:56` | `:87`, `:83` |
| `improvements._read_improvement` `:139`, `_check_improvement` `:152`, `_lock_improvement` `:160`, `_require_open` `:169`, `_detail_response` `:264` | `:166`, `:179`, `:187`, `:196`, `:324` |
| `tickets.person_at_site` `:365`, `people_at_site` `:742`, `_today` `:181` | `:366`, `:743`, `:182` |
| `documents._JOIN_COLUMNS` `:468` | `:467` |
| `equipment.py` documents bullet `:50-53` | `:52-55` |
| `local_db.py` v37 | at `:1148`, as S069 added it |

- **Fact:** S069 added `_lock_for_analysis` (lock, key, open). It does not fit mark done
  (Decision 2).
- **Fact:** every other cited line (`documents.OWNERS :161`, `_owner_key :183`,
  `_removed_branches :491`, nosniff `:366-369`, `file_store._OWNER_FOLDERS :23`, the
  `tickets_core` constants, `auth_utils :314`, `:439`, `conftest :162`, `:213`,
  `test_documents_api :487`, `Plan.MD :201`) matches.
- No difference changes the design.

## 5. Not done, deferred or assumed

- **Screens** are S071's, as the brief says. Until then the frontend's removed-documents card
  receives rows with `owner: "action"` that it has no label for (S071 § 5.8 adds it). Nobody can
  make such a row through the screens before S071.
- **No new browser test** (§ 8.4: none in this step).
- **`test_migration_v12.py::test_the_owner_check_keeps_its_name_and_counts_three_owners`** is
  left as it is (frozen history; it stays green, as § 8.3 says).
- **Assumption:** a removed photo of a countermeasure of a *closed* improvement can still be
  erased for good (lock_for_purge makes no state check, as for every owner).

## Tests

- **Unit suites, the final full run** (`YANTRA_TEST_RUN=s070c1 tooling/run-tests.bat`): backend
  3665 passed, frontend 309 passed, tooling 185 passed. All suites passed.
- **Browser, targeted** (Normal with spec files): `e2e/equipment.spec.js`, `e2e/settings.spec.js`
  (the removed-documents card), `e2e/improvements.spec.js` (the improvement detail that gained
  fields), `e2e/tickets-raise.spec.js` (ticket photos, the third owner) and `e2e/screens.spec.js`:
  99 passed, 2 skipped (the existing skips), 110 s.
- **Browser, the whole suite at Normal** (`tooling/run-e2e-tests.bat`, once, at the end): 275
  passed, 13 skipped (the existing skips), 163 s.

## Manual checks

None in this step (§ 8.4 and § 8.5): no screen changes and no real-device check. S071 holds the
browser tests and the camera check.

## Docs updated

- `docs/schema.md`: the `improvement_actions` row, `equipment_documents` with `action_id`, its
  key and the four-owner CHECK, the Mermaid overview (two tables' fields and three links), and
  the line "migration v38".
- `docs/schema.html`: by hand (no generator): the Overview, Equipment and Tickets tabs (the table
  in full on Tickets, `action_id` on `equipment_documents`, the three links), the Tickets tab's
  note, and the header (migration v38, 43 tables, 67 links).
- `docs/Plan.MD`: § 3, a paragraph beside `pm_job:work`'s: who marks a countermeasure done is
  decided by data (the owner). § 4.2, after the improvement bullet: the countermeasures in short,
  and "until R05.4 a wrong *done* stays and the engineer adds a new countermeasure".
- `docs/Maintenance-Philosophy.md` § 12 Glossary: the row *Countermeasure* with its six kinds.
- `.claude/CLAUDE.md`: not edited (the orchestrator's instruction); the text is below.

## Proposed CLAUDE.md changes

1. § Step workflow, entry *Self-check, repo items*, item (2). Replace

   > (2) The lock notes: the LOCK ORDER notes in `tickets.py` and `masters.py`; the database runs REPEATABLE READ, so a plain read made after an earlier plain read sees the old snapshot.

   with

   > (2) The lock notes: the LOCK ORDER notes in `tickets.py`, `masters.py` and `improvements.py` (S070: (6c) the countermeasure row, always after its improvement (6b)); the database runs REPEATABLE READ, so a plain read made after an earlier plain read sees the old snapshot.

2. § Yantra Specifics, *Files (S006)*. After "Served only through permission-checked routes, never as static files." add

   > Four owners (`documents.OWNERS`, `file_store._OWNER_FOLDERS`): a node (`equipment/`), a model (`equipment-models/`), a ticket (`tickets/`) and, since S070, a countermeasure (`improvement-actions/<id>/`; read through its improvement's predicate, written by its owner or by `improvement:edit` at the site, restored and erased by `equipment:purge_documents` there).

## Fix rounds

### Round 1

Answers to `4-code-review-r1.md` (2 minor, 3 nits).

- **CR1-01 Fixed.** `ACTIONS_FULL` now reads "An improvement holds up to 30 countermeasures. Change an
  open one instead." The rule is unchanged (cancelled rows still count). Core test and
  `test_improvement_actions_api.py` (the 31st is 409) updated.
- **CR1-02 Fixed.** `documents.py` has one helper `_scoped_branch(...)`; `_removed_branches` loops
  over the node, ticket and countermeasure branches with it. The model branch stays as it was.
  Behaviour-neutral: `test_documents_api.py` (removed-documents tests) passes.
- **CR1-03 Fixed.** `done_time_error` compares with the problem time cut to the minute, the minute
  the message shows. Test `test_done_time_in_the_minute_of_a_problem_with_seconds_passes`: fails
  without the fix ("Not before the problem happened, 28-10-2026 15:15" for a done time in the same
  minute); passes with it.
- **CR1-04 Deferred** to S072, as its amendment A1 (orchestrator): the removed item carries the
  improvement's state too. No code here.
- **CR1-05 Fixed.** The `app.py` comment names four owners and the countermeasure documents route.

Runs: backend (`YANTRA_TEST_RUN=s070f1`) test_improvements_core, test_improvement_actions_api,
test_documents_api, test_improvements_api, test_improvement_whys_api, test_migration_v38: 390
passed. `npx vite build` ok. Browser: `e2e/improvements.spec.js`, `settings.spec.js`,
`screens.spec.js`: 33 passed, 1 skipped.

Docs updated: none, because the round changes no documented behaviour beyond a message text.

## Feedback (Round 1)

- none

## Feedback

- hindrance: a heredoc that appended the core tests failed on an apostrophe in a test string
  (`unexpected EOF while looking for matching '`), as README § Shell warns; I lost one run and
  redid it with the Edit tool (1 run, 1 min).
- waste: the orchestrator asked for a targeted browser run and then the whole Normal run, in a
  step with no frontend change and no new browser test; the whole run covers every targeted spec
  (110 s spent on a run that the next one repeats).
- idea: `docs/schema.html` keeps all tabs on one JSON line, so a hand edit needs a script that
  parses the JSON and checks a clean round-trip; a small shared tool in `tooling/` (add a table
  or column to named tabs) would save each migration step that work (one script written, ~5 min).
