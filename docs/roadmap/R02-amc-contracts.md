```
Roadmap: R02 — Annual maintenance contracts (AMC)
Doc: roadmap
Author: Roadmapper (Opus)
Date: 30-10-2026
Status: Approved (gate R, 27-10-2026, by KLA; re-plan of 30-10-2026, the vendor master, approved 30-10-2026 by KLA: Q9.1 a, Q9.2 a plus a phone, Q9.3 a, Q9.4 a, Q9.5 a)
```

# R02 — Annual maintenance contracts (AMC)

**The point:** Yantra gets a **vendor master** and a **contract register**. The vendor master
(R02.9, new, built first) lists the outside firms once; a contractor's Team record may name its
vendor. The register holds, per vendor contract, the period, the equipment covered, what is
covered, the PM visits agreed and the cost. The roadmap now has **nine items**: seven can be
built now, two wait for the PM module (Plan.MD § 4.3, build phase 4). The first useful result is
**R02.9, R02.1 and R02.2**: the vendors, the register, and an *Under contract* card on every
covered machine. Breakdown calls come from the tickets (R02.6), never typed twice. The re-plan
adds **D11** (KLA, 30-10-2026) and **five new questions** (Q9.1–Q9.5); it supersedes Q1.6.

## The feature

**What KLA asked (27-10-2026, verbatim):** "we need to plan being able to track annual
maintenance contracts. contract details: from, to, what equipment, what is covered, number of
pm visits agreed, cost. actual visits and maintenance done, breakdown visits if any".

**What KLA asked (30-10-2026, verbatim):** "in road map for AMC, there is no vendor master
better to have it from the start  a vendor 's employee in teams table can be linked to this
(may be  it not  mandatory)". Then: "yes, re-plan R02 with the vendor master".

**Why (fact):** important equipment is under AMC (Plant-Facts § 4, 13-10-2026). The vendors
known so far are Atlas Copco (the two screw compressors of the extrusion line), Toyota Material
Handling (the electric pallet truck) and Sartorius (the moisture analyser, on call); the
contracts read on 27-10-2026 add Fuji Electric (UPS and harmonic filter) and VP Power Systems
(servo stabiliser and UPS). A packing-machine AMC technician also visits (the daily report of
09-10-2026). Today nobody can see in one place which machine is under which contract, until
when, and whether the vendor did the visits paid for. Plan.MD § 2 parked the register as "a
later master" (16-10-2026), with the terms in the equipment's notes meanwhile. ISO 55001 asks
that outsourced maintenance be controlled, and ISO 9001 § 8.4 that each outside provider's
performance be checked (§ Standards). A check per provider needs one record per provider: the
vendor master.

**Decided by KLA** (the orchestrator records them in Plan.MD at gate R):

| # | Decision | What it means for the roadmap |
|---|---|---|
| D1 | **A roadmap, not one step.** | This file. |
| D2 | **PM visits wait for PM.** No stand-alone visit log. | The vendor's agreed visits become PM plans, and the actual visits PM jobs. The plan's assignee is a Team record **linked to the contract's vendor** (D11; was "the vendor, a contractor in Team"; Plan.MD § 4.3, *Performer*). The register holds now what PM needs later: **PM visits agreed per year** on the contract. Later a PM plan points at its contract, and compliance is jobs done against visits agreed (R02.7). |
| D3 | **Breakdown visits stay on tickets.** | A vendor's breakdown call is a ticket assigned to a Team record **linked to the vendor** (D11; S018: `ticket_assignees`, `ticket_labour`). The contract page lists the tickets on its equipment, in its period, that such a record worked on: derived, not re-entered (R02.6). Downtime, MTTR and the failure codes stay in one place. |
| D4 | **Contract cost is stored**, seen by managers, `contract:read_senior` (D5). | **A deliberate departure from Plan.MD § 2**, "Maintenance cost — not in v1". Recorded in Plan.MD at gate R, 27-10-2026. |
| D5 | **Two read keys** (KLA, 27-10-2026, at gate R; replaces "managers and admin only"). | `contract:read_basic`, same holders as `equipment:read` (`("*",)`, site-scoped): **every field except the price, the cost note and the documents** (vendor, type, contract number, from and to, status, coverage ticks and text, PM visits, response time, notes, machines, breakdown calls). `contract:read_senior`, **managers** of the contract's site (admin by the bypass; IT admin not): adds **the price, the cost note and every attached document** (a quote or signed contract shows the price, so all documents sit here). D10 adds a middle key, `contract:read` (engineers and managers), for the call-out number. Answers Q1.2 and Q3.1. |
| D6 | **Renewal makes a new record linked to the old one** (Q4.1 a, KLA, 27-10-2026). | Each year keeps its terms, cost and breakdown calls (R02.4). |
| D7 | **One coverage per contract; a mixed quote becomes two contracts** (KLA, 27-10-2026, after the real documents). | Fuji's quote `AMC14082369550-R` holds a comprehensive AMC (UPS) and a labour AMC (harmonic filter): entered as two contracts with the same vendor (one `vendors` row, D11) and contract number, the quote attached to both. The design stays: coverage on the contract. |
| D8 | **The price is per machine** (replaces Q1.7 a). | Every quote prices each machine (VP Power ₹9,000 / ₹4,900; Toyota ₹18,040 a truck; Fuji ₹9,809 / ₹28,028). An optional price, before GST, on each machine line (`contract_equipment`, R02.2), seen and entered only by `contract:read_senior`; the contract's total is their sum, never typed. So the price lands with R02.2, and R02.1 holds the cost note only. Cost per machine-year (R02.8) is then exact. |
| D9 | **"Only the vendor may repair" tick.** | Fuji (annexure § 1 A i) and Toyota (terms 7) end the contract if anyone else repairs or tampers with the machine. A tick on the contract; when set, the machine card shows, in a warning colour, "Do not repair. Call the engineer; the vendor repairs this machine." |
| D10 | **Call-out number, for engineers, managers and admin** (KLA, 27-10-2026). | A *Call-out number* on the contract (the vendor's breakdown line, e.g. VP Power's 24-hour number). Read with a third key, **`contract:read`**, held by **engineers and managers** of the contract's site (admin by the bypass); shown to them on the contract page and the machine card. Everyone else sees "Call the engineer". So D5's two keys become three, which is CLAUDE-COMMON § RBAC Pattern's three-level read hierarchy: `read_basic` (all but price, documents and the call-out number), `read` (adds the call-out number), `read_senior` (adds the price, the cost note and the documents). A firm's service number, kept in the database only; never in the repo (no real numbers in tests or docs). It stays on the contract, not on the vendor (Q9.2). |
| D11 | **A vendor master from the start; a Team record may be linked to its vendor** (KLA, 30-10-2026). | A new item, **R02.9**, built first: a `vendors` table shared by all sites, a *Vendors* tab in Masters, and an optional *Vendor* on a contractor's Team record (`people.vendor_id`). The contract's vendor is a `vendors` row (R02.1). Breakdown calls and PM visits are matched through the link (R02.6, R02.7). **Supersedes Q1.6 a** (one Team record per firm as the vendor) and the line "no vendor master apart from Team". |

**Plan.MD changes for the orchestrator at gate R** (this re-plan; the 27-10-2026 wording is
already in Plan.MD § 2 *In v1* item 9):
- § 2 *In v1* item 9: replace "vendor (one Team record per firm, employment *contractor*)" with
  "vendor (from the *Vendors* master in Masters, shared by all sites; a contractor's Team record
  may name its vendor, optional)". Replace "Breakdown calls are the vendor's tickets (assignee or
  labour row)" with "Breakdown calls are the tickets on which a Team record linked to the vendor
  is an assignee or has a labour row". Replace "with the vendor as assignee" with "with a Team
  record linked to the vendor as assignee".
- § 4.3 *Performer*: "An **AMC vendor** is a contractor record in Team" becomes "An **AMC
  vendor** is a row of the *Vendors* master; its technician, or a service record such as
  'Atlas Copco service', is a contractor in Team linked to it and can be the plan's assignee
  (30-10-2026)".
- The Team description (§ 2 or § 3, where `people:edit` is described, Plan.MD line 162): a
  contractor may name its vendor.

**What it is not:** no purchase orders, invoices or payments (accounts keep them); no vendor
addresses or tax numbers (Q9.2: a phone only); no approved-vendor list or vendor rating (§ Out);
no visit log apart from PM jobs (D2).

## What exists

Checked against the code at HEAD `d216f48` (30-10-2026).

| What | State today | Evidence |
|---|---|---|
| Vendor as a Team record | **Built.** A Team record is a person or a contractor firm, with employment `direct` or `contractor`. **No link from a person to a firm**: the `people` columns are name, employment, username, active and who/when. | `masters_core.py:30` `EMPLOYMENT`; `local_db.py:214-225` (`people`); `docs/schema/notes.json` `people`. |
| Team dialog | **Built (S010, S011).** Name, *Employment* (Direct employee / Contractor), trades, login, sites and roles. `people:edit` (engineers, IT admin) edits; the person row is locked first. | `PeoplePanel.vue:405-470`; `masters.py:1288-1340` `update_person`; `config_rbac.py:171`. |
| A shared firm master | **Built for makers only (S012).** `manufacturers`: name (unique; the parser folds case and repeated spaces), active, who/when; no site. Read `masters:read` (everyone); edited with `equipment:edit` (engineers, so managers, and IT admin, at any site). Deactivating refuses while active models remain. The *Manufacturers* tab is the pattern R02.9 copies. | `local_db.py:170-179`; `masters.py:515-545`; `ManufacturersPanel.vue`; `masters_core.py:201` `_MANUFACTURER_FIELDS`. |
| Vendor on a ticket | **Built.** Assignees and labour rows name Team records. An assignee must hold a Technician, Engineer or Manager row at the ticket's site; a labour row may name anyone with a membership there. | `tickets.py:136` `ASSIGNEE_AT_SITE`; `config_rbac.py:64` `ASSIGNABLE_ROLES`. |
| Waiting on a vendor | **Built (S019).** A ticket in *scheduled* with the waiting reason *vendor* counts as EN 13306 logistic delay. | `tickets_core.py:320` `WAITING_REASONS["vendor"]`. |
| Documents | **Built (S006, S012, S017, S070, S075).** Five owners: equipment, model, ticket, countermeasure, one-point lesson; the owners are data in `documents.py` (`OWNERS`), and the CHECK counts one owner column per row. | `documents.py:180`; `file_store._OWNER_FOLDERS`; `local_db.py:1220-1223` (v38 widened the CHECK). The contract is a sixth owner (R02.3). |
| Equipment history | **Built (S002, S038, S044).** `equipment_events` takes new event kinds without a new table. | `docs/schema/notes.json` `equipment_events`. |
| Site-scoped keys | **Built (S011).** A key in `SITE_SCOPED` is checked at the record's site. | `config_rbac.py:196`. |
| Daily tasks, push and email | **Built (S013, S021, S032, S074).** `scheduled_tasks.SCHEDULE` (two entries), alert kinds and channels in `alerts_core.py`. | `scheduled_tasks.py:12-16`; `alerts_core.py:38` `KINDS`, `:58` `CHANNELS`. |
| Masters tabs | **Built.** Twelve sections in the level-2 toolbar, each shown by its key. | `frontend/src/views/MastersView.vue:28-39`. |
| Contract terms in notes | **Plan.MD § 2:** "In v1 the terms go in the equipment's notes." | No code; any such notes are moved by hand once R02.2 is live (§ Out of the roadmap). |
| PM plans and jobs | **Not built.** No PM tables; `docs/schema/notes.json` lists `pm_plans` and `pm_jobs` as planned. | `docs/schema/notes.json` `planned`. |
| Migrations | Latest **v41** (S075). `_PRECONDITIONS` has entries for v20, v25 and v34 only; a new table or a new NULL column carries none (v27's comment: "a new NULLable column needs no value from any existing row"). | `local_db.py:1354`, `:1478`, `:745`. |

**What no item rebuilds:** the Team register (a vendor's people stay Team records; R02.9 adds
one optional column), the masters pattern (`useMasterForm`, `FormModal`, `ActiveToggle`), ticket
assignees, labour and waiting reasons (the breakdown calls), the documents module (one more
owner), the equipment history (new event kinds), the worker and the alert channels (one more
kind).

## Standards

**How the numbers are marked.** ISO 55001 § 8.3 and ISO 9001 clauses that Plan.MD already cites
are given plain. The rest are marked *to verify*.

| Standard | What it says, in plain words | How R02 follows it | Items |
|---|---|---|---|
| **ISO 55001 § 8.3 Outsourcing** (cited in Plan.MD § 2; the 2024 edition's number *to verify*) | Work given to an outside firm stays the plant's responsibility. The plant decides what is outsourced, how it is controlled, and keeps the evidence. | The vendor master names each outside firm once. The register names, per machine, which vendor maintains it under which terms and until when; the vendor's work is recorded as tickets and PM jobs like the plant's own, by Team records linked to the vendor. | R02.9, R02.1, R02.2, R02.6, R02.7 |
| **ISO 9001:2015 § 8.4 Control of externally provided processes, products and services** (sub-clauses *to verify*) | Choose outside providers on criteria, check their performance, and keep records of it. Clause 8.4.3 says the agreement must state what is required. | The *Vendors* tab is the list of outside providers; R02.8 reports performance **per vendor** (all its contracts, all its people), which needs one record per provider. The contract records what is agreed (visits, coverage, response time). ISO 9001 is a future goal for the plant. | R02.9, R02.1, R02.8 |
| **ISO 9001:2015 § 7.5 Documented information** | Keep the records that show the work was done, protected from loss and change. | The signed contract is a document on the contract (R02.3); who changed a contract or a vendor and when is kept (who/when columns, R02.9, R02.1, R02.2). | R02.9, R02.1–R02.3 |
| **EN 13269 Maintenance — Guideline on preparation of maintenance contracts** (edition and content *to verify*) | A European guide to what a maintenance contract should state: scope, the equipment, the services, response times, what is excluded, how performance is measured. | The contract's fields follow that list: equipment, covered and not covered, PM visits, breakdown calls, response time. | R02.1 |
| **EN 13306 Maintenance terminology** | Names the kinds of maintenance: *preventive* (planned, before failure), *corrective* (after a failure), *deferred corrective*, and *logistic delay* (waiting for parts, a vendor or an expert). | The vendor's PM visits are preventive maintenance (PM jobs); breakdown calls are corrective maintenance (tickets); waiting for the vendor is logistic delay (S019). R02 adds no new kind. | R02.6, R02.7 |
| **ISO 14224 § 9 Maintenance data** (Table 8, "maintenance resources"; *to verify*) | Each maintenance event records who did it, including whether the work was done in-house or by a contractor. | Already recorded: the labour row names the Team record, whose employment is *contractor*. R02.9 adds which contractor firm. R02.6 reads it; nothing is typed again. | R02.9, R02.6 |
| **SMRP metrics** (metric numbers *to verify*) | *Contractor cost as a share of total maintenance cost*; *PM compliance* (jobs done on time against jobs due); *MTTR*. | R02.8 gives PM compliance per contract and per vendor, and MTTR of the covered machines. The contractor cost share needs the total maintenance cost, which Yantra does not record (Plan.MD § 2), so R02.8 shows only the contract cost per machine-year. | R02.8 |
| **TPM, planned maintenance pillar** | Planned maintenance covers all the work on a machine, whoever does it. An outside vendor's visits are planned and checked like the plant's own. | D2: the vendor's visits become PM plans with the vendor's Team record as performer, verified by the engineer. | R02.7 |
| **ISO/IEC 27001:2022 A.5.15 Access control, A.8.3 Information access restriction** (A.8.3 *to verify*) | People see only the information they need for their job. | The price and documents are behind `contract:read_senior`, managers at the contract's site and admin; the call-out number behind `contract:read`; the rest of the contract is `contract:read_basic` (D5, D10). A vendor holds only a phone (Q9.2), read as the brief decides (recommended: the editors, as D10). | R02.9, R02.1 |

## Showcase

**Who uses it, and what each can do (user stories):**

- **As a maintenance engineer**, I add each outside firm once in Masters › Vendors: Atlas
  Copco, Toyota Material Handling, Sartorius, Fuji Electric, VP Power Systems. I link the
  vendor's technician in Team, or a record such as "Atlas Copco service" when the firm sends a
  different person each time. I see at a glance which vendor has nobody linked.
- **As a maintenance manager**, I see every contract at my site with its status (*In force*,
  *Ends in 25 days*, *Ended*) and its cost. I get a reminder before a contract ends, so I renew
  it in time or let it go on purpose.
- **As a maintenance engineer**, I add a contract: I choose the vendor, the period, the machines
  it covers, what is covered and not covered, the PM visits per year and the response time. I
  attach the signed contract. When it ends, I *Renew* it, and the terms and machines carry
  over.
- **As a maintenance engineer**, I open a contract and see every breakdown call the vendor's
  people worked on in its period, with the downtime and the days waited for the vendor.
- **As a technician on the floor**, I open a machine from its QR label and see *Under AMC with
  Atlas Copco until 31-03-2027*, with the response time and what is covered. So I call the
  engineer instead of opening a machine under warranty.
- **As an operator**, I see the same line on the machine, so I know a vendor looks after it.
- **Later, with PM**: as an engineer, I see *4 visits agreed, 2 done, 1 due* on the contract,
  and the vendor's visit reports on the PM jobs.
- **Later, with reports**: as a manager, I see per vendor, across its contracts, the visits done
  against agreed and the breakdown calls, before the renewal talk.
- **As IT admin**, I keep the vendors and the register tidy (Q9.4, Q1.3) but do not see the cost
  (D4).

**Mock-ups** (`docs/roadmap/R02-mockups/`; the deck's order is in § Slides, which shows 06
first because R02.9 is built first):

| File | Screen | Viewport |
|---|---|---|
| `06-vendors-tab.html` | Masters › Vendors on a phone, with the people linked per vendor; below it, the Team dialog's *Vendor* field (R02.9) | phone |
| `01-contracts-list.html` | Masters › Contracts: the register, as a manager sees it | desktop |
| `02-contract-dialog.html` | *Add contract*: the dialog | desktop |
| `03-contract-page.html` | One contract: terms, cost, machines covered, documents, breakdown calls, PM visits (greyed: comes with PM) | desktop |
| `04-equipment-under-contract.html` | The equipment page on a phone, with the *Under contract* card | phone |
| `05-ticket-contract-hint.html` | A ticket on a covered machine, with the contract line and the vendor assigned | phone |

**Two mock-ups of 27-10-2026 still show the old vendor** (fact; this re-plan writes only 06):
`02-contract-dialog.html:49` says "A contractor in Team." under *Vendor* (now "Choose a vendor
from Vendors."), and `03-contract-page.html:59` shows "Atlas Copco (India) · contractor" (now
"Atlas Copco"). They are pictures of the idea; R02.1's brief uses the new wording.

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R02.9 | **Vendor master** (new, first): the `vendors` table, a *Vendors* tab in Masters, an optional *Vendor* on a contractor's Team record | M | full | — | → S079, 30-10-2026 |
| R02.1 | Contract register: the contract record (vendor from Vendors), the list in Masters › Contracts, the dialog, three keys, the cost note for managers | M | full | R02.9 | → S080, 30-10-2026 |
| R02.2 | Equipment covered: the contract page, its machines and their prices, the *Under contract* card on the equipment page, a list filter | M | full | R02.1 | → S081 + S082 (split at the card), 30-10-2026 |
| R02.3 | Contract documents: the signed contract and its annexures on the contract | S | full | R02.1 | → S083, 30-10-2026 |
| R02.4 | Renewal: *Renew* makes the next contract with the same terms and machines; the chain is kept | S | full | R02.2 | → S085, 30-10-2026 |
| R02.5 | Reminders before a contract ends: push and email | S–M | full | R02.1 | → S084, 30-10-2026 |
| R02.6 | Breakdown calls on the contract, derived from tickets through the vendor's linked Team records; the contract line on the ticket page | M | full | R02.2 (and R02.9's link) | → S086, 30-10-2026 |
| R02.7 | PM visits against the contract: PM plans point at their contract; agreed against done | M | full | R02.2 and the PM engine (phase 4) | open — **waits for PM** |
| R02.8 | Vendor performance report, per contract and per vendor: visits compliance, breakdown calls, waiting on the vendor, MTTR, cost per machine-year | M | full | R02.6, R02.7, reports (phase 5) | open — **waits for PM** |

R02.9 keeps the next free item number: items are never renumbered (README § Numbers), so the
new first item is .9 and is first in § Order.

### R02.9 — Vendor master (new, 30-10-2026)

- **Goal:** each outside firm the plant buys maintenance from is one record, named once, so a
  contract, a ticket and a report all point at the same vendor. KLA's "vendor master … from the
  start" (D11).
- **The record** (`vendors`, one migration, shared by all sites like `manufacturers`):
  - **Name** (required, up to 100, unique without regard to case or repeated spaces, as
    `manufacturers`; e.g. "Atlas Copco").
  - **Active** (a vendor is never deleted; one no longer used is set inactive).
  - **Note** (optional, up to 255; e.g. "Screw compressors, MCC2"). No email, address or
    tax number (Q9.2): the call-out number stays on the contract (D10); accounts keep the rest.
  - **Phone** (optional, KLA 30-10-2026, Q9.2 "a plus phone"): the firm's office number. Who
    reads it is settled in the step's brief (recommended: as D10, the holders of `equipment:edit`;
    the call-out number on the contract stays the breakdown line). A firm's number lives in the
    database only; never a real number in the repo.
  - Created and updated who and when.
- **The link on Team** (same migration): `people.vendor_id`, a NULL foreign key to `vendors`,
  and a CHECK that a person with a vendor is a *contractor*
  (`vendor_id IS NULL OR employment = 'contractor'`). **Optional**, as KLA asked: a contractor
  with no vendor (e.g. a casual fitter, a calibration agency for now) stays as it is.
  - **Why the link sits in R02.9, not R02.1:** it is the same concern (who the vendor is), it
    lets the plant link its people before the first contract, and it keeps R02.1 to the
    contract alone. R02.9 stays within the size rule: one new table, two screens (the *Vendors*
    tab and the Team dialog).
  - **Employment changes back to direct:** the dialog hides and clears *Vendor* when *Direct
    employee* is chosen, so the save sends no vendor. The API refuses a direct employee with a
    vendor ("A direct employee works for no vendor. Clear the vendor, then save."), and the
    CHECK holds it in the database. Proposed: refuse rather than clear silently in the API, so no
    link is lost without the user seeing it.
  - **Only active vendors are offered** for a new link; a person already linked to an inactive
    vendor keeps it and shows "(inactive)".
- **Deactivating a vendor with linked people:** allowed, and the links stay. The links are the
  history that R02.6 and R02.8 read: an old technician's tickets still count for the vendor's
  past contracts. This departs from the manufacturer pattern (which refuses while active models
  remain), because a vendor's people may still work on open tickets. From R02.1 on, an inactive
  vendor is not offered for a new contract; a contract keeps its vendor.
- **Lock order** (for the brief and `masters.py`'s LOCK ORDER note): a person write that sets
  a vendor locks the person, then reads the vendor row `LOCK IN SHARE MODE` to check it is
  active; a vendor update locks only its own row and counts nothing. No cycle.
- **Keys** (Q9.4, recommended): read `masters:read` (everyone, as every master); add and edit
  with `equipment:edit` at any site (engineers, so managers, and IT admin), as manufacturers.
  The link on a person is part of the person and uses `people:edit` (engineers and IT admin):
  the same people. No new key, so `test_role_matrix` gains no row.
- **Screens:**
  - A **Vendors** tab in Masters, before *Team* (mock-up 06): name with its note, **People**
    (the count of active Team records linked), status; *Add vendor*, *Edit*, *Show inactive*;
    one dialog (`FormModal.vue`, `useMasterForm`), as `ManufacturersPanel.vue`.
  - The **Team dialog** gets *Vendor (optional)*, shown only for a contractor; the Team list
    shows the vendor beside the *Contractor* badge ("Contractor · Atlas Copco").
- **Text on screen (scope B):** button *Add vendor*; field help "The firm, as it should always
  be spelled, e.g. Atlas Copco."; refusal "A vendor with this name exists. Use that one, or
  enter a different name."; Team help "The firm this contractor works for. Their tickets then
  count as the vendor's breakdown calls on its contracts."; empty state "No vendors yet. Add
  the first one with *Add vendor*."; under the table "A vendor with no people cannot be
  assigned to tickets. Link one in Team."
- **Migration:** one, the next free version (v42 at HEAD `d216f48`): `CREATE TABLE vendors`,
  `ALTER TABLE people ADD COLUMN vendor_id INT NULL`, its FK, an index, and the CHECK, each
  written to re-run safely (`IF NOT EXISTS`, as v38). **No `_PRECONDITIONS` entry** (checked
  against `local_db.py`): no existing row changes; the new column is NULL on every row, which
  passes the FK and the CHECK; the existing entries (v20, v25, v34) guard renames and seeds,
  which this has none of. The upgrade test (`test_migration_*`) and `conftest.py` `_TABLES` get
  the new table.
- **Track: full.** It fails two light criteria: it has a migration, and it adds a locking rule
  (person → vendor). It is otherwise small (about 15 files: migration, `masters.py`,
  `masters_core.py`, the store, `VendorsPanel.vue`, `MastersView.vue`, `PeoplePanel.vue`, their
  tests, the `masters` browser spec, `docs/schema/notes.json`, Plant-Facts).
- **Docs due:** `docs/schema/notes.json` (a `vendors` line; the `people` line names the link),
  then `tooling\schema-docs.bat write`; Plant-Facts § 4 records the five vendors (names and
  what they maintain only; no numbers or addresses); Plan.MD only if the step departs from the
  gate-R wording.
- **After it:** the plant has one list of its outside firms, and each vendor's people are
  marked as such in Team. Usable alone: the Team list shows who works for which firm.
- **Leaves for later:** contract counts per vendor on the tab (R02.1 may add a column); an
  approved-vendor status and rating (§ Out).

### R02.1 — Contract register

- **Goal:** one record per vendor contract, listed with its status, so the plant knows what
  it has bought and until when. The fields KLA named: from, to, what is covered, PM visits
  agreed, cost.
- **The record** (`contracts`, one migration):
  - **Site** (required; Q1.5). The contract's keys are checked here.
  - **Vendor**: an active row of `vendors` (R02.9, D11; was a Team record, Q1.6, superseded).
  - **Type**: Warranty / AMC / CMC / On call (Q1.1).
  - **Title** (e.g. "Atlas Copco AMC 2026–27") and the vendor's **contract number**.
  - **From** and **To** (dates, DD-MM-YYYY; To on or after From).
  - **What is covered** (Q1.4 b): ticks for *Labour*, *Spare parts*, *Consumables* (oil,
    filters), and *Breakdown calls* (included, or a number per year); a free-text **Covered**
    and **Not covered** (up to 1,000 characters each).
  - **PM visits per year** (whole number, 0–52, may be empty) — the field PM reads later (D2).
  - **Response time** in hours (may be empty).
  - **Cost note** — only for `contract:read_senior` holders (D5). The price itself is per
    machine and lands with R02.2 (D8). An editor's save without `read_senior` leaves it as it
    was; the API never sends it to anyone else.
  - **Only the vendor may repair** (tick, D9) and a **Call-out number** (D10).
  - **Renewal of** (the earlier contract; empty here, filled by R02.4).
  - Notes; created and updated who and when.
- **Status** is derived from the dates, never stored: *Starts on …*, *In force*, *Ends in N
  days* (within the reminder window, R02.5), *Ended*. A contract is never deleted; one
  entered by mistake is set inactive.
- **Keys** (all site-scoped, added to `SITE_SCOPED`; holders: Q1.2, Q1.3):
  `contract:read_basic` (as `equipment:read`: all but price, documents and call-out number),
  `contract:read` (engineers and managers: the call-out number, D10), `contract:read_senior`
  (managers: price and documents), `contract:edit` (D5; admin by the bypass).
- **Screens:** a **Contracts** tab in Masters (Q1.8): a table with type, title, vendor, site,
  from, to, status badge, and cost for senior holders; filters site, type, status, vendor;
  *Add contract* and *Edit* open one dialog (`FormModal.vue`), whose *Vendor* lists the active
  vendors.
- **Text on screen (scope B):** button *Add contract*; status badges *In force*, *Ends in 25
  days*, *Ended*, *Starts on 01-04-2027*; field help "Choose a vendor from Vendors."; refusals
  "Choose a vendor. The list holds the active vendors of Masters › Vendors." and "Enter a To
  date on or after the From date."; empty state "No contracts yet. Add the first one with *Add
  contract*."
- **After it:** the manager sees every contract at the site, its vendor, its end date and its
  cost.
- **Migrations:** one (`contracts`, with an FK to `vendors`). **Leaves for later:** the machines
  (R02.2), documents (R02.3), renewal (R02.4), reminders (R02.5).

### R02.2 — Equipment covered

- **Goal:** each contract names its machines, and each machine shows its contract. This is
  KLA's "what equipment".
- **What changes:**
  - `contract_equipment` (one migration): contract → equipment node, with an optional
    **price** before GST (D8; `contract:read_senior` only; the contract's total is the sum).
    Nodes of the contract's site only; any level (Q2.1 a). One node may be in two contracts at
    once (Q2.2 a).
  - A **contract page** (`/contracts/:id`): the terms, the cost (senior holders), the machines
    covered (*Add machines* with the equipment picker, *Remove*), and the cards that later
    items fill (documents, breakdown calls, PM visits).
  - Each add and remove writes a line in the machine's history (`equipment_events`, new kinds
    `contract_added` and `contract_removed`), so the machine's card shows when it came under
    which contract (ISO 9001 § 7.5).
  - **The equipment page** gets an *Under contract* card, after *Open tickets*: per contract
    in force on the node or its ancestors, "Under AMC with Atlas Copco until 31-03-2027", the
    response time, the coverage ticks, the call-out number for `contract:read` holders (D10;
    others see "Call the engineer"), the warning "Do not repair. Call the engineer; the vendor
    repairs this machine." when the contract has the D9 tick, and a link to the contract for
    `contract:read_basic` holders. A contract that ended in the last 90 days shows as "AMC with
    … ended on …".
  - **The equipment list** gets a filter *Contract: Any / Under contract / Not under
    contract*.
- **Text on screen (scope B):** "Under AMC with Atlas Copco until 31-03-2027"; "Response time:
  24 hours"; "Covered: labour, breakdown calls. Not covered: spare parts."; "No contract on
  this machine." (shown only to editors, so others see no empty card).
- **After it:** a technician scanning a QR label sees at once that a vendor looks after the
  machine and what is covered.
- **Migrations:** one (`contract_equipment`). **Leaves for later:** the printed asset list's
  contract column (not proposed).

### R02.3 — Contract documents

- **Goal:** the signed contract, its scope annexure and the vendor's quote live on the
  contract, behind the contract's keys.
- **What changes:** a **sixth** owner in `documents.py` (`OWNERS`; five today since S070 and
  S075), with `contract:read_senior` to read and `contract:edit` to write; a folder in
  `file_store._OWNER_FOLDERS`; `equipment_documents.contract_id` and the owner CHECK widened to
  six (one migration; no rows change and every row still has exactly one owner, so no
  `_PRECONDITIONS` entry, as v38). The removed-documents purge (S008) lists contract documents
  too.
- **Note:** documents read with `contract:read_senior` (managers, D5), so quotes and invoices may
  be attached; a `contract:read_basic` holder sees no documents. Write needs `contract:edit`;
  whether an editor without `read_senior` may upload (and then not see the file) is for the
  brief.
- **After it:** the engineer finds the contract from a phone when the vendor disputes what is
  covered.
- **Migrations:** one (column and CHECK). **Leaves for later:** none.

### R02.4 — Renewal

- **Goal:** renewing a contract takes one action, and the history of earlier contracts stays.
- **What changes:** *Renew* on a contract opens the dialog filled with its terms and vendor,
  From = the day after its To, To = one year later, prices empty (managers fill them). Saving
  creates a new contract with *Renewal of* = the old one and copies its machines. The old
  contract stays as it was, read-only once ended. The contract page shows the chain ("Renews:
  Atlas Copco AMC 2025–26"). An inactive vendor is refused on renewal ("Atlas Copco is
  inactive. Make it active in Masters › Vendors, or choose another vendor.").
- **After it:** each year's terms, cost and breakdown calls stay comparable, year by year (D6).
- **Migrations:** none (the column is in R02.1). **Leaves for later:** none.

### R02.5 — Reminders before a contract ends

- **Goal:** no contract ends unnoticed.
- **What changes:** a daily task in `scheduled_tasks.SCHEDULE` finds contracts whose To date
  is 60 or 15 days away (Q5.1 a) and that have no renewal yet. A new alert kind *Contract
  ending* in `alerts_core.py`: push to the engineers and managers of the contract's site,
  email to its managers (S032 channel). The lead days are settings (Settings › Notifications).
  The message carries the contract id; the email names no address (CLAUDE.md §
  Notifications).
- **Text on screen (scope B):** push "Contract ends in 15 days: Atlas Copco AMC 2026–27 (SMTW).
  Renew it or let it end." Email subject "Contract ends on 31-03-2027: Atlas Copco AMC
  2026–27".
- **After it:** the manager hears about an ending contract two months and two weeks ahead.
- **Migrations:** none (settings in `app_settings`). **Leaves for later:** a dashboard tile
  (phase 5 dashboard).

### R02.6 — Breakdown calls on the contract

- **Goal:** the contract shows the vendor's breakdown calls without anyone typing them again
  (D3). KLA's "breakdown visits if any".
- **What it shows:** a *Breakdown calls* card on the contract page: every ticket on a covered
  node or its parts, raised within the contract's period, on which **a Team record linked to
  the contract's vendor** (`people.vendor_id`, R02.9) is an assignee or has a labour row (Q6.1
  a). Per ticket: serial, machine, intensity, raised, back in service, downtime, waiting on the
  vendor (S019 *vendor* reason), state, and the vendor's people who worked on it. A total line:
  N calls, downtime, waiting on the vendor. Breakdown calls included (R02.1) shows as "3 of 4
  calls used" when a number was agreed.
- **Which link counts (Q9.5 a, recommended):** the person's link as it is now. A technician
  who moves to another firm gets a new Team record, so the old tickets stay with the old
  vendor; the Team dialog warns before a linked person's vendor is changed ("Their earlier
  tickets will count for the new vendor. For a person who changed firm, add a new Team
  record.").
- **On the ticket page:** a line under the machine, "Under AMC with Atlas Copco until
  31-03-2027 · response 24 hours · breakdown calls included", so the engineer assigns the
  vendor's people instead of an in-house technician. The assignee picker shows the vendor
  beside a linked person ("Atlas Copco service · Atlas Copco").
- **Fact to note in the brief:** to be assigned, a Team record needs a Technician row at the
  ticket's site (`ASSIGNABLE_ROLES`); a labour row needs only a membership. The contract page
  warns in two cases:
  - "No Team record is linked to Atlas Copco. Link the vendor's technician, or a record such
    as 'Atlas Copco service', in Masters › Team."
  - "No Team record of Atlas Copco has a Technician row at SMTW, so the vendor cannot be
    assigned to tickets there. Ask an engineer to add one in Team." Engineers can add it
    (`people:assign_technicians`).
- **After it:** the engineer sees how often the vendor came, and how long the plant waited.
- **Migrations:** none. **Leaves for later:** the vendor's arrival time (Q6.2 a); the report
  across contracts (R02.8).

### R02.7 — PM visits against the contract (waits for PM)

- **Goal:** the agreed visits and the actual visits are compared, as D2 decided. KLA's
  "number of pm visits agreed … actual visits and maintenance done".
- **Waits for:** the PM engine's plans and jobs (Plan.MD § 4.3, phase 4). **What the register
  holds now for it:** PM visits per year (R02.1), the machines (R02.2), the vendor (R02.1) and
  its linked Team records (R02.9).
- **What changes (when PM exists):**
  - A PM plan may name its **contract** (Q7.1 a): optional `contract_id` on `pm_plans`. The
    plan's assignee stays a Team record (Plan.MD § 4.3); a plan may name a contract only when
    its assignee is **linked to the contract's vendor** (`people.vendor_id` = the contract's
    `vendor_id`). The PM plan step's brief puts the column in PM's own migration, so R02.7
    needs none.
  - *Make PM plans from this contract*: for each covered machine, a calendar plan with an
    assignee chosen from the vendor's linked Team records (the only one when there is one),
    and the interval 12 ÷ visits per year months (4 visits = every 3 months), from a PM
    template the engineer picks.
  - The contract page's *PM visits* card: per contract year, agreed, done (jobs done or
    verified), due, overdue; each job with its date and the vendor's report attached.
- **After it:** the manager sees "4 visits agreed, 2 done, 1 overdue" before the renewal talk.
- **Migrations:** none if the PM brief takes the column; else one. **Leaves for later:** the
  report across contracts (R02.8).

### R02.8 — Vendor performance report (waits for PM)

- **Goal:** per contract and **per vendor** (a `vendors` row, across its contracts), how the
  vendor did against what was agreed (ISO 9001 § 8.4, "monitor performance" of each outside
  provider).
- **What it shows:** grouped by vendor, then contract: PM visits compliance (R02.7), breakdown
  calls and those beyond the agreed number, waiting on the vendor (S019), MTTR and downtime of
  the covered machines, and for senior holders the cost per machine-year. A reader sees only
  the contracts of the sites where the key is held. Export to Excel as every phase-5 report.
- **Waits for:** R02.6, R02.7 and the phase-5 reports frame (Plan.MD § 4.6).
- **Migrations:** none. **Leaves for later:** the SMRP contractor cost share (needs the total
  maintenance cost, not recorded); a vendor rating (§ Out).

## Order

1. **R02.9 first** (D11). Every later item points at a vendor: R02.1's contract, R02.6's
   matching, R02.7's assignee, R02.8's grouping. Built first, the contract table is made with
   its final FK, and no contract ever names a Team record that a later migration would have to
   move. It is usable alone: the plant lists its vendors and links their people in Team.
2. **R02.1 next.** The register alone is useful: a manager sees what ends when, and its cost.
3. **R02.2.** It is what the floor sees (the card on the machine), and every later item reads
   the machines covered.
4. **R02.3 and R02.5, in parallel.** Small; each closes a gap the register leaves (where the
   paper lives, and who is told before the end).
5. **R02.4.** Renewal matters at the first contract end; the known AMCs' end dates are not
   recorded (risk below), so it can follow R02.5.
6. **R02.6.** It needs the machines (R02.2) and the vendor links (R02.9), and gives the first
   look at vendor work.
7. **R02.7 when the PM engine exists**, then **R02.8** with the phase-5 reports.

**Cost of the change:** the first contract arrives one step later (R02.9 is about half a day of
step time with reviews). In return, no migration later moves contracts from Team records to
vendors.

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
- R02.3 ∥ R02.5: R02.3 changes `documents.py`, a migration and the contract page; R02.5 changes
  `scheduled_tasks.py`, `alerts_core.py`, `task_handlers.py` and the Settings view, with no
  migration.
- R02.4 ∥ R02.5 and R02.6 ∥ R02.5: same reason.
- **R02.9 has no parallel partner:** every other item that could start now depends on it, and
  it shares `masters.py`, `MastersView.vue` and `local_db.py` with R02.1.

**Not in parallel:** R02.9 → R02.1 → R02.2 → R02.3 (four migrations, and each extends the
last); R02.4 and R02.6 (both change the contract page and `contracts.py`).

**Effort (estimate):** R02.9 and R02.1–R02.6 about four and a half days of step time with
reviews. R02.7 and R02.8 are sized when PM is briefed.

**Can be done now:** R02.9, R02.1–R02.6. **Waits for PM:** R02.7, R02.8.

## Decisions for the user

**Answered 30-10-2026 by KLA:** Q9.1 a, Q9.2 a plus a phone on the vendor, Q9.3 a, Q9.4 a, Q9.5 a. (Was: open now, Q9.1–Q9.5.) They wait for R02.9, except Q9.5 (R02.6). Answer as "9.1
a". The recommended option is first and marked.

**Q9.1. One table for vendors, or one for all firms with the manufacturers?** Waits: R02.9.
- **(a) A separate `vendors` table — recommended.** A manufacturer describes a model (ISO
  14224's maker); a vendor holds a contract and sends people. Atlas Copco is then two rows, one
  in each master, which is right: the maker of a machine is often not its service vendor.
  `manufacturers` and S012's production rows stay as they are.
- (b) One `firms` table with a role (maker, vendor or both). One spelling of Atlas Copco, but a
  migration renames S012's table and its rows in production (a `_PRECONDITIONS` entry and an
  upgrade test), and every model screen changes.

**Q9.2. Which fields does a vendor hold?** Waits: R02.9.
- **(a) Name, active and a note only — recommended.** The call-out number stays on the
  contract, read by `contract:read` (D10); purchase details stay with accounts. Nothing on the
  vendor needs a senior key.
- (b) Also phone, GSTIN and address. Duplicates accounts' supplier data, and a phone on the
  vendor would need its own read rule, as D10 did for the call-out number.

**Q9.3. A firm that sends a different, unnamed technician each time: how is it assigned?**
Waits: R02.9, R02.6.
- **(a) A Team record such as "Atlas Copco service", contractor, linked to the vendor —
  recommended.** It can be assigned on tickets and named on labour rows, as today's firm
  records are; named technicians may be added later and linked too.
- (b) Tickets may name the vendor itself as an assignee. A second kind of assignee changes
  S018's tables and every assignee rule.
- (c) Every visiting technician must have a named Team record. Exact, but the plant must add a
  record for each stranger before the ticket can be assigned.

**Q9.4. Who adds and edits vendors, and who reads them?** Waits: R02.9.
- **(a) Edit: `equipment:edit` (engineers, so managers, and IT admin), as manufacturers; read:
  `masters:read` (everyone) — recommended.** No new key; the same people edit the Team link
  (`people:edit`) and, later, contracts (`contract:edit`, Q1.3 a).
- (b) A new key `vendor:edit` with the same holders. A clearer name; one more key and one more
  row in `test_role_matrix`.
- (c) IT admin only (`masters:edit`). Engineers who meet the vendors must ask IT admin.

**Q9.5. A person's vendor changes: which vendor do their earlier tickets count for?** Waits:
R02.6.
- **(a) The current link; a person who changes firm gets a new Team record — recommended.**
  Simple; the Team dialog warns before a linked person's vendor is changed. Rare at the plant.
- (b) Copy the vendor onto each assignee and labour row when it is written. Exact history; a
  migration on S018's ticket tables, with rows in production (a backfill and a
  `_PRECONDITIONS` entry), and every ticket write changes.

**Not asked:** whether the link is required. KLA said it may be optional (30-10-2026); R02.9
makes it optional.

**Answered at gate R, 27-10-2026, by KLA:** Q1.2 and Q3.1 by D5; Q4.1 a (D6); Q1.7 superseded by
D8; every other question **as recommended (a)** — Q1.1 a (Warranty, AMC, CMC, On call), Q1.3 a
(engineer, so manager, and IT admin edit; an editor without `contract:read_senior` never sees or
sends the price, D5), Q1.4 b (ticks plus free text), Q1.5 a, Q1.8 a, Q2.1 a, Q2.2 a, Q5.1 a,
Q6.1 a, Q6.2 a, Q7.1 a. Recorded in Plan.MD § 2 (In v1 item 9; the *Maintenance cost*
exception; the *AMC register* line removed). **Q1.6 a is superseded by D11, 30-10-2026.**

The answered questions, kept as they were asked (questions are numbered by their item):

**Q1.1. Which contract types?** **Answered: (a).**
- **(a) Warranty, AMC, CMC, On call — recommended.** *AMC* (annual maintenance contract):
  labour and visits, parts charged. *CMC* (comprehensive maintenance contract): parts
  included. *Warranty*: the maker's, usually no cost. *On call*: a rate contract with no
  visits agreed (the Sartorius analyser). A fixed list in code; the coverage ticks say the
  rest.
- (b) AMC and CMC only. Warranties stay in the notes.
- (c) A list kept in Masters. More screens; nobody has asked for more types.

**Q1.2. Who sees contracts, at the contract's site?** **Answered: D5.**
- **(a) Every role, like `equipment:read` — recommended.** The terms are not secret, and an
  operator or technician who sees "under warranty, call the vendor" does not open the machine.
  The cost stays hidden (D4).
- (b) Technician and up, and IT admin. Operators and supervisors see no card.

**Q1.3. Who edits contracts (`contract:edit`)?** **Answered: (a).**
- **(a) Engineer (so the manager) and IT admin — recommended.** As `equipment:edit`. The
  cost is entered only by managers (D4).
- (b) Manager only. Engineers know the terms but must ask the manager.

**Q1.4. How is "what is covered" recorded?** **Answered: (b).**
- (a) Free text only. Simple, but no list can show "machines whose parts are covered".
- **(b) Ticks (labour, spare parts, consumables, breakdown calls) plus free-text *Covered* and
  *Not covered* — recommended.** The ticks show on the machine's card in a few words; the text
  holds the detail.
- (c) A line per covered item (each with its own limits). Heavy; no case needs it yet.

**Q1.5. One site per contract?** **Answered: (a).**
- **(a) Yes — recommended.** The keys and the cost are checked at one site. A vendor with
  machines at two sites gets two contracts (e.g. "Toyota MH — SMTW", "Toyota MH — SSVT"); with
  R02.9 both name the same vendor row.
- (b) A contract across sites. A manager of one site would see a cost that covers another
  site's machines, or the cost must be split. More code and rules.

**Q1.6. How is the vendor recorded?** **Superseded by D11 (30-10-2026), and by Q9.1–Q9.5.** It
was answered (a) on 27-10-2026.
- (a) One Team record per vendor firm, employment *contractor*. The same record is assigned to
  tickets and named on labour rows, so R02.6 finds the calls. The vendor's technicians are not
  separate records.
- (b) The firm and its technicians as separate Team records, linked to the contract. Better
  names on labour, but a firm grouping is needed in Team (a new column). *(D11 is close to
  this option: the grouping is the `vendors` master and `people.vendor_id`.)*
- (c) Free text. No link to tickets, so R02.6 cannot work.

**Q1.7. How is the cost recorded?** **Superseded by D8** (a price per machine).
- (a) One amount for the contract period, in ₹, before GST, with a note. Enough for cost per
  machine-year.
- (b) An amount and a payment schedule (instalments, paid dates). Accounts' work; a second
  table.
- (c) An amount per machine. Most quotes give one total.

**Q1.8. Where does the register live?** **Answered: (a).**
- **(a) A *Contracts* tab in Masters, with its own key — recommended.** Plan.MD calls it a
  master; the bottom bar on a phone already has six items.
- (b) A new nav item, *Contracts*. Faster to reach; a seventh item on the phone's bar.

**Q2.1. Which levels can a contract cover?** **Answered: (a).**
- **(a) Any node: equipment, component-unit or component — recommended.** A warranty on a
  replaced motor, or the pallet truck's battery contract, sits on the part. The card shows on
  the node and its parts.
- (b) Equipment only.

**Q2.2. May one machine be under two contracts at once?** **Answered: (a).**
- **(a) Yes, with a warning when two contracts of the same type overlap — recommended.** A
  maker's warranty on a new motor inside a machine under AMC is normal.
- (b) Never two at a time.

**Q3.1. Who reads contract documents?** **Answered: D5** (`contract:read_senior`, managers;
invoices may be attached).
- (a) `contract:read` holders, and price documents (invoices) are not attached. The signed
  contract helps the floor; accounts keep invoices.
- (b) `contract:read_senior` only. Safe for prices; the floor cannot read the scope.

**Q4.1. Renewal: a new record or a longer end date?** **Answered: D6 (a).**
- **(a) A new record linked to the old one — recommended.** Each year keeps its terms, cost
  and calls; R02.8 compares years.
- (b) Extend the To date. One record; last year's cost and terms are overwritten.

**Q5.1. When and to whom are reminders sent?** **Answered: (a).**
- **(a) 60 and 15 days before the end; push to the site's engineers and managers, email to
  its managers; not once a renewal exists — recommended.**
- (b) One reminder, 30 days before, to managers only.
- (c) No reminder; the list's *Ends in N days* badge only.

**Q6.1. Which tickets count as the vendor's breakdown calls?** **Answered: (a)**; with D11, "the
vendor" reads "a Team record linked to the vendor".
- **(a) Tickets on a covered node or its parts, raised in the period, with the vendor as
  assignee or on a labour row — recommended.**
- (b) Every ticket on a covered machine in the period, marked when the vendor worked on it.
  Shows the in-house fixes too; the list grows.

**Q6.2. Record when the vendor was called and when they arrived?** **Answered: (a).**
- **(a) Not now — recommended.** The assignment time and the waiting reason *vendor* (S019)
  already show how long the plant waited. Decide again with R02.8.
- (b) Two new timeline events on the ticket, *Vendor called* and *Vendor arrived*. The
  vendor's response time against the contract becomes exact; one more action on the phone.

**Q7.1. How does PM know a plan belongs to a contract?** **Answered: (a).**
- **(a) An optional contract on the PM plan, in PM's own migration — recommended.** Compliance
  per contract is a plain count.
- (b) No link: count the jobs whose assignee is linked to the vendor, on the covered machines,
  in the period. Breaks when the vendor has two contracts on one machine.

**Not asked again:** Plan.MD § 4.3 settles that a PM plan's assignee is a Team record, with the
engineer verifying the job and the vendor's report attached (D11 keeps this; only "the vendor is
a Team record" changes, above); § 4.2 settles that a garage or vendor repair is a ticket with the
waiting reason *vendor*. **Departures stated:** D4 (cost stored); moving the AMC register from
*Not in v1* into v1; D11 (a vendor master, against Plan.MD § 2 item 9's "one Team record per
firm" and § 4.3's "a contractor record in Team").

## Out of the roadmap and risks

**Out (fact):**
- Purchase orders, invoices, payments and GST: accounts' work.
- Vendor email, addresses and tax numbers (Q9.2: a phone only).
- An approved-vendor list or a vendor rating. ISO 9001 § 8.4.1 asks for criteria to choose and
  re-evaluate providers; many plants keep an approved-vendor list for it. R02.8's report is the
  evidence; an approval status on the vendor is a later step, if KLA wants one.
- Calibration agencies, garages and inspectors (Plan.MD § 4.1, § 4.3) as vendors: they stay
  contractor Team records with no vendor until a later step chooses to link them.
- A link to the ERP's supplier list (*to verify* whether accounts keep one in ERPNext).
- A visit log apart from PM jobs (D2).
- The total maintenance cost and the SMRP contractor cost share (Plan.MD § 2).
- Insurance policies and statutory certificates: the certification plans of § 4.3.
- Vehicle papers: Vaahan keeps them (Plan.MD § 4.1).
- Moving AMC terms already typed into equipment notes: by hand, once R02.2 is live.
- Linking today's contractor Team records to vendors: by hand in Team, once R02.9 is live (no
  migration guesses a firm from a name).

**Risks:**
- **Checked against five real documents** (27-10-2026, `scratch/`): VP Power Systems (servo
  stabiliser and UPS), Fuji Electric (UPS and harmonic filter, with a terms annexure), and
  Toyota MH for each company (a pallet truck and a stacker each). Atlas Copco's is still unseen.
  R02.9's coder records the five vendors in Plant-Facts § 4 (names and what they maintain; no
  phone numbers or addresses); Fuji and VP Power are not there yet. The Fuji PDF has six blank
  lines before its header; Yantra's upload check may refuse it, which R02.3's brief should
  check.
- **A vendor with no linked Team record finds no breakdown calls.** R02.6 counts only tickets
  worked by linked people. Until the engineer links them (or adds "Atlas Copco service"), the
  card is empty. R02.9's *People* count and R02.6's warning show the gap.
- **The link is current, not historical** (Q9.5 a). Re-linking a person to another vendor moves
  their past tickets with them. The Team dialog's warning and the "new record for a new firm"
  rule limit it.
- **Two masters spell one firm** (Q9.1 a): Atlas Copco as a manufacturer and as a vendor. A
  typo in one does not reach the other; the help text names the spelling rule.
- **PM may change shape.** R02.7's design rests on Plan.MD § 4.3 as it stands. If the PM plan
  brief settles the assignee differently, R02.7 is re-planned.
- **A vendor's people without a Technician row cannot be assigned** (`ASSIGNABLE_ROLES`). R02.6
  warns on the contract page; until then, the engineer must add the row in Team.
- **Cost visibility goes beyond the register.** An attached invoice or a cost typed into notes
  would show the price to every reader. A hint under *Notes* ("Do not enter prices here")
  limits it; the vendor's note gets the same hint.
- **Shared code:** R02.9 changes the Masters view and the Team dialog; R02.3 changes
  `documents.py`, and R02.2 the equipment page and list. Those steps run the targeted browser
  specs `masters`, `equipment` and `screens`.

## Slides

1. **Annual maintenance contracts in Yantra**
   - One list of the vendors; which machine is under which contract, until when, and what is
     covered.
   - Breakdown calls from tickets; PM visits from PM jobs: nothing typed twice.
   - Nine items: seven now, two when PM is built.
2. **What you asked, and what is decided**
   - From, to, equipment, covered, PM visits agreed, cost; actual visits; breakdown calls.
   - 27-10-2026: a roadmap; PM visits wait for PM; breakdowns stay on tickets; three read keys;
     renewal is a new record; price per machine.
   - 30-10-2026 (D11): a vendor master from the start; a contractor in Team may name its vendor.
3. **The standards, in plain words**
   - ISO 55001 § 8.3: outsourced work is still yours; control it and keep the evidence.
   - ISO 9001 § 8.4: say what you require of each outside provider, and check how each did.
   - EN 13306: vendor PM is preventive, a call-out is corrective, waiting for the vendor is
     logistic delay.
4. **The vendors** — mock-up `06-vendors-tab.html`
   - Engineers and IT admin, in Masters › Vendors: each firm once, with the people linked.
   - In Team, a contractor names its firm; "Atlas Copco service" covers unnamed visitors.
5. **The register** — mock-up `01-contracts-list.html`
   - Managers and engineers, in Masters › Contracts.
   - Each contract with its status: *In force*, *Ends in 25 days*, *Ended*; cost for managers
     only.
6. **Adding a contract** — mock-up `02-contract-dialog.html`
   - The engineer picks the vendor from Vendors, the period, coverage ticks, PM visits per
     year, response time.
   - The manager adds the prices.
7. **One contract** — mock-up `03-contract-page.html`
   - Terms, machines covered, the signed contract, the breakdown calls of the vendor's people.
   - PM visits agreed against done appears when PM is built.
8. **On the machine** — mock-up `04-equipment-under-contract.html`
   - Technicians and operators, from the QR label on a phone.
   - "Under AMC with Atlas Copco until 31-03-2027": call the engineer, do not open it.
9. **On the ticket** — mock-up `05-ticket-contract-hint.html`
   - The engineer sees the contract and assigns the vendor's person.
   - The ticket then counts as a breakdown call on the contract.
10. **The items as a timeline**
    - Now: R02.9 vendors → R02.1 register → R02.2 machines → R02.3 documents ∥ R02.5 reminders
      → R02.4 renewal → R02.6 breakdown calls.
    - With PM (phase 4): R02.7 PM visits. With reports (phase 5): R02.8 vendor performance.
11. **Your decisions now**
    - Q9.1 vendors apart from manufacturers · Q9.2 vendor fields · Q9.3 a firm with unnamed
      technicians · Q9.4 who edits vendors · Q9.5 which vendor a moved person's tickets count
      for.
12. **Decided before**
    - Q1.1–Q7.1 answered on 27-10-2026; Q1.6 replaced by the vendor master (D11).

## Log

- 31-10-2026 — **Departure, S087** (KLA): a contract is no longer at one site (Q1.5 a reversed): machines of any site, the four contract keys company-wide (so D5 and D10's "of the contract's site" no longer hold), reminders to the people at the machines' sites. v42–v47 are squashed into v50 with the change; S088 squashes v20–v41 first.
- 30-10-2026 — **Gate R for the re-plan** (KLA): Q9.1 a, Q9.2 a plus a phone on the vendor (its read rule in R02.9's brief), Q9.3 a, Q9.4 a, Q9.5 a. Plan.MD § 2 item 9, § 4.3 *Performer* and the Team line updated. KLA: R02.9 and R02.1–R02.6 to be built on 30-10-2026, run as R05.
- 30-10-2026 — **Re-plan: the vendor master** (KLA, 30-10-2026; back to gate R). New item
  **R02.9 Vendor master** (`vendors` table shared by all sites, a *Vendors* tab in Masters, an
  optional `people.vendor_id` on a contractor's Team record), first in § Order; R02.1 depends on
  it. New decision **D11**; **Q1.6 a superseded**, and the "no vendor master apart from Team"
  line removed. D2, D3 and D7 reworded (the vendor is a `vendors` row; the assignee is a Team
  record linked to it); their meaning stays. R02.1 (vendor from Vendors), R02.4 (inactive
  vendor refused), R02.6 (matching through the link, two warnings, the vendor in the assignee
  picker), R02.7 (the assignee linked to the contract's vendor) and R02.8 (grouped by vendor)
  changed. R02.3 corrected: the contract is the sixth document owner (S070 and S075 added two
  since 27-10-2026). § What exists re-checked at HEAD `d216f48` (latest migration v41). Five
  new questions Q9.1–Q9.5; one new mock-up `06-vendors-tab.html`; slides 4, 11 and 12 new. The
  Plan.MD changes for gate R are listed under § The feature.
  Feedback of this re-plan:
  - `rule` — The mock-up file number is given by the order of writing (06), but the deck's
    order puts it first. README § The showcase says files are numbered "in the order of the
    deck"; a re-plan that adds a first screen cannot follow both. Evidence: § Slides 4 uses
    `06-vendors-tab.html`. A line in the README that a re-plan appends numbers and § Slides sets
    the order would settle it.
  - `hindrance` — The re-plan may write only the new mock-up, so `02-contract-dialog.html:49`
    and `03-contract-page.html:59` still show the vendor as a Team contractor. A re-plan
    should be allowed to correct the wording of its own roadmap's mock-ups.
- 27-10-2026 — **Re-approved at gate R** after reading five real documents in `scratch/` (VP
  Power, Fuji quote and annexure, two Toyota quotes): D7 (mixed quote = two contracts), D8
  (price per machine, supersedes Q1.7), D9 (only-the-vendor-repairs tick), D10 (call-out number
  for engineers, managers and admin, through a third key `contract:read`). The documents also
  confirm Q1.5 (Toyota quotes each company apart), 4 PM visits a year, breakdown calls included
  / unlimited / not included, and the 60-day reminder (Fuji: renewal two months before
  expiry).
- 27-10-2026 — **Approved at gate R** by KLA: the rest as recommended; Plan.MD § 2 updated.
- 27-10-2026 — Gate R answers so far: D5 (two read keys, `read_basic` all but price and
  documents, `read_senior` managers; Q1.2, Q3.1), D6 (Q4.1 a).
- 27-10-2026 — First version (Draft): eight items (six now, two waiting for PM), KLA's four
  decisions D1–D4 recorded, the Plan.MD wording for the cost departure proposed, sixteen
  questions for KLA, five mock-ups. Checked against HEAD `c9142b4`.

## Feedback

- `idea` — The contract fields rest on three vendors named in Plant-Facts and no real
  contract. A rule that a roadmap for a register asks the user for one or two real samples
  (a PDF in `scratch/`) before gate R would ground the fields.
- `hindrance` — The step size rule (at most one new table) splits the register from its
  machine list (R02.1, R02.2), though a link table is part of the same concern. A note in the
  size rule that a pure link table does not count would remove the split.
- `waste` — Plan.MD is about 900 lines; finding the AMC, cost and performer lines took several
  greps. A short index of decisions by topic at the top of Plan.MD would save the next roadmapper
  that search.
- `idea` (30-10-2026) — The first plan missed the vendor master because "a firm is a Team
  record" was already in Plan.MD. A roadmapper check "does each party the feature names have
  one record of its own?" would have raised it before gate R.
