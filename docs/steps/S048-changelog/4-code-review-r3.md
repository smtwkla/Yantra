```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S048 — Code review, round 3 (amendment A1)

**Verdict: no `blocker` or `major` finding is open.** The hook, its tests and the two `.claude/CLAUDE.md` lines do what A1 asks. There is 1 minor finding and 2 nits. The minor finding is in the skill text in `../smtw-common`: it says where the commits are, and that place is wrong for `claude -p`.

Scope: A1 only. Reviewed against the snapshot `refs/steps/S048` (c92549c), plus the skill text in `../smtw-common/.claude/skills/pre-flight/SKILL.md` (uncommitted there; read-only).

Files read in full: `tooling/changelog/release_changelog.py`, `tooling/tests/test_release_changelog.py` (the shell part, from `class Done`), `../smtw-common/.claude/skills/pre-flight/SKILL.md`. Read in part: the `.claude/CLAUDE.md` diff, the brief's § 7 A1 and the Review log "Gate A for A1", and the impl report § Amendment A1.

## Tests run

- **Tooling suite** (`YANTRA_TEST_RUN=s048cr3`, `tooling/run-tooling-tests.bat`): PASSED, 185 passed. That matches the impl report.
- **Backend and frontend suites**: not run. A1 touches no file of either.
- **Browser tests**: none, as the orchestrator asked. A1 changes no screen.
- **The real Claude CLI**: not run, by instruction.

## Findings

### CR3-01 (minor) — the skill looks for the commits in the wrong place and form

`../smtw-common/.claude/skills/pre-flight/SKILL.md` § 3b step 1, and § 0's table row `notes unattended`.

- **Problem.** § 3b says: "The commits are on the input, in the form of § 3a step 2; do not look for them anywhere else." Two parts of that are wrong for the hook.
  - Fact (read in the installed CLI's code, `claude.exe`, the function that reads piped stdin): in print mode the CLI joins the prompt and stdin as `[prompt, stdin].join("\n")`. So the model gets one message: `/pre-flight notes unattended`, a line break, then the commit list. The commits are the text after the mode words, inside the skill's arguments, not a separate input.
  - Fact: the hook's list (`release_changelog.py:91`, `--format=commit %h%n%s%n%b%n`) is `commit <short sha>`, the subject, the body and a blank line per commit. § 3a step 2 is `%H%n%s%n%b%n---`: a full sha with no `commit ` word, and a `---` line between commits.
  - Assumption: how the CLI splits a multi-line argument from the skill name. I did not settle this, but the commits reach the model either way, so it does not change the fix.
- **Failure scenario.** The model follows § 0 literally. The arguments are not exactly `notes unattended`, because 40 commit lines follow. The model picks "none" (the whole run) or `notes`. Both need a shell, and the hook allows only `Read`. The model then prints an explanation and no `- ` lines, or a few items written without § 3c's rules. The release writes an empty or rule-breaking section, and nothing in the log shows why. A model that looks for `---` lines may also merge commits wrongly.
- **Suggested fix** (orchestrator, in smtw-common). In § 0's table, make the third row `notes unattended`, followed by the commit list. In § 3b step 1, use this text:

  > 1. Read the *Release notes* setting (§ 1) for the readers. The commits follow the words `notes unattended` in the arguments (the hook pipes them on standard input, and `claude -p` adds them after the prompt). Each commit is a line `commit <short sha>`, its subject, its body, and a blank line. Release commits are already left out. Do not look for commits anywhere else.

  Also add one line to § 0: "The first line of the arguments decides the mode; any lines after it are the input."

## Nits

- **CR3-02** (nit) `../smtw-common/.claude/skills/pre-flight/SKILL.md` § 1, last line: the stop line "This repo has no Pre-flight section…" contradicts § 0's "print nothing" when the mode is unattended. Add "(unattended: print nothing)". The hook drops that line anyway, because it is not a `- ` line.
- **CR3-03** (nit) `tooling/changelog/release_changelog.py:7-10`: the docstring is wrapped badly ("or\nnothing (an empty\nsection)"). Re-wrap the sentence.

## Checked and found consistent

- The command line: `[claude, "-p", "/pre-flight notes unattended", "--model", "sonnet", "--tools", "Read", "--strict-mcp-config", "--no-session-persistence"]`, `cwd=REPO_ROOT`, the commits on `input`, `CLAUDE_TIMEOUT_S = 300` (`release_changelog.py:23-25`, `:104-108`). This matches A1 word for word. The list form passes the slash argument to the CLI unchanged, with no MSYS path conversion.
- Only `Read` is allowed, so the run cannot write a file or start a shell, and in print mode a refused tool fails at once instead of waiting for an answer. § 3b needs only `Read`: it reads the setting, and the commits come in the prompt. No step in § 3b or § 3c needs git or a shell.
- The fallbacks are unchanged: Claude missing, no commits, a timeout, `OSError`, a non-zero exit, and output with no `- ` lines each give an empty section and exit 0. The rules-file case is removed together with its test. Nothing else refers to `RULES_FILE`.
- `clean_items` keeps only the `- ` lines, so any text from the model outside the items (CR3-01, CR3-02) never reaches `CHANGELOG.md`.
- The tests: `test_claude_is_run_as_the_pre_flight_skill_from_the_repo_root` asserts the full argument list, `cwd`, stdin and the timeout. `shell()` now sets `REPO_ROOT` to the temp folder. The timeout test uses 300. No test calls the real CLI. This covers A1's § Tests.
- `tooling/changelog/notes-rules.md` is deleted. No code, test or doc outside the step's own history still names it. The leftovers in `scratch/` are gitignored drafts.
- `.claude/CLAUDE.md` § Pre-flight *Release notes* is exactly A1's text. It matches the form that skill § 1 gives as its example (`<file>; readers: …`). § Yantra Specifics *Release* names the skill call, says the run is read-only, points at § 3c, and no longer mentions a rules file.
- The skill's arguments and modes: none, `notes` and `notes unattended` each have one path. Unattended never asks a question, offers no options and never waits. It prints only `- ` lines, or nothing. § 3c holds every rule A1 lists: 15 words or fewer, present tense, no "now", one item per feature, only what a commit states, the leave-outs, no internals, and 1 to 8 items. Its release-commit rule matches the hook's `--invert-grep --grep=^release v`.
- The docs pass: `## Docs updated` names the two `.claude/CLAUDE.md` edits. `docs/Plan.MD` says nothing about release notes, and no other doc in § Docs to keep current is affected.
- Scope: nothing outside A1 was built, and `release.py` is unchanged.

## Manual checks still open

- [ ] After KLA commits, pushes and syncs smtw-common: run the hook's Claude path once by hand on a real range, with no notes file for HEAD. Confirm that the printed items follow § 3c: no step numbers, nothing the commits do not say. This is the only check of how the CLI passes the skill's arguments (CR3-01), and no unit test can make it.

## Feedback

- hindrance: to settle how `claude -p` joins the prompt and stdin, I had to search the 297 MB `claude.exe` for its JavaScript, because running the CLI was forbidden (4 searches, about 4 min).
- idea: the brief's two CLI checks (stdin with a plain prompt; a slash command with no stdin) left out the one combination the hook uses. Each "Checked" line in a brief should name the exact command line the code will run.
