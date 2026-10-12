# Maintenance Philosophy — Domain Knowledge

How VEL's plants approach maintenance, and the rules Yantra must encode. Read this
before designing or changing any maintenance module (breakdowns, PM, meters,
reports). It records *why* the plant works the way it does; `docs/Plan.MD` records
*what* Yantra will build.

Status markers:

- **Decided** — agreed and recorded in `docs/Plan.MD`.
- **Proposed** — a standard industry definition, offered as a starting point; confirm before relying on it.
- **TBD** — not yet known; to be filled in by the maintenance team.

---

## 1. Goals of maintenance at VEL

TBD — what the plant is optimising for, in order of priority (e.g. machine uptime,
safety, product quality, cost of spares, audit/compliance), and which plants and
areas are in scope first.

## 2. Maintenance strategies used

| Strategy | Meaning | In Yantra |
|---|---|---|
| Breakdown (corrective) | Repair after a failure | Breakdown tickets — v1 (**Decided**) |
| Preventive — calendar | Fixed-interval tasks (every N days/weeks/months) | PM plans with calendar trigger — v1 (**Decided**) |
| Preventive — usage | Tasks every N run hours / production count | PM plans with meter trigger — v1 (**Decided**) |
| Condition-based | Act when a measured value crosses a limit | Gauge meters with limits — v1, manual readings (**Decided**); automatic IIoT feeds later |
| Predictive | Forecast failure from trends | Not planned |

TBD — which strategy applies to which class of machine, and who decides.

## 3. Machine criticality

Machines are graded **A / B / C** (**Decided**). Escalation time for an
unacknowledged breakdown is set per criticality (**Decided**; values TBD —
Plan.MD open question 2).

TBD — what each grade means at VEL. A common scheme (**Proposed**):

- **A** — stops a production line or is a safety risk; no standby.
- **B** — slows production or has a standby; repair within the shift.
- **C** — no direct production impact; repair when convenient.

## 4. Breakdowns

**Decided** lifecycle and ownership:

```
raised ──► acknowledged ──► in progress ──► machine up ──► closed
(operator)  (technician/     (technician)    (technician)   (engineer)
             engineer)
```

- The operator records whether the machine is **stopped** or **running degraded**;
  only stopped time counts as downtime.
- Only an engineer closes a breakdown, and can send it back to "in progress".
- Symptom codes are picked by the operator; cause and action codes by the
  technician/engineer. Engineers maintain the code lists.

**Downtime definition** — TBD (Plan.MD open question 4): does downtime end at
"machine up" (technician) or at the operator's confirmation?

TBD — what counts as a breakdown versus a minor stoppage or an adjustment by the
operator; whether planned stops are ever logged as breakdowns.

## 5. Preventive maintenance

**Decided:**

- A PM plan belongs to one machine (any level of the machine tree) and one task.
- Checklists use OK / Not OK / NA with remarks; readings have a unit and min/max limits.
- **The next calendar job is due from the completion date of the previous one**,
  not from its due date — a late job pushes the schedule out. A plan needing a
  fixed rhythm is edited by the engineer.
- A meter crossing its threshold **creates the PM job automatically**, as a
  calendar job falling due does.
- The technician does the job; **the engineer verifies** it and can send it back.
- A reading outside its limits is flagged on the job, and a breakdown can be
  raised from it in one tap.

TBD — how much lateness is tolerated before a PM job is "overdue"; whether a
skipped PM is allowed and who may skip it; shutdown/annual-overhaul planning.

## 6. Meters and readings

**Decided:**

- **Counter** meters only go up (run hours, production count) and trigger every N units.
- **Gauge** meters are levels (temperature, vibration, clearance, wear in mm) and
  trigger on crossing limits.
- A counter reading lower than the previous one is rejected unless marked as a
  meter reset.
- Readings are entered by hand for now; every reading records its source so an
  automatic feed can be added later.

TBD — which meters matter per machine class, and the limits for each.

## 7. Measures (KPIs)

Definitions below are **Proposed** — confirm before reports are built (phase 5).

| Measure | Definition |
|---|---|
| Downtime | Sum of stopped time per machine / location / cause, per period (see § 4 for when it ends) |
| MTBF (mean time between failures) | Available operating time ÷ number of breakdowns, per period |
| MTTR (mean time to repair) | Total repair time (in progress → machine up) ÷ number of breakdowns |
| Response time | Raised → acknowledged |
| PM compliance | PM jobs done on time ÷ PM jobs due, per period |

TBD — what "available operating time" is at VEL (shift calendar, planned stops),
and whether degraded running counts towards MTBF.

## 8. Roles and responsibilities

From `docs/Plan.MD` § 3 (**Decided**): operators raise breakdowns and log readings;
technicians work breakdowns and PM jobs; engineers assign, verify and close, and
own the masters (machines, PM plans, codes); the maintenance manager sees all
locations and reports; IT admin handles settings and housekeeping, not maintenance work.

TBD — shift patterns, on-call arrangement, and who covers when the engineer is absent.

## 9. Glossary

| Term | Meaning |
|---|---|
| Breakdown | An unplanned failure that needs repair (Yantra ticket `BD-YYYY-MM-NNN`) |
| PM | Preventive maintenance — planned work from a PM plan (job `PM-YYYY-MM-NNN`) |
| PM plan | The recurring task definition: machine, checklist, readings, triggers |
| PM job | One occurrence of a PM plan, generated when due |
| Meter | A tracked quantity on a machine — counter or gauge |
| Criticality | A / B / C grade of a machine's importance |

TBD — plant-specific terms (local names for machines, areas, shifts).
