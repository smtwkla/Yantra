```
Step: S046 — iPhone browser tests in a Docker container
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: light
Status: Approved (25-10-2026 by KLA; open questions 1–5 as proposed, incl. 3: S045's guard skips on a native WebKit run); coded after S045
Baseline: 967e888 + uncommitted S037, S038, S039, S040, S043 (and S045 in progress, test files only; it owns `frontend/e2e/support/test.js`)
```

# S046 — iPhone browser tests in a Docker container

**The need (KLA, 25-10-2026).** "I need the 125% scaling on this machine, as this user. Is
there any way we can run the tests on a VM or container that does not inherit this?" Then: "for
iphone tests, let's do the docker way."

**Why the iPhone tests fail here.** On Windows, Playwright's WebKit multiplies the emulated
device's pixel ratio by the display scale: at 125 % an iPhone 14 window is 312 px wide
(`devicePixelRatio` 3.75), not 390 (S040 CR r2, S045 #6). Chromium applies the emulation exactly,
so only `phone-webkit` is hit. S045 added a guard (`frontend/e2e/support/test.js`,
`windowWidthGuard`) that stops such a run with the reason; whether it fails or skips is still
the user's open question there.

**Track: light.** No app code, no migration, no RBAC, no locking; tooling and test config only,
on Playwright's documented remote-browser pattern; about 7 files.

**Coded after S045** (S045 owns `frontend/e2e/support/test.js`; this step does not edit it).

## 1. What will be built

1. **WebKit runs in a Linux container; everything else stays on the host.** When a run
   includes `phone-webkit`, the runner starts one container from Playwright's official image,
   `mcr.microsoft.com/playwright:v<version>-noble`, running `npx -y playwright@<version>
   run-server --port 3000 --host 0.0.0.0` as `--user pwuser` (Playwright's documented line,
   BR1-08), published on `127.0.0.1:3999` only. The image ships no `playwright` npm package
   (BR1-03, checked), so `npx` fetches it from npm: a named volume `yantra-e2e-npm` on the npm
   cache (`-v yantra-e2e-npm:/home/pwuser/.npm`) keeps it after the first run. The
   `phone-webkit` project then **connects** to it (`use.connectOptions`), with
   `exposeNetwork: "<loopback>"`, so the browser's requests to `127.0.0.1:<port>` are carried
   back to the host: the lanes' Vite and backend stay where they are, on `127.0.0.1`, unchanged.
   The two Chromium projects run natively, as today.
2. **One command, as today.** `tooling/run-e2e-tests.bat` (and `tooling/e2e/run_lanes.py`)
   start the container before the lanes, **inside `one_run_at_a_time()`** (the e2e lock, BR1-07),
   and pass the address to every lane and to the single-stack (`lanes == 1`) run alike
   (`E2E_WEBKIT_WS=ws://127.0.0.1:3999/`). In order (BR1-01, BR1-02, BR1-09):
   1. `docker rm -f yantra-e2e-webkit` (a container left by a hard-killed run would else block
      the name);
   2. when the image is not present (`docker image inspect`), pull it as its own announced step
      ("Pulling the WebKit image, about 2.5 GB, once per Playwright version"), with no time limit;
   3. start the container **attached**, its output written to `scratch/e2e-lanes/webkit.log`;
   4. wait for "Listening on ws://" in that log, 60 s at most;
   5. after the run, a failed or interrupted run included, `docker rm -f` it.
   One merged report, as today.
3. **The version follows the project.** `<version>` is read at run time from
   `frontend/node_modules/@playwright/test/package.json` (today `1.64.1`), so a Playwright update
   needs no edit. A client and server of different versions refuse to connect, so this matters.
4. **When the WebKit server cannot start** (BR1-04). Docker itself being down is caught earlier,
   by the `.bat`'s dev-DB step, as today. The cases this step meets each stop the run before any
   lane, with a message that names the cause and both ways out: run without the iPhone tests
   (`--project=phone-chromium --project=desktop-chromium`), or run WebKit on Windows
   (`E2E_WEBKIT=native`):
   - the image pull fails: "The WebKit image could not be downloaded. Check the internet
     connection, then run again.";
   - port 3999 is taken: "Port 3999 is in use, so the WebKit server cannot start. Close the
     program that uses it, then run again.";
   - the container name is still taken after `docker rm -f`: "The old WebKit container could not
     be removed. Run docker rm -f yantra-e2e-webkit, then run again.";
   - no "Listening" in 60 s: "The WebKit server did not start in 60 s. See
     scratch/e2e-lanes/webkit.log."
   `E2E_WEBKIT=native` runs WebKit on Windows as today (the S045 guard then applies), for a host
   at 100 % or for comparison.
5. **A run without phone-webkit** (`--project=desktop-chromium`, …) starts no container.

### Out of scope

- The Chromium projects in Docker (they are exact on Windows; see Open question 2).
- Running the backend, Vite or the dev DB in a container for the tests (they stay on the host).
- CI (GitHub Actions).
- S045's guard: fail or skip natively stays the user's call there (Open question 3).

## 2. Standards and practice

- **Test-environment fidelity** (ISTQB: the test environment should match the operational one
  as closely as practical): an iPhone is 390 CSS px wide at a pixel ratio of 3; the container
  gives exactly that, measured (§ 5, fact 4), where the scaled Windows host cannot.
- **Reproducible tooling:** the browser comes from a pinned, published image of the same
  version as the test runner, not from the machine's settings.

## 3. Where

| File | Change |
|---|---|
| `tooling/e2e/run_lanes.py` | start and stop the WebKit container (`webkit_server()` context manager inside `one_run_at_a_time()`: `docker rm -f` first; the image pull as its own step; `docker run --rm --init --user pwuser --name yantra-e2e-webkit -p 127.0.0.1:3999:3000 -v yantra-e2e-npm:/home/pwuser/.npm …` attached, output to `scratch/e2e-lanes/webkit.log`; wait for "Listening" there; `docker rm -f` at the end); read the Playwright version; skip it when the args name projects without `phone-webkit`, or when `E2E_WEBKIT=native`; set `E2E_WEBKIT_WS` for the lanes and the `lanes == 1` run; the module docstring (BR1-10) |
| `frontend/playwright.config.js` | `phone-webkit`: `connectOptions: { wsEndpoint: process.env.E2E_WEBKIT_WS, exposeNetwork: "<loopback>" }` when `E2E_WEBKIT_WS` is set |
| `tooling/run-e2e-tests.bat` | header comment (BR1-10); step 3 installs only `chromium` natively unless `E2E_WEBKIT=native` (WebKit is in the image) |
| `tooling/tests/test_run_lanes.py` | the pure parts: when a container is needed (args → yes/no), the version read, the `docker run` argument list |
| `.claude/CLAUDE.md` | § Browser tests (S024): WebKit runs in Docker, the port 3999, `E2E_WEBKIT=native`, the first run pulls the image (about 2.5 GB); § SMTW-Review's *Browser tests* point the same (BR1-10) |
| `docs/steps/README.md` | the index row (by the orchestrator) |

### Docs (housekeeping, by the coder)

`.claude/CLAUDE.md` § Browser tests and § SMTW-Review's *Browser tests* point (from § Docs to
keep current: a dev command changes); the `run_lanes.py` docstring and the `.bat` header
(BR1-10). No schema, Plan.MD or domain doc is due.

## 4. Design decisions

1. **Only the browser in Docker, through `run-server` and `exposeNetwork`.** The lanes'
   `webServer` (backend, Vite) is started by the Playwright runner itself
   (`playwright.config.js` `webServer`), so moving the runner would move the whole stack into
   Linux (a second `node_modules` for esbuild's native binary, a Linux `uv` environment, the DB
   at `host.docker.internal`). The remote browser needs none of it. Rejected: the runner in the
   container (several times the change, two dependency trees); a Windows DPI override on the
   WebKit executable (to verify, breaks on each Playwright update); a VM (heavy).
2. **One container for all lanes.** `run-server` takes several clients; each lane's browser is
   its own process in it. Rejected: one container per lane (six images' memory, six ports).
3. **Bound to `127.0.0.1` only** (`-p 127.0.0.1:3999:3000`): the browser server is not open on
   the network (ISO 27001 A.8.20, network security: a service listens only where it is needed;
   BR1-11).
4. **Native WebKit kept as an opt-in** (`E2E_WEBKIT=native`), not removed: a 100 % host can
   still compare.

## 5. Tests and acceptance

**Facts checked while planning (25-10-2026):**
1. `@playwright/test` is `1.64.1` (`frontend/package.json:20`, installed the same).
2. `mcr.microsoft.com/playwright:v1.64.1-noble` exists (`docker manifest inspect`: an OCI index).
3. The lanes listen on `127.0.0.1` (`frontend/e2e/support/stack.js`: backend `5010 + n`, Vite
   `5180 + n`; Vite with `--host 127.0.0.1`) — not reachable from a container directly; hence
   `exposeNetwork`.
4. **Probe:** a `run-server` container on `127.0.0.1:3999`, a host page on `127.0.0.1:5999`,
   `webkit.connect(ws, { exposeNetwork: "<loopback>" })` with `devices["iPhone 14"]`: the page
   loaded, `innerWidth` **390**, `devicePixelRatio` **3**, an iPhone user agent. (In Git Bash the
   `docker run` needs `MSYS_NO_PATHCONV=1`; the `.bat` and Python's `subprocess` do not.)
5. Six lanes on one `run-server` under load: **to verify** in the coder's full run. The coder
   reports at gate B the WebKit run time beside the Chromium projects', and any WebKit crash
   (the container's default 64 MB `/dev/shm`), and **tunes nothing alone** (BR1-05): a change
   such as `--ipc=host` or fewer WebKit lanes is the user's call at gate B.
6. A client and the server refuse each other when their **major.minor** differ; the patch is
   ignored (BR1-06, checked in `node_modules`). Reading the version from `@playwright/test`
   gives the same major.minor by construction.

**Automated:**
- `tooling/tests/test_run_lanes.py`: the container decision per args and `E2E_WEBKIT`; the
  version read; the `docker run` arguments (port bound to 127.0.0.1, `--rm`, `--init`, the image
  tag from the version).
- **Important:** the full e2e suite (`tooling/run-e2e-tests.bat`, no arguments) on this PC at
  125 %: `phone-webkit` passes in the container (the S045 guard does not fire: the window is 390
  px), with the counts of all three projects; the container is gone after the run (`docker ps`).
- The same with `--project=desktop-chromium`: no container started.
- The § 1.4 cases (BR1-04), each stopping before any lane with its message: the image tag made
  wrong for one run (the pull fails); port 3999 taken by a dummy listener. A leftover
  `yantra-e2e-webkit` container from a killed run is removed and the run goes on (BR1-01). The
  pure parts (the message per case, the argument list) are unit tests in `test_run_lanes.py`.

**On a real device:** none.

**Acceptance:** an e2e run on this PC, at the user's 125 % scale, gives a green `phone-webkit`
without any change to the display settings.

## 6. Open questions and assumptions

1. **Default WebKit in Docker** (§ 1.2). **Proposed:** yes, every run that includes
   `phone-webkit`. Alternative: only with `E2E_WEBKIT=docker` (native stays the default; the
   scaled PC then needs the flag every time).
2. **The Chromium projects too?** **Proposed:** no: they are exact on Windows, and native is
   faster. Alternative: all three in the container (one browser source for all; more load on the
   one container).
3. **S045's guard on a native run** (for the user at gate A). **Proposed:** with Docker the
   default, the guard only fires on `E2E_WEBKIT=native`; make it **skip** with its message there,
   so a native run on a scaled PC is green for the two Chromium projects and names the skipped
   WebKit count. Alternative: keep it failing (as built in S045). The guard's file is S045's; the
   answer is applied in S045's fix round.
4. **Port 3999** (assumption): free on the dev machine; it sits outside the e2e ranges
   (5002, 5011–5030, 5177, 5181–5200) and the dev ports (3307, 5001, 5176).
5. **The image pull** (assumption): about 2.5 GB on the first run, once per Playwright version,
   as its own announced step (BR1-09). The `npx` fetch of the `playwright` package needs the
   internet once; then the `yantra-e2e-npm` volume holds it (BR1-03).

## 7. Amendments

None.

## Review log

### U1 — user answers, 25-10-2026 (before drafting)

- Keep 125 % display scaling on this PC and user.
- iPhone tests: "the docker way".

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

0 blocker, 0 major, 5 minor, 6 nits. Light track: the only round.

| Finding | Answer |
|---|---|
| BR1-01 minor — a hard-killed run leaves the container, and the name conflicts next time | Accepted: `docker rm -f` first, inside the lock (§ 1.2 step 1, § 3, § 5) |
| BR1-02 minor — `-d --rm` loses a failed start's logs | Accepted: attached, output to `scratch/e2e-lanes/webkit.log`, "Listening" read there (§ 1.2) |
| BR1-03 minor — the image has no `playwright` package, so `npx` downloads it every run | Accepted: the named npm-cache volume `yantra-e2e-npm` (§ 1.1, § 6.5) |
| BR1-04 minor — "Docker is not running" never reaches `run_lanes.py` | Accepted: § 1.4 and § 5 rewritten for the real cases (pull fails, port busy, name taken, no "Listening"), each message naming the cause and both ways out |
| BR1-05 minor — no plan for a slow or crashing remote WebKit | Accepted: the coder reports times and crashes at gate B and tunes nothing alone (§ 5, fact 5) |
| BR1-06…BR1-11 nits | Accepted. BR1-06: major.minor wording (§ 5, fact 6). BR1-07: inside `one_run_at_a_time()`, and the `lanes == 1` run gets `E2E_WEBKIT_WS`. BR1-08: `--user pwuser`. BR1-09: the pull as its own announced step. BR1-10: the docs pass also covers § SMTW-Review, the `run_lanes.py` docstring and the `.bat` header. BR1-11: ISO 27001 A.8.20 cited. |

### U2 — approval, 25-10-2026

- Approved by KLA ("S046 approved"), with the proposed defaults of § Open questions 1–5. Q3 settles S045 CR1-03: the guard skips (with its message) on a native WebKit run.
