```
Roadmap: R03 — Preventive maintenance (PM)
Doc: roadmap
Author: Planner (Opus 5.5); earlier versions Roadmapper (Opus)
Date: 12-11-2026
Status: Approved (gate R, 02-11-2026, by KLA: the re-plans "one path" and "readings and
conditions"; first approved 27-10-2026). Re-planned 12-11-2026 ("rules on the meter"), gate R
waived overnight, then approved at gate R 13-11-2026 by KLA; Q22.1, Q23.1, Q23.2 answered (a) 13-11-2026; parent
meters become explicit links on the part (13-11-2026, S104 A1)
```

# R03 — Preventive maintenance (PM)

**The point (third re-plan, 12-11-2026: rules on the meter):** KLA moved the rules of a mapped
reading from the template to the meter (answers 18.3 · 2b and 18.3 · 4a). A *Meter reading* item on
a template has no limits and no rules. The **meter** carries its rules (above or below a threshold,
several per meter), and every saved reading of that meter, from any source, is checked against them.
A crossing raises a **condition ticket**: a condition-based maintenance ticket, handled like a
breakdown ticket, detected by *condition monitoring* (ISO 14224), and not counted as a breakdown. A
rule never makes a PM job, and the meter holds no corrective steps: the engineer decides the work
on the ticket. A *Measurement* item keeps its limits on the template, and a value outside them only
asks for a defect ticket at *Mark job done* (Q10.1). So: **R03.22 is dropped** (no rule makes a PM
job); **R03.23 becomes the one item for rules**, *Meter rules raise a condition ticket*, with the
rules on the meter; **R03.21 stays** as the reading hook, now for the meter's rules too; **R03.24
holds** as it was; **R03.10, R03.14 and R03.16** lose their parts about condition jobs. Milestone 1c
drops from about 4.25 to about **3.5 step-days**. KLA has **three questions** (§ Decisions): Q22.1
(shrunk: when a meter's rules may raise a new ticket), Q23.1 (where a meter's rules sit) and Q23.2
(a condition ticket re-graded *critical*). Q22.2 falls away.

**The point (second re-plan, 02-11-2026: readings and conditions):** KLA answered Q18.3, and the
answer changes the design. A template's reading item is now one of two kinds: a **Measurement**
(kept on the job) or a **Meter reading** (saved as an ordinary meter reading on the machine's own
meter of that type). A template that needs a meter type the machine does not have **does not apply**
to that machine. And a template may carry a **condition rule** (a reading above or below a limit)
that acts on **every saved reading**, from any source, by making a PM job or a ticket. So:
**R03.18 and R03.20 change**, **R03.19 changes a little**, and **four items are new**: R03.21 (act
on a reading at once), R03.22 (condition rules make a PM job), R03.23 (or a ticket) and R03.24 (a
reading logged elsewhere meets the job's reading). **R03.10 and R03.16 change**; neither merges
away. About **4.25 step-days** more. KLA has **7 new questions** (§ Decisions); Q19.2 is
answered (a); R03.18 waits for Q18.5. (*12-11-2026: the condition rule on a template, its PM job
and its* Do within N days *are replaced by the third re-plan above.*)

**The point (first re-plan, 02-11-2026: one path):** PM moves to **one path**. A PM template is
the only place work is written; it links to a class, a type, a model or one machine, and each machine's PM plans are the
templates that reach it. Three new items, **R03.18–R03.20** (about **4 step-days**), turn the coded
and held steps S096–S102 into that path; **R03.8 is merged into them**. Nothing is committed or
released until the three are done (KLA, 5b). After them the roadmap goes on as approved: photos,
tickets from items, labour, CIL, compliance, routes.

## The feature

Plan.MD § 2, module 3: "PM templates applied to equipment; plans with checklists and readings,
triggered by calendar or by meter; jobs filled on the phone with photos; engineer sign-off." The
design so far is in Plan.MD § 4.3 (template, plan, job, the shared item shape, triggers, routes,
rescheduling), § 4.4 (CIL), § 4.5 (meters), § 4.2 (tickets from PM, parts used, meter targets on
deferred work), § 3 (roles and the PM keys), § 4.6 (PM compliance) and § 4.7 (alerts). The domain
rules are in Maintenance-Philosophy § 5 (CIL) and § 7 (planned maintenance).

**One path (KLA, 02-11-2026, fact):** "a better simple way would be to define templates, link them
to model | equipment | class; each equipment thus gets a list of pm templates inherited | attached.
they become its pm plan. I believe this 'one path to do it' is better approach, rather than enabling
writing plan for each machine and a template." And: "the template defines stuff. but the actual
meter reading that triggers the PM must be per-machine". So:

- **The template holds the work:** its items, its trigger (a calendar interval and / or an interval
  of a **meter type**), the photo settings, who does it (maintenance or operator) and the
  verification flag.
- **The machine holds its own facts:** for each template that reaches it, one **plan row** with the
  assignee, *Not for this machine* (the opt-out), the *Last done* seed, and all the schedule state:
  jobs, reschedules, history. Its meters are its own (Q18.3, second re-plan): the template names a
  meter type, and the machine's own meter of that type is used, or the template does not apply.
- **One way to make a plan:** link a template. A one-off for one machine is a template linked to
  that machine only. A machine that needs different work opts out of the inherited template and gets
  its own template (KLA, 3a). Nobody edits a plan's items.

**Rules on the meter (KLA, 12-11-2026, fact):** "Mapped meters: the rules move to the meter. but the
meter need not mention all the corrective steps. it just triggers a 'condition based monitoring
triggered maintenance task' - very similar to a breakdown task. but burdening the meter with all the
steps needed to be taken is not right." And: "for a one-off reading out of limit, Only ask for a
defect ticket, as built". And earlier: "if it is a mapped meter, i guess the triggers defined on the
meter must be the ones handling it. it must not be possible to define triggers at the pm template for
mapped meters, to avoid conflicting config / confusion". So:

- **A template's *Meter reading* item** names a meter type and nothing more: no limits, no rules
  (S104's D6 already builds "no limits").
- **The meter** holds its rules: above or below a threshold, several per meter. They are checked on
  every saved reading of that meter, from a PM job, the Readings sheet, the equipment page, or an
  IIoT feed later.
- **A crossing raises a condition ticket** on the machine. The engineer works it as any ticket. It is
  not a breakdown, so it counts in no breakdown figure.
- **A *Measurement* item** keeps its limits on the template item; out of limits, *Mark job done*
  asks for a defect ticket (Q10.1). No follow-up job.

**Why now (fact):** the asset register (S001–S004, S012, S033, S043, S044, S061, S062), meters and
readings (S037–S040, S050–S052), tickets (S017–S020, S027, S034) and alerts (S021, S032) are built.
Plan.MD § 8 puts PM in phase 4, after tickets, because a Not OK item on a PM or CIL job raises a
ticket. PM's first seven items are coded (S095–S102) and held for this rework.

**Why it matters at VEL (fact, Plant-Facts § 4 and § 6):** there is no PM schedule to migrate.
Many machines run until they break, and some are forgotten. Press availability has fallen to about
70 % at times. Known preventive tasks exist only in people's heads: the extruder gearbox oil every
5,000 run hours, roller shells trued every 60–70 run hours, the compressor AMC's A / B / D checks,
the daily genset round. The presses are one class in several types, and each press is a different
model, so filters and pump elements differ per press (Plant-Facts § 4): work for every press, work
for one type and work for one model are three real layers. PM is how the plant climbs from the
reactive rung to the preventive one (Maintenance-Philosophy § 8, the maturity ladder).

**Meter values entered once, acted on at once (KLA, 02-11-2026, fact):** KLA wants PM to be
deterministic, and a meter value to be entered once, wherever it is entered (a PM job, the
Readings sheet, the equipment page, IIoT later), and acted on at once. A template with a *reading
duty* ("Check the hoist brake air gap every month or 300 h") reminds someone to read the meter; a
**rule on the meter** ("Brake air gap above 1.5 mm") acts on the value by raising a condition
ticket (changed 12-11-2026: it was a condition rule on a template).

**What it is not:** no spares or stock, no cost, no shutdown planning, no IIoT feed (but every
reading path, an IIoT feed included, goes through the one insert function, so the rules will act
on it unchanged). Certification
plans, calibration, fitness-for-use inspections and procedures are a follow-on (Q0.1, § Out).

## What exists

Checked against the working tree on 02-11-2026: HEAD `c9cd091` plus the held, uncommitted steps
S095–S103 (`git status`: `backend/pm_*.py`, `frontend/src/views/Pm*.vue`, the PM tests and specs
are untracked). Production runs release v0.1.15, whose last migration is **v50** (fact:
`git show d2287bb:backend/local_db.py`). So **v51–v56 exist only on dev and test databases**.

**Re-checked 12-11-2026 (HEAD `c7e9f0b` plus the held steps):** S104 (R03.18) is being coded; its
brief's D6 gives a *Meter reading* item no limits of its own. `tickets.source` is still
`ENUM('manual')`, and a ticket has no detection-method column. A breakdown is a ticket of intensity
*critical* (`tickets_core.BREAKDOWN_INTENSITY`, `is_breakdown`); every count of breakdowns today goes
through it (`improvements_core`, the contract calls in `contracts.py`, the down state in
`equipment.py`, the alerts). The MTBF report waits for phase 5 (Plan § 4.6). Plan § 4.2's shared
ticket API rule already says "a system that keeps flagging the same equipment adds to its open
ticket instead of opening new ones". **Correction (fact):** the question at *Mark job done* for a Not
OK item or a value out of limits (Q10.1) is not built: S098 built the red mark on the item and left
the question to R03.10 (`docs/steps/S098-pm-job-phone/1-brief.md`, *Out of scope*).

**Built in R03 so far (coded, reviewed, snapshotted, held):**

| Piece | Step | Evidence | In the rework |
|---|---|---|---|
| Scheduling core | S095 | `backend/pm_schedule_core.py` (`next_due`, `job_state`, `timeliness`), `test_pm_schedule_core.py` | **Kept as it is.** It takes plain values; it never knew where they came from. |
| Plans with their own items | S096 | `pm_plans`, `pm_plan_items` (v51); `pm_plans.py`, `pm_plans_core.py`; `PmPlanView.vue`, `PmItemDialog.vue`, `PmPlansCard.vue`; key `pm_plan:edit` (engineer, site-scoped) | **The main rework.** The work columns and the items move to the template; the plan keeps the machine's columns. The editor's parts move to the template page. |
| Jobs come due | S097 | `pm_jobs`, `pm_job_events` (v52); `pm_jobs.settle_plan_job`, the daily `pm_generate` (05:00 IST); `PmJobsView.vue`; key `pm_job:read` | **Little change.** The plan row and its lock (6e) stay; the run reads the trigger from the plan's template through one join. |
| The job on the phone | S098 | `pm_job_results` (v53), `pm_work.py`, `PmJobView.vue`; key `pm_job:work`; the reading path `meters.write_reading` | *Start* copies the **template's** active items (`plan_item_id` becomes `template_item_id`). The rest is unchanged. |
| Verify and send back | S099 | `pm_jobs.needs_verification` (v54), `PmJobVerifyDialog.vue`; key `pm_job:verify` | Mark done copies the template's flag, not the plan's. |
| Reschedule and skip | S101 | `rescheduled_on`, `rescheduled_meter` (v55); two dialogs | A change of the **template's** schedule clears the move (today: the plan's). |
| PM alerts | S102 | the four alert markers (v56), `pm_jobs.alert_scan` (08:00 IST) | Unchanged; the alert text names the template. |
| Test hygiene | S100 | three tests that depended on other tests' rows | Unchanged. |

**What R03 builds on (as in the first version, 27-10-2026):**

| Piece | State today | Evidence | How PM uses it |
|---|---|---|---|
| Equipment tree, classes, types, models | Built | `equipment` (`class_id`, `type_id`, `model_id`), `equipment_classes`, `equipment_types` (one class, many types), `equipment_models` (`class_id`, `type_id`) | A template links to a class (every node of the class at any level), a type, a model or one node. |
| Property filter | Built (S062) | `property_filter_core.py`; `GET /api/equipment?props=` | No longer used by PM: links replace *Apply* (§ R03.8). |
| Meters and readings | Built (S037–S040) | `meter_types` (kinds `counter`, `gauge`, `amount`, `yes_no`; a Yes / No type has its expected answer), `model_meters` (a model's meters: every machine of the model has them, computed live, with a gauge's default Min / Max), `node_meters` (`own` 1: a machine's own meter, *This machine only*; `own` 0: an override of the model meter's limits, kept only while it differs), `meter_readings`; `meters_core.effective_meters` (the model's meters plus the node's own), `meters.meter_in_force`; meters and limits are edited with `equipment:edit` | **Changed (Q18.3):** the template names a meter **type**, and the machine's own meter of that type is used: `meter_in_force(cur, node, model, type)` already answers it. One meter per type per node (`uq_model_meters`, `uq_node_meters`), so the answer is one meter or none. S096's search of the nodes above (`pm_plans.meter_choices`) goes. **Changed 12-11-2026:** the meter's rules follow the same two places, the model meter and the machine (R03.23, Q23.1). |
| The reading rules | Built (S039, S098) | `meters.lock_node`, `meter_in_force`, `write_reading`; CLAUDE.md § SMTW-Review, *Meter readings* | Unchanged rules. **`write_reading` is the one insert of `meter_readings`** (fact: one `insert_row(cur, "meter_readings", …)` in `backend/`; callers `log_reading`, which the S040 sheet calls row by row, and `pm_work.py`'s reading item). So it is the one place a rule can hear of every reading (R03.21). Readings go up to 7 days back (`READING_BACKDATE_DAYS`) and are removed, never edited (`remove_reading_row`). |
| Meter limits | Built (S038, S039) | a gauge's Min / Max on the model, overridden on a node; `meter_readings.limit_state` *low* / *high* / *not_ok* | **Unchanged:** they stay the *High* / *Low* display flags and raise nothing. **Changed 12-11-2026:** the meter's rules sit beside them, on the same meter (R03.23); a template's *Meter reading* item has no limits (S104 D6). |
| Job queue | Built (S013) | `task_queue.enqueue(cur, …)` adds a task in the caller's transaction; the worker polls every 5 s (`company_settings.WORKER_POLL_SECONDS`) | R03.21's reading check is one task, queued in the reading's transaction and run after its commit, as alerts are (S021). |
| Tickets | Built (S017–S020, S027, S034) | `tickets.source` is `ENUM('manual')`; intensity *critical* = breakdown, *degraded* / *initial* = defect (`is_breakdown`); LOCK ORDER (1) node → (6) counter → (7) ticket (`tickets.py`) | R03.10 adds the source `pm`, R03.23 the source `condition` (the first of the two adds both). A condition ticket is raised *initial*, so it is out of every breakdown count by its intensity (Q23.2 for a re-grade). |
| A job's reading result | Held (S098) | `pm_job_results.reading_id` and a copy of `value` (v53) | R03.24 links a reading logged elsewhere through the same column. |
| Team, contractors, site roles | Built (S010, S011, S079) | `people`, `memberships`, `ASSIGNABLE_ROLES` | The assignee stays on the machine's plan row. |
| Files and photos | Built (S006, S008, S083) | `equipment_documents`, six owners | R03.6 and R03.17 add owners. |
| Worker and daily schedule | Built (S013) | `scheduled_tasks.SCHEDULE` holds `pm_generate` and `pm_job_alert_scan` | The daily run also keeps plan rows in step (R03.19). |
| Masters | Built | `MastersView.vue` sections (Classes, Types, Models, Meter types, Failure codes, …); site-less masters such as failure codes are written with the key held at any site | *Masters › PM templates* is a new section. Masters › Models › *Meters* gains *Set rules* (R03.23). |

**What no item rebuilds:** the scheduling core, the job states and their locks, the job page, the
verification and reschedule dialogs, the alert scan, the meters and the reading rules, the ticket
flow, the equipment picker (`EquipmentPicker.vue`), the documents store, the worker, the time field.

## Standards

The PM module touches the maintenance standards more than any module so far. Clause numbers already
used in Plan.MD are given plain; others are marked *to verify*. The first re-plans added three rows
(marked *new*) and changed the TPM and ISO 55001 rows. The third re-plan (12-11-2026) changes the
EN 13306, ISO 17359, RCM, ISO 14224 data and SMRP rows (marked *changed 12-11*) and adds SMRP MTBF.

| Standard | What it says, in plain words | How R03 follows it | Items |
|---|---|---|---|
| **TPM — planned maintenance pillar** | The maintenance team runs a planned system: it decides in advance what work each machine needs and when, does it, and learns from the results. The work is written as a **standard**, once for each kind of equipment, and improved there. | **Changed:** the template is the standard; every machine it reaches does the same work. An improvement to the template reaches every machine at its next job. A machine that needs other work gets its own template, not a private edit. | R03.18–R03.20, R03.3–R03.9, R03.14 |
| **TPM — autonomous maintenance (CIL)** | Operators look after their own machines: clean, inspect, lubricate, and tag what is wrong. Cleaning *is* inspection. A check sheet at the machine is the standard. | CIL is a template done by the operator (Plan § 4.4), with Clean / Inspect / Lubricate groups and a "CIL today" list. A Not OK item becomes a ticket, the red tag. | R03.12, R03.13 |
| **TPM — visual standards, one-point lessons** | Show "what good looks like" with a picture at the point of work. | Help text on every item; a reference photo per template item (R03.17). | R03.18, R03.17 |
| **ISO 14224 — taxonomy: class, type, item** (*new*; Annex A tables *to verify*) | Equipment is grouped in **classes** (pump, compressor), each split into **types** (centrifugal, screw), so data compare across like items. Data are recorded on the item they belong to, at any level of the hierarchy (unit, subunit, maintainable item). | A template links to a class or a type, and reaches every node of it at any level: the motor greasing reaches a motor inside a press. Each event is still one job on one machine. | R03.18, R03.19 |
| **EN 13460 — documentation for maintenance** (*new*; clause *to verify*) | The maker supplies the information needed to maintain the equipment, including the preventive tasks and their intervals. | A template linked to a **model** holds the maker's schedule; every machine of that model gets it. The maker's manual is already a model document (S012). With Q23.1 (a), a model meter's rules hold the maker's wear limits for every machine of the model. | R03.19, R03.23 |
| **EN 13306 — maintenance terms** (term numbers *to verify*; *changed 12-11*) | *Preventive maintenance*: done to lower the chance of failure. *Predetermined*: at set intervals of time or use. *Condition-based maintenance*: preventive work that includes a check of the machine's condition, by measurement or inspection, and the action that the result calls for. *Inspection*: a check for conformity, with no repair. *Deferred corrective maintenance*: repair that is planned, not done at once. *Maintenance plan*: the set of tasks with their time scale. | A calendar or meter trigger is predetermined. A template with a **reading duty** is the inspection (it measures). **Changed 12-11:** the condition-based part is the **meter's rule** and its ticket: the rule assesses the condition on every reading, and the condition ticket is the action it calls for; the engineer decides the work on the ticket (KLA, 2b). A condition ticket deferred to a slot (S019) is deferred corrective work. *Task* and *Check* split work from inspection. | R03.1, R03.18, R03.21, R03.23, R03.15, R03.16 |
| **ISO 17359 — condition monitoring, general guidelines** (*new*; clause numbers and the words *alert* / *alarm* *to verify*; *changed 12-11*) | Condition monitoring is a loop: choose what to measure for each failure mode, measure it at a set interval, compare each value with set limits, and act when a limit is crossed. The limits belong to the measured point. It names two levels of limit: an early one (*alert*: plan the work) and a late one (*alarm*: act now). | The reading duty is the measurement at an interval. **Changed 12-11:** the limit and the action sit on the **meter**, the measured point, not on a template. Several rules on one meter give the two levels: 1.5 mm (alert) and 2.0 mm (alarm) on the brake air gap; both raise, or add to, the one open condition ticket of that meter (Q22.1). The rule checks every saved reading, so the comparison does not wait for a daily run (R03.21). | R03.21, R03.23, R03.24 |
| **RCM — the P-F interval** (*new*; reliability-centred maintenance, SAE JA1011, *to verify*; *changed 12-11*) | Many failures give a warning first: P is the point where the coming failure can first be found, F is the failure. A check must be made more often than the time from P to F, or it finds the fault too late. | It tells the engineer how to set a reading duty's interval (shorter than the time the brake air gap takes to grow from the first rule's threshold to failure) and where to set the first rule: near P, early enough to plan the work. Yantra cannot know the P-F interval; the engineer sets both, and the readings history shows if the interval is too long. | R03.18, R03.23 (guidance on the template page and the rules dialog) |
| **ISO 14224 — maintenance data** (clause and table numbers *to verify*; *changed 12-11*) | Record every maintenance event against the item it was done on: category, activity, date, who, man-hours, parts; how a failure was found (*detection method*); and its impact (critical, degraded, incipient). | One job per machine per occurrence, even on a route; labour and parts on the job; a ticket raised from a PM item carries the detection method *periodic maintenance*; a ticket raised by a meter's rule carries *condition monitoring*. **Changed 12-11:** a condition ticket is a finding on a running machine, raised *initial* (ISO's *incipient*), not a failure that stopped it. Run hours are read at the level where they differ: **changed (Q18.3)**, the machine's own meter of the type only, so a part whose hours differ from its machine's carries its own meter. | R03.3, R03.10, R03.11, R03.15, R03.18, R03.23 |
| **ISO 55001 — asset management system** | Plan and control the work on assets (§ 8.1 *to verify*); control changes to it (§ 8.2, *to verify*, *new*); keep the information you need (§ 7.5); measure the system (§ 9.1); control work done by outsiders (§ 8.3). | **Changed:** a template change is one controlled change with who and when; a started job keeps the items it started with; removing a link keeps the plan's history. A rule change on a machine's meter is a line in its history, as a limits change is. Compliance is the measure; AMC vendors perform plans and the engineer verifies them. | R03.18, R03.19, R03.4, R03.5, R03.14, R03.23 |
| **SMRP — PM compliance** (metric number *to verify*; *changed 12-11*) | The share of PM jobs due in a period that were done on time, within a set window. Rescheduled jobs are counted apart. | The report counts jobs done within the on-time window (Q1.1) against jobs due; reschedules and skips beside it. A plan set *Not for this machine* makes no jobs, so it is not counted as missed; the list shows it. **Changed 12-11:** a meter's rule makes a ticket, not a PM job, so PM compliance holds scheduled work only (the second re-plan counted condition jobs apart; there are none now). | R03.1, R03.14, R03.20 |
| **SMRP — MTBF** (*new 12-11*; Plan § 4.5 cites metric 3.5.1, *to verify*) | Mean time between failures: the running time divided by the number of failures. A failure is a loss of the machine's function. | Not built in R03 (phase 5). A condition ticket stays out of it while the machine runs, because it is raised *initial* and every breakdown count goes by intensity; Q23.2 decides a re-grade to *critical*. R03.23 stores the source, so the KPI work can show the detection mix (how many faults were found before they stopped the machine). | R03.23 (data only) |
| **SMRP — schedule compliance, planned work** (*to verify*) | The share of the scheduled work done in its week; the share of hours spent on planned jobs. | Not measured in R03. R03.11's labour gives the hours for a later figure. | R03.11 (data only) |
| **ISO 9001:2015 § 7.1.3** | The organisation maintains the infrastructure it needs. | Plans and completed jobs are the evidence. *PM plans that do not apply* shows where the evidence would be missing. | All, R03.20 |
| **ISO 9001 § 7.1.5** | Measuring instruments are calibrated or verified at set intervals. | Not built here (Q0.1). | (follow-on) |
| **ISO 9001 § 7.5.3** | Records are kept, protected from change, and show who did what and when. | A job keeps its own copy of the items from its start, also when the template changes later; every state change is an event; a plan row is never deleted. A rule is set inactive, never deleted, because a ticket names it. | R03.3–R03.5, R03.18, R03.19, R03.23 |
| **ISO 9001 § 9.1, § 10.2** | Monitor and measure; a nonconformity gets a recorded reaction. | The compliance report; a Not OK item raises a ticket; a reading past a meter's rule raises a condition ticket. | R03.14, R03.10, R03.23 |
| **ISO 27001 A.5.3 Segregation of duties** | One person should not both do and approve the same work, where the risk calls for it. | Q5.2 (a): an engineer may verify his own job; it is recorded. | R03.5 |

## Showcase

Who uses PM and what each can do (in the app's words):

- **Engineer** (desk and phone)
  - I write a template once in *Masters › PM templates*: *Press — monthly hydraulic check*, its
    items, *every 1 month or 250 h of Run hours*. (09)
  - I link it to the class *Hydraulic press*. Every press gets it as a PM plan, at once, and a new
    press gets it the day it is added. I see each press and how its plan stands. (10)
  - I link the maker's filter change to the press's model, and a prefill valve check to the type
    *Pilot-operated with prefill*. (10, 11)
  - On HP003 I see its plans and where each comes from: from class, from model, from type, this
    machine. HP003 has an auto-lube unit, so I set the weekly lubrication *Not for this machine*,
    say why, and attach its own *Auto-lube unit check*. (11)
  - Each morning I see *PM plans without an assignee* and *PM plans that do not apply*, and fix
    them: assign three plans to Technician B at once, add the missing Run hours meter. (12)
  - On a template I choose what each reading is: a *Measurement* that stays on the job, with its
    own limits, or a *Meter reading* that is saved on the machine's own meter of that type, with no
    limits on the template. I see at once which machines have that meter, and which ones the
    template does not apply to, and why. (14)
  - On the crane model's *Brake air gap* meter I add a rule: above 1.5 mm. Every crane of the model
    has it. EOT02 has older pads, so on its *Meters* card I set its own rules: above 1.5 mm, and
    above 2.0 mm with the note *Pads near the end*. A crossing raises a condition ticket on the
    crane, and I decide the work on the ticket, as for a breakdown. (16)
  - I see each finished job, its Not OK items and readings, and I *Verify job* or *Send back*. (04)
  - I move a due job to a later date with a reason, after a good oil analysis.
- **Technician** (phone)
  - I open *PM* and see my jobs: due, overdue, upcoming. (02)
  - I start a job and fill it item by item: OK / Not OK / NA, a reading with its limits, a photo
    where needed. A reading out of limits turns red as I type. (03)
  - The supervisor already read the brake air gap on the Readings sheet this morning. My job shows
    "Already read: 1.2 mm · Today 09:40 · Supervisor A", and I need not read it again. (15)
  - A brake air gap of 1.6 mm, saved on the Readings sheet at 17:50, raises ticket TK-2026-11-031 on
    EOT02 a few seconds later: *Defect · initial*, *Condition monitoring*, with the reading that
    raised it. The engineer assigns it to me; I adjust the brake, log the new gap, and tap *Fixed*.
    (17)
- **Production supervisor** (phone)
  - I see *CIL today* for my packing line and tap *All OK* or fill item by item, naming the
    operator. (06)
  - I enter the day's readings once, on the Readings sheet. Any PM job that needed them counts
    them, and the meters' rules act on them at once.
- **Fitter without a phone, with an engineer** (phone)
  - We walk the genset round together; the engineer records each stop for me. (07)
- **Maintenance manager** (desk)
  - I see PM compliance per unit and per template for the month, the overdue jobs and the skips
    with their reasons. (08)
  - The condition tickets are defects found before a stop; they are not in my breakdown figures.
- **AMC vendor** (no login)
  - The compressor's A check is a template linked to the compressor's model; its plans are assigned
    to the vendor. The engineer records the visit and attaches the vendor's report.

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R03.1 | Scheduling core: when a plan's next job is due, upcoming, overdue, on time (pure functions) | M | full | — | → S095, 01-11-2026 (held) |
| R03.2 | PM plans on a machine, written by hand: items, triggers, performer, assignee | L | full | — | → S096, 01-11-2026 (held; reworked by R03.18) |
| R03.3 | Jobs come due: the daily run, `PM-` serials, the *PM* list, due jobs on the equipment page | L | full | R03.1, R03.2 | → S097, 01-11-2026 (held) |
| R03.4 | Do the job on the phone: start, fill items, readings to meters, done; *Open work* on *Me* | L | full | R03.3 | → S098, 01-11-2026 (held) |
| R03.5 | Verify and send back: the engineer's sign-off | M | full | R03.4 | → S099, 02-11-2026 (held) |
| R03.6 | Photos on job items, and the photo setting enforced | M | full | R03.4, R03.18 | open |
| R03.7 | Alerts: PM job due, PM job overdue | S–M | full | R03.3 | → S102, 02-11-2026 (held) |
| R03.8 | PM templates: write once, apply to a class | L | full | R03.2 | dropped — merged into R03.18–R03.20 (02-11-2026) |
| R03.9 | Reschedule and skip, each with a reason | S | full | R03.3 | → S101, 02-11-2026 (held) |
| R03.10 | A ticket from what the technician finds: a Not OK item, a *Measurement* out of its limits. **Changed 12-11:** a *Meter reading* item never asks; the meter's rules handle its reading (R03.23) | M | full | R03.4, R03.18 | open |
| R03.11 | Labour and parts on PM jobs | M | full | R03.4, R03.18 | open |
| R03.12 | CIL by operators: Clean / Inspect / Lubricate, the supervisor's *CIL today* | L | full | R03.5, R03.6, R03.19 | open |
| R03.13 | CIL before use: *Start CIL* from the machine's QR | S | full | R03.12 | open |
| R03.14 | PM compliance report and the overdue list | M | full | R03.5, R03.9, R03.18 | open |
| R03.15 | PM routes: one walk, many machines | L | full | R03.4, R03.12 | open |
| R03.16 | A ticket's target by meter value (deferred work); the machine's own meter of the type, checked on every reading save | M | full | R03.1, R03.21 | open |
| R03.17 | Reference photos on template items: what good looks like | M | full | R03.6, R03.18 | open |
| R03.18 | **One path:** templates hold the work in *Masters › PM templates*; a machine's plans are rows linked to them; *Attach PM template* on a machine; one migration replaces v51–v56. **Changed:** two reading kinds (*Measurement*, *Meter reading*); meters matched by type on the machine's own meters; a template that needs a missing meter does not apply | L | full | R03.1–R03.5, R03.7, R03.9 (held code) | → S104, 02-11-2026 |
| R03.19 | **Links by class, type and model**, kept in step when a link, a machine, or its class, type or model changes; *Not for this machine* | M–L | full | R03.18 | open |
| R03.20 | **The engineer's lists:** PM plans without an assignee, PM plans that **do not apply** (changed: a missing meter, no meter to pick); assign many at once | S–M | full | R03.19 | open |
| R03.21 | **Act on a reading at once:** every saved reading queues one check after its commit; it settles the PM plans that use the meter (the meter trigger no longer waits for 05:00), and is the hook for the meter's rules (R03.23) and ticket targets (R03.16) | M | full | R03.18 | open |
| R03.22 | ~~Condition rules make a PM job~~ | — | — | — | dropped (12-11-2026): a crossing never makes a PM job (KLA, 2b); the rule moves to the meter, R03.23 |
| R03.23 | **Meter rules raise a condition ticket (changed 12-11):** rules (above / below a threshold, several per meter) sit on the meter; every saved reading is checked; a crossing raises a condition-based maintenance ticket, handled like a breakdown ticket and out of the breakdown counts (KLA, 2b) | L | full | R03.21 | open |
| R03.24 | **A reading logged elsewhere counts:** a job's meter reading is met by a reading of that meter logged since the job came due (KLA, 3a) | S–M | full | R03.18 | open |

**Size and the step rule (fact):** the step skill asks a split when a step adds more than one table
and two screens, or passes about 25 files. R03.18 changes six unreleased tables (one new table of
links; the rest move columns between a template and a plan) and its test set-up edits are many but
mechanical; its split point is named in its section. R03.3, R03.15 each add a record and its lines.
R03.23 adds one table (the rules) and changes two screens (the *Meters* card, Masters › Models ›
*Meters*) plus a line on the ticket page; its split point is named in its section.

### R03.1 — Scheduling core (→ S095, held)

- **Goal:** one pure module decides, for a plan, when its next job is due and how a job stands.
  Built as `pm_schedule_core.py` (Plan § 4.3, *Built (S095)*).
- **In the re-plan:** kept as it is. Its inputs (interval, meter value, last done, seed, override)
  now come from the template and the machine's plan row together; the core does not change.
  (12-11-2026: `KINDS` gains no `condition`; R03.22 is dropped.)

### R03.2 — PM plans on a machine (→ S096, held; reworked by R03.18)

- **Goal as built:** an engineer writes a PM plan by hand on any node: title, items, trigger,
  performer, assignee, verification flag, *Last done* seed (Plan § 4.3, *Built (S096)*).
- **In the re-plan (KLA, 1a):** writing a plan by hand goes. The title, items, trigger, performer
  and verification flag move to the template (R03.18); the node, assignee, *Last done* seed and
  active state stay on the plan row. S096's rules move with their fields: items synced by id and
  never deleted, the meter rule (`meter_choice_error`: a counter for the trigger; **second re-plan:**
  its search of the nodes above goes, and the template's meter types are checked against the
  machine's own meters, R03.18), the assignee rule (`ASSIGNABLE_ROLES` at the node's site), the plan
  row lock (6e) first, then the node shared, scrapped refused.

### R03.3 — Jobs come due (→ S097, held)

- **Goal as built:** a plan's job appears by itself when it falls due (Plan § 4.3, *Built (S097)*).
- **In the re-plan:** `settle_plan_job` and the daily `pm_generate` read the trigger through the
  plan's template. A plan runs when it is **in force**: linked, not *Not for this machine*, its
  template active, its machine not scrapped. A plan that stops being in force cancels its open, not
  started job with a timeline line, as S097's deactivation does (D7).

### R03.4 — Do the job on the phone (→ S098, held)

- **Goal as built:** start, fill item by item, readings to meters, done (Plan § 4.3, *Built (S098)*).
- **In the re-plan (KLA, 2a):** *Start* copies the **template's** active items into
  `pm_job_results`. A job not started follows template edits; a started job keeps its copy.
- **In the second re-plan (Q18.3):** a *Meter reading* item logs its value on the job's own node's
  meter of the item's type, through `write_reading` as today; a *Measurement* item keeps its value
  on the job only. The result row's `meter_equipment_id` goes: the meter is always the job's node's.
  R03.24 lets a reading logged elsewhere fill a meter reading item.
- **12-11-2026:** a *Meter reading* item's value is checked by the meter's rules like any reading
  (R03.21's task, R03.23), because it goes through `write_reading`. Nothing on the job decides.

### R03.5 — Verify and send back (→ S099, held)

- **In the re-plan:** *Mark job done* copies the template's *An engineer verifies each job* into
  `pm_jobs.needs_verification`. Nothing else changes.

### R03.6 — Photos on job items

- **Goal:** evidence where the template asks for it (Plan § 2: "jobs filled on the phone with
  photos").
- **What it builds:** *Add photo* on a job item, through the documents store (S006): a new owner in
  `equipment_documents`; thumbnails; *required* photos block *Mark job done*; removed photos
  restored or purged in Settings (S008).
- **Standards:** ISO 9001 § 7.5.3. **Migrations:** one. **Device check:** a real camera on an
  Android phone and the iPhone.

### R03.7 — Alerts: PM job due, PM job overdue (→ S102, held)

- **In the re-plan:** unchanged. A plan with no assignee sends *PM job due* to nobody, and *overdue*
  to the unit's verifiers only (S102's rule); R03.20's list is where the engineer fixes it.

### R03.8 — PM templates (dropped — merged into R03.18–R03.20, 02-11-2026)

- **Why:** KLA's one path (1a) makes the template the only place work is written, so templates are
  no longer a second way beside hand-written plans; they are the base the plans stand on.
- **Where its parts went:** the tables and *Masters › PM templates* → R03.18; links to a class (in
  place of *Apply to equipment*), the untick of exceptions (now *Not for this machine*) → R03.19;
  the first job's spread → R03.19's leftover; the site-less master and its key → Q18.4.
- **Replaced decision:** Q8.1 (a), "plans keep a copy; *Update plans*", is replaced by KLA's 2a: a
  live link. The *Apply* dialog with the property filter (mock-up 05) is dropped: a link reaches the
  whole class, and the engineer opts a machine out.

### R03.9 — Reschedule and skip (→ S101, held)

- **In the re-plan:** a change of the template's schedule clears a due job's move on every plan of
  the template (S101: "a schedule edit of the plan clears it"). A plan-row edit (assignee, meter,
  *Last done*) keeps it.

### R03.10 — A ticket from what the technician finds

- **Goal:** what a job finds becomes a ticket, the red tag (Plan § 4.3).
- **What it builds:** at *Mark job done*, each Not OK check and each *Measurement* out of its limits
  without a ticket offers a defect ticket, already filled in, per **Q10.1** (*Raise defect ticket*
  or *No ticket* with a remark). S098 built the red mark on the item, not this question. *Raise
  ticket* stays on every item, by hand. `tickets.source` gains `pm`, the detection method is
  *periodic maintenance*, and the ticket links its job result.
- **Changed 12-11-2026 (KLA, 2b and 4a):** a *Meter reading* item **never asks**. Its reading was
  checked by the meter's rules when it was saved (R03.23), so the template and the meter never both
  decide on one value (KLA: "to avoid conflicting config"). The item shows the meter's *High* /
  *Low* mark, and the condition ticket its reading raised or added to, if any ("Ticket
  TK-2026-11-031, raised by the meter's rule above 1.5 mm"). A technician who sees more than the rule
  does still taps *Raise ticket* on the item. The second re-plan's "offered only when no condition
  rule made a job or a ticket" goes.
- **Merge or not:** R03.10 stays an item: a person judges on the job. R03.23's rule raises a ticket
  by itself. The two share one ticket-raising function (named by the first brief), so the ticket's
  form is the same; R03.16's note says how the three ticket items meet.
- **Standards:** ISO 14224 detection method; ISO 9001 § 10.2; TPM red tag. **Migrations:** one
  (`tickets.source` gains `pm`, and `condition` too if R03.23 is not built yet; the job result link).

### R03.11 — Labour and parts on PM jobs

- **Goal:** who worked and how long, and the parts fitted, on a PM job as on a ticket (Q11.1).
- **What it builds:** *Add labour* and *Add part* on the job page, the dialogs of S018 and S020.
- **Standards:** ISO 14224 (man-hours, parts replaced). **Migrations:** one.

### R03.12 — CIL by operators

- **Goal:** CIL becomes a template done by the operator (Plan § 4.4), linked by class like any
  template, recorded on the phone or by the supervisor.
- **What it builds:** items grouped *Clean*, *Inspect*, *Lubricate* (a template item field);
  `pm_job:work` widened to the operator for operator templates at his units; *CIL today* (mock-up
  06); verification off by default for operator templates (Q5.1).
- **Standards:** TPM autonomous maintenance; ISO 14224. **Migrations:** one (the item group).

### R03.13 — CIL before use

- **Goal:** *Start CIL* from the machine's QR for a template with the *before use* trigger; at most
  one such job per machine per IST day; never overdue, left out of compliance.
- **Migrations:** none (the template's trigger column allows it, R03.18).

### R03.14 — PM compliance report

- **Goal:** the measure of the PM programme (Plan § 4.6).
- **What it builds:** a *Compliance* tab on *PM* (mock-up 08): per month, site, unit and **template**
  (new: one template's on-time rate across all its machines shows a template that is too heavy),
  jobs due, on time, late, skipped, open; reschedules beside it; the overdue list; print. Key
  `report:read`.
- **Changed 12-11-2026:** no rule makes a PM job any more (R03.22 dropped), so every job in the
  report is scheduled work, and the second re-plan's "condition jobs counted apart, against their
  *Do within* window" goes. Condition tickets are tickets; they are not in PM compliance.
- **Standards:** SMRP PM compliance; ISO 9001 § 9.1. **Migrations:** none.

### R03.15 — PM routes

- **Goal:** one walk, many machines (Plan § 4.3 *PM routes*): the genset round first (Q15.1).
- **What it builds:** `pm_routes` and `pm_route_stops` (a machine's plan per stop, in walking order);
  the route editor; the route screen (mock-up 07). Jobs stay one per machine.
- **Migrations:** one (two tables).

### R03.16 — A ticket's target by meter value

- **Goal:** defer a defect "until 1,000 run hours from now" (Plan § 4.2, S019), computed by R03.1.
- **Changed in the second re-plan:** the target names a meter type, and the ticket's machine's own
  meter of that type is used (Q18.3's rule); a machine without one offers no meter target. The
  target is checked on every saved reading through R03.21's task, as well as in the daily run, so
  a deferred ticket reads *Overdue* the moment the reading passes it.
- **Where R03.10, R03.16 and R03.23 meet (12-11-2026):** all three end in a ticket, and they do not
  merge.
  - R03.10: a **person**, on a PM job, raises a ticket for what he found.
  - R03.23: the **meter's rule** raises a condition ticket by itself, when a gauge or Yes / No
    reading crosses a threshold.
  - R03.16: a **target on a ticket that exists**, from any source (a condition ticket too: "pads at
    1.6 mm; replace them within 500 run hours"), on a counter.
  - R03.10 and R03.23 share the ticket-raising function; R03.16 and R03.23 share R03.21's reading
    check (one task per reading, a part each). Each adds its own columns to `tickets`, so they do not
    run in parallel.
- **Migrations:** one (`tickets`: meter type and target value). Per **Q16.1**.

### R03.17 — Reference photos on template items

- **Goal:** TPM's visual standard on every item.
- **What it builds:** a reference photo on a **template** item, shown on the job item. (Simpler than
  approved: there are no plan items any more, so one owner, not two.)
- **Migrations:** one (an owner in `equipment_documents`).

### R03.18 — One path: templates hold the work, a machine's plans are rows (→ S104, 02-11-2026)

- **Goal:** the work is written once, on a template in *Masters › PM templates*; a machine gets a
  PM plan only by a template linked to it. This item builds the template, the plan rows, the links
  table and the link to **one machine**; R03.19 adds class, type and model.
- **After it:** an engineer writes *Press — monthly hydraulic check* once, attaches it to the pilot
  presses one by one, sets each press's assignee and *Last done*, and every S097–S102 flow works as
  today. The pilot can start on the presses (Q0.2).
- **The migration (Q18.1, recommended (a)):** one migration **v57** replaces v51–v56, numbered above
  every version a dev or test database holds, as S087 replaced v42–v47 with v50. It holds PM's
  whole shape:
  - `pm_templates` (new): name (unique), performer, `needs_verification`, `trigger_kind`
    (`calendar`, `meter`, `both`, `before_use`), `calendar_every`, `calendar_unit`, `meter_type_id`,
    `meter_every`, `active`, who and when. S096's CHECKs move with the columns.
  - `pm_template_items`: S096's `pm_plan_items` with `template_id`. **Changed (Q18.3):** a
    *Reading* item has a reading kind, `measurement` (its unit and limits on the item; the value
    stays on the job) or `meter` (a meter **type**; no unit, limits or meter node of its own: the
    meter's unit and limits in force are shown). A CHECK keeps the columns of each kind apart.
  - `pm_template_links` (new): one row per template and target; the target kind `class`, `type`,
    `model` or `equipment` with exactly one target column set (a CHECK); a removed link is set
    inactive with who and when, never deleted. All four kinds exist from v57, so R03.19 needs no
    migration.
  - `pm_plans` reshaped: `equipment_id`, `template_id` (unique together: a template that reaches a
    machine twice is one plan), `assignee_id`, `last_done_on`, `last_done_meter`, `linked` (kept by the sync), *Not for this machine*
    (flag, reason, who, when), who and when. Title, items, trigger and flags leave it.
  - `pm_jobs`, `pm_job_events`: v52–v56's final shape, unchanged.
  - `pm_job_results`: v53's, with `template_item_id` in place of `plan_item_id`, the reading kind
    copied at *Start*, and no `meter_equipment_id` (the meter is the job's node's).
  - `pm_plans` has no meter column at all (second re-plan): the meter is found when needed.
  - On dev and test databases at v51–v56, v57 first drops the six PM tables (they hold test rows
    only), then creates the final shape. Production (v50) holds none: the drops are no-ops. The old
    texts are frozen in `backend/tests/fixtures/migrations_v56.py`; the `v51`–`v56` rows of a dev
    database stay as history. No precondition: no production row exists.
- **Templates:** *Masters › PM templates* (a new Masters section; mock-up 09): the list (name,
  trigger in words, item count, machines reached) and the template page, built from S096's editor
  parts (`PmItemDialog.vue`, the trigger card, the item table, *Move up* / *Move down*). A template
  is never deleted: *Deactivate* stops all its plans. The page says that a change reaches every
  machine at its next job, and a started job keeps its items (KLA, 2a). Key per **Q18.4**.
- **A template change reaches the plans:** after the template's commit, each plan of the template
  is settled in its own transaction (plan (6e) first, then the node shared), as the daily run does.
  So a new interval moves every open, not started job at once. A change of the schedule clears the
  moves of S101. A request that ends half-way is caught by the next morning's run.
- **The machine's plans (mock-up 11):** the equipment page's PM card lists the node's plans and its
  parts' plans, each with its template's name, its **source** ("This machine" in R03.18; class,
  type, model in R03.19), the trigger in words and the open job or next due. *Attach PM template*
  (`pm_plan:edit` at the node's site) picks a template and makes the machine link and the plan row.
  The plan page (the S096 route, `/equipment/pm/<id>`) shows the template's work read-only with
  *Open template*, and the machine's settings: *Assign jobs to*, *Last done*, the meters the
  template uses on this machine (read-only: "Uses HP003's Run hours"; or "Does not apply: no Run
  hours meter on HP003"), and *Remove from this machine* for a machine link (Q19.1 decides what removal
  does; R03.18 builds the recommended answer).
- **The meters (Q18.3, KLA 02-11-2026; replaces the first re-plan's "node or a node above it"):**
  - **Two reading kinds.** A *Measurement* (vibration, main pressure, hook wear) has its own unit
    and limits; its value stays on the job. A *Meter reading* names a meter type; its value is
    saved as an ordinary meter reading (source `pm`) through `write_reading`, as S098 does.
  - **Matched by type on the machine's own meters.** The meter is the job's node's meter of that
    type among its effective meters: the model's meters plus the node's own
    (`meters_core.effective_meters`, `meters.meter_in_force`). The nodes above are never searched,
    unless the template's author ticks it for that meter (Q18.5, answered 02-11-2026).
    One meter per type per node (`uq_model_meters`, `uq_node_meters`), so the match is one meter or
    none: nothing to pick, nothing stored, found when it is needed (the run, the card, *Start*).
  - **This drops S096's search of the nodes above** (`pm_plans.meter_choices`, the ancestor branch
    of `meter_choice_error`) and the engineer's pick when two qualify. A departure from Plan § 4.3
    *Which meter a plan uses* and Maintenance-Philosophy § 8 (the gearbox on the extruder's hours);
    Q18.5's answer keeps a parent's meter only by the explicit tick.
  - **A template applies to a machine only when every meter type it needs is there:** the meter
    trigger's type and each *Meter reading* item's type. With one
    missing, the plan row is kept (it is linked), but it **does not apply**: it makes no job, its
    open, not started job is cancelled with a timeline line ("Does not apply: no Brake air gap
    meter on EOT03"), and R03.20 lists it with the reason. Judged live from the meters in force, so
    adding the meter makes it apply at the next settle (the daily run, a template save, R03.21's
    reading check). A started job keeps its copy (S098 D9: a meter gone since *Start* keeps the
    value on the job only).
  - **A *Meter reading* item has no limits and no rules of its own** (S104 D6; KLA 2b, 12-11-2026):
    it shows the meter's own limits in force (*High* / *Low*). The meter's rules are the meter's
    (R03.23), never the template's, so one meter has one configuration.
  - The applicability rule is pure: `applies(needed_meter_type_ids, meters_in_force)` → applies, or
    the missing types (name for the brief), with its tests first.
- **One function keeps plan rows in step:** `sync_node` (name for the brief), with a pure core
  (`pm_links_core`: which templates reach a node, from its class, type, model and its own id, and
  what to do with each plan row: make, relink, unlink). In R03.18 it is called by *Attach* and
  *Remove*; R03.19 adds its other callers. Each plan in its own transaction: the plan (6e) first,
  then the node shared; a new plan: the node shared, the insert, `uq` as the guard. A new plan row
  has no assignee (KLA, 4a) and no *Last done*, so its first job counts from the day it is made
  (S095).
- **What the held steps change:** `pm_jobs.py`, `pm_work.py` and `pm_jobs_core.py` read the plan
  with its template through one SELECT; `LOCK_PLAN` stays. `pm_work.py`'s *Start* reads the
  template's items. The list and the job page show the template's name. Recommended to the brief:
  *Start* also copies the template's name onto the job, so a renamed template does not rename an old
  record (ISO 9001 § 7.5.3).
- **Tests and screens that change:**
  - Backend, rewritten: `test_pm_plans_api.py` and `test_pm_plans_core.py` (split into the
    template's tests and the plan row's tests); `test_migration_v51.py`–`test_migration_v56.py`
    become one `test_migration_v57.py` (a fresh database; a dev database at v56 with rows).
  - Backend, new: the template API, `pm_links_core` (pure, first), the applicability rule (pure),
    the attach and remove routes; `test_pm_work_api.py` gains the two reading kinds.
  - Backend, set-up only (one shared helper makes a template, links it to a node and returns the
    plan): `test_pm_generate.py`, `test_pm_jobs_api.py`, `test_pm_work_api.py`,
    `test_pm_verify_api.py`, `test_pm_reschedule_api.py`, `test_pm_alerts.py`; `conftest.py`
    `_TABLES`; the role matrix if Q18.4 (b) adds a key.
  - Unchanged: `test_pm_schedule_core.py`, `test_pm_jobs_core.py`, `test_pm_work_core.py` (pure;
    field names only, if any).
  - Frontend: new `PmTemplatesPanel.vue` and the template page; `PmPlanView.vue` becomes the
    machine's plan page; `PmItemDialog.vue` moves to the template; `PmPlansCard.vue` (sources,
    *Attach PM template*); `MastersView.vue` (the section); the router; `pmLabels.js` (source
    words). `PmJobView.vue`, `PmJobsView.vue`: the name only.
  - Browser: `pm-plans.spec.js` rewritten (templates, attach, the plan page); a new
    `pm-templates.spec.js`; set-up only, through one helper in `e2e/support/`, in `pm-jobs`,
    `pm-job`, `pm-verify`, `pm-reschedule`, `me` and `screens` specs. A new file in `e2e/support/`
    is shared code (settings: *Shared code*): the whole browser suite runs again, and
    `screens.spec.js` on `phone-webkit` once.
  - Docs: `docs/schema/` (`notes.json`: the planned `pm_templates`, `pm_template_items` move in;
    `pm_template_links` is new; `pm_plan_items` goes), CLAUDE.md § SMTW-Review's PM bullets (S096's
    becomes the template's and the plan row's; S098's names the template's items), Plan.MD § 4.3.
- **Standards:** TPM planned maintenance (the standard, written once); EN 13306 (maintenance plan);
  ISO 9001 § 7.5.3 (the job's copy; plan rows never deleted); ISO 55001 § 8.2 (a controlled change).
- **Size:** L, about 2 step-days; about 35 files, of which about 12 change a set-up line only. The
  second re-plan adds the reading kinds and the applicability rule and removes the meter picker:
  about the same size. The third re-plan changes nothing in it (S104's D6 already matches).
  **Split point** if the brief passes that: the template page with its items (R03.18a: the tables
  and *Masters › PM templates*, with the old plans still in place) before the plan rows and the job
  reads (R03.18b). The split costs a second pass over `pm_plans.py`, so one step is recommended.
- **Leaves for later:** the links by class, type and model (R03.19), the two lists (R03.20), a
  template's own change history (who changed which item when; today only *updated by*), a copy of a
  template ("Save as new template").

### R03.19 — Links by class, type and model, kept in step

- **Goal:** a template linked to a class, a type or a model reaches every node of it, at any level
  and any site (Q19.3), and keeps reaching the right nodes as the equipment changes (KLA, 1a).
- **After it:** *Press — monthly hydraulic check* linked once to the class *Hydraulic press* gives
  14 presses their plan; the 15th press gets it the day it is added; HP009, out of use, is set
  *Not for this machine*.
- **What it builds:**
  - The template page's **Links** card (mock-up 10): *Add link* to a class, a type (Q18.2), a model
    or one machine; *Remove link*; each link with the count it reaches. Below it, every machine the
    template reaches, with its source, assignee, next job, and a flag for *No assignee*, *Cannot
    run* and *Not for this machine*.
  - **Not for this machine** on the machine's plan page (`pm_plan:edit` at the node's site): a
    required reason ("Out of use until the cylinder is rebuilt"); the plan stops, its open, not
    started job is cancelled with a timeline line; *Use for this machine* undoes it. The card shows
    these plans behind *Not for this machine (n)*.
  - **A second source meets *Not for this machine* (Q19.2 (a), KLA 02-11-2026):** the opt-out
    wins. It sits on the machine's one plan for the template (KLA, 1a), so it holds whatever link
    reaches the machine: a class, type or model link added later leaves the plan stopped. A direct
    link of that template to that machine is refused with the reason: "Not for this machine since
    02-11-2026: Auto-lube unit fitted. Use it again with *Use for this machine*." Only *Use for this
    machine* undoes it. The sync (`sync_node`) never clears the flag.
  - **`sync_node` called from every place that changes what reaches a node:**
    1. a link added or removed (the template page, *Attach*, *Remove*): after the link's commit, for
       each node the link reaches;
    2. equipment writes that change a node's class, type or model, and the create of a node (with
       its parts): after their commit, so `equipment.py` keeps its rule that a node writer never
       waits on a plan row (its LOCK ORDER note);
    3. a template's *Activate* / *Deactivate*: after its commit, for its plans;
    4. **the daily `pm_generate`, as the safety net:** first the sync over every node a link
       reaches and every node with a plan row, then the settle of each plan. A request that ended
       between its commit and its sync is put right by the next morning.
    A move changes no class, type or model; with the meter found when needed (R03.18), it needs no
    sync. **Second re-plan:** a meter added or removed on a node or on its model changes only
    whether a template applies, which is judged live (R03.18); so it needs no sync either. A model
    change changes both the reach (a model link) and the meters; the sync handles the first, the
    next settle the second. A scrapped node gets no new plan; its plans are cancelled as S097 does.
  - **A link removed, or a class, type or model changed so a template no longer reaches a node:**
    per **Q19.1**.
- **Tests and screens:** `pm_links_core` tests (the reach by class at any level, type, model; one
  plan for two sources; relink; unlink); API tests of the links and of each caller of the sync
  (`test_equipment_api.py`: a class change and a new node make or unlink plans); the daily run's
  sync (`test_pm_generate.py`); a browser test of the Links card and *Not for this machine*.
- **Standards:** ISO 14224 taxonomy (class, type, at any level); EN 13460 (the maker's schedule by
  model); TPM (one standard for every machine of a kind).
- **Migrations:** none (v57 has the four link kinds).
- **Size:** M–L, about 1.5 step-days.
- **Leaves for later:** spreading the first due dates, so 14 new plans do not fall due on one
  morning (today the engineer types a different *Last done* per press, or links machine by machine
  for the pilot); a link that names one site (Q19.3 (b)).

### R03.20 — The engineer's lists: no assignee, does not apply

- **Goal:** what the one path leaves undone shows on one screen, so no plan is forgotten (KLA, 1a
  and 4a).
- **What it builds:** a *Plans* tab on the PM list, for holders of `pm_plan:edit` at the units shown
  (mock-up 12), with filters *All plans*, *No assignee (n)*, *Does not apply (n)* and *Not for this
  machine (n)*, by unit:
  - **PM plans without an assignee:** maintenance plans in force with no assignee (operator
    templates have none by design). Per **Q20.1** (a): tick plans and *Assign jobs to* one person; a
    person not assignable at a plan's site is refused for that plan with its reason.
  - **PM plans that do not apply** (**changed**, Q18.3): the machine has no meter of a type the
    template needs. Each row names the missing meter type and what to do: "No Brake air gap meter
    on EOT03. Add it on the machine's *Meters* card, or to its model, or set the plan *Not for this
    machine*." The first re-plan's other two cases go: "two meters qualify, pick one" (the match is
    now one or none) and "runs by calendar only" (a missing meter now stops the template, per
    Q18.5).
  - The tab shows a count badge when either list is not empty.
- **Tests and screens:** API tests of the two lists and the many-plan assignment (at the site;
  refused people); the applicability rule's tests are R03.18's; a browser test of the tab.
- **Standards:** ISO 9001 § 7.1.3 (no machine silently without maintenance); SMRP (a plan that does
  not apply would otherwise be invisible to PM compliance).
- **Migrations:** none. **Size:** S–M, about 0.6 step-days (the meter picker's case is gone).
- **Leaves for later:** "machines with no PM plan" (§ Out, as before); an alert for the lists.

### R03.21 — Act on a reading at once (changed 12-11-2026)

- **Goal:** every saved reading of a meter is checked at once, after its commit. The PM plans that
  use that meter as their trigger settle, so a job comes due when the reading passes its point, not
  at 05:00 the next day. The same check is the hook for the meter's rules (R03.23) and a ticket's
  meter target (R03.16).
- **After it:** a supervisor saves HP003's Run hours as 2,091 h on the Readings sheet at 18:00. The
  job *Press — monthly hydraulic check*, due at 2,090 h, is on the *Due* list a few seconds later,
  not the next morning.
- **What it builds:**
  - **The hook:** `meters.write_reading`, the one insert of `meter_readings` (the readings route,
    the sheet row by row, a PM item; an IIoT feed later), queues one task `reading_check`
    (equipment id, meter type id; name for the brief; the second re-plan's `pm_reading_check`,
    renamed because it now serves tickets too) with `task_queue.enqueue` in the reading's own
    transaction. A refused or rolled-back reading queues nothing. `remove_reading_row` queues the
    same task.
  - **The task** (worker), in parts, each in its own transaction so a failure in one does not undo
    another:
    1. **PM plans (this item):** each plan in force whose template's meter trigger uses this meter:
       the plans of the reading's node, and the plans of the parts that link this meter (S104 A1,
       13-11-2026: `node_meter_links`, `ix_node_meter_links_source`; the link in use). The
       daily run's `_settle_one`, one plan per transaction: the plan (6e) first, then the node (1)
       shared. The settle is idempotent, so a repeated task or a burst of readings changes nothing
       twice.
    2. **The meter's rules (R03.23)** and 3. **ticket targets (R03.16)**: added by those items.
  - **The daily run stays** as the safety net: calendar triggers, a stopped worker, a failed task, a
    meter added, a model change.
- **Departure:** Q3.2 (a) of 27-10-2026 ("meter-triggered jobs appear in the daily run") becomes
  "at the reading, and in the daily run". It follows from KLA's 02-11-2026 answer.
- **Design risks the brief must settle (not decided here):**
  - **Lock order.** The reading path takes the node (1) FOR UPDATE first (`meters.lock_node`,
    meters.py's LOCK ORDER note). Every PM write takes the plan (6e), then the job (6f), then the
    node (pm_jobs.py, pm_work.py). Settling a plan inside the reading's transaction would take (1)
    and then (6e): the reverse order. A PM item save (6e → 6f → 1) and a sheet save on the same
    machine could then deadlock. The task after the commit keeps the PM order, as alerts do (S021).
    The other way is a settle after the commit in the same request (as R03.18's template save
    does); it is quicker but makes a sheet of 48 rows settle 48 times inside the request, and a
    request that ends between leaves the job to the daily run.
  - **The snapshot.** The task's first plain read comes after (6e) and (1), so it sees the
    reading that queued it (REPEATABLE READ: pm_jobs.py's note).
  - **Linked parts.** A reading on a machine's meter may settle plans on the parts that link that
    meter (S104 A1, 13-11-2026; replaces the parent tick). The task finds them through
    `node_meter_links` by source and type, and keeps only the links in use.
  - **Back-dated and removed readings** (S039: up to 7 days back; removed, never edited). The
    settle uses the newest reading and the usage since the base (`readings_across_reset`), as
    today, so a back-dated reading counts only through those. A removed reading never cancels a
    job already made (S097's `decide` refreshes a due job, it does not undo it); the brief checks
    that the refresh does not move the due point back below a job a person has seen.
  - **The PM item's own reading.** It is written under (6e) and (6f); its task runs after that
    commit and finds the job `in_progress`, so the settle does nothing (`decide` returns None).
  - **The alert.** S102 sends *PM job due* the morning the job turns *Due*: kept for meter jobs
    (quiet, in the morning). The second re-plan's "send at once for condition jobs" goes: there are
    none (R03.22 dropped). A condition ticket alerts as any new defect (S021).
- **Tests:** the task is queued in the reading's transaction (a rolled-back reading queues none);
  only the plans that use the meter are settled; a part's plan through the parent tick; a sheet save
  of 10 rows makes one job; a removal; the daily run unchanged.
- **Standards:** ISO 17359 (each value compared with its limit when it is taken); SMRP PM compliance
  (a job that comes due when its point is reached is judged against the right due point).
- **Migrations:** none (`task_queue` takes any task type). **Size:** M, about 1 step-day.
- **Leaves for later:** collapsing repeated tasks for one meter; the IIoT feed itself.

### R03.22 — Condition rules make a PM job (dropped, 12-11-2026)

- **Why:** KLA's 2b (12-11-2026): a crossing never makes a PM job from a template, and the meter
  holds no corrective steps. The rule moves from the template to the meter, and its action is a
  condition ticket, on which the engineer decides the work.
- **Where its parts went:**
  - the rule (meter, above / below, threshold; Yes / No: not the expected answer) → R03.23, on the
    meter;
  - the check on every saved reading → R03.21's task, part 2 (R03.23);
  - "judge the newest active reading by time taken" and "a reading taken before the last fix makes
    nothing" → R03.23 and Q22.1;
  - one open job per plan as the repeat guard → one open condition ticket per meter (Q22.1);
  - the second re-plan's recommendations kept: a counter has no threshold rule (it has *every N* on
    a template); an amount per period gets no rule yet.
- **What goes with it:** *Do within N days* (Q22.2 falls away: a ticket has its own plan, S019's
  *Defer* with a planned date); `pm_schedule_core.KINDS` gains no `condition`; the job's "made by a
  reading" column; *PM job due* sent at once; R03.14's count of condition jobs; the template page's
  card *Other templates on Brake air gap*; the list of plans where a rule is not checked (*Not for
  this machine*, does not apply, not linked, inactive template, scrapped machine), because a
  meter's rule depends on no template. Mock-up 13 is superseded and left out of the deck.
- **Leaves for later:** a rule that makes a PM job from a named template, if the plant asks for it
  once condition tickets are in use (not planned).

### R03.23 — Meter rules raise a condition ticket (changed 12-11-2026)

- **Goal:** condition-based maintenance (EN 13306) with the rule on the meter (KLA, 2b). A meter
  carries **rules**: *above* or *below* a threshold for a gauge, *not the expected answer* for a
  Yes / No meter; several per meter. Every saved reading of that meter, from any source (the
  Readings sheet, the equipment page, a PM job's *Meter reading* item, an IIoT feed later), is
  checked through R03.21's task. A crossing raises a **condition ticket**: a defect ticket on the
  machine, detected by *condition monitoring*, handled like any ticket (acknowledge, assign, start,
  *Fixed*, close; *Defer* with S019). The meter holds no corrective steps; the engineer decides the
  work on the ticket. A rule never makes a PM job.
- **After it:** Engineer A opens the crane model's *Brake air gap* meter in Masters › Models and adds
  a rule: above 1.5 mm. Every crane of the model has it. EOT02 has older pads, so on its *Meters*
  card Engineer A sets its own rules: above 1.5 mm, and above 2.0 mm with the note *Pads near the
  end* (mock-up 16). Supervisor A saves 1.6 mm for EOT02 on the Readings sheet at 17:50. A few
  seconds later ticket TK-2026-11-031 is on EOT02: *Defect · initial*, *Condition monitoring*,
  "Brake air gap 1.6 mm at 05-11-2026 17:50 is above 1.5 mm" (mock-up 17). The new-defect alert
  goes out as for any defect (S021). Two days later a reading of 2.1 mm crosses the second rule; it
  adds a line to the same open ticket (Q22.1 (a)). Engineer A assigns it; Technician A adjusts the
  brake, logs 0.8 mm and taps *Fixed*; Engineer A closes it.
- **What it builds:**
  - **The rules, on the meter** (where: **Q23.1**; recommended (a)): a model meter's rules reach
    every machine of the model, as S038's limits do (the maker's wear limits per model, EN 13460).
    A machine may set its own rules for a model meter; they replace the model's rules on that
    machine, and *Use the model's rules* clears them. An empty set of its own means "no rules on
    this machine" (a crane out of use). A machine's own meter (*This machine only*) has its own
    rules. Edited with `equipment:edit` (the key that edits meters and limits today) in
    Masters › Models › *Meters* (*Set rules*) and on the equipment page's *Meters* card (*Set
    rules*, at the node's site). A machine's change writes a line in its history, as S038's limits
    do.
  - **A rule** has a direction, a threshold (a gauge; at most the type's decimals) and an optional
    note of up to 100 characters ("Pads near the end"), copied into the ticket's text. Nothing more:
    no items, no steps, no *Do within*, no intensity. Kinds: gauge and Yes / No. A counter has no
    threshold rule; an amount per period gets no rule yet.
  - **The check**, pure (in `meters_core` or a new `meter_rules_core`; the brief chooses): from the
    rules in force on the meter, the newest active reading of the meter by time taken, and the open
    condition ticket → the rules crossed, and whether to raise a ticket or add a line. Its tests come
    first. A back-dated reading that is not the newest raises nothing.
  - **The ticket:** the worker (R03.21's task, part 2) raises it through the ticket-raising function
    shared with R03.10, on the machine of the reading's node (with the node as the ticket's part when
    the meter is on a component-unit or component, Plan § 4.2); intensity *initial*; source
    `condition`; the ticket names the rule and the reading. Its *Found by* is the person who logged
    the reading; *Raised by* reads "Meter rule". A reading with no person (an IIoT feed, later) needs
    a system reporter.
  - **One open condition ticket per meter (Q22.1):** a crossing while it is open (any state but
    *closed*) adds a timeline line to it, as Plan § 4.2's shared ticket API rule says; after it is
    closed, the next crossing reading taken after the close raises a new ticket.
  - **Not a breakdown:** raised *initial*, so it is out of every breakdown count, which all go by
    intensity (`is_breakdown`: improvements, contract calls, the down state, the alerts; MTBF in
    phase 5). A re-grade to *critical* (the crane stopped before the fix): **Q23.2**.
  - **On the screens:** the ticket page shows "Raised by a meter rule" with the reading and the rule
    (mock-up 17), and a *Condition monitoring* badge; the ticket list marks it *Condition*; the
    *Meters* card lists each meter's rules (marked *From the model* or *Set on this machine*) and
    links its open condition ticket (mock-up 16).
  - **A removed reading (Q22.3 (b), KLA 02-11-2026):** nothing changes; the engineer closes the
    ticket *Not a fault* with a remark.
- **Assumptions (stated, not asked; KLA may overturn them):** the meter's Min / Max stay the
  *High* / *Low* flags (S038, S039) beside its rules; they raise nothing. The rules dialog shows
  the limits and warns when a threshold lies inside them. A condition ticket is always raised
  *initial*; a person re-grades it.
- **Design risks the brief must settle:**
  - **Lock order.** The task takes the node (1) FOR UPDATE first, reads the open condition ticket
    after it (the repeat guard), then takes the serial counter (6) and inserts the ticket (7):
    `tickets.py`'s order. It touches no PM row, so it takes no plan lock. Two tasks for one meter
    serialise on the node.
  - **Not in the reading's transaction.** A ticket raised there would hold the node already, in the
    right order, and the user would see it on save. But a failed raise would then refuse the reading,
    and the reading is the record: the task after the commit is recommended.
  - **The snapshot.** The task's first plain read comes after (1), so it sees the reading that
    queued it (REPEATABLE READ).
  - **Which rules judge a reading.** The rules in force when the task runs. A rule added today does
    not look back at yesterday's readings (no back-scan); the next reading is judged.
  - **A model change** on a node changes its rules at once (they follow the model, as its meters
    do); a machine's own rules for a type no longer on the model are left out, as an override is
    (`effective_meters`).
  - **A scrapped machine:** the brief checks that no reading, and so no ticket, reaches one.
  - **The migration touches a production table:** `tickets` holds production rows. Widening
    `tickets.source` and adding columns changes no row; the brief checks whether CLAUDE.md
    § SMTW-Review, *Migrations* asks for a `_PRECONDITIONS` entry.
- **Standards:** EN 13306 condition-based maintenance (the rule is the assessment, the ticket the
  action) and deferred corrective maintenance (a deferred condition ticket); ISO 17359 (limits on
  the measured point; two levels by two rules); ISO 14224 detection method *condition monitoring*,
  impact *incipient* (*initial*); ISO 9001 § 10.2 (a recorded reaction); ISO 55001 § 8.2 (a rule
  change is in the machine's history).
- **Migrations:** one, v59 (v58 is S104 A1's meter links, 13-11-2026): the rules table (`meter_rules`, name for the brief: a rule on a model
  meter, on a machine's set for a model meter, or on a machine's own meter; direction, threshold,
  note, active, who and when; never deleted, set inactive, because a ticket names its rule);
  `tickets.source` gains `condition` (and `pm` if R03.10 is not built yet); the ticket's rule and
  reading; the equipment history's value for a rule change.
- **Size:** L, about 1.75 step-days: one new table, two screens changed (the *Meters* card with its
  rules dialog; Masters › Models › *Meters*), a line on the ticket page and the list, the task's
  part 2, about 22 files. **Split point** if the brief passes 25 files: R03.23a the rules on the
  meter (table, dialogs, shown on the card; no action) before R03.23b the ticket. Rules that do
  nothing are of no use alone, so one step is recommended.
- **Depends on:** R03.21.
- **Leaves for later:** a rule on a trend ("rose 0.3 mm in a month": predictive, a later rung); a rule
  over two meters; a rule's own intensity; an e-mail for a rule's ticket; rules on a meter type for
  every model (Q23.1 (b)).

### R03.24 — A reading logged elsewhere counts

- **Goal:** a meter value is entered once (KLA, 3a). A job's *Meter reading* item is met by a
  reading of that meter logged elsewhere (the Readings sheet, the equipment page, another job)
  since the job came due (Q24.1). The job shows it and needs no new entry; the technician may still
  add one.
- **After it:** Supervisor A logs EOT01's *Brake air gap* 1.2 mm on the Readings sheet at 09:40.
  Technician A starts *EOT crane — check hoist brake air gap* at 11:00; item 1 reads "Already read:
  1.2 mm · Today 09:40 · Readings sheet, Supervisor A" and counts as filled (mock-up 15).
- **What it builds:** at *Start* and when the job page loads, each unfilled *Meter reading* item is
  filled from the newest active reading of its meter in the window (Q24.1): the job's node's meter of
  the type, or the parent's when the template ticks it (Q18.5). `pm_job_results.reading_id` names it
  and `value` keeps a copy, with the reading's source and who logged it shown. *Add a new reading*
  stays (a new reading at the job's time, through `write_reading`). A person still taps *Mark job
  done* (Q24.2 (a)).
- **Checked 12-11-2026: it still holds.** Nothing in it depended on a rule on a template. The
  reading counted on the job was checked by the meter's rules when it was saved (R03.23); counting it
  on the job inserts no reading, so it queues no check and raises nothing again. A new reading added
  on the job is checked like any other.
- **Design risks the brief must settle:**
  - S098 D8 replaces "the job's own reading" (source `pm`) when the technician changes the value.
    A reading logged elsewhere is never removed or replaced by the job: a change adds a new reading.
  - A counted reading removed later: before *Mark job done* the item becomes unfilled again; after
    it, the done job keeps its copy of the value (ISO 9001 § 7.5.3).
  - Locks: the fill is a write of the result row, so it takes (6e) and (6f) as every pm_work write
    does, then reads the readings plainly; it needs no node lock (it inserts no reading).
- **Standards:** ISO 17359 (one measurement, used everywhere it is needed); ISO 9001 § 7.5.3 (the
  job names the reading and who took it).
- **Migrations:** none (v53's `reading_id` and `value` copy; v57 keeps them).
- **Size:** S–M, about 0.75 step-days. **Depends on:** R03.18.
- **Leaves for later:** a reading duty met with no job at all (the rule "read every month" checked
  against the readings, with a job only when a reading is missing).

## Order

**Milestone 1 — a PM job on the phone (R03.1–R03.5, R03.7, R03.9): coded and held.** S095–S099,
S101 and S102 are reviewed and snapshotted; S100 (tests) with them.

**Milestone 1b — one path (R03.18 → R03.19 → R03.20, about 4 step-days).**

1. **R03.18**, with the two reading kinds and the own-meter match (now S104, being coded). It
   reshapes what S096–S102 stand on, so it comes first and alone: it touches every PM module, the
   migration and the PM specs.
2. **R03.19.** The other link kinds and the sync's callers need R03.18's links table and function.
3. **R03.20.** The lists need R03.19's plans to exist in numbers.

**Milestone 1c — readings and conditions (R03.21, R03.23, R03.24, about 3.5 step-days; changed
12-11-2026).**

4. **R03.21 ∥ R03.24.** R03.21 is the hook the meter's rules need; R03.24 is small and needs only
   R03.18's reading kinds.
5. **R03.23**, after R03.21 (its rule check is part 2 of R03.21's task). It may run beside R03.24
   if R03.24 is not done yet.
6. **Then the held steps and the rework are committed and released together** (KLA, 5b; Q0.3 (b):
   after R03.24, with the meter's rules). The orchestrator chooses the commit order; S103 (Help, no
   PM file) sits on top of the snapshot chain and may go first. R03.23's v59 may be squashed into
   v57 before the release, as no production database holds either.

**Why this order:** something usable comes first. After R03.18 the pilot presses run PM with
machine links; R03.19 and R03.20 make it scale. The meter's rules come next, on the same reading
hook, before the rest of the roadmap, because KLA wants a value acted on at once, and R03.16 and
R03.10 build on R03.21 and R03.23.

**Milestone 2 — the full PM job (R03.6, R03.10, R03.11, about 3 step-days).**

7. **R03.6** (it may be coded beside R03.20: see the pairs), then **R03.10**, then **R03.11** (each
   adds a migration and changes the job page). R03.10 after R03.23 adds only `pm` to
   `tickets.source`.

**Milestone 3 — operators, measures, routes (R03.12–R03.17, about 7.5 step-days).**

8. **R03.12**, then **R03.13 ∥ R03.14.**
9. **R03.15.**
10. **R03.16**, then **R03.17** (both add a migration).

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
- **R03.21 ∥ R03.24:** neither adds a migration. R03.21 changes `meters.py`, the task handlers, the
  worker's task list and `pm_jobs.py`'s settle; R03.24 changes `pm_work.py` and the job page. The
  briefs keep `pm_jobs.py` to R03.21.
- **R03.23 ∥ R03.24** (new 12-11-2026): only R03.23 adds a migration. R03.23 changes `meters.py`,
  `meters_core.py`, `tickets.py`, the task handler, the *Meters* card, Masters › Models › *Meters*
  and the ticket page; R03.24 changes `pm_work.py` and the job page. The briefs keep the job page's
  line about a rule's ticket (R03.10) out of both.
- R03.20 ∥ R03.6 (R03.20 adds no migration and changes the PM list; R03.6 changes the job page and
  the documents store; both may touch `pmLabels.js`, so the briefs keep their changes apart or run
  them in order).
- R03.13 ∥ R03.14.

**Not in parallel:** R03.18 with anything in PM; R03.18 → R03.19 → R03.20 build on each other;
R03.21 → R03.23 (the rule check sits in R03.21's task); R03.23 with R03.10 or R03.16 (each adds a
migration and changes `tickets`); R03.10 and R03.11 both add a migration; R03.16 and R03.17 both
add a migration.

**Effort (estimate):** S about half a day, M about one day, L about 1.5–2 days of step time with
reviews. Left to do: about **4 step-days** for the rework (R03.18 being coded), about **3.5** for
readings and conditions (R03.21 1, R03.23 1.75, R03.24 0.75; was 4.25), and about **10.5** for the
rest: **about 18 step-days** in all (was 19). Assumption: the briefs settle no new questions.

## Decisions for the user

Questions are numbered by their item: Q22.1 is the first question of R03.22. Answer as "22.1 a". A
question keeps its number when its item is dropped.

### Questions of 12-11-2026, rules on the meter (answered 13-11-2026, below)

**Q22.1 (shrunk 12-11-2026). When may a meter's rules raise a new ticket?** Waits: R03.23. KLA's
answer (a) of 02-11-2026 ("act again on a reading taken after the work was done that still crosses")
carries over as option (a); the new part is one ticket per meter, now that one meter has several
rules.
- **(a) One open condition ticket per meter. A crossing of any of its rules while that ticket is
  open (any state but *closed*) adds a line to it. After it is closed, the next crossing reading
  taken after the close raises a new ticket — recommended.** The 1.5 mm and 2.0 mm crossings land on
  one ticket, because the brake is one fault. A fix that did not work shows: the reading after
  *Fixed* still crosses, the line lands on the ticket before it is closed, and the engineer sends
  it back. It follows Plan § 4.2: "a system that keeps flagging the same equipment adds to its open
  ticket".
- (b) One open ticket per rule. The 2.0 mm rule raises a second ticket while the 1.5 mm one is
  open. The late level stands out, but one brake has two tickets to work and close.
- (c) As (a), but a new ticket only after a reading on the good side first (the condition must clear,
  then cross again). No ticket from a slowly creeping value, but a fix that did not work raises
  nothing new until a good reading is seen.

**Q23.1. Where do a meter's rules sit?** Waits: R03.23. Meters live on the model (every machine of
the model has them) or on one machine (*This machine only*); a machine may already override a model
meter's limits (S038).
- **(a) Where the meter is defined, as its limits are: a model meter's rules reach every machine of
  the model; a machine may set its own rules for that meter, which replace the model's there; a
  machine's own meter has its own rules — recommended.** The maker's wear limits are set once per
  model (EN 13460), one change reaches every crane of the model, and a crane with other pads gets
  its own set. Two places to look (Masters › Models and the machine's *Meters* card); the card shows
  both, marked *From the model* or *Set on this machine*.
- (b) On the meter type in Masters › Meter types: one set for every machine with that meter type,
  plant-wide; a machine may replace it. One place to look, but a 5 t crane and a 20 t crane share
  one brake threshold unless each is replaced by hand, and a meter type is shared by unlike machines.
- (c) On each machine only. Nothing inherited, simple to read; 14 presses need 14 identical sets,
  typed and kept the same by hand.

**Q23.2. A condition ticket is re-graded *critical* (the machine stopped before the fix). Does it
count as a breakdown from then?** Waits: R03.23 (and the KPI work, phase 5). Under both options, a
condition ticket that stays *initial* or *degraded* counts in no breakdown figure (KLA's rule).
- **(a) Yes, from the re-grade, as any ticket: downtime runs, the breakdown alerts go, and it
  counts in MTBF and the breakdown counts. It keeps its *condition monitoring* source, so the
  detection mix shows that the warning came in time but the work did not — recommended.** The
  figures stay honest: ISO 14224 counts a stop as a failure, whatever found the fault. No new code:
  every count already goes by intensity.
- (b) No, never: every breakdown figure leaves out tickets of source `condition`, whatever their
  intensity. MTBF hides a stop the plant had; every count (improvements, contract calls, the down
  state, the alerts, MTBF later) needs a source filter.

### Answers (KLA, 13-11-2026)

| Question | Answer |
|---|---|
| Q22.1 | (a) One open condition ticket per meter; a crossing of any of its rules while it is open adds a line to it; after the close, the next crossing reading taken after the close raises a new ticket. |
| Q23.1 | (a) A meter's rules sit where the meter is defined, as its limits: a model meter's rules reach every machine of the model; a machine may set its own, which replace the model's there; a machine's own meter has its own. |
| Q23.2 | (a) A condition ticket re-graded *critical* counts as a breakdown from the re-grade, as any ticket; it keeps its *condition monitoring* source. |
| Parent meters | **Replaces Q18.5's per-template tick.** A part takes a meter from a node above it only through an explicit link set on the part's *Meters* card ("use a meter from above": this part uses PR-07's *Run hours*); one meter per type on a node (own, model's or linked); a template asks only for the meter type and finds the node's own or linked meter. Built as an amendment to S104 (A1), before S104's gate B. |

### Answers (KLA, 12-11-2026, in discussion: where a reading's rules live; recorded as decided, not asked again)

| Answer | What KLA decided |
|---|---|
| 18.3 · 2b | **Replaces 18.3 · 2a and 18.3 · 1a.** A *mapped* reading (a *Meter reading* item) has no limits or rules on the template: its rules live **on the meter** only, so one meter has one configuration. A meter's rule (above / below a limit; several per meter) acts on every saved reading of that meter, from any source. A crossing does **not** make a PM job from a template, and the meter holds no corrective steps: it raises a **condition-based maintenance task, handled like a breakdown ticket**; the engineer decides the work on the ticket. Consequences for the re-plan: R03.22 (a condition rule makes a PM job) goes; R03.23 (a ticket) becomes the action, with the rule on the meter, not on a condition template; such a ticket is condition-based, not a breakdown (ISO 14224 detection method *condition monitoring*), so the breakdown KPIs must not count it. **Built into this re-plan (12-11-2026).** |
| 18.3 · 4a | A *one-off* reading (a *Measurement* item) keeps its limits on the template item, and a value outside them only asks for a defect ticket at *Mark job done* (Q10.1; built in R03.10, S098 built the red mark). No follow-up PM job. |

### Answers (KLA, 02-11-2026, gate R of the readings re-plan; their options are in this file's history, git)

| Question | Answer | Since 12-11-2026 |
|---|---|---|
| Q0.3 | (b) Release after R03.24, with the condition rules (not after R03.20, as recommended). | Holds. Milestone 1c is now R03.21, R03.23, R03.24; R03.23's v58 may be squashed into v57 before the release. |
| Q18.5 | (a) with an explicit opt-in: own meters only, for every meter a template needs (the trigger too); a missing type makes the template not apply. Per meter, the template's author may tick *If the machine has no meter of this type, use the meter from a parent node* (the nearest node above with the type); never implicit. The tick is per meter, on any meter a template names. | Holds. A template now names meters only in its trigger and its *Meter reading* items: condition rules are no longer on templates. |
| Q22.1 | (a) Act again on a reading taken after the work was done that still crosses. | Re-asked in shrunk form above (one ticket per meter); (a) carries over as option (a). |
| Q22.2 | (a) *Do within N days* on the template; condition jobs counted apart. | Falls away: there is no condition job and no *Do within*. A condition ticket's plan is S019's *Defer* with a planned date. |
| Q22.3 | (b) A removed reading changes nothing: what it made stays; the engineer can still skip it (not the recommendation). | Holds for the ticket: it stays; the engineer closes it *Not a fault* with a remark. |
| Q24.1 | (a) A reading taken since the job was made counts. | Holds. |
| Q24.2 | (a) A person still taps *Mark job done*. | Holds. |
| R03.22's skip cases | Kept: no rule checked on a plan *Not for this machine*, not applying, not linked, of an inactive template or a scrapped machine. | Fall away: a meter's rule depends on no template. A crane out of use gets an empty set of its own (Q23.1 (a)). |

**Q19.2 — answered (a) by KLA, 02-11-2026.** *Not for this machine* wins: it sits on the machine's
one plan for the template, whatever link reaches it, and a direct link of that template to the
machine is refused with the reason. Built into R03.19. (Option (b), a direct link clears the
opt-out, was not chosen.)

### Answers (KLA, 02-11-2026, in discussion: Q18.3; recorded as decided, not asked again)

| Answer | What KLA decided |
|---|---|
| 18.3 | **Two reading kinds** on a template item: *Measurement* (unit and limits, the value stays on the job) and *Meter reading* (a meter type, matched by type among the machine's own effective meters: the model's meters plus its own, never the nodes above: one or none). The value entered on the job is saved as an ordinary meter reading. **No meter of the type: the template does not apply** to that machine, which is listed with the reason. ~~**Condition rules** (condition-based maintenance): a template may carry a condition trigger on a meter type (above / below a limit, or every N of a counter), checked on every saved reading of that meter from any source, not only in the daily run.~~ **Changed by 2b (12-11-2026):** the rules are on the meter; the check on every saved reading stays. |
| 18.3 · 1a | ~~A condition template chooses what a crossing makes: a PM job or a ticket.~~ **Replaced by 2b (12-11-2026):** a crossing raises a condition ticket. |
| 18.3 · 2a | ~~The limits live on the condition template; one meter type may carry several rules (adjust at 1.5 mm, replace at 2.0 mm).~~ **Replaced by 2b (12-11-2026):** the rules live on the meter, several per meter. The meter's own Min / Max (S038) stay the *High* / *Low* display flags (an assumption of this re-plan, R03.23). |
| 18.3 · 3a | A reading duty is met by a reading of that meter logged elsewhere after the job came due: the job shows it, no new entry is needed, and one may be added. |

**Answers (KLA, 02-11-2026, gate R of the one-path re-plan):** Q18.1 (a) one migration v57 replaces
v51–v56; Q18.2 (a) a template may also link to a type; Q18.4 (a) templates are site-less masters,
written by `pm_plan:edit` held at any site; a machine's plan needs the key at the machine's site;
Q19.1 (a) a plan no longer reached is kept but stops, and comes back with its history; Q19.3 (a) a
class, type or model link reaches every site; Q20.1 (a) assign many plans at once. Their options
are in this file's history (git).

**Answers (KLA, 02-11-2026, the one-path decision; not asked again):**

| Answer | What KLA decided |
|---|---|
| 1a | One path: a PM template is the only place work is written (items, trigger: a calendar interval and / or an interval of a meter type, photo settings, verification flag). A template links to a class (every machine of it, at any level), a model (the maker's schedule) or one machine (a one-off, or a component-unit with no model). A machine's PM plans are the templates it inherits or has attached, each shown with its source; the same template reaching a machine twice is one plan. Per machine stays a plan row: assignee, active / *Not for this machine*, and all schedule state. (Its meter: replaced by 18.3, own meters only.) |
| 2a | A template change reaches every machine at its next job (a live link); a started job keeps its copied items. **Replaces Q8.1 (a).** |
| 3a | A machine that needs different work opts out of the inherited template and gets its own template linked to it; no per-machine item edits. |
| 4a | A machine that newly inherits a template gets an empty assignee; the engineer gets *PM plans without an assignee*. |
| 5b | Nothing is adopted (committed, released) until the rework is done. |

**Answers (KLA, 27-10-2026, in the session; all at the recommendation):**

| Question | Answer | Note |
|---|---|---|
| Q0.1 | a | Certification, calibration, fitness-for-use and fire extinguishers: a follow-on roadmap (R04), started after R03.8 (now: after R03.20). |
| Q0.2 | a | The hydraulic presses pilot PM. |
| Q1.1 | a | On time = done within 10 % of the interval, at least 1 day. |
| Q1.2 | a | A meter plan's next job counts from the reading when last done, plus N. |
| Q2.1 | a | Plan § 4.3's item shape: Task / Check / Reading, a photo setting per item, no signature. |
| Q2.2 | a | IT admin reads PM only. |
| Q3.1 | a | One open job per plan, shown as *Upcoming* a little before it is due. |
| Q3.2 | a | Meter-triggered jobs appear in the daily run. (**Changed by 18.3:** also at once on the reading, R03.21.) |
| Q3.3 | a | A job nobody does stays overdue until done or skipped. |
| Q5.1 | a | Verification is a flag per plan: default yes for maintenance, no for CIL. (Now a flag per template.) |
| Q5.2 | a | An engineer may verify a job they did; it is recorded. |
| Q7.1 | a | The overdue alert goes to the assignee and the unit's engineers (departs from Plan: Telegram is parked). |
| Q8.1 | a | ~~Plans keep a copy of the template; *Update plans*.~~ **Replaced by 2a (02-11-2026): a live link.** |
| Q9.1 | a | A rescheduled job is on time against the new date; reschedules are counted. |
| Q9.2 | a | An engineer may skip a due job with a reason; it counts as not done. |
| Q10.1 | a | At *Mark job done*, each Not OK item without a ticket asks: *Raise defect ticket* or *No ticket* with a remark. (12-11-2026: a *Measurement* out of its limits asks too; a *Meter reading* item never asks, R03.10.) |
| Q11.1 | a | Labour minutes are recorded on PM jobs. |
| Q12.1 | a | CIL is part of R03. |
| Q15.1 | a | The genset round pilots routes (departs from Plan: the fleet inspection). |
| Q16.1 | a | The ticket's target by meter value is built in R03 (R03.16). |

**Not asked again (decided in Plan.MD or by KLA, followed as written):** one plan per node and task
(Maintenance-Philosophy § 7); the next calendar job from the last completion (§ 4.3); a meter
crossing its *every N* point creates the job by itself (§ 4.3); both triggers whichever first
(§ 4.3); job states due → in progress → done → verified, send back by the engineer (§ 4.3); recorded
on behalf (§ 4.3, § 4.4); `PM-YYYY-MM-NNN` (§ 4.3); `pm_job:work` from the operator up, which jobs
by data (§ 3); CIL as a PM plan (§ 4.4); AMC vendors as contractor people performing plans (§ 4.3);
no drawn signature (§ 4.3); a reading out of limits raises a ticket, not a PM job (§ 4.3 *Triggers ›
Meter*, which 2b returns to); breakdown or defect by intensity (§ 4.2); KLA's 1a–5b, 18.3 and 2b
above.

**Departures from Plan.MD (for the orchestrator to record when approved):**
- § 4.3 *PM plan*: "created from a template or by hand" → only from a template (KLA, 1a); a one-off
  is a template linked to one machine. The plan-level "Built (S096)" paragraph changes.
- § 4.3 *PM template*: "Engineers apply a template by picking equipment … then removing exceptions"
  → a live link to a class, type or model, and *Not for this machine* (KLA, 1a, 3a).
- § 9 open question 6 (decided 27-10-2026 as a copy with *Update plans*) → a live link (KLA, 2a).
- **Changed (18.3):** § 4.3 *Which meter a plan uses* ("the picker offers the node's own meters and
  its ancestors'"; the gearbox on the extruder's hours) → the machine's own meters only, matched by
  type, one or none, a parent's only when ticked; a template that needs a missing meter does not
  apply. The same line in Maintenance-Philosophy § 8. The first re-plan's "two qualify: the engineer
  picks" goes.
- **New (18.3):** § 4.3 *Item types › Reading* → two kinds, *Measurement* and *Meter reading*.
- **Changed 12-11-2026 (2b):** § 4.3 *Triggers › Meter*, "A reading that crosses a gauge's limit
  raises a ticket, not a PM job": still a ticket, not a PM job, but the limit that raises it is a
  **rule on the meter** (several per meter), not the gauge's Min / Max. (The second re-plan's "a
  condition template chooses a PM job or a ticket" is withdrawn.)
- **Changed 12-11-2026 (2b):** § 4.5 "gauge (a level; triggers on crossing limits)" and
  Maintenance-Philosophy § 7 (*Condition-based: gauge meters with limits*) and § 8 (*Gauge meters …
  trigger on crossing limits*) → the meter's Min / Max are display flags; what raises a ticket is
  the meter's rules. § 4.5's oil cleanliness line ("Over the limit raises the offline filtration
  job") → raises a condition ticket, on which the engineer plans the filtration. § 4.5's lab results
  ("a value over limit raises a ticket with detection method *condition monitoring*") holds when the
  lab value is a *Meter reading*; as a *Measurement*, *Mark job done* asks instead.
- **Changed 12-11-2026:** § 4.2 *Detection method* (**Proposed**) → built for the source
  `condition` (R03.23) and `pm` (R03.10).
- **New (18.3):** Q3.2 (a) and § 4.3 "meter-triggered jobs in the daily run" → also at once on
  every saved reading (R03.21); the daily run stays as the safety net.
- Plan.MD § 1's PM row still says "condition rules on every saved reading make a PM job or a ticket"
  → "a meter's rules on every saved reading raise a condition ticket" (the § 4.3 block is already
  changed, 12-11-2026).
- A fourth link kind, type (Q18.2 a).
- Earlier departures stand: Q7.1 (a), Q10.1 (a), Q15.1 (a), the key `pm_job:read`.

## Out of the roadmap and risks

**Out (fact):**
- Certification plans, calibration, fitness-for-use and fleet inspections as plan kinds: the
  follow-on of Q0.1 (R04), now after R03.20. They become templates with extra fields.
- Procedures and one-point lessons (Plan § 4.3a): their own roadmap. R05.9 ("a countermeasure
  becomes a PM plan") now means "a countermeasure becomes a template linked to the machine or its
  class": R05's text should say so when it is taken up.
- The maintenance strategy field and a "machines with no PM plan" list (Plan § 4.1): proposed for
  the follow-on; R03.20's lists cover plans that exist, not machines without any.
- A template's change history line by line; versions of a template.
- A rule that makes a PM job (dropped by KLA, 12-11-2026); rules on a trend or over two meters; the
  MTBF and breakdown reports themselves (phase 5).
- Spares, stock, cost, the AMC register; the dashboard, Excel export, the daily summary email;
  shutdown planning; kiosks; IIoT readings; Vaahan's odometer feed; *Status: PM due* on the list.

**Risks:**
- **The reading hook and the lock order (second re-plan).** The reading path holds the node (1)
  first; PM writes hold the plan (6e) and the job (6f) first. A plan settled inside the reading's
  transaction would invert that order and could deadlock with a PM item save on the same machine.
  R03.21 recommends a task after the commit, as alerts do; its brief must check every path.
- **A wrong reading acts at once (changed 12-11).** A typo (16 for 1.6 mm) raises a condition
  ticket within seconds, before anyone sees the reading. Q22.3 (b): removing the reading changes
  nothing; the engineer closes the ticket *Not a fault* with a remark. The counter's order check
  (S039) still refuses a lower counter value, but a gauge has no such check.
- **Repeats (changed 12-11).** A creeping value read every day crosses the threshold every day. One
  open condition ticket per meter (Q22.1 (a)) turns the repeats into lines on that ticket.
- **Two sets of numbers on one meter (new 12-11).** The Min / Max flags and the rules sit side by
  side; an engineer may read one for the other. The card shows both with their words (*Limits*,
  *Rules*), and the rules dialog warns when a threshold lies inside the limits.
- **A model's rule acts on every machine of the model (new 12-11).** With Q23.1 (a), a rule added
  to a model meter judges the next reading of every machine of the model; a machine with other
  parts needs its own set first. Readings taken before the rule raise nothing (no back-scan).
- **The breakdown figures (new 12-11).** Today every breakdown count goes by intensity, so a
  condition ticket raised *initial* is out of them. The phase-5 KPI work must keep that rule, and
  Q23.2 decides a re-grade to *critical*.
- **Silent stops by a missing meter (second re-plan).** With Q18.5 (a), a template that reaches a
  class does not apply to every machine of it that lacks the meter type, and makes no job there.
  R03.20 lists them; the engineer must read the list, or the gap is as silent as before.
- **Parts lose their run-hours work (second re-plan).** Q18.5 (a) drops the implicit search of the
  nodes above: a gearbox or a motor without its own meter gets no run-hours plan unless the
  template ticks the parent's meter. Content work: tick it, or add a meter to the part.
- **A class link acts at once on many machines (new).** Linking *Press — monthly hydraulic check* to
  the class makes 14 plans, with no assignee, all due one month later on the same day. The pilot can
  use machine links first (Q19.3 (a)); *Last done* per press spreads the dates; R03.20 shows the
  missing assignees. An engineer's change to a class template reaches every site's machines
  (Q18.4, Q19.3).
- **The sync runs after a commit (new).** A request that fails between the commit and the sync
  leaves a machine without its new plan until the next morning's run. The daily run is the safety
  net; a stopped worker leaves it undone (the *Background tasks* card shows that). The same holds
  for a reading's check: a stopped worker raises no condition ticket until it runs again.
- **Lock order (new).** A template change settles its plans one transaction each, after its own
  commit, because a template lock held while plan locks are taken would read the jobs from an old
  snapshot (REPEATABLE READ; pm_jobs.py's note). Equipment writes never take a plan lock in their
  transaction (equipment.py's rule); they call the sync after their commit.
- **The rework reopens reviewed code (new).** S096–S102 were reviewed against the plan-with-items
  shape. R03.18 must keep their invariants (CLAUDE.md § SMTW-Review, *PM plans* to *PM alerts*):
  the plan lock (6e) first, one open job per plan, the job's copy at *Start*, the reading path. The
  code reviewer re-checks each.
- **R03.18 is large.** About 35 files; its split point is named in its section.
- **Content, not code, is the bottleneck (Plant-Facts § 6).** Templates and rules must be written
  by the engineers; one template per class or model, and one rule set per model meter, make that
  smaller than one per machine.
- **Meter triggers are only as good as the readings.** A press whose run hours are not entered
  never comes due by meter; both triggers is the safety net; R03.20 lists the plans with no meter.
  A meter's rules judge only the readings someone enters.
- **The reading path is shared (S098).** A PM reading that bypasses `write_reading` breaks the
  counter order rule, and is not checked by the meter's rules.
- **Month arithmetic and IST.** Unchanged: S095's tests fix the edge cases.
- **Phones and photos (R03.6).** The front proxy blocks an in-page camera; the file input is used.
- **Floating schedules drift.** Plan's decision; the compliance window (Q1.1) shows it.

## Slides

The re-plan deck (12-11-2026, rules on the meter). Mock-ups 01, 05 and 13 are superseded and left
out; they keep their file names because S096's brief links 01. Mock-ups 16 (rules on the meter) and
17 (a condition ticket) are new. The deck order is set here, not by the file numbers.

1. **Preventive maintenance in Yantra: one path, readings entered once**
   - The work is written once, on a PM template, linked to a class, type, model or machine.
   - A reading is a *Measurement* or a *Meter reading*; a meter reading is saved on the machine's
     own meter.
   - The meter's rules check every saved reading, at once, and raise a condition ticket.
2. **The standards, in plain words**
   - TPM: the work is a standard, written once for each kind of machine.
   - EN 13306: a reading duty is an inspection; the meter's rule and its ticket are condition-based
     maintenance.
   - ISO 17359: measure at an interval, compare with a limit on the measured point, act; two
     limits, two levels.
   - ISO 14224: a condition ticket is found by *condition monitoring*; it is not a breakdown.
3. **The template: the work, written once** — `09-pm-template.html`
   - The engineer writes items and *every 1 month or 250 h of Run hours*.
   - A change reaches every machine at its next job; a started job keeps its items.
4. **Two kinds of reading, and which machines it fits** — `14-reading-kinds.html`
   - *Measurement*: its own limits, kept on the job. *Meter reading*: saved on the machine's own
     meter of the type, no limits on the template.
   - A crane without a *Brake air gap* meter: the template does not apply, and says why.
5. **Rules on the meter** — `16-meter-rules.html`
   - Engineers set rules on a meter: above 1.5 mm, above 2.0 mm. A model's rules reach every
     machine of the model; a machine may have its own.
   - The rule says when, not what to do: the engineer decides the work on the ticket.
6. **A condition ticket** — `17-condition-ticket.html`
   - A reading of 1.6 mm on the Readings sheet raises a ticket on the crane within seconds.
   - Handled like any ticket; a later crossing adds a line to it; not in the breakdown figures.
7. **A reading logged elsewhere counts** — `15-job-reading-elsewhere.html`
   - The supervisor's sheet reading fills the technician's job item; no second reading.
   - *Add a new reading* stays; a *Measurement* is still typed on the job.
8. **Links: where the template reaches** — `10-template-links.html`
   - Linked to the class *Hydraulic press*: 14 presses at once, and every new press.
   - Each press's state: running, no assignee, does not apply, not for this machine.
9. **A machine's PM plans** — `11-machine-pm-plans.html`
   - HP003: plans from class, model, type and this machine; the meters each one uses.
10. **The engineer's lists** — `12-pm-plans-lists.html`
    - *No assignee*: assign three at once. *Does not apply*: the missing meter, and what to do.
11. **What changed on 12-11-2026, and the timeline**
    - No rule on a template, no PM job from a reading: R03.22 dropped; R03.23 puts the rules on the
      meter and raises a condition ticket.
    - Coded and held: R03.1–R03.5, R03.7, R03.9. One path (about 4 days): R03.18 (being coded) →
      R03.19 → R03.20.
    - Readings and rules (about 3.5 days): R03.21 ∥ R03.24, then R03.23. Release after them.
    - Then about 10.5 days: photos, tickets from items, labour; CIL, compliance, routes, meter
      targets, reference photos.
12. **Your decisions** (recommended answer in brackets)
    - Q22.1 one open condition ticket per meter; a later crossing adds a line (a).
    - Q23.1 rules on the model's meter, a machine may have its own (a).
    - Q23.2 a condition ticket re-graded *critical* is a breakdown from then (a).

## Log

- 27-10-2026 — First version (Draft): 17 items from Plan.MD § 4.3, § 4.4, § 4.2, § 4.6 and § 4.7,
  checked against HEAD `c9142b4`; no PM code or key exists; `meter_readings.source` already allows
  `pm`. Eight mock-ups in `R03-mockups/` (with `mockup.css` for the sidebar and top bar, which live
  in scoped Vue styles). 20 questions for KLA.
- 27-10-2026 — Renumbered R02 → R03 by the orchestrator: a parallel session took R02 for annual maintenance contracts (`R02-amc-contracts.md`). Mock-ups moved to `R03-mockups/`; the follow-on roadmap of Q0.1 is now R04.
- 27-10-2026 — Gate R: KLA answered all 20 questions at the recommendation (Q10.1 after an explanation). Deck: https://claude.ai/artifact/96s6in9nPD3TkhECozuHCv. Lasting decisions recorded in Plan.MD (§ 1 and § 9).
- 02-11-2026 — **Re-plan: one path** (KLA's decision of 02-11-2026, answers 1a–5b). What changed and
  why: KLA chose templates as the only place work is written, linked to a class, a model or one
  machine, with a plan row per machine for its meter, assignee and schedule. So: **R03.18–R03.20
  added** (the rework of the held S096–S102: templates and plan rows with one migration v57 in place
  of the unreleased v51–v56; links by class, type and model kept in step by one sync function with
  the daily run as the safety net; the two lists). **R03.8 dropped, merged** into them. **Q8.1 (a)
  replaced** by 2a (a live link). R03.2–R03.5, R03.7, R03.9 keep their step links, marked held, with
  a note on what the rework changes in each; R03.6, R03.10–R03.12, R03.14 and R03.17 now depend on
  R03.18 or R03.19; R03.14 gains a per-template view; R03.17 needs one owner, not two. The order
  gains milestone 1b, before anything is committed (5b); parallel pairs now R03.20 ∥ R03.6 and
  R03.13 ∥ R03.14. Standards: ISO 14224 taxonomy, EN 13460 and ISO 55001 § 8.2 added; the TPM row
  changed. Eight new questions (Q18.1–Q20.1). Mock-ups: 09–12 added (the template, its links, a
  machine's plans, the engineer's lists); 01 and 05 marked superseded, kept for S096's link. The
  order changed and new decisions came, so the roadmap is back at gate R. Checked against the
  working tree (HEAD `c9cd091` plus the held steps); production is at v50.
  - Feedback for this re-plan: in § Feedback below.
- 02-11-2026, gate R answers (KLA): Q18.1 (a) one v57; Q18.2 (a) a link by type too; Q18.4 (a);
  Q19.1 (a); Q19.3 (a); Q20.1 (a). Q18.3 and Q19.2: KLA asked for more explanation; open. The
  deck: <https://claude.ai/artifact/FPqaLxE5XD4xg7hENCAGop>.
- 02-11-2026, Q18.3 answered by KLA in discussion (replaces options a–c; needs a re-plan):
  - **Two reading kinds on a template item.** (1) *Measurement*: unit and limits, the value stays on
    the job only. (2) *Meter reading*: names a meter type, found by type among the machine's own
    effective meters (model meters plus its own; never the nodes above: one meter per type per node,
    `uq_model_meters`, `uq_node_meters`, so the match is one or none). The value entered on the job
    is saved as an ordinary meter reading.
  - **No meter of the type on the machine:** the template does not apply to that machine (flat
    refusal), and the machine is listed with the reason (R03.20's *cannot run* list).
  - **Condition rules on meters (condition-based maintenance, EN 13306):** a template may have a
    condition trigger (a meter type, `>` / `<`, a threshold; or every N of a counter, e.g. 30,000
    strokes). It is evaluated **on every saved reading of that meter, from any source** (PM job,
    readings sheet, IIoT later), not only in the daily run. A reading-duty template ("Check brake
    pad air gap every 1 month or 300 h") reminds someone to take the reading; the condition template
    acts on it.
  - **1a:** the condition template says what a crossing creates: a PM job or a ticket (Plan § 4.3
    said a ticket; now the template chooses).
  - **2a:** the thresholds live on the condition template, so one meter may carry several rules
    (adjust at 1.5 mm, replace at 2.0 mm); the meter's own Min / Max (S038) stay as the *High* /
    *Low* display flags.
  - **3a:** a reading duty is met by a reading of that meter logged elsewhere after the job came due:
    the job shows it and needs no new entry (the technician may add one).
  - Effect: R03.10 and R03.16 partly merge into this; the meter trigger moves from the daily check to
    every reading save. Q19.2 is still open. Sent to the roadmapper for a re-plan (back to gate R).
- 02-11-2026 — **Re-plan: readings and conditions** (KLA's answer to Q18.3 above). What changed and
  why: KLA wants PM deterministic, and a meter value entered once and acted on at once.
  - **R03.18 changed:** two reading kinds (*Measurement*, *Meter reading*); a meter is matched by
    type on the machine's own effective meters (model plus own), never the nodes above: S096's
    `meter_choices` search and the engineer's pick go; `pm_plans` has no meter column; a template
    that needs a missing meter type does not apply (judged live). Q18.5 asks whether that covers
    the trigger meter too.
  - **R03.19:** a meter change needs no sync (applicability is live). **R03.20:** *Cannot run*
    becomes *Does not apply*; the "pick the meter" and "calendar only" cases go.
  - **New:** R03.21 (every saved reading settles the plans that watch its meter, through a worker
    task after the reading's commit; the daily run stays), R03.22 (condition rules make a PM job;
    v58), R03.23 (or a defect ticket; v59), R03.24 (a reading logged elsewhere meets a job's meter
    reading; no migration).
  - **R03.10 and R03.16 do not merge:** R03.10 narrows to what a person judges on the job (the
    automatic ticket from a reading is R03.23; one shared ticket-raising function); R03.16 stays a
    ticket's own target, now on the machine's own meter and checked on every reading save.
    R03.14 counts condition jobs apart. R03.4's note names the reading kinds.
  - **Order:** milestone 1c (R03.21 ∥ R03.24, then R03.22 → R03.23) after 1b; new pair R03.21 ∥
    R03.24; about 19 step-days in all. **Standards:** EN 13306 row changed (condition-based,
    deferred corrective); ISO 17359 and RCM's P-F interval added (clauses to verify). **Decisions:**
    the 02-11 gate answers moved into the answers tables; Q19.2 kept open; 7 new questions (Q0.3,
    Q18.5, Q22.1–Q22.3, Q24.1, Q24.2); new departures from Plan.MD § 4.3, § 4.5 and
    Maintenance-Philosophy § 7–8, and from Q3.2 (a). **Mock-ups:** 13–15 added (a condition rule,
    the reading kinds and the machine match, a job with a reading logged elsewhere); 09–12 changed
    to the own-meter rule. Back at gate R. Checked against the working tree (HEAD `c9cd091` plus the
    held steps' `meters.py`, `pm_*.py`, `local_db.py` v51–v56); production is at v50.
  - Feedback for this re-plan: in § Feedback below, under its date.
- 02-11-2026, Q19.2 (a) by KLA: *Not for this machine* wins over every link that reaches the
  machine, and a direct link of that template to the machine is refused with the reason; built into
  R03.19. Also noted in R03.22: a plan set *Not for this machine*, or a template that does not apply
  for a missing meter type, has none of its condition rules evaluated on that machine.
- 02-11-2026, gate R answers on the readings re-plan (KLA): **Q0.3 (b)** release after R03.24, with
  condition rules (not after R03.20, as recommended); **Q22.1 (a)**; **Q22.2 (a)**; **Q22.3 (b)** a
  removed reading changes nothing: the job it made stays (not the recommendation; the engineer can
  still skip it with a reason, S101); **Q24.1 (a)**; **Q24.2 (a)**; the three extra skip cases of
  R03.22 (plan no longer linked, inactive template, scrapped machine) kept. **Q18.5 open**: KLA asked
  for a plainer explanation. To carry into § Decisions and § Order (milestone 1c before the release)
  when Q18.5 is answered.
- 02-11-2026, **Q18.5 (a) with an explicit opt-in** (KLA): the default is own meters only, for every
  meter a template needs (the trigger too); a missing meter type makes the template not apply. The
  template's author may tick, per meter, *If the machine has no meter of this type, use the meter
  from a parent node*: then the nearest node above that has the type is used (still one meter or
  none, found walking up). Never implicit. Scope (the trigger only, or every meter the template
  names) asked of KLA.
- 02-11-2026, **approved at gate R** (KLA): the tick is per meter, on any meter a template names
  (trigger, meter reading items, condition rules) (1a); the roadmap is approved as re-planned (2a).
  Lasting decisions recorded in Plan.MD § 4.3 (the "Decided 02-11-2026" block) and its § 1 row.
  Deck: <https://claude.ai/artifact/FPqaLxE5XD4xg7hENCAGop>. Next: R03.18 as a step.
- 12-11-2026, KLA in discussion: answers 18.3 · 2b (a mapped reading's rules live on the meter; a
  crossing raises a condition-based maintenance ticket, handled like a breakdown ticket, out of the
  breakdown KPIs; never a PM job) and 18.3 · 4a (a *Measurement* out of limits only asks for a defect
  ticket). Recorded in § Decisions and in Plan.MD § 4.3's *Condition rules* bullet. Sent to the
  planner for a re-plan of R03.21–R03.23.
- 12-11-2026 — **Re-plan: rules on the meter** (Planner, Opus 5.5; KLA's answers 2b and 4a above).
  What changed and why: KLA moved a mapped reading's rules from the template to the meter, so a meter
  has one configuration, and a crossing raises a ticket on which the engineer decides the work.
  - **R03.22 dropped** (a rule never makes a PM job); its parts listed in its section; mock-up 13
    superseded.
  - **R03.23 rewritten:** *Meter rules raise a condition ticket*: rules on the meter (model meter,
    a machine's own set, a machine's own meter; Q23.1), checked by R03.21's task, one open condition
    ticket per meter (Q22.1), raised *initial* with source `condition`, out of the breakdown counts
    (Q23.2 for a re-grade); size M → L (about 1.75 step-days), migration v58 (was v59), depends on
    R03.21 (was R03.22); split point named.
  - **R03.21 changed:** the task is `reading_check`, in parts (PM plans; the meter's rules, R03.23;
    ticket targets, R03.16); it also settles a part's plan that takes the meter from a parent node
    (Q18.5's tick, which the earlier text missed); "send at once for condition jobs" goes.
  - **R03.24 checked:** it holds; a note added (the parent's meter when ticked; a counted reading
    raises nothing again).
  - **R03.10:** a *Meter reading* item never asks at *Mark job done*; a *Measurement* out of limits
    asks (Q10.1). Fact corrected: S098 built the red mark, not the question. **R03.14:** no condition
    jobs to count apart. **R03.16:** a note on how R03.10, R03.16 and R03.23 meet. **R03.18:** text
    aligned with S104's D6 and Q18.5's answer; no change to the step. **R03.1, R03.4:** a line each.
  - **Order:** milestone 1c is R03.21 ∥ R03.24, then R03.23 (new pair R03.23 ∥ R03.24); release
    after it (Q0.3 (b)); about 3.5 step-days (was 4.25), about 18 in all (was 19).
  - **Standards:** EN 13306, ISO 17359, RCM, ISO 14224 data and SMRP PM compliance rows changed; SMRP
    MTBF added (clause to verify).
  - **Decisions:** the readings gate's answers (Q0.3, Q18.5, Q22.1–Q22.3, Q24.1, Q24.2) moved into
    an answers table with what each means now; Q22.2 falls away; Q22.1 re-asked, shrunk; two new
    questions Q23.1 (where the rules sit) and Q23.2 (a re-grade to *critical*); departures from
    Plan.MD § 1, § 4.2, § 4.3, § 4.5 and Maintenance-Philosophy § 7–8 restated.
  - **Mock-ups:** 16 (rules on the meter, the *Meters* card and the rules dialog) and 17 (a
    condition ticket on the phone) added. **Slides:** 12, re-ordered.
  - Gate R waived by KLA for this re-plan; Q22.1, Q23.1 and Q23.2 are open and wait for R03.23.
    Checked against the working tree (HEAD `c7e9f0b` plus the held steps and S104 in coding).
  - Feedback for this re-plan: in § Feedback below, under its date.

## Feedback

**Re-plan 12-11-2026, rules on the meter:**

- `hindrance` — The planner has no Edit tool, and the spawn prompt forbids edits through a script's
  string literals, so this re-plan of a 1,200-line roadmap rewrote the whole file with Write to
  change about a fifth of it. That costs output and risks dropping a line unseen. Either the Edit
  tool for the planner, or a rule that a re-plan may use `sed` for a one-line change, would make
  re-plans cheaper and safer.
- `rule` — The gate answers of 02-11-2026 on the readings re-plan were again recorded only in
  § Log, while § Decisions still listed the seven questions as new and open, with their
  recommendations (the same gap as the earlier feedback below). A line in the orchestrator's gate R
  step, "move each answered question into an answers table", would keep § Decisions true; this
  re-plan moved them.
- `idea` — An item's text names the items that build on it (R03.21's "the base for R03.22"), so
  dropping one item meant finding every mention by hand (about 25 in this file). A short "Built on
  by" column in the items table would show at once which sections a drop or merge touches.

**Re-plan 02-11-2026, readings and conditions:**

- `hindrance` — The gate answers of 02-11-2026 (Q18.1, Q18.2, Q18.4, Q19.1, Q19.3, Q20.1) were
  recorded only as a Log line, while § Decisions still listed them in full under "New questions";
  this re-plan had to move them into the answers tables before adding questions. A line in the
  orchestrator's gate R step, "move each answered question to the answers table", would keep
  § Decisions current.
- `rule` — The roadmapper's prompt says a re-plan adds its feedback "under its `## Log` entry"; the
  spawn prompt says "end the file's `## Feedback`"; the first re-plan put it in `## Feedback`. This
  file follows the spawn prompt and points to it from the Log. One place in the prompt would settle it.
- `idea` — The roadmap names the lock-order and back-dating risks for R03.21–R03.23 from the LOCK
  ORDER notes of `meters.py`, `pm_jobs.py`, `pm_work.py` and `tickets.py`. A short, current list of
  the lock numbers (1), (6), (6e), (6f), (7) in one place would save each planner reading four
  module docstrings to find the order.

**Re-plan 02-11-2026, one path:**

- `hindrance` — A re-plan cannot renumber mock-ups to the deck's order without breaking the step
  briefs that link them: S096–S099's briefs link `R03-mockups/01-pm-plan.html` to `04-verify.html`
  (e.g. `docs/steps/S096-pm-plans/1-brief.md:43`), and the roadmapper may not edit step files. This
  re-plan numbers its new mock-ups 09–12 and puts the order in `## Slides`. A line in
  `docs/roadmap/README.md` ("a re-plan appends numbers; the slide outline sets the order") would
  make it the rule.
- `rule` — `docs/roadmap/README.md` and the roadmapper's prompt name four item states (`open`,
  `→ S0NN`, `done`, `dropped`) but no state for an item merged into others or for a coded step held
  back; this file writes "dropped — merged into R03.18–R03.20" and "→ S096, … (held)". Two states,
  `merged into R0N.n` and `held`, would let `tooling/roadmap/` read them.
- `hindrance` — The step rule's "about 25 files" counts a test file whose set-up line changes the
  same as new code. A rework of coded steps (R03.18: about 35 files, about 12 of them a set-up line)
  then looks larger than its review is. Evidence: six backend test files and seven
  specs make plans through `/api/pm/plans` only for their set-up (`grep -l "pm/plans"`; the files
  are untracked, so `git grep` misses them). A size note "set-up
  only edits counted apart" in the step skill would size such items honestly.
