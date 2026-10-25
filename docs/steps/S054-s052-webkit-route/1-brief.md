```
Step: S054 — S052's Meters-card failure test fails on the iPhone
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: fix
Status: Done (committed b11db2e, 25-10-2026; released in v0.1.9; no device checks)
Baseline: e08f5bb
```

# S054 — S052's Meters-card failure test fails on the iPhone

**The bug.** The release of 25-10-2026, 17:26, stopped on one browser test (`scratch/release-tests/`):
`frontend/e2e/tickets-work.spec.js:648`, "S052: when the Meters card cannot load it says so; Try again
keeps the card in place until the answer arrives". It fails on `phone-webkit` only; it passes on
`phone-chromium` and `desktop-chromium`. Every unit suite was green (backend 3075, frontend 179, deps
42, tooling 172); the browser run had 1 failed and 559 passed.

**How to see it.** `scratch/s052-rerun.cmd`: `E2E_LANES=1`, `tooling/run-e2e-tests.bat
e2e/tickets-work.spec.js --project=phone-webkit --repeat-each=3 -g "Meters card cannot load"` →
3 of 3 failed (25-10-2026, 17:45; `scratch/s052-webkit-rerun.log`). A steady failure, not a flake.

**What fails.** The test fakes the card's first request with `page.route('**/api/tickets/<id>/meters')`
(a 503, then holds the retry), registered before `asPerson` navigates. On WebKit the fake never takes
effect: the card shows the real readings ("Run hours 100.0 h …") instead of "Meter readings could not
be loaded. Try again in a minute." (`tickets-work.spec.js:664`, the 10 s `toContainText` timeout).

**Why the release, not S052's coder, found it.** The test is a logic test (no `@device` tag), so at the
Normal level it runs on `phone-chromium` only (S047); the release's Full level was its first run on
WebKit.

**The cause** (`0-advice-webkit-route.md`, verified by trace and a probe on all three projects). The
app registers its service worker at start-up (`frontend/src/main.js:21`, `frontend/public/sw.js`). On
WebKit, Playwright's `page.route` does not see requests made by a page that a service worker controls;
Chromium routes them (Playwright 1.24+). So on `phone-webkit` the card's GET went to the network
(200) and the fake never ran. `readings.spec.js:19-21` already sets `test.use({ serviceWorkers:
"block" })` for this reason (S040); `tickets-work.spec.js` does not.

**The fix.** `test.use({ serviceWorkers: "block" })` at the top of `frontend/e2e/tickets-work.spec.js`,
with a comment naming the reason and pointing at `readings.spec.js:19-21` (file level, as the readings
spec; the advisor verified a copy of the test under it on all three projects). The app is not at
fault. Docs pass: one rule in `.claude/CLAUDE.md` § Browser tests: "A spec that fakes requests with
`page.route` / `context.route` sets `test.use({ serviceWorkers: "block" })` at file level: on WebKit a
service-worker-controlled page's requests bypass the route." Rejected: a config-level block with
`notifications.spec.js` opting back in (`notifications.spec.js:251` needs the service worker) — a wider
change than a fix-lane step.

**The failing test** is the test itself (red today on WebKit); the fix is green on all three projects.

**Files.** `frontend/e2e/tickets-work.spec.js`; `.claude/CLAUDE.md` (the rule).

## Review log

### U1 — 25-10-2026

KLA chose "B: find the cause first" (the advisor, then the coder) over skipping the test on the iPhone.
