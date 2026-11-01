```
Step: S089 — Changelog test matches the badge exactly
Doc: impl report
Author: Coder
Date: 01-11-2026
```

# S089 — Impl report

## What was built
The S048 changelog browser test now matches the "This version" badge exactly. No app code changed.

## How it works
`getByText("This version")` matched two elements when the running version has no notes: the badge and "No notes were written for this version." With `{ exact: true }` it matches the badge only.

## Files touched
- `frontend/e2e/changelog.spec.js` — line 24 (1 file). The file is LF in the index and in the working copy; unchanged.

## Decisions taken
None.

## Not done / deferred / assumed
Nothing. The whole browser suite was not run: only a test file changed.

## Red, then green
- Before: `tooling/run-e2e-tests.bat e2e/changelog.spec.js --project=desktop-chromium` — 2 failed (both S048 sidebar tests, at line 24), 1 passed.
- After: same command — 3 passed.
- Unit suites, `YANTRA_TEST_RUN=s089c1 tooling/run-tests.bat`: backend 4467 passed, frontend 412 passed, tooling 231 passed.

## Docs updated
None, because only a test line changed.

## Manual checks
- [auto] it_admin opens the change log from the sidebar version — frontend/e2e/changelog.spec.js::S048: it_admin opens the change log from the version in the sidebar
- [auto] admin opens the change log from the sidebar version — frontend/e2e/changelog.spec.js::S048: admin opens the change log from the version in the sidebar

## Feedback
- none
