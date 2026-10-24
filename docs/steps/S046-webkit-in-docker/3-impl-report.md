```
Step: S046 — iPhone browser tests in a Docker container
Doc: impl-report
Author: Coder (Sonnet)
Date: 25-10-2026
```

# S046 — implementation report

`phone-webkit` now runs in a Linux container and passes on this PC at 125 % display scale. The full e2e suite gave 455 passed, 7 skipped, 0 failed. All four unit suites pass. One small addition to the brief (a `chown` of the npm volume, Decisions 1).

## 1. What was built

- **A WebKit server in Docker.** When a run includes `phone-webkit`, `run_lanes.py` starts one container `yantra-e2e-webkit` from `mcr.microsoft.com/playwright:v<version>-noble`. It runs `playwright run-server` and is published on `127.0.0.1:3999` only.
- **`phone-webkit` connects to it** (`connectOptions` with `exposeNetwork: "<loopback>"`), so the lanes' Vite and backend stay on the host.
- **Opt-out.** `E2E_WEBKIT=native` runs WebKit on Windows as before (S045's guard then skips it). A run naming projects without `phone-webkit` starts no container.
- **Failure messages.** The run stops before any lane, with a message naming the cause and both ways out, for: image pull failed, port 3999 in use, old container not removable, no "Listening" in 60 s.

## 2. How it works

Inside `one_run_at_a_time()`, `main()` calls `needs_webkit_server(args, E2E_WEBKIT)`. If yes, `webkit_server(version)`:

1. `docker rm -f yantra-e2e-webkit`, then checks the name is gone.
2. Pulls the image when `docker image inspect` fails (announced, no time limit).
3. Checks that 127.0.0.1:3999 is free.
4. Runs a throw-away `chown` of the npm-cache volume (Decisions 1).
5. Starts `docker run --rm --init --user pwuser … -p 127.0.0.1:3999:3000 -v yantra-e2e-npm:/home/pwuser/.npm …` attached, output to `scratch/e2e-lanes/webkit.log`.
6. Waits up to 60 s for "Listening on ws://".
7. Yields `ws://127.0.0.1:3999/`, which `main()` puts in `E2E_WEBKIT_WS`. Every lane and the `lanes == 1` run inherit it, and `playwright.config.js` reads it.
8. In `finally`, `docker rm -f` again.

The version is read from `frontend/node_modules/@playwright/test/package.json`. The `.bat` installs only Chromium natively unless `E2E_WEBKIT=native`.

## 3. Files touched

- `tooling/e2e/run_lanes.py`: the container logic, pure helpers, docstring.
- `frontend/playwright.config.js`: `phone-webkit` `connectOptions` when `E2E_WEBKIT_WS` is set.
- `tooling/run-e2e-tests.bat`: header comment; step 3 installs only Chromium unless `E2E_WEBKIT=native`.
- `tooling/tests/test_run_lanes.py`: 8 tests (container decision per args and mode, version read, `docker run` arguments, failure messages).
- `.claude/CLAUDE.md`: § Browser tests (S024) and § SMTW-Review's *Browser tests* point.
- `docs/steps/S046-webkit-in-docker/1-brief.md`: Status `In code review`. The README index row is left to the orchestrator.

`frontend/e2e/support/test.js` is not touched (S045's).

## 4. Decisions taken

1. **Departure: one extra `docker run … chown`.** A new named volume is owned by root, so `npx` as `pwuser` failed with EACCES (found in the first trial; log `webkit.log`). Each run now does `docker run --rm --user root -v yantra-e2e-npm:/home/pwuser/.npm <image> chown pwuser:pwuser /home/pwuser/.npm` (about 1 s, idempotent). The brief did not foresee it.
2. **Port check by a socket probe** before `docker run` (round 1 dropped the "port is already allocated" fallback, CR1-02).
3. **`--project` forms.** Read as Playwright 1.64.1 reads them (round 1, CR1-01); this is not in the brief but a run could otherwise start a needless container.
4. `WebkitUnavailable` is a small exception so `main()` prints the message and returns 1 without a traceback.

## 5. Not done, deferred, assumed

- Nothing tuned (BR1-05): no `--ipc=host`, no WebKit lane cap. No WebKit crash seen in six lanes on one container (below).
- The README index row is left to the orchestrator.
- The "name taken after `docker rm -f`" message is unit-tested only; it cannot be reproduced without breaking Docker.
- **Assumed:** the first `npx` fetch of `playwright` needs the internet once, then the volume holds it.

## 6. Tests run

- **Unit/full:** `YANTRA_TEST_RUN=s046c1 tooling/run-tests.bat`: backend 2964 passed, frontend 168 passed, deps 42 passed, tooling 123 passed. ALL SUITES PASSED. `vite build` not run: no frontend source changed.
- **Full e2e** (`tooling/run-e2e-tests.bat`, no arguments, 6 lanes, 2:49 to 2:56, 384 s) on this PC at 125 % scale:

| Project | Passed | Failed | Skipped |
|---|---|---|---|
| phone-chromium | 152 | 0 | 2 |
| phone-webkit (in the container) | 151 | 0 | 3 |
| desktop-chromium | 152 | 0 | 2 |
| Total | 455 | 0 | 7 |

  The 7 skips are the specs' own browser-specific skips (notifications, one `screens` test), not S045's guard. The known flakes (S045 #2, #3) did not occur. The WebKit run time is not separable from the Chromium projects' in the shared lanes; the whole suite took 384 s. No WebKit crash or `/dev/shm` problem appeared. `docker ps -a` after the run: no container left.
- **Native path:** `E2E_WEBKIT=native tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit`: 9 skipped, 0 passed, no container started (S045's guard fires).
- **No container without phone-webkit:** `e2e/labels.spec.js --project=desktop-chromium`: 4 passed, no "WebKit server up" line, no container.
- **Failure cases** (driven by calling `webkit_server` directly): the wrong tag `0.0.1` gives the pull message; a dummy listener on 3999 gives the port message; both stop before any lane. A leftover `yantra-e2e-webkit` container (a `sleep 300` of the same image) was removed and the server then started. Each message was printed with both ways out.

## Docs updated

- `.claude/CLAUDE.md` § Browser tests (S024): the container, port 3999, `E2E_WEBKIT=native`, volume, 2.5 GB first pull, Chromium-only install; and § SMTW-Review's *Browser tests* point.
- `tooling/e2e/run_lanes.py` docstring and `tooling/run-e2e-tests.bat` header (BR1-10).
- None needed: `docs/schema.md`, `Plan.MD`, `device-checks.md` (the brief has no real-device check), `example_secrets_app.py`, `Keycloak.md`.

## Manual checks

- [auto] `phone-webkit` passes at 125 % scale in the container with counts for all three projects — full run above (no single test file).
- [x] The container is gone after the run — by the coder, 25-10-2026, run by hand (`docker ps -a` after the full run, 0 containers).
- [auto] A run with only `desktop-chromium` starts no container — run above; `test_run_lanes.py::TestWebkitServer::test_a_run_without_phone_webkit_starts_none`.
- [auto] The container decision, version read, `docker run` arguments, failure messages — `tooling/tests/test_run_lanes.py::TestWebkitServer`.
- [x] Pull failure, port taken, leftover container (BR1-01, BR1-04) — by the coder, 25-10-2026, run by hand as above (no test file).
- On a real device: none.

## Fix rounds

### Round 1

Tooling suite after the round: 129 passed (123 before, 6 new). Full `tooling/run-tests.bat` (`YANTRA_TEST_RUN=s046c2`): backend 2964, frontend 168, deps 42, tooling 129, all passed.

Red first: I wrote the six new tests before the fix and ran them against the old code: 6 failed (wildcard/upper-case/variadic forms, `named_projects` forms, `lane_count`, `E2E_WEBKIT=Native`, early exit said "did not start in 60 s", `chown` failure not caught). After the fix: 129 passed.

- **CR1-01 Fixed.** `named_projects` reads `--project=a` and `--project a b ...` (names up to the next option). No `-p`, no comma split. `needs_webkit_server` starts the container unless every named project is a plain name (no `*`) that is not `phone-webkit` (case-insensitive). Tests: `TestWebkitServer::test_project_forms_as_playwright_reads_them`, `test_named_projects_reads_only_playwrights_forms`. Fails without the fix: `--project=phone-*` returned False. Passes with it.
- **CR1-02 Fixed.** An early exit now raises its own message ("The WebKit server stopped before it was ready. See scratch/e2e-lanes/webkit.log.", with both ways out). The 60 s message is for the deadline only. The "port is already allocated" branch is dropped; the socket probe keeps the `port` message. Test: `TestWebkitStart::test_a_container_that_stops_early_is_not_called_a_timeout`. Fails without the fix: the message contained "did not start in". Passes with it.
- **CR1-03 Fixed.** The `chown` run's return code is checked. On failure the run prints Docker's error and "The cache folder of the WebKit server could not be prepared. Check that Docker Desktop is running, then run again." plus both ways out. Test: `TestWebkitStart::test_a_failed_cache_folder_hand_over_stops_the_run`. Fails without the fix: no exception was raised and the run went on to the 60 s message. Passes with it.
- **CR1-04 Fixed.** `lane_count` uses `named_projects`. Test: `TestWebkitServer::test_lane_count_uses_the_same_parse`. Fails without the fix: the old count was 1 project for `--project a b`. Passes with it. A wildcard counts as one project, so a wildcard run may get fewer lanes than it has groups; it only costs time.
- **CR1-05 Fixed.** The two hand-run checks are now `- [x] … by the coder, 25-10-2026, run by hand`, not `[auto]`.
- **CR1-06 Fixed.** `webkit_mode()` lowercases `E2E_WEBKIT`, as the `.bat` does (`if /i`). Test: `test_native_mode_is_read_case_insensitively`. Fails without the fix: `Native` still started the container. Passes with it.

Browser runs (targeted; `playwright.config.js` not changed, so no full suite):

| Command | Result | Container |
|---|---|---|
| `e2e/screens.spec.js` | 26 passed, 1 skipped, 3 lanes | started ("WebKit server up") |
| `e2e/screens.spec.js --project=desktop-chromium` | 8 passed | not started |
| `e2e/screens.spec.js --project=phone-*` | 18 passed (phone-chromium and phone-webkit) | started |

`docker ps -a` after each run: no `yantra-e2e-webkit` left.

## Docs updated (round 1)

- None needed: `.claude/CLAUDE.md` § Browser tests already says a run naming projects without `phone-webkit` starts no container; the exact `--project` rule is in the `run_lanes.py` docstring (updated). `tooling/run-e2e-tests.bat` unchanged (it already compared `E2E_WEBKIT` with `/i`).
