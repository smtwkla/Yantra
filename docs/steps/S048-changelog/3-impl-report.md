```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: impl-report
Author: Coder (Sonnet)
Date: 26-10-2026
```

# S048 — Implementation report

## 1. What was built

- `CHANGELOG.md` at the repo root, with one back-filled section `## 0.1.10 — 25-10-2026` (8 items).
- The sidebar's version number is a button for holders of `settings:edit` (IT Admin, Admin). It opens the dialog "What changed in Yantra". Everyone else sees plain text.
- The release hook `tooling/changelog/release_changelog.py` writes each release's section into `CHANGELOG.md` and stages it. The three Release run configs call it as `POST_BUMP_SCRIPT`.
- (Amendment A1: the rules file `tooling/changelog/notes-rules.md` is removed; the Claude path runs the pre-flight skill, `/pre-flight notes unattended`.)

## 2. How it works

- **Bundling.** `vite.config.js` reads `../CHANGELOG.md` (required, no fallback) and defines `__APP_CHANGELOG__`. `Dockerfile.frontend` copies the file beside `VERSION`.
- **Parser** `utils/changelog.js` (pure): every `## ` line opens a block, split at the first ` — ` or ` - ` into version and date; a leading `v` is dropped; `- ` lines are items; an indented line right after an item joins it; all other lines are skipped. Text only, no HTML.
- **Dialog** `ChangelogModal.vue`: a plain Bootstrap modal in `<Teleport to="body">`, with `open()` / `close()` called through a template ref. One block per version ("v0.1.10 — 25-10-2026"), a "This version" badge on the running one, "No entry for v… yet." when the running version has no block, "No changes are recorded yet." when the file has no block, "No notes were written for this version." for an empty block, and one "Close" button. It scrolls inside when long.
- **Hook.** The items come from the first source that works: (a) `scratch/release-notes.md` when its first line `<!-- commit <sha> -->` names HEAD (another commit's file is ignored, with a printed line); (b) the Claude CLI (`claude -p --model sonnet --tools "" --no-session-persistence <rules>`, commit list on stdin, 180 s limit, only `- ` lines kept); (c) an empty section, with the reason printed. It inserts `## <version> — <DD-MM-YYYY, IST>` after the `# ` title, runs `git add CHANGELOG.md` and prints one line naming the source. It exits 1 only when `CHANGELOG.md` cannot be read or written, or `git add` fails.
- The commit list is `git log <last v-tag>..HEAD --no-merges`, release commits skipped (`--invert-grep --grep=^release v`).

## 3. Files touched

| File | Change |
|---|---|
| `CHANGELOG.md` (new) | The file and the 0.1.10 section |
| `frontend/vite.config.js` | Reads `../CHANGELOG.md`, defines `__APP_CHANGELOG__` |
| `tooling/build/Dockerfile.frontend` | `COPY CHANGELOG.md /build/CHANGELOG.md` |
| `frontend/src/utils/changelog.js` (new) | `parseChangelog` |
| `frontend/src/components/layout/ChangelogModal.vue` (new) | The dialog |
| `frontend/src/components/layout/AppSidebar.vue` | Version button for `settings:edit`, dotted underline, `title="See what changed"` |
| `frontend/tests/changelog.test.js` (new) | 10 parser tests |
| `frontend/e2e/changelog.spec.js` (new) | 3 browser tests |
| `tooling/changelog/release_changelog.py` (new) | The hook |
| `tooling/changelog/notes-rules.md` (new; deleted in A1) | The prompt |
| `tooling/tests/test_release_changelog.py` (new) | 10 tests |
| `.idea/runConfigurations/Release__{patch,minor,major}_.xml` | `POST_BUMP_SCRIPT` env (`.idea/` is gitignored, so this change is local to this machine) |
| `.claude/CLAUDE.md`, `docs/steps/S048-changelog/1-brief.md`, `docs/steps/INDEX.md` | Docs pass, status |

## 4. Decisions taken

- The hook treats a missing `CHANGELOG.md` as empty and creates it. The brief says the file is required in the bundle; the hook only writes. A file that exists but cannot be written exits 1.
- The hook also exits 1 when `git add CHANGELOG.md` fails (the brief says exit 1 only for an unreadable or unwritable `CHANGELOG.md`). An unstaged file would leave the tree unclean for the next release.
- `notes_file_sha` is a small extra pure helper, used only to name the other commit in the "not used" line.
- `.idea/` is gitignored, so the run-config change is not in a commit. KLA should set the env var on other machines.
- The e2e tests carry `{ tag: "@device" }` and skip on `phone-chromium`, as the brief's tag rule says. The manager test uses the seed person `manager`.

## 5. Not done, deferred or assumed

- **The one Claude check, by hand.** `claude -p --model haiku --tools "" --no-session-persistence "<notes-rules.md>"`, with the whole history up to v0.1.10 (15 KB) on stdin, gave exit 0 and three `- ` lines. They broke the rules: one names a step number ("S048 changelog modal"), one invents things the history does not say ("a Keycloak-free dev login check, and an accessible feedback view"), and few commits are covered. Haiku is a weak model and the input was the whole history, not one release's commits, so this does not test Sonnet on a normal release. The format (only `- ` lines, exit 0) works. KLA should read the first real hook output. A guard that rejects lines with a step number is not built, as the brief does not ask for it.
- Because of that, the back-fill in `CHANGELOG.md` was drafted by me from the commit subjects, not taken from Claude's output. KLA reads it at gate B.
- The hook's Claude path (timeout, failing exit, no items, success) and its notes paths are covered by tests with `subprocess.run` patched (added in fix round 1); `git add` is covered by a stubbed `_git`. No real release and no `claude -p` with Sonnet was run.
- `docs/Plan.MD`: checked, it lists no admin screens or sidebar version, so no change due.
- Until the text below is applied in smtw-common, a retry after a failed build or deploy re-tests (accepted in the brief). Once applied, Yantra's Release run configs also need `STAMP_CARRY_FILES=CHANGELOG.md`; it is not set now, as nothing reads it yet.
- The dialog is desktop-only, as the brief says.

## 6. Tests

- New browser spec alone (`desktop-chromium`, 1 lane): 3 passed.
- Whole browser suite at Normal, once: 214 passed, 7 skipped (3 are the new tests on `phone-chromium`), 0 failed, 1.9 min.
- Full unit suites (`YANTRA_TEST_RUN=s048c1`): backend 3075 passed, frontend 189 passed (10 new), tooling 174 passed (10 new).
- `npx vite build` passes (only the known chunk-size warning).

## Manual checks

- [auto] IT Admin sees the version as a button, opens the dialog, sees "This version", Close is in view and closes it — `frontend/e2e/changelog.spec.js::S048: it_admin opens the change log from the version in the sidebar`
- [auto] Admin does the same — `frontend/e2e/changelog.spec.js::S048: admin opens the change log from the version in the sidebar`
- [auto] A manager sees the version as plain text, no button — `frontend/e2e/changelog.spec.js::S048: a manager sees the version as plain text, not a button`
- [auto] Parser cases (two versions, both dash types, skipped lines, empty text, heading with no items, markup as text, no-dash heading, leading `v`, re-wrapped item) — `frontend/tests/changelog.test.js`
- [auto] Hook core and shell (no Claude, no notes file: an empty section, exit 0) — `tooling/tests/test_release_changelog.py`
- Plain note: KLA reads the back-filled 0.1.10 section in `CHANGELOG.md`.

## Docs updated

- `.claude/CLAUDE.md`: § Pre-flight setting *Release notes*; § Yantra Specifics *Release* gets the change-log sentence; § SMTW-Review spec-to-step map gets `changelog` S048.
- `docs/Plan.MD`: none, because it names no admin screen or sidebar version.
- `docs/schema.md`, `docs/steps/device-checks.md`, `example_secrets_app.py`, `docs/Keycloak.md`: none, because no migration, real-device check, secret or role changed.

## Texts for smtw-common

For `tooling/common/preflight_stamp.py` and its test. Checked in a scratch copy: the carry tests pass with these changes. The core stays pure, so the extra files come in as a parameter and the shell reads the variable.

1. `carry_text` takes `also_allowed`:

```python
def carry_text(parent_note, parent_sha, changed_files, release_sha, test_cmd, now, machine,
               also_allowed=()):
    """The stamp for a release commit, or None.

    Carried only when the parent's stamp is valid and the release commit changes VERSION and at
    most the files in `also_allowed`.
    The carried stamp keeps the parent's tested_at, so it expires with the original."""
    changed = set(changed_files)
    if "VERSION" not in changed or not changed <= {"VERSION", *also_allowed}:
        return None
```

2. `carry()` passes the files from the environment (`STAMP_CARRY_FILES`, comma-separated; Yantra sets `CHANGELOG.md`):

```python
also_allowed = [f.strip() for f in os.environ.get("STAMP_CARRY_FILES", "").split(",") if f.strip()]
text = carry_text(read(parent), parent, changed.splitlines(), release_sha, test_cmd,
                  now_ist(), machine_name(), also_allowed)
```

3. A test in `tooling/tests/test_preflight_stamp.py`, beside the other carry tests:

```python
def test_carry_text_when_version_and_an_allowed_file_changed():
    note = a_stamp(sha=OTHER_SHA)
    kwargs = dict(also_allowed=["CHANGELOG.md"])
    now = TESTED_AT + timedelta(hours=1)
    assert ps.carry_text(note, OTHER_SHA, ["VERSION", "CHANGELOG.md"], SHA, CMD, now, MACHINE, **kwargs)
    assert ps.carry_text(note, OTHER_SHA, ["VERSION", "pyproject.toml"], SHA, CMD, now, MACHINE, **kwargs) is None
    assert ps.carry_text(note, OTHER_SHA, ["CHANGELOG.md"], SHA, CMD, now, MACHINE, **kwargs) is None  # VERSION must change
    assert ps.carry_text(note, OTHER_SHA, ["VERSION", "CHANGELOG.md"], SHA, CMD, now, MACHINE) is None  # default: VERSION only
```

4. A shell test beside `test_carry_writes_the_carried_stamp` (checked in a scratch copy, red when `split(",")` is changed to `split(";")`):

```python
def test_carry_reads_the_allowed_files_from_the_environment(monkeypatch, this_machine):
    written = {}
    monkeypatch.setattr(ps, "_git", FakeGit({("rev-parse",): (0, OTHER_SHA + "\n"),
                                             ("diff",): (0, "VERSION\nCHANGELOG.md\n"),
                                             ("notes",): (0, a_stamp(sha=OTHER_SHA))}))
    monkeypatch.setattr(ps, "_add_note", lambda sha, text: written.update(sha=sha, text=text))
    monkeypatch.setenv("STAMP_CARRY_FILES", " CHANGELOG.md ,")
    assert ps.carry(SHA, CMD) == "The pre-flight stamp of bbbbbbb is carried to the release commit aaaaaaa."
    assert written["sha"] == SHA
    monkeypatch.delenv("STAMP_CARRY_FILES")
    written.clear()
    assert ps.carry(SHA, CMD) is None
    assert written == {}
```

The module's header comment ("changes only VERSION") and the `carry()` docstring should then say "VERSION and the files in STAMP_CARRY_FILES".

## Feedback

- hindrance: a Python script that edited `.claude/CLAUDE.md` failed an assert on a line it contains (a backslash path), costing a retry (2 tool calls); the `Edit` tool would have avoided it.
- waste: the one allowed `claude -p` check ran on the whole 15 KB history, which is not a release's commit list, so it showed little about the real path (1 call).
- idea: the brief could say that `.idea/` is gitignored, so the run-config change is not reviewable in a diff (found only by `git check-ignore`).

## Fix round 1

Answers `4-code-review-r1.md`. Run name `s048f1`.

### Round 1

- **CR1-01 Fixed (rules text and printing only).** `notes-rules.md`: "3 to 8 items" is now "1 to 8 items, as many as the commits give. Do not pad to a number", and a new rule says "State only what the commits say. Do not add, guess or infer a feature that no commit names." **This departs from the brief's "3-8 items" (section 1.2), because of CR1-01.** The hook now prints each item it wrote under its one line (`  - <item>`), through `say()`, which replaces characters the console cannot show. Not built, by instruction: the step-number filter (option b) and a release stop (option c). KLA decided at gate B (26-10-2026): option (a), so no filter and no release stop (brief, Review log "Gate B"). Test: `test_main_prints_the_items_it_wrote`.
- **CR1-02 Fixed.** `choose_items` reads the notes file inside `try/except (OSError, UnicodeDecodeError)`, prints "scratch/release-notes.md cannot be read (...); not used." and goes on to Claude. An unreadable rules file gives an empty section "the rules file cannot be read (...)" and the Claude call is skipped. Tests: `test_notes_file_that_is_not_utf8_is_skipped`, `test_rules_file_that_is_not_utf8_skips_claude`. Red without the fix: with `except OSError` only, the notes test fails with `UnicodeDecodeError`; with the fix, it passes.
- **CR1-03 Fixed.** Eight tests with `subprocess.run` patched (the real CLI is never called): success (also checks the commit list goes to stdin), timeout, failing exit (a `- Please run /login` line is not an item), `OSError`, output with no bullet, a notes file for HEAD (Claude not called), a notes file for another commit (the "not used" line, then Claude). Red without the fix: with the `returncode` check disabled, `test_claude_failing_exit_is_not_turned_into_items` fails (`['- Please run /login'] == []`); with the check, it passes. The report's "tested with stubs" sentence in section 5 is corrected.
- **CR1-04 Fixed (report text only).** The `## Texts for smtw-common` docstring is written out in full, and item 4 adds the `FakeGit` test with `monkeypatch.setenv`. Checked in `scratch/cr04/` (copies of `preflight_stamp.py`, its test and the conftest): the 9 carry tests pass; the new env test fails when `split(",")` becomes `split(";")`. The `release.py` tests fail there only because `release.py` is not in the scratch copy. `tooling/common/` and smtw-common are untouched.
- **CR1-05 Fixed.** `changelog.spec.js`: the dots are now escaped for the regex (`"\\."` in the JS string). Spec run alone on `desktop-chromium`: 3 passed.
- **CR1-06 Fixed.** `notes_for_head` calls `notes_file_sha` and compares the sha.
- **CR1-07 Fixed.** The `git add` exit 1 is in "Decisions taken".
- **CR1-08 Fixed.** `ChangelogModal.vue`: key is `${n}-${entry.version}`.
- **CR1-09 Fixed.** Each back-fill item is one sentence. The urgency sentence is dropped from item 1; item 4 is reworded; items 5 to 7 are shortened to what the commits state.

**Tests (final full run, `YANTRA_TEST_RUN=s048f1`):** backend 3075 passed, frontend 189 passed, tooling 184 passed (10 new in `test_release_changelog.py`, 20 in all). `npx vite build` passes (chunk-size warning only). Browser: `e2e/changelog.spec.js` on `desktop-chromium`, 3 passed; the whole suite was not run, as instructed.

**Docs updated:** `.claude/CLAUDE.md` § Yantra Specifics *Release* (the change-log sentence: the hook prints the items, skips an unreadable notes or rules file, and only an unwritable `CHANGELOG.md` stops a release). `docs/Plan.MD`, schema, device checks, secrets, Keycloak: none, because nothing they describe changed.

### Feedback

- idea: a short note in the coder prompt that `python - <<EOF` with `
` inside a heredoc arrives as a real newline here would save the two broken edits (2 tool calls); use the `Edit` tool for any text with backslashes.

## Fix round 2

- **CR2-01 Fixed.** `release_changelog.py` prints "1 item" for one and "N items" otherwise. `test_main_prints_the_items_it_wrote` now asserts "from Claude (1 item)"; the new `test_main_prints_a_plural_count_for_two_items` asserts "(2 items)". Red then green: with the old line the singular assert fails ("(1 items)" printed); with the fix both pass.
- **Gate B recorded.** KLA chose CR1-01 option (a): no step-number filter and no release stop. The Round 1 CR1-01 answer says so now; `.claude/CLAUDE.md` did not mention the wait, so it needed no change.

**Tests (`YANTRA_TEST_RUN=s048f2`):** tooling 185 passed (was 184; 1 new test).

**Docs updated:** none, because the round changed one print line and a report sentence.

### Feedback

- none

## Amendment A1 — notes by the pre-flight skill

- **What changed.** The Claude path of `release_changelog.py` no longer sends the rules file as a prompt. It runs the pre-flight skill from the repo root, with the commit list on stdin: `claude -p "/pre-flight notes unattended" --model sonnet --tools Read --strict-mcp-config --no-session-persistence`. `CLAUDE_TIMEOUT_S` is 300. `ask_claude(commits)` lost its prompt argument; the "rules file cannot be read" case is gone. `clean_items`, the notes-file path, the fallbacks and their messages are unchanged (no message named 180 s or the rules file, except that one case).
- **Files.** `tooling/changelog/release_changelog.py` (changed); `tooling/changelog/notes-rules.md` (deleted); `tooling/tests/test_release_changelog.py` (rules-file test removed, `shell()` lost its rules file and now sets `REPO_ROOT`, timeout test uses 300, new `test_claude_is_run_as_the_pre_flight_skill_from_the_repo_root` asserts the command line, `cwd`, stdin and timeout); `.claude/CLAUDE.md` (3 edits). Sections 1 and 3 of this report were corrected where they described the current design; the older fix-round text is history and unchanged.
- **Tests (`YANTRA_TEST_RUN=s048a1`).** `tooling/run-tooling-tests.bat`: 185 passed. No backend, frontend or browser run (no code or screen there changed). No test calls the real CLI.
- **Decisions.** The skill name and mode words are one constant, `CLAUDE_PROMPT`. A comment points to the skill's § 3c for the rules. `REPO_ROOT` is the `cwd`, so the skill and its files are found.
- **Docs updated:** `.claude/CLAUDE.md` § Pre-flight *Release notes* line (exact text from the amendment) and § Yantra Specifics *Release* (skill call; "or rules" dropped). Others: none, because nothing they describe changed.

### Feedback

- none

## Fix round 3 (code review r3, by the orchestrator, 26-10-2026)

- CR3-01 (minor), CR3-02 (nit): skill text in `../smtw-common/.claude/skills/pre-flight/SKILL.md`
  (§ 0: the first line of the arguments is the mode, the rest the input; § 3b step 1: where the
  commits are and their form; § 1: unattended prints nothing). Uncommitted, for KLA to sync.
- CR3-03 (nit): `tooling/changelog/release_changelog.py` docstring re-wrapped.
- Tests: `tooling/run-tooling-tests.bat` (`YANTRA_TEST_RUN=s048f3`): 185 passed.

