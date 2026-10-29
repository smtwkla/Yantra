```
Step: S070 — Countermeasures
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066, S067, S068 (in code review); S069 coded before S070
Status: Approved 30-10-2026 by KLA (delegated: R05 gate R, "start coding unless a defining question")
From: R05.3 (first half: the record and its API; the screens are S071)
```

# S070 — Countermeasures

## 1. What will be built

R05.1 gives an improvement its problem and tickets (S067, S068); R05.2 gives it the why-why and
the root cause (S069). **R05.3 adds what the team will do about it**: countermeasures, each with a
kind, an owner and a due date, marked done with what was done (ISO 9001 § 10.2.1 (c), § 2).
R05.3 is an L item with a backend and screens that can ship apart, so it is **split at the API**,
as R05.1 was (§ 9, *The split*). **This step builds the backend half**: the table, the rules, the
API and a fourth owner in the documents store. **S071**
(`docs/steps/S071-countermeasure-screens/1-brief.md`) builds the screens on § 6, as written here.

1. **Add a countermeasure** (`POST /api/improvements/<id>/actions`): a kind (one of six, Q3.1 a), a
   text ("what will be done"), an owner (Q3.2 a: any active person with a membership at the
   site, a person without a login too) and a due date. Engineers and managers of the improvement's site
   (`improvement:edit`), while the improvement is open.
2. **Change** an open countermeasure: kind, text, owner, due date (`PUT`).
3. **Cancel** an open countermeasure with a reason (`POST …/cancel`). It stays on the record
   (ISO 9001 § 7.5.3); nothing is deleted.
4. **Mark done** (`POST …/done`): what was done (`"What did you do?"`) and when (`"Done on"`, the
   S051 time field: *Now* sends nothing and the server's clock decides). The **owner** marks their
   own; an `improvement:edit` holder marks any, also for an owner without a login or without
   `improvement:read` (Q3.2 a). Which
   ones a user may mark is decided **by data** (the owner), not by a new key, as Plan § 3 decides
   `pm_job:work`.
5. **Overdue**: an open countermeasure whose due date is before today (IST) carries
   `overdue_days`, computed, never stored.
6. **A photo of the work** through the documents store: a fourth owner, the countermeasure
   (`equipment_documents.action_id`, the owner CHECK widened). The owner and `improvement:edit`
   holders add, retitle and remove; every reader of the improvement sees; files are served only
   through the permission-checked routes (§ Yantra Specifics, *Files*).
7. **My open countermeasures** for *Me › Open work* (`GET /api/improvements/actions/mine`).
8. **The owner choices** (`GET /api/improvements/owners?improvement_id=`).
9. **The improvement detail** gains `actions`, `action_counts` and `problem_at`.

**States of the improvement:** unchanged. It stays *Analysing* (S067 D3); R05.4 adds *Actions
open* and *Watching* (every countermeasure done or cancelled) and reads this step's states.

**After S070 and S071:** milestone 1. The team's countermeasures on the contactor case
(IM-2026-10-001) are owned, dated and tracked; the fitter's gasket job shows on his engineer's
list, the technician's on her own *Me*.

### Out of scope

- **Every screen** (S071): the countermeasures card, the dialogs, *Me › Open work*, the removed-
  documents row, the browser tests.
- Alerts: *countermeasure given to you*, *overdue* (R05.5). An owner without a login never gets one.
- The improvement states *Actions open*, *Watching*, the timeline and its history of edits
  (R05.4). This step keeps `created_*`, `updated_*`, `done_*` and `cancelled_*` on the row only
  (the departure S067 § 2 recorded).
- A *Preventive* countermeasure linked to a PM plan (R05.9, deferred): it is done when marked done,
  like every kind (gate R, consequences).
- A *Lesson* countermeasure linked to its lesson (R05.6); a checklist of machines for *Spread*.
- **Reopening** a done countermeasure, and deleting one (§ 9 Q1 answered (a), D5). Until R05.4, a
  wrong *done* stays on the record and the engineer adds a new countermeasure.
- A new key: none (D2).

## 2. Standards and practice

- **ISO 9001:2015 § 10.2.1 (c)** (nonconformity and corrective action). In plain words: after
  finding the causes, take the action needed, so the failure does not come back. Countermeasures
  are those actions, each with an owner and a date. (a) and (b) are S067 and S069; (d), checking
  that the action worked, is R05.4. Clause letters as Plan § 1 cites them; the next edition's
  numbers are *to verify* (R05 § Standards).
- **ISO 9001 § 10.2.2** (records). In plain words: keep a record of the actions taken and their
  result. Each countermeasure keeps who added it, who owns it, what was done, when, who recorded
  it, and the photo.
- **ISO 9001 § 7.5.3** (control of records). In plain words: records are kept, protected from
  change, and show who did what and when. A done or cancelled countermeasure cannot be changed; a
  cancel keeps the row with its reason. **Departure (recorded, as S067 § 2):** an edit of an open
  countermeasure keeps no earlier text; R05.4's timeline adds the history.
- **EN 13306** (maintenance terms; term numbers *to verify*). In plain words: *corrective
  maintenance* is done after a fault is found; *preventive maintenance* is done to lower the
  chance of failure; *improvement maintenance* raises reliability without changing the item's
  function. The kinds *Corrective*, *Preventive* and *Design-out* use these meanings.
- **TPM — maintenance prevention** (MP, design-out). In plain words: remove the failure mode
  instead of maintaining it, for example a sealed contact block. The kind *Design-out*.
- **TPM — horizontal deployment** (*yokoten*). In plain words: a fix found on one machine is
  applied to the similar machines before they fail too. The kind *Spread*.
- **TPM — one-point lesson** (training pillar). In plain words: one page, one point, mostly a
  picture, shown to the team at the machine. The kind *Lesson*; the lesson itself is R05.6.
- **The six kinds, one plain sentence each** (Q3.1 a; S071 shows these words):

  | Kind (`kind`) | For the floor | Rests on |
  |---|---|---|
  | *Correction* (`correction`) | Fixes this failure now, often already done on the ticket. | ISO 9001 § 10.2.1 (a) |
  | *Corrective* (`corrective`) | Removes the cause here, so this failure does not come back. | ISO 9001 § 10.2.1 (c); EN 13306 corrective |
  | *Preventive* (`preventive`) | Adds regular work that stops the failure before it happens. | EN 13306 preventive |
  | *Design-out* (`design_out`) | Changes the machine so this failure cannot happen. | TPM MP; EN 13306 improvement maintenance |
  | *Lesson* (`lesson`) | Teaches the team what was learned. | TPM one-point lesson |
  | *Spread* (`spread`) | Applies the fix to the similar machines. | TPM yokoten; ISO 9001 § 10.2.1 (b) "elsewhere" |

- **ISO 27001 A.5.15 (access control)** and **A.8.3 (information access restriction)**. In plain
  words: give each person only what their work needs; serve files only after checking who asks.
  The owner may record their own work without the engineer's key; photos are served only through
  the routes that check the improvement's access (S006's rule).

## 3. Where

S070 is coded after S069. Files marked **(S067)** are in the working tree now; S069 changes some
of them first, so line numbers in `backend/improvements.py`, `backend/improvements_core.py`,
`backend/local_db.py` and `backend/tests/conftest.py` are S067's working tree on 30-10-2026 and
may move; function and constant names are the anchors.

### Backend

- `backend/local_db.py`: migration **v38** (§ 4.1). S069 adds v37; S067's v36 starts at
  `backend/local_db.py:1104`. No `_PRECONDITIONS` entry (§ 4.1).
- `backend/improvements_core.py` **(S067)**: the kinds, the action states, the bounds and
  messages, `validate_action`, `validate_done`, `validate_cancel`, `due_date_error`,
  `done_time_error`, `overdue_days`, `action_counts`, `action_flags` (§ 5). It reuses
  `_text` (`backend/improvements_core.py:60`) and `_is_id` (`:56`).
- `backend/improvements.py` **(S067)**: the routes of § 6; the detail gains `actions` and
  `action_counts` and `problem_at`; `_lock_action` ((6c), § 5.6); the documents owner's four
  functions `read_action`, `read_action_for_change`, `lock_action_for_change`,
  `lock_action_for_purge` (§ 5.8); the LOCK ORDER note gains the countermeasure writes. Reuses
  `_lock_improvement` (`backend/improvements.py:160`), `_check_improvement` (`:152`),
  `_read_improvement` (`:139`), `_require_open` (`:169`), `_detail_response` (`:264`), and
  `people_at_site`, `person_at_site` from `tickets.py` (`backend/tickets.py:742`, `:365`).
- `backend/documents.py`: the owner `"action"` in `OWNERS` (`backend/documents.py:161`); a fourth
  stacked route decorator `_ACTION_DOCS` on every documents route; a fourth branch in
  `_removed_branches` (`:491`), with the shared alias `ticket_state` renamed `owner_state` in every
  branch and in `_JOIN_COLUMNS` (`:468`), and a column `action_kind`; the module docstring
  (owners, locks) (§ 5.8).
- `backend/file_store.py`: `_OWNER_FOLDERS` (`backend/file_store.py:23`) gains
  `"action": "improvement-actions"`.
- `backend/equipment.py`: docstring only. The global LOCK ORDER (`backend/equipment.py:9`) gains
  **(6c) the countermeasure row** after (6b); the documents.py bullet (`backend/equipment.py:50-53`,
  "exactly one owner lock … never two") gains: a countermeasure's document takes its improvement
  (6b) then the countermeasure (6c), in that order.
- `backend/tickets.py`: unchanged. No ticket lock is taken by this step.

### Tests

- `backend/tests/test_migration_v38.py` (new), on the pattern of `test_migration_v36.py`
  (`VERSIONS = list(range(20, 37))`, `backend/tests/test_migration_v36.py:17`, slices its own
  range; S069's `test_migration_v37.py` likewise), with documents of all three existing owners in
  the v37 database (the production shape).
- `backend/tests/test_improvements_core.py` **(S067)**: the new pure functions (§ 8.2).
- `backend/tests/test_improvement_actions_api.py` (new): every route of § 6 and the detail's new
  fields. A file of its own, as S069's `test_improvement_whys_api.py`.
- `backend/tests/test_documents_api.py`: the countermeasure as an owner (upload, list, serve,
  retitle, remove, restore, purge, the removed list); `TestOwnerCheckConstraint`
  (`backend/tests/test_documents_api.py:487`) gains the four-owner case (two of
  `ticket_id`, `action_id` refused) (§ 8.3).
- `backend/tests/conftest.py`: `improvement_actions` joins `_TABLES`
  (`backend/tests/conftest.py:162`), before `improvements` (the fixture deletes with
  `FOREIGN_KEY_CHECKS = 0`, so the order is for reading only).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the table `improvement_actions`, the column
  `equipment_documents.action_id` and its CHECK, the Mermaid overview (improvement_actions →
  improvements, people; equipment_documents → improvement_actions), the "migration v38" line.
- `docs/Plan.MD`: § 3, one paragraph: who marks a countermeasure done is decided by data (the
  owner), beside `pm_job:work`'s paragraph (`docs/Plan.MD:201`); § 4.6 or the R05 row of § 1, one
  line: until R05.4 a wrong *done* stays and the engineer adds a new countermeasure (§ 9 Q1). The screens (§ 6) are S071's.
- `docs/Maintenance-Philosophy.md` § 12 Glossary: the row *Countermeasure* and its six kinds in
  one line each (§ 2's table).
- `.claude/CLAUDE.md` § Step workflow, *Self-check, repo items* (2): the LOCK ORDER note of
  `improvements.py` now covers (6c); § Yantra Specifics, *Files (S006)*: a fourth owner, the
  countermeasure. (The § SMTW-Review spec map is S071's.)

**File count:** 11 code and test files (6 code: `local_db.py`, `improvements_core.py`,
`improvements.py`, `documents.py`, `file_store.py`, `equipment.py`; 5 tests), 4 docs.

## 4. Data model

### 4.1 Migration v38

```sql
-- Countermeasures (S070, R05.3): what the team does about an improvement's root cause, each
-- with a kind, an owner and a due date (ISO 9001 § 10.2.1 c).  Never deleted: a cancel keeps the
-- row with its reason (ISO 9001 § 7.5.3).
CREATE TABLE IF NOT EXISTS improvement_actions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    improvement_id  INT NOT NULL,
    kind            ENUM('correction','corrective','preventive','design_out','lesson','spread') NOT NULL,
    text            VARCHAR(500) NOT NULL,
    owner_id        INT NOT NULL,
    due_date        DATE NOT NULL,
    state           ENUM('open','done','cancelled') NOT NULL DEFAULT 'open',
    done_text       VARCHAR(1000) NULL,
    done_at         DATETIME NULL,
    done_by         VARCHAR(100) NULL,
    cancel_reason   VARCHAR(500) NULL,
    cancelled_at    DATETIME NULL,
    cancelled_by    VARCHAR(100) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    updated_at      DATETIME NULL,
    updated_by      VARCHAR(100) NULL,
    KEY ix_improvement_actions_improvement (improvement_id, id),
    KEY ix_improvement_actions_owner_state (owner_id, state, due_date),
    CONSTRAINT fk_improvement_actions_improvement FOREIGN KEY (improvement_id) REFERENCES improvements (id),
    CONSTRAINT fk_improvement_actions_owner FOREIGN KEY (owner_id) REFERENCES people (id),
    CONSTRAINT chk_improvement_actions_done
        CHECK ((state = 'done') = (done_text IS NOT NULL AND done_at IS NOT NULL AND done_by IS NOT NULL)),
    CONSTRAINT chk_improvement_actions_cancelled
        CHECK ((state = 'cancelled') = (cancel_reason IS NOT NULL AND cancelled_at IS NOT NULL
                                        AND cancelled_by IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A photo or document of a countermeasure: the fourth owner of the documents store.
ALTER TABLE equipment_documents
    ADD COLUMN IF NOT EXISTS action_id INT NULL AFTER ticket_id,
    ADD KEY IF NOT EXISTS ix_equipment_documents_action (action_id, removed_at),
    ADD CONSTRAINT fk_equipment_documents_action
        FOREIGN KEY IF NOT EXISTS (action_id) REFERENCES improvement_actions (id);
ALTER TABLE equipment_documents DROP CONSTRAINT IF EXISTS chk_equipment_documents_owner;
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) + (ticket_id IS NOT NULL)
           + (action_id IS NOT NULL) = 1);
```

- **The CHECKs on `improvement_actions`** have the v21 shape (`chk_tickets_plan`): a done row
  carries its text, time and recorder; a row that is not done never carries all three. The same
  for cancelled. The shell writes each set together or not at all, so the looser form loses
  nothing (BR1-02).
- **`ix_improvement_actions_owner_state`** serves *my open countermeasures* (`owner_id = ? AND
  state = 'open' ORDER BY due_date`).
- **The owner CHECK** is dropped and added again with its name, as the v12 squash did
  (`backend/tests/fixtures/migrations_v13.py:522-523`). Every existing row has exactly one of the
  three owners (the old CHECK held it) and `action_id` NULL, so it meets the new CHECK.
- **Re-run safety:** `IF NOT EXISTS` on the table, the column, the key, the foreign key (as v35)
  and the CHECK (as v21, `backend/local_db.py:613`); `DROP CONSTRAINT IF EXISTS`. A half-applied
  v38 (dropped, not added) runs again and adds it. `ADD KEY IF NOT EXISTS`: S069's v37 is its
  first use, and its re-run test proves it (S069 BR1-10); § 8.1 here proves it again.
- **No precondition** (the v21 reasoning, `backend/local_db.py:600`): a new table; on
  `equipment_documents` a nullable column, a key and a CHECK that every existing row meets.
  Nothing is converted or dropped. The nullable column add is instant; the foreign-key add and
  the CHECK scan the existing documents rows (production holds documents and photos); § 8.1 runs
  v38 on a v37 database with rows of all three owners.
- **Rollback:** a release before v38 never reads `improvement_actions`; its documents
  queries name their columns and their removed-list branches join their own owner, so a
  countermeasure's photo row is invisible to it.
- **Text:** utf8mb4; MariaDB counts characters in `VARCHAR(n)` (S067 § 4.1), so Tamil fits.
- **Shared with later steps:** R05.6, R03.6 and R03.17 each widen the same CHECK the same way
  (R05 § Order, *Not in parallel*).

### 4.2 What is computed, never stored

- `overdue_days` (§ 5.4), `action_counts` (§ 5.4), each countermeasure's `can_change`,
  `can_mark_done` and `can_add_photo` (§ 5.7).
- `owner.has_login` (`people.username IS NOT NULL`, `backend/local_db.py:218`), `owner.active`
  and `owner.may_own` (today a member of the site), read for all the owners in one query
  (`WHERE p.id IN (…) AND ms.site_id = %s`, no query per row); `problem_at`, the earliest linked
  ticket's `occurred_at`; the names of `created_by`, `done_by`, `cancelled_by` (the person whose login it
  is, else the login, as S067's `created_by_name`).

## 5. Rules

### 5.1 Where a write is allowed

As S067 § 5.5 and S069 § 5.1, in this order: (1) the improvement inside S067's access predicate
(`improvement:read` units), else 404; (2) the writer's right at the improvement's site (§ 5.7),
else 403; (3) the improvement open (`improvements_core.is_open`), else 409 "This improvement is
closed" (`IMPROVEMENT_CLOSED`); (4) the countermeasure's own state (§ 5.5), else 409.

### 5.2 The fields

**Add and change** (`validate_action(body, creating)` for `clean_body`,
`backend/api_common.py:121`):

| Field | `POST` | `PUT` | Rule and message (field) |
|---|---|---|---|
| `kind` | required | optional, not `null` | one of `ACTION_KINDS`: "Choose the kind" (`kind`) |
| `text` | required | optional, not `null` | text, trimmed, 1–500: "Enter what will be done" / "What will be done: up to 500 characters" / "What will be done must be text" (`text`) |
| `owner_id` | required | optional, not `null` | integer ≥ 1, not a boolean: "Choose the owner" (`owner_id`); then the shell, § 5.3 |
| `due_date` | required | optional, not `null` | `YYYY-MM-DD` (`date.fromisoformat` after trim): "Enter the date as YYYY-MM-DD" (`due_date`, `LABOUR_DATE_FORMAT`, `backend/tickets_core.py:361`); then `due_date_error`, § 5.3 |

- An absent field on a `PUT` stays as it is; a field equal to the stored value is not written; a
  `PUT` that changes nothing answers 200 and writes nothing (no `updated_at`), as S067 § 5.2.
  Unknown fields, the state and the done and cancel fields are ignored.
- **At most 30 countermeasures** per improvement, cancelled ones counted (`ACTIONS_MAX`): a `POST`
  on an improvement with 30 is 409 "An improvement holds up to 30 countermeasures. Change or
  cancel one instead." (no field). A bound for every input (self-check 6); a team that needs more
  is splitting one problem into many.

**Mark done** (`validate_done(body, _creating)`):

| Field | Rule and message (field) |
|---|---|
| `done_text` | required, text, trimmed, 1–1000: "Say what you did" / "What you did: up to 1000 characters" / "What you did must be text" (`done_text`) |
| `done_at` | optional; absent or `null` → the server's IST now (the S051 *Now* tick sends nothing); else `parse_event_time` (`backend/tickets_core.py:101`, "Enter the time as YYYY-MM-DD HH:MM"), then `done_time_error`, § 5.3 (`done_at`) |

**Cancel** (`validate_cancel(body, _creating)`):

| Field | Rule and message (field) |
|---|---|
| `reason` | required, text, trimmed, 1–500: "Say why it is cancelled" / "Reason: up to 500 characters" / "Reason must be text" (`reason`) |

### 5.3 Owner, due date, done time

- **The owner** (Q3.2 a as approved, D3): an **active person with a membership at the
  improvement's site, any role**, a person without a login too. Checked with
  `person_at_site(cur, owner_id, site_id)` (`backend/tickets.py:365`) is not None; else 400 "Choose
  a person of this site" (`owner_id`). On a `PUT` only when `owner_id` changes (as S067's lead,
  BR1-07 there), so an owner who has since left the site stays until someone picks another; the
  detail's `owner.active` and `owner.may_own` tell S071 to mark them.
- **An owner who cannot act on it:** an owner without a login, and an owner whose role at the site
  lacks `improvement:read` (today the storekeeper), never see the countermeasure: `mine` needs
  `improvement:read`, and their `can_mark_done` is never true. An `improvement:edit` holder marks
  the work done for them, as Q3.2 a says for the owner without a login.
- **The due date** (`due_date_error(due, problem_date, today)`): from the date of the earliest
  linked ticket (`problem_at`'s date) to today + `PLANNED_DATE_MAX_DAYS` (365,
  `backend/tickets_core.py:327`). Before: "Choose a date from 28-10-2026, the day the problem
  happened" (the date written DD-MM-YYYY); after: "Choose a date within a year"
  (`PLANNED_DATE_TOO_FAR`, `backend/tickets_core.py:370`). A date in the past is allowed: a
  *Correction* done on the ticket on 28-10 reads "due 28-10, done 28-10". On a `PUT` checked only
  when it changes. The same floor as the done time (D7).
- **The done time** (`done_time_error(done_at, now, problem_at)`): not more than `FUTURE_SKEW`
  (5 minutes, `backend/tickets_core.py:52`) ahead of now: "That time is in the future"
  (`EVENT_TIME_FUTURE`); not before the earliest linked ticket's `occurred_at` (`problem_at`):
  "Not before the problem happened, 28-10-2026 15:15". No 7-day limit (D6): the
  *Correction* of a ticket fixed weeks before the analysis is recorded truthfully.

### 5.4 Overdue and counts (pure)

- `overdue_days(state, due_date, today)`: `(today - due_date).days` when `state == "open"` and the
  difference is above 0, else 0. Due today is not overdue. `today` is the IST date (the shell's
  `_now().date()`, as `tickets._today`, `backend/tickets.py:181`).
- `action_counts(actions)`: `{open, done, cancelled, overdue}`. S071's card header "2 of 6 done"
  reads it; R05.4's *Watching* rule ("every countermeasure done or cancelled") will read `open`.

### 5.5 States: actor × state × already there

`ACTION_STATES = ("open", "done", "cancelled")`. Done and cancelled are final (D5).

| Action | Who (§ 5.7) | from `open` | from `done` | from `cancelled` |
|---|---|---|---|---|
| Change (`PUT`) | `improvement:edit` at the site | 200 | 409 "Only an open countermeasure can be changed" | the same 409 |
| Mark done | the owner, or `improvement:edit` at the site | 200, `done` | 409 "This countermeasure is already done" | 409 "This countermeasure was cancelled" |
| Cancel | `improvement:edit` at the site | 200, `cancelled` | 409 "A done countermeasure cannot be cancelled" | 409 "This countermeasure is already cancelled" |
| Add a photo, retitle, remove a photo | the owner, or `improvement:edit` at the site | 201 / 200 / 204 | the same | 409 "This countermeasure was cancelled" |

- Every row also needs the improvement open (§ 5.1 (3)), checked before the countermeasure's state.
- A countermeasure of another improvement, or an unknown id, in a nested route: 404 "Not found".
- **Mark done writes** `state = 'done'`, `done_text`, `done_at` (sent, or now), `done_by =
  actor()`. **Cancel writes** `state = 'cancelled'`, `cancel_reason`, `cancelled_at = now`,
  `cancelled_by = actor()`. Neither stamps `updated_*`: those record the last change of the
  planned fields. `done_by` is who recorded it; when that is not the owner (the engineer for the
  fitter without a phone), the detail shows both (`done_by_name`, `owner.name`).

### 5.6 Locks

The database runs REPEATABLE READ. Each route takes its locking reads first; every decision comes
from a locking read or a plain read made after the lock that guards it.

**The global order** (`backend/equipment.py:9`): … (6) the serial counter → (6b) the improvement
row → **(6c) the countermeasure row (new)** → (7) the ticket row. A countermeasure write takes
(6b) `FOR UPDATE` first, then (6c) `FOR UPDATE` (`_lock_action`: `SELECT id, improvement_id, state,
kind, text, owner_id, due_date FROM improvement_actions WHERE id = %s AND improvement_id = %s FOR
UPDATE`; 404 when missing). No route of this step takes a ticket lock.

**Add** (`POST /api/improvements/<id>/actions`), one `transaction`:

1. (6b) the improvement `FOR UPDATE` (`state`, `unit_id`); 404 when missing.
2. Plain reads, the transaction's first: predicate 404, `improvement:edit` at the site 403, open
   409, the count 409 (`ACTIONS_MAX`), the owner (400), `problem_at` (links change only under
   (6b)) and the due date (400).
3. Insert (its foreign keys take shared locks on the improvement, held exclusive, and on the
   owner's `people` row).
4. The detail, read inside the transaction.

**Change** (`PUT …/actions/<action_id>`): (1) (6b); (2) (6c); (3) plain reads: predicate 404, key
403, open 409, the countermeasure's state from (6c) 409, owner and due date (with `problem_at`)
when changed (400);
(4) `update_row` (a new owner takes a shared lock on that person).

**Mark done** (`POST …/actions/<action_id>/done`): (1) (6b); (2) (6c) (`state`, `owner_id`);
(3) plain reads: predicate 404, the right by data (§ 5.7) 403, open 409, the state from (6c) 409,
`problem_at` (`SELECT MIN(t.occurred_at)` over the improvement's links: links change only under
(6b)), the done time 400; (4) the `UPDATE`.

**Cancel** (`POST …/actions/<action_id>/cancel`): (1) (6b); (2) (6c); (3) plain reads: predicate
404, key 403, open 409, state 409; (4) the `UPDATE`.

**A document of a countermeasure** (§ 5.8): the documents store takes **one owner lock**; for a
countermeasure that is (6b) then (6c), its improvement and itself:
1. a plain read of `improvement_actions.improvement_id` (it never changes; 404 when missing);
2. (6b) `FOR UPDATE` (`state`);
3. (6c) `FOR UPDATE` (`state`, `owner_id`);
4. plain reads: predicate 404, the right (the write key: owner or `improvement:edit`; restore and
   purge: `equipment:purge_documents` at the site) 403, then for writes and restore the improvement
   open and the countermeasure not cancelled, 409, all from the locked rows of 2 and 3;
5. the `equipment_documents` statement (an insert takes a shared lock on the countermeasure, held
   exclusive).
Step 1 starts the snapshot before the locks; nothing is decided from a plain read of a row the
locks guard: the states and the owner come from 2 and 3; the predicate is a plain read, as every
access check.

**Reads** (detail, mine, owners): plain, no lock.

**No new deadlock cycle, checked against the notes:**
- (6b) → (6c): every writer of a countermeasure takes its improvement first; nothing takes a
  countermeasure and then an improvement. The documents path reads `improvement_id` with a plain
  read (no lock) before (6b).
- (6c) → `equipment_documents` rows: nothing else locks those (documents.py's note,
  `backend/documents.py:28-35`).
- *Tickets:* no ticket lock here; ticket writes never touch improvements or countermeasures.
- *The person row:* an add or a change of owner takes shared locks only on the improvement (held)
  and the owner's `people` row, never on a unit. masters.py's person edit (person → memberships →
  person_units → units) never waits on an improvement or a countermeasure row. **No cycle**
  (S067's accepted one ran through the unit's foreign-key lock, which this step does not take).
- *S069's freeze:* a cause's code change counts improvements `LOCK IN SHARE MODE`; this step
  never locks a cause.

The coder writes this into improvements.py's LOCK ORDER note, adds (6c) to equipment.py's order,
and names the countermeasure lock in documents.py's *Locks* paragraph.

### 5.7 Permissions (owner by data)

No new key (D2). S067's keys, site-scoped:

| Action | Route decorator | Then, at the improvement's site |
|---|---|---|
| Read the countermeasures and their photos | `improvement:read` | the predicate (404) |
| Add, change, cancel | `improvement:edit` | predicate 404, `require_perm_at(EDIT_KEY, site)` 403 |
| Mark done; add, retitle, remove a photo | `improvement:read` | predicate 404; then **`has_perm_at(EDIT_KEY, site)` or `current_person_id(cur) == owner_id`** (`backend/auth_utils.py:439`, `:314`), else 403 "Only the owner, or an engineer or manager of this site, can do this" |
| Restore, purge a removed photo | `equipment:purge_documents` | predicate 404, the key at the site 403 (as every owner, S008) |
| My open countermeasures | `improvement:read` | the predicate, as a filter |
| The owner choices | `improvement:edit` | predicate 404, the key at the site 403 |

- **Owner by data** (as `pm_job:work`, Plan § 3, `docs/Plan.MD:201`): the owner is
  `people.id`; the user is the owner when their own Team record (`current_person_id`) is it. A
  user with no Team record is the owner of nothing. The routes' `improvement:read` decorator and
  the predicate come first, so an owner without the key (the storekeeper) is refused there and
  never reaches the owner rule (§ 5.3). IT admin (no person) never is; IT admin holds
  `improvement:read` only, so reads and nothing more.
- **Flags in the detail and in *mine*** (`action_flags`, pure, fed `is_open`, the state, `may_edit`
  and `is_owner`): `can_change` = improvement open and state open and `may_edit`;
  `can_mark_done` = improvement open and state open and (`may_edit` or `is_owner`);
  `can_add_photo` = improvement open and state not cancelled and (`may_edit` or `is_owner`). S071
  shows each control from these, so no button ends in a 403.
- **Identity:** no field here changes who can log in or what anyone sees. The owner's name shows
  to every reader; no login, role or email. A request with no identity gets `require_perm`'s 401,
  never admin.

### 5.8 Photos: the documents store's fourth owner

- `OWNERS["action"] = Owner("action_id", "/api/improvements/actions/{}/documents", "countermeasure",
  read_action, read_action_for_change, lock_action_for_change, lock_action_for_purge,
  "improvement:read", "improvement:read", "equipment:purge_documents")`, the four functions in
  `improvements.py` with the ticket's names (`documents.py` imports them, as it imports
  `read_ticket`; `improvements.py` never imports `documents.py`).
- **The write key is `improvement:read`** (D4): `_owner_key` (`backend/documents.py:183`) checks
  the owner's write key held at any site, and a technician owner holds only `improvement:read`.
  The narrower rule is applied at the improvement's site by `read_action_for_change` and
  `lock_action_for_change`, which **branch on the key** and say so in their docstrings:
  `improvement:read` (the write key) → the owner or `improvement:edit` at the site (§ 5.7); the
  purge key (restore) → `require_perm_at(key, site)`. `lock_action_for_purge` always applies
  `require_perm_at(key, site)`.
- **Every kind** (`photo`, `document`) as every owner (S018 removed photos-only). S071's *Mark done*
  offers photos.
- **Routes**: `_ACTION_DOCS = "/improvements/actions/<int:owner_id>/documents"` and `_FOR_ACTION`
  stacked on list, upload, file, thumb, title, remove, restore, purge. The paths cannot meet
  `improvements_bp`'s `/<int:improvement_id>`: `actions` is not an integer (the S067 BR2-05 rule).
- **Files**: `DATA_DIR/improvement-actions/<action_id>/` (`file_store._OWNER_FOLDERS`), served only
  by `_serve` after the predicate (ISO 27001 A.8.3); `X-Content-Type-Options: nosniff` and
  `private` caching as for every owner (`backend/documents.py:366-369`). The file type is still
  decided from the first bytes (`detect_file_type`), not the name or the client's type (S006).
- **Removed list** (`GET /api/equipment/removed-documents`): a fourth branch, scoped by the
  improvement's unit to the units where `equipment:purge_documents` is held; `owner` `"action"`,
  `name` the improvement's serial ("IM-2026-10-001"), `action_kind` the kind's code (NULL in the
  other branches; S071 labels it from its one label table, BR1-03), `unit`, and `state` = the
  countermeasure's state. The UNION's shared alias `ticket_state` becomes `owner_state` in every
  branch and in `_JOIN_COLUMNS`, so `_removed_item` reads one named column for both owners; the
  item's key stays `state`. S071 refuses restore on a cancelled one with a reason, as for a closed
  ticket (`frontend/src/views/settings/RemovedDocuments.vue:85`). The search `q` matches the
  serial, the title and the original name.
- **A removed photo** keeps its row and file (S006); it is not listed in the detail.

### 5.9 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing. Uploads keep
S006's order (files written with no transaction open; a failed insert removes them). No
background task, no alert.

## 6. API

All under S067's `improvements_bp` (`/api/improvements`), ids `<int:…>`. Every write answers with
the whole improvement detail (S068 BR1-09: one answer, one page copy).

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `POST /api/improvements/<id>/actions` | `improvement:edit` | `{kind, text, owner_id, due_date}` | 201, the detail; 400, 403, 404, 409 per § 5 |
| `PUT /api/improvements/<id>/actions/<action_id>` | `improvement:edit` | `{kind?, text?, owner_id?, due_date?}` | 200, the detail |
| `POST /api/improvements/<id>/actions/<action_id>/done` | `improvement:read` + owner by data | `{done_text, done_at?}` | 200, the detail |
| `POST /api/improvements/<id>/actions/<action_id>/cancel` | `improvement:edit` | `{reason}` | 200, the detail |
| `GET /api/improvements/actions/mine` | `improvement:read` | — | `{items, total}` (below) |
| `GET /api/improvements/owners` | `improvement:edit` | `improvement_id` (required: 400 "improvement_id is required") | `{items: [{id, name}]}` by name |
| `…/api/improvements/actions/<action_id>/documents` (list, upload, `/<doc_id>/file`, `/thumb`, `PUT`, `DELETE`, `/restore`, `/purge`) | § 5.7 | as every owner (S006, S008) | as every owner |
| `GET /api/improvements/<id>` (S067) | `improvement:read` | — | gains `actions`, `action_counts`, `problem_at` |

**`actions`** (by `id`, the order they were added): `[{id, kind, text, owner{id, name, active,
has_login, may_own}, due_date, state, overdue_days, done_text, done_at, done_by_name,
cancel_reason, cancelled_at, cancelled_by_name, created_at, created_by_name, updated_at,
can_change, can_mark_done, can_add_photo, documents: [{id, kind, title, has_thumb}]}]`. The
documents of all the improvement's countermeasures are read in one query (`WHERE action_id IN
(…) AND removed_at IS NULL`, newest first), no N+1.

**`action_counts`**: `{open, done, cancelled, overdue}`.

**`problem_at`**: the earliest linked ticket's `occurred_at` (the floor of the due date and the
done time, § 5.3); S071 sets the date input's `min` from it.

**`mine`**: the user's open countermeasures (`owner_id = current_person_id`, `state = 'open'`) of
open improvements inside the predicate, by `due_date, id`; `LIMIT 200` (`MAX_PER_PAGE`) with
`total` (a person owns a handful; the bound is self-check 6). Item: `{id, kind, text, due_date,
overdue_days, can_mark_done, can_add_photo, improvement{id, serial, title, machine{id, code,
name}}}`. A user with no Team record gets `{items: [], total: 0}`.

**`owners`**: `people_at_site(cur, site_id)` (`backend/tickets.py:742`), unfiltered (any role,
§ 5.3), answered as `{id, name}`.

## 7. Design decisions

- **D1. Countermeasures in a table of their own, nested under the improvement** (as R05.3 says).
  Their routes live in `improvements.py`. Rejected: a blueprint of their own (one more module for
  routes that always need the improvement's lock and predicate).
- **D2. No new key; the owner by data.** `improvement:edit` plans the work; the owner records their
  own work with `improvement:read`, as Plan § 3 decides `pm_job:work`. Rejected:
  `improvement:work` for the technician and up (it would let any technician mark any
  countermeasure done; the owner is the one who did it).
- **D3. The owner is any active member of the site** (Q3.2 a as approved; § 9 Q2 answered (b)).
  The storekeeper owns "keep two spare contact blocks in stock" truthfully; like the owner without
  a login, they cannot open it, and an engineer marks it done. Rejected: only people who hold
  `improvement:read` (the work would be credited to the engineer, the downside Q3.2 b was
  rejected for).
- **D4. The countermeasure joins the documents store as a fourth owner, with `improvement:read` as
  its write key and the narrower rule in its lock function.** One upload path, one file layout,
  one removed list (S006, S008, S017's pattern), no second file store. Rejected: a photo column on
  the countermeasure (a second upload path with its own checks); `improvement:edit` as the write
  key (the technician owner could not add the photo of their own work).
- **D5. Done and cancelled are final; nothing is deleted.** A wrong countermeasure is cancelled with
  a reason; the record of what was planned stays (ISO 9001 § 7.5.3). Rejected: delete (loses the
  record); reopen a done one (§ 9 Q1: R05.4's timeline is the place for undo, with its history).
- **D6. The done time's floor is the problem, not 7 days back.** A *Correction* is often done on
  the ticket before the improvement exists; the earliest linked ticket bounds a typo. Rejected:
  tickets' 7-day window (refuses the true time of a correction); no floor (a typo of a year).
- **D7. The due date may lie in the past, back to the problem** (the earliest linked ticket's
  date, the done time's floor too). The team records a correction already done, with its true
  dates. Rejected: today or later only, as a ticket's planned date (refuses that record); the
  improvement's start as the floor (a correction done before it would read due after done).
- **D8. Mark done does not stamp `updated_*`.** `done_*` record who recorded the work and when;
  `updated_*` keep the last change of the plan (kind, text, owner, due). Rejected: one stamp for
  both (the plan's last change is lost on the done).
- **D9. *Mine* is its own route, not a filter of the list.** It answers countermeasures across
  improvements with the improvement's serial and machine, the shape *Me* needs, in one query.
  Rejected: `GET /api/improvements?owner=me` (answers improvements, not countermeasures).
- **D10. Flags from the server** (`can_change`, `can_mark_done`, `can_add_photo`). The owner rule
  is data the frontend cannot know (it needs the Team record and the site's keys). Rejected:
  the frontend comparing `userPersonId` with `owner.id` (a second copy of the rule).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v38.py`)

- A fresh database: `improvement_actions` with its keys, both CHECKs and foreign keys;
  `equipment_documents.action_id`, `ix_equipment_documents_action`,
  `fk_equipment_documents_action`; `chk_equipment_documents_owner` names `action_id`.
- **A v37 database with documents of all three owners** (a node, a model, a ticket), an
  improvement and a why: every row kept, `action_id` NULL, the new CHECK met.
- The CHECKs: a row `done` without `done_text` refused; `open` with `done_text`, `done_at` and
  `done_by` all set refused; `cancelled` without a reason refused; `open` with all three cancel
  fields set refused; a document with `ticket_id` and `action_id` refused (4025).
- A re-run of v38 changes nothing (`_schema()` equal); a half-applied v38 (the CHECK dropped, not
  added) runs again and adds it.

### 8.2 Backend (`test_improvements_core.py`, `test_improvement_actions_api.py`)

**Core:** `validate_action` (each message of § 5.2: missing, empty after trim, 500 / 501, a
number, an unknown kind, `null` on a `PUT`, a boolean `owner_id`, `due_date` "31-10-2026" and
"2026-02-30"); `validate_done` (1000 / 1001, `done_at` absent and `null` → not given, a bad
format); `validate_cancel`; `due_date_error` (the problem's date passes, the day before refused
with the date in DD-MM-YYYY, today + 365 passes, + 366 refused); `done_time_error` (now + 5 min passes,
+ 6 refused, equal to `problem_at` passes, a minute before refused with the time);
`overdue_days` (due yesterday 1, today 0, done 0, cancelled 0); `action_counts`; `action_flags` (each combination of open / done /
cancelled, improvement open, `may_edit`, `is_owner`).

**API**, each test with its own ticket and improvement (S067's set-up through
`ticket_helpers.py`), so the kept worker database gives the starting state. "Another site" and
"a key missing here" as S067 § 8.2 (BR1-03 there).
- **Add:** each of the six kinds (201, state open, `created_by_name`); an owner without a login
  (201, `has_login` false); a storekeeper (201; the engineer then marks it done, 200); an inactive
  person, a person of another site (400 on `owner_id`); the due-date bounds (400); the 31st (409); an operator (403); an operator here who
  is engineer elsewhere (403); an engineer of another site (404).
- **Change:** each field; no change writes nothing; an owner who left the site kept when unchanged,
  refused when sent anew; a done one and a cancelled one (409).
- **Mark done:** the owner (a technician, `improvement:read` only) marks their own (200, `done_by`
  is their login, `updated_at` unchanged); a technician who is not the owner (403); an engineer
  for an owner without a login (200, `done_by_name` the engineer, `owner.name` the fitter); with
  `done_at` an hour ago (stored); in the future (400); before the first ticket's time (400 with
  the time); already done (409), cancelled (409); a missing `done_text` (400).
- **Cancel:** with a reason (200); no reason (400); done (409); already cancelled (409); the owner
  technician (403).
- **Detail:** `actions` by id with `overdue_days` (the test's ticket happened today, so the API
  refuses an earlier due date: the test moves the countermeasure's `due_date` 2 days back with
  `db_rows`, `backend/tests/conftest.py`, then reads 2 days); `action_counts`; `problem_at`; the
  flags for the engineer, the owner and an operator who owns nothing; `documents` of a
  countermeasure; `owner.may_own` false after the owner's membership is removed.
- **Mine:** the owner's open ones by due date; not the done or cancelled ones; not another
  person's; IT admin (no Team record) gets an empty list; an operator moved off the unit (outside
  the predicate) no longer sees theirs.
- **Owners:** every active person of the site, the storekeeper and people without a login
  included, by name; no `improvement_id` (400); another site (404); a key missing here (403).
- **The database down** (`db_down`, `backend/tests/conftest.py:213`): `POST …/actions` answers 503.

### 8.3 Existing tests that break or run again

- `backend/tests/test_documents_api.py`: green as it is (the owner CHECK keeps its name and still
  refuses two owners and none, `:487-500`). Gains a class `TestActionDocuments` on the pattern of
  the ticket owner's (`:504` on): the owner technician uploads a photo (201); a non-owner
  technician (403); the engineer (201); the operator reads the list and the file (200), a reader
  of another unit (404); upload on a cancelled countermeasure (409); a document of another
  countermeasure's id (404); retitle and remove by the owner, and by a technician who is not the
  owner (403); restore and purge by the manager; restore on a cancelled countermeasure (409); the
  removed list shows the row with `owner` `"action"`, the serial and `action_kind`, and the ticket
  rows still carry `state`; the file is served with `nosniff`. And the CHECK case with `ticket_id` and `action_id` both set.
- `backend/tests/test_migration_v12.py`: `test_the_owner_check_keeps_its_name_and_counts_three_owners`
  (`:78`) reads the migrated schema; it asserts the name and `ticket_id` only, so it stays green
  (its name says "three"; the coder leaves it, a frozen-history test).
- `backend/tests/test_migration_v36.py`, `v37`: unchanged (each slices its own range).
- `backend/tests/test_rbac.py` `test_role_matrix`: unchanged (no new key).
- `backend/tests/test_improvements_api.py`: the detail gains two fields; it pins the **list**
  item's key set only (S069 § 6), so it stays green.

### 8.4 Automated (e2e)

None in this step: no screen changes, and no spec reads the detail's new fields. The browser tests
of countermeasures are S071's. The coder runs the whole browser suite at Normal once at the end,
as the step workflow asks.

### 8.5 On a real device

None. S071 holds the camera check.

### 8.6 Acceptance

- All unit suites green; the whole browser suite at Normal green once at the end.
- By API: the six countermeasures of the contactor case can be added to IM-2026-10-001; the
  technician marks hers done with a photo; the engineer marks the fitter's.
- `docs/schema.md` and `docs/schema.html` show v38.

## 9. Open questions and assumptions

- **The split** (by the size rule, Phase 1). R05.3 in one brief listed about 24 code and test files
  and passed 600 lines with two concerns (a backend with the documents owner, and the screens on
  two pages). It is cut at the API, as R05.1 was (S067 BR1-01): this step the backend (11 code and
  test files), **S071** the screens. S070 is coded first; S071 builds on § 6 as written. Nothing is
  visible to users until S071.
- **Q1. Reopen a done countermeasure?** Answered 30-10-2026: **(a) no**. A wrong *done* stays
  until R05.4; the engineer adds a new countermeasure; R05.4 brings undo with its timeline (D5).
- **Q2. Who may own a countermeasure?** Answered 30-10-2026: **(b)**, gate R's Q3.2 (a) as
  approved: any active member of the site (D3, § 5.3).
- **Assumption:** the improvement stays *Analysing* while countermeasures are added; R05.4 decides
  whether countermeasures need a root cause first (Q2.2 a puts the root cause before *Watching*,
  not before countermeasures).
- **Assumption:** *Me › Open work* reads `mine` beside the tickets (S071). **R03.4** adds PM jobs
  to the same tab later; whichever comes second merges into the first's layout (R05 § Order,
  *Not in parallel*).
- **Assumption:** the clause numbers of EN 13306 and the next ISO 9001 edition are *to verify*.
- **Length:** about 660 lines, past the size rule's 600, as S067 (664) was. It is one concern (the
  backend), most of it § 5.6's lock sequences and § 5.8's documents owner; no further cut.
- **No defining question:** Q1 and Q2 were choices inside gate R's answers; both are answered.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 1 (items 1, 4, 9; *Out of scope*), § 3 (backend,
docs), § 4.1 (CHECK note, no-precondition note, rollback), § 4.2, § 5.3, § 5.6 (Add, Change, the
documents path, the person row), § 5.7, § 5.8, § 6, § 7 D3 and D7, § 8.1, § 8.2, § 8.3, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (b): the owner is any active member of the site, as gate R's Q3.2 (a) was approved. An owner without `improvement:read` (the storekeeper) never sees it; an `improvement:edit` holder marks it done. `may_own` is now "a member of the site"; `owners` is unfiltered. § 9 Q2 answered (b), Q1 answered (a). § 1, § 4.2, § 5.3, § 5.7, § 6, D3, § 8.2, § 9. |
| BR1-02 minor | Accepted (a): the v21 CHECK shape stays; § 4.1's text and § 8.1's test corrected. |
| BR1-03 minor | Accepted (a): the removed-list branch sends `name` = the serial and `action_kind`; S071 labels it. § 3, § 5.8. |
| BR1-04…BR1-16 nits | Accepted: BR1-04 no cycle on the person row (§ 5.6); BR1-05 equipment.py's documents bullet (§ 3); BR1-06 the four functions named, the key branch in their docstrings (§ 3, § 5.8); BR1-07 `owner_state` alias (§ 3, § 5.8); BR1-08 the owners' memberships in one query (§ 4.2); BR1-09 `PLANNED_DATE_MAX_DAYS`, and one floor for both dates, the earliest linked ticket, sent as `problem_at` (§ 5.3, § 5.6, § 6, D7, § 8.2); BR1-10 "Not before the problem happened, …"; BR1-11 "…, or an engineer or manager of this site, …"; BR1-12 the two document tests (§ 8.3); BR1-13 the predicate a plain read (§ 5.6); BR1-14 the rebuild claim corrected (§ 4.1); BR1-15 "a release before v38"; BR1-16 the line numbers. |
