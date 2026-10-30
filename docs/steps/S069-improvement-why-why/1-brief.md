```
Step: S069 — Why-why and the root cause
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066, S067 (snapshot e0a89f0, in code review); S068 coded before S069
Status: Done (committed 9c2c7f9, adopted 30-10-2026; checks: 5 auto; row 50 optional)
From: R05.2
```

# S069 — Why-why and the root cause

## 1. What will be built

R05.1 gives an improvement its problem and its tickets (S067 backend, S068 screens). **This step adds
the analysis itself**: from the symptom, through a chain of *Why? / Because* lines, to a root cause
the plant can change (TPM why-why, § 2). It is coded **after S068**: the files S067 and S068 create
exist by then, and § 3 names them as such.

1. **The why-why chain** (Q2.1 a). One ordered chain of lines on the improvement. Each line has a
   question (`"Why?"`), an answer (`"Because"`) and optional evidence (`"Evidence (optional)"`).
   The chain has any length up to 20 lines (§ 5.2). Each line keeps who wrote it and when, and who
   changed it last and when.
   - *Add why* appends a line at the end.
   - *Edit* changes a line's text, and its place in the chain (`"Place in the chain"`).
   - *Remove why* deletes a line, after a confirmation on the row; the lines after it move up.
2. **The root cause** (Q2.2 a). A text (what the plant can change) plus one cause from the
   failure-cause list (Masters › Failure codes, S016). Set, then changed as the analysis goes on;
   never cleared (D4). The dialog fills the text with the last why's answer when no root cause is set
   yet.
3. **Contributing causes** (Q2.1 a). One optional free text on the improvement, in the root-cause
   dialog: the causes that helped the failure but are not the root.
4. **Both causes side by side** (Q2.3 a). Under the root cause, the page shows the linked tickets'
   own causes and one line on the difference. The tickets are never written.
5. **A used cause is frozen** (Q2.2 a, "as a ticket does"). Once an improvement's root cause uses a
   cause, Masters refuses to change that cause's code, as it does for a cause a ticket uses
   (`_check_code_frozen`, `backend/masters.py:743`).
6. **Help text** on the why-why card: "Ask why until the answer is something the plant can change."

**Who:** every reader of the improvement sees the chain and the root cause (`improvement:read`).
Only `improvement:edit` holders at the improvement's site write them (engineers and managers), and
only while the improvement is open (S067 § 5.3, `IMPROVEMENT_OPEN_STATES`).

**After it:** the full analysis of TK-2026-10-002 is on record: five whys, from "the press did not
start" to "the presses have no PM plan", and the root cause "4.2 Management error".

### Out of scope

- The rule "root cause required before *Watching*" (Q2.2 a). R05.4 adds the states and enforces it
  there; this step stores and shows the root cause only.
- The timeline and the history of edits (R05.4): *why added*, *root cause set* and their changes.
  This step keeps `created_*` / `updated_*` on the rows only (§ 2, the departure S067 recorded).
- Countermeasures and the mock-up's `"Go to countermeasures"` button (R05.3).
- A tree of whys (Q2.1 b), a fishbone (Q2.1 c), several root causes, a separate root-cause list
  (Q2.2 c).
- Changing a ticket's cause from the improvement (Q2.3 b, not chosen).
- A rule that the root cause must follow a why, or that the chain ends at the root cause (§ 9).
- Drag-and-drop ordering (D3).

## 2. Standards and practice

- **TPM — why-why analysis** (the "5 whys", a tool of the focused-improvement pillar). In plain
  words: ask "why?" again and again until the answer is something the plant can change: a method, a
  standard, a design. "The contact was dirty" is not a root cause; "nobody cleans the panels" is.
  The step builds the classic single chain (Q2.1 a), any length, so a team can stop at three whys or
  go to seven. The help text on the card says the rule in one line. Each answer may carry evidence,
  so a "because" is a fact seen, not a guess.
- **ISO 14224 — failure cause** (Annex B, Table B.3, as S016 cites it; clause numbers *to verify*).
  In plain words: the failure cause is "the circumstances during design, manufacture or use which
  have led to a failure", sorted in five groups (design, fabrication / installation, operation /
  maintenance, management, miscellaneous). A ticket's cause is usually the immediate one (worn
  contacts, 3.4). The standard leaves root-cause analysis to separate methods. **How the step
  follows it:** the root cause picks from the **same** cause list, so root causes count by the same
  ISO groups as the tickets' causes, and a report can set them side by side. The ticket keeps its
  own cause (Q2.3 a).
- **IEC 62740:2015 — Root cause analysis (RCA)** (title as R05 cites it; content and clause numbers
  *to verify*). In plain words: a standard on how to run an RCA: describe the problem, gather
  evidence, find the causes, check them, then act. It lists why-why among its methods. **How the
  step follows it:** the problem (S067) → whys with evidence → a root cause; the actions are R05.3,
  the check R05.4. Only the why-why method is built (Q2.1 a).
- **ISO 9001:2015 § 10.2.1 (b)** (nonconformity and corrective action). In plain words: after a
  failure, review it, find its causes, and check whether the same can happen elsewhere. The why-why
  and the root cause are this "find its causes". *Whether it can happen elsewhere* is R05.3's
  *Spread* kind. Clause letters as Plan § 1 cites them; the next edition's numbers are *to verify*
  (R05 § Standards).
- **ISO 9001 § 7.5.3** (control of records). In plain words: records are kept, protected from
  change, and show who did what and when. Each why line and the root cause keep who wrote them and
  when (`created_*`, `updated_*`), and a closed improvement is read-only (R05.4). **Departure
  (recorded, as S067 § 2):** an edit or a removal of a why, and a change of the root cause, keep no
  history of the earlier text in this step. R05.4's timeline adds the history and backfills what
  the rows show. The analysis is a working draft until the team sets the root cause and R05.4 moves
  the state on. Rejected: soft-deleted whys and an edit table now (D6).

## 3. Where

S069 is coded after S068. The files marked **(S067)** or **(S068)** are new in those steps and
exist when this step starts; S069 changes them. S067 is being coded now, so line numbers in
`backend/` files S067 touches (`improvements_core.py`, `improvements.py`, `tickets.py`,
`local_db.py`, `config_rbac.py`, `conftest.py`) are S067's working tree on 30-10-2026 and may
move; the function and constant names are the anchors.

### Backend

- `backend/local_db.py`: migration **v37** (§ 4.1). S067 adds v36 (`backend/local_db.py:1104`,
  "Improvements and their tickets (S067)", in S067's working tree; v35 is the latest committed,
  `:1079`). No `_PRECONDITIONS` entry (§ 4.1).
- `backend/improvements_core.py` **(S067)**: the why and root-cause validators, the reorder and
  renumber rules, the bounds and messages (§ 5.2, § 5.3). It reuses S067's `_text`
  (`backend/improvements_core.py:60`) and `_is_id` (`:56`).
- `backend/improvements.py` **(S067)**: the routes of § 6; the detail gains `whys`, `root_cause`,
  `contributing_causes`; the LOCK ORDER note gains the why and root-cause writes (§ 5.4).
  The new routes reuse S067's helpers: `_lock_improvement` ((6b)), `_check_improvement` (the
  predicate 404, then the key at the site 403), `_require_open` (409) and `_detail_response` (the
  answer). `_LOCK_IMPROVEMENT` ("the values an edit compares with") gains `root_cause`,
  `root_cause_id` and `contributing_causes`; the detail's select (`_IMPROVEMENT_COLUMNS`) joins the
  root cause's `failure_causes` row.
- `backend/masters.py`: a cause's code is frozen also when an improvement's root cause uses it
  (§ 5.5). `_check_code_frozen` (`backend/masters.py:743`) and `_update_plain_master` (`:763`) gain
  an optional second user; `update_failure_cause` (`:795`) passes `improvements.root_cause_id`.
  The failure-codes comment (`:651-655`) and the docstring of `update_failure_cause` say so.
- `backend/tickets.py`: docstring only. The LOCK ORDER note's paragraph on the code freeze
  (`backend/tickets.py:79-83`) names the improvements count after the tickets count.
- `backend/equipment.py`: docstring only. S067's `improvements.py` bullet in the global LOCK ORDER
  note (`backend/equipment.py:9`) gains "then, on a root-cause write, the failure cause's shared
  foreign-key lock".

### Frontend

- `frontend/src/views/ImprovementDetailView.vue` **(S068)**: the right column (`col-lg-6`, the half
  S068 left free, S068 § 5.4) holds the cards *Why-why* and *Root cause* and the note on the two
  causes; on a phone they follow *Tickets* (§ 5.7).
- `frontend/src/views/improvements/WhyDialog.vue` (new): *Add why* / *Edit why*, one
  `useFormModal` (§ 5.7).
- `frontend/src/views/improvements/RootCauseDialog.vue` (new): *Root cause*, `useFormModal` with
  `send` (§ 5.7).
- `frontend/src/utils/improvementLabels.js` **(S068)**: `ticketCauses(tickets)` (the distinct causes
  of the linked tickets, in code order), `defaultRootCause(whys)` (the last why's answer, cut to
  500), `causeText(cause)` ("4.2 Management error").
- `frontend/src/stores/masters.js`: `CAUSE_GROUPS` (the five ISO groups and their labels) and
  `causeGroupLabel(group)`, beside `ensureFailureCauses` (`frontend/src/stores/masters.js:81`).
  Today the same list is written twice: `GROUPS` in `FailureCausesPanel.vue:17` and `CAUSE_GROUPS`
  in `MoveDialog.vue:55`. The root-cause picker would be a third copy (CLAUDE-COMMON *DRY*), so the
  two move to the store (D7).
- `frontend/src/views/tickets/MoveDialog.vue`: imports `CAUSE_GROUPS` from the store; its own list
  (`:55-58`) goes. Labels and order unchanged.
- `frontend/src/views/masters/FailureCausesPanel.vue`: imports `CAUSE_GROUPS` and
  `causeGroupLabel` from the store; `GROUPS` and `groupLabel` (`:17-24`) go. Its `GROUPS` entries are
  `{value, label}` objects and `MoveDialog`'s are `[value, label]` pairs: the store keeps the object
  form, and `MoveDialog`'s `causeGroups` (`:92-94`) reads `g.value` / `g.label`.

### Tests

- `backend/tests/test_migration_v37.py` (new), on the pattern of `test_migration_v35.py`
  (`VERSIONS` slices its own range, `backend/tests/test_migration_v35.py:16`); S067's
  `test_migration_v36.py` slices `range(20, 37)` and is untouched.
- `backend/tests/test_improvements_core.py` **(S067)**: the validators and the reorder rule (§ 8.2).
- `backend/tests/test_improvement_whys_api.py` (new): the why routes, the root-cause route, the
  detail's new fields (§ 8.2). A file of its own, so S067's `test_improvements_api.py` stays as it is.
- `backend/tests/test_failure_codes_api.py`: `TestCauseAndActionCodeFrozenOnceUsed`
  (`backend/tests/test_failure_codes_api.py:268`) gains a case: a cause used only by a root cause
  keeps its code (§ 8.2). Its two existing asserts of "This code is used by tickets and can no
  longer change" (`:256`, `:281`) stay true (§ 5.5).
- `backend/tests/conftest.py`: `improvement_whys` joins `_TABLES` (`backend/tests/conftest.py:162`),
  before S067's `improvements`.
- `frontend/tests/improvementLabels.test.js` **(S068)**: `ticketCauses`, `defaultRootCause`,
  `causeText`.
- `frontend/e2e/improvements.spec.js` **(S068)**: the S069 tests (§ 8.3).
- `frontend/tests/masters.test.js`: `describe("failure codes (S016)")` (`frontend/tests/masters.test.js:65`) gains one case: `causeGroupLabel` for each of the five groups and an unknown value (returned as it is).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the table `improvement_whys`, the three new columns of
  `improvements`, the Mermaid overview (improvement_whys → improvements; improvements →
  failure_causes), the "migration v37" line.
- `docs/Plan.MD`: § 6 *Screens*, the improvement page gains the why-why and root-cause cards; § 4.6
  or the R05 row of § 1 needs no change (the decisions are there already).
- `docs/Maintenance-Philosophy.md` § 12 Glossary: rows *Why-why* and *Root cause* (beside
  *Failure cause*), one plain sentence each.
- `.claude/CLAUDE.md` § SMTW-Review: the spec map's `improvements` entry reads S067/S068/S069.
- `docs/steps/device-checks.md`: the row of § 8.4.

**File count:** 21 code and test files (backend: 6 code, 5 tests; frontend: 7 code, 3 tests), and
6 docs. Under the size rule's 25 code and test files; no split proposed (§ 9).

## 4. Data model

### 4.1 Migration v37

```sql
-- The why-why chain of an improvement (S069, R05.2): one ordered chain of Why? / Because lines
-- (TPM why-why; Q2.1 a).  position is 1..n with no gaps, kept by improvements.py under the
-- improvement's lock (S067 § 5.4, (6b)); no unique key, so a reorder needs no temporary values.
CREATE TABLE IF NOT EXISTS improvement_whys (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    improvement_id  INT NOT NULL,
    position        SMALLINT NOT NULL,
    question        VARCHAR(300) NOT NULL,
    answer          VARCHAR(1000) NOT NULL,
    evidence        VARCHAR(500) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    updated_at      DATETIME NULL,
    updated_by      VARCHAR(100) NULL,
    KEY ix_improvement_whys_position (improvement_id, position),
    CONSTRAINT chk_improvement_whys_position CHECK (position >= 1),
    CONSTRAINT fk_improvement_whys_improvement FOREIGN KEY (improvement_id) REFERENCES improvements (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The root cause (Q2.2 a): a text and one cause of the failure-cause list, both or neither; and
-- the contributing causes, a free text (Q2.1 a).
ALTER TABLE improvements
    ADD COLUMN IF NOT EXISTS root_cause          VARCHAR(500)  NULL AFTER problem,
    ADD COLUMN IF NOT EXISTS root_cause_id       INT           NULL AFTER root_cause,
    ADD COLUMN IF NOT EXISTS contributing_causes VARCHAR(2000) NULL AFTER root_cause_id,
    ADD KEY IF NOT EXISTS ix_improvements_root_cause (root_cause_id),
    ADD CONSTRAINT fk_improvements_root_cause
        FOREIGN KEY IF NOT EXISTS (root_cause_id) REFERENCES failure_causes (id);
ALTER TABLE improvements ADD CONSTRAINT IF NOT EXISTS chk_improvements_root_cause
    CHECK ((root_cause IS NULL) = (root_cause_id IS NULL));
```

- **The CHECK** keeps "a text and a cause, both or neither" a database rule. Every row S067 wrote
  has both NULL, so it meets the CHECK.
- **`ix_improvements_root_cause`** serves the freeze's shared-lock count (§ 5.5), as the
  foreign key would make one anyway; the name makes the count's index explicit.
- **Text bounds:** utf8mb4; MariaDB counts characters in `VARCHAR(n)`, so Tamil text fits (S067
  § 4.1). The bounds are § 5.2's.
- **Re-run safety:** `IF NOT EXISTS` on the table, each column, the key, the foreign key
  (`FOREIGN KEY IF NOT EXISTS`, as v35, `backend/local_db.py:1090-1093`) and the CHECK
  (`ADD CONSTRAINT IF NOT EXISTS … CHECK`, as v21, `backend/local_db.py:613`). A half-applied v37
  runs again. `ADD KEY IF NOT EXISTS` has no precedent in `local_db.py`; MariaDB accepts
  `ADD {INDEX|KEY} [IF NOT EXISTS]`, and § 8.1's re-run test is what proves it here (BR1-10).
- **No precondition:** a new table, three nullable columns and a CHECK that every existing row
  meets (all NULL). Nothing is converted or dropped (the v21 reasoning, `backend/local_db.py:600`).
- **Rollback:** the previous release (S067/S068) does not read the new table or columns.
- **No row of `improvement_whys` is soft-deleted:** *Remove why* deletes the row (D6).

### 4.2 What is computed, never stored

- The tickets' causes beside the root cause: from S067's detail (`tickets[].cause`), made distinct in
  the frontend (`ticketCauses`, a display helper).
- `created_by_name` / `updated_by_name` of a why, as S067's `created_by_name` (the person whose login
  it is, or the login itself).

## 5. Rules

### 5.1 Where a write is allowed

Every write of this step (add, edit, remove a why; set the root cause) needs, in this order, as S067
§ 5.5 for its own writes:

1. the improvement inside S067's access predicate (`improvement:read` units): otherwise 404;
2. `improvement:edit` at the improvement's site (`require_perm_at`, `backend/auth_utils.py:451`):
   otherwise 403;
3. the improvement open (`improvements_core.is_open`, `backend/improvements_core.py:108`, S067):
   otherwise 409 `IMPROVEMENT_CLOSED` "This improvement is closed" (`:45`). Every improvement is
   open until R05.4; the check is written now, as S067 did.

The route decorator is `@require_perm("improvement:edit")` (any site), as S067's writes.

### 5.2 The fields

**A why** (`validate_why(body, creating)` in `improvements_core`, for `clean_body`,
`backend/api_common.py:121`):

| Field | `POST` | `PUT` | Rule and message (field) |
|---|---|---|---|
| `question` | required | optional | text, trimmed, 1–300: "Enter the question" / "Question: up to 300 characters" / "Question must be text" (`question`) |
| `answer` | required | optional | text, trimmed, 1–1000: "Enter the answer" / "Answer: up to 1000 characters" / "Answer must be text" (`answer`) |
| `evidence` | optional: absent, `null` or empty after trim → NULL | optional: absent → unchanged; `null` or empty after trim → NULL | text, trimmed, up to 500: "Evidence: up to 500 characters" / "Evidence must be text" (`evidence`) |
| `position` | not taken | optional | integer, not a boolean, 1…n (n = the number of whys): "Choose a place from 1 to n" (`position`); the type is checked by `validate_why`, the range by the core's `position_error(n, position)` (§ 5.3), which builds the message |

- `question` or `answer` sent as `null` on a `PUT` is "Enter the question" / "Enter the answer", as
  S067's `title` (`validate_improvement`, `backend/improvements_core.py:75`).
- An absent field on a `PUT` stays as it is. A field equal to the stored value is not written. A
  `PUT` that changes nothing answers 200 with the detail and writes nothing (no `updated_at`), as
  S067 § 5.2.
- Unknown body fields are ignored.
- **At most 20 whys** (`WHYS_MAX`): a `POST` on an improvement with 20 whys is 409 "An analysis holds
  up to 20 whys. Change a why instead." (no field: the dialog shows it at the top). Twenty is four
  times the classic five; the bound keeps the page and the record sane. The page hides nothing for
  it (§ 9).

**The root cause** (`validate_root_cause(body, _creating)`, one route, always a `PUT`; it takes the
`creating` argument `clean_body` passes, `backend/api_common.py:126`, and ignores it, as
`validate_link(body, _creating=True)` in S067's core):

| Field | Rule and message (field) |
|---|---|
| `root_cause` | required, text, trimmed, 1–500: "Enter the root cause" / "Root cause: up to 500 characters" / "Root cause must be text" (`root_cause`) |
| `root_cause_id` | required, integer ≥ 1, not a boolean: "Choose the cause" (`root_cause_id`); then the shell: the cause exists and is active when it differs from the stored one, else 400 "Choose an active cause from the list" (`root_cause_id`) |
| `contributing_causes` | optional; absent → unchanged; `null` or empty after trim → NULL; text 1–2000: "Other causes: up to 2000 characters" / "Other causes must be text" (`contributing_causes`) |

- `root_cause` and `root_cause_id` are always sent together; the root cause is never cleared (D4).
- A cause that is the stored one is not checked again, so a root cause whose cause was later
  deactivated survives an edit of the text (as S067 § 5.6 keeps an unchanged lead). A deactivated
  cause stays on the records that use it, as on tickets (`backend/tickets.py:82-83`).
- The active check is a plain read, as `_check_active_code` at close (`backend/tickets.py:775`):
  a deactivation at the same moment is accepted, as there.
- Changed fields only are written (`update_row`, `backend/db_helpers.py:68`, stamps
  `improvements.updated_at` / `updated_by`); nothing changed → 200, nothing written.

### 5.3 Order: add, move, remove

Pure functions in `improvements_core`; the shell feeds them the improvement's whys, read under its
lock, as `[(id, position)]` by position.

- **Add:** the new why gets `position = n + 1`.
- **Move** (`PUT` with a `position` that differs): `reorder(ids, why_id, new_position)` → the
  `(id, position)` pairs that change. The why moves to `new_position`; the lines between shift by
  one. Example: whys A1 B2 C3, move C to 1 → C1 A2 B3. A `position` outside 1…n is 400 "Choose a
  place from 1 to n" (`position`, n written as the number): `position_error(n, position)` in
  the core returns the message or None, as `removal_error` does, and the shell raises the 400
  with it (BR1-02).
- **Remove:** `renumber(ids_without_removed)` → the pairs that change; the lines after the removed
  one move up by one.
- **The invariant:** after every write the positions are exactly 1…n. Only the routes of this step
  write `improvement_whys`, and each takes the improvement's lock first (§ 5.4), so two writers never
  interleave.
- **Read order:** `ORDER BY position, id` (the `id` only breaks a tie the invariant rules out).
- **A why of another improvement** (`/improvements/1/whys/<a why of improvement 2>`) or an unknown
  why: 404 "Not found".

### 5.4 Locks

The database runs REPEATABLE READ (settings, *Self-check, repo items* (2)). Every route below takes
its locking read first, so its first plain read, and the snapshot, start after the lock is granted:
every plain read sees what was committed before the lock.

**The global order** (`backend/equipment.py:9`, with S067's (6b)): … (6) the serial counter →
**(6b) the improvement row** → (7) the ticket row. This step adds **no new lock level**: why rows are
never locked on their own; the improvement's lock guards them. It adds **one edge**: (6b) → a
failure cause's **shared** foreign-key lock, on a root-cause write.

**Add why** (`POST /api/improvements/<id>/whys`), one `transaction`:

1. (6b) The improvement row `FOR UPDATE` (`state`, `unit_id`). 404 when missing.
2. Plain reads, the transaction's first: the access predicate (404), the key at the site (403), the
   open state (409), the whys' count (409 at `WHYS_MAX`).
3. Insert the why at n + 1 (its foreign key takes the improvement's shared lock, already held
   exclusive).
4. Read the detail inside the transaction (S067's pattern).

**Edit why** (`PUT /api/improvements/<id>/whys/<why_id>`):

1. (6b) `FOR UPDATE`.
2. Plain reads: predicate 404, key 403, open 409, the why row by `id` and `improvement_id` (404), the
   whys `(id, position)` by position (for `position`).
3. `update_row` on the why's own changes: its changed text fields and, when it moved, its new
   `position` (one dict, so the moved why is stamped `updated_*`). Then `UPDATE improvement_whys
   SET position = %s WHERE id = %s` for each **other** pair `reorder` returned: a row that only
   shifted gets no stamp (BR1-07).

**Remove why** (`DELETE /api/improvements/<id>/whys/<why_id>`): (1) (6b) `FOR UPDATE`; (2) plain
reads: predicate 404, key 403, open 409, the why (404), the whys by position; (3) `DELETE` the why,
then the position updates `renumber` returned.

**Set root cause** (`PUT /api/improvements/<id>/root-cause`):

1. (6b) `FOR UPDATE` (`state`, `unit_id`, `root_cause`, `root_cause_id`, `contributing_causes`).
2. Plain reads: predicate 404, key 403, open 409; when `root_cause_id` differs from the stored one,
   the cause's `active` (400).
3. `update_row` with the changed fields. A new `root_cause_id` takes a **shared** lock on that
   `failure_causes` row through the foreign key.

**A cause's code change** (masters.py, changed, § 5.5): (1) the cause row `FOR UPDATE`
(`_lock_row`, `backend/masters.py:144`); (2) its tickets counted `LOCK IN SHARE MODE` (unchanged);
(3) its improvements counted `LOCK IN SHARE MODE` (`WHERE root_cause_id = %s`, through
`ix_improvements_root_cause`); (4) the update.

**Reads** (the detail): plain, no lock.

**Why the freeze is race-free** (the tickets' argument, `backend/tickets.py:79-83`): a root-cause
write that holds the cause's shared foreign-key lock commits before the code change gets its
exclusive lock, and step (3) counts it. A later one waits behind the cause's lock and then sees the
new code, which is allowed: the code changed before its first use.

**No new deadlock cycle, checked against the notes:**

- *(6b) → cause (shared).* The one path that holds a cause exclusive and then waits on improvements
  is the code change, step (3). It waits only on improvement rows whose committed `root_cause_id`
  is that cause. A root-cause write waits for a cause's shared lock only when it **changes** its
  `root_cause_id` to that cause (InnoDB checks a foreign key only when the column changes), and
  then its row's committed index entry names the **old** cause. So the code change of cause C never
  waits on a writer that waits for C: no cycle. A writer that keeps its cause takes no cause lock.
- *Ticket writes* (`backend/tickets.py:23`): no route of this step locks a ticket. A ticket close
  takes the cause's shared lock after the ticket; nothing here holds an improvement and then waits
  for a ticket.
- *Masters* (`backend/masters.py:1-33`): no masters write locks an improvement or a why; the
  freeze's count takes only shared locks.
- *S067's routes:* all take (6b) first; why and root-cause writes take nothing before (6b).

The coder writes this into improvements.py's LOCK ORDER note, adds the edge to the S067 bullet of
equipment.py's note, and names the improvements count in tickets.py's freeze paragraph.

### 5.5 The freeze of a used cause

- `_check_code_frozen(cur, clean, locked, ticket_column, root_cause_column=None)`: when `code`
  changes, count tickets as today (409 "This code is used by tickets and can no longer change",
  unchanged); then, when `root_cause_column` is given, count `improvements` `WHERE
  root_cause_id = %s LOCK IN SHARE MODE`: 409 "This code is used by an improvement's root cause and
  can no longer change" (`code`).
- `_update_plain_master` passes the new argument through; only `update_failure_cause` gives it.
  Failure modes and maintenance actions are not used by improvements and are unchanged.
- The label, the group, the description and the active flag stay editable, as for a ticket's cause
  (S016 § 5.3, `backend/masters.py:796-797`). A group change reclassifies the root causes too, which
  is what the ISO roll-up wants.
- Deactivating a cause needs no check (as today): an inactive cause stays on the improvements that
  use it and drops out of the picker.
- The column name is a code constant, never client input (as `ticket_column`).

### 5.6 Permissions

No new key. S067's keys (S067 § 5.5; `config_rbac.py` after S067):

| Action | Key | Where checked |
|---|---|---|
| Read the whys, the root cause, the contributing causes | `improvement:read` | S067's detail route and its predicate |
| Add, edit, remove a why; set the root cause | `improvement:edit` at the improvement's site | § 5.1 |
| Change a cause's code (Masters) | `failure_codes:edit`, global (unchanged, `backend/config_rbac.py:157`) | `update_failure_cause` |

- The screens show every control from the detail's `permissions` and `is_open` (S067 § 5.5), so no
  button ends in a 403.
- **Identity:** no field of this step changes who can log in or what anyone sees. Names only: a why
  shows its writer's name, never a login, role or email.
- **A request with no identity** gets the 401 of `require_perm`, never admin (unchanged).

### 5.7 The screens

On the improvement page (S068 § 5.4), the right column on a wide screen; on a phone, after the
*Tickets* card, in this order:

**The card *Why-why*:**

- Header: "Why-why" and, for an editor of an open improvement, `"Add why"`
  (`btn btn-outline-primary`, icon `fa-solid fa-plus`, the ticket page's size as S068 BR1-11).
- Under the header, always: the help line "Ask why until the answer is something the plant can
  change." (`small text-secondary`).
- One row per why, by position: "**1. Why did the press not start?**", then the answer, then
  "Evidence: …" (`text-secondary`) when set, then "Priya (engineer), 29-10-2026 11:52" small (the
  writer; "changed by … " when `updated_at` is set and the changer differs).
- For an editor of an open improvement each row has an edit button (icon `fa-solid fa-pen`,
  `aria-label` "Edit why 3") and a remove button (icon `fa-solid fa-trash`, `btn-outline-danger`,
  `aria-label` "Remove why 3"), the labour rows' pattern (`frontend/src/views/tickets/LabourPanel.vue:144-151`).
- **Remove** asks inline on the row (`confirmingRemoveId`, as S068's ticket remove): the line
  "Remove why 3? You cannot undo this." with `"Remove why"` (`btn-danger`) and `"Cancel"`. A refusal
  shows under it. No dialog.
- Empty: "No whys yet." and, for an editor, "Start with why the problem happened."

**The dialog *Add why* / *Edit why*** (`WhyDialog.vue`, `useFormModal({ path:
"/api/improvements/<id>/whys", … })`, `frontend/src/composables/useFormModal.js:20`; the edit
`PUT`s to `<path>/<why_id>`, which is § 6's route):

- **The call contract** (BR1-04): `useFormModal` calls `blank()` with no argument at set-up
  (`frontend/src/composables/useFormModal.js:22`, `const form = ref(blank())`), so `blank(seed = {})`
  reads the seed with optional chaining and gives empty strings then.
- *Add*: `openCreate(seed)` with `seed = {previousAnswer}`; `blank(seed = {})` gives `{question: "",
  answer: "", evidence: ""}`; `seed.previousAnswer` feeds the line above the fields. When a why exists, the dialog shows the last answer above the fields
  ("Because: Its contact faces were coated with fine dust.", `text-secondary`), so the engineer
  writes the next "why" from it on a phone without scrolling the page.
- *Edit*: `openEdit(why)`; `fromRecord` gives `{question, answer, evidence: evidence ?? "",
  position}`; the previous line's answer shows as above (none for the first).
- Fields: **`"Why?"`** (textarea, 2 rows, `maxlength` 300, placeholder "Why did the press not
  start?"), **`"Because"`** (textarea, 3 rows, `maxlength` 1000), **`"Evidence (optional)"`**
  (input, `maxlength` 500, help "What you saw or measured: a photo, a reading, a part."),
  **`"Place in the chain"`** (select 1…n, only on *Edit* when n > 1).
- Buttons: `"Add why"` / `"Save why"`; `"Cancel"`. The page takes the answer (the whole detail).
- `toBody` sends `evidence` as `null` when empty, and `position` on every *Edit* (never on *Add*):
  the current position writes nothing (§ 5.3, `reorder` returns no pairs; BR1-08).
- Every field renders its `fieldError`; the 20-whys refusal has no field and shows at the top
  (`modalError`).

**The card *Root cause*:**

- Header: "Root cause" (icon `fa-solid fa-crosshairs`, as the mock-up) and, for an editor of an open
  improvement, `"Set root cause"` when none is set, `"Edit root cause"` when one
  is (not `"Edit"`: the problem card has S068's `"Edit"`, and two buttons of one name on a page
  confuse a screen reader and a test locator).
- Set: the cause as a badge, "4.2 Management error", and "Group: Management" (BR1-01: the plain
  word of the Masters panel's column; the standard is named in § 2, not on the card)
  (`causeGroupLabel`); then the text; then, when set, "Other causes: …". An inactive cause shows
  "(inactive)" after its label.
- Not set: "No root cause yet. Find it with the why-why first."
- **The note on the two causes** (Q2.3 a), under the card, always when any linked ticket has a
  cause: "Cause on the tickets: 3.4 Expected wear and tear" (each distinct cause, `ticketCauses`, joined
  by ", "), then one line: "The ticket's cause says why the part failed. The root cause says why
  the plant let it happen." A ticket with no cause yet (not closed) adds nothing to the list.

**The dialog *Root cause*** (`RootCauseDialog.vue`; `useFormModal` with `path: null` and
`send(() => apiPut(...))`, the pattern `MoveDialog.vue` uses, `frontend/src/views/tickets/MoveDialog.vue:66`):

- Opened with `openCreate(seed)`, `seed = {improvement}`; `blank(seed = {})` (BR1-04: also called
  with no seed at set-up) gives `{root_cause: seed.improvement?.root_cause?.text ??
  defaultRootCause(seed.improvement?.whys ?? []), root_cause_id: seed.improvement?.root_cause?.cause.id
  ?? "", contributing_causes: seed.improvement?.contributing_causes ?? ""}`; with no seed, every
  field is an empty string.
- Fields: **`"Root cause"`** (textarea, 3 rows, `maxlength` 500, help "What the plant can change.
  Often the last answer of the why-why."), **`"Cause"`** (select: "Choose the cause" first, then the
  active causes in `optgroup`s by `CAUSE_GROUPS`, as `MoveDialog.vue:296`; the stored cause, when
  inactive, listed last, marked "(inactive)"), **`"Other causes (optional)"`** (textarea, 3 rows,
  `maxlength` 2000, help "Causes that helped, but are not the root.").
- Buttons: `"Save root cause"`; `"Cancel"`.
- The cause list comes from `ensureFailureCauses()` (`frontend/src/stores/masters.js:81`; route
  `GET /api/masters/failure-causes`, `masters:read`, every role). A load error shows at the top; the
  save still sends what is chosen.

**The one-tap path** (self-check 13): after the last why, *Set root cause* → the text is already the
last answer → choose the cause → *Save root cause*. Three taps and one pick.

**Words for the floor** (§ Use on the floor): "why", "because", "evidence", "root cause", "other
causes"; no "RCA", no "contributing". The engineer fills the chain; the operator reads it, so the
rows are short plain lines.

### 5.8 The database down

The new routes go through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*). The page shows its load error with `"Retry"` (S068 § 5.8); a dialog
shows the error at the top. No background task, no alert.

## 6. API

All under S067's blueprint `improvements_bp` (`/api/improvements`), ids declared `<int:…>` as S067
BR2-05. Every write answers with the whole detail, as S067's writes (S068 BR1-09: one answer, one
page copy).

| Route | Key | Body | Answer |
|---|---|---|---|
| `POST /api/improvements/<id>/whys` | `improvement:edit` | `{question, answer, evidence?}` | 201, the detail; 400, 403, 404, 409 per § 5 |
| `PUT /api/improvements/<id>/whys/<why_id>` | `improvement:edit` | `{question?, answer?, evidence?, position?}` | 200, the detail |
| `DELETE /api/improvements/<id>/whys/<why_id>` | `improvement:edit` | — | 200, the detail |
| `PUT /api/improvements/<id>/root-cause` | `improvement:edit` | `{root_cause, root_cause_id, contributing_causes?}` | 200, the detail |
| `GET /api/improvements/<id>` (S067) | `improvement:read` | — | gains the fields below |

**The detail gains:**

- `whys: [{id, position, question, answer, evidence, created_at, created_by_name, updated_at,
  updated_by_name}]` by position;
- `root_cause: {text, cause{id, code, label, cause_group, active}} | null`;
- `contributing_causes: string | null`.

S067's `PUT /api/improvements/<id>` ignores unknown fields (S067 § 5.2), so it never writes these.
The list (`GET /api/improvements`) is unchanged: `backend/tests/test_improvements_api.py:514` pins
the list item's key set, so the `LEFT JOIN failure_causes` added to the shared select
(`_IMPROVEMENT_FROM`) adds no field to the list item (BR1-11).

## 7. Design decisions

- **D1. Whys in a table of their own, the root cause as columns on `improvements`** (as R05.2 says).
  A chain has any number of lines; the root cause is one per improvement, and R05.4's state rule
  reads it from the row. Rejected: the root cause as a flagged why (the CHECK "text and cause
  together" and R05.4's rule get harder); the whys as one JSON text (no who-and-when per line).
- **D2. A why is a question and an answer, both required; evidence optional** (Q2.1 a, the mock-up's
  "1. Why … ? / Because …"). The question keeps each step of the chain readable on its own for the
  operator. Rejected: the answer only, with "Why?" implied (the chain then reads as a list of facts
  with no logic between them); an answer optional, to fill later (half lines in a record; a later
  edit fills it as easily).
- **D3. Order by a `"Place in the chain"` select in the edit dialog**, and append on *Add*. One
  field in a dialog the engineer already uses, easy with a gloved thumb. Rejected: drag-and-drop (hard
  on a phone, a new library); up / down buttons on each row (two more buttons per row, four in all,
  on a narrow screen); insert-between buttons (rarely needed: a moved line does it).
- **D4. The root cause is set and changed, never cleared.** A wrong root cause is replaced by a better
  one; R05.4 reads "root cause set" as a state rule, and a clear would need its own reverse rule.
  Rejected: a *Clear* button (no use case at the plant; it would undo R05.4's move).
- **D5. The root cause's text is prefilled with the last why's answer.** TPM: the root cause is where
  the chain ends. The engineer usually keeps or shortens it. Rejected: an empty field (retyping on a
  phone); a server rule that the root cause must equal or follow the last why (the team often words
  it better, and a rule would refuse good analyses).
- **D6. *Remove why* deletes the row; no history in this step** (S067's recorded departure, § 2).
  R05.4's timeline brings the history for every improvement event at once, with one design. Rejected:
  `improvement_why_edits` and soft-deleted whys now (a second history design that R05.4 would have to
  absorb or replace).
- **D7. One `CAUSE_GROUPS` list in the masters store.** The root-cause picker needs the five ISO
  groups; two copies exist already (`FailureCausesPanel.vue:17`, `MoveDialog.vue:55`). A third copy
  breaks CLAUDE-COMMON *DRY*, so all three read the store's. Rejected: a third copy (DRY); the group
  label from the server (the backend has no labels today, and the picker reads the whole list
  anyway); a label file in `frontend/src/utils/`, where other label tables live (`ticketLabels.js`):
  the store is chosen because the panel and both pickers already import the cause list from it,
  so the groups come with one import (BR1-12).
- **D8. The freeze extends `_check_code_frozen` with an optional second user** and keeps the tickets'
  message as it is. The 409 says which kind of record uses the cause, and the two existing asserts
  stay. Rejected: one combined message "used by tickets or improvements" (changes the text and its
  tests for no gain); a generic list of `(table, column)` users (one more user only; R05.6 adds none).
- **D9. A separate route for the root cause** (`PUT …/root-cause`), not S067's `PUT`. It has its own
  dialog and its own rules (both fields together, the active cause), and R05.4 will write a
  "root cause set" event from exactly this route. Rejected: widening `validate_improvement` (S067's
  validator and dialog would carry fields they never show).
- **D10. At most 20 whys.** A bound for every input (self-check 6); four times the classic five. The
  page does not hide *Add why* at 20: the refusal is rare and states what to do.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v37.py`)

- A fresh database: `improvement_whys` with its key, CHECK and foreign key; `improvements` with the
  three columns, `ix_improvements_root_cause`, `fk_improvements_root_cause`,
  `chk_improvements_root_cause`.
- A v36 database with an improvement and its link: every old row kept; the three columns NULL.
- The CHECK: a row with `root_cause` set and `root_cause_id` NULL is refused, and the other way
  round; both NULL and both set pass. `position = 0` is refused.
- A re-run of v37 changes nothing (`_schema()` equal, as `test_migration_v35.py`).

### 8.2 Backend (`test_improvements_core.py`, `test_improvement_whys_api.py`, `test_failure_codes_api.py`)

**Core:** `validate_why` (each message of § 5.2: missing, empty after trim, 300 / 301, 1000 / 1001,
500 / 501, a number, `null` question or answer on a `PUT`, `null` evidence → NULL, evidence absent on
a `PUT` → not in `clean`, a boolean `position`); `validate_root_cause` (each message, 500 / 501, 2000 / 2001, `contributing_causes`
`null` and empty → NULL, a boolean `root_cause_id`); `position_error` (0 and n + 1 refused with "Choose a
place from 1 to 3", 1 and n pass); `reorder` (to the front, to the end, one step
down, to its own place → no pairs); `renumber` (the first, a middle, the last removed).

**API** (`test_improvement_whys_api.py`), each test with its own ticket and improvement (S067's
set-up through `ticket_helpers.py`), so the kept worker database gives the starting state. "Another
site" and "a key missing here" as S067 § 8.2 (BR1-03 there).

- **Add why:** three whys get positions 1, 2, 3 and carry `created_by_name`; an operator (403); an
  operator here who is engineer elsewhere (403); an engineer of another site (404); an unknown
  improvement (404); the 21st why (409 with the message); bounds (400).
- **Edit why:** the text of why 2 (200, `updated_at` set, the others unchanged); a `PUT` with no
  change writes nothing; `position` 3 → 1 gives C1 A2 B3 with no gap; `position` 0 and n + 1 (400
  "Choose a place from 1 to 3"); a why of another improvement (404).
- **Remove why:** why 2 of 3 → the rest are 1, 2; the last why; a why of another improvement (404);
  the operator (403).
- **Root cause:** set with an active cause (200, the detail's `root_cause` with `cause_group`); a
  missing text or cause (400); an inactive cause, newly chosen (400 "Choose an active cause from the
  list"); a cause deactivated after it was set, kept when only the text changes (200, `active`
  false); `contributing_causes` set, then cleared with `""`; a `PUT` with no change writes nothing;
  the operator (403); another site (404). The linked tickets' rows are unchanged after a root cause
  is set (their `updated_at` stays).
- **Detail:** an operator of the unit reads `whys`, `root_cause` and `contributing_causes`; whys by
  position.
- **The database down** (`db_down`, `backend/tests/conftest.py:213`): `POST …/whys` answers 503.

**Freeze** (`test_failure_codes_api.py`, `TestCauseAndActionCodeFrozenOnceUsed`): a cause used only
by an improvement's root cause → a code change is 409 "This code is used by an improvement's root
cause and can no longer change" (`code`); its label, group and active flag still change (200); a
re-save with the same code passes. The existing ticket cases are unchanged.

### 8.3 Automated (e2e, targeted: `improvements.spec.js`, `screens.spec.js`, `tickets-work.spec.js`, `masters.spec.js`)

Set-up by API as S068 § 8.1 (a back-in-service ticket by `raiseByApi`, an improvement by
`POST /api/improvements`). For the two causes, the ticket is closed by API with cause 3.4
(`moveByApi(…, "close", { cause_id: await causeId("3.4"), … })`, as
`frontend/e2e/tickets-parts.spec.js:281`). The seed engineer "Priya (engineer)" edits; the seed
operator reads.

- **important** S069: the engineer adds three whys through `"Add why"` (the second dialog shows the
  first answer above its fields), sees "1. …", "2. …", "3. …" and the evidence line; opens
  "Edit why 3", picks place 1 in `"Place in the chain"`, saves: the chain reads 1, 2, 3 in the new
  order. Each dialog calls `expectDialogFits`.
- **important** S069: the engineer removes why 2 through the inline confirmation ("Remove why 2? You
  cannot undo this.", `"Remove why"`): two whys left, numbered 1 and 2.
- **important** S069: the engineer taps `"Set root cause"`: the text holds the last why's answer;
  picks "4.2 Management error"; `"Save root cause"`. The card shows "4.2 Management error",
  "Group: Management" and the text; the note shows "Cause on the tickets: 3.4 Expected wear and tear" and
  the line on the difference. The button now reads `"Edit root cause"`.
- S069: the help line "Ask why until the answer is something the plant can change." shows on the
  card, also with no whys.
- S069: the operator opens the page: the whys and the root cause show; no `"Add why"`, no edit or
  remove buttons, no `"Set root cause"` or `"Edit root cause"`.
- `screens.spec.js`: no new route; it runs again because the page changed. `tickets-work.spec.js`
  (the close dialog's cause list, `MoveDialog.vue`) and `masters.spec.js` (Failure causes panel's
  group column and filter; `frontend/e2e/masters.spec.js:103` picks the group by its label "Operation / maintenance", which stays) run again for the `CAUSE_GROUPS` move; no line is expected to change.
- **S068's tests on the same page:** the page gains buttons named "Edit why n" and `"Edit root cause"`. Playwright matches a role name as a substring unless `exact: true`, so an S068 locator `getByRole("button", { name: "Edit" })` would match them too. The coder checks every `"Edit"` and `"Add ticket"` locator in `improvements.spec.js` and scopes it to its card or adds `exact: true`.
- No test is `@device`: none checks a layout (a fit helper in a flow test does not tag it).

### 8.4 On a real device

- The why dialog on an iPhone: tap `"Because"` in *Add why*; the keyboard opens; the field and
  `"Add why"` can still be reached by scrolling the dialog. Account: an engineer. Network: the plant
  Wi-Fi. Where: either. Not important (the iPhone keyboard over a dialog is a kind the browser
  cannot judge; the Android flow is in § 8.3).

### 8.5 Acceptance

- All unit suites green; `npx vite build` clean; the targeted specs of § 8.3 green; the whole
  browser suite at Normal once at the end (the step changes a dialog of the ticket page and a
  Masters panel).
- The analysis of TK-2026-10-002 can be entered on a phone: five whys and the root cause 4.2.
- A cause used by a root cause keeps its code in Masters.
- `docs/schema.md` and `docs/schema.html` show v37.

## 9. Open questions and assumptions

- **Assumption:** S067 and S068 are coded as their approved briefs say before S069 starts (names,
  routes, the detail, the page layout, (6b)). If their review rounds or code change § 6 of S067 or
  § 5.4 of S068, this brief follows before it is coded.
- **Size:** 21 code and test files and 6 docs; below the size rule's 25, one concern (the analysis).
  If the reviewer counts the docs in, the cut would be at the API: S069 the backend (v37, the
  routes, the freeze), a next step the screens. Not proposed. The draft passes the size rule's
  600 lines (about 690), mostly § 5.4's lock sequences and § 5.7's screen rules; it adds one table
  and no new screen (two dialogs and two cards on S068's page). For the user to decide.
- **Not built, by choice:** a server rule that the root cause needs at least one why (D5). A team
  that sets a root cause with no whys is visible on the page ("No whys yet."); R05.4 may add such a
  rule to *Watching* if KLA wants it.
- **Assumption:** the root cause stays editable while the improvement is open, also after R05.3's
  countermeasures exist. R05.4 decides whether a later state locks it.
- **Assumption:** IEC 62740's content as the roadmap states it; marked *to verify* in § 2.
- **Nothing here needs KLA before review:** Q2.1–Q2.3 are answered (a) at gate R; the rest are
  choices within them, listed in § 7.

## 10. Amendments

### A1 — An edit sends the place in the chain only when it changed (30-10-2026, from CR1-01)

- **Why:** BR1-08 dropped the rule "position left out when unchanged", so every edit sent
  `position`. On a page that is out of date (another person removed or moved a why), a text-only
  edit then moves the why to a place nobody chose.
- **Rule:** the *Edit why* dialog sends `position` only when the user changed the
  `"Place in the chain"` select. The server rule is unchanged: an absent `position` on a `PUT`
  keeps the why's place.
- **Approval:** decided by the orchestrator under KLA's delegation for R05 ("start coding unless
  a defining question"), 30-10-2026. It changes no route and no message. Shown to KLA at gate B.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 4.1 (re-run note), § 5.2 (`evidence` row, `position`
row, `validate_root_cause`, "Enter the root cause"), § 5.3 (`position_error`), § 5.4 *Edit why*,
§ 5.7 (both dialogs' `blank`, `toBody`, "Group: Management", "Cause on the tickets"), § 6 (the
list), § 7 D7, § 8.2 (core cases), § 8.3 (the card's group and the note).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted, option (b) by the orchestrator: the line stays, worded "Group: Management" (the Masters panel's word); no "ISO 14224" on the card; the standard stays named in § 2. § 5.7, § 8.3. |
| BR1-02 minor | Accepted (a): `position_error(n, position)` in the core builds "Choose a place from 1 to n"; the shell raises the 400. § 5.2, § 5.3, § 8.2. |
| BR1-03 minor | Accepted (a): the `evidence` row splits `POST` (absent, `null`, empty → NULL) and `PUT` (absent → unchanged; `null`, empty → NULL). § 5.2, § 8.2. |
| BR1-04 minor | Accepted (a): both dialogs' `blank(seed = {})` read the seed with optional chaining, since `useFormModal` calls `blank()` at set-up (`useFormModal.js:22`). § 5.7. |
| BR1-05…BR1-12 nits | Accepted: BR1-05 "Enter the root cause"; BR1-06 "Cause on the tickets: …"; BR1-07 the moved why's `position` in its own `update_row`, the loop for the other pairs; BR1-08 `position` sent on every *Edit*; BR1-09 `validate_root_cause(body, _creating)`; BR1-10 `ADD KEY IF NOT EXISTS` proved by § 8.1's re-run; BR1-11 the list item keeps its key set; BR1-12 why the store, not `utils/`, in D7. |
