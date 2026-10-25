```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: brief
Author: Orchestrator (Opus)
Date: 25-10-2026
Track: light (the reviewer's major switched it to full; KLA kept light at gate A, U2)
Status: Gate B (CR r1 and r2: 0 blocker, 0 major; fix rounds 1 and 2 done)
Baseline: 6321983 (S057 committed; the review was against db5b803 + uncommitted S057, the same tree)
```

# S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base

**The need (KLA, 25-10-2026).** "Look at what is in CLAUDE.md. Does it have anything to be lifted to
CLAUDE-COMMON or SMTW-WebApp-Base.md?" The orchestrator listed 13 points; KLA chose **all except 11**
(push and email notifications), and decided the two conflicts with the base: **test databases** —
the base keeps one test database as the start and adds Yantra's way as the next stage (U1);
**worker** — the base adopts Yantra's way (U1).

**Track: light** — text for two synced docs, one environment variable renamed in three files, no
migration, no RBAC, no app code; follows S049's and S057's lift form.

## 1. What will be built

The coder writes, in the impl report under `## Lift to smtw-common`, **ready to paste**, each text
below with the exact place it goes (file, section, before or after which line). KLA makes the edits
in `smtw-common` (as S049 and S057). Each text is written for any SMTW app: no Yantra names, values or
step numbers in the rule itself; a provenance tag "(Yantra, S0NN, DD-MM-YYYY)" may follow, as the
base already does ("VelKilnMaster, Sept 2026"). Each text **says which base sentences it replaces or
amends** (BR1-02), quoting them.

### 1.1 To `CLAUDE-COMMON.md`

| # | Point (Yantra's source in `.claude/CLAUDE.md`) | Where in CLAUDE-COMMON |
|---|---|---|
| 1 | **Mail relay values and personal addresses never go into a repo** (S032's scope, BR1-01): mail relay hosts, ports and credentials, and any person's email address — no code default, example, test value or doc; they come from the deployment's vars (Ansible); tests use reserved names (`example.test`); a person's address comes from the login token, is never typed, and a task payload carries the person's id, never the address (`:30`, *Notifications (S021)*, its last sentences; memory `no-smtp-values-in-repo`). Not widened to every endpoint: public service URLs, realm names and devops paths are in repos today. | § Conventions, beside *Secrets* |
| 2 | **Software inventory**: a CycloneDX SBOM per lockfile in `sbom/`, regenerated and committed with every dependency change, never edited by hand; an audit against OSV with exit codes 0 clean, 1 a critical, high or unknown vulnerability, 2 the check could not complete; direct dependencies with no release in 12 months flagged (`:28`). | § Engineering rules, after *Dependency health* |
| 3 | **Test output**: each suite's whole output in `scratch/<suite>-tests.log`; its last line says PASSED or FAILED, the counts, the time and the log path; read that line and the log, never re-run to see the summary (`:16`, *Tests*). | § Wrapper scripts |
| 4 | **Known faults are marked strict**, naming the step and the fault (`xfail(strict=True)`, Playwright `test.fail`, Vitest `it.fails`), so the run turns red when the fault is fixed; a test that also passes now and then is no known fault (`:40`). The rule holds the principle and points at the base § Pre-flight *Known fault* setting for each repo's mark syntax, so the two do not repeat each other (BR1-10). | § Engineering rules, after *Testing* |

### 1.2 To `SMTW-WebApp-Base.md`

| # | Point (source) | Base section |
|---|---|---|
| 5 | **The app runs while the database is missing or down**: nothing connects at import; `get_db()` raises `DBUnavailable` → 503; the schema check retries every 30 s; `/api/health` reports `schema_ready` (`:20`; `backend/local_db.py:9-12`). Amends § Local DB Migration Pattern's "`init_db(config)` is called at startup" (BR1-02). | § DB Connection Pattern, a new sub-section |
| 6 | **Migration preconditions**: a version that cannot run on existing data gets a check function (`_PRECONDITIONS`, `backend/local_db.py:1102`) returning go or a reason; all pending versions are checked before any is applied, so a refusal changes nothing; the reason shows in the settings screen. After a squash, the old migration texts stay frozen in a test fixture for the upgrade tests; a squashed version is numbered above the highest version production recorded (`backend/local_db.py:61-62`) (`:21`). Replaces § Migration squashing's "squash all migrations into a single v1 entry" (Yantra's code calls its v20 a departure from it) (BR1-02). | § Local DB Migration Pattern, and § Migration squashing |
| 7 | **Test databases, next stage** (U1): the base keeps "a separate prefix, dropped on exit" and "truncate once per session" as the start; it adds: when the suite passes a few minutes, or agents test in parallel, run pytest-xdist (`--dist loadscope`) with one database per worker and run name, kept between runs, a run-name variable so two runs never share one, named locks that carry the database's name, and a manual chore to drop old test databases (`:17`, *Backend tests in parallel*). | § Testing Pattern, and the § Local DB Migration Pattern line on test prefixes |
| 8 | **Release tests and image builds on a temporary git worktree** (of HEAD; of the tag `v<version>`), never the working folder; the build refuses a dirty tree, a missing tag, HEAD not at the tag, a version already in the registry; `--dry-run` runs the refusals only (`:22`). Extends the base § Pre-flight's *Tests a clean copy of HEAD* setting (BR1-02). | § Versioning & Release |
| 9 | **Deploy check**: `erp_spanner.py` exits 0 even when the playbook fails, so the deploy script reads the PLAY RECAP itself; then it polls the public `/api/health` until `schema_ready`, for a bounded time; on any failure after the version stamp it prints the rollback lines (`:24`). Text only: `tooling/deploy.py` keeps Yantra's constants and is not lifted (§ Out of scope). | § Versioning & Release, a new *Deploy* sub-section |
| 10 | **Browser testing pattern** (new section): its own stack per run (database rebuilt every run, identity from test headers, a request without them gets no access); levels (a quick smoke run, the whole suite on the logic device, the release level); logic tested once on one device, layout tests tagged `@device` by the rule of `:29`; parallel lanes, planned by measured time, each with its own database, ports and Vite cache; one run per machine (a lock in the main working folder's `scratch/`); WebKit on Windows multiplies the emulated pixel ratio by the display scale, so it runs in the Playwright Docker image; a spec that fakes requests with `page.route` blocks service workers (WebKit) (`:29`). About half a page (`:29` is near a thousand words of Yantra detail), in generic terms: "the screens spec", "the logic device", "the repo's lock file", "test identity headers" (BR1-08). | a new § Browser Testing Pattern, after § Testing Pattern |
| 12 | **Secrets fallback**: a missing secrets file falls back to the example only in dev and test; in production Ansible renders it from a template, and the example's field names follow that template (`:18`). | § Secrets Pattern |
| 13 | **npm 10.9 crashes (`edgesOut`) resolving optional peers**: use `npx npm@11 install` to change dependencies; `npm ci` is fine (`:25`). | § Common Pitfalls, one row |
| W | **Worker without APScheduler** (U1, the base adopts): the worker enqueues its daily tasks itself from a schedule table in IST (`scheduled_tasks.SCHEDULE`), one worker under the singleton lock (`:27`). The base's § Background Worker step 2 and the Stack table's *Scheduling* row offer it as the default for a few daily jobs, APScheduler for cron-like schedules. The coder reads `backend/worker.py` and `backend/scheduled_tasks.py` and describes what they do, not more. Also changes the base's other APScheduler sentences: § Singleton via DB lock ("the APScheduler"), the Bootstrap checklist's step 1 (`apscheduler`), and the Common Pitfalls row "Two scheduler / monitor instances" (BR1-02). Reading of "base adopts" (BR1-09): Yantra's way becomes the base default; APScheduler stays named as the option for cron-like schedules — KLA confirms at gate A. | § Stack table, § Background Worker / Job Queue Pattern › DB-backed queue |

### 1.3 Tools that go along

Tests follow S057 U2: they live only in `smtw-common`'s `tooling/common/tests/`, never synced. Unlike
S057's step tests, these stay in Yantra until the lift (§ 6 Q3): the deps tests are one of
`run-tests.bat`'s four suites and run in the release.

- **`tooling/run_logged.py`** (point 3) is generic but for its variable `YANTRA_TEST_SUMMARY`.
  Renamed to `TEST_SUMMARY_FILE` in `tooling/run_logged.py:10, 63`, `tooling/run-tests.bat:10-12, 22`
  and `tooling/tests/test_run_logged.py:41` (the reviewer's grep of `tooling`, `.claude`, `docs`,
  `backend`, `frontend`, `.run` and `.idea` found no other use). Lift list: the script to
  `tooling/common/run_logged.py` (synced, a `FILES` entry); its test to `tooling/common/tests/`. The
  test imports `run_logged` through `tooling/tests/conftest.py` today (it puts `tooling/` on
  `sys.path`); the lift list gives the one `sys.path` line it needs at its new place, as S049's
  tests have (BR1-04). After the lift, Yantra's four wrappers that call `%~dp0run_logged.py`
  (`run-backend-tests.bat`, `run-frontend-tests.bat`, `run-deps-tests.bat`,
  `run-tooling-tests.bat`) call `%~dp0common\run_logged.py`, and the comments of `run-tests.bat:4`
  and `run-tooling-tests.bat:3` stop listing it among the tooling tests (BR1-04).
- **`tooling/deps/`** (point 2): `audit.py` and `audit_core.py` name no project; lift list: to
  `tooling/deps/` in `smtw-common`, synced as a folder **without** `tests/` and `pytest.ini`
  (BR1-03). Its tests (`tooling/deps/tests/test_audit_core.py` and `fixtures/`) go to
  `tooling/common/tests/`; the lift list names the Yantra lines to make generic there (docstring
  line 4, `test_sbom_names_yantra_layout` at line 142) and their import path. The audit wrapper
  `tooling/run-deps-audit.bat` names nothing of Yantra (it is `cd` and `uv run tooling\deps\audit.py`)
  and is lifted too (a `FILES` entry); `run-deps-tests.bat` stays Yantra's (it uses `YANTRA_*`
  variables) and after the lift is removed with the deps suite in `run-tests.bat` (BR1-06).

### 1.4 After the lift, in Yantra

The impl report lists what `.claude/CLAUDE.md` can then shrink to: each lifted bullet becomes one line
naming Yantra's own values and "pattern: SMTW-WebApp-Base § …" (or CLAUDE-COMMON § …). The coder
does **not** shrink `CLAUDE.md` now: until KLA pastes the texts, `CLAUDE.md` is the only copy.

### Out of scope

- Point 11 (push and email notifications; KLA, U1).
- Writing to `smtw-common` (KLA's).
- Lifting `tooling/deploy.py` (Yantra's PuTTY session, paths and target are constants); point 9 is
  the rule only.
- Changing Yantra's behaviour: only the variable rename of § 1.3.

## 2. Standards and practice

ISO 9001 § 7.5.3 (control of documented information): a lesson learnt in one repo is recorded once, in
the controlled common document, and each repo points at it. ISO 27001 for two points (BR1-07, clause
numbers to verify by the coder against the 2022 Annex A): point 2, technical vulnerability management
(know what you run and check it against published vulnerabilities); point 1, keeping protected
information out of places it does not belong. No maintenance standard applies.

## 3. Where

| File | Change |
|---|---|
| `tooling/run_logged.py`, `tooling/run-tests.bat`, `tooling/tests/test_run_logged.py` | `YANTRA_TEST_SUMMARY` → `TEST_SUMMARY_FILE` (§ 1.3) |
| `docs/steps/S058-lift-lessons-to-common/3-impl-report.md` | the texts of § 1.1–1.2, the lift list of § 1.3, the after-lift list of § 1.4 |

Docs (housekeeping, by the coder): none — `.claude/CLAUDE.md` does not name the variable (grep, 25-10-2026).

## 4. Design decisions

1. **Ready-to-paste texts in the impl report, KLA edits `smtw-common`** (as S049, S057). Rejected:
   staged copies of the whole common files in the step folder: they go stale the moment `smtw-common`
   changes.
2. **The rename to `TEST_SUMMARY_FILE`** so the lifted script names no repo. Rejected: lifting it
   with `YANTRA_` in it.
3. **`CLAUDE.md` is not shrunk now** (§ 1.4): it stays the only copy until the paste.

## 5. Tests and acceptance

- `tooling/run-tests.bat` green, and its closing summary lines still print (the rename works end to
  end); `tooling/run-tooling-tests.bat` green.
- `grep -rn YANTRA_TEST_SUMMARY tooling` finds nothing.
- The code reviewer checks each text against its source in `CLAUDE.md` and the code it describes
  (nothing lost, nothing invented, no Yantra name in a rule), and each "where" against the current
  `CLAUDE-COMMON.md` and `SMTW-WebApp-Base.md` (the section exists; the text does not repeat or
  contradict what is there, or says what it replaces).
- Manual checks: none.

## 6. Open questions and assumptions

1. **The variable's new name**: `TEST_SUMMARY_FILE` (KLA, U2).
2. **Assumption**: the S057 lift happens first or together; S058's lift list adds to it and does
   not repeat it (the reviewer found no overlap).
3. **The deps and `run_logged` tests stay in Yantra until the lift** (§ 1.3), unlike S057's step
   tests (KLA, S057 U3). Recommended, because the deps suite is one of the four unit suites and runs
   in the release; removing it now changes `run-tests.bat` and the release tests. Alternative: stage
   them now as S057 did. Answered (U2): they stay.
4. **The worker text** (BR1-09): Yantra's way becomes the base default, APScheduler stays as the
   option for cron-like schedules. Answered (U2): as written.

## 7. Amendments

None.

## Review log

### U1 — 25-10-2026 (before drafting)

KLA: "All except 11 can make it." Test databases: "ok" to the base keeping one test database as the
start and adding Yantra's way as the next stage. Worker: "base adopts".

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major: point 1 widened beyond S032's decided scope | Accepted (option 1): S032's scope kept, its principle stated (§ 1.1 point 1). The major switches the track to full; proposed to KLA to keep light, since the fix returns to a rule KLA already decided |
| BR1-02 minor: the base sentences replaced are not all named | Accepted: each point names what it replaces or amends (points 5, 6, 8, W; § 1 intro) |
| BR1-03 minor: deps tests synced and naming Yantra | Accepted: tests to `tooling/common/tests/`, not synced; the Yantra lines named for the lift (§ 1.3) |
| BR1-04 minor: `run_logged`'s test import, the wrappers | Accepted: the import line in the lift list; the four wrappers and two comments in the after-lift list (§ 1.3) |
| BR1-05…BR1-10 nits | Accepted, all: `:16` / `:17`; `run-deps-audit.bat` lifted (it names nothing of Yantra); ISO 27001 for points 1–2; point 10's length and generic terms; the APScheduler reading to KLA (§ 6 Q4); point 4 points at the base's *Known fault* setting |

### U2 — 26-10-2026, gate A

KLA: "adopt S057, start S058" — the brief approved with the recommended answers: the track stays
light; Q1 `TEST_SUMMARY_FILE`; Q3 the deps and `run_logged` tests stay in Yantra until the lift; Q4
the worker text as written (Yantra's way the base default, APScheduler the option for cron-like
schedules). S057 committed as 6321983 the same day, so Q2's assumption holds.
