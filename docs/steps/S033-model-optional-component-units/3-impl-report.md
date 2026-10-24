```
Step: S033 — Model optional on component-units
Doc: impl-report
Author: Coder (Opus)
Date: 24-10-2026
```

# S033 — Implementation report

**Result.** A component-unit may now have no model. Its class (required) and type (optional)
are then picked in the form. Equipment and components still need a model, in the code and in
the database (v28 CHECK). All four suites are green, and the targeted e2e run passed 69 of 69.
There is one departure from the brief's test list: two tests in `test_migration_v9.py` asserted
the old NOT NULL rule. I changed them to the new rule (Decisions 1).

## 1. What was built

- **The rule** (§ 1.1). `model_id: null` is accepted for a `component_unit` only. Equipment and
  components get "Pick a model", as before. Migration **v28** makes `equipment.model_id` NULLable
  and adds `chk_equipment_model_level` (`model_id IS NOT NULL OR level = 'component_unit'`).
- **Without a model.** The user picks the class (active when newly picked) and the type (an
  active type of that class, or no type). An unchanged inactive class or type is kept. The code
  prefix comes from the class at creation. A later class change keeps the code.
- **Changing between the two** on an existing component-unit. Clearing the model writes the
  history line *model* "`<model>` → No model". Setting a model again takes the class and type from
  the model, and the history gets *model*, *class* and *type* lines as they change.
- **The form** (`EquipmentFormModal.vue`). For a component-unit the *Model* select starts with
  **No model**. Picking it hides the class filter and shows **Class** and **Type** under *Model*,
  with the help line "Without a model, the class sets the code prefix. A later class change keeps
  the code." The hint for a class with no model reads, for a component-unit, "This class has no
  model yet. Pick No model, or add a model in Masters › Models." It hides once *No model* is
  picked.
- **Screens that show the model.** The equipment page shows *Model* "No model" and leaves out the
  *Manufacturer* line. The equipment list and the printed asset list show "—". The documents
  card has no model group.
- **The API** (§ 6): node responses carry `model_id`, `model_designation`, `manufacturer_name` and
  `model_label` as `null` for a node without a model.

## 2. How it works

### Pure core (`equipment_core.py`)

- `_parse_model_id` now returns `None` for `null`. `validate_equipment` then refuses `None`
  unless the level (sent on create, stored on update) is `component_unit`.
- A new `_check_class_and_type(data, clean, creating, stored, errors)` holds the § 5.1 tables:
  - The model is not settled (absent on create, or refused) → nothing more is reported, so
    "Pick a model" stands alone (BR3-01).
  - **With a model** (sent as an id, or stored and not cleared), a `class_id` or `type_id` in the
    body is refused with "Class comes from the model" / "Type comes from the model", even as
    `null`. These two keys left `_REFUSED_FIELDS`, and their old shared text is gone.
  - **Without a model**:
    - The class is required on create and when this write clears a model. On a no-model node an
      absent class keeps the stored one. A class that is `null` or not an id → "Pick a class".
    - The class *after the write* is compared with the stored one. On update, a changed class
      with no `type_id` → "Pick a type of the new class, or No type" (BR1-01).
    - A changed class with `type_id` equal to the stored type → "This type belongs to another
      class" (BR2-01). The text comes from the existing `check_type_class`.
    - A `type_id` that is neither `null` nor an id → "Pick a type".
    - On create an absent type is no type.
- `stored` on update is now `{code, level, model_id, class_id, type_id}`.
- `_display` shows a `None` model label as `NO_MODEL = "No model"`, so `tracked_changes` writes
  "Atlas Copco GA37 → No model" and back.

### Shell

- `masters_core.model_label(None, None)` returns `None`.
- `masters._lock_type_for_model` is now public as `lock_type_of_class(cur, type_id, class_id)`.
  The body and messages are the same, and models still call it.
- `equipment.py`:
  - `NODE_JOINS` uses `LEFT JOIN` to `equipment_models` and `manufacturers`.
  - On update, `stored` comes from the locked row (`LOCK_EQUIPMENT` already read the columns).
    `class_id` and `type_id` now join `parent_id`, `unit_id` and `model_id` in the "sent back
    unchanged → dropped" loop. What is left in `clean` is exactly what is *newly picked*
    (§ 5.2), so an unchanged inactive class or type is never locked or refused.
  - A write with a model goes through `_pick_model` (4), (5), as before. A write without one
    goes through the new `_pick_class_and_type` helper:
    - it locks a newly picked class with the existing `_lock_class` (5): 400 "Unknown class",
      409 "The class is inactive";
    - it locks a newly picked type with `lock_type_of_class` (5a), against the class the row
      will hold: 400 "Unknown type", 400 "This type belongs to another class", 409 "The type is
      inactive".

    On create the class is always locked, because it gives the code prefix through the same
    serial counter (6).
  - The lock-order docstring gained (5a). The cross-module paragraph now says this module locks
    types, after classes, which is the order `masters.py` takes too.
- `documents._inherited` returns no group when `model_id` is `None`. This is for clarity only:
  the old query already matched nothing.

### Frontend

- `modelPicker.js`:
  - new constants `NO_MODEL = "none"` and `NO_MODEL_LEVEL`;
  - `modelChoices` takes `level` (default: no *No model* option, so other callers are
    unchanged);
  - two new helpers, `noModelClassChoices` and `noModelTypeChoices`, list the active entries
    plus the node's current one, marked "(inactive)". They share one small filter with
    `modelChoices`.
- `EquipmentFormModal.vue`:
  - `class_id` and `type_id` are form keys in every state (`COMMON_BLANK`, `fromRecord`). So a
    refusal on them shows beside the field, not at the top (BR2-03).
  - `fromRecord` loads `model_id: null` as `NO_MODEL`.
  - `toBody` handles three cases:
    - `""` (nothing picked) leaves `model_id`, `class_id` and `type_id` out. The backend
      answers "Pick a model" on the *Model* field;
    - `NO_MODEL` sends `model_id: null`, with the class and the type (`""` → `null`);
    - a model id sends `model_id` only.
  - `@change` handlers carry the defaults and resets:
    - picking *No model* prefills *Class* from the class filter, else the node's class on edit;
    - *Type* starts at the node's type when the class is the node's, else at "No type";
    - changing *Class* resets *Type*;
    - switching *Level* to component while *No model* is picked sets *Model* back to the
      placeholder.
  - The types list is loaded with the other masters (`ensureEquipmentTypes`).
- `EquipmentDetailView.vue`, `EquipmentView.vue` and `AssetListPrintView.vue` show "No model",
  "—" and "—". The asset list's phone line already leaves out empty values.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v28: `model_id` NULLable, `chk_equipment_model_level` |
| `backend/equipment_core.py` | No-model rule, `_check_class_and_type`, new messages, `NO_MODEL`, docstrings |
| `backend/equipment.py` | Left joins; `stored` with model/class/type; unchanged class/type dropped; `_pick_class_and_type`; lock-order docstring |
| `backend/masters.py` | `_lock_type_for_model` → public `lock_type_of_class` |
| `backend/masters_core.py` | `model_label(None, None)` → `None` |
| `backend/documents.py` | `_inherited` skips a node without a model |
| `backend/tests/test_equipment_core.py` | `_update` gains the stored model 2, class 1, type None; changed rows; new `TestNoModel` |
| `backend/tests/test_equipment_api.py` | Changed refusal texts; new `TestNoModel` (16 tests) |
| `backend/tests/test_migration_v28.py` | New: v27 → v28 keeps rows, the CHECK, the FK, re-run |
| `backend/tests/test_migration_v9.py` | `model_id` NULLable; a null model on equipment refused by the CHECK (4025) |
| `frontend/src/utils/modelPicker.js` | `NO_MODEL`, `NO_MODEL_LEVEL`, `level` option, class/type choice helpers |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | No model, Class and Type fields, body, loading, defaults, resets, hint, help line |
| `frontend/src/views/EquipmentDetailView.vue` | *Model* "No model", no *Manufacturer* line |
| `frontend/src/views/EquipmentView.vue` | "—" in *Model* |
| `frontend/src/views/AssetListPrintView.vue` | "—" in *Model* |
| `frontend/src/utils/equipmentLabels.js` | Comment on the *model* event |
| `frontend/tests/modelPicker.test.js` | No model offered per level; class and type choices |
| `frontend/e2e/equipment.spec.js` | Two S033 tests |
| `docs/steps/S033-…/1-brief.md`, `docs/steps/README.md` | Status |

`docs/Plan.MD` and `docs/schema.md` (the equipment row) were changed by the planner before
coding, as the brief says.

## 4. Decisions taken

1. **Two more existing tests changed (departure from the § 8 list).** `test_migration_v9.py`
   asserted `model_id` NOT NULL (`test_the_shape_holds`) and a 1048 for a null model on
   equipment (`test_an_equipment_row_with_a_null_model_is_refused`). The brief's list of
   changing tests did not name them. Both now assert the v28 rule: the column is NULLable, and
   the same insert is refused by `chk_equipment_model_level` (4025). The intent of the second
   test stays the same.
2. **`_pick_class_and_type` in `equipment.py`**, beside `_pick_model`. It reuses `_lock_class`
   and `lock_type_of_class` and adds no lock code of its own (decision 10).
3. **Dropping an unchanged `class_id` / `type_id` in the update loop** that already dropped an
   unchanged parent, unit or model. This is how "newly picked" (§ 5.2) reaches the locks.
4. **Type default when *No model* is picked.** The brief says *Type* starts at the node's type on
   edit. I keep it only when the prefilled class is the node's own. If the class filter gives
   another class, *Type* starts at "No type", the same as the reset on a class change.
   Otherwise the save would always fail with "This type belongs to another class".
5. **Class and type choice helpers in `modelPicker.js`** (`noModelClassChoices`,
   `noModelTypeChoices`), with unit tests. They keep the "active, plus the current one marked
   (inactive)" rule in one pure place, shared with `modelChoices`. No existing helper did this
   for classes or types: `EquipmentView.vue` lists every class and type for its filters, not
   active-or-current.
6. **`@change` handlers, not watchers**, for the defaults and resets. They run only on a user's
   pick, so loading a record never changes it and never makes the dialog look edited.
7. **"Select a class…" is a disabled placeholder**, as "Select a model…" is. A new no-model
   dialog that gets no class from the filter starts on it, and `toBody` sends `null` for it
   ("Pick a class").
8. **No early "Pick a type" after "Pick a class".** When the class is refused, the type is not
   checked in the same save: there is no class to check it against.

## 5. Not done, deferred or assumed

- **`schema.md` overview and `schema.html` at v28: not regenerated.** The generator is not in
  the repo (I found no script that writes `schema.html`). Per brief § 3 Docs the planner does it
  at gate B.
- **Rollback (release notes, § 4).** The previous release reads nodes through inner joins to the
  model. A component-unit saved without a model then drops out of its lists, and an edit of it
  answers 409. A rollback after such nodes exist needs a model on each of them first, or the
  db-server dump restored. The migration comment in `local_db.py` says so too.
- **Production MariaDB version:** to verify, as in S031. Both v28 statements ran on the dev image
  (MariaDB 11.4), including the re-run test.
- **Local services.** Docker Desktop was not running when I started. I started it and the dev
  DB container (`tooling/dev/dev-db-up.bat`) to run the tests. Both are still running.
- **ISO 14224 clause and table numbers** (§ 9.2): still to verify against the user's copy.

## Tests run

- Backend, full: `YANTRA_TEST_RUN=s033c1 tooling/run-tests.bat`. The final run passed all four
  suites:

  | Suite | Result |
  |---|---|
  | backend | 2519 passed |
  | frontend | 130 passed |
  | deps | 42 passed |
  | tooling | 106 passed |

  The first full run had 2 failures, both in `test_migration_v9.py` (Decisions 1). They were
  fixed and confirmed by a targeted run before the final full run.
- `npx vite build`: built; only the existing chunk-size warning.
- **E2E, targeted**: `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/asset-list.spec.js
  e2e/screens.spec.js` → **69 passed**, all three projects. These are the specs of the changed
  screens (the equipment form, page and list; the asset list print) plus `screens.spec.js`.
  No shared frontend code changed, so the full suite was not needed.
  - First, the two new tests passed alone on one lane (desktop-chromium).
  - The first targeted run had 1 failure: S029 "Down now…" on phone-chromium, with
    `net::ERR_ADDRESS_IN_USE` loading a Vite module while the full backend suite ran at the
    same time. It is a port fault on the machine, not a fault of this step. The re-run on a
    quiet machine passed 69 of 69.

## Manual checks

- [auto] **Important** — The engineer adds a part to the e2e extruder, level *Component unit*,
  picks *No model* (dialog fits), picks a class and leaves *No type* (dialog fits), and saves.
  The page shows *Model* "No model" and no *Manufacturer* line, and the list at level
  component-unit shows the row with "—" in *Model* —
  `frontend/e2e/equipment.spec.js::S033: engineer adds a component-unit with No model; its page and the list show no model`
- [auto] The Add equipment dialog (level *Equipment*) does not offer *No model* —
  `frontend/e2e/equipment.spec.js::S033: the Add equipment dialog does not offer No model`
- [auto] The existing dialogs that pick "Atlas Copco GA37 — CMP / Screw compressor" still pass,
  in the same 69-test run. The spec has two such dialogs, not the three the brief counts:
  `frontend/e2e/equipment.spec.js::S026: the server's refusal of a field at the bottom of the Add equipment dialog is on screen`
  and `frontend/e2e/equipment.spec.js::S003: engineer adds equipment from the list; its page opens`.
  The new S033 test checks that the same option is still offered.
- [auto] `screens.spec.js` unchanged, green in the same run

Real-device checks: none (brief § 8). No rows were added to `docs/steps/device-checks.md`.

## Fix rounds

### Round 1

All three findings of `4-code-review-r1.md` are fixed. No behaviour changed.

- **CR1-01 — Fixed.** The prefill of *No model* is now a pure helper, `noModelDefaults({ classFilter, currentClassId, currentTypeId })` → `{ class_id, type_id }`, in `frontend/src/utils/modelPicker.js`. `onModelChange` in `EquipmentFormModal.vue` only assigns its result. The rule is the same as before, including Decision 4 (the type is kept only when the class is the node's own). Five vitest cases in `frontend/tests/modelPicker.test.js`: filter of another class, edit with no filter, filter equal to the node's class, create with no filter, node without a type.
  - Red: with the condition changed to `true`, the first case fails (`expected { class_id: 2, type_id: 5 } to deeply equal { class_id: 2, type_id: '' }`). With the fix restored, 17 of 17 pass.
  - `onClassChange` and `onLevelChange` stay as they are: each is one assignment, and the review asked only for the prefill helper.
- **CR1-02 — Fixed.** New API test `TestNoModel::test_an_unchanged_inactive_type_is_kept` in `backend/tests/test_equipment_api.py`: deactivate the node's type, rename the node with the same `class_id` and `type_id`, expect 200. It passes. No red run: the test covers behaviour that was already correct, and no code changed for it.
- **CR1-03 — Fixed.** One-line comment above the `check_type_class` call in `backend/equipment_core.py` (`_check_class_and_type`): it is called for its one wording (Decision 10) and never returns `None` there.

Tests run (`YANTRA_TEST_RUN=s033c2`):

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | backend 2520 passed, frontend 135 passed, deps 42 passed, tooling 106 passed |
| `npx vite build` | built; only the existing chunk-size warning |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` | 60 passed, all three projects (the form was touched; no shared frontend code) |

Files touched in this round: `backend/equipment_core.py`, `backend/tests/test_equipment_api.py`, `frontend/src/utils/modelPicker.js`, `frontend/src/views/equipment/EquipmentFormModal.vue`, `frontend/tests/modelPicker.test.js`.
