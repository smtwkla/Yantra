```
Step: S046 — iPhone browser tests in a Docker container
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 967e888 + uncommitted S037, S038, S039, S040, S043 (and S045 in progress, test files only; it owns `frontend/e2e/support/test.js`)

**Verdict: no blocker or major finding. 5 minor, 6 nits.** The design holds: the pinned
Playwright (1.64.1, `@playwright/test` and `playwright-core` installed the same) supports
`connectOptions.exposeNetwork` in a project's `use`, `"<loopback>"` matches `127.0.0.1`, and
`run-server` takes several clients. The light track holds (no app code, Playwright's documented
pattern, six files); this is the only review round. The minor findings are gaps the coder would
otherwise fill alone: the leftover container, the lost logs of a failed start, the npm download
at every container start, the wrong "Docker is not running" case, and no plan for a slow remote
WebKit. Facts file read: `scratch/brief-facts-S046.md`.

## Minor

### BR1-01 — minor — a container left by a killed run blocks the next run

- **Problem.** `docker run -d --rm --name yantra-e2e-webkit`: `--rm` removes the container only
  when it stops. A host process killed hard (PyCharm's stop button, a closed terminal, a crash
  before the `finally`) leaves it running, detached. The next run's `docker run --name
  yantra-e2e-webkit` then fails with Docker's name conflict, not with the § 1.4 message. After a
  Playwright update the leftover is also the old version, which 1.64's server would refuse.
- **Why it matters.** The code reviewer and `/smtw-review` run the suite in the background; a
  stuck run will be killed now and then. The user then sees a Docker error and has to know the
  container's name.
- **Options.** (a) `docker rm -f yantra-e2e-webkit` before `docker run`, errors ignored, inside
  `one_run_at_a_time()`: the lock guarantees that no other run owns the name. **Recommended.**
  (b) A random name per run: orphans stay, and port 3999 stays taken.

### BR1-02 — minor — a failed container start leaves no log to read

- **Problem.** With `-d --rm`, a container that exits early (the `npx -y` download fails, the
  server crashes) is removed together with its logs. The "Listening" wait then ends after 60 s
  with "no such container", and nobody can see why.
- **Why it matters.** The cases of BR1-03 and BR1-04 all end here; without the log the only
  fix is to run the `docker run` line by hand.
- **Options.** (a) Start the container attached, not detached: `subprocess.Popen([...docker run
  --rm --name … -p … --init <image> …], stdout=scratch/e2e-lanes/webkit.log)`, and wait for
  "Listening on ws://" by reading that file; the log stays after the run like the lane logs, and
  the end is still `docker rm -f` (BR1-01 covers a leftover). **Recommended:** the same shape as
  the lanes, and no `docker logs` polling. (b) Keep `-d` but drop `--rm`, print `docker logs
  yantra-e2e-webkit` on a failed wait, and rely on `docker rm -f` at start and end.

### BR1-03 — minor — every container start downloads `playwright` from npm

- **Problem.** The image has no `playwright` package: in `mcr.microsoft.com/playwright:
  v1.64.1-noble` there is no `/ms-playwright-agent`, `npm ls -g` lists only npm, corepack and
  yarn, and there is no npx cache (checked 25-10-2026 with `docker run --rm --entrypoint sh`).
  `npx -y playwright@1.64.1` therefore fetches `playwright` and `playwright-core` from the npm
  registry at each start; `--rm` drops the cache. The brief does not say so.
- **Why it matters.** Every e2e run needs internet, the download runs inside the 60 s wait,
  and a slow registry fails the run at the wait (then BR1-02).
- **Options.** (a) Accept and state it: in the brief and CLAUDE.md § Browser tests ("the
  WebKit server needs internet at each run"), with the wait at 120 s. (b) A named volume for
  npm's cache, `-v yantra-e2e-npm:/root/.npm` (or `/home/pwuser/.npm`, see BR1-08): one flag,
  the download happens once per version, later runs work offline. **Recommended.** (c) A
  derived image with the package pre-installed: a Dockerfile and a build step, too much for
  this.

### BR1-04 — minor — "Docker is not running" is not a case the runner can see

- **Problem.** § 1.4 and § 5 ("Docker stopped: the run stops with the § 1.4 message before any
  lane") assume `run_lanes.py` meets Docker Desktop down. It never does: step 1 of
  `run-e2e-tests.bat` (`docker compose ps`) fails first, with "The dev DB container is not
  running. Start it with tooling\dev\dev-db-up.bat." The cases the runner does meet are: the
  image cannot be pulled (offline on the first run of a version), the container does not start
  (port 3999 busy, the name taken, BR1-01), and no "Listening" line within the wait (BR1-02,
  BR1-03).
- **Why it matters.** The coder would write a test for a case that cannot happen, and the
  message would name a wrong cause (scope B: say what happened).
- **Options.** (a) Rewrite § 1.4 and the § 5 check for the real cases: one message "The WebKit
  browser server did not start, so the iPhone tests cannot run. <docker's last stderr line or
  the log path>. Run again with --project=phone-chromium --project=desktop-chromium, or with
  E2E_WEBKIT=native." The § 5 check becomes "the image tag made wrong for one run" (already
  listed) and "port 3999 held by another process". **Recommended.** (b) Keep a Docker-down
  check in `run_lanes.py` too (`docker info`): redundant with step 1.

### BR1-05 — minor — no plan if the remote WebKit is slow

- **Problem.** Fact 5 leaves "six lanes on one `run-server` under load" to the coder's full
  run, but says nothing about what the coder does if `phone-webkit` tests then hit the 60 s test
  timeout or the 10 s expect timeout. Every page load in Vite dev mode is some hundred module
  requests, and each one is tunnelled back through the lane's worker process (that is how
  `exposeNetwork` works). A WebKit crash in the container ("Target crashed") is the other
  possible symptom (Docker's default `/dev/shm` is 64 MB).
- **Why it matters.** The coder would raise timeouts or add Docker flags alone, which changes
  what a green run means.
- **Options.** (a) State the rule: the coder records the three projects' run times from the
  lane logs (today's native times from `scratch/s045-e2e-full.log` for comparison) and reports
  them at gate B; a timeout or crash that only `phone-webkit` shows is reported with counts, and
  nothing is tuned without the user. **Recommended.** (b) Decide now: `timeout: 90_000` on the
  `phone-webkit` project and `--shm-size=1g` on the container, so the first full run already has
  them. Fewer round trips, but settings nobody has measured.

## Nits

- **BR1-06** (nit) § 1.3: the server compares major.minor only (`playwrightServer.ts`,
  `userAgentVersionMatchesErrorMessage`: `1.64` against `1.64`); a patch update still connects.
  Say "same major.minor"; the tag follows the installed version anyway.
- **BR1-07** (nit) § 3 `run_lanes.py` row: say that `webkit_server()` wraps `run()` inside
  `one_run_at_a_time()` (the name `yantra-e2e-webkit` and port 3999 are shared by all runs, so
  the lock must cover the container), and that the `lanes == 1` path gets `E2E_WEBKIT_WS` too,
  as § 1.2 says.
- **BR1-08** (nit) § 1.1 `docker run`: Playwright's documented line runs the server as `--user
  pwuser --workdir /home/pwuser` (the image has `pwuser`, uid 1001; the brief's line runs as
  root). Either add it, or say root is accepted (WebKit needs no sandbox flag). The cache path
  of BR1-03 (b) follows the choice.
- **BR1-09** (nit) § 5 fact / § 6 Q5: the first-run pull (2.5 GB on disk here, `docker image
  ls`) must happen before the "Listening" wait starts, not inside it: an explicit `docker image
  inspect` → `docker pull` step with one line printed ("Pulling the WebKit browser image, about
  2 GB, once per Playwright version"), so a silent minute is explained.
- **BR1-10** (nit) § 3 docs pass: besides CLAUDE.md § Browser tests, update § SMTW-Review's
  "Browser tests" point ("needs the dev DB container up" → and Docker for the WebKit server,
  the first run pulls the image), `run_lanes.py`'s docstring and the `.bat` header: the run now
  needs the dev DB container, the WebKit image and (BR1-03) the npm registry.
- **BR1-11** (nit) § 2: name ISO 27001 A.8.20 (network security: a service listens only where
  it is needed) for decision 3, the `127.0.0.1` binding; one line.

## Checked and found consistent

- `@playwright/test` and `playwright-core` are both 1.64.1; `ConnectOptions` in
  `playwright/types/test.d.ts` has `wsEndpoint`, `headers`, `exposeNetwork`, `timeout`, and
  `connectOptions` is a per-project `use` option, so `phone-webkit` alone connects remotely.
- `"<loopback>"` matches `localhost`, `*.localhost`, `127.0.0.1`, `[::1]`; the lanes' `baseURL`
  and `YANTRA_API_URL` are `http://127.0.0.1:<port>` (`stack.js`), so both are tunnelled.
- `run-server` (hidden command) takes `--port`, `--host`, `--path` (default `/`),
  `--max-clients` (default unlimited): `ws://127.0.0.1:3999/` is right, and one server serves
  the lanes; each lane has `workers: 1`, so at most six connections.
- `devices["iPhone 14"]` has `defaultBrowserType: "webkit"`, so `browserName` stays `"webkit"`
  and S045's `windowWidthGuard` still runs; the probe's 390 px means it passes. The brief does
  not edit `test.js`; S045's status names S046 for CR1-03 and Q3 asks the user at gate A.
- The e2e lock: `main()` holds `one_run_at_a_time()` around `run()`; a container started in
  `run()` is covered (BR1-07 asks the brief to say so).
- `webServer`, `globalSetup` (the seed) and the merge stay on the host, untouched; no spec uses
  `toHaveScreenshot`, so Linux fonts change nothing.
- Port 3999 is free here (`netstat`), no `yantra-e2e*` container exists, and the image is local.
- `lane_count` already keys on `--project=` arguments; the container decision can use the same
  parse, and `tooling/tests/test_run_lanes.py` is the right home for its tests.
- Step 3 of the `.bat` installing only Chromium unless `E2E_WEBKIT=native`: correct, a remote
  browser needs no local WebKit.
- Light track: no app code, migration, RBAC or locking rule; Playwright's documented remote
  pattern; six files. The docs pass names the one due doc (CLAUDE.md, a dev command) correctly.
- Standards: ISTQB test-environment fidelity is the right frame for a tooling step; no
  maintenance standard applies.
