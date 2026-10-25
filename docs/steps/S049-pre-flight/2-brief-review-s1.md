```
Step: S049 — Pre-flight before a release
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 01d3566 (uncommitted: `docs/steps/README.md` and S054's brief, step documents only)

**Verdict: no blocker or major finding. The brief still holds against HEAD; four nits, all wording.**

Staleness review of the approved brief (baseline c32e02f) against the four commits since:
9739276 (readings UI), e08f5bb (S049's step docs), b11db2e (S054: `test.use({ serviceWorkers:
"block" })` in `frontend/e2e/tickets-work.spec.js`, one sentence in `.claude/CLAUDE.md` § Browser
tests) and 01d3566 (`release v0.1.9`, `VERSION` only). Of the files in § 3 Where, only
`.claude/CLAUDE.md` changed. `tooling/common/release.py`, `tooling/release-tests.bat`,
`tooling/common/sync_common.py`, `tooling/e2e/run_lanes.py` and `tooling/tests/conftest.py` are
unchanged since the baseline. I re-read the brief's statements about those files and about the
release flow, and checked them against HEAD and against the v0.1.9 release run of today
(`scratch/release-tests/`, 17:56–18:04). I did not re-review the rest of the brief.

## Nits

- **BS1-01** (nit) header: `Status` ends "not coded yet (after S054)". S054 is `Done` (b11db2e). Drop
  "(after S054)". After this review, set `Baseline:` to `01d3566`.
- **BS1-02** (nit) § 1.2 *Known fault*: "its specs use `test.skip(condition, reason)` only" now reads
  loosely. Two specs also carry a file-level `test.use({ serviceWorkers: "block" })`
  (`readings.spec.js:21` already at the baseline; `tickets-work.spec.js:16` since S054), and
  `.claude/CLAUDE.md` § Browser tests makes that a rule for every spec that fakes requests. Neither is
  an expected-to-fail mark, so the convention the brief sets (`test.fail()` per test) still stands and
  does not collide with it. Suggested wording: "Yantra has no expected-to-fail mark yet; its only
  per-test modifier is `test.skip(condition, reason)`." Fact, not a design change.
- **BS1-03** (nit) intro and § 6 Q4: "about 10 minutes" / "about 10–12 minutes". The v0.1.9 release run
  took about 8 minutes: the four unit suites 88 s (`test-summary-release.txt`, done 17:57:30), the
  browser tests at Full 17:58–18:04 (lane logs: 5.1–5.8 min each), the report copied 18:04:04, the
  release commit 18:04:06. Say "about 8–10 minutes", so the skill's "how long it may take" line
  (§ 1.6 step 3) is right.
- **BS1-04** (nit, outside S049, for the record): `release.py:119-122` puts every body line of the commits
  since the last release into the release commit's bullets, so `release v0.1.9`'s body carries the
  `Co-Authored-By:` and `Claude-Session:` trailers as bullets. Nothing in S049 reads the message (the
  carry checks `git diff --name-only`, not the text), so no change to this brief; a one-line filter for
  the queue's Tidy-up, if KLA wants it.

## Checked and found consistent

- **`release.py` line numbers and steps.** The dirty-tree refusal is `release.py:90-94` (§ 1.3, § 1.5);
  step 2 "Run tests" is lines 96–103 and runs `TEST_CMD` with `shell=True` (§ 1.4 step 5); step 4
  commits with `git add VERSION` only (lines 147–160) after an optional `POST_BUMP_SCRIPT` (lines
  141–145); the push is `git push --follow-tags origin HEAD` (line 186), which pushes no notes ref
  (§ 1.3). `TEST_CMD` is `tooling\release-tests.bat` in all three Release run configs; none sets
  `POST_BUMP_SCRIPT` (§ 1.5 "unset in Yantra's Release run configs").
- **The carried stamp (§ 1.5, decision 4).** `git show --stat 01d3566`: `VERSION | 2 +-`, one file;
  `git diff --name-only b11db2e 01d3566` prints `VERSION` alone. The rule "HEAD's first parent carries
  a valid stamp and the diff lists exactly `VERSION`" would have carried today's stamp from b11db2e to
  01d3566.
- **The release flow today.** The release tested b11db2e (committed 17:54:09), then committed 01d3566
  two seconds after the browser report was copied: tests first, bump after, as § 1.1 assumes. The
  run was green: 3075 backend, 179 frontend, 42 deps, 172 tooling; the six e2e lanes all "passed",
  with 7 conditional skips (`test.skip`, `notifications.spec.js`, `screens.spec.js`).
- **`release-tests.bat` (§ 1.2, § 1.7).** Unchanged. It tests a worktree of HEAD in
  `%TEMP%\yantra-release-tests` ("Tests a clean copy of HEAD: yes"), sets
  `YANTRA_TEST_LOG_DIR=scratch\release-tests`, and its `:copy_e2e_report` copies the HTML report,
  `e2e-lanes` and `e2e-backend*.log` (lines 77–79), not `results.json`; § 1.7's change is still due.
- **The failure logs (§ 1.2).** `scratch/release-tests/` holds `backend-tests-release.log`,
  `frontend-tests-release.log`, `deps-tests-release.log`, `tooling-tests-release.log` and
  `test-summary-release.txt` (one `== <suite>: PASSED in …` line each), and `e2e/html/`,
  `e2e/e2e-lanes/`, `e2e/e2e-backend-lane<n>.log`, as the brief names them. (Three logs without the
  `-release` suffix from 22-10 lie beside them; the skill reads the suffixed names, so they do no harm.)
- **The lock copy (§ 1.4 step 2).** `run_lanes.main_scratch` (line 298, `git rev-parse
  --git-common-dir`) and `one_run_at_a_time` (line 508, `msvcrt` / `fcntl`) exist as described.
  `.gitignore:15` is `scratch/`.
- **The lift (§ 1.8).** `sync_common.FILES` lists `tooling/common/release.py`; `.claude/skills` is in
  `DIRS`, synced whole; `tooling/tests/conftest.py` adds only `tooling/` to `sys.path` (BR2-08).
- **Git facts (§ 1.3).** git 2.45.1; `notes.rewriteRef` not set; `refs/notes/preflight` does not exist
  yet.
- **S054's CLAUDE.md change** is one sentence in the § Browser tests bullet. The coder's new
  `## Pre-flight` section and the § Release bullet (§ 3 Docs) do not touch it, and the settings
  reader (heading to next `## `) is unaffected.
- **§ 1.6 step 5** "Yantra test names start with `S0NN:`" still holds (every lane log).
