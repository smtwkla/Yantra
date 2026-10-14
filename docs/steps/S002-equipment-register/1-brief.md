```
Step: S002 — Equipment register
Doc: brief
Author: Planner (Opus)
Date: 14-10-2026 (revised 14-10-2026 after brief-reviews r1, r2 and r3)
Status: Approved 14-10-2026 by KLA
```

# S002 — Equipment register: the equipment tree (backend)

Second slice of Plan.MD phase 2. It builds on S001: sites, units, equipment
classes and unit access. S001 must be committed before S002's code starts.

**Split (BR1-04, confirmed by the user 14-10-2026):** S002 is the **backend**:
- the migration;
- the pure core;
- the API;
- unit-access enforcement;
- the backend tests.

The screens become **S003 "Equipment register — screens"**, planned once S002 is
approved; documents/QR move down one number. The screen design
agreed so far is kept in the appendix *Handover to S003*, so nothing is lost.

Background reading:
- `docs/Plan.MD` § 3, § 4.1, § 5;
- `docs/Maintenance-Philosophy.md` § 7, § 9, § 12;
- `docs/Plant-Facts.md` § 2–3;
- `docs/steps/S001-basic-masters/1-brief.md`: its rules on codes, audit and errors
  carry over;
- `.claude/SMTW-WebApp-Base.md`: serial numbers, API responses, pagination, the
  event-sourced module pattern (for contrast, § 6 Events).

## 1. What will be built

The **equipment register API**: every maintained item of the plant, arranged as a
tree. There is one table, and each row is an individual physical item with three
possible levels:
- **equipment**;
- **component-unit**;
- **component**.

Every node of the tree gets a permanent code, issued automatically (`VBM001`).
The API can:
- list, search and filter;
- read one node with its parts and history;
- create nodes;
- edit them;
- move equipment to another unit;
- move a part to another parent;
- change status, criticality and class.

Every move and every change of status, criticality or class is written to an
**event history**.

From this step on, **unit access is enforced** on the server. Each user sees and
edits only equipment at their units; holders of `equipment:read_all_units`
(manager, IT admin; admin bypasses) see all units.

**Out of scope:**
- the screens (S003);
- documents and photos, QR labels;
- bulk import (not needed now, user 14-10-2026);
- breakdowns, PM and meters (phases 3–4);
- the full history card (phase 5);
- parts, ISO 14224 level 9 (later, with spares);
- rotable tracking (later);
- a standby relationship ("compressor 2 backs up compressor 1");
- a remark on events, such as a reason for scrapping (§ 10).

## 2. Standards and practice

**ISO 14224 taxonomy (levels 6–8).**

| Level | ISO 14224 | Yantra | Example |
|---|---|---|---|
| 6 | Equipment unit | **equipment** | `VBM001`, the vertical blade mill |
| 7 | Subunit | **component-unit** | its drive; its hydraulic power pack |
| 8 | Maintainable item | **component** | the drive's motor `MOT017`; the gearbox `GB003` |

- ISO 14224's levels are applied as far as they are meaningful. A simple machine
  with no real subunit has its maintainable items directly under the equipment
  unit. That is why a component may sit under an equipment.
- **Boundary.** Each equipment class in ISO 14224 Annex A has a boundary diagram:
  what is inside the unit for failure recording. Utilities that feed a machine
  are outside it. The two Atlas Copco compressors feeding MCC2 are therefore
  **their own equipment**, not components of the extruder. This is guidance for
  the engineer loading the register; it isn't enforced in code.

**Criticality ranking.** The meanings are those of Maintenance-Philosophy § 9,
**decided 14-10-2026**:

| Grade | Meaning |
|---|---|
| **A** | Stops a production line or is a safety/environment risk; no standby |
| **B** | Slows production or has a standby; repair within the shift |
| **C** | No direct production impact; repair when convenient |

Where this comes from:
- **TPM.** The planned-maintenance pillar's first step is to *evaluate and rank
  equipment* (A/B/C by production, quality, safety and maintenance factors), so
  that PM effort goes where it matters. This is where plant people will have met
  A/B/C.
- **ISO 55001 § 6.1** (2014 numbering; risks and opportunities) and **§ 6.2.2** (planning,
  decision-making criteria) are the clauses where criticality lives.
- **NORSOK Z-008** ("Risk based maintenance and consequence classification",
  oil & gas) classes the *consequence* of failure for safety, environment and
  production, with redundancy lowering the class. A/B/C with "no standby / has
  standby" is that scheme in plain words. We adopt the idea, not its code lists.

**EN 13306 states.**
- The *condition* is **up** or **down**: can the item perform its function now?
- Within up, the *use* is **operating**, **standby** or **idle**.
- Yantra's register status maps as follows:
  - `in_service` is up, operating or idle;
  - `standby` is EN 13306 standby;
  - `out_of_use` has no EN 13306 term: it is a life-cycle status, withdrawn and
    not maintained;
  - `scrapped` is end of life.
- **"Down" is derived** from open breakdown tickets (phase 3) and is never typed,
  so two sources can't disagree.

**ISO 55000 life cycle.** The usual stages are acquire, operate and maintain, and
dispose. "Scrapped" is disposal.

**ISO 55001 controlled register** (clause numbers as in the 2014 edition, as in S001;
ISO 55001:2024 exists).
- **§ 7.5–7.6:** codes are permanent and nothing is hard-deleted.
- **§ 8.2 (management of change):** changes to assets are assessed and recorded.
  Moves, reclassification and scrapping are such changes, and the event history
  is their record.
- **ISO 14224** also needs to know *where* equipment was when it failed. The
  events' full-path snapshots keep that.

**ISO 27001:2022 A.5.15 (access control) and A.8.3 (information access
restriction).** S001 granted unit access; S002 is the **enforcing** side.
Equipment outside a user's units is not shown at all (404).

## 3. Decisions taken with the user (14-10-2026)

1. **Criticality.** The meanings are as above.
   - It is **required** on equipment, and new equipment starts at **C**.
   - Component-units and components **inherit** their equipment's grade unless
     graded themselves.
2. **Status.** Four states: **in service**, **standby**, **out of use**
   (laid up; no PM due) and **scrapped** (final, read-only).
3. **Tree.** Fixed three levels.
   - A component sits under a component-unit **or directly under an equipment**.
   - **Only equipment has a unit**; its parts follow it.
4. **History.** An **event table now**: one row per tracked change, with old →
   new values.

## 4. Where

### Backend

- **Migration v4** in `backend/local_db.py`: the tables `serial_counters`,
  `equipment` and `equipment_events` (§ 5).
- **`backend/equipment_core.py`** (new, pure; no DB, no Flask, no `now()`):
  - `validate_equipment(data, creating, this_year)`: the `(clean, errors)` shape
    of `masters_core`, with `errors` a list of `{field, message}`;
  - `format_equipment_code(prefix, number)`: `prefix + str(number).zfill(3)`;
  - `check_parent(child_level, parent_level)`;
  - `effective_criticality(own, equipment_grade)`;
  - `full_path(site_code, unit_code, codes_root_to_node)`;
  - `tracked_changes(before, after)`: two dicts of **display values** keyed by
    the tracked names; returns `[(event, old, new)]` (§ 6 Events);
  - `check_status_change(old, new)`.
- **`backend/equipment.py`** (new blueprint at `/api/equipment`): the routes, unit
  access, the code issue, locking and events. It reuses `get_db()` and
  `transaction()` from `db_helpers.py`.
  - A comment at the top states the lock order (§ 6 Locking).
- **Shared shell code moves out of `masters.py`** (BR1-09, BR3-03), so that
  `equipment.py` reuses it rather than copying it.
  - **`backend/api_common.py`** (new): the request-level pieces.
    - `ApiError`.
    - The `UNIQUE_KEY_ERRORS` dict.
    - `register_error_handlers(app)`, which handles `ApiError` and the 1062 → 409
      mapping **at app level**; `app.py` calls it once.
    - `actor()` and `clean_body(validator, creating)`, today `_actor` and
      `_clean_body` in `masters.py`.
    - Each module adds its own keys at import:
      `UNIQUE_KEY_ERRORS.update({...})`.
  - **`backend/db_helpers.py`** gains the generic SQL helpers: `insert_row`,
    `update_row`, `count` and `fetch_one`, today `_insert`, `_update`, `_count`
    and `_fetch_one` in `masters.py`.
    - `masters.py`'s `_lock_row` stays where it is: it returns only the id.
      `equipment.py` needs locking reads that return decision columns
      (§ Locking), so it has its own.
  - **Behaviour is unchanged.**
    - The existing `TestErrorMapping` tests are the regression tests for the move:
      a 1062 on `PRIMARY` gives a generic 409 with no `field`, and any other
      `IntegrityError` is re-raised.
    - Their monkeypatch target changes name, from `masters._insert` to
      `masters.insert_row`. Patch the name where `masters` looks it up.
- **`backend/masters.py`**:
  - Its error and helper code moves to `api_common.py` and `db_helpers.py`.
  - **Frozen codes:** "referenced" now also counts equipment, **including
    scrapped equipment**. A scrapped `VBM001` still carries the prefix and still
    appears in history.
    - A unit with any equipment can't change its code or its site.
    - A class with any equipment can't change its code.
  - **Activation:** a unit can't be deactivated while it holds equipment that
    isn't scrapped → 409, field `active`.
    - Laid-up (`out_of_use`) equipment also blocks it (user, 14-10-2026; § 10).
  - These counts are safe only because the equipment create locks the unit and
    class rows (§ 6 Locking).
- **`backend/config_rbac.py`**: new entries, ordered to match the nav (Equipment
  before Masters):
  - `equipment:read` = `("*",)`;
  - `equipment:read_all_units` = `("maint_manager", "it_admin")`;
  - `equipment:edit` stays as it is.

### Tests

- `backend/tests/test_equipment_core.py` (new, pure).
- `backend/tests/test_equipment_api.py` (new, against the DB). It provides a
  `make_equipment` fixture through `conftest.py`, so that `test_masters_api.py`
  can use it too.
- `backend/tests/test_masters_api.py`: `TestUnitCodeFreeze`,
  `TestActivationRules` and the class-freeze cases gain equipment cases.
- **Breaking tests to update:**
  - `test_rbac.py::TestComputePermissions::test_role_matrix` (every row);
  - `test_auth.py::test_storekeeper_client_role_accepted` and
    `test_realm_role_maps_to_user`, which assert `permissions == ["masters:read"]`
    exactly.
- `conftest.py`:
  - The truncate list becomes `("equipment_events", "equipment", "user_units",
    "units", "sites", "equipment_classes", "serial_counters")`.
  - `equipment` references itself (`parent_id`), so a plain `DELETE` fails with
    error 1451. The truncate runs with `SET FOREIGN_KEY_CHECKS=0` on its own
    connection, then sets it back to 1 (BR2-04).
  - `role_client(role, username=None)` gains an optional username, so unit-access
    tests use a **fresh username** each, not the shared `test_<role>`
    (BR2-05).
    - It is sent as a second test header, `X-Test-User`, which the test
      `_inject_test_user` hook reads. When the header is absent, the username
      stays `test_<role>`.
    - Like `X-Test-Role`, it only works when `TESTING` is on (BR3-04).
  - Code assertions are **relative** (`n`, `n+1`) within a fresh class from
    `uniq.class_code()`, never absolute.

### Docs

None for the coder. At approval the planner records the following:
- **Plan § 4.1:** the status list gains "out of use"; the standby relationship is
  not recorded.
- **Plan § 5:** `equipment_events`; `serial_counters` used from phase 2.
- **Plan § 3:** the `equipment:read_all_units` row.
- **Maintenance-Philosophy § 9:** A/B/C are now Decided.

## 5. Data model (migration v4)

- The audit convention follows S001 § 4.
- Unique keys, foreign keys and checks are **named**.

**`serial_counters`**: one row per numbering scope. It is reused later by the
`BD-` and `PM-` serials.

| Column | Type |
|---|---|
| `scope` | `VARCHAR(40) PRIMARY KEY`, e.g. `EQ:VBM` |
| `last_value` | `INT NOT NULL` |

It is a counter, not a record, so it has no audit columns.

**`equipment`**:

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `code` | `VARCHAR(12) NOT NULL`, issued by the shell, never changes. `uq_equipment_code` |
| `level` | `ENUM('equipment','component_unit','component') NOT NULL`, fixed at create |
| `parent_id` | `INT NULL`. `fk_equipment_parent` → `equipment` |
| `unit_id` | `INT NULL`. `fk_equipment_unit` → `units` |
| `class_id` | `INT NOT NULL`. `fk_equipment_class` → `equipment_classes` |
| `name` | `VARCHAR(100) NOT NULL` |
| `make`, `model` | `VARCHAR(100) NULL` |
| `serial_no` | `VARCHAR(100) NULL`. The manufacturer's serial, not unique |
| `year` | `SMALLINT NULL`; 1900 ≤ year ≤ this year + 1 (IST) |
| `criticality` | `ENUM('A','B','C') NULL`. Required on equipment (shell rule, default `C`); NULL on a part means "inherit" |
| `status` | `ENUM('in_service','standby','out_of_use','scrapped') NOT NULL DEFAULT 'in_service'` |
| audit | `created_at`, `created_by`, `updated_at`, `updated_by` |

- **Check** `chk_equipment_level_place`:
  `(level = 'equipment') = (unit_id IS NOT NULL) AND (level = 'equipment') = (parent_id IS NULL)`.
  MariaDB enforces CHECK constraints. So "equipment has a unit and no parent;
  parts have a parent and no unit" is a database rule, not only a shell rule.
- The FKs give indexes on `parent_id`, `unit_id` and `class_id`.

**`equipment_events`**: a **history log**, not event-sourced state.
`equipment.status` and the other columns remain the truth; nothing replays events.

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `equipment_id` | `fk_equipment_events_equipment` → `equipment` |
| `event` | `ENUM('created','moved_unit','moved_parent','status','criticality','class') NOT NULL` |
| `old_value`, `new_value` | `VARCHAR(200) NULL`, text snapshots (§ 6 Events) |
| `created_at`, `created_by` | as in the audit convention |

The index is `(equipment_id, created_at)`.

## 6. Rules

### Resolving a node's unit (one place)

A part's unit is that of its **root equipment**. The tree is fixed at three
levels, so the root is at most two steps up.

There is **one SQL fragment** (BR2-03), a module constant in `equipment.py`,
used by the list, the detail, the access check and the target checks:

```
FROM equipment e
LEFT JOIN equipment p  ON p.id  = e.parent_id
LEFT JOIN equipment gp ON gp.id = p.parent_id
JOIN units u ON u.id = COALESCE(gp.unit_id, p.unit_id, e.unit_id)
JOIN sites s ON s.id = u.site_id
-- root_id          = COALESCE(gp.id, p.id, e.id)
-- root_criticality = CASE WHEN gp.id IS NOT NULL THEN gp.criticality
--                         WHEN p.id  IS NOT NULL THEN p.criticality
--                         ELSE e.criticality END
-- effective        = COALESCE(e.criticality, root_criticality)
```

- `root_criticality` is the **equipment's** grade at every depth. A component
  under a graded component-unit still inherits the equipment's grade (decision
  § 3.1).
- It is written as a `CASE` that picks the root row, not as a `COALESCE` over the
  levels (BR3-04 corrects the round-2 reason).
  - The equipment's grade is never NULL (shell rule), so a COALESCE in the order
    `gp, p, e` would give the same answer.
  - But if an equipment's grade were ever NULL, the COALESCE would silently fall
    through to the component-unit's grade and **mask** the error.
  - The CASE **exposes** it as a NULL effective grade.
- The list's `criticality` filter works on the **effective** grade.
- **The fragment is only ever used for plain reads.** It is never used with
  `FOR UPDATE`.
  - MariaDB has no `FOR UPDATE OF`. A locking read through the join would also
    lock the parent and grandparent rows, and two opposite re-parents would then
    deadlock (BR2-01).
  - Locking always uses the single-row form (§ Locking).

There are **three helpers**. Only they call `_accessible_unit_ids`, and nothing
else in `equipment.py` touches `user_units`.
- **`_accessible_unit_ids(cur)`** returns:
  - `None` for holders of `equipment:read_all_units`, checked with `has_perm`, so
    admin is included;
  - otherwise the user's **active** unit ids, with the username compared
    lower-case (S001 BR1-11).
- **`_load_node_for_user(cur, node_id, for_update)`**: loads the node being read
  or written.
  1. With `for_update`, it first locks the node with
     `SELECT id, level, status, parent_id, unit_id, class_id FROM equipment WHERE id = %s FOR UPDATE`,
     and returns that row for the decisions (§ Locking).
  2. It then reads the node through the fragment, for access and display.
  3. A missing node, or one outside the user's units → **404**.
- **`_load_target_node(cur, node_id, field)`** (BR3-02): loads a **target parent**
  in a create or re-parent. It works in this order:
  1. It locks the row as above. A missing row → **400** with `field`
     (`parent_id`).
  2. It resolves the target's root unit through the fragment. Outside the user's
     units → **403** with `field`.
  3. The locked row is scrapped → **409** with `field`.
  4. The level rule, from the locked row → **400** with `field`.

  A target can't use the 404 helper: a request naming a target the user can't
  access is answered with 403, as stated in § Unit access.

**Consequence of "active units only"** (BR2-09). A unit can be deactivated only
when it holds no equipment that is still in use. Scrapped equipment left in a
deactivated unit is then invisible to engineers, technicians and operators. Only
holders of `read_all_units` still see it. That is accepted: it is history, and the
manager can open it.

### Codes

- On create, the shell issues the code from the class prefix with a per-prefix
  counter, `scope = 'EQ:' + class code`. This is decided Plan Q3.
- **The counter bump and the INSERT are one transaction** (BR1-01):
  1. `INSERT INTO serial_counters (scope, last_value) VALUES (%s, 1) ON DUPLICATE KEY UPDATE last_value = last_value + 1`
  2. `SELECT last_value FROM serial_counters WHERE scope = %s`, on the same
     connection, inside the transaction. It sees its own write, and the row stays
     locked until commit.
     - Not `LAST_INSERT_ID()`, not `MAX(code)`.
- **No gaps from failures.** A create that fails after the bump rolls the bump
  back. The only failures possible there are a DB error and an impossible 1062.
  Gaps appear only from scrapping; numbers are never re-issued after commit.
- **No race on a brand-new prefix.** Creates of one class are serialised by the
  class row lock, taken before the counter (§ Locking). The duplicate-key
  deadlock on a first `INSERT` therefore can't occur (BR2-07; corrects round 1).
- The format is `prefix + str(n).zfill(3)`: `VBM001`; `VBM1000` after `VBM999`.
- **Codes never change**, not on a move and not on reclassification (Plan § 4.1).
  A `VBM` equipment reclassified to `HP` keeps `VBM001`. The class change is
  logged and affects only grouping and reporting.

### Tree

| Level | Allowed parent | Unit |
|---|---|---|
| equipment | none | required; an active unit |
| component_unit | an equipment | none; its root's |
| component | a component_unit or an equipment | none; its root's |

- `level` can't be changed after create.
- **Re-parenting:** the level rule must still hold, the new parent must not be
  scrapped, and the node takes the new root's unit. A component-unit moves with
  its components.
- **Moving equipment** to another unit moves its subtree implicitly. It writes
  **one** `moved_unit` event, on the equipment.
- **Full path:** `SITE.UNIT.EQUIP[.COMPUNIT][.COMPONENT]`, for example
  `SMTW.FWMILL.VBM001.DRV002.MOT017`. It is derived, never stored.

### Criticality

- **Equipment:** required, default `C`. `criticality: null` on a PUT → 400.
- **Parts:** optional. `null` means "inherit"; setting `null` again re-inherits.
- Effective criticality = the part's own grade, or else its root equipment's.
- The API returns both `criticality` (own) and `effective_criticality`.

### Status

| Change | Rule |
|---|---|
| on create | `in_service` (default), `standby` or `out_of_use`. `scrapped` → 400: nothing is born scrapped |
| in_service ↔ standby ↔ out_of_use | allowed, any direction |
| any → scrapped | only if every direct and indirect part is already scrapped. Otherwise 409 "Scrap or move its parts first", field `status` |
| scrapped → anything | **no**. Final (decided). |

- **A scrapped node is read-only.** **Any** PUT on it → 409 "This record is
  scrapped and cannot be changed", with no field. It can't be a create or move
  target either: 409, field `parent_id`.
- **Scrapping and other changes in one PUT:** applied together; the node is
  read-only afterwards.
- A scrapped node stays visible on its parent's page and in its own history. It
  drops out of the list unless `include_scrapped=1` is passed.
- Parts have their own status. A motor can be scrapped and replaced while the mill
  stays in service.

### Classes and units as targets

| Change | Refused when | Response |
|---|---|---|
| Create, or move to an inactive unit | the unit is inactive | 409, field `unit_id` |
| Create, or reclassify to an inactive class | the class is inactive | 409, field `class_id` |
| Create under a parent, or move to a parent | the parent is scrapped | 409, field `parent_id` |

Existing equipment keeps a unit or class that is later deactivated.

### Unit access (Plan § 3; ISO 27001 A.8.3)

**Order of checks on every write:**
1. permission → 403, from `require_perm`;
2. load the node with access → 404;
3. scrapped → 409;
4. validation → 400;
5. rules and targets → 409 / 403.

This order means a 400 never reveals a node the user can't see.

**Targets:**
- **POST and PUT** need access to the **target** unit, or to the target parent's
  root unit, as well → **403**, with field `unit_id` or `parent_id`.
- The 403 (rather than 404) is acceptable: `GET /api/masters/units` already lists
  every unit to every role, so a unit's existence isn't a secret. A parent id is a
  weak leak at most.

**Lists:**
- Filters intersect with access. `unit_id` for a unit the user can't access
  returns an empty page, not a 403.
- `site_id` filters through `units.site_id`.
- A user with no unit rows and without `read_all_units` gets an empty list. That
  is not an error.

### Locking (BR1-02, revised after BR2-01 / BR2-02)

**One global lock order**, for every write in `equipment.py`:

> **(1) the node's own row → (2) the target parent row → (3) the unit row →
> (4) the class row → (5) the `serial_counters` row**

Each step is taken only when the write needs it.

- **Every lock is a single-row `SELECT … FROM <table> WHERE id = %s FOR UPDATE`.**
  It is never taken through the join fragment.
- **Ancestors are never locked.** They are resolved by plain reads, after the
  locks.

**Decisions come from the locking read itself** (BR2-02, made exact by BR3-01).
- Each locking `SELECT` returns the columns that the decisions about that row
  need:

  | Table | Columns returned by the lock |
  |---|---|
  | `equipment` | `id, level, status, parent_id, unit_id, class_id` |
  | `units` | `id, active` |
  | `equipment_classes` | `id, code, active` |

- Every refusal about a row is decided **only from that returned row**. This
  covers scrapped, level rule, active, and the class prefix.
- The reason is REPEATABLE READ:
  - A locking read always returns the **latest committed** version of the row,
    even after waiting for a lock.
  - A plain read returns the transaction's **snapshot**, which is fixed by the
    first plain read.
  - A write that takes a later lock, for example the target parent after its own
    node, may wait on a concurrent commit. A plain read of that target afterwards
    could show the state from before the wait: a parent that has just been
    scrapped, a deactivated unit, or a renamed class prefix.
- **The fragment and other plain reads are used only for access checks and
  display values:** paths, codes, names, and the target's root unit.
- `_accessible_unit_ids` runs **after** the node lock.
- **Accepted consequence:** if a user's unit access is revoked while their write
  waits for a lock, the write still completes (missing sentence from BR2-01).
  Access is checked once per request, which is normal for a request-scoped
  permission check.
- This is also why S001's counts in `masters.py` are safe: there, `_lock_row` is
  the first statement of the transaction.

| Write | Locks, in order | Checks after the locks |
|---|---|---|
| Create equipment | (3) unit; (4) class; (5) counter | unit active; class active; prefix read **after** the class lock; access to the unit |
| Create part | (2) parent; (4) class; (5) counter | parent not scrapped; level rule; class active; access to the parent's root unit (plain fragment read) |
| Edit fields, criticality, status (not scrapping) | (1) node | access → 404; scrapped → 409 |
| Reclassify | (1) node; (4) target class | as above; class active |
| Move equipment to a unit | (1) node; (3) target unit | as above; unit active; access to the target |
| Re-parent a part | (1) node; (2) target parent | as above; target not scrapped; level rule; access to the target's root |
| Scrap | (1) node; then a **locking read of the subtree**: `SELECT id, status FROM equipment WHERE parent_id = %s FOR UPDATE` for the children, then `… WHERE parent_id IN (…) FOR UPDATE` for the grandchildren. The second read is skipped when there are no children, because `IN ()` is invalid SQL. | any child or grandchild not scrapped → 409 |

**Why there's no deadlock in the normal case:**
- Every path takes its locks in the global order.
- A child is always created or re-parented by locking the *target parent* row, so
  it can't slip under a node whose scrap check is waiting.
- `level` is immutable and a parent is always a higher level, so the tree has no
  cycles.

**The one remaining deadlock, accepted.** The scrap check locks a node's subtree
top-down: the node, then its children. That is the reverse of the global order.

*Example:* someone scraps N while someone else re-parents component X between two
component-units of that same N.
- Each locks one row the other needs.
- InnoDB detects this and aborts one of them with a 500, and the user retries.

Two people would need to edit the inside of one machine while a third scraps it,
at the same moment. That is accepted, in line with the user's decision on S001
CR2-01 (deadlocks are not given special handling).

**Interaction with `masters.py`:**

| Function in `masters.py` | Locks |
|---|---|
| `update_unit` | the unit row, then the **site** row |
| `create_unit` | the **site** row only (BR3-04) |
| `update_equipment_class` | the class row |
| `replace_user_units` | `user_units` rows and the unit rows it checks |

- `equipment.py` never locks `sites` or `user_units`.
- It locks units and classes only *after* any equipment rows.
- Masters locks no equipment rows.

So no cycle spans the two modules. Masters' equipment counts run after its own
row lock, the first statement in its transaction. The equipment create locks
those same unit and class rows before its INSERT, so the counts are safe (S001
rule, extended in § 4).

### Events (BR1-06)

**When events are written:**
- In the same transaction as the change, so a rolled-back edit leaves no event.
- One event per tracked change. The shell resolves display values before and
  after the UPDATE and calls `tracked_changes`. The comparison logic lives in the
  core.
- Edits to name, make, model, serial or year are **not** events. They keep only
  the audit columns' last change.

**What each event records:**

| Event | `old_value` → `new_value` | When |
|---|---|---|
| `created` | NULL → full path | on insert |
| `moved_unit` | full path before → after | equipment only, unit changed |
| `moved_parent` | full path before → after | parts only, parent changed. **One** event even when the unit changes too: the unit change is visible in the paths |
| `status` | stored values, e.g. `in_service` → `standby` | status changed; the UI labels them |
| `criticality` | `inherit` / `A` / `B` / `C` | the node's **own** value changed. A part whose *effective* grade changes because its equipment was regraded gets **no** event |
| `class` | class codes, e.g. `VBM` → `HP` | class changed |

The detail view orders events by `created_at DESC, id DESC`, because one PUT can
write two rows in the same second.

### Errors

Errors follow the S001 shape: `{error, field?}`, with 400, 403, 404 or 409.
- **Unknown ids** (BR2-06): a `unit_id`, `parent_id` or `class_id` that doesn't
  exist → 400 with that field, as in masters for `site_id`.
- **`code` and `level` in a PUT body:**
  - equal to the stored value → accepted, as unchanged;
  - different → 400, with field `code` or `level`, "cannot be changed".
- **Body validation runs after the node load,** so a 404 always comes before a
  400. The order is the one in § Unit access.
- A 1062 on `uq_equipment_code` → 409 "Code collision — retry", with no field.
- A CHECK violation (pymysql `OperationalError` 4025) can't happen through the
  API, because the shell validates first. If it did, it would stay a logged 500.
- Any other database error stays a logged 500.

## 7. API (`/api/equipment/…`)

| Method and path | Permission |
|---|---|
| `GET /` | `equipment:read` |
| `GET /<id>` | `equipment:read` |
| `POST /` | `equipment:edit` |
| `PUT /<id>` | `equipment:edit` |

**`GET /`: the list**
- Returns `{items, total, page, per_page}`, ordered by code.
- Paging:
  - `page` ≥ 1, default 1;
  - `per_page` 1–200, default 50;
  - other values → 400 with `field`;
  - a page past the end returns `items: []` with the true `total`.
- Filters:
  - `site_id`, `unit_id`, `class_id`;
  - `status`, `criticality`;
  - `level`, one of `equipment` / `component_unit` / `component` / `all`, default
    `equipment`;
  - `q`: `LIKE %q%` on code and name, with `%` and `_` escaped, trimmed, empty
    ignored;
  - `include_scrapped`.
- Unknown enum values → 400.
- **Row fields:**
  - `id`, `code`, `level`, `name`;
  - `class_id`, `class_code`;
  - `unit_id` and `unit` (the unit's full code), both for the root;
  - `full_path`, `effective_criticality`, `status`;
  - `part_count`: the direct children that aren't scrapped.

**`GET /<id>`: one node**
- All fields, `full_path`, `effective_criticality`.
- `ancestors`: `[{id, code, level, name}]`, from the root down.
- `children`: the subtree, two levels at most, **including scrapped** nodes. Each
  carries `status`.
- `events`: newest first.

**`POST /`: create**
- Any level. Equipment needs `unit_id`; parts need `parent_id`.
- Returns 201 with the node, as `GET /<id>` returns it.

**`PUT /<id>`: change**
- Fields; `class_id`; `criticality`; `status`; `unit_id` (equipment) or
  `parent_id` (parts).
- Returns 200 with the node.

**Paging.** Pagination is a return to the base pattern, unlike S001's small lists,
because about 500 pieces of equipment plus their parts are too many for one
response.

There's no DELETE; equipment is scrapped instead.

## 8. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Four statuses; "down" derived from breakdowns | User decision; EN 13306 separates condition from use | Typing "under repair" by hand |
| Fixed three levels; components may sit under equipment | User decision; ISO 14224 levels applied where meaningful | Free-depth tree |
| Only equipment has a unit; one SQL fragment resolves a part's unit | User decision; one place for a security rule | A unit on every node; the resolution repeated per route |
| Criticality required on equipment (default C); parts inherit | User decision | Optional while loading |
| An event history log with full-path text snapshots | User decision; ISO 55001 § 8.2 / ISO 14224; snapshots survive renames | Last change only; storing ids; event sourcing |
| The code never changes, even on reclassification | Plan § 4.1 | Re-issuing the code on a class change |
| The counter is in the create transaction; no gaps from failures | Atomic; base pattern (BR1-01) | Bumping in a separate autocommit statement |
| One global lock order: node → parent → unit → class → counter; single-row locks; locks before decisions | No races on prefix, scrap or deactivation; no join locks (BR1-02, BR2-01, BR2-02) | Class first; locking through the join; checks before locks |
| A generic `serial_counters` table | Reused for `BD-` and `PM-`; base pattern | A counter column on `equipment_classes` |
| `equipment:read_all_units` is a **scope** key | RBAC: no role names in routes. It is a deliberate departure from the read_basic / read / read_senior naming, because it says *where*, not *how much* | Checking `maint_manager` in code |
| 404 for a node outside the user's units; 403 for an inaccessible target | Doesn't reveal nodes; units are public anyway | 403 everywhere |
| Shared `api_common.py` (errors, `actor`, `clean_body`) and generic SQL helpers in `db_helpers.py` | DRY: two blueprints (BR1-09, BR3-03) | Copying them into `equipment.py`; per-blueprint handlers |
| Scrapping a node with live parts → 409 | Explicit; nothing scrapped by accident | Scrapping the subtree automatically |
| Scrapped equipment still freezes unit and class codes | It still carries the prefix and appears in history | Counting only live equipment |
| A CHECK constraint for the level/place rule | The database guards the tree shape too | Enforced by the shell only |
| The screens split into S003 (user, 14-10-2026) | README "one reviewable slice"; S002 is reviewable through its API tests (BR1-04) | One large step |

## 9. Tests and acceptance

### Pure (`test_equipment_core.py`)

- `format_equipment_code`: 1 → `VBM001`, 999 → `VBM999`, 1000 → `VBM1000`,
  10000 → `VBM10000`.
- `check_parent`: the full level × parent-level table.
- `effective_criticality`.
- `full_path` at each depth.
- `tracked_changes`:
  - each tracked field;
  - untracked fields;
  - no change;
  - criticality `inherit` → `A`.
- `check_status_change`: the full table, including into and out of scrapped, and
  scrapped on create.
- Validation:
  - year bounds, with `this_year` passed in;
  - required fields per level;
  - the enums;
  - `criticality: null` on equipment vs on a part.

### API (`test_equipment_api.py`)

- **Codes:**
  - each level created; codes are per prefix and relative (`n`, `n+1`);
  - two classes have independent counters;
  - a create refused by validation (400) or a rule (409) uses **no** number: the
    next successful create gets the next one.
- **Tree:**
  - wrong parent level → 400;
  - a unit on a part, or no unit on equipment → 400;
  - the CHECK constraint holds when the shell is bypassed in a direct SQL test. It
    raises pymysql `OperationalError` 4025, not `IntegrityError`.
- **Reclassify:** the code is unchanged and a `class` event is written. To an
  inactive class → 409, field `class_id`.
- **Move equipment to another unit:** one `moved_unit` event with full paths; the
  parts' `full_path` follows. To an inactive unit → 409.
- **Re-parent:**
  - a component, and a component-unit together with its components;
  - a cross-unit re-parent gives one `moved_parent` event;
  - into a scrapped parent → 409.
- **Status:**
  - every allowed change;
  - scrapped on create → 400;
  - scrapping with live parts → 409;
  - any PUT on a scrapped node → 409;
  - scrapping plus a name change in one PUT applies both.
- **Events:**
  - one per changed tracked field;
  - none for an untracked edit;
  - none when a part's effective grade changes through its equipment;
  - a forced rollback leaves none. The test wraps the event-writer helper so
    that it calls through, then raises. Events are written *after* the UPDATE,
    so patching the UPDATE would prove nothing (BR2-05);
  - the order is newest first.
- **Unit access:**
  - an engineer sees only their units, in the list and the detail;
  - a node elsewhere → 404, and a 400-worthy body on such a node still gives 404;
  - a POST or move to a target they can't access → 403 with `field`;
  - a filter on an inaccessible unit → an empty page;
  - the manager, IT admin and admin see everything;
  - a user with no rows → an empty list, using a fresh username;
  - every other unit-access case also uses its own fresh username.
- **Unknown ids and immutable fields:**
  - unknown `unit_id`, `parent_id` or `class_id` → 400 with that field;
  - `code` or `level` changed in a PUT → 400; unchanged → accepted;
  - a 400-worthy body on a node the user can't see → 404.
- **Criticality:** a component under a component-unit that has its own grade
  inherits the **equipment's** grade; the `criticality` filter uses the effective
  grade.
- **Paging and filters:**
  - the `page` and `per_page` bounds;
  - each filter, including `level=all`;
  - `q` with `%` or `_`;
  - scrapped hidden by default;
  - the `part_count` definition.
- **S001 rules, extended (`test_masters_api.py`):**
  - a unit with equipment (even scrapped) can't change its code or site;
  - a class with equipment (even scrapped) can't change its code;
  - a unit holding equipment that isn't scrapped can't be deactivated.
- **Errors:** `TestErrorMapping` still passes after the move to `api_common.py` (monkeypatch target renamed).
- **RBAC:** the operator and technician can read and get 403 on writes; the
  engineer, manager and IT admin can write.

### Acceptance

- `tooling/run-tests.bat` is green.
- Through the API, as an engineer, the firewood mill can be loaded:
  - `VBM001`, with its drive (a component-unit) and the drive's motor and gearbox;
  - two breakers, each with a motor.
- One breaker's motor can be moved to the other breaker, and the event shows both
  full paths.

## 10. Open questions and assumptions

1. **Decided (user, 14-10-2026) — split (BR1-04).** S002 is the backend; the
   screens become S003.
2. **Decided (user, 14-10-2026) — unit deactivation.** Laid-up (`out_of_use`)
   equipment **blocks** deactivating its unit: it must be moved or scrapped
   first. A laid-up machine still physically stands in that unit.
3. **Decided (user, 14-10-2026) — bulk import.** Not needed now; equipment is
   entered through the screens. It can become its own step later if wanted.
4. **Assumption:** every node, parts included, needs a class, because Plan § 4.1
   builds every code from its class prefix. Component-units such as "drive"
   therefore need classes, e.g. `DRV`.
5. **Assumption:** a deactivated class still counts as "in use" for the frozen
   rule. Deactivating it doesn't free its code.
6. **Deferred:** a `remark` on events (reason for scrapping, ISO 55001 § 8.2). It
   is one migration whenever it is wanted.

## Appendix — Handover to S003 (screens)

Kept from the first draft and from round 1, so S003 starts from them:

- **Navigation and landing:**
  - A new nav item **Equipment** (`/equipment`, perm `equipment:read`) before
    Masters.
  - `frontend/src/router/index.js` gets the routes `/equipment` (name
    `equipment`) and `/equipment/:id`. The detail route is outside the nav, so
    `canOpenRoute` lets it through and the API's 404 does the gating.
  - Today `/` is a fixed `redirect: "/masters"` (BR1-05). It becomes
    `redirect: () => landingPath(...) ?? "/equipment"`, so the landing rule lives
    in one place.
  - Three tests in `navigation.test.js` change: "maint_operator sees Masters
    only", "manager and IT admin see Masters and Settings", and "everyone with a
    role lands on Masters".
- **`EquipmentView.vue`:**
  - filters: site/unit, class, status, criticality, level, and search; typing a
    search switches `level` to `all`;
  - a filter change resets to page 1, and the total is shown;
  - "Add equipment" shows with `equipment:edit`.
- **`EquipmentDetailView.vue`:**
  - the path;
  - the fields, with "inherited" criticality marked;
  - the parts tree, scrapped nodes greyed;
  - the history;
  - Edit / Add part / Move / Change status.
- **Modals:**
  - `useMasterForm.js` is generalised into `composables/useFormModal.js`, with
    the after-save hook as a parameter. `changeActive` stays in a masters wrapper,
    and the masters panels change only their import (BR1-12).
  - The create/edit, move and status modals are instances of it.
  - The Scrapped confirmation reuses `ActiveToggle.vue`'s inline Yes/No shape,
    not a browser `confirm()`.
- The default site (S001 A1) preselects the unit picker's site.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 14-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 Counter rule contradicts itself | major | **Accepted, option (a).** Counter in the transaction; no gaps from failures; read-back on the same connection; the deadlock on a brand-new prefix accepted and stated; test replaced. |
| BR1-02 Locking unspecified | major | **Accepted.** New § 6 Locking: create and update order, prefix read after the class lock, scrap check under the node lock, no-cycle argument; comment required in `equipment.py`. |
| BR1-03 A part's unit not defined in one place | major | **Accepted.** One SQL fragment plus two helpers; POST target rule; check order; filters intersect access; `level=all`. |
| BR1-04 Step too large | major | **Accepted provisionally, option (a)**: screens split to S003; the design is kept in the appendix. **For the user to confirm** (§ 10.1). |
| BR1-05 `router/index.js`; `/` redirect claim wrong | minor | **Accepted**, moved to the S003 handover (redirect via `landingPath`, routes, the three breaking tests). |
| BR1-06 Event snapshot forms | minor | **Accepted.** Full paths for both move events; one `moved_parent` on a cross-unit re-parent; `inherit`; no event on an inherited grade change; display-value signature; order `created_at DESC, id DESC`; "history log, not event-sourced" stated. |
| BR1-07 Status gaps | minor | **Accepted.** Status on POST (not scrapped); move into a scrapped parent → 409; any PUT on a scrapped node → 409; scrap plus other fields together; inactive class/unit targets → 409 with fields; messages given; `criticality: null` rules. |
| BR1-08 Pagination and filters | minor | **Accepted.** Bounds; LIKE escaping; unknown enums → 400; `part_count` defined; `unit_id` / `class_id` in rows; scrapped children carry status. |
| BR1-09 Shape of `api_errors.py` | minor | **Accepted.** App-level `register_error_handlers(app)` plus a dict registry; `TestErrorMapping` as the regression tests; the `uq_equipment_code` message. |
| BR1-10 Frozen and activation precision | minor | **Accepted.** Scrapped equipment counts as a reference; counts rely on § 6 Locking; shared `make_equipment` fixture. The out_of_use-blocks-deactivation consequence goes **to the user** (§ 10.2). |
| BR1-11 Standards | minor | **Accepted.** EN 13306 states corrected; ISO 14224 wording softened; ISO 55001 § 6.1 / § 6.2.2 / § 8.2; NORSOK Z-008 named and scoped; TPM equipment ranking; ISO 27001 A.5.15 / A.8.3; ISO 55000 stages phrasing. |
| BR1-12 `useMasterForm.js` reuse | minor | **Accepted**, in the S003 handover: generalise into `composables/useFormModal.js`. |
| BR1-13 RBAC points | minor | **Accepted.** Scope key recorded as a departure in § 8; key order; the breaking tests named. |
| BR1-14 Data-model nits | nit | **Accepted.** The CHECK constraint is added; FKs named. **Deferred:** the event `remark` (§ 10.6). |
| BR1-15 Plan / Philosophy updates owed | nit | **Accepted.** Listed in § 4 Docs, done at approval. |
| BR1-16 Tests | nit | **Accepted.** Truncate order including `serial_counters`; relative code assertions; how to force the rollback; `zfill(3)`. Navigation tests moved to S003. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 14-10-2026

The reviewer verified that every round-1 finding is in the brief text. Two new
majors came from the round-1 locking text.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 The lock order deadlocks | major | **Accepted.** One global order: node → target parent → unit → class → counter. Single-row `FOR UPDATE`, never through the join; ancestors read plainly. The `masters.py` interaction restated accurately (it locks unit → site; equipment never locks sites or `user_units`). The one remaining reverse-order case (the scrap subtree check against a concurrent re-parent inside the same machine) is **accepted** as a rare 500, in line with the user's S001 CR2-01 decision. |
| BR2-02 A plain subtree read after the lock is wrong under REPEATABLE READ | major | **Accepted.** "Locks first, then decisions"; the scrap check is a locking read of the subtree; masters' safety explained by `_lock_row` being the first statement. |
| BR2-03 Fragment incomplete; criticality inheritance order | minor | **Accepted.** Joins to `units` and `sites`; `root_criticality` as a `CASE` (the equipment's grade, never the component-unit's); the filter is on the effective grade; the fragment is for plain reads only. |
| BR2-04 Self-referencing FK breaks the truncate | minor | **Accepted.** `SET FOREIGN_KEY_CHECKS=0` on the truncate connection. |
| BR2-05 Test feasibility | minor | **Accepted.** The rollback test wraps the event writer; a CHECK violation is `OperationalError` 4025; fresh usernames through `role_client(role, username=…)`. |
| BR2-06 Unknown ids; `code` / `level` in a PUT; validation order | minor | **Accepted.** 400 with field; unchanged accepted, changed → 400; body validated after the node load. |
| BR2-07 The brand-new-prefix deadlock can't occur; wrong cross-reference | nit | **Accepted.** Replaced: the class lock serialises creates per prefix. |
| BR2-08 ISO 55001 edition | nit | **Accepted.** "2014 numbering" stated. |
| BR2-09 Scrapped equipment in a deactivated unit is hidden | nit | **Accepted.** The consequence is stated and accepted (§ 6). |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 14-10-2026

This is the last round under the 3-round limit. BR3-01 (major) is answered below
but **not re-reviewed**. That goes to the user at gate A.

| Finding | Severity | Response |
|---|---|---|
| BR3-01 Decisions must come from the locking read itself | major | **Accepted.** Each locking `SELECT` returns its decision columns (equipment `id, level, status, parent_id, unit_id, class_id`; units `id, active`; classes `id, code, active`). Refusals are decided only from those rows; the fragment is for access and display only; `_accessible_unit_ids` runs after the node lock. The missing BR2-01 consequence sentence is added (access revoked during a lock wait: the write still completes). |
| BR3-02 Loading a target parent | minor | **Accepted.** A third helper, `_load_target_node(cur, id, field)`, with the order 400 (missing) → 403 (outside the user's units) → 409 (scrapped) → 400 (level rule). |
| BR3-03 Shared shell helpers | minor | **Accepted.** `api_errors.py` becomes `api_common.py` (errors, `actor`, `clean_body`); `insert_row`, `update_row`, `count` and `fetch_one` move to `db_helpers.py`; the `TestErrorMapping` monkeypatch target is renamed. |
| BR3-04 Small corrections in § 6 | nit | **Accepted.** CASE-vs-COALESCE reason corrected (it exposes rather than masks a NULL); `create_unit` locks only the site; the grandchildren read is skipped when there are no children; `role_client(…, username)` uses an `X-Test-User` test header. |

### Gate A — user decisions, 14-10-2026

- **Approved** without a fourth brief-review round. BR3-01's fix (decisions from
  the locking reads) is to be verified at code review against the real code.
- **Split confirmed:** S002 backend, S003 screens.
- **`out_of_use` equipment blocks** deactivating its unit.
- **Bulk import:** not needed now.
