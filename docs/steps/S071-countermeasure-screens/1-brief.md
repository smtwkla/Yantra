```
Step: S071 — Countermeasures: screens
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066, S067, S068 (in code review); S069, S070 coded before S071
Status: Approved 30-10-2026 by KLA (delegated: R05 gate R, "start coding unless a defining question")
From: R05.3 (second half; backend in S070)
```

# S071 — Countermeasures: screens

## 1. What will be built

R05.3 was split at the API (S070 § 9, *The split*). **S070** builds the countermeasures, their
rules, the API and the documents owner (`docs/steps/S070-improvement-countermeasures/1-brief.md`).
**This step builds the screens** on S070 § 6, exactly as written there. It adds no route, table or
key.

1. **The card *Countermeasures*** on the improvement page (mock-up
   `docs/roadmap/R05-mockups/03-countermeasures.html`, `.png`): "Countermeasures (2 of 6 done)",
   one row per countermeasure with its kind, what will be done, the owner, the due date and the
   state; *Overdue 2 days* in red past the due date. `"Add countermeasure"` for engineers and
   managers while the improvement is open.
2. **Add / change** a countermeasure in one dialog: *Kind* (the six, each with its plain sentence),
   *What will be done*, *Owner*, *Due date*.
3. **Cancel** an open countermeasure with a reason, asked inline on its row.
4. **Mark done** (mock-up `04-my-countermeasure.html`): *What did you do?*, *Done on* (the S051
   time field with *Now*) and photos of the work, then `"Mark done"`. On a phone, with a gloved
   thumb.
5. **Photos of a countermeasure** on the improvement page: `"Photos (n)"` (or `"Add photos"` when
   there are none yet) opens the documents cards of that countermeasure under its row (view, add,
   retitle, remove), as the ticket page shows its photos.
6. ***Me › Open work*** lists my open countermeasures above my tickets, overdue first by due date,
   each with `"Mark done"` (mock-up 04).
7. **Settings › Removed documents** shows a removed countermeasure photo with its improvement, so
   the manager can restore or delete it (S008).

**After S070 and S071:** milestone 1 of R05. On IM-2026-10-001 the engineer adds the six
countermeasures of the contactor case; Kannan sees *Replace the torn door gasket* on his *Me* and
marks it done with a photo; Priya marks the fitter's job done for him.

### Out of scope

- Everything S070 builds, and everything S070 § 1 *Out of scope* leaves to later items (alerts
  R05.5; states, timeline and history R05.4; lessons R05.6; PM plans R05.9; reopen, S070 § 9 Q1).
- The mock-up's line "Becomes a PM plan once PM is built (R03)" and *Open lesson* (R05.9, R05.6).
- The mock-up's state badge *Actions open* and the line "When every countermeasure is done, the
  improvement moves to *Watching*" (R05.4).
- A count on the *Open work* tab ("Open work (3)" in the mock-up): the tabs keep their labels
  (`me.spec.js:139` checks they fit; a count would widen them).
- Any change to the shared `FormModal.vue` or `e2e/support/dialogs.js` (BR1-01): *Mark done* uses
  FormModal's standard submit button, and the cancel asks on the row.

## 2. Standards and practice

The standards behind the countermeasures are S070 § 2 (ISO 9001 § 10.2.1 (c), § 10.2.2, § 7.5.3
with its recorded departure; EN 13306; TPM maintenance prevention, yokoten, one-point lesson; ISO
27001 A.5.15, A.8.3). On the screens:

- **The six kinds, said for the floor** (Q3.1 a). One set of sentences, S070 § 2's table word for
  word, in `ACTION_KINDS`: the *Kind* select shows the chosen kind's sentence under it, and the
  card ends with all six. So a technician reading *Design-out* learns what it means where he meets
  it.
- **TPM — autonomous and focused improvement on the floor.** In plain words: the person who does the
  work records it, where the work is. The owner marks their own countermeasure done on their phone,
  from *Me*, with a photo as evidence (ISO 9001 § 10.2.2: the record of the action and its result).
- **ISO 27001 A.5.15 (access control)**, on screen. Every control follows the server's flags
  (`can_change`, `can_mark_done`, `can_add_photo`) and `permissions` / `is_open` (S070 § 5.7), so no
  button ends in a refusal.

## 3. Where

S071 is coded after S070. Files marked **(S068)** are new in S068 and exist in the working tree
(S068 is in code review); **(S069)** marks S069's changes to them.

### Frontend

- `frontend/src/views/ImprovementDetailView.vue` **(S068, S069)**: the card *Countermeasures*
  (§ 5.1), after S069's *Root cause* card, across the full width under the two columns.
- `frontend/src/components/CountermeasureItem.vue` (new): one countermeasure's row, used on the
  improvement page and on *Me*, for both answer shapes (§ 5.2); the inline cancel (§ 5.4).
- `frontend/src/views/improvements/ActionDialog.vue` (new): *Add countermeasure* / *Change
  countermeasure*, one `useFormModal` (§ 5.3).
- `frontend/src/views/improvements/MarkDoneDialog.vue` (new): what was done, the time, photos
  (§ 5.5). Used by the page and by *Me*.
- `frontend/src/composables/usePhotoUploads.js` (new): the photo list, the size check and the
  one-at-a-time upload, taken out of `RaiseTicketView.vue` (`frontend/src/views/RaiseTicketView.vue:230-270`)
  so *Mark done* does not copy it (CLAUDE-COMMON *DRY*; D3). Its call contract: § 5.6.
- `frontend/src/views/RaiseTicketView.vue`: uses `usePhotoUploads`; it still uploads each photo
  the moment it is chosen, with the same markup (§ 5.6).
- `frontend/src/components/documents/DocumentsCards.vue`: emits `changed` after a successful
  upload, title edit or remove (BR1-07), so the improvement page can reload its count. Its other
  callers ignore the event.
- `frontend/src/views/MeView.vue`: *Open work* gains the countermeasures (§ 5.7).
- `frontend/src/utils/improvementLabels.js` **(S068, S069)**: `ACTION_KINDS` (key, label,
  sentence), `actionKindLabel`, `ACTION_STATE_LABELS`, `overdueText(days)` ("Overdue 1 day" /
  "Overdue 2 days"), `actionCountsText(counts)` ("2 of 6 done"; cancelled ones left out of both
  numbers), `defaultDueDate(today)` (today + 14 days, `YYYY-MM-DD` through `toLocalDateValue`,
  `frontend/src/utils/ticketLabels.js:311`).
- `frontend/src/views/settings/RemovedDocuments.vue`: the countermeasure row, its restore refusal
  and the search placeholder (§ 5.8).

### Tests

- `frontend/tests/improvementLabels.test.js` **(S068)**: § 8.2.
- `frontend/e2e/improvements.spec.js` **(S068)**: the S071 tests of the page (§ 8.1).
- `frontend/e2e/me.spec.js`: the S071 *Me* tests (§ 8.1).
- `frontend/e2e/screens.spec.js`, `frontend/e2e/tickets-raise.spec.js`, `frontend/e2e/journeys.spec.js`,
  `frontend/e2e/settings.spec.js`, `frontend/e2e/equipment.spec.js`, `frontend/e2e/tickets-work.spec.js`:
  run again, no line expected to change (§ 8.2).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 6 *Screens*: the improvement page's *Countermeasures* card; *Me* (`docs/Plan.MD:829`):
  *Open work* lists my open countermeasures too (S071), and PM jobs join it in phase 4 (R03.4).
- `.claude/CLAUDE.md` § SMTW-Review: the spec map adds or extends the `improvements` entry
  (S068's docs pass adds it; it is not in the tree yet) to read S067/S068/S069/S071, and `me` reads
  S031/S064/S071.
- `docs/steps/device-checks.md`: the rows of § 8.3.

**File count:** 14 code and test files (11 code, 3 tests changed; 6 more specs run again), 3 docs.

## 4. Data model

None. The screens read and write only through S070 § 6 and S067 § 6.

## 5. Rules

### 5.1 The card *Countermeasures*

- **Header:** "Countermeasures" and, when any exist, `actionCountsText(action_counts)` in the
  header ("Countermeasures (2 of 6 done)"). `"Add countermeasure"` (`btn btn-outline-primary`, icon
  `fa-solid fa-plus`, the ticket page's size as S068 BR1-11) when `permissions` holds
  `improvement:edit` and `is_open`.
- **Rows:** a `list-group` at every width (as S068's and S069's cards), one `CountermeasureItem`
  per entry of `actions`, in the server's order (as added). On a wide screen (`lg` and up) the
  row's parts sit side by side (`d-lg-flex`: the kind and state badges, the text, the owner, the
  due date, the buttons), which reads like the mock-up's table; on a phone they stack. One markup
  (BR1-05).
- **Empty:** "No countermeasures yet." and, for an editor of an open improvement, "Add what the team
  will do about the root cause."
- **The six kinds**, under the card, always (`small text-secondary`): one line per kind, its label
  in italics and S070 § 2's sentence, from `ACTION_KINDS` ("*Correction*: Fixes this failure now,
  often already done on the ticket." …).

### 5.2 One countermeasure (`CountermeasureItem.vue`)

**Two answer shapes** (BR1-04): a detail entry (S070 § 6 `actions`) and a `mine` item (no `state`,
`owner`, `done_*`, `cancelled_*` or `documents`). The component reads `state ?? "open"`, shows the
owner line only when `owner` is present, the done and cancelled lines only when `state` says so,
and the photos button only when `documents` is present. `showImprovement` (set on *Me*) adds the
improvement line; the done `POST` on *Me* uses `item.improvement.id`.

- **Line 1:** the kind badge (`badge text-bg-light border`, `actionKindLabel`); the state badge:
  *Open* (`text-bg-secondary`), *Done* (`text-bg-success`), *Cancelled* (`text-bg-light`), and,
  for an open one with `overdue_days > 0`, `overdueText` (`text-bg-danger`) instead of *Open*;
  at the right "due 08-11-2026" (`formatDateTime`, which gives DD-MM-YYYY for a date-only value,
  `frontend/src/utils/datetime.js:11`).
- **Line 2:** the text (`overflow-wrap: anywhere`).
- **Line 3:** "Owner: Kannan (technician)"; " (not at this site now)" when `owner.active` or
  `owner.may_own` is false (as S068's lead).
- **Done:** "Done 28-10-2026 16:10 · recorded by Priya (engineer)" (`formatDateTime` of `done_at`;
  the "recorded by" part only when `done_by_name` differs from `owner.name`), then the done text.
- **Cancelled:** "Cancelled 30-10-2026 11:52 by Priya (engineer): <reason>" (`formatDateTime` of
  `cancelled_at`, with the time), the row in `text-secondary`.
- **The photos button** (BR1-07, BR1-17), `btn btn-outline-secondary`:
  - on a done row: `"Photos (n)"` when `documents.length > 0`; `"Add photos"` when it is 0 and
    `can_add_photo`; nothing otherwise;
  - on an open or cancelled row: `"Photos (n)"` only when `documents.length > 0` (to view).
  A tap toggles `DocumentsCards` under the row (§ 5.5, last part).
- **The component's contract** (BR2-04): `CountermeasureItem` makes no call. It emits `change`,
  `cancel(reason)`, `mark-done` and `photos`; the page (or *Me*) makes the calls and replaces its
  copy, as S068's remove (`ImprovementDetailView.vue:66-87`). The page holds `cancellingId` and
  `photosOpenId` and passes `cancelling` and `photosOpen` down, which is how "only one row asks at a
  time" (§ 5.4) and "one open at a time" (§ 5.5) hold.
- **With `showImprovement`** (on *Me*): line 4 a link "IM-2026-10-001 · HP003 will not start" to
  the improvement page; an overdue row gets the `list-group-item-danger` background (mock-up 04).
- **Buttons** (the ticket page's size, gloved thumbs):
  - `"Mark done"` (`btn btn-success`, full width on a phone) when `can_mark_done`;
  - change (icon `fa-solid fa-pen`, `aria-label` "Change countermeasure 3", the row's number in
    the list) and cancel (icon `fa-solid fa-ban`, `btn-outline-danger`, `aria-label` "Cancel
    countermeasure 3") when `can_change`. Not on *Me*: *Me* is for doing the work, not planning it.

### 5.3 The dialog *Add countermeasure* / *Change countermeasure*

`ActionDialog.vue`, `useFormModal({ path: "/api/improvements/<id>/actions", … })`
(`frontend/src/composables/useFormModal.js:20`); the change `PUT`s to `<path>/<action_id>`.

- **The call contract** (self-check 13; S069 BR1-04): `useFormModal` calls `blank()` with no argument
  at set-up (`useFormModal.js:22`), so `blank(seed = {})` reads the seed with optional chaining.
  *Add*: `openCreate(seed)`, `seed = {today}`; `blank` gives `{kind: "", text: "", owner_id: "",
  due_date: defaultDueDate(seed.today)}` (`defaultDueDate` of `undefined` gives ""). *Change*:
  `openEdit(action)`; `fromRecord` gives `{kind, text, owner_id: owner.id, due_date}`.
- **Fields:** **`"Kind"`** (select, "Choose the kind" first, then the six labels; under it the
  chosen kind's sentence as `form-text`), **`"What will be done"`** (textarea, 3 rows,
  `maxlength` 500), **`"Owner"`** (select, "Choose the owner" first, then the people of
  `GET /api/improvements/owners?improvement_id=<id>` by name; on *Change*, an owner not in that list
  is listed last, marked "(not at this site now)", so an edit of the text alone keeps them),
  **`"Due date"`** (`type="date"`, `min` = `problem_at.slice(0, 10)`, S070 § 6, the floor the server
  checks; help "By when it should be done").
- **Buttons:** FormModal's own: `"Add countermeasure"` / `"Save countermeasure"` (`saveLabel`) and
  `"Cancel"`.
- A load error of the owner list shows at the top; the save still sends what is chosen. Every
  field renders its `fieldError`; the 30-countermeasures refusal has no field and shows at the top.
- **The common case** (self-check 13): kind, a line of text, the owner, the date already two weeks
  ahead: three picks and a sentence.

### 5.4 Cancel, inline on the row (BR1-01)

No dialog: the row asks, the pattern of the Labour and Parts panels and S068's *Remove ticket*
(`confirmingRemoveId`, `frontend/src/views/tickets/LabourPanel.vue:153-156`). A tap on the cancel
icon replaces the row's buttons with:

- the line "Cancel this countermeasure? It stays on the record with your reason.";
- **`"Why cancel it?"`** (textarea, 2 rows, `maxlength` 500, with its `<label>`, help "For
  example: done by another countermeasure, or added by mistake."), focused;
- `"Cancel countermeasure"` (`btn-danger`, disabled while the reason is empty after trim) and
  `"Keep it"` (`btn-outline-secondary`).

`"Cancel countermeasure"` sends `POST …/actions/<action_id>/cancel` `{reason}`; the answer (the
detail) replaces the page's copy. A refusal shows under the field (`reason`) or under the row (no
field). Only one row asks at a time; `"Keep it"` restores the buttons. A textarea inside a row has
no precedent in the app (D7); it is one field, so the row stays short on a phone.

### 5.5 The dialog *Mark countermeasure done*

`MarkDoneDialog.vue`, one dialog for the page and *Me*, in `FormModal` with its standard footer:
`"Cancel"` and the submit `"Mark done"` (`saveLabel`; FormModal's `btn btn-primary`, as every ticket
move dialog, `MoveDialog.vue`; D1). It does **not** use `useFormModal`'s `send()`, which closes the
modal as soon as its request resolves (`useFormModal.js:79-92`); it writes its own `save()` (BR1-02).

- **Opening:** `MarkDoneDialog.open({ improvementId, action })` (the page's id, or
  `item.improvement.id` on *Me*). The dialog copies the action's id and text at `open()`, so it
  does not depend on the row, which is gone from *Me* after the first reload (BR2-01).
- **Above the fields:** the countermeasure's text (`text-secondary`).
- **Dirty** (BR2-08): the dialog passes `:dirty="dirty || files.length > 0"` to `FormModal` (its own
  prop; no shared change), so a ✕ with only photos chosen asks "Discard your changes?".
- **Fields:** **`"What did you do?"`** (textarea, 3 rows, `maxlength` 1000, placeholder "New
  gasket fitted."); **`"Done on"`**: `EventFields` (`frontend/src/views/tickets/EventFields.vue`)
  with `withRemark: false`, `timeLabel: "Done on"`, `idPrefix: "done"`, its `timeError` the
  field error of `done_at`, keyed on an opens counter (as `MoveDialog.vue:99`), so a reopened
  dialog starts at *Now* even after a typed time and a cancel. *Now* sends `null` (S051 U2).
- **Photos:** a large `"Add photos"` button (a `label` over a hidden file input, `multiple`,
  `accept` `ACCEPT.photo`, no `capture`, so a phone offers the camera and the gallery, as
  `RaiseTicketView.vue:291-293`) feeding `usePhotoUploads` with `previews: true`; each chosen
  photo shows as a small thumbnail with a ✕ (`aria-label` "Remove <name>"). A photo above the limit
  (`upload_max_mb` of the countermeasure's documents list, loaded on open) is marked at once:
  "Larger than 10 MB", as the raise screen.
- **`save()`, in order:**
  1. `saving` true; `apiPost(…/actions/<action_id>/done, {done_text, done_at: time})`.
  2. A refusal: `error` (or the field's message) is set, as `MoveDialog.save` does
     (`MoveDialog.vue:151-155`); a 409 with no field also emits `reload` (as
     `MoveDialog.vue:96-98`), since the page or tab behind is stale; `saving` false; no photo is
     sent.
  3. Success: emit `saved(detail)` at once (BR2-01 a): the page replaces its copy, so the row shows
     *Done* behind the dialog; *Me* reloads its tab. Call `markClean()` (`useFormModal.js:35`), so
     a close asks no "Discard your changes?"; then `uploadAll()` with `saving` still true, so the ✕
     and the buttons stay blocked while photos go.
  4. Every photo uploaded (or none chosen): when at least one photo was uploaded, emit `reload`
     (the page reloads the detail, so the row reads `"Photos (n)"`; *Me* reloads, a no-op for the
     row); then `modal.close()`.
  5. A photo failed: a `donePhase` ref puts FormModal in `closeOnly` mode with "Marked done. A
     photo was not saved. Add it again, or close.", each failed photo with its reason, the
     `IPHONE_PHOTO_HINT` when the server refused a HEIC file (as `DocumentUploadModal.vue`), and
     `"Add photos"` again (S070 allows photos on a done countermeasure). Photos chosen in this phase
     upload at once with `saving` true, so the ✕ and `"Close"` stay blocked (`FormModal.vue:55`,
     `:173`) and a close mid-upload never drops a photo silently (BR2-03); after each successful
     upload the dialog emits `reload`. `"Close"` just closes: no close event is needed.
- **Events, by caller:** the page listens to `saved` (replace the copy) and `reload` (reload the
  detail, the `MoveDialog` contract it already has). *Me* reloads its tab on either; its `mine`
  item has no detail to take.
- **The one-tap path:** type what was done, keep *Now*, tap `"Add photos"` → the camera → `"Mark
  done"`.

**Photos later, on the page:** the row's photos button toggles, under that row, `DocumentsCards`
(`frontend/src/components/documents/DocumentsCards.vue:28`) with `basePath`
`/api/improvements/actions/<id>/documents`, `canEdit` = `can_add_photo`, `largeAdd`, as the ticket
page uses it (`frontend/src/views/TicketDetailView.vue:502`). One open at a time. On its new
`changed` event the page reloads the detail, so `"Photos (n)"` stays true.

### 5.6 `usePhotoUploads` — the call contract (BR1-03)

`usePhotoUploads({ path, maxMb, previews = false })`, `path` and `maxMb` refs or getters, returns:

- `files`: `[{key, file, name, previewUrl, state: "pending" | "uploading" | "done" | "failed",
  message}]`;
- `add(fileList)`: appends each file as `pending`; a file above `maxMb` is `failed` at once
  ("Larger than N MB"); `previewUrl` (an object URL) only when `previews` is true;
- `remove(key)`: takes a file off and revokes its URL;
- `uploadAll()`: uploads every `pending` file, one at a time (kinder to a slow mobile link), as
  kind `photo` with the title from the file name (`withoutExtension`, cut to `TITLE_MAX`, as today);
  a `failed` file is not sent again unless chosen again;
- `uploading` (computed), `revokeAll()` (called on the dialog's close and on unmount).

**The raise screen keeps its behaviour:** `onPhotosChosen` calls `add` then `uploadAll` at once,
`previews` false. Every chosen photo now shows its row at once (today a row appears when its
upload starts, `RaiseTicketView.vue:269`); a `pending` row shows the spinner, as `uploading`, so
the template needs no new icon (BR2-02). The rows keep their markup and icons (`tickets-raise.spec.js:39-40` reads
`.list-group-item` and `.fa-check`). *Mark done* calls `add` on choose and `uploadAll` after the
done.

### 5.7 *Me › Open work*

- When the user holds `improvement:read` (`userPermissions`), the *Open work* tab also loads
  `GET /api/improvements/actions/mine`, in the same `Promise.all` as the tickets
  (`frontend/src/views/MeView.vue:98`), **on page 1 only** (the pager counts tickets).
- Above the tickets: the heading "Countermeasures (n)" (`h6`; `n` is `mine`'s `total`, not
  `items.length`, since `mine` stops at 200, S070 § 6), then one `CountermeasureItem` per
  item with `showImprovement`, in the server's order (by due date, so overdue first). Then the
  tickets as today, under "Tickets" (`h6`) when countermeasures showed.
- **Empty states:** no countermeasures shows nothing for them; the tickets' texts stay as they are
  (`MeView.vue:122-127`), so "No open tickets are assigned to you." shows under the countermeasures
  when only those exist. The *not in Team* line (`MeView.vue:158-161`) is unchanged (`mine` is
  empty then too).
- **After *Mark done*** (or its `reload`): the tab reloads; the row is gone.
- **A load error** of `mine` shows as the tab's load error with `"Retry"` (one error line for the
  tab, as today).
- **The default tab** stays `defaultMeTab` (`frontend/src/utils/ticketLabels.js:520`): an operator
  who owns a countermeasure lands on *Raised by me* and taps *Open work* (§ 9).
- **R03.4** later adds PM jobs to this tab; whichever step comes second fits into the first's
  layout (R05 § Order, *Not in parallel*).

### 5.8 Settings › Removed documents

`RemovedDocuments.vue`: a row with `owner === "action"` shows "Countermeasure IM-2026-10-001 ·
Corrective" (`item.name`, then `actionKindLabel(item.action_kind)`, S070 § 5.8: the one label
table) and its unit; `restoreBlocked` (`:83`) adds "Cancelled countermeasures cannot be changed"
when `state === "cancelled"`. The search placeholder (`:132`) names improvements too: "Search
equipment code, model, ticket, improvement, title or file name…". Restore and purge use the item's
`path` as for every owner.

### 5.9 Words for the floor

"Countermeasure" is the roadmap's word (Q3.1). The screens use plain verbs: *What will be done*,
*What did you do?*, *Done on*, *Why cancel it?*, *Keep it*, *Remove* (the app's verb). The kinds
keep their one-sentence explanations (§ 5.1, § 5.3). No "CAPA", no "action item".

### 5.10 The database down

The calls go to S070's routes, which answer 503 while the database is down. The page and *Me* show
their load error with `"Retry"`; a dialog shows the error at the top; the inline cancel shows it
under the row. A photo upload's 503 ("File storage is unavailable — try again later") shows on its
row (§ 5.5).

## 6. API

None new. S070 § 6 as it stands: the countermeasure routes, `mine`, `owners`, the documents routes
of the fourth owner, the detail's `actions`, `action_counts` and `problem_at`, the removed list's
`action_kind`; S067's detail for `permissions` and `is_open`. If S070's review rounds change § 6,
this brief follows before it is coded.

## 7. Design decisions

- **D1. *Mark done* is one dialog with the photos inside; its submit is FormModal's standard
  button.** The mock-up's floor path: what, when, a photo, done. The photos go after the done, so
  the done record never waits for a slow upload. The button is FormModal's primary one, as every
  ticket move dialog (BR1-01 b): no change to shared code. Rejected: a green full-width button
  (needs a `FormModal` prop and a change of `expectDialogFits`, both shared code); photos first,
  then the done (a failed done leaves photos on an open countermeasure); a second dialog for photos.
- **D2. One `CountermeasureItem` for the page and *Me*.** The same rows, flags and badges in two
  places, for both answer shapes. Rejected: two copies (they drift).
- **D3. `usePhotoUploads` taken out of the raise screen.** *Mark done* needs the same size check,
  one-at-a-time upload and row states. Rejected: a copy in `MarkDoneDialog.vue` (DRY);
  `DocumentUploadModal` (one file, a title to type, and a dialog over a dialog).
- **D4. Photos later through `DocumentsCards` under the row**, with a `changed` event so the count
  stays true. Viewing, adding, retitling and removing exist there already for every owner.
  Rejected: a new photo strip (a second viewer); no count on the button (loses the glance).
- **D5. No change or cancel buttons on *Me*.** *Me* is the doer's list; planning is on the
  improvement page. Rejected: the full row everywhere (more buttons on a narrow phone row).
- **D6. Default due date two weeks ahead.** Most countermeasures are planned for the next weeks; the
  engineer changes it when not. Rejected: empty (one more pick on every add); today (always wrong).
- **D7. Cancel asks inline on the row, with the reason there** (BR1-01 b). The panels' and S068's
  pattern; no dialog whose `"Cancel"` close button would sit beside `"Cancel countermeasure"`.
  Rejected: a dialog (needs shared-code changes, D1); a renamed action such as *Withdraw* (the
  state is *Cancelled* everywhere, one word for one thing).
- **D8. One list markup at every width** (BR1-05). Rejected: a table on a desktop and a list on a
  phone (every row rendered twice, doubled buttons).

## 8. Tests and acceptance

### 8.1 Automated (e2e, targeted: `improvements.spec.js`, `me.spec.js`, `screens.spec.js`)

Set-up by API as S068 § 8.1 (a back-in-service ticket, an improvement by `POST
/api/improvements`) and S070's routes for countermeasures. Seed people (`tooling/e2e/seed_e2e.py:36`):
the engineer "Priya (engineer)", the technician "Kannan (technician)", "Ravi (technician)" (persona
`technician2`, `:41`), the operator "Muthu (operator)", "Ramesh (operator, no phone)" (no login),
the manager "Arun (manager)". Each test makes its own records. `"Mark done"` is a row button and
the dialog's submit: the tests scope the row button to its row and press the submit with
`saveDialog(page, "Mark done")` (`frontend/e2e/support/tickets.js:99`).

In `improvements.spec.js`:
- **important** S071: the engineer taps `"Add countermeasure"`, picks *Corrective* (its sentence
  shows), types the text, picks Kannan, keeps the default date, saves: the row shows *Corrective*,
  *Open*, "Owner: Kannan (technician)" and the header "Countermeasures (0 of 1 done)". The engineer
  changes the due date through "Change countermeasure 1"; then adds a second and cancels it on its
  row ("Cancel countermeasure 2", types the reason, `"Cancel countermeasure"` with `exact: true`):
  the row shows *Cancelled* and the reason; the header reads "(0 of 1 done)". Each dialog calls
  `expectDialogFits`.
- S071: the engineer marks done a countermeasure owned by "Ramesh (operator, no phone)": the row
  shows "recorded by Priya (engineer)" and `"Add photos"`.
- S071: Ravi (a technician who is not the owner) opens the page: no `"Mark done"`, no change or
  cancel buttons on Kannan's row; the operator Muthu sees the rows and the six kinds and no
  `"Add countermeasure"`.
- Every S071 locator of `"Add photos"` and `"Add photo"` uses `exact: true` (§ 8.2).
- S071: the manager removes a countermeasure's photo through the photo cards (the button then reads
  `"Add photos"`, not `"Photos (1)"`), opens Settings › Removed documents, sees "Countermeasure
  IM-… · Corrective" and restores it.

In `me.spec.js`:
- **important** S071: Kannan opens *Me › Open work*: "Countermeasures (1)" with the row and the
  improvement's serial above his tickets; taps the row's `"Mark done"`, types what he did, keeps
  *Now*, adds `frontend/e2e/fixtures/test-photo.jpg` (`setInputFiles`, as
  `equipment.spec.js:1026`), presses the submit: the row leaves *Me*. On the improvement page the
  row shows *Done* and `"Photos (1)"`; a tap shows the photo card with one photo.
  `expectDialogFits` on the dialog.
- S071: an overdue countermeasure: the test fulfils `GET /api/improvements/actions/mine` with the
  real answer and `overdue_days: 2` on its item (`page.route`, as S064's access-log test,
  `settings.spec.js:93`); *Me* shows "Overdue 2 days". (The API refuses a due date before the
  problem, which in a test is today: S070 § 5.3.) The spec gains the file-level
  `test.use({ serviceWorkers: "block" })` with its comment, as `readings.spec.js:20-22`.

Also:
- `screens.spec.js`: no new route; it runs again because the page and *Me* changed.
- No test is `@device`: none checks a layout (a fit helper in a flow test does not tag it).

### 8.2 Existing tests that run again, and locators

- `frontend/e2e/me.spec.js`: the S031 tests read the tabs, the count line "… open tickets assigned
  to you" and the not-in-Team line (`:50-120`); none of their users owns a countermeasure, so no
  "Countermeasures" heading shows and no line changes. `:139` (the three tabs fit) is unchanged:
  the tab labels do not change. The file-level `serviceWorkers: "block"` changes nothing for them
  (they register no service worker).
- `frontend/e2e/tickets-raise.spec.js` and `frontend/e2e/journeys.spec.js` (`:81`, the raise
  journey's photo): the photo step now runs through `usePhotoUploads` with the same labels, markup
  and states (§ 5.6), so no line is expected to change.
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/tickets-work.spec.js`: `DocumentsCards` gains an
  emit only; no line changes.
- `frontend/e2e/settings.spec.js`: the removed-documents card gains a row kind and a longer
  placeholder; no spec reads the placeholder; its existing rows are unchanged.
- `frontend/e2e/improvements.spec.js` **(S068, S069)**: the page gains buttons named "Change
  countermeasure n", "Cancel countermeasure n", `"Add countermeasure"`, `"Mark done"`,
  `"Photos (n)"` and `"Add photos"`. `"Add photo"`, the header button of `DocumentsCards`
  (`DocumentsCards.vue:344`), is a substring of `"Add photos"`, and both are on the page once the
  cards are open under a row: the S071 specs name each with `exact: true` (BR2-05). S068's locators
  already use `exact: true` (`improvements.spec.js:25, 58, 73, 86`); the coder checks S069's (`"Add why"`, `"Edit root
  cause"`) the same way. `"Cancel"` (a dialog's close button) is never on the page beside
  `"Cancel countermeasure"`: the cancel is inline (§ 5.4), and `expectDialogFits`'s "Cancel"
  locator (`frontend/e2e/support/dialogs.js:34`) meets only FormModal's close button in
  `ActionDialog` and `MarkDoneDialog`.
- `frontend/tests/ticketLabels.test.js`: `defaultMeTab` unchanged (`:399`).

**Frontend unit** (`frontend/tests/improvementLabels.test.js`): `ACTION_KINDS` holds S070 § 2's six
labels and sentences word for word; `actionKindLabel` (an unknown key returned as it is);
`overdueText` (1 day, 2 days, 0 → ""); `actionCountsText` (none, 2 of 6, cancelled left out);
`defaultDueDate` (14 days, across a month end, `undefined` → "").

### 8.3 On a real device

- **important** *Mark done* with the camera on an Android phone: open *Me*, the row's `"Mark done"`,
  `"Add photos"` → the camera → a photo of a panel; the thumbnail shows; `"Mark done"`; the photo
  opens on the improvement page. With a work glove on: the photo button, the *Now* tick and
  `"Mark done"` hit at the first tap. Account: a technician (Kannan's role). Network: the plant
  Wi-Fi. Where: either; on production, KLA prepares an improvement on the TEST machine with a
  countermeasure owned by the test login (as row 6 of `device-checks.md`). A browser cannot judge
  the real camera or the gloved tap (settings: *Device checks*).
- An iPhone photo in *Mark done*: HEIC refused with the "Most Compatible" note, or a JPEG saved.
  Account: a technician. Network: the plant Wi-Fi. Where: either, prepared as above. Not important
  (S006's existing check covers the note; this checks it in the new dialog).

### 8.4 Acceptance

- The frontend unit suite green; `npx vite build` clean; the targeted specs green; the whole
  browser suite at Normal once at the end (`RaiseTicketView.vue` and `DocumentsCards.vue` changed,
  and *Me* is the landing page).
- On a phone (`phone-chromium`) every new dialog fits (`expectDialogFits` in the flows).
- The contactor case's six countermeasures can be entered and marked done on a phone.

## 9. Open questions and assumptions

- **The split** (S070 § 9): R05.3 was cut at the API; this step holds the screens. S070 is coded
  first, and this brief builds on S070 § 6 as written.
- **Assumption:** the operator who owns a countermeasure lands on *Raised by me* (S031's
  `defaultMeTab`: *Open work* only for `ticket:work` holders) and taps *Open work*. Changing the
  default for owners would need a call before the first paint; R05.5's alert brings them to the
  countermeasure anyway. Not proposed.
- **Assumption:** the mock-up shows the countermeasures as a table on a desktop; the page uses one
  list whose rows lay out in a line on a wide screen (§ 5.1, D8).
- **Departure from the mock-up** (BR1-01 b): *Mark done* is FormModal's primary button, not the
  mock-up's full-width green one.
- **Doubt:** the mock-up's state badge *Actions open* is R05.4's; S071 keeps S068's *Analysing*.
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: § 1 (items 3, 4, 5; *Out of scope*), § 2, § 3 (`CancelActionDialog.vue` gone;
`DocumentsCards.vue` added; the specs that run again; file count), § 5.1, § 5.2, § 5.3, § 5.4
(rewritten: inline cancel), § 5.5 (the footer, the `save()` sequence, the photos button), § 5.6
(new: `usePhotoUploads` contract; *Me* is now § 5.7, removed documents § 5.8, words § 5.9, DB down
§ 5.10), § 5.8, § 5.9, § 5.10, § 6, § 7 (D1, D4, D7 and D8 new), § 8.1, § 8.2, § 8.3, § 8.4, § 9.

| Finding | Answer |
|---|---|
| BR1-01 major | Accepted (b): no change to `FormModal.vue` or `e2e/support/dialogs.js`. *Mark done* uses FormModal's standard submit, `"Mark done"`; the cancel asks inline on the row with the reason field, `"Cancel countermeasure"` / `"Keep it"`. § 1, § 3, § 5.4, § 5.5, D1, D7, § 8.1, § 8.2, § 9. |
| BR1-02 minor | Accepted (a): § 5.5 writes `save()`: the done `POST`, `markClean()`, the uploads under `saving`, close or the `closeOnly` phase; `send()` is not used. |
| BR1-03 minor | Accepted (a): the `usePhotoUploads` call contract in § 5.6; the raise screen keeps its immediate upload and markup. |
| BR1-04 minor | Accepted (a): `CountermeasureItem` reads both shapes (§ 5.2). |
| BR1-05 minor | Accepted (a): one `list-group` at every width, `d-lg-flex` rows (§ 5.1, D8, § 9). |
| BR1-06 minor | Accepted (a): one set of sentences, S070 § 2's word for word (§ 2, § 5.1, § 8.2). |
| BR1-07 minor | Accepted (a): the photos button's rule (§ 5.2) and a `changed` emit from `DocumentsCards` that reloads the detail (§ 3, § 5.5, D4). |
| BR1-08…BR1-17 nits | Accepted: BR1-08 `reload` on a 409 with no field (§ 5.5); BR1-09 `EventFields` keyed on an opens counter (§ 5.5); BR1-10 the overdue test in `me.spec.js` with `serviceWorkers: "block"` (§ 8.1); BR1-11 `journeys.spec.js` named (§ 3, § 8.2); BR1-12 the row button scoped, the submit through `saveDialog`, Ravi's persona `technician2` (§ 8.1); BR1-13 "KLA prepares one" (§ 8.3); BR1-14 "Add it again, or close."; "Remove <name>" (§ 5.5); BR1-15 `min` from `problem_at` (S070 BR1-09), the cancelled line with its time, `TicketDetailView.vue:502` (§ 5.2, § 5.3, § 5.5); BR1-16 the placeholder (§ 5.8); BR1-17 `"Add photos"` when there is none yet (§ 5.2). Also S070 BR1-03: the removed row labels `action_kind` (§ 5.8). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 3 (*Docs*), § 5.2 (the component's contract), § 5.5
(opening, dirty, steps 3–5, events by caller), § 5.6 (the raise screen's rows), § 5.7 (the heading's
count), § 8.1, § 8.2.

| Finding | Answer |
|---|---|
| BR2-01 minor | Accepted (a): the dialog emits `saved(detail)` right after the done `POST`, and `reload` once a photo was uploaded (at step 4 and after each upload in the `donePhase`); no close event; the dialog copies the action's text at `open()`. § 5.5. |
| BR2-02…BR2-08 nits | Accepted: BR2-02 a `pending` raise row shows the spinner (§ 5.6); BR2-03 photos in the `donePhase` upload with `saving` true (§ 5.5); BR2-04 `CountermeasureItem` emits, the page calls and holds `cancellingId` / `photosOpenId`, `MarkDoneDialog.open({ improvementId, action })` (§ 5.2, § 5.5); BR2-05 `"Add photo"` / `"Add photos"` with `exact: true`, lines `:73`, `:86` (§ 8.1, § 8.2); BR2-06 "adds or extends the entry" (§ 3); BR2-07 the heading's `n` is `mine`'s `total` (§ 5.7); BR2-08 `:dirty="dirty \|\| files.length > 0"` (§ 5.5). |
