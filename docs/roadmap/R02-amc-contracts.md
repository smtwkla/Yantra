```
Roadmap: R02 — Annual maintenance contracts (AMC)
Doc: roadmap
Author: Roadmapper (Opus)
Date: 27-10-2026
Status: Approved (gate R, 27-10-2026, by KLA; D7–D10 added the same day)
```

# R02 — Annual maintenance contracts (AMC)

**The point:** Yantra gets a **contract register**: per vendor contract, the period, the
equipment covered, what is covered, the PM visits agreed and the cost. This roadmap cuts it
into **eight items**. Six can be built now; two wait for the PM module (Plan.MD § 4.3, build
phase 4). The first useful result is **R02.1 and R02.2**: the register and an *Under contract*
card on every covered machine. Breakdown calls come from the tickets (R02.6), never typed
twice. KLA has **four decisions made** (27-10-2026, below) and **sixteen questions** to answer
(§ Decisions for the user).

## The feature

**What KLA asked (27-10-2026, verbatim):** "we need to plan being able to track annual
maintenance contracts. contract details: from, to, what equipment, what is covered, number of
pm visits agreed, cost. actual visits and maintenance done, breakdown visits if any".

**Why (fact):** important equipment is under AMC (Plant-Facts § 4, 13-10-2026). The vendors
known so far are Atlas Copco (the two screw compressors of the extrusion line), Toyota Material
Handling (the electric pallet truck) and Sartorius (the moisture analyser, on call). A
packing-machine AMC technician also visits (the daily report of 09-10-2026). Today nobody can
see in one place which machine is under which contract, until when, and whether the vendor
did the visits paid for. Plan.MD § 2 parked the register as "a later master" (16-10-2026), with
the terms in the equipment's notes meanwhile. ISO 55001 asks that outsourced maintenance be
controlled (§ Standards).

**Decided by KLA, 27-10-2026** (the orchestrator records them in Plan.MD at gate R):

| # | Decision | What it means for the roadmap |
|---|---|---|
| D1 | **A roadmap, not one step.** | This file. |
| D2 | **PM visits wait for PM.** No stand-alone visit log. | The vendor's agreed visits become PM plans, and the actual visits PM jobs, with the vendor (a contractor in Team) as the plan's assignee (Plan.MD § 4.3, *Performer*). The register holds now what PM needs later: **PM visits agreed per year** on the contract. Later a PM plan points at its contract, and compliance is jobs done against visits agreed (R02.7). |
| D3 | **Breakdown visits stay on tickets.** | A vendor's breakdown call is a ticket assigned to the vendor (S018: `ticket_assignees`, `ticket_labour`). The contract page lists the tickets on its equipment, in its period, that the vendor worked on: derived, not re-entered (R02.6). Downtime, MTTR and the failure codes stay in one place. |
| D4 | **Contract cost is stored**, seen by managers, `contract:read_senior` (D5). | **A deliberate departure from Plan.MD § 2**, "Maintenance cost — not in v1". Proposed Plan.MD wording below. |
| D5 | **Two read keys** (KLA, 27-10-2026, at gate R; replaces "managers and admin only"). | `contract:read_basic`, same holders as `equipment:read` (`("*",)`, site-scoped): **every field except the price, the cost note and the documents** (vendor, type, contract number, from and to, status, coverage ticks and text, PM visits, response time, notes, machines, breakdown calls). `contract:read_senior`, **managers** of the contract's site (admin by the bypass; IT admin not): adds **the price, the cost note and every attached document** (a quote or signed contract shows the price, so all documents sit here). D10 adds a middle key, `contract:read` (engineers and managers), for the call-out number. Answers Q1.2 and Q3.1. |
| D6 | **Renewal makes a new record linked to the old one** (Q4.1 a, KLA, 27-10-2026). | Each year keeps its terms, cost and breakdown calls (R02.4). |
| D7 | **One coverage per contract; a mixed quote becomes two contracts** (KLA, 27-10-2026, after the real documents). | Fuji's quote `AMC14082369550-R` holds a comprehensive AMC (UPS) and a labour AMC (harmonic filter): entered as two contracts with the same vendor and contract number, the quote attached to both. The design stays: coverage on the contract. |
| D8 | **The price is per machine** (replaces Q1.7 a). | Every quote prices each machine (VP Power ₹9,000 / ₹4,900; Toyota ₹18,040 a truck; Fuji ₹9,809 / ₹28,028). An optional price, before GST, on each machine line (`contract_equipment`, R02.2), seen and entered only by `contract:read_senior`; the contract's total is their sum, never typed. So the price lands with R02.2, and R02.1 holds the cost note only. Cost per machine-year (R02.8) is then exact. |
| D9 | **"Only the vendor may repair" tick.** | Fuji (annexure § 1 A i) and Toyota (terms 7) end the contract if anyone else repairs or tampers with the machine. A tick on the contract; when set, the machine card shows, in a warning colour, "Do not repair. Call the engineer; the vendor repairs this machine." |
| D10 | **Call-out number, for engineers, managers and admin** (KLA, 27-10-2026). | A *Call-out number* on the contract (the vendor's breakdown line, e.g. VP Power's 24-hour number). Read with a third key, **`contract:read`**, held by **engineers and managers** of the contract's site (admin by the bypass); shown to them on the contract page and the machine card. Everyone else sees "Call the engineer". So D5's two keys become three, which is CLAUDE-COMMON § RBAC Pattern's three-level read hierarchy: `read_basic` (all but price, documents and the call-out number), `read` (adds the call-out number), `read_senior` (adds the price, the cost note and the documents). A firm's service number, kept in the database only; never in the repo (no real numbers in tests or docs). |

**Proposed Plan.MD wording (for the orchestrator at gate R):**
- § 2 *In v1*, a new item 9: "**Maintenance contracts** (R02, 27-10-2026): a register of vendor
  contracts (warranty, AMC, CMC, on call): vendor, period, equipment covered, what is covered,
  PM visits agreed per year, response time, cost. Breakdown calls are the vendor's tickets; the
  agreed visits become PM plans when PM is built (§ 4.3)."
- § 2 *Not in v1*, the *AMC register* line goes. The *Maintenance cost* line gets: "Exception
  (R02, 27-10-2026): the cost of a maintenance contract is stored on the contract and seen only
  by the managers of its site and admin (`contract:read_senior`). It is not spread over tickets
  or jobs, and no other maintenance cost is recorded."

**What it is not:** no purchase orders, invoices or payments (accounts keep them); no vendor
master apart from Team; no visit log apart from PM jobs (D2).

## What exists

Checked against the code at HEAD `c9142b4` (27-10-2026).

| What | State today | Evidence |
|---|---|---|
| Vendor as a Team record | **Built.** A Team record is a person or a contractor firm, with employment `direct` or `contractor`. | `masters_core.py:24-25` `EMPLOYMENT`; `docs/schema.md` `people` ("one record per person, or per contractor firm (the user's choice)"). |
| Vendor on a ticket | **Built.** Assignees and labour rows name Team records. An assignee must hold a Technician, Engineer or Manager row at the ticket's site; a labour row may name anyone with a membership there. | `tickets.py:19-20`, `:125` `ASSIGNEE_AT_SITE`; `config_rbac.py:64` `ASSIGNABLE_ROLES`. |
| Waiting on a vendor | **Built (S019).** A ticket in *scheduled* with the waiting reason *vendor* counts as EN 13306 logistic delay. | `tickets_core.py:309-311` `WAITING_REASONS["vendor"]`. |
| Documents | **Built (S006, S012, S017).** One owner per file: equipment, model or ticket; the owners are data in `documents.py` (`OWNERS`). | `documents.py:150-181`; `local_db.py:480-481` `chk_equipment_documents_owner`. A fourth owner, the contract, needs a column and a new CHECK (R02.3). |
| Equipment history | **Built (S002, S038, S044).** `equipment_events` takes new event kinds without a new table. | `docs/schema.md` `equipment_events`. |
| Site-scoped keys | **Built (S011).** A key in `SITE_SCOPED` is checked at the record's site. | `config_rbac.py:166-179`. |
| Daily tasks, push and email | **Built (S013, S021, S032).** `scheduled_tasks.SCHEDULE` (one entry today), alert kinds and channels in `alerts_core.py`. | `scheduled_tasks.py:12-13`; `alerts_core.py:26` `KINDS`, `:46` `CHANNELS`. |
| Masters tabs | **Built.** Eleven tabs, each with its own key. | `frontend/src/views/MastersView.vue:26-36`. |
| Contract terms in notes | **Plan.MD § 2:** "In v1 the terms go in the equipment's notes." | No code; any such notes are moved by hand once R02.2 is live (§ Out of the roadmap). |
| PM plans and jobs | **Not built.** No PM tables; `docs/schema.md` lists `pm_plans` and `pm_jobs` as planned. | `docs/schema.md` § Planned tables. |
| Migrations | Latest **v34** (S061). | `local_db.py:1049`. |

**What no item rebuilds:** the Team register (the vendor is a Team record), ticket assignees,
labour and waiting reasons (the breakdown calls), the documents module (one more owner),
the equipment history (new event kinds), the worker and the alert channels (one more kind).

## Standards

**How the numbers are marked.** ISO 55001 § 8.3 and ISO 9001 clauses that Plan.MD already cites
are given plain. The rest are marked *to verify*.

| Standard | What it says, in plain words | How R02 follows it | Items |
|---|---|---|---|
| **ISO 55001 § 8.3 Outsourcing** (cited in Plan.MD § 2; the 2024 edition's number *to verify*) | Work given to an outside firm stays the plant's responsibility. The plant decides what is outsourced, how it is controlled, and keeps the evidence. | The register names, per machine, who maintains it under which terms and until when; the vendor's work is recorded as tickets and PM jobs like the plant's own. | R02.1, R02.2, R02.6, R02.7 |
| **ISO 9001:2015 § 8.4 Control of externally provided processes, products and services** (sub-clauses *to verify*) | Choose outside providers on criteria, check their performance, and keep records of it. Clause 8.4.3 says the agreement must state what is required. | The contract records what is agreed (visits, coverage, response time). R02.8 reports how the vendor performed against it, which is the "monitor performance" record. ISO 9001 is a future goal for the plant. | R02.1, R02.8 |
| **ISO 9001:2015 § 7.5 Documented information** | Keep the records that show the work was done, protected from loss and change. | The signed contract is a document on the contract (R02.3); who changed a contract and when is kept (R02.1, R02.2). | R02.1–R02.3 |
| **EN 13269 Maintenance — Guideline on preparation of maintenance contracts** (edition and content *to verify*) | A European guide to what a maintenance contract should state: scope, the equipment, the services, response times, what is excluded, how performance is measured. | The contract's fields follow that list: equipment, covered and not covered, PM visits, breakdown calls, response time. | R02.1 |
| **EN 13306 Maintenance terminology** | Names the kinds of maintenance: *preventive* (planned, before failure), *corrective* (after a failure), *deferred corrective*, and *logistic delay* (waiting for parts, a vendor or an expert). | The vendor's PM visits are preventive maintenance (PM jobs); breakdown calls are corrective maintenance (tickets); waiting for the vendor is logistic delay (S019). R02 adds no new kind. | R02.6, R02.7 |
| **ISO 14224 § 9 Maintenance data** (Table 8, "maintenance resources"; *to verify*) | Each maintenance event records who did it, including whether the work was done in-house or by a contractor. | Already recorded: the labour row names the Team record, whose employment is *contractor*. R02.6 reads it; nothing is typed again. | R02.6 |
| **SMRP metrics** (metric numbers *to verify*) | *Contractor cost as a share of total maintenance cost*; *PM compliance* (jobs done on time against jobs due); *MTTR*. | R02.8 gives PM compliance per contract and MTTR of the covered machines. The contractor cost share needs the total maintenance cost, which Yantra does not record (Plan.MD § 2), so R02.8 shows only the contract cost per machine-year. | R02.8 |
| **TPM, planned maintenance pillar** | Planned maintenance covers all the work on a machine, whoever does it. An outside vendor's visits are planned and checked like the plant's own. | D2: the vendor's visits become PM plans with the vendor as performer, verified by the engineer. | R02.7 |
| **ISO/IEC 27001:2022 A.5.15 Access control, A.8.3 Information access restriction** (A.8.3 *to verify*) | People see only the information they need for their job. | The price and documents are behind `contract:read_senior`, managers at the contract's site and admin; the rest of the contract is `contract:read_basic` (D5). | R02.1 |

## Showcase

**Who uses it, and what each can do (user stories):**

- **As a maintenance manager**, I see every contract at my site with its status (*In force*,
  *Ends in 25 days*, *Ended*) and its cost. I get a reminder before a contract ends, so I renew
  it in time or let it go on purpose.
- **As a maintenance engineer**, I add a contract: the vendor, the period, the machines it
  covers, what is covered and not covered, the PM visits per year and the response time. I
  attach the signed contract. When it ends, I *Renew* it, and the terms and machines carry
  over.
- **As a maintenance engineer**, I open a contract and see every breakdown call the vendor
  worked on in its period, with the downtime and the days waited for the vendor.
- **As a technician on the floor**, I open a machine from its QR label and see *Under AMC with
  Atlas Copco until 31-03-2027*, with the response time and what is covered. So I call the
  vendor instead of opening a machine under warranty.
- **As an operator**, I see the same line on the machine, so I know a vendor looks after it.
- **Later, with PM**: as an engineer, I see *4 visits agreed, 2 done, 1 due* on the contract,
  and the vendor's visit reports on the PM jobs.
- **As IT admin**, I keep the register tidy (Q1.3) but do not see the cost (D4).

**Mock-ups** (`docs/roadmap/R02-mockups/`, in the deck's order):

| File | Screen | Viewport |
|---|---|---|
| `01-contracts-list.html` | Masters › Contracts: the register, as a manager sees it | desktop |
| `02-contract-dialog.html` | *Add contract*: the dialog | desktop |
| `03-contract-page.html` | One contract: terms, cost, machines covered, documents, breakdown calls, PM visits (greyed: comes with PM) | desktop |
| `04-equipment-under-contract.html` | The equipment page on a phone, with the *Under contract* card | phone |
| `05-ticket-contract-hint.html` | A ticket on a covered machine, with the contract line and the vendor assigned | phone |

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R02.1 | Contract register: the contract record, the list in Masters › Contracts, the dialog, three keys, the cost for managers | M | full | — | open |
| R02.2 | Equipment covered: the contract page, its machines, the *Under contract* card on the equipment page, a list filter | M | full | R02.1 | open |
| R02.3 | Contract documents: the signed contract and its annexures on the contract | S | full | R02.1 | open |
| R02.4 | Renewal: *Renew* makes the next contract with the same terms and machines; the chain is kept | S | full | R02.2 | open |
| R02.5 | Reminders before a contract ends: push and email | S–M | full | R02.1 | open |
| R02.6 | Breakdown calls on the contract, derived from tickets; the contract line on the ticket page | M | full | R02.2 | open |
| R02.7 | PM visits against the contract: PM plans point at their contract; agreed against done | M | full | R02.2 and the PM engine (phase 4) | open — **waits for PM** |
| R02.8 | Vendor performance report: visits compliance, breakdown calls, waiting on the vendor, MTTR, cost per machine-year | M | full | R02.6, R02.7, reports (phase 5) | open — **waits for PM** |

### R02.1 — Contract register

- **Goal:** one record per vendor contract, listed with its status, so the plant knows what
  it has bought and until when. The fields KLA named: from, to, what is covered, PM visits
  agreed, cost.
- **The record** (`contracts`, one migration):
  - **Site** (required; Q1.5). The contract's keys are checked here.
  - **Vendor**: a Team record of employment *contractor* (Q1.6).
  - **Type**: Warranty / AMC / CMC / On call (Q1.1).
  - **Title** (e.g. "Atlas Copco AMC 2026–27") and the vendor's **contract number**.
  - **From** and **To** (dates, DD-MM-YYYY; To on or after From).
  - **What is covered** (Q1.4 b, recommended): ticks for *Labour*, *Spare parts*,
    *Consumables* (oil, filters), and *Breakdown calls* (included, or a number per year); a
    free-text **Covered** and **Not covered** (up to 1,000 characters each).
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
  `contract:read_basic` (as `equipment:read`: all but price, documents and call-out number), `contract:read` (engineers and managers: the call-out number, D10), `contract:read_senior` (managers: price and documents), `contract:edit` (D5; admin by the bypass).
- **Screens:** a **Contracts** tab in Masters (Q1.8): a table with type, title, vendor, site,
  from, to, status badge, and cost for senior holders; filters site, type, status; *Add
  contract* and *Edit* open one dialog (`FormModal.vue`).
- **Text on screen (scope B):** button *Add contract*; status badges *In force*, *Ends in 25
  days*, *Ended*, *Starts on 01-04-2027*; refusals "Choose a vendor from Team. The vendor must
  be a contractor." and "Enter a To date on or after the From date."; empty state "No
  contracts yet. Add the first one with *Add contract*."
- **After it:** the manager sees every contract at the site, its end date and its cost.
- **Migrations:** one (`contracts`). **Leaves for later:** the machines (R02.2), documents
  (R02.3), renewal (R02.4), reminders (R02.5).

### R02.2 — Equipment covered

- **Goal:** each contract names its machines, and each machine shows its contract. This is
  KLA's "what equipment".
- **What changes:**
  - `contract_equipment` (one migration): contract → equipment node, with an optional
    **price** before GST (D8; `contract:read_senior` only; the contract's total is the sum). Nodes of the contract's
    site only; which levels: Q2.1. One node may be in two contracts at once (Q2.2).
  - A **contract page** (`/contracts/:id`): the terms, the cost (senior holders), the machines
    covered (*Add machines* with the equipment picker, *Remove*), and the cards that later
    items fill (documents, breakdown calls, PM visits).
  - Each add and remove writes a line in the machine's history (`equipment_events`, new kinds
    `contract_added` and `contract_removed`), so the machine's card shows when it came under
    which contract (ISO 9001 § 7.5).
  - **The equipment page** gets an *Under contract* card, after *Open tickets*: per contract
    in force on the node or its ancestors, "Under AMC with Atlas Copco until 31-03-2027",
    the response time, the coverage ticks, the call-out number for `contract:read` holders (D10; others see "Call the engineer"), the warning "Do not
    repair. Call the engineer; the vendor repairs this machine." when the contract has the D9
    tick, and a link to the contract for `contract:read_basic` holders. A contract that ended in the last 90 days shows as "AMC with … ended on …".
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
- **What changes:** a fourth owner in `documents.py` (`OWNERS`), with `contract:read_senior` to read
  and `contract:edit` to write; `equipment_documents.contract_id` and the owner CHECK widened
  to four (one migration, no rows change, so no `_PRECONDITIONS` entry; to confirm in the
  brief). The removed-documents purge (S008) lists contract documents too.
- **Note:** documents read with `contract:read_senior` (managers, D5), so quotes and invoices may
  be attached; a `contract:read_basic` holder sees no documents. Write needs `contract:edit`;
  whether an editor without `read_senior` may upload (and then not see the file) is for the brief.
- **After it:** the engineer finds the contract from a phone when the vendor disputes what is
  covered.
- **Migrations:** one (column and CHECK). **Leaves for later:** none.

### R02.4 — Renewal

- **Goal:** renewing a contract takes one action, and the history of earlier contracts stays.
- **What changes:** *Renew* on a contract opens the dialog filled with its terms, From = the day
  after its To, To = one year later, cost empty (managers fill it). Saving creates a new
  contract with *Renewal of* = the old one and copies its machines. The old contract stays as
  it was, read-only once ended. The contract page shows the chain ("Renews: Atlas Copco AMC
  2025–26").
- **Q4.1** (recommended: a new record) settles renewal against extending the end date.
- **After it:** each year's terms, cost and breakdown calls stay comparable, year by year.
- **Migrations:** none (the column is in R02.1). **Leaves for later:** none.

### R02.5 — Reminders before a contract ends

- **Goal:** no contract ends unnoticed.
- **What changes:** a daily task in `scheduled_tasks.SCHEDULE` finds contracts whose To date
  is N days away (Q5.1: 60 and 15 days recommended) and that have no renewal yet. A new alert
  kind *Contract ending* in `alerts_core.py`: push to the engineers and managers of the
  contract's site, email to its managers (S032 channel). The lead days are settings (Settings ›
  Notifications). The message carries the contract id; the email names no address (CLAUDE.md §
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
  node or its parts, raised within the contract's period, on which the vendor is an assignee
  or has a labour row (Q6.1). Per ticket: serial, machine, intensity, raised, back in service,
  downtime, waiting on the vendor (S019 *vendor* reason), state. A total line: N calls,
  downtime, waiting on the vendor. Breakdown calls included (R02.1) shows as "3 of 4 calls
  used" when a number was agreed.
- **On the ticket page:** a line under the machine, "Under AMC with Atlas Copco until
  31-03-2027 · response 24 hours · breakdown calls included", so the engineer assigns the vendor
  instead of an in-house technician.
- **Fact to note in the brief:** to be assigned, the vendor's Team record needs a Technician
  row at the ticket's site (`ASSIGNABLE_ROLES`); a labour row needs only a membership. The
  contract page warns "Atlas Copco has no Technician row at SMTW, so it cannot be assigned to
  tickets there. Ask an engineer to add one in Team." Engineers can add it
  (`people:assign_technicians`).
- **After it:** the engineer sees how often the vendor came, and how long the plant waited.
- **Migrations:** none. **Leaves for later:** the vendor's arrival time (Q6.2); the report
  across contracts (R02.8).

### R02.7 — PM visits against the contract (waits for PM)

- **Goal:** the agreed visits and the actual visits are compared, as D2 decided. KLA's
  "number of pm visits agreed … actual visits and maintenance done".
- **Waits for:** the PM engine's plans and jobs (Plan.MD § 4.3, phase 4). **What the register
  holds now for it:** PM visits per year (R02.1), the machines (R02.2), the vendor as a Team
  record (R02.1).
- **What changes (when PM exists):**
  - A PM plan may name its **contract** (Q7.1 a): optional `contract_id` on `pm_plans`, on a
    plan whose assignee is the contract's vendor. Recommended: the PM plan step's brief puts
    the column in PM's own migration, so R02.7 needs none.
  - *Make PM plans from this contract*: for each covered machine, a calendar plan with the
    vendor as assignee and the interval 12 ÷ visits per year months (4 visits = every 3
    months), from a PM template the engineer picks.
  - The contract page's *PM visits* card: per contract year, agreed, done (jobs done or
    verified), due, overdue; each job with its date and the vendor's report attached.
- **After it:** the manager sees "4 visits agreed, 2 done, 1 overdue" before the renewal talk.
- **Migrations:** none if the PM brief takes the column; else one. **Leaves for later:** the
  report across contracts (R02.8).

### R02.8 — Vendor performance report (waits for PM)

- **Goal:** per contract and per vendor, how the vendor did against what was agreed (ISO 9001
  § 8.4, "monitor performance").
- **What it shows:** PM visits compliance (R02.7), breakdown calls and those beyond the
  agreed number, waiting on the vendor (S019), MTTR and downtime of the covered machines, and
  for senior holders the cost per machine-year. Export to Excel as every phase-5 report.
- **Waits for:** R02.6, R02.7 and the phase-5 reports frame (Plan.MD § 4.6).
- **Migrations:** none. **Leaves for later:** the SMRP contractor cost share (needs the total
  maintenance cost, not recorded).

## Order

1. **R02.1 first.** The register alone is useful: a manager sees what ends when, and its cost.
2. **R02.2 next.** It is what the floor sees (the card on the machine), and every later item
   reads the machines covered.
3. **R02.3 and R02.5, in parallel.** Small; each closes a gap the register leaves (where the
   paper lives, and who is told before the end).
4. **R02.4.** Renewal matters at the first contract end; the known AMCs' end dates are not
   recorded (risk below), so it can follow R02.5.
5. **R02.6.** It needs the machines (R02.2), and gives the first look at vendor work.
6. **R02.7 when the PM engine exists**, then **R02.8** with the phase-5 reports.

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
- R02.3 ∥ R02.5: R02.3 changes `documents.py`, a migration and the contract page; R02.5 changes
  `scheduled_tasks.py`, `alerts_core.py`, `task_handlers.py` and the Settings view, with no
  migration.
- R02.4 ∥ R02.5 and R02.6 ∥ R02.5: same reason.

**Not in parallel:** R02.1 → R02.2 → R02.3 (three migrations, and each extends the last);
R02.4 and R02.6 (both change the contract page and `contracts.py`).

**Effort (estimate):** R02.1–R02.6 about four days of step time with reviews. R02.7 and R02.8
are sized when PM is briefed.

**Can be done now:** R02.1–R02.6. **Waits for PM:** R02.7, R02.8.

## Decisions for the user

**Answered at gate R, 27-10-2026, by KLA:** Q1.2 and Q3.1 by D5; Q4.1 a (D6); every other
question **as recommended (a)** — Q1.1 a (Warranty, AMC, CMC, On call), Q1.3 a (engineer, so
manager, and IT admin edit; an editor without `contract:read_senior` never sees or sends the
price, D5), Q1.4 b (ticks plus free text), Q1.5 a, Q1.6 a, Q1.7 a, Q1.8 a, Q2.1 a, Q2.2 a,
Q5.1 a, Q6.1 a, Q6.2 a, Q7.1 a. Recorded in Plan.MD § 2 (In v1 item 9; the *Maintenance cost*
exception; the *AMC register* line removed).

Questions are numbered by their item (Q2.1 is the first question of R02.2). Answer as "1.1 a".
D1–D4 (§ The feature) are decided and not asked again.

**Q1.1. Which contract types?** Waits: R02.1.
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

**Q1.3. Who edits contracts (`contract:edit`)?** Waits: R02.1.
- **(a) Engineer (so the manager) and IT admin — recommended.** As `equipment:edit`. The
  cost is entered only by managers (D4).
- (b) Manager only. Engineers know the terms but must ask the manager.

**Q1.4. How is "what is covered" recorded?** Waits: R02.1.
- (a) Free text only. Simple, but no list can show "machines whose parts are covered".
- **(b) Ticks (labour, spare parts, consumables, breakdown calls) plus free-text *Covered* and
  *Not covered* — recommended.** The ticks show on the machine's card in a few words; the text
  holds the detail.
- (c) A line per covered item (each with its own limits). Heavy; no case needs it yet.

**Q1.5. One site per contract?** Waits: R02.1.
- **(a) Yes — recommended.** The keys and the cost are checked at one site. A vendor with
  machines at two sites gets two contracts (e.g. "Toyota MH — SMTW", "Toyota MH — SSVT").
- (b) A contract across sites. A manager of one site would see a cost that covers another
  site's machines, or the cost must be split. More code and rules.

**Q1.6. How is the vendor recorded?** Waits: R02.1.
- **(a) One Team record per vendor firm, employment *contractor* — recommended.** The
  same record is assigned to tickets and named on labour rows, so R02.6 finds the calls. The
  vendor's technicians are not separate records.
- (b) The firm and its technicians as separate Team records, linked to the contract. Better
  names on labour, but a firm grouping is needed in Team (a new column).
- (c) Free text. No link to tickets, so R02.6 cannot work.

**Q1.7. How is the cost recorded?** **Superseded by D8** (a price per machine).
- **(a) One amount for the contract period, in ₹, before GST, with a note — recommended.**
  Enough for cost per machine-year.
- (b) An amount and a payment schedule (instalments, paid dates). Accounts' work; a second
  table.
- (c) An amount per machine. Most quotes give one total.

**Q1.8. Where does the register live?** Waits: R02.1.
- **(a) A *Contracts* tab in Masters, with its own key — recommended.** Plan.MD calls it a
  master; the bottom bar on a phone already has six items.
- (b) A new nav item, *Contracts*. Faster to reach; a seventh item on the phone's bar.

**Q2.1. Which levels can a contract cover?** Waits: R02.2.
- **(a) Any node: equipment, component-unit or component — recommended.** A warranty on a
  replaced motor, or the pallet truck's battery contract, sits on the part. The card shows on
  the node and its parts.
- (b) Equipment only.

**Q2.2. May one machine be under two contracts at once?** Waits: R02.2.
- **(a) Yes, with a warning when two contracts of the same type overlap — recommended.** A
  maker's warranty on a new motor inside a machine under AMC is normal.
- (b) Never two at a time.

**Q3.1. Who reads contract documents?** **Answered: D5** (`contract:read_senior`, managers; invoices may be attached).
- **(a) `contract:read` holders, and price documents (invoices) are not attached —
  recommended.** The signed contract helps the floor; accounts keep invoices.
- (b) `contract:read_senior` only. Safe for prices; the floor cannot read the scope.

**Q4.1. Renewal: a new record or a longer end date?** **Answered: D6 (a).**
- **(a) A new record linked to the old one — recommended.** Each year keeps its terms, cost
  and calls; R02.8 compares years.
- (b) Extend the To date. One record; last year's cost and terms are overwritten.

**Q5.1. When and to whom are reminders sent?** Waits: R02.5.
- **(a) 60 and 15 days before the end; push to the site's engineers and managers, email to
  its managers; not once a renewal exists — recommended.**
- (b) One reminder, 30 days before, to managers only.
- (c) No reminder; the list's *Ends in N days* badge only.

**Q6.1. Which tickets count as the vendor's breakdown calls?** Waits: R02.6.
- **(a) Tickets on a covered node or its parts, raised in the period, with the vendor as
  assignee or on a labour row — recommended.**
- (b) Every ticket on a covered machine in the period, marked when the vendor worked on it.
  Shows the in-house fixes too; the list grows.

**Q6.2. Record when the vendor was called and when they arrived?** Waits: R02.6, R02.8.
- **(a) Not now — recommended.** The assignment time and the waiting reason *vendor* (S019)
  already show how long the plant waited. Decide again with R02.8.
- (b) Two new timeline events on the ticket, *Vendor called* and *Vendor arrived*. The
  vendor's response time against the contract becomes exact; one more action on the phone.

**Q7.1. How does PM know a plan belongs to a contract?** Waits: R02.7 and the PM plan brief.
- **(a) An optional contract on the PM plan, in PM's own migration — recommended.** Compliance
  per contract is a plain count.
- (b) No link: count the jobs whose assignee is the vendor, on the covered machines, in the
  period. Breaks when the vendor has two contracts on one machine.

**Not asked again:** Plan.MD § 4.3 settles that an AMC vendor is a contractor record in Team
and can be a PM plan's assignee, with the engineer verifying the job and the vendor's report
attached; § 4.2 settles that a garage or vendor repair is a ticket with the waiting reason
*vendor*. **Departures stated:** D4 (cost stored), and moving the AMC register from *Not in
v1* into v1.

## Out of the roadmap and risks

**Out (fact):**
- Purchase orders, invoices, payments and GST: accounts' work.
- A visit log apart from PM jobs (D2).
- The total maintenance cost and the SMRP contractor cost share (Plan.MD § 2).
- Insurance policies and statutory certificates: the certification plans of § 4.3.
- Vehicle papers: Vaahan keeps them (Plan.MD § 4.1).
- Moving AMC terms already typed into equipment notes: by hand, once R02.2 is live.

**Risks:**
- **Checked against five real documents** (27-10-2026, `scratch/`): VP Power Systems (servo
  stabiliser and UPS), Fuji Electric (UPS and harmonic filter, with a terms annexure), and
  Toyota MH for each company (a pallet truck and a stacker each). Atlas Copco's is still unseen.
  R02.1's coder records the plant facts in Plant-Facts (no phone numbers or addresses). The
  Fuji PDF has six blank lines before its header; Yantra's upload check may refuse it, which
  R02.3's brief should check.
- **PM may change shape.** R02.7's design rests on Plan.MD § 4.3 as it stands. If the PM plan
  brief settles the assignee differently, R02.7 is re-planned.
- **A vendor without a Technician row cannot be assigned** (`ASSIGNABLE_ROLES`). R02.6 warns
  on the contract page; until then, the engineer must add the row in Team.
- **Cost visibility goes beyond the register.** An attached invoice or a cost typed into notes
  would show the price to every reader. Q3.1 a and a hint under *Notes* ("Do not enter prices
  here") limit it.
- **Shared code:** R02.3 changes `documents.py`, and R02.2 the equipment page and list; those
  steps run the targeted browser specs `equipment` and `masters` plus `screens`.

## Slides

1. **Annual maintenance contracts in Yantra**
   - Which machine is under which contract, until when, and what is covered.
   - Breakdown calls from tickets; PM visits from PM jobs: nothing typed twice.
   - Eight items: six now, two when PM is built.
2. **What you asked, and what is decided**
   - From, to, equipment, covered, PM visits agreed, cost; actual visits; breakdown calls.
   - Decided 27-10-2026: a roadmap; PM visits wait for PM; breakdowns stay on tickets; cost and documents seen by managers, everything else by all (D5); renewal is a new record (D6).
3. **The standards, in plain words**
   - ISO 55001 § 8.3: outsourced work is still yours; control it and keep the evidence.
   - ISO 9001 § 8.4: say what you require of a vendor, and check how they did.
   - EN 13306: vendor PM is preventive, a call-out is corrective, waiting for the vendor is logistic delay.
4. **The register** — mock-up `01-contracts-list.html`
   - Managers and engineers, in Masters › Contracts.
   - Each contract with its status: *In force*, *Ends in 25 days*, *Ended*; cost for managers only.
5. **Adding a contract** — mock-up `02-contract-dialog.html`
   - The engineer fills vendor, period, coverage ticks, PM visits per year, response time.
   - The manager adds the cost.
6. **One contract** — mock-up `03-contract-page.html`
   - Terms, machines covered, the signed contract, the vendor's breakdown calls.
   - PM visits agreed against done appears when PM is built.
7. **On the machine** — mock-up `04-equipment-under-contract.html`
   - Technicians and operators, from the QR label on a phone.
   - "Under AMC with Atlas Copco until 31-03-2027": call the vendor, do not open it.
8. **On the ticket** — mock-up `05-ticket-contract-hint.html`
   - The engineer sees the contract and assigns the vendor.
   - The ticket then counts as a breakdown call on the contract.
9. **The items as a timeline**
   - Now: R02.1 register → R02.2 machines → R02.3 documents ∥ R02.5 reminders → R02.4 renewal → R02.6 breakdown calls.
   - With PM (phase 4): R02.7 PM visits. With reports (phase 5): R02.8 vendor performance.
10. **Your decisions (1 of 2)**
    - Q1.1 types · Q1.2 who sees · Q1.3 who edits · Q1.4 coverage · Q1.5 one site · Q1.6 vendor record · Q1.7 cost · Q1.8 where it lives.
11. **Your decisions (2 of 2)**
    - Q2.1 levels · Q2.2 two contracts · Q3.1 documents · Q4.1 renewal · Q5.1 reminders · Q6.1 which tickets · Q6.2 vendor arrival · Q7.1 PM link.

## Log

- 27-10-2026 — **Re-approved at gate R** after reading five real documents in `scratch/` (VP Power, Fuji quote and annexure, two Toyota quotes): D7 (mixed quote = two contracts), D8 (price per machine, supersedes Q1.7), D9 (only-the-vendor-repairs tick), D10 (call-out number for engineers, managers and admin, through a third key `contract:read`). The documents also confirm Q1.5 (Toyota quotes each company apart), 4 PM visits a year, breakdown calls included / unlimited / not included, and the 60-day reminder (Fuji: renewal two months before expiry).
- 27-10-2026 — **Approved at gate R** by KLA: the rest as recommended; Plan.MD § 2 updated.
- 27-10-2026 — Gate R answers so far: D5 (two read keys, `read_basic` all but price and documents, `read_senior` managers; Q1.2, Q3.1), D6 (Q4.1 a).
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
