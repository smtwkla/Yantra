```
Step: S047 — Browser test levels: Basic, Normal, Full
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. 1 new minor.** CR1-01 … CR1-05 are fixed as
the fix round says. The CR1-01 fix brings in one new fault: a run that matches no test no longer
prints the brief's line "No test matches these arguments: …". It prints "The tests could not be
listed: Error: No tests found" instead. The exit code stays 1, so the run is still not silent.

Re-read, from the snapshot `refs/steps/S047` (39d9477), not the working tree:
`tooling/e2e/run_lanes.py` (`list_groups`, `main`, `run`), the fix round's tests in
`tooling/tests/test_run_lanes.py` (`TestListGroups`, the two new `TestLevels` tests, the
existing `run()` tests), `frontend/vite.config.js` in full, `tooling/release-tests.bat` in full.
Not re-read: the rest of the step (round 2 verifies, it does not re-review).

## Tests

- **Unit tests, my run** (worktree of `refs/steps/S047` in my scratchpad, removed afterwards; the
  working tree holds S051's edits, so no `run-tests.bat`): `tooling/tests/`: 166 passed, 1
  failed. The one failure is `TestWebkitServer::test_the_installed_version_is_readable`. It
  reads `frontend/node_modules/@playwright/test/package.json`, which a bare worktree does not
  have (`FileNotFoundError`). That is my set-up, not the code. The coder's `run-tests.bat` in
  the main folder passed it (tooling 167 passed).
- **`test_run_lanes.py` alone:** 57 passed, the same one failure for the same reason.
- **Playwright probes** (a throw-away config in my scratchpad, Playwright 1.64.1 from
  `frontend/node_modules`): see CR2-01.
- **Browser tests:** not run, as the task says. The coder's targeted run (`e2e/labels.spec.js`
  at Normal, 4 passed) starts the dev server with the new `vite.config.js`.

## Minor

### CR2-01 — minor — `tooling/e2e/run_lanes.py:466-468`: a run that matches no test now says "could not be listed", not the brief's line

- **Problem.** The CR1-01 fix treats any `--list` exit code other than 0 as a listing failure.
  But Playwright's `--list` also exits 1 when nothing matches, with `errors` =
  `["Error: No tests found"]`. I checked this with a scratchpad config and one good spec:
  `--list -g nomatch` gives exit 1 and that error, and a positional file that does not exist
  gives exit 1 and "No tests found. Make sure that arguments are regular expressions…". So
  `list_groups` returns an error, and `run()` never reaches its `if not groups` branch. The
  brief § 1.2 ("No silent empty run") asks for "No test matches these arguments: <args>." and
  exit 1. The unit test `test_no_test_found_is_exit_1_with_its_line` still passes, because it
  mocks `list_groups` to return `({}, None)`, which the real Playwright no longer produces.
- **Failure scenario.** A coder runs `tooling/run-e2e-tests.bat --project=desktop-chromium
  e2e/me.spec.js -g S031` with a `-g` that matches nothing. The run prints "The tests could not
  be listed: Error: No tests found (playwright --list exit code 1)". "Could not be listed"
  suggests a broken spec or config, and the line does not echo the arguments to check. The exit
  code is still 1, so nothing passes by mistake; only the message points the wrong way, which is
  the kind of fault CR1-01 was about.
- **Fix.** Pass `--pass-with-no-tests` to the `--list` run only (`_playwright(["--list",
  "--reporter=json", "--pass-with-no-tests", *args])`). I checked both cases with it: no match
  gives exit 0, `errors` = `[]`, no suites, so `run()` prints the brief's line; a spec with a
  syntax error still gives exit 1 and the `SyntaxError` in `errors`, so CR1-01 stays fixed. The
  lanes keep running without the flag (§ 1.2). Add a `TestListGroups` test that checks the
  `--list` command carries the flag, with a comment saying why.

## Earlier findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | minor | Fixed | `list_groups` returns the report's `errors` messages, or stderr, and the exit code. A load error is now printed. `TestListGroups` covers a load error, a failed list with no message and a good list, with its red result recorded. New fault: CR2-01. |
| CR1-02 | nit | Fixed | `searchForWorkspaceRoot(fileURLToPath(new URL(".", import.meta.url)))`. The trailing separator does no harm: `searchForPackageRoot` returns the folder, and Vite resolves each `fs.allow` entry. Every start today runs from `frontend/`, so the allowed root is the same as before. No unit test, with the reason given. |
| CR1-03 | nit | Fixed | `RELEASE_RESULT` starts at 0. Each red part prints its own line and sets it to 1, then `exit /b %RELEASE_RESULT%`. The `^(` `^)` escapes keep the first `echo` inside its block. "all green" prints only at 0. Not run, with the reason given. |
| CR1-04 | nit | Fixed | The header is re-wrapped to the width of its neighbours. |
| CR1-05 | nit | Fixed | `os.environ.pop("E2E_LEVEL", None)` runs after `expand_level` and before `os.environ.update(level_env)`, so a Normal run still sets it. Two `TestLevels` tests, the first with its red result recorded. |

## Is a run needed before the release?

No separate run is needed. The release's own `release-tests.bat` runs both changes:

- `vite.config.js` (CR1-02) gives the same allowed folder as before for every start from
  `frontend/`, the release worktree's included. The coder's targeted run already started the dev
  server with it. The release's Full run starts it again in the worktree, where the
  `node_modules` junction is the case D12 is about.
- The release script's closing lines (CR1-03) print on every release. A green release shows
  "all green" and exits 0. The one path no run shows is "both parts red", and its code reads
  correctly. A wrong exit code there would only stop a release, never let a red one pass.

## Checked and found consistent

- `list_groups` still returns `(None, …)` for output that is not JSON (D7), now with stderr
  first.
- `main()` order: level refusal → `E2E_LEVEL` pop → level environment → lock → `run()`. The
  `--list` run, the lanes and `single_stack` inherit `os.environ`, so all see the same level.
- `release-tests.bat`: the e2e report is still copied before the worktree is removed, and the
  junction is still removed before the unlock.
- The fix round's impl-report section is in scope A. It names its runs and the two changes it
  did not run, with reasons. "Docs updated: none" is right: no fix changes what a doc
  describes.

## Manual browser check

None. The step changes test tooling only, and the brief lists no real-device check.
