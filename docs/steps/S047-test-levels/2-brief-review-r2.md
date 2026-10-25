```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (no step code is uncommitted; the 25-10-2026 run-rule edits to `.claude/CLAUDE.md`, the two agents, the step skill and `docs/steps/README.md` are uncommitted docs)

**Verdict: no `blocker` or `major` finding is open.** Three `minor` findings: the `@device` list says 19 tests but `screens.spec.js` has 9 tests per project, so the set is 23 (BR2-01); the lane timings keyed by group alone skew the plan between a Normal and a Full run (BR2-02); the `step_stats.py` counting rule cannot tell a Normal run from a pre-S047 full run (BR2-03). Every round-1 answer marked `Accepted` is in the brief text (list at the end). Facts file: `scratch/brief-facts-S047.md` (round-1 draft), used for file and name existence; the names it does not list were checked against the code and a `npx playwright test --list` run (477 tests, 4 s, no stack started).

**Re-read this round** (the orchestrator's list): the intro figures; § 1.1; § 1.2; § 1.3; § 1.4 journeys 2 and 3; § 1.5 steps 1, 3–6, the output lines and the fallback; § 1.6; § 1.7; § 3 rows for `run_lanes.py`, `test_run_lanes.py`, `step_stats.py`; § 4 decisions 3, 9, 10; § 5 runs 3 and 5; § 6. The brief folder is untracked, so there is no git diff of the brief; the comparison is against the sections the Review log names and round 1's text. Not re-reviewed: § 2, § 4 decisions 1, 2, 4–8, Out of scope, § 1.4 journeys 1 and 4.

## Findings

### BR2-01 — minor — The `@device` list counts `screens.spec.js` as 5 tests; it has 9

**Problem.** § 1.3 says "the 5 tests of `screens.spec.js`", the table row says "all 5", and the heading says "The list (19 tests)"; § 6 Q1 and decision 3 carry "19 tests" to KLA. `npx playwright test --list` gives 9 tests per project in `screens.spec.js`: `every screen opens as <role>` for 7 roles (`screens.spec.js:79`, a loop over the role keys), `a request that lost its test headers gets no access, never admin` (`:92`), and `S040: the manager's bottom bar …` (`:103`). The 14 single rows of the table are right (each title checked at its line; the three `notifications.spec.js` rows and `tickets-work.spec.js:123` branch on the project as stated). So the set is 14 + 9 = **23**, and Basic runs 9 + 4 = 13 tests on `phone-chromium`, not 9.

**Why it matters.** The number is what KLA weighs at gate A (coverage against time). The coder's `--list -g @device` check would give 23 and report a difference that is not one.

**Options.** (a) **Recommended:** write 23 and "the 9 tests of `screens.spec.js` (7 roles, the lost-headers test, the S040 bottom bar)" in § 1.3, decision 3 and § 6 Q1. (b) Drop the count and keep the rule and the rows only.

### BR2-02 — minor — A group's measured time skews the plan when Normal and Full runs alternate

**Problem.** § 1.5 step 2 weighs a group (project × spec file) by "its measured time from the last run that ran it", and step 6 writes the groups that ran. At Full, `desktop-chromium` × `readings.spec.js` runs 32 tests (about 90 s); at Normal the same group runs its one `@device` test (`readings.spec.js:395`, a few seconds). After a release's Full run, the next Normal run plans that group at the Full time and puts it on a lane alone; after a Normal run, the next Full run plans it at one test's time and overloads its lane. The key is the same group, but the test set differs by level.

**Why it matters.** Balance is the point of § 1.5; the imbalance returns exactly in the release-then-coder sequence the brief sets up. Correctness is not affected.

**Options.** (a) **Recommended:** store for each group the tests run and the seconds (`{"desktop-chromium readings.spec.js": {"tests": 32, "seconds": 91}}`), and weigh a group as the test count the `--list` run found × (seconds ÷ tests). Step 2's rule for unmeasured groups already works this way, so one rule covers both. (b) Key the timings by level as well (`normal` / `full`), so each level keeps its own measurements; a new level's first run falls back to the mean. (a) is one rule and one file shape; state it in § 1.5 steps 2 and 6 and in the § 3 test list ("the timings update").

### BR2-03 — minor — `step_stats.py` cannot tell a Normal run from a pre-S047 full run

**Problem.** § 3 (row `step_stats.py`) counts a run as `normal` when it has "no spec file" and as `full` when it has `--level=full`, then says "A run logged before S047 (no `--level`, no spec file) counts as full, as before". A Normal run after S047 is also "no `--level`, no spec file" (decision 8: no flag means Normal), so the two rules name the same command text. The parser (`e2e_invocations`, `step_stats.py:141-153`) sees only the command. Also unstated: a run with both `--level=full` and a spec file (full or targeted?).

**Why it matters.** `/step stats` is how KLA compares the cost before and after this step; the "E2E runs" column must not count S040's 1 full run as normal, nor a coder's Normal run as full. Left as is, the coder picks a rule alone.

**Options.** (a) **Recommended:** the run's start time decides: a no-flag, no-spec run started before S047's commit counts as full, after it as normal. `step_stats.py` already has each run's start (the per-run table's *Started* column), so this is one dated constant with a comment naming S047. (b) Count every no-flag, no-spec run as normal and accept that earlier steps' full runs read as normal (simpler; the before/after comparison is lost in that column, the *E2E min* column is unaffected). For the second point: a spec file makes a run targeted at any level, since the question the column answers is "how much of the suite ran". State both in § 3.

## Nits

- **BR2-04** (nit) § 3 row `step_stats.py`: `test_invocations_in_subshells_and_with_a_timeout` (`test_step_stats.py:88`) also asserts the two-value tuple and breaks with the new shape; name it. The per-run table (`step_stats.py:368`, "E2E (full/targeted, min)") and `run.e2e_full, run.e2e_targeted` (`:223`) change with the column; name them so the coder does not change one table and not the other.
- **BR2-05** (nit) § 1.2 "No silent empty run": in Playwright 1.64.1 the "No tests found" error is raised only without `--shard` (`runner/index.js:6666`: `!testRun.config.config.shard` is in the condition). So in the `--shard` fallback `--pass-with-no-tests` changes nothing; say that the merged-totals check is the only guard there, so the coder does not look for a flag that does something.
- **BR2-06** (nit) Intro: `scratch/step-stats.md` as it stands holds S040 only (built 25-10-2026 10:49 for one step: 47 min of 2.6 h, which matches). The other four rows cannot be checked from the file. Name the build the figures came from, or rerun `tooling/step-stats.bat` for the five steps before approval. The sums hold (28 + 47 + 5 + 12 + 8 = 100; 1.8 + 2.6 + 0.8 + 0.9 + 0.7 = 6.8 h = 408 min).

## Round-1 answers checked in the text

Every `Accepted` answer is in the brief, not only in the Review log: BR1-01 (§ 1.1 last bullet, § 1.2 step 2, "No silent empty run", § 1.7 last bullet, decision 9, § 5 run 5); BR1-02 (§ 1.3 purpose rule, the exclusions, the list, decision 3, § 6 Q1); BR1-03 (§ 1.4 journey 3: one minute later via `setEventTime`, which exists at `e2e/support/tickets.js:93`, and a higher value); BR1-04 (§ 1.6: `scratch/` made in `main()`, the git call once with `cwd=ROOT`, the fallback line; § 3 names `test_a_second_run_cannot_take_the_lock`); BR1-05 (§ 1.2 Basic refuses `--grep`; § 1.5 step 1 `E2E_LEVEL` on the `--list` run; step 5 names the pass-through arguments; decision 10); BR1-06 (§ 3 `b/n/t/f`; § 1.5 the output lines stay, the plan line); BR1-07 (§ 1.1 Basic about 2 min; § 1.5 `readings.spec.js` 32; § 5 run 3 477 + 12 = 489); BR1-08 (§ 1.6 step 3 `e2e-backend*.log`, which matches the lane logs `e2e-backend-lane<n>.log`); BR1-09 (§ 1.4 "back in service"); BR1-10 (§ 1.7 full sentences, one term "the whole suite at Normal"); BR1-11 (intro figures named; see BR2-06); BR1-12 (§ 2 paraphrased, "Part 1, concepts"); BR1-13 (§ 1.5 step 3, § 3); BR1-14 (§ 1.2 the order in `main()`); BR1-15 (§ 1.5 step 1 `tests[].projectName`, `specs[].file`).

## Checked and found consistent

- The `--list` run today: 477 tests, 159 per project, 36 groups; `readings.spec.js` 32; the 14 single `@device` rows name real tests at the lines given, and each meets the rule stated (title words, or a `test.skip` / branch on `phone-webkit` or `desktop-chromium`). The tests round 1 named as matching the literal rule (`equipment.spec.js:344` with `expectTouchTarget`, `readings.spec.js:654` with the 44 px check, `notifications.spec.js:180`, `tickets-work.spec.js:81`) are flow tests whose title names no layout check, so the purpose rule leaves them untagged, as § 1.3 says. `notifications.spec.js:87` and `:153` skip only `phone-webkit` and stay untagged, as stated. No title names a tap target, so the rule's word list loses nothing by omitting it.
- § 1.2 step 3: `TestWebkitServer::test_a_full_run_needs_it` (`test_run_lanes.py:67`) asserts `needs_webkit_server([], "")`, which an expanded Full argument list keeps true; Basic and Normal expand to Chromium names, which `test_a_run_without_phone_webkit_starts_none` already covers.
- § 1.2 and § 1.5: the project `grep` and the CLI `--grep` combine as "both" (round-1 evidence); `E2E_LEVEL` is inherited by the lanes and the `--list` run alike; the planned lane has no `--shard`, so a lane with no matching test does fail with "No tests found" (`runner/index.js:6666-6674`), as "No silent empty run" relies on.
- § 1.5 step 5: `createFileMatcher` (`lib/util.js:97-105`) prefixes `**/` to a plain pattern, so the `--list` JSON's `specs[].file` (`readings.spec.js`) works as `testMatch`. Step 6: the summed test durations leave out each lane's stack start and the `beforeAll` hooks; the stack start is one per lane whatever the plan, so the plan loses nothing by it.
- § 1.5 step 3: `run()` re-reads `E2E_LANES` at `run_lanes.py:315-317`, a copy of `main()`'s 299-301; `lane_count` (`:90`) and `PROJECT_COUNT` (`:57`) have no other caller than the two tests § 3 names as replaced.
- § 1.6: `ROOT` at `run_lanes.py:46`, `LOCK_FILE` at `:58`; `test_run_lanes.py:11` imports the module, so the git call must not run at import; `playwright.config.js:54` redirects the backend log into `../scratch/`; `release.py:97-103` aborts on a non-zero `TEST_CMD` before the version bump. The git common dir from a linked worktree is the main repository's `.git` (round 1), so its parent is the working folder.
- § 1.7 and § 3 Docs: the texts to change exist as quoted: `.claude/CLAUDE.md:29` ("**never** in `run-tests.bat` or the release"; "the **full** suite **once** when the step's coding is done"), `coder.md:102-104` (`--project=desktop-chromium`), `code-reviewer.md:56-57`, `SKILL.md:317-323`, `docs/steps/README.md:147-151`.
- § 3 `step_stats.py`: `e2e_invocations` at `:141-153`, `LANES_DONE` at `:43`, the column at `:297`, `TestE2e::test_invocations_full_or_targeted` at `test_step_stats.py:81`.
- § 5 run 3: 477 + 4 × 3 = 489 holds today. Run 5 is the BR1-01 case and now runs the S044 tests on desktop with no `@device` filter.
- Messages the run prints (scope B): the unknown-level line, the Basic refusal, the fallback line, the git fallback line and the no-test line each say what happened and what to do, with no code or field name.
- Track: full is still right; no screen, so no UX check; standards unchanged from round 1.
