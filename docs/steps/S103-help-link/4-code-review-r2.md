```
Step: S103 — Help: a link in the app to the user guide in the gallery
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 02-11-2026
```

# S103 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** Fix round 1 fixes CR1-02 to CR1-10 as the
findings asked, and it brings in no new fault. CR1-01 stays open for KLA at gate B. Two new nits
remain.

## Tests run

- Tooling suite, `YANTRA_TEST_RUN=s103cr2 tooling/run-tooling-tests.bat`: **PASSED**, 258 passed
  (`scratch/tooling-tests-s103cr2.log`). The suite includes the line-width test, so the changed
  `tooling/help/*.py` lines and `test_help_pages.py` keep to 120 characters.
- I ran no backend or frontend suite. The round changed no backend code and no app code in
  `frontend/src`. It changed only `frontend/help-tour/shot.js`, which no unit suite runs.
- Browser tests: I ran none. No spec or screen changed, so the coder's choice to run none is
  right. The coder re-ran the tour once (19 passed, `scratch/help-shots-run3.log`).

## Status of the round 1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Open, for KLA at gate B (not part of this round, as agreed) |
| CR1-02 | minor | Fixed |
| CR1-03 | minor | Fixed |
| CR1-04 | minor | Fixed |
| CR1-05 | minor | Fixed |
| CR1-06 | nit | Fixed |
| CR1-07 | nit | Fixed (the comment option) |
| CR1-08 | nit | Fixed |
| CR1-09 | nit | Fixed |
| CR1-10 | nit | Fixed; one gap, CR2-02 |

How I verified each fix:

- **CR1-02.** The cover and the *About these screens* slide no longer name steps, "adoption" or a
  tooling path. A grep of `help/` for `S0NN`, `adoption` and `tooling` finds nothing on the three
  pages. The new wording follows the brief's own assumption (§ 6, "v0.1.15 + PM, 02-11-2026") and
  the Help home's footer.
- **CR1-03.** `equipment:edit` is `("maint_engineer", "it_admin")` (`backend/config_rbac.py:96`).
  `ROLE_INCLUDES` gives the manager the engineer's keys (`:83`). Both the `equipment` and the
  `model` owners use `equipment:edit` as their write key (`backend/documents.py:195-200`). So
  "Engineer, manager and IT admin" is right for sections 2–5 and the rules row. Restore and erase
  stay "Manager and IT admin" (`equipment:purge_documents`, `:99`), which is also right.
- **CR1-04.** `shot.js` imports `expect` from `@playwright/test` (line 4). `tryDo` is called
  inside the tests' bodies, so `expect.soft(false, …)` marks the running test failed and the test
  still goes on to take its shot. A failed test makes `npx playwright test` exit 1. `tour.py:91-94`
  returns that `returncode`, `main()` prints "The tour failed", and `sys.exit(main())` passes the
  code on. `tooling/help-shots.bat` ends with `exit /b %ERRORLEVEL%`. `tour.config.js` has
  `retries: 0`, so a retry cannot turn a failed test green. The tour still writes the WebP files
  after a failed run, and the new `help/README.md` line tells the user not to copy any shot then.
  The missing red run has a stated reason (it needs a broken selector), so it is not a finding.
- **CR1-05.** `sql()` now uses `run_lanes.COMPOSE` (a list, `run_lanes.py:73`) and
  `run_lanes.DEV_ROOT_PASSWORD` (`:74`), the same form as `run_lanes.py:444`.
- **CR1-06.** The comment before `check_target` says what the check can refuse.
- **CR1-07.** The `tour.py` docstring names the four files that hold lane 9 and its ports. My
  round 1 count of five places counted `setup_tour.py` and `tour.py` apart; four files is right.
- **CR1-08.** The docstring lists `scratch/e2e-vite-lane9/`.
- **CR1-09.** `help/README.md` says to open each `index.html` itself, and step 2 copies only the
  files that do not start with `doc-`.
- **CR1-10.** The test checks names of at most 100 characters, paths below the app folder of at
  most 120 (as the collector's `MAX_PATH_CHARS`, "characters below the app folder"), and paths that
  differ only in capitals. For the gap, see CR2-02.

## Findings

No `blocker`, `major` or `minor` finding is new in this round.

## Nits

- **CR2-01** (nit) `help/guide/index.html:184`, `:1199`, `help/README.md:59`: the cover's line now
  says the date twice ("Screens taken 02-11-2026 … as of 02-11-2026"), so end it after "sample
  plant data" and keep only the new sentence. The version is now also on the closing slide, so
  add "and its last slide" to README step 3, or a retake leaves that slide stale.
- **CR2-02** (nit) `tooling/tests/test_help_pages.py:79-81`: the capitals check compares whole
  file paths only, but the collector also compares each folder prefix (`validate.py`
  `_case_clashes`). `PART` allows capitals, so `Shots/a.webp` beside `shots/b.webp` passes here
  and is refused there. Check every prefix of each path, as the collector does.

## Manual checks

Unchanged from round 1. The impl report's `## Manual checks` still carries every important check
of the brief. Still for the user:

- [ ] **Important.** Open `help/guide/index.html` from disk at about 1366 × 768 and at 360 px,
  and `help/documents/index.html` at 360 px and at 1366 px (as in round 1). Look also at the new
  cover line and the last slide.
- [ ] **Important.** On a phone, the top bar at 360 px (CR1-01: KLA decides at gate B).
- [ ] **Important.** Device-checks row 69, after the release and the first publish.
- Device-checks row 70.

## Checked and found consistent

- Files re-read: the fix round's diff of all seven files; `frontend/help-tour/shot.js` (imports),
  `frontend/help-tour/tour.config.js`, `tooling/help/tour.py` (the run and exit path),
  `tooling/help-shots.bat`, `tooling/tests/test_help_pages.py:55-82`, `help/README.md:28-64`,
  `help/guide/index.html:178-186` and `:1191-1201`.
- Facts checked against their source: `backend/config_rbac.py:82-99`,
  `backend/documents.py:194-204`, `tooling/e2e/run_lanes.py:73-74`, and the gallery collector's
  `rules.py:30` and `validate.py:45,155-167` (read only).
- The round's `## Docs updated` names `help/README.md`. No other doc in *Docs to keep current* is
  due: the round has no migration, no secret, no role change and no maintenance rule.
- The round's changes stay inside the findings. It touches no app code, no spec and no shared
  frontend file.

## Feedback

- none
