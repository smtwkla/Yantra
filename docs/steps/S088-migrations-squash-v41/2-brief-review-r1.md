```
Step: S088 — Squash migrations v20–v41
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: 26810aa (the uncommitted working-tree edits are six frontend and e2e files of no
open step; none is a file S088 touches)

**Verdict: no blocker or major finding. Five minor findings and a short list of nits.** The numbering
departure (D1, v41) holds on every database shape I could construct; the precondition catches every
non-empty database that lacks v41; the equivalence test and the schema-docs check together prove the
squashed text. The 36-file size is right for one step: the deletions and two-line edits cannot be
split off without leaving the suite red between the halves (§ 3's own reason), and the only reviewable
unit is `local_db.py` plus the new test file. Facts file used: `scratch/brief-facts-S088.md`.

**How I checked D1 (the orchestrator's question).** `init_db` (`local_db.py:1718-1753`) computes
`pending = [m for m in _MIGRATIONS if m[0] not in applied]`, checks every pending version's
precondition, then applies in list order. With `_MIGRATIONS = [v41, v42 … v47]`:

| Database | `applied` | pending | precondition 41 | result |
|---|---|---|---|---|
| empty (e2e lanes, rebuilt each run `e2e_backend.py:63`; the schema-docs database, `schema_docs.py:104-106`; a new worker's `vel_yantra_test_<run>_gw9`; a new install) | {} | 41 … 47 | `db_version` absent → pass | builds v41, then v42–v47 |
| fresh v41 interrupted (its first statement made `db_version`, nothing recorded) | {} | 41 … 47 | table present, empty → pass | re-runs: every statement `IF NOT EXISTS` / `INSERT IGNORE` |
| production (1–5, 20–41 recorded; v0.1.14 of 30-10-2026, `_MIGRATIONS` ending at v41) | ⊇ {41} | 42 … 47 | not called (41 not pending) | as without S088 |
| dev `vel_yantra_master`, the `dev` and step-run test databases (20–47) | ⊇ {41} | none | not called | nothing runs |
| the release worktree's `vel_yantra_test_release_*` (kept between runs; last migrated by v0.1.14's tests at v41 or by a later pre-flight) | ⊇ {41} | 42 … 47 or none | not called | as production |
| `vel_yantra_upgrade_*` of any run | — | — | — | `_recreate()` drops them before use |
| a kept test database of an old run name below v41 (v13, v38 …) | rows, no 41 | 41 … 47 | rows present → **refuse** | nothing applied; `conftest` fails with the text |
| S087 coded first (… 48) | ⊇ {41} | none | not called | nothing runs |

A database that has v41 recorded got it only through the real v20–v41 texts (the version is written
after the last statement), so it has v41's shape or later; the base rule's purpose ("no database skips
a squash whose shape it lacks") is met. The one gap is BR1-01.

## Findings

### BR1-01 — minor — § 5.2: a database the *old* release left half-built passes the precondition and gets a wrong schema silently

**Problem.** The precondition passes when `db_version` is empty, to let a half-applied squashed v41
re-run. A database that release v0.1.14 (or any earlier one) started on and left half-way through its
v20 has the same signature: `db_version` present and empty, some tables present in their v20 shape
(`equipment.status`, `tickets.state` without `scheduled`, `equipment_classes` without `category_id`).
The squashed v41 then skips those tables (`CREATE TABLE IF NOT EXISTS`), records 41, and v42–v47 run
on the wrong shape: the case § 5.2 "Why it is needed" describes, through the door it leaves open.

**Why it matters.** It is the only non-empty shape the design cannot tell from the one it must accept.
No such database exists today (production is at v41; every fresh database is made by the tooling and
rebuilt), so it is a documentation gap, not a live risk.

**Options.**
1. State it in § 5.2's *Not refused* list as an accepted gap, with the reason: the only databases a
   release half-builds are tool-made ones that the next run drops; production and dev are past v41.
   **Recommended.**
2. Add a shape marker to the check: when `db_version` is empty and `equipment` exists, require its
   `lifecycle` column (the squash creates `equipment` with it; a v20 half-build has `status`). Cheap,
   but it guards only tables created after `equipment` in v20's order, so it is partial and reads as
   if it were complete.
3. Refuse any database with tables (D2's rejected alternative): simplest and complete, at the cost of
   the "a half-applied vN re-runs" convention every entry since v20 states.

### BR1-02 — minor — § 5.2: the refusal text gives the wrong way out for the one real case

**Problem.** The text ends "Drop a dev or test database and start the app again". The only way a
non-test database reaches this refusal is a production dump restored from before v0.1.14 (the rollback
path v25's comment names, `local_db.py:717-718`), and for it the advice is wrong: the way out is to
run release v0.1.14 first, which brings it to v41, then this release. A3 says so in the brief; the
screen does not. Style B asks the message to say what the user can do next.

**Why it matters.** IT admin reads this in Settings › Database with the app refusing to serve; a wrong
instruction costs a call to KLA.

**Options.**
1. Two sentences, one per case: "This database is at schema v{N}, older than v41, and this release
   cannot update it. A dev or test database: drop it and start the app again. A restored production
   database: deploy release v0.1.14 first, which brings it to v41. — S088 § 5.2". **Recommended.**
2. Keep the text and record the restored-dump case only in § 5.3 Rollback. Shorter on screen, but the
   screen then misleads in the case that matters.

### BR1-03 — minor — § 3, § 8.1: the precondition is keyed on the number 41, so it also guards the fixture's old v41; the brief does not say so

**Problem.** `_PRECONDITIONS.get(version)` is looked up by number. When a test applies
`MIGRATIONS_V41` in one call on an empty database, the check runs before anything is applied and
passes (no `db_version`). But a test that applies the fixture's v20–v40 first and its v41 in a second
call is refused: `db_version` then holds 20–40. § 8.1's six tests happen to avoid it (test 2 applies
`OLD` in one call; test 3 wants the refusal), and nothing in § 3 or the fixture's docstring states the
rule. A coder writing a seventh test, or S087's coder building "the v47 shape = `V41` then the fixture's
v42–v47" (S087 § 8.1), must know it.

**Why it matters.** A rule the coder would otherwise discover from a failing test; and S087 is told to
start from S088's helpers and pattern.

**Options.**
1. Add one line to § 3's fixture entry and to the fixture's docstring: "The engine's precondition for
   version 41 (`_v41_squash_check`) applies to this list's v41 too: apply the fixture in one call on an
   empty database, never its v41 after its v20–v40." **Recommended.**
2. Key the check on a sentinel instead of the number (e.g. check the entry's description). More code
   for a test-only concern; rejected.

### BR1-04 — minor — § 1, § 3: the line ranges `:76-1398` / `:77-1398` take v42's comment into the squash

**Problem.** v41's entry ends at `local_db.py:1386` (`]),`). Lines 1387–1398 are v42's comment
("S079 — the vendor master …"). The brief replaces `:77-1398` and calls `:1399-1538` "v42–v47
unchanged", so the coder would delete v42's comment from `local_db.py` and copy it into
`MIGRATIONS_V41`; acceptance item 3 then defines the fixture as `:76-1398` at 26810aa, which includes
that comment and the `_MIGRATIONS = [` line. S087's brief reads the same file as `:1387-1538` for
v42–v47, comment included, so the two briefs would disagree on who owns those twelve lines.

**Why it matters.** "v42–v47 byte-for-byte unchanged" (§ 1 item 1) would be false, and the fixture
would hold a comment about an entry it does not contain.

**Options.**
1. Replace `:77-1386` (the entries v20–v41 with their comments); leave `:1387-1538` unchanged; the
   fixture is `:77-1386` at 26810aa, inside a `MIGRATIONS_V41 = [` … `]` of its own. Also § 4 item 3's
   v39 range is `:1276-1316` (the second `UPDATE` ends at 1316, not 1310). **Recommended.**
2. Anchor by name instead of line (README § Anchors by name): "from the entry `(20, …` to the end of
   the entry `(41, …`". Robust if S087 is coded first after all.

### BR1-05 — minor — § 5.2: the check re-implements `_get_applied_versions`

**Problem.** The brief has the check read `information_schema.TABLES … TABLE_SCHEMA = DATABASE()` and
then `SELECT MAX(version)`, "as the old checks read". The old checks read *other* tables' columns;
this one reads `db_version`, which `_get_applied_versions(cur)` (`local_db.py:1710-1715`) already
reads with the same two steps (`SHOW TABLES LIKE 'db_version'`, `SELECT version`). Two readers of the
same table in one module is the duplicate CLAUDE-COMMON § DRY asks not to plan.

**Options.**
1. `applied = _get_applied_versions(cur)`; refuse with `max(applied)` when it is non-empty.
   Three lines, and the check and the engine cannot disagree on what "recorded" means. **Recommended.**
2. Keep the brief's text; accept the duplicate for symmetry with the removed checks (which go anyway).

## Nits

- **BR1-06** (nit) § 4 item 1: the ENUM example "`equipment_events.event` with `lifecycle`, no `status`"
  names 8 of v41's 12 values; say "the 12 values of v33's `MODIFY` (`local_db.py:1030-1033`)" so the
  coder does not stop at v25's list.
- **BR1-07** (nit) § 4 item 1: name the tables whose audit columns are *not* last at v41, so the coder
  does not tidy them: `property_definitions` (`all_classes`, `per_item_only` after `updated_by`, v34),
  `model_property_values` and `equipment_property_values` (`value_lat`, `value_lng` last, v34),
  `ticket_events` (`updated_at`, `updated_by` after `machine_stopped`, v23), `people` (`email` last, v27).
- **BR1-08** (nit) § 8.2: say that each kept file's slice constants change too (`V38 = [… m[0] in
  range(20, 39)]` selects nothing once v20–v40 are gone), and that the set-ups `_a_v37_database_with_rows`
  / `_a_v40_database_with_rows` become "`_recreate()`, `_migrate(SQUASHED)`, the fills". The header
  line "each on an empty database given SQUASHED" implies it; one sentence makes it explicit.
- **BR1-09** (nit) § 3 Docs, SMTW-Review › *Migrations*: the current point also says "v1–v13 live only
  in `backend/tests/fixtures/migrations_v13.py`"; say that this sentence goes with D5 (or stays if Q3
  keeps the file). The ellipsis hides it.
- **BR1-10** (nit) § 3 Backend: "(`grep` finds no other user: to verify by the coder)" — the facts file
  already shows `_old_tables_for_v20`, `_v20_shape_check`, `_v25_shape_check`, `_v34_gps_name_check`,
  `V34_SEED_NAME` and `V34_SEED_CREATOR` used in one code file and no test; state it as verified.
- **BR1-11** (nit) § 3 Tests: `test_migration_v41_squash.py` beside the kept `test_migration_v41.py`
  invites a mix-up in `-k` selections and in `/step` reports; `test_migration_squash_v41.py` reads apart.
- **BR1-12** (nit) § 8.3: add the release worktree's `vel_yantra_test_release_*` to the list of kept
  databases that skip v41 (they are at v41 or later: v0.1.14's tests ran on them on 30-10-2026), so the
  pre-flight's first run after S088 is known safe.

## Checked and found consistent

- The engine: `pending` in list order, every pending precondition checked before any statement runs
  (`local_db.py:1734-1740`); no engine change is needed (§ 1 Out of scope).
- The table count: v20 creates 27 tables (the old test asserts 27), v22–v41 add 19, so 46; v42–v44 add
  3, so `schema.json`'s 49 (`"migration": 47`, from `MAX(version)` of a fresh build, stays 47).
- D4: every row-converting statement is a no-op on an empty database — v20's two `user_units` moves
  (`:535-540`), v25's `UPDATE equipment_events` (`:726`), v39's seven `INSERT … SELECT` and two
  `UPDATE improvements` (`:1276-1316`); every `RENAME`, `MODIFY`, `DROP CONSTRAINT IF EXISTS` and
  `ADD COLUMN` is subsumed by the final `CREATE`. A database that held such rows has v41 recorded.
- The seed statements and their `created_by` tags: `migration-v11` (`conftest.py:197-200`,
  `test_failure_codes_api.py:241`), `migration-v29` (`test_meter_types_api.py:42`), `migration-v31`,
  `migration-v34` (`conftest._SEEDED_TABLES`) — all kept verbatim by § 4 item 2; no other code reads a
  tag (`migration-v8` is read only by the deleted `test_migration_v8.py`).
- The equivalence test's `_schema()` (`test_migration_v20.py:65-84`) compares tables with engine and
  collation, columns with position, type, nullability, default, extra, charset and collation, every index
  column, foreign keys with their rules and columns, and CHECK clauses: enough to catch a tidied column
  order, a `COLLATE` written where the old text had none, or a CHECK rewritten in other words. The
  schema-docs check (acceptance item 1) is the second, independent proof.
- The test census: 10 deleted files (v8, v20, v21, v23–v27, v40, `migrations_v13.py`), 22 changed
  (v10, v11, v22, v28–v39, v41, v42–v47, `db_names.py`), 3 new; 36 with `local_db.py`. v9, v12 and v13
  run on the test database and never read `db_version`; v10's and v11's re-run tests delete row 20 on
  the test database and cannot survive (no row 20; a deleted row 41 is refused with 42–47 present), as
  § 8.2 says. The helpers v42–v47 import (`_keys`, `_foreign_keys`, `_one_improvement`, `_link` in v36;
  `_add_why`, `_checks`, `_cause_id`, `_set_root_cause` in v37; `_add_action`, `_add_document`,
  `_documents_of_three_owners`, `_owner_check_clause` in v38; `_add_lesson` in v41; `_fill_one_ticket`
  in v22) all sit in files that keep at least one test (D7). The fills insert at the old shape, and every
  column v23–v41 added to those tables is nullable or has a default, so they should run on v41 as the
  brief's "to verify" expects.
- `test_modules.py:40-41` and `test_schema_docs_shell.py:73,174` read `LATEST_VERSION` only; the
  tooling tests read no migration text (`tooling/tests/test_schema_docs_core.py` names `user_units` as a
  notes example only).
- `.claude/CLAUDE.md`: the *Migrations (S025)* bullet and the SMTW-Review › *Migrations* point are the
  two places that name the squash; the proposed texts are right (BR1-09 for the v13 sentence).
- Standards: ISO 9001 § 7.5.3 is the right clause and is explained in plain words; no maintenance
  standard is touched; the base's squashing and precondition patterns are named, and the departure is
  stated where it is made.
- Track full, no screen, no device check: § 8.4 "None" is right.

## Feedback

- waste: reading `local_db.py` in full (1 846 lines, four reads) was asked for and was needed for D4,
  but the facts file's *Cited lines* could have printed the entry boundaries (`(41, …` at :1354, its
  `]),` at :1386) and saved the boundary hunt that produced BR1-04 (about 5 minutes).
- idea: `brief_facts.py` could list, for a cited range `file:A-B`, the first and last line's text; a
  range that ends inside the next entry's comment would then show itself.
