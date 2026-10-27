```
Step: S063 — Equipment category above the class
Doc: impl-report
Author: Orchestrator as coder (Opus), by KLA's decision of 27-10-2026
Date: 27-10-2026
```

# S063 — Implementation report

Equipment categories are built as the brief says, with no departure. Engineers keep a list of
category names in *Masters › Equip Category*, pick one category per class in *Equip Class*, and
filter the equipment list and the printed asset list by category. Migration v35 adds the table
and the class's column; nothing is seeded. All unit suites and the targeted browser run are
green; the whole-suite run is recorded under § Tests.

## 1. What was built

- **Masters › Equip Category** (before *Equip Class*): a table of Name, Classes (active classes
  in it), Status, *Edit*; *Add category*; the edit dialog with *Deactivate* / *Reactivate*.
  Hidden *Add* and *Edit* without `equipment:edit`. With no categories it says "No equipment
  categories yet. Add one, then pick it for each class in Equip Class."
- **The class's category:** a *Category* select in the class dialog (*No category* first, the
  active categories, the class's own inactive one marked "(inactive)"), and a *Category* column
  in the classes table ("—" for none).
- **The filter:** *All categories* in the equipment list's filter row, before *All classes*. A
  chosen category narrows the class select and clears a class outside it (with its type). The
  level stays. `category_id` is in the URL, so a reload keeps it. *Print asset list* carries it;
  the section header reads "Category: <name>".
- **The API:** `GET/POST /api/masters/equipment-categories`, `PUT …/<id>`; the class routes take
  and return `category_id` and return `category_name`; `GET /api/equipment` and
  `/api/equipment/asset-list` take `category_id`.

## 2. How it works

- **Migration v35** (`local_db.py`) creates `equipment_categories` (name unique, active, audit
  columns) and adds `equipment_classes.category_id INT NULL` with the foreign key
  `fk_equipment_classes_category`, all with `IF NOT EXISTS`. MariaDB's `FOREIGN KEY IF NOT
  EXISTS` works: the re-run test passes with one key and an equal schema, so the brief's fallback
  was not needed.
- **Validation** (`masters_core.py`, pure): `validate_equipment_category` (name 1–50 characters,
  trimmed; active); `_CLASS_FIELDS` gains the optional `category_id` (`_parse_optional_id`);
  `category_in_use(n)` builds the deactivation refusal, singular and plural.
- **Routes** (`masters.py`):
  - the category list joins a sub-count of active classes (`class_count`);
  - the category update locks its row, then on deactivate counts the active classes (a plain
    read, the transaction's first) and refuses with 409 on `active`;
  - the class create now runs in a transaction: when a category is given, it locks it first
    (`_lock_active_parent`: unknown → 400 on `category_id`, inactive → 409), then inserts;
  - the class update keeps its checks, then calls `_lock_category_of_class`: a new non-null
    category is locked and checked (field `category_id`); a reactivation that keeps a category
    locks and checks it (field `active`); otherwise the category is not read;
  - the class responses come from `_CLASS_SELECT`, a `LEFT JOIN` for `category_name`.
- **The filter** (`equipment.py`): `_list_filters` reads `category_id` with `int_arg` and adds
  `c.category_id = %s`. `NODE_JOINS` already joins the node's class as `c`, so the list and the
  asset list both get it, and a node matches by its own class.
- **Frontend:** the store's `equipmentCategories`; `EquipmentCategoriesPanel.vue` on the
  `useMasterForm` pattern; the class dialog's `toBody` sends `null` for *No category*;
  `utils/equipmentFilters.js` (pure) gives the class choices under a category and says when a
  chosen class falls outside it; `assetList.js` carries and names the key.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v35 |
| `backend/masters_core.py` | `CATEGORY_NAME_MAX`, `_CATEGORY_FIELDS`, `validate_equipment_category`, `category_in_use`; `category_id` on the class |
| `backend/masters.py` | Category routes, `_CLASS_SELECT` / `_CATEGORY_SELECT`, the class create in a transaction, `_lock_category_of_class`, the unique-key message, lock notes and `_lock_active_parent` docstring |
| `backend/equipment.py` | `category_id` in `_list_filters` and its docstring |
| `backend/tests/conftest.py` | `equipment_categories` in `_TABLES`; `Uniq.category_name`; the `make_category` fixture |
| `backend/tests/test_masters_api.py` | `TestEquipmentCategories`, `TestClassCategory`; the read and 403 tests cover the new route |
| `backend/tests/test_masters_core.py` | `TestEquipmentCategory` |
| `backend/tests/test_equipment_api.py` | The category filter and its 400 |
| `backend/tests/test_asset_list_api.py` | The category filter; parts come with their machine |
| `backend/tests/test_migration_v35.py` | New: fresh, key, v34 upgrade, re-run |
| `frontend/src/stores/masters.js` | `equipmentCategories`, `ensureEquipmentCategories`, reset |
| `frontend/src/views/masters/EquipmentCategoriesPanel.vue` | New panel |
| `frontend/src/views/MastersView.vue` | The *Equip Category* section |
| `frontend/src/views/masters/EquipmentClassesPanel.vue` | Category select and column |
| `frontend/src/utils/equipmentFilters.js` | New: `classChoicesFor`, `classOutsideCategory` |
| `frontend/src/views/EquipmentView.vue` | The Category select, the narrowed class choices, `category_id` in the URL and the API call |
| `frontend/src/utils/assetList.js` | `category_id` in `FILTER_KEYS`; "Category: …" in `filtersLabel` |
| `frontend/src/views/AssetListPrintView.vue` | Loads the categories for the header |
| `frontend/tests/equipmentFilters.test.js` | New |
| `frontend/tests/assetList.test.js` | The category key and label |
| `frontend/e2e/support/properties.js` | New helper `categorySetup` |
| `frontend/e2e/masters.spec.js` | The S063 flow test; *Equip Category* in the sections loop (with a `before` step) |
| `frontend/e2e/equipment.spec.js` | The S063 filter test |
| `frontend/e2e/asset-list.spec.js` | The S063 print test |
| Docs | § Docs updated |

## 4. Decisions taken

- **Shared test helpers** (not named in the brief's § 3): `make_category` and
  `Uniq.category_name` in `conftest.py`, and `categorySetup` in `e2e/support/properties.js`.
  Reason: three test files need a category of their own (DRY). A change to `e2e/support/`
  means the whole browser suite runs again, which this step does anyway.
- **The sections loop in `masters.spec.js`** gained an optional `before` step, so the *Equip
  Category* entry makes a row first (the e2e database has no categories). The brief left this
  to the coder (§ 8.4).
- **The category select is shown even when no categories exist** (only *All categories*), as
  the brief says. Hiding it until a category exists was considered and not done: not in the
  brief.
- **A duplicate category name is 409, not the 400 of brief § 8.2** (CR1-01): 409 is the app's
  rule for every unique key (`api_common._integrity_error`), and the test asserts 409.
- No other decision beyond the brief.

## 5. Not done, deferred or assumed

- Out of scope as the brief says: reports, PM templates and strategy by category; the category
  on the equipment page, rows and labels; a "No category" list filter.
- The categories themselves are KLA's to create after the deploy, then the classes are mapped
  in *Equip Class* (brief § 1, *Mapping the classes*).

## Manual checks

- [auto] **important** The engineer opens *Equip Category*, adds a category, gives a class that
  category in *Equip Class*, and the classes table shows it; the category's Classes count reads
  1, and *Deactivate* is refused at the top of the dialog with "1 active class is in this
  category. Move it to another category first." —
  `frontend/e2e/masters.spec.js::S063: engineer adds a category, puts a class in it, and cannot deactivate it while the class is active`
- [auto] *Equip Category* opens, and an empty *Add category* is refused beside its field with
  "Name is required" —
  `frontend/e2e/masters.spec.js::engineer: the Equip Category section opens, and an empty add category is refused beside its field`
- [auto] **important** On the equipment list the engineer picks a category; the class select
  lists only its classes; the list shows only their machines; a reload keeps it —
  `frontend/e2e/equipment.spec.js::S063: engineer picks a category; the class select lists only its classes, the list only their machines, and a reload keeps it`
- [auto] *Print asset list* with a category filter shows "Category: <name>" in the section
  header — `frontend/e2e/asset-list.spec.js::S063: Print asset list with a category filter names the category in the section header`

On a real device: none (brief § 8.5). No row added to `docs/steps/device-checks.md`.

## Tests

- **Backend while coding:** `test_masters_core.py` and `test_masters_api.py`, 499 passed;
  `test_migration_v35.py`, `test_migration_v34.py`, `test_equipment_api.py`,
  `test_asset_list_api.py`, `test_modules.py`, 246 passed.
- **All unit suites** (`YANTRA_TEST_RUN=s063c1 tooling/run-tests.bat`): backend 3315 passed,
  frontend 243 passed, tooling 185 passed.
- **Build check** (`npx vite build`): built; only the existing chunk-size warning.
- **Targeted** (`e2e/masters.spec.js e2e/equipment.spec.js e2e/asset-list.spec.js
  e2e/screens.spec.js`, Normal): 93 passed, 1 skipped (the existing desktop skip in
  `screens.spec.js`), 97 s. All four S063 tests passed on their first run.
- **Whole suite** (Normal, `tooling/run-e2e-tests.bat`, once at the end of coding): 234 passed,
  7 skipped (existing skips), **1 failed**: `equipment.spec.js` "S012: IT admin adds a
  manufacturer and a model of it". Cause: that test finds its maker's row by a substring match
  on "E2E maker phone-chromium", and `propertySetup` makes makers named "E2E maker
  phone-chromium <random>"; the new S063 asset-list test now runs before it on the same lane,
  so three rows matched. Fixed in fix round 1 (the test matches the maker's cell exactly); the
  targeted re-run there is green.

## Docs updated

- `docs/schema.md`: the `equipment_categories` row, `category_id` on `equipment_classes`, the
  Mermaid overview (table, column, link), the "migration v35" line.
- `docs/schema.html`: the overview and Equipment tabs (table, column, link), the meta line
  (v35, 39 tables, 57 links).
- `docs/Plan.MD` § 4.1: an *Equipment category* bullet before *Equipment type*; § 2 *Not in v1*:
  the equipment-groups line says groups of classes are built as the category.
- `docs/Maintenance-Philosophy.md`: the glossary row *Equipment category*.
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map gains S063 under `masters`,
  `equipment` and `asset-list`.
- `backend/example_secrets_app.py`, `docs/Keycloak.md`, `docs/steps/device-checks.md`: none,
  because no secret, role or device check changed.

## Feedback

- hindrance: Bash heredocs that held Python with `'` inside a `'''` string or `\n` inside JSON failed twice ("unexpected EOF", a count of 0); a script file written with the Write tool worked each time (about 4 min lost).
- idea: `tooling/steps/brief_facts.py` could flag a "new" shared test helper (fixture, `e2e/support/` export) the brief does not name, since a `support/` change re-runs the whole browser suite.

## Fix rounds

### Round 1 (`4-code-review-r1.md`: 0 blocker, 0 major, 0 minor, 5 nits), 27-10-2026

| Finding | Answer |
|---|---|
| CR1-01 nit | Accepted: § 4 *Decisions taken* records the 409. |
| CR1-02 nit | Fixed: `EquipmentCategoriesPanel.vue`'s empty text says "Add one, …" only with `equipment:edit` ("No equipment categories yet." otherwise), and "No active categories. Turn on Show inactive to see the others." when only inactive ones exist. |
| CR1-03 nit | Held for KLA at gate B; KLA chose (a), 28-10-2026. Fixed: the reactivation refusal (field `active`) reads "This class's category is inactive. Pick another category or No category, then reactivate." (`masters_core.CLASS_CATEGORY_INACTIVE`; `masters._lock_category_of_class` locks the stored category itself, so the message is its own); the API test asserts it. `test_masters_api.py` and `test_masters_core.py`: 499 passed. Brief § 5.2 records the text. |
| CR1-04 nit | Fixed: the `_lock_active_parent` docstring re-wrapped. |
| CR1-05 nit | Fixed: `activeFirstBy(records, key)` in `equipmentFilters.js` serves `classChoicesFor` and the list's `categoryChoices`; a unit test added. |
| Whole-suite failure (orchestrator) | Fixed: `equipment.spec.js` S012 test finds the maker's row by its exact cell. |

Tests of the round: frontend 244 passed; `vite build` built; `test_masters_api.py` and
`test_masters_core.py` 499 passed; targeted browser run (`e2e/equipment.spec.js
e2e/masters.spec.js e2e/asset-list.spec.js e2e/screens.spec.js`, Normal) 93 passed, 1 skipped
(the existing skip), 122 s, the S012 test included.
