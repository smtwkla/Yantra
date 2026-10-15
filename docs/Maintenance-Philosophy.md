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
| **Focused improvement** | Remove chronic losses: why-why / root-cause analysis | Later, built on failure data |
| **Quality maintenance** | Equipment conditions that prevent defects | Out of scope |
| **Early equipment management** | Use maintenance experience when buying equipment | Out of scope; equipment history may feed it later |
| **Training & education** | Skills of operators and technicians | Later (skill matrix, one-point lessons) |
| **Safety, health & environment** | Safe maintenance (e.g. lock-out / tag-out) | Later, if wanted |
| **TPM in office** | Administrative losses | Out of scope |

## 4. Losses Yantra tracks

TPM names **six big losses**: breakdowns, setup/adjustment, minor stops, reduced
speed, start-up rejects, production rejects. Yantra tracks **breakdowns** only
(**Proposed**). The others need production data and are not maintenance tickets.
This also answers "what counts as a breakdown": a failure needing maintenance
work, not a minor stop the operator clears.

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
- Detecting a *missed* before-use CIL needs evidence that the equipment ran;
  deferred until production counts exist.

TBD — whether an engineer verifies CIL jobs; the CIL items per equipment class.

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
- **Intensity** is captured on the ticket (**Decided**). Scale **Proposed** from
  ISO 14224 failure impact:
  - **critical** — equipment stopped;
  - **degraded** — running with reduced function;
  - **incipient** — still running normally, early signs (noise, leak, heat).
  Only critical time counts as downtime.
- Only an engineer closes a ticket, and can send it back to "in progress".
- **Failure coding** — symptom by the operator; cause and action by the
  technician/engineer; lists maintained by engineers. Moving to ISO 14224-style
  coding (failure mode, cause, action required; mechanism and detection method
  optional; lists scoped by equipment class) is **pending evaluation** — adopt if it is
  not too daunting for the floor.
- Frivolous closures are excluded from downtime and MTBF/MTTR (**Proposed**).

TBD — downtime end: "back in service" (technician) or the operator's confirmation
(Plan.MD open question 4); escalation times per criticality.

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
| Corrective | Repair after a failure | Breakdown tickets — v1 |
| Preventive — calendar | Fixed-interval tasks | PM plans, calendar trigger — v1 |
| Preventive — usage | Every N run hours / production count | PM plans, meter trigger — v1 |
| Condition-based | Act when a measured value crosses a limit | Gauge meters with limits — v1, manual readings; IIoT later |
| Predictive | Forecast failure from trends | Not planned |

TBD — how late a PM job may be before it is "overdue" (the SRS suggests a
compliance window, e.g. ±10 % of the interval — **Proposed**); whether a PM may be
skipped and by whom; shutdown / annual-overhaul planning.

## 8. Meters, readings and production data

**Decided:**

- **Counter** meters only go up (run hours, production count) and trigger every N units.
- **Gauge** meters are levels (temperature, vibration, clearance, wear in mm) and
  trigger on crossing limits.
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

## 10. Measures (KPIs)

Definitions below are **Proposed** — confirm before reports are built (phase 5).

| Measure | Definition |
|---|---|
| Downtime | Sum of critical (stopped) time per equipment / unit / cause, per period |
| MTBF (mean time between failures) | Available operating time ÷ number of breakdowns, per period |
| MTTR (mean time to repair) | Total repair time (in progress → back in service) ÷ number of breakdowns |
| Response time | Raised → acknowledged |
| PM compliance | PM jobs done on time ÷ PM jobs due, per period |
| Availability (OEE factor) | Run time ÷ planned production time — needs production data (later) |

TBD — what "available operating time" is at VEL (shift calendar, planned stops),
and whether degraded running counts towards MTBF.

## 11. Roles and responsibilities

From `docs/Plan.MD` § 3 (**Decided**):

- **Operators** — CIL on their equipment, raise tickets (red tags), log readings.
- **Technicians** — work tickets and PM jobs.
- **Engineers** — assign, verify and close; own the masters (equipment, classes,
  templates, plans, codes).
- **Maintenance manager** — all units, reports.
- **Storekeeper** — maintenance stores; no v1 work (spares come later).
- **IT admin** — settings and housekeeping, not maintenance work.

Everyone except the manager works only at the **units (shop floors) they are
given**, held in Yantra's DB. Production supervisors are left out for now.

TBD — shift patterns, on-call arrangement, and who covers when the engineer is absent.

## 12. Glossary

| Term | Meaning |
|---|---|
| TPM | Total Productive Maintenance — the framework this document follows |
| OEE | Overall Equipment Effectiveness = Availability × Performance × Quality |
| CIL | Clean, Inspect, Lubricate — the operator's routine care of a piece of equipment |
| Red tag | An abnormality needing maintenance — in Yantra, a breakdown ticket |
| Intensity | How bad a ticket's problem is: critical / degraded / incipient (proposed) |
| Breakdown | An unplanned failure that needs repair (ticket `BD-YYYY-MM-NNN`) |
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
