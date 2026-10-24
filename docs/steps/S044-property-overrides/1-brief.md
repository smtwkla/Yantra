```
Step: S044 — Property overrides on equipment items
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026 (revised 25-10-2026: brief-review r1, r2)
Track: full
Status: Approved (25-10-2026 by KLA; open questions 1–6 accepted as proposed)
Baseline: 5731712 (stale check 25-10-2026: since the approved baseline, only S040 A1 and S045 changed code; of the files this brief names, `frontend/e2e/masters.spec.js` changed in S045's deactivate test and `docs/Plan.MD` in S040's line, neither used by S044; no staleness review needed)
```

# S044 — Property overrides on equipment items

**The need (KLA, 24-10-2026, S043 split).** S043 holds a model's technical data: a motor
model's rated power, a pump model's displacement. One item can differ from its model: a motor
rewound to 5.5 kW, a pump with a larger impeller, a gearbox with a changed ratio. Its own
nameplate then says something the model does not. A component-unit without a model (S033)
has no values at all today: its card lists its class's properties with "—".

This step lets one item hold **its own value** of a property. It wins over the model's value
on that item only. Every set, change and clear is a line in the item's history (S043 U2).

Built on the working tree: `ff9ddb3` plus the snapshots `refs/steps/S038` … `refs/steps/S040`
(S037, S038, S043, S039, S040), and S045 in progress (test files only). This step's migration
is **v33** (v32 is S039's). Track: full — a migration, a new table, a locking write route, and
an event in the equipment history.

## 1. What will be built

1. **An item's own value** of a property linked to its class (S043 § 5.5). One per item and
   property. It holds one value of the property's data type (number, choice, text or yes/no),
   checked by the same rules as a model's value (`check_model_values`, generalised in § 5.1).
2. **The Properties card** (`EquipmentDetailView.vue`) shows, for each row, the value in force:
   - the item's own value; on an item **with a model** it is marked "· this machine" in small
     text (BR1-06: on a model-less component-unit every value is its own, so no mark);
   - else the model's value, as today;
   - else "—".
   The line under the rows changes:
   - with a model and no own value: "Values from model <model>." (as today);
   - with a model and at least one own value: "Values from model <model>, except those marked
     this machine.";
   - without a model (S033): no line.
   The card shows when the class has any active property, as today (S043 § 7.4).
3. **Edit this machine's values** — a button on the card for `equipment:edit` at the item's
   site (`canEdit`, the page's site-based flag), hidden on a scrapped item. It opens one dialog,
   `ItemPropertiesModal.vue`, titled **"This machine's values — <code>"** (BR1-07), so it is
   not taken for the model's dialog ("Properties of <model>"), which changes every machine of
   the model. It holds one `PropertyInput` per row of the card. Each input starts at the
   item's own value, or empty. Under each input, small grey text gives the model's value:
   "Model: 7.5 kW", or "Model: no value", or nothing on a model-less item. The text is the
   input's `hint` (a new `PropertyInput` prop, BR1-05), so it sits with its own input.
   - Typing a value sets or changes the item's own value.
   - Emptying the input clears it: the row falls back to the model's value.
   - *Save* sends every row, as the model dialog does; the backend keeps only the real changes
     (§ 5.1, `item_changes`).
4. **Edit model values** (S043) stays, second, after *Edit this machine's values* (BR2-07):
   the floor edits this machine's nameplate far more often, and the model button changes every
   machine of the model, so it stands apart. It is for `equipment:edit` held at any site, only
   on an item with a model. A model-less component-unit shows only *Edit this machine's values*.
   On a phone the two `btn-sm` buttons wrap onto their own lines (BR1-12).
5. **History.** Each changed row writes one `property` event, old → new:
   - old and new are "<property>: <display>" (e.g. "Rated power: 7.5 kW");
   - the side with no own value shows the value that was in force at the time of the write,
     marked as the model's (BR1-03, **for the user at gate A**): "Rated power: 7.5 kW
     (model)", or "Rated power: no value (model)" when the model has none, or "Rated power: no
     value" on a model-less item;
   - the history line names the property once (BR1-04): "Property: Rated power: 7.5 kW
     (model) → 5.5 kW".
6. **The Masters freeze** (S043 § 5.2) counts item values too: a property with item values
   keeps its data type and unit, as one with model values does. The two refusal texts become
   (BR1-08): "The data type cannot be changed: the property has options or values. Make a new
   property instead." (`DATA_TYPE_FIXED`) and "The unit cannot be changed: the property has
   values. Make a new property instead." (`UNIT_FIXED`). A value hidden by a class change (§ 1.7)
   still freezes the property and counts in `value_count`, as a model's hidden value does.
7. **The model or the class changes on an item:**
   - **the model changes, is set or is cleared** (S033): the item's own values stay. A
     nameplate belongs to the item, not to the model it was filed under;
   - **the class changes:** an own value of a property the new class lacks stays stored but is
     not shown, as a model's value does when its property leaves the class (S043 § 4.1: "the
     values stay"). It shows again if the property is linked again;
   - **a model of another class** changes both: the values stay, and those of properties the
     new class lacks are hidden (BR1-14).

### Out of scope

- Extra properties on one item that its class does not have (S043 § 4.5 "model extras",
  later).
- Item values in the equipment list, the asset list print, or search.
- Bulk entry of nameplate data (an import): typed one item at a time.
- Readings: a value that changes in service is a meter reading (S039), not a property.

## 2. Standards and practice

- **ISO 14224, equipment data** (clause 8, Table 5 "Equipment data (common data)"; the
  taxonomy § 8.2, Figure 3; Annex A, the class-specific data — numbers to verify against the
  user's copy): the taxonomy runs plant → unit → **equipment unit** → subunit → component. The
  maker and the model designation are **attributes of the equipment unit**, not a level of
  their own, and the design and nameplate data belong to the unit too. Yantra's model (S012,
  S043) is a convenience that stores a value once for many units. So the item's own value is
  the standard's own place; the model's value is the default. Why: reliability data compares
  like with like only when each item's real rating is known.
- **ISO 55001 § 7.5 (information requirements)** (to verify, as in S033): the organisation
  decides which asset data it keeps and at what quality. A value that says where it came from
  (this machine or its model) is data whose quality the reader can judge.
- **Change record (ISO 9001 § 7.5.3, control of documented information; to verify):** a
  changed rating is logged with who, when, old and new, as every register change is (S004). The
  record states the value before and after, not a pointer to where the old one came from
  (BR1-03).
- **TPM, equipment history card:** a rewind or an up-rated part is part of the machine's life
  story; it shows on its history, next to the tickets that led to it.

## 3. Where

### Backend

| File | Change |
|---|---|
| `backend/local_db.py` | migration **v33**: `equipment_property_values` (§ 4) and the `property` value in `equipment_events.event`; a "Rollback:" line in the v33 comment, as v27–v32 have (BR1-09); `LATEST_VERSION` follows |
| `backend/properties_core.py` | `check_model_values` → `check_values(values, properties, options, stored)` (same rules; the model route keeps its behaviour; docstring "a values save, a model's or an item's", BR1-10); `item_changes(changes, stored)` (§ 5.1, BR1-02); `property_view(properties, model_values, option_labels, item_values=None)` adds `source` "item"; `item_events(properties, changes, before, model_displays, option_labels, has_model)` → the `property` event triples (§ 5.4); `properties` carries each property's `unit`, `option_labels` is `{option_id: label}` (BR2-01); `DATA_TYPE_FIXED`, `UNIT_FIXED` reworded (§ 1.6) |
| `backend/properties.py` | `item_values(cur, node_id)` (new, public); `_options_by_property` and `_linked_properties` renamed `options_by_property` and `linked_properties`, with their callers in `properties.py`, since `item_properties.py` imports them (BR2-02); `equipment_properties(cur, class_id, model_id, node_id)` adds the item's values; `update_property`'s `has_values` also checks `equipment_property_values`; `_PROPERTY_SELECT`'s `value_count` counts both tables; the docstring gains one line pointing at `item_properties.py`. It still imports nothing from `equipment.py` |
| `backend/item_properties.py` (new, BR1-01) | `item_properties_bp`: `GET` and `PUT /equipment/<id>/properties` (§ 6); `_item_properties(cur, node)` (the dialog's rows); the LOCK ORDER note of the item write (§ 5.3). It imports from `equipment.py` (`load_node_for_user`, `SCRAPPED_MESSAGE`, `write_events`) and from `properties.py` (`options_by_property`, `linked_properties`, `item_values`: public names, as every other cross-module import in `backend/`, BR2-02) |
| `backend/app.py` | register `item_properties_bp` at `/api` (as `meters_bp`) |
| `backend/equipment.py` | the detail calls `equipment_properties` with the node's id; the LOCK ORDER note's properties bullet names the item write in `item_properties.py` (§ 5.3) |

**Why a new module (BR1-01).** `equipment.py` already imports `equipment_properties` from
`properties.py` (line 116). A `properties.py` that imported back from `equipment.py` would be a
circular import, and the app would not start. `item_properties.py` imports from both and is
imported by neither, as `meters.py` stands beside `masters.py`. Rejected: moving the card's
query into `equipment.py` (it belongs with the property code), and a lazy import inside
`_detail` (it hides the cycle instead of removing it).

### Frontend

| File | Change |
|---|---|
| `frontend/src/views/equipment/ItemPropertiesModal.vue` (new) | the dialog (§ 1.3), on `useFormModal` and `FormModal`, keyed `values.<property_id>` as `ModelPropertiesModal.vue`; title "This machine's values — <code>" |
| `frontend/src/components/PropertyInput.vue` | a `hint` prop: one `div.form-text` inside the `mb-3` wrapper, **after** the `invalid-feedback` line, which stays directly after the input, so a refusal stays beside its field and the hint does not push it down (BR2-06); `ModelPropertiesModal.vue` passes none (BR1-05) |
| `frontend/src/views/EquipmentDetailView.vue` | the card's "· this machine" mark (only with a model), the line under the rows, the *Edit this machine's values* button, the dialog |
| `frontend/src/utils/equipmentLabels.js` | the `property` event's history line; `limitsOnly` renamed `secondSide` and used by both the meter-limits and the property line (BR1-04); the header comment names S044 (BR1-15) |

### Tests

| File | Change |
|---|---|
| `backend/tests/test_properties_core.py` | `check_values`, `item_changes`, `property_view` with item values, `item_events` |
| `backend/tests/test_properties_api.py` | the freeze with item values; `value_count`; the new refusal texts |
| `backend/tests/test_item_properties_api.py` (new) | the two routes (§ 8.2) |
| `backend/tests/test_migration_v33.py` (new) | fresh database, upgrade from v32, re-run, on the pattern of `test_migration_v32.py` |
| `backend/tests/test_migration_v9.py` | `test_the_shape_holds`: the latest `equipment_events.event` ENUM gains `property` |
| `backend/tests/conftest.py` | `equipment_property_values` in `_TABLES`, before `equipment` (BR1-11) |
| `frontend/tests/equipmentLabels.test.js` | the `property` line; the meter-limits line still reads the same after the rename |
| `frontend/e2e/equipment.spec.js` | the e2e tests (§ 8.4), set up with `propertySetup` and `noModelPart` (`frontend/e2e/support/properties.js`) |

### Docs (housekeeping, by the coder)

Per `.claude/CLAUDE.md` § Docs to keep current:
- `docs/schema.md` and `docs/schema.html`: `equipment_property_values`, the `property` event,
  the "migration v33" line (by hand; no generator);
- `docs/Plan.MD` § 4.1: item values built (S044);
- `docs/Maintenance-Philosophy.md` glossary *Property*: "an item holds its own only where its
  nameplate differs (S044)" already says it; add "shown as this machine's, logged in its
  history";
- `.claude/CLAUDE.md` § SMTW-Review spec map: `equipment` S044.

## 4. Data model (migration v33)

```sql
CREATE TABLE IF NOT EXISTS equipment_property_values (
    equipment_id  INT NOT NULL,
    property_id   INT NOT NULL,
    value_number  DECIMAL(16,4) NULL,
    value_text    VARCHAR(100) NULL,
    value_bool    TINYINT(1) NULL,
    option_id     INT NULL,
    updated_at    DATETIME NULL,
    updated_by    VARCHAR(100) NULL,
    PRIMARY KEY (equipment_id, property_id),
    CONSTRAINT fk_equipment_property_values_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_equipment_property_values_property FOREIGN KEY (property_id)
        REFERENCES property_definitions (id),
    CONSTRAINT fk_equipment_property_values_option FOREIGN KEY (option_id, property_id)
        REFERENCES property_options (id, property_id),
    CONSTRAINT chk_equipment_property_one_value CHECK (
        (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
        + (option_id IS NOT NULL) = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE equipment_events MODIFY event
    ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
         'meter_added','meter_removed','meter_limits','property') NOT NULL;
```

- The same columns as `model_property_values` (v31), keyed by `equipment_id` (S043 § 4.5).
- New rows only; no existing row changes, so no `_PRECONDITIONS` entry. The `ALTER` appends a
  value at the end of the ENUM, as v30 did; existing events keep their values.
- Re-run: `CREATE TABLE IF NOT EXISTS`; the `MODIFY` is the same statement again.
- Rollback to the previous release: it ignores the table; it cannot show a `property` event
  (an unknown ENUM value fails its history read). A rollback after item values exist needs the
  db-server dump. Stated in a "Rollback:" line in the v33 comment, as v27–v32 have (BR1-09).

## 5. Rules

### 5.1 Validation (pure, `properties_core.py`)

- **The body:** `{"values": {"<property_id>": raw}}`, keys checked by `parse_value_keys` (S043).
  A missing `values` or a non-object: 400 "Send the values as an object" (`VALUES_NOT_OBJECT`).
  An empty object saves nothing and answers 200 with the rows (`parse_value_keys` returns no
  ids, as for the model route).
- **`check_values`** is `check_model_values` renamed, with the same checks in the same order
  (unknown ids first, then by property name; the first refusal answers and nothing is saved,
  S043 CR1-05):
  - the property is unknown, inactive or not linked to the item's class: "This property is not
    on the class" (`NOT_ON_CLASS`);
  - `raw` is `""` or `null`: **clear** the item's own value (no row afterwards);
  - otherwise `parse_value` by data type, with S043's messages (`ENTER_NUMBER`,
    `TOO_MANY_DECIMALS`, `NUMBER_TOO_BIG`, `TEXT_TOO_LONG`, `CHOOSE_YES_NO`, `CHOOSE_OPTION`);
    a stored inactive option may stay (S043's rule).
  The model route calls it unchanged; its tests stay green.
- **`item_changes(changes, stored)`** (pure, BR1-02) takes `check_values`' output and the
  item's stored own rows, and returns only the real changes. The write (insert, update or
  delete) and `item_events` both take its output, so no write and no event come from a row that
  did not change. It drops:
  - a clear (`None`) of a property with **no stored own row**;
  - a value equal to the stored own value. Equality by data type: a number as `Decimal`
    against the stored `DECIMAL(16,4)` (`5.5` equals `5.5000`); text exactly; yes/no as 0/1;
    a choice by option id.
- **A value equal to the model's** is stored as the item's own (decision 3).

### 5.2 Checks against the database (`item_properties.py`)

- The node: `load_node_for_user(cur, node_id, for_update=True, key="equipment:edit")` — 404 for
  a node the user cannot see, 403 without `equipment:edit` at its site (the helper's own text).
- Scrapped: 409 `SCRAPPED_MESSAGE` ("This record is scrapped and cannot be changed"), decided
  from the locked row. The `GET` works on a scrapped item (read-only).
- The properties: the ids named, locked ascending `FOR UPDATE`, reading `id, name, data_type,
  unit, active` (the unit for the history texts, BR2-01); their class links for the
  node's class (from the locked node row) read `LOCK IN SHARE MODE`; their options read
  `LOCK IN SHARE MODE` (S043's model write, the same reads).
- The item's stored own rows for the named ids: read after the locks (the node lock (1) holds
  every writer of them), for `item_changes` and the history texts.
- The model's values for the named ids: read `LOCK IN SHARE MODE` after the locks (BR2-04), so
  the "(model)" side is the committed value in force at write time, not the snapshot taken at
  the node read. No new cycle: the model save takes the model, then the properties, then these
  rows; this write never takes the model.
- `option_labels` for the history: built from the options already share-read (S043's
  `options_by_property` returns the label), as `_card_rows` does (BR2-01).

### 5.3 Locks

The item write:

1. the node's `equipment` row (`load_node_for_user`, `FOR UPDATE`; equipment.py step (1));
2. the `property_definitions` rows named, ascending, `FOR UPDATE`;
3. the `class_properties` rows of the node's class for those ids, and their
   `property_options` rows, `LOCK IN SHARE MODE`; then the model's `model_property_values`
   rows for those ids, `LOCK IN SHARE MODE` (BR2-04);
4. the `equipment_property_values` rows: insert, update or delete by primary key; then the
   `equipment_events` inserts.

No cycle:
- properties.py's other writes lock a class or a model, then properties and options, and
  **never equipment**. This write takes equipment first, then properties. No path takes a
  property row and then an equipment row.
- `update_property` holds a property row (2) and then share-reads both value tables. An item
  write waiting on that property row holds only the node (1), which `update_property` never
  needs.
- Removing a property from a class takes the class row, then deletes the link row; this write
  share-locks the link row but never takes the class row. A remove that comes first makes this
  write refuse "This property is not on the class"; one that comes second waits for the link
  row's share lock.
- The node's model and class are read from its locked row; a concurrent node edit (model or
  class change, equipment.py (1)) waits on the same row, so the class used for the links is the
  one committed.
- The `GET` and the detail read plainly.

Both LOCK ORDER notes (`item_properties.py` docstring, `equipment.py`'s properties bullet) say
this; `properties.py`'s docstring points at `item_properties.py`.

### 5.4 History (`item_events`, pure)

- One `property` event per change from `item_changes`, in property-name order, in the write's
  transaction.
- `old_value`, `new_value`: "<name>: <display>" — `display` from `format_value` (S043), e.g.
  "Rated power: 7.5 kW", "Shaft orientation: Horizontal", "Ex-proof: Yes".
- The side with no own value (BR1-03, **for the user at gate A**): the model's value in force
  at write time, marked "(model)": "Rated power: 7.5 kW (model)"; "Rated power: no value
  (model)" when the model has none; "Rated power: no value" on a model-less item (S033).
- Length: name ≤ 80 + ": " + display (text ≤ 100 is the longest; a number with a unit ≤ 39: `DECIMAL(16,4)` gives up to 18 characters, a space and a unit ≤ 20, BR2-05) + " (model)" 8
  = 190, within `VARCHAR(200)`.
- `equipmentLabels.js`: `case "property": return change("Property", oldValue, secondSide(oldValue, newValue));`
  — `secondSide` is `limitsOnly` renamed (BR1-04); it cuts the repeated "<name>: " from the new
  side, so the line reads "Property: Rated power: 7.5 kW (model) → 5.5 kW". The meter-limits
  line keeps its text.

### 5.5 Reads

- **The detail** (`GET /api/equipment/<id>`): `properties` rows gain the item's values;
  `source` is `"item"`, `"model"` or `null`; `display` is the value in force. One extra query
  (`item_values`), not per row.
- **The dialog's rows** (`GET /api/equipment/<id>/properties`: `load_node_for_user(cur, node_id,
  for_update=False, key="equipment:read")`, the form `list_node_meters` uses for a stand-alone
  route on a node, which also checks the key at the node's site, BR2-03): per linked active property, by name — `property_id`, `name`,
  `data_type`, `unit`, `options` (active, plus the stored inactive one), `value` (the item's own,
  or null), `model_display` (the model's value as text, or null), `has_model`. `has_model` is
  kept (BR1-13): the route stands alone, without the page's node.

### 5.6 The database down

Both routes go through `get_db()`: `DBUnavailable` → 503, as every route. The dialog's failed
fetch leaves it closed with the message on the card (S043's pattern, `propertiesError`); a
failed save keeps the dialog open with the typed values (`FormModal`).

## 6. API

| Route | Key | Body | Answer |
|---|---|---|---|
| `GET /api/equipment/<id>/properties` | `equipment:read` at the node's site (`load_node_for_user(..., key="equipment:read")`, BR2-03) | — | `{items: [...]}` (§ 5.5) |
| `PUT /api/equipment/<id>/properties` | `equipment:edit` at the node's site | `{values: {"<property_id>": raw or "" / null}}` | 200 `{items: [...]}`; 400 (field `values.<id>`), 403, 404, 409 scrapped |

`GET /api/equipment/<id>` changes only inside `properties` (`source` may be `"item"`).

## 7. Design decisions

1. **One table keyed by item, the model's columns** (S043 § 4.5). Rejected: a JSON column on
   `equipment` (no type checks, no FK to options).
2. **The item's value wins on that item only; the model's stays the default.** Rejected:
   copying the model's values to each item (copies drift; S038 decision 1).
3. **A value equal to the model's is kept as the item's own.** A nameplate is a fact of the
   item: if the model's value is later corrected, the item must keep what its plate says.
   Rejected: S038's rule for limits ("equal to the model is no override"), which suits a
   setting, not a recorded fact.
4. **Own values survive a model change and a class change.** They describe the item. A value
   of a property the new class lacks is hidden, not deleted, like a model's (S043). Rejected:
   clearing them (the nameplate data would be lost by a filing fix).
5. **`equipment:edit` at the item's site**, as S038's node meters. Rejected: the model keepers'
   global key (an engineer of another site would edit this site's machine).
6. **One dialog for all of the item's values**, as the model's (S043). Rejected: a dialog per
   row (more taps for a nameplate of six values).
7. **The history records the value in force, marked "(model)"** (BR1-03, for the user at gate
   A). A reader a year later sees the rewind took the motor from 7.5 kW to 5.5 kW. Rejected:
   "model value" with no number (the old rating is lost), and "model value 7.5 kW" (longer, no
   clearer).
8. **The item write in its own module, `item_properties.py`** (BR1-01; § 3, "Why a new
   module").
9. **The backend keeps only real changes** (`item_changes`, BR1-02). The dialog sends every
   row, as the model dialog does. Rejected: the dialog sending only changed rows (the API is
   open to a full body, so the backend rule is needed anyway).

## 8. Tests and acceptance

### 8.1 Core (`test_properties_core.py`)

- `check_values`: every S043 model case still passes under the new name; clear by `""` and by
  `null`.
- `item_changes`: a clear with no stored row dropped; an equal value dropped per data type
  (`5.5` vs `5.5000`, text, yes/no, option id); a real set, change and clear kept.
- `property_view` with item values: item wins (`source` "item"), model fallback, none.
- `item_events`: the unit and an option label in the texts ("Rated power: 5.5 kW",
  "Shaft orientation: Horizontal", BR2-01); set from the model's value ("7.5 kW (model)"), from a model with no value
  ("no value (model)"), on a model-less item ("no value"), a change, a clear back to the
  model's value.

### 8.2 API (`test_item_properties_api.py`)

- `GET`: an item with a model, own values and none; a model-less component-unit (`has_model`
  false, `model_display` null); a scrapped item readable.
- `PUT`: set, change, clear, each with its `property` event (old and new texts, the "(model)"
  side); equal to the model's value stored; a full body with one change writes one row and one
  event; a clear of a row with no own value writes nothing.
- Refusals: 403 without `equipment:edit` at the site (an engineer of another site); 404 an
  unseen node; 409 scrapped; 400 not on the class (unlinked, inactive, unknown), with the
  first refusal by name and nothing saved; each data type's bad value; an inactive stored
  option kept.
- The model changes, or is cleared on a component-unit: own values stay. The class changes:
  an own value of an unlinked property is hidden in `GET` and the detail, and shows again
  when linked. A model of another class: both rules at once.
- The detail's `properties` rows carry `source` "item".

### 8.3 Masters (`test_properties_api.py`), migration, shape

- A property with only item values: its data type and unit are frozen (409, the new texts);
  `value_count` counts the item value, a hidden one too.
- `test_migration_v33.py`: the table, its FKs and CHECK (one value only), the ENUM; upgrade
  from v32; re-run.
- `test_migration_v9.py::test_the_shape_holds`: the ENUM's last value is `property`.

### 8.4 Automated (e2e, `frontend/e2e/equipment.spec.js`, targeted)

Set-up per test by API: `propertySetup(propertyTag(testInfo), …)` (its own class, model and
machine at SMTW.MCC1, the three projects on one database); `noModelPart` for a component-unit.

- **Important.** The engineer opens a machine whose model gives *Rated power* 7.5 kW, taps
  *Edit this machine's values* (the dialog fits, `expectDialogFits`; its title "This machine's
  values — <code>"; "Model: 7.5 kW" under the input), types 5.5 and saves. The card shows
  "5.5 kW · this machine" and the line "Values from model …, except those marked this
  machine."; the History card shows "Property: Rated power: 7.5 kW (model) → 5.5 kW".
- The engineer clears it: the card shows 7.5 kW again with no mark.
- A model-less component-unit: only *Edit this machine's values* shows; a saved value shows
  with **no** "· this machine" mark.
- The operator sees no *Edit this machine's values*; nor does anyone on a scrapped machine.
- A refusal (a number with five decimals) shows under its input (`expectFieldMessage`).

The coder runs `equipment.spec.js`, `masters.spec.js` (the freeze, and the model dialog with
`PropertyInput`'s new prop unset) and `screens.spec.js` (targeted: no shared frontend code
changes).

### 8.5 On a real device

None. The dialog and the card are the same parts as S043's, checked by the e2e run on the
three projects.

### 8.6 Acceptance

The important e2e test green on the three projects; all suites green; the schema docs at v33.

## 9. Open questions and assumptions

1. **Own values on a model change** (§ 1.7, decision 4). **Proposed:** kept. Alternative:
   cleared, with a history line each — fits a "wrong model, start again" fix, but loses a
   real nameplate on a filing correction. *ISO 14224 (reviewer, r1):* the maker and model are
   attributes of the equipment unit; correcting which model a unit was filed under changes one
   attribute, and the unit's recorded nameplate data stay true. A "start again" fix clears the
   values one by one in the dialog, each with a history line. An own value equal to the new
   model's keeps its mark; harmless, and the history says when it was typed.
2. **Equal to the model's value** (decision 3). **Proposed:** kept as the item's own.
   Alternative: dropped as no override (S038's rule), so the item follows later model edits.
   *ISO 14224 (reviewer, r1):* a nameplate reading is a verified attribute of this unit (§ 9.4,
   data quality: the data's source is known). S038's rule fits a limit, a setting; a rating is
   a fact. The cost: an engineer who types the model's number by habit pins it to the machine;
   the clear path and the "Model: …" hint make that visible.
3. **A class change** (§ 1.7). **Proposed:** hidden, kept. Alternative: deleted, with a
   history line. *ISO 14224 (reviewer, r1):* Annex A data are class-specific, so a property the
   new class lacks has no row on the card; deleting the value would lose a fact on a filing
   fix, as S043 § 5.4 reasons for models. A hidden value still freezes the property's type and
   unit and counts in `value_count` (§ 1.6).
4. **The history's old side** (BR1-03, decision 7, **for the user at gate A**). **Proposed:**
   the value in force at write time, marked "(model)": "Rated power: 7.5 kW (model) → 5.5 kW".
   Alternative: "model value" with no number (shorter; the old rating is lost).
5. **The words** (assumption): *Edit this machine's values*, "This machine's values — <code>",
   "· this machine", "Values from model <model>, except those marked this machine.", "Model:
   <value>", "Model: no value", "(model)", and the two freeze texts of § 1.6. *Machine* is the
   word S038 uses on node meters ("set on this machine"); a component-unit is called a machine
   there too.
6. **Standards numbers** (to verify): ISO 14224 clause 8 Table 5, § 8.2 Figure 3, § 9.4,
   Annex A; ISO 55001 § 7.5; ISO 9001 § 7.5.3.

## 10. Amendments

None.

## Review log

### U1 — from S043, 24-10-2026

- An override on an equipment item is logged in the equipment's history (S043 U2).
- Split from S043; reuses `PropertyInput.vue` and the card (S043 § 4.5, the queued item).

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

1 major, 6 minor, 8 nits; no blocker.

| Finding | Answer |
|---|---|
| BR1-01 major — `properties.py` importing from `equipment.py` is a circular import | Accepted (a): a new `item_properties.py` holds `item_properties_bp`, the `GET` and `PUT`, `_item_properties` and the write's LOCK ORDER note; it imports from both; `properties.py` imports nothing from `equipment.py`. § 3 (with "Why a new module"), § 5.2, § 5.3, decision 8 |
| BR1-02 minor — "no change" not fully defined; what the dialog sends | Accepted (a): pure `item_changes(changes, stored)` drops a clear with no stored row and an equal value (equality per data type stated); the write and `item_events` take its output; the dialog sends every row. § 1.3, § 5.1, § 5.4, decision 9, § 8.1, § 8.2 |
| BR1-03 minor — "model value" records nothing of what was in force | Accepted (a), **for the user at gate A**: the old side is the model's value at write time, marked "(model)"; "no value (model)", "no value" on a model-less item; length 190 ≤ 200. § 1.5, § 2, § 5.4, decision 7, § 9.4 |
| BR1-04 minor — the history line names the property twice | Accepted (a): `limitsOnly` renamed `secondSide`, used by both lines: "Property: Rated power: 7.5 kW (model) → 5.5 kW". § 1.5, § 3, § 5.4, § 8.4 |
| BR1-05 minor — the "Model: …" hint detached from its input | Accepted (a): a `hint` prop on `PropertyInput` (a `div.form-text` inside the `mb-3`); the component is listed as changed. § 1.3, § 3, § 8.4 |
| BR1-06 minor — "· this machine" on every row of a model-less item | Accepted (a): the mark only when the node has a model; `source` stays "item". § 1.2, § 8.4 |
| BR1-07 minor — the item dialog needs a title saying its reach | Accepted (a): "This machine's values — <code>". § 1.3, § 3, § 8.4, § 9.5 |
| BR1-08…BR1-15 nits | All accepted. BR1-08: the freeze texts reworded (§ 1.6). BR1-09: a "Rollback:" line in the v33 comment (§ 3, § 4). BR1-10: `check_values`' docstring generalised (§ 3). BR1-11: `_TABLES`, before `equipment` (§ 3). BR1-12: the two `btn-sm` buttons wrap (§ 1.4). BR1-13: `has_model` kept, the route stands alone (§ 5.5). BR1-14: a model of another class, both rules (§ 1.7, § 8.2). BR1-15: `equipmentLabels.js`'s header names S044 (§ 3). The reviewer's ISO 14224 reasoning on the three open questions is recorded beside each (§ 9.1–9.3), with the note that a hidden value still freezes the property and counts in `value_count` (§ 1.6). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 25-10-2026

0 blocker, 0 major, 1 minor, 7 nits.

| Finding | Answer |
|---|---|
| BR2-01 minor — `item_events` cannot format the unit or an option label | Accepted (a): the locking property read selects `unit`; `item_events(..., option_labels, has_model)`, `option_labels` from the share-read options; § 3, § 5.2, § 8.1 |
| BR2-02…BR2-08 nits | All accepted. BR2-02: `options_by_property`, `linked_properties`, `item_values` are public names. BR2-03: the dialog's `GET` uses `load_node_for_user(..., key="equipment:read")`, as `list_node_meters`. BR2-04: the model's values read `LOCK IN SHARE MODE` (lock step 3), no new cycle. BR2-05: the length reads "a number with a unit ≤ 39". BR2-06: the hint after the `invalid-feedback`. BR2-07: *Edit this machine's values* first, *Edit model values* second. BR2-08: the README row set (Gate A). |

### U3 — approval, 25-10-2026

- Approved by KLA ("S044 approved, implement"). § 9 items 1–4 as proposed: own values kept on a model change; a value equal to the model's kept as the item's own; hidden, not deleted, on a class change; the history's old side shows the value in force marked "(model)". Items 5–6 (words, standards numbers) accepted as written.
