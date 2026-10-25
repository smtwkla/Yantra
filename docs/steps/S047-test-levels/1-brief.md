```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: full
Status: Done (committed 1a34660, 25-10-2026; checks: 7 runs recorded, no device checks)
Baseline: 4d89084 + uncommitted step docs and the 25-10-2026 run-rule edits (.claude/CLAUDE.md, agents, step skill); reviewed against in r2
```

# S047 — Browser test levels: Basic, Normal, Full

**The need (KLA, 25-10-2026).** "Playwright tests are costly." A full run takes 6.5 minutes
today (S046's run: 462 tests, 384 s; 12.3 min before S046, with WebKit on Windows). In S039,
S040, S044, S045 and S046 the browser runs took at least 100 of 408 agent minutes
(`tooling/step-stats.bat` on 25-10-2026, the per-step table: 28 + 47 + 5 + 12 + 8 minutes of
1.8 + 2.6 + 0.8 + 0.9 + 0.7 hours; a later run with `S040` overwrote `scratch/step-stats.md`).
KLA asked for:

1. three levels: "Basic functionality — one thread (end to end action) to test a lot of
   functions. Normal: functionality with normal and edge cases. Full functionality and screen
   layout — all nits and all";
2. "what's the point in checking the logic flow … on android and also on desktop and iPhone?
   Only screen issues need to be repeated for all platforms. Most logic coding agents will need
   only either android or desktop";
3. the iPhone out of routine use by step agents: "Only before release. The release run
   configuration already triggers tests. Let it run them";
4. "Balance the lanes."

**Track: full.** No app code, no migration, no RBAC. But it changes shared test config
(`frontend/playwright.config.js`), the release's tests (`tooling/release-tests.bat`) and the run
rules every later step depends on; about 22 files, most of them one-line tags.

**The two other parts of KLA's message are their own steps** (U1 below): S048 *What's new* (the
app shows a version's notes once to admin, IT admin and engineers; needs a migration) and S049
the *pre-flight* skill (step check, draft the What's new text). Both are queued in the README.

## 1. What will be built

### 1.1 Three levels, chosen with one flag

`tooling/run-e2e-tests.bat --level=basic|normal|full [spec files] [other Playwright args]`.
`run_lanes.py` reads and removes `--level=…` and passes the rest on, as today.

| Level | Tests | Devices (projects) | Who runs it, when | Estimate |
|---|---|---|---|---|
| **Basic** | the journey tests and `screens.spec.js` (tag `@smoke`) | `phone-chromium` only | the coder, any time it wants a quick whole-app check; optional | about 2 min |
| **Normal** (default: no flag) | every test on `phone-chromium`; on `desktop-chromium` only the tests tagged `@device` | Android phone, desktop | the coder: **targeted** runs (Normal with spec files named) as often as it needs, and **the whole suite at Normal** once when the step's coding is done | about 2–3 min for the whole suite (the coder measures it) |
| **Full** | every test on all three projects (today's run) | Android phone, iPhone, desktop | the release (`tooling/release-tests.bat`), automatically; KLA when he asks | about 6 min |

- **Why logic runs on one device.** A flow test checks the backend rules and the screen's
  logic: what a click saves, what a refusal says. These do not change with the browser engine
  or the screen width. Running them three times triples the time and finds nothing new. Only
  screen layout and device-specific behaviour differ per device.
- **Why the Android phone carries the logic.** The shop floor uses phones (Plan.MD § 1, Users:
  "Shop floor on phones (mobile-first)"; the Pixel 7 project is the Android phone), so the logic
  is tested on the screen most people use. Every flow then also exercises the phone layout
  (bottom bar, dialogs as sheets).
- **`@device`** marks a test that must run on every device: its purpose is a layout check or a
  device's own behaviour. The rule and the list are in § 1.3.
- **Full is unchanged from today**: every test on every device. So flows that call
  `expectDialogFits` or `expectFieldMessage` still check every dialog on the iPhone's 390 px
  once per release; Normal checks them at the Pixel 7's 412 px, and the `@device` tests also on
  desktop.
- **An explicit `--project` wins** over the level's devices, and then every matching test runs
  on the named projects, with no `@device` filter (BR1-01). Example, a reviewer re-running one
  test on desktop: `--project=desktop-chromium e2e/x.spec.js -g "S0NN"`.

### 1.2 How the levels are wired

`main()` does these in order (BR1-14):

1. Read `--level` (default `normal`; an unknown value stops the run with "Use --level=basic,
   normal or full.").
2. Expand the level into Playwright arguments, but add `--project` arguments only when the
   caller named none:
   - Basic → `--project=phone-chromium --grep @smoke`. A caller's `--grep`, `-g` or
     `--grep-invert` at Basic is refused with one line: "Basic runs the smoke tests only. To run
     chosen tests, use Normal with the spec file and -g." (BR1-05 point 1);
   - Normal → `--project=phone-chromium --project=desktop-chromium`, and the environment
     variable `E2E_LEVEL=normal`. **`E2E_LEVEL` is set only when the level chose the projects**:
     a caller who names `--project` gets no `@device` filter (BR1-01);
   - Full → no project argument (all three).
3. `needs_webkit_server` (S046) reads the expanded arguments. Basic and Normal name only
   Chromium projects, so they start no container; Full names none, so it starts one, as
   `TestWebkitServer::test_a_full_run_needs_it` expects.
4. Make `ROOT / "scratch"` (BR1-04), take the lock (§ 1.6), then plan and run the lanes (§ 1.5).

`frontend/playwright.config.js`: when `E2E_LEVEL` is `normal`, the `desktop-chromium` project
gets `grep: /@device/`; otherwise no project has a `grep`. Playwright applies a project's
`grep` to that project only, and a CLI `--grep` as a second filter: a test runs only when both
match (BR1 evidence: `runner/index.js:2648-2655`, `:6647-6653`).

**No silent empty run** (BR1-01 option b). With planned lanes every lane gets at least one
group with tests, so `--pass-with-no-tests` is dropped from the lane command. When the `--list`
run finds no test, the runner stops with "No test matches these arguments: <args>." and exit 1.
In the `--shard` fallback (§ 1.5) `--pass-with-no-tests` stays: Playwright raises "No tests
found" only without `--shard` (`runner/index.js:6666`), so the flag changes nothing there, and
the runner's own check of the merged totals (exit 1 when no test ran) is the only guard
(BR2-05).

### 1.3 The tags

Playwright tags (`test("title", { tag: "@device" }, async …)`, since Playwright 1.42; the repo
has 1.64.1; the repo's `test` from `frontend/e2e/support/test.js` keeps the signature).

- **`@smoke`** marks the Basic level: the four journey tests (§ 1.4) and the 9 tests of
  `screens.spec.js` per project (`every screen opens as <role>` for 7 roles at
  `screens.spec.js:79`, the lost-headers test at `:92`, the S040 bottom bar at `:103`): 13
  tests on `phone-chromium` (BR2-01).
- **`@device`** marks a test whose **purpose** is a layout check or a device's own behaviour
  (BR1-02 option a). A test gets it when:
  1. its title names a layout check (fits, in view, on screen, scrolls to, no sideways scroll,
     above or below another element), or its main assertion is a geometry;
  2. it runs only on, or asserts differently on, a project other than `phone-chromium`;
  3. it is in `screens.spec.js`.

  These do **not** tag a test: a call to `expectDialogFits`, `expectFieldMessage`,
  `expectNoSidewaysScroll` or `expectTouchTarget` inside a flow test, and a `test.skip` that
  only leaves out `phone-webkit`. The Full level checks those per device once per release
  (design decision 4).
- **The list (23 tests)**, from the titles and branches checked on 25-10-2026:

  | Spec | Line | Test (title start) | Rule |
  |---|---|---|---|
  | `equipment.spec.js` | 36 | S003: the Add equipment dialog fits | 1 |
  | `equipment.spec.js` | 44 | S026: the server's refusal … is on screen | 1 |
  | `equipment.spec.js` | 177 | S029: the bulb is in view without scrolling … | 1 |
  | `masters.spec.js` | 142 | operator: the failure codes are read-only, and the lists fit a phone | 1 |
  | `me.spec.js` | 138 | S031: the three tabs fit the screen width | 1 |
  | `notifications.spec.js` | 104 | S021: on an iPhone outside the Home Screen … | 2 |
  | `notifications.spec.js` | 112 | S021: a browser that blocked notifications … | 2 |
  | `notifications.spec.js` | 241 | S021: the manifest is served and parses … (branches on `phone-webkit`) | 2 |
  | `readings.spec.js` | 395 | S040: Save readings is disabled while saving, and the bar is above the bottom nav | 1 |
  | `tickets-notes.spec.js` | 108 | S027: Save note with an empty field … in view | 1 |
  | `tickets-raise.spec.js` | 87 | S026: Save with nothing chosen scrolls the raise form … | 1 |
  | `tickets-raise.spec.js` | 141 | S018 A1: Already fixed with a start time; the fields fit … | 1 |
  | `tickets-work.spec.js` | 123 | S026: Add labour with no time spent scrolls the dialog … (branches on `phone-webkit`) | 1, 2 |
  | `tickets-work.spec.js` | 491 | S034: a production slot … the reason is above the date | 1 |
  | `screens.spec.js` | 79, 92, 103 | all 9: every screen opens as <role> (7 roles), the lost-headers test, S040: the manager's bottom bar … | 3 |

  The coder tags these, confirms the set with `npx playwright test --list -g @device`, and
  reports in the impl report any test it adds or leaves out by the rule, with the reason.
- **Untagged** marks a logic test: it runs on `phone-chromium` at Normal, and on all three at
  Full. A new test is untagged unless the rule above applies, so the default is the cheap run.
- A test may carry both tags (`{ tag: ["@smoke", "@device"] }`): the `screens.spec.js` tests do.

### 1.4 Basic: four journey tests

A new spec `frontend/e2e/journeys.spec.js`, tagged `@smoke`. Each journey is one test that
walks one real piece of work from start to end through the screens, and checks what each person
sees at each stage. It uses the existing helpers (`frontend/e2e/support/people.js`,
`frontend/e2e/support/tickets.js`, `frontend/e2e/support/meters.js`,
`frontend/e2e/support/dialogs.js`) and makes its own data (names with the project name, as the
other specs). The journeys repeat checks the other specs make in detail; that is their purpose.

1. **Equipment.** The engineer adds an equipment item from the list, opens its page, uploads a
   document, and sees its QR label on the labels screen.
2. **A breakdown ticket, raise to close.** The operator raises a ticket on that equipment; the
   engineer assigns a technician; the technician starts work, adds labour, a part line and a
   note, and puts the equipment back in service (BR1-09: the app's term, EN 13306
   *restoration*); the engineer closes the ticket; the operator's *Me* screen shows it closed.
3. **Readings.** A supervisor logs a counter reading on an equipment page. Then the supervisor
   fills the unit's readings sheet with a higher value for the same meter, with *Time taken*
   one minute later (the specs' `setEventTime` helper), and saves it; the meter's history shows
   both readings (BR1-03: two readings at the same minute are refused, `SAME_MINUTE`, and a
   counter must go up).
4. **Masters.** IT admin adds a manufacturer and a model with a meter; an equipment item of that
   model shows the meter on its page.

The coder reads `equipment.spec.js`, `tickets-work.spec.js`, `tickets-parts.spec.js`,
`readings.spec.js` and `masters.spec.js` for the working selectors. Each journey should stay
under about 30 s on one lane.

### 1.5 Balanced lanes

**The fault.** Playwright's `--shard` splits by test count, and a spec file in one project is
one group that cannot be split (`fullyParallel: false`). It cuts the count into equal slices
and gives each group to the lane where the group *starts* (`filterForShard`,
`frontend/node_modules/playwright/lib/runner/index.js:2462`). With a few large groups
(`readings.spec.js` has 32 tests) the lanes come out uneven: S046's run gave lanes 1, 3, 5
about 100 tests each and lanes 2, 4, 6 about 52 (`scratch/s046-full-e2e.log:4-9`), so half the
lanes sat idle at the end.

**The fix: the runner plans the lanes itself.**
1. `run_lanes.py` runs `npx playwright test --list --reporter=json` once, with the run's
   arguments after the level expansion **and the same `E2E_LEVEL`** as the lanes will have
   (BR1-05 point 2). It reads each test's project (`tests[].projectName`) and file
   (`specs[].file`) and counts the tests per group (BR1-15). `--list` starts no web server and
   no global setup (BR1 evidence: `runner/index.js:7140-7143`; a run took 4 s).
2. It weighs each group by its **measured seconds per test** times the number of tests the
   `--list` run gives for it now (BR2-02: the same group runs 32 tests at Full and 1 `@device`
   test at Normal on `desktop-chromium × readings.spec.js`, so a stored total alone would skew
   the plan). `scratch/e2e-timings.json` stores, per group, the tests and the seconds of the
   last run that ran it. A group with no measurement uses the mean seconds per test of the
   measured groups, or 3 s per test when nothing is measured.
3. It packs the groups into the lanes, longest first, each into the lane with the least total
   so far (the LPT rule: *longest processing time first*). Lanes = the smaller of `E2E_LANES`
   and the number of groups. `lane_count` and `PROJECT_COUNT` are removed; `run()` stops
   re-reading `E2E_LANES` (`run_lanes.py:315-317` repeats `main()`'s check) (BR1-13).
4. It prints the plan as one line per lane before the lanes start, e.g.
   `lane 1 plan: 3 groups, 84 s (phone-chromium readings.spec.js, …)`.
5. Each lane gets its plan in `E2E_LANE_PLAN` (JSON: project → list of spec file names), and
   runs `npx playwright test` with the run's other arguments. The lane command leaves out the
   spec files and the `--project` arguments, which the plan replaces, and `--shard`. Every other
   argument passes through unchanged: `--grep`, `-g`, `--grep-invert`, `--repeat-each`,
   `--timeout`, `--retries` and the like (BR1-05 point 3). `playwright.config.js`, when
   `E2E_LANE_PLAN` is set, keeps only the plan's projects and gives each its files as
   `testMatch` (a plain file name gets `**/` in front, `lib/util.js:97-105`).
6. After the merge, `run_lanes.py` reads the merged JSON report (a `json` reporter added to
   `playwright.merge.config.js`, written to `scratch/e2e-report/results.json`), counts each
   group's tests that ran and sums their durations, and updates `scratch/e2e-timings.json` with
   both numbers. It writes only the groups that ran and keeps the others.
- **The output lines stay** (BR1-06): `lane <n>: exit … — …` and `All lanes done in N s`, which
  `tooling/steps/step_stats.py` parses (`LANES_DONE`, `step_stats.py:43`).
- **Fallback.** When an argument names a test by line (`x.spec.js:42`), or a positional
  argument is not a plain `*.spec.js` path, the runner uses `--shard` as today, and says so in
  one line: "This run names tests by line, so the lanes are split by Playwright's --shard."
  `E2E_LANES=1` runs the single stack as today.

### 1.6 The release runs the Full level

`tooling/release-tests.bat` (the Release run configs' `TEST_CMD`) runs, on its worktree of HEAD:
1. `tooling\run-tests.bat`, as today;
2. then `tooling\run-e2e-tests.bat --level=full`, **also when step 1 was red**, so one release
   attempt shows every fault;
3. copies the worktree's `scratch\e2e-report\html`, `scratch\e2e-lanes\` and
   `scratch\e2e-backend*.log` (BR1-08) to `scratch\release-tests\e2e\` of the working folder,
   **before** the worktree is removed, also when the e2e run failed;
4. exits 0 only when both are green.

- **The machine's e2e lock must be the working folder's.** Today `run_lanes.py` takes
  `ROOT / "scratch" / "e2e-run.lock"`, with `ROOT` the script's own repo
  (`run_lanes.py:46,58`). In the release worktree that is a different file, so a release run
  and an agent's run could use the same ports and lane databases at once. The lock and
  `e2e-timings.json` move to the main working folder's `scratch/`: the parent of
  `git rev-parse --path-format=absolute --git-common-dir`. Ports, lane databases and the WebKit
  container are per machine, so this one lock is the right scope.
- **The git call** (BR1-04) runs once in `main()`, with `cwd=ROOT`, never at import
  (`tooling/tests/test_run_lanes.py:11` imports the module). When git is not on the path or
  `ROOT` is not in a repository, the lock and the timings stay in `ROOT / "scratch"`, and the
  run says so in one line: "Git did not find the main working folder, so the e2e lock is in
  <path>."
- **`scratch/` is made explicitly** at the start of `main()` (`ROOT / "scratch"` and the main
  folder's), not as a side effect of taking the lock: `scratch/` is gitignored, so the
  worktree has none, and the single-stack path's backend log redirect
  (`playwright.config.js:54`) needs it.
- The release needs the dev DB container (already needed by step 1) and Docker Desktop (the
  WebKit container, S046). When either is missing, the e2e step fails with the existing
  messages, and the release stops before the version bump (`release.py:97-103`).
- The release takes about 6–7 minutes longer.

### 1.7 The rules, rewritten (docs pass)

The run rules written on 25-10-2026 into the coder, the code reviewer, the step skill and
`CLAUDE.md` ("the full suite once when the step's coding is done"; "step agents never run
`phone-webkit`") change as follows (BR1-10):
- The coder runs targeted runs (Normal with spec files) as often as it needs. It may run Basic
  when it wants a quick whole-app check.
- The coder runs the whole suite at Normal once, when the coding is done. It runs it again
  only with a reason it states in the report.
- In a fix round, the coder runs targeted runs only.
- The code reviewer never runs the whole suite. It re-runs only the specs that one of its own
  findings needs.
- The Full level runs only in the release, and when KLA asks.
- `CLAUDE.md` § Browser tests: "never in `run-tests.bat` or the release" becomes "never in
  `run-tests.bat`; at the Full level in the release".
- The "get a new test green alone first" example in `.claude/agents/coder.md` changes from
  `--project=desktop-chromium` to `--project=phone-chromium`, the logic device (BR1-01).

### Out of scope

- S048 *What's new* and S049 the pre-flight skill (own steps).
- Fixing S045's open flakes #2 and #3, or changing what an existing test asserts. This step only
  tags tests, adds the journeys and changes how runs are planned.
- A level for the backend suites (`run-tests.bat` takes about 40 s already).
- Running lanes on another machine or in CI.

## 2. Standards and practice

- **Smoke test** (ISTQB glossary, BR1-12, paraphrased): a small set of tests that covers the
  main functions, run first to decide whether further testing is worth it. Basic is a smoke
  test: a few broad journeys, run first and fast.
- **Regression testing** (ISTQB glossary, paraphrased): running tests again after a change to
  find faults the change brought into unchanged parts. Normal is each step's regression run;
  Full is the release's regression run on every supported device.
- **Test pyramid** (Mike Cohn, *Succeeding with Agile*, 2009): many fast low-level tests, few
  slow end-to-end ones. Yantra's logic is tested in the backend suites (2964 tests); browser
  tests should prove that the screens use it right, once, not test it again per device. This
  step follows that: logic once, layout per device.
- **Risk-based testing** (ISO/IEC/IEEE 29119 Part 1, concepts; no clause number until checked):
  test effort follows risk. Only KLA uses an iPhone, so its tests run once per release; the
  shop floor's Android phones carry every test.
- No maintenance standard (TPM, ISO 14224, EN 13306) applies: this is development tooling.

## 3. Where

| File | Change |
|---|---|
| `tooling/e2e/run_lanes.py` | `--level`; level expansion; `--list` groups; timings; LPT plan and its printed line; `E2E_LANE_PLAN` per lane; no `--pass-with-no-tests` on planned lanes; `--shard` fallback; lock and timings in the main folder's `scratch/`; `scratch/` made explicitly; `lane_count`, `PROJECT_COUNT` and the second `E2E_LANES` read removed |
| `tooling/tests/test_run_lanes.py` | replaced: `TestLaneCount`, `test_lane_count_uses_the_same_parse`; changed: `test_a_second_run_cannot_take_the_lock` (it monkeypatches `LOCK_FILE`, BR1-04). New: level parsing and refusals; an explicit `--project` gets no `E2E_LEVEL`; Basic refuses `--grep`; the packing (LPT, unknown groups, more lanes than groups); the lane arguments (what is removed, what passes through); the fallback; the timings update; the lock path from the common dir and its fallback; no test found → exit 1 |
| `tooling/run-e2e-tests.bat` | header comment: the levels; default Normal |
| `tooling/release-tests.bat` | the Full e2e run after `run-tests.bat`, the report copy, the combined exit code |
| `frontend/playwright.config.js` | `E2E_LEVEL=normal` → `desktop-chromium` `grep: /@device/`; `E2E_LANE_PLAN` → projects and `testMatch` |
| `frontend/playwright.merge.config.js` | a `json` reporter to `../scratch/e2e-report/results.json` |
| `frontend/e2e/journeys.spec.js` | new: the four journeys (§ 1.4) |
| `frontend/e2e/*.spec.js` (the existing specs with a tagged test) | tags only, per § 1.3 |
| `tooling/steps/step_stats.py`, `tooling/tests/test_step_stats.py` | `e2e_invocations` (`step_stats.py:141-152`) counts by level (BR1-06 option a). A run that names a spec file is targeted, at any level. Otherwise: `--level=basic` is basic, `--level=full` is full, and a run with no `--level` is normal when it started after S047's commit, full before it (BR2-03: the same command text meant the whole three-device suite before S047). The column "E2E runs" shows `b/n/t/f`, also in the per-run table (`step_stats.py:368`) and where the per-step cell is built (`:223`). Tests extended: `TestE2e::test_invocations_full_or_targeted` and `test_invocations_in_subshells_and_with_a_timeout` (`test_step_stats.py:88`) (BR2-04) |

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md` § Browser tests: the levels, the tags, the release runs Full, the lock in
  the main folder; § SMTW-Review: the spec-to-step map gains `journeys` S047, and the audit's
  full run means `--level=full`.
- `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`, `.claude/skills/step/SKILL.md`:
  the rules of § 1.7, with the commands.
- `docs/steps/README.md` § Manual checks: the run rule (it still says "the full suite only when
  the step changes shared frontend code").
- No schema, Plan.MD or domain doc is due.

## 4. Design decisions

1. **Logic on one device, layout on every device** (KLA's point 2). Rejected: three levels by
   tag only, every test on two or three devices (the first draft): it kept the triple runs of
   logic tests, which is most of the time.
2. **The Android phone carries the logic**, not desktop: the shop floor's device; it also
   exercises the phone layout. Rejected: desktop (faster rendering, but most users are not on
   it).
3. **`@device` marks the exception by purpose; logic is untagged** (BR1-02 option a). Nearly
   every test is logic; tagging the few layout tests is less churn, and a new test defaults to
   the cheap run. Rejected: (a) tagging every logic test `@core`; (b) tagging every test that
   calls a geometry helper (the literal reading): it would tag most flow tests and bring
   Normal's desktop run back towards today's. **KLA decides this at gate A** (coverage against
   time, § 6 Q1).
4. **Full keeps today's run unchanged** (every test, three devices), so the release still checks
   every dialog of every flow on the iPhone. Rejected: Full = logic once + `@device` on three
   devices: faster, but a dialog met only inside a flow would never be checked at 390 px.
5. **Planned lanes from measured times** instead of `--shard`. Rejected: (a) `fullyParallel:
   true`, which splits files across lanes: the specs keep state across a file's tests
   (`test.beforeAll` in 9 specs) and each lane has its own database, so tests would lose their
   data; (b) splitting large spec files by hand: it drifts as specs grow; (c) Playwright's
   `PWTEST_SHARD_WEIGHTS` (`cli/testActions.js:194`): undocumented, and it still counts tests,
   not time.
6. **The release runs e2e even when the unit suites are red**, so one attempt shows every
   fault. Rejected: skip e2e on red (saves 6 min on a failed release, but hides browser faults
   until the next attempt).
7. **One lock for the machine, in the main folder**, found through git's common dir. Rejected:
   an environment variable set by `release-tests.bat` (another way to get it wrong).
8. **No flag means Normal.** Rejected: Full by default (an agent that forgets the flag would
   start the iPhone).
9. **An explicit `--project` turns the `@device` filter off** (BR1-01). Rejected: keeping the
   filter, which makes a one-test debugging run on desktop run nothing.
10. **Basic refuses a caller's `--grep`** (BR1-05). Rejected: combining both into one regex
    (`(?=.*@smoke)(?=.*S0NN)`): hard to read, and Normal with the spec file already does the job.

## 5. Tests and acceptance

- **Unit (tooling suite, `tooling/run-tooling-tests.bat`):** the tests named in § 3, red first
  where they replace behaviour (the packing, the lock path, the `--project` rule).
- **Runs the coder makes and reports, with counts and times:**
  1. `--level=basic`: the journeys and `screens.spec.js` on `phone-chromium` only, green; time.
  2. Normal, the whole suite: green; the test count per project (`desktop-chromium` runs only
     the `@device` tests); the time; the plan's lane totals. The longest lane should be within
     about 20 % of the shortest, unless one group alone is longer.
  3. `--level=full`: green (`phone-webkit` in the container). The count is the one that
     `npx playwright test --list` gives for all three projects before this step, plus 4 × 3 for
     the journeys (BR1-07: 477 + 12 = 489 on 25-10-2026). Report the time, and the lane balance
     as above.
  4. A targeted run (`e2e/labels.spec.js`): Normal, two projects, no container.
  5. `--project=desktop-chromium e2e/equipment.spec.js -g "S044"`: runs the S044 tests on
     desktop, not zero (BR1-01).
  6. `tooling/release-tests.bat` once on HEAD: both parts run, the report lands in
     `scratch\release-tests\e2e\`, exit 0. And once with an e2e failure forced (a temporary
     wrong assertion, then reverted): exit 1, and the report is still copied.
  7. Two runs at once (one from the release worktree, one from the working folder): the second
     waits for the lock.
- **Accept when:** all four suites are green; the seven runs above give what they state; the
  final `@device` and `@smoke` lists are in the impl report.

### Manual checks

- On a real device: none.
- Automated: the runs above (the coder's, recorded in the impl report).

## 6. Open questions and assumptions

1. **The `@device` rule (§ 1.3, decision 3)**: tag by purpose (23 tests; recommended) or by
   any geometry helper (most flow tests; more desktop coverage at Normal, a longer Normal run).
   KLA decides.
2. **The journeys (§ 1.4)**: are these four the right "one thread" each? Proposed as above.
3. **Basic includes `screens.spec.js`** (each screen opens for each role). Proposed: yes; it is
   broad and short. Alternative: only the four journeys.
4. **Assumption**: the whole suite at Normal takes about 2–3 minutes. The coder measures it; if
   it is over 4 minutes, it reports the slowest groups.

## 7. Amendments

None.

## Review log

### U1 — user answers, 25-10-2026 (before drafting)

- Split: three steps — S047 test levels, S048 What's new, S049 pre-flight skill.
- At the end of coding the coder runs the Normal level (not Full).
- The pre-flight skill does not run the tests; the release does.
- Logic tests on one device; only screen issues on every device (KLA: "Only screen issues need
  to be repeated for all platforms").
- The iPhone only before a release, in the release's own tests.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major: an explicit `--project=desktop-chromium` runs nothing at Normal | Accepted, (a) and (b): `E2E_LEVEL` only when the level chose the projects (§ 1.1, § 1.2, decision 9); planned lanes drop `--pass-with-no-tests` and no test found is exit 1 (§ 1.2); the coder.md example moves to `phone-chromium` (§ 1.7); run 5 in § 5 |
| BR1-02 major: the `@device` rule is ambiguous | Accepted, (a): tag by purpose, with the 19-test list in § 1.3 (helpers inside a flow and a webkit-only skip do not tag); the choice goes to KLA at gate A (§ 6 Q1, decision 3) |
| BR1-03 minor: journey 3 hits the same-minute refusal | Accepted, (a): the sheet's time one minute later and a higher value (§ 1.4) |
| BR1-04 minor: `scratch/` no longer made in the worktree; the git call | Accepted, (a): `scratch/` made explicitly in `main()`; the git call once in `main()`, `cwd=ROOT`, with a fallback and its line; `test_a_second_run_cannot_take_the_lock` named in § 3 (§ 1.6) |
| BR1-05 minor: three argument rules | Accepted: Basic refuses `--grep` (decision 10); `--list` runs with the lanes' `E2E_LEVEL`; the arguments that pass through are named (§ 1.2, § 1.5) |
| BR1-06 minor: `step_stats.py` counts every run without a spec as full | Accepted, (a): counted by level, `b/n/t/f`; the output lines stay; the plan line is new (§ 1.5, § 3) |
| BR1-07 minor: stale counts | Accepted: the Full count from `--list` plus 12 (489 today); `readings.spec.js` 32 tests; Basic about 2 min (§ 1.1, § 1.5, § 5) |
| BR1-08…BR1-15 nits | Accepted, all: backend logs copied (§ 1.6); "back in service" (§ 1.4); § 1.7 in full sentences, one term "the whole suite at Normal"; the five steps' figures named (intro); ISTQB paraphrased, 29119 Part 1 without a clause; `PROJECT_COUNT` and the second `E2E_LANES` read removed (§ 1.5); the order in `main()` (§ 1.2); the JSON fields named (§ 1.5) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor: `screens.spec.js` has 9 tests per project, so the `@device` set is 23 and Basic is 13 | Accepted: § 1.3 (`@smoke` count, the list's title and row), § 6 Q1. (The round-1 answer above says 19; 23 is current.) |
| BR2-02 minor: timings keyed by group alone skew the plan between Normal and Full | Accepted, as recommended: store tests and seconds per group; weight = listed tests × seconds per test (§ 1.5 steps 2 and 6) |
| BR2-03 minor: `step_stats.py` cannot tell a pre-S047 full run from a Normal run by the command | Accepted, as recommended: a spec file makes a run targeted; otherwise the run's start against S047's commit date decides (§ 3) |
| BR2-04…BR2-06 nits | Accepted, all: the extra step_stats tests and lines named (§ 3); the fallback guard stated (§ 1.2); the figures' source named (intro) |

### U2 — approval, 25-10-2026

KLA: "Approved, by purpose, journeys ok, Basic includes screens."
- Q1: `@device` by purpose (the 23-test list of § 1.3).
- Q2: the four journeys of § 1.4 as proposed.
- Q3: Basic includes `screens.spec.js`.
