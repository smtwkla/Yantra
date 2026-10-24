Step: S035 — Equipment properties: master, classes and models
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026 (revised 24-10-2026: brief-review r1, r2)
Track: full
Baseline: 437d993 (stale check 24-10-2026: no code changed since)
Status: Approved 24-10-2026 by KLA (split kept: S036 queued)

# S035 — Equipment properties: master, classes and models

**The request (KLA, 24-10-2026).** Equipment models need technical data that the register
has no fields for: a motor's rating, a pump's displacement (cc/rev), maximum operating
pressure, flow rate, a pump's execution (open or closed), a valve's drain (internal or
external), its poppet type. These cannot be fields in the code. The masters need a list of
*custom fields* that can be linked to models, and the equipment made from a model then has
the data. A value is entered on the model, or overridden on one equipment item.

**User decisions (KLA, 24-10-2026), from the discussion before this brief:**

| # | Decision |
|---|---|
| U1 | Properties are linked to the **equipment class**, not to each model. Extra properties on one model of a class may come **later** (§ 1, *Out of scope*). |
| U2 | An override on an equipment item is **logged** in the equipment's history (S036). |
| U3 | The people who keep the equipment masters today define the properties. |
| U4 | The main classes start from **ISO 14224 Annex A** (seed, § 4.6). |
| U5 | No property is required; values arrive over time. |
| U6 | A class's properties are a **table** with an **Add property…** button. It opens the list of properties not yet on the class; several can be ticked, then **Add** (KLA at gate A, 24-10-2026). |

**This changes an earlier decision.** Plan.MD § 1 lists "Per-class custom fields (e.g. press
tonnage)" as out of scope for v1, and the *Equipment class* definition (Plan.MD § 4.1) says
"No class-specific custom fields in v1." S035 replaces both lines (§ 11).

**Split (proposed).** The whole feature has five tables and four screens, past the size rule
(more than one table and two screens). It is cut in two steps:

- **S035 (this brief):** the property master, the options of a choice property, the class
  links, the values on models, the seed, and a *Properties* card on the
  equipment page that shows the model's values.
- **S036 (queued):** an override per equipment item, logged in the equipment history (U2),
  with its dialog on the equipment page. S035 leaves the place for it (§ 4.5).

S035 is useful alone: most equipment items of one model share its nameplate data.

**Track: full.** A migration (v26) with new tables and a seed, new routes with locks, a new
module.

## 1. What will be built

1. **Properties** — a new section of *Masters*. A property has:
   - a **name** ("Power – design", "Displacement", "Drain"), unique in the list;
   - a **data type**: *number*, *choice*, *text* or *yes/no*;
   - a **unit** for a number ("kW", "bar", "cc/rev", "L/min"); none for the other types;
   - for a choice, its **options** ("Internal", "External");
   - an optional **description** (what the property means, where to read it);
   - an **active** flag. A property is never deleted; an inactive one is hidden everywhere
     except this list.
2. **Class properties** (U6). On *Masters › Equip Class*, a row's **Properties** button shows
   the class's properties as a **table** in the panel (name, type, unit, **Remove**), with
   **Add property…** above it. *Add property…* opens a dialog listing the active properties
   **not yet on the class**; the user ticks one or more and presses **Add properties**. A
   property can belong to any number of classes ("Power – design" serves pumps, motors and
   compressors). Details in § 7.2.
3. **Model values.** On *Masters › Models*, a row's **Properties** button opens a dialog with
   one input per property of the model's class, by data type. An empty input means "no
   value". Save stores the filled ones and clears the emptied ones.
4. **Properties card on the equipment page**, beside *Details*: each property of the item's
   class, with the model's value and unit, or "—". The card shows only when the class has
   at least one property. It shows the model's values, with the line "Values from model
   <model label>." Users with `equipment:edit` get **Edit model values** on the card, which
   opens the same model dialog as Masters (BR1-04). In S036 the item's own values join it.
5. **Seed** (migration v26): 22 properties after ISO 14224 Annex A for pumps, electric
   motors, compressors, valves, combustion engines and electric generators, plus common
   nameplate data (§ 4.6). The request's examples (displacement, maximum operating
   pressure, drain, poppet type) are **not** seeded: they are the kind of property the
   plant's engineers define themselves in *Masters › Properties*. The seed makes properties only. It links
   none to a class, because the plant's class codes are not known to the code (§ 9.5).

**Type or property (BR1-01).** How equipment of a class is **built** is its **type** (S004,
ISO 14224 class → type): a pump is centrifugal or reciprocating, an `RPP` is closed or open
execution. Yantra keeps that on the model's `type_id`, and the failure-code scoping and the
like-with-like comparisons read it. A **property** is a datum about the item: a rating, a
dimension, a design detail such as *Drain*. So the seed has no *Pump type*, *Motor type*,
*Compressor type*, *Valve type* or *Execution*: those are types, set up in *Masters › Equip
Type*. The help line of the property dialog says so (§ 7.1).

### Out of scope

- **Overrides on an equipment item** and their history: S036.
- **Extra properties on one model only** (U1, later): the tables leave room for it (§ 4.5).
- **Filtering or searching** the equipment list by a property ("every motor of 7.5 kW at
  1440 rpm"), and a **CSV import** of values: a later step.
- Properties on the **asset list** print or the **QR labels**.
- **Required** properties and **completeness** figures (U5).
- **Readings** (oil temperature, run hours): they change in operation and belong to the
  readings of Plan.MD § 6, not here.
- Formulas, properties shown only under a condition, number bounds (minimum and maximum),
  and ranges ("0–250 bar"; a range is two properties).
- A history of changes to a model's values or a class's links (masters keep `updated_at`
  and `updated_by` only, as today).
- Ordering the properties by hand: they show by name (§ 9.6).

## 2. Standards and practice

- **ISO 14224:2016, Annex A — equipment-specific data** (to verify: clause numbers and the
  exact property names against the standard's text). For each equipment class, Annex A lists
  the technical data worth recording: for pumps, for example, the design power, the design
  suction and discharge pressure, the speed, the number of stages and the shaft sealing. A
  property list per class is exactly that structure, and the seed takes its names from it,
  so data stays comparable between sites and with other plants. The seed's option lists
  (*Coupling*, *Shaft sealing*, *Actuation*) are also from memory: **to verify** against the
  text.
- **ISO 14224 — design and operating values** (BR1-02). Annex A's *design* value is the
  maker's rating (nameplate, data sheet). Its *operating* value is the actual service
  condition (the pressure and flow the pump runs at). In Yantra the model holds the design
  value (S035), and an item holds its own design value only where its nameplate differs
  from the model's (S036: a rewound motor now 5.5 kW). An operating value changes in
  service, so it is a reading (Plan.MD § 6), not a property. The seed names say "– design"
  where Annex A does.
- **ISO 55001 § 7.5 — asset information** (*Information requirements*). The organisation
  decides which information it keeps about its assets, and keeps its quality. The property
  master is that decision, made once in Masters instead of in each engineer's notebook.
- **ISO 14224 — equipment taxonomy.** Data belongs to the item it describes. A pump's drive
  motor is its own component of class *Electric motor*, so its power is a property of the
  motor, not "motor power" on the pump. The help line of the class's properties table says so (§ 7.2).
- **IEC 61360 — property dictionaries** (the basis of ECLASS): a property is defined once,
  with a data type and a unit, and reused across classes. Yantra follows that: one
  definition, linked to many classes, a unit fixed per property. Yantra departs from it in
  one point: no property codes from an outside dictionary, because the plant's set is small.
- **TPM — equipment knowledge.** TPM's autonomous and planned maintenance pillars start from
  knowing the equipment's design data (ratings, settings, materials). The properties make it
  visible on the shop floor, beside the tickets.

## 3. Where

### 3.1 Backend

| File | Change |
|---|---|
| `backend/local_db.py` | migration **v26** (§ 4.1, § 4.6); `LATEST_VERSION` follows |
| `backend/properties_core.py` (new) | pure: `validate_property`, `validate_option`, `parse_value(data_type, raw)`, `format_value(data_type, value, unit, option_label)`, `property_view(...)` for the card (§ 5) |
| `backend/properties.py` (new) | blueprint `properties_bp`: the routes of § 6; LOCK ORDER note (§ 5.6) |
| `backend/app.py` | `app.register_blueprint(properties_bp, url_prefix="/api/masters")`, beside `masters_bp` (line 173) |
| `backend/equipment.py` | `_detail()` (line 266) adds `properties` (§ 6.3), read through a helper in `properties.py` |

### 3.2 Backend tests

| File | Change |
|---|---|
| `backend/tests/test_properties_core.py` (new) | the pure rules (§ 8.1) |
| `backend/tests/test_properties_api.py` (new) | the routes, locks and permissions (§ 8.2) |
| `backend/tests/test_migration_v26.py` (new) | fresh database, upgrade from v25, re-run (§ 8.3), on the pattern of `test_migration_v25.py` |
| `backend/tests/conftest.py` | `model_property_values` and `class_properties` in `_TABLES` (line 139) before `equipment_models` and `equipment_classes`; the seeded `property_definitions` and `property_options` kept like the failure codes: `SEED_CREATOR = "migration-v11"` stays (`test_migration_v11.py` imports it), and a new `_SEED_CREATORS = {"failure_modes": SEED_CREATOR, …, "property_definitions": "migration-v26", "property_options": "migration-v26"}` drives `_clean_tables` (BR1-06); the `db_down` fixture moves here (BR1-16) |
| `backend/tests/test_access_control_api.py`, `backend/tests/test_auth.py` | their local `db_down` fixture removed; they use the one in `conftest.py`, unchanged in behaviour |
| `backend/tests/test_equipment_api.py` | a test of the detail's `properties` (§ 8.2) |

### 3.3 Frontend

| File | Change |
|---|---|
| `frontend/src/stores/masters.js` | `properties` ref and `ensureProperties()`, on the pattern of `equipmentModels` |
| `frontend/src/views/MastersView.vue` | the *Properties* section after *Models* (`perm: "masters:read"`) |
| `frontend/src/views/masters/PropertiesPanel.vue` (new) | the list, the create and edit dialog, the options of a choice (§ 7.1) |
| `frontend/src/views/masters/ClassPropertiesView.vue` (new) | the class's properties table in the panel, *Add property…*, *Remove*, *Back* (§ 7.2) |
| `frontend/src/views/masters/AddPropertiesModal.vue` (new) | the picker: search, tick boxes of the properties not yet on the class, *Add properties* (§ 7.2) |
| `frontend/src/views/masters/EquipmentClassesPanel.vue` | the row's *Properties* button, which shows `ClassPropertiesView` instead of the table, as `ModelsPanel.vue`'s *Documents* does |
| `frontend/src/views/masters/ModelPropertiesModal.vue` (new) | the value dialog (§ 7.3) |
| `frontend/src/views/masters/ModelsPanel.vue` | the row's *Properties* button and the dialog |
| `frontend/src/components/PropertyInput.vue` (new) | one input for one property by data type; S036 reuses it |
| `frontend/src/utils/propertyFormat.js` (new) | the display of a value with its unit, the data-type labels |
| `frontend/src/views/EquipmentDetailView.vue` | the *Properties* card and its **Edit model values** button, which opens `ModelPropertiesModal` (§ 7.4) |

### 3.4 Frontend tests, e2e and seed

| File | Change |
|---|---|
| `frontend/tests/propertyFormat.test.js` (new) | the display rules |
| `frontend/e2e/masters.spec.js` | the S035 flows of § 8.4 |
| `frontend/e2e/equipment.spec.js` | the card |
| `tooling/e2e/seed_e2e.py` | none: the tests set up by API (S024) |

### 3.5 Docs (at approval, by the planner)

`docs/Plan.MD` § 1 and § 4.1 (§ 9); `docs/Maintenance-Philosophy.md` glossary: *property*;
`docs/steps/README.md` index row; S036 in *Queued*.

## 4. Data model (migration v26)

### 4.1 Tables

```sql
CREATE TABLE IF NOT EXISTS property_definitions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(80) NOT NULL,
    data_type    ENUM('number','choice','text','yes_no') NOT NULL,
    unit         VARCHAR(20) NULL,            -- number only
    description  VARCHAR(300) NULL,
    active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at, created_by, updated_at, updated_by,   -- as every master
    CONSTRAINT uq_property_definitions_name UNIQUE (name),
    CONSTRAINT chk_property_unit CHECK (data_type = 'number' OR unit IS NULL)
);
CREATE TABLE IF NOT EXISTS property_options (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    property_id  INT NOT NULL,
    label        VARCHAR(60) NOT NULL,
    active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at, created_by, updated_at, updated_by,
    CONSTRAINT uq_property_options_label UNIQUE (property_id, label),
    CONSTRAINT uq_property_options_id_property UNIQUE (id, property_id),
    CONSTRAINT fk_property_options_property FOREIGN KEY (property_id) REFERENCES property_definitions (id)
);
CREATE TABLE IF NOT EXISTS class_properties (
    class_id     INT NOT NULL,
    property_id  INT NOT NULL,
    created_at, created_by,
    PRIMARY KEY (class_id, property_id),
    CONSTRAINT fk_class_properties_class FOREIGN KEY (class_id) REFERENCES equipment_classes (id),
    CONSTRAINT fk_class_properties_property FOREIGN KEY (property_id) REFERENCES property_definitions (id)
);
CREATE TABLE IF NOT EXISTS model_property_values (
    model_id      INT NOT NULL,
    property_id   INT NOT NULL,
    value_number  DECIMAL(16,4) NULL,
    value_text    VARCHAR(100) NULL,
    value_bool    TINYINT(1) NULL,
    option_id     INT NULL,
    updated_at, updated_by,
    PRIMARY KEY (model_id, property_id),
    CONSTRAINT fk_model_property_values_model FOREIGN KEY (model_id) REFERENCES equipment_models (id),
    CONSTRAINT fk_model_property_values_property FOREIGN KEY (property_id) REFERENCES property_definitions (id),
    CONSTRAINT fk_model_property_values_option FOREIGN KEY (option_id, property_id)
        REFERENCES property_options (id, property_id),
    CONSTRAINT chk_model_property_one_value CHECK (
        (value_number IS NOT NULL) + (value_text IS NOT NULL) + (value_bool IS NOT NULL)
        + (option_id IS NOT NULL) = 1)
);
```

Column types follow the existing masters (`created_at DATETIME NOT NULL DEFAULT
CURRENT_TIMESTAMP`, `created_by VARCHAR(100) NOT NULL`, `updated_at DATETIME NULL`,
`updated_by VARCHAR(100) NULL`; `local_db.py` line 122 on). Every table is InnoDB, utf8mb4.

### 4.2 Why these columns

- **One typed column per data type**, and exactly one filled (`chk_model_property_one_value`).
  The database refuses a text in a number. A query "pumps above 200 bar" is plain SQL on
  `value_number`. Which column must hold the value follows from the property's
  `data_type`; the backend checks that (§ 5.2), because a CHECK cannot read another table.
- **`DECIMAL(16,4)`**: up to 12 digits before the point and 4 after, enough for a
  displacement of 0.0045 l/rev and a power of 1 200 000 W. Read and written through
  `Decimal(str(...))`, as `tickets_core.part_quantity` (line 885) does, never through a
  float.
- **The option's composite FK** makes "the option belongs to this property" a database rule,
  as S012 does for a model's type (`fk_equipment_models_type`).
- **No row means no value.** Clearing a value deletes its row.
- **`class_properties` has no `active`**: unticking deletes the link. The values stay (§ 5.4).

### 4.3 Data that exists

v26 adds tables and seed rows only. It changes no existing row, so it needs no
`_PRECONDITIONS` entry.

### 4.4 Indexes

The primary keys cover the reads: a class's links by `class_id`, a model's values by
`model_id`. The FK on `property_id` gets its index from InnoDB.

### 4.5 Room for S036 and for model extras

- **S036** adds `equipment_property_values` (the same columns, keyed by `equipment_id`) and
  the `property` event in `equipment_events.event`. S035 changes nothing there.
- **Extra properties on one model** (U1, later) would add `model_properties (model_id,
  property_id)`. A model's property set would then be its class's plus its own. The value
  table needs no change for it.

### 4.6 Seed

`INSERT IGNORE` on the property's name, `created_by = 'migration-v26'`, as the S016 seed
(`local_db.py` line 541). A re-run keeps an engineer's edit of a seed row. The names follow
ISO 14224 Annex A where it has the class (to verify against the text); the rows marked
*local* are common nameplate data. The request's own examples are left to the users (§ 1.5).

- **Options** resolve their property by name at run time, keyed on
  `uq_property_options_label` (BR1-06):
  `INSERT IGNORE INTO property_options (property_id, label, created_by) SELECT id,
  'Horizontal', 'migration-v26' FROM property_definitions WHERE name = 'Shaft orientation'`.
- **Descriptions** (BR1-14, BR2-09): the rating rows (*Power – design*, *Speed*,
  *Voltage*, *Rated current*, *Frequency*, the pressures, *Flow rate – design*, *Free air
  delivery*, *Generator rating*) get "The
  maker's rating, from the nameplate or the data sheet." *Number of stages*, *Nominal size*
  and *Fuel tank capacity* get "From the data sheet." The other rows get none, except *Degree of protection* ("The IP code
  on the nameplate, for example IP55") and *Mounting* ("The IM or B/V code, for example
  B3").
- No *Pump type*, *Motor type*, *Compressor type*, *Valve type* or *Execution*: they are
  equipment types (§ 1, *Type or property*).

| Name | Type | Unit or options | From |
|---|---|---|---|
| Power – design | number | kW | Annex A: pumps, motors, compressors, engines |
| Speed | number | rpm | Annex A: pumps, motors, compressors, engines |
| Voltage | number | V | Annex A: motors, generators |
| Rated current | number | A | local (nameplate) |
| Frequency | number | Hz | Annex A: generators |
| Suction pressure – design | number | bar | Annex A: pumps |
| Discharge pressure – design | number | bar | Annex A: pumps, compressors |
| Flow rate – design | number | L/min | Annex A: pumps (Annex A uses m³/h; L/min is the plant's unit for hydraulics) |
| Free air delivery | number | m³/min | local (compressor nameplate) |
| Number of stages | number | — | Annex A: pumps, compressors |
| Shaft sealing | choice | Mechanical seal, Packed gland, Lip seal, Seal-less | Annex A: pumps |
| Shaft orientation | choice | Horizontal, Vertical | Annex A: pumps |
| Coupling | choice | Rigid, Flexible, Magnetic, Direct | Annex A: pumps |
| Insulation class | choice | A, B, E, F, H | Annex A: motors (IEC 60034-1) |
| Degree of protection | text | — ("IP55") | Annex A: motors (IEC 60529) |
| Frame size | text | — ("132M") | local (nameplate) |
| Mounting | text | — ("B3", "B35") | local (IEC 60034-7) |
| Variable speed drive | yes/no | — | Annex A: motors |
| Actuation | choice | Manual, Solenoid, Pneumatic, Hydraulic, Electric motor | Annex A: valves |
| Nominal size | number | mm | Annex A: valves |
| Generator rating | number | kVA | Annex A: generators |
| Fuel tank capacity | number | L | local (diesel generators) |

## 5. Rules (pure core: `properties_core.py`)

### 5.1 A property

| Field | Rule | Message (scope B) |
|---|---|---|
| name | required; trimmed, inner spaces collapsed; 1–80 characters; unique, case-insensitive (the column's collation), inactive rows count | "Enter a name" · "Use 80 characters or fewer" · "A property with this name exists" (409) |
| data_type | required on create; one of the four; **fixed** once the property has **any option or any value** (BR1-03) | "Choose a data type" · "The data type cannot be changed: the property has options or models hold values of it. Make a new property instead." (409) |
| unit | number: optional, trimmed, 1–20 characters, empty → NULL; another type: must be empty; **fixed** once a value exists. A change of `data_type` away from *number* sets `unit` to NULL in the same UPDATE | "Use 20 characters or fewer" · "Only a number has a unit" · "The unit cannot be changed: models hold values of this property. Make a new property instead." (409) |
| description | optional, trimmed, up to 300 characters; empty → NULL | "Use 300 characters or fewer" |
| active | yes / no | — |

**The combined record** (BR1-03). `validate_property` sees only the fields sent, so the
route checks the stored row plus the changed fields: a `PUT {"unit": "kW"}` on a text
property is a 400 on `unit` "Only a number has a unit", and a `PUT {"data_type": "text"}` on
a number with a unit clears the unit. No request reaches `chk_property_unit` and a 500.

**Duplicates** are caught by the UNIQUE indexes, not by a query first (BR1-05):
`properties.py` registers in `api_common.UNIQUE_KEY_ERRORS`, as `masters.py` does (lines
48–69), `uq_property_definitions_name` → `("name", "A property with this name exists")` and
`uq_property_options_label` → `("label", "An option with this label exists")`, both 409.

**An option's label** (`validate_option`, BR1-08): required; trimmed, inner spaces
collapsed; 1–60 characters; unique within its property, case-insensitive. Messages "Enter a
label", "Use 60 characters or fewer".

A choice property needs at least one active option to be **linked or given a value**; it
may exist with none while being set up.

A `PUT` without a field leaves it unchanged. A wrong type (a number for `name`, a string for
`active`) is a 400 with the field's message.

### 5.2 A value

`parse_value(data_type, raw)` → `(value, None)` or `(None, message)`:

| Data type | Accepts | Stored in | Message |
|---|---|---|---|
| number | a number or a numeric string; up to 4 decimals; more than −10¹² and less than 10¹²; not a bool, NaN or infinity | `value_number` | "Enter a number" · "Use up to 4 decimals" · "Enter a smaller number" |
| text | a string, trimmed, 1–100 characters | `value_text` | "Use 100 characters or fewer" |
| yes_no | `true` or `false` (JSON) | `value_bool` | "Choose Yes or No" |
| choice | an option id of **this** property, active (an inactive one only if it is the stored value, unchanged) | `option_id` | "Choose an option from the list" |

`null`, or an empty or blank string, means **clear**. A number keeps its sign; a negative
value is allowed (a temperature rating).

**The number form** (BR1-08): a JSON number (not a bool), or a string that is, after
trimming, an optional `-`, one or more digits, and optionally `.` with one to four digits.
No `+`, no inner spaces, no exponent, no thousands separator. Anything else is "Enter a
number". The value is read with `Decimal(str(...))`, as `tickets_core.part_quantity` does.
In answers, a number's `value` is the normalised string ("62.5", never "62.5000", BR1-10).

### 5.3 The model's values

`PUT /equipment-models/<id>/properties` with `{"values": {"<property_id>": value, …}}`:

- `values` missing or not an object → 400 on `values` "Send the values as an object"; `{}` →
  200, nothing changes (BR1-08);
- a key that is not a positive whole number in a string (`"abc"`, `"12.0"`, `"-1"`) → 400
  on `values.<key>` "This property is not on the class";
- only the properties in the body change; the others stay;
- a property must be **active** and linked to the **model's class** → else 400 on
  `values.<id>` "This property is not on the class";
- an unknown property id → 400, the same message;
- the model may be inactive: its data stays correct for the equipment that uses it;
- the values are checked in the order of the property names; the **first** refused one
  answers 400 with `field: "values.<property_id>"`, and nothing is saved. This keeps the
  one-field error shape of `api_common.ApiError` (line 32); a user with two wrong values
  sees the second after fixing the first.

### 5.4 Links and values that stay

- **Unticking** a property of a class deletes the link only. The models' values of it stay
  in the table and are shown nowhere. Ticking it again shows them again. So an unticked
  box by mistake loses no data.
- **Deactivating** a property hides it from the tick boxes, the dialogs and the card; its
  links and values stay.
- **Deactivating** an option: it cannot be newly picked; a stored value still shows its
  label. Deactivating the **last** active option of a linked choice is allowed: the link and
  the values stay, and nothing new can be picked until an option is active again (BR1-08).
- **Renaming** a property or an option changes the label everywhere, values unchanged.
- A model's class never changes (S012), so a model's values never end up on another class.

### 5.5 The card's view

`property_view(properties, model_values, options)` → the rows of § 7.4, by name: each
active property linked to the item's class, with the model's value formatted by
`format_value` ("62.5 kVA", "Yes", "Internal"), or `None` for "—". A number shows without
trailing zeros ("62.5", not "62.5000"), with a space before the unit. The zeros are cut with
`format(value.normalize(), "f")`: a plain `normalize()` gives "1E+2" for 100 (checked:
`Decimal("100.0000")` → `format(..., "f")` → "100").

### 5.6 Transactions and locks (`properties.py` LOCK ORDER)

One order for every write in the module, each step taken only when the write needs it:

1. the `equipment_classes` row, or the `equipment_models` row
2. the `property_definitions` row(s), by id, ascending
3. the `property_options` row

- **Edit a property** (`PUT /properties/<id>`): lock (2). The "values exist" check for a
  data-type or unit change is a locking read (`SELECT 1 FROM model_property_values WHERE
  property_id = %s LIMIT 1 LOCK IN SHARE MODE`), so a value saved at the same moment is
  seen, or waits: a value insert takes a shared lock on the property row through the FK,
  which the edit holds exclusively.
- **Add or edit an option**: lock (2), then (3) for an edit.
- **Add properties to a class** (`POST /equipment-classes/<id>/properties`): lock (1) the
  class, then (2) each property in the body, ascending, `FOR UPDATE`, to check it is active
  (and, for a choice, has an active option, read with `LOCK IN SHARE MODE` on its options),
  then `INSERT IGNORE` the links.
- **Remove a property from a class** (`DELETE /equipment-classes/<id>/properties/<pid>`):
  lock (1) the class, then delete the link.
- **Set a model's values**: lock (1) the model, read its class (fixed), then lock (2) the
  properties named in the body, ascending, `FOR UPDATE`, and check them active and linked
  (a locking read of `class_properties`), then (3) a choice's option with `LOCK IN SHARE
  MODE`. Upsert with `INSERT … ON DUPLICATE KEY UPDATE`; clear with `DELETE`.
- These rows are new tables, so no existing route takes them; the masters' own order
  (manufacturer → model → class, `masters.py` `update_equipment_model`) is not mixed with
  this one: no route here locks a manufacturer, and the model is locked before the class
  is read (plainly, as it never changes).
- **The database down**: every route goes through `get_db()` and answers 503
  (`DBUnavailable`), as the other masters.

## 6. API

### 6.1 Properties

| Route | Key | Body / answer |
|---|---|---|
| `GET /api/masters/properties` | `masters:read` | `{"items": [...]}`: every field, plus `options` (id, label, active), `class_count` and `value_count` (the models holding a value of it, BR2-01); `?include_inactive=1` as the other masters (`_include_inactive`) |
| `POST /api/masters/properties` | `equipment:edit` | name, data_type, unit, description; for a choice, optional `options: ["Internal", …]` created in the same transaction → 201 |
| `PUT /api/masters/properties/<id>` | `equipment:edit` | any of name, data_type, unit, description, active |
| `POST /api/masters/properties/<id>/options` | `equipment:edit` | `{"label"}` → 201; only on a choice property ("Only a choice has options", 400 on `label`); a duplicate → 409 (§ 5.1) |
| `PUT /api/masters/property-options/<id>` | `equipment:edit` | `{"label"}` and/or `{"active"}` |

`equipment:edit` is the key that already keeps classes, types and models
(`masters.py` lines 317, 498): the same people (U3). It is in `SITE_SCOPED`, but
`require_perm` checks it as the union over the user's sites, as for the other masters,
because a property is the same at every site.

### 6.2 Class links and model values

| Route | Key | Body / answer |
|---|---|---|
| `GET /api/masters/equipment-classes/<id>/properties` | `masters:read` | `{"items": [{property_id, name, data_type, unit, active}]}`, by name; inactive linked ones included (the table marks them) |
| `POST /api/masters/equipment-classes/<id>/properties` | `equipment:edit` | `{"property_ids": [...]}`: the properties to **add** (U6), read as a set; an id already on the class is skipped, no error; each new one must be active, and a choice must have an active option → else 400 on `property_ids` "Choose active properties"; an unknown id → the same 400; an empty list or not a list of integers → 400 on `property_ids` "Choose at least one property"; an inactive class → allowed, as an inactive model (BR1-08) → 200 with the GET's answer |
| `DELETE /api/masters/equipment-classes/<id>/properties/<property_id>` | `equipment:edit` | removes one link; the models' values stay (§ 5.4); not on the class → 404 → 200 with the GET's answer |

Two routes instead of one `PUT` of the full set (U6): each request says what it changes, so
two engineers editing one class at the same time do not undo each other's work.
| `GET /api/masters/equipment-models/<id>/properties` | `masters:read` | `{"items": [{property_id, name, data_type, unit, options, value, display}]}`, the class's active properties by name |
| `PUT /api/masters/equipment-models/<id>/properties` | `equipment:edit` | `{"values": {...}}` (§ 5.3) → the same answer as the GET; a refusal as `{"error": "Enter a number", "field": "values.12"}` with 400 |

An unknown class or model → 404. A body that is not an object, or `property_ids` that is
not a list of integers, → 400.

The frontend shows the message under the input named by `field` (S026: the dialog scrolls
to it and puts the cursor there). The `values.<id>` field name is new; `ModelPropertiesModal`
maps it to its input.

### 6.3 Equipment detail

`GET /api/equipment/<id>` (unchanged key, `equipment:read` at the item's site) adds:

```json
"properties": [
  {"property_id": 3, "name": "Generator rating", "value": "62.5", "unit": "kVA",
   "display": "62.5 kVA", "source": "model"}
]
```

`source` is `"model"` or `null` (no value); S036 adds `"item"`. An empty list when the class
has no active property.

## 7. Screens

### 7.1 Masters › Properties

- A table: **Name**, **Type** ("Number · kW", "Choice · 2 options" — the active options,
  BR1-13 — "Text", "Yes / No"),
  **Classes** (the count), and the active toggle, as the other panels (`ActiveToggle`,
  *Show inactive*).
- **Add property** opens the `FormModal` dialog (`useMasterForm`): name, data type (a
  select), unit (shown only for a number), description, and for a choice an **Options**
  list: one input per option with **Add option**. A help line under the data type: "How the
  equipment is built (centrifugal, open execution) is its type: use Equip Type for that."
  The dialog fits a phone (`expectDialogFits`).
- **Edit**: the same dialog, with the two rules of § 5.1 (BR2-01):
  - **Data type** is disabled when the property has an option (any, active or not) or
    `value_count > 0`, with the line "This property has options or values, so its data type
    is fixed.";
  - **Unit** is disabled when `value_count > 0`, with the line "Models hold values of this
    property, so its unit is fixed.".

  An option
  is renamed in place or deactivated with its toggle; there is no delete.

### 7.2 Class properties: table and picker (U6)

**The table** (`ClassPropertiesView`, in the panel). A row's **Properties** button on *Equip
Class* replaces the class table with this view, as *Documents* does on *Models*; **Back**
brings the class table back.

- Heading "Properties of <class code> — <class name>". A help line: "The data this kind of
  equipment has. A part's own data, such as its motor's power, goes on the part's class."
- A table by name: **Name**, **Type** ("Number", "Choice", "Text", "Yes / No"), **Unit**,
  and a **Remove** button per row. An inactive property shows "(inactive)" after its name.
- Under the table, in grey: "Removing a property keeps the models' values. Add it again to
  show them." **Remove** needs no confirmation, because no value is lost (§ 5.4); the row
  goes at once.
- No properties yet: "No properties on this class yet." with **Add property…**.
- Users without `equipment:edit` see the table without *Add property…* and *Remove*.

**The picker** (`AddPropertiesModal`, a dialog). **Add property…** opens it.

- Title "Add properties to <class code>". A search box filters the list by name.
- One tick box per active property **not yet on the class**, by name, with its type and
  unit in grey. A choice with no active option shows disabled, with "(no options yet)".
- **Add properties** (disabled until one box is ticked) sends one `POST` with the ticked
  ids; the dialog closes and the table shows the new rows. **Cancel** closes it.
- Every property already on the class: "Every property is on this class. Make a new one in
  Properties." and only **Close**.
- **Wiring** (BR1-07): `useFormModal` for the modal and `send(request)` with its own
  request, as the Team dialog does (`useMasterForm.js` line 47). Its form has one key,
  `property_ids`, so a refusal shows under the list.

### 7.3 Model properties dialog

- Title "Properties of <model label>". One `PropertyInput` per property:
  - number: a text input with `inputmode="decimal"` and the unit after it;
  - choice: a select with "—" and the active options (plus the stored one if inactive);
  - text: a text input;
  - yes/no: three buttons **Yes**, **No**, **Not set**.
- **Save values**. A refused value shows its message under its input (§ 5.3: one at a time).
- **Opening** (BR2-03): the dialog fetches `GET /equipment-models/<id>/properties` first,
  then opens with the answer as its seed (`openEdit`), so `useFormModal`'s snapshot, taken
  in `nextTick` after `open()`, holds the stored values and an untouched **Cancel** closes
  without the leave-guard. A failed fetch shows its message and does not open the dialog.
  The picker opens empty (nothing ticked), so it needs no fetch beyond the properties list
  the panel already holds.
- **Wiring** (BR1-07): `useFormModal` with `send(request)`, as § 7.2. The form is keyed by
  the literal strings `"values.<property_id>"`, and the request builds `{"values": {...}}`
  from them. So a refusal's `field` (`"values.12"`) is a key of the form, `fieldError` shows
  it under the input and `modalError` stays empty (`useFormModal.js` lines 51–53).
  `PropertyInput` takes the message as a prop.
- Opened from *Masters › Models* and from the equipment page's card (§ 7.4).
- No properties on the class: the dialog says "The class <code> has no properties yet. Add
  them in Equip Class." and shows only **Close**.

### 7.4 Properties card (equipment page)

- Beside *Details*, as *Parts* is (`EquipmentDetailView.vue` lines 220–245). On a phone the
  cards stack.
- A two-column list: name, value ("62.5 kVA" or "—"). Under it, in grey: "Values from model
  <model label>."
- Users with `equipment:edit` at any site see a button **Edit model values** in the card's
  header: the page's existing `canEditModels` (`EquipmentDetailView.vue` line 55), not
  `canEdit` (the item's site, not scrapped). It matches the API's union check for model
  values, and shows on every lifecycle, as model data stays right for a scrapped item
  (BR2-02). It opens `ModelPropertiesModal` for `node.model_id`, titled with
  `node.model_label`; the dialog's `saved` event calls the page's `load()`, so the card shows
  the new values (BR1-04, BR2-07). The dialog's title names the model, so the user
  sees that every item of the model changes.
- Hidden when the class has no active property.

## 8. Tests and acceptance

### 8.1 Pure (`test_properties_core.py`)

- name: trimmed and collapsed; empty; 81 characters; a number → each message;
- unit on a non-number → refused; 21 characters → refused;
- `parse_value`: number `"62.5"`, `62.5`, `"-40"` → accepted; `"1e3"` → "Enter a number"
  (plain digits only, § 9.8); `"0.00001"` → "Use up to 4 decimals"; `10**12` → "Enter a
  smaller number"; `True`, `"NaN"` → "Enter a number"; text 100 and 101 characters;
  yes_no `true` and `"yes"`; blank → clear;
- `format_value`: `Decimal("62.5000")` → "62.5 kVA"; `Decimal("3")` → "3"; no unit →
  no trailing space; yes/no → "Yes" / "No".

### 8.2 API (`test_properties_api.py`, `test_equipment_api.py`)

- create each type; a choice with options; a duplicate name (case) → 409; a unit on a
  choice → 400;
- change the data type and the unit with no options and no values → allowed; a choice with
  an option → 409 on `data_type`; a number with one model value → 409 on both; number with
  unit → text clears the unit; `{"unit": "kW"}` on a text property → 400 (BR1-03);
- `values` not an object → 400; `{}` → 200; a key `"abc"` → 400 (BR1-08);
- options: add to a number property → 400; duplicate label → 409; deactivate; an inactive
  option is refused as a new value but kept when unchanged;
- class links (U6): add two at once; add one already linked → skipped, 200; a repeated id
  → one link; an inactive property → 400; a choice with no active option → 400; `[]` →
  400; an inactive class → added; remove one → the models' values stay, and adding it
  again shows them; remove one not on the class → 404; an inactive property already linked
  stays in the GET and can be removed;
- model values: set each type; clear by `null` and by `""`; a property not on the class →
  400; two wrong values → the first by name answers, nothing saved; an inactive model →
  allowed;
- permissions: an operator → 403 on every write, 200 on the reads; an engineer at one site
  → 200 on the writes (the union);
- the detail's `properties`: a model value shows with `source: "model"`; a property without
  a value → `display: null`; an unlinked or inactive property → absent;
- the database down: one write and one read → 503, with the `db_down` fixture moved to
  `conftest.py` (§ 3.2; the bodies in `test_access_control_api.py` lines 42–47 and
  `test_auth.py` lines 63–68 are identical; `conftest.py` imports `db_helpers`; the comment in
  `test_health.py` line 14 is updated) (BR2-04);
- `conftest.py`: the five-table clean-up keeps the seeded properties and options
  (`created_by = 'migration-v26'`). `_SEEDED_TABLES` today takes one creator
  (`SEED_CREATOR = "migration-v11"`, line 146): it becomes a creator per table;
- `test_role_matrix` (`test_rbac.py` line 198): unchanged, no new key.

### 8.3 Migration (`test_migration_v26.py`)

- a fresh database reaches v26 with the tables, the CHECKs and the seed (22 properties,
  their options);
- an upgrade from v25 with a class, a model and equipment keeps every row;
- a re-run changes nothing and keeps an edited seed row (renamed "Power – design" stays
  renamed: `INSERT IGNORE` keys on the name, so the old name comes back as a **new** row —
  the test states which; see § 9.4).

### 8.4 Automated (e2e)

`masters.spec.js` and `equipment.spec.js`, names `S035: …`; targeted, plus
`screens.spec.js`. Set up by API (S024).

- **important**: an engineer adds a choice property with two options, adds it to a class
  through *Add property…* (two properties ticked at once, both rows appear), sets it on a
  model, and the equipment page of an item of that model shows the value;
- **Remove** on the class table takes the row away, and the picker lists the property again;
- **important**: a number value with its unit shows as "62.5 kVA" on the card;
- a refused number ("abc") shows "Enter a number" under its input;
- an operator sees the *Properties* section read-only (no *Add property*, no *Properties*
  buttons on classes and models);
- **Edit model values** on the card opens the model dialog; after a save the card shows the
  new value;
- the property dialog, the picker and the model dialog fit a phone; the model dialog
  is checked on a model whose class has properties, because `expectDialogFits` needs a Save
  and a Cancel button (`dialogs.js` lines 33–35; BR1-11).

### 8.5 On a real device

None: a browser judges every screen here.

### 8.6 Acceptance

All suites green; the e2e targeted run green on the three projects; the seed present in a
fresh database; no change to an existing table.

## 9. Open questions and assumptions

1. **Question: the split.** S035 as above (master, classes, model values, the card),
   S036 for overrides. **Recommended:** split. Option: one step, about 30 files and one
   more table, past the size rule.
2. **Closed (BR1-01): "Execution — open / closed" on pumps** is an equipment type, as
   S004 already decided for `RPP` (*Closed execution*, *Open execution*). It is not in the
   seed.
3. **Closed (KLA, 24-10-2026): the request's examples** (poppet type, drain, displacement,
   maximum operating pressure) were examples of what users will define, not seed rows. They
   are not in the seed.
4. **Assumption: the seed key.** `INSERT IGNORE` keys on the name, so a renamed seed row
   comes back under its old name on a re-run. A migration runs once, so this happens only
   on a hand re-run. Accepted as S016 does; stated in the test (§ 8.3).
5. **Assumption: no link in the seed.** The plant's class codes are not known to the code,
   so the engineer ticks the properties on each class (about five minutes per class).
   Option: link by class name at migration time — rejected, the names are free text.
6. **Assumption: properties show by name.** A hand order (pressure next to flow) needs an
   order column and up / down buttons. Option for a later step.
7. **Assumption: one unit per property.** A pump in m³/h and another in L/min share one unit;
   the user converts once. Option: units with conversion — rejected, too much for the gain.
8. **Assumption: numbers in plain digits** ("1000", not "1e3"), with up to 4 decimals.

## 10. Design decisions

1. **Properties on the class** (U1). A property is defined once and linked to many classes.
   Rejected: per model (each new model is linked again; models become hard to compare).
2. **Typed value columns** (EAV with one column per type). Rejected: a JSON column on the
   model (MariaDB's JSON is text; no type check by the database; harder queries); one text
   column (no number comparisons).
3. **A choice is a list of option rows**, stored by id. Renaming an option renames it
   everywhere. Rejected: the label stored on the value (a rename leaves old spellings).
4. **The unit belongs to the property and is fixed once a value exists.** Rejected: a unit
   per value (250 bar and 250 psi in one column).
5. **Unticking keeps the values** (§ 5.4). Rejected: refusing to untick while values exist
   (the engineer clears each model first); deleting the values (a slip loses data).
6. **A new module `properties.py`**, with its own LOCK ORDER. `masters.py` is over 1 100
   lines. Rejected: more routes in `masters.py`.
7. **The keepers are `equipment:edit`** (U3), as for classes and models. Rejected: a new key
   (no one needs to hold one without the other today).
8. **One model dialog**, `ModelPropertiesModal`, opened from Masters and from the card
   (BR1-04). The item's own values and their dialog come with overrides in S036, where they
   also write history. Rejected: a link to Masters (no route for it today, and a long way
   round on the floor).
9. **A type is not a property** (BR1-01). How equipment is built stays the S004 type, so a
   pump's kind lives in one place. Rejected: properties for the kind as well (one fact in two
   places), or properties replacing types (undoes S004 and S012).

## 11. Docs (at approval)

- `docs/Plan.MD` § 1: remove "Per-class custom fields (e.g. press tonnage)" from *Not in
  v1*; § 4.1 *Equipment class*: "No class-specific custom fields in v1" → "A class carries
  properties (S035): technical data defined once in Masters, valued on its models (S035)
  and on its items (S036)."
- `docs/Maintenance-Philosophy.md` glossary: **Property** — a technical datum of a class of
  equipment (ISO 14224 Annex A *equipment-specific data*), with a data type and a unit. The
  model holds the maker's rating; an item holds its own only where its nameplate differs
  (S036). How the equipment is built is its *type*, not a property; values that change in
  service are readings.
- `docs/steps/README.md`: S036 in *Queued* — "Property overrides on equipment items, logged
  in the history (S035 § 4.5)".

## 12. Amendments

None.

## Review log

| ID | Severity | Answer |
|---|---|---|
| BR1-01 | major | Accepted, option (a): *Pump type*, *Compressor type*, *Motor type*, *Valve type* and *Execution* dropped from the seed (26 rows; 22 after the user's change); the type-or-property rule in § 1 and decision 9; § 9.2 closed; a help line in the property dialog (§ 7.1). |
| BR1-02 | minor | Accepted: § 2 says design = the maker's rating, the S036 override = the item's own nameplate value, operating values = readings; the option lists marked to verify; the glossary text follows (§ 11). |
| BR1-03 | minor | Accepted, option (a): `data_type` fixed once any option or value exists; the unit cleared when the type leaves *number*; the route checks the combined record (§ 5.1); tests in § 8.2. |
| BR1-04 | minor | Accepted, option (a): **Edit model values** on the card opens `ModelPropertiesModal` (§ 1.4, § 7.3, § 7.4, decision 8); e2e in § 8.4. |
| BR1-05 | minor | Accepted: the two `UNIQUE_KEY_ERRORS` entries and the option message (§ 5.1, § 6.1). |
| BR1-06 | minor | Accepted, option (a): the option seed statement (§ 4.6); `SEED_CREATOR` kept, `_SEED_CREATORS` added (§ 3.2). |
| BR1-07 | minor | Accepted, option (a): both dialogs on `useFormModal` with `send(request)`; the model form keyed by `"values.<id>"` (§ 7.2, § 7.3). |
| BR1-08 | minor | Accepted: the option label rule (§ 5.1), the number form (§ 5.2), `values` shape and keys (§ 5.3), the set and the inactive class (§ 6.2), the last active option (§ 5.4); tests in § 8.2. |
| BR1-09…BR1-18 | nit | Accepted: Baseline set at approval; numbers sent normalised (§ 5.2); the fit check on a model with properties (§ 8.4); § 1.2 aligned; option count = active; seed descriptions (§ 4.6); ISO 55001 § 7.5 line (§ 2); `db_down` moved to `conftest.py` (§ 3.2); `_TABLES` order named; BR1-18 needs no change. |
| BR2-01 | minor | Accepted: `value_count` on the GET items (§ 6.1); the two disable rules and help lines in § 7.1. |
| BR2-02 | minor | Accepted: the card button follows `canEditModels`, on every lifecycle (§ 7.4). |
| BR2-03 | minor | Accepted: both set dialogs fetch first, then open with the answer as seed (§ 7.3). |
| BR2-04 | minor | Accepted: § 8.2 now uses the moved `db_down`, with the identical bodies, the import and the `test_health.py` comment. |
| BR2-05…BR2-09 | nit | Accepted: the item-5 sentence put back; "26 seed properties"; `node.model_id`, `node.model_label` and `saved` → `load()` named; "Send the values as an object"; descriptions split by kind; the ISO 55001 tag dropped. |
| U6 (gate A) | user | Accepted: the class's properties are a table in the panel with **Add property…**, a picker of the properties not yet on the class with several ticked at once, and **Remove** per row (§ 1.2, § 3.3, § 5.6, § 6.2, § 7.2, § 8.2, § 8.4). The full-set `PUT` became `POST` (add) and `DELETE` (remove one). |
| U7 (gate A) | user | Accepted: the request's examples are not seeded (*Displacement*, *Maximum operating pressure*, *Drain*, *Poppet type*); the seed has 22 rows (§ 1.5, § 4.6); § 9.3 closed. |
