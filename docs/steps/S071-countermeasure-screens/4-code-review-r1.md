```
Step: S071 — Countermeasures: screens
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S071 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** I found 2 minor findings and 4 nits. The
screens follow the brief: the card, the two dialogs, the inline cancel, the photos under the row,
*Me › Open work* and the removed-documents row. Every control follows the server's flags. The
save order of *Mark done* is right, and the raise screen keeps its behaviour.

## Tests run

- **Unit suites** (`YANTRA_TEST_RUN=s071cr1 tooling\run-tests.bat`): backend 3666 passed,
  frontend 321 passed, tooling 185 passed. All suites passed. The counts match the coder's run
  (s071c1).
- **Frontend build**: not run again. The coder's `npx vite build` is clean, and the unit suite
  imports every changed module that the build would refuse.
- **Browser tests**: none re-run. No finding of mine needs a run. The coder's report names the
  right specs: the targeted run covered `improvements` and `me` (the new tests), `tickets-raise`
  and `journeys` (the `usePhotoUploads` extraction), `equipment` and `tickets-work`
  (`DocumentsCards`), `settings` (the removed-documents row) and `screens`: 153 passed, 3
  skipped. `e2e/support/improvements.js` changed, so the coder also ran `screens.spec.js` on
  `phone-webkit` (9 passed). The whole Normal run passed once: 282 passed, 13 skipped.

## Findings

### CR1-01 (minor) — *Change countermeasure* says the current owner has left the site while the list loads, or when it fails

- **Where:** `frontend/src/views/improvements/ActionDialog.vue:36-41` (`ownerChoices`) with
  `:44-54` (`loadOwners` empties `owners` first).
- **Problem:** `ownerChoices` adds the opened owner with "(not at this site now)" whenever that
  owner is not in `owners`. `loadOwners` sets `owners` to `[]` before its request. So on every
  *Change*, the select shows "Kannan (technician) (not at this site now)" until the list
  arrives. When the list fails to load, the wrong label stays. The detail already says whether
  the owner left: `owner.active` and `owner.may_own`, which `CountermeasureItem` uses for the same
  words.
- **Failure scenario:** On the plant Wi-Fi, an engineer opens *Change countermeasure 1* to move
  the due date. For a second, or for good after a load error, the owner field reads "Kannan
  (technician) (not at this site now)". The engineer thinks Kannan has left and picks another
  owner, though Kannan still works at the site.
- **Fix:** Decide the marker from the detail, as the row does: keep the opened owner as
  `{id, name, left: !owner.active || !owner.may_own}`, and add "(not at this site now)" only when
  `left` is true. Keep listing the opened owner while the list is missing, under the plain name.

### CR1-02 (minor) — No test adds a photo again in the close-only phase

- **Where:** `frontend/e2e/improvements.spec.js:482` (the refused-photo test);
  `frontend/src/views/improvements/MarkDoneDialog.vue:70-79` (`uploadChosen`) and `:111-117`.
- **Problem:** The test checks that a refused photo leaves the dialog open, close-only, with
  the countermeasure done. It does not test the phase's own path. This path is the reason the
  phase exists (brief § 5.5 step 5, BR2-03): a photo chosen there uploads at once with `saving`
  true, then the dialog emits `reload`, so the row reads `"Photos (1)"`. That branch has its own
  code (`uploadChosen`), and no test runs it.
- **Failure scenario:** A later change sets `saving` false too early in `uploadChosen`, or drops
  its `emit("reload")`. The technician adds the photo again and taps *Close*. The row behind
  still reads `"Add photos"`, or the close drops the upload. The suite stays green.
- **Fix:** Extend the test. After the close-only phase shows, call `setInputFiles(TEST_PHOTO)` on
  the dialog's file input. Expect the row `li[data-photo="test-photo.jpg"]` to show `.fa-check`,
  then tap *Close*, and expect the row's `"Photos (1)"` button (`exact: true`).

## Nits

- **CR1-03** (nit) `frontend/src/views/ImprovementDetailView.vue:140`: a refused cancel with no
  field (409: the owner marked it done on *Me* meanwhile) leaves the stale row asking. Reload the
  detail on a 409 with no field, as `MarkDoneDialog.save` and `MoveDialog` do.
- **CR1-04** (nit) `frontend/src/views/improvements/MarkDoneDialog.vue:60-68`: the previews are
  freed only at the next `open()` and on unmount. § 5.6 says `revokeAll()` runs on the dialog's
  close too. Call it after `modal.value.close()` and on the close-only *Close*, or change the
  composable's comment to say "at the next open".
- **CR1-05** (nit) `frontend/src/components/CountermeasureItem.vue:171`: the wide layout repeats
  Bootstrap's `lg` breakpoint as a bare `992px`. The brief says `d-lg-flex`, and the report does
  not name this choice. Say in the comment that 992px is Bootstrap's `lg`, or use the
  `d-lg-flex` and `order-lg-*` classes.
- **CR1-06** (nit) `frontend/e2e/improvements.spec.js` (the first S071 test): the test checks
  only the default due date's format. It could check the date against `istDay(14)`, so a wrong
  default shows in the flow too (the unit test covers `defaultDueDate` alone).

## Use on the floor

- *Mark done* on a phone: FormModal is full screen below `sm` with a fixed footer, so
  `"Mark done"` stays in view. The row's `"Mark done"` is `btn-success`, full width on a phone.
  `"Add photos"` in the dialog is `btn-lg w-100`. No `btn-sm` is on any new control. The footer
  button is FormModal's normal `btn-primary` (D1, accepted at review); the gloved first tap is
  device-check row 51.
- The inline cancel asks first, with a required reason. `"Cancel countermeasure"` is `btn-danger`
  and stays disabled while the reason is empty. The cancel icon is `btn-outline-danger`, apart
  from the pen.
- The screen texts follow writing style B: "Marked done. A photo was not saved. Add it again, or
  close.", "Cancel this countermeasure? It stays on the record with your reason.", "Why cancel
  it?", "Keep it". The load-error line "The people could not be loaded: …" matches the app's
  other dialogs.
- Empty states: "No countermeasures yet." with the editor's hint. *Me* shows no heading when I
  own none. The not-in-Team line is unchanged.

## Checked and found consistent

- **The save order of *Mark done*:** the done `POST` goes first. A refusal sends no photo, and a
  409 with no field also emits `reload`. On success, `saved(detail)` goes out at once, then
  `markClean()`, then `uploadAll()` with `saving` still true. FormModal's `onHide` blocks ✕ and
  Esc while saving. A failed photo sets `donePhase`, and the footer becomes *Close* only.
  `dirty` is off in that phase.
- **No double POST:** FormModal's submit is disabled while `saving`, and a form whose default
  button is disabled does no implicit submission. `uploadAll` marks a row `uploading` before its
  first await, so two calls never send the same file.
- **`usePhotoUploads` and the raise screen:** the size check, the title (`withoutExtension`,
  200), kind `photo`, one file at a time and the per-row message are the same as before. A
  `pending` row shows the spinner. `uploading` has no gap between files, since nothing awaits
  between a row's `done` and the next row's `uploading`. `tickets-raise` and `journeys` passed
  in the targeted run.
- **`DocumentsCards` `changed`:** it fires after a remove, an upload and a title change (the
  only three writes in the component). The equipment page, the Models panel and the ticket page
  do not listen, so nothing changes for them.
- **The improvement page:** `load()` keeps the detail while it reloads, so a `reload` or
  `changed` never unmounts the open dialog or the photo cards. `onSaved` closes the ask.
  `cancellingId` and `photosOpenId` keep one row asking and one row's cards open at a time.
- **Hidden, not disabled:** `"Add countermeasure"` only with `improvement:edit` and `is_open`.
  `"Mark done"` only with `can_mark_done`. The pen and the cancel only with `can_change`, and
  never on *Me*. The photo cards' `canEdit` is `can_add_photo`. The photos button follows
  § 5.2's rule, and a `mine` item (no `documents`) shows none.
- ***Me › Open work*:** `mine` loads only on page 1 of *Open work*, only for holders of
  `improvement:read`, in the same `Promise.all`. A load error is the tab's one error line with
  *Retry*. An owner without `improvement:read` (the storekeeper, who has no *Me* either) makes no
  call, so no 403 shows. The heading uses `total`. `saved` and `reload` reload the tab. The
  dialog sits outside the list, so it stays open after the row leaves. `defaultMeTab` is
  unchanged.
- **`ActionDialog`:** `blank(seed = {})` takes no seed at set-up, as self-check 13 asks. The due
  date's `min` is `problem_at`'s day. The 30-countermeasures refusal shows at the top. Every
  field renders its `fieldError`.
- **Removed documents:** the row reads "Countermeasure IM-… · Corrective" from `action_kind`.
  Restore is blocked on a cancelled countermeasure, and the placeholder names improvements.
  These match `documents.py`'s `'action'` owner.
- **The six sentences** are word for word S070 § 2's table, with a unit test.
- **`expectDialogFits`** is called on every dialog the new tests open: *Add* twice, *Change*, and
  *Mark done* in three tests. The cancel has no dialog. No new test is tagged `@device`, and none
  checks a layout. `exact: true` is on every `"Add photos"` and `"Mark done"` locator.
- **Docs:** `docs/Plan.MD` (*Me* and the *Improvements* bullet) and `docs/steps/device-checks.md`
  rows 51 and 52 match the change. The step has no migration, secret, role or rule. The
  CLAUDE.md spec-map change is proposed in the report, as instructed.
- **Manual checks:** the report carries both important checks: the two **important** flows as
  `[auto]` with their tests, and row 51 as an unticked box.
- **Scope:** no backend file, no change to `FormModal.vue` or `e2e/support/dialogs.js`, no count
  on the tab. The report names the two extra events (`ask-cancel`, `keep`) and the slot.

## Manual browser check (the user)

- Row 51 (**important**): *Mark done* from *Me* with the camera on an Android phone, with a work
  glove on: `"Add photos"`, the *Now* tick and the footer's `"Mark done"` at the first tap.
- Row 52: a HEIC photo from an iPhone in *Mark done*.
- On a desktop, glance at the card at `lg` width with a long countermeasure text: the badges,
  the text, the due date and the buttons sit in one line.

## Feedback

- waste: `step_snapshot.py diff S071 --stat` lists the S075 and S077 brief edits and S070's status
  line, which are not S071's change; I read the list twice to sort them out (1 min).
- idea: the snapshot diff could leave out `docs/steps/S0NN-*/` of every other step, as it already
  leaves out the step's own folder, so a code reviewer sees only the step's code and docs.
