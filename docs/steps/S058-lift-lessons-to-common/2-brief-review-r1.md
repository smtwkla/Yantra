```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: db5b803 + uncommitted S057

# S058 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01, the widened "no endpoints in the repo" rule).** Three
`minor` findings, six nits. Light track: this is the only round. Every light criterion holds (three
tooling files renamed, no migration, no auth, no locking, no new pattern); the `major` switches the
track to full by the README's rule, and KLA may keep light at approval (23-10-2026).

Facts file read: `scratch/brief-facts-S058.md`. Its file and route facts held; its code-name section
was mostly noise (see Feedback), so I checked the code names in the files.

## Findings

### BR1-01 — major — Point 1 widens S032's policy into a rule the repo already breaks

**Problem.** § 1.1 point 1 says the SMTP policy is "written as the wider rule: infrastructure
endpoints and personal addresses never go into the repo". S032's decision (CLAUDE.md:30, memory
`no-smtp-values-in-repo`) is narrower: SMTP hosts, ports and email addresses. No U-decision in the
brief widens it.

**Why it matters.** The text goes into CLAUDE-COMMON's Invariants, which every repo must follow. As
worded, Yantra itself breaks it today: the Keycloak realm `Office.smtw.in` (CLAUDE.md:9), the PuTTY
session `ansible-ws` and `/home/kla/smtw/erp_server` (CLAUDE.md:24), the OSV, PyPI and npm URLs in
`tooling/deps/audit.py:32-34`, the Playwright image in CLAUDE.md:29. The base too (`smtwkla/smtw-common`,
`mcr.microsoft.com`). The coder would have to draw the boundary alone.

**Options.**
1. Keep S032's scope and state the principle behind it: mail relay hosts, ports and credentials, and
   any person's address, never go into a repo (no code default, example, test value or doc); they
   come from the deployment's vars; tests use reserved names (`example.test`); a person's address
   comes from the login token and a task payload carries the person's id. **Recommended**: it is
   what KLA decided, and it is true of every repo.
2. Widen the rule, with the boundary written out (what counts as an endpoint; public service URLs,
   realm names and devops paths excepted), and put the question to KLA at approval.

### BR1-02 — minor — The base lines a point replaces are not all named

**Problem.** § 5 asks the code reviewer to check that each text "says what it replaces", but the
brief names the replaced lines only for W (two places) and 7 (two places). Missing:
- **W**: § Singleton via DB lock ("keeps any singleton to one instance: the APScheduler, …");
  § Fresh Project Bootstrap Checklist step 1 (`uv add … apscheduler`); § Common Pitfalls row "Two
  scheduler / monitor instances running … `start_scheduler`".
- **6**: § Migration squashing says "squash all migrations into a single v1 entry"; Yantra's
  `local_db.py:61-62` calls its numbering "a departure from SMTW-WebApp-Base § Migration squashing".
  The point must say it replaces that sentence (and touches "Version numbers need not be
  contiguous").
- **5**: § Local DB Migration Pattern says "`init_db(config)` is called at startup and applies any
  pending migrations automatically"; Yantra connects nothing at import and retries on requests.
  Bootstrap step 7 names `local_db.py (pool + migrations + singleton lock)`.
- **8**: the already-lifted § Pre-flight Before Every Release has the setting *Tests a clean copy of
  HEAD*; point 8 extends it (how: a worktree) and must not repeat it.

**Why it matters.** A pasted text that leaves the old sentence standing gives the base two answers.
The coder has only the brief's table to find them.

**Options.** (1) Add to each row of § 1.2 the base sentence(s) the text replaces or amends, as S049's
lift did ("replace … with"). **Recommended.** (2) Leave it to the coder and the code reviewer: slower,
and a miss reaches KLA's paste.

### BR1-03 — minor — `tooling/deps/tests/` names Yantra and would be synced into every repo

**Problem.** § 1.3 lifts `tooling/deps/` "as is, synced as a folder", `tests/` included, because it
"names no project". Two facts against it:
- `tooling/deps/tests/test_audit_core.py` names Yantra: the docstring (line 4, "Yantra's backend
  lockfile") and `test_sbom_names_yantra_layout` (line 142). `audit.py` and `audit_core.py` do not.
- S057 decided (U2) that the common tools' tests live only in `smtw-common`'s `tooling/common/tests/`
  and are not synced. The brief follows that for `test_run_logged.py` (§ 1.3, first bullet) but not
  for the deps tests, so one step would lift tests two ways.

**Why it matters.** A synced `tests/` folder lands in every sibling repo and runs in none of their
suites; a Yantra name in a common file is what this step exists to remove.

**Options.** (1) Sync `tooling/deps/audit.py`, `audit_core.py` and `pytest.ini` as the folder; move
`tests/` (with its fixtures) to `smtw-common`'s `tooling/common/tests/` in the lift list, after the
coder renames the test and its docstring line; say how the test imports `audit_core` from there.
**Recommended.** (2) Keep `tests/` synced and only rename: contradicts S057's U2.

### BR1-04 — minor — The lifted `run_logged.py` and its test: the new place is not described

**Problem.** § 1.3 sends `test_run_logged.py` to `tooling/common/tests/`. Today it does
`import run_logged` and resolves it through `tooling/tests/conftest.py`, which puts `tooling/` on
`sys.path`. At the new place `run_logged.py` is in `tooling/common/`; the brief does not say what the
test needs there (its own `sys.path` line, as S049's tests do, or `smtw-common`'s conftest). The
after-lift list says "Yantra's wrappers" without naming them: `run-backend-tests.bat`,
`run-frontend-tests.bat`, `run-deps-tests.bat` and `run-tooling-tests.bat` all call
`%~dp0run_logged.py`; `run-tests.bat:4` and `run-tooling-tests.bat:3` list `run_logged` among the
tooling tests, which leave Yantra's suite with the lift (as S057's did).

**Why it matters.** A test that imports by a path that no longer exists fails at the first run in
`smtw-common`; a wrapper not on the list keeps calling a file the after-lift step deletes.

**Options.** (1) Add to § 1.3: the test's import at its new place, the four wrappers, and the two
comments; the coder fixes the test for its new place as S057 § 1.5 did (a staging copy, or a note in
the lift list). **Recommended.** (2) Leave the import to KLA at paste time.

## Nits

- **BR1-05** (nit) § 1.1 rows 3 and 7: the source is `:16` (*Tests*) and `:17` (*Backend tests in
  parallel*); `:13` is the *Dev commands* parent bullet.
- **BR1-06** (nit) § 1.3 second bullet: `run-deps-audit.bat` uses no `YANTRA_*` variable (it is `cd`
  and `uv run tooling\deps\audit.py`); only `run-deps-tests.bat` does. Correct the reason, or lift the
  audit wrapper too.
- **BR1-07** (nit) § 2: the Standards entry lists ISO 27001. Name it for points 1 and 2 in one plain
  line each: Annex A 8.8 (technical vulnerability management: know what you run, check it against
  published vulnerabilities — the SBOM and OSV check) and A 5.12/8.12 (classify and keep protected
  information out of places it does not belong — the secrets rule).
- **BR1-08** (nit) § 1.2 point 10: set a length target (about half a page; `:29` is near a thousand
  words of Yantra detail) and name the generic terms for Yantra's names: `screens.spec.js` → "the
  screens spec", `phone-chromium` → "the logic device", `scratch/e2e-run.lock` → "the repo's lock
  file", `X-Test-Role` / `X-Test-User` → "test identity headers".
- **BR1-09** (nit) § 1.2 W: KLA said "base adopts"; the brief keeps APScheduler "for cron-like
  schedules". Say that reading in the approval summary so KLA confirms it.
- **BR1-10** (nit) § 1.1 point 4: say the CLAUDE-COMMON rule holds the principle (strict marks, the
  step and the fault named, a flaky test is no known fault) and points at the base § Pre-flight
  *Known fault* setting for each repo's mark syntax, so the two do not repeat each other.

## Checked and found consistent

- The rename's file list is complete: `YANTRA_TEST_SUMMARY` is in `tooling/run_logged.py:10, 63`,
  `tooling/run-tests.bat:10-12, 22`, `tooling/tests/test_run_logged.py:41` and nowhere else in
  `tooling/`, `.claude/`, `backend/`, `frontend/`, `.run/`, `.idea/`; `release-tests.bat` sets only
  `YANTRA_TEST_RUN` and `YANTRA_TEST_LOG_DIR`; `## Pre-flight` names the summary file, not the
  variable; the two hits in `docs/steps/` (S049's review, this brief) are history, not to edit.
- Each source line exists and says what the brief claims: `:18` (secrets fallback;
  `backend/config.py:27-38` falls back only when `IS_DEV or IS_TESTING`), `:20` (DB may not exist;
  `local_db.py:9-12`; `app.py:100-106` returns `schema_ready`), `:21` (`_PRECONDITIONS` at
  `local_db.py:1102`, None or a reason; `MigrationBlocked` keeps the message for Settings › Database;
  `:61-62` on the numbering), `:22` (`release-tests.bat` worktree of HEAD; `build.bat` refuses a
  dirty tree, no tag, HEAD not at the tag, a version in the registry; `--dry-run`), `:24`
  (`deploy.py:62, 174-177` PLAY RECAP; `HEALTH_TIMEOUT_SECONDS = 180`; `rollback_lines`), `:25`,
  `:27` (`scheduled_tasks.SCHEDULE`, daily, due from `task_queue`'s last enqueue; `worker.py`
  `named_lock(LOCK_WORKER, …)`), `:28` (`audit.py` docstring: exit 0/1/2, "Nothing here names a
  project"), `:29`, `:30`, `:40`.
- Each "where" heading exists in the current `CLAUDE-COMMON.md` (§ Conventions › Secrets,
  § Engineering rules › Dependency health and Testing, § Wrapper scripts) and
  `SMTW-WebApp-Base.md` (§ Stack, § DB Connection Pattern, § Local DB Migration Pattern,
  § Migration squashing, § Background Worker / Job Queue Pattern › DB-backed queue, § Secrets Pattern,
  § Versioning & Release, § Testing Pattern, § Common Pitfalls).
- The base's test-prefix line ("Tests use a separate prefix … drop test DBs on exit") and "Truncate
  the test DB once per session" are the ones point 7 keeps as the start (U1).
- `erp_spanner.py` is the devops repo's tool, so "no file of that name" is right; the rule of point 9
  (read the PLAY RECAP, poll `/api/health` for a bounded time, print the rollback) carries without
  Yantra's constants.
- No overlap with S057's lift list (skill, agents, `tooling/steps/`, `tooling/roadmap/`, seven
  wrappers, two READMEs, a CLAUDE-COMMON section on numbered steps); assumption 2 covers the order.
- Point 11 is left out as KLA chose; `CLAUDE.md` is not shrunk now (decision 3) — right, it is the
  only copy until the paste.
- Manual checks: none, and none needed (no screen).

## Feedback

- hindrance: the facts file's code-name search treats `.` as any character: `test.fail` "defined at"
  six `pytest.fail` lines, `example.test` "used in 83 test files", `it.fails` and `page.route`
  "defined at" Vue files — 5 of 12 names were noise, each re-checked by grep
  (`scratch/brief-facts-S058.md` § Code names).
- waste: the facts file lists `backend/local_db.py` three times, once per citation (§ Files).
- idea: for a step whose output is text for other docs, let `brief_facts.py` also check each
  "§ Heading" the brief cites in a named `.md` file (exists or not); I checked 13 headings by
  `grep -n "^#"`.
