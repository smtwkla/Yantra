```
Step: S094 — Python lines at most 120 characters
Doc: impl report
Author: Coder (Sonnet)
Date: 01-11-2026
Track: light
Baseline: f8a699c
```

# S094 — Implementation report

## 1. What was built

- `tooling/tests/test_line_width.py`: a test that fails on any `.py` line over 120 characters, and its own unit tests.
- All 123 long lines in 46 files wrapped. No line's meaning changed.

## 2. How it works

- `long_lines(root, rel_paths)` returns `(path, line, length)` rows. It reads each file in text mode and uses `splitlines()`, so it counts characters, not bytes, and a CRLF is not counted.
- It skips the exempt files (the two frozen fixtures, and the prefixes `tooling/common/`, `tooling/steps/`, `tooling/roadmap/`, `tooling/deps/`, `.claude/`).
- In `backend/local_db.py` it skips the block from `_MIGRATIONS = [` to the `]` at column 0.
- `python_files(root)` runs `git ls-files --cached --others --exclude-standard -- "*.py"` in the repo root, which it finds from `__file__`.
- `test_repo_python_lines_fit` feeds the git list to `long_lines` and names each `file:line` and its length.

Red then green (the new test alone, `YANTRA_TEST_RUN=s094c1 tooling/run-tooling-tests.bat tooling/tests/test_line_width.py`):
- Before the wraps: `1 failed, 237 passed`. `test_repo_python_lines_fit` listed the long lines (123 outside the exemptions, the same count as `scratch/count_long_lines.py`).
- After the wraps: green (full run below).

## 3. Files touched

- New: `tooling/tests/test_line_width.py`.
- Wrapped, 46 files: 12 in `backend/` (`alerts.py`, `alerts_core.py`, `app.py`, `contracts_core.py`, `documents.py`, `equipment.py`, `file_store.py`, `improvements.py`, `masters.py`, `procedures.py`, `properties_core.py`, `tickets.py`), 31 in `backend/tests/` (including `conftest.py`), `tooling/schema/schema_docs_core.py`, `tooling/tests/test_run_lanes.py` and `tooling/tests/test_schema_docs_core.py`.
- `.claude/CLAUDE.md` (one line), `docs/steps/INDEX.md` and the brief's `Status` (In code review).
- Not touched: `_MIGRATIONS`, the frozen fixtures, the synced files.

## 4. Decisions taken

- **How I edited.** 123 lines in 46 files, so I used throw-away helper scripts in `scratch/` (`wrap.py`, `hand*.py`, gitignored). They read and write bytes and keep each file's line ending; there was no text-mode rewrite. The Edit tool was not used for these. Result: the 10 CRLF files stay all-CRLF and the LF files stay LF (checked by byte count: no file has mixed endings).
- **Proof that no meaning changed.** Each changed file was parsed before (`git show HEAD:`) and after, and the ASTs compared (with whitespace in string values normalised, because docstring wraps change newlines). 41 of the 46 files are identical. The other 5 differ only where I broke code around a line (items below), by design.
- **Splits.**
  - Prose (docstrings, comments) break at a word.
  - Code breaks inside brackets, with no backslash.
  - Long imports got parentheses (`alerts_core.py`, `tickets.py` twice).
  - Messages kept whole. Only `schema_docs_core.py:219` (the CLI message) was split (and, as the rule-4 exception below, `:291-292`), at the sentence end: `"...one object {{...}}. "` then `"Fix the file, then run the command again."`, both pieces keep the `f`/plain prefix right. `:288` is split in an f-string piece; every piece with a brace keeps `f`.
  - SQL strings were split into adjacent literals at a space (`alerts.py` x2, `improvements.py` x2, `equipment.py`, `tickets.py`, `test_documents_api.py` x3, `test_migration_v36.py`).
- **Five spots where code was rearranged, not only wrapped** (all ASTs differ there, the behaviour does not):
  - `tests/conftest.py`: the `DELETE ... NOT IN (...)` placeholder list went into a local `creator_marks`.
  - `test_improvement_register_api.py:124`: one `assert a and b` became two asserts.
  - `test_site_roles_api.py`: a local `manager_all` for the repeated text.
  - `test_run_lanes.py`: a local `expected`.
  - `test_procedures_api.py:208`: a local `rows` (a call split inside its brackets made it unreadable).
- **Rule-4 exception (CR1-05).** `schema_docs_core.py:291-292`: the phrase that `test_schema_docs_core.py:259` asserts (`under "tables", then run …`) is split mid-sentence. The split cannot be avoided: the second sentence alone is 148 characters. The test asserts a piece that lies inside one literal, so it still passes.
- **Moved a trailing comment.** `test_contract_alerts.py` import: the note `add_device: a fixture used by name` is now the line above; `# noqa: F401` stays on the import. `test_schema_docs_shell.py:33` likewise.
- **Auto-wrap look.** Some wraps in tests use bracket alignment and leave a short last line (e.g. `(0, 2, 0), (2, 0,` / `100)])`). They are valid and readable enough; I did not re-flow them by hand, to keep the diff mechanical.
- **Prose orphans.** Wrapped docstring lines may leave a short second line; I did not re-flow whole paragraphs.

## 5. Not done, deferred, assumed

- No browser run (no frontend file changed).
- The same test for smtw-common's own files: not in this step.
- Assumed: the `.claude/` prefix covers the synced `.claude/hooks/*.py` (BR1-02).

## 6. Manual checks

None in the brief.

## Docs updated

- `.claude/CLAUDE.md` § Yantra Specifics: new line *Python line width (S094)* (the rule, the test, the three exemptions).
- Other docs: none, because no migration, no secret, no module behaviour and no real-device check changed.

## Tests

- `tooling/run-tests.bat` with `YANTRA_TEST_RUN=s094c1`, one full run at the end: backend 4471 passed (127 s), frontend 412 passed (6 s), tooling 238 passed (2 s). ALL SUITES PASSED. The tooling count includes the 7 tests of `test_line_width.py`.
- Targeted: `tooling/tests/test_line_width.py` red then green as shown above.

## Feedback

- hindrance: my own helper scripts, written as heredocs, turned a doubled backslash into a single one and a `\r\n` escape inside a Python string became a real CR LF; one wrapped test line broke the file (it showed as a SyntaxError in the AST check) (`test_email_core.py:207`, 3 runs, about 5 min).
- idea: a `wrap-long-lines` helper in `tooling/` would help for the next such step, with the AST comparison built in (not tested here, since this step used throw-away scripts in `scratch/`).

## Fix round 1

Findings of `4-code-review-r1.md`, all answered.

- **CR1-01 Fixed.** `python_files` now returns only paths that exist as files (a path in the index but deleted in the working tree is left out). The temp-repo test adds a committed-and-indexed file, deletes it from disk, and expects it absent. Without the fix: `test_file_list_has_committed_and_untracked_and_leaves_out_ignored_and_deleted` fails (`'deleted.py' != 'untracked.py'`); with it: passes.
- **CR1-02 Fixed.** The 8 wraps now break at an outer bracket or use a local, so each argument stays whole: `test_alerts.py` (payload dict), `test_closed_email.py` (`json=` on its own line), `test_equipment_api.py` (two asserts), `test_improvement_timeline_api.py` (local `added`), `test_ticket_work_api.py` (local `restored_at`), `test_improvement_register_core.py` (parametrize list on one line), `tickets.py` (parenthesised conditional), `improvements.py` (tuple on one line). Same behaviour. The AST (strings with whitespace normalised) is identical to HEAD in 5 of the 8 files; the 3 test files `test_equipment_api.py`, `test_improvement_timeline_api.py` and `test_ticket_work_api.py` differ only where a local or a split assert was added.
- **CR1-03 Fixed.** Paragraphs re-flowed in `alerts.py`, `documents.py`, `equipment.py`, `properties_core.py` (two places) and `alerts_core.py`. All 13 edited files parse, and every string constant is the same with whitespace normalised. No line over 120.
- **CR1-04 Fixed.** `long_lines` raises `ValueError("<file>: the _MIGRATIONS block has no closing ']' at column 0")` when the block is still open at the end of the file. New test `test_migrations_block_without_closing_bracket_fails_clearly`. Without the fix: `DID NOT RAISE ValueError`; with it: passes.
- **CR1-05 Fixed.** Named in § 4 above.
- **CR1-06 Fixed.** § 4 now says "Five spots".

Line endings: `properties_core.py` and `test_ticket_work_api.py` stay all-CRLF (counts of CRLF and LF equal, by bytes); the others stay LF. Edits were by a script that reads and writes bytes.

Runs (`YANTRA_TEST_RUN=s094f1`): `tooling/run-tooling-tests.bat`: 239 passed. `tooling/run-backend-tests.bat` on the 11 files of the touched modules and tests (`test_alerts`, `test_alerts_core`, `test_closed_email`, `test_equipment_api`, `test_improvement_timeline_api`, `test_ticket_work_api`, `test_improvement_register_core`, `test_properties_core`, `test_documents_api`, `test_improvements_api`, `test_tickets_core`): 1208 passed. No full suite (wraps only), no browser run.

Docs updated: none, because only wraps and the new test's guards changed.

## Feedback (fix round 1)

- hindrance: a bash heredoc with a Python script turned `
` in my replacement text into real newlines, which broke the new test file (SyntaxError at collection); I found it only on the first run (1 run, 3 min).
