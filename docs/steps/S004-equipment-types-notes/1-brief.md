```
Step: S004 — Equipment types and notes
Doc: brief
Author: Planner (Opus)
Date: 15-10-2026 (revised 15-10-2026 after brief-reviews r1 and r2)
Status: Done (committed 226ce67, 15-10-2026)
```

# S004 — Equipment types and notes

Builds on S002 (equipment backend) and S003 (screens), both Done (6d58ce5).

Background reading:
- `docs/steps/S002-equipment-register/1-brief.md` § 5–7 (data model, rules,
  locking, events, API) and its `3-impl-report.md`;
- `docs/steps/S003-equipment-screens/1-brief.md` § 4–5 (dialogs, labels,
  `useFormModal`);
- `docs/steps/S001-basic-masters/1-brief.md` (masters patterns);
- `docs/Plan.MD` § 4.1.

## 1. What will be built

The user's example (15-10-2026): `RPP001`, class `RPP` (radial piston pump),
model 11 RCE, serial 123123. The class is broad: radial piston pumps come as
**closed execution** or **open execution**, and that difference should be
recorded so it can be filtered and compared.

1. **Equipment types, per class.** A small master list: each class can have
   types, e.g. `RPP` → *Closed execution*, *Open execution*. Each node of the
   equipment tree can have **one type of its own class**, or none.
   - Managed in **Masters → Equipment types**, by the same people who manage
     classes (`equipment:edit`).
   - The equipment list can be **filtered by type**.
   - A type change is recorded in the equipment's **history**, like a class change.
2. **Notes on equipment.** A free-text field, several lines, for anything that
   doesn't fit a column (mounting, ratings, where the manual is).
   - **No change history** for notes (user, 15-10-2026). The record's "last
     updated by / when" still shows who changed it.
   - The list's **search** also looks in notes (user, 15-10-2026).

**Out of scope:**
- types without a class (a generic list); properties that cut across classes,
  such as "flameproof" (§ 9.1);
- attributes per class or type (kW, pressure, …): ISO 14224's
  "equipment-specific data", later if needed;
- importing types or notes in bulk;
- reporting by type (it comes with breakdowns and KPIs).

## 2. Standards and practice

- **ISO 14224 taxonomy: equipment class and equipment type.** ISO 14224 (the
  standard for reliability and maintenance data) classifies each equipment unit
  by **class** (what it is: pump, compressor, electric motor) and, within the
  class, by **type** (how it is built: a pump is centrifugal, reciprocating or
  rotary; ISO 14224 Annex A lists the types per class). A type always belongs to
  one class. Yantra follows that: types are defined **per class**, and an
  equipment's type must belong to its class. This is what makes later
  comparisons meaningful: the standard's point is that reliability figures are
  only comparable within a class/type pair, so "the MTBF of closed-execution
  radial piston pumps" compares like with like. *Closed / open execution* is a
  plant-specific type under a plant-specific class, which the standard allows:
  its lists are typical, not closed.
- **Data quality over free text (ISO 14224 clause 6, data quality; ISO 55001
  § 7.5, 2014 numbering).** ISO 14224 warns that free text can't be counted or compared, and
  ISO 55001 § 7.5 (information requirements) asks for asset information of a
  known quality. So anything the plant wants to *filter or compare* by goes into
  a structured field (the type); the notes field is for reading only. That is
  the line between the two features in this step. Notes are not a departure:
  ISO 14224's common equipment data (Table 5) has a free-text **remarks** item
  for exactly this.
- **ISO 27001:2022 A.5.12 (classification of information).** Notes are readable
  by every role with `equipment:read` at that unit, operators included. Nothing
  sensitive belongs there: no control-panel passwords, no AMC prices. The field's
  help text says so.
- **ISO 55001 § 8.2 (management of change; 2014 numbering).** A type change reclassifies the
  equipment, so it is logged like a class change. Notes are reference text, and
  by the user's decision are not logged; the audit columns still show the last
  change.

## 3. Where

### Backend

- **Migration v5** in `backend/local_db.py`: the five statements of § 4.1,
  verbatim.
- **`backend/masters_core.py`:** `validate_equipment_type(data, creating)`: pure,
  in the shape of the other masters validators: a `_TYPE_FIELDS` table like
  `_CLASS_FIELDS`, with `class_id` (an id), `name` and **`active`**, so a
  Deactivate/Reactivate `PUT {active}` reaches the update (without `active` it
  would be a silent no-op) (BR2-01). It rejects the name `none` (any case),
  which history uses for "no type" (BR1-06). Whether `class_id` *changed* is
  decided by the shell (§ 5.1).
- **`backend/masters.py`:** `GET/POST /equipment-types`, `PUT /equipment-types/<id>`
  (§ 6.1). A `_lock_class_for_type(cur, class_id, field)` helper in the shape of
  `_lock_site_for_unit`; `field` is `class_id` on create and `active` on
  reactivation (§ 5.1, BR2-02).
  - `masters.py` registers `uq_equipment_types_class_name` → field `name`, "A type
    with this name already exists in this class" in `UNIQUE_KEY_ERRORS`, through
    its existing `update(...)` call: each module registers its own keys (BR2-04);
  - the `?site_id` parser `_site_filter` becomes a shared `_int_filter(name)`,
    used for `site_id` and `class_id` (BR2-04).
- **`backend/equipment_core.py`:**
  - `_fields`: `type_id` (nullable id) and `notes` through the existing
    `optional_text_parser("Notes", NOTES_MAX)` with `NOTES_MAX = 2000`; it
    already trims, keeps inner line breaks and turns empty into `None`
    (BR1-09);
  - `_TRACKED` gains `("type_name", "type")`; `_display` shows a missing type as
    `none`;
  - a pure `check_type_class(type_class_id, node_class_id)` returning the error
    message or `None`.
- **`backend/equipment.py`:**
  - `_NODE_FROM` gains `LEFT JOIN equipment_types t ON t.id = e.type_id`;
    `_NODE_COLUMNS` gains `e.type_id`, `t.name AS type_name`, `e.notes`;
  - `_LOCK_EQUIPMENT` also selects `type_id`, so "the node has a type" is
    decided from the locking read (S002 BR3-01; BR1-01);
  - a locking read `_LOCK_TYPE` and helper `_lock_type` (§ 5.3);
  - create and update apply the type rules of § 5.2, as written there;
  - the module docstring's lock order and its note on `masters.py` are updated
    (type between class and counter; masters locks class then type), and the
    counter is renumbered (6) in the `_next_code` comment too (BR1-03, BR2-04);
  - `_written_state` takes the type name from the type lock, as it does for unit
    and class codes;
  - the list gains the `type_id` filter, and `q` searches notes and the type name
    too (§ 5.4).
- **`backend/tests/`:** `test_masters_core.py`, `test_masters_api.py`,
  `test_equipment_core.py`, `test_equipment_api.py` (§ 8). Existing tests and
  fixtures that change (BR1-03):
  - `test_equipment_api.py::TestListing::test_row_fields` asserts the exact key
    set of a list row: it gains `type_id` and `type_name` and stays exact, which
    also guards "the list has no `notes`";
  - `conftest.py::_TABLES` gains `equipment_types`, between `equipment` and
    `equipment_classes`; a `make_type` fixture beside `make_equipment` (BR2-04).

### Frontend

- **`frontend/src/stores/masters.js`:** `ensureEquipmentTypes()` (all types, with
  inactive), cleared by `resetMasters()`.
- **`frontend/src/views/MastersView.vue`:** a section **Equipment types** (icon
  `fa-solid fa-sitemap`, perm `masters:read`) after Equipment classes.
- **`frontend/src/composables/useFormModal.js`** and **`useMasterForm.js`:** an
  optional `label(record)` parameter, default `(r) => r.full_code ?? r.code`,
  sets `editingLabel`; `useMasterForm` passes it through. The three existing
  panels don't change (BR1-04).
- **`frontend/src/views/masters/EquipmentTypesPanel.vue`** (new): the Units panel
  pattern: a class filter, a table, the create/edit dialog with
  Deactivate/Reactivate (`useMasterForm`, `ActiveToggle`), labelled
  `` (t) => `${t.class_code} · ${t.name}` ``.
  - **Create:** a class `<select>` (active classes) with its field error, and
    the name.
  - **Edit:** the class as plain text; the form **doesn't send `class_id`**. Only
    the name is sent; activation goes through `ActiveToggle` (BR1-04).
- **`frontend/src/views/equipment/EquipmentFormModal.vue`:**
  - **Type** after Class: "— none —" plus the active types of the chosen class
    (the current type stays listed, marked "(inactive)", when inactive). A class
    with no types shows only "— none —"; no extra empty state.
  - Changing the class **resets Type to none through `@change` on the class
    `<select>`**, as the site select resets the unit. Not a `watch` on
    `form.class_id`, which would fire when `fromRecord` fills the form and clear
    the type as the edit dialog opens (BR1-07);
  - **Notes**: a 4-row textarea, `maxlength` 2000, at the end of the form, with
    the help text "Visible to everyone who can see this equipment — no passwords
    or prices" (§ 2);
  - `fromRecord` gains `type_id: node.type_id ?? ""` and `notes: node.notes ??
    ""`; `toBody` sends `type_id` (`""` → `null`) and `notes` (empty → `null`).
    S003 § 5.3's "Edit sends …" list is thereby extended with `type_id` and
    `notes`;
  - `ensureEquipmentTypes()` is awaited when the dialog opens;
  - Type and Notes each render `fieldError("type_id")` / `fieldError("notes")`
    (S003 § 5.7): otherwise a 409 "The type is inactive" would be shown nowhere,
    since `modalError` hides errors on fields the form has (BR2-03).
- **`frontend/src/views/EquipmentDetailView.vue`:** Type in Details; a **Notes**
  block below Details when notes exist, written as entered (`white-space:
  pre-wrap`, which also keeps aligned spacing) (BR1-07). The page needs no
  types cache: `type_name` is in the response.
- **`frontend/src/views/EquipmentView.vue`:**
  - a **Type** filter, shown when a class is chosen **or** `type_id` is in the
    URL (so a bookmarked type filter is never applied invisibly). With a class,
    it lists that class's types; with only `type_id`, it lists all types,
    labelled `RPP · Closed execution` (BR2-05). Inactive ones are marked
    "(inactive)", since equipment can still carry them;
  - choosing a class **always** clears `type_id`, as choosing a site clears
    `unit_id`;
    `listUrl()`'s keys gain `type_id`; `ensureEquipmentTypes()` joins the list's
    `Promise.all` (BR1-07);
  - the Class cell shows the type after the class code, muted: `RPP · Closed
    execution`.
- **`frontend/src/utils/equipmentLabels.js`:** `describeEvent` for `type`:
  "Type: Closed execution → Open execution", with `none` shown as "None".
- **Tests:** `frontend/tests/equipmentLabels.test.js`.

### Docs

None for the coder. At approval the planner records (BR1-10):
- Plan § 4.1: `type` and `notes` in the field list, and the class/type rule;
- Plan § 2: next to "no per-class custom fields", that a type is a pick-list
  value within a class, not a custom attribute;
- Plan § 5: the `equipment_types` row;
- Maintenance-Philosophy § 12 glossary: "Equipment type".

## 4. Data model (migration v5)

**`equipment_types`**: the audit convention of S001 § 4.

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `class_id` | `INT NOT NULL`. `fk_equipment_types_class` → `equipment_classes`. **Fixed after create** |
| `name` | `VARCHAR(100) NOT NULL`, e.g. "Closed execution" |
| `active` | `TINYINT(1) NOT NULL DEFAULT 1` |
| audit | `created_at`, `created_by`, `updated_at`, `updated_by` |

- `uq_equipment_types_class_name UNIQUE (class_id, name)`: no two types of one
  class with the same name. The table's default collation makes it
  case-insensitive, so "Closed execution" and "closed execution" clash.
- `uq_equipment_types_id_class UNIQUE (id, class_id)`: the target of the
  composite FK below.
- **No code.** A type doesn't appear in equipment codes, so a name is enough.

**`equipment`** gains:

| Column | Type / rule |
|---|---|
| `type_id` | `INT NULL` |
| `notes` | `TEXT NULL`; the shell limits it to 2000 characters |

- **`fk_equipment_type FOREIGN KEY (type_id, class_id) REFERENCES equipment_types (id, class_id)`.**
  With `type_id` NULL the FK isn't checked; with a type, the database itself
  guarantees that **the type belongs to the equipment's class**, as the CHECK in
  S002 guards the tree shape. The shell still validates first (§ 5.2), so this
  is a backstop: a violation would be a logged 500, never a normal path.

**`equipment_events.event`** gains `type`. Old and new values are the type names
(text snapshots, S002 § 6 Events); `none` when there is no type.

### 4.1 Migration v5, verbatim (BR1-02)

`init_db` runs statements one by one and records the version only after the
last. MariaDB DDL isn't transactional, so a failure half-way leaves the earlier
statements applied, and the 30-second `ensure_schema()` retry would then fail
on them forever. So **every statement is safe to run twice**:

```sql
CREATE TABLE IF NOT EXISTS equipment_types (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    class_id    INT NOT NULL,
    name        VARCHAR(100) NOT NULL,
    active      TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  VARCHAR(100) NOT NULL,
    updated_at  DATETIME NULL,
    updated_by  VARCHAR(100) NULL,
    CONSTRAINT uq_equipment_types_class_name UNIQUE (class_id, name),
    CONSTRAINT uq_equipment_types_id_class UNIQUE (id, class_id),
    CONSTRAINT fk_equipment_types_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4

ALTER TABLE equipment ADD COLUMN IF NOT EXISTS type_id INT NULL AFTER class_id

ALTER TABLE equipment ADD COLUMN IF NOT EXISTS notes TEXT NULL

ALTER TABLE equipment ADD CONSTRAINT fk_equipment_type FOREIGN KEY IF NOT EXISTS
    (type_id, class_id) REFERENCES equipment_types (id, class_id)

ALTER TABLE equipment_events MODIFY event
    ENUM('created','moved_unit','moved_parent','status','criticality','class','type') NOT NULL
```

- The audit columns are those of the S001 masters tables (v2).
- `uq_equipment_types_id_class` is the index InnoDB needs on the referenced side,
  so it is in the `CREATE TABLE`, which runs before the FK. InnoDB adds the
  referencing index on `(type_id, class_id)` itself. Both sides are `INT`.
- Existing equipment rows pass the FK: `type_id` is NULL, and a composite FK
  isn't checked when any of its columns is NULL.
- The ENUM statement restates `NOT NULL` and keeps the six values **in their
  order**, appending `type` at the end: a metadata-only change, old rows
  untouched. `MODIFY` is idempotent by nature.

## 5. Rules

### 5.1 Types (masters)

- Name: required, trimmed, 1–100 characters; unique within its class → **409**,
  field `name`.
- Name `none` (any case) → 400, field `name`: history uses it for "no type"
  (BR1-06).
- `class_id`: required on create. The shell **locks the class row first**
  (`_lock_class_for_type`, like `_lock_site_for_unit`): missing → 400, inactive →
  409, both field `class_id`. Then it inserts (BR1-05).
- `class_id` **can't change** afterwards. The validator only parses it; the
  shell compares it with the locked type row: different → 400 "Class cannot be
  changed", field `class_id`; the same value is accepted (the S001 pattern for a
  unit's site) (BR1-05).
- A type created under the wrong class is deactivated and created again.
- **Reactivating** a type (`active: 1`) locks its class and requires it active,
  else 409, field `active`, "The class is inactive". As for units under an
  inactive site (BR1-05).
- **The PUT's order** (BR2-02): a plain read of the type (unknown → 404); when
  reactivating, lock the **stored** class (field `active`); lock the type; then
  compare a sent `class_id` with the locked type's (→ 400 if different).
- **Renaming** is always allowed: types have no code, and history keeps the old
  name as text.
- **Deactivating** is always allowed: equipment that has the type keeps it; it
  just can't be newly chosen. No "in use" check is needed.
- `GET ?class_id=x` with a non-number → 400, field `class_id`, as `_site_filter`
  does.
- No delete (as for every master).

### 5.2 An equipment's type

- Optional at every level (equipment, component-unit, component), because every
  node has a class.
- **A type must belong to the node's class** after the write, and a class change
  needs a type decision; the type is **never cleared silently**. The PUT applies
  this, every decision from a locking read (BR1-01):

  ```
  locked = _LOCK_EQUIPMENT row (now with type_id)
  sent_type = "type_id" in the body as sent, before unchanged fields are dropped
  clean = validated body; parent_id, unit_id, class_id and type_id are dropped
          when equal to the locked row's value
  class_changes = "class_id" in clean
  new_class = clean.get("class_id", locked["class_id"])
  resulting_type = clean.get("type_id", locked["type_id"])

  if class_changes and locked["type_id"] is not None and not sent_type:
      400 type_id "Pick a type of the new class, or none"
  if resulting_type is not None and ("type_id" in clean or class_changes):
      t = _lock_type(resulting_type)                       # (5) in the lock order
      t is None                  -> 400 type_id "Unknown type"
      t.class_id != new_class    -> 400 type_id "This type belongs to another class"
      "type_id" in clean and not t.active
                                 -> 409 type_id "The type is inactive"
  ```

  What this gives:

  | PUT | Result |
  |---|---|
  | type and class unchanged | no type lock |
  | a new type | lock; class and active checked |
  | class changed, `type_id: null` | no lock; `class` and `type` (X → none) events |
  | class changed, a type of the new class | lock; class checked |
  | class changed, the **old** type sent back | lock; 400 "belongs to another class" |
  | class changed, nothing about type, node typed | 400 "Pick a type of the new class, or none" |
  | other fields only, type deactivated since | 200: keeping it is allowed (no active check) |

  So the composite FK never fires on a normal path; it stays a backstop.
- **Create:** the class is `clean["class_id"]`. When `type_id` is present and not
  null, the type is locked after the class: unknown 400, other class 400,
  inactive 409. A `type_id: null` on create is dropped, like a `None`
  `parent_id`.
- The edit dialog always sends `type_id` and resets it when the class changes, so
  users meet the 400s only through the API.
- **Events compare type names** (BR1-06). Reclassifying `RPP` / *Standard* to
  `HP` / *Standard* in one PUT writes a `class` event and **no** `type` event,
  because the name is the same; this is accepted, as S002 accepted similar
  display-only residuals. The **before** name comes from the plain snapshot,
  which is display only, as S002 CR1-01 recorded for site codes.
- Message texts: "Unknown type", "This type belongs to another class", "The type
  is inactive", "Pick a type of the new class, or none", "Class cannot be
  changed", "A type with this name already exists in this class" (BR1-09).
- A scrapped node stays read-only (S002), type and notes included.

### 5.3 Locking

S002's single global lock order gains the type, between class and counter:

**node → target parent → unit → class → type → serial_counters**

- `_LOCK_TYPE = "SELECT id, class_id, name, active FROM equipment_types WHERE id = %s FOR UPDATE"`.
- Taken when § 5.2's algorithm needs it: a new type, or a class change with a
  resulting type.
- Decisions come from the locked rows (S002 BR3-01): the node's `type_id` from
  `_LOCK_EQUIPMENT`; the type's existence, `active` and `class_id` from
  `_LOCK_TYPE`.
- **Masters** locks class → type, the same order as `equipment.py`:
  - `POST /equipment-types` locks the class row, then inserts;
  - `PUT /equipment-types/<id>`, when reactivating, must lock the class too. To
    keep the one order (class → type), it **reads the type's `class_id` with a
    plain read** (safe: a type's class never changes), **locks the class, then
    the type**. Other PUTs lock the type only.

  Neither locks equipment, so no lock cycle is added. A type deactivated while an
  equipment write waits for its lock is seen as inactive by that write.
- `class_id` of a type never changes, so the class match can't be undone by a
  concurrent type edit.

### 5.4 Notes and search

- `notes`: optional; trimmed at both ends; empty → `NULL`; at most 2000
  characters → else **400**, field `notes`. Inner line breaks are kept.
- Not tracked in events (user). The audit columns are updated as for any field.
- **Search** `q` matches code, name, **notes** and **the type name** (all
  `LIKE %q%`, escaped as today). Matching the type name means "closed" finds
  closed-execution pumps even when their names don't say so.
- `type_id` list filter: a positive integer, else 400; combined with the others
  by AND.

### 5.5 API shapes

- **List rows and detail** gain `type_id` and `type_name` (`null` when none);
  the **detail** also gains `notes`. The list doesn't return notes (they can be
  long).
- **Create and PUT** accept `type_id` and `notes`.

## 6. API

### 6.1 Masters (`/api/masters/equipment-types`)

| Method and path | Permission |
|---|---|
| `GET /equipment-types?class_id=&include_inactive=1` | `masters:read` |
| `POST /equipment-types` `{class_id, name}` | `equipment:edit` |
| `PUT /equipment-types/<id>` `{name?, active?}` | `equipment:edit` |

- Items: `id`, `class_id`, `class_code`, `name`, `active`, audit. Ordered by
  class code, then name. Not paginated (small, as all masters).
- Inactive hidden unless `include_inactive=1`; `class_id` filter optional.

### 6.2 Equipment

No new endpoints; § 5.5 lists the changed shapes.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Types **per class** (user, 15-10-2026) | ISO 14224: a type belongs to a class; no nonsense pairs; comparisons stay like-for-like | One generic list for all classes |
| A composite FK `(type_id, class_id)` | The database guarantees the type matches the class, like S002's CHECK | Shell check only |
| A class change without a type decision → 400 | No silent side effect (CLAUDE-COMMON "explicit over implicit") | Clearing the type automatically |
| A type's class is fixed; renaming allowed | Keeps the composite FK and the history simple; types have no code | Moving a type to another class |
| Types have a name, no code | They don't build equipment codes | A short code per type |
| Type changes logged; notes not | ISO 55001 § 8.2 for reclassification; notes are reference text (user) | Logging both; logging neither |
| Search covers notes and the type name | Notes: user; type name: "closed" finds closed-execution pumps | Separate searches |
| `notes` as `TEXT`, limit 2000 in the shell | Room for a few paragraphs; the limit keeps pages readable | `VARCHAR(500)`; no limit |
| Types managed in a Masters section of their own | Same pattern as units under sites; the class panel stays simple | Types inside the class dialog |
| The type rule as an algorithm on the locked rows | No path reaches the FK as a 500; every decision from a locking read (BR1-01) | Locking the type only when it changes |
| Every v5 statement safe to run twice | DDL isn't transactional; a half-applied v5 must not block `ensure_schema` forever (BR1-02) | Plain `CREATE`/`ADD` |
| Type events compare names; the name `none` is reserved | Simple; the only miss (same name across a class change) still has its `class` event (BR1-06) | Comparing ids with a separate display key |
| Lock order node → parent → unit → class → **type** → counter | Extends S002's one global order; single-row lock | Locking the type before the class |

## 8. Tests and acceptance

### Pure

- `validate_equipment_type`: name required/blank/101 characters/`None`/`NONE`;
  `class_id` required on create, parsed as an id on update. (The changed-class
  rule is the shell's; its tests are API tests.)
- `validate_equipment`: `type_id` null and id; `notes` empty → null, 2000 OK,
  2001 → error, line breaks kept.
- `check_type_class`: match, mismatch.
- `tracked_changes`: type set, changed, cleared (`none`); notes change gives no
  event.

### API

- **Masters:** create, list (filter, inactive, bad `class_id` → 400), rename,
  deactivate/reactivate; duplicate name in a class → 409 (case-insensitive);
  the same name in another class is fine; inactive class on create → 409;
  reactivating under an inactive class → 409; class change → 400, the same
  `class_id` sent back → 200; RBAC: engineer can write, operator 403, every role
  reads.
- **Equipment:**
  - create with a type of its class → 201, `type_name` in the response, a
    `created` event only;
  - type of another class → 400 `type_id`; unknown → 400; inactive → 409;
  - keeping a type deactivated later: PUT other fields → 200;
  - set, change, clear the type → one `type` event each, with names;
  - class change while typed, no `type_id` → 400 `type_id`; with `type_id: null`
    → 200, `class` and `type` events; with a type of the new class → 200; with
    the **old** type sent back → 400 `type_id` (not a 500);
  - the same type name in two classes: reclassify across them → a `class` event
    only (§ 5.2, accepted);
  - notes: saved with line breaks, 2001 characters → 400, no event on change,
    `updated_by` set;
  - list: `type_id` filter; `q` finds by a word in notes and in the type name;
    list rows have no `notes`;
  - scrapped node: type or notes PUT → 409 (S002 rule).
- **Migration (manual check, not in the suite** — the test DB is always brought
  to the latest version; BR1-02): the dev DB, at v4 with S002/S003 rows,
  migrates to v5; existing rows get `type_id` and `notes` NULL; old events keep
  their values; running the five statements a second time by hand gives no
  error.

### Frontend (vitest)

- `describeEvent` for `type`: set (None → X), change, clear (X → None).

### Manual checks (user)

- Masters → Equipment types: add *Closed execution* and *Open execution* under
  `RPP`; a duplicate is refused; deactivate one.
- Equipment `RPP001`: pick a type; the inactive type isn't offered; change the
  class in the dialog and see Type reset; notes with several lines show as
  written on the page.
- List: filter by class `RPP` then type; search a word from the notes.
- History shows type changes and no notes changes.
- Masters → Equipment types: the deactivate confirmation names "RPP · Closed
  execution".

### Acceptance

- `tooling/run-tests.bat` green; `npx vite build` clean.
- The user can record `RPP001` as *RPP · Closed execution* with notes, and find
  it by type filter and by a word in its notes.

## 9. Open questions and assumptions

1. **Decided (user, 15-10-2026) — per-class types** (ISO 14224);
   cross-class properties like "flameproof" go in notes for now.
2. **Decided (user, 15-10-2026) — search on the type name** in addition to notes.
3. **Assumption:** every level may have a type (a motor component can be
   "squirrel cage").
4. **Assumption:** 2000 characters is enough for notes.
5. **Rule (was an assumption):** types of an inactive class stay as they are; a
   class can't get new or reactivated types while inactive (§ 5.1).

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 15-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 The class-change rule leaves a path to a 500 | major | **Accepted, option (a).** § 5.2 now gives the PUT algorithm on the locked rows, with a table of cases; `_LOCK_EQUIPMENT` gains `type_id`; create rule stated; tests for the old type sent back (§ 3, § 5.2, § 5.3, § 8). |
| BR1-02 Migration v5 statements and re-run safety | minor | **Accepted, option (a).** § 4.1 gives the five statements verbatim, each safe to run twice, `NOT NULL` restated, `type` appended; the v4 → v5 test is a manual dev-DB check. |
| BR1-03 Breaking tests and fixtures | minor | **Accepted.** `test_row_fields`, `conftest._TABLES` and the `equipment.py` docstring named (§ 3). |
| BR1-04 `useFormModal` labels by code | minor | **Accepted, option (a).** Optional `label(record)` parameter; the types edit form shows the class as text and doesn't send `class_id` (§ 3). |
| BR1-05 Validator vs shell; masters locks; reactivation; unique key | minor | **Accepted.** The shell decides a changed class; POST locks the class first; reactivation needs an active class; the masters PUT keeps class → type order; `UNIQUE_KEY_ERRORS` entry; bad `class_id` filter → 400 (§ 3, § 5.1, § 5.3). |
| BR1-06 Type events compare names | minor | **Accepted, option (a).** The same-name miss accepted and stated; the name `none` reserved (§ 3, § 5.1, § 5.2). |
| BR1-07 Frontend specifics | minor | **Accepted.** `@change` reset, `toBody`/`fromRecord`, cache call sites, type filter rules, "(inactive)", `pre-wrap` (§ 3). |
| BR1-08 Standards corrections | minor | **Accepted.** "Equipment-specific data"; Table 5 remarks; plant-specific types allowed; ISO 55001 2014 numbering; ISO 27001 A.5.12 with a help text on the notes field (§ 1, § 2, § 3). |
| BR1-09 Small backend points | nit | **Accepted.** `optional_text_parser` reused; messages fixed; before-name from the snapshot stated; `type_id: null` dropped on create (§ 3, § 5.2). |
| BR1-10 Docs at approval | nit | **Accepted.** Plan § 2, § 4.1, § 5 and the glossary listed (§ 3 Docs). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 15-10-2026

All round-1 answers verified in the text; the § 5.2 algorithm walked through 15
cases and the migration checked on MariaDB 11.4. No blocker or major finding.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 `active` missing from the types validator | minor | **Accepted.** `_TYPE_FIELDS` with `active` (§ 3). |
| BR2-02 Lock helper field; PUT order | minor | **Accepted.** `_lock_class_for_type(cur, class_id, field)`; the PUT's order stated (§ 3, § 5.1). |
| BR2-03 Field errors for type and notes | minor | **Accepted.** Both render `fieldError` (§ 3). |
| BR2-04 Where the unique key is registered; small names | nit | **Accepted.** Registered in `masters.py`; `_int_filter(name)`; `make_type` fixture; counter (6) (§ 3). |
| BR2-05 Type filter without a class | nit | **Accepted.** All types, labelled with the class; choosing a class always clears the type (§ 3). |
| BR2-06 ISO 14224 data-quality clause | nit | **Accepted.** Clause 6 (§ 2). |

### Gate A — user decision, 15-10-2026

- **Approved**, with types per class and search on the type name (§ 9.1–9.2).
- Types are optional at every level; empty means no type (user question, answered).
- Coder: Opus (a new lock in the global order; a schema change).
