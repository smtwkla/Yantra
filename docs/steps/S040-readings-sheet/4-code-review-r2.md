```
Step: S040 — End-of-day readings sheet
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** Fix round 1 fixes CR1-01 to CR1-09 as its report says, and its tests come with a red result. This round brings one `minor` finding: the new discard question puts the destructive button first and does not use the app's existing words (CR2-01). The one red e2e test, `readings.spec.js:189` on phone-webkit, is caused by the host's display scaling. This round's code does not cause it (§ The phone-webkit failure).

Files re-read: `frontend/src/views/ReadingsView.vue` and `frontend/src/views/readings/ReadingSheetRow.vue` in full; `frontend/e2e/readings.spec.js` (header, `:189`, and every S040 test); the `IN` lists of `backend/meters.py`; the round-1 lines of `docs/Plan.MD` § 4.5; the impl report's "Fix rounds". Only these files changed after the round-1 review (file times checked). `FormModal.vue`, `ReadingFormModal.vue`, `EquipmentDetailView.vue` and `e2e/support/` did not change after my round-1 runs.

## Test results (this review, run name `s040cr2`)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | **PASSED**. Backend 2964 passed, frontend 167, deps 42, tooling 115. |
| `npx vite build` | **PASSED**, built in 4.36 s. Only the usual chunk-size warning. |
| `tooling/run-e2e-tests.bat e2e/readings.spec.js e2e/screens.spec.js` (6 lanes, 3 projects), 00:54–00:56 IST | **RED**: 97 passed, 1 failed, 1 skipped. The failure is `readings.spec.js:189` (S039 Yes / No) on phone-webkit, "Yes is off screen". All 16 S040 tests pass in all three projects. |
| `readings.spec.js:189`, phone-webkit alone (`E2E_LANES=1`) | **RED**, the same failure. |
| Probe: `:189` on phone-webkit, 3 runs with the service worker blocked, 3 runs with it allowed (a copy of the spec in the scratchpad, run with a scratch config) | **RED** in all 6 runs. |

Why these specs: the fix round changed only the *Readings* screen and its spec. It changed no shared frontend code, so the full suite is not due. `tickets-work.spec.js` is not affected by this round.

## The phone-webkit failure of `readings.spec.js:189`

**Judgement: the host causes it. This round's code does not.** Evidence:

1. **The code under test did not change.** The test opens the equipment page and S039's *Log reading* dialog. Neither file, nor `FormModal.vue` nor `e2e/support/`, changed after 23:27 on 24-10. The test passed on phone-webkit in both of my round-1 runs (23:57–00:15).
2. **`serviceWorkers: "block"` is not the cause.** The test fails the same with and without it (6 of 6 runs above).
3. **The mechanism is the window width.** My probe on phone-webkit read `devicePixelRatio` 3.75 and `innerWidth` 312. The page itself lays out 391 px wide. iPhone 14 is 3 and 390. Windows here is at 125 % (`AppliedDPI` = 120), and 3 × 1.25 = 3.75, 390 / 1.25 = 312. So the window is 79 px narrower than the page. When the dialog opens and takes the focus, WebKit scrolls the window 37 px to the right (`scrollX` 37 in the probe). The left *Yes* button then starts at a negative `x`. The screenshot shows the same: the left edge of the dialog and of the bottom nav is cut off. phone-chromium reads 412 / 412 with no scroll.
4. **A real iPhone does not do this.** There, the window is as wide as the page, so nothing can scroll sideways. The S040 sheet's own Yes / No test (the same box check) passes on phone-webkit, because nothing moves the focus there.

**Not explained:** why the same host passed the test until about 00:25. The 125 % scale is old (`e2e/support/dialogs.js` notes it since S024). My assumption: the display state changed after midnight, for example the monitors went to sleep or the session was locked. With three monitors, Playwright's WebKit then picks up a different scale.

**How the user can confirm it:**

1. Wake the monitors and unlock the session at the PC.
2. Run `tooling/run-e2e-tests.bat e2e/readings.spec.js --project=phone-webkit`. If the test passes, the display state was the cause.
3. If it still fails, set *Settings › System › Display › Scale* to 100 % on the main display. Sign out and in, so that `AppliedDPI` reads 96. Then run step 2 again. A pass confirms the host scaling.

Recommendation (outside this step, for the user): add a check to the e2e set-up that stops a phone-webkit run with a plain message when `innerWidth` differs from the project's viewport width. Then a host problem shows as one clear error, not as a layout failure in a random test.

## The three questions of this round

- **`test.use({ serviceWorkers: "block" })` for the whole file: sound.**
  - `test.use` at the top of a file applies to that file only. The S021 push tests are in `notifications.spec.js`, which waits for `navigator.serviceWorker.ready` (`:251`) and is not affected.
  - The service worker has no `fetch` handler and caches nothing (CLAUDE.md § Notifications), so blocking it changes nothing on the readings screens. `push.js:58` catches a refused registration, and the console watch stays clean.
  - The S039 tests of the file do not use push. Nothing the readings tests check depends on the worker.
- **`isToday` uses the browser's own date, not IST: a nit (CR2-03).** The API sends IST times, and `isToday` compares their date with the browser's local date. On a browser set to IST, which the plant's phones are, the result is right. Only a browser set to another time zone marks "Today" wrongly, for 5½ hours a day. "Read today" is a business rule, so CLAUDE-COMMON's IST rule applies, and the fix is one line. It is not `major`: it only changes a label and a count, and no reading is lost or wrongly saved.
- **The new screen text:**
  - "Not saved. Change Time taken, then save again." holds scope B. It says what happened and what to do, in one short line. The reason is on the *Time taken* field just above it.
  - The discard question holds scope B in its words. It is not consistent with the app's existing discard question, and its buttons are in the wrong order (CR2-01).

## Round-1 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR1-01 | blocker | **Fixed** | `lastLine` uses the screen's rule ("Today …" when the date is today in IST, else "… · DD-MM-YYYY HH:MM"). The "read today" test takes its reading `Math.min(2, minutesIntoIstDay())` minutes back. Red at 00:19 IST on the real clock, then green. Green in my run at 00:54–00:56, inside the hour the finding was about. |
| CR1-02 | minor | **Fixed** | The picker is `disabled` while saving. A site picked with unsaved readings asks first, and the picker goes back to the current site (`:key`). *Keep* keeps the values; *Discard* switches and drops them. Two tests, red in the mutation run. New wording issue: CR2-01. |
| CR1-03 | minor | **Fixed** | `nothingToShow` is true when no site is left, also after a 404. The test asserts the no-units message, no picker and the forgotten site. Red in the mutation run. |
| CR1-04 | minor | **Fixed** | A 400 on `taken_at` stops the loop, shows once on the field, and marks the refused row and the rows after it. A 409 `SAME_MINUTE` stays on its row and the loop goes on. Only the time window gives a 400 on `taken_at` (`meters_core.parse_reading_request`), so stopping the loop on it is right. Two tests, red in the mutation run. |
| CR1-05 | minor | **Fixed** | 503 and no-answer tests: both rows read "Not saved. Try again in a minute.", the values are kept, and one POST was sent. 404 tests with and without a site left. The 404-with-sites-left test passed on the old code too; the report says so and why. |
| CR1-06 | nit | **Fixed** | `meters.py:80`, `:274` use `_marks`. `masters.py` keeps its inline form, for the import direction the report gives. |
| CR1-07 | nit | **Fixed** | The header of `ReadingSheetRow.vue` says what the row writes and that only Undo is emitted. |
| CR1-08 | nit | **Fixed** | `saveAll` sets `now` first. |
| CR1-09 | nit | **Fixed** | `show-idle`: no `p-0`, `min-height: 44px`. |
| CR1-10 | nit | **Open, held for the user at gate B** | Not changed, as agreed. |

**Red, then green:** CR1-01 has its red run on the real clock. CR1-02 to CR1-05 have the mutation run. The nits need no test.

## Findings

### CR2-01 (minor) — the discard question puts *Discard* first and filled red, with words unlike the app's

- **Where:** `frontend/src/views/ReadingsView.vue:308-312`.
- **Problem:**
  - The app already has a discard question: FormModal's "Discard your changes?" (`FormModal.vue:174-176`). There, *Keep editing* comes first as the primary button, and *Discard* comes second as `btn-outline-danger`.
  - The sheet's question puts *Discard* first as a filled `btn-danger`, and *Keep* second as `btn-outline-secondary`. The destructive button is the one the eye and the thumb meet first.
  - The words differ for the same thing: *Keep* against *Keep editing*, and "You cannot get them back." against the app's "You cannot undo this." (`ReadingHistoryModal.vue:141`, and the CLAUDE-COMMON example). CLAUDE-COMMON scope B asks for the same word for the same thing in the whole app.
- **Failure scenario:** a manager types 20 readings, touches the site picker by mistake, and taps the first button of the bar on a phone. All 20 values are gone. That is the loss CR1-02 was meant to prevent.
- **Fix:** follow FormModal's bar. Put the safe button first as `btn-primary`, for example *Keep readings*, or *Keep editing* as in FormModal. Put *Discard* second as `btn-outline-danger`. End the question with "You cannot undo this." Update the two CR1-02 tests' button names if they change.

## Nits

- **CR2-02** (nit) `frontend/src/views/ReadingsView.vue:308`: if the user clears the typed rows while the question waits, it reads "Discard 0 typed readings?". Show the question only while `pending > 0`, for example `v-if="wantedSite !== null && pending > 0"`, and clear `wantedSite` when `pending` drops to 0.
- **CR2-03** (nit) `frontend/src/utils/meterLabels.js:130-134`: `isToday` compares an IST date with the browser's local date. Compare it with the IST date of `now`, for example `new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(now)`, so a browser in another time zone counts the plant's day (CLAUDE-COMMON: business logic uses IST). Remove Decision 5's note once it is done.

## Checked and found consistent

- **The save loop after the fix:**
  - `wantedSite` is cleared when a save starts. The picker is disabled while saving, so the question cannot come back during the loop.
  - *Discard* during a save cannot happen, because the question is gone by then.
  - `notSaved` switches to the time text only on a `taken_at` 400. A server failure keeps "Not saved. Try again in a minute."
  - After a time refusal, the page scrolls to the first `.invalid-feedback`, which is the *Time taken* field at the top. After any other refusal, it scrolls to the first `[role="alert"]`, as before.
- **The picker's `:key`:** re-creating the `<select>` is the simple way to show the current site again while the question waits. The CR1-02 test checks that the selected option reads SMTW. Decision 4 of the round reports it.
- **CR1-03 path:** with one site and a 404, `goneSites` empties the choices, and the no-units message shows. With sites left, the picker shows them and the warning. Both are tested.
- **Tests:** each new test makes its own machine, counts POSTs with `watchPosts`, and asserts what the user sees: the messages, the kept values and the disabled picker. It also checks the server side where it matters (one POST). `consoleWatch.allowFailedRequest` names each expected failure.
- **Security and layers:** the round adds no route, permission or SQL. The time and same-minute rules stay on the server, and the screen only reads `status` and `field`.
- **Docs pass:** the round's `## Docs updated` line matches the diff. `Plan.MD` § 4.5 names the time refusal and the discard question. No other doc in § Docs to keep current is affected. No migration.
- **Manual checks:** the round adds four `[auto]` rows, each with named tests that pass in my run on all three projects. The real-device check is still an open box that matches row 33 of `device-checks.md`.
- **Impl report writing:** scope A holds. Each answer leads with the status, then says what changed and how it was tested.
- **Track:** full. Nothing in the round changes that.

## For the user's manual browser check

- Row 33 of `docs/steps/device-checks.md`, on an Android phone and an iPhone: the decimal keypad, the keyboard not hiding a row's message or *Save readings*, and *Yes* / *No* easy to hit with a thumb.
- On a phone: type a reading, pick another site, and check that the question is easy to read and that the safe button is the easy one to hit (CR2-01).
- On this PC: confirm the phone-webkit failure of `readings.spec.js:189` as described in § The phone-webkit failure, before the release's full run.
