```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 26-10-2026
```

# S048 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 4 minor findings and 5 nits. One minor finding (CR1-01) needs KLA's decision at gate B.

The dialog, the sidebar button, the bundling and the parser match the brief. The release hook follows the brief and never stops a release on a Claude fault. The `## Texts for smtw-common` text is correct.

Reviewed against: c7803b1 + the uncommitted S048 files only (the files the orchestrator listed). The S059 planning changes (`docs/Plan.MD`, `docs/roadmap/*`, `docs/steps/INDEX.md`, `docs/steps/S059-token-checks/`) were left out.

## Tests run

- **Unit suites** (`YANTRA_TEST_RUN=s048cr1 tooling/run-tests.bat`): all PASSED. Backend 3075 passed, frontend 189 passed, tooling 174 passed.
- **Build check** (`npx vite build`, output to `scratch/s048cr1-dist`): passes, with only the known chunk-size warning.
- **Browser tests**: none re-run. No finding of mine needs a browser run. The coder's report names the right specs: the new spec alone on `desktop-chromium` (3 passed) and the whole suite at Normal once (214 passed, 7 skipped, 0 failed). `screens.spec.js` is in that whole-suite run, and the brief adds no route.
- **Real Claude CLI**: not called.

## Findings

### CR1-01 (minor) — Claude's items go into the release with no check and no one reading them

`tooling/changelog/release_changelog.py:132-135`, `:152`; `tooling/changelog/notes-rules.md:5-11`.

**Problem.** On the Claude path, the hook writes Claude's lines into `CHANGELOG.md` and the release commit, and the build and deploy follow. Nobody sees the lines before IT Admin sees them in the app: the hook prints only the count ("… from Claude (5 items)"). The coder's one manual run (haiku, the whole history) gave a step number ("S048 changelog modal") and two invented features. The rules file also has two gaps that invite that fault:

1. "Write 3 to 8 items" conflicts with a patch release that has one app change. The model must pad to three items, which is how it invents.
2. Nothing says "use only what the commits say". The haiku run invented features the history does not name.

**Failure scenario.** KLA runs Release (patch) from PyCharm without a pre-flight, for a release with one bug fix. Claude writes three items, two of them made up, one naming "S061". The release commits, builds and deploys. IT Admin reads features that do not exist. A fix needs a new commit and the next release.

**Suggested fix.** Two parts:
- **Rules text** (within the brief's scope, the coder's text): change "3 to 8 items" to "1 to 8 items" (or "at most 8"), and add "Use only what the commits say. Do not add or guess features." The brief § 1.2 says "3–8 items", so the orchestrator should note the change in the Review log.
- **For KLA at gate B** (a design change, not for the coder to decide):
  - (a) keep as built: KLA reads `CHANGELOG.md` after each release that used Claude;
  - (b) **recommended**: the hook drops any line that names a step number (`\bS\d{3}\b`), and prints the items it wrote under its one line, so KLA sees them in the release output before the build. Cheap and deterministic. (Print with `errors="replace"` or ASCII-safe output: the PyCharm console may not be UTF-8.)
  - (c) also stop the release for a confirmation when the items came from Claude. This breaks "never stops a release" and an unattended run, so not recommended.

### CR1-02 (minor) — An unreadable notes file, rules file or VERSION aborts the release

`tooling/changelog/release_changelog.py:125`, `:132`, `:139`.

**Problem.** The brief § 1.2 says the hook exits 0 "in every case but one: `CHANGELOG.md` cannot be read or written". But `NOTES_FILE.read_text(encoding="utf-8")` and `RULES_FILE.read_text(...)` run outside any `try`. A `UnicodeDecodeError` or `OSError` there ends the hook with a traceback and exit 1, and `release.py` aborts ("Post-bump script failed.").

**Failure scenario.** KLA edits `scratch/release-notes.md` in Notepad, as the pre-flight report invites, and saves it as ANSI with an em dash in one item. The next release aborts at the hook with a `UnicodeDecodeError` traceback, after the version bump. The bumped `VERSION` stays in the working tree, so the retry first needs a manual `git checkout VERSION`.

**Suggested fix.** Read the notes file inside `try … except (OSError, UnicodeDecodeError)`, print "Release notes: scratch/release-notes.md cannot be read (…); not used." and go on to Claude. Treat a missing or unreadable rules file the same way ("empty section: the rules file cannot be read"). Add a test of an unreadable notes file (bytes that are not UTF-8) that ends with exit 0. `VERSION` can stay as it is: `release.py` just wrote it.

### CR1-03 (minor) — The hook's Claude path and notes path have no tests

`tooling/tests/test_release_changelog.py:70-93`.

**Problem.** The only shell test is "no Claude CLI, no notes file". `ask_claude`'s failure modes (timeout, non-zero exit, output with no `- ` line, `OSError`), its success path, and `choose_items`'s two notes cases (a file for HEAD; a file for another commit, with its "not used" line) are untested. The impl report says "The hook's Claude path and `git add` were tested with stubs only", but no test stubs the Claude call. CLAUDE-COMMON § Testing asks for the key failure modes. The brief listed only the one shell test, so this is not a scope gap, but these branches decide what goes into a release.

**Failure scenario.** A later edit swaps the order of the `returncode` check and `clean_items`. Claude's login error ("- Please run /login" or a similar line) then becomes a changelog item. No test turns red.

**Suggested fix.** Add stubbed tests (patch `rc.subprocess.run` and `rc.shutil.which`, no real CLI): timeout → empty section, the reason printed, exit 0; exit 1 → empty section; output with a preamble and two `- ` lines → two items "from Claude"; a notes file for HEAD → "from pre-flight"; a notes file for another sha → the "not used" line, then the Claude path. Correct the report's sentence about stubs to say what the tests cover.

### CR1-04 (minor) — The smtw-common text has no shell test for `STAMP_CARRY_FILES`

`docs/steps/S048-changelog/3-impl-report.md`, § Texts for smtw-common, item 3.

**Problem.** The text's change is correct: `carry_text` keeps "VERSION must change" and "at most the listed files", and `carry()` reads the variable. Its test covers only the pure `carry_text`. The new environment read in `carry()` (split at commas, stripped, empty items dropped) has no test. The existing shell tests in `smtw-common/tooling/common/tests/test_preflight_stamp.py:299-316` (`FakeGit`, `this_machine`) make one easy to add.

**Failure scenario.** A typo in the parsing (for example `split(";")`) leaves `also_allowed` empty. Every Yantra release commit then changes `VERSION` and `CHANGELOG.md`, the stamp is never carried, and a retry after a failed build re-tests for an hour. No test shows it.

**Suggested fix.** Add to the text a shell test beside `test_carry_writes_the_carried_stamp`: `monkeypatch.setenv("STAMP_CARRY_FILES", "CHANGELOG.md")`, `FakeGit` with `("diff",): (0, "VERSION\nCHANGELOG.md\n")`, and assert the note is written; a second case without the variable asserts `None`. Also replace the `"""...` placeholder in item 1's docstring with the full docstring text, so the block pastes as it stands.

## Nits

- **CR1-05** (nit) `frontend/e2e/changelog.spec.js:23`: `VERSION.replaceAll(".", "\.")` replaces "." with "." (in a JS string, `"\."` is `"."`), so the regex's dots match any character. Use `"\\."`.
- **CR1-06** (nit) `tooling/changelog/release_changelog.py:38-56`: `notes_for_head` repeats `notes_file_sha`'s parsing of the first line. Let `notes_for_head` call `notes_file_sha` and compare the result with `head_sha`.
- **CR1-07** (nit) `docs/steps/S048-changelog/3-impl-report.md` § 4: the hook also exits 1 when `git add CHANGELOG.md` fails. That is a departure from the brief's "every case but one", and a right one (an unstaged `CHANGELOG.md` would leave the tree unclean for the next release). The report names it only in § 2; add it to "Decisions taken".
- **CR1-08** (nit) `frontend/src/components/layout/ChangelogModal.vue:55`: `:key="entry.version"` gives a duplicate key when the file names one version twice (a hand-edit mistake). Use the index, or `` `${i}-${entry.version}` ``.
- **CR1-09** (nit) `CHANGELOG.md:4-11`: four of the eight items have two sentences, and the rules file asks for "one short sentence" per item. Also, "show a light background by how urgent it is" is hard to follow; "are coloured by how urgent the ticket is" says it plainly. KLA reads the back-fill at gate B anyway.

## Manual browser checks for the user

- None needed. The brief has no real-device check, and the three `[auto]` checks have a passing run behind them.
- Plain note (from the report): KLA reads the back-filled 0.1.10 section of `CHANGELOG.md`, and the first real section the hook writes.

## Checked and found consistent

- **The hook under `release.py`.** `release.py:181-184` runs it as `"{sys.executable} {PROJECT_ROOT / script}"` with `cwd=PROJECT_ROOT`, after the bump and only when there are changes. The hook finds its paths from `__file__` and uses only the standard library, so `release.py`'s uv interpreter runs it. Its output is not captured, so its lines show in the release console.
- **The sha check.** The release commit is not made yet when the hook runs, so HEAD is the commit the pre-flight saw. `notes_for_head` compares the full sha exactly; a notes file with zero items for HEAD gives an empty section "from pre-flight", which fits the rules ("nothing at all when no commit changes the app").
- **The Claude call.** `shutil.which("claude")` finds `C:\Users\KLA\.local\bin\claude.EXE` here, a real executable, so the multi-line prompt with quotes passes intact (a `claude.cmd` npm shim would mangle it through `cmd.exe`; not the case on this machine). stdin carries the commit list; `encoding="utf-8", errors="replace"` on both pipes; the 180 s timeout, `OSError` and a non-zero exit all give an empty section with the reason printed. `--tools ""` lets Claude change nothing.
- **The commit list.** `git describe --tags --abbrev=0 --match "v[0-9]*"`, then `git log <tag>..HEAD --no-merges`, release commits dropped. It matches `release.py`'s own range.
- **Line endings.** `write_text` writes CRLF on Windows; `core.autocrlf=true` stores LF; the parser splits on `\r?\n`, so a CRLF file from a Windows build worktree parses the same.
- **The departures.** The hook creates a missing `CHANGELOG.md`: harmless, as the bundle still requires the file and the release always has it. `notes_file_sha` is a small pure helper with one use, for the "not used" line: right-sized (but see CR1-06). Both are in "Decisions taken".
- **The dialog.** `<Teleport to="body">` (BR1-01); `open()` / `close()` through a template ref, as `PhotoViewer.vue`; `modal-dialog-scrollable`; all text through interpolation, no `v-html`, so a `<b>` in the file stays text. The four states are wired: "This version" badge, "No entry for v… yet." (only when blocks exist), "No changes are recorded yet." (no block), "No notes were written for this version." (empty block). One "Close" button. Scope B wording is plain and matches the brief.
- **The permission.** The button and the modal show only when `userPermissions` holds `settings:edit` (a key, not a role name). `/api/auth/me` gives Admin every key, and the Admin browser test proves it. No backend route, so no RBAC change.
- **The bundling.** `vite.config.js` reads `../CHANGELOG.md` with no fallback, like `VERSION`, and defines `__APP_CHANGELOG__` with `JSON.stringify`. `Dockerfile.frontend` copies it beside `VERSION`. The release and build worktrees get it through git once it is committed.
- **The parser.** It follows every rule of brief § 1 (BR1-04); the 10 vitest cases cover the brief's § 5 list, plus "an indented line after a blank line is not joined".
- **The browser tests.** Each asserts what the user sees: the button by its name, the dialog by its title, the running version's heading, the "This version" badge, Close `toBeInViewport` and the dialog hidden after Close; the manager test asserts plain text and no button. The `@device` tag is right by the tag rule (the tests run only on `desktop-chromium`), with the brief's `test.skip` on other projects.
- **The smtw-common text, item 1 and 2.** The set logic `"VERSION" in changed and changed <= {"VERSION", *also_allowed}` keeps today's behaviour with the default `()` and refuses a commit without `VERSION`. The test's four asserts are right against `a_stamp`, `OTHER_SHA`, `SHA`, `CMD`, `TESTED_AT` and `MACHINE` in the real test file.
- **The back-fill.** One section, `## 0.1.10 — 25-10-2026` (tag `v0.1.10` is dated 25-10-2026), eight items in users' words, with no step numbers, file names or code.
- **Docs pass.** `.claude/CLAUDE.md` has the *Release notes* setting under § Pre-flight, the change-log sentence in § Yantra Specifics *Release*, and `changelog` S048 in the spec-to-step map. `docs/Plan.MD` names no admin screen or sidebar version, so nothing is due. No migration, secret, role or device check.
- **Run configs.** The three `.idea/runConfigurations/Release__*.xml` carry `POST_BUMP_SCRIPT=tooling/changelog/release_changelog.py` (local only; `.idea/` is gitignored, as the report says).
- **Track.** Light holds: no migration, no RBAC change, no locking, no new dependency.
- **Manual checks.** The report's `## Manual checks` lists the brief's checks as `[auto]` with their tests.

## Feedback

- hindrance: the orchestrator had to list S048's files by hand, because the working tree mixes them with S059's planning files and `git status` cannot tell them apart (brief prompt, 12 paths).
- rule: the "unreported departure is at least major" rule does not say whether a departure named in § 2 "How it works" but not in "Decisions taken" counts as reported (CR1-07, judged nit).
- idea: the coder agent could add, for a hook or script that calls an external CLI, one stubbed test per failure branch to its checklist; the brief's § 5 named only the "CLI not found" case (CR1-03).
