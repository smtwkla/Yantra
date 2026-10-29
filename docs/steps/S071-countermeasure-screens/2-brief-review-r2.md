```
Step: S071 — Countermeasures: screens
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068 (S069 and S070 are approved but not in the
tree: `views/improvements/` holds only S068's two dialogs, `local_db.py` ends at v36)

# S071 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (BR2-01): the *Mark done*
dialog's hand-over to its caller relies on a close event `FormModal` does not have. Seven nits. No
finding needs KLA's decision; none is defining. The brief can go to gate A once BR2-01 is answered.

Facts file read: `scratch/brief-facts-S071.md` (regenerated after S068's coding: the S068 files are
listed as existing). Every file, line and name the changed sections cite was checked against it, and
against the code where it left a question.

**Re-read this round** (the diff `scratch/S071-brief-r1.md` → `1-brief.md`): § 1 (items 3–5, *Out of
scope*), § 2, § 3, § 5.1–5.6, § 5.7 (the `reload` line), § 5.8–5.10, § 6, § 7 (D1, D2, D4, D7, D8),
§ 8.1–8.4, § 9, the Review log; and S070 § 6 as it now stands. Not re-read: § 4, the unchanged lines
of § 5.7.

**Round 1 answers, checked in the text:** BR1-01 (b) is in § 1 *Out of scope*, § 5.4, § 5.5, D1, D7,
§ 8.2 and § 9; BR1-02 in § 5.5 `save()`; BR1-03 in § 5.6; BR1-04 in § 5.2; BR1-05 in § 5.1, D8, § 9;
BR1-06 in § 2, § 5.1, § 8.2; BR1-07 in § 3, § 5.2, § 5.5, D4; the nits BR1-08…BR1-17 each where the
log says. All reflected.

## Findings

### BR2-01 — minor — The caller gets the detail at a close that `FormModal` does not report, and that detail lacks the photos

**Problem.** § 5.5 step 4 says "the caller takes the detail" when the dialog closes, and step 5 says
"`"Close"` hands the detail to the caller". `FormModal` emits only `save` (`FormModal.vue:38`); the
`closeOnly` footer's `"Close"` is a plain `data-bs-dismiss` button (`:186`), and the brief rules out
a `FormModal` change (§ 1 *Out of scope*). The dialog cannot know when the user pressed `"Close"`.
Today's `closeOnly` users (`ItemPropertiesModal`, `ReadingHistoryModal`, …) hand nothing back; the
components that listen to `hidden.bs.modal` do so on their own element (`PhotoViewer.vue:89`), not
on a child's.

Also, the detail kept at step 3 is the answer of the done `POST`, before any photo went up. After
the one-tap path on the improvement page (text, *Now*, a photo, `"Mark done"`), the row would read
`"Add photos"` though a photo was saved, until the next reload.

**Why it matters.** The coder would invent the hand-over of the floor's main dialog alone, and the
natural choice (the step-3 detail at close) shows a wrong row on the page.

**Options.**

- (a) **Recommended.** The dialog emits `saved(detail)` right after step 3 succeeds, before the
  uploads: the page replaces its copy at once (the row shows *Done* behind the dialog); *Me* reloads
  its tab. When at least one photo was uploaded, the dialog emits `reload`: at step 4 before
  `modal.close()`, and in the `donePhase` after each successful upload. The page reloads the detail
  on `reload` (the `MoveDialog` contract it already has); *Me* reloads the tab (a no-op for the row,
  already gone). No close event is needed; `"Close"` in the `donePhase` just closes. Two
  consequences to write down: the dialog copies the action's text at `open()` (on *Me* the row's
  item is gone after the reload), and the dialog's `saved` carries the detail only on the page (on
  *Me* the `mine` item has no detail to give; *Me* reloads on either event).
- (b) The dialog listens to `hidden.bs.modal` on the `FormModal`'s root element through a template
  ref and emits then. Works, but reaches into the child's DOM, and the page still shows the stale
  row while the dialog is open.

### Nits

- **BR2-02** (nit) § 5.6: today a raise row appears when its upload starts (`uploadOne`, one at a
  time, `RaiseTicketView.vue:269`); with `add` then `uploadAll` every chosen photo shows at once and
  the later ones sit in `pending`, a state the raise template has no icon for (`:300-306`). Say that
  `pending` shows as the spinner (or that the rows render `pending` as `uploading`).
  `tickets-raise.spec.js:40` reads only `.fa-check`, so no line changes.
- **BR2-03** (nit) § 5.5 step 5: photos chosen in the `donePhase` upload at once; say they run with
  `saving` true too, so the ✕ and `"Close"` stay blocked (`FormModal.vue:55, 173`) and a Close
  mid-upload does not drop the photo silently.
- **BR2-04** (nit) § 5.2, § 5.4: name the component's contract: `CountermeasureItem` emits
  (`change`, `cancel(reason)`, `mark-done`, `photos`) and the page makes the calls and replaces its
  copy (as S068's remove, `ImprovementDetailView.vue:66-87`); the page holds `cancellingId` and
  `photosOpenId`, which is how "only one row asks at a time" and "one open at a time" hold;
  `MarkDoneDialog.open({ improvementId, action })` (the page's id, or `item.improvement.id` on *Me*).
- **BR2-05** (nit) § 8.1, § 8.2: `"Add photo"` (the header button of `DocumentsCards`,
  `DocumentsCards.vue:344`) is a substring of `"Add photos"` (the row button and the dialog's); once
  the cards are open under a row both are on the page, so the S071 specs name each with
  `exact: true`. The S068 lines are `improvements.spec.js:73` ("Remove ticket") and `:86` ("Edit"),
  not 72 and 85.
- **BR2-06** (nit) § 3 *Docs*: `.claude/CLAUDE.md` § SMTW-Review has no `improvements` entry in the
  tree today (S068's docs pass, `S068 1-brief.md:117`, is still in code review); write "adds or
  extends the entry", so the coder does not look for a line that is not there.
- **BR2-07** (nit) § 5.7: the heading's `n` in "Countermeasures (n)" is `mine`'s `total`, not
  `items.length` (`LIMIT 200`, S070 § 6); say which.
- **BR2-08** (nit) § 5.5: chosen photos are not in `form`, so `dirty` stays false when only photos
  were chosen and the ✕ closes without "Discard your changes?". Pass
  `:dirty="dirty || files.length > 0"` to `FormModal` (the dialog's own prop; no shared change),
  or say the text is required anyway (S070 § 5.2) and accept it.

## Checked and found consistent

- **S070 § 6 as it stands** after its round 1: `problem_at` (the earliest linked ticket's
  `occurred_at`; `slice(0, 10)` gives the `min` date), `action_kind` on the removed list, the
  `mine` item shape (no `state`, `owner`, `done_*`, `documents`; `can_mark_done`, `can_add_photo`,
  `improvement{id, serial, title, machine}`), `owners` with `improvement_id` required, the cancel
  body `{reason}`, the done body `{done_text, done_at?}`, every write answering the detail. § 6 of
  this brief names each; § 5.2, § 5.3, § 5.4, § 5.8 use them as written. `problem_at` is never null:
  an improvement keeps at least one ticket (S067).
- **BR1-01 (b) holds in the code.** `expectDialogFits` finds the close button inside
  `.modal-footer` of the open dialog (`dialogs.js:34`), so the page's `"Cancel countermeasure"`
  buttons and the row icons' `aria-label`s never meet it; `saveDialog` presses the footer's
  `button[type=submit]` (`tickets.js:99-105`), so the row's `"Mark done"` and the submit do not
  clash. S068's inline *Remove ticket* confirm already has a `"Cancel"` button on the same page
  (`ImprovementDetailView.vue:186`); it shows only while a ticket remove is being confirmed, never
  in the S071 flows.
- **The inline cancel's precedent** is as cited: `confirmingRemoveId` with the buttons replaced by
  the question and two buttons (`LabourPanel.vue:153-156`, `ImprovementDetailView.vue:182-189`).
  The confirmation states the consequence ("It stays on the record with your reason.", scope B);
  `"Cancel countermeasure"` is apart from the row's everyday buttons once the row asks.
- **`save()` of *Mark done*** fits the code: `send()` closes on resolve (`useFormModal.js:79-92`,
  `finish`), so a hand-written `save()` is right; `markClean()` (`:35`) makes `dirty` false before
  the `closeOnly` footer; `onHide` lets a close through once `saving` is false and `dirty` false
  (`FormModal.vue:53-65`); the `MoveDialog` lines cited are the error assignment (`:151-155`), the
  409 `reload` watch (`:96-98`) and the opens counter (`:99`).
- **`usePhotoUploads`** matches what `RaiseTicketView.vue:230-270` does today (the size check
  against `upload_max_mb` × MB, kind `photo`, title `withoutExtension(name).slice(0, TITLE_MAX)`,
  one at a time, the `uploading` computed that disables the label); the markup at `:291-293`
  (label over a hidden `multiple` input, `ACCEPT.photo`, no `capture`) stays in the view.
- **`DocumentsCards`**: `defineProps` at `:28`, `basePath`, `canEdit`, `largeAdd` exist; a `changed`
  emit after the upload modal's `@saved`, the title modal's `@saved` and `remove()` (`:382-384`,
  `:217-231`) is one line each; the `basePath` watch's first `load()` is not a change. The ticket
  page's call is `TicketDetailView.vue:502-507`, with `large-add`. The other callers
  (`EquipmentDetailView`, `ModelsPanel`, `PhotoViewer`) ignore an unknown event.
- **`MeView.vue`**: `Promise.all` at `:98`; `emptyText` at `:122-126`; the not-in-Team block at
  `:158-161`; `load()` returns early without `ticket:read`, which every `improvement:read` role
  holds. `me.spec.js:139` is the `@device` tabs test and reads the three labels only.
- **Tests and fixtures**: `seed_e2e.py:36` opens `PEOPLE`, `technician2` at `:41`;
  `settings.spec.js:93` is the `page.route` fulfil; `readings.spec.js:20-22` the file-level
  `serviceWorkers: "block"` with its comment; `equipment.spec.js:1026` a `setInputFiles` into a
  dialog; `DocumentUploadModal.vue:64` the HEIC hint rule (`isHeicFile` and a refusal);
  `formatDateTime` (`datetime.js:11`) gives DD-MM-YYYY for a date-only value and the time
  otherwise; `toLocalDateValue` at `ticketLabels.js:311`, `defaultMeTab` at `:520`;
  `restoreBlocked` at `RemovedDocuments.vue:83`, the placeholder at `:132`; `device-checks.md` row
  6 carries "KLA prepares one"; `docs/Plan.MD:829` is the *Me* line.
- **S069 names** the brief relies on exist in S069's approved brief: the card *Root cause*,
  `"Add why"`, `"Edit root cause"`, `RootCauseDialog.vue`, and S069's additions to
  `improvementLabels.js` and `improvementLabels.test.js` (`S069 1-brief.md:133-137, 166`). S068's
  `improvementLabels.js` has none of the S071 names yet, as § 3 says.
- **S068 BR1-11** is the ticket page's button size, `btn btn-outline-primary` without `btn-sm`
  (`S068 1-brief.md:192-194`); § 5.1's `"Add countermeasure"` follows it.
- **Standards** (§ 2): one set of sentences, S070 § 2's table word for word (checked against
  `S070 1-brief.md:95-102`: six rows, keys `correction`, `corrective`, `preventive`, `design_out`,
  `lesson`, `spread`); ISO 9001 § 10.2.2, TPM autonomous and focused improvement, ISO 27001 A.5.15
  explained in plain words, the rest pointed at S070 § 2.
- **Use on the floor**: the technician's path is unchanged by BR1-01 (b): *Me* → the row's
  `"Mark done"` → type, keep *Now*, `"Add photos"` → camera → the submit; the submit is now
  FormModal's standard button, which every ticket move dialog uses, so the floor knows it. The
  inline cancel adds one field and two buttons to a row, one row at a time. No business rule sits in
  a Vue file: `overdue_days`, the flags, the counts and `problem_at` come from the server.
- **Manual checks**: the two device rows keep account, network and where, now with the production
  preparation; both are kinds a browser cannot judge. No automated check sits on the device list.
- **Track**: full; this is round 2 of up to 3.

## Feedback

- rule: the agent prompt's closing notes say "Do NOT Write report/summary/findings .md files", while
  the role's job is to write `2-brief-review-rN.md`; the two sentences contradict, and a careful
  reader stops to resolve it (1 min).
- hindrance: `git diff --no-index` of the brief against `scratch/S071-brief-r1.md` was 40 KB and went
  to a tool-results file, one extra read; an orchestrator-made `scratch/S071-brief-r1.diff` passed
  with the task would save it.
- idea: when the round-1 copy exists, the orchestrator could list in its task the line numbers the
  brief's citations changed (here `improvements.spec.js` 72→73, 85→86 drifted by one); a brief-facts
  run that also prints the cited line's text would catch such drift mechanically.
