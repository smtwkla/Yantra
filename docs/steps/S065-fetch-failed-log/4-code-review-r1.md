```
Step: S065 — A dropped connection logs no console error
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 28-10-2026
```

# S065 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The change does what the brief asks, in the three files it names. This round has one nit (CR1-01).

## Test runs

- **Unit suites** (`YANTRA_TEST_RUN=s065cr1 tooling/run-tests.bat`): backend **3323 passed**, frontend **269 passed**, tooling **185 passed**. ALL SUITES PASSED.
- **Browser, the coder's runs:** the two targeted runs of the brief (`floor.spec.js:60` and `readings.spec.js:494` on `phone-chromium`: 3 passed; `screens.spec.js:85` on `phone-webkit`: 7 passed), the CR1-01 test of `masters.spec.js` without the removed allow line (1 passed), and the whole suite at Normal once, because `api.js` is shared code (260 passed, 12 skipped, 0 failed). That is the right set. I ran no browser test: no finding of mine needs one.
- **Build:** the coder ran `npx vite build` (built, chunk-size warning only). The change adds one constant and one condition, so I did not repeat it.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `frontend/tests/api.test.js:48` and `:60`: remove the two `logged.mockRestore()` calls. The new `vi.restoreAllMocks()` in `afterEach` already restores the spy, also when an assertion fails.

## Checked and found consistent

- **`send()` message list** (`api.js:22-26`, `:33`): the three texts match the brief and the advice's checked snippet (`0-advice-fetch-failed-log.md:153-164`) exactly, including the Firefox text's final full stop. `includes` compares the whole message, so a coding-error text that only contains "Failed to fetch" (Chromium's "Failed to execute 'fetch' on 'Window': …") still logs. CR1-04's intent holds.
- **Coding-error path:** a `TypeError` with any other text logs `console.error("fetch failed", cause)` once, then throws the same `Error` (status 0, `NO_CONNECTION_TEXT`, `cause`). The new test asserts both the one log and the thrown error.
- **AbortError path:** unchanged. `if (!(cause instanceof TypeError)) throw cause;` comes first, and the existing "an abort goes on as it is" test still passes.
- **New tests:** the three `it.each` cases check the message, status 0 and no log; the report gives the red result (3 failed on the old `send()`, with "expected error to not be called"). The coding-error case passing on both versions is correct: it guards CR1-04.
- **`vi.restoreAllMocks()` in `afterEach`:** a small addition beyond the brief, stated in "Decisions taken". It restores only `vi.spyOn` spies; the file's `vi.mock` of the auth store and the `vi.stubGlobal` stubs are not affected. It is the right guard against a spy that outlives a failed test.
- **`masters.spec.js`:** the `allowBrowserError("fetch failed")` line is removed; the `net::ERR_FAILED` line stays. No other spec, support file or source file names "fetch failed" now (grep of `frontend/src`, `frontend/e2e`, `frontend/tests`).
- **Code comment:** it says why (a `TypeError` is both a lost connection and a coding error; the engines' texts) and cites no file outside the repo and nothing in `scratch/`.
- **Fix-lane criteria:** three code files, tests included. No permission, route, response shape, migration, setting, lock or security-sensitive code. No feature added.
- **Docs pass:** "None" is right. No doc in `CLAUDE.md` § Docs to keep current is made wrong.
- **Manual checks:** the impl report lists the four checks as `[auto]`, each with a passing run behind it. The brief has no real-device check.
- **Scope A in the report:** plain and short; no finding.

## Manual browser check for the user

None. All checks are automated. The advisor's optional Mac check (a real iPhone leaving a page while a request runs) is not needed for this fix.

## Feedback

- none
