```
Roadmap: R05 — Improvement and root-cause analysis (RCA)
Doc: roadmap
Author: Roadmapper (Opus)
Date: 29-10-2026
Status: Approved (gate R, 30-10-2026, KLA): R05.7, R05.8, R05.9 deferred; every other answer (a)
```

# R05 — Improvement and root-cause analysis (RCA)

**The point:** R05 adds an **Improvement** record in **10 items**. The team analyses
TK-2026-10-002 (the dusty contactor) after the **first three** (R05.1–R05.3): problem, why-why to
the root cause, and countermeasures with an owner and a due date. The verified close follows in
R05.4. Lessons for the floor come in R05.6–R05.7. The link to PM plans waits for R03.2 (R05.9).
KLA has **22 questions** to answer (§ Decisions). R05.1 waits only for Q0.1 and Q1.1–Q1.4.
The effort is about **12 step-days** (estimate, § Order).

## The feature

**What (KLA, 29-10-2026):** a closed ticket in production, TK-2026-10-002, a breakdown raised
28-10-2026 15:15: "The main contactor's NC auxiliary contact was not passing the control supply.
After cleaning the contactor contacts, the supply was restored and the machine started working
normally." It was closed 29-10-2026 11:23 with the note "Contactor cleaned". KLA wants the team to
find the root cause and learn from it: clean contactors before they fail, keep dust out of panels,
blow panels out with air.

**Why Yantra cannot do it today (fact):**
- A closed ticket is final and read-only. A work note needs an open ticket
  (`backend/tickets.py`: `add_note` → `_lock_open_ticket`, 409 on a closed ticket).
- "Not fixed" is a new linked ticket, never a reopen (Plan § 9 Q4; S018).
- The ticket's cause code (ISO 14224, S016) says why *this part* failed. Nothing records why the
  plant let it fail, what the team will change, who does it by when, and whether it worked.

**Where the product plan already points (fact):**
- Maintenance-Philosophy § 3, *Focused improvement* row: "Remove chronic losses: why-why /
  root-cause analysis", brought forward for the presses, with the welded output relays and the
  door sensor as first targets, and *maintenance prevention* named.
- Plan § 4.6 *Chronic problems*: "TPM focused improvement, brought forward for the presses."
- Plan § 1 *Standards*: ISO 9001 § 10.2 "nonconformity and corrective action (tickets with cause
  and action codes)". Tickets give the *reaction*; the corrective action and its review are
  missing.
- Glossary, *Repeat failure*: "the fix did not hold (TPM focused improvement; ISO 9001 § 10.2)".
- Plan § 4.3a *Procedures* (proposed): one-point lessons for the training pillar.
- Plant-Facts § 4: "Press PLC panels get dusty and need frequent cleaning"; the electrical head's
  daily report: "7 packing machines cleaned with air".

**What it is not:** no cost of loss (Plan § 2: no maintenance cost in v1), no FMEA or RCM study,
no safety-incident investigation, no full Procedures master (only its one-point-lesson kind).

## What exists

Checked against HEAD `32eb122` (29-10-2026). Nothing of improvement is built: no table, no key
in `backend/config_rbac.py`, no screen; `grep -i "improvement|root.cause|chronic"` in `backend/`
finds nothing outside `.venv`.

| Piece | State today | Evidence | How R05 uses it |
|---|---|---|---|
| Tickets, events, timeline | Built (S017, S018, S027) | `tickets`, `ticket_events`; closed is final (`_lock_open_ticket`) | Improvements link tickets; the closed ticket stays untouched. Its page shows the link, derived. |
| Repeats | Built (S018, S025) | `tickets.repeat_of_id`; `REPEAT_WINDOW_DAYS` 7; `_repeats()` | A repeat is a trigger for an improvement (R05.8). |
| Failure codes | Built (S016) | `failure_modes` (per class or General), `failure_causes` with ISO's five `cause_group`s (seed `1.1`…`5.6`), `maintenance_actions`; a code is frozen once used | The root cause picks from `failure_causes` (R05.2). The watch checks the failure mode (R05.4). |
| Downtime, repair time | Built (S018, S019) | computed from events, never stored | The problem's loss and the before / after figures (R05.1, R05.4). |
| Team and memberships | Built (S010, S011) | `people`, `memberships`; people without a login (S017) | Countermeasure owners. |
| Site-scoped RBAC | Built (S011) | `SITE_SCOPED`, `has_perm_at`, `accessible_unit_ids` | Every new key is site-scoped (§ RBAC deviation). |
| *Me* › *Open work* | Built (S031, S035) | open tickets assigned to me | Countermeasures I own join it (R05.3). R03.4 adds PM jobs to the same tab. |
| Alerts | Built (S021, S032) | `alerts_core.KINDS` = breakdown, defect, escalation, assigned, closed; `CHANNELS`; tasks `ticket_alert` | New kinds for countermeasures (R05.5). The core is ticket-shaped today. |
| Worker and daily schedule | Built (S013) | `scheduled_tasks.SCHEDULE`, `task_handlers.HANDLERS` | A daily task finds overdue countermeasures and ended watches (R05.5). |
| Documents and photos | Built (S006, S008) | `equipment_documents`, CHECK `chk_equipment_documents_owner`: one of equipment, model, ticket | A countermeasure photo (R05.3) and lesson photos (R05.6) add owners. |
| Serial numbers | Built (S017) | `serial_counters`; `tickets_core.serial_scope` gives `TK:YYYY-MM` | `IM-YYYY-MM-NNN` (Q0.1). R03.3 adds `PM-` the same way. |
| Time field | Built (S051) | the *Now* tick | *Done on* for a countermeasure. |
| Procedures, one-point lessons | Proposed, not built | Plan § 4.3a; `docs/schema.md` § Planned: `procedures`, `procedure_items`, `procedure_completions`; queued *Procedure master* | R05.6 builds the first kind (one-point lesson); R05.7 the completion records. |
| PM plans, templates | Roadmap R03, approved, not built | R03.2 (`pm_plans`), R03.8 (templates) | A preventive countermeasure becomes a PM plan (R05.9). |
| Chronic problems report | Proposed, not built | Plan § 4.6; `report:read` is not in `config_rbac.py` yet | R05.8 builds its core as the *Suggested* list. |

**What no item rebuilds:** the ticket flow and its repeat link, the failure-code masters, the
downtime figures, the Team pickers, the documents store, the alert channels, the worker, the time
field, and R03's PM plans and templates.

## Standards

Clause numbers already used in Plan.MD are given plain; others are marked *to verify*.

| Standard | What it says, in plain words | How R05 follows it | Items |
|---|---|---|---|
| **TPM — Focused improvement** (*Kobetsu Kaizen*) | A small team takes one chronic loss, finds its root cause and removes it for good. It does not stop at the repair. | The Improvement record: one problem, its tickets, the analysis, the countermeasures, the check that the loss went away. | R05.1–R05.4 |
| **TPM — why-why analysis** (5 whys) | Ask "why?" again and again until the answer is something the plant can change: a method, a standard, a design. "The contact was dirty" is not a root cause; "nobody cleans the panels" is. | An ordered chain of *Why … ? / Because …* lines, with evidence, ending in a root cause (Q2.1). | R05.2 |
| **TPM — horizontal deployment** (*Yokoten*) | A fix found on one machine is applied to the similar machines before they fail too. | A countermeasure kind *Spread* (Q3.1); a lesson shown on every machine of the class (Q6.2). | R05.3, R05.6 |
| **TPM — maintenance prevention** (MP, design-out) | Remove the failure mode instead of maintaining it: a sealed part, a better design. Maintenance-Philosophy names the solid-state relays. | A countermeasure kind *Design-out*. | R05.3 |
| **TPM — one-point lesson** (training pillar) | One page, one point, mostly a picture: what to do and why. Written by the person who knows; shown to the team at the machine. | The lesson (R05.6) and the record of who was shown it (R05.7). | R05.6, R05.7 |
| **ISO 9001:2015 § 10.2** (the next edition, due around 2026: numbers *to verify*) | When something goes wrong: (a) react and correct it; (b) find the causes, and whether it can happen elsewhere; (c) act; (d) review whether the action worked; (f) change the system if needed. **§ 10.2.2:** keep records of what went wrong, what was done and the result. | (a) is the ticket. (b) is the why-why and *Spread*. (c) is the countermeasures. (d) is the verified close. (f) is a PM plan or a lesson. The record keeps all of it. | R05.1–R05.4, R05.9 |
| **ISO 9001 § 7.5.3** | Records are kept, protected from change, and show who did what and when. | Each line carries who and when; a closed improvement is read-only; the timeline (R05.4). | R05.1–R05.4 |
| **ISO 9001 § 7.1.6** organisational knowledge | The organisation keeps the knowledge it learned, including lessons from failures. | Lessons on the machine and its class; closed improvements searchable. | R05.6, R05.10 |
| **ISO 9001 § 7.2, § 7.3** competence and awareness | People are trained for their work and know how their actions matter. Records show it. | *Shown to* records per lesson. | R05.7 |
| **ISO 9001 § 9.3** management review, **§ 10.3** continual improvement | Management reviews the corrective actions and their results at set times. | The improvement register, printable (R05.10). | R05.10 |
| **ISO 14224** — failure cause (clause and Table B.3 numbers *to verify*) | *Failure cause*: the circumstances in design, manufacture or use that led to a failure, in five groups. A ticket's cause is often the immediate one; the standard leaves root-cause analysis to separate methods. | The ticket keeps its own cause (Q2.3). The improvement records the **root cause** from the same cause list, so both roll up the ISO way. | R05.2 |
| **IEC 62740:2015** root cause analysis (content *to verify*) | A standard on how to run an RCA: describe the problem, collect evidence, find causes, check them, act. It lists why-why, fishbone and fault-tree methods. | R05 follows its order: problem → evidence on each why → root cause → actions → review. Only why-why is built (Q2.1). | R05.1–R05.4 |
| **EN 13306** (term numbers *to verify*) | *Corrective maintenance*: after a fault is found. *Preventive maintenance*: to lower the chance of failure. *Improvement maintenance*: to raise reliability, maintainability or safety without changing the item's function. | Countermeasure kinds use these words: *Corrective*, *Preventive*, *Design-out* (improvement maintenance). | R05.3 |
| **ISO 55001** § 10 nonconformity and corrective action, continual improvement (numbers differ between the 2014 and 2024 editions: *to verify*) | The asset-management system corrects what went wrong and improves itself. | The same loop as ISO 9001 § 10.2. | R05.4 |
| **SMRP — MTBF** (metric 3.5.1, as Plan § 4.5 cites; *to verify*) | Mean time between failures: it rises when a root cause is removed. | The verify screen shows failures and downtime before and after (R05.4). Full MTBF waits for the phase 5 reports. | R05.4 |
| **ISO 27001 A.5.3** segregation of duties | One person should not both do and approve the same work, where the risk calls for it. | Q4.2: may the lead verify their own improvement? Tickets and PM allow self-sign-off, recorded. | R05.4 |

## Showcase

Who uses improvements and what each can do (in the app's words):

- **Engineer** (desk and phone)
  - On a closed breakdown I tap *Start improvement*. The ticket links to it and stays as it was.
    (01)
  - I write the problem, then the why-why: *Why did the press not start?* … until I reach a cause
    the plant can change. I pick the root cause from the cause list. (02)
  - I add countermeasures, each with a kind, an owner and a due date: replace the gasket, a
    monthly panel clean on every press, a sealed contact block. (03)
  - I see *Suggested* improvements: repeats, long breakdowns, one symptom again and again. (07)
  - I write a one-point lesson with two photos, in Tamil, for the press operators. (06)
- **Technician** (phone)
  - I see my countermeasures on *Me › Open work*, with the due date. I mark one done with what I
    did and a photo. (04)
  - I add a note to the improvement: "Same dust seen on HP005's panel last month."
- **Maintenance manager** (desk)
  - After the watch period I see whether the failure came back, and the figures before and after.
    I *Close as effective* or send it back to be analysed again. (05)
  - I print the register of open and closed improvements for the monthly review.
- **Production supervisor** (phone)
  - I open the lesson on the press's page and show it to my operators. I record who was shown.
    (06)
- **Operator** (phone, later the kiosk)
  - I scan the press's QR and see the lesson: a picture and one line in Tamil.

## Gate R (30-10-2026, KLA)

- **Approved**, with **R05.7, R05.8 and R05.9 deferred** ("not needed now"). They stay in the
  roadmap with status `deferred`, and their questions Q7.1, Q8.1 and Q9.1 stay open until one is
  taken up.
- **Every other question: (a)**, the recommendation: Q0.1, Q1.1–Q1.4, Q2.1–Q2.3, Q3.1, Q3.2,
  Q4.1–Q4.3, Q5.1, Q6.1–Q6.3, Q10.1.
- **Q0.2, the order:** KLA asked to plan and build the rest of R05 now (R05.1–R05.6, R05.10), one
  step after the other, before R03's milestone 1. This goes beyond (a), which put only R05.1–R05.3
  first.
- **How the steps run (KLA):** each step is briefed and reviewed through all its rounds, then
  coded without stopping at gate A, unless a review raises a defining, breaking or show-stopping
  question. Gate B stays: KLA commits each step.
- **Consequences of the deferrals (orchestrator):** without R05.8 there is no *Suggested* list
  and no hint on the ticket page; the engineer starts each improvement by judgement. Without
  R05.9 a *Preventive* countermeasure is done when its owner marks it done, like the other kinds.
  Without R05.7 a lesson has no *shown to* record. Milestone 2 is R05.4 and R05.5; milestone 3 is
  R05.6 and R05.10.

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R05.1 | Improvement record: start from tickets, the problem, linked tickets, the list; the ticket shows the link | L | full | — | → S067 (backend) + S068 (screens), 30-10-2026 |
| R05.2 | Why-why and the root cause | M | full | R05.1 | → S069, 30-10-2026 |
| R05.3 | Countermeasures: kind, owner, due date, done; on *Me › Open work* | L | full | R05.1 | → S070 (backend) + S071 (screens), 30-10-2026 |
| R05.4 | States, timeline and notes; the watch period; verified close | L | full | R05.2, R05.3 | → S072 (backend) + S073 (screens), 30-10-2026 |
| R05.5 | Alerts: countermeasure given to you, overdue, watch ended | M | full | R05.3, R05.4 | → S074, 30-10-2026 |
| R05.6 | One-point lessons: the first kind of the Procedures master | L | full | R05.3 | → S075 (backend) + S077 (screens), 30-10-2026 |
| R05.7 | Who was shown a lesson (completion records) | M | full | R05.6 | deferred |
| R05.8 | *Suggested* improvements: the when-to-analyse rule | M | full | R05.1 | deferred |
| R05.9 | A preventive countermeasure becomes a PM plan | M | full | R05.3, R03.2, R03.8 | deferred |
| R05.10 | The improvement register, printable for the review | S | full | R05.4 | → S076, 30-10-2026 |

**Size and the step rule (fact):** R05.1 adds two tables, a record and its ticket links, as R03
counted a plan and its items (R03 § Items, feedback raised there). It is one concern with two
screens and a line on the ticket page. If a brief passes 25 files, it splits there.

### R05.1 — Improvement record from tickets

- **Goal:** an engineer starts an improvement from one or more tickets and writes the problem. The
  team sees it beside the tickets.
- **What it builds:**
  - Tables `improvements` (serial `IM-YYYY-MM-NNN` per Q0.1, site, the machine, title, problem
    text, state, lead, created by and when) and `improvement_tickets` (the links; at most one open
    improvement per ticket, Q1.4).
  - *Start improvement* on the ticket page for tickets per **Q1.1** (back in service or closed),
    shown to `improvement:edit` holders at the ticket's site. *Add ticket* on the improvement links
    more tickets of the same site.
  - The **improvement page** (mock-up 02, left half): the problem and the linked tickets, with
    each ticket's symptom, cause and downtime, and the sum. Downtime is computed as today, never
    stored.
  - The **ticket page** shows "Analysed in IM-2026-10-001 · Analysing", derived from the link. The
    closed ticket row is not written (Plan: closed is final).
  - The list (mock-up 07, left): *Open* and *Closed*, filter by unit; where it lives per **Q1.2**.
  - Keys per **Q1.3**: `improvement:read`, `improvement:edit`, both in `SITE_SCOPED`.
  - The serial helper takes a prefix (`tickets_core.serial_scope` is `TK:` only); R03.3 needs the
    same for `PM-`, so whichever goes first generalises it.
- **After it:** TK-2026-10-002 has its improvement with the problem written down.
- **Standards:** TPM focused improvement; ISO 9001 § 10.2.1 (a), § 10.2.2.
- **Migrations:** one (two tables). **Leaves for later:** a named team of people on the record; an
  improvement with no ticket (Q1.1 b).

### R05.2 — Why-why and the root cause

- **Goal:** the analysis itself: from the symptom to a cause the plant can change.
- **What it builds:**
  - Table `improvement_whys`: order, the question, the answer, evidence (optional), who and when.
    Shape per **Q2.1**.
  - The root cause on `improvements`: a text and one cause from `failure_causes` (per **Q2.2**).
    Using a cause freezes it, as a ticket does (S016).
  - The page shows the ticket's cause beside the root cause, with one line on the difference
    (mock-up 02). The ticket's code is not changed (**Q2.3**).
  - Help text on the why-why card: "Ask why until the answer is something the plant can change."
- **After it:** the full analysis of TK-2026-10-002 is on record.
- **Standards:** TPM why-why; ISO 14224 failure cause and cause groups; IEC 62740; ISO 9001
  § 10.2.1 (b).
- **Migrations:** one (a table and two columns). **Leaves for later:** a fishbone (4M) view;
  branches (Q2.1 b).

### R05.3 — Countermeasures

- **Goal:** each countermeasure has an owner and a due date, and is marked done with what was done.
- **What it builds:**
  - Table `improvement_actions`: kind (per **Q3.1**: *Correction*, *Corrective*, *Preventive*,
    *Design-out*, *Lesson*, *Spread*), text, owner (per **Q3.2**), due date, state (open / done /
    cancelled with a reason), done text, done time (the *Now* tick, S051), done by.
  - The countermeasures card (mock-up 03): *Add countermeasure*, edit, cancel; *Overdue* badge
    past the due date.
  - *Me › Open work* lists my open countermeasures beside my tickets (mock-up 04). The owner marks
    their own one done; `improvement:edit` holders mark any. Which ones a user may mark is decided
    by data (owner), as `pm_job:work` is (Plan § 3).
  - A photo on *Mark done* through the documents store: one more owner in
    `chk_equipment_documents_owner`.
- **After it:** milestone 1. The team's actions on the contactor case are owned and tracked.
- **Standards:** ISO 9001 § 10.2.1 (c); EN 13306 corrective, preventive, improvement
  maintenance; TPM maintenance prevention and yokoten.
- **Migrations:** one (a table and the CHECK). **Leaves for later:** a checklist of machines for
  *Spread* (each machine ticked as done).

### R05.4 — States, timeline and the verified close

- **Goal:** the loop closes only when someone checks that the fix worked (ISO 9001 § 10.2.1 (d)).
- **What it builds:**
  - Table `improvement_events`: the timeline (as `ticket_events`): started, ticket linked, why
    added, root cause set, countermeasure added or done, notes, state changes.
  - States: *Analysing* → *Actions open* (root cause set) → *Watching* (every countermeasure done
    or cancelled) → *Ready to verify* (watch ended) → *Closed: effective* or *Closed: not
    effective*; *Dropped* with a reason from any open state. An event backfills R05.1–R05.3's
    records.
  - The watch per **Q4.1**: Yantra counts tickets with the same symptom on the linked machines
    after the last countermeasure, and shows breakdowns, that symptom and downtime before and after
    (mock-up 05). A ticket that comes back during the watch is shown per **Q4.3**.
  - *Close as effective* and *Not effective — analyse again* (remark required); *not effective*
    starts a new improvement linked to it, with the same tickets. Key `improvement:verify` per
    **Q4.2**, in `SITE_SCOPED`.
  - *Add note* on the timeline for every `improvement:read` holder at the site (Q1.3).
  - A closed improvement is read-only.
- **After it:** the full loop of ISO 9001 § 10.2.
- **Standards:** ISO 9001 § 10.2.1 (d), § 7.5.3; ISO 55001 § 10; SMRP MTBF (data only); ISO 27001
  A.5.3 (Q4.2).
- **Migrations:** one (one table). The watch's figures are computed, never stored. Pure core
  first: the state rules and the watch count are plain functions (CLAUDE-COMMON *Pure core, thin
  shell*).

### R05.5 — Alerts

- **Goal:** owners hear about their countermeasures; nothing waits unseen.
- **What it builds:** per **Q5.1**, kinds in `alerts_core`: *Countermeasure given to you* (push to
  the owner, not when the owner gave it to themselves); *Countermeasure overdue* (push once to the
  owner and the lead); *Ready to verify* (push to the verifiers of the site). A daily task in
  `scheduled_tasks.SCHEDULE` finds overdue countermeasures and ended watches. An owner without a
  login gets nothing; the lead gets the overdue alert.
- **Note (fact):** `alerts_core` and the `ticket_alert` task are shaped for tickets. R03.7 (PM
  alerts) needs the same widening; whichever goes first does it, and the second reuses it.
- **Standards:** ISO 9001 § 10.2 (actions done on time).
- **Migrations:** none. **Leaves for later:** email (one entry in `CHANNELS`).

### R05.6 — One-point lessons

- **Goal:** what the team learned reaches the floor as a picture and one line, in Tamil where
  needed (Plant-Facts § 4: operators are not trained before use; the owner wants Tamil with
  pictures).
- **What it builds:**
  - The first slice of the Procedures master (Plan § 4.3a), per **Q6.1**: table `procedures`
    with kind *one-point lesson* only (title, short text, the machine or the class per **Q6.2**,
    who changed it and when; the other kinds come with their own roadmap). Serial `OPL-NNN`
    (to settle in the brief).
  - Photos through the documents store (one more owner).
  - A *Lessons* card on the equipment page (the machine's and its class's), and the lesson page
    (mock-up 06), large text for a phone. A countermeasure of kind *Lesson* links its lesson.
  - Key `procedure:edit` per **Q6.3**. Site rule: a lesson on a machine is site-scoped; one on a
    class is a site-less master, edited by the key held at any site (as failure codes and R03.8's
    templates).
- **After it:** the operators of every press see "Keep the panel door shut".
- **Standards:** TPM one-point lesson, training pillar, yokoten; ISO 9001 § 7.1.6, § 7.5.
- **Migrations:** one (one table and the CHECK). **Leaves for later:** steps in the shared item
  shape, the other kinds (work instruction, diagnostic, onboarding), the lesson on PM templates.

### R05.7 — Who was shown a lesson

- **Goal:** a record that the team learned it (ISO 9001 § 7.2, § 7.3; Plan § 4.3a *completion
  record*, the seed of the skill matrix).
- **What it builds:** table `procedure_completions` (person, lesson, date, recorded by);
  *Record who was shown* on the lesson page (pick several people with a membership at the site,
  operators without a login included, S017); the list on the lesson. Per **Q7.1**. Key per Q6.3
  (a supervisor records it).
- **Migrations:** one (one table). **Leaves for later:** "who has not seen it yet" against a
  unit's operators; the skill matrix; blocking CIL for the untrained (Plan § 4.3a).

### R05.8 — Suggested improvements

- **Goal:** Yantra points at the losses worth analysing, so the choice is not memory alone.
- **What it builds:**
  - A pure core: for each ticket and machine, whether the rule of **Q8.1** holds: a repeat; a grade
    A breakdown down N hours or more; the same symptom on the same machine M times in D days.
  - The *Suggested* list (mock-up 07, right): candidates with no improvement yet, with the reason.
    This is the core of Plan § 4.6 *Chronic problems* (per machine or component and symptom).
  - The hint on a qualifying ticket's page (mock-up 01).
  - The numbers as settings in Settings › Notifications or a new card (the brief decides).
- **Standards:** TPM focused improvement (chronic losses first); Glossary *Repeat failure*.
- **Migrations:** none expected (settings rows; the brief checks). **Leaves for later:** the
  printed chronic-problems report with Excel export (phase 5).

### R05.9 — A preventive countermeasure becomes a PM plan

- **Goal:** a *Preventive* countermeasure lives on as planned work, not as a one-time task.
- **What it builds:** on a *Preventive* countermeasure, *Link PM plan*: pick an existing plan or
  a template's application (R03.2, R03.8), or open the plan editor seeded with the
  countermeasure's text. The countermeasure is done when its plan is active (per **Q9.1**). The plan
  shows "From IM-…". The watch (R05.4) shows the plan's jobs.
- **After it:** "Monthly: blow the panel out, clean the contactors, check the gasket" runs on every
  press as a PM plan. R03's own mock-up 04 already shows the item "Blow the dust out of the PLC
  panel".
- **Standards:** ISO 9001 § 10.2.1 (f) (change the system); TPM planned maintenance.
- **Migrations:** one (a link column). **Depends on** R03.2 and, for a class, R03.8.

### R05.10 — The improvement register

- **Goal:** the measure and the review (ISO 9001 § 9.3, § 10.3).
- **What it builds:** per site and period: improvements started, open by state and age,
  countermeasures overdue, closed effective and not effective; print. Per **Q10.1**. Key
  `report:read` (Plan § 3; R03.14 may create it first).
- **Migrations:** none. **Leaves for later:** Excel export (Plan § 4.6), the dashboard.

## Order

**Milestone 1 — the contactor case analysed and owned (R05.1–R05.3, about 4.5 step-days).**

1. **R05.1 first.** Everything else hangs on the record. It can run beside **R03.1** (PM's pure
   scheduling core, no migration, no shared file): one parallel pair across the two roadmaps.
2. **R05.2**, then **R05.3** (both add a migration, so not in parallel). After R05.3 the team has
   the full analysis and owned actions: the smallest slice that gives value before PM and
   Procedures exist.

**Milestone 2 — the closed loop (R05.4, R05.5, R05.8; about 3.5 step-days).**

3. **R05.4.** The verified close; it needs whys and countermeasures to exist.
4. **R05.5 ∥ R05.8.** Alerts change `alerts_core`, `task_handlers` and the schedule; suggestions
   are a new pure file, the list tab and the ticket-page hint. No migration in either.

**Milestone 3 — learning (R05.6, R05.7, R05.10; about 3.25 step-days).**

5. **R05.6**, then **R05.7 ∥ R05.10.** Lessons before their completion records; the register has
   no migration and shares no file with R05.7.

**Milestone 4 — with PM (R05.9, about 1 step-day).**

6. **R05.9** after R03.2 (a plan on a machine) and R03.8 (a template for the class).

**How R05 fits with R03 (per Q0.2):** recommended, R05's milestone 1 first (KLA's case is waiting,
and none of it needs PM), then R03's milestone 1, then the rest of R05 between R03's milestones.

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
R05.1 ∥ R03.1; R05.5 ∥ R05.8; R05.7 ∥ R05.10.

**Not in parallel:**
- R05.2, R05.3, R05.4, R05.6 each add a migration.
- R05.3 and R03.4 both change *Me › Open work*.
- R05.5 and R03.7 both widen `alerts_core`.
- R05.3, R05.6, R03.6 and R03.17 each change `chk_equipment_documents_owner`.

**Effort (estimate):** S about half a day, M about one day, L about 1.5–2 days of step time with
reviews: about **12 step-days** in all. Assumption: the briefs settle no new questions.

## Decisions for the user

Questions are numbered by their item, as in R03: Q3.1 is the first question of R05.3. Q0.n are
about the whole roadmap. Answer as "3.1 a".

**Q0.1. What is the record called in the app?** Waits: R05.1.
- **(a) *Improvement*, serial `IM-YYYY-MM-NNN` — recommended.** A plain word a technician follows.
  It is TPM's name (focused improvement); RCA is one tool inside it.
- (b) *RCA*, serial `RCA-…`. Exact, but jargon on the floor.
- (c) *Corrective action* (CAPA), as ISO 9001 says. Office words; it also hides design-out and
  lessons.

**Q0.2. When is R05 built, against R03?** Waits: the queue.
- **(a) R05.1–R05.3 first, then R03's milestone 1, then the rest of R05 between R03's milestones —
  recommended.** A real case is waiting, milestone 1 needs no PM, and R05.1 runs beside R03.1. PM
  starts about 4.5 step-days later.
- (b) After R03's milestone 1. PM first; the contactor case waits about a week more.
- (c) After all of R03 (about 20 step-days).

**Q1.1. What may an improvement start from?** Waits: R05.1.
- **(a) One or more tickets that are back in service or closed — recommended.** An analysis needs
  the repair to be over. Tickets you add later may be in any state.
- (b) Also with no ticket: an idea, a near miss, a PM finding. Wider, but the problem then has no
  machine record behind it. Easy to add later.
- (c) Closed tickets only. The engineer waits for the close before starting.

**Q1.2. Where do improvements live in the nav?** ("Module" = a sidebar section.) Waits: R05.1.
- **(a) A tab *Improvements* on the *Tickets* page — recommended.** No new nav item: the phone's
  bottom bar already has five, and R03.3 adds *PM*. Improvements sit beside the tickets they
  come from.
- (b) A nav item of its own, *Improve* (a module). Easier to find; the bottom bar grows to seven.
- (c) Only on *Me* and on the ticket. Nobody sees the list.

**Q1.3. Who sees and who writes?** Waits: R05.1, R05.4. All keys site-scoped.
- **(a) `improvement:read` for the operator and up, and IT admin; `improvement:edit` (start, the
  problem, whys, countermeasures) for engineers and so managers; notes on the timeline for every
  reader; IT admin reads only — recommended.** TPM wants operators to see and add to the analysis;
  the engineer leads it. IT admin reads only, as R03 Q2.2 decided for PM.
- (b) Read from the technician up only. Operators see lessons but not the analysis.
- (c) Technicians also write whys and countermeasures. More hands, less order.

**Q1.4. In how many improvements can one ticket be?** Waits: R05.1.
- **(a) In at most one open improvement; a *not effective* improvement passes its tickets to its
  follow-up — recommended.** One place to look; no two teams on the same failure.
- (b) Any number. A ticket can feed a machine analysis and a plant-wide one.

**Q2.1. What shape has the why-why?** Waits: R05.2.
- **(a) One chain of *Why? / Because* lines, any length, each with optional evidence; a free text
  for contributing causes — recommended.** Simple to fill on a phone; it is the classic TPM form.
- (b) A tree: each answer may branch into several whys. Closer to real failures; harder to show
  on a phone.
- (c) A fishbone by 4M (man, machine, method, material) plus environment. A different tool, better
  for team brainstorming at a desk.

**Q2.2. How is the root cause recorded?** Waits: R05.2, R05.4.
- **(a) A text and one cause from the existing cause list (Masters › Failure codes), required
  before *Watching* — recommended.** Root causes then count by ISO group beside the tickets'
  causes.
- (b) A text only. Nothing to count.
- (c) A separate root-cause list (e.g. 4M). A second master to keep.

**Q2.3. May the analysis change the ticket's cause code?** Waits: R05.2.
- **(a) No. The closed ticket stays as it was; the improvement shows both causes — recommended.**
  Plan: closed is final (ISO 9001 § 7.5.3). The two codes answer different questions.
- (b) Yes, the engineer corrects it through the improvement, with a timeline line. A departure
  from "closed is final".

**Q3.1. Which kinds of countermeasure?** Waits: R05.3.
- **(a) Six fixed kinds: *Correction*, *Corrective*, *Preventive*, *Design-out*, *Lesson*,
  *Spread* — recommended.** Each maps to ISO 9001 § 10.2, EN 13306 or TPM, and R05.6 and R05.9
  hang off two of them.
- (b) Free text, no kind. Nothing to count or to link.
- (c) ISO 9001's three: correction, corrective action, preventive action. Design-out, lessons and
  spreading then hide under "corrective".

**Q3.2. Who can own a countermeasure?** Waits: R05.3.
- **(a) Anyone with a membership at the site, a person without a login too; such an owner gets no
  alert, and the lead marks the work done — recommended.** The fitter without a phone can own the
  gasket job (Plant-Facts § 5).
- (b) Only people with a login. Simpler alerts; some work is credited to the wrong person.

**Q4.1. How is "it worked" checked?** Waits: R05.4.
- **(a) A watch period, default 90 days from the last countermeasure done, set per improvement
  from 30 to 365; Yantra counts the same symptom on the linked machines and shows before and after;
  the verifier decides — recommended.** Dust builds up over months, so 30 days proves little.
- (b) A fixed 30 days for every improvement.
- (c) No watch: verify as soon as the countermeasures are done. Effectiveness is then a guess.

**Q4.2. Who verifies?** Waits: R05.4.
- **(a) An engineer or manager of the site, the lead too, recorded as such — recommended.** The
  plant has few engineers; tickets (self-close) and PM (R03 Q5.2) allow the same. A recorded
  departure from ISO 27001 A.5.3.
- (b) The manager only.
- (c) Anyone with the key except the lead.

**Q4.3. What does a repeat during the watch do?** Waits: R05.4.
- **(a) It shows on the improvement with a warning; the watch goes on; the verifier decides —
  recommended.** A repeat may have another cause (a new contactor fault, not dust).
- (b) It ends the watch at once as *not effective*.

**Q5.1. Which alerts?** Waits: R05.5.
- **(a) Push: *Countermeasure given to you* to the owner; *Countermeasure overdue* once to the
  owner and the lead; *Ready to verify* to the site's verifiers — recommended.** The channels exist
  (S021); email is one line later.
- (b) As (a), plus email to the site's managers for overdue countermeasures.
- (c) No alerts; the lists and *Me* only.

**Q6.1. How is the one-point lesson built?** Waits: R05.6.
- **(a) As the first kind of the Procedures master (Plan § 4.3a), `procedures` with kind
  *one-point lesson* only — recommended.** Nothing is built twice; the other kinds join later.
- (b) A lesson text on the improvement only. Quick, but the lesson is not on the machine.
- (c) Wait for a Procedures roadmap. The learning output waits.

**Q6.2. Where does a lesson show?** Waits: R05.6.
- **(a) On the improvement's machine, and on every machine of its class when ticked — recommended.**
  Yokoten: every press's operators see it.
- (b) On the one machine only.

**Q6.3. Who writes lessons and records who was shown?** Waits: R05.6, R05.7.
- **(a) Engineers and managers write (`procedure:edit`); supervisors, engineers and managers record
  who was shown — recommended.** Plan § 4.3a: "edited by engineers"; supervisors run the floor
  briefings.
- (b) Supervisors also write lessons. TPM lets operators and supervisors write one-point lessons
  on autonomous maintenance; content control is looser.

**Q7.1. Record who was shown a lesson?** Waits: R05.7.
- **(a) Yes, as R05.7 — recommended.** The seed of the skill matrix (Plan § 4.3a); evidence for
  ISO 9001 § 7.2.
- (b) Not in R05.

**Q8.1. When should the team analyse a failure?** (the when-to-do-an-RCA rule) Waits: R05.8.
- **(a) Yantra suggests; the engineer decides. Suggested: every repeat; a grade A breakdown down 4
  hours or more; the same symptom on the same machine 3 times in 90 days. The numbers are settings —
  recommended.** The plant has few engineers; forcing an RCA for each of hundreds of breakdowns
  gives empty forms. An engineer may start one for any ticket.
- (b) Every breakdown needs an improvement or a written reason why not. Thorough; heavy at this
  plant's maturity (Maintenance-Philosophy § 1: no TPM yet).
- (c) No rule; the engineer's judgement only. No *Suggested* list.

**Q9.1. When is a *Preventive* countermeasure done?** Waits: R05.9.
- **(a) When its PM plan is active — recommended.** The plan then carries the work; the watch
  shows its jobs.
- (b) When the plan's first job is verified. Surer, but the improvement waits up to a full
  interval.

**Q10.1. Build the register report in R05?** Waits: R05.10.
- **(a) Yes, as R05.10, printable — recommended.** ISO 9001 § 9.3 asks for it at the review.
- (b) Later, with the phase 5 reports.

**Not asked again (decided in Plan.MD, followed as written):** closed is final and "not fixed" is
a new ticket (Plan § 9 Q4); the ISO 14224 cause list with five groups (S016); the repeat window of
7 days (S018); recorded on behalf and people without a login (S017); no maintenance cost (Plan
§ 2); push as the only alert channel besides the managers' email (§ 4.7); the procedure fields of
§ 4.3a.

**Departures from Plan.MD proposed here:**
- The one-point-lesson kind of § 4.3a is built ahead of the rest of the Procedures master (Q6.1).
- The *Suggested* list is the first form of § 4.6's chronic-problems report, ahead of phase 5
  (R05.8).
- New keys not in § 3's first cut: `improvement:read`, `improvement:edit`, `improvement:verify`,
  `procedure:edit`.

## Out of the roadmap and risks

**Out (fact):**
- Fishbone, fault tree, P-M analysis, FMEA and RCM studies.
- A named team on the improvement; an improvement with no ticket (Q1.1 b).
- The other kinds of procedure (work instruction, diagnostic, onboarding), procedure steps, the
  skill matrix: a Procedures roadmap later.
- Cost of loss and savings (Plan § 2: no cost in v1).
- Safety incident investigation (ISO 45001).
- Excel export, the dashboard, the printed chronic-problems report (phase 5).
- An improvement started from a PM finding: after R03.10, a small step if wanted.

**Risks:**
- **The roadmap number (fact).** Plan.MD § 1 (*Preventive maintenance* row), § 9 Q20 and Q24, and
  R03 Q0.1 promise R04 to the certification and calibration follow-on, so this roadmap is R05
  (renumbered by the orchestrator, 29-10-2026). R04 stays reserved for that follow-on.
- **Content, not code, is the bottleneck.** A why-why done in haste stops at "the contact was
  dirty". The help text and the cause list nudge; KLA's guidance in the first cases matters more.
- **Few engineers.** Every analysis is engineer time. Q8.1 (a) keeps the load to a few a month.
- **The watch counts symptoms.** The symptom is optional at raise and required at close (S018).
  An open ticket with no symptom does not count until it is closed.
- **Shared files with R03.** `serial_counters` (R03.3), *Me › Open work* (R03.4), `alerts_core`
  (R03.7) and the documents CHECK (R03.6, R03.17). Whichever step comes first generalises; the
  second reuses. § Order lists the pairs that must not run in parallel.
- **Tamil content.** The DB is utf8mb4 (Plan § 4.3a), so Tamil text works today. Print and phone
  fonts are a device check (`docs/steps/device-checks.md`).
- **Sample data (fact).** The machine of TK-2026-10-002 was not given to the roadmapper. The
  mock-ups use HP003 at SSVT.SHOP as a stand-in, and their cause codes and back-in-service time
  are samples.

## Slides

1. **Improvement: learn from every serious breakdown**
   - A closed ticket says what broke. An improvement asks why, fixes the cause and checks it held.
   - The case: TK-2026-10-002, a contactor's dusty auxiliary contact stopped a machine.
   - 10 items; the team analyses this case after the first three.
2. **The standards, in plain words**
   - TPM focused improvement: take one loss and remove its root cause. Why-why: ask why until the
     plant can change the answer.
   - ISO 9001 § 10.2: correct, find the cause, act, check it worked, keep the record.
   - ISO 14224: the ticket's cause vs. the root cause, one cause list. EN 13306: corrective,
     preventive, improvement maintenance. TPM design-out, yokoten, one-point lessons.
3. **Start from the ticket** — `01-closed-ticket.html`
   - On a closed breakdown the engineer taps *Start improvement*; the ticket stays as it was.
   - A yellow hint when the rule suggests it.
4. **Why-why to the root cause** — `02-analysis.html`
   - Five whys, from "the press did not start" to "the presses have no PM plan".
   - The root cause from the cause list, beside the ticket's own cause.
5. **Countermeasures, each owned** — `03-countermeasures.html`
   - Correction, corrective, preventive, design-out, lesson, spread: each with an owner and a due
     date.
   - The monthly panel clean becomes a PM plan when PM is built.
6. **My countermeasures on the phone** — `04-my-countermeasure.html`
   - Countermeasures join tickets on *Me › Open work*; overdue in red.
   - *Mark done* with what was done and a photo.
7. **Did it work?** — `05-verify.html`
   - 90 days watched; the same symptom counted before and after.
   - *Close as effective*, or *Not effective — analyse again*.
8. **A one-point lesson for the floor** — `06-lesson.html`
   - A picture and one line, in Tamil, on every press's page.
   - The supervisor records who was shown.
9. **Improvements and suggestions** — `07-improvements.html`
   - A tab on *Tickets*: open, suggested, closed.
   - Suggested: repeats, long grade A breakdowns, one symptom again and again.
10. **The items as a timeline**
    - Milestone 1 (about 4.5 days): R05.1 → R05.2 → R05.3: the contactor case analysed and owned.
    - Milestone 2 (about 3.5 days): verified close, alerts, suggestions.
    - Milestone 3 (about 3.25 days): lessons, who was shown, the register. Milestone 4: PM plans,
      after R03.2 and R03.8.
11. **Your decisions** (recommended answer in brackets)
    - Q0.1 call it *Improvement* (a); Q0.2 milestone 1 before PM (a); Q1.1 start from tickets back
      in service or closed (a); Q1.2 a tab on Tickets (a); Q1.3 operators read, engineers write
      (a); Q1.4 one open improvement per ticket (a).
    - Q2.1 one why chain (a); Q2.2 root cause from the cause list (a); Q2.3 the ticket is not
      changed (a); Q3.1 six kinds (a); Q3.2 any site member owns (a); Q4.1 a 90-day watch (a); Q4.2
      the lead may verify (a); Q4.3 a repeat warns (a).
    - Q5.1 push alerts (a); Q6.1 lessons as the first procedure kind (a); Q6.2 on the class too
      (a); Q6.3 engineers write, supervisors record (a); Q7.1 who was shown (a); Q8.1 Yantra
      suggests, the engineer decides (a); Q9.1 done when the PM plan is active (a); Q10.1 the
      register (a).

## Log

- 30-10-2026 — Gate R: approved by KLA; R05.7, R05.8, R05.9 deferred; every other answer (a); the rest of R05 built now, before R03's milestone 1.

- 29-10-2026 — First version (Draft): 10 items from KLA's request (TK-2026-10-002),
  Maintenance-Philosophy § 3 (focused improvement, training), Plan § 4.2, § 4.3a, § 4.6 and § 1
  (ISO 9001 § 10.2), checked against HEAD `32eb122`; no improvement code or key exists. Seven
  mock-ups in `R05-mockups/` (with `mockup.css`, copied from R03's). 22 questions for KLA. The
  number R04 was promised in Plan.MD to the certification follow-on; see § Risks.
- 29-10-2026 — Renumbered R04 → R05 by the orchestrator: R04 is reserved for the certification and
  calibration follow-on (Plan § 1, § 9 Q20, Q24; R03 Q0.1). Mock-ups moved to `R05-mockups/`.

## Feedback

- `rule` — A roadmap number was reserved in prose before the roadmap existed: Plan.MD § 1 (PM
  row), § 9 Q20 and Q24, and R03 Q0.1 call the certification follow-on "R04", while the agent
  rule gives R04 to the next roadmap written (this one; renumbered R05). Proposal: name a future roadmap "a
  follow-on roadmap", never a number, until the orchestrator gives it one.
- `rule` — The *Roadmap mock-ups* setting in `.claude/CLAUDE.md` still names only Bootstrap and
  `main.css`. The app's icons need Font Awesome (`frontend/src/main.js`), and the sidebar, top bar
  and bottom nav styles are scoped in Vue, so every roadmap copies a `mockup.css` (R03's, now
  R05's). R03's feedback raised this on 27-10-2026; the setting is unchanged.
- `idea` — `docs/roadmap/README.md` does not say whether *Depends on* may name another roadmap's
  item. R05.9 depends on R03.2 and R03.8, and § Order pairs R05.1 with R03.1. One line in the
  README ("items of another roadmap are named in full, e.g. R03.2") would settle it.
