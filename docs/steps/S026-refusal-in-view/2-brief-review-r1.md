```
Step: S026 — A refusal is always in view
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: 3df667c + uncommitted S019, S020, S025

(The working tree holds more than the orchestrator named: S019's `ScheduleFields.vue`
and its `MoveDialog.vue` changes, S020's `PartsPanel.vue`, `machineParts.js` and
`tickets-parts.spec.js`, and S025's ticket dialogs. The brief's inventory reads
those files as they are now.)

# S026 — Brief review, round 1

**Verdict: no `blocker` or `major` finding. Light track holds; this is the only
round.** Four `minor` findings and four `nit`s. The design is right and small. The
`minor` findings correct one claim about the code (five messages the search will
not find), name a rule the coder would otherwise decide alone (which field gets
the cursor), ask for Q1 to be answered before coding, and trim item 3 of § 1 so
the coder does not refactor dialogs that need no change.

**Light-track check.** No migration, no auth or access code, no locking, no new
dependency, no endpoint. The change follows the existing `FormModal` /
`useFormModal` pattern. Files: 6 named, plus 2 markup fixes (BR1-01) and
`RaiseTicketView.vue` if Q1 is accepted — under 10.

## Findings

### BR1-01 (minor) — Five field messages are not marked, so the search will not find them

**Problem.** § 4.1 says "every dialog already marks its fields with `is-invalid` /
`invalid-feedback d-block`". That is not true for these (fact, from the code):

| Dialog | Message | Markup now | Field marked `is-invalid`? |
|---|---|---|---|
| `EquipmentFormModal.vue` | `fieldError('level')` (line 184) | `text-danger small` | yes (the Level select, create-part mode only) |
| `EquipmentFormModal.vue` | `fieldError('parent_id')` (line 207) | `text-danger small` | no — the parent is plain text |
| `PeoplePanel.vue` | `fieldError('employment')` (line 355) | `text-danger small` | no — radios, no class |
| `PeoplePanel.vue` | `fieldError('username')`, read-only branch (line 380) | `text-danger small` | no — plain text |
| `PeoplePanel.vue` | `rowError` on a site row (lines 428, 430) | `text-danger small` | no |

`PeoplePanel`'s `rowError` is the one that matters on the floor: the Team dialog is
the longest dialog in the app, the site rows are at its bottom, and a refused row
(`saveRows`, line 215) hides the `sites` alert (`v-if="fieldError('sites') &&
!rowError"`) and shows only the unmarked row message. On a phone that is the
labour bug again. The other four are server-only refusals and rare.

**Why it matters.** Item 3 of § 1 tells the coder to "confirm each one's messages
are found", but the brief's own claim says there is nothing to find. A coder who
trusts § 4.1 skips the check.

**Options.**
- (a) **Recommended.** Change the five messages to `class="invalid-feedback
  d-block"` (the S024 A2 form). Add `EquipmentFormModal.vue` and `PeoplePanel.vue`
  to the § 3 table with that one line each, and correct § 4.1 to "every dialog
  marks its fields … except the five in BR1-01, fixed here".
- (b) Widen the search to `.text-danger`. Rejected: `EquipmentMoveModal`'s
  `searchError` is `text-danger` too and is not a refusal of a save; the search
  would land on it.

`EquipmentMoveModal.vue`'s `searchError` (line 160) stays as it is: it answers a
search, not Save. Say so in § 3 so the coder does not touch it.

### BR1-02 (minor) — "The field nearest it" is not defined

**Problem.** § 3 says `revealError()` "focuses the field nearest it"; § 4.3 says
"the nearest input, select or button". Three cases in the inventory have no
`.is-invalid` element at all, only a message under a group of buttons:
`RegradeDialog` intensity (line 100), `MoveDialog` `machine_down` (line 212) and
`machine_stopped` (line 277), and `PeoplePanel` employment (after BR1-01). The
top bar (`.alert-danger`) has no field. "Nearest" could mean the button above the
message, the first button of the group, or the next input below. The coder would
decide alone.

**Recommendation.** Write the rule in § 4.3:
1. Take the first element in document order that matches `.is-invalid,
   .invalid-feedback.d-block, .alert-danger` inside `.modal-body`.
2. Scroll it to the middle (`block: "center"`).
3. Focus: if it is `.is-invalid`, focus it. If it is an `.invalid-feedback`, focus
   the first `input, select, textarea, button` inside its parent element (the
   `.mb-3` block or `fieldset`) — for a choice group that is the first choice
   button. If it is the top `.alert-danger`, scroll only; nothing to type.
   Always `focus({ preventScroll: true })`.

Check this gives the brief's own example: for `minutes` both the hours and the
minutes inputs carry `is-invalid` (LabourPanel lines 205, 207); the first is
hours, so the cursor goes to hours as § 5 asserts.

### BR1-03 (minor) — Q1 (the Raise ticket page) needs an answer before coding, and it changes where the search lives

**Problem.** § 1 puts page forms out of scope; § 6 Q1 proposes to put the raise
page in. The coder cannot start on both. The raise page is the operator's main
screen (Plan.MD § 3; the operator raises from the machine's QR label), and the
same bug is there: `RaiseTicketView.vue` shows a refusal for *How bad is it?* at
the top (line 405) and Save at the bottom (line 517, `btn-lg w-100`). Its
messages are already marked (`is-invalid` / `invalid-feedback d-block`, lines
405–491; two `alert-danger`, 388 and 516), so the same search works.

**Fact for the e2e side.** No page test uses `expectFieldMessage` today: every call
passes a dialog (`tickets-work`, `masters`, `tickets-parts`). `tickets-raise.spec.js`
checks its message with `toBeVisible()` directly (line 84). So the `toBeInViewport()`
change breaks no page test either way. The helper's comment says "`scope`: the
page or the open dialog"; after this step a page scope asserts the rule too.

**Options.**
- (a) **Recommended: include the raise page.** Put the search in one small
  function, `utils/revealError.js` (`revealError(rootEl)`: the three selectors,
  scroll, focus per BR1-02), called by `FormModal.revealError()` on its
  `.modal-body` and by `RaiseTicketView` on its form after a refusal. Two real
  uses, one function — CLAUDE-COMMON "no new abstraction without a second use"
  is met. `scrollIntoView` scrolls whichever ancestor scrolls, so the same call
  works for the modal body and the page. One more file; light still holds. Add
  one automated check: on the phone set-ups, raise with nothing chosen, Save,
  "Choose how bad it is" (or the page's wording) is in the viewport.
- (b) Leave the page out (a later step). Then keep the search inside
  `FormModal.vue` as the brief says, and change the helper's comment to say a
  page scope now asserts "in the viewport" too.

Either way, close Q1 in the brief before approval.

### BR1-04 (minor) — Item 3 of § 1 asks for wiring that no dialog needs

**Problem.** § 1 item 3 and the § 3 row "Dialogs with their own error refs" say
`tradesError`, `fileError`, `loadError` must be "wired to the same call, or
folded into `useFormModal`'s `error`". From the code:

- `tradesError` (LabourPanel line 166), `loadError` (MoveDialog line 187,
  EditTicketDialog line 75) and `nodesError` (PartsPanel line 198) all reach
  `FormModal` through its `error` prop. § 3 already gives `FormModal` a watch on
  that prop. Nothing to wire.
- `fileError` (DocumentUploadModal line 56) is not a refusal of Save: it shows the
  moment the file is chosen, next to the input the user just touched, and Save is
  disabled with the same text (`saveDisabledReason`); `save()` returns before any
  request. Nothing to wire.
- `rowError` (PeoplePanel) is set together with a throw that `send()` turns into
  `error = {field: "sites"}` (line 217), so `useFormModal`'s watch fires. Found
  once BR1-01 fixes its markup. Nothing to wire.

**Why it matters.** "Fold the ref into `useFormModal`'s `error`" invites a
refactor of four dialogs for no gain; a light-track coder on Sonnet may do it.

**Recommendation.** Replace item 3's second sentence with: "Messages a dialog
passes to `FormModal`'s `error` prop are covered by the prop watch; no dialog
needs its own call. The coder confirms this per dialog and lists the result."
Drop the § 3 row, or keep it with "expected: none". Keep the 21-line list in the
impl report.

### BR1-05 (nit) — State the timing facts the coder must rely on

The orchestrator asked whether the watch fires on a same-value re-refusal. It
does, and the brief should say why, so the coder adds no `deep: true` and no
message comparison:

- Every refusal assigns a **new object** (`error.value = { field, message }` in
  the dialogs' own checks; `send()` in the catch). `watch(error)` on a `ref`
  fires on a change of identity, so the second "Time spent must be…" in a row
  fires again. `send()` also sets `error.value = null` before the request.
- The watch must skip `null` (`openCreate`, `openEdit`, `send` all set it) and
  guard `modal.value?.revealError()`: the ref is null before mount.
- `nextTick` is needed, as the brief says: a `watch` with the default `flush:
  "pre"` runs before the DOM has the `is-invalid` class. `flush: "post"` is the
  same thing in one option.
- The scroll must be instant (the `scrollIntoView` default, no `behavior:
  "smooth"`): `toBeInViewport()` polls, but a smooth scroll under a 10 s
  `expect` timeout is a flake waiting to happen on the WebKit project.
- A server refusal with no field triggers both watches (`useFormModal`'s on
  `error`, `FormModal`'s on the `error` prop). Two scrolls to the same element
  are harmless; say so in § 4.2, or let the prop watch alone cover the top bar.

### BR1-06 (nit) — The new test reproduces the bug on one set-up only; say which, and make the pick safe

- The Add-labour body (picker list 16 rem, trade, date, time) is about 600 px.
  On the iPhone 14 project (viewport 390 × 664) the body shows about 530 px, so
  *Time spent* is below the fold — the bug. On Pixel 7 (412 × 839) and desktop
  the whole body fits, so the test passes there with or without the fix. Fine,
  but note it in § 5, and consider one line on `phone-webkit` only before Save:
  `await expect(hours).not.toBeInViewport()` — then the test proves the scroll.
- "Pick a name by clicking it": pick a person with at most one trade (Kannan or
  Ravi hold one each; Priya none, `seed_e2e.py` lines 40–42). A person with two
  trades is refused on *Trade worked* first ("Choose the trade worked"), above
  the fold, and the test would not reach the time field.
- The existing test (`tickets-work.spec.js` line 99) fills the time first, as the
  brief says. Confirmed.

### BR1-07 (nit) — Standards wording

- ISO 9241-110:2020 renamed *error tolerance* to **use error robustness**; the
  2006 edition had *error tolerance*. Use the current name, or cite the edition.
  The principle: the system helps the user see and correct an error with little
  effort — a message out of sight fails it.
- WCAG 2.2 SC 2.4.11 is *Focus Not Obscured (Minimum)*, level AA: when an element
  gets focus, it is not entirely hidden by other content. Correct citation; the
  phone keyboard (Q2) is exactly the case it names. SC 3.3.1 *Error
  Identification* is also right. The screen-reader benefit of moving focus is
  better placed under SC 3.3.1 than claimed as its text; one word.

### BR1-08 (nit) — Scope A wording

- "The S024 browser test did not catch it: it fills the time before it presses
  Save, and its message check … not that it is on screen." — 40 words, two
  ideas. Split at the colon.
- § 1 item 3, second sentence (the parenthesis with three ref names) — see
  BR1-04; if kept, split into two sentences.
- § 4.1 "the first message is the one the user meets first" — "meets" is
  unusual; "reads first".

No UI text is added by this step; scope B has nothing to check.

## Checked and found consistent

- **Inventory.** 21 `FormModal` users: 11 masters panels through `useMasterForm`
  (which passes `modal` through, line 48), `EquipmentFormModal`,
  `EquipmentMoveModal`, `EquipmentStatusModal`, `DocumentUploadModal`,
  `DocumentTitleModal`, `LabourPanel`, `AssignDialog`, `EditTicketDialog`,
  `MoveDialog`, `RegradeDialog`. `PartsPanel` (untracked) is the 22nd and is
  rightly left out; its markup is already in the S024 A2 form. `PhotoViewer` is
  the only other Bootstrap modal and has no form. No `FormModal` user is missed.
- **Markup.** Apart from BR1-01, every field message in the 21 dialogs and in
  `EventFields`, `StartedAtFields`, `ScheduleFields` and `PersonPicker` is
  `is-invalid` on the control plus `invalid-feedback d-block`. The top bar is
  `alert alert-danger` (FormModal line 146). `PeoplePanel`'s `trade_ids` and
  `sites` messages are `alert-danger` inside the body and are found by the same
  search.
- **Existing field-message tests under `toBeInViewport()`.** All eight calls pass
  a dialog. "Already a breakdown" (regrade, no field) and "Nothing to change"
  (`tickets_core.NOTHING_TO_CHANGE`, no field) go to the top bar of a short
  dialog; "Close its tickets first" has field `active`, not in the Units form,
  so it is `modalError` at the top; "Add a remark" ×3 and the two parts
  messages sit by their fields in dialogs that fit a phone. None should fail
  after the change; the brief's rule "a failure means the code, not the test"
  is right.
- **`toBeInViewport()` is the right assertion.** It uses the Intersection
  Observer, which clips by every scrolling ancestor, so a message scrolled out
  of `.modal-body` counts as not intersecting even though the dialog itself is
  on screen. `toBeVisible()` only checks CSS visibility and size, which is why
  the S024 test passed.
- **Trigger design (§ 4.2).** Both refusal paths set the same `error` ref, so one
  watch covers both; the rejected alternative (re-check after each Save press)
  would miss the server's late answer. Agreed.
- **`saveDisabledReason` out of scope.** `EquipmentMoveModal`,
  `EquipmentStatusModal` and `DocumentUploadModal` disable Save with a reason;
  no refusal, nothing to reveal. Agreed.
- **Manual checks.** The split is right: the three automated checks are things a
  browser judges; the device row is the iOS keyboard, which Playwright's WebKit
  has not, and it names account (none), network (any) and where (dev server).
  The two important automated checks are the right ones to mark.
- **Q2.** One more fact for the device check: iOS Safari opens the keyboard on a
  programmatic `focus()` only inside a user gesture. The dialog's own check runs
  in the Save tap (keyboard opens); the server's refusal comes after an `await`
  (keyboard may stay closed). The labour dialog's own check catches every time
  error before a request, so the server path cannot be forced there. The row in
  `device-checks.md` can add a second try on a server refusal — a Masters
  dialog saved with a code that exists — or just note that the two can differ.
