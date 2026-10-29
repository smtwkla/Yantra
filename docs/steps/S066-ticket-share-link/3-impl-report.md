Step: S066 — Share a ticket's link
Doc: impl report
Author: coder (Sonnet 5.5)
Date: 29-10-2026

**State: code, unit tests and browser tests done and green (run 30-10-2026, Docker up).**

## 1. What was built

One button in the ticket page's title row, after the badges, for everyone who can open the ticket, open or closed:

- On a phone (browser has `navigator.share` and a coarse main pointer): **Share** (`fa-share-nodes`). It opens the share sheet with `title` = serial, `text` = `TK-2026-10-002 · SMTW.MCC2 · VBM001 — <problem>` (no trailing dash with no problem text), `url` = `<origin>/tickets/<id>`.
- Elsewhere: **Copy link** (`fa-link`). It copies the link; **Link copied** (`role="status"`) shows for 3 seconds; a second tap restarts the 3 seconds.
- When the copy cannot run (no clipboard API, or `writeText` rejects): a read-only box labelled **Copy this link**, selected when shown, on its own line. No error text.
- `AbortError` from the share sheet: nothing happens. Any other share failure falls back to the copy path.

## 2. How it works

- `ticketShareText(ticket)` (pure, `ticketLabels.js`) builds the line from `problemText` (symptom, else the description cut at 80).
- `useShareLink()` picks `mode` once (`window.matchMedia?.("(pointer: coarse)")` guarded), and `share(payload)` makes its `navigator.share` or `clipboard.writeText` call before any `await` (brief § 4.5). The timer is cleared on a second tap and on scope dispose.
- `TicketShare.vue` resolves the link with `router.resolve({ name: "ticket-detail", … })` and `new URL(href, window.location.origin)`, and is placed in the title row with `:key="ticket.id"`.

## 3. Files touched (8 code and test, 3 docs, 1 report)

- `frontend/src/utils/ticketLabels.js` — `ticketShareText`.
- `frontend/src/composables/useShareLink.js` (new) — `useShareLink`, `SHARE_COPIED_MS`.
- `frontend/src/views/tickets/TicketShare.vue` (new) — the button, the status text, the box.
- `frontend/src/views/TicketDetailView.vue` — imports and places `<TicketShare :key="ticket.id" …>` in the title row.
- `frontend/tests/ticketLabels.test.js` — 4 tests of `ticketShareText`.
- `frontend/tests/shareLink.test.js` (new) — 10 tests of `useShareLink`.
- `frontend/e2e/tickets-work.spec.js` — 3 new `S066:` tests and one assertion in the technician flow test.
- `docs/Plan.MD`, `docs/steps/device-checks.md`, this report; status in the brief and `docs/steps/INDEX.md` (row set to Implementing).

## 4. Decisions taken

1. **Flag: an extra file, `TicketShare.vue`.** The brief's § 3 lists no new component. The composable holds its state (`copied`, `manualUrl`) once per call; if it were called in `TicketDetailView`, a `:key` on an element would reset only the DOM, not that state, and "Link copied" or the box would stay across *Repeat of* / *Came back as*. A small child component keyed by `ticket.id` calls the composable fresh for each ticket. The view's change is two lines.
2. `data-testid="ticket-share"` on the button and `ticket-share-link` on the box, for the browser tests.
3. The root element is `ms-auto` (button to the right of the badges) and becomes `w-100` while the box shows, so the box takes its own line.

## 5. Not done, deferred or assumed

- Nothing outstanding. The sideways-scroll check on a phone is covered by the existing `S052: … has no sideways scroll` test, which passed with the button shown.

## Tests run

- `tooling/run-frontend-tests.bat tests/ticketLabels.test.js tests/shareLink.test.js`: PASSED, 2 files, 67 tests.
- `npx vite build` in `frontend/`: built, only the existing chunk-size warning.
- `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js --project=phone-chromium -g "S066"`: 2 passed, 1 skipped (the `@device` desktop test), 14 s.
- Same with `--project=desktop-chromium`: first run 1 failed: the phone test ran on desktop, where the main pointer is not coarse, so Share is not shown. **Fix:** that test now skips on the desktop project (`test.skip(testInfo.project.name === DESKTOP, …)`, `tickets-work.spec.js`). Re-run: 2 passed, 1 skipped, 12.5 s.
- Targeted: `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/screens.spec.js` (before the skip fix; the skip changes only the desktop-project lane of an untagged test, which Normal does not run): 53 passed, 2 skipped, 88 s.
- `YANTRA_TEST_RUN=s066c1 tooling/run-tests.bat`: ALL PASSED. Backend 3323 passed (105 s), frontend 283 passed (10 s), tooling 185 passed (2 s).
- Whole-suite browser run at Normal (`tooling/run-e2e-tests.bat`), once, after the fix: 263 passed, 13 skipped, 0 failed, 184 s (3 min).
- Red-then-green: not applicable (new feature, not a fix round).

## Docs updated

- `docs/Plan.MD` § 4.2: one line, the Share / Copy link button (S066).
- `docs/steps/device-checks.md`: rows 47 (Android, important) and 48 (iPhone).
- None else due: no migration, secret or role.

## Manual checks

- *Automated:*
  - [auto] important: on the phone a closed ticket shows Share, which sends serial, line and link — `frontend/e2e/tickets-work.spec.js::S066: on a phone with a share sheet, …`
  - [auto] important: on the desktop Copy link copies the link and Link copied shows — `…::S066: on a desktop, Copy link copies …`
  - [auto] with no clipboard the box shows the link — `…::S066: with no clipboard, …`
  - [auto] the button shows on an open ticket — `…::technician: acknowledge, start, back in service; …` (one assertion)
  - [auto] no sideways scroll — existing `S052: the ticket page with the Meters card has no sideways scroll`
- On a real device (rows in `docs/steps/device-checks.md`):
  - [ ] **important** Android, installed app, production: Share opens the share sheet; send to WhatsApp; the message holds the line and the link; the link opens the ticket after login (row 47).
  - iPhone in Safari, production: the same; note what reaches WhatsApp (row 48).

## Shared docs

None (the main working folder is used, no worktree).

## Feedback

- hindrance: the browser and backend test wrappers fail at once when Docker Desktop is not running, and a coder may not start it, so the run stalls until the orchestrator answers; a pre-check in the spawn prompt ("Docker Desktop is up") would save the round trip (`tooling\dev\dev-db-up.bat` failed at the first browser run).
- waste: one `-g S066` run on desktop-chromium hit the phone-only test, because an untagged test with no project skip runs on every named project (1 run, 1.5 min).

## Fix rounds

### Round 1

- **CR1-01** (`.claude/CLAUDE.md` spec-to-step map): Not fixed here. `.claude/CLAUDE.md` is the user's to change; the orchestrator takes it to the user.
- **CR1-02** (nit): Fixed. New test `copy mode calls writeText before any await` in `frontend/tests/shareLink.test.js` (share not awaited, `writeText` already called once). Fails without the fix: with `await Promise.resolve()` put before the copy-mode call, `writeText` was called 0 times; passes with the code restored.
- **CR1-03** (nit): Fixed. New test `closing the scope clears the Link copied timer` (an `effectScope` runs the composable, one timer after a copy, 0 after `scope.stop()`). Fails without the fix: with the `onScopeDispose(stopTimer)` line removed, `expected 1 to be +0` (timer count); passes with it restored.
- **CR1-04** (nit): Fixed. `TicketShare.vue` now has two roots: the button group always keeps `ms-auto` in the page's title row, and the "Copy this link" box is a `w-100` sibling that wraps to its own line. The `ms-auto` / `w-100` class switch is gone. Test ids unchanged.

Runs:
- `tooling/run-frontend-tests.bat tests/shareLink.test.js`: PASSED, 12 tests (red run above: 3 failed, 9 passed with both mutations in).
- `npx vite build` in `frontend/`: built, only the existing chunk-size warning.
- `tooling/run-e2e-tests.bat e2e/tickets-work.spec.js e2e/screens.spec.js`: 53 passed, 2 skipped, 94 s.
- `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js --project=desktop-chromium -g "S066"`: 2 passed, 1 skipped (the phone test), 14.6 s.
- No backend change, so no backend run; the whole browser suite not run (scope: one component's markup).

Docs updated: none, because the round changes markup and tests only.

### Feedback

- none
