```
Step: S094 — Python lines at most 120 characters
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 01-11-2026
```

Reviewed against: f8a699c (no uncommitted step code; only `docs/steps/INDEX.md` and the S093 brief are modified)

**Verdict: no `blocker` or `major` is open.** BR1-01 (major) is answered in § 1 and the answer holds. Two `minor`
findings remain, both in the text added since round 1. Round 2 re-read only the diff of
`scratch/S094-brief-r1.md` against the brief: § 1 (the test's file list, root, checker function; the synced
prefixes), § 3 (the split rules), § 4 (universal newlines) and the Review log. Light track: round 1 was meant to
be the only round; this round exists because round 1 had a major.

## Findings

### BR2-01 — minor — § 3 rules 3 and 4 contradict each other on the one line both name

**Problem.** Rule 3 names `tooling/schema/schema_docs_core.py:219` as a literal to split. Rule 4 says a message
a user sees or a test asserts is "never split; break the code around it instead". Line 219 is both: a CLI
message, asserted by `tooling/tests/test_schema_docs_core.py` (`"must hold one object" in …` and
`endswith("Fix the file, then run the command again.")`). The code around it cannot help: the line is 136
characters, the literal alone is 115, and at the 12-column indent inside a bracket it is still 127.

**Why it matters.** The coder has to choose between two rules of the brief for the first literal it meets.

**Options.**
- A (recommended): add to rule 4: when the literal alone does not fit (rule 3), split it at a sentence end so
  each phrase a test asserts or a reader would search stays in one piece. For line 219 that is
  `"… one object {{...}}. "` + `"Fix the file, then run the command again."`; both asserted phrases stay whole
  and `git grep` still finds them.
- B: shorten the message so it fits. Changes a user-visible text in a wraps-only step; rejected.

### BR2-02 — minor — The fix of BR1-01 (the `--others` flag) has no test

**Problem.** § 1 lists the files with `git ls-files --cached --others --exclude-standard -- "*.py"`. § 5's
tests feed the checker paths directly (BR1-05) and run the real tree; none proves that the list holds an
untracked file. Today the lists with and without `--others` are the same (189 files), so a coder who writes
`git ls-files -- "*.py"` by habit passes every test, and the major of round 1 is back unnoticed. The test file
itself is untracked while the step is coded, which hides nothing because it has no long line.

**Why it matters.** The flag is the reason for round 2; the brief's own acceptance should show it.

**Options.**
- A (recommended): one more temp-tree test in § 5: `git init` in `tmp_path`, one `.py` staged, one untracked,
  one ignored by a `.gitignore` there; the list function returns the first two. (`git add` in a temp repo is
  not the repo's index: README § Shell on Windows, rule 8 is about this repo.)
- B: say in § 5 that the flag is git's documented behaviour and is not tested. Cheaper; the regression stays
  possible.

## Nits

- **BR2-03** (nit) § 4 *Characters, not bytes*: with universal newlines `len(line)` still counts the `\n` of a
  line read by iteration; say the newline is stripped first (`read().splitlines()`, as
  `scratch/count_long_lines.py` does), or a 120-character line fails as 121.

## Checked and found consistent

- BR1-01: `git ls-files --cached --others --exclude-standard -- "*.py"` at f8a699c lists the same 189 files as
  `git ls-files -- "*.py"` (no untracked `.py` today). `.gitignore` excludes `scratch/`, `/data/`, `.venv/`,
  `frontend/node_modules/`, `__pycache__/` and `backend/secrets_*.py`, so the secrets file is never read.
  Files in an untracked folder are listed one by one (no `--directory`). The pathspec matches at any depth.
- BR1-02: the five prefixes cover every synced `.py`: `tooling/common/*.py` (eight in `sync_common.FILES` plus
  `sync_common.py` itself), `tooling/deps/audit.py` and `audit_core.py` (`FILES`), `tooling/steps/`,
  `tooling/roadmap/`, `.claude/hooks/`, `.claude/skills/`, `.claude/agents/` (`DIRS`). `.claude/` holds one
  tracked `.py`, `hooks/guard-common.py`, and none of Yantra's own.
- BR1-06: `Path(__file__).resolve().parents[2]` from `tooling/tests/test_line_width.py` is the repo root.
- BR1-08: the three f-strings named in rule 3 are the ones round 1 named; line 288 is already two adjacent
  `f"…"` pieces.
- BR1-09: rule 5 cites README § Shell on Windows rule 7, which is the line-endings rule (31-10-2026).
- The Review log answers every round-1 finding, and each accepted answer is in the brief's text, not only in
  the log. BR1-04 is left to the user at gate A, as the rule asks.

## Feedback

- none
