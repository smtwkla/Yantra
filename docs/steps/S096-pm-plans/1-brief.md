```
Step: S096 — PM plans on a machine
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 01-11-2026
Track: full
Baseline: refs/steps/S095 (a4ee0a0; c9cd091 + S095), stale-brief check by the orchestrator 01-11-2026: S095 adds `backend/pm_schedule_core.py` (KINDS, CALENDAR_UNITS as briefed) and renames `contracts_core.add_months`; nothing else in § 3 changed
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1: 1 minor, 3 nits, CR1-01…CR1-04, fixed in fix round 1; verify review r2: 1 nit, CR2-01, fixed by the orchestrator in S097's snapshot; no device check); approved 01-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 7 minor, 7 nits, all accepted; the decisions of § 9 flagged for KLA at gate B)
From: R03.2
```

# S096 — PM plans on a machine

## 1. What will be built

R03.2 of `docs/roadmap/R03-pm.md`. **An engineer writes a PM plan on any node of the equipment
tree, by hand**: what to do (its items), when (by calendar, by meter, or whichever comes first), who
does it (maintenance or the operator, and a default assignee from Team), and whether an engineer
verifies each job. The plans show on a **PM card** on the equipment page, each with its trigger in
words ("Every month or 250 h, whichever comes first"). No job is made yet: jobs come with R03.3.

1. **The record** (migration **v51**, § 4): `pm_plans` (one row per plan, on one node) and
   `pm_plan_items` (its items, in order). A plan is never deleted; *Deactivate* stops it, and a
   stopped plan makes no jobs (R03.3 reads `active`). An item removed from a plan is set inactive,
   never deleted (§ 5.4).
2. **Items** (Q2.1 a, Plan § 4.3 *Item types*): *Task* (done / not done), *Check* (OK / Not OK /
   NA), *Reading* (a value with a unit and optional Min / Max). A reading may name a **meter of the
   node or of a node above it** (Plan § 4.3 *Which meter a plan uses*); it then takes the meter's
   unit, and R03.4 writes its value as a meter reading. Every item has optional **help text** and a
   **photo setting**: none / optional / required (enforced from R03.6).
3. **Triggers** (S095's vocabulary, § 5.2): `trigger_kind` is `calendar`, `meter`, `both` or
   `before_use` (S095 `pm_schedule_core.KINDS`). Calendar: every N days, weeks, months or years.
   Meter: every N units of one **counter** meter of the node or a node above it. *Last done* seed:
   the date and the meter value of the last time the work was done before Yantra. The column allows
   `before_use` now, so R03.13 needs no migration; S096's API does not accept it yet (D6).
4. **Performer** `maintenance` or `operator`; **default assignee** (maintenance plans only): a
   person who holds a Technician, Engineer or Manager role at the node's site
   (`config_rbac.ASSIGNABLE_ROLES`), contractors of a vendor included. **Needs verification** per
   plan (Q5.1 a): default yes for maintenance, no for operator.
5. **The PM card** on the equipment page (§ 5.8): the node's plans and its parts' plans, each with
   its title, its trigger in words and one small line (items, who does it). *Add PM plan* for
   editors; *Inactive plans (n)* behind a link.
6. **The plan page** (§ 5.9, mock-up `docs/roadmap/R03-mockups/01-pm-plan.html`): a page, not a
   dialog, at `/equipment/<id>/pm/new` and `/equipment/pm/<plan id>`. Two cards (*Plan*, *When is
   it due?*) and the *Items* card; *Add item* opens the **item dialog** (`FormModal.vue`); *Save
   plan* saves the plan and all its items in one request. Readers without the key see the same
   page read-only.
7. **One new key** `pm_plan:edit`: the engineer (so the manager); not IT admin (Q2.2 a); in
   `config_rbac.SITE_SCOPED`, checked at the node's site. Plans are **read with
   `equipment:read`** (D3).

**After S096:** the engineers enter the pilot's plans (Q0.2 a: the hydraulic presses) while R03.3
is coded.

### Out of scope

- Jobs, the daily run, the next-due line and *Upcoming* (R03.3); S096 never calls S095's core
  functions, it imports only its constants (D7 of S095).
- Doing a job, readings written by a job (R03.4); verification (R03.5); photos on job items and the
  photo setting enforced (R03.6); alerts (R03.7).
- Templates and *Apply to equipment* (R03.8); CIL groups *Clean / Inspect / Lubricate* (R03.12);
  *Start CIL* and before-use plans on the screen (R03.13); reference photos (R03.17).
- A trigger "when a gauge reading crosses a limit" (Plan § 4.3, *Meter* trigger, second half): a
  reading item's limits flag the value on the job (R03.4) and a ticket follows (R03.10); no plan
  is triggered by a gauge.
- A history of earlier values of a plan or its items (only who created and who last changed, § 5.4).
- Drag and drop to order items (D9).

## 2. Standards and practice

- **TPM — planned maintenance pillar.** In plain words: the maintenance team decides in advance what
  work each machine needs and when, does it, and learns from the results; breakdowns fall as
  planned work rises. S096 is the "decides in advance" part: a written plan per machine, with its
  items and its interval. Plant-Facts § 6: there is no PM schedule to migrate today.
- **EN 13306 — maintenance terms** (term numbers *to verify*). In plain words: a *maintenance task*
  is work done (grease, change, clean); an *inspection* is a check for conformity, with no repair;
  *predetermined* maintenance runs at set intervals of time or use, without looking at condition
  first; *condition-based* maintenance acts on a measurement. S096 follows it: *Task* is work done,
  *Check* is inspection, *Reading* is a measurement with limits (the condition part); a calendar or
  meter trigger is predetermined.
- **ISO 55001 § 7.5, information requirements** (2014 edition; the clause in the 2024 edition *to
  verify*). In plain words: decide what information you need about your assets and keep it. A plan
  is that information for planned work: what, when, by whom, and which meter counts.
- **ISO 9001:2015 § 7.5.3, control of documented information.** In plain words: records are kept,
  protected from loss and change, and show who did what and when. A plan and an item are never
  deleted (inactive instead), and each row keeps who created it and who changed it last.
  **Departure (recorded):** no history of earlier values, as every master and the contracts
  (S080 § 2); a started job keeps its own copy of the items (R03.4), so a later plan change never
  rewrites what a job recorded.
- **ISO 14224** (clause *to verify*). In plain words: record maintenance against the item it was
  done on, and run hours at the level where they differ. A plan sits on one node at any level, and
  its meter may be the node's own or one above it (a gearbox plan counts the extruder's run hours;
  an alternating pump with its own hour meter counts its own).
- **ISO/IEC 27001:2022 A.5.15, access control.** In plain words: each person may do only what the
  work needs, and the system enforces it. Writing plans is the engineer's and the manager's at their
  site; IT admin reads only (Q2.2 a, as for improvements and lessons).

## 3. Where

S095 (R03.1, the scheduling core) is coded before S096 and creates `backend/pm_schedule_core.py`
with the constants `CALENDAR`, `METER`, `BOTH`, `BEFORE_USE`, `KINDS`, `DAY`, `WEEK`, `MONTH`,
`YEAR`, `CALENDAR_UNITS` (`docs/steps/S095-pm-schedule-core/1-brief.md` § 5.1, D7). These names do
not exist at the baseline; S096 imports them and nothing else from that module. S095 adds no
migration, so v51 is S096's.

### Backend

- `backend/local_db.py`: migration **v51** at the end of `_MIGRATIONS`, after v50 (§ 4.1). No
  `_PRECONDITIONS` entry (two new tables; no existing row changes).
- `backend/pm_plans_core.py` (new, pure): the bounds and messages, `validate_plan(body, creating)`,
  `validate_item(body, choices)`, `validate_items(raw, choices)`, `trigger_kind_of(calendar_on,
  meter_on)`, `plan_rules_error(merged, meter_type, today)` (BR1-02), `meter_choice_error(choices,
  equipment_id, meter_type_id, kinds)`, `default_verification(performer)`, `interval_number(value,
  decimals)` (BR1-03), `trigger_text(plan, meter_type)`, `meter_label(code, meter_type)`,
  `item_limits_text(item, meter_type)`, `sync_items(stored, sent)` (§ 5). Imports: the constants
  above from `pm_schedule_core`; `collapsed`, `flag_parser`, `optional_text_parser`,
  `validate_fields` from `backend/masters_core.py` (S080 D9's public names, `masters_core.py:379`);
  `parse_number`, `format_number`, `grouped_number`, `MIN_ABOVE_MAX`, `NO_LIMITS_FOR_KIND`,
  `BELOW_ZERO`, `COUNTER`, `GAUGE` from `backend/meters_core.py`; `iso_date` from
  `backend/contracts_core.py` (below).
- `backend/contracts_core.py`: one line beside `_iso_date`, `iso_date = _iso_date`, the public name
  another core imports (the `masters_core.py:379` pattern; BR1-06), so no third copy of the parser
  is made. S095 renames `_add_months` to `add_months` in the same file: anchor by name, not line.
- `backend/pm_plans.py` (new): the blueprint `pm_plans_bp` (§ 6), the LOCK ORDER note (§ 5.7), the
  answer builders `_plan_out`, `_summary_out`. Imports: `has_perm_at`, `require_perm`,
  `require_perm_at` (`backend/auth_utils.py`); `ApiError`, `UNIQUE_KEY_ERRORS`, `actor`,
  `clean_body`, `int_arg` (`backend/api_common.py`); `get_db`, `insert_row`, `update_row`, `marks`,
  `row_to_dict`, `transaction` (`backend/db_helpers.py`); `IST`, `SCRAPPED_MESSAGE`,
  `load_node_for_user`, `node_path` (`backend/equipment.py`); `SCRAPPED` (`backend/equipment_core.py`);
  `meters_with_last` (new, below); `person_at_site`, `ASSIGNEE_AT_SITE` (`backend/tickets.py:371`,
  `backend/tickets.py:141`); `ASSIGNABLE_ROLES` (`backend/config_rbac.py:64`).
- `backend/meters.py`: one new public function `meters_with_last(cur, nodes)` → `{node_id: [meter,
  …]}`: each node's meters in force (`effective_meters`) with `last`, in a few queries for all
  nodes (`read_models_meters`, `_nodes_rows`, `_last_readings`, `_add_last`), exactly what
  `readings_sheet`'s inner `meters_of` does today (`backend/meters.py:489`). `readings_sheet` then
  calls it (one copy of the rule, CLAUDE-COMMON *DRY*); no change of behaviour.
- `backend/app.py`: `app.register_blueprint(pm_plans_bp, url_prefix="/api/pm")`, after the
  `contracts_bp` line (`backend/app.py:201`).
- `backend/config_rbac.py`: `"pm_plan:edit": ("maint_engineer",)` after the contract keys, with a
  comment (§ 5.6); the key joins `SITE_SCOPED`.
- `backend/equipment.py`: docstring only. The LOCK ORDER note gains a `pm_plans.py` bullet (§ 5.7).

### Tests

- `backend/tests/test_migration_v51.py` (new; § 8.1), helpers from `backend/tests/migration_helpers.py`
  (`_recreate`, `_migrate`, `_run`, `_schema`) as `test_migration_v50.py` uses them.
- `backend/tests/test_migration_v50.py`: `V50 = [m for m in local_db._MIGRATIONS if m[0] <= 50]`
  (as `SQUASHED` filters in `backend/tests/migration_helpers.py`), so the file tests v50 alone again;
  its `_versions() == [41, 50]` asserts stay (BR1-01).
- `backend/tests/test_migration_squash_v41.py`: `CURRENT` stays the whole list; its versions assert
  becomes `_versions() == [*range(20, 42), *[m[0] for m in CURRENT if m[0] > 41]]`, so production's
  v41 is still shown to reach the latest version and no later migration edits it again (BR1-01).
- `backend/tests/test_pm_plans_core.py` (new; § 8.2), written and green before the shell.
- `backend/tests/test_pm_plans_api.py` (new; § 8.2).
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and a new `test_pm_plan_keys` (§ 8.3).
- `backend/tests/conftest.py`: `pm_plan_items` and `pm_plans` join `_TABLES`, first in the tuple
  (`backend/tests/conftest.py:186`).

### Frontend

- `frontend/src/views/PmPlanView.vue` (new): the plan page (§ 5.9).
- `frontend/src/views/equipment/PmItemDialog.vue` (new): the item dialog (§ 5.10).
- `frontend/src/views/equipment/PmPlansCard.vue` (new): the PM card (§ 5.8).
- `frontend/src/views/EquipmentDetailView.vue`: the card after *Open tickets* (§ 5.8).
- `frontend/src/router/index.js`: two routes, `pm-plan-new` and `pm-plan` (§ 5.9). A shared file
  (settings: *Shared code*): the whole browser suite runs again at the end, as it does anyway.
- `frontend/src/utils/pmLabels.js` (new, pure): `ITEM_TYPES`, `PHOTO_SETTINGS`, `PERFORMERS`,
  `CALENDAR_UNITS` (value and plural label), `kindFromTicks(calendarOn, meterOn)`,
  `planBody(form, items)`, `itemBody(form)`, `moveItem(items, index, step)`.
- `frontend/tests/pmLabels.test.js` (new).
- `frontend/e2e/pm-plans.spec.js` (new; § 8.4). Its set-up helpers live in the spec file, not in
  `frontend/e2e/support/`, so the shared support files stay unchanged.
- `frontend/e2e/screens.spec.js`: two screens (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: a new area *Preventive maintenance* (note: "PM plans and their items
  (S096); jobs, templates and routes come with R03."); `pm_plans` and `pm_plan_items` move from
  `planned` to `tables` with their lines. The new `pm_plans` line drops the planned line's *kind
  (PM / CIL)* (a CIL plan is a plan whose performer is the operator, Plan § 4.4) and *source
  template* (R03.8's migration adds it), so R03.8 and R03.12 know (BR1-09). Then
  `tooling\schema-docs.bat write`, read
  `git diff docs/schema/`, and `check` exits 0. `docs/schema/schema.json` and
  `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 4.3: a *Built (S096)* paragraph under *PM plan*; the per-plan "Photo required"
  line is superseded (it already says "supersedes the three lines above once built"); calendar
  units gain *years* (a small departure from "every N days / weeks / months", D8). § 3: one
  paragraph for `pm_plan:edit` (who, site-scoped, read with `equipment:read`), as for
  `procedure:edit`.
- `.claude/CLAUDE.md`: § Step workflow, *Self-check, repo items* (2): `pm_plans.py` joins the list
  of LOCK ORDER notes; § SMTW-Review gains the point of § 8.6.
- `docs/Keycloak.md`: no change (no Keycloak role changes).

**File count:** 24 code and test files (backend 8: `local_db.py`, `pm_plans_core.py`, `pm_plans.py`,
`meters.py`, `contracts_core.py`, `app.py`, `config_rbac.py`, `equipment.py`; backend tests 7, two
of them the migration tests of BR1-01; frontend 9:
`PmPlanView.vue`, `PmItemDialog.vue`, `PmPlansCard.vue`, `EquipmentDetailView.vue`,
`router/index.js`, `pmLabels.js`, its test, `pm-plans.spec.js`, `screens.spec.js`), and 5 docs. A
record and its lines are one concern (the roadmap's size note); two screens (the card, the page)
and one dialog. No split (§ 9).

## 4. Data model

### 4.1 Migration v51

```sql
-- PM plans (S096, R03.2): the planned work on one node of the equipment tree, written by an
-- engineer.  trigger_kind takes pm_schedule_core.KINDS (S095); the calendar columns are set exactly
-- for calendar and both, the meter columns exactly for meter and both, none for before_use (R03.13).
-- The meter is a counter of the node or of a node above it (meter_equipment_id names which).
-- last_done_on / last_done_meter: the engineer's seed, when the work was last done before Yantra.
-- Never deleted: a plan entered by mistake or no longer wanted is set inactive (ISO 9001 § 7.5.3).
CREATE TABLE IF NOT EXISTS pm_plans (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id        INT NOT NULL,
    title               VARCHAR(100) NOT NULL,
    performer           ENUM('maintenance','operator') NOT NULL DEFAULT 'maintenance',
    assignee_id         INT NULL,
    needs_verification  TINYINT(1) NOT NULL DEFAULT 1,
    trigger_kind        ENUM('calendar','meter','both','before_use') NOT NULL,
    calendar_every      SMALLINT NULL,
    calendar_unit       ENUM('day','week','month','year') NULL,
    meter_equipment_id  INT NULL,
    meter_type_id       INT NULL,
    meter_every         DECIMAL(14,3) NULL,
    last_done_on        DATE NULL,
    last_done_meter     DECIMAL(14,3) NULL,
    active              TINYINT(1) NOT NULL DEFAULT 1,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          VARCHAR(100) NOT NULL,
    updated_at          DATETIME NULL,
    updated_by          VARCHAR(100) NULL,
    CONSTRAINT uq_pm_plans_title UNIQUE (equipment_id, title),
    CONSTRAINT fk_pm_plans_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_pm_plans_assignee FOREIGN KEY (assignee_id) REFERENCES people (id),
    CONSTRAINT fk_pm_plans_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_pm_plans_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    CONSTRAINT chk_pm_plans_calendar CHECK (
        (calendar_every IS NOT NULL) = (trigger_kind IN ('calendar','both'))
        AND (calendar_unit IS NOT NULL) = (calendar_every IS NOT NULL)
        AND (calendar_every IS NULL OR calendar_every BETWEEN 1 AND 3650)),
    CONSTRAINT chk_pm_plans_meter CHECK (
        (meter_type_id IS NOT NULL) = (trigger_kind IN ('meter','both'))
        AND (meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL)
        AND (meter_every IS NOT NULL) = (meter_type_id IS NOT NULL)
        AND (meter_every IS NULL OR meter_every > 0)),
    CONSTRAINT chk_pm_plans_seed CHECK (
        (last_done_meter IS NULL OR (meter_type_id IS NOT NULL AND last_done_meter >= 0))
        AND (last_done_on IS NULL OR trigger_kind <> 'before_use')),
    CONSTRAINT chk_pm_plans_assignee CHECK (assignee_id IS NULL OR performer = 'maintenance')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The items of a plan, in order (position 1..n over the active items).  A reading may name a
-- meter (meter_equipment_id + meter_type_id): it then takes the meter's unit (unit NULL), and R03.4
-- logs its value as a meter reading.  Removed items are set inactive, never deleted, so R03.4's
-- results and R03.17's reference photos can name an item for ever.
CREATE TABLE IF NOT EXISTS pm_plan_items (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    plan_id             INT NOT NULL,
    position            SMALLINT NOT NULL,
    item_type           ENUM('task','check','reading') NOT NULL,
    text                VARCHAR(200) NOT NULL,
    help_text           VARCHAR(500) NULL,
    photo               ENUM('none','optional','required') NOT NULL DEFAULT 'optional',
    unit                VARCHAR(20) NULL,
    min_value           DECIMAL(14,3) NULL,
    max_value           DECIMAL(14,3) NULL,
    meter_equipment_id  INT NULL,
    meter_type_id       INT NULL,
    active              TINYINT(1) NOT NULL DEFAULT 1,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          VARCHAR(100) NOT NULL,
    updated_at          DATETIME NULL,
    updated_by          VARCHAR(100) NULL,
    INDEX ix_pm_plan_items_plan (plan_id, active, position),
    CONSTRAINT fk_pm_plan_items_plan FOREIGN KEY (plan_id) REFERENCES pm_plans (id),
    CONSTRAINT fk_pm_plan_items_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_pm_plan_items_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    CONSTRAINT chk_pm_plan_items_position CHECK (position >= 1),
    CONSTRAINT chk_pm_plan_items_reading CHECK (item_type = 'reading'
        OR (unit IS NULL AND min_value IS NULL AND max_value IS NULL AND meter_type_id IS NULL)),
    CONSTRAINT chk_pm_plan_items_meter CHECK ((meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL)
        AND (meter_type_id IS NULL OR unit IS NULL)),
    CONSTRAINT chk_pm_plan_items_limits CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **The ENUMs equal S095's constants.** `trigger_kind` lists `pm_schedule_core.KINDS` and
  `calendar_unit` `CALENDAR_UNITS`, in their order; a test in `test_migration_v51.py` reads the
  column types from `information_schema` and compares (§ 8.1), so the two cannot drift (S095 D7).
  The core's plan mapping names the key `trigger_kind` too (S095 § 5.1, its BR1-01), so R03.3's
  shell passes the row as it is (extra keys are ignored).
- **`chk_pm_plans_calendar` 1–3650:** the database's outer bound; the per-unit bounds (at most 10
  years, § 5.1) are the API's.
- **`uq_pm_plans_title`:** one title per node, inactive plans included. It also stops a double tap
  on *Save plan* from making two plans (a create takes no counter lock). The collation is
  case-insensitive, so "Monthly check" and "monthly check" clash. 409 "This machine already has a
  plan with this title, active or inactive. Choose another title, or reactivate that plan."
  (`title`, through `UNIQUE_KEY_ERRORS`).
- **No unique key on `position`:** inactive items keep their last position; the API writes 1..n
  over the active items on every save (§ 5.4).
- **Foreign keys:** no `ON DELETE`, so `RESTRICT`, as every foreign key in the schema. MariaDB makes
  the index behind each foreign key that has none.
- **Text:** utf8mb4; `VARCHAR(n)` and Python's `len` both count code points (S075 § 4.1).
- **Re-run safety:** `CREATE TABLE IF NOT EXISTS`, two statements; a run stopped between them
  completes on the next start.
- **No precondition:** new tables only. Rollback: release v0.1.15 (v50) never reads them.

### 4.2 What is computed, never stored

- `trigger_text`, `meter_label`, an item's `limits_text`, `item_count`, `can_edit`, `can_add`.
- The meter's name, unit, kind and decimals (from `meter_types`), the meter node's code, the node's
  path and site, the assignee's name (joins).

## 5. Rules

### 5.1 The plan fields

**Two phases** (BR1-02). (1) `validate_plan(body, creating)` for `clean_body`
(`backend/api_common.py:121`), before any read: the per-field rules of the table, with
`meter_every` and `last_done_meter` parsed at the column's 3 decimals (`parse_number(raw, 3)`) and
`last_done_on` as a date from 2000-01-01 (`iso_date`). (2) After the shell's reads (§ 5.7),
`plan_rules_error(merged, meter_type, today) → (field, message) | None` on the stored row merged
with the clean body: the trigger rules below (null-ness by `trigger_kind`), the per-unit maximum
on the merged `calendar_every` / `calendar_unit`, the meter type's decimals on `meter_every` and
`last_done_meter` (the same `parse_number` texts), `meter_every` > 0, and `last_done_on` ≤ `today`
(the IST date, passed in by the shell). On a `POST` a required field missing is refused; on a
`PUT` an absent field stays as it is. Unknown fields are ignored. **Message style** (S080 BR1-01): a missing or empty field says what to do, as a sentence
with a period ("Enter a title."); a too long or wrong-type value uses the masters parsers' form,
without a period ("Title must be at most 100 characters").

| Field | `POST` | Rule | Message (field) |
|---|---|---|---|
| `equipment_id` | required | integer ≥ 1, not a boolean | "Choose the equipment." (`equipment_id`) |
| `title` | required | text; `collapsed`; 1–100 | "Enter a title." / "Title must be at most 100 characters" / "Title must be text" |
| `performer` | optional, default `maintenance` | `maintenance` or `operator` | "Choose who does the jobs." (`performer`) |
| `assignee_id` | optional | integer ≥ 1 or `null` | "Choose a person from the list." (`assignee_id`); the site rule § 5.3 |
| `needs_verification` | optional, default `default_verification(performer)` | `flag_parser("Verification")` | "Verification must be true or false" |
| `trigger_kind` | required | one of `KINDS`; `before_use` refused in S096 (D6) | "Tick By calendar or By meter, or both." (`trigger_kind`, also when missing); `before_use`: "Before-use plans are not available yet. Choose a calendar or meter interval." |
| `calendar_every` | for `calendar`, `both` | integer, not a boolean, ≥ 1; the unit's maximum (day 3650, week 520, month 120, year 10, `CALENDAR_MAX`) in `plan_rules_error` | "Enter a whole number from 1 to 120." (the number is the chosen unit's maximum; `calendar_every`) |
| `calendar_unit` | for `calendar`, `both` | one of `CALENDAR_UNITS` | "Choose days, weeks, months or years." (`calendar_unit`) |
| `meter_equipment_id`, `meter_type_id` | for `meter`, `both` | integers ≥ 1; the pair must be a **counter** among the meter choices (§ 5.5) | "Choose a meter from the list." (`meter_type_id`); a gauge: "Choose a counter meter, such as run hours." |
| `meter_every` | for `meter`, `both` | `parse_number(raw, 3)`; the type's decimals and > 0 in `plan_rules_error` | `parse_number`'s texts ("Enter a whole number", "Enter a number with up to 1 decimal", "Enter a smaller number"); ≤ 0: "Enter a number above 0." (`meter_every`) |
| `last_done_on` | optional | `null` or `YYYY-MM-DD` (`iso_date`), from 2000-01-01; ≤ today in `plan_rules_error` | "Enter a date from 01-01-2000 to today." (`last_done_on`) |
| `last_done_meter` | optional | `null`, or `parse_number(raw, 3)` ≥ 0; the type's decimals in `plan_rules_error` | `parse_number`'s texts; below 0: "A counter cannot be below zero" (`BELOW_ZERO[COUNTER]`); `last_done_meter` |
| `active` | ignored on `POST` | `flag_parser("Active")` | "Active must be true or false" |
| `items` | required | a list; § 5.4 | "Add at least one item." (`items`) |

- **The trigger on merged values** (in `plan_rules_error`, over the stored row on a `PUT`): for
  `calendar` the meter fields must be `null`, for `meter` the calendar fields, and so on, as the
  CHECKs. The screen sends every field, and sends `null` for an unticked trigger, so this only
  meets a hand-made request: "Clear the meter fields for a calendar plan." / "Clear the calendar
  fields for a meter plan." (on the first field that breaks it). `last_done_meter` without a meter:
  "Tick By meter to enter the meter value." (`last_done_meter`).
- **`last_done_meter` is not compared with the meter's latest reading** (A3): a seed above the
  latest reading is saved (the engineer may know better than a stale reading).
- **`equipment_id` is fixed after create.** On a `PUT`, equal to the stored one is no change; a
  different one: 400 "A plan stays on its equipment. Deactivate it and add a plan on the other
  one." (`equipment_id`), as S080's site rule.
- **`performer` change:** to `operator` with an assignee (sent or stored, merged): 400 "Operator
  plans have no assignee. Choose No one yet." (`assignee_id`). The page clears the assignee when
  the performer becomes *Operator*, so only a hand-made request meets it.
- **`needs_verification` on a `PUT`** is written only when sent; a performer change does not
  change it (the page offers the new performer's default, § 5.9).
- A `PUT` writes every field it was sent (`update_row`, `backend/db_helpers.py:68`) and stamps
  `updated_at`, `updated_by`; a field equal to the stored one is left out, and a `PUT` that changes
  nothing writes nothing.

### 5.2 Triggers in words (`trigger_text`)

`trigger_text(plan, meter_type)`, pure. Numbers go through `interval_number(value, decimals)`
(BR1-03): the places the value really has (`len(format_number(value).partition(".")[2])`, at most
the type's decimals), then `grouped_number(value, places)`, so "250" on the 1-decimal *Run hours*
reads "250", "0.5" reads "0.5" and "5000" reads "5,000" (`grouped_number` alone would give
"250.0"):

| `trigger_kind` | Text |
|---|---|
| `calendar` | "Every day" / "Every 3 days", "Every week" / "Every 2 weeks", "Every month" / "Every 6 months", "Every year" / "Every 2 years" |
| `meter` | "Every 250 h", "Every 5,000 h", "Every 10,000 strokes" (the type's unit) |
| `both` | "Every month or 250 h, whichever comes first" |
| `before_use` | "Before each use" (never written by S096's API; the text is ready for R03.13) |

`meter_label(code, meter_type)`: "Run hours · HP003" (the meter's name, then the code of the node
that carries it). The card shows it under the trigger text when the plan has a meter.

### 5.3 The assignee

- **Who:** `tickets.person_at_site(cur, person_id, site_id)` at the node's current site, plain;
  `None` or a role not in `ASSIGNABLE_ROLES` → 400 `ASSIGNEE_AT_SITE` ("Choose a technician,
  engineer or manager at this site", `assignee_id`). A contractor linked to a vendor (S079) holds a
  Technician row and qualifies, so an AMC vendor can be a plan's assignee (Plan § 4.3).
- **Checked whenever it is sent**, equal to the stored one or not (D10). A person who left the site
  therefore blocks the save until the engineer picks another person or *No one yet*; the page shows
  that before the save (§ 5.9).
- **`null`** is *No one yet*: allowed for every plan.
- A person deactivated, or a machine moved to another site, after the save keeps the stored id;
  R03.3 decides what a job does with such an assignee (§ 9 A4).

### 5.4 The items

`validate_items(raw, choices)` → the clean list, or the first error as `("items", "Item 3: <the
item's message>")`. `raw` must be a list ("Items must be a list", `items`), of 1 to `MAX_ITEMS`
(50) entries ("Add at least one item." / "A plan holds at most 50 items."). An entry that is not an
object: "Item 3: Reload the page." Each entry is checked by `validate_item(body, choices)` (also
the item-check route's, § 6; there a body that is not an object is `clean_body`'s 400):

| Field | Rule | Message (field) |
|---|---|---|
| `id` | absent or `null` for a new item; an integer ≥ 1 for an existing one (§ sync) | — (sync, below) |
| `item_type` | required: `task`, `check` or `reading` | "Choose Task, Check or Reading." (`item_type`) |
| `text` | required; text; `collapsed`; 1–200 | "Enter what to do or check." / "Item must be at most 200 characters" / "Item must be text" (`text`) |
| `help_text` | optional; `optional_text_parser("Help text", 500)` (trimmed, line breaks kept; empty → `null`) | "Help text must be at most 500 characters" / "Help text must be text" |
| `photo` | optional, default `optional`; `none`, `optional`, `required` | "Choose a photo setting." (`photo`) |
| `unit` | reading without a meter: optional, `optional_text_parser("Unit", 20, collapse=True)` | "Unit must be at most 20 characters" / "Unit must be text" |
| `meter_equipment_id`, `meter_type_id` | reading only; both or neither; the pair a **counter or gauge** among the choices (§ 5.5) | "Choose a meter from the list." (`meter_type_id`) |
| `min_value`, `max_value` | reading only; `parse_number(raw, decimals)`: decimals 3 without a meter, the type's with one; none for a counter meter; min ≤ max | `parse_number`'s texts; "A counter has no limits" (`NO_LIMITS_FOR_KIND`, `min_value`); "Min must not be above Max" (`MIN_ABOVE_MAX`, `max_value`) |

- **Task or Check with a unit, a limit or a meter** (any of the five not `null`): "Only a reading
  has a unit, limits or a meter." (the first such field). The dialog sends `null` for the hidden
  fields, so this only meets a hand-made request.
- **A reading with a meter and a unit** not `null`: "A reading that logs a meter uses the meter's
  unit. Clear Unit." (`unit`). The dialog hides *Unit* once a meter is chosen.
- **Limits may be negative** (a temperature); `parse_number` accepts a sign. `LIMIT_MAX` bounds
  both (`backend/meters_core.py:43`).
- **The answer's `limits_text`** (`item_limits_text`): "30–60 °C", "up to 60 °C", "from 30 °C", or
  `null`; for an item with a meter, then " · logs Oil temperature · HP003". The unit is the meter
  type's, or the item's (it may be empty: then the numbers alone). Min and Max go through
  `interval_number` with an en dash, so a 1-decimal gauge reads "30–60 °C", not "30.0–60.0 °C"
  (BR1-03; `meters_core._range` is private and is not imported).

**Sync** (`sync_items(stored, sent)`, pure, on a `PUT` with `items`): `stored` are the plan's
active items (locked plan, § 5.7), `sent` the clean list in its new order.

- A sent item with an `id` that is not among `stored` (another plan's, an inactive one, unknown):
  400 "Item 3 was removed or changed by someone else. Reload the page." (`items`).
- The same `id` twice: 400 "Item 3 appears twice. Reload the page." (`items`).
- A sent item with an `id`: an update of the fields that differ, and of `position` when it moved.
- A sent item without an `id`: an insert at its position.
- A stored item not sent: `active = 0` (removed). Its position stays as it was.
- Positions are 1..n in the sent order. Result: `{"insert": [...], "update": [(id, changes)],
  "deactivate": [ids]}`; the shell runs `insert_row` / `update_row` for each. An item update stamps
  the item's `updated_*`; the plan row is stamped only when its own fields change.
- **No job exists yet**, so any item may change (R03.4 copies the items into the job at *Start*,
  roadmap R03.4); R03.4 and R03.17 can name an item for ever because a removed item stays a row.

### 5.5 The meter choices

`meters_with_last(cur, nodes)` over the node and the nodes above it: its parent and its
grandparent (`node["parent_id"]`, `node["gp_id"]`, the `_NODE_COLUMNS` of `backend/equipment.py:208`;
the tree has three levels, Plan § 4.1). Each ancestor is read with `load_node_for_user(cur, id,
for_update=False)` (`backend/equipment.py:399`): every node of a path is in the root's unit, so
access is the same as the node's (`backend/meters.py:588`, `_ticket_path`'s note).

- A **choice** is `{equipment_id, code, name, level, meter_type: {id, name, unit, kind, decimals},
  min_value, max_value, last: {value, taken_at} | null, label}` for every meter **in force**
  (`effective_meters`, `backend/meters_core.py:223`) of kind `counter` or `gauge`, the node first,
  then its parent, then its grandparent; each node's meters in `effective_meters`' order. Amount
  and Yes / No meters are left out: a reading item of a Yes / No meter is a *Check*, and an amount
  per period is not a job's value.
- `meter_choice_error(choices, equipment_id, meter_type_id, kinds)`: the pair is a choice and its
  kind is in `kinds` (`(COUNTER,)` for the trigger, `(COUNTER, GAUGE)` for an item) → `None`, else
  the message of § 5.1 / § 5.4.
- **Checked whenever sent** (D10), from plain reads after the locks (§ 5.7). A meter removed from
  the model or the node since the plan was saved blocks the next save of that field; the page shows
  it on load (§ 5.9).
- **No counter meter at all** on the node and above: the page cannot tick *By meter* (§ 5.9).

### 5.6 Permissions

| Key | Holders | Where |
|---|---|---|
| `pm_plan:edit` (new) | `("maint_engineer",)`, so the manager; not IT admin (Q2.2 a), not the supervisor | `SITE_SCOPED`; checked at the node's current site |
| `equipment:read` (existing) | `("*",)` | the node through `load_node_for_user`: 404 outside the user's units |

Comment in `config_rbac.py`: "PM plans (S096, R03.2): written by the engineer (so the manager) at
the node's site; not IT admin, who reads PM only (R03 Q2.2 a, ISO 27001 A.8.2); not the supervisor.
Plans are read with equipment:read, as one-point lessons (S075 D5); jobs get pm_job:read (R03.3)."

| Route | Decorator | Then |
|---|---|---|
| `GET /api/pm/plans?equipment_id=` | `equipment:read` | `load_node_for_user(..., for_update=False, key="equipment:read")`: 404 outside the units |
| `GET /api/pm/plans/<id>` | `equipment:read` | the plan's node, as above: 404 for a missing plan and for one outside the units |
| `POST /api/pm/plans` | `pm_plan:edit` | the node 404, then `pm_plan:edit` at its site 403 ("You can't do this at BRICKS", `require_perm_at`), scrapped 409 |
| `PUT /api/pm/plans/<id>` | `pm_plan:edit` | the plan 404, its node 404, the key at its site 403, scrapped 409 |
| `GET /api/pm/meter-choices?equipment_id=` | `pm_plan:edit` | the node 404, the key at its site 403 |
| `POST /api/pm/item-check` | `pm_plan:edit` | the body's `equipment_id`: 404, 403 |

- `require_perm` (`backend/auth_utils.py:495`) answers 403 when the key is held nowhere; a request
  with no identity is refused 401 before any route, never admin.
- **Buttons follow the answer's flags:** *Add PM plan* with the list's `can_add`; the page's
  inputs, *Add item*, *Save plan* and *Deactivate* with the detail's `can_edit`. `can_add` and
  `can_edit` = `has_perm_at("pm_plan:edit", site)` and the node not scrapped. So no button ends in a
  403 or 409.
- **The people list** of the page is `GET /api/tickets/people?equipment_id=` (`tickets.list_people`,
  `backend/tickets.py:789`; `ticket:raise` at the node's site, held by every `pm_plan:edit` holder,
  since the engineer's role includes the operator's). The page keeps the people with `assignable`
  (D11).
- **Who sees what:** operator, supervisor, technician, storekeeper, IT admin: the card and the page,
  read-only. Engineer and manager: they write at their sites; an engineer who is an operator at
  BRICKS reads BRICKS plans and writes none there.
- **Identity:** no field changes who can log in or what anyone sees. `assignee_id` names a person;
  only their name is answered (no email, no login).

### 5.7 Locks

The database runs REPEATABLE READ. Each write decides from its locking reads and from plain reads
made after the locks that guard them; access checks are plain reads. **A locking read does not
start the snapshot; the first plain read does.** pm_plans.py takes per write at most one exclusive
row lock, the plan's own, then only shared locks.

**Create** (`POST /api/pm/plans`), one `transaction`:

1. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` — (1) shared, the first
   statement; missing → 404 "Not found".
2. Plain (the snapshot starts here, after the lock): `load_node_for_user(cur, id, for_update=False,
   key="pm_plan:edit")` → 404 / 403; then the locked row's `lifecycle` `scrapped` → 409
   `SCRAPPED_MESSAGE`.
3. Plain: the meter choices (§ 5.5), the assignee (§ 5.3); `plan_rules_error` (§ 5.1); the items
   (§ 5.4).
4. `insert_row(cur, "pm_plans", …)`: shared foreign-key locks on the node (held), the person, the
   meter type and the meter's node (the node or an ancestor). `uq_pm_plans_title` → 409.
5. `insert_row(cur, "pm_plan_items", …)` per item, in order (foreign keys: the new plan, the meter
   type, the meter's node, shared).
6. The answer (§ 6.1), read inside the transaction.

**Change** (`PUT /api/pm/plans/<id>`), one `transaction`:

1. `SELECT * FROM pm_plans WHERE id = %s FOR UPDATE` — (6e) the plan row, exclusive, the first
   statement; missing → 404.
2. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` with the locked row's
   `equipment_id` — (1) shared.
3. Plain: `load_node_for_user(..., key="pm_plan:edit")` → 404 / 403; scrapped → 409 (every `PUT`,
   `{active}` alone too: a scrapped node is read-only, `backend/equipment.py:183`); the meter
   choices and the assignee when sent; then `plan_rules_error(merged, meter_type, today)` (§ 5.1).
4. When `items` is sent: plain read of the plan's active items (`ORDER BY position, id`); every
   item write holds (6e), so the read sees the newest committed rows; `sync_items`.
5. `update_row` of the plan; the item inserts, updates and deactivations (shared foreign-key locks
   as in create).
6. The answer.

**The item check, the meter choices and the reads:** plain, no lock.

**No deadlock cycle**, against the LOCK ORDER notes (`backend/equipment.py`, `backend/contracts.py`,
`backend/procedures.py`, `backend/meters.py`):

- *The plan row (6e):* only pm_plans.py locks it, always first in its transaction, one row per
  write. Nothing holds another lock and then waits on a plan row. (R03.3's daily run and R03.4
  must keep this: lock the plan first; the brief of R03.3 extends this note.)
- *The node (1), shared, after (6e):* the node writers (equipment.py, meters.py, item_properties.py,
  the scrap) hold the node exclusive and never wait on a plan row, so a plan write waits behind them
  and finishes. contracts.py takes the same order (its contract row first, then the node `LOCK IN
  SHARE MODE`, `backend/contracts.py:520`).
- *A create* takes no existing plan row: it share-locks the node and inserts. Two creates of one
  title on one node: the second waits on the first's unique-index entry and gets 1062 → 409.
- *The meter's node, an ancestor, through a foreign key (shared):* a scrap locks a subtree top-down
  (equipment.py's "one accepted deadlock"); a plan write holding the part shared and waiting for
  the machine's shared lock behind that scrap is the same accepted case as a ticket raised on a
  part (`backend/equipment.py`, the tickets.py S017 bullet): InnoDB rolls one side back (1213, a
  plain 500); a retry gives the right answer. A move locks the moved node and its target parent,
  never a child, so no cycle with it.
- *The person, the meter type:* shared through foreign keys; their writers (masters.py's person
  and meter-type writes) never wait on a plan row.

The coder writes this into pm_plans.py's LOCK ORDER note and adds to equipment.py's note, after the
contracts.py bullet: "(6e) the PM plan row (pm_plans.py, S096): one at a time, first in its
transaction, then the node (1) LOCK IN SHARE MODE; a plan create takes the node LOCK IN SHARE MODE
and locks no plan row. The inserts and updates take shared foreign-key locks on the node or an
ancestor (the meter's), a person and a meter type. No other module locks a pm_plans or pm_plan_items
row, so it adds no lock cycle beyond the accepted scrap case."

### 5.8 The PM card (equipment page)

`PmPlansCard.vue`, loaded by itself, as `LessonsCard.vue` (`frontend/src/views/equipment/LessonsCard.vue`).

- **Place:** after *Open tickets* and before the *Details* row, on every width (`order-0` in the
  page's flex column, so on a phone it comes before Documents and Details). Lessons, *Under
  contract* and *Open tickets* stay first: they are what the technician who scans the QR label
  needs now; PM is planned work.
- **Shown** when the node or its parts have a plan, or `can_add`. No empty box for a floor reader
  of a machine with no plan.
- **Header:** "PM plans (n)" (the active count) and, with `can_add`, the button *Add PM plan*
  (`tap-target`), which opens `/equipment/<id>/pm/new`.
- **One row per active plan**, a link to `/equipment/pm/<plan id>`: the title in bold; the trigger
  text; under it a small line: "Run hours · HP003" when the plan has a meter, then "7 items ·
  Kannan (technician)" (or "· No one yet", or "· Operator" for an operator plan). A plan on a part
  shows the part's code first: "GBX001 · Gearbox oil change". The node's own plans come first, then
  its parts' plans; each group by title.
- **Inactive plans:** a link "Inactive plans (2)" under the rows shows them, greyed, with the badge
  *Inactive*. For every reader (an inactive plan is history, not a secret).
- **Empty state** for an editor: "No PM plans yet. Add the first one with Add PM plan."
- **Load error:** "PM plans could not be loaded: <message>".
- A scrapped node: the rows, no button (`can_add` false).

### 5.9 The plan page

Routes (`frontend/src/router/index.js`), after the lesson route, both under `/equipment/` so the
*Equipment* nav item stays lit (the lesson route's comment); not nav items, so the API's 404 is the
gate:

- `{ path: "/equipment/:id(\\d+)/pm/new", name: "pm-plan-new", component: PmPlanView, meta: { title:
  "PM plan" } }`
- `{ path: "/equipment/pm/:id(\\d+)", name: "pm-plan", component: PmPlanView, meta: { title: "PM plan" } }`

**Load:** new: `GET /api/equipment/<id>` (the node), `GET /api/pm/meter-choices?equipment_id=`,
`GET /api/tickets/people?equipment_id=`. Existing: `GET /api/pm/plans/<id>`; then the meter choices
and the people only when `can_edit`. A 404: "PM plan not found, or not at your units." with *Back
to the equipment*. A 403 on a new plan (typed URL): "You can't add PM plans here." with the same link.

**Layout** (mock-up 01): the path line "SMTW › MCC2 › HP003 › PM plans" (as the equipment page's);
the heading "New PM plan" or the plan's title, with the badge *Inactive* when so. From `lg` two
columns: left the *Plan* card and the *When is it due?* card, right the *Items* card; on a phone one
column in that order. The buttons at the end, right-aligned from `md`, full width on a phone.

**Plan card:**
1. **Title** — text; help "For example: Monthly hydraulic check".
2. **Equipment** — read-only: "HP003 — Hydraulic press 3 · SMTW.MCC2".
3. **Done by** — *Maintenance* / *Operator* (`PERFORMERS`). Changing it sets the verification tick
   to the new performer's default (§ 5.1) and, for *Operator*, clears *Assign jobs to*.
4. **Assign jobs to** — for *Maintenance*: a select, *No one yet* then the assignable people by name
   ("Kannan (technician)"; a contractor with "· Atlas Copco"). For *Operator* the select is replaced
   by the line "Operator plans are not assigned: the operators of the unit do them." A stored
   assignee not in the list: shown as the first option "Kannan — no longer at this site", with the
   warning "Choose another person, or No one yet." under the field.
5. **An engineer verifies each job** — tick; help "Leave it ticked for maintenance work. Untick it
   for routine checks."

**When is it due? card:**
1. Tick **By calendar: every** [number] [*days* / *weeks* / *months* / *years*] (one line, wraps on
   a phone).
2. Tick **By meter: every** [number] [unit] **of** [meter select: the counter choices, "Run hours ·
   HP003"]. Under it: "Run hours now: 1,996.4 h (26-10-2026 18:00)" from the choice's `last`, or
   "No reading yet." With no counter choice: the tick disabled and the reason under it: "This
   machine has no counter meter. Add one on the Meters card first." A stored meter not among the
   choices: "Run hours · HP003 is no longer on this machine. Choose another meter."
3. Help: "Both ticked: the job is due at whichever comes first."
4. **Last done** — a date (`<input type="date">`, max today) and, with *By meter*, the meter value
   with the unit after it; help "When was this work last done, before Yantra? Leave it empty if you
   do not know."
- The two ticks give `trigger_kind` through `kindFromTicks` (`calendar`, `meter`, `both`, or `null`
  → the API's "Tick By calendar or By meter, or both."). An unticked trigger sends `null` for its
  fields; its typed values stay in the form while the page is open.

**Items card:** header "Items (n)" and *Add item* (with `can_edit`). From `md` a table (#, Type,
Item, Limits / meter, Photo, actions); on a phone a list, one item per row: the type badge and the
text, a small line with the limits / meter and the photo setting. Badges: *Task* `text-bg-secondary`,
*Check* `text-bg-light border`, *Reading* `text-bg-info` (the mock-up). Each row, with `can_edit`:
*Move up* and *Move down* (icon buttons with those labels, `tap-target`; the first row has no *Move
up*, the last no *Move down*) and a tap on the text opens the item dialog to edit it. Under the list
the legend of the mock-up: "Task: done or not done. Check: OK, Not OK or NA. Reading: a value with
limits; a reading that names a meter also logs a meter reading." Empty: "No items yet. Add the
first item."

**Buttons:** *Cancel* and *Save plan* (`can_edit` only; a reader sees *Back to the equipment*).
- *Save plan* sends `POST /api/pm/plans` or `PUT /api/pm/plans/<id>` with `planBody(form, items)`:
  every field, and `items` as the list in its order (each with its `id` when it has one). While it
  runs the button is disabled and reads "Saving…". A refusal shows beside its field (the page's
  `fieldError(name)`); an `items` refusal ("Item 3: …") shows above the items list, and row 3 is
  outlined red. On success the page goes to the equipment page (`router.push`), where the card
  shows the plan: the engineer enters the next plan from there.
- *Cancel* goes back to the equipment page; with unsaved changes it asks first, in place: "Leave
  without saving? Your changes are lost." *Yes* / *No*. (Leaving through the nav loses them without
  asking, as on *Raise ticket*: the app has no route-leave guard; § 9 A5.)
- **Deactivate / Reactivate** (an existing plan, `can_edit`): `ActiveToggle.vue` as it is, label
  the plan's title ("Deactivate **Monthly hydraulic check**?" *Yes* / *No*), left of the buttons. It
  sends `PUT {active}` alone and reloads the page. Under it, while asking, the line "It makes no
  more jobs." states the consequence (CLAUDE-COMMON scope B; BR1-14). The page provides `FORM_DIRTY`
  (`frontend/src/utils/formDirty.js`), so with unsaved changes the toggle is blocked with its own
  reason ("Save your changes first, or cancel them"). An inactive plan shows the line "This plan is
  inactive. It makes no jobs."
- **Read-only** (`can_edit` false): the same cards with the values as text, no inputs, no item
  actions; the items' help text under each item.
- **Created / changed:** a small line at the end: "Created 01-11-2026 by Priya · Changed
  02-11-2026 by Arun" (names only, as the lesson page; BR1-04).

### 5.10 The item dialog

`PmItemDialog.vue`: `FormModal.vue` through `useFormModal` (`frontend/src/composables/useFormModal.js`).
Title *Add item* / *Edit item 3*. Fields, one column:

1. **Type** — three large toggle buttons *Task*, *Check*, *Reading* (`btn-group`, `tap-target`),
   with the legend line for the chosen one under them; default *Check*.
2. **What to do or check** — text; help for Task "For example: Grease the main bearing", for Check
   "For example: No oil leaks at the cylinder seals", for Reading "For example: Main pressure at full
   load".
3. Reading only: **Logs a meter** — select: *No meter* then the counter and gauge choices
   ("Oil temperature · HP003 (°C)"); help "The value is also saved as a meter reading." Without a
   meter: **Unit** (text, help "For example: bar, mm, °C"). With a counter meter: no limits. Else
   **Min** and **Max** (number inputs, `inputmode="decimal"`, side by side), help "Out of these
   limits, the job marks the value High or Low." When a gauge meter is chosen, Min and Max are
   filled from the choice's limits in force (`min_value`, `max_value`, § 5.5); the engineer may
   change or clear them, since a check limit may be tighter than the meter's alarm limit (BR1-05).
   The item's limits are the job's (R03.4); the meter reading R03.4 writes keeps the meter's own
   `limit_state` (`meters.log_reading`).
4. **Help text** — text area, optional; help "How to do it, or what good looks like."
5. **Photo** — *No photo* / *Optional* / *Required*; default *Optional*.
6. On edit, in the footer's left slot: *Remove item*, with its own confirmation in place: "Remove
   item 3? It goes when you save the plan." *Yes* / *No*.

- **Call contract** (settings: *Self-check, repo items* (13)): `useFormModal({ path:
  "/api/pm/item-check", blank, fromRecord, afterSave, toBody: itemBody, label: (item) => item.text
  })` (an item has no `code`, so the default `label` of `useFormModal.js` would read nothing;
  BR1-12). `blank()` returns
  `item_type: "check"`, `photo: "optional"`, every other field empty, and takes no seed
  (`openCreate()` is called without one). `fromRecord(item)` copies the item (its `id` kept, the
  meter as one select value `"<equipment_id>:<meter_type_id>"`). The dialog's save always calls
  `send(() => apiPost("/api/pm/item-check", { equipment_id, ...itemBody(form) }))`, never `save()`:
  the check route is a `POST` for a new and an edited item alike, and writes nothing. `afterSave(
  result)` emits `done({ item: result, index })` to the page, which puts the item into its list
  (a new one at the end) and marks the page dirty. *Remove item* emits `remove(index)`.
- **Why a check route:** a refusal shows beside its field in the dialog, at once, on a phone (S026,
  "a refusal is always in view"), from the backend's own rules, and the plan's save checks every
  item again (D2).
- **The one-tap path:** *Add item*, type the text, *Save item* (the dialog's save button label):
  a Check with an optional photo.
- **Disabled controls:** none in the dialog.

### 5.11 The database down

Every route goes through `get_db()`: 503 while the database is down or missing (§ Yantra Specifics,
*DB may not exist*). No background task, no alert, no file.

## 6. API

All under `pm_plans_bp` at `/api/pm`, ids `<int:…>`. The list and create routes use `/plans` with
`strict_slashes=False`, as procedures.py's.

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/pm/plans?equipment_id=` | `equipment:read` | `equipment_id` required | 200 `{items, inactive, can_add}` (§ 6.2); 400, 404 |
| `GET /api/pm/plans/<id>` | `equipment:read` | — | 200, the plan (§ 6.1); 404 |
| `POST /api/pm/plans` | `pm_plan:edit` | § 5.1, § 5.4 | 201, the plan; 400, 403, 404, 409 |
| `PUT /api/pm/plans/<id>` | `pm_plan:edit` | any subset of § 5.1; `items` replaces the list (§ 5.4) | 200, the plan; 400, 403, 404, 409 |
| `GET /api/pm/meter-choices?equipment_id=` | `pm_plan:edit` | `equipment_id` required | 200 `{items}` (§ 5.5); 400, 403, 404 |
| `POST /api/pm/item-check` | `pm_plan:edit` | `equipment_id` and one item (§ 5.4) | 200, the clean item (§ 6.1's item shape, `id` as sent); 400, 403, 404 |

- `equipment_id` missing in a query: 400 "equipment_id is required" (as `list_lessons`,
  `backend/procedures.py:303`); not a whole number ≥ 1: `int_arg`'s 400.
- **An item-check refusal** carries the item's own field (`text`, `max_value`, …), so the dialog
  shows it beside the field; a plan save's item refusal carries `items` and "Item N: …".

### 6.1 The plan

`{id, equipment: {id, code, name, level, full_path, site_code}, title, performer, assignee: {id,
name, role} | null, needs_verification, trigger_kind, calendar_every, calendar_unit, meter: {equipment_id,
code, meter_type: {id, name, unit, kind, decimals}} | null, meter_every, last_done_on,
last_done_meter, trigger_text, meter_label, active, created_at, created_by_name, updated_at,
updated_by_name, items, can_edit}`.

- An item: `{id, position, item_type, text, help_text, photo, unit, min_value, max_value, meter: {…}
  | null, limits_text}`; the active items in `position` order.
- Numbers (`meter_every`, `last_done_meter`, the limits) as strings through `format_number` ("250",
  "62.5"), `null` when empty; booleans as `true` / `false`; dates `YYYY-MM-DD`, times as
  `row_to_dict` gives them (`backend/db_helpers.py:100`).
- The names of `created_by` / `updated_by` through `people.username` (as `_LESSON_SELECT`,
  `backend/procedures.py:92`), the login when no person matches.

### 6.2 The card list

`items`: the active plans of the node and of its parts (`equipment_id` in the node, its children
and grandchildren; plain), each `{id, title, equipment: {id, code}, own (the node's own),
performer, assignee: {id, name, role} | null, trigger_text, meter_label, item_count, active}`, the
own plans first, each group by title. The assignee's `role` is their membership's role at the
node's current site (one join of `memberships` for the whole list), `null` when they hold none
there any more; the card shows "Kannan (technician)" from it (BR1-04). `inactive`: the same for the inactive plans. `can_add` (§ 5.6).
At most `MAX_PER_PAGE` (200) rows in each list; no machine has that many plans.

## 7. Design decisions

- **D1. The editor is a page, not a dialog** (mock-up 01). A plan holds a header, a trigger and up
  to 50 items, and each item opens its own dialog; a dialog inside a dialog does not work on a
  phone (Bootstrap shows one modal at a time). Rejected: `FormModal` for the plan (nested modals,
  a cramped phone screen).
- **D2. One save for the plan and its items; each item checked in the dialog by a check route.**
  `Save plan` sends the plan with its whole item list, saved in one transaction under the plan's
  lock, as the mock-up's single button promises; the plan and its items never disagree. The dialog
  asks `POST /api/pm/item-check` first, which runs the same `validate_item`, so the engineer sees
  "Min must not be above Max" beside *Max* at once. Rejected: one route per item (POST / PUT /
  DELETE / reorder: four more routes, a new plan must be saved before its first item, and a half
  edited plan is live); checking items only at *Save plan* (the refusal for item 3 then appears on
  the page, away from the field).
- **D3. Plans are read with `equipment:read`; no `pm_plan:read`.** A plan is part of the machine's
  record, as a lesson (S075 D5); every reader of the machine reads its plans, IT admin included
  (Q2.2 a). A `pm_plan:read` key would equal `equipment:read` today. R03.3's `pm_job:read` is for
  jobs. Rejected: a new read key (a matrix row with no difference).
- **D4. Removed items stay as inactive rows; items keep their ids across saves (sync by id).**
  R03.4's results and R03.17's reference photos will name an item, and an item's readings across
  jobs form a trend (ISO 14224). Rejected: replace-all on every save (new ids each time, orphaned
  photos later); hard delete (fine today, a migration later).
- **D5. The meter is named by node and type** (`meter_equipment_id`, `meter_type_id`), not by type
  alone. A part and its machine may both carry *Run hours*; Plan § 4.3 says the alternating pump
  picks its own, the gearbox its machine's. `meter_type_id` keeps S095's name; the core never needs
  the node. Rejected: the type alone (ambiguous when two levels carry the same type).
- **D6. `before_use` is in the column and refused by S096's API.** The column takes all four of
  S095's `KINDS`, so R03.13 needs no migration; until R03.13 builds *Start CIL*, a before-use plan
  would make nothing, so the API says so. Rejected: accepting it now (a plan that silently never
  runs).
- **D7. The default assignee follows the ticket rule** (`ASSIGNABLE_ROLES` at the node's site,
  `tickets.person_at_site`), and operator plans have none. The same people may be assigned a
  ticket and a PM job; an operator job is done by whoever runs the machine (R03.12's *CIL today*).
  Rejected: any person with a membership (operators assigned maintenance work); an assignee on
  operator plans (R03.12 may allow it; relaxing a rule needs no data change).
- **D8. Calendar units day, week, month, year; at most 10 years.** S095's `CALENDAR_UNITS` has
  years; a fire extinguisher's replacement (5 years, Plan § 4.3) and a pressure test need them. A
  small departure from Plan § 4.3's "days / weeks / months", recorded in Plan.MD. Rejected: months
  only past a year (60 months reads badly).
- **D9. Items move with *Move up* / *Move down*,** not drag and drop. Two large buttons work with a
  gloved thumb and need no library. Rejected: drag handles (the mock-up's dots; a new dependency
  and poor on a phone).
- **D10. A meter and an assignee are checked whenever they are sent, equal to the stored value or
  not.** The page sends the whole form, so a plan whose meter or person is gone cannot be saved
  stale; the page warns on load, before the engineer types. Rejected: skipping the check for an
  unchanged value (S080's vendor rule; here it would keep a plan pointing at a meter the machine no
  longer has, which R03.3 could not schedule).
- **D11. The people list reuses `GET /api/tickets/people`.** It already answers the node's site
  people with `assignable` and the vendor name. Rejected: a PM copy of `people_at_site` (two lists
  to keep equal).
- **D12. The card shows the node's plans and its parts' plans.** An engineer on the extruder's page
  sees the gearbox oil change too; the add button adds on the node itself. Rejected: the node's own
  only (the machine page hides most of its PM).
- **D13. One title per node** (`uq_pm_plans_title`): two plans of one name on one machine is a
  mistake, and the key stops a double tap from making two plans. Rejected: no key (duplicates on a
  double tap; a create takes no counter).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v51.py`)

- A fresh database: both tables with their keys (`uq_pm_plans_title`, `ix_pm_plan_items_plan`) and
  foreign keys (`fk_pm_plans_equipment`, `fk_pm_plans_assignee`, `fk_pm_plans_meter_equipment`,
  `fk_pm_plans_meter_type`, `fk_pm_plan_items_plan`, `fk_pm_plan_items_meter_equipment`,
  `fk_pm_plan_items_meter_type`).
- **A v50 database with a node, a person and a meter type** migrates to v51; the rows are kept.
- `trigger_kind`'s ENUM equals `pm_schedule_core.KINDS` and `calendar_unit`'s `CALENDAR_UNITS`, in
  order (from `information_schema.COLUMNS.COLUMN_TYPE`).
- The CHECKs refuse (4025): `calendar` with no `calendar_every`; `calendar` with a meter; `meter`
  without `meter_equipment_id`; `meter_every` 0; `calendar_every` 0 and 3651; `calendar_unit`
  without `calendar_every`; `last_done_meter` without a meter; −1; `before_use` with
  `last_done_on`; an assignee on an operator plan; an item `task` with a unit; a reading with a
  meter and a unit; a meter type without its node; Min above Max; position 0. They pass:
  `both` with all five fields, `before_use` with none, `calendar_every` 1 and 3650, Min = Max.
- A duplicate title on one node is refused (1062); the same title on two nodes passes.
- A `meter_type_id` that does not exist is refused (1452).
- A re-run of v51 changes nothing (`_schema()` equal).

### 8.2 Backend (`test_pm_plans_core.py`, `test_pm_plans_api.py`)

**Core** (no database): `validate_plan` — each message of § 5.1; every required field missing on a
`POST`; nothing required on a `PUT`; the title collapsed; 100 / 101 characters; `performer`
"Operator" (case) refused; `needs_verification` absent → `True` for maintenance, `False` for
operator; `trigger_kind` missing, `"weekly"`, `before_use` refused with their texts;
`calendar_every` `true`, `"3"`, 0 refused; `calendar_unit` "months" refused; `meter_every` "0.0005"
(4 decimals) and `true` refused; `last_done_on` "1999-12-31", "02-10-2026" refused;
`last_done_meter` "-1" refused, "0" passes. `plan_rules_error(merged, meter_type, today)`: the
null-ness rules (each mix); `calendar_every` 120 months pass, 121 refused with "… from 1 to 120.";
3650 days pass, 3651 refused; 10 / 11 years; a `PUT` that sends only `calendar_unit` year over a
stored 120 refused on the merged pair; `meter_every` "250", "0.5" pass on a 1-decimal type, "0.05",
"0", "-5" refused; `last_done_meter` "0.05" on a 1-decimal type refused; `last_done_on` today
passes, tomorrow refused. `default_verification`. `interval_number` ("250" with 1 decimal →
"250", "0.5" → "0.5", "5000" → "5,000", "1234567.8" → "12,34,567.8").
`trigger_text` for every row of § 5.2 (singular and plural, Indian grouping "5,000 h", a
1-decimal type "Every 0.5 h"). `meter_label`. `meter_choice_error` (missing pair, a gauge for the
trigger, an amount, a pair not in the choices). `validate_item` — each message of § 5.4; Task with a
unit; reading with a meter and a unit; counter meter with a limit; −20 to 60 passes; "62.55" on a
1-decimal type refused; Min = Max passes. `validate_items` — not a list, empty, 50 pass, 51
refused, "Item 3: …" prefix. `sync_items` — insert, update of changed fields only, move, removal,
an unknown id, an id twice, positions 1..n; nothing changed → nothing to write.
`item_limits_text`.

**API**, each test with its own site, unit, model and machine (`make_site`, `make_unit`,
`make_model`, `make_equipment`, `make_meter_type`, `make_person`, `user_at_sites` and
`give_site_role` of `backend/tests/conftest.py`; titles with `uniq`; rows read with `db_rows`):
- **Create:** an engineer at site A, a calendar plan with three items (201; the answer's
  `trigger_text`, `items` in order, `can_edit` true; `created_by` the engineer); a `both` plan with
  a counter model meter of the machine; a plan on a part with its machine's counter (the ancestor
  choice) and one with the part's own counter of the same type (two plans, two different
  `meter_equipment_id`); the manager (201); IT admin, an operator, a technician, a supervisor, a
  storekeeper (403); an engineer of A on a node of B where they are operator (403 naming B); a node
  outside the user's units (404); a missing node (404); a scrapped node (409); a gauge as the
  trigger (400 `meter_type_id`); a meter of another machine (400); `before_use` (400); no items
  (400 `items`); 51 items (400); an assignee who is a technician at A (201), an operator at A, a
  technician of B only, an inactive person (400 `ASSIGNEE_AT_SITE`); an operator plan with an
  assignee (400); a duplicate title on the node (409 `title`); default `needs_verification` by
  performer.
- **Change:** each plan field; `equipment_id` equal (200) and different (400); a meter change; a
  calendar plan made `both` and back; items: an update keeps the id, a move changes positions, a
  removal sets `active = 0` and the row stays (`db_rows`), a new item is inserted; another plan's
  item id (400); `{active: false}` then `{active: true}`; a `PUT` with nothing changed leaves
  `updated_at` NULL; a scrapped node (409, `{active}` alone too); an engineer of B (404 without a
  role at A; 403 when operator at A); a missing plan (404); a stored assignee who left the site,
  sent again (400).
- **Read:** the card list for an operator at the node's unit (200; own plans then parts' plans;
  `inactive`; `can_add` false); for the engineer (`can_add` true; false on a scrapped node); a user
  outside the unit (404); `equipment_id` missing (400). The detail for IT admin (200, `can_edit`
  false) and for an engineer (true).
- **Meter choices:** the node's counter and gauge meters in force, then the parent's, then the
  grandparent's, each with `last`; an amount and a Yes / No meter left out; a removed own meter left
  out; the operator (403).
- **Item check:** 200 with `limits_text`; each refusal with its own field (`max_value`, `text`,
  `unit`); IT admin (403); a node of another site (404).
- **The database down** (`db_down`, `backend/tests/conftest.py:241`): `GET /api/pm/plans` and `POST
  /api/pm/plans` answer 503.

### 8.3 Existing tests that change or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` — `pm_plan:edit` joins the engineer and manager
  rows; the comment above the rows gains "S096: pm_plan:edit to the engineer (so the manager); not
  IT admin, not the supervisor". New `test_pm_plan_keys`: the holders of `pm_plan:edit` are exactly
  `maint_engineer` and `maint_manager` (`compute_permissions` over `ROLES`) and it is in
  `SITE_SCOPED`. `test_site_scoped_keys_exist` and `test_every_role_gets_wildcard_permissions` stay
  green.
- `backend/tests/test_readings_api.py`: runs again unchanged (the sheet now calls
  `meters_with_last`); green.
- `backend/tests/test_meters_api.py`: runs again; green.
- `backend/tests/test_modules.py` (`LATEST_VERSION`): green at 51.
- `backend/tests/test_migration_v50.py`: today it builds `local_db._MIGRATIONS` whole (`V50`, line
  25) and asserts `_versions() == [41, 50]` (lines 114, 156, 250): red once v51 is appended. Fixed
  by § 3's filter to `<= 50` (BR1-01).
- `backend/tests/test_migration_squash_v41.py`: builds `CURRENT = local_db._MIGRATIONS` (line 27)
  and asserts `_versions() == [*range(20, 42), 50]` (line 108): red once v51 is appended. Fixed by
  § 3's versions assert over the later migrations (BR1-01).
- `backend/tests/test_schema_docs_shell.py`: green once `tooling\schema-docs.bat write` has run.
- `backend/tests/test_auth.py`: compares `/api/auth/me`'s `permissions` with `compute_permissions`;
  green.
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/lessons.spec.js`, `frontend/e2e/contracts.spec.js`
  and `frontend/e2e/readings.spec.js` open the equipment page; the new card appears only where a
  plan exists or for editors (an engineer sees "PM plans" with *Add PM plan* on every machine). The
  two order tests that use `"Open tickets"` (`frontend/e2e/contracts.spec.js:586`, *S082: the Under
  contract card comes before Open tickets*; `frontend/e2e/lessons.spec.js:258`) check cards above
  *Open tickets*; the PM card comes after it, so both stay green. A test that counts the page's
  cards would change: the coder checks these specs and names any line changed in the impl report.

### 8.4 Automated (e2e, `frontend/e2e/pm-plans.spec.js`)

Set-up by API in the spec (`apiAs`, `frontend/e2e/support/people.js`): each test makes its own
machine with `meterMachine(testInfo, tag, { unit: "SMTW.MCC2", modelMeters: [["Run hours", {}],
["Oil temperature", {}]] })` (`frontend/e2e/support/meters.js:10`; MCC2 so the operator sees it) and
plans by `POST /api/pm/plans` as the engineer. Every flow test calls `expectDialogFits` on each item
dialog it opens; refusals with `expectFieldMessage`. Untagged unless marked.

- **important** `S096: the engineer writes a PM plan and sees it on the PM card` — on the machine's
  page `"Add PM plan"`; title "Monthly hydraulic check"; *By calendar* every 1 *months*; *By meter*
  every 250 of "Run hours · <code>"; *Add item* a Check "Oil level in the sight glass is above min";
  *Add item* a Reading "Power-pack oil temperature", meter "Oil temperature", Min 30, Max 60;
  `"Save plan"`; back on the equipment page the card shows the title, "Every month or 250 h,
  whichever comes first" and "2 items".
- **important** `S096: the plan page refuses an empty save beside the fields` — `"Save plan"` at
  once: "Enter a title." beside *Title*; with a title: "Tick By calendar or By meter, or both.";
  with a calendar interval: "Add at least one item." above the items.
- **important** `S096: a reading with Min above Max is refused in the item dialog` — "Min must not be
  above Max" beside *Max*; the dialog stays open.
- `S096: the engineer edits a plan: moves an item up, removes one, and the card shows the new
  order and count` — `"Move up"`, `"Remove item"` with its *Yes*; after *Save plan* the plan page
  lists the items in the new order and the card "2 items".
- **important** `S096: a deactivated plan leaves the card and shows under Inactive plans` —
  `"Deactivate"`, *Yes*; the card has no row; `"Inactive plans (1)"` shows it with *Inactive*.
- **important** `S096: the technician and IT admin read the plan but cannot change it` — no `"Add PM
  plan"` on the card, the plan page has no `"Save plan"`, no `"Add item"`, the items' text shows.
- `S096: a machine with no counter meter says why By meter cannot be ticked` — a machine of a model
  with only *Oil temperature*: the tick is disabled and "This machine has no counter meter. Add one
  on the Meters card first." shows.
- `S096: a part's plan may count its machine's run hours` — a part made with `noModelPart`
  (`frontend/e2e/support/properties.js:70`) under the machine; on the part's page *Add PM plan*: the
  meter list offers "Run hours · <machine code>"; after the save the machine's card shows the plan
  with the part's code first.
- `S096: the plan page fits a phone with no sideways scroll` (`@device`) — a plan with three items:
  `expectNoSidewaysScroll`; the items show as a list, not a table, below `md`.

`frontend/e2e/screens.spec.js` (its `screens()` list): the plan page `/equipment/pm/<id>` (title
"PM plan", heading the plan's title) for `EVERYONE`, on a machine the file makes in `SMTW.MCC2`
(as the lesson's, so other specs' extruder pages gain no plan); the new-plan page
`/equipment/<id>/pm/new` (heading "New PM plan") for the engineer and the manager.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/pm-plans.spec.js
e2e/equipment.spec.js e2e/screens.spec.js`, and the whole suite at Normal once at the end (the
router is a shared file). No change to `api.js` or `e2e/support/`, so no extra WebKit run.

### 8.5 On a real device

None. The page, the dialog and the card are browser screens that a browser engine judges (fit, no
sideways scroll, disabled reasons). No camera, printer, QR scan or login is involved.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal browser
  runs green.
- By screen: on a press at SMTW, "Monthly hydraulic check", every 1 month or 250 h of the press's
  run hours, last done 02-10-2026 at 1,840 h, seven items as mock-up 01; the card reads "Every month
  or 250 h, whichever comes first"; the technician and IT admin read it; IT admin cannot save.
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**PM plans (S096):** every plan write goes
  through pm_plans.py: the plan row FOR UPDATE first (a change), then the node LOCK IN SHARE MODE,
  scrapped refused; the meter (plan and reading items) is a meter in force on the node or a node
  above it (`pm_plans_core.meter_choice_error`), a counter for the trigger; the assignee holds an
  `ASSIGNABLE_ROLES` role at the node's site; items are synced by id and a removed item is set
  inactive, never deleted (R03.4's results and R03.17's photos name it). `trigger_kind` and
  `calendar_unit` equal `pm_schedule_core.KINDS` and `CALENDAR_UNITS` (a migration test pins it). A
  path that deletes an item row, or writes a plan without the node lock, breaks R03.3–R03.17."

## 9. Open questions and assumptions

All choices below were **decided by the orchestrator under KLA's go-ahead of 01-11-2026 ("Do those
steps … stop only for real show stoppers"), to confirm at gate B.** None is defining.

- **Q1. The editor as a page with one *Save plan* (D1, D2)**, items checked one by one in a dialog.
  Taken as recommended.
- **Q2. Read with `equipment:read`, no `pm_plan:read` (D3).** The storekeeper also reads plans (he
  reads the machine). Taken as recommended.
- **Q3. `before_use` refused by the API until R03.13 (D6).** Taken as recommended.
- **Q4. Operator plans have no assignee (D7).** R03.12 may relax it. Taken as recommended.
- **Q5. Calendar in years too, at most 10 years (D8).** A departure from Plan § 4.3's list,
  recorded in Plan.MD. Taken as recommended.
- **Q6. The card shows the parts' plans too (D12); one title per node (D13).** Taken as recommended.
- **A1. S095's constants.** `pm_schedule_core` exists when S096 is coded (S095 is coded first). If
  its names differ, the staleness review fixes this brief before coding.
- **A2. No next-due line.** The mock-up's "Next due: 02-11-2026 or at 2,090.0 h" comes with R03.3;
  S096 shows the meter's latest reading only.
- **A3. The seed is not checked against the latest reading** (§ 5.1). A typo (18,400 for 1,840 h)
  makes a far due point; R03.3's next-due line will show it on the card.
- **A4. A moved machine or a departed assignee** keeps the stored assignee; R03.3 decides what a job
  does then (unassigned, by the roadmap's spirit). S096 shows the warning on the page.
- **A5. No route-leave guard.** Leaving through the nav loses unsaved plan edits, as on *Raise
  ticket*; *Cancel* asks.
- **A6. Notes for R03.3 and R03.4** (not S096's to build): skip plans of scrapped nodes and
  inactive plans; the plan row is locked first (§ 5.7); the row goes to S095's core as it is (its
  key is `trigger_kind` too); S095's `created_on` is the IST date of `created_at` (BR1-13). For
  R03.4: an item's Min / Max judge the job's value; the meter reading it writes keeps the meter's
  own limit state (BR1-05).
- **The size rule:** two tables (a record and its lines), two screens and one dialog, 24 code and
  test files: no split (BR1-07). The coder codes and hands back in the order backend (core tests
  first), backend tests, frontend, and the code review reads the diff in that order. **Length** about 990 lines, past S080 (824): most of it is the field tables,
  the lock sequences and the tests by name.
- **Standards *to verify*:** EN 13306 term numbers; ISO 55001:2024's clause for information
  requirements; ISO 14224's clause.
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 01-11-2026

Sections changed: § 3 (Backend: `pm_plans_core` functions, `contracts_core.py`; Tests: the two
migration tests; Docs: `notes.json`; file count), § 4.1 (the ENUM note, the title message), § 5.1
(two phases, table rows, the `before_use` text), § 5.2 (`interval_number`), § 5.4 (`limits_text`),
§ 5.7 (create step 3, change step 3), § 5.9 (Deactivate's consequence line, the Created line),
§ 5.10 (Min / Max pre-fill, `label`), § 6.1 and § 6.2 (`assignee.role`), § 8.2 (core tests), § 8.3
(the two migration tests), § 9 (A6, the size rule).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): `test_migration_v50.py` filters `V50` to `<= 50`; `test_migration_squash_v41.py` keeps `CURRENT` whole and asserts the versions over the later migrations. Both named in § 3 Tests and § 8.3; file count 24. |
| BR1-02 minor | Accepted (a): `validate_plan` parses at 3 decimals and dates from 2000; `plan_rules_error(merged, meter_type, today)` holds the null-ness rules, the per-unit maximum on the merged pair, the type's decimals, `meter_every` > 0 and `last_done_on` ≤ today. `trigger_error` is gone. § 3, § 5.1, § 5.7, § 8.2. |
| BR1-03 minor | Accepted (a): `interval_number(value, decimals)` in `pm_plans_core`; `trigger_text` and `item_limits_text` use it ("Every 250 h", "30–60 °C"). § 3, § 5.2, § 5.4, § 8.2. |
| BR1-04 minor | Accepted (a): `assignee: {id, name, role}` in § 6.1 and § 6.2, the role at the node's current site; the Created / Changed line shows names only. |
| BR1-05 minor | Accepted (a): a gauge meter pre-fills Min and Max from its limits in force, editable; the item's limits are the job's, the meter reading keeps the meter's state. § 5.10, § 9 A6. |
| BR1-06 minor | Accepted (a): `iso_date = _iso_date` in `contracts_core.py`, imported by `pm_plans_core`; anchored by name, as S095 renames `_add_months` in the same file. § 3. |
| BR1-07 minor | Accepted (a): one step; the coder hands back in the order backend, backend tests, frontend, and the code review reads it so. § 9. |
| BR1-08…BR1-14 nits | Accepted: BR1-08 S095's key is `trigger_kind`, the row goes as it is (§ 4.1, A6); BR1-09 the `pm_plans` notes line drops *kind* and *source template* (§ 3 Docs); BR1-10 the 409 names active or inactive plans (§ 4.1); BR1-11 "Before-use plans are not available yet." (§ 5.1); BR1-12 `label: (item) => item.text` (§ 5.10); BR1-13 `created_on` is the IST date of `created_at` (A6); BR1-14 "It makes no more jobs." under the question (§ 5.9). |
