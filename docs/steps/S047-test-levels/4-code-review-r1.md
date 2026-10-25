```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. 1 minor, 4 nits.** The step builds what the
approved brief asks for. The three levels, the `@device` (23) and `@smoke` (13) sets, the four
journeys, the planned lanes, the lock in the main folder and the release's Full run all match
§ 1.1–§ 1.7. The departures D1, D2, D12 and D13 are listed in "Decisions taken" and hold up (see
"Checked and found consistent"). The one minor finding is an error message: a spec file that
cannot load is reported as "No test matches these arguments".

Reviewed: `git diff -w --ignore-cr-at-eol HEAD --` for the files the impl report names, and the
untracked `frontend/e2e/journeys.spec.js` and `3-impl-report.md`. Read in full:
`tooling/e2e/run_lanes.py`, `tooling/release-tests.bat`, `frontend/playwright.config.js`,
`frontend/vite.config.js`, `frontend/e2e/journeys.spec.js`. Not this step's, so not reviewed:
`docs/Plan.MD`, the S050–S053 folders and rows, the status edits in the S040/S044/S045/S046 files.

## Tests

- **Unit suites, my run:** `YANTRA_TEST_RUN=s047cr1 tooling/run-tests.bat`: backend 3012
  passed (58 s), frontend 170 passed (14 s), deps 42 passed, tooling 162 passed (8 s); ALL
  SUITES: PASSED.
- **`npx vite build`** in `frontend/`: built in 3.8 s, only the known chunk-size warning. The
  build does not read `server.fs` or `cacheDir`, so D12 does not change it.
- **Browser tests:** not re-run (standing rule, 25-10-2026). The coder's runs cover the right
  set for this step: Basic, the whole suite at Normal once, Full, a targeted run, an explicit
  `--project` run, `release-tests.bat` green and with a forced failure, and two runs at once
  (impl report § 7). The step changes `playwright.config.js`, so the whole-suite runs are
  justified. My one finding needed no browser run: I checked it with a throw-away Playwright
  config in my scratchpad (below).

## Minor

### CR1-01 — minor — `tooling/e2e/run_lanes.py:454-464`, `:580`: a spec file that cannot load is reported as "No test matches"

- **Problem.** `list_groups` ignores the `--list` run's exit code and the report's `errors`. It
  only checks that the output parses as JSON. When a spec file has a syntax or import error,
  Playwright 1.64.1 lists **no test at all**, from any file, and puts the error in
  `report["errors"]`. I checked this with a scratchpad config (one good spec, one with
  `const x = ;`): exit 1, `errors` = `[SyntaxError: …bad.spec.js…]`, `groups_of(report)` = `{}`.
  `run()` then prints "No test matches these arguments: --project=phone-chromium
  --project=desktop-chromium." and exits 1.
- **Failure scenario.** A coder adds a test with a typo, then runs the targeted specs. The run
  says no test matches the arguments, and the coder looks for a wrong file name or `-g`. The
  real cause, the syntax error, is not printed anywhere. Before S047, every lane printed it in
  its log. The run is not silent, because the exit code is 1, but the message points the
  wrong way. The decision about a failed `--list` (impl report D7) covers only output that is
  not JSON.
- **Fix.** In `list_groups`, return the error when `report.get("errors")` is not empty or
  `listed.returncode != 0`. Join each error's `message` into the text after "The tests could
  not be listed:". Add a `TestRun` test with a report that has `errors` and no suites.

## Nits

- **CR1-02** (nit) `frontend/vite.config.js:32`: base the allowed root on the config's own
  folder (`searchForWorkspaceRoot(fileURLToPath(new URL(".", import.meta.url)))`), not on
  `process.cwd()`. Vite's default uses the config root. Today every start (`npm run dev`, the
  e2e `webServer`) runs from `frontend/`, so nothing is widened. But a start from the repo root
  would allow the whole repo, `backend/secrets_app.py` included, on a server bound to `0.0.0.0`.
- **CR1-03** (nit) `tooling/release-tests.bat:56-63`: when both parts are red, the closing line
  names only the unit suites and drops the e2e report's path. Print both lines, then exit 1, so
  the end of the output shows every fault (design decision 6).
- **CR1-04** (nit) `tooling/release-tests.bat:4`: the header line is about 170 characters long.
  Re-wrap it to the width of the lines around it.
- **CR1-05** (nit) `tooling/e2e/run_lanes.py:551`: when the level did not choose the projects,
  remove `E2E_LEVEL` from `os.environ` (`os.environ.pop("E2E_LEVEL", None)`). An `E2E_LEVEL=normal`
  left in the caller's shell would otherwise filter a `--project=desktop-chromium` run to
  `@device`, which BR1-01 rules out.

## Checked and found consistent

- **Levels** (`read_level`, `expand_level`). No flag is Normal. An unknown value and a bare
  `--level` are refused with "Use --level=basic, normal or full." Basic refuses `-g`, `--grep`
  and `--grep-invert` in both forms, with the brief's line. Basic adds `--project=phone-chromium`
  only when no project is named. Normal adds both Chromium projects and `E2E_LEVEL=normal` only
  when no project is named. Full adds nothing. A refusal returns 1 before the lock or any
  subprocess. `needs_webkit_server` reads the expanded arguments: Basic and Normal start no
  container, Full and a named `phone-webkit` start one.
- **`playwright.config.js`.** The `grep: /@device/` goes on `desktop-chromium` only, and only at
  `E2E_LEVEL=normal`. `E2E_LANE_PLAN` keeps the plan's projects and sets their `testMatch`. With
  neither variable set, the project list is the same as at HEAD.
- **The `--list` plan.** It runs with the expanded arguments and the lanes' `E2E_LEVEL`
  (`os.environ` is updated first). `groups_of` walks nested suites. An empty result gives exit 1
  with its line. One group runs on the single stack.
- **LPT packing.** Groups are taken longest first, ties broken by name, so the plan is the same
  on every run. Lanes = min(`E2E_LANES`, groups). Weight = tests now × measured seconds per test.
  An unmeasured group gets the mean, or 3 s when nothing is measured (BR2-02).
- **Lane arguments.** `split_args` drops `--project` and its names (variadic, as Playwright
  reads it) and keeps the values of `VALUE_OPTIONS`. `lane_arguments` drops `--shard` in both
  forms. Planned lanes run without `--pass-with-no-tests`. A `:line` or a non-spec positional
  goes to the `--shard` fallback, with its line; there `--pass-with-no-tests` stays and the
  merged-totals check guards (BR2-05). A value option missing from `VALUE_OPTIONS` only sends the
  run to the slower fallback, never to a wrong plan (D5).
- **No silent empty run.** `ran` is true when any test in the merged report has a result. A
  merged report with no result prints "No test ran." and exits 1. A run whose tests all failed
  is reported as a failure, not as no test (D13's test).
- **Timings and D13.** Only passed and skipped results are measured. A group with no counted
  test keeps its earlier entry. The file is written inside the lock, and a broken file reads as
  empty. Leaving failed tests out is a sound refinement of § 1.5 step 6: a dead stack times out
  every test, and those times would skew the next plan.
- **Lock and timings path.** `main_scratch` runs `git rev-parse --path-format=absolute
  --git-common-dir` once, in `main()`, with `cwd=ROOT`. The parent of the result is the main
  working folder in both a checkout and a worktree. When git is missing or fails, the run uses
  `ROOT/scratch` and prints the brief's line. `ROOT/scratch`, the shared `scratch/` and
  `scratch/e2e-lanes/` are made before the lock is taken (BR1-04). `TestMainScratch` covers
  all four paths.
- **`release-tests.bat`.** The e2e run (`--level=full`) runs after `run-tests.bat` whatever the
  unit result was. `:copy_e2e_report` runs before `:remove_worktree`, also after a red e2e run.
  It copies the HTML report, the lane logs and `e2e-backend*.log`, and robocopy's bit-mask exit
  code cannot stop the script. The exit code is 0 only when both parts were 0. The junction is
  still removed first and the worktree unlocked after it, as before.
- **D12, `vite.config.js`.** `server.fs.allow` adds only the real `node_modules` path. In a
  normal checkout that path is inside the default root, so nothing changes. In the release
  worktree it is the working folder's `frontend/node_modules`: package files only, which the
  dev server serves anyway. `cacheDir` keeps its default unless `E2E_VITE_CACHE_DIR` is set,
  which only `playwright.config.js`'s `webServer` does (`scratch/e2e-vite<-laneN>`).
  `realpathSync` needs `node_modules`, which every Vite or vitest start has, including the
  Docker build after `npm ci` (`tooling/build/Dockerfile.frontend:6`).
- **D1, `LEVELS_SINCE`.** 25-10-2026 05:50 UTC (11:20 IST), timezone-aware, compared with the
  aware run start that `_time` parses. A run with no start counts as before (full). The
  orchestrator may move it to the commit time; the result is the same for every run but the
  coder's own.
- **D2, temporary commit objects.** No ref holds them: `git for-each-ref` shows only `main`,
  the remotes, the tags and `refs/steps/*`. The index is empty (`git diff --cached`), there is
  no stash, and `git worktree list` shows only the main folder. `%TEMP%\yantra-release-tests` is
  gone.
- **Tags.** `@device` is on the 14 tests of § 1.3 outside `screens.spec.js` plus its 3 tests
  (9 per project), 23 in all. `@smoke` is on the 3 `screens.spec.js` tests (9) and the 4
  journeys, 13 in all. A search of every untagged test title for the rule's words finds only
  logic tests ("Turn on for this phone", "a gauge above its limit", "fitted to a component",
  "Fitted here before"). The journeys are untagged `@device`, as decision 3 wants.
- **Journeys against § 1.4.** (1) The engineer adds the item from the list, opens its page,
  uploads a document and sees one label with its code and QR. (2) The operator raises; the
  engineer assigns Kannan; the technician acknowledges, starts, adds labour, a part and a note,
  and sets *Back in service*; the engineer closes; the operator's *Me* lists it under Closed.
  (3) The supervisor logs 500 on the page two minutes back, then 508 on the sheet one minute
  back; the history has both rows. This avoids `SAME_MINUTE` and keeps the counter rising
  (BR1-03). (4) IT admin adds a manufacturer and a model with a *Run hours* meter; a new item
  of that model shows the meter. Every dialog the journeys open goes through `dialogFrom` or
  `openAction`, which both call `expectDialogFits`. Names carry the project and a run-unique
  suffix. Journey 2 makes its own item through the API when it runs alone (D8).
- **`step_stats.py`.** A spec file makes a run targeted at any level. Otherwise the `--level`
  flag decides, or, with no flag, the run's start against `LEVELS_SINCE`. Both tables show
  `b/n/t/f` through `e2e_runs_text`. The `All lanes done in N s` and `lane <n>: exit …` lines
  are unchanged.
- **Unit tests against § 3.** Levels and refusals, the explicit `--project`, Basic's grep, LPT,
  unknown groups, more lanes than groups, the lane arguments, the fallback, the timings update,
  the lock path and its fallback, and "no test found → exit 1" are all tested. `TestLaneCount`
  is removed. The red-then-green results are recorded for `test_run_lanes.py`, D13's two tests
  and `test_step_stats.py`.
- **Docs pass.** `.claude/CLAUDE.md` (*Release*, *Browser tests*, § SMTW-Review with `journeys`
  S047 and `--level=full`), `.claude/agents/coder.md`, `.claude/agents/code-reviewer.md`,
  `.claude/skills/step/SKILL.md` and README § Manual checks carry the rules of § 1.7. The
  "never in `run-tests.bat`; at the Full level in the release" wording is in place, and the
  coder's new-test example uses `--project=phone-chromium`. No schema, Plan, domain, secrets,
  Keycloak or device-check doc is due.
- **Manual checks.** The brief has no important check and no real-device check. The impl
  report's `## Manual checks` says so and names the coder's runs as the automated checks.
- **Writing style.** The impl report follows scope A. The step adds no screen text. The new
  console lines ("Use --level=basic, normal or full.", the Basic refusal, the fallback line, the
  release's closing lines) are short and say what to do.

## Manual browser check

None. This step changes test tooling only, and the brief lists no real-device check.
