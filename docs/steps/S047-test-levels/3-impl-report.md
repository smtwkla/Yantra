```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S047 — implementation report

The browser tests now run at three levels, and the lanes are planned from measured times. The whole suite at Normal takes 119 s (186 tests), Basic 49 s (13 tests), Full 320 s (489 tests) once the lane timings are measured. All seven runs of § 5 give what the brief states (§ 7). All four unit suites pass. No app code changed. Departures from the brief, all in Decisions: **D12** two fixes in `frontend/vite.config.js` (dev-server settings) that the release worktree needed, found by the first release runs; **D13** failed tests do not go into the timings; D1 the `LEVELS_SINCE` time; D2 temporary commit objects (on no branch) for the release runs.

## 1. What was built

- **Three levels**, chosen with `tooling/run-e2e-tests.bat --level=basic|normal|full`; no flag is Normal.
  - **Basic**: the 13 `@smoke` tests (4 journeys, 9 `screens.spec.js` tests) on `phone-chromium`.
  - **Normal**: every test on `phone-chromium`; on `desktop-chromium` only the 23 `@device` tests.
  - **Full**: every test on all three projects, `phone-webkit` in its container (unchanged from before).
  - A `--project` the caller names wins: every matching test runs there, with no `@device` filter.
  - Basic refuses a caller's `--grep`, `-g` or `--grep-invert`, with the brief's line.
  - An unknown level stops the run with "Use --level=basic, normal or full."
- **Tags** on 23 existing tests (`@device`; the 9 in `screens.spec.js` also `@smoke`), exactly the list of § 1.3.
- **Four journey tests**, `frontend/e2e/journeys.spec.js`, tagged `@smoke` (§ 1.4).
- **Planned lanes** instead of `--shard`: weighed by measured seconds per test, packed longest first (LPT). The plan is printed, one line per lane, before the lanes start.
- **No silent empty run**: a run that selects no test stops with "No test matches these arguments: …" and exit 1; a lane run in which no test ran ends with "No test ran." and exit 1.
- **The machine's lock and the timings** live in the main working folder's `scratch/`, found through git's common dir, so the release worktree and the working folder share one lock.
- **The release runs Full**: `tooling/release-tests.bat` runs the unit suites, then the e2e run at `--level=full` (also after a red unit run), copies the report and logs to `scratch\release-tests\e2e\`, and exits 0 only when both are green.
- **`/step stats`** counts e2e runs by level: the column is "E2E runs (b/n/t/f)".

## 2. How it works

`run_lanes.py main(args)`, in order:

1. Checks `E2E_LANES` (1–20), as before.
2. `read_level(args)` takes out `--level=…` (default `normal`). `expand_level(level, rest)` returns the Playwright arguments and extra environment:
   - Basic: `--project=phone-chromium` (only when the caller named no project) + the args + `--grep @smoke`; a caller's grep raises `Refused`.
   - Normal with no project named: `--project=phone-chromium --project=desktop-chromium` + the args, and `E2E_LEVEL=normal`.
   - Normal with a project named, and Full: the args unchanged, no `E2E_LEVEL`.
   A refusal prints its line and returns 1 before anything else runs.
3. `E2E_LEVEL` goes into `os.environ`, so the `--list` run and every lane inherit it.
4. `main_scratch()` runs `git rev-parse --path-format=absolute --git-common-dir` once (`cwd=ROOT`); the parent of the result + `scratch` is the shared folder. When git is missing or fails, it uses `ROOT/scratch` and prints the brief's line.
5. Makes `ROOT/scratch`, the shared `scratch/` and `scratch/e2e-lanes/`, then takes the lock `<shared>/e2e-run.lock`.
6. `needs_webkit_server` reads the expanded arguments: Basic and Normal name Chromium projects only, so no container; Full names none, so one (S046 unchanged).
7. `run(args, wanted, <shared>/e2e-timings.json)`:
   - `E2E_LANES=1`: the single stack, as before (no `--list`).
   - Otherwise `npx playwright test --list --reporter=json <args>` (no web server, no global setup; about 4 s). `groups_of` counts tests per (project, spec file), walking nested suites.
   - No group: the "No test matches" line, exit 1. One group: the single stack.
   - `split_args` separates positional arguments from the others (`--project` and its names dropped; a known value option keeps its value). If every positional is a plain `*.spec.js` path, the lanes are planned; otherwise (a `:line`, or a filter word) the fallback line is printed and the lanes use `--shard=n/N --pass-with-no-tests <args>` as before.
   - Planned: `group_weights` = tests now × (seconds ÷ tests) from the timings file; an unmeasured group takes the mean seconds per test over the measured groups, or 3 s when none is. `plan_lanes` packs longest first into the least loaded lane; lanes = min(`E2E_LANES`, groups). Each lane runs `npx playwright test <other args>` (no spec files, no `--project`, no `--shard`, no `--pass-with-no-tests`) with `E2E_LANE_PLAN={project: [files]}`.
   - After the lanes, `merge()` writes the HTML report and, new, `scratch/e2e-report/results.json` (a `json` reporter in `playwright.merge.config.js`). `measured_groups` counts each group's tests that have a result and sums their durations; `updated_timings` replaces those groups in the timings file and keeps the others.
   - The output lines `lane <n>: exit … — …` and `All lanes done in N s` are unchanged (`step_stats.py` parses the second).

`frontend/playwright.config.js` builds its project list from one array: with `E2E_LEVEL=normal`, `desktop-chromium` gets `grep: /@device/`; with `E2E_LANE_PLAN`, only the plan's projects are kept, each with its files as `testMatch` (a plain name matches as `**/<name>`). Without either variable the config is as before.

`tooling/release-tests.bat`: after `run-tests.bat` (exit code kept as `UNIT_RESULT`), it calls the worktree's `run-e2e-tests.bat --level=full` (`E2E_RESULT`), then `:copy_e2e_report` (robocopy of `scratch\e2e-report\html`, `scratch\e2e-lanes\` and `scratch\e2e-backend*.log` into `scratch\release-tests\e2e\`, the folder emptied first), then removes the worktree as before. It prints one closing line and exits 1 if either part was red, else 0.

`tooling/steps/step_stats.py`: `e2e_invocations(commands, started)` returns (basic, normal, targeted, full). A segment with a `.spec.js` is targeted at any level; else `--level=basic|normal|full` decides; with no flag, a run that started at or after `LEVELS_SINCE` is normal, before it full. `Run` has the four counters; both tables show `b/n/t/f` through one helper, `e2e_runs_text`.

## 3. Files touched

- `tooling/e2e/run_lanes.py`: levels, `--list` groups, timings, LPT plan and its line, `E2E_LANE_PLAN`, the `--shard` fallback, the no-test checks, lock and timings in the main folder's `scratch/`, `scratch/` made explicitly; `lane_count`, `PROJECT_COUNT` and the second `E2E_LANES` read removed; docstring.
- `tooling/tests/test_run_lanes.py`: `TestLaneCount` and `test_lane_count_uses_the_same_parse` removed; the lock test takes a path; new `TestLevels` (9), `TestLaneArguments` (4), `TestPlan` (8), `TestTimings` (4), `TestMainScratch` (4), `TestRun` (7).
- `tooling/run-e2e-tests.bat`: header comment (levels, default Normal, planned lanes, the lock).
- `tooling/release-tests.bat`: the Full e2e run, the report copy, the combined exit code, header comment.
- `frontend/playwright.config.js`: projects from one array; `E2E_LEVEL` grep; `E2E_LANE_PLAN` projects and `testMatch`; header comment.
- `frontend/playwright.merge.config.js`: the `json` reporter to `../scratch/e2e-report/results.json`.
- `frontend/vite.config.js` (not in the brief's list, D12): `server.fs.allow` adds the real `node_modules`; `cacheDir` from `E2E_VITE_CACHE_DIR`, default unchanged. `playwright.config.js` sets `E2E_VITE_CACHE_DIR=../scratch/e2e-vite<-laneN>` for its Vite.
- `frontend/e2e/journeys.spec.js`: new, the four journeys.
- `frontend/e2e/equipment.spec.js`, `masters.spec.js`, `me.spec.js`, `notifications.spec.js`, `readings.spec.js`, `tickets-notes.spec.js`, `tickets-raise.spec.js`, `tickets-work.spec.js`: `{ tag: "@device" }` only.
- `frontend/e2e/screens.spec.js`: `{ tag: ["@smoke", "@device"] }` on its three tests (9 per project).
- `tooling/steps/step_stats.py`: counts by level, `LEVELS_SINCE`, `e2e_runs_text`, both table headers, docstring.
- `tooling/tests/test_step_stats.py`: `test_invocations_full_or_targeted` and `test_invocations_in_subshells_and_with_a_timeout` changed to the 4-tuple; new `test_invocations_by_level_after_s047`, `test_the_runs_cell_sums_each_level`.
- Docs: see `## Docs updated`.
- Step files: `1-brief.md` (Status), `docs/steps/README.md` (index row, § Manual checks), this report.

## 4. Decisions taken

1. **D1 — `LEVELS_SINCE` is 25-10-2026 11:20 IST, not S047's commit time** (departure). The brief says "started after S047's commit". The commit does not exist yet, and my own Normal runs (from 11:27) come before it, so they would count as full. 11:20 IST is just before the first run of the new runner; S046's runs ended earlier that morning. The orchestrator may move the constant to the commit time if it prefers; it is one line, `tooling/steps/step_stats.py`.
2. **D2 — the `release-tests.bat` runs used commit objects on no branch** (`git commit-tree` with a temporary index; HEAD, branches and the user's index untouched). `release-tests.bat` tests a commit, and the step's code is uncommitted; its optional argument (`release-tests.bat <commit>`) exists for trying the script out. Each object holds the working tree at the time; the forced-failure object is the same with one wrong assertion in `labels.spec.js` (`"15 labels on 9 sheets"`, 2 s timeout), written from a copy into a temporary index, so the working folder never held it. The objects used: `9ecc8f0` and `e56e61c` (the two red release runs that found D12), `c99270a` (the first green one), `793fd53` (6b, forced failure) and `6e65638` (the final 6a, the code as handed over). Both objects are unreferenced and git's garbage collection removes them; nothing to clean up.
3. **Which tests the timings count** (`measured_groups`). A test skipped at run time counts: the `--list` count that the weight multiplies includes it. **A failed test does not count** (D13, a refinement of § 1.5 step 6, which says "the tests that ran"): the red release runs of D12 wrote their timed-out tests (11 s each) into the timings, and the next plan was off by up to 60 %. A group with no passed or skipped test keeps its earlier timing. "No test ran" is checked separately, on any result.
4. **Fallback lanes are capped at the number of groups** from the same `--list` run (before: `lane_count`'s estimate). One rule for both modes.
5. **`VALUE_OPTIONS`**: the Playwright options whose value is the next argument (`-g`, `--grep`, `--grep-invert`, `--timeout`, `--repeat-each`, `--retries`, `--reporter`, `-j`, `--workers`, `--max-failures`, `--trace`, `--global-timeout`, `--shard`, `--output`). An option missing from it makes its value look like a positional argument, which sends the run to the `--shard` fallback: slower, never wrong. A caller's `--shard` is dropped from planned lanes (the brief: no `--shard` on a planned lane).
6. **`--level` without `=`** is refused like an unknown level.
7. **A `--list` run that fails** (for example a syntax error in the config) stops with "The tests could not be listed:" and its output, exit 1. The brief did not cover it.
8. **Journey 2 runs alone too.** It raises on journey 1's equipment item when journey 1 ran first in the file (the brief's "that equipment"); run alone (`-g journey.2`) it makes its own item through the API. Otherwise a debugging run of journey 2 would fail for a reason outside it.
9. **The journeys' data**: names carry the project and a run-unique suffix; journey 1 and 2 use the operator's unit MCC2 (the operator raises there); journey 3 uses S038's `meterMachine` at MCC1 (API set-up, as the readings spec); the first reading is taken 2 minutes back, the sheet's 1 minute back (both from one `thisMinute()`), so neither is in the future.
10. **Journeys make no `@device` claim**: they are logic tests, so at Normal they run on `phone-chromium` only and at Full on all three (the brief's rule).
11. **Normal's lane times were not kept per lane.** The Full run that followed overwrote `scratch/e2e-lanes/`. The plan's totals (96–100 s) and the wall time (119 s) are reported instead. The Normal run was made before D12's `vite.config.js` change; I did not run it again, because the two release runs on the final code (6a, 6b) ran every Normal test at Full.
12. **D12 — two Vite fixes the release worktree needed** (departure: a file outside the brief's list, `frontend/vite.config.js`; dev-server and test settings only, the production build does not read `server`, and `cacheDir` keeps its default outside the e2e run). Found by the first runs of `release-tests.bat`:
    - **Every e2e test failed** (483 failed, 6 skipped). In the worktree, `frontend/node_modules` is a junction. Vite serves a dependency's files (the Font Awesome fonts) by their real path, which is in the working folder, outside the worktree's allowed folders, so it answered 403, and every test's console watch failed. Fix: `server.fs.allow` = Vite's default root (`searchForWorkspaceRoot`) plus the real `node_modules`. In a normal checkout the second entry is inside the first, so nothing changes there.
    - **One lane's tests all failed** (lane 5: 91 failed, at 11 s each, so the run took 19 minutes). The six lanes' Vite servers share one dependency cache, `node_modules/.vite`. In the worktree the config hash differs, so all six re-optimised at once, and one rename failed with `EPERM`. Through the junction, the worktree also rewrote the working folder's cache. Fix: each stack's Vite has its own cache, `scratch/e2e-vite-lane<n>/` (`E2E_VITE_CACHE_DIR`, set by `playwright.config.js`, read as `cacheDir` by `vite.config.js`). A lane's first start of a version then optimises once, a few seconds.
    Both are test-tooling causes, not app faults, so I fixed them rather than stop; the orchestrator may want KLA to see them at gate B.

## 5. Not done, deferred or assumed

- **The lane plan needs one measured run per group.** The first Full run (run 3) had no WebKit timings, so its lanes ran 4.3 to 6.7 minutes; once the timings held every group, the lanes of a Full run came within 8–15 % (runs 6a, 6b). A new spec file starts at the mean, and a failed run leaves its groups' timings as they were (D13).
- The timings file `scratch/e2e-timings.json` is per machine and not in git, so a fresh checkout plans its first run by the 3 s default.
- S045's open flakes #2 and #3 were not met in these runs.
- No `.bat` test exists for `release-tests.bat`; it is checked by runs 6a and 6b only.

## 6. Tags: the final lists

`npx playwright test --list -g @device --project=phone-chromium`: **23 tests in 9 files**, exactly § 1.3's list; none added or left out by the rule. I checked every test title against the rule's words (fits, in view, on screen, scroll, sideways, above, below, phone, desktop, iPhone) and every branch on the project or the viewport:

| Spec | Line | Test |
|---|---|---|
| `equipment.spec.js` | 36 | S003: the Add equipment dialog fits |
| `equipment.spec.js` | 44 | S026: the server's refusal … is on screen |
| `equipment.spec.js` | 177 | S029: the bulb is in view without scrolling … |
| `masters.spec.js` | 142 | operator: the failure codes are read-only, and the lists fit a phone |
| `me.spec.js` | 138 | S031: the three tabs fit the screen width |
| `notifications.spec.js` | 104, 112, 241 | S021: the iPhone Home Screen step; blocked notifications (desktop); the manifest (branches on `phone-webkit`) |
| `readings.spec.js` | 395 | S040: Save readings is disabled while saving, and the bar is above the bottom nav |
| `tickets-notes.spec.js` | 108 | S027: Save note with an empty field … in view |
| `tickets-raise.spec.js` | 87, 141 | S026: … scrolls the raise form …; S018 A1: … the fields fit … |
| `tickets-work.spec.js` | 123, 491 | S026: Add labour … scrolls the dialog … (branches on `phone-webkit`); S034: … the reason is above the date |
| `screens.spec.js` | 79, 92, 103 | the 9 tests (7 roles, lost headers, S040 bottom bar), also `@smoke` |

Left untagged on purpose (the rule's exclusions): `notifications.spec.js:87`, `:153` (skip `phone-webkit` only); `readings.spec.js:189`, `:358`, `:654` and `equipment.spec.js:344` (tap-target sizes inside flow tests); `tickets-work.spec.js:81` (one box comparison inside a flow test); `tickets-raise.spec.js:22` (`expectNoSidewaysScroll` inside a flow).

`--list -g @smoke --project=phone-chromium`: **13 tests in 2 files** (`journeys.spec.js` 4, `screens.spec.js` 9).

## 7. The runs of § 5

Every run used the dev DB container; Docker Desktop for run 3 and the release runs.

| # | Command | Result | Time |
|---|---|---|---|
| 1 | `run-e2e-tests.bat --level=basic` | 13 passed, `phone-chromium` only; no container; 2 lanes (plan 38 s / 12 s) | 49 s |
| 2 | `run-e2e-tests.bat` (whole suite, Normal) | 182 passed, 4 skipped = 186: `phone-chromium` 163 (159 + 4 journeys), `desktop-chromium` 23 (the `@device` tests); no container | 119 s |
| 3 | `run-e2e-tests.bat --level=full` | 482 passed, 7 skipped = **489** (477 + 12, as § 5 expects); `phone-webkit` in the container | 411 s |
| 4 | `run-e2e-tests.bat e2e/labels.spec.js` | 4 passed; Normal names both Chromium projects, but `labels.spec.js` has no `@device` test, so one group ran on the single stack; no container | 21 s |
| 5 | `run-e2e-tests.bat --project=desktop-chromium e2e/equipment.spec.js -g S044` | 5 passed on `desktop-chromium` (not zero: no `@device` filter with an explicit project) | 23 s |
| 6a | `release-tests.bat 6e65638` (D2; the code as handed over) | unit suites green (backend 3012, frontend 170, deps 42, tooling 162), then Full: 482 passed, 7 skipped = 489; "Release tests: all green.", exit 0; report, lane logs and the six backend logs in `scratch\release-tests\e2e\`; worktree removed | unit suites about 2 min, then e2e 12:44:34–12:49:59 (lanes 320 s) |
| 6b | `release-tests.bat 793fd53` (forced failure) | unit suites green; Full: 3 failed (the forced `labels.spec.js:40` on each project), 479 passed, 7 skipped; "Release tests: the browser tests failed. Report: …", exit 1; the report was still copied (`scratch\release-tests\e2e\html\index.html`, 12:39) | e2e 338 s |
| 7 | run 6b's e2e (worktree) and `run-e2e-tests.bat e2e/asset-list.spec.js` (working folder), started at 12:34:04 while 6b's lanes ran | the working-folder run printed "Another e2e run is in progress on this machine; waiting for it to finish." at 12:34:07, 6b's lanes ended at 12:39:38, then it ran: 3 passed, finished 12:40:01 | — |

**Lane balance.**
- Run 2 (Normal), the plan: 100, 97, 97, 97, 97, 96 s, within 4 %; `phone-chromium readings.spec.js` alone is the longest group (100 s). Wall time 119 s.
- Run 3 (Full), the plan: 189, 185, 187, 183, 190, 184 s; actual lanes 6.7, 5.8, 4.3, 5.0, 4.7, 6.1 min (longest 56 % above shortest), because the WebKit groups were not measured yet (§ 5).
- Run 6b (Full, timings measured by the green release run before it), the plan: 301, 300, 301, 302, 305, 305 s; actual lanes 4.9, 4.9, 4.8, 4.8, 5.5, 5.0 min (longest 15 % above shortest).
- Run 6a final (Full), the plan: 270, 270, 271, 269, 274, 272 s; actual 4.9, 5.0, 5.2, 5.2, 5.1, 4.8 min (longest 8 % above shortest); 320 s in all, against S046's 384 s for 27 fewer tests.
- The plan's totals are below the actual lane times by about 30 s: each lane's stack start and the `beforeAll` hooks are not in the measured seconds (as the brief accepts). They are the same for every lane, so the balance holds.
- The red release runs of D12 are not in this table: `9ecc8f0` (483 failed, the 403s), `e56e61c` (lane 5's 91 failed, the cache race; 1141 s), and the first green one, `c99270a` (489, 401 s, lanes 4.0–6.5 min, planned from the timings the red runs had written; this led to D13).

Also run while building (targeted, not in § 5): `e2e/me.spec.js e2e/screens.spec.js e2e/tickets-notes.spec.js`, 31 passed, 1 skipped, 6 planned lanes, 61 s (it first wrote the timings file and `results.json`); `e2e/journeys.spec.js --project=phone-chromium -g S047` on one lane, 4 passed, 31 s (the new test green alone first); `e2e/journeys.spec.js --project=desktop-chromium -g journey.2` on one lane, 1 passed (journey 2 alone, D8).

**Unit suites**, `YANTRA_TEST_RUN=s047c1 tooling/run-tests.bat`, once at the end: backend 3012 passed (57 s), frontend 170 passed (14 s), deps 42 passed, tooling 162 passed (8 s); ALL SUITES: PASSED. `npx vite build`: built, only the known chunk-size warning.

**Red, then green** (the tests that replace behaviour):
- `test_run_lanes.py` against HEAD's `run_lanes.py`: 35 failed, 16 passed (the levels, the plan, the timings, the lock path and `run()` do not exist there; `test_a_second_run_cannot_take_the_lock` fails on the new `lock_file` argument). With the new file: 51 passed.
- D13's two tests (`TestTimings::test_a_failed_test_is_not_measured`, `TestRun::test_a_run_whose_tests_all_failed_is_a_failure_not_no_test`) with the change undone (every result counted; "ran" taken from the measured groups): both failed, the first with `(1, 11.0) != (1, 1.0)`. With the change: 53 passed.
- `test_step_stats.py` against HEAD's `step_stats.py`: 4 failed (`test_invocations_full_or_targeted`, `test_invocations_by_level_after_s047`, `test_the_runs_cell_sums_each_level`, `test_invocations_in_subshells_and_with_a_timeout`), 12 passed. With the new file: 16 passed.

## Manual checks

- On a real device: none (the brief has none; no row added to `device-checks.md`).
- Automated: the runs of § 7 above, made by the coder. No Playwright test asserts them; they are runs of the tooling itself.

## Docs updated

- `.claude/CLAUDE.md`: § Yantra Specifics, *Browser tests*: the levels, the tags and their rule, planned lanes, `results.json` and the timings, the lock in the main folder, who runs which level, "never in `run-tests.bat`; at the Full level in the release". *Release*: `TEST_CMD` now runs the unit suites, then Full, with the report copy, the combined exit code and the `server.fs.allow` note (D12). The lanes' list gains the per-lane Vite cache `scratch/e2e-vite-lane<n>/` (D12). § SMTW-Review, *Browser tests*: the map gains `journeys` S047; a state-of-the-suite run is `--level=full`.
- `.claude/agents/coder.md`: the new-test-alone example on `--project=phone-chromium`; the levels; the `@device` rule for new tests; targeted runs, optional Basic, the whole suite at Normal once, fix rounds targeted only, never Full. The 25-10-2026 lines ("the full suite once", "never `phone-webkit`") replaced.
- `.claude/agents/code-reviewer.md`: *Which browser tests a step needs*: the levels, the coder's runs, the reviewer re-runs only its findings' specs, Full only in the release; a wrong or missing `@device` tag as a finding (nit / minor).
- `.claude/skills/step/SKILL.md`: fix-lane step 3 (the whole e2e suite at Normal); § Phase 2 step 3, *Browser runs at their level*; the gate-B summary line; the worktree note (the lock is in the main folder).
- `docs/steps/README.md` § Manual checks: the levels, the coder's and the reviewer's runs, Full in the release (the old "full suite only when the step changes shared frontend code" replaced).
- `docs/Plan.MD` shows as changed in the working folder; that edit is not mine (another session).
- Not due: `docs/schema.*` (no migration), `docs/Plan.MD`, the domain docs, `example_secrets_app.py`, `docs/Keycloak.md`, `device-checks.md` (no device check).

## Fix rounds

### Round 1 (code review r1)

Five findings, all fixed. Test run name `s047c2`.

- **CR1-01 (minor) — Fixed.** `list_groups` (`tooling/e2e/run_lanes.py`) now returns an error when the report's `errors` is not empty or the `--list` exit code is not 0. The text is each error's `message`, or Playwright's stderr when there is none, then `(playwright --list exit code N)`. `run()` prints it after "The tests could not be listed:". New `TestListGroups` in `tooling/tests/test_run_lanes.py`: a load error is returned with its message, a failed list with no message reports the exit code, a good list still returns the groups. Fails without the fix: `assert {} is None` (both error tests; the old code returned `{}` and run() said "No test matches"). Passes with it.
- **CR1-02 (nit) — Fixed.** `frontend/vite.config.js`: `searchForWorkspaceRoot(fileURLToPath(new URL(".", import.meta.url)))` replaces `process.cwd()`. Checked by the targeted browser run below (the dev server starts and serves the app). No unit test: the config is not testable without a server, and the failure needs a start from the repo root.
- **CR1-03 (nit) — Fixed.** `tooling/release-tests.bat` sets `RELEASE_RESULT`, prints the unit line and the browser line when both parts failed, then exits with `RELEASE_RESULT`. Not run (the brief and the task rule out a `release-tests.bat` run); the change is two `set` lines and an `exit /b`.
- **CR1-04 (nit) — Fixed.** The header line of `release-tests.bat` is re-wrapped to the width of its neighbours.
- **CR1-05 (nit) — Fixed.** `main()` runs `os.environ.pop("E2E_LEVEL", None)` before it applies the level's environment. New tests in `TestLevels`: an inherited `E2E_LEVEL=normal` with `--project=desktop-chromium` reaches `run()` as unset (fails without the fix: `assert 'normal' is None`; passes with it), and a Normal run with no project still sets `normal`.

Runs: `tooling/run-tests.bat`: backend 3012 passed (104 s), frontend 170 passed (14 s), deps 42 passed, tooling 167 passed (8 s); ALL SUITES: PASSED. Browser: `e2e/labels.spec.js` at Normal, 4 passed on `phone-chromium` (it has no `@device` test, so `desktop-chromium` ran none). No Full run, no `release-tests.bat` run.

Docs updated: none, because no fix changes a behaviour that a doc describes (the changes are an error message, a safer path setting, the release script's closing lines, a line width and an environment guard).

### Round 2 (code review r2, async)

One finding, fixed. Test run name `s047c3`.

- **CR2-01 (minor) — Fixed.** `list_groups` (`tooling/e2e/run_lanes.py`) now runs `playwright test --list --pass-with-no-tests --reporter=json`, so an empty selection exits 0 and `run()` prints "No test matches these arguments: <args>." and returns 1. A spec with a syntax error still reports its error (CR1-01: the `errors` check is unchanged). The lane commands still carry no `--pass-with-no-tests` (an empty planned lane is a fault); the existing `TestRun` tests check that. New test `TestListGroups::test_the_list_command_passes_with_no_tests` checks the `--list` command line. Fails without the fix: `assert '--pass-with-no-tests' in 'npx playwright test --list --reporter=json -g nothing'`; passes with it.

Runs: `tooling/run-tooling-tests.bat`: 168 passed (7 s). Real check: `tooling/run-e2e-tests.bat e2e/labels.spec.js -g "no such test xyz"` printed "No test matches these arguments: --project=phone-chromium --project=desktop-chromium e2e/labels.spec.js -g "no such test xyz"." and exited 1; no server started. No other browser run.

Docs updated: none, because the change only affects an exit path of a test tool that no doc describes.
