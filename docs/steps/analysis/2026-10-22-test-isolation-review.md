# Code review — test isolation, quiet test output, release tests and build from a worktree

- **Change:** tooling change, not a step (no brief): parallel backend tests with one database per run and worker, per-database named locks (`backend/local_db.py`, `backend/worker.py`), `tooling/run_logged.py`, `tooling/release-tests.bat`, `tooling/build/build.bat` from a worktree of tag `v%VERSION%` with `--dry-run`. The user approved the design.
- **Reviewer:** code-reviewer (Claude), round 1
- **Date:** 22-10-2026
- **Input:** working-tree diff (`git diff -w --ignore-cr-at-eol`) of the files listed by the orchestrator, the coder's report summary, `pytest-xdist` in `backend/pyproject.toml` / `uv.lock` (committed in 63eda6c).

**Verdict: no `blocker` or `major` finding is open.** There are 3 `minor` findings and 8 nits.

## Test results

- `tooling/run-tests.bat` with `YANTRA_TEST_RUN=crtools`, run while another reviewer ran tests under another run name: **exit 0**.
  - backend: PASSED in 55 s, 2280 passed (`scratch/backend-tests-crtools.log`);
  - frontend: PASSED in 26 s, 114 passed;
  - deps: PASSED in 1 s, 42 passed;
  - tooling: PASSED in 1 s, 91 passed;
  - the summary block printed all four lines and `== ALL SUITES: PASSED`.
- The failure path: `tooling\run-tooling-tests.bat -k zz_no_such_test_zz` exits **5**, and its log ends `91 deselected`. pytest's "no tests collected" code passes through, so the suite reads FAILED, not PASSED.
- `tooling/build/build.bat --dry-run` on this dirty tree: it **refused**, with `ERROR: the working tree has changes...` and exit 1. No worktree was left behind (`git worktree list` shows only the main one). I did not run `build.bat` without `--dry-run`.
- No e2e run. The change touches no screen, no API and no `e2e/support/` file.
- Junction safety, tested in a scratch git repo with a sentinel file as the junction target:
  - `git worktree remove --force` on a worktree that holds a junction **deletes the target's files** (the sentinel was gone). This is why the junction must go first. The script does remove it first (see CR1-01).
  - `if exist` sees a live junction and a dangling junction (both TRUE).
  - `rmdir` without `/s` removes only the link; the sentinel was kept.
  - `rmdir /s /q` on a folder that holds a junction does not follow the junction; the sentinel was kept.
- `!BUILD_BACKEND!` with quoted arguments and a path with a space: the command got the right argument list, and `if errorlevel 1` saw its exit code 3.

## Findings

### CR1-01 (minor) — a stale release worktree keeps a junction that `git worktree remove --force` follows

`tooling/release-tests.bat:25` and `:30`.

**Problem.** The script itself is safe: `:remove_worktree` removes the junction with `rmdir` (no `/s`) and stops if the junction is still there, before it runs `git worktree remove --force`. The test above confirms each guard. A run that is cut off (Ctrl+C, a closed terminal, a PyCharm stop during the release) leaves `%TEMP%\yantra-release-tests` registered as a git worktree, with `frontend\node_modules` still a junction to the working folder's.

**Failure scenario.** After a cut-off release, the user sees the extra worktree in `git worktree list` or in PyCharm's Git worktree view. The user removes it there, or runs `git worktree remove --force`, which git's own hint suggests. Git follows the junction and empties `frontend\node_modules` of the working folder. No source is lost, but `npx npm@11 install` / `npm ci` must run again, and an agent's run in between fails in a confusing way.

**Fix.** Add the worktree with `--lock --reason "holds a junction to frontend\node_modules; remove it with tooling\release-tests.bat"`. A locked worktree refuses `git worktree remove --force` (it needs `-f -f`), and `git worktree prune` skips it. In `:remove_worktree`, run `git worktree unlock` after the junction is gone, then remove the worktree. Also say in `.claude/CLAUDE.md` § Release: "never remove this worktree by hand; run `tooling\release-tests.bat` again, which removes the junction first."

### CR1-02 (minor) — the agents are not told to set `YANTRA_TEST_RUN`

`.claude/CLAUDE.md:18`; `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`, `.claude/skills/step/SKILL.md` do not mention it.

**Problem.** The run name defaults to `dev`. Only `.claude/CLAUDE.md` says "two runs at the same time need different `YANTRA_TEST_RUN` values". The prompts that start test runs (the coder's, the code reviewer's, `/step`) do not say it. The orchestrator now launches agents that test at the same time, as this review did.

**Failure scenario.** `/step` runs a coder and a code reviewer of two steps in parallel. Neither sets the variable. Both use `vel_yantra_test_dev_gw0..7`. `_clean_tables` of one run deletes the rows of the other mid-run. The tests fail at random, and an agent may "fix" a test that is not broken. The isolation this change builds then holds only for the release run.

**Fix.** Choose one:
- (recommended) In `coder.md` and `code-reviewer.md`, tell each agent to run the tests with `YANTRA_TEST_RUN` set to its step and role (e.g. `s021coder`, `s021cr2`).
- Or have `/step` set the name when it launches an agent.

Either way, the old `dev` stays the default for the user's own runs.

### CR1-03 (minor) — the frontend, deps and tooling logs are shared between runs

`tooling/run-frontend-tests.bat:7`, `tooling/run-deps-tests.bat:7`, `tooling/run-tooling-tests.bat:8`.

**Problem.** The backend log and the summary file carry the run name (`backend-tests-<run>.log`, `test-summary-<run>.txt`). The other three suites write `scratch\frontend-tests.log`, `deps-tests.log` and `tooling-tests.log` for every run. The release run is safe, because `release-tests.bat` sets its own `YANTRA_TEST_LOG_DIR`.

**Failure scenario.** Two agents run `run-tests.bat` with different run names, as this review did. Both open `scratch\frontend-tests.log` for writing, and the output of one overwrites or interleaves with the other. One agent's summary line says `frontend: FAILED ... (log: ...frontend-tests.log)`. The agent reads the log, as `.claude/CLAUDE.md` tells it to, and sees the other run's passing output, or a mix of both. This is the "do not re-run, read the log" path the change sets up.

**Fix.** Name the three logs as the backend's: `<suite>-tests.log` for `dev`, `<suite>-tests-<run>.log` otherwise. It is one `if` line in each script, or put the rule once in `run_logged.py`, which already reads the environment.

## Nits

- **CR1-04** (nit) `tooling/build/build.bat:10`, `.claude/CLAUDE.md:23`: `--dry-run` skips the registry refusal ("a version already in the registry"), because that check needs the login. Write "the git refusals and the checkout" rather than "its refusals".
- **CR1-05** (nit) `backend/tests/conftest.py:56`: the xdist controller imports `conftest.py`, so it creates `vel_yantra_test_<run>_main` and migrates it through `app`'s `ensure_schema`. No test ever uses that database (it is in the DB list for every run name). Say so in the comment, or skip `_create_test_db` when `PYTEST_XDIST_WORKER` is unset and `-n` is given. The comment is enough.
- **CR1-06** (nit) dev MariaDB: the test databases are kept per run name and never dropped. Today there are 4 run names, about 45 test databases, plus the old `vel_yantra_test` and `vel_yantra_upgrade`, which nothing uses now. Add one line to `.claude/CLAUDE.md` on how to drop them (`dev-db-reset.bat`, or a `DROP DATABASE` list), and drop the two old ones.
- **CR1-07** (nit) `backend/local_db.py:34`: the docstring names MariaDB's 64-character limit, but `named_lock` does not check it. A database name over 46 characters would give a `GET_LOCK` error at startup. Add `assert len(name) <= 64`, or leave it with a comment saying production names are short.
- **CR1-08** (nit) `.claude/CLAUDE.md:27`: "one worker, `GET_LOCK(LOCK_WORKER)`" should say `named_lock(LOCK_WORKER, database)`, as line 18 does.
- **CR1-09** (nit) `.claude/SMTW-WebApp-Base.md` § Lock-ID registry: this is a gap to raise, not to fix here. The base names lock keys only. Yantra's finding, that MariaDB `GET_LOCK` names are server-wide, so a name must carry the database's, is worth adding to the base for the other SMTW apps that share a DB server.
- **CR1-10** (nit) `sbom/backend.cdx.json`: `pytest-xdist` and `execnet` went into `pyproject.toml` / `uv.lock` in commit 63eda6c without the SBOM (`.claude/CLAUDE.md` § Software inventory). Commit the regenerated `sbom/` with this change.
- **CR1-11** (nit) dependency health: `pytest-xdist` 3.8.0 (01-07-2025) has had no release in 12 months, as the coder flagged. It is the pytest-dev organisation's own plugin and is still maintained, and no maintained alternative exists. It is in the `dev` group only, so it is never in an image. Recommendation: keep it, and record it as accepted in the next dependency report.

## Checked and found consistent

- **Lock names in production.** The migration lock is `yantra_migrations:vel_yantra_master` (35 characters), and the worker lock is `yantra_worker:vel_yantra_master`. Every product use goes through `named_lock`: `init_db` takes and releases the same `lock` variable, and `Worker` builds its default name once. No other code reads `LOCK_WORKER` or `LOCK_MIGRATIONS` (grep).
  - The worker is still a singleton per database.
  - A second Yantra database on the same server (Plan.MD's later `vel_yantra_test`) now gets its own worker. The old global name would have blocked it.
  - During a deploy, compose stops the old container before it starts the new one, so two versions do not migrate at once.
  - If an old worker and a new one ever ran together, they would not hold one shared lock. `claim_next` uses `FOR UPDATE SKIP LOCKED`, so a task is still claimed once.
  - A rollback runs one version only.
- **Database names are safe.** `db_names._part` keeps `[a-z0-9]` and at most 12 characters, so names stay under 64 (longest upgrade name 44, longest test lock 60). The `CREATE DATABASE` f-string holds only that cleaned identifier. The fixed prefixes `vel_yantra_test_` / `vel_yantra_upgrade_` can never name `vel_yantra_master`, `vel_yantra_e2e` (whose guard needs `_e2e` at the end) or another app's database. The upgrade tests drop only `UPGRADE_DB`.
- **The wildcard grants are dev-only.** They run as root on the `docker-compose.dev.yml` container (`run-backend-tests.bat`) and in its first-init script. `` `vel\_yantra\_test\_%` `` escapes `_`, so it matches only names that start with `vel_yantra_test_`. In the batch file, `%%` gives `%`.
- **Isolation under `--dist loadscope`.** Each worker process has its own databases, its own `DATA_DIR` (`mkdtemp` per process, removed by the session fixture and by `atexit`), and its own worker-test lock (`TEST_WORKER_LOCK`). `_clean_tables` runs once per worker session on that worker's database. Every `information_schema` query in the v20–v24 tests filters by `DATABASE()`. No backend test writes a fixed path. The full suite passed in two runs (the coder's and mine), alongside another run.
- **`test_init_db_holds_the_lock_of_its_database`** asserts that the lock is held during the migration check and free afterwards, not only the name's format.
- **`run_logged.py` exit codes.** The verdict comes only from the child's exit code, so a failing suite cannot print PASSED. The count parsing is for display only. If `Popen` fails, Python exits 1 with a traceback and no line is printed; `run-tests.bat` then says "A suite with no line above failed". `run-tests.bat` runs all four suites and exits 1 if any `call ... || set "FAILED=1"` was hit. Each suite script ends with `exit /b %ERRORLEVEL%`. `release.py` runs `TEST_CMD` with `shell=True` and aborts on a non-zero code.
- **`release-tests.bat`.**
  - The junction is removed before any recursive delete, at the start, after a failed `mklink`, and at the end.
  - Exit code: `RESULT` holds `run-tests.bat`'s code, and a cleanup failure does not hide a failed run.
  - The worktree uses `example_secrets_app.py`, whose dev credentials match the dev compose.
  - `release.py` checks for a clean tree first, so a worktree of HEAD is the tree being released.
- **`build.bat`.**
  - The git refusals (dirty tree, no tag, HEAD not at the tag) run before the checkout.
  - The checkout is `worktree add --detach` of `v%VERSION%`, and its `VERSION` is checked against the tag.
  - The images are built from `%SRC%` with the worktree's own Dockerfiles and `.dockerignore`.
  - The checkout is removed after each failure and before the push.
  - `--dry-run` exits before any login, build or push.
  - The build checkout holds no junction, so `rmdir /s /q` is safe there. `git worktree remove` refuses the main worktree.
- **Windows batch.** `setlocal` in every script. Paths are quoted, and spaces are tested. `||` after `call` of a batch that ends in `exit /b N` works. `goto :checkout` from inside an `if` block is valid. `npx vitest run` is the same as `npm test` (`"test": "vitest run"`).
- **Scope A.** `.claude/CLAUDE.md` and the batch-file headers follow scope A. They put the point first and use one term for the run name (`YANTRA_TEST_RUN`).

## Manual checks for the user

- [ ] Once this change is committed, run one release test on it: `tooling\release-tests.bat`. Check that it ends with `== ALL SUITES: PASSED`, that `%TEMP%\yantra-release-tests` is gone, and that `frontend\node_modules` is intact. This review could not run it end to end, because HEAD does not yet hold the new scripts.
- [ ] On the next real release, check that `build.bat` builds both images from `%TEMP%\yantra-build-v<version>`, then removes the folder before the push. Only `--dry-run`'s refusal path was tested here.
- [ ] After the next deploy, check the backend and worker logs for `Worker lock yantra_worker:vel_yantra_master taken`, and check that the tasks card in Settings shows the worker running.
