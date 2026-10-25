```
Step: S057 — The step tools name no repo, and the lift list
Doc: impl-report
Author: Coder (Sonnet)
Date: 25-10-2026
```

# S057 — Implementation report

**Result.** The step tools now read the repo's own values from `.claude/CLAUDE.md` § Step workflow
(six new entries). The seven step test files left `tooling/tests/` for the staging folder, fixed for
`smtw-common`'s layout, and passed from a copy laid out like `smtw-common`. The lift list is below.
Every tool prints the same text for Yantra as before, except the differences listed under *Before
and after*, which come from the change itself or from the live transcript.

## 1. What was built

- `step_facts.py`: `read_step_settings(text)`, `backticked(value)`, `load_step_settings()`, `stop()`;
  `gather()` stops with one line (exit 2) when `docs/steps/INDEX.md` is missing.
- `brief_facts.py`: the folders to search, to look a module up in, and to look a test file up in come
  from *Code folders*; without the entry, the whole repo except `docs/`.
- `step_stats.py`: the browser-run counting reads five `Browser-test …` entries. The counters are one
  `{level: count}` per run; the columns, the header letters and the explanation line are built from the
  levels. Without a wrapper there are no E2E columns.
- `step_check.py`: check 7 is skipped when `docs/steps/device-checks.md` does not exist.
- `render_mockups.mjs`: comments say "the app"; a missing Playwright prints one clear line, exit 1.
- Tests: the seven step test files updated, 25 new tests written, then moved to the staging folder.
- Docs: six entries in § Step workflow; six rows in the README's table, with a rule line.

## 2. How it works

- **Reader.** `read_step_settings` takes the text between `## Step workflow` and the next `## `, and reads
  each line `- **<Entry>**: <value>` (one line per entry, as in `## Pre-flight`). A value `none` is `None`.
  `backticked` returns the backticked words of a value. No section gives `None`.
- **Stop messages.** `load_step_settings()` stops (exit 2, message on stderr) with S056's text when the
  section is missing. `brief_facts.main` and `step_stats.main` call it. `step_ls`, `step_check`,
  `step_feedback` and `step_snapshot` do not read settings, so they still run. `gather()` stops with the
  `INDEX.md` message.
- **Browser runs.** `e2e_config(settings)` returns an `E2eConfig` or `None` (no wrapper or no levels).
  It stops (exit 2) on levels with the same first letter and on a default-level time that is not a date.
  `default_level(config, started)` picks the first history pair whose time is after the run's start (an
  unknown start counts as earliest, as the old code's "full" did), else the first word of the entry.
  A spec-file match counts as `targeted` only when `targeted` is among the levels.
- **Yantra's values** reproduce the old constants: wrapper `run-e2e-tests.bat`, levels
  `basic normal targeted full`, spec `.spec.js`, default `normal` with `full` before
  `2026-10-25T05:50Z`, total line `All lanes done in (\d+) s`.

## 3. Files touched

| File | Change |
|---|---|
| `tooling/steps/step_facts.py` | reader, `backticked`, `load_step_settings`, `stop`, `INDEX.md` check |
| `tooling/steps/brief_facts.py` | folders from *Code folders*; `grep`, `check_*`, `summarise_hits` take them |
| `tooling/steps/step_stats.py` | `E2eConfig`, `e2e_config`, `default_level`; `Run.e2e` dict; report built from levels |
| `tooling/steps/step_check.py` | check 7 skipped without the device-check file |
| `tooling/roadmap/render_mockups.mjs` | comments; Playwright-missing message (loaded in `main`) |
| `tooling/run-tooling-tests.bat` | comment stops naming the step tools; command unchanged |
| `tooling/tests/test_step_*.py`, `test_brief_facts.py`, `test_render_mockups.py` | moved (`git mv`) to `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/` and fixed there |
| `.claude/CLAUDE.md` | six entries in § Step workflow |
| `docs/steps/README.md` | six table rows, the one-line rule, the `INDEX.md` and `device-checks.md` notes |
| `docs/steps/INDEX.md`, `1-brief.md` | status `In code review` |

(Nothing in `tooling/tests/` remains of the step tests; the `git mv` staged the renames in the index.)

## 4. Decisions taken

1. **`stop()` in `step_facts.py`** prints to stderr and raises `SystemExit(2)`; used by the settings
   loader, `gather()` and `step_stats.e2e_config` (small shared helper, no copy).
2. **`E2eConfig` dataclass** carries the five entries to the pure functions, so the tests build one
   from a dict (`e2e_config({...})`).
3. **Unknown start time** of a run takes the earliest history level, which keeps the old tests' result
   (`full`). In production every run with commands has a start.
4. **`targeted` counts only if it is a level**; without it, a spec-file run falls to the default level.
   The brief does not say; this keeps the counters complete.
5. **Playwright loaded inside `main()`** in `render_mockups.mjs`, so importing the module (`VIEWPORTS`,
   `viewportOf`) never exits.
6. **Entry values hold no extra backticks.** Prose beside the backticked words uses plain words, since
   the reader takes every backticked word as data.
7. **README rows and the rule** also say that, with no wrapper, the other four `Browser-test` entries
   are ignored.
8. **The module lookup** applies to the dotless short name (`local_db`), as before; the brief's example
   `run_logged.x` is loose, and the test uses the dotless name.
9. Test name for the renderer's new test is `test_playwright_missing_says_so`; it needs Node only and
   runs in `smtw-common` too.

No departure from the brief.

## 5. Not done, deferred, assumed

- Nothing written to `smtw-common` or any other repo (KLA does the lift).
- **Assumed:** the `Browser-test default level` history is sorted by time ascending; the first pair
  later than the run's start wins.
- **No browser tests are due:** no screen, API or frontend file changed.
- The INDEX row's summary still says "*Browser-test runs*" (the orchestrator's text before U4); not
  touched.

## 6. Tests

- Before the move: `tooling/run-tooling-tests.bat` (run name `s057c1`): **288 passed**: 115 in the seven
  step files (90 before the step plus 25 new tests) and 173 in the five files that stay. The renderer tests **ran, not skipped** (the run of the seven files with `-rs`
  printed no skip; `frontend/node_modules/playwright` exists).
- After the move: `tooling/run-tooling-tests.bat`: **173 passed** (the five remaining files).
- The staged files from a copy laid out like `smtw-common`: **112 passed, 3 skipped** (the three
  renderer tests that need `frontend/`; the new `test_playwright_missing_says_so` ran and passed) — 115
  collected, the same count as before the move. Commands are under *Until the lift*.
- Full suite (`tooling/run-tests.bat`, run name `s057c1`, after the move): backend 3075 passed, frontend 179 passed, deps 42 passed, tooling 173 passed. No frontend build check: no frontend file changed.

### Red then green (new behaviour tests)

The new tests exercise code that did not exist; they could not pass on the old code (the functions are
new). Not applicable as a fix round.

## Before and after

Captured before any change and after, with the tools called directly
(`uv run --no-project python tooling/steps/<script>.py`), in `scratch/s057/before/` and
`scratch/s057/after/`. `feedback` is **identical**. The differences:

| Tool | Differences | Why |
|---|---|---|
| `step-ls all` | rows of the files this step changed (`M .claude/CLAUDE.md`, the tools, `README.md`) and the S057 staged files | the working tree changed by this step |
| `step-check` | 7 more "tree: … no step claims it (10)" lines | the same files, not yet claimed by a committed step |
| `step-stats` (without the "Built" line) | the S057 row, the coder-role row (24 calls instead of 23, 203 min instead of 194), the day's orchestrator row | **this coder run itself** is a live transcript, and it printed "All lanes done in 9 s" while reading code; every other row is equal |
| `step-brief-facts S056` | line counts and line numbers of the changed files; `SEARCH_DIRS` "not found" (removed); the moved test files "no such test file" / fewer test users | the changes themselves (the brief S056 names these constants and files) |

The two § 5 differences did not show in S056's output (it names no `tooling/` module and no test id under
another folder); both are covered by new unit tests
(`test_a_module_is_looked_up_in_each_code_folder_then_in_the_step_tools`,
`test_a_test_id_is_looked_up_at_the_root_then_in_each_code_folder`). Any other difference: none found.

The no-section behaviour is tested: `brief_facts.main` and `step_stats.main` exit 2 with the message;
`step_check.run()` runs without the device-check file.

## Until the lift: testing a step tool from Yantra

The staged tests are not run by any Yantra command. To run them from a copy laid out like `smtw-common`
(in the session scratchpad; delete it after):

```
mkdir proof/tooling/common proof/tooling/steps proof/tooling/roadmap
cp tooling/steps/*.py proof/tooling/steps/
cp tooling/roadmap/render_mockups.mjs proof/tooling/roadmap/
cp -r docs/steps/S057-step-tooling-lift/lift/tooling/common/tests proof/tooling/common/tests
cd proof && uv run --no-project --with "pytest>=8,<10" pytest tooling/common/tests -rs
```

## Docs updated

- `.claude/CLAUDE.md` § Step workflow: the six entries (*Code folders*, *Browser-test wrapper*,
  *Browser-test levels*, *Browser-test spec files*, *Browser-test default level*, *Browser-test total line*).
- `docs/steps/README.md` § The repo's settings and index: the six rows with their `none` behaviour, the
  one-line-of-backticked-words rule, the `INDEX.md` message, the optional device-check file.
- `tooling/run-tooling-tests.bat` comment (see files).
- No schema, plan or domain doc is due (no migration, no module change).

## Manual checks

None in the brief. No browser test is due (no screen changed), and no row goes to the device-check list.

## Lift to smtw-common

Ready to paste. KLA does it; nothing here was written to `smtw-common`.

### 1. Files to copy to the same paths in `smtw-common`

- `.claude/skills/step/` (syncs with the skills folder, no `sync_common.py` entry)
- `.claude/agents/`: `advisor.md`, `brief-reviewer.md`, `code-reviewer.md`, `coder.md`, `roadmapper.md`
- `tooling/steps/`: `brief_facts.py`, `step_check.py`, `step_facts.py`, `step_feedback.py`, `step_ls.py`,
  `step_snapshot.py`, `step_stats.py` (not `__pycache__`)
- `tooling/roadmap/`: `render_mockups.mjs`
- `tooling/step-brief-facts.bat`, `tooling/step-check.bat`, `tooling/step-feedback.bat`,
  `tooling/step-ls.bat`, `tooling/step-snapshot.bat`, `tooling/step-stats.bat`, `tooling/render-mockups.bat`
- `docs/steps/README.md`, `docs/roadmap/README.md`

**The tests:** copy the folder `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/` (seven
files) into `smtw-common`'s `tooling/common/tests/`, as they are (already fixed for that place). In
`smtw-common` `test_render_mockups.py` skips three tests (no `frontend/`). Then delete
`docs/steps/S057-step-tooling-lift/lift/` in Yantra.

**Never copy:** `docs/steps/INDEX.md`, `docs/roadmap/INDEX.md`, `docs/steps/device-checks.md`, the step
folders (`docs/steps/S0NN-*`), `docs/roadmap/R0N-*`, `.claude/CLAUDE.md`.

### 2. `sync_common.py` in `smtw-common`

- `DIRS` gains `(".claude/agents", ".claude/agents")`, `("tooling/steps", "tooling/steps")`,
  `("tooling/roadmap", "tooling/roadmap")`.
- `FILES` gains the seven `.bat` files above and the two READMEs (`docs/steps/README.md`,
  `docs/roadmap/README.md`).

### 3. `tooling/run-common-tests.bat`

No change; it already runs `tooling\common\tests`.

### 4. `smtw-common`'s own docs of what syncs

The "Repository structure" block of `tooling/common/README.md`: mark each new folder and file
"[synced]". The root `CLAUDE.md` § Contents: add the same. (Every SMTW repo receives these files at the
next `sync_all.py`, whether it works in steps or not; a repo opts in by adding a `## Step workflow`
section and `docs/steps/INDEX.md`. Without them `/step` and the two settings-reading tools stop with
their one-line message.)

### 5. `CLAUDE-COMMON.md`: new section

Place it after "Stale bundle detection" under Invariants (or under Defaults; KLA chooses):

```
### Working in numbered steps (optional)

A repo may work in numbered steps with `/step`: a brief, a brief review, the code with an impl report,
and a code review, each in `docs/steps/S0NN-<slug>/`. The skill (`.claude/skills/step/`), the agents
(`.claude/agents/`), the tools (`tooling/steps/`, `tooling/roadmap/` and the `tooling/step-*.bat` and
`tooling/render-mockups.bat` wrappers) and the two READMEs (`docs/steps/README.md`,
`docs/roadmap/README.md`) come from `smtw-common` and are edited there, never in the repo. A repo opts
in with two things of its own: a `## Step workflow` section in its `.claude/CLAUDE.md` (the entries
are listed in `docs/steps/README.md` § The repo's settings and index; one line each, in the form of
`## Pre-flight`) and its `docs/steps/INDEX.md`. The tools' tests live and run in `smtw-common` only
(`tooling/common/tests`, `tooling/run-common-tests.bat`).
```

### 6. After the lift, in Yantra

- `.claude/CLAUDE.md` § Step workflow, first paragraph: add that the skill, the agents, `tooling/steps/`,
  `tooling/roadmap/`, the `tooling/step-*.bat` wrappers, `tooling/render-mockups.bat` and the two
  READMEs come from `smtw-common` and are edited there, not here (a sync overwrites them).
- Delete the staging folder `docs/steps/S057-step-tooling-lift/lift/`.

## Feedback

- hindrance: the Bash tool refused heredocs holding backticks and quotes together ("unexpected EOF"), so four edits needed a script written by the Write tool first (3 failed calls, about 5 min)
- hindrance: `step-stats` and `step-brief-facts` outputs change by themselves when the coder runs (its own live transcript, its own edited files), so a before/after diff cannot be exact (the S057 row, 9 E2E min from a grep of the string)
- idea: the brief could say which settings values the README rows should hold word for word; the README rows and the CLAUDE.md entries had to be written twice from one table
- rule: the brief's example "`run_logged.x`" for the module lookup does not match the code (the lookup uses the part after the last dot); the dotless name is what works

## Fix rounds

### Round 1

- **CR1-01 Fixed.** `e2e_config` in `tooling/steps/step_stats.py` now calls `stop()` (one line, exit 2) when the default level or a history level is not one of the *Browser-test levels*, when the total line is not a valid regular expression, and when it has no group or more than one. Tests in the staged `test_step_stats.py`: `test_a_default_level_that_is_not_a_level_is_refused` and `test_a_total_line_without_one_group_is_refused` (three bad lines: no group, two groups, unclosed). Without the fix both fail (2 failed, the config is built and no `SystemExit` is raised); with it both pass.
- **CR1-02 Fixed.** The `step_stats` docstring now reads "The header shows each level's first letter, e.g. b/n/t/f = basic / normal / targeted / full." No repo name.
- **CR1-03 Fixed.** The S057 row in `docs/steps/INDEX.md` now says six new settings entries and that the tests leave Yantra through the staging folder.
- **CR1-04 Fixed.** The README row *Browser-test spec files* now says a spec-file run is `targeted` only when `targeted` is a level; otherwise it counts at its `--level` or the default level.
- **CR1-05 Fixed.** `render_mockups.mjs` catches only `MODULE_NOT_FOUND` / `ERR_MODULE_NOT_FOUND` for the "Playwright is not installed" message and rethrows anything else (`node --check` ok; no test, the renderer tests skip without Playwright in the copy).

Tests: staged tests from a scratch copy laid out like `smtw-common`: 114 passed, 3 skipped (the renderer, no Playwright); copy deleted. `YANTRA_TEST_RUN=s057c2 tooling/run-tooling-tests.bat`: 173 passed (corrected in Round 2). No browser tests (no screen). Docs updated: `docs/steps/INDEX.md` row, `docs/steps/README.md` row; no other doc due. Nothing staged in git, nothing written to `smtw-common`.

### Feedback

- none

### Round 2

- **CR2-01 Fixed.** The Round 1 test line now says 173 passed. The 263 came from an old log: I read `scratch/tooling-tests.log` (the unnamed run, 19:41), not the log of my run name `scratch/tooling-tests-s057c2.log`.
- **CR2-02 Fixed.** `e2e_config` in `tooling/steps/step_stats.py` stops with one line, exit 2, when *Browser-test default level* has an even number of words (a trailing level with no time): "The browser-test default level ends with full, which has no date and time after it. ...". New test `test_a_level_without_a_time_is_refused` in the staged `test_step_stats.py`. Without the fix it fails (no `SystemExit` is raised, `zip` drops the level); with it, it passes.
- **CR2-03 Fixed.** The docstring in `step_stats.py` is wrapped to the file's line length (the whole paragraph, not only line 25).

Tests: staged tests from a scratch copy laid out like `smtw-common`: 115 passed, 3 skipped (the renderer, no Playwright); copy deleted. `YANTRA_TEST_RUN=s057c3 tooling/run-tooling-tests.bat`: 173 passed (last line of `scratch/tooling-tests-s057c3.log`). No browser tests (no screen). Docs updated: none, because no setting, convention or index row changed. Nothing staged in git, nothing written to `smtw-common`.

#### Feedback

- hindrance: `run-tooling-tests.bat` leaves the unnamed `scratch/tooling-tests.log` next to `tooling-tests-<run>.log`; reading the wrong one gave 263 (1 extra command to find the right log)
