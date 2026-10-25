```
Step: S049 — Pre-flight before a release
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S049 — code review, round 1 (with amendment A1)

**Verdict: no `blocker` or `major` finding is open.** Three `minor` findings and five nits. The
gate cannot skip `TEST_CMD` on untested code in Yantra as it is set up. One generic path can skip
it (CR1-03, "clean copy: no" only). One race can make a release fail in the window (CR1-02). One of
KLA's test steps can start a real release (CR1-01).

**Tests run by the reviewer:**
- `YANTRA_TEST_RUN=s049cr1 tooling/run-tooling-tests.bat`: **PASSED**, 240 passed in 8 s (this
  includes the 63 new tests and the 5 of `test_step_feedback.py`, another change).
- Not run: the backend and frontend suites, `vite build`, the e2e specs. No app code, frontend
  file or API changed; `release-tests.bat` gains one `robocopy` line that only the release runs.
  No browser spec is due (the spec-to-step map names none for tooling).
- Read-only checks: `preflight_stamp.py gate "tooling\release-tests.bat"` gives "Tests passed in
  pre-flight on 25-10-2026 18:38 for 01d3566. …", exit 0. The same command with a trailing space
  gives "… made with another test command …", exit 1 (exact equality holds). `git notes
  --ref=preflight list` holds only run 1's note on `01d3566`. The note is stored with LF line ends.
  `notes.rewriteRef` is not set. `.idea/runConfigurations/Pre_flight.xml` is gitignored and has the
  shape of `Release__patch_.xml`, with `TEST_CMD=tooling\release-tests.bat`.

## Findings

### CR1-01 (minor) — KLA's test step 6 can start a real release

`docs/steps/S049-pre-flight/3-impl-report.md:137`

**Problem.** Step 6 says: start **Pre-flight**, and while it runs, start **Release patch**. The
release stops only if the pre-flight still holds its lock at that moment.

**Failure scenario.** The pre-flight ends (or fails early, for example on a refusal) before KLA
clicks **Release patch**. HEAD carries the stamp from step 2, so the release skips its tests. It
then bumps, tags, builds, deploys and pushes, outside a maintenance window.

**Fix.** Replace step 6 with a read-only check while the pre-flight runs:
`uv run --no-project python -c "import sys; sys.path.insert(0, 'tooling/common'); import preflight_stamp as p; print(p.preflight_running())"`.
Expect `True` while it runs and `False` after it ends. The release's abort itself is covered by
`test_release_aborts_while_a_preflight_runs`.

### CR1-02 (minor) — a pre-flight started during a release's test run removes the release's worktree

`tooling/common/release.py:106-122`, `tooling/common/preflight.py:148`

**Problem.** `release.py` checks the pre-flight lock once, before step 2. It does not hold the
lock while `TEST_CMD` runs. So a pre-flight started after that check runs `release-tests.bat`
too, and its `:remove_worktree` removes `%TEMP%\yantra-release-tests` while the release uses it.
The brief (BR2-04) covers only the other order: a release started during a pre-flight.

**Failure scenario.** In the maintenance window HEAD has no stamp, so Release patch runs its
tests. During that run, KLA clicks the **Pre-flight** run config, or A1's later post-commit hook
starts one. The release's worktree goes, its suites fail, and the release aborts "Tests failed."
with the users waiting. This direction fails the release. It never skips tests.

**Fix.** In `release.py`, hold `preflight_stamp.held_lock(preflight_stamp.lock_path())` around
`run(test_cmd)`. When the lock is not got, abort with the existing line. In `preflight.py`, make
the refusal "Another pre-flight or a release is running its tests. Wait for it to finish." Add one
test. The release must keep running when the lock code raises (§ 1.5): treat an error as "got the
lock". This changes the approved design a little, so KLA may decide it at gate B.

### CR1-03 (minor) — with "clean copy: no", the tree can change during the run and the stamp still goes on HEAD

`tooling/common/preflight.py:171-181`

**Problem.** When "Tests a clean copy of HEAD" is `no`, the dirty-tree refusal runs only before
the test command. Nothing checks the tree after the run. The "HEAD moved" check sees new commits
only. Yantra says `yes`, so Yantra cannot reach this path. Every repo with a plain `pytest` can
reach it after the lift.

**Failure scenario.** A repo's test command is `pytest`. KLA starts pre-flight on a clean tree. He
then edits a file to try a fix, the tests pass with the edit, and he reverts the edit
(`git checkout -- file`). HEAD is stamped, but the tests never ran on HEAD as committed. The
release then skips `TEST_CMD` for that commit.

**Fix.** When `clean_copy` is false, call `ps.tree_clean()` again after the run. If the tree is
dirty, print "The working tree changed during pre-flight, so the tests did not run on commit
abc1234 alone. No stamp. Run pre-flight again.", exit 1, and add a row to the skill's table. Add one
test with `World(clean_copy=False)` and a `tree_clean` stub that answers clean, then dirty. The
check misses an edit made and reverted within the run. That gap is accepted, as for "HEAD moved"
(BR2-18).

## Nits

- **CR1-04** (nit) `tooling/common/preflight_stamp.py:134`: a `tested_at` in the future is valid
  until 7 days past that future time (D6). A clock that was wrong at stamp time then extends the
  stamp. Answer "cannot be read" when `tested_at` is more than a few minutes after `now`. This is
  the safe direction.
- **CR1-05** (nit) `tooling/common/preflight.py:148,171`: an unexpected `OSError` ends in a
  traceback with exit 1. Examples: `scratch/` cannot be written, or `Popen` fails. The skill's
  table has no row for that, and § 1.4 calls "not run" exit 2. Catch `OSError` around the lock and
  the run, print one line, and exit 2. Or add a skill row: "anything else: report the last lines,
  no bug report".
- **CR1-06** (nit) `.claude/skills/pre-flight/SKILL.md:77`: above `RERUN_MAX` the skill re-runs
  nothing, but it does not say what follows. Say that each failure then counts as steady and gets
  the four options.
- **CR1-07** (nit) `tooling/common/preflight_stamp.py:279-280`: the generic file names Yantra and
  `tooling/e2e/run_lanes.py` in a comment. Write "a deliberate copy of the repo-specific e2e lock
  code (S049 BR2-07)", and keep the file path in the impl report.
- **CR1-08** (nit) `docs/steps/S049-pre-flight/3-impl-report.md`: the report has no closing
  `## Feedback` section. `.claude/agents/coder.md:163` asks for one. Add it in the fix round.

## Answers to the orchestrator's points

**Every path where `release.py` could skip `TEST_CMD` on untested code:**

| Path | Result |
|---|---|
| The sha | `preflight.py` reads it once (`:161`) and stamps only that sha (`:181`). A later HEAD gives "HEAD moved", exit 1. `release.py` stamps the sha it read before `run()`. **Holds.** |
| `test_cmd` | Exact string equality (`:139`); `parse` strips the stored value. A different or padded `TEST_CMD` always means the tests run (the safe direction). `TEST_CMD=skip` never writes and never carries. **Holds.** |
| The machine | `platform.node()` on both sides. **Holds.** |
| The 168 h boundary | `now - tested_at > 7 days`, tested one minute either side. Exactly 168 h is valid. **Holds.** The only gap is a future `tested_at` (CR1-04). |
| The carried stamp | `sorted(changed) == ["VERSION"]`, plus `check` on the parent's note against the parent sha, the release's `TEST_CMD`, this machine and now. The carried stamp keeps the parent's `tested_at`. A `POST_BUMP_SCRIPT` that adds files means no carry. **Holds.** |
| `-B` | Pre-flight stamps only on `main`. The release's own stamp on another branch follows a green run of that exact sha. **Holds.** |
| An amended or rebased commit | A new sha has no note. If a user sets `notes.rewriteRef`, the copied note names the old sha, and `check` answers "names another commit". **Holds.** |
| The tree | `release.py` refuses a dirty tree (step 1). Pre-flight relies on "clean copy". With `yes`, Yantra's worktree tests HEAD. With `no`, see CR1-03. |

**No error in the gate fails a release.** The import is guarded with `ImportError`; the test
covers it through `sys.modules[...] = None`. `release_gate`, `write`, `carry`, `head_sha` and
`preflight_running` each catch `Exception`. `read` and `main_scratch` catch only `OSError`, but
they are called only inside functions that catch everything. The test
`test_release_goes_on_when_every_stamp_function_meets_a_git_error` runs the real module with git
raising, and the release completes. A lock error in `preflight_running` answers `False`.

**`release.py`'s remainder is unchanged.** `git diff -w` shows only the docstring lines, the
guarded import, step 2 and the carry after the commit in step 4. The four removed lines are the
re-indented test run and the old step-2 heading. CRLF is kept (`file`: CRLF; the stat is 34+/4−,
not a whole-file change).

**`preflight.py`:**
- The settings reader takes `TEST_CMD` from the environment first, and treats an empty or blank
  value as unset. Otherwise it reads the section, from the heading to the next `## `, with the
  backticks stripped. `PREFLIGHT_CLEAN_COPY` comes first in the same way. A missing value is `no`.
- The lock is taken once, with no waiting, and exits 2 when it is held.
- HEAD moved gives exit 1. The exit codes match § 1.4, except for CR1-05.
- `stdin` is `DEVNULL`, and the script never asks a question. The test
  `test_run_tests_never_waits_for_input` proves it.

**The skill against § 1.6.** These match: the settings stop line, the step-check and step-ls
information, the background run, and the table of outcomes by last line. The bug report has the
ISTQB shape. The re-run is once, one run per suite, capped at 10, with the uncommitted-changes
note. The flaky-only case has its three options. Steady failures get four options, up to four
questions at a time. The repo without `/step` and the closing line also match. The known-fault
convention in `.claude/CLAUDE.md` § Pre-flight is strict, as KLA chose at Q3 (`test.fail(true,
"S0NN: …")`, `xfail(strict=True)`, `it.fails`). Only CR1-06 is open.

**Genericity.** `preflight.py`, `preflight_stamp.py` and `SKILL.md` name no Yantra file, port or
tool, except the comment of CR1-07. `S049` appears only as a reference in docstrings.

**The lift section and KLA's test steps.** The file list, the `FILES` entries and the § 1.9 texts
are ready to paste. KLA's steps 1–5 and 7 are right. Step 6: CR1-01.

**Departures:**
- **D3** (`carry_text` takes `check`'s inputs): agreed. A valid parent stamp needs them, and the
  core stays pure.
- **D4** (`write` returns git's message): agreed. § 1.4's line must name the message.
- **D8** (the running check before the `skip` branch): agreed. It is still before any test or
  bump, and it protects the worktree in the `skip` case too.
- **D9** (run 5 through the environment): agreed. The section path of the reader is covered by
  unit tests.
- **D14** (the brief's broken `\r`, `1-brief.md:406`): the run config has the right value. The
  planner should fix the brief's text.

**The coder's open question: should a red pre-flight remove an existing stamp on the same
commit?** Recommendation: **yes**, as a small amendment for KLA at gate B.
- Reason: the latest evidence should decide (ISO 9001 § 8.6: release when the planned checks
  *show* the requirements are met). A commit that passed once and then failed is flaky. Today the
  release would still skip its tests on the old pass.
- Remove the stamp on any red run of that sha, whatever its test command. That is the safe
  direction (at worst the release tests again) and the simplest rule.
- The red line then adds "The earlier stamp of abc1234 was removed." A failed removal prints a
  warning; the exit code stays 1.
- "HEAD moved" concerns another sha, so it removes nothing.

## Manual checks

The impl report's `## Manual checks` holds the brief's one important check as an unticked box.
That is correct: it needs KLA's real release. It is not a device check, so it needs no
`device-checks.md` row.

For KLA, in the browser or on the laptop:
- [ ] **important** — Run `/pre-flight` or the **Pre-flight** run config, then **Release patch**
  in the window. The console shows "Tests passed in pre-flight …", goes straight to the version
  bump, and prints "The pre-flight stamp of … is carried to the release commit …".

## Checked and found consistent

- The stamp format, `parse` and `check`, in the order of § 1.3, with the reasons ending "The
  tests run now.". Times show as DD-MM-YYYY HH:MM IST.
- The note is written with `-F` through a temporary file that is then removed. `read` returns
  `None` on "no note".
- The lock code copies `run_lanes`, changed to try once (D11). `preflight_running` creates no
  file when none exists.
- The gate CLI changes nothing.
- `release-tests.bat` copies `results.json` into `scratch\release-tests\e2e\`, and its comment
  item 5 is updated.
- The tests cover § 3's list: every `check` rule, `carry_text` with `["VERSION"]`, two files,
  none, and invalid parents; `release_gate`, `write`, `carry` and `preflight_running` with git
  stubbed or raising; the reader with A1's environment; the refusals for both values of "clean
  copy"; the lock held in a second process; HEAD moved; red; the failed write; the tee; no input.
  The release's steps 2 and 4 are tested with `run` faked. The red-first demonstration is recorded
  (22 failed with the core stubbed).
- `.claude/CLAUDE.md`: the `## Pre-flight` section and the *Pre-flight (S049)* bullet match the
  code, including the departure from the base and the sync caveat. No schema, Plan.MD, secret or
  Keycloak doc is due.
- Scope: nothing is built beyond the brief and A1. The post-commit hook is not built, as A1 says.

## Feedback

- waste: `cmd //c tooling\\run-tooling-tests.bat` lost its backslash in Git Bash; `./tooling/run-tooling-tests.bat` worked (1 run lost).
- idea: the `gate` CLI could also print `preflight_running()`, so a check like CR1-01's needs no Python one-liner (`preflight_stamp.py:352`).
