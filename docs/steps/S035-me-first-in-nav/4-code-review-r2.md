```
Step: S035 — Me first in the nav
Doc: code review r2
Author: Code reviewer (Opus)
Date: 24-10-2026
Track: fix
```

# S035 — Code review, round 2

**Verdict: one `blocker` is open (CR2-01).** The full e2e suite is red: 10
tests fail. The cause is not S035's code. S033's e2e test adds a part under
the shared seed extruder, and two label checks expect the extruder to have
exactly one part. The fix of CR1-01 itself is correct. CR1-01, CR1-02 and
CR1-03 are fixed.

## Test results (my own runs, `YANTRA_TEST_RUN=s035cr2`)

- `tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 138,
  deps 42, tooling 106.
- `npx vite build` in `frontend/`: built in 5.09 s. Only the old chunk-size
  warning.
- `tooling/run-e2e-tests.bat`, **full** suite: the fix round changed
  `router/index.js`, which is shared frontend code. Result: **10 failed,
  6 skipped, 287 passed** (303 tests, 6 lanes, 317 s). Report:
  `scratch/e2e-report/html/index.html`.
  - `labels.spec.js:69` "the equipment page prints a node's label with its
    parts": failed on all 3 devices (lanes 1, 3 and 5).
  - `screens.spec.js:69` "every screen opens as …", step
    `/labels?ids=1&parts=1`: failed for all 7 roles on phone-webkit (lane 3).
  - The new S035 test passed on all 3 devices.

## Status of the round-1 findings

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed. The e2e test exists and passes. The report gives its red result. |
| CR1-02 | nit | Fixed. The report gives the `vite build` result. |
| CR1-03 | nit | Fixed. The heading counts the files correctly. |

## Findings

### CR2-01 (blocker) — The full e2e suite is red: S033's test leaks a part into the labels checks

- **Where:** `frontend/e2e/equipment.spec.js:196` (S033, committed in
  c9234ce) adds a component-unit under the seed extruder.
  `frontend/e2e/labels.spec.js:77` and `frontend/e2e/screens.spec.js:56`
  expect "2 labels on 1 sheet" for the extruder with its parts.
- **Problem:** each lane has one database for all its specs. When
  `equipment.spec.js:196` runs in the same lane and project before the label
  checks, the extruder has two parts. The page then shows "3 labels on 1
  sheet" (the page snapshot in
  `scratch/e2e-report/results/lane3/screens-every-screen-opens-as-operator-phone-webkit/error-context.md`
  says so). Whether the fault shows depends on how the lanes split the tests.
  S035's new test adds 3 tests, so the split moved. With `E2E_LANES=1` the
  fault would always show, because `equipment.spec.js` runs before
  `labels.spec.js`.
- **Failure scenario:** the user runs the full suite before a release, as
  the rules ask. It is red, and the release waits on a fault that has
  nothing to do with the release's changes.
- **The report's e2e line:** the fix round says "287 passed, 6 skipped,
  0 failed". That is 293 tests, but the suite has 303
  (`npx playwright test --list`). The 10 missing tests match the 10 that
  fail here. The coder's run was most likely red too, and the report misread
  it.
- **Fix:** choose one of these two:
  1. **A separate fix-lane step for S033's test (recommended).** Make
     `equipment.spec.js:196` add its part under a seed node that no label
     count depends on, or make the label checks independent of it. Then run
     S035's targeted specs again. This keeps S035 to its own change, and the
     fault belongs to S033.
  2. Fix the test in S035's next round. That is one test file more, so the
     step has 7 files and goes further past the fix lane's "about 5".

  Either way, correct the fix round's e2e line in `3-impl-report.md` to the
  real result.

## Nits

- **CR2-02** (nit) `frontend/src/router/index.js:113` and
  `frontend/src/App.vue:27`: the rule `landingPath(perms) ?? "/equipment"` is
  now written twice. Put it in one helper in `navigation.js` (for example
  `homePath(perms)`), with a unit test, and call it from both.
- **CR2-03** (nit) `frontend/src/router/index.js:61`: the comment still says
  *Me* is "a nav item after Tickets". Since S035 it is the first item.

## The fix of CR1-01: checks made

I read `router/index.js` and `App.vue` in full, and `stores/auth.js`
(`loadProfile`, `initAuth`).

- **Order of the auth values:** `loadProfile` sets `authenticated` before
  `userPermissions` (`auth.js:89`, `:94`). So when the `App.vue` watcher
  runs, `authenticated` is already true, and the `home` branch takes effect.
- **No permissions:** `/api/auth/me` returns a new empty list. The watcher
  runs and sends `home` to `/equipment`. `App.vue` then shows
  `NoAccessView`, as before. The guard does not loop: for `/equipment`,
  `landingPath` is null, so it returns `true`. `screens.spec.js:82` (no
  access) passed.
- **DB down:** `/api/auth/me` returns the token's permissions only
  (`app.py:161`). A technician gets an empty list, so the result is the same
  as "no permissions". An IT admin lands on the first item its token
  permissions show.
- **`/api/auth/me` fails:** `authenticated` stays false, and `App.vue` shows
  the error card. The `home` route never renders.
- **Deep link and refresh:** a path other than `/` does not match `home`, so
  the guard and the watcher behave as before. A refresh on `/me` stays on
  `/me`.
- **Back to `/`:** both paths use `replace`, so `/` leaves no history entry.
  No screen links to `/` (searched `frontend/src`). An in-app visit to `/`
  after login goes through the guard, which redirects at once.
- **Flash of an empty page:** before login the shell does not render, only
  the spinner. After login, the shell can render for one frame with an empty
  main area, before `replace` to `/me` completes. `MeView` is imported
  statically, so the gap is short. It is a manual check below, not a
  finding.
- **Storekeeper:** `landingPath` gives `/equipment` (unit test in
  `navigation.test.js`). `me.spec.js:131` passed. No e2e test opens `/` as
  the storekeeper. The unit test covers the rule, and the router code is the
  same for every role, so this is enough.
- **Red, then green:** the report gives the red result of the new test on
  the old router (received `/equipment`), and the green result after the
  fix.

## Fix-lane limits

The step still fits the fix lane, but only just. The user should confirm it
at gate B.

- **Files:** 6 code, test and doc files (`navigation.js`,
  `navigation.test.js`, `Plan.MD`, `router/index.js`, `App.vue`,
  `me.spec.js`), plus the status lines in 2. That is a little past "about 5".
- **Permissions:** no key changes, and `config_rbac.py` is untouched. The
  router guard is a convenience redirect, not an access check: the API
  gates every route.
- **Interface:** no API, schema or setting changes. The new `home` route has
  no path of its own beyond `/`, which existed already.
- **Behaviour already described:** the router fix makes the landing page
  work as S031 and this brief describe it ("the first item the user may
  see"). The fault was latent since S031, because *Equipment* was first and
  was also the fallback.
- **Reported:** the fix round names the two extra files and asks the user
  to confirm them. That is enough. No unreported departure.

## Checked and found consistent

- The new e2e test asserts what the user sees: the URL `/me`, and the
  accessible name of the first visible nav item (sidebar or bottom bar).
- The `home` route renders nothing (`render: () => null`), and has no
  `meta.title`. It is never shown after login.
- The `App.vue` watcher keeps its old branch for routes the user may not
  open. The new branch returns first, so the two cannot both run.
- The `S035` test name follows the e2e naming rule (step first).
- The impl report's `## Manual checks (round 1)` lists the new automated
  check as `[auto]`, with its test.
- Screen text: no label or message changed in this round.
- Re-read in this round: `frontend/src/router/index.js`,
  `frontend/src/App.vue`, `frontend/src/stores/auth.js` (the login part),
  the diff of `frontend/e2e/me.spec.js`, and `3-impl-report.md` § Fix
  rounds. I did not re-read the rest of the step.

## Manual browser checks for the user

1. Sign in as a technician on a phone, from a fresh tab on the app's root
   address.
2. Check that the app opens on *Me*, with no visible blank page in between.
3. Check that *Me* is the first item of the bottom bar.
