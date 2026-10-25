```
Step: S057 — The step tools name no repo, and the lift list
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: db5b803 + uncommitted S057 (`docs/steps/S057-step-tooling-lift/`, `docs/steps/INDEX.md`); unrelated uncommitted: `docs/roadmap/INDEX.md`, `docs/roadmap/R01-auth-hardening.md`.

**Verdict: no blocker or major finding is open.** Six minor findings and nine nits. The "Today" table is complete apart from one comment in `render_mockups.mjs` (nit). The sync facts, the two named output differences and the pytest basenames check out. The minors are: the *Browser-test runs* entry's grammar (the user's call, Q1), gaps in the lift list, the sync's fan-out to every repo, a traceback in a repo without `docs/steps/INDEX.md`, the renderer test's `ROOT` after the move, and the `none` default of *Code folders*. Facts file: `scratch/brief-facts-S057.md`, used; its "no such file" for `tooling/run-common-tests.bat` is right (the file is in `smtw-common`, verified at `../smtw-common/tooling/run-common-tests.bat`).

## Findings

### BR1-01 — minor — § 1.2: the *Browser-test runs* entry carries a second grammar

**Problem.** *Code folders* is read by one rule: the backticked words of the value. *Browser-test runs* adds a second rule: split at `;`, then a key (the words before the first backtick) and positional backticked values, with one key (`no level`) taking 1 or 3 values. The brief itself calls the form "the most intricate" (Q1) and asks the user. Two details are unstated: a `total line` regex that contains `;` breaks the split, and two levels with the same first letter give the same header letter.

**Why it matters.** Every SMTW repo must write this line by hand; the more syntax inside one value, the more ways to get it wrong, and the reader gives no useful error for a wrong key. It is also the one place where the settings form departs from `## Pre-flight`'s "one bullet, one value".

**Options.**
- (A) Keep the form as proposed. State the two rules: a value never contains `;`, and the levels' first letters must differ (the reader refuses otherwise).
- (B) One entry per value, each read by the same backticked-words rule as *Code folders*: *Browser-test wrapper* (`run-e2e-tests.bat`), *Browser-test spec files* (`.spec.js`), *Browser-test levels* (`basic` `normal` `targeted` `full`), *Browser-test default level* (`normal`; `full` before `2026-10-25T05:50Z`), *Browser-test total line* (the regex). Five bullets, five README rows; `none` on *levels* switches the E2E columns off. **Recommended**: one grammar for every entry, and a wrong value is visible in its own bullet.
- (C) A TOML file (decision 1, rejected; agreed).

This is a judgement call for the user; the brief should put the choice in Q1 with both forms shown.

### BR1-02 — minor — § 1.6: the lift list has three gaps

**Problem.**
1. Item 3 says `smtw-common`'s `tooling/run-common-tests.bat` "also runs `tooling\steps\tests` (the renderer's test skips there: no `frontend/`)". The renderer's test moves to `tooling/roadmap/tests/` (§ 1.5), so it is not run by that line; either add `tooling\roadmap\tests` to item 3 or drop the parenthesis.
2. `smtw-common` documents what syncs in two places the list does not name: `tooling/common/README.md` (the "Repository structure" block, "[synced]" per entry) and its root `CLAUDE.md` § Contents ("When adding a new shared artifact, register it in FILES or DIRS … otherwise it will not reach target projects"). Both need the new folders and files.
3. Decision 4 says "every repo can check the tools it received", but the list does not say how a receiving repo runs them. Yantra has `tooling/run-tooling-tests.bat` (repo-own, rightly not lifted); another repo has nothing. One line in item 4's CLAUDE-COMMON text does it: `uv run --no-project --with "pytest>=8,<10" pytest tooling/steps/tests tooling/roadmap/tests`.

**Why it matters.** § 5 makes the code reviewer check the list for completeness; a list the brief already knows to be short costs a review round.

**Options.** Add the three points to § 1.6 (recommended). Or state that items 2 and 3 are KLA's to work out at lift time.

### BR1-03 — minor — § 1.6, Q3: the sync fans out to every sibling repo

**Problem.** `../smtw-common/tooling/common/sync_all.py` runs `sync_common.py` in every sibling folder that has `tooling/common/sync_common.py` (fact: its docstring, lines 5-22). After the lift, every SMTW repo receives `.claude/agents/`, `tooling/steps/`, `tooling/roadmap/`, the seven `.bat` files, `docs/steps/README.md` and `docs/roadmap/README.md`, whether or not it works in steps. The brief's Q3 only asks whether another repo already has `docs/steps/` (so nothing is overwritten); it does not say that the lift creates `docs/steps/` and `docs/roadmap/` in every repo.

**Why it matters.** KLA decides the lift; he should see that a repo that never uses `/step` gets two `docs/` folders and six step wrappers. The orchestrator's stop message ("no Step workflow section") covers `/step`; the tools' behaviour in such a repo is BR1-04.

**Options.**
- (A) State it in § 1.6 and Q3: the files land in every repo; a repo opts in by adding the section and `INDEX.md`; the README files are the procedure's text and stay. **Recommended** (no code change).
- (B) Put the two READMEs under `.claude/` instead, so `docs/` stays untouched in repos that do not opt in. Rejected by me: the skill, agents and README name `docs/steps/README.md` throughout (S056), and the step folders live beside it.

### BR1-04 — minor — § 1.1: a repo without `docs/steps/INDEX.md` gets a traceback

**Problem.** `step_facts.gather()` (line 166) reads `docs/steps/INDEX.md` with no check; `step_feedback.py` globs `docs/steps/` (line 50, no error, empty). After the lift (BR1-03), `tooling/step-ls.bat` or `step-check.bat` in a repo that has not opted in ends with a `FileNotFoundError` traceback. The brief handles only the missing settings section (exit 2 with S056's message).

**Why it matters.** It is the same case as the missing section (a repo not yet opted in), handled two ways: one plain message, one traceback.

**Options.**
- (A) In `gather()`: when `INDEX.md` is missing, stop with one line, exit 2: "This repo has no docs/steps/INDEX.md. docs/steps/README.md § The repo's settings and index gives its shape." **Recommended**: three lines, and the same place every tool goes through.
- (B) Leave it: the traceback names the file. Acceptable if the user prefers no change beyond the scope.

### BR1-05 — minor — § 1.5: the renderer test's `ROOT` must change too, or the test skips silently

**Problem.** § 1.5 says "Each test's `sys.path.insert` is fixed for its new place". `tooling/tests/test_render_mockups.py` has no `sys.path.insert`; it has `ROOT = Path(__file__).resolve().parents[2]` (line 11). At `tooling/roadmap/tests/test_render_mockups.py`, `parents[2]` is `tooling/`, not the repo root. The test then looks for `tooling/frontend/node_modules/playwright`, does not find it, and **skips** (`needs_node`, line 14-16) rather than fails: the move would quietly switch the test off, and `run-tooling-tests.bat` stays green.

**Why it matters.** The acceptance "the count before plus the new tests" would still hold (a skipped test is counted), so nothing catches it.

**Options.** Say in § 1.5: "`test_render_mockups.py`'s `ROOT` becomes `parents[3]`", and add to § 5 that the moved renderer test runs (not skips) on the dev machine, where `frontend/node_modules/playwright` exists (recommended).

### BR1-06 — minor — § 1.2: the `none` default of *Code folders* counts the step files as code

**Problem.** With `none` or a missing entry, `brief_facts` greps the whole repo. Every brief and review under `docs/steps/` names the code names it discusses, so "used in N code file(s)" would list `docs/steps/S0NN-…/1-brief.md` as a code file, and a name used nowhere in code would read as used.

**Why it matters.** The facts file exists so the brief reviewer trusts its counts; a default that inflates them is worse than no count.

**Options.**
- (A) `none`: grep the whole repo except `docs/` (`git grep … -- . ':!docs'`). **Recommended**: one pathspec, and the README's `none` column says "the whole repo except `docs/`".
- (B) `none`: report paths and test ids only, skip the code-name section. Simpler, but loses the most useful part of the facts file.
- (C) Keep "the whole repo" and say in the README that the step files then count as code files.

## Nits

- **BR1-07** (nit) Today table, row j: `render_mockups.mjs:7-8` also ties the sizes to Yantra's browser-test projects ("the Pixel 7 the logic tests use", "the desktop project"). Keep the sizes; reword to "a Pixel 7-size phone (412 x 915, scale 2) and a 1366 x 768 desktop".
- **BR1-08** (nit) § 1.1: `read_settings` is also the name of `tooling/common/preflight.py:83` (a different signature, `(text, environ)`). Two synced modules, one name, two meanings: call this one `step_settings` or `read_step_settings`.
- **BR1-09** (nit) § 1.2 `no level`: parse the time with `step_stats._time()` (it already maps `Z` to `+00:00`); `datetime.fromisoformat` accepts `Z` only from Python 3.11, and the synced scripts declare `requires-python >= 3.10`.
- **BR1-10** (nit) § 1.5 "the existing level tests, unchanged in result": `test_step_stats.py:86-109` assert the tuple `(0, 0, 2, 1)`; with one `{level: count}` per run the asserts change shape. Say "the same counts, asserted on the dict".
- **BR1-11** (nit) § 5, "The tools with the settings section removed": name the two tools that read an entry and stop (`brief_facts.py`, `step_stats.py`); the other four read no setting and must still run.
- **BR1-12** (nit) § 1.5, new test "`step_check`'s run with no device-check file": `run()` reads git and the real step files, and the existing tests are "no git and no files". Make the skip a pure step (`rows = []` when the file is missing; `check_device_rows` already returns `[]` for empty rows) and test that, not `run()`.
- **BR1-13** (nit) § 1.2: say which module parses the *Browser-test runs* value (step_stats, pure and unit-tested), as § 1.1 does for `read_settings`.
- **BR1-14** (nit) § 1.1 and the README row: say that an entry is one line. PyCharm re-wraps Markdown (README § IDE reformatting); a wrapped bullet would lose the rest of its value to the reader, as it would for `## Pre-flight`.
- **BR1-15** (nit) § 1.6 item 1: "`tooling/roadmap/` (with `tests/`)" — the renderer's test needs `node` and `frontend/node_modules/playwright`, which `smtw-common` has not; say it skips there (it does today: `needs_node`), so a red run in `smtw-common` is not expected from it.

## Checked and found consistent

- **Today table (a–j)**: every line number and value verified in `brief_facts.py`, `step_stats.py`, `step_check.py`, `render_mockups.mjs`. A grep of `tooling/steps/`, `tooling/roadmap/`, the seven `.bat` wrappers and `run-tooling-tests.bat` for repo words (Yantra, vel_, backend, frontend, run-e2e, .spec.js, ports, device-checks) finds nothing else beyond BR1-07's comment; `step_facts.SHARED_DOCS`, `step_snapshot.py:142` and `step_stats.py:310` name convention paths, as the brief says. `run-tooling-tests.bat`'s `YANTRA_*` variables are Yantra's own file, not lifted.
- **The agents, skill and READMEs** name Yantra nowhere (0 hits in the five agent files, `SKILL.md`, both READMEs).
- **Sync facts**: `SELF_SRC` line 22, `FILES` line 25, `DIRS` line 40 with `.claude/skills` whole; `sync_dir` writes and deletes nothing; `../smtw-common/tooling/common/sync_common.py` is byte-identical to Yantra's apart from line endings; `smtw-common` keeps tests in `tooling/common/tests/` and runs them with `tooling/run-common-tests.bat` (`pytest tooling\common\tests`, with `--with python-dotenv`). `smtw-common` has no `.claude/agents/`, `tooling/steps/` or `docs/`, so until the lift a sync touches none of the step files, as § 1.6 says. The hook `.claude/hooks/guard-common.py` guards secrets and SSH only; it needs no change for the lift.
- **The two output differences (§ 5)**: (b) today's module lookup is `("backend", "tooling/steps")`; with the code folders in order it becomes `backend`, `frontend/src`, `frontend/e2e`, `frontend/tests`, `tooling`, `tooling/steps`, so only a module directly under `tooling/` changes (the facts file shows `run_logged.x`: "defined at none found" today). (c) today's test-id lookup is root, `backend/`, `backend/tests/`; the new order keeps those three first, so an id found today is found the same way. `SEARCH_DIRS`, the wrapper regex (prefix allowed), `.spec.js`, the four levels, the `LEVELS_SINCE` time and the lanes regex reproduce today's values; the "b/n/t/f" headers are the levels' first letters.
- **Pytest collection**: no `pytest.ini`, `tox.ini`, `setup.cfg` or `[tool.pytest.ini_options]` at the root or under `tooling/` (the root `pyproject.toml` has none), so the default `prepend` import mode applies; the seven moving basenames (`test_step_facts`, `test_step_feedback`, `test_step_ls`, `test_step_snapshot`, `test_step_stats`, `test_brief_facts`, `test_render_mockups`) are distinct from the five staying (`test_deploy`, `test_preflight`, `test_preflight_stamp`, `test_run_lanes`, `test_run_logged`). `tooling/tests/conftest.py` only adds `tooling/` to `sys.path`; none of the seven imports from `tooling/` directly (each inserts `…/steps` itself), so they need no conftest at their new place. `__pycache__/` is gitignored, so the snapshot and the sync carry none.
- **Citations**: `preflight.py:62-80` (`read_section`), `SMTW-WebApp-Base.md:64` (`frontend/` in the layout), S056 § Out of scope's S057 text, S056 row k (stack words kept), S056 decision 1 ("S057's parsers will read this one the same way", S056 brief line 75), S049's lift-list form (`3-impl-report.md` § Lift to smtw-common). The INDEX row for S057 matches the brief's title and status.
- **Track full, Sonnet, no manual checks**: right for a tooling refactor with a diff-based acceptance; no screen, so no UX section is due. Standards (twelve-factor config, ISO 9001 § 7.5.3) are the same two S056 named and fit.
- **Design**: one reader in `step_facts.py`, pure parsing with the shell kept to reading `CLAUDE.md`; no new abstraction beyond what two tools use; the device-check path kept fixed (decision 5) is right-sized.

## Feedback

- waste: the facts file listed `brief_facts.py` five times and `step_stats.py` four times (once per cited line range), 9 lines for 2 facts (`scratch/brief-facts-S057.md:8-13, 31-32`); one line per file with its ranges would do.
- hindrance: checking `smtw-common` needed six `ls`/`cat` calls into `../smtw-common` because the brief cites it from memory; a facts-run option that lists a sibling repo's files named in the brief (read-only) would save them.
- idea: the facts run could flag a cited test file whose `ROOT`/`parents[n]` depends on its folder depth when the brief moves it (BR1-05 took a manual read of each test's head).
