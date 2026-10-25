```
Step: S049 — Pre-flight before a release
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S049 — implementation report

Pre-flight is built: `/pre-flight` (or the new **Pre-flight** run config) runs the release's tests on HEAD before the maintenance window, and a green run stamps that commit with a git note. `release.py` then skips its tests for that commit, and carries the stamp to the release commit. All six runs of § 5 give what the brief states (§ 7). Amendment A1 is in (environment first, the run config, no input). The four unit suites pass (§ 8). No app code changed. Departures from the brief, all small, are in § 4: **D3** `carry_text` takes the check's inputs too; **D4** `write` returns git's message instead of `False`; **D9** run 5 sets `TEST_CMD` in the environment (A1) instead of editing `CLAUDE.md`.

## 1. What was built

- **The stamp module** `tooling/common/preflight_stamp.py` (generic, stdlib):
  - a pure core: `stamp_text`, `parse`, `check`, `carry_text`;
  - a shell: `read`, `write`, `head_sha`, `tree_clean`, `machine_name`, `release_gate`, `carry`, `preflight_running`, and the pre-flight lock;
  - a CLI: `preflight_stamp.py gate "<test command>"` prints what the release would decide and changes nothing.
- **The run** `tooling/common/preflight.py` (generic, stdlib): the settings, one run at a time, the refusals, the sha read once, the test command, "HEAD moved", the stamp. Exit codes 0 / 1 / 2 as § 1.4.
- **The release** `tooling/common/release.py`, step 2 and step 4 only (§ 1.5):
  - a pre-flight still running aborts the release before any test or bump;
  - a valid stamp skips `TEST_CMD` ("Tests passed in pre-flight on … for abc1234. The release does not run them again.");
  - no valid stamp: the reason in one line, then `TEST_CMD` as before; a green run stamps the sha read before it;
  - after the `release vX.Y.Z` commit, the parent's valid stamp is carried when only `VERSION` changed;
  - without `preflight_stamp.py` (a partial sync) the release says "The pre-flight check is not installed. The tests run now." and runs its tests.
- **The skill** `.claude/skills/pre-flight/SKILL.md` (generic): § 1.6.
- **Yantra's settings**: the `## Pre-flight` section of `.claude/CLAUDE.md`, and `tooling/release-tests.bat` copies `results.json` too.
- **A1**: `TEST_CMD` and `PREFLIGHT_CLEAN_COPY` from the environment first; the run config `.idea/runConfigurations/Pre_flight.xml`; no input ever awaited.

## 2. How it works

**The stamp.** A note in `refs/notes/preflight`, plain `key: value` lines:

```
preflight: 1
result: passed
commit: <full sha>
tested_at: 2026-10-25T19:02:11+05:30
test_cmd: tooling\release-tests.bat
machine: <platform.node()>
by: <git user.name>
carried_from: <full sha>        (a carried stamp only)
summary: <one of the last 10 non-empty output lines>   (repeated)
```

`write` puts the text in a temporary file and runs `git notes --ref=preflight add -f -F <file> <sha>`. `check(note_text, head_sha, test_cmd, now, machine)` answers `(valid, reason)` in this order: no note → "No pre-flight stamp for abc1234."; not a stamp, an unknown version or an unreadable time → "… cannot be read."; `result` not `passed` → "… does not record a pass."; another `commit` → "… names another commit."; older than 7 × 24 h → "… is 9 days old; a stamp is valid for 7 days." (between 168 h and 8 days: "more than 7 days old"); another `test_cmd` (exact string equality) → "… was made with another test command."; another machine → "… was made on another computer." Each reason ends with "The tests run now." A valid stamp gives "Tests passed in pre-flight on 25-10-2026 19:02 for abc1234. The release does not run them again." (IST, DD-MM-YYYY HH:MM).

`carry_text(parent_note, parent_sha, changed_files, release_sha, test_cmd, now, machine)` returns a stamp only when the changed files are exactly `["VERSION"]` and the parent's stamp passes `check`. The new stamp names the release commit and `carried_from: <parent>`, and keeps the parent's `tested_at`, so it expires with the original. `carry(release_sha, test_cmd)` reads the first parent (`rev-parse <sha>^1`), `git diff --name-only <parent> <sha>`, the parent's note, and writes the result.

**Never fail a release.** Every shell function that `release.py` calls catches its own errors: `release_gate` answers "not valid" ("The pre-flight stamp could not be checked: … The tests run now."), `write` and `carry` return a warning text, `preflight_running` and `head_sha` answer `False` / `None`. `release.py` imports the module in `try/except ImportError`.

**The lock.** `scratch/preflight.lock` in the main working folder (the parent of `git rev-parse --git-common-dir`). `held_lock(path)` tries `msvcrt.locking` / `fcntl.flock` once, without waiting, and yields `True` or `False`. `preflight.py` holds it for the whole run; `preflight_running()` tries it and gives it back at once. When the lock file does not exist, no pre-flight ever ran, so it answers `False` without creating anything.

**`preflight.py`, in order:**
1. The settings: `read_settings(text, os.environ)`. The test command is `TEST_CMD` when set and not empty, else the section's *Test command*; "clean copy" is `PREFLIGHT_CLEAN_COPY` when set, else the section's line, else `no`. No test command → the brief's line, exit 2.
2. The lock; taken elsewhere → "Another pre-flight is running. Wait for it to finish.", exit 2.
3. Not on `main` → refusal. Uncommitted changes with "clean copy" `no` → refusal; with `yes` → "The working tree has uncommitted changes; the tests run on commit abc1234 only."
4. The full sha of HEAD, once.
5. "Pre-flight runs <command> on abc1234. Log: <path>", then the test command (`shell=True`, in the repo root, stdin from `DEVNULL`), its output to the console and to `scratch/preflight/<short-sha>.log`; the last 10 non-empty lines are kept for the stamp's summary.
6. HEAD again: moved → no stamp, exit 1; red → no stamp, exit 1; green → `write` on the sha of step 4 → "Pre-flight passed for abc1234. Stamped until 01-11-2026 19:02.", exit 0, or the failed-write line, exit 1.

**`release.py` step 2:** first `preflight_running()` (abort); then, unless `TEST_CMD=skip`, `release_gate(TEST_CMD)`; valid → no test run; else `head_sha()` before `run(TEST_CMD)` and `write(that sha, TEST_CMD)` after a green run (a failed write prints "WARNING: the pre-flight stamp could not be written: … The release goes on."). **Step 4:** right after the commit, before the tag, `carry(head_sha(), TEST_CMD)`; its line is printed when there is one.

## 3. Files touched

| File | Change |
|---|---|
| `tooling/common/preflight_stamp.py` | new: the stamp, the gate, the carry, the lock, the `gate` CLI |
| `tooling/common/preflight.py` | new: the run (A1: the environment first, stdin from `DEVNULL`) |
| `tooling/common/release.py` | the guarded import; step 2 (running pre-flight, the gate, the stamp after a green run); step 4 (the carry); three docstring lines. Nothing else changed, CRLF kept |
| `tooling/tests/test_preflight_stamp.py` | new: 42 tests (the pure core, the shell with git stubbed, release.py steps 2 and 4 with `run` faked) |
| `tooling/tests/test_preflight.py` | new: 21 tests (the reader, A1's environment, refusals, lock, sha once, HEAD moved, red, failed write, the tee, no input) |
| `.claude/skills/pre-flight/SKILL.md` | new: the skill (§ 1.6) |
| `tooling/release-tests.bat` | copies `scratch\e2e-report\results.json` to `scratch\release-tests\e2e\` too; comment item 5 |
| `.claude/CLAUDE.md` | the `## Pre-flight` section; the *Pre-flight (S049)* bullet after § Release |
| `.idea/runConfigurations/Pre_flight.xml` | new, gitignored (A1): the **Pre-flight** run config |
| `docs/steps/S049-pre-flight/1-brief.md`, `docs/steps/README.md` | Status `In code review` |

## 4. Decisions taken

- **D1** The `## Pre-flight` section sits in `.claude/CLAUDE.md` between *Yantra Specifics* and *Docs to keep current*, as its own `##` section, because the reader stops at the next `## `.
- **D2** Extra console lines the brief does not word, all scope B: "Pre-flight runs <command> on abc1234. Log: <path>" (start of a run); "Git could not read HEAD, so pre-flight cannot run. Check the repo with git status." (exit 2); the gate's reasons "… cannot be read.", "… does not record a pass.", "… names another commit.", "Git could not read HEAD, so the pre-flight stamp is not checked.", "The pre-flight stamp could not be checked: <error>."; for the release "The pre-flight stamp of abc1234 is carried to the release commit def5678." and the two warnings.
- **D3** `carry_text` takes `parent_sha`, `test_cmd`, `now` and `machine` beside the brief's three arguments: "the parent carries a **valid** stamp" needs `check`'s inputs, and the core stays pure.
- **D4** `write(sha, test_cmd, tested_at=None, summary=())` returns `None` on success and git's message on failure (brief: "returns `False`"), because `preflight.py`'s line must name git's message (§ 1.4). The shared low-level writer `_add_note` serves `write` and `carry`.
- **D5** The age line says "more than 7 days old" between 168 h and 8 days, where whole days would read "7 days old; a stamp is valid for 7 days".
- **D6** A future `tested_at` (a clock set back) is not refused: the brief's rule is "no more than 168 h before now" (r2 accepted the clock case).
- **D7** "Tests a clean copy of HEAD" missing or not `yes` counts as `no`, the side that refuses a dirty tree. With `TEST_CMD` set and no section at all, pre-flight runs with "clean copy" `no` (A1: the section is only the fallback).
- **D8** The pre-flight-running check in `release.py` comes first in step 2, before the `skip` branch, so it holds also for `TEST_CMD=skip`; it is still before any test or bump.
- **D9** § 5 run 5 sets `TEST_CMD=cmd /c exit 1` in the environment for one run (A1's own route) instead of editing and reverting `CLAUDE.md`; the result is the same and nothing needed reverting.
- **D10** `tested_at` is the time the run finished green, so the 7 days count from the pass.
- **D11** The lock code is a deliberate copy of `run_lanes.main_scratch` / `one_run_at_a_time` (BR2-07), changed to try once instead of waiting.
- **D12** The release's own stamp (after its green `TEST_CMD`) has no `summary:` lines: `release.py` lets the test output pass to the console as before and does not capture it.
- **D13** The skill's `RERUN_MAX` (10) is a number in the skill's text: no code reads it.
- **D14** A1 item 2 in the brief (line 406) reads "`TEST_CMD=tooling` / `elease-tests.bat`" across two lines: the `\r` of `\release` became a line break when it was written. The run config has the right value `tooling\release-tests.bat`, as in the Release run configs. The planner may fix the brief's text.

## 5. Not done, deferred or assumed

- The lift to `smtw-common` is KLA's (§ 1.8); nothing was written outside the repo. The text is below.
- The release itself was never run (it bumps, tags, builds, deploys and pushes). Its step 2 and step 4 are covered by unit tests with `run` faked, and by the `gate` CLI and the carry on throw-away commits (§ 7). The manual check below is the end-to-end proof.
- The stamp of run 1 stays on HEAD `01d3566` (it is real: the tests passed on that commit). Next release from that commit would skip its tests within 7 days. HEAD will move when KLA commits S049, so in practice the next release tests again or needs a new pre-flight.
- A post-commit hook that runs pre-flight (A1's later idea) is not built.

## 6. The tests

Pure core first, then the shell. The red-first demonstration (§ 5 "red first for `check`, `carry` and `release_gate`"): with `check` returning `(True, "stub")`, `carry_text` returning `"stub"` and `release_gate` returning `(True, "stub")` on a copy of the module, `test_preflight_stamp.py` gave **22 failed, 20 passed** (every `check`, `carry_text`, `carry`, `release_gate` test and the release-goes-on test failed); with the module restored, **42 passed**. The tests were written right after the module, not before it, so this red run stands in for "written first".

## 7. The runs of § 5

All on `main`, HEAD `01d3566` (release v0.1.9), with this step's files uncommitted. `release.py` was never run.

1. **Pre-flight, green** (`uv run --no-project python tooling/common/preflight.py`, in the background, 18:24–18:38). It printed "The working tree has uncommitted changes; the tests run on commit 01d3566 only." (the "clean copy: yes" path), ran `tooling\release-tests.bat` (the four suites: backend 3075, frontend 179, deps 42, tooling 172 passed; the browser tests at Full: 560 passed, 7 skipped, 567 in 346 s; "Release tests: all green."), and ended "Pre-flight passed for 01d3566. Stamped until 01-11-2026 18:38.", exit 0. `git notes --ref=preflight show HEAD` shows the stamp (`commit: 01d3566ba8bd…`, `tested_at: 2026-10-25T18:38:11+05:30`, `test_cmd: tooling\release-tests.bat`, `machine: KLA-SG25`, `by: KLA`, ten `summary:` lines). `scratch/release-tests/e2e/results.json` is there (§ 1.7). **The stamp stays on `01d3566`**: it is real.
2. **`gate "tooling\release-tests.bat"`**, tree dirty: "Tests passed in pre-flight on 25-10-2026 18:38 for 01d3566. The release does not run them again.", exit 0.
3. **`gate "tooling\run-tests.bat"`**: "The pre-flight stamp of 01d3566 was made with another test command. The tests run now.", exit 1.
4. **A second pre-flight during run 1**: "Another pre-flight is running. Wait for it to finish.", exit 2. Also during run 1, `preflight_stamp.preflight_running()` answered `True` (the release would abort).
5. **A red run**, `TEST_CMD=cmd /c exit 1` for that one command (D9): "Pre-flight failed for 01d3566: the test command exited 1. No stamp.", exit 1. No note was written: `refs/notes/preflight` still holds the one note of run 1, unchanged (`tested_at` 18:38:11).
6. **The carry** on throw-away commit objects made with `git commit-tree` on no branch: parent `912aa2b` (HEAD's tree, child of HEAD), child `518050d` changing only `VERSION`, child `c71c872` changing `VERSION` and `pyproject.toml`. `write` on the parent; `carry(518050d)` → "The pre-flight stamp of 912aa2b is carried to the release commit 518050d."; its note has `commit: 518050d…`, `carried_from: 912aa2b…` and the parent's `tested_at`, and `check` calls it valid. `carry(c71c872)` → nothing; no note. Both notes removed afterwards (`git notes --ref=preflight remove`); only run 1's note is left. The throw-away objects are unreachable and go with the next `git gc`.

Seen in the runs, for the reviewer and KLA:
- The stamp's ten `summary:` lines are the last ten non-empty output lines, so for Yantra they are mostly Playwright progress lines and the report path, not the suite lines. They do no harm (nothing reads them); a filter would need repo knowledge the generic code does not have.
- Run 5 overwrote run 1's log `scratch/preflight/01d3566.log` (same sha). Run 1's output is kept in `scratch/s049-run1.out`.
- A red run leaves an earlier green stamp of the same sha in place. With the same test command that would mean a flaky suite passed once and failed once; the release would still skip. The brief does not say to remove a stamp on red, so I did not build it. **For KLA:** should a red pre-flight remove the commit's stamp? Recommended: yes (one `git notes remove` on red), as a small amendment.

## 8. The unit suites

`YANTRA_TEST_RUN=s049c1 tooling/run-tests.bat`, once at the end: **ALL SUITES: PASSED** — backend 3075 passed (108 s), frontend 179 passed (13 s), deps 42 passed (1 s), tooling 240 passed (8 s): 172 before, the 63 new, and 5 in `tooling/tests/test_step_feedback.py`, another session's uncommitted file. No frontend code changed, so no `vite build`; no screen or API changed, so no e2e run beyond the one inside run 1.

## Manual checks

- [ ] **important** — Run `/pre-flight` (or the **Pre-flight** run config) before the next release; then **Release patch**: its console shows "Tests passed in pre-flight …" and goes straight to the version bump.

### How KLA tests it before copying it to smtw-common

1. Commit S049 (the new HEAD has no stamp).
2. In PyCharm, run the **Pre-flight** run config (A1). Expect about 8–10 minutes of test output, then "Pre-flight passed for <sha>. Stamped until <date time>." Or say `/pre-flight` in Claude Code.
3. In a terminal in the repo root: `git notes --ref=preflight show HEAD`. Expect the stamp, with `commit:` your HEAD and `machine:` this computer.
4. `uv run --no-project python tooling/common/preflight_stamp.py gate "tooling\release-tests.bat"`. Expect "Tests passed in pre-flight on … for <sha>. The release does not run them again."
5. `uv run --no-project python tooling/common/preflight_stamp.py gate "tooling\run-tests.bat"`. Expect "… was made with another test command. The tests run now."
6. Start **Pre-flight** again. While it runs, in a terminal in the repo root: `uv run --no-project python -c "import sys; sys.path.insert(0, 'tooling/common'); import preflight_stamp as p; print(p.preflight_running())"`. Expect `True`. Run the same line after the pre-flight ends; expect `False`. This check is read-only. Do **not** start **Release patch** to test the abort: when the pre-flight has already ended, the release finds the stamp and goes on to bump, tag, build, deploy and push (CR1-01). The abort itself is covered by `test_release_aborts_while_a_preflight_runs`.
7. Run **Release patch** in the window. Expect "Tests passed in pre-flight …", no test output, the version bump, and "The pre-flight stamp of <sha> is carried to the release commit <sha>." (the manual check above).

## Docs updated

- `.claude/CLAUDE.md`: the new `## Pre-flight` section (Yantra's five settings, the strict known-fault mark of Q3); the *Pre-flight (S049)* bullet after § Release (the stamp, the 7 days, the abort while a pre-flight runs, the carry, the `gate` CLI, the departure from `SMTW-WebApp-Base.md`, the "until the lift, a sync restores the old `release.py`" line, the run config).
- `docs/steps/README.md`: only the S049 row's status. The S048 queue row was already done by the planner.
- No schema, `Plan.MD`, domain doc, secret or `device-checks.md` row is due: no migration, no app code, and the manual check runs on KLA's laptop, not a phone.
- `SMTW-WebApp-Base.md` and `CLAUDE-COMMON.md` are synced files: not edited here; their text is below for the lift.

## Lift to smtw-common

**Files** (copy each to the same path in `smtw-common`):
- `.claude/skills/pre-flight/SKILL.md` (the `.claude/skills` folder syncs whole; no entry needed)
- `tooling/common/preflight_stamp.py`
- `tooling/common/preflight.py`
- `tooling/common/release.py`
- the tests `tooling/tests/test_preflight_stamp.py` and `tooling/tests/test_preflight.py`, if smtw-common keeps tests (they add `tooling/common` to `sys.path` themselves)

In `smtw-common`'s `tooling/common/sync_common.py`, add to `FILES`:

```python
    ("tooling/common/preflight_stamp.py", "tooling/common/preflight_stamp.py"),
    ("tooling/common/preflight.py", "tooling/common/preflight.py"),
```

**`CLAUDE-COMMON.md` § Release workflow**, step 2, replace with:

> 2. Run `TEST_CMD`, unless HEAD carries a valid pre-flight stamp (`/pre-flight`, `tooling/common/preflight_stamp.py`): the tests passed on this exact commit, on this machine, with this `TEST_CMD`, within 7 days. The full suite must be 100% green. The frontend build must also complete with no new errors (pre-existing chunk-size warnings are acceptable).

and add under its rules:

> - Run `/pre-flight` before the maintenance window, so a failing test is found before the users stop work. The skill needs a `## Pre-flight` section in the repo's `CLAUDE.md`; the release's gate is on everywhere and does nothing where no stamp exists.

**`SMTW-WebApp-Base.md` § Pre-flight Before Every Release**, replace "Pre-flight is automated by `release.py` — it runs the test suite and aborts on failure before bumping or tagging." with:

> Pre-flight runs in two stages. **Before the maintenance window**, `/pre-flight` (`tooling/common/preflight.py`, or a run config that sets the Release run configs' `TEST_CMD`) runs the release's tests on HEAD; a green run stamps that commit with a git note (`refs/notes/preflight`, not pushed), and a red run gives one bug report per failure and asks what to do (fix the code, fix the test, mark as a known fault, investigate). **In the window**, `release.py` skips `TEST_CMD` when HEAD carries a valid stamp (this exact commit, this machine, this `TEST_CMD`, at most 7 days old); otherwise it runs the tests and aborts on failure before bumping or tagging, as before, and stamps a green run. The release commit (only `VERSION` changed) carries the stamp, so a retry after a failed build or deploy does not test again. A release started while a pre-flight runs aborts before anything changes. The repo's settings are a `## Pre-flight` section in its `CLAUDE.md`: *Test command*, *Tests a clean copy of HEAD* (`yes` | `no`), *Failure logs*, *Re-run failing tests*, *Known fault*.

After the lift, Yantra's `.claude/CLAUDE.md` *Pre-flight (S049)* bullet can drop its "departs from the base" and "until that lift" sentences.

## Amendment A1 — deterministic, runnable from PyCharm

1. **The environment first.** `preflight.read_settings(text, environ)`: the test command is `TEST_CMD` when set and not empty (blank counts as unset), else the section's *Test command*; "clean copy" is `PREFLIGHT_CLEAN_COPY` (`yes` | `no`) when set, else the section's line, else `no`. With `TEST_CMD` set, the section may be missing.
2. **The run config** `.idea/runConfigurations/Pre_flight.xml` (gitignored): the shape of `Release__patch_.xml`, name "Pre-flight", `SCRIPT_NAME` `$PROJECT_DIR$/tooling/common/preflight.py`, no parameters, working folder `$PROJECT_DIR$`, env `PYTHONUNBUFFERED=1` and `TEST_CMD=tooling\release-tests.bat` only (no build or deploy settings). PyCharm runs it with the project interpreter; `preflight.py` is stdlib-only and finds `preflight_stamp` beside it.
3. **No input.** `preflight.py` asks nothing; the test command gets stdin from `DEVNULL`, so a command that reads input gets end-of-file and cannot wait (a later post-commit hook can run it unattended).
4. **Tests** (`test_preflight.py`): `TEST_CMD` set wins over the section; unset uses the section; empty and blank count as unset; set with no section; `PREFLIGHT_CLEAN_COPY` set, set with no section, and empty; and `run_tests` with a command that reads stdin gets `''` and ends.

## Feedback

Added in fix round 1 (CR1-08), from what this report records of the first run and A1:

- hindrance: A1 item 2 of the brief reached the coder with the `\r` of `\release` turned into a line break, so the run config's value had to be rebuilt from the Release run configs (`1-brief.md:406`, D14).
- waste: run 5 (red) overwrote run 1's log `scratch/preflight/01d3566.log`, because the log is named by the short sha only; run 1's output had to be saved by hand (`scratch/s049-run1.out`).
- idea: § 5's runs need a way to test a red pre-flight without touching HEAD's real stamp (since A2 a red run removes it); an option to run on a given sha would make that safe.

## Fix rounds

### Round 1 (code review r1)

All eight findings are fixed; A2 (approved by KLA, 25-10-2026) is built in the same round (§ Amendment A2 below). Tooling suite: **PASSED, 258 passed** (`YANTRA_TEST_RUN=s049c2 tooling/run-tooling-tests.bat`; 240 before, 18 new). The backend and frontend suites were not run: no change reaches `backend/` or `frontend/`. No e2e run: no screen or API changed.

**Red, then green.** The 18 new tests were written first and run on the old code: 28 failed (the 18, plus the `World` and release tests that now stub `remove` / `release_lock`, which did not exist then). Then, for each fix with a test, the fix was undone in place, its tests run alone, the exact bytes restored (checked equal), and the tests run again (script: `C:\Users\KLA\AppData\Local\Temp\claude\C--Users-KLA-PycharmProjects-Yantra\4cb08d41-5654-498e-a3ec-a8406a3f2557\scratchpad\red_green.py`). The results are in each answer.

- **CR1-01** (minor) — **Fixed.** KLA's test step 6 no longer starts a release. It runs the read-only `preflight_running()` line while a pre-flight runs (expect `True`) and after it ends (expect `False`), and says why the release must not be started to test the abort. No code change, so no red run.
- **CR1-02** (minor) — **Fixed**, as A2 item 2. `release.py` gains `run_tests(test_cmd)`: it runs `TEST_CMD` inside `preflight_stamp.release_lock()`. Lock got → the tests run with it held. A pre-flight holds it → the step-0 abort (the same text, now the constant `PREFLIGHT_RUNNING`). A lock error → "WARNING: the pre-flight lock could not be taken: <error>. The tests run without it." and the tests run. `release_lock()` never raises an error of its own; an abort or an error of the test run passes through, and the lock is given back. Tests: `test_release_holds_the_preflight_lock_while_its_tests_run`, `test_release_aborts_when_a_preflight_takes_the_lock_first`, `test_release_runs_its_tests_when_the_lock_cannot_be_taken`; `release_lock` itself in `test_release_lock_is_held_inside_and_refuses_a_preflight` (a second process gets `False` while the release holds it), `test_release_lock_while_a_preflight_holds_it`, `test_release_lock_never_raises`; the real-module test `test_release_goes_on_when_every_stamp_function_meets_a_git_error` now also checks the lock warning; `test_release_red_tests_still_abort` checks the lock is given back on the abort. Fails without the fix (`run_tests` reduced to `return run(test_cmd)`): 3 failed (`assert False is True` on `locked_during_tests`; `DID NOT RAISE SystemExit`; the warning missing); passes with it: 3 passed. `release_lock` without the lock (`got, error = True, None`): 3 failed; with it: 3 passed. `preflight.py`'s refusal keeps A2's words "Another pre-flight is running. Wait for it to finish." (the reviewer proposed "Another pre-flight or a release is running its tests."); the skill's row names both cases.
- **CR1-03** (minor) — **Fixed.** With "clean copy: no", `run_locked` calls `ps.tree_clean()` again after the run, after the red check. Dirty → "The working tree changed during pre-flight, so the tests did not run on commit abc1234 alone. No stamp. Run pre-flight again.", exit 1, no stamp. The skill has a row for it. Tests: `test_tree_changed_during_the_run_when_the_command_tests_the_working_folder` (`tree_clean` answers clean, then dirty) and `test_tree_still_clean_after_the_run_stamps`. Fails without the fix: `assert 0 == 1` (it stamped and exited 0); passes with it. The gap the reviewer names (an edit made and reverted within the run) stays, as accepted.
- **CR1-04** (nit) — **Fixed.** `check` answers not valid when `tested_at` is more than `CLOCK_SKEW` = **5 minutes** after now: "The pre-flight stamp of abc1234 is dated later than now; this computer's clock may have been wrong. The tests run now." Five minutes covers the drift between two clock syncs and is far below the days a wrong clock could add. Tests: `test_check_a_stamp_from_the_future_is_not_valid` (6 minutes ahead) and `test_check_tolerates_a_small_clock_skew` (4 minutes ahead). Fails without the fix: `assert (True, 'Tests… them again.') == (False, …)`; passes with it.
- **CR1-05** (nit) — **Fixed.** `preflight.main` catches `OSError` around the lock and the run: "Pre-flight stopped because of a file or system error: <error>. No stamp.", exit 2, no traceback. The skill has a row for it (report the line; no bug report, no re-run). Test: `test_an_os_error_ends_in_one_line_and_exit_2` (`run_tests` raises `PermissionError`). Fails without the fix: the `PermissionError` escapes; passes with it.
- **CR1-06** (nit) — **Fixed.** The skill's re-run step says that above `RERUN_MAX` each failure counts as steady and gets the four options of step 5. Text only.
- **CR1-07** (nit) — **Fixed.** The comment in `preflight_stamp.py` reads "A deliberate copy of the repo-specific e2e lock code (S049 BR2-07): generic code cannot import a repo's file." In Yantra the source of the copy is `tooling/e2e/run_lanes.py` (`main_scratch`, `one_run_at_a_time`).
- **CR1-08** (nit) — **Fixed.** The report has its `## Feedback` above, for the first run and A1; this round and A2 have their own below.

**Decisions taken in this round:**
- **D15** The future-stamp line is its own reason, not "cannot be read" (the reviewer's words): it says what happened and the likely cause (scope B).
- **D16** In `run_locked` the order after the run is: HEAD moved → red (with the removal) → tree changed → write. A red run on a changed tree still removes the stamp: the safe direction.
- **D17** `release_lock()` yields `(got, error)`, so `release.py` can tell "a pre-flight holds it" from "the lock code failed". When unlocking fails at the end, the error is dropped, with a comment: `held_lock` closes the file anyway, and closing frees the lock.
- **D18** The abort text is one constant `PREFLIGHT_RUNNING` in `release.py`, used by step 0 and by `run_tests`, so the two cannot drift.
- **D19** `_git_message(result)` is shared by `_add_note` and `remove`, instead of a second copy of the line.

**Checks.** `release.py` keeps CRLF (no bare LF), and `git diff -w` shows only S049's lines: the docstring, the guarded import, `PREFLIGHT_RUNNING` and `run_tests`, step 2, and the carry. `release.py` was never run. `preflight.py` was not run with any command: its red path would now remove the real stamp on `01d3566`. `remove` was tried on real git with a throw-away `git commit-tree` object (`88e2858`, on no branch): `write` → a stamp; `remove` → `(True, None)`; `read` → `None`; `remove` again → `(False, None)`. `git notes --ref=preflight list` holds only the note on `01d3566` before and after, and `check` on it still says "Tests passed in pre-flight on 25-10-2026 18:38 for 01d3566."

**Docs updated in this round:**
- `.claude/CLAUDE.md`, the *Pre-flight (S049)* bullet: the 5-minute `CLOCK_SKEW`; a red pre-flight removes the commit's stamp; the release holds the pre-flight lock while `TEST_CMD` runs.
- `.claude/skills/pre-flight/SKILL.md`: the rows for the tree changed, the file or system error, and the red line's removal; the re-run cap.
- No schema, `Plan.MD`, domain doc, secret, Keycloak or `device-checks.md` change is due: no migration, no app code, no device check.

#### Feedback

- hindrance: a Python heredoc with an apostrophe inside (`this computer's`) broke the Bash tool's quoting ("unexpected EOF"), so the patch had to go through a script file (1 run lost).
- hindrance: the red-green script crashed printing pytest's `\ufffd` on the cp1252 console; it needed `PYTHONIOENCODING=utf-8` and a second run (1 min).
- hindrance: the Write tool refused a scratchpad file holding this report's text ("Subagents should return findings as text"), so the sections went in with Edit instead (1 call lost).
- idea: a `tooling/red-green.bat <file> <old> <new> <tests>` wrapper would make the standing "undo the fix, run red, restore" rule one command that also checks the restore.

## Amendment A2 — a red run removes the stamp; the release holds the lock

1. **A red run removes the stamp.** `preflight_stamp.remove(sha)` reads the note (to know whether one was there), then runs `git notes --ref=preflight remove --ignore-missing <sha>`, whatever the note's test command. It returns `(removed, error)` and never raises. `preflight.report_red(sha, code)` calls it and prints the red line last: "Pre-flight failed for abc1234: the test command exited 1. No stamp. Its earlier stamp is removed." when there was one. A failed removal prints, before the red line, "The earlier pre-flight stamp of abc1234 could not be removed: <git's message>. Remove it with: git notes --ref=preflight remove abc1234"; the exit stays 1. "HEAD moved" removes nothing. Tests: `test_red_run` (tried, nothing there), `test_red_run_removes_the_earlier_stamp`, `test_red_run_when_the_stamp_cannot_be_removed`, `test_head_moved_removes_nothing`; `remove` with git stubbed: `test_remove_takes_the_stamp_off`, `test_remove_when_there_is_no_stamp`, `test_remove_returns_gits_message`, `test_remove_never_raises`; and on real git (Round 1, Checks). Fails without the fix (`removed, error = False, None` in place of the call): 3 failed (the line lacks "Its earlier stamp is removed.", the warning line is missing, `remove` was not called); passes with it: 3 passed. This closes the open question of § 7 ("A red run leaves an earlier green stamp of the same sha in place").
2. **The release holds the lock** around its own `TEST_CMD` run: CR1-02 above.
3. **Tests**: as listed in items 1 and 2.

**Decisions taken:** D16–D19 above. "Its earlier stamp is removed." is A2's wording. The warning line for a failed removal is mine (A2 says only "prints git's message"); it names the command, because the release would otherwise skip its tests on that stamp.

#### Feedback

- none

### Round 2 (code review r2, async)

All three findings (nits) are fixed. Tooling suite: see the count below.

- **CR2-01** (nit) -- **Fixed.** The skill's row "The working tree changed during pre-flight" now gives the advice: a test command that leaves files outside `.gitignore` -> add them to `.gitignore`, or set "Tests a clean copy of HEAD" to `yes` only if the command really tests a clean copy. Text only, no red run.
- **CR2-02** (nit) -- **Fixed.** `preflight.run_tests` wraps the read loop and `wait()` in `try/finally`; the `finally` kills the process (and waits for it) when `poll()` shows it still runs, so no test command outlives `preflight.py`. Test: `test_run_tests_kills_the_command_when_the_run_fails` (a stub process whose output raises `OSError`; expects `kill` then `wait` and the error to pass through). Fails without the fix: `assert [] == ['kill', 'wait']`; passes with it. (`Popen.kill` ends the shell on Windows; a child of the shell may need `taskkill /T`; not added, since the usual cause is a closed pipe, which ends the child too.)
- **CR2-03** (nit) -- **Fixed.** The warning reads "Any earlier pre-flight stamp of abc1234 could not be removed: <git's message>. Remove it with: ..." . `test_red_run_when_the_stamp_cannot_be_removed` expects the new words; it fails on the old text (`assert 'The earlier ...' == 'Any earlier ...'`) and passes with the change.

Docs updated: `.claude/skills/pre-flight/SKILL.md` (CR2-01). None else due: no migration, app code, secret, Keycloak or device check. Files keep CRLF. `release.py` and `preflight.py` were not run.

#### Feedback

- none

- **Verified by the orchestrator** (25-10-2026): `test_run_tests_kills_the_command_when_the_run_fails` run against the snapshot's earlier `preflight.py` (`refs/steps/S049` d2c2a77) fails with `assert [] == ['kill', 'wait']`, the red result this round claims.
