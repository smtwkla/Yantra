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
| Login | Keycloak SSO for everyone, realm `Office.smtw.in`, client `vel-yantra-master`. Keycloak says who may log in (client role `maintenance_team`) and who is IT admin (`it_admin`); the org-wide realm role `mspv-apps-admin` is admin. The maintenance roles are held **in Yantra, per site** (S011, decided 16-10-2026); Yantra maps roles to permissions. **Operators are Keycloak local users** in the same realm, with password login: no AD account, so no CAL (decided 13-10-2026; no PINs, no RFID/badges exist). Requirements: see *Shared-device login* below. Client, roles and setup: `docs/Keycloak.md`. |
| Sites and units | **All sites are covered** (decided 13-10-2026): the main factory, stock yards, farms and SSVT. Sites are created in Yantra (not fixed in code). SSVT is a site in the same company for now. Each site has units; unit codes use dot notation **`SITE.UNIT`** (e.g. `SMTW.KILN`, `BRICKS.SHED1`). Site list: `docs/Plant-Facts.md` § 2. |
| Shop-floor access | Which units a user may see is held in **Yantra's DB**, not in Keycloak (decided 12-10-2026). Since S011 (16-10-2026) a user's **role is per site** too: per site one role, and either all units of the site or chosen units. A manager normally has all units of their site(s). Since S011 A1 the roles hang off the person in **Team**: the token's login → the active person with that login → their site roles (deactivating the person ends access). |
| OneERP | Read-only. OneERP warehouses become equipment units. The warehouse mapping may be deferred. **Yantra's nomenclature leads** (decided 13-10-2026): OneERP warehouse codes may be renamed to match Yantra's `SITE.UNIT` codes (e.g. `SMTW.MCC` → `SMTW.MCC1` / `SMTW.MCC2`), rather than Yantra adopting OneERP's names. Renames are done in OneERP by its owners. |
| Hosting | customer7 (10.24.0.112), web container published on port **8990**. Front-proxy vhost is public (Keycloak is the gate); live since 11-10-2026. |
| Access from outside | Shop-floor phones use **mobile data**, so every role works from anywhere (decided 11-10-2026), **except IT admin, which works only from the plant network** (S013, 18-10-2026; ISO 27001 A.8.2). Managers work from anywhere too. Admin (`mspv-apps-admin`) bypasses the gate, so a wrong network list can be fixed from anywhere; protect it with Keycloak two-factor login. The VPN pool counts as internal. Internal ranges are set in Settings › Network. The real client IP comes from `X-Real-IP`; every sighting is in the access log (365 days, purged by the worker). |
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
- Spares and stock (spares consumed per job, stock levels, OneERP stock entries). Wear parts kept in stock (augers, mixer paddles, shredding knives, liners) wait for this, as does a structured **bill of materials** per model (ISO 14224 level 9 parts with maker or generic part numbers). Makers' parts lists are model documents (S012); parts actually used are recorded per ticket (§ 4.2, *Proposed*).
- **AMC register** (contract terms per equipment: vendor, visits per year, response time, expiry) — a later master (16-10-2026). ISO 55001 § 8.3 asks that outsourced maintenance be controlled. In v1 the terms go in the equipment's notes; the vendor's visits are PM jobs (§ 4.3).
- **Maintenance cost** — no labour cost (rates × hours) or other cost on tickets and PM jobs (decided 13-10-2026). Who worked and time spent are still recorded (§ 4.2), so cost can be derived later without changing how work is captured.
- **Rotable tracking** (motors, gearboxes, hydraulic pumps moving between equipment, with install/remove history) — later, with spares. See § 4.1.
- Telemetry from **plant-3i** (the sister IIoT repo): production counts per day, run hours, gauge values such as oil temperature, and PLC malfunction flags. The data model leaves room for it (reading `source`).
- Offline mode.
- Tamil UI and Tamil master data — possibly a later version.
- Equipment groups (a set of equipment picked by hand) — equipment class covers selecting equipment.
- Per-class custom fields (e.g. press tonnage). (Equipment *types* — S004 — are a pick-list value within a class, not a custom attribute.)
- **Kiosks** (Raspberry Pi, shared) — a later version (decided 13-10-2026). Their login design is already settled (§ 3, *Shared-device login*).
- Detecting missed "before use" CIL checks (needs a signal that the equipment ran).
- Production counts per equipment, posted to OneERP — a later version; until then no write-back to OneERP.
- **Installation and modification work** (a new concrete machine wired up, trials of new
  packing machines) — not recorded in Yantra in v1 (decided 18-10-2026, daily-report use
  case). EN 13306 keeps modification and installation apart from maintenance. Such work is
  written by hand on the printed daily work log (§ 4.6); the new equipment itself is
  registered with its in-service date.
- Backfilling history from the plant's notebooks — later.
- Multiple companies. VEL is one org unit; SSVT, a separate company, is handled as a site for now.

## 3. Roles

**Roles per site** (S011, decided 16-10-2026; A1). The maintenance roles below are held in Yantra, on the person in **Team**: per person and site, **one** role, with all the site's units or chosen ones. For a person with a login those rows are their access. IT admin grants every role; an engineer (`people:assign_technicians` at the site) assigns **Technicians** at their own site only; nobody changes their own access. A person without a login can be a Technician **or an Operator** (the row then says where they work, for pick-lists). **Operators without a login** are created by supervisors and engineers at their own site (decided 16-10-2026, sorting-line use case; the permission key is settled in the brief that builds it, on the pattern of `people:assign_technicians`). They are needed so CIL jobs and tickets can say who did the check and who found the fault when the operator has no phone (ISO 14224: who detected, who worked). At a record, a user's rights are those of their role at the record's site; navigation and site-less masters use the union over their sites. `it_admin` and `admin` stay in Keycloak and apply everywhere; Keycloak's `maintenance_team` only lets a user log in. A deliberate departure from the base RBAC pattern (roles from the token), recorded in `.claude/CLAUDE.md`.

| Role | Who | Can do |
|---|---|---|
| `maint_operator` | Equipment operators | Raise breakdowns, log readings, do CIL jobs, see the status and open tickets of equipment |
| `maint_technician` | Maintenance technicians | Pick up and work breakdowns and PM jobs: record work, checklists, readings, photos; mark a breakdown "equipment back up" |
| `maint_engineer` | Maintenance engineers | Assign work; verify PM jobs; **close breakdowns**; create and edit equipment, PM plans, checklists and codes |
| `maint_manager` | Maintenance manager | Everything the engineer can, plus reports and dashboards across all units of their site(s) |
| `maint_supervisor` | Production supervisors (S011 A1, decided 16-10-2026) | An operator's rights today (CIL, raise issues, readings), more reports later; usually wider units than an operator. Production-side (TPM autonomous maintenance): above the operator, **off** the maintenance ladder, so a supervisor does not work tickets. Records on behalf of operators without a phone: CIL done, fault found, **back in service** with the technician's name, each with the event time; creates operators without a login at their site (sorting-line use case, 16-10-2026) |
| `maint_storekeeper` | Maintenance stores | No v1 work (spares are not in v1); the role exists so these users can sign in. Stands outside the maintenance ladder. |
| `it_admin` | IT | Users' role view, master data housekeeping (units, OneERP sync), settings, notification channels. **Not** maintenance work and not all-powerful. |
| `admin` | Admin | Everything (bypass in code, per the RBAC pattern; also the org-wide `mspv-apps-admin` Keycloak role) |

Production supervisors have the `maint_supervisor` role (S011 A1, 16-10-2026; it
replaces "no special role", decided 13-10-2026). There is still no
maintenance-supervisor role: EN 15628's "maintenance supervisor" is about an engineer here.

**Unit access.** Roles say *what* a user may do; each site row also says
*where*: all units of the site, or chosen units. Operators, technicians and
engineers see and act only on equipment, tickets and jobs at their units. The
maintenance manager normally has all units of their site(s). Every list and
detail endpoint filters by the user's units on the server, per permission key.

**Shared-device login** (kiosks; decided 13-10-2026). Operators are Keycloak
local users with passwords. Logout ends the Keycloak session too, and the screen
always shows who is logged in, with a large logout button. The Keycloak
settings and the full requirements (usernames, password policy, lockout,
leavers, inactivity) are in `docs/Keycloak.md` § 5–6.

The full permission matrix (`config_rbac.py`, `module:action` keys) is written
with each module. First cut of the main keys:

| Key | operator | supervisor | technician | engineer | manager | it_admin |
|---|---|---|---|---|---|---|
| `masters:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `masters:edit` | | | | | | ✓ |
| `masters:read_senior` | | | | | | ✓ |
| `equipment:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `equipment:edit` | | | | ✓ | ✓ | ✓ |
| `equipment:read_all_units` | | | | | | ✓ |
| `equipment:purge_documents` | | | | | ✓ | ✓ |
| `breakdown:raise` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `breakdown:work` | | | ✓ | ✓ | ✓ | |
| `breakdown:close` | | | | ✓ | ✓ | |
| `pm_plan:edit` | | | | ✓ | ✓ | |
| `pm_job:work` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `pm_job:verify` | | | | ✓ | ✓ | |
| `reading:log` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `report:read` | | | | ✓ | ✓ | |
| `settings:edit` | | | | | | ✓ |
| `access_log:view` | | | | | ✓ | ✓ |
| `people:edit` | | | | ✓ | ✓ | ✓ |
| `people:assign_technicians` | | | | ✓ | ✓ | ✓ |

Site-scoped keys (`config_rbac.SITE_SCOPED`: `equipment:read`, `equipment:edit`,
`equipment:purge_documents`, `people:assign_technicians`, and every later breakdown,
PM, reading and report key) are checked at the record's site; the others are global.
`masters:edit` (decided 13-10-2026) covers sites and units, and every site role above
Technician — IT admin only. `masters:read_senior` (IT admin) is needed to see logins
and the site roles of people with a login;
engineers may be added in phase 3, when they assign work. `equipment:edit` covers equipment classes and equipment — engineers
(and so the manager) and IT admin. `equipment:read_all_units` (decided 14-10-2026, S002) is a
*scope* key: its holders see equipment at every unit; everyone else sees only the
units in their unit access. `equipment:purge_documents` (decided 16-10-2026, S008) —
manager and IT admin — lists removed documents and restores or deletes them for
good; erasing is kept apart from the everyday remove (ISO 27001 A.5.3, A.8.2).
`people:edit` (S010 A1) maintains the Team register and the trades — engineers (and
so the manager) and IT admin. A person's login, and deactivating or reactivating a
person who has one, need `masters:edit` too (IT admin), since a login turns roles
into access (ISO 27001 A.5.3, A.8.2); nobody sets their own login.
`people:assign_technicians` (S011 A1, gate A) — engineers (and so the manager) and IT
admin, checked per site — adds, changes or removes **Technician** rows at that site for
any person; roles above Technician stay IT admin's (ISO 27001 A.5.18 lets the
information owner grant, A.8.2 least privilege). Engineers see a person's site rows
when the person has no login, and of a person with a login only the rows at their
own sites.

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
  nameplate details in the remarks (superseded by the parts-used line of § 4.2 if adopted). **When built:** only a short list is tracked
  (e.g. motors above a kW threshold, gearboxes, hydraulic pumps); identity is our
  own code on a riveted or engraved metal tag with QR; the nameplate serial and
  data (kW, rpm, frame, mounting, make) are attributes, used to find
  interchangeable spares. The tree already gives components codes, so nothing in
  v1 needs redoing.
- **Dies and mould boxes brought forward** (*Proposed*, 16-10-2026, pressing-shop use case).
  A press's top die, bottom die and mould box carry serial numbers and move between presses,
  and bottom dies go to the machine shop for surface grinding. They are **components** under
  the press with their own codes; a move is a re-parent, already logged by S002. Two small
  additions give die history without the full rotables design: (a) a fit or removal records the
  press's stroke counter at that moment (a reading with source `move`), so strokes per press and
  lifetime strokes per die follow from the readings; (b) a history view centred on the die: fits,
  strokes, grinds, remaining thickness (a reading item on the grinding job). ISO 14224 tracks
  maintainable items by serial across installations; TPM names die and jig management as part
  of planned maintenance. The position-versus-item split still waits for spares.
- **Press tree** (16-10-2026): presses are modelled to component level from the start, since
  tickets and procedures point at components: power pack (pump and its radial piston elements,
  motor, unloading / relief / proportional valves, return filter, suction strainer), cylinders,
  controls (PLC, pressure transducer, relay board), safety door (pneumatic cylinder, magnetic
  sensor). The **safety-door component-unit is graded A** on every press: criticality A covers
  safety risk, so its tickets outrank production tickets and escalate faster; no new flag.
- **Fields:** code, name, **model** (required on every node; it gives the equipment class and type — decided 17-10-2026, S012), serial number, year, maintenance strategy (*Proposed*, above), criticality (A/B/C; required on equipment, default C; component-units and components inherit unless graded), status (in service / standby / out of use / scrapped — scrapped is final and read-only), unit. Only equipment has a unit; its parts follow it (decided 14-10-2026, S002). Which machine backs up which (a standby relationship) is not recorded. Notes: free text for reading, searchable, not in the history (S004).
- **Equipment class:** what a piece of equipment *is* (hydraulic press, ball mill, kiln fan, …), a list maintained by engineers. Used to pick equipment when applying a PM template, to compare MTBF/downtime across equipment of a kind, and (if failure codes are adopted) to scope code lists. No class-specific custom fields in v1. A class is a **kind**, not a container like sites and units: the same class is used at any level of the tree — a blower is a component-unit in one machine and a stand-alone machine elsewhere — so "all compressors in the plant" is one class across every level (clarified by the user 16-10-2026). So a class has no level of its own; a level shown for a class is derived from where it is used.
- **Equipment type** (decided 15-10-2026, S004): how equipment of a class is built, e.g. `RPP` → closed / open execution (ISO 14224 class → type). Types are defined per class, maintained by engineers; an equipment's type must belong to its class.
- **Sites and units:** sites (SMTW, BRICKS, SSVT, the farms, …) are created in Yantra. Each site has units — its areas and shop floors — coded `SITE.UNIT` (e.g. `SMTW.KILN`, `SSVT.SHOP`). A unit can be mapped to a OneERP warehouse code. Until the sync exists, units are maintained by hand.
- **Codes frozen once in use** (decided 13-10-2026, S001). A site, unit or equipment-class
  code — and a unit's site — can be corrected only while nothing references the record
  (site: has units; unit: has users' unit access or, later, equipment; class: has
  equipment). After that it is frozen. For class codes this protects equipment codes,
  which embed the prefix. For sites and units it is change control (ISO 55001): OneERP
  warehouse names, printed lists and history snapshots follow the codes. Master records
  are deactivated, never deleted.
- **Documents:** manuals, drawings, photos attached to a piece of equipment (S006). Not on equipment classes or types: a class or type mixes products of different makers, so manufacturer documentation belongs to the equipment **model** (decided 16-10-2026; S009 dropped). Model documents are uploaded once in Masters › Models and shown read-only on every equipment of that model, at every site (S012).
- **Maintenance strategy** (*Proposed*, 16-10-2026, forgotten-machines use case): a field on
  equipment — *planned*, *run-to-failure*, *not decided* (the default for new equipment). EN
  13306 lists run-to-failure as a legitimate strategy and RCM picks it where a failure costs
  little, which is most grade C equipment; the fault is when nobody chose it (an electric wood
  cutting machine went unused and forgotten for years). ISO 55001 § 7.5: know what you have
  and what you decided for it. The dashboard lists the not-decided equipment until an engineer
  chooses. One enum, no logic.
- **Verification rounds** (*Proposed*, 16-10-2026): a job per unit where someone walks the
  floor scanning QR labels; scanned equipment are confirmed, unscanned listed as not found,
  unregistered machines found on the walk are added. ISO 55002 recommends periodic physical
  verification (the accounting fixed-asset audit is the same walk). Cheap: labels and unit
  lists exist.
- **Document kinds** (*Proposed*, 16-10-2026, pressing-shop use case): a document's kind
  becomes a short pick-list — hydraulic diagram, electrical diagram, manual, parts list,
  certificate, photo, other — instead of document / photo. Then a **missing-drawings list**
  (equipment of a class with no document of a kind) turns "where is the circuit diagram" into
  a list to work down. EN 13460 names the documents a maintainer should hold per equipment;
  ISO 55001 § 7.5 asks the organisation to decide what asset information it needs and keep it.
  Presses designed in house get an in-house **model** (e.g. `SMTW-HYP-01`) holding the design
  drawings (S012); drawings of a later alteration to one press stay on that **equipment**;
  a photographed sketch counts. Replacing a drawing is remove then attach; the removed file
  stays (S008), which is enough version control.
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
- **Production marks "back in service" too** (decided 16-10-2026, sorting-line use case): the
  supervisor, or whoever has operator rights at the unit, can record "back in service" and
  name the technician who did the work from Team. Standard CMMS requester sign-off: production
  confirms the restoration (EN 13306), which is where the SMRP repair time ends. Needed because
  technicians on the floor may have no phone. *Proposed:* the same person may record
  "technician arrived" (→ in progress) so repair time starts when work starts, not at dispatch.
- **Event time is entered, not implied** (decided 16-10-2026): every transition recorded after
  the fact carries a "when" the user enters, defaulting to now. ISO 14224 counts failure and
  restoration by event time, so a supervisor typing at the end of the shift still gives correct
  downtime and MTTR.
- **Reported by** (*Proposed*): the operator who found the fault, picked from Team, kept apart
  from who raised the ticket (the supervisor). Keeps operator ownership visible (TPM).
- **Deferred work** (*Proposed*, 16-10-2026, extrusion-line use case). Much work is requested
  while the machine runs and done later, once parts are bought or fabricated and a slot is
  found: a touchscreen to replace, worn scrapers, a liner "good for another 1,000 hours", a
  filter the AMC vendor asked for. EN 13306 calls this *deferred corrective maintenance*;
  SMRP measures planned against reactive work. Design to settle in the phase 3 brief:
  - a **scheduled** state between acknowledged and in progress, set by the engineer with a
    planned date and a waiting reason (parts, shutdown slot, vendor);
  - a target **by meter value** as well as by date ("at 1,000 run hours from now"), reusing
    the meter-trigger machinery of PM plans, so the ticket falls due when the reading crosses it;
  - the stop taken for a scheduled ticket is **planned downtime**, reported apart from
    breakdown downtime (EN 13306, SMRP; OEE treats them differently);
  - a waiting reason also on a **critical** ticket (parts, vendor, workshop, expert), so
    downtime splits into active repair and waiting (EN 13306: active maintenance time,
    logistic delay, administrative delay). A press cylinder three weeks at the maker is waiting.
- **Diagnostic procedures** (*Proposed*, 16-10-2026, pressing-shop use case). Fault diagnosis
  on the hydraulic presses depends on one person, guided over the phone test by test. EN 13306
  names fault diagnosis as a step of corrective maintenance; TPM's training pillar writes expert
  knowledge down as one-point lessons. Yantra should hold a **procedure per symptom** for an
  equipment class ("not building pressure": test 1 run the pump against the closed relief and
  record the gauge; test 2 command 100 bar and record transducer and gauge; …), each step a
  checklist or reading item like a PM plan's. The engineer attaches it to the ticket, runs it on
  site and types the readings; the expert reads them on the ticket timeline and answers there.
  Reuses the PM item machinery. The highest-value addition from the use cases.
- **Failure-mode lists scoped by class** are brought forward for the press class (16-10-2026):
  "not building pressure", "not holding pressure", "slow return", "door not sensed", "output
  stuck on", … Tickets point at the **component** (unloading valve, transducer, relay board,
  door sensor), so chronic problems are visible per component (§ 4.6).
- **Intensity** (the TPM red tag is this ticket): the operator grades the problem. Scale (decided 15-10-2026), from ISO 14224's failure impact: **critical** (equipment stopped), **degraded** (running with reduced function), **initial** (still fine, early signs; ISO 14224 calls it *incipient*). Only critical time counts as downtime.
- **Codes** (ISO 14224 core, decided 15-10-2026): failure mode (the operator picks it as the symptom), failure cause and maintenance action (technician/engineer pick). Lists trimmed from ISO 14224 Annex B, maintained by engineers. Mechanism not in v1; detection method automatic (below).
- **No approval step:** a raised ticket goes straight to maintenance. If it turns out frivolous, the engineer **closes it directly** from raised or acknowledged, with a required code (e.g. *no fault found*, *not a breakdown*) and remarks.
- **Parts used** (*Proposed*, 17-10-2026, parts use case): a structured line on tickets and
  PM jobs — part number, description, quantity, maker if any — replacing "action *replaced* plus
  nameplate details in the remarks". No stock, no cost. The number is either a **maker's part
  number** (from a Haendle drawing, or from the quote of a service engineer whose maker gives no
  parts list) or a **generic designation** (bearing `6205-2RS`, a valve or filter element by
  standard spec), since many press spares are bought generic. The line sits on the ticket's
  **component**, so a part lands against the thing it fits; the vendor's quote and findings
  attach to the ticket. Over time this builds the parts list the maker never gave, and seeds
  each model's bill of materials when spares come. ISO 14224 lists parts replaced among the
  maintenance-record fields. Ordering and the item master stay in **OneERP** (ISO 8000: one
  item master); a later link maps Yantra part numbers to OneERP item codes.
- **Who worked:** one or more technicians per ticket, with time spent. Each labour row carries the **trade worked** (pre-filled when the technician has only one), so man-hours per discipline (ISO 14224 Table 8) can be summed (S010, 16-10-2026).
- **Work done without a ticket** (*Proposed*, 18-10-2026, daily-report use case): work that
  walks into the workshop (a portable vibrator needing new carbon brushes) gets its ticket after
  the fact, on one screen where an engineer or supervisor raises and closes it in one go: event
  times, the technician named, cause and action, parts used. The record matters more than the
  workflow (ISO 14224 wants every maintenance event recorded, whoever asked for it).
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
- **Performer:** maintenance (team or technician, the default for generated jobs) or operator (CIL plans). An **AMC vendor** is a contractor record in Team and can be the plan's assignee (16-10-2026); the engineer verifies the job with the vendor's report attached. Calibration of instruments (e.g. the moisture analyser) is an ordinary calendar plan with the certificate attached (ISO 9001 § 7.1.5 wants calibration records with due dates).
- **Both triggers, whichever first** (16-10-2026): standby equipment gathers hours slowly, so its plans use calendar and meter together, as OEM schedules are written.
- **Fitness-for-use inspection** (*Proposed*, 16-10-2026): a PM template applied to every
  class, performer the engineer, calendar (e.g. yearly), with a checklist and an outcome — fit /
  fit with conditions / not fit; "not fit" sets the equipment out of use. Gives every machine,
  run-to-failure ones included, a periodic look. Self-verification allowed for this plan kind
  (the engineer does and signs). Statutory examinations (the Factories Act requires periodic
  examination of pressure plant, hoists and lifting machines by a competent person — the
  compressors' air receivers are pressure plant; confirm with whoever handles safety) are the
  same plan with the certificate attached.
- **Certification plans** (*Proposed*, 17-10-2026, statutory use case): a plan flagged
  *certification* carries a **valid-until** date on each job, with the certificate attached.
  The dashboard lists certificates expiring within 30 days or expired; a **compliance register**
  report (equipment, last certificate, valid until, by whom) is the evidence an inspector or
  insurer asks for (ISO 55001 § 6.2 and ISO 45001 § 6.1.3: identify legal requirements and show
  compliance). Covers the Factories Act examinations by a competent person — lifts and hoists
  at least every six months, lifting machines (EOT cranes) at least every twelve, pressure
  plant at the intervals in the state rules, examined by the government inspector against a
  fee — and conveyors, which may be an insurer's or internal requirement (to confirm). The
  performer is a contractor in Team or the inspector recorded the same way. The fee is a cost,
  not tracked in v1; its receipt is attached as a document.
- **Needs-verification flag per plan** (*Proposed*, 17-10-2026): default yes for maintenance
  work, no for routine checks (a quarterly extinguisher check) and CIL. Settles open question 10.
- **Fire extinguishers** (17-10-2026): equipment with a code and QR label, class *fire
  extinguisher*, types CO2 / dry powder / foam / water, grade A. One PM template per type,
  applied by type: quarterly check (scan the label, checklist — gauge in green, seal intact,
  hose sound, accessible, signage — done), yearly refill, pressure test, replacement.
  Intervals per **IS 2190**, the Indian standard for portable extinguishers; the user's figures
  (yearly refill; replace at 3 or 5 years by type) are to be checked against it when the
  templates are written. Replacement is a calendar plan with its first due date set by hand
  to the end of life; on completion the old unit is scrapped and the new one registered.
- **PM routes** (*Proposed*, 18-10-2026, daily-report use case): one walk, many stops. The
  fitter's daily genset round (fuel level, leaks, battery, runs properly) and the electrical
  team's daily EB meter readings are inspections (EN 13306: a check for conformity, no repair)
  over many pieces of equipment; one job per equipment would give each man ten jobs a day.
  Every CMMS has a **PM route** for this (SMRP: inspection or lubrication route). Proposed
  shape: the jobs stay one per equipment in the data (ISO 14224 records per equipment; the
  history card stays simple), and a route is a named **grouping and a screen**: the plans it
  covers in walking order, one performer, one "all OK" tap per stop, readings typed inline, a
  stop left undone stays due. The verification round (§ 4.1), the proposed "CIL due today at
  my units" list (§ 4.4), the genset round, the EB walk, the packing-machine blow-down and the
  quarterly extinguisher check all become routes, so no third special case is built. Genset
  plans follow the OEM schedule (daily visual, periodic test run, battery, oil by hours); the
  calendar-and-meter rule above fits them, as standby sets gather hours slowly.
- **Which meter a plan uses** (*Proposed*, 16-10-2026): no inheritance logic. A meter trigger
  names one meter, and the picker offers the node's own meters and its ancestors'. A gearbox
  plan picks the extruder's run hours; an alternating pump with its own hour meter picks its own.
  ISO 14224: record run hours at the level where they differ.
- **Rescheduling** (*Proposed*, 16-10-2026): the engineer may push a due job to a new date or meter value with a reason kept on the job (e.g. oil change extended after a good oil analysis). Settles the philosophy doc's "may a PM be skipped and by whom"; SMRP tracks it as PM rescheduled.

**PM job** (generated from a plan):

```
due ──► in progress ──► done ──► verified
        (technician)    (technician)  (engineer)
                                └─ engineer can send back to "in progress"
```

- The technician fills checklist, readings and photos on the phone.
- **Recorded on behalf** (decided 18-10-2026, daily-report use case): a technician without a
  phone (the fitter on the genset round) is paired with a supervisor or engineer, who records
  the job naming the technician as *performed by* and entering the time, as for CIL (§ 4.4).
- A reading outside its limits is flagged on the job; the technician can raise a breakdown ticket from it in one tap.
- Overdue jobs show on dashboards and are notified.
- Serial: `PM-YYYY-MM-NNN`.

### 4.3a Procedures (*Proposed*, 16-10-2026)

One master for written know-how, instead of a wiki: how to clean a press, how to change pump
elements, how to diagnose "not building pressure". TPM calls these **one-point lessons** and
standard work; a CMMS calls them job plans. Knowledge kept away from the equipment and the
ticket is knowledge nobody opens at the press, so a procedure shows on the equipment page (via
its class), on the PM template it explains, and on the ticket it is attached to.

- **Fields:** title, kind (work instruction / diagnostic / one-point lesson / onboarding),
  optional equipment class, a Markdown body with attached photos, optional numbered **steps**
  as checklist and reading items (the PM item shape), who changed it and when (ISO 9001 § 7.5
  control of documented information). Edited by engineers.
- **Onboarding** (16-10-2026): dos and don'ts of a machine or tool, shown one card at a time
  (picture + short text) on the phone or kiosk before first use, written in **Tamil** (the DB is
  utf8mb4, so content is Tamil today while the UI stays English). A **completion record** —
  person, procedure, equipment or class, date, recorded by the supervisor or by the operator at
  the kiosk — is the seed of the skill matrix (TPM training pillar; ISO 45001 § 7.2 competence).
  Blocking CIL for an untrained operator can come later, once records exist.
- **Used from:** PM templates (the "how" behind a checklist), tickets (the diagnostic case —
  open question 15 is a procedure of kind *diagnostic* with steps), the equipment page.
- Past jobs keep their own copy of the items, so editing a procedure never rewrites history.
- Rejected: a separate wiki (knowledge split from the equipment); per-equipment notes (not
  reusable across a class).

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
- **Recorded on behalf** (16-10-2026, sorting-line use case): where operators have no phone,
  the check is done from the paper CIL sheet at the machine (the TPM autonomous-maintenance
  check sheet, visual management) and the supervisor records it in Yantra, naming the
  operator from Team as **performed by** and entering the time (event time, as for tickets).
  *Proposed:* a "CIL due today at my units" list with one tap per machine, so a supervisor
  with six machines does not scan six QR codes.
- Whether CIL jobs need engineer verification is open question 10.
- **Missed checks:** frequency-based CIL shows overdue like any PM job. Missed
  *before-use* checks are not detected in v1 — that needs evidence the equipment
  ran (production counts, later).

### 4.5 Meters and readings

- A piece of equipment has meters: run hours, production count, or a measured quantity (oil temperature, roller clearance, vibration, wear mm). Each meter has a unit of measure and a type: **counter** (only goes up; triggers every N units) or **gauge** (a level; triggers on crossing limits).
- Readings are entered by hand — from a "log reading" screen (via the equipment's QR) or as part of a PM job. A reading carries the time it was **taken**, entered by the user and defaulting to now (16-10-2026): operators read run hours off the HMI into a notebook and type them in at the end of the day.
- **Press end-of-day meters** (16-10-2026): strokes and run hours (counters), energy meter kWh
  (counter; kWh per stroke later is the energy performance indicator of ISO 50001), maximum
  power-pack oil temperature of the day (gauge with a limit).
- **Hydraulic oil cleanliness** (16-10-2026): an **ISO 4406** cleanliness code per press as a
  gauge meter with a target by the most sensitive component (proportional valves need cleaner
  oil than plain spool valves), fed by a sampling PM plan. Over the limit raises the offline
  filtration job, condition-based, with a measured before and after. Return filters are changed
  on the clogging indicator, not the calendar. Most hydraulic failures trace to contamination.
- **Lab results are readings** (16-10-2026): an oil analysis is a PM plan "take sample", with the lab's values (silicon, water, viscosity, …) entered as gauge readings on the job, each with a limit, and the report attached. A value over limit raises a ticket with detection method *condition monitoring*. Classic condition-based maintenance (EN 13306).
- **EB incomers and gensets** (18-10-2026, daily-report use case): each electricity-board
  incoming connection is equipment (class *EB supply*) with a kWh counter meter read daily by
  the electrical team; gensets carry run hours (counter) and fuel level (gauge) read on the
  daily round. Daily kWh per site is the first energy figure ISO 50001 asks for.
- A counter reading lower than the previous one is rejected unless marked as a meter reset.
- Each reading stores its source (`manual` now; `iiot` later), so an automatic feed can be added without changing the model.

### 4.6 History and reports

- **Equipment history card:** all breakdowns, PM jobs and readings of a piece of equipment, newest first.
- **Downtime:** per equipment / unit / cause code, per period.
- **MTBF / MTTR** per equipment and unit.
- **PM compliance:** jobs due vs. done on time vs. overdue, per unit and plan.
- **Compliance register** (*Proposed*, 17-10-2026): certificates per equipment — last, valid until, by whom; expiring and expired (§ 4.3).
- **Reading trends:** a chart per meter, with its limits drawn in.
- **Chronic problems** (16-10-2026, pressing shop): tickets by component and failure mode per
  equipment over a period, with downtime. Shows "press 7, door not sensed, nine tickets in six
  months" or the welded-relay count that justifies converting to solid-state relays. TPM
  focused improvement, brought forward for the presses.
- **Daily work log** (decided 18-10-2026, daily-report use case): everything recorded for a
  day — tickets moved, PM and route jobs done, readings taken — per site, team and person,
  with planned against reactive work (SMRP). **Printed from Yantra**, it replaces the
  electrical head's handwritten daily report; odd jobs and new installations are written by
  hand on the printout, not entered (§ 2, Not in v1). The report is generated from the
  records, never written a second time.
- **Waiting versus repair:** downtime split by waiting reason (§ 4.2).
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
| Daily summary (open tickets, overdue PMs, yesterday's downtime and work done) | | | engineers, manager |

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
| `equipment` | Register fields, `level` (equipment / component-unit / component), `parent_id` for the tree, `unit_id` (equipment only), `model_id` (required), `class_id` and `type_id` (copied from the model, S012) |
| `manufacturers` | Makers: name (unique without regard to case), active (S012). Generic and in-house makers are ordinary rows |
| `equipment_models` | Manufacturer, designation (unique per maker), class, optional type of that class — all but the designation fixed after creation; active (S012) |
| `equipment_events` | Equipment history: one row per move or change of status, criticality or class — old → new, who, when (S002) |
| `memberships` | Person → site: the person's one role at that site, and "all units" (S011 A1) |
| `person_units` | Person → unit: the units within a site where the person has a membership without "all units" (S011 A1) |
| `user_units` | Legacy (S001): username → unit. Copied to `person_units` by migration v8 and no longer used; kept for a rollback, dropped by a later step |
| `trades` | Trades (electrician, fitter, tool maker, …), kept in the UI (S010) |
| `people` | The Team register: one record per person, or per contractor firm (the user's choice): name, employment (direct / contractor), optional Yantra login set by IT admin, active (S010 A1) |
| `person_trades` | Person → trades, none or more (S010 A1) |
| `procedures` | *Proposed* (§ 4.3a): title, kind, optional class, Markdown body, steps as items, attachments |
| `procedure_completions` | *Proposed* (§ 4.3a): person, procedure, equipment or class, date, recorded by — onboarding done |
| `verification_rounds`, `verification_items` | *Proposed* (§ 4.1): a walk per unit; per equipment confirmed / not found, who, when |
| `pm_routes`, `pm_route_plans` | *Proposed* (§ 4.3): a named walk — performer, the plans it covers in order; jobs stay one per equipment |
| `equipment_documents` | Files attached to equipment or to an equipment model (exactly one owner, S012): kind (document / photo; a pick-list of kinds is proposed, § 4.1), title (editable), original name, system-generated stored name, type, size, thumbnail flag; created / updated / removed who and when — removal hides, the file stays (S006); a removed document is restored or deleted for good (row and file, logged) by the manager or IT admin from Settings (S008) |
| `codes` | Symptom / cause / action pick-lists (`kind`, code, label, active) |
| `breakdowns` | Ticket: equipment, state, intensity, codes, remarks, serial |
| `breakdown_events` | One row per state change: who, when, remark — the timestamps come from here |
| `breakdown_labour` | Person, trade worked and time spent per ticket |
| `parts_used` | *Proposed* (§ 4.2): per ticket or PM job — part number, description, quantity, maker, component |
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
| `access_log` | One row per sighting of a login session from an address, or a refusal (S013); kept 365 days |
| `task_queue` | Base pattern: notifications, PM generation, sync; first task the daily access-log purge (S013) |
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
3. **Breakdowns** — the full ticket flow, codes, labour, photos, Telegram + web push for new tickets and escalation. First module the shop floor uses. *Proposed* (16-10-2026): the **pressing shops** (SMTW and SSVT) as the pilot, since press availability is the plant's worst loss and its diagnosis bottleneck is what the diagnostic procedures address.
4. **Meters, PM and CIL** — meters and readings, PM templates and plans with checklists and readings, calendar / meter / before-use triggers, PM and CIL jobs, verification.
5. **History, reports, daily email** — history card, downtime, MTBF/MTTR, PM compliance, reading trends, Excel export, daily summary.
6. **OneERP warehouse sync** — unit mapping from OneERP (can move earlier if wanted; it is independent).

## 9. Open questions

1. ~~**Keycloak roles:** realm or client roles?~~ Decided 12-10-2026: client roles of `vel-yantra-master` (`maint_operator`, `maint_technician`, `maint_engineer`, `maint_manager`, `maint_storekeeper`, `it_admin`). **Superseded 16-10-2026 (S011):** Keycloak keeps `maintenance_team` and `it_admin`; the maintenance roles are held in Yantra per site.
2. **Escalation times:** how long before an unacknowledged breakdown escalates, per criticality? *Deferred 15-10-2026: decided with the notification step (Telegram / web push); stored as settings, not code.*
3. ~~**Equipment codes**~~ Decided 13-10-2026: class prefix of 2–4 letters + 3-digit number (`VBM001`), growing to 4 digits past 999; one counter per prefix across all sites, so a code survives a move.
4. ~~**Downtime definition**~~ Decided 15-10-2026: downtime ends at the technician's **"back in service"** (SMRP: repair time runs to restoration). Whether the operator can mark "not fixed" to reopen the ticket is settled with the phase 3 brief.
5. ~~**Failure coding**~~ Decided 15-10-2026: the **ISO 14224 core** — failure **mode** (the operator picks it as the symptom), failure **cause** and maintenance **action** (technician/engineer), with lists trimmed from ISO 14224 Annex B and maintained by engineers. Mechanism is left out for now; detection method is filled automatically from the ticket's source (§ 4.2). Mode lists may later be scoped by equipment class.
6. **Template edits:** when a PM template changes, do plans created from it update, or keep their copy until re-applied?
7. ~~**Unit access upkeep**~~ Decided 13-10-2026: IT admin maintains users' unit lists (and sites and units) — `masters:edit`.
8. ~~**CIL shifts**~~ Superseded: CIL is per equipment, before use or by frequency (§ 4.4); missed before-use detection is deferred.
9. ~~**Intensity scale**~~ Decided 15-10-2026: **critical / degraded / initial** — ISO 14224's failure impact, with the plain word *initial* for the standard's *incipient*.
10. **CIL verification:** does an engineer verify CIL jobs, or are they done when the operator submits? *Proposed 17-10-2026:* a needs-verification flag per plan, default no for CIL and routine checks (§ 4.3).
12. **Closing discipline** (*Proposed*, 16-10-2026): the engineer codes cause and action from the technician's verbal report after the fact. TPM practice is to close within the shift; tickets back in service but not closed by end of shift should show on the engineer's dashboard. No extra approval step.
13. **Deferred work** (*Proposed*, 16-10-2026, § 4.2): scheduled state, meter-value targets, planned downtime. To settle in the phase 3 brief.
14. **PM rescheduling** (*Proposed*, 16-10-2026, § 4.3): engineer pushes a due job with a reason.
15. **Diagnostic procedures on tickets** (*Proposed*, 16-10-2026, § 4.2): per class and symptom, steps as checklist and reading items. Which phase: with breakdowns (3) or with PM items (4)? Folded into the **Procedures** master (§ 4.3a) as kind *diagnostic*.
17. **Document kinds and missing-drawings list** (*Proposed*, 16-10-2026, § 4.1): a small change to S006; which step carries it?
18. **Maintenance strategy field, fitness-for-use inspection, verification rounds** (*Proposed*, 16-10-2026, § 4.1, § 4.3): the answer to forgotten machines.
19. **Onboarding procedures and completion records** (*Proposed*, 16-10-2026, § 4.3a).
20. **Certification plans with valid-until and the compliance register** (*Proposed*, 17-10-2026, § 4.3): statutory examinations and extinguishers.
21. **Parts-used line on tickets and jobs** (*Proposed*, 17-10-2026, § 4.2): maker or generic part numbers, per component, ahead of spares.
22. **PM routes** (*Proposed*, 18-10-2026, § 4.3): one screen for a walk over many equipment; verification rounds and the CIL-due list fold into it. Which step builds it?
23. **Work done without a ticket** (*Proposed*, 18-10-2026, § 4.2): raise-and-close on one screen for work that arrived with no ticket.
16. **Die tracking** (*Proposed*, 16-10-2026, § 4.1): counter snapshot on fit / removal and a die-centred history, ahead of the rotables design.
11. ~~**Kiosks.**~~ Decided 13-10-2026: not in v1; not tied to a unit; operators are Keycloak local users with passwords; logout manual or on inactivity; no supervisor role (superseded 16-10-2026 by S011 A1: `maint_supervisor`, production-side); resets by IT in Keycloak (Decisions table, § 3).
