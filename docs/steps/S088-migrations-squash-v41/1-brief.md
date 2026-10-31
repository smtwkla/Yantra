```
Step: S088 — Squash migrations v20–v41
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 31-10-2026
Track: full
Baseline: 26810aa + uncommitted edits outside a step (`EquipmentPicker.vue` label, `ContractFields.vue` layout, four e2e specs, the `.claude/CLAUDE.md` timing note), from review r1
Status: In code review 31-10-2026 (coder Opus, run s088c1); approved 31-10-2026 by KLA (all recommended answers, § 9); was: Gate A 31-10-2026 (review r1: 0 blocker, 0 major, 5 minor, 7 nits; all accepted)
```

# S088 — Squash migrations v20–v41

## 1. What will be built

KLA, 31-10-2026: "Let's squish all the migrations. Prod is on v41." Then: "Squish 20-41 first."
**Decided by KLA:** this step squashes only the **released** migrations v20–v41. v42–v47 (S079–S086,
not released) stay as separate migrations after it, unchanged. *Rejected by KLA:* one squash of
v20–v47 (or v20–v48) into one entry above every recorded version (v50); and, earlier, squashing only
v42–v47.

**KLA's plan after this step (not in S088):** S087 folds v42–v47 and its own v48 into one entry,
**v50**. The end state is `_MIGRATIONS` = [v41 (this step), v50 (S087)]. S087's v50 tests then replace
the per-version tests of v42–v47, so this step changes those only as far as keeps them green (§ 8.3).

1. **One squashed migration, numbered v41.** The entry *Full schema (squashed S001–S075)* replaces
   v20–v41 in `_MIGRATIONS` (`backend/local_db.py:77-1386`, the entries and their comments). It builds the v41 schema (46 tables) with
   `CREATE TABLE IF NOT EXISTS`, in the final column order, plus the seed rows as `INSERT IGNORE`.
   v42–v47 follow it, byte-for-byte unchanged. `LATEST_VERSION` stays 47.
2. **What each database does:**
   - **production (v41 recorded):** v41 is applied, so the engine skips it. v42–v47 run as they would
     have without this step. **This step runs nothing on production.**
   - **dev and test databases at v47** (e.g. `vel_yantra_master`, which records 1–13 and 20–47,
     checked read-only 31-10-2026): v41 is applied; nothing runs.
   - **a fresh database** (e2e, the schema docs, a new install): v41 builds the v41 schema, then
     v42–v47.
   - **a database with versions recorded but not v41** (an old kept test database at v38, a v13
     database): **refused** by a new precondition, unchanged (§ 5.2).
3. **The old texts are kept, frozen.** `backend/tests/fixtures/migrations_v41.py` (new) holds v20–v41
   exactly as at 26810aa. The new upgrade tests build a database from it and prove the squashed v41
   builds the same schema and the same seed rows (§ 8.1).
4. **The schema docs do not change.** `tooling\schema-docs.bat write` must leave `docs/schema/`
   byte-identical: the main proof that the squash lost nothing (§ 8.5).
5. **Tests:** the per-version tests of v20–v41 keep their constraint tests on the squashed v41 and
   lose their upgrade-path tests (S025's rule, § 8.2). v42–v47's tests change two lines each.

### Out of scope

- Squashing v42–v47 or S087's v48 (S087, as KLA plans).
- Any schema change: the squashed v41 is today's v41 shape, column for column. The legacy table
  `user_units` stays (empty on a fresh database), as v20 kept it.
- A change to the migration engine (`init_db`): the engine already applies "every listed version not
  recorded", in list order (`local_db.py:1735`), which is what this design needs.
- A change to `SMTW-WebApp-Base.md` (synced from smtw-common): the numbering departure (§ 7 D1) is
  recorded here and in `.claude/CLAUDE.md`; a note to the base is KLA's call (§ 9 Q4).

## 2. Standards and practice

- **ISO 9001 § 7.5.3 (control of documented information).** The standard asks that records are kept,
  can be found, and are protected from unintended change. The migration texts are the record of how
  the schema came to be. This step keeps them in a frozen fixture that a test runs, so the record is
  both kept and checked; git keeps every earlier version as well. The rule "never edit an applied
  migration" (CLAUDE-COMMON § Migrations) is kept: no applied text changes; the list loses entries
  that every real database has already applied.
- **SMTW-WebApp-Base § Local DB Migration Pattern › Migration squashing.** Followed: full schema as
  `CREATE TABLE IF NOT EXISTS`, idempotent data statements, frozen fixture, upgrade tests from it, a
  precondition for a shape the entry cannot handle. **Departure:** the number. The base says "above
  the highest version any deployed database has recorded"; this step uses v41, production's own
  version (§ 7 D1 gives the reason and why it is safe).
- **› Preconditions.** The new check refuses before anything is applied and says what to do; its test
  starts from the old shape (the frozen fixture), not from an empty database.
- No maintenance standard (TPM, ISO 14224, EN 13306, ISO 55000, SMRP) is touched: no table, column or
  rule changes.

## 3. Where

**File count:** 36 code and test files (1 backend, 35 test files: 3 new, 10 deleted, 22 changed), 1
doc. Over the ~25 guide, but 17 of the test files are deletions or two-line edits (an import, a
version list), and a split would leave the suite red between the halves.

### Backend

- `backend/local_db.py`:
  - `_MIGRATIONS`: the entries v20–v41 with their comments (`:77-1386`, from `(20, …` to the `]),` that
    ends `(41, …`) replaced by one entry `(41, "Full schema (squashed S001–S075)", [...])` (§ 4).
    v42–v47 with their comments (`:1387-1538`, from v42's comment "S079 — the vendor master …")
    unchanged.
  - The header comment (`:51-74`): rewritten for two squashes: v1–v13 into v20 (S025, 21-10-2026),
    then v20–v41 into v41 (S088, 31-10-2026); production at v41; the fixture names; "new migrations
    continue after the last entry". The "Conventions carried over" list stays.
  - `_PRECONDITIONS` (`:1630`): `{41: _v41_squash_check}` **(new function)**. `_old_tables_for_v20`,
    `_v20_shape_check`, `_v25_shape_check`, `_v34_gps_name_check`, `V34_SEED_NAME` and
    `V34_SEED_CREATOR` (`:1548-1627`) are removed: their versions are no longer in the list, so the
    engine never calls them (`check = _PRECONDITIONS.get(version)` runs only for pending listed
    versions). Their texts stay in git and in S025, S030 and S061's briefs. No other user (verified by the
    facts run: `local_db.py` only, no test outside the dropped ones).
  - The docstring (`:1-12`): "v1–v13 were squashed into v20 (S025)" gains "and v20–v41 into v41
    (S088)".

### Tests

New:
- `backend/tests/fixtures/migrations_v41.py` **(new)**: `MIGRATIONS_V41 = [` … `]`, holding a frozen
  copy of v20–v41 from 26810aa (`local_db.py:77-1386`, the entries and their comments, verbatim).
  Docstring: FROZEN — never edit; production's schema is the result of these texts (on v0.1.3's
  masters for v20); a test fixture only. It holds no precondition functions: the tests run it only on
  an empty database, where every old precondition passed. **The rule (also in the docstring):** the
  engine's precondition for version 41 (`_v41_squash_check`) is looked up by number, so it applies to
  this list's v41 too: apply the fixture in one call on an empty database, never its v41 after its
  v20–v40 (that is refused; § 8.1 test 3 relies on it). S087's coder, building a v47 shape from the
  fixture, needs the same rule.
- `backend/tests/migration_helpers.py` **(new)**: the shared helpers of `test_migration_v20.py`,
  moved unchanged: `UPGRADE_CONFIG`, `_recreate`, `_run`, `_migrate`, `_rows`, `_schema`, `_versions`.
- `backend/tests/test_migration_squash_v41.py` **(new)**: § 8.1.

Deleted (every test in them is an upgrade path that no database takes again, § 8.2):
- `backend/tests/test_migration_v8.py`, `test_migration_v20.py`, `test_migration_v21.py`,
  `test_migration_v23.py`, `test_migration_v24.py`, `test_migration_v25.py`, `test_migration_v26.py`,
  `test_migration_v27.py`, `test_migration_v40.py`.
- `backend/tests/fixtures/migrations_v13.py`: nothing runs it after `test_migration_v20.py` goes (§ 7
  D5; KLA may keep it, § 9 Q3).

Changed:
- `test_migration_v10.py`, `test_migration_v11.py`: the re-run tests go (§ 8.2); docstrings say v41.
- `test_migration_v22.py`, `test_migration_v28.py` … `test_migration_v39.py`, `test_migration_v41.py`
  (14 files): keep the constraint tests listed in § 8.2, on the squashed v41; the other tests go.
- `test_migration_v42.py` … `test_migration_v47.py` (6 files): import from `tests.migration_helpers`;
  `VERSIONS` starts at 41 (§ 8.3).
- `backend/tests/db_names.py`: the docstring's "the migration upgrade tests' (test_migration_v2*.py)"
  becomes "(test_migration_*.py)".

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md` § Yantra Specifics › *Migrations (S025)* → *Migrations (S025, S088)*: "v1–v13
  were squashed into one migration **v20** (21-10-2026), and v20–v41 into one migration **v41**
  (S088, 31-10-2026; production was at v41); new migrations append after the last entry. … The old
  texts live only in `backend/tests/fixtures/migrations_v41.py` (frozen; it starts at v20)."
- `.claude/CLAUDE.md` § SMTW-Review › *Migrations*: "`_MIGRATIONS` starts at v41 (v20–v41 squashed
  31-10-2026, S088); v20–v41 live only in `backend/tests/fixtures/migrations_v41.py` and are never
  edited; … Check both on every migration after v41." The current sentence "v1–v13 live only in
  `backend/tests/fixtures/migrations_v13.py`" goes with D5; if KLA keeps the file (§ 9 Q3), it stays.
- `docs/schema/`: unchanged (§ 8.5). `docs/schema.md`: names no version; unchanged.
- **Comments citing old versions stay.** `backend/` and `docs/schema/notes.json` cite "v38", "v43" and
  so on (e.g. `notes.json`'s "S069 (v37) adds the root cause"). They stay: they date a column and point
  to its step, which is history, and the fixture still holds that version's text. Rewriting them would
  lose the link to the step for no gain.

## 4. Data model

No table, column, key or constraint changes. The squashed v41 holds:

1. **The DDL:** one `CREATE TABLE IF NOT EXISTS` per v41 table (46: the 49 tables of
   `docs/schema/schema.json` less `vendors`, `contracts`, `contract_equipment`), with every column in
   its v41 `ORDINAL_POSITION`, every key, foreign key and CHECK named as today. Tables are created in
   foreign-key order (a referenced table first). The FK graph at v47 (read from `vel_yantra_master`,
   31-10-2026) has no cycle except self-references (`equipment`, `improvements`, `tickets`), so one
   order exists. **How to write it:** build a v41 database from the fixture, take `SHOW CREATE TABLE`
   as the draft, and write each statement in the file's style: named constraints, no
   `AUTO_INCREMENT=n`, and each table's `ENGINE`/charset clause as the old CREATE wrote it (not the
   explicit `COLLATE` that `SHOW CREATE TABLE` prints), so a fresh database gets what the old texts
   gave it. `ENUM` values in their v41 order: e.g. `equipment_events.event` has the 12 values of
   v33's `MODIFY` (`local_db.py:1030-1033`), not v25's shorter list. **Columns not in the usual order**
   (keep them so; do not tidy): `property_definitions` (`all_classes`, `per_item_only` after
   `updated_by`, v34), `model_property_values` and `equipment_property_values` (`value_lat`,
   `value_lng` last, v34), `ticket_events` (`updated_at`, `updated_by` after `machine_stopped`, v23),
   `people` (`email` last, v27). The equivalence test catches any other.
2. **The seed rows, in the order the old migrations wrote them**, so their ids match (the
   `property_options` rows find their property by name, but the test compares whole rows, ids
   included):
   - `app_settings`: `upload_max_mb`, `internal_networks` (was v20), `escalate_minutes_a`/`_b`/`_c`
     (was v24);
   - `failure_modes`, `failure_causes`, `maintenance_actions`, `created_by` `migration-v11` (was v20);
   - `meter_types`, eight rows, `created_by` `migration-v29` (was v29);
   - `property_definitions` (22 rows) and `property_options`, `created_by` `migration-v31` (was v31);
   - `property_definitions` "GPS location", `created_by` `migration-v34` (was v34).
   The `created_by` tags stay verbatim: `backend/tests/conftest.py:197-200` (`SEED_CREATOR`, `_SEEDED_TABLES`),
   `test_failure_codes_api.py:241` and `test_meter_types_api.py:42` depend on them.
3. **Not carried over:** the statements that only convert rows that exist: v20's move of `user_units`
   into `people`/`person_units` (`local_db.py:535-540`), v25's rename and its `UPDATE equipment_events`
   (`:720-726`), v39's back-filled `improvement_events` lines and its two `UPDATE improvements`
   (`:1276-1316`), and every `RENAME`/`MODIFY`/`DROP … IF EXISTS` that brought an old table to its
   later shape. The squashed v41 runs only on an empty database (the precondition refuses any other),
   where they insert and change nothing. Every database that held such rows has v41 recorded and
   never runs it. (§ 7 D4.)
4. **Comments:** the comments of v20–v41 that explain a column's rule (why a CHECK, why a key, what a
   NULL means) are carried to the table's CREATE, shortened. The comments about a version's upgrade,
   precondition or rollback are not: they describe paths that no longer exist, and the fixture keeps
   them.

## 5. Rules

### 5.1 How the version is recorded

Unchanged engine: `pending = [m for m in _MIGRATIONS if m[0] not in applied]` (`local_db.py:1735`),
applied in list order, each recorded in `db_version` after its last statement.

| Database | Recorded | Pending after S088 | Result |
|---|---|---|---|
| fresh | none | 41, 42 … 47 | builds everything; records 41 … 47 |
| production | … 20 … 41 | 42 … 47 (the next release) | as without S088 |
| dev / test at v47 | 1–13, 20 … 47 | none | nothing runs |
| S087 coded first: at v48 | … 48 | none | nothing runs |
| an old database at v20 … v40 | some, not 41 | 41 … 47 | **refused**, nothing applied |
| a v13 or v5 database | 1 … 13 | 41 … 47 | **refused**, nothing applied |

A fresh database records v41 with the new description; production keeps its old v41 row ("One-point
lessons and their photos (S075)"). Settings › Database shows the highest version's description, so
neither shows the difference.

### 5.2 The precondition `_v41_squash_check`

- **Refuses** when `db_version` exists and holds at least one row (v41 is pending, so every row
  recorded is another version). Read through the engine's own reader: `applied =
  _get_applied_versions(cur)` (`local_db.py:1710-1715`); refuse with `max(applied)` when it is not
  empty. The check and the engine then cannot disagree on what "recorded" means (CLAUDE-COMMON § DRY).
- **Passes** when `db_version` is absent (an empty database) or empty (a half-applied fresh v41: its
  first statement created `db_version`, nothing is recorded yet), so a half-applied v41 re-runs.
- **Refusal text** (Settings › Database, IT admin; style B of CLAUDE-COMMON):
  `"This database is at schema v{N}, older than v41, and this release cannot update it. A dev or test database: drop it and start the app again. A restored production database: deploy release v0.1.14 first, which brings it to v41. — S088 § 5.2"`,
  `N` = `max(applied)`. The second case is a production dump restored from before v0.1.14 (the
  rollback path v25's comment names, `local_db.py:717-718`): the way out is the old release first.
- **Why it is needed.** Without it, a database recorded at, say, v38 would run v41: every `CREATE …
  IF NOT EXISTS` would skip its existing tables, v41 would be recorded, and v42–v47 would then run on
  tables that lack the v39–v41 columns, a wrong schema with no error until a query fails. Such
  databases exist only as old kept test databases of other run names (`vel_yantra_test_<run>_*`,
  CLAUDE.md's drop procedure removes them); production is at v41. A refusal names the cause at once.
- **Not refused:** a database with tables but no `db_version` (not a Yantra database); out of scope.
- **Accepted gap (BR1-01):** a database that an *old* release left half-way through its v20 has the
  same signature as a half-applied squashed v41 (`db_version` present and empty, some tables present,
  in their v20 shape). It passes, the squashed v41 skips those tables, and v42–v47 run on the wrong
  shape. Accepted because no such database exists: the only databases a release half-builds are
  tool-made ones (e2e, schema docs, a new test worker) that the next run drops and rebuilds;
  production and dev are past v41. *Rejected:* a shape marker (e.g. require `equipment.lifecycle`
  when `db_version` is empty: partial, and reads as complete); refusing any database with tables
  (D2: breaks the re-run of a half-applied v41).
- The engine checks every pending version's precondition before applying any (`local_db.py:1736-1740`),
  so a refused database gets neither v41 nor v42–v47.

### 5.3 Production, release and rollback

- **Production runs nothing of this step.** It has v41 recorded; the next release applies v42–v47
  (and S087's) exactly as it would have without S088. The schema docs are identical (§ 8.5), so the
  squashed text cannot have changed what production gets.
- **Production's rows** are not read or written by this step. The question "does v41 touch
  production's rows" does not arise: v41 never runs there.
- **A half-applied squashed v41** (a fresh install interrupted): every statement is `IF NOT EXISTS` or
  `INSERT IGNORE`; `db_version` is empty, so the precondition passes; the re-run completes it (§ 8.1
  test 5).
- **Rollback:** nothing to roll back on production. On a fresh install, a release before S088 sees
  v41 … v47 recorded and the same schema.
- **Pre-flight and the release tests** run the new tests (§ 8.1) in `tooling\release-tests.bat`'s
  backend suite, against the frozen fixture's shape.

### 5.4 Order with S087

S087 (brief in review) appends v48 and, per KLA's plan, folds v42–v48 into v50. **Recommended: code
S088 first.** S088 replaces `local_db.py:77-1386` and touches nothing after it (v42's comment from `:1387` stays); S087 appends after
v47. If S087 goes first, the conflict is textual only (the end of the list, S087's planned
`test_migration_v48.py` importing from `tests.test_migration_v20`, which S088 deletes). S088 first
gives S087 the helpers module, the fixture pattern, and a list of two entries to reason about.

## 6. API

No route changes. `/api/health` and Settings › Database: a refused database shows § 5.2's text, as
the old refusals did; `schema_latest` stays `LATEST_VERSION` (47).

## 7. Design decisions

- **D1. Number the squash v41, production's own version.** The base's rule ("above the highest
  recorded version") exists so that no database skips a squash whose shape it lacks. At v41, the
  databases that skip the entry are those with v41 recorded, and each of them has the v41 shape (or
  later) already: production got it through v20–v41 (each step tested on the way, and released); the
  dev and test databases likewise. Every other database runs it, and the precondition lets only an
  empty one through. So the rule's purpose holds.
  *Rejected:* **v50 (above v48).** Placed after v42–v47 in the list, it cannot work: on a fresh
  database v42 (`ALTER TABLE people …`, `local_db.py:1412-1417`) would run before the tables exist.
  Placed first in the list, out of number order, it would run on every database, production
  included, as `CREATE IF NOT EXISTS` no-ops; but `MAX(version)` would then be 50 while
  `LATEST_VERSION` (the last entry) is 47, so Settings › Database would show v50, `test_modules.py:40`
  (`schema_version == LATEST_VERSION`) would fail, and the schema docs would refuse their build
  (`schema_docs.py:110-135`: the built `MAX(version)` must equal `LATEST_VERSION`). It also takes the
  number S087 plans for its v50.
- **D2. A precondition refuses any recorded database without v41** (§ 5.2), with one accepted gap
  (a database an old release left half-way through v20, § 5.2). *Rejected:* no
  precondition (a silent wrong schema on an old database); refusing any database with tables
  (refuses a half-applied fresh v41, which must re-run).
- **D3. Old preconditions removed with their versions.** v20/v25/v34's checks guard transitions no
  database takes again. *Rejected:* freezing them into the fixture to keep their tests: the code would
  test history only.
- **D4. Row-converting statements are not carried over** (§ 4 item 3): they act only on rows an empty
  database lacks. *Rejected:* carrying them for fidelity: dead text that reads as if it mattered.
- **D5. Delete `fixtures/migrations_v13.py`** with `test_migration_v20.py`, its only user. The new
  fixture's v20 entry is itself the squash of v1–v13, and git keeps the file. *Alternative (§ 9 Q3):*
  keep it, frozen and unused, as the history of v1–v13 in the tree.
- **D6. Per-version tests: S025's rule** (§ 8.2): a test of a table's shape or a constraint stays, on
  the squashed v41; a test of an upgrade path, a re-run or an old precondition goes; a file left with
  no test is deleted. *Rejected:* (a) running all 86 old tests from the fixture (the old
  preconditions frozen too: tests of paths no database takes, at today's run time); (b) dropping
  every v20–v41 test (loses the behaviour tests of the CHECKs and keys, which the equivalence test
  compares only as text).
- **D7. Shared helpers move to `tests/migration_helpers.py`**, only those of `test_migration_v20.py`
  (deleted). Helpers in kept files (`_fill_one_ticket` in v22, `_keys`/`_foreign_keys`/
  `_one_improvement` in v36, `_add_action`/`_add_document`/… in v38, `_add_lesson` in v41) stay where
  they are, so the imports of v42–v47 need no other change. Helpers that only the dropped tests used
  go with them.

## 8. Tests and acceptance

### 8.1 New: `backend/tests/test_migration_squash_v41.py`

In `UPGRADE_DB` (`tests/db_names.py`), helpers from `tests.migration_helpers`. `SQUASHED =
[m for m in local_db._MIGRATIONS if m[0] == 41]`; `OLD = MIGRATIONS_V41`; `CURRENT =
local_db._MIGRATIONS`.

1. `test_v41_builds_what_v20_to_v41_built` (equivalence): a module fixture builds `OLD` on an empty
   database and reads `_schema()` and every table's rows, without `db_version` and without the
   columns filled by `CURRENT_TIMESTAMP` (`created_at` and the like). Then an empty database gets
   `SQUASHED`: `_schema()` equal part by part (tables, columns with position, type, default, extra,
   charset, collation; indexes; foreign keys and their columns; CHECK clauses); 46 tables; the rows
   equal (the seeds of § 4 item 2, ids included); `_versions() == [41]`.
2. `test_production_s_v41_gets_v42_to_v47` (production's path): build `OLD` (production's shape),
   add rows with the kept helpers (`_fill_one_ticket`, `_one_improvement`, `_add_action`,
   `_add_lesson`); run `CURRENT`: `_versions() == [*range(20, 48)]`; the v41 row of `db_version` keeps
   its old description; every row kept; `_schema()` equal to that of an empty database given
   `CURRENT`.
3. `test_a_database_below_v41_is_refused_unchanged`: build `OLD` up to v40 (`m[0] < 41`); run
   `CURRENT`: `MigrationBlocked` with § 5.2's text for v40; `describe_error` gives the same text;
   `_versions()` and `_schema()` unchanged (no v41, no v42).
4. `test_a_v13_database_is_refused`: a database with only `db_version` rows 1–13 (made by SQL, no
   fixture needed): refused with "v13".
5. `test_a_half_applied_v41_re_runs`: on an empty database, run an entry `(41, …, statements[:n])`
   holding the first half of `SQUASHED`'s statements, then delete its `db_version` row (a real
   half-applied run records nothing; `db_version` is now empty, so § 5.2 passes); run `SQUASHED`:
   schema and rows equal to test 1's reference, `_versions() == [41]`.
6. `test_a_rerun_keeps_edits_and_restores_a_missing_setting`: `SQUASHED`; edit a seed label
   (`failure_modes` `NOI`), set `internal_networks` to `10.24.0.0/16`, delete `upload_max_mb`; delete
   the `db_version` row 41; run `SQUASHED` twice: schema unchanged, both edits kept, `upload_max_mb`
   back at `20`, `_versions() == [41]`. (This takes over the intent of the re-run tests dropped from
   `test_migration_v10.py` and `test_migration_v11.py`.)

### 8.2 The old per-version tests

Kept (each on an empty database given `SQUASHED`; `VERSIONS = [41]`; rows inserted at the old shape
fixed where v41 needs more, *to verify*; every column v23–v41 added is nullable or has a default, so
the fills should run as they are). Each kept file's slice constants change too: `V38 = [… m[0] in
range(20, 39)]` selects nothing once v20–v40 are gone, so it becomes `SQUASHED`; a set-up such as
`_a_v37_database_with_rows` or `_a_v40_database_with_rows` becomes "`_recreate()`,
`_migrate(SQUASHED)`, the fills".

| File | Kept tests |
|---|---|
| `test_migration_v10.py` | `test_tables_and_the_default` (test DB, unchanged) |
| `test_migration_v11.py` | `test_tables_and_their_unique_keys`, `test_seed_rows` (test DB, unchanged) |
| `test_migration_v9.py`, `v12`, `v13` | all, unchanged (test DB; they never touch `db_version`) |
| `test_migration_v22.py` | `test_the_checks_hold_in_the_database` |
| `test_migration_v28.py` | `test_the_check_refuses_equipment_or_a_component_without_a_model`, `test_the_check_accepts_a_component_unit_without_a_model_and_the_fk_still_holds` |
| `test_migration_v29.py` | `test_the_name_is_unique_whatever_its_case`, `test_the_yes_no_check_refuses_a_row_of_the_wrong_shape`, `test_the_check_accepts_a_well_formed_yes_no_row_and_refuses_decimals_over_3` |
| `test_migration_v30.py` | `test_one_meter_of_a_type_per_model_and_per_node`, `test_the_limits_check_refuses_min_above_max_and_accepts_one_side` |
| `test_migration_v31.py` | `test_the_database_keeps_the_value_rules` |
| `test_migration_v32.py` | `test_the_database_keeps_the_links_and_the_lists` |
| `test_migration_v33.py` | `test_the_database_keeps_one_value_and_the_option_s_property` |
| `test_migration_v34.py` | `test_the_checks_refuse_a_broken_location` |
| `test_migration_v35.py` | `test_the_key_refuses_an_unknown_category` |
| `test_migration_v36.py` | `test_one_open_link_per_ticket_and_any_number_of_closed_ones`, `test_the_check_refuses_another_open_link_value` |
| `test_migration_v37.py` | `test_the_checks_keep_the_root_cause_whole_and_positions_from_one` |
| `test_migration_v38.py` | `test_the_checks_keep_done_and_cancelled_whole` |
| `test_migration_v39.py` | `test_the_checks`, `test_a_dropped_row_and_one_follow_up_per_improvement` |
| `test_migration_v41.py` | `test_a_document_has_exactly_one_of_five_owners`, `test_one_lesson_per_countermeasure_and_any_number_without_one`, `test_tamil_text_at_the_bounds_is_stored_whole` |

Dropped, by kind (the impl report lists each file's fate):
- **Upgrade paths:** every `test_a_v<N-1>_database_…` (e.g. `test_a_v40_database_keeps_every_row`,
  `test_a_v24_database_with_equipment_and_history_gets_v25`,
  `test_a_v38_database_keeps_every_row_and_gets_its_states_and_lines`), all of
  `test_migration_v20.py` (v13 and v0.1.3 paths) and `test_migration_v8.py` (the `user_units` move,
  which v41 does not carry, § 4 item 3).
- **Fresh-shape checks** `test_a_fresh_database_gets_v<N>` and v29's/v31's seed tests: test 1 of
  § 8.1 compares the whole schema and every seed row with the old texts.
- **Re-runs** (`test_a_rerun_changes_nothing`, `test_running_v<N>_again_…`,
  `test_a_half_applied_v38_…`, `test_a_half_applied_v41_…`, the re-runs of v10 and v11 that delete the
  `db_version` row 20 on the test DB): § 8.1 tests 5 and 6. The v10/v11 re-runs also could not stay:
  on the kept test DB, a deleted row 41 is now refused by § 5.2.
- **Old preconditions:** `test_both_columns_are_refused_unchanged`, `test_neither_column_is_refused`
  (v25), `test_the_precondition_refuses_a_hand_made_gps_location` (v34).
- **Superseded:** `test_a_document_has_exactly_one_of_four_owners` (v38): v41 counts five owners.

### 8.3 Existing tests that change or run again

- `test_migration_v42.py` … `test_migration_v47.py`: `from tests.migration_helpers import …` in place
  of `from tests.test_migration_v20 import …`; `VERSIONS = [41, *range(42, N)]`. Their slices
  (`m[0] in range(20, N)`) stay: they now pick v41 and the following entries. Nothing else; S087's
  v50 tests replace them (§ 1).
- `test_modules.py:40-41` (`LATEST_VERSION`), `test_schema_docs_shell.py:73,174`: unchanged and green
  (`LATEST_VERSION` stays 47).
- `backend/tests/conftest.py`: `_TABLES`, `SEED_CREATOR`, `_SEEDED_TABLES` unchanged (no table added; the tags kept).
  The `SEED_CREATOR` comment "for test_migration_v11.py" stays true.
- The `db_down` fixture: unchanged.
- The whole backend suite: `tooling/run-backend-tests.bat` green. The kept test databases of the
  `dev` and step runs are at v47 and skip v41; the release worktree's `vel_yantra_test_release_*` are
  at v41 or later (v0.1.14's tests ran on them on 30-10-2026), so they skip v41 too and the first
  pre-flight after S088 is safe; a kept database of an old run below v41 is refused
  (drop it by CLAUDE.md's procedure).
- No frontend or e2e change: the e2e databases are dropped and rebuilt every run
  (`tooling/e2e/e2e_backend.py:63`), so they take the fresh path. A Basic run
  (`tooling/run-e2e-tests.bat --level=basic`) once, to see the fresh path end to end.

### 8.4 On a real device

None: nothing a user sees changes.

### 8.5 Acceptance

1. `tooling\schema-docs.bat write`, then `git diff --exit-code docs/schema/`: **no change** (the main
   proof: 49 tables, every column, key, foreign key and CHECK as before; `"migration": 47`). Then
   `tooling\schema-docs.bat check` exits 0 (with the step's `YANTRA_TEST_RUN`).
2. § 8.1's six tests green; `tooling/run-tests.bat` green.
3. `_MIGRATIONS` holds v41 … v47; `MIGRATIONS_V41`'s entries equal `local_db.py:77-1386` at 26810aa, and
   `:1387-1538` (v42–v47 with their comments) is unchanged (the coder
   checks with `git show 26810aa:backend/local_db.py`, and states it in the impl report).
4. `grep -rn "test_migration_v20\|migrations_v13" backend tooling .claude/CLAUDE.md` finds nothing.
5. Basic e2e green.

**SMTW-Review point:** CLAUDE.md § SMTW-Review › *Migrations* is updated (§ 3 Docs); no new point.

## 9. Open questions and assumptions

- **Q1 (gate A). The number v41** (D1). Recommended: v41. Alternative: v50 placed first in the list,
  with the costs D1 lists.
- **Q2 (gate A). The precondition** (D2). Recommended: refuse any database with a recorded version
  and no v41. Alternative: none (a silent wrong schema on an old kept database).
- **Q3 (gate A). `fixtures/migrations_v13.py`** (D5). Recommended: delete (git keeps it).
  Alternative: keep it frozen and unused.
- **Q4. A note to SMTW-WebApp-Base** in smtw-common: "a squash may take the number of the version
  every deployed database has recorded, when the squashed entry is exactly that version's shape and a
  precondition refuses every other non-empty database". Not in this step (the base is synced); KLA
  decides whether to add it there.
- **Q5 (gate A). Old tests** (D6). Recommended: S025's rule (22 tests kept on the squashed v41).
  Alternatives: keep all, run from the fixture; or drop all.
- **A1 (fact, KLA).** Production is at v41; release v0.1.14 (`e77d635`) is the last, and its
  `_MIGRATIONS` ends at v41 (checked: `git show v0.1.14:backend/local_db.py`).
- **A2 (fact, checked 31-10-2026).** `vel_yantra_master` records 1–13 and 20–47.
- **A3 (assumption).** No other Yantra database exists outside the dev server (production, dev,
  tests, e2e). One at v20–v40 (e.g. a restored production dump) is refused by § 5.2, whose text says
  to deploy v0.1.14 first.
- **A4 (to verify by the coder).** `SHOW CREATE TABLE` plus the old charset clauses reproduce every
  `TABLE_COLLATION` and column collation; § 8.1 test 1 and § 8.5 item 1 prove it.

- **Answered at gate A by KLA, 31-10-2026 ("Approved"):** the recommended answers: Q1 v41; Q2 the precondition; Q3 delete `fixtures/migrations_v13.py`; Q5 S025's rule. Q4 (a note to SMTW-WebApp-Base) stays KLA's, outside this step.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 31-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 an old release's half-built v20 passes the precondition | minor | **Accepted** (option 1): stated as an accepted gap in § 5.2 with the reason; D2 names it |
| BR1-02 the refusal text misleads for a restored production dump | minor | **Accepted** (option 1): a second sentence per case in § 5.2; A3 updated |
| BR1-03 the precondition, keyed on 41, also guards the fixture's v41 | minor | **Accepted** (option 1): the rule in § 3's fixture entry and in the fixture's docstring |
| BR1-04 the line ranges took v42's comment | minor | **Accepted** (option 1): `:77-1386` replaced, `:1387-1538` unchanged (§ 1, § 3, § 5.4, § 8.5); v39 `:1276-1316`; the v20 move `:535-540` |
| BR1-05 the check re-implements `_get_applied_versions` | minor | **Accepted** (option 1): § 5.2 reads through `_get_applied_versions(cur)` |
| BR1-06…BR1-12 | nit | All accepted: the 12 ENUM values of v33 (BR1-06); the columns not in the usual order (BR1-07); the kept files' slices and set-ups (BR1-08); the v13 sentence of SMTW-Review (BR1-09); the old checks' users stated as verified (BR1-10); the new file renamed `test_migration_squash_v41.py` (BR1-11); the release databases in § 8.3 (BR1-12). None rejected. |
