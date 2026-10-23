```
Step: S029 — Ticket light on the equipment list
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 23-10-2026
```

# S029 — Code review r2

**Verdict: no blocker or major finding is open.** CR1-01 is fixed. The fix round brings in no new finding. Every suite is green, and the targeted e2e run passes on the three projects.

Scope: a verify round (README § round 2 and later). I re-read the fix round's diff only: `listUrl()` and `canSeeTickets` in `frontend/src/views/EquipmentView.vue`, and the S029 block of `frontend/e2e/equipment.spec.js`. The uncommitted S028 changes in the working tree are not reviewed here.

## Test results (run by the reviewer, 23-10-2026)

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s029cr2 tooling/run-tests.bat` | backend **2316 passed**; frontend **119 passed**; deps **42 passed**; tooling **91 passed**. All suites PASSED. |
| `npx vite build` (`frontend/`) | built in 4.0 s, no errors |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` | **51 passed** (Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium; 6 lanes), 76 s. Exit 0. |

Why these specs: the fix round changed the equipment screen (`equipment.spec.js`), and `screens.spec.js` opens `/equipment` for every role. The fix round changed no shared frontend code, so the full suite was not needed. The count rose from 48 to 51: the new test runs once per project.

## Status of the round 1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | **Fixed, verified** |
| CR1-02 | minor | Not fixed, by the user's choice |
| CR1-03 | nit | Not fixed, by the user's choice |
| CR1-04 | nit | Not fixed, by the user's choice |
| CR1-05 | nit | Not fixed, by the user's choice |

### CR1-01 — verification

- **The fix.** `EquipmentView.vue:158-159` skips the `tickets` key in `listUrl()` when `canSeeTickets` is false. The URL keeps its `tickets=down`, so nothing in the address bar changes behind the user's back. This matches the fix proposed in r1.
- **No side effect for users who see the filter.** `canSeeTickets` reads `userPermissions`. That list is filled from `/api/auth/me` before the router lets any view open (`router/index.js:103` already depends on it), so an engineer's first `load()` sees the right value. `canEdit` on the same screen relies on the same order.
- **The new e2e test** (`equipment.spec.js:157`). The storekeeper opens `/equipment?tickets=down&q=<prefix>`. The test expects the red, amber and green machines as rows, and no *Tickets* select. It asserts what the user sees, and passes on all three projects.
- **The test fails without the fix (by reasoning, not by a run).** Without the skip, `listUrl()` would send `tickets=down`. The API answers the empty page to a user with no `ticket:read` (`equipment.py:526`, covered by `TestTicketLight::test_no_ticket_read_anywhere`), so none of the three rows would show and the first `toBeVisible` would fail. I did not revert the line to run it: my role does not edit code, even for a moment.

## Nits

None new.

## Checked and found consistent

- **Fix round diff.** One condition and a comment that says why; no other change in `EquipmentView.vue` from the fix round.
- **Test fixture.** The new test makes its own machines through `lightMachines(testInfo, "bookmark")`, so it shares no rows with the other S029 tests or projects.
- **Impl report.** Fix rounds § Round 1 answers CR1-01 and names the test. It follows scope A. It states the user's choice on CR1-02..CR1-05.
- **Manual checks.** The r1 manual check for CR1-01 is now automated by the new test.

## Manual browser check for the user

- Open `/equipment` on a phone and judge whether the bulbs read clearly at a glance (CR1-02, left open by the user's choice).
