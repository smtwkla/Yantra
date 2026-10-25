```
Step: S050 — Meter reading register
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S050 — Meter reading register: implementation report

The register is built as briefed: a *Register* tab on *Readings*, *Open register* on the *Meters* card, one read-only route, and the raise screen's search moved to a shared `EquipmentPicker.vue`. There is no migration, no new permission key and no write. All four suites pass, and so do the targeted and the whole browser suites at Normal (§ 6). No open question. Four small choices the brief does not settle are flagged under *Decisions taken* (items 1, 2, 5 and 8).

## 1. What was built

- **Tabs on *Readings*.** *Sheet* (S040's sheet, moved unchanged to `readings/ReadingsSheet.vue`) and *Register*. The tab is in the URL (`?tab=register`); *Sheet* is the default for a `reading:log` holder. A user without `reading:log` (the storekeeper, IT admin) gets only *Register* and no tab bar; a typed `?tab=sheet` opens *Register* for them, so the sheet never mounts.
- **Typed readings survive a tab switch.** Each tab mounts the first time it shows, then stays mounted (seen-flag with `v-if`, then `v-show`). A user who arrives on `?tab=register` never mounts the sheet, so no `GET /api/readings/sheet` runs.
- **The nav item** *Readings* now needs `equipment:read` (was `reading:log`); its place is unchanged, after *Tickets*.
- **`EquipmentPicker.vue`** (new, `components/`): the raise screen's search, unchanged in behaviour and wording (*Which equipment?*, "Code or name", "Searching…", "No equipment found at your units.", "More found — type more of the code or name.", 20 matches at any level, `full_path` under each). It emits `@pick` with the id. *Raise ticket* and the register both use it.
- **The register** (`readings/ReadingsRegister.vue`, new):
  - no node: the picker and "Find a machine or part to see its readings.";
  - a node (`&node=<id>`): a node card (code — name, `full_path`, *Open equipment page*, *Change*), the picker hidden;
  - *Meters: All* opens a check box per column and *Show all*; the last tick is disabled; the choice is in the URL (`&meters=3,7`, absent = all); the boxes tick the answer's `shown`;
  - the table: *Time* first ("23-10-2026 18:00"), then one column per meter, headed "Run hours (h)" or a Yes / No type's name alone; a column of a meter no longer on the node carries the grey line "No longer on this machine"; a cell holds the number only (Indian grouping) or *Yes* / *No*, with *High*, *Low*, *Not OK*, *Reset* badges; empty when that meter has no reading at that minute;
  - 30 rows a page, *Show more*;
  - on a phone the time column is sticky on the left and the meter columns scroll inside the frame;
  - empty states and failures in the brief's words (§ 1.7): no meters, "No readings yet.", the 404 / 403 message (with the picker under it), and the load failure with *Try again*.
- ***Open register*** on the *Meters* card header, a link to `/readings?tab=register&node=<id>`, shown while the node has a meter in force, for everyone who sees the card.
- **The route** `GET /api/equipment/<id>/readings/register?meter_type_ids=&page=&per_page=` (`equipment:read`), in the brief's § 6 shape.

## 2. How it works

- **Pure core (`meters_core.py`).**
  - `parse_meter_type_ids(raw) -> (ids, errors)`: None for absent or empty; a comma list of positive integers, trimmed, duplicates dropped in first-named order; anything else is "Pick a meter" on `meter_type_ids`.
  - `register_columns(meters_in_force, read_types)`: the `effective_meters` list in its order (the *Meters* card's: by name), each `in_force: true` with its limits; then each type with an active reading that is not in force, by name, `in_force: false`, no limits.
  - `shown_meter_ids(columns, wanted)`: the wanted ids that are columns, in column order; all columns when none is wanted or none is left (the stale bookmark).
  - `register_rows(readings, columns)`: groups the readings by `taken_at`, newest first; each cell `{id, value, limit_state, is_reset}`, the value worded by the column's kind (`answer_word` / `format_number`). Readings are taken in id order, so if the data ever holds two active readings of one meter at one minute, the higher id wins (a comment says so).
- **Shell (`meters.py`, `readings_register`).** It parses the ids and the paging, then in one cursor: `load_node_for_user(…, for_update=False, key="equipment:read")` (404 outside the units or unknown; the key checked at the node's site), `_meters_of` (the columns in force), one query for the types with an active reading on the node, then, for the shown types, `COUNT(DISTINCT taken_at)`, the page's minutes (`SELECT DISTINCT taken_at … ORDER BY taken_at DESC LIMIT … OFFSET …`) and the readings at those minutes (`taken_at IN (…)`). That is a fixed handful of queries, none per meter or row. With no column, the reading queries are skipped. Times go out through `rows_to_list` (`row_to_dict`), as everywhere.
- **The shell screen (`ReadingsView.vue`).** `tab` is *Register* when the user lacks `reading:log` or the URL says so; else *Sheet*. A tap on a tab replaces the query (as on *Me*). The register's last query is remembered while the sheet shows and given back on the way back, so the picked node and ticks stay.
- **The register screen.** `parseRegisterQuery(route.query)` reads `node` and `meters` (bad values dropped). A watch on the node and meters, active only while the tab shows and the route is *Readings*, reloads page 1; back from *Sheet* to the same URL keeps what is loaded. Another node clears the screen first; other ticks keep the table until the answer. *Show more* loads the next page and drops a row whose time is already shown (a reading logged between two pages); it shows while `page × per_page < total`.

## 3. Files touched

Backend:
- `backend/meters_core.py`: `parse_meter_type_ids`, `register_columns`, `shown_meter_ids`, `register_rows`; module docstring.
- `backend/meters.py`: the register route and `_read_meter_types`; imports; module docstring.
- `backend/tests/test_meters_core.py`: `TestRegisterColumns`, `TestShownMeterIds`, `TestRegisterRows`, `TestParseMeterTypeIds`.
- `backend/tests/test_readings_api.py`: `TestRegister` (§ 8.2).

Frontend:
- `frontend/src/components/EquipmentPicker.vue` (new): the search moved out of `RaiseTicketView.vue`.
- `frontend/src/views/RaiseTicketView.vue`: uses `EquipmentPicker`; its search code, `PICKER_SIZE` and the `useDebounced` import removed.
- `frontend/src/views/ReadingsView.vue`: now the tab shell.
- `frontend/src/views/readings/ReadingsSheet.vue` (new): the S040 sheet, unchanged but its import paths.
- `frontend/src/views/readings/ReadingsRegister.vue` (new): the register.
- `frontend/src/views/equipment/MetersCard.vue`: *Open register*; docstring.
- `frontend/src/stores/navigation.js`: *Readings* needs `equipment:read`.
- `frontend/src/router/index.js`: the route's comment only.
- `frontend/src/utils/meterLabels.js`: `formatReading(…, { unit: false })`; `meterHeader`, `parseRegisterQuery`, `registerQuery`.
- `frontend/tests/navigation.test.js`: every `equipment:read` role sees *Readings* after *Tickets*; IT admin's and the storekeeper's lists gain it.
- `frontend/tests/meterLabels.test.js`: the unit option, the header, the query helpers.
- `frontend/e2e/readings.spec.js`: nine `S050:` tests and their helpers (`logReadings`, `partOf`, `pickInRegister`).
- `frontend/e2e/screens.spec.js`: `/readings` for `EVERYONE`; the storekeeper and IT admin see *Which equipment?*; `READING_ROLES` removed.

Docs: `docs/Plan.MD`, `.claude/CLAUDE.md` (§ *Docs updated*); the brief's status, the README index row and this report.

Checked, no change needed: `backend/tests/test_rbac.py` (no route-to-key list; no new key), `backend/tests/conftest.py` (the existing fixtures sufficed), `tickets-raise.spec.js`, `journeys.spec.js` (both green unchanged).

## 4. Decisions taken

1. **A fourth pure function, `shown_meter_ids`** (beyond the three of § 3). The stale-id rule (§ 5.5: ignore ids that are not columns; none left = all) is a business rule, so it sits in the core with its tests rather than in the route.
2. **`full_path` on the answer's `node`** (beyond § 6's sample `{id, code, name, level}`). The node card needs it (BR2-02), and a user who comes from a link has no search row to take it from. The alternative, a second `GET /api/equipment/<id>`, was rejected. The columns' `meter_type` also carries `expected_answer` (it is `meter_type_of`'s shape, as on the *Meters* list).
3. **Seen-flag plus `v-show`, not `<KeepAlive>`** (§ 1.1 lets the coder choose). It is plain to read and keeps the S040 sheet component exactly as it was.
4. **The register's URL is remembered while *Sheet* shows.** A tab tap replaces the query as on *Me*; going to *Sheet* writes `{}` (the default), so without the memory the picked node and ticks would be lost on the way back.
5. **The chooser's label when not all are ticked: "Meters: 1 of 2".** The brief names only *Meters: All*. The chooser is a panel under the button, not a Bootstrap dropdown.
6. **The URL helpers went to `meterLabels.js`** (§ 9 item 4): parsing `node` and `meters` with bad values dropped is more than two lines. `meterHeader` sits beside them.
7. ***Show more* follows the server's pages** (`page × per_page < total`), not the rows shown (`ReadingHistoryModal` uses the rows). When a reading is logged between two pages, the newest minute is never in the loaded rows, so a rows-based test would leave a *Show more* that loads nothing, forever. The de-duplication by time (§ 5.3.5) is inline, as the history does by id; `useShowMore` is for a list already loaded, a different job.
8. **The first column is headed *Time*** (the brief gives no word).
9. **The picker's input id is `equipment-search`** (was `raise-search`); no test or style used the old id.
10. **On a 404 / 403 the picker shows under the message**, so "Find another machine." can be done at once.

No departure from the brief's rules, wording or API.

## 5. Not done, deferred or assumed

- Out of scope as the brief says: who logged a reading and its note (§ 9 item 1), a tap on a cell (§ 9 item 2), date ranges, export, charts.
- Assumed: the brief's cell example "the number only" holds for every kind but Yes / No, which reads *Yes* / *No* (BR1-10).
- `phone-webkit` was not run (Normal never runs it); the sideways-scroll test runs there in the release's Full run (§ 8.5).

## 6. Tests

- **Core, while coding:** `test_meters_core.py` 166 passed.
- **API, while coding:** `test_readings_api.py -k Register` 15 passed.
- **New e2e tests alone:** `E2E_LANES=1 … e2e/readings.spec.js --project=phone-chromium -g "S050"`: 9 passed; the `@device` test also alone on `desktop-chromium`: 1 passed.
- **Targeted, Normal** (`readings.spec.js`, `screens.spec.js`, `tickets-raise.spec.js`, `journeys.spec.js`; the readings and raise screens and the nav changed, journey 3 opens `/readings`): 83 passed, 1 skipped (S040's bottom-bar test skips itself on desktop: no bottom bar), 1.3 min.
- **`tooling/run-tests.bat`** (`YANTRA_TEST_RUN=s050c1`): backend 3054 passed, frontend 174 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- **`npx vite build`:** built; only the existing chunk-size warning.
- **Whole e2e suite, Normal** (`tooling/run-e2e-tests.bat`, no flag, no `--project`, run once when the coding was done): 200 passed, 4 skipped, 6 lanes, 117 s. The four skips are the tests' own device guards: S021's iPhone test (both Chromium projects) and its blocked-notifications test (phone-chromium), and S040's bottom-bar test on desktop.

## Manual checks

- [auto] **important** — S050: an engineer opens *Open register* from a press's *Meters* card and sees one row per reading time, newest first, one column per meter, with *High* on an over-limit gauge — `frontend/e2e/readings.spec.js`::S050: Open register on a press's Meters card shows a row per reading time, newest first, a column per meter, High on an over-limit gauge
- [auto] **important** — S050: unticking all but one meter leaves only that column and only the times that meter was read; the URL keeps it after a reload — `frontend/e2e/readings.spec.js`::S050: unticking all but one meter leaves its column and the times it was read; the URL keeps it after a reload
- [auto] **important** — S050: a supervisor types a value on the sheet, opens *Register*, comes back to *Sheet*, and the typed value is still there — `frontend/e2e/readings.spec.js`::S050: a value typed on the sheet is still there after a look at the Register tab (BR1-01)
- [auto] S050: the picker finds a component-unit by code (its row shows the `full_path`) and the register shows its own meters — `frontend/e2e/readings.spec.js`::S050: the search finds a component-unit by code, its row shows the full path, and the register shows its own meters
- [auto] S050: a link with a stale `meters=` id opens the register with the remaining columns, no error shown — `frontend/e2e/readings.spec.js`::S050: a link with a stale meters id opens the register with the remaining columns and no error
- [auto] S050: *Show more* adds the next 30 rows with no row twice — `frontend/e2e/readings.spec.js`::S050: Show more adds the next 30 rows with no row twice
- [auto] **important** — S050: the storekeeper sees *Readings* in the nav, only the *Register* tab, and can open a machine's register; `/readings?tab=sheet` opens *Register* for them — `frontend/e2e/readings.spec.js`::S050: the storekeeper sees Readings in the nav with only the Register tab, opens a machine's register, and ?tab=sheet opens Register
- [auto] S050: after a pick, the picker hides and the node card shows; *Change* brings the picker back — `frontend/e2e/readings.spec.js`::S050: after a pick the search hides and the node card shows; Change brings the search back
- [auto] S050: the meter columns scroll sideways inside the table's frame, the page does not, and the time column stays in view (`@device`: phone-chromium and desktop-chromium at Normal) — `frontend/e2e/readings.spec.js`::S050: the meter columns scroll sideways inside the table's frame, not the page, and the time column stays in view
- [auto] `/readings` opens for every role; the storekeeper and IT admin see the picker's search field — `frontend/e2e/screens.spec.js`::every screen opens as storekeeper, ::every screen opens as it_admin (and the five other roles)
- [auto] the raise flow still picks equipment by search — `frontend/e2e/tickets-raise.spec.js`::S017: raise from the Tickets list naming a person with no login; the open ticket is listed first, ::S017: with no symptom and no description, the description is asked for, ::S026: Save with nothing chosen scrolls the raise form to the first message

On a real device: none (§ 8.5). No row added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/Plan.MD` — § 4.5: the "Decided (S050)" line turned into "Built (S050, 25-10-2026)": both tabs, who sees which, the register's behaviour and the route. § 6 *Screens*, the *Readings* line: every `equipment:read` role, the two tabs.
- `.claude/CLAUDE.md` — § SMTW-Review, the spec-to-step map: `readings` S039/S040/S050/S051 (`journeys` S047 was already there, from S047).
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `docs/Keycloak.md`: none, because no role, client or claim changed.
- `docs/steps/device-checks.md`: none, because the step has no real-device check.

## Fix rounds

### Round 1 (code review r1)

- **CR1-01 Fixed.** `EquipmentPicker` now stays mounted and is hidden with `v-show` while a node is picked, in `RaiseTicketView.vue` (a sibling before the ticket chain, `v-show="!ticket && !nodeId"`; the node branch became `v-else-if="nodeId"`) and in `ReadingsRegister.vue` (one picker in one wrapper, shown when no node is picked or the node was not found; the not-found alert sits in the same wrapper). *Change* brings back the search text and the matches. Tests: `tickets-raise.spec.js::S050: Change on the raise form brings back the earlier search text and its matches (CR1-01)` (new), and the register's *Change* test now asserts the picker is hidden after a pick and the text and match are back. Fails without the fix (picker back to `v-if`): `Expected: "E2E extruder"  Received: ""`; passes with it.
- **CR1-02 Fixed.** The failed page is kept (`failedPage`). A failure of page 1 keeps the alert at the top. A failure of page 2 or later shows the same words and *Try again* under the table, in the place of *Show more*; *Try again* asks for the failed page. Test: `readings.spec.js::S050: a failed Show more shows its message and Try again under the table, where Show more was (CR1-02)` (page 2 answered 503, the line is in view, *Show more* is gone, *Try again* then loads the 32 rows). Fails without the fix (bottom line removed): `toContainText ... "Readings could not be loaded. Try again in a minute."` not found; passes with it.
- **CR1-03 Fixed.** One `readingBadgeClass(label)` in `utils/meterLabels.js`, used by `ReadingHistoryModal.vue` and `ReadingsRegister.vue`; both local copies are gone. Unit test in `meterLabels.test.js` (Reset is info, High and Not OK are warning). A pure rename of a moved helper: no red run (the test cannot fail on the old code, which had no export).
- **CR1-04 Fixed.** *Open register* on the Meters card is no longer `btn-sm`; it has `touch-target` (the class *Log reading* uses on the same card). No test: size only.
- **CR1-05 Fixed.** `aria-controls` is set only while the chooser panel exists (`:aria-controls="chooserOpen ? 'register-chooser' : null"`).
- **CR1-06 Fixed.** `readings.spec.js::S050: a link to a machine that does not exist shows the not-found message with the search under it (CR1-06)` opens `node=999999999`, expects the message word for word and the search visible. It passed at once (it covers existing behaviour).

Decision: the pick of the register's two pickers (no node, not found) is now one instance. The not-found alert is inside the picker's wrapper, so a pick from there starts a new load as before.

Tests run: `YANTRA_TEST_RUN=s050c2 tooling/run-tests.bat`: backend 3054, frontend 175, deps 42, tooling 168, all passed; `npx vite build` built. Browser: targeted Normal run of `readings`, `tickets-raise`, `equipment`, `screens`: 111 passed, 1 skipped (S040's bottom-bar guard on desktop). No shared frontend code changed, so no whole-suite run.

Docs updated: none, because the fixes change no behaviour a doc describes.

### Round 2 (code review r2, async)

- **CR2-01 (nit) — Fixed** by the orchestrator, 25-10-2026: the comment `<!-- Step 2: saved; add photos -->` in `RaiseTicketView.vue` moved back above the `v-if="ticket"` block. Comment only; no run needed.
