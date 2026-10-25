```
Step: S049 — Pre-flight before a release
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: full
Status: Implementing (approved 25-10-2026 by KLA, open questions 1-3 as recommended)
Baseline: c32e02f (brief-review r2; uncommitted changes were step documents only)
```

# S049 — Pre-flight before a release

**The need (KLA, 25-10-2026).** "When I click 'release patch' usually I have to get a maintenance
window from the users — 'stop using the software, as an update is being released'. Then finding a
bug costs time." The release runs the full tests (Yantra: about 10 minutes, the unit suites and the
browser tests at the Full level, S047); a red test sends KLA back to the code with the users
waiting. So: "if pre-flight checks for bugs, runs full tests, we can create bug reports and spawn
fix rounds. If no bugs found, there must be a way for pre-flight to mark that 'commit xyzabc does
not have any bugs — tests passed' based on which release will run."

KLA's answers (U1–U3): pre-flight **lists the bugs and asks** ("a failing test may need a code fix
or a test fix"); the mark is a **git note**; valid **7 days** for now; the skill is **generic, for
every SMTW repo, and lifted to `smtw-common` later** ("write it accordingly now. we will lift
later").

**Built for the lift.** Every generic file is written in Yantra at the path it will have in
`smtw-common`, names no Yantra file, port or tool, and reads the repo's own settings from the
repo's `CLAUDE.md` (§ 1.2). KLA copies them to `smtw-common` later (§ 1.8); the agents never write
there (the step skill's rule **Agents change nothing outside the repo**).

**Track: full.** It changes the release (`tooling/common/release.py`) and adds a skill and two
scripts; no app code, no migration, no RBAC.

**Replaces the queued S049** ("draft the What's new text, no tests"): the What's new draft waits for
S048, which builds the screen it would fill (Out of scope).

## 1. What will be built

### 1.1 The flow

```
/pre-flight  (KLA, any time before the maintenance window)
  1. tooling/common/preflight.py   the sha of HEAD, the repo's test command, the report
  2. green → a git note on that sha: "passed"            → "Ready to release abc1234."
     red   → bug reports; KLA chooses per bug: fix the code, fix the test, mark it a known
             fault, or investigate → fix-lane steps where the repo has /step; then /pre-flight again
Release patch  (in the window)
  release.py, step 2 "Run tests":
     a valid stamp for HEAD with the same TEST_CMD → "Tests passed in pre-flight …", no test run
     no valid stamp                                → TEST_CMD as today; green → it stamps HEAD
  release.py, step 4: the release commit (only VERSION changed) carries the stamp
```

### 1.2 The repo's settings: a `## Pre-flight` section in its `CLAUDE.md`

The skill and `preflight.py` read the repo's settings from a section `## Pre-flight` of its
`.claude/CLAUDE.md` (Yantra's, § 3). It holds, as a list:
- **Test command**: what pre-flight runs. It must equal the Release run configs' `TEST_CMD`
  (Yantra: `tooling\release-tests.bat`), so pre-flight tests exactly what the release would; the
  release checks this (§ 1.3).
- **Tests a clean copy of HEAD**: `yes` when the test command tests HEAD in its own worktree and
  ignores the working folder (Yantra: `yes`, `release-tests.bat` uses `%TEMP%\yantra-release-tests`);
  `no` otherwise (a plain `pytest` tests the working folder). It decides the dirty-tree rule of
  § 1.4 (BR1-05).
- **Failure logs**: where the failures are after a red run (Yantra: the unit logs
  `scratch/release-tests/<suite>-tests-release.log` with the summary
  `scratch/release-tests/test-summary-release.txt`, BR1-04; the browser report
  `scratch/release-tests/e2e/results.json` and its HTML in `scratch/release-tests/e2e/html/`).
- **Re-run failing tests**: the command shapes for re-running failed tests in one go (Yantra:
  `tooling/run-backend-tests.bat <file>::<test> …`, `tooling/run-frontend-tests.bat <file> -t
  "<name>"`, `tooling/run-e2e-tests.bat --level=full e2e/<spec>:<line> … --project=<the failed project>`, so a
  failure on one device is re-run on that device only; BR2-13).
- **Known fault**: how the repo marks a test expected to fail. Yantra has no such convention yet
  (its specs use `test.skip(condition, reason)` only; BR2-03); this step sets one, **strict**, so a
  known fault that gets fixed turns its test red and the mark is removed, never left silently: a
  browser test gets Playwright's `test.fail()` with a comment naming the fault and its step; a
  backend test `@pytest.mark.xfail(strict=True, reason="<fault, step>")`; a frontend unit test
  vitest's `it.fails(…)` with the same comment. KLA decides strict or not at gate A (§ 6 Q3).

`preflight.py` reads only the first two (BR2-05): it reads from the `## Pre-flight` heading to the
next `## `, finds the lines starting `- **Test command**:` and `- **Tests a clean copy of HEAD**:`,
and takes the value with its backticks stripped, e.g. `` - **Test command**: `tooling\release-tests.bat` ``.
The release compares the stamp's command to `TEST_CMD` by plain string equality, backslash included.
"Tests a clean copy of HEAD" is the repo's own claim, checked by the person who writes it: the tool
cannot verify it, and a wrong `yes` would stamp HEAD for code the command did not test (BR2-20). A repo with no such section: the skill stops with "This repo
has no Pre-flight section in its CLAUDE.md. Add one with its test command, the release's TEST_CMD."

### 1.3 The stamp: `tooling/common/preflight_stamp.py`

- **A git note** in `refs/notes/preflight` on the tested commit, written with
  `git notes --ref=preflight add -f -F <file> <sha>` (a file, so the text needs no quoting; nit).
  A note attaches text without changing the commit. Git does not push notes unless that ref is
  named (`git push --follow-tags` in `release.py` pushes tags only), so the stamp stays on the
  machine by default. `git gc` keeps notes. Read-only check, 25-10-2026: `notes.rewriteRef` is not
  set here, so an amend or rebase does not copy a note, and a stamp is bound to its sha anyway.
- **The text**, plain `key: value` lines, readable with `git notes --ref=preflight show HEAD`:

  ```
  preflight: 1
  result: passed
  commit: <full sha>
  tested_at: 2026-10-25T14:30:00+05:30
  test_cmd: tooling\release-tests.bat
  machine: <computer name>
  by: <git user.name>
  carried_from: <full sha>          (only on a release commit, § 1.5)
  summary: <the test command's last summary lines, at most 10, each prefixed>
  ```

- **Valid** when all hold: `preflight: 1`; `result: passed`; `commit` is the full sha of HEAD;
  `tested_at` (ISO 8601 with offset) no more than `STAMP_VALID_DAYS` × 24 h (7 days, 168 h) before
  now; `test_cmd` equals the release's `TEST_CMD` exactly; `machine` is this computer. A dirty tree
  is the release's own refusal (`release.py:90-94`), not the stamp's (BR2-01). Messages show times as DD-MM-YYYY HH:MM
  IST.
- **Pure core**: `stamp_text(...)`, `parse(text)`, `check(note_text, head_sha, test_cmd, now,
  machine)` → `(valid, reason)`. **Shell**: `read(sha)` (`None` when the commit has no note: `git
  notes show` exits 1 with "no note found" on git 2.45), `write(sha, ...)` (returns `False` on a git
  error), `head_sha()`, `tree_clean()` (for `preflight.py`), `machine_name()`, `release_gate(test_cmd)`
  (§ 1.5), `preflight_running()` (§ 1.5). The carry has a pure part, `carry_text(parent_note,
  changed_files, release_sha)` → the note text or `None`, and the shell `carry(release_sha)` around
  it (BR2-09). A git
  error is never "valid": `check` gets `None` and answers "no stamp".
- **Trust** (nit): the stamp is evidence made on this machine. Anyone who can write to the repo can
  write a note; on a one-person release laptop that is accepted, as for every local git ref.
- **A small CLI** for checks by hand: `preflight_stamp.py gate "<test command>"` prints what the
  release would decide, changes nothing.

### 1.4 `tooling/common/preflight.py` (the run)

`uv run --no-project python tooling/common/preflight.py`, stdlib only:
1. **The settings**: reads the test command and "Tests a clean copy of HEAD" from `CLAUDE.md`
   (§ 1.2). Missing → the line of § 1.2, exit 2.
2. **One run at a time**: takes an exclusive lock on `scratch/preflight.lock` in the main working
   folder (the parent of `git rev-parse --git-common-dir`, as S047's e2e lock); a second run says
   "Another pre-flight is running. Wait for it to finish." and exits 2 (BR1-09: Yantra's test
   command removes the worktree of a run already in progress). The lock code (`msvcrt` / `fcntl`,
   the common-dir lookup) is a deliberate copy of `run_lanes.main_scratch` and
   `one_run_at_a_time`, because generic code cannot import a repo's file; a later tidy-up may make
   `run_lanes` use the generic one (BR2-07). `preflight.py` creates `scratch/` and
   `scratch/preflight/` when missing; it assumes `scratch/` is gitignored, as in every SMTW repo
   (Yantra: `.gitignore:15`); where it is not, the lock file would show as an uncommitted change
   (BR2-06).
3. **Refuses**, exit 2, with one line each:
   - not on `main`: "Pre-flight runs on main, as the release does. You are on <branch>.";
   - uncommitted changes, **only when "Tests a clean copy of HEAD" is `no`**: "The working tree has
     uncommitted changes, and the test command tests the working folder. Commit or stash them, then
     run pre-flight again." With `yes`, it says "The working tree has uncommitted changes; the
     tests run on commit abc1234 only." and goes on (BR1-05).
4. **The sha**: reads the full sha of HEAD once, before the test command starts, and keeps it
   (BR1-01). The stamp, if any, goes on this sha, never on a later HEAD.
5. **Runs the test command** in the repo root (`shell=True`, as `release.py` runs `TEST_CMD`), its
   output passing through to the console and into `scratch/preflight/<short-sha>.log`.
6. **After the run**, HEAD is read again:
   - HEAD is no longer the sha of step 4 → "A commit was made during pre-flight, so it is not clear
     which commit the tests ran on. No stamp. Run pre-flight again." exit 1 (the test command
     resolves HEAD itself when it starts, so the two reads could differ; BR1-01). Accepted for the
     record (BR2-18): the window between the two reads is milliseconds, and the one miss is a
     commit during the run followed by a reset to the same sha before its end. Also for the record:
     Yantra's worktree links the working folder's `frontend/node_modules`; the same lockfile gives
     the same packages, and a changed lockfile is a new sha;
   - green (exit 0) → `write(sha, …)`; on success "Pre-flight passed for abc1234. Stamped until
     01-11-2026 14:30." exit 0; when the note cannot be written, "Pre-flight passed for abc1234, but
     the stamp could not be written: <git's message>. The release will run its tests." exit 1
     (BR1-11);
   - red → "Pre-flight failed for abc1234: the test command exited <n>. No stamp." exit 1.

Exit codes: 0 passed and stamped; 1 the tests failed, the stamp failed, or HEAD moved; 2 not run
(no settings, another run, a refusal) (BR1-08).

### 1.5 `tooling/common/release.py`, steps 2 and 4

Step 2, before running `TEST_CMD` (unless it is `skip`):
1. `preflight_stamp.release_gate(TEST_CMD)`:
   - valid → print "Tests passed in pre-flight on 25-10-2026 14:30 for abc1234. The release does
     not run them again." and go on to step 3;
   - not valid → print the reason in one line, ending with what happens next (BR2-10): "No
     pre-flight stamp for abc1234. The tests run now." / "The pre-flight stamp of abc1234 is 9 days
     old; a stamp is valid for 7 days. The tests run now." / "The pre-flight stamp of abc1234 was
     made with another test command. The tests run now." / "… on another computer. The tests run
     now." — and run `TEST_CMD` as today.
0. **First of all, a pre-flight still running** (BR2-04): `preflight_running()` tries the
   pre-flight lock without waiting; when another process holds it, the release aborts before any
   test or bump: "A pre-flight is still running on this computer, and the release would remove its
   test worktree. Wait for it to finish, then start the release again." This is the one way the
   gate stops a release, and it stops it before anything changes.
2. After a green `TEST_CMD` run → `write` on the sha read before the run (the release's tree is
   clean, `release.py:90`, and nobody commits during a release). A failed write prints a warning
   and the release goes on.

Step 4, right after the `release vX.Y.Z` commit (BR1-03): when HEAD's first parent carries a valid
stamp and `git diff --name-only <parent> HEAD` lists exactly `VERSION`, `release.py` writes a stamp
on the release commit with `carried_from: <parent sha>` and the parent's `tested_at` (the carried
stamp expires with the original). So a release whose build or deploy failed, retried from the
release commit, finds a valid stamp. A post-bump script that changes other files (`POST_BUMP_SCRIPT`;
unset in Yantra's Release run configs) means no carry, and the retry tests again.

**The gate can only skip tests, never fail a release through an error of its own** (BR2-02):
- `release.py` imports the module inside `try/except ImportError`; without it (a sync fetched the
  new `release.py` but not `preflight_stamp.py`; `sync_common.py` goes on after a failed fetch), it
  prints "The pre-flight check is not installed. The tests run now." and runs `TEST_CMD`;
- `release_gate`, `write`, `carry` and `preflight_running` each catch their own errors: the gate
  answers "not valid" and the tests run; a failed `write` or `carry` prints a warning and the
  release goes on; `preflight_running` answers "not running";
- tests cover each of these.

### 1.6 The skill: `.claude/skills/pre-flight/SKILL.md`

1. Reads the repo's `## Pre-flight` section (§ 1.2); stops if it is missing.
2. Where the repo has the `/step` skill: runs `tooling/step-check.bat` (it always exits 0; its lines
   are the result, nit) and `tooling/step-ls.bat`, and lists, as information, its problems and the
   steps not `Done`.
3. Runs `preflight.py` **in the background** (a long run can pass the Bash tool's 10-minute limit),
   and says it has started and how long it may take.
4. **Green**: "Ready to release abc1234: every test passed. Stamped until 01-11-2026 14:30." with the
   test summary and the information of step 2.
5. **Exit 1 for another reason** (BR2-11): it reads `preflight.py`'s last console line first. "HEAD
   moved" → says so and offers to run again. "Passed, but the stamp could not be written" →
   reports git's message, writes no bug report and re-runs nothing.
   **Red**: reads the failure logs and writes one **bug report** per failure into
   `scratch/preflight/<short-sha>.md` and the message: what failed (the test, the device, the
   error's first lines), the step its name points to (Yantra test names start with `S0NN:`), and
   where the cause may be — the test or the code, with the files the error names (ISTQB *defect
   report*). Then it re-runs the failed tests **once, in one targeted run per suite** with the
   repo's re-run command (at most `RERUN_MAX` = 10 tests; above that it re-runs none and says so,
   BR1-07), and marks each "failed again" or "passed on re-run (flaky)". The re-run runs in the working folder;
   when `git status --porcelain` is not empty, the verdict adds "(the working tree has uncommitted
   changes)", because a fix already in the folder can make a test pass (BR2-12).
6. **Only flaky failures left** (every failure passed on re-run): offers "Run pre-flight again now",
   "Fix the flaky test" (a fix-lane step, as S045 did; BR2-14) and "Stop here" (BR1-02); a second
   clean run stamps the commit.
7. **Steady failures**: asks KLA **per bug** (one question each, up to four questions at a time),
   with four options (BR1-06):
   - **Fix the code** → a fix-lane step (`/step fix`) with the bug report as its bug;
   - **Fix the test** → a fix-lane step whose fix is in the test (the code is right);
   - **Mark as a known fault** → a fix-lane step that marks the test expected to fail, the repo's
     way (§ 1.2 "Known fault"), with a comment naming the fault, so the release can run; the fault
     goes into the step's brief as open (BR1-02);
   - **Investigate first** → the advisor on the failure, in the folder of the step the test names
     (`/step ask S0NN …`), then the question again.

   In a repo without `/step`, the options say what to change, and the skill changes nothing;
   *Investigate first* there means the skill investigates itself, read-only (reads the code and the
   log, runs the one test), writes what it found into the bug report, and asks again (BR2-15).
8. Ends with: "Commit the fixes, then run /pre-flight again: the new commit has no stamp."

The skill never commits, never writes a stamp itself, never runs the release, and never turns a red
run green.

### 1.7 Yantra's settings

The new `## Pre-flight` section of `.claude/CLAUDE.md` holds the values of § 1.2.
`tooling/release-tests.bat` also copies `scratch/e2e-report/results.json` into
`scratch/release-tests/e2e/` (today it copies the HTML report, the lane logs and the backend logs),
so the skill can read the browser failures.

### 1.8 The lift to `smtw-common` (KLA, later)

KLA copies `.claude/skills/pre-flight/SKILL.md`, `tooling/common/preflight_stamp.py`,
`tooling/common/preflight.py` and `tooling/common/release.py` to the same paths in `smtw-common`.
`sync_common.py` already syncs the whole `.claude/skills` folder, so the skill needs no entry; the
two scripts are added to its `FILES` list (nit). He adds the § 1.9 text to `CLAUDE-COMMON.md` and
`SMTW-WebApp-Base.md`. The coder writes the file list and the § 1.9 text into the impl report under
`## Lift to smtw-common`, ready to paste, and the tests (`tooling/tests/test_preflight_stamp.py`) go
with them.

**Until the lift**, a run of `sync_common.py` overwrites Yantra's `release.py` with the old one from
`smtw-common`. That is safe (the release then runs its tests every time, as today), and
`.claude/CLAUDE.md` § Release says so in one line.

### 1.9 The common docs' text (for the lift)

- `CLAUDE-COMMON.md` § Release workflow, step 2: "Run `TEST_CMD`, unless HEAD carries a valid
  pre-flight stamp (`/pre-flight`, `tooling/common/preflight_stamp.py`): the tests passed on this
  exact commit, on this machine, with this `TEST_CMD`, within 7 days." And under its rules: "Run
  `/pre-flight` before the maintenance window, so a failing test is found before the users stop
  work. The skill needs a `## Pre-flight` section in the repo's `CLAUDE.md`; the release's gate is on
  everywhere and does nothing where no stamp exists."
- `SMTW-WebApp-Base.md` § Pre-flight Before Every Release: the two-stage flow of § 1.1 replaces
  "Pre-flight is automated by `release.py`".

### Out of scope

- The *What's new* draft (the old S049): with S048, or as an amendment of S049.
- Writing to `smtw-common`: KLA does the lift.
- Pushing the notes ref; stamps from other machines.
- The dependency audit in pre-flight (§ 6 Q1).
- Fixing anything automatically: every fix goes through KLA's answer and the fix lane.

## 2. Standards and practice

- **ISO 9001 § 8.6 (release of products and services)**, the plant's future goal (BR1-10): release
  only after the planned checks show the requirements are met, and keep documented information of
  the release, including who authorised it. The stamp records the checks passed, when, and `by:`
  whom, on the exact commit.
- **Exit criteria / release readiness** (ISTQB glossary, paraphrased): the conditions a build must
  meet before release — here, every test green on the exact commit. Pre-flight checks them before
  the maintenance window instead of during it.
- **Test completion report** (ISO/IEC/IEEE 29119-3, the test documentation part): what was tested,
  the result and the open defects. The pre-flight report and the stamp are that record.
- **Defect report** (ISTQB): what failed, where, how to repeat it, its likely cause; § 1.6's bug
  report has that shape.
- **Change management** (ISO/IEC 27001 Annex A 8.32, paraphrased; nit): changes to systems in use
  follow a controlled path; a tested commit and a maintenance window are part of it.
- **A deliberate departure from `SMTW-WebApp-Base.md` § Pre-flight Before Every Release** ("Pre-flight
  is automated by `release.py`"): the tests move before the window; the release still aborts on red
  when there is no stamp. Recorded in Yantra's `CLAUDE.md` until the lift updates the base.

## 3. Where

| File | Change |
|---|---|
| `tooling/common/preflight_stamp.py` | new, generic, stdlib: § 1.3; `STAMP_VALID_DAYS` (7), `NOTES_REF`; pure `stamp_text`, `parse`, `check`; shell `read`, `write`, `head_sha`, `tree_clean`, `machine_name`, `release_gate`, `carry(release_sha)`; the `gate` CLI |
| `tooling/common/preflight.py` | new, generic, stdlib: § 1.4; reads the two settings from `.claude/CLAUDE.md` |
| `tooling/common/release.py` | step 2: the gate and the stamp after a green run; step 4: the carried stamp (§ 1.5); `import preflight_stamp` from its own folder |
| `tooling/tests/test_preflight_stamp.py` | new (adds `tooling/common` to `sys.path`, as `release.py` finds its sibling; `tooling/tests/conftest.py` adds only `tooling/`; BR2-08): `check` for every rule of § 1.3 (wrong sha, too old by one minute past 168 h and valid one minute before, another test command, another machine, `result: failed`, unknown version, garbled text, `None`), `stamp_text` ↔ `parse`; `carry_text` with `["VERSION"]`, `["VERSION", "pyproject.toml"]` and an invalid parent note (BR2-09); `release_gate` with git stubbed; each guard of § 1.5 (an import error, a raising `release_gate` / `write` / `carry` / `preflight_running`) |
| `tooling/tests/test_preflight.py` | new: `preflight.py`'s settings reader (backticks, a missing section, a missing line), its refusals (both values of "clean copy"), the lock, the sha read once, "HEAD moved", the failed write (git and the command stubbed) |
| `.claude/skills/pre-flight/SKILL.md` | new, generic: § 1.6 |
| `tooling/release-tests.bat` | copies `results.json` too (§ 1.7) |

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md`: the new `## Pre-flight` section (§ 1.2, § 1.7); § Release: the stamp, the 7
  days, the departure from the base, the "until the lift, a sync restores the old `release.py`" line.
- `docs/steps/README.md`: the queue's S048 row says "before S049, which drafts its text"; it becomes
  "the What's new draft comes with S048, or as an amendment of S049" (nit; done by the planner with
  this brief).
- The impl report's `## Lift to smtw-common`: the file list and the § 1.9 text.
- No schema, Plan.MD or domain doc is due.

## 4. Design decisions

1. **The gate lives in `release.py`**, which every SMTW repo shares. The skill and `preflight.py`
   need a repo's `## Pre-flight` section; the gate in `release.py` needs nothing: after the lift it
   is on in every repo, and inert where no stamp exists (BR2-17). Rejected: the gate in Yantra's `release-tests.bat` (Yantra only).
2. **The stamp is a git note on the tested sha** (KLA, U1), read once before the run (BR1-01).
   Rejected: a commit (it changes HEAD), a tag per run, a file in `scratch/`.
3. **The stamp names its test command, which must match the release's `TEST_CMD`**: a green run of a
   smaller command must not let the release skip the full one.
4. **The release commit carries the stamp** when it changes only `VERSION` (BR1-03), so a retry
   after a failed build or deploy does not test again. Rejected: re-testing on every retry.
5. **A stamp is valid only on the machine that made it.** Rejected: any machine.
6. **Pre-flight runs with a dirty working tree when the test command tests a clean copy of HEAD**
   (BR1-05): KLA keeps working while it runs. Rejected: always refuse a dirty tree (pre-flight
   would be unusable during normal work).
7. **Lists and asks; never fixes alone** (KLA, U1). A steady failure ends in a fix of the code, a fix
   of the test, or a marked known fault — never in "release anyway", which the release's own red run
   would refuse (BR1-02).
8. **Failed tests are re-run once, together, capped at 10**, to tell steady from flaky; a re-run never
   makes the run green.
9. **Built in Yantra at the common paths, lifted by KLA** (U3), keeping the agents' rule. Rejected:
   the coder writing into `../smtw-common`.

## 5. Tests and acceptance

- **Unit** (`tooling/run-tooling-tests.bat`): § 3's tests, red first for `check`, `carry` and
  `release_gate`.
- **Runs the coder makes and reports** (on a clean HEAD of the working folder; the coder does **not**
  run `release.py`, which bumps, tags, builds and deploys):
  1. `uv run --no-project python tooling/common/preflight.py`: green, stamped;
     `git notes --ref=preflight show HEAD` shows the note.
  2. `preflight_stamp.py gate "tooling\release-tests.bat"`: "Tests passed in pre-flight …" (with
     the step's own files uncommitted: the gate reads no tree state, BR2-01).
  3. `preflight_stamp.py gate "tooling\run-tests.bat"`: "… made with another test command."
  4. A second `preflight.py` while the first runs: "Another pre-flight is running …", exit 2.
  5. A red run: a temporary Test command `cmd /c exit 1` in the working folder's `CLAUDE.md`,
     reverted after the run (BR2-16): "Pre-flight failed …", exit 1, no note.
  6. `carry` on a throw-away pair of commit objects (a parent with a stamp, a child changing only
     `VERSION`): the child gets the carried stamp; notes on throw-away objects are removed afterwards
     (`git notes --ref=preflight remove`).
- **Accept when** the four unit suites are green and the six runs give what § 1 says.

### Manual checks (KLA's laptop, the dev working folder)

1. **important** — Run `/pre-flight` before the next release; then **Release patch**: its console
   shows "Tests passed in pre-flight …" and goes straight to the version bump.

## 6. Open questions and assumptions

1. **The dependency audit**: proposed **not** in pre-flight for now (a finding often has no fix yet
   and would block the stamp); the audit stays its own check. Alternative: in the report as
   information.
2. **Steps not `Done`** since the last release: proposed as information in the report, not a blocker.
3. **A known fault's mark, strict or not** (BR2-03): proposed **strict** — `test.fail()`,
   `xfail(strict=True)`, `it.fails` — so a fixed fault turns its test red until the mark is removed.
   Alternative: non-strict (`test.fixme`, `xfail` without strict): a fixed fault stays marked
   silently.
4. **Assumption**: Yantra's test command takes about 10–12 minutes (S047: the browser part 320–338 s).

## 7. Amendments

None.

## Review log

### U1 — user answers, 25-10-2026 (before drafting)

- Pre-flight lists the bugs and asks: "a failing test may need a code fix or a test fix."
- The stamp is a git note ("git note we will go with").
- "The stamp need not have more than a few days validity. may be 3. ok, 7 for now."

### U2 — the base's pre-flight, 25-10-2026

KLA asked whether CLAUDE-COMMON already had pre-flight: `SMTW-WebApp-Base.md` § Pre-flight Before
Every Release says "Pre-flight is automated by `release.py`". This step departs from it (§ 2).

### U3 — generic, lifted later, 25-10-2026

KLA: "let's lift the pre-flight skill to smtw-common. then CLAUDE-COMMON.md can point to it." Then:
"write it accordingly now. we will lift later." The generic files are built at their common paths in
Yantra (§ 1.8); the gate moves from `release-tests.bat` into `release.py` (decision 1).

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

Round 1 read the earlier draft (the gate in `release-tests.bat`, before U3); every finding is
answered against this text.

| Finding | Answer |
|---|---|
| BR1-01 major: which sha is stamped | Accepted: the sha read once before the run; the stamp only on it; "HEAD moved" → no stamp (§ 1.4 steps 4 and 6, decision 2) |
| BR1-02 major: "Leave it" is a dead end | Accepted: the four options are fix the code, fix the test, mark as a known fault (the repo's expected-to-fail way), investigate; flaky-only → "Run pre-flight again now" (§ 1.6, decision 7) |
| BR1-03 major: the release commit has no stamp | Accepted: `release.py` carries the stamp to the release commit when only `VERSION` changed (§ 1.5, decision 4) |
| BR1-04 minor: the log names | Accepted: `<suite>-tests-release.log`, `test-summary-release.txt`, in Yantra's settings (§ 1.2); the skill reads them, no parser in the generic code |
| BR1-05 minor: a dirty tree blocks normal work | Accepted: "Tests a clean copy of HEAD: yes" lets pre-flight run with a dirty tree (§ 1.2, § 1.4, decision 6) |
| BR1-06 minor: five options, a limit of four | Accepted: four options; re-run is an outcome (§ 1.6) |
| BR1-07 minor: one re-run per failure is slow | Accepted: one targeted run per suite, capped at 10 (§ 1.6, decision 8) |
| BR1-08 minor: exit 2 had no source | Accepted: exit codes defined by `preflight.py` (§ 1.4) |
| BR1-09 minor: two runs at once | Accepted: the pre-flight lock (§ 1.4 step 2) |
| BR1-10 minor: ISO 9001 § 8.6, `by:` | Accepted (§ 2, § 1.3) |
| BR1-11 minor: counts in batch, a failed write | Moot for batch (the gate is Python now); a failed write gives exit 1 in pre-flight and a warning in the release (§ 1.4, § 1.5) |
| BR1-12…BR1-23 nits | Accepted, all: the skills folder syncs whole (§ 1.8); ISO 8601 with offset and the 168 h boundary tested (§ 1.3, § 3); `--porcelain` named (§ 1.3); `-F` (§ 1.3); step-check always exits 0 (§ 1.6); `--fresh` gone (the gate moved); step-ls for "not Done" (§ 1.6); `/step ask S0NN` (§ 1.6); one console line per outcome (§ 1.4); the trust sentence (§ 1.3); the S048 queue row (§ 3 Docs); ISO/IEC 27001 A 8.32 (§ 2) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor: the clean-tree rule in the stamp | Accepted: dropped from *Valid*; the release's own refusal covers it (§ 1.3, § 5 run 2) |
| BR2-02 minor: the gate could fail a release | Accepted: `try/except ImportError`; each function catches its own errors; tests (§ 1.5, § 3) |
| BR2-03 minor: no known-fault convention exists | Accepted: a new, strict convention proposed; KLA decides at gate A (§ 1.2, § 6 Q3) |
| BR2-04 minor: a release during a pre-flight | Accepted, a variant of the recommendation: `release.py` checks the pre-flight lock first and aborts before anything changes (§ 1.5 step 0), instead of a marker in `release-tests.bat`, so every repo gets it |
| BR2-05…BR2-20 nits | Accepted, all: the settings line format (§ 1.2); `scratch/` created and assumed gitignored (§ 1.4); the lock copy is deliberate (§ 1.4); `tooling/common` on `sys.path` and a second test file (§ 3); `carry_text` (§ 1.3, § 3); "The tests run now." (§ 1.5); the skill's other exit-1 outcomes (§ 1.6); the dirty-folder note on re-runs (§ 1.6); `--project=` (§ 1.2); "Fix the flaky test" (§ 1.6); *Investigate first* without `/step` (§ 1.6); run 5 with a temporary command (§ 5); the gate is on everywhere (decision 1, § 1.9); the HEAD-moved window and the junction, accepted for the record (§ 1.4); the README row (planner); "clean copy" is the repo's claim (§ 1.2) |

### U4 — approval, 25-10-2026

KLA: "Approved, as recommended." Q1: no dependency audit in pre-flight. Q2: steps not `Done` are information only. Q3: known faults are marked strictly (`test.fail()`, `xfail(strict=True)`, `it.fails`).
