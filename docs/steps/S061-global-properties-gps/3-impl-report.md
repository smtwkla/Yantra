Step: S061 — Properties for every class, and a GPS location
Doc: impl-report
Author: Coder (Opus)
Date: 27-10-2026

# S061 — Implementation report

S061 is built as the brief says, with no departure from the approved design. All three unit
suites pass, the targeted browser run passes, and the whole-suite browser run passes (counts in
§ Tests). The migration is **v34**. One small forced choice in the precondition is flagged under
§ Decisions taken (D-1): it lets a half-applied v34 run again.

## 1. What was built

- **A *Location* data type** (`geo`): a latitude and a longitude, 6 decimals each.
  - Masters › Properties offers it as "Location".
  - On *Edit this machine's values*, a Location input takes "11.016823, 76.955812" (a comma,
    spaces, or both between the numbers). The button **Use my current location** fills it from
    the browser's position, and a line under it gives the accuracy.
  - The card shows the value and an **Open in Maps** link (Google Maps).
- **Two flags on a property**, each a tick box in the Masters dialog and a badge in the table:
  - *Applies to every class* (`all_classes`): the property shows on every equipment, no link
    needed. Badge *Every class*.
  - *Value set on each machine* (`per_item_only`): left out of the model's dialog, refused on a
    model save, entered only per machine. Badge *Each machine*. Turning it on is refused (409)
    while any model has a value.
- **The seed "GPS location"** (Location, both flags), from migration v34.
- **Location only on top-level equipment**: component-units and components never show it, and an
  item save of it on a part is refused "This property is not on the class".
- **The hint on a machine that moves**: when a GPS location has a value and the Mobility in force
  is *Portable* or *Mobile*, the card shows "This machine moves. The location may be out of date."
  under the GPS row.
- **Masters › Equip Class › Properties** lists the every-class properties too, marked *Every
  class*, with no *Remove*. The *Add property…* picker leaves them out.
- **The card's model line and *Edit model values*** show only when the card has a row that is not
  per-machine (BR1-06), so a machine with only "GPS location" shows neither.

## 2. How it works

### The pure core (`properties_core.py`)

- `GEO` joins `DATA_TYPES`. `GEO_COLUMNS = ("value_lat", "value_lng")` sits beside
  `VALUE_COLUMNS`; `ALL_VALUE_COLUMNS` is the six value columns a change carries.
- `parse_value("geo", raw)` takes a string only. It matches two plain numbers (the rule of
  `_NUMBER_RE`), rounds each to 6 decimals (`ROUND_HALF_UP`), then checks −90..90 and −180..180.
  It returns `(lat, lng)` as Decimals. A JSON number, one number, three numbers or letters get
  "Enter the location as latitude, longitude, for example 11.016823, 76.955812".
- One reader of the stored value, `_stored_raw(data_type, row)`, gives a location's `(lat, lng)`
  or another type's one column. `stored_value`, `value_display` and `map_url` use it.
  `geo_text` writes "11.0168, 76.9558" (no trailing zeros, by `number_text`).
- `check_values(..., owner=)` now needs `OWNER_MODEL` or `OWNER_ITEM`. A model save of a
  `per_item_only` property is refused "Set this property on each machine, not on the model". A
  location fills both `value_lat` and `value_lng`.
- `_same_value` compares the two location columns as Decimals, as it does `value_number`, so a
  re-save of the same location writes no row and no history line.
- `property_changes(..., model_has_values=)` refuses turning `per_item_only` on while a model has
  a value: 409, field `per_item_only`. Turning it off is always allowed.
- The two flags are parsed as `active` is (true / false / 0 / 1); anything else gets "Choose yes
  or no". A shared `_flag(message)` parser now serves `active` too.
- `property_view` rows gain `data_type`, `per_item_only` and `map_url`.
- `on_level(properties, level)` drops a Location unless the level is `equipment`.
- `value_in_force(rows, name)` and `moving_hint(rows)` read property_view's rows by name
  (`casefold`). The names are constants: `MOBILITY`, `MOVING_LABELS`, `MOVING_HINT`.
- `item_events` writes "no value" without "(model)" for a per-machine property.

### The shell (`properties.py`, `item_properties.py`, `equipment.py`)

- `linked_properties(cur, class_id, level)` selects the active properties linked to the class
  **or** with `all_classes = 1`, then applies `on_level`. The card passes the node's level; the
  item dialog passes it too; the model dialog passes `equipment` and then drops the
  `per_item_only` rows.
- `lock_value_properties(cur, class_id, ids, level)` reads both flags from the property rows it
  locks FOR UPDATE at step (2). A property counts as `linked` when it is linked or every-class,
  and shown at that level. The model save passes level `equipment` and `OWNER_MODEL`; the item
  save passes the locked node's level and `OWNER_ITEM`.
- `update_property` keeps its two locking reads of the value tables, now kept apart, so the model
  table alone decides the `per_item_only` refusal.
- `_class_properties` (the class table, and the answers of *Add* and *Remove*) is one query: the
  properties with `all_classes = 1` or a link to the class, one row each, with `all_classes` as
  a boolean.
- `write_values` and `_VALUE_COLUMNS` carry `value_lat` and `value_lng`.
- The equipment detail gets `moving_hint` (text or null) beside `properties`.
- No new lock and no new order; one line was added to each LOCK ORDER note (§ 5.7).

### Migration v34 (`local_db.py`)

- `property_definitions`: one `ALTER TABLE` appends `geo` to the ENUM and adds `all_classes` and
  `per_item_only` (`IF NOT EXISTS`).
- `model_property_values` and `equipment_property_values`: one `ALTER TABLE` each adds
  `value_lat DECIMAL(8,6)` and `value_lng DECIMAL(9,6)`, and drops-if-exists, then adds the one-value
  CHECK (with `value_lat` as the fifth slot), the pair CHECK and the range CHECK.
- `INSERT IGNORE` seeds "GPS location", `created_by` `migration-v34`.
- `_PRECONDITIONS[34]` (`_v34_gps_name_check`): an absent `property_definitions` passes; a row
  named "GPS location" (any case, by the collation) that v34 did not seed refuses v34 with the
  brief's text.

### The frontend

- `propertyFormat.js`: "Location" in `DATA_TYPES`; three small helpers for the button,
  `positionText` (6 decimals), `accuracyText` (the 50 m rule) and `locationErrorText`.
- `PropertyInput.vue`: the Location input and **Use my current location**
  (`getCurrentPosition`, `enableHighAccuracy: true`, `timeout: 20000`, `maximumAge: 0`). The
  button shows only when `window.isSecureContext` and the Geolocation API exist. The accuracy line
  and the two error messages show under the input.
- `ItemPropertiesModal.vue`: no "Model: …" line on a per-machine row.
- `PropertiesPanel.vue`: two tick boxes (sent on create and edit), two badges; the 409 shows
  under *Value set on each machine*.
- `ClassPropertiesView.vue`: every-class rows get the *Every class* badge and no *Remove*.
- `AddPropertiesModal.vue`: every-class properties are left out of the picker.
- `EquipmentDetailView.vue`: *Open in Maps* under a Location value; the hint under the GPS row;
  no "· this machine" on a per-machine row; the model line and *Edit model values* only when the
  card has a row that is not per-machine.

## 3. Files touched

| File | Change |
|---|---|
| `backend/properties_core.py` | `GEO`, its parse, display and map link; the two flags; `owner` in `check_values`; `on_level`, `value_in_force`, `moving_hint`; `_same_value` and `item_events` for S061 |
| `backend/properties.py` | flags in the selects; every-class and level in `linked_properties`, `lock_value_properties`, `_class_properties`; model dialog and save without per-machine; the two new value columns |
| `backend/item_properties.py` | the node's level passed; dialog rows carry `per_item_only`; `OWNER_ITEM` |
| `backend/equipment.py` | the card gets the node's level and the field `moving_hint` |
| `backend/local_db.py` | migration v34 and `_PRECONDITIONS[34]` |
| `backend/tests/test_properties_core.py` | existing calls gain `owner`, whole-row compares gain the new keys; new Location, flag, hint and history tests |
| `backend/tests/test_properties_api.py` | `_made(rows)`; existing class-table tests filter the seed rows; new flag, per-machine and class-table tests |
| `backend/tests/test_item_properties_api.py` | `_made(rows)`; the four broken tests fixed; new every-class, Location and hint tests |
| `backend/tests/test_equipment_api.py` | `_made(rows)`; whole-row compares gain `data_type`, `per_item_only`, `map_url`; the "empty list" test now asserts the one seed row |
| `backend/tests/test_migration_v34.py` | new: fresh database, CHECKs, v33 rows kept, re-run, precondition |
| `backend/tests/conftest.py` | `_SEEDED_TABLES` holds a tuple of creators; `property_definitions` keeps `migration-v31` and `migration-v34` |
| `frontend/src/utils/propertyFormat.js` | "Location"; `positionText`, `accuracyText`, `locationErrorText` |
| `frontend/src/components/PropertyInput.vue` | the Location input and *Use my current location* |
| `frontend/src/views/equipment/ItemPropertiesModal.vue` | no model hint on a per-machine row |
| `frontend/src/views/masters/PropertiesPanel.vue` | two tick boxes, two badges |
| `frontend/src/views/masters/ClassPropertiesView.vue` | *Every class* badge, no *Remove* |
| `frontend/src/views/masters/AddPropertiesModal.vue` | every-class properties left out |
| `frontend/src/views/EquipmentDetailView.vue` | *Open in Maps*, the hint, the per-machine rules of the card |
| `frontend/tests/propertyFormat.test.js` | "Location" and the three helpers |
| `frontend/e2e/equipment.spec.js` | `dt` / `dd` lists gain "GPS location" / "—"; the hidden-card test moved to a component-unit; seven S061 tests |
| `frontend/e2e/masters.spec.js` | the class table shows the GPS row; row count 3; the card's lists; one S061 test |
| `docs/schema.md`, `docs/schema.html`, `docs/Plan.MD`, `docs/steps/device-checks.md`, `.claude/CLAUDE.md` | the docs pass (§ Docs updated) |

## 4. Decisions taken

- **D-1. The precondition lets v34's own seed row pass.** The brief says the check refuses v34
  "while a property named GPS location exists". Read literally, a half-applied v34 (the seed
  inserted, the version not yet recorded) would then refuse itself on the next start. The brief
  also asks for a re-runnable migration (§ 4, § 8.3 "a re-run changes nothing"). So the check
  counts only rows with `created_by <> 'migration-v34'`: a hand-made row still refuses (the
  purpose, D8). Flagged for the reviewer: a small reading of the brief, not a design change.
- **D-2. `owner` is a required keyword of `check_values`** (`owner=OWNER_MODEL` / `OWNER_ITEM`),
  so no caller can forget it. The constants live in `properties_core`.
- **D-3. `per_item_only` may be absent from a property dict** in the core (`prop.get`), and means
  "not per-machine". The shell always selects it; the existing core tests build properties
  without it, and they stay valid.
- **D-4. One `_flag(message)` parser** serves `active`, `all_classes` and `per_item_only`
  (instead of a near-copy of `_parse_active`).
- **D-5. `GEO_LEVEL = "equipment"` is a constant in `properties_core`**, not an import of
  `equipment_core.LEVELS[0]`: the core stays free of the equipment module, and the name says why.
- **D-6. The class table includes inactive every-class properties**, as it includes inactive
  linked ones (marked "(inactive)"). The brief's "a distinct union" does not say; this keeps one
  rule for the table.
- **D-7. The location helpers are pure functions in `propertyFormat.js`**, so the 6 decimals, the
  50 m rule and the two messages have unit tests. The component only calls the browser.
- **D-8. Screen text the brief did not give** (scope B):
  - help under *Applies to every class*: "Shows on every machine. No need to add it to each
    class.";
  - help under *Value set on each machine*: "Not on the model: each machine has its own, for
    example where it stands.";
  - the Location input's placeholder: "11.016823, 76.955812".
- **D-9. The hint and the map link sit inside the GPS row's `dd`** (under the value), so they
  read as part of that row.
- **D-10. Backend tests that make an every-class property turn the flag off afterwards** (a
  fixture's teardown), and the hint test renames its "Mobility" afterwards. The test databases are
  shared by every test of a worker; otherwise the property would show on every later card. The
  e2e tests do the same in a `finally`, since a lane's database is shared by its tests.

## 5. Not done, deferred or assumed

- **Not tested on MariaDB 11.8** (brief § 9 A1). The statements ran on the dev image 11.4 only.
  Running v34 on a throwaway `mariadb:11.8` container would pull an image from outside the repo;
  the orchestrator was to ask KLA before spawning the coder, and I received no go-ahead, so I did
  not do it. Assumption: `ADD COLUMN IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` and named CHECKs
  behave the same in 11.8.
- **Assumed:** Chromium in the browser tests answers a geolocation request without a granted
  permission with "denied" (the blocked-message test passes, so this holds for the logic device).
- **The *Use my current location* button on a real phone** is a device check (§ Manual checks).
- **The hint text is fixed English**, as every screen text today.

## Tests

- **Unit suites, final full run** (`YANTRA_TEST_RUN=s061c1 tooling/run-tests.bat`):
  - backend: PASSED, 3169 passed;
  - frontend: PASSED, 192 passed;
  - tooling: PASSED, 185 passed.
- **Build check** `npx vite build`: built (only the existing chunk-size warning).
- **New tests alone** (one lane, `phone-chromium`, `-g "S061"`): equipment.spec.js 7 passed;
  masters.spec.js 1 passed.
- **Targeted browser run** (Normal; `e2e/equipment.spec.js e2e/masters.spec.js
  e2e/screens.spec.js`: the screens and APIs this step changed, plus the screens spec the settings
  always add): 77 passed, 1 skipped.
- **Whole-suite browser run** (Normal, `tooling/run-e2e-tests.bat`, no flag, no spec file):
  229 tests over 6 lanes: **222 passed, 7 skipped, 0 failed** ("All lanes done in 158 s"). The
  skips are the existing ones (`test.skip` conditions of earlier steps); none is an S061 test.

## Manual checks

Automated (browser tests, from the passing runs above):

- [auto] An engineer opens *Edit this machine's values* on a top-level machine, taps *Use my current location*, saves; the card shows the numbers and *Open in Maps* with the Google URL, and the history shows the line. **important** — `frontend/e2e/equipment.spec.js`::"S061: engineer taps Use my current location; the card shows the location with Open in Maps, and the history the line"
- [auto] A pasted "11.0168234567, 76.9558123" saves as "11.016823, 76.955812" — `frontend/e2e/equipment.spec.js`::"S061: a pasted location with many decimals saves as 6 decimals"
- [auto] "95, 76" shows "The latitude must be between -90 and 90" under its input — `frontend/e2e/equipment.spec.js`::"S061: a latitude of 95 is refused under its input"
- [auto] The geolocation permission refused shows the blocked message under the input — `frontend/e2e/equipment.spec.js`::"S061: a blocked location permission shows the blocked message under the input"
- [auto] Masters › Properties: an engineer makes a Yes/No property with *Applies to every class*; it shows on a machine of a class without links, and in that class's table marked *Every class*, with no *Remove*; the picker does not list it. **important** — `frontend/e2e/masters.spec.js`::"S061: engineer makes a Yes / No property for every class; a machine of an unlinked class shows it, the class table marks it, the picker leaves it out"
- [auto] A per-machine property is absent from *Edit model values* — `frontend/e2e/equipment.spec.js`::"S061: a property set on each machine is not in Edit model values"
- [auto] A top-level machine whose card has only "GPS location" shows no "Values from model …" line and no *Edit model values* (BR1-06) — `frontend/e2e/equipment.spec.js`::"S061: a machine whose card has only GPS location shows no model line and no Edit model values"
- [auto] A machine with Mobility *Portable* and a GPS location shows the hint — `frontend/e2e/equipment.spec.js`::"S061: a Portable machine with a GPS location shows the hint under it"
- [auto] The changed test "S043: the card is hidden when the class has no property" now uses a component-unit of a class with no links — `frontend/e2e/equipment.spec.js`::"S043: the card is hidden when the class has no property"

On a real device (IT Admin, after the deploy; rows 41–43 of `docs/steps/device-checks.md`):

- [ ] **Important.** Android phone in Chrome, at a stockyard genset: *Use my current location*, allow the prompt; the accuracy line shows, and *Open in Maps* opens the Maps app at the genset.
- [ ] **Important.** The same on an iPhone in Safari, and as the installed app (PWA): the prompt shows, the position fills, and *Open in Maps* opens Maps.
- Inside a shed: the accuracy line shows "Rough location" when the phone reports above 50 m.

## Docs updated

- `docs/schema.md`: the `property_definitions` row (the `geo` type, the two flags, the seed,
  Location only on top-level equipment), the two value-table rows (`value_lat`, `value_lng`, the
  pair and range CHECKs, the fifth one-value slot), and the "migration v34" line. The Mermaid
  overview lists keyed columns only, so it does not change.
- `docs/schema.html`: the meta line (migration v34), and the Equipment tab: `all_classes` and
  `per_item_only` on `property_definitions`, `value_lat` and `value_lng` on both value tables.
- `docs/Plan.MD` § 4.1 *Equipment class*: "location" among the data types, and a "Built
  27-10-2026 (S061, v34)" sentence after the gate-A decision (kept as it was).
- `docs/steps/device-checks.md`: rows 41–43 from brief § 8.5.
- `.claude/CLAUDE.md` § SMTW-Review: S061 added to the spec-to-step map for `masters` and
  `equipment`.

## Shared docs

None: the work ran in the main working folder, not a worktree. The brief's status and its
`docs/steps/INDEX.md` row were set directly (`Implementing`, then `In code review`).

## Feedback

- hindrance: a Bash heredoc holding Python with `'''` strings failed twice with "unexpected EOF while looking for matching `'`"; I moved the text to scratch files (2 tool calls lost).
- waste: the first API test run used a test database whose session cleanup, still on the old `conftest.py`, had deleted the new seed row; the seed did not come back, because v34 was recorded as applied. I dropped the run's test databases by hand (1 extra run, about 2 min).
- idea: when a step adds seed rows, the brief could name the `_SEEDED_TABLES` change as the first edit, before any test run, so the test databases never lose the seed.
- rule: brief § 9 A1 left "ask KLA before spawning the coder" open, and the spawn prompt did not say whether the 11.8 check was allowed; I skipped it. One line in the spawn prompt would settle it.

## Fix rounds

### Round 1

All six findings of `4-code-review-r1.md` are fixed.

- **CR1-01 (minor) — Fixed.** `_parse_geo` (`backend/properties_core.py`) now checks the range on the unrounded `Decimal`s first and rounds after, so a number with more than 28 digits gets the latitude or longitude message, not `InvalidOperation` (a 500). Two inputs were added to `test_refusals` (`"1111111111111111111111111, 5"` and `"5, 1111111111111111111111111"`). Fails without the fix: `decimal.InvalidOperation` at `properties_core.py:333` (2 failed, 139 passed); passes with it.
- **CR1-02 (minor) — Fixed.** `btn-sm` removed from *Use my current location* (`PropertyInput.vue`).
- **CR1-03 (nit) — Fixed.** For a Location, the button, its error line and the accuracy line now come after the field's `error` line, so the server's refusal stays under the input.
- **CR1-04 (nit) — Fixed.** The text in `PropertiesPanel.vue` is now "Each machine gets its own value, for example where it stands. Models do not hold it."
- **CR1-05 (nit) — Fixed.** The button reads "Finding the location…" while the reading runs. The accuracy line shows only while the input still holds the text the reading put there (`locatedText`), so typing a value hides it. No new test: both are display details of the component; the two e2e flows that tap the button still pass. Red run not possible for these (no component test harness exists for `PropertyInput`).
- **CR1-06 (nit) — Fixed.** The empty line before the new columns removed from the three entity blocks in `docs/schema.html` (3 places).

### Tests (round 1)

- `YANTRA_TEST_RUN=s061c2 tooling/run-tests.bat`: backend PASSED 3171 passed; frontend PASSED 192 passed; tooling PASSED 185 passed.
- `npx vite build` in `frontend/`: built (only the existing chunk-size warning).
- Browser, targeted (`e2e/equipment.spec.js e2e/masters.spec.js e2e/screens.spec.js`): 77 passed, 1 skipped, 0 failed. No whole-suite run (fix round).

### Docs updated (round 1)

- `docs/schema.html`: the three blank lines removed (CR1-06). No other doc is due.

### Feedback (round 1)

- none
