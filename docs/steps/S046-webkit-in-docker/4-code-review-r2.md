```
Step: S046 — iPhone browser tests in a Docker container
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. All six r1 findings are fixed. 0 blocker, 0 major, 0 minor, 2 nits.**

Reviewed: the snapshot `refs/steps/S046` (15eaa41), not the working tree. Files re-read:
`tooling/e2e/run_lanes.py` (in full), `tooling/tests/test_run_lanes.py` (the S046 tests),
`3-impl-report.md` § Manual checks and § Fix rounds / Round 1. Diff read with
`git diff -w --ignore-cr-at-eol refs/steps/S040 refs/steps/S046`. Playwright 1.64.1's CLI
source read in `frontend/node_modules`: `playwright/lib/program.js:210` (the option),
`playwright-core/lib/utilsBundle.js:55070-55150` (the bundled Commander `parseOptions`), and
`playwright/lib/runner/index.js:2134` (`filterProjects`).

## Tests

- **Not re-run.** The coder's round-1 run stands: `tooling/run-tests.bat` with
  `YANTRA_TEST_RUN=s046c2`, backend 2964, frontend 168, deps 42, tooling 129, all passed. No
  finding of mine needs a run.
- **Browser tests: not re-run** (standing rule, 25-10-2026). The coder's targeted runs are the
  right ones. The fix round changed only `run_lanes.py`, not `playwright.config.js` or any
  shared frontend code, so `screens.spec.js` in three forms is enough:
  - no `--project`: 26 passed, 1 skipped, container started;
  - `--project=desktop-chromium`: 8 passed, no container;
  - `--project=phone-*`: 18 passed, container started.

  `docker ps -a` showed no leftover container after each run.

## Earlier findings

| ID | Status | Verified |
|---|---|---|
| CR1-01 | Fixed | See "CR1-01 against Playwright's CLI" below. |
| CR1-02 | Fixed | `run_lanes.py:145,189-190`: a stopped process now gives the "stopped" message. The 60 s message is only for the deadline. The "port is already allocated" branch is gone. |
| CR1-03 | Fixed | `run_lanes.py:179-182`: a failed `chown` raises `WebkitUnavailable` with Docker's stderr, the "cache" line and both ways out. The container is not started. |
| CR1-04 | Fixed | `run_lanes.py:94`: `lane_count` uses `named_projects`. The wildcard trade-off is accepted (see below). |
| CR1-05 | Fixed | `3-impl-report.md:85,88`: the two checks run by hand are `[x] … run by hand`, not `[auto]`. |
| CR1-06 | Fixed | `run_lanes.py:102`: `webkit_mode()` lowercases `E2E_WEBKIT`, as the `.bat`'s `if /i` does. |

### CR1-01 against Playwright's CLI

`named_projects` and `needs_webkit_server` now match how Playwright 1.64.1 reads projects:

- **`--project a b`.** The option is `--project <project-name...>`, so it is variadic. Commander
  takes the next argument as the value, then keeps taking arguments while each one does not
  start with `-`. The parse does the same (`reading` until an argument starts with `-`).
- **`--project=a b`.** Commander's `--opt=value` branch emits `a` and does not set
  `activeVariadicOption`, so `b` is a test filter, not a project. The parse also stops reading
  after `--project=…` (`reading = False`). This matches.
- **Case and wildcards.** `filterProjects` lowercases every name and turns a name with `*`
  into a pattern. The parse treats any `*` as "may match phone-webkit" and compares plain names
  case-insensitively. So the container is skipped only when every named project is a plain
  name other than `phone-webkit`. That is the rule the orchestrator asked for, and it errs
  towards the container.
- **No `-p`, no comma split.** `program.js` defines no short form for `--project` in `test`.
  `filterProjects` does not split at commas. The parse now reads `-p a` as no project and
  `--project=a,b` as the one name `a,b` (tests at `test_run_lanes.py:84-87`). With `a,b`,
  Playwright fails with "Project(s) … not found" before any test runs, so skipping the
  container is harmless.
- **Project dependencies.** `playwright.config.js` has no `dependencies`, so naming another
  project cannot pull in `phone-webkit`.

The forms the parse still reads differently are contrived and harmless. Example: an argument
after `--` is an operand to Commander, but the parse still reads a `--project=…` there. That
form changes nothing in a real run.

### CR1-02 message (scope B)

"The WebKit server stopped before it was ready. See scratch/e2e-lanes/webkit.log." is followed
by `WAYS_OUT`. It says what happened and where to find the cause, then what the user can do.
It is one short line with no blame. The log holds the cause (npx, network, port), which the
runner cannot name reliably. That is acceptable for a developer tool.

### CR1-03 failure path

The check runs before the log is opened and before `Popen`, so nothing is left to clean up. A
container never started, and the earlier `docker rm -f` already removed any old one. `main`
prints the exception text and returns 1. The order is Docker's stderr first, then the
plain line and both ways out. CR2-01 is a small polish.

### CR1-04 wildcard trade-off

A wildcard counts as one project in `lane_count`. With no spec file named, the count is
`13 spec files × 1`, so a run still gets its 6 lanes. With spec files named, a wildcard run may
get fewer lanes than its groups. Example: `screens.spec.js --project=phone-*` gets 1 lane for
2 groups. That costs time only, never a wrong result, and the coder states it. Accepted.

### Red results

The fix round names a red result for each of the six new tests, run against the old code, and
says what each one showed. Each new test fails on the old behaviour by construction:
- the wildcard and upper-case forms returned False;
- `-p a` returned `["a"]`;
- the old count was 1 project for `--project a b`;
- `Native` started the container;
- the early exit said "did not start in";
- a failed `chown` raised nothing.

## Nits

- **CR2-01** (nit) `tooling/e2e/run_lanes.py:182`: when Docker writes nothing to stderr, the
  message starts with an empty line. Join only the non-empty parts, e.g.
  `"\n".join(filter(None, [handed_over.stderr.strip(), webkit_failure("cache")]))`.
- **CR2-02** (nit) `tooling/tests/test_run_lanes.py:155-174`: the two `TestWebkitStart` tests
  use `try/except/else` with a hand-raised `AssertionError`. `with pytest.raises(run_lanes.WebkitUnavailable) as stop:`
  says the same in two lines.

## Checked and found consistent

- The fix round's diff is limited to `run_lanes.py`, `test_run_lanes.py` and the impl report.
  It changed no `.bat`, config, frontend or doc file. No new fault came in with it.
- `needs_webkit_server` returns True for no named project, so a full run and a run of spec
  files only still start the container.
- `E2E_WEBKIT=native` still wins over any `--project`.
- The new "cache" and "stopped" messages both end with `WAYS_OUT`. The tests assert
  `E2E_WEBKIT=native` in both.
- The module docstring states the new rule (lines 32-33). The impl report's "Docs updated
  (round 1)" correctly says no other doc is due: `.claude/CLAUDE.md` § Browser tests already
  says a run naming projects without `phone-webkit` starts no container.
- Scope A of the fix round's text holds: the point comes first and each finding has a status,
  its tests and its red result.
- The duplicate `E2E_LANES` check in `run()` (`run_lanes.py:314-316`) was there before S046.
  It is not part of this step.

## Manual browser check for the user

None for this step. The acceptance run (a full e2e run at 125 % with `phone-webkit` green in
the container) is the coder's recorded round-0 run. The user's full run before the next
release repeats it.
