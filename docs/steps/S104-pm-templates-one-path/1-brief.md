```
Step: S104 — PM templates: one path
Doc: brief
Author: Orchestrator (Opus)
Date: 02-11-2026
Track: full
Baseline: 82d38ac + uncommitted S095, S096, S097, S098, S099, S100, S101, S102 (held)
Status: Gate B 13-11-2026 (code review r1–r8: blockers CR1-01 and majors fixed; A1 approved 13-11-2026 and built; fix rounds 1–8; verify review r9: 1 nit, CR9-01, fixed by the orchestrator; no device check); snapshot round 11 1a05dc7
From: R03.18
```

# S104 — PM templates: one path

> **Amendment A1 (§ 10, proposed 13-11-2026, not yet approved):** a part takes a meter from a node
> above it only through a link set on the part's *Meters* card. Once approved, A1 replaces the
> template's parent tick in § 1 item 4, § 4.1, § 5.1–§ 5.3, § 5.10 and D11, and the old-meter note of
> § 9 item 6. § 10 A1.3 lists each replaced sentence; the sections below are left as approved.

## 1. What will be built

The work of a PM plan is written once, on a **PM template** in *Masters › PM templates*. A machine
gets a PM plan only by a template linked to it. This step builds the template, the links table, the
plan row per machine and template, and the link to **one machine** (*Attach PM template*). R03.19
adds links by class, type and model. It reworks the held S096–S102 code onto this shape; nothing of
S095–S102 is committed before it (R03 answer 5b).

After it, an engineer writes *Press — monthly hydraulic check* once, attaches it to the pilot
presses one by one, sets each press's assignee and *Last done*, and every S097–S102 flow (jobs come
due, the job on the phone, verify, send back, reschedule, skip, alerts) works as today.

1. **One migration v57** replaces the unreleased v51–v56 (R03 Q18.1 a). It drops the six PM tables
   (they hold test rows only; production is at v50 and holds none) and creates PM's whole shape:
   `pm_templates`, `pm_template_items`, `pm_template_links`, `pm_plans` (reshaped), `pm_jobs`,
   `pm_job_events`, `pm_job_results` (§ 4.1). The old texts are frozen in
   `backend/tests/fixtures/migrations_v56.py`.
2. **Masters › PM templates** (mock-up 09): the list (name, trigger in words, item count, machines,
   active) and the template page, built from S096's editor parts: name, *Done by*, *An engineer
   verifies each job*, *When is it due?* (calendar, meter type, or both), the items with *Add item*,
   *Move up* / *Move down*, *Save template*, *Deactivate template*. A template is never deleted.
   The page says: "A change here reaches every machine at its next job. A job already started keeps
   the items it started with."
3. **Two reading kinds** on a *Reading* item (R03 answer 18.3, mock-up 14): *Measurement* (its own
   unit and limits; the value stays on the job) and *Meter reading* (a meter **type**; the value is
   saved as an ordinary meter reading of the machine's meter of that type, as S098 does).
4. **The meter match** (R03 answer 18.3, Q18.5 a with the opt-in): a template names meter types,
   never meters. On a machine, each type is matched among the machine's own meters in force (its
   model's plus its own; one per type, so one or none). Per meter (the trigger's, each *Meter
   reading* item's), the template may tick *If the machine has no meter of this type, use the meter
   from a parent node*: then the nearest node above that has the type is used. A template that
   needs a type the machine lacks **does not apply** there: its plan makes no job, and its open,
   not started job is cancelled with a timeline line naming the missing meter.
5. **A machine's plans** (mock-up 11): the equipment page's PM card lists the plans of the node and
   its parts, each with its template's name, its source ("This machine"), the trigger in words and
   the open job or next due, or "Does not apply: no Run hours meter on HP003". *Attach PM template*
   picks an active template and makes the machine link and the plan row.
6. **The plan page** (`/equipment/pm/<id>`, S096's route): the template's work read-only with
   *Open template*; the machine's own settings: *Assign jobs to*, *Last done* (date, meter value),
   the meters the template uses on this machine (read-only: "HP003's own Run hours", "HP002's Run
   hours (from the parent node)", or "Does not apply: no Run hours meter on HP003"); *Save plan*;
   *Remove from this machine*.
7. **A template change reaches the plans:** after the template's commit, each of its plans is
   settled in its own transaction, as the daily run does. A changed interval moves every open, not
   started job at once; a change of the schedule drops the jobs' reschedules (S101 D4).
8. **The jobs read the template:** the list, the job page, *Start* (copies the template's active
   items and its name onto the job), *Mark job done*, the alerts and the daily run read the
   template through the plan row.

### Out of scope

- Links by class, type and model, the template's *Links* card and the list of machines it reaches,
  *Not for this machine* on the screen (R03.19). v57 holds their columns, so R03.19 needs no
  migration.
- The engineer's lists (*PM plans without an assignee*, *Does not apply*), assigning many plans at
  once (R03.20).
- Acting on a reading at once (R03.21); condition rules (R03.22, R03.23); a reading logged elsewhere
  meeting a job's item (R03.24).
- A template's own change history (who changed which item when; today only *updated by*), a copy of
  a template ("Save as new template") (R03.18 *Leaves for later*).
- *Before use* triggers (R03.13): kept in the column, not offered, as S096.
- Photos on items (R03.6), reference photos (R03.17).
- **The help tour and the guide's PM slides** (BR1-04, Q1 at gate A): `tooling/help/setup_tour.py`
  makes PM plans with the old `POST /api/pm/plans` body, and `frontend/help-tour/desktop.tour.js`
  opens `/equipment/<id>/pm/new` (slide 62). Both stop working with this step. They are updated at
  the guide's retake before the release (CLAUDE.md § Docs to keep current, `help/`); until then
  `tooling/help-shots.bat` fails at the PM set-up.

## 2. Standards and practice

- **TPM — planned maintenance pillar.** The plant decides in advance what work each machine needs,
  writes it as a **standard**, and improves the standard. Here the template is the standard: one
  place, every machine it reaches does the same work, and an improvement reaches every machine at
  its next job.
- **EN 13306 — maintenance plan; inspection; predetermined maintenance** (term numbers *to verify*).
  A maintenance plan is a set of tasks with their time scale. A calendar or meter trigger is
  predetermined maintenance (at set intervals of time or use). A *Check* or a *Reading* is an
  inspection (a check for conformity, no repair); a *Task* is maintenance work.
- **ISO 14224 — record maintenance data on the item it was done on** (clause *to verify*). One job is
  one machine and one occurrence; a meter is read on the machine whose hours it counts, which is why
  the match uses the machine's own meters, and a parent's only when the template says so.
- **ISO 55001 § 8.2 — management of change** (clause *to verify*). A change to how assets are
  maintained is controlled. A template save is one recorded change (who, when) that reaches every
  plan; a started job keeps the items it started with.
- **ISO 9001 § 7.5.3 — control of documented information.** Records are kept and protected from
  change. A job keeps its own copy of the items and of the template's name from *Start*; a plan row,
  a template, a template item and a link are never deleted (set inactive).

## 3. Where

### Backend

| File | Change |
|---|---|
| `backend/local_db.py` | v51–v56 removed from `_MIGRATIONS`; **v57** appended (§ 4.1); its comment block. |
| `backend/tests/fixtures/migrations_v56.py` | **New**, frozen: the texts of v51–v56, as `migrations_v47.py` holds v42–v47. |
| `backend/pm_templates_core.py` | **New**, pure: the template's fields, its trigger rules, the items (two reading kinds), `sync_items`, the trigger in words, the limits text. Moved out of `pm_plans_core.py` (the item and trigger rules) with the changes of § 5.1–§ 5.2. |
| `backend/pm_templates.py` | **New** blueprint `pm_templates_bp` (prefix `/api/pm`): the template list, detail, create, change, the item check; the after-commit settle of the template's plans (§ 5.6). |
| `backend/pm_links_core.py` | **New**, pure: which templates reach a node (`reaching_templates`), what to do with each plan row (`plan_actions`: make, relink, unlink), the meters a template needs (`needed_meters`), whether it applies (`applies`), and why a plan stops (`stop_remark`) (§ 5.3, § 5.4). |
| `backend/pm_plans_core.py` | Reshaped: only the plan row's fields (`assignee_id`, `last_done_on`, `last_done_meter`) and their rules; the item, trigger and words parts move to `pm_templates_core.py`. |
| `backend/pm_plans.py` | Reshaped: the card list, the plan detail, *Attach* (`POST /api/pm/plans`), the plan settings (`PUT /api/pm/plans/<id>`), *Remove from this machine* (`POST /api/pm/plans/<id>/remove`), `sync_node` (§ 5.4). `meter_choices`, `/meter-choices` and `/item-check` go. |
| `backend/pm_jobs.py` | `PLAN_SELECT` (the plan row with its template, one SELECT, § 5.7); `resolve_meters` (§ 5.3); `settle_plan_job` and `schedule_inputs` read the template and the resolved meter; the job copies its meter node (`pm_jobs.meter_equipment_id`, § 4.1); `JOB_FROM` joins the template; `generate`'s candidates; `_settle_one` becomes public `settle_one(conn, plan_id, actor, *, keep_reschedule=True)` (BR1-03: the run passes `RUN_ACTOR`, a template save the engineer); `_meter_base` checks the base's meter (§ 5.3); `job_changes` compares `meter_equipment_id` too; `_alert_one` reads the job's meter copy and passes the plan's in force (no stop remark) as `alerts_core.pm_alert_due`'s `plan_active`; `plan_schedules` resolves the card's meters in one pass. |
| `backend/pm_jobs_core.py` | `decide` takes the plan's stop remark (None = in force) in place of `plan_active`; the remarks (§ 5.4). |
| `backend/pm_work.py` | Imports `item_limits_text` and `meter_label` from `pm_templates_core` (they move with the item rules). *Start*: resolves each *Meter reading* item's meter (409 when one is missing, § 5.7), copies the template's active items and name; `_done_meter` and the reschedule read the job's meter copy. |
| `backend/pm_work_core.py` | `COPIED_FIELDS` and `result_rows`: `template_item_id`, `reading_kind`, the resolved `meter_equipment_id`. |
| `backend/app.py` | Registers `pm_templates_bp`. |
| `backend/equipment.py` | The LOCK ORDER list: (6g) the template row; (6e)'s text (§ 5.9). |
| `backend/alerts.py`, `backend/alerts_core.py` | None expected: `pl_title` stays an alias in `JOB_FROM` (§ 5.7). To verify by the coder. |

### Tests

| File | Change |
|---|---|
| `backend/tests/test_migration_v51.py` … `test_migration_v56.py` | Removed (plain `rm`), replaced by `test_migration_v57.py`. |
| `backend/tests/test_migration_v57.py` | **New** (§ 8.1). |
| `backend/tests/test_pm_templates_core.py` | **New**: the template's rules (from `test_pm_plans_core.py`'s trigger and item tests, with the reading kinds). |
| `backend/tests/test_pm_templates_api.py` | **New**: the template routes, the after-commit settle. |
| `backend/tests/test_pm_links_core.py` | **New**, pure, written and green first. |
| `backend/tests/test_pm_plans_core.py`, `test_pm_plans_api.py` | Rewritten: the plan row's rules; the card, attach, settings, remove. |
| `backend/tests/pm_helpers.py` | **New**: one shared set-up, `plan_on(client, node, **template_fields)` (a template, linked to the node, returns the plan) and its fixtures (§ 8.3). Replaces `test_pm_plans_api.create` and `test_pm_work_api.plan_with` as the import point. |
| `test_pm_generate.py`, `test_pm_jobs_api.py`, `test_pm_work_api.py`, `test_pm_verify_api.py`, `test_pm_reschedule_api.py`, `test_pm_alerts.py` | Set-up through `pm_helpers`; the SQL that writes moved columns (`set_plan`, `test_pm_generate.alone`, `test_pm_alerts.py:249,385`'s `set_plan(..., active=0)`, `test_pm_reschedule_api.py`'s trigger UPDATE) writes the template (`pm_templates.active`, the trigger) or `pm_plans.linked`; the imports of `PLAN_INACTIVE_REMARK` follow the new remarks; `test_pm_work_api.py` gains the two reading kinds and the parent tick (§ 8.2). |
| `test_equipment_api.py` | `test_scrapping_with_a_started_pm_job_is_409`: its `INSERT INTO pm_plans` makes a template and a plan row. |
| `backend/tests/conftest.py` | `_TABLES`: `pm_template_links`, `pm_template_items`, `pm_templates` in; `pm_plan_items` out; the order respects the foreign keys. |
| `test_pm_schedule_core.py`, `test_pm_jobs_core.py`, `test_pm_work_core.py`, `test_alerts_core.py` | Pure: `decide`'s new argument in `test_pm_jobs_core.py`; field names only elsewhere, if any. |
| `test_rbac.py` | No change: no key is added (Q18.4 a). |

### Frontend

| File | Change |
|---|---|
| `frontend/src/views/masters/PmTemplatesPanel.vue` | **New**: the list, *Add PM template*, the inactive ones behind *Inactive templates (n)*. |
| `frontend/src/views/PmTemplateView.vue` | **New**: the template page (routes `pm-template-new` `/masters/pm-templates/new`, `pm-template` `/masters/pm-templates/:id`), built from `PmPlanView.vue`'s editor parts. |
| `frontend/src/views/PmPlanView.vue` | Becomes the machine's plan page (§ 5.10); its editor parts move to `PmTemplateView.vue`. The route `pm-plan-new` goes. |
| `frontend/src/views/equipment/PmItemDialog.vue` → `frontend/src/views/pm/PmItemDialog.vue` | Moved beside the other PM dialogs (BR1-18). The reading kind, the meter type pick, the parent tick; checks through `POST /api/pm/template-item-check`. |
| `frontend/src/views/equipment/PmAttachDialog.vue` | **New**: *Attach PM template* (a template pick, the meters it would use here). |
| `frontend/src/views/equipment/PmPlansCard.vue` | Sources, *Attach PM template*, "Does not apply" lines. |
| `frontend/src/views/MastersView.vue` | The section `pm_templates` ("PM templates", perm `equipment:read`). |
| `frontend/src/router/index.js` | The two template routes; `pm-plan-new` removed. |
| `frontend/src/utils/pmLabels.js`, `frontend/tests/pmLabels.test.js` | The template form and body (from `planForm` / `planBody`), the reading-kind words, the source words, the plan settings body. |
| `PmJobView.vue`, `PmJobsView.vue`, `PmJobRow.vue` | The job's name (its copy, else the template's); a *Meter reading* item's meter line. |
| `frontend/e2e/support/pm.js` | **New** (shared code, settings: *Shared code*): `pmPlanByApi(request, node, template)` makes a template and attaches it. |
| `frontend/e2e/pm-plans.spec.js` | Rewritten (attach, the plan page, remove). |
| `frontend/e2e/pm-templates.spec.js` | **New** (the list, the template page, the reading kinds). |
| `pm-job.spec.js`, `pm-jobs.spec.js`, `pm-reschedule.spec.js`, `pm-verify.spec.js`, `me.spec.js`, `screens.spec.js` | Set-up through `e2e/support/pm.js`; `pm-job.spec.js:236`'s plan PUT becomes a template PUT; `screens.spec.js` shoots the template page and the attach dialog. |

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: `pm_templates`, `pm_template_items` move in from `planned`;
  `pm_template_links` new; `pm_plan_items` out; `pm_plans`, `pm_jobs`, `pm_job_results` notes
  updated. Then `tooling\schema-docs.bat write` (the step's `YANTRA_TEST_RUN`), `check` exits 0.
- `.claude/CLAUDE.md` § SMTW-Review: *PM plans (S096)* becomes *PM templates and plan rows
  (S104)* (§ 8.6); *PM job results (S098)* names the template's items and the meter copy; *PM jobs
  (S097)* names the stop remarks.
- `docs/Plan.MD` § 4.3: the "Built (S096 …)" paragraph becomes "Built (S104 …)", in the words of the
  "Decided 02-11-2026" block; the bullet "Which meter a plan uses (*Proposed*, 16-10-2026)" becomes
  "Decided 02-11-2026 (S104): a template names a meter type, matched on the machine's own meters; a
  parent's only with the template's tick" (BR1-06).
- `docs/Maintenance-Philosophy.md` § 8: "a plan names one meter, its own node's or an ancestor's — a
  gearbox on the extruder's hours" becomes the same rule, keeping the example: "the gearbox's
  greasing is a template on the extruder, or the gearbox gets its own hour meter where its hours
  differ (ISO 14224)" (BR1-06).
- `docs/roadmap/R03-pm.md`: R03.18 → S104 (the orchestrator, at planning).

## 4. Data model

### 4.1 Migration v57

Numbered 57, above every version a dev or test database holds (v56), as S087's v50 replaced
v42–v47 (SMTW-WebApp-Base § Migration squashing). Three shapes:

- **Fresh** (a new install, e2e, the tests' new databases) and **production at v50**: the drops
  find nothing; the creates make every table.
- **Dev and test at v51–v56** (rows from tests and hand trials only): step 1 drops the six tables,
  then the creates make the final shape. The `v51`–`v56` rows of `db_version` stay as history.
- **No precondition:** production holds none of these tables (v50). Every statement is safe to run
  twice (`DROP TABLE IF EXISTS`, `CREATE TABLE IF NOT EXISTS`), so a half-applied v57 re-runs.
  A half-applied v57 that had already created a table and then fails would drop it again on the
  re-run: harmless, it holds no rows yet.

Statements, in order:

1. `DROP TABLE IF EXISTS pm_job_results, pm_job_events, pm_jobs, pm_plan_items, pm_plans` (children
   first: their foreign keys). No other table references them (checked: `grep "REFERENCES pm_"`
   finds only these five tables' own keys).
2. **`pm_templates`**: `id`; `name` VARCHAR(100) NOT NULL, `uq_pm_templates_name`; `performer`
   ENUM('maintenance','operator') default maintenance; `needs_verification` TINYINT(1) default 1;
   `trigger_kind` ENUM('calendar','meter','both','before_use'); `calendar_every` SMALLINT NULL;
   `calendar_unit` ENUM('day','week','month','year') NULL; `meter_type_id` INT NULL (FK
   `meter_types`); `meter_every` DECIMAL(14,3) NULL; `meter_from_parent` TINYINT(1) NOT NULL
   default 0; `active` default 1; `created_at`, `created_by`, `updated_at`, `updated_by`. CHECKs
   from v51's, without the meter node: `chk_pm_templates_calendar` (as `chk_pm_plans_calendar`),
   `chk_pm_templates_meter` (`meter_type_id` set exactly for `meter` / `both`; `meter_every` with
   it, > 0; `meter_from_parent` = 0 without a meter type).
3. **`pm_template_items`**: v51's `pm_plan_items` with `template_id` (FK `pm_templates`) for
   `plan_id`, no `meter_equipment_id`, plus `reading_kind` ENUM('measurement','meter') NULL and
   `meter_from_parent` TINYINT(1) NOT NULL default 0. Index `ix_pm_template_items_template
   (template_id, active, position)`. CHECKs:
   - `chk_pm_template_items_reading`: `reading_kind` set exactly when `item_type = 'reading'`;
   - `chk_pm_template_items_kind`: a `measurement` has no `meter_type_id` and `meter_from_parent`
     = 0; a `meter` has `meter_type_id` and no `unit`, `min_value`, `max_value` (D6);
   - `chk_pm_template_items_position`, `chk_pm_template_items_limits` as v51's.
4. **`pm_template_links`**: `id`; `template_id` (FK); `target_kind`
   ENUM('class','type','model','equipment'); `class_id` (FK `equipment_classes`), `type_id` (FK
   `equipment_types`), `model_id` (FK `equipment_models`), `equipment_id` (FK `equipment`), all
   NULL; `target_id` INT AS (COALESCE(class_id, type_id, model_id, equipment_id)) PERSISTENT;
   `open_target_id` INT AS (CASE WHEN active = 1 THEN COALESCE(class_id, type_id, model_id,
   equipment_id) END) PERSISTENT (self-contained, as v52's `open_plan_id`; BR1-09); `active` default
   1; `created_at`, `created_by`, `removed_at`, `removed_by`. CHECKs: `chk_pm_template_links_target`
   (exactly the column of `target_kind` is set, the other three NULL);
   `chk_pm_template_links_removed` (`removed_at` and `removed_by` set exactly when `active` = 0).
   Keys: `uq_pm_template_links_open (template_id, target_kind, open_target_id)` (one active link per
   template and target; NULLs pass, so removed links pile up as history, as `uq_pm_jobs_open_plan`
   does); `ix_pm_template_links_target (target_kind, target_id, active)` (R03.19's lookups).
   A removed link is set inactive, never deleted; adding it again inserts a new row.
5. **`pm_plans`** (reshaped): `id`; `equipment_id` (FK); `template_id` (FK); `uq_pm_plans_template
   (equipment_id, template_id)`; `assignee_id` (FK people) NULL; `last_done_on` DATE NULL;
   `last_done_meter` DECIMAL(14,3) NULL; `seed_meter_equipment_id` INT NULL (FK `equipment`) and
   `seed_meter_type_id` INT NULL (FK `meter_types`): the meter the seed was entered for, written with
   `last_done_meter` (BR1-01); `linked` TINYINT(1) NOT NULL default 1 (kept by `sync_node`);
   `linked_at` DATETIME NOT NULL (written at make and at relink; the schedule's start when there is
   no base job and no seed, BR1-05); `not_for_machine` TINYINT(1) NOT NULL default 0, `not_for_reason`
   VARCHAR(500) NULL, `not_for_by` VARCHAR(100) NULL, `not_for_at` DATETIME NULL (R03.19's;
   written by nothing in S104); `created_*`, `updated_*`. No title, trigger, performer, flag, meter
   or `active` column. CHECKs: `chk_pm_plans_seed` (`last_done_meter` NULL or ≥ 0; the two seed
   meter columns set exactly when `last_done_meter` is);
   `chk_pm_plans_not_for` (reason, by and at set exactly when `not_for_machine` = 1). The rule
   "an assignee only on a maintenance plan" and "no meter seed without a meter trigger" move to the
   API (§ 5.5), since the performer and trigger live on the template.
6. **`pm_jobs`**: v52–v56's final shape (with v53's, v54's, v55's and v56's columns and CHECKs),
   plus three columns:
   - `meter_equipment_id` INT NULL (FK `equipment`) and `meter_type_id` INT NULL (FK
     `meter_types`): the meter the due point was computed on (§ 5.3), copied with the due copies at
     create and refresh; NULL without a meter trigger; both or neither. `chk_pm_jobs_windows` gains:
     `due_meter` NULL or `meter_equipment_id` set; `(meter_equipment_id IS NULL) = (meter_type_id
     IS NULL)`. They are kept on a done or skipped job as the base's meter (BR1-01);
   - `title` VARCHAR(100) NULL: the template's name, copied at *Start* (D8); NULL on a job not
     started.
7. **`pm_job_events`**: v52's, unchanged.
8. **`pm_job_results`**: v53's, with `template_item_id` (FK `pm_template_items`) for
   `plan_item_id` (`uq_pm_job_results_item (job_id, template_item_id)`), plus `reading_kind`
   ENUM('measurement','meter') NULL copied at *Start*. `meter_equipment_id` stays: the node whose
   meter the reading is saved on, resolved at *Start* (D7; a departure from R03.18's text, which
   dropped it before the parent tick was decided). `chk_pm_job_results_reading` gains:
   `reading_kind = 'meter'` exactly when `meter_type_id` is set.

### 4.2 What is computed, never stored

- Whether a plan is **in force**: `linked` = 1, `not_for_machine` = 0, its template active
  (`pm_links_core.stop_remark`).
- Whether a template **applies** to a machine, and the meter each needed type resolves to
  (§ 5.3): judged live from the meters in force.
- The trigger in words, the standing (S097 D4), as before.

## 5. Rules

### 5.1 The template fields

S096 § 5.1's plan fields, moved to the template, with these changes:

- `name` (S096's *title*): required, 1–100 characters after collapsing spaces, unique among all
  templates, active or inactive (`uq_pm_templates_name` → 409 on `name`: "A PM template with this
  name already exists, active or inactive. Choose another name, or reactivate that template.").
- The trigger: `trigger_kind` (`calendar`, `meter`, `both`; `before_use` refused as S096),
  `calendar_every` / `calendar_unit` (S096's bounds, `CALENDAR_MAX`), `meter_type_id` (a meter type
  of kind *counter*, else 400 `COUNTER_NEEDED`), `meter_every` (> 0, the type's decimals),
  `meter_from_parent` (boolean; only with a meter type, else 400 "Tick By meter first.").
- `performer`, `needs_verification` (default by performer, S096's `default_verification`).
- No assignee, no *Last done* (they are the plan row's, § 5.5).
- `active`: `{active}` alone deactivates or reactivates (§ 5.6).
- A `PUT` without a field keeps it; a field equal to the stored one is not written; a change of
  nothing writes nothing (S096's `plan_changes`).
- **The schedule fields** (`SCHEDULE_FIELDS`): `trigger_kind`, the calendar fields, `meter_type_id`,
  `meter_every`, `meter_from_parent`. A save that changes one drops the open jobs' reschedules
  (S101 D4), on every plan of the template.

### 5.2 The items and the two reading kinds

S096 § 5.4's rules (1–50 active items, `position` from the list order, synced by id, a removed item
set inactive, never deleted; *Task*, *Check*, *Reading*; text, help text, photo), with the reading
kinds (mock-up 14):

| | *Measurement* | *Meter reading* |
|---|---|---|
| `reading_kind` | `measurement` | `meter` |
| Unit | optional, ≤ 20 characters | none: the meter type's unit (400 `METER_UNIT` when sent) |
| Min / Max | optional, Min ≤ Max | none (D6): the machine's meter's own limits in force show on the job (400 "A meter reading uses the machine's meter limits. Clear Min and Max.") |
| Meter type | none (400 `ONLY_METER_READING`: "Only a meter reading names a meter type.") | required; a meter type of kind *counter* or *gauge* (400 "Choose a counter or gauge meter type.") |
| Parent tick | none | `meter_from_parent`, default false |
| On the job | the value stays on the job | the value is saved as a meter reading (source `pm`) through `meters.write_reading`, as S098 § 5.5 |

- A *Reading* item without `reading_kind`: 400 "Choose Measurement or Meter reading." A *Task* or
  *Check* with any reading field: 400 `ONLY_READING` (S096's).
- Changing an item's kind is a change of that item (same id); a started job keeps its copy.

### 5.3 The meter match and whether a template applies

- **The needed meters** (`pm_links_core.needed_meters(template, items)`): the trigger's
  `(meter_type_id, meter_from_parent)` when the trigger has a meter, and each active *Meter reading*
  item's. One type named twice is one need; it may use the parent only when **every** mention ticks
  it (the stricter wins, so a tick on one item never moves another's meter).
- **Resolution** (`pm_jobs.resolve_meters(cur, node, needs)` → `{meter_type_id: node_id or None}`):
  1. the node's own meter of the type in force (`meters.meter_in_force(cur, node_id, model_id,
     type)`: the model's meters plus the node's own, `meters_core.effective_meters`);
  2. only when the need ticks the parent: the parent, then the grandparent (the tree has three
     levels, Plan § 4.1), the first that has the type in force;
  3. else None.
  One meter per type per node (`uq_model_meters`, `uq_node_meters`), so each step gives one meter or
  none: nothing to pick, nothing stored on the plan.
- **Applies** (`pm_links_core.applies(needs, resolved)` → the missing types, empty when it applies):
  pure, its tests first.
- **Where it is resolved:** the settle (the daily run, a template save, a plan save, attach), the
  card and the plan page (in one pass over the node's subtree and its ancestors, `meters_with_last`,
  no query per plan), the attach dialog's preview, *Start*.
- **A job carries its meter:** create and refresh copy the resolved trigger meter's node to
  `pm_jobs.meter_equipment_id` with the due copies. The list, the job page, the alert scan, *Mark
  job done* and the reschedule read the job's copy (one join, as today's `pl.meter_equipment_id`).
  A meter added or removed under an open, not started job is picked up at the next settle (a
  refresh rewrites the copies; a missing type cancels the job).
- **Does not apply:** the plan row stays (it is linked); it makes no job; its open, not started job
  is cancelled with the line "Does not apply: no Brake air gap meter on EOT03." (`stop_remark`; the
  type names in the template's order, joined with "or" past one: "no Run hours or Oil temperature
  meter on HP003"). A started job keeps its copy (S098 D9).
- **The meter base follows the meter** (BR1-01). The schedule's base value must be a value of the
  meter the trigger resolves to now:
  - the last base job's `done_meter` is used only when that job's copied meter
    (`pm_jobs.meter_equipment_id`, `pm_jobs.meter_type_id`, § 4.1 item 6) equals the meter the
    trigger resolves to now (node and type);
  - else the seed (`last_done_meter`) is used, only when no base job exists and its
    `seed_meter_equipment_id` and `seed_meter_type_id` equal the resolved node and type;
  - else the start value falls back to S095 D9's rule (`_meter_base`'s path without a seed: the latest
    reading of the resolved meter at or before the base time, else the first after it);
  - so a part that gains its own meter, or a template whose meter type changes, counts on the new
    meter from its readings, never from a value of another meter;
  - the plan page shows, when a seed is stored but not used: "Last done meter value was entered for
    HP002's Run hours. Enter it again for the meter this plan uses now."
- **The meter seed:** `last_done_meter` is a value of the trigger meter on this machine; with a
  trigger meter that does not resolve, the seed is kept and unused.

### 5.4 Plan rows and `sync_node`

- **Which templates reach a node** (`pm_links_core.reaching_templates(node_facts, links)`): pure;
  in S104 only the active `equipment` links naming the node. R03.19 adds class, type and model.
- **What to do with each plan row** (`pm_links_core.plan_actions(reaching_ids, plans)` → make,
  relink, unlink lists): a reaching template with no row → **make**; a row with `linked` = 0 whose
  template reaches → **relink**; a row with `linked` = 1 whose template no longer reaches →
  **unlink**. A row is never deleted.
- **`pm_plans.sync_node(conn, node_id, actor)`**: reads the node's links and plans plainly, asks
  `plan_actions`, then writes each plan in its own transaction (§ 5.9): make (node shared, insert,
  `uq_pm_plans_template` as the guard: a 1062 means another request made it, and the row is then
  settled), relink / unlink (plan (6e), node shared, `linked` written), then
  `settle_plan_job` in the same transaction. On a 1062 the make transaction is rolled back, and the
  row (read plainly by `(equipment_id, template_id)`) takes the relink path in a new transaction,
  (6e) first, so no job is written without its plan's lock (BR1-02). Called by *Attach* and *Remove*; R03.19 adds its
  other callers.
- **A new plan row** has no assignee (R03 answer 4a) and no *Last done*, so its first job counts
  from the day it is linked (S095's `created_on`, now `linked_at`'s date). A relinked row keeps its
  assignee, its seed and its jobs (R03 Q19.1 a), and gets a new `linked_at`: with no base job and no
  seed, it counts from the relink, so a plan removed for months does not come back overdue at once
  (BR1-05). With a base job or a seed, the count goes on from them, as before the removal.
- **Why a plan stops** (`pm_links_core.stop_remark(template_active, linked, not_for_machine,
  missing_type_names, node_code)` → None, or the remark): in this order — "The template was
  deactivated.", "The template was removed from this machine.", "Not for this machine: <reason>"
  (R03.19), "Does not apply: no … meter on <code>." `pm_jobs_core.decide` takes it in place of
  `plan_active`: a remark cancels a due job with that remark, and makes no job (S097 § 5.5's table
  otherwise unchanged; the scrapped remark keeps its place after it).

### 5.5 Attach, the plan settings, remove

- **Attach** (`POST /api/pm/plans {equipment_id, template_id}`): `pm_plan:edit` at the node's site
  (403 naming the site), equipment:read's units (404), the node not scrapped (409
  `SCRAPPED_MESSAGE`), the template active (409 "This template is inactive. Reactivate it in Masters
  › PM templates first."), no active `equipment` link of this template on this node (409 "This
  template is already attached to this machine."). It inserts the link, then calls `sync_node`.
  A template that does not apply may be attached: the answer and the card say why it makes no job.
  Answer: the plan's detail (§ 6), 201.
- **The plan settings** (`PUT /api/pm/plans/<id>`): `assignee_id`, `last_done_on`,
  `last_done_meter`, any subset; `pm_plan:edit` at the node's site; scrapped 409. Rules from S096
  § 5.1 and § 5.3:
  - `assignee_id`: null, or an active person with an `ASSIGNABLE_ROLES` role at the node's site
    (400 `ASSIGNEE_AT_SITE`); refused on an *operator* template's plan (400
    `OPERATOR_NO_ASSIGNEE`);
  - `last_done_on`: from 01-01-2000 to today (IST), or null (400 `LAST_DONE_DATE`);
  - `last_done_meter`: ≥ 0, the trigger type's decimals, or null; refused when the template has no
    meter trigger (400 "This template has no meter trigger. Clear the meter value.") and when the
    trigger meter does not resolve on this machine (400 "This machine has no Run hours meter. Add
    the meter first."); saved with the resolved meter in `seed_meter_equipment_id` and
    `seed_meter_type_id` (BR1-01); null clears all three;
  - any other field is refused (400, `field` = its name; D12), with the message:

    | Field | Message |
    |---|---|
    | `items`, `title`, `performer`, `needs_verification`, the trigger fields | "Change the work on the template." |
    | `template_id`, `equipment_id` | "A plan stays on its machine and template. Remove it and attach another." |
    | anything else | "Unknown field: <name>." |
  - A template changed from *maintenance* to *operator* keeps each plan's stored assignee but uses
    none (`pm_jobs._job_assignee` gives None for an operator template, so the open job's assignee is
    cleared at the settle with its `assignee_changed` line); the plan page shows "Operator plans
    have no assignee." and its *Save plan* sends `assignee_id: null`. Changed back, the stored
    assignee is used again. Rejected: clearing the plans' assignees in the template's transaction
    (it would write plan rows under (6g)).
  - A change of `last_done_on` or `last_done_meter` drops the open job's reschedule (S101 D4, as
    S096's `SCHEDULE_FIELDS`); an assignee change does not. Then `settle_plan_job`.
- **Remove from this machine** (`POST /api/pm/plans/<id>/remove`): `pm_plan:edit` at the node's site;
  the plan's template has an active `equipment` link to this node, else 409 "This plan does not
  come from a link to this machine." (R03.19's sources). It sets that link inactive (`removed_at`,
  `removed_by`), then `sync_node` unlinks the plan and cancels its open, not started job ("The
  template was removed from this machine."). A started job is left to finish (S097: the settle
  leaves `in_progress` alone). Allowed on a scrapped node? No: 409 `SCRAPPED_MESSAGE`, as every PM
  write on it (the scrap cancels its jobs already).
- Attaching the template again relinks the same plan row with its history (R03 Q19.1 a).

### 5.6 A template change reaches the plans

- The template save (create, change, deactivate, reactivate) commits first: the template row and
  its items, in one transaction (§ 5.9).
- Then, outside that transaction, each plan of the template (`linked` = 1 or with an open job,
  ordered by id) is settled in its own transaction through `pm_jobs.settle_one(conn, plan_id,
  actor(), keep_reschedule=…)` — the daily run's function, made public with an `actor` argument, so
  the job's timeline lines name the engineer, not `pm_generate` (BR1-03); `keep_reschedule=False`
  when the save changed a schedule field (§ 5.1).
- One plan's failure is logged and the others go on (as `generate`); the answer is still the saved
  template (200 / 201), since the change is committed. The next morning's run settles any plan a
  failed or cut request left (R03.18). A lost connection ends the loop; the saved template stands,
  and the client sees a 503 (BR1-12): the page says "The template may be saved. Reload the page to
  see it."; a repeated PUT with the same body writes nothing and settles the plans again.
- The answer reports `plans_settled` (count) and `plans_failed` (count) so the page can say "Saved.
  N machines will update at the next daily run." with N = `plans_failed`, when it is above 0.
- **A confirmation before a schedule change on several machines** (BR1-08): when a schedule field
  (§ 5.1) changed and `plan_count` > 1, *Save template* first asks "Change the schedule for N
  machines? Their jobs move to the new interval. Jobs already started are not changed." (ISO 55001
  § 8.2: a controlled change). Other changes save at once.
- A deactivation cancels each plan's open, not started job ("The template was deactivated.");
  a reactivation lets each plan make its job again at the settle.
- Cost: a template on 50 machines settles 50 plans, about 50 small transactions; acceptable for the
  ~50-user scale (CLAUDE-COMMON *Right-sized*). Not a background task: the engineer sees the moved
  jobs at once (R03.18).

### 5.7 The jobs read the template

- `pm_jobs.PLAN_SELECT`: the plan row with its template's columns under the old names, so
  `pm_schedule_core.next_due`, `schedule_inputs` and `decide` take the same dict: `pl.*`,
  `tp.name AS title`, `tp.performer`, `tp.needs_verification`, `tp.trigger_kind`,
  `tp.calendar_every`, `tp.calendar_unit`, `tp.meter_type_id`, `tp.meter_every`,
  `tp.meter_from_parent`, `tp.active AS template_active`. `LOCK_PLAN` stays `SELECT * FROM pm_plans
  WHERE id = %s FOR UPDATE` (6e); the joined row is read plainly after it.
- `settle_plan_job`: reads `PLAN_SELECT`, resolves the needs (§ 5.3), computes `stop_remark`, then as
  today; `schedule_inputs` reads the resolved trigger meter node in place of the plan's column.
- `JOB_FROM`: joins `pm_templates tp`; `pl_title` = `COALESCE(j.title, tp.name)`;
  `pl_active` = the plan in force (linked, not *Not for this machine*, template active);
  `pl_needs_verification`, `pl_performer`, `pl_trigger_kind` from the template; the meter from
  `j.meter_equipment_id`; `item_count` from the template's active items. `alerts_core` and
  `alerts.py` then need no change.
- `generate`'s candidates: plans in force and linked (`linked` = 1, `not_for_machine` = 0, template
  active), plus any plan with a due job (so a stopped plan's leftover job is cancelled).
- *Start* (`pm_work.start_job`): after its locks (§ 5.9), reads the template's active items and the
  template's name; resolves each *Meter reading* item's need; a missing one → 409 "This job cannot
  start: no Brake air gap meter on EOT03. Ask an engineer." (the next settle cancels the job); copies
  the items (`template_item_id`, the item fields, `reading_kind`, the resolved
  `meter_equipment_id`) and writes `title` on the job.
- An item save, *Mark job done*, verify, send back, reschedule, skip: unchanged rules; they read the
  result's or the job's meter copy, and the template through `PLAN_SELECT` where they read the plan
  (`needs_verification` at *Mark job done* from the template, read plainly after (6e); D10).
- The job page of a due job shows the template's active items now ("These are the plan's items
  now…", S098's line, kept).

### 5.8 Permissions

| Route / button | Key | Where checked |
|---|---|---|
| Template list, detail (`GET /api/pm/templates…`), the Masters section | `equipment:read` | `require_perm` (held at any site); a template is a site-less master, readable by every role that reads equipment |
| Template create, change, deactivate, item check | `pm_plan:edit` | `require_perm` (held at any site; R03 Q18.4 a); `can_edit` in the answers |
| Card list, plan detail | `equipment:read` | the node through `load_node_for_user` (404 outside the user's units), as S096 |
| Attach, plan settings, remove | `pm_plan:edit` | at the node's current site (`has_perm_at`, 403 naming the site) |
| Job routes | unchanged (`pm_job:read`, `pm_job:work`, `pm_job:verify`) | unchanged |

- No new key; `pm_plan:edit` stays in `SITE_SCOPED` (it is checked at the site for plans and by
  the union for templates, as `procedure:edit` for a class lesson, S075).
- IT admin reads templates and plans, writes nothing (it holds `equipment:read`, not
  `pm_plan:edit`; R03 Q2.2 a).
- The Masters nav item shows only to holders of an edit key (`navigation.js`, S064 UX-12), so a
  technician never sees *Masters › PM templates*. He reaches a template from the plan page's *Open
  template*: the routes `pm-template` and `pm-template-new` are not nav items, so `canOpenRoute`
  lets them open and the API is the gate (BR1-15).
- An engineer of site A edits a template that site B's machines use (Q18.4 a, accepted): the
  template is the plant's standard. Each save names its writer (`updated_by`).

### 5.9 Locks

Lock numbers are equipment.py's. New: **(6g) the PM template row** (`pm_templates`): taken
`FOR UPDATE` only by a template save, first in its transaction, with no other row lock but its items'
writes and the shared foreign-key locks on meter types; taken `LOCK IN SHARE MODE` by *Attach*.
Nothing that holds (6g) exclusive waits on a plan, a job, a node or a counter, so it closes no cycle.
The template save, holding (6g), takes the meter types shared through its items' foreign keys: a
lower number after a higher one, one way only, since `masters.py`'s meter-type writes never wait on a
template row. The (6g) entry in `equipment.py`'s list says so, as (6) after (6e) is stated (BR1-16).

1. **Template create**: plain reads (the meter types) → the template insert (`uq_pm_templates_name`
   the guard: 1062 → 409) → the item inserts → commit → § 5.6's settles (none for a new template).
2. **Template change**: (6g) `SELECT * FROM pm_templates WHERE id = %s FOR UPDATE`, the first
   statement (404) → plain: the meter types, the active items (every item write holds (6g)) →
   `update_row`, the item inserts, updates, deactivations → commit → § 5.6: per plan, (6e) → (1)
   shared → plain reads (the template read here sees the committed change) → the job write.
3. **Attach**: (1) the node LOCK IN SHARE MODE (404) → (6g) the template LOCK IN SHARE MODE (404;
   its `active` decides the 409) → plain: access (404 / 403), scrapped from the locked node, the
   active link → the link insert (`uq_pm_template_links_open` the guard: 1062 → the 409 "already
   attached") → commit. Then `sync_node` (step 5). The template's shared lock makes a concurrent
   deactivation either wait for the attach (and its after-commit settle then sees the new plan) or
   commit first (and the attach sees it inactive).
4. **Remove**: (6e) the plan FOR UPDATE (404) → (1) the node shared → plain: access, the link →
   the link UPDATE (its row, by id, exclusive; nothing else locks a link) → commit → `sync_node`.
5. **`sync_node`**, per plan, its own transaction: make: (1) shared → the insert (FK shared on the
   node, the template) → `settle_plan_job`; relink / unlink: (6e) → (1) shared → plain → the
   `linked` and `linked_at` UPDATE → `settle_plan_job`. Each plan's transaction is the S097
   daily-run shape. A make's 1062: rollback, then the relink path (§ 5.4, BR1-02).
6. **Plan settings**: (6e) → (1) shared → plain: access, scrapped, the template (`PLAN_SELECT`),
   the assignee → `update_row` → `settle_plan_job`.
7. **The daily run, the alert scan, the job routes**: unchanged; the template is read plainly after
   (6e). A template save committed between the run's plain read and its commit is settled again by
   the save's own after-commit settle, which waits on (6e): the last writer sees the newest
   template.

Rollback of an after-commit settle undoes only that plan's job write; the template stays saved.

### 5.10 Screens

- **Masters › PM templates** (`PmTemplatesPanel.vue`): rows "Press — monthly hydraulic check ·
  Every month or 250 h, whichever comes first · 7 items · 3 machines"; *Add PM template* (only with
  `pm_plan:edit` anywhere, `can_add` in the answer); *Inactive templates (n)* below, folded. A row
  opens the template page. The empty state: "No PM templates yet. Add one to start planned
  maintenance." (with the key) or "No PM templates yet." (without).
- **The template page** (`PmTemplateView.vue`, mock-up 09): S096's plan editor without the
  equipment, the assignee and *Last done*: *Name*, *Done by*, *An engineer verifies each job*,
  *When is it due?* (*By calendar: every N days / weeks / months / years*; *By meter: every N of*
  a counter meter type; the tick *If the machine has no meter of this type, use the meter from a
  parent node*), the note "The template names the meter type. Each machine uses its own meter of
  that type. A machine without one: the template does not apply there.", the items table (#, Type,
  Item, "Limits / meter type", Photo), *Add item*, *Move up* / *Move down*, the change note of § 1
  item 2, *Save template*, *Deactivate template* / *Reactivate template* (with confirmation:
  "Deactivate this template? Its N machines stop getting jobs. Jobs already started can be
  finished."). Header line: "Used on N machines". Read-only for a reader without the key.
  **One count** (BR1-14): "Used on N machines", `plan_count` and the deactivation's N count the
  template's plan rows with `linked` = 1 (a plan that does not apply counts; an unlinked one does
  not). The card's header "PM plans (N)" counts the node's and its parts' linked plans the same way.
- **The item dialog** (`PmItemDialog.vue`, mock-up 14): for *Reading*, the radio "What kind of
  reading?" — *Measurement* ("A value with its own unit and limits. It stays on the job only.") /
  *Meter reading* ("Saved as a reading of the machine's own meter of this type, as if logged on
  the Readings sheet."); *Measurement* shows *Unit*, *Min*, *Max*; *Meter reading* shows *Meter
  type* (counters and gauges, from `GET /api/masters/meter-types`), the parent tick, and "Unit and
  limits come from each machine's meter.". *Save item* checks through
  `POST /api/pm/template-item-check` (S096 D2's pattern).
- **The PM card** (`PmPlansCard.vue`, mock-up 11): each plan "Press — monthly hydraulic check ·
  This machine · Every month or 250 h, whichever comes first", then the schedule line (S097) or
  "Does not apply: no Run hours meter on HP003" (muted, with the reason) or "Removed from this
  machine" (an unlinked plan: listed behind *Not in use (n)*, as S096's *Inactive plans*); a part's
  plan names the part ("MOT014 · …"). *Attach PM template* (with `pm_plan:edit` at the node's site,
  not scrapped).
- **The attach dialog** (`PmAttachDialog.vue`): a select of the active templates by name (each with
  its trigger in words); when one is picked, the meters it would use here, as the plan page shows
  them, or "Does not apply here: no … meter on HP003. You can attach it; it makes no job until the
  meter is added."; *Attach template*. One tap after the pick. Refusals beside the select.
- **The plan page** (`PmPlanView.vue`, mock-up 11): the template's name with *Open template*, its
  summary ("7 items · Maintenance · an engineer verifies"), the trigger in words, the items
  read-only; "Attached to this machine" (R03.19 brings mock-up 11's "Reaches this machine from: Class …" for the
  other sources; BR1-13); *Assign jobs to* (S096's pick; hidden on an
  operator template, with "Operator plans have no assignee."), *Meters this plan uses* (read-only
  lines), *Last done (before Yantra)* (date; meter value when the template has a meter trigger);
  the note "The work comes from the template. To change it for this machine only, attach a
  template of its own."; *Save plan*; *Remove from this machine* (confirmation: "Remove this
  template from HP003? Its job that has not started is cancelled. Its history stays, and attaching
  it again brings it back."). The open job and the done jobs as S097 shows them.
- **Job screens**: the name is the job's copy, else the template's; a *Meter reading* item shows
  "Meter reading · HP003's Run hours" and the meter's limits in force; a *Measurement* "Measurement
  · 180–200 bar".
- **Phone**: every dialog fits (`expectDialogFits`); the template page's items show as S096's
  editor does: a list below 768 px and a table above (`pm-item-list` / `pm-items`; BR1-17).

### 5.11 The database down

Every new route answers 503 through `get_db()`'s `DBUnavailable`, as every route. The after-commit
settle runs only after a commit, so a dropped connection there leaves the template saved and the
plans for the daily run (§ 5.6).

## 6. API

All under `/api/pm` (the blueprints' prefix, `backend/app.py`).

| Method, path | Key | Body / query | Answer |
|---|---|---|---|
| `GET /templates` | `equipment:read` | — | `{items: [active templates], inactive: [inactive templates], can_add}`, each `{id, name, trigger_text, item_count, plan_count, active}` (one request, as the card's answer; BR1-19) |
| `GET /templates/<id>` | `equipment:read` | — | `{id, name, performer, needs_verification, trigger_kind, calendar_every, calendar_unit, meter_type, meter_every, meter_from_parent, trigger_text, active, items: [{id, position, item_type, text, help_text, photo, reading_kind, unit, min_value, max_value, meter_type, meter_from_parent, limits_text}], plan_count, created_*, updated_*, can_edit}` |
| `POST /templates` | `pm_plan:edit` | the fields of § 5.1 and `items` | the detail, 201 |
| `PUT /templates/<id>` | `pm_plan:edit` | any subset; `items` replaces the list by id; `{active}` alone | the detail with `plans_settled`, `plans_failed` |
| `POST /template-item-check` | `pm_plan:edit` | `{item}` | the clean item, or 400 with its field |
| `GET /plans?equipment_id=` | `equipment:read` | — | `{items: [plan summary + source + applies + schedule], unlinked: [...], can_add}` |
| `GET /plans/<id>` | `equipment:read` | — | `{id, equipment, template: {id, name, summary, trigger_text, items, active}, source, assignee, last_done_on, last_done_meter, meters: [{meter_type, equipment, from_parent}], applies, stop_remark, linked, can_edit, can_remove}` |
| `POST /plans` | `pm_plan:edit` at the node's site | `{equipment_id, template_id}` | the plan detail, 201 |
| `PUT /plans/<id>` | `pm_plan:edit` at the node's site | `{assignee_id, last_done_on, last_done_meter}` subset | the plan detail |
| `POST /plans/<id>/remove` | `pm_plan:edit` at the node's site | — | the plan detail |
| `GET /plans/attach-preview?equipment_id=&template_id=` | `pm_plan:edit` at the node's site | — | `{meters, applies, missing}` for the dialog |

Removed: `GET /meter-choices`, `POST /item-check`, the plan create with items. The job routes keep
their shapes; `plan` in the job answer gains `template_id`.

## 7. Design decisions

- **D1. One migration v57 drops and recreates** (R03 Q18.1 a). Rejected: converging statements, as
  v50 did — the plan's columns move to a new table, and the dev rows are test rows only.
- **D2. Template reads with `equipment:read`, writes with `pm_plan:edit` held anywhere** (Q18.4 a).
  Rejected: `masters:read` for reads — every role holds it, while PM is read by the roles that read
  equipment; the same set today, but the plan page already uses `equipment:read`.
- **D3. The plan row stays when its link goes** (`linked` = 0; R03 Q19.1 a), so relinking brings
  its assignee, seed and jobs back. Rejected: delete the row — breaks ISO 9001 § 7.5.3 and the jobs'
  foreign key.
- **D4. Applicability and the meter are resolved live, never stored on the plan** (R03 answer 18.3).
  Rejected: a stored meter per plan — needs a sync on every meter change, which R03.19 avoids.
- **D5. The job copies its trigger meter** (`pm_jobs.meter_equipment_id`, `meter_type_id`),
  refreshed with the due copies. The list, the alert scan and *Mark job done* then read one column,
  with no resolution per row; and a done job's copy tells whether its `done_meter` is a value of the
  meter in use now, so a base on another meter is never used (BR1-01). Rejected: resolving per row in
  the list — a query set per job (N+1).
- **D6. A *Meter reading* item has no limits of its own** (R03.18's recommendation): one source of
  limits per meter, the meter's own; a rule's threshold is R03.22's condition template. Rejected:
  S096's tighter item limits — two limits for one meter, which disagree on the job.
- **D7. `pm_job_results.meter_equipment_id` stays**, resolved at *Start*: with the parent tick, the
  meter may be the parent's, and the record must say on which node the reading was saved. A
  departure from R03.18's text, written before Q18.5's answer.
- **D8. *Start* copies the template's name onto the job** (`pm_jobs.title`), so a renamed template
  does not rename an old record (ISO 9001 § 7.5.3; R03.18's recommendation). A due job shows the
  current name. Rejected: copying at job creation — a due job would keep an old name after a fix of
  a typo.
- **D9. The template save settles its plans after its commit, in the request** (R03.18). Rejected:
  a worker task — the engineer would not see the moved jobs at once; inside the save's transaction —
  one transaction holding many plans breaks the one-plan-per-transaction rule of S097 D6.
- **D10. *Mark job done* copies `needs_verification` from the template**, read plainly after (6e), not
  from a locked row: the template's lock is not in the job's lock order; a template change racing
  a *Mark job done* gives either value, both valid at that moment.
- **D11. The parent tick: the stricter of several mentions wins** (§ 5.3), so one type has one meter
  per machine on a template. Rejected: per mention — the trigger and an item of the same type could
  read two different meters.
- **D12. Unknown fields on the plan settings are refused** (§ 5.5), unlike S096's ignore, so an old
  screen cannot think it saved the work. A deliberate departure from the repo's `clean_body` habit.
- **D13. *Attach* allows a template that does not apply**, and says why. Rejected: refuse it — the
  engineer adds the meter later and would have to attach again.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v57.py`)

- A fresh database: every table and key of § 4.1; the CHECKs refuse a bad row each
  (`chk_pm_template_items_kind`, `chk_pm_template_links_target`, `chk_pm_plans_not_for`); two active
  links of one template and node refused, an inactive one and a new active one pass.
- A database at v56 with rows (built from `migrations_v56.py`, `migration_helpers`): v57 drops the
  six tables and creates the final shape; `db_version` keeps v51–v56 and gains v57.
- Running v57 twice changes nothing.
- `trigger_kind` and `calendar_unit` equal `pm_schedule_core.KINDS` and `CALENDAR_UNITS` (S096's
  pin, moved to the template).

### 8.2 Backend

- **`test_pm_links_core.py`** (first): `plan_actions` (make, relink, unlink, nothing; a row linked
  and reached; an empty node); `needed_meters` (trigger only, items only, the same type twice with
  and without the tick: the stricter wins); `applies`; `stop_remark` (order of the reasons; one and
  two missing types; the words).
- **`test_pm_templates_core.py`**: S096's trigger and item rule tests, moved; the reading kinds
  (§ 5.2's table, each refusal); `meter_from_parent` without a meter type.
- **`test_pm_templates_api.py`**: list and detail for each role (IT admin reads, cannot write);
  create, name taken (409), change with items synced (removed item inactive); a change of the
  interval moves the open job of each plan (two machines); a change of the schedule drops a
  reschedule, a name change keeps it; deactivate cancels each not started job with its remark and
  leaves an in-progress job; reactivate makes the jobs again; one plan's settle failing (a
  monkeypatched `settle_one`); the job's timeline lines of a template save name the engineer
  (BR1-03); a relinked plan with no base job counts from the relink (BR1-05) leaves the template saved and `plans_failed` = 1.
- **`test_pm_plans_api.py`**: attach (201; the plan row; a second attach 409; inactive template 409;
  scrapped 409; another site 403; outside the units 404); attach of a template that does not apply
  (no job; the card's line); the meter match: own meter, the model's meter, a part with no meter
  (does not apply), the parent tick (the press's meter used, the reading saved on the press); the
  plan settings (each rule of § 5.5; unknown field 400; a seed change drops a reschedule); remove
  (link inactive, plan `linked` 0, job cancelled with the remark, a started job left); attach again
  (same plan id, assignee and jobs kept); the card (sources, unlinked list, one pass: no query per
  plan — counted with the cursor, as earlier steps' N+1 tests do, *to verify* that such a helper
  exists, else assert the count of `meters_with_last` calls).
- **`test_pm_generate.py`**: a meter added to the node makes a not-applying plan's job at the next
  run; a meter removed cancels the due job with "Does not apply: …".
- **`test_pm_work_api.py`**: *Start* copies `template_item_id`, `reading_kind`, the resolved meter
  node and `title`; a *Measurement* logs no meter reading; a *Meter reading* logs one on the
  resolved node (own, and the parent's with the tick); a meter gone since the settle → *Start* 409;
  a template renamed after *Start* leaves the job's title.
- **`test_pm_jobs_api.py`, `test_pm_verify_api.py`, `test_pm_reschedule_api.py`, `test_pm_alerts.py`**:
  set-up through `pm_helpers`; their assertions unchanged, except the plan's fields now set on the
  template (`set_plan` writes `pm_templates` for the trigger, `pm_plans` for the seed).

### 8.3 Existing tests that change or run again

- The shared set-up `backend/tests/pm_helpers.py`: `template_body(**fields)`, `plan_on(client, node,
  **fields)` (POST a template, POST `/plans` to attach it, return the plan detail), the fixtures
  `site`, `eng`, `engineer_a`, `at_site`, `hours`, `oil`, `press` (from `test_pm_plans_api.py:37-94`),
  `technician`, `tech`. `test_pm_plans_api.create` and `test_pm_work_api.plan_with` keep their names
  as thin wrappers only if the coder finds it shortens the diff; the imports point at `pm_helpers`.
- `test_equipment_api.py::…::test_scrapping_with_a_started_pm_job_is_409`: the plan insert through a
  template row.
- `conftest.py` `_TABLES` (§ 3); `test_rbac.py::TestComputePermissions::test_role_matrix` runs
  unchanged (no key change).
- `test_pm_schedule_core.py`, `test_pm_work_core.py`, `test_alerts_core.py`: run again; field names
  only.
- `test_pm_jobs_core.py`: `decide`'s new first argument (the remark).

### 8.4 Automated (browser)

Specs: `pm-templates.spec.js` (new), `pm-plans.spec.js` (rewritten), the set-up of `pm-job`,
`pm-jobs`, `pm-reschedule`, `pm-verify`, `me`, `screens` through `e2e/support/pm.js`. Lines that use
S096's labels change: `"Add PM plan"` (`pm-plans.spec.js:55,163,185`), `"New PM plan"` (`:56`;
also `screens.spec.js:112`, which becomes the template page's heading `"New PM template"`; BR1-11),
`"Save plan"` (`:75,88,129,167,194`, kept on the plan page), `"Deactivate"` (`:144,170`),
`"Inactive plans (1)"` (`:153`), `"You can't add PM plans here."` (`:241`), `"PM plans (1)"` /
`"PM plans (0)"` (`:81,151`). `pm-job.spec.js:97,285` keep "These are the plan's items now…".
`pm-job.spec.js:236`'s `PUT /api/pm/plans/:id` becomes a template `PUT`.

- **important** An engineer adds a template with a *Check*, a *Measurement* and a *Meter reading*
  item, saves, and sees it in *Masters › PM templates* with its trigger in words
  (`pm-templates.spec.js`).
- **important** On a press, *Attach PM template* → the card lists it with "This machine" and its
  next due; the plan page shows "HP…'s own Run hours" (`pm-plans.spec.js`).
- **important** A template needing a meter the machine lacks: the attach dialog and the card say
  "Does not apply: no … meter on …" (`pm-plans.spec.js`).
- A change of the template's interval moves the machine's next due on the card
  (`pm-templates.spec.js`).
- *Remove from this machine* moves the plan to *Not in use (1)*; attaching again brings it back with
  its assignee (`pm-plans.spec.js`).
- A job of a *Meter reading* item: the value logged shows on the machine's Readings register
  (`pm-job.spec.js`).
- A technician opens the template page read-only (no *Save template*) (`pm-templates.spec.js`).
- The template page, the item dialog and the attach dialog fit a phone (`screens.spec.js`,
  `expectDialogFits` in the flows).

Runs: the coder's targeted runs of these specs plus `screens.spec.js`; a new file in `e2e/support/`
is shared code: the whole suite once at the end, and `screens.spec.js` on `--project=phone-webkit`
once (settings: *Shared code*).

### 8.5 On a real device

None: no camera, printer, Keycloak or keyboard behaviour is new. The template page's table on a real
phone is covered by the browser's phone projects.

### 8.6 Acceptance and the SMTW-Review point

- All three unit suites green; `tooling\schema-docs.bat check` exits 0; the browser runs of § 8.4.
- **CLAUDE.md § SMTW-Review, replacing *PM plans (S096)*:** "**PM templates and plan rows (S104):**
  the work (items, trigger, performer, verification) lives only on `pm_templates` /
  `pm_template_items`, written by `pm_templates.py` under the template's lock (6g); a machine's
  `pm_plans` row holds only its own facts (assignee, *Last done*, `linked`, *Not for this
  machine*) and is made, relinked and unlinked only by `pm_plans.sync_node`; nothing deletes a
  template, an item, a link or a plan row. A template names meter types; the meter is resolved live
  (`pm_jobs.resolve_meters`: own meters, a parent's only with `meter_from_parent`), never stored on
  the plan; a template that lacks a meter on the machine does not apply (`pm_links_core.applies`).
  A template save settles each of its plans after its commit, one transaction per plan. A path that
  writes work onto a plan row, stores a meter on it, or settles plans inside the template's
  transaction breaks R03.18."

## 9. Open questions and assumptions

1. **Decided (KLA, 02-11-2026):** the six PM tables on dev and test databases hold no data to keep;
   v57 drops them ("no trial data to keep, drop them"). Nothing of S095–S102 was released (R03
   answer 5b).
2. **Checked (round 1):** `GET /api/masters/meter-types` lists the meter types with `kind`
   (`SELECT *` under `masters:read`), for the item dialog's pick.
3. **Settled (BR1-20):** the attach preview stays on the server (`GET /plans/attach-preview`), so
   the resolution rule (`resolve_meters`, `applies`) has one home and the dialog shows exactly what
   the plan page will show.
4. **Assumption:** the card's "one pass" meter resolution reuses `meters.meters_with_last` over the
   subtree and the node's ancestors (§ 5.3); no new meters query.
5. **Decided (KLA, gate A, 04-11-2026, Q1 a):** the help tour (`tooling/help/setup_tour.py`,
   `frontend/help-tour/desktop.tour.js`) breaks with this step. It is left to the guide's retake
   before the release (*Out of scope*); this step does not touch it.
6. **Decided (KLA, 13-11-2026, "Keep"; code review CR2-01):** while the plan page shows the old-meter
   note (the stored *Last done* meter value was entered for another meter than the plan uses now), the
   meter field starts empty, a save with it empty keeps the old value stored and unused, and *Clear old
   meter value* removes it after a confirm; the next due does not move.

## 10. Amendments

### A1 — Meter links on the part replace the template's parent tick

```
Amendment: A1
Requested by: KLA, 13-11-2026
Author: Brief writer (Fable)
Status: Approved 13-11-2026 by KLA ("approved"; answers 1a, 2a, 3a; no brief review, by KLA's approval); Baseline: snapshot round 7 30edbf8
Checked against: the working tree of 13-11-2026 (HEAD c7e9f0b + the held steps + S104 after fix round 5)
```

KLA, 13-11-2026: "Now this meter inheritance 'use parent meter' is getting scary. Why not make it
explicit? When a child is linked to a parent, user explicitly chooses what meters of the Parent can
pass through to the children." Decided the same day (R03-pm.md § *Answers (KLA, 13-11-2026)*, row
*Parent meters*; it replaces Q18.5's tick).

#### A1.1 What will be built

A part (a component unit or a component) that has no meter of its own can **use the meter of a node
above it**. An engineer sets this on the part's *Meters* card: "MOT014 uses PR-07's Run hours". A PM
template then finds that meter by its type, as it finds a machine's own meter. The template's tick
*If the machine has no meter of this type, use the meter from a parent node* goes: a template only
names a meter type, and nothing walks up the tree.

1. **A meter link** (new table `node_meter_links`): part, meter type, source node. The source is the
   part's parent or its parent's parent, and has that meter itself (its model's or its own).
2. **One meter per type on a node:** its model's, its own, or a linked one, never two.
3. **Readings stay where the meter is.** The part's *Meters* card shows the linked meter read-only:
   the source's last reading and limits, no *Log reading*, no *Set limits*. The reading paths
   (`meters.log_reading`, `meters.write_reading`, the S039 lock and neighbour checks) do not change.
4. **The limits are the source meter's** (R03 Q23.1 (a): rules sit where the meter is defined). The
   part sets no limits on a linked meter; R03.23's rules will be the source meter's too.
5. **PM finds the meter by type:** the part's own meter in force, else its link in use, else the
   template does not apply there (§ 5.3's words and stop remark stay).
6. **Removing a link asks first**, naming the PM plans that use it. So does **moving a part** to
   another parent: the links to nodes that are no longer above it are removed with the move.
7. **The plan page's old-meter note and *Clear old meter value* go** (§ 9 item 6). A *Last done*
   meter value stays stored with the meter it was entered for, and is shown and used only while the
   plan uses that meter (A1.8 AD6; KLA confirms it at approval, A1.10 item 1).
8. **Migration v58** adds the table and drops the two `meter_from_parent` columns (A1.5).

**Out of scope**
- Settling a part's PM plans at once when a link is set or removed. As for an own meter today
  (§ 5.3), the card and the plan page show "Does not apply" at once, and the open, not started job
  is cancelled or made at the next settle (the 05:00 run, or a save of the plan or its template).
  R03.21's reading hook is the place for an at-once settle.
- A refusal in *Masters › Models* when a model gains or loses a meter type that links use (A1.6.1
  says what the link then shows).
- Links between machines, or to a node that is not above the part.
- The reading sheet, the reading register and the ticket's *Meters* card: they list a meter where it
  is, so a linked meter is not repeated under the part.
- The roadmap's own text (R03.18, R03.21, R03.23; A1.10 item 5): the orchestrator's.

#### A1.2 Standards and practice

- **ISO 14224 — equipment hierarchy; operating time of an item** (taxonomy levels and the table of
  operational data: *to verify*). The standard arranges a machine as equipment unit, subunit and
  maintainable item, and records operating time (hours run, cycles) on the item it is measured on.
  A motor inside a press has no hour meter: it runs when the press runs. The link writes that fact
  down per part, on the part, in place of a rule hidden in a template. A part whose hours differ
  (a standby pump) gets its own meter.
- **EN 13306 — predetermined maintenance; operating time** (term numbers *to verify*).
  Predetermined maintenance is done at set intervals of time or of units of use. The units of use
  of a part must be a count the plant trusts; the link names which count that is.
- **TPM — planned maintenance.** Time-based work by running hours needs one agreed hour count per
  part. One meter per type on a node keeps it to one.
- **ISO 9001 § 7.5.3 — control of documented information.** The part's history holds each link set
  and removed, with who and when (`equipment_events`). A reading is stored once, on the source.
- **ISO 55001 § 8.2 — management of change** (clause *to verify*). Removing a link changes how a
  part is maintained; the confirmation names the PM plans it stops.

#### A1.3 What A1 replaces in this brief and in S104 as built

| Where | Approved text | With A1 |
|---|---|---|
| § 1 item 4, § 5.3 *Resolution* step 2, § 5.10 (template page, item dialog) | the tick *If the machine has no meter of this type, use the meter from a parent node* | no tick; step 2 is "the part's link in use" (A1.6.2) |
| § 1 item 6, § 5.10 plan page | "HP002's Run hours (from the parent node)" | "PR-07's Run hours (linked meter)" |
| § 4.1 items 2 and 3 | `pm_templates.meter_from_parent`, `pm_template_items.meter_from_parent` and their CHECK parts | dropped by v58 (A1.5) |
| § 5.1 | the field `meter_from_parent`, its 400 "Tick By meter first.", its place in `SCHEDULE_FIELDS` | gone; a body that still sends it is not refused: the field is ignored, as any unknown field of a template body |
| § 5.2 table row *Parent tick* | per item | gone |
| § 5.3 *The needed meters* | `(meter_type_id, meter_from_parent)`, the stricter mention wins | the meter type ids only |
| § 6 | `meter_from_parent` in the template and item answers; `meters[].from_parent` | removed; `meters[].from_link` |
| D7 | `pm_job_results.meter_equipment_id` stays "with the parent tick" | stays, for a linked meter: the record says on which node the reading was saved |
| D11 | the stricter of several mentions wins | falls away: one type has one meter on a node |
| § 5.3 last bullets, § 9 item 6 (CR2-01, CR3-01, CR4-02…CR4-04) | the plan page's note "Last done meter value was entered for …", the empty field while it shows, *Clear old meter value* | gone (A1.6.3); § 5.3's rule "a seed counts only for the meter it was entered for" (BR1-01) stays |
| § 8.6 SMTW-Review point | "own meters, a parent's only with `meter_from_parent`" | "own meters, else the part's meter link in use" (A1.9) |

Code removed: `meter_from_parent` in `pm_templates_core.py` (the field, `TICK_BY_METER_FIRST`, its
part of `item_limits_text`), `pm_templates.py`, `pm_plans_core.py` and `pm_jobs.py`
(`PLAN_COLUMNS`, `_meter_items`); `PARENT_TICK` and the two tick boxes in the frontend;
`pm_plans.seed_not_used` and `pm_plans._seed_note`; `seed_note` in the plan answer; `clearSeedBody`
and the note's branches of `planSettingsForm`, `planSettingsBody` and `lastDoneHint` in
`pmLabels.js`; the note and its button in `PmPlanView.vue`.

#### A1.4 Where

**Backend**

| File | Change |
|---|---|
| `backend/local_db.py` | **v58** appended (A1.5); v57 is not edited. |
| `backend/meters_core.py` | Pure, tests first: `link_states` (which links are in use, and why not), `link_text` ("Run hours from PR-07"), `broken_links` (the links a move breaks), `move_warning` and the texts of A1.6.7. |
| `backend/equipment.py` | `read_meter_links(cur, node_ids)` and `link_plan_names(cur, link_ids)` (plain reads; here because `meters.py` and `pm_jobs.py` import this module, AD9). `update_equipment`: a new parent removes the broken links, after asking (A1.6.4). The LOCK ORDER note (A1.6.6). |
| `backend/meters.py` | Routes: the link choices, add, remove (A1.7). `_meters_out` adds the linked meters and `linked_by`. `add_node_meter` and `change_node_meter` refuse a linked type (A1.6.1). Its LOCK note. |
| `backend/pm_links_core.py` | `needed_meters` returns types only; `resolve_meters(needs, node_id, types_by_node, links)`; `IN_FORCE_SQL` moves here from `pm_jobs.py`; `LINK_PLANS_SQL` (A1.6.5). |
| `backend/pm_jobs.py` | `meters_on_paths` also reads the nodes' links (one query more, none per plan) and gives the links in use; `plan_resolutions`, `plan_meters_out` (`from_link`); `PLAN_COLUMNS` and `_meter_items` lose the tick; the module note. |
| `backend/pm_templates_core.py`, `backend/pm_templates.py`, `backend/pm_plans_core.py` | The tick removed (A1.3). |
| `backend/pm_plans.py` | The seed note removed; `last_done_meter` is answered only when `pm_jobs_core.seed_matches` (A1.6.3). |
| `backend/pm_work.py` | None expected: *Start* and the items use `pm_jobs.plan_resolutions`. The comment naming D11 goes. To verify by the coder. |

**Tests**

| File | Change |
|---|---|
| `backend/tests/test_migration_v58.py` | **New** (A1.9). `test_migration_v57.py` stays: it runs the migrations up to 57 only (its `V57` list). |
| `backend/tests/test_meters_core.py`, `backend/tests/test_meters_api.py` | New tests of the link rules and routes. |
| `backend/tests/test_equipment_api.py` | `TestReparent`: the move with links. |
| `backend/tests/test_pm_links_core.py`, `test_pm_templates_core.py`, `test_pm_templates_api.py`, `test_pm_plans_core.py`, `test_pm_plans_api.py`, `test_pm_generate.py`, `test_pm_work_api.py`, `backend/tests/pm_helpers.py` | The tick's tests go; the parent cases are set up with a link (`pm_helpers.link_meter`); the seed tests (A1.9). |
| `backend/tests/conftest.py` | `_TABLES`: `node_meter_links`, before `node_meters`. |

**Frontend**

| File | Change |
|---|---|
| `frontend/src/views/equipment/MeterLinkDialog.vue` | **New**: *Use a meter from above* (A1.6.7). |
| `frontend/src/views/equipment/MetersCard.vue` | The linked rows, *Use a meter from above*, *Remove link* and its question; the own meter's *Remove* question names the parts that link it. |
| `frontend/src/views/equipment/EquipmentMoveModal.vue` | The warning and *Move and remove links* (A1.6.4). |
| `frontend/src/utils/meterLabels.js`, `frontend/src/utils/equipmentLabels.js` and their tests `frontend/tests/meterLabels.test.js`, `frontend/tests/equipmentLabels.test.js` | The source badge "From PR-07", the not-in-use lines, the two questions; the history lines `meter_linked`, `meter_unlinked`. |
| `frontend/src/utils/pmLabels.js`, `frontend/tests/pmLabels.test.js` | The tick and the seed note removed; `meterUseText`; the plan form sends the meter value only when it changed (A1.6.3). |
| `frontend/src/views/PmTemplateView.vue`, `frontend/src/views/pm/PmItemDialog.vue`, `frontend/src/views/PmPlanView.vue` | The tick boxes removed; the notes of A1.6.7; the seed note and its button removed. |
| `frontend/e2e/support/meters.js`, `frontend/e2e/support/pm.js` | `linkMeterByApi(part, source, meterName)`; `templateItem` and `splitPlanBody` stop sending the tick and link the meter instead (shared code). |
| `frontend/e2e/equipment.spec.js`, `pm-plans.spec.js`, `pm-templates.spec.js`, `pm-job.spec.js`, `screens.spec.js` | A1.9. |

**Docs (housekeeping, by the coder)**
- `docs/schema/notes.json`: `node_meter_links` (area *Equipment*); `pm_templates`, `pm_template_items`
  and `equipment_events` notes updated. Then `tooling\schema-docs.bat write`; `check` exits 0.
- `.claude/CLAUDE.md` § SMTW-Review: the S104 point's sentence and the new point (A1.9).
- `docs/Plan.MD` § 4.3, the bullet *Which meter a plan uses*: "… matched on the machine's own
  meters; a meter of a node above only through a link set on the part's Meters card (13-11-2026,
  S104 A1)". § 4.5 (meters and readings) and § 4.1's bullet *Meters on the equipment page*: one
  line each on the linked meter.
- `docs/Maintenance-Philosophy.md` § 8, the gearbox sentence: "the gearbox uses the extruder's Run
  hours through a link on the gearbox's Meters card, or gets its own hour meter where its hours
  differ (ISO 14224)".

About 45 files; the size and the split are in A1.10 item 2.

#### A1.5 Data model — migration v58

**v58 is appended; v57 is not edited** (AD2). Statements, each safe to run twice:

1. `CREATE TABLE IF NOT EXISTS node_meter_links`: `id`; `equipment_id` INT NOT NULL (FK
   `equipment`: the part); `meter_type_id` INT NOT NULL (FK `meter_types`); `source_equipment_id`
   INT NOT NULL (FK `equipment`: the node whose meter it is); `created_at`, `created_by`. Keys:
   `uq_node_meter_links (equipment_id, meter_type_id)` (one link per part and type);
   `ix_node_meter_links_source (source_equipment_id, meter_type_id)` (the parts that use a meter).
   CHECK `chk_node_meter_links_source`: `source_equipment_id <> equipment_id`. No `active` and no
   `updated_*`: a link is never changed; a removed link's row is deleted and the part's history
   keeps both lines, as `contract_equipment` does (S081).
2. `ALTER TABLE equipment_events MODIFY event ENUM(…)`: v50's list plus `'meter_linked'`,
   `'meter_unlinked'` at the end (the form of v50's own MODIFY of this column).
3. `pm_templates`: `DROP CONSTRAINT IF EXISTS chk_pm_templates_meter`, then `DROP COLUMN IF EXISTS
   meter_from_parent`, then `ADD CONSTRAINT IF NOT EXISTS chk_pm_templates_meter` with v57's first
   three conditions. The CHECK goes first because it names the column.
4. `pm_template_items`: the same three steps for `chk_pm_template_items_kind` (v57's text without
   the two `meter_from_parent = 0` conditions).

The three ALTER forms are v50's (`DROP COLUMN IF EXISTS`, `DROP CONSTRAINT IF EXISTS`, `ADD
CONSTRAINT IF NOT EXISTS`, in `local_db.py`'s v50 entry), tested by `test_migration_v50.py` on the
dev MariaDB 11.4.

- **Shapes:** production at v50 runs v57, then v58, on empty PM tables. A dev or test database at
  v57 keeps its rows: a template that had the tick loses it, so its parts' plans do not apply until
  a link is set (dev data only; decided 02-11-2026 that it is disposable).
- **No precondition:** a dropped column and a weaker CHECK refuse no stored row.
- **A half-applied v58** (stopped between a DROP and its ADD) re-runs to the same shape.
- **Computed, never stored:** whether a link is in use (A1.6.1); which meter a plan uses (§ 4.2).

#### A1.6 Rules

##### A1.6.1 The link

- **Who:** a node with a node above it (level `component_unit` or `component`). A machine has none
  above: 400 "A machine has no node above it. Add the meter on the machine itself."
- **The source** is the part's parent or its parent's parent, read from the tree at the write. Any
  other node (a sibling, a part of its own, another machine, itself, an unknown id): 400 on
  `source_equipment_id`, "Pick a node above this part."
- **The source has the meter itself:** a meter of that type in force there, its model's or its own
  (`meters_core.effective_meters`), never a linked one, so there are no chains. A part two levels
  down links the machine directly. Not so: 409 on `source_equipment_id`, "PR-07 has no Run hours
  meter. Reload the page."
- **One meter per type on a node**, checked under the part's lock:
  - a link is refused when the part has that type in force (409 on `meter_type_id`,
    `meters.ALREADY_ON_NODE`) or already links it (409 on `meter_type_id`: "This part already uses
    PR-07's Run hours. Remove that link first."; `uq_node_meter_links` is the guard);
  - *Add meter* (`add_node_meter`) is refused while the part links that type: 409 on
    `meter_type_id`, "This part uses PR-07's Run hours. Remove that link first." The *Add meter*
    dialog does not offer a linked type (its list leaves out every type on the card). So replacing
    a linked meter by an own one is two acts: *Remove link* (asked), then *Add meter* (AD5).
- **Any meter kind** may be linked. PM uses counters and gauges; the others only show.
- **Body:** `meter_type_id` and `source_equipment_id`, each an integer of 1 or more. Missing, null,
  a boolean, a string or 0: 400 on that field, "Pick a meter" (`meters_core.PICK_A_METER`). An
  unknown meter type: the same 400.
- **A link is never changed:** remove it and set another.
- **Readings and limits:** logging a reading of a linked type on the part is refused as today (409
  `meters.NOT_ON_NODE`: the part has no such meter). `change_node_meter` on a linked type: 409 "This
  is PR-07's meter. Set its limits on PR-07."
- **In use, judged live** (`meters_core.link_states(own_type_ids, links, above_ids, types_by_node)`,
  pure). A link is in use unless, in this order:
  1. `own`: the part has that type in force itself. Its model gained the type in Masters, or its
     model changed. The meter on the part wins, as a model meter wins over an own row today.
  2. `not_above`: the source is not above the part. The move removes such links (A1.6.4); this
     guards a row left by the race A1.6.6 names.
  3. `no_source_meter`: the source has no meter of that type in force now (removed there, or its
     model lost it).
  A link not in use stays, shows on the card with its reason and *Remove link*, and counts for
  nothing; it is in use again when its reason ends. Nothing but *Remove link* and a move deletes one.
- **History** (the part's `equipment_events`): `meter_linked` with new value "Run hours from PR-07";
  `meter_unlinked` with old value "Run hours from PR-07". The screen: "Meter linked: Run hours
  from PR-07", "Meter link removed: Run hours from PR-07".
- **States:** removing a link that is not there: 404. A scrapped part is read-only (409
  `SCRAPPED_MESSAGE`). A node above a part in use is never scrapped: a scrap needs every part
  scrapped first (`_check_parts_scrapped`), so the source needs no scrapped check of its own.

##### A1.6.2 The PM match (replaces § 5.3 *The needed meters* and *Resolution*)

- `pm_links_core.needed_meters(template, items)` → the meter types in the order first named (the
  trigger's, then each active *Meter reading* item's), each once.
- `pm_links_core.resolve_meters(needs, node_id, types_by_node, links)` → `{meter_type_id: node id or
  None}`: (1) the node itself when it has the type in force; (2) else the source of the node's link
  of that type in use; (3) else None. `links` is `{meter_type_id: source id}` of the links in use.
- `pm_jobs.meters_on_paths` reads the nodes, their parents and grandparents and their meters as
  today, plus the nodes' links (`equipment.read_meter_links`), and asks `link_states`. The card's
  one pass stays: one query more for any number of plans.
- Everything after the match is § 5.3 as approved: the job's meter copy, "Does not apply", the meter
  base that follows the meter, *Start*'s 409, the reading saved on the resolved node (D7).
- A link set or removed is picked up as an own meter is (§ 5.3): live on the card and the plan
  page, by the job at the next settle.

##### A1.6.3 The *Last done* meter value (replaces § 9 item 6)

- The plan row keeps `last_done_meter` with the meter it was entered for (`seed_meter_equipment_id`,
  `seed_meter_type_id`; BR1-01). It is used, and answered by the API, only while the plan's trigger
  resolves to that meter (`pm_jobs_core.seed_matches`). Otherwise the plan answers
  `last_done_meter: null`, and the plan page shows an empty field with no note.
- So after a link is removed, or replaced by an own meter, the old value is out of sight and out of
  the schedule at once. If the same link is set again, the plan uses that same meter again and the
  value counts again (while no job was done since): the value is a fact about that meter.
- A value typed on the plan page is stored for the meter the plan uses now and replaces the old one
  (`plan_changes`, CR1-05, unchanged). An empty field left empty sends no `last_done_meter` (the
  page sends the field only when it differs from what it loaded), so a save of the assignee does
  not touch a stored value. Emptying a shown value sends null and clears it (§ 5.5).
- `pm_plans_core.schedule_changed` (CR4-01) is unchanged: clearing a value the plan does not use
  keeps the open job's reschedule.

##### A1.6.4 Moving a part

- A move to another parent (`update_equipment` with a new `parent_id`) breaks the links whose
  source is no longer above their part: the links of the moved node and of its parts whose source
  is not the moved node, the new parent, or the new parent's parent
  (`meters_core.broken_links(links, kept_ids)`). A component moved from a component unit to its
  machine keeps its link to the machine. A component unit takes its components with it, so their
  links to it stay. A machine moved to another unit (`unit_id`) breaks nothing.
- **With no broken link** the move is as today.
- **With one or more, the move asks first:** without `remove_meter_links: true` in the body it is
  refused, 409, `field` `remove_meter_links`, `code` `meter_links`, and nothing is written:
  "This move removes 2 meter links: MOT014 — Run hours from PR-07; GBX003 — Oil temperature from
  PR-07. PM plans that use them make no job until the part has the meter again: Motor — 2,000 h
  greasing (MOT014). A Last done meter value entered for these meters is no longer used."
  The plans sentence is left out when no plan uses them. More than 5 links or 5 plans: the first 5,
  then "and N more".
- **With the flag** the move deletes those link rows and writes one `meter_unlinked` line on each
  link's part, with the `moved_parent` line, in the move's transaction.
- `remove_meter_links` is read from the body by the shell: only JSON `true` counts; absent, false or
  any other value is "not confirmed". With nothing to remove it is ignored. It is not a column
  (`validate_equipment` ignores a field it does not know, `equipment_core.py`).

##### A1.6.5 Permissions

| Route / button | Key | Where checked |
|---|---|---|
| The card's list with the linked meters (`GET /api/equipment/<id>/meters`), the link choices | `equipment:read` | `load_node_for_user` (404 outside the user's units), as today |
| *Use a meter from above* (add), *Remove link* | `equipment:edit` | at the part's site, in `meters.lock_node` (403), as every node meter write |
| The move | `equipment:edit` | unchanged: at the node's site and the new parent's |

- No new key. The source needs no key of its own: every node of a path is in the root machine's
  unit, so the part's access is the source's (the rule `pm_jobs.meters_on_paths` states).
- IT admin holds `equipment:edit`, so it may set and remove a link, as it may add a machine's own
  meter today. It still writes no template and no plan.
- The card names the PM templates that use a link (`used_by`): template names are readable with
  `equipment:read` (§ 5.8). `pm_links_core.LINK_PLANS_SQL` lists the plans in force
  (`IN_FORCE_SQL`) of a link's part whose template names the link's type as its trigger or in an
  active *Meter reading* item: `needed_meters`' rule as SQL, checked against it by a test (A1.9).

##### A1.6.6 Locks

Lock numbers are `equipment.py`'s. The database runs REPEATABLE READ. No new lock number: a link
write is a `meters.py` write under (1).

1. **Add link:** (1) the part `FOR UPDATE`, the first statement (`meters.lock_node`: 404, 403, 409
   scrapped from the locked row) → each node above the part up to the source, nearest first, one
   row each, `SELECT id, parent_id, level, model_id FROM equipment WHERE id = %s LOCK IN SHARE
   MODE`: the part's `parent_id` comes from its locked row, the next from the row just locked, two
   rows at most → the source not reached: 400 → plain reads: the meter type, the part's meters in
   force and its link of the type, the source's meters in force (its `model_id` from its locked
   row) → the insert (`uq_node_meter_links`: 1062 → 409; foreign-key shared locks on the part and
   the source, both held, and the meter type) → the `equipment_events` insert.
2. **Remove link:** (1) the part `FOR UPDATE` → plain: the link (404) → `DELETE … WHERE id = %s` →
   the event.
3. **`add_node_meter`, `change_node_meter`:** as today ((1) → (4b) → the `node_meters` row), then a
   plain read of the part's link of the type for the refusal.
4. **The move:** (1) the node → (2) the new parent `FOR UPDATE` (both as today), then its other
   locks as today → plain reads: the node's parts, their links and the node's, the plans
   (`LINK_PLANS_SQL`) → the 409, or `DELETE FROM node_meter_links WHERE id IN (…)` → `update_row` →
   the events. The new parent's `level` and `parent_id` come from its locked row.

- **What decides what.** "Above" is decided from locking reads. Whether the part has the type or a
  link is decided from plain reads made after (1): every write of a part's `node_meters` and
  `node_meter_links` rows holds that part's (1) first, and the snapshot starts at `lock_node`'s
  plain read, after the lock. It is the argument of the reading write, in the note of `meters.py`.
  The source's meters are read plainly, as a model's meters are read today. A meter removed there
  in the same instant leaves a link that shows `no_source_meter`.
- **No locking read of a row that may not exist** (no gap lock on `uq_node_meter_links`).
- **No cycle.** A link write holds the part and waits only for nodes above it, child first, the
  order of a re-parent ((1), then (2)). The writers that hold a node above (a meter or reading
  write there, an equipment edit, a move of the part's parent) never wait on the part. A PM write
  holds its plan (6e) first and a node after; a link write never waits on a plan or a job. Two
  link writes on parts of one machine share the source's lock.
- **Two accepted deadlocks, of the scrap's kind** (top-down against bottom-up; InnoDB rolls one
  back, 1213): a scrap of a node above (the node, then its parts) against a link write on a part;
  and a move of a component unit, whose `meter_unlinked` insert takes a part's row shared through
  its foreign key, against a link write on that part.
- **One residual:** a move reads its parts plainly. A component moved out of the unit by another
  request in the same instant is still seen as its part, and its links to nodes outside the unit
  are removed; the engineer sets them again.
- **Rollback:** a refused or failed write leaves no row and no history line. No counter is used.
- The move and the link routes never lock a plan, a job or a template row, so the rule "a node
  writer never waits on a plan" holds; this is why A1 writes no plan row (AD6, AD7).

##### A1.6.7 Screens

- **The Meters card** (`MetersCard.vue`). A linked meter is a row among the others, by name: "Run
  hours · h · Counter", the badge "From PR-07", the source's limits in force, the source's last
  reading (it opens the source's history: `ReadingHistoryModal` reads only the node's `id`), and the
  line "Read on PR-07 — Press 7. Log readings there." with a link to PR-07's page. No *Log reading*
  and no *Set limits* on it. For an editor: *Remove link*.
  - A link not in use shows, in place of the reading: "Not in use: MOT014 has its own Run hours
    meter." / "Not in use: PR-07 is not above MOT014." / "Not in use: PR-07 has no Run hours meter
    now."
  - The header gains *Use a meter from above*, beside *Add meter*: for an editor, on a part only.
    *Open register* shows while the node has a meter of its own.
  - **Remove link** asks in the row, as *Remove* does: "Stop using PR-07's Run hours on MOT014?
    Readings stay on PR-07." With PM plans (`used_by`): "Stop using PR-07's Run hours on MOT014?
    These PM plans use it and make no job until MOT014 has a Run hours meter again: Motor — 2,000 h
    greasing, Motor — yearly check. A Last done meter value entered for this meter is no longer
    used. Readings stay on PR-07." Buttons *Remove link* (red) and *Keep*.
  - An own meter's *Remove* question, when parts link it (`linked_by`), adds: "MOT014 and GBX003 use
    this meter through a link. Their PM plans that need it make no job until it is back."
  - A row's key is its type and its source, since a link not in use can sit beside an own meter.
- **The link dialog** (`MeterLinkDialog.vue`, title "Use a meter from above"), `FormModal` with
  `useFormModal`: `blank(seed)` returns `{ choice: seed ?? "" }`; the card loads the choices, then
  calls `openCreate(seed)` with the one choice when there is only one. Text: "MOT014 — Main motor.
  Pick the meter this part runs with. Readings are logged on that node; this part shows them."
  Then one radio row per choice, the nearest node first: "PR-07 — Press 7 · Run hours (h) · last
  12,345 h on 12-11-2026". Save button *Use this meter*; disabled with "Pick a meter" until one is
  picked. Common case: open, one row preselected, one tap. No choice: "The nodes above have no
  meter this part can use. Add the meter on the machine first.", save disabled with "No meter to
  use". Refusals show beside the list (`fieldError` of `meter_type_id` and `source_equipment_id`).
  The radio rows are at least 44 px high; the dialog fits a phone (`expectDialogFits`).
- **The move dialog** (`EquipmentMoveModal.vue`): its form gains `remove_meter_links: false`. On
  the refusal of A1.6.4 it shows the message in a warning box above the buttons, and the save
  button reads *Move and remove links*; that save sends `remove_meter_links: true`. Picking another
  parent clears the warning and the flag.
- **The plan page:** *Meters this plan uses*: "MOT014's own Run hours" or "PR-07's Run hours
  (linked meter)". On a part whose plan does not apply, one more line: "Add a Run hours meter on
  MOT014, or use one from a node above (Meters card)." No old-meter note.
- **The template page:** no tick. Its note reads: "The template names the meter type. Each machine
  uses its own meter of that type, or the meter of a node above that its Meters card links. A
  machine without one: the template does not apply there."
- **The item dialog:** no tick. *Meter reading*: "Saved as a reading of the machine's meter of this
  type, its own or a linked one, as if logged on the Readings sheet."
- Job screens, the PM card, the attach dialog: no change of text.

##### A1.6.8 The database down

Every new route answers 503 through `get_db()`. A1 adds no background task and no work after a
commit.

#### A1.7 API

| Method, path | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/equipment/<id>/meters` | `equipment:read` | — | the list as today. Each own or model meter gains `linked_by: [{id, code}]`. A linked meter is an entry `{meter_type, source: "linked", linked_from: {id, code, name}, in_use, not_in_use (null, "own", "not_above", "no_source_meter"), min_value, max_value, limits_text, last, used_by: [template names]}` with the source's limits and last reading (null when not in use), `overridden: false`, `linked_by: []` and the model fields null |
| `GET /api/equipment/<id>/meter-links/choices` | `equipment:read` | — | `{items: [{equipment: {id, code, name, level}, meter_type, limits_text, last}]}`: the meters in force on the nodes above, without the types the part has or links; empty for a machine |
| `POST /api/equipment/<id>/meter-links` | `equipment:edit` at the part's site | `{meter_type_id, source_equipment_id}` | the node's meters, 201 |
| `DELETE /api/equipment/<id>/meter-links/<meter_type_id>` | `equipment:edit` at the part's site | — | the node's meters, 200 |
| `PUT /api/equipment/<id>` | unchanged | gains `remove_meter_links` | unchanged; the 409 of A1.6.4 |

`GET /api/pm/templates/<id>`, `POST` and `PUT /api/pm/templates` lose `meter_from_parent`;
`GET /api/pm/plans…` and the attach preview answer `meters[].from_link` in place of `from_parent`;
the plan detail loses `seed_note`.

#### A1.8 Design decisions

- **AD1. A table of its own, `node_meter_links`.** Rejected: a third kind of row in `node_meters`
  (a source column). Every reader of a node's meters (`effective_meters`, the reading sheet, the
  register, the ticket card, `meter_in_force` in the reading path) would have to leave the linked
  rows out; with a table of its own they are untouched, and a reading can never be saved on a part
  for a meter that is not there.
- **AD2. Migration v58 appended; v57 not edited.** v57 has run on the dev database and on the test
  databases kept between runs. An edited v57 would not run there again, and each would need a
  reset by hand (`dev-db-reset.bat` drops every dev table, not only PM's). The repo rule is that an
  applied migration is never edited. The cost: production creates two columns in v57 and drops
  them in v58, on empty tables. Rejected: editing v57 (cleaner history, but breaks the rule and the
  databases at v57); a v58 that drops and recreates all PM tables, as v57 did for v51–v56 (a
  frozen fixture and renamed tests for no gain). A squash of the unreleased PM migrations before
  the release stays possible, as R03 notes; R03.23's migration is then v59.
- **AD3. The link names the node where the meter is; no chains.** One hop to resolve, one place for
  the readings and the limits.
- **AD4. The meter on the part wins over its link, and a link not in use is kept and shown.** A
  model edit in Masters reaches many machines and cannot ask about each link. Rejected: deleting
  links from a Masters write (a hidden change far from the part), and refusing the Masters write
  (A1.10 item 4).
- **AD5. No "replace" action.** Removing the link (asked) and adding the meter are two plain acts.
  Rejected: one action that does both: a second confirm path for a rare case.
- **AD6. The old-meter note and *Clear old meter value* go; the value stays stored with its meter,
  hidden and unused while the plan uses another meter or none.** This is the fewest states: the
  plan page shows a value only when it counts. It supersedes § 9 item 6 (KLA's "Keep" of
  13-11-2026, taken before this request), and it words the 13-11 decision "the values are cleared"
  as "no longer used": the value is gone from the page and the schedule at once, and comes back
  only if the same meter does. Rejected: (b) deleting the value at the act: a meter or equipment
  write would have to write plan rows, which hold their own lock (6e) first, so it could only be
  done after the commit, plan by plan, from two modules that PM imports (the dependency R03.19
  must design for its own sync); and a link removed by mistake would lose the values. (c) keeping
  the note as built: no code change, but the state KLA finds surprising stays. KLA decides
  (A1.10 item 1).
- **AD7. No settle at the act** (out of scope above): the same rule as an own meter (§ 5.3), and no
  node writer waits on a plan.
- **AD8. The move asks through a refusal the server words**, on the field `remove_meter_links`, so
  the list of links and plans is the server's, and the shared `useFormModal.js` is not changed (its
  error holds the field, not the code). The pattern is S039's `counter_lower`.
- **AD9. `read_meter_links` and `link_plan_names` live in `equipment.py`.** The move is there, and
  `equipment.py` imports no shell module above it (`meters.py` and `pm_jobs.py` import it); it
  already counts PM jobs for the scrap (`_check_no_started_pm_jobs`). `LINK_PLANS_SQL` and
  `IN_FORCE_SQL` sit in the pure `pm_links_core.py`, as `contracts_core.py` holds SQL texts that
  `equipment.py` uses. Rejected: a lazy import of `meters` in `equipment.py`.
- **AD10. The link write share-locks the nodes above it**, so "above" is exact against a move of the
  part's parent. Rejected: no locks and only the `not_above` state: a dead link the user must find.

#### A1.9 Tests and acceptance

**Migration** (`backend/tests/test_migration_v58.py`): a fresh database has `node_meter_links` with
its keys, foreign keys and CHECK (a self-link refused; a second link of one part and type refused,
1062), the two new events in the ENUM, and no `meter_from_parent` column; the two rewritten CHECKs
still refuse a meter trigger without `meter_every` and a *Measurement* with a meter type. A
database at v57 with a template and an item that have the tick (built from the migrations up to
57): v58 keeps the rows and drops the columns; `db_version` gains 58. A second run changes nothing.

**Backend, new**
- `test_meters_core.py`: `link_states` (in use; each reason; their order), `link_text`,
  `broken_links` (the cases of A1.6.4), `move_warning` (no plan; plans; more than 5).
- `test_meters_api.py`, class `TestMeterLinks` (fixtures: a press with a model meter, a component
  under it, a component unit with a component; `make_equipment`, `add_own_meter`): a component
  links the press's meter (201; the entry with the press's limits and last reading; the history
  line); the machine as the source of a component under a unit; each refusal of A1.6.1 (a machine;
  a sibling, a child, another machine, itself, an unknown id; the source without the type; the part
  with its own, with its model's, with a link; each bad body field; scrapped 409; another site
  403; outside the units 404; a technician 403; IT admin 201); *Add meter* and *Set limits* on a
  linked type (409); a reading logged on the part (409) and on the source (the part's `last`
  follows); remove (200, the line; again 404); not in use: the part's model gains the type, the
  source's own meter is removed and added back; `used_by` (the trigger; a *Meter reading* item; not
  an unlinked plan, not an inactive template) equals the plans whose `meters` in `GET
  /api/pm/plans` name the source; `linked_by`; the choices (a machine: none; types on the part left
  out); the database down (`db_down`).
- `test_equipment_api.py::TestReparent`: a component with a link moves to another machine: 409
  with the field, the code and the text naming the link and the plan, nothing written; with the
  flag: moved, the row gone, both history lines; a component unit moves with its component (the
  component's link to the old machine goes, its link to the unit stays); a component moved from
  its unit to its machine keeps its link, no refusal; the flag with nothing to remove; a machine
  moved to another unit removes nothing.

**Backend, existing tests that change** (the session database gives no link; each test makes its own)
- `test_pm_links_core.py`: the `needed_meters` tests with the tick (`item`, `template`, `need`
  helpers) and the `resolve_meters` tests: rewritten for types and links.
- `test_pm_templates_core.py`, `test_pm_templates_api.py`: every `meter_from_parent` case goes
  ("Tick By meter first.", the item's tick, `item_limits_text` "…, or a parent node's"); one new
  case: a body with `meter_from_parent` saves and the answer has no such field.
- `test_pm_plans_core.py`: `SCHEDULE_FIELDS` without the tick.
- `test_pm_plans_api.py::TestMeterMatch`: `test_the_parent_tick_uses_the_press_s_meter` becomes a
  link test (`from_link`); `test_the_seed_follows_the_meter` is set up with a link: the value shows
  while linked, is null after the link goes and an own meter comes, the next due ignores it, a
  typed value is stored for the own meter; new: the same link set again brings the value back, and
  an assignee save in between does not clear it; `test_clear_old_value_removes_the_unused_seed`
  goes; `test_clearing_the_unused_seed_keeps_the_open_job_s_reschedule` stays with a null sent by
  the API; `test_the_card_resolves_every_plan_in_one_pass` is set up with links and also counts
  one `read_meter_links` call; the `from_parent` assertions read `from_link`.
- `test_pm_generate.py` (the plan with `meter_from_parent=True`), `test_pm_work_api.py`
  (`_gauge_item(oil, from_parent=True)`: the reading is saved on the press through the link),
  `pm_helpers.py` (`template_body`, `plan_on`: a meter on another node is linked, not ticked).
- `test_migration_v57.py`: unchanged. `test_rbac.py::TestComputePermissions::test_role_matrix`:
  unchanged (no key). `conftest.py` `_TABLES`: A1.4.

**Frontend unit:** `meterLabels.test.js` (the badge, the three not-in-use lines, the two
questions), `equipmentLabels.test.js` (the two history lines), `pmLabels.test.js` (no tick in the
forms and bodies; `meterUseText` "PR-07's Run hours (linked meter)"; the plan body leaves an
unchanged meter value out, sends null for an emptied one; no `clearSeedBody`).

**Automated (browser)**
- **important** A part uses a meter from above: on a component's page, *Use a meter from above*,
  the dialog lists the press's Run hours, *Use this meter*; the card shows "From <press>" and the
  press's last reading, and no *Log reading* on that row (`equipment.spec.js`; `expectDialogFits`).
- **important** A plan on a part counts on the linked meter: a template by Run hours attached to
  the part says "Does not apply: no Run hours meter on <part>"; after the link, the plan page shows
  "<press>'s Run hours (linked meter)" and the card a next due (`pm-plans.spec.js`).
- **important** *Remove link* names the plan that uses it; after *Remove link* the row is gone and
  the PM card says "Does not apply" (`equipment.spec.js`).
- Moving a part asks before it removes its links: the warning names the link, *Move and remove
  links* moves it, the history shows "Meter link removed" (`equipment.spec.js`; the 409 is told to
  the console guard: `consoleWatch.allowFailedRequest`).
- After the link goes and an own meter is added, *Last done* meter value is empty and no note shows
  (`pm-plans.spec.js`; replaces the test "S104: Clear old meter value removes the note of a seed
  entered for another meter").
- The template page and the item dialog show no tick (`pm-templates.spec.js`, one assertion each in
  the existing tests).
- The link dialog fits a phone (`screens.spec.js`, `@device`).

Lines that use changed labels (the facts run lists them):
`"(from the parent node)"` (`pm-plans.spec.js`, `pmLabels.test.js`);
`"Clear old meter value"` (three lines of `pm-plans.spec.js`, two of `pmLabels.test.js`);
`"If the machine has no meter of this type, use the meter from a parent node"` (`PARENT_TICK`; in
no test line); `meter_from_parent` in the bodies of `pm-job.spec.js` and `e2e/support/pm.js`.
Runs: targeted (`equipment.spec.js`, `pm-plans.spec.js`, `pm-templates.spec.js`,
`pm-job.spec.js`, `screens.spec.js`); `e2e/support/` changes, so the whole suite once at the end and
`screens.spec.js` on `--project=phone-webkit` once (settings: *Shared code*).

**On a real device:** none. A browser judges the dialog and the card.

**Acceptance:** the three unit suites green; `tooling\schema-docs.bat check` exits 0; the runs above.

**CLAUDE.md § SMTW-Review:** in *PM templates and plan rows (S104)*, "(`pm_jobs.resolve_meters`: own
meters, a parent's only with `meter_from_parent`)" becomes "(`pm_links_core.resolve_meters`: the
node's own meter, else its meter link in use)". New point: "**Meter links (S104 A1):** a part uses
the meter of a node above it only through a `node_meter_links` row (one per part and type), set and
removed in `meters.py` under the part's lock (1) and removed by a move in `equipment.py`; the source
has the meter itself (no chains). Readings, limits and rules stay on the source: nothing writes a
reading or a limit on the part for a linked type. A link counts only while `meters_core.link_states`
says it is in use. No meter or equipment write locks or writes a plan row; a *Last done* meter value
counts only for the meter it was entered for (`pm_jobs_core.seed_matches`). A path that searches the
nodes above without a link, saves a linked reading on the part, or writes a plan from a node write
breaks A1."

#### A1.10 Open points

**Answers (KLA, 13-11-2026):** item 1 (a) — the *Last done* meter value stays stored with its meter,
hidden and unused, no note and no button (this replaces § 9 item 6's "Keep"); item 2 (a) — one
amendment, not split; the source stays the part's parent or grandparent (KLA asked what "any node
above" would add: nothing, since the tree has three levels, `equipment_core._ALLOWED_PARENTS`).

1. **For KLA — what happens to a *Last done* meter value when its meter goes** (AD6).
   (a) **Recommended:** it stays stored with its meter, hidden and unused; no note, no button; it
   counts again only if the same link is set again. The questions say "is no longer used".
   (b) It is deleted when the link is removed or the part moved. More code (plan rows written after
   the commit from the meter and equipment modules), and a link removed by mistake loses the values.
   (c) The note and *Clear old meter value* stay as built (§ 9 item 6): no change to that code; the
   plan page keeps the extra state.
2. **For KLA — size.** A1 touches about 45 files, above the 25 that call for a split. The cut that
   could ship apart: **A1 keeps only the removal of the tick** (S104 ships with own meters only:
   about 22 files, mostly deletions), and **a new step builds the meter links** (the table, the
   card, the move, the PM match through a link: about 28 files) before the release. As written, A1
   holds both, as decided on 13-11-2026. Either way the coder should be Opus: locks across three
   modules, a migration, and the PM match.
3. **Assumption:** IT admin may set and remove a link, since it holds `equipment:edit` (A1.6.5).
4. **Assumption:** *Masters › Models* is not changed. A model that gains a type makes its machines'
   links of that type "not in use" (the part's own meter wins); a model that loses a type a link
   names makes that link "not in use" and its plans not apply (R03.20's list shows them).
5. **For the orchestrator — the roadmap:** R03.18's sentences on Q18.5's tick; R03.21's "plans of
   nodes below it whose template takes the meter from a parent node" becomes "plans of the parts
   that link this meter" (`ix_node_meter_links_source`); R03.23's migration number is v59.
6. **To verify by the coder:** MariaDB 11.4 drops `meter_from_parent` once the CHECK that names it
   is dropped (the order of A1.5); `pm_work.py` needs no change.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

0 blocker, 0 major, 8 minor, 12 nits. No round 2: none is a blocker or a major.

| Finding | Answer |
|---|---|
| BR1-01 (minor) meter base on another meter | Accepted (a): `pm_jobs` copies `meter_type_id` beside `meter_equipment_id`; a base job is used only when its meter equals the resolved one; the seed carries its meter (`seed_meter_equipment_id`, `seed_meter_type_id`) and is used only when it matches; else S095 D9's reading rule; the plan page's line when a seed is not used (§ 4.1, § 5.3). |
| BR1-02 (minor) `sync_node`'s 1062 without (6e) | Accepted (a): rollback, then the relink path with (6e) first (§ 5.4, § 5.9 step 5). |
| BR1-03 (minor) the settle's actor | Accepted (a): public `settle_one(conn, plan_id, actor, *, keep_reschedule)`; a template save passes the engineer (§ 3, § 5.6, § 8.2). |
| BR1-04 (minor) the help tour breaks | Accepted (a), written into *Out of scope*; KLA chose it at gate A (Q1 a, 04-11-2026). |
| BR1-05 (minor) a relinked plan's start | Accepted (a): `pm_plans.linked_at`, written at make and relink, is the start without a base job or seed (§ 4.1, § 5.4). |
| BR1-06 (minor) old meter rule in two docs | Accepted (a): Plan.MD § 4.3's bullet and Maintenance-Philosophy § 8 in § 3 Docs. |
| BR1-07 (minor) unknown-field sentence | Accepted (a): a rule and a table of messages (§ 5.5). |
| BR1-08 (minor) no confirmation on a schedule change | Accepted (a): a confirmation when a schedule field changed and `plan_count` > 1 (§ 5.6). |
| BR1-09…BR1-20 (nits) | Accepted: BR1-09 the COALESCE inline in `open_target_id`; BR1-10 `alone` and `test_pm_alerts.py`'s `set_plan(active=0)` named; BR1-11 `screens.spec.js:112`; BR1-12 the counts and the 503 after a save; BR1-13 "Attached to this machine"; BR1-14 one count of linked plans; BR1-15 the technician reaches a template by *Open template*; BR1-16 the meter types' shared locks under (6g) stated; BR1-17 list below 768 px, table above; BR1-18 the moved imports and `PmItemDialog.vue` to `views/pm/`; BR1-19 one list request with `inactive`; BR1-20 the preview stays on the server (§ 9 item 3). |

### Gate A — 04-11-2026

KLA: "1a 2a". Q1 (a): the help tour is left to the guide's retake. The brief is approved; the coder is Opus.

## Feedback

**Amendment A1, 13-11-2026 (brief writer):**

- `rule`: an amendment has no size rule. The README says "a change too big for the step becomes a
  new step", and the brief writer's limits (25 files, 600 lines) speak of a brief. A1 was decided as
  an amendment before it was sized, and came out at about 45 files and 570 lines (§ 10 A1.4,
  A1.10 item 2). A threshold checked before the user is asked "amendment or new step" would help.
- `rule`: the decision card said the *Last done* values "are cleared" at a meter act. Three LOCK
  ORDER notes (`equipment.py`, `pm_jobs.py`, `pm_plans.py`) forbid a node writer to wait on a plan
  row, so that wording could not be built as asked without work after the commit (A1.8 AD6). A
  one-line check, "does the decision make one module's write touch another module's locked rows?",
  before the card goes to the user would have caught it; about 20 minutes of design here.
- `hindrance`: the facts run marked two new names (A1's table and one of its state names) as
  planned in an earlier step and "now coded — re-check", only because their sentences cited that
  step as a reason: `planned_in` in `brief_facts.py` falls back to any step id in the sentence. I
  reworded the sentences to make the report clean.
- `hindrance`: the facts run misses a quoted screen label that wraps onto a second line in the
  brief: `"Clear old meter value"` was absent from *Screen text in the tests* until it stood on one
  line (`scratch/brief-facts-S104.md`).
