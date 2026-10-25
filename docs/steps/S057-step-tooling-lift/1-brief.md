```
Step: S057 — The step tools name no repo, and the lift list
Doc: brief
Author: Orchestrator (Opus)
Date: 25-10-2026
Track: full
Status: Gate B (CR r1 and r2: 0 blocker, 0 major; fix rounds 1 and 2 done)
Baseline: db5b803 (brief-review r1; uncommitted changes were S057's own step files and the unrelated R01 roadmap files)
```

# S057 — The step tools name no repo, and the lift list

**The need (KLA, 25-10-2026).** "We can prepare step skill for lifting" — to `smtw-common`, so the
other SMTW apps use the same workflow. KLA chose two steps (S056 U1): S056 made the prose generic and
put Yantra's values in `.claude/CLAUDE.md` § Step workflow (done, 713fbd6); **S057 makes the tools
generic and writes the lift list**. S056 § Out of scope names this step's part: "`step_stats.py`'s
browser-test parsing and `brief_facts.py`'s `SEARCH_DIRS` (`backend`, `frontend/src`, …) read from
the settings; the `.bat` wrappers; the lift list and the `sync_common.py` change".

**Today** (facts, read at db5b803). The step tools are generic except for these lines:

| # | Where | Yantra value in the code |
|---|---|---|
| a | `tooling/steps/brief_facts.py:29` | `SEARCH_DIRS = ("backend", "frontend/src", "frontend/e2e", "frontend/tests", "tooling")` |
| b | `tooling/steps/brief_facts.py:116` | a module is looked up in `("backend", "tooling/steps")` |
| c | `tooling/steps/brief_facts.py:165` | a test id's file is looked up at the root, `backend/` and `backend/tests/` |
| d | `tooling/steps/step_stats.py:48` | `LANES_DONE`: the line "All lanes done in N s" of Yantra's lane runner |
| e | `tooling/steps/step_stats.py:55` | `E2E_WRAPPER`: `run-e2e-tests.bat` |
| f | `tooling/steps/step_stats.py:57-58` | `SPEC_ARG` (`.spec.js`) and `LEVEL_ARG` (`--level=(basic\|normal\|full)`) |
| g | `tooling/steps/step_stats.py:59-61, 150-165` | `LEVELS_SINCE` (S047's runner, 25-10-2026 05:50 UTC): no flag is `full` before it, `normal` after |
| h | `tooling/steps/step_stats.py:168-171, 186-191, 313-317, 386` | the four counters `e2e_basic` … `e2e_full` and the "b/n/t/f" headers |
| i | `tooling/steps/step_check.py:168` | reads `docs/steps/device-checks.md` and fails when it is missing |
| j | `tooling/roadmap/render_mockups.mjs:3, 7-8, 12-13, 20` | "look like Yantra" and "the Pixel 7 the logic tests use", "the desktop project" (comments, BR1-07); `require` from `frontend/package.json` throws a raw error when Playwright is not installed |
| k | `tooling/steps/step_facts.py:166` | `gather()` reads `docs/steps/INDEX.md` unchecked: a repo without it gets a `FileNotFoundError` traceback (BR1-04) |

The rest is generic already: `step_facts.py`, `step_ls.py`, `step_feedback.py`, `step_snapshot.py`
and the six `tooling/step-*.bat` wrappers plus `tooling/render-mockups.bat` (each `cd /d "%~dp0.."`
then `uv run --no-project python tooling\steps\….py %*` or `node …`). `step_facts.py:13`
(`SHARED_DOCS`) names `docs/steps/INDEX.md` and `docs/steps/device-checks.md`, which are the
conventions' fixed paths (README § The repo's settings and index), not Yantra values.

**The sync** (facts). `tooling/common/sync_common.py` is itself synced from `smtw-common`
(`SELF_SRC`, line 22; it updates itself first), so its `FILES` (line 25) and `DIRS` (line 40) are
changed in `smtw-common`, never in Yantra. `DIRS` already syncs `.claude/skills` whole, so the
`step` skill needs no entry. A sync writes only files that exist in `smtw-common` and deletes
nothing (`sync_dir`). `smtw-common` keeps its tests in `tooling/common/tests` and runs them with
`tooling/run-common-tests.bat`.

**Track: full.** It sets what every SMTW repo must write in its settings for the tools to work. No
app code, no migration, no RBAC; about 9 files.

**A refactor for Yantra.** Every tool's output for Yantra stays the same, except the two differences
§ 5 names.

## 1. What will be built

### 1.1 One settings reader

`tooling/steps/step_facts.py` gets `read_step_settings(text)` (not `read_settings`: that name is
`preflight.py:83`'s, BR1-08) → `{entry: value}` for the bullets of
`.claude/CLAUDE.md` § Step workflow, or `None` when the section is missing. It reads the form
`preflight.py` reads (`read_section`, `tooling/common/preflight.py:62-79`): the section runs from
`## Step workflow` to the next `## `; a line `- **<Entry>**: <value>` is an entry. A value `none`
reads as `None`. **An entry is one line** (BR1-14): a bullet the IDE wraps loses the rest of its
value, as in `## Pre-flight`; the README's entry table says so. A helper `backticked(value)` → the
list of backticked words in the value. Every entry the tools read is a list of backticked words: one
grammar (BR1-01).

The two tools that read an entry, `brief_facts.py` and `step_stats.py` (BR1-11), stop when they
find **no section**, with S056's message, exit 2: "This repo has
no Step workflow section in its CLAUDE.md. Add one; docs/steps/README.md lists the entries (see
`## Pre-flight` for the form)." A **missing or `none` entry** takes the default of § 1.2. The other
four tools read no setting and run without the section.

**No `INDEX.md`** (BR1-04, row k): `gather()`, which every tool but `step_feedback.py` goes through,
stops with one line, exit 2: "This repo has no docs/steps/INDEX.md. docs/steps/README.md § The
repo's settings and index gives its shape." (`step_feedback.py` only globs the folders and finds
none.)

### 1.2 Six new settings entries, read by the tools

Added to Yantra's § Step workflow and to the README's entry table (§ The repo's settings and index),
each with its `none` behaviour. Each value is backticked words (§ 1.1); a value holds no backtick.

**Code folders**, read by `brief_facts.py`:

- `- **Code folders**: `backend` `frontend/src` `frontend/e2e` `frontend/tests` `tooling``
  - (a) the folders `git grep` searches (`SEARCH_DIRS`);
  - (b) a module `x.py` is looked up in each code folder, then in `tooling/steps` (the step tools
    sync to every repo);
  - (c) a test id's file is looked up at the root, then `<folder>/<file>` and
    `<folder>/tests/<file>` for each code folder, in the listed order;
  - `none` or missing: the whole repo **except `docs/`** (`git grep … -- . ':!docs'`, BR1-06: the
    step files name the code names they discuss and would count as code), modules in
    `tooling/steps` only, test files at the root only.

**Browser-test runs**, five entries (BR1-01 option B; KLA's choice, U4), read by the pure
functions of `step_stats.py` (BR1-13), unit-tested:

| Entry | Yantra's value | Meaning | Missing or `none` |
|---|---|---|---|
| *Browser-test wrapper* | `run-e2e-tests.bat` | the file name of the command that starts a run (rows d–e) | no browser runs are counted; the report leaves out the E2E columns |
| *Browser-test levels* | `basic` `normal` `targeted` `full` | the names counted, in the order of the columns; the header letters are their first letters (`b/n/t/f`); `targeted` is the reserved name for a run naming a spec file; a run with `--level=<name>` counts as that name. Two levels with the same first letter: the tool stops, exit 2, naming them | as for the wrapper |
| *Browser-test spec files* | `.spec.js` | a run naming a file with this ending is `targeted`, at any level (row f) | no run is `targeted` |
| *Browser-test default level* | `normal` `full` `2026-10-25T05:50Z` | the first word: the level of a run with no flag and no spec file; then pairs `<level>` `<time>`: such a run that started before the time has that level (row g, Yantra's history). The time is parsed with `step_stats._time()` (`Z` → `+00:00`; `fromisoformat` takes `Z` only from Python 3.11, BR1-09) | the first level other than `targeted` |
| *Browser-test total line* | `All lanes done in (\d+) s` | a regular expression with one group, the run's seconds (row d) | only Playwright's line below |

Playwright's own "N passed (1.2m)" line, for 40 tests or more, stays built in (`PLAYWRIGHT_DONE`,
`E2E_MIN_TESTS`): Playwright is the SMTW stack's browser-test tool.

The counters of (h) become one `{level: count}` per run; the columns and headers are built from
the levels.

### 1.3 The device-check list is optional (i)

`step_check.py` skips check 7 when `docs/steps/device-checks.md` does not exist (a repo whose
*Device checks* entry is `none`): `run()` takes `rows = []` then, and `check_device_rows` already
returns no problem for empty rows (BR1-12). The path stays the convention's fixed one.

### 1.4 The mock-up renderer (j)

`render_mockups.mjs`: the comments say "the app" instead of "Yantra", and "a Pixel 7-size phone
(412 x 915, scale 2) and a 1366 x 768 desktop" instead of naming Yantra's browser-test projects
(the sizes stay, BR1-07); when Playwright cannot be
loaded from `frontend/node_modules`, it prints "Playwright is not installed in frontend/. The mock-up
deck needs the browser tests' Playwright." and exits 1. `frontend/` stays: it is the SMTW base layout
(`.claude/SMTW-WebApp-Base.md:64`), as S056 row k kept the stack words.

### 1.5 The step tests leave Yantra in this step (KLA, U2, U3)

The step tools' tests live only in `smtw-common` (U2). They leave Yantra now (U3), through a staging
folder that holds them until the lift:

1. The coder updates the seven tests in `tooling/tests/` (`test_step_facts.py`,
   `test_step_feedback.py`, `test_step_ls.py`, `test_step_snapshot.py`, `test_step_stats.py`,
   `test_brief_facts.py`, `test_render_mockups.py`), writes the new tests beside them, and runs
   `tooling/run-tooling-tests.bat` green there (the renderer test runs, not skips).
2. Then it moves all of them (`git mv` for the seven, plain move for new files) to
   `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/`, the path they will have in `smtw-common`, and fixes each for that place:
   the tests are fixed for **`smtw-common`'s** layout, not the staging folder's (`tooling/common/tests/` → `parents[2] / "steps"`;
   `test_render_mockups.py`'s `ROOT` → `parents[3]`), so they run there unchanged, and nobody runs
   them in the staging folder.
3. To prove the fixed copies work, the coder runs them once from a temporary copy laid out as
   `smtw-common` is (in the session scratchpad: `tooling/steps/`, `tooling/roadmap/`,
   `tooling/common/tests/`; the renderer test skips there, having run before the move), with
   `uv run --no-project --with "pytest>=8,<10" pytest tooling/common/tests`, and gives the result in
   the report. The temporary copy is deleted after.
4. `tooling/run-tooling-tests.bat`'s comment stops naming the step tools; its command is unchanged
   (`tooling\tests` now holds only `test_deploy.py`, `test_preflight.py`, `test_preflight_stamp.py`,
   `test_run_lanes.py`, `test_run_logged.py`).

No Yantra test run sees the staged tests (`run-tooling-tests.bat` runs `tooling\tests` only; no
pytest config collects `docs/`). Until the lift, a change to a step tool in Yantra is tested by
running the staged tests from a temporary copy, as in item 3 (the impl report gives the commands).

Their sample strings (`backend/tickets_core.py`, `run-e2e-tests.bat`, …) stay: they are test data,
and the settings reader's tests give the values explicitly.

New tests: `read_step_settings` (section missing, entry missing, `none`, backticks stripped, the
section ending at the next `## `); `brief_facts` with folders given and with `None` (`docs/` left
out); `step_stats` with Yantra's entries (the existing level tests: the same counts, asserted on the
dict instead of the tuple `(0, 0, 2, 1)`, BR1-10), with two levels (`targeted` `normal`, no total
line), with levels whose first letters clash (refused), and with no wrapper (no E2E columns);
`step_check`'s device rows with no device-check file, on the pure part (BR1-12); `gather()` with no
`INDEX.md` (the message).

### 1.6 The lift list (in the impl report, for KLA)

The coder writes, in the impl report under `## Lift to smtw-common`, ready to paste, as S049 did:

1. **Files to copy** to the same paths in `smtw-common`: `.claude/skills/step/` (syncs with the
   skills folder, no entry), `.claude/agents/` (the five agent files), `tooling/steps/`,
   `tooling/roadmap/`, the six `tooling/step-*.bat`, `tooling/render-mockups.bat`,
   `docs/steps/README.md`, `docs/roadmap/README.md`.
   **The tests** (U2, U3): copy the staging folder `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/` to `smtw-common`'s
   `tooling/common/tests/` (not a synced folder), as they are: § 1.5 already fixed them for that
   place. `test_render_mockups.py` skips in `smtw-common`, which has no `frontend/` (BR1-15). Then
   delete `docs/steps/S057-step-tooling-lift/lift/` in Yantra. **Never** `docs/steps/INDEX.md`,
   `docs/roadmap/INDEX.md`, `docs/steps/device-checks.md` or the step folders.
2. **`sync_common.py`** in `smtw-common`: `DIRS` gains `(".claude/agents", ".claude/agents")`,
   `("tooling/steps", "tooling/steps")`, `("tooling/roadmap", "tooling/roadmap")`; `FILES` gains the
   seven `.bat` files and the two READMEs.
3. **`smtw-common`'s `tooling/run-common-tests.bat`**: no change; it already runs
   `tooling\common\tests` (U2; BR1-02.1 no longer applies).
4. **`smtw-common`'s own docs of what syncs** (BR1-02.2): the "Repository structure" block of
   `tooling/common/README.md` (each new folder and file marked "[synced]") and its root `CLAUDE.md`
   § Contents.
5. **`CLAUDE-COMMON.md`**, a short section (text in the report): repos may work in numbered steps
   with `/step`; the skill, the agents, `tooling/steps/`, `tooling/roadmap/` and the two READMEs come
   from `smtw-common` and are edited there; a repo opts in with a `## Step workflow` section (entries
   in `docs/steps/README.md`) and its own `docs/steps/INDEX.md`; the tools' tests live and run in
   `smtw-common` only (U2).
6. **After the lift, in Yantra**: § Step workflow's first paragraph says these files come from
   `smtw-common` and are edited there, not here (a sync overwrites them); the staging folder is
   deleted (item 1).

**Every SMTW repo receives the files** (BR1-03, fact: `../smtw-common/tooling/common/sync_all.py`
runs the sync in every sibling repo): after the lift, each repo gets `.claude/agents/`,
`tooling/steps/`, `tooling/roadmap/`, the seven wrappers and `docs/steps/README.md`,
`docs/roadmap/README.md`, whether it works in steps or not. A repo opts in by adding the section
and `INDEX.md`; without them `/step` stops with S056's message and the tools with theirs (§ 1.1).

**Until the lift**, a sync does not touch any of these files (none exists in `smtw-common`), so
nothing changes for Yantra.

### Out of scope

- Writing to `smtw-common`: KLA does the lift (as S049 § 1.8), or asks for it in a later request.
- Any change to what the tools report for Yantra beyond § 5's two differences.
- The prose (S056, done); the past step files.
- A delete step in `sync_common.py` (a file removed in `smtw-common` stays in each repo): it is the
  sync's existing behaviour, for every synced file.

## 2. Standards and practice

- **Separation of configuration from code** (twelve-factor's "config" factor): what differs between
  repos lives in each repo's settings, not in the shared tools — the split S056 made for the prose,
  and pre-flight's `## Pre-flight` makes for its scripts.
- **ISO 9001 § 7.5.3 (control of documented information)**, the plant's future goal: one
  controlled version of the procedure and its tools, in `smtw-common`, with each repo's specifics
  recorded beside it (as S056 § 2).
- No maintenance standard applies: this is development tooling.

## 3. Where

| File | Change |
|---|---|
| `tooling/steps/step_facts.py` | `read_step_settings`, `backticked`, the no-section message, the no-`INDEX.md` message (§ 1.1) |
| `tooling/steps/brief_facts.py` | folders from *Code folders* (§ 1.2 a–c) |
| `tooling/steps/step_stats.py` | runs counted from the five *Browser-test* entries; counters as one dict; columns from the levels (§ 1.2) |
| `tooling/steps/step_check.py` | check 7 skipped without the device-check file (§ 1.3) |
| `tooling/roadmap/render_mockups.mjs` | comment; message when Playwright is missing (§ 1.4) |
| `tooling/tests/` → `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/` | the seven step tests and the new ones, run green, then moved and fixed for `smtw-common` (§ 1.5, U3) |
| `tooling/run-tooling-tests.bat` | its comment stops naming the step tools (§ 1.5 item 4) |
| `.claude/CLAUDE.md` § Step workflow | the six new entries (§ 1.2) |
| `docs/steps/README.md` § The repo's settings and index | the six entries in the table, with their `none` behaviour; a line that the tools read them; that an entry is one line of backticked words |

### Docs (housekeeping, by the coder)

`.claude/CLAUDE.md` (the entries, above). No schema, plan or domain doc is due.

## 4. Design decisions

1. **The settings in `CLAUDE.md`, read by one reader** (S056 decision 1: "S057's parsers will read
   this one the same way"). Rejected: a machine-friendly `.claude/step-workflow.toml`: easier to
   parse, but a second place for the same settings.
2. **New entries of backticked words** rather than parsing the prose entries (*Browser tests* is a paragraph).
   Rejected: reading the wrapper's name out of *Browser tests*: fragile, and that entry is written for
   the agents.
3. **Yantra's level history stays in the setting** (`full` before 2026-10-25T05:50Z), so `/step stats`
   over Yantra's old transcripts is unchanged. Rejected: dropping it: S001–S046's runs would count
   as `normal`.
4. **The tests live only in `smtw-common`** (KLA, U2), in `tooling/common/tests/` as the pre-flight
   tests do: the tools are tested where they are edited; a repo does not carry tests for code it
   only receives. They leave Yantra in this step through a staging folder in the step's folder (U3).
   Rejected: tests synced with the code (`tooling/steps/tests/`) into every repo (the first
   proposal); deleting them outright (the new tests would exist only in the coder's run); removing
   them only at the lift.
5. **The device-check path stays fixed** (`docs/steps/device-checks.md`), optional. Rejected: a path
   setting: one more entry for no gain.
6. **KLA does the lift** (as S049): `smtw-common` is another repo (CLAUDE-COMMON § Agents change
   nothing outside the repo).

## 5. Tests and acceptance

- **Before and after, the same output** (the main acceptance), captured at the baseline and after
  the change, diffed, both in the impl report: `tooling/step-ls.bat all`, `tooling/step-check.bat`,
  `tooling/step-feedback.bat`, `tooling/step-stats.bat` (its `scratch/step-stats.md`, less the
  "Built …" line) and `tooling/step-brief-facts.bat S056`. Expected differences, and only these:
  1. `brief_facts`: a name defined as a module in `tooling/` (e.g. `run_logged.x`) now shows "a
     module (tooling/run_logged.py)" (§ 1.2 b);
  2. `brief_facts`: a test id whose file sits under a code folder other than `backend/` is now found.
  Any other difference is a defect.
- `tooling/run-tooling-tests.bat` green before the move (the count before plus the new tests) and
  after it (the five remaining files); the staged tests green from the `smtw-common`-shaped copy
  (§ 1.5 item 3), the same count as before the move.
- With the settings section removed (a test on the pure reader, or a fake root): `brief_facts.py`
  and `step_stats.py` exit 2 with S056's message; `step_ls.py`, `step_check.py`, `step_feedback.py`
  and `step_snapshot.py` still run.
- The renderer test **runs, not skips**, on the dev machine (`frontend/node_modules/playwright`
  exists), before the move: the impl report shows it passed.
- **The lift list** (§ 1.6) is checked by the code reviewer against the files: every file the step
  tools, the skill and the agents read or call is on it, and no repo-own file is.
- **Coder: Sonnet.** No Opus criterion holds: no transactions, locks, auth or migration; the logic
  is small.
- Manual checks: none.

## 6. Open questions and assumptions

1. **The browser-test entries' form** (BR1-01). Answered (U4): five entries. Was recommended: **five entries**, each a list of
   backticked words, the one grammar of *Code folders* (§ 1.2); a wrong value shows in its own
   bullet. Alternative: **one entry** *Browser-test runs*, split at `;` into keyed parts
   (`wrapper`, `spec files`, `levels`, `no level … before …`, `total line`): one bullet, but a
   second grammar, and a value may then hold no `;`. A TOML file stays rejected (decision 1).
2. **Tests**: answered (U2): only in `smtw-common` (decision 4).
3. **No other repo has a `docs/steps/` folder** (KLA, U2: "none"), so the lift overwrites nothing.
   The lift creates `docs/steps/` and `docs/roadmap/` (each with its README) in every
   SMTW repo, opted in or not (§ 1.6, BR1-03).

## 7. Amendments

None.

## Review log

### U1 — 25-10-2026 (before drafting)

KLA: "Draft S057." The scope is S056's § Out of scope for S057 and S056 U1 ("S057 tooling and
lift").

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor: the *Browser-test runs* entry's second grammar | Accepted as the proposal: five entries of backticked words (option B), a first-letter clash refused (§ 1.1, § 1.2); the form goes to KLA at gate A with the one-entry form as the alternative (§ 6 Q1) |
| BR1-02 minor: lift list gaps | Accepted: `tooling\roadmap\tests` in item 3; `smtw-common`'s README and `CLAUDE.md` as item 4; how a repo runs the tests in item 5 (§ 1.6) |
| BR1-03 minor: the sync fans out to every repo | Accepted (option A): stated in § 1.6 and § 6 Q3 |
| BR1-04 minor: traceback without `INDEX.md` | Accepted (option A): a one-line message, exit 2, in `gather()` (row k, § 1.1, tests) |
| BR1-05 minor: the renderer test's `ROOT` | Accepted: `parents[3]` at its new place (since U2: in the lift list, § 1.6 item 1); § 5 checks that it runs, not skips |
| BR1-06 minor: `none` of *Code folders* counts step files | Accepted (option A): the whole repo except `docs/` (§ 1.2) |
| BR1-07…BR1-15 nits | Accepted, all: row j's comments; `read_step_settings`; `_time()`; dict asserts; the two tools named; the device-check skip on the pure part; the parsing module named; one line per entry; the renderer test skips in `smtw-common` |

### U2 — 25-10-2026, at gate A

KLA: "Q2 only in common repo. Q3 none." The tests stay in Yantra's `tooling/tests/` until the lift,
then live only in `smtw-common`'s `tooling/common/tests/` (§ 1.5, § 1.6 items 1, 3, 5, 6, § 3,
decision 4, § 5). No other repo has `docs/steps/` (§ 6 Q3). Q1 still open.

### U3 — 25-10-2026, at gate A

KLA: "The test for step can be removed from Yantra repo." Then, asked where they wait until the
lift: the staging folder `docs/steps/S057-step-tooling-lift/lift/tooling/common/tests/` (§ 1.5, § 1.6 items 1 and 6, § 3, decision 4, § 5).

### U4 — 25-10-2026, at gate A

KLA, Q1: "Five" — the five browser-test entries of § 1.2.

### U5 — approval, 25-10-2026

KLA: "Ok" to "Shall I set the brief to Approved and start coding?" Coder: Sonnet.
