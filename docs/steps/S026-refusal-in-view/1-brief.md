```
Step: S026 — A refusal is always in view
Doc: brief
Author: Planner (Opus)
Date: 22-10-2026 (revised 22-10-2026 after brief-review r1)
Track: light
Baseline: b6b8dfb (stale brief check 22-10-2026: no file of this brief changed since review r1)
Status: Gate B — code review r3 clean (0 blocker, 0 major; 2 minor, 2 nit open); awaiting the user (approved 22-10-2026 by KLA; Q1: (a); A1 by KLA 22-10-2026)
```

# S026 — A refusal is always in view

**The bug (KLA, 22-10-2026).** Ticket › *Add labour*: KLA picked a name and pressed
**Save**. Nothing happened. The dialog body scrolls (`modal-dialog-scrollable`), and
*Time spent* was below the visible part. `LabourPanel.vue`'s own check refused the save
and wrote "Time spent must be between 1 minute and 24 hours" under that field, out of
sight. Save looked dead.

The S024 browser test did not catch it. It fills the time before it presses Save. Its
message check (`expectFieldMessage`) asks only that the message is visible in the page,
not that it is on screen.

**The rule.** `SMTW-WebApp-Base.md` § Form / Modal Pattern now has *A refusal is always in
view* (added in `smtw-common`, 22-10-2026; it reaches Yantra by the next sync). This step
makes every Yantra dialog follow it, as the user asked: "look at all dialogues".

## 1. What will be built, and out of scope

**Built:**
1. **The dialog shows the refusal.** When a save is refused, the dialog scrolls the first
   message into view (to the middle of the dialog body) and puts the cursor in its field.
   A message for no field (the red bar at the top of the dialog) is scrolled into view
   the same way. It works for both kinds of refusal:
   - the dialog's own check, before any request (labour time, regrade, assign, move …);
   - the server's refusal (`{error, field}` from the API, S001 pattern).
2. **Done once, in shared code.** One function, `revealError(container)` in
   `frontend/src/utils/revealError.js`, finds the first message in a container, scrolls
   it and focuses its field (rule in § 4.3). `FormModal.vue` calls it on its dialog body.
   `useFormModal.js` makes `FormModal` call it whenever its `error` becomes a message.
   Every dialog gets it with no change of its own.
3. **Every dialog is checked.** The coder goes through the 21 dialogs in § 3 and confirms
   that the search finds each one's messages. Five messages are not marked today; they
   are fixed here (§ 3). The impl report lists all 21 dialogs with what was done to each
   (most: nothing).
4. **The *Raise ticket* page too** (if the user accepts Q1, § 6). The page calls
   `revealError()` on its form after a refusal.
5. **The browser tests check "on screen", not only "visible".** `expectFieldMessage`
   (`frontend/e2e/support/dialogs.js`) changes from `toBeVisible()` to
   `toBeInViewport()`. Every existing field-message test then enforces the rule. A new
   test reproduces the bug.

**Out of scope:**
- **Disabled Save with a reason** (`saveDisabledReason`): there is no refusal there, the
  button says why. Unchanged.
- **`PartsPanel.vue`** (S020's work, untracked, not committed). It uses `useFormModal`, so
  it gets the behaviour with no change; the coder does not edit it.
- Any change to the server, the messages' wording or the dialogs' layout.

## 2. Standards and practice

- **ISO 9241-110:2020 (interaction principles) — *use error robustness* and
  *self-descriptiveness*:** the system helps the user see and correct an error with
  little effort. A message out of sight fails both.
- **WCAG 2.2, SC 3.3.1 *Error Identification*** (the error is shown in text and names the
  field; moving the cursor there also tells a screen reader where the problem is) **and
  SC 2.4.11 *Focus Not Obscured (Minimum)*, level AA** (a focused field is not entirely
  hidden by other content, for example the phone keyboard, Q2).
- No maintenance standard is touched.

## 3. Where

| File | Change |
|---|---|
| `frontend/src/utils/revealError.js` (new) | `revealError(container)`: the search, scroll and focus of § 4.3. Plain DOM, no Vue. |
| `frontend/src/components/FormModal.vue` | Exposes `revealError()`, which calls the utility on its `.modal-body`. A `watch` on the `error` prop (the top bar) calls it when the prop becomes a message. |
| `frontend/src/composables/useFormModal.js` | A `watch` on `error` (§ 4.2): skips `null`; with `flush: "post"` it calls `modal.value?.revealError()`. |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | `level` and `parent_id` messages: `text-danger small` → `invalid-feedback d-block` (BR1-01). |
| `frontend/src/views/masters/PeoplePanel.vue` | `employment`, read-only `username` and the site rows' `rowError` messages: `text-danger small` → `invalid-feedback d-block` (BR1-01). `rowError` matters most: the Team dialog is the longest one, and the site rows are at its bottom. |
| `frontend/src/views/RaiseTicketView.vue` | Only if Q1 is accepted: after a refusal (its own check or the server's), `revealError()` on the form, after the DOM update. |
| `frontend/e2e/support/dialogs.js` | `expectFieldMessage`: `toBeInViewport()` in place of `toBeVisible()`; its comment says it applies to a page too. |
| `frontend/e2e/tickets-work.spec.js` | The new labour test (§ 5). |
| `frontend/e2e/tickets-raise.spec.js` | Only if Q1 is accepted: the raise-page test (§ 5). |
| `docs/steps/device-checks.md` | The real-iPhone row (§ 5). |

**The dialogs to check** (21; all use `FormModal` and `useFormModal`):
- Masters: Sites, Units, Equipment classes, Equipment types, Manufacturers, Models, People
  (Team), Trades, Failure modes, Failure causes, Maintenance actions (11 panels, through
  `useMasterForm.js`).
- Equipment: `EquipmentFormModal`, `EquipmentMoveModal`, `EquipmentStatusModal`.
- Documents: `DocumentUploadModal`, `DocumentTitleModal`.
- Tickets: `LabourPanel`, `AssignDialog`, `EditTicketDialog`, `MoveDialog` (with the
  fields of `EventFields.vue`, `StartedAtFields.vue`, `ScheduleFields.vue`),
  `RegradeDialog`.

**Nothing to wire for the dialogs' own error refs** (BR1-04). `tradesError`
(LabourPanel), `loadError` (MoveDialog, EditTicketDialog) and `nodesError` (PartsPanel)
reach `FormModal` through its `error` prop, which the prop watch covers. `fileError`
(DocumentUploadModal) is not a refusal: Save is disabled while it shows. `rowError`
(PeoplePanel) already goes into `useFormModal`'s `error`; only its markup changes.

**Left alone:** `EquipmentMoveModal`'s `searchError` (`text-danger`) answers a search, not
Save. `PhotoViewer.vue` (a viewer with no Save) and `ActiveToggle.vue` (a toggle, no
dialog) are not dialogs with a form.

## 4. Design decisions

1. **Find the message in the page, not by field name.** The search takes the first
   element marked as refused, in page order. *Why:* the dialogs mark their fields with
   `is-invalid` and their messages with `invalid-feedback d-block` (S024 A2 made that
   uniform), except the five fixed here. So one search works for all, and the first
   message is the one the user reads first. *Rejected:* passing the field name and finding
   the field by id. Not every field has an id that matches its API name (the time field
   is `labour-hours`, the error field is `minutes`), so each dialog would need a map.
   *Also rejected:* widening the search to `.text-danger`. It would land on
   `searchError`, which is not a refusal.
2. **The trigger is the error state.** *Why:* the dialog's own checks and the server's
   refusal both set `useFormModal`'s `error`, so one `watch` covers both. *Timing facts
   the coder relies on* (BR1-05):
   - every refusal assigns a **new object**, and `send()` sets `null` first, so the watch
     fires on a second identical refusal too: no `deep`, no message comparison;
   - the watch skips `null` (`openCreate`, `openEdit` and `send` set it) and guards
     `modal.value?.` (null before mount);
   - `flush: "post"`, so the `is-invalid` class is in the DOM when the search runs;
   - a server refusal with no field fires both watches (`error` and the `error` prop).
     Two scrolls to the same element are harmless.

   *Rejected:* `FormModal` re-checking after every Save press. A server refusal arrives
   later than the press, so it would need a delay or a `MutationObserver`.
3. **The search, the scroll and the focus** (BR1-02):
   1. Take the first element in page order that matches
      `.is-invalid, .invalid-feedback.d-block, .alert-danger` inside the container.
   2. Scroll it to the middle: `scrollIntoView({ block: "center" })`, instant (no
      `behavior: "smooth"`, which would make the `toBeInViewport()` tests flaky).
      `scrollIntoView` scrolls whichever ancestor scrolls: the dialog body, or the page.
   3. Focus, always with `focus({ preventScroll: true })`:
      - an `.is-invalid` element: focus it;
      - an `.invalid-feedback`: focus the first `input, select, textarea, button` inside
        its parent element (the `.mb-3` block or `fieldset`). For a group of choice
        buttons that is the first choice;
      - the top `.alert-danger`: scroll only; there is nothing to type.

   For `minutes` both time inputs carry `is-invalid`; the first is hours, so the cursor
   goes to hours. *Why the middle:* the field's label stays in view above it; a focus on
   its own would put the field at the edge. *Rejected:* scroll only, no focus. The base
   rule asks for the cursor in the field, and a screen reader needs it (WCAG 3.3.1).
4. **One utility, two callers** (if Q1 is accepted). `FormModal` and `RaiseTicketView`
   call the same `revealError(container)`. That is the second real use that justifies a
   separate file. If Q1 is declined, the function stays inside `FormModal.vue` and
   `revealError.js` is not created.

## 5. Tests and acceptance

**Automated** (e2e, `tooling/run-e2e-tests.bat`, all three set-ups):
- **Important:** *Add labour* on a ticket. Pick, by clicking it, a person with at most one
  trade (Kannan or Ravi, `seed_e2e.py`), so that *Trade worked* is not refused first.
  Leave *Time spent* empty and press **Save**. "Time spent must be between 1 minute and
  24 hours" is on screen (`toBeInViewport`), and the cursor is in the hours field. Then
  fill the time and Save: the labour row shows. This test also clicks a name in the
  picker, which no test does today.
  - The bug shows only on the iPhone 14 set-up (390 × 664): there *Time spent* is below
    the fold. On Pixel 7 and desktop the whole dialog fits. So on `phone-webkit` the test
    first checks that the hours field is **not** in the viewport before Save. That proves
    the scroll happened.
- **Important:** every existing field-message test still passes with `toBeInViewport()`.
  A test that fails then shows a dialog that broke the rule; the fix is in the code, not
  in the test.
- A server refusal for a field low in a dialog, on the phone set-up, is on screen. The
  coder picks one (for example a Masters duplicate code, or the equipment dialog).
- Only if Q1 is accepted: on the phone set-ups, *Raise ticket* with nothing chosen,
  **Save**: "Choose how bad it is" is in the viewport.
- The frontend unit tests and the backend tests stay green.

**On a real device:**
- **Important:** on a real **iPhone** (Safari), dev server, any network: ticket ›
  *Add labour*, pick a name, leave *Time spent* empty, Save. The dialog scrolls to the
  message, and the keyboard does not hide it. *Why on a device:* iOS lays its keyboard
  over the page when the cursor moves to a field, and Playwright's WebKit has no
  keyboard. The coder adds this as a row in `device-checks.md` (account: none; where: dev
  server).

## 6. Open questions and assumptions

- **Q1. The *Raise ticket* page — answered (a) by KLA at gate A, 22-10-2026: included.** It is a page, not a dialog. On
  a phone it is long and Save is at the bottom, so a refusal for *How bad is it?* (at the
  top) is out of sight the same way. It is the operator's main screen.
  - **(a) Include it (recommended).** One more screen file and one more test. Its markup is
    already in the right form. The search moves to `utils/revealError.js` (§ 4.4).
  - **(b) Leave it to a later step.** The search stays inside `FormModal.vue`.
- **Q2. The keyboard on a phone.** Putting the cursor in a field opens the phone's
  keyboard, which covers part of the screen. Assumed acceptable: the user is about to type
  in that field. If the device check shows the message hidden under it, a follow-up drops
  the focus on phones.
- **Assumption:** after the next `sync_common.py` run, Yantra's
  `.claude/SMTW-WebApp-Base.md` has the rule; until then, the introduction above quotes it.

## Gate A — 22-10-2026 (KLA)

Approved on the light track. Q1: (a), include the *Raise ticket* page; the search lives in
`utils/revealError.js`. Coder: Sonnet.

## 7. Amendments

### A1 — dialogs are typed into only once open (user, 22-10-2026; approved: "continue S026 here, add the fix")

**Why.** A full run in parallel lanes (22-10-2026) failed three WebKit tests the same way as
CR1-02: a test types into a dialog while Bootstrap's open animation runs; at its end
(`shown.bs.modal`) the focus trap moves focus to the modal and the typed text is lost (the
S003 "engineer adds equipment" failure, S020 CR1-02, and two S020 parts tests). A busy CPU
makes the animation longer, so it fails more often.

**What.** `openDialog()` in `frontend/e2e/support/dialogs.js` returns only when the dialog is
fully open: after `.modal.show`, it waits until the modal element has the focus the trap
gives it at `shown` (or an equivalent signal of the end of the transition), so every test
that opens a dialog through it types after the trap. Tests that open a dialog without
`openDialog` (CR1-02's) use it or `expectDialogFits`. Test code only; no product change.

**Checks.** The full e2e suite in lanes, twice, with no WebKit lost-typing failure.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 five messages are not marked | minor | **Accepted** (option a): the five messages in `EquipmentFormModal` and `PeoplePanel` change to `invalid-feedback d-block`; both files added to § 3; § 4.1 corrected; `searchError` left alone and said so in § 3 |
| BR1-02 "the field nearest it" is not defined | minor | **Accepted**: the search, scroll and focus rule written out in § 4.3 (choice groups focus the first choice; the top bar scrolls only) |
| BR1-03 Q1 must be answered before coding | minor | **Accepted**: Q1 is now a decision for the user at gate A, with (a) recommended; § 3, § 4.4 and § 5 say what each answer means |
| BR1-04 no dialog needs its own refs wired | minor | **Accepted**: § 1 item 3 and § 3 trimmed; § 3 says why each ref needs nothing |
| BR1-05 timing facts | nit | **Accepted**: listed in § 4.2 (new object per refusal, skip `null`, `modal.value?.`, `flush: "post"`, instant scroll in § 4.3, double trigger harmless) |
| BR1-06 the test reproduces the bug on one set-up | nit | **Accepted**: § 5 names the iPhone 14 set-up, adds the pre-Save `not.toBeInViewport()` check there, and picks Kannan or Ravi |
| BR1-07 standards wording | nit | **Accepted**: ISO 9241-110:2020 *use error robustness*; SC 2.4.11 named in full with its level; the screen-reader point moved under SC 3.3.1 |
| BR1-08 scope A wording | nit | **Accepted**: the long sentence split; § 1 item 3 rewritten; "meets" → "reads" |
