```
Step: S077 — One-point lessons: screens
Doc: impl-report
Author: Coder (Sonnet)
Date: 30-10-2026
From: R05.6
```

# S077 — Implementation report

**Result:** the screens of one-point lessons are built as the brief says, on S075's API: the *Lessons* card
on the equipment page, the lesson page with print, the dialog *Add lesson* / *Change lesson* with photos,
*Write lesson* on a countermeasure, and the lesson row in Settings › Removed documents. All unit suites are
green (backend 4051, frontend 368, tooling 185); the build is clean; the new browser tests pass, the targeted run
(123 passed, 2 skipped) and the whole suite at Normal (313 passed, 15 skipped) are green (§ Tests). No question for the user: the stale
brief check found only details that the code settles (§ 0).

## 0. Stale brief check (§ 9)

I compared every field, route and file the brief cites with S075's code, S071's screens, the equipment page
and Settings › Removed documents as they are now. **No difference changes the design.** Differences, and what
I did:

| Brief says | Code has | Followed |
|---|---|---|
| `datetime.js` exports only `formatDateTime`; `lessonDate` is `formatDateTime(…).slice(0, 10)` (§ 3) | `datetime.js` now also exports `formatDate` (the date part, DD-MM-YYYY) | `lessonDate` calls `formatDate`: the same result, no `slice` |
| `FormModal.vue:121-123`, the `hidden.bs.modal` listener | The listener is at `FormModal.vue:121-124` (S071 added nothing there); it only clears `visible` | One line added: `emit("closed")` after it; `defineEmits(["save", "closed"])` |
| The S064 UX-07 comment at `EquipmentDetailView.vue:233-234`; *Open tickets* at `:260` | The comment is at `:231-233`, the card at `:253` | Comment rewritten (Lessons, Open tickets, then Documents and Photos); the card placed before *Open tickets* in the DOM, `order-0` |
| `equipment.spec.js:946-954` (Documents before Details on a phone) | Same lines, same test | Runs green: Documents stays `order-1`, Details `order-2` |
| S075 § 6.3 `source: {improvement: {id, serial, title}, action_id}` | Exactly that (`procedures._source`) | Used as the brief says (`lesson.source.improvement`) |
| `usePhotoUploads({path, maxMb, previews})`, `uploadAll()` returns the count, `files` rows with `state` | Same (`composables/usePhotoUploads.js`); `path` and `maxMb` go through `toValue`, so a getter works | `path` is a getter on `savedLesson`, set after the `POST`, as the brief's "a ref set after the POST" |
| `MarkDoneDialog`'s save sequence: `POST`, `markClean()`, `uploadAll()` under `saving`, a close-only phase on a failed photo | Same; it emits `saved` right after the `POST` and keeps no `closed` hook | `LessonDialog.save()` follows the sequence; it emits `saved` only from FormModal's `closed` (BR2-01) |
| `CountermeasureItem`: emits `change`, `ask-cancel`, `keep`, `cancel`, `mark-done`, `photos`; flags `can_*` | Same; a `mine` item has neither `lesson` nor `can_write_lesson` | Added `write-lesson` and the lesson line, both guarded by the fields |
| `DocumentsCards` fires `changed` and takes `large-add` (S071 BR1-07) | Same | Used under *Edit photos* with `@changed="load"` |
| S075's removed row: `owner` `"procedure"`, `name` the serial, `code`, `unit`, `path` | Same (`documents._removed_item`, `_REMOVED_PROCEDURE_BRANCH`) | The row reads `item.name`, `item.code`, `item.unit` |
| § 8.1: each test makes "its own machines", so no other test's page changes | A lesson ticked for the class shows on **every machine of the class**, so a class lesson written by one test shows on the machines of all the other tests (class `HP` for every `meterMachine`) | Tests look for their own lesson's row (a unique title or the serial) and never count rows or expect "no card" on an HP machine; the *empty card* test uses the seed extruder, whose class no spec writes a lesson for (D8) |

## 1. What was built

- **The *Lessons* card** on the equipment page (`LessonsCard.vue`): the machine's lessons and its class's, each
  with its cover photo (or a grey icon), its title in large type, its number and, for a class lesson, the
  badge "Every <class>"; *Add lesson* for writers; "Retired lessons (n)" for writers; no card for a reader of a
  machine with no lessons. It stands before *Open tickets*, with `order-0`, on every width.
- **The lesson page** (`LessonView.vue`, route `/equipment/lessons/:id`): the target line, the retired
  banner, the card (number, date, writer, title, photos with captions, text), the link "From improvement …",
  "Last changed …", and the buttons *Print lesson*, *Change lesson*, *Edit photos*, *Retire lesson* /
  *Bring back lesson* (the retire question replaces the button row).
- **The dialog** (`LessonDialog.vue`): title, lesson text, the class tick, photos when adding; its own
  `save()` (POST, `markClean`, upload under `saving`, close or a close-only phase); it hands the saved lesson to
  its caller from FormModal's `closed`.
- **On a countermeasure**: the line "Lesson OPL-007 · title" (link, "(retired)") or the button *Write lesson*;
  the improvement page opens the dialog seeded from the row and reloads on `saved`, staying on the page.
- **Settings › Removed documents**: the row "Lesson OPL-007" with the machine's code and unit; the search
  placeholder names "lesson number".
- **Shared code:** `FormModal.vue` emits `closed` (one line plus the emits list).

## 2. How it works

**The card.** `LessonsCard` loads `GET /api/procedures?equipment_id=` on mount and when `node.id` changes
(a sequence number drops stale answers). The card shows when the list has items, `can_add` or retired rows,
or when the load failed ("Lessons could not be loaded: …"). Covers are fetched as blobs (`/thumb` when
`has_thumb`, else `/file`) and shown through object URLs, revoked on reload and unmount. The dialog sits inside
the card; after an add the card reloads, then emits `saved(lesson)`, and `EquipmentDetailView` pushes to the
lesson's page.

**The page.** `LessonView` loads `GET /api/procedures/<id>`. Photos are the full files, fetched as blobs and kept
by document id across a reload (only new ones are fetched, stale ones are revoked), so a change under *Edit
photos* does not blink the page. *Edit photos* shows `DocumentsCards` (both cards, *Photos* and *Documents*)
for `/api/procedures/<id>/documents`; its `changed` event reloads the page's copy. Retire and bring back are a
`PUT {active}` whose answer replaces the copy. A 404 shows "Lesson not found, or not at your units." with a link
to `/equipment`; any other error shows the server's text with *Retry*. Print is `window.print()`; the page's
print rule keeps the photos to 40 vh and drops the link styling, and `.no-print` hides the buttons and the
navigation.

**The dialog.** `openCreate({machine, body, action_id})` keeps the machine and the `action_id` in a `seed`
ref; they are no form fields, so a refusal on either shows at the top (`modalError`). `toBody` adds them only
on a create; a change sends title, text and `for_class` (without `for_class` when the tick is hidden), never
`action_id`. The class name for the tick comes from the caller, else `GET /api/equipment/<id>` (class id,
then the name through `ensureEquipmentClasses`); a failed read keeps the label "Show on every machine of this
machine's class". The upload limit comes from `GET /api/equipment/<id>/documents` when adding. `save()` posts,
keeps the answer in `savedLesson`, `markClean()`, uploads the photos with `saving` still true, and then closes;
a failed photo leaves the close-only phase ("Lesson saved. A photo was not saved. Add it again, or close.").
`@closed` emits `saved(lesson)` once, whichever way the dialog was closed after a save, and never after a
*Cancel*.

## 3. Files touched

Code (10):
- `frontend/src/components/FormModal.vue` (shared): `closed` emit from the `hidden.bs.modal` listener.
- `frontend/src/router/index.js` (shared): the route `lesson`.
- `frontend/src/views/EquipmentDetailView.vue`: `LessonsCard` before *Open tickets*; docstring and comment.
- `frontend/src/views/equipment/LessonsCard.vue` (new): the card.
- `frontend/src/views/equipment/LessonDialog.vue` (new): the dialog.
- `frontend/src/views/LessonView.vue` (new): the page.
- `frontend/src/utils/lessonLabels.js` (new): `lessonTargetText`, `classBadgeText`, `lessonDate`, `classTickLabel`
  (D1), the two bounds.
- `frontend/src/components/CountermeasureItem.vue`: the lesson line and *Write lesson*, `write-lesson`.
- `frontend/src/views/ImprovementDetailView.vue`: the `LessonDialog`, opened on `write-lesson`, reloading on `saved`.
- `frontend/src/views/settings/RemovedDocuments.vue`: the lesson row, the search placeholder.

Tests (5):
- `frontend/tests/lessonLabels.test.js` (new): 6 tests.
- `frontend/e2e/lessons.spec.js` (new): 11 tests (two `@device`).
- `frontend/e2e/support/lessons.js` (new): `lessonMachines`, `writeLessonByApi`, `addLessonPhotoByApi`.
- `frontend/e2e/improvements.spec.js`: the *Write lesson* test.
- `frontend/e2e/screens.spec.js`: the lesson page joins `screens()` for every role.

Docs (3): `docs/Plan.MD` (§ 6), `docs/steps/device-checks.md` (rows 56–58), this report (plus the brief's
status and the index row). No backend file is changed.

## 4. Decisions taken

- **D1. `classTickLabel(className)`** is in `lessonLabels.js` beside the other words (the brief gives the two
  texts, not a helper), so the plain label and the named one are tested without mounting the dialog.
- **D2. The dialog sits inside `LessonsCard`** (the brief says "the card opens the dialog"; where the dialog
  lives was open). The card emits `saved(lesson)`; the page pushes. A single root `<div class="order-0">` holds
  the card and the dialog, so the flex ordering of the page's column still applies to the card.
- **D3. The card shows the retired rows in the same list** as the active ones (after "Retired lessons (n)" is
  tapped), each with its "Retired" badge, instead of a second list: one row markup.
- **D4. `lessonDate` calls `formatDate`** (§ 0): same output as the brief's `slice`.
- **D5. The change dialog without the tick** (`can_change_class` false: an engineer of another site on a class
  lesson) sends no `for_class` at all, though the server treats an unchanged value as no change.
- **D6. The seed text is cut to 1000 characters** (`LESSON_BODY_MAX`) when the countermeasure's text (up to
  500) seeds the lesson: it can never be longer than the field, so the cut is only a guard.
- **D7. Photo captions are the photo's title** (S071's `usePhotoUploads` titles a photo with its file name
  without the extension); the caption is the lesson's own choice, changed under *Edit photos*.
- **D8. Tests and class lessons** (a departure from § 8.1's isolation, forced by the data): a class lesson
  shows on every HP machine, so a test never counts rows or expects an empty card on an HP machine. The
  *no card* test uses the seed extruder; the others look for their own row by unique title or serial.
- **D9. The retire question's wording** is the brief's: "Retire OPL-007? It leaves the machine's page. You can
  bring it back."

No departure from the brief's behaviour.

## 5. Not done, deferred or assumed

- **Not done:** *Shown to* and *Record who was shown* (R05.7, out of scope); a plant-wide list (S075 D6);
  Tamil labels (the app's labels stay English).
- **Assumed (brief § 9):** the page downloads each photo at full size; Tamil glyphs come from the system fonts;
  no bound on photos. The device checks (rows 56–58) confirm the last.
- **Not checked by a browser test:** the print layout itself (rows 57, a paper check), and Tamil glyphs (row 56).
  A test checks the characters.
- **`api.js` is unchanged, but `e2e/support/lessons.js` is new**, so the WebKit run of `screens.spec.js` was due (shared code: `e2e/support/`). It was not made in the first round; the code reviewer ran it (9 passed) and Round 1 ran it again (CR1-02).

## Docs updated

- `docs/Plan.MD` § 6 *Screens*: the *Lessons* card on the equipment page and the one-point lesson page, with
  print, *Write lesson* and the removed-documents row.
- `docs/steps/device-checks.md`: rows 56, 57 and 58 (TEST machine, test lesson retired after; Tamil on Samsung,
  iPhone and A4; a real QR scan).
- Not due: `docs/schema.md` (no migration), `docs/Keycloak.md`, `backend/example_secrets_app.py`,
  `docs/Maintenance-Philosophy.md` and `docs/Plant-Facts.md` (no rule or fact learned). `.claude/CLAUDE.md` is
  not edited by the coder; the exact text is under *Proposed CLAUDE.md changes*.

## Proposed CLAUDE.md changes

In `.claude/CLAUDE.md` § SMTW-Review, *Browser tests*, change the spec-to-step map:

1. add the entry `lessons` S075/S077 (a new spec file);
2. `equipment`: append `/S077` to its steps (the *Lessons* card);
3. `screens`: it reads "every route and S064"; it now includes the lesson page, so write "every route, S064 and S077";
4. `improvements` (S068 and later, the map does not list it yet): add the entry with S077 (*Write lesson*) among its steps.

And one new point under § SMTW-Review (after *Meter readings (S039)*):

> - **One-point lessons (S075, S077):** a lesson ticked for its class shows on every machine of that class, at
> every site, so a browser test of the lessons screens never counts rows or expects an empty card on a
> machine of class `HP` (every `meterMachine` is one); it looks for its own lesson's row. A new test that
> expects no *Lessons* card uses a machine whose class has no class lesson. The card shows on every node
> for `equipment:read` holders, the lesson page is a route with no nav item (the API's 404 is its gate), and
> `FormModal`'s `closed` event is the one place a dialog hands its saved record to a page after the fade.

## Manual checks

- [auto] An engineer adds a lesson with a photo on a machine; the card and the page show it — `frontend/e2e/lessons.spec.js::S077: an engineer adds a lesson with a photo on a machine; the card and the page show it`
- [auto] A lesson for the class shows on another machine of the class with its badge — `frontend/e2e/lessons.spec.js::S077: a lesson for the class shows on another machine of the class with its badge`
- [auto] An operator reads a lesson and sees no Add, Change or Edit photos — `frontend/e2e/lessons.spec.js::S077: an operator reads a lesson and sees no Add, Change or Edit photos`
- [auto] An operator sees no Lessons card on a machine with no lessons — `frontend/e2e/lessons.spec.js::S077: an operator sees no Lessons card on a machine with no lessons`
- [auto] An engineer changes the title and unticks the class; the other machine no longer lists it (on a lesson linked to a countermeasure; the class name shows in the tick) — `frontend/e2e/lessons.spec.js::S077: an engineer changes the title and unticks the class; the other machine no longer lists it`
- [auto] Retire asks first, the card leaves the lesson, Retired lessons brings it back — `frontend/e2e/lessons.spec.js::S077: retire asks first, the card leaves the lesson, Retired lessons brings it back`
- [auto] The server's refusal of an empty lesson text shows beside the field — `frontend/e2e/lessons.spec.js::S077: the server's refusal of an empty lesson text shows beside the field`
- [auto] A removed lesson photo is listed in Settings and restored — `frontend/e2e/lessons.spec.js::S077: a removed lesson photo is listed in Settings and restored`
- [auto] A Tamil title and text are shown as typed — `frontend/e2e/lessons.spec.js::S077: a Tamil title and text are shown as typed`
- [auto] Write lesson on a Lesson countermeasure opens the dialog seeded, and the countermeasure then links its lesson — `frontend/e2e/improvements.spec.js::S077: Write lesson on a Lesson countermeasure opens the dialog seeded, and the countermeasure then links its lesson`
- [auto] On a phone the Lessons card is in view after opening the machine by its QR link, with open tickets on it — `frontend/e2e/lessons.spec.js::S077: on a phone the Lessons card is in view after opening the machine by its QR link, with open tickets on it`
- [auto] The lesson page's title and first photo are on screen without scrolling — `frontend/e2e/lessons.spec.js::S077: the lesson page's title and first photo are on screen without scrolling`
- [auto] The lesson page opens for every role — `frontend/e2e/screens.spec.js::every screen opens as <role>` (the lesson route is in `screens()`)

On a real device (rows 56–58 of `docs/steps/device-checks.md`; Done left empty):

- [ ] **important** — On a **Samsung Galaxy** phone, as an engineer, add a lesson on the **TEST machine**
  (production) or any machine (dev server): the title and one line typed in **Tamil**, one line in English, a
  photo taken with the camera. Open it on an **iPhone** and a desktop browser: the Tamil letters show (no
  boxes), the line break is kept, the photo shows. **Retire the lesson when rows 57 and 58 are done.**
  (Row 56. Account: an engineer's login. Network: plant Wi-Fi. Where: either.)
- [ ] **important** — Print that lesson from a desktop browser on the plant's printer, on A4: the Tamil letters
  print correctly, the photo and the text fit one page, no menu or button prints. (Row 57. Where: production,
  TEST machine.)
- [ ] Scan the **TEST machine's** QR label with an operator's phone camera: its page opens with the *Lessons*
  card (row 56's lesson) in the first screenful. (Row 58. Account: an Operator test login at the TEST machine's
  unit, ask KLA. Network: mobile data. Where: production, TEST machine.)

## Tests

- **Frontend unit, while coding:** `tests/lessonLabels.test.js`: 6 passed. `npx vite build`: built, only the
  existing chunk-size warning.
- **New browser tests alone** (`E2E_LANES=1`, `phone-chromium`, `-g S077`): `lessons.spec.js` and
  `improvements.spec.js`: **12 passed**. The first runs failed 3 of the 11 (class lessons of other tests showed
  on the empty machine; D8) and then the "Last changed" text (a regular expression with `^` read the line
  break of the template); fixed in the tests, not in the screens.
- **Targeted, Normal** (`lessons`, `improvements`, `equipment`, `settings`, `screens`, `me` specs): **123 passed,
  2 skipped** (1.8 min).
- **All unit suites, once** (`YANTRA_TEST_RUN=s077c1 tooling/run-tests.bat`): **backend 4051 passed, frontend
  368 passed, tooling 185 passed**, ALL SUITES: PASSED.
- **Whole browser suite at Normal, once** (due: `FormModal.vue` and the router are shared code; `tooling/run-e2e-tests.bat`,
  6 lanes): **313 passed, 15 skipped** (3.1 min), no failure. It covers FormModal's `closed` event for every other dialog.

## Feedback

- hindrance: a class lesson shows on every machine of its class, so the brief's "each test makes its own
  machines" does not isolate the lesson tests; three tests failed on another test's class lesson before the
  design of § 8.1 was changed (D8) (3 failed tests, 2 runs, about 4 min).
- idea: the brief could say which seed class has no class lesson, or `meterMachine` could take a class code, so a
  test of an empty list has a machine to use.
- hindrance: Playwright's `getByText` with a regular expression anchored at `^` did not match text that the
  template wraps over two lines (the "Last changed" line); no other test in the repo does this, so nothing
  warned (1 run, 1 min).
- waste: the heredoc rule (§ Shell) and the harness that rejected one quote-heavy heredoc cost one repeat; the
  Write tool plus a script file worked at once (1 call).

## Fix rounds

### Round 1

Findings of `4-code-review-r1.md`: 5 minor, 4 nits. All fixed.

- **CR1-01 Fixed.** `LessonView.vue` keeps a `photoFailed` map (as `DocumentsCards`' `thumbFailed`). A failed photo fetch sets it,
  and the figure shows "The photo could not be loaded. Reload the page." in place of the spinner. A reload clears the entry and
  tries again; `revokePhotos` clears the map. New test `S077: a lesson photo that cannot be loaded shows a short line to reload`
  (the file route answers 503). Fails without the fix: `element(s) not found` for the line (the spinner stays); passes with it.
- **CR1-02 Fixed.** § 5's last bullet is corrected above. The reviewer's WebKit run: `screens.spec.js --project=phone-webkit`,
  9 passed (1.8 min). My Round 1 run of it: see § Tests below.
- **CR1-03 Fixed.** New test `S077: a photo the server refuses leaves the lesson saved; Close opens the lesson` (`bad.jpg`
  with a non-image buffer, `allowFailedRequest("/api/procedures/", 400)`; asserts the text, no submit button, then *Close*, then the
  URL `/equipment/lessons/<id>` and the heading). Fails without the fix (I changed `@closed="onClosed"` in `LessonDialog.vue` to
  an empty handler): `expect(page).toHaveURL(/\/equipment\/lessons\/\d+$/)` timed out; passes with it restored.
- **CR1-04 Fixed.** `support/lessons.js` has `retireLessonByApi(lesson)`; the class-lesson test ends with it. A side effect, found
  by the targeted run: a retired class lesson shows under *Retired lessons* of every HP machine for a writer, so the retire test's
  button name `Retired lessons (1)` failed in its lane. It now matches `/^Retired lessons \(\d+\)$/` and still finds its own row by
  serial. D8's rule stands: no test counts rows on an HP machine, and now a retired class lesson only adds to a count.
- **CR1-05 Fixed.** New `frontend/src/utils/download.js` with `downloadBlobUrl(url, fileName)` (the anchor, `download` name, click,
  remove). `DocumentsCards.downloadPdf` and `LessonView.downloadDocument` call it; each keeps its own blob cache and revoke.
  Behaviour-neutral; the equipment and screens specs pass.
- **CR1-06 Fixed.** `usePhotoUploads.js` header now says the previews are freed at the next open and on unmount, not at close,
  so the fade shows no broken image.
- **CR1-07 Fixed.** *Retired lessons (n)* has `tap-target`.
- **CR1-08 Fixed.** *Retry* on the lesson page has `tap-target`.
- **CR1-09 Fixed.** The card's empty text is "No lessons in use." (no test or doc names the old text apart from the brief and reviews).

### Tests (Round 1)

- Unit: `tooling/run-frontend-tests.bat`: 368 passed. `npx vite build`: built, only the chunk-size warning. No backend file changed.
- New tests alone (`E2E_LANES=1`, `phone-chromium`): 3 passed (the two new and the class test).
- Targeted, Normal: `lessons`, `equipment`, `screens` specs: **85 passed, 2 skipped** (1.6 min) after the retire-test fix; the run
  before it had that one failure.
- WebKit (`e2e/support/` changed): `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`: **9 passed** (1.4 min), WebKit in Docker.

### Docs updated (Round 1)

none, because the round changes no behaviour a doc describes beyond one empty-card word and a failure line; `docs/Plan.MD` § 6 does not quote either.

### Feedback (Round 1)

- hindrance: retiring a class lesson in one test changed the *Retired lessons* count in another test of the same lane; D8's "never count rows" rule had covered the card's rows but not the retired button's count (1 failed run, 2 min).
- idea: `retireLessonByApi`-style clean-up helpers are easy to forget; a fixture that retires the lessons a test writes would keep every lesson test isolated.

### Round 2 (orchestrator, 30-10-2026)

- **CR2-01 (nit), fixed** in `frontend/e2e/lessons.spec.js`: the class-lesson test retires its lesson in a `finally`, so a failed run leaves no class lesson on the lane's HP machines. Test-only change, made by the orchestrator.
- **Run:** `tooling/run-e2e-tests.bat e2e/lessons.spec.js`: 15 passed.
