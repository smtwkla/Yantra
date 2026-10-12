# Yantra — Plan (v1)

Yantra is a computerised maintenance management system (CMMS) for VEL's plants.
Operators report breakdowns and log machine readings from their phones; the
maintenance team works the jobs; engineers plan preventive maintenance and sign
it off; managers see downtime and compliance.

Status: broad outline agreed 11-10-2026. Data model, screens and phases below
are the starting shape, to be detailed module by module before each is built.

## 1. Decisions so far

| Topic | Decision |
|---|---|
| Name | **Yantra** (app, package, repo). Deployment ID `vel_yantra_master` (later `vel_yantra_test`). URL `vel-yantra.mspv.app`. |
| Shape | Standalone Flask + Vue app on the SMTW web-app base (`.claude/SMTW-WebApp-Base.md`), like VelKilnMaster. Not a Frappe app. |
| Users | Shop floor on phones (mobile-first); engineers and managers also on desktop. English only. Online only — no offline mode. |
| Login | Keycloak SSO for everyone, realm `Office.smtw.in`. Keycloak supplies role membership; Yantra maps roles to permissions. |
| OneERP | Read-only. OneERP warehouses become machine locations. The warehouse mapping may be deferred. |
| Hosting | customer7 (10.24.0.112), web container published on port **8990**. Front-proxy vhost is public (Keycloak is the gate); live since 11-10-2026. |
| Access from outside | Shop-floor phones use **mobile data**, so all roles get `access:wan` (decided 11-10-2026): the network gate does not restrict by role; Keycloak login is the gate. The real-client-IP handling and access log of the base pattern still apply. |
| Files | Photos and documents on disk under `data/`, which is an **App-FS** NFS export mounted into the container (like OneERP's files). No MinIO. |
| Repos | App code and docs here. Deployment in `smtw_erp_devops/erp_server/yantra/`, run with `erp_spanner.py <org> yantra <instance>` (like `erp_server/delivery`), so another org or a `test` instance is just a host file + settings file. |

## 2. Scope

### In v1

1. **Machine register** — machines and their parts, location, documents, QR label.
2. **Breakdown tickets** — raised on the shop floor, worked by maintenance, closed by the engineer, with downtime timestamps and cause/action codes.
3. **Preventive maintenance (PM)** — plans with checklists and readings, triggered by calendar or by meter; jobs filled on the phone with photos; engineer sign-off.
4. **Meter readings** — manual entry on the phone.
5. **History and reports** — machine history card, downtime, MTBF/MTTR, PM compliance.
6. **Notifications** — web push, Telegram, email.

### Not in v1

- Spares and stock (spares consumed per job, stock levels, OneERP stock entries).
- Automatic meter feeds from IIoT / plant-3i — the data model leaves room for it.
- Offline mode, Tamil UI.
- Any write-back to OneERP.
- Multiple companies (VEL only).

## 3. Roles

Roles come from Keycloak. A user may hold several; permissions are the union.

| Role | Who | Can do |
|---|---|---|
| `maint_operator` | Machine operators and Production Supervisors | Raise breakdowns, log readings, see the status and open tickets of machines |
| `maint_technician` | Maintenance technicians | Pick up and work breakdowns and PM jobs: record work, checklists, readings, photos; mark a breakdown "machine back up" |
| `maint_engineer` | Maintenance engineers | Assign work; verify PM jobs; **close breakdowns**; create and edit machines, PM plans, checklists and codes |
| `maint_manager` | Maintenance manager | Everything the engineer can, plus reports and dashboards across all locations |
| `it_admin` | IT | Users' role view, master data housekeeping (locations, OneERP sync), settings, notification channels. **Not** maintenance work and not all-powerful. |
| `admin` | Admin | Everything (bypass in code, per the RBAC pattern; also the org-wide `mspv-apps-admin` Keycloak role) |

The full permission matrix (`config_rbac.py`, `module:action` keys) is written
with each module. First cut of the main keys:

| Key | operator | technician | engineer | manager | it_admin |
|---|---|---|---|---|---|
| `machine:read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `machine:edit` | | | ✓ | ✓ | ✓ |
| `breakdown:raise` | ✓ | ✓ | ✓ | ✓ | |
| `breakdown:work` | | ✓ | ✓ | ✓ | |
| `breakdown:close` | | | ✓ | ✓ | |
| `pm_plan:edit` | | | ✓ | ✓ | |
| `pm_job:work` | | ✓ | ✓ | ✓ | |
| `pm_job:verify` | | | ✓ | ✓ | |
| `reading:log` | ✓ | ✓ | ✓ | ✓ | |
| `report:read` | | | ✓ | ✓ | |
| `settings:edit` | | | | | ✓ |

## 4. Modules

### 4.1 Machine register

- **Machine tree:** machine → sub-assembly → component. PM plans and tickets can point at any level.
- **Fields:** code (unique, human-readable), name, make, model, serial number, year, criticality (A/B/C), status (in service / standby / scrapped), location.
- **Location:** a location list in Yantra. Each location can be mapped to a OneERP warehouse code (e.g. SMTW.MCC, SMTW.KILN, SMTW.MACSHP, SSVT.SHOP, BRICKS, STOCKY1.SHED1). Until the sync exists, locations are maintained by hand.
- **Documents:** manuals, drawings, photos attached to a machine.
- **QR label:** printable per machine; scanning it on a phone opens the machine page, from where an operator can raise a breakdown or log a reading in one tap.

### 4.2 Breakdown tickets

States and who moves them:

```
raised ──► acknowledged ──► in progress ──► machine up ──► closed
(operator)  (technician/     (technician)    (technician)   (engineer)
             engineer)
                                              └─ engineer can send back to "in progress"
```

- **Timestamps** for each transition. From them: response time (raised → acknowledged), repair time (in progress → machine up), downtime (raised → machine up).
- **Machine stopped?** The operator says whether the machine is stopped or running degraded; only stopped time counts as downtime.
- **Codes:** symptom (operator picks), cause and action (technician/engineer pick). Pick-lists maintained by engineers.
- **Who worked:** one or more technicians per ticket, with time spent.
- **Photos and remarks** at any step.
- **Notifications:** new ticket → maintenance; escalation if not acknowledged within a set time (per criticality).
- Serial: `BD-YYYY-MM-NNN`.

### 4.3 Preventive maintenance

**PM plan** (one per machine and task, e.g. "Kiln fan — monthly bearing check"):

- Checklist items: OK / Not OK / NA, with remarks.
- Reading items: a measured value with unit and limits (min/max), e.g. temperature, vibration, roller clearance, wear in mm.
- Photo required: yes/no per plan.
- **Triggers** — one or both:
  - **Calendar:** every N days / weeks / months. **The next job is due from the completion date of the last one.** If a plan needs a different rhythm, the engineer edits the plan.
  - **Meter:** every N units of a meter (run hours, production count), or when a reading crosses a limit. **Crossing creates a PM job automatically** and notifies, just like a calendar job falling due.
- Assigned team or technician (default for generated jobs).

**PM job** (generated from a plan):

```
due ──► in progress ──► done ──► verified
        (technician)    (technician)  (engineer)
                                └─ engineer can send back to "in progress"
```

- The technician fills checklist, readings and photos on the phone.
- A reading outside its limits is flagged on the job; the technician can raise a breakdown ticket from it in one tap.
- Overdue jobs show on dashboards and are notified.
- Serial: `PM-YYYY-MM-NNN`.

### 4.4 Meters and readings

- A machine has meters: run hours, production count, or a measured quantity (oil temperature, roller clearance, vibration, wear mm). Each meter has a unit and a type: **counter** (only goes up; triggers every N units) or **gauge** (a level; triggers on crossing limits).
- Readings are entered by hand — from a "log reading" screen (via the machine's QR) or as part of a PM job.
- A counter reading lower than the previous one is rejected unless marked as a meter reset.
- Each reading stores its source (`manual` now; `iiot` later), so an automatic feed can be added without changing the model.

### 4.5 History and reports

- **Machine history card:** all breakdowns, PM jobs and readings of a machine, newest first.
- **Downtime:** per machine / location / cause code, per period.
- **MTBF / MTTR** per machine and location.
- **PM compliance:** jobs due vs. done on time vs. overdue, per location and plan.
- **Reading trends:** a chart per meter, with its limits drawn in.
- Export to Excel for each report.

### 4.6 Notifications

| Event | Web push | Telegram | Email |
|---|---|---|---|
| New breakdown | maintenance on duty | maintenance group | |
| Breakdown not acknowledged in time | engineers | maintenance group | |
| Job assigned to you | the technician | | |
| PM job due / overdue | assigned technician | maintenance group (overdue only) | |
| Reading out of limits | engineers | | |
| Daily summary (open tickets, overdue PMs, yesterday's downtime) | | | engineers, manager |

- **Web push:** Yantra is installable as a PWA; push uses the browser's Web Push (VAPID keys, no third party).
- **Telegram:** the base pattern — group-routed, sent from the job queue.
- **Email:** the existing mail server, from the job queue.
- All sends go through the DB-backed job queue, so a slow channel never blocks a request.

## 5. Data model (broad strokes)

| Table | Holds |
|---|---|
| `locations` | Code, name, optional OneERP warehouse code |
| `machines` | Register fields, `parent_id` for the tree, `location_id` |
| `machine_documents` | Files attached to machines |
| `codes` | Symptom / cause / action pick-lists (`kind`, code, label, active) |
| `breakdowns` | Ticket: machine, state, stopped flag, codes, remarks, serial |
| `breakdown_events` | One row per state change: who, when, remark — the timestamps come from here |
| `breakdown_labour` | Technician and time spent per ticket |
| `meters` | Per machine: name, unit, type (counter/gauge), limits |
| `meter_readings` | Value, time, who, source (`manual`/`iiot`), PM job link if taken during one |
| `pm_plans` | Machine, title, triggers (calendar interval, meter + threshold), default assignee, photo required |
| `pm_plan_items` | Checklist and reading items of a plan |
| `pm_jobs` | Generated job: plan, due date or triggering reading, state, serial |
| `pm_job_results` | One row per plan item: result or value, remark |
| `pm_job_events` | State changes, like `breakdown_events` |
| `attachments` | Photos and files for tickets and jobs (system-generated names) |
| `push_subscriptions` | Web push endpoints per user and device |
| `serial_counters` | Per-scope counters for `BD-` and `PM-` serials (locked `FOR UPDATE`) |
| `task_queue` | Base pattern: notifications, PM generation, sync |
| `app_settings` | Escalation times, upload limits, internal networks, etc. |

All timestamps are stored as IST (`DATETIME`, connection timezone Asia/Kolkata) per
the base timezone policy. Dates are shown as DD-MM-YYYY.

## 6. Screens

**Phone (operator, technician):**

- Home: "my jobs" (assigned tickets and PM jobs due), "raise breakdown", "scan machine".
- Machine page (from QR): status, open tickets, due PMs; buttons "raise breakdown", "log reading".
- Raise breakdown: machine, stopped?, symptom, remark, photo — four taps for the common case.
- Ticket: timeline, act on the next step, add photos, labour.
- PM job: checklist and readings one item per row, out-of-limit flagged as you type, photos, "done".

**Desktop (engineer, manager, admin):**

- Dashboard: open tickets by age, machines down now, PMs due/overdue, out-of-limit readings.
- Machine register and tree, PM plans and their items, codes, locations.
- Ticket and PM job lists with filters; verify / close queues.
- Reports (§ 4.5).
- Settings (IT-Admin): escalation times, notification channels, OneERP sync, internal networks.

## 7. Integrations

| System | Use | Direction |
|---|---|---|
| Keycloak (`sso.mspv.app`) | Login (OIDC + PKCE), role membership | read |
| OneERP | Warehouse list → location mapping | read-only, scheduled sync; API key in `secrets_app.py` |
| Telegram | Notifications | send |
| Mail server | Daily summary | send |
| Web Push | Phone notifications | send |

## 8. Build phases

Each phase ends usable on its own.

1. **Foundation** — app skeleton per the base: Keycloak login, roles and RBAC, internet exposure (real client IP, network gate, access log), migrations, job queue, version endpoint and stale-bundle check, PWA shell. Deployment in `smtw_erp_devops/erp_server/yantra/` via `erp_spanner.py` (add `yantra` to its known apps; Yantra migrates its DB at startup, so `erp_spanner migrate` is not used), first deploy to customer7:8990.
2. **Machine register** — locations, machine tree, documents, QR labels. Lets the team load the machine list.
3. **Breakdowns** — the full ticket flow, codes, labour, photos, Telegram + web push for new tickets and escalation. First module the shop floor uses.
4. **Meters and PM** — meters and readings, PM plans with checklists and readings, calendar and meter triggers, PM jobs, verification.
5. **History, reports, daily email** — history card, downtime, MTBF/MTTR, PM compliance, reading trends, Excel export, daily summary.
6. **OneERP warehouse sync** — location mapping from OneERP (can move earlier if wanted; it is independent).

## 9. Open questions

1. **Keycloak roles:** create the six roles as realm roles, or as client roles of a `yantra` client?
2. **Escalation times:** how long before an unacknowledged breakdown escalates, per criticality?
3. **Machine codes:** is there an existing numbering scheme to adopt?
4. **Downtime definition:** does downtime end at "machine up" (technician) or at the operator's confirmation?
