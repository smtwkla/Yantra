# Fixes for the test-isolation review (round 1)

Review: `2026-10-22-test-isolation-review.md` (not edited). Change: tooling, not a step. Not committed.

| ID | Result | What changed |
|---|---|---|
| CR1-01 | Fixed | `tooling/release-tests.bat` adds the worktree with `--lock --reason "..."`. `:remove_worktree` removes the junction first, then runs `git worktree unlock`, then `git worktree remove --force`. A stale locked worktree from a cut-off run is cleaned the same way at the start of the next run. `.claude/CLAUDE.md` § Release warns: never remove that worktree by hand. Proved on a temporary commit object: the worktree showed `locked` during the run and was gone after; a second run over a stale locked worktree with a live junction removed both; `frontend\node_modules` kept its 76 entries both times. I did not run `git worktree remove --force` on the locked worktree myself (refused by the permission check); the lock is what git documents. |
| CR1-02 | Already fixed before this round | `coder.md` and others carry the run-name rule. No change. |
| CR1-03 | Fixed | `run-frontend-tests.bat`, `run-deps-tests.bat`, `run-tooling-tests.bat` set `LOG` to `<suite>-tests.log`, or `<suite>-tests-<run>.log` when `YANTRA_TEST_RUN` is set and is not `dev`. The release run writes `frontend-tests-release.log` etc. in `scratch\release-tests\`. |
| CR1-04 | Fixed | `build.bat` header and `.claude/CLAUDE.md` say `--dry-run` runs the git refusals (dirty tree, no tag, HEAD not at the tag) and the checkout, and does not check the registry. |
| CR1-05 | Documented, not changed | The xdist controller needs `import app` (the conftest imports it), and `app` needs a database. Skipping the create would add a second code path through `conftest.py` for one idle database per run. The reason is in `_create_test_db`'s docstring. |
| CR1-06 | Documented | `.claude/CLAUDE.md` (Dev commands, Tests) has the two-step command: write the `DROP DATABASE` list for `vel_yantra_test`, `vel_yantra_upgrade` and every `vel_yantra_test_*` / `vel_yantra_upgrade_*`, read it, run it. The SELECT was run to check it lists the databases (56 test/upgrade ones plus the 2 old ones). Nothing was dropped. |
| CR1-07 | Fixed | `local_db.named_lock` raises `ValueError` over 64 characters (`MAX_LOCK_NAME_LENGTH`). Test: `test_modules.py::TestMigrationLock::test_a_name_over_the_mariadb_limit_is_refused`. |
| CR1-08 | Fixed | `.claude/CLAUDE.md` Worker line: `named_lock(LOCK_WORKER, database)`. |
| CR1-09 | Proposal written | `2026-10-22-base-proposal-lock-names.md`, for the user to paste into smtw-common. The synced `.claude/SMTW-WebApp-Base.md` is not edited. |
| CR1-10 | Not in this task | `sbom/backend.cdx.json` is already in the working tree; the user commits it with the change. |
| CR1-11 | Not in this task | Accepted by the reviewer's recommendation; record in the next dependency report. |
