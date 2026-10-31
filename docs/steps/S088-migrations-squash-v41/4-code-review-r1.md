```
Step: S088 — Squash migrations v20–v41
Doc: code-review r1
Author: Code reviewer (Opus, run s088cr1)
Date: 31-10-2026
```

# S088 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There is 1 minor finding and 1 nit. The
squashed v41 builds the same schema and seed rows as v20–v41. The fixture is byte-equal to
26810aa, and v42–v47 are unchanged. All suites are green, and the schema docs check exits 0. The
minor finding is about the dev machine, not the code: the default `dev` run's kept test databases
are at v33, so the next backend run without a run name is refused until they are dropped.

## Test results (run `s088cr1`)

- `tooling\run-tests.bat`: **ALL SUITES PASSED**. Backend 4471 passed (222 s; a new run name, so
  the worker databases were built first), frontend 408 passed, tooling 231 passed
  (`scratch/test-summary-s088cr1.txt`).
- `tooling\schema-docs.bat check`, after the suites: **PASSED, exit 0**. The fresh build applied
  v41 (squashed), then v42–v47; "Schema docs at migration v47: 4 passed". `git diff 26810aa --
  docs/schema/` is empty.
- Browser tests: none run by me. No frontend file or API is part of this step; the frontend and e2e
  edits in the tree are KLA's and are not reviewed here. The coder's Basic run (13 passed, every lane
  built fresh through the new v41) is the run that brief § 8.3 asks for.

## Own checks of the focus points

- **Fixture byte-equal (§ 8.5 item 3).** A scratch script compared the lines inside
  `MIGRATIONS_V41 = [ … ]` with `git show 26810aa:backend/local_db.py` lines 77–1386: equal, 1310
  lines. It also compared the v42–v47 block, from v42's comment, with lines 1387–1538: equal, 152
  lines, followed by the same `]`.
- **v42–v47 unchanged** (above). `LATEST_VERSION` is still 47.
- **The equivalence test is real.** `_schema()` compares the following:
  - tables, with engine and collation;
  - columns, with position, type (ENUM values in order), nullability, default, extra, charset and
    collation;
  - indexes, with the ones MariaDB makes for foreign keys;
  - foreign keys, with their rules and columns;
  - CHECK clauses, in the server's normalised text.

  `_all_rows()` compares every row of every table, ids included; only the `CURRENT_TIMESTAMP`
  columns are left out. A lost column, key, CHECK, collation, ENUM value or seed row therefore fails
  the test, and so does a seed row in the wrong order (different ids). The comparison leaves out
  column and table comments, generated-column expressions and index prefix lengths. A grep of the
  fixture finds none of them, so for v20–v41 the comparison is complete.
- **The precondition on every database shape (§ 5.2).**
  - `_v41_squash_check` reads `_get_applied_versions(cur)`. With `db_version` absent or empty it
    passes; otherwise it refuses with `max(applied)`.
  - The engine checks every pending precondition before it applies any (`init_db`, `local_db.py:1413-1417`).
    So a refused database gets neither v41 nor v42–v47.
  - Tests 3 and 4 cover v40 and v13; test 5 covers a half-applied v41.
  - Production (v41 recorded) never calls the check, because v41 is not pending there.
  - The old precondition functions had no other user: a grep finds no `_PRECONDITIONS` or
    `MigrationBlocked` outside `local_db.py`, except comments in the frozen fixture.
- **Production's path.** `test_production_s_v41_gets_v42_to_v47` builds the fixture's shape with a
  ticket, an improvement, a countermeasure and a lesson. It then runs the current list and proves
  four things: versions 20–47 are recorded, the old v41 description is kept, every row is kept, and
  the schema equals a fresh build.
- **Release databases.** A read-only query of the dev server (31-10-2026):
  `vel_yantra_test_release_gw0`…`gw7` and `_main` are at v41. They skip the squash, so the first
  pre-flight after S088 is safe.
- **Tests kept and dropped (§ 8.2).** Each kept file holds exactly the tests that § 8.2 lists, on
  `SQUASHED`. The cross-file helpers still exist where other files import them (v22
  `_fill_one_ticket`; v36 `_keys`, `_foreign_keys`, `_one_improvement`; v38 `_add_action`,
  `_add_document`, `_documents_of_three_owners`). The suite's green run confirms the imports.
- **Acceptance § 8.5 item 4.** No hit for `test_migration_v20`, `migrations_v13` or the removed
  checks in `backend`, `tooling` or `.claude/CLAUDE.md`, the new untracked files included.

## Findings

### CR1-01 (minor) — the `dev` run's test databases are at v33, so a default backend run is refused

- **Where:**
  - the brief, § 8.3: "The kept test databases of the `dev` and step runs are at v47";
  - `3-impl-report.md` § 5: "Kept test databases of other run names below v41 (if any)".
- **Problem:** a read-only query of the dev server (31-10-2026) shows the default run's worker
  databases `vel_yantra_test_dev_gw0` … `gw7` at **v33** (only `vel_yantra_test_dev_main` is at v46).
  The report does not state the real state. In all, 1 307 `vel_yantra_test_*` databases are at
  v24–v40.
- **Failure scenario:** KLA runs `tooling\run-tests.bat` or a PyCharm test config without
  `YANTRA_TEST_RUN` after this step is committed. Before S088 the engine would have brought those
  databases from v33 to v47. Now `_v41_squash_check` refuses them, so `conftest._clean_tables` fails
  every test on every worker: "Test database not ready (is the dev DB up?): This database is at
  schema v33, older than v41 …". Nothing is damaged, and the message says to drop the database, but
  the whole backend suite is red until someone acts. The same happens to any old run name that is
  used again.
- **Fix:** no code change. At gate B, tell KLA to run the drop procedure in `.claude/CLAUDE.md`
  (§ Backend tests in parallel, two steps) before the next test run without a run name. That
  procedure drops every `vel_yantra_test_*` and `vel_yantra_upgrade_*`. In the impl report, change
  § 5's "(if any)" to the real state (the `dev` workers at v33).

## Nits

- **CR1-02** (nit) `backend/tests/test_migration_v22.py:13` (and v28–v39, v41,
  `test_migration_squash_v41.py:27`): the same `SQUASHED = [m for m in local_db._MIGRATIONS if
  m[0] == 41]` is written in 16 files. Define it once in `tests/migration_helpers.py` and import it.

## Scope and decisions

- Everything that § 3 asks for is built. Nothing beyond it is built.
- D-2 (the docstrings of v9, v12 and v13) and D-3 (the helpers' docstring) are departures, and the
  report lists both. They are needed for § 8.5 item 4 and change no test.
- D-4 to D-10 are choices in how the code is written. The equivalence test covers each of them.
- **Track:** full. No track finding.
- **Docs pass:** the report's `## Docs updated` matches the diff and § Docs to keep current.
  `.claude/CLAUDE.md` § Migrations (S025, S088) and § SMTW-Review › Migrations are updated. The
  `docs/schema/` files are unchanged, and the check exits 0. `Plan.MD` and the domain docs: no
  change is due.
- **Manual checks:** the brief has none (§ 8.4), and the report says so. No device-check row is due.

## Manual browser check for the user

None. Nothing a user sees changes. A refusal shows only on a database below v41, and test 3 checks
its text through `describe_error`.

## Checked and found consistent

- `local_db.py`: the docstring and the header comment (two squashes, why v41, the fixture's name).
  The squashed entry: 46 `CREATE TABLE IF NOT EXISTS` statements in foreign-key order, then the seed
  rows as `INSERT IGNORE` in the old order with the `created_by` tags verbatim (`conftest.SEED_CREATOR`
  and `_SEEDED_TABLES` still match). The rule comments of the tables are carried over, and the
  upgrade comments are left out (§ 4 item 4). `user_units` is kept, empty, as the brief says.
- `_v41_squash_check`: its text equals § 5.2, and `_PRECONDITIONS = {41: …}`. The engine is unchanged.
- `tests/fixtures/migrations_v41.py`: the frozen docstring carries the BR1-03 rule (apply it in one
  call on an empty database).
- `tests/migration_helpers.py`: the helpers are moved unchanged.
- `test_migration_squash_v41.py`: the six tests of § 8.1. The refusal is asserted as an exact text.
  The half-applied test asserts that some tables, but not all of them, exist before the re-run.
  Test 6 takes over the re-runs dropped from `test_migration_v10.py` and `test_migration_v11.py`.
- `test_migration_v42.py` … `v47.py`: two lines each, as § 8.3 says.
- `backend/tests/db_names.py`: the docstring.
- Edge cases:
  - DB down: the engine is unchanged, and `ensure_schema` still keeps a refusal for Settings ›
    Database.
  - Concurrency: the precondition runs inside the migration lock, as before.
  - Security: no route, permission or SQL built from strings in the step's code. The f-string seeds
    of `property_options` are constant text copied from v31.

## Feedback

- hindrance: `ast.literal_eval` cannot read `_MIGRATIONS`, because the property-options seed is a
  starred generator. A Python-level comparison of the old and new lists needed a fallback to a
  line comparison (1 failed run, about 1 min; `scratch` script `cmp_fixture.py`).
- idea: the brief's facts about kept test databases ("the `dev` runs are at v47") were not checked
  against the server. A read-only `MAX(version)` query per `vel_yantra_test_*` database (two
  `docker compose exec` calls) found the `dev` workers at v33. A step that adds a precondition could
  have `step-brief-facts` or the coder run that query (about 1 min).
