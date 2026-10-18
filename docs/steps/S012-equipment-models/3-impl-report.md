```
Step: S012 — Equipment models
Doc: impl-report
Author: Coder (Opus)
Date: 17-10-2026
```

# S012 — Implementation report

Baseline: HEAD `c486a4a` (S010 + S011). The unrelated uncommitted changes in the tree
(`docs/Plan.MD`, `Maintenance-Philosophy.md`, `Plant-Facts.md`, `docs/review/`, the criticality
badge colours in `frontend/src/utils/equipmentLabels.js`) are kept; `equipmentLabels.js` got
the `case "model"` on top of the colour change.

**Before the first test run on any machine with a pre-v9 test DB, run
`tooling/dev/dev-db-reset.bat`** (brief § 4.2, BR3-01). `conftest` runs `ensure_schema()`
before it empties the tables, so v9 would meet old equipment rows, stop at the
`fk_equipment_model` foreign key (1452) and stay half-applied. I reset both dev databases
before my first run, as the task allowed.

## Tests run

- `tooling/run-tests.bat`: **backend 986 passed**, **frontend 51 passed** (9 files).
- `npx vite build` in `frontend/`: built with no warnings or errors.
- The dev seed was run against a temporary dev backend on port 5002 (`FLASK_DEBUG=1
  DEV_AUTH_BYPASS=1`, on the freshly reset `vel_yantra_master`). It seeded 4 manufacturers,
  6 models and 6 equipment plus 1 component unit, each created by model. The dev DB now
  holds that seed data. Your PyCharm "Backend" on 5001 was running old code: restart it.

## 1. What was built

1. **Masters › Manufacturers:** list, create, rename, deactivate and reactivate. A name is
   trimmed and runs of spaces become one. Names are unique without regard to case (409 "A
   manufacturer with this name exists"). A manufacturer with active models can't be
   deactivated (409).
2. **Masters › Models:** a manufacturer, a designation (at most 80 characters), a class and
   an optional type of that class.
   - The manufacturer, class and type are fixed after create (400 "… cannot be changed").
     Only the designation can be edited, and it is unique per manufacturer (409).
   - Create and reactivate need an active manufacturer and class (409).
   - The list is ordered by manufacturer, then designation, and filters by class and
     manufacturer.
   - Each row has a **Documents** button, which opens the model's Documents and Photos cards
     in the panel (S009's in-panel view).
3. **Class deactivation** is refused while the class has active models: 409 "Deactivate this
   class's models first".
4. **Equipment is created by model.**
   - `model_id` is required ("Pick a model"). An unknown model is 400 and a newly picked
     inactive one is 409. An unchanged inactive model is kept.
   - The class and type are always written from the model, so a model without a type
     writes `type_id = NULL`.
   - `make`, `model`, `class_id` and `type_id` are refused on POST/PUT, even as `null` or
     unchanged (§ 5.4).
   - A model change writes a "model" event, plus "class" and "type" events when they differ.
     The code is kept on a reclassification.
5. **The equipment form** replaces Make, Model, Class and Type with:
   - an optional class filter (not saved);
   - a required Model picker ("Atlas Copco GA37 — CMP / Screw compressor"), active models
     only, with the current inactive one kept and marked "(inactive)";
   - the class and type shown read-only below the picker;
   - a hint when the filtered class has no model.
6. **The equipment page** shows Manufacturer and Model. The Documents and Photos cards also
   list the model's documents under "From model *…*", read-only, with "Managed in Masters ›
   Models" for users holding `equipment:edit` at any site.
7. **The equipment list** has a Model column. Search also matches the manufacturer, the
   designation and the full label. The placeholder reads "Search code, name, model, notes…".
8. **Removed documents (Settings)** also lists removed model documents, at every site. A
   model row shows "Model *label*", and restore and delete-for-good work through the model's
   URL.
9. **History** reads "Model: Atlas Copco GA37 → Atlas Copco GA55".
10. **The dev seed** has the manufacturers (Haendle GmbH, Atlas Copco, Generic, SMTW
    (in-house)) and the models (Atlas Copco GA37, Haendle "VAH 600", SMTW-HYP-01, and
    Generic vertical blade mill / bore pump / gearbox). It creates all equipment by model.

## 2. How it works

- **Migration v9** (`local_db.py`) is SQL only, and every statement is safe to re-run. It:
  - creates `manufacturers` and `equipment_models`, with the composite FK
    `(type_id, class_id) → equipment_types` and the `uq_equipment_models_id_class` key;
  - adds `equipment.model_id INT NOT NULL`, its index and the composite FK
    `(model_id, class_id) → equipment_models`;
  - drops `make` and `model`;
  - makes `equipment_documents.equipment_id` nullable, then adds `model_id`, its index, its
    FK and the one-owner CHECK;
  - appends `'model'` to the events ENUM, keeping the seven old values in order.

  The plain `MODIFY equipment_id INT NULL` ran on the dev MariaDB 11.4, so S009's fallback
  was not needed.
- **Pure core.**
  - `masters_core`: `validate_manufacturer`, `validate_equipment_model` and
    `model_label(manufacturer, designation)`, which is the one place a model's label is
    built.
  - `equipment_core`:
    - `derive_from_model(stored_model_id, model)` returns `(class_id, type_id, message)`.
      The message is "This model is inactive" only when the model is newly picked, and the
      shell maps it to 409.
    - `validate_equipment` refuses the four old keys, with `model_id` taking its own "Pick a
      model" message.
    - `_TRACKED` gains `("model_label", "model")`.
- **Equipment shell** (`equipment.py`). The lock order is node (1) → parent (2) → unit
  (3) → **model (4)** → class (5) → serial counter (6).
  - `_pick_model` locks the model, derives the class and type, locks the class (active
    check, and the prefix on create) and writes both ids into the write.
  - The type is no longer locked. `_check_type_on_update`, `_lock_type` and `_LOCK_TYPE` are
    gone.
  - `NODE_JOINS` inner-joins `equipment_models` and `manufacturers`, so a model invisible to
    the snapshot gives the existing `_reread` 409 "try again" (BR3-04).
  - `_written_state` patches `model_designation` from the locked model row. The
    manufacturer name comes from the re-read.
  - `LOCK_EQUIPMENT` gains `model_id`.
- **Masters shell** (`masters.py`): the new routes follow the lock orders of § 5.5. The
  module docstring lists them.
  - Model create locks manufacturer → class → type, then inserts.
  - Reactivation reads the fixed ids plainly, then locks manufacturer → model → class.
  - Designation edit and deactivate lock the model row alone.
  - Manufacturer and class deactivation lock the row, then count the active models plainly.
- **Documents** (`documents.py`, `file_store.py`) are generalised to two owners, following
  S009's `OWNERS` table and stacked route decorators.
  - The blueprint is now mounted at `/api`. Node URLs are unchanged, and model URLs live
    under `/api/masters/equipment-models/<id>/documents`.
  - Node owners keep S011's keyed site checks: `load_node_for_user(…, key)` and
    `_lock_node_for_change(…, key)`. Model owners take a plain read, or a lock on the model
    row alone, behind the routes' global `require_perm`.
  - The node list's `inherited` holds one model group, left out when the model has no
    documents.
  - The removed list is a paged `UNION ALL` of the S008 node branch (unit scope unchanged;
    left out, not the whole list, when the user has no units) and a model branch with no
    unit condition. Each item gains `owner` and `path`.
  - Restore and purge are generalised by owner (new code, BR2-03).
  - Files go to `DATA_DIR/equipment/<id>/` or `DATA_DIR/equipment-models/<id>/`.
- **Frontend.**
  - The document cards and dialogs moved to `components/documents/` (`DocumentsCards.vue`
    takes `basePath`), with S009's patch adapted to the model owner.
  - The equipment page's own documents keep `canEdit` from S011's `node.permissions`; the
    "Managed in" hint uses the global `userPermissions`.
  - The picker list is built in `utils/modelPicker.js`, which has vitest tests.

## 3. Files touched

**Backend**
- `backend/local_db.py`: migration v9.
- `backend/masters_core.py`: validators for manufacturer and model, `model_label`, and
  `_parse_optional_id` and name collapsing.
- `backend/masters.py`: manufacturer and model routes; the class-deactivation rule; the
  `UNIQUE_KEY_ERRORS` entries; the docstring with the lock orders.
- `backend/equipment_core.py`: `derive_from_model`, the refused fields, `model_id` with
  "Pick a model", the "model" tracked event, and a docstring for `check_type_class`.
- `backend/equipment.py`: model and class locking, the model joins and fields, search, the
  event designation patch, the docstring; the type locking removed.
- `backend/documents.py`: rewritten for two owners (node, model), the inherited group, the
  `UNION ALL` removed list, and restore and purge by owner.
- `backend/file_store.py`: owner folders (`owner_folder`, `file_path(owner, id, name)`,
  `write_file(owner, id, …)`).
- `backend/app.py`: `documents_bp` mounted at `/api`.

**Backend tests**
- `backend/tests/conftest.py`: the `make_manufacturer` and `make_model` fixtures;
  `make_equipment` creates by model; `Uniq.manufacturer_name` and `designation`; `_TABLES`.
- `backend/tests/documents_helpers.py`: the `*_to` helpers by URL, `model_docs_url`,
  `owner_files`.
- `backend/tests/test_models_api.py` (new): manufacturers, models, class deactivation,
  RBAC, and a model type of another class refused by the database (1452).
- `backend/tests/test_migration_v9.py` (new): re-run twice, shape, NULL model 1048, CHECK
  4025.
- `backend/tests/test_equipment_api.py`: equipment created by model; reclassify and type
  cases rewritten as model changes; new `TestModels`.
- `backend/tests/test_equipment_core.py`: `derive_from_model`, the refused fields, the
  model event.
- `backend/tests/test_masters_core.py`: the manufacturer and model validators, the label.
- `backend/tests/test_masters_api.py`: the two cases named in BR3-03.
- `backend/tests/test_site_checks_api.py`: `world` uses a model; the `type_id: None` case
  becomes a model of another class.
- `backend/tests/test_documents_api.py`: model documents, the inherited group, access,
  failures, the CHECK.
- `backend/tests/test_removed_documents_api.py`: model rows, `q`, restore and purge,
  refusals; a user with no units still sees model rows.

**Frontend**
- `frontend/src/components/documents/DocumentsCards.vue` (new, from S009's patch),
  `DocumentUploadModal.vue`, `DocumentTitleModal.vue`, `PhotoViewer.vue`: moved from
  `views/equipment/`, now take `basePath`, model owner, "Visible at every site".
- `frontend/src/views/equipment/EquipmentDocuments.vue`: deleted (replaced by
  `DocumentsCards`).
- `frontend/src/views/equipment/EquipmentFormModal.vue`: the class filter and Model picker
  replace Class, Type, Make and Model.
- `frontend/src/views/EquipmentDetailView.vue`: Manufacturer and Model; `DocumentsCards`
  with the model's documents; a reload after an edit.
- `frontend/src/views/EquipmentView.vue`: the Model column and the search placeholder.
- `frontend/src/views/masters/ManufacturersPanel.vue`, `ModelsPanel.vue` (new);
  `frontend/src/views/MastersView.vue`: the two sections after Equip Type.
- `frontend/src/views/settings/RemovedDocuments.vue`: model rows; action URLs from `path`.
- `frontend/src/stores/masters.js`: `ensureManufacturers`, `ensureModels`, the reset.
- `frontend/src/utils/modelPicker.js` (new), `frontend/tests/modelPicker.test.js` (new).
- `frontend/src/utils/equipmentLabels.js` and `frontend/tests/equipmentLabels.test.js`:
  `case "model"` and its test.

**Tooling and docs**
- `tooling/dev/seed_dev.py`: manufacturers, models, equipment by model.
- `docs/steps/S012-equipment-models/1-brief.md` and `docs/steps/README.md`: status set to
  In code review.

## 4. Decisions taken

None changes the design; each is a small choice the brief left open.

1. **`check_type_class` stays in `equipment_core`.** `masters.py` imports it for the
   model-create type check (400 "This type belongs to another class"). Its docstring now
   speaks of a "record", since equipment no longer picks a type.
2. **Search uses one expression**, `CONCAT(mf.name, ' ', m.designation) LIKE …`. It matches
   the designation, the manufacturer name, and the full label "Atlas Copco GA37".
3. **`model_label()` in `masters_core`** is the single place a label is built, for model
   lists, node rows, events, the inherited group and removed rows. SQL returns the parts.
4. **Two extra parts on the `Owner` dataclass, beyond S009's:** `lock_for_purge` (a node
   without the scrapped check, S008 § 5.3) and `log_name`. Thanks to `log_name`, node log
   lines still say "of node 12" and model lines say "of model 3".
5. **Messages the brief did not give:**
   - "The manufacturer has active models; deactivate them first" (409, `active`);
   - "Unknown manufacturer" (400) and "The manufacturer is inactive" (409);
   - "Manufacturer / Class / Type cannot be changed" (400);
   - "Designation is required" and "Designation must be at most 80 characters";
   - on reactivation, "The manufacturer is inactive" and "The class is inactive" with
     field `active`, as type reactivation does today.
6. **A newly picked model always locks its class,** even when the class is the same as
   before (§ 5.3 rule 5 says "when the model is newly picked").
7. **Removed-list node rows also gain `owner` (`"equipment"`) and `path`.** Model rows
   carry `name` = the label, and `code`, `equipment_id`, `level`, `status`, `unit` and
   `full_path` are null (S009 A1's shape, with `code` null as § 5.6 says).
8. **Frontend prop name:** `everyUnit` from the S009 patch became `everySite`, and the
   upload line reads "Visible at every site: no confidential documents (contracts,
   prices)."
9. **The equipment form's class filter** starts at "All classes" on every open, and offers
   active classes only.
   - The model already picked stays listed when the filter is set to another class, so the
     select never goes blank.
   - The defence-in-depth 409 on `class_id` shows at the top of the dialog.
   - Serial no., Year, Criticality and Status now share one wrapping row.
10. **Removed-documents card:** a model row shows "Model *label*" with a line "Every machine
    of this model", and the search placeholder adds "model".
11. **Test helper:** `make_equipment(cls=…, type_id=…)` makes a fresh model of that class
    and type for each call; `model=` reuses a given one.
12. **Seed:** the Haendle designation "VAH 600" is made up, as the seed's equipment is. The
    Generic designations follow the brief ("Generic gearbox" and so on), so their labels
    read "Generic Generic gearbox". That is honest but repetitive; it is a naming question
    for you, not code.

## 5. Not done, deferred or assumed

- `docs/Plan.MD` § 4.1 and § 5 are for the planner, at approval (brief § 3 Docs). I did not
  touch them.
- **Test cases dropped or rewritten, because their rule is gone (§ 3 Tests):**
  - `test_equipment_api.py::TestTypes`:
    - `test_create_refusals`, `test_put_refusals`: equipment no longer takes a type. The
      same refusals now apply to model create (`test_models_api.py`).
    - `test_class_change_while_typed_needs_a_type_decision`: S004's "Pick a type of the new
      class, or none" rule is gone.
    - `test_class_change_with_the_old_type_sent_back_is_400`: `type_id` is refused outright
      now (`TestModels::test_old_fields_are_refused…`).
    - `test_class_change_of_an_untyped_node_needs_nothing`: covered by the model-change
      cases.
    - `test_the_type_name_in_events_comes_from_the_lock`: the type is no longer locked.
      Replaced by the designation-from-the-lock assertion in
      `TestRereadAfterWrite::test_class_unit_and_designation_in_events_come_from_the_locks`.
    - `test_create_without_a_type_or_with_null`: `type_id: null` is now refused. Rewritten
      as `test_create_with_a_model_without_a_type`.
  - Rewritten as model changes:
    - `TestReclassify`, all four cases; the two inactive-class cases deactivate the class by
      SQL (BR3-02);
    - `test_set_change_clear…`, `test_class_change_with_no_type`,
      `…with_a_type_of_the_new_class`, `test_the_same_type_name…`, `test_a_scrapped_node…`;
    - `TestEvents::test_one_event_per_changed_tracked_field` and
      `test_untracked_edits_write_no_event` (no make/model).
  - `test_equipment_core.py::TestTypeAndNotes`: the four `type_id` parsing cases were
    dropped and replaced by `TestModelAndRefusedFields`.
- **Not verified in a browser:** the screens were built against the API and the build
  passes, but I did not click through them. The manual checks below cover them.
- **Production:** the release check below (MariaDB ≥ 10.5, no equipment rows) is the guard
  for v9's `NOT NULL` column. If it is missed, recovery is manual SQL (brief § 4.2).

## Fix rounds

### Round 1

Findings of `4-code-review-r1.md`.

- **CR1-01 (minor) - Fixed.** `_lock_class_for_type` is deleted from `backend/masters.py`;
  `create_equipment_type` and `update_equipment_type` call
  `_lock_active_parent(cur, "equipment_classes", class_id, field, "class")`. Same query, messages
  and fields, so no test change.
- **CR1-02 (nit) - Fixed.** The model branch of the removed-documents search in
  `backend/documents.py` now matches `CONCAT(mf.name, ' ', m.designation)` (as the equipment list
  does), then title and file name. `test_q_matches_designation_manufacturer_title_and_file_name`
  also searches by the model's full label.
- **CR1-03 (nit) - Fixed.** `ManufacturersPanel.reload` refreshes the manufacturers and the
  models caches together (`Promise.all`), so a rename shows in the equipment form's picker
  without a reload.

## Manual checks

- [ ] As engineer: add manufacturer "Atlas Copco" and model "GA37" (class CMP, type Screw compressor); create a compressor by picking it: class and type are shown from the model; the page shows Manufacturer and Model.
- [ ] Add "SMTW (in-house)" / `SMTW-HYP-01` (class press) and a Generic model; create a press and a component with them.
- [ ] Upload a manual on the model in Masters › Models; it appears "From model" on every compressor of that model, read-only; remove it in Masters; restore it from Settings › Removed documents.
- [ ] **Production, at the release:** before deploying, note the MariaDB version (Settings › Database; needs ≥ 10.5) and confirm that there is no equipment: as admin or IT admin (sees every unit), open the Equipment list with **Show scrapped** ticked and **Level = All levels**; the total must be 0. v9 adds `model_id` as `NOT NULL` and drops make/model. If the total is not 0, stop and tell the planner.

Also:
- On a phone (Android, iPhone), pick a model from the list (long labels).
