```
Step: S094 — Python lines at most 120 characters
Doc: code review r2
Author: Code reviewer (Opus)
Date: 01-11-2026
Status: Done — 0 blocker, 0 major, 0 minor, 0 nits
```

# S094 — Code review, round 2

**Verdict: no blocker or major finding is open.** All six findings of round 1 are fixed, and the fix round
brings in no new fault.

## Test results

- `YANTRA_TEST_RUN=s094cr2 tooling/run-tooling-tests.bat`: PASSED, 239 passed (1 s). That is round 1's 238
  plus the new `test_migrations_block_without_closing_bracket_fails_clearly`.
- No backend run: no finding of mine needs one. The coder ran the 11 backend test files of the touched
  modules (1208 passed, `s094f1`).
- No full suite, no browser run, no schema docs check: the fix round touches no screen, API,
  `local_db.py` or `docs/schema/`.

## Round 1 findings

| ID | Status | Checked how |
|---|---|---|
| CR1-01 | Fixed | `python_files` keeps only paths that exist as files. The temp-repo test indexes `deleted.py`, removes it from disk and expects it absent. The red result is reported (`'deleted.py' != 'untracked.py'`). |
| CR1-02 | Fixed | The 8 wraps now break at an outer bracket or use a local. Each argument stays whole. |
| CR1-03 | Fixed | The docstring paragraphs in the 5 production modules are re-flowed with no orphan line in the middle. |
| CR1-04 | Fixed | `long_lines` raises `ValueError` when the `_MIGRATIONS` block is still open at the end of the file. The flag is reset per file, so the check is per file. The new test uses `]  # end` and expects the error. The red result is reported (`DID NOT RAISE`). |
| CR1-05 | Fixed | § 4 of the report names the split in `schema_docs_core.py:291-292` as a rule-4 exception. |
| CR1-06 | Fixed | § 4 says "Five spots". |

## How I checked the fix round's diff

- **Syntax trees** (my own script, round 1's snapshot `2c2b39f` against the working tree, string constants
  with whitespace normalised, the 14 files of the diff):
  - 10 files have an identical tree;
  - `test_equipment_api.py`, `test_improvement_timeline_api.py` and `test_ticket_work_api.py` differ only by
    the local or the split assert the report names. The split of `a == sorted(…) == b == c` into
    `a == sorted(…)` and `a == b == c` asserts the same thing;
  - `test_line_width.py` differs by the two new guards and their tests.
- **Line endings by bytes:** `properties_core.py` and `test_ticket_work_api.py` are all-CRLF in the working
  tree, the other 12 files all-LF. No file has a lone CR, and every file ends with a newline. Git stores all 14
  as LF (`git ls-files --eol`: `i/lf`), so the CRLF of the two files is the checkout's `core.autocrlf`, as in
  round 1.
- **Line width:** the longest line in the 14 files is 120 characters.

## Nits

None.

## Checked and found consistent

- Files I re-read: the 14 files of the fix round's diff (hunks), `tooling/tests/test_line_width.py` lines
  1-70 in full, and `3-impl-report.md` § Fix round 1.
- The new `git add` in the temp-repo test stages only inside `tmp_path`, never the repo's index.
- Docs pass: the fix round changes only wraps, docstrings and the test's guards, so no doc is due. The
  report says so.

## Manual checks

None. The brief has no manual check.

## Feedback

- idea: my round 1 scripts had to be written again for round 2 (syntax trees with normalised strings, line
  endings by bytes, against a snapshot ref). A `step_snapshot.py` option that prints both for the files of
  `diff --from-round N` would save each round of a mechanical step (scratchpad `cmp_r2.py`, about 3 min).
