```
Step: S038 — Meters on models and equipment
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: full
Status: Gate B (CR r2: 0 blocker, 0 major; r1–r2 findings fixed; CR1-01 kept as built by the user, U5)
Baseline: e451c33 + uncommitted S035, S036, S041, S042, S037 (coded, gate B; built with no departure from its brief — stale check 24-10-2026: S038 holds)
```

# S038 — Meters on models and equipment

**The need (KLA, 24-10-2026).** "Meter link to equipment model / equipment."
Second of the three meter steps. S037 builds the catalogue of meter types; this
step puts meter types on **models** and on **nodes**, with gauge limits; S039
records readings, and S040 the end-of-day sheet.

User answers (U1, 24-10-2026):
- meters are defined on the **model**, and every equipment of that model has
  them; an equipment may **add its own** meters; readings are per equipment;
- gauge limits (min / max) live on the **model's meter** as defaults, and one
  equipment may **override** them.

User answers (U2, 24-10-2026, after round 1): **every level** of the tree may
carry meters (§ 9.1 settled).

Built on e451c33 plus S037 (v29, `meter_types`), which is approved and coded
before this step. This step's migration is **v30**; S039 (v32; v31 went to S043, 24-10-2026) depends on it.

## 1. What will be built

1. **A model's meters.** In Masters › Models, each model row gets a *Meters*
   button. It opens the model's meters **in the panel**, in place of the models
   table, as the model's documents do today (`ModelsPanel.vue`, `documentsFor`:
   "Not a dialog, because the cards open dialogs of their own"; BR1-01): a
   header with the model's name and the back link "← Models" (as the
   documents view, `ModelsPanel.vue:98`; BR2-04), *Add meter* above the list, and per
   meter its type (name and unit), kind, what a good reading is (below) and,
   for editors, *Set limits* (gauges) and *Remove*. *Add meter* and *Set
   limits* open one dialog, `ModelMeterFormModal.vue` (a `FormModal`): the
   meter type select (on add only; active types not yet on the model; each
   option shows the kind, and the unit when there is one: "Oil temperature
   (°C, Gauge)", "Oil level above min (Yes / No)"; BR3-05) and, for a gauge,
   **Min** and **Max** (each optional).
   **What a good reading is, by kind** (BR3-01): a gauge shows its limits text;
   a counter and an amount show no limits line (`limits_text` is `null`); a
   Yes / No meter shows "Expected: Yes" or "Expected: No", a label built in
   `meterLabels.js` from `meter_type.expected_answer` (the rule stays on the
   type, S037 decision 7). "Remove" sets the row inactive, so history
   (S039 readings) never loses its meaning. Empty states (BR1-19): "No
   meters." with *Add meter* for editors; when every active type is on the
   model already, the select is replaced by "Every meter type is on this
   model already. Add meter types in Masters › Meter types."
2. **A node's meters are its model's meters plus its own.** On the equipment
   page, a *Meters* card lists, for the node:
   - every **active meter of its model** (none for a component-unit without a
     model, S033), marked "From the model";
   - every **own meter** added on this node, marked "This machine only";
   - for each: name, unit, kind, and for a gauge the limits **in force**: this
     node's override when set, else the model's, shown as "Limits: 10–60 °C",
     "Limits: up to 60 °C", "Limits: from 10 °C" or "No limits". A counter
     and an amount show no limits line; a Yes / No meter shows "Expected: Yes"
     or "Expected: No" in its place (BR3-01, as § 1.1).
   Any level may carry meters (U2). Examples from Maintenance-Philosophy § 8
   (BR1-09): an alternating pump (a component-unit) has its own hour meter,
   because it runs only half the time; a die (a component with a serial) has
   its own strokes. A gearbox does **not** need one: its oil change runs on the
   extruder's hours (Plant-Facts line 117), and a PM plan names the ancestor's
   meter (phase 4). Empty state (BR1-19): "No meters." with *Add meter* for
   editors.
3. **Changes on a node** (engineer and up, IT admin: `equipment:edit` at the
   node's site), from the card:
   - **Add meter**: an active meter type that is not already on the node (from
     the model or its own), the select's options showing kind and unit as in
     § 1.1 (BR3-05); for a gauge, optional limits;
   - **Set limits** on a gauge from the model: the override min and max; *Use
     the model's limits* clears the override. It sits in the dialog's
     `#footer-left` slot (`FormModal.vue:177`, where the masters put
     `ActiveToggle`), apart from *Save*, and shows only when `overridden`
     (BR2-09);
   - **Set limits** on an own gauge;
   - **Remove** an own meter (inactive). A meter from the model cannot be
     removed on one node: the help says "Comes from the model <designation>.
     Remove it in Masters › Models, or change this machine's model."
   - **Remove asks first** (BR1-07), inline, as the documents' remove, but
     with the buttons *Remove* / *Keep* instead of the documents' *Yes* / *No*:
     a verb that names the result (scope B; a deliberate departure, BR2-05). On a
     node, "Remove Oil temperature from this machine? Readings stay in
     history." [*Remove*] [*Keep*]; on a model, "Remove Oil temperature from
     Atlas Copco GA37? Every machine of this model loses it. Readings stay in
     history." [*Remove*] [*Keep*].
   - *Add meter*'s picker when every active type is in force on the node:
     "Every meter type is on this machine already. Add meter types in Masters ›
     Meter types." (BR1-19).
4. **History.** Each change on a node writes an `equipment_events` line:
   *meter added* "Oil temperature", *meter removed* "Oil temperature", *meter
   limits* "Oil temperature: 10–60 °C → up to 55 °C" (§ 5.5). Changes on a model are
   not in a node's history (models have no history, S012).
5. **Meter types freeze once used.** S037's kind, unit, decimals and
   expected answer (Yes / No types, U3) can no longer change once any model
   meter or node meter (active or not) uses the type: 409 "This meter type is
   in use. Its kind, unit, decimals and expected answer cannot change. Make a
   new meter type." Name and active stay editable.
6. **Model change on a node** (S012, S033): the node's meters follow the new
   model at once. Own meters and overrides stay. An override whose meter type is
   not on the new model has no effect and is not shown; it comes back if the
   model returns. Readings of a meter no longer on the node stay in history
   (S039).

### Out of scope

- Readings (S039), and showing the last reading on the card (S039).
- Limits on counters, amounts per period and Yes / No meters (U3). A counter
  triggers PM every N units (phase 4), not on a limit; an amount is a
  quantity produced, not a condition; a Yes / No meter's good answer is fixed
  on its type (S037 decision 7). Limits are for gauges only.
- Two meters of one type on one node. A machine with two motors carries each
  motor's run hours on the motor's own node (component-unit).
- Copying a model's meters to each node (decision 1).

## 2. Standards and practice

- **ISO 14224 equipment data** (clause 8, to verify against the user's copy):
  data that hold for every unit of a model belong to the model, and unit data
  (serial, installation) to the unit. A model's meter list is model data; one
  press's tighter limit is unit data.
- **EN 13306 condition-based maintenance and condition monitoring** (term
  numbers to verify): a gauge with limits is the measured condition; crossing a
  limit is the signal to act. This step sets the limits; S039 flags readings
  outside them; raising the job on a crossing waits for phase 4 (Plan.MD § 8).
- **ISO 55001 § 7.5 (information requirements)**: a limit change is recorded
  with who and when, so a limit is traceable.
- **TPM autonomous maintenance, the visual standard** (BR1-23): the limits on
  the machine's card are the range the operator checks the gauge against, as a
  green band on a dial. S039 turns that check into a recorded reading.

## 3. Where

### Backend

- `backend/local_db.py`: migration v30 (§ 4).
- `backend/meters_core.py` (new, pure): `validate_limits(body, kind, decimals,
  stored)` (§ 5.1), `effective_meters` (§ 5.2), `limits_text` (the history
  and card wording, the one source of it; BR1-08), `tracked_meter_change(type_name,
  unit, old_limits, new_limits)` → the `(event, old_value, new_value)` tuples
  for `_write_events` (BR1-12).
- `backend/meters.py` (new blueprint, registered with `url_prefix="/api"` as
  `documents_bp` is, `app.py:177`; paths in § 6): the node meter routes; uses `load_node_for_user` and the LOCK ORDER of
  `equipment.py`.
- `backend/masters.py`: the model meter routes; the meter type update gains the
  in-use check (§ 5.3); the LOCK ORDER docstring gains model → meter type.
- `backend/equipment.py`: the LOCK ORDER docstring gains (1) node → (4b) meter
  type; `_detail` unchanged (the card loads its own list, § 6);
  `SCRAPPED_MESSAGE` defined here (the literal is at `equipment.py:758`) and
  imported by `documents.py` and `meters.py`, so a meters module does not
  depend on the documents module for an equipment rule (BR1-16).
- `backend/documents.py`: imports `SCRAPPED_MESSAGE` from `equipment.py`
  instead of defining it (line 85); one line.
- `validate_meter_type` (`masters_core.py`, S037) is unchanged; the in-use rule
  is in the shell (BR1-11).
- `backend/app.py`: register the blueprint.

### Frontend

- `frontend/src/views/masters/ModelsPanel.vue`: the *Meters* button and the
  in-panel meters view (`metersFor`, as `documentsFor`; BR1-01).
- `frontend/src/views/masters/ModelMeterFormModal.vue` (new): add and *Set
  limits* for a model meter.
- `frontend/src/views/equipment/MetersCard.vue` (new) and
  `frontend/src/views/equipment/NodeMeterFormModal.vue` (new).
- `frontend/src/views/EquipmentDetailView.vue`: the card after the Details /
  Parts row (line 220–247 block), before *Notes* (BR1-13).
- `frontend/src/utils/meterLabels.js` (new): the four kind labels
  (*Counter*, *Gauge*, *Amount per period*, *Yes / No*, S037 § 9.1), the
  source words ("From the model", "This machine only") and the expected-answer
  label ("Expected: Yes" / "Expected: No"; BR3-01). The limits text comes from
  the API (BR1-08).
- `frontend/src/views/masters/MeterTypesPanel.vue` (S037): its *Kind* column
  and radios read the kind labels from `meterLabels.js`, so the words live
  once (BR3-04).
- `frontend/src/utils/equipmentLabels.js`: the three new event names.

### Tests

- `backend/tests/test_meters_core.py` (new), `backend/tests/test_meters_api.py`
  (new), `backend/tests/test_models_api.py` (model meters),
  `backend/tests/test_meter_types_api.py` (the in-use freeze),
  `backend/tests/test_migration_v30.py` (new).
- `backend/tests/conftest.py`: `node_meters`, `model_meters` join `_TABLES`
  (first; `_TABLES` cleans with `FOREIGN_KEY_CHECKS = 0`). `meter_types` is in
  `_SEEDED_TABLES` since S037, not in `_TABLES` (S037 BR1-13).
- `frontend/tests/meterLabels.test.js` (new): the kind labels and source
  words.
- `frontend/tests/equipmentLabels.test.js`: `describeEvent` for the three new
  events (BR1-21).
- `frontend/e2e/equipment.spec.js` and `frontend/e2e/masters.spec.js` (§ 8).

### Docs (housekeeping, by the coder)

The docs pass (`.claude/CLAUDE.md` § Docs to keep current), in this step:

- `docs/schema.md` and `docs/schema.html`: `model_meters`, `node_meters` and
  the three new `equipment_events` values (v30), by hand from the migration
  text: the table rows, the Mermaid overview, the Equipment tab, the links to
  `equipment_models`, `equipment` and `meter_types`, and the "migration v30"
  line.
- `docs/Plan.MD` § 4.1 (a node's meters on its page) and § 4.5 (meters on the
  model, overrides, own meters): what was built. The gate A decisions are
  already recorded there.

## 4. Data model (migration v30)

```sql
CREATE TABLE IF NOT EXISTS model_meters (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    model_id       INT NOT NULL,
    meter_type_id  INT NOT NULL,
    min_value      DECIMAL(14,3) NULL,
    max_value      DECIMAL(14,3) NULL,
    active         TINYINT(1) NOT NULL DEFAULT 1,
    created_at, created_by, updated_at, updated_by,      -- as every master
    CONSTRAINT uq_model_meters UNIQUE (model_id, meter_type_id),
    CONSTRAINT fk_model_meters_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
    CONSTRAINT fk_model_meters_type  FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    CONSTRAINT chk_model_meters_limits CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS node_meters (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id   INT NOT NULL,
    meter_type_id  INT NOT NULL,
    own            TINYINT(1) NOT NULL,   -- 1: added on this node; 0: an override of the model's meter
    min_value      DECIMAL(14,3) NULL,
    max_value      DECIMAL(14,3) NULL,
    active         TINYINT(1) NOT NULL DEFAULT 1,
    created_at, created_by, updated_at, updated_by,
    CONSTRAINT uq_node_meters UNIQUE (equipment_id, meter_type_id),
    CONSTRAINT fk_node_meters_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_node_meters_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    CONSTRAINT chk_node_meters_limits CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE equipment_events MODIFY event
    ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
         'meter_added','meter_removed','meter_limits') NOT NULL;
```

- The current ENUM is v25's (`local_db.py:729`); v30 appends three values, so
  no row changes.
- A counter, amount or Yes / No row's `min_value` / `max_value` stay NULL: a
  code rule (§ 5.1), since the kind is on `meter_types` (U3).
- An override row (`own = 0`) is deleted rather than kept when it would equal
  the model (*Use the model's limits*), so "an override exists" means "a limit
  differs" (§ 5.3, BR1-03). An `own = 1` row is never deleted; its `own` flag
  never changes after insert (BR1-04).
- No `_PRECONDITIONS` entry: new tables, and an ENUM widened at its end.
- `DECIMAL(14,3)`: up to 99,999,999,999.999, enough for a lifetime stroke or kWh
  count; 3 decimals is S037's `MAX_DECIMALS`.
- Rollback: the previous release ignores both tables; the ENUM keeps its new
  values, and the old `describeEvent` shows an unknown event as its raw name
  (`equipmentLabels.js:76`).

## 5. Rules

### 5.1 Validation (pure)

| Input | Result |
|---|---|
| `meter_type_id` missing, not an id | 400 "Pick a meter type" (`meter_type_id`) |
| `min_value` / `max_value` absent | the value in force before the write (`stored`, below) (BR2-01) |
| `min_value` / `max_value` explicit `null` | clears that limit (stored NULL) (BR1-03) |
| `use_model_limits: true` (node PUT) | clears the override (§ 5.3) |
| a limit that is a bool, a float, or a string that is not a decimal number, or with more decimals than the type allows | 400 "Enter a number with up to N decimals" (the field) (BR1-05); for a 0-decimal type, "Enter a whole number" (BR2-08) |
| a limit beyond ±99,999,999,999.999 | 400 "Enter a smaller number" (the field) |
| `min_value > max_value`, on the pair after the write (body merged over `stored`) | 400 "Min must not be above Max" (`max_value`) (BR2-01) |
| any limit sent for a counter | 400 "A counter has no limits" (the field) |
| any limit sent for an amount per period (U3) | 400 "An amount per period has no limits" (the field) |
| any limit sent for a Yes / No meter (U3) | 400 "A Yes / No meter has no limits" (the field) |
| an explicit `null` limit on a counter, an amount or a Yes / No meter | accepted: `null` is not "a limit sent" (a form that posts every field stays accepted; BR3-03) |
| Numbers | accepted as a decimal string ("62.5") or an integer; parsed with `Decimal(str(value))`, never `float`; returned as strings, as DECIMAL (BR1-05) |

The kind check runs before the number checks, so a counter with `"abc"` reads
"A counter has no limits", not "Enter a number …" (BR3-03).

`validate_limits(body, kind, decimals, stored)` is pure (BR2-01; the shape of
`validate_equipment(body, creating, this_year, stored)`, `equipment.py:760`).
`stored` is the limits pair in force before the write: the row's own limits;
for a first override on a node (no row yet), the model's; on a create, NULLs.
It merges the body over `stored`, checks the pair and returns the merged
pair, which the shell stores. The shell calls it after the locked reads of
the meter type (`kind`, `decimals`) and the row supply its inputs.

### 5.2 The meters of a node (`effective_meters`, pure)

Inputs: the model's active `model_meters` rows (none without a model), the
node's `node_meters` rows, each with its meter type. Output, ordered by meter
type name:

- each active model meter, with limits = the override row's when an active
  `own = 0` row of that type exists, else the model's; `source: "model"`;
- each active `own = 1` row; `source: "node"`;
- an `own = 0` row whose type is not an active model meter: left out;
- an `own = 1` row whose type is now also on the model, **active or not**:
  shown once, as the model's, with the node row's limits as its override (the
  model gained the type after the node did). Its row keeps `own = 1` (BR1-04).
  A removed own meter has NULL limits (§ 5.3), so no stale override appears
  (BR2-02).

On a write, the model id comes from the locked node row (`LOCK_EQUIPMENT`
returns `model_id`), not from a plain re-read (BR1-17).

### 5.3 Checks against the database

- **An inactive model** (BR2-03) may gain, change and lose meters: it stays
  on its equipment (S012, `masters.py:519`), and those machines still run.
  The model row is locked with `_lock_row` (404 when missing), not
  `_lock_active_parent`; the *Meters* button shows on inactive model rows
  too, as *Documents* does (`ModelsPanel.vue:145`).
- **Add a meter to a model:** the meter type active (locked); not already on the
  model: 409 "This model already has this meter" (`meter_type_id`), from the
  unique key; a removed (inactive) row of that type is reactivated with the sent
  limits instead of a new row. POST is the one way to reactivate; `PUT` takes
  `active: false` only (BR1-18).
- **Add a meter to a node:** the type active; not already in force on the node
  (from the model or own): 409 "This machine already has this meter"
  (`meter_type_id`); an inactive own row is reactivated (BR1-20).
- **`UNIQUE_KEY_ERRORS`** (BR1-15): `uq_model_meters` → (`meter_type_id`, "This
  model already has this meter"), registered in `masters.py` beside the others
  (`masters.py:48`); `uq_node_meters` → (`meter_type_id`, "This machine already
  has this meter"), in `meters.py`.
- **An override equal to the model** (BR1-03): a node `PUT` whose limits after
  the write equal the model's on both sides is not stored as an override: the
  `own = 0` row is deleted, as *Use the model's limits*; on an `own = 1` row
  both limits are set NULL and the row is kept (§ 4 never deletes it; BR2-02).
  So a limit in a row means a limit differs, and `overridden` in the node
  GET is true only then. Not refused: the
  engineer who types the model's numbers gets what they asked for.
- **Use the model's limits** (BR1-04): on an `own = 0` row, deletes the row; on
  an `own = 1` row (the model gained the type later), sets both limits NULL and
  keeps the row, so a later model change gives back the machine's own meter.
- **Limits on a model meter from a node:** the row is `own = 0`; refused when the
  type is not an active meter of the node's model: 409 "This meter is no longer
  on the model. Reload the page."
- **Remove an own meter:** `active = 0` and both limits NULL (BR2-02), so the
  row can never later act as a stale override. Removing a model meter on a
  node: 409 (text of § 1.3).
- **A limits write never changes `active`** (BR2-02). *Set limits* on a model
  meter whose type has an inactive `own = 1` row on the node writes the
  limits into that row (the unique key allows no second row) and leaves it
  inactive: a removed own meter stays removed after a later model change.
- **Meter type in use** (§ 1.5): under the meter type's lock, a count of
  `model_meters` and `node_meters` rows of the type, active or not, both
  `LOCK IN SHARE MODE`, as `_check_code_frozen` (`masters.py:638`) does
  (BR1-02). A "change" is a merged value that differs from the stored one,
  as `_check_code_frozen` decides (`"code" in clean and clean["code"] !=
  locked["code"]`; BR3-02): a `PUT` from the edit dialog that re-sends the
  same kind, unit, decimals and expected answer passes, so name and active
  stay editable in practice.
- **A deactivated meter type** stays in force where it is linked; it is only not
  offered for new links (S037 § 1.1).
- **A scrapped node** is read-only (S017): every node meter write → 409, as the
  documents do: 409 "This record is scrapped and cannot be changed"
  (`SCRAPPED_MESSAGE`, now in `equipment.py`, reused; BR2-06), decided from the locked node
  row. `load_node_for_user` (`equipment.py:303`) gives 404 for a node outside
  the user's units and 403 without the key at its site; it has no scrapped check.

### 5.4 Locks

The global order of `equipment.py` gains one step, (4b) the meter type row,
after (4) the model and before (5) the class:

- **Node meter add / limits / remove:** (1) the node row (`load_node_for_user`
  with `for_update`, key `equipment:edit`, its site check) → (4b) the meter type
  row `FOR UPDATE` (active check, kind) → the `node_meters` row (insert, or
  `SELECT … FOR UPDATE` by its unique key). The model's meter rows are read
  plainly after (1): they change only under the model's lock, and a race only
  shows a stale "from the model" until reload (the write itself checks against
  what it read; accepted, § 7 decision 6).
- **Model meter add / edit / remove** (`masters.py`): (4) the model row → (4b)
  the meter type row → the `model_meters` row. Manufacturer → model → class →
  type is unchanged; (4b) sits after model, and no model meter write takes a
  class or type.
- **Meter type update** (`masters.py`): the meter type row `FOR UPDATE`, then
  the two counts `LOCK IN SHARE MODE` (BR1-02). A locking read sees the latest
  committed rows, whatever plain read came earlier in the transaction
  (REPEATABLE READ fixes the snapshot at the first plain read, so a plain count
  could miss a link committed during the lock wait). The share locks fall on
  link rows, which only link writes touch, after their own type lock: no
  cycle.
- No path takes (4b) then (1) or (4): no cycle. `documents.py` and `tickets.py`
  take no meter lock.

### 5.5 History

- Node writes write their `equipment_events` line in the same transaction
  (`_write_events`, `equipment.py:421`). A rollback writes none.
- Text: `meter_added` new_value "Oil temperature"; `meter_removed` old_value
  "Oil temperature"; `meter_limits` old "Oil temperature: 10–60 °C" new
  "Oil temperature: up to 55 °C" (`limits_text`). Both sides always show the
  limits **in force**: setting an override writes old = the model's values,
  new = the override; clearing it writes the reverse (BR1-06). `describeEvent`
  reads "Meter limits: Oil temperature: 10–60 °C → up to 55 °C".
- Each side is at most 60 (name) + 2 + 2 × 18 (numbers) + 3 + 20 (unit) ≈ 125
  characters; `old_value` and `new_value` are `VARCHAR(200)`
  (`local_db.py:350`), so the texts fit.

### 5.6 Reads

- `GET` of a node's meters needs `equipment:read` at the node's site
  (`load_node_for_user` without lock). Unit access as every node read.
- `GET` of a model's meters needs `masters:read`.

### 5.7 The database down

Every route → 503 (`DBUnavailable`); the card shows "Meters could not be
loaded", as the tickets card (`EquipmentDetailView.vue:197`).

## 6. API

| Method | Path | Key | Body | Response |
|---|---|---|---|---|
| GET | `/api/masters/equipment-models/<id>/meters` | `masters:read` | — | `[{id, meter_type: {id,name,unit,kind,decimals,expected_answer}, min_value, max_value, limits_text, active}]` (`limits_text` null for a non-gauge; BR3-01) |
| POST | `/api/masters/equipment-models/<id>/meters` | `equipment:edit` | `meter_type_id, min_value?, max_value?` | 201, the row (BR1-18) |
| PUT | `/api/masters/model-meters/<id>` | `equipment:edit` | `min_value?, max_value?, active: false?` | 200, the row |
| GET | `/api/equipment/<id>/meters` | `equipment:read` at site | — | `[{meter_type, source, min_value, max_value, model_min, model_max, overridden, limits_text, model_limits_text}]`, `meter_type` as in the model GET, with `expected_answer` (§ 5.2; BR1-03, BR1-08, BR3-01) |
| POST | `/api/equipment/<id>/meters` | `equipment:edit` at site | `meter_type_id, min_value?, max_value?` | 201, the list |
| PUT | `/api/equipment/<id>/meters/<meter_type_id>` | `equipment:edit` at site | `min_value?, max_value?, use_model_limits?, active: false?` (BR2-07) | 200, the list |

The node routes live in `meters.py` under `/api/equipment/...`, as
`documents.py` serves node documents beside `equipment.py` (`app.py:177`).

## 7. Design decisions

1. **Live inheritance, not copies** (U1). A node's meters are computed from its
   model each time. Adding "Oil temperature" to a press model gives all ten
   presses the meter at once. Rejected: copying the model's meters into each
   node (ten writes per model change, and copies drift).
2. **One `node_meters` table for own meters and overrides** (`own` flag).
   Rejected: two tables (two lock targets, two unique keys for one rule "one
   meter of a type per node").
3. **Identity = (node, meter type).** S039's readings key on it. Rejected: an
   id per inherited meter (it would need the copies of decision 1).
4. **Remove = inactive.** Readings (S039) keep their meter's name and unit.
5. **Kind, unit, decimals and the expected answer freeze once used.** A
   changed unit would re-label every past reading; a flipped expected answer
   would turn every past *OK* into *Not OK* (U3). Rejected: a free edit.
6. **Plain read of the model's meters on a node write.** The node write locks
   the node and the meter type; locking the model too would put (4) inside every
   node meter write for a stale-display race only.
7. **Model meters edited in Masters, node meters on the equipment page.** Each
   where its owner already edits (models: Masters; machines: their page).

## 8. Tests and acceptance

### Backend (pytest)

- `test_meters_core.py`: every row of § 5.1 (including a bool, a float, "abc",
  "62.55" on a 1-decimal type, `null`, "Enter a whole number" on a 0-decimal
  type); `validate_limits` from each `stored` start point: a row, the model's
  limits (a first override), NULLs (a create), and a one-sided update against
  a stored other side (BR2-01); `effective_meters` for each case of
  § 5.2 (no model; override; stale override; own; own later also on model;
  inactive rows); `limits_text`'s four wordings, and `null` for a counter, an
  amount and a Yes / No meter (BR3-01); a counter with `"abc"` reads "A
  counter has no limits" and an explicit `null` on it passes (BR3-03);
  `tracked_meter_change` for set and clear of an override (both sides in
  force).
- `test_models_api.py`: add, edit limits, remove, reactivate a model meter;
  counter with limits → 400; amount and Yes / No with limits → 400 (U3); inactive type → 409; duplicate → 409; operator →
  403.
- `test_meters_api.py`: a node's list (model + own + override); add own; set and
  clear an override; an override equal to the model leaves no row and
  `overridden: false`; *Use the model's limits* on an own meter the model
  later gained keeps the row with NULL limits; remove own clears its limits;
  *Set limits* on a model meter whose type has an inactive own row writes that
  row and leaves it inactive; an override equal to the model on an own row
  keeps the row with NULLs (BR2-02); meters added to an inactive model
  (BR2-03); remove a model
  meter → 409; another site's
  engineer → 403; storekeeper read at its unit; scrapped → 409; an event line per
  write and none on a refused write; a model change on the node changes the list.
- `test_meter_types_api.py`: the freeze (§ 1.5) with an inactive link too, and of a Yes / No type's expected answer (U3); name
  still editable; a `PUT` re-sending the same kind, unit and decimals on a type
  in use passes (BR3-02). The test makes its own meter type (S037's seed rule).
- `test_migration_v30.py`: from v29; the ENUM keeps every old event row.
- `test_rbac.py`: unchanged (no new key).

### Automated (e2e)

- **Important.** `masters.spec.js`: "S038: engineer adds Oil temperature with
  limits to a model" (the in-panel view opens, the dialog fits a phone, "← Models"
  returns to the models).
- `equipment.spec.js`: "S038: the press page shows its model's meters and an
  own meter".
- **Important.** `equipment.spec.js`: "S038: engineer overrides a limit and
  the history shows it" (the dialog fits; the history line reads both sides).
- `equipment.spec.js`: "S038: removing an own meter asks first" (the inline
  confirm, then *Remove*).
- `equipment.spec.js`: "S038: an operator sees the Meters card without edit
  buttons".
- `frontend/tests/meterLabels.test.js`: the Yes / No label "Expected: Yes" /
  "Expected: No" (BR3-01).
- **Models the e2e tests use** (S039 BR3-03): this step's e2e tests give
  meters to models other than `SMTW-HYP-01` (the hydraulic press model,
  `seed_dev.MODELS`), which S039's e2e set-up keeps for its own machines.

### On a real device

None.

### Acceptance

A model with two meters gives each of its machines both; one machine adds a
third and tightens a limit; the history shows both changes.

## 9. Open questions and assumptions

1. **All levels may carry meters**: settled by the user (U2, 24-10-2026),
   with the examples of § 1.2 (BR1-09).
2. **The words** (assumption): *Meters*, *Add meter*, *Set limits*, *Use the
   model's limits*, *Remove*, *Keep* (not *Yes* / *No*, BR2-05), "From the model", "This machine only",
   the four limits wordings of § 1.2, the two remove confirmations and the
   empty states of § 1.1–1.3.
3. **Who edits a model's meters**: `equipment:edit` (engineers), as models
   (S012). Settled (U4, D6).
4. **Standards numbers** (to verify): ISO 14224 clause 8; EN 13306 terms.
5. **Size** (BR1-10): the facts run counts about 25 files with this round's
   additions (two concerns: a model's meters in Masters, about 8 files; a
   node's meters on the equipment page with history). Proposed: **keep one
   step**. The migration (both tables), `effective_meters`, `limits_text` and
   the freeze are shared, and the node card is empty without model meters.
   The cut, if the user wants it: S038a = v30, the model meters, the freeze;
   S038b = the node routes, the card, history (no migration). Settled: one
   step (U4, D1).

## 10. Amendments

None.

## Review log

### U1 — user answers, 24-10-2026 (before drafting)

- Meters defined on the model, every equipment of the model has them; an
  equipment may add its own; readings per equipment.
- Gauge limits on the model's meter, overridable per equipment.
- S039 builds per-equipment entry and an end-of-day sheet.

### U2 — user answers, 24-10-2026 (after round 1)

- Every level of the tree may carry meters (§ 9.1).
- For S039 and S040: operator and up log readings, not IT admin; a fixed
  7-day back-date window; the end-of-day sheet is its own step, S040.

### U3 — user comments on the review page, 24-10-2026

- A third meter kind, `amount` (*Amount per period*, e.g. *Shift production*;
  S037). It carries no limits: `validate_limits` refuses limits for it as for a
  counter (§ 5.1, § 4). Limits stay for gauges only.
- A fourth kind, `yes_no` (*Yes / No*, S037): no limits either; its expected
  answer is on the type and joins the freeze of § 1.5.
- ISO 4406 removed from § 2 (with the oil-sampling plan, phase 4).

### U4 — approval, 24-10-2026

- "I have reviewed the brief. Except what I changed above, it all is
  accepted. Implement." Approved by KLA.
- D1: keep S038 as one step (§ 9.5 settled). D6: `equipment:edit` edits a
  model's meters (§ 9.3 settled). D11: the words of § 9.2. D12: the clause
  numbers stay "to verify".

### Round 1 — `2-brief-review-r1.md` (Fable), answered 24-10-2026

1 major, 9 minor, 13 nits.

| Finding | Answer |
|---|---|
| BR1-01 major — one dialog lists, adds, edits and removes | Accepted (a): the in-panel view as `documentsFor`, one `ModelMeterFormModal` for add and *Set limits*; § 1.1, § 3 |
| BR1-02 minor — plain in-use count | Accepted (a): both counts `LOCK IN SHARE MODE`, as `_check_code_frozen`; § 5.3, § 5.4 |
| BR1-03 minor — `null` on a limit; no override flag | Accepted: `null` clears a limit; `overridden` and the limits texts in the node GET; an override equal to the model is stored as no override (row deleted), not refused; § 5.1, § 5.3, § 6 |
| BR1-04 minor — own meter the model later gains | Accepted (a): `own` never changes; *Use the model's limits* clears an own row's limits and keeps it; § 4, § 5.2, § 5.3 |
| BR1-05 minor — strings vs numbers in § 5.1 | Accepted (a): rows reworded; `validate_limits(body, kind, decimals, creating)`; § 5.1 |
| BR1-06 minor — the history text | Accepted (a): both sides show the limits in force; length checked; § 5.5 |
| BR1-07 minor — *Remove* without confirm | Accepted (a): inline confirm, the two texts; § 1.3 |
| BR1-08 minor — limits wording in two places | Accepted (a): the API returns `limits_text`; `meterLabels.js` keeps kinds and sources; § 3, § 6 |
| BR1-09 minor — the gearbox example | Accepted (a): the alternating pump and the die; § 1.2, § 9.1 |
| BR1-10 minor — size and the cut | Accepted (a): keep one step, the cut named; deferred to gate A — user; § 9.5 |
| BR1-11…BR1-23 nits | All accepted. BR1-11: `masters_core.py` out of *Where*. BR1-12: `tracked_meter_change` described. BR1-13: the card before *Notes*. BR1-14: `ENGINE=InnoDB`. BR1-15: the `UNIQUE_KEY_ERRORS` entries. BR1-16: `SCRAPPED_MESSAGE` moves to `equipment.py`. BR1-17: model id from the locked row. BR1-18: POST returns the row; PUT only deactivates. BR1-19: empty states. BR1-20: "already has". BR1-21: `equipmentLabels.test.js`. BR1-22: two checks marked important. BR1-23: the TPM visual standard. |

From S037's review: S037 BR1-13 (`meter_types` in `_SEEDED_TABLES`, not
`_TABLES`) fixed in § 3.

### Round 2 — `2-brief-review-r2.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 3 minor, 6 nits. Review loop complete.

| Finding | Answer |
|---|---|
| BR2-01 minor — a one-sided limits update unchecked by the pure function | Accepted (a): `validate_limits(body, kind, decimals, stored)`; `stored` = the row, else the model (first override), else NULLs; the merged pair is checked and stored; § 3, § 5.1, § 8 |
| BR2-02 minor — an inactive own row of a type the model gains | Accepted (a): Remove clears both limits; a row of a model type holds the override, active or not; a limits write never changes `active`; equal to the model on `own = 1` → NULLs, row kept; § 5.2, § 5.3, § 8 |
| BR2-03 minor — meters on an inactive model | Accepted (a): allowed, `_lock_row`, the *Meters* button on inactive rows; § 5.3, § 8 |
| BR2-04…BR2-09 nits | All accepted. BR2-04: "← Models". BR2-05: *Remove* / *Keep* is a deliberate departure from *Yes* / *No*. BR2-06: `SCRAPPED_MESSAGE` in `equipment.py`. BR2-07: `active: false?`. BR2-08: "Enter a whole number" at 0 decimals. BR2-09: *Use the model's limits* in `#footer-left`, only when overridden. |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 1 minor, 4 nits. Re-read the U3 sections only.

| Finding | Answer |
|---|---|
| BR3-01 minor — what a non-gauge meter shows in the unit and limits places | Accepted (a): `limits_text` null for counter and amount; "Expected: Yes / No" from `meter_type.expected_answer` in `meterLabels.js`; `expected_answer` in both GETs; tests; § 1.1, § 1.2, § 3, § 6, § 8 |
| BR3-02…BR3-05 nits | All accepted. BR3-02: "change" = a merged value differing from the stored one, as `_check_code_frozen`. BR3-03: explicit `null` is not a limit sent; the kind check first. BR3-04: the four kind labels in `meterLabels.js`, read by S037's panel. BR3-05: kind and unit in each select option. |

From S039's review round 3: S039 BR3-03 — this step's e2e tests keep off the
`SMTW-HYP-01` model (§ 8).

### U5 — gate B answer, 24-10-2026

- CR1-01 (an own meter added over a stale override deletes the override): the user said "ignore it". Kept as built; no change to code or docs.
