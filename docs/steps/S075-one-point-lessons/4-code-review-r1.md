```
Step: S075 — One-point lessons
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S075 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The backend matches the brief. The security,
lock and permission paths hold. Two nits.

**Test run (s075cr1):** `YANTRA_TEST_RUN=s075cr1 tooling/run-tests.bat`: backend 3982 passed, frontend
346 passed, tooling 185 passed (all PASSED). No frontend file changed, so no build check. No browser
re-run: no finding of mine needs one.

**Reviewed:** `step_snapshot.py diff S075` (parent: the S074 snapshot). I read in full
`procedures.py`, `procedures_core.py`, `test_migration_v41.py`, and the documents, improvements,
local_db, config_rbac, file_store, equipment and app hunks. I also read the surrounding
`documents.py` routes (list, upload, serve, title, remove, removed list, restore), `load_node_for_user`,
`NODE_JOINS`, `_visible_condition`, `next_counter`, `update_row`, `require_perm_at`, and the test
classes the report names. The S074 files and `INDEX.md` in the diff are the orchestrator's, not the
coder's.

## Nits

- **CR1-01** (nit) `backend/procedures.py:32` and `:287`: the note says the "lesson already linked"
  plain read is a decision guarded by a lock, but under REPEATABLE READ its snapshot comes from
  `load_node_for_user`. That read runs before the wait on (6) and (6c). So a double tap waits on
  `OPL`, misses the first lesson, and meets `uq_procedures_action`: the user gets the 409 "This
  countermeasure already has a lesson", without the serial. The result is still correct. Fix the
  note: say the unique key is the guard and the plain read only gives the message with the serial.
- **CR1-02** (nit) `backend/tests/test_documents_api.py` `TestLessonDocuments`: no test covers the
  403 branch of the lesson's documents path. That case is an engineer here who is an operator at the
  machine lesson's site: they see the lesson but hold no key there. Add an upload that is refused with
  403 naming the site, and assert `owner_files` stays empty. This pins
  `read_procedure_for_change`'s refusal before any file is written.

## Checked and found consistent

- **Migration v41** (`local_db.py`): word for word as brief § 4.1. Every statement is safe to re-run.
  The CHECK is dropped and added again under its name. There is no precondition, by v38's reasoning.
  `test_migration_v41.py` covers each § 8.1 case: a fresh database; a v40 database with documents of
  all four owners; the five-owner CHECK (4025); `uq_procedures_action` (1062, NULLs repeat); Tamil
  text at 80 and 1000; a re-run; a half-applied run.
- **Schema docs**: `docs/schema.md` has the `procedures` row, the five-owner
  `equipment_documents` row with its new index, the `OPL` counter scope, the Mermaid entity with its
  four links, and the "migration v41" line. `procedure_items` and `procedure_completions` stay in
  § Planned. `docs/schema.html` has the "Migration v41" header, the `procedures` entity and the
  `procedure_id` links.
- **Other docs**: Plan.MD § 3 (key row and paragraph) and § 4.3a (*Built in part*, with the
  departures), and Maintenance-Philosophy § 3 and § 12, are updated as § 3 asks.
  `.claude/CLAUDE.md` is left to the orchestrator, by instruction; the report gives the wording.
- **Permissions**: `procedure:edit` goes to `maint_engineer` only (so the manager), and it is in
  `SITE_SCOPED`. `test_role_matrix` and `test_procedure_keys` are updated. Operator, supervisor,
  technician, storekeeper and IT admin get 403 on create (tested).
  - Create uses `load_node_for_user(…, key=EDIT_KEY)`: 404 outside the units, then 403 at the
    machine's site (tested both ways).
  - A change is decided from the **locked** `class_id`. A machine lesson needs its units (404) and
    the key at its site (403). A class lesson needs only the route's any-site check.
  - A tick or untick calls `require_perm_at` at the machine's site, whatever the stored target
    (tested: changed from another site with 200; unticked from there with 403).
  - Reads use `equipment:read`. A machine lesson is visible only inside the reader's units; a class
    lesson at every site. `machine` is null outside the reader's units (tested).
  - No actor comes from the client: `actor()` is the session's.
- **The documents store's fifth owner** (`documents.py`):
  - `_PROCEDURE_DOCS` is stacked on all eight routes. Every route runs `_owner_key` first, and then
    the owner's read or lock function before any file is read or served (`_serve` reads the row after
    `read_procedure`; an upload checks `read_procedure_for_change` before `_read_upload`).
  - A file is served with `nosniff` and `private` caching (tested). Files go to
    `DATA_DIR/procedures/<id>/` through `_OWNER_FOLDERS` (tested). No path part comes from the client.
  - D2: one lock function for change and purge is right, because a lesson has no state rule (the
    model owner does the same). The purge key reaches `require_perm_at` through `key`.
  - Removed list: the lesson branch has no condition with every unit. Otherwise it shows class
    lessons, or rows in the units where `equipment:purge_documents` is held. With no units, only
    class lessons show; the branch is never left out (as the model branch). The search covers four
    columns. All values are bound parameters; `marks()` builds only the placeholders.
    `test_the_unit_scope_is_enforced_fail_closed` changes one line, as § 8.3 says.
  - D5: the removed row's `equipment_id` is the machine's id. The node branch of
    `RemovedDocuments.vue` then links the machine until S077. The row's `path` targets the lesson's
    documents URL, so restore and purge work there.
- **Locks** (§ 5.6) against the LOCK ORDER notes in `equipment.py`, `improvements.py`, `documents.py`
  and `procedures.py`:
  - Create takes (6) `OPL`, then (6c) shared, then the insert's foreign-key shared locks.
  - A change and a lesson document each take (6d) `FOR UPDATE` as their first statement, and the
    first plain read comes after it, so each decision sees the fresh row.
  - No module locks or updates `procedures` rows except procedures.py and the documents path.
    Nothing deletes `improvement_actions`, `equipment` or `equipment_classes` rows, or changes their
    ids, so no parent write waits on a lesson row.
  - S074's scan takes (6b) and then (6c) exclusive, and never waits on `OPL` or (6d). No cycle.
  - (6d) joins the global order in `equipment.py`, with the procedures.py bullet.
- **The link** (§ 5.3): `lesson_source` is one plain read through S067's predicate (400
  `action_id`). The machine must be the improvement's machine (400 `equipment_id`, with the code
  from D1). (6c) is taken shared, and `lesson_link_error` refuses another kind and a cancelled
  countermeasure (409). The linked-lesson check gives a 409 with the serial, and
  `UNIQUE_KEY_ERRORS["uq_procedures_action"]` is the backstop. A stored link is kept
  (`link_kept_error`). A closed improvement's row and its timeline are untouched (tested).
- **The improvement detail** (§ 6.4): `lesson` comes from one query for all countermeasures.
  `can_write_lesson` follows the create's own checks, on the machine's **current** unit and site.
  The extra read runs only when a countermeasure could take a lesson (D3). It is tested after a
  cross-site move.
- **Pure core**: `procedures_core.py` holds no DB access and no clock. `validate_lesson` follows the
  § 5.2 table: the title's whitespace is collapsed, the body keeps its line breaks, and a null on a
  change is refused (D8). `improvements_core` exposes `is_id` and `text_field` (D10). The import
  direction is `improvements` → `procedures_core` → `improvements_core`, with no cycle;
  `procedures` → `improvements` is one-way and noted.
- **The database down**: every route goes through `get_db()`. `POST /api/procedures` → 503 (tested).
- **Departures** (report § 4, D1–D10): each one is small, has a reason, and changes no behaviour the
  brief describes. The stale check (§ 0) matches the tree.
- **Track and tests**: the step is full track. The tests cover § 8.2 and § 8.3, failure modes
  included. `conftest._TABLES` gains `procedures`.
- **Browser tests**: there is no screen change (§ 8.4). The coder ran a targeted run (equipment,
  settings, improvements, screens: 99 passed, 2 skipped) and the whole Normal suite once (290 passed,
  13 skipped), as § 8.4 asks. `settings.spec.js` covers the removed-documents list, which gains a
  branch.
- **Manual checks**: none in this step (§ 8.4, § 8.5); the report says so.

## Manual browser check

None for S075: it has no screens. S077 holds the screen checks and the Tamil checks on a phone and on
paper.

## Feedback

- hindrance: the step diff showed S074's review file and `INDEX.md` changes made after S074's
  snapshot, which are not S075's work (`step_snapshot.py diff S075 --stat`, 1 min to rule out).
