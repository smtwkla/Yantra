Step: S066 — Share a ticket's link
Doc: brief-review r1
Author: brief reviewer (Fable)
Date: 29-10-2026

Reviewed against: 32eb122

**Verdict: no blocker or major finding is open.** Five `minor` findings and a list of nits. The
light track holds (no migration, no auth or security code, no locking, no new dependency, no
endpoint, 7 files); this is the only round. Facts file read: `scratch/brief-facts-S066.md`.

I ran one read-only probe (`scratch/s066-share-check.mjs`, Playwright from `frontend/`, a page
on `http://127.0.0.1:5177` fulfilled by `page.route`, no server). Its facts, which the brief's
"to verify" points and the tests depend on:

| Project | `(pointer: coarse)` | `navigator.share` | `navigator.clipboard` | `isSecureContext` |
|---|---|---|---|---|
| `phone-chromium` (Pixel 7) | **matches** | undefined | present | true |
| `desktop-chromium` | does not match | undefined | present; `grantPermissions(["clipboard-read","clipboard-write"])` and a write / read-back work | true |
| `phone-webkit` (native WebKit on Windows; the Linux container is assumed the same) | matches | undefined | present; **`grantPermissions(["clipboard-write"])` is refused: "Unknown permission: clipboard-write"** | true |

So: the `matchMedia` stub of § 4.1 is not needed; every project needs the `navigator.share` stub to
show `"Share"`; and the loopback e2e origin is a secure context, so the clipboard is there.

## Findings

### BR1-01 — minor — § 5: the desktop copy test must skip the other projects

**Problem.** The brief says the `"Copy link"` test is `@device` "because it runs only there", but
names no skip. A `@device` test runs on `phone-chromium` at every level and on `phone-webkit` at
Full. On WebKit `grantPermissions(["clipboard-read", "clipboard-write"])` throws (probe above), so
the release's Full run would go red on that test.

**Why it matters.** The release tests run at Full on the iPhone project; one thrown
`grantPermissions` fails the lane.

**Options.**
1. *(recommended)* First line of the test:
   `test.skip(testInfo.project.name !== "desktop-chromium", "the copy path with a readable clipboard: desktop Chromium only")`,
   the pattern of `notifications.spec.js:113` and `changelog.spec.js:15`. Say so in § 5.
2. Drop the `@device` tag and let it run on `phone-chromium` only, without the clipboard read-back
   (assert `"Link copied"` only). Weaker: the copied text is then never checked.

Two notes for the same section, from the probe (fact):
- Chromium has no `navigator.share` in either project, so the "clipboard removed" test on
  `phone-chromium` needs no share stub: the button already reads `"Copy link"` there. Removing the
  clipboard in `page.addInitScript` needs
  `Object.defineProperty(navigator, "clipboard", { value: undefined })`; `delete navigator.clipboard`
  does nothing (it is a prototype getter).
- § 4.1's "if it does not, the browser test stubs `matchMedia`" can be closed: Pixel 7 matches
  `(pointer: coarse)`.

### BR1-02 — minor — § 1 / § 5: `ticketShareText` with no problem text is undefined

**Problem.** The line is `TK-… · SMTW.MCC2 · VBM001 — <problem>`. `problemText` returns `""` for a
ticket with no symptom and no description (`ticketLabels.js:116-120`). § 5 lists "an empty
description" as a test case but not what it should give; the coder would decide alone whether the
line ends in ` — `.

**Why it matters.** A trailing dash in a WhatsApp message looks like a cut-off text.

**Options.**
1. *(recommended)* No problem text: the line ends at the machine code, as `alert_text` does
   (`alerts_core.py:201-203`: `lead = serial · what if what else serial`). Write the expected
   string into § 5.
2. Show `—` with nothing after it. Rejected: looks broken.

### BR1-03 — minor — § 3 Docs: `docs/steps/device-checks.md` is due

**Problem.** § 3 says no doc beyond `Plan.MD` is due, "no … real-device-only check". § 5 then
lists an **important** real-device check (Android, production). README § Manual checks: the coder
appends real-device checks as rows to the device-check list; CLAUDE.md § Docs to keep current
lists it as due when the step "has a real-device check".

**Why it matters.** The coder follows the Docs line and leaves the row out; gate B then has no row
for IT Admin.

**Options.**
1. *(recommended)* Add `docs/steps/device-checks.md` to the Docs line: one row for the Android
   check (and one for the iPhone, BR1-04), where: Production, TEST machine's ticket.
2. Make the Android check a plain note and drop the row. Rejected: the share sheet is the point of
   the step and a browser cannot show it.

### BR1-04 — minor — § 1 / § 4 / § 5: Safari's user-gesture rule, and the iPhone row

**Problem.** Safari (the owner's iPhone, Plant-Facts.md:157) allows `navigator.share` and
`navigator.clipboard.writeText` only inside the tap's user activation; an `await` before the call
loses it and the call rejects with `NotAllowedError` (fact, WebKit; Chromium is more lenient). The
brief's composable "picks share or copy once, runs the call", which fits, but nothing says the
call must be the first thing in the click handler. The brief's fallback "another share failure →
copy path" runs after an `await`, so on Safari it lands in the manual box, not in a copy; that is
acceptable but should be stated. The iPhone device row ("the same, if one is at hand") has no
account, network or where, and the owner has an iPhone.

**Why it matters.** A coder who adds an `await` (a `nextTick`, a load) before the share breaks the
iPhone silently; the browser tests stub `navigator.share` and cannot show it.

**Options.**
1. *(recommended)* Add a rule to § 4: `share()` calls `navigator.share` / `writeText`
   synchronously in the click handler, no `await` before it; the share → copy fallback may end in
   the manual box on Safari. Make the iPhone row a full device row (plain, not important): account
   any maintenance user, network mobile data, where production (TEST machine's ticket); what to
   see: WhatsApp receives the text line and the link (assumption: iOS passes `url` to every
   target and `text` to most; the row shows what arrives).
2. Leave it to the coder. Rejected: the e2e stub hides the fault.

### BR1-05 — minor — § 1: the copy state must reset when the page moves to another ticket

**Problem.** The ticket page stays mounted when the route's id changes (`watch(() => route.params.id,
load)`, `TicketDetailView.vue:198`), and it links to other tickets on the same page: *Repeat of*
(line 289) and *Came back as* (line 294). With the manual box or `"Link copied"` open, a tap on
such a link shows the next ticket with the old ticket's link in the box.

**Why it matters.** The user copies the wrong ticket's link.

**Options.**
1. *(recommended)* Put the button, the status text and the box in one element with
   `:key="ticket.id"`, so Vue remounts them with a fresh composable per ticket. One line, no
   composable API for a reset.
2. `useShareLink()` returns `reset()`, called from `load()`. More surface for the same effect.

## Nits

- **BR1-06** (nit) § 2: "To verify: the production address is HTTPS (`DEPLOY_HEALTH_URL`)" — the
  value is a run-config variable, not in the repo. The repo settles it: `docs/Keycloak.md:22` root URL
  `https://vel-yantra.mspv.app`, and Plan § 4.1 (label address). Cite that and drop "to verify".
- **BR1-07** (nit) § 3: `SHARE_COPIED_MS` belongs in `useShareLink.js`, whose rule it is, not in
  `ticketLabels.js` (texts); `shareLink.test.js` imports it from there.
- **BR1-08** (nit) § 1: the button's look is unspecified. Say `btn btn-outline-secondary`, default
  size (not `btn-sm`: gloved thumbs; not primary: the action bar's next move stays the obvious tap),
  and the fit test `expectNoSidewaysScroll` of `tickets-work.spec.js:709` still covers the row.
- **BR1-09** (nit) § 1: "a read-only text box beside it" — in the title row's `d-flex flex-wrap` a
  `form-control` is 100 % wide, so on a phone the box takes its own line under the badges. Write
  "below the button on a phone"; keep it `readonly`, selected on show; `select()` does not select
  on iOS, where the user long-presses the box (fine, no change).
- **BR1-10** (nit) § 3 composable: guard `window.matchMedia?.(…)` (jsdom in vitest has none;
  pattern `push.js:46`); a second tap clears the running timer; clear it on `onScopeDispose`.
- **BR1-11** (nit) § 1: `router.resolve({ name: "ticket-detail", params: { id } }).href` + origin
  is right for the app's base (`createWebHistory()` with no base reads `<base href>` or `/`;
  `vite.config.js` sets no `base`, so `.href` is `/tickets/<id>`). `window.location.href` gives
  the same on this page with no router import; say which one the coder uses.
- **BR1-12** (nit) § 5 unit tests of `useShareLink`: stub `navigator.share` and `matchMedia` with
  `vi.stubGlobal` / `Object.defineProperty`, and restore after each test (`vi.unstubAllGlobals`), or
  `ticketLabels.test.js` in the same run sees the stubs.

## Checked and found consistent

- Light-track criteria: no migration, no auth / RBAC / security code, no locking, no new
  dependency, no endpoint, 7 files (6 code and test files plus `Plan.MD`). The new composable
  follows `composables/useShowMore.js`; its reason (unit tests with a stubbed `navigator`) is real.
- Design: `ticketShareText` is a pure helper beside `problemText`; the view stays presentational; no
  backend change; no new abstraction beyond the composable.
- `problemText` at `ticketLabels.js:116` cuts the description at 80 with `…`, as § 5 says.
- The ticket detail carries `unit.site_code`, `unit.code`, `machine.code` (view lines 312, 322) for
  the place text; `alert_text` builds the same `site.unit · machine` (`alerts_core.py:201`).
- `alerts_core.TICKET_PATH = "/tickets/{id}"` (line 68): the id link is the one push alerts use.
- The title row `data-testid="ticket-title"` (line 216) is shown on open and closed tickets; the
  only test that touches it checks its background colour (`tickets-work.spec.js:557-563`), which a
  button does not change; `screens.spec.js:68` asserts the serial heading only.
- `page.addInitScript` is the pattern for a stubbed browser API (`notifications.spec.js:35-58`).
- Standards: none applies; the TPM *focused improvement* pillar is cited correctly
  (Maintenance-Philosophy.md:60: chronic losses, root-cause analysis by the team).
- Secure context: `navigator.clipboard` and `navigator.share` are absent on plain `http` other than
  loopback (the LAN-by-IP dev server), so the manual box is the right third path; the e2e stack on
  `127.0.0.1` has both APIs (probe).
- Scope B: `"Share"`, `"Copy link"`, `"Link copied"`, `"Copy this link"` are short, verb-first, no
  codes; no error message is shown on the fallback, which is right.
- Permissions: nothing new; the API's 403 / 404 stays the gate (`router/index.js:42-43`).
- Manual checks: the Android share-sheet check is rightly on the device list (a browser cannot
  open a share sheet) and carries account, network and where; the four `[auto]` checks are ones a
  browser can judge.

## Feedback

- waste: the first probe ran on `about:blank` (`page.setContent`), where no context is secure, and
  reported the clipboard absent; a second run on a `page.route`-fulfilled loopback origin was needed
  (2 runs, ~3 min). An advice note for "probe a browser API under a Playwright project" could say:
  use a loopback origin.
- idea: `brief_facts.py` lists `"Share"` as found in 3 backend test lines (`conftest.py:214`, two
  helpers), which are SQL or comment words, not screen text; a filter to frontend test files for
  the *Screen text* section would save the reader a check.
