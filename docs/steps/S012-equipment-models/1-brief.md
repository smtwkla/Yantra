```
Step: S012 — Equipment models
Doc: brief
Author: Planner (Opus)
Date: 16-10-2026 (revised 16-10-2026 after brief-review r1; rewritten 17-10-2026 after the user's gate-A changes; revised 17-10-2026 after brief-review r3)
Track: full
Status: Committed 3e338b4; manual checks pending (approved 17-10-2026 by KLA)
```

# S012 — Equipment models

Today each piece of equipment has two free-text fields, **Make** and **Model**.
"Atlas Copco", "ATLAS COPCO" and "Atlas copco" are three makers to the
database, a manual can't be attached to "every GA37", and nothing stops a pump
model being typed on a motor.

This step adds two masters, **Manufacturers** and **Models**. A model carries
its equipment class and type. A piece of equipment then *picks its model*, and
its class and type come from the model: to create a machine, you pick a model.
The model's documents (manuals, drawings, parts lists) are uploaded once and
shown on every machine of that model. It replaces the dropped S009 (documents on
classes and types): manufacturer documentation belongs to the manufacturer's
product, not to a class that mixes makers (user, 16-10-2026).

**Depends on:** S010 and S011 (migration v8). This step is migration **v9**.
S010 and S011 are not yet committed; S012 is coded after them.

User decisions (16-10-2026 while planning; 17-10-2026 at gate A):
1. **Manufacturers are their own list** (a master), picked by the model.
2. **A model belongs to one equipment class and optionally one of its types**,
   fixed for life (option (a) of 17-10-2026, not a model free across classes).
3. **Every node has a model** (17-10-2026). The equipment's **class and type come
   from the model**; the equipment form has no class or type picker. Where no
   maker model fits, a plain master record is the escape hatch: a "Generic"
   model of the class, or an in-house design such as `SMTW-HYP-01` under the
   manufacturer "SMTW (in-house)". These are ordinary records, not special code.
4. **The free-text Make and Model are dropped** (17-10-2026): production holds
   no make/model text, so nothing is converted; migration v9 drops the columns.
5. **Model documents are managed on the model** (Masters › Models) and shown
   read-only on every equipment of that model. Removed model documents appear on
   S008's removed-documents screen.

## 1. What will be built

1. **Masters › Manufacturers:** a list of makers (name, active). Create, edit,
   deactivate/reactivate; never deleted.
2. **Masters › Models:** each model has a manufacturer, a **model designation**
   (the maker's own name for the product, e.g. `GA37`, `V100TA1`, or our own
   `SMTW-HYP-01`), an equipment class, and optionally a type of that class.
   Create, edit, deactivate/reactivate; never deleted. The list shows "Atlas
   Copco GA37" with its class and type, and filters by class and manufacturer.
3. **Model documents and photos:** each model row has a **Documents** button. It
   opens, inside the panel, that model's Documents and Photos cards with S006's
   rules (PDF documents, photos with thumbnails, title edit, remove hides and
   keeps). This is S009's in-panel view, reused.
4. **The equipment form:** the Make, Model, **Class and Type** fields go. A
   required **Model** picker takes their place:
   - an optional **class filter** above it narrows the list (it is not saved);
   - each entry reads "Atlas Copco GA37 — CMP / Screw compressor";
   - below the picker, the resulting class and type are shown read-only;
   - only active models are offered; on edit, the node's current model stays
     listed even when inactive, marked "(inactive)", as classes and types are.
     The form loads models with `include_inactive=1` for that.
   - When the class has no model yet, a hint says "Add a model in Masters ›
     Models (a Generic one if the maker is unknown)".
5. **The equipment page** shows Manufacturer and Model, next to Class and Type.
6. **On the equipment page,** the Documents and Photos cards also list the
   model's documents under "From model *Atlas Copco GA37*", read-only, after the
   node's own. For editors a plain line says "Managed in Masters › Models".
7. **The removed-documents screen** (Settings, S008) also lists removed model
   documents, with restore and delete-for-good.
8. **Search:** the equipment list's search also matches the model designation
   and the manufacturer name.
9. **History:** a change of model writes an equipment event "model"; when the new
   model has another class or type, the "class" and "type" events are written
   too, as today.
10. **The dev seed** (`tooling/dev/seed_dev.py`, from S010/S011) seeds
    manufacturers and models (including a Generic and an in-house one) and
    creates equipment by model.

**Out of scope:**
- model attributes (rated power, speed, capacity: ISO 14224's design data);
- vendor or AMC contacts on a manufacturer;
- filtering the equipment list by model or manufacturer (the search covers it);
- adding a model from inside the equipment form (models are added in Masters);
- documents on a component inherited from its parent's model (each node shows its
  own model only);
- moving or copying a node document onto its model (re-upload it there);
- spares per model, QR labels, and everything S006 left out.

## 2. Standards and practice

- **ISO 14224 (equipment data, Table 5 and Annex A).** For every equipment unit
  ISO 14224 lists common data that includes the **manufacturer's name** and the
  **manufacturer's model designation**, apart from the unit's class and type. The
  point is *data pooling*: reliability (MTBF, failure modes) can be compared
  across identical units only when "identical" is recorded the same way every
  time. A picked model does that; free text doesn't.
  - *Departure 1:* the standard does not scope a model to a class; Yantra does
    (decision 2), because a product is always one kind of thing.
  - *Departure 2:* the standard records class, type and model as separate
    attributes; Yantra **derives** class and type from the model (decision 3).
    The model is the most specific of the three, so it fixes the other two;
    deriving them removes a whole class of inconsistent records and makes data
    entry one pick.
  - Generic and in-house models keep the record complete: ISO 14224 expects the
    attribute to be filled, and "Generic" says honestly that the maker is not
    known, which a blank does not distinguish from "nobody looked".
  - A Generic model is not a real product, so it doesn't satisfy the pooling
    argument or ISO 8000's "one record per real thing" (BR3-07.7). Generic rows
    mean "maker unknown". Any later per-model reliability comparison leaves them
    out or flags them; the manufacturer name "Generic" makes them easy to find.
- **EN 13460 (Documentation for maintenance).** It separates documents that come
  with a product (operating and maintenance manuals, drawings, parts lists) from
  those about one unit. Product documentation is true for every unit of a model,
  so it belongs on the model; a unit's own papers (its test certificate, its
  nameplate photo, its as-altered drawing) stay on the equipment (S006). For our
  own designs the in-house model holds the design drawings; a press altered
  after it was built keeps its alteration drawings on the equipment.
- **ISO 55001:2014 § 7.6 (documented information; control § 7.6.3).** One
  controlled copy: a manual uploaded once on the model, a corrected edition
  uploaded once, and every machine of that model shows it. S006's traceability
  applies unchanged. Masters are deactivated, never deleted (as S001).
- **ISO 27001:2022.**
  - **A.8.3 (information access restriction).** A model's documents are generic,
    not about one site's machines, so they are visible to everyone who can read
    equipment, at every site, like the models themselves. This deliberately
    departs from site scoping, as S009 did for classes. Node documents keep their
    site and unit scope (S011). Files are served only through permission-checked
    routes.
  - **A.5.12 (classification of information).** The upload dialog's "No
    confidential documents (contracts, prices)" line gains "Visible at every
    site" for models.
- **Master data practice (ISO 8000, data quality).** One record per real thing,
  with one spelling: names are unique without regard to case or repeated spaces.

## 3. Where

### Backend
- **Migration v9** in `backend/local_db.py`, written out in § 4: tables
  `manufacturers` and `equipment_models`; `equipment.model_id`; the old `make`
  and `model` columns dropped; `equipment_documents.model_id` and the one-owner
  CHECK; the events ENUM. SQL only, each statement safe to run twice.
- **`backend/masters_core.py`:** validators for manufacturer and model.
- **`backend/masters.py`:** routes for manufacturers and models (§ 6), with the
  lock order of § 5.5; class deactivation refused while the class has active
  models (§ 5.2); `UNIQUE_KEY_ERRORS` gains `uq_manufacturers_name` and
  `uq_equipment_models_maker_designation`, with the 409 texts of § 5.1 and § 5.2.
- **`backend/equipment_core.py`:** `model_id` among the writable fields,
  required on create; `make`, `model`, `class_id` and `type_id` refused (§ 5.4);
  `derive_from_model` (§ 5.3) as a pure function; the "model" event in
  `_TRACKED`. S004's "Pick a type of the new class, or none" rule and
  `check_type_class` on equipment writes go (the type can no longer be picked).
- **`backend/equipment.py`:** lock and check the model on create and update
  (§ 5.3, § 5.5); class and type written from the model; `_check_type_on_update`
  and the equipment write's type lock go. `_NODE_COLUMNS` joins `equipment_models`
  and `manufacturers` with an **inner `JOIN`**, as the class (BR3-04): a model
  invisible to the re-read's snapshot gives the existing `_reread` 409 "try
  again", the race the class already accepts. The detail and list carry `model_id`, `model_designation`,
  `manufacturer_name` and `model_label`, and no longer `make` / `model`. Search
  adds the designation and manufacturer name. `LOCK_EQUIPMENT` gains `model_id`.
- **`backend/documents.py`** and **`backend/file_store.py`:** generalised from "a
  node" to "an owner", with two owners: node (`equipment/<id>/`) and model
  (`equipment-models/<id>/` under `DATA_DIR`). This reuses S009's design (S009
  brief § 3–§ 5 and its A1 for the removed list) and its code in
  `docs/steps/S009-class-type-documents/s009-code.patch`, with the owners `class`
  and `type` replaced by `model`. The patch predates S011, so its node checks
  must follow S011's keyed site checks (`load_node_for_user(…, key)`,
  `_lock_node_for_change(…, key)`), not the patch's. In the frontend, the node's
  own documents keep `canEdit` from S011's `node.permissions`; the "Managed in
  Masters" hint and the Models panel use the global `userPermissions`.
- **`backend/app.py`:** `documents_bp` is mounted at `/api` and its routes spell
  out `/equipment/…` and `/masters/equipment-models/…`, as the S009 patch did
  (today it is mounted at `/api/equipment`; the node URLs don't change).
- **New code, not in the patch** (BR2-03): the patch's removed list, restore and
  purge are node-only, so the `UNION ALL` list and restore/purge by owner are
  written new, following S009 A1's rules.
- **The "model" event's value** (BR2-05, BR3-04): `_written_state` patches
  `model_designation` from the locked model row (a rename committed while this
  write waited), as it does the class code; `manufacturer_name` comes from the
  re-read (a display-only residual, accepted as S002 accepted site codes). One
  stale-re-read test, as for the class code.
- **Docstrings** of `equipment.py`, `masters.py`, `documents.py` and
  `file_store.py` state the new lock order and owners.

### Frontend
- **`frontend/src/views/masters/ManufacturersPanel.vue`** and
  **`ModelsPanel.vue`** (new), and two sections in `MastersView.vue`:
  "Manufacturers" and "Models" (perm `masters:read`), after Equip Type.
- **`frontend/src/stores/masters.js`:** `ensureManufacturers()`, `ensureModels()`.
- **`frontend/src/components/documents/`:** the documents cards and their dialogs
  move here and take a `basePath`, as in S009 (`DocumentsCards.vue`,
  `DocumentUploadModal.vue`, `DocumentTitleModal.vue`, `PhotoViewer.vue`).
- **`frontend/src/views/equipment/EquipmentFormModal.vue`:** the Model picker
  replaces Make, Model, Class and Type (§ 1.4). The list building (class filter,
  active / current-inactive, labels) goes in a small helper
  `utils/modelPicker.js` with vitest tests, as `siteRoles.js` in S011.
- **`frontend/src/views/EquipmentDetailView.vue`:** Manufacturer and Model; the
  inherited model documents.
- **`frontend/src/views/EquipmentView.vue`** (BR3-07.5): a **Model** column
  (`model_label`) after Class, so a row found by "GA37" shows why; the search
  placeholder reads "Search code, name, model, notes…".
- **`frontend/src/utils/equipmentLabels.js`** (BR3-05): `describeEvent` gains
  `case "model"` → "Model: Atlas Copco GA37 → Atlas Copco GA55"; a line in
  `frontend/tests/equipmentLabels.test.js`.
- **`frontend/src/views/settings/RemovedDocuments.vue`:** model rows (§ 5.6).

### Tests
- New: `test_models_api.py`, `test_migration_v9.py`, the picker helper's vitest.
- Changed: `test_masters_core.py`, `test_masters_api.py`, `test_equipment_core.py`,
  `test_equipment_api.py`, `test_documents_api.py`,
  `test_removed_documents_api.py`, `test_site_checks_api.py`,
  `tests/conftest.py`, and every helper that creates equipment. **Equipment is
  now created by model**, so:
  - a shared test helper creates a manufacturer and a model for a class (and
    type) and returns the model id; equipment-creating helpers and cases send
    `model_id` instead of `class_id` / `type_id` / `make` / `model`;
  - cases about picking a type or changing class on equipment (S004's type rules
    on equipment, `TestReclassify`, the class-change half of `TestTypes`) are
    rewritten as model changes or dropped where the rule is gone; the report
    lists each dropped case and why;
  - cases broken by the class-deactivation rule (§ 5.2) (BR3-03):
    - `test_masters_api.py::TestEquipmentClasses::test_deactivated_class_with_equipment_stays_frozen`
      and `test_equipment_api.py::TestReclassify::test_existing_equipment_keeps_a_deactivated_class`:
      deactivate the model first, then the class; still assert the frozen code;
    - `test_masters_api.py::TestEquipmentTypes::test_deactivating_a_type_in_use_is_allowed`:
      the equipment gets a model carrying that type;
    - `test_site_checks_api.py::test_status_notes_type_at_b`: the
      `{"type_id": None}` parameter becomes `{"model_id": <a model of another class>}`;
    - `test_to_an_inactive_class_is_409` and
      `test_create_with_an_inactive_class_is_409`: the bypassed-shell case of
      § 8 (BR3-02);
  - `conftest.Uniq` gains `manufacturer_name()` and `designation()` (BR3-07.6);
  - `test_equipment_api.py::TestList::test_row_fields` gains `model_id`,
    `model_designation`, `manufacturer_name`, `model_label`;
  - `tests/documents_helpers.py` follows the `file_store` owner signatures;
  - `conftest._TABLES` gains `equipment_models` and `manufacturers` (after
    `equipment`, before `equipment_types` and `equipment_classes`).
- `test_rbac.py` and `navigation.test.js` need no change: no new permission keys.

### Tooling
- `tooling/dev/seed_dev.py`: manufacturers (Haendle GmbH, Atlas Copco, Generic,
  SMTW (in-house)) and models (Atlas Copco GA37, class CMP, type Screw
  compressor; a Haendle main-extruder model; a Generic model per seeded class
  without a maker, e.g. a Generic gearbox for the `GBX` component unit; one
  `SMTW-HYP-01` press); the `EQUIPMENT` tuples replace `make, model` with a model
  key, and equipment is created by `model_id`.

### Docs (at approval, by the planner)
- `docs/Plan.MD` § 4.1: fields (model in place of make/model; class and type from
  the model), the in-house-model note under document kinds, § 5 tables.

## 4. Data model (migration v9)

InnoDB, utf8mb4 with the server's case-insensitive collation (as every Yantra
table); audit columns as S001 (`created_at`, `created_by`, `updated_at`,
`updated_by`).

### 4.1 New tables

```sql
CREATE TABLE IF NOT EXISTS manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    <audit columns as S001>,
    CONSTRAINT uq_manufacturers_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS equipment_models (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_id INT NOT NULL,
    designation VARCHAR(80) NOT NULL,
    class_id INT NOT NULL,
    type_id INT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    <audit columns as S001>,
    CONSTRAINT uq_equipment_models_maker_designation UNIQUE (manufacturer_id, designation),
    CONSTRAINT uq_equipment_models_id_class UNIQUE (id, class_id),
    CONSTRAINT fk_equipment_models_manufacturer FOREIGN KEY (manufacturer_id) REFERENCES manufacturers (id),
    CONSTRAINT fk_equipment_models_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
    CONSTRAINT fk_equipment_models_type FOREIGN KEY (type_id, class_id)
        REFERENCES equipment_types (id, class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- The case-insensitive key refuses "ATLAS COPCO" next to "Atlas Copco".
- One designation per manufacturer: the same maker can't have two `GA37`s. So
  Generic models are named by what they are ("Generic screw compressor",
  "Generic gear pump"), one per class or type as needed.
- **Designation at most 80 characters** (BR1-05): the event value "manufacturer
  designation" is then at most 181, inside the events' `VARCHAR(200)`.
- **Composite FKs, as migration v5** (BR1-04): the model's type must be of the
  model's class, and the equipment's model must be of the equipment's class
  (§ 4.2). Safe because a model's class and type never change (§ 5.2).

### 4.2 Changes to existing tables

In this order, each safe to re-run:

```sql
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS model_id INT NOT NULL AFTER type_id;
ALTER TABLE equipment ADD INDEX IF NOT EXISTS ix_equipment_model (model_id, class_id);
ALTER TABLE equipment ADD CONSTRAINT fk_equipment_model FOREIGN KEY IF NOT EXISTS
    (model_id, class_id) REFERENCES equipment_models (id, class_id);
ALTER TABLE equipment DROP COLUMN IF EXISTS make;
ALTER TABLE equipment DROP COLUMN IF EXISTS model;

ALTER TABLE equipment_documents MODIFY equipment_id INT NULL;
ALTER TABLE equipment_documents ADD COLUMN IF NOT EXISTS model_id INT NULL AFTER equipment_id;
ALTER TABLE equipment_documents ADD INDEX IF NOT EXISTS ix_equipment_documents_model (model_id, removed_at);
ALTER TABLE equipment_documents ADD CONSTRAINT fk_equipment_documents_model FOREIGN KEY IF NOT EXISTS
    (model_id) REFERENCES equipment_models (id);
ALTER TABLE equipment_documents ADD CONSTRAINT IF NOT EXISTS chk_equipment_documents_owner
    CHECK ((equipment_id IS NOT NULL) + (model_id IS NOT NULL) = 1);

ALTER TABLE equipment_events MODIFY event
    ENUM('created','moved_unit','moved_parent','status','criticality','class','type','model') NOT NULL;
```

- **`equipment.model_id` is `NOT NULL`** (user, 17-10-2026): production holds
  only sites and units, no equipment, so the column can be added as required.
  The database then guarantees "every node has a model", not only the API.
- **On a table that already has equipment** (BR3-01): the `ADD COLUMN` succeeds
  and fills existing rows with 0. The `ADD CONSTRAINT … FOREIGN KEY` then fails
  (1452). v9 is left half-applied, with no `db_version` row. It keeps failing on
  every 30-s retry until the equipment rows are gone, and the app serves 503
  meanwhile.
  - **Dev and test:** run `tooling/dev/dev-db-reset.bat` (it resets both
    `vel_yantra_master` and `vel_yantra_test`) **before the first test run**,
    because `conftest` runs `ensure_schema()` before it empties the tables. The
    impl report says so.
  - **Production:** the § 8 check prevents it. If it were missed, recovery is
    manual SQL by the user (delete the equipment rows, or drop the half-added
    column and index), then a restart.
- **Dropping `make` and `model`** loses no data, for the same reason.
- `equipment.class_id` and `equipment.type_id` stay: codes, filters, reports and
  the S004 FKs use them. They are written from the model and never set apart from
  it.
- The events ENUM keeps the existing values in their order and appends `model`
  (BR1-02); the coder checks the current list in v4/v5 and copies it exactly.
- The `MODIFY equipment_id` and the CHECK ran as written on MariaDB 11.4 in the
  S009 code. If the dev DB refuses the `MODIFY` (error 1832), the fallback of S009
  brief § 4 applies; the report says which was used.
- **Production MariaDB version:** the CHECK needs ≥ 10.2.1 and `ADD CONSTRAINT
  IF NOT EXISTS` ≥ 10.5. The user reads it from Settings › Database before the
  release (§ 8).

## 5. Rules

### 5.1 Manufacturers
- Name: required, at most 100 characters, trimmed, inner spaces collapsed;
  unique without regard to case → 409 "A manufacturer with this name exists".
- The name may be edited (a typo). Models and equipment show the new name at
  once.
- Deactivating a manufacturer that has active models → 409, as a site with
  active units (S001). Its models must be deactivated first.

### 5.2 Models
- **Designation:** required, at most **80** characters, trimmed, inner spaces
  collapsed; unique per manufacturer without regard to case → 409 "This
  manufacturer already has a model with this designation".
- **Manufacturer, class, type:** the manufacturer and class must exist and be
  active when the model is created (inactive → 409; unknown → 400 on its field).
  The type, when given, must be a type **of that class** (else 400 "This type
  belongs to another class", as S004) and active (else 409).
- **Fixed after creation:** manufacturer, class and type can't be changed (400).
  A wrong model is deactivated and a new one created. The designation can be
  edited (a typo).
- **Inactive model:** stays on the equipment that has it and keeps its documents
  (listed, served, editable); it just can't be newly picked. Reactivating needs
  an active manufacturer and class (409 otherwise).
- **Class deactivation** (S001's class route) is refused while the class has
  active models → 409 "Deactivate this class's models first". Otherwise a class
  could be inactive while its models still put new equipment in it.
- **List order:** manufacturer name, then designation. A model's `label` is
  "<manufacturer name> <designation>".

### 5.3 Equipment and its model

A pure function in `equipment_core.py` (BR3-07.3: it returns a message, and the
shell picks the status, as every pure validator here does):

```
derive_from_model(stored_model_id, model) -> (class_id, type_id, message)
  stored_model_id = the locked node's model_id (None on create)
  model = the locked row of the model the request picks: {id, class_id, type_id, active}
  message = "This model is inactive" or None; the shell maps it to 409 on model_id
```

Rules:

1. **Create:** `model_id` is required → 400 `model_id` "Pick a model". `model_id`
   gets this message of its own for both "missing" and `null`, not the generic
   "… is required" / "… must be a record id" texts (BR3-07.2).
2. **Unknown `model_id`** → 400 `model_id` "Unknown model" (decided by the shell
   when the locking read finds no row, as `_lock_type` does).
3. **Newly picked** (create, or a `model_id` different from the stored one): the
   model must be active → else 409 `model_id` "This model is inactive". An
   unchanged inactive model is kept.
4. **Class and type come from the model:** the node's `class_id` and `type_id`
   are set to the model's, both always written, so a model with no type writes
   `type_id = NULL` and the "type X → none" event (BR3-07.4). On an update, a new
   model with another class is a reclassification (the code is kept, as a class
   change is today) and writes the "class" event; another type writes the "type"
   event.
5. **The model's class must be active** when the model is newly picked (the
   shell's existing `_lock_class` → 409 `class_id` "The class is inactive").
   **Defence in depth** (BR3-02): through the API an active model always has an
   active class (§ 5.2), so this is unreachable; it stays because the class lock
   is needed for the code prefix anyway. The model's type is **not** checked for
   active: the model's own `active` governs what can be picked (BR1-06).
6. **Update:** `model_id` may be left out (no change) but not cleared: `null` →
   400 "Pick a model".
7. **Levels:** every level has a model (a motor component, a valve), since every
   node needs a class and the class now comes from the model. A part under a
   parent of the same model, or of another, is fine.

### 5.4 Fields the API refuses
`POST`/`PUT /api/equipment` refuse the keys `make`, `model`, `class_id` and
`type_id`, **including when sent as `null` or unchanged** → 400 on that field,
"Make and model are now picked from Models" (`make`/`model`) or "Class and type
come from the model" (`class_id`/`type_id`). This is a new, explicit rule in
`validate_equipment`, which otherwise ignores unknown keys; it makes an old open
tab fail loudly. The stale-bundle check prompts the reload anyway.

### 5.5 Who and where; lock order

| Action | Permission |
|---|---|
| List manufacturers and models | `masters:read` (`*`) |
| Create/edit manufacturers and models | `equipment:edit`, held at **any** site (`require_perm`, the global union, as classes and types: S011 decision 5) |
| List, open, download model documents | `equipment:read`, held anywhere (§ 2, A.8.3) |
| Upload, edit title, remove a model document | `equipment:edit`, held anywhere |
| Restore and delete-for-good a model document | `equipment:purge_documents`, held anywhere |
| Pick a model on an equipment | the equipment's own write rule (S011: `equipment:edit` at its site) |

No new permission keys. **Stated consequence** (as S009 A1): a manager at one
site can restore or erase a model document that machines at other sites show.

**Lock order:** manufacturer → model → class → type, in every module, stated in
the module docstrings.
- **`equipment.py`:** (1) node, (2) parent, (3) unit, **(4) model**, (5) class,
  (6) serial counter. The model is locked only when newly picked; it gives the
  class and type. The class is then locked (active check and the code prefix on
  create). The type is no longer locked by equipment writes: it comes from the
  model, whose type never changes; its name for the event is read plainly.
- **`masters.py`:**
  - model create: manufacturer → class → type → insert;
  - model reactivate: manufacturer → model → class;
  - model designation edit or deactivate: model row alone;
  - manufacturer deactivate: manufacturer row, then a plain count of its active
    models (a concurrent reactivate waits on the manufacturer lock);
  - class deactivate: class row, then a plain count of its active models (a
    concurrent model create or reactivate waits on the class lock);
  - existing class → type paths unchanged.
- **`documents.py`:** a model document write takes one owner lock (the model
  row), then only `equipment_documents` rows (S009 § 5.3).

### 5.6 Documents on the equipment page and in the removed list
- `GET /api/equipment/<id>/documents` (after the node's site check, S011) adds
  `inherited`: the model's group (owner `model`, its label and its `path`), when
  the model has documents not removed. As S009 § 5.4, with one group.
- The removed list (`GET /api/equipment/removed-documents`) is the `UNION ALL` of
  S009 A1: the node branch unchanged (S011's keyed unit scope; an empty unit set
  leaves out the node branch, not the whole list), plus a model branch with no
  unit condition. A model row: `owner = "model"`, `code` null, `name` the model's
  label, shown as "Model *Atlas Copco GA37*"; `q` matches the designation, the
  manufacturer name, the title and the original name. Restore and purge follow
  S009 A1 with the model owner.

## 6. API

| Method & path | Permission |
|---|---|
| `GET /api/masters/manufacturers` (`?include_inactive=1`) | `masters:read` |
| `POST /api/masters/manufacturers`, `PUT …/<id>` | `equipment:edit` (any site) |
| `GET /api/masters/equipment-models` (`?include_inactive=1&class_id=&manufacturer_id=`) | `masters:read` |
| `POST /api/masters/equipment-models`, `PUT …/<id>` | `equipment:edit` (any site) |
| `GET/POST /api/masters/equipment-models/<id>/documents`, `…/<doc_id>` (title), `…/<doc_id>/file`, `/thumb`, remove, `/restore`, `/purge` | as § 5.5, same shapes as the node routes (S006, S008) |
| `GET /api/equipment/<id>/documents` | as now, plus `inherited` |
| `POST`/`PUT /api/equipment` | `model_id` (required on create); `make`/`model`/`class_id`/`type_id` refused (§ 5.4) |

Lists return `{items, total}`, not paginated (S001: small lists). A model item:
`id, manufacturer_id, manufacturer_name, designation, label` ("Atlas Copco
GA37"), `class_id, class_code, class_name, type_id, type_name, active`, audit.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Manufacturer master | User decision 1; one spelling per maker (ISO 14224 data pooling) | Text on the model |
| Model under one class and at most one type | User decision 2; a product is one kind of thing | A model free across classes (user chose (a), 17-10-2026) |
| Class and type come from the model; one pick creates a machine | User decision 3; no inconsistent class/type/model; faster entry | Class, type and model picked separately and checked against each other |
| Model required on every node, with Generic and in-house models as the escape hatch | User decision 3; complete ISO 14224 data; "Generic" is an honest "maker unknown" | Optional model (blank can't tell "unknown" from "not entered"); special "unknown" flag or code |
| Generic / in-house as ordinary records, no special code | Simplest; engineers add them as needed | Auto-created Generic model per class |
| `model_id NOT NULL` in the database, and required by the API | Production has no equipment (user, 17-10-2026), so the database can hold the rule too. Cost: v9 stops half-applied on any DB with equipment rows; dev/test are reset, production is guarded by the § 8 check (BR3-01) | NULL-able column, API-only rule (needed only if old equipment existed) |
| Model's manufacturer, class and type fixed after creation | Equipment rely on them; makes the composite FKs safe; a fix = deactivate + new | Editable, with a check of every equipment using it |
| A class with active models can't be deactivated | Keeps the class of every pickable model active | Picking refused at use time only |
| Make/model columns dropped, nothing converted | No such data on production (user decision 4) | Keeping them read-only, converting old text |
| Composite FKs (model ↔ class, model type ↔ class) | The pattern of migration v5; holds when the shell is bypassed | Plain FKs |
| One documents table, owners node and model + CHECK | S009's design and code, reused; real FKs | A second table for model documents |
| Model documents visible at every site | Generic maker information (A.8.3), as S009 decided for classes | Scoping by where the model is used |
| No new permission keys | Models are equipment masters, like classes: `equipment:edit` | A `models:edit` key |

## 8. Tests and acceptance

### Pure (`test_masters_core.py`, `test_equipment_core.py`)
- Manufacturer validator: required, length 100/101, trimming and space
  collapsing. Model validator: the same with 80/81.
- `derive_from_model`: create without a model; class and type taken from the
  model (with and without a type); newly picked inactive → 409 vs unchanged
  inactive kept; a model whose type is inactive can be picked.
- `validate_equipment`: `make`, `model`, `class_id`, `type_id` refused, also as
  `null`; `model_id` required on create; `null` refused on update.
- `tracked_changes`: "model" on a model change; "class" and "type" too when the
  new model differs in them.

### API
- **Manufacturers:** create/list/edit; duplicate by case or by repeated spaces →
  409; deactivate with an active model → 409; `include_inactive`.
- **Models:** create/list/edit; duplicate designation per maker by case → 409,
  the same designation under another maker → 201; inactive manufacturer or
  class → 409; unknown manufacturer → 400; type of another class → 400; change
  of manufacturer/class/type → 400; reactivate under an inactive manufacturer →
  409; filters `class_id`, `manufacturer_id`.
- **Classes:** deactivating a class with an active model → 409; with only
  inactive models → 200.
- **Equipment:** create by model (class, type and code prefix from the model);
  no model → 400; inactive model → 409; model of an inactive class (class
  deactivated by SQL, bypassing § 5.2) → 409 `class_id`; each
  refused field of § 5.4; update to a model of another class (class, type and
  model events, code kept); `null` model → 400; search by designation and by
  manufacturer name.
- **Database rules with the shell bypassed:** a model of another class on an
  equipment row, and a type of another class on a model row → `IntegrityError`
  1452.
- **Documents:** upload/list/title/remove/serve on a model; the node's
  `inherited` group (present, absent when no documents, follows a model change at
  once); a node at another site → 404 while the model's documents stay reachable
  through the model route; the S006 and S008 node tests keep their behaviour.
- **Removed list:** model rows for a manager limited to one site; `q` on a model
  row; restore and purge of a model document; the node branch's unit scope
  unchanged.
- **RBAC:** an operator: 403 on every manufacturer/model/model-document write, 200
  on reads; an engineer at one site: 200 on model writes; purge of a model
  document by an engineer → 403.
- **Migration v9 (`test_migration_v9.py`):** as `test_migration_v8.py`: delete
  `db_version` 9 and call `init_db` twice; the second run changes nothing; the
  `make`/`model` columns are gone; an equipment row with `model_id` NULL →
  `IntegrityError` 1048 (BR3-07.1); the CHECK refuses a document with no owner and one with
  two (`OperationalError` 4025, as S009's test).

### Frontend
- Vitest for the picker helper: the class filter, active models only, the
  current inactive model kept and marked, the label "Maker designation — CLASS /
  Type".

### Manual checks (important, for the impl report)
- [ ] As engineer: add manufacturer "Atlas Copco" and model "GA37" (class CMP,
  type Screw compressor); create a compressor by picking it: class and type are
  shown from the model; the page shows Manufacturer and Model.
- [ ] Add "SMTW (in-house)" / `SMTW-HYP-01` (class press) and a Generic model;
  create a press and a component with them.
- [ ] Upload a manual on the model in Masters › Models; it appears "From model"
  on every compressor of that model, read-only; remove it in Masters; restore it
  from Settings › Removed documents.
- [ ] **Production, at the release:** before deploying, note the MariaDB version
  (Settings › Database; needs ≥ 10.5) and confirm that there is no equipment:
  as admin or IT admin (sees every unit), open the Equipment list with **Show
  scrapped** ticked and **Level = All levels**; the total must be 0 (BR3-06).
  v9 adds `model_id` as `NOT NULL` and drops make/model. If the total is not 0,
  stop and tell the planner.

Also (plain): on a phone (Android, iPhone), pick a model from the list (long
labels).

### Acceptance
- `tooling/run-tests.bat` green and the frontend build clean.
- An engineer creates the SMTW compressors by picking their real model, and one
  manual shows on both.

## 9. Open questions and assumptions

1. **Decided — a model on every level** (user, 17-10-2026, the recommendation). As written (§ 5.3 rule 7):
   the class now comes from the model, so a component without a model would need
   its own class picker again. The cost is a master record per kind of part
   (often a Generic one: "Generic gear pump"). The alternative is a model only
   on equipment level, with components keeping class and type pickers — two ways
   to fill the form. **Recommendation:** every level, as written.
2. **Decided — escape models** (user, 17-10-2026): the user creates Generic and
   in-house manufacturers and models in Masters when needed. No naming rule, help
   line or seeded production records come with this step; only the dev seed has
   examples.
3. **Decided — no description** (user, 17-10-2026, the recommendation): should models also have an optional plain description (e.g. "37 kW
   oil-injected screw compressor")? Recommendation: no, not now; design data is
   out of scope.
4. **Assumption:** production has no equipment, only sites and units (user,
   17-10-2026); the release check in § 8 confirms it.
5. **Assumption:** Manufacturers and Models are two more Masters sections (nine
   in all); the toolbar shows icons on a phone, so it still fits.
6. **Assumption:** a component inherits nothing from its parent's model; each
   node shows its own model's documents only.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 lock order / type derivation | major | **Accepted** (option 1): model locked before the type; `masters.py` orders. *Rewritten 17-10-2026:* order now manufacturer → model → class → type (§ 5.5); `check_model` replaced by `derive_from_model` (§ 5.3) |
| BR1-02 events ENUM | major | **Accepted** (option 1): `MODIFY event ENUM(…,'model')` in § 4.2 |
| BR1-03 conversion SQL | minor | **Accepted**; *superseded 17-10-2026:* no conversion, the columns are dropped (user decision 4) |
| BR1-04 composite FKs | minor | **Accepted** (option 1): `(model_id, class_id)` and `(type_id, class_id)` composite FKs; bypassed-shell tests |
| BR1-05 event length, "none", type event | minor | **Accepted** (option 1): designation ≤ 80; "type" event when the model changes the type |
| BR1-06 § 5.3 edges | minor | **Accepted**: model-set type not checked for active; unknown model 400; levels line; `_NODE_COLUMNS` join |
| BR1-07 breaking tests, seed, wording | minor | **Accepted**; *rewritten 17-10-2026:* equipment is created by model, test changes in § 3 |
| BR1-08 manual checks | minor | **Accepted**: production check (important) with the MariaDB version; phone check as a plain note |
| BR1-09 standards | nit | **Accepted**: ISO 55001:2014 numbering; A.5.12 added |
| BR1-10 small gaps | nit | **Accepted**: model folder `equipment-models/<id>/`; removed-list `q`/`code`/`name`; inactive current model listed; docstrings and `UNIQUE_KEY_ERRORS` |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 model lock vs join | minor | **Accepted**: the model is locked only when newly picked; `LOCK_EQUIPMENT` gains `model_id` (§ 5.5) |
| BR2-02 message needs class codes | minor | **Accepted**; *superseded 17-10-2026:* the class comes from the model, so no mismatch is possible |
| BR2-03 § 3 gaps | minor | **Accepted**: `app.py` mount at `/api`; `test_row_fields`; `documents_helpers.py`; removed list/restore/purge by owner as new code (§ 3) |
| BR2-04 small gaps | nit | **Accepted**: `model_id` parsing; inactive type on model create → 409 and list order (§ 5.2); form loads with `include_inactive=1` (§ 1.4) |
| BR2-05 event value "none" | nit | **Accepted**: label from the locked row plus a plain manufacturer read (§ 3) |

### Changes at gate A — user, 17-10-2026

Brief rewritten in place before approval; the next review round covers it.
1. Model tied to one class (option (a)).
2. Old make/model text: no data on production; columns dropped, no conversion
   (§ 4.2; old § 4.3 and `legacy_*` removed).
3. Model mandatory on every node; Generic and in-house models as the escape
   hatch (§ 5.3, § 9 Q1–Q2).
4. Class and type come from the model; the equipment form has a model picker
   only (§ 1.4, § 5.3, § 5.4); class deactivation refused while it has active
   models (§ 5.2); lock order manufacturer → model → class → type (§ 5.5).
5. `equipment.model_id NOT NULL`: production has no equipment at all, only sites
   and units (§ 4.2).

### Round 3 — `2-brief-review-r3.md` (Fable), answered 17-10-2026

The last round on the full track; no blocker or major finding.

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 failure on a populated table | minor | **Accepted** (option 1): § 4.2 states the FK fails, v9 is half-applied and stuck; dev/test reset before the first test run; production recovery; the cost added to § 7 |
| BR3-02 inactive-class case unreachable | minor | **Accepted** (option 1): rule 5 marked defence in depth; § 8 case built by SQL |
| BR3-03 cases broken by the class-deactivation rule | minor | **Accepted**: the cases named with their fixes (§ 3 Tests) |
| BR3-04 inner or LEFT JOIN | minor | **Accepted** (option 1): inner `JOIN`; designation patched from the locked row; plain manufacturer read dropped (§ 3) |
| BR3-05 "model" event label | minor | **Accepted**: `equipmentLabels.js` and its test in § 3 |
| BR3-06 production check can pass with rows | minor | **Accepted** (option 1): admin, Show scrapped, Level = All levels, total 0 (§ 8) |
| BR3-07 small gaps | nit | **Accepted** all seven: 1048 test; own "Pick a model" message; `derive_from_model` returns a message, the shell picks 409; `type_id` written NULL; a Model column in the list and the search placeholder; `Uniq` and seed lines; the Generic-model sentence in § 2 |
