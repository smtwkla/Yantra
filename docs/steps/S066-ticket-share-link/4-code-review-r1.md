Step: S066 — Share a ticket's link
Doc: code-review r1
Author: code reviewer (Opus 5.5)
Date: 30-10-2026

**Verdict: no `blocker` or `major` finding is open.** One `minor` (the spec-to-step map in `.claude/CLAUDE.md`) and three nits.

Reviewed: the snapshot `refs/steps/S066` (213f2ff) against 32eb122, S066 files only (the R05 roadmap files in the snapshot are not part of the step). The working tree's S066 files match the snapshot.

## Tests run

- `YANTRA_TEST_RUN=s066cr1 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 3323 passed (127 s), frontend 283 passed (8 s), tooling 185 passed (2 s).
- `npx vite build` in `frontend/`: built in 4.6 s, only the existing chunk-size warning.
- Browser tests: none re-run. No finding of mine needs a browser run. The coder's runs name the right specs: the new tests alone on `phone-chromium` and `desktop-chromium`, the targeted run `e2e/tickets-work.spec.js e2e/screens.spec.js` (53 passed, 2 skipped), and the whole suite at Normal once (263 passed, 13 skipped). No shared frontend file (`api.js`, the router, `e2e/support/`, `FormModal.vue`) changed, so no extra WebKit run is due.

## Findings

### CR1-01 (minor) `.claude/CLAUDE.md:83` — the spec-to-step map does not name S066

- **Problem.** § SMTW-Review maps each spec file to its steps: `tickets-work` S018/S052. S066 adds three `S066:` tests and one assertion to `tickets-work.spec.js`, but the map does not list S066. The impl report's `## Docs updated` says no other doc is due. § Docs to keep current makes `.claude/CLAUDE.md` due for "a point for § SMTW-Review", and earlier steps (S064 in nine specs) kept this map current.
- **Failure scenario.** A later `/smtw-review` finds a red `S066:` test in `tickets-work.spec.js`. It reports the test against S018/S052 from the map, and the reader looks in the wrong step's brief.
- **Fix.** Change `tickets-work` S018/S052 to `tickets-work` S018/S052/S066 in the map, and list `.claude/CLAUDE.md` under `## Docs updated`.

## Nits

- **CR1-02** (nit) `frontend/tests/shareLink.test.js:30`: add the same "before any await" test for copy mode (`writeText` called once right after an un-awaited `share()`). Brief § 4.5 covers both calls, and today only `navigator.share` is pinned.
- **CR1-03** (nit) `frontend/tests/shareLink.test.js`: add a test that disposing the scope clears the timer (`effectScope().run(useShareLink)`, copy, `scope.stop()`, advance the timers, no error and `vi.getTimerCount()` is 0). Brief § 3 names the dispose, and no test holds it.
- **CR1-04** (nit) `frontend/src/views/tickets/TicketShare.vue:32`: the root's class switches from `ms-auto` to `w-100` when the box shows, so the button jumps from the right end of the title row to the left. Keep `ms-auto` on the button's position (for example `justify-content-end` on the full-width root), so the button stays under the thumb.

## Points the orchestrator asked about

- **The call is first in the tap (brief § 4.5).** Fact: `onTap` (`TicketShare.vue:24-26`) builds the payload synchronously (`router.resolve`, `ticketShareText`) and calls `share()` without `await`. In share mode `navigator.share(payload)` is the first expression in `share()`. In copy mode `copy()` resets the refs and reaches `navigator.clipboard.writeText(url)` before its first `await`. Correct.
- **`AbortError`.** Caught by name and returned with no copy and no message (`useShareLink.js:57`). Unit test present. `share()` cannot reject (every path catches), so `onTap` leaves no unhandled promise.
- **The timer.** `copy()` calls `stopTimer()` first, so a second tap restarts the 3 seconds (unit test present). `onScopeDispose(stopTimer)` is registered when a scope exists, which it does in the component. Correct; untested (CR1-03).
- **The fallback box.** It shows when `navigator.clipboard?.writeText` is missing or rejects, with the label "Copy this link", read-only, and selected after render (`watch(..., { flush: "post" })`). Unit tests and the browser test cover both. Device row 48 tells the iPhone user to long-press.
- **The link.** `new URL(router.resolve({ name: "ticket-detail", … }).href, window.location.origin).href`, as the brief says. The route name exists (`router/index.js:58`). The browser tests assert `<origin>/tickets/<id>`.
- **`TicketShare.vue`, the departure.** The coder is right. A `:key` on a plain element in the view would reset only the DOM: the composable's refs live in the view's setup, so "Link copied" or the box would carry over to the next ticket. A keyed child component is the smallest way to get the fresh state the brief asks for. It is reported in "Decisions taken" (1), it fits the existing `views/tickets/` folder, and the step stays inside the light track (frontend only, about 8 code and test files).
- **The phone test's skip on `desktop-chromium`.** A skip is right, and keying it to the project name is the repo's pattern (`notifications.spec.js:88,113`, `changelog.spec.js:15`). The test is untagged, so Normal and Full run it only on `phone-chromium`; the skip matters only when someone names `--project=desktop-chromium`. Keying it to the pointer (`testInfo.project.use.hasTouch`) would give the same result today, because `desktop-chromium` is the only project without touch, so it is not a finding.
- **The `@device` tag.** The desktop copy test is tagged and runs only on `desktop-chromium`: the rule's "runs only on a project other than `phone-chromium`" applies. The share test and the no-clipboard test run on `phone-chromium` and stay untagged. Both correct.
- **Wording (scope B).** "Share" and "Copy link" start with a verb. "Link copied" is a short status line. "Copy this link" says what to do. No error text is shown, as the brief asks. All plain enough for the floor.

## Manual browser checks still open

- Row 47 (**important**): Android phone, installed app, production: Share opens the share sheet, WhatsApp gets the line and the link, and the link opens the ticket after login.
- Row 48: iPhone in Safari, production: the same, and note what reaches WhatsApp.

The impl report's `## Manual checks` carries both, and every important automated check as `[auto]` with its test.

## Checked and found consistent

- `ticketShareText`: the place reads `serial · site.unit · machine` as `alerts_core.alert_text` names the place; no trailing dash with no problem text; `null` description handled by `problemText` (`?? ""`); the component's code is not used (the four unit tests match brief § 5).
- The ticket API returns `unit.site_code` and `unit.code` (`backend/tickets.py:216`) and `machine.code`.
- `useShareLink`: the mode is picked once with the guarded `window.matchMedia?.(…)?.matches`; `navigator.share` is checked with `typeof`; the unit stubs are removed after each test (`vi.unstubAllGlobals`).
- Browser tests assert what the user sees: the share stub receives the exact title, line and link; the desktop test reads the clipboard back and finds the `role="status"` line; the no-clipboard test reads the box's value; the open-ticket assertion is in the technician flow test. No new dialog, so no `expectDialogFits` is due.
- Layout: default-size button (no `btn-sm`), `btn-outline-secondary`, in the `flex-wrap` title row; the existing S052 no-sideways-scroll test passed with the button shown.
- Scope: everything in brief § 1 and § 3 is built; nothing else; no backend change. The light track holds: no migration, no RBAC, no backend.
- Docs: `docs/Plan.MD` § 4.2 has the S066 line; `docs/steps/device-checks.md` rows 47 and 48 are full rows (what to do, account, network, where). No migration, secret or role, so no other doc is due apart from CR1-01.
- No deprecated API: no `document.execCommand("copy")`. Comments say why (Safari's user activation, the router base path).

## Feedback

- waste: the orchestrator's prompt restated the step's file list and the coder's run counts, which the impl report already holds; I read both (about 2 min).
- idea: `step_snapshot.py diff S066` could take a path filter by default for the snapshot's unrelated untracked files (here 18 R05 roadmap files), or the snapshot could leave out files outside the step's own change; I read the `--stat` and then a plain `git diff` with paths instead (1 extra command).
