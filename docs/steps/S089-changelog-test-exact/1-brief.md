```
Step: S089 — Changelog test matches the badge exactly
Doc: brief
Author: Orchestrator (Opus)
Date: 01-11-2026
Track: fix
Baseline: 0bb67c5
Status: Done (committed at adoption, 01-11-2026; no device check); was: Gate B 01-11-2026 (code review r1: 0 blocker, 0 major, 0 minor, 1 nit, fixed by the orchestrator in fix round 1, test only)
```

# S089 — Changelog test matches the badge exactly

Found by the pre-flight of `0bb67c5` (`scratch/preflight/0bb67c5.md`, bug 1). KLA, 01-11-2026: fix the test.

## The bug

The S048 browser test *S048: it_admin opens the change log from the version in the sidebar* (and the
`admin` twin) fails on `desktop-chromium` every run: `getByText('This version')` resolves to 2 elements
(strict-mode violation).

## Steps to see it

`tooling/run-e2e-tests.bat --level=full e2e/changelog.spec.js:14 --project=desktop-chromium`

## Cause

- `frontend/e2e/changelog.spec.js:24` asserts `dialog.getByText("This version")`. A string given to
  `getByText` matches any element whose text contains it, ignoring case.
- The running version is 0.1.14 (`VERSION`), and its `CHANGELOG.md` section is empty: v0.1.14 released only
  `d490e69 WIP;` (schema docs tooling), which the notes rules leave out. So `ChangelogModal.vue:58` shows the
  badge "This version" and `ChangelogModal.vue:63` shows "No notes were written for this version."
  Both match.
- The app is right. The test fails whenever the running version has no notes.

## The fix

`frontend/e2e/changelog.spec.js:24`: `dialog.getByText("This version", { exact: true })`, which matches the
badge only (exact: whole text, case-sensitive). No app code changes.

## Files

- `frontend/e2e/changelog.spec.js` (one line)

## The test that fails on the bug

The test itself: both S048 tests at `changelog.spec.js:14` fail before the fix on `desktop-chromium` and
pass after it. No unit test changes. Targeted run only: `tooling/run-e2e-tests.bat e2e/changelog.spec.js
--project=desktop-chromium`. Unit suites: `YANTRA_TEST_RUN=s089c1 tooling/run-tests.bat`, as
the fix lane asks.

## Review log

| ID | Finding | Answer |
|---|---|---|
| CR1-01 (nit) | The badge was not checked to sit in the running version's heading | Accepted, fix round 1 (orchestrator): the badge is looked up inside the `v<VERSION>` heading; `e2e/changelog.spec.js --project=desktop-chromium` 3 passed |
