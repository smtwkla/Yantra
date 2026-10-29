```
Step: S077 — One-point lessons: screens
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066–S069 (gate B), S070 (being coded); S071–S075 approved or in review, coded before S077
Status: In review
From: R05.6 (second half; backend in S075)
```

# S077 — One-point lessons: screens

## 1. What will be built

S075 (`docs/steps/S075-one-point-lessons/1-brief.md`) builds the one-point lesson's record, rules,
API and photos. **This step builds the screens on S075 § 6, as written there** (§ 9, *The split*):

1. **A *Lessons* card on the equipment page** (every node): the machine's own lessons and its
   class's, each with its first photo, its title in large text and a badge when it is for the
   whole class. Tap a lesson to open it. `"Add lesson"` for engineers and managers of the site.
   Retired lessons under `"Retired lessons (n)"` for writers. The card stands high on the page, so
   the operator who scans the press's QR label sees it first.
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

- `frontend/src/views/EquipmentDetailView.vue`: the `LessonsCard` after the *Open tickets* card, with
  `order-0` (`frontend/src/views/EquipmentDetailView.vue:260`, the card order of S029), so it comes
  before *Details* on every width (§ 5.1); its docstring.
- `frontend/src/views/equipment/LessonsCard.vue` (new): the card (§ 5.1). Loads
  `GET /api/procedures?equipment_id=` itself, as `MetersCard.vue` loads the node's meters.
- `frontend/src/views/LessonView.vue` (new): the lesson page (§ 5.2).
- `frontend/src/views/equipment/LessonDialog.vue` (new): *Add lesson* / *Change lesson*, one
  `useFormModal` (§ 5.3).
- `frontend/src/router/index.js`: the route `/equipment/lessons/:id(\\d+)`, name `lesson`, meta title
  `"Lesson"`, after `equipment-detail` (`frontend/src/router/index.js:32`). The path starts with
  `/equipment/`, so the *Equipment* nav item stays lit; not a nav item, so the API's 404 is the gate
  (as S068's improvement page).
- `frontend/src/utils/lessonLabels.js` (new): `lessonTargetText(lesson)` ("HP003 — Hydraulic press
  3 · for every Hydraulic press"; "For every Hydraulic press" when `machine` is null; "HP003 —
  Hydraulic press 3" without the class), `classBadgeText(cls)` ("Every Hydraulic press"),
  `LESSON_TITLE_MAX` 80, `LESSON_BODY_MAX` 1000 (S075 § 5.2).
- `frontend/src/components/CountermeasureItem.vue` **(S071)**: the lesson line and `"Write lesson"`
  (§ 5.4); emits `write-lesson`.
- `frontend/src/views/ImprovementDetailView.vue` **(S068, S071)**: holds the `LessonDialog`, opens it
  on `write-lesson`, reloads the improvement after the save.
- `frontend/src/views/settings/RemovedDocuments.vue`: the lesson row (§ 5.5).

### Tests

- `frontend/tests/lessonLabels.test.js` (new): § 8.2.
- `frontend/e2e/lessons.spec.js` (new): the S077 tests (§ 8.1).
- `frontend/e2e/support/lessons.js` (new): `writeLessonByApi(machineId, {title, body, forClass,
  actionId})` as an engineer, and `addLessonPhotoByApi`, on the pattern of
  `frontend/e2e/support/improvements.js` (`startImprovementByApi`).
- `frontend/e2e/improvements.spec.js` (new in S068): the countermeasure's lesson test (§ 8.1).
- `frontend/e2e/screens.spec.js`: the lesson page joins `screens()` (`frontend/e2e/screens.spec.js:38`)
  for every role (§ 8.1).
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/settings.spec.js`, `frontend/e2e/me.spec.js`: run
  again (§ 8.3).

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
  of a machine with no lessons sees no card (no empty box on the floor).
- **Header:** "Lessons" with the count of `items`; `"Add lesson"` (`btn btn-sm btn-primary
  tap-target`) when `can_add`.
- **One row per lesson** (a `router-link` to `/equipment/lessons/<id>`, the whole row tappable,
  `list-group-item-action`): the cover photo (`cover`, the thumbnail through `apiGetBlob`, 64 px
  square, `object-fit: cover`; a grey `fa-solid fa-chalkboard-user` icon when `cover` is null); the
  title (`fs-5`, `overflow-wrap: anywhere`); under it the serial (`small text-secondary`) and, when
  `for_class`, the badge `classBadgeText` (`badge text-bg-info`).
- **Retired:** `"Retired lessons (n)"` (`btn btn-link`) when `retired` is not empty; a tap shows those
  rows, each with a `"Retired"` badge (`text-bg-secondary`).
- **Thumbnails** are object URLs, revoked on reload and on unmount (DocumentsCards' rule,
  `frontend/src/components/documents/DocumentsCards.vue` header).
- **Errors:** a failed load shows "Lessons could not be loaded: <message>" in the card (as the open
  tickets card), and the rest of the page works.
- **Place:** after *Open tickets*, `order-0 mb-3`: on a phone before *Details*, so a QR scan opens
  the page with the lessons in the first screenful (an `@device` test, § 8.1).

### 5.2 The lesson page (`LessonView.vue`)

Top to bottom, one column, `max-width` 720 px centred on a wide screen:

1. **The target line** (`lessonTargetText`), a link to the machine when `machine` is set.
2. **A banner** "Retired — this lesson is no longer shown on the machine's page." (`alert
   alert-secondary`) when `active` is false.
3. **The card:** "One-point lesson" (`small text-uppercase text-secondary`); "OPL-007 · 30-10-2026
   · Engineer A" (`formatDateTime` date part, `created_by_name`); the **title** as `h2` (`fs-3`); then
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
- **Retire asks first,** inline under the button: "Retire OPL-007? It leaves the machine's page. You
  can bring it back." with `"Retire lesson"` and `"Keep it"`. Bringing back needs no question.
- **Photos** are fetched as blobs (`/api/procedures/<id>/documents/<doc>/file`) and shown through
  object URLs, revoked on unmount and on reload. The full file, not the thumbnail: the lesson is read
  from the picture.
- **Print** (`window.print()`): `main.css`'s print rules hide the chrome (`.no-print`,
  `frontend/src/assets/main.css:152`); the page's own print rule keeps the card on one A4 page where
  it fits (`img { max-height: 40vh }` in print) and drops the link styling. Tamil glyphs on paper
  are a device check (§ 8.4).
- **Not found** (404, a lesson outside the reader's units): the app's not-found text as on the
  improvement page; a 503: "Yantra cannot reach its database. Try again in a minute." (the app's
  `api.js` message).

### 5.3 The dialog *Add lesson* / *Change lesson* (`LessonDialog.vue`)

`useFormModal({ path: "/api/procedures", blank, fromRecord, afterSave, toBody })`
(`frontend/src/composables/useFormModal.js:20`):

- **`blank(seed)`** returns `{equipment_id: seed.machine.id, title: seed.title ?? "", body:
  seed.body ?? "", for_class: false, action_id: seed.action_id ?? null}`. `openCreate(seed)` is called
  with `{machine: {id, code, name, class: {id, code, name}}}` from the card (the node and its class)
  or from the countermeasure (§ 5.4: the improvement's machine; `body` the countermeasure's text;
  `action_id`).
- **`fromRecord(lesson)`** fills title, body, `for_class`; `openEdit` sends a `PUT` with only those.
- **Fields:** `"Title"` (input, `maxlength` 80, a counter "12 / 80"); `"Lesson text"` (textarea, 5
  rows, `maxlength` 1000, a counter; help "One point: what to do and why. Write in Tamil, English or
  both."); `"Show on every machine of class Hydraulic press"` (checkbox; the class name from the
  seed or the lesson; shown when adding, and when changing only if `can_change_class`; help "The
  lesson then shows on every machine of this class, at every site."). Each renders
  `fieldError(name)`; `equipment_id` and `action_id` refusals show at the top (`modalError`).
- **Photos, when adding only:** `"Add photos"` (file input, `accept="image/*"`, `multiple`,
  `capture` not set so the phone offers camera and gallery) through `usePhotoUploads` (new in S071, its § 5.6) with
  `previews: true`; the list shows each with its state. After the `POST` answers 201, `afterSave`
  sets `path` to `/api/procedures/<new id>/documents` and calls `uploadAll()`; then the page opens
  the new lesson (`router.push`). A failed photo shows its row "failed" and the lesson is kept: the
  writer adds it again from *Edit photos*.
- **Buttons:** `"Save lesson"` and `"Cancel"`; closing with typed input asks (FormModal's `dirty`).
- **The common case in one path:** on the machine's page tap *Add lesson*, type the title and the
  text, pick two photos, *Save lesson*.

### 5.4 On the countermeasure (`CountermeasureItem.vue`, S071 § 5.2)

For an entry with kind `lesson` (detail shape only; `mine` items have no `lesson`):
- **Line under the text:** when `lesson`: "Lesson OPL-007 · Keep the panel door shut" (a
  `router-link` to the lesson; " (retired)" when `lesson.active` is false).
- **Button:** `"Write lesson"` (`btn btn-outline-primary tap-target`) when `can_write_lesson`. The
  component makes no call (S071 BR2-04): it emits `write-lesson`; `ImprovementDetailView` opens
  `LessonDialog` with `{machine: improvement.machine (with its class), body: action.text,
  action_id: action.id}` and, after the save, reloads the improvement (the lesson line then shows).
  The improvement's `machine` carries no class (S067 § 6: `{id, code, name}`, pinned by
  `backend/tests/test_improvements_api.py:120`), so the page first reads the machine
  (`GET /api/equipment/<id>`: `class_code`, and the class name from `ensureEquipmentClasses`, as the
  equipment page does) and then opens the dialog. A failed read opens the dialog with the tick label
  "Show on every machine of this machine's class".
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

Every call shows the app's 503 message where the card or page shows its load error; the dialog
shows the refusal at the top (`modalError`).

## 6. API

S075 § 6, unchanged.

## 7. Design decisions

- **D1. The card loads its own data** (`GET /api/procedures?equipment_id=`), as `MetersCard.vue`.
  The equipment detail stays as it is, and its tests too. Rejected: lessons inside
  `GET /api/equipment/<id>` (a change to equipment.py's detail and its tests for one card).
- **D2. The card comes right after *Open tickets*,** before *Details*, on every width. An operator
  who scans the QR wants what to do, not the serial number. Rejected: after *Documents* (below the
  fold on a phone).
- **D3. A page of its own for a lesson, not a dialog.** It is printed, linked from a countermeasure
  and opened from a QR scan; a page has a URL. Rejected: a dialog on the equipment page (no link,
  no print).
- **D4. Photos are picked in the *Add lesson* dialog and uploaded after the save** (S071's
  `usePhotoUploads`, as *Mark done*): one flow for the common case. Changes to photos later go through
  the existing `DocumentsCards` under *Edit photos*. Rejected: photos only after the save on the
  page (two flows for one lesson); a new photo editor (DocumentsCards already retitles and removes).
- **D5. Print through the browser** with the app's print rules, no PDF. Rejected: a PDF route (a
  new dependency and a font question on the server).
- **D6. Retired lessons stay reachable for writers** under a link on the card (ISO 9001 § 7.5.3:
  obsolete kept and marked). Rejected: no retired list (a retired lesson could not be brought back
  from the screen).

## 8. Tests and acceptance

### 8.1 Automated (e2e, targeted: `lessons.spec.js`, `improvements.spec.js`, `screens.spec.js`)

Each test makes its lessons by API (`support/lessons.js`) on the seed's machines. Every flow test
calls `expectDialogFits` on each dialog it opens (the S024 convention); untagged unless stated.

- `S077: an engineer adds a lesson with a photo on a machine; the card and the page show it` — on
  `/equipment/<id>`, *Add lesson*, title, text with a line break, one photo (the e2e fixture
  image), *Save lesson*: the lesson page shows the serial `OPL-…`, the title, the photo, the text with
  its two lines; back on the machine, the card's row shows the title and the thumbnail.
- `S077: a lesson for the class shows on another machine of the class with its badge` — by API on
  machine A with `for_class`; machine B's card shows the row and "Every <class>".
- `S077: an operator reads a lesson and sees no Add, Change or Edit photos` — asserts the text and
  that `"Add lesson"`, `"Change lesson"`, `"Edit photos"` and `"Retire lesson"` are absent; `"Print
  lesson"` is present.
- `S077: an operator sees no Lessons card on a machine with no lessons`.
- `S077: an engineer changes the title and unticks the class; the other machine no longer lists it`.
- `S077: retire asks first, the card leaves the lesson, Retired lessons brings it back` — the
  inline question, the row gone for an operator, the writer's `"Retired lessons (1)"`, *Bring back
  lesson*.
- `S077: the server's refusal of an empty lesson text shows beside the field` — a text of spaces
  only (the `maxlength` stops a long one), *Save lesson*: "Enter the lesson text" under
  `"Lesson text"` (`expectFieldMessage`).
- `S077: a Tamil title and text are shown as typed` — by API with a Tamil title and body; the page
  shows them unchanged (the browser test checks the characters, not the glyphs: § 8.4).
- In `improvements.spec.js`: `S077: Write lesson on a Lesson countermeasure opens the dialog seeded,
  and the countermeasure then links its lesson` — the text seeded from the countermeasure, *Save
  lesson*, back on the improvement the line "Lesson OPL-…" links the page; `"Write lesson"` is gone;
  *Mark done* is still there.
- `S077: on a phone the Lessons card is in view after opening the machine by its QR link` (`@device`:
  a geometry check, `/e/<code>`, the card's top inside the viewport on `phone-chromium`; on
  `desktop-chromium` too, at Normal).
- `S077: the lesson page's title and first photo are on screen without scrolling` (`@device`).
- In `screens.spec.js`: `{ path: "/equipment/lessons/<id>", title: "Lesson", shows: the title heading,
  who: EVERYONE }`, the lesson made in the file's `beforeAll` on `seed.extruder` (the storekeeper reads
  lessons: `equipment:read`).

**Runs:** targeted (Normal with spec files) `tooling/run-e2e-tests.bat e2e/lessons.spec.js
e2e/improvements.spec.js e2e/equipment.spec.js e2e/settings.spec.js e2e/screens.spec.js`. The router
is shared code (§ Step workflow, *Shared code*), so the coder runs the whole suite at Normal once at
the end, as every step does.

### 8.2 Unit (`frontend/tests/lessonLabels.test.js`)

`lessonTargetText` (machine and class; class only, `machine` null; machine only), `classBadgeText`.

### 8.3 Existing tests that run again, and locators

- `frontend/e2e/equipment.spec.js`: the new card adds a heading "Lessons" and a button `"Add lesson"`
  for engineers. Its tests read `"Add equipment"`, `"Add part"`, documents and lifecycle controls by
  their names (`frontend/e2e/equipment.spec.js:39-115`); none reads a bare Add, so none is
  expected to change (to verify in the run).
- `frontend/e2e/settings.spec.js`: the removed-documents tests make their own rows; a lesson row
  appears only for lessons the run made. No change expected.
- `frontend/e2e/me.spec.js` (S071): `mine` items have no `lesson`; the row is unchanged.
- `frontend/e2e/screens.spec.js`: one more screen per role.

### 8.4 On a real device (rows for `docs/steps/device-checks.md`)

- [ ] **important** — On a **Samsung Galaxy** phone, as an engineer, add a lesson on a press with
  the title and one line typed in **Tamil** with the phone keyboard, one line in English, and a photo
  taken with the camera. Open it on an **iPhone** and on a desktop browser: the Tamil letters show
  correctly (no boxes), the line break is kept, the photo shows. Account: an engineer's login.
  Network: plant Wi-Fi. Where: either (the dev server on KLA's laptop, or production on the TEST
  machine).
- [ ] **important** — Print that lesson from a desktop browser on the plant's printer, on A4: the
  Tamil letters print correctly, the photo and the text fit one page, no menu or button prints.
  Account: any login. Network: plant Wi-Fi. Where: production on the TEST machine.
- [ ] Scan the press's QR label with an operator's phone camera: the machine's page opens with the
  *Lessons* card in the first screenful. Account: an operator's login at the unit. Network: mobile
  data. Where: production on the TEST machine.

### 8.5 Acceptance

- All unit suites green; the targeted runs green; the whole suite at Normal green once at the end.
- On the dev server: OPL-001 on HP003 for every hydraulic press, written from IM-2026-10-001's
  *Lesson* countermeasure, shows on HP005's page to an operator and prints on one page.
- The device checks of § 8.4 done or skipped by KLA.

## 9. Open questions and assumptions

- **The split:** S075 § 9. This step is the screens on S075 § 6 (15 code and test files). Coded after
  S075 and S071.
- **Assumption:** *Write lesson* reads the machine once for its class name (§ 5.4) rather than
  widening S067's `machine` object, whose key set a test pins.
- **Assumption:** no bound on photos (S075 § 9); the page shows all, in order.
- **Assumption:** Tamil glyphs come from the phone's and the printer's system fonts; Yantra loads no
  Tamil web font. The device checks of § 8.4 confirm it.
- **No defining question.**

## 10. Amendments

None.

## Review log

None yet.
