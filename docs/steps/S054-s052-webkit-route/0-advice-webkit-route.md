```
Step: S054 — S052's Meters-card failure test fails on the iPhone
Doc: advice webkit-route
Author: Advisor (Fable)
Date: 25-10-2026
```

# Why `page.route` misses the Meters card's GET on phone-webkit, and the fix

## The answer

The app's service worker is the cause, not the test's glob, the Docker connection, timing or a cache.
On WebKit, Playwright's `page.route` does not see a request made by a page that a service worker
controls; Yantra registers `sw.js` at start-up (`frontend/src/main.js:21`), so by the time the card
asks for `/api/tickets/<id>/meters` the page is controlled and the fake never runs. Chromium routes
such requests since Playwright 1.24 (Chromium only), which is why the two Chromium projects pass.
The fix is in the test: `test.use({ serviceWorkers: "block" })`, as `readings.spec.js:19-21` already
does for the same reason (S040 found it; `docs/steps/S040-readings-sheet/3-impl-report.md:150`).
Verified today: with the option the S052 test passes on all three projects; the app is not at fault.

## Summary table

| Option | What it gave on this machine | Cost | Status |
|---|---|---|---|
| 1. `test.use({ serviceWorkers: "block" })` at the top of `tickets-work.spec.js` (as `readings.spec.js`) | The copied S052 test passed on phone-webkit, phone-chromium and desktop-chromium (run of 17:45, 9 of 9 green) | One line and a comment; every test in the file then runs without the service worker (no test there uses push) | Documented Playwright option (`playwright-core/types/types.d.ts:11720`), not deprecated. **Recommended** |
| 2. The same option in a `test.describe` around the S052 failure test only | Same result (the probe ran the test inside a describe with the option) | Narrowest change; the next `page.route` in the file falls into the same trap | Documented |
| 3. `use: { serviceWorkers: "block" }` in `playwright.config.js`, with `test.use({ serviceWorkers: "allow" })` in `notifications.spec.js` | Not run | Every future `page.route` is safe; every other test then sees an app without its service worker, and `notifications.spec.js:251` (`navigator.serviceWorker.ready`) needs the opt-out | Documented; a design choice for the planner |
| 4. Leave the service worker on and route differently (`context.route`, unregister the worker in the test) | Not run | `context.route` has the same limit (Playwright issue #1090: service-worker routing is "Chromium-only"); unregistering is more test code for the same effect | Not recommended |
| 5. Skip the test on phone-webkit | — | Loses the check on the iPhone for no reason; the option above costs less | Not recommended (KLA chose B, the brief's U1) |

## Evidence

### The failing run (fact)

The trace of the first failure (`scratch/s052-webkit-rerun.log`, 17:39; the unzipped trace is kept in
`scratch/s054-webkit-failure-trace/`, because my probe run replaced `scratch/e2e-report/results/`):

- `test.trace` actions, in order: `Route requests` (6894 ms) → `Set extra HTTP headers` →
  `Wait for event "response"` → `Navigate` → `Expect "toContainText"` (fails after 10 s). There is no
  `Fulfill` action: the handler never ran. The route was registered before the navigation, so timing
  is not the cause.
- `6-trace.network` (the page's requests): `GET http://127.0.0.1:5177/sw.js` 200 comes before
  `GET /api/auth/me`; then `GET http://127.0.0.1:5177/api/tickets/2/meters` 200 from the network.
  The URL is the same on all three projects (`127.0.0.1:5177`, no query), so the glob matches and the
  Docker connection with `exposeNetwork` is not the cause.

### The probe (fact)

Temporary spec `frontend/e2e/zz-advice-route.spec.js` (deleted after the run; its text is in § Code
below), run by `scratch/s054-advice-route.cmd` (`E2E_LANES=1`, all three projects), log
`scratch/s054-advice-route.log`. Each probe registers a 503 fake for the card's GET, opens the
ticket, then reads `navigator.serviceWorker.controller` and counts the handler's calls:

| Project | `serviceWorkers` | Page controlled by the worker | Handler calls | Card's GET |
|---|---|---|---|---|
| phone-webkit | default (`allow`) | yes | **0** | 200, real readings shown |
| phone-webkit | `block` | no | 1 | 503, "Meter readings could not be loaded." |
| phone-chromium | default | yes | 1 | 503 |
| phone-chromium | `block` | no | 1 | 503 |
| desktop-chromium | default | yes | 1 | 503 |
| desktop-chromium | `block` | no | 1 | 503 |

The copy of the S052 test (held retry included) under `serviceWorkers: "block"` passed on all three
projects (log lines 13, 18, 23). The console watcher found no problem on the ticket page with the
worker blocked.

### The documentation (fact)

- `frontend/node_modules/playwright-core/types/types.d.ts:4443`: "`page.route()` will not intercept
  requests intercepted by Service Worker. See issue 1090. We recommend disabling Service Workers when
  using request interception by setting `serviceWorkers` to `'block'`." The same note is on
  `browserContext.route` (line 10402) and HAR replay (line 4515).
- `types.d.ts:11718`: `serviceWorkers: 'block'` — "Playwright will block all registration of
  Service Workers."
- https://playwright.dev/docs/network § "Missing Network Events and Service Workers": the same advice.
- https://github.com/microsoft/playwright/issues/1090 (closed 22-07-2022, Playwright 1.24): routing of
  requests that go through a service worker landed "on Chromium-only for now".
- The repo already knows this: `readings.spec.js:19-21` ("WebKit does not route them while the app's
  service worker (S021) controls the page") and S040's impl report line 150; S040's code review r2
  called the file-level option sound. S052's test was never run on WebKit before the release (Normal
  level runs logic tests on phone-chromium only, S047), so the trap was not seen.

### Why Chromium passes with the worker in control (assumption)

Yantra's `sw.js` has no `fetch` handler. Chromium's Playwright integration routes a controlled page's
requests since 1.24, and Chromium itself skips a worker without a `fetch` handler, so the request goes
through the page's own network path where `page.route` sits (the probe's `request.serviceWorker()` was
null on Chromium). WebKit hands a controlled page's loads to the worker's process even without a
`fetch` handler, outside the page's interception. I did not read WebKit's source for this; the
observed behaviour (table above) is what the fix relies on, not the mechanism.

### Ruled out (fact)

- The glob and the host: the request URL is identical across projects; the same glob fires on WebKit
  once the worker is blocked.
- `exposeNetwork` / the remote WebKit: the fix works over the same Docker connection.
- Timing: the route is registered before `page.goto` (trace); the probe registers it the same way.
- A GET cache: the 200 was a network response (`fromServiceWorker=false`, fresh readings of a machine
  made seconds before).
- The identity headers (`setExtraHTTPHeaders`): the request reached the backend as the technician on
  every project.

## What the step should change

1. **The fix (brief § The fix):** add `test.use({ serviceWorkers: "block" })` near the top of
   `frontend/e2e/tickets-work.spec.js`, with a two-line comment that names the reason and points at
   `readings.spec.js:19-21` — the same words, so the next reader sees one rule (recommendation:
   option 1). The S052 test's body stays as it is.
2. **A rule for future specs (brief § Files, or a line in `.claude/CLAUDE.md` § Browser tests):**
   a spec that calls `page.route` or `context.route` sets `serviceWorkers: "block"` at file level, and
   a test that needs the worker (`notifications.spec.js`) never shares a file with a `page.route`.
   This is the third time the trap matters (S040, S052, and any step that fakes a failure next); the
   planner may prefer option 3 (config-level block, `notifications.spec.js` opts back in) — a design
   choice I do not make here.
3. **The acceptance:** `scratch/s052-rerun.cmd` (3 of 3 on phone-webkit) and the test on the two
   Chromium projects; no app code changes, so no targeted screen run beyond that.
4. **Nothing in the app:** `TicketMetersCard.vue`, `api.js`, `sw.js` and `push.js` behave as designed;
   the worker caches nothing and has no `fetch` handler (CLAUDE.md § Notifications holds).

## What the user should check

Nothing before the coder starts. After the fix:

1. On this machine, with Docker Desktop running: run `scratch\s052-rerun.cmd`. Expected: `3 passed`
   on phone-webkit (today: 3 failed).
2. Optional: `tooling\run-e2e-tests.bat e2e/tickets-work.spec.js --project=phone-chromium
   --project=desktop-chromium -g "Meters card cannot load"`. Expected: 2 passed (unchanged).

## Code to start from

The one-line fix, verified today inside a `test.describe` on all three projects (option 2); at file
level it is the same call outside any describe, as `readings.spec.js:21`:

```js
// The page's own requests are faked by page.route below.  WebKit does not route them while the
// app's service worker (S021) controls the page, so none is started (readings.spec.js:19, S040).
test.use({ serviceWorkers: "block" });
```

The probe spec as it ran (deleted; recreate it as `frontend/e2e/zz-advice-route.spec.js` and run
`scratch\s054-advice-route.cmd` to repeat the measurement):

```js
import { test, expect } from "./support/test.js";
import { logByApi, meterMachine } from "./support/meters.js";
import { asPerson } from "./support/people.js";
import { card, istLocal, raiseByApi, thisMinute } from "./support/tickets.js";

async function pressTicket(testInfo, tag, at) {
  const machine = await meterMachine(testInfo, tag, {
    unit: "SMTW.MCC2", ownMeters: [["Run hours", {}], ["Oil temperature", { max_value: "60" }]],
  });
  const ticket = await raiseByApi("operator", {
    equipment_id: machine.id, intensity: "critical", description: `S054 probe: ${tag}`, occurred_at: at,
  });
  return { machine, ticket };
}

/** Fake the card's GET with a 503 and record what the browser did. */
async function probe(page, testInfo, tag) {
  const base = thisMinute();
  const { ticket } = await pressTicket(testInfo, tag, istLocal(60, base));
  await logByApi(ticket.machine, "Run hours", "100", istLocal(90, base));
  const seen = [];
  let routed = 0;
  page.on("request", (r) => { if (r.url().includes("/meters")) seen.push(`request ${r.method()} ${r.url()} sw=${r.serviceWorker() ? "yes" : "no"}`); });
  page.on("response", (r) => { if (r.url().includes("/meters")) seen.push(`response ${r.status()} ${r.url()} fromSW=${r.fromServiceWorker()}`); });
  await page.route(`**/api/tickets/${ticket.id}/meters`, (route) => {
    routed += 1;
    return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: "Database unavailable" }) });
  });
  await asPerson(page, "technician", `/tickets/${ticket.id}`);
  const meters = card(page, "Meters");
  await meters.waitFor();
  await expect(meters).toContainText(/could not be loaded|Readings up to/);
  const sw = await page.evaluate(() => ({
    supported: "serviceWorker" in navigator,
    controlled: Boolean(navigator.serviceWorker?.controller),
  }));
  const text = (await meters.innerText()).replace(/\s+/g, " ").slice(0, 70);
  const result = { project: testInfo.project.name, tag, routed, sw, seen, text };
  console.log(`S054-PROBE ${JSON.stringify(result)}`);
  return result;
}

test("S054 probe A: default serviceWorkers (allow)", async ({ page, consoleWatch }, testInfo) => {
  consoleWatch.allowFailedRequest("/meters", 503);
  await probe(page, testInfo, "s54a");
});

test.describe("with serviceWorkers block", () => {
  test.use({ serviceWorkers: "block" });

  test("S054 probe B: serviceWorkers block", async ({ page, consoleWatch }, testInfo) => {
    consoleWatch.allowFailedRequest("/meters", 503);
    const result = await probe(page, testInfo, "s54b");
    expect(result.routed).toBe(1);
    expect(result.sw.controlled).toBe(false);
  });
  // Probe C was a verbatim copy of tickets-work.spec.js:648 (S052) inside this describe; it passed.
});
```

Files left behind on purpose, all under `scratch/`: `s054-advice-route.cmd`, `s054-advice-route.log`,
`s054-webkit-failure-trace/`. The temporary spec is deleted; no other repo file was touched.
