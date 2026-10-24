```
Step: S045 — The known flaky tests made steady
Doc: impl report
Author: Coder
Date: 25-10-2026
Track: fix
```

# S045 — Impl report

Result: five flaky tests are steady in the repeat runs, and a guard stops phone-webkit when its window is narrower than the device. No app code changed. On this PC (Windows scale 125 %) the guard stops every phone-webkit test, as expected.

## 1. What was built, cause and fix per item

| # | Test | Cause confirmed in the code | Fix |
|---|---|---|---|
| 1 | `masters.spec.js` "a deactivated mode is hidden unless Show inactive…" | No wait for the dialog before *Deactivate*, *Yes* and *Reactivate*; the buttons were found on the page and clicked at once. *Yes* is an inline confirm that appears after *Deactivate* is clicked. | `openDialog(page)` before each click; click inside the dialog; `expect(yes).toBeVisible()` before *Yes*. |
| 2 | `tickets-raise.spec.js` "S018 A1: Already fixed with a start time…" | Bootstrap sets `:root { scroll-behavior: smooth }` (`bootstrap.css` line 192, no reduced-motion preference). Each `fill` scrolls with an animation, so the Save button moves. `scrollIntoViewIfNeeded` waits for the button to stand still and timed out on WebKit under load. I did not see it fail in 10 idle runs; the cause is from the CSS and the Playwright behaviour, not from a red run. | `el.scrollIntoView({ block: "center", behavior: "instant" })`, which ends any running animation, then `expect(...).toBeInViewport()`. No sleep. |
| 3 | `tickets-parts.spec.js` "S020: technician adds a part line the short way…" | `PartsPanel.vue` renders the *Yes* button in a `v-if` block of the line; the ticket reloads after each save, so the element the test held could be replaced. The `line` locator was used for *Yes* straight after the click on *Remove*. I did not see it fail in 10 idle runs; the cause is read from the code. | Locate *Yes* afresh in the line, `expect(yes).toBeVisible()`, then click. |
| 4 | `tickets-work.spec.js` "S019: the Overdue filter…" | `seed_e2e.py` writes `planned_date` as today minus 1 day when the e2e database is built; the test computed `istDay(-1)` at run time, so a run after midnight expected the wrong day. | The test reads the seeded ticket's `planned_date` from `GET /api/tickets?state=overdue` and expects the badge and the line from it. It also checks the date is before today. |
| 5 | `test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed` | `do_POST` answered 307 without reading the request body; Windows aborts the socket (WinError 10053) while the client still sends. | `self.rfile.read(Content-Length)` before `send_response(307)`. |
| 6 | Guard, all phone-webkit tests | Windows display scale above 100 % narrows the WebKit window (312 px instead of 390). | An auto fixture `windowWidthGuard` in `e2e/support/test.js`. |

## 2. How the guard works

For a WebKit project with a `viewport` width, the fixture sets a page with a `width=device-width` viewport meta and reads `window.innerWidth`. `about:blank` and a plain document report 784 px, so a device-width page is needed. If the width differs from the project's, the test fails at once with: "The phone-webkit window is 312 px wide, not 390. Set Windows display scale to 100 % and sign in again." Chromium projects skip the check.

## 3. Proof

- #5: 20 runs in a loop with the fix: 20 passed, 0 failed. Same loop with the fix removed: 14 passed, 6 failed. This confirms the cause.
- #4 red: with the expected day set to `istDay(-2)`, the test fails ("Expected: Overdue since 23-10, Received: Overdue since 24-10"). Restored: `--repeat-each=10` on desktop-chromium, 10 passed.
- #1: `--repeat-each=10`, phone-chromium, `E2E_LANES=1`: 10 passed.
- #2: `--repeat-each=10`, phone-webkit, `E2E_LANES=1`: 10 passed (run before the guard was added, on this 312 px window).
- #3: same, phone-webkit: 10 passed.
- #6: on this PC, phone-webkit stops with the message above; phone-chromium and desktop-chromium run the same test and pass.
- Final runs:
  - `YANTRA_TEST_RUN=s045c1 tooling/run-tests.bat`: backend 2964 passed, frontend 168 passed, deps 42 passed, tooling 115 passed. All green.
  - Full e2e suite (6 lanes, 441 tests): 290 passed, 4 skipped, 147 failed. All 147 failures are phone-webkit tests (147 per project) and each one shows the guard message (312 px, not 390). phone-chromium and desktop-chromium: 0 failures. Log: `scratch/s045-e2e-full.log`.

## 4. Files touched (6, plus the step files)

- `backend/tests/test_alerts.py`: read the request body in the test server (#5).
- `frontend/e2e/masters.spec.js`: dialog waits (#1). The file also holds S037 changes by others.
- `frontend/e2e/tickets-raise.spec.js`: instant scroll (#2).
- `frontend/e2e/tickets-parts.spec.js`: fresh *Yes* locator (#3).
- `frontend/e2e/tickets-work.spec.js`: planned date from the API (#4). Imports `apiAs`.
- `frontend/e2e/support/test.js`: the guard (#6).
- `docs/steps/S045-flaky-tests/1-brief.md`: Status set to In code review.
- `docs/steps/S045-flaky-tests/3-impl-report.md`: this report.

## 5. Decisions taken

- #4: fixed in the test (read the date), not in `seed_e2e.py`; the brief allowed either.
- #6: the guard applies to any WebKit project with a viewport width, not only the name `phone-webkit`. It runs in every WebKit test, costing one `setContent` per test.
- #6: the guard fails each test, not the whole run; "stops at once" means every phone-webkit test fails in about a second with the message.
- #2 and #3: the causes could not be reproduced idle (10 of 10 passed before and after), so their proof is the repeat runs plus the mechanism read from the code. A load-dependent flake can still show again.

## 6. Not done, deferred or assumed

- phone-webkit could not be run in the final full suite on this PC. It needs a host at 100 % scale before a release.
- The 4 skipped tests are not from this step.
- `readings.spec.js:362` also uses `scrollIntoViewIfNeeded`; left alone (not in the brief, S040's file).

## Docs updated

None, because the change is test-only.

## Manual checks

None in the brief.
- Not a check of the brief, for the user: run the full e2e suite once on a host at 100 % display scale to see phone-webkit pass.
