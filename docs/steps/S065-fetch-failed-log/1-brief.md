```
Step: S065 — A dropped connection logs no console error
Doc: brief
Author: Orchestrator (Opus)
Date: 28-10-2026
Track: fix
Status: Done (committed 410ad3b; checks: 5 auto)
Baseline: 33ce411 (working tree also holds S064's Status lines in INDEX.md and its brief)
```

# S065 — A dropped connection logs no console error

KLA, 28-10-2026: pre-flight on 33ce411 was red; after the advice, "Fix the code as advised".

## The bug

Pre-flight on 33ce411 (Full level): 5 browser tests fail, all on the console guard only; their
screen assertions pass. Steady on one re-run each. Bug reports: `scratch/preflight/33ce411.md`.

- phone-chromium `e2e/floor.spec.js:60` (S064: a dropped connection shows the plain no-connection
  text) and `e2e/readings.spec.js:494` (S040: a failed save (no answer) stops the loop):
  `console.error: fetch failed TypeError: Failed to fetch`.
- phone-webkit `e2e/screens.spec.js:85` (every screen opens as <role>), 3 of 7 roles, which ones
  vary: `console.error: fetch failed TypeError: Load failed`.

**To see it:** `tooling/run-e2e-tests.bat --level=full e2e/floor.spec.js:60 e2e/readings.spec.js:494 --project=phone-chromium`
and `tooling/run-e2e-tests.bat --level=full e2e/screens.spec.js:85 --project=phone-webkit`.

**Cause (checked):**
- `frontend/src/api.js:23`: `send()` logs `console.error("fetch failed", cause)` for every
  `TypeError` from `fetch`. It came from S064's fix round 1 (CR1-04), after the coder's
  whole-suite run; the verify review judged no whole-suite run was needed.
- The guard `frontend/e2e/support/console.js` (applied in `support/test.js:30-37`) fails a test on
  any console.error not allowed.
- WebKit rejects a fetch still running when the page is left with `TypeError: Load failed`;
  Chromium does not (confirmed by the advisor's run, `0-advice-fetch-failed-log.md` in S064's
  folder). `screens.spec.js` moves between screens with `page.goto`, so an iPhone logs the line.

## The fix

As advised (S064 `0-advice-fetch-failed-log.md`, candidate (b)): a dropped connection is the
user's network, not a fault, and the screen already shows `NO_CONNECTION_TEXT`. Any other
`TypeError` (a coding error: a bad header value or URL) still logs, as CR1-04 wanted.

- `frontend/src/api.js` `send()`: a list of the three engines' network-failure messages,
  "Failed to fetch" (Chromium), "Load failed" (WebKit), "NetworkError when attempting to fetch
  resource." (Firefox); log `console.error("fetch failed", cause)` only when the message is not
  in the list. The throw is unchanged (status 0, `NO_CONNECTION_TEXT`, `cause`). Update the
  comment above `send()` (it must not cite files in `scratch/`, which is not in the repo).
- `frontend/tests/api.test.js`: with `vi.spyOn(console, "error")`: each of the three network
  texts logs nothing and throws status 0 with `NO_CONNECTION_TEXT`; a non-network `TypeError`
  (e.g. "Failed to execute 'fetch' on 'Window': Invalid value") logs once and throws the same.
- `frontend/e2e/masters.spec.js:647`: remove `consoleWatch.allowBrowserError("fetch failed");`,
  dead after the fix. Keep line 648 (`net::ERR_FAILED`).
- No change to `support/console.js`, `floor.spec.js`, `readings.spec.js`, `screens.spec.js`.

**The test that fails on the bug:** the new `api.test.js` case "a network text logs nothing"
(red on 33ce411, green after); in the browser, the 5 failing tests above.

**Runs:** `tooling/run-frontend-tests.bat tests/api.test.js`; all unit suites; the two targeted
browser runs above (`phone-webkit` needs Docker Desktop, it is running); then, because `api.js`
is shared code (settings: *Shared code*), the whole suite at Normal once. Then `/pre-flight`
again after the commit.

**Docs:** none due (no migration, secret, role or invariant).

## Fix-lane criteria

Three files, tests included; no permission, route, response shape, migration or setting; no
security-sensitive code; no locking. It fixes S064's CR1-04 change against the browser tests'
rule (S024 § 5.3), and adds no feature.

## Review log

| ID | Answer |
|---|---|
