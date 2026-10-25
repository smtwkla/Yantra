```
Step: S057 — The step tools name no repo, and the lift list
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S057 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 minor findings and 3 nits. The tools give the same output for Yantra as before, the staged tests pass from a copy laid out like `smtw-common`, and the lift list is complete.

Reviewed against: db5b803 + the uncommitted S057 changes (`git diff HEAD -M`; the unrelated R01 roadmap files were left out).

## Tests run

- `tooling/run-tooling-tests.bat`, `YANTRA_TEST_RUN=s057cr1`: **173 passed** (the five files left in `tooling/tests`).
- The staged tests, from a copy laid out like `smtw-common` in the session scratchpad (`tooling/steps/`, `tooling/roadmap/`, `tooling/common/tests/`), with `uv run --no-project --with "pytest>=8,<10" pytest tooling/common/tests -rs`: **112 passed, 3 skipped**. The three skips are the renderer tests that need `frontend/node_modules/playwright`. This is the coder's count. The copy was deleted after the run.
- The renderer in Yantra: `node tooling/roadmap/render_mockups.mjs` on a one-file folder in `scratch/` rendered the PNG, exit 0. Playwright still loads now that it is loaded inside `main()`.
- **Old and new `step_stats` compared directly.** I ran HEAD's `step_stats.py` and `step_facts.py` (from a copy in `scratch/`) and the new ones on the same 390+ stored runs, in one process, for the whole report and for `S047`. The order was new, old, new. Every line is equal except "Built …". A first run in the order old, new showed one difference, the day's orchestrator tokens. That line comes from the live session transcripts, and it was equal when the run was repeated.
- Full unit suite: not run. No backend or frontend file changed. The coder's full run is in the report (backend 3075, frontend 179, deps 42, tooling 173).
- Browser tests: none due (no screen or API changed). None run.

## Findings

### CR1-01 (minor) A typo in two Browser-test entries crashes `/step stats` with a traceback

`tooling/steps/step_stats.py:192`, `:230`, `:227`, `:154`.

**Problem.** `e2e_config` stops with a clear message for two wrong values: levels that share a first letter, and a time that is not a date. Two other wrong values are not checked:
- A default level, or a history level, that is not one of the *Browser-test levels*. `e2e_invocations` then does `counts[unflagged] += 1` and raises `KeyError`.
- A *Browser-test total line* with no group. `e2e_seconds` then calls `match.group(1)` and raises `IndexError` (an invalid regular expression raises `re.error` in `e2e_config`).

**Failure scenario.** A repo writes `- **Browser-test default level**: `norml``. `/step stats` builds the config, then fails with `KeyError: 'norml'` at the first run with no flag. I checked both cases in a short script (`CRASH KeyError 'norml'`; `CRASH IndexError no such group`). The README promises a one-line stop for wrong settings, and every SMTW repo receives this tool at the lift.

**Fix.** In `e2e_config`, call `stop()` with one line each:
- when the default level, or a history level, is not in `levels`;
- when the total line does not compile, or has no group (`re.compile(...).groups != 1`).

Add one test for each case to the staged `test_step_stats.py`.

### CR1-02 (minor) The synced `step_stats.py` names Yantra

`tooling/steps/step_stats.py:25`.

**Problem.** The module docstring says "Yantra: b/n/t/f = basic / normal / targeted / full." The step's goal is that the step tools name no repo (title, § 1). This file goes to every SMTW repo at the lift.

**Failure scenario.** A developer in another repo reads `step_stats.py` and finds Yantra's levels described as if they were the tool's own. This is the same kind of leak as row j's "look like Yantra", which this step removed from `render_mockups.mjs`.

**Fix.** Write "e.g. b/n/t/f = basic / normal / targeted / full" without the repo's name, or remove the sentence. The README already gives the example.

## Nits

- **CR1-03** (nit) `docs/steps/INDEX.md:65`: the S057 row still says "two new settings entries (*Code folders*, *Browser-test runs*)" and "the step tools' tests move beside them". Since U3 and U4 it should say six entries, and that the tests leave Yantra through the staging folder. The coder changed the row's status, so the row is its to update (README § Gates, last line).
- **CR1-04** (nit) `docs/steps/README.md` row *Browser-test spec files*: add what decision 4 does. When `targeted` is not one of the levels, a run that names a spec file counts at its `--level` or at the default level.
- **CR1-05** (nit) `tooling/roadmap/render_mockups.mjs:47`: the bare `catch {` reports every `require` failure as "not installed". Catch only `err.code === "MODULE_NOT_FOUND"` and rethrow anything else, so a broken install shows its real cause.

## The coder's decisions

| # | Decision | Judgement |
|---|---|---|
| 1 | A shared `stop()` in `step_facts.py` | **Right.** One helper for the three stop messages, so no copy. |
| 3 | An unknown start time takes the earliest history level | **Right.** It reproduces the old `None → full`, and the direct comparison above confirms it. |
| 4 | A spec-file run is `targeted` only when `targeted` is a level | **Right.** Every run still lands in a column, and the brief is silent on this case. The README should say it (CR1-04). No question for the user. |
| 5 | Playwright loaded inside `main()` | **Right.** Importing `VIEWPORTS` / `viewportOf` never exits, and rendering still works (checked). |
| 8 | The brief's `run_logged.x` vs the code's last-dot lookup | **Right.** The code looks up `x.py` after the last dot, as it did before S057. The brief's example is a slip in the brief, not a departure. The test uses the dotless `run_logged`. No question for the user. |

None of the five needs the user. Decisions 2, 6, 7 and 9 are within the brief.

## The checks you asked for

- **Before and after captures** (`scratch/s057/before`, `scratch/s057/after`), each difference explained:
  - `feedback`: identical.
  - `ls` and `check`: only S057's own working-tree changes (the "no step claims it" lines and the staged renames).
  - `stats`: only the S057 row, the coder role row (+1 call, +9 min) and the day's orchestrator tokens. These come from the coder's live transcript. The direct comparison above shows that no counting changed.
  - `brief-facts S056`: line counts, line numbers, the removed `SEARCH_DIRS` and the moved test files. All of these follow from the change itself.

  The two differences § 5 expects do not show for S056. Unit tests cover both, and I read those tests.
- **`step_stats` with Yantra's five entries** reproduces:
  - `--level=(basic|normal|full)`, built from the levels without `targeted`;
  - `\.spec\.js\b`;
  - the wrapper pattern;
  - `full` before `2026-10-25T05:50Z` and `normal` after;
  - the lanes total line, with Playwright's line as the fallback;
  - the `b/n/t/f` headers and cells, including the spaces.

  The `none` and missing defaults follow § 1.2. With no wrapper or no levels there are no E2E columns. With no spec-file entry no run is targeted. With no default level, the first level other than `targeted` is used. Each has a test.
- **Staged tests fixed for `smtw-common`:** `parents[2] / "steps"` in six files and `parents[3]` for the renderer's `ROOT`. They ran green from the `smtw-common`-shaped copy (above). No Yantra command collects them, because `run-tooling-tests.bat` runs `tooling\tests` only.
- **The lift list (§ 1.6)** is complete. The skill and the five agents name these paths:
  - the six `tooling/step-*.bat`, `tooling/render-mockups.bat` and `tooling/steps/step_snapshot.py`;
  - `docs/steps/README.md`, `docs/roadmap/README.md`;
  - the repo-own files, which are rightly on the "never copy" list: `INDEX.md` ×2, `.claude/CLAUDE.md`, the step and roadmap folders.

  The tools import only `step_facts`, `step_snapshot` and the standard library. The wrappers call only `tooling\steps\*.py` and `tooling\roadmap\render_mockups.mjs`. No repo-own file is on the list. `.claude/CLAUDE-COMMON.md` and `.claude/SMTW-WebApp-Base.md` already sync. Nothing in `.claude/`, the READMEs or `tooling/` still names `tooling/tests/test_step_*`.
- **The docs pass:**
  - § Step workflow's six entries are one line each. Their only backticked words are the values. They match what `backticked()` parses, as the direct comparison shows.
  - The README has six rows, each with its `none` behaviour, plus the one-line rule, the `INDEX.md` message and the optional device-check file.
  - No schema, plan or domain doc is due.

## Manual browser checks for the user

None. The brief lists no manual checks, and no screen changed.

## Checked and found consistent

- `read_step_settings` handles these cases:
  - the section ends at the next `## `, and a `###` heading stays inside it;
  - `none` and `` `none` `` read as `None`;
  - CRLF line endings;
  - a missing file reads as no section.
- `brief_facts.py` and `step_stats.py` stop with S056's message, exit 2. The other four tools never read the settings (grep of `load_step_settings`).
- `gather()` stops with the `INDEX.md` message, exit 2.
- `step_check.run()` skips check 7 without `device-checks.md`.
- `brief_facts`:
  - with no *Code folders*, `git grep` runs on `. ':!docs'`;
  - modules are looked up in each code folder, then in `tooling/steps`;
  - test files are looked up at the root, then in each `<folder>/` and `<folder>/tests/`.
- The `run-tooling-tests.bat` command is unchanged and only its comment changed.
- The impl report has a `## Docs updated`, a `## Manual checks` (none), the lift list, and the commands for testing until the lift.
- Scope: nothing was built beyond the brief, and nothing was written to `smtw-common`.

## Feedback

- hindrance: `git diff -w` hid a space in the `step_stats` row format, so I suspected an output change that was not there; I settled it from HEAD's source and the exact capture diff (3 extra commands).
- idea: give `step_stats.build_report` a `--compare-with <dir>` mode, or keep a small script in `scratch/`, that runs the old and new modules in one process; the before/after capture can never be exact for `stats`, because the coder's own transcript changes it (this run: about 5 min to write one).
- rule: the brief's § 5 says "any other difference is a defect", but `step-stats` and `step-brief-facts` always differ by the step's own transcript and files; § 5 could name those differences as expected (S057 impl report, Feedback item 2).
