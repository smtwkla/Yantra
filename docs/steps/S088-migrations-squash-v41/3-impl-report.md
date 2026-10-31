```
Step: S088 — Squash migrations v20–v41
Doc: impl-report
Author: Coder (Opus, run s088c1)
Date: 31-10-2026
```

# S088 — implementation report

**Result:** built as the brief says. `_MIGRATIONS` now holds the squashed v41 and v42–v47 unchanged.
`tooling\schema-docs.bat write` leaves `docs/schema/` byte-identical (`git diff --exit-code docs/schema/`
exits 0), and `check` exits 0. All unit suites and the Basic browser run are green (numbers in § Tests).
Two small departures from the brief, both docstring-only, are in § 4.

## 1. What was built

- **One squashed migration, v41** (`backend/local_db.py`): *Full schema (squashed S001–S075)*. It holds
  46 `CREATE TABLE IF NOT EXISTS` statements in foreign-key order, every column in its v41 position, every
  key, foreign key and CHECK under its old name, then the seed rows (`INSERT IGNORE`) in the order the old
  migrations wrote them. v42–v47 follow, byte-for-byte unchanged. `LATEST_VERSION` stays 47.
- **The precondition `_v41_squash_check`** (`_PRECONDITIONS = {41: …}`): refuses a database that has
  versions recorded but not v41, with the text of § 5.2. The v20, v25 and v34 checks and their constants are
  removed.
- **The frozen fixture** `backend/tests/fixtures/migrations_v41.py`: `MIGRATIONS_V41`, the v20–v41 entries
  and their comments, verbatim from 26810aa.
- **The shared helpers** `backend/tests/migration_helpers.py` (moved unchanged from the deleted v20 test).
- **The squash tests** `backend/tests/test_migration_squash_v41.py`: the six tests of § 8.1.
- **The per-version tests** cut to S025's rule (§ 8.2); v42–v47's two-line change (§ 8.3).

## 2. How it works

- **How the squashed text was made.** A scratch script built a database from the fixture and read
  `SHOW CREATE TABLE` for each table. A second script turned each into the file's style: no backticks, no
  `AUTO_INCREMENT=n`, `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4` as the old CREATEs wrote it (none on
  `db_version` and `app_settings`, as before), `CONSTRAINT … UNIQUE` and `INDEX` lines, and no line for an
  index MariaDB makes itself for a foreign key. The CHECK texts were taken from the old statements (the last
  definition of each name), not from the server's normalised form, so they read as before. `payload` of
  `task_queue` is written `JSON`, as v20 wrote it. The seed statements are copied verbatim from the fixture
  (v20's settings and failure codes, v24's escalation times, v29's meter types, v31's properties and options,
  v34's GPS location). Then the comments were added by hand: the rule comments of v20–v41 per table,
  shortened; no upgrade, precondition or rollback comment.
- **The proof** is in three places, each comparing the old texts with the new one:
  1. `test_v41_builds_what_v20_to_v41_built`: tables, columns (position, type, default, extra, charset,
     collation), indexes, foreign keys and their columns, CHECK clauses; every row of every table with ids
     (only the `CURRENT_TIMESTAMP` columns left out); `_versions() == [41]`.
  2. The schema docs: built fresh through v41 and v42–v47, `docs/schema/` did not change.
  3. Acceptance § 8.5 item 3: the fixture's lines equal `local_db.py:77-1386` at 26810aa, and the v42–v47
     block (152 lines, from v42's comment) equals `:1387-1538` at 26810aa (both checked with `cmp` against
     `git show 26810aa:backend/local_db.py`).
- **What each database does** (unchanged engine: `pending` = every listed version not recorded):
  - an empty database: v41 builds everything, then v42–v47 run;
  - production and the dev and test databases (v41 recorded): v41 is skipped; nothing else changes
    (`test_production_s_v41_gets_v42_to_v47`: a database built by the fixture, with a ticket, an improvement, a
    countermeasure and a lesson, gets v42–v47, keeps every row and its old v41 description, and ends with the
    schema of a fresh database);
  - versions recorded but not v41: `_v41_squash_check` reads `_get_applied_versions(cur)` and refuses with
    `max(applied)`; the engine checks every pending precondition before applying any, so nothing runs
    (tests 3 and 4, at v40 and at v13);
  - `db_version` empty (a half-applied v41): the check passes and v41 re-runs to completion (test 5).

## 3. Files touched

Backend (1):
- `backend/local_db.py`: v20–v41 replaced by the squashed v41 (`:77-1386` at 26810aa); the header comment
  for two squashes; the docstring; `_v41_squash_check` replaces `_old_tables_for_v20`, `_v20_shape_check`,
  `_v25_shape_check`, `_v34_gps_name_check`, `V34_SEED_NAME`, `V34_SEED_CREATOR`.

Tests, new (3):
- `backend/tests/fixtures/migrations_v41.py`: the frozen v20–v41 texts, with the BR1-03 rule in the docstring.
- `backend/tests/migration_helpers.py`: `UPGRADE_CONFIG`, `_recreate`, `_run`, `_migrate`, `_rows`, `_schema`,
  `_versions`.
- `backend/tests/test_migration_squash_v41.py`: § 8.1's six tests.

Tests, deleted (10):
- `test_migration_v8.py`, `v20`, `v21`, `v23`, `v24`, `v25`, `v26`, `v27`, `v40`; `fixtures/migrations_v13.py`.

Tests, changed (26):
- `test_migration_v10.py`, `v11.py`: the re-run tests go (and their now unused helpers); docstrings say v41.
- `test_migration_v9.py`, `v12.py`, `v13.py`: docstring only (they named `test_migration_v20.py`; § 4 D-2).
- `test_migration_v22.py`, `v28.py` … `v39.py`, `v41.py` (14): the kept tests of § 8.2 on `SQUASHED`; the
  other tests, the slice constants, `VERSIONS` and the helpers only they used go; new docstrings.
  `test_migration_v41.py`'s set-up is renamed `_a_database_with_rows` (it builds the squashed v41 and the
  rows; the tests' second `_migrate` went).
- `test_migration_v42.py` … `v47.py` (6): `from tests.migration_helpers import …`; `VERSIONS = [41, *range(42, N)]`.
- `backend/tests/db_names.py`: "(test_migration_v2*.py)" becomes "(test_migration_*.py)".

Docs and step files:
- `.claude/CLAUDE.md`: § Yantra Specifics › *Migrations (S025, S088)* and § SMTW-Review › *Migrations*.
- `docs/steps/S088-migrations-squash-v41/1-brief.md` (Status), `docs/steps/INDEX.md` (the S088 row's status),
  this report.

### Each old test file's fate (§ 8.2)

| File | Fate | Kept |
|---|---|---|
| `test_migration_v8.py` | deleted | — (the `user_units` move, not carried) |
| `v9`, `v12`, `v13` | kept, docstring only | all |
| `v10` | changed | `test_tables_and_the_default` |
| `v11` | changed | `test_tables_and_their_unique_keys`, `test_seed_rows` |
| `v20`, `v21`, `v23`–`v27`, `v40` | deleted | — (upgrade paths, fresh-shape checks, re-runs, old preconditions) |
| `v22` | changed | `test_the_checks_hold_in_the_database` |
| `v28` | changed | the two CHECK tests |
| `v29` | changed | the three key and CHECK tests |
| `v30` | changed | the unique-key and limits tests |
| `v31`, `v32`, `v33`, `v34`, `v35`, `v37`, `v38` | changed | one test each, as § 8.2 lists |
| `v36` | changed | the open-link key and CHECK tests |
| `v39` | changed | `test_the_checks`, `test_a_dropped_row_and_one_follow_up_per_improvement` |
| `v41` | changed | the five-owner, one-lesson and Tamil tests |

## 4. Decisions taken

- **D-1 The draft was made by a script, then checked by the equivalence test** (as § 4 says: "take `SHOW
  CREATE TABLE` as the draft"). The scripts stay in `scratch/` (`s088_dump_v41.py`, `s088_gen_entry.py`,
  `s088_assemble.py`, `s088_polish.py`, `s088_compare.py`); none is part of the step.
- **D-2 Departure: `test_migration_v9.py`, `v12.py` and `v13.py` changed** (the brief says "unchanged"). Their
  docstrings named `test_migration_v20.py`, which acceptance § 8.5 item 4 wants gone. Only line 2 or 3 of each
  docstring changed; no test changed.
- **D-3 Departure: `migration_helpers.py`'s docstring** names "the v20 squash's test file", not
  `test_migration_v20.py`, for the same grep.
- **D-4 Table order.** Grouped by area (core, masters, Team, register, failure codes, tickets, access log and
  queue, meters, properties, improvements, procedures and documents), each table after the tables it
  references; the script asserted the order against the foreign keys.
- **D-5 Indexes MariaDB makes for a foreign key are not written** (the old texts did not write them either);
  the equivalence test proves MariaDB makes the same ones under the same names (e.g. `fk_memberships_site`).
  Indexes the old texts wrote under their own names stay (e.g. `ix_equipment_model`, the composite index
  `fk_equipment_models_type` that MariaDB made for the two-column key is made again).
- **D-6 `improvement_tickets.open_link`** is written `TINYINT(1) NULL DEFAULT 1` (the server prints it without
  `NULL`): same column, clearer.
- **D-7 The long ENUMs and CHECKs are wrapped** by hand to the file's width; the CHECK texts keep the old
  wording (`(level = 'equipment') = (unit_id IS NOT NULL) …`), not the server's.
- **D-8 The data section's heading** explains why the rows are in the old order and why the `created_by`
  tags stay; one-line comments were added above the escalation, meter-type and GPS seeds (their old version
  comments did not travel).
- **D-9 `_all_rows` in the squash test uses one connection** for every table: with a connection per table the
  module took 112 s, now 34 s (one process).
- **D-10 The kept tests' unused helpers went with the dropped tests** (D7: "helpers that only the dropped tests
  used go"), but helpers another kept file imports stay (`_add_document`, `_documents_of_three_owners`,
  `_owner_check_clause` in v38 for v41 and v45; `_keys`, `_foreign_keys`, `_one_improvement` in v36). Gone, for
  example: v37's `_checks` (v38 and v39 imported it only for dropped tests), v39's `_a_v38_database_with_rows`,
  v34's `_columns` and `_checks`. A scratch script (`scratch/s088_cut.py`) removed a helper only when no kept
  test, no other helper and no other test file named it.

## 5. Not done, deferred or assumed

- **Q4** (a note to SMTW-WebApp-Base about the squash number) stays KLA's, outside the step.
- `test_migration_v42.py` … `v47.py` keep docstrings that say "the v20-v41 migration tests also use" the
  upgrade database; § 8.3 asks for two lines only, and S087's v50 tests replace these files.
- The pre-existing `SyntaxWarning: invalid escape sequence '\s'` in `db_names.py`'s docstring
  (`tooling\schema-docs.bat`) is not from this step and is left.
- **Kept test databases are not at v47** (corrected in fix round 1, CR1-01). The code reviewer found: the `dev`
  run's worker databases at v33; 1 307 `vel_yantra_test_*` databases at v24-v40; the `release` ones at v41.
  After S088 a backend run without `YANTRA_TEST_RUN` (run name `dev`) is refused, because those databases hold
  versions below v41, until KLA runs the drop procedure in `.claude/CLAUDE.md` (§ Yantra Specifics, *Backend
  tests in parallel*). I dropped no database; I touched only `vel_yantra_test_s088c1_*`,
  `vel_yantra_upgrade_s088c1_*` and the `s088c1` schema-docs database.

## Tests

- **Squash tests alone:** `tooling/run-backend-tests.bat tests/test_migration_squash_v41.py -n 0`:
  6 passed in 34 s.
- **The migration test files** (26 files, targeted): 92 passed after one fix in my own new test (a `KeyError`
  for the tables v43–v45 add, in the production-path test).
- **Schema docs:** `tooling\schema-docs.bat write` (PASSED, 4 passed), `git diff --exit-code docs/schema/`
  exit 0; `tooling\schema-docs.bat check`: PASSED, exit 0. All with `YANTRA_TEST_RUN=s088c1`.
- **Full unit run** (`YANTRA_TEST_RUN=s088c1 tooling\run-tests.bat`): ALL SUITES PASSED — backend 4471 passed (195 s), frontend 408 passed
  (25 s), tooling 231 passed (1 s). The backend's 195 s is well above the usual ~40 s; I did not measure
  where the time went (the migration modules each run on one worker under `loadscope`; the squash module
  alone takes 34 s in one process).
- **Browser tests, Basic** (`tooling/run-e2e-tests.bat --level=basic`; every lane builds its database fresh
  through the new v41): 13 passed (2.5 min, all lanes done in 155 s), on `phone-chromium`.
- No frontend file changed, so no build check and no targeted browser specs.

## Manual checks

None: nothing a user sees changes (§ 8.4). No row added to `docs/steps/device-checks.md`.

## Docs updated

- `.claude/CLAUDE.md` § Yantra Specifics › *Migrations (S025, S088)*: the second squash, the precondition,
  the fixture `migrations_v41.py` and the helpers module.
- `.claude/CLAUDE.md` § SMTW-Review › *Migrations*: starts at v41; `migrations_v41.py`; "after v41". The v13
  sentence went with the file (D5).
- `docs/schema/`: unchanged, as § 8.5 requires (write left no diff; check exit 0).
- `docs/schema.md`, `docs/Plan.MD`, the domain docs: none, because no table, column or rule changed.

## Feedback

- hindrance: a scratch script cannot import `config` without `YANTRA_TESTING=1` (no `secrets_app.py`
  in the tree); found by a failed run (1 run, 1 min).
- waste: `git rm` staged the ten deletions in the index; I had to `git reset` them back to unstaged so the
  user's index stays his (1 command; the rules say "never commit", not "never stage" — worth a line).
- hindrance: `sed -i` with a multi-line Python replacement mangled two scratch scripts; the Edit tool then
  fixed them (3 tries, ~3 min; README § Shell rule 1 already says so — I broke it).
- idea: the full backend run took 195 s against the usual ~40 s; a `--durations` line in the backend
  wrapper's log would show at once whether the migration modules (one worker each under `loadscope`) are
  the cause (scratch/backend-tests-s088c1.log).

## Fix round 1

- **CR1-01 (minor), Fixed (report only).** § 5 now states the real versions of the kept databases: the `dev`
  run's worker databases at v33; 1 307 `vel_yantra_test_*` databases at v24-v40; the `release` ones at v41.
  After S088 a backend run without `YANTRA_TEST_RUN` is refused until KLA runs the drop procedure in
  `.claude/CLAUDE.md`. No code change, no database dropped.
- **CR1-02 (nit), Fixed.** `SQUASHED` is defined once in `backend/tests/migration_helpers.py` and imported by
  14 per-version test files and `test_migration_squash_v41.py` (15 files; `import local_db` stays only where
  the file still uses it).
- **Tests:** `YANTRA_TEST_RUN=s088f1 tooling/run-backend-tests.bat` on the 15 touched files: 39 passed (53 s).
  Red-then-green does not apply: no test for a fault changed.

### Feedback (fix round 1)

- none
