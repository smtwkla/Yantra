```
Step: S094 — Python lines at most 120 characters
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: light
Baseline: f8a699c
Status: Gate B 01-11-2026 (code review r1: 1 minor, 5 nits, all fixed; r2: clean)
```

# S094 — Python lines at most 120 characters

From the feedback triage of 01-11-2026 (`docs/steps/feedback-log.md`, theme `line-width`; KLA chose "wrap all,
then test"). In S087 five docstring lines over 120 columns stayed open as nit CR1-03 through two review rounds;
one `awk` found them. A test makes a long line show in the step that writes it.

**Track: light**, proposed. Every light criterion holds except the file count (46 files). The change is
mechanical: it wraps lines and changes no behaviour, no migration, no permission and no lock. Full would add
review rounds that look at nothing new. The user may set it to full at gate A.

## 1. What will be built, and out of scope

- **Wrap** every Python line over 120 characters in the repo's own files: 123 lines in 46 files (counted
  01-11-2026 at `f8a699c` by `scratch/count_long_lines.py`: characters, not bytes, so an em dash counts as one).
  12 production modules in `backend/` (29 lines), 31 files in `backend/tests/` (86 lines, `conftest.py`
  included), `tooling/schema/schema_docs_core.py` and 2 files in `tooling/tests/` (8 lines). The script prints
  the list by file; `backend/local_db.py` has none outside `_MIGRATIONS`.
- **A test**, `tooling/tests/test_line_width.py`: every `.py` file git lists as tracked or as new and not
  ignored (`git ls-files --cached --others --exclude-standard -- "*.py"`, BR1-01: a step's new files are
  untracked until the user commits; `scratch/`, `data/`, `.venv` and `node_modules` stay out as gitignored),
  each line at most 120 characters, except the lines listed below; a failure names `file:line` and the length of
  each long line. The test finds the repo root from `__file__` (`Path(__file__).resolve().parents[2]`) and runs
  `git` there, so it works from PyCharm and in the release worktree (BR1-06). The check itself is a function
  that takes the root and a list of paths and returns `(path, line, length)` rows; the real-tree test feeds it
  git's list, the temp-tree tests feed paths directly (BR1-05).
- **Not checked, never wrapped** (each for a stated reason):
  - the `_MIGRATIONS` list of `backend/local_db.py` (from `_MIGRATIONS = [` to its closing `]` at column 0;
    2 lines today): an applied migration is never edited (CLAUDE-COMMON § Migrations are append-only); the
    test finds the block by those two lines;
  - `backend/tests/fixtures/migrations_v41.py` and `migrations_v47.py` (2 lines): frozen copies of the
    squashed migrations, never edited (`.claude/CLAUDE.md` § Migrations);
  - the files synced from smtw-common (`tooling/common/`, `tooling/steps/`, `tooling/roadmap/`, `tooling/deps/`
    and `.claude/`, whose `hooks/` holds a synced `.py`, BR1-02; checked against `tooling/common/sync_common.py`
    `FILES` and `DIRS`; 5 lines in 4 files): edited in smtw-common only; a sync overwrites them.
- **Out of scope**: JavaScript and Vue files; a formatter or linter (ruff, black) as a new dependency; the long
  lines of smtw-common (a later change there, if KLA wants it).

## 2. Standards and practice

PEP 8 § Maximum Line Length allows a team to agree a longer limit than 79; 120 is this repo's existing practice
(the reviews cite it, e.g. S087 CR1-03). ISO 9001 § 7.5 asks that documented information stays legible; code
counts. A check in the test run follows the rule "make the fault show where it is made" of the step workflow.

## 3. Where

- The 46 files of § 1: wraps only. No line's meaning changes. The split rule (BR1-03, BR1-08, BR1-09):
  1. Docstrings and comments break at a word.
  2. Code breaks inside brackets (implicit line joining), never with a backslash, and keeps string literals whole.
  3. A literal is split into adjacent literals with the same text only when it alone does not fit (today the SQL
     fragments and the CLI message of `tooling/schema/schema_docs_core.py:219`). Every piece of an f-string that
     holds a brace keeps the `f` prefix (`schema_docs_core.py:219` and `:288` with `{{`/`}}`,
     `backend/tests/conftest.py:220`).
  4. A message that a test asserts or that a user sees is never split: a split text is no longer found by
     `git grep` or the facts tool's screen-text search. Break the code around it instead. Only when the literal
     alone does not fit (rule 3, e.g. `schema_docs_core.py:219`), split it at a sentence end, so each phrase a
     test asserts stays whole in one piece (BR2-01).
  5. Edit with the Edit tool, so each file keeps its line endings (`docs/steps/README.md` § Shell on Windows,
     rule 7); the diff shows only the wrapped lines.
- `tooling/tests/test_line_width.py`: new.
- **Docs (housekeeping, by the coder)**: `.claude/CLAUDE.md` § Yantra Specifics, one line: Python lines at most
  120 characters, checked by `tooling/tests/test_line_width.py`, and the three exemptions.

## 4. Design decisions

- **A plain test in the tooling suite, not a linter.** It runs in `tooling/run-tests.bat` with no new
  dependency (*Dependency health*) and checks one rule. Rejected: ruff with `line-length = 120` (a new dev
  dependency and its own run, for one rule).
- **Characters, not bytes.** `len(line)` on the UTF-8 text, read in text mode with universal newlines and split with `splitlines()`, so the newline and a CR
  of a CRLF file (10 of the 46 in the working tree) is not counted (BR1-07). `awk length` counts bytes, so it overcounts
  comments with em dashes (it found 140; the real count is 132 in all, 123 outside the exemptions).
- **Exemptions by path and by the migrations block, with no `# noqa` marker.** A marker cannot sit inside a SQL
  string, and the exempt places are fixed and few. Rejected: a per-line allow marker.
- **A user-visible string keeps its exact text.** A split message or SQL string is joined by Python into the
  same value; the existing tests that assert messages prove it.

## 5. Tests and acceptance

- `tooling/tests/test_line_width.py` red on the tree before the wraps (it lists 123 lines), green after.
  Its own unit tests on a temp tree: a long line fails with `file:line`; a long line in each exempt place passes;
  the `_MIGRATIONS` block ends at its `]`, so a long line after it fails. One test on a temp git repo: the file
  list holds a committed and an untracked `.py` and leaves out a gitignored one (BR2-02, the `--others` flag).
- All unit suites green after the wraps: `tooling/run-tests.bat`; no test changes its assertion.
- No browser run: no screen and no frontend file changes.
- No manual check.

## 6. Open questions and assumptions

- Assumption: no other step is coded while S094 is (it touches 46 files; `INDEX.md` queue note). Nothing is
  being coded on 01-11-2026.
- Open: should smtw-common get the same test for its own files? Not in this step.

## 7. Amendments

None.

## Review log

| ID | Finding | Answer |
|---|---|---|
| BR1-01 | major: `git ls-files` alone misses a step's new, untracked files | Accepted: `--cached --others --exclude-standard` (§ 1) |
| BR1-02 | minor: the synced exemption misses `.claude/hooks/` | Accepted: `.claude/` added to the synced prefixes (§ 1) |
| BR1-03 | minor: state the split rule; never split an asserted message | Accepted: § 3, rules 1–4 |
| BR1-04 | minor: full track by the file count | Kept light, for the user to decide at gate A (the review recommends light) |
| BR1-05…BR1-09 | nits | Accepted: checker function (BR1-05) and root from `__file__` (BR1-06) in § 1; universal newlines in § 4 (BR1-07); f-string pieces and line endings in § 3 rules 3 and 5 (BR1-08, BR1-09) |
| BR2-01 | minor: § 3 rules 3 and 4 contradict on `schema_docs_core.py:219` | Accepted: rule 4 allows a split at a sentence end when the literal alone does not fit |
| BR2-02 | minor: the `--others` flag has no test | Accepted: a temp git repo test in § 5 |
| BR2-03 | nit: say the newline is stripped | Accepted: `splitlines()` in § 4 |
