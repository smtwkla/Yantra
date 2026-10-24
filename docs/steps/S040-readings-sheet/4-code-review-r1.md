```
Step: S040 — End-of-day readings sheet
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 1

**Verdict: one `blocker` is open (CR1-01).** Two new S040 browser tests fail in all three projects when they run between 00:00 and 01:00 IST. The fault is in the tests, not in the screen. Apart from that, the sheet is built as briefed. The four minor findings are about typed input lost on a site switch, a dead-end screen after a 404, a bad *Time taken* refused once per row, and two untested failure paths.

Scope: the working tree (tracked and untracked files) against the snapshot `refs/steps/S039` (48373a9), read with a temporary index, so the S039 files show only S040's changes.

## Test results (this review, run name `s040cr1`)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | **PASSED**. Backend 2964 passed, frontend 167, deps 42, tooling 115. |
| `npx vite build` | **PASSED**, built in 4.71 s. Only the usual chunk-size warning. |
| Full e2e (`tooling/run-e2e-tests.bat`, 6 lanes, 3 projects), started 23:57 on 24-10, finished 00:09 on 25-10 | **RED**: 404 passed, 3 failed, 7 skipped. The 3 failures are `tickets-work.spec.js:420` (S019 *Overdue*) in each project. The seed was written before midnight and the test ran after it, so "yesterday" moved by one day. This is not an S040 fault, and the test passed on the re-run below. |
| Targeted re-run: `e2e/tickets-work.spec.js e2e/readings.spec.js e2e/screens.spec.js`, 00:10–00:15 on 25-10 | **RED**: 134 passed, 6 failed, 1 skipped. The 6 failures are `readings.spec.js:235` and `readings.spec.js:325` in each project (CR1-01). |

Why the full suite: S040 changes the router (`router/index.js`) and the nav store. The router is listed as shared frontend code.

## Findings

### CR1-01 (blocker) — two S040 e2e tests fail in the first hour after midnight IST

- **Where:** `frontend/e2e/readings.spec.js:240`, `:247`, `:327`, `:331`. Also `:432`, `:438`, which has a two-minute window.
- **Problem:** the tests log a reading `istLocal(60)` (60 minutes ago). They then expect the row to read "Today HH:MM · …". Between 00:00 and 01:00 IST, that reading is yesterday's, and the screen correctly shows "1,000.0 h · 24-10-2026 23:10". Line 432 does the same with `istLocal(2)`, so it fails between 00:00 and 00:02.
- **Failure scenario:** observed in this review. At 00:10 IST the re-run failed "the end-of-day sheet saves the filled rows and shows each refusal" (an **important** check) and "a shift production row takes an amount lower than the last one" in Pixel 7, iPhone 14 and desktop. A late-night release check or full run is red for an hour every day.
- **Fix:** keep "earlier" inside today. For example, use `istLocal(Math.min(60, minutesSinceIstMidnight - 1))`, or skip the "Today" wording when the reading crosses midnight. Better still, assert the line with the same rule the screen uses: "Today HH:MM · …" when the date is today, else "… · DD-MM-YYYY HH:MM". Line 331's `"· 420 pcs"` assumes the "Today" form in the same way. Then re-run the readings spec, and keep the `[auto]` mark of the important check only with that green run behind it.

### CR1-02 (minor) — switching the site drops typed readings, and the picker stays live during a save

- **Where:** `frontend/src/views/ReadingsView.vue:153-155` (the `watch` on `siteId`), `:77-81` (`resetStates`), `:268` (the `<select>`, not disabled while saving), `:209-211`.
- **Problem:**
  - Decision 10 is a choice the brief did not make. It loses typed input with no question. That goes against the app's own S007 rule ("no lost input") and CLAUDE-COMMON scope B, which asks the screen to state a consequence before it acts.
  - The picker is also not disabled while *Save readings* runs. A switch during the loop calls `resetStates()`, which deletes the old site's row states. The next iteration of `saveAll` then reads `states[row.key].phase` on `undefined` and throws a `TypeError`. The remaining rows are never posted, and no message says so.
- **Failure scenario:** a manager types 20 readings at SMTW and touches the site picker by mistake on a phone. All 20 values are gone. Or they change the site while the save runs: the rows after the current one are silently not saved.
- **Fix:** disable the picker while `saving` is true. When filled rows that are not yet saved exist, ask before the switch. For example: "Switch to BRICKS? The 5 readings you typed are not saved." with *Switch site* and *Stay*. Revert the `<select>` if the user stays.
- **Note:** the picker shows only to users who log readings at several sites (manager, admin). Press supervisors with one site are not affected, so this is `minor`.

### CR1-03 (minor) — after a 404 with no other site left, the screen offers an empty picker

- **Where:** `frontend/src/views/ReadingsView.vue:52-53` (`showPicker`, `nothingToShow`), `:139-144`.
- **Problem:** after a 404, `siteGone` stays true until a load succeeds. `nothingToShow` requires `!siteGone`, so it never becomes true. Decision 7 says that when no site is left, the `noUnits` message shows. The code shows something else: a `<select>` whose only option is the disabled "Pick a site", under the warning "This site is no longer available. Pick another site."
- **Failure scenario:** an operator's only site is deactivated while their tab holds the cached lists. They open *Readings* and are told to pick another site, but the list has none. The screen has no way forward, and its text asks for something the user cannot do.
- **Fix:** when `siteChoices` is empty after a 404, show the `noUnits` message, as Decision 7 says. For example, make `nothingToShow` true when `siteChoices.length === 0`, and keep the picker only when choices remain. Add an e2e or component test with a routed 404 (see CR1-05).

### CR1-04 (minor) — a refused *Time taken* is posted and shown once per row; a one-row clash marks the shared time field

- **Where:** `frontend/src/views/ReadingsView.vue:196-201` (`markRefused`), `:209-228`; `backend/meters.py:57`, `:365` (`SAME_MINUTE`, 409 on `taken_at`).
- **Problem:**
  - The sheet has one *Time taken*. When the server refuses it (for example, more than 7 days back), the loop still posts every filled row. Each row then shows the same refusal.
  - The other way round: `SAME_MINUTE` is a refusal of **one** row (that meter already has a reading at that minute). Because its field is `taken_at`, `markRefused` also puts the message on the sheet's shared time field. That suggests the whole sheet's time is wrong.
- **Failure scenario:**
  - A supervisor sets *Time taken* to 8 days back and fills 30 rows. *Save readings* sends 30 POSTs, and the page shows the same refusal 31 times.
  - A supervisor logs Run hours on the equipment page at 17:50, then saves the sheet with "Now" within the same minute. The time field says "A reading at this time exists. Pick another time, or remove that reading first." It reads as if every row has a clash.
- **Fix:**
  - Stop the loop on a 400 refusal of `taken_at` (the time is the sheet's, so every row would get the same answer). Show it once on the time field, and mark the remaining rows "Not saved".
  - Keep a 409 `SAME_MINUTE` on its row only. For example, set `timeError` only for a 400 on `taken_at`, not for a 409.

### CR1-05 (minor) — the stop-on-failure loop and the 404 path have no test

- **Where:** `frontend/src/views/ReadingsView.vue:203-235` (`saveAll`), `:136-150` (`loadSheet`'s 404 branch); `frontend/e2e/readings.spec.js`.
- **Problem:**
  - The brief's main failure rule has no test of the screen: a 502, 503, 504 or no answer stops the loop, and the failed row and every filled row after it read "Not saved. Try again in a minute." with their values kept (§ 1.7). Only the helper `isUnavailable` and `notSavedOr` has unit tests. Nothing checks that the loop stops, that later rows are not posted, or that their values stay.
  - The 404 path ("This site is no longer available…", the remembered site forgotten; BR2-07) is also untested. That is how CR1-03 got through.
- **Failure scenario:** a later change keeps going after a 503, or clears the typed values. The suite stays green, and on a weak plant network the supervisor loses the rest of the sheet.
- **Fix:** add one e2e test that fills two rows on the test's own machines. Use `page.route` to answer the first POST with 503 (and one variant with `route.abort()` for no network). Assert that both rows read "Not saved. Try again in a minute.", that both values are kept, and that the second POST was never sent. Add one test that routes the sheet GET to 404 and asserts the message and the forgotten `yantra.readings.site_id`.

## Nits

- **CR1-06** (nit) `backend/meters.py:80`, `:274`, `backend/masters.py:866`: S040 adds `_marks(ids)` at `meters.py:435`, but the three other new `IN (…)` lists in the same diff write `", ".join(["%s"] * len(...))` inline. Use `_marks` in `meters.py`, or keep the inline form everywhere.
- **CR1-07** (nit) `frontend/src/views/readings/ReadingSheetRow.vue:14-15`, `:46`, `:84`, `:95`: the header says the row "only reports what the user does". The row in fact writes the parent's state object through `v-model="state.value"` and `pick()`. Correct the comment, or emit updates.
- **CR1-08** (nit) `frontend/src/views/ReadingsView.vue:39`, `:132`: `now` is set only when the sheet loads. A sheet left open across midnight keeps yesterday's "Today" marks and count. Set `now.value = new Date()` at the start of `saveAll`.
- **CR1-09** (nit) `frontend/src/views/ReadingsView.vue:330`: *Show out of use (n)* is `btn btn-link p-0`, a text-sized tap target on a floor screen. Drop `p-0`, or give it the row height.
- **CR1-10** (nit, design question for gate B) `frontend/src/views/ReadingsView.vue:84-90`: Decision 4 counts the folded out-of-use rows, so "N of M read today" never reaches M while idle presses are folded. Ask the user whether the counts should use only the shown rows. The brief's BR2-05 asks for one denominator, which either choice keeps.

## The four departures and the Decisions taken

| Item | Judgement |
|---|---|
| 1. 403, not 404, for a role with no `reading:log` anywhere | **Accepted.** `require_perm` answers 403 on every route, and the screen never sends such a user there (`canOpenRoute` is false, tested in `navigation.test.js`). A user who holds the key elsewhere still gets the brief's 404 (`test_a_site_without_a_unit_of_the_user_is_404`). Reported as Decision 1. |
| 2. A new `ReadingSheetRow.vue` | **Accepted.** It is presentation only, and the split keeps the view readable. Reported as Decision 3. Only CR1-07 applies. |
| 3. S039's not-saved helpers moved to `meterLabels.js` | **Accepted.** The brief asked for this (BS1-02). `ReadingFormModal.vue` now uses `notSavedOr` from there, with no change in behaviour. It has unit tests for 502, 503, 504, no status, and the pass-through of 400, 403, 404, 409 and 500. |
| 4. The sticky bar in the page flow, without end padding | **Accepted.** `position: sticky; bottom: 0` on the last child of the sheet pins the bar to the bottom of `.app-content` (`overflow-y: auto`, `App.vue:106`). That is above the 56 px nav, because `.app-main` has `padding-bottom: 56px` (`main.css:78`). In its own place at the end of the sheet, the bar takes its own height, so the last row is reachable without padding. The −1.5 rem margin matches `.app-content`'s padding. Checked by the e2e box test on Pixel 7 and iPhone 14. |
| Decision 4 (counts include folded rows) | Consistent with BR2-05. A question for the user (CR1-10). |
| Decisions 6, 8 (scroll to the first refusal; Save disabled when nothing is pending) | Good: they serve S026 and the "never does nothing in silence" rule. |
| Decision 7 (a 404 site dropped; `noUnits` when none is left) | The second half is not what the code does (CR1-03). |
| Decision 9 (new screen words) | Scope B holds. Each message is one plain line saying what happened and what to do. "Pick a site" is a placeholder, not a button. |
| Decision 10 (switching the site discards typed rows) | **Not accepted as is.** Typed input is lost without a question (CR1-02). |
| Decision 11 (`shows(page, key)`) | Fine. |

## S039 CR2-01 — verified

`savedMessage` (`frontend/src/utils/meterLabels.js:90-101`) returns "Saved. Above the limit." when `max_value` is null, and "Saved. Below the limit." when `min_value` is null. The vitest case "does not name a limit the meter does not have (CR2-01)" (`frontend/tests/meterLabels.test.js:73-78`) asserts both. Moving S040's helpers into the same file did not touch it.

## Checked and found consistent

- **Site scoping:**
  - `_sheet_units` (`meters.py:419-432`) uses `accessible_unit_ids(cur, "reading:log")`. That key is in `SITE_SCOPED` (S039), so the set holds only the units of sites where the person logs readings.
  - An inactive or unknown site, an empty set, or a site with no matching active unit each give 404.
  - Admin's set is `None`, so the route checks `active` on the site and units itself (BR1-17). This is tested for admin.
  - IT admin and the storekeeper get 403.
  - `site_id` is checked as ASCII digits ≥ 1, so "1.5", "-1", "0", "abc" and an empty value each give 400 "Pick a site" on `site_id`.
  - The actor is never taken from the client.
- **Batch reads, no N+1:** the sheet makes seven queries whatever the site's size: the site, its units, the machines, the children, the grandchildren, the model meters, the node meters, and the last readings. `unit_id` is set only on the top level (`schema.md:40`), so the machines query cannot pick up parts. Scrapped nodes are left out at each level, and a scrapped part's own parts go with it. The one-node card reads (`_node_rows`, `_meters_out`, `read_model_meters`) now call the same batch helpers with one id, and the S038 and S039 tests still pass. All SQL is parameterised. The `IN` lists are built only from `%s` marks.
- **`my-units`:** `reading_unit_ids` sits beside `edit_unit_ids`. The three whole-dict assertions are extended (BS1-03), with a new test for operator plus storekeeper at two sites. Admin gets `null`, IT admin `[]`, and a user with no rows `[]`.
- **Undo only for `equipment:edit`:** `canUndoAt(unit.id)` reads `edit_unit_ids` (`null` = every unit). The *Ask an engineer* line shows once, after a saved row without Undo. The server's remove route still enforces the key. Undo is disabled while a save runs, and it keeps the value. A 409 shows on its row.
- **The *Meter reset* tick** shows only after `err.code === "counter_lower"` (`api.js:25` carries `code`). No message text is matched. `is_reset` is sent only for counters. Amount and Yes / No rows never show the tick, as e2e asserts for the amount row.
- **The save loop:** it stops on 502, 503, 504 or no status (`isUnavailable`). The failed row and the filled rows after it read `NOT_SAVED` with their values kept. A 400 or 409 shows on its row and the loop goes on. A second press skips saved rows (e2e: the oil row's history total is 1). The value posted is the one at the row's turn.
- **Phone layout:**
  - Unit headings are sticky (`top: 0`, `z-index: 2`, below the bar's 3).
  - The Yes / No buttons are `btn-lg` with `min-height: 48px`, and e2e checks their boxes are inside the viewport.
  - The inputs use `inputmode="decimal"` with the unit as an `input-group-text`.
  - No fixed widths. e2e checks for no sideways scroll on both phones.
  - Undo is `btn-sm`. It is for engineers only, as the S039 card's engineer buttons are (S039 CR2).
- **Nav and `navigation.test.js`:** *Readings* sits after *Tickets* with `reading:log`. The five `visible(...)` lists are extended. A new case checks the order and `canOpenRoute` for operator, supervisor, engineer and manager, and the refusal for the storekeeper and IT admin. `screens.spec.js` opens `/readings` for the reading roles and checks the manager's six-item bottom bar.
- **e2e quality:** each S040 test makes its own machines with `meterMachine` and reads only its own card. Counts are read as differences. The tests assert what the user sees (messages, `readonly`, `aria-pressed`, boxes) and check server state through the API. The sheet opens no dialog, so `expectDialogFits` does not apply.
- **Empty states:** a site with no meters shows the message with the picker kept, and *Time taken* and the bar hidden (e2e on BRICKS). A user with no units sees the app's `noUnits` text. A load failure shows "Readings could not be loaded. Try again in a minute." with *Try again*.
- **`localStorage`:** read and written in `try`/`catch`. A remembered site no longer offered falls back to the first site. The e2e test covers the reload.
- **Docs pass:** `## Docs updated` matches the diff. `Plan.MD` § 4.5 and § 6 are updated, as are the `.claude/CLAUDE.md` spec map (`readings` S039/S040) and the meter-readings point, and `device-checks.md` row 33. No migration, so no schema doc is due. No other doc in § Docs to keep current is made wrong.
- **Manual checks:** the impl report's `## Manual checks` carries every check of § 8. The two important automated ones are `[auto]`. The real-device check is an open box matching row 33. CR1-01 leaves the first important check without a green run of mine until it is fixed.
- **Track:** full. No migration.
- **Writing style:** the impl report is in scope A. The screen text in the new files is in scope B, apart from CR1-03's dead-end message.

## For the user's manual browser check

- Row 33 of `docs/steps/device-checks.md`, on an Android phone and an iPhone:
  - the decimal keypad;
  - the keyboard not hiding a row's message or *Save readings*;
  - *Yes* / *No* easy to hit with a thumb.
- On a phone: scroll a long sheet and check that the unit heading stays visible under the top bar and that the sticky bar never covers a row's message.
