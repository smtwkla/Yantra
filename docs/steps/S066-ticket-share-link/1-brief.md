Step: S066 — Share a ticket's link
Doc: brief
Author: orchestrator (Opus 5.5)
Date: 29-10-2026
Track: light
Baseline: 32eb122
Status: Committed 9162097 (adopted 30-10-2026); checks: 5 auto; important check pending: row 47 of device-checks.md (IT Admin)

## 1. What will be built, and out of scope

**Why.** KLA wanted to send closed ticket TK-2026-10-002 (an NC auxiliary contact that did not pass
the control supply) to the team to discuss its root cause. Today the only way to get the ticket's
link is to copy it from the browser's address bar, which the installed app (PWA) on a phone does not
show. The root-cause record itself is roadmap R04; this step only makes the link easy to send.

**What will be built.**

- The ticket page (`frontend/src/views/TicketDetailView.vue`) gets one button in its title row
  (`data-testid="ticket-title"`), after the badges: `btn btn-outline-secondary`, default size (not
  `btn-sm`: gloved thumbs; not primary: the action bar's next move stays the obvious tap). It shows
  for everyone who can open the ticket, in every state, open and closed.
- **On a phone** (the browser has `navigator.share`, and the main pointer is coarse) the button
  reads `"Share"` (icon `fa-share-nodes`). It opens the phone's share sheet (WhatsApp, Telegram,
  Copy, …) with:
  - `title`: the serial, e.g. `TK-2026-10-002`;
  - `text`: one line, `TK-2026-10-002 · SMTW.MCC2 · VBM001 — <problem>`; `<problem>` is
    `problemText(ticket)` (the symptom, else the start of the description; `ticketLabels.js:116`).
    With no problem text the line ends at the machine code, `TK-2026-10-002 · SMTW.MCC2 · VBM001`,
    as `alert_text` does (`alerts_core.py:201-203`);
  - `url`: the ticket's full link, `<origin>/tickets/<id>`.
- **Elsewhere** (a desktop, or a phone browser with no share sheet) the button reads
  `"Copy link"` (icon `fa-link`). It copies the full link to the clipboard. A short text
  `"Link copied"` shows beside the button for 3 seconds (`role="status"`). A second tap restarts
  the 3 seconds.
- **When the copy cannot run** (no clipboard API, which is the case on plain `http` other than
  `localhost`, or the browser refuses): a read-only text box holding the link shows under the button
  (on a phone it takes its own line under the badges), selected when shown, with the label
  `"Copy this link"`. No error is shown; the user copies by hand (on iOS, `select()` does not
  select; the user long-presses the box).
- **When the user closes the share sheet without sharing** (`AbortError`): nothing happens. Any
  other share failure falls back to the copy path above; on Safari that copy is refused too (the
  tap's user activation is used up), so it ends in the manual box. That is accepted.
- The button, the `"Link copied"` text and the box sit in one element with `:key="ticket.id"`, so
  they start fresh when the page moves to another ticket through *Repeat of* or *Came back as*
  (the page stays mounted, `TicketDetailView.vue:198`).
- The line is built by one pure helper, `ticketShareText(ticket)` in
  `frontend/src/utils/ticketLabels.js`, beside `problemText`. The link is
  `new URL(router.resolve({ name: "ticket-detail", params: { id } }).href, window.location.origin).href`:
  the app has no base path (`vite.config.js` sets none; `createWebHistory()`), so this is
  `<origin>/tickets/<id>`, and it stays right if a base or a query is ever added.

**Out of scope.**

- A link by serial (`/tickets/TK-2026-10-002`). The id link already works for anyone who may see the
  ticket and is what push alerts use (`alerts_core.TICKET_PATH`, `alerts_core.py:68`).
- Share or copy on the ticket list, the equipment page or anywhere else.
- Notes or discussion on a closed ticket, and the root-cause record: roadmap R04.
- Any backend change.

## 2. Standards and practice

- No maintenance standard applies to a link button. It serves the TPM habit of *focused improvement*
  (Maintenance-Philosophy § TPM pillars): a fault is discussed by the team, with the record at hand.
- The Web Share API (W3C) and the Async Clipboard API both need a secure context (HTTPS or
  `localhost`). Production is HTTPS: `https://vel-yantra.mspv.app` (`docs/Keycloak.md:22`).

## 3. Where

| File | Change |
|---|---|
| `frontend/src/utils/ticketLabels.js` | `ticketShareText(ticket)` |
| `frontend/src/composables/useShareLink.js` (new) | `useShareLink()` → `{ mode, share(payload), copied, manualUrl }` and `SHARE_COPIED_MS = 3000`: picks share or copy once (`window.matchMedia?.("(pointer: coarse)")`, guarded: jsdom has none), runs the call, handles `AbortError`, the fallback and the timer (cleared on a second tap and on `onScopeDispose`). Kept out of the view so it can be unit-tested with stubbed `navigator` |
| `frontend/src/views/TicketDetailView.vue` | the keyed element with the button, the `"Link copied"` text and the box, in the title row |
| `frontend/tests/ticketLabels.test.js` | tests of `ticketShareText` |
| `frontend/tests/shareLink.test.js` (new) | tests of `useShareLink` |
| `frontend/e2e/tickets-work.spec.js` | the browser tests below |

Docs (housekeeping, by the coder):

- `docs/Plan.MD` § 4.2 (tickets), one line: the ticket page has a Share / Copy link button (S066).
- `docs/steps/device-checks.md`: two rows, the Android check (important) and the iPhone check (§ 5).

None of the other docs of § Docs to keep current is due: no migration, secret or role.

## 4. Design decisions

1. **One button whose meaning follows the device**, not two buttons. A phone's share sheet already
   offers *Copy*, so a phone needs only Share; a desktop's share sheet (Windows) is clumsy, so a
   desktop gets Copy. Rejected: always Share where `navigator.share` exists — Chrome on Windows has
   it and would open the Windows share dialog on the office PC.
   The test for "a phone" is `navigator.share` present **and** `(pointer: coarse)`. Fact (BR1-01
   probe): Playwright's Pixel 7 matches `(pointer: coarse)`; `navigator.share` is undefined in
   Playwright's Chromium and WebKit, so a test that wants `"Share"` stubs it.
2. **In the title row**, not the action bar. The action bar holds the ticket's moves (S052); a link
   is not a move, and the title row is the same on an open and a closed ticket.
3. **A manual fallback, not an error.** On the dev server reached over the LAN by IP (plain `http`)
   the clipboard API is missing; the box lets the user still copy. Rejected: the old
   `document.execCommand("copy")` — deprecated (CLAUDE-COMMON § Deprecation).
4. **The share text names the place** (`site.unit · machine`) as the push alert's title does
   (`alerts_core.alert_text`), so a message in a WhatsApp group reads the same as an alert.
5. **The call is the first thing the tap does.** Safari allows `navigator.share` and
   `navigator.clipboard.writeText` only inside the tap's user activation; an `await` before the call
   (a `nextTick`, a load) makes it reject with `NotAllowedError`. So `share()` calls one of them
   synchronously in the click handler, with no `await` before it. The browser tests stub the share
   sheet and cannot catch this; the iPhone device row does.

## 5. Tests and acceptance

Unit (`tooling/run-frontend-tests.bat tests/ticketLabels.test.js tests/shareLink.test.js`):

- `ticketShareText`: symptom present; no symptom (description, cut at 80 with `…`); a ticket on a
  component (the machine code still shown); no symptom and an empty description →
  `"TK-2026-10-002 · SMTW.MCC2 · VBM001"` (no trailing dash).
- `useShareLink`: share mode calls `navigator.share` with `{title, text, url}`; `AbortError` → no
  copy, no message; another rejection → copy path; copy mode writes the URL and sets `copied` for
  `SHARE_COPIED_MS` (fake timers); a second tap restarts the timer; no `navigator.clipboard` →
  `manualUrl` set; `writeText` rejects → `manualUrl` set; no `window.matchMedia` → copy mode. Stubs
  through `vi.stubGlobal` / `Object.defineProperty`, restored after each test
  (`vi.unstubAllGlobals`), so `ticketLabels.test.js` in the same run sees none.

Browser (`frontend/e2e/tickets-work.spec.js`):

- [auto] **important** On the phone (`phone-chromium`, untagged), a closed ticket shows `"Share"`;
  tapping it calls the share sheet (stubbed by `page.addInitScript`) with the serial, the line and
  `<origin>/tickets/<id>`.
- [auto] **important** On the desktop (`@device`; first line
  `test.skip(testInfo.project.name !== "desktop-chromium", "the copy path with a readable clipboard: desktop Chromium only")`,
  the pattern of `notifications.spec.js:113`; WebKit refuses `grantPermissions(["clipboard-write"])`):
  `"Copy link"` copies `<origin>/tickets/<id>` (`grantPermissions(["clipboard-read",
  "clipboard-write"])`, read back) and `"Link copied"` shows.
- [auto] On `phone-chromium` with the clipboard removed
  (`Object.defineProperty(navigator, "clipboard", { value: undefined })` in `page.addInitScript`;
  `delete` does nothing, it is a prototype getter) and no share stub, the button reads
  `"Copy link"` and a tap shows the box `"Copy this link"` holding the link.
- [auto] The button shows on an open ticket too (any existing open-ticket test, one assertion).
- The title row still has no sideways scroll on a phone: the existing `expectNoSidewaysScroll`
  test (`tickets-work.spec.js:709`) covers it.

Targeted run: `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/screens.spec.js`.

On a real device (rows in `docs/steps/device-checks.md`):

- [ ] **important** On an Android phone with the installed app, on production: *Share* opens the
  share sheet; send to WhatsApp; the message holds the line and the link; the link opens the ticket
  after login. Account: any maintenance user; network: mobile data or plant Wi-Fi; where:
  production (TEST machine's ticket).
- On an iPhone in Safari, on production: the same; note what reaches WhatsApp (iOS may pass only
  the link to some apps). Account: any maintenance user; network: mobile data; where: production
  (TEST machine's ticket).

## 6. Open questions and assumptions

- Assumption: the label `"Share"` on a phone is plain enough for floor users; WhatsApp's own
  sheet then does the rest.
- Assumption: no permission check is needed beyond what opens the ticket page; the link gives
  nothing to someone who may not see the ticket (the API's 403 / 404 stays the gate, router note
  `router/index.js` at the tickets routes).

## 7. Amendments

None.

## Review log

| Finding | Answer |
|---|---|
| BR1-01 | Accepted: § 5 desktop test skips every project but `desktop-chromium`; the clipboard-removed test needs no share stub and uses `Object.defineProperty`; § 4.1 states the probe facts. |
| BR1-02 | Accepted: with no problem text the line ends at the machine code; expected string in § 5. |
| BR1-03 | Accepted: `docs/steps/device-checks.md` added to the Docs list (two rows). |
| BR1-04 | Accepted: § 4.5 (the call is synchronous in the tap); § 1 states the Safari fallback ends in the manual box; the iPhone row is a full device row. |
| BR1-05 | Accepted: one element keyed by `ticket.id` (§ 1). |
| BR1-06…BR1-12 | Accepted: HTTPS cited from `docs/Keycloak.md:22`; `SHARE_COPIED_MS` moved to the composable; button style named; the box under the button; `matchMedia?.` guard, timer reset and dispose; `router.resolve` kept (works with any base); stubs restored per test. |
