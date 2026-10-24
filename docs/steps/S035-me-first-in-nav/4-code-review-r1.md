```
Step: S035 — Me first in the nav
Doc: code review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
Track: fix
```

# S035 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` and two nits.
The change is correct, small and inside the fix-lane limits.

## Test results (my own runs, `YANTRA_TEST_RUN=s035cr1`)

- `tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2520, frontend 138,
  deps 42, tooling 106.
- `npx vite build` in `frontend/`: built. Only the old chunk-size warning.
- `tooling/run-e2e-tests.bat e2e/me.spec.js e2e/screens.spec.js`: 42 passed
  (3 devices). These are the right targeted specs: the Me screen's spec and
  the every-route spec. No shared frontend code changed (`navigation.js` is
  not on the full-suite list), so the full suite is not needed.

## Findings

### CR1-01 (minor) — No browser test checks the new landing page or order

- **Where:** `3-impl-report.md` § Manual checks ("covered by … the e2e run
  above"); brief § Manual checks ("The e2e run covers the order and the
  landing page").
- **Problem:** no e2e spec asserts either fact. `me.spec.js` and
  `screens.spec.js` open their pages by path (`asPerson(page, "technician",
  "/me")`); the only `goto("/")` is `screens.spec.js:85`, for a user with no
  access. The e2e run passing shows that nothing broke, not that the user
  lands on *Me*. The unit tests in `navigation.test.js` do cover
  `landingPath` and the order. But the wiring that uses them is not tested:
  the `/` redirect (`router/index.js:19`), the guard (`:112`) and the
  `App.vue:27` watcher.
- **Failure scenario:** a later change sets a fixed redirect for `/`, or
  sorts the bottom bar on its own. The unit tests stay green, the user lands
  on *Equipment* again, and no test catches it.
- **Fix:** do one of these two:
  1. Add one e2e test in `me.spec.js`: a technician opens `/`, lands on
     `/me`, and the first bottom-bar or sidebar item is *Me*. The storekeeper
     test at `me.spec.js:123` already covers the other side.
  2. Correct the report line to say the unit tests cover the order and the
     landing page, and the e2e run only shows that nothing broke.

  I recommend option 1: it is a few lines, and it automates the user's
  stated choice (U1).

## Nits

- **CR1-02** (nit) `3-impl-report.md` § Tests: the report skips `npx vite
  build`, but the code-review rules ask for it when the frontend changes. I
  ran it, and it is green. Next time, run it and give the result.
- **CR1-03** (nit) `3-impl-report.md` § Files touched: the heading says 4,
  but the list names 5 files (`docs/steps/README.md` and the brief share one
  line). Say "4 code and doc files, plus the step status in 2".

## Fix-lane limits

- **Files:** `navigation.js`, `navigation.test.js` and `docs/Plan.MD`, plus
  the status lines in `README.md` and the brief. That is within "about 5".
- **No permission change:** the `me` item keeps `perm: "ticket:read"`.
  `config_rbac.py` is untouched.
- **No API, schema, setting, security or locking change:** only the order of
  one frontend array changed.
- **"Fixes behaviour already described":** this is a change of a decided
  order (S031 § 1.1, U1), not a bug. The brief says so openly, and the user
  asked for it on the fix lane (U1, 24-10-2026). I accept it on that basis.
  It is not a finding.

## Checked and found consistent

- `navigation.js`: `me` is at index 0. The order is *Me*, *Equipment*,
  *Tickets*, *Masters*, *Settings*, as the brief says. The other items are
  unchanged.
- `landingNavItem` returns the first visible item. So the order change moves
  the landing page with no other code change: the `/` redirect, the guard,
  `App.vue` and `NotFoundView.vue` ("Go to Me") all follow.
- The sidebar and `AppBottomNav.vue` both read `navItems` with no slice or
  sort of their own, so both show *Me* first.
- The storekeeper (no `ticket:read`) still sees *Equipment* first and lands
  on `/equipment`. The unit test covers it, and `me.spec.js:123` passed.
- No permissions: `landingPath` stays null. The `/` redirect falls back to
  `/equipment` as before, and `screens.spec.js:82` passed.
- `navigation.test.js`: every list and landing assertion uses the new order.
  The storekeeper landing is added for both `landingPath` and
  `landingNavItem`, as the brief asks. The report gives the red run
  (4 failed on the old order) and the green run (10 passed).
- `docs/Plan.MD`: both lines (module list item 8 and § Screens, phone) now
  say *Me* first and name the new landing page, with S035 and the date. No
  other doc names the landing page or the nav order.
- No `Decisions taken`, and none are needed: nothing departs from the brief.
- Screen text: no label or message changed. The *Me* label and icon stay as
  they were.

## Manual browser checks for the user

None are required. To confirm the landing page by eye, do this:

1. Sign in as a technician on a phone.
2. Check that the app opens on *Me*, and that *Me* is the first item of the
   bottom bar.
