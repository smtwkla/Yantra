```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: brief
Author: Orchestrator (Opus)
Date: 02-11-2026
Track: light
Baseline: refs/steps/S102 (c9cd091 + S095–S102, uncommitted)
Status: Committed 82d38ac (02-11-2026, by KLA; important checks pending: the two views by eye, and device-checks row 69 after the release; row 70 plain); was: Gate B 02-11-2026 (code review r1: 5 minor, 5 nits; r2: 2 nits; all fixed in fix rounds 1–2; CR1-01 by KLA (a); verify review r3: no finding; device checks rows 69–70); was: In code review; was approved 02-11-2026 by KLA (1a HTML, 2: the documents page, 3a Yantra's users only, 4a light; review r1: 0 blocker, 0 major, 10 minor, 4 nits, all accepted; revised the same day on KLA's word: plain web pages on gallery.mspv.app, no claude.ai artifacts)
```

# S103 — Help: a link in the app to the user guide in the gallery

KLA, 02-11-2026: Yantra gets a Help section. Help is **app documentation**, for the plant's users,
kept apart from `docs/` (developer documentation). It is **delivered through SMTW's gallery,
<https://gallery.mspv.app>**; the app only links to it (KLA: "Help section must be delivered to the
user via gallery, app only links"). The first Help content exists as a draft: the user guide deck
(72 slides of real screens, made 02-11-2026 as a claude.ai Slides artifact, private) with 8
masters onboarding slides for the team that enters the equipment.

KLA's answers (02-11-2026): (1a) two gallery pages, a Help home that links to the guide and later
pages; (2b) the link address is fixed in the code, no setting; (3a) the Help source and the
screenshot tool live in the repo, and move to smtw-common once they are mature; (4a) light track.

KLA, 02-11-2026, after review r1: "the deck should be presented as a html page. Either generated
from MD or as html itself. There should be no dependence on Claude artifacts … publish both the
user guide (slide show) and doc as web pages on gallery". So every Help page is a plain web page
of our own (HTML, CSS and a little JavaScript, no library), complete in the repo with its
pictures, published by the gallery as its apps are (KLA: "We now have a gallery.mspv.app"). The
gallery (the Gallery repo; contract `docs/SMTW-Utils-Gallery.md` there, synced from smtw-common)
serves static apps behind the same Keycloak realm as Yantra (`Office.smtw.in`), from the LAN and
the internet; its collector publishes the **committed** files of each repo's gallery folder. The
claude.ai drafts are not used after the step.

## 1. What will be built

- **A Help button in the top bar**, beside the bell, on every screen, phone and desktop
  (`AppTopbar.vue`): a question-mark icon, 44 px tap target, `aria-label` and `title` "Help". It
  opens the Help home in a new tab (`target="_blank"`, `rel="noopener noreferrer"`). Everyone who
  is logged in sees it, also a person with no Team record; no permission key.
- **The Help home**, a plain web page: a short line on what Help is and one card per guide:
  today the **User guide**, with a line per section (getting around, equipment, tickets,
  improvements, lessons, readings, PM, contracts, masters and onboarding, settings), and the app
  version its screens show; the *Entering equipment* card links into the guide's section 9
  (`../guide/#mt1`, relative, as the contract's § 5 asks); the **Documents and photos** card
  links to `../documents/`. Later guides are new cards. Its
  address is fixed by the contract before any publish, `https://gallery.mspv.app/yantra/home/`
  (D10), so the coder needs nothing from a publish (BR1-02).
- **The user guide as one web page, two views** (D7, D8): the 72 slides of the Slides deck,
  moved into one file `help/guide/index.html`, each slide a `<section id="…">` in order, with
  its screenshot from `help/guide/shots/` beside it (a relative path, not a gallery upload).
  - **Slide show** (the default on a screen at least 900 px wide): one slide at a time, scaled to
    fit the window; next and back by the arrow keys, Space, Page Up / Page Down, a swipe, or two
    44 px buttons; the slide number (*12 / 72*); a *Contents* menu by section; the address ends
    in the slide's id (`#x20`), so a link opens that slide and the browser's Back works.
  - **Reading page** (the default under 900 px, so on every phone; a *Read as a page* /
    *Show as slides* button switches on any screen): the same sections one under the other, the
    text above its picture, readable at 360 px with no sideways scroll; `#x20` scrolls to it.
  - The inline styles of the deck's slides become a few classes in the page's `<style>` (a
    light and a dark slide, a text column, a phone shot, a desktop shot, a grid), so both views
    come from one copy of the text. The page's script (about 100 lines, inline) only switches
    views and slides; with JavaScript off, the reading page shows.
- **Documents and photos, a reading page** (KLA, gate A: "To equipment and models, users can
  upload and attach documents. That's the doc"): `help/documents/index.html`, a third gallery
  app, written like the guide's reading view (the same classes, copied into its `<style>`; no
  slide show), with its own screenshots in `help/documents/shots/`. Its sections, each with the
  steps in the app's own button names, who may do it, and a shot on the phone or the desktop:
  1. **Where each goes**: the maker's documents (manual, drawings, spare-parts list) on the
     **model**, so every machine of that model shows them under *From model …*; this machine's
     own (test report, invoice, the nameplate photo) on the **machine** (from the guide's `mt7`).
  2. **Add a document to a machine**: the machine's page › **Documents** › **Add document**,
     choose the PDF, a title, **Upload** (`DocumentUploadModal.vue`); the new row.
  3. **Add a photo**: **Photos** › **Add photo**; on a phone the camera opens; **Upload**.
  4. **The model's documents**: Masters › **Models** › the model › its **Documents** card; then
     the machine's page showing the group *From model …*.
  5. **Open, download, rename, remove**: the title opens the PDF in a new tab; **Download**;
     *More actions* › **Edit title** / **Remove**, and the confirmation "Remove this document?".
  6. **Removed documents**: Settings › **Removed documents**: restore, or erase for good
     (`equipment:purge_documents`: manager or IT admin; `RemovedDocuments.vue`).
  7. **The rules**: PDF only for documents; JPEG, PNG or WebP for photos; the size limit
     (`upload_max_mb`, 20 MB unless Settings say otherwise); who may add (`equipment:edit`:
     engineer or IT admin, on machines and models); and one line each on the other places with
     documents or photos (tickets, countermeasures, one-point lessons, contracts, where only
     managers see a contract's).
  The coder checks each label against the `.vue` files before writing it.
- **The Help source in the repo**, a new top folder `help/` (not under `docs/`), which is
  Yantra's gallery folder (D10): each subfolder is one gallery app with its `gallery.toml`; a file
  directly in `help/` is not published (contract § 1):
  - `help/README.md`: what Help is, who reads it, what each file is, how to see a page (open the
    file in a browser), how to publish a change (commit it, then KLA runs the Gallery repo's
    `tooling
un-collector.bat`; nothing in the app or the release does), how to retake the
    screenshots (`tooling/help-shots.bat`, then the table in `guide-outline.md`);
  - `help/home/`: `gallery.toml` (title "Yantra Help", the `[access]` of D11) and `index.html`;
  - `help/guide/`: `gallery.toml` (title "Yantra user guide", the same `[access]`),
    `index.html` and `shots/*.webp` (67 pictures, lossless WebP, 3.5 MB in all; D5; the
    contract allows `webp`, 25 MB a file, 50 MB an app);
  - `help/documents/`: `gallery.toml` (title "Documents and photos", the same `[access]`),
    `index.html`, `shots/*.webp`;
  - `help/guide-outline.md`: the screenshot list (the documents page's shots in a second table) with who, where and the how-to lines, plus a
    table *slide id → shot file → alt text*, so a retake can match each slide to its picture
    (BR1-07). Its paths name `tooling/help-shots.bat` and `scratch/help-shots/`, not
    `scratch/tour/` (BR1-11). It sits beside the apps, not in `guide/`, so it is not published.
- **The screenshot tour as repo tooling**, moved from `scratch/tour/` (where it ran on 02-11-2026)
  and tidied: one driver, `tooling/help/tour.py`, does in one `try/finally` (BR1-03): take the
  machine's e2e lock; create the lane database and its grant; start the e2e backend and Vite on
  lane 9 (database `vel_yantra_lane9_e2e`, backend 5019, Vite 5189); load the e2e seed; add the
  standard plant data (`setup_tour.py`); run `npx playwright test -c help-tour/tour.config.js`
  from `frontend/` with `E2E_LANE=9` in its environment; then stop both servers and release the
  lock, also on a failure. `serve.py`'s stop-file protocol goes. The lock, the main scratch
  folder, the lane database name and the database creation are imported from
  `tooling/e2e/run_lanes.py` (`one_run_at_a_time`, `main_scratch`, `lane_database`,
  `create_databases`), not copied (BR1-04). One command: `tooling/help-shots.bat`.
- **The standard data** is made through the API as each role, except three touch-ups no API
  allows, kept in one named function `setup_tour.touch_ups()` with this reason in its docstring
  (BR1-06): the seed people's names lose their " (role)" ending, so a screen shows "Kannan", not
  "Kannan (technician) (Technician)"; the seed's scrapped compressor gets a plant name; the seed's
  overdue ticket gets a plant description. They are SQL on the lane database only, after
  `e2e_backend.check_target`.

**Out of scope:** Help pages rendered inside the app; a per-screen link ("help for this page");
a setting for the address (KLA 2b); publishing from a script or the release (KLA runs the
collector); the Gallery repo's `repos.toml` entry (KLA adds it, § 6 Q1); a Markdown source
and its generator (D7); serving Help from the app's own server (possible later: the pages need
nothing but a static folder); fixing the two app oddities the tour noticed (an empty *Updated* shows "·"; timeline lines keep
the name a person had when written) — queued in the index instead. (The third, "Kannan
(technician) (Technician)", came from the seed's names, BR1-06.)

## 2. Standards and practice

- **ISO 9001 § 7.5 (documented information):** the guide is controlled: its source is versioned
  with the code it describes, and the Help home names the app version the screens show.
- **TPM, education and training pillar:** the guide is the training material; the masters slides
  are the onboarding standard for the team entering equipment (ISO 14224's taxonomy in plain words).

## 3. Where

| File | Change |
|---|---|
| `frontend/src/help.js` (new) | `HELP_URL = "https://gallery.mspv.app/yantra/home/"` (D10), with a comment naming `help/` as the source |
| `frontend/src/components/layout/AppTopbar.vue` | the Help link before the bell; the doc comment names it |
| `frontend/e2e/floor.spec.js` | S103 tests (§ 5) beside S064's top-bar test |
| `help/README.md`, `help/home/index.html` (new) | the Help source and the Help home, § 1 |
| `help/home/gallery.toml`, `help/guide/gallery.toml`, `help/guide/index.html`, `help/guide/shots/*.webp`, `help/guide-outline.md` (new) | the user guide page (from the deck's `slides/*.html` and `deck.json` in the orchestrator's scratchpad, which the orchestrator copies to `scratch/help-draft/` for the coder) and its 67 pictures (the 02-11-2026 PNGs, converted) |
| `help/documents/gallery.toml`, `help/documents/index.html`, `help/documents/shots/*.webp` (new) | the Documents and photos page, § 1 |
| `frontend/help-tour/documents.tour.js` (new) | the documents page's shots (about 10, phone and desktop): it uploads through the dialogs with `setInputFiles`, a small PDF and the lesson photo made by `make_photo.py` (Pillow can write the PDF too); the third project of `tour.config.js` |
| `tooling/tests/test_help_pages.py` (new) | the page checks of § 5 |
| `frontend/help-tour/` (new): `tour.config.js`, `phone.tour.js`, `desktop.tour.js`, `shot.js` | the tour's browser part (D3; from `scratch/tour/specs/`). After the move `shot.js` imports `../e2e/support/…`; `tour.config.js` has `testDir: "."`, `testMatch: "*.tour.js"`, its two projects keep their own match (`/phone/`, `/desktop/`) (BR1-13) |
| `tooling/help/` (new): `tour.py`, `setup_tour.py`, `make_photo.py` | the driver, the standard data, the lesson's photo. `setup_tour.py`'s nine lines over 120 characters are wrapped (the line-width test, BR1-12) |
| `tooling/help-shots.bat` (new) | the one command: `uv run … tooling/help/tour.py` |
| `.claude/CLAUDE.md` | § Yantra Specifics: a *Help (S103)* bullet (the gallery, `help/`, `HELP_URL`, the tour, lane 9 and its output folder); § Docs to keep current: the row "`help/` · a step changes a screen the guide shows: nothing in the step; the guide is retaken and republished before a release that changes screens, on KLA's word (`tooling/help-shots.bat`, `help/README.md`)" (BR1-08) |

**Output paths** (D4, BR1-05): every file the tour writes is under `scratch/help-shots/`: the
shots (PNG, and the lossless WebP copies made with Pillow, which the backend already uses; the
person retaking copies the WebP files into `help/guide/shots/`), the ids (`data.json`), the logs (`backend.log`, `vite.log`), Playwright's `outputDir`
(`../../scratch/help-shots/results` from `tour.config.js`); and the lane's files folder
`scratch/e2e-data/lane9/` (made by `e2e_backend.py`). Nothing under `frontend/help-tour/`.

*Docs (housekeeping, by the coder):* `docs/Plan.MD` § 6 Screens: one line on the Help button.

## 4. Design decisions

- **D1. A top-bar button, not a nav item.** The bottom bar on a phone already holds five items for
  a technician; a sixth would crowd it, and a nav item with no permission would also become the
  landing page of a user with no other item (`navigation.landingNavItem`). The top bar is on every
  screen at every width. Rejected: a nav item in `navItems`.
- **D2. A fixed address in `frontend/src/help.js`** (KLA 2b). The Help home is the one fixed
  address: a new guide or a republished deck changes only the Help home's content, never its
  address, so the app needs no change. Rejected: a setting (KLA).
- **D3. The tour's browser part lives in `frontend/help-tour/`, its Python part in
  `tooling/help/`.** Specs and their config must resolve `@playwright/test` from
  `frontend/node_modules`; under `frontend/` that works with no junction (the 02-11-2026 run
  needed a `node_modules` junction in `scratch/tour/`). `frontend/playwright.config.js`
  (`testDir: "./e2e"`) does not pick the folder up. Vitest would: `vite.config.js:27` excludes
  only `e2e/**`, and its default include matches any `*.spec.js`; so the tour's files are named
  `*.tour.js` (`phone.tour.js`, `desktop.tour.js`) and `tour.config.js` sets
  `testMatch: "*.tour.js"`, with no change to `vite.config.js`.
  Rejected: everything in `tooling/help/` with a junction made at each run.
- **D4. Lane 9 and the e2e lock.** The tour is a browser run: it holds the lock from
  `run_lanes.one_run_at_a_time` (the main working folder's `scratch/e2e-run.lock`, also from a
  worktree), so it never runs beside the browser suite; lane 9 is above the default 6 lanes and
  under `MAX_LANES`. It writes only its lane database and the paths in § 3. `create_databases(9)`
  also grants lanes 1–8, which is harmless.
- **D5. The pictures are committed, as lossless WebP** (KLA: no dependence on artifacts). The
  collector publishes only committed files, so the pictures must be in git; a page also opens
  from disk. 67 shots: PNG 9.8 MB, WebP at
  quality 85 4.9 MB, lossless WebP 3.5 MB (measured with Pillow on the 02-11-2026 shots), so
  lossless is both smaller and exact. A retake adds about 3.5 MB to the history, once per
  release at most. Rejected: PNG (three times the size); claude.ai uploads (the old D5).
- **D7. The page is written as HTML, not generated from Markdown** (KLA 1: "Which is better for
  LLMs to read, update? If markdown is an advantage we do it"). Markdown is shorter, but each
  slide needs layout Markdown lacks (two columns, a shot beside the text, a dark slide), so it
  would hold raw HTML anyway; and the class-based HTML of § 1, about 15 plain lines a slide, reads
  and edits as easily for Claude. A generator would add code, a library and a build step for
  little gain. The slides are already HTML
  with two-column layouts that Markdown cannot express without raw HTML, and Python has no
  Markdown library in the standard library, so a generator would add a dependency or a home-made
  parser. One HTML file is the source and the published page: no build step. Rejected:
  Markdown + a generator script; keeping the Slides artifact type (KLA).
- **D8. One page with two views, not two pages.** The slide show suits a laptop or a projector
  in training; a phone in portrait would scale a 1920 × 1080 slide to a fifth (34 px text to
  6 px), so it gets the reading page. One copy of the text keeps the two from drifting.
  Rejected: a separate slide page and doc page (the same text twice); the slide show on phones.
- **D9. Plain static pages under the gallery contract.** Relative URLs only, no service worker,
  no CDN, no browser storage (the view choice lives in the address, not `localStorage`), so the
  pages (all three) follow contract § 5 and depend on nothing of the gallery but its serving. The app links
  only to the Help home (D2); the home links to the guide.
- **D10. `help/` is Yantra's gallery folder, repo key `yantra`, three apps `home`, `guide` and `documents`.**
  The contract publishes `<folder>/<slug>/` at `/<key>/<slug>/`, and `repos.toml` may name a
  folder other than `gallery` (contract § 6), so the Help source keeps the name KLA chose and
  needs no second folder. The addresses are then `https://gallery.mspv.app/yantra/home/` and
  `…/yantra/guide/`, known before the first publish. The README and the outline sit directly
  in `help/` and are not published (contract § 1). Rejected: a `gallery/` folder beside
  `help/` (two folders for one thing); one app holding both pages (the home would then live at
  `…/help/index.html` with the guide in a subfolder, fine too, but one app a guide gives each its
  own card in the gallery's list).
- **D11. Access: Yantra's users only** (KLA 3a). The three manifests carry
  `[access] client = "vel-yantra-master"`, `roles = ["maintenance_team", "it_admin"]`: the
  roles that may log in to Yantra (`docs/Keycloak.md` § 3.2); gallery admins
  (`mspv-apps-admin`, Yantra's admin) open every app anyway. The guide shows the plant's
  screens and the masters set-up, so it stays with the people who use them. Rejected: no
  `[access]` (every user of the realm, office staff included).
- **D12. Documents and photos is its own page, not slides** (KLA 2). It is a how-to the
  onboarding team keeps open beside the app while entering machines, so it reads top to bottom,
  on a phone too. It sits beside the guide, which keeps its slide `mt7` and links to it.
- **D6. Text the tour cannot show** (test logins such as `e2e_operator` in history lines, blocked
  notifications, no worker) stays as the deck's closing slide says. Apart from the three
  touch-ups of § 1, the tour does not patch the app or the seed.

## 5. Tests and acceptance

**Automated** (`frontend/e2e/floor.spec.js`):
- "S103: the top bar has a Help link to the gallery, opening in a new tab", untagged: as the
  operator on `/me` and as IT admin on `/settings`, the visible top bar has a link named "Help" with
  `href` = `HELP_URL`, `target="_blank"` and `rel` containing `noopener`. The test never opens the
  gallery (it is outside the test stack).
- "S103: Help, the bell and Sign out fit the top bar at 360 px", `@device`: at 360 × 780 the Help
  link, the bell and Sign out are fully in view, each at least 44 px high; the page title
  (`.topbar-center`) is in view and at least 60 px wide (it may end in "…", BR1-09); the page has
  no sideways scroll (`expectNoSidewaysScroll`).
- `tooling/tests/test_help_pages.py` (tooling suite, a few ms): every `<img src>` in
  `help/guide/index.html` names a file in `help/guide/shots/`, and every shot file is used;
  every `<img>` has a non-empty `alt`; the `<section id>`s are unique; every `#id` link in the
  guide and the Help home's `../guide/#…` links name a section; every `src` and `href` in both
  pages is relative (no `/`-rooted URL, no `/_blob/`, no `claude.ai`, no other site; D9); each `gallery.toml` has exactly the keys of D10 and D11 and `contract = 1`.
- The checks of `test_help_pages.py` cover `help/documents/` the same way (its `shots/`, its
  ids, its links).
- The two views (the coder checks by eye, no browser test: the page is not part of the app):
  the guide opened from disk at 1366 × 768 shows slides with working keys, buttons and
  *Contents*; at 360 px it shows the reading page with no sideways scroll; `#mt1` opens section
  9 in both; the documents page at 360 px and 1366 px. **Important.**
- Existing: S064's top-bar test (`floor.spec.js`) and the notifications bell tests
  (`notifications.spec.js`) still pass; `screens.spec.js` unchanged.
- Runs: targeted `tooling/run-e2e-tests.bat e2e/floor.spec.js e2e/notifications.spec.js
  e2e/screens.spec.js`, then the whole suite at Normal once; unit suites `tooling/run-tests.bat`
  (the line-width test covers `tooling/help/*.py`).

**The tour** (the coder runs it once): `tooling/help-shots.bat` makes the 67 guide screenshots and the documents page's shots into
`scratch/help-shots/` with no failure, leaves `git status` as it was apart from the step's own
files, frees ports 5019 and 5189, and releases the lock. **Important.**

**On a real device** (IT Admin; the operator test login; production on the TEST machine, after the
release and the first publish; on the plant Wi-Fi and again on mobile data, BR1-10): tap **Help**
on an Android phone and on the iPhone; the Help home opens in a new tab, through the Keycloak login
(a real login is a device check) or at once when the realm session is still open; **Open the user
guide** shows the reading page, and its pictures load (**important**). Also: a realm user without
`maintenance_team` or `it_admin` gets the gallery's "not found" for both pages.

## 6. Open questions and assumptions

- **Q1 (KLA, before the first publish, not before the coding).** KLA adds Yantra to the Gallery
  repo's `repos.toml` (`key = "yantra"`, `path = "../Yantra"`, `folder = "help"`), commits the
  step, then runs the collector (`tooling
un-collector.bat --dry-run` first). Until then the
  Help button leads to the gallery's "not found"; so the first publish goes before the release
  that ships the button.
- **Q2.** A later step that changes a screen the guide shows does nothing about the guide; it is
  retaken before a release that changes screens, on KLA's word (the *Docs to keep current* row).
- **Assumption:** the Help home shows the app version of its screens (v0.1.15 + PM, 02-11-2026),
  written by hand when the guide is retaken.

## Review log

| ID | Finding | Answer |
|---|---|---|
| BR1-01 | Belongs on the full track by file count (about 85, 73 of them guide content) | Accepted (a): keep light; the code files number about 12, KLA chose light (4a). For KLA at gate A |
| BR1-02 | Q1 must be settled before coding | Accepted (a), then superseded by KLA-2: the address is fixed by the gallery contract (D10), so nothing waits on a publish |
| BR1-03 | The tour's run protocol is left to the coder | Accepted (a): one driver `tooling/help/tour.py` in a `try/finally`; `serve.py` goes; § 1, § 3 |
| BR1-04 | The tour copies `run_lanes.py` | Accepted (a): it imports `one_run_at_a_time`, `main_scratch`, `lane_database`, `create_databases`; § 1, D4 |
| BR1-05 | D4's output paths not named | Accepted (a): § 3 *Output paths* |
| BR1-06 | The tour writes to the database directly | Accepted (a): the three touch-ups named in § 1 and D6, one function; the "(Technician)" oddity was the seed's, removed from Out of scope |
| BR1-07 | No map from slide to screenshot | Accepted (a): a table in `help/guide-outline.md` |
| BR1-08 | The `help/` docs row contradicts Q2 | Accepted (a): the row's text in § 3; Q2 says the same |
| BR1-09 | The title loses a third of its room at 360 px | Accepted (a): the `@device` test asserts the title in view and ≥ 60 px |
| BR1-10 | The device check names no account or network | Accepted (a): § 5 |
| KLA-1 | 02-11-2026, after r1: HTML pages, no dependence on artifacts, the slide show and a doc both as web pages | Accepted: § 1 (one guide page, two views), D5 (WebP committed), D7–D9, § 5 page checks; not re-reviewed (light track, no blocker or major open) |
| KLA-2 | 02-11-2026: "We now have a gallery.mspv.app": the gallery is SMTW's, not claude.ai | Accepted: § 1, `help/` as the gallery folder (D10), access (D11), Q1 is now the `repos.toml` entry and the publish; no claude.ai page is used |
| CR1-01 | Code review r1: the phone top bar of round 1 broke the 44 px targets and Sign out's icon (S064 UX-02) | KLA 02-11-2026 (a): hide the word "Yantra" on phones, keep 44 × 44 targets and the icon; fixed in fix round 2. A hamburger menu for Help and Sign out is queued for later |
| BR1-11…BR1-14 | Nits | Accepted: paths in `guide-outline.md`, the long lines, the imports after the move, "73 files" + `outline.md` |
