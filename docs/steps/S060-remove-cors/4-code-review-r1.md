```
Step: S060 — Remove flask-cors
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 26-10-2026
Track: fix
Baseline: c7803b1 + uncommitted S048, S059
Status: In code review
```

# S060 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One nit only. Flask-CORS is gone, and no
caller needs it. The new test fails on the old code and passes now.

## Tests

- `YANTRA_TEST_RUN=s060cr1 tooling/run-tests.bat`: backend PASSED 3099, frontend PASSED 189,
  tooling PASSED 185 (ALL SUITES: PASSED).
- Browser tests: I ran none. The coder's Basic run (13 passed) covers the one thing a browser
  can show here: the app still works through Vite's proxy. No screen or API shape changed, so no
  targeted spec is due. No finding of mine needs a re-run.
- No frontend file of S060 changed, so no build check is due.

## Nits

- **CR1-01** (nit) `docs/steps/S060-remove-cors/3-impl-report.md:1-7`: the header has no
  `Baseline:` line (README § Header block). Add `Baseline: c7803b1 + uncommitted S048, S059`.

## Checked and found consistent

- **No cross-origin caller.** Fact: every call is same-origin or comes from outside a browser.
  - `frontend/src/api.js` calls relative `/api/…` URLs only.
  - `frontend/vite.config.js:39-45` proxies `/api` to the backend (`YANTRA_API_URL` in the e2e
    runs, `playwright.config.js:81`).
  - The e2e set-up calls the backend directly (`e2e/support/people.js:39` Playwright's
    `APIRequestContext`; `tooling/e2e/seed_e2e.py` from Python). Neither is a browser page, so CORS
    never applies to them.
  - No spec runs `fetch` inside the page against `BACKEND_URL`.
  - Production: `tooling/build/nginx.conf:29-33` forwards `/api/` from the same origin. The devops
    `compose.yml.j2` (read-only) sets no `CORS_ORIGINS`. No `Access-Control` or CORS line exists
    in Nginx or the devops templates.
  - `CORS_ORIGINS` appears nowhere else in the repo (one old scratch snapshot only).
  - OPTIONS: Flask's automatic OPTIONS answer stays, without CORS headers. Nothing sends a
    preflight.
- **Hook order (S013).** `app.after_request(make_access_log_hook(...))` at `app.py:43` is still
  the first `after_request` registered. `_log_slow_request` (`app.py:82`) registers later, so the
  access log still runs last and sees the final status. The new comment ("above any later one") is
  true. The `access_control.py:244` docstring now matches.
- **`app.py` imports.** `os` is still used (`:73`, `:207`). No `flask_cors` import is left in
  `backend/`.
- **Lockfile.** `uv.lock` loses only the `flask-cors` package block and its two references
  (`dependencies`, `requires-dist`). `flask` and `werkzeug` stay, as other packages need them.
  `pyproject.toml` loses only the `flask-cors>=5.0` line.
- **SBOM.** In `sbom/backend.cdx.json` the only removed `name`/`version`/`purl` is `flask-cors`
  6.0.5. Every other changed line is a `bom-ref` renumbered by one (e.g. `frozenlist-17` →
  `-16`), which is what the generator does when a component goes. No other `sbom/` file changed.
- **Audit exit 1.** Fact: `sbom/frontend.cdx.json` is unchanged, and the findings (undici
  7.30.0, @vitest/mocker 4.1.11) are frontend dev dependencies. A backend removal cannot cause
  them. Not this step's.
- **Test.** `test_no_cors_headers_are_sent` checks both cases of the bug: no `Origin` (Flask-CORS's
  `always_send` branch) and `Origin: http://localhost:5176`. The impl report records the red run
  on the old code (`AssertionError: {}`, 1 failed). The test asserts the header the user reported.
- **Docs pass.** No migration, so no schema doc is due. `.claude/CLAUDE.md` § Docs to keep
  current: no entry is due (no invariant, command, port or secret). `Plan.MD` and `docs/` name no
  CORS outside old step files. The synced `SMTW-WebApp-Base.md:1431` is left for smtw-common, with
  a ready text in the impl report, as the brief asks.
- **Scope.** Everything in the brief's § The fix is built; nothing else changed. "Decisions taken:
  none" is true.
- **Fix-lane criteria** still hold: about 5 files plus the generated lockfile and SBOM, no
  permission, route, migration or setting change.
- **Manual checks.** Both are `[auto]` with a passing run behind them. The brief has no
  real-device check.
- **Security.** Removing the header narrows exposure; no route, permission or actor handling
  changed.

## Manual browser check for the user

- None needed. Optional, after the next deploy: open production's `/api/health` and confirm the
  response has no `Access-Control-Allow-Origin` header.

## Feedback

- none
