```
Step: S058 — Yantra's general lessons, written for CLAUDE-COMMON and the base
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S058 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 5 minor findings and 9 nits. The rename is complete and works end to end. The texts match the code they describe, with the exceptions below. Two provenance tags are still placeholders or wrong.

Reviewed against: 6321983 + the uncommitted S058 changes (`git diff -w --ignore-cr-at-eol`, and the untracked S058 files). The S058 brief, its review r1, the S057 brief line and the `INDEX.md` row are the orchestrator's bookkeeping and were not reviewed.

## Tests run

- `YANTRA_TEST_RUN=s058cr1 tooling/run-tests.bat`: **all four suites green**. backend 3075 passed (98 s), frontend 179 passed (15 s), deps 42 passed (1 s), tooling 173 passed (1 s), `== ALL SUITES: PASSED`, exit 0. The closing "Test summary" block printed the four lines from `scratch/test-summary-s058cr1.txt`, so `TEST_SUMMARY_FILE` is set, appended to and read back.
- Browser tests: none due (no screen or API changed). None run.

## Findings

### CR1-01 (minor) Point 5 says nothing connects at import, but `app.py` tries the migrations at import

`docs/steps/S058-lift-lessons-to-common/3-impl-report.md:197-199`, `:214-215`; the code: `backend/app.py:32-33`.

**Problem.** The new base sub-section starts with "**Nothing connects at import.** Create the pool lazily". The amended Local DB bullet says "the first requests and the worker call it" (`ensure_schema`). But `app.py:33` calls `ensure_schema(DB_CONFIG)` at import, and its comment says "migrations are tried now and retried later". That opens a connection at import. What is true is narrower: `local_db.py` connects at nothing at import (its docstring), and the import never *fails* when the database is down, because `ensure_schema` never raises. The brief's acceptance is "nothing invented".

**Failure scenario.** A developer follows the base text and removes the start-up attempt from a new app. The first migration then waits for the first request. Or a reader of Yantra's `app.py` sees it break the rule the base says Yantra came from.

**Fix.** Reword the bullet: "**Nothing fails at import.** Create the pool lazily (it opens no connection). `app.py` calls `ensure_schema` once at start and carries on whatever it returns." Change the Local DB bullet to "`app.py` at start, the first requests and the worker call it".

### CR1-02 (minor) Point 6 leaves two "After squashing" bullets that the new numbering makes wrong

`3-impl-report.md:238-255`; the base: `.claude/SMTW-WebApp-Base.md:485-490`.

**Problem.** Point 6 numbers a squash above the highest recorded version and keeps every "After squashing" bullet except one. Two of them then contradict the new text, and the report does not name them (brief BR1-02: each text names what it replaces):
- "Dev databases must be recreated (drop + recreate)." Yantra's v20 was written to be safe on a v13 database (`backend/local_db.py:54-62`: "a v13 database: every CREATE skips and every data statement is a no-op"). A squash numbered above means existing databases run it, so it must be idempotent on every shape they have, not recreated.
- "Incremental migrations (v2+) continue to use `ALTER TABLE`." With the squash at vN, the next ones are vN+1.

**Failure scenario.** A repo follows the base: it squashes into v20 but keeps "Dev databases must be recreated" and writes data statements that are not idempotent. A v13 database then runs v20 and fails on a duplicate seed row.

**Fix.** Add to point 6: replace the first bullet with "Every existing database runs the squashed entry, so each statement must be safe on every shape a database can have (`CREATE TABLE IF NOT EXISTS`, idempotent data statements); a shape it cannot handle gets a precondition." Replace "(v2+)" with "(after the squashed version)".

### CR1-03 (minor) Two provenance tags are not ready to paste: point 7 is `S0xx`, point 8 names the wrong steps

`3-impl-report.md:311-315`, `:343`.

**Problem.** The texts are meant to be pasted as they are. Point 7 ends "(Yantra, S0xx, October 2026; …)". The parallel test databases came from no step: commit 3a20198 of 22-10-2026 ("parallel backend tests (a database per run and worker, 370 s to 37 s) … release tests in a locked worktree, images built from the tag"). Point 8 ends "(Yantra, S049/S055, October 2026.)". But the same commit 3a20198 built the release-test worktree and the build from the tag, and S025 (b6b8dfb) added the build's refusals. S049 and S055 changed `release-tests.bat` later (pre-flight, the Full level).

**Failure scenario.** KLA pastes the text as written. The base then carries a placeholder, or credits the worktree to the pre-flight step, and a later reader looks in the wrong step folder.

**Fix.** Point 7: "(Yantra, 22-10-2026, tooling commit 3a20198, not a step; a 6-minute suite became about 40 seconds.)". Point 8: "(Yantra, S025 and 22-10-2026, tooling commit 3a20198.)". Remove the note at `:314-315`.

### CR1-04 (minor) Point 7 leaves out the database grant the parallel set-up needs

`3-impl-report.md:297-309`; the code: `backend/tests/db_names.py:11-14`, `backend/tests/conftest.py:181-182`.

**Problem.** The tests create their databases themselves (`CREATE DATABASE IF NOT EXISTS`). That works only because the test user has a wildcard grant on `vel_yantra_test_%` and `vel_yantra_upgrade_%`, made by `tooling/run-backend-tests.bat` and `tooling/dev/init-test-db.sql` (`db_names.py` docstring). The base's start uses one database that a person or a script creates. The text does not say the user now needs the right to create databases by pattern.

**Failure scenario.** A repo adopts the next stage as written. Every worker fails at start with "Access denied … to database 'appname_test_dev_gw0'", and the developer has to find the cause.

**Fix.** Add to the "One database per worker" bullet: "The test DB user needs a wildcard grant on `appname_test_%` and `appname_upgrade_%` (`GRANT ALL ON \`appname\_test\_%\`.* …`), made by the test wrapper or the dev DB's init script."

### CR1-05 (minor) The after-lift list for the deps suite names a check that does not exist and misses the places that name four suites

`3-impl-report.md:558-562`, `:580`, `:586-587`.

**Problem.** § 9.2 says: after the lift, remove the deps suite "from `tooling/release-tests.bat`'s summary check". `release-tests.bat` has no per-suite summary check (it calls `run-tests.bat` and reads its exit code, `:52`, `:61`). The places that do name the deps suite or "four suites" are not listed:
- `tooling/run-tests.bat:3-4` and `:7` ("the lines of all four");
- `tooling/release-tests.bat:3` ("the four unit suites");
- `.claude/CLAUDE.md` *Dev commands › Tests* ("all four suites: backend, frontend, deps, tooling"), *Release* ("the four unit suites"), *Software inventory* ("only its unit tests are: `run-deps-tests.bat`", and "`tooling/deps/` … is meant to move to `smtw-common`"), `## Pre-flight` *Failure logs* ("suites `backend`, `frontend`, `deps`, `tooling`"), and `## Step workflow` *Unit tests* ("backend, frontend, deps, tooling").

The § 10 row for *Software inventory* keeps the audit command but does not say to drop the `run-deps-tests.bat` sentence.

**Failure scenario.** KLA does the lift from this list. The pre-flight's failure-log setting still names `deps-tests-release.log`, and agents look for a fourth summary line that never comes.

**Fix.** In § 9.2, replace the `release-tests.bat` item with the list above, and add the *Software inventory* sentence to the § 10 row.

## Nits

- **CR1-06** (nit) `3-impl-report.md:268`: "so a half-migrated database cannot happen" claims too much; MariaDB DDL is not transactional, and `local_db.py:76-77` relies on re-runs. Write "so a refusal never leaves some pending versions applied and others not".
- **CR1-07** (nit) `3-impl-report.md:248-249`: "**Replaces** (the last bullet): … — **keep it**" contradicts itself; write "**Keeps** the last bullet … and **adds**".
- **CR1-08** (nit) `3-impl-report.md:165`: the log is `scratch/<suite>-tests-<run>.log` when a run name is set (`scratch/backend-tests-s058cr1.log`); add "(with the run name, when one is set)".
- **CR1-09** (nit) `3-impl-report.md:357-366`: `deploy.py:176-177` also aborts when no `PLAY RECAP` is in the output; add it to step 1. Step 4: `--check` only shows the host and the stamped line, and `--stamp-only` leaves the deploy to a person; "help when the playbook already ran" does not describe them.
- **CR1-10** (nit) `3-impl-report.md:393-411`: point 10 leaves out the flow-test rule that every opened dialog is checked to fit (the Android width checks every dialog), and adds the in-view bullet the brief did not list. Add the first; keep the second but name it in "Decisions taken".
- **CR1-11** (nit) `3-impl-report.md:333-336`: point 8 leaves out the Vite gotcha of the junction: Vite serves the junction's files by their real path, so `vite.config.js` adds the real `node_modules` to `server.fs.allow` (`.claude/CLAUDE.md` *Release*).
- **CR1-12** (nit) `3-impl-report.md:528-533`: `run-deps-tests.bat` calls `run_logged.py` at line 9, not 8; the `run-tooling-tests.bat` list spans lines 3-4. After the lift, `run-deps-tests.bat` is removed (§ 9.2), so three wrappers change, not four.
- **CR1-13** (nit) `3-impl-report.md:541-557`: three fixtures name Yantra (`npm-frontend.cdx.json`, `uv-backend.cdx.json`, `uv-backend-nodev.cdx.json`, grep `-il yantra`); say they stay as recorded or are renamed. The note at `:551` says `sys` is imported above; `test_audit_core.py` does not import `sys` today.
- **CR1-14** (nit) `3-impl-report.md:374-377`: the "Where" for point 10 asks itself a question and answers it ("Add one line …? Not needed: …"); state the decision in one sentence (scope A, rule 1).

## Manual checks

None (brief § 5). The impl report's `## Manual checks` says none, which matches.

## Checked and found consistent

- **The rename.** `TEST_SUMMARY_FILE` in `tooling/run_logged.py:10, 63`, `tooling/run-tests.bat:10-12, 22`, `tooling/tests/test_run_logged.py:41`. A grep of `*.py`, `*.bat`, `*.md`, `*.xml`, `*.js` (with `.run`, `.idea`, `backend`, `frontend`) finds the old name only in step documents (history). The summary file is still written (test run above).
- **Quotes.** Every quoted base sentence exists in `.claude/CLAUDE-COMMON.md` or `.claude/SMTW-WebApp-Base.md`. Two differ only by a line break in the file (the squash sentence, `:481-482`; the singleton sentence, `:454-455`). Every named section and heading exists.
- **Point 1** keeps S032's scope: mail relay host, port and credentials, and personal addresses. It says other URLs, realm names and paths may be in a repo. The diff has no real SMTP host, port or address; only `example.test`.
- **Point W** matches `backend/scheduled_tasks.py` (`SCHEDULE` of `(type, "HH:MM")`, pure `due_tasks`, last enqueued from `task_queue`) and `backend/worker.py` (`run_once`: `ensure_schema`, `connect`, `holds_lock` with `IS_USED_LOCK = CONNECTION_ID()` then `GET_LOCK(name, 0)`, `requeue_stale`, `enqueue_scheduled`, drain; three transactions per task). All six APScheduler places in the base are named, and the monitoring daemon's "scheduler" sentence is kept on purpose.
- **Points 2, 4, 9, 12, 13** match `.claude/CLAUDE.md` and the code (`deploy.py` `_FAILED_RECAP`, `HEALTH_TIMEOUT_SECONDS = 180`; `config.py:27-38` fallback in dev and test only).
- **Point 5** otherwise matches `local_db.py` (`ensure_schema` never raises, 30 s retry, `_schema_lock`), `db_helpers.get_db`, the 503 handler and `/api/health`.
- **Generic texts.** No Yantra name, value or step number in a rule; provenance tags only. `erp_spanner.py` is the shared SMTW devops tool.
- **Lift list.** The `sys.path` lines resolve: `parent.parent` of `tooling/common/tests/` is `tooling/common/`, and `parents[2] / "deps"` is `tooling/deps/`, as S057's staged tests do. `run-deps-audit.bat` names nothing of Yantra. No file name clashes with S057's seven staged tests.
- **§ 10** covers every lifted bullet (`:16`, `:17`, `:18`, `:20`, `:21`, `:22`, `:24`, `:25`, `:27`, `:28`, `:29`, `:30`, `:40`). `CLAUDE.md` is unchanged.
- **ISO 27001** numbers carry "to verify" and stay out of the pasted texts.
- **Docs pass.** None due: no migration, and no listed doc names the variable. **Track light** holds: no migration, RBAC, app code or screen.

## Feedback

- hindrance: the secrets hook blocked a read-only `git log` because a path argument matched `secrets_*` (a guessed `backend/secrets_loader.py`); one command lost, re-run without it (1 call).
- idea: for a lift step, a small script that checks each quoted "Replaces" sentence against the synced file, with line breaks folded, would replace the manual grep loop (two false misses from line breaks here).
