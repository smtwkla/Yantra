```
Step: S071 — Countermeasures: screens
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068 (being coded: `ImprovementDetailView.vue`,
`improvements.spec.js` and `views/improvements/` are in the tree; S069 and S070 are not)

# S071 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01).** The footer buttons the brief specifies for
*Mark done* and *Cancel countermeasure* do not exist in `FormModal.vue`, and the cancel dialog as
written breaks `expectDialogFits`. Six `minor` findings give the coder rules it would otherwise
decide alone. No finding is defining; BR1-01 is a judgement call on the look of two buttons that
KLA may want to make.

Facts file read: `scratch/brief-facts-S071.md`. It predates S068's coding: it says
`frontend/e2e/improvements.spec.js`, `views/improvements/*` and `improvementLabels.js` do not
exist; they do now (`git status`). I checked those against the working tree.

Every field the brief uses exists in S070 § 6 (`actions[]`, `action_counts`, `mine`, `owners`,
the flags, `documents`), with one gap in BR1-04.

## Findings

### BR1-01 — major — The dialog footers the brief specifies need `FormModal` changes it does not name, and the cancel dialog breaks `expectDialogFits`

**Problem.** `FormModal.vue` renders a fixed footer: a close button with the text `Cancel`
(`frontend/src/components/FormModal.vue:193`) and a submit button with the class `btn btn-primary`
and the text `saveLabel` (`:194-201`). There is no prop for the submit button's class or the close
button's text. The brief asks for:

- § 5.5: `"Mark done"` as `btn-success btn-lg w-100` (D1);
- § 5.4: `"Cancel countermeasure"` as `btn-danger` and a close button `"Keep it"`, and in the same
  bullet "FormModal's own close button keeps its text". The two sentences contradict each other.

`expectDialogFits` (`frontend/e2e/support/dialogs.js:34`) finds the close button with
`getByRole("button", { name: "Cancel" })`, a substring match. With a submit `"Cancel countermeasure"`
next to a close `"Cancel"` the locator matches two buttons and `boundingBox()` fails on strict
mode. With `"Keep it"` as the close button it matches the submit by accident and measures the wrong
button. Either way the test the brief requires (§ 8.1, "Each dialog calls `expectDialogFits`")
cannot pass as designed.

**Why it matters.** The coder cannot build § 5.4 and § 5.5 as written without changing shared code
(`FormModal.vue`, `e2e/support/dialogs.js`: settings, *Shared code*), and the brief lists neither in
§ 3. A user who reads "Cancel" and "Cancel countermeasure" side by side taps the wrong one.

**Options.**

- (a) **Recommended.** Add two small props to `FormModal`: `cancelLabel` (default `"Cancel"`) and
  `saveVariant` (default `"primary"`, used as `btn-<variant>`; the size classes can go with it or stay
  the default). Change `expectDialogFits` to find the close button by
  `.modal-footer button[data-bs-dismiss="modal"]` instead of its text, so it also holds for a
  renamed close button. Name both files in § 3 and § 8.2. Both are shared code: the whole browser
  suite at Normal (already planned, § 8.4) **and** the WebKit screens run
  (`tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`, about 3 min, settings:
  *Shared code*). The cancel dialog then reads `"Keep it"` / `"Cancel countermeasure"`, as the brief
  wants.
- (b) No shared-code change: *Mark done* uses the standard primary submit button, as every ticket
  move dialog does today (`MoveDialog.vue`), and the cancel asks inline on the row (the S068 /
  S069 remove pattern, `confirmingRemoveId`) with the reason textarea in the row, `"Cancel
  countermeasure"` (`btn-danger`) and `"Keep it"`. No dialog, no fit check, no helper change.
  Cheaper, but the big green button of mock-up 04 is lost, and an inline textarea in a row has no
  precedent in the app.
- (c) Keep the dialog and rename the submit so it does not contain "Cancel" (for example
  `"Withdraw countermeasure"`). Rejected: the state is *Cancelled* everywhere (S070), and one word
  for one thing holds.

**KLA's call:** the look of the two buttons, (a) or (b). Not defining: R05.3 ships either way.

### BR1-02 — minor — *Mark done*'s save sequence cannot run through `send()` as written

**Problem.** § 5.5 says the dialog uses `useFormModal` "with `path: null` and `send`", and then
describes (1) the done `POST`, (2) the photo uploads, (3) close. `send()` closes the modal as soon
as its request resolves (`useFormModal.js:74-92`, `finish` → `modal.close()` → `afterSave`), so the
uploads cannot follow it inside the open dialog. If the request function did both the `POST` and
the uploads and threw on a failed photo, the error would show in the normal footer, not the
`closeOnly` mode the brief wants, and a second tap on `"Mark done"` would `POST` again and get
409 "This countermeasure is already done".

Two more points the sequence leaves open:

- `dirty`: after the done succeeds the form still differs from its snapshot, so `"Close"` in
  `closeOnly` mode would raise "Discard your changes?" (`FormModal.vue:61-64`). The dialog must
  call `markClean()` (exposed by `useFormModal`) once the done is saved.
- the ✕ and `"Close"` must stay blocked while photos upload (FormModal blocks hide while `saving`
  is true, `:55-56`), so `saving` must cover the uploads too.

**Why it matters.** The coder would invent the state machine of the floor's main dialog alone.

**Options.**

- (a) **Recommended.** Write the sequence in § 5.5: `save()` sets `saving`, calls `apiPost(…/done)`;
  a refusal assigns `error` (as `MoveDialog.save` does, `MoveDialog.vue:151-155`) and returns; on
  success it keeps the detail, calls `markClean()`, uploads the pending photos one at a time with
  `saving` still true; all uploaded → `modal.close()` and `afterSave(detail)`; any failed → a
  `donePhase` ref switches FormModal to `closeOnly` with the failure list and `"Add photos"`, and
  `"Close"` hands the detail to the caller (the page replaces its copy; *Me* reloads). `send()` is
  not used.
- (b) Two steps for the user: *Mark done* saves and closes; the photos go through `"Photos (n)"`
  on the row. Rejected by D1 (one more step on a phone).

### BR1-03 — minor — `usePhotoUploads` has no call contract, and its two callers differ

**Problem.** § 3 and D3 say the composable takes "the photo list, the size check and the
one-at-a-time upload" out of `RaiseTicketView.vue:230-270`. The raise screen uploads each photo
the moment it is chosen (`onPhotosChosen` → `uploadOne`), has no thumbnails and no remove. *Mark
done* holds the photos as thumbnails with a remove ✕ until the done is saved, then uploads them.
The brief does not say what the composable exposes, nor that the raise screen keeps its immediate
upload (§ 3 says only "no change a user can see").

**Why it matters.** Self-check 13 (the composable's call contract) is the step settings' own item.
`tickets-raise.spec.js:39-40` reads the raise rows by `.list-group-item` and `.fa-check`; the brief
promises no line changes, so the raise markup and timing must stay.

**Options.**

- (a) **Recommended.** State the contract in § 3 or § 5.5: `usePhotoUploads({ path, maxMb })`
  returns `files` (`[{key, file, name, previewUrl, state: "pending" | "uploading" | "done" |
  "failed", message}]`), `add(fileList)` (the size check marks a too-large file `failed` at once,
  "Larger than N MB"; `previewUrl` only when `previews: true`), `remove(key)` (revokes the URL),
  `uploadAll()` (one at a time; a failed one is skipped on a second call only when chosen again),
  `uploading`, `revokeAll()`. The raise screen calls `add` then `uploadAll` in `onPhotosChosen`,
  so its behaviour is unchanged; *Mark done* calls `add` on choose and `uploadAll` after the done.
  The title rule (`withoutExtension`, `TITLE_MAX`) and `kind: "photo"` live in the composable.
- (b) Keep the raise screen as it is and give *Mark done* its own small upload loop. Rejected by
  D3 (DRY), but it is the cheaper fallback if the contract grows.

### BR1-04 — minor — `mine` items have no `state`, `owner` or `done_*`; `CountermeasureItem`'s contract for the two shapes is missing

**Problem.** § 5.2 renders line 1 from `state`, line 3 from `owner`, and the done and cancelled
lines from `done_*` / `cancelled_*`. S070 § 6's `mine` item is `{id, kind, text, due_date,
overdue_days, can_mark_done, can_add_photo, improvement{…}}`: no `state` (always open), no `owner`
(the user), no `done_*`. The same component on *Me* would read `undefined` for them.

**Options.**

- (a) **Recommended.** § 5.2: the component takes both shapes: `state ?? "open"`; the owner line
  only when `owner` is present; the done and cancelled lines only when `state` says so;
  `"Photos (n)"` only when `documents` is present. The `done` `POST` on *Me* uses
  `item.improvement.id`.
- (b) Ask S070 to add `state` and `owner` to `mine`. Rejected: data the row never needs there.

### BR1-05 — minor — Two layouts from one component means two markups in the DOM, or an invalid table

**Problem.** § 5.1 asks for a `<table>` on `lg` and a `list-group` on a phone, "one component, two
layouts by Bootstrap's display classes". A component cannot be a `<tr>` inside a `<table>` and an
`<li>` inside a `<ul>` at once; the page would render every row twice (one hidden by `d-none`),
doubling the buttons and the `DocumentsCards` toggles. The photo cards under a `<tr>` need a
second `<tr colspan>` row too. The S068 and S069 cards on the same page are `list-group`s at
every width.

**Options.**

- (a) **Recommended.** One `list-group` at every width; on `lg` the row's lines sit side by side
  with a flex or grid row (`d-lg-flex`, the kind and state badges, the text, the owner, the due
  date, the buttons), which reads like the mock-up's table. One markup, no second copy. Say so in
  § 5.1 and the § 9 assumption.
- (b) A real table on `lg` with a `layout` prop and the rows rendered once per layout under a
  `v-if` on a media query (`matchMedia`). More code for a page the engineer uses on a phone first.

### BR1-06 — minor — The six kinds have two sentence sets

**Problem.** § 2 says the card's line shows "S070 § 2's table, word for word", and the dialog shows
"the chosen kind's sentence". § 5.1 then gives a shorter set ("*Correction* fixes this failure
now. *Corrective* removes the cause here. …") built from `ACTION_KINDS`, which holds one sentence
per kind. The coder must pick one; S070 § 2's sentences are the ones the standards note explains
("Removes the cause here, so this failure does not come back.").

**Options.**

- (a) **Recommended.** One set, S070 § 2's table word for word, in `ACTION_KINDS`, shown under the
  select and in the card's line ("Correction: fixes this failure now, often already done on the
  ticket. Corrective: …"). Longer, but the plain words a technician learns from. Fix § 2 and § 5.1
  to agree, and § 8.2's unit test asserts that set.
- (b) The short set in both places, and § 2 drops "word for word".

### BR1-07 — minor — `"Photos (n)"`: when it shows, and the count goes stale after the cards change

**Problem.** Two rules are missing:

1. § 5.2 puts `"Photos (n)"` under **Done** "when the row has documents or `can_add_photo`", but
   `can_add_photo` is true on every open row of an owner or editor (S070 § 5.7: state not
   cancelled). Read literally, every open row of the engineer gets a `"Photos (0)"` button; read
   by the heading, only done rows do. The floor case (a photo as evidence of the work) is the done
   row; S070 allows photos on open rows, but no screen flow needs them.
2. The count `n` comes from the detail's `documents`. `DocumentsCards` keeps its own list and emits
   nothing (no `defineEmits` in `DocumentsCards.vue`), so after an add or a remove in the cards the
   row still says the old `n` until the page reloads. The § 8.1 test ("a tap shows the photo card
   with one photo") passes, but a manager who removes the photo sees "Photos (1)" above an empty
   card.

**Options.**

- (a) **Recommended.** Rule 1: `"Photos (n)"` on a done row when `documents.length > 0 ||
  can_add_photo`; on an open or cancelled row only when `documents.length > 0` (view). Rule 2:
  give `DocumentsCards` an `@changed` emit after a successful upload, retitle or remove (one line
  in `load()`'s callers or in `remove`/`@saved`); the improvement page reloads the detail on it,
  as it does after every write. `DocumentsCards` is not in the *Shared code* list, but
  `equipment.spec.js` and `tickets-work.spec.js` touch it; the whole-suite run covers them.
- (b) Drop `n` from the label ("Photos") and accept no count. Loses the glance the row gives.

## Nits

- **BR1-08** (nit) § 5.5: a 409 on the done (cancelled or done meanwhile) means the page or the
  tab behind is stale; emit `reload` on a 409 with no field, as `MoveDialog.vue:96-98` does.
- **BR1-09** (nit) § 5.5: key `EventFields` on an opens counter (`MoveDialog.vue:99`, CR1-03
  there), so a reopened dialog starts at *Now* also after the user typed a time and cancelled.
- **BR1-10** (nit) § 8.1: name the spec file of the overdue test (`me.spec.js`, since it asserts
  *Me*). A spec that uses `page.route` adds the file-level `test.use({ serviceWorkers: "block" })`
  with its comment (`readings.spec.js:20-22`, `tickets-work.spec.js:13-16`); say so.
- **BR1-11** (nit) § 8.2: `journeys.spec.js:81` also runs a photo upload, and the raise journey
  goes through `RaiseTicketView`; name it with `tickets-raise.spec.js` (the whole-suite run covers
  it anyway).
- **BR1-12** (nit) § 8.1, § 8.2: `"Mark done"` is a row button and the dialog's submit, and *Me*
  may list several rows; the tests scope the row button to its row and press the submit with
  `saveDialog(page, "Mark done")` (`e2e/support/tickets.js:99`). Ravi's persona key is
  `technician2` (`seed_e2e.py:41`).
- **BR1-13** (nit) § 8.3: on production the camera row needs an improvement on the TEST machine
  with a countermeasure owned by the test login; write "KLA prepares one" into the row, as row 6
  of `device-checks.md` does.
- **BR1-14** (nit) UI text (scope B): "Marked done. A photo was not saved:" says what happened but
  not what to do; "Marked done. A photo was not saved. Add it again, or close." The ✕'s
  `aria-label` "Take off <name>" uses a word the app has nowhere; "Remove <name>" is the app's
  verb.
- **BR1-15** (nit) § 5.3, § 5.2, § 5.5: `min` on *Due date* is `created_at.slice(0, 10)` (the
  detail's `created_at` is a datetime with `+05:30`); the cancelled line's date through
  `formatDateTime` shows the time too ("30-10-2026 11:52"), say which; the ticket page's
  `DocumentsCards` call is `TicketDetailView.vue:502`, not `:482`.
- **BR1-16** (nit) § 5.7: the search box's placeholder (`RemovedDocuments.vue:132`) lists the
  owners it searches; add "improvement".
- **BR1-17** (nit) § 5.2: "Photos (0)" on a done row with no photo yet reads oddly; "Add photos"
  when `n` is 0 and `can_add_photo`, else "Photos (n)", or keep "Photos (0)" and say so.

## Checked and found consistent

- S070 § 6 covers every field the screens read and write: `actions[]` with `owner{active,
  may_own}`, `done_by_name`, `cancelled_by_name`, `overdue_days`, the three flags, `documents`;
  `action_counts`; `owners`; the documents routes of the fourth owner; S067's `permissions`,
  `is_open`, `created_at`. The one gap is BR1-04.
- The S051 time field: `EventFields` with `withRemark: false`, `timeLabel`, `idPrefix`,
  `timeError` exist as props (`EventFields.vue:26-39`); *Now* ticked sends `null`, which S070
  § 5.2 reads as the server's now. The *Now* label is a 44 px tap target (`EventFields.vue:146`).
- `useFormModal` calls `blank()` with no argument at set-up (`useFormModal.js:22`); the brief's
  `blank(seed = {})` and `defaultDueDate(undefined) → ""` follow S069 BR1-04. `modalError` shows
  the 30-countermeasures refusal (no field) at the top.
- `MeView.vue`: the `Promise.all` at `:98`, the empty texts at `:122-127`, the not-in-Team line
  at `:158-161`, `defaultMeTab` at `ticketLabels.js:520`; the S031 tests in `me.spec.js` read the
  tabs, the count line and the not-in-Team line only, and `:139` (`@device`) reads the tab labels,
  which do not change. The S035 landing test is unchanged.
- `page.route` with a fulfilled answer is the S064 pattern (`settings.spec.js:93`); the overdue
  test needs it because S070 refuses a due date before the improvement's start.
- No new test is `@device`: none asserts a geometry or differs by project; `expectDialogFits` in
  a flow test does not tag it (settings, *Browser tests*).
- The device checks: the camera and the gloved tap are kinds a browser cannot judge; the HEIC row
  is plain, as S006's row 46 covers the note. Both rows carry account, network and where.
- Photos: `accept` `ACCEPT.photo` and no `capture` (`RaiseTicketView.vue:293`,
  `DocumentUploadModal.vue:12`); the limit from the documents list's `upload_max_mb`; the HEIC
  hint only after a refusal (`isHeicFile`, `DocumentUploadModal.vue:64`), the S064 rule.
- Permissions on screen: every control follows `can_change`, `can_mark_done`, `can_add_photo`,
  `permissions` and `is_open`; the manager holds `equipment:purge_documents`
  (`config_rbac.py:99`) for the restore test; `restoreBlocked` at `RemovedDocuments.vue:83`.
- The S068 spec's locators already use `exact: true` for `"Edit"`, `"Add ticket"`, `"Start
  improvement"`, `"Remove ticket"` (`improvements.spec.js:25, 58, 85, 72`), so § 8.2's worry is
  mostly met; `"Cancel"` is not used there.
- Standards: § 2 names ISO 9001 § 10.2.2, TPM autonomous and focused improvement, and ISO 27001
  A.5.15 in plain words, and points at S070 § 2 for the rest; the six kinds' sentences are the
  teaching device (BR1-06 only asks for one set).
- Use on the floor: the technician's path is *Me* → `"Mark done"` → type, keep *Now*,
  `"Add photos"` → camera → `"Mark done"`: four taps and a sentence; the big buttons and the
  dialog's fit are checked; no business rule sits in a Vue file (`overdue_days`, the flags and the
  counts come from the server; the labels are display helpers).
- D6 (a due date two weeks ahead) and D5 (no change or cancel on *Me*) are stated with their
  rejected options; the out-of-scope list keeps R05.4's state badge and the *Open work* count out.

## Feedback

- waste: the facts file was made before S068's coder wrote `improvements.spec.js`,
  `views/improvements/*` and `improvementLabels.js`, so it reports them as "no such file"; I
  re-checked each with `ls` and `git status` (about 3 minutes).
- idea: when two steps of one split are reviewed in parallel (S070 and S071 here), run S071's
  review after S070's round-1 answers are in; every S070 § 6 change makes a BS round here.
- hindrance: `expectDialogFits`'s substring "Cancel" locator is the kind of fact a brief relies on
  without knowing it; a line in `docs/steps/README.md` § Manual checks or the settings ("a dialog's
  footer has a close button named Cancel and one submit button") would save reading the helper.
