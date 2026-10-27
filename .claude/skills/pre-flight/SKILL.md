---
name: pre-flight
description: Run the release's tests on HEAD before the maintenance window, so a failing test is found before the users stop work. Green stamps the commit (a git note) and the release then skips its tests; red writes one bug report per failure, re-runs the failed tests once, and asks per bug what to do (fix the code, fix the test, mark as a known fault, investigate). Where the repo asks for it, it also drafts the release notes from the commits since the last release; `/pre-flight notes` drafts only the notes (the release hook calls it unattended). Use when the user says /pre-flight, "pre-flight", "is it ready to release", or asks to test before a release.
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

## 0. How it was started: with a person, or unattended

Decide this first, from the arguments. The first line of the arguments decides the mode; any
lines after it are the input.

| Arguments | Started by | Do |
|---|---|---|
| none | a person, in a Claude Code session | the whole run, § 1 to § 6 |
| `notes` | a person, in a Claude Code session | only the release notes: § 1, then § 3a; write the notes file and show the items; no tests, no stamp |
| `notes unattended`, followed by the commit list | the release hook (`claude -p`, from a PyCharm Release run config, or a terminal) | only § 3b |

**Unattended means no person is there.** Nobody reads a question, so never ask one, never offer
options, never wait, and never stop to say what is missing. Work with what you have: the commits
on the input and the repo's settings. Only `Read` is allowed there (no shell, no git, no writes).
Whatever goes wrong (no settings, no commits on the input, a file you cannot read), print nothing
at all: the release then writes an empty section and goes on.

## 1. The repo's settings

Read the `## Pre-flight` section of the repo's `.claude/CLAUDE.md` (from the heading to the next
`## `). It holds:
- **Test command**: what pre-flight runs; it must equal the Release run configs' `TEST_CMD`.
- **Tests a clean copy of HEAD**: `yes` when the command tests HEAD in its own worktree.
- **Failure logs**: where the failures are after a red run.
- **Re-run failing tests**: the command shapes to re-run failed tests in one go.
- **Known fault**: how the repo marks a test expected to fail.
- **Release notes** (optional): the notes file, then `readers:` and who reads the notes, e.g.
  `scratch/release-notes.md; readers: IT Admin, Admin and maintenance engineers of Yantra, a plant
  maintenance app`. Without it, skip § 3a and § 3b.

No such section: stop with "This repo has no Pre-flight section in its CLAUDE.md. Add one with its
test command, the release's TEST_CMD." (Unattended: print nothing.)

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

## 3a. Release notes, while the run goes on (only with the *Release notes* setting)

The release turns the notes into the new version's section of the repo's changelog (the repo's
release hook reads the notes file; the version number is chosen only at the release). Write the
notes while the tests run, so they cost no waiting.

1. Find the last release tag: `git describe --tags --abbrev=0 --match "v[0-9]*"`. No tag: use
   every commit.
2. Read the commits since it: `git log <tag>..HEAD --format="%H%n%s%n%b%n---"`. Leave out the
   commits whose subject starts `release v`.
3. Write the items by § 3c.
4. Write the notes file: the first line `<!-- commit <full sha of HEAD> -->`, then only the `- `
   items, no heading. When no commit changes the app, write the first line alone. The release
   uses the file only when that line names the commit it releases.
5. The file is a draft in a gitignored folder: never commit it, and never write the changelog
   itself.

The report (§ 4, § 5; for `notes`, the whole answer) shows the items under "Release notes for the
next release" and ends that part with: "Edit <the notes file> if you want; the release uses it for
commit <short sha>." A red run still writes the file; a fix commit makes it stale, and the next
pre-flight writes it again.

## 3b. Release notes, unattended (`notes unattended`)

The release hook found no notes file for the commit it releases, so it asks for the items now.
Read § 0 again: no questions, nothing but the items.

1. Read the *Release notes* setting (§ 1) for the readers. The commits follow the words `notes
   unattended` in the arguments (the hook pipes them on standard input, and `claude -p` adds them
   after the prompt). Each commit is a line `commit <short sha>`, its subject, its body, and a
   blank line. Release commits are already left out. Do not look for commits anywhere else.
2. Write the items by § 3c.
3. Print only the `- ` lines: no heading, no greeting, no sha line, no explanation before or
   after, no code fence. When no commit changes the app, print nothing.

## 3c. How to write the items (both paths)

The notes are read by the setting's *readers*, in the app, after the release. They are end users,
not developers: they want to know what they can now do or see, nothing else. Write for them:

- **Only what matters to the readers.** If a reader would not notice the change on a screen, in a
  report, in a message or in how the app behaves, leave it out.
- **No technical words**: no API, endpoint, token, cache, database, migration, query, backend,
  frontend, refactor, dependency, CORS, header, or the names of libraries and tools. Say what the
  reader sees: "Sign-in shows a clear message when the login server is down", not "503 on JWKS
  fetch failure".
- **Terse.** One line per item, 15 words or fewer. A full sentence, no trailing full stop needed.
- **The readers' words.** What the reader does or sees on a screen: "Close a ticket from the
  list", not "add close endpoint". The app's own names for screens and buttons.
- **Present tense**, active. No "now", "new:", "we", exclamation marks or praise ("improved",
  "better", "enhanced" alone say nothing: say what changed).
- **One item per feature.** Merge the commits about one feature into one item. A fix is an item
  only if a reader noticed the fault: "Readings save again after a network drop".
- **Small fixes may be grouped by area.** Several small fixes in one part of the app, none worth
  a line of its own: one item such as "Tickets: various bug fixes".
- **Only what a commit states.** Never guess a feature from a file name, and never add detail the
  commit does not give.
- **Leave out** what no reader sees: tooling, tests, docs, the step workflow, refactors, builds,
  dependency updates, release commits.
- **No internals**: no step or ticket numbers (`S0NN`), file names, code names, commit ids,
  version numbers or dates.
- **1 to 8 items**, the most useful first. More features than 8: keep the 8 that matter most to the
  readers. No commit changes the app: no items.

## 4. Green

Report: "Ready to release <short sha>: every test passed. Stamped until <the time in the last
line>." Add the test summary (the lines before the last one), the information of § 2, and the
release notes of § 3a.

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
