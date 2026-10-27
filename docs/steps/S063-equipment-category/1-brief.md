```
Step: S063 — Equipment category above the class
Doc: brief
Author: Orchestrator (Opus)
Date: 27-10-2026
Track: full
Status: Gate B (approved 27-10-2026 by KLA; coded by the orchestrator (Opus), KLA 27-10-2026)
Baseline: c9142b4
```

# S063 — Equipment category above the class

## 1. What will be built

An **equipment category** is a group of equipment classes: *Lifting equipment* holds EOT crane,
chain block, hoist and sling; *Utilities* holds compressor, pump and blower. ISO 14224 groups
its classes into categories the same way (§ 2). Each class is in at most one category. A
machine's category is its class's category; nothing is stored on the machine.

1. **A category master.** *Masters › Equip Category*, a new section before *Equip Class*. It
   is a list of names with *Active*, kept by engineers (`equipment:edit`, as classes are).
   The table shows Name, Classes (how many active classes are in it), Status, and *Edit*.
2. **No starting list** (KLA, Q1). The table starts empty and KLA creates the categories.
   § 4.2 gives suggested names, for reference only; nothing is seeded.
3. **A category on the class.** The *Add / Edit equipment class* dialog gets a *Category*
   select, with *No category* first (rules in § 5.2). The classes table gets a *Category*
   column.
4. **A category filter** on the equipment list. It is a select *All categories* in the
   filter row, just before *All classes*. A chosen category narrows the class select to the
   classes in it. *Print asset list* carries the filter, and its section header names it
   ("Category: Lifting equipment · Class: EOT").
5. **The API.** `GET /api/equipment` and `GET /api/equipment/asset-list` take `category_id`.
   The class routes take and return `category_id` and also return `category_name`.

**Mapping the classes.** No class or category list exists on paper today. After the deploy,
KLA or an engineer (1) creates the categories in *Masters › Equip Category*, then (2) opens
*Masters › Equip Class* and picks a category for each class. A blank in the *Category* column
shows the classes still to do. The migration maps nothing.

### Out of scope

- **Hand-picked equipment groups** stay out (Plan.MD § 2 *Not in v1*). A category groups
  classes, not machines, so it does not reopen that decision.
- Seeding categories (Q1).
- Reports by category (downtime, MTBF), PM templates applied by category, and the
  maintenance strategy per category. They come with their modules, which are not built yet.
  This step only gives them the field to group by.
- The category on the equipment page, in the equipment list's rows and on labels.
- A category inside the *Filter by property* dialog, or properties linked to a category.
- A "No category" choice in the equipment list's filter. The classes table shows the classes
  without a category.
- More than one category per class.

## 2. Standards and practice

- **ISO 14224** (equipment taxonomy and reliability data) groups its equipment classes into
  **equipment categories** in Annex A (Table A.4 has an *equipment category* column: rotating,
  mechanical, electrical, safety and control, and others; table number *to verify*). The
  category is a grouping of classes, not a level of the taxonomy. The level above the class
  in the taxonomy is the plant section, which Yantra's units are. Yantra uses the standard's
  term and its rule (each class in one category). It departs on purpose in the list itself:
  the plant groups by use (lifting, material handling, vehicles), because its statutory
  checks and its people think that way. ISO 14224 allows a plant to adapt its lists.
- **OSH Code 2020 and its rules** (Occupational Safety, Health and Working Conditions Code;
  in force, confirmed by KLA 27-10-2026; it replaced the Factories Act 1948, whose
  ss. 28–29 held these rules; the clause of the rules *to verify*, BR1-07): lifts and hoists are examined by a competent
  person at least every 6 months; lifting machines, chains, ropes and lifting tackle at least
  every 12 months. This is the main later use: one statutory plan applied to every class in
  *Lifting equipment* (Plan.MD § 4.3, *Certification plans*).
- **EN 13306** names run-to-failure as a valid maintenance strategy. *Power tools* is the
  typical category for it, which is why the category will help when strategies are chosen
  (Plan.MD § 4.1, *Maintenance strategy*, Proposed).
- **SMRP** metrics (MTBF, downtime) are compared across equipment of a kind. A category is
  one more level to group them at, once reports exist.
- **ISO 55001 § 7.5** (information requirements): know what assets you have. A grouped
  register makes "all lifting equipment" a list a person can print and check.

## 3. Where

### Backend

- `backend/local_db.py`: migration **v35** (§ 4.1). No precondition: the table is new and the
  column is nullable.
- `backend/masters_core.py`: `_CATEGORY_FIELDS` (name, active), `validate_equipment_category`,
  `CATEGORY_NAME_MAX = 50`; `_CLASS_FIELDS` gains `category_id` (`_parse_optional_id("Category")`,
  not required).
- `backend/masters.py`:
  - the three category routes (§ 6);
  - the class routes read and return the category (§ 5.2). `create_equipment_class` gains
    `with transaction(conn), conn.cursor() as cur:` around the category lock and the insert,
    and re-reads the row after it, on the shape of `create_equipment_model` (BR1-02): on the
    autocommit connection a `FOR UPDATE` alone would lock nothing;
  - the `UNIQUE_KEY_ERRORS` entry `uq_equipment_categories_name`;
  - the docstrings: the module's lock notes gain the category (§ 5.3), and
    `_lock_active_parent`'s first line names the category too (BR1-12).
- `backend/equipment.py`: `_list_filters` gains `("category_id", "c.category_id")` in its loop,
  and its docstring names the category. `NODE_JOINS` already joins `equipment_classes c`, so
  both the list and the asset list get it.

### Frontend

- `frontend/src/stores/masters.js`: `equipmentCategories`, `ensureEquipmentCategories`,
  cleared in `resetMasters`.
- `frontend/src/views/masters/EquipmentCategoriesPanel.vue` (new), on the pattern of
  `TradesPanel.vue` and `useMasterForm`.
- `frontend/src/views/MastersView.vue`: the section `{ key: "categories", icon:
  "fa-solid fa-layer-group", label: "Equip Category", perm: "masters:read" }`, placed before
  *Equip Class*.
- `frontend/src/views/masters/EquipmentClassesPanel.vue`: the Category select in the dialog
  and the Category column (§ 5.2, *The dialog*).
- `frontend/src/utils/equipmentFilters.js` (new, pure): `classChoicesFor(classes, categoryId,
  selectedClassId)` and `classOutsideCategory(classes, categoryId, classId)` (§ 5.4).
- `frontend/src/views/EquipmentView.vue`: the Category select, `category_id` in `listUrl()`
  and in the query keys, the narrowed class choices.
- `frontend/src/utils/assetList.js`: `category_id` in `FILTER_KEYS`; `filtersLabel` names it
  first, from `lookups.categories`.
- `frontend/src/views/AssetListPrintView.vue`: loads the categories and passes them in the
  lookups.

### Tests

- `backend/tests/test_migration_v35.py` (new), on the pattern of `test_migration_v34.py`.
- `backend/tests/test_migration_v34.py`: unchanged; it slices `range(20, 35)`, so v35 does not
  touch it (checked: `VERSIONS = list(range(20, 35))`, line 21).
- `backend/tests/test_masters_api.py`: category routes, the class's category (§ 8.2).
- `backend/tests/test_masters_core.py`: the category fields and the class's `category_id`.
- `backend/tests/test_equipment_api.py` and `backend/tests/test_asset_list_api.py`: the filter.
- `backend/tests/conftest.py`: `equipment_categories` joins `_TABLES` (no seed rows, so it is
  emptied like every other table). Order does not matter: the fixture deletes with
  `FOREIGN_KEY_CHECKS = 0` (`conftest.py`, `_clean_tables`).
- `frontend/tests/equipmentFilters.test.js` (new) and `frontend/tests/assetList.test.js`.
- `frontend/e2e/masters.spec.js`, `frontend/e2e/equipment.spec.js`,
  `frontend/e2e/asset-list.spec.js` (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the new table, the class's column, the Mermaid
  overview, the "migration v35" line.
- `docs/Plan.MD` § 4.1: an *Equipment category* bullet after *Equipment class*; § 2 *Not in
  v1*: the equipment-groups line says categories group classes and are built (S063).
- `docs/Maintenance-Philosophy.md`: the glossary row *Equipment category*.

## 4. Data model

### 4.1 Migration v35

```sql
CREATE TABLE IF NOT EXISTS equipment_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    active      TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  VARCHAR(100) NOT NULL,
    updated_at  DATETIME NULL,
    updated_by  VARCHAR(100) NULL,
    CONSTRAINT uq_equipment_categories_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE equipment_classes
    ADD COLUMN IF NOT EXISTS category_id INT NULL AFTER name,
    ADD CONSTRAINT fk_equipment_classes_category
        FOREIGN KEY IF NOT EXISTS (category_id) REFERENCES equipment_categories (id);
```

- **Re-run safety:** `IF NOT EXISTS` on the table, the column and the key, so a half-applied
  v35 runs again. No earlier migration adds a foreign key to an existing table, so MariaDB's
  `FOREIGN KEY IF NOT EXISTS` form is *to verify* by the coder in `test_migration_v35.py`
  (a re-run changes nothing; `_schema()` in `test_migration_v20.py` compares the referential
  constraints and indexes, so a doubled key fails it). **Fallback** if that form does not
  work: `DROP FOREIGN KEY IF EXISTS fk_equipment_classes_category`, then `ADD CONSTRAINT …
  FOREIGN KEY`, the drop-then-add shape v34 uses for its CHECKs (BR1-10).
- **Existing rows:** every class gets `category_id` NULL. No row changes otherwise.
- **No seed rows** (Q1).
- **Rollback:** the previous release reads `SELECT *` from classes and ignores the extra
  column; the new table is unused.
- **No precondition:** nothing in production can conflict with a new table and a nullable
  column.

### 4.2 Suggested names (not seeded; for KLA to create, Q1)

| Name | Classes it would hold (examples) |
|---|---|
| Process machines | presses, extruders, mills, mixers, kilns, dryers |
| Conveyors | belt and screw conveyors, bucket elevators, feeders |
| Lifting equipment | EOT cranes, hoists, chain blocks, slings |
| Material handling | forklifts, pallet trucks, stackers (MHE) |
| Vehicles | road vehicles, tractors, earth movers |
| Power generation | diesel generators (DG), solar plant |
| Electrical distribution | transformers, panels, MCCs, capacitor banks |
| Utilities | compressors, pumps, blowers, water treatment |
| Pressure vessels | air receivers, boilers, autoclaves (statutory examination; Plant-Facts § 4) |
| Measuring instruments | verniers, multimeters, weigh scales (calibration, Plan.MD § 4.3; ISO 9001 § 7.1.5) |
| Workshop machines | lathes, surface grinders, drilling machines, welding sets |
| Power tools | hand drills, angle grinders, cutters |
| Safety and fire | fire extinguishers, hydrants, alarms |

*Drives and transmission* is dropped (KLA, Q2). Part-level classes such as Gearbox and Motor
may stay with no category, or go in a category KLA creates. *Pressure vessels* and *Measuring
instruments* were added by BR1-08; KLA may ignore them.

## 5. Rules

### 5.1 The category

- **Name:** required, trimmed, 1–50 characters (`_parse_bounded_name`), unique in any case
  (the column's collation compares). A duplicate is refused beside the Name field: "A
  category with this name already exists".
- **Rename:** always allowed. No code is built from it, and classes refer to it by id.
- **Deactivate:** refused while an **active** class is in the category (KLA, Q3). Field
  `active`, so the message shows at the top of the dialog (`modalError`), as a class's
  "Deactivate this class's models first" does today (BR1-03). The text (scope B, BR1-13):
  "N active classes are in this category. Move them to another category first." (with N = 1:
  "1 active class is in this category. Move it to another category first."). Inactive
  classes do not block it.
- **Reactivate:** always allowed.
- **Never deleted** (Plan.MD § 4.1, master records are deactivated).

### 5.2 The class's category

- `category_id` is optional on create and update. Absent on a `PUT`: unchanged. `null`:
  no category. A non-integer, a boolean or < 1: 400 "Category must be a record id"
  (`_parse_optional_id`).
- **When the category is read** (BR1-01): the save locks the category and checks it exists
  and is active when (a) it sets a non-null `category_id` that differs from the stored one
  (a create counts as differing), or (b) it makes the class active again and the class keeps
  a category. Otherwise the category is not read.
- **Refusals:** unknown id: 400 "Unknown category" on `category_id`. Inactive: 409 "The
  category is inactive" on `category_id` in case (a), on `active` in case (b) (the model's
  convention, masters.py 550–553; BR1-11). In case (b) the text is "This class's category is
  inactive. Pick another category or No category, then reactivate." (KLA at gate B, CR1-03,
  28-10-2026).
- So nobody can move a class into an unknown or inactive category, and the foreign key never
  answers a 500. An inactive class may keep an inactive category (§ 5.1 allows that), and is
  refused when it is made active again, unless the same save picks an active category or
  *No category*.
- The class's other rules are unchanged (code frozen once in use, deactivate refused while
  active models).
- Responses of `GET / POST / PUT /api/masters/equipment-classes` carry `category_id` and
  `category_name` (`LEFT JOIN equipment_categories`; null with no category).
- **The dialog** (BR1-04, on the pattern of `ModelsPanel.vue`): the Category select lists
  *No category*, then the active categories by name, then the class's current category when
  it is inactive, marked "(inactive)", so an edit of the name alone never clears it.
  `fromRecord` carries `category_id`; `toBody` sends `null` for *No category* (`""`).

### 5.3 Locks

The masters module's order is class → type; the category comes **after the class**.

- **Class create** (now in a transaction, § 3): (1) the category row `FOR UPDATE` when § 5.2
  says it is read, (2) the insert. The insert takes a shared lock on the category through
  the foreign key.
- **Class update:** (1) the class row `FOR UPDATE` (`_lock_row`), (2) its plain checks as
  today, (3) the category row `FOR UPDATE` when § 5.2 says it is read
  (`_lock_active_parent(cur, "equipment_categories", id, field, "category")`), (4) the update.
- **Category update:** (1) the category row `FOR UPDATE`, (2) on deactivate, a plain count of
  the active classes with this `category_id`, (3) the update.
- **Why the count is safe:** a class write that moves a class into the category, or
  reactivates one in it, takes the category lock at (3) first. It waits for the deactivation
  to commit and then sees `active = 0` (a locking read sees the newest row), or it commits
  first and the count sees it. The count is the transaction's first plain read, so its
  snapshot starts after the lock is held (REPEATABLE READ). This is the pattern of
  "class deactivate: its row, then a plain count of its active models" in `masters.py`'s
  docstring.
- **No cycle:** the category update takes no class lock; the class update takes the category
  after its class. A class create takes only the category.

### 5.4 The equipment list's filter

- **The select:** *All categories*, then active categories by name, then inactive ones
  marked "(inactive)" (the class select's pattern). The key is `category_id` in the URL.
- **Class choices:** with a category chosen, the class select lists only that category's
  classes (`classChoicesFor`). A class already chosen that is outside it is still listed,
  last, so a hand-made URL never filters invisibly (the type select's rule).
- **Choosing a category** clears the class and the type when the chosen class is outside the
  new category (`classOutsideCategory`); a class inside it stays.
- **Choosing a class** does not change the category.
- **The level stays** (BR1-05): choosing a category does not widen the level, as choosing a
  class does not. A category of part-level classes shows "No equipment matches these
  filters." at the default *Machines* level until the user changes *Level*. One behaviour for
  class and category.
- **Server:** `category_id` is read by `int_arg(…, minimum=1)` like `class_id`. A bad value
  is 400 "category_id must be a whole number at least 1". An unknown or inactive category
  gives what the rows give: none, or its machines.
- **Meaning:** a node matches when its **own** class is in the category, at any level, as the
  class filter does. At the default level (*Machines*) this is the machine's class.
- **The asset list** carries `category_id` from the list (`assetListPath`). Filters choose
  machines and parts come with them (S015 § 4). The header reads "Category: <name>" first,
  or "Category: #<id>" when the name is not known.

### 5.5 Permissions

- `GET /api/masters/equipment-categories`: `masters:read`, as every master list.
- `POST` and `PUT`: `equipment:edit`, as classes. It is site-scoped, but a category is at no
  site, so `require_perm` checks it as the union (the class routes' rule).
- The panel hides *Add category* and *Edit* without `equipment:edit`, as the classes panel.
- The list filters need `equipment:read` as today. No new key; `config_rbac.py` is unchanged.

### 5.6 The database down

The new routes go through `get_db()` like the other masters: 503 when the database is down.
The panel shows the load error with its message, as the classes panel.

## 6. API

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/masters/equipment-categories` | `masters:read` | `include_inactive=1` | `{items: [{id, name, active, class_count, …audit}]}`, by name; `class_count` = active classes in it |
| `POST /api/masters/equipment-categories` | `equipment:edit` | `{name, active?}` | 201, the row |
| `PUT /api/masters/equipment-categories/<id>` | `equipment:edit` | `{name?, active?}` | the row; 404 unknown; 409 § 5.1 |
| `POST / PUT /api/masters/equipment-classes…` | `equipment:edit` | adds `category_id?` | adds `category_id`, `category_name` |
| `GET /api/equipment`, `GET /api/equipment/asset-list` | `equipment:read` | adds `category_id` | unchanged shape |

## 7. Design decisions

- **D1. The term *equipment category*,** ISO 14224's word. Rejected: *equipment group*,
  which Plan.MD already uses for hand-picked sets of machines.
- **D2. One category per class, on the class.** A machine gets it through its class. Rejected:
  a category per machine (two machines of one class could differ, and ISO 14224 compares
  classes); several categories per class (a class would be counted twice in a downtime
  total).
- **D3. A name only, no code.** A class code becomes the equipment code's prefix; a category
  builds nothing, so it needs no code. Rejected: a 2–4 letter code like the class.
- **D4. An empty table; KLA creates the categories** (KLA, Q1). Rejected: a seeded starting
  list.
- **D5. Deactivate refused while active classes are in it** (KLA, Q3), as a class with active
  models. Rejected: allow it and show the inactive category on its classes; a filter would
  then offer a category nobody can pick for a new class.
- **D6. A plain select in the filter row,** next to *Class*. Rejected: a category inside the
  *Filter by property* dialog; the category is a fixed fact of the class, not a property
  value.
- **D7. Mapping by hand in Masters.** Rejected: a guess in the migration from class names; a
  wrong guess is worse than a blank the engineer sees.
- **D8. `class_count` counts active classes only,** the number that blocks deactivation.
- **D9. The level stays when a category is chosen** (BR1-05 a), as for a class. Rejected:
  widening to *All levels* on the first pick, as search and the property filter do; the class
  and category filters would then behave differently.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v35.py`)

- A fresh database: the table (empty), the column, the foreign key.
- A v34 database with classes and equipment: every row kept, `category_id` NULL.
- A re-run of v35 changes nothing (no error, one foreign key, `_schema()` equal).

### 8.2 API (`backend/tests/test_masters_api.py`, `test_masters_core.py`)

Each test creates its own categories, with names from the file's unique helper (`uniq`), so
no run clashes with an earlier run's rows in the kept worker database (BR1-09).

- Category: create, rename, duplicate name in another case (400 beside `name`), empty and
  51-character names, deactivate with an active class (409 with the count and the text of
  § 5.1), deactivate with only an inactive class (200), reactivate.
- Class: create with a category, with `null`, with an unknown id (400), with an inactive one
  (409 on `category_id`), with `true` and `"3"` (400); create inactive with an unknown id
  (400, not 500); update without `category_id` keeps it; reactivating a class whose category
  is inactive (409 on `active`), and the same save with *No category* (200); the responses
  carry `category_name`.
- Permissions: an operator and a technician get 403 on `POST` / `PUT`; every role reads the
  list.
- `class_count` counts only active classes.
- The database down (`db_down` fixture, `conftest.py`): the category list answers 503.

### 8.3 List filter (`test_equipment_api.py`, `test_asset_list_api.py`)

- `category_id` returns the nodes of every class in it, and no other; with `class_id` both
  apply; `category_id=abc` and `0` give 400; an unknown id gives an empty list.
- The asset list filters machines by their class's category, and parts still come with their
  machine whatever their own category.

### 8.4 Automated (e2e, targeted: `masters.spec.js`, `equipment.spec.js`, `asset-list.spec.js`, `screens.spec.js`)

The e2e database has no categories (nothing is seeded); each test creates its own.

- **important** S063: the engineer opens *Equip Category*, adds a category, gives a class that
  category in *Equip Class*, and the classes table shows it in the Category column
  (`masters.spec.js`).
- S063: *Equip Category* joins the loop of sections whose empty *Add* is refused beside its
  field, with "Name is required" (`masters.spec.js`). The loop's first step expects a row,
  so the test creates one category by API first, or the coder adapts the loop entry.
- **important** S063: on the equipment list the engineer picks a category; the class select
  lists only its classes; the list shows only the machines of those classes; a reload keeps
  it (`equipment.spec.js`).
- S063: *Print asset list* with a category filter shows "Category: <name>" in the section
  header (`asset-list.spec.js`).
- Each dialog opened calls `expectDialogFits`. No test is `@device`: none checks a layout.

### 8.5 On a real device

None. Every check here is one a browser engine can judge.

### 8.6 Acceptance

All unit suites green; the targeted browser specs green; the whole-suite run (Normal) once at
the end; `docs/schema.md` and `docs/schema.html` show v35.

## 9. Open questions and assumptions

- **Q1. Seed a starting list?** Answered by KLA, 27-10-2026: **no**, an empty table; KLA
  creates the categories.
- **Q2. The suggested names.** Answered by KLA, 27-10-2026: drop *Drives and transmission*.
  The list is reference only (§ 4.2).
- **Q3. Deactivating a category with active classes in it.** Answered by KLA, 27-10-2026:
  refused until its classes move (D5).
- **Assumption:** the plant needs no category on the machine itself (a DG set used as a
  process machine stays in its class's category).
- **Assumption:** about 30–50 classes in production, so one engineer maps them in a sitting.
- **BR1-07, answered by KLA, 27-10-2026:** the OSH Code 2020 is in force (§ 2).

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 27-10-2026

KLA answered Q1–Q3 during the review (§ 9): no seed, *Drives and transmission* dropped,
deactivation refused.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): § 5.2 *When the category is read*; § 8.2 adds the inactive-create case. |
| BR1-02 minor | Accepted: § 3 masters.py, the create route gains a transaction; § 5.3. |
| BR1-03 minor | Accepted: § 5.1, the refusal shows at the top of the dialog. |
| BR1-04 minor | Accepted: § 5.2 *The dialog*. |
| BR1-05 minor | Accepted (a): § 5.4 *The level stays*; D9. |
| BR1-06 minor | Accepted: § 1 intro and § 2 say grouping, not a level. |
| BR1-07 minor | Accepted: § 2 names the OSH Code, with the date and clause *to verify*; § 9. |
| BR1-08 minor | Accepted (a) as suggestions only: § 4.2 lists *Pressure vessels* and *Measuring instruments*; nothing is seeded (Q1). |
| BR1-09 minor | Accepted, reduced: no seed rows remain (Q1); § 8.2 still has each test create its own names. |
| BR1-10…BR1-14 nits | Accepted: BR1-10 § 4.1 fallback; BR1-11 § 5.2 field `active`; BR1-12 § 3 docstrings (the conftest comment is moot without seed rows); BR1-13 § 5.1 text; BR1-14 § 2 title. |
