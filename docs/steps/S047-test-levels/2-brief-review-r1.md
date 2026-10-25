```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (no step code is uncommitted; the 25-10-2026 run-rule edits to `.claude/CLAUDE.md`, the two agents, the step skill and `docs/steps/README.md` are uncommitted docs)

**Verdict: two `major` findings are open.** BR1-01: at Normal, an explicit `--project=desktop-chromium` run gets the `@device` filter too, so the brief's own debugging example runs zero tests and `--pass-with-no-tests` calls it green. BR1-02: the `@device` rule tags by any "in view" assertion, which `expectFieldMessage` is, so it would tag most refusal tests; the candidate list misses the tests that match the rule as written. The Playwright behaviour the design relies on holds (evidence below). Facts file: `scratch/brief-facts-S047.md`, used; the names it does not list (`filterForShard`, `PWTEST_SHARD_WEIGHTS`, `--list`, `testMatch`, the grep combination) are checked here against `frontend/node_modules/playwright/lib`.

## Evidence for the Playwright 1.64.1 claims

| Claim in the brief | Holds? | Where |
|---|---|---|
| A project-level `grep` filters that project only; a CLI `--grep` combines with it as "both" (§ 1.2, U5) | Yes | `runner/index.js:2648-2655`: the project grep is applied in `createProjectSuite` per project; `:6647-6653`: the CLI grep is a separate `preOnlyTestFilters` entry. Both must pass. |
| `--grep @smoke` matches a tag | Yes | both filters match `test._grepTitleWithTags()` (`:2651`, `:6651`) |
| `--list` starts no web server and no global setup (§ 1.5 step 1, U4) | Yes | `:7140-7143`: in list mode the tasks are `createLoadTask` and `createReportBeginTask` only; no `createPluginSetupTasks` (the web-server plugin) and no `createGlobalSetupTasks`. Run here: `npx playwright test --list --reporter=json` took 4 s, exit 0, no backend started. |
| `--list --reporter=json` gives per-project, per-file counts | Yes | the JSON has `suites[].specs[].file` (e.g. `readings.spec.js`), `specs[].tags`, and `tests[].projectName`. Today: **477 tests in 36 groups** (12 files × 3 projects, 159 per project). |
| `testMatch` with a plain file name per project (§ 1.5 step 4) | Yes | `lib/util.js:97-105`: a string pattern without `**/` gets `**/` prefixed and is matched with minimatch (`nocase`), so `"readings.spec.js"` matches. |
| `{ tag: "@device" }` syntax | Yes | tags since 1.42; the repo's `test` is `base.extend(...)` (`e2e/support/test.js:6`), which keeps the signature. |
| `filterForShard` gives a group to the lane where it starts (§ 1.5) | Yes | `runner/index.js:2462-2490` (the `position >= from && position < to` test on the group's first test). `PWTEST_SHARD_WEIGHTS` at `cli/testActions.js:194`. |
| S046's lanes 100 / 52 / 99 / 52 / 101 / 51 | Yes | `scratch/s046-full-e2e.log:4-9`; 455 passed + 7 skipped = 462, 384 s |
| `git rev-parse --path-format=absolute --git-common-dir` | Holds | git 2.45.1 here (`--path-format` needs 2.31); from the main folder it prints `C:/Users/KLA/PycharmProjects/Yantra/.git`. From a linked worktree git prints the main repository's `.git` (that is what the common dir is). Not run from a worktree: creating one would write to `.git`. |

## Findings

### BR1-01 — major — At Normal, an explicit `--project=desktop-chromium` runs nothing, and the lanes call it green

**Problem.** § 1.2 sets `E2E_LEVEL=normal` for every Normal run, and the config then gives `desktop-chromium` `grep: /@device/`. § 1.1 says an explicit `--project` wins over the level's devices, but the grep stays. The brief's own example, `--project=desktop-chromium e2e/x.spec.js -g "S0NN"`, then combines the project grep (`@device`) with the CLI grep (`S0NN`) as "both" (evidence above), and an untagged test matches nothing. `run_lanes.py:229` adds `--pass-with-no-tests` to every lane, so the lane exits 0 with no test run, and the run reports green.

**Why it matters.** The coder's rule "get a new test green alone first" (`.claude/agents/coder.md:98-105`) uses exactly this form, with `--project=desktop-chromium`. A coder would see a green run of zero tests and move on. A reviewer re-running one test on desktop would too.

**Options.**
- (a) **Recommended.** `E2E_LEVEL=normal` (the desktop `@device` filter) is set only when the level chose the projects, that is when the caller named no `--project`. A caller who names projects gets every matching test on them, as today. State it in § 1.2 and test it in `test_run_lanes.py`.
- (b) Keep the filter and drop `--pass-with-no-tests` when the caller named a spec file or a grep, so an empty lane fails with Playwright's "No tests found" message. Safer than today in every case, but it still refuses the one-test debugging run.
- (c) Both (a) and (b).

Either way the docs pass must change the example in `coder.md:102-104` to the logic device, `--project=phone-chromium` (the brief's Normal device), and say when desktop gets every test.

### BR1-02 — major — The `@device` rule is ambiguous and the candidate list misses tests that match it

**Problem.** § 1.3 rule 1 tags a test that "asserts a size, position, scroll or 'in view' (`toBeInViewport`, `boundingBox`, `scrollWidth`, a 'fits' title)". `expectFieldMessage` (`e2e/support/dialogs.js:72-75`) **is** `toBeInViewport`, and `expectDialogFits` is three `boundingBox` checks. Both are called in most flow tests of 9 specs (facts file: `expectDialogFits` in 9 test files). Read literally, rule 1 tags most refusal tests and every dialog flow, and Normal's desktop run grows back towards today's. Read as "the test's purpose", it tags a dozen. The candidate list in § 1.3 follows neither reading: it omits tests that match the rule as written, among them:

- `tickets-raise.spec.js:141` "S018 A1: Already fixed with a start time; **the fields fit** …" (`expectNoSidewaysScroll`, `toBeInViewport` on Save) — a "fits" title, the brief's own criterion;
- `readings.spec.js:395` "S040: Save readings is disabled while saving, and **the bar is above the bottom nav**" (Save's box against the nav's box);
- `equipment.spec.js:44` "S026: the server's refusal of a field at the bottom of the Add equipment dialog **is on screen**";
- the tap-target tests: `readings.spec.js:189, 358` and `:654` (S040 A1, `height ≥ 44` and `expectNoSidewaysScroll`), `equipment.spec.js` `expectTouchTarget` (`:257-260`);
- `tickets-raise.spec.js:22` "S017: raise from the equipment page …" (`expectNoSidewaysScroll` at `:26`);
- `tickets-work.spec.js:81` "engineer: Close waits for the labour …" (`:90-91`, the action bar above the Times card), `:491` "S034: a production slot … the reason is above the date" (`:500-501`);
- `notifications.spec.js:180` (the Remove confirmation `toBeInViewport`, `:192`).

Rule 2 ("a branch or skip on `testInfo.project.name`") over-tags: `notifications.spec.js:87` and `:152` only `test.skip` on `phone-webkit`; they are logic tests, and `@device` would run them on desktop for nothing.

**Why it matters.** Which tests carry `@device` decides Normal's time, which is the point of the step. Left as is, the coder decides the reading alone, and the two readings differ by perhaps 60 desktop tests per run.

**Options.**
- (a) **Recommended: tag by purpose.** A test is `@device` when (1) its title names a layout check (fits, in view, on screen, no sideways scroll, above the nav, tap target), or its main assertion is a geometry; (2) it runs only on, or asserts differently on, a project other than `phone-chromium` (`notifications.spec.js:104, 112, 241`, `tickets-work.spec.js:123`); (3) it is in `screens.spec.js`. A `test.skip` that only excludes `phone-webkit` does not count. Calls to `expectDialogFits`, `expectFieldMessage`, `expectNoSidewaysScroll` or `expectTouchTarget` inside a flow test do not tag it: Full checks those per device once per release (design decision 4 already says so). The brief lists the set; the coder confirms it with `npx playwright test --list -g @device` and reports additions.
- (b) Tag by any geometry assertion (the literal rule 1). More desktop coverage at Normal, a longer Normal run. If KLA prefers coverage, say so and drop the "cheap by default" claim of § 1.3.

This is a judgement for the user (coverage against time), so it is not a nit.

### BR1-03 — minor — Journey 3 runs into the same-minute refusal

**Problem.** § 1.4 journey 3: the supervisor logs a counter reading on the equipment page, then fills the unit's sheet and saves. Both forms default *Time taken* to now. A second reading of the same meter at the same minute is refused (`readings.spec.js:532` "a reading already at that minute is refused on its own row", `SAME_MINUTE`; S039/S040 rule). Within one test the two saves fall in the same minute most of the time, so the journey fails on its second step. A counter must also go up.

**Why it matters.** The coder would find it on the first run and choose a fix alone.

**Options.** (a) **Recommended:** the sheet's *Time taken* is set one minute later than the first reading (the specs' `setEventTime` helper), and the counter value is higher. (b) The sheet reads a second meter of the same equipment (a gauge), and the history check is per meter. State the choice in § 1.4.

### BR1-04 — minor — The lock move removes the side effect that creates the worktree's `scratch/`

**Problem.** `scratch/` is gitignored, so the release worktree has none. Today `one_run_at_a_time` makes it (`run_lanes.py:259`, `LOCK_FILE.parent.mkdir`). With the lock in the main folder (§ 1.6) that no longer happens in the worktree. The lanes path still creates it (`run_lanes.py:224`, `LANE_LOGS.mkdir(parents=True)`) before the backend's `> ../scratch/e2e-backend-lane<n>.log` redirect (`playwright.config.js:54`) needs it. The single-stack path (`run_lanes.py:320-323`, `lanes == 1`) creates nothing, so in a fresh worktree the backend log redirect fails and the web server does not start.

**Why it matters.** The release runs Full with 6 lanes, so it would not hit this today; a `--list` with one group, or `E2E_LANES=1` in the worktree, would.

**Options.** (a) **Recommended:** `run()` makes `ROOT / "scratch"` at its start, stated in § 1.6, not left to a side effect. (b) Leave the lanes-only behaviour and say so in the brief.

Two related rules for the same paragraph: the git call runs with `cwd=ROOT`, once in `main()`, not at import (`tooling/tests/test_run_lanes.py:11` imports the module); when git is not on the path or `ROOT` is not a repository, the lock falls back to `ROOT / "scratch"` and the run says so in one line. The test `test_a_second_run_cannot_take_the_lock` (`test_run_lanes.py:46`) monkeypatches `LOCK_FILE`; the brief's § 3 should name it among the tests that change.

### BR1-05 — minor — Three argument rules the coder would settle alone

**Problem.**
1. **Basic plus a caller's `-g`.** Playwright takes one `--grep`; the last one wins. Basic adds `--grep @smoke`, so `--level=basic -g "S0NN"` runs either the smoke set or the S0NN tests, not both.
2. **The `--list` run's environment.** § 1.5 step 1 says `--list` runs "with the run's arguments". It must also run with the lanes' `E2E_LEVEL`, or at Normal the desktop groups are weighed by all their tests and the plan is skewed (the lanes still run the right tests; only the balance is off).
3. **Which arguments a lane keeps.** § 1.5 step 4 removes spec files and `--project`; it should say that `--grep`, `-g`, `--grep-invert`, `--repeat-each`, `--timeout` and the like pass through unchanged.

**Why it matters.** Each is a one-line rule; without it the coder guesses, and the tests in § 3 cannot check it.

**Options.** For 1: (a) **Recommended:** at Basic a caller's `--grep` is refused with one line ("Basic runs the smoke set; name a level without `--grep`, or run Normal with the spec file"); (b) combine both into one regex `(?=.*@smoke)(?=.*S0NN)`. For 2 and 3: state them.

### BR1-06 — minor — `step_stats.py` counts every run without a spec file as "full"

**Problem.** `e2e_invocations` (`tooling/steps/step_stats.py:141-152`) counts a `run-e2e-tests.bat` call with no `.spec.js` argument as a full run. After this step a `--level=basic` run and the Normal whole-suite run would both count as "full", and the stats column "E2E runs (full/targeted)" would mix three things. § 3 leaves it at "to verify".

**Why it matters.** `/step stats` is how KLA judges the cost this step is meant to cut; the column must tell Normal from Full.

**Options.** (a) **Recommended:** count by level: `basic` / `normal` (no spec file) / `targeted` (spec files) / `full` (`--level=full`); one more column or a `b/n/t/f` cell; `test_step_stats.py::TestE2e::test_invocations_full_or_targeted` extended. (b) Keep two columns, "full" meaning `--level=full` only, Normal whole-suite runs counted as targeted. Either way the brief should say that the output lines `lane n: exit … — …` and `All lanes done in N s` stay (`LANES_DONE`, `step_stats.py:43` parses the second), and that the plan is printed as a new line before them.

### BR1-07 — minor — Stale counts in the acceptance

**Problem.** § 5 run 3 accepts a Full count "equal to today's run (462 with the journeys added: 462 + 4 × 3)". The suite has **477** tests now (159 per project; S044 added 15 since S046's 462), so Full should give 489. § 1.5 says `readings.spec.js` has 33 tests; it has 32. § 1.1 estimates Basic at "about 1 min"; four journeys of about 30 s each are one group on one lane, so about 2 min, plus `screens.spec.js` on another lane.

**Why it matters.** A coder matching 474 against 489 would look for a fault that is not there.

**Options.** (a) **Recommended:** "the count the `--list` run gives for all three projects, plus 4 × 3", and "about 2 min". (b) Update the numbers to 489 and 32.

## Nits

- **BR1-08** (nit) § 1.6 step 3: copy `scratch\e2e-backend-lane*.log` too; a web server that failed to start is explained only there.
- **BR1-09** (nit) § 1.4 journey 2: "marks it done" is not the app's term; write "puts it back in service" (EN 13306: restoration), as `tickets-work.spec.js` does.
- **BR1-10** (nit) § 1.7: telegraphic list items ("fix rounds: targeted only;"). Write them as full sentences, and use one term for the Normal whole-suite run throughout ("the whole suite at Normal"); "full suite" only inside the quoted old rules.
- **BR1-11** (nit) Intro: "at least 1.7 of 6.8 agent hours" matches no five rows of `scratch/step-stats.md` (S040–S046 give 6.5 h and 108 min). Name the rows or the sum.
- **BR1-12** (nit) § 2: the ISTQB glossary wording differs between versions; cite the version or paraphrase without quotation marks. For ISO/IEC/IEEE 29119-1 write "Part 1, concepts" without a clause number until checked.
- **BR1-13** (nit) § 3 `run_lanes.py`: `PROJECT_COUNT` goes with `lane_count`; `run()` re-reads `E2E_LANES` (`run_lanes.py:315-317`, a copy of `main()`'s 299-301) and can lose the copy in the same edit.
- **BR1-14** (nit) § 1.1 / § 1.2: state the order in `main()`: the level is expanded first, `needs_webkit_server` then reads the expanded arguments, so `TestWebkitServer::test_a_full_run_needs_it` keeps passing and Normal starts no container.
- **BR1-15** (nit) § 1.5 step 1: name where the plan reads the data: `specs[].file`, `tests[].projectName`, `specs[].tags` of the JSON (confirmed above), so the coder does not search for it.

## Checked and found consistent

- Track: full is right (`playwright.config.js` is shared test config; the release's tests change; about 22 files).
- `e2e_backend.py` paths are worktree-relative (`REPO`, `DATA_DIR` made with `os.makedirs`), `playwright.config.js` `REPORT_DIR` and the blob dirs are relative to the worktree's `frontend/`, the compose file carries `name: yantra-dev`, so the worktree's copy addresses the same dev DB container; `playwright_version()` reads through the `node_modules` junction. Only `scratch/` itself is at risk (BR1-04).
- `release-tests.bat` can call the worktree's `run-e2e-tests.bat`: `npx playwright install chromium` and `npx vite` resolve through the junction (vitest already does), `uv run --project ../backend` uses the worktree's `.venv` built by `run-tests.bat`, and `release.py` aborts on a non-zero `TEST_CMD` before the version bump (`release.py:97-103`), with no timeout on the test step.
- The lock in the main folder is the right scope: ports 5011–5030 / 5181–5200, the lane databases and the WebKit container (`127.0.0.1:3999`) are per machine.
- Rejected `fullyParallel: true` is right: `test.beforeAll` in 9 specs, one database per lane.
- Design decision 4 (Full unchanged) keeps every `expectDialogFits` on the iPhone once per release.
- The tests the brief names as replaced (`TestLaneCount`, `test_lane_count_uses_the_same_parse`) are the ones that call `lane_count`; `TestWebkitServer` stays valid with BR1-14's order.
- Journey 4: IT admin may add equipment (`config_rbac.py:96`, `equipment:edit` includes `it_admin`) and edit masters (`:134`).
- Standards: a smoke test, regression testing, the test pyramid and risk-based testing are the right names for the three levels; no maintenance standard applies to test tooling.
- Manual checks: none on a real device is right; the coder's six runs are the automated checks.
- No Plan.MD decision is touched; the quote "Shop floor on phones (mobile-first)" is exact (`docs/Plan.MD:20`).
