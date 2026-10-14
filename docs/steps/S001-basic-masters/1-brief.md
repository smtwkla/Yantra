```
Step: S001 — Basic masters
Doc: brief
Author: Planner (Opus)
Date: 13-10-2026 (revised 13-10-2026 after brief-reviews r1 and r2)
Status: Done (committed 817844c, 14-10-2026)
```

# S001 — Basic masters: sites, units, equipment classes, unit access

This is the first slice of Plan.MD phase 2 (equipment register). Background reading:

- `docs/Plan.MD` § 3, § 4.1, § 5
- `docs/Maintenance-Philosophy.md`
- `docs/Plant-Facts.md` § 2
- `.claude/SMTW-WebApp-Base.md` (DB access, migrations, RBAC, API responses,
  frontend page patterns)

## 1. What will be built

This step builds the four masters every later module points at:

- **Sites**: the facilities.
- **Units**: the areas within a site.
- **Equipment classes**: what a piece of equipment is. The class code is also the
  equipment-code prefix.
- **Users' unit access**: which units each user may work at.

Each master gets create, list and edit, plus deactivate and reactivate. No master
record is ever hard-deleted. Unit-access rows are current state: they are replaced
on save, and each change is logged (§ 5). The masters are managed from the existing **Masters** page.

**Out of scope:**
- the equipment register (S002);
- documents and QR labels;
- failure codes;
- the OneERP warehouse sync;
- *enforcing* unit access on queries. That starts with S002, which brings the
  first unit-scoped data.

## 2. Standards and practice

**Functional locations.** Sites and units are what CMMS practice calls
**functional locations**: fixed places where equipment is installed, as opposed
to the equipment itself, which moves. ISO 14224 uses the same split (its
installation and plant/unit levels), and so do SAP PM and most CMMS products.
The screens keep the plant's words, "site" and "unit".

**ISO 14224 taxonomy.**
- A site is level 3 ("installation"). A unit is levels 4–5 ("plant/unit,
  section/system").
- Equipment class is ISO 14224's own concept. Annex A gives 2-letter class codes
  such as `PU` (pump), `EM` (electric motor) and `CO` (compressor).
- We **deliberately depart** from those codes and use our own 2–4-letter
  prefixes (`VBM`, `HP`, `MOT`), because plant people must recognise them on QR
  labels.

**ISO 55001 § 7.5–7.6** (information requirements; documented information;
clause numbers as in the 2014 edition). The asset register must be *controlled*:
changes are traceable, and records are deactivated, not deleted, so history
never points at a missing record. In S001 this means:
- a code may be corrected only until something uses it (§ 5);
- the audit columns on each master record the **last** change (who and when).
  They are not a full history; a renamed site keeps no trace of its old name.
  That is enough for v1 masters.

**ISO 27001:2022 access control.**
- **A.5.15 (access control):** unit access is the "where" of access control,
  kept apart from roles, which are the "what".
- **A.5.18 (access rights):** access must be granted, reviewed and revoked
  traceably. Every unit-access change writes one structured line to the
  application log (actor, user, units before, units after). Logs are shipped
  centrally, so the trail exists without a history table.
- **A.5.3 (segregation of duties):** only IT admin grants access, which keeps
  granting access apart from doing the work.

## 3. Where

### Backend

- **Migration v2**, appended to `_MIGRATIONS` in `backend/local_db.py`. It creates
  `sites`, `units`, `equipment_classes` and `user_units`. Each
  `CREATE TABLE IF NOT EXISTS` is a separate statement, per the base pattern.
- **`backend/masters_core.py`** (new, pure): validates and normalises each
  master's input.
  - Each validator returns `(clean_data, errors)`, where `errors` is a list of
    `{field, message}`.
  - No DB access and no Flask.
- **`backend/masters.py`**: the routes, as a thin shell. They replace the
  placeholder `GET /`.
- **`get_db()` and its teardown move from `app.py` to `backend/db_helpers.py`.**
  - `db_helpers.py` imports `get_pooled_db` and `ensure_schema` from `local_db`,
    and `DB_CONFIG` from `config`.
  - `app.py` registers the teardown.
  - `local_db.py` stays free of Flask.
  - Why: blueprints can't use `from app import get_db` without a circular import.
- **New helper `transaction(conn)` in `db_helpers.py`**: a context manager that
  does begin, then commit, or rollback on an exception.
  - Connections are autocommit. Replacing a user's unit access, and a code
    change with its in-use check, must each be atomic.
  - Later modules will reuse it.
- **`backend/config_rbac.py`**:
  - `masters:edit` becomes `("it_admin",)`.
  - New key `masters:read_senior` = `("it_admin",)`, for reading unit access.
    It is the read hierarchy's "sensitive" level. Engineers can be added in
    phase 3, when they assign work.
  - New key `equipment:edit` = `("maint_engineer", "it_admin")`. The manager
    inherits it through the role ladder.
  - `masters:read` stays `("*",)`.

### Frontend

- **`frontend/src/api.js`**: copy `field` from the error body onto the thrown
  error, next to `code`, so panels can show the message beside the field.
- **New `frontend/src/components/layout/ModuleToolbar.vue`**: the level-2 icon
  toolbar of the base pattern, reusable by later modules.
  - It is data-driven: an array of `{key, icon, label, perm}`, filtered by
    permission like `navItems`.
  - It is hidden when only one section remains.
  - It emits the chosen key.
- **`frontend/src/views/MastersView.vue`**: the toolbar with Sites | Units |
  Equipment classes | Unit access. The section is local state, not a route.
  Unit access needs `masters:read_senior`.
- **New panels** `frontend/src/views/masters/{SitesPanel,UnitsPanel,EquipmentClassesPanel,UserUnitsPanel}.vue`:
  - Each is a table plus a Bootstrap modal for create and edit.
  - Edit buttons are hidden without the matching edit permission.
  - The code field carries a hint: "cannot be changed once in use".
- **New store `frontend/src/stores/masters.js`**: cached `ensureSites()`,
  `ensureUnits()` and `ensureEquipmentClasses()`, invalidated after a save. The
  Units and Unit access panels use them now; S002 will too.

### Tests

- `backend/tests/test_masters_core.py` (new, pure).
- `backend/tests/test_masters_api.py` (new, against the test DB). It takes over
  the two `TestMasters` tests from `test_modules.py` (every role can read; an
  unknown role gets 403), now against `GET /api/masters/sites`.
- `backend/tests/test_modules.py`: remove `TestMasters`, since the placeholder
  route goes.
- `backend/tests/test_auth.py`: `test_valid_bearer_token_reaches_route` asserts
  that an engineer holds `masters:edit`. Change it to `equipment:edit`.
- `backend/tests/test_rbac.py`: role-matrix update.
- `backend/tests/conftest.py`: a session-scoped truncate of the master tables
  (§ 8).
- `frontend/tests/navigation.test.js`: per-role permission lists.

### Docs

- None for the coder. The planner recorded the approved decisions in
  `docs/Plan.MD` at approval: the `masters:read_senior` row in § 3, and the
  frozen-once-in-use rule in § 4.1.

## 4. Data model (migration v2)

**Common columns:**
- All tables are InnoDB and utf8mb4.
- `id` is `INT AUTO_INCREMENT PRIMARY KEY`.

**Audit convention** (for all Yantra tables from now on):
- `created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`.
- `created_by VARCHAR(100) NOT NULL`.
- `updated_at DATETIME NULL` and `updated_by VARCHAR(100) NULL`. These stay NULL
  until the first edit; the shell then sets both in the same `UPDATE`, with
  `NOW()`.
- No `ON UPDATE CURRENT_TIMESTAMP`, so a time is never recorded without an actor.
- The actor is always `g.user["username"]`, never a value from the client.
- The connection's time zone is IST, so `NOW()` and `CURRENT_TIMESTAMP` are IST.

| Table | Columns | Keys |
|---|---|---|
| `sites` | `id`, `code VARCHAR(20)`, `name VARCHAR(100)`, `address VARCHAR(255) NULL`, `active TINYINT(1) NOT NULL DEFAULT 1`, audit | `uq_sites_code (code)` |
| `units` | `id`, `site_id`, `code VARCHAR(20)` (the part after the dot, e.g. `FWMILL`), `name VARCHAR(100)`, `oneerp_warehouse VARCHAR(140) NULL`, `active`, audit | `uq_units_site_code (site_id, code)`, `uq_units_warehouse (oneerp_warehouse)` (many NULLs allowed), FK `site_id` → `sites` |
| `equipment_classes` | `id`, `code VARCHAR(4)` (the equipment-code prefix), `name VARCHAR(100)`, `active`, audit | `uq_equipment_classes_code (code)` |
| `user_units` | `username VARCHAR(100)`, `unit_id`, `granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`, `granted_by VARCHAR(100) NOT NULL` | `PK(username, unit_id)`, FK `unit_id` → `units` |

Unique indexes are **named** as above, so the shell can tell from MariaDB's
1062 message (`... for key 'uq_units_site_code'`) which rule was broken (§ 5).

## 5. Rules

### Code formats

Codes are stripped and upper-cased before they are checked.

| Master | Pattern | Notes |
|---|---|---|
| Site | `^[A-Z][A-Z0-9-]{1,19}$` | Allows `SMTW-KP` and `AGRI-VKM`. The dot is reserved as the separator. |
| Unit | `^[A-Z0-9][A-Z0-9-]{1,19}$` | At least 2 characters, like site codes |
| Equipment class | `^[A-Z]{2,4}$` | |

### Codes are frozen once in use

- A code may be changed by the holder of the edit permission **while nothing
  references the record**. This covers typos during the first data load.
- Once the record is referenced, a PUT that changes the code → **409 "code is in
  use"**. A `code` equal to the stored one, or no `code` in the body, means
  "unchanged" and is accepted.
- **A unit's `site_id` follows the same rule**, because it is half of the full
  code `SITE.UNIT` (BR2-01). It can change while the unit is unreferenced;
  otherwise → 409 "unit is in use". The new site must be active (§ Activation),
  and the new `(site_id, code)` must still be unique.
- **Why freeze, when nothing in the DB would break?** For a class it is integrity:
  the prefix sits inside every equipment code. For sites and units it is
  **change control** (ISO 55001), not a database constraint. Children reference
  by `id` and the path is derived, so the DB would cope. What a rename disturbs is
  outside the DB: OneERP warehouse names that mirror `SITE.UNIT`, printed lists,
  people's habits, and S003's path snapshots.
- What "referenced" means in S001:

  | Record | Referenced when it has … |
  |---|---|
  | Site | any unit, active or inactive |
  | Unit | any `user_units` row |
  | Class | nothing yet |

  S002 adds "has equipment" to units and classes. From then on the class prefix
  is baked into equipment codes, so a class code that is in use can never change.
- The check and the update run in one `transaction()`. The record's row is locked
  with `SELECT … FOR UPDATE` before references are counted. A concurrent insert of
  a child row needs a lock on the parent row through the foreign key, so it waits
  and can't slip in between.
- Every other field can always be edited: `name`, `address` (sites),
  `oneerp_warehouse` (units) and `active`. The check covers `code` and, for
  units, `site_id`.
- **Pointer for S003 and later:** tickets and jobs should save a snapshot of the
  full path as it was at event time, so a later rename or move doesn't rewrite
  old records.

### Full code `SITE.UNIT` is derived

- The unit's full code is not stored; API responses return it as `full_code`.
- This follows Plan.MD's "full path is derived" rule.

### OneERP warehouse

- The value is stripped but **not** upper-cased, because OneERP names are
  case-sensitive. Empty means NULL.
- It must be unique: one warehouse maps to one unit (Plan.MD § 1). A duplicate →
  409.
- It is otherwise free text until the OneERP sync (phase 6) validates it.

### Activation

- A site can't be deactivated while it has active units → 409.
- A unit can't be created or reactivated under an inactive site → 409.

### Duplicates → 409 from the database

- Duplicates are caught by the UNIQUE or primary keys. The shell maps
  `pymysql.err.IntegrityError` 1062 to 409.
- The shell reads the named key from the error message and returns a matching
  `field` and plain message, e.g. `uq_units_site_code` → `field: code`, "A unit
  with this code already exists at this site"; `uq_units_warehouse` →
  `field: oneerp_warehouse`, "This OneERP warehouse is already mapped to another
  unit".
- A pre-check with a SELECT is not relied on, because a SELECT followed by an
  INSERT is a race.

### Equipment code numbering

Decided 13-10-2026; built in S002, not here:
- The format is a 2–4-letter prefix plus 3 digits, e.g. `VBM001`.
- There is one counter per prefix across all sites, so a code survives a move
  between sites.
- The number grows to 4 digits past 999.
- The counter itself is a `serial_counters` row locked `FOR UPDATE`.

S001 only stores the prefix.

### Unit access

- **Usernames:**
  - A username is the Keycloak `preferred_username`, stripped and lower-cased,
    and must match `^[a-z0-9][a-z0-9._@-]{0,99}$`.
  - A username that matches no Keycloak user is accepted knowingly: Yantra can't
    list Keycloak users. The panel lists the users who have access rows, and a
    new user is added by typing a username.
- **Saving:**
  - Saving replaces that user's whole unit set in one `transaction()`: delete,
    then insert. An empty set removes the user from the list.
  - After commit, one structured log line is written:
    `user_units changed: actor=<a> user=<u> before=[SMTW.FWMILL,…] after=[…]`.
- **Inactive units:**
  - Only **active** units can be newly granted.
  - Access rows on a unit that is later deactivated are **kept**, so
    reactivating the unit restores access. S002's queries only see active units
    anyway.
  - `GET /user-units` returns `active` per unit, and the panel shows inactive
    units greyed out.
  - On save, an inactive unit the user **already holds** may stay in the list.
    An inactive unit **not already held** → 400. IT admin can untick an inactive
    unit to revoke it.
- **For S002:** the unit filter compares `g.user["username"].lower()` with
  `user_units.username`. Both sides are lower-case by rule.
- The manager's "all units" is a role rule, enforced in S002's queries. The
  manager needs no rows.

## 6. API (`/api/masters/…`)

**Lists:**
- Lists return `{items, total}`, ordered by code, and are **not paginated**. This
  is a deliberate departure from the base pattern: the lists are small (sites
  < 10, units < 100, classes < 200).
- Inactive records are hidden unless `?include_inactive=1` is passed.
- `GET /units` without `site_id` returns all units. Unit rows include `site_code`
  and `full_code`.

**Writes:**
- `POST` → 201 with the created record.
- `PUT` → 200 with the updated record, as the base's flat object.

**Errors:**
- Errors return `{error, field?}`.
  - 400 is a validation error. It carries the first error from `masters_core`
    and its `field`, so the screen shows one problem at a time, beside the field.
  - 404.
  - 409 is a duplicate, a code in use, or an activation rule.
- 409 is an addition to the base's 400/404/500, for conflicts the user can
  resolve.

| Method and path | Permission |
|---|---|
| `GET /sites`, `GET /units?site_id=`, `GET /equipment-classes` | `masters:read` (all roles) |
| `POST /sites`, `PUT /sites/<id>`, `POST /units`, `PUT /units/<id>` | `masters:edit` (IT admin) |
| `POST /equipment-classes`, `PUT /equipment-classes/<id>` | `equipment:edit` (engineer, manager, IT admin) |
| `GET /user-units` | `masters:read_senior` (IT admin) |
| `PUT /user-units/<username>` with `{unit_ids: [...]}` | `masters:edit` (IT admin) |

**Unit-access shapes:**
- `GET /user-units` returns one item per username:
  `{username, units: [{id, full_code, name, active}]}`.
- `PUT /user-units/<username>` → 200 with the same item for that user, with
  `units: []` when the set was emptied.

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Sites, units and unit access are edited by IT admin only (`masters:edit`). Equipment classes, and later equipment, are also edited by engineers (`equipment:edit`). | User decision, 13-10-2026 | Per-master keys; one key for all masters |
| Unit access is read under `masters:read_senior` (IT admin) | Keeps reads apart from writes, per the RBAC read hierarchy; engineers can be added in phase 3 | Gating the read with `masters:edit` |
| The class code is the equipment-code prefix (one field) | Two codes could drift apart | Separate `code` and `prefix` fields |
| The unit code is stored without the site part, and the full code is derived | Plan.MD's derived-path rule | Storing `SITE.UNIT` |
| Codes are frozen once in use (BR1-01) | Allows typo fixes during the data load; full immutability once anything depends on the code | Always immutable (too costly for places); always editable (too loose for class codes) |
| No hard delete; deactivation instead | ISO 55001 controlled register; history integrity | Deleting records that nothing references |
| The unit-access trail is a structured log line, not a table (BR1-02) | Meets ISO 27001 A.5.18 traceability with no new schema | A `user_unit_changes` table |
| Audit columns hold the last change only | Enough for v1 masters; stated rather than implied | Full change history |
| `oneerp_warehouse` is unique | One warehouse maps to one unit (Plan.MD § 1) | Allowing many units per warehouse |
| No seed data in the migration | Production data belongs in the DB, entered through the UI, not in code | Seeding the sites and units from Plant-Facts § 2 |
| `get_db()` and `transaction()` live in `db_helpers.py` | Avoids a circular import; keeps `local_db.py` free of Flask | Moving them into `local_db.py` |
| A reusable `ModuleToolbar.vue` | Every later module has a level-2 toolbar (Plan § 6) | Inline in `MastersView` now, extracted later |
| No pagination on master lists | Lists are small; simpler UI | Base-pattern server-side pagination |

## 8. Tests and acceptance

### Pure (`test_masters_core.py`)

- Code normalisation, and the regex boundaries:
  - class codes of 1, 2, 4 and 5 letters;
  - site and unit codes of 1 and 2 characters, with a dot, with a hyphen, and
    with a leading digit.
- Username normalisation and format.
- `oneerp_warehouse`: stripped but not upper-cased; empty becomes None.
- Required fields; names that are only whitespace; the shape of `errors`.

### API (`test_masters_api.py`)

- Create, list and edit, the happy path for each master. POST returns 201 and PUT
  returns 200 with the record.
- Duplicate code → 409, and duplicate `oneerp_warehouse` → 409, both coming from
  the database, each with its own `field` and message.
- Invalid code → 400 with `field`.
- Code changes:
  - a site with no units can change its code;
  - a unit with no access rows can change its code, and can move to another
    active site;
  - a site with a unit → 409;
  - a unit with access rows → 409 on a code change and on a site change;
  - an unchanged code, or no code, in the PUT body is accepted.
- Deactivating a site with active units → 409. A unit under an inactive site →
  409.
- The `include_inactive` filter.
- Audit: `created_*` is set on create; `updated_*` is NULL until the first edit
  and then set to the role client's username (e.g. `test_it_admin`).
- Unit access:
  - Replacing a user's set is atomic: an unknown `unit_id`, or an inactive unit
    not already held, → 400 and nothing changes.
  - An inactive unit already held may stay.
  - An empty list removes the user.
  - The log line is written (`caplog`).
- Every role can read sites (taken over from `test_modules.py`). An unknown role
  gets 403.

### RBAC

- An engineer gets 403 on site, unit and unit-access writes, and 2xx on class
  writes.
- An operator gets 403 on all writes.
- Every role can read sites, units and classes. Only IT admin and admin can read
  user-units.

### Test-DB hygiene

- The truncate runs once per session, after `ensure_schema()`. It runs in FK
  order (`user_units`, `units`, `sites`, `equipment_classes`) or with
  `SET FOREIGN_KEY_CHECKS=0`.
- Tests use unique codes and unique `oneerp_warehouse` values from a counter
  fixture, never fixed ones such as `SMTW`. This follows the base rule "fix the test, not the fixture".

### Frontend

- `navigation.test.js` permission lists match `config_rbac`.
- A manual browser check of each panel:
  - create, edit and deactivate;
  - errors shown inline;
  - the code hint;
  - inactive units greyed out in Unit access.

### Acceptance

- `tooling/run-tests.bat` is green.
- Through the UI, IT admin can enter the six sites in Plant-Facts § 2 and the
  units `SMTW.FWMILL`, `SMTW.MCC1` and `SMTW.MCC2`, and can grant a user units.
- An engineer can add the `VBM` class.

## 9. Open questions and assumptions

1. **Assumption:** operators, technicians, engineers and managers can all *read*
   sites, units and classes, as pick-lists for later screens.
2. **Assumption:** the role clients in the test suite use usernames such as
   `test_it_admin`, so the audit columns are checked against those names.
3. **Confirmed by the user at approval (13-10-2026):** codes are correctable
   until used (BR1-01), and the extra read key `masters:read_senior` (BR1-07).

## 10. Amendments

### A1 — Default site; deactivate inside the edit dialog (13-10-2026)

```
Requested by: the user, 13-10-2026, during code review r1
Status: Approved 13-10-2026 by KLA
```

The user asked for two things:
- "Add a 'Default [ ]' in site, to make it the preferred site in selections."
- "Move the deactivate button to the edit site dialog."

#### A1.1 Default site

**What.**
- A **Default** checkbox on the site form.
- At most one site is the default, and there may be none.
- Wherever a screen asks the user to *pick one site*, the default site is
  preselected. In S001 that is the Site field of the Add-unit dialog; in S002 it
  will be the equipment form.
- The site lists mark the default site with a "Default" badge.

**Data model.**
- Migration **v3** (appended; v2 stays as applied, per "migrations are
  append-only") adds `sites.is_default TINYINT(1) NULL`.
- The value is 1 for the default site and **NULL** for every other site, never 0.
- A named unique index `uq_sites_default (is_default)` then lets the **database**
  guarantee there is only one default. MariaDB allows any number of NULLs under a
  UNIQUE index, so the index only bites on a second 1.
- The API shows the column as a boolean `is_default`.

**Rules.**
- Ticking Default on site B while site A is the default **moves** the default:
  - In one `transaction()`, A's row is locked and cleared, then B is set.
  - Both rows get `updated_at` / `updated_by`.
  - The 1062 error on `uq_sites_default`, raised if two saves race, maps to a 409
    "Another site was made the default at the same time; reload and try again".
- Unticking Default on the default site leaves **no default**. That is allowed.
- An inactive site can't be the default:
  - Ticking Default on an inactive site → 409 (field `is_default`).
  - Deactivating the default site → 409 "This is the default site; untick
    Default first" (field `active`).

  This is explicit, like the existing "site with active units" rule. It avoids
  quietly leaving no default.
- `is_default` is accepted on POST and PUT, under `masters:edit` (IT admin), like
  every other site field.
- The default site is **one setting for everyone** (a site field), as requested.

**Standard.** None governs this; it is a usability default. It also doesn't
touch the record's identity, so the "frozen once in use" rule doesn't apply.

#### A1.2 Deactivate / reactivate inside the edit dialog

**What.**
- The row button for deactivate and reactivate is removed.
- The **edit** dialog gets a **Deactivate** button (or **Reactivate** for an
  inactive record), placed on the left of the footer, away from Save.
- The create dialog has no such button.

**Scope.** All three panels: sites, units and equipment classes. They share
`useMasterForm.js` and `FormModal.vue`, so moving the button for sites only would
leave the screens inconsistent.

**Behaviour.**
- The button acts immediately, sending a separate `PUT {active}`. It doesn't wait
  for Save, and other unsaved edits in the dialog are not sent.
- A refusal shows inside the dialog, e.g. the 409 for a site with active units or
  for the default site.
- On success the dialog closes and the list reloads.
- Deactivating asks for confirmation inside the dialog, as an inline "Deactivate
  `SMTW-KP`? Yes / No" row, not a browser `confirm()`. Deactivation hides the
  record from pick-lists. Reactivating needs no confirmation.

#### A1.3 Where

- `backend/local_db.py`: migration v3.
- `backend/masters_core.py`: validate `is_default` as a boolean.
- `backend/masters.py`:
  - the default move and its activation rules;
  - `is_default` in site responses;
  - the 1062 mapping for `uq_sites_default`.
- `frontend/src/components/FormModal.vue`: a left-side footer slot.
- `frontend/src/views/masters/useMasterForm.js`: deactivate/reactivate from the
  dialog, with the inline confirmation.
- `frontend/src/views/masters/SitesPanel.vue`:
  - the Default checkbox and badge;
  - the row button removed.
- `frontend/src/views/masters/UnitsPanel.vue`:
  - the default site preselected in the Add-unit dialog;
  - the row button removed.
- `frontend/src/views/masters/EquipmentClassesPanel.vue`: the row button removed.
- `frontend/src/stores/masters.js`: a `defaultSiteId()` helper for S002 to reuse.

#### A1.4 Tests

**Pure:** `is_default` accepts true, false, 1 and 0, and rejects anything else.

**API:**
- Set a default.
- Move the default from A to B: A is cleared and both audits are set.
- Untick the default: no default remains.
- Set Default on an inactive site → 409.
- Deactivate the default site → 409.
- Create a site with Default ticked while another site is the default: the
  default moves.
- `is_default` appears in `GET /sites`.
- An engineer gets 403 when setting Default.

**Manual (browser):**
- The badge and the preselection in Add-unit.
- The Deactivate and Reactivate buttons in each edit dialog.
- The inline confirmation.
- A refusal shown inside the dialog.

#### A1.5 Points settled at approval (13-10-2026)

1. **Filters — decided by the user:** the default site is preselected only in
   *pick-one* fields. Site **filters**, such as the Units panel's, stay on "All
   sites".
2. **Deactivate in the dialog — decided by the user:** all three dialogs (sites,
   units, equipment classes), as in A1.2.
3. **Per-user default (later, not in A1):** one default for everyone suits a
   single main factory. A user who works at SSVT would rather have their own
   default, for example the site of their units. That can come later without
   changing this column.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 13-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 Immutable site/unit codes | major | **Accepted, option (b)**, frozen once in use. § 5 rewritten (reference table, lock-then-count in a transaction, unchanged code accepted), § 7 and § 8 updated, S003 snapshot pointer added. Flagged to the user in § 9.3. |
| BR1-02 No trail for unit-access changes | major | **Accepted, option (a).** A structured log line per PUT; § 2 now says the audit columns hold the last change only. Test via `caplog`. |
| BR1-03 Broken tests not listed | minor | **Accepted.** `test_modules.py` (`TestMasters` moves) and `test_auth.py` (engineer → `equipment:edit`) added to § 3. |
| BR1-04 Access rows on a deactivated unit | minor | **Accepted.** Rows are kept; `active` is returned per unit and shown greyed; a held inactive unit may stay on save; a newly added inactive unit → 400. |
| BR1-05 409 from the UNIQUE index | minor | **Accepted.** `IntegrityError` 1062 → 409; no reliance on a pre-check (§ 5). |
| BR1-06 Where `get_db()` lives | minor | **Accepted, option (a).** `get_db()`, the teardown and `transaction()` go to `db_helpers.py`; `local_db.py` stays free of Flask. |
| BR1-07 GET gated by an edit key | minor | **Accepted.** New `masters:read_senior = ("it_admin",)` for `GET /user-units`. Flagged to the user in § 9.3 (one key more than they chose). |
| BR1-08 Standards citations | minor | **Accepted.** ISO 27001 now cites A.5.15, A.5.18 and A.5.3 (A.8.2 removed). ISO 55001 cited as § 7.5–7.6 (2014 edition). "Functional locations" explained in § 2. |
| BR1-09 `oneerp_warehouse` uniqueness | minor | **Accepted.** `UNIQUE(oneerp_warehouse)`; stripped, not upper-cased; empty → NULL. |
| BR1-10 API details | minor | **Accepted.** `api.js` copies `field`; 201 / 200 bodies; `errors` as a list of `{field, message}`, first one returned; `GET /units` with no filter returns all units. |
| BR1-11 Username rules | minor | **Accepted.** Format regex added; lower-case rule stated for both sides of the S002 filter. |
| BR1-12 Level-2 toolbar | minor | **Accepted.** Reusable `components/layout/ModuleToolbar.vue`. |
| BR1-13 Warn before a code is frozen | nit | **Accepted.** Hint under the code field. |
| BR1-14 Test-DB hygiene | nit | **Accepted.** § 8 "Test-DB hygiene". |
| BR1-15 Small points | nit | **Accepted.** INT AUTO_INCREMENT ids; audit convention fixed for all tables (§ 4); lists ordered by code; unit code minimum length 2. |
| BR1-16 Step status | nit | **Accepted.** Status set to `In review`; README index updated. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 13-10-2026

The reviewer verified every round-1 change and found no blocker or major
finding open. The user approved the brief. The round-2 findings below are
consistent with what was approved, and are folded in at approval.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 Unit `site_id` outside the frozen rule | minor | **Accepted.** `site_id` follows the same rule as `code` (§ 5); tests added (§ 8). |
| BR2-02 "Nothing is ever hard-deleted" not exact | nit | **Accepted.** § 1 reworded: no *master record* is hard-deleted; unit-access rows are replaced on save, with the change logged. |
| BR2-03 Why site and unit codes freeze | nit | **Accepted.** § 5 explains: integrity for class codes; change control (ISO 55001) for sites and units. |
| BR2-04 Which key collided | nit | **Accepted.** Unique indexes named in § 4; the shell maps the key name to a `field` and a plain message (§ 5). |
| BR2-05 Small gaps | nit | **Accepted.** No `code` in the body = unchanged; unit code-change happy-path test; counter fixture covers `oneerp_warehouse`. |
| BR2-06 Record the frozen rule in Plan.MD | nit | **Accepted.** Recorded in Plan.MD § 4.1, with the `masters:read_senior` row in § 3. |
