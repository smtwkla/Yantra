```
Step: S065 — A dropped connection logs no console error
Doc: impl report
Author: Coder (Sonnet)
Date: 28-10-2026
```

# S065 — Impl report

## What was built

`api.js` no longer writes a console error when `fetch` fails because of the network. A coding error (a `TypeError` with another text) still logs once. The screen text and the thrown error are unchanged.

## How it works

`send()` in `frontend/src/api.js` catches a `TypeError`. It logs `console.error("fetch failed", cause)` only when `cause.message` is not in `NETWORK_FAILURE_MESSAGES`: "Failed to fetch" (Chromium), "Load failed" (WebKit), "NetworkError when attempting to fetch resource." (Firefox). Both kinds then throw an `Error` with `NO_CONNECTION_TEXT`, status 0 and `cause`. An `AbortError` passes on as before. The comment above `send()` is rewritten and cites no `scratch/` file.

## Files touched (3)

- `frontend/src/api.js`: the message list and the conditional log; new comment.
- `frontend/tests/api.test.js`: three network-text cases (`it.each`) and one coding-error case; `vi.restoreAllMocks()` in `afterEach`.
- `frontend/e2e/masters.spec.js`: removed `consoleWatch.allowBrowserError("fetch failed");` (dead now); the `net::ERR_FAILED` line stays.

## Decisions taken

- `vi.restoreAllMocks()` added to the file's `afterEach`: without it a failed assertion left the `console.error` spy in place and the next test counted its calls. No departure from the brief.
- Source code kept as the advisor's checked snippet, with its comment shortened of the `scratch/` references.

## Red, then green

- Red on the old `send()`: `tooling/run-frontend-tests.bat tests/api.test.js` gave 3 failed, 7 passed. The three network-text cases failed with `expected "error" to not be called at all, but actually been called 1 times`. The coding-error case passed on the old code, as it should (it keeps CR1-04).
- Green with the fix: 10 passed.

## Runs (YANTRA_TEST_RUN=s065c1)

- `tooling/run-tests.bat`: backend 3323 passed; frontend 269 passed; tooling 185 passed; all suites passed.
- `npx vite build` in `frontend/`: built (chunk-size warning only, as before).
- `--level=full e2e/floor.spec.js:60 e2e/readings.spec.js:494 --project=phone-chromium`: 3 passed (the line `readings.spec.js:494` holds two tests, the 503 one and the no-answer one).
- `--level=full e2e/screens.spec.js:85 --project=phone-webkit`: 7 passed (all 7 roles).
- `e2e/masters.spec.js -g "CR1-01" --project=phone-chromium`: 1 passed (without the `fetch failed` allow).
- Whole suite at Normal (`api.js` is shared code): 260 passed, 12 skipped, 0 failed (4.1 min, "All lanes done in 259 s").

## Docs updated

None, because the change adds no migration, secret, role, invariant, dev command or device check, and changes no module behaviour that `docs/Plan.MD` describes.

## Not done / assumed

- Not verified on a real iPhone (the advisor's optional Mac check): the fix does not depend on it.
- The three texts are not a standard. A browser that changes its text makes a network failure log again, and the offline tests go red with the new text in the message.

## Manual checks

- [auto] A dropped connection shows the plain no-connection text, with no console error — `frontend/e2e/floor.spec.js::S064: a dropped connection shows the plain no-connection text`
- [auto] A failed save (no answer) stops the loop — `frontend/e2e/readings.spec.js::S040: a failed save (no answer) stops the loop; both rows read Not saved and keep their values`
- [auto] Every screen opens as each role on the iPhone project — `frontend/e2e/screens.spec.js::every screen opens as <role>`
- [auto] A network text logs nothing; a coding-error TypeError logs once — `frontend/tests/api.test.js`

No check on a real device.

## Fix rounds

### Round 1

- CR1-01 (nit): Fixed. The two `logged.mockRestore()` calls are removed from `frontend/tests/api.test.js`; `vi.restoreAllMocks()` in `afterEach` restores the spy. No red run: the change removes redundant code and adds no test for a fault.
- Run (`YANTRA_TEST_RUN=s065cr1`): `tooling\run-frontend-tests.bat tests/api.test.js`: 10 passed (10).
- Docs updated: none, because only a test changed.
- No other suite and no browser run, as the round changes one test file only.

## Feedback

- none
