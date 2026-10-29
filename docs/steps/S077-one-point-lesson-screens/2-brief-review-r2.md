```
Step: S077 — One-point lessons: screens
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069, S070, S071 (being coded; in the
tree now: `CountermeasureItem.vue`, `MarkDoneDialog.vue`, `usePhotoUploads.js`). S075 is not in
the tree: its names were checked against `docs/steps/S075-one-point-lessons/1-brief.md` § 5–6 as
answered in its round 1 (`lesson_source`, `can_write_lesson` from the machine's current unit and
site, the (6d) row lock).

# S077 — Brief review, round 2

**Verdict: no `blocker` or `major` is open.** Three `minor` findings and five nits, all in the
rewritten § 5.3 and § 8.1; none needs KLA's decision, none is defining. Every round-1 finding
marked `Accepted` is in the brief's text (checked one by one, § 1 to § 9). Full track; the facts
file `scratch/brief-facts-S077.md` read first (it predates S071's files landing: it lists
`CountermeasureItem.vue` as missing and `usePhotoUploads` as found; both are in the tree now).

**Re-read this round** (the diff `scratch/S077-brief-r1.md` → the brief): § 1 item 1; § 3; § 5.1;
§ 5.2 (the retire question, the photos, not found); § 5.3 whole; § 5.4; § 5.7; D2, D4, D7; § 8.1;
§ 8.3; § 8.4; § 9. Against the code: `useFormModal.js`, `FormModal.vue`, `usePhotoUploads.js`,
`MarkDoneDialog.vue` (S071's `save()` as coded), `CountermeasureItem.vue`,
`EquipmentDetailView.vue:233-290, 357-378`, `MetersCard.vue:55-70, 130-175`, `datetime.js`,
`documentTypes.js`, `DocumentUploadModal.vue:110-130`, `DocumentsCards.vue:106`,
`ImprovementDetailView.vue:147`, `api_common.py:79`, `config_rbac.py:99`, the router, `meters.js`,
`seed_e2e.py:38-58`, `console.js:43`, `equipment.spec.js:46, 946-954`, `settings.spec.js:66-69`,
`device-checks.md` § Where. Not re-read: § 2, § 5.5, § 5.6, D1, D3, D5, D6, § 8.2, § 8.5.

## Findings

### BR2-01 — minor — § 5.3 step 5: the close-only `"Close"` cannot emit `saved`

**Problem.** Step 5 says: in the `closeOnly` phase `"Close"` closes **and emits `saved(lesson)`**;
the callers act only on `saved` (D7: the equipment page pushes to the lesson page). FormModal's
close-only footer is one `data-bs-dismiss` button (`FormModal.vue:185-187`) and FormModal emits
nothing when the modal hides (`:121-123` only clears `visible`; its one emit is `save`). So after
a failed photo the writer presses *Close* and stays on the equipment page: no lesson page, and on
the improvement page no reload, so the new "Lesson OPL-…" line is missing until a reload. S071's
`MarkDoneDialog.vue:97` avoids this by emitting `saved` right after the `POST`, which S077 cannot
do: the equipment page would push to the lesson page and unmount the dialog while the photos go
(BR1-01's problem).

**Why it matters.** The failed-photo path is the one D4 was changed for ("a failed photo is
seen"); as written it ends in a dead end the browser test of § 8.1 does not cover (no test fails a
photo).

**Options.**
- (a) **Recommended.** `FormModal` emits `closed` from its `hidden.bs.modal` listener
  (`FormModal.vue:121-123`, one line; `defineEmits(["save", "closed"])`). The dialog keeps the
  saved lesson in a ref at step 3 and emits `saved(lesson)` from `@closed` when that ref is set:
  one path for step 4 (`modal.close()` fires it after the fade) and step 5 (*Close*). Name
  `FormModal.vue` in § 3 as shared code; the whole-suite run the brief already plans covers it
  (§ Step workflow, *Shared code*).
- (b) The dialog listens for the hidden event itself. It has no handle on FormModal's element
  (`modal` is the component ref), so this needs an `expose` of the element: more than (a).
- (c) Emit `saved` at step 3 as S071 does, and let the equipment page push at once. Rejected by
  BR1-01: the push unmounts the dialog mid-upload.

### BR2-02 — minor — § 5.3: *Change lesson* on a machine lesson has no class name for the tick

**Problem.** The tick reads "Show on every machine of class Hydraulic press", "the class name from
the seed or the lesson". On *Change* the dialog is opened from the lesson page with `openEdit(lesson)`,
and S075 § 6.3's detail gives `class: {…} | null` — **null for a machine lesson** (§ 5.1: `class_id`
NULL when unticked) — and `machine: {id, code, name}` without a class. A writer at the site
(`can_change_class` true) who opens *Change lesson* on a machine lesson sees a tick with no class
name, and the common case of ticking a lesson for the class after the fact is exactly this one.
§ 5.4 solves the same gap for *Write lesson* with a read of `GET /api/equipment/<id>`, but only on
the improvement page.

**Options.**
- (a) **Recommended.** The dialog resolves the class itself: on open, when it will show the tick
  and has no class (no `seed.machine.class`, no `lesson.class`), it reads
  `GET /api/equipment/<machine id>` (`class_id`, `class_code`; the name through
  `ensureEquipmentClasses`, as `EquipmentDetailView.vue:117-120`), with § 5.4's fallback label
  "Show on every machine of this machine's class" on a failed read. § 5.4's page-side read moves
  into the dialog (one copy; `ActionDialog` loads its owner list the same way), and § 9's
  assumption says so. The equipment page still passes the class it has, so no read there.
- (b) The lesson page reads the machine before `openEdit`: a second copy of § 5.4's read.
- (c) Widen S075 § 6.3: `class` always the machine's class and `for_class` the tick. S075 is
  approved; this is an amendment there for one label.

### BR2-03 — minor — § 5.3: `toBody` sends `action_id: null` on a `PUT`, a 409 for a linked lesson

**Problem.** "`openCreate(seed)` keeps the seed in a ref and `toBody` adds both [`equipment_id`,
`action_id`] to the `POST`." `useFormModal.save()` is not used, but the dialog's own `save()` calls
`toBody(form)` for the `PUT` too (step 1: "or `apiPut` on a change"). On the lesson page nothing
calls `openCreate`, so the seed ref is empty and `toBody` adds `action_id: null`. S075 § 5.3:
"a different id or `null` when one is stored → 409 'A lesson keeps the countermeasure it was
written for'". Every title change of a lesson written from a countermeasure (§ 8.5's own
acceptance case) is refused; `equipment_id` is ignored on a `PUT`, so only `action_id` bites.

**Fix.** Add the two only when creating: `toBody` reads `editingId.value === null` (or `openEdit`
clears the seed ref and `toBody` skips `undefined`). One sentence in § 5.3; the "changes the title"
test of § 8.1 should run on the countermeasure's lesson, so the run catches a regression.

## Nits

- **BR2-04** (nit) § 5.3: `:dirty="dirty || files.length > 0"` makes the close-only *Close* ask
  "Discard your changes?" (`FormModal.vue:61-64`: `dirty` is read on every hide; the done and
  failed rows are still in `files`). Write it as `MarkDoneDialog.vue:128` does:
  `!closePhase && (dirty || files.length > 0)`.
- **BR2-05** (nit) § 5.3: say where `usePhotoUploads`' `maxMb` comes from for a new lesson; no
  documents list exists before the `POST` (S071 loads it from the countermeasure's list,
  `MarkDoneDialog.vue:52-58`). Recommended: `upload_max_mb` of `GET /api/equipment/<machine
  id>/documents` on open (one setting for every owner), so an oversized photo is marked "Larger
  than 10 MB" before the save instead of landing in the close-only phase; else `null` and say so.
- **BR2-06** (nit) § 5.1: the card shows for `can_add` with no lessons; give the writer's empty
  line, e.g. "No lessons yet." (scope B: one line, what the user sees).
- **BR2-07** (nit) § 8.1, test 1: "the dialog stays open while the photo uploads" is a timing
  assertion on the 1-file fixture (`frontend/e2e/fixtures/test-photo.jpg`, uploaded in
  milliseconds on a lane): flaky either way. Assert the end state only: the lesson page with the
  serial, title, photo and text.
- **BR2-08** (nit) § 8.1, the `@device` card test: say it writes a lesson by API on the machine
  first. An operator on a machine with no lessons sees no card (§ 5.1), so the test as described
  has nothing to find.

## Checked and found consistent

- **Round 1 answers in the text:** BR1-01 (§ 5.3's `save()` sequence, D4), BR1-02 (`blank(seed =
  {})`), BR1-03 (the seed ref, `modalError`), BR1-04 (`saved`, D7, § 3, § 5.1, § 5.4, § 8.1),
  BR1-05 (§ 1, § 3, § 5.1, D2, the `@device` test with three tickets), BR1-06 (§ 8.4: the TEST
  machine, retire after, the operator login), BR1-07 (§ 5.2, § 9), BR1-08 (§ 5.2, § 8.1), BR1-09
  (§ 8.1's removed-photo test, § 8.3 corrected), BR1-10 (`lessonMachines`, `screens.spec.js`'s own
  machine), and the ten nits BR1-11…BR1-20, each where the Review log says.
- **S075 as it now stands:** § 5.4 uses `can_write_lesson` as S075 § 5.7 defines it (the machine's
  current unit in the user's units, the key at its site), so the page's `GET /api/equipment/<id>`
  before the dialog cannot 404; § 5.2's "From improvement …" line reads `source.improvement`
  (`{id, serial, title}`, S075 § 5.9); `cover {doc_id, has_thumb}`, `total`, `retired`, `can_add`,
  `can_edit`, `can_change_class`, `documents` oldest first, `created_by_name`, `updated_at`: S075
  § 6.2–6.4 unchanged by its round 1. The (6d) lock touches no screen.
- **`usePhotoUploads` as coded** (`usePhotoUploads.js:25`): `path` is read with `toValue` at each
  upload, so a ref set after the `POST` works; `previews: true`, `files` rows with `state` and
  `message`, `uploadAll()` one file at a time, `revokeAll()` on unmount — as § 5.3 relies on.
- **`useFormModal` as coded:** `blank()` is called with no argument at set-up (`:22`); `openCreate(seed)`
  passes the seed (`:59`); `modalError` shows a refusal whose field is not a form key (`:52-54`);
  `markClean` (`:35`); `label` is used only for `editingLabel` (`:66`), so `lesson.serial` is right.
- **The card's place:** the page's column is `d-flex flex-column` (`EquipmentDetailView.vue:235`);
  *Raise ticket*, the edit buttons and *Open tickets* are `order-0`, Documents `order-1 order-md-0`
  (`:378`), Details' row `order-2 order-md-0` (`:287`). A card between the edit buttons and *Open
  tickets* with `order-0` is first on every width; the S064 test (`equipment.spec.js:946-954`)
  compares only the Documents and Details headers by `^\s*Documents` / `^\s*Details`, which a
  "Lessons" header does not match.
- **`lessonDate`:** `formatDateTime` returns "DD-MM-YYYY HH:MM" (`datetime.js:11-18`), so
  `.slice(0, 10)` is the date.
- **The retire question** replaces the row as `MetersCard.vue:163-170` does (`confirmingId`); one
  `"Retire lesson"` button on screen for the test's locator.
- **Tests' set-up:** `meterMachine(testInfo, tag, { unit })` makes a machine of class `HP`
  (`meters.js:10-27`); the operator's unit is `SMTW.MCC2` (`seed_e2e.py:38`); `raiseByApi`
  (`support/tickets.js:27`) raises the three tickets; `/e/:code` is `router/index.js:39`; the
  manager holds `equipment:purge_documents` at every SMTW unit (`config_rbac.py:99`,
  `seed_e2e.py:44`) and opens Settings in `settings.spec.js:66`; `allowFailedRequest` is
  `console.js:43`; `ACCEPT.photo` is `documentTypes.js:9`; `IPHONE_PHOTO_HINT` is shown as
  `DocumentUploadModal.vue:122` and `MarkDoneDialog.vue:166`.
- **UI text (scope B):** "Lesson saved. A photo was not saved. Add it again, or close." matches
  S071's wording; "Retire OPL-007? It leaves the machine's page. You can bring it back." names the
  consequence; "Lesson not found, or not at your units." / "Back to the list" is the improvement
  page's form (`ImprovementDetailView.vue:147-148`); the 503 text is `DB_LOST_TEXT`
  (`api_common.py:79`).
- **Device checks (§ 8.4):** the TEST machine, an account, a network and a where on each; "never
  on a real press" matches `device-checks.md:21`; check 2 (paper) and check 3 (a real QR scan) are
  kinds a browser cannot judge.
- **D7** is a judgement KLA made through the orchestrator's choices; the text says who navigates
  and who stays, and § 8.1's two flow tests assert it.

## Feedback

- idea: re-run `tooling/step-brief-facts.bat` before each round when the tree changed between
  rounds; this round's facts file still says `CountermeasureItem.vue` is missing while S071 had
  put it and `MarkDoneDialog.vue` in the tree, and reading S071's coded `save()` was the fastest
  check of § 5.3 (4 file reads to find it).
- hindrance: `git diff --no-index` of the two brief copies is 31 KB and went to a tool-result
  file; a `--stat`-style list of the changed sections from the Review log's "Sections changed"
  line would have been enough to start from (the diff was still needed for the wording).
