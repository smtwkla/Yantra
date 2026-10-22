```
Step: S016 — Failure codes
Doc: brief
Author: Planner (Opus)
Date: 18-10-2026 (revised 18-10-2026 after brief-review r1)
Track: full
Baseline: 90284ec (stale brief check 20-10-2026: no file of this brief changed since a2190f3)
Status: Done (committed 6c771e1; checks: 3 auto) (approved 20-10-2026 by KLA)
```

# S016 — Failure codes

Phase 3 (tickets: breakdowns and defects) needs three pick-lists before a ticket
can be raised or closed (Plan.MD § 4.2 *Codes*, decided 15-10-2026; open
question 5):

- **failure mode** — what is seen; the operator picks it as the **symptom** when
  raising a ticket (S017);
- **failure cause** — why it failed; the technician or engineer picks it when
  the work is done (S018);
- **maintenance action** — what was done; picked with the cause (S018).

The lists are trimmed from ISO 14224 Annex B and maintained by engineers.
Failure modes are **scoped by equipment class**, brought forward for the press
class (Plan.MD § 4.2, 16-10-2026): a press operator sees "not building pressure",
"slow return", "safety door not sensed" next to the symptoms every machine can
have (noise, leak, overheating).

This step builds the three masters only. Nothing uses them yet: S017 (raise a
ticket) and S018 (work and close it) do.

User decisions (18-10-2026, before the brief):
1. The migration **pre-fills** the lists from ISO 14224 Annex B; engineers trim
   them and add the plant's own (§ 4.3).
2. **English labels only** for now; a second-language label can be added later
   as a column without changing the design.

**Track: full** — a migration with seed rows and a new permission key.
**Depends on:** nothing uncommitted (baseline a2190f3). Migration **v11**.

## 1. What will be built

1. **Masters › Failure codes** — a new Masters section with a switch between
   three lists: **Modes**, **Causes**, **Actions**. Everyone who can read masters
   sees them; engineers, managers and IT admin add and edit.
2. **Failure modes (symptoms).** Each has a **code** (e.g. `NOI`, `NBP`), a
   **label** in plain words for the operator ("Abnormal noise", "Not building
   pressure"), an optional **description** (help text, e.g. the ISO name or what
   to look for), and either **one equipment class** or **General** (shown for
   every class). A filter shows *All*, *General*, or one class. A mode's class is
   fixed once created, like an equipment type's.
3. **Failure causes.** Code, label, optional description, and an **ISO cause
   group** — one of ISO 14224's five: *design*, *fabrication / installation*,
   *operation / maintenance*, *management*, *miscellaneous*. The plant's own
   causes ("oil contamination", "dust in panel") are added under a group, so
   reports can roll them up the ISO way.
4. **Maintenance actions.** Code, label, optional description.
5. **Active / inactive** on every row, as on other masters: an inactive code is
   not offered for new tickets, and stays on old ones.
6. **Pre-filled lists** (migration v11): 14 general failure modes, 15 causes
   and 12 actions from ISO 14224 Annex B (§ 4.3). Press-class modes are entered
   by engineers in the screen (§ 4.4), because the press class's code is not
   known to a migration.
7. **The list endpoint for modes takes a class:** `class_id=N` returns that
   class's modes plus the general ones — the list S017's "raise ticket" screen
   will show for equipment of class N.

**Out of scope:**
- tickets, and any use of the codes (S017, S018);
- "code frozen once in use" — nothing references a code yet; S017 and S018 add
  the check when tickets start pointing at them (§ 5.4);
- failure **mechanism** (ISO 14224 B.2) — left out of v1 (Plan.MD Q5); see
  § 9 Q2;
- modes scoped by equipment **type** or by tree level (component vs equipment);
- causes or actions scoped by class;
- a second-language label (user decision 2);
- a manual sort order (§ 9 Q1);
- diagnostic procedures per symptom (Plan.MD § 4.3a, later).

## 2. Standards and practice

- **ISO 14224 (reliability and maintenance data), § 9 and Annex B.** A failure
  record carries, among others, the **failure mode** (the observed effect —
  "the way the failure is seen"), the **failure cause** (the circumstances
  during design, manufacture or use that led to the failure), the **failure
  mechanism** (the physical process: wear, corrosion, short circuit) and the
  **maintenance activity** (what was done). Annex B gives code lists for each:
  - **Failure modes** are listed **per equipment class** (Tables B.6–B.15: a
    pump's modes differ from a compressor's), with three-letter codes reused
    across classes where they mean the same thing (`NOI` noise, `VIB`
    vibration, `OHE` overheating, `FTS` fail to start). Yantra follows this:
    a mode belongs to a class, and the common ones are **General**. The codes
    of the pre-filled modes are ISO's; their labels are plain words an
    operator understands, with the ISO name in the description.
  - **Failure causes** (Table B.3) are in five groups (design; fabrication /
    installation; operation / maintenance; management; miscellaneous), each
    with a few causes numbered `1.1`, `3.4`, … Yantra seeds those numbers as
    the codes and keeps the group as a field, so local causes added later
    still roll up to ISO's groups. The point of the groups, in plain terms:
    they show whether failures come from how the machine was made, how it is
    run and maintained, or how the work is organised — each calls for a
    different fix.
  - **Maintenance activities** (Table B.5) — replace, repair, modify, adjust,
    refit, check, service, test, inspection, overhaul, combination, other —
    seeded with ISO's numbers as codes.
  - ISO 14224 expects lists to be **trimmed** to what the user needs; a list
    nobody understands produces "other" everywhere. Engineers deactivate what
    the plant doesn't use (`Maintenance-Philosophy.md` § 2: we adopt ISO's
    structure, not its oil-and-gas lists).
- **Cause vs mechanism.** Technicians often name the mechanism as the cause
  ("worn", "contaminated", "short circuit"). ISO keeps them apart: *worn* is the
  mechanism, *expected wear and tear* or *maintenance error* (filter not
  changed) is the cause. Mechanism is not in v1, so a local cause like "oil
  contamination" is allowed under the *operation / maintenance* group; this is a
  deliberate, pragmatic blur, to revisit when mechanism is added (§ 9 Q2).
- **EN 13306 (maintenance terminology)** uses the same three ideas: *failure
  mode*, *failure cause*, and the maintenance *action* / *task*. The screen and
  the tables use these standard names; the operator-facing word is "symptom".
- **TPM — focused improvement.** Chronic losses are found by counting tickets
  per component and failure mode (Plan.MD § 4.6, chronic problems). That works
  only if the operator's symptom list is short and specific to the machine —
  hence class-scoped modes for the presses first.
- **SMRP** downtime and MTBF reports by cause (Plan.MD § 4.6) need a coded
  cause on every closed breakdown; this step provides the list.
- **ISO 55001 § 7.5 and § 9.1** (asset management: decide the asset information
  you need and keep it; evaluate performance from it). Coded failures are that
  information: without a fixed list, the failure history can be read but not
  counted (BR1-15).

## 3. Where

### Backend
- **`backend/local_db.py`** — migration **v11** "Failure modes, causes,
  maintenance actions": three new tables (§ 4.1) and the seed rows (§ 4.3), each
  statement safe to run twice (as in v5).
- **`backend/config_rbac.py`** — new key **`failure_codes:edit`**:
  `("maint_engineer", "it_admin")` (managers inherit it). Global, **not** in
  `SITE_SCOPED`: the lists are site-less masters, like equipment classes.
- **`backend/masters_core.py`** (pure) — `FAILURE_CODE_RE`, `CAUSE_GROUPS`,
  `FAILURE_LABEL_MAX`, `FAILURE_DESCRIPTION_MAX`; validators
  `validate_failure_mode`, `validate_failure_cause`,
  `validate_maintenance_action` on the existing `_validate` pattern.
  `CAUSE_GROUPS` mirrors the ENUM, as `EMPLOYMENT` does for `people.employment`.
- **`backend/masters.py`** — list / create / update routes for the three lists
  (§ 6), on the equipment-types pattern (class fixed after create; class must be
  active at create and at reactivation, `_lock_active_parent`). The five unique
  indexes of § 4.1 are registered in `UNIQUE_KEY_ERRORS` with plain messages
  (field `code` or `label`), so a duplicate gives `409 {error, field}` (BR1-06).

### Frontend
- **`frontend/src/views/MastersView.vue`** — new section `failure_codes`
  ("Failure codes", `perm: "masters:read"`), after *Models*.
- **`frontend/src/views/masters/FailureCodesPanel.vue`** (new) — the
  Modes / Causes / Actions switch, holding the three panels below.
- **`frontend/src/views/masters/FailureModesPanel.vue`**,
  **`FailureCausesPanel.vue`**, **`MaintenanceActionsPanel.vue`** (new) — list,
  filter (modes: class; causes: group), Show inactive, add / edit with
  `FormModal` + `useMasterForm`, `ActiveToggle`; editing only with
  `failure_codes:edit`.
- **`frontend/src/stores/masters.js`** — `failureModes`, `failureCauses`,
  `maintenanceActions` refs and `ensureX()` functions; cleared by
  `resetMasters()` like the others.

### Tests
- `backend/tests/test_masters_core.py` — the three validators.
- `backend/tests/test_failure_codes_api.py` (new) — the routes (§ 8).
- `backend/tests/test_migration_v11.py` (new) — tables, seeds, re-run.
- `backend/tests/test_rbac.py` — the new key; `TestComputePermissions.test_role_matrix`
  asserts each role's exact set, so the `maint_engineer`, `maint_manager` and
  `it_admin` rows gain `failure_codes:edit` (not a looser assertion; BR1-04).
- `backend/tests/conftest.py` — session clean-up and `Uniq.failure_code()` (§ 8
  *Test isolation*).
- `frontend/tests/masters.test.js` — the new store lists, if the existing tests
  cover the store's lists that way.

### Docs (at approval, by the planner)
- `docs/Plan.MD` § 3 (the key), § 4.2 *Codes* (scoping and cause groups),
  § 5 (the three tables replace the `codes` row).
- `docs/Maintenance-Philosophy.md` glossary: failure mode, failure cause,
  maintenance action, cause group.

## 4. Data model (migration v11)

### 4.1 New tables

Three tables, not one `codes` table with a `kind` column (§ 7 decision 1).
All three have the usual audit columns (`created_at`, `created_by`,
`updated_at`, `updated_by`), InnoDB, utf8mb4 (case-insensitive collation, as
the other masters).

**`failure_modes`**

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `code` | VARCHAR(8) NOT NULL | UNIQUE `uq_failure_modes_code` |
| `label` | VARCHAR(60) NOT NULL | what the operator reads |
| `description` | VARCHAR(255) NULL | help text |
| `class_id` | INT NULL | FK `equipment_classes`; NULL = General |
| `active` | TINYINT(1) NOT NULL DEFAULT 1 | |

Index `ix_failure_modes_class (class_id, active)` for the picker query.

**`failure_causes`**

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `code` | VARCHAR(8) NOT NULL | UNIQUE `uq_failure_causes_code` |
| `label` | VARCHAR(60) NOT NULL | UNIQUE `uq_failure_causes_label` |
| `description` | VARCHAR(255) NULL | |
| `cause_group` | ENUM('design','fabrication','operation','management','misc') NOT NULL | ISO 14224 Table B.3 groups 1–5 |
| `active` | TINYINT(1) NOT NULL DEFAULT 1 | |

**`maintenance_actions`**

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `code` | VARCHAR(8) NOT NULL | UNIQUE `uq_maintenance_actions_code` |
| `label` | VARCHAR(60) NOT NULL | UNIQUE `uq_maintenance_actions_label` |
| `description` | VARCHAR(255) NULL | |
| `active` | TINYINT(1) NOT NULL DEFAULT 1 | |

`created_by` of seed rows is `migration-v11` (the v8 precedent, BR1-09); tests
and later code tell seed rows apart by it.

### 4.2 No change to existing tables

### 4.3 Seed rows

`INSERT IGNORE` keyed on the unique code, so a re-run keeps an engineer's edit
of a seed row (label, active). The text is frozen in the migration.

**General failure modes** (`class_id` NULL). Code from ISO 14224 Annex B;
label in plain words; description = the ISO name.

| Code | Label | Description (ISO name) |
|---|---|---|
| `BRD` | Stopped, won't run | Breakdown |
| `FTS` | Won't start | Fail to start on demand |
| `STP` | Won't stop | Fail to stop on demand |
| `UST` | Stops by itself | Spurious stop |
| `ELU` | Leaking (oil, water, air) | External leakage (ISO `ELU` utility medium / `ELP` process medium; one entry here) |
| `NOI` | Abnormal noise | Noise |
| `VIB` | Vibration | Vibration |
| `OHE` | Overheating | Overheating |
| `LOO` | Low output or slow | Low output |
| `ERO` | Erratic, behaves oddly | Erratic output |
| `PDE` | Reading out of range | Parameter deviation |
| `STD` | Broken, cracked or worn part | Structural deficiency |
| `SER` | Loose, dirty or minor problem | Minor in-service problems |
| `OTH` | Other | Other |

**Failure causes** (ISO 14224 Table B.3, trimmed). The "x.0 general" rows and
5.2 *common cause* (a reliability-analysis term) are left out.

| Code | Group | Label |
|---|---|---|
| `1.1` | design | Improper capacity |
| `1.2` | design | Improper material |
| `2.1` | fabrication | Fabrication error |
| `2.2` | fabrication | Installation error |
| `3.1` | operation | Off-design service |
| `3.2` | operation | Operating error |
| `3.3` | operation | Maintenance error |
| `3.4` | operation | Expected wear and tear |
| `4.1` | management | Documentation error |
| `4.2` | management | Management error |
| `5.1` | misc | No cause found |
| `5.3` | misc | Combined causes |
| `5.4` | misc | Caused by another failure |
| `5.5` | misc | Other |
| `5.6` | misc | Unknown |

*Caused by another failure* is ISO's "other unit / cascading failure", in plain
words. *No cause found* is the likely code for S018's frivolous close ("no
fault found"); S018 decides.

**Maintenance actions** (ISO 14224 Table B.5, all twelve):

| Code | Label | Description |
|---|---|---|
| `1` | Replace | Replace with a new or reconditioned item of the same type and make |
| `2` | Repair | Manual repair work to restore the item |
| `3` | Modify | Replace, renew or change to a different design or material |
| `4` | Adjust | Bring a value back within limits (e.g. valve zero/span) |
| `5` | Refit | Small repair or tidy-up short of a full repair: re-tighten, touch up, clean a seat |
| `6` | Check | Looked for the cause; nothing repaired, or the fix was a restart or reset, or the work is deferred |
| `7` | Service | Periodic service: cleaning, lubrication, filter change |
| `8` | Test | Test the function or performance |
| `9` | Inspection | Careful look at the item, with or without opening it, by eye, ear and hand |
| `10` | Overhaul | Major overhaul |
| `11` | Combination | Several of the above |
| `12` | Other | Other action |

The coder and the brief reviewer check the codes and names above against
ISO 14224:2016 Annex B as far as they can; a correction is a review finding,
not a silent change.

### 4.4 Press modes (entered in the screen, not seeded)

Proposed for the pilot (Plan.MD § 4.2, `Plant-Facts.md` § 4, pressing shop), for
an engineer to enter under the press class during the manual checks:

| Suggested code | Label |
|---|---|
| `NBP` | Not building pressure |
| `NHP` | Not holding pressure (in ISO terms an internal leakage, `INL`) |
| `SRT` | Slow return |
| `DNS` | Safety door not sensed |
| `OSO` | Output stuck on |
| `ACF` | Auto cycle fails |

## 5. Rules

### 5.1 Codes and labels
- **Code:** trimmed, upper-cased, 1–8 characters: letters and digits in parts
  joined by single dots (`^[A-Z0-9]+(\.[A-Z0-9]+)*$` plus the length check), so
  ISO's `3.4` and `NOI` fit and a typo like `3.` or `1..2` is refused (BR1-10).
  Unique within its list (database).
- **Label:** trimmed, inner spaces collapsed (as manufacturer names, S012),
  1–60 characters (fits a phone line). Causes and actions: unique within the
  list (database, case-insensitive by collation).
- **Mode labels** are unique within what one picker shows: a class mode's label
  may not equal another mode's of the same class or a general one; a general
  mode's label may not equal any mode's. Checked by the API (409, field
  `label`), inactive rows included, so a reactivation can't bring a duplicate
  back. The query compares with a plain `=` on `label`, so the column's
  case-insensitive collation applies (no `LOWER()`; BR1-11). Not a database
  rule: the scope crosses the NULL class. Two engineers
  saving the same label at the same moment could both pass; that is accepted —
  the codes differ, nothing breaks, and one is renamed.
- **Description:** optional, trimmed, up to 255; empty becomes NULL.

### 5.2 Mode class
- Optional on create (absent or `null` = General); the class must exist and be
  **active** (locked, `_lock_active_parent`).
- **Fixed after create** (400 if a PUT sends a different `class_id`), like an
  equipment type: a mode created under the wrong class is deactivated and made
  again. Reason: once tickets use it, moving it would re-label history.
  So a class mode can't be turned into a General one: rename or deactivate the
  class mode first (its label would collide, inactive rows included), then
  create the General one (BR1-11).
- **Reactivating** a mode of an inactive class is refused (409), as for types.
- **Deactivating a class** needs no check on its modes: equipment of an
  inactive class still exists and still raises tickets, so its modes stay
  offered for it.

### 5.3 Cause group
- Required on create; one of the five values; may be changed later, also once
  tickets reference the cause (§ 5.4).

### 5.4 Editing now vs later
- Everything but a mode's class can be edited in this step: code, label,
  description, group, active.
- **S017 and S018 must add** "code frozen once in use" (Plan.MD § 4.1, the rule
  for every master code): when a ticket references a row, its code can no
  longer change. The label may still be corrected. This is written here so the
  later briefs pick it up.
- A cause's **group stays editable** once in use: it is a reclassification,
  and applying it to all history is what the ISO roll-up wants (one cause never
  rolls up two ways). S018 must not freeze it by analogy with the code (BR1-12).
- **S017 checks the mode's class in the API**, on the locked ticket: the mode
  must be General or of the class of the ticket's **equipment** (the level-6
  node, even when the ticket is on a component). Not a composite foreign key
  as in S004/S012: General modes have `class_id NULL`, which a composite key
  can never match (BR1-03).

### 5.5 Who
- Read: `masters:read` (everyone).
- Create, edit, activate / deactivate: `failure_codes:edit` — engineers (and so
  managers) at any of their sites, and IT admin. Global key: the lists are the
  same at every site.

## 6. API

All under `/api/masters`, on the existing masters error format.

| Method | Path | Perm | Notes |
|---|---|---|---|
| GET | `/failure-modes` | `masters:read` | `include_inactive=1`; `class_id=N` → modes of class N **plus** general, ordered by label; without it all modes, ordered general first, then class code, then label. Each row has `class_code` (NULL for general) |
| POST | `/failure-modes` | `failure_codes:edit` | `code`, `label`, `description?`, `class_id?` → 201 |
| PUT | `/failure-modes/<id>` | `failure_codes:edit` | `code`, `label`, `description`, `active`; `class_id` only if unchanged |
| GET | `/failure-causes` | `masters:read` | `include_inactive=1`; ordered `cause_group, code` — the ENUM sorts in its declared order (design … misc), so local causes stay in their group (BR1-07) |
| POST | `/failure-causes` | `failure_codes:edit` | `code`, `label`, `cause_group`, `description?` |
| PUT | `/failure-causes/<id>` | `failure_codes:edit` | any of those, `active` |
| GET | `/maintenance-actions` | `masters:read` | `include_inactive=1`; ordered `CHAR_LENGTH(code), code`, so ISO's `1`…`12` come in number order |
| POST | `/maintenance-actions` | `failure_codes:edit` | `code`, `label`, `description?` |
| PUT | `/maintenance-actions/<id>` | `failure_codes:edit` | any of those, `active` |

Duplicate code → 409 `code`; duplicate label → 409 `label`; unknown id → 404.


## 7. Design decisions

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| 1 | **Three tables** (`failure_modes`, `failure_causes`, `maintenance_actions`) | Each has its own field (mode: class; cause: group); S017/S018's ticket columns get a plain foreign key that also guarantees the kind (a cause column can only hold a cause) — the database-rule approach of S004/S012 | One `codes` table with `kind` (Plan.MD § 5 sketch): fewer routes, but a ticket's `cause_id` could point at an action; guarding that needs app checks or a composite key trick |
| 2 | **Mode: one class or General** (nullable `class_id`) | ISO lists modes per class; most symptoms are common, so General avoids repeating "Noise" under every class. The picker shows class + general | Many-to-many mode ↔ classes (more tables, more UI, for little gain); modes not scoped (Plan.MD's original v1 — the press pilot needs scoping) |
| 3 | **Codes kept, ISO codes for seeds** | ISO 14224 uses codes for data exchange; the shared ticket API (later) and reports need a stable key that survives a label fix; the user learns the ISO terms | Label only (one less field for engineers; but a relabel would look like a new symptom to anything outside Yantra) |
| 4 | **Cause group as a field** | Keeps ISO's roll-up while the plant adds its own specific causes | Only ISO's fixed causes (too coarse for the press pilot: "oil contamination" matters); free causes with no group (no roll-up) |
| 5 | **New key `failure_codes:edit`** (engineer, IT admin) | A new master gets its own `module:action` key (RBAC pattern); today's grantees match `equipment:edit`, but they can diverge (e.g. only the manager) without touching equipment | Reuse `equipment:edit` (no RBAC change; ties codes to equipment editing for good) |
| 6 | **Seed by migration** (user decision 1) | Lists ready on day one; engineers trim | Empty lists |
| 7 | **Press modes typed in the UI**, not seeded | The press class's code exists only in each database; a migration can't rely on it | A migration that looks up a class by code (fragile across dev / prod) |
| 8 | **Mode labels checked by the API**, races accepted | The rule (a class mode vs. its class and General) can't be a unique index at all: a generated `IFNULL(class_id, 0)` key would stop two General "Noise" rows, but not a General "Noise" beside a press "Noise" (BR1-14). A handful of engineers edit this list | A persistent generated column `IFNULL(class_id, 0)` with a unique index (insufficient) |
| 9 | **One Masters section with a three-way switch** | Masters already has 8 sections; three more crowd the toolbar on a phone | Three Masters sections |

## 8. Tests and acceptance

### Pure (`test_masters_core.py`)
- Code: upper-cased and trimmed; `3.4`, `NOI`, `12` accepted; empty, 9 chars,
  a leading dot, an inner space or another character (`-`, `/`) fail.
- Label: required, collapsed spaces, 60 max. Description: optional, empty →
  None, 255 max.
- Cause group: required on create, one of five; mode `class_id` optional / null.

### API (`test_failure_codes_api.py`)
- Engineer creates, edits, deactivates and reactivates a row in each list;
  IT admin too; operator and technician get 403 on POST / PUT; everyone reads.
- Mode: `class_id=N` returns class N's modes plus general, not other classes';
  `include_inactive` works; class fixed after create (400); inactive class at
  create and at reactivation (409); unknown class → 400 `Unknown class`
  (BR1-08).
- Mode labels: same label in the same class → 409; class label equal to a
  general one → 409; general label equal to any class mode → 409; same label
  in two different classes → allowed.
- Duplicate code → 409 in each list; duplicate cause / action label → 409.

### Migration (`test_migration_v11.py`)
- The three tables and their five named unique keys exist; seed rows
  (`created_by = 'migration-v11'`) count 14 / 15 / 12.
- Re-run (delete `db_version` 11, `init_db` twice) changes nothing and keeps an
  edited seed row's label and active flag; the row is restored in `finally`
  (as `test_migration_v10.py` restores its setting).

### Test isolation (BR1-05)
- The three tables are **not** added to `conftest._TABLES` (that would wipe
  the seeds). Instead the session clean-up deletes their **non-seed** rows
  (`created_by <> 'migration-v11'`), so a second run starts clean.
- `Uniq.failure_code()` gives codes that fit the code rule (e.g. `T0001`).
- Seed assertions count only `created_by = 'migration-v11'` rows.

### RBAC (`test_rbac.py`)
- `failure_codes:edit` granted to engineer, manager (inherited), IT admin; not
  to operator, technician, supervisor, storekeeper; not site-scoped.
- `test_role_matrix` rows for engineer, manager and IT admin updated (BR1-04).

### Manual checks
Important:
- [ ] As an engineer, open Masters › Failure codes: the pre-filled modes,
  causes and actions are there; enter the press modes of § 4.4 under the press
  class; filter by the press class shows them; *General* shows the 14 general
  ones.
- [ ] As an operator, the section is read-only (no Add, no edit, no toggle).
- [ ] On a phone, the switch and the lists are usable (no sideways scroll).

Also:
- Deactivate a seed mode; it disappears unless *Show inactive*; reactivate it.
- Try to add a press mode labelled "Abnormal noise": refused, it is already a
  general mode.

### Acceptance
- `tooling/run-tests.bat` green, the frontend build clean.

## 9. Open questions and assumptions

1. **Order in the picker** — alphabetical by label for now; "Other" then sits
   among the O's. A manual sort order (most common first, Other last) can come
   with S017 when the raise screen is built, if the operators need it.
   *Assumption: alphabetical is fine for the masters screen.*
2. **Failure mechanism** (ISO 14224 B.2: wear, fatigue, contamination, short
   circuit, …) — out of v1 (Plan.MD Q5). If chronic-problem reports show
   technicians writing mechanisms into causes, add mechanism as a fourth list
   later. Proposed to note in Plan.MD as a later item.
3. **Should IT admin edit failure codes?** Proposed yes (masters housekeeping,
   like classes). The alternative is engineers and managers only — the codes
   are maintenance knowledge.
4. **Seed labels** — the plain-word labels of § 4.3 are proposals; change any at
   gate A or later in the screen.
5. *Assumption:* modes are scoped by the class of the ticket's **equipment**
   node (level 6), even when the ticket is on a component: the operator does
   not know the component (§ 5.4). S017 confirms.

## 10. Amendments

(none)

## Gate A — 20-10-2026 (KLA)

Approved as it stands after review r1. Answers: § 9 Q3 — **IT admin edits
failure codes too** (`failure_codes:edit` = engineer, IT admin, as proposed);
§ 9 Q4 — **seed labels as proposed** in § 4.3. Not to be built yet: coding
waits for `/step implement S016` (the stale brief check runs then).

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 18-10-2026

0 blocker, 0 major, 7 minor, 8 nit. All accepted.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted — § 4.3 descriptions of `1` Replace, `5` Refit, `6` Check, `9` Inspection now say what Table B.5 says |
| BR1-02 minor | Accepted — `SER` *Loose, dirty or minor problem* added (14 general modes); `STD` narrowed to broken, cracked or worn |
| BR1-03 minor | Accepted — § 5.4: S017 checks the mode's class in the API, against the ticket's equipment (level 6); not a composite FK. Assumption 5 sharpened |
| BR1-04 minor | Accepted — § 3 and § 8 name `test_role_matrix` and its three rows |
| BR1-05 minor | Accepted — § 8 *Test isolation*: non-seed rows deleted per session, `Uniq.failure_code()`, seed counts filtered, re-run test restores the row |
| BR1-06 minor | Accepted — five unique indexes named (§ 4.1), registered in `UNIQUE_KEY_ERRORS` (§ 3) |
| BR1-07 minor | Accepted — causes ordered `cause_group, code` (§ 6) |
| BR1-08 nit | Accepted — unknown class is 400 |
| BR1-09 nit | Accepted — seeds `created_by = 'migration-v11'` |
| BR1-10 nit | Accepted — stricter code rule, dots only between parts |
| BR1-11 nit | Accepted — plain `=` on `label` (§ 5.1); class → General path (§ 5.2) |
| BR1-12 nit | Accepted — cause group stays editable once in use (§ 5.3, § 5.4) |
| BR1-13 nit | Accepted — `ELU` description names the ELU/ELP merge; `NHP` points at ISO `INL` |
| BR1-14 nit | Accepted — decision 8's reason: a unique index can't express the rule |
| BR1-15 nit | Accepted — ISO 55001 § 7.5 / § 9.1 line in § 2 |
