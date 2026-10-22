```
Step: S026 — A refusal is always in view
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S026 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** CR2-01 is fixed. This round found
no new finding. CR1-03 to CR1-06 stay open for the user at gate B.

What I reviewed:
- Fix round 2: the change to `frontend/e2e/equipment.spec.js` and the "Fix round 2"
  section of `3-impl-report.md`.
- The whole of `frontend/e2e`, searched for any Playwright action that nothing awaits.
- The product files, checked for any change since round 2.

## Test results (run by the reviewer)

| Suite | Result |
|---|---|
| `tooling/run-frontend-tests.bat` | Green: 13 files, **110 passed** |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` | Green: **39 passed**, exit 0, 76 s, all three set-ups |

Why these specs: the round changed only `equipment.spec.js`. `screens.spec.js` runs with
every targeted run (README rule). The round changed no shared frontend code and no
`e2e/support/` file, so a full run was not needed. My search found no problem in any
other spec, so I ran no other spec. Backend tests were not run: no server code changed
in this step.

## Findings

None in this round.

## Status of earlier findings

| Finding | Severity | Status |
|---|---|---|
| CR1-01 strict-mode `.or()` wait on the raise page | blocker | Fixed (round 2) |
| CR1-02 Add equipment test typed during the open animation | blocker | Fixed (round 2) |
| CR1-03 server-refusal test does not prove a scroll | minor | Open. Left for the user at gate B |
| CR1-04 S017 list test depends on the 50-ticket cap | minor | Open. Left for the user at gate B |
| CR1-05 `toBeInViewport()` with no `ratio` | nit | Open. Left for the user at gate B |
| CR1-06 impl report wording | nit | Open. Left for the user at gate B |
| CR2-01 five un-awaited actions in `equipment.spec.js` | major | **Fixed.** Lines 19, 38, 81, 87 and 103 now read `await (await openDialog(page)).…fill(…)` or `.selectOption(…)`. The diff shows only these five lines changed in the round |

## Checked and found consistent

- **No un-awaited Playwright action is left in `frontend/e2e`.** I searched every spec and
  support file for `fill`, `selectOption`, `check`, `click`, `press`, `type` and
  `setInputFiles` on any locator, in statements with no `await` or `return`.
  - The only hits are `labels.spec.js:62` and `:75`. Both clicks sit inside an awaited
    `Promise.all` with `waitForEvent("page")`. That is the right pattern for a click that
    opens a new tab.
  - No continuation line (a chain that starts with `.fill(` and so on) is un-awaited.
  - Every `openDialog(page)` call is awaited, except `return openDialog(page)` in the async
    `openAction` (`support/tickets.js:89`). Its callers await it.
  - Every call of `openAction`, `expectDialogFits`, `saveDialog`, `discardDialog` and
    `openAddPart` is awaited.
  - No web-first assertion (`toBeVisible`, `toHaveText`, `toBeInViewport` and the like) is
    un-awaited. The `expect` lines with no `await` check plain values (a status code, a
    count, a box), which are synchronous.
  - The coder's search covered only `openDialog` and `openAction` results. My wider search
    confirms the result: CR2-01 was the only case.
- **No product code changed in the round.** Since round 2 (09:01), only
  `frontend/e2e/equipment.spec.js` and `3-impl-report.md` changed. The six product files
  (`revealError.js`, `FormModal.vue`, `useFormModal.js`, `RaiseTicketView.vue`,
  `EquipmentFormModal.vue`, `PeoplePanel.vue`) were last written at 07:41. Their diff is
  the one round 1 checked.
- **Impl report.** "Fix round 2" names the finding, the five lines, the file and the test
  runs. It follows scope A.
- **Manual checks.** The `## Manual checks` section still carries every important check
  of the brief: four `[auto]` rows with their tests, and the unticked iPhone row that
  points to `device-checks.md` row 12.
- **Track.** It stays light: frontend and test code only, no migration, no RBAC change,
  no new dependency.

## For the user's manual browser check

- **Device row 12 (real iPhone, Safari).** Open a ticket and press *Add labour*. Tap a
  name, leave *Time spent* empty and press **Save**. The dialog scrolls to the message,
  and the cursor is in the hours box. Say whether the keyboard hides the message (Q2).
- Optional, on the dev server at phone width: open *Masters › Team* and edit a person
  with a site row. Make a row save fail. The red line under the row looks as before, and
  the dialog scrolls to it.
- Decide CR1-03 to CR1-06 at gate B.
