```
Step: S040 — End-of-day readings sheet
Doc: impl-report
Author: Coder (Sonnet)
Date: 24-10-2026
```

# S040 — End-of-day readings sheet: implementation report

The *Readings* page is built as briefed: one sheet per site, grouped by unit, saved row by row through S039's routes, with the nav item, the sheet read and `reading_unit_ids` on `my-units`. There is no migration. All four suites pass and so does the full browser suite (counts in § 6). One departure from the brief: a role without `reading:log` gets 403 from the sheet, not 404 (*Decisions taken* 1). No open question.

## 1. What was built

- **The nav item and route.** *Readings* (`/readings`, icon `fa-gauge`, `reading:log`) after *Tickets*. The storekeeper and IT admin do not see it and cannot open the route.
- **The sheet read.** `GET /api/readings/sheet?site_id=`: the site's active units where the user logs, each with its machines that have meters in force (on the machine or a part), not scrapped, in code order, parts nested, each meter with `last`. A unit with no such machine is left out. 404 for an unknown, inactive or foreign site, and for a site whose units are all inactive, admin too. 400 "Pick a site" for a missing or bad `site_id`.
- **`my-units` gains `reading_unit_ids`** (null = every unit). `readingSites(allUnits, allSites, mine)` in `stores/equipment.js` builds the site picker from it.
- **The page.**
  - Site: no picker for one site; a picker for several, the last choice remembered under `yantra.readings.site_id` (read and written in `try`/`catch`); a remembered site no longer offered falls back to the first; a 404 on the sheet forgets the site and shows "This site is no longer available. Pick another site."
  - One *Time taken* for the sheet (`EventFields`, "Now" sends no `taken_at`).
  - One card per machine; its parts' meters are titled blocks inside it. Unit headings are sticky. Out-of-use machines sit behind *Show out of use (n)* at the end of each unit.
  - Each meter row: name, last reading ("12,345.6 h · 23-10-2026 18:00", or "Today 17:50 · 12,345.6 h" with a tick and a grey row when read today), and the input with its unit. An amount shows S039's help sentence. A Yes / No meter shows two toggle buttons (48 px high; a second tap clears).
  - Header: "9 of 48 read today". Save bar: "3 of 48 filled" and *Save readings*; sticky above the bottom nav on a phone, at the end of the sheet on desktop.
  - *Save readings* posts each filled row in turn. A 400 or 409 shows on its row and the loop goes on. A 502, 503, 504 or no answer stops the loop: that row and the filled rows after it read "Not saved. Try again in a minute." with their values kept. The button is disabled while a save runs and when nothing is left to save.
  - The *Meter reset* tick shows on a counter row only after the `counter_lower` refusal.
  - A saved row is read-only and reads "Saved" (or S039's "Saved. Above the limit of 60 °C." / "Saved. Not OK: the expected answer is Yes."). *Undo* shows only for `equipment:edit` holders at the row's unit; for others the line "A wrong reading is removed by an engineer. Ask one." shows once after the first save.
  - Empty states: no meters at the site ("No machine at this site has meters. …", *Time taken* and the bar hidden, picker kept); no unit: the app's `noUnits` message; load failure with *Try again*.
- **Shared with S039.** `NOT_SAVED`, `isUnavailable` and `notSavedOr` moved from `ReadingFormModal.vue` into `meterLabels.js`; both screens use them. `isToday` is new there.

## 2. How it works

- **The sheet read (`meters.py`).** Six queries for the site, none per node: the site, its units, the machines (`unit_id IN …`), their children and grandchildren (`parent_id IN …`), the model meters of all models at once (`masters.read_models_meters`), the `node_meters` rows of all nodes (`_nodes_rows`) and the last reading per node and meter (`_last_readings`). `effective_meters` (S038, pure) then runs per node in memory, and `_add_last` puts `last` on each meter. The one-node reads (`_node_rows`, `_meters_out`) call the same batch helpers with one id.
- **The page (`ReadingsView.vue`).** It loads the masters' sites and units and `my-units`, picks the site, loads the sheet and keeps one state object per row (value, reset tick, phase, message, error). `ReadingSheetRow.vue` shows a row and reports Undo. Saving loops over the rows in screen order and reads each row's value at its turn. After a save, the first refusal on the page scrolls into view.
- **Undo** calls S039's `DELETE /api/equipment/<id>/readings/<reading_id>` with the id from the POST's answer; the row returns to editable with its value.

## 3. Files touched

Backend:
- `backend/meters.py`: the sheet route and its helpers; `_nodes_rows`, `_last_readings` and `_add_last` take many nodes.
- `backend/masters.py`: `read_models_meters` (many models, one query); `read_model_meters` calls it.
- `backend/equipment.py`: `my_units` gains `reading_unit_ids`.

Backend tests:
- `backend/tests/test_readings_api.py`: `TestSheet`, 15 cases (6 of them one parametrised 400).
- `backend/tests/test_equipment_api.py`: the three whole-dict `my-units` assertions extended; one new test for `reading_unit_ids`.

Frontend:
- `frontend/src/views/ReadingsView.vue` (new), `frontend/src/views/readings/ReadingSheetRow.vue` (new).
- `frontend/src/stores/navigation.js`, `frontend/src/router/index.js`: the item and the route.
- `frontend/src/stores/equipment.js`: `readingSites`; the comment on the `my-units` shape.
- `frontend/src/utils/meterLabels.js`: `NOT_SAVED`, `isUnavailable`, `notSavedOr`, `isToday`.
- `frontend/src/views/equipment/ReadingFormModal.vue`: uses the shared `notSavedOr`.

Frontend tests:
- `frontend/tests/navigation.test.js`, `frontend/tests/meterLabels.test.js`, `frontend/tests/readingSites.test.js` (new).
- `frontend/e2e/readings.spec.js` (8 S040 tests), `frontend/e2e/screens.spec.js` (`/readings` and the bottom-bar test).

Docs: see *Docs updated*; also this report and the brief's status.

## 4. Decisions taken

1. **A role without `reading:log` gets 403, not 404** (departure from § 8 "a storekeeper role: 404"). The route uses `require_perm("reading:log")` like every other route, which answers 403 when the key is held nowhere. A user who holds the key at another site only gets the 404 of § 5.1. The test names both.
2. **Batch reads in `masters.py` and `meters.py`.** `read_models_meters` is new; the node card's reads were turned into the same batch helpers instead of a second copy for the sheet.
3. **`ReadingSheetRow.vue` is a new component** the brief's *Where* does not list. It keeps the view's template readable (a row has five states).
4. **Counts use every meter row of the sheet,** including the machines folded as out of use. "3 of 48 filled" and "9 of 48 read today" share one denominator (BR2-05); the idle presses count as rows not read.
5. **The bar is `position: sticky` inside the page, so no end padding is needed.** In the flow, it takes its own space after the last unit; the brief's padding is for a fixed bar. The "Ask an engineer" line sits inside the bar.
6. **The first refusal is scrolled into view after a save** (S026). The e2e test on the iPhone found the refusal of a row far above the Save button out of view.
7. **A site that answered 404 is dropped from the offered list for the session,** and the picker shows with "Pick a site" until another is chosen; if none is left, the `noUnits` message shows.
8. ***Save readings* is also disabled when no row is waiting to be saved,** so a press never does nothing in silence.
9. **New screen words:** "The reading was not removed. Try again in a minute." (Undo with no answer), "Show out of use (n)" / "Hide out of use", "Pick a site" (picker placeholder).
10. **Switching the site discards the typed rows** without asking; only *Time taken* is kept (§ 1.2). Said here because the brief is silent on a dirty sheet.
11. **`screens.spec.js`: `shows(page, key)`** takes the role, so the manager's check can be the picker and the others' the heading.

## 5. Not done, deferred or assumed

- **Real-device check** (row 33 of `device-checks.md`): the keypad, the keyboard over a message and the bar, the thumb on *Yes* / *No*.
- **Standards numbers** stay "to verify" (U4 D12); no screen cites them.
- **Assumed:** a part of a scrapped part is left out with it (the live rows are the ones read); a machine with meters only on a part is listed with no meters of its own.
- **Not done, as briefed:** a sheet across sites, shifts, offline entry.

## 6. Tests run

Final full run, `YANTRA_TEST_RUN=s040c1 tooling/run-tests.bat`:

| Suite | Result |
|---|---|
| backend | PASSED, 2964 passed, 105 s |
| frontend | PASSED, 167 passed, 31 s |
| deps | PASSED, 42 passed |
| tooling | PASSED, 115 passed, 13 s |

- `npx vite build` in `frontend/`: built in 4.25 s, the usual chunk-size warning only.
- **New e2e tests alone first** (`E2E_LANES=1`, `desktop-chromium`, `-g "S040"`): the first run had 3 failures, all in my tests (a last-reading hour ago reads "Today …", not a date; the Save button is not in the viewport on desktop). Second run: 8 passed. Then phone-chromium and phone-webkit: one failure, the refusal out of view (*Decisions taken* 6); fixed, and both passed.
- **Full e2e suite** (`tooling/run-e2e-tests.bat`, 6 lanes, three projects), because the nav is shared frontend code: **407 passed, 0 failed, 7 skipped** in 12.1 min (414 tests). The 7 skips are the 6 that S039 reported and the new bottom-bar test on desktop-chromium (it skips itself where there is no bottom bar). No known flaky test failed: `masters.spec.js:62`, `tickets-raise.spec.js:141` on phone-webkit and `tickets-parts.spec.js:129` all passed.

## Manual checks

- [auto] **Important.** The end-of-day sheet saves the filled rows and shows each refusal (one good row, one too-low counter row with its *Meter reset* tick; no sideways scroll on Pixel 7 and iPhone 14) — `frontend/e2e/readings.spec.js::S040: the end-of-day sheet saves the filled rows and shows each refusal`
- [auto] Undo on a saved row makes it editable again — `frontend/e2e/readings.spec.js::S040: Undo on a saved row makes it editable again`
- [auto] The operator's saved row reads Saved, the sheet shows the Ask an engineer line once, no Undo; the operator's sheet shows MCC2 only — `frontend/e2e/readings.spec.js::S040: the operator's saved row reads Saved, the sheet shows the Ask an engineer line once, and there is no Undo`
- [auto] A shift production row takes an amount lower than the last one — `frontend/e2e/readings.spec.js::S040: a shift production row takes an amount lower than the last one`
- [auto] **Important.** A Yes / No row answered No saves and shows Not OK (buttons at least 48 px high and inside the viewport; a second tap clears) — `frontend/e2e/readings.spec.js::S040: a Yes / No row answered No saves and shows Not OK`
- [auto] Save readings is disabled while saving; its box is inside the viewport and above the bottom bar on a phone — `frontend/e2e/readings.spec.js::S040: Save readings is disabled while saving, and the bar is above the bottom nav`
- [auto] The supervisor sees no site picker and both units on one sheet; the manager picks a site and it is remembered — `frontend/e2e/readings.spec.js::S040: the supervisor sees no site picker and both MCC1 and MCC2 on one sheet; the manager picks a site and it is remembered`
- [auto] A meter read today shows Today and its tick — `frontend/e2e/readings.spec.js::S040: a meter read today shows Today and its tick`
- [auto] `/readings` opens for the reading roles (heading with the site code, or the picker for the manager) — `frontend/e2e/screens.spec.js::every screen opens as <role>`
- [auto] The manager's bottom bar shows all six items without sideways scroll — `frontend/e2e/screens.spec.js::S040: the manager's bottom bar shows all six items without sideways scroll`

On a real device (row 33 of `docs/steps/device-checks.md`):

- [ ] **Important.** The decimal keypad on an Android phone and an iPhone on the sheet, the keyboard not hiding a row's message or the *Save readings* button, and *Yes* / *No* easy to hit with a thumb. Account: a test login with the Supervisor role at SMTW; company Wi-Fi; production on the TEST machine, or the dev server.

## Docs updated

- `docs/Plan.MD`: § 4.5, a "Built (S040)" bullet (route, sheet read, `reading_unit_ids`, saving, Undo, the folded machines); § 6, the *Readings* screen and the nav order.
- `.claude/CLAUDE.md` § SMTW-Review: the spec map (`readings` S039/S040); the meter-readings point names the sheet as a user of `log_reading`.
- `docs/steps/device-checks.md`: row 33, the real-device check of § 8.
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`: none, because the step adds no maintenance rule, plant fact, role, claim or secret.
- Round 1: `docs/Plan.MD` § 4.5 again (a refused *Time taken* shows once and stops the loop; switching the site with typed readings asks first). Nothing else, because the round adds no migration, role, secret, plant fact or maintenance rule, and `device-checks.md` row 33 is unchanged.

## Fix rounds

### Round 1

Answers to `4-code-review-r1.md`. Run name `s040c2`. The machine's clock during the work was 00:17 to 00:45 IST on 25-10-2026, the hour CR1-01 is about.

**CR1-01 (blocker): Fixed.** `frontend/e2e/readings.spec.js` no longer assumes that "an hour ago" is today.
- `lastLine(taken, reading)` builds the expected last-reading text with the screen's own rule: "Today HH:MM · v" when the date is today in IST, else "v · DD-MM-YYYY HH:MM". The save test and the shift test use it. The shift test no longer assumes the "Today" form.
- The "read today" test takes its reading `Math.min(2, minutesIntoIstDay())` minutes ago, so it is always today's, also at 00:01.
- Red, then green on the real clock. At 00:19 IST, before the fix, "saves the filled rows" and "a shift production row" failed on desktop-chromium (`Received string: " 420 pcs · 24-10-2026 23:19 "`). After the fix, all 8 old S040 tests pass at 00:21 on desktop-chromium, and in the later runs on all three projects. The important check's `[auto]` stands on those green runs.

**CR1-02 (minor): Fixed.**
- The picker is `disabled` while saving, so `resetStates()` cannot run mid-save and the `TypeError` is gone. `saveAll` also clears a waiting question.
- A site picked while typed, unsaved readings exist does not switch. The picker goes back to the current site and an inline question shows: "Discard 3 typed readings? Switching site removes them. You cannot get them back." with *Discard* and *Keep*. With nothing typed, the switch needs no question. This replaces Decision 10.
- Tests: "the site picker asks before it discards typed readings, and waits during a save" (question text, picker back on SMTW, *Keep* keeps the value, picker disabled during a held POST) and "Discard on the picker's question switches site and drops the typed readings".
- Both fail without the fix (mutation run below).

**CR1-03 (minor): Fixed.** `nothingToShow` no longer requires `!siteGone`. With no site left, the app's no-units message shows, as Decision 7 says. After a 404 the picker shows only when other sites are left. Test: "a 404 with no site left shows the no-units message, not an empty picker" (no picker, no "no longer available" warning, `yantra.readings.site_id` forgotten). It fails without the fix.

**CR1-04 (minor): Fixed.**
- `markRefused` no longer writes `timeError`. A 400 on `taken_at` stops the loop and shows its message once, on the shared field. The refused row and every filled row after it read "Not saved. Change Time taken, then save again." (new screen text; "Try again in a minute" would be wrong here), with their values kept. The page scrolls to the time field's message.
- A 409 `SAME_MINUTE` stays on its row, the loop goes on, and the time field is not marked.
- Tests: "a refused Time taken shows once on the time field and stops the loop" (8 days back; one `.invalid-feedback`; one POST only) and "a reading already at that minute is refused on its own row, not on Time taken". Both fail without the fix.

**CR1-05 (minor): Fixed.** New e2e tests, each on its own machine with two rows:
- "a failed save (503) stops the loop…" and "a failed save (no answer)…" (`route.abort`): both rows read "Not saved. Try again in a minute.", both values are kept, exactly one POST was sent, and *Save readings* is enabled again.
- "a 404 on the sheet forgets the site and offers the sites that are left" (manager: the first sheet read answers 404; the warning shows, `yantra.readings.site_id` is null, one site is offered, and picking it opens its sheet).
- The no-site-left 404 test is under CR1-03.
- The two failed-save tests fail when the loop does not stop. The 404-with-sites-left test passes on the old code too, because that behaviour was already right; it now guards it.
- `test.use({ serviceWorkers: "block" })` at the top of `readings.spec.js`: on WebKit, `page.route` did not intercept the page's requests while the app's service worker controlled the page, so the new tests failed on phone-webkit until then. The S021 worker has no `fetch` handler and caches nothing. The option applies to the S039 tests of the file too; they do not use push.

**Red, then green (mutation run).** I put the old behaviour back into `ReadingsView.vue` at six places: no stop on 502/503/504, no `taken_at` stop, `timeError` set by every refusal, no confirm, picker never disabled, `!siteGone` in `nothingToShow`. I ran the eight new tests on desktop-chromium. Seven failed: both failed-save tests, the time test, the same-minute test, both picker tests, and the no-site-left 404 test. The 404-with-sites-left test passed, as said above. I restored the file (identical to the fixed copy) and the tests pass again.

**CR1-06 (nit): Fixed.** The two inline `IN (…)` lists in `backend/meters.py` (`_nodes_rows`, `_last_readings`) use `_marks`. `backend/masters.py:866` keeps its inline form, like the other `IN` lists of `masters.py`. `meters.py` imports `masters`, so `masters.py` cannot import `_marks`.

**CR1-07 (nit): Fixed.** The header comment of `ReadingSheetRow.vue` now says that the row writes the user's input into the parent's state object (`v-model`, `pick()`, the reset tick) and emits only Undo.

**CR1-08 (nit): Fixed.** `saveAll` sets `now.value = new Date()` first. A sheet left open past midnight now counts the new day's readings after a save.

**CR1-09 (nit): Fixed.** *Show out of use (n)* lost `p-0` and has `min-height: 44px` (class `show-idle`).

**CR1-10 (nit, design question): held for the user at gate B.** Not changed.

#### Decisions taken in this round

1. **Decision 10 is replaced.** Switching the site with typed readings asks first and keeps them on *Keep*. Words: "Discard n typed reading(s)? Switching site removes them. You cannot get them back." with *Discard* and *Keep*.
2. **A new screen text** for a refused *Time taken*: "Not saved. Change Time taken, then save again."
3. **A refused time marks the refused row too**, so every filled row says why it is not saved.
4. **The picker is re-created (`:key`) to put it back on the current site** while the question waits. A plain `v-model` would leave the `<select>` showing the new choice.
5. **Noted only:** `isToday` compares with the browser's own date, while the server stores IST. No finding asks for a change. The plant's browsers are on IST.

#### Tests run (round 1)

- `YANTRA_TEST_RUN=s040c2 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2964 passed (109 s), frontend 167 passed, deps 42 passed, tooling 115 passed. An earlier full run had `test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed` fail with `ConnectionAbortedError`, while the e2e run used the machine at the same time. That file passes alone (60 passed) and passed in the final full run.
- `npx vite build`: built in 4.47 s, the usual chunk-size warning only.
- E2E, `tooling/run-e2e-tests.bat e2e/readings.spec.js e2e/tickets-work.spec.js e2e/screens.spec.js` (6 lanes, 3 projects), final run: **163 passed, 1 failed, 1 skipped (165)**.
  - The one failure is `readings.spec.js:189` "S039: a No on a Yes / No meter, then Save, shows Not OK" on phone-webkit only ("Yes is off screen"). It is not caused by this round. It fails the same with the spec file that passed at 00:25, and it passes on phone-chromium. A probe on phone-webkit showed `devicePixelRatio` 3.75 and `innerWidth` 312, where the iPhone 14 emulation expects 3 and 390. The host's display scaling seems to be at 125 %, so WebKit zooms the page out. I did not touch that test. Check the Windows display scale (100 % expected), then run it again.
  - The S019 *Overdue* test (`tickets-work.spec.js:420`) passed in every run this round.
  - The eight new tests passed on all three projects in the final run.

#### Manual checks (round 1)

The list above stays. The first important check is green again with the clock-independent test. New `[auto]` rows:
- [auto] A failed save (503, no answer) stops the loop and keeps the values — `frontend/e2e/readings.spec.js::S040: a failed save (503) stops the loop; both rows read Not saved and keep their values` and `::S040: a failed save (no answer) stops the loop; both rows read Not saved and keep their values`
- [auto] A refused Time taken shows once and stops the loop; a same-minute clash stays on its row — `frontend/e2e/readings.spec.js::S040: a refused Time taken shows once on the time field and stops the loop (CR1-04)` and `::S040: a reading already at that minute is refused on its own row, not on Time taken (CR1-04)`
- [auto] The site picker asks before discarding typed readings and waits during a save — `frontend/e2e/readings.spec.js::S040: the site picker asks before it discards typed readings, and waits during a save (CR1-02)` and `::S040: Discard on the picker's question switches site and drops the typed readings (CR1-02)`
- [auto] A 404 on the sheet — `frontend/e2e/readings.spec.js::S040: a 404 on the sheet forgets the site and offers the sites that are left (CR1-05)` and `::S040: a 404 with no site left shows the no-units message, not an empty picker (CR1-03)`

### Round 2

Answers to `4-code-review-r2.md`. Run name `s040c3`. Only the Readings screen, `meterLabels.js` and their tests changed.

**CR2-01 (minor): Fixed.** The discard question follows FormModal's bar. *Keep editing* comes first as `btn-primary`, *Discard* second as `btn-outline-danger`. The text ends "You cannot undo this." (This replaces the wording of Round 1, Decision 1.) The CR1-02 test now checks the button order, the two classes and the new text, and clicks *Keep editing*. Red, then green: with the old bar put back, the test fails ("Expected substring: … You cannot undo this. Received: … You cannot get them back.DiscardKeep editing"); with the fix it passes.

**CR2-02 (nit): Fixed.** The question shows only while `wantedSite !== null && pending > 0`, and a `watch` on `pending` clears `wantedSite` when it drops to 0, so typing again does not bring the old question back. New test: "clearing the typed readings closes the picker's question (CR2-02)" (the picker stays on SMTW). Red, then green: with the old template and no watch, it fails ("Expected: 0, Received: 1" on the question); with the fix it passes.

**CR2-03 (nit): Fixed.** `isToday` compares the reading's date with the IST date of `now` (`Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" })`). The vitest cases build `now` from UTC strings, so they do not depend on the machine's time zone. New case: "isToday counts the IST day whatever the browser's time zone is (CR2-03)" (01:30 IST on 25-10 is 24-10 in UTC). Red, then green: with the local-date code and `TZ=UTC`, it fails; with the fix it passes under `TZ=UTC` and under the machine's IST. The note in Round 1, Decision 5 no longer applies.

#### Decisions taken in this round

1. **Button text *Keep editing*, as in FormModal**, not *Keep readings*. Same word for the same thing.
2. **Both a `v-if` guard and a `watch`** for CR2-02: the guard hides the question at once, the watch resets the state.

#### Docs updated (round 2)

None, because the round changes wording of a question and a date rule only. `docs/Plan.MD` § 4.5 names the question without its button words.

#### Tests run (round 2)

- `YANTRA_TEST_RUN=s040c3 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2964, frontend 168, deps 42, tooling 115.
- `npx vite build`: built in 4.42 s, the usual chunk-size warning only.
- E2E, `e2e/readings.spec.js` and `e2e/screens.spec.js` on desktop-chromium and phone-chromium (6 lanes): 67 passed, 1 skipped, 0 failed. No shared frontend code changed, so no full suite.
- phone-webkit, `e2e/readings.spec.js`, run once: 24 passed, 1 failed. The failure is the known `readings.spec.js:189` (S039 Yes / No, "Yes is off screen"), caused by the host display scale (CR r2). All S040 tests pass on phone-webkit, including the new one. Not counted as red.

#### Manual checks (round 2)

The list above stays. The picker test is now:
- [auto] The site picker asks before discarding typed readings, Keep editing first — `frontend/e2e/readings.spec.js::S040: the site picker asks before it discards typed readings, and waits during a save (CR1-02)`
- [auto] Clearing the typed readings closes the question — `frontend/e2e/readings.spec.js::S040: clearing the typed readings closes the picker's question (CR2-02)`

## Amendment A1 — Enter more readings after a save

Run name `s040a1`. Frontend only: no backend change, no migration.

### What was built

- After a save that leaves no row to retry, the round is read-only: every row (empty ones too) and *Time taken*. The save button reads *Saved* and is disabled.
- A button **Enter more readings** (`btn-primary`, 44 px minimum) sits beside it. It starts a new round: every row empty and editable, *Time taken* back to Now, the sheet reloaded so the saved round shows as each row's last reading, and the old round's *Undo* gone.
- A partial save keeps today's behaviour: the refused rows stay editable, *Save readings* stays enabled, and *Enter more readings* does not show.
- The server already refuses one meter at one minute. A browser test now proves it on the sheet.

### How it works

- `ReadingsView.vue`: `roundDone` is true when no save runs, no filled row is unsaved (`pending === 0`) and at least one row is saved. It passes `locked` to every row and to *Time taken*, and swaps the button. `enterMore()` sets `takenAt` to null, clears the time error and calls `loadSheet(siteId)`, which rebuilds the row states.
- Undo on a saved row makes it a pending row again, so `roundDone` turns false and the round opens at once.
- Switching the site or leaving the page asks nothing after a saved round, because the discard question counts only typed, unsaved rows (`pending`).
- `ReadingSheetRow.vue`: new prop `locked`; the input is `readonly`, the Yes / No buttons are disabled and the *Meter reset* tick is hidden when the row is saved or locked.
- `EventFields.vue`: new prop `locked` (default false): *Change* and *Now* are hidden and the input is `readonly`.

### Files touched (6)

- `frontend/src/views/ReadingsView.vue`: `roundDone`, `enterMore`, the two buttons.
- `frontend/src/views/readings/ReadingSheetRow.vue`: `locked`.
- `frontend/src/views/tickets/EventFields.vue`: `locked`.
- `frontend/e2e/readings.spec.js`: three new tests.
- `docs/Plan.MD`: § 4.5 S040 bullet.
- `docs/steps/S040-readings-sheet/3-impl-report.md`: this section.

### Decisions taken

1. **`locked` on the shared `EventFields.vue`** (a small additive prop, default false, so the ticket dialogs are unchanged), rather than a copy of the time field on the sheet. The brief names only the two sheet files; this is a forced choice to avoid a near-copy.
2. **Undo stays available in a read-only round** (for `equipment:edit` holders). A1 says "every row is read-only" and the existing S040 Undo test and § 1.6 need Undo; Undo is how a wrong round is corrected.
3. **If the reload of *Enter more readings* fails**, the sheet shows the usual "Readings could not be loaded. Try again in a minute." with *Try again*, and the old round is gone (it was saved). I did not keep the old view under the error.
4. **A saved round at "Now" and the next round at "Now" in the same minute** are refused by the server (`SAME_MINUTE`), as the user's question expects. The test sets the first round's time back 30 minutes so the second round, at Now, is another minute.
5. After a round saved at "Now", *Time taken* still reads "Now" while locked (it is not turned into a clock time).

### Not done

- phone-webkit: not counted. This PC's display scale (125 %) is blocked by S045's guard.
- No vitest case: no pure logic changed.
- I did not run `tickets-*.spec.js` although `EventFields.vue` is shared with the ticket dialogs; the prop defaults to off and S045's files stay untouched. Say if you want a run.

### Docs updated

- `docs/Plan.MD` § 4.5: one sentence on the read-only round and *Enter more readings*.
- Others: none, because there is no migration, role, secret, plant fact or maintenance rule. `docs/steps/device-checks.md` row 33 is unchanged (no new real-device check in A1).

### Tests run

- Red first: the three new tests, `E2E_LANES=1`, desktop-chromium, `-g "S040 A1"`, before the change: 3 failed (the button *Enter more readings* was not found). After the change: 3 passed. One of my tests then needed a fix (the second round at Now fell in the first round's minute and got the 409; see decision 4).
- `YANTRA_TEST_RUN=s040a1 tooling/run-tests.bat`: ALL SUITES PASSED. Backend 2964, frontend 168, deps 42, tooling 115.
- `npx vite build`: built in 4.24 s, the usual chunk-size warning only.
- E2E `readings.spec.js` and `screens.spec.js` on desktop-chromium and phone-chromium (6 lanes): 73 passed, 1 skipped (the bottom-bar test, which skips itself on desktop), 0 failed. No full suite: no shared file in the `FormModal`/`api.js`/router/auth/`support` list changed.

### Manual checks (A1)

- [auto] A full save makes the round read-only, *Saved* is disabled, and *Enter more readings* starts a fresh round — `frontend/e2e/readings.spec.js::S040 A1: a full save makes the round read-only, and Enter more readings starts a fresh one`
- [auto] A partial save keeps the refused row editable and shows no *Enter more readings* — `frontend/e2e/readings.spec.js::S040 A1: a partial save keeps the refused row editable and offers no Enter more readings`
- [auto] The same meter at the same minute is refused in the next round; another meter is not — `frontend/e2e/readings.spec.js::S040 A1: the same meter at the same minute is refused in the next round; another meter is not`
