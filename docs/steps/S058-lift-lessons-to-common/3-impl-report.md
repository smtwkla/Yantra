```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: impl report
Author: Coder (Sonnet)
Date: 26-10-2026
Brief: 1-brief.md (Approved 26-10-2026, U2)
Track: light
```

# S058 — Implementation report

## 1. What was built

- One code change: the environment variable `YANTRA_TEST_SUMMARY` is now `TEST_SUMMARY_FILE`, so the
  script that is lifted to `smtw-common` names no repo.
- Thirteen ready-to-paste texts for `CLAUDE-COMMON.md` (points 1–4) and `SMTW-WebApp-Base.md` (points
  5–10, 12, 13, W), each with its place and the base sentences it replaces or amends (§ 8).
- The lift list for the tools (§ 9) and the list of what `.claude/CLAUDE.md` shrinks to after the
  lift (§ 10).

Nothing was written to `../smtw-common`. `.claude/CLAUDE.md` is not shrunk and not changed (it does not
name the variable).

## 2. How it works

`tooling/run_logged.py` appends its summary line to the file named by `TEST_SUMMARY_FILE`, when that
variable is set. `tooling/run-tests.bat` sets the variable (per run name: `test-summary.txt`, or
`test-summary-<run>.txt`), deletes the old file, lets the four suites append, and prints the file at the
end. Only the name changed.

Grep of the whole repo (excluding `node_modules`, `.git`, `scratch`) for `YANTRA_TEST_SUMMARY` before the
change found the three files of the brief and nothing else in code, `.claude`, `.run`, `.idea`, `backend`
or `frontend`. The other hits are the step documents (this brief, its review, the S049 review and the
`INDEX.md` row), which describe the old name and are history; I did not edit them. After the change the
only code hits for the old name are two stale `__pycache__` files (not tracked).

## 3. Files touched

| File | Change |
|---|---|
| `tooling/run_logged.py` | docstring line 10 and `os.environ.get` at line 63: `TEST_SUMMARY_FILE` |
| `tooling/run-tests.bat` | lines 10, 11, 12, 22: `TEST_SUMMARY_FILE` |
| `tooling/tests/test_run_logged.py` | line 41: `monkeypatch.setenv("TEST_SUMMARY_FILE", …)` |
| `docs/steps/S058-lift-lessons-to-common/3-impl-report.md` | this report |

Count: 3 code files, 1 report. (`INDEX.md` already shows S058 as Implementing; I set the brief's status
line no further: it stays `Approved` until the orchestrator moves it, see § 5.)

## 4. Decisions taken

1. **The tests' own `sys.path` line at the new place** (§ 9) is given for both lifted test files; the
   brief asked for it for `run_logged` and, by BR1-03, an import path for the deps tests.
2. **Deps fixtures** move into `tooling/common/tests/fixtures/deps/` (a sub-folder) so they cannot clash
   with other tests' fixtures; the lifted test then needs `FIXTURES = Path(__file__).parent / "fixtures" / "deps"`.
3. **ISO 27001:2022 Annex A numbers** (§ 7) are from my knowledge of the 2022 edition; the standard is
   paywalled and I could not check the text. Each number carries "to verify".
4. **Point 7 and W wording keep the base's start intact.** The base's single test database stays the
   default; the parallel set-up is a "next stage" sub-section (U1). The worker text makes the built-in
   schedule the default and APScheduler the named option (U2 Q4).
5. **Point 10 adds one bullet the brief did not list** ("a refusal or message is asserted in view",
   from S054's rule in `CLAUDE.md`); keep or drop it when pasting.
6. **Point 1 stays at S032's scope** (mail relay hosts, ports, credentials; any person's address). I wrote
   the closing sentence of the rule so it does not claim public URLs or realm names are secret.

## 5. Not done, deferred, assumed

- Not done (by design): no paste into `smtw-common`; `CLAUDE.md` not shrunk; no test moved or deleted;
  `tooling/deploy.py` not lifted (point 9 is the rule only); point 11 not touched.
- Assumed: S057's lift is pasted first or together; nothing below repeats it.
- The brief's `Status` stays `Approved` in the file and the orchestrator sets `In code review` (I was told
  not to edit anything beyond the listed files and the report). **Orchestrator: please set it.**
- Checked while writing, for the reviewer: the base's `## Stack` row *Scheduling* and the project layout
  line `worker.py # Separate process: APScheduler + task_queue drainer` and `scheduled_tasks.py # Cron
  registry` also name APScheduler or cron; point W's text amends them too (§ 8, W).

## 6. Tests

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s058c1 tooling/run-tooling-tests.bat` | `== tooling: PASSED in 2 s: 173 passed` (log `scratch/tooling-tests-s058c1.log`) |
| `YANTRA_TEST_RUN=s058c1 tooling/run-tests.bat` (all four suites) | see § 6.1 |

`grep -rn YANTRA_TEST_SUMMARY tooling` (source files): no hit.

### 6.1 Full run

`YANTRA_TEST_RUN=s058c1 tooling/run-tests.bat`, all four suites green; the closing "Test summary" block
was printed from `scratch/test-summary-s058c1.txt`, so the renamed variable works end to end:

- backend: PASSED in 119 s: 3075 passed
- frontend: PASSED in 31 s: 179 passed
- deps: PASSED in 0 s: 42 passed
- tooling: PASSED in 2 s: 173 passed
- `== ALL SUITES: PASSED`

No browser tests (no screen or API change).

## 7. Standards and practice

- **ISO 9001:2015 § 7.5.3** (control of documented information): a lesson learnt in one repo is
  recorded once, in the controlled common document, and each repo points at it.
- **ISO/IEC 27001:2022 Annex A** (numbers from memory of the 2022 edition, **to verify** against the
  standard text):
  - point 2 (software inventory and audit): A.8.8 *Management of technical vulnerabilities* (know what
    you run, check it against published vulnerabilities); A.5.9 *Inventory of information and other
    associated assets* (the SBOM is an inventory of software components).
  - point 1 (mail relay values and personal addresses out of the repo): A.5.17 *Authentication
    information* (relay credentials); A.5.34 *Privacy and protection of PII* (personal email addresses).
- No maintenance standard applies.

These references are for KLA's information. They are **not** written into the common texts below, which
stay generic; KLA may add them to the paste if wanted.

## 8. Lift to smtw-common

Each text is for any SMTW app: no Yantra name, value or step number in the rule itself, a provenance tag
at most. "Replaces" quotes the current sentence in the file as it stands in Yantra's synced copy
(`.claude/CLAUDE-COMMON.md`, `.claude/SMTW-WebApp-Base.md`, read 26-10-2026). Where I write
*(new)*, nothing is replaced.

### 8.1 To `CLAUDE-COMMON.md`

#### Point 1 — Mail relay values and personal addresses

**Where:** `### Conventions`, a new bullet directly after the **Secrets** bullet. **Replaces:** nothing
(the Secrets bullet stays: "**Secrets**: Credentials in gitignored `secrets_*.py` files, with
`example_secrets_*.py` templates. (Canonical description — repo `CLAUDE.md` links here, doesn't
restate.)").

```markdown
- **Mail relay values and personal addresses never go into a repo**: the host, port and credentials of a
  mail relay, and any person's email address, appear nowhere in the repo — no code default, example,
  test value or doc. They come from the deployment's variables (Ansible), through the secrets file.
  Tests and examples use reserved names (`example.test`). A person's address comes from the login
  token, is never typed in, and is shown only to its owner and the administrator. A background-task
  payload carries the person's id, never the address, so the queue and the logs hold no address.
  (Yantra, S032, 24-10-2026.) This covers the mail relay and people's addresses only; other service
  URLs, realm names and deployment paths may be in a repo.
```

#### Point 2 — Software inventory

**Where:** `### Engineering rules`, directly after **Dependency health**. **Amends:** it adds the method to
"**Dependency health**: Prefer actively maintained libraries. Flag dependencies that are unmaintained (no
release in 12+ months, archived repo), end-of-life, or abandoned, and suggest a maintained alternative."
That sentence stays.

```markdown
- **Software inventory**: keep a CycloneDX software bill of materials (SBOM) for every lockfile
  (`uv.lock`, `package-lock.json`) in `sbom/`, one file per lockfile named after its folder
  (`backend.cdx.json`). Generate it with the audit script, never edit it by hand, and commit `sbom/`
  with every dependency change. The audit (`tooling/deps/audit.py`, wrapper `tooling/run-deps-audit.bat`)
  looks every library up in OSV and flags direct dependencies with no release in 12 months, as *Dependency
  health* asks. Exit codes: **0** clean, **1** a critical, high or unknown-severity vulnerability, **2** the
  check could not be completed. Run it before a release; keep it out of the normal test run (it needs the
  network). Its report goes to `scratch/dependency-report.md`. (Yantra, S022, 18-10-2026.)
```

#### Point 3 — Test output

**Where:** `### Wrapper scripts`, a second paragraph after the existing one. **Replaces:** nothing. The
existing paragraph stays: "Wrap recurring test/build/query commands in `tooling/*.bat` (or `.sh`) scripts
so Claude Code permissions can whitelist them once. Prefer running the wrapper over retyping the raw
command."

```markdown
A test wrapper writes the suite's whole output to `scratch/<suite>-tests.log` (with the run name,
`scratch/<suite>-tests-<run>.log`, when one is set) and prints one last line:
PASSED or FAILED, the counts, the time and the log path (`tooling/common/run_logged.py` does this for
any command). Read that line and the log; never run the suite again just to see its summary. A
wrapper that runs several suites sets `TEST_SUMMARY_FILE` to a file, so each suite appends its line and
the wrapper prints all lines again at the end.
```

#### Point 4 — Known faults are marked strict

**Where:** `### Engineering rules`, directly after **Testing**. **Replaces:** nothing; it adds to "**Testing**:
Write tests for new functionality — happy path plus key failure modes."

```markdown
- **Known faults are marked strict**: a test that fails because of a fault you accept for now carries a
  strict expected-failure mark that names the step and the fault, so the run turns red when the fault
  is fixed and the mark has to come off. A test that also passes now and then is no known fault: fix
  the test. The mark's syntax for each test tool is the repo's `## Pre-flight` setting *Known fault*
  (`SMTW-WebApp-Base.md` § Pre-flight Before Every Release); this rule does not repeat it.
  (Yantra, S049, 25-10-2026.)
```

### 8.2 To `SMTW-WebApp-Base.md`

#### Point 5 — The app runs while the database is missing or down

**Where:** `## DB Connection Pattern`, a new `###` sub-section after "### Per-request connection from a
pool, cached on `g`" and before "### Timezone policy".

**Amends:** § Local DB Migration Pattern, the bullet "`init_db(config)` is called at startup and applies any
pending migrations automatically." is replaced by:

```markdown
- `ensure_schema(config)` applies any pending migrations; `app.py` at start, the first requests and the worker call it
  (§ DB Connection Pattern › The app runs while the database is down). `init_db(config)` is what it
  runs.
```

and in § Singleton via DB lock the sentence "Gunicorn workers boot concurrently, so every worker calls
`init_db`." becomes "Gunicorn workers boot concurrently, so every worker calls `ensure_schema`, which runs
`init_db`." (the rest of that paragraph stays).

New sub-section:

```markdown
### The app runs while the database is missing or down

A fresh deployment starts before its database exists, and a database restart must not take the app
down. So:

- **Nothing fails at import.** Create the pool lazily (it opens no connection). `app.py` calls
  `ensure_schema` once at start and carries on whatever it returns, so it starts with the database
  unreachable.
- **`ensure_schema(config)`** runs the migrations and retries at most every 30 seconds; it returns `None`
  when the schema is up to date, else the last error message, and never raises. The caller decides what
  an unavailable database means. The result is cached under a lock, so concurrent requests do not
  start parallel attempts.
- **`get_db()` raises `DBUnavailable`** when the schema is not ready or the connection fails; one error
  handler turns it into a `503` with a plain message. Pages that do not need the database (the login
  configuration, the version) keep working.
- **`GET /api/health`** is public and returns `{"status": "ok", "schema_ready": true|false}`. Deploy
  scripts poll it (§ Versioning & Release › Deploy).
- A status screen (Settings › Database) shows reachability, the schema version and the last error,
  using its own short-timeout connection so a dead database cannot tie up the pool.
- Tests: a `db_down` fixture makes the database unreachable, and every layer that touches the database
  has a test that it returns `503`, not `500`.

(Yantra, S013/S025, October 2026.)
```

#### Point 6 — Migration preconditions

**Where:** `## Local DB Migration Pattern`, a new `###` sub-section "Preconditions" directly before
"### Migration squashing". And in `### Migration squashing`:

**Replaces** (first paragraph, first sentence): "When the migration list grows long (20+), squash all
migrations into a single v1 entry containing the full schema as `CREATE TABLE IF NOT EXISTS` statements."
**with:**

```markdown
When the migration list grows long (20+), squash all migrations into a single entry containing the full
schema as `CREATE TABLE IF NOT EXISTS` statements, numbered **above the highest version any deployed
database has recorded** (a squashed `v1` would be skipped on a database that already holds `v1`–`v5`).
```

**Keeps** the last bullet ("Version numbers need not be contiguous (e.g. v1, v2, v3 … v13, v15 is fine
if v14 was dropped during squash).") and **adds** a bullet.

**Replaces** two "After squashing" bullets that the new numbering makes wrong:

- "Dev databases must be recreated (drop + recreate). Document this clearly." **with:**

```markdown
- Every existing database runs the squashed entry, so each statement must be safe on every shape a
  database can have (`CREATE TABLE IF NOT EXISTS`, idempotent data statements); a shape it cannot
  handle gets a precondition.
```

- "Incremental migrations (v2+) continue to use `ALTER TABLE`." **with** the same sentence with "(v2+)"
  changed to "(after the squashed version)".

The added bullet:

```markdown
- Keep the old migration texts, frozen and never edited, in a test fixture (`tests/fixtures/migrations_vN.py`).
  The upgrade tests build a database from them and run the new migrations on it, so the squashed entry is
  tested against the shape production really has.
```

New sub-section before "Migration squashing":

```markdown
### Preconditions

A migration that cannot run on the data that exists (it adds a NOT NULL column, drops a table that still
has rows, or needs a clean-up first) gets a **precondition**, never an edit of an applied migration.

- `_PRECONDITIONS` is a dict `version → check(cursor)`; the check returns `None` (go) or a one-line
  reason, in plain words, that says what to do first.
- Before any pending version is applied, the engine checks the preconditions of **all** pending versions.
  One refusal means nothing is applied, so a refusal never leaves some pending versions applied and others not. The reason shows in
  the status screen (Settings › Database) and in the log; the app keeps serving with `schema_ready`
  false (§ DB Connection Pattern).
- A migration that touches no existing rows (a new table, a nullable column) states that in a comment
  ("No `_PRECONDITIONS` entry: …") so the next reader knows it was considered.
- Write the test from the production schema (the frozen fixture above), not from an empty database.

(Yantra, S025, 21-10-2026.)
```

#### Point 7 — Test databases, next stage

**Where:** `## Testing Pattern`, a new `###` sub-section "Backend tests in parallel (the next stage)" at the
end of the section, after the paragraph "Write `test_rbac.py` first, before any module tests. It validates
the policy file itself and catches mistakes immediately."

**Amends, does not replace:** § Local DB Migration Pattern, "Tests use a separate prefix (e.g.
`appname_test_`) and drop test DBs on exit." and § Testing Pattern, Layer 3, "Truncate the test DB once per
session (session-scoped `pytest_configure`), not per class …". Both stay as the start. Add to the end of
the first one: " When the suite takes more than a few minutes, or agents test in parallel, use the
parallel set-up (§ Testing Pattern › Backend tests in parallel)." Add the same pointer to the end of the
Layer 3 bullet.

```markdown
### Backend tests in parallel (the next stage)

Start with one test database, as above. Move to this when the backend suite takes more than a few
minutes, or when several agents or windows run tests at once and collide on the one database.

- Run **pytest-xdist** with `--dist loadscope` (all tests of a module on one worker, so module-scoped
  fixtures stay valid). `<APP>_TEST_WORKERS` sets the worker count (default 8); `-n 0` runs one process.
- **One database per worker and run name**: `appname_test_<run>_<worker>`, and
  `appname_upgrade_<run>_<worker>` for the upgrade tests. A small `db_names.py` builds the names. The
  tests create them and **keep them between runs** (a run starts with a truncate, not a rebuild). The
  test DB user needs a wildcard grant on `appname_test_%` and `appname_upgrade_%`
  (``GRANT ALL ON `appname\_test\_%`.* …``), made by the test wrapper or the dev DB's init script;
  without it every worker fails at start with "Access denied".
- **A run-name variable** (`<APP>_TEST_RUN`, default `dev`) is in every database name, so two runs at
  the same time never share a database. Each agent, window and the release tests use their own
  name; reserve `dev` and `release` for the person and the release.
- **Named locks carry the database's name** (`GET_LOCK('<lock>:<database>')`), because MariaDB locks are
  server-wide; otherwise two parallel runs wait on each other's lock.
- **Dropping old test databases** is a manual chore (the tooling never drops them: about a dozen per
  run name accumulate). Write the `DROP DATABASE` list from `information_schema.schemata` to a file
  in `scratch/`, read it, then run it; never during a test run (the next run rebuilds what it needs).

(Yantra, 22-10-2026, a tooling commit, not a step; a 6-minute suite became about 40 seconds.)
```

#### Point 8 — Release tests and image builds on a temporary worktree

**Where:** `## Versioning & Release`, a new `###` sub-section "Tests and builds on a clean copy" directly
after "### Release pipeline (`release.py`)" (before "### Version bumper").

**Extends:** § Pre-flight Before Every Release, the setting *Tests a clean copy of HEAD* (`yes` | `no`)
that the repo's `## Pre-flight` names. No sentence is replaced.

```markdown
### Tests and builds on a clean copy

Run the release's tests on a **temporary git worktree of HEAD**, and build the images from a temporary
worktree of the release tag `v<version>`; never from the working folder. Then edits and test runs in
the working folder during a release cannot touch what is tested or built. This is what the pre-flight
setting *Tests a clean copy of HEAD: yes* means.

- The test worktree links the working folder's dependency folder (`frontend/node_modules`) with a
  junction or symlink, so it is not reinstalled. **Never remove that worktree by hand** (`git
  worktree remove`, the IDE): removing a worktree follows the link and empties the working folder's
  dependencies. The test script removes the link first, then the worktree. Vite serves the files behind
  a junction by their real path, so `vite.config.js` adds the real `node_modules` to `server.fs.allow`.
- The build script **refuses** a dirty tree, a missing tag, a HEAD that is not the tagged commit, and a
  version already in the registry. `--dry-run` runs the refusals and the checkout only (no registry
  check, login, build or push).
- Give the release tests their own run name (`<APP>_TEST_RUN=release`) and their own log folder
  (`scratch/release-tests/`).

(Yantra, S025 and 22-10-2026, a tooling commit.)
```

#### Point 9 — Deploy check

**Where:** `## Versioning & Release`, a new `###` sub-section "Deploy" directly after the sub-section of
point 8. **Replaces:** nothing. Text only; Yantra's `tooling/deploy.py` keeps its constants.

```markdown
### Deploy

A deploy script cannot trust the exit code of the tool it calls: `erp_spanner.py` exits 0 even when the
Ansible playbook fails. So:

1. Read the playbook's `PLAY RECAP` yourself, and treat `failed` or `unreachable` greater than 0, or no
   `PLAY RECAP` in the output, as a failed deploy.
2. Then poll the public `/api/health` until `schema_ready` is true, for a bounded time (3 minutes).
   Success means the new version answers and its migrations ran, not that the playbook finished.
3. On any failure after the version was stamped, print the **rollback lines** and stop: stamp the previous
   version and deploy again; if the new schema was already applied, restore the database dump taken
   before the deploy first. The script prints them; the person runs them (CLAUDE-COMMON § Release &
   deployment authorization).
4. Offer a read-only mode (`--check`: shows the host and the stamped line, changes nothing) and a
   stamp-only mode (`--stamp-only`: writes the version stamp and leaves the deploy to a person).

(Yantra, S025, 21-10-2026.)
```

#### Point 10 — Browser Testing Pattern (new section)

**Where:** a new `## Browser Testing Pattern` section directly after `## Testing Pattern` (so before
`## Dev Data Tooling`). **Replaces:** nothing. Testing Pattern's intro stays as it is.

```markdown
## Browser Testing Pattern

Playwright specs test what the user sees, end to end, against a real backend. The pattern below came
from a phone-first app; adjust the devices to yours.

- **Its own stack per run.** The tests start their own backend and Vite on spare ports, with a database
  dropped and rebuilt every run and its own `DATA_DIR`. Identity comes from test headers
  (`X-Test-User`, `X-Test-Role`); a request without them gets no access, so a test cannot pass by
  accident through an open door. A seed script builds the data.
- **Levels.** A quick run (`@smoke` tests: a few journeys of real work, and the one spec that opens
  every route) on the main device; the whole suite on the main device, with only the `@device` tests
  on the other devices; and a release level that adds the iPhone engine. Run the full level in the
  release, not in the normal unit-test run.
- **Test logic once.** Run the logic tests on one device (the main phone). Tag a test `@device` only
  when its purpose is a layout check (fits, in view, no sideways scroll, a geometry assertion) or when
  it runs only on, or asserts differently on, another device. A helper that checks a dialog's fit inside
  a flow test does not tag it.
- **Every dialog a flow test opens is checked to fit** the screen (the main phone's narrow width does
  this in every flow), so another device checks a dialog only through a `@device` test.
- **Parallel lanes, planned by measured time.** Split the run into lanes (default 6). Each lane has
  its own database, backend port, Vite port, data folder, log and Vite dependency cache (six servers
  writing one cache race on its rename). List the tests once, weigh each spec file by its measured
  seconds per test (a timings file updated after each run), and pack the longest first into the least
  loaded lane. Merge the blob reports into one HTML report.
- **One run per machine.** A lock file in the **main working folder's** `scratch/` (not the
  worktree's) makes a second run wait; the timings file lives there too.
- **WebKit on Windows** multiplies the emulated pixel ratio by the display scale (a 125 % display gives
  a narrower window than the device), so run WebKit in the Playwright Docker image
  (`mcr.microsoft.com/playwright:v<version>-noble`, `playwright run-server` on a loopback port) and
  connect to it with `exposeNetwork` for the loopback; the stacks stay on the host. Pin the image to
  the Playwright version; the first pull is large.
- **A spec that fakes requests** (`page.route`, `context.route`) sets `test.use({ serviceWorkers:
  "block" })` at file level: on WebKit a page controlled by a service worker bypasses the route.
- A refusal or message is asserted **in view** (`toBeInViewport()`), not only present.

(Yantra, S024/S046/S047/S054, October 2026.)
```

#### Point 12 — Secrets fallback

**Where:** `## Secrets Pattern`, a new bullet at the end. **Amends:** it extends "A corresponding
`example_secrets_*.py` is checked in to document all required fields with placeholder values."

```markdown
- A missing secrets file falls back to the example **only in dev and test**; in production a missing
  file stops the app at startup. In production the file is rendered by Ansible from a template
  (`secrets_app.py.j2` in the devops repo): when you add or rename a field, change the example and the
  template together.
```

#### Point 13 — npm 10.9 pitfall

**Where:** `## Common Pitfalls`, a new row at the end of the table (pad the cells as the table does).
**Replaces:** nothing.

```markdown
| npm 10.9 crashes (`edgesOut`) when it resolves vitest's optional peers | Use `npx npm@11 install` to change dependencies; `npm ci` (Docker, CI) is fine |
```

#### Point W — Worker without APScheduler

**What the code does** (`backend/worker.py`, `backend/scheduled_tasks.py`; read 26-10-2026):

- `scheduled_tasks.SCHEDULE` is a list of `(task_type, "HH:MM")` pairs, IST, daily. Today it holds one entry.
- `due_tasks(schedule, last_enqueued, now_ist)` is pure. A task is due when today's time has passed and no
  task of that type was enqueued since that time. `last_enqueued` is read from `task_queue` itself
  (`created_at` of the last row of that type). So a worker that was down over the time runs it once when
  it comes back, and a restart never runs it twice.
- The worker loop (`run_once`, every `WORKER_POLL_SECONDS`) does: `ensure_schema`; ping its one dedicated
  connection and take, or confirm, the singleton lock with `GET_LOCK(name, 0)`; requeue stale claims;
  enqueue the due scheduled tasks; claim and run tasks until none is due. Each task takes three
  transactions: the claim (committed so the attempt counts), the handler with `mark_done`, and on an
  exception `mark_failed` after the rollback.
- No cron expressions, no APScheduler, no second thread.

**Where and what it replaces** (all in `SMTW-WebApp-Base.md`):

1. `## Stack`, row *Scheduling*. **Replaces** "`| Scheduling     | APScheduler → `task_queue`  | Cron
   specs in Python; jobs enqueue rather than run inline    |`" with:

```markdown
| Scheduling     | Built-in schedule → `task_queue` | Worker enqueues daily tasks from a table (IST); APScheduler only for cron-like schedules |
```

2. `## Project Layout`, two lines. **Replaces** "`│   ├── scheduled_tasks.py      # Cron registry:
   task_type + cron expression`" with "`│   ├── scheduled_tasks.py      # Schedule table: (task_type, "HH:MM" IST) + pure due_tasks()`" and
   "`│   ├── worker.py               # Separate process: APScheduler + task_queue drainer`" with
   "`│   ├── worker.py               # Separate process: schedule enqueuer + task_queue drainer`".

3. `### Singleton via DB lock`, in "keeps any singleton to one instance: the APScheduler, the queue
   drainer, background monitor threads." **replace** "the APScheduler, the queue drainer," with "the
   worker (schedule and queue drainer),".

4. `## Background Worker / Job Queue Pattern › DB-backed queue (default)`, in the `worker.py` bullet,
   **replace** step 2: "2. Start APScheduler. Scheduled jobs (`scheduled_tasks.py`: task_type + cron
   expression) **enqueue** a task at cron time rather than doing the work inline, so scheduled work gets the
   same retries and history as everything else." with:

```markdown
  2. Enqueue the scheduled tasks that are due. `scheduled_tasks.py` holds a table of `(task_type,
     "HH:MM")` in IST and a pure `due_tasks(schedule, last_enqueued, now)`: a task is due when today's time
     has passed and nothing of that type was enqueued since. "Last enqueued" is read from `task_queue`
     itself, so a worker that was down runs the task once when it returns, and a restart never runs it
     twice. The scheduled work gets the same retries and history as everything else. For schedules
     that are not daily-at-a-time (every 15 minutes, first of the month), use APScheduler with cron
     specs in the same place and the same rule: it **enqueues**, it does not run the work.
```

   Also in that list, step 1 and 3 stay; add one sentence after step 3: "Take the lock again after every
   reconnect: a lock belongs to the connection, and an idle night kills the connection and the lock with
   it." (Yantra's worker checks `IS_USED_LOCK(name) = CONNECTION_ID()` each loop.)

5. `## Fresh Project Bootstrap Checklist`, step 1: **replace** "`uv add flask flask-cors pymysql
   pyjwt[crypto] apscheduler`" with "`uv add flask flask-cors pymysql pyjwt[crypto]`" and add "(add
   `apscheduler` only if you need cron-like schedules)".

6. `## Common Pitfalls`, the row "Two scheduler / monitor instances running | Same singleton lock around
   `start_scheduler` and monitor threads". **Replace** with:

```markdown
| Two workers or monitor threads running | Same singleton lock around the worker loop and monitor threads |
```

7. `## Background Worker / Job Queue Pattern › Background monitoring daemon`, the last sentence "Anything
   less frequent or heavier belongs in the scheduler → `task_queue` instead." stays (the word "scheduler"
   now means the schedule table).

## 9. Tools that go along (lift list)

Tests live only in `smtw-common`'s `tooling/common/tests/`, never synced (S057 U2). Until the lift, all of
the following stays in Yantra, unchanged except the rename.

### 9.1 `run_logged.py` (point 3)

- Script: `tooling/run_logged.py` → `smtw-common` `tooling/common/run_logged.py`; add a `FILES` entry in
  `sync_common.py` (synced). Already generic after the rename: it names no repo; its docstring example line
  shows `== backend: PASSED in 58 s …` and `C:\\...\\scratch\\backend-tests.log`, which is a sample, not a
  Yantra name.
- Test: `tooling/tests/test_run_logged.py` → `tooling/common/tests/test_run_logged.py`. It does `import
  run_logged`, which today works because `tooling/tests/conftest.py` puts `tooling/` on `sys.path`. At the
  new place add at the top (before `import run_logged`):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # tooling/common/, where run_logged.py lives
```

  The file already has `import sys`; keep one import.
- Yantra's wrappers after the lift call `%~dp0common\run_logged.py`: `run-backend-tests.bat` (line 38),
  `run-frontend-tests.bat` (line 9), `run-tooling-tests.bat` (line 10); `run-deps-tests.bat` (line 9)
  is removed with the deps suite (§ 9.2), so three wrappers change. The
  comments change: `run-tests.bat:4` (the list "deploy.py, steps, run_lanes, run_logged" in
  `run-tests.bat` line 4 names `run_logged` as a tooling test) and `run-tooling-tests.bat` (the list over
  lines 3-4, "deploy.py, S025; preflight; run_lanes; run_logged") stop listing it. `tooling/tests/test_run_logged.py`
  is deleted from Yantra with the lift (it moves).

### 9.2 `tooling/deps/` (point 2)

- Scripts: `tooling/deps/audit.py` and `tooling/deps/audit_core.py` → `smtw-common` `tooling/deps/`, synced
  as a **folder without `tests/` and without `pytest.ini`** (a `DIRS` entry that excludes them, or a
  `FILES` entry per script). They name no project (grep for `Yantra|yantra` in the two scripts: no hit).
- Wrapper: `tooling/run-deps-audit.bat` → a `FILES` entry (it is only `cd` and `uv run tooling\deps\audit.py`).
- Tests: `tooling/deps/tests/test_audit_core.py` → `tooling/common/tests/test_audit_core.py`; its
  `tests/fixtures/` → `tooling/common/tests/fixtures/deps/`. Changes in the moved test:
  - add before `import audit_core as core` (the Yantra `pytest.ini` had `pythonpath = .`, which goes
    away with the folder):

```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "deps"))   # tooling/deps/, where audit_core.py lives
```

    (`test_audit_core.py` does not import `sys` today: add `import sys` with the other imports, and
    put these lines after `Path` is imported and before `import audit_core as core`.)
  - Three fixtures name Yantra in their data (`npm-frontend.cdx.json`, `uv-backend.cdx.json`,
    `uv-backend-nodev.cdx.json`; `grep -il yantra`). They are recorded tool output: they stay as
    recorded, and no test asserts on the name.
  - `FIXTURES = Path(__file__).parent / "fixtures"` → `FIXTURES = Path(__file__).parent / "fixtures" / "deps"`.
  - docstring line 4: "`uv export` of Yantra's backend lockfile (full and --no-dev)" → "`uv export` of an
    SMTW backend lockfile (full and --no-dev)".
  - line 142: rename `test_sbom_names_yantra_layout` to `test_sbom_names_standard_layout` (its data is
    `backend/uv.lock`, `frontend/package-lock.json`, `uv.lock`, a layout many repos share; no name in the
    assertion changes).
- `tooling/run-deps-tests.bat` **stays Yantra's** (it uses `YANTRA_TEST_LOG_DIR` and `YANTRA_TEST_RUN`).
  After the lift remove it, and the deps suite, from every place that names it or counts "four suites",
  because the tests then run in `smtw-common`:
  - `tooling/run-tests.bat` lines 3-4 and 7 (comment: "the lines of all four") and line 17 (the call);
  - `tooling/release-tests.bat` line 3 ("the four unit suites"); it has no per-suite check (it reads
    `run-tests.bat`'s exit code), so nothing else changes there;
  - `.claude/CLAUDE.md`: *Dev commands › Tests* ("all four suites: backend, frontend, deps, tooling"),
    *Release* ("the four unit suites"), *Software inventory* (the sentence "only its unit tests are:
    `run-deps-tests.bat`", and "`tooling/deps/` … is meant to move to `smtw-common`"), `## Pre-flight`
    *Failure logs* (suites `backend`, `frontend`, `deps`, `tooling`, and `deps-tests-release.log`), and
    `## Step workflow` *Unit tests* ("backend, frontend, deps, tooling").
  Decide with KLA whether Yantra keeps any test of the audit (BR1-06: no).
- `tooling/deps/pytest.ini` and `tooling/deps/tests/` are deleted from Yantra after the lift.

## 10. After the lift: what `.claude/CLAUDE.md` shrinks to

Do this only after KLA has pasted the texts and synced; until then `CLAUDE.md` is the only copy. Each
lifted bullet becomes one line with Yantra's own values and a pointer. `:N` = line in `CLAUDE.md` today.

| Bullet (line) | After the lift |
|---|---|
| Tests (`:16`, "Tests: `tooling/run-tests.bat` … read that line and the log, do not re-run to see the summary.") | Keep the wrapper names and `-q`. Replace the sentences about the log and summary line with "Test output: CLAUDE-COMMON § Wrapper scripts." |
| Backend tests in parallel (`:17`) | Keep `YANTRA_TEST_WORKERS` default 8, `YANTRA_TEST_RUN` default `dev`, the reserved names, the Yantra DB names `vel_yantra_test_<run>_<worker>` and the ready-made drop command with the container name and root password. Replace the explanation with "pattern: SMTW-WebApp-Base § Testing Pattern › Backend tests in parallel". |
| Secrets (`:18`) | Keep the Ansible template path. Replace "Missing file falls back to the example only in dev/test" by a pointer to § Secrets Pattern. |
| DB may not exist (`:20`) | "The app serves while the DB is down: pattern SMTW-WebApp-Base § DB Connection Pattern; Yantra's code: `local_db.ensure_schema()`, `DBUnavailable`, `/api/health`." |
| Migrations (`:21`) | Keep "v20 is the squash; new migrations start at v21" and the `backend/tests/fixtures/migrations_v13.py` path; pointer to § Local DB Migration Pattern › Preconditions and Migration squashing for the rule. |
| Release (`:22`) | Keep `TEST_CMD`, the worktree path `%TEMP%\yantra-release-tests` and `%TEMP%\yantra-build-v<version>`, the `YANTRA_TEST_RUN=release` name and the logs folder; replace the explanation of why with a pointer to § Versioning & Release › Tests and builds on a clean copy. |
| Deploy (`:24`) | Keep the PuTTY session, the paths, `YANTRA_VER`, `DEPLOY_HEALTH_URL`; replace the PLAY RECAP, health poll and rollback explanation with a pointer to § Versioning & Release › Deploy. |
| npm (`:25`) | Delete (the pitfall is in the base's table). Or keep one line "npm 10.9: see Common Pitfalls". |
| Worker (`:27`) | Keep `named_lock(LOCK_WORKER, database)` and `scheduled_tasks.SCHEDULE`; pointer to § Background Worker / Job Queue Pattern. |
| Software inventory (`:28`) | Keep the audit command `tooling/run-deps-audit.bat`, the folder names `sbom/*.cdx.json` and the report path; pointer to CLAUDE-COMMON § Engineering rules › Software inventory. Drop the sentence "only its unit tests are: `run-deps-tests.bat`" and the "meant to move to `smtw-common`" remark (§ 9.2). |
| Browser tests (`:29`, about 1000 words) | Keep Yantra's values only: ports 5002/5177/5010+n/5180+n, DB names, the three projects, the levels' device lists, the tag rule wording, the lane count, the Docker container name and port 3999, the spec-to-step map. Replace the reasoning (why, WebKit pixel ratio, service workers, lock location) with "pattern: SMTW-WebApp-Base § Browser Testing Pattern". Target: under half. |
| Pre-flight `:40` known fault mark | Keep the three marks (the syntax for each tool is the repo's setting); add "rule: CLAUDE-COMMON § Engineering rules › Known faults are marked strict". |
| Notifications (`:30`), its last sentences on SMTP | Replace "**Policy: SMTP hosts, ports and email addresses never go into the repo** …" with "Mail values: CLAUDE-COMMON § Conventions", keep Yantra's secret names (`SMTP_HOST`, … `SMTP_FROM`) and "email is off unless host, port and from are set". The rest of that bullet stays (point 11, not lifted). |
| `.claude/CLAUDE.md` § Docs to keep current | No change. |

The three wrappers and two comments of § 9.1 and the deps wrapper, suite and the places listed in § 9.2
change at the same time, in one commit with the `CLAUDE.md` shrink.

## 11. Docs updated

None, because `.claude/CLAUDE.md` does not name `YANTRA_TEST_SUMMARY` (grep above), the change has no
migration, no module, no secret, no role, no real-device check, and no maintenance rule or plant fact.
(`docs/steps/INDEX.md` is the orchestrator's; its S058 row still describes the old name in its text and is
history.)

## 12. Manual checks

None (brief § 5).

## Feedback

- hindrance: The Read tool cut `SMTW-WebApp-Base.md` at 25 000 tokens (965 of 1320 lines), so reading
  the base to quote sentences took two calls (2 reads).
- rule: The brief's point 7 asks for a provenance tag "(Yantra, S0NN, …)" but I could not find the step
  that brought in pytest-xdist in the files I read, and the step index has no search by topic; I left
  `S0xx` in the text for KLA to fill (§ 8.2 point 7).
- idea: The lift list for a tool with tests (§ 9.2) always needs the same three edits (a `sys.path` line,
  the fixtures path, names of the repo); a checklist line in the README's lift form would save writing
  them each time.

## Fix round 1

Text edits only, in this report; no code changed, so no test run is due. Docs pass: none, as before.

- **CR1-01 Fixed.** Point 5 now says "Nothing fails at import" (pool lazy, `app.py` calls `ensure_schema` once at start and carries on); the amended Local DB bullet says "`app.py` at start, the first requests and the worker".
- **CR1-02 Fixed.** Point 6 now names and replaces the two "After squashing" bullets (dev databases recreated; "(v2+)") with the idempotent-statements text and "(after the squashed version)".
- **CR1-03 Fixed.** Point 7 tag: "(Yantra, 22-10-2026, a tooling commit, not a step; …)"; point 8 tag: "(Yantra, S025 and 22-10-2026, a tooling commit.)". The `S0xx` note is removed. I did not write the commit hash into the pasted text (a tag in the base should not depend on a Yantra hash); it is 3a20198 if KLA wants it.
- **CR1-04 Fixed.** Point 7's "One database per worker" bullet now states the wildcard grant on `appname_test_%` and `appname_upgrade_%`.
- **CR1-05 Fixed.** § 9.2 now lists every place that names the deps suite or "four suites" (`run-tests.bat`, `release-tests.bat` line 3, five `CLAUDE.md` places); the wrong "summary check" claim is gone. The § 10 *Software inventory* row adds the two sentences to drop. The closing line of § 10 says "three wrappers".
- **CR1-06 Fixed.** "so a refusal never leaves some pending versions applied and others not."
- **CR1-07 Fixed.** Now "**Keeps** the last bullet … and **adds** a bullet."
- **CR1-08 Fixed.** Point 3 names `scratch/<suite>-tests-<run>.log` when a run name is set.
- **CR1-09 Fixed.** Point 9 step 1 adds "no `PLAY RECAP` in the output"; step 4 describes `--check` and `--stamp-only` as they are.
- **CR1-10 Fixed.** Point 10 adds the "every dialog a flow test opens is checked to fit" bullet; the in-view bullet stays and is named in Decisions taken (item 5).
- **CR1-11 Fixed.** Point 8 adds the Vite `server.fs.allow` gotcha of the junction.
- **CR1-12 Fixed.** § 9.1: `run-deps-tests.bat` line 9, the `run-tooling-tests.bat` list over lines 3-4, three wrappers change (the deps one is removed).
- **CR1-13 Fixed.** § 9.2 says the three fixtures that name Yantra stay as recorded tool output; the `sys` note now says `test_audit_core.py` imports no `sys` today and that `import sys` is to be added.
- **CR1-14 Fixed.** Point 10's "Where" states the decision in one sentence ("Testing Pattern's intro stays as it is").

### Feedback (fix round 1)

- none

## Fix round 2 (orchestrator, 26-10-2026)

- CR2-01 (nit): point 6 now quotes the whole base bullet, including "Document this clearly.", so the paste replaces both sentences.
