```
Step: S026 — A refusal is always in view
Doc: impl-report
Author: Coder (Sonnet)
Date: 22-10-2026
```

# S026 — Impl report

## 1. What was built

- When a save is refused, the dialog scrolls the first message to the middle of its body and puts the cursor in the field. This covers the dialog's own checks and the server's refusals, and the red bar at the top (scroll only).
- The *Raise ticket* page does the same on its form (Q1 answer (a)).
- The five unmarked messages in the equipment and Team dialogs now use the same mark as every other message.
- `expectFieldMessage` now asks for "on screen" (`toBeInViewport`), not only "visible". Four new browser tests: the labour bug, a server refusal low in a dialog, and the raise page.

## 2. How it works

- `frontend/src/utils/revealError.js`, `revealError(container)`: takes the first element in page order matching `.is-invalid, .invalid-feedback.d-block, .alert-danger`, and scrolls it to the middle (`scrollIntoView({ block: "center" })`, instant). Then it focuses with `preventScroll: true`:
  - an `.is-invalid` element: itself;
  - an `.invalid-feedback`: the first `input, select, textarea, button` in its parent;
  - an `.alert-danger`: nothing (scroll only).
- `FormModal.vue` exposes `revealError()` (the utility on its `.modal-body`). It also watches its `error` prop (the top bar) with `flush: "post"` and calls it when the prop becomes a message.
- `useFormModal.js` watches its `error` ref (`flush: "post"`), skips `null`, and calls `modal.value?.revealError()`. Every refusal assigns a new object and `send()` clears to `null` first, so a second identical refusal fires again. No `deep`.
- `RaiseTicketView.vue`: the `<form>` has a ref, and a post-flush watch on `[fieldErrors, formError]` calls `revealError(formEl.value)` when either holds a message. `save()` assigns a new `fieldErrors` object per refusal; reset to `{}` is skipped by the check.

## 3. Files touched (12)

| File | Change |
|---|---|
| `frontend/src/utils/revealError.js` (new) | the search, scroll and focus |
| `frontend/src/components/FormModal.vue` | `reveal()`, the `error` prop watch, exposes `revealError` |
| `frontend/src/composables/useFormModal.js` | the `error` watch |
| `frontend/src/views/RaiseTicketView.vue` | form ref, watch, import |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | `level`, `parent_id` messages: `invalid-feedback d-block` |
| `frontend/src/views/masters/PeoplePanel.vue` | `employment`, read-only `username`, and both `rowError` messages: `invalid-feedback d-block` |
| `frontend/e2e/support/dialogs.js` | `expectFieldMessage` uses `toBeInViewport()`; comment says it fits a page too |
| `frontend/e2e/tickets-work.spec.js` | the labour test |
| `frontend/e2e/tickets-raise.spec.js` | the raise-page test |
| `frontend/e2e/equipment.spec.js` | the server-refusal test |
| `docs/steps/device-checks.md` | row 12 (real iPhone) |
| `docs/steps/README.md` and the brief | S026 status row / header: In code review |

No server code changed, so the backend tests were not run.

## 4. The 21 dialogs and the Raise ticket page

All 21 use `FormModal` and `useFormModal` (or, for the two document dialogs, `FormModal` with a `modalError`, and `EditTicketDialog` / `LabourPanel` with `useFormModal`'s `error`). I checked, by reading each file, that its messages carry `is-invalid` on the field and `invalid-feedback d-block` on the message (or reach the top bar through the `error` prop). Done to each:

| # | Dialog | Done |
|---|---|---|
| 1-10 | Masters: Sites, Units, Equipment classes, Equipment types, Manufacturers, Models, Trades, Failure modes, Failure causes, Maintenance actions (through `useMasterForm.js`) | Nothing. They get the behaviour from `useFormModal`. Covered by the existing Masters refusal tests, now `toBeInViewport` |
| 11 | People (Team) | Markup: `employment`, read-only `username` and the two `rowError` messages (site row and no-row case) changed to `invalid-feedback d-block`. `rowError` already goes into `useFormModal`'s `error`, so the watch covers it |
| 12 | `EquipmentFormModal` | Markup: `level` and `parent_id` messages changed. New e2e test: server refusal on `year`, low in the dialog |
| 13 | `EquipmentMoveModal` | Nothing. `searchError` (`text-danger`) left alone as the brief says |
| 14 | `EquipmentStatusModal` | Nothing |
| 15 | `DocumentUploadModal` | Nothing. `fileError` is not a refusal (Save is disabled while it shows) |
| 16 | `DocumentTitleModal` | Nothing |
| 17 | `LabourPanel` | Nothing in the file. `tradesError` reaches the top bar through the `error` prop. New e2e test reproduces the bug |
| 18 | `AssignDialog` | Nothing |
| 19 | `EditTicketDialog` | Nothing. `loadError` goes through the `error` prop |
| 20 | `MoveDialog` (with `EventFields`, `StartedAtFields`, `ScheduleFields`) | Nothing. `loadError` goes through the `error` prop; its field messages were already marked |
| 21 | `RegradeDialog` | Nothing |

`PartsPanel` (not one of the 21) was not edited; it gets the behaviour through `useFormModal`.

**Raise ticket page:** `RaiseTicketView.vue` changed as in § 2. Its messages were already in the right form.

## 5. Decisions taken

- `FormModal` has one internal `reveal()` used by the prop watch and exposed as `revealError`, so `useFormModal` calls a method on the modal and does not reach into its DOM.
- The labour test raises its ticket on the **mill** (`seed.mcc1Mill`, supervisor), not the extruder. In the first run the new test's three tickets (one per project) pushed the extruder's open-tickets list past the API's 50-item cap, and the existing test "raise from the Tickets list" (S017) then could not find its ticket in that warning list. That was a limit of the shared test database, not of the page. It also means the raise page's open-tickets warning silently shows only the first 50 tickets; not touched here (see § 6).
- The server-refusal test uses the Add equipment dialog's `year` (1800); it checks one visible message, in view, with the cursor in the field.
- The raise-page test also checks the second refusal ("Describe the problem, or pick a symptom") with the cursor in the description.

## 6. Not done, deferred or assumed

- No existing field-message test failed under `toBeInViewport()`, so no dialog needed a code fix beyond the five messages.
- The warning list on the raise page ("Already reported on this machine") shows at most 50 tickets (API default `per_page`). Not a real-life problem for a machine, but worth knowing; not changed.
- Q2 (the phone keyboard over the message) is assumed acceptable until the device check (row 12) says otherwise.
- The e2e `phone-webkit` set-up has no keyboard, so the iPhone keyboard question is for the device.

## 7. Results

- Frontend unit tests: 13 files, 110 tests passed.
- `npx vite build`: built.
- `tooling/run-e2e-tests.bat`: **189 passed** (3 set-ups), exit 0. The first run had 1 failure, explained in § 5 and fixed in the test; the second run is the one reported.
- Backend tests: not run (no server change).

## Fix round 1 and A1

**Result: both blockers are closed, and A1 is built. The full e2e suite passed twice: 189 passed, 189 passed (3 set-ups, 6 lanes), with no WebKit lost-typing failure.**

### Findings

| Finding | Answer |
|---|---|
| CR1-01 blocker | **Fixed.** `tickets-raise.spec.js` waits for one element: `expect(page.getByLabel(/What is wrong\?/)).toBeVisible()`. The working tree already held this line when this round started. |
| CR1-02 blocker | **Fixed.** The Add equipment test calls `expectDialogFits(page)` after opening the dialog, and checks the message text `/Year must be between/`. Both were already in the tree. `expectDialogFits` now also waits until the dialog is fully open (A1). |
| CR1-03, CR1-04, CR1-05, CR1-06 | **Not touched.** The user decides them at gate B. |

### A1: a dialog is typed into only once it is open

- `openDialog(page)` in `frontend/e2e/support/dialogs.js` is now `async`. It waits for `.modal.show`, then waits until `document.activeElement` is inside the modal. Bootstrap's focus trap moves focus there at `shown.bs.modal`, the end of the fade. It returns the dialog locator.
- `expectDialogFits` calls it, so it waits out the transition too.
- Every call site now awaits it: `equipment`, `tickets-work`, `tickets-parts` specs, and `support/tickets.js` (`openAction`).
- Tests that opened a dialog with a raw `page.locator(".modal.show")` and then typed now use `await openDialog(page)`: `masters.spec.js` (five places), `tickets-work.spec.js` (labour, one dialog at line 271, the event-time and Ravi picks). The first full run showed why: the masters test "a press mode labelled like a General one is refused" lost its *Code* fill on WebKit (HTTP 400 instead of 409).
- `saveDialog` (`support/tickets.js`) uses a plain locator and not `openDialog`. In the S019 schedule test the focus is on `<body>` at that point (a clicked "Change" button was removed), so the focus wait would time out. The dialog is open already there.
- Decision: the end-of-transition signal is "focus inside the modal". It needs no change to the product code.

### Files

- `frontend/e2e/support/dialogs.js`, `frontend/e2e/support/tickets.js`: A1 helpers.
- `frontend/e2e/equipment.spec.js`, `tickets-work.spec.js`, `tickets-parts.spec.js`, `masters.spec.js`: awaits and `openDialog` use.
- Note: commit `c7e6396` (the user's lane-runner commit) already contains S026's earlier edits to `dialogs.js` and the specs `equipment`, `tickets-raise` and `tickets-work`. The working-tree changes of this round come on top of it.
- No product code changed.

### Results

- `tooling/run-frontend-tests.bat`: 13 files, 110 tests passed.
- `tooling/run-e2e-tests.bat`, full, run twice in a row: **189 passed** and **189 passed**, exit 0. A first attempt with a broken edit (missed `await` in five lines) and a second one (the `saveDialog` focus wait, and the masters test) failed; both were test-code faults found by the runs and fixed above.
- Backend tests not run (no server change).
- Manual checks: unchanged. The `[auto]` rows of the server-refusal and raise-page checks now rest on two stable runs.

## Fix round 2

### Findings

- **CR2-01 (major): Fixed.** Five actions in `frontend/e2e/equipment.spec.js` (lines 19, 38, 81, 87, 103) ran `(await openDialog(page)).getByLabel(...).fill(...)` or `.selectOption(...)` without an outer `await`. Each now starts with `await (await openDialog(page))`, as in `masters.spec.js:144`. A search of all of `frontend/e2e` for the same pattern (`openDialog` or `openAction` result used without `await`) found no other case.

### Files

- `frontend/e2e/equipment.spec.js`: five added `await`s. No product code changed.

### Results

- `tooling/run-frontend-tests.bat`: 13 files, 110 tests passed.
- `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js`: 39 passed, all three set-ups. These are the only spec files changed, plus `screens.spec.js` as the README asks.
- Backend tests not run (no server change). CR1-03 to CR1-06 left alone, as instructed.

## Manual checks

- [auto] Add labour with no time spent: the message is on screen and the cursor is in the hours field; on the iPhone 14 set-up the hours field is first off screen. After filling the time, the labour row shows — `frontend/e2e/tickets-work.spec.js::S026: Add labour with no time spent scrolls the dialog to the message and puts the cursor in the hours field`
- [auto] Every existing field-message test passes with `toBeInViewport()` — `frontend/e2e/support/dialogs.js::expectFieldMessage` (the whole run: 189 passed)
- [auto] A server refusal for a field low in a dialog is on screen on the phone set-ups — `frontend/e2e/equipment.spec.js::S026: the server's refusal of a field at the bottom of the Add equipment dialog is on screen`
- [auto] Raise ticket with nothing chosen: "Choose how bad it is" is in view — `frontend/e2e/tickets-raise.spec.js::S026: Save with nothing chosen scrolls the raise form to the first message`
- [auto] Frontend unit tests green (110)
- [ ] **Important:** on a real iPhone (Safari), dev server: ticket › Add labour, pick a name, leave Time spent empty, Save. The dialog scrolls to the message and the keyboard does not hide it (`device-checks.md` row 12)
