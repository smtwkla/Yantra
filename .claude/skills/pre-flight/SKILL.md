---
name: pre-flight
description: Run the release's tests on HEAD before the maintenance window, so a failing test is found before the users stop work. Green stamps the commit (a git note) and the release then skips its tests; red writes one bug report per failure, re-runs the failed tests once, and asks per bug what to do (fix the code, fix the test, mark as a known fault, investigate). Use when the user says /pre-flight, "pre-flight", "is it ready to release", or asks to test before a release.
---

# /pre-flight — the release's tests, before the window

`tooling/common/preflight.py` does the deterministic part: it runs the repo's test command (the
release's `TEST_CMD`) on HEAD and, when it is green, stamps that exact commit
(`tooling/common/preflight_stamp.py`, a note in `refs/notes/preflight`, valid for 7 days on this
computer). `release.py` then prints "Tests passed in pre-flight …" and does not run the tests
again. This skill runs it, reads the result, and turns a red run into bug reports and questions.

**Never**: commit, write a stamp yourself (`git notes …`), run the release, or turn a red run
green (a re-run that passes does not stamp). Every fix goes through the user's answer.

Standards (say them in plain words when they help the user): *exit criteria / release
readiness* (ISTQB): every test green on the exact commit before release; *defect report*
(ISTQB): what failed, where, how to repeat it, the likely cause; *test completion report*
(ISO/IEC/IEEE 29119-3); ISO 9001 § 8.6: release only after the planned checks pass, with a record
of who authorised it (the stamp's `by:` line).

## 1. The repo's settings

Read the `## Pre-flight` section of the repo's `.claude/CLAUDE.md` (from the heading to the next
`## `). It holds:
- **Test command**: what pre-flight runs; it must equal the Release run configs' `TEST_CMD`.
- **Tests a clean copy of HEAD**: `yes` when the command tests HEAD in its own worktree.
- **Failure logs**: where the failures are after a red run.
- **Re-run failing tests**: the command shapes to re-run failed tests in one go.
- **Known fault**: how the repo marks a test expected to fail.

No such section: stop with "This repo has no Pre-flight section in its CLAUDE.md. Add one with its
test command, the release's TEST_CMD."

## 2. Information first (repos with the `/step` skill)

Where `.claude/skills/step/` exists, run `tooling/step-check.bat` (it always exits 0; its lines are
the result) and `tooling/step-ls.bat`. Keep their problems and the steps not `Done` as
**information** for the report. They never block the run.

## 3. Start the run, in the background

Run `uv run --no-project python tooling/common/preflight.py` from the repo root **in the
background** (a run can pass the Bash tool's 10-minute limit). Say that it has started, on which
commit (`git rev-parse --short HEAD`), and how long it may take (the repo's CLAUDE.md may say;
else "several minutes"). Wait for the completion notice; do not poll.

Its exit code and **last console line** decide what comes next:

| Exit | Last line starts with | Next |
|---|---|---|
| 0 | "Pre-flight passed for …" | § 4 |
| 1 | "Pre-flight failed for …" | § 5. A red run removes the commit's earlier stamp: the line then ends "Its earlier stamp is removed." When the removal failed, the line before it says so and gives the `git notes` command; report it, because the release would still skip its tests on that stamp. |
| 1 | "A commit was made during pre-flight" | Say so; offer to run it again. No bug report. |
| 1 | "The working tree changed during pre-flight" | The command tests the working folder, and a file changed during the run. Say so; offer to run it again on a tree left alone. No bug report. If it happens every time, the test command leaves files outside `.gitignore`: add them to `.gitignore`, or set "Tests a clean copy of HEAD" to `yes` only if the command really tests a clean copy. |
| 1 | "Pre-flight passed for …, but the stamp could not be written" | Report git's message from that line. No bug report, no re-run. |
| 2 | "Pre-flight stopped because of a file or system error" | Report the line as it is (a folder that cannot be written, a command that cannot start). No bug report, no re-run. |
| 2 | (a refusal: no settings, another pre-flight or a release running its tests, not on main, uncommitted changes) | Report the line as it is. |

The run's whole output is in `scratch/preflight/<short-sha>.log`.

## 4. Green

Report: "Ready to release <short sha>: every test passed. Stamped until <the time in the last
line>." Add the test summary (the lines before the last one) and the information of § 2.

## 5. Red: bug reports, one re-run, then the questions

1. **Read the failures** from the settings' *Failure logs* (summary files first, then each failed
   suite's log; a browser report's JSON for the failed tests, their project and their error).
2. **Write one bug report per failure** into `scratch/preflight/<short-sha>.md`, and show them in
   the message. Each has:
   - what failed: the test's full name, the suite, the device or project, the error's first lines;
   - the step its name points to (where test names start with a step id, e.g. `S0NN: …`);
   - how to repeat it: the re-run command for that one test;
   - where the cause may be: the test or the code, with the files and lines the error names.
3. **Re-run the failed tests once**, together, one targeted run per suite with the settings'
   *Re-run failing tests* shapes, in the working folder. At most `RERUN_MAX` = 10 tests in all;
   above that, re-run none and say so: each failure then counts as steady and gets the four
   options of step 5. Mark each bug "failed again" or "passed on re-run (flaky)".
   When `git status --porcelain` prints anything, add "(the working tree has uncommitted
   changes)" to each verdict: a fix already in the folder can make a test pass.
4. **Only flaky failures left** (each passed on re-run): ask one question with the options
   "Run pre-flight again now", "Fix the flaky test" (a fix-lane step where the repo has `/step`)
   and "Stop here". A second clean run stamps the commit.
5. **Steady failures**: ask **per bug**, one question each (up to four questions at a time), with
   these four options:
   - **Fix the code** — a fix-lane step (`/step fix`) with the bug report as its bug;
   - **Fix the test** — a fix-lane step whose fix is in the test; the code is right;
   - **Mark as a known fault** — a fix-lane step that marks the test expected to fail, the repo's
     way (the settings' *Known fault*), with the fault named in the mark, so the release can run;
     the fault goes into that step's brief as open;
   - **Investigate first** — the advisor on the failure, in the folder of the step the test names
     (`/step ask S0NN …`); then ask the question again.

   In a repo without `/step`: the options say what to change, and the skill changes nothing.
   *Investigate first* there means: investigate yourself, read-only (read the code and the log,
   run the one test), write what you found into the bug report, and ask again.

## 6. End

End every red or flaky outcome with: "Commit the fixes, then run /pre-flight again: the new commit
has no stamp."
