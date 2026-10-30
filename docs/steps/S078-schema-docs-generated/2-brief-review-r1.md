```
Step: S078 — Schema docs from the migrations
Doc: brief-review r1
Author: brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 12a682e (uncommitted: only `docs/steps/INDEX.md` and this step's folder; no step code).

Facts file: `scratch/brief-facts-S078.md` (30-10-2026 run on this draft). Dev DB read 30-10-2026 by
read-only queries (version, `CHECK_CONSTRAINTS`, counts).

## Verdict

**No blocker or major finding is open.** Three `minor` findings and eight nits. KLA's decisions of
30-10-2026 (one generated `schema.json`, the same data in `schema-data.js`, a hand-kept `notes.json`, the
page draws in the browser, no edit history, the check at three points, no documenter agent) are sound and
complete; nothing here re-opens them.

**On the cut (one step or two).** Recommendation: **one step**, as the brief proposes. Reasons: the page
is the only consumer of `schema-data.js`, so the format of § 4.2 and decision D2 are proved only when the
page draws it; the page's new code is about 150 lines plus a vitest file; and the cut's "frozen old page"
would be a third state of the docs (hand-kept, frozen, generated) for the steps in between. The brief's
length comes from exact rules and message texts, which is what the coder needs; the file count (20) is
under the limit. Given two languages, the first `notes.json` migration with its comparison script, and the
release hook, I recommend an **Opus coder**.

**The points the orchestrator asked me to weigh**, in short (details in the findings and the consistent
list): the tests' homes fit both suites; the shell test does not build a database, so the parallel
workers and the named locks are untouched; the database name, grant, lock and clean-up hold;
`release-tests.bat` reaches the dev DB through `example_secrets_app.py` (127.0.0.1:3307) exactly as the
worktree's backend suite does; the 11.4 / 11.8 question cannot block a gate B, because the check only
ever runs on the dev container (production never runs it) — the one-time diff comes when the dev image
moves to 11.8, and the brief says what to do then; `notes.json` loses nothing (46 built rows, 11 planned
rows, four tab notes, all named); the page's loading plan is right for `file://`; every repo reference is
listed and no synced file is edited.

## Findings

### BR1-01 — minor — The shell drops a database with no guard on host and name

**Problem.** § 5.1.3 runs `DROP DATABASE IF EXISTS` on `config.DB_CONFIG`'s server with the name from
`db_names.py`. The name can never be `vel_yantra_master` (it is built from the fixed part `schemadocs`),
but the host is whatever `secrets_app.py` holds when one exists: the shell runs with `YANTRA_TESTING=1`,
which only falls back to the example file when the real one is absent. The repo already has the guard for
this case: `tooling/e2e/e2e_backend.py` `check_target` refuses a host outside `LOCAL_HOSTS` and a name
without the expected ending before `_recreate_database` drops anything.

**Why it matters.** A destructive command on a server named by a secrets file deserves the same two-line
guard the e2e backend has; without it the brief leaves the coder to decide whether to add one.

**Options.**
- (a) **Recommended**: the shell refuses, with exit 2, a host not in the e2e backend's `LOCAL_HOSTS`
  and a database name that does not end in `_schemadocs`, before the lock and the drop; message in the
  form of `check_target`'s. Mirror `_recreate_database` (DROP then CREATE on a connection with no
  database selected) rather than `conftest._create_test_db` (CREATE IF NOT EXISTS), which is the pattern
  § 5.1.3 cites today.
- (b) Import `check_target` from `tooling/e2e/e2e_backend.py` — rejected: that module imports the app and
  the harness at module level; a copy of three lines is cheaper than the import.
- (c) No guard, as drafted.

### BR1-02 — minor — Where the gate B check runs, and the run name, for a worktree-coded step

**Problem.** § 5.7.2 and the § 5.10 row say the orchestrator runs `tooling\schema-docs.bat check` at
gate B, with a non-zero exit a blocker. The step skill lets a second coder work in its own git worktree
(`.claude/skills/step/SKILL.md` § Parallel steps). For such a step the main working folder holds neither
the migration nor the new `docs/schema/` files, so a check run there reports the previous step's state:
green for a stale doc, or red for a migration that is not this step's. The brief names the folder for the
INDEX.md edit (§ 3, "the coder in a worktree") but not for the check. The run name has the same gap: the
orchestrator's check and a coder's `write` in the same minute with `YANTRA_TEST_RUN` unset share
`vel_yantra_test_dev_schemadocs` and wait on each other's lock (harmless, but the 60 s wait and the
exit-2 message would surprise).

**Why it matters.** A gate B blocker must be judged on the tree that holds the step's changes.

**Options.**
- (a) **Recommended**: in § 5.7.2 and in the § 5.10 row add: the check runs in the tree that holds the
  step's changes (the coder's worktree when it used one, else the working folder), with
  `YANTRA_TEST_RUN` set to the step's run name (as the test runs: `s078c1` style), so it never shares a
  database with a run in progress.
- (b) Run it in the main folder after adopt — rejected: gate B comes before the commit.

### BR1-03 — minor — The catalogue read of checks: the filter column, and the one column-level CHECK

**Problem.** Two facts of § 5.2 differ from the server (read 30-10-2026 on the dev DB, 11.4.13):
1. `information_schema.CHECK_CONSTRAINTS` has no `TABLE_SCHEMA` column; its columns are
   `CONSTRAINT_CATALOG`, `CONSTRAINT_SCHEMA`, `TABLE_NAME`, `CONSTRAINT_NAME`, `LEVEL`, `CHECK_CLAUSE`.
   The filter is `CONSTRAINT_SCHEMA` (as every `test_migration_*` test writes it). The brief's table says
   "five result sets for `TABLE_SCHEMA = SCHEMA_DOCS_DB`".
2. One of the 29 checks is **column-level**: `task_queue` has `LEVEL = 'Column'`, `CONSTRAINT_NAME` =
   `payload`, clause `` json_valid(`payload`) ``. The other 28 are `Table` and named `chk_*`. The brief
   does not read `LEVEL`, and § 5.9's naming bullet says a check is `chk_<table>_<what>`, so `payload`
   would look like a broken name to a reader, and the coder has to decide how to write it.

**Why it matters.** (1) costs the coder a run; (2) is a rule the coder would set alone, and the Tables
view's *Checks* table shows it.

**Options.**
- (a) **Recommended**: read `LEVEL` too and write it on the check line (`"level": "table" | "column"`,
  lower case); a column-level check's name is the column's, as MariaDB names it. Add `payload` to § 5.9's
  naming bullet as the second exception beside `ux_access_log_sighting`. Correct the filter column.
- (b) Leave `LEVEL` out and only note the exception in § 5.9 — fewer keys, but the JSON then shows a
  check named like a column with no hint why.

## Nits

- **BR1-04** (nit) § 3 / § 5.5: a script run by path has its own folder as `sys.path[0]`, not the
  current folder, so `schema_docs.py` must insert `backend/` (from its own path: `parents[2] / "backend"`)
  before `import config, local_db` and `from tests.db_names import SCHEMA_DOCS_DB`. Say so; "it runs in
  the backend's uv project" only gives it the venv.
- **BR1-05** (nit) § 5.5 *Output*: on exit 2 no count line prints, so `run_test_suite.counts_of` writes
  "no test counts found" in the summary line. Either accept that in the text, or print
  `Schema docs: not completed` as the last line and say the summary shows no counts.
- **BR1-06** (nit) § 5.3 / § 5.5: say the order: the shell parses `notes.json` **before** it builds the
  database, so an invalid file ends the run in a second (exit 1, checks 3 and 4 failed), not after a
  migration build. Also say what check 3 does with a `tables` entry that lacks `area` or `holds` (treat a
  missing `area` as the "names area" message with `(none)`, and an empty or missing `holds` as a problem
  of its own or as allowed — one line decides it).
- **BR1-07** (nit) § 5.3: "the committed file" means the file on disk in the tree being checked (in the
  working folder it is often uncommitted). Write "the file on disk" once and keep it.
- **BR1-08** (nit) § 2: the sub-clause letters are right; drop the *to verify* marks. ISO 9001:2015
  7.5.2 a) is "identification and description (e.g. a title, date, author, or reference number)";
  7.5.3.1 a) "it is available and suitable for use, where and when it is needed"; 7.5.3.2 c) "control of
  changes (e.g. version control)". For KLA: 7.5.2 says a document must say what it is and which version;
  7.5.3 says the documents the work relies on must be at hand, fit for use, and changed only under
  control — here the migration number is the identification, the check is the control.
- **BR1-09** (nit) § 5.10 the schema row: add "or edits `docs/schema/notes.json`" to the *due when*
  text; § 5.7.1 names it, the row does not, and the row is what the coder reads (D2 makes a notes edit
  need a `write`).
- **BR1-10** (nit) § 5.7.3: `run-tests.bat` prints its summary block before the schema line is appended
  to `test-summary-release.txt`, so the line is in the file but not in that block; `schema-docs.bat`'s
  own last line shows it. Say so, so nobody looks for it in the block.
- **BR1-11** (nit) § 8.2 test 1: say the shell reads `config.DB_CONFIG` inside `main` (a copy at import
  would not see the monkeypatch), and that the refused connection is the first one (no database
  selected), before any lock.

## Checked and found consistent

- **Facts**: 46 base tables, 75 foreign keys, `db_version` at 41, server 11.4.13 (dev DB, 30-10-2026);
  today's page says 45 tables because it leaves `db_version` out (D6). `schema.md` has 46 built rows and
  11 planned rows (57 table rows), four tab notes in `TABS`; § 5.8's lists add up to 46 (20 + 7 + 14 + 5).
- **D5 and § 5.4 against the DDL**: `uq_sites_default (is_default)`, `uq_improvements_follow_up
  (follow_up_of_id)` and `uq_procedures_action (action_id)` are single-column, so `UK` and `o|--o|` hold;
  `uq_improvement_tickets_open (ticket_id, open_link)` is composite, so `open_link` loses `UK` as the
  brief says. `open_link` is a plain column (`DEFAULT 1`), not a generated one; no generated columns on
  the dev DB.
- **§ 5.2 normalisation against the server**: `int(11)`, `bigint(20)`, `tinyint(1)` are printed;
  `COLUMN_DEFAULT` is `current_timestamp()` and SQL NULL for the auto-increment ids; `EXTRA` is
  `auto_increment` and `on update current_timestamp()`; check clauses come back-quoted and lower-cased.
  Only `information_schema` is read: no rows, no secrets (ISO 27001 point holds).
- **The database name**: `_part` keeps lower-case letters and digits, cut to 12, so `schemadocs` is
  10 characters and never a worker part (`gw<n>`, `main`); the lock name
  `yantra_schema_docs:vel_yantra_test_<run>_schemadocs` is at most 58 characters (limit 64 in
  `named_lock`); the grant `vel\_yantra\_test\_%` (init-test-db.sql, run-backend-tests.bat) covers it;
  the drop list in CLAUDE.md § Dev commands covers it; `init_db`'s lock is `yantra_migrations:<db>`, a
  different name.
- **The tests' homes**: the tooling suite runs `uv run --no-project --with pytest … pytest -q
  tooling\tests` from the repo root with `tooling/` on `sys.path` (its `conftest.py`); a stdlib-only core
  imported from `tooling/schema` works there. The backend suite runs `tests/` with `backend/` on the
  path; the shell test's two cases touch no `SCHEMA_DOCS_DB`, so pytest-xdist's workers and the named
  locks are unaffected; vitest's default include takes `frontend/tests/schemaView.test.js` (only `e2e/**`
  is excluded; environment jsdom, `node:vm` is fine there).
- **The release hook**: `release-tests.bat` sets `YANTRA_TEST_RUN=release` and `YANTRA_TEST_LOG_DIR`
  for the whole script; the worktree has no `secrets_app.py`, so `YANTRA_TESTING=1` takes
  `example_secrets_app.py` (`127.0.0.1:3307`, `vel_yantra_master` user), as the worktree's backend suite
  already does; `run_test_suite.py` passes exit 2 through; `TEST_SUMMARY_FILE` must be set again after
  `run-tests.bat` (its `setlocal` drops it) — the brief does that.
- **Down and concurrent**: a refused connection on 127.0.0.1 fails at once (`OperationalError` 2003),
  caught as `pymysql.MySQLError`; two run names never share a database; the same run name waits on
  `GET_LOCK` 60 s then exits 2; a cut-off run's lock dies with its session and its database is dropped by
  the next run.
- **References**: every `schema.md` / `schema.html` cite outside the step folders is in the brief
  (`.claude/CLAUDE.md` lines 9, 51, 71; `docs/Plan.MD` 901–903; R02 68, 72, 77; R03 49, 57, 62; R05 70;
  the page's own footer); `docs/review/*` and `docs/steps/feedback-log.md` are records; the synced
  `.claude/skills/smtw-review/SKILL.md` and `SMTW-WebApp-Base.md` § layout go to the F1/F2 follow-ups.
  The coder's rule "never edit a file marked … generated" (`.claude/agents/coder.md`) matches the
  `_note` wording "Generated by …".
- **Design and structure**: pure core (rows in, text and problems out), thin shell, the page's pure
  functions in one classic script tested in `node:vm`; one wrapper through `run_test_suite.py`; no new
  dependency; no abstraction without a second use.
- **Page texts** (scope B): buttons start with a verb (`Show diagram`, `Show tables`, the zoom buttons
  as today); the three messages say what happened and what to do; no codes.
- **Manual check**: one, marked important, with where (KLA's laptop), browsers and network; a browser
  engine could open `file://`, but the brief's D10 reason (the CDN, the app's harness) is sound, and the
  check is rightly not a row of the IT Admin device list.
- **Standards**: ISO 9001 § 7.5.2 and § 7.5.3 named and explained (letters confirmed, BR1-08); the
  maintenance standards rightly not touched.

## Feedback

- waste: the facts file lists 95 code names, most of them SQL identifiers (`TABLE_NAME`, `COLUMN_TYPE`,
  every table name) with "defined at none found" and long test-file lists; about 250 of its 331 lines
  gave this review nothing (`scratch/brief-facts-S078.md` lines 61–325).
- idea: `brief_facts.py` could skip a backticked name that is an upper-case `information_schema` column
  or a table name found in the migrations' DDL, or fold them into one "SQL names" line.
- rule: the brief carries `Baseline: 12a682e` while `In review`; `docs/steps/README.md` § Stale brief
  check says the orchestrator copies the review's line at approval. Harmless, but the two differ.
