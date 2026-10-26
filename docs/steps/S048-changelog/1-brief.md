```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: brief
Author: Orchestrator (Opus)
Date: 26-10-2026
Track: light
Status: Gate B (A1 coded, code review r3 fixed)
Baseline: c7803b1
```

# S048 — What changed: one CHANGELOG, opened from the version number

**The point:** one file, `CHANGELOG.md`, says in plain words what each release changed. It is
built into the frontend. Admin and IT Admin click the version number at the bottom of the sidebar
("v0.1.10") and read it in a dialog. Nothing is stored and nothing pops up by itself.

**Track: light** — frontend only, one new dialog on an existing pattern, no migration, no new
dependency, no RBAC change (it reuses the key `settings:edit`, § 4), about 7 files. U2 adds
the release-notes writer (§ 1.2): one small tooling script with its test, the three Release run
configs, and a text for smtw-common, about 13 files in all. Kept light: the new part is release
tooling, with no data, login or locking (KLA may say full at gate A).

**This replaces the queued S048** ("each version's notes, shown once to admin, IT admin and
engineers after a deploy; needs a migration: who has seen which version", user, 25-10-2026). KLA
changed it on 26-10-2026 (U1): one CHANGELOG file, bundled with the frontend, opened from the
version number by IT Admin and Admin. So: no "seen" table, no automatic display, no engineers.

## 1. What will be built, and out of scope

- **`CHANGELOG.md`** at the repo root, in a fixed, simple form (§ 1.1). The coder writes the
  first version of it (§ 6 Q2).
- **Bundled at build time:** `frontend/vite.config.js` reads `../CHANGELOG.md` as it reads
  `../VERSION` (`vite.config.js:14`) and defines `__APP_CHANGELOG__` (the raw text) next to
  `__APP_VERSION__` (`:27`). `tooling/build/Dockerfile.frontend` copies it as it copies `VERSION`
  (`:7`: `COPY VERSION /build/VERSION` → add `COPY CHANGELOG.md /build/CHANGELOG.md`). The file
  is required, as `VERSION` is: no fallback (BR1-05: the Docker `COPY` fails on a missing file
  anyway). A file with no version block (empty, or only the title) makes the dialog say "No changes
  are recorded yet."
- **The parser** `frontend/src/utils/changelog.js`, pure: `parseChangelog(text)` → a list of
  versions `{ version, date, items: [string] }`, in file order (newest first by convention).
  Rules (BR1-04): every line starting `## ` opens a block; its text is split at the first ` — ` or
  ` - ` into version and date (no dash: the whole text is the version, date `""`); a leading `v`
  is dropped from the version. A line starting `- ` under a block is a new item; an indented line
  (leading spaces) right after an item joins that item with one space (an editor's re-wrap). Every
  other line (the `#` title, blank lines, a paragraph, an item before the first heading) is
  skipped. No markdown library and no HTML: the dialog shows
  the items as text through Vue's interpolation, so nothing in the file can inject markup.
- **The dialog** `frontend/src/components/layout/ChangelogModal.vue`: title "What changed in
  Yantra"; one block per version, its heading "v0.1.10 — 25-10-2026" (with the `v`, as the sidebar
  shows it, BR1-07), its items as a list; the running version (`__APP_VERSION__`) carries a badge
  "This version"; one button "Close". When the running version has no block (its section was
  forgotten), one line at the top: "No entry for v0.1.11 yet." (BR1-06, § 6 Q4). Read-only, so it
  is a plain Bootstrap modal like `frontend/src/components/documents/PhotoViewer.vue`, not
  `FormModal` (a form dialog with a dirty guard), with PhotoViewer's `open()` / `close()` called by
  `AppSidebar` through a template ref. **Its root is wrapped in `<Teleport to="body">`** (BR1-01):
  the sidebar is `position: fixed; z-index: 100`, a stacking context, so a modal inside it would sit
  under Bootstrap's backdrop (on `body`, z-index 1050) and "Close" could not be clicked. It scrolls
  inside when long (`modal-dialog-scrollable`).
- **The sidebar** `frontend/src/components/layout/AppSidebar.vue:40-42`: when the user holds
  `settings:edit` (`userPermissions`, `frontend/src/stores/auth.js`; Admin's list holds every key), the version
  becomes a button: the same small text with a dotted underline always shown (a cue that it can
  be clicked, BR1-10), `title="See what changed"`, and it opens the dialog. For everyone else it stays plain text, as today.
- **Out of scope:**
  - Phones: the sidebar is hidden below 576 px (`AppSidebar.vue:110-111`) and the version is shown
    nowhere else, so the dialog is a desktop feature. IT Admin's work is at a desk (it is refused
    off the plant network anyway, S013).
  - Showing the notes once after a deploy, and any "seen" record (the old S048).
  - Editing `release.py`, `preflight_stamp.py` or the pre-flight skill in this repo: they come
    from smtw-common. The release uses its existing `POST_BUMP_SCRIPT` hook (§ 1.2); the skill's
    new section and the stamp-carry change are texts for KLA (§ 1.3).
  - A backend route: the text is in the bundle, which every visitor downloads anyway, so the key
    only decides who sees the button, not who can read the text (§ 4).

### 1.1 The file's form

```
# What changed in Yantra

## 0.1.10 — 25-10-2026
- The readings sheet keeps each machine's last reading beside the new one.
- …

## 0.1.9 — 25-10-2026
- …
```

Version without the `v`, an em dash or a hyphen between version and date (the parser takes either),
the date in DD-MM-YYYY (CLAUDE-COMMON § Conventions). Items in scope B words: what the user can
now do or see, not code or step numbers ("Engineers can close a ticket from the list", not
"S018: ticket close route").

### 1.2 Who writes each release's section (U2)

KLA, 26-10-2026 (U2): the pre-flight writes the notes from the commits since the last release; a
release started from PyCharm without them has Claude write them then; if that is too much trouble,
the release gets an empty section. The design below does the Claude path, with the empty section
as its fallback.

- **The notes file** `scratch/release-notes.md` (gitignored, so it does not make the tree unclean
  for `release.py` step 1). First line `<!-- commit <full sha of HEAD> -->`, then `- ` items only,
  no heading: the version number is chosen only at the release (patch, minor or major).
- **The pre-flight writes it** (skill section, § 1.3; written in smtw-common by the
  orchestrator, 26-10-2026, KLA's go-ahead): while the tests run in the background, it
  reads the commit subjects and bodies since the last release tag (`git describe --tags --abbrev=0
  --match "v[0-9]*"`, then `git log <tag>..HEAD`, release commits skipped), writes 3–8 items by the
  rules in `tooling/changelog/notes-rules.md`, and shows them in its report: "Edit
  scratch/release-notes.md if you want; the release uses it for this commit."
- **The rules file** `tooling/changelog/notes-rules.md` (new): one prompt, used by both paths. It
  says: items in the users' words (scope B: what IT Admin, Admin or the plant users can now do or
  see), no step numbers, file names or code; merge commits about one feature into one item; leave
  out tooling, tests and docs-only commits; 3–8 items; output only the `- ` lines; nothing at all
  when no commit changes the app.
- **The release writes the section** through `release.py`'s existing hook `POST_BUMP_SCRIPT`
  (`tooling/common/release.py:15-16`, `:177-184`: run after the bump, before the release commit;
  it must `git add` what it changes; a non-zero exit aborts the release). New script
  `tooling/changelog/release_changelog.py` (standard library only: the hook runs under
  `release.py`'s interpreter):
  1. reads the new version from `VERSION` and today's date in IST;
  2. **the items**, first source that works:
     a. `scratch/release-notes.md`, when its first line names HEAD's full sha (the release commit
        is not made yet, so HEAD is the commit the pre-flight saw). A file for another commit is
        ignored, with the line "Release notes: scratch/release-notes.md is for commit <short>,
        not HEAD; not used.";
     b. **Claude now**: when `shutil.which("claude")` finds the CLI, it runs `claude -p --model
        sonnet --tools "" --no-session-persistence "<the rules file's text>"` with the commit
        list on stdin, a timeout of `CLAUDE_TIMEOUT_S = 180`, and keeps only the output lines
        that start with `- ` (checked 26-10-2026: `claude -p --model haiku --tools ""` with two
        commit subjects on stdin printed two `- ` lines, exit 0). No tools, so it needs no
        permission and can change nothing;
     c. **none**: an empty section. The script prints why ("Release notes: Claude CLI not found",
        "… Claude timed out after 180 s", "… Claude gave no items").
  3. inserts `## <version> — <DD-MM-YYYY>` and the items after the file's `# ` title line (at the
     top when there is none), and runs `git add CHANGELOG.md`;
  4. prints one line naming the source ("Release notes for v0.1.11: from pre-flight (5 items)").
  It exits 0 in every case but one: `CHANGELOG.md` cannot be read or written (then the release
  aborts before its commit, as for any failed hook). Claude being absent, slow or wrong never
  stops a release.
- **The pure core** in the same file, unit-tested: `insert_section(text, version, date, items)`,
  `notes_for_head(file_text, head_sha)` (items, or `None` for another commit), and
  `clean_items(output)` (only `- ` lines, stripped).
- **An empty section in the dialog**: the block shows its heading and the line "No notes were
  written for this version."
- **The run configs**: the three `.idea/runConfigurations/Release__*.xml` gain
  `<env name="POST_BUMP_SCRIPT" value="tooling/changelog/release_changelog.py" />`.

### 1.3 The texts for smtw-common (for KLA, in the impl report)

Both files are synced from smtw-common; the coder changes neither here.
- **The pre-flight skill** (done: KLA, 26-10-2026, "update has to happen in smtw-common. you can do
  directly"; the orchestrator wrote it in `../smtw-common`, uncommitted, for KLA to commit, push
  and sync), a new optional section: "Release notes (when the `## Pre-flight`
  settings name *Release notes*)": the file and the rules file from that setting, the commit
  range, the sha line, run while the tests run, shown in the report. Without the setting the
  skill does nothing new, so other repos are unaffected.
- **`preflight_stamp.carry_text`** (`tooling/common/preflight_stamp.py:160`) carries the stamp
  only when the release commit changes exactly `VERSION`. With `CHANGELOG.md` in the release
  commit it stops carrying, so a retry after a failed build or deploy would test again (the first
  release run still skips its tests: step 2 checks the stamp on HEAD before the commit). The text:
  also allow the files named in a new environment variable `STAMP_CARRY_FILES` (Yantra:
  `CHANGELOG.md`), with its test, under `## Texts for smtw-common` in the impl report. Until
  KLA applies it, the retry case re-tests: accepted.

Yantra's own setting, in `.claude/CLAUDE.md` § Pre-flight (the coder adds it): `- **Release
notes**: scratch/release-notes.md, by the rules in tooling/changelog/notes-rules.md`.

## 2. Standards and practice

ISO 9001:2015 § 7.5.3 (control of documented information, to verify): each release's changes are
recorded in one controlled place, and the record is available where it is needed (the people who
look after the app read it in the app). ISO 55001 § 7.5 (information for asset management) is not
named: the changelog is about the software, not about the plant's assets (BR1-09). No maintenance
standard applies.

## 3. Where

| File | Change |
|---|---|
| `CHANGELOG.md` (new, repo root) | The file (§ 1.1), with the sections of § 6 Q2 |
| `frontend/vite.config.js` | Read `../CHANGELOG.md` (required, no fallback), `define` `__APP_CHANGELOG__` |
| `tooling/build/Dockerfile.frontend` | `COPY CHANGELOG.md /build/CHANGELOG.md` beside the `VERSION` line |
| `frontend/src/utils/changelog.js` (new) | `parseChangelog(text)` |
| `frontend/src/components/layout/ChangelogModal.vue` (new) | The dialog |
| `frontend/src/components/layout/AppSidebar.vue` | The version becomes a button for `settings:edit` holders |
| `frontend/tests/changelog.test.js` (new) | Parser tests |
| `frontend/e2e/changelog.spec.js` (new) | Browser tests (§ 5) |
| `tooling/changelog/release_changelog.py` (new) | The release hook (§ 1.2) |
| `tooling/changelog/notes-rules.md` (new) | The one prompt for both paths (§ 1.2) |
| `tooling/tests/test_release_changelog.py` (new) | Tests of the hook (§ 5) |
| `.idea/runConfigurations/Release__patch_.xml`, `…minor_.xml`, `…major_.xml` | `POST_BUMP_SCRIPT` |

**The release worktrees** get the file through git (`tooling/release-tests.bat` and
`tooling/build/build.bat` check out HEAD and the tag), so nothing else changes.

### Docs (housekeeping, by the coder)

- `.claude/CLAUDE.md`: the § Pre-flight setting *Release notes* (§ 1.3); one line in § Yantra
  Specifics *Release*: the hook writes the version's section into `CHANGELOG.md` in the release
  commit (from the pre-flight's notes, else Claude, else empty). No row in § Docs to keep current:
  steps do not touch the file.
- `.claude/CLAUDE.md` § SMTW-Review, *Browser tests*: `changelog` → S048 in the spec-to-step map
  (BR1-08).
- `docs/Plan.MD`: none due unless it lists the admin screens (the coder checks).

## 4. Design decisions

1. **Reuse `settings:edit`** to show the button. It is held by IT Admin only
   (`backend/config_rbac.py:152`), and Admin passes every key, which is exactly "IT-Admin and
   Admin". The frontend checks a permission key, never a role name (CLAUDE-COMMON § RBAC Pattern:
   the sidebar filters by permission). Rejected: a new key `changelog:read` (an RBAC change and a
   `test_rbac.py` row for a button whose text is public in the bundle anyway); a role check on
   `userRoles` (breaks the pattern).
2. **The text is built in at build time** (`define`, like `__APP_VERSION__`), not fetched. It
   always matches the running build, works offline from the server's point of view, and needs no
   route. Rejected: a `?raw` import of `../CHANGELOG.md` (the dev server's `fs.allow`,
   `vite.config.js:34`, deliberately keeps files outside `frontend/` off it); a backend route
   `/api/changelog` (a route for public text).
3. **The file lives at the repo root**, where people look for a changelog, and the Dockerfile
   copies it as it copies `VERSION`. Rejected: `frontend/CHANGELOG.md` (no Dockerfile change, but a
   project-wide record hidden in the frontend folder).
4. **Our own small parser, text only.** Rejected: a markdown library (a new dependency, and HTML
   rendering of a file anyone with commit access edits).

## 5. Tests and acceptance

- **Unit (vitest)** `frontend/tests/changelog.test.js`: two versions with items → two entries in
  file order, version and date split; an em dash and a hyphen both work; lines that are not a
  heading or a bullet are skipped; an item before any heading is skipped; empty text → `[]`; a
  heading with no items → an entry with `items: []`; text with `<b>` stays text (the parser does not
  strip or interpret it); a heading `## Next version` (no dash) → version "Next version", date "";
  `## v0.1.3 — 16-10-2026` → version "0.1.3"; an indented continuation line joins its item (BR1-04).
- **Browser** `frontend/e2e/changelog.spec.js`, `desktop-chromium` (the sidebar is hidden on
  phones, so these are `@device` tests by the tag rule: they run only on a project other than
  `phone-chromium`):
  - each test starts with `test.skip(testInfo.project.name !== "desktop-chromium", "the sidebar
    is hidden on phones")`, because at Normal and Full every test also runs on `phone-chromium`
    (BR1-03; precedent `frontend/e2e/notifications.spec.js:113`);
  - as IT Admin, the version in the sidebar is a button; clicking it opens "What changed in
    Yantra", the running version's block shows "This version", "Close" is in view
    (`toBeInViewport`) and closes it. Not `expectDialogFits`: it requires a submit and a "Cancel"
    button (`frontend/e2e/support/dialogs.js:30-41`); the Close-only check follows
    `frontend/e2e/readings.spec.js:46-52` (BR1-02);
  - as Admin, the same button opens the same dialog (BR1-11);
  - as a manager (no `settings:edit`), the version is plain text: no button.
- **Tooling (pytest)** `tooling/tests/test_release_changelog.py`, core only plus one shell test:
  `insert_section` after the title, with no title, into an empty file, with no items (heading
  only); `notes_for_head` with the matching sha, another sha (`None`), no sha line (`None`);
  `clean_items` keeps only `- ` lines (a preamble line and a blank line dropped, empty output →
  `[]`); the shell with `claude` not found and no notes file writes an empty section and exits 0
  (`shutil.which` patched; the file in a temp folder, no git). No test calls the real Claude CLI.
- **The dialog**: the empty-section line is covered by a vitest case of the parser (`items: []`)
  and one browser assertion only if the back-filled file has an empty section; else none.
- `frontend/e2e/screens.spec.js`: unchanged (no new route).
- `npx vite build` in `frontend/` passes.
- Full unit suites green; a targeted browser run (the new spec plus `screens.spec.js`) and the
  whole suite at Normal once at the end.
- **No real-device check:** a browser can judge all of it.

## 6. Open questions and assumptions

1. **Answered (U1):** who sees it (IT Admin and Admin), where (the sidebar's version number), how
   (one file bundled with the frontend).
2. **Answered (KLA, 26-10-2026: "backfill - one single entry enough"):** one section,
   `## 0.1.10 — 25-10-2026`, with up to eight plain items on what Yantra does as of v0.1.10, drafted
   from the commits up to tag `v0.1.10` by the rules file; KLA reads it at gate B.
3. **Answered (U2):** the pre-flight writes the notes; a release without them has Claude write
   them; failing that, an empty section (§ 1.2). Steps do not touch the file.
4. **Answered (approved as recommended):** **A forgotten section** (BR1-06): the dialog's top line "No entry for v0.1.11
   yet." when the running version has no block, so IT Admin notices. Alternative: show nothing
   extra.

## 7. Amendments

### A1 — The pre-flight skill writes the notes, on both paths (26-10-2026) — Approved (KLA, 26-10-2026)

**Why:** KLA, at gate B: "anyways, it is claude that is going to write the release notes. the
pre-flight skill must contain proper instructions to generate proper release notes. be terse,
etc... if release py invokes claude code, it must invoke this skill". This reverses U2's choice
of a bare prompt plus a repo rules file.

**What changes:**
- **The writing rules live in the pre-flight skill** (smtw-common, § 3a), not in
  `tooling/changelog/notes-rules.md`, which is deleted. The skill's rules: terse; one line per
  item, 15 words or fewer; what the user can now do or see, in the users' words; present tense, no
  "now", no exclamation; one item per feature, related commits merged; nothing a commit does not
  state; leave out tooling, tests, docs, refactors and release commits; no step numbers, file
  names, code names or commit ids; 1 to 8 items, most useful first; nothing at all when no commit
  changes the app.
- **The repo's setting names the readers:** `.claude/CLAUDE.md` § Pre-flight, *Release notes*:
  `scratch/release-notes.md; readers: IT Admin, Admin and maintenance engineers of Yantra, a plant
  maintenance app` (KLA at approval: "in future, it will include engineers too"; the notes are
  written for engineers from now on; who may open the dialog stays `settings:edit`, since opening
  it to engineers is a permission change for a later step).
- **The skill knows how it was started** (KLA at approval: "the skill must be aware of the
  execution source - pycharm or in a normal claude code session. in run config invokation, it
  must not ask for further details etc.. must work with what it has"). Skill § 0, by argument:
  none = a person, the whole run; `notes` = a person, notes only (§ 3a: from git, writes the notes
  file, shows the items, no tests or stamp); `notes unattended` = the release hook (§ 3b): no
  question, no options, no waiting; only the commits on the input and the settings; prints only
  the `- ` lines; on any problem prints nothing, so the release writes an empty section. The
  writing rules are § 3c, shared by both paths.
- **The hook runs the skill:** `claude -p "/pre-flight notes unattended" --model sonnet --tools Read
  --strict-mcp-config --no-session-persistence`, from the repo root, with the commit list on
  standard input. Read only, to read the settings: no shell and no writes, so nothing can prompt
  or change a file in an unattended release. `--strict-mcp-config` with no config turns off the
  connectors (checked 26-10-2026: `--tools ""` alone left Gmail and Microsoft 365 available).
  The timeout becomes `CLAUDE_TIMEOUT_S = 300`, because the skill and the settings are read
  first. `clean_items` keeps only the `- ` lines, as now.
- **Checked 26-10-2026:** `claude -p --model haiku --tools "" "/project-scratch"` loaded that
  skill and followed it (exit 0). From Git Bash the slash argument needs
  `MSYS_NO_PATHCONV=1`; the hook calls it from Python, which passes it unchanged.
- **Who does what:** the orchestrator writes the skill text in `../smtw-common` (KLA's go-ahead
  of 26-10-2026 for that file). The coder changes the hook, its tests, the setting line and the
  CLAUDE.md *Release* text, and deletes the rules file. Until KLA commits, pushes and syncs
  smtw-common, Yantra's copy of the skill has no notes mode: a release then gets Claude's
  best effort from the plain skill, or an empty section.

**Out of scope:** the step-number filter (KLA chose CR1-01 (a)); any change to `release.py`.

**Tests:** the hook's tests assert the new command line (skill call `/pre-flight notes unattended`, `--tools Read`,
`--strict-mcp-config`, the commit list on stdin, the 300 s timeout); the notes-file and fallback
paths stay. No test calls the real CLI. The tooling suite runs; no browser run (no screen
changes).

## Review log

### U1 — 26-10-2026 (before drafting)

KLA, on the queued S048: "let's do it this way: we just have one CHANGELOG file, we bundle it with
front end. IT-Admin and Admin can click on the version number in the sidebar to view it."

### U2 — 26-10-2026 (at gate A, answers Q3)

KLA: "pre-flight skill must look at the commits since release write this to some file. If instead,
release is done directly from pycharm without the required file, we have two options - just skip
the content and mark release with empty / have the release script invoke Claude and run the skill
and generate. Let's try the later, down grade to former if it's too much trouble." Folded into
§ 1.2 and § 1.3. Changed from the request: the release calls Claude with the commit list and the
rules file, not the whole skill (no tools, no permission prompts, nothing it can change); the same
rules file drives the pre-flight's draft.

### Gate A — 26-10-2026

KLA: "S048 approved"; Q2 one single back-fill entry; Q4 as recommended; the pre-flight skill
changed directly in smtw-common. Track stays light. Coder: Sonnet.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 26-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor: the modal inside the fixed sidebar sits under the backdrop | Accepted: `<Teleport to="body">`, PhotoViewer-style `open()` / `close()` through a template ref (§ 1) |
| BR1-02 minor: `expectDialogFits` needs submit and Cancel | Accepted: Close `toBeInViewport`, as `readings.spec.js:46-52`; the shared helper unchanged (§ 5) |
| BR1-03 minor: the tests also run on `phone-chromium` | Accepted: `test.skip` unless `desktop-chromium` (§ 5) |
| BR1-04 minor: parser rules for re-wrapped bullets, other headings, `v` | Accepted: one rule set and a test per case (§ 1, § 5) |
| BR1-05 minor: the fallback holds only locally | Accepted: the file is required, as `VERSION`; the manual build check is dropped (§ 1, § 5) |
| BR1-06 minor: a running version with no block | Accepted as a question for KLA (§ 6 Q4); recommended: one line "No entry for v… yet." |
| BR1-07…BR1-11 nits | Accepted, all: headings with the `v`; the spec-to-step map row; ISO 55001 not named, with the reason; a permanent dotted underline; an Admin test |

### Code review r1 — `4-code-review-r1.md` (Opus), 26-10-2026

0 blocker, 0 major, 4 minor, 5 nits; all sent to fix round 1. CR1-01: the rules file changes from
"3–8 items" (§ 1.2) to "1 to 8 items", with a rule that every item must be stated by the commits
(a fix round departure, accepted by the orchestrator: a release with one change must not be padded);
the hook prints the items it wrote. The rest of CR1-01 (a filter that drops lines naming a step
number, or a release stop) goes to KLA at gate B.

### Gate B — 26-10-2026

KLA on CR1-01: "a" — no filter and no release stop. KLA reads the items the release prints (or
`CHANGELOG.md`) and fixes a bad line in a later commit. Code review r2: 0 blocker, 0 major, 1 nit
(CR2-01), sent to fix round 2.

### Gate A for A1 — 26-10-2026

KLA: "approve A1", with two changes folded into A1: the readers include maintenance engineers;
the skill knows whether a person or the release hook started it, and unattended never asks. The
orchestrator wrote the skill text in `../smtw-common` (§ 0, § 1 setting, § 3a–3c; uncommitted).
Coder: Sonnet.

### Code review r3 (A1) — `4-code-review-r3.md` (Opus), 26-10-2026

0 blocker, 0 major, 1 minor, 2 nits; all fixed by the orchestrator (fix round 3). CR3-01: skill
§ 0 and § 3b now say the commits follow `notes unattended` in the arguments (`claude -p` joins the
prompt and stdin), in the hook's form `commit <short sha>`, subject, body, blank line. CR3-02:
skill § 1's stop line says "Unattended: print nothing". CR3-03: the hook's docstring re-wrapped.
Tooling suite 185 passed (`s048f3`).
