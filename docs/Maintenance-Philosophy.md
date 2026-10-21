# Maintenance Philosophy — Domain Knowledge

How VEL's plants should approach maintenance, and the rules Yantra must encode.
Read this before designing or changing any maintenance module (breakdowns, PM,
CIL, meters, reports). It records *why*; `docs/Plan.MD` records *what* Yantra
will build; `docs/Plant-Facts.md` records the factories *as they are*.

Status markers:

- **Decided** — agreed and recorded in `docs/Plan.MD`.
- **Proposed** — a standard industry definition, offered as a starting point; confirm before relying on it.
- **TBD** — not yet known; to be filled in by the maintenance team.

---

## 1. Starting point

- The plant is about 70 years old. **There is no TPM or 5S programme** and no
  systematic maintenance data — only notes in notebooks (**Decided**, 12-10-2026).
- About 500 pieces of equipment across three sites (per the SRS draft; site mapping to Yantra
  units TBD).
- Operators already do informal autonomous maintenance on every equipment: they
  clean, lubricate and flag malfunctions. Yantra formalises what already happens
  before asking for more.
- Yantra starts with no history. Backfilling from the notebooks is deferred
  (**Decided**).

So this document describes a **target**, not current practice. Yantra introduces
it step by step.

## 2. Framework: TPM

Yantra is built on **Total Productive Maintenance (TPM)** (**Decided**, 12-10-2026):

- **Goals:** zero breakdowns, zero defects, zero accidents.
- **Ownership is shared:** operators care for their equipment day to day; the
  maintenance team does planned and skilled work and fixes what operators find.
- **Measure:** OEE (Availability × Performance × Quality). Yantra measures
  *availability* (downtime, MTBF, MTTR). Performance and quality need production
  counts, which come later (§ 8).

Standards used for terms and data structure, to bring maturity into the system
(**Decided** in principle; detail per section):

- **EN 13306** — maintenance types (corrective, preventive, condition-based, predictive).
- **ISO 14224** — equipment taxonomy and failure data (failure mode, mechanism,
  cause, detection method, impact). We adopt its structure, not its oil-and-gas
  code lists.

**Foundation — 5S.** TPM rests on 5S (sort, set in order, shine, standardise,
sustain). Not in Yantra's scope; recorded as context.

## 3. The eight pillars and Yantra

| Pillar | What it means | In Yantra |
|---|---|---|
| **Autonomous maintenance** | Operators clean, inspect, lubricate and tag abnormalities | CIL jobs (§ 5) and breakdown tickets (§ 6) — v1 |
| **Planned maintenance** | Maintenance team: breakdown, preventive, condition-based work | Breakdown tickets, PM plans, meters, limits — v1 |
| **Focused improvement** | Remove chronic losses: why-why / root-cause analysis | Brought forward for the presses (16-10-2026): tickets at component level with class-scoped failure modes, and a chronic-problem report (Plan § 4.6). Its first targets: welded output relays (convert to solid-state — *maintenance prevention*, removing the failure mode instead of maintaining it) and the safety-door sensor alignment |
| **Quality maintenance** | Equipment conditions that prevent defects | Out of scope |
| **Early equipment management** | Use maintenance experience when buying equipment | Out of scope; equipment history may feed it later |
| **Training & education** | Skills of operators and technicians | **Procedures** (Plan § 4.3a, *Proposed* 16-10-2026): one-point lessons, work instructions and the expert's diagnostic tests, written once and shown on the equipment page, the PM template and the ticket. **Onboarding** cards in Tamil with pictures, stepped through before first use, with a completion record per person (ISO 45001 § 7.2) — the seed of the skill matrix |
| **Safety, health & environment** | Safe maintenance (e.g. lock-out / tag-out) | Later, if wanted |
| **TPM in office** | Administrative losses | Out of scope |

## 4. Losses Yantra tracks

TPM names **six big losses**: breakdowns, setup/adjustment, minor stops, reduced
speed, start-up rejects, production rejects. Yantra tracks **breakdowns** only
(**Proposed**). The others need production data and are not maintenance tickets.
This also answers "what counts as a breakdown": a failure needing maintenance
work, not a minor stop the operator clears. A stop taken for scheduled work
(roller turning, a planned part change) is **planned downtime**, not a breakdown
(**Proposed**, 16-10-2026; § 7).

## 5. Autonomous maintenance — CIL

**Decided** (12-10-2026):

- CIL (clean / inspect / lubricate) is part of each equipment's **maintenance plan**:
  a plan performed by the operator. It is not a piece of equipment flag.
- **Clean and Inspect are mandatory; Lubricate only if the equipment needs it.**
  The checklist is defined per equipment and varies.
- **No checklist defined = CIL not required** for that equipment.
- **Trigger** is chosen per equipment:
  - **Before use** — before the equipment's first use on a day it runs. Equipment
    used daily get it daily; equipment used rarely get it each day they are used.
    The operator starts it from the equipment's QR.
  - **Frequency** — a fixed calendar interval.
- A problem found during CIL is raised as a breakdown ticket (§ 6).
- Where operators have no phone (**Decided**, 16-10-2026), the check is done from
  the paper CIL sheet at the machine (the TPM autonomous-maintenance check sheet)
  and the supervisor records it in Yantra, naming the operator as performer and
  entering the time. The operator still owns the check; Yantra records the exception.
- Detecting a *missed* before-use CIL needs evidence that the equipment ran;
  deferred until production counts exist.

TBD — the CIL items per equipment class. Whether an engineer verifies CIL jobs:
**Proposed** (17-10-2026) no by default, a flag per plan (§ 7).

Future (**Proposed**): TPM rolls autonomous maintenance out in seven steps, from
initial cleaning to self-management. Tracking which step each area has reached
may come later; v1 does not.

## 6. Breakdowns (the red tag)

In TPM an operator puts a **red tag** on a problem that needs maintenance. In
Yantra **the red tag is the breakdown ticket** (**Decided**) — one record type.

**Decided** lifecycle and ownership:

```
raised ──► acknowledged ──► in progress ──► back in service ──► closed
(operator) (technician/     (technician)    (technician)        (engineer)
            engineer)
raised / acknowledged ──► closed   (engineer: frivolous, with code + remarks)
```

- **No approval step.** A ticket goes straight to maintenance. If it turns out
  frivolous, the engineer closes it with a suitable code and remarks (**Decided**).
- **Intensity** is captured on the ticket (**Decided**). Scale **Decided**
  (15-10-2026) from ISO 14224 failure impact:
  - **critical** — equipment stopped;
  - **degraded** — running with reduced function;
  - **initial** — still running normally, early signs (noise, leak, heat).
    ISO 14224 calls this *incipient*; Yantra uses the plain word.
  Only critical time counts as downtime.
- Only an engineer closes a ticket, and can send it back to "in progress".
- **Failure coding** (**Decided**, 15-10-2026): the ISO 14224 core.
  - **Failure mode**: what is seen, picked by the operator as the symptom.
  - **Failure cause**: why it failed, picked by the technician/engineer.
  - **Maintenance action**: what was done, picked by the technician/engineer.
  Lists are trimmed from ISO 14224 Annex B and maintained by engineers.
  Mechanism is not used for now; detection method is filled automatically from
  the ticket's source. Mode lists may later be scoped by equipment class.
- Frivolous closures are excluded from downtime and MTBF/MTTR (**Proposed**).

**Decided** (16-10-2026, sorting-line use case): production can also mark "back in
service", naming the technician from Team, because technicians on the floor may
have no phone. This is requester sign-off: production confirms the restoration
(EN 13306), where SMRP's repair time ends. Transitions recorded after the fact
carry the event time entered by the user (ISO 14224 counts failures and
restorations by when they happened). Operators without a login exist in Team so
"who found it" and "who did it" can be recorded (ISO 14224 detection and labour).

**Decided** (15-10-2026): downtime ends at the technician's "back in service".
Whether the operator can mark "not fixed" to reopen is settled with the phase 3
brief. Escalation times per criticality: **deferred** to the notification step
(Telegram / web push).

## 7. Planned maintenance

**Decided:**

- **Equipment class** says what a piece of equipment is; a **PM template** says what work to do.
  Engineers apply a template to equipment picked by class; each equipment gets its
  own plan with its own schedule. No hand-picked equipment groups.
- A PM plan belongs to one node of the equipment tree (equipment, component-unit or component) and one task.
- Checklists use OK / Not OK / NA with remarks; readings have a unit of measure and min/max limits.
- **The next calendar job is due from the completion date of the previous one**,
  not from its due date — a late job pushes the schedule out. A plan needing a
  fixed rhythm is edited by the engineer.
- A meter crossing its threshold **creates the PM job automatically**, as a
  calendar job falling due does.
- The technician does the job; **the engineer verifies** it and can send it back.
- A reading outside its limits is flagged on the job, and a breakdown can be
  raised from it in one tap.

Maintenance types (EN 13306) and where they live:

| Type | Meaning | In Yantra |
|---|---|---|
| Run-to-failure | Deliberately no preventive work; repair when it fails | A chosen **strategy** on the equipment (**Proposed**, 16-10-2026), right for most grade C equipment (RCM: low consequence). Still gets the fitness-for-use inspection. "Not decided" is the gap to close, not a strategy |
| Corrective | Repair after a failure | Breakdown tickets — v1 |
| Preventive — calendar | Fixed-interval tasks | PM plans, calendar trigger — v1 |
| Preventive — usage | Every N run hours / production count | PM plans, meter trigger — v1 |
| Condition-based | Act when a measured value crosses a limit | Gauge meters with limits — v1, manual readings; IIoT later |
| Predictive | Forecast failure from trends | A later rung (decided 18-10-2026): once Yantra holds a year of coded tickets and readings, **aibots** reasons over them and over **plant-3i**'s telemetry (Plan § 8, later rungs) |

**Deferred corrective maintenance** (**Decided** 21-10-2026, S019; proposed 16-10-2026). EN 13306 splits
corrective work into *immediate* (the door sensor: fix now) and *deferred* (worn
scrapers, a touchscreen, a liner good for another 1,000 hours: request now, plan
parts and a slot, fix later). Most of the extrusion line's work is deferred. Yantra
holds it as a ticket in a *scheduled* state with a planned date and a waiting
reason (a meter-value target comes with the PM engine), and counts the stop taken
for it as **planned downtime**, apart from breakdown downtime. A stopped machine
waiting for parts, a vendor or an expert is in the same state, so its downtime
splits into active repair and waiting. SMRP's planned-versus-reactive ratio is the
measure of a plant moving from firefighting to TPM; a ticket that went through
*scheduled* stands in for SMRP's planned work until Yantra has job plans.

**Contamination control for hydraulics** (16-10-2026, pressing shop). Most hydraulic
failures trace to fluid contamination; the presses' sticking valves, worn pump elements,
scored cylinders and transducer trouble are the pattern. The standard is **ISO 4406**, a
cleanliness code from particle counts, targeted by the most sensitive component. Yantra
holds the code as a gauge meter per press (Plan § 4.5); the offline filter runs as a
condition-based job when the code is over target, with a measured result. Filters are
changed on their clogging indicator. "Every sample would fail" is the reason to measure,
not to skip: it turns filtration from a guess into a job with a before and after.

**Forgotten machines** (**Proposed**, 16-10-2026). Many machines are used until they
break and some are forgotten altogether (an electric wood cutting machine, unused
for years). ISO 55001 § 7.5 asks the organisation to know what it has and what it
decided for each asset. Yantra answers with three things: a maintenance strategy on
every equipment with "not decided" shown as a gap; a periodic **fitness-for-use
inspection** by the engineer on every machine (fit / fit with conditions / not fit),
which also carries statutory examinations under the Factories Act; and
**verification rounds**, a walk per unit scanning QR labels, the physical check
ISO 55002 recommends.

**Statutory and safety equipment** (**Proposed**, 17-10-2026). Lifts, hoists, EOT
cranes and pressure vessels must be examined by a competent person at intervals the
Factories Act 1948 sets (lifts and hoists six-monthly, lifting machines yearly,
pressure plant per the state rules, with a fee to the government inspector), and a
certificate obtained. Fire extinguishers follow IS 2190: periodic checks, refills,
pressure tests and replacement by type. All are **equipment** in Yantra, graded A
(safety), with a certification plan that records *valid until* and holds the
certificate, so expiry is visible before an inspector finds it. ISO 55001 § 6.2 and
ISO 45001 § 6.1.3 ask that legal requirements be identified and compliance shown;
the compliance register (Plan § 4.6) is that evidence. Routine checks such as the
quarterly extinguisher check need no engineer verification (a flag per plan, which
also answers whether CIL jobs are verified: no, by default).

**Parts and part numbers** (**Decided** 21-10-2026, S020, for tickets; proposed 17-10-2026). Some makers (Haendle) supply
drawings with part numbers; many do not, and their service engineer identifies the
part and quotes. Many press spares (bearings, hydraulic valves, filters) are bought
generic, by standard designation. The practice is to **build the parts list from
maintenance history**: every part fitted is recorded on the ticket, against the
component, with its maker or generic number (ISO 14224 counts parts replaced among
the record fields). Makers' lists live on the model (EN 13460); a structured bill
of materials and stock come with spares; ordering and the item master stay in
OneERP (ISO 8000: one item master).

**Maintenance documentation** (16-10-2026, pressing shop). EN 13460 lists what a
maintainer should hold per equipment: hydraulic and electrical diagrams, manuals,
parts lists. Many presses were designed or altered in house and their diagrams are
missing, out of date or a hand sketch. Yantra cannot draw them, but it holds what
exists on the equipment, reachable from any phone, and lists the equipment that
has none (Plan § 4.1). A photographed sketch today beats a clean drawing nobody can find.

**Usage-based replacement of wearing parts** (16-10-2026): parts with a rated life in
operations (press output relays, which weld near end of life and stop the press) are
replaced on the stroke counter before they fail, until the failure mode is designed out.

**Rescheduling** (**Proposed**, 16-10-2026): the engineer may push a due PM job
to a later date or meter value with a reason (e.g. oil life extended on a good
analysis). Skipping without a reason is not allowed.

**Contracted maintenance** (16-10-2026): AMC vendors (compressors, pallet truck,
moisture analyser) are contractor records in Team and perform PM plans like
anyone else; the engineer verifies with the vendor's report attached. ISO 55001
§ 8.3 asks that outsourced work be controlled, so the contract terms will get a
register later.

**Inspection routes** (**Proposed**, 18-10-2026). A daily genset round and a daily
EB meter walk are inspections (EN 13306: a check for conformity, no repair) over
many pieces of equipment. The record stays per equipment (ISO 14224) but the work
is one walk, so Yantra groups the plans into a **route**, the standard CMMS answer
(SMRP: inspection and lubrication routes). Verification rounds and the CIL-due
list are routes too (Plan § 4.3).

**The vehicle fleet** (**Proposed**, 20-10-2026). Forty vehicles are inspected
about twice a year, when someone is free, and the small defects found are deferred
and forgotten. Nothing here needs a vehicle-specific design: a vehicle is equipment,
the driver is its operator (TPM autonomous maintenance: a short daily pre-trip check
as a before-use CIL plan, recorded by the drivers' supervisor), the monthly round is
the fitness-for-use inspection run as a route (EN 13306 inspection; SMRP route),
every defect is a ticket, and a repair deferred for parts or a garage slot is
deferred corrective maintenance in the *scheduled* state, measured by SMRP's backlog
age so it cannot be forgotten. Vaahan keeps the legal papers and the bills
(Plan § 4.1, § 7).

**The daily report is generated, not written** (**Decided**, 18-10-2026). The
electrical team head reports the day's work to the owner. In Yantra that report is
a query over what was recorded, printed. Recording the work and writing the report
are one effort, not two, or one of them stops being done. Odd jobs and new
installations stay off Yantra and are written on the printout: EN 13306 keeps
modification apart from maintenance, so the maintenance record is not diluted.

TBD — how late a PM job may be before it is "overdue" (the SRS suggests a
compliance window, e.g. ±10 % of the interval — **Proposed**); shutdown / annual-overhaul planning.

## 8. Meters, readings and production data

**Decided:**

- **Counter** meters only go up (run hours, production count) and trigger every N units.
- **Gauge** meters are levels (temperature, vibration, clearance, wear in mm) and
  trigger on crossing limits. Also an ISO 4406 oil cleanliness code and the day's
  maximum oil temperature (16-10-2026).
- **Energy** (16-10-2026): a kWh counter per press, so kWh per stroke can be reported
  later — ISO 50001's energy performance indicator, and the cost of a press that is
  waiting with its power pack running.
- **Which meter a plan uses** (**Proposed**, 16-10-2026): a plan names one meter, its
  own node's or an ancestor's — a gearbox on the extruder's hours, an alternating
  pump on its own. No inheritance logic (ISO 14224: hours at the level where they differ).
- **Tooling** (16-10-2026): a die that moves between presses is a component with a
  serial; a fit or removal snapshots the press's stroke counter, so strokes per die
  per press follow from readings (Plan § 4.1).
- A counter reading lower than the previous one is rejected unless marked as a
  meter reset.
- Readings are entered by hand for now; every reading records its source so an
  automatic feed can be added later.
- **Production counts** per equipment: a later version. Yantra will capture them
  per equipment and post them to OneERP, which remains the home of production data.
  They will also serve as usage meters and as evidence that a piece of equipment ran.
- **Telemetry (later):** the sister IIoT system **plant-3i** will feed Yantra
  production counts, run hours, gauge values (e.g. oil temperature) and PLC
  malfunction flags. Counts and run hours become counter readings, gauge values
  feed condition-based triggers, and malfunction flags are candidates for raising
  tickets automatically (**Proposed**).
- **VelKilnMaster** (the kiln app, later) may likewise flag kiln sensors as
  needing maintenance — another candidate source of automatic tickets.
- **The later rungs** (decided 18-10-2026). Maintenance maturity climbs reactive →
  preventive → condition-based → predictive; no rung can be skipped, because each
  rests on the records of the one below. Yantra builds the first three. The
  fourth, **predictive maintenance**, **digital twins** and **remote monitoring**,
  is built across the three sister repos with a fixed division of labour:
  **plant-3i** acquires (one digital twin per machine, polling the PLC: the
  press twin exists, extruder and compressor twins follow), **Yantra** holds the
  asset register, the coded failure history and the readings with limits, and
  **aibots** reasons and communicates (forecasts from Yantra's and plant-3i's
  data, alerts, questions answered over the records). Bots never touch devices.
  The national context (MRAM 2026, ABB survey, NITI Aayog "AI for Viksit
  Bharat", reported 18-10-2026): 88 % of Indian industrial businesses see an
  unplanned outage at least monthly and 19 % run to failure; the report names
  AI-based predictive maintenance, digital twins and remote monitoring as the
  enablers. The plant is in that 19 % today; the ladder is how it leaves it.

TBD — which meters matter per equipment class, and the limits for each.

## 9. Equipment criticality

Equipment are graded **A / B / C** (**Decided**). Escalation time for an
unacknowledged breakdown is set per criticality (**Decided**; values TBD).

What each grade means at VEL (**Decided**, 14-10-2026, S002):

- **A** — stops a production line or is a safety/environment risk; no standby.
- **B** — slows production or has a standby; repair within the shift.
- **C** — no direct production impact; repair when convenient.

Criticality is required on equipment (new equipment starts at C). Component-units
and components inherit their equipment's grade unless graded themselves.

A **safety function** (a press's safety door and its sensor) is graded A as a
component-unit whatever the press's own grade (**Decided**, 16-10-2026): grade A
covers safety risk, so its tickets outrank production tickets and escalate first.

## 10. Measures (KPIs)

Definitions below are **Proposed** — confirm before reports are built (phase 5).

| Measure | Definition |
|---|---|
| Downtime | EN 13306 *down time*: sum of critical (stopped) time per equipment / unit / cause, per period; for one breakdown, its *time to restoration* (failure → back in service, S018) |
| MTBF (mean time between failures) | Available operating time ÷ number of breakdowns, per period |
| MTTR (mean time to restoration) | Total downtime ÷ number of breakdowns — EN 13306 / SMRP 3.5.5: failure to restoration (Plan.MD Q4) |
| Mean active repair time | Total repair time (time in progress, EN 13306 *active corrective maintenance time*) ÷ number of breakdowns — what maintenance controls; MTTR minus it is waiting |
| Waiting time | Time a stopped machine spends in *scheduled* (S019), per waiting reason, summed into EN 13306's *logistic delay* (parts, vendor, expert) and *administrative delay* (production slot, approval); *other* stays apart. Shows what the plant waits for |
| Planned downtime | Time from a start marked "machine stopped for this work" on a scheduled ticket to back in service (S019). Planned stops, kept out of breakdown downtime and MTTR; part of SMRP's scheduled downtime |
| Response time | Raised → first acknowledged or started — the plant's own work-management measure, not an SMRP or EN 13306 term |
| PM compliance | PM jobs done on time ÷ PM jobs due, per period |
| Availability (OEE factor) | Run time ÷ planned production time — needs production data (later) |

TBD — what "available operating time" is at VEL (shift calendar, planned stops),
and whether degraded running counts towards MTBF.

## 11. Roles and responsibilities

From `docs/Plan.MD` § 3 (**Decided**):

- **Operators** — CIL on their equipment, raise tickets (red tags), log readings.
- **Production supervisors** (decided 16-10-2026, S011 A1) — an operator's rights,
  usually over more units; more reports later. TPM autonomous maintenance: operators
  and their supervisors own the cleaning, inspection and lubrication of their
  machines (CIL verification may later sit with them, Plan § 9.10). Production-side,
  off the maintenance ladder: a supervisor does not work tickets. (EN 15628's
  "maintenance supervisor" is a maintenance-side level, about an engineer here.)
- **Technicians** — work tickets and PM jobs. A technician without a phone (the
  fitter on the genset round) is paired with a supervisor or engineer who records
  for them, naming them as performed by (decided 18-10-2026).
- **Engineers** — assign, verify and close; own the masters (equipment, classes,
  templates, plans, codes).
- **Maintenance manager** — all units of their site(s), reports.
- **Storekeeper** — maintenance stores; no v1 work (spares come later).
- **IT admin** — settings and housekeeping, not maintenance work.

Roles are **per site** (decided 16-10-2026): one person can be manager at one
site and engineer at another. Within a site, everyone works only at the
**units (shop floors) they are given**, or all units of the site (usually the
manager), held in Yantra's DB on the person in Team. IT admin grants the roles;
an engineer assigns Technicians at their own site.

TBD — shift patterns, on-call arrangement, and who covers when the engineer is absent.

## 12. Glossary

| Term | Meaning |
|---|---|
| TPM | Total Productive Maintenance — the framework this document follows |
| OEE | Overall Equipment Effectiveness = Availability × Performance × Quality |
| CIL | Clean, Inspect, Lubricate — the operator's routine care of a piece of equipment |
| Red tag | An abnormality needing maintenance — in Yantra, a breakdown ticket |
| Intensity | How bad a ticket's problem is: critical / degraded / initial (ISO 14224 failure impact) |
| Breakdown | A ticket of *critical* intensity: the equipment has stopped (a failure, EN 13306); downtime runs |
| Defect | A ticket of *degraded* or *initial* intensity: the equipment runs but something is abnormal (the TPM tag) |
| Ticket | Yantra's record of one problem on equipment, breakdown or defect (`TK-YYYY-MM-NNN`): the work request, then the work order |
| Work request | EN 13460: what is wrong, where, how urgent, who asks — a ticket when raised (Plan § 4.2 calls it the *maintenance request*) |
| Work order | EN 13460: the same record once maintenance takes it up — who worked, what they did, when |
| Failure / fault | EN 13306: a failure is the *event* (the item loses its ability to perform); a fault is the *state* after it |
| Partial failure | EN 13306: the item still runs with reduced function — Yantra's *degraded* intensity |
| Response time | Raised → first acknowledged or started: how fast maintenance reacts (the plant's own measure) |
| Repair time | EN 13306 *active corrective maintenance time*: the time a ticket is in progress, hands on the machine |
| Downtime | EN 13306 *down time*: while a breakdown's machine cannot run, failure to restoration (*time to restoration*); its mean is MTTR |
| Repeat failure | The same fault back within 7 days of its back in service: a new ticket linked as *repeat of* — the fix did not hold (TPM focused improvement; ISO 9001 § 10.2) |
| Not a fault | A ticket closed with a cause and remark because nothing was wrong (or a mis-operation); left out of failure counts |
| Failure mode | How a failure is seen — the operator's "symptom" (ISO 14224), per equipment class or General |
| Failure cause | Why it failed: the circumstances in design, manufacture or use that led to it (ISO 14224) |
| Cause group | ISO 14224's five groups of causes: design, fabrication / installation, operation / maintenance, management, miscellaneous |
| Failure mechanism | The physical process of the failure: wear, corrosion, short circuit (ISO 14224) — not recorded in v1 |
| Maintenance action | What was done: replace, repair, adjust, check, … (ISO 14224 maintenance activity) |
| PM | Preventive maintenance — planned work from a PM plan (job `PM-YYYY-MM-NNN`) |
| Equipment class | What a piece of equipment is (hydraulic press, ball mill, …) |
| Equipment type | How equipment of a class is built, e.g. a radial piston pump in closed or open execution (ISO 14224 type within class) |
| PM template | Reusable work definition applied to many equipment |
| PM plan | The recurring task for one equipment: checklist, readings, triggers, performer |
| PM job | One occurrence of a PM plan, generated when due |
| Meter | A tracked quantity on a piece of equipment — counter or gauge |
| Criticality | A / B / C grade of an equipment's importance |
| Site | A facility: SMTW, BRICKS, SSVT, a farm (ISO 14224 level 3) |
| Unit | An area or shop floor within a site, e.g. `SMTW.FWMILL` (levels 4–5) |
| Equipment | A maintained item: press, pump, solar system (level 6) — not "asset", which OneERP uses for fixed-asset accounting |
| Component-unit | A functional subassembly of an equipment: drive, power pack (level 7) |
| Component | A maintainable item: motor, gearbox (level 8) |
| Part | A replaceable piece: bearing, seal (level 9) — a spare, not in the tree |
| Equipment code | Permanent identity: class prefix + number (e.g. `VBM001`) |
| Full path | Derived from where the equipment sits: `SITE.UNIT.EQUIPMENT…` |

TBD — plant-specific terms (local names for equipment, areas, shifts).
