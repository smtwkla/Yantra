```
Step: S049 — Pre-flight before a release
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: c32e02f (no step code is uncommitted; only the S049 docs and the README row)

**Verdict: three `major` findings are open.** The stamp can vouch for a commit the tests never ran (BR1-01); two of the four answers KLA can give lead to a release the pipeline refuses (BR1-02); and design decision 3 does not hold against `release.py`'s flow (BR1-03). The idea is right and small; the fixes are rules in the brief, not new parts. Facts file read: `scratch/brief-facts-S049.md`; every "no such file" there is a new file of this step. No floor screen is touched, so `Plant-Facts.md` and `Maintenance-Philosophy.md` do not apply; the console lines and the skill's questions are reviewed under scope B. Full track is right (a new module and a change to the release's tests).

## Findings

### BR1-01 — major — The stamp must be written to the commit the worktree tested, resolved at the start, not to HEAD at the end

**Problem.** § 1.3 says `stamp.write(sha, results)` runs "after a green run on a clean HEAD", and § 1.4 step 4 "after a green run on a clean HEAD → `stamp.write`". Neither says *which* sha. `release-tests.bat` today resolves `REF` (`HEAD`) when it makes the worktree (line 38) and prints the short sha from the worktree (line 49); the working folder's HEAD is free to move for the next 10 minutes. The skill runs pre-flight **in the background** (§ 1.5 item 1) while KLA keeps working. If the write resolves HEAD at the end, a commit made during the run gets the stamp without a test. The clean-tree check at the end does not catch it: after a commit the tree is clean again.

**Why it matters.** This is the one hole that releases untested code with a green line on the console. Everything else the orchestrator asked about (amend, rebase, a copied note) is caught by the `commit:` line; this one is not.

**Options.**
- (a) **Recommended.** Resolve the full sha once, before anything else, from the worktree (`git -C "%WT%" rev-parse HEAD`, next to line 49) into a variable, and write the stamp to that sha only. The stamp text's `commit:` line is that sha. Drop "on a clean HEAD" from the write rule: the worktree tested the commit, so the working folder's state is irrelevant to the stamp (it stays relevant to the *check*, § 1.4 step 2, where it is harmless). State the rule in § 1.3 and § 1.4, and add a unit test: `stamp_text` carries the sha it was given, not a HEAD it looked up.
- (b) Re-check at the end that HEAD still equals the sha the worktree was made from, and refuse to stamp otherwise. Correct too, but it throws away a good run because KLA committed a doc.

### BR1-02 — major — "Leave it" and "Re-run" promise a release the pipeline refuses; say what each answer leads to

**Problem.** § 1.5 item 4: *Leave it* → "KLA releases without this fix". § 1.5 last paragraph: a bug left as *Leave it* or *Re-run* "does not make the run green: no stamp is written, and the release runs its own tests". But the release's own tests are the same tests: `release.py:101-103` aborts on a non-zero `TEST_CMD`, and a steadily failing test keeps it non-zero. So *Leave it* ends in `ABORT: Tests failed.` inside the maintenance window, which is the thing S049 exists to prevent. *Re-run* (a flake that passed on its second try) has the same end unless the flake happens to pass in the release's run.

**Why it matters.** KLA will pick *Leave it* for a test he judges wrong or unimportant, and find out at release time that the only way through is `TEST_CMD=skip` or editing the test by hand. The brief should give the honest routes.

**Options.**
- (a) **Recommended.** *Leave it* means: a fix-lane step marks the test as expected to fail with a comment naming the open fault (`test.fixme` / `test.fail` in Playwright, `xfail` in pytest; the repo's existing convention, CLAUDE.md § SMTW-Review "Tests marked as expected to fail or skipped carry a comment naming the open fault"), and the bug goes to the queue in `docs/steps/README.md`. Then the run can be green and stamped. For *Re-run* (flaky): the brief says why a flake stays red (decision 6, right), and the skill, when every remaining failure is a flake that passed on re-run, offers "Run pre-flight again now" rather than only after fix steps (§ 1.5 item 5). A flake that fails twice in a row is not a flake: it goes to *Fix the test* (S045 is the precedent).
- (b) Keep the answers as they are and say plainly in the option's text that the release will abort on this test until it is fixed or marked; *Leave it* then only records the decision. Honest, but it leaves KLA with the by-hand edit at the worst time.

### BR1-03 — major — Design decision 3 does not hold: a release that fails at build or deploy re-runs the tests on its second try

**Problem.** Decision 3 and § 1.4 step 4: "a release whose tests passed but whose build or deploy failed skips the tests on its second try." Trace `release.py`: the tests run on HEAD = X (line 101); the stamp (pre-flight's or the release's own) is on X; then `bump_ver.py`, `git commit` "release vN" and the tag make a new HEAD = R (lines 131-158); the build or deploy fails; `abort`. The second try runs on HEAD = R, which has no stamp (`commit:` is X's sha), so `release-tests.bat` runs the full 10 minutes again. The release's own stamp on X is never read by anyone: the only path back to X is a failure between the tests and the commit (`bump_ver.py` failing), which is rare.

**Why it matters.** The in-window retry is exactly the case KLA described ("finding a bug costs time" with the users waiting). The user approves decision 3 on a premise that is false. Checked: `POST_BUMP_SCRIPT` is not set in the Release run configs (`.idea/runConfigurations/Release__patch_.xml` and siblings), so R differs from X in `VERSION` only.

**Options.**
- (a) **Recommended.** `stamp.check` accepts HEAD = R when all hold: R's subject starts with `release v`; R's first parent carries a valid stamp (same rules); `git diff --name-only R~1 R` is exactly `VERSION`. The pure check takes these as inputs (`parent_note_text`, `subject`, `changed_files`), so it stays testable without git. The console line then says "Tests passed in pre-flight on … for abc1234, the parent of this release commit (VERSION only)". About fifteen lines, and it is the one scenario decision 3 is for.
- (b) Drop decision 3's claim: say that the release's own green run stamps X for the record only, and that a failed build or deploy re-runs the tests on the retry (as today). Simpler, but it leaves the window problem half solved.
- (c) Also stamp R after a green run — impossible: R does not exist when the tests run.

### BR1-04 — minor — The unit suites' results are not where § 1.2 step 4 says, and the parsers should reuse `run_logged.py`

**Problem.** § 1.2 step 4 reads "each unit suite's last line and its failed test ids (`scratch/release-tests/<suite>-tests.log`)". Checked against the code and the 25-10 release run:
- the files are `<suite>-tests-release.log` (`run-backend-tests.bat:26` and siblings add `-%YANTRA_TEST_RUN%` when the run is not `dev`; `release-tests.bat:32` sets `release`);
- the `== backend: PASSED in 58 s: 2277 passed …` line is **not in the log**. `run_logged.py:50-62` writes the command's output to the log, closes it, then prints the summary line to the console and appends it to `YANTRA_TEST_SUMMARY` = `scratch/release-tests/test-summary-release.txt` (`run-tests.bat:10-11`). A log's last line is pytest's `3012 passed in 97.16s (0:01:37)`, vitest's `Duration 11.58s (…)`, or a teardown warning (`scratch/backend-tests.log` ends in `OSError: cannot send (already closed?)` today);
- the failed ids are in the logs: pytest's `FAILED tests/test_x.py::TestY::test_z` lines (seen in `scratch/backend-tests.log`), vitest's `FAIL` / `×` lines;
- in the 25-10 run, `test-summary-release.txt` holds the frontend, deps and tooling lines but **no backend line**, while `backend-tests-release.log` says `3012 passed`. I could not tell why (a separate backend run at the same minute, or a lost append). The parser must treat a missing suite line as "no result", never as green; green stays the exit code (§ 1.2 step 6, right).

**Why it matters.** The coder would find all this and design the parsers alone; and a parser of "the last line" would mis-read a warning as the result.

**Options.**
- (a) **Recommended.** Counts and verdict per suite from `test-summary-release.txt` (one regular line per suite); failed ids from the logs with two small patterns (pytest `^FAILED (\S+)`, vitest's `FAIL` lines); reuse `run_logged.COUNTS` and `run_logged.ANSI` by import (the tooling tests already put `tooling/` on `sys.path`, `tooling/tests/conftest.py:5`), not a second regex. Name the files correctly in § 1.2 and § 3. The e2e error text in `results.json` (`tests[].results[].errors[].message`) carries ANSI colour codes: strip them with the same `ANSI`.
- (b) Make `run_logged.py` append its summary line to the log too, and parse the log only. One place, but it changes a shared script for this reader alone.

### BR1-05 — minor — Pre-flight refuses a dirty tree, which makes it unusable during normal work; the stamp does not need it

**Problem.** § 1.2 step 1 refuses when the working tree has changes. Pre-flight runs "any time before the maintenance window", that is, while KLA works: right now `docs/steps/README.md` is modified and `docs/steps/S049-pre-flight/` is untracked, so pre-flight would refuse today. The tests run on a worktree of HEAD and the stamp binds to HEAD's sha (BR1-01), so uncommitted files change nothing about what is tested or vouched for. `release.py` refuses a dirty tree for its own reason (the release commit), and still will.

**Why it matters.** A tool that refuses in the common case is run less; the gain of S049 is that pre-flight runs early and often. This is a judgement call for the user, so it is not a nit.

**Options.**
- (a) **Recommended.** Warn and run: "The working tree has uncommitted changes. Pre-flight tests HEAD abc1234 only; commit them before the release." Stamp HEAD as usual. Keep the branch check.
- (b) Keep the refusal (as the brief). Simplest rule; KLA stashes or commits first.

### BR1-06 — minor — Five answers per bug; the question tool allows four, and "Re-run" names an outcome, not an action

**Problem.** § 1.5 item 4 lists five options per question (Fix the code, Fix the test, Re-run, Leave it, Investigate first). AskUserQuestion takes up to four questions per call and **two to four options per question**; the fifth cannot be offered. *Re-run* is also not something KLA asks for: the skill already re-ran the test once in item 3; the answer is "it is a flake, no step". Scope B: options are buttons and should start with a verb that names the result.

**Options.**
- (a) **Recommended.** Four options: **Fix the code**, **Fix the test**, **Accept as a flake** (shown only when the re-run passed; otherwise **Mark as expected to fail**, per BR1-02), **Investigate first**. The report records the re-run result for every failure, so no option is needed for it.
- (b) Two questions per bug (what to do; whether to investigate first). Doubles the taps.

### BR1-07 — minor — One re-run per failure can cost longer than the run itself; re-run the failures together, and name tests by line

**Problem.** § 1.5 item 3 re-runs "that one test once at its device" with `-g "<title>"`. A dead lane fails every test in it (S047 impl report: lane 5, 91 failures); 91 targeted runs at about 1-2 minutes each (stack start, Docker for the iPhone) is over an hour. Also `-g` is a regular expression and the titles hold `(`, `?`, `'` and `+` (e.g. "S018 … (production too)"), so an unescaped title matches nothing or the wrong test; and `%*` in `run-e2e-tests.bat` passes quotes through `cmd`, which mangles some of them.

**Options.**
- (a) **Recommended.** One targeted run for all browser failures: the failed spec files, each failed project as its own `--project=`, and the tests named by line (`tickets-work.spec.js:589`, from `results.json`'s `line`; `run_lanes.py` falls back to `--shard` for line names, which is fine for a handful). Cap it: when more than about 10 tests failed, skip the re-run and say so (one cause, most likely a stack, not ten flakes). Backend failures: one `tooling\run-backend-tests.bat <files> -k "<names>" -n 0` run.
- (b) Keep one run per failure with the title regex-escaped. Correct, slow.

### BR1-08 — minor — Exit code 2 "the tests could not be run" has no source: `release-tests.bat` exits 1 for everything

**Problem.** § 1.2's exit codes: 1 a test failed, 2 refused or the tests could not be run. `release-tests.bat` exits 1 both for a red suite and for "could not create the test worktree" (lines 39-42, 44-48); `run_lanes.py` exits 1 for a dead WebKit server, no test selected, and a merge that failed (line 621). Pre-flight cannot tell them apart from the exit code, and the brief does not say how else.

**Options.**
- (a) **Recommended.** `release-tests.bat` exits 2 when the worktree or the junction could not be made (`release.py` treats any non-zero as failed, so nothing changes there), and pre-flight reads "could not run" from the files: no `test-summary-release.txt` line for a suite, or no `results.json`, means that part never finished. The report says which. Bug reports are written only for failures with a test id.
- (b) Drop exit 2 for "could not be run" and report every non-green as 1 with the text saying why. Simpler; the skill reads the text anyway.

### BR1-09 — minor — Two runs at once share one worktree path and the first is destroyed

**Problem.** `release-tests.bat:37` removes `%TEMP%\yantra-release-tests` before making it. Today one person runs it in the foreground. With pre-flight in the background, a second `/pre-flight`, or a **Release** started while pre-flight still runs, removes the live worktree under the running tests (the e2e lock in `scratch/e2e-run.lock` guards only the browser part). The brief does not mention it.

**Options.**
- (a) **Recommended.** `release-tests.bat` writes a marker file (`%WT%\.running` with the start time) after the worktree is made and deletes it at the end; at the start, a worktree with a marker younger than 30 minutes makes it refuse: "Release tests are already running (started 14:02). Wait for them, or remove %WT% with tooling\release-tests.bat after they end." An older marker is a cut-off run and is cleaned up as today. The skill also checks `git worktree list` for the path before starting and tells KLA.
- (b) Reuse `run_lanes.one_run_at_a_time` on a second lock file from `preflight.py`. Guards pre-flight against pre-flight, not against the Release run config (batch).

### BR1-10 — minor — Standards: ISO 9001 § 8.6 is the clause about release; add who ran it

**Problem.** § 2 cites ISO 9001 § 7.5 (documented information). The clause that matches S049 is **§ 8.6 Release of products and services**: the organisation verifies at planned stages that the requirements are met, release "shall not proceed until the planned arrangements have been satisfactorily completed", and it keeps documented information with *evidence of conformity with the acceptance criteria* and *traceability to the person authorising the release*. The stamp is that evidence; § 7.5 only says how such records are kept. The stamp text has `machine` but no person.

**Options.**
- (a) **Recommended.** Cite § 8.6 first and § 7.5 for the record-keeping; add `by: <git user.name>` to the stamp text (one line, read from `git config user.name`). ISTQB and ISO/IEC/IEEE 29119-3 (test completion report) are cited correctly; "release readiness" is a paraphrase, not a glossary term, and the brief says so.
- (b) Leave § 2 as is. The user is learning the standard, so the better clause is worth the line.

### BR1-11 — minor — Where `stamp.write` gets its counts, and what a failed write does to the exit code

**Problem.** § 1.3's text carries unit counts per suite and the e2e totals; § 1.4 step 4 calls `stamp.write` from batch. The brief does not say where batch gets `results` from, and a `cmd` script cannot build that text. It also does not say what happens when `git notes add` itself fails after a green run.

**Options.**
- (a) **Recommended.** `stamp.py write <sha>` reads `scratch/release-tests/test-summary-release.txt` (the four lines) and `scratch/release-tests/e2e/results.json` (`stats.expected`, `skipped`, `unexpected`, `flaky`; `expected` is the passed count) itself; batch passes only the sha. A failed write prints "The tests passed, but the pre-flight stamp could not be written: <git's line>." and leaves the exit code 0: the tests were green, and pre-flight already reports "green but no stamp" as a fault (§ 1.2 step 6). Say both in § 1.4.
- (b) Pass the counts as arguments from batch. Fragile quoting for no gain.

## Nits

- **BR1-12** (nit) § 1.5: `tooling/common/sync_common.py` lists no skills; it syncs the whole `.claude/skills` folder (`DIRS`, line 37) and only writes files that exist in smtw-common, never deleting. Say: "a Yantra-own skill folder survives the sync because the sync adds and overwrites but never deletes; the same holds for `step`".
- **BR1-13** (nit) § 1.3: write `tested_at` in ISO 8601 with the offset (`2026-10-25T14:30:00+05:30`), which `datetime.fromisoformat` reads and which fixes the zone; show the Indian format on the console. Define the boundary: stale when older than 7 × 24 hours. Note for the record that `notes.rewriteRef` is unset on this machine (checked), so an amend or rebase copies no note, and that the `commit:` check would catch a copied note anyway.
- **BR1-14** (nit) § 1.2 step 1: define "has changes" as `git status --porcelain` non-empty, untracked files included, the same test `release.py:90` makes (if BR1-05 (a) is taken, the same test drives the warning).
- **BR1-15** (nit) § 1.3: write the note with `git notes --ref=preflight add -f -F <file> <sha>` (or `-F -` on stdin) from Python with an argument list, not `-m` with a multi-line text through a shell. `git notes --ref=preflight show <sha>` exits 1 with `error: no note found for object …` on stderr when there is none (checked on git 2.45.1.windows.1); `read` returns None on that, and raises on any other exit code.
- **BR1-16** (nit) § 1.2 step 2: `step_check.py:198` always returns 0; say that step-check's lines go into the report and never change pre-flight's result (the skill judges them).
- **BR1-17** (nit) § 1.4: say where `--fresh` goes in the arguments (test 3 in § 5 uses `--fresh <commit>`): a loop over `%1` that takes `--fresh` and otherwise the ref, instead of `REF=%~1`.
- **BR1-18** (nit) § 1.5 item 2: the steps "not `Done` since the last `release v…` commit" come from `tooling/step-ls.bat`'s table (the skill reads it); name the source.
- **BR1-19** (nit) § 1.5 item 4: `/step ask` needs a step id; use the `S0NN` from the test's title, else the step whose spec file it is in (the map in CLAUDE.md § SMTW-Review).
- **BR1-20** (nit) § 1.4 step 3, scope B: "The pre-flight stamp of abc1234 is 9 days old; it is valid for 7." → "The pre-flight stamp of abc1234 is 9 days old; a stamp is valid for 7 days. The tests run now."
- **BR1-21** (nit) § 1.3: one sentence on the trust boundary: the stamp is a convenience for the person who can already set `TEST_CMD=skip`, not a security control; anyone who can write this repo's refs can write a note.
- **BR1-22** (nit) `docs/steps/README.md` queue: the S048 row still says "Before S049, which drafts its text"; S049 is now pre-flight and the What's new draft is out of scope here.
- **BR1-23** (nit) § 2: one line on ISO/IEC 27001:2022 A.8.32 (change management: changes to production go through a defined, tested procedure) would place the release gate for the IT reader; optional.

## Checked and found consistent

- `release.py` (synced, unchanged): branch check, `git status --porcelain` clean check, `TEST_CMD` with abort on non-zero (lines 97-103), then bump, commit, tag, build, deploy, push. `TEST_CMD=tooling\release-tests.bat` in all three Release run configs. The brief's claim that no change to `release.py` is needed holds.
- The stamp binds to the full sha, so an amended commit, a rebase, a cherry-pick and a different ref all get a new sha and no valid stamp. A note copied by `notes.rewriteRef` (unset here) would carry the old `commit:` line and fail the check. A stamp on a commit that is later released stays local: `git push --follow-tags origin HEAD` pushes no notes ref. Notes commits hang off `refs/notes/preflight`, so `gc` keeps them.
- `git notes --ref=preflight` resolves to `refs/notes/preflight`; `add -f` overwrites an existing note; `list` exits 0 with no output when the ref does not exist (checked, read-only).
- A clock set forward makes a fresh stamp stale (the safe side); set back, an old stamp looks young. One laptop, 7 days; acceptable, and the brief's machine rule already says "passed here".
- `release-tests.bat`: `robocopy`'s exit code never leaves `:copy_e2e_report` (it ends in `exit /b 0`); `%ERRORLEVEL%` after `call` is read on its own line, with no delayed expansion in play; `RELEASE_RESULT` is read after the `if` blocks. Adding `results.json` to the copy (one more `robocopy` line) and the stamp write after line 67 fits that structure. The worktree is fresh each run, so a stale `results.json` cannot be copied.
- `results.json` is written by the merge config (`frontend/playwright.merge.config.js`, the `json` reporter) in every lane mode, `E2E_LANES=1` included (`run_lanes.py:611`); `stats` holds `expected`, `unexpected`, `skipped`, `flaky`; each failed test has `projectName`, `file`, `line` and `results[].errors[].message`. The step id is the title's `S0NN:` prefix in every spec checked.
- S047's figures: 320–338 s for the browser part, about 2 minutes for the unit suites; the 10–12 minute assumption holds with the worktree and `uv sync` added. The throw-away commit objects of § 5 test 3 are S047 D2's method.
- The fix lane and `/step ask` exist in `.claude/skills/step/SKILL.md` with the criteria the brief relies on; a test-only fix fits the lane (S041, S042). The brief's limits (never commits, never stamps by hand, never runs the release) match CLAUDE-COMMON § Release & deployment authorization.
- Right-sized: two stdlib modules, one batch change, one skill; no new dependency, no flag beyond `--fresh`. The pure `check` / parsers in `stamp.py` and `preflight.py` with the shell at the edges follow "pure core, thin shell".
- Open questions: Q1 (no audit in pre-flight) — agree; the audit needs the network and often has no fix. Q2 (steps not `Done` as information) — agree; today most committed steps wait on device checks for days, so blocking would block every release.
- Manual check: one, plain, on KLA's laptop with its place named; no device rows are due.
