```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: brief
Author: Orchestrator (Opus)
Date: 25-10-2026
Track: light
Status: In review
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
base already does ("VelKilnMaster, Sept 2026").

### 1.1 To `CLAUDE-COMMON.md`

| # | Point (Yantra's source in `.claude/CLAUDE.md`) | Where in CLAUDE-COMMON |
|---|---|---|
| 1 | **No SMTP hosts, ports or email addresses in a repo**: only from the Ansible vars; tests use reserved values (`example.test`); a person's address comes from the login token, is never typed, and a task payload carries the person's id, never the address (`:30`, *Notifications (S021)*, its last sentences; memory `no-smtp-values-in-repo`). Written as the wider rule: infrastructure endpoints and personal addresses never go into the repo. | § Conventions, beside *Secrets* |
| 2 | **Software inventory**: a CycloneDX SBOM per lockfile in `sbom/`, regenerated and committed with every dependency change, never edited by hand; an audit against OSV with exit codes 0 clean, 1 a critical, high or unknown vulnerability, 2 the check could not complete; direct dependencies with no release in 12 months flagged (`:28`). | § Engineering rules, after *Dependency health* |
| 3 | **Test output**: each suite's whole output in `scratch/<suite>-tests.log`; its last line says PASSED or FAILED, the counts, the time and the log path; read that line and the log, never re-run to see the summary (`:13`, *Tests*). | § Wrapper scripts |
| 4 | **Known faults are marked strict**, naming the step and the fault (`xfail(strict=True)`, Playwright `test.fail`, Vitest `it.fails`), so the run turns red when the fault is fixed; a test that also passes now and then is no known fault (`:40`). | § Engineering rules, after *Testing* |

### 1.2 To `SMTW-WebApp-Base.md`

| # | Point (source) | Base section |
|---|---|---|
| 5 | **The app runs while the database is missing or down**: nothing connects at import; `get_db()` raises `DBUnavailable` → 503; the schema check retries every 30 s; `/api/health` reports `schema_ready` (`:20`; `backend/local_db.py:9-12`). | § DB Connection Pattern, a new sub-section |
| 6 | **Migration preconditions**: a version that cannot run on existing data gets a check function (`_PRECONDITIONS`, `backend/local_db.py:1102`) returning go or a reason; all pending versions are checked before any is applied, so a refusal changes nothing; the reason shows in the settings screen. After a squash, the old migration texts stay frozen in a test fixture for the upgrade tests; a squashed version is numbered above the highest version production recorded (`backend/local_db.py:61-62`) (`:21`). | § Local DB Migration Pattern, and § Migration squashing |
| 7 | **Test databases, next stage** (U1): the base keeps "a separate prefix, dropped on exit" and "truncate once per session" as the start; it adds: when the suite passes a few minutes, or agents test in parallel, run pytest-xdist (`--dist loadscope`) with one database per worker and run name, kept between runs, a run-name variable so two runs never share one, named locks that carry the database's name, and a manual chore to drop old test databases (`:13`, *Backend tests in parallel*). | § Testing Pattern, and the § Local DB Migration Pattern line on test prefixes |
| 8 | **Release tests and image builds on a temporary git worktree** (of HEAD; of the tag `v<version>`), never the working folder; the build refuses a dirty tree, a missing tag, HEAD not at the tag, a version already in the registry; `--dry-run` runs the refusals only (`:22`). | § Versioning & Release |
| 9 | **Deploy check**: `erp_spanner.py` exits 0 even when the playbook fails, so the deploy script reads the PLAY RECAP itself; then it polls the public `/api/health` until `schema_ready`, for a bounded time; on any failure after the version stamp it prints the rollback lines (`:24`). Text only: `tooling/deploy.py` keeps Yantra's constants and is not lifted (§ Out of scope). | § Versioning & Release, a new *Deploy* sub-section |
| 10 | **Browser testing pattern** (new section): its own stack per run (database rebuilt every run, identity from test headers, a request without them gets no access); levels (a quick smoke run, the whole suite on the logic device, the release level); logic tested once on one device, layout tests tagged `@device` by the rule of `:29`; parallel lanes, planned by measured time, each with its own database, ports and Vite cache; one run per machine (a lock in the main working folder's `scratch/`); WebKit on Windows multiplies the emulated pixel ratio by the display scale, so it runs in the Playwright Docker image; a spec that fakes requests with `page.route` blocks service workers (WebKit) (`:29`). | a new § Browser Testing Pattern, after § Testing Pattern |
| 12 | **Secrets fallback**: a missing secrets file falls back to the example only in dev and test; in production Ansible renders it from a template, and the example's field names follow that template (`:18`). | § Secrets Pattern |
| 13 | **npm 10.9 crashes (`edgesOut`) resolving optional peers**: use `npx npm@11 install` to change dependencies; `npm ci` is fine (`:25`). | § Common Pitfalls, one row |
| W | **Worker without APScheduler** (U1, the base adopts): the worker enqueues its daily tasks itself from a schedule table in IST (`scheduled_tasks.SCHEDULE`), one worker under the singleton lock (`:27`). The base's § Background Worker step 2 and the Stack table's *Scheduling* row offer it as the default for a few daily jobs, APScheduler for cron-like schedules. The coder reads `backend/worker.py` and `backend/scheduled_tasks.py` and describes what they do, not more. | § Stack table, § Background Worker / Job Queue Pattern › DB-backed queue |

### 1.3 Tools that go along

- **`tooling/run_logged.py`** (point 3) is generic but for its variable `YANTRA_TEST_SUMMARY`.
  Renamed to `TEST_SUMMARY_FILE` in `tooling/run_logged.py:10, 63`, `tooling/run-tests.bat:10-12, 22`
  and `tooling/tests/test_run_logged.py:41`. Then it goes on the lift list (to
  `tooling/common/run_logged.py` in `smtw-common`, synced; its test to `tooling/common/tests/`).
  Yantra's wrappers keep calling `tooling/run_logged.py` until the lift; the after-lift list says to
  point them at `tooling/common/run_logged.py`.
- **`tooling/deps/`** (point 2, `audit.py`, `audit_core.py`, `tests/`, `pytest.ini`): names no
  project (`.claude/CLAUDE.md:28`); on the lift list as is, synced as a folder. The wrappers
  `tooling/run-deps-audit.bat` and `run-deps-tests.bat` stay Yantra's (they use `YANTRA_*`
  variables); the text of point 2 tells another repo the one command (`uv run tooling/deps/audit.py`).

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
the controlled common document, and each repo points at it. No maintenance standard applies.

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

1. **The variable's new name**: `TEST_SUMMARY_FILE` proposed.
2. **Assumption**: the S057 lift happens first or together; S058's lift list adds to it and does
   not repeat it.

## 7. Amendments

None.

## Review log

### U1 — 25-10-2026 (before drafting)

KLA: "All except 11 can make it." Test databases: "ok" to the base keeping one test database as the
start and adding Yantra's way as the next stage. Worker: "base adopts".
