Step: S061 — Properties for every class, and a GPS location
Doc: brief
Author: Orchestrator (Opus)
Date: 27-10-2026 (revised 27-10-2026: brief-review r1)
Track: full
Status: Committed fb6a025 (adopted 27-10-2026); checks left: device-checks rows 41–43 for IT Admin (approved 27-10-2026 by KLA: Q1 a, Q2 a, Q3 as proposed; A1 answered: production runs MariaDB 11.8.8; A2 confirmed)
Baseline: d6431f1

# S061 — Properties for every class, and a GPS location

The design was agreed with KLA in the session of 27-10-2026, before this brief:

- a property data type for a map position;
- a property "GPS location" of that type;
- a flag that keeps a property's value on each machine, never on the model;
- a flag that puts a property on every class.

KLA has already made **Mobility** on production by hand: a choice with Fixed, Mobile and
Portable. This step does not seed it. After the release, KLA ticks *Applies to every class* on it.

## 1. What will be built

1. **A new data type, *Location*** (`geo`): a latitude and a longitude, 6 decimals each (about
   10 cm), entered as "11.016823, 76.955812". The display drops trailing zeros: "11.0168,
   76.9558" (BR1-11).
   - **Entry.** The input has a button *Use my current location*. It reads the browser's
     position (Geolocation API) and fills the field. The user can also type or paste the
     numbers, e.g. from Google Maps.
   - **Display.** On the equipment page the value reads "11.016823, 76.955812", with a link
     *Open in Maps* that opens Google Maps at that point (a phone opens the Maps app).
2. **A flag *Applies to every class*** (`all_classes`) on a property. A property with the flag
   shows on every equipment, and needs no link to its class. Values stay where they are (models,
   items) when the flag is turned off; the property is then shown again only on the classes
   linked to it.
3. **A flag *Value set on each machine*** (`per_item_only`) on a property. Such a property is
   left out of the model's dialog (*Edit model values*), and a model's save of it is refused. It is
   entered only in *Edit this machine's values*, on the equipment page. It suits installation
   data, which differ per machine (where it stands), as opposed to design data from the maker.
4. **The seed property "GPS location"**: type Location, *Applies to every class*, *Value set on
   each machine*.
5. **Location only on top-level equipment.** A Location property shows only on nodes of level
   *equipment*, not on component-units or components. A part is where its machine is (§ 7 D5;
   open question Q2).
6. **A hint on portable and mobile machines** (§ 7 D7; open question Q1). When a machine has a
   GPS location, and its Mobility in force is *Portable* or *Mobile*, the card shows under the
   GPS row: "This machine moves. The location may be out of date." The value is still allowed.
   A pure helper reads the value in force of a property by name, so later rules (PM, filters)
   can use it too.
7. **Masters › Properties** gets the type *Location* in the type list, two tick boxes in the
   dialog, and two small badges in the table: *Every class*, *Each machine*.
8. **Masters › Equip Class › Properties** lists the every-class properties too, each marked
   *Every class*, with no *Remove*. The *Add property…* picker leaves them out.

### Out of scope

- A map view of all machines, or a search by distance.
- A history of where a portable machine has been. A portable machine's place is its unit, and its
  moves are already logged (`moved_unit` events).
- A rule that ties GPS location to Mobility beyond the hint, e.g. refusing a value.
- Coordinates on sites or units.
- Seeding Mobility, or changing its options (KLA's row on production stays as made).
- A *Stationary* option for Mobility (IEC term, see § 2; KLA chose three options).
- A Location property on component-units and components (§ 7 D5).

## 2. Standards and practice

- **ISO 14224 (equipment data in maintenance), its clause on equipment data.** It separates the
  data of an equipment unit into kinds, among them:
  - *design data*, the same for every unit built to one design (rated power, speed; the
    equipment-specific data of Annex A, which S043 cites);
  - *installation and operation data*, which differ per unit (where it is installed, when it
    started).
  - In plain words: put the maker's numbers on the model once, and put where-it-stands on each
    machine. *Value set on each machine* is that split in Yantra. (No clause or table number is
    cited: not verified, BR1-10.)
- **IEC 60050-826, section 826-16 (International Electrotechnical Vocabulary, electrical
  installations: equipment).** It defines *fixed*, *stationary*, *portable* and *hand-held*
  equipment.
  - In plain words: *fixed* is fastened in place, *stationary* is too heavy to move in use, and
    *portable* is moved, or easily moved, while connected.
  - Why it matters: portable electrical equipment needs more frequent inspection and testing.
    KLA's Mobility uses *Fixed*, *Portable* and *Mobile* (self-propelled); *Stationary* is left
    out on purpose (§ 1 Out of scope).
- **ISO 27001 A.5.34 (privacy and protection of personal data).** The browser reads the phone's
  position only when the user taps the button, and only once. The position is stored as the
  machine's data. Who set it is in the machine's history (S044's `property` events). Nothing
  tracks a person. Each browser asks the user before it gives the position (the browser's own
  prompt).
- **ISO 55001 § 7.5 (information requirements).** An organisation decides what information
  it keeps about its assets. A location is a usual attribute of an asset in a register.
- **TPM, autonomous maintenance.** An operator or a fitter must find the machine. A position on
  the machine's page helps for machines away from a shop floor: farm borewells, stockyard
  gensets, transformers (Plant-Facts: the stockyard 63 kVA genset).

## 3. Where

### Backend

- `backend/local_db.py`: migration **v34** (§ 4), and its `_PRECONDITIONS` entry.
- `backend/properties_core.py`: the type `GEO`, its parse and display, the two flags in
  `validate_property` and `property_changes`, the columns of a value, `property_view` and
  `item_events` for Location, the helper `value_in_force` and the hint rule (§ 5).
- `backend/properties.py`: the flags in the selects; `linked_properties` and
  `lock_value_properties` take `all_classes` and the node level into account; the model dialog
  and the model save leave out or refuse `per_item_only`; `write_values` and `_VALUE_COLUMNS`
  carry the two new columns; `list_class_properties` returns the every-class properties (§ 5, § 6).
- `backend/item_properties.py`: the node's level passed to `linked_properties`; the dialog rows
  carry `per_item_only`.
- `backend/equipment.py`: `equipment_properties` is called with the node's level (line 312).

### Frontend

- `frontend/src/components/PropertyInput.vue`: the Location input, with *Use my current
  location* (§ 7 D3).
- `frontend/src/utils/propertyFormat.js`: *Location* in `DATA_TYPES`; `typeSummary` gives
  "Location".
- `frontend/src/views/masters/PropertiesPanel.vue`: two tick boxes, two badges, the type.
- `frontend/src/views/masters/ClassPropertiesView.vue`: every-class rows marked, no *Remove*.
- `frontend/src/views/masters/AddPropertiesModal.vue`: every-class properties left out.
- `frontend/src/views/equipment/ItemPropertiesModal.vue`: no model hint on a per-machine row.
- `frontend/src/views/EquipmentDetailView.vue`: *Open in Maps* link, the hint, no "· this
  machine" mark on a per-machine row; the "Values from model …" line and *Edit model values*
  only when the card has a row that is not per-machine (BR1-06).

### Tests

- `backend/tests/test_properties_core.py`, `backend/tests/test_properties_api.py`,
  `backend/tests/test_item_properties_api.py`, `backend/tests/test_equipment_api.py`: new tests
  (§ 8), and the changed ones listed in § 8.2.
- `backend/tests/test_migration_v34.py` (new).
- `backend/tests/conftest.py`: `_SEEDED_TABLES` keeps the seed rows of v31 **and** v34 (§ 8.3).
- `frontend/tests/propertyFormat.test.js`.
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/masters.spec.js` (BR1-13: the full paths).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the new columns, the CHECKs, the ENUM value, the
  seed row, "migration v34".
- `docs/Plan.MD` § 4.1 *Equipment class*: every-class properties, per-machine values, Location.
- `docs/steps/device-checks.md`: the rows of § 8.5.

## 4. Data model (migration v34)

One migration, re-runnable. Verified on the dev MariaDB 11.4.13 (27-10-2026, a scratch database):

- one `ALTER TABLE` can hold `ADD COLUMN IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` and
  `ADD CONSTRAINT`;
- running it twice gives the same table;
- the new pair CHECK refuses a latitude without a longitude (error 4025).

Statements:

1. `property_definitions`, in one `ALTER TABLE` (BR1-16):
   - `MODIFY data_type ENUM('number','choice','text','yes_no','geo') NOT NULL`, the value
     appended at the end, so no row changes;
   - `ADD COLUMN IF NOT EXISTS all_classes TINYINT(1) NOT NULL DEFAULT 0`;
   - `ADD COLUMN IF NOT EXISTS per_item_only TINYINT(1) NOT NULL DEFAULT 0`.
2. `model_property_values` and `equipment_property_values`, each in one `ALTER TABLE`:
   - `ADD COLUMN IF NOT EXISTS value_lat DECIMAL(8,6) NULL` (±90.000000);
   - `ADD COLUMN IF NOT EXISTS value_lng DECIMAL(9,6) NULL` (±180.000000);
   - `DROP CONSTRAINT IF EXISTS chk_<table>_one_value`, then `ADD CONSTRAINT` with the same name.
     It counts `value_lat` as the fifth value slot:
     `(value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL) +
     (option_id IS NOT NULL) + (value_lat IS NOT NULL) = 1`;
   - `DROP CONSTRAINT IF EXISTS chk_<table>_geo_pair`, then
     `ADD CONSTRAINT chk_<table>_geo_pair CHECK ((value_lat IS NULL) = (value_lng IS NULL))`;
   - `DROP CONSTRAINT IF EXISTS chk_<table>_geo_range`, then
     `ADD CONSTRAINT chk_<table>_geo_range CHECK (value_lat IS NULL OR (value_lat BETWEEN -90 AND
     90 AND value_lng BETWEEN -180 AND 180))` (BR1-03: the columns alone hold up to 99.999999 and
     999.999999).
   - The names are `chk_model_property_one_value` / `chk_equipment_property_one_value` (v31, v33),
     `chk_model_property_geo_pair` / `chk_equipment_property_geo_pair`, and
     `chk_model_property_geo_range` / `chk_equipment_property_geo_range`.
   - Every existing row has both new columns NULL and exactly one old column set, so it meets
     both CHECKs.
   - The model table gets the columns too, although no model holds a value of "GPS location".
     A Location property without *Value set on each machine* may still hold a model value.
3. The seed: `INSERT IGNORE INTO property_definitions (name, data_type, description, all_classes,
   per_item_only, created_by) VALUES ('GPS location', 'geo', 'Where the machine stands. Tap Use
   my current location next to the machine, or paste from Google Maps.', 1, 1, 'migration-v34')`.

**Precondition** (`_PRECONDITIONS[34]`, SMTW-WebApp-Base § Local DB Migration Pattern ›
Preconditions). It refuses v34 while a property named "GPS location" exists. The name is
compared without regard to case, by the column's collation. Without the refusal, `INSERT IGNORE`
would keep a hand-made row with another type and no flags, and nothing would say so.

- **An absent table passes** (BR1-01). `init_db` runs the check of every pending version
  before any is applied (`local_db.py:1206-1212`), so on an empty database
  `property_definitions` does not exist yet. The check first reads `information_schema.TABLES`
  (`TABLE_SCHEMA = DATABASE()`, as `_old_tables_for_v20` does) and passes when the table is
  absent, as the v20 and v25 checks do ("An absent table passes", `local_db.py:1049`, `1081`).

- Production today: KLA made Mobility by hand; no "GPS location" is known. The check costs one
  query.
- Refusal text (Settings › Database): "A property named GPS location already exists. Rename it in
  Masters › Properties; the update then adds the new one."

**Rollback** (corrected, BR1-04). The previous release reads `property_definitions` with
`SELECT p.*`, so it gets the two flags and ignores them.

- "GPS location" shows in its Masters with the raw type `geo`. It shows on no card, because the
  old `linked_properties` reads class links only.
- **Known risk:** if someone links a `geo` property to a class in the old release, the old code
  looks up `VALUE_COLUMNS["geo"]` and fails (500). Every equipment page of that class and the
  model dialog then fail, until the link is removed with *Remove*. The data is not harmed.
- The CHECKs still hold, since the old code writes one old column and leaves the new ones NULL.
- A rollback is rare, and the fix is one *Remove*, so the risk is accepted.

## 5. Rules

### 5.1 The flags (`properties_core.validate_property`, `property_changes`)

- Both are optional booleans, as `active` (`_parse_active`: true / false / 0 / 1). Any other
  value: "Choose yes or no".
- A create without a flag stores 0.
- **`all_classes`** may change at any time.
  - Off → on: existing links stay; they change nothing while the flag is on.
  - On → off: the property shows again only on its linked classes; values elsewhere stay, hidden,
    as with *Remove* from a class (S043 § 5.4).
- **`per_item_only`**:
  - **Turning it on** is refused while any model holds a value of the property: 409, field
    `per_item_only` (the dialog shows it under that tick box, BR1-07), "Models have values of
    this property. Clear them in each model first, or make a new property." This is the checked form of "fixed once a value exists" (the 27-10-2026
    session), for the only case that would strand values.
  - **Turning it off** is allowed at any time: the items' values stay, and models may then get
    values too.
  - The check is a locking read of `model_property_values` under the property's lock, as
    `has_values` today (`properties.py`, `update_property`).

### 5.2 A Location value (`properties_core.parse_value`, type `geo`)

- The value is sent as one string, as typed: the latitude and the longitude, separated by a comma,
  by spaces, or by both. Examples: "11.016823, 76.955812", "11.016823,76.955812",
  "11.016823 76.955812".
- Each number is plain digits: an optional minus, digits, optionally a point and digits (the
  rule of `_NUMBER_RE`).
- More than 6 decimals are **rounded** to 6 (`ROUND_HALF_UP`), not refused. Google Maps pastes up
  to 15 decimals, and 6 decimals is about 10 cm.
- Ranges: latitude −90 to 90, longitude −180 to 180, ends included.
- "0, 0" is accepted. It is in range, and the plant is far from it.
- Blank or null clears the value, as for every type.
- Messages (scope B):
  - not a string, not two numbers, or anything after them: "Enter the location as latitude,
    longitude, for example 11.016823, 76.955812";
  - latitude out of range: "The latitude must be between -90 and 90";
  - longitude out of range: "The longitude must be between -180 and 180".
- **The shape in the core** (BR1-05):
  - `parse_value` for `geo` returns `(lat, lng)` as two Decimals;
  - `GEO_COLUMNS = ("value_lat", "value_lng")` sits beside `VALUE_COLUMNS`;
  - every reader of a value's columns handles both: `check_values` (builds the columns),
    `stored_value`, `value_display`, `_same_value`, `write_values` and `_VALUE_COLUMNS` in
    `properties.py`;
  - `_same_value` compares both as Decimals, as it does `value_number`. A re-save with the same
    location writes no row and no history line.
- Stored in `value_lat` and `value_lng`, the other value columns NULL.
- **The value as the API sends it** (`stored_value`): the string "11.016823, 76.955812", with
  each number by `number_text` (no trailing zeros: "11.0168, 76.9558").
- **Display** (`format_value`): the same string.
- **The map link**: `https://www.google.com/maps/search/?api=1&query=<lat>,<lng>` (the
  documented Google Maps URLs form). The backend sends it as `map_url` on a card row with a
  value, else null. It is built from the stored numbers only, so no outside input enters the URL.

### 5.3 Which properties a node shows (`properties.linked_properties`)

- The active properties that are linked to the node's class **or** have `all_classes = 1`, by
  name.
- A `geo` property is left out unless the node's level is `equipment` (§ 7 D5).
- The function takes the node's level. Callers:
  - the card (`equipment_properties`, `equipment.py:312`);
  - the item dialog (`item_properties._item_properties`).
- The model dialog has no node. It uses level `equipment`, then leaves out the `per_item_only`
  properties (§ 5.4). A model's machines are almost always top level, and a Location property
  without the flag may be valued on a model.
  - **Known gap, accepted** (BR1-15): a model used only inside other machines (a motor model in a
    press) offers such a Location property, which none of its machines shows.
- **The class table** (`list_class_properties`, BR1-08): one row per property, the linked ones
  and the every-class ones together (a distinct union), built in `_class_properties`
  (`properties.py:211`), so the answers of *Add* and *Remove* carry the every-class rows too
  (BR2-01). An every-class row carries
  `all_classes: true`, and the table marks it *Every class* with no *Remove*, linked or not. The
  API still accepts a link of an every-class property; it has no effect while the flag is on,
  and takes effect if the flag is turned off.
- **Saves** (`lock_value_properties`): a property counts as `linked` when it is linked to the
  class or has `all_classes = 1`. The flag is read from the property row locked FOR UPDATE at
  step (2), so a flag change waits or is seen.
  - An item save also refuses a `geo` property on a node that is not of level `equipment`:
    "This property is not on the class" (`NOT_ON_CLASS`, the same message as any property the
    node does not show).

### 5.4 Per-machine properties

- The model dialog (`GET /equipment-models/<id>/properties`) leaves them out.
- A model save (`PUT`) naming one is refused: 400, field `values.<id>`, "Set this property on
  each machine, not on the model". The check runs in `check_values` (it gets `per_item_only`
  in `properties`, and an `owner` argument `"model"` / `"item"`).
- The item dialog rows carry `per_item_only: true`. The input shows no "Model: …" hint for
  them.
- The card rows carry `per_item_only`. The frontend gives such a row no "· this machine" mark,
  because every value of it is the machine's own.
- **The model line and *Edit model values*** (BR1-06): the card shows "Values from model …" and
  the *Edit model values* button only when it has a row that is not `per_item_only`. On release
  day most top-level machines have only "GPS location" on the card. Without this rule they would
  say "Values from model …", and the model dialog would say the class has no properties.
- `property_view` keeps its rule: an own value wins, else the model's. For a per-machine
  property no model value exists (§ 5.1), so the rule needs no change.

### 5.5 The value in force, and the hint (pure)

- `value_in_force(rows, name)`: from `property_view`'s rows, the row whose property name equals
  `name` without regard to case (`casefold`); None when there is none or it has no value.
- `moving_hint(rows)`: the hint text of § 1 item 6, or None. It is set when:
  - a row of type `geo` has a value; and
  - the row in force named `MOBILITY` ("Mobility") has a display, compared by `casefold`, in
    `MOVING_LABELS` ("Portable", "Mobile").
- The names are constants in `properties_core`. When KLA renames the property or an option, the
  hint stops showing; nothing fails.
- The card answer (`equipment_properties`) gets a field `moving_hint` (text or null). The card
  shows it under the Location row.
- `property_view`'s rows gain `data_type`, `per_item_only` and `map_url`, so the hint and the
  card can read them.

### 5.6 History

An item's set, change or clear of a Location value writes the usual `property` event
(`item_events`): "GPS location: no value" → "GPS location: 11.016823, 76.955812". A per-machine
property has no model value, so its "no value" side carries no "(model)" mark.

- To fix in `item_events`: today the side without an own value reads
  "no value (model)" when the item has a model. For a `per_item_only` property it reads
  "no value", as on an item without a model.

### 5.7 Locks

No new lock and no new order. The notes in `properties.py` and `item_properties.py` stay as
they are, with one line added each:

- the flags are read from the property row at step (2), which the writes already lock;
- `update_property`'s new check for turning `per_item_only` on is the locking read of
  `model_property_values` it already makes (`has_values`); it now also counts the model rows
  alone.

### 5.8 The database down

As today: every route answers 503 through `get_db()` (`DBUnavailable`). The *Use my current
location* button needs no server.

## 6. API

All routes exist. Keys unchanged: reads `masters:read` or `equipment:read`; writes
`equipment:edit` (the union for masters, the node's site for an item, S044).

| Route | Change |
|---|---|
| `GET /api/masters/properties` | Each property carries `all_classes`, `per_item_only` |
| `POST` / `PUT /api/masters/properties[/<id>]` | Take `all_classes`, `per_item_only`; data type `geo`; 409 of § 5.1 |
| `GET /api/masters/equipment-classes/<id>/properties` | Also lists every-class properties, each with `all_classes: true` |
| `GET` / `PUT /api/masters/equipment-models/<id>/properties` | Leaves out / refuses per-machine properties (§ 5.4) |
| `GET` / `PUT /api/equipment/<id>/properties` | Every-class properties; Location by level; rows with `per_item_only` |
| `GET /api/equipment/<id>` | `properties` rows carry `data_type`, `per_item_only`, `map_url`; new field `moving_hint` |

## 7. Design decisions

- **D1. Two DECIMAL columns for Location** (agreed with KLA). The database checks the range and
  the pairing (`chk_<table>_geo_range`, `chk_<table>_geo_pair`, § 4), so a later writer (a PM
  feed, an import) cannot store a latitude of 95.
  - Rejected: text "lat, lng" in `value_text`. Nothing would stop a typo, and a later map or
    distance search would have to parse text.
  - Rejected: a spatial `POINT` column. It adds a column type the app uses nowhere, for no need
    today.
- **D2. Flags on the property, not a new link table** (agreed with KLA). *Applies to every
  class* is one column. Linking the property to every class would miss each new class.
- **D3. *Use my current location*, one reading.** `navigator.geolocation.getCurrentPosition`
  with `enableHighAccuracy: true`, a timeout of 20 s, and no cached position (`maximumAge: 0`).
  - After the reading, the field shows the numbers (6 decimals). A line under it says "About
    12 m accurate" (`coords.accuracy`, rounded).
  - Above 50 m, the line reads "Rough location (about 300 m). Go into the open, then try again."
    The value is still filled in; the user decides.
  - Errors, shown under the input:
    - permission refused: "Location is blocked for Yantra in this browser. Allow it in the
      browser's settings, or type the location" (BR1-07: in Yantra a *site* is a plant site);
    - no position, or the timeout: "The phone could not find its location. Try again in the
      open, or type the location".
  - The button shows only when `window.isSecureContext && navigator.geolocation` (BR1-14).
    Production is HTTPS; the dev server on `localhost` counts as secure.
  - Rejected: watching the position until it is accurate. More code, and a user standing at the
    machine can tap again.
- **D4. The map link uses Google Maps' URL form.** It needs no key, opens the Maps app on
  Android and iPhone, and opens a browser tab on a desktop.
  - Rejected: `geo:` URIs. Android opens them, but iPhone Safari is not documented to (an
    assumption); the Google form works on both.
- **D5. Location only on top-level equipment.** A bearing or a gearbox is where its machine is.
  A GPS row on every part would be noise on the floor.
  - The rule is by data type, not a third flag.
  - Rejected: show it on every node, "—" on parts.
  - Rejected: a level setting per property. It solves a case nobody has yet.
  - Open question Q2.
- **D6. Turning on *Value set on each machine* is refused while a model has a value.** It is
  never silently cleared, as S043 fixes the data type once values exist.
- **D7. The hint is text only, from a pure helper** (KLA, 27-10-2026: "allow for now, … cheap to
  check with proper property-helper functions").
  - The property and option names are constants. A rename turns the hint off quietly.
  - Rejected: a link by id to KLA's Mobility row. The id differs between production, dev and
    the tests.
  - Open question Q1.
- **D8. The precondition refuses a hand-made "GPS location"** (§ 4). Rejected: rename or merge
  it in the migration. That would change KLA's data without asking.

## 8. Tests and acceptance

### 8.1 Core (`test_properties_core.py`)

- Location parse:
  - the three separators;
  - rounding at 7 decimals (`11.0000005` → `11.000001`);
  - the ends ±90 and ±180 accepted; 90.000001 and −180.000001 refused, each with its message;
  - one number, three numbers, letters and a JSON number refused;
  - blank clears;
  - "0, 0" accepted.
- `stored_value` and `format_value` for `geo`: no trailing zeros. `map_url`.
- `validate_property`: the two flags (true, false, 0, 1 accepted; "yes" refused); type `geo`
  accepted; a unit on `geo` refused (`UNIT_ONLY_NUMBER`).
- `property_changes`: turning `per_item_only` on with model values → 409; turning it off with
  them → allowed.
- `check_values`: owner `"model"` with a per-machine property → refused; owner `"item"` →
  accepted.
- `value_in_force`, `moving_hint`:
  - Portable, Mobile and Fixed;
  - Mobility missing;
  - Mobility without a value;
  - GPS without a value;
  - names in other case.
- `item_events` for a per-machine property on an item with a model: "no value", no "(model)".

### 8.2 API (`test_properties_api.py`, `test_item_properties_api.py`)

- A property with `all_classes` shows on the card of an item whose class has no link; turning the
  flag off hides it again; its item value stays in the table.
- A save of an every-class property on an item of an unlinked class is accepted.
- A re-save of the item dialog with the same location writes no row and no event (BR1-05; the
  pattern of `test_a_clear_of_a_row_with_no_own_value_writes_nothing`).
- The 409 for turning `per_item_only` on names the field `per_item_only` (BR1-07).
- Per-machine:
  - absent from the model dialog;
  - a model `PUT` naming it → 400;
  - turning the flag on with a model value → 409, without one → 200.
- Location:
  - an item `PUT` stores it and writes the `property` event;
  - the card has `display` and `map_url`;
  - a component-unit's card and dialog leave it out, and its `PUT` → 400 `NOT_ON_CLASS`.
- `moving_hint`: set when Mobility (made in the test) is Portable and GPS has a value; null when
  Fixed.
- Class properties list: the every-class rows carry `all_classes: true`; a property that is
  both linked and every-class is listed once (BR1-08).
- Permissions: unchanged keys. One test: an operator (`equipment:read` only) gets 403 on the item
  `PUT` of a Location value. **`test_role_matrix`** (`backend/tests/test_rbac.py`): no new key, so no change; check it still
  passes.
- **Existing tests to check:**
  - `test_properties_core.py`: its `check_values` calls gain the `owner` argument; its
    `property_view` tests that compare whole rows gain `data_type`, `per_item_only` and `map_url`.
  - **The seed row in existing tests** (BR1-02). "GPS location" is active and every-class, so it
    is on every top-level card, item dialog and class table, in the backend test database and in
    every e2e lane database. These tests break (checked by the reviewer):

    | File | Line | What breaks |
    |---|---|---|
    | `backend/tests/test_equipment_api.py` | 1552 | exact `properties` list on a top-level node: the GPS row added, every row gains `data_type`, `per_item_only`, `map_url` |
    | `backend/tests/test_equipment_api.py` | 1562 | `properties == []` on a top-level node with no links: now one row |
    | `backend/tests/test_item_properties_api.py` | 116, 119 | the dialog's id list gains the GPS row; the full-dict compare gains `per_item_only` |
    | `backend/tests/test_item_properties_api.py` | 139 | `len(items) == 4` → 5 (a top-level node) |
    | `backend/tests/test_properties_api.py` | 252 | a class list `== []` → the GPS row on every class |
    | `frontend/e2e/equipment.spec.js` | 372–373, 387, 395, 449, 461, 473, 481, 520 | exact `dt` / `dd` lists on top-level machines |
    | `frontend/e2e/masters.spec.js` | 360, 374, 388–389 | "No properties on this class yet." never shows now; row count 2 → 3; the card's `dt` list |

    **The convention:**
    - Backend tests compare the card and the dialog **without the seed rows**, through one helper
      per test module, `_made(rows)`: the rows whose `property_id` is among the ids the test made.
      Whole-row compares (`test_equipment_api.py:1552`) add `data_type`, `per_item_only` and
      `map_url` to the expected rows (BR2-03).
    - E2E tests assert `dt` lists with "GPS location" as the last row, and `dd` lists with "—"
      last (BR2-02). The by-name order puts
      "E2E …" before "GPS …".
    - `masters.spec.js:360` asserts the GPS row marked *Every class* instead of the empty
      state; `:374` expects 3.
    - `test_a_model_less_component_unit` reads a component-unit and stays as it is.
  - The `_SEEDED_TABLES` cleanup (`conftest.py`) today keeps only `created_by = 'migration-v31'`
    rows. It must keep `'migration-v34'` too, or the session deletes the GPS seed. Make the value
    a tuple of creators, and keep `SEED_CREATOR` for `test_migration_v11.py`.

### 8.3 Migration (`test_migration_v34.py`, the pattern of `test_migration_v33.py`)

- A fresh database gets the columns, the ENUM value, the six CHECKs (a lat without lng refused,
  4025; two value slots refused, 4025; a latitude of 91 refused, 4025) and the seed row with
  both flags.
- An empty database passes the precondition and migrates to v34 (BR1-01).
- A v33 database with model values, item values and events keeps every row.
- A re-run changes nothing.
- The precondition refuses a database holding "gps LOCATION", and passes without one.

### 8.4 Automated (e2e, targeted: `frontend/e2e/equipment.spec.js`, `frontend/e2e/masters.spec.js`, `frontend/e2e/screens.spec.js`)

Each test starts with "S061:". All untagged (logic) unless said.

- An engineer opens *Edit this machine's values* on a top-level machine, taps *Use my current
  location*, saves. The test calls `page.context().grantPermissions(["geolocation"])` and
  `page.context().setGeolocation(...)` before `asPerson` opens the page (BR1-14).
  The card shows the numbers and *Open in Maps* with the Google URL, and the history shows the
  line. **important**
- A pasted "11.0168234567, 76.9558123" saves as "11.016823, 76.955812".
- "95, 76" shows "The latitude must be between -90 and 90" under its input.
- The geolocation permission refused → the blocked message under the input.
- Masters › Properties: an engineer makes a Yes/No property with *Applies to every class*. It
  shows on a machine of a class without links, and in that class's table marked *Every class*,
  with no *Remove*. The picker does not list it. **important**
- A per-machine property is absent from *Edit model values*.
- A top-level machine whose card has only "GPS location" shows no "Values from model …" line
  and no *Edit model values* (BR1-06).
- A machine with Mobility *Portable* (property made in the test) and a GPS location shows the
  hint.
- **Existing tests that change:** "S043: the card is hidden when the class has no property"
  (`equipment.spec.js:398`). A top-level machine now always has "GPS location". The test moves to
  a component-unit, made with `noModelPart` (`frontend/e2e/support/properties.js:53`), of a class
  with no links (no Location there; BR2-05). It does not make the seed inactive:
  a failed test would leave the lane's seed inactive for every later test (BR1-12).
- The other existing tests that change: § 8.2, the table of BR1-02.

### 8.5 On a real device

Done by IT Admin, after the deploy (BR1-09):

- **Where:** production, on the phone, at a top-level machine.
- **Account:** a Yantra login that holds `equipment:edit` at the machine's site, e.g. an
  engineer of that site. The `it_admin` role alone grants nothing in Yantra (§ RBAC deviation).
- **Network:** the phone's location service on. The plant Wi-Fi or mobile data is needed for the
  page and the save; the position itself comes from GPS.
- **iPhone note:** an installed app (PWA) on iOS may ask for the location each time. A repeated
  prompt is expected there, not a fault.

The checks:

- **important** On an Android phone in Chrome, at a stockyard genset: *Use my current location*.
  Allow the prompt. The accuracy line shows, and *Open in Maps* opens the Maps app at the genset.
- **important** The same on an iPhone in Safari, and as the installed app (PWA): the prompt
  shows, the position fills, and *Open in Maps* opens Maps.
- Inside a shed: the accuracy line shows "Rough location" when the phone reports above 50 m.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs green; the whole-suite run once at the end.
- `docs/schema.md` and `schema.html` show v34.

## 9. Open questions and assumptions

- **Q1. The hint on portable and mobile machines** (§ 5.5, D7). **KLA: (a).**
  - (a) **Recommended:** build it now, text only, from the pure helper. Small (one function,
    one line on the card); KLA asked for the check.
  - (b) Build the helper only, no hint. The helper then has no user yet.
  - (c) Neither; decide later.
- **Q2. Location on parts** (D5). **KLA: (a).**
  - (a) **Recommended:** top-level equipment only.
  - (b) Every node.
- **Q3. Button text.** "Use my current location" (recommended) or "Use this phone's location".
  The second is wrong on a desktop. **KLA: "Use my current location".**
- **A1. Answered by KLA, 27-10-2026: production runs MariaDB 11.8.8** (schema v33), not 11.4
  like dev (`tooling/dev/docker-compose.dev.yml`: `mariadb:11.4`). The § 4 statements were
  tested on 11.4.13 only.
  - Assumption: `ADD COLUMN IF NOT EXISTS`, `DROP CONSTRAINT IF EXISTS` and named CHECKs have
    existed since MariaDB 10.2 to 10.4 and behave the same in 11.8. The risk is low, but not
    tested.
  - The release's upgrade test runs on the dev image (11.4), so it does not cover 11.8.
  - The dev image differing from production is a gap of its own: queued in `docs/steps/INDEX.md`,
    not part of this step.
  - **Open for the coding session:** whether the coder also runs v34 on a throwaway
    `mariadb:11.8` container. It needs KLA's OK, because it pulls an image outside the repo.
    Ask KLA before spawning the coder.
- **A2. Confirmed by KLA, 27-10-2026:** the Mobility row on production is named "Mobility",
  with options "Fixed", "Mobile", "Portable". The hint compares without regard to case.

## 10. Amendments

None yet.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 27-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major — the precondition fails on an empty database | **Accepted** (a): an absent `property_definitions` passes (`information_schema.TABLES`, as v20 and v25); § 4, and a migrate-from-empty case in § 8.3 |
| BR1-02 major — existing tests that break under-listed | **Accepted** (a): the reviewer's table in § 8.2, and one convention (backend `_made(rows)` per module; e2e `dt` lists with "GPS location" last; `masters.spec.js:360`, `:374`) |
| BR1-03 minor — D1 claims a range check the migration lacks | **Accepted** (a): `chk_<table>_geo_range` in the same re-runnable `ALTER` (§ 4); D1 reworded; a 91 refused in § 8.3 |
| BR1-04 minor — the rollback paragraph is wrong | **Accepted**: § 4 Rollback states the real behaviour and the known risk (a `geo` link in the old release fails that class's pages until *Remove*), accepted |
| BR1-05 minor — the geo value's shape and `_same_value` | **Accepted** (a): § 5.2 names `(lat, lng)` Decimals, `GEO_COLUMNS`, the six readers, and `_same_value`; a re-save test in § 8.2 |
| BR1-06 minor — the model line and *Edit model values* on a per-machine-only card | **Accepted** (a): § 5.4 and § 3; an e2e assertion in § 8.4 |
| BR1-07 minor — "site" in the blocked message; the 409 names no field | **Accepted**: the new text in D3; the 409 carries `field: "per_item_only"` (§ 5.1, § 8.2) |
| BR1-08 minor — linked and every-class: one row or two | **Accepted** (a): one row, marked *Every class*, no *Remove*; the link still accepted (§ 5.3, § 8.2) |
| BR1-09 minor — device checks lack account and network | **Accepted**: § 8.5 names where, account, network and the iOS PWA prompt |
| BR1-10 minor — standards' numbers "to verify" | **Accepted**: unverified numbers removed (ISO 14224 cited by its clause on equipment data, no number; IEC 60050-826 by section 826-16); ISO 27001 A.5.34 kept (confirmed); ISO 55001 § 7.5 added (§ 2) |
| BR1-11…BR1-16 nits | All accepted: trailing zeros said in § 1 (11); the hidden-card test moves to a component, not a deactivated seed (12); `frontend/e2e/…` paths (13); `window.isSecureContext && navigator.geolocation` and the Playwright calls named (14); the component-only model gap stated as accepted (15); the ENUM `MODIFY` in the same `ALTER` (16) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 27-10-2026

0 blocker, 0 major, 0 minor. BR2-01…BR2-05 (nits): all accepted. `_class_properties` named
(§ 5.3); `dd` lists with "—" last (§ 8.2); whole-row compares gain the new keys (§ 8.2); the
precondition's sentence moved above the bullets (§ 4); the hidden-card test uses `noModelPart`
(§ 8.4).

### Approval — gate A, 27-10-2026

KLA approved: Q1 (a), Q2 (a), Q3 as proposed, A2 confirmed. A1: production runs MariaDB 11.8.8;
the brief records it (§ 9 A1), and the dev image gap is queued. Coder: Opus (a migration on tables
with production rows, about 25 files).
