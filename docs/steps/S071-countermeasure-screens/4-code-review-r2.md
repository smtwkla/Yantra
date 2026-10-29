```
Step: S071 — Countermeasures: screens
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S071 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01, CR1-02, CR1-03,
CR1-04 and CR1-06, and answers CR1-05 with a comment. I found 1 new nit. This round verifies the
fix round only (`step_snapshot.py diff S071 --from-round 1`).

## Tests run

- **Frontend unit suite** (`YANTRA_TEST_RUN=s071cr2 tooling\run-frontend-tests.bat`): 321
  passed. The fix round changed only files under `frontend/`, so the other suites were not run
  again.
- **Frontend build**: not run again. The coder's `npx vite build` is clean, and the round's code
  changes are three lines in three components.
- **Browser tests**: none re-run. No finding of mine needs a run. The coder's targeted run names
  the right specs: `improvements` (the changed tests and screens), `me` (`CountermeasureItem`,
  `ActionDialog` are shared with *Me*) and `screens`: 44 passed, 1 skipped. The round changes no
  file in `e2e/support/` and no shared frontend file, so no WebKit run is due.

## Earlier findings

| ID | Status | Check |
|---|---|---|
| CR1-01 (minor) | Fixed | `ActionDialog.openChange` stores `left` from `owner.active` and `owner.may_own`, the same fields `CountermeasureItem` uses. `ownerChoices` shows the plain name while the list loads or fails. |
| CR1-02 (minor) | Fixed | The refused-photo test adds `TEST_PHOTO` in the close-only phase, waits for the row's `.fa-check`, closes, and expects `"Photos (1)"` (`exact: true`). The red run is reported: without `emit("reload")` the `"Photos (1)"` locator was not found. |
| CR1-03 (nit) | Fixed | `cancelAction` calls `load()` on a 409 with no field, with the same test as `MoveDialog` and `MarkDoneDialog`. No test, for the stated reason (a second writer is needed between load and tap). See CR2-01. |
| CR1-04 (nit) | Fixed (second option) | The `usePhotoUploads.js` contract comment now says the next open and unmount, which is what the code does. The reason (no close event, the fade) is sound. |
| CR1-05 (nit) | Answered | The CSS comment now names 992px as Bootstrap's `lg`. The reason for scoped CSS is valid: the rule resets the base flex rules. |
| CR1-06 (nit) | Fixed | The first S071 test expects `istDay(14)`. The browser runs with `timezoneId: "Asia/Kolkata"`, so `defaultDueDate`'s local date and `istDay` agree. No red run, with a reason given. |

## Nits

- **CR2-01** (nit) `frontend/src/views/ImprovementDetailView.vue:147`: after the stale-row
  reload the countermeasure shows *Done*, but its cancel ask stays open (`cancellingId` is kept),
  and a second tap on *Cancel countermeasure* gets the same 409. Clear `cancellingId` after the
  reload when the row's `can_change` is false, or leave it as is: the server's message and
  *Keep it* tell the user what to do.

## Checked and found consistent

- **The 409 reload:** `ApiError` carries `status` (`api.js:60`). `load()` keeps the detail while
  it reloads, so the open row does not unmount, and the refusal's message stays under the ask.
  `load()` catches its own errors, so the call without `await` leaves no unhandled rejection.
- **The owner marker:** an owner who is still in the site's list shows from the list, under the
  plain name. The opened owner is added only when the list lacks it. The marker then follows
  the detail, not the list's load state.
- **The extended test:** the close-only phase uploads at once (`uploadChosen`), and the row's
  `.fa-check` shows only after the upload's answer, so the *Close* tap waits for the upload.
- **Writing style:** the round adds no screen text. The impl report's fix-round section is in
  scope A.
- **Docs:** the round changes no behaviour a doc describes; "none" is right.
- **Files re-read:** the fix round's diff, and around it `ImprovementDetailView.vue` (`load`,
  `askCancel`, `cancelAction`, the row's props), `CountermeasureItem.vue` (the cancel ask),
  `api.js` (`status`), `playwright.config.js` (`timezoneId`), `e2e/support/tickets.js`
  (`istDay`) and `improvementLabels.js` (`defaultDueDate`).

## Manual browser check (the user)

Unchanged from round 1:

- Row 51 (**important**): *Mark done* from *Me* with the camera on an Android phone, with a work
  glove on.
- Row 52: a HEIC photo from an iPhone in *Mark done*.
- On a desktop, glance at the card at `lg` width with a long countermeasure text.

## Feedback

- none
