```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 02-11-2026
```

# S103 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The three gallery apps follow the contract,
the unit suites and the build are green, and the code matches the brief. Five `minor` findings
remain: the top bar's phone layout weakens two earlier approved rules (for KLA at gate B), the
guide shows developer text that is wrong once the step is committed, the documents page leaves out
the managers, the tour hides failed actions, and `setup_tour.py` copies two `run_lanes.py` values.

## Tests run

- Unit suites, `YANTRA_TEST_RUN=s103cr1 tooling/run-tests.bat`: **PASSED**. Backend 5310 passed,
  frontend 458 passed, tooling 258 passed (`scratch/s103cr1-unit.out`). The line-width test ran
  first and passed, so `tooling/help/*.py` keep to 120 characters.
- Build check, `npx vite build` (to `scratch/s103cr1-build`): built in 5.6 s, the usual chunk-size
  warning only.
- Browser tests: I ran none. The coder's runs name the right specs: targeted `floor.spec.js`,
  `notifications.spec.js` and `screens.spec.js` (39 passed, 5 skipped), and the whole suite at
  Normal once (423 passed, 15 skipped, 0 failed). None of my findings needs a re-run.
- Not in this step's diff: `tooling/run-tests.bat` and most of the `.claude/CLAUDE.md` hunks. The
  snapshot diff shows them because the step's base is S102's snapshot, but they come from the
  feedback triage of 02-11-2026 (the line-width check first). Only the *Help (S103)* bullet and the
  `help/` row of *Docs to keep current* are S103's.

## Gallery contract (no collector refusal found)

I checked every rule of contract § 1–§ 5 (`C:\Users\KLA\PycharmProjects\gallery\docs\SMTW-Utils-Gallery.md`,
constants in `collector/rules.py`):

- `help/` holds exactly three folders, `home`, `guide`, `documents`, each a valid slug with a
  `gallery.toml`. `README.md` and `guide-outline.md` sit directly in `help/`, so they are skipped,
  not refused.
- The three manifests have `contract = 1` (an integer), a title of 1–80 characters, a one-line
  description under 300, and an `[access]` table with only `client` and `roles`.
  `vel-yantra-master` matches `CLIENT_PATTERN`. `maintenance_team` and `it_admin` match
  `ROLE_PATTERN`, and both are client roles on that client (`docs/Keycloak.md` § 3.2), as the
  contract requires.
- Every file name matches `SEGMENT_PATTERN`. The extensions are `html` and `webp`, in lower case.
  No path is near 120 characters or 8 levels, there are no case collisions, and no name is a
  Windows device name. The largest file is 155 KB. The apps are 9 KB, 3.5 MB and 333 KB.
  Nothing in `help/` is ignored by git.
- § 5: every `src` and `href` is relative. There is no `/`-rooted URL, no CDN, no web font link,
  no service worker and no browser storage. The guide's view lives in `?view=` and the slide in
  the hash.

## Findings

### CR1-01 (minor) — The phone top bar breaks two approved rules of S021 and S064

`frontend/src/components/layout/AppTopbar.vue:137-152` (and the comment at `:99`).

- **Problem.** The coder lists this departure: below 576 px, Help and the bell are 36 px wide, the
  name is capped at 4.5 rem (72 px), and Sign out loses its icon. This is shared layout on every
  screen, and it changes behaviour that earlier briefs approved:
  - S064 UX-02 asks for "a **Sign out** button with icon and word";
  - the bell's 44 × 44 tap target ("a gloved thumb", the comment at `:99`) is now 36 × 44.

  The S064 test still passes, but it cannot see the change. `toHaveText(me.name)` reads the DOM
  text, not the text left after the ellipsis.
- **Failure scenario.** A supervisor whose Team name is "Saravanan Kumar" picks up a shared phone.
  The top bar shows "Saravan…", so the name is less useful for spotting who is still logged in,
  which is the reason S064 put it there. A gloved thumb has 8 px less width on the bell and on Help.
- **Suggested fix.** KLA decides at gate B. Both options keep the brief's 60 px title test green:
  1. **Recommended.** Below 576 px, hide the "Yantra" brand on the left instead. It takes about
     45 px, and the browser tab and the home-screen icon already name the app. Keep Help and the
     bell at 44 × 44, keep Sign out's icon, and drop the name cap or loosen it. The coder measures
     the title at 360 px (about 100 px expected).
  2. Keep the layout as built. KLA records that he accepts it, and the comment at `:99` changes to
     "44 px high; 36 px wide below sm (S103)".

### CR1-02 (minor) — The guide shows developer text that is wrong once the step is committed

`help/guide/index.html:184`, `help/guide/index.html:1199-1200`.

- **Problem.** The cover says "The PM screens are from steps S095–S102, not yet committed". The
  closing slide says "The PM screens come from steps S095–S102, waiting for adoption" and "run the
  screenshot tour again (tooling/help-shots.bat; help/README.md)". The gallery publishes only
  committed files, so on the first publish the PM steps are committed and both lines are false.
  Step numbers, "adoption" and a tooling path are also words a plant user does not know (scope B).
- **Failure scenario.** An operator opens the guide after the release. The first slide tells them
  that the PM screens they use every day are "not yet committed".
- **Suggested fix.**
  - Cover: end the line at "Screens taken 02-11-2026 on a test copy with sample plant data."
  - Closing slide: delete the step line and the tour line. `help/README.md` § Retake the
    screenshots already holds the tour.
  - Keep the lines that explain what a user sees (`e2e_operator` in history lines, the blocked
    notifications, the empty access log).

### CR1-03 (minor) — The documents page says managers cannot add documents

`help/documents/index.html`, § 7 *The rules* row "Who adds to a machine or a model", and the
*who* lines of sections 2, 3, 4 and 5.

- **Problem.** The page says "Engineer and IT admin. Everyone else can open and download." But
  `equipment:edit` is `("maint_engineer", "it_admin")` and `ROLE_INCLUDES` makes manager ⊇
  engineer (`backend/config_rbac.py:75`), so a manager can also add, rename and remove. The brief
  (§ 1 item 7) left the manager out too, and the coder copied it. The other claims are right:
  restore and erase are manager and IT admin (`equipment:purge_documents`), a contract's documents
  are for managers only, and ticket documents are for `ticket:work` holders.
- **Failure scenario.** A manager reads "Everyone else can open and download". He asks an engineer
  to upload a drawing that he could upload himself.
- **Suggested fix.** "Engineer, manager and IT admin. Everyone else can open and download." Use
  the same three roles in the *who* lines of sections 2–5 ("Engineer, manager, IT admin").

### CR1-04 (minor) — The tour passes when one of its actions fails

`frontend/help-tour/shot.js` (`tryDo`), used 29 times in `desktop.tour.js` and `phone.tour.js`.

- **Problem.** `tryDo` catches the error, logs "TRY FAILED …" and goes on, so the test and the tour
  still pass. A retake runs exactly when a screen has changed, which is when a selector breaks.
  CLAUDE-COMMON § Engineering rules: never silently swallow exceptions. A log line inside a
  passing run of 19 tests is close to silent.
- **Failure scenario.** A later step renames *Assign* to *Assign people*. `tooling/help-shots.bat`
  prints "The tour passed". The shot `28-ticket-assign-dialog-desktop` shows the ticket page with
  no dialog, and it is copied into `help/guide/shots/` and published.
- **Suggested fix.** Keep the "go on and still take the shot" behaviour, but fail the run at the
  end. Two ways:
  - in `tryDo`, use `expect.soft(…)` or push the label to `test.info().annotations`, and fail the
    test after its last shot when any label failed;
  - or make `tour.py` return 1 when Playwright's output holds "TRY FAILED", and print the labels.

### CR1-05 (minor) — `setup_tour.py` copies two values of `run_lanes.py`

`tooling/help/setup_tour.py:64-67` (`sql`).

- **Problem.** `sql()` builds its own `docker compose -f …/docker-compose.dev.yml` command and
  writes `-pdev-root-password` again. `run_lanes.py` already has both, as `COMPOSE` (`:73`) and
  `DEV_ROOT_PASSWORD` (`:74`), and `setup_tour.py` imports `run_lanes`. BR1-04 asked for imports,
  not copies.
- **Failure scenario.** The dev compose file moves, or its root password changes. `run_lanes.py`
  is updated, but the touch-ups fail, or they reach a different container than `create_databases`.
- **Suggested fix.** `subprocess.run([*run_lanes.COMPOSE, "exec", "-T", "mariadb", "mariadb",
  "-uroot", f"-p{run_lanes.DEV_ROOT_PASSWORD}", LANE_DATABASE, "-e", statement], check=True)`.

## Nits

- **CR1-06** (nit) `tooling/help/setup_tour.py:87`: `check_target` gets a dict written on the line
  before, so it can only refuse when `LANE_DATABASE` loses its `_e2e` ending. Say that in a comment,
  or pass the lane's real target (`e2e_backend.E2E_DATABASE`, which also proves that the backend and
  the touch-ups name the same database).
- **CR1-07** (nit) `tooling/help/tour.py`, `setup_tour.py:16,21,27`, `frontend/help-tour/tour.config.js:17`,
  `documents.tour.js:13`: lane 9 and its ports are written in five places (`"9"`, `5019`, `5189`).
  Have `setup_tour.py` read `E2E_LANE` the way `e2e_backend.py` does. Have the JS files take the URL
  from `e2e/support/stack.js`, or add one comment that names all five places.
- **CR1-08** (nit) `tooling/help/tour.py:84`: Vite's cache goes to `scratch/e2e-vite-lane9/`, a path
  that is not in the brief's *Output paths* or in the docstring's list. Add it to the docstring.
- **CR1-09** (nit) `help/README.md:32` and step 2 of § Retake: from disk, the home's
  `../guide/` link opens a folder listing, not the page, so say "open each `index.html` itself".
  Step 2's "copy the `webp/*.webp` files into `help/guide/shots/`" also copies the `doc-*` files
  there. Say "the files not starting `doc-`".
- **CR1-10** (nit) `tooling/tests/test_help_pages.py:73-81`: add the three cheap contract checks the
  file leaves to the collector: the 120-character path, two paths that differ only in capitals, and
  the 100-character name. One invalid app stops every publish, and the collector runs only after a
  commit.

## Manual checks

The impl report's `## Manual checks` carries every important check of the brief: the two
`floor.spec.js` tests and the page checks as `[auto]`, the tour as `[auto]` with its two logged
runs, the two views by eye, and the phone check after the first publish (device-checks row 69) as
unticked boxes. Row 70 (a realm user without the roles) is listed too. Still for the user:

- [ ] **Important.** Open `help/guide/index.html` from disk at about 1366 × 768: the slides, the
  arrow keys, the two buttons and *Contents* work. At 360 px it is the reading page with no
  sideways scroll. `#mt1` opens section 9 in both views. Open `help/documents/index.html` at 360 px
  and at 1366 px.
- [ ] **Important.** On a phone, the top bar at 360 px. If CR1-01 is kept as built, check that the
  36 px Help and bell targets work with a gloved thumb.
- [ ] **Important.** Device-checks row 69, after the release and the first publish.
- Device-checks row 70.

## Checked and found consistent

- **Brief § 1, Help button.** It sits before the bell, with `aria-label` and `title` "Help",
  `target="_blank"` and `rel="noopener noreferrer"`. It has no permission check, so it also shows
  on `NoAccessView` (a person with no Team record, `App.vue:63-67`). `HELP_URL` is fixed in
  `frontend/src/help.js` (D2, D10).
- **Brief § 5 tests.** The link test checks the `href`, the `target` and the `rel` as the operator
  and as IT admin, and never opens the gallery. The fit test is tagged `@device` by the rule (its
  title names fits; its main assertion is geometry). It checks each control at ≥ 44 px high and in
  view, the title at ≥ 60 px and in view, and no sideways scroll.
- **Desktop layout.** `flex: 1 1 auto; text-align: center` on `.topbar-center` keeps the title in
  the middle of the free space, as `justify-content: space-between` did before. `screens.spec.js`
  and `notifications.spec.js` still read `.topbar-center`.
- **The guide's two views.**
  - The reading page is the CSS default. With JavaScript off, `[data-js]` and the pager stay hidden
    and *Contents* is a `<details>`, so it still works.
  - The slide show is `body.show`, and `fit()` scales a 1920 × 1080 slide.
  - Next and back set the hash, so Back works.
  - Keys: arrows, Page Up / Page Down, Space and Shift+Space (not on a focused control), Home and
    End. A swipe of 50 px or more. Escape closes *Contents*.
  - `?view=` is written by `replaceState` with a relative address.
  - The 72 sections have unique ids, and the home's `../guide/#mt1` names one.
  - The section 9 range (slides 57–66) is correct.
- **The documents page's labels** match the `.vue` files: *Add document*, *Add photo*, *Upload*,
  *Download*, *More actions*, *Edit title*, "Remove this document?", "It disappears from every
  machine of this model.", *Yes* / *No*, *Restore*, *Delete for good*, "Delete for good? The file
  cannot be recovered.", "Choose a file", "Enter a title", "What does the photo show?", the
  paperclip's title *Documents*, *From model …*, Settings › *Uploads* "Largest file for documents
  and photos", and the HEIC note.
- **The tour.**
  - `tour.py` takes `run_lanes.one_run_at_a_time` on the main scratch lock, outside the `try`.
  - The `try/finally` stops Vite and the backend (`taskkill /T`) after a failed wait, a failed seed
    or a raised `setup_tour`.
  - It imports `main_scratch`, `lane_database` and `create_databases` (no copy), and it sets
    `E2E_LANE` before `e2e_backend` is imported.
  - Its files go to `scratch/help-shots/` and `scratch/e2e-data/lane9/` (and CR1-08).
  - The touch-ups run only on `vel_yantra_lane9_e2e`, after `check_target`.
- **The tour's files are not picked up by other runs.** Vitest ignores `*.tour.js`, and
  `playwright.config.js` keeps `testDir: "./e2e"`.
- **`test_help_pages.py`** covers § 5: pictures exist, are all used and have an alt; ids are unique;
  `#` links name a section; URLs are relative with no `_blob` and no `claude.ai`; the manifests
  have the D10 and D11 keys and `contract = 1`. It covers `documents/` too.
- **The docs pass.** `.claude/CLAUDE.md` has the *Help (S103)* bullet and the `help/` row (BR1-08).
  `docs/Plan.MD` § 6 has the Help line. `docs/steps/device-checks.md` has rows 69 and 70. There is
  no migration, secret or role change, so no other doc is due.
- **Track.** The step stays light. There is no migration, no RBAC or security code, and no
  locking. The code files number about 12 (BR1-01, KLA kept light).
- **The other departures** are in "Decisions taken" and are fine: system fonts instead of Google
  Fonts (contract § 5 lists no font host), no dark mode on the guide, the corrected range, the
  `doc-NN` names, and WebP method 4.

## Feedback

- hindrance: the step diff from S102's snapshot also shows the 02-11-2026 feedback-triage changes
  (`tooling/run-tests.bat`, eight `.claude/CLAUDE.md` hunks), so I had to find which hunks were
  S103's (`git show c9cd091 --stat`, `git diff HEAD`; 3 extra commands).
- idea: the gallery collector could check one folder in the working tree before a commit and before
  the `repos.toml` entry. A reviewer could then run the real rules instead of re-reading
  `rules.py` by hand (the coder asked for the same; about 10 min here).
