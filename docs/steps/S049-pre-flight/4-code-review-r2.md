```
Step: S049 — Pre-flight before a release
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S049 — code review, round 2 (verify fix round 1 and amendment A2)

**Verdict: no `blocker` or `major` finding is open.** All eight findings of round 1 are fixed, and
A2 items 1–2 are built as approved. The fix round's own diff brings in no new fault that can make a
release skip `TEST_CMD` on untested code, or fail a release through the gate's own error. Three new
nits (CR2-01…CR2-03) remain. Each is small and lies outside the release path.

**Read from the snapshot** `refs/steps/S049` = `d2c2a77` (parent `01d3566`): the fix round and
A2 sections of `3-impl-report.md`, brief § 1.4, § 1.5 and § 7 (A1, A2), and in full
`tooling/common/release.py`, `tooling/common/preflight_stamp.py`, `tooling/common/preflight.py`,
`.claude/skills/pre-flight/SKILL.md`, the *Pre-flight (S049)* bullet of `.claude/CLAUDE.md`, and
the new and changed tests in `tooling/tests/test_preflight.py` and
`tooling/tests/test_preflight_stamp.py`. I re-read nothing else of the step.

**Tests run by the reviewer:**
- `YANTRA_TEST_RUN=s049cr2 uv run --no-project python -m pytest tooling/tests/test_preflight.py
  tooling/tests/test_preflight_stamp.py -q`, on a temporary worktree of `refs/steps/S049`:
  **81 passed** in 0.9 s (63 from round 1, plus 18 new). The worktree is removed.
- A read-only probe of the real `release_lock()` (a scratch lock file, not the repo's) checks the
  lock's state inside the block, during a `SystemExit`, and after it. Inside the block, a second
  process gets `False`. The `SystemExit` passes through with its code. After it, a second process
  gets `True`, so the lock is given back. This covers what `test_release_red_tests_still_abort`
  checks only on the fake lock.
- Not run, as the orchestrator's brief for this round says: `tooling/run-tests.bat`,
  `release.py` and `preflight.py`. The coder's tooling suite shows 258 passed. No backend,
  frontend or screen file changed, so no e2e spec is due.
- `git notes --ref=preflight list` holds only the note on `01d3566`, before and after this review.

## Round 1 findings

| ID | Severity | Status | Verified by |
|---|---|---|---|
| CR1-01 | minor | **Fixed** | Step 6 of *How KLA tests it* runs only the read-only `preflight_running()` line and says why not to start **Release patch**. |
| CR1-02 | minor | **Fixed** (A2 item 2) | `release.py:80-90` `run_tests`; `preflight_stamp.py:340-360` `release_lock`. See the focus points below. |
| CR1-03 | minor | **Fixed** | `preflight.py:200-204`; tests `…tree_changed_during_the_run…`, `…tree_still_clean_after_the_run_stamps`; skill row `SKILL.md:56`. |
| CR1-04 | nit | **Fixed** | `preflight_stamp.py:39,139-141`; tests at 6 minutes (refused) and 4 minutes (valid). |
| CR1-05 | nit | **Fixed** | `preflight.py:164-172`; test `test_an_os_error_ends_in_one_line_and_exit_2`; skill row `SKILL.md:58`. See CR2-02. |
| CR1-06 | nit | **Fixed** | `SKILL.md:79-81`. |
| CR1-07 | nit | **Fixed** | `preflight_stamp.py:303-304` names no repo file. |
| CR1-08 | nit | **Fixed** | The report has `## Feedback` for the first run and A1, and one per section after it. |

**Red, then green.** Each fixed fault that has a test comes with its red result: CR1-02 / A2
item 2 (3 failed, then 3 passed, for both `run_tests` and `release_lock`), CR1-03, CR1-04,
CR1-05 and A2 item 1 (3 failed, then 3 passed). For CR1-01, CR1-06, CR1-07 and CR1-08 the fix is
text only, so no red run is due.

## The focus points

**`run_tests()` and `release_lock()` (CR1-02, A2 item 2): correct.**
- **The lock is held during `TEST_CMD`.** `run(test_cmd)` runs inside `with
  preflight_stamp.release_lock()`. The probe and
  `test_release_lock_is_held_inside_and_refuses_a_preflight` show that a second process is refused
  then.
- **The lock code never stops the release with an error of its own.** `lock_path()`, `mkdir` and
  `open` go through `enter_context` inside `except Exception`. A failing `_lock` gives
  `(False, None)` from `held_lock`. A failed unlock at the end is caught in `stack.close()`. The
  real-module test `…every_stamp_function_meets_a_git_error` now also shows the warning "the
  pre-flight lock could not be taken: git exploded." and checks that the release completes.
- **An abort gives the lock back.** `abort()` raises `SystemExit`, a `BaseException`. That
  exception passes through `yield` in `release_lock`. Its `finally` closes the stack, and
  `held_lock` unlocks the file and closes it. The probe shows the lock free after the exit.
- **The lock is not passed on to the test command.** Python opens files as non-inheritable
  (PEP 446), so `release-tests.bat` and its children do not hold the lock. `msvcrt` and `flock`
  locks belong to the process that holds the handle.
- **One abort text.** `PREFLIGHT_RUNNING` (`release.py:76`) is used by step 0 (`:124`) and by
  `run_tests` (`:89`). The two can no longer drift apart (D18).
- **Both lock checks are needed.** `preflight_running()` at step 0 and the lock in `run_tests`
  both stay. A pre-flight can start between the gate's decision and `run_tests`. That case aborts
  before any test or bump, so nothing changes.
- **The release's other steps are unchanged.** `git diff -w --ignore-cr-at-eol 01d3566 d2c2a77`
  on `release.py` shows 48 lines added and 2 removed, all from S049. The committed blob has LF line
  ends, which is git's `autocrlf` normalisation.

**The red path and D16 (order after the run): correct.** The order is HEAD moved, then red with
the removal, then tree changed, then write.
- **HEAD moved** comes first and removes nothing, because the run concerns another commit
  (`test_head_moved_removes_nothing`).
- **Red** calls `ps.remove(sha)` on the sha read before the run, whatever the stamp's test
  command. The warning prints before the red line, so the red line stays last for the skill's
  table. The exit stays 1.
- **A red run on a changed tree** still removes the stamp. That is the safe direction: at worst
  the release tests again. I agree with D16.
- `remove()` reads the note first only to word the line. `--ignore-missing` makes "no note" a
  success, and every error is caught. Its four stub tests and the coder's real-git trial on a
  throw-away commit cover it.

**CR1-03, the tree check: correct, with one gap in the skill's advice (CR2-01).** The check runs
only when "clean copy" is `no`, so Yantra's `yes` path is unchanged. A failing `git status` counts
as dirty (`tree_clean` returns `False`), so the run gets no stamp: the safe side.

**CR1-04, the 5-minute skew: correct.** The rule is `tested_at - now > CLOCK_SKEW`. It runs after
the commit check and before the age check. Exactly 5 minutes ahead is still valid. A carried stamp
uses the same `check`, so it gets the same rule. Five minutes covers the drift between NTP syncs
and is far below the 7 days. I agree with D15: "is dated later than now; this computer's clock may
have been wrong" says what happened and why. "Cannot be read" would say neither.

**CR1-05, the `OSError` line: correct for what it catches.** It catches `OSError` around the lock
and `run_locked`. Exit code 2 and the line "Pre-flight stopped because of a file or system error:
<error>. No stamp." match § 1.4 "not run". A mid-run error leaves the test command running: see
CR2-02.

**D17 (`release_lock` yields `(got, error)`; a failed unlock is dropped): agreed.** The release
must tell a held lock (abort) from a broken lock (warn and test). The dropped unlock error has a
comment that gives the reason: `held_lock`'s outer `finally` still closes the handle, and closing
frees the lock. Windows's `LockFile` documentation says the release on close may come "a moment"
later. This matters only after an unlock has already failed, which is rare and harmless here.

**D19 (`_git_message` shared by `_add_note` and `remove`): agreed.** It removes a near-copy.

**The coder's wording of the failed-removal warning.** "The earlier pre-flight stamp of abc1234
could not be removed: <git's message>. Remove it with: git notes --ref=preflight remove abc1234"
follows scope B: what happened, why, and what to do. Naming the command is right, because the
release would otherwise skip its tests on that stamp. One case reads wrong: see CR2-03.

**`preflight.py`'s refusal while a release holds the lock.** It still says "Another pre-flight is
running. Wait for it to finish." That is A2 item 2's own wording, which KLA approved. The skill's
refusal row names both cases ("another pre-flight or a release running its tests"). No finding.

## Nits

- **CR2-01** (nit) `.claude/skills/pre-flight/SKILL.md:56`: in a repo whose test command leaves
  files in the tree that `.gitignore` does not cover (a coverage file, a report), every run with
  "clean copy: no" ends "The working tree changed…". "Run it again" then repeats the same result.
  Add to the row: "When nobody touched the tree, show `git status --porcelain`: the test command
  leaves those files; gitignore them."
- **CR2-02** (nit) `tooling/common/preflight.py:115-127`: when an `OSError` comes mid-run (for
  example, the log write fails on a full disk), `run_tests` leaves the `with` block without
  stopping or waiting for the test command. The lock is then free and the line says "No stamp"
  while the command may still run. Wrap the read loop in `try/finally` that calls
  `process.kill()` and `process.wait()` when the loop did not end normally.
- **CR2-03** (nit) `tooling/common/preflight.py:147-149`: `remove()` returns an error even when no
  stamp was there. This happens when git itself fails, and then `read` failed too. The line then
  says "The earlier pre-flight stamp … could not be removed", a stamp that may not exist. Write "Any
  earlier pre-flight stamp of abc1234 could not be removed: …", or give the current line only when
  `read` found a note.

## Manual checks

The impl report's `## Manual checks` still holds the brief's one important check as an unticked
box. That is correct: it needs KLA's real release on the laptop, not a phone, so it needs no
`device-checks.md` row.

For KLA:
- [ ] **important** — Run **Pre-flight** (or `/pre-flight`) on the S049 commit, then **Release
  patch** in the window. The console shows "Tests passed in pre-flight …", goes straight to the
  version bump, and prints "The pre-flight stamp of … is carried to the release commit …".

## Checked and found consistent

- `release.py` step 2: the `skip` branch, the missing-module branch (`run_tests` then runs
  without a lock) and the stamp after a green run are as in round 1. The sha read before the run is
  still the one stamped.
- The fake `release_lock` in `fake_stamp_module` has the real one's shape (`(got, error)`, given
  back in `finally`). The three new release tests cover held, refused and error.
- `held_lock` is unchanged. `preflight_running()` still creates no lock file when none exists.
- The docs pass for this round:
  - the *Pre-flight (S049)* bullet in `.claude/CLAUDE.md` names `CLOCK_SKEW`, the removal on red
    and the lock held around `TEST_CMD`, and it matches the code;
  - the skill has a row for each new last line, and for the removal or its failure;
  - no schema, `Plan.MD`, secret, Keycloak or `device-checks.md` change is due.
- The `## Lift to smtw-common` text is still right. It lists the same files, and A2 adds no file.
- Scope: nothing is built beyond the brief, A1 and A2.

## Feedback

- rule: the agent file says to run `tooling/run-tests.bat` in round 2, but the orchestrator named one pytest line for a tooling-only fix round; the agent file could say that a round that touches only `tooling/` runs only the tooling suite (`.claude/agents/code-reviewer.md`, "Round 2 and later").
- idea: the snapshot has no commit for the state before the fix round, so I could not diff "the fix round's own diff" and had to read every round file in full. A snapshot per review round, for example `refs/steps/S049-r1`, would make round 2 a real diff (`git show refs/steps/S049`, 5 files read in full).
