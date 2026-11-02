```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: impl-report
Author: Coder (Sonnet)
Date: 02-11-2026
```

# S103 — Implementation report

The step is built and green: the Help button, the three gallery apps in `help/`, the tour as repo tooling
and the page checks. Unit suites, the browser suite and the tour all pass. Nothing waits on KLA except the
publish (`repos.toml` entry, commit, collector) and the device checks.

## 1. What was built

- **The Help button.** A question-mark link in the top bar before the bell, on every screen, for everyone
  logged in (no permission key). `aria-label` and `title` are "Help", 44 px high, it opens
  `HELP_URL` (`https://gallery.mspv.app/yantra/home/`, `frontend/src/help.js`) in a new tab with
  `rel="noopener noreferrer"`.
- **`help/`, Yantra's gallery folder**, three apps, each with a `gallery.toml` (`contract = 1`, title,
  description, `[access]` client `vel-yantra-master`, roles `maintenance_team` and `it_admin`):
  - `home/`: the Help home (draft made plain: no claude meta tag, no Google font link). Cards: User guide,
    Entering equipment (links `../guide/#mt1`), Documents and photos (links `../documents/`).
  - `guide/`: the 72 slides in one `index.html` with 67 lossless WebP shots (3.4 MB). Two views: the
    reading page (default below 900 px and with JavaScript off) and the slide show (900 px and wider).
  - `documents/`: the Documents and photos reading page, seven sections, 12 shots in `shots/`.
  - `README.md` and `guide-outline.md` sit directly in `help/` and are not published.
- **The tour as repo tooling.** `tooling/help-shots.bat` runs `tooling/help/tour.py`, which in one
  `try/finally` takes the e2e lock, makes the lane 9 database and the sample files, starts the e2e backend and
  Vite on lane 9, loads the seed and `setup_tour.py`'s data, runs Playwright with
  `frontend/help-tour/tour.config.js`, writes lossless WebP copies, then stops both servers and releases the
  lock. Everything it writes is under `scratch/help-shots/`.
- **The Documents and photos shots**: `frontend/help-tour/documents.tour.js` (third project `documents`)
  uploads through the real dialogs and takes 12 shots (`doc-01` to `doc-12`).
- **`tooling/tests/test_help_pages.py`**: the page checks of § 5.

## 2. How it works

**Guide page.** Each slide is a `<section id="…" class="slide light|alt|dark row|stack phone|desk">`. The
inline styles of the deck became about 60 rules in the page's `<style>`. The base rules are the reading page.
`body.show` (set by the script) switches them to a 1920 × 1080 slide that the script scales with
`transform: scale(k)` to fit the window. Images keep `width` and `height` attributes: the reading page sets
`height: auto; max-width: 100%`, the slide show lets the attributes stand. The two crops of slide `x12` use one
file; in the reading page the second crop is hidden (`.crop.dup`). The script (about 100 lines, inline) only
switches views and slides:
- The view is in the address (`?view=page` or `?view=slides`; default by width), the slide in the hash
  (`#x20`). Next and back set the hash, so the browser's Back works; `hashchange` shows the slide.
- Keys: arrows, Space (Shift+Space back), Page Up / Page Down, Home, End. A swipe of 50 px or more. Two 44 px
  buttons and *12 / 72*. *Contents* is a `<details>` menu (works without JavaScript) with one entry per
  section, plus a link back to the Help home.
- No library, no CDN, no storage. System fonts (the deck's Rubik and Public Sans came from Google Fonts,
  which the contract does not list).

**Tour.** As § 1. `setup_tour.py` imports `e2e_backend` and `run_lanes` from `tooling/e2e` (the lock,
`main_scratch`, `lane_database`, `create_databases`, `check_target`); its three SQL touch-ups are in
`touch_ups()` with the reason in the docstring, after `check_target`. `tour.py` runs in the backend's uv
environment (`uv run --project backend`) because it needs Pillow for the WebP copies and the sample files.

## 3. Files touched

Counts: 87 files in `help/` (3 manifests, 3 pages, 79 shots, README, outline), 5 in `frontend/help-tour/`
(`tour.config.js`, `shot.js`, `phone.tour.js`, `desktop.tour.js`, `documents.tour.js`), 3 in `tooling/help/`,
plus the list below.

- `frontend/src/help.js` (new): `HELP_URL`.
- `frontend/src/components/layout/AppTopbar.vue`: the Help link; phone CSS (below).
- `frontend/e2e/floor.spec.js`: the two S103 tests.
- `help/README.md`, `help/guide-outline.md`, `help/home/*`, `help/guide/*`, `help/documents/*` (new).
- `frontend/help-tour/*` (new): `tour.config.js`, `shot.js`, `phone.tour.js`, `desktop.tour.js`
  (moved from `scratch/tour/specs/`, imports and paths changed), `documents.tour.js`.
- `tooling/help/tour.py`, `setup_tour.py`, `make_photo.py`; `tooling/help-shots.bat` (new).
- `tooling/tests/test_help_pages.py` (new).
- `.claude/CLAUDE.md`: *Help (S103)* bullet and the `help/` row of *Docs to keep current*.
- `docs/steps/device-checks.md` (rows 69, 70), `docs/steps/INDEX.md` and the brief's `Status` (In code review).

## 4. Decisions taken

- **The top bar's phone layout changed (forced by the brief's own @device test).** With Help added, the page
  title shrank to 20 px at 360 px (the name took the room, and the title box was only as wide as its text, so
  the test measured the text). Fixes in `AppTopbar.vue`: `.topbar-center` is `flex: 1 1 auto; text-align:
  center` (the title now owns the free space), and below 576 px Help and the bell are 36 px wide (still 44 px
  high), the name is at most 4.5 rem, and the Sign out button drops its icon and keeps its word. The title is
  73 px wide at 360 px. On a desktop the title is now centred in the free space, as before to the eye.
- **Fonts.** The guide uses system fonts. The deck's Rubik and Public Sans were loaded from Google Fonts, which
  contract § 5 does not allow; shipping the font files was more than the step asked.
- **No dark mode** on the guide (the brief said only if cheap).
- **`<aside>` notes**: shown as a note under each slide in the reading page, hidden in the slide show.
- **Slide text kept as the draft**, with one change: the closing slide's last line named `scratch/tour/`; it now
  names `tooling/help-shots.bat` and `help/README.md`. The cover still says the PM screens are "from steps
  S095–S102, not yet committed"; KLA may want that line changed when the PM steps are committed (the README's
  retake list covers it).
- **The home's range "slides 54–61"** (draft) was wrong: section 9 is slides 57–66 (`mt1` is slide 57). Fixed.
- **Documents shots are named `doc-NN-…`**: a first run used numbers 70–81, which collide with the guide's PM
  shots. The second tour run made the `doc-*` files, and the 12 files in `help/documents/shots/` are from it.
- **WebP method 4** in `tour.py` (method 6 took about 15 minutes for 80 shots on this machine, and the size
  difference is small). The guide's 67 files are from the 02-11-2026 PNGs (as the brief says), made with method 6.
- **Contents menu**: ten entries (the section's first slide) and a link "← Yantra Help". Below 560 px the bar's
  own "Yantra Help" link is hidden so the bar stays on one row; the menu keeps the link.
- **A tool the brief did not name**: `scratch/help-check/check.mjs` (a throw-away Playwright script, not in the
  repo) checked all 72 slides for overflow at 1366 × 768, the keys, buttons, Contents, the toggle and the
  360 px reading page.

## 5. Not done, deferred or assumed

- **The gallery publish.** `repos.toml` entry, commit and collector are KLA's (brief § 6 Q1). I did not run the
  collector's `--dry-run`: it reads only committed files and needs the `repos.toml` entry, which is another
  repo. As a stand-in I ran the collector's own `parse_manifest` (read-only, `python -I`) on the three
  manifests: no errors. Python may have written `.pyc` files under the Gallery repo's `collector/__pycache__`.
- **The slide show was checked in headless Chromium** (screenshots at 1366 × 768 and 360 px, a script for the
  keys), not by eye on real devices; that is the device checks' job.
- The guide's `Updated`, `·` and name oddities that the tour noticed stay out of scope (brief).
- The version on the home and the cover (v0.1.15 + PM, 02-11-2026) is written by hand, as the brief assumed.
- `docs/Plan.MD` § 6 already holds the Help line (written before this step), so I made no change there.
- Not run: `npx playwright test` on `phone-webkit` (the round changes no `@device` test of an existing spec
  and adds no `page.route`; the new `@device` test runs on desktop and the iPhone in the release).

## Docs updated

- `.claude/CLAUDE.md`: § Yantra Specifics, bullet *Help (S103)*; § Docs to keep current, the `help/` row.
- `docs/steps/device-checks.md`: rows 69 and 70.
- `help/README.md` and `help/guide-outline.md` (new; they are the Help source's own docs).
- `docs/Plan.MD`: none, because § 6 already names the Help button.
- `docs/schema/*`, `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `backend/example_secrets_app.py`,
  `docs/Keycloak.md`: none, because the step has no migration, no maintenance rule, no secret and no role
  change.

## Manual checks

- [auto] The top bar has a Help link to the gallery, opening in a new tab — `frontend/e2e/floor.spec.js::S103: the top bar has a Help link to the gallery, opening in a new tab` (operator on `/me`, IT admin on `/settings`).
- [auto] Help, the bell and Sign out fit the top bar at 360 px — `frontend/e2e/floor.spec.js::S103: Help, the bell and Sign out fit the top bar at 360 px` (`@device`; passed on `phone-chromium` alone and in the whole suite).
- [auto] Pictures, alts, ids, links, relative URLs, manifests and file names of the three apps — `tooling/tests/test_help_pages.py` (all tests in the file).
- [auto] The tour makes the 67 guide shots and the 12 documents shots, frees ports 5019 and 5189, and releases the lock — run twice with `tooling/help-shots.bat`, 19 tests passed each time (`scratch/help-shots-run.log`, `scratch/help-shots-run2.log`).
- [auto] S064's top-bar test and the bell tests still pass — `frontend/e2e/floor.spec.js`, `frontend/e2e/notifications.spec.js`, `frontend/e2e/screens.spec.js` (targeted run).
- [ ] **Important.** The two views, by eye: open `help/guide/index.html` from disk at about 1366 × 768 (slides, arrow keys, buttons, *Contents*) and at 360 px (the reading page, no sideways scroll); `#mt1` opens section 9 in both; `help/documents/index.html` at 360 px and 1366 px. (I ran this as a script and read the screenshots; it needs your eye.)
- [ ] **Important.** On a real device, after the release and the first publish: tap **Help** on an Android phone and on the iPhone; the guide's pictures load (device-checks row 69).
- A realm user without `maintenance_team` or `it_admin` gets the gallery's "not found" (device-checks row 70).

## Test results

- Unit suites, `YANTRA_TEST_RUN=s103c1 tooling/run-tests.bat`: backend 5310 passed (`scratch/backend-tests-s103c1.log`), frontend 458 passed (`scratch/frontend-tests-s103c1.log`), tooling 258 passed (`scratch/tooling-tests-s103c1.log`). The line-width test is in the tooling suite and covers `tooling/help/*.py`.
- Build: `npx vite build` in `frontend/` passed (the usual chunk-size warning).
- Browser, targeted (`floor`, `notifications`, `screens`): 39 passed, 5 skipped (`scratch/s103-e2e-targeted.out`).
- Browser, whole suite at Normal, once: 423 passed, 15 skipped, 0 failed, 392 s (`scratch/s103-e2e-whole.out`).

## Fix rounds

### Round 1

- **CR1-01** (phone top bar): left as built, for KLA at gate B. `AppTopbar.vue` is not touched.
- **CR1-02** Fixed. The guide's cover and closing slide now say "The screens show Yantra v0.1.15 with
  preventive maintenance, as of 02-11-2026" (as the Help home's footer). The step numbers, "adoption" and
  the tooling line are gone from the slides; `help/README.md` and `guide-outline.md` hold them.
- **CR1-03** Fixed. `help/documents/index.html`: the *who* lines of sections 2, 3, 4 and 5 and the rules row
  now say "Engineer, manager and IT admin" (`equipment:edit` is engineer and IT admin, and manager inherits
  engineer, `config_rbac.py:75`). Restore and erase stay "Manager, IT admin" (`equipment:purge_documents`).
- **CR1-04** Fixed. `tryDo` in `frontend/help-tour/shot.js` still goes on and takes the shot, and now also
  calls `expect.soft(false, "tour action failed: <label>")`, so the test, the tour and `tooling/help-shots.bat`
  end non-zero and name the label. Red run: not made (it needs a broken selector in the tour); the tour
  re-run passed 19 tests with 0 "TRY FAILED" lines (`scratch/help-shots-run3.log`), so no shot changed and no
  WebP file was copied.
- **CR1-05** Fixed. `setup_tour.sql` uses `run_lanes.COMPOSE` and `run_lanes.DEV_ROOT_PASSWORD`.
- **CR1-06** Fixed with a comment in `touch_ups` (the check can refuse only if `LANE_DATABASE` loses `_e2e`).
- **CR1-07** Fixed by one comment in the `tour.py` docstring naming the four files that write lane 9 and its
  ports. Not made to read `E2E_LANE` (the tour is lane 9 by design).
- **CR1-08** Fixed. The `tour.py` docstring lists `scratch/e2e-vite-lane9/`.
- **CR1-09** Fixed in `help/README.md`: open each `index.html` itself; copy the `webp` files that do not
  start with `doc-` into `help/guide/shots/`. Also a line that a failed tour action fails the run.
- **CR1-10** Fixed. `tooling/tests/test_help_pages.py` checks names of at most 100 characters, paths of at
  most 120, and no two paths that differ only in capitals. Red run: not made (the pages are valid; the
  checks only guard later changes).

Tests: tooling suite 258 passed alone; the full run is in the line below. Browser: no spec or screen
changed, so none was run. The tour was run once (above).

Docs updated (round): `help/README.md`. Others: none, because no maintenance rule, secret or role changed.

#### Feedback (round 1)

- hindrance: the Bash heredoc with a Python replace of a string holding a backslash-n failed twice (the
  match did not hold); the Edit tool worked (2 retries, 3 min).

### Round 2

- **CR1-01** Fixed, by KLA's answer of 02-11-2026 (option a). In `AppTopbar.vue`, below 576 px the brand
  word "Yantra" (`.topbar-left`) is hidden; the top bar has no separate logo, so nothing else goes. Help and
  the bell are 44 x 44 px again, and Sign out has its icon and its word again (S064 UX-02). Round 1's phone
  rules for the icon width, the Sign out icon and the Sign out padding are removed. I kept two small rules:
  the name cap of 4.5 rem with a 0.25 rem margin, and the smaller phone font sizes that were there before
  the step. The page title is at least 60 px wide at 360 px (the test passes on the logic device, desktop
  and the iPhone); I did not measure how much room is left above 60 px, so a long name still shortens
  first. The red run of the strengthened test was not made: it would need the round 1 CSS put back.
  `floor.spec.js` (S103 fit test) now also asserts each control is at least 44 px wide and that the Sign out
  icon is visible.
- **CR2-01** Fixed. The guide's cover says the date once ("Screens taken on a test copy with sample plant
  data. The screens show Yantra v0.1.15 with preventive maintenance, as of 02-11-2026."). `help/README.md`
  step 3 now names the Help home, the guide's cover and its last slide.
- **CR2-02** Fixed. `test_help_pages.py` compares every folder prefix of each path, as the collector does, and
  names the clashing spellings. Red run: not made (the pages are valid; the check only guards later changes).

Docs updated (round): `help/README.md`. Others: none, because no maintenance rule, secret or role changed.

Screenshots: the guide's phone shots show the brand word "Yantra" in the top bar and no Help link; on a phone
the app now hides the word and shows Help. I did not retake them.
Tests: tooling suite 258 passed alone. Browser, targeted (`floor`, `notifications`, `screens`): 39 passed,
5 skipped (`scratch/s103f2-e2e.out`). S103 tests on `phone-webkit`: 2 passed (`scratch/s103f2-webkit.out`).
`npx vite build` passed. Full unit run: see the summary lines in `scratch/s103f2-all.out`.

#### Feedback (round 2)

- none

## Feedback

- hindrance: the brief text has "tooling\run-collector.bat" and "tooling\run-collector.bat --dry-run" turned into a line break plus "un-collector.bat" (the `\r` of the path was read as a carriage return) in § 1 and § 6 Q1 of `1-brief.md`; I took the real name from the Gallery repo (1 check).
- waste: lossless WebP at `method=6` took about 15 minutes for 67 shots (and again 10 minutes beside the first tour run's own conversion); `method=4` is enough (`tooling/help/tour.py`, two background runs overlapped).
- hindrance: a Bash command with two heredocs holding CSS and JS failed with "unexpected EOF"; I used the Write tool instead (1 retry, 2 min).
- rule: the brief's section 9 range "slides 54–61" came from the draft and was wrong (`mt1` is slide 57); a brief that cites slide numbers could name ids (`mt1`) instead.
- idea: the Gallery's collector has no read-only "check this folder" mode that works before a commit and before the `repos.toml` entry; a `--path` option would let a coder run the real checks.
