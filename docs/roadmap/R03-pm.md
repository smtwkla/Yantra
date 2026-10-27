```
Roadmap: R03 — Preventive maintenance (PM)
Doc: roadmap
Author: Roadmapper (Opus)
Date: 27-10-2026
Status: Approved (KLA, 27-10-2026, gate R)
```

# R03 — Preventive maintenance (PM)

**The point:** PM is cut into **17 items**. A technician fills a real PM job on the phone after
the **first four** (R03.1–R03.4), and the engineer signs it off after the fifth (R03.5). Templates
for whole classes come next (R03.8), then operators' CIL (R03.12–R03.13), the compliance report
(R03.14) and routes (R03.15). KLA answered the **20 questions** on 27-10-2026, all at the recommendation (§ Decisions). The first
step, R03.1, waits only for Q1.1, Q1.2 and Q3.1, which set the scheduling rules. The effort is
about **20 step-days** (estimate, § Order).

## The feature

Plan.MD § 2, module 3: "PM templates applied to equipment; plans with checklists and readings,
triggered by calendar or by meter; jobs filled on the phone with photos; engineer sign-off." The
design so far is in Plan.MD § 4.3 (template, plan, job, the shared item shape, triggers, routes,
rescheduling), § 4.4 (CIL), § 4.5 (meters), § 4.2 (tickets from PM, parts used, meter targets on
deferred work), § 3 (roles and the PM keys), § 4.6 (PM compliance) and § 4.7 (alerts). The domain
rules are in Maintenance-Philosophy § 5 (CIL) and § 7 (planned maintenance).

**Why now (fact):** the asset register (S001–S004, S012, S033, S043, S044, S061, S062), meters and
readings (S037–S040, S050–S052), tickets (S017–S020, S027, S034) and alerts (S021, S032) are built.
Plan.MD § 8 puts PM in phase 4, after tickets, because a Not OK item on a PM or CIL job raises a
ticket. The user asked to "prepare for the PM module" and gave no scope or order.

**Why it matters at VEL (fact, Plant-Facts § 4 and § 6):** there is no PM schedule to migrate.
Many machines run until they break, and some are forgotten. Press availability has fallen to about
70 % at times. Known preventive tasks exist only in people's heads: the extruder gearbox oil every
5,000 run hours, roller shells trued every 60–70 run hours, the compressor AMC's A / B / D checks,
the daily genset round. PM is how the plant climbs from the reactive rung to the preventive one
(Maintenance-Philosophy § 8, the maturity ladder).

**What it is not:** no spares or stock, no cost, no shutdown planning, no IIoT feed. Certification
plans, calibration, fitness-for-use inspections and procedures are a follow-on (Q0.1, § Out).

## What exists

Checked against HEAD `c9142b4` (27-10-2026). Nothing of PM is built: no PM table, no PM key in
`backend/config_rbac.py`, no PM screen. What PM builds on:

| Piece | State today | Evidence | How PM uses it |
|---|---|---|---|
| Equipment tree, classes, models | Built | `equipment`, `equipment_classes`, `equipment_models` (`docs/schema.md`); a plan "can point at any level" (Plan § 4.1) | A plan belongs to one node at any level. A class is a kind across levels, so "apply to every press" is one class. |
| Property filter | Built (S062) | `property_filter_core.py`; `GET /api/equipment?props=` | The template's *Apply* dialog narrows the class's machines by property (e.g. rated power). |
| Meters and readings | Built (S037–S040) | `meter_types`, `model_meters`, `node_meters`, `meter_readings`; `meter_readings.source` is already `ENUM('manual','pm','move','iiot')` (`backend/local_db.py:987`) | Meter triggers read the latest counter reading. A reading item that names a meter writes a reading with source `pm`. |
| The reading rules | Built (S039) | `meters.log_reading` takes the node lock (`equipment.load_node_for_user`, `for_update`) and checks both neighbours (`meters_core.counter_error`); a CLAUDE.md § SMTW-Review invariant | A PM reading goes through the same locked path, never a second insert. |
| Tickets | Built (S017–S020, S027, S034) | `tickets.source` is `ENUM('manual')` only (`local_db.py:385`); `ticket_labour`, `ticket_parts` | A Not OK item raises a defect ticket (a new source `pm`). Labour and parts reuse the ticket dialogs' shape. |
| Deferred work | Built (S019, S034) | state `scheduled`, planned date, waiting reason; "a target by meter value … with the PM engine" (Plan § 4.2) | R03.16 adds the meter target with the PM core. |
| Team, contractors, site roles | Built (S010, S011) | `people`, `memberships`; `ASSIGNABLE_ROLES` (`config_rbac.py:64`); operators without a login (S017) | Assignee, *performed by*, AMC vendors as contractor people. |
| Files and photos | Built (S006, S008, S017) | `equipment_documents` with `chk_equipment_documents_owner`: exactly one of equipment, model, ticket (`local_db.py:480`) | Job photos and reference photos add a fourth and fifth owner. |
| Serial numbers | Built | `serial_counters`, "later `PM-`" (`docs/schema.md`); `tickets_core.serial_scope` | `PM-YYYY-MM-NNN` (Plan § 4.3). |
| Worker and daily schedule | Built (S013) | `scheduled_tasks.SCHEDULE` (one daily entry, `purge_access_log`); `task_handlers.HANDLERS` | A daily `pm_generate` task creates the jobs that fall due. |
| Alerts | Built (S021, S032) | `alerts_core.KINDS`, `AUDIENCE`, `CHANNELS`; push per device, email | Two new kinds: PM job due, PM job overdue. |
| Me page | Built (S031, S035) | *Open work* lists open tickets assigned to me | PM jobs join *Open work* (Plan § 6). |
| The time field and back-dating | Built (S051, S039) | the *Now* tick; readings 7 days back | *Started* and *Done* times on a job, entered after the fact. |
| Planned tables | Named, not built | `docs/schema.md` § Planned tables: `pm_templates`, `pm_template_items`, `pm_plans`, `pm_plan_items`, `pm_jobs`, `pm_job_results`, `pm_job_events`, `pm_routes`, `pm_route_plans` | The items below follow these names; each brief may change them. |

**What no item rebuilds:** the meters and the reading rules, the ticket flow and its dialogs, the
equipment picker (`EquipmentPicker.vue`), the property filter, the documents store, the worker and
its queue, the alert channels, the time field.

## Standards

The PM module touches the maintenance standards more than any module so far. Clause numbers already
used in Plan.MD are given plain; others are marked *to verify*.

| Standard | What it says, in plain words | How R03 follows it | Items |
|---|---|---|---|
| **TPM — planned maintenance pillar** | The maintenance team runs a planned system: it decides in advance what work each machine needs and when, does it, and learns from the results. Breakdowns fall as planned work rises. | Plans per machine, jobs that come due by themselves, the engineer's sign-off, and the compliance report. | R03.2–R03.9, R03.14 |
| **TPM — autonomous maintenance (CIL)** | Operators look after their own machines: clean, inspect, lubricate, and tag what is wrong. Cleaning *is* inspection: dirt hides leaks and cracks. A check sheet at the machine is the standard. | CIL is a PM plan done by the operator (Plan § 4.4), with Clean / Inspect / Lubricate groups and a "CIL today" list for the supervisor. A Not OK item becomes a ticket, the red tag. | R03.10, R03.12, R03.13 |
| **TPM — visual standards, one-point lessons** | Show "what good looks like" with a picture at the point of work, so anyone can judge OK or Not OK the same way. | Help text on every item (R03.2); a reference photo per item (R03.17). | R03.2, R03.17 |
| **EN 13306 — maintenance terms** (term numbers *to verify*) | *Preventive maintenance*: done to lower the chance of failure. *Predetermined*: at set intervals of time or use, without looking at condition first. *Scheduled*: by a timetable. *Condition-based*: after measuring the condition. *Inspection*: a check for conformity, with no repair. *Deferred corrective*: repair planned for later. | The trigger says which: calendar or meter is predetermined; a reading item with limits is condition-based. Item types split *task* (work done) from *check* (inspection), as Plan § 4.3 proposes. Routes are inspections. | R03.1, R03.2, R03.15, R03.16 |
| **ISO 14224 — maintenance data** (clause and table numbers *to verify*) | Record every maintenance event against the item it was done on: category (preventive or corrective), activity, date, who, man-hours, parts. Record how a failure was found (detection method: periodic maintenance, inspection, operator observation …). | One job per machine per occurrence, even on a route; labour and parts on the job; a ticket raised from a PM item carries the detection method *periodic maintenance*. Run hours are read at the level where they differ (Plan § 4.3, *Which meter a plan uses*). | R03.3, R03.10, R03.11, R03.15 |
| **ISO 55001 — asset management system** | Plan and control the work on assets (§ 8.1 *to verify*); keep the information you decided you need (§ 7.5); measure how the system performs (§ 9.1); control work done by outsiders (§ 8.3). | Plans and their history are the planned control; jobs keep their own copy of the items; compliance is the measure; AMC vendors are contractor people who perform plans, verified by the engineer. | R03.2, R03.4, R03.5, R03.14 |
| **SMRP — PM compliance** (metric number *to verify*) | The share of PM jobs due in a period that were done on time, within a set window. Rescheduled jobs are counted apart, so a plant cannot look compliant by moving dates. | The report counts jobs done within the on-time window (Q1.1) against jobs due; reschedules and skips are shown beside it (Q9.1, Q9.2). | R03.1, R03.14 |
| **SMRP — schedule compliance, planned work** (*to verify*) | Schedule compliance: the share of the work scheduled for a week that was done that week. Planned work: the share of hours spent on planned jobs. | Not measured in R03: Yantra has no weekly schedule. R03.11's labour on PM jobs gives the hours for a later planned-versus-reactive figure (Plan § 4.6, daily work log). | R03.11 (data only) |
| **ISO 9001:2015 § 7.1.3** | The organisation maintains the infrastructure it needs to make good products. | Plans and completed jobs are the evidence that machines are maintained. | All |
| **ISO 9001 § 7.1.5** | Measuring instruments are calibrated or verified at set intervals, and the results are kept. | Not built here. An in-house verification is a PM plan with reading items (Plan § 4.3, *Calibration*), so R03 builds the engine it needs; the calibration fields are in the follow-on (Q0.1). | (follow-on) |
| **ISO 9001 § 7.5.3** | Records are kept, protected from change, and show who did what and when. | A job keeps its own copy of the items from its start; every state change is an event with who and when; no drawn signature (Plan § 4.3). | R03.3, R03.4, R03.5 |
| **ISO 9001 § 9.1** | Monitor and measure what matters, and analyse it. | The PM compliance report. | R03.14 |
| **ISO 9001 § 10.2** | A nonconformity gets a recorded reaction and a corrective action. | A Not OK item or an out-of-limit reading raises a ticket linked to the job. | R03.10 |
| **ISO 27001 A.5.3 Segregation of duties** | One person should not both do and approve the same work, where the risk calls for it. | Q5.2: may an engineer verify his own job? Tickets already allow self-close (Plan § 3). | R03.5 |

## Showcase

Who uses PM and what each can do (in the app's words):

- **Engineer** (desk and phone)
  - I write a PM plan on a machine: its items, *every 1 month or 250 h*, who does it. (01)
  - I write a template once, *Press — monthly hydraulic check*, and apply it to every hydraulic
    press at SSVT, leaving out the one out of use. (05)
  - I see each finished job, its Not OK items and readings, and I *Verify job* or *Send back* with
    a remark. (04)
  - I push a job to a later date with a reason, after a good oil analysis.
- **Technician** (phone)
  - I open *PM* and see my jobs: due, overdue, upcoming. (02)
  - I start a job and fill it item by item: OK / Not OK / NA, a reading with its limits, a photo
    where needed. A reading out of limits turns red as I type. (03)
  - When I mark it done, Yantra offers a defect ticket for each Not OK item, already filled in.
- **Production supervisor** (phone)
  - I see *CIL today* for my packing line. For each machine I tap *All OK* or fill it item by item,
    naming the operator who did the check. (06)
- **Operator** (phone, later the kiosk)
  - I scan the machine's QR and tap *Start CIL* before I run it.
- **Fitter without a phone, with an engineer** (phone)
  - We walk the genset round together. The engineer records each stop for me: fuel level, battery,
    *All OK*. (07)
- **Maintenance manager** (desk)
  - I see PM compliance per unit for the month, the overdue jobs and the skips with their
    reasons. (08)
- **AMC vendor** (no login)
  - The compressor's A check is a plan assigned to the vendor. The engineer records the visit and
    attaches the vendor's report.

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R03.1 | Scheduling core: when a plan's next job is due, upcoming, overdue, on time (pure functions) | M | full | — | open |
| R03.2 | PM plans on a machine, written by hand: items, triggers, performer, assignee | L | full | — | open |
| R03.3 | Jobs come due: the daily run, `PM-` serials, the *PM* list, due jobs on the equipment page | L | full | R03.1, R03.2 | open |
| R03.4 | Do the job on the phone: start, fill items, readings to meters, done; *Open work* on *Me* | L | full | R03.3 | open |
| R03.5 | Verify and send back: the engineer's sign-off | M | full | R03.4 | open |
| R03.6 | Photos on job items, and the photo setting enforced | M | full | R03.4 | open |
| R03.7 | Alerts: PM job due, PM job overdue | S–M | full | R03.3 | open |
| R03.8 | PM templates: write once, apply to a class | L | full | R03.2 | open |
| R03.9 | Reschedule and skip, each with a reason | S | full | R03.3 | open |
| R03.10 | A ticket from a Not OK item or an out-of-limit reading | M | full | R03.4 | open |
| R03.11 | Labour and parts on PM jobs | M | full | R03.4 | open |
| R03.12 | CIL by operators: Clean / Inspect / Lubricate, the supervisor's *CIL today* | L | full | R03.5, R03.6 | open |
| R03.13 | CIL before use: *Start CIL* from the machine's QR | S | full | R03.12 | open |
| R03.14 | PM compliance report and the overdue list | M | full | R03.5, R03.9 | open |
| R03.15 | PM routes: one walk, many machines | L | full | R03.4, R03.12 | open |
| R03.16 | A ticket's target by meter value (deferred work) | M | full | R03.1 | open |
| R03.17 | Reference photos on items: what good looks like | M | full | R03.6, R03.8 | open |

**Size and the step rule (fact):** the step skill asks a split when a step adds more than one table
and two screens. R03.2, R03.3, R03.8 and R03.15 each add **two** tables: a record and its lines (a
plan and its items; a job and its events; a template and its items; a route and its stops). Each
is one concern with at most two screens. If a brief passes 25 files, it splits there.

### R03.1 — Scheduling core

- **Goal:** one pure module decides, for a plan, when its next job is due and how a job stands:
  not yet, upcoming, due, overdue, done on time or late. No DB, no clock, no Flask (CLAUDE-COMMON
  *Pure core, thin shell*); unit tests first.
- **What it decides:**
  - Calendar: every N days, weeks or months, **from the last job's done time** (Plan § 4.3,
    decided). Month arithmetic is explicit: one month after 31-01 is 28-02 (or 29-02).
  - Meter: every N units of one counter meter, from the reading at the last done time (Q1.2).
  - Both: whichever comes first; a done job restarts both (OEM practice, Plan § 4.3).
  - The first job of a new plan: from a *Last done* date and meter value typed by the engineer, or
    from the plan's start date when nothing was done before.
  - Upcoming: the window before due when the job shows (Q3.1). Overdue: past due. On time: done
    within the window of Q1.1. A rescheduled due date (R03.9) replaces the computed one.
  - A meter plan with no reading yet: "No reading yet", never due by meter.
- **After it:** nothing on screen. R03.3 shows its answers.
- **Standards:** EN 13306 (predetermined, scheduled), SMRP PM compliance (the window).
- **Migrations:** none. **Leaves for later:** forecasts by usage rate (a meter's average per day
  to guess a date), a fixed-rhythm option (Plan decided floating).

### R03.2 — PM plans on a machine

- **Goal:** an engineer writes a PM plan on any node of the tree by hand.
- **What it builds:**
  - Tables `pm_plans` (node, title, performer *maintenance* or *operator*, default assignee from
    Team, needs-verification flag (Q5.1), calendar interval, meter type and interval, *last done*
    seed, active) and `pm_plan_items` (order, type, text, help text, unit and limits for a reading,
    optional meter, photo setting).
  - Item types per Q2.1: *Task* (done / not done), *Check* (OK / Not OK / NA), *Reading* (a value
    with limits; may name a meter of the node or an ancestor, Plan § 4.3 *Which meter a plan
    uses*).
  - The trigger column allows *before use* from the start, so R03.13 needs no migration.
  - Screens: a **PM card** on the equipment page (the node's plans, each with its trigger in words)
    and the **plan editor** (mock-up 01). Deactivating a plan stops new jobs; a plan is never
    deleted.
  - Key `pm_plan:edit` (engineer; the manager inherits; IT admin per Q2.2), in `SITE_SCOPED`.
- **After it:** engineers enter the pilot's plans (Q0.2) while R03.3 is coded.
- **Standards:** TPM planned maintenance; EN 13306 task versus inspection; ISO 55001 § 7.5.
- **Migrations:** one (two tables). **Leaves for later:** templates (R03.8), CIL groups (R03.12),
  reference photos (R03.17).

### R03.3 — Jobs come due

- **Goal:** a plan's job appears by itself when it falls due, and the team sees it.
- **What it builds:**
  - Tables `pm_jobs` (plan, node, serial `PM-YYYY-MM-NNN`, state, due date, due meter value,
    assignee, created why: calendar / meter) and `pm_job_events` (the timeline, as
    `ticket_events`).
  - A daily task `pm_generate` in `scheduled_tasks.SCHEDULE`, early morning IST: for each active
    plan, the core decides; at most **one open job per plan** (Q3.1). Meter plans use the latest
    reading, so readings typed on the evening sheet make the job next morning (Q3.2). Saving a plan
    whose job is already due creates it at once.
  - Screens: a **PM** nav item after *Tickets* (mock-up 02: *Due*, *Upcoming*, *Done*; filters by
    unit and *assigned to me*), and the open job on the equipment page's PM card.
  - Key `pm_job:read` (operator and up; IT admin per Q2.2), in `SITE_SCOPED`.
- **After it:** a technician sees his PM jobs on the phone; nobody fills them yet.
- **Standards:** ISO 14224 (one record per machine per event); ISO 9001 § 7.5.3.
- **Migrations:** one (two tables). **Leaves for later:** alerts (R03.7), the forecast view.
- **Note (fact):** the worker must run for jobs to appear; Settings' *Background tasks* card
  already shows an overdue daily task (`scheduled_tasks.is_overdue`).

### R03.4 — Do the job on the phone

- **Goal:** the first usable slice. A technician starts a job, fills it and marks it done.
- **What it builds:**
  - Table `pm_job_results`: one row per item, **copied from the plan at *Start*** (so a job not
    started follows plan edits; a started job keeps its copy, Plan § 4.3a "never rewrites
    history").
  - The **job page** (mock-up 03): one item per row, large OK / Not OK / NA buttons, readings
    flagged *High* / *Low* as typed; each item saved as it is filled, so a network drop loses at
    most one item; *Mark job done* once every item is filled.
  - *Performed by* (anyone with a membership at the site; default me) and the *Started* / *Done*
    times with the *Now* tick, up to 7 days back: *recorded on behalf* (Plan § 4.3, decided).
  - A reading item that names a meter writes a `meter_readings` row with source `pm` through
    `meters.log_reading`'s locked path, refactored into one shared function (CLAUDE.md
    § SMTW-Review, *Meter readings*). A refused counter value shows on the item.
  - *Me* › *Open work* lists my open PM jobs beside my tickets.
  - Key `pm_job:work` granted to the technician here; R03.12 widens it to the operator.
  - Without R03.5 every job ends at *done*.
- **After it:** PM works end to end on the pilot machines, without sign-off.
- **Standards:** TPM planned maintenance; EN 13306 inspection; ISO 14224; ISO 9001 § 7.5.3.
- **Migrations:** one (one table). **Leaves for later:** photos (R03.6), tickets from items
  (R03.10), labour and parts (R03.11).

### R03.5 — Verify and send back

- **Goal:** the engineer signs off a finished job, or sends it back with a remark (Plan § 4.3,
  decided: due → in progress → done → verified).
- **What it builds:** a *To verify* tab (mock-up 04); *Verify job* and *Send back* (remark
  required); the needs-verification flag takes effect (Q5.1); self-verification per Q5.2; the
  job's timeline on its page. Key `pm_job:verify` (engineer), in `SITE_SCOPED`. A sent-back job's
  next due date counts from its new done time.
- **After it:** the full PM loop of Plan § 4.3.
- **Standards:** ISO 9001 § 7.5.3; ISO 27001 A.5.3 (Q5.2); ISO 55001 § 8.3 (AMC work verified).
- **Migrations:** none. **Leaves for later:** a verification due-time alert.

### R03.6 — Photos on job items

- **Goal:** evidence where the plan asks for it (Plan § 2: "jobs filled on the phone with photos").
- **What it builds:** *Add photo* on a job item, through the documents store (S006): a new owner in
  `equipment_documents` (the CHECK grows to four owners); thumbnails; *required* photos block *Mark
  job done*; removed photos restored or purged in Settings (S008).
- **Standards:** ISO 9001 § 7.5.3 (evidence on the step that produced it, Plan § 4.3).
- **Migrations:** one (a column and the CHECK). **Leaves for later:** reference photos (R03.17).
- **Device check:** a real camera on an Android phone and the iPhone (`docs/steps/device-checks.md`).

### R03.7 — Alerts: PM job due, PM job overdue

- **Goal:** the assignee hears that a job is due; overdue jobs reach someone who acts (Plan § 4.7).
- **What it builds:** two alert kinds in `alerts_core` (push): *PM job due* to the assignee when the
  daily run makes it due; *PM job overdue*, once, to the assignee and, while Telegram is parked, to
  the unit's engineers (Q7.1). A contractor assignee (no login) is skipped; the engineers get it.
- **Standards:** TPM (planned work done when planned).
- **Migrations:** none. **Leaves for later:** the daily summary email (Plan § 4.7, phase 5).

### R03.8 — PM templates

- **Goal:** write the work once and apply it to every machine of a class (Plan § 4.3, decided).
- **What it builds:**
  - Tables `pm_templates` and `pm_template_items` (the same item shape).
  - *Masters › PM templates*: the list and the editor (the plan editor's parts reused).
  - *Apply to equipment* (mock-up 05): class, site / unit, the S062 property filter; every node of
    the class at any level; untick exceptions; a node that already has a plan from this template is
    shown and cannot be ticked; one *first job due* date and assignee. One plan per node, with
    `template_id`.
  - Template edits reach plans per **Q8.1** (Plan open question 6).
  - Templates are site-less masters, so `pm_plan:edit` at any site edits them (the union, as
    failure codes); applying creates plans only at sites where the key is held.
- **After it:** the presses' monthly check on 14 presses in one dialog.
- **Standards:** TPM planned maintenance; ISO 14224 (a class = equipment whose data compare).
- **Migrations:** one (two tables). **Leaves for later:** spreading first due dates over days, so
  14 jobs do not fall due on one morning (the engineer applies in batches until then).

### R03.9 — Reschedule and skip

- **Goal:** the engineer moves a due job to a new date or meter value, or skips it, always with a
  reason (Plan § 4.3 and Maintenance-Philosophy § 7, *Rescheduling*, proposed: "skipping without a
  reason is not allowed").
- **What it builds:** *Reschedule* and *Skip* on a due job (`pm_job:verify` holders); events with
  the reason; how each counts per **Q9.1** and **Q9.2**.
- **Standards:** SMRP (PM rescheduled is tracked).
- **Migrations:** none.

### R03.10 — A ticket from a Not OK item

- **Goal:** what a job finds becomes a ticket, the red tag (Plan § 4.3, decided: "raise a breakdown
  ticket from it in one tap").
- **What it builds:** at *Mark job done*, each Not OK check and out-of-limit reading without a
  ticket offers a defect ticket, already filled in (machine, item text, remark, the job's photo
  linked), per **Q10.1**; *Raise ticket* stays on the item too. `tickets.source` gains `pm`, and the
  ticket links its job result; the ticket page shows "From PM-…". The detection method *periodic
  maintenance* (ISO 14224) follows from the source.
- **Standards:** ISO 14224 detection method; ISO 9001 § 10.2; TPM red tag.
- **Migrations:** one (`tickets`: a source value and a link column; no existing row changes).

### R03.11 — Labour and parts on PM jobs

- **Goal:** who worked and how long, and the parts fitted, on a PM job as on a ticket (Plan § 4.2,
  "PM jobs decided with PM"; Plan Q21).
- **What it builds:** *Add labour* and *Add part* on the job page, the same dialogs as S018 and
  S020, per **Q11.1**. The brief chooses between a job column on `ticket_labour` /
  `ticket_parts` (one owner of two) and two new tables.
- **Standards:** ISO 14224 (man-hours, parts replaced); SMRP planned-work hours (data only).
- **Migrations:** one.

### R03.12 — CIL by operators

- **Goal:** CIL becomes a PM plan done by the operator (Plan § 4.4, decided), recorded on the phone
  or by the supervisor.
- **What it builds:**
  - Items grouped *Clean*, *Inspect*, *Lubricate* (Clean and Inspect required, Lubricate optional;
    Maintenance-Philosophy § 5).
  - `pm_job:work` widened to the operator; **which** jobs a user works follows the plan's performer
    and the user's units (Plan § 3, decided): an operator works CIL jobs at his units only.
  - *CIL today* (mock-up 06): per unit, each machine with *All OK* or *Fill item by item*, and
    *Performed by* naming the operator (operators without a login included, S017).
  - Verification off by default for CIL (Q5.1).
- **Standards:** TPM autonomous maintenance (the check sheet); ISO 14224 (who did it).
- **Migrations:** one (the item group). **Leaves for later:** the kiosk (Plan § 2, not in v1).

### R03.13 — CIL before use

- **Goal:** before-use CIL: the operator starts it from the machine's QR (Plan § 4.4, decided).
- **What it builds:** *Start CIL* on the equipment page for a plan with the *before use* trigger;
  at most one such job per machine per IST day; it shows on *CIL today* as not done until done.
  Never overdue, and left out of compliance: missed before-use checks are not detected in v1
  (Plan § 2, *Not in v1*).
- **Migrations:** none (R03.2's trigger allows it).

### R03.14 — PM compliance report

- **Goal:** the measure of the PM programme (Plan § 4.6; Maintenance-Philosophy § 10).
- **What it builds:** a *Compliance* tab on *PM* (mock-up 08): per month, site, unit and plan, jobs
  due, done on time (Q1.1), late, skipped, still open; reschedules beside it (Q9.1); the overdue
  list; print. Key `report:read` (engineer and manager, Plan § 3), in `SITE_SCOPED`.
- **Standards:** SMRP PM compliance; ISO 9001 § 9.1; ISO 55001 § 9.1.
- **Migrations:** none. **Leaves for later:** Excel export (Plan § 4.6), the dashboard.

### R03.15 — PM routes

- **Goal:** one walk, many machines (Plan § 4.3 *PM routes*, proposed; Plan Q22): the genset round,
  the EB meter walk, the fleet's monthly inspection.
- **What it builds:** tables `pm_routes` and `pm_route_stops` (a plan per stop, in walking order,
  one performer); the route editor; the **route screen** (mock-up 07): each stop's due job, *All
  OK* per stop, readings inline, an undone stop stays due on its own machine. Jobs stay one per
  machine (ISO 14224). The pilot route per **Q15.1**.
- **Standards:** EN 13306 inspection; SMRP inspection and lubrication routes; ISO 14224.
- **Migrations:** one (two tables). **Leaves for later:** verification rounds (Plan § 4.1) as a
  route kind.

### R03.16 — A ticket's target by meter value

- **Goal:** defer a defect "until 1,000 run hours from now", not only to a date (Plan § 4.2, S019:
  "later, with the PM engine … reusing the meter-trigger machinery").
- **What it builds:** the *Defer* / *Put on hold* dialog gains *or at a meter value* (a counter
  meter of the node or an ancestor); the ticket reads *Overdue* when the latest reading passes it,
  computed by R03.1's core.
- **Migrations:** one (`tickets`: meter type and target value). Per **Q16.1**.

### R03.17 — Reference photos on items

- **Goal:** TPM's visual standard on every item: the correct oil level, the grease nipple, a worn
  scraper beside a new one (Plan § 4.3, *Item types*).
- **What it builds:** a reference photo on template and plan items, shown on the job item; a plan
  made from a template shows the template's photo.
- **Migrations:** one (owners in `equipment_documents`). **Leaves for later:** procedures
  (Plan § 4.3a).

## Order

**Milestone 1 — a PM job on the phone (R03.1–R03.5, about 7 step-days).**

1. **R03.1 ∥ R03.2 first, in parallel.** The core is a new pure file; the plans are a migration
   and screens. They share no file, and R03.2 does not call the core (the next-due line comes with
   R03.3). The core first follows CLAUDE-COMMON *Pure core, thin shell*.
2. **R03.3**, then **R03.4.** After R03.4 a technician fills a real job on the pilot machines
   (Q0.2). This is the first usable slice.
3. **R03.5.** The engineer's sign-off closes Plan § 4.3's loop.

**Milestone 2 — the full PM job (R03.6–R03.11, about 6 step-days).**

4. **R03.6 ∥ R03.7.** Photos change the documents store and the job page; alerts change
   `alerts_core`, `task_handlers` and the daily schedule. One migration between them (R03.6).
5. **R03.8 ∥ R03.9.** Templates are Masters screens and a migration; reschedule and skip are the
   job page and no migration. Templates come here, not earlier, because the pilot's few plans are
   quicker by hand, and the template editor reuses the plan editor once it has settled.
6. **R03.10**, then **R03.11** (both add a migration, so not in parallel).

**Milestone 3 — operators, measures, routes (R03.12–R03.17, about 7 step-days).**

7. **R03.12**, then **R03.13 ∥ R03.14.** CIL widens a permission, so it waits until the job page
   has settled. Before-use CIL (no migration) and the compliance report (no migration, a new tab)
   share no file.
8. **R03.15.** Routes reuse the job page's item rows and the CIL list's *All OK*.
9. **R03.16**, then **R03.17** (both add a migration).

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
R03.1 ∥ R03.2; R03.6 ∥ R03.7; R03.8 ∥ R03.9; R03.13 ∥ R03.14.

**Not in parallel:** R03.3 to R03.5 build on each other; R03.10 and R03.11 both add a migration
and change the job page; R03.16 and R03.17 both add a migration.

**Effort (estimate):** S about half a day, M about one day, L about 1.5–2 days of step time with
reviews: about **20 step-days** in all. Assumption: the briefs settle no new questions.

## Decisions for the user

**Answers (KLA, 27-10-2026, in the session; all at the recommendation):**

| Question | Answer | Note |
|---|---|---|
| Q0.1 | a | Certification, calibration, fitness-for-use and fire extinguishers: a follow-on roadmap (R04), started after R03.8. |
| Q0.2 | a | The hydraulic presses pilot PM. |
| Q1.1 | a | On time = done within 10 % of the interval, at least 1 day. |
| Q1.2 | a | A meter plan's next job counts from the reading when last done, plus N. |
| Q2.1 | a | Plan § 4.3's item shape: Task / Check / Reading, a photo setting per item, no signature. |
| Q2.2 | a | IT admin reads PM only. |
| Q3.1 | a | One open job per plan, shown as *Upcoming* a little before it is due. |
| Q3.2 | a | Meter-triggered jobs appear in the daily run. |
| Q3.3 | a | A job nobody does stays overdue until done or skipped. |
| Q5.1 | a | Verification is a flag per plan: default yes for maintenance plans, no for CIL. |
| Q5.2 | a | An engineer may verify a job they did; it is recorded. |
| Q7.1 | a | The overdue alert goes to the assignee and the unit's engineers (departs from Plan: Telegram is parked). |
| Q8.1 | a | Plans keep a copy of the template; *Update plans* sends a change to the plans the engineer ticks. |
| Q9.1 | a | A rescheduled job is on time against the new date; reschedules are counted. |
| Q9.2 | a | An engineer may skip a due job with a reason; it counts as not done. |
| Q10.1 | a | At *Mark job done*, each Not OK item without a ticket asks: *Raise defect ticket* or *No ticket* with a remark; *Raise ticket* stays on the item. Explained to KLA before the answer (departs from Plan's optional "can raise"). |
| Q11.1 | a | Labour minutes are recorded on PM jobs. |
| Q12.1 | a | CIL is part of R03. |
| Q15.1 | a | The genset round pilots routes (departs from Plan: the fleet inspection). |
| Q16.1 | a | The ticket's target by meter value is built in R03 (R03.16). |

Also accepted: the new key `pm_job:read` (not in Plan § 3's first cut).

Questions are numbered by their item, as R01's: Q3.1 is the first question of R03.3. Q0.n are about
the whole roadmap. Answer as "3.1 a".

**Q0.1. Certification plans, calibration, fitness-for-use and fire extinguishers: where?** Waits:
nothing in R03.
- **(a) A follow-on roadmap (R04), started after R03.8 — recommended.** They are PM plans with
  extra fields (valid until, certificate, calibration class) and a compliance register (Plan § 4.3,
  Q20, Q24). R03 builds the engine they need. Fire extinguishers' quarterly checks work with R03
  as plain templates.
- (b) Add them as items to R03 now. A longer roadmap; the first slice does not change.
- (c) Leave them in Plan.MD as proposed, with no roadmap.

**Q0.2. Which machines pilot PM?** Waits: R03.2 (the plans to enter), R03.4 (the device checks).
- **(a) The pressing shops' hydraulic presses (SSVT, SMTW) — recommended.** Plan § 8 named them the
  ticket pilot; their availability is the plant's worst loss; their monthly hydraulic check and
  meters (strokes, run hours, oil temperature) use every part of R03.1–R03.5.
- (b) The extrusion line (MCC1, MCC2): the gearbox oil at 5,000 h, roller shells every 60–70 h, the
  compressor AMC. Strong meter triggers; fewer machines.
- (c) Both at once. More plans to write before anything is learned.

**Q1.1. When is a job done on time?** Waits: R03.1, R03.14.
- **(a) Within 10 % of the interval after the due date, at least 1 day — recommended.** A monthly
  job is on time up to 3 days late; a yearly one up to 36 days. The SRS draft proposed it
  (Maintenance-Philosophy § 7, TBD); it is common SMRP practice. A meter plan: within 10 % of N.
- (b) A fixed grace of 3 days for every plan. Simple, but harsh on yearly plans and lax on weekly
  ones.
- (c) No grace: late from the day after due.

**Q1.2. A meter plan's next job counts from where?** Waits: R03.1.
- **(a) From the meter's reading at the last done time, plus N — recommended.** The same floating
  rule as the calendar (Plan § 4.3, decided). An oil change done at 5,040 h is next due at
  10,040 h.
- (b) From fixed marks on the dial (5,000, 10,000, 15,000 h), as some OEM tables read. A late job
  does not push the schedule out, which departs from Plan's calendar rule.

**Q2.1. Adopt the item shape Plan § 4.3 proposes?** Waits: R03.2.
- **(a) Yes: *Task*, *Check*, *Reading*; a photo setting per item (none / optional / required);
  help text on every item; no signature step — recommended.** It splits work done from inspection
  (EN 13306), and the evidence sits on the step that made it.
- (b) The older shape: checklist items (OK / Not OK / NA) and reading items, one *photo required*
  flag per plan.

**Q2.2. What may IT admin do in PM?** Waits: R03.2, R03.3.
- **(a) Read plans and jobs; not edit plans or work jobs — recommended.** Plan § 3's first cut
  gives the PM keys to no IT admin, as `reading:log` ("logging is plant work").
- (b) Everything, as for tickets (S017 decision 7). IT admin is held to the plant network, so it
  could not fill a job on the floor on mobile data anyway.

**Q3.1. When does a job appear, and how far ahead?** Waits: R03.1, R03.3.
- **(a) One open job per plan. It shows as *Upcoming* a little before due (calendar: 7 days or
  10 % of the interval, the shorter; meter: within 10 % of N), then *Due* — recommended.** The
  floating rule means the next job's date is known only once this one is done, so jobs further
  ahead cannot be fixed.
- (b) Only on the due day. Nobody can plan the week.
- (c) A calendar of future jobs for N weeks ahead, as fixed-schedule CMMS do. It conflicts with the
  floating rule: each done job would move every later one.

**Q3.2. When does a meter-triggered job appear?** Waits: R03.3.
- **(a) In the daily run, early morning, from the readings entered by then — recommended.**
  Readings come in on the evening sheet (S040), so the job is there for the morning shift. The
  reading path does not change.
- (b) At once, when the reading that crosses the mark is saved. A minute sooner; the locked reading
  path then also creates jobs.

**Q3.3. What happens to a job nobody does?** Waits: R03.3.
- **(a) It stays open and *Overdue* until done or skipped with a reason; no second job piles up —
  recommended.** It follows the floating rule and Maintenance-Philosophy § 7 ("skipping without a
  reason is not allowed").
- (b) It closes itself as *Missed* when the next would fall due. Lists stay short, but missed work
  disappears from view.

**Q5.1. Which jobs need an engineer's verification?** (Plan open question 10.) Waits: R03.5,
R03.12.
- **(a) A flag per plan: yes by default for maintenance plans, no for CIL and routine checks —
  recommended.** Plan § 4.3 proposed it (17-10-2026).
- (b) Every job. Engineers verify dozens of CIL checks a day.
- (c) None. *Done* is final; the sign-off of Plan § 2 is lost.

**Q5.2. May an engineer verify a job he did himself?** Waits: R03.5.
- **(a) Yes, recorded as such — recommended.** The plant has few engineers; tickets already allow
  self-close (Plan § 3), a recorded departure from ISO 27001 A.5.3.
- (b) No: another engineer or the manager verifies it.

**Q7.1. Who gets the *PM job overdue* alert?** Waits: R03.7.
- **(a) The assignee and the unit's engineers, by push — recommended.** Plan § 4.7 sends overdue
  to the Telegram group, which is parked (21-10-2026); without it nobody above the assignee hears.
  A departure from § 4.7's table while Telegram is parked.
- (b) The assignee only.

**Q8.1. When a template changes, what happens to its plans?** (Plan open question 6.) Waits:
R03.8.
- **(a) Plans keep their own copy. The template shows which plans differ, and *Update plans* copies
  the change to the ones the engineer ticks; a started job is never changed — recommended.** A
  machine's plan may differ on purpose (a smaller press, an older model).
- (b) A live link: plans always follow the template and cannot be edited alone.
- (c) A copy, never updated: each plan is edited by hand.

**Q9.1. A rescheduled job is on time against which date?** Waits: R03.9, R03.14.
- **(a) The new date; the report shows the number of reschedules beside the compliance figure —
  recommended.** A reasoned move (oil analysis good) is a sound decision, not a failure; the count
  shows abuse.
- (b) The original date. Every reschedule counts as late.

**Q9.2. May a due job be skipped?** Waits: R03.9.
- **(a) Yes, by the engineer, with a reason; it counts as not done; the next job counts from the
  skip — recommended.** For a machine out of use for a month, or a job made pointless by a repair.
- (b) No skip; only reschedule.

**Q10.1. How does a Not OK item become a ticket?** Waits: R03.10.
- **(a) At *Mark job done*, Yantra asks for each Not OK item without a ticket: *Raise defect
  ticket* (filled in, one tap) or *No ticket* with a remark — recommended.** Nothing found is
  forgotten. A small departure from Plan § 4.3's "can raise … in one tap", which is optional.
- (b) A ticket for every Not OK item, without asking. Plan § 4.3's fleet inspection says "every Not
  OK raises a defect ticket"; a trivial Not OK then needs closing as *not a fault*.
- (c) A *Raise ticket* button on the item only, as Plan § 4.3 reads.

**Q11.1. Record time spent on PM jobs?** Waits: R03.11.
- **(a) Yes: labour rows (person, trade, minutes) as on tickets — recommended.** It gives
  man-hours per trade for planned work (ISO 14224) and the daily work log (Plan § 4.6).
- (b) *Performed by* and the start and done times only.

**Q12.1. Is CIL part of this roadmap?** Waits: R03.12, R03.13.
- **(a) Yes, as R03.12–R03.13 — recommended.** CIL is a PM plan with the operator as performer
  (Plan § 4.4, decided): the same tables, job page and alerts.
- (b) A roadmap of its own after R03. The operators wait longer for no saving.

**Q15.1. Which route pilots PM routes?** Waits: R03.15.
- **(a) The daily genset round — recommended.** Daily, so it is tested every day; a few gensets
  already named (Plant-Facts § 4); the fitter has no phone, so it tests *recorded on behalf*. A
  departure from Plan § 4.3, which proposed the fleet.
- (b) The fleet's monthly inspection (Plan § 4.3's proposal). It needs the 40 vehicles loaded
  first, and gives feedback once a month.
- (c) The EB meter walk. Readings only; it tests less of the route.

**Q16.1. Build the ticket's meter target in R03?** Waits: R03.16.
- **(a) Yes, as R03.16, last — recommended.** S019 left it for the PM engine; R03.1 has the
  machinery.
- (b) Later, outside R03.

**Not asked again (decided in Plan.MD, followed as written):** a template applied by class, one
plan per node (§ 4.3, Maintenance-Philosophy § 7); the next calendar job from the last completion
(§ 4.3); a meter crossing creates the job by itself (§ 4.3); both triggers whichever first (§ 4.3);
job states due → in progress → done → verified, send back by the engineer (§ 4.3); recorded on
behalf (§ 4.3, § 4.4); `PM-YYYY-MM-NNN` (§ 4.3); `pm_job:work` from the operator up, which jobs
by data (§ 3); CIL as a PM plan, before use or by frequency (§ 4.4); missed before-use checks not
detected (§ 2); AMC vendors as contractor people performing plans (§ 4.3); no drawn signature
(§ 4.3).

**Departures from Plan.MD proposed here:** Q7.1 (a) (overdue alerts to engineers while Telegram is
parked); Q10.1 (a) (a prompt at *done*); Q15.1 (a) (genset round, not the fleet); a new key
`pm_job:read` not in § 3's first cut.

## Out of the roadmap and risks

**Out (fact):**
- Certification plans with *valid until* and the compliance register; calibration (instrument
  fields, classes); fitness-for-use and fleet inspections as plan kinds: the follow-on of Q0.1.
- Procedures and one-point lessons (Plan § 4.3a), and diagnostic steps on tickets: their own
  roadmap; R03's item shape is built so they can reuse it.
- The maintenance strategy field (*planned / run-to-failure / not decided*, Plan § 4.1) and a
  "machines with no plan" list. Small and useful once templates exist; proposed for the follow-on.
- Spares, stock, cost, the AMC register (Plan § 2, not in v1).
- The dashboard, Excel export, the daily summary email and the printed daily work log (phase 5).
- Shutdown and overhaul planning; a weekly schedule and SMRP schedule compliance.
- Kiosks; IIoT readings from plant-3i (source `iiot`); Vaahan's odometer feed.
- Equipment *Status: PM due* on the equipment list (the glossary's derived status): after R03.3, a
  small step if wanted.

**Risks:**
- **Content, not code, is the bottleneck (fact: Plant-Facts § 6, "no existing PM schedule").**
  Every plan's items and intervals must be written by the engineers. Q0.2's pilot keeps it small;
  makers' manuals on the models (S012) are the source.
- **Meter triggers are only as good as the readings.** A press whose run hours are not entered
  never comes due by meter. The core shows "No reading yet"; whichever-first with a calendar
  interval is the safety net.
- **A stopped worker makes no jobs.** The *Background tasks* card shows it; R03.7's alerts depend
  on it too.
- **The reading path is shared (R03.4).** A PM reading that bypasses `meters.log_reading`'s lock
  breaks the counter order rule (CLAUDE.md § SMTW-Review). R03.4 refactors, it does not copy.
- **Four items add two tables each.** They stay one concern, but a brief past 25 files splits.
- **Month arithmetic and IST.** Due dates are IST dates; the daily run is IST; the core is pure, so
  its tests fix the edge cases (31st, February, a job done just before midnight).
- **Phones and photos.** The front proxy's `Permissions-Policy: camera=()` blocks an in-page camera
  (R01.1); R03.6 uses the file input, as tickets do, so nothing breaks. A real camera check is a
  device check.
- **Floating schedules drift.** A monthly job done late every time slides through the calendar.
  That is Plan's decision; the compliance window (Q1.1) shows it.

## Slides

1. **Preventive maintenance in Yantra**
   - Plans per machine; jobs come due by date or by meter; filled on the phone; signed off by the
     engineer.
   - CIL by operators; routes for rounds; PM compliance for the manager.
   - 17 items; a technician fills a real job after the first four.
2. **The standards, in plain words**
   - TPM: maintenance plans the work; operators clean, inspect, lubricate.
   - EN 13306: *task* is work, *check* is inspection; calendar and meter are predetermined.
   - ISO 14224: one record per machine per event, with who, time and parts. SMRP: PM compliance =
     jobs done on time ÷ jobs due. ISO 9001 § 7.1.3, § 7.5.3, § 9.1, § 10.2.
3. **The engineer writes a plan** — `01-pm-plan.html`
   - Items: *Task*, *Check*, *Reading* (a reading may log the meter).
   - *Every 1 month or 250 h*, whichever comes first; next due shown at once.
4. **The technician's PM list** — `02-pm-jobs.html`
   - *Due*, *Upcoming*, *Done*; overdue in red; meter jobs show the meter now.
   - An AMC visit is a job assigned to the vendor.
5. **Filling a job on the phone** — `03-pm-job.html`
   - Large OK / Not OK / NA; a reading out of limits turns red as typed.
   - Each item is saved as it is filled; *Mark job done* when all are.
6. **The engineer verifies** — `04-verify.html`
   - Not OK items and readings at a glance; the ticket raised from one.
   - *Verify job* or *Send back* with a remark. The next job counts from the done time.
7. **A template for a whole class** — `05-apply-template.html`
   - *Press — monthly hydraulic check* applied to the presses at SSVT.
   - Untick the machine out of use; each press gets its own plan and meter.
8. **CIL today, for the supervisor** — `06-cil-today.html`
   - The packing line's six machines; *All OK* or item by item.
   - *Performed by* names the operator who did the check.
9. **A route: the daily genset round** — `07-route.html`
   - Four gensets in walking order; *All OK* per stop; fuel level typed inline.
   - Recorded by the engineer for the fitter, who has no phone.
10. **PM compliance** — `08-pm-compliance.html`
    - Per unit and month: due, on time, late, skipped, open.
    - Reschedules and skips shown with their reasons.
11. **The items as a timeline**
    - Milestone 1 (about 7 days): R03.1 ∥ R03.2 → R03.3 → R03.4 → R03.5: a signed-off job on the
      phone.
    - Milestone 2 (about 6 days): photos, alerts, templates, reschedule, tickets from items, labour
      and parts.
    - Milestone 3 (about 7 days): CIL, before-use CIL, compliance, routes, meter targets on
      tickets, reference photos.
12. **Your decisions** (recommended answer in brackets)
    - Q0.1 follow-on roadmap for certification and calibration (a); Q0.2 pilot: presses (a); Q1.1
      on time within 10 % (a); Q1.2 meter from the last done reading (a); Q2.1 the Task / Check /
      Reading shape (a); Q2.2 IT admin reads only (a).
    - Q3.1 one open job, shown a little ahead (a); Q3.2 meter jobs in the daily run (a); Q3.3
      missed jobs stay overdue (a); Q5.1 verification flag per plan (a); Q5.2 self-verification
      allowed (a); Q7.1 overdue to engineers too (a).
    - Q8.1 template changes offered to plans (a); Q9.1 reschedule against the new date (a); Q9.2
      skip with a reason (a); Q10.1 ask at done (a); Q11.1 labour on jobs (a); Q12.1 CIL in R03
      (a); Q15.1 genset round pilot (a); Q16.1 meter targets in R03 (a).

## Log

- 27-10-2026 — First version (Draft): 17 items from Plan.MD § 4.3, § 4.4, § 4.2, § 4.6 and § 4.7,
  checked against HEAD `c9142b4`; no PM code or key exists; `meter_readings.source` already allows
  `pm`. Eight mock-ups in `R03-mockups/` (with `mockup.css` for the sidebar and top bar, which live
  in scoped Vue styles). 20 questions for KLA.
- 27-10-2026 — Renumbered R02 → R03 by the orchestrator: a parallel session took R02 for annual maintenance contracts (`R02-amc-contracts.md`). Mock-ups moved to `R03-mockups/`; the follow-on roadmap of Q0.1 is now R04.
- 27-10-2026 — Gate R: KLA answered all 20 questions at the recommendation (Q10.1 after an explanation). Deck: https://claude.ai/artifact/96s6in9nPD3TkhECozuHCv. Lasting decisions recorded in Plan.MD (§ 1 and § 9).

## Feedback

- `hindrance` — The step skill's size rule ("more than one table and two screens") counts a record
  and its lines as two tables; four R03 items (plan, job, template, route) cannot be cut there.
  Evidence: `.claude/skills/step/SKILL.md:168-172`. A clause "a record and its lines count as one"
  would match how such steps are reviewed.
- `rule` — The *Roadmap mock-ups* setting names Bootstrap and `main.css` only, but the app's icons
  are Font Awesome (`frontend/src/main.js:4`) and the sidebar and top bar styles are scoped in Vue
  (`AppSidebar.vue`, `AppTopbar.vue`), so a mock-up needs both a third link and its own chrome CSS.
  Proposal: the setting names `@fortawesome/fontawesome-free/css/all.min.css` and allows a shared
  `mockup.css` in the folder.
- `idea` — `docs/roadmap/README.md` does not say how to number questions about the whole roadmap;
  this file uses Q0.n beside R01's per-item Qn.m. One line in the README would fix it.
- `waste` — Plan.MD (875 lines) holds whole step reports inside module bullets (e.g. § 4.1's
  property paragraph, § 4.5's S040 paragraph); reading it in full for PM cost most of the reading
  time. The queued *Module and schema docs* item would help the next roadmap.
