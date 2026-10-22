```
Step: S026 — A refusal is always in view
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S026 — Code review, round 2

**Verdict: one `major` finding is open (CR2-01). No blocker is open.** CR1-01 and CR1-02
are fixed. A1 is built as the amendment says, and its focus wait is sound. But the fix
round left five browser-test actions in `equipment.spec.js` that nothing awaits. That
is the same kind of race A1 is meant to remove.

What I reviewed:
- The change from `b6b8dfb`, limited to S026's files (impl report § 3 and "Fix round 1 and
  A1"). This includes the S026 parts of commit `c7e6396`.
- The lane-runner files of `c7e6396` (`stack.js`, `playwright*.config.js`, `tooling/e2e/`)
  belong to the user's own commit. They are not part of this review.

## Test results (run by the reviewer)

| Suite | Result |
|---|---|
| `tooling/run-frontend-tests.bat` | Green: 13 files, **110 passed** |
| `tooling/run-e2e-tests.bat`, **full** suite, 6 lanes, all three set-ups | Green: **189 passed**, exit 0, 195 s. No WebKit failure |

Why the full suite: the round changed `e2e/support/` (`dialogs.js`, `tickets.js`). The
README rule asks for a full run then. The frontend unit tests ran at the same time as the
e2e run, so the run was also under extra CPU load. The backend tests were not run: no
server code changed in this step.

## Findings

### CR2-01 — major — `frontend/e2e/equipment.spec.js:19, 38, 81, 87, 103`

**Problem.** Five lines read like this:

```js
(await openDialog(page)).getByLabel("Name").fill(maker);
```

The `await` applies only to `openDialog()`. Nothing awaits the `fill()` or
`selectOption()` itself, so the promise floats. The next line (`saveDialog`, or
`expectDialogFits` on line 38) starts while the action may still run. Before this round
these lines were `await openDialog(page).getByLabel(…).fill(…)`, which awaited the
action. The impl report says a "missed `await` in five lines" was fixed. The parentheses
were added, but the outer `await` was not.

**Failure scenario.**
- In the S012 test (line 19), `saveDialog` checks the Save label and clicks it. Under
  load, the click can reach the page before `fill(maker)` has typed the name. The server
  then refuses "Name is required". The test fails at the row check, in a test S026 did not
  mean to change.
- The same race applies to the move (line 81), the status (line 87) and the document
  title (line 103). The title test then fails at `toContainText("… 2026 edition")`.
- If a floating action fails, its error is reported apart from its line, or after the
  test has moved on. That makes a failure hard to read.
- Both coder runs and my run were green, so today the action usually wins the race. That
  is luck, not order. A1's own check is "no lost-typing failure", and these lines can
  still lose typing.

**Fix.** Add the outer `await` on each of the five lines, as `masters.spec.js:144` and
`tickets-work.spec.js:387` already do:
`await (await openDialog(page)).getByLabel("Name").fill(maker);`
Or split each line into `const d = await openDialog(page);` and `await d.getByLabel(…).fill(…);`.

## Status of round 1 findings

| Finding | Severity | Status |
|---|---|---|
| CR1-01 strict-mode `.or()` wait on the raise page | blocker | **Fixed.** `tickets-raise.spec.js:92` waits for one element, `getByLabel(/What is wrong\?/)`. It was already fixed in `c7e6396`, as the coder says |
| CR1-02 Add equipment test typed during the open animation | blocker | **Fixed.** The test calls `expectDialogFits(page)` after the click, then `await openDialog(page)`, and checks `/Year must be between/`. The first two were already in `c7e6396`; the `await` came with A1 |
| CR1-03 server-refusal test does not prove a scroll | minor | Open. Left for the user at gate B |
| CR1-04 S017 list test depends on the 50-ticket cap | minor | Open. Left for the user at gate B |
| CR1-05 `toBeInViewport()` with no `ratio` | nit | Open. Left for the user at gate B |
| CR1-06 impl report wording | nit | Open. Left for the user at gate B |

## Checked and found consistent

- **No product code changed in the round.** The six product files (`revealError.js`,
  `FormModal.vue`, `useFormModal.js`, `RaiseTicketView.vue`, `EquipmentFormModal.vue`,
  `PeoplePanel.vue`) were last written at 07:41. Round 1 was written at 08:15. Their
  diff is the one round 1 checked.
- **A1: the focus wait is a reliable end-of-opening signal.**
  - Bootstrap 5.3 calls `_focustrap.activate()` in `transitionComplete`, just before
    `shown.bs.modal`. With `autofocus: true` it focuses the `.modal` element. After that,
    no focus move comes from Bootstrap, so typing is safe.
  - Before that moment the focus is outside the modal. It is on the clicked button
    (Chromium) or on `<body>` (WebKit). No app code focuses a field on open: I found no
    `autofocus` and no `focus()` call outside `FormModal`'s confirm bar and
    `revealError`. So the wait cannot pass early.
  - `openDialog` first checks that the dialog is visible, then polls
    `modal.contains(document.activeElement)` for up to 5 s. The fade is 300 ms, so 5 s
    leaves room under load.
  - `expectDialogFits` calls `openDialog`, so every flow test that checks fit also waits
    out the opening. `openAction` calls both. The second call passes at once, because the
    focus is still in the modal.
- **A1: the `saveDialog` exception is sound.** `saveDialog` types nothing. It checks the
  Save label and clicks. A click is not lost to the focus trap: only typed text is. Every
  test types its input before it calls `saveDialog`, through a dialog it got from
  `openDialog`, `openAction` or `expectDialogFits`. So the exception leaves no
  lost-typing window. A focus wait there would wrongly time out once the focus has left
  the modal. In the S019 test, a likely cause is `revealError` focusing the remark box,
  which then disappears when the reason changes to "slot". The report names a different
  cause (a removed "Change" button), but either way the exception is right.
- **A1: no raw locator is typed into.** The only raw `.modal.show` locators left are
  `masters.spec.js:68`, a click on **Yes** after `expectDialogFits`, and the `toHaveCount(0)`
  checks. Neither types.
- **A1: the checks.** The amendment asks for the full suite in lanes, twice, with no
  WebKit lost-typing failure. The coder reports two green runs. My run makes a third. The
  green runs do not cover CR2-01: there the action usually wins the race.
- **The five masters and four tickets-work changes** await `openDialog` correctly.
  `tickets-parts.spec.js` (`openAddPart`, `discardDialog`, the change dialog) awaits it too.
- **Scope.** The round touched test code and docs only, as A1 says. The brief header and
  the README row show the round. Device row 12 is unchanged.
- **Manual checks.** The `## Manual checks` section still carries every important check of
  the brief. The two `[auto]` rows that rested on CR1-01 and CR1-02 now rest on passing
  runs.
- **Track.** It stays light: frontend and test code only, no migration, no RBAC change and
  no new dependency.

## For the user's manual browser check

- **Device row 12 (real iPhone, Safari).** Open a ticket, press *Add labour*, tap a name,
  leave *Time spent* empty and press **Save**. The dialog scrolls to the message, and the
  cursor is in the hours box. Say whether the keyboard hides the message (Q2).
- Optional, on the dev server at phone width: open *Masters › Team*, edit a person with a
  site row, and make a row save fail. The red line under the row looks as before, and
  the dialog scrolls to it.
