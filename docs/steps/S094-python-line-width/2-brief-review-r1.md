```
Step: S094 — Python lines at most 120 characters
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 01-11-2026
```

Reviewed against: f8a699c (the working tree holds no uncommitted code; only `docs/steps/INDEX.md` and the S093 brief are modified)

**Verdict: one `major` is open (BR1-01: the test reads only git-tracked files, so it misses the new files a step writes).** Light track, so this is the only round; the answer to BR1-01 is re-read because it is a major. Facts file read: `scratch/brief-facts-S094.md`. I re-ran `scratch/count_long_lines.py` and a copy of it that prints each long line's text, and read all 132 long lines.

## Findings

### BR1-01 — major — The test checks git-tracked files only, so a step's new files are not checked

**Problem.** § 1 says the test reads "every git-tracked `.py` file" (`git ls-files "*.py"`, as the count script does). A step's new files (a new test module, a new core module) are untracked while the step is coded and reviewed: the agents never `git add` (`docs/steps/README.md` § Shell on Windows, item 8), and the user commits at gate B. The test is green on them until the commit, and the long line shows in the next step's run, as another step's problem.

**Why it matters.** The brief's reason for the test is "A test makes a long line show in the step that writes it." S087's CR1-03 lines were in files of that step. A new test file is the most common place a step adds lines, so the test as specified misses its main case.

**Options.**
- A (recommended): list tracked and untracked files that are not ignored: `git ls-files --cached --others --exclude-standard -- "*.py"`. `scratch/`, `data/`, `.venv` and `node_modules` are gitignored, so they stay out; in the release worktree the list is the tracked files. One flag, no new design.
- B: walk the code folders (`backend`, `tooling`) with `Path.rglob("*.py")` and skip `__pycache__`. Needs its own skip list and misses a `.py` added elsewhere.

Fix the brief's § 1 and § 5 ("every tracked or new `.py` file"); the temp-tree test then also covers an untracked file.

### BR1-02 — minor — The synced exemption misses `.claude/hooks/` (synced by `sync_common.DIRS`)

**Problem.** § 1 exempts `tooling/common/`, `tooling/steps/`, `tooling/roadmap/`, `tooling/deps/`. `tooling/common/sync_common.py` also syncs the directories `.claude/skills`, `.claude/hooks` and `.claude/agents` (`DIRS`, lines 69–75). `.claude/hooks/guard-common.py` is a tracked `.py` file from smtw-common. It has no long line today, so the counts are right, but a later sync can bring one, and the test would then be red on a file Yantra must not edit (a sync overwrites it).

**Why it matters.** A red tooling suite that no Yantra change can fix, between a sync and a smtw-common fix.

**Options.**
- A (recommended): add `.claude/` to the exempt prefixes, with a comment in the test that the list follows `sync_common.FILES` and `DIRS`. The other prefixes are complete: all nine `tooling/common/*.py` are in `FILES` or are `SELF_SRC`; both `tooling/deps/*.py` are in `FILES`; `tooling/steps/` and `tooling/roadmap/` are `DIRS`.
- B: import `sync_common` in the test and derive the exempt set from `FILES` and `DIRS`. Couples a test to a synced module for four prefixes; not worth it.

### BR1-03 — minor — Say when a string literal may be split: at a bracket first, a literal only when it alone is too long, never a message a test or a screen names

**Problem.** § 3 says "a long string literal splits into adjacent literals with the same text" with no preference. Of the 123 lines, nearly all break inside a bracket with every literal kept whole: the long line is an `assert` with a tuple, a call with keyword arguments, an import, a list of strings. Only the SQL fragments (`alerts.py:287`, `:380`, `improvements.py:868`, `:1448`, `tickets.py:1398`, `conftest.py:220`, and the `db_rows(...)` lines in the tests) and the CLI message `tooling/schema/schema_docs_core.py:219` hold one literal that does not fit on its own line.

**Why it matters.** A split message can no longer be found by `git grep`: the facts tool's *Screen text in the tests* section and a reviewer looking for `"Choose an engineer or manager of this site"` (`test_improvements_api.py:201`) or `"Close its tickets first (2 open)"` (`test_masters_api.py:343`) find nothing. The value is the same; the code is harder to search.

**Options.**
- A (recommended): add to § 3: break at a bracket and keep each literal whole; split a literal only when it alone does not fit at its indent, SQL at a keyword with the joining space kept, a message at a sentence end. The same text is produced; the existing tests prove it, as § 4 says.
- B: leave the rule to the coder. Two coders split differently.

### BR1-04 — minor — Belongs on the full track by the file count (46 files, criterion "roughly 10 files or fewer")

**Problem.** The brief says so itself (header note). The rule (`docs/steps/README.md` § Tracks; 23-10-2026) asks the reviewer to raise it as a minor so the user decides at gate A. The other four light criteria hold: no migration or data change (the migrations are exempt, not edited), no auth or security code, no locking, no new module or dependency.

**Recommendation.** Keep light. Every change is a wrap that the unit suites check, the test is one module in an existing suite, and a full track would add review rounds that read the same 123 wraps again. The user may override.

## Nits

- **BR1-05** (nit) § 5: say the checker is a function that takes the repo root and a list of paths and returns `(path, line, length)` rows. The real-tree test feeds it git's list; the temp-tree tests feed paths directly, so they need no `git init`.
- **BR1-06** (nit) § 1: the test finds the repo root from `__file__` (`Path(__file__).resolve().parents[2]`) and runs `git` there, not in the current directory: PyCharm runs a test from another folder, and the release runs the suite in a worktree.
- **BR1-07** (nit) § 4 *Characters, not bytes*: add that the file is read in text mode with universal newlines (as the count script does), so a CR is not counted. The working tree is mixed today: 10 of the 46 files have CRLF line endings (`test_ticket_work_api.py`, `properties_core.py`, …), and a byte-wise read would count 121 for a 120-character line there.
- **BR1-08** (nit) § 3: the three f-strings with doubled braces or a nested quote (`schema_docs_core.py:219` `{{...}}`, `:288` `}}`, `conftest.py:220` `{', '.join(...)}`) keep the `f` prefix on every piece that holds a brace; a piece without it would print `{{` as two braces. `tooling/tests/test_schema_docs_core.py` asserts the first message, so a slip shows, but the rule saves a fix round.
- **BR1-09** (nit) § 1: the wraps keep each file's line endings (README § Shell on Windows, item 7: the Edit tool, never a text-mode rewrite), or the diff shows 46 whole files.

## Checked and found consistent

- The counts: 123 lines in 46 files to wrap; 29 in 12 `backend/` modules, 86 in 31 `backend/tests/` files, 8 in `tooling/schema/schema_docs_core.py` and 2 `tooling/tests/` files; exempt 2 (`_MIGRATIONS`), 2 (frozen fixtures), 5 in 4 synced files; 132 in all. `scratch/count_long_lines.py` reproduces them at f8a699c.
- The `_MIGRATIONS` block detection: `_MIGRATIONS = [` is line 85 of `backend/local_db.py`, and the first `]` at column 0 is its close at line 1257; `_PRECONDITIONS` (line 1284) is a one-line dict. The block's two long lines are a Settings help text (line 1128) and a CHECK constraint (line 1213); `local_db.py` has no long line outside the block.
- The frozen fixtures: `backend/tests/fixtures/` holds `__init__.py`, `migrations_v41.py` and `migrations_v47.py` only; the two long lines are the same two texts as in `_MIGRATIONS`.
- No docstring among the 123 lines is read by code: `__doc__` is used only in `tooling/steps/brief_facts.py`, `step_claim.py` and `step_snapshot.py` (synced, exempt). No argparse `description=__doc__` in Yantra's own files.
- No linter is configured (no ruff, flake8 or pycodestyle setting in any `.toml`, `.cfg`, `.ini` or `.bat`), so the `# noqa: F401` comment on `test_contract_alerts.py:30` can move with its wrap.
- No long line sits inside a triple-quoted non-docstring string outside the exempt blocks; every SQL fragment to split is already one of several adjacent literals.
- The test belongs in the tooling suite: it needs no database, runs under `uv run --no-project --with pytest` from the repo root (`run-tooling-tests.bat`), and `tooling/tests/` is Yantra's own (not synced; smtw-common's tests are in `tooling/common/tests` there). Its `conftest.py` only adds `tooling/` to `sys.path`.
- The standards line fits a tooling step (PEP 8 § Maximum Line Length allows an agreed limit; ISO 9001 § 7.5.2 asks for documented information that is legible).
- `.claude/CLAUDE.md` § Yantra Specifics is the right place for the one-line rule; `docs/steps/README.md` and CLAUDE-COMMON are synced and out of scope, as § 1 says.
- The assumption that no other step is coded beside S094 holds: `INDEX.md` lists S093 as Done at f8a699c and nothing as Implementing.

## Feedback

- idea: `scratch/count_long_lines.py` prints counts per file only; a `--lines` flag that prints `file:line (length)` with the text would have saved the reviewer and will save the coder a script of their own (I wrote one to judge the 123 wraps, 1 run).
- hindrance: the dump's stdout went through cp1252 when redirected to a file, so the Read tool flagged the file as not UTF-8 (em dashes shown as U+FFFD); `PYTHONUTF8=1` before such a run avoids it (1 re-read, no run lost).
