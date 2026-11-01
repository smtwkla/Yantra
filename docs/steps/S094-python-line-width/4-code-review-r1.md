```
Step: S094 — Python lines at most 120 characters
Doc: code review r1
Author: Code reviewer (Opus)
Date: 01-11-2026
Status: Done — 0 blocker, 0 major, 1 minor, 5 nits
```

# S094 — Code review, round 1

**Verdict: no blocker or major finding is open.** The wraps change no behaviour, and the line endings are unchanged.
One minor finding: the new test crashes on a tracked file that a step deletes without staging (CR1-01).

## Test results

- `YANTRA_TEST_RUN=s094cr1 tooling/run-tooling-tests.bat`: PASSED, 238 passed (1 s). The 7 tests of
  `test_line_width.py` are in it, `test_repo_python_lines_fit` included, so the tree has no long line now.
- Backend and frontend suites: not run again. The coder's full run (`s094c1`) was green: backend 4471,
  frontend 412, tooling 238. No finding of mine needs a backend run.
- No browser run: no screen, API or frontend file changed. No schema docs check: `local_db.py` and
  `docs/schema/` are not in the diff.

## How I checked that no wrap changes behaviour

- **Syntax trees** (my own script, `git show HEAD:<file>` against the working tree, all 46 files):
  - 32 files have an identical tree;
  - 9 differ only inside docstrings (whitespace). A second script compared every string constant that is not a
    docstring: all are identical in these 9 files. So every SQL and message split joins back to the same value;
  - 5 differ by the rearrangements the report lists: `conftest.py` (`creator_marks`),
    `test_improvement_register_api.py:124` (one `assert a and b` became two asserts, which is stricter),
    `test_procedures_api.py:208` (`rows`), `test_site_roles_api.py` (`manager_all`, the two log lines build the
    same text), `test_run_lanes.py` (`expected`). Each keeps the behaviour.
- **Split literals:** the SQL fragments in `alerts.py`, `improvements.py`, `equipment.py`, `tickets.py`,
  `test_documents_api.py` and `test_migration_v36.py` are split at a space, and the piece boundaries keep one
  space. `schema_docs_core.py:219` is split at the sentence end; the test's `endswith("Fix the file, then run
  the command again.")` still finds a whole phrase. Every f-string piece with a brace keeps its `f`
  (`schema_docs_core.py:219`, `:291`, `equipment.py:682`, `improvements.py:871-872`).
- **Rule 4:** no message that a test asserts or a user sees was split in the test files or in `backend/`. The
  long messages in tests now sit whole on their own line (e.g. `test_models_api.py:349`,
  `test_ticket_work_api.py:919`). The one exception is CR1-05.
- **Line endings:** for each changed `.py` file I counted CRLF, LF and lone CR by bytes. The 10 CRLF files are
  all-CRLF, the 36 LF files are all-LF, no file has a lone CR, and every file still ends with a newline.
  `git diff --stat` and `git diff -w --ignore-cr-at-eol --stat` give the same totals (46 files, +253 −126), so
  the diff holds only the wrapped lines. The byte-mode scripts are reported in "Decisions taken"; the result
  is what the brief's rule 5 asks for.

## Findings

### CR1-01 (minor) — a tracked file deleted without staging crashes the test

- **Where:** `tooling/tests/test_line_width.py:42` (`read_text`) with `python_files`, which runs
  `git ls-files --cached`.
- **Problem:** `--cached` lists every file in the index, also one that is deleted in the working tree. I
  checked this on a temp repo: after `rm a.py`, `git ls-files --cached --others --exclude-standard -- "*.py"`
  still prints `a.py`. `long_lines` then reads a missing file.
- **Failure scenario:** a later step removes a module (or a test file). Agents never stage, so the file stays
  in the index until KLA commits. `tooling/run-tests.bat` then shows the tooling suite red with a
  `FileNotFoundError` in `test_repo_python_lines_fit`, a fault that has nothing to do with line width. The
  coder loses a run to find out why.
- **Fix:** skip a listed path that does not exist (`if not path.is_file(): continue`), or drop the deleted
  files from the list (`git ls-files --deleted` subtracted). Add a case to the temp-repo test: a committed file
  removed from the working tree is left out.

## Nits

- **CR1-02** (nit) `backend/tests/test_alerts.py:259`, `test_closed_email.py:106`, `test_equipment_api.py:1012`,
  `test_improvement_timeline_api.py:72`, `test_ticket_work_api.py:1146`, `test_improvement_register_core.py:116`,
  `backend/tickets.py:1249`, `backend/improvements.py:307`: these wraps split one argument across lines (e.g.
  `local(start` / `+ timedelta(minutes=130)))`, `{})}))`). Break at the outer bracket instead, so each argument
  stays whole; legibility is the step's purpose.
- **CR1-03** (nit) `backend/alerts.py:10-12`, `backend/documents.py:14-18`, `backend/equipment.py:122-123`,
  `backend/properties_core.py:6-7` and `:511-512`, `backend/alerts_core.py:474-475`: the wrapped docstring
  lines leave a short orphan line in the middle of a paragraph (`ticket lock, which is the` / `handler's.`).
  Re-flow the paragraph in these production modules.
- **CR1-04** (nit) `tooling/tests/test_line_width.py:44-55`: when `_MIGRATIONS = [` is found but no `]` at
  column 0 follows (e.g. a later `]  # end`), the rest of `local_db.py` is exempt with no sign. Fail when the
  block is still open at the end of the file.
- **CR1-05** (nit) `tooling/schema/schema_docs_core.py:291-292`: the phrase that
  `test_schema_docs_core.py:259` asserts (`under "tables", then run …`) is split mid-sentence. The split is
  unavoidable (the second sentence alone is 148 characters), but the report does not name it as a rule-4
  exception; add it to "Decisions taken".
- **CR1-06** (nit) `3-impl-report.md` § 4: "Four spots where code was rearranged" lists five (the fifth,
  `test_procedures_api.py`, is under "Also"). Say "Five spots".

## Checked and found consistent

- `test_line_width.py` against § 1 and § 5: the file list is `git ls-files --cached --others
  --exclude-standard -- "*.py"`; the root is `Path(__file__).resolve().parents[2]`; the check is a function of a
  root and paths that returns `(path, line, length)`; it reads UTF-8 text and uses `splitlines()`, so it counts
  characters and no CR; the failure lists `file:line is N characters`. Its own tests cover a long line, exactly
  120, an em dash line in a CRLF file, each exempt place (`.claude/hooks/` included), the `_MIGRATIONS` block
  ending at its `]`, and the temp git repo with a committed, an untracked and a gitignored file.
- The synced exemptions match `tooling/common/sync_common.py` `FILES` and `DIRS`: every synced `.py` sits under
  `tooling/common/`, `tooling/deps/`, `tooling/steps/`, `tooling/roadmap/` or `.claude/`.
- Not touched: the `_MIGRATIONS` block, `migrations_v41.py`, `migrations_v47.py` and the synced files.
- `.claude/CLAUDE.md` § Yantra Specifics: one top-level bullet, *Python line width (S094)*, with the rule, the
  test, the three exemptions and the split rule.
- Docs pass: no migration, secret, role or module behaviour changed, so no other doc is due.
- Scope: only wraps and the new test. The diff also shows `.claude/skills/pre-flight/SKILL.md` and
  `.claude/skills/step/SKILL.md`; these are synced files, the card-format edits of the 01-11-2026 feedback
  triage, not S094's wraps. The orchestrator should confirm they belong to that triage.
- Track light: the user kept it light at gate A. The change meets no full-track criterion other than the file
  count, which the brief names.
- `docs/steps/INDEX.md` and the brief's status: In code review.

## Manual checks

None. The brief has no manual check, and the report's § 6 says so.

## Feedback

- idea: the AST comparison that proves "wraps only" took me two throw-away scripts (a whole-tree compare, then
  a compare of the non-docstring string constants, so the split literals are proven equal). A
  `tooling/steps` helper that prints both for the changed files would serve the coder and the reviewer of any
  mechanical step (my scratchpad scripts `astcmp.py`, `strcmp.py`, `eol.py`; about 5 min).
- hindrance: `git diff --stat -- '*.py'` prints one "LF will be replaced by CRLF" warning per file to stderr,
  36 lines before the one total line I needed (`git diff --stat`, 2 runs).
