# Yantra — Plan (v1)

Yantra is a computerised maintenance management system (CMMS) for VEL's plants.
Operators report breakdowns and defects and log equipment readings from their phones; the
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
| Security hardening | Roadmap R01 (gate R, 26-10-2026; `docs/roadmap/R01-auth-hardening.md`). **Every API route declares its permission check** (`@require_perm`, "checked in route" with a reason, or "public" with a reason); a route with no declaration is refused (fail-closed, OWASP ASVS V8 deny by default). **Every Keycloak role is a network-gate decision**: plant network only, or allowed from outside with a dated reason (a test enforces it). A failed sign-in renewal after a network drop **keeps the page and its typing**; after a real end of session, *Sign in again* discards it. Raise ticket and the Readings sheet ask "Discard your changes?" before you leave; Settings does not. Database details in Settings › Database are for **IT admin only**. A **Content Security Policy** is enforced from its release, checked right after the deploy. **Sign-in tokens** (S059, R01.2): only RS256, the issuer must be the public realm URL, `exp`, `iat` and `iss` are required (30 s clock allowance), the token type must be `Bearer`; no retry on a bad token (PyJWT re-fetches keys itself, 5 s limit); Keycloak down answers 503 "Sign-in cannot be checked right now", logged as a failed sign-in with reason `login_server_down`. Dev servers listen on 127.0.0.1 (a "Frontend (LAN)" run config for phone checks). Uploads up to 100 MB pass the front proxy (101 MB there, devops). **Access changes are log lines, not a table**: KLA will ship the logs to Loki, whose retention sets how far back an access review can look (ISO 27001 A.5.18, A.8.15). |
| Preventive maintenance | Roadmap R03 (gate R, 27-10-2026; `docs/roadmap/R03-pm.md`), 17 items in three milestones; all 20 answers at the recommendation. **Scheduling:** a job is on time when done within 10 % of its interval (at least 1 day); a meter plan's next job counts from the reading when last done, plus the interval; one open job per plan, shown as *Upcoming* a little before it is due; meter-triggered jobs appear in the daily run; a job nobody does stays overdue until done or skipped; a rescheduled job is on time against its new date, and reschedules are counted; an engineer may skip a due job with a reason, and it counts as not done. **Items:** § 4.3's Task / Check / Reading, a photo setting per item. **Sign-off:** verification is a flag per plan (default yes for maintenance, no for CIL); an engineer may verify a job they did, recorded. **Findings:** at *Mark job done* each Not OK item without a ticket asks *Raise defect ticket* or *No ticket* with a remark (a departure from § 4.3 / § 4.4's optional "can raise"). **Templates:** plans keep a copy; *Update plans* sends a change to the plans the engineer ticks. **Other:** IT admin reads PM only (new key `pm_job:read`); the overdue alert goes to the assignee and the unit's engineers; labour minutes and parts on PM jobs; CIL is in R03; the genset round pilots routes (not the fleet); the hydraulic presses pilot PM; ticket targets by meter value in R03; certification, calibration, fitness-for-use and extinguishers go to a follow-on roadmap R04, after R03.8. |
| Improvement (RCA) | Roadmap R05 (gate R, 30-10-2026; `docs/roadmap/R05-rca.md`), from closed ticket TK-2026-10-002 (a dusty contactor). TPM focused improvement with why-why; ISO 9001 § 10.2. Items R05.1–R05.6 and R05.10 are built now, before R03's milestone 1; R05.7 (who was shown a lesson), R05.8 (*Suggested* improvements) and R05.9 (a countermeasure becomes a PM plan) are deferred. All other answers at the recommendation. **Record:** *Improvement*, serial `IM-YYYY-MM-NNN`, started by an engineer from one or more tickets that are back in service or closed; a ticket is in at most one open improvement; a tab *Improvements* on the Tickets page, no new nav item. **Keys** (site-scoped): `improvement:read` operator and up and IT admin (read only); `improvement:edit` engineers and managers; notes for every reader; `improvement:verify` engineers and managers, the lead too (recorded; a departure from ISO 27001 A.5.3). **Analysis:** one why-why chain with optional evidence; the root cause is a text plus one cause from the failure-cause list, required before *Watching*; the closed ticket's cause is never changed. **Countermeasures:** six kinds (Correction, Corrective, Preventive, Design-out, Lesson, Spread); an owner with a membership at the site, a person without a login too. **Verified close:** a watch of 90 days (30–365, per improvement) from the last countermeasure done; a repeat during the watch shows a warning, the verifier decides. **Alerts:** push only (given to you, overdue, ready to verify). **Lessons:** one-point lessons as the first kind of the Procedures master, on the machine and, when ticked, its class; written by engineers and managers. **Register:** printable, in R05. |
| Standards | **ISO 9001 certification is a future goal; Yantra is built to be compliant and to nudge the plant towards it** (decided 20-10-2026). The clauses that touch maintenance and measurement, and where Yantra serves them: **§ 7.1.3** infrastructure is maintained (equipment register, PM); **§ 7.1.5** monitoring and measuring resources (calibration, § 4.3); **§ 7.5** documented information (who changed what and when; retention); **§ 8.5.1** production under controlled conditions (suitable equipment and instruments); **§ 9.1** monitoring and measurement (KPIs, § 4.6); **§ 10.2** nonconformity and corrective action (tickets with cause and action codes). Each brief names the clause it serves, as it already does for ISO 14224 and ISO 55001. |
| Schema and releases | **One squashed migration v20** replaces v1–v13 (S025, decided 21-10-2026; production was on v0.1.3 with masters only and is the one instance); later migrations continue from v21. A release is verified by the deploy: `/api/health` must report `schema_ready` within 3 minutes, else the deploy fails with the rollback lines. A backup before every deploy and guards for migrations that touch existing data are queued (*Safe migrations*). |
| Files | Photos and documents on disk under `data/`, which is an **App-FS** NFS export mounted into the container (like OneERP's files). No MinIO. |
| Repos | App code and docs here. Deployment in `smtw_erp_devops/erp_server/yantra/`, run with `erp_spanner.py <org> yantra <instance>` (like `erp_server/delivery`), so another org or a `test` instance is just a host file + settings file. |

## 2. Scope

### In v1

1. **Equipment register** — equipment and its component-units and components, equipment class, unit, documents, QR label.
2. **Tickets: breakdowns and defects** (maintenance requests that become work orders) — raised on the shop floor, worked by maintenance, closed by the engineer, with downtime timestamps and cause/action codes.
3. **Preventive maintenance (PM)** — PM templates applied to equipment; plans with checklists and readings, triggered by calendar or by meter; jobs filled on the phone with photos; engineer sign-off.
4. **CIL** (clean / inspect / lubricate) — operator checks, defined per equipment as part of its maintenance plan (§ 4.4).
5. **Meter readings** — manual entry on the phone.
6. **History and reports** — equipment history card, downtime, MTBF/MTTR, PM compliance.
7. **Notifications** — web push, Telegram, email.
8. **Me** (S031, 23-10-2026) — one page per person, a nav item, first in the nav since S035 (24-10-2026), three tabs: *Open work* (open tickets assigned to me), *Raised by me* (tickets I raised or that name me as the reporter) and *My activity* (timeline lines I recorded). Read-only. Not on it: time booked, another person's work (a team report, later), notifications (they stay under the bell). The landing page for every role with `ticket:read` (S035, 24-10-2026; it was Equipment until then); the storekeeper still lands on Equipment.
9. **Maintenance contracts** (roadmap R02, gate R 27-10-2026) — a register of vendor contracts (Warranty, AMC, CMC, On call), one site per contract: vendor (one Team record per firm, employment *contractor*), period, the equipment nodes covered (any level; two contracts on one node allowed, a warning when two of one type overlap), what is covered (ticks: labour, spare parts, consumables, breakdown calls; plus free text *Covered* / *Not covered*), PM visits agreed per year, response time, a call-out number (shown on the contract and the machine card to engineers, managers and admin; `contract:read`), an *Only the vendor may repair* tick (the card then warns "Do not repair"), a price per machine before GST (the total is their sum) and a cost note. One coverage per contract: a vendor quote that mixes coverages is entered as two contracts. A *Contracts* tab in Masters. Keys: `contract:read_basic` (the holders of `equipment:read`) reads everything except the call-out number, the price, the cost note and the documents; `contract:read` (engineers and managers of the site) adds the call-out number; `contract:read_senior` (managers of the site; admin by the bypass) adds those; `contract:edit` engineers (so managers) and IT admin, an editor without `read_senior` never sees or sends the price. Renewal makes a new record linked to the old one. Reminders 60 and 15 days before the end (push to engineers and managers, email to managers), not once renewed. Breakdown calls are the vendor's tickets (assignee or labour row) on the covered nodes in the period, derived, never re-entered; no vendor-arrival time for now. The agreed PM visits become PM plans with the vendor as assignee and an optional contract on the plan (§ 4.3), when PM is built; ISO 55001 § 8.3 and ISO 9001 § 8.4.

### Not in v1

- **Parts** (ISO 14224 level 9 — bearings, seals) — the v1 equipment tree stops at component (decided 13-10-2026). Parts come with spares.
- Spares and stock (spares consumed per job, stock levels, OneERP stock entries). Wear parts kept in stock (augers, mixer paddles, shredding knives, liners) wait for this, as does a structured **bill of materials** per model (ISO 14224 level 9 parts with maker or generic part numbers). Makers' parts lists are model documents (S012); parts actually used are recorded per ticket (§ 4.2, *Proposed*).
- **Maintenance cost** — no labour cost (rates × hours) or other cost on tickets and PM jobs (decided 13-10-2026). Who worked and time spent are still recorded (§ 4.2), so cost can be derived later without changing how work is captured. **Exception** (R02, 27-10-2026): the cost of a maintenance contract is stored on the contract and seen only by the managers of its site and admin (`contract:read_senior`); it is not spread over tickets or jobs, and no other maintenance cost is recorded.
- **Rotable tracking** (motors, gearboxes, hydraulic pumps moving between equipment, with install/remove history) — later, with spares. See § 4.1.
- Telemetry from **plant-3i** (the sister IIoT repo): production counts per day, run hours, gauge values such as oil temperature, and PLC malfunction flags. The data model leaves room for it (reading `source`).
- Offline mode.
- Tamil UI and Tamil master data — possibly a later version.
- Equipment groups (a set of equipment picked by hand) — equipment class covers selecting equipment. Groups of *classes* are built as the **equipment category** (§ 4.1, S063); they pick no machine by hand.
- **Kiosks** (Raspberry Pi, shared) — a later version (decided 13-10-2026). Their login design is already settled (§ 3, *Shared-device login*).
- Detecting missed "before use" CIL checks (needs a signal that the equipment ran).
- Production counts per equipment, posted to OneERP — a later version; until then no write-back to OneERP.
- **Installation and modification work** (a new concrete machine wired up, trials of new
  packing machines) — not recorded in Yantra in v1 (decided 18-10-2026, daily-report use
  case). EN 13306 keeps modification and installation apart from maintenance. Such work is
  written by hand on the printed daily work log (§ 4.6); the new equipment itself is
  registered with its in-service date.
- Backfilling history from the plant's notebooks: by hand on the ticket screens until
  30-11-2026 (S028); a bulk import later.
- Multiple companies. VEL is one org unit; SSVT, a separate company, is handled as a site for now.

## 3. Roles

**Roles per site** (S011, decided 16-10-2026; A1). The maintenance roles below are held in Yantra, on the person in **Team**: per person and site, **one** role, with all the site's units or chosen ones. For a person with a login those rows are their access. IT admin grants every role; an engineer (`people:assign_technicians` at the site) assigns **Technicians** at their own site only; nobody changes their own access. A person without a login can be a Technician **or an Operator** (the row then says where they work, for pick-lists). **Operators without a login** are created by supervisors and engineers at their own site (decided 16-10-2026, sorting-line use case; the permission key is settled in the brief that builds it, on the pattern of `people:assign_technicians`; queued). Until then only IT admin sets an Operator row on a person without a login (S017, approved 20-10-2026; it changes S011 A1's "without a login, only a technician"). They are needed so CIL jobs and tickets can say who did the check and who found the fault when the operator has no phone (ISO 14224: who detected, who worked). At a record, a user's rights are those of their role at the record's site; navigation and site-less masters use the union over their sites. `it_admin` and `admin` stay in Keycloak and apply everywhere; Keycloak's `maintenance_team` only lets a user log in. A deliberate departure from the base RBAC pattern (roles from the token), recorded in `.claude/CLAUDE.md`.

| Role | Who | Can do |
|---|---|---|
| `maint_operator` | Equipment operators | Raise breakdowns, log readings, do CIL jobs, see the status and open tickets of equipment |
| `maint_technician` | Maintenance technicians | Pick up and work breakdowns and PM jobs: record work, checklists, readings, photos; mark a breakdown "equipment back up" |
| `maint_engineer` | Maintenance engineers | Assign work; verify PM jobs; **close breakdowns**; create and edit equipment, PM plans, checklists and codes |
| `maint_manager` | Maintenance manager | Everything the engineer can, plus reports and dashboards across all units of their site(s) |
| `maint_supervisor` | Production supervisors (S011 A1, decided 16-10-2026) | An operator's rights today (CIL, raise issues, readings), more reports later; usually wider units than an operator. Production-side (TPM autonomous maintenance): above the operator, **off** the maintenance ladder, so a supervisor does not work tickets. Records on behalf of operators without a phone: CIL done, fault found, **back in service** with the technician's name, each with the event time; creates operators without a login at their site (sorting-line use case, 16-10-2026) |
| `maint_storekeeper` | Maintenance stores | No v1 work (spares are not in v1); the role exists so these users can sign in. Stands outside the maintenance ladder. |
| `it_admin` | IT | Users' role view, master data housekeeping (units, OneERP sync), settings, notification channels. **Full access to tickets** at every site (S017, user 20-10-2026: a deliberate departure from "not maintenance work" and from ISO 27001 A.5.3 segregation of duties; every ticket action is logged with its user, A.8.15). Not all-powerful. |
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

**What each role sees in the menus** (decided 28-10-2026, S064, from the UX audit). *Masters*
shows in the nav only to holders of an edit key on masters data (`masters:edit`,
`equipment:edit`, `people:edit`, `failure_codes:edit`: engineer, manager, IT admin); the floor
roles still read the same lists where they work (equipment page, ticket pick-lists), and
`masters:read` stays every role's for those pick-lists. Settings shows the *Database* and
*Background tasks* cards only with `settings:edit` (IT admin); a manager sees *Removed
documents* first. Sign out is a labelled button of at least 44 px on every width (shared
devices), a departure from the base's Topbar rule.

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
| `ticket:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket:raise` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket:work` | | | ✓ | ✓ | ✓ | ✓ |
| `ticket:restore` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket:assign` | | | | ✓ | ✓ | ✓ |
| `ticket:close` | | | | ✓ | ✓ | ✓ |
| `ticket:edit_notes` | | | | ✓ | ✓ | ✓ |
| `improvement:read` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `improvement:edit` | | | | ✓ | ✓ | |
| `pm_plan:edit` | | | | ✓ | ✓ | |
| `pm_job:work` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `pm_job:verify` | | | | ✓ | ✓ | |
| `reading:log` | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `report:read` | | | | ✓ | ✓ | |
| `settings:edit` | | | | | | ✓ |
| `access_log:view` | | | | | ✓ | ✓ |
| `people:edit` | | | | ✓ | ✓ | ✓ |
| `people:assign_technicians` | | | | ✓ | ✓ | ✓ |
| `failure_codes:edit` | | | | ✓ | ✓ | ✓ |

Site-scoped keys (`config_rbac.SITE_SCOPED`: `equipment:read`, `equipment:edit`,
`equipment:purge_documents`, `people:assign_technicians`, and every later breakdown,
PM, reading and report key) are checked at the record's site; the others are global.
`reading:log` is built (S039, 24-10-2026) as in the table: the operator and up, at the node's
site, not IT admin; removing a reading is a correction, held by `equipment:edit`, so IT admin
removes a reading but does not log one.
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
`failure_codes:edit` (S016, approved 20-10-2026) — engineers (and so the manager) and
IT admin — maintains the failure modes, causes and maintenance actions. Global, not
site-scoped: the lists are the same at every site.
`ticket:read` and `ticket:raise` (S017, approved 20-10-2026) replace `breakdown:raise`:
granted to the operator (so the whole ladder and the supervisor) and IT admin, not the
storekeeper; site-scoped. Ticket photos are written with `ticket:raise`, removed ones
restored or purged with `equipment:purge_documents`.
`ticket:work`, `ticket:restore`, `ticket:assign` and `ticket:close` (S018, approved
20-10-2026) replace `breakdown:work` and `breakdown:close`, all site-scoped and all held by
IT admin: `ticket:work` (acknowledge, start, edit, labour, lower the grade) from the
technician up; `ticket:restore` (back in service) from the operator up, so production
confirms restorations, and (S027) adds work notes; `ticket:assign` and `ticket:close`
(close, not a fault, send back) engineer and manager. `ticket:edit_notes` (S027, approved
22-10-2026; site-scoped) corrects a note, keeping the earlier text: engineer, manager and IT
admin. **Self-close is allowed** (user, gate A): an engineer may close a
ticket he worked himself — a recorded departure from segregation of duties (ISO 27001
A.5.3), since the plant has few engineers. Assignees are technician, engineer or manager;
the person named on back in service and on labour rows may be **anyone with a membership
at the ticket's site, operators included** (an operator who fixes his own defect is
recorded truthfully; his rows carry no trade, so man-hours per trade are unaffected).
`ticket:backdate` (S028, approved 22-10-2026; global) enters ticket times up to 3 years
back: held by no role, so by admin only through the bypass (ISO 27001 A.8.2).
`improvement:read` and `improvement:edit` (S067, R05 Q1.3 a, 30-10-2026; both site-scoped)
cover the improvement record (TPM focused improvement): `improvement:read` from the operator
up and IT admin, because TPM wants the floor to see the analysis; `improvement:edit` (start
one from a ticket, edit it, add and remove its tickets) engineer and manager, who lead the
analysis. IT admin reads only, as for PM (R03 Q2.2; ISO 27001 A.8.2); the storekeeper holds
neither. The lead of an improvement is an active person whose role at its site grants
`improvement:edit`, so the lead list follows the key. A ticket page lists only the
improvements its reader can open (`improvement:read` at the improvement's unit or its
machine's unit; S067 A1).

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
- **Fields:** code, name, **model** (required on equipment and components; it gives the equipment class and type — decided 17-10-2026, S012. A component-unit may have no model, and then its class (required) and type (optional) are picked directly — decided 24-10-2026, S033, since ISO 14224 asks for maker and model on the equipment unit, not on its subunits), serial number, year, maintenance strategy (*Proposed*, above), criticality (A/B/C; required on equipment, default C; component-units and components inherit unless graded), **lifecycle** (in service / standby / out of use / scrapped; called *status* until S030, renamed 23-10-2026 so that *status* means whether a machine is down or working — scrapped is final and read-only; equipment with open tickets cannot be scrapped, S017), unit. Only equipment has a unit; its parts follow it (decided 14-10-2026, S002). Which machine backs up which (a standby relationship) is not recorded. Notes: free text for reading, searchable, not in the history (S004).
- **Equipment class:** what a piece of equipment *is* (hydraulic press, ball mill, kiln fan, …), a list maintained by engineers. Used to pick equipment when applying a PM template, to compare MTBF/downtime across equipment of a kind, and (if failure codes are adopted) to scope code lists. A class carries **properties** (S043, decided 24-10-2026): technical data defined once in Masters (number with a unit, choice, text, yes/no, location since S061; ISO 14224 Annex A), linked to classes, valued on its models (S043) and overridden on an item where its nameplate differs (S044, built 25-10-2026: *Edit this machine's values* on the equipment page's Properties card, for equipment:edit at the item's site; the card marks such a value "· this machine"; each set, change and clear is a line in the item's history, the model's value then in force marked "(model)"; a component-unit without a model holds only its own values; own values stay on a model or class change, hidden while the class lacks the property; v33 `equipment_property_values`). Decided 27-10-2026 (S061): a property may *apply to every class* (no class links needed), and may be *set on each machine* only (installation data, ISO 14224; never on the model); a *Location* data type (latitude, longitude) with "GPS location" seeded as both, shown on top-level equipment only, and a hint on machines whose Mobility is Portable or Mobile (Mobility made by hand on production, Fixed / Mobile / Portable). Built 27-10-2026 (S061, v34 `all_classes`, `per_item_only`, `value_lat` / `value_lng`): Masters › Properties has two tick boxes and the badges *Every class* and *Each machine*; a class's table lists the every-class properties, marked, with no *Remove*, and its picker leaves them out; the model's dialog leaves out per-machine properties and a model's save of one is refused; on the equipment page a Location row links *Open in Maps* (Google Maps), *Use my current location* fills it from the browser's position (one reading, its accuracy shown), and the model line and *Edit model values* show only when the card has a row that can come from the model. Decided 27-10-2026 (S062): the equipment list and the printed asset list filter by property — lines of property, operator, value, joined by one *All / Any* switch (no nested groups); the value in force is the item's own, then the model's; a node matches only where its class shows the property; *not equal to* and *is not* leave out nodes with no value; the first property filter widens the list to *All levels*, as the first search does; the filter is checked by the server before the dialog closes. Built 27-10-2026 (S062, no migration): the equipment list has *Filter by property* in its filter row (*Properties (2)* once set); its dialog takes up to 10 lines of property, operator (in words: *more than*, *at least*, *between*, *is*, *is not*, *contains*, *has a value*, *has no value*, …) and value, *All conditions* or *Any condition* from two lines, and lists only the class's properties when the list has a class filter; a refused value shows under its line. The filter lives in the URL as one key, `props` (a reload, a bookmark and *Back* keep it; applying and clearing it are steps of the browser's history); a line under the filter row reads it ("Properties (all of): Rated power more than 7.5 kW · …") with *Clear property filter*, and an unreadable `props` says so instead of the list. *Print asset list* carries it, the API (`GET /api/equipment`, `GET /api/equipment/asset-list`, key `props`) applies it to the machines, and the section header names it. How the equipment is built stays its *type* (S004), not a property. A class is a **kind**, not a container like sites and units: the same class is used at any level of the tree — a blower is a component-unit in one machine and a stand-alone machine elsewhere — so "all compressors in the plant" is one class across every level (clarified by the user 16-10-2026). So a class has no level of its own; a level shown for a class is derived from where it is used.
- **Equipment category** (decided and built 27-10-2026, S063, v35 `equipment_categories`, `equipment_classes.category_id`): a group of equipment classes, ISO 14224's *equipment category* (Annex A), e.g. Lifting equipment (EOT crane, hoist, chain block, sling), Utilities, Power tools. A grouping of classes, not a level of the taxonomy. Each class is in at most one category, picked in *Masters › Equip Class*; a machine's category is its class's, nothing is stored on the machine. A name only (no code), kept by engineers in *Masters › Equip Category* (`equipment:edit`); nothing seeded (KLA creates the list); deactivating is refused while an active class is in it ("N active classes are in this category. Move them to another category first."). The equipment list filters by it (*All categories*, before *All classes*; a chosen category narrows the class select; the level stays, as for a class) and *Print asset list* carries it ("Category: <name>" in the section header). Later uses: reports by category, one statutory plan for every class in Lifting equipment (OSH Code 2020 rules, § 4.3 *Certification plans*), the maintenance strategy per category (Power tools: run-to-failure).
- **Equipment type** (decided 15-10-2026, S004): how equipment of a class is built, e.g. `RPP` → closed / open execution (ISO 14224 class → type). Types are defined per class, maintained by engineers; an equipment's type must belong to its class.
- **Sites and units:** sites (SMTW, BRICKS, SSVT, the farms, …) are created in Yantra. Each site has units — its areas and shop floors — coded `SITE.UNIT` (e.g. `SMTW.KILN`, `SSVT.SHOP`). A unit can be mapped to a OneERP warehouse code. Until the sync exists, units are maintained by hand.
- **Codes frozen once in use** (decided 13-10-2026, S001). A site, unit or equipment-class
  code — and a unit's site — can be corrected only while nothing references the record
  (site: has units; unit: has users' unit access, equipment, or any ticket — open or
  closed, S025; class: has equipment). After that it is frozen. A unit also cannot be
  deactivated while it has tickets not closed ("Close its tickets first (N open)", S025):
  an inactive unit drops out of access, so its team could not close them. The freeze is on
  the unit record, not the machine: a machine with open tickets can still move (U3). For class codes this protects equipment codes,
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
- **Vehicles are equipment** (*Proposed*, 20-10-2026, fleet use case). The 40 vehicles of SMTW
  and SSVT are equipment at units `SMTW.FLEET` and `SSVT.FLEET` (master data below); the
  odometer is a counter meter in km (§ 4.5), run hours for tractors, earth movers and
  material handling. ISO 14224's taxonomy is written for plant but fits as is. The boundary with
  **Vaahan** (§ 7): Vaahan keeps what is vehicle-specific and legal (registration, insurance,
  permits, fitness certificate, PUC, road tax, trips, refuelling, tyres) and the garage bills;
  Yantra holds the work (defects, tickets, inspections, PM by km). No second register of
  vehicle papers in Yantra; the Yantra ticket number goes in Vaahan's maintenance report. The
  one duplication is the vehicle itself, which must be equipment here for tickets and plans to
  hang off: identity fields only, loaded once by hand, synced from Vaahan later (§ 7).
- **Vehicle master data** (*Proposed*, 20-10-2026, fleet use case; all entered from the
  Masters screens, no code change). **Two classes**, since the class is what failure-mode
  lists, PM templates and the fitness inspection hang off, and ISO 14224 defines a class as
  equipment whose failure data is comparable: **Vehicle** (`VEH`; road-registered, km meter)
  and **Material handling** (`MHE`; forklifts, the Toyota electric pallet truck, the SSVT
  stackers; hour meter, no road papers; listed in Vaahan too). **Types** are Vaahan's RTO
  categories in the same words, so the sync is a plain mapping: motor cycle, light passenger
  vehicle, heavy passenger vehicle, LGV three-wheeler, LGV four-wheeler, HGV, HGV tipper,
  tractor, earth mover under Vehicle; forklift, electric pallet truck, stacker under Material
  handling. Vaahan's `odometer_type` per model (distance, hours, both) says which meters each
  equipment gets. **Makers and models** one to one with Vaahan's (Tata Motors, Ashok Leyland,
  Mahindra, TAFE, Toyota Material Handling, …; designation = Vaahan's model name, the variant
  appended only where it changes parts, e.g. *Bolero Pickup*); the model carries the owner's
  manual and the maker's service schedule as model documents (S012), the source of PM-by-km
  templates. **Equipment row**: code `VEH001` / `MHE001`, serial number = registration number,
  name = registration plus the common name (*TN 72 AB 1234 Tata 407*). **No component-units**
  at first: the symptom names the subsystem; a tree is added to a vehicle only when a ticket
  needs to point lower, as the press tree was.
- **Verification rounds** (*Proposed*, 16-10-2026): a job per unit where someone walks the
  floor scanning QR labels; scanned equipment are confirmed, unscanned listed as not found,
  unregistered machines found on the walk are added. ISO 55002 recommends periodic physical
  verification (the accounting fixed-asset audit is the same walk). Cheap: labels and unit
  lists exist.
- **Printable asset list** (S015, decided 20-10-2026): the paper form of the verification
  walk until the rounds exist. From the equipment list's filters, one A4 portrait section
  per unit; the filters choose machines, parts optional (indented, following their machine);
  an optional checklist (Found, Remarks, signature footer for maintenance and accounts).
  The Yantra code and serial number identify the item; no accounts asset number. Print
  only, no export. CARO 2020 does not apply to the businesses.
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
- **Meters on the equipment page** (S038, built 24-10-2026): a *Meters* card, after the
  details and parts and before the notes, lists the node's meters: its model's and its own
  (§ 4.5). Any level may carry meters: an alternating pump (a component-unit) has its own
  hour meter, a die its own strokes; a gearbox's oil change runs on its machine's hours.
- **QR label** (S014, decided 18-10-2026): 52 mm square, printed on A4 paper (15 per sheet) for now, for any node of the tree. It shows the QR, the **code**, the **site** code and the name. The QR holds a short link `<label address>/e/<code>` (address a setting, default `https://vel-yantra.mspv.app`), so a label never goes out of date; error correction level Q for dirty paper. Scanning it with a phone camera opens the equipment page, from where an operator can raise a ticket or log a reading in one tap. QR made in the backend with `qrcode` (python-qrcode).

### 4.2 Tickets: breakdowns and defects

**One ticket for every problem found on equipment** (decided 18-10-2026). A ticket is the
**maintenance request** of EN 13460 (ISO 14224 calls it a *notification*); once maintenance
acknowledges it, the same record is the **work order**: who worked, what they did, when, parts,
sign-off. One table with states, not a request table and a work-order table: right-sized for
about 50 users, and the record of the event stays in one place (ISO 14224).

- **Breakdown or defect** comes from the **intensity** (below), not from a separate field:
  - **breakdown** — *critical*: the equipment has stopped; downtime runs; notifications and
    escalation apply;
  - **defect** — *degraded* or *initial*: the equipment still runs but something is abnormal (a
    leak, a noise, a loose guard, a worn scraper). No downtime. This is the TPM tag an operator
    hangs during autonomous maintenance (*fuguai*, abnormality); catching defects before they
    stop the machine is what TPM and the detection-method mix (below) measure.
  - A defect that gets worse is **re-graded critical** with the event time; downtime starts then.
  - Most defects are **deferred work** (below): planned for a slot, parts or a vendor.
- **Sources:** raised by hand (an operator, supervisor or technician), from a Not OK item on a
  CIL or PM job (phase 4), from an out-of-limits reading (phase 4), or by another system (the
  shared ticket API, later). Every source lands in the same ticket.
- Table and permission-key names settled by S017 (approved 20-10-2026): tables `tickets`,
  `ticket_events`; keys `ticket:*`. **The symptom (failure mode) is optional at raise** and
  required at close (S018). **"Not fixed" after back in service is a new ticket**, linked to
  the old one, not a reopen (built in S018). Entered times may be back-dated up to 7 days; admin
  (key `ticket:backdate`) up to 3 years; everyone up to 3 years until 30-11-2026 for the
  backlog, and a raise more than 7 days back sends no alert (S028).

States and who moves them:

```
raised ──► acknowledged ──► in progress ──► back in service ──► closed
(operator) (technician/     (technician)    (technician)        (engineer)
            engineer)
                                              └─ engineer can send back to "in progress"
raised / acknowledged ──► closed  (engineer, frivolous — code + remarks required)
```

- **Timestamps** for each transition. From them: response time (raised → acknowledged), repair time (in progress → back in service), downtime (raised → back in service).
- **As built by S018** (approved 20-10-2026): work may **start straight from raised**;
  **back in service** may be recorded after the fact from raised or acknowledged, with an
  optional *started* time (this settles "technician arrived" above); **not a fault** closes
  with a cause and a required remark, also after *Start* (S025: started on arrival, nothing
  found; its times stay blank, out of MTBF and MTTR); **send back** asks "machine down again?" — yes makes
  it a breakdown again, no lowers only a critical ticket; **"Not fixed — raise again"**
  opens a new ticket linked as a repeat when the old one's back-in-service time is within
  **7 days**; once a ticket has come back as a repeat it can no longer be sent back (S025:
  the failure that came back is on the repeat; it can still be closed). The times are computed from the events, never stored: **response time**
  (raised → first acknowledged or started; the plant's own measure), **repair time** (EN
  13306 *active corrective maintenance time*: time in progress), **downtime** (EN 13306
  *down time*, the *time to restoration* of a breakdown; its mean is **MTTR**). Closing
  needs cause, action, symptom and at least one labour row. Ticket attachments: photos
  and vendor documents (PDF reports, quotes).
- **Improvement (S067, 30-10-2026; R05.1):** a ticket back in service or closed can start an
  improvement (TPM focused improvement), and a ticket in any state can be added to one; a ticket
  closed as *not a fault* can do neither, and a ticket is in at most one open improvement. The
  ticket row is never written: the improvement only links it. The ticket detail lists its
  improvements and says whether this user may start one (`GET /api/tickets/<id>`:
  `improvements`, `can_start_improvement`). The screens are S068's.
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
- **Deferred work** (*Decided* 21-10-2026 as S019, except meter targets; first proposed 16-10-2026, extrusion-line use case). Much work is requested
  while the machine runs and done later, once parts are bought or fabricated and a slot is
  found: a touchscreen to replace, worn scrapers, a liner "good for another 1,000 hours", a
  filter the AMC vendor asked for. EN 13306 calls this *deferred corrective maintenance*;
  SMRP measures planned against reactive work. Decided in S019 (21-10-2026):
  - one **scheduled** state between acknowledged and in progress, shown as *Deferred* on a
    defect and *Waiting* on a critical ticket. It carries a **required planned date** (today
    or later, within 365 days) and a **waiting reason**. The engineer (`ticket:assign`)
    schedules from raised or acknowledged and changes the plan; a technician (`ticket:work`)
    may schedule from in progress, when work stops for a part. Every slip is an event with a
    remark; *Overdue* is a list filter and a badge;
  - six waiting reasons, a fixed list in code, each mapped to an EN 13306 delay:
    parts, vendor, expert → logistic delay; production slot, approval → administrative
    delay; other → neither. No *workshop* reason: time in the workshop is active repair;
  - a critical ticket's downtime splits into active repair (in progress) and waiting, per
    reason. A press cylinder three weeks at the maker is waiting;
  - the stop taken for a scheduled job is **planned downtime**, by the technician's answer
    at *Start* ("Is the machine stopped for this work?"), reported apart from breakdown
    downtime (EN 13306, SMRP; OEE treats them differently);
  - S034 (24-10-2026): the date means **planned** for a production slot and **check again by**
    for every other reason (someone outside maintenance controls the wait). The date stays
    required; the dialog asks the reason first and offers *In 7 / 14 / 30 days*. The button
    reads *Defer* or *Put on hold*; the timeline line and the fallback label read *On hold*;
    the list filter reads *Deferred / Waiting*;
  - *later*, with the PM engine (phase 4): a target **by meter value** as well as by date
    ("at 1,000 run hours from now"), reusing the meter-trigger machinery of PM plans.
- **Fleet defects** (20-10-2026, fleet use case): each defect found on a vehicle is a ticket of
  its own, mostly *initial* or *degraded*, so one inspection of 40 vehicles gives a backlog of
  tickets instead of one paper report. The drivers' supervisor raises them on the driver's
  behalf (*reported by* the driver, an Operator row without a login, S017). Repairs are done
  in house (a Technician) or at a garage (a contractor in Team, the ticket's assignee, S018).
  A vehicle at the garage is a **scheduled** ticket with the waiting reason *vendor* (deferred
  work, above), so the days away count as logistic delay, not repair time, and the ticket
  cannot be forgotten: it stays open and shows on the engineer's dashboard past its planned
  date. SMRP measures this as backlog age.
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
- **Vehicle failure codes** (*Proposed*, 20-10-2026, fleet use case; entered in Masters ›
  Failure codes, no migration). The General modes apply to a vehicle as they are. ISO 14224
  Annex B has no vehicle class, so a **Vehicle**-scoped list in the driver's words, codes
  distinct since the code is unique across classes: `VBRK` brakes weak, pulling or noisy;
  `VSTR` steering play or pulling; `VCLU` clutch slipping or hard; `VGBX` gear hard to shift
  or jumping; `VSUS` suspension noise or sagging; `VELE` lights, horn, wipers or indicators
  not working; `VTYR` tyre worn, damaged or puncture; `VSMK` smoke or high fuel use; `VWRN`
  warning lamp on; `VAC` AC not cooling; `VBDY` body, cabin or glass damage. **Material
  handling** gets the General list plus brakes, tyres and *mast or forks*. **Causes**: the
  ISO list unchanged plus one addition managers will want to count, `3.5` *Accident or
  external damage* in the operation group (today it would hide under operating error).
  **Actions**: ISO's twelve unchanged (*Service* covers an oil change).
- **Intensity** (the TPM red tag is this ticket): the operator grades the problem. Scale (decided 15-10-2026), from ISO 14224's failure impact: **critical** (equipment stopped), **degraded** (running with reduced function), **initial** (still fine, early signs; ISO 14224 calls it *incipient*). Only critical time counts as downtime.
- **Codes** (ISO 14224 core, decided 15-10-2026): failure mode (the operator picks it as the symptom), failure cause and maintenance action (technician/engineer pick). Lists trimmed from ISO 14224 Annex B, maintained by engineers. Mechanism not in v1; detection method automatic (below). **S016 (approved 20-10-2026):** three masters, pre-filled from Annex B with ISO's codes and plain-word labels. A failure mode belongs to **one equipment class or is General**; the picker shows the class of the ticket's equipment (level 6, even when the ticket is on a component) plus General — checked in the API, since a General mode has no class. A cause carries one of ISO's five **cause groups** (design, fabrication / installation, operation / maintenance, management, miscellaneous), so the plant's own causes roll up the ISO way; the group stays editable once in use. A code is frozen once a ticket uses it (added by S017/S018). *Later:* failure mechanism as a fourth list, if technicians keep writing mechanisms ("worn", "contaminated") as causes.
- **No approval step:** a raised ticket goes straight to maintenance. If it turns out frivolous, the engineer **closes it directly** from raised or acknowledged, with a required code (e.g. *no fault found*, *not a breakdown*) and remarks.
- **Parts used** (*Decided* 21-10-2026 as S020 for tickets; PM jobs decided with PM; first proposed 17-10-2026, parts use case): a structured line on tickets and
  PM jobs — part number, description, quantity, maker if any — replacing "action *replaced* plus
  nameplate details in the remarks". No stock, no cost. The number is either a **maker's part
  number** (from a Haendle drawing, or from the quote of a service engineer whose maker gives no
  parts list) or a **generic designation** (bearing `6205-2RS`, a valve or filter element by
  standard spec), since many press spares are bought generic. The line sits on the ticket's
  **component**, so a part lands against the thing it fits; the vendor's quote and findings
  attach to the ticket. Over time this builds the parts list the maker never gave, and seeds
  each model's bill of materials when spares come. ISO 14224 lists parts replaced among the
  maintenance-record fields. Ordering and the item master stay in **OneERP** (ISO 8000: one
  item master); a later link maps Yantra part numbers to OneERP item codes. Decided in S020
  (21-10-2026): no parts master; each line holds a description, an optional part number with
  its kind (*maker's* or *standard*), a free-text maker (required for a maker's number), a
  quantity with a unit (*nos, set, m, L, kg*) and the node it was fitted to (the machine or a
  component, default the ticket's component). Recorded by `ticket:work` holders until the
  ticket is closed. The *Add* dialog suggests the lines already recorded on the same machine.
  A ticket with parts cannot be closed as *not a fault*. Closing with the action *Replace*,
  *Modify* or *Overhaul* and no parts shows a hint, not a refusal.
- **Who worked:** one or more technicians per ticket, with time spent. Each labour row carries the **trade worked** (pre-filled when the technician has only one), so man-hours per discipline (ISO 14224 Table 8) can be summed (S010, 16-10-2026).
- **Work done without a ticket** (*Decided* 20-10-2026 as S018 A1: an *Already fixed — back in service* checkbox on the raise screen, for every `ticket:restore` holder; raise and back in service in one save, the engineer still closes; first proposed 18-10-2026, daily-report use case): work that
  walks into the workshop (a portable vibrator needing new carbon brushes) gets its ticket after
  the fact: raised and marked back in service in one save, with the times and the technician
  named; the engineer then closes it with cause and action like any ticket. The record matters more than the
  workflow (ISO 14224 wants every maintenance event recorded, whoever asked for it).
- **Photos and remarks** at any step, and **work notes** (S027, approved 22-10-2026): on an
  open ticket, anyone who may confirm the machine is back (`ticket:restore`) writes what was
  found and tried, as a line on the timeline; the raise's *What is wrong?* is the first note.
  New findings are new notes; an engineer corrects a typo or wrong fact (`ticket:edit_notes`),
  and the earlier text is kept (EN 13306 fault diagnosis; ISO 9001 § 7.5.3).
- **Notifications** (S021, § 4.7): web push per device. A new breakdown → engineers, the unit's supervisor and the maintenance manager; a new defect → engineers, quietly; a breakdown not acknowledged in time (A 10, B 30, C 60 minutes) → engineers and managers, once; a job assigned by an engineer → that person.
- **Meters on the ticket** (S052, built 25-10-2026): the ticket page's *Meters* card shows the meters of the machine and the part as they stood **at the ticket's time** (*When it happened*), with a 7-day High / Low / Not OK warning (§ 4.5).
- **Share a ticket's link** (S066): the ticket page's title row has one button: *Share* on a phone (the share sheet, with the serial, place and problem, and the link) or *Copy link* elsewhere, with a box to copy by hand when the clipboard is missing. Frontend only.
- Serial: `TK-YYYY-MM-NNN` (decided 20-10-2026, S017): one series for breakdowns and defects, since a defect can become a breakdown; numbered by the month the ticket is written.
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
- **Item types** (*Proposed*, 20-10-2026; supersedes the three lines above once built). One
  **item shape** is shared by PM template items, PM plan items, procedure steps (§ 4.3a) and
  steps attached to a ticket, with one result row per item. Types:
  - **Task** — done / not done ("grease the bearing", "clean the filter"). EN 13306 separates a
    *maintenance task* from an *inspection*; "Not OK" on a task is meaningless, and the split
    makes reporting honest: Not-OK checks count defects found, undone tasks measure PM quality.
  - **Check** — OK / Not OK / NA with remarks (today's checklist item; EN 13306 inspection).
  - **Reading** — a value with unit of measure and limits (today's reading item). A reading
    that names a **meter** (§ 4.1) also writes a meter reading with source `pm`, so one entry on
    the job feeds the meter trigger and the die or press history; a plain measurement
    (vibration, clearance) has limits but no meter.
  - Every item carries optional **help text** and a **reference photo** — TPM's visual standard,
    "what good looks like" (the grease nipple, the correct oil level, a worn scraper beside a new
    one) — and a **photo setting**: none / optional / required. The per-plan "photo required"
    flag goes; it was too coarse (evidence belongs to the step that produced it).
  - **No signature step.** Every action records who and when, and the sign-offs are states —
    technician *done*, engineer *verified*, supervisor *back in service* — which is the record
    ISO 9001 § 7.5.3 asks for. A drawn signature on a phone adds friction and no evidence; the
    one case without a login (a contractor or government inspector) is covered by the attached
    certificate on certification plans. Rejected: a separate checkbox type beside task (same
    thing); photo as a type of its own (a photo is evidence on a step, not a step).
- **Triggers** — one or both:
  - **Calendar:** every N days / weeks / months. **The next job is due from the completion date of the last one.** If a plan needs a different rhythm, the engineer edits the plan.
  - **Meter:** every N units of a meter (run hours, production count), or when a reading crosses a limit. **Crossing creates a PM job automatically** and notifies, just like a calendar job falling due.
- **Performer:** maintenance (team or technician, the default for generated jobs) or operator (CIL plans). An **AMC vendor** is a contractor record in Team and can be the plan's assignee (16-10-2026); the engineer verifies the job with the vendor's report attached. Calibration of instruments: see **Calibration** below (20-10-2026; supersedes "an ordinary calendar plan with the certificate attached").
- **Both triggers, whichever first** (16-10-2026): standby equipment gathers hours slowly, so its plans use calendar and meter together, as OEM schedules are written.
- **Fitness-for-use inspection** (*Proposed*, 16-10-2026): a PM template applied to every
  class, performer the engineer, calendar (e.g. yearly), with a checklist and an outcome — fit /
  fit with conditions / not fit; "not fit" sets the equipment out of use. Gives every machine,
  run-to-failure ones included, a periodic look. Self-verification allowed for this plan kind
  (the engineer does and signs). Statutory examinations (the Factories Act requires periodic
  examination of pressure plant, hoists and lifting machines by a competent person — the
  compressors' air receivers are pressure plant; confirm with whoever handles safety) are the
  same plan with the certificate attached.
- **Fleet inspection** (*Proposed*, 20-10-2026, fleet use case): the fitness-for-use inspection
  applied to the *Vehicle* class, **monthly** (today about six-monthly, when an inspector is
  free; a plan with an interval makes an overdue fleet visible instead of waiting to be
  remembered). Checklist: brakes, steering, suspension, leaks, lights, battery, tyres with
  tread depth as a reading, papers present; outcome fit / fit with conditions / not fit; every
  Not OK raises a defect ticket. Performer: the head engineer (self-verification, as for every
  fitness-for-use plan) or a visiting polytechnic faculty member, recorded as a contractor in
  Team without a login; the engineer enters the round for them or attaches their report. A
  round done early resets the next due date, as every calendar plan does. Run as a **PM
  route** (below): forty vehicles with a full checklist each is a day's work, and forty
  separate jobs a month is how a monthly target slips back to six-monthly. The fleet is
  proposed as the **pilot for routes**, ahead of the genset round. Apart from this, a short
  daily pre-trip check by the driver is a before-use CIL plan (§ 4.4), recorded by the
  supervisor until drivers get a kiosk: TPM keeps the user's daily look and the specialist's
  periodic inspection as two layers. In the US the driver's check is a legal form (the Driver
  Vehicle Inspection Report, 49 CFR 396.11: a safety defect is repaired before the next trip);
  India has no equivalent rule, so this is practice, not law.
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
- **Calibration** (*Proposed*, 20-10-2026; ISO 9001 § 7.1.5, monitoring and measuring
  resources — the clause an auditor or a BIS inspector will hold the plant to). The plant has
  no calibration policy; ISO 9001 is a future goal, so this is built in its shape from the
  start. **Instruments are equipment** of class *measuring instrument* (types: vernier, DMM,
  pressure transducer, temperature indicator, thermocouple, weigh scale, weighbridge, moisture
  analyser, energy meter, thermal camera, IR thermometer, flexural strength machine, …), owned
  by the Quality lab, production or maintenance, with extra fields: range, **required
  accuracy** (what the process needs, not the brochure figure — ISO 10012's *metrological
  confirmation*: a vernier reading to 0.02 mm is ample for a roller gap held between 1.5 and
  2.5 mm), **calibration class**, owning department and **custodian** (a vernier lives with a
  technician, not a unit). Not every instrument needs a certificate; the class decides:
  - *Critical, external*: the result goes on a product claim or a safety decision —
    flexural strength machine (force verification per IS 1828 / ISO 7500-1), moisture
    analyser, lab scales. Yearly, by a **NABL-accredited** lab (ISO/IEC 17025): accreditation
    is how traceability to national standards is proven without auditing the lab oneself,
    and the first thing BIS asks for.
  - *Reference standard*: the plant's own reference DMM, slip set and reference pressure
    gauge, used only to check other instruments. NABL, since every in-house check hangs off
    them.
  - *Working, verified in-house*: verniers, DMMs, IR thermometers, pressure transducers,
    temperature indicators. Checked against a reference standard, or by a traceable
    certificate from the current agencies — acceptable to ISO 9001 only if the certificate
    names the reference used and its certificate number, the uncertainty, and as-found and
    as-left values.
  - *Legal metrology*: the weighbridge and trade scales, verified and stamped by the state
    department under the Legal Metrology Act 2009 (weighbridge yearly; accuracy classes per
    OIML R 76 / IS 9281). A stamp proves fitness for trade; a lab scale used on product tests
    still needs a calibration certificate. Have the scale's vendor check it with test weights
    before the inspector's visit: a failed verification seals the scale until re-verified.
  - *Replace on schedule*: thermocouples (Type K drifts and costs little).
  - *Indication only*: thermal camera, energy sub-meters, panel meters — labelled "no
    calibration required", which ISO 9001 allows where traceability is not needed.

  The schedule and evidence are a **certification plan** per instrument (above): valid-until
  date, certificate attached, the certifying body a contractor in Team and the Legal
  Metrology inspector recorded the same way; the compliance register is the calibration due
  list. An **in-house verification** is a PM plan whose reading items hold the error at each
  check point, limits set to the required accuracy, plus a checklist item naming the
  reference used. An over-limit value raises a ticket (§ 4.5), which is the record of the
  **out-of-tolerance review** § 7.1.5.2 c asks for and plants forget: what did the
  instrument measure since its last check, and what follows. The QR label (S014) is the
  calibration sticker: scanning shows status and due date. Intervals start from the maker's
  figure and are adjusted on history (ILAC-G24). Lab staff are technicians and the lab head
  an engineer at the Lab unit, so no new role. Not built: a separate calibration module. The
  written policy (classes, intervals, who approves them, out-of-tolerance steps) is the
  plant's document, drafted alongside the step. Verifying the presses' transducers and
  proportional valves in-house against a reference gauge also addresses their known drift
  (Plant-Facts § 4).
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
  in the shared **item shape** of § 4.3 (task / check / reading, each with help text, reference
  photo and photo setting; 20-10-2026), who changed it and when (ISO 9001 § 7.5 control of
  documented information). Edited by engineers.
- **Onboarding** (16-10-2026): dos and don'ts of a machine or tool, shown one card at a time
  (picture + short text) on the phone or kiosk before first use, written in **Tamil** (the DB is
  utf8mb4, so content is Tamil today while the UI stays English). A **completion record** —
  person, procedure, equipment or class, date, recorded by the supervisor or by the operator at
  the kiosk — is the seed of the skill matrix (TPM training pillar; ISO 45001 § 7.2 competence).
  Blocking CIL for an untrained operator can come later, once records exist.
- **Used from:** PM templates (the "how" behind a checklist), tickets (the diagnostic case —
  open question 15 is a procedure of kind *diagnostic* with steps), the equipment page.
- **Any kind attaches to a ticket** (20-10-2026), not only diagnostic: "change pump elements"
  on a repair ticket is the work-order case a CMMS job plan serves. Attaching copies the steps
  onto the ticket as result rows, exactly as a PM job copies its plan items; the technician
  fills them on the phone and they show on the ticket timeline. Lands with PM items (phase 4);
  S017 and S018 stay as briefed.
- Past jobs and tickets keep their own copy of the items, so editing a procedure never
  rewrites history.
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

- A piece of equipment has meters: run hours, production count, or a measured quantity (oil temperature, roller clearance, vibration, wear mm). Each meter is a *meter type* (the catalogue entry: name, unit of measure, decimals) of one **kind**: **counter** (only goes up; triggers every N units), **gauge** (a level; triggers on crossing limits), **amount per period** (a quantity for the period just ended) or **yes / no** (a check with an expected answer).
- **Decided 24-10-2026 (S037–S040, approved by KLA):**
  - **Meter types** are a catalogue in Masters (S037), edited by `equipment:edit`, each of one **kind**: *counter* (a running total; a lower reading is refused unless marked as a reset), *gauge* (a level with min / max limits), *amount per period* (a quantity for the period just ended, e.g. *Shift production*; 0 or more, summed for totals) or *Yes / No* (a check such as *Oil level above min*, with its expected answer on the type). Eight types are seeded. ISO 4406 codes wait for the oil-sampling plan (phase 4).
  - **Built (S037, 24-10-2026):** Masters › Meter types, migration v29 (`meter_types`), `/api/masters/meter-types`; a Yes / No type has no unit and no decimals; kind, unit and decimals stay editable until S038 freezes them on use.
  - **Meters live on the model** (S038): every node of the model has them; a node may override a gauge's limits and add its own meters; every level of the tree may carry meters. A used meter type's kind, unit, decimals and expected answer freeze.
  - **Built (S038, 24-10-2026):** migration v30 (`model_meters`, `node_meters`; three `equipment_events` values). Masters › Models › *Meters* lists a model's meters with a gauge's default limits (*Add meter*, *Set limits*, *Remove*, asked first; `/api/masters/equipment-models/<id>/meters`, `/api/masters/model-meters/<id>`). The equipment page's *Meters* card shows the node's meters, computed live: its model's (*From the model*) plus its own (*This machine only*), each with the limits in force or a Yes / No meter's expected answer; engineers add own meters, override a gauge's limits (*Use the model's limits* clears it) and remove own meters (`/api/equipment/<id>/meters`). An override equal to the model is not kept. Each node change is a history line with the limits in force on both sides; model changes are not in a node's history. A model change on a node changes its meters at once; overrides and own meters stay. Limits are for gauges only, stored as `DECIMAL(14,3)` with at most the type's decimals.
  - **Readings** (S039): per node and meter, the time taken to the minute and at most **7 days back for everyone** (a departure from S028's `backdate_days`, chosen by the user); a gauge outside its limits and a Yes / No answer other than the expected one are saved and marked (*High*, *Low*, *Not OK*); **only `equipment:edit` holders remove a reading** (engineer, manager, IT admin), never edit it in place.
  - **Built (S039, 24-10-2026):** migration v32 (`meter_readings`); on the equipment page's *Meters* card each meter shows its last reading ("12,345.6 h · 23-10-2026 18:00", Indian grouping, with a *High* / *Low* / *Not OK* mark), which opens its *History* (30 a page, *Show more*); *Log reading* (`reading:log`) takes the value (a Yes / No meter: two large *Yes* / *No* buttons, then *Save*), *Time of reading* ("Now" is the server's clock), *Meter reset* on a counter, and a note. A counter reading may not be lower than the active reading before it in time, nor higher than the one after it (unless that one is a reset); a reset may not be higher than the one before; equal values pass; two active readings of one meter at one minute are refused. The "lower" refusal carries the code `counter_lower`, by which a screen offers the *Meter reset* tick. An amount is 0 or more with no order; a gauge stores *low* / *high* against the limits in force when saved, a Yes / No meter *not OK* (stored as 1 / 0). A removed reading is hidden with who and when, and no longer counts; a reset with a later reading cannot be removed. `GET/POST /api/equipment/<id>/readings`, `DELETE /api/equipment/<id>/readings/<reading_id>`; the node's meters list carries each meter's `last`. Every reading write takes the node lock first, then reads plainly. **Time field (S051, 25-10-2026):** *Time of reading* shows the time with a *Now* tick; see the S040 line below.
  - **The end-of-day sheet** (S040): one sheet per **site**, grouped by unit, saved row by row through the same rules; out-of-use machines folded away; meters read today marked.
  - **Built (S040, 24-10-2026):** the *Readings* page (`/readings`, nav item after *Tickets*, `reading:log`; the storekeeper and IT admin do not see it). `GET /api/readings/sheet?site_id=` gives the site's active units where the user logs (`accessible_unit_ids(cur, "reading:log")`; 404 for an unknown, inactive or foreign site, admin too), each with the machines that have meters in force on the machine or a part (not scrapped; tree order; parts nested), each meter with its last reading; a few queries for the whole site, none per node. `GET /api/equipment/my-units` gains `reading_unit_ids` (null = every unit), from which the screen builds the site picker (shown only to a user who logs at several sites; the last site is remembered in the browser under `yantra.readings.site_id`). One *Time of reading* for the sheet ("Now" sends no time). One card per machine with its parts' meters as titled blocks; a Yes / No meter is two large buttons (pick, then save); a meter read today reads "Today 17:50 · 12,345.6 h" with a tick, and the header counts "9 of 48 read today". *Save readings* (a sticky bar above the bottom nav on a phone) posts each filled row in turn with S039's POST: a refusal shows on its row and the others go on; a 502 / 503 / 504 or no answer stops the loop and the remaining rows read "Not saved. Try again in a minute." with their values kept; a refused *Time of reading* (it is the sheet's) shows once on that field and stops the loop. Switching the site with typed readings asks first ("Discard 3 typed readings?"), and the picker waits while a save runs. The *Meter reset* tick appears on a counter row only after the `counter_lower` refusal. A saved row is read-only; *Undo* (S039's remove route) shows only for `equipment:edit` holders at the row's unit; for others one line, "A wrong reading is removed by an engineer. Ask one.", shows after the first save. Machines out of use sit behind *Show out of use* at the end of each unit. After a full save the round is read-only (rows and *Time of reading*), the button reads *Saved* and is disabled, and *Enter more readings* starts a new round (rows empty, time now, last readings reloaded); a partial save keeps the refused rows editable, and *Enter more readings* shows there too once no filled row is left to retry (A1, 25-10-2026). No migration. **Time field (S051, 25-10-2026):** the shared time field shows the date and time at once, with a *Now* tick to its right: ticked, it is read-only and follows the phone's clock (every 30 s) while the server's clock still decides; unticked, it is editable.
  - **Built (S050, 25-10-2026):** the *Readings* page has two tabs, *Sheet* (S040's sheet, the default for `reading:log` holders) and *Register*; the tab is in the URL (`?tab=register`). The page opens to every `equipment:read` holder: the storekeeper and IT admin see only *Register*, with no tab bar, and a typed `?tab=sheet` opens *Register* for them (a departure from S040, where they did not see the page). Each tab mounts the first time it shows and then stays mounted, so readings typed on the sheet survive a look at the register. *Register* shows every active reading of one node (equipment, component-unit or component): the node is found with the raise screen's equipment search (*Which equipment?*, now the shared `EquipmentPicker.vue`) or opened from *Open register* on the *Meters* card (shown while the node has a meter in force); then a node card (the name with an X beside it, *Clear and choose another*, and *Open equipment page*), *Meters: All* with a check box per meter (one, some or all; the last tick cannot be cleared; the choice in the URL as `&meters=3,7`), and the table: a row per exact minute, newest first, 30 a page with *Show more*; a column per meter in the *Meters* card's order headed "Run hours (h)", then meters no longer on the node that have active readings ("No longer on this machine"); cells hold the number only, Indian grouping, with *High* / *Low* / *Not OK* / *Reset*. On a phone the time column stays fixed and the meter columns scroll sideways inside the table's frame. Removed readings and who logged a reading stay in the per-meter *History*. `GET /api/equipment/<id>/readings/register?meter_type_ids=&page=&per_page=` (`equipment:read`; ids that are not a column are ignored, the answer's `shown` lists the ones used; a malformed list is 400). Read-only; no migration.
  - **Built (S052, 25-10-2026):** the ticket page has a *Meters* card after *Details*, *Times* and *Assigned*: one heading per node of the path from the ticket's machine down to its part (machine → component-unit → component) that has a meter in force, each with *Open register* (S050's register for that node). Each meter shows the last active reading taken **at or before the ticket's time** (*When it happened*), never a later one, with its marks and its age ("23-10-2026 06:00 · 8 h before"; "at that time" in the same minute), or "No reading before this time"; a gauge marked *High* / *Low* or a Yes / No *Not OK* in the 7 days before (`MARK_WINDOW_DAYS`, the window (at − 7 d, at]) gets a warning line ("High or Low 3 times in the 7 days before"). On every ticket, defects too. The card draws nothing while loading and is hidden when no node has a meter; a part moved to another machine since the raise is left out, and a reader who sees the ticket only through its own unit (the machine moved to a unit outside theirs) gets no card. Worked out on each view, nothing stored: `GET /api/tickets/<id>/meters` (`ticket:read`; the path checked under `equipment:read`), plain reads, no migration. Saving the run hours at failure for MTBF in operating units (ISO 14224, SMRP 3.5.1) waits for the KPI work (phase 5).
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
  records, never written a second time. The *Me* page's *My activity* tab (S031) is the
  per-person on-screen view of the ticket part of this log; the printed report stays phase 5.
- **Waiting versus repair:** downtime split by waiting reason (§ 4.2).
- Export to Excel for each report.
- Tickets closed as frivolous are excluded from downtime and MTBF/MTTR (Proposed — confirm before phase 5).

### 4.7 Notifications

| Event | Web push | Telegram | Email |
|---|---|---|---|
| New breakdown | engineers, the unit's supervisor, maintenance manager (S021) | maintenance group | |
| New defect | engineers, quietly (S021) | | |
| Machine down again (sent back with the machine down) | as a new breakdown, no escalation (S021) | | |
| Breakdown not acknowledged in time | engineers and managers, once (S021) | maintenance group | |
| Job assigned to you | the person assigned by an engineer, not on taking a ticket oneself (S021 A1) | | |
| Ticket closed (close or not a fault) | | | the site's managers covering the unit, not the closer; not for a close dated over 7 days back (S032) |
| PM job due / overdue | assigned technician | maintenance group (overdue only) | |
| Reading out of limits | engineers | | |
| Daily summary (open tickets, overdue PMs, yesterday's downtime and work done) | | | engineers, manager |

- **Web push:** Yantra is installable as a PWA; push uses the browser's Web Push (VAPID keys, no third party).
- **Telegram:** the base pattern — group-routed, sent from the job queue. **Parked 21-10-2026** (user: "for now, its PWA alone"): web push is the only channel until push has run on the real phones; the design is kept in `docs/steps/S023-alerts-telegram/1-brief.md`.
- **Email** (S032, 23-10-2026): Mailgun over SMTP (`smtplib`, STARTTLS), from the job queue, plain text, one email per recipient. Addresses come from the Keycloak login token, copied onto the Team record at each login; nobody types one in Yantra. Office 365 (Microsoft Graph) was rejected: it refuses basic SMTP login.
- All sends go through the DB-backed job queue, so a slow channel never blocks a request.

## 5. Data model

Moved to [`schema.md`](schema.md) (23-10-2026): what each table holds, the
built and the planned tables, and the relationship diagram (also
[`schema.html`](schema.html), to open in a browser).

## 6. Screens

**Phone (operator, technician):**

- *Me* (S031): open work assigned to me, tickets I raised, my activity; PM jobs due and CIL jobs join *Open work* in phase 4; first in the nav and the landing page for roles with `ticket:read` (S035, 24-10-2026; S031 U1 had kept Equipment).
- Equipment page (from QR): status, open tickets, due PMs; buttons "raise breakdown", "log reading", "start CIL" (before-use equipment).
- *Readings* (S040, 24-10-2026; S050, 25-10-2026): fourth in the nav for every role with `equipment:read` (*Me*, *Equipment*, *Tickets*, *Readings*, *Masters*, *Settings*). Two tabs: *Sheet*, the end-of-day sheet for roles with `reading:log` (one site, every meter grouped by unit, *Save readings* in a bar above the bottom nav), and *Register*, every reading of one node as a table (the only tab for the storekeeper and IT admin) (§ 4.5).
- Raise breakdown or defect: equipment, intensity (critical = breakdown, else defect), symptom, remark, photo — four taps for the common case.
- Ticket: timeline, act on the next step, add photos, labour.
- Every form (dialogs and the *Raise ticket* page): a refused save scrolls to the first message and puts the cursor in its field, so a refusal is never out of sight on a phone (S026, 22-10-2026; `SMTW-WebApp-Base.md` § Form / Modal Pattern).
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
| aibots (later) | Reasoning over Yantra's history and plant-3i's data: forecasts from reading trends and failure history (predictive maintenance), remote-monitoring alerts, and later ad-hoc questions over the records. Bots never talk to devices (the aibots boundary rule: plant-3i acquires, aibots reasons and communicates) | read / receive |
| VelKilnMaster (later) | Kiln sensors flagged as needing maintenance, via the shared ticket API (§ 4.2) | receive |
| VELVaahanMaster (later, *Proposed* 20-10-2026) | Vaahan is the **vehicle master**; Yantra holds each vehicle as equipment with only its maintenance identity (code, name, class and type, unit, registration number as serial, model), loaded once by hand (40 rows, little churn) and then kept in step by a scheduled read-only sync keyed on the registration number, like the OneERP warehouse sync (Vaahan is live and used daily, so the sync is worth building; Vaahan's own maintenance-report doctype is frozen, not grown, once Yantra holds the work). Odometer readings from trips and refuelling into the vehicle's km meter (reading source `vaahan`), so PM by km needs no retyping; until then the inspector types the odo. Vaahan's maintenance report carries the Yantra ticket number (Q25) | read |

## 8. Build phases

Each phase ends usable on its own.

1. **Foundation** — app skeleton per the base: Keycloak login, roles and RBAC, internet exposure (real client IP, network gate, access log), migrations, job queue, version endpoint and stale-bundle check, PWA shell. Deployment in `smtw_erp_devops/erp_server/yantra/` via `erp_spanner.py` (add `yantra` to its known apps; Yantra migrates its DB at startup, so `erp_spanner migrate` is not used), first deploy to customer7:8990.
2. **Equipment register** — sites and units, users' unit access, equipment classes, equipment tree, documents, QR labels. Lets the team load the equipment list.
3. **Breakdowns and defects** — the full ticket flow for both (decided 18-10-2026), deferred work, codes, labour, photos, Telegram + web push for new tickets and escalation. First module the shop floor uses. *Proposed* (16-10-2026): the **pressing shops** (SMTW and SSVT) as the pilot, since press availability is the plant's worst loss and its diagnosis bottleneck is what the diagnostic procedures address.
4. **Meters, PM and CIL** — the PM engine (decided 18-10-2026: phase 4, after tickets; daily inspection is a CIL / PM plan and its Not OK items raise defect tickets, so tickets come first): meters and readings, PM templates and plans with checklists and readings, calendar / meter / before-use triggers, PM and CIL jobs, verification.
5. **History, reports, daily email** — history card, downtime, MTBF/MTTR, PM compliance, reading trends, Excel export, daily summary.
6. **OneERP warehouse sync** — unit mapping from OneERP (can move earlier if wanted; it is independent).

**Later rungs** (decided 18-10-2026, not phases of v1): **predictive maintenance,
digital twins and remote monitoring**, built with the sister repos and not
inside Yantra alone. plant-3i runs the digital twins (press today; extruder and
compressor twins to follow) and feeds readings and malfunction flags (§ 7);
aibots reasons over Yantra's coded history and plant-3i's data and sends the
alerts; Yantra stays the register, the failure history and the readings with
limits. The order is fixed by the maturity ladder (Maintenance-Philosophy § 8):
these rungs need a year of coded tickets and readings first.

## 9. Open questions

1. ~~**Keycloak roles:** realm or client roles?~~ Decided 12-10-2026: client roles of `vel-yantra-master` (`maint_operator`, `maint_technician`, `maint_engineer`, `maint_manager`, `maint_storekeeper`, `it_admin`). **Superseded 16-10-2026 (S011):** Keycloak keeps `maintenance_team` and `it_admin`; the maintenance roles are held in Yantra per site.
2. ~~**Escalation times:**~~ Decided 21-10-2026 (S021): an unacknowledged breakdown escalates after **A 10, B 30, C 60 minutes**, once, to the unit's engineers and managers; the times are settings (Settings › Notifications), not code.
3. ~~**Equipment codes**~~ Decided 13-10-2026: class prefix of 2–4 letters + 3-digit number (`VBM001`), growing to 4 digits past 999; one counter per prefix across all sites, so a code survives a move.
4. ~~**Downtime definition**~~ Decided 15-10-2026: downtime ends at the technician's **"back in service"** (SMRP: repair time runs to restoration). "Not fixed" is a **new ticket** linked to the old one, not a reopen (decided 20-10-2026, S017/S018). S018 computes downtime from the events to back in service, and repair time as the time in progress (EN 13306 active corrective maintenance time).
5. ~~**Failure coding**~~ Decided 15-10-2026: the **ISO 14224 core** — failure **mode** (the operator picks it as the symptom), failure **cause** and maintenance **action** (technician/engineer), with lists trimmed from ISO 14224 Annex B and maintained by engineers. Mechanism is left out for now; detection method is filled automatically from the ticket's source (§ 4.2). Mode lists may later be scoped by equipment class. *Scoped by class (one class or General) from S016, approved 20-10-2026.*
6. ~~**Template edits:**~~ Decided 27-10-2026 (R03 Q8.1): plans keep their copy; *Update plans* sends a template change to the plans the engineer ticks.
7. ~~**Unit access upkeep**~~ Decided 13-10-2026: IT admin maintains users' unit lists (and sites and units) — `masters:edit`.
8. ~~**CIL shifts**~~ Superseded: CIL is per equipment, before use or by frequency (§ 4.4); missed before-use detection is deferred.
9. ~~**Intensity scale**~~ Decided 15-10-2026: **critical / degraded / initial** — ISO 14224's failure impact, with the plain word *initial* for the standard's *incipient*.
10. ~~**CIL verification:**~~ Decided 27-10-2026 (R03 Q5.1): a needs-verification flag per plan, default yes for maintenance plans and no for CIL.
12. **Closing discipline** (*Proposed*, 16-10-2026): the engineer codes cause and action from the technician's verbal report after the fact. TPM practice is to close within the shift; tickets back in service but not closed by end of shift should show on the engineer's dashboard. No extra approval step.
13. ~~**Deferred work**~~ Decided 21-10-2026 (S019, § 4.2): scheduled state with planned date and waiting reason, the waiting split, planned downtime. Meter-value targets wait for phase 4.
14. ~~**PM rescheduling**~~ Decided 27-10-2026 (R03 Q9.1, Q9.2; item R03.9): the engineer reschedules with a reason, and the job is on time against the new date (reschedules counted); a skip with a reason counts as not done.
15. **Diagnostic procedures on tickets** (*Proposed*, 16-10-2026, § 4.2): per class and symptom, steps as checklist and reading items. Which phase: with breakdowns (3) or with PM items (4)? Folded into the **Procedures** master (§ 4.3a) as kind *diagnostic*. 20-10-2026: any kind attaches to a ticket; item types settled in § 4.3; phase 4.
17. **Document kinds and missing-drawings list** (*Proposed*, 16-10-2026, § 4.1): a small change to S006; which step carries it?
18. **Maintenance strategy field, fitness-for-use inspection, verification rounds** (*Proposed*, 16-10-2026, § 4.1, § 4.3): the answer to forgotten machines.
19. **Onboarding procedures and completion records** (*Proposed*, 16-10-2026, § 4.3a).
20. **Certification plans with valid-until and the compliance register** (*Proposed*, 17-10-2026, § 4.3): statutory examinations and extinguishers. Goes to the follow-on roadmap R04 (R03 Q0.1, 27-10-2026), started after R03.8.
21. ~~**Parts-used line on tickets and jobs**~~ Decided 21-10-2026 for tickets (S020, § 4.2); PM jobs' parts and labour: R03.11 (R03 Q11.1, 27-10-2026).
22. ~~**PM routes**~~ Decided 27-10-2026: item R03.15; the genset round pilots it (R03 Q15.1).
23. **Work done without a ticket** (*Decided* 20-10-2026, S018 A1, § 4.2): *Already fixed* on the raise screen records raise and back in service in one save; closing stays the engineer's. No separate screen.
24. **Calibration** (*Proposed*, 20-10-2026, § 4.3): measuring-instrument class with required accuracy, calibration class and custodian; certification plans per instrument; in-house verification plans with error readings and the out-of-tolerance ticket. Phase 4, after certification plans (Q20). ISO 9001 § 7.1.5. Goes to the follow-on roadmap R04 (R03 Q0.1, 27-10-2026), started after R03.8.
25. **Fleet and Vaahan** (*Proposed*, 20-10-2026, § 4.1, § 4.3, § 7): no step of its own; vehicles ride on S017/S018 (tickets), S019 (deferred work) and the route step. Vaahan is live and used daily (20-10-2026), so its maintenance-report doctype is to be frozen, not grown, and the vehicle sync and odometer feed are worth building. To settle: the vehicle list and types to load by hand first; which phase builds the sync and the odometer feed (alongside the OneERP sync, phase 6, or earlier with PM by km in phase 4); whether the fleet is the route pilot.
16. **Die tracking** (*Proposed*, 16-10-2026, § 4.1): counter snapshot on fit / removal and a die-centred history, ahead of the rotables design.
11. ~~**Kiosks.**~~ Decided 13-10-2026: not in v1; not tied to a unit; operators are Keycloak local users with passwords; logout manual or on inactivity; no supervisor role (superseded 16-10-2026 by S011 A1: `maint_supervisor`, production-side); resets by IT in Keycloak (Decisions table, § 3).
