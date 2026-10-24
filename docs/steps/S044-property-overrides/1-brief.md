```
Step: S044 — Property overrides on equipment items
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: full
Status: Draft
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
   - the item's own value, marked "· this machine" in small text, when it has one;
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
   `ItemPropertiesModal.vue`, with one `PropertyInput` per row of the card. Each input starts at
   the item's own value, or empty. Under each input, small grey text gives the model's value:
   "Model: 7.5 kW", or "Model: no value", or nothing on a model-less item.
   - Typing a value sets or changes the item's own value.
   - Emptying the input clears it: the row falls back to the model's value.
   - *Save* saves every changed row in one request; nothing else changes.
4. **Edit model values** (S043) stays beside it, for `equipment:edit` held at any site, only
   on an item with a model. A model-less component-unit shows only *Edit this machine's values*.
   On a phone the two buttons wrap; each is a full-size button.
5. **History.** Each saved row writes one `property` event, old → new:
   - old and new are "<property>: <display>" (e.g. "Rated power: 7.5 kW");
   - a side with no own value reads "<property>: model value" (or "<property>: no value" on a
     model-less item);
   - the history line reads "Property: Rated power: model value → Rated power: 5.5 kW".
6. **The Masters freeze** (S043 § 5.2) counts item values too: a property with item values
   keeps its data type and unit, as one with model values does. The two refusal texts say
   "models or equipment items hold values" (`DATA_TYPE_FIXED`, `UNIT_FIXED`).
7. **The model or the class changes on an item:**
   - **the model changes, is set or is cleared** (S033): the item's own values stay. A
     nameplate belongs to the item, not to the model it was filed under;
   - **the class changes:** an own value of a property the new class lacks stays stored but is
     not shown, as a model's value does when its property leaves the class (S043 § 4.1: "the
     values stay"). It shows again if the property is linked again.

### Out of scope

- Extra properties on one item that its class does not have (S043 § 4.5 "model extras",
  later).
- Item values in the equipment list, the asset list print, or search.
- Bulk entry of nameplate data (an import): typed one item at a time.
- Readings: a value that changes in service is a meter reading (S039), not a property.

## 2. Standards and practice

- **ISO 14224, equipment data** (clause 8, Table 5 "Equipment data (common data)" — numbers
  to verify against the user's copy): it separates the data of an equipment *class* and *type*
  from the data of one *equipment unit*, such as its serial number and its own technical data.
  S043 holds the design data on the model; this step holds the item's **as-built** data, where
  its nameplate differs. Why: reliability data compares like with like only when each item's
  real rating is known.
- **ISO 55001 § 7.5 (information requirements)** (to verify, as in S033): the organisation
  decides which asset data it keeps and at what quality. A value that says where it came from
  (this machine or its model) is data whose quality the reader can judge.
- **Change record (ISO 9001 § 7.5.3, control of documented information; to verify):** a
  changed rating is logged with who, when, old and new, as every register change is (S004).
- **TPM, equipment history card:** a rewind or an up-rated part is part of the machine's life
  story; it shows on its history, next to the tickets that led to it.

## 3. Where

### Backend

| File | Change |
|---|---|
| `backend/local_db.py` | migration **v33**: `equipment_property_values` (§ 4) and the `property` value in `equipment_events.event`; `LATEST_VERSION` follows |
| `backend/properties_core.py` | `check_model_values` → `check_values(values, properties, options, stored)` (same rules; the model route keeps its behaviour); `property_view(properties, model_values, option_labels, item_values=None)` adds `source` "item"; `item_events(properties, changes, before, labels, has_model)` → the `property` event triples (§ 5.4); `DATA_TYPE_FIXED`, `UNIT_FIXED` reworded (§ 1.6) |
| `backend/properties.py` | `_item_values(cur, node_id)`; `equipment_properties(cur, class_id, model_id, node_id)` adds the item's values; `_item_properties(cur, node)` (the dialog's rows); a second blueprint `item_properties_bp` with `GET` and `PUT /equipment/<id>/properties` (§ 6); `update_property`'s `has_values` also checks `equipment_property_values`; `_PROPERTY_SELECT`'s `value_count` counts both tables; the LOCK ORDER note gains the item write (§ 5.3) |
| `backend/app.py` | register `item_properties_bp` at `/api` (as `meters_bp`) |
| `backend/equipment.py` | the detail calls `equipment_properties` with the node's id; the LOCK ORDER note's properties bullet names the item write (§ 5.3) |

### Frontend

| File | Change |
|---|---|
| `frontend/src/views/equipment/ItemPropertiesModal.vue` (new) | the dialog (§ 1.3), on `useFormModal` and `FormModal`, keyed `values.<property_id>` as `ModelPropertiesModal.vue` |
| `frontend/src/views/EquipmentDetailView.vue` | the card's "· this machine" mark, the line under the rows, the *Edit this machine's values* button, the dialog |
| `frontend/src/utils/equipmentLabels.js` | the `property` event's history line |

`PropertyInput.vue` is reused unchanged.

### Tests

| File | Change |
|---|---|
| `backend/tests/test_properties_core.py` | `check_values`, `property_view` with item values, `item_events` |
| `backend/tests/test_properties_api.py` | the freeze with item values; `value_count` |
| `backend/tests/test_item_properties_api.py` (new) | the two routes (§ 8.2) |
| `backend/tests/test_migration_v33.py` (new) | fresh database, upgrade from v32, re-run, on the pattern of `test_migration_v32.py` |
| `backend/tests/test_migration_v9.py` | `test_the_shape_holds`: the latest `equipment_events.event` ENUM gains `property` |
| `backend/tests/conftest.py` | `equipment_property_values` in `_TABLES`, before `equipment` and `property_definitions` |
| `frontend/tests/equipmentLabels.test.js` | the `property` line |
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
  db-server dump. Stated in the impl report's release notes, as S038 did for v30.

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
- **A value equal to the model's** is stored as the item's own (decision 3). A value equal to
  the item's stored own value is no change: no write, no event.

### 5.2 Checks against the database (`properties.py`)

- The node: `load_node_for_user(cur, node_id, for_update=True, key="equipment:edit")` — 404 for
  a node the user cannot see, 403 without `equipment:edit` at its site (the helper's own text).
- Scrapped: 409 `SCRAPPED_MESSAGE` ("This record is scrapped and cannot be changed"), decided
  from the locked row. The `GET` works on a scrapped item (read-only).
- The properties: the ids named, locked ascending `FOR UPDATE`; their class links for the
  node's class (from the locked node row) read `LOCK IN SHARE MODE`; their options read
  `LOCK IN SHARE MODE` (S043's model write, the same reads).

### 5.3 Locks

The item write:

1. the node's `equipment` row (`load_node_for_user`, `FOR UPDATE`; equipment.py step (1));
2. the `property_definitions` rows named, ascending, `FOR UPDATE`;
3. the `class_properties` rows of the node's class for those ids, and their
   `property_options` rows, `LOCK IN SHARE MODE`;
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

Both LOCK ORDER notes (`properties.py` docstring, `equipment.py`'s properties bullet) say this.

### 5.4 History (`item_events`, pure)

- One `property` event per changed row, in property-name order, in the write's transaction.
- `old_value`, `new_value`: "<name>: <display>" — `display` from `format_value` (S043), e.g.
  "Rated power: 7.5 kW", "Shaft orientation: Horizontal", "Ex-proof: Yes".
- The side with no own value: "<name>: model value" when the item has a model, "<name>: no
  value" when it has none (S033).
- Length: name ≤ 80 + ": " + display ≤ 120 (text ≤ 100; a number with a unit ≤ 20) stays within
  `VARCHAR(200)`.
- `equipmentLabels.js`: `case "property": return change("Property", oldValue, newValue);`.

### 5.5 Reads

- **The detail** (`GET /api/equipment/<id>`): `properties` rows gain the item's values;
  `source` is `"item"`, `"model"` or `null`; `display` is the value in force. One extra query
  (`_item_values`), not per row.
- **The dialog's rows** (`GET /api/equipment/<id>/properties`, `equipment:read`, the node's
  access as the detail): per linked active property, by name — `property_id`, `name`,
  `data_type`, `unit`, `options` (active, plus the stored inactive one), `value` (the item's own,
  or null), `model_display` (the model's value as text, or null), `has_model`.

### 5.6 The database down

Both routes go through `get_db()`: `DBUnavailable` → 503, as every route. The dialog's failed
fetch leaves it closed with the message on the card (S043's pattern, `propertiesError`); a
failed save keeps the dialog open with the typed values (`FormModal`).

## 6. API

| Route | Key | Body | Answer |
|---|---|---|---|
| `GET /api/equipment/<id>/properties` | `equipment:read`, the node's access | — | `{items: [...]}` (§ 5.5) |
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
7. **"model value" in the history,** not the model's number: the model's value can change
   later, so naming it would record a value that was never this item's.

## 8. Tests and acceptance

### 8.1 Core (`test_properties_core.py`)

- `check_values`: every S043 model case still passes under the new name; clear by `""` and by
  `null`.
- `property_view` with item values: item wins (`source` "item"), model fallback, none.
- `item_events`: set from model value, change, clear; a model-less item's "no value"; no
  event for an unchanged value.

### 8.2 API (`test_item_properties_api.py`)

- `GET`: an item with a model, own values and none; a model-less component-unit (`has_model`
  false, `model_display` null); a scrapped item readable.
- `PUT`: set, change, clear, each with its `property` event (old and new texts); equal to the
  model's value stored; an unchanged value writes nothing.
- Refusals: 403 without `equipment:edit` at the site (an engineer of another site); 404 an
  unseen node; 409 scrapped; 400 not on the class (unlinked, inactive, unknown), with the
  first refusal by name and nothing saved; each data type's bad value; an inactive stored
  option kept.
- The model changes, or is cleared on a component-unit: own values stay. The class changes:
  an own value of an unlinked property is hidden in `GET` and the detail, and shows again
  when linked.
- The detail's `properties` rows carry `source` "item".

### 8.3 Masters (`test_properties_api.py`), migration, shape

- A property with only item values: its data type and unit are frozen (409, the new texts);
  `value_count` counts the item value.
- `test_migration_v33.py`: the table, its FKs and CHECK (one value only), the ENUM; upgrade
  from v32; re-run.
- `test_migration_v9.py::test_the_shape_holds`: the ENUM's last value is `property`.

### 8.4 Automated (e2e, `frontend/e2e/equipment.spec.js`, targeted)

Set-up per test by API: `propertySetup(propertyTag(testInfo), …)` (its own class, model and
machine at SMTW.MCC1, the three projects on one database); `noModelPart` for a component-unit.

- **Important.** The engineer opens a machine whose model gives *Rated power* 7.5 kW, taps
  *Edit this machine's values* (the dialog fits, `expectDialogFits`; "Model: 7.5 kW" under the
  input), types 5.5 and saves. The card shows "5.5 kW · this machine" and the line "Values from
  model …, except those marked this machine."; the History card shows "Property: Rated power:
  model value → Rated power: 5.5 kW".
- The engineer clears it: the card shows 7.5 kW again with no mark.
- A model-less component-unit: only *Edit this machine's values* shows; a saved value shows.
- The operator sees no *Edit this machine's values*; nor does anyone on a scrapped machine.
- A refusal (a number with five decimals) shows under its input (`expectFieldMessage`).

The coder runs `equipment.spec.js`, `masters.spec.js` (the freeze) and `screens.spec.js`
(targeted: no shared frontend code changes).

### 8.5 On a real device

None. The dialog and the card are the same parts as S043's, checked by the e2e run on the
three projects.

### 8.6 Acceptance

The important e2e test green on the three projects; all suites green; the schema docs at v33.

## 9. Open questions and assumptions

1. **Own values on a model change** (§ 1.7, decision 4). **Proposed:** kept. Alternative:
   cleared, with a history line each — fits a "wrong model, start again" fix, but loses a
   real nameplate on a filing correction.
2. **Equal to the model's value** (decision 3). **Proposed:** kept as the item's own.
   Alternative: dropped as no override (S038's rule), so the item follows later model edits.
3. **A class change** (§ 1.7). **Proposed:** hidden, kept. Alternative: deleted, with a
   history line.
4. **The words** (assumption): *Edit this machine's values*, "· this machine", "Values from
   model <model>, except those marked this machine.", "Model: <value>", "Model: no value",
   "<property>: model value". *Machine* is the word S038 uses on node meters ("set on this
   machine"); a component-unit is called a machine there too.
5. **Standards numbers** (to verify): ISO 14224 clause 8 Table 5; ISO 55001 § 7.5; ISO 9001
   § 7.5.3.

## 10. Amendments

None.

## Review log

### U1 — from S043, 24-10-2026

- An override on an equipment item is logged in the equipment's history (S043 U2).
- Split from S043; reuses `PropertyInput.vue` and the card (S043 § 4.5, the queued item).
