```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S048 — Code review, round 2 (verify)

**Verdict: no `blocker` or `major` finding is open.** All nine round-1 findings are fixed. The fix round brings in no new fault. There is 1 new nit.

Reviewed against: `refs/steps/S048` (c92549c) against its parent c7803b1, for the files that fix round 1 lists. The working tree matches the snapshot for all of those files. The S059 planning files were left out.

Files re-read in full: `tooling/changelog/release_changelog.py`, `tooling/changelog/notes-rules.md`, `tooling/tests/test_release_changelog.py`, `CHANGELOG.md`. Read in part: `frontend/e2e/changelog.spec.js` (the heading regex), `frontend/src/components/layout/ChangelogModal.vue` (the `v-for` keys), the `.claude/CLAUDE.md` diff, and the impl report (§ 4, § 5, § Texts for smtw-common, § Fix round 1). The brief's Review log entry "Code review r1" was read.

## Tests run

- **Tooling suite** (`YANTRA_TEST_RUN=s048cr2`, `tooling/run-tooling-tests.bat`): PASSED, 184 passed. That is 10 more than in round 1, which matches the report.
- **Frontend suite** (`YANTRA_TEST_RUN=s048cr2`, `tooling/run-frontend-tests.bat`): PASSED, 189 passed. I ran it because `ChangelogModal.vue` changed.
- **Backend suite**: not run. The fix round touched no backend file, and the coder's full run `s048f1` shows 3075 passed.
- **Browser tests**: none re-run. No finding of mine needs a browser run. The coder ran the targeted spec `e2e/changelog.spec.js` on `desktop-chromium` (3 passed). That is the right spec, because the fix round changed only that spec and the dialog's keys.
- **Real Claude CLI**: not called.

## Round-1 findings

| ID | Severity | Status | Verified |
|---|---|---|---|
| CR1-01 | minor | Fixed (the parts in scope) | `notes-rules.md` says "1 to 8 items … Do not pad to a number", and has the new rule "State only what the commits say. Do not add, guess or infer a feature that no commit names." `main()` prints each item through `say()`, which replaces characters the console cannot show. The departure from brief § 1.2 ("3–8 items") is in the fix round section and in the brief's Review log. The step-number filter and the release stop are held for KLA at gate B, so they are not open findings here. Test: `test_main_prints_the_items_it_wrote`. |
| CR1-02 | minor | Fixed | `choose_items` reads the notes file inside `try/except (OSError, UnicodeDecodeError)`, prints the "cannot be read … not used" line and goes on to Claude. An unreadable rules file gives an empty section and skips the Claude call. Both tests use bytes that are not UTF-8. The red result is given (with `except OSError` only, the notes test fails). |
| CR1-03 | minor | Fixed | Eight stubbed tests cover success (including the commit list on stdin), timeout, a failing exit, `OSError`, output with no bullet, notes for HEAD (Claude not called) and notes for another commit (the "not used" line, then Claude). `subprocess.run` is patched, so no test calls the real CLI. The red result is given for the `returncode` check. The § 5 sentence about stubs is corrected. |
| CR1-04 | minor | Fixed | The smtw-common text now has the full docstring and a shell test, `test_carry_reads_the_allowed_files_from_the_environment`, that sets `STAMP_CARRY_FILES` and asserts the note is written, then deletes the variable and asserts `None`. The test uses the real fixtures (`FakeGit`, `this_machine`, `a_stamp`). The red result is given (`split(";")`). |
| CR1-05 | nit | Fixed | `VERSION.replaceAll(".", "\\.")`, so the regex dots are literal. |
| CR1-06 | nit | Fixed | `notes_for_head` calls `notes_file_sha` and compares the result with `head_sha`. |
| CR1-07 | nit | Fixed | The `git add` exit 1 is in § 4 "Decisions taken". |
| CR1-08 | nit | Fixed | `:key="`${n}-${entry.version}`"`. |
| CR1-09 | nit | Fixed | Each of the eight back-fill items is one sentence, and the urgency wording is gone. |

## Findings

No new `blocker`, `major` or `minor` finding.

## Nits

- **CR2-01** (nit) `tooling/changelog/release_changelog.py:160`: the release console prints "(1 items)" for a one-item release, and with CR1-01's "1 to 8 items" that case is now common. Print "1 item" for one item and "N items" for more, and change the assert in `test_main_prints_the_items_it_wrote` to match.

## Manual browser checks for the user

- None needed. The brief has no real-device check. The three `[auto]` checks have a passing run behind them (`e2e/changelog.spec.js` on `desktop-chromium`, 3 passed after the fix round).
- Plain note: KLA reads the back-filled 0.1.10 section of `CHANGELOG.md`, and the items the hook prints in the first real release.
- For KLA at gate B (held from CR1-01, not open here): the step-number filter (option b) and the release stop (option c).

## Checked and found consistent

- **The fix round's diff brings in no new fault.** `say()` encodes and decodes with the console's own encoding and `errors="replace"`, so it cannot raise on a cp1252 console. When `sys.stdout.encoding` is `None`, it falls back to ASCII. The item lines print as "  - <item>", because the items already start with "- ".
- **The exit codes.** The hook still exits 1 only when `CHANGELOG.md` cannot be read or written, or when `git add` fails. The second case is a decision recorded in § 4. A notes or rules file that cannot be read now ends with exit 0, as brief § 1.2 asks.
- **The rules text.** "1 to 8 items" agrees with "If no commit changes what the app does or shows, output nothing at all". Neither rule asks for padding.
- **The tests' isolation.** The `shell()` helper points `RULES_FILE` and `NOTES_FILE` at `tmp_path`, and `monkeypatch` restores them. No test reads the real `scratch/release-notes.md` or calls git or Claude.
- **Docs pass.** The `.claude/CLAUDE.md` § Yantra Specifics *Release* sentence says that the hook prints the items, skips an unreadable notes or rules file, and stops a release only when `CHANGELOG.md` cannot be written. That matches the code. No other listed doc is due.
- **Track.** Light still holds: no migration, no RBAC change, no new dependency.

## Feedback

- hindrance: Git Bash turned `git show refs/steps/S048:<path>` into a Windows path list, and git rejected the argument; `MSYS_NO_PATHCONV=1` fixed it (2 commands).
- idea: the orchestrator's spawn prompt could say that the working tree equals the snapshot, so the reviewer can skip the compare (1 command).
