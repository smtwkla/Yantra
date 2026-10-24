```
Step: S035 — Me first in the nav
Doc: impl report
Author: Coder
Date: 24-10-2026
Track: fix
```

# S035 — Impl report

## What was built

*Me* is now the first item of the sidebar and the phone bottom bar. Every role with `ticket:read` now opens the app on *Me*. The storekeeper (no `ticket:read`) still opens on *Equipment*.

## How it works

`navItems` in `frontend/src/stores/navigation.js` is the one list for the sidebar and the bottom bar. `landingNavItem` returns the first item the user may see, so moving `me` to index 0 changes the landing page with no other code change.

## Files touched (4 code and doc files, plus the step status in 2)

- `frontend/src/stores/navigation.js`: `me` moved to the top of `navItems`.
- `frontend/tests/navigation.test.js`: new order and landing page; storekeeper landing on `/equipment` added.
- `docs/Plan.MD`: two lines (the *Me* decision and the phase list) now state *Me* first and the new landing page.
- `docs/steps/README.md` and the brief: status `In code review`.

## Red, then green

The test file was changed first and run on the old order: 4 failed, 6 passed (order of the visible lists, landing path, landing nav item). After the change: 10 passed.

## Decisions taken

None. No e2e spec relied on landing on *Equipment* after login: `screens.spec.js:85` opens `/` for a user with no access, and `me.spec.js:123` (storekeeper) still lands on `/equipment`. No spec changed.

## Not done / deferred / assumed

Nothing. No backend, permission, API or schema change.

## Tests

- `YANTRA_TEST_RUN=s035c1 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 138, deps 42, tooling 106.
- `tooling/run-e2e-tests.bat e2e/me.spec.js e2e/screens.spec.js`: 42 passed (3 devices). These are the specs of the Me screen and the every-route spec.
- `npx vite build` not run: the change is one array order, and the frontend tests passed.

## Manual checks

None in the brief. The order and landing page are covered by `frontend/tests/navigation.test.js` (unit) and the e2e run above.

## Fix rounds

### Round 1

Result: the new e2e test found a real fault in the landing page. The fix touches `router/index.js` and `App.vue`, which the brief did not name. Please confirm this scope (see CR1-01).

- **CR1-01 (minor): Fixed, and it was a real fault.** Added `S035: a technician opening / lands on Me, and Me is the first nav item` to `frontend/e2e/me.spec.js`. It opens `/` as the technician, expects the URL `/me`, and expects the first visible nav item (sidebar or bottom bar) to be named *Me*.
  - **The fault.** The old `/` route was `redirect: () => landingPath(userPermissions.value) ?? "/equipment"`. A redirect runs on the first navigation, before login, when the permission list is still empty. So `/` always went to `/equipment`. `App.vue` only corrects a route the user may not open, and the technician may open `/equipment`. The user never reached *Me* on a fresh load of `/`. The unit tests could not see this. (Before, the first item was *Equipment*, so the fault was hidden.)
  - **Red, then green.** With the nav order moved back temporarily: fails on `expect(page).toHaveURL(/\/me(\?|$)/)`, received `/equipment`. With the new order but the old router, the same assertion failed. With the router fix: passes on desktop-chromium, phone-chromium and phone-webkit. The nav file is restored to *Me* first.
  - **The change.** `/` is now a route named `home` that renders nothing. The router guard sends `home` to the landing path once the user is authenticated. The permissions watcher in `App.vue` does the same when permissions arrive after login. No permissions still falls back to `/equipment`.
- **CR1-02 (nit): Fixed.** `npx vite build` in `frontend/`: built in 3.86 s. Only the old chunk-size warning.
- **CR1-03 (nit): Fixed.** Heading now reads "Files touched (4 code and doc files, plus the step status in 2)". The two new source files of this round are listed below.

Additional files this round: `frontend/src/router/index.js` (the `home` route and guard), `frontend/src/App.vue` (the watcher), `frontend/e2e/me.spec.js` (the new test).

Tests of this round:
- `YANTRA_TEST_RUN=s035c2 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 138, deps 42, tooling 106.
- Full e2e suite (the router is shared frontend code): corrected in round 2. The reviewer saw 10 failed, 6 skipped, 287 passed (303 tests). The 10 failures come from S033's test in `equipment.spec.js` (CR2-01); this round-1 line wrongly said 0 failed.

### Round 2

- **CR2-01 (blocker): Corrected in the report; the cause is not fixed here.** The round 1 e2e line is rewritten above: 10 failed, 6 skipped, 287 passed, from S033's test (`equipment.spec.js:196` adds a part under the seed extruder, so two label checks count 3 labels, not 2). The fix belongs to step S041. `equipment.spec.js` is not touched in S035.
- **CR2-02 (nit): Fixed.** New helper `homePath(permissions)` in `frontend/src/stores/navigation.js` (landing path, or `/equipment` when none). `router/index.js` and `App.vue` both call it. New unit test `the home path is the landing page, or Equipment when the user has none (S035)` in `frontend/tests/navigation.test.js`. No red run: this is a pure refactor with no fault, and the helper did not exist before.
- **CR2-03 (nit): Fixed.** The comment at `router/index.js:61` now says Me is "the first nav item (S035)".

Tests of this round:
- `YANTRA_TEST_RUN=s035c3 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 139, deps 42, tooling 106.
- `npx vite build` in `frontend/`: built in 3.88 s, only the old chunk-size warning.
- `tooling/run-e2e-tests.bat e2e/me.spec.js`: 21 passed. The full suite is not run here; the S041 coder runs it on the combined tree.

## Manual checks (round 1)

- [auto] A technician opening `/` lands on Me, and Me is the first nav item — `frontend/e2e/me.spec.js`::`S035: a technician opening / lands on Me, and Me is the first nav item`
