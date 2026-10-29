```
Step: S077 — One-point lessons: screens
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066–S070, S071 (being coded); S072–S075 coded before S077
Status: Approved 30-10-2026 by KLA (delegated: R05 gate R, "start coding unless a defining question")
From: R05.6 (second half; backend in S075)
```

# S077 — One-point lessons: screens

## 1. What will be built

S075 (`docs/steps/S075-one-point-lessons/1-brief.md`) builds the one-point lesson's record, rules,
API and photos. **This step builds the screens on S075 § 6, as written there** (§ 9, *The split*):

1. **A *Lessons* card on the equipment page** (every node): the machine's own lessons and its
   class's, each with its first photo, its title in large text and a badge when it is for the
   whole class. Tap a lesson to open it. `"Add lesson"` for engineers and managers of the site.
   Retired lessons under `"Retired lessons (n)"` for writers. The card stands before *Open
   tickets*, so the operator who scans the press's QR label sees it first.
2. **The lesson page** (`/equipment/lessons/<id>`, mock-up `docs/roadmap/R05-mockups/06-lesson.html`):
   the machine and the class it is for, the serial, date and writer, the title, the photos with
   their captions, and the text in large type for a phone; "From improvement IM-…" when the reader
   may open it; `"Print lesson"` for a sheet at the machine (TPM practice: the lesson is posted where
   it is used). Writers change it, add, retitle and remove photos, and retire or bring it back.
3. **The dialog *Add lesson* / *Change lesson***: title, the lesson text, the tick `"Show on every
   machine of class <class>"`, and, when adding, the photos (uploaded after the save, S071's
   `usePhotoUploads`).
4. **On the countermeasure** (S071's row): a *Lesson* countermeasure shows its lesson
   ("Lesson OPL-007 · Keep the panel door shut", a link), or `"Write lesson"` when the user may write
   it; the dialog then opens seeded from the countermeasure (S075 § 5.3). The owner still marks it
   done (S075 D8).
5. **Settings › Removed documents**: a lesson's removed photo shows as "Lesson OPL-007" with its
   machine and unit; restore and purge as for every owner.

**After S075 and S077:** the press operators at SSVT.SHOP scan HP005's label and read "Keep the
panel door shut" with the photo of the dusty contactor, in Tamil and English.

### Out of scope

- The record, rules and API (S075). *Shown to* and *Record who was shown* in mock-up 06 (R05.7,
  deferred): the page shows neither.
- A plant-wide lesson list (S075 D6); a lesson on a PM template or a ticket; the kiosk.
- Tamil labels: the app's labels stay English, the lesson's content may be Tamil (Plan § 4.3a).

## 2. Standards and practice

S075 § 2 holds the standards; this step shows them:
- **TPM — one-point lesson.** In plain words: one point, mostly a picture, taught at the machine.
  The page puts the photos and the title first, in large type; print gives the sheet posted at the
  machine.
- **TPM — yokoten.** In plain words: spread what was learned to the similar machines. The badge
  "Every Hydraulic press" says on the card that the lesson comes from the class.
- **ISO 9001 § 7.1.6** (organisational knowledge) and **§ 7.5.3** (control). In plain words: the
  knowledge is available where it is needed; an obsolete document is kept and marked. The card is on
  the machine's page; a retired lesson shows a "Retired" banner, never vanishes for its writers.
- **WCAG 2.2 SC 2.5.5** (target size, as S064 cites it). In plain words: controls large enough for
  a thumb. Buttons are `tap-target` (44 px, `frontend/src/assets/main.css:142`), as on the floor
  screens.

## 3. Where

S077 is coded after S075 (and S071, whose files it extends). Files marked **(S071)** are new in
S071; the facts run shows them as missing until S071 lands.

### Frontend

- `frontend/src/views/EquipmentDetailView.vue`: the `LessonsCard` after the *Raise ticket* button
  and the edit buttons, **before** the *Open tickets* card (`frontend/src/views/EquipmentDetailView.vue:260`),
  with `order-0`, so it comes first on every width (§ 5.1); on `saved` it pushes to the new lesson's
  page (BR1-04); its docstring, and the S064 UX-07 comment (`EquipmentDetailView.vue:233-234`): on a
  phone the order is now Lessons, Open tickets, Documents and Photos, then the long cards. Documents
  stays `order-1`, before Details `order-2`, so the S064 test (`frontend/e2e/equipment.spec.js:946-954`)
  still holds.
- `frontend/src/views/equipment/LessonsCard.vue` (new): the card (§ 5.1). Loads
  `GET /api/procedures?equipment_id=` itself, as `MetersCard.vue` loads the node's meters.
- `frontend/src/views/LessonView.vue` (new): the lesson page (§ 5.2).
- `frontend/src/views/equipment/LessonDialog.vue` (new): *Add lesson* / *Change lesson*, one
  `useFormModal` for the form and its errors, with its own `save()` (S071 § 5.5's sequence; § 5.3).
  It emits `saved(lesson)` from FormModal's `closed` and navigates nowhere; the caller decides
  (§ 5.3). It reads the machine itself when it needs the class name (§ 5.3).
- `frontend/src/components/FormModal.vue` (**shared code**, § Step workflow *Shared code*): one line,
  `emit("closed")` in its `hidden.bs.modal` listener (`FormModal.vue:121-123`), and
  `defineEmits(["save", "closed"])`. Every other caller ignores the event; the whole browser suite at
  Normal (§ 8.1, *Runs*) covers it.
- `frontend/src/router/index.js`: the route `/equipment/lessons/:id(\\d+)`, name `lesson`, meta title
  `"Lesson"`, after `equipment-detail` (`frontend/src/router/index.js:32`). The path starts with
  `/equipment/`, so the *Equipment* nav item stays lit; not a nav item, so the API's 404 is the gate
  (as S068's improvement page).
- `frontend/src/utils/lessonLabels.js` (new): `lessonTargetText(lesson)` ("HP003 — Hydraulic press
  3 · for every Hydraulic press"; "For every Hydraulic press" when `machine` is null; "HP003 —
  Hydraulic press 3" without the class), `classBadgeText(cls)` ("Every Hydraulic press"),
  `lessonDate(created_at)` (the date part, `formatDateTime(created_at).slice(0, 10)`, DD-MM-YYYY;
  `frontend/src/utils/datetime.js` exports only `formatDateTime`), `LESSON_TITLE_MAX` 80,
  `LESSON_BODY_MAX` 1000 (S075 § 5.2).
- `frontend/src/components/CountermeasureItem.vue` **(S071)**: the lesson line and `"Write lesson"`
  (§ 5.4); emits `write-lesson`.
- `frontend/src/views/ImprovementDetailView.vue` **(S068, S071)**: holds the `LessonDialog`, opens it
  on `write-lesson`, and on `saved` reloads the improvement and stays on the page (BR1-04).
- `frontend/src/views/settings/RemovedDocuments.vue`: the lesson row (§ 5.5).

### Tests

- `frontend/tests/lessonLabels.test.js` (new): § 8.2.
- `frontend/e2e/lessons.spec.js` (new): the S077 tests (§ 8.1).
- `frontend/e2e/support/lessons.js` (new): `writeLessonByApi(machineId, {title, body, forClass,
  actionId})` as an engineer, and `addLessonPhotoByApi`, on the pattern of
  `frontend/e2e/support/improvements.js` (`startImprovementByApi`); `lessonMachines(testInfo, tag)`:
  two calls of `meterMachine(testInfo, tag, { unit: "SMTW.MCC2" })` (`frontend/e2e/support/meters.js:10`),
  two machines of class `HP` in the operator's unit (`tooling/e2e/seed_e2e.py:38`).
- `frontend/e2e/improvements.spec.js` (new in S068): the countermeasure's lesson test (§ 8.1).
- `frontend/e2e/screens.spec.js`: the lesson page joins `screens()` (`frontend/e2e/screens.spec.js:38`)
  for every role (§ 8.1).
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/settings.spec.js`, `frontend/e2e/me.spec.js`: run
  again (§ 8.3). The removed-documents row's test is in `lessons.spec.js` (§ 8.1).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 6 *Screens*: the *Lessons* card on the equipment page, the lesson page, print,
  *Write lesson* on a countermeasure.
- `.claude/CLAUDE.md` § SMTW-Review: the spec map gains `lessons` S075/S077; `improvements` reads
  S077 too; `equipment` and `screens` read S077.
- `docs/steps/device-checks.md`: the rows of § 8.4.

**File count:** 15 code and test files (10 code, 5 tests new or changed; 3 more specs run again),
3 docs.

## 4. Data model

None (S075 § 4).

## 5. Rules

### 5.1 The card *Lessons* (`LessonsCard.vue`)

- **When it shows:** when `items` is not empty, or `can_add`, or `retired` is not empty. A reader
  of a machine with no lessons sees no card (no empty box on the floor). A writer (`can_add`) on a
  machine with no lessons sees the card with the line "No lessons yet." and `"Add lesson"`.
- **Header:** "Lessons", with "(n)" from `total` (S075 § 6.2 caps `items` at 200) when `total` > 0;
  `"Add lesson"` (`btn btn-sm btn-primary tap-target`) when `can_add`.
- **One row per lesson** (a `router-link` to `/equipment/lessons/<id>`, the whole row tappable,
  `list-group-item-action`): the cover photo (`cover`: `…/documents/<doc_id>/thumb` when
  `has_thumb`, else `/file`, the rule of `DocumentsCards.vue:106`; fetched through `apiGetBlob`, 64 px
  square, `object-fit: cover`; a grey `fa-solid fa-chalkboard-user` icon when `cover` is null); the
  title (`fs-5`, `overflow-wrap: anywhere`); under it the serial (`small text-secondary`) and, when
  `for_class`, the badge `classBadgeText` (`badge text-bg-info`).
- **Retired:** `"Retired lessons (n)"` (`btn btn-link`) when `retired` is not empty; a tap shows those
  rows, each with a `"Retired"` badge (`text-bg-secondary`).
- **Thumbnails** are object URLs, revoked on reload and on unmount (DocumentsCards' rule,
  `frontend/src/components/documents/DocumentsCards.vue` header). The card reloads when `node.id`
  changes (Vue Router reuses the page), as `MetersCard.vue:63` watches it.
- **Add lesson** opens `LessonDialog` with the node and its class (§ 5.3); on `saved` the equipment
  page pushes to `/equipment/lessons/<id>`: the writer sees the lesson as the operator will.
- **Errors:** a failed load shows "Lessons could not be loaded: <message>" in the card (as the open
  tickets card), and the rest of the page works.
- **Place:** after the *Raise ticket* button and the edit buttons, before *Open tickets*,
  `order-0 mb-3`. A press with three open tickets would otherwise push the lesson below the fold
  after a QR scan (BR1-05); the raise flow has its own "Already reported" check, so an operator about
  to raise a ticket loses nothing. An `@device` test checks it with open tickets on the machine
  (§ 8.1).

### 5.2 The lesson page (`LessonView.vue`)

Top to bottom, one column, `max-width` 720 px centred on a wide screen:

1. **The target line** (`lessonTargetText`), a link to the machine when `machine` is set.
2. **A banner** "Retired — this lesson is no longer shown on the machine's page." (`alert
   alert-secondary`) when `active` is false.
3. **The card:** "One-point lesson" (`small text-uppercase text-secondary`); "OPL-007 · 30-10-2026
   · Engineer A" (`lessonDate(created_at)`, `created_by_name`); the **title** as `h2` (`fs-3`); then
   each **photo** of `documents` with kind `photo`, in their order, full card width (`img-fluid`,
   `max-height: 60vh`), its title under it as the caption (`small`); then the **text**
   (`fs-5`, `white-space: pre-line`, `overflow-wrap: anywhere`). Documents of kind `document` follow
   as download links (the same blob path as DocumentsCards).
4. **"From improvement IM-2026-10-001 · HP003 will not start"** (a link to
   `/tickets/improvements/<id>`) when `source`.
5. **"Last changed 31-10-2026 10:12 by Engineer A"** (`small text-secondary`) when `updated_at`.
6. **Buttons** (`no-print`, `tap-target`, full width on a phone): `"Print lesson"`
   (`btn-outline-secondary`, every reader); when `can_edit`: `"Change lesson"` (`btn-primary`),
   `"Edit photos"` (toggles `DocumentsCards` with `base-path` `/api/procedures/<id>/documents` and
   `can-edit`, below the buttons; a change reloads the page's copy through its `changed` event, S071
   BR1-07), and `"Retire lesson"` / `"Bring back lesson"` (`btn-outline-danger` / `btn-outline-success`).
   *Edit photos* shows both of DocumentsCards' cards, *Photos* and *Documents*: a lesson may carry a
   PDF (S075 § 5.8), so the *Documents* card is wanted. DocumentsCards lists newest first, the page
   oldest first (S075 § 6.3, BR1-12 there); the page's order is the lesson's.
- **Retire asks first:** the question **replaces the button row** (as `MetersCard.vue:136-173`):
  "Retire OPL-007? It leaves the machine's page. You can bring it back." with `"Retire lesson"`
  (`btn-danger`) and `"Keep it"`; only one `"Retire lesson"` button is ever on screen. Bringing back
  needs no question.
- **Photos** are fetched as blobs (`/api/procedures/<id>/documents/<doc>/file`) and shown through
  object URLs, revoked on unmount and on reload. The full file, not the thumbnail (400 px,
  `THUMB_BOX`, `backend/documents_core.py:37`): the lesson is read from the picture. The cost is an
  assumption (§ 9).
- **Print** (`window.print()`): `main.css`'s print rules hide the chrome (`.no-print`,
  `frontend/src/assets/main.css:152`); the page's own print rule keeps the card on one A4 page where
  it fits (`img { max-height: 40vh }` in print) and drops the link styling. Tamil glyphs on paper
  are a device check (§ 8.4).
- **Not found** (404, a lesson outside the reader's units): "Lesson not found, or not at your
  units." with `"Back to the list"` to `/equipment` (the improvement page's form,
  `ImprovementDetailView.vue:147`). A 503 shows the server's text, "Yantra can't reach its database.
  Try again in a few minutes." (`DB_LOST_TEXT`, `backend/api_common.py:79`).

### 5.3 The dialog *Add lesson* / *Change lesson* (`LessonDialog.vue`)

`useFormModal({ path: "/api/procedures", blank, fromRecord, toBody, label: (lesson) =>
lesson.serial })` (`frontend/src/composables/useFormModal.js:20`; a lesson has no `code`, the default
label's field) for the form, `error`, `fieldError`, `modalError`, `dirty` and `markClean`. The dialog
does **not** use `send()`, which closes the modal before `afterSave` runs (`useFormModal.js:74-77`):
it writes its own `save()`, S071 § 5.5's sequence.

- **`blank(seed = {})`** (it is called with no seed when the composable is created,
  `useFormModal.js:22`) returns `{title: seed.title ?? "", body: seed.body ?? "", for_class: false}`.
  **`equipment_id` and `action_id` stay out of the form** (BR1-03): `openCreate(seed)` keeps the seed
  in a ref (`seed.machine?.id`, `seed.action_id ?? null`) and `toBody` adds both to the `POST`. So a
  refusal on either field is not a form key, and `modalError` shows it at the top (S026: a refusal
  is always in view). The seed comes from the card (`{machine: {id, code, name, class: {id, code,
  name}}}`, the node and its class) or from the countermeasure (§ 5.4: the improvement's machine;
  `body` the countermeasure's text; `action_id`). **Only when creating** (`editingId.value ===
  null`) does `toBody` add `equipment_id` and `action_id`; a change (`PUT`) sends title, body and
  `for_class` only, so a lesson written from a countermeasure is never sent `action_id: null`, which
  S075 § 5.3 refuses with 409 (BR2-03).
- **`fromRecord(lesson)`** fills title, body, `for_class`; a change sends a `PUT` with only those.
- **Fields:** `"Title"` (input, `maxlength` 80, a counter "12 / 80"); `"Lesson text"` (textarea, 5
  rows, `maxlength` 1000, a counter; help "One point: what to do and why. Write in Tamil, English or
  both."); `"Show on every machine of class Hydraulic press"` (checkbox; the class name from the
  seed or the lesson, else read by the dialog, below; shown when adding, and when changing only if
  `can_change_class`; help "The
  lesson then shows on every machine of this class, at every site."). Each renders
  `fieldError(name)`; `equipment_id` and `action_id` refusals show at the top (`modalError`).
- **The class name** (BR2-02): when the tick will show and neither `seed.machine.class` nor
  `lesson.class` gives the name (a machine lesson's detail has `class: null`, S075 § 6.3; the
  improvement's `machine` has no class, § 5.4), the dialog reads `GET /api/equipment/<machine id>`
  on open (`class_id`, `class_code`; the name through `ensureEquipmentClasses`, as
  `EquipmentDetailView.vue:117-120`). A failed read keeps the label "Show on every machine of this
  machine's class". The equipment page passes the class it has, so no read there.
- **Photos, when adding only:** `"Add photos"` (a `label` over a hidden file input, `accept`
  `ACCEPT.photo`, `multiple`, no `capture`, so the phone offers camera and gallery, as S071 § 5.5)
  through `usePhotoUploads` (new in S071, its § 5.6) with `previews: true`; its `path` is a ref, set
  after the `POST` to `/api/procedures/<new id>/documents`. Its `maxMb` is `upload_max_mb` of
  `GET /api/equipment/<machine id>/documents`, read on open (one setting for every owner), so an
  oversized photo is marked "Larger than 10 MB" before the save. FormModal gets
  `:dirty="!closePhase && (dirty || files.length > 0)"` (as `MarkDoneDialog.vue:128`), so a ✕ with
  only photos chosen asks "Discard your changes?" and the close-only *Close* does not.
- **`save()`, in order** (S071 § 5.5, word for word in its shape):
  1. `saving` true; `apiPost("/api/procedures", toBody(form))` (or `apiPut` on a change).
  2. A refusal: `error` is set (beside the field, or at the top), `saving` false; no photo is sent.
  3. Success: keep the answer in a `savedLesson` ref; `markClean()` (`useFormModal.js:35`), so a
     close asks nothing; set the uploads' `path`;
     `uploadAll()` with `saving` still true, so the ✕ and the buttons stay blocked while photos go.
  4. Every photo uploaded (or none chosen): `modal.close()`.
  5. A photo failed: a `closeOnly` phase in FormModal with "Lesson saved. A photo was not saved. Add
     it again, or close.", each failed photo with its reason, `IPHONE_PHOTO_HINT` when the server
     refused a HEIC file (as `DocumentUploadModal.vue:122`), and `"Add photos"` again; photos chosen
     in this phase upload at once under `saving`. `"Close"` (FormModal's `data-bs-dismiss`) closes.
  6. **On FormModal's `closed`** (BR2-01): when `savedLesson` is set, emit `saved(savedLesson)` and
     clear it. One path for step 4 (after the fade) and step 5 (*Close*); a *Cancel* before a save
     emits nothing.
  A change (`PUT`) has no photos: steps 1–4 and 6.
- **The caller acts on `saved`** (BR1-04): the equipment page pushes to the lesson page (§ 5.1); the
  improvement page reloads the improvement and stays (§ 5.4); the lesson page replaces its copy.
- **Buttons:** `"Save lesson"` and `"Cancel"`; closing with typed input asks (FormModal's `dirty`).
- **The common case in one path:** on the machine's page tap *Add lesson*, type the title and the
  text, pick two photos, *Save lesson*.

### 5.4 On the countermeasure (`CountermeasureItem.vue`, S071 § 5.2)

For an entry with kind `lesson` (detail shape only; `mine` items have no `lesson`):
- **Line under the text:** when `lesson`: "Lesson OPL-007 · Keep the panel door shut" (a
  `router-link` to the lesson; " (retired)" when `lesson.active` is false).
- **Button:** `"Write lesson"` (`btn btn-outline-primary tap-target`) when `can_write_lesson`. The
  component makes no call (S071 BR2-04): it emits `write-lesson`; `ImprovementDetailView` opens
  `LessonDialog` with `{machine: improvement.machine, body: action.text,
  action_id: action.id}`; on `saved` it reloads the improvement and **stays**: the engineer is working
  the improvement, and the new line "Lesson OPL-007 · …" is the link to the lesson.
  The improvement's `machine` carries no class (S067 § 6: `{id, code, name}`, pinned by
  `backend/tests/test_improvements_api.py:120`); the dialog reads it on open (§ 5.3, *The class
  name*).
- *Mark done* stays as S071 built it.

### 5.5 Settings › Removed documents

A row with `owner` `"procedure"`: "Lesson <serial>" (`item.name`), then the machine's code
(`item.code`, S075 § 5.8) and `item.unit` in `small text-secondary`. Restore and purge as for every
owner; no state refusal (S075 § 5.8: no state rule). The search placeholder adds "lesson number".

### 5.6 Words for the floor

Short words a low-literacy or Tamil-speaking user follows: "Lessons", "Add lesson", "Lesson text",
"Show on every machine of class …", "Print lesson", "Retired". No "OPL" without the word "Lesson"
before it, except the serial itself. The lesson's own text is the writer's (Tamil or English).

### 5.7 The database down

Every call shows the server's 503 text (`DB_LOST_TEXT`) where the card or page shows its load
error; the dialog
shows the refusal at the top (`modalError`).

## 6. API

S075 § 6, unchanged.

## 7. Design decisions

- **D1. The card loads its own data** (`GET /api/procedures?equipment_id=`), as `MetersCard.vue`.
  The equipment detail stays as it is, and its tests too. Rejected: lessons inside
  `GET /api/equipment/<id>` (a change to equipment.py's detail and its tests for one card).
- **D2. The card comes before *Open tickets*,** right after the *Raise ticket* button, on every
  width. An operator who scans the QR wants what to do, not the serial number, and a press often has
  open tickets (Plant-Facts § 4). Rejected: after *Open tickets* (below the fold on a busy press);
  after *Documents* (further down); capping the card to three lessons (a state for little gain).
- **D3. A page of its own for a lesson, not a dialog.** It is printed, linked from a countermeasure
  and opened from a QR scan; a page has a URL. Rejected: a dialog on the equipment page (no link,
  no print).
- **D4. Photos are picked in the *Add lesson* dialog and uploaded after the save, inside the
  open dialog** (S071's `usePhotoUploads` and *Mark done*'s `save()`): one flow for the common case,
  and a failed photo is seen. Changes to photos later go through
  the existing `DocumentsCards` under *Edit photos*. Rejected: photos only after the save on the
  page (two flows for one lesson); a new photo editor (DocumentsCards already retitles and removes).
- **D5. Print through the browser** with the app's print rules, no PDF. Rejected: a PDF route (a
  new dependency and a font question on the server).
- **D6. Retired lessons stay reachable for writers** under a link on the card (ISO 9001 § 7.5.3:
  obsolete kept and marked). Rejected: no retired list (a retired lesson could not be brought back
  from the screen).
- **D7. After *Save lesson* the equipment page opens the lesson; the improvement page stays.**
  The dialog navigates nowhere and each caller decides. Rejected: both callers open the lesson page
  (pulls the engineer out of the improvement after each lesson).

## 8. Tests and acceptance

### 8.1 Automated (e2e, targeted: `lessons.spec.js`, `improvements.spec.js`, `screens.spec.js`)

Each test makes its own machines with `lessonMachines` (two machines of class `HP` in
`SMTW.MCC2`, the operator's unit, BR1-10) and its lessons by API (`support/lessons.js`), so no seed
machine gains a lesson and no other spec's page changes. Every flow test calls `expectDialogFits` on
each dialog it opens (the S024 convention); untagged unless stated.

- `S077: an engineer adds a lesson with a photo on a machine; the card and the page show it` — on
  `/equipment/<id>`, *Add lesson*, title, text with a line break, one photo (the e2e fixture
  image), *Save lesson*: the lesson page opens and shows the serial `OPL-…`, the title, the photo,
  the text with its two lines (the end state only, no timing); back on the machine, the card's row
  shows the title and the thumbnail.
- `S077: a lesson for the class shows on another machine of the class with its badge` — by API on
  machine A with `for_class`; machine B's card shows the row and "Every <class>".
- `S077: an operator reads a lesson and sees no Add, Change or Edit photos` — asserts the text and
  that `"Add lesson"`, `"Change lesson"`, `"Edit photos"` and `"Retire lesson"` are absent; `"Print
  lesson"` is present.
- `S077: an operator sees no Lessons card on a machine with no lessons`.
- `S077: an engineer changes the title and unticks the class; the other machine no longer lists it` —
  on a lesson written from a *Lesson* countermeasure (by API, linked), so a `PUT` that sent
  `action_id` would fail the test (BR2-03); the class name shows in the tick of *Change lesson* on a
  machine lesson (BR2-02).
- `S077: retire asks first, the card leaves the lesson, Retired lessons brings it back` — the
  question replaces the buttons (one `"Retire lesson"` button on screen), *Retire lesson*, the row
  gone for an operator, the writer's `"Retired lessons (1)"`, *Bring back lesson*.
- `S077: the server's refusal of an empty lesson text shows beside the field` — a text of spaces
  only (the `maxlength` stops a long one), *Save lesson*: "Enter the lesson text" under
  `"Lesson text"` (`expectFieldMessage`); the test calls `consoleWatch.allowFailedRequest(
  "/api/procedures", 400)` (`frontend/e2e/support/console.js:43`), as `equipment.spec.js:46`.
- `S077: a removed lesson photo is listed in Settings and restored` — the engineer removes the photo
  under *Edit photos*; the manager opens Settings › Removed documents and sees "Lesson OPL-…" with the
  machine's code and unit, *Restore*; the lesson page shows the photo again (BR1-09).
- `S077: a Tamil title and text are shown as typed` — by API with a Tamil title and body; the page
  shows them unchanged (the browser test checks the characters, not the glyphs: § 8.4).
- In `improvements.spec.js`: `S077: Write lesson on a Lesson countermeasure opens the dialog seeded,
  and the countermeasure then links its lesson` — the text seeded from the countermeasure, *Save
  lesson*: the page stays on the improvement (BR1-04), the line "Lesson OPL-…" links the lesson
  page; `"Write lesson"` is gone; *Mark done* is still there.
- `S077: on a phone the Lessons card is in view after opening the machine by its QR link, with open
  tickets on it` (`@device`: a geometry check; a lesson written by API on the machine and three
  open tickets raised by API on it, then
  `/e/<code>` as the operator, the card's top inside the viewport on `phone-chromium`; on
  `desktop-chromium` too, at Normal).
- `S077: the lesson page's title and first photo are on screen without scrolling` (`@device`).
- In `screens.spec.js`: `{ path: "/equipment/lessons/<id>", title: "Lesson", shows: the title heading,
  who: EVERYONE }`, the lesson made in the file's `beforeAll` on a machine the file makes in
  `SMTW.MCC2` (`meterMachine`), not on `seed.extruder`, so the extruder pages of other specs gain no
  card (the storekeeper reads lessons: `equipment:read`).

**Runs:** targeted (Normal with spec files) `tooling/run-e2e-tests.bat e2e/lessons.spec.js
e2e/improvements.spec.js e2e/equipment.spec.js e2e/settings.spec.js e2e/screens.spec.js`. The router
and `FormModal.vue` are shared code (§ Step workflow, *Shared code*), so the coder runs the whole
suite at Normal once at the end, as every step does; it covers FormModal's new `closed` event for
every other dialog.

### 8.2 Unit (`frontend/tests/lessonLabels.test.js`)

`lessonTargetText` (machine and class; class only, `machine` null; machine only), `classBadgeText`.

### 8.3 Existing tests that run again, and locators

- `frontend/e2e/equipment.spec.js`: the new card adds a heading "Lessons" and a button `"Add lesson"`
  for engineers. Its tests read `"Add equipment"`, `"Add part"`, documents and lifecycle controls by
  their names (`frontend/e2e/equipment.spec.js:39-115`); none reads a bare Add, so none is
  expected to change (to verify in the run).
- `frontend/e2e/settings.spec.js`: it checks only that the Removed documents card is there
  (`frontend/e2e/settings.spec.js:66-69`); no change. The lesson row's test is § 8.1's.
- `frontend/e2e/equipment.spec.js:946-954` (S064: Documents before Details on a phone): Documents stays
  `order-1` and Details `order-2`; the Lessons card is `order-0` before Open tickets, so the test
  holds.
- `frontend/e2e/me.spec.js` (S071): `mine` items have no `lesson`; the row is unchanged.
- `frontend/e2e/screens.spec.js`: one more screen per role.

### 8.4 On a real device (rows for `docs/steps/device-checks.md`)

- [ ] **important** — On a **Samsung Galaxy** phone, as an engineer, add a lesson on the **TEST
  machine** (production) or any machine (dev server), with the title and one line typed in **Tamil**
  with the phone keyboard, one line in English, and a photo taken with the camera. Open it on an
  **iPhone** and on a desktop browser: the Tamil letters show correctly (no boxes), the line break is
  kept, the photo shows. **Retire the lesson when checks 2 and 3 are done.** Account: an engineer's
  login. Network: plant Wi-Fi. Where: either (the dev server on KLA's laptop, or production on the
  TEST machine). Never on a real press: its operators would see it at once, and a lesson cannot be
  deleted (S075 D11).
- [ ] **important** — Print that lesson from a desktop browser on the plant's printer, on A4: the
  Tamil letters print correctly, the photo and the text fit one page, no menu or button prints.
  Account: any login. Network: plant Wi-Fi. Where: production on the TEST machine.
- [ ] Scan the **TEST machine's** QR label with an operator's phone camera: its page opens with the
  *Lessons* card (check 1's lesson) in the first screenful. Account: a test login with the Operator
  role at the TEST machine's unit (ask KLA). Network: mobile data. Where: production on the TEST
  machine.

### 8.5 Acceptance

- All unit suites green; the targeted runs green; the whole suite at Normal green once at the end.
- On the dev server: OPL-001 on HP003 for every hydraulic press, written from IM-2026-10-001's
  *Lesson* countermeasure, shows on HP005's page to an operator and prints on one page.
- The device checks of § 8.4 done or skipped by KLA.

## 9. Open questions and assumptions

- **The split:** S075 § 9. This step is the screens on S075 § 6 (15 code and test files). Coded after
  S075 and S071.
- **Assumption:** the dialog reads the machine once for its class name when its seed or the lesson
  has none (§ 5.3), rather than widening S067's `machine` object (a test pins its key set) or S075
  § 6.3's `class`.
- **Staleness check due before coding.** The brief was approved while S071 was being coded, and
  S072–S075 land first. Before S077 is coded, a staleness review (`2-brief-review-s1.md`) checks
  S071's `CountermeasureItem.vue`, `usePhotoUploads`, `MarkDoneDialog.vue` and `FormModal.vue`, and
  S075's API, against the code then.
- **Assumption:** no bound on photos (S075 § 9); the page shows all, in order.
- **Assumption (BR1-07):** the page downloads each photo at full size (3–8 MB from a phone camera,
  up to `upload_max_mb`): a few lessons, read mostly on plant Wi-Fi. A medium size (about 1200 px)
  is a documents-store change for every owner, left to the Procedures roadmap; the 400 px thumbnail
  is too small to read a dusty contactor from.
- **Assumption:** Tamil glyphs come from the phone's and the printer's system fonts; Yantra loads no
  Tamil web font. The device checks of § 8.4 confirm it.
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status), § 1 (item 1), § 3 (frontend, tests), § 5.1, § 5.2, § 5.3, § 5.4,
§ 5.7, § 7 (D2, D4, new D7), § 8.1, § 8.3, § 8.4, § 9.

| Finding | Answer |
|---|---|
| BR1-01 major | Accepted (a): the dialog writes its own `save()` in S071 § 5.5's sequence: `POST`, `markClean()`, `uploadAll()` under `saving`, a `closeOnly` phase on a failed photo ("Lesson saved. A photo was not saved. Add it again, or close."), then close and emit `saved`; `usePhotoUploads`' `path` is the ref set after the `POST`; FormModal's `dirty` counts chosen photos. § 3, § 5.3, D4, § 8.1. |
| BR1-02 minor | Accepted: `blank(seed = {})` with optional chaining; no machine read from it. § 5.3. |
| BR1-03 minor | Accepted (a): `equipment_id` and `action_id` stay out of the form, in a seed ref; `toBody` adds them; their refusals show at the top through `modalError`. § 5.3. |
| BR1-04 minor | Accepted (a): the dialog emits `saved(lesson)` and navigates nowhere; the equipment page pushes to the lesson page; *Write lesson* from the improvement page reloads the improvement and stays. § 3, § 5.1, § 5.3, § 5.4, new D7, § 8.1. |
| BR1-05 minor | Accepted (a): *Lessons* comes after *Raise ticket* and before *Open tickets*; the `@device` test raises three open tickets first. § 1, § 3, § 5.1, D2, § 8.1. |
| BR1-06 minor | Accepted: check 1 on the TEST machine (production) or any machine (dev server), the lesson retired after checks 2 and 3; check 3 scans the TEST machine's label with an operator login at its unit. § 8.4. |
| BR1-07 minor | Accepted (a): full-size photos kept; the cost recorded as an assumption, a medium size left to the Procedures roadmap. § 5.2, § 9. |
| BR1-08 minor | Accepted: the retire question replaces the button row, as `MetersCard`; one `"Retire lesson"` button on screen. § 5.2, § 8.1. |
| BR1-09 minor | Accepted: a test of the removed lesson photo in Settings, restored; § 8.3's line on `settings.spec.js` corrected. § 3, § 8.1, § 8.3. |
| BR1-10 minor | Accepted: `lessonMachines` (two `meterMachine` calls in `SMTW.MCC2`, class `HP`) for every test; `screens.spec.js` writes its lesson on a machine it makes, not on `seed.extruder`. § 3, § 8.1. |
| BR1-11…BR1-20 nits | Accepted: BR1-11 the 503 text is the server's `DB_LOST_TEXT` (§ 5.2, § 5.7); BR1-12 the cover's `/thumb` or `/file` rule (§ 5.1); BR1-13 the count from `total`, no "(0)" (§ 5.1); BR1-14 the card reloads on `node.id` (§ 5.1); BR1-15 the S064 UX-07 comment and test (§ 3, § 8.3); BR1-16 `label: (lesson) => lesson.serial` (§ 5.3); BR1-17 the not-found text (§ 5.2); BR1-18 `allowFailedRequest` (§ 8.1); BR1-19 the *Documents* card under *Edit photos* is wanted (§ 5.2); BR1-20 `lessonDate` in `lessonLabels.js` (§ 3, § 5.2). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 3 (frontend: `LessonDialog.vue`, `FormModal.vue`),
§ 5.1, § 5.3, § 5.4, § 8.1, § 9.

| Finding | Answer |
|---|---|
| BR2-01 minor | Accepted (a): `FormModal` emits `closed` from its `hidden.bs.modal` listener (one line, shared code, named in § 3 and § 8.1 *Runs*; the whole suite at Normal covers it); the dialog keeps the answer in `savedLesson` and emits `saved(lesson)` from `@closed`, one path for step 4 and the close-only *Close*. § 3, § 5.3, § 8.1. |
| BR2-02 minor | Accepted (a): the dialog reads the machine on open when it shows the tick and has no class name; § 5.4's page-side read moves into it. § 3, § 5.3, § 5.4, § 8.1, § 9. |
| BR2-03 minor | Accepted: `toBody` adds `equipment_id` and `action_id` only when creating; the change test runs on a lesson linked to a countermeasure. § 5.3, § 8.1. |
| BR2-04…BR2-08 nits | Accepted: BR2-04 `:dirty="!closePhase && (dirty \|\| files.length > 0)"` (§ 5.3); BR2-05 `maxMb` from `upload_max_mb` of the machine's documents list, read on open (§ 5.3); BR2-06 "No lessons yet." for a writer (§ 5.1); BR2-07 test 1 asserts the end state only (§ 8.1); BR2-08 the `@device` card test writes a lesson by API first (§ 8.1). |
