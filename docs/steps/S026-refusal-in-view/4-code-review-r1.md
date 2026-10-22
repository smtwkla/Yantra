```
Step: S026 — A refusal is always in view
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S026 — Code review, round 1

**Verdict: two `blocker` findings are open (CR1-01, CR1-02).** My e2e run was red: two of
the new S026 tests failed on `phone-webkit`. In both, the test is at fault, not the product
code. The product change itself follows the brief.

Reviewed: the working-tree diff against `b6b8dfb`, limited to the 12 files in the impl
report. The S027 files in the tree are not part of this review.

## Test results (run by the reviewer)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | Green. Frontend unit tests: 13 files, **110 passed**. Backend: **2003 passed**. Tooling: 42 + 60 passed |
| `tooling/run-e2e-tests.bat` (all three set-ups) | **Red: 187 passed, 2 failed**, exit 1. Failed: `[phone-webkit] equipment.spec.js:42` (S026 server refusal) and `[phone-webkit] tickets-raise.spec.js:87` (S026 raise page) |
| The two failing tests alone, `--project=phone-webkit -g S026 --repeat-each=4` | 8 passed. They pass on their own and fail in the full run: both are races (below) |

The impl report says 189 passed. That was a lucky run, not a stable one.

## Findings

### CR1-01 — blocker — `frontend/e2e/tickets-raise.spec.js:92`

**Problem.** The wait before Save is
`expect(page.getByText("Already reported on this machine:").or(page.getByLabel(/What is wrong\?/))).toBeVisible()`.
When both are on the page, `.or()` resolves to two elements, and `toBeVisible()` fails in
strict mode.

**Failure scenario.** In the full run, other tests have left open tickets on the extruder.
If the open-tickets list has loaded by the time this line runs, both the warning and the
*What is wrong?* box are visible. The test then fails with "strict mode violation …
resolved to 2 elements". That is what happened in my run. When run alone, the extruder has
no open tickets, so only the text box shows and the test passes. The coder's green run had
the list arrive a moment later.

**Fix.** Wait for one element: `await expect(page.getByLabel(/What is wrong\?/)).toBeVisible()`.
If the test should also wait for the list, add `.first()` to the `.or()` locator.

### CR1-02 — blocker — `frontend/e2e/equipment.spec.js:45-51`

**Problem.** The test fills the Add equipment dialog while Bootstrap's open animation is
still running. `openDialog(page)` matches `.modal.show`, and Bootstrap adds `show` when the
fade starts. At the end of the fade (`shown.bs.modal`), Bootstrap's focus trap moves focus
to the modal element. A `fill()` in progress at that moment loses its text. The test also
skips `expectDialogFits(page)`, which the S024 rules ask of every flow test and which waits
out the open animation (its own comment says so).

**Failure scenario.** Seen in my run (trace kept under
`scratch/e2e-report/results/equipment-S026-the-server--a8382-…-phone-webkit/`). The POST
body was `{"name": "", "year": 1800, …}`, because the *Name* fill was lost. The server
refused `name` ("Name is required"), not `year`. The dialog correctly scrolled to *Name*
and focused it, and the test then failed at
`expect(dialog.getByLabel("Year")).toBeFocused()`. So the S026 code worked, and the test
checked the wrong field.

**Fix.**
- Call `await expectDialogFits(page)` right after clicking **Add equipment**, as the other
  dialog tests do.
- Check the message text, not only that one message exists, e.g.
  `expectFieldMessage(dialog, /year/i)` with the server's real wording. A lost fill then
  fails with a clear message.
- If `expectDialogFits` can pass before `shown`, wait for the focus trap itself:
  `await expect(page.locator(".modal.show")).toBeFocused()`.

The S003 test "engineer adds equipment from the list" (`equipment.spec.js:58`) fills the
same dialog the same way. It was there before S026 and is outside this step. It is
noted here so the same fix can be applied to it later.

### CR1-03 — minor — `frontend/e2e/equipment.spec.js:51-55`

**Problem.** The server-refusal test does not prove that anything scrolled.
`fill("1800")` makes Playwright scroll *Year* into view, so its message is already on
screen before Save. In WebKit, clicking a button does not move focus, so *Year* is still
focused after Save. On `phone-webkit`, the test would pass with the S026 code removed.

**Failure scenario.** A later change breaks the `useFormModal` watch, which is the
server-refusal path. The labour test does not catch it, because it covers only the
dialog's own check. On WebKit this test does not catch it either. On Chromium only the
`toBeFocused` check would catch it, because there the click moves focus to Save.

**Fix.** Do it the way the labour test does. After the fills, scroll the dialog body to the
top (`dialog.locator(".modal-body").evaluate((b) => { b.scrollTop = 0; })`), then move focus
off the field. On the phone set-ups, check that *Year* is `not.toBeInViewport()` before Save.

### CR1-04 — minor — `frontend/e2e/tickets-work.spec.js:124-128` (the move to the mill) and `frontend/e2e/tickets-raise.spec.js:52-63`

**The decision is sound as a test fix. It leaves a fragile test in place.**

- **Why the S017 test failed.** It raises an `initial` ticket on the extruder and expects it
  in the raise page's "Already reported" list. That list comes from
  `GET /api/tickets?equipment_id=…&state=open`. The API sorts open tickets by intensity,
  critical first (`tickets.py:540`), and returns at most 50. Every more severe open ticket
  on the extruder, from any test in any of the three set-ups, pushes the `initial` ticket
  further down. The labour test's three critical tickets pushed it past 50.
- **What the move hides.** The S017 test still depends on fewer than 50 more severe open
  tickets on a shared machine. The next step that raises tickets on the extruder in its
  tests (S027, for example) will break it again, in a test that step did not touch.
- **The product side.** The raise page silently drops tickets past the 50th, with no
  "and N more" line, although the response carries `total`. On a real machine 50 open
  tickets is not realistic, so this is not a defect today. The report says so (§ 6).
- **Fix.**
  - Give the S017 list test its own seeded machine, one that no other test raises
    tickets on.
  - Or change its assertion so it does not depend on the list's length.
  - Add an "and N more" line on the raise page to the Queued table, if the user wants it.

### CR1-05 — nit — `frontend/e2e/support/dialogs.js:58`

`toBeInViewport()` passes when any part of the element is on screen (ratio > 0). A message
cut off at the bottom edge of the dialog body, with one pixel row showing, passes. That is
the same kind of fault as the labour bug. Consider `toBeInViewport({ ratio: 1 })`: the
messages are short, and after the centring scroll they are fully on screen. The brief
asked for plain `toBeInViewport()`, so the current code is not a departure.

### CR1-06 — nit — `docs/steps/S026-refusal-in-view/3-impl-report.md` (scope A)

- § 1: "Four new browser tests" is followed by three. There are three tests, each run on
  three set-ups.
- § 4, lead-in: the bracket "(or, for the two document dialogs, FormModal with a
  `modalError`, and `EditTicketDialog` / `LabourPanel` with `useFormModal`'s `error`)" is
  hard to follow, and reads as if some dialogs do not use `useFormModal`. All 21 do; say
  that in one sentence.
- § 7: after the fixes, report the real e2e result and the backend run (2003 passed today).

## Checked and found consistent

- **§ 4.3 search order.** `revealError.js` takes the first match of
  `.is-invalid, .invalid-feedback.d-block, .alert-danger` in DOM order inside the given
  container. A null container or no match does nothing.
- **Instant scroll.** `scrollIntoView({ block: "center" })` is called with no `behavior`.
- **Focus per element kind.** An `.is-invalid` element focuses itself. An `.invalid-feedback`
  focuses the first `input, select, textarea, button` in its parent element. An
  `.alert-danger` is scrolled to only. Every focus call uses `preventScroll: true`.
- **Labour fields.** For `minutes`, hours comes before minutes in the DOM, so the cursor
  goes to hours. The labour test asserts this.
- **Raise page.** For the intensity refusal, the parent is the `<fieldset>`, so focus goes
  to the first choice button. That opens no keyboard.
- **Team dialog.** The read-only `username` message has no control in its parent, so it
  is scrolled to only. That is right: there is nothing to type.
- **§ 4.2 watch timing.**
  - `useFormModal`'s watch skips `null`, uses `modal.value?.`, and runs with
    `flush: "post"`.
  - `send()` sets `null` before the request.
  - Every refusal assigns a new object: `LabourPanel`, `AssignDialog`, `MoveDialog`,
    `RegradeDialog`, the equipment and move dialogs' load errors, and `send()`'s catch.
    So a second identical refusal fires again.
  - `FormModal`'s watch on the `error` prop also runs post flush.
  - A refusal with no field fires both watches and scrolls twice to the same alert. That
    is harmless.
- **Raise page watch.** `save()` clears `fieldErrors` and `formError` first. Own checks then
  assign a new object, and server refusals a new object or a new string. The reset to `{}`
  is skipped by the length check. Both alerts that can hold a refusal (`repeat_of_id`,
  `formError`) and every field are inside `formEl`.
- **All 21 dialogs and the Raise page are accounted for.** I confirmed by `grep` that every
  `<FormModal>` user takes `modal` from `useFormModal`, including both document dialogs and
  `PartsPanel`. Its refusals reach `error` or the `error` prop. `tradesError` and `loadError`
  go through the prop. `searchError`, `PhotoViewer` and `ActiveToggle` were left alone, as
  the brief says.
- **Other `alert-danger` boxes inside dialogs.** Two Team dialog alerts sit mid-form:
  `trade_ids`, and `sites` when there is no row error. Both are refusals, so the search
  finding them is right. As § 4.3 says, they are scrolled to only.
- **The five re-marked messages look as before.** In Bootstrap 5.3, `.invalid-feedback`
  uses `--bs-form-invalid-color` (the same red as `text-danger`) and `font-size: .875em`
  (the same as `small`). The only change is `margin-top: .25rem`. The site-row message
  already had `mt-1`, which is the same margin. `d-block` keeps them shown without the
  sibling rule, as S024 A2 requires.
- **Labour reproduction.** On `phone-webkit` the test asserts *Hours* is
  `not.toBeInViewport()` before Save, then the message in view, *Hours* focused and in view.
  It passed on all three set-ups in my run, so the scroll is proven there. It clicks
  Kannan in the picker, calls `expectDialogFits`, and then saves and checks the labour row.
- **`expectFieldMessage`** now uses `toBeInViewport()`. Every existing field-message test
  passed with it in my run.
- **Scope.** No server change. No wording or layout change beyond the brief.
  `PartsPanel.vue` was not edited. `revealError.js` exists because Q1 was answered (a),
  as § 4.4 says. The one unplanned choice, the private `reveal()` in `FormModal` exposed
  as `revealError`, is listed in "Decisions taken".
- **Track.** It stays light: 12 files, frontend and tests only, no migration, no
  RBAC or auth code, no new dependency.
- **Layers.** Plain DOM in a utility. No business rule moved into Vue. No duplicate
  of an existing helper (`grep` for `scrollIntoView` found no earlier one).
- **Code comments** say why: instant scroll, `preventScroll`, post flush.
- **Screen text (scope B).** No user-visible text was added or changed.
- **Manual checks.** The report's `## Manual checks` carries every important check
  of the brief. The real-iPhone check is an unticked box and row 12 in
  `device-checks.md`. Two `[auto]` rows rest on the tests in CR1-01 and CR1-02: the
  server-refusal check and the raise-page check. They stand only once those tests pass
  reliably.
- **Brief header and README row.** Both show `In code review` with the gate A answer.

## For the user's manual browser check

- **Device row 12 (real iPhone, Safari).** Ticket › *Add labour*, tap a name, leave
  *Time spent* empty, **Save**. The dialog scrolls to the message and the cursor is in the
  hours box. Say whether the keyboard hides the message (Q2).
- Optional, on the dev server, phone width: *Masters › Team*, edit a person with a site
  row, and cause a refused row save. The red line under the row looks as it did before
  (same red, same size), and the dialog scrolls to it.
