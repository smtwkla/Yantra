```
Step: S077 — One-point lessons: screens
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069, S070 (being coded). S071 and S075,
which this brief builds on, are approved or in review and not in the tree: their names
(`CountermeasureItem.vue`, `usePhotoUploads`, `/api/procedures`, the flags) were checked against
their briefs, not code.

# S077 — Brief review, round 1

**Verdict: one `major` is open (BR1-01, the photo upload after the save runs in a closed dialog);
no blocker.** Nine `minor` findings, two of them judgement calls for KLA (BR1-04, BR1-05, BR1-07);
none is defining. Full track; facts file `scratch/brief-facts-S077.md` read first. Background read:
S075 § 5–6, S071 § 5.2–5.6, R05.6 and gate R in `docs/roadmap/R05-rca.md`, mock-up 06,
Plant-Facts § 4, Plan § 4.3a and § 6, and the code the brief touches (the equipment page,
`MetersCard.vue`, `useFormModal.js`, `FormModal.vue`, `DocumentsCards.vue`, the router,
`RemovedDocuments.vue`, `ImprovementDetailView.vue`, `EquipmentByCodeView.vue`, `main.css`, the
specs and their support files).

## Findings

### BR1-01 — major — § 5.3: the photos upload after `useFormModal` has closed the dialog

**Problem.** § 5.3 says: after the `POST` answers 201, `afterSave` sets the upload path and calls
`uploadAll()`, then the page opens the new lesson; "a failed photo shows its row *failed*".
`useFormModal.finish()` closes the modal **before** it awaits `afterSave`
(`frontend/src/composables/useFormModal.js:74-77`). So the uploads run while the dialog is gone:
the writer sees no progress, a failed row is in a closed dialog, and `router.push` to the lesson
page happens while photos are still going (or after a failure nobody saw). "`afterSave` sets
`path`" is also ambiguous: `useFormModal`'s `path` is a fixed string; the one to set is
`usePhotoUploads`' `path` ref (S071 § 5.6).

**Why it matters.** The common case (§ 5.3's last line) is a title, a text and two photos from
the floor. A photo that fails on a slow link must be seen; "the writer adds it again from *Edit
photos*" needs the writer to know it failed. S071 met the same problem for *Mark done* and
settled it (S071 BR1-02, § 5.5): the dialog does not use `send()`.

**Options.**
- (a) **Recommended.** Follow S071 § 5.5's `save()` word for word: `saving` true; `apiPost`;
  a refusal shows as today; on success `markClean()`, then `uploadAll()` with `saving` still
  true (the ✕ and the buttons stay blocked); every photo done → close and emit `saved(lesson)`;
  a photo failed → the `closeOnly` phase with "Lesson saved. A photo was not saved. Add it again,
  or close.", the failed rows with their reasons, `IPHONE_PHOTO_HINT` on a refused HEIC, and
  `"Add photos"` again (uploads at once under `saving`). Pass `:dirty="dirty || files.length > 0"`
  to `FormModal` (S071 BR2-08). The caller acts on `saved` (BR1-04).
- (b) Keep `send()` and move the photo step to the lesson page (photos only after the save,
  through *Edit photos*). Rejected by D4 already: two flows for one lesson.

### BR1-02 — minor — § 5.3: `blank(seed)` is called with no seed at set-up

**Problem.** `useFormModal` calls `blank()` with no argument when the composable is created
(`useFormModal.js:22`). § 5.3's `blank(seed)` reads `seed.machine.id` and throws before the
dialog is ever opened. S071 § 5.3 records the contract: `blank(seed = {})` with optional chaining
(self-check item 13).

**Fix.** Write `blank(seed = {})` returning `{equipment_id: seed.machine?.id ?? null, title:
seed.title ?? "", body: seed.body ?? "", for_class: false, action_id: seed.action_id ?? null}`,
and say so in § 5.3.

### BR1-03 — minor — § 5.3: the `equipment_id` and `action_id` refusals would be invisible

**Problem.** § 5.3 says those refusals "show at the top (`modalError`)". `modalError` shows a
refusal only when its field is **not** a key of the form (`useFormModal.js:52-54`). `blank()`
puts `equipment_id` and `action_id` in the form, so a refusal such as S075's 400 "A lesson for
this countermeasure goes on HP003, the improvement's machine" (`equipment_id`) or 409 "This
countermeasure already has its lesson, OPL-007" (`action_id`) would be shown nowhere (S026: a
refusal is always in view).

**Options.**
- (a) **Recommended.** Keep both out of `form`: hold the seed in a ref and add `equipment_id` and
  `action_id` in `toBody`. Then `modalError` shows their refusals at the top, as the brief wants.
- (b) Keep them in the form and render `fieldError("equipment_id")` and `fieldError("action_id")`
  in an alert at the top of the body.

### BR1-04 — minor — § 5.3 / § 5.4 / § 8.1: where the writer lands after *Save lesson*

**Problem.** § 5.3 says the page opens the new lesson (`router.push`). § 5.4 says the
improvement page reloads the improvement after the save (the lesson line then shows). § 8.1's
countermeasure test says "back on the improvement", which implies a navigation away and back. The
coder would have to decide which caller does what.

**Options** (KLA's call; not defining).
- (a) **Recommended.** The dialog emits `saved(lesson)` and navigates nowhere. The equipment
  card's page pushes to `/equipment/lessons/<id>` (the writer wants to see the lesson as the
  operator will). The improvement page reloads the detail and stays: the engineer is working the
  improvement, and the new line "Lesson OPL-007 · …" is the link if they want to look.
- (b) Both callers push to the lesson page. One rule, but it pulls the engineer out of the
  improvement after each lesson.

Whichever is chosen, § 8.1's countermeasure test should say it.

### BR1-05 — minor — § 5.1, D2: the operator's first screenful depends on the open tickets

**Problem.** After a QR scan the operator's page shows, in order: the path line, the heading
with badges, the full-width red *Raise ticket* (operators hold `ticket:raise`), the *Open tickets*
card (operators hold `ticket:read`; it lists **every** open ticket of the machine,
`EquipmentDetailView.vue:260-285`), then *Lessons*. A press with three open tickets (Plant-Facts
§ 4: presses fail often, some problems take months) pushes the lesson below the fold on a phone.
The brief's `@device` test will pass on a machine with no tickets and say nothing about that
press.

**Options** (KLA's call; not defining).
- (a) **Recommended.** *Lessons* right after *Raise ticket* and before *Open tickets*. The
  lesson is why the card is high (D2: "what to do, not the serial number"); the raise flow has
  its own "Already reported" check, so the operator about to raise a ticket loses nothing.
- (b) Keep the order; accept that the lesson is in view only on a quiet machine.
- (c) Keep the order and cap the card: the first three lessons and "All lessons (n)". Adds a
  state for little gain: a machine has a few lessons.

### BR1-06 — minor — § 8.4: the device checks would write a test lesson on a real press

**Problem.** Check 1 says "add a lesson on a press … Where: either (… or production on the TEST
machine)", and check 3 "scan the press's QR label". On production, a lesson on a real press is
seen by its operators at once, and S075 has no delete: it can only be retired, and it keeps its
`OPL-` number for good. `docs/steps/device-checks.md` § Where says "Never use a real machine".

**Fix.** Check 1: "on the **TEST** machine (production) or any machine (dev server)"; add
"Retire the lesson when the checks are done". Check 3: "the TEST machine's QR label", account an
operator login that sees `SMTW.MCC2`. Check 2 prints that lesson, so it inherits the fix.

### BR1-07 — minor — § 5.2: the page downloads every photo at full size

**Problem.** The page fetches each photo's full file ("the lesson is read from the picture").
A phone camera's JPEG is 3–8 MB; the store allows 10 MB (`upload_max_mb`). A lesson with three
photos is 10–20 MB per open, on mobile data for an operator at a press (check 3 of § 8.4 is on
mobile data). The thumbnail is `THUMB_BOX` 400 × 400 (`backend/documents_core.py:37`), too small
to read a dusty contactor from.

**Options** (KLA's call; not defining).
- (a) **Recommended for now.** Keep the full file and write the cost down in § 9 as an
  assumption: a few lessons, read mostly on plant Wi-Fi; a medium size (about 1200 px) is a
  documents-store change for the Procedures roadmap, where every owner would gain it.
- (b) Show the 400 px thumbnail in the page and the full file on tap (the viewer). The lesson
  is then read from a small picture: against the point of an OPL.
- (c) Add a medium size to the store now. Out of this step's scope (S075 is the backend, and
  the store is shared by five owners).

### BR1-08 — minor — § 5.2: two `"Retire lesson"` buttons during the inline question

**Problem.** § 5.2 puts the question "Retire OPL-007? …" with `"Retire lesson"` and `"Keep it"`
under the button, so the trigger and the confirm are both on screen with the same name: two red
buttons for the user, and a strict-mode clash for `getByRole("button", { name: "Retire lesson"
})` in § 8.1's test. `MetersCard.vue:136-173` and `ImprovementDetailView.vue:213-227` replace the
row's buttons with the question.

**Fix.** The question replaces the button row (as MetersCard): `"Retire lesson"` (`btn-danger`)
and `"Keep it"` only while asking. Say it in § 5.2 and § 8.1.

### BR1-09 — minor — § 5.5, § 8.3: the removed-documents row has no test, and § 8.3 misreads `settings.spec.js`

**Problem.** § 8.3 says `settings.spec.js`'s removed-documents tests "make their own rows". The
file checks only that the card exists (`frontend/e2e/settings.spec.js:66-69`); the row flows are
S071's planned test in `improvements.spec.js` and the equipment tests. So § 5.5 is a screen change
with no automated check, and a lesson row drawn by the node branch (`RemovedDocuments.vue:191`,
a link to `/equipment/undefined`) would pass every test.

**Fix.** Add to § 8.1: the manager removes a lesson photo under *Edit photos*, opens
Settings › Removed documents, sees "Lesson OPL-…" with the machine's code and unit, restores it,
and the page shows the photo again. Correct § 8.3's line.

### BR1-10 — minor — § 8.1: which machines the tests use, and the shared extruder

**Problem.** The operator tests need a machine the operator can open (`SMTW.MCC2` only,
`tooling/e2e/seed_e2e.py:38`); `equipment.spec.js`'s `createEquipment` makes machines in
`SMTW.MCC1` (`:256-269`), which the operator cannot see (404). The class test needs two machines
of one class; the seed has none (extruder, compressor, mill and pump are four classes). And the
lesson `screens.spec.js` adds to `seed.extruder` in `beforeAll` shows on every other spec's
extruder page for the run (`journeys.spec.js`, `equipment.spec.js`, `tickets-raise.spec.js`): a
card no earlier test expects, and one more request per page open.

**Fix.** Name the helper in `support/lessons.js`: two calls of `meterMachine(testInfo, tag, {
unit: "SMTW.MCC2" })` (`frontend/e2e/support/meters.js:10`) give two machines of class `HP` in the
operator's unit; use them for the class, operator and `@device` tests. For `screens.spec.js`,
either accept the card on the extruder (and say the earlier specs were checked in the run) or
write the lesson on a machine the file makes.

## Nits

- **BR1-11** (nit) § 5.2, § 5.7: the 503 text is the server's, not `api.js`'s, and reads
  "Yantra can't reach its database. Try again in a few minutes." (`backend/api_common.py:79`,
  `DB_LOST_TEXT`). Quote it so, or just say "the app's 503 text".
- **BR1-12** (nit) § 5.1: the cover's URL is `…/documents/<doc_id>/thumb` when `has_thumb`, else
  `/file` (the rule of `DocumentsCards.vue:106`); say it.
- **BR1-13** (nit) § 5.1: the header count is `total`, not `items.length` (S075 § 6.2 caps
  `items` at 200); no "(0)" for a writer on a machine with no lessons.
- **BR1-14** (nit) § 5.1: the card reloads when `node.id` changes (Vue Router reuses the page;
  the watch of `MetersCard.vue:63`), revoking its thumbnails.
- **BR1-15** (nit) § 3: `EquipmentDetailView.vue:233-234`'s comment (S064 UX-07: Documents right
  after Open tickets on a phone) needs the Lessons card added; the S064 test
  `equipment.spec.js:946-954` still holds (Documents `order-1` stays before Details `order-2`).
- **BR1-16** (nit) § 5.3: pass `label: (lesson) => lesson.serial` to `useFormModal`; its default
  reads `record.code`, which a lesson has not.
- **BR1-17** (nit) § 5.2: write the not-found text: "Lesson not found, or not at your units." with
  "Back to the list" to `/equipment` (the improvement page's form, `ImprovementDetailView.vue:147`).
- **BR1-18** (nit) § 8.1: the refusal test needs `consoleWatch.allowFailedRequest("/api/procedures",
  400)` (`frontend/e2e/support/console.js:43`), as `equipment.spec.js:46`.
- **BR1-19** (nit) § 5.2: `DocumentsCards` under *Edit photos* also draws its *Documents* card
  (kind `document` is allowed, S075 § 5.8); say that it is wanted, so the coder does not hide it.
- **BR1-20** (nit) § 5.2: `datetime.js` exports only `formatDateTime`; say how the date part is
  taken (`formatDateTime(created_at).slice(0, 10)`), or add `formatDate` to `lessonLabels.js`.

## Checked and found consistent

- Every field, flag and route the screens use exists in S075 § 6 as written: `items`, `retired`,
  `total`, `can_add`, the item's `cover {doc_id, has_thumb}`, `for_class`, `class`, `own`; the
  detail's `machine | null`, `created_by_name`, `updated_at`, `updated_by_name`, `source`,
  `documents` oldest first, `can_edit`, `can_change_class`; the countermeasure's `lesson` and
  `can_write_lesson`; the removed row's `owner "procedure"`, `name`, `code`, `unit`; the
  messages of S075 § 5.2 ("Enter the lesson text"); the bounds 80 / 1000.
- The site rule is hidden behind flags, so no button ends in a 403 (S075 § 5.7; the tick hidden
  when `can_change_class` is false, and an unchanged `for_class` on a `PUT` is not written).
- The route `/equipment/lessons/:id(\d+)` does not collide with `/equipment/:id(\d+)`; a route
  that is not a nav item passes `canOpenRoute` (`stores/navigation.js:34-37`), as the improvement
  page does.
- `GET /api/equipment/<id>` gives `class_id` and `class_code` (`backend/equipment.py:266-267`),
  and the equipment page already builds the class label from `ensureEquipmentClasses`
  (`EquipmentDetailView.vue:117-120`); § 5.4's read for *Write lesson* works. The improvement's
  `machine` is `{id, code, name}` (`backend/improvements.py:272`, pinned at
  `test_improvements_api.py:120`).
- Print: `main.css:152-169` hides `.no-print` and resets the shell; the two print views call
  `window.print()` the same way. A page of its own for the lesson (D3) is right: QR, link, print.
- The card's place is `order-0` in the page's flex column, which puts it at its DOM position on
  every width.
- Standards: TPM one-point lesson and yokoten, ISO 9001 § 7.1.6 and § 7.5.3, WCAG 2.2 SC 2.5.5
  named and explained, each shown on a control; `tap-target` is `main.css:142`.
- Use on the floor: UI text follows scope B ("Add lesson", "Save lesson", "Print lesson",
  "Retire OPL-007? It leaves the machine's page. You can bring it back.", "Keep it"); no card
  for a reader of a machine with no lessons; pictures and the title first, large; the lesson's
  text may be Tamil while the labels stay English (Plan § 4.3a).
- Tests: titles `S077:`; the two `@device` tests are geometry checks and the rest untagged;
  `expectDialogFits` on each dialog; the device checks are of the kinds a browser cannot judge
  (Tamil typed on a phone keyboard and read on another device, paper, a real QR scan) and carry
  account, network and where (BR1-06 fixes the machine).
- No new abstraction: the card loads itself as `MetersCard`, the dialog is one `useFormModal`,
  photos go through `usePhotoUploads` and `DocumentsCards`.

## Feedback

- idea: the facts file could grep a quoted UI text the brief attributes to a file (here the 503
  text "as `api.js`'s message"), which would have shown the wrong file and wording without a
  manual grep (`backend/api_common.py:79`).
- waste: the facts file's *Screen text in the tests* section lists 46 lines for `"Title"` and 20
  for `"Cancel"`, generic words that matter in no test here; a cap, or skipping labels under
  two words, would save the read.
