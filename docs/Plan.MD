# Yantra — Plan (v1)

Yantra is a computerised maintenance management system (CMMS) for VEL's plants.
Operators report breakdowns and log equipment readings from their phones; the
maintenance team works the jobs; engineers plan preventive maintenance and sign
it off; managers see downtime and compliance.

Status: broad outline agreed 11-10-2026; updated 12-10-2026 after reviewing the
external SRS draft (equipment classes, PM templates, CIL, shop-floor access,
intensity). Domain rules: `docs/Maintenance-Philosophy.md` (TPM-based). Data
model, screens and phases below are the starting shape, to be detailed module by
module before each is built.

## 1. Decisions so far

| Topic | Decision |
|---|---|
| Name | **Yantra** (app, package, repo). Deployment ID `vel_yantra_master` (later `vel_yantra_test`). URL `vel-yantra.mspv.app`. |
| Shape | Standalone Flask + Vue app on the SMTW web-app base (`.claude/SMTW-WebApp-Base.md`), like VelKilnMaster. Not a Frappe app. |
| Users | Shop floor on phones (mobile-first); engineers and managers also on desktop. English only (Tamil possibly in a later version). Online only — no offline mode. |
| Kiosks | Raspberry Pi kiosks on the shop floor, where operators and supervisors log on and enter things fast (stated 13-10-2026). A kiosk is **not tied to a unit**; what a user may do there follows their own unit access. Kiosks sit inside the plant, not in public areas. Sessions are personal: a user stays logged in across several entries and is logged out **manually or after a period of inactivity** (decided 13-10-2026). **Not in v1** — a later version. |
| Login | Keycloak SSO for everyone, realm `Office.smtw.in`, client `vel-yantra-master`. Keycloak supplies role membership (client roles of `vel-yantra-master`); Yantra maps roles to permissions. **Operators are Keycloak local users** in the same realm, with password login: no AD account, so no CAL (decided 13-10-2026; no PINs, no RFID/badges exist). Requirements: see *Shared-device login* below. |
| Sites and units | **All sites are covered** (decided 13-10-2026): the main factory, stock yards, farms and SSVT. Sites are created in Yantra (not fixed in code). SSVT is a site in the same company for now. Each site has units; unit codes use dot notation **`SITE.UNIT`** (e.g. `SMTW.KILN`, `BRICKS.SHED1`). Site list: `docs/Plant-Facts.md` § 2. |
| Shop-floor access | Which units a user may see is held in **Yantra's DB** (user → units), not in Keycloak (decided 12-10-2026). Applies to operators, technicians and engineers; the manager sees all units. |
| OneERP | Read-only. OneERP warehouses become equipment units. The warehouse mapping may be deferred. **Yantra's nomenclature leads** (decided 13-10-2026): OneERP warehouse codes may be renamed to match Yantra's `SITE.UNIT` codes (e.g. `SMTW.MCC` → `SMTW.MCC1` / `SMTW.MCC2`), rather than Yantra adopting OneERP's names. Renames are done in OneERP by its owners. |
| Hosting | customer7 (10.24.0.112), web container published on port **8990**. Front-proxy vhost is public (Keycloak is the gate); live since 11-10-2026. |
| Access from outside | Shop-floor phones use **mobile data**, so all roles get `access:wan` (decided 11-10-2026): the network gate does not restrict by role; Keycloak login is the gate. The real-client-IP handling and access log of the base pattern still apply. |
| Files | Photos and documents on disk under `data/`, which is an **App-FS** NFS export mounted into the container (like OneERP's files). No MinIO. |
| Repos | App code and docs here. Deployment in `smtw_erp_devops/erp_server/yantra/`, run with `erp_spanner.py <org> yantra <instance>` (like `erp_server/delivery`), so another org or a `test` instance is just a host file + settings file. |

## 2. Scope

### In v1

1. **Equipment register** — equipment and its component-units and components, equipment class, unit, documents, QR label.
2. **Breakdown tickets** — raised on the shop floor, worked by maintenance, closed by the engineer, with downtime timestamps and cause/action codes.
3. **Preventive maintenance (PM)** — PM templates applied to equipment; plans with checklists and readings, triggered by calendar or by meter; jobs filled on the phone with photos; engineer sign-off.
4. **CIL** (clean / inspect / lubricate) — operator checks, defined per equipment as part of its maintenance plan (§ 4.4).
5. **Meter readings** — manual entry on the phone.
6. **History and reports** — equipment history card, downtime, MTBF/MTTR, PM compliance.
7. **Notifications** — web push, Telegram, email.

### Not in v1

- **Parts** (ISO 14224 level 9 — bearings, seals) — the v1 equipment tree stops at component (decided 13-10-2026). Parts come with spares.
- Spares and stock (spares consumed per job, stock levels, OneERP stock entries).
- **Maintenance cost** — no labour cost (rates × hours) or other cost on tickets and PM jobs (decided 13-10-2026). Who worked and time spent are still recorded (§ 4.2), so cost can be derived later without changing how work is captured.
- **Rotable tracking** (motors, gearboxes, hydraulic pumps moving between equipment, with install/remove history) — later, with spares. See § 4.1.
- Telemetry from **plant-3i** (the sister IIoT repo): production counts per day, run hours, gauge values such as oil temperature, and PLC malfunction flags. The data model leaves room for it (reading `source`).
- Offline mode.
- Tamil UI and Tamil master data — possibly a later version.
- Equipment groups (a set of equipment picked by hand) — equipment class covers selecting equipment.
- Per-class custom fields (e.g. press tonnage). (Equipment *types* — S004 — are a pick-list value within a class, not a custom attribute.)
- A production-supervisor role — none planned: production supervisors have no special role in Yantra (decided 13-10-2026). There is no maintenance-supervisor role either.
- **Kiosks** (Raspberry Pi, shared) — a later version (decided 13-10-2026). Their login design is already settled (§ 3, *Shared-device login*).
- Detecting missed "before use" CIL checks (needs a signal that the equipment ran).
- Production counts per equipment, posted to OneERP — a later version; until then no write-back to OneERP.
- Backfilling history from the plant's notebooks — later.
- Multiple companies. VEL is one org unit; SSVT, a separate company, is handled as a site for now.

## 3. Roles

Roles come from Keycloak. A user may hold several; permissions are the union.

| Role | Who | Can do |
|---|---|---|
| `maint_operator` | Equipment operators | Raise breakdowns, log readings, do CIL jobs, see the status and open tickets of equipment |
| `maint_technician` | Maintenance technicians | Pick up and work breakdowns and PM jobs: record work, checklists, readings, photos; mark a breakdown "equipment back up" |
| `maint_engineer` | Maintenance engineers | Assign work; verify PM jobs; **close breakdowns**; create and edit equipment, PM plans, checklists and codes |
| `maint_manager` | Maintenance manager | Everything the engineer can, plus reports and dashboards across all units |
| `maint_storekeeper` | Maintenance stores | No v1 work (spares are not in v1); the role exists so these users can sign in. Stands outside the maintenance ladder. |
| `it_admin` | IT | Users' role view, master data housekeeping (units, OneERP sync), settings, notification channels. **Not** maintenance work and not all-powerful. |
| `admin` | Admin | Everything (bypass in code, per the RBAC pattern; also the org-wide `mspv-apps-admin` Keycloak role) |

Production supervisors have no special role in Yantra (decided 12-10-2026,
confirmed 13-10-2026); there is no maintenance-supervisor role.

**Unit access.** Roles say *what* a user may do; a per-user list of units,
kept in Yantra's DB, says *where*. Operators, technicians and engineers see and
act only on equipment, tickets and jobs at their units. The
maintenance manager sees all units. Every list and detail endpoint filters by
the user's units on the server.

**Shared-device login** (kiosks; decided 13-10-2026). Operators are Keycloak
local users in `Office.smtw.in` with passwords. Requirements:

- **Logout ends the Keycloak session too** (OIDC RP-initiated logout), both on
  manual logout and on inactivity timeout. Clearing only Yantra's token would
  leave the Keycloak cookie in the kiosk browser and sign the next person in as
  the previous one. The kiosk browser saves no passwords; "Remember me" is off.
- The screen always shows **who is logged in**, with a large logout button, so a
  forgotten session is noticed by the next person.
- **Usernames** follow one scheme that cannot clash with AD users — preferably
  the OneERP employee number (e.g. `E1042`).
- **Password policy** (realm-wide) per NIST SP 800-63B: minimum 8 characters,
  checked against breached-password lists, no forced complexity or periodic
  change. Brute-force protection on, with a **temporary** lockout (e.g. 15 min),
  so nobody can lock a colleague out for good from a shared kiosk.
- **Joiners and leavers** (ISO 27001 A.5.18): local users are not in AD, so
  disabling someone in AD does not disable them — the Keycloak user is disabled
  by hand when an operator leaves. Accounts and password resets are IT's job in
  Keycloak (`it_admin`), outside Yantra; Yantra stores no passwords.
- Inactivity timeout: start at about 5 minutes on kiosks (OWASP suggests 2–5
  min for shared devices); tune when kiosks arrive.

The full permission matrix (`config_rbac.py`, `module:action` keys) is written
with each module. First cut of the main keys:

| Key | operator | technician | engineer | manager | it_admin |
|---|---|---|---|---|---|
| `masters:read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `masters:edit` | | | | | ✓ |
| `masters:read_senior` | | | | | ✓ |
| `equipment:read` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `equipment:edit` | | | ✓ | ✓ | ✓ |
| `equipment:read_all_units` | | | | ✓ | ✓ |
| `equipment:purge_documents` | | | | ✓ | ✓ |
| `breakdown:raise` | ✓ | ✓ | ✓ | ✓ | |
| `breakdown:work` | | ✓ | ✓ | ✓ | |
| `breakdown:close` | | | ✓ | ✓ | |
| `pm_plan:edit` | | | ✓ | ✓ | |
| `pm_job:work` | ✓ | ✓ | ✓ | ✓ | |
| `pm_job:verify` | | | ✓ | ✓ | |
| `reading:log` | ✓ | ✓ | ✓ | ✓ | |
| `report:read` | | | ✓ | ✓ | |
| `settings:edit` | | | | | ✓ |

`masters:edit` (decided 13-10-2026) covers sites, units and users' unit access — IT
admin only. `masters:read_senior` (IT admin) is needed to view users' unit access;
engineers may be added in phase 3, when they assign work. `equipment:edit` covers equipment classes and equipment — engineers
(and so the manager) and IT admin. `equipment:read_all_units` (decided 14-10-2026, S002) is a
*scope* key: its holders see equipment at every unit; everyone else sees only the
units in their unit access. `equipment:purge_documents` (decided 16-10-2026, S008) —
manager and IT admin — lists removed documents and restores or deletes them for
good; erasing is kept apart from the everyday remove (ISO 27001 A.5.3, A.8.2).

`pm_job:work` is granted to operators because CIL jobs are PM jobs. *Which* jobs a
user may work is decided by data, not by more permissions: the plan's performer
(operator or maintenance) and the user's units. An operator therefore works
CIL jobs at their units and nothing else.

## 4. Modules

### 4.1 Equipment register

- **Hierarchy** (decided 13-10-2026), aligned with ISO 14224's taxonomy:

  | Level | Example | ISO 14224 level |
  |---|---|---|
  | **Site** | `SMTW`, `BRICKS`, `SSVT` | 3 installation |
  | **Unit** | `FWMILL`, `KILN` | 4–5 plant/unit, section/system |
  | **Equipment** | vertical blade mill | 6 equipment unit |
  | **Component-unit** | drive, hydraulic power pack | 7 subunit |
  | **Component** | motor, gearbox | 8 component / maintainable item |
  | **Part** | bearing, seal | 9 part — not in v1; spares, not in the tree (later) |

  Site and unit are places; equipment, component-units and components form the
  equipment tree. PM plans and tickets can point at any level of the tree.
- **Code = permanent identity** (decided 13-10-2026). Every node of the equipment
  tree has a code: the equipment class's prefix plus a sequential number, e.g.
  `VBM001`, `HP003`, `MOT017` (scheme details: open question 3). The code is
  printed on the QR label and never changes — not on a move, not on reclassification.
- **Full path is derived**, never stored as identity: `SITE.UNIT.EQUIPMENT`, extended
  down the tree (`SMTW.FWMILL.VBM001.MOT017`). It follows the equipment's current
  unit and parent, so moving a press from SMTW to SSVT or swapping a motor changes
  the path but not the code; the move is kept in the equipment's history.
- **Rotables (later, with spares; decided 13-10-2026).** A *rotable* is a component
  that is removed, repaired and refitted, often elsewhere (motors, gearboxes,
  hydraulic pumps). Tracking it means separating the *position* (e.g. VBM001's
  main drive) from the *physical item* (motor `MOT017`) and recording every
  install and removal, giving both a position history and an item history. It is
  deferred because it only works if every swap is recorded, because equipment-level
  history comes first, and because spare motors are OneERP stock (serial numbers).
  **v1:** a replacement is recorded on the ticket — action code "replaced" and the
  nameplate details in the remarks. **When built:** only a short list is tracked
  (e.g. motors above a kW threshold, gearboxes, hydraulic pumps); identity is our
  own code on a riveted or engraved metal tag with QR; the nameplate serial and
  data (kW, rpm, frame, mounting, make) are attributes, used to find
  interchangeable spares. The tree already gives components codes, so nothing in
  v1 needs redoing.
- **Fields:** code, name, equipment class, make, model, serial number, year, type (optional; one of its class's types — decided 15-10-2026, S004), criticality (A/B/C; required on equipment, default C; component-units and components inherit unless graded), status (in service / standby / out of use / scrapped — scrapped is final and read-only), unit. Only equipment has a unit; its parts follow it (decided 14-10-2026, S002). Which machine backs up which (a standby relationship) is not recorded. Notes: free text for reading, searchable, not in the history (S004).
- **Equipment class:** what a piece of equipment *is* (hydraulic press, ball mill, kiln fan, …), a list maintained by engineers. Used to pick equipment when applying a PM template, to compare MTBF/downtime across equipment of a kind, and (if failure codes are adopted) to scope code lists. No class-specific custom fields in v1.
- **Equipment type** (decided 15-10-2026, S004): how equipment of a class is built, e.g. `RPP` → closed / open execution (ISO 14224 class → type). Types are defined per class, maintained by engineers; an equipment's type must belong to its class.
- **Sites and units:** sites (SMTW, BRICKS, SSVT, the farms, …) are created in Yantra. Each site has units — its areas and shop floors — coded `SITE.UNIT` (e.g. `SMTW.KILN`, `SSVT.SHOP`). A unit can be mapped to a OneERP warehouse code. Until the sync exists, units are maintained by hand.
- **Codes frozen once in use** (decided 13-10-2026, S001). A site, unit or equipment-class
  code — and a unit's site — can be corrected only while nothing references the record
  (site: has units; unit: has users' unit access or, later, equipment; class: has
  equipment). After that it is frozen. For class codes this protects equipment codes,
  which embed the prefix. For sites and units it is change control (ISO 55001): OneERP
  warehouse names, printed lists and history snapshots follow the codes. Master records
  are deactivated, never deleted.
- **Documents:** manuals, drawings, photos attached to a piece of equipment (S006), or to an equipment class or type and then shown read-only on every node of it, at every unit — one controlled copy (decided 16-10-2026, S009). Each node shows its own class's and type's documents, not its parent's.
- **QR label:** printable per equipment; scanning it on a phone opens the equipment page, from where an operator can raise a breakdown or log a reading in one tap.

### 4.2 Breakdown tickets

States and who moves them:

```
raised ──► acknowledged ──► in progress ──► back in service ──► closed
(operator) (technician/     (technician)    (technician)        (engineer)
            engineer)
                                              └─ engineer can send back to "in progress"
raised / acknowledged ──► closed  (engineer, frivolous — code + remarks required)
```

- **Timestamps** for each transition. From them: response time (raised → acknowledged), repair time (in progress → back in service), downtime (raised → back in service).
- **Intensity** (the TPM red tag is this ticket): the operator grades the problem. Scale (decided 15-10-2026), from ISO 14224's failure impact: **critical** (equipment stopped), **degraded** (running with reduced function), **initial** (still fine, early signs; ISO 14224 calls it *incipient*). Only critical time counts as downtime.
- **Codes** (ISO 14224 core, decided 15-10-2026): failure mode (the operator picks it as the symptom), failure cause and maintenance action (technician/engineer pick). Lists trimmed from ISO 14224 Annex B, maintained by engineers. Mechanism not in v1; detection method automatic (below).
- **No approval step:** a raised ticket goes straight to maintenance. If it turns out frivolous, the engineer **closes it directly** from raised or acknowledged, with a required code (e.g. *no fault found*, *not a breakdown*) and remarks.
- **Who worked:** one or more technicians per ticket, with time spent.
- **Photos and remarks** at any step.
- **Notifications:** new ticket → maintenance; escalation if not acknowledged within a set time (per criticality).
- Serial: `BD-YYYY-MM-NNN`.
- **Shared ticket API (later)** — the intended way for other systems (plant-3i,
  VelKilnMaster, any later one) to raise tickets: one authenticated endpoint, not
  one integration per system. The caller sends the equipment's permanent code,
  symptom, intensity and a description. Each ticket records its **source**
  (`operator`, `plant-3i`, `vel-kiln`, …). A system that keeps flagging the same
  equipment adds to its open ticket instead of opening new ones. Sensors that
  raise flags are registered in Yantra as equipment or components with their own
  codes.
- **Detection method** (ISO 14224 — how the failure was found; **Proposed**):
  filled automatically from where the ticket came from — operator observation
  (raised by hand or from CIL), periodic maintenance (from a PM job), condition
  monitoring (from a reading or a system via the API). Over time the mix shows
  whether failures are being caught before they stop production.

### 4.3 Preventive maintenance

**PM template** (the work, e.g. "Press — monthly hydraulic check"): checklist and
reading items, triggers, photo required. A class usually has several templates
(monthly, annual); a template may also span classes (e.g. motor greasing).
Engineers apply a template by picking equipment — typically by equipment class, then
removing exceptions — and Yantra creates one PM plan per equipment. Each plan keeps
its own schedule and meter. How later template edits reach existing plans is open
question 6. CIL plans can come from templates the same way.

**PM plan** (one per equipment and task, e.g. "Kiln fan — monthly bearing check"; created from a template or by hand):

- Checklist items: OK / Not OK / NA, with remarks.
- Reading items: a measured value with unit of measure and limits (min/max), e.g. temperature, vibration, roller clearance, wear in mm.
- Photo required: yes/no per plan.
- **Triggers** — one or both:
  - **Calendar:** every N days / weeks / months. **The next job is due from the completion date of the last one.** If a plan needs a different rhythm, the engineer edits the plan.
  - **Meter:** every N units of a meter (run hours, production count), or when a reading crosses a limit. **Crossing creates a PM job automatically** and notifies, just like a calendar job falling due.
- **Performer:** maintenance (team or technician, the default for generated jobs) or operator (CIL plans).

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

### 4.4 CIL (clean / inspect / lubricate)

CIL is a **PM plan whose performer is the operator** — not a piece of equipment flag and not a
separate module. Each equipment's CIL checklist is defined with its maintenance plan:

- **Items** are grouped Clean / Inspect / Lubricate. Clean and Inspect are always
  present; Lubricate only if the equipment needs it. Items vary per equipment.
- **No CIL plan** (null checklist) means CIL is not required for that equipment.
- **Trigger**, chosen per equipment:
  - **Before use** — due before the equipment's first use on a day it runs. Yantra
    cannot know a piece of equipment is starting, so the operator starts it: scan the
    equipment's QR → "Start CIL". At most one before-use CIL job per equipment per day.
  - **Frequency** — a calendar interval, like any calendar PM plan.
- Operators do CIL jobs on the phone for equipment at their units. A Not OK
  item can raise a breakdown ticket in one tap.
- Whether CIL jobs need engineer verification is open question 10.
- **Missed checks:** frequency-based CIL shows overdue like any PM job. Missed
  *before-use* checks are not detected in v1 — that needs evidence the equipment
  ran (production counts, later).

### 4.5 Meters and readings

- A piece of equipment has meters: run hours, production count, or a measured quantity (oil temperature, roller clearance, vibration, wear mm). Each meter has a unit of measure and a type: **counter** (only goes up; triggers every N units) or **gauge** (a level; triggers on crossing limits).
- Readings are entered by hand — from a "log reading" screen (via the equipment's QR) or as part of a PM job.
- A counter reading lower than the previous one is rejected unless marked as a meter reset.
- Each reading stores its source (`manual` now; `iiot` later), so an automatic feed can be added without changing the model.

### 4.6 History and reports

- **Equipment history card:** all breakdowns, PM jobs and readings of a piece of equipment, newest first.
- **Downtime:** per equipment / unit / cause code, per period.
- **MTBF / MTTR** per equipment and unit.
- **PM compliance:** jobs due vs. done on time vs. overdue, per unit and plan.
- **Reading trends:** a chart per meter, with its limits drawn in.
- Export to Excel for each report.
- Tickets closed as frivolous are excluded from downtime and MTBF/MTTR (Proposed — confirm before phase 5).

### 4.7 Notifications

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
| `sites` | Code (e.g. `SMTW`, `BRICKS`), name, address, active |
| `units` | `site_id`, code (the part after the dot; the full `SITE.UNIT` code is derived), name, optional OneERP warehouse code, active |
| `equipment_classes` | Code (= the equipment-code prefix, e.g. `VBM`), name, active |
| `equipment_types` | Per class: name, active (S004); `equipment.type_id` must be a type of the equipment's class |
| `equipment` | Register fields, `level` (equipment / component-unit / component), `parent_id` for the tree, `unit_id` (equipment only), `equipment_class_id` |
| `equipment_events` | Equipment history: one row per move or change of status, criticality or class — old → new, who, when (S002) |
| `user_units` | User (Keycloak username) → unit: the shop-floor access list |
| `equipment_documents` | Files attached to equipment: kind (document / photo), title (editable), original name, system-generated stored name, type, size, thumbnail flag; created / updated / removed who and when — removal hides, the file stays (S006); a removed document is restored or deleted for good (row and file, logged) by the manager or IT admin from Settings (S008); owner is exactly one of node, class or type (S009) |
| `codes` | Symptom / cause / action pick-lists (`kind`, code, label, active) |
| `breakdowns` | Ticket: equipment, state, intensity, codes, remarks, serial |
| `breakdown_events` | One row per state change: who, when, remark — the timestamps come from here |
| `breakdown_labour` | Technician and time spent per ticket |
| `meters` | Per equipment: name, unit of measure, type (counter/gauge), limits |
| `meter_readings` | Value, time, who, source (`manual`/`iiot`), PM job link if taken during one |
| `pm_templates`, `pm_template_items` | Reusable PM work: items, triggers, photo required |
| `pm_plans` | Equipment, title, kind (PM / CIL), performer (maintenance / operator), source template, triggers (calendar interval, meter + threshold, before use), default assignee, photo required |
| `pm_plan_items` | Checklist and reading items of a plan; CIL items carry their group (C / I / L) |
| `pm_jobs` | Generated job: plan, due date or triggering reading, state, serial |
| `pm_job_results` | One row per plan item: result or value, remark |
| `pm_job_events` | State changes, like `breakdown_events` |
| `attachments` | Photos and files for tickets and jobs (system-generated names) |
| `push_subscriptions` | Web push endpoints per user and device |
| `serial_counters` | Per-scope counters (locked `FOR UPDATE`): equipment codes per class prefix from phase 2 (S002), later `BD-` and `PM-` serials |
| `task_queue` | Base pattern: notifications, PM generation, sync |
| `app_settings` | Escalation times, upload limits, internal networks, etc. |

All timestamps are stored as IST (`DATETIME`, connection timezone Asia/Kolkata) per
the base timezone policy. Dates are shown as DD-MM-YYYY.

## 6. Screens

**Phone (operator, technician):**

- Home: "my jobs" (assigned tickets and PM jobs due; CIL jobs for operators), "raise breakdown", "scan equipment".
- Equipment page (from QR): status, open tickets, due PMs; buttons "raise breakdown", "log reading", "start CIL" (before-use equipment).
- Raise breakdown: equipment, intensity, symptom, remark, photo — four taps for the common case.
- Ticket: timeline, act on the next step, add photos, labour.
- PM job: checklist and readings one item per row, out-of-limit flagged as you type, photos, "done".

**Desktop (engineer, manager, admin):**

- Dashboard: open tickets by age, equipment down now, PMs due/overdue, out-of-limit readings.
- Equipment register and tree, equipment classes, PM templates (apply to equipment) and plans (including CIL), codes, units, users' unit access. *Built so far (15-10-2026): the equipment register — list, equipment page with tree and history (S003), and the masters (S001).*
- Ticket and PM job lists with filters; verify / close queues.
- Reports (§ 4.6).
- Settings (IT-Admin): escalation times, notification channels, OneERP sync, internal networks.

## 7. Integrations

| System | Use | Direction |
|---|---|---|
| Keycloak (`sso.mspv.app`) | Login (OIDC + PKCE), role membership | read |
| OneERP | Warehouse list → unit mapping | read-only, scheduled sync; API key in `secrets_app.py` |
| Telegram | Notifications | send |
| Mail server | Daily summary | send |
| Web Push | Phone notifications | send |
| plant-3i (later) | Telemetry: production counts, run hours, gauge values, PLC malfunction flags; raises tickets via the shared ticket API (§ 4.2) | read / receive |
| VelKilnMaster (later) | Kiln sensors flagged as needing maintenance, via the shared ticket API (§ 4.2) | receive |

## 8. Build phases

Each phase ends usable on its own.

1. **Foundation** — app skeleton per the base: Keycloak login, roles and RBAC, internet exposure (real client IP, network gate, access log), migrations, job queue, version endpoint and stale-bundle check, PWA shell. Deployment in `smtw_erp_devops/erp_server/yantra/` via `erp_spanner.py` (add `yantra` to its known apps; Yantra migrates its DB at startup, so `erp_spanner migrate` is not used), first deploy to customer7:8990.
2. **Equipment register** — sites and units, users' unit access, equipment classes, equipment tree, documents, QR labels. Lets the team load the equipment list.
3. **Breakdowns** — the full ticket flow, codes, labour, photos, Telegram + web push for new tickets and escalation. First module the shop floor uses.
4. **Meters, PM and CIL** — meters and readings, PM templates and plans with checklists and readings, calendar / meter / before-use triggers, PM and CIL jobs, verification.
5. **History, reports, daily email** — history card, downtime, MTBF/MTTR, PM compliance, reading trends, Excel export, daily summary.
6. **OneERP warehouse sync** — unit mapping from OneERP (can move earlier if wanted; it is independent).

## 9. Open questions

1. ~~**Keycloak roles:** realm or client roles?~~ Decided 12-10-2026: client roles of `vel-yantra-master` (`maint_operator`, `maint_technician`, `maint_engineer`, `maint_manager`, `maint_storekeeper`, `it_admin`).
2. **Escalation times:** how long before an unacknowledged breakdown escalates, per criticality? *Deferred 15-10-2026: decided with the notification step (Telegram / web push); stored as settings, not code.*
3. ~~**Equipment codes**~~ Decided 13-10-2026: class prefix of 2–4 letters + 3-digit number (`VBM001`), growing to 4 digits past 999; one counter per prefix across all sites, so a code survives a move.
4. ~~**Downtime definition**~~ Decided 15-10-2026: downtime ends at the technician's **"back in service"** (SMRP: repair time runs to restoration). Whether the operator can mark "not fixed" to reopen the ticket is settled with the phase 3 brief.
5. ~~**Failure coding**~~ Decided 15-10-2026: the **ISO 14224 core** — failure **mode** (the operator picks it as the symptom), failure **cause** and maintenance **action** (technician/engineer), with lists trimmed from ISO 14224 Annex B and maintained by engineers. Mechanism is left out for now; detection method is filled automatically from the ticket's source (§ 4.2). Mode lists may later be scoped by equipment class.
6. **Template edits:** when a PM template changes, do plans created from it update, or keep their copy until re-applied?
7. ~~**Unit access upkeep**~~ Decided 13-10-2026: IT admin maintains users' unit lists (and sites and units) — `masters:edit`.
8. ~~**CIL shifts**~~ Superseded: CIL is per equipment, before use or by frequency (§ 4.4); missed before-use detection is deferred.
9. ~~**Intensity scale**~~ Decided 15-10-2026: **critical / degraded / initial** — ISO 14224's failure impact, with the plain word *initial* for the standard's *incipient*.
10. **CIL verification:** does an engineer verify CIL jobs, or are they done when the operator submits?
11. ~~**Kiosks.**~~ Decided 13-10-2026: not in v1; not tied to a unit; operators are Keycloak local users with passwords; logout manual or on inactivity; no supervisor role; resets by IT in Keycloak (Decisions table, § 3).
