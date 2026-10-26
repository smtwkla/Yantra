```
Step: S048 — What changed: one CHANGELOG, opened from the version number
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 26-10-2026
```

Reviewed against: c7803b1 (the uncommitted changes are step docs only: the S048 and S059 step files, `docs/steps/INDEX.md`, the R01 roadmap row; no code)

# S048 — Brief review, round 1

**Verdict:** no `blocker` or `major` finding. Six `minor` findings and five nits. The light track
holds (every criterion checked below), so this is the step's only brief-review round; the
orchestrator answers the findings in the Review log and the brief goes to KLA.

The six minors are gaps the coder would otherwise fill alone: where the dialog mounts (the sidebar
is a stacking context, BR1-01), a test helper that cannot pass on a Close-only dialog (BR1-02), the
desktop-only skip (BR1-03), the parser's edge cases (BR1-04), a build claim that does not hold for
the image (BR1-05), and one judgement call for KLA (BR1-06).

Facts file used: `scratch/brief-facts-S048.md`. Two of its "no such file" lines are false alarms
from partial paths in the brief: `frontend/src/components/documents/PhotoViewer.vue` and
`frontend/src/stores/auth.js` both exist.

## Minor findings

### BR1-01 — minor — Where the dialog mounts: not inside the sidebar

**Problem.** The brief puts the button in `AppSidebar.vue` and says it "opens the dialog", but not
where `ChangelogModal` is rendered. The natural place, inside the sidebar's template, breaks the
dialog: `.sidebar` is `position: fixed; z-index: 100` (`AppSidebar.vue:60-68`), so it is a
stacking context. A Bootstrap modal rendered inside it keeps its `z-index: 1055` only within that
context, while Bootstrap appends the backdrop (`z-index: 1050`) to `document.body`. The grey
backdrop then covers the dialog, and the Close button cannot be clicked (Playwright's click would
time out on the backdrop intercepting the pointer).

**Why it matters.** The coder finds it only when the browser test fails, and then picks a fix
alone (a z-index bump on the sidebar is the tempting wrong one).

**Options.**
1. **Recommended:** `ChangelogModal.vue` wraps its root `.modal` in `<Teleport to="body">`.
   `AppSidebar` owns it through a template ref and calls `open()` / `close()` as `DocumentsCards`
   does with `PhotoViewer` (`defineExpose({ open, close })`). One line, no new state. Vue's
   template ref works through a Teleport.
2. Mount `ChangelogModal` in `App.vue` beside `UpdateToast`, and let the sidebar's click set a
   ref in a small store (as `appVersion.js` does for the toast). More moving parts for one dialog.
3. Render it in the sidebar and raise the sidebar's z-index above 1050. Rejected: it would put
   the sidebar over every other dialog's backdrop.

### BR1-02 — minor — `expectDialogFits` cannot pass on a Close-only dialog

**Problem.** § 5 says the test checks "the dialog fits (`expectDialogFits`)". The helper
(`frontend/e2e/support/dialogs.js:30-41`) locates `.modal-footer button[type=submit]` and a
button named "Cancel" and asserts both are on screen. The changelog dialog has one button,
"Close", so the helper fails with "Save off screen: null".

**Why it matters.** The test as written cannot pass; the coder would either change the shared
helper (a `e2e/support/` change re-runs the whole browser suite, settings *Shared code*) or
invent a check.

**Options.**
1. **Recommended:** use the existing precedent for a close-only dialog, `readings.spec.js:46-52`
   (`openHistory`): `openDialog(page)`, then
   `expect(dialog.locator(".modal-footer").getByRole("button", { name: "Close" })).toBeInViewport()`.
   Add `dialogBox.height <= viewport.height` if the brief wants the "no taller than the screen"
   half too; on desktop (768 px high) a long list makes this the check that matters, with
   `modal-dialog-scrollable` on the dialog (§ 1 says "scrolls inside when long"; name the class).
2. Teach `expectDialogFits` a Close-only dialog. Rejected for this step: a shared-helper change
   and a whole-suite run for one dialog.

### BR1-03 — minor — The desktop-only tests need a skip on the phone projects

**Problem.** § 5 tags the two tests `@device` because they run only on `desktop-chromium`. The
tag is right, but a tag does not confine a test: at the Normal level every test runs on
`phone-chromium` (CLAUDE.md *Browser tests*), where the sidebar is `display: none` below 576 px,
so "the version in the sidebar is a button" fails there.

**Why it matters.** The whole-suite run at the end of coding goes red on the Android phone, and
the coder decides the fix alone.

**Options.**
1. **Recommended:** the brief states the first line of each test:
   `test.skip(testInfo.project.name !== "desktop-chromium", "the sidebar is hidden on phones")`,
   the precedent `notifications.spec.js:18, 113` (`const DESKTOP = "desktop-chromium"`).
2. A file-level `test.skip` on the project. Same effect; the per-test form is the repo's pattern.

### BR1-04 — minor — Parser rules for lines the form does not cover

**Problem.** § 1 says the parser "reads only `## <version> — <DD-MM-YYYY>` headings and `- `
bullets; any other line is skipped". Three cases are left to the coder:
- **A wrapped bullet.** KLA edits step files in PyCharm, which re-wraps long lines
  (`docs/steps/README.md` § IDE reformatting). A bullet's second line (indented, no `- `) is
  "any other line" and is dropped: the user reads half a sentence.
- **A `##` heading not in the form.** Q3's alternative uses `## Next version`. Is it skipped (and
  its bullets then join the previous version's block, or are dropped?) or shown?
- **A heading with a version but no date**, or `v0.1.10` with the `v` the file is told not to
  have.

**Why it matters.** Each is a rule the coder sets alone, and the unit tests in § 5 do not name
them, so the behaviour is whatever the first implementation did.

**Options.**
1. **Recommended, one simple rule set:** every `## ` line starts a block; its text is split at the
   first ` — ` or ` - ` into `version` (a leading `v` stripped) and `date` (empty when there is
   none); a `- ` line adds an item to the current block; a non-empty line that starts with
   whitespace joins the previous item with a space; everything else (the `#` title, blank lines,
   paragraphs, `###`) is skipped; an item before the first `##` is skipped. `## Next version`
   then shows as a block headed "Next version", which is also what Q3's alternative wants. Add a
   unit test for each case to § 5.
2. Keep the strict form and treat a line outside it as an error the parser reports (the dialog
   shows "The changelog has a line it cannot read: …"). More code for a file only KLA edits.

### BR1-05 — minor — "A missing file must not break the build" holds only for a local `vite build`

**Problem.** § 1 and § 5 say a missing `CHANGELOG.md` must not break the build, give
`vite.config.js` a fallback to "", and add a manual check (rename the file, build, restore). But
`tooling/build/Dockerfile.frontend` gets `COPY CHANGELOG.md /build/CHANGELOG.md`, and Docker's
`COPY` of a missing file fails the image build whatever the config does. `VERSION` has no
fallback either (`vite.config.js:14` throws when it is missing). The fallback protects only a
developer who deleted the file, and costs a code path plus a manual test.

**Why it matters.** The brief states a guarantee the step does not give, and the coder spends a
manual run on it.

**Options.**
1. **Recommended:** drop the fallback and the rename-and-restore check. The file is committed, the
   release worktrees and the build context have it (the brief says so in § 3), and a missing file
   fails loudly like a missing `VERSION`. Keep "No changes are recorded yet." for a parse that
   yields no block (Q2's "start empty" alternative, and the test `empty text → []`).
2. Keep the fallback and change the claim to "a missing file fails the image build; a local
   `vite build` still runs" — then the manual check is still not worth a line.

### BR1-06 — minor — The running version has no block in the file (KLA's call)

**Problem.** § 1 gives the running version's block a badge "This version". It says nothing for
the case where the file has no block for the running version: a release whose section was
forgotten (Q3 recommends writing it before the pre-flight, but nothing enforces it). IT Admin
then opens the dialog after a deploy, sees the newest block is 0.1.10 while the sidebar says
v0.1.11, and may read it as "nothing changed".

**Why it matters.** It is the one moment the dialog exists for, and the state is likely at least
once. It is a judgement call, so it goes to KLA rather than the coder.

**Options.**
1. **Recommended:** one line at the top of the body when `__APP_VERSION__` matches no block:
   "No entry for v0.1.11 yet." (scope B: what the user sees, no blame). One `v-if`, one browser
   assertion is not needed (a unit test of a tiny `hasEntry(versions, running)` helper, or none).
2. Show nothing and rely on Q3's process. Cheaper; the user is left to notice the mismatch.

## Nits

- **BR1-07** (nit) § 1, dialog headings: show "v0.1.10 — 25-10-2026" with the `v`, as the
  sidebar shows "v0.1.10" (one term for one thing); the file keeps the bare number.
- **BR1-08** (nit) § 3 Docs: add `changelog` → S048 to the spec-to-step map in `.claude/CLAUDE.md`
  § SMTW-Review (*Browser tests*), where every spec file is listed; the coder adds it with the
  other CLAUDE.md lines.
- **BR1-09** (nit) § 2: S001, S003, S006 and S008 cited ISO 55001 § 7.5–7.6 (documented
  information of the asset management system) for the same idea; name it beside ISO 9001 § 7.5.3,
  or say in a few words why 9001 alone (the changelog is about the software, not the assets —
  which is a fair reason).
- **BR1-10** (nit) § 1, use at the desk: the button is 0.7 rem muted text whose only cue is an
  underline on hover; IT Admin may never find it. A permanent cue costs nothing: a dotted
  underline, or a small `fa-circle-info` after the number. KLA chose "click the version number",
  so this is a suggestion, not a change of the decision.
- **BR1-11** (nit) § 5: the brief says Admin sees the button but tests only IT Admin. `admin` is
  a test identity (`e2e/support/people.js:8`, `TOKEN_ROLE.admin`; `apiAs("admin")` is already
  used), so the first test can run for `["it_admin", "admin"]`, or the brief says IT Admin stands
  for both because Admin passes every key.

## Light track

Checked against `docs/steps/README.md` § Tracks; every criterion holds:
- no migration, no change to data: none;
- no auth, RBAC or security-sensitive code: the frontend hides a button by an existing key, as
  `SettingsView.vue:54` and `NotificationsSettings.vue:25` already do; `config_rbac.py` is
  untouched; the text is public in the bundle and the brief says so;
- no transactions, locking, concurrency: none;
- an existing pattern: the `define` of `__APP_VERSION__`, a `PhotoViewer`-style modal, a pure
  util with vitest tests; no dependency; no endpoint;
- about 10 files: 8 in § 3 plus `.claude/CLAUDE.md`, and `docs/Plan.MD` if due.

This is the step's only brief-review round.

## Manual checks

Right as split: every check in § 5 is one a browser can judge, and the brief lists no device
check. The one manual run (the build without the file) goes with BR1-05.

## Checked and found consistent

- **`settings:edit`** is held by `it_admin` only (`backend/config_rbac.py:152`), and admin gets
  every key (`backend/access_core.py:51-52`, `compute_permissions`), so "IT Admin and Admin" is
  exactly the holders. `userPermissions` comes from `/api/auth/me` (`stores/auth.js:26, 93`), and
  the frontend already checks it with `includes("settings:edit")`; CLAUDE-COMMON § RBAC Pattern
  (filter by permission, never by role name) is followed. No `SITE_SCOPED` question: the key is
  global.
- **The `define` and the build.** `vite.config.js:14` reads `../VERSION` relative to the
  process's folder and `:27-29` defines `__APP_VERSION__`; `../CHANGELOG.md` resolves the same
  way everywhere it is built or served: vitest (`run-frontend-tests.bat` runs in `frontend/`),
  the e2e Vite servers (Playwright's `webServer` runs in the config's folder, `frontend/`), the
  image (`WORKDIR /build/frontend`, so `../CHANGELOG.md` is the `COPY` target
  `/build/CHANGELOG.md`). `.dockerignore` excludes no root file. `build.bat` builds from the tag's
  worktree with the worktree root as context (`:113, :126`); `release-tests.bat` tests a worktree
  of HEAD; both have the committed file, so § 3's "nothing else changes" holds.
- **vitest sees the define:** one `vite.config.js` carries both the `test:` block and `define`,
  and vitest applies `define` (the existing `appVersion.js` guards `typeof __APP_VERSION__`, the
  pattern the modal can copy).
- **The sidebar** is hidden below 576 px (`AppSidebar.vue:110-111`), and the version is shown
  nowhere else (`__APP_VERSION__` is used only in `AppSidebar.vue` and `stores/appVersion.js`);
  `desktop-chromium` is 1366 px wide, so the tests belong there.
- **The dialog pattern:** `PhotoViewer.vue` is a plain Bootstrap modal with
  `Modal.getOrCreateInstance`, `open()` / `close()` through `defineExpose`, no form and no dirty
  guard — the right model for a read-only dialog. `FormModal` has a `closeOnly` footer, but it
  wraps a `<form>` with the discard guard; not using it is right.
- **The `@device` tag:** the rule in CLAUDE.md *Browser tests* ("runs only on … a project other
  than `phone-chromium`") covers these tests; the brief reads it correctly (the skip itself is
  BR1-03).
- **The e2e identities** the tests need exist: `it_admin` (token role), `manager` (a seed person
  without `settings:edit`), `admin` (`people.js:8`).
- **Scope B wording:** "What changed in Yantra", "This version", "Close", "See what changed",
  "No changes are recorded yet." are short, plain and start with the right word.
- **Standards:** ISO 9001:2015 § 7.5.3 is the right clause (control of documented information:
  available where needed, protected, with changes controlled), and the brief explains it in
  plain words.
- **Docs:** `.claude/CLAUDE.md` § Docs to keep current gets a `CHANGELOG.md` row and § Yantra
  Specifics *Release* a line — the right places; `docs/Plan.MD` names no admin screen that would
  change (its Settings bullet at `:813` lists settings, not the sidebar). `INDEX.md` has the new
  row and the old queued S048 row is gone.
- **`screens.spec.js` unchanged** is right: no new route.

## Feedback

- hindrance: the facts file reported `components/documents/PhotoViewer.vue` and `stores/auth.js`
  as "no such file" because the brief wrote them with partial paths; both exist, so I checked
  them by hand (2 lookups; `brief_facts.py` could match a partial path by suffix).
- waste: a chained read-only Bash command stopped at a `grep` with no match (exit 1) and lost the
  commands after it, one re-run (1 min; my own chaining, not the tooling).
