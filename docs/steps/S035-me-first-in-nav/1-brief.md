```
Step: S035 — Me first in the nav
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: fix
Status: Gate B (CR r3: 0 findings; r1–r2 findings all fixed; full e2e on the combined tree 296 passed, 1 flaky)
Baseline: e451c33
```

# S035 — Me first in the nav

**The request (KLA, 24-10-2026).** "Move me icon in sidebar to top (first)."
Asked on the fix lane. The user chose (24-10-2026): *Me* first, and the app
opens on *Me*.

**A departure from S031** (S031 § 1.1: "*Equipment* stays first", U1). This is
not a bug fix in the strict sense: it is a small change of a decided order,
asked for by the user on the fix lane. It meets the other fix-lane criteria.

## The change

- `frontend/src/stores/navigation.js:11`: move the `me` item to the top of
  `navItems`, before `equipment`. The order is then *Me*, *Equipment*,
  *Tickets*, *Masters*, *Settings*. The sidebar and the phone bottom bar both
  read `navItems` (its comment, line 2).
- **The landing page follows.** `landingNavItem` (line 33) returns the first
  nav item the user may see. It is used by the `/` redirect and the guard
  (`frontend/src/router/index.js:19`, `:112`), `App.vue:27` and
  `NotFoundView.vue:12`. So:
  - every role with `ticket:read` lands on *Me*: operator, supervisor,
    engineer, manager, and IT admin (`config_rbac.py:105`, and the IT_ADMIN
    list in `navigation.test.js:19`);
  - the storekeeper (no `ticket:read`) still lands on *Equipment*;
  - no permissions: still no landing page.
- No backend change, no permission change, no API change.

## Tests

- `frontend/tests/navigation.test.js`, changed to the new order (red first on
  the old order, then green):
  - the `visible(...)` lists in "maint_operator sees…" (line 29) and
    "Equipment is first for every role…" (line 33) start with `me`; rename
    the second test to say *Me* is first;
  - "everyone with a role lands on Equipment" (line 45): roles with
    `ticket:read` land on `/me`; add the storekeeper landing on
    `/equipment`;
  - "the landing nav item is Equipment for every role" (line 67): it is *Me*
    (`navItems[0]`) for those roles, and *Equipment* for the storekeeper.
- e2e: the targeted specs `me.spec.js` and `screens.spec.js`. The coder
  greps `frontend/e2e/` for any test that relies on landing on *Equipment*
  after login (only `screens.spec.js:85` opens `/`, for a user with no
  access) and fixes what breaks.
- Full suite: `tooling/run-tests.bat`.

## Docs

- `docs/Plan.MD`: if it states the nav order or the landing page, record
  the new order (S035, 24-10-2026). The coder greps for "landing" and "nav".

## Manual checks

None. The e2e run covers the order and the landing page.

## Review log

### U1 — user answer, 24-10-2026

- Me first, and the app opens on Me (rather than: Me first, still opening on
  Equipment).
