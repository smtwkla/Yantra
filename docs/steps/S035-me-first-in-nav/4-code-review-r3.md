```
Step: S035 — Me first in the nav
Doc: code review r3
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S035 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** Fix round 2 fixes
CR2-01, CR2-02 and CR2-03. The round brings in no new fault. This round has
no new findings.

## Tests

- `YANTRA_TEST_RUN=s035cr3 tooling/run-tests.bat`: ALL SUITES PASSED.
  Backend 2520, frontend 142, deps 42, tooling 106. The frontend count is
  142, not the report's 139, because the working tree also holds other
  steps' unit tests (S036's `ticketLabels.test.js`).
- `npx vite build` in `frontend/`: built in 4.30 s. Only the old chunk-size
  warning shows.
- e2e: I did not run it again. The confirming run is the S041 coder's full
  run on the combined tree, which holds S035's router, `App.vue`, navigation
  and `me.spec.js` changes. Result: 296 passed, 1 failed, 6 skipped (303).
  The 10 label failures of CR2-01 are gone. The one failure,
  `tickets-parts.spec.js:129` on phone-webkit, passed on re-run. That spec
  does not test anything S035 changed, so I count it as a flaky test, not a
  fault of this step. A full run fits this step because the router is
  shared frontend code.

## Findings of earlier rounds

| ID | Severity | Status |
|---|---|---|
| CR1-01 | minor | Fixed (round 2). |
| CR1-02 | nit | Fixed (round 2). |
| CR1-03 | nit | Fixed (round 2). |
| CR2-01 | blocker | Fixed. The report's round 1 e2e line now gives the real result (10 failed). Step S041 fixes the cause in `frontend/e2e/equipment.spec.js`. The full run above is green apart from one flaky test. |
| CR2-02 | nit | Fixed. `homePath(permissions)` in `frontend/src/stores/navigation.js` returns `landingPath(permissions) ?? "/equipment"`. `router/index.js` (the `beforeEach` guard) and `App.vue` (the permissions watcher) both call it. The duplicate fallback is gone. A vitest case covers a technician (`/me`), the storekeeper (`/equipment`) and no permissions (`/equipment`). |
| CR2-03 | nit | Fixed. The comment at `router/index.js:61` now says Me is "the first nav item (S035)". |

The report gives no red result for the new `homePath` test, and it says why.
The change is a pure refactor with no fault to show, and the helper did not
exist before. That reason is enough.

## Checked and found consistent

- `homePath` keeps the old behaviour exactly: the fallback `/equipment` is
  the same as the old `redirect` on `/`. It is a pure function in the
  navigation store, the right layer.
- The guard and the watcher call the same helper, so `/` cannot land on two
  different pages.
- The import lines in `router/index.js` and `App.vue` still use
  `landingPath` for the "cannot open this route" case, so no import is left
  unused.
- The report's round 2 section is in scope A: one point per bullet, and it
  says what was fixed and what was not.

## Manual browser check

None is new. The `## Manual checks` section carries the brief's check as
`[auto]` (`me.spec.js`, a technician opening `/` lands on Me). The full e2e
run above passes it.

Files re-read this round: `frontend/src/stores/navigation.js`,
`frontend/src/router/index.js`, `frontend/src/App.vue`,
`frontend/tests/navigation.test.js`, and the round 2 section of
`3-impl-report.md`.
