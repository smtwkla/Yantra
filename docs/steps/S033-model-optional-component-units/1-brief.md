```
Step: S033 — Model optional on component-units
Doc: brief
Author: Planner (Opus)
Date: 23-10-2026
Track: full
Status: Done (committed c9234ce; checks: 3 auto; approved 24-10-2026 by KLA; open questions 1–3 accepted as written)
Baseline: 6ab6af0 (nothing of a step uncommitted; stale check 24-10-2026: no change since)
```

# S033 — Model optional on component-units

**The need (KLA, 23-10-2026).** "We need a step for 'model optional on
component-units'." Since S012 (decided 17-10-2026) every node needs a model,
and the node's class and type come from the model. For many component-units
(a gearbox, a motor or a pump inside a machine) nobody knows the maker and
model, and there is nothing to gain from inventing one. Today the form then
says "Add a model in Masters › Models (a Generic one if the maker is
unknown)", so the register fills with placeholder models.

This step lets a **component-unit** have **no model**. Without a model, the
user picks its **class** (required, it gives the code prefix) and its
**type** (optional) directly. Equipment and components still need a model.

User answers before drafting (U1): class picked directly; component-units
only; existing data left as it is.

Built on 6ab6af0 (S032 committed as b100494, migration v27). This step's
migration is **v28**.

## 1. What will be built

1. **The rule.** A node of level `component_unit` may have no model. A node
   of level `equipment` or `component` must have one, as today. The database
   holds the rule as well (§ 4).
2. **With a model** (every level): unchanged. Class and type come from the
   model and are shown, not picked (S012 § 5.3).
3. **Without a model** (component-units only): the user picks
   - **Class**: required, an active class when newly picked; an unchanged
     inactive class is kept, as for models (§ 5.2);
   - **Type**: optional, an active type of that class when newly picked;
     same rule.

   The code prefix comes from the class at creation, as today. A later class
   change keeps the code, as today (S012: "A model of another class later
   keeps the code").
4. **Changing between the two** on an existing component-unit:
   - **model → no model:** the form keeps the class and type the node had;
     the user may change them in the same save; the history gets a *model*
     line "`<old model>` → No model";
   - **no model → model:** class and type come from the model, as today;
     the history gets *model*, and *class* / *type* lines when they change.
5. **The form** (`EquipmentFormModal.vue`, Scope B), with this contract
   (BR1-02):
   - **The choice.** For a component-unit, the *Model* select gets a first
     option **No model**, with the value `NO_MODEL = "none"` (a constant in
     `modelPicker.js`). The disabled placeholder "Select a model…" (`""`)
     stays for every level. For equipment and components, *No model* is not
     offered.
   - **The fields.** Whenever `form.model_id` is `NO_MODEL`, the class
     filter is hidden and two fields show under *Model*: **Class**
     (required; "Select a class…", then the active classes) and **Type**
     ("No type", then the active types of the picked class). Help text:
     "Without a model, the class sets the code prefix. A later class change
     keeps the code." (BR3-04), which replaces the
     line "The model's class sets the code prefix. A model of another class
     later keeps the code." (`EquipmentFormModal.vue:237`) while *No model*
     is picked (BR2-05). On edit, an
     unchanged inactive class or type stays listed, marked "(inactive)", as
     `modelChoices` does for a model.
   - **Defaults.** Picking *No model* prefills *Class* with the class filter's
     value when one is set (BR1-14), else with the node's current class on
     edit; *Type* starts at the node's current type on edit, else "No type".
   - **Resets.** Changing *Class* resets *Type* to "No type". Switching
     *Level* (the *Add part* dialog) from component-unit to component while
     *No model* is picked sets *Model* back to the placeholder.
   - **The body** (`toBody`):
     - `""` (nothing picked): `model_id`, `class_id` and `type_id` are all
       left out (BR3-01). On create the backend
       then answers "Pick a model" on `model_id`, which is on screen (§ 5.1).
       On edit `""` cannot occur (the placeholder is disabled and an edit
       starts with the node's value);
     - `NO_MODEL`: `model_id: null`, `class_id` (`null` for the placeholder
       "Select a class…", so the backend's "Pick a class" is the one text,
       BR2-02), and `type_id` (`null` for "No type");
     - a model id: `model_id` only, never `class_id` / `type_id`.
   - **Form keys** (BR2-03): `class_id` and `type_id` are keys of the form
     object in every state (`COMMON_BLANK`, `fromRecord`); `toBody` drops
     them when a model is picked. So `useFormModal` puts "Pick a class"
     beside its field and not also at the top (`useFormModal.js:52–54`).
   - **Loading** (`fromRecord`): a node with `model_id: null` loads as
     `NO_MODEL`, with its `class_id` and `type_id`.
   - **Hint.** "This class has no model yet. Add a model in Masters › Models
     (a Generic one if the maker is unknown)." reads, for a component-unit:
     "This class has no model yet. Pick No model, or add a model in Masters ›
     Models." The hint hides once *No model* is picked (BR2-04).
   - **Refusals.** "Pick a model" stays on `model_id`; "Pick a class" lands
     on the *Class* field, which is on screen whenever it can be sent.
6. **Screens that show the model** show **No model** or "—" for a node
   without one (§ 7.5):
   - the equipment page: *Model* "No model"; the *Manufacturer* line left
     out;
   - the equipment list's *Model* column and the asset list print
     (`AssetListPrintView.vue`): "—";
   - the equipment page's documents cards: no *model documents* card
     (`documents._inherited` already returns none, § 3).
7. **Search** in the equipment list keeps finding a node without a model by
   its other words (SQL `TRUE OR NULL` is TRUE; no change needed, BR1-09).
8. **The API** (§ 6): `model_id` may be `null` for a component-unit, with
   `class_id` and optional `type_id`.

### Out of scope

- Removing the placeholder models already in the register (U1: data left as
  it is). A user can clear the model of a **component-unit** by editing it;
  equipment and components with a Generic model keep it (BR1-12).
- No model on equipment or components.
- A manufacturer without a model ("ABB, model unknown"): not asked; a later
  step if wanted.
- Labels (QR): they do not show the model today (`labels_core.py`), so they
  do not change.

## 2. Standards and practice

- **ISO 14224 § 8 and Annex A (equipment hierarchy and data)** (BR1-03).
  ISO 14224 places the *subunit* (our component-unit, taxonomy level 7)
  under the *equipment unit* (level 6). Its equipment data (clause 8, Table
  5 "Equipment data (common data)": equipment class, type, manufacturer's
  name, manufacturer's model designation, …) describe the **equipment
  unit**. Annex A's per-class tables name subunits and maintainable items by
  their subdivision only, with no maker or model attribute. So the standard
  asks for a maker and model on the equipment unit, and neither asks for nor
  forbids them on a subunit. S012's "model on every node" went beyond the
  standard; this step brings the rule back to its shape: a model on
  equipment, a subunit identified by its class and name, a model when known.
  Table and clause numbers to verify against the user's copy.
- **ISO 55001 § 7.5 (information requirements)** (BR1-15). The organisation
  decides which asset attributes it needs and at what quality. For a subunit
  the class is needed (code, failure codes, reports); the maker and model
  are needed only when known.
- **Data quality (ISO 8000, plain practice).** A field that must be filled
  but whose value is not known gets filled with noise. An honest "No model"
  keeps the register's model data trustworthy for the BOM and spares work
  later (Plan.MD § 2, Not in v1).
- **Departure from S012** (decided 17-10-2026: "model required on every
  node"): stated here and recorded in Plan.MD § 4.1 at approval.

## 3. Where

### Backend

- `backend/local_db.py`: migration v28 (§ 4).
- `backend/equipment_core.py`:
  - `validate_equipment`: the rules of § 5.1; `stored` becomes `{code,
    level, model_id, class_id, type_id}` (BR1-06, BR1-01);
  - new messages `PICK_A_CLASS = "Pick a class"`, `CLASS_FROM_MODEL =
    "Class comes from the model"`, `TYPE_FROM_MODEL = "Type comes from the
    model"`, `PICK_A_TYPE_OF_CLASS = "Pick a type of the new class, or No
    type"`, `PICK_A_TYPE = "Pick a type"`;
  - `NO_MODEL = "No model"`, used by `_display` / `tracked_changes` when the
    model label is None (BR1-05), beside `NO_TYPE` and `INHERIT`;
  - the module docstring: "Every node has a model (S012)" becomes the new
    rule.
- `backend/equipment.py`:
  - `update_equipment` passes the stored `model_id`, `class_id`, `type_id`
    to the validator (from the locked row, `LOCK_EQUIPMENT` already reads
    them);
  - a write without a model locks the class with the existing `_lock_class`
    (messages unchanged: 400 "Unknown class", 409 "The class is inactive");
    its docstring ("the class of a newly picked model", "defence in depth")
    changes, as the active check is now a real rule for a directly picked
    class (BR1-04);
  - the type with `lock_type_of_class` (below), imported from `masters.py`;
  - `NODE_JOINS`: `equipment_models` and `manufacturers` become `LEFT JOIN`;
    the comment "Inner joins, as the class: every node has a model" changes;
  - the lock-order docstring gains (5a).
- `backend/masters.py`: `_lock_type_for_model` (`masters.py:467–477`)
  becomes public as `lock_type_of_class(cur, type_id, class_id)`, same body
  and messages (400 "Unknown type", 400 "This type belongs to another
  class", 409 "The type is inactive"); models keep calling it. `masters.py`
  does not import `equipment.py`, so there is no import cycle (BR1-04).
- `backend/masters_core.py`: `model_label(None, None)` → `None`.
- `backend/documents.py`: the node's inherited model documents
  (`_inherited`, line ~220) are skipped when the node has no model. It
  already returns none (`WHERE model_id = NULL` matches nothing); the skip
  is for clarity, not a fix (BR1-10).
- `backend/asset_list_core.py`: no change (it does not read the model; the
  asset list takes `model_label` from the node query).

### Frontend

- `frontend/src/views/equipment/EquipmentFormModal.vue`: § 1.5.
- `frontend/src/utils/modelPicker.js`: `NO_MODEL`; `modelChoices` gains the
  level (default: no *No model* choice, so existing callers are unchanged).
- `frontend/src/utils/equipmentLabels.js`: the comment "Every node has a
  model (S012), so neither side is ever empty" (`describeEvent`, lines
  72–74) changes; the values pass through as they are (BR1-05).
- `frontend/src/views/EquipmentDetailView.vue`: *Model* "No model", no
  *Manufacturer* line.
- `frontend/src/views/EquipmentView.vue`,
  `frontend/src/views/AssetListPrintView.vue`: "—" for no model.

### Tests

§ 8 names the tests, the existing ones that change and the new ones
(BR1-07).

### Docs (at approval, by the planner)

- `docs/Plan.MD` § 4.1 *Fields*: "model (required on every node …)" becomes
  "model (required on equipment and components; optional on component-units,
  whose class and type are then picked — S033)".
- `docs/schema.md`: the `equipment` row ("`model_id` (required)"); the
  coder regenerates `schema.md`'s overview and `schema.html` at v28 if the
  generator is in the repo by then, else the planner does it at gate B.

## 4. Data model (migration v28)

```sql
ALTER TABLE equipment MODIFY model_id INT NULL;
ALTER TABLE equipment ADD CONSTRAINT IF NOT EXISTS chk_equipment_model_level
    CHECK (model_id IS NOT NULL OR level = 'component_unit');
```

- Both statements checked on MariaDB 11.4.13 (dev image) on 23-10-2026:
  `MODIFY` keeps `fk_equipment_model (model_id, class_id)` in place, and the
  `ADD CONSTRAINT IF NOT EXISTS` runs a second time without error, so a
  half-applied v28 re-runs. Production MariaDB version: to verify (as in
  S031).
- `fk_equipment_model` stays: InnoDB skips a foreign key check when one of
  its columns is NULL (MATCH SIMPLE), so a node without a model passes, and
  a node with one still must match the model's class.
- `fk_equipment_type (type_id, class_id)` is unchanged and checks a directly
  picked type against the class.
- No `_PRECONDITIONS` entry: every existing row has a model (the column was
  NOT NULL), so the CHECK holds for all of them. The change only widens what
  a row may hold.
- Rollback to the previous release: the old code reads nodes through inner
  joins to the model, so a component-unit saved without a model vanishes
  from its lists, and an edit of it fails with 409 (`_reread` finds no row,
  BR1-16). A rollback after users saved such nodes needs those nodes to get
  a model first, or the db-server dump restored. Stated in the impl
  report's release notes.

## 5. Rules

### 5.1 Validation (`validate_equipment`, pure)

The validator gets the body and, on update, `stored = {code, level,
model_id, class_id, type_id}` (BR1-06).

**The model.**

| Case | Result |
|---|---|
| Create, `model_id` absent, any level | 400 "Pick a model" (`model_id`), reported first even when `class_id` / `type_id` are sent; those keys are then not reported (BR3-01). Only an explicit `null` means no model (BR1-06) |
| Create or update, `model_id: null`, level equipment or component | 400 "Pick a model" (`model_id`), as today |
| `model_id: null`, level component_unit | no model; the class rules below apply |
| `model_id` = an id | today's rule |
| Update, `model_id` absent | the stored model decides (`stored["model_id"]`) |

**Class and type with a model** (sent, or stored and not cleared): `class_id`
or `type_id` in the body → 400 "Class comes from the model" (`class_id`) /
"Type comes from the model" (`type_id`), even as `null` or unchanged (§ 7.4).

**Class and type without a model** (sent `null`, or stored NULL and not set):

| Case | Result |
|---|---|
| Create, or update with `model_id: null` on a node that had a model: `class_id` absent or `null` | 400 "Pick a class" (`class_id`) |
| Update of a no-model node: `class_id` absent | the stored class stays |
| `class_id: null` on a no-model node | 400 "Pick a class" (`class_id`) |
| The class after the write differs from the stored one (or create), and `type_id` absent | create: no type; update: 400 "Pick a type of the new class, or No type" (`type_id`) (BR1-01) |
| `type_id: null` | no type |
| `type_id` = an id | checked against **the class the row will hold after the write**: the sent `class_id`, else the stored one (§ 5.2) |
| Update: the class after the write differs from the stored one, and the sent `type_id` is an id equal to the stored type (not `null`, BR3-02) | 400 "This type belongs to another class" (`type_id`): the stored type is always of the stored class (the FK holds it), so it cannot be of the new one. Pure, no lock needed (BR2-01) |

So the database never receives a type of one class with a class of
another, and `fk_equipment_type` never answers 1452 (which
`api_common._integrity_error` would turn into a 500).

A `class_id` that is neither `null` nor an id (`"x"`, `""`, a bool, a
negative number) → 400 "Pick a class" (`class_id`); a `type_id` that is
neither `null` nor an id → 400 "Pick a type" (`type_id`, new constant
`PICK_A_TYPE`) (BR2-02). The user never sees a "must be a record id" text.

### 5.2 Checks against the database (`equipment.py`)

- **Newly picked** (BR1-06): a class or type that differs from the locked
  row's `class_id` / `type_id` (on create, every class and type). Only a
  newly picked one must be active; an unchanged inactive one is kept.
- The class (`_lock_class`): 400 "Unknown class", 409 "The class is
  inactive" (existing texts, BR1-04).
- The type (`lock_type_of_class`): 400 "Unknown type", 400 "This type belongs
  to another class", 409 "The type is inactive" (existing texts).
- The class of a new node without a model gives the code prefix through the
  same serial counter (6), as today.
- **Deactivating a class** (BR1-11) is not blocked by model-less
  component-units of that class: `update_equipment_class` counts active
  models only (`masters.py:338`), as a type's deactivation is not blocked by
  its equipment. The nodes keep the inactive class, and the "unchanged
  inactive class is kept" rule covers their edits. A U1 consequence,
  accepted.

### 5.3 Locks

The order of `equipment.py`'s docstring, with one new step after (5):

1. (1) the node's own row, (2) the target parent, (3) the unit — unchanged;
2. (4) the model row, only when a write newly picks a model — unchanged;
3. (5) the class row: the model's (today), or the directly picked one
   (new), `FOR UPDATE` as today. Without a model: on create always (the
   prefix), on update only when newly picked (BR1-06);
4. **(5a) the type row**, only when a write without a model newly picks a
   type: `lock_type_of_class`'s `SELECT id, class_id, active FROM
   equipment_types WHERE id = %s FOR UPDATE`;
5. (6) the serial counter, on create — unchanged.

`masters.py` locks class → type (types, failure modes) and manufacturer →
model → class → type (models), so class (5) before type (5a) keeps one
order across both modules; equipment rows still come first. A write with a
model never locks a type, as today (the model's type never changes, S012
§ 5.5).

### 5.4 History (`equipment_events`)

- Clearing the model: event `model`, old = the model label, new = `NO_MODEL`
  ("No model"), from `equipment_core` (BR1-05). Setting a model on a
  no-model node: old = "No model". When the class or type also changes in
  the same save, `class` / `type` lines follow, as today.
- Creating a node without a model: the `created` line as today.
- A class or type change on a node without a model: `class` / `type` lines
  as today.

### 5.5 Reads

- Every node query (`NODE_JOINS`) uses `LEFT JOIN` to the model and the
  manufacturer. `model_id`, `model_designation`, `manufacturer_name`,
  `model_label` are `null` for a node without a model.
- No other query joins `equipment_models` for nodes (checked by grep and by
  the reviewer, 23-10-2026: tickets, alerts and the S031 *Me* page join
  `equipment` and `equipment_classes` only; `documents.py:454` joins a
  document's own model, which exists).

### 5.6 The database down

Nothing new: every route here already answers 503 through `get_db()`.

## 6. API

- `POST /api/equipment`: `model_id` is required as a key; `null` is allowed
  for `level: "component_unit"`, with `class_id` (required) and `type_id`
  (optional, `null` = no type).
- `PUT /api/equipment/<id>`: as § 5.1.
- Node responses (`GET /api/equipment`, `GET /api/equipment/<id>`, the tree,
  the asset list): `model_id`, `model_designation`, `manufacturer_name`,
  `model_label` may be `null`. `class_id`, `class_code`, `type_id`,
  `type_name` are as today.
- Permissions: unchanged (`equipment:edit` for writes, at the node's site).

## 7. Design decisions

1. **Class picked directly when there is no model** (U1). The class gives
   the code prefix and the ISO 14224 class, so it stays required. Rejected:
   a hidden "unknown maker" model per class (a fake row per class, and
   placeholder data under another name).
2. **Component-units only** (U1). Rejected: also components (the user did
   not ask; components carry part numbers, which the BOM work will need).
3. **Keep `fk_equipment_model`, add a CHECK.** The FK still guards that a
   model's class matches the node's; NULL skips it. The CHECK keeps the
   level rule in the database, so no code path can write a model-less
   equipment. Rejected: the rule in code only.
4. **Refuse `class_id` / `type_id` beside a model** instead of ignoring
   them. A client that sends both has a bug, and silence would hide which
   value won.
5. **"No model" in screens, "—" in tables.** Words where there is room, a
   dash in dense columns and print, as the other empty columns.
6. **Data left as it is** (U1). No migration touches rows, so no
   precondition and no backup are needed for the data.
7. **A class change must restate the type** (BR1-01). Rejected: clearing the
   type silently (against decision 4), and refusing every write that does
   not restate both (a type-only change would need the class too).
8. **An absent `model_id` on create means "Pick a model" at every level**
   (BR1-06). A client must say "no model" with `null`; a client that forgot
   the field gets the refusal on the field that is on screen. Rejected:
   absent = `null` for a component-unit (the forgotten field would answer
   "Pick a class").
9. **A sentinel for *No model* in the form** (BR1-02). The form tells
   "nothing picked" from "No model", so each refusal lands beside a field
   on screen (S026). Rejected: refusing `""` in the form as well (the rule
   twice, front and back).
10. **Reuse the existing class and type locks** (BR1-04). One lock helper
    and one wording per refusal. Rejected: a copy in `equipment.py`.

## 8. Tests and acceptance

### Backend (pytest)

New tests in `test_equipment_core.py`:
- one case per row of the § 5.1 tables;
- BR1-01's cases: a class change on a no-model node without `type_id`
  → "Pick a type of the new class, or No type"; `model_id: null` with a new
  `class_id` and no `type_id` → the same; `type_id` alone → accepted (its
  class is a database check, tested in the API tests, BR2-07);
- BR2-01's two cases: `class_id: B` with the stored `type_id: A1`, and
  `model_id: null, class_id: B, type_id: A1` → 400 "This type belongs to
  another class";
- BR2-02: `class_id: ""` / `"x"` → "Pick a class"; `type_id: "x"` →
  "Pick a type";
- BR3-01: create with `model_id` absent and `class_id` / `type_id` sent →
  the one error "Pick a model" on `model_id`;
- BR3-02: stored type None, a class change with `type_id: None` → accepted;
- update without `model_id` on a stored-model node with `class_id` →
  "Class comes from the model"; on a no-model node with `class_id` and
  `type_id` → accepted;
- `tracked_changes`: model "Atlas Copco GA37" → "No model", and back
  (BR1-05).

Existing tests that change (BR1-07), with the intended new assertion:
- `test_equipment_core.py`:
  - `TestValidateCreate.test_required_fields_per_level`: the
    `component_unit` row still lists `model_id` among the missing fields
    (an absent `model_id` is "Pick a model", § 5.1);
  - `TestModelAndRefusedFields.test_a_model_may_be_left_out_on_update_but_not_cleared`:
    unchanged for the equipment default; a new `stored_level="component_unit"`
    case: `model_id: null` with a `class_id` is accepted;
  - `TestModelAndRefusedFields.test_old_fields_are_refused_even_as_null`: the
    `class_id` / `type_id` rows now read "Class comes from the model" /
    "Type comes from the model", and hold only when the node has a model;
  - the test helper `_update` (line 21) gains the stored `model_id`
    (default `2`, non-None, so the update half of
    `test_old_fields_are_refused_even_as_null` keeps asserting the refusal,
    BR2-06), `class_id` (default `1`) and `type_id` (default `None`),
    so the "accepted" cases read against a class-1 node with no type
    (BR3-03).
- `test_equipment_api.py`:
  - `TestModels.test_old_fields_are_refused_even_null_or_unchanged`: the same
    two rows and texts;
  - `test_a_null_model_on_update_is_400` and `test_no_model_is_400` keep
    passing unchanged (equipment level).
- `frontend/tests/modelPicker.test.js`: the existing cases pass with the
  default level; new cases: *No model* offered for a component-unit, not for
  equipment or component.

New API tests in `test_equipment_api.py`:
- create a component-unit without a model, with class and type: 201; code
  prefix from the class; `model_label` null;
- the same with an inactive class (409 "The class is inactive"), an inactive
  type (409), a type of another class (400), an unknown class (400);
- on a no-model node, `type_id` alone of another class → 400 "This type
  belongs to another class" (the database check, BR2-07);
- create equipment or a component with `model_id: null`: 400 "Pick a model";
- clear the model on a component-unit (with its class): the history line
  "… → No model"; set a model again: class and type from the model, the
  history lines;
- a no-model node of a class deactivated later: an edit of its name keeps
  the class (unchanged inactive);
- the list, the detail and the tree return a node without a model; the list
  search finds it by its name;
- the documents route of a node without a model: no model card, no error.

`test_migration_v28.py` (new, on the pattern of `test_migration_v26.py`):
from v27 with an equipment row; after v28 the column is NULLable; the CHECK
refuses an `equipment`-level row without a model and accepts a
component-unit; re-run is a no-op.

### Automated (e2e)

- **Important** — `equipment.spec.js`: the engineer opens the e2e extruder,
  adds a part, level *Component unit*, picks *No model*;
  `expectDialogFits(page)`; picks a class, leaves *No type*;
  `expectDialogFits(page)` again (BR1-08); saves; the equipment page shows
  *Model* "No model"; then `/equipment?level=component_unit&q=<name>` shows
  the row with "—" in *Model*.
- `equipment.spec.js`: on the add-equipment form (level *Equipment*), *No
  model* is not offered; the three existing dialogs that pick "Atlas Copco
  GA37 — CMP / Screw compressor" keep passing.
- `screens.spec.js`: unchanged; runs with the targeted specs.

The e2e run is targeted (`equipment.spec.js`, `asset-list.spec.js`,
`screens.spec.js`): no shared frontend code changes.

### On a real device

None: the form is the existing dialog with two more selects, which the e2e
test drives on the three browser projects, with the fit checked.

### Acceptance

- All four suites green; the targeted e2e specs green.

## 9. Open questions and assumptions

1. **The words** (assumption): option "No model"; fields "Class", "Type";
   help "Without a model, the class sets the code prefix. A later class
   change keeps the code."; "Pick a type of
   the new class, or No type"; "—" in the list and the asset list.
2. **ISO 14224 citation** (to verify): clause 8 Table 5 and Annex A, as
   § 2; the user's copy decides the numbers.
3. **Rollback** (assumption): acceptable as stated in § 4 — a rollback after
   model-less nodes exist needs a model on them first.

## 10. Amendments

None.

## Review log

### U1 — user answers, 23-10-2026 (before drafting)

- Class source without a model: pick the class directly (type optional).
- Levels: component-units only.
- Existing data: left as it is.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 23-10-2026

0 blocker, 2 major, 6 minor, 8 nits. Reviewed against 6ab6af0 (S032
committed meanwhile; the brief's base line updated).

| Finding | Answer |
|---|---|
| BR1-01 major — a class change can leave a type of the old class (1452 → 500) | Accepted (a): a class change must restate `type_id`; a `type_id` is checked against the class after the write; § 5.1, decision 7, § 8 |
| BR1-02 major — "nothing picked" vs "No model"; refusal on a hidden field | Accepted (a): `NO_MODEL` sentinel; `""` leaves `model_id` out; the body, loading, resets and inactive-kept rules; § 1.5, decision 9 |
| BR1-03 minor — ISO 14224 cited beyond what it says | Accepted (a): § 2 rewritten (maker and model are equipment-unit data; subunits by name only) |
| BR1-04 minor — planned duplicate locks, a third "inactive" wording | Accepted (a): `_lock_class` reused, `masters._lock_type_for_model` made public as `lock_type_of_class`; existing texts; § 3, § 5.2 |
| BR1-05 minor — "No model" history text in the shell | Accepted (a): `NO_MODEL` in `equipment_core`, a `tracked_changes` case, `equipmentLabels.js` comment; § 3, § 5.4 |
| BR1-06 minor — validator inputs | Accepted (a): absent on create = "Pick a model"; `stored` gains model, class and type; "newly picked" defined and when to lock; § 5.1–5.3, decision 8 |
| BR1-07 minor — breaking tests not named | Accepted (a): listed in § 8 with the new assertions |
| BR1-08 minor — e2e lacks the fit check and the list level | Accepted (a): `expectDialogFits` twice; the list opened at level component-unit with `q` |
| BR1-09…BR1-16 nits | All accepted. BR1-09: no `COALESCE` (TRUE OR NULL). BR1-10: the documents skip is for clarity. BR1-11: class deactivation not blocked, stated. BR1-12: out of scope wording. BR1-13: § 1.6 "No model or —". BR1-14: Class prefilled from the class filter. BR1-15: ISO 55001 § 7.5. BR1-16: rollback also 409 on edit. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 23-10-2026

0 blocker, 1 major, 1 minor, 5 nits.

| Finding | Answer |
|---|---|
| BR2-01 major — a class change that restates the old type is not "newly picked", so unchecked (1452 → 500) | Accepted (a): a pure § 5.1 row, class changed and `type_id` equal to the stored type → 400 "This type belongs to another class"; two core tests; § 5.3 unchanged |
| BR2-02 minor — refusal text for a non-id class or type; the class placeholder | Accepted (a): "Pick a class" / "Pick a type" (new `PICK_A_TYPE`); `toBody` sends `class_id: null` for the placeholder; § 5.1, § 1.5, § 8 |
| BR2-03…BR2-07 nits | All accepted. BR2-03: `class_id` / `type_id` always form keys. BR2-04: hint hidden once *No model* is picked. BR2-05: the help line replaced while *No model* is picked. BR2-06: `_update`'s stored model default `2`. BR2-07: the type-of-another-class case moved to the API tests. |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 23-10-2026

0 blocker, 0 major, 2 minor, 2 nits. Review loop complete.

| Finding | Answer |
|---|---|
| BR3-01 minor — `""` could send class and type keys; a hidden-field error | Accepted (a): `toBody` leaves all three out for `""`; § 5.1 "Pick a model" reported first; one core case |
| BR3-02 minor — the class-change row matched `type_id: null` | Accepted (a): "an id equal to the stored type"; core case stored type None + `type_id: None` → accepted |
| BR3-03, BR3-04 nits | Accepted. BR3-03: `_update` defaults named (model 2, class 1, type None). BR3-04: help adds "A later class change keeps the code." |

### U2 — approval, 24-10-2026

- Approved as it stands by KLA, after round 3.
- § 9.1 words: accepted as written.
- § 9.2 ISO 14224 clause 8 Table 5 and Annex A: kept, still "to verify" against the user's copy.
- § 9.3 rollback: accepted as stated in § 4.
