```
Step: S046 — iPhone browser tests in a Docker container
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. 2 minor, 4 nits.** The design is built as
approved: one `run-server` container inside the e2e lock, bound to `127.0.0.1:3999`, the image
tag and the `npx` package pinned to the installed `@playwright/test`, removed on every exit
path, and `phone-webkit` connected with `exposeNetwork: "<loopback>"`. The two minor findings
are about edges: the `--project` parse does not match how Playwright reads projects, and an
early container exit is reported as a 60 s timeout.

Reviewed: `git diff -w --ignore-cr-at-eol refs/steps/S040 --` `tooling/e2e/run_lanes.py`,
`frontend/playwright.config.js`, `tooling/run-e2e-tests.bat`, `tooling/tests/test_run_lanes.py`,
`.claude/CLAUDE.md`, the brief's status line, and the untracked `3-impl-report.md`;
`run_lanes.py` read in full. `frontend/e2e/support/test.js` is identical to `refs/steps/S045`
and `refs/steps/S040` (`git diff --ignore-cr-at-eol --stat` empty): S046 did not change it.

## Tests

- **Tooling suite, my run:** `YANTRA_TEST_RUN=s046cr1 tooling/run-tooling-tests.bat`: 123
  passed (`scratch/tooling-tests-s046cr1.log`). No backend or frontend code changed, so I did
  not re-run those suites; the coder's run (backend 2964, frontend 168, deps 42, tooling 123)
  stands.
- **Browser tests:** not re-run (standing rule, 25-10-2026). The coder ran the **full** suite,
  which is the right choice: the step changes `playwright.config.js`, which every spec uses.
  Result: 455 passed, 0 failed, 7 skipped; `phone-webkit` in the container 151 passed. The
  native path and the no-container path were also run. No finding of mine needs a browser run.

## Minor

### CR1-01 — minor — `tooling/e2e/run_lanes.py:82-101`: the project parse differs from Playwright's

- **Problem.** `named_projects` reads `--project=a`, `--project a`, `-p a` and comma lists.
  Playwright 1.64.1 reads projects differently (`node_modules/playwright/lib/program.js:210`,
  `runner/index.js` `filterProjects`):
  - `--project <project-name...>` is variadic: `--project a b` names both;
  - names match case-insensitively and support `*` wildcards;
  - there is no `-p` option and no comma split.

  So the parse handles two forms Playwright does not have, and misses three it does have.
- **Failure scenario.** The user runs `tooling/run-e2e-tests.bat --project=phone-*` (or
  `--project=Phone-WebKit`, or `--project phone-chromium phone-webkit`).
  `needs_webkit_server` returns `False`, so no container starts and `E2E_WEBKIT_WS` is unset.
  Playwright still selects `phone-webkit` and runs it on Windows. If an old WebKit is still in
  the browser cache, S045's guard skips every iPhone test on the 125 % display, and the run is
  green with the iPhone tests silently skipped. Without a cached WebKit, every `phone-webkit`
  test fails with "Executable doesn't exist", because the `.bat` now installs only Chromium.
- **Suggested fix.** Turn the decision around, so an unknown form errs towards the container.
  Start no container only when every named project is a plain name (no `*`) and none equals
  `phone-webkit` case-insensitively. Collect every value after `--project` up to the next
  argument that starts with `-` (variadic). Drop the `-p` and comma forms. Add one unit test
  each for the wildcard, the upper-case name and the variadic form.

### CR1-02 — minor — `tooling/e2e/run_lanes.py:170-174`: an early exit says "did not start in 60 s"

- **Problem.** When the container exits before "Listening", the cause is `"port"` only if the
  log has "port is already allocated", and `"timeout"` otherwise. The timeout message says "The
  WebKit server did not start in 60 s". The "port is already allocated" text is in practice
  unreachable: Docker Desktop's proxy listens on host `127.0.0.1:3999` for a container that
  publishes the port, so `_port_in_use()` catches that case first. The early exits that do
  happen have other causes. Examples:
  - `npx` cannot fetch `playwright` on the first run of a version without internet;
  - Docker Desktop answers "Ports are not available" for a port in a Windows excluded range
    (`netsh int ipv4 show excludedportrange`; today 3999 is not in one);
  - a permission error on the npm cache (CR1-03).
- **Failure scenario.** The first run after a Playwright update happens offline. The pull of
  the image succeeded earlier, but `npx` fails at once. The user reads "The WebKit server did
  not start in 60 s" after about 2 s and looks for a slow machine, not a network fault (scope
  B: say what happened).
- **Suggested fix.** Give the early-exit path its own line: "The WebKit server stopped before it
  was ready. See scratch/e2e-lanes/webkit.log." Then add `WAYS_OUT`, as for the other causes.
  Keep the 60 s message for the deadline only. Either drop the "port is already allocated"
  branch, or also match Docker Desktop's "Ports are not available". Update the message test
  with the new cause.

## Nits

- **CR1-03** (nit) `tooling/e2e/run_lanes.py:162-164`: the `chown` run's return code is
  ignored. If it fails, the server then fails with EACCES, and the user gets CR1-02's message.
  Check `returncode` and raise `WebkitUnavailable` with the log path, or at least print Docker's
  stderr.
- **CR1-04** (nit) `tooling/e2e/run_lanes.py:71-79`: `lane_count` keeps its own `--project`
  count (`a.startswith("--project")`). Use `named_projects(args)` there too, so the lane count
  and the container decision read the arguments the same way (BR1-02's "checked" note proposed
  the same parse).
- **CR1-05** (nit) `3-impl-report.md:85,88`: `[auto]` means a passing automated test (README §
  Manual checks). "Container gone, `docker ps -a`" and "pull failure, port taken, leftover
  container, run by hand" are recorded observations. List them as done by hand, for example
  `- [x] … — by the coder, 25-10-2026, run by hand`, not as `[auto]`.
- **CR1-06** (nit) `tooling/run-e2e-tests.bat:35` against `run_lanes.py:286`: the `.bat` compares
  `E2E_WEBKIT` case-insensitively (`if /i`), Python exactly (`== "native"`). With
  `E2E_WEBKIT=Native`, the `.bat` installs WebKit and Python still starts the container. Use
  `.lower()` in Python.

## The points the orchestrator asked about

- **The `chown` departure (Decisions 1): sound, minimal and safe; keep it.** A new named volume
  takes the mount point's ownership from the image. The image has no `/home/pwuser/.npm`, so
  Docker creates the folder as root and `npx` as `pwuser` fails. The `chown` is not recursive,
  which is enough: everything below the folder is then written by `pwuser`. It runs as root
  only inside a throw-away container and touches only the volume. It costs about 1 s per run and
  is idempotent. Alternatives:
  - mount the volume on `/home/pwuser`, which the image owns as `pwuser`, so Docker copies that
    ownership: no extra run, but the volume then holds the whole home folder;
  - point npm at a folder `pwuser` owns (`-e npm_config_cache=/tmp/npm-cache` with the volume
    there): no extra run, one more environment variable.

  Neither is clearly better, so the brief would not prefer one. The departure is reported in
  Decisions taken, as the rules ask. Only CR1-03 applies.
- **Socket probe (Decisions 2): needed, in scope.** It is how the brief's § 1.4 port message is
  reached when a host program holds the port: Docker Desktop's own error for that case does not
  contain "port is already allocated". The probe runs inside the lock, so no other e2e run can
  take the port between the probe and `docker run`. The fallback string is the weak part
  (CR1-02).
- **`--project` forms (Decisions 3): the parse itself is needed** (brief § 1.5: a run without
  `phone-webkit` starts no container), but the forms are wrong (CR1-01). `-p` and comma lists
  go beyond Playwright's own CLI and should be dropped, not extended.
- **`WebkitUnavailable` (Decisions 4): needed, in scope.** It is a small exception that turns
  the § 1.4 messages into a printed line and exit code 1, without a traceback. It has no other
  use and adds no layer.
- **Container lifecycle.**
  - The container is removed in `finally` on success, failure, an exception in `run()` and
    Ctrl+C: `KeyboardInterrupt` passes through `finally`, and Docker's signal proxy also stops
    the attached `docker run`.
  - A container left by a hard-killed run is removed first, and the name is checked after the
    removal. The coder ran this case.
  - Everything runs inside `one_run_at_a_time()`, so the fixed name and port are never shared
    by two runs.
  - The `lanes == 1` path inherits `E2E_WEBKIT_WS` through `os.environ`.
- **Network exposure.**
  - The host side is `127.0.0.1:3999` only (`-p 127.0.0.1:3999:3000`, unit-tested).
  - `0.0.0.0` inside the container is Playwright's documented line and is needed for the port
    publish to work.
  - `exposeNetwork: "<loopback>"` lets the remote browser reach only the host's loopback,
    through the Playwright client of each lane. The browser gets no wider LAN access.
  - The `run-server` endpoint has no token, so any local process could connect during a run.
    That is acceptable on a single-user dev PC, and the brief accepted it (decision 3,
    ISO 27001 A.8.20).
- **Pinned versions.** `@playwright/test`, `playwright` and `playwright-core` are all 1.64.1 in
  `node_modules`, and `package.json` pins `1.64.1` exactly. The image tag and the `npx` package
  are both built from that one version (`playwright_version()`), so they match by construction.
- **Messages (scope B).** The four § 1.4 messages are the brief's text: what happened, then what
  to do, then both ways out (`WAYS_OUT`). The pull announcement says what is happening and why
  it takes time. The early-exit wording is CR1-02.
- **Docs pass.**
  - `.claude/CLAUDE.md` § Browser tests describes the container, the port, the volume, the
    first pull, `E2E_WEBKIT=native` and the Chromium-only install correctly.
  - The § SMTW-Review *Browser tests* point names the Docker need and the native way out.
  - The `run_lanes.py` docstring and the `.bat` header are updated (BR1-10).
  - No schema, Plan.MD, device-check, secrets or Keycloak doc is due.
  - The README index row is left to the orchestrator; it already reads `In code review`.

## Checked and found consistent

- Scope matches brief §§ 1–3:
  - `docker rm -f` comes first, then the announced pull with no time limit, then the attached
    start with its log;
  - the "Listening" wait is 60 s, and `docker rm -f` runs at the end;
  - the version is read from `@playwright/test`;
  - `E2E_WEBKIT=native` skips the container, and the `.bat` installs only Chromium otherwise.
- `docker run` arguments match the brief: `--rm --init --user pwuser --name yantra-e2e-webkit
  -p 127.0.0.1:3999:3000 -v yantra-e2e-npm:/home/pwuser/.npm`, `npx -y playwright@<version>
  run-server --port 3000 --host 0.0.0.0`.
- `playwright.config.js`: `connectOptions` is set only when `E2E_WEBKIT_WS` is set, so the
  native path is unchanged. `devices["iPhone 14"]` keeps `browserName` WebKit, so S045's guard
  still runs and passes at 390 px.
- No business code, migration, RBAC or locking changed. The light track holds (6 files).
- Tests cover the brief's § 5 unit list: the decision per arguments and mode, the version
  read, the `docker run` arguments (loopback, `--rm`, `--init`, `--user`, attached), and every
  message with both ways out. They test only the forms the parse claims; CR1-01 adds the
  missing ones.
- The § 5 important check (full run at 125 %, `phone-webkit` green in the container, all three
  projects counted) has a recorded passing run, and the brief has no real-device check.
- BR1-05: nothing was tuned; no WebKit crash was seen in six lanes. The impl report states
  that the WebKit run time cannot be separated from the Chromium projects' times.
- Comments say why (the `chown`, the leftover container, `exposeNetwork`). No deprecated API.
  No exception is swallowed except the `chown` return code (CR1-03).

## Manual browser check for the user

None for this step. The acceptance run (a full e2e run at 125 % with `phone-webkit` green) is
the coder's recorded run. The user's pre-release full run will repeat it.
