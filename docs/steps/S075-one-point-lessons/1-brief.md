```
Step: S075 — One-point lessons
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066–S069 (gate B), S070 (being coded); S071–S074 approved or in review, coded before S075
Status: In review
From: R05.6 (first half: the record, its API and the documents owner; the screens are S077)
```

# S075 — One-point lessons

## 1. What will be built

R05.1–R05.5 let the team analyse a failure, act on it and check that the action worked (S067–S074).
**R05.6 carries what the team learned to the floor**: a **one-point lesson**, one title, one short
text and a few photos, shown on the machine's page and, when ticked, on every machine of its class
(TPM yokoten). It is the first kind of the Procedures master (Plan § 4.3a; gate R Q6.1 a). R05.6 is
an L item with a backend and screens that can ship apart, so it is **split at the API**, as R05.1,
R05.3 and R05.4 were (§ 9, *The split*). **This step builds the backend half.** **S077**
(`docs/steps/S077-one-point-lesson-screens/1-brief.md`) builds the screens on § 6, as written here.

1. **Write a lesson** (`POST /api/procedures`) on a machine (any node of the equipment register),
   with a title and a short text, in Tamil or English; optionally **for every machine of the
   machine's class** (`for_class`, Q6.2 a). Engineers and managers (new key `procedure:edit`,
   Q6.3 a). Serial **`OPL-NNN`**, one plant-wide series (D3).
2. **Change** it (`PUT`): title, text, the class tick, and **retire** or bring it back (`active`).
   Nothing is deleted (ISO 9001 § 7.5.3).
3. **Photos** through the documents store: a **fifth owner**, the lesson
   (`equipment_documents.procedure_id`, the owner CHECK widened again). Files are served only through
   the permission-checked routes (§ Yantra Specifics, *Files (S006)*).
4. **Read**: the lessons of one machine (its own and its class's) for the equipment page's *Lessons*
   card, and one lesson in full for the lesson page. Every user who can open the machine reads its
   lessons (`equipment:read`), operators included: the operator scans the press's QR label and sees
   the lesson (D5).
5. **From a countermeasure:** a lesson written for a countermeasure of kind *Lesson* (S070) links it
   (`procedures.action_id`). The improvement's detail shows each countermeasure's lesson and whether
   the user may write it (`lesson`, `can_write_lesson`). The lesson shows "From improvement IM-…" to
   readers of that improvement. The countermeasure is still marked done by its owner (D8).

**After S075 and S077:** milestone 3's first half. The press operators at SSVT.SHOP open HP003 and
every hydraulic press and see "Keep the panel door shut", with the photo of the dusty contactor.

### Out of scope

- **Every screen** (S077): the *Lessons* card, the lesson page, the lesson dialog, the countermeasure's
  lesson line and *Write lesson*, the removed-documents row, print, the browser tests.
- **Who was shown a lesson** (R05.7, deferred at gate R): no `procedure_completions`, no *Shown to*.
- The other kinds of procedure (work instruction, diagnostic, onboarding), numbered steps in the
  shared item shape (`procedure_items`, Plan § 4.3), a Markdown body, a lesson on a PM template or a
  ticket, a lesson for a class with no machine named (D2).
- A plant-wide list of lessons (a Masters tab): lessons are reached from a machine (D6).
- The history of a lesson's earlier texts and an approval step (§ 2, the departures).
- Alerts about lessons; a timeline line on the improvement for a lesson written (D8).

## 2. Standards and practice

- **TPM — one-point lesson** (OPL; training pillar). In plain words: one page about one point,
  mostly a picture and a few words, written by the person who knows, taught at the machine in a few
  minutes. TPM practice names three types: basic knowledge, a problem case and an improvement case
  (*to verify*). A lesson written from an improvement is the *improvement case*. S075 keeps it one
  page: one title (80 characters), one text (1000 characters) and its photos.
- **TPM — education and training pillar.** In plain words: operators and technicians learn the
  skills their machines need, in small steps, and the plant keeps what it learned. The lesson is
  the first piece; the record of who was taught (R05.7) and the skill matrix (Plan § 4.3a) come
  later.
- **TPM — horizontal deployment** (*yokoten*). In plain words: what was learned on one machine is
  spread to the similar machines before they fail too. The class tick shows the lesson on every
  machine of the class (Q6.2 a).
- **ISO 9001:2015 § 7.1.6** (organisational knowledge). In plain words: the organisation decides
  what knowledge it needs, keeps it and makes it available, including lessons learned from
  failures. The lesson lives on the machine's page, where it is needed, not in a file nobody opens
  (Plan § 4.3a).
- **ISO 9001 § 7.5.2 and § 7.5.3** (documented information: creating, updating, control). In plain
  words: a document carries an identity (title, number, date, author), is reviewed and approved
  before use, is available where it is needed, is protected, and its changes are controlled;
  obsolete documents are kept but marked. The lesson carries `OPL-NNN`, who wrote it and when, who
  changed it last and when; a retired lesson is kept and marked, never deleted.
  **Departures (recorded):** (1) an edit keeps no earlier text (as S067 § 2 recorded for
  improvements before R05.4): a lesson's revision history is left to the Procedures roadmap; (2) no
  separate approval step: the writer holds `procedure:edit` (an engineer or a manager), as Plan
  § 4.3a says "edited by engineers". Clause numbers of the next ISO 9001 edition are *to verify*
  (R05 § Standards).
- **ISO 27001 A.5.15** (access control) and **A.8.3** (information access restriction). In plain
  words: give each person only what their work needs, and serve files only after checking who
  asks. Lessons are read with the machine's own read key; photos are served only through the
  documents routes after the lesson's access check (S006's rule).

## 3. Where

S075 is coded after S074. Files marked **(S067)** or **(S070)** exist in the working tree now; S070
is being coded and S072–S074 change some of them first, so line numbers in `backend/improvements.py`,
`backend/documents.py`, `backend/local_db.py`, `backend/equipment.py` and `backend/tests/conftest.py`
are the working tree's on 30-10-2026 and may move. Function and constant names are the anchors.
Names new in S070–S074 are marked so; the facts run shows them as missing until those steps land.

### Backend

- `backend/local_db.py`: migration **v41** (§ 4.1). S070's v38 starts at `backend/local_db.py:1186`;
  S072 adds v39, S074 v40. No `_PRECONDITIONS` entry (§ 4.1).
- `backend/procedures_core.py` (new, pure): the kind, the keys, the serial, the bounds and messages,
  `validate_lesson`, `lesson_link_error`, `lesson_flags` (§ 5). It imports `_text` and `_is_id` from
  `backend/improvements_core.py` (D10).
- `backend/procedures.py` (new): the blueprint `procedures_bp` (§ 6), the lesson reads, the locks
  (§ 5.6) and the documents owner's four functions `read_procedure`, `read_procedure_for_change`,
  `lock_procedure_for_change`, `lock_procedure_for_purge` (§ 5.8), with a LOCK ORDER note. It imports
  `NODE_JOINS`, `accessible_unit_ids` and `load_node_for_user` from `backend/equipment.py`, and
  `read_action` (new in S070) and `lesson_source` (new here) from `backend/improvements.py`;
  `next_counter` from `backend/db_helpers.py:78`.
- `backend/app.py`: registers `procedures_bp` at `/api/procedures`, beside `improvements_bp`
  (`backend/app.py:192`).
- `backend/config_rbac.py`: the key `procedure:edit` (`maint_engineer`, so the manager) after the
  improvement keys (`backend/config_rbac.py:133`), with its comment; added to `SITE_SCOPED`
  (`backend/config_rbac.py:175`) (§ 5.7).
- `backend/documents.py`: the owner `"procedure"` in `OWNERS` (`backend/documents.py:170`); a fifth
  stacked route decorator `_PROCEDURE_DOCS` / `_FOR_PROCEDURE` on every documents route, as S070's
  `_ACTION_DOCS` (`backend/documents.py:194`); a fifth branch in `_removed_branches`
  (`backend/documents.py:528`) and `_removed_item` (`:506`); the module docstring (owners, locks)
  (§ 5.8).
- `backend/file_store.py`: `_OWNER_FOLDERS` (`backend/file_store.py:23`) gains
  `"procedure": "procedures"`; the docstring's layout line.
- `backend/improvements.py` **(S067, S070)**: `_actions` (`backend/improvements.py:351`) gains each
  countermeasure's `lesson` and `can_write_lesson` (one more query, § 6.4); a new read
  `lesson_source(cur, action_id)` for procedures.py (§ 5.9); the import-direction note
  (`backend/improvements.py:104`) names procedures.py as a new importer. No write route changes.
- `backend/equipment.py`: docstring only. The global LOCK ORDER (`backend/equipment.py:9`) gains a
  bullet for procedures.py, as properties.py's (§ 5.6); the documents.py bullet names the lesson
  row as one more owner lock.

### Tests

- `backend/tests/test_migration_v41.py` (new), on the pattern of `test_migration_v36.py`
  (`VERSIONS = list(range(20, 37))`, `backend/tests/test_migration_v36.py:17`; v41 slices
  `range(20, 42)`) (§ 8.1).
- `backend/tests/test_procedures_core.py` (new): the pure functions (§ 8.2).
- `backend/tests/test_procedures_api.py` (new): every route of § 6 (§ 8.2).
- `backend/tests/test_documents_api.py`: a class `TestLessonDocuments` on the pattern of
  `TestActionDocuments` (new in S070, `backend/tests/test_documents_api.py:687`);
  `TestOwnerCheckConstraint` (`:490`) gains the five-owner case (§ 8.3).
- `backend/tests/test_removed_documents_api.py`: `test_the_unit_scope_is_enforced_fail_closed`
  (`backend/tests/test_removed_documents_api.py:136`) changes one line (§ 8.3); the lesson rows.
- `backend/tests/test_improvement_actions_api.py` (new in S070): the countermeasure's `lesson` and
  `can_write_lesson` (§ 8.2).
- `backend/tests/test_rbac.py`: `test_role_matrix` (`backend/tests/test_rbac.py:219`) and a key
  test (§ 8.3).
- `backend/tests/conftest.py`: `procedures` joins `_TABLES` (`backend/tests/conftest.py:162`),
  before `improvement_actions` (the fixture deletes with `FOREIGN_KEY_CHECKS = 0`; the order is for
  reading only).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the table `procedures` (out of § Planned: `procedure_items`
  and `procedure_completions` stay planned), the column `equipment_documents.procedure_id` and its
  CHECK, the Mermaid overview (procedures → equipment, equipment_classes, improvement_actions;
  equipment_documents → procedures), the "migration v41" line.
- `docs/Plan.MD`: § 3, the key table gains `procedure:edit` (engineer, manager) and one paragraph
  (lessons read with `equipment:read`; edited at the machine's site, a class lesson at any site);
  § 4.3a, a line "*Built in part* (S075, S077): the one-point-lesson kind" with this step's
  departures (plain text, not Markdown; a lesson always names a machine; no steps, history or
  approval step).
- `docs/Maintenance-Philosophy.md`: § 3's *Training & education* row gains "one-point lessons
  built (S075, S077)"; § 12 Glossary gains *One-point lesson (OPL)* and *Yokoten* if absent.
- `.claude/CLAUDE.md`: § Yantra Specifics, *Files (S006)*: a fifth owner, the lesson
  (`DATA_DIR/procedures/<id>/`); § Step workflow, *Self-check, repo items* (2): the LOCK ORDER note
  of `procedures.py` joins those of `tickets.py` and `masters.py`. (The § SMTW-Review spec map is
  S077's.)

**File count:** 17 code and test files (9 code: `local_db.py`, `procedures_core.py`,
`procedures.py`, `app.py`, `config_rbac.py`, `documents.py`, `file_store.py`, `improvements.py`,
`equipment.py`; 8 tests), 5 docs.

## 4. Data model

### 4.1 Migration v41

```sql
-- One-point lessons (S075, R05.6): the first kind of the Procedures master (Plan § 4.3a).  A
-- lesson names the machine it was written on; class_id, when set, shows it on every machine of
-- that class too (TPM yokoten).  action_id: the countermeasure of kind Lesson it was written for
-- (one lesson per countermeasure).  Never deleted: a retired lesson keeps its row (ISO 9001 § 7.5.3).
CREATE TABLE IF NOT EXISTS procedures (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    serial        VARCHAR(16) NOT NULL,
    kind          ENUM('one_point_lesson') NOT NULL DEFAULT 'one_point_lesson',
    equipment_id  INT NOT NULL,
    class_id      INT NULL,
    title         VARCHAR(80) NOT NULL,
    body          VARCHAR(1000) NOT NULL,
    action_id     INT NULL,
    active        TINYINT(1) NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    VARCHAR(100) NOT NULL,
    updated_at    DATETIME NULL,
    updated_by    VARCHAR(100) NULL,
    CONSTRAINT uq_procedures_serial UNIQUE (serial),
    CONSTRAINT uq_procedures_action UNIQUE (action_id),
    KEY ix_procedures_equipment (equipment_id, active),
    KEY ix_procedures_class (class_id, active),
    CONSTRAINT fk_procedures_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_procedures_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
    CONSTRAINT fk_procedures_action FOREIGN KEY (action_id) REFERENCES improvement_actions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A photo or document of a lesson: the fifth owner of the documents store.
ALTER TABLE equipment_documents
    ADD COLUMN IF NOT EXISTS procedure_id INT NULL AFTER action_id,
    ADD KEY IF NOT EXISTS ix_equipment_documents_procedure (procedure_id, removed_at),
    ADD CONSTRAINT fk_equipment_documents_procedure
        FOREIGN KEY IF NOT EXISTS (procedure_id) REFERENCES procedures (id);
ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner;
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL)
           + (action_id IS NOT NULL) + (procedure_id IS NOT NULL) = 1);
```

- **`kind`** holds one value today; the other kinds of Plan § 4.3a append theirs at the end (no row
  changes). A later kind that needs no machine makes `equipment_id` NULLable then (D2).
- **`uq_procedures_action`** allows one lesson per countermeasure and any number of lessons with no
  countermeasure (NULLs), as `uq_improvement_tickets_open` (v36) does. It also catches two writers
  racing to link one countermeasure (§ 5.6).
- **`active`** is the retire flag, the masters' pattern (`ActiveToggle`); a retired lesson leaves the
  card for readers but keeps its row, its photos and its serial.
- **The owner CHECK** is dropped and added again with its name, as S070's v38 did
  (`backend/local_db.py:1186`). Every existing row has exactly one of the four owners and
  `procedure_id` NULL, so it meets the new CHECK.
- **Re-run safety:** `IF NOT EXISTS` on the table, the column, the key, the foreign key and the
  CHECK; `DROP CONSTRAINT IF EXISTS`. A half-applied v41 (the CHECK dropped, not added) runs again
  and adds it (§ 8.1).
- **No precondition** (v38's reasoning): a new table; on `equipment_documents` a nullable column, a
  key and a CHECK every existing row meets. Nothing is converted or dropped. The foreign-key add and
  the CHECK scan the documents rows (production holds node, model and ticket documents); § 8.1 runs
  v41 on a v40 database with rows of all four owners.
- **Rollback:** a release before v41 never reads `procedures`; its documents queries name their
  columns, and its removed-list branches join their own owner, so a lesson's photo row is invisible
  to it.
- **Text:** utf8mb4. MariaDB counts characters (code points) in `VARCHAR(n)`, and Python's `len`
  counts the same, so the bounds agree. Tamil writes a letter with a vowel sign as two code points,
  so 1000 is about 600 Tamil letters (assumption, fine for one point).
- **Serial counter:** one `serial_counters` row, scope `OPL` (no colon: one series for the plant,
  D3). The existing scopes are `EQ:<prefix>`, `TK:YYYY-MM` and `IM:YYYY-MM` (`backend/equipment.py`
  `_next_code`, `backend/tickets.py:871`, `backend/improvements.py:525`), so `OPL` meets none.

### 4.2 What is computed, never stored

- `for_class` (`class_id IS NOT NULL`); the class's code and name; the machine's code, name and site.
- The flags `can_add`, `can_edit`, `can_change_class` (§ 5.7) and the countermeasure's
  `can_write_lesson`.
- `source`: the improvement a linked lesson came from (§ 5.9).
- The cover photo of each lesson on the card (§ 6.2).

## 5. Rules

### 5.1 The lesson and its machine

- A lesson **always names a machine** (`equipment_id`): any node of the register, at any level and
  in any lifecycle. The machine never changes after the write (D2). A scrapped machine's lessons stay:
  a class lesson written on a press that is later scrapped still teaches the other presses. A lesson
  may be written on a scrapped node too (no lifecycle rule: a lesson is knowledge, not a change to the
  asset).
- **The class tick** (`for_class`): true stores `class_id` = the machine's `class_id` **at that
  moment** (from the plain read of the node, § 5.6); false stores NULL. A later change of the
  machine's class (a new model) leaves the lesson's class as it was; the team ticks again if needed.
- **Where a lesson shows** (§ 6.2): on the page of node N, every lesson with `equipment_id = N`, and
  every lesson with `class_id = N.class_id`. A node does not show its parts' or its parent's
  lessons (as model documents, `backend/documents.py` `_inherited`).

### 5.2 The fields

`validate_lesson(body, creating)` for `clean_body` (`backend/api_common.py:121`):

| Field | `POST` | `PUT` | Rule and message (field) |
|---|---|---|---|
| `equipment_id` | required | ignored | integer ≥ 1, not a boolean: "Choose the machine" (`equipment_id`); then § 5.6 (404 when not visible) |
| `title` | required | optional, not `null` | text; inner runs of spaces and line breaks become one space, trimmed; 1–80: "Enter a title" / "Title: up to 80 characters" / "Title must be text" (`title`) |
| `body` | required | optional, not `null` | text, trimmed, line breaks kept, 1–1000: "Enter the lesson text" / "Lesson text: up to 1000 characters" / "Lesson text must be text" (`body`) |
| `for_class` | optional, default false | optional | `true` or `false`: "For the class must be true or false" (`for_class`) |
| `action_id` | optional, `null` = none | optional | integer ≥ 1 or `null`: "Choose a countermeasure" (`action_id`); then § 5.3 |
| `active` | ignored (a new lesson is active) | optional | `true` or `false`: "Active must be true or false" (`active`) |

- `kind` is never read from the body: the server writes `one_point_lesson`.
- An absent field on a `PUT` stays as it is; a field equal to the stored value is not written; a
  `PUT` that changes nothing answers 200 and writes nothing (no `updated_at`), as S067 § 5.2.
  Unknown fields are ignored.
- **The title collapses whitespace** (masters' `_collapsed` rule, `backend/masters_core.py:69`): a
  title is one line on a card and on paper. The body keeps its line breaks: an operator line in
  Tamil and one in English (mock-up 06).

### 5.3 The link to a countermeasure

`action_id` on a `POST`, or on a `PUT` while the stored `action_id` is NULL:

1. The countermeasure through its improvement's predicate: `read_action(cur, action_id)` (new in
   S070) → 404 becomes **400** "Choose a countermeasure" (`action_id`): a body field names a record
   the user cannot open, as S067's lead (400). (`procedures.py` turns the 404 into the 400 by
   reading first with `lesson_source`'s predicate, § 5.9, not by catching the error.)
2. The countermeasure's row `LOCK IN SHARE MODE` (§ 5.6) → `lesson_link_error(kind, state)`:
   - kind not `lesson`: 409 "Only a countermeasure of kind Lesson links a lesson" (`action_id`);
   - `cancelled`: 409 "This countermeasure was cancelled" (`action_id`; S070's words);
   - `open` or `done`: allowed. The improvement may be in any state, closed too: linking writes only
     the lesson row, never the improvement (D8).
3. **The machine:** the lesson's `equipment_id` must be the improvement's machine
   (`improvements.equipment_id`, which never changes): else 400 "A lesson for this countermeasure
   goes on HP003, the improvement's machine" (the code filled in; `equipment_id`). The class tick is
   free. So every reader of the improvement can open its lesson (D9).
4. **One lesson per countermeasure:** another lesson with this `action_id` → 409 "This
   countermeasure already has its lesson, OPL-007" (`action_id`). A race past the plain check meets
   `uq_procedures_action`: `UNIQUE_KEY_ERRORS["uq_procedures_action"] = ("action_id", "This
   countermeasure already has a lesson")`, 409.

On a `PUT`: `action_id` equal to the stored one is no change; a different id or `null` when one is
stored → 409 "A lesson keeps the countermeasure it was written for" (`action_id`). The link records
where the lesson came from (ISO 9001 § 7.5.2: identity), so it is set once. A later change of the
countermeasure's kind (S070's `PUT`) leaves the link as it is: it still says where the lesson came
from.

### 5.4 Retire

`active` false hides the lesson from the card's readers (§ 6.2) and keeps its page, photos and
serial for anyone who opens it (the page says "Retired", S077). `active` true brings it back. A
retired lesson can still be changed (no state rule: fewer refusals for the same result). A
countermeasure's link to a retired lesson stays.

### 5.5 Who may write: the site rule

A lesson is **site-scoped while it is the machine's, and site-less once it is the class's**
(Q6.3 a; the rule failure codes follow, `backend/config_rbac.py:157`, here applied per record):

| Write | The key `procedure:edit` must be held … |
|---|---|
| Create (with or without the tick) | at the machine's site, and the machine inside the user's units (`load_node_for_user`, 404 then 403) |
| Change title, body, `active`, a photo — **machine lesson** (`class_id` NULL) | at the machine's site (404 outside the units, then 403) |
| The same — **class lesson** (`class_id` set) | at any site (`check_perm`, 403) |
| Tick or untick the class | at the machine's site (403 naming the site), whatever the stored target |
| Restore or purge a removed photo | `equipment:purge_documents` at the machine's site for a machine lesson, at any site for a class lesson (as model documents, S012 § 5.6) |

- The **decision of which row applies** comes from the locked row's `class_id` (§ 5.6).
- **Create always needs the machine's site:** a lesson is written from a machine the writer works
  on; the tick is part of the same write.
- **Untick needs the machine's site:** it turns a site-less lesson back into a site's, so a writer at
  another site cannot pull a lesson onto a site where they hold no right.
- A request with no identity gets `require_perm`'s 401, never admin. No field here changes who can
  log in or what anyone sees beyond the lesson itself; the writer's name shows to every reader, no
  login, role or email.

### 5.6 Locks

The database runs REPEATABLE READ. Each route takes its locking reads before deciding; every
decision comes from a locking read or from a plain read made after the lock that guards it; access
checks are plain reads, as every predicate.

**Where procedures.py stands in the global order** (`backend/equipment.py:9`). It takes, per write,
**either** (6) the `OPL` serial counter (create only) **or** (P) one procedures row `FOR UPDATE`
(change, a document's owner lock), never both, and never two procedures rows. Then only shared
locks: a countermeasure row (6c, new in S070) `LOCK IN SHARE MODE` when linking, and the foreign-key
shared locks of its insert or update (the machine (1), the class (5), the countermeasure (6c)).
`equipment_documents` rows follow under (P), which nothing else locks.

**Create** (`POST /api/procedures`), one `transaction`:

1. Plain reads, the transaction's first: the machine through `load_node_for_user(cur, equipment_id,
   for_update=False, key="procedure:edit")` (404 outside the units, 403 without the key at its
   site); its `class_id` for the tick.
2. With `action_id`: `lesson_source` (the predicate, 400, § 5.3 (1)); then (6c) `SELECT id,
   improvement_id, kind, state FROM improvement_actions WHERE id = %s LOCK IN SHARE MODE` → 409
   (§ 5.3 (2)); the improvement's `equipment_id` (plain; never changes) → 400; the existing lesson
   with this `action_id` (plain) → 409.
3. (6) `next_counter(cur, "OPL")` (`backend/db_helpers.py:78`): only lesson creates take this row,
   so two creates serialise here. A refused or failed create rolls the bump back: no gap.
4. The `procedures` insert (shared FK locks on the machine, the class, the countermeasure; a lost
   race on the link meets `uq_procedures_action`, 409).
5. The detail, read inside the transaction.

**Change** (`PUT /api/procedures/<id>`):

1. (P) `SELECT id, equipment_id, class_id, action_id, active, title, body FROM procedures WHERE id = %s
   FOR UPDATE`; 404 when missing.
2. Plain reads: the rights of § 5.5 from the locked `class_id` (a machine lesson: the node
   predicate 404, the key at its site 403; a class lesson: `check_perm` 403); when `for_class`
   changes, the machine's site and class (plain read through `NODE_JOINS`) and the key at that site
   (403); when `action_id` is sent and the locked one is NULL, § 5.3 with (6c) shared.
3. `update_row` of the changed fields, stamping `updated_at`, `updated_by` (a new class or
   countermeasure takes its shared FK lock).

**A document of a lesson** (§ 5.8): the documents store's one owner lock is (P):
1. (P) `FOR UPDATE` (the same statement); 404 when missing;
2. plain reads: the read right (§ 5.7) 404, the write or purge right of § 5.5 403, all decided by the
   locked `class_id`;
3. the `equipment_documents` statement (an insert takes a shared lock on the procedures row, held).

**Reads** (the list, the detail, the improvement's `lesson`): plain, no lock.

**No new deadlock cycle, checked against the notes:**
- *The counter:* only lesson creates take the `OPL` row, and they hold nothing exclusive before it.
  Whoever holds a machine, class or countermeasure exclusive never waits on an `OPL` row.
- *(P):* only procedures.py and the documents path lock a procedures row, one at a time, first in
  their transaction. No other module locks or updates procedures rows; improvements.py reads them
  plainly. So no path holds another lock and then waits on (P).
- *The machine (1), the class (5):* a create or a change takes them shared through the foreign keys,
  after (6) or (P). A node write (equipment.py: scrap, move, edit) and a class write (masters.py)
  hold them exclusive and never wait on a procedures row or the `OPL` counter. InnoDB checks a
  child's foreign key only when the column changes, and updates of `equipment` and
  `equipment_classes` never change `id`, so they take no lock on procedures rows.
- *(6c):* the link takes it shared, without (6b) first. S070–S074's writers take (6b) then (6c)
  exclusive and never wait on (P) or the `OPL` counter, so a lesson create waiting on (6c) waits
  behind them and nothing waits on it. Two lesson writes on one countermeasure share the lock and
  meet on `uq_procedures_action`. S074 D4 rejected a scan that took (6c) before (6b)
  (`docs/steps/S074-improvement-alerts/1-brief.md` D4): that write then took the improvement too;
  this one never does.

The coder writes this into procedures.py's LOCK ORDER note, adds a procedures.py bullet to
equipment.py's order (as the properties.py bullet), and names the lesson lock in documents.py's
*Locks* paragraph.

### 5.7 Permissions

One new key, **`procedure:edit`** (`maint_engineer`, so the manager; not IT admin, not the
supervisor), in `SITE_SCOPED` (Q6.3 a; D4). Reading needs no new key: **`equipment:read`** (D5).

| Action | Route decorator | Then |
|---|---|---|
| A machine's lessons (`GET /api/procedures?equipment_id=`) | `equipment:read` | the node predicate (`load_node_for_user`, 404) |
| One lesson, machine lesson | `equipment:read` | the node predicate, 404 |
| One lesson, class lesson | `equipment:read` | none: every holder of `equipment:read` at any site, as model documents (S012 § 2) |
| Create, change, retire, tick | `procedure:edit` (held at any site) | § 5.5 |
| Photos: list, file, thumb | `equipment:read` (`_owner_key`) | `read_procedure`: as *one lesson* |
| Photos: upload, retitle, remove | `procedure:edit` (`_owner_key`) | `read_procedure_for_change` / `lock_procedure_for_change`: § 5.5 |
| Photos: restore, purge | `equipment:purge_documents` (`_owner_key`) | § 5.5, last row |

- **Flags** (`lesson_flags`, pure, fed the stored `for_class` and three booleans the shell reads:
  `edit_here` = `has_perm_at("procedure:edit", machine site)`, `edit_anywhere` =
  `has_perm("procedure:edit")`): `can_edit` = `edit_anywhere` for a class lesson, else `edit_here`;
  `can_change_class` = `edit_here`. The list's `can_add` = `edit_here` at the node's site. S077 shows
  each control from these, so no button ends in a 403 (S070 D10).
- **The countermeasure's `can_write_lesson`** (§ 6.4): kind `lesson`, state not `cancelled`, no
  lesson linked, and `has_perm_at("procedure:edit", site)` at the improvement's site (its machine's
  site is the same: S067 § 5.7).
- **Who holds what** (Plan § 3 matrix): operator, supervisor, technician, storekeeper read lessons
  on the machines of their units; engineers and managers write at their site and change class
  lessons anywhere; IT admin reads only (`equipment:read_all_units`: every unit).

### 5.8 Photos: the documents store's fifth owner

- `OWNERS["procedure"] = Owner("procedure_id", "/api/procedures/{}/documents", "lesson",
  read_procedure, read_procedure_for_change, lock_procedure_for_change, lock_procedure_for_purge,
  "equipment:read", "procedure:edit", "equipment:purge_documents")`. The four functions live in
  procedures.py; documents.py imports them, as it imports `read_action`. procedures.py never imports
  documents.py.
- **The functions branch on the stored target** and say so in their docstrings: a machine lesson
  checks the node predicate (404) and the key at the machine's site (403); a class lesson needs
  nothing beyond `_owner_key`'s any-site check (`backend/documents.py:201`). `lock_procedure_for_*`
  decide from the locked (P) row; `read_procedure_for_change` repeats the checks with plain reads
  so a refused upload reads and writes no file (S006 § 5.6).
- **No state rule:** a retired lesson's photos may be added, retitled and removed (§ 5.4); a
  scrapped machine's lesson too (§ 5.1).
- **Every kind** (`photo`, `document`), as every owner (S018). A lesson is "mostly a picture"; the
  documents store has no count bound for any owner, and this step adds none (assumption, § 9).
- **Routes**: `_PROCEDURE_DOCS = "/procedures/<int:owner_id>/documents"` and `_FOR_PROCEDURE` stacked
  on list, upload, file, thumb, title, remove, restore, purge. They live in `documents_bp` (prefix
  `/api`); `procedures_bp`'s own routes are `/`, `/<int:procedure_id>`, and none ends in
  `/documents`, so the two blueprints never claim one URL (as tickets and their documents).
- **Files**: `DATA_DIR/procedures/<procedure_id>/` (`file_store._OWNER_FOLDERS`), served only by
  `_serve` (`backend/documents.py:367`) after the read check (ISO 27001 A.8.3), with
  `X-Content-Type-Options: nosniff` and `private` caching as for every owner (`:386`). The file type
  is decided from the first bytes (`detect_file_type`), not the name or the client's type (S006).
- **Removed list** (`GET /api/equipment/removed-documents`): a fifth branch,
  `_REMOVED_PROCEDURE_BRANCH`: `owner` `"procedure"`, `name` the serial ("OPL-007"), `code` the
  machine's code, the machine's `site_code` and `unit_code` (through `NODE_JOINS`), `owner_state`
  NULL, `action_kind` NULL. Its
  scope: `pr.class_id IS NOT NULL OR u.id IN (units where equipment:purge_documents is held)`; with
  no such units, only the class lessons' rows (as the model branch, which is never left out). The
  search `q` matches the serial, the title and the original name. `_removed_item` gives a lesson row
  its unit and `full_path` None, as a countermeasure's.
- **A removed photo** keeps its row and file (S006) and is not listed in the detail.

### 5.9 The source line

`improvements.lesson_source(cur, action_id)` (new, plain read): the countermeasure's improvement as
`{improvement: {id, serial, title}, action_id}` when the user may open the improvement (S067's
predicate, `_visible_condition`, `backend/improvements.py:192`), else `None`. One query, no
exception. The lesson detail's `source` is it; a reader without `improvement:read` there (the
storekeeper) sees no line. procedures.py also uses it for § 5.3 (1).

### 5.10 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing. Uploads keep
S006's order (files written with no transaction open; a failed insert removes them). No background
task, no alert.

## 6. API

All under `procedures_bp` (`/api/procedures`), ids `<int:…>`. Every write answers with the lesson's
whole detail (one answer, one page copy, S068 BR1-09).

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/procedures` | `equipment:read` | `equipment_id` (required: 400 "equipment_id is required") | the machine's lessons, § 6.2 |
| `GET /api/procedures/<id>` | `equipment:read` | — | the detail, § 6.3 |
| `POST /api/procedures` | `procedure:edit` | `{equipment_id, title, body, for_class?, action_id?}` | 201, the detail; 400, 403, 404, 409 per § 5 |
| `PUT /api/procedures/<id>` | `procedure:edit` | `{title?, body?, for_class?, action_id?, active?}` | 200, the detail |
| `…/api/procedures/<id>/documents` (list, upload, `/<doc_id>/file`, `/thumb`, `PUT`, `DELETE`, `/restore`, `/purge`) | § 5.7 | as every owner (S006, S008) | as every owner |
| `GET /api/improvements/<id>` (S067) | `improvement:read` | — | each of `actions` gains `lesson`, `can_write_lesson` (§ 6.4) |

### 6.2 A machine's lessons

`{items, retired, total, can_add}`:
- `items`: the active lessons of § 5.1, newest first (`id DESC`), `LIMIT 200` (`MAX_PER_PAGE`,
  `backend/api_common.py:133`), with `total` (the count of active ones; a bound for self-check 6).
- `retired`: the retired ones, same shape, only when the user holds `procedure:edit` at any site
  (`has_perm`), else `[]`. Same limit.
- Item: `{id, serial, title, for_class, class: {id, code, name} | null, own: bool (written on this
  node), active, cover: {doc_id, has_thumb} | null}`. `cover` is the lesson's oldest photo not
  removed, read for all items in one query (`MIN(id)` per `procedure_id` where `kind = 'photo'` and
  `removed_at IS NULL`), no N+1.
- `can_add`: `has_perm_at("procedure:edit", node site)`.

### 6.3 One lesson

`{id, serial, kind, title, body, active, for_class, class: {id, code, name} | null,
machine: {id, code, name} | null, created_at, created_by_name, updated_at, updated_by_name,
source: {improvement: {id, serial, title}, action_id} | null, documents: [{id, kind, title,
has_thumb}], can_edit, can_change_class}`.

- `machine` is `null` for a class lesson whose machine is outside the reader's units
  (`accessible_unit_ids`): the class line names it instead.
- `documents`: not removed, **oldest first** (`created_at, id`): the order the writer added the
  photos is the lesson's order (mock-up 06: photo 1, then photo 2). The documents route's own list
  stays newest first.
- The names of `created_by` and `updated_by`: the person whose login it is, else the login, as
  S067's `created_by_name`.

### 6.4 The countermeasure's lesson (improvement detail)

Each entry of `actions` (S070 § 6) gains `lesson: {id, serial, title, active} | null` (one query for
all the improvement's countermeasures: `SELECT id, serial, title, active, action_id FROM procedures
WHERE action_id IN (…)`) and `can_write_lesson` (§ 5.7). `_actions`' docstring: four queries for any
number.

## 7. Design decisions

- **D1. One table `procedures` with a `kind`, not a `lessons` table** (Q6.1 a). The other kinds of
  Plan § 4.3a join it with their own ENUM value and columns; the serial, the documents owner and the
  card stay one. Rejected: a lessons table now and a procedures table later (two masters for one
  thing); a text on the improvement (Q6.1 b: the lesson is not on the machine).
- **D2. A lesson always names its machine; the class is a tick on top** (`equipment_id` NOT NULL,
  `class_id` set from the machine). This is the mock-up's own line, "HP003 — Hydraulic press 3 · for
  every hydraulic press". The machine never changes, so the site rule (§ 5.5) has one anchor and a
  linked lesson always sits on its improvement's machine. **A small departure** from the roadmap's
  "the machine or the class": a class lesson is written from one of its machines. Rejected: exactly
  one of `equipment_id` or `class_id` (a class lesson loses where it was learned; unticking needs a
  machine picker; the edit route gains a target change with two site rules).
- **D3. Serial `OPL-NNN`, one series for the plant, through `serial_counters`** (scope `OPL`), past
  999 the number grows (`OPL-1000`), as equipment codes. A lesson is a reference people cite on the
  floor ("see OPL-007"); a short number is easier to say than `OPL-2026-10-001`, and lessons are a
  few a month. Rejected: `OPL-YYYY-MM-NNN` like tickets (long for a poster; months mean nothing to
  a lesson); a per-site series (a class lesson has no site).
- **D4. A new key `procedure:edit`, site-scoped, checked per record** (Q6.3 a). One key serves both
  rules: `has_perm_at` for a machine lesson, `has_perm` (held at any site) for a class lesson, the
  documents store's `_owner_key` pattern. Rejected: two keys (`procedure:edit` and
  `procedure:edit_class`; one person, one right); a global key like `failure_codes:edit` (an
  engineer of SSVT could rewrite SMTW's machine lessons).
- **D5. Lessons are read with `equipment:read`, no `procedure:read`.** The lesson belongs to the
  machine's page; whoever may open the machine (every role, at their units) reads its lessons, the
  operator after a QR scan included. Rejected: `improvement:read` (the storekeeper and anyone outside
  the improvement process could not see the floor's lessons); a new read key (a second list to keep
  equal to `equipment:read`).
- **D6. No plant-wide lesson list in R05.6.** Lessons are found where they apply: the machine, the
  class, the countermeasure. Rejected: a Masters tab now (not in the roadmap item; it can come with
  the Procedures roadmap).
- **D7. Plain text, not Markdown.** One point needs no headings or lists; line breaks are kept. No
  renderer, so no new dependency and no HTML from a user's text (ISO 27001 A.8.28, secure coding;
  *to verify*). A **departure** from Plan § 4.3a's "Markdown body", recorded there. Rejected:
  Markdown now (a library and an HTML sanitiser for one paragraph).
- **D8. The countermeasure is not done when its lesson exists; its owner marks it done.** In TPM a
  lesson counts when it is taught at the machine, and the record of who was taught is R05.7,
  deferred. Writing the lesson is the means; showing it is the countermeasure. So the link is a column
  on the lesson, written by procedures.py alone: no write of the improvement, its states or its
  timeline (S072 D8 covers improvements.py's writes; this write changes no improvement row). S077
  puts the lesson line on the countermeasure and offers *Mark done* as before. Rejected: done on
  write (a lesson written but never shown would close the countermeasure; procedures.py would then
  take (6b) and (6c) exclusive and write S072's timeline); the analogue of Q9.1 (a) was settled only
  for PM plans, and R05.9 is deferred.
- **D9. The link sits on the lesson (`procedures.action_id`, unique), not on the countermeasure.**
  One countermeasure, one lesson; the lesson remembers where it came from even if the improvement is
  closed. The machine must be the improvement's machine, so every reader of the improvement can open
  the lesson. Rejected: `improvement_actions.procedure_id` (a write of S070's row, so of the
  improvement's timeline and locks); linking an existing lesson to several countermeasures (rare;
  the class tick already shares a lesson across machines).
- **D10. `procedures_core` imports `_text` and `_is_id` from `improvements_core`.** One copy of the
  text rule. Rejected: copying them (DRY); moving them to `api_common.py` now (S070–S074 are changing
  `improvements_core.py`; a later tidy-up can lift them).
- **D11. Retire, not delete** (ISO 9001 § 7.5.3: obsolete documents kept and marked). The masters'
  `active` pattern. Rejected: delete (loses the record and the serial).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v41.py`)

- A fresh database: `procedures` with its keys, unique keys and foreign keys;
  `equipment_documents.procedure_id`, `ix_equipment_documents_procedure`,
  `fk_equipment_documents_procedure`; `chk_equipment_documents_owner` names `procedure_id`.
- **A v40 database with documents of all four owners** (a node, a model, a ticket, a countermeasure):
  every row kept, `procedure_id` NULL, the new CHECK met.
- The CHECK: a document with `action_id` and `procedure_id` both set is refused (4025); a lesson's
  document alone is accepted.
- `uq_procedures_action`: two lessons with one `action_id` refused (1062); two with NULL accepted.
- A Tamil title of 80 characters and a body of 1000 are stored whole (`VARCHAR` counts characters).
- A re-run of v41 changes nothing (`_schema()` equal); a half-applied v41 (the CHECK dropped, not
  added) runs again and adds it.

### 8.2 Backend (`test_procedures_core.py`, `test_procedures_api.py`, `test_improvement_actions_api.py`)

**Core:** `validate_lesson` (each message of § 5.2: missing on `POST`, empty after trim, 80 / 81 and
1000 / 1001, a number, `null` on a `PUT`, a boolean `equipment_id`, `for_class` "yes", `active` on a
`POST` ignored; the title "Keep  the\npanel" → "Keep the panel"; the body's line breaks kept; a Tamil
title of 80 characters passes, 81 refused); `format_lesson_serial` (1 → `OPL-001`, 1000 →
`OPL-1000`); `lesson_link_error` (lesson open, lesson done → None; corrective, cancelled → each message);
`lesson_flags` (machine and class lesson × `edit_here` × `edit_anywhere`).

**API**, each test with its own machines (the kept worker database gives the starting state;
`make_equipment`, `user_at_sites`, `role_client` as `test_documents_api.py`). "Another site" and "a
key missing here" as S067 § 8.2:
- **Create:** an engineer on a machine at the site (201, `OPL-` serial, `created_by_name`, active);
  with `for_class` (the class stored, `for_class` true); a Tamil title and body (stored and answered
  unchanged); an operator, a supervisor, a technician, IT admin (403); an engineer of another site
  on this machine (404: outside the units); an engineer here who is operator elsewhere, on the other
  site's machine (403: they read it as operator there, but hold no key there); a scrapped machine (201, § 5.1); two creates give
  consecutive serials.
- **Create with a countermeasure** (S070's set-up through `ticket_helpers.py`): a *Lesson*
  countermeasure, open (201, linked) and done (201); a *Corrective* one (409); a cancelled one (409);
  one of an improvement the user cannot open (400 `action_id`); on another machine than the
  improvement's (400 `equipment_id`, the code in the message); a second lesson for it (409 with the
  first's serial); a closed improvement's done *Lesson* countermeasure (201, the improvement row
  and its timeline unchanged: `updated_at` and the events count equal before and after).
- **Change:** each field; no change writes nothing; the tick on and off (`class_id` set, NULL); a
  class lesson changed by an engineer of another site (200); the same engineer unticks it (403
  naming the site); a machine lesson changed by an engineer of another site (404); `active` false
  then true; `action_id` set on an unlinked lesson (200), changed or cleared on a linked one (409).
- **List:** the node's own lessons and its class's, newest first; not a part's or the parent's; a
  retired one only in `retired`, and `retired` empty for an operator; `cover` the oldest photo, null
  without photos; `can_add` true for the engineer here, false for the operator; a node outside the
  units (404); no `equipment_id` (400).
- **Detail:** every field of § 6.3; `documents` oldest first; a class lesson opened by an operator of
  another site's unit (200, `machine` null); a machine lesson by them (404); `source` for an operator
  (who holds `improvement:read`) and `null` for the storekeeper; the flags for the engineer here, an
  engineer elsewhere (class lesson: `can_edit` true, `can_change_class` false).
- **The countermeasure:** the improvement detail's `lesson` after a create; `can_write_lesson` true for
  the engineer on an open *Lesson* countermeasure with no lesson, false after the lesson exists, on a
  cancelled one, on another kind, and for the technician owner.
- **The database down** (`db_down`, `backend/tests/conftest.py:213`): `POST /api/procedures` answers
  503.

### 8.3 Existing tests that break or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` (`:187-219`): `procedure:edit` joins the expected
  sets of `maint_engineer` and `maint_manager`, as S072 and S074 leave them; a new
  `test_procedure_keys` (engineer and manager hold it, IT admin and the floor roles do not; it is in
  `SITE_SCOPED`), beside `test_improvement_keys` (`:98`).
- `backend/tests/test_removed_documents_api.py`:
  `test_the_unit_scope_is_enforced_fail_closed` (`:136-149`): its last line asserts every row a user
  with no units sees is a model's; with the fifth branch a removed photo of a class lesson (from
  another test in the kept database) is visible too. The line becomes `item["owner"] in ("model",
  "procedure")`, with the comment "No units leaves model rows and class lessons' rows (S075 § 5.8)".
  New tests: a removed lesson photo listed with `owner` `"procedure"` and the serial; a machine
  lesson's row only for the manager of its unit; restore and purge by the manager.
- `backend/tests/test_documents_api.py`: green as it is (the owner CHECK keeps its name, `:490-500`).
  Gains `TestLessonDocuments`: the engineer uploads a photo (201) and the file lands under
  `DATA_DIR/procedures/<id>/`; a technician (403); the operator reads the list and the file (200);
  a reader of another unit, machine lesson (404); a class lesson's photo read by an operator of
  another site (200); an engineer of another site uploads to a class lesson (201) and to a machine
  lesson (404); retitle and remove; a retired lesson accepts a photo (201); the file is served with
  `nosniff`; and the CHECK case with `action_id` and `procedure_id` both set.
- `backend/tests/test_migration_v12.py` (`test_the_owner_check_keeps_its_name_and_counts_three_owners`,
  `:78`), `test_migration_v36.py` to `v40`: unchanged (each slices its own range).
- `backend/tests/test_modules.py` (`:40-41`): reads `LATEST_VERSION`, now 41; green.
- `backend/tests/test_improvements_api.py`: pins the list item's key set only (`:514`); green.
- `backend/tests/test_improvement_actions_api.py`: pins `owner` and `owners`' key sets, not an
  action's (`:128`, `:510`); green, plus § 8.2's new tests.

### 8.4 Automated (e2e)

None in this step: no screen changes. The detail's new fields are ignored by S071's screens. The
coder runs the whole browser suite at Normal once at the end (the removed-documents screen reads the
list, which gains a branch; `e2e/settings.spec.js` runs in it).

### 8.5 On a real device

None. S077 holds the Tamil checks on a phone and on paper.

### 8.6 Acceptance

- All unit suites green; the whole browser suite at Normal green once at the end.
- By API: OPL-001 "Keep the panel door shut" on HP003, ticked for its class, with a Tamil line and
  two photos, linked to IM-2026-10-001's *Lesson* countermeasure; an operator of SSVT.SHOP reads it
  on HP005's list.
- `docs/schema.md` and `docs/schema.html` show v41.

## 9. Open questions and assumptions

- **The split** (by the size rule, Phase 1). R05.6 in one brief listed about 29 code and test files
  with two concerns (a new master with a documents owner, and three screens with a new route). It is
  cut at the API, as R05.1, R05.3 and R05.4 were: this step the backend (17 code and test files),
  **S077** the screens. S075 is coded first; S077 builds on § 6 as written. Nothing is visible to
  users until S077.
- **Decisions the roadmap did not settle** (taken here as the recommended answer; none is defining):
  - Q1. The class lesson names its machine (D2). (b) exactly one of machine or class.
  - Q2. The countermeasure is done by its owner, not when its lesson exists (D8). (b) done on write.
  - Q3. `OPL-NNN`, one plant series (D3). (b) `OPL-YYYY-MM-NNN`.
  - Q4. Read with `equipment:read` (D5). (b) `improvement:read`.
- **Assumption:** no bound on the number of photos per lesson (the documents store has none for any
  owner). S077's page shows them all; a writer adds two or three (mock-up 06).
- **Assumption:** until S077, Settings › Removed documents draws a lesson's row as a node row
  (`frontend/src/views/settings/RemovedDocuments.vue`, its `v-else` branch); S077 § 5.5 gives it its
  own. S075 and S077 ship in one release, as S070 and S071.
- **Assumption:** v36–v41 reach production in one release (S072 § 9's assumption, extended). v41 is
  written for rows anyway (§ 4.1, § 8.1).
- **Assumption:** the TPM OPL types and ISO 27001 A.8.28 are *to verify*; the ISO 9001 clause numbers
  are the 2015 edition's.
- **Length:** about 730 lines, past the size rule's 600, as S067 (664) and S070 (about 700) were.
  It is one concern (the backend); most of it is § 5.5's site rule, § 5.6's lock sequences and
  § 5.8's documents owner. No further cut.
- **No defining question.**

## 10. Amendments

None.

## Review log

None yet.
