```
Step: S050 — Meter reading register
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026 (revised 25-10-2026: brief-review r1, r2)
Track: full
Status: Done (committed b5783a8, 25-10-2026; checks: auto; no device checks)
Baseline: refs/steps/S051 2dbd791 (staleness review s1, 25-10-2026, against S047 and S051)
```

# S050 — Meter reading register

**The need (KLA, 25-10-2026).** "We need a 'meter reading register' — to view all the
readings of an equipment / component-unit / component. Format: rows represent a time of
reading, cols for various meters (one col / selected cols / all cols). Rev chrono order. May
be as a tab in readings module."

Today a reading can be seen only one meter at a time, in the *History* dialog of the
equipment page's *Meters* card (S039 § 1.3, `ReadingHistoryModal.vue`). A press with strokes,
run hours, kWh and oil temperature needs four dialogs to see one evening's round. The register
shows them side by side, like the paper log book at the machine.

User answers (25-10-2026, before the draft):
- U1: a *Register* tab on the *Readings* page, and a button on the equipment page's *Meters*
  card that opens it for that node. Anyone who can see the equipment (`equipment:read`) opens
  it; the *Readings* nav item shows for them too, with only the *Register* tab for the
  storekeeper and IT admin.
- U2: the columns are the meters of the picked node only. A motor's run hours are seen by
  picking the motor (a component-unit).
- U3: a row is one exact minute (`taken_at`). The sheet is not changed: a round that crosses
  a minute boundary while it saves shows as two rows.

Built on 4d89084 (S044) plus S046, S047 (browser test levels and tags, gate B, snapshot
refs/steps/S047) and S051 (gate B, refs/steps/S051). S051 changed the shared time field and
also keyed it per opening in `ReadingsView.vue` (`rounds`, raised in `enterMore()`, `:key`) and
`RaiseTicketView.vue` (`restoreFieldKey`, raised in `resetForm()`, `:key`), and added six
`S051:` tests to `readings.spec.js`, two of which drive the sheet through `/readings` and its
*Now* box (BS1-03). No S050 design change follows: the sheet moved to `ReadingsSheet.vue`
carries `rounds` and `enterMore()` with it; the picker extraction leaves `restoreFieldKey` in
`RaiseTicketView.vue`; the S051 tests must stay green (*Sheet* stays the default tab, and the
*Register* tab has no *Now* box) (§ 9 items 6–7). **No migration, no new permission key, no write.**

## 1. What will be built

1. **The *Readings* page gets two tabs: *Sheet* and *Register*.** *Sheet* is S040's end-of-day
   sheet, unchanged. *Register* is new. The tab lives in the URL query (`?tab=register`), as
   on *Me* (S031), so Back returns to it.
   - A `reading:log` holder sees both tabs; *Sheet* is the default.
   - A user with `equipment:read` and no `reading:log` (the storekeeper, IT admin) sees only
     *Register*, and the tab bar is not shown. A `?tab=sheet` typed by such a user opens
     *Register*, so the sheet never mounts for them (BR1-11).
   - **Typed readings survive a tab switch** (BR1-01). The rule: **each tab mounts the first
     time it shows, and then stays mounted** (`<KeepAlive>` around the tab components, or a
     `v-if` seen-flag plus `v-show`; the coder states which; BR2-01). A supervisor who types a
     round, opens *Register* to compare with yesterday and comes back finds the typed values
     still there. A user who arrives at `?tab=register&node=` from the card never mounts the
     sheet, so no `GET /api/readings/sheet` runs for them.
2. **The *Readings* nav item** shows for every `equipment:read` holder (today: `reading:log`).
   Its place is unchanged: after *Tickets*. The landing page is unchanged, because *Me* and
   *Equipment* come first (S035).
3. **Picking a node on the *Register* tab** (BR1-04). The equipment search of *Raise ticket*
   (`RaiseTicketView.vue`, lines 139–168 and 344–371; BS1-04) moves to a shared component,
   `EquipmentPicker.vue`, used by both screens with the same behaviour and wording: the label
   *Which equipment?* with a fixed input id, owned by the picker (the raise tests find it by
   that label, `tickets-raise.spec.js` lines 58, 80, 90; BR2-03), a search field (placeholder
   "Code or name"), debounced (`useDebounced`), up to 20 matches at any
   level from `GET /api/equipment?level=all&q=&per_page=20` (the user's units only), each row
   "code — name" with its `full_path` under it, "Searching…", "No equipment found at your
   units.", and "More found — type more of the code or name." when the API's `total` is
   larger. It emits the picked id; each screen decides what a pick does. On the register a
   pick sets the URL to `?tab=register&node=<id>`. While `node=` is in the URL the picker is
   hidden and, as on the raise screen after a pick, a node card shows instead: "code — name",
   its `full_path`, *Change* (back to the picker, `node` dropped from the URL) and *Open
   equipment page* (BR2-02).
4. **The *Open register* button** (BR1-08) on the *Meters* card (`MetersCard.vue`) opens
   `/readings?tab=register&node=<id>`. It shows when the node has at least one meter in force,
   for everyone who sees the card. A node whose meters were all removed shows no button (the
   card reads "No meters."); its old readings are reached by the *Register* tab's search
   (BR1-15).
5. **The register table.**
   - **Rows:** one row per minute at which at least one shown meter has an active reading,
     **newest first**. The first column is the time ("23-10-2026 18:00", the app's date-time
     format).
   - **Columns:** one per meter, headed with the meter's name and unit ("Run hours (h)"); a
     meter type with no unit (a Yes / No check) is headed with its name alone, no brackets
     (BR2-06).
     Order: the node's meters in force, in the order of the *Meters* card; then meters that
     are **no longer on this node** but have active readings, with a small grey line under
     the header: "No longer on this machine" (BR1-09).
   - **Cell:** the number only, Indian grouping, the unit left to the header (BR1-10:
     `formatReading(value, meterType, { unit: false })`, a new option with a unit test); a Yes /
     No cell reads *Yes* / *No*. Beside it the marks *High*, *Low*, *Not OK* and *Reset*
     (`readingBadges`). An empty cell when that meter has no reading at that minute.
   - **Removed readings** (S039 § 1.4) are not shown. The per-meter *History* keeps *Show
     removed* for `equipment:edit` holders.
   - **Paging:** 30 rows at a time, then *Show more*, as in the *History* dialog.
   - **On a phone:** the time column stays fixed on the left; the meter columns scroll
     sideways inside the table's frame, never the page.
6. **Choosing the columns.** Above the table, *Meters: All* opens a list of check boxes, one
   per meter, and *Show all*. One, several or all meters may be ticked; at least one stays
   ticked (the last tick cannot be cleared). The choice is in the URL (`&meters=3,7`; absent
   = all), so a link or Back keeps it. Rows are counted over the ticked meters only: a minute
   with readings only of unticked meters is not a row. An id in the URL that is no longer a
   column (a stale bookmark) is ignored by the server; the screen ticks what the answer's
   `shown` lists (BR1-03).
7. **Empty states** (scope B):
   - no node picked: "Find a machine or part to see its readings.";
   - the node has no meter and no reading: "This machine has no meters. Engineers add meters
     in Masters › Models or on the machine's page.";
   - meters but no reading of the ticked ones: "No readings yet.";
   - the node is not found or outside the user's units (404), or the key is not held at its
     site (403; cannot happen for a site role today, as `equipment:read` is `("*",)`): "This
     machine was not found, or you have no access to it. Find another machine." (BR1-12);
   - a load failure: "Readings could not be loaded. Try again in a minute." with *Try again*.

### Out of scope

- Who logged each reading and its note: they stay in the per-meter *History* (§ 9 item 1).
- A date range filter, totals per period, charts or trends, export to Excel / CSV, printing.
- Readings of a node's parts as extra columns (U2).
- Grouping readings of nearby minutes into one row, or changing the sheet's time (U3).
- Removing a reading from the register (it stays in *History* and on the sheet's *Undo*).
- Scrapped nodes in the search (the equipment list leaves them out by default); a scrapped
  node opened by its link still shows its register (read-only like everything about it).

## 2. Standards and practice

- **TPM, autonomous maintenance (pillar 1):** operators keep a log of the checks and
  readings at their machine, and the log is read to spot drift before it becomes a
  breakdown. The register is that log book on screen: one row per round, all meters side by
  side, newest first, so a rising temperature or a slowing counter shows at a glance.
- **ISO 17359 (condition monitoring and diagnostics of machines — general guidelines):** set
  the measuring points, take readings at set intervals, record each with its time, compare it
  with earlier values and with alert limits (trending), and act on a change. The register is
  the "compare with earlier values" step on screen: each meter's values in time order, next
  to its limit marks.
- **EN 13306:2017, the definition of *condition monitoring*:** a maintenance activity that
  measures an item's parameters at set intervals, by hand or automatically. A meter reading
  is such a measurement; the register is a read view of them and adds no rule.
- **ISO 55001 § 7.5 (information requirements):** the organisation decides which asset
  information it needs, and keeps it of a quality and in a form that the people who decide on
  the asset can use. The register gives every role that may see the equipment the same view,
  including the storekeeper (spares by run hours) and IT admin. (ISO 55000 is the overview;
  ISO 55001 holds the requirement, BR1-06.)
- **Departure:** none. No KPI is computed (SMRP metrics wait for the reports phase).

## 3. Where

### Backend

- `backend/meters_core.py` — three new pure functions:
  - `register_columns(meters_in_force, read_types)`: the columns in force, then the
    removed-from-node ones (§ 5.1);
  - `register_rows(readings, columns)`: plain reading rows in, rows out
    (`[{taken_at, cells: {meter_type_id: cell}}]`), newest first; the columns give each
    meter's kind, and the core words the value with `answer_word` / `format_number`, already
    in `meters_core` (BR1-02);
  - `parse_meter_type_ids(raw) -> (ids, errors)`, next to `parse_meter_type_id` and in its
    return shape; `ids` is `None` for "all" (absent or empty) (BR1-05, BR2-05, § 5.5).
- `backend/meters.py` — new route `GET /api/equipment/<id>/readings/register` (§ 6), key
  `equipment:read`, access through `load_node_for_user(..., for_update=False,
  key="equipment:read")` as `list_readings` does. Reuses `_meters_of`, `_marks`, `int_arg`,
  `MAX_PAGE`, `MAX_PER_PAGE` and `HISTORY_PER_PAGE`.

### Frontend

- `frontend/src/views/ReadingsView.vue` — becomes the tab shell: the tab bar, the default
  tab by permission, the tab in the URL query (the `MeView.vue` pattern), the sheet kept
  mounted across a tab switch (§ 1.1, BR1-01).
- `frontend/src/views/readings/ReadingsSheet.vue` — new file: the S040 sheet moved out of
  `ReadingsView.vue` **unchanged** (script, template and styles) except its import paths,
  one folder deeper (`../../api`, `./ReadingSheetRow.vue`, …; BR2-04). Its comment header
  moves with it.
- `frontend/src/views/readings/ReadingsRegister.vue` — new: the picker, the node heading,
  the column chooser, the table, *Show more*, the empty states.
- `frontend/src/components/EquipmentPicker.vue` — new: the search moved out of
  `RaiseTicketView.vue` (§ 1.3, BR1-04). `EquipmentMoveModal.vue` keeps its own per-level
  searches (a different rule).
- `frontend/src/views/RaiseTicketView.vue` — uses `EquipmentPicker.vue`; behaviour and
  wording unchanged.
- `frontend/src/stores/navigation.js` — the *Readings* item: `perm: "equipment:read"`.
- `frontend/src/views/equipment/MetersCard.vue` — the *Open register* button in the card
  header.
- `frontend/src/utils/meterLabels.js` — `formatReading` gains the option `{ unit: false }`
  (BR1-10); reuse `readingBadges`; add `registerQuery` / `parseRegisterQuery` (pure: the
  URL's `node`, `meters` ↔ values; bad values dropped) only if the coder needs them outside
  the component (§ 9 item 4).

### Tests

- `backend/tests/test_meters_core.py` — `register_rows`, `register_columns`,
  `parse_meter_type_ids` (§ 8.1).
- `backend/tests/test_readings_api.py` — the new route (§ 8.2).
- `backend/tests/test_rbac.py` / `test_role_matrix` — no change: no new key, and the file
  holds no route-to-key list (grep for "route" finds none, 25-10-2026).
- `frontend/tests/navigation.test.js` — the test "Readings follows Tickets for the reading
  roles; the storekeeper and IT admin do not see it (S040)" (line 41) changes: every role with
  `equipment:read` sees *Readings*; `canOpenRoute("readings", …)` is true for them. The
  expected nav lists of IT admin (line 38, `visible(IT_ADMIN)`) and the storekeeper (line 54,
  `visible(STOREKEEPER)` → `["equipment", "readings", "masters"]`) gain `"readings"`
  (BR1-13). Lines 63 and 84 (the storekeeper lands on *Equipment*) stay true, because
  *Equipment* comes before *Readings*.
- `frontend/tests/meterLabels.test.js` — `formatReading(…, { unit: false })`; the query
  helpers, if added (§ 9 item 4).
- `frontend/e2e/tickets-raise.spec.js` — unchanged; its tests that pick equipment by search
  check that the raise flow still works with `EquipmentPicker.vue` (run as targeted specs).
- `frontend/e2e/readings.spec.js` — new `S050:` tests (§ 8.4). The S040 tests open
  `/readings` and must still land on the sheet for `reading:log` holders (no change
  expected).
- `frontend/e2e/screens.spec.js` — the `/readings` row: `who` becomes `EVERYONE`; the
  storekeeper and IT admin see the picker's search field; the S040 bottom-bar test is
  unchanged (the manager already has six items). `READING_ROLES` is then unused: remove it
  (BR2-10).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` — § 4.5: a "Built (S050)" line; § 6 *Screens*, the *Readings* line (line
  799, "for roles with `reading:log`"; BS1-05). § 4.5 already has a "Decided (S050)" line: turn
  it into "Built (S050)" rather than adding a second line: both tabs and who sees which (BR1-14).
- `.claude/CLAUDE.md` — § SMTW-Review, the spec-to-step map: `readings` S039/S040/S050/S051 (BS1-08), and `journeys` S047.
- No schema doc change (no migration). `docs/Keycloak.md`: no change (no role or key).

## 4. Data model

No migration. The route reads `meter_readings` (v32) through its index
`ix_meter_readings_meter_time (equipment_id, meter_type_id, taken_at)`, and `node_meters`,
`model_meters`, `meter_types` as `_meters_of` does.

## 5. Rules

### 5.1 The columns (pure, `register_columns`)

1. In force: the node's meters from `_meters_of(cur, node_id, model_id)` (model meters plus
   own, S038), in that order.
2. Removed from the node: every meter type with at least one **active** reading on this node
   that is not in force, ordered by name. Each gets `in_force: false`.
3. A meter type in neither list is not a column.

### 5.2 The rows (pure, `register_rows`)

1. Input: the active readings (`removed_at IS NULL`) of this node for the shown meter types,
   at the page's minutes (§ 5.3), and the columns.
2. One row per distinct `taken_at`, newest first. Each row's `cells` maps
   `meter_type_id` → `{id, value, limit_state, is_reset}`, `is_reset` a boolean (BR2-07). The
   column of the reading's meter
   gives its kind: a Yes / No value is worded with `answer_word` ("yes" / "no"), any other
   with `format_number`, as `reading_out` does (BR1-02).
3. Two active readings of one meter at one minute cannot exist (S039: refused, `SAME_MINUTE`),
   so a cell holds at most one reading. If the data ever holds two, the one with the higher
   `id` wins and the core says so in a comment (no error to the user).

### 5.3 Paging (the shell)

1. `total` = the number of distinct `taken_at` of active readings of the shown meters on
   this node.
2. The page's minutes: `SELECT DISTINCT taken_at … ORDER BY taken_at DESC LIMIT %s OFFSET %s`.
3. The readings at those minutes: one query with `taken_at IN (…)`.
4. A fixed handful of queries (the columns through `_meters_of`, the removed-from-node types,
   the count, the minutes, the readings), none per meter or per row (BR1-16).
5. A reading logged between two pages shifts the minutes by one: the screen drops a row whose
   time it already shows (as `ReadingHistoryModal.vue` does with ids).

### 5.4 Access

1. Key `equipment:read`, which is in `SITE_SCOPED`: `load_node_for_user` gives 404 for a
   node outside the user's units and checks the key at the node's site (403), as
   `list_readings` does.
2. No removed reading, no `created_by`, no note in the answer: nothing beyond what the
   *Meters* card and the history show to the same user.
3. A request without identity gets 401 / no access as every route (`require_perm`).

### 5.5 Inputs

- `meter_type_ids`: optional, a comma list of positive integers, parsed by
  `meters_core.parse_meter_type_ids` (BR1-05). Absent or empty = all columns. Spaces around
  an id are trimmed (" 3 , 7 " = 3, 7). A malformed list ("3,x", "3,", "0", "-1") → 400
  "Pick a meter" on field `meter_type_ids` (`PICK_A_METER`): an API caller's error.
  Duplicates are ignored. An id that is not a column of this node is **ignored** (a stale
  bookmark, BR1-03); when none is left, all columns are shown. The answer's `shown` lists the
  ids used.
- `page`, `per_page`: `int_arg` with `MAX_PAGE`, `MAX_PER_PAGE`; default `per_page` is
  `HISTORY_PER_PAGE` (30).

### 5.6 The database down

The route uses `get_db()`, so an unreachable DB answers 503 like every read
(`DBUnavailable`). The screen shows the load-failure message with *Try again*.

## 6. API

`GET /api/equipment/<id>/readings/register?meter_type_ids=3,7&page=1&per_page=30`
(`equipment:read`)

```json
{
  "node": {"id": 12, "code": "MCC2-PR-04", "name": "Press 4", "level": "equipment"},
  "columns": [
    {"meter_type": {"id": 3, "name": "Run hours", "unit": "h", "kind": "counter", "decimals": 1},
     "in_force": true, "min_value": null, "max_value": null},
    {"meter_type": {"id": 9, "name": "Oil temperature", "unit": "°C", "kind": "gauge", "decimals": 0},
     "in_force": false, "min_value": null, "max_value": null}
  ],
  "shown": [3, 9],
  "rows": [
    {"taken_at": "2026-10-23 18:00:00",
     "cells": {"3": {"id": 812, "value": "12345.6", "limit_state": null, "is_reset": false}}}
  ],
  "total": 214, "page": 1, "per_page": 30
}
```

- `columns` lists every column of the node (§ 5.1), whatever is shown, so the chooser can
  offer them all. `shown` is the set the rows were built for, after stale ids are dropped
  (§ 5.5); the screen ticks exactly these.
- Times are sent in the API's usual date-time format (the coder uses `row_to_dict` as
  `reading_out` does; the JSON sample's format is illustrative).
- Errors: 400 `meter_type_ids` malformed (§ 5.5), 404 (§ 5.4), 403 (key not held at the
  node's site), 503 (§ 5.6).

## 7. Design decisions

1. **One register endpoint, not N calls to the history route.** The pivot (rows by minute)
   is business shaping, so it lives in the backend's pure core (CLAUDE-COMMON: backend heavy,
   pure core). Rejected: the screen calls `GET …/readings?meter_type_id=` once per meter and
   merges — paging by minute across meters cannot be done that way, and it is N requests.
2. **A row is an exact minute** (U3). Rejected: a time window (a row's time would be
   approximate), and sending one time for the whole sheet round (a change to S040 the user
   declined).
3. **Columns include meters no longer on the node** (§ 5.1.2). Their readings are part of the
   machine's record (ISO 55001 § 7.5). Rejected: in-force meters only — readings of a removed
   meter would vanish from every view but the database. The card's *Open register* button
   still follows the meters in force (a node with none shows no button); the tab's search
   reaches such a node (BR1-15).
4. **Tabs on the existing page, not a new nav item** (U1). Six nav items already fill a
   phone's bottom bar (S040 test). The sheet moves to its own component unchanged, so the
   shell stays small, and it stays mounted across a tab switch so typed readings are never
   lost (BR1-01). Rejected: a seventh nav item; a register only on the equipment page; a
   "Discard typed readings?" question on a tab switch (more code, one more question).
5. **The *Readings* nav item opens to every `equipment:read` holder** (U1). This changes S040
   decision "the storekeeper and IT admin do not see it": they see the page with only the
   *Register* tab. It is a read of what they already see on the equipment page, so no new
   data reaches them.
6. **Removed readings are not in the register.** It is the record as it stands; a correction
   is audited in the per-meter *History* (*Show removed*). Rejected: a *Show removed* toggle
   here too — a removed and an active reading can share a minute and a cell.
7. **The choice of columns and the node live in the URL**, as the Me tabs and the ticket
   filters do. A link from the *Meters* card, a bookmark and Back all work. Rejected: browser
   storage.
8. **The search is the raise screen's, moved to `EquipmentPicker.vue`** and used by both
   screens (BR1-04: DRY, and one wording for one control). Rejected: a third copy of the
   search in the register; a site → unit → machine → part chain of pickers (four taps for the
   common case; the QR label and the card's button already cover "this machine").

## 8. Tests and acceptance

### 8.1 Core (`test_meters_core.py`)

- `register_rows`: readings of three meters at three minutes → three rows, newest first;
  a minute with only one meter gives one filled cell; a Yes / No value comes back as words
  (its column says the kind); an empty input → `[]`; two readings of one meter at one minute
  → the higher id (§ 5.2.3).
- `register_columns`: in force only; in force plus a removed-from-node type with readings
  (after, by name, `in_force: false`); a type with only removed readings is not a column.
- `parse_meter_type_ids`: absent and empty → all; "3,7"; "3,3" → [3]; " 3 , 7 " → [3, 7];
  "3,x", "3,", "0", "-1" → the error.

### 8.2 API (`test_readings_api.py`)

- Happy path: rows newest first, cells per meter, `total` counts minutes not readings,
  `page` 2 gives the next minutes.
- `meter_type_ids=3`: only minutes where meter 3 has a reading; `columns` still lists all.
- Removed readings are not in rows or `total`; a meter whose only readings are removed is
  not a column.
- A meter removed from the node (own meter set inactive, S038) with readings: a column with
  `in_force: false`.
- 400 on `meter_type_ids=x`, `0`, `-1`; an id that is not a column is ignored and left out
  of `shown`; only such ids → all columns.
- 404 for a node outside the user's units and for an unknown id; the storekeeper and IT admin
  get 200 at their units.
- A node with no meters and no readings: `columns: []`, `rows: []`, `total: 0`.
- `db_down` fixture: 503.

### 8.3 Frontend unit (`navigation.test.js`, `meterLabels.test.js`)

- Every role with `equipment:read` sees *Readings* after *Tickets*; the storekeeper's and IT
  admin's lists gain it; `canOpenRoute("readings", …)` true for them.
- `formatReading(value, type, { unit: false })` gives the number without the unit.
- The query helpers, if added: a bad `meters` value is dropped; absent = all.

### 8.4 Automated (e2e, `frontend/e2e/readings.spec.js`, targeted; set-up by API)

- **important** — S050: an engineer opens *Open register* from a press's *Meters* card and
  sees one row per reading time, newest first, one column per meter, with *High* on an
  over-limit gauge.
- **important** — S050: unticking all but one meter in *Meters* leaves only that column and
  only the times that meter was read; the URL keeps it after a reload.
- **important** — S050: a supervisor types a value on the sheet, opens *Register*, comes back
  to *Sheet*, and the typed value is still there (BR1-01).
- S050: the picker finds a component-unit by code (its row shows the `full_path`) and the
  register shows its own meters.
- S050: a link with a stale `meters=` id opens the register with the remaining columns, no
  error shown.
- S050: *Show more* adds the next 30 rows with no row twice.
- **important** — S050: the storekeeper sees *Readings* in the nav, only the *Register* tab
  (no *Sheet*), and can open a machine's register; `/readings?tab=sheet` opens *Register*
  for them (BR1-11, BR2-08).
- S050: after a pick, the picker hides and the node card shows; *Change* brings the picker
  back (BR2-02).
- S050: the meter columns scroll sideways inside the table's frame, the page does not, and
  the time column stays in view. A layout test: tagged `@device` (S047 § 1.3), so at Normal it
  runs on `phone-chromium` and on `desktop-chromium` (1366 px). Its set-up gives the node enough
  meters that the frame overflows at 1366 px too; it asserts the frame's `scrollWidth >
  clientWidth`, the page's `scrollWidth` ≤ its width, and the time column in view (BS1-02).
- The other S050 tests are untagged logic tests. The storekeeper nav test finds *Readings* by
  role in whichever nav is visible (bottom bar or side bar), so it stays a logic test.
  `screens.spec.js` already carries `@smoke` and `@device` (BS1-02).
- `screens.spec.js`: `/readings` opens for every role; the storekeeper and IT admin see the
  picker's search field.
- `tickets-raise.spec.js` (targeted, unchanged): the raise flow still picks equipment by
  search.

### 8.5 On a real device

None (BR1-07). The sideways-scroll test of § 8.4 runs on `phone-webkit` in the release's Full
run (`tooling/release-tests.bat`, S047), which is the iPhone check (BS1-01).

### 8.6 Acceptance

All suites green (`tooling/run-tests.bat`). Browser runs at the levels of S047 (BS1-01): the
targeted specs at Normal (`readings.spec.js`, `screens.spec.js`, `tickets-raise.spec.js`,
`journeys.spec.js` — journey 3 opens `/readings`, BS1-07) as often as needed; the whole suite
at Normal once when the coding is done (`tooling/run-e2e-tests.bat`, no flag and no
`--project`: an explicit `--project` turns the `@device` filter off); never `--level=full`.

## 9. Open questions and assumptions

1. **Who and note per row.** Proposed: not in the register (§ 1 Out of scope); the cell's
   meter *History* shows them. Alternative: a last column *By* with the distinct names of
   the row's readings (a row may have several). Assumption until answered: not shown.
2. **Tapping a cell.** Proposed: nothing in this step. Alternative: a tap opens that meter's
   *History* dialog at that reading (needs the dialog to accept a start point).
3. **Search result limit.** 20 matches and the raise screen's "More found" line (§ 1.3);
   settled by BR1-04.
4. **Pure URL helpers.** If the component parses `node` / `meters` from the query in more
   than a line or two, the parsing goes to `meterLabels.js` with unit tests; otherwise it
   stays in the component. The coder states which.
5. **Default tab for a `reading:log` holder** opening `/readings`: *Sheet* (as today). The
   *Open register* button and the tab's link always carry `?tab=register`.
6. **S047** — settled (BS1-06): coded first; the new S050 tests follow its tags (§ 8.4).
7. **S051** — settled (BS1-06): coded first (see the intro for what it changed). It changed
   `EventFields.vue`, `RaiseTicketView.vue`, `tickets-raise.spec.js` and the S040 e2e tests that clicked *Change*.
   S050 moves the sheet's code but does not change it, edits `RaiseTicketView.vue` (the
   picker) and adds tests to `readings.spec.js`: the two steps are coded one after the other,
   never in parallel (BR2-09).

## 10. Amendments

None.

## Review log

### U1–U3 — before the draft, 25-10-2026

Recorded in the header section above: tab + link for every `equipment:read` holder; the
node's own meters only; one row per exact minute, the sheet unchanged.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major — typed readings lost on a tab switch | Accepted (a): the sheet stays mounted (`v-show` or `<KeepAlive>`); § 1.1, § 3, decision 4; important e2e test in § 8.4. |
| BR1-02 minor — the core cannot word a Yes / No cell | Accepted (a): `register_rows(readings, columns)`, worded with `answer_word` / `format_number`; § 3, § 5.2, § 8.1. |
| BR1-03 minor — a stale `meters=` gives a 400 | Accepted (a): ids that are not a column are ignored, `shown` is returned and ticked; 400 only for a malformed list; § 1.6, § 5.5, § 6, § 8.2, § 8.4. |
| BR1-04 minor — a third equipment search | Accepted (a): `EquipmentPicker.vue` extracted from `RaiseTicketView.vue`, its wording and `full_path` kept; § 1.3, § 3, decision 8, § 8.4. |
| BR1-05 minor — where the id list is parsed | Accepted (a): `meters_core.parse_meter_type_ids` with core tests; § 3, § 5.5, § 8.1. |
| BR1-06 minor — "to verify" placeholders, ISO 55000 | Accepted (a): standards cited by name and year without guessed clauses; ISO 55001 § 7.5; § 2, decision 3. |
| BR1-07 minor — a device check a browser runs | Accepted (a): dropped; § 8.5. |
| BR1-08…BR1-17 nits | All accepted: *Open register* (08); "No longer on this machine" under the header (09); number only in cells, `formatReading` option `{ unit: false }` (10); `?tab=sheet` without `reading:log` opens *Register* (11); 403 shown with the 404 text (12); `navigation.test.js` lines 38 and 54 named, 63 and 84 stay true (13); Plan.MD § 6 line 797 added (14); a node with no meter in force has no button, its readings reached by the search (15); query-count wording (16); one result-count wording (17). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor — `v-show` mounts the sheet for a register-only visit | Accepted: each tab mounts the first time it shows, then stays mounted; § 1.1. |
| BR2-02 minor — the picker stays above the table after a pick | Accepted: the raise screen's node card (code — name, `full_path`, *Change*, *Open equipment page*), picker hidden while `node=` is set; § 1.3, § 8.4. |
| BR2-03 minor — the picker's label not named | Accepted: the picker owns *Which equipment?* and a fixed input id; line range 341–368; § 1.3. |
| BR2-04…BR2-10 nits | All accepted: import paths change in `ReadingsSheet.vue` (04); `parse_meter_type_ids` returns `(ids, errors)`, `None` for all (05); no brackets for a type with no unit (06); `is_reset` a boolean (07); `?tab=sheet` storekeeper e2e check (08); § 9.7 names `RaiseTicketView.vue` and `tickets-raise.spec.js` (09); `READING_ROLES` removed (10). |

### U4 — approval, 25-10-2026

KLA approved the brief as it stands after round 2. Open questions as proposed: who logged
each reading is not shown (item 1); a tap on a cell does nothing in this step (item 2); items
3–7 as written.

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BS1-01 minor — the run instruction after S047 | Accepted: targeted Normal, the whole suite at Normal once with no `--project`, never Full; the iPhone check is the release's Full run (§ 8.5, § 8.6) |
| BS1-02 minor — the sideways-scroll test is `@device` | Accepted, as recommended: tagged, no device in the title, enough meters to overflow at 1366 px, frame `scrollWidth > clientWidth`; the other tests untagged; the storekeeper nav test finds *Readings* in the visible nav (§ 8.4) |
| BS1-03 minor — S051 changed more than the time field | Accepted: the intro names the keys and the S051 tests; no design change (intro) |
| BS1-04…BS1-08 nits | Accepted, all: template lines 344–371 (§ 1.3); Plan.MD line 799 and the existing "Decided (S050)" line (§ 3 Docs); § 9 items 6–7 settled; `journeys.spec.js` targeted (§ 8.6); the spec map `readings` S039/S040/S050/S051 (§ 3 Docs) |

### U5 — gate B question, 25-10-2026

The meter chooser reads "Meters: 1 of 2" when only some meters are ticked (the coder's wording; the brief named only "Meters: All"). KLA: keep "Meters: 1 of 2".
