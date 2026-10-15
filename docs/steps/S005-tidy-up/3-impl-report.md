```
Step: S005 — Tidy-up: page not found, leftover review nits
Doc: impl-report
Author: Coder (Sonnet)
Date: 15-10-2026
Status: In code review
```

# S005 — Implementation report

## 1. What was built

- A "Page not found" page for any address no route matches, with a button to the user's landing page.
- Four nits closed: a post-commit read-back message that does not invite a retry; one `SEARCH_DELAY_MS`; the `_lock_type` docstring; the Type filter showing a type of another class.

## 2. How it works

- **Not found.** A last route `/:pathMatch(.*)*` (name `not-found`) renders `NotFoundView.vue`: icon, "Page not found", "The address **{{ route.fullPath }}** doesn't exist in Yantra." (text interpolation, wraps via `text-break`), and a "Go to <label>" button to `landingNavItem(userPermissions)`; hidden when there is none. `canOpenRoute` already allows routes that are not nav items, so the guard needs no change.
- **`landingNavItem`** returns the first visible nav item or `null`; `landingPath` is now `landingNavItem(...)?.path ?? null`.
- **Post-commit message.** `SAVED_BUT_UNREADABLE` ("Saved, but the record could not be read back — reload the page") is passed to `_reread` at the two post-commit calls (create and update), each with a one-line comment. In-transaction calls are unchanged (409 "try again", rolled back).
- **Search delay.** `useDebounced.js` exports `SEARCH_DELAY_MS = 300` as the default of `delayMs`; `EquipmentView` and `EquipmentMoveModal` drop their copies. The view comment names the constant.
- **`_lock_type` docstring** reworded as in § 4.4.
- **Type filter.** `typeChoices` appends the URL's `type_id` type last when it is not among the chosen class's types; `typeLabel` is `Name` when the type's class is the chosen class, else `CLS · Name`. An unknown `type_id` is left blank.

## 3. Files touched (12)

- `backend/equipment.py`: constant `SAVED_BUT_UNREADABLE`; two post-commit `_reread` calls; `_lock_type` docstring.
- `backend/tests/test_equipment_api.py`: new test `test_create_that_cannot_read_back_after_commit_says_reload_and_is_saved`.
- `frontend/src/views/NotFoundView.vue` (new): the page.
- `frontend/src/router/index.js`: import and catch-all route.
- `frontend/src/stores/navigation.js`: `landingNavItem`; `landingPath` derived from it.
- `frontend/src/composables/useDebounced.js`: exported `SEARCH_DELAY_MS`, default delay.
- `frontend/src/views/EquipmentView.vue`: local constant removed; comment; Type filter fix.
- `frontend/src/views/equipment/EquipmentMoveModal.vue`: local constant removed.
- `frontend/tests/navigation.test.js`: `landingNavItem` and `not-found` tests.
- `docs/steps/S005-tidy-up/1-brief.md`, `docs/steps/README.md`, this report: status "In code review".

## 4. Decisions taken

- A module constant `SAVED_BUT_UNREADABLE` in `equipment.py`, so the message is defined once and the test imports it instead of copying the string (forced by DRY; not in the brief).
- The new test counts reads with a closure over `stale_reread`'s change function (first read returns the row, later reads `None`); it also asserts the count is 2, so it fails if the call structure changes.
- The icon is `fa-triangle-exclamation` (brief only says "an icon").
- No departures from the brief.

## 5. Not done / deferred / assumed

- Update's post-commit message has no test (the brief asks for create only).
- Done steps' reports not edited (brief § 6).

**Tests run**
- `tooling/run-tests.bat`: backend 552 passed (one new), frontend 26 passed (4 files).
- `npx vite build` in `frontend/`: built, no errors.

**Manual browser checks still needed (brief § 5)**
- `/nope`, `/equipment/abc`, `/masters/x`: "Page not found" with the path; "Go to Equipment" works; sidebar and topbar stay.
- `/equipment/999999`: still "Equipment not found, or not at your units".
- Both search boxes (list, move dialog) still wait before searching.
- `/equipment?class_id=<RPP>&type_id=<type of another class>`: the Type filter shows that type as `CLS · Name`, and the empty list makes sense; `?type_id=999999` stays blank.
