```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096, S097, S098, S099, S100, S101, S102 (the step's own files are new)

**Verdict: no blocker or major finding. Ten minor findings, four nits.** Light track, so this is the only round. The facts file `scratch/brief-facts-S103.md` was given and used. One check lies outside the repo (BR1-02: who can open a gallery page, and whether a public page keeps its address); it goes to the user.

The code the brief cites holds: `AppTopbar.vue` is the one top bar (rendered twice by `App.vue`, `topbar-desktop` and `topbar-mobile`), the bell is a 44 px `router-link` shown to `push:subscribe` holders, and that key is `("*",)`, so every logged-in person sees it; `vite.config.js:27` excludes only `e2e/**` and vitest's default include is `**/*.{test,spec}.?(c|m)[jt]s?(x)`, so `*.tour.js` is not picked up; `playwright.config.js` has `testDir: "./e2e"`; `run_lanes.py` holds the lock with `msvcrt.locking` on byte 0 of `scratch/e2e-run.lock` in the main working folder (`one_run_at_a_time`, `_lock`, `main_scratch`), creates lane databases with the dev root password (`create_databases`, `lane_database`), and `e2e_backend.py` with `E2E_LANE=9` takes `vel_yantra_lane9_e2e`, port 5019 and `scratch/e2e-data/lane9/`. `scratch/tour/` holds 67 PNGs, and the deck's source is `deck.json` plus 72 slides.

## Findings

### BR1-01 — minor — Belongs on the full track: the file count

**Problem.** The light criterion "roughly 10 files or fewer" fails. The step adds about 85 files: 73 under `help/guide/`, `help/README.md`, `help/home/index.html`, `help.js`, four tour files, three Python files, the `.bat`, and edits to `AppTopbar.vue`, `floor.spec.js`, `.claude/CLAUDE.md` and `Plan.MD`. The tour is also a new tooling stack (lock, servers, seed, data, Playwright), not a plain copy of an existing pattern.

**Why it matters.** The track rule asks for the finding; it alone never blocks (23-10-2026).

**Options.** (a) Keep light: the 73 guide files are content, and the code files number about 12 (recommended; KLA chose 4a). (b) Switch to full.

### BR1-02 — minor — Q1 must be settled before coding, not before the release

**Problem.** `HELP_URL` is fixed in the code (D2) and the browser test asserts it. The brief's deck link is a private gallery address (`claude.ai/artifact/…`), and § 6 says the deck is private now. If plant staff need a public link, the Help home's address may change when it is published for them, and with it the code and the test. Q1 says "to verify before the release".

**Why it matters.** The coder hard-codes the address at the start. A later address change is a second edit of `help.js` and `floor.spec.js` after the step is done, and the device check (§ 5) cannot run before Q1 is answered.

**Options.** (a) KLA checks the Help home's Share menu and publishes it for plant staff before the coder starts; the orchestrator writes the final address into § 3 (`HELP_URL`'s value) (recommended). (b) Keep Q1 for the release and accept the second edit.

I cannot verify the gallery's sharing model from the repo (assumption: a page shared with "anyone with the link" may get a different address from the private one).

### BR1-03 — minor — The tour's run protocol is left to the coder

**Problem.** § 1 and § 3 say one command, `tooling/help-shots.bat`: "start the stack, run the tour, stop". The run of 02-11-2026 was three commands: `serve.py` (takes the lock, starts the servers, seeds, then waits for a stop file `scratch/tour/stop`), `setup_tour.py`, `npx playwright test`, then the stop file by hand. The brief does not say how the `.bat` sequences them, who holds the lock across the steps, or how the Playwright run gets `E2E_LANE=9` (shot.js re-exports `apiAs` and `personId`, whose port comes from `e2e/support/stack.js` reading `E2E_LANE`).

**Why it matters.** The coder decides the tool's shape alone. A `.bat` that starts `serve.py` in the background and polls for "seeded" is fragile; the stop file is a hand-off that a failed Playwright run leaves behind with the servers up (§ 5 asks that the ports are freed and the lock released).

**Options.** (a) One Python driver, `tooling/help/tour.py`: lock, database and grant, backend and Vite, seed, `setup_tour`, `npx playwright test -c help-tour/tour.config.js` with `E2E_LANE=9` in its environment, then stop, all in one `try/finally`; `serve.py` folds into it; the `.bat` calls it; no stop file (recommended). (b) Keep `serve.py` with the stop file and write the sequencing into the `.bat`.

### BR1-04 — minor — The tour copies `run_lanes.py` instead of importing it

**Problem.** `scratch/tour/serve.py` has its own `lock()` (the same `msvcrt.locking` on byte 0), its own CREATE DATABASE and GRANT statement with the dev root password as a literal, and locks `ROOT/scratch/e2e-run.lock`, not `run_lanes.main_scratch()`. D4 says it holds the lock "as `run_lanes.py` does".

**Why it matters.** Two copies of the lock drift; in a worktree the copy locks a different file, so the tour could run beside a release's browser run. The root password string gets a third home.

**Options.** (a) Import `one_run_at_a_time`, `main_scratch`, `lane_database` and `create_databases` from `tooling/e2e/run_lanes.py` (a `sys.path` entry for `tooling/e2e`, as `e2e_backend.py` does for `backend`); `create_databases(9)` grants lanes 1–9, which is harmless (recommended). (b) Lift the four helpers into a small shared module both import. (c) Keep the copies and state it.

### BR1-05 — minor — D4's "writes only its lane database and `scratch/`" needs the paths named

**Problem.** The moved files write elsewhere unless changed: `tour.config.js` has `outputDir: "./results"` (under `frontend/help-tour/`, a tracked folder); `setup_tour.py` writes `scratch/tour/data.json`, which `shot.js` reads as `../data.json` relative to itself (under `frontend/help-tour/` that is a tracked path); `shot.js` writes to `HERE/../shots`; `serve.py` writes `backend.log` and `vite.log` beside itself.

**Why it matters.** The coder picks the paths alone, and a wrong pick leaves untracked files in `frontend/help-tour/` after every run (§ 5 asks that `git status` is unchanged).

**Options.** (a) § 3 names them: PNGs `scratch/help-shots/`, the ids `scratch/help-shots/data.json`, logs `scratch/help-shots/backend.log` and `vite.log`, Playwright's `outputDir` `../../scratch/help-shots/results` (recommended). (b) One folder constant in `tour.py` passed to Playwright through an environment variable the config reads.

### BR1-06 — minor — The tour writes to the database directly, which the brief does not say

**Problem.** § 1 says the tour "adds standard plant data through the API", and D6 says it "does not patch the app or the seed". `setup_tour.py` also runs three SQL statements as root through `docker compose exec` (`sql()`, lines 77, 109, 111): it strips " (role)" from every `people.name`, renames the seed's scrapped compressor, and rewrites a ticket's description.

**Why it matters.** A departure from the stated pattern the coder would carry over or drop alone. The people rename is also the cause of the "Kannan (technician) (Technician)" oddity § 1 lists as the app's: the top bar's name comes from `seed_e2e.display_names`, not from `people.name`, so the two no longer agree.

**Options.** (a) State the three touch-ups in § 1 and D6 with why (no API renames a person or edits a raised ticket's description), and keep them in one named function (recommended). (b) Drop them: the shots then show "Kannan (technician)" as the person's name, and the app oddity disappears from the index queue (it is the tour's doing, not the app's).

### BR1-07 — minor — No map from slide to screenshot for a retake (D5, README)

**Problem.** The slides reference gallery uploads by hash (`x01.html`: `src="/_blob/bac9f0…"`, alt "Me page, open work, on a phone"); neither the slide nor `deck.json` names the PNG (`01-me-open-work-phone.png`). D5 says a retake means "pointing the slides at the new uploads".

**Why it matters.** The repo copy of the guide does not render locally, and the person retaking has to match 64 images to slides by eye.

**Options.** (a) `help/guide/outline.md` gets a column (or a short `images.md` table): slide id, PNG file, alt text, written once by the coder from the deck; the README says the `/_blob/` images resolve only in the gallery (recommended). (b) The slides' `alt` text is made the PNG's file name at the next republish.

### BR1-08 — minor — The `help/` row of Docs to keep current contradicts Q2

**Problem.** § 3 adds a row for `help/` to `.claude/CLAUDE.md` § Docs to keep current, whose form is "due when the step…". Q2 assumes a step that changes a screen the guide shows does **not** note it. The brief does not say what the row says.

**Why it matters.** The coder writes the rule alone, and the docs pass of every later step reads it.

**Options.** (a) The row says: "changes a screen the guide shows: nothing in the step; the guide is retaken and republished before a release that changes screens, on KLA's word (`tooling/help-shots.bat`, `help/README.md`)" (recommended, matches Q2). (b) Drop the row and leave the rule in `help/README.md`.

### BR1-09 — minor — At 360 px the page title loses a third of its room

**Problem.** The right group grows from about 150 px (bell 44, gap 8, Sign out about 100) to about 195 px. With "Yantra" (about 45 px) and 24 px padding, the title keeps about 95 px of 360: "Improvement register", "My notifications" and "Page not found" end in an ellipsis at 0.85 rem bold (`.topbar-center` has `min-width: 0` and `text-overflow: ellipsis`; the user name shrinks to nothing first). The brief's 360 px test checks Help, the bell and Sign out, not the title.

**Why it matters.** The title tells a phone user which screen is open; the bottom bar also shows it, so a cut title is a nuisance, not a block.

**Options.** (a) Accept the ellipsis, and the `@device` test also asserts the title is in view with a width of at least 60 px, so a later change cannot push it out (recommended). (b) Hide the "Yantra" brand below 400 px to give the title 45 px back.

### BR1-10 — minor — The device check names no account and no network

**Problem.** § 5's device check says IT Admin, production on the TEST machine, "for a plant user", on an Android phone and the iPhone. No test login, no network.

**Why it matters.** The network decides the result: the gallery is an outside site, and the plant Wi-Fi may filter it where mobile data does not. The rule asks for account, network and where on every device check.

**Options.** (a) "The operator test login; on the plant Wi-Fi and again on mobile data; production on the TEST machine" (recommended). (b) Plant Wi-Fi only.

## Nits

- **BR1-11** (nit) § 1 and D5: `help/guide/outline.md` says "Shots are in `scratch/tour/shots/`" and the deck's closing slide says "run the screenshot tour again (`scratch/tour/`)"; both change to `tooling/help-shots.bat` and `scratch/help-shots/` (the slide at the next republish).
- **BR1-12** (nit) § 3, `tooling/help/setup_tour.py`: nine lines are over 120 characters (85, 94, 131, 132, 224, 236, 296, 313, 334); the line-width test is red until the coder wraps them. Say so in the row.
- **BR1-13** (nit) § 3, `frontend/help-tour/`: `shot.js` imports `../../../frontend/e2e/support/people.js` and `dialogs.js`; under `frontend/help-tour/` they are `../e2e/support/…`; `tour.config.js` `testDir` becomes `"."` and its two projects keep their `testMatch` (`/phone/`, `/desktop/`) and scale factors (2 and 1.5, which the outline states).
- **BR1-14** (nit) § 1: "73 files" counts `deck.json` and the 72 slides; with `outline.md` the folder holds 74. Say "the deck's 73 files and `outline.md`".

## Checked and found consistent

- D1: `navItems` has five phone items and `landingNavItem(permissions)` picks the first item the person may open, so a keyless nav item would become a landing page.
- D3: `frontend/playwright.config.js` reads only `./e2e`; vitest's include does not match `*.tour.js`; `frontend/package.json` has `"type": "module"`, so the tour's ESM files need no `package.json` of their own (the scratch copy had one).
- D4: lane 9 is above the default 6 and under `MAX_LANES` 20; `e2e_backend.py` drops and rebuilds `vel_yantra_lane9_e2e` and empties `scratch/e2e-data/lane9/`; `scratch/` is gitignored. The tour's writes stay in the repo tree and the dev database container; the processes it kills are its own.
- § 5: S064's top-bar test asserts Sign out in view and 44 px high; one more 44 px link leaves it so on the Pixel 7 (412 px). `expectNoSidewaysScroll` exists in `e2e/support/dialogs.js`. IT admin holds `push:subscribe` (`*`), so the bell is there in both runs of the first test.
- Use on the floor: Help sits beside the bell, apart from Sign out; a question-mark icon with `aria-label` and `title` "Help" needs no reading; it shows also to a person with no Team record (the top bar renders beside `NoAccessView`), which is the one place such a person can learn what to do.
- Standards: ISO 9001 § 7.5 (documented information is identified, versioned and controlled: the source in git, the version on the Help home) and the TPM education-and-training pillar are named and fit; the masters slides as onboarding with ISO 14224's taxonomy is right.
- Manual checks: the two browser checks are automated; the tour run is the coder's check, marked important; the device check is the only one a browser cannot do (a real tab to an outside site on a real phone).

## Feedback

- waste: the facts file listed `node_modules` and `e2e_operator` as code names with their users (6 lines of no use); backticked words that are a folder or a test login could be skipped (`scratch/brief-facts-S103.md` § Code names).
- idea: a brief that moves files from `scratch/` could get, in the facts file, the long-line count of each `.py` it moves (BR1-12 cost one awk run; `brief_facts.py` has the file list).
