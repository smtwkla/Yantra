```
Step: S077 — One-point lessons: screens
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S077 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 5 minor findings and 4 nits. The
screens follow the brief. The save sequence of the dialog, the create-only `equipment_id` /
`action_id`, the class name in the tick and the shared `FormModal` change are correct. The open
points are a photo that fails to load on the lesson page, one test gap, test isolation from class
lessons, a small near-copy, and a wrong line in the impl report.

Read: the brief with its Review log, the impl report, the step's whole diff
(`step_snapshot.py diff S077`), `useFormModal.js`, `usePhotoUploads.js`, `FormModal.vue`,
`DocumentsCards.vue` (blobs and download), `EquipmentDetailView.vue` (the card's place),
`RemovedDocuments.vue`, `backend/procedures.py` (list, detail, PUT) and `improvements.py`
(`can_write_lesson`).

## Test runs

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s077cr1 tooling/run-tests.bat` | backend 4051 passed, frontend 368 passed, tooling 185 passed: PASSED |
| `npx vite build` | built; only the existing chunk-size warning |
| `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit` (due: `e2e/support/lessons.js` is new, CR1-02) | **9 passed** (1.8 min), WebKit in Docker |

I did not run the whole suite. The coder's runs are recorded with real counts: the new tests alone
12 passed; targeted (lessons, improvements, equipment, settings, screens, me) 123 passed and 2
skipped; the whole suite at Normal 313 passed and 15 skipped. The targeted run names the right
specs (brief § 8.1 *Runs*, plus `me.spec.js`).

## Findings

### CR1-01 (minor) — a lesson photo that fails to load spins for ever

`frontend/src/views/LessonView.vue:65` and `:180`. A failed photo fetch is dropped
(`() => {}`). `photoUrls[p.id]` stays empty, so the template shows the spinner under the
caption for as long as the page is open.

- **Scenario:** An operator on weak plant Wi-Fi opens a lesson. One 6 MB photo fails (a timeout, or
  a 503). The page shows a spinning icon where the picture should be. The operator waits for a
  picture that never comes, and nothing says to reload.
- **Fix:** Keep a `photoFailed` map, as `DocumentsCards.vue` keeps `thumbFailed` (its
  `loadThumbs`). Show a short line in place of the spinner, for example "The photo could not be
  loaded. Reload the page." Clear the map in `revokePhotos`.

### CR1-02 (minor) — the impl report says `e2e/support/` is unchanged; the WebKit run was due

`docs/steps/S077-one-point-lesson-screens/3-impl-report.md`, § 5, last bullet. The bullet says
"`e2e/support/` and `api.js` are unchanged, so the WebKit run of `screens.spec.js` was not due".
But `frontend/e2e/support/lessons.js` is a new file there. `.claude/CLAUDE.md` § Step workflow,
*Shared code*, then asks for `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`
once.

- **Scenario:** The report tells gate B that the run was not due, so nobody runs it, and a WebKit-only
  fault in the new set-up would reach the release.
- **Fix:** I ran it in this round: 9 passed. Correct the bullet, and record this run under § Tests.

### CR1-03 (minor) — no test of the close-only path, where `saved` comes from `@closed`

`frontend/src/views/equipment/LessonDialog.vue:130-160` (`save()`, `onClosed`); `frontend/e2e/lessons.spec.js`.
BR2-01 adds FormModal's `closed` event so that the close-only *Close* hands the saved lesson to
the page. No test goes through that path: test 1 uploads a good photo, so it covers only the
close after the photos. S071 has this test for *Mark done* (`frontend/e2e/improvements.spec.js:502`).

- **Scenario:** A later change emits `saved` only from `save()`, or clears `savedLesson` in
  `reset()` before the fade ends. The lesson is saved, but after *Close* the engineer stays on
  the machine's page, and the card shows the lesson only after a reload. Every test stays green.
- **Fix:** Add `S077: a photo the server refuses leaves the lesson saved; Close opens the lesson`,
  on the pattern of S071's test. Use `bad.jpg` with a non-image buffer, and
  `consoleWatch.allowFailedRequest("/api/procedures/", 400)`. Assert the text "Lesson saved. A photo
  was not saved. Add it again, or close.", the footer with *Close* only, then *Close*, then the URL
  `/equipment/lessons/<id>`.

### CR1-04 (minor) — the class lesson of one test stays on every HP machine for the rest of the lane

`frontend/e2e/lessons.spec.js:63` (`a lesson for the class shows on another machine of the class`).
D8 records why the lessons tests do not count rows. But the test leaves its class lesson active.
For the rest of the run, every class `HP` machine in that lane's database gets a *Lessons* card
above *Open tickets* and the Meters card. That includes every `meterMachine` of
`readings.spec.js`, `equipment.spec.js`, `tickets-work.spec.js`, `journeys.spec.js` and
`screens.spec.js`. Brief § 8.1 asks that "no other spec's page changes". The whole suite passed
once, but the lane plan decides whether a spec runs before or after this test.

- **Scenario:** A later `@device` test on an HP machine's page checks that the Meters card or the
  *Open tickets* card is in the first screenful. It passes when it runs before `lessons.spec.js`
  in its lane and fails after it, so it fails only now and then.
- **Fix:** End the test by retiring its lesson by API (or unticking it), with a small
  `retireLessonByApi(lesson)` in `support/lessons.js`. A retired class lesson shows on no card for
  a reader. Add one line to D8 that says so.

### CR1-05 (minor) — `downloadDocument` repeats DocumentsCards' `downloadPdf`

`frontend/src/views/LessonView.vue:128-143` is a near-copy of
`frontend/src/components/documents/DocumentsCards.vue:170-183`: fetch the blob, make an `<a
download="<title>.pdf">`, click it, remove it.

- **Scenario:** A later fix to the download (a file name on iOS, a different extension) is made in
  DocumentsCards only. Then the lesson page's PDF links download differently from every other
  document link.
- **Fix:** Move the anchor part into one helper in `frontend/src/utils/` (for example
  `downloadBlobUrl(url, fileName)`), and call it from both. Each caller keeps its own blob cache.

## Nits

- **CR1-06** (nit) `frontend/src/composables/usePhotoUploads.js:16`: the header still says "FormModal emits no close event". Change it to say that the preview is freed at the next open and on unmount, so that it is not freed during the fade.
- **CR1-07** (nit) `frontend/src/views/equipment/LessonsCard.vue:142`: "Retired lessons (n)" is a `btn-link p-0`, a small target on a phone. Add `tap-target`, as the card's other button has.
- **CR1-08** (nit) `frontend/src/views/LessonView.vue:155`: the *Retry* button has no `tap-target`, unlike every other button on the page.
- **CR1-09** (nit) `frontend/src/views/equipment/LessonsCard.vue:121`: when a writer's machine has only retired lessons, the card says "No lessons yet." above "Retired lessons (1)". "No lessons in use." would be true in both cases.

## Checked and found consistent

- **The `FormModal.vue` `closed` emit:** no other caller listens for `closed` (grep of `frontend/src`).
  Before S077 the event was not declared, and no listener could hang on it. The change does not
  alter any existing dialog's behaviour. The emit on the `hidden.bs.modal` listener runs after the
  fade, also on the unmount path, and there it does no harm.
- **The save sequence of `LessonDialog`:** POST, then `savedLesson`, then `markClean()`, then
  `uploadAll()` with `saving` still true, then `modal.close()`. A failed photo sets `closePhase`,
  and FormModal gets `closeOnly`. Photos chosen in that phase go up at once, under `saving`.
  `:dirty="!closePhase && (dirty || files.length > 0)"`. `saved` comes only from `@closed`, once,
  and never after a *Cancel* (`savedLesson` is null then). A refusal sets a new `error` object, so
  the reveal fires. A refusal on `equipment_id` or `action_id` is no form key and shows in
  `modalError`.
- **`equipment_id` / `action_id` only on create:** `toBody` adds them only when `editingId` is
  null. A change sends title, body and `for_class`, or only title and body without the tick (D5).
  The change test runs on a lesson linked to a countermeasure (BR2-03).
- **The class tick label:** the card passes the node's class from the classes store. The improvement
  page and a machine lesson's change read `GET /api/equipment/<id>` and `ensureEquipmentClasses`.
  A failed read keeps "Show on every machine of this machine's class" (`classTickLabel`, unit-tested).
  `improvements.spec.js` asserts the named label from the improvement's machine.
- **The operator's path after a QR scan:** the card stands after *Raise ticket* and the edit buttons,
  before *Open tickets*, `order-0`. Documents stays `order-1` and Details `order-2`. The titles are
  `fs-5` on the card and `fs-3` on the page. On the page, the photos come before the text, at full
  width, `max-height: 60vh`. The text is `fs-5` with `pre-line`. The Tamil test checks the characters,
  and real glyphs are device check row 56. A reader with no lessons sees no card. The `@device`
  QR test raises three open tickets first. Screen text is short and plain (scope B), and "OPL" never
  stands without "Lesson" before it, except as the serial.
- **The lesson page and *Print lesson*:** it follows brief § 5.2: the target line, the retired
  banner, the serial, date and writer, "From improvement …" when `source` is set, and "Last
  changed …". `.no-print` is on the buttons, the PDF list and *Edit photos*. Photos are 40 vh in
  print. The not-found text and its link are as the brief says. A 503 shows the server's text with
  *Retry*. Object URLs are revoked on reload and on unmount, and a reload keeps the photos it has.
- ***Write lesson* on a countermeasure:** the button follows `can_write_lesson`, which
  `may_write_lesson` computes with the create's own unit and site checks. The page opens the dialog
  with the improvement's machine, the row's text (cut to 1000 characters, D6) and `action_id`. On
  `saved` it reloads and stays on the improvement. The lesson line shows " (retired)" when
  `lesson.active` is false.
- **The retire question:** it replaces the button row, so only one *Retire lesson* is on screen.
  The danger button and *Keep it* are both `tap-target`. Bringing back asks nothing. The test
  asserts all of this.
- **The removed-documents lesson row:** "Lesson <serial>" with the code and unit, and "lesson
  number" in the search placeholder. `restoreBlocked` has no rule for `procedure`, which matches
  S075 § 5.8.
- **`expectDialogFits`:** it is called on every FormModal the flow tests open: *Add lesson* twice,
  *Change lesson* twice, and *Write lesson*. The DocumentsCards photo viewer has no Save or Cancel,
  so the helper does not apply; S071's test does the same.
- **Tags:** the two `@device` tests are geometry checks, and every other test is untagged.
- **D8 (test isolation):** reported as a departure, and forced by the data (class lessons show on
  every machine of the class). The empty-card test uses the seed extruder. `screens.spec.js` writes
  a machine-only lesson on a machine it makes. See CR1-04 for the lesson that is left active.
- **Security:** the step adds no backend route. The page has no nav item, and the API's 404 is its
  gate. The dialog takes no actor from the client.
- **Docs pass:** `docs/Plan.MD` § 6 and `device-checks.md` rows 56–58 are updated. No migration.
  `.claude/CLAUDE.md` is left to the orchestrator by instruction, and the text is proposed in the
  report.
- **Manual checks:** the report carries every automated check as `[auto]`, each with a test that
  asserts what the user sees, and the two important device checks as unticked boxes.

## Manual browser checks still needed

- Rows 56–58 of `docs/steps/device-checks.md`: Tamil on a Samsung phone, an iPhone and a desktop;
  printing on A4 at the plant's printer; a real QR scan of the TEST machine.

## Feedback

- hindrance: the coder's report said `e2e/support/` was unchanged although `step_snapshot.py diff --stat` lists `frontend/e2e/support/lessons.js` as new; a line in the report cannot be trusted for a "due" decision (1 WebKit run, 2 min).
- idea: `step_snapshot.py diff --stat` could flag the files that match the *Shared code* entry, so that the coder and the reviewer see the WebKit and whole-suite duties at once.
