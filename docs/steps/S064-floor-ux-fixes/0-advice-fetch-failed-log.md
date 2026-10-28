Step: S064 — Floor UX fixes
Doc: advice fetch-failed-log
Author: Advisor (Fable)
Date: 28-10-2026

## The answer

Log a `TypeError` from `fetch` with `console.error` only when its message is not a browser's
network-failure text; log nothing for "Failed to fetch" (Chromium), "Load failed" (WebKit) and
"NetworkError when attempting to fetch resource." (Firefox). That is candidate (b). It makes all
5 red tests pass, keeps CR1-04's point (a bad header value or a bad URL still shows as a
`console.error` and fails a browser test), and touches 2 files (3 with a tidy-up). It fits the fix lane.

The WebKit hypothesis is confirmed on this machine: when the page is left with a request in flight,
WebKit rejects the fetch with `TypeError: Load failed` and runs the catch handler; Chromium never
runs the handler. At that moment `pagehide` has not fired and `document.visibilityState` is still
`visible`, so candidate (c) cannot tell the two apart.

## Summary table

| Option | 5 tests pass? | What it hides | Fits the guard's purpose (S024 § 5.3) | Files | Cost / status |
|---|---|---|---|---|---|
| (a) `console.warn` in `send()` | Yes (the guard fails only `[Vue warn]` warnings) | A coding error no longer fails a browser test by itself; the screen assertion usually still catches it | Partly | 1 (+1 tidy-up) | 1 line; every screen leave on an iPhone writes a warning in devtools |
| (b) log only a non-network `TypeError` | Yes | Nothing: a network failure is on the screen as "No connection…", and the browser's own line is still caught in Chromium | Yes | 2 (+1 tidy-up) | A list of three browser texts, not a standard; a new text fails loud, not silent |
| (c) skip the log on `pagehide` / `visibilitychange` | No: the two Chromium tests stay red; and the WebKit catch runs before `pagehide` | — | — | 1 | Does not work (run A below) |
| (d) allow "fetch failed" in `console.js` ALLOWED | Yes | A coding error in every test: the opposite of CR1-04; breaks BR1-10's "exactly two sources" | No | 1 | 1 line |
| (e) `allowBrowserError("fetch failed")` in the 3 specs | Yes | A coding error in the one test meant to catch it (every screen, every role); every future WebKit test that navigates needs the line | No | 3 | Grows with each test |
| (f) mark the 5 tests as known faults | Yes (strict marks) | The three tests' real checks until the mark comes off | No | 3 | The fault is one line in `api.js`; a mark is the wrong tool |

## Option (b): tell a network failure from a coding error by the message

**Evidence, run on this machine** (`node scratch/fetch-on-leave.cjs` from the repo root, 28-10-2026;
Playwright 1.64.1's own Chromium 156.0.8078.4 and WebKit 27.2 from
`%LOCALAPPDATA%\ms-playwright`, revision 2370 = `frontend/node_modules/playwright-core/browsers.json`;
nothing installed). A local page calls `fetch` and reports the rejection in its `catch`:

| Case | Chromium | WebKit |
|---|---|---|
| A. `page.goto` to another page while the request is in flight | no console line at all: the catch never runs | `fetch failed TypeError: Load failed`; at that moment `pagehide=false`, `visibilityState=visible` |
| B. the test aborts the request (`route.abort("failed")`) | browser line `Failed to load resource: net::ERR_FAILED`, then `TypeError: Failed to fetch` | `console.info: Web Inspector blocked … from loading` (not an error), then `TypeError: Load failed` |
| C. no server on the port | `Failed to load resource: net::ERR_CONNECTION_REFUSED`, then `TypeError: Failed to fetch` | `Failed to load resource: Could not connect to server`, then `TypeError: Load failed` |
| D. a bad header value (`"a\nb"`) | `TypeError: Failed to execute 'fetch' on 'Window': Invalid value` | `TypeError: Header 'X-Bad' has invalid value: 'a\nb'` |
| E. a bad URL (`http://[bad`) | `TypeError: Failed to execute 'fetch' on 'Window': Failed to parse URL from http://[bad` | `TypeError: URL is not valid or contains user credentials.` |

- *Fact:* a network failure has exactly one message per engine: "Failed to fetch" in Chromium,
  "Load failed" in WebKit (cases A, B, C). A coding error has another message (cases D, E). Every
  rejection is a `TypeError`, never a `DOMException`; an `AbortError` is a `DOMException` and
  `send()` already passes it on (`api.test.js` "an abort goes on as it is").
- *Fact:* Firefox's text is "NetworkError when attempting to fetch resource." (MDN's `fetch()`
  page names it as Firefox's; <https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch>). Not
  run here: no Firefox project in `playwright.config.js` and no Firefox installed.
- *Fact:* the texts are not standard. The Fetch standard says only "reject with a TypeError"; MDN:
  "Message wording is also browser-specific and not standardized." WebKit's fallback text lives in
  `Source/WebCore/Modules/fetch/FetchResponse.cpp` (`"Load failed"_s` in
  `FetchResponse::consumeBodyReceivedByChunk`, main branch, read 28-10-2026).
- *Fact:* the proposed rule sorts all six observed messages right and passes an `AbortError` through
  (`node scratch/send-network-messages.cjs`: the three network texts log nothing, the three coding
  errors log `fetch failed TypeError: …`, all throw status 0).
- *Assumption:* when a browser changes its text, a network failure starts to log `console.error`,
  and the offline tests go red with the new text in the message. That is the loud side: nothing is
  hidden, and the fix is one string in the list.
- *Recommendation:* (b). It is the only option that keeps CR1-04 (the reason the line exists) and
  removes the noise on both engines. Fix lane: yes (2–3 files, no interface change).

Why the other candidates lose: (a) is one line but gives up CR1-04 in the browser tests and writes
a warning on every iPhone screen leave; (d) and (e) hide the one case the line is for; (f) marks a
one-line fault as known across three specs.

## Option (c): `pagehide` / `visibilitychange`

- *Fact:* in run A (WebKit) the catch runs with `pagehide=false` and `visibilityState=visible`. The
  rejection comes first, the unload events later (or never, for a headless page close). A flag set
  in `pagehide` is still false when `send()` decides.
- *Fact:* the two Chromium tests fail on `route.abort`, not on a page leave. (c) does not touch them.
- *Recommendation:* drop (c).

## Options (d), (e), (f): the tests

- *Fact:* `console.js`'s header and S024 BR1-10 fix the allow-list at "exactly two sources, so any new
  warning still fails". (d) adds a third source for every test.
- *Fact:* `masters.spec.js:647` already does (e) for the CR1-01 test (`allowBrowserError("fetch failed")`).
  With (b) that line matches nothing and should go; its `net::ERR_FAILED` line stays.
- *Fact:* `screens.spec.js:85` is the test "that would have caught S017's blank raise screen"; (e)
  there would allow a coding error on every screen for every role.
- *Recommendation:* no change to `console.js`; remove the dead line in `masters.spec.js`.

## Is WebKit's "Load failed" on page leave what a real iPhone does?

- *Fact:* Playwright's WebKit does it (run A). The engine is WebCore, the same core as Safari's;
  the Windows build differs in the network layer (curl), not in the Fetch module or the frame loader
  that stops loads on navigation.
- *Fact:* Safari on iOS 18 reports a failed fetch with the same text, `TypeError: Load failed`
  (Apple Developer Forums thread 771127, a different trigger: a fetch right after the document
  becomes visible).
- *Assumption:* a real iPhone rejects an in-flight fetch with "Load failed" when the user leaves the
  page, as the Windows build does. Not verified here: it needs Safari Web Inspector on a Mac.
- It does not matter for the fix: on a real phone the line goes to a console nobody opens, and the
  user sees nothing (the view is gone). The fix is for the guard and for a clean devtools console.

## Why the fault reached the pre-flight

- *Fact:* the line came in fix round 1 for CR1-04 (`3-impl-report.md:418`); the coder's targeted run
  was `masters`, `equipment`, `screens` at Normal (`phone-chromium` and `desktop-chromium`), so no
  WebKit run and no offline test outside `masters` (which allowed the line). The verify review
  (`4-code-review-r2.md:19`) read `api.js` as shared but judged "only a failed fetch reaches that
  line", which is true, and missed that two other specs make a fetch fail on purpose and that WebKit
  fails fetches on every `page.goto`.
- *Recommendation:* a change to `api.js` (a shared file by `.claude/CLAUDE.md` § Step workflow,
  *Shared code*) runs the whole browser suite again, as that entry already says; the orchestrator may
  add "including `--level=full` when the change can log or throw", since only the iPhone project
  shows this kind of fault.

## What the step should change

1. `frontend/src/api.js` `send()`: the snippet below. Keep the throw as it is (status 0,
   `NO_CONNECTION_TEXT`, `cause` attached). Update the comment above `send()`.
2. `frontend/tests/api.test.js`: two cases with `vi.spyOn(console, "error")`: each of the three
   network texts logs nothing; a non-network `TypeError` (e.g. "Failed to execute 'fetch' on
   'Window': Invalid value") logs once and still throws status 0 with `NO_CONNECTION_TEXT`.
3. `frontend/e2e/masters.spec.js:647`: remove `consoleWatch.allowBrowserError("fetch failed");`
   (dead with (b)). Keep line 648.
4. No change to `frontend/e2e/support/console.js`, `floor.spec.js`, `readings.spec.js`,
   `screens.spec.js`.
5. `3-impl-report.md` § Fix rounds: a round 3 with the runs below; the `## Feedback` idea of round 1
   (a global allow for "fetch failed") is answered by this file.
6. Runs for the coder: `tooling/run-frontend-tests.bat tests/api.test.js`; then
   `tooling/run-e2e-tests.bat --level=full e2e/floor.spec.js:60 e2e/readings.spec.js:494 --project=phone-chromium`
   and `tooling/run-e2e-tests.bat --level=full e2e/screens.spec.js:85 --project=phone-webkit`
   (Docker Desktop up); then, because `api.js` is shared, the whole suite at Normal and a new
   `/pre-flight`.

## What the user should check

1. Optional, needs a Mac with Safari and the iPhone cabled: open Yantra on the iPhone, Safari ›
   Develop › the iPhone › the page; tap a bottom-nav item while a list still loads. A console line
   `TypeError: Load failed` before the fix, none after it, confirms the assumption above. Nothing in the
   fix depends on it.
2. Nothing else: the runs in point 6 above are the coder's.

## Code to start from

Checked with `node scratch/send-network-messages.cjs` (28-10-2026, repo root) against the six
messages of the table above and an `AbortError`; not yet run inside the app.

```js
// fetch() rejects with a TypeError both for a lost connection and for a coding error (a bad header
// value, a bad URL).  The browser's text for the lost connection is not standard, but each engine
// has one (scratch/fetch-on-leave.cjs, 28-10-2026): Chromium "Failed to fetch", WebKit "Load failed"
// (also when the page is left while a request runs), Firefox "NetworkError when attempting to fetch
// resource.".  Those are the user's network and are not logged: the screen shows NO_CONNECTION_TEXT.
// Any other TypeError is a coding error and is logged (CR1-04).  An AbortError is the caller's and
// goes on as it is.
const NETWORK_FAILURE_MESSAGES = [
  "Failed to fetch",
  "Load failed",
  "NetworkError when attempting to fetch resource.",
];

async function send(url, options) {
  try {
    return await fetch(url, options);
  } catch (cause) {
    if (!(cause instanceof TypeError)) throw cause;
    if (!NETWORK_FAILURE_MESSAGES.includes(cause.message)) console.error("fetch failed", cause);
    const err = new Error(NO_CONNECTION_TEXT, { cause });
    err.status = 0;
    err.code = null;
    err.field = null;
    err.ip = null;
    throw err;
  }
}
```

Scripts (read-only, nothing installed): `scratch/fetch-on-leave.cjs` (the five cases on both
engines; about 40 s) and `scratch/send-network-messages.cjs` (the rule against the messages).

## Feedback

- waste: my first `fetch-on-leave.cjs` run returned the fetch promise from `page.evaluate`, which waited for it, so case A showed "ok 200" on both engines; one re-run after the fix (2 min).
- hindrance: WebKit's exact source line for "Load failed" on a cancelled load was not findable by web search; only the `FetchResponse.cpp` fallback string turned up (3 fetches).
- idea: the shared-code rule in CLAUDE.md § Step workflow could say that a change to `api.js` or `support/` runs the whole suite at Full once, since only `phone-webkit` shows a page-leave rejection.
