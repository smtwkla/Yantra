# Plant Facts — the factories as they are

Actual facts, data and history about VEL's factories: sites, shop floors,
equipment, people, stores, practices. **Facts only** — what is true today, with its
source. Rules and targets belong in `docs/Maintenance-Philosophy.md`; what Yantra
builds belongs in `docs/Plan.MD`.

Conventions:

- Each fact carries its **source** and the **date** it was recorded (DD-MM-YYYY).
- "User" means confirmed by the project owner in a design session. "SRS draft"
  means the external CMMS SRS v0.4 (12-10-2026) — confirmed facts listed there.
- Unknowns are marked **TBD**. When a fact changes, update it and note the old
  value in § 10 rather than deleting history.

---

## 1. Organisation

| Fact | Source |
|---|---|
| Sree Murugan Tile Works (SMTW), manufacturing, India — a partnership firm | SRS draft 12-10-2026; user 13-10-2026 |
| Partners: Lakshmi Anand Kaliappan (the project owner), Mithunvel K L | User, 13-10-2026 |
| Established 01-04-1958 (the plant is close to 70 years old) | User, 13-10-2026 |
| CARO 2020 (auditor's report on physical verification of fixed assets) does not apply to the businesses | User, 20-10-2026 |
| Main factory and working head office: SMTW, 10/712, Surandai Road, Pavoorchatram | User, 13-10-2026 |
| Registered head office: 10/710, Surandai Road, Pavoorchatram — a formal office only, no operations | User, 13-10-2026 |
| **VEL** is the combined org unit (SMTW with its sites and SSVT) for which Yantra is implemented — hence deployment ID `vel_yantra_master` | User, 13-10-2026 |
| Products — TBD (tiles; full product range to be listed) | — |
| **Not ISO 9001 certified; certification is a future goal.** Yantra is to be ISO 9001 compliant and nudge the plant towards it | User, 20-10-2026 |

### Sister concern

| Fact | Source |
|---|---|
| Sree Shenbaga Vinayagar Tiles Pvt Ltd — plant code **SSVT**; Lakshmi Anand Kaliappan is a director | User, 13-10-2026 |
| SSVT is a job-work unit for SMTW and has hydraulic presses | User, 13-10-2026 |
| Address — TBD (to be given) | — |

## 2. Sites and shop floors

| Code | Name | What it holds | Address |
|---|---|---|---|
| **SMTW** | Main factory, Pavoorchatram | Manufacturing; working head office | 10/712, Surandai Road, Pavoorchatram |
| **BRICKS** | Stock yard 1, Keelathottam — the "bricks campus"; also seen as SMTW-KT and STOCKY1 | Clay filtration plant, clay stock, bore well, open well | TBD |
| **SMTW-KP** | Stock yard 2, Keelapavoor village (Karambai plot) | Clay stock, a shed for goats and cows, bore wells | TBD |
| **AGRI-VKM** | Vettaikarankulam farm | Gooseberry, drip system, bore pumps, solar pump | TBD |
| **AGRI-KDK** | Kadabokaathi farm | Coconut, open wells, bore pumps, solar | TBD |
| **SSVT** | Sister concern's job-work unit (§ 1) | Hydraulic presses — about 12 (user, 16-10-2026) | TBD |

Source: user, 13-10-2026.

### Areas within SMTW (main factory)

| Group | Areas |
|---|---|
| Raw material | Clay stock; clay blending plots |
| Forming | Old extrusion and pressing line; new extrusion and punching line (called **MCC**, in two parts MCC1 and MCC2); hydraulic presses (two at SMTW; user, 16-10-2026) |
| Drying and firing | Drying areas; kiln; firewood processing mill |
| Quality | Lab |
| Finishing and dispatch | Sorting and packing line; delivery |
| Maintenance | Mechanical workshop and toolroom; electrical workshop; auto workshop |
| Stores and admin | Main store; office |

Source: user, 13-10-2026. The grouping is editorial; the areas are as given.

### Unit codes

Codes follow `SITE.UNIT`. Recorded as they are fixed:

| Code | Unit | Equipment (known so far) | Source |
|---|---|---|---|
| `SMTW.FWMILL` | SMTW's firewood processing mill | Vertical blade mill, breakers, electric saw, others | User, 13-10-2026 |
| `SMTW.MCC1` | New extrusion and punching line — first part | One line, one operator: two box feeders, a coarse roller mill, a fine roller mill, a clay spreader on a conveyor, conveyors between them (as dictated 16-10-2026; names to confirm) | User, 16-10-2026 |
| `SMTW.MCC2` | New extrusion and punching line — second part | New extruder (Haendle GmbH); puncher (Keller-HCW GmbH); Atlas Copco screw compressors (2); others | User, 13-10-2026 |
| `SMTW.FLEET`, `SSVT.FLEET` (*Proposed*) | The vehicle fleet of each company | About 40 vehicles in all (trucks, tractors, cars, forklifts; list to come from Vaahan, § 7). Forklifts and the pallet truck are in Vaahan too | User, 20-10-2026 |

The new extrusion line is known internally as **MCC** (origin of the name not known).

| Fact | Source |
|---|---|
| OneERP warehouse codes seen as possible equipment units: SMTW.MCC, SMTW.KILN, SMTW.MACSHP, SSVT.SHOP, BRICKS, STOCKY1.SHED1 | Plan.MD, 11-10-2026 |

OneERP warehouse codes may be renamed to follow Yantra's `SITE.UNIT` codes (user, 13-10-2026).

OneERP warehouses also hold **production items**, not only spares. Example:
`SMTW.FWMILL` is a OneERP warehouse holding firewood, cut firewood and sawdust,
and possibly a few spare parts and tools kept on site (user, 13-10-2026). So most
units are likely to have a matching OneERP warehouse.

TBD — how the remaining OneERP warehouse codes map to sites and units.

## 3. Equipment

| Fact | Source |
|---|---|
| About 500 machines and equipment in total | SRS draft, 12-10-2026 (its "three sites" predates the site list in § 2) |

| No existing equipment-numbering scheme | User, 13-10-2026 |
| **Hydraulic presses** (two at SMTW, about 12 at SSVT), one class in several types: 40 t direct-operated (two cylinders, 4–6 valves); gravity-assisted direct-operated; pilot-operated gravity-assisted with prefill; the same with a locked safety door. Each press is a different model, so filters and pump elements differ per press. Higher types have proportional valves with analog pressure control from the PLC | User, 16-10-2026 |
| Each press carries a top die, a bottom die and a mould box, all with serial numbers, which move between presses. Bottom dies are surface-ground in the plant's machine shop and refitted, possibly on another press | User, 16-10-2026 |
| Each press has one operator at the selection screen and 4–5 workers around it; a floor supervisor with a phone | User, 16-10-2026 |

TBD — split per site; equipment classes and counts; which equipment is critical;
equipment used daily vs. rarely.

## 4. Maintenance practice today

| Fact | Source |
|---|---|
| No TPM or 5S programme in place | User, 12-10-2026 |
| No systematic maintenance data; some information kept in notebooks | User, 12-10-2026 |
| Operators already do informal autonomous maintenance on all machines: cleaning, lubricating, flagging malfunctions | User, 12-10-2026 |
| Repairs happen in-situ (on the machine), in the Mechanical shop, in the Electrical shop, or externally (vendor) | SRS draft, 12-10-2026 |
| Important equipment is under **annual maintenance contracts (AMC)** with vendors. AMC vendors visit to do preventive maintenance and attend breakdown calls as per the contract | User, 13-10-2026 |
| AMC vendors known so far: **Atlas Copco** for the two screw compressors shared by the extrusion line (one runs, one on standby; vendor does A / B / D checks and may ask for filter changes); **Toyota Material Handling** for an electric pallet truck (batteries); **Sartorius** moisture analyser calibrated and serviced by the vendor on call | User, 16-10-2026 |
| Extruder main gearbox: synthetic oil, changed every 5,000 run hours. Oil samples go to an outside lab now and then; contaminants (e.g. silicon, pointing to a failed seal) or oil condition decide whether to change early or run another 1,000–2,000 h | User, 16-10-2026 |
| Fine roller mill: the roller shells are trued every 60–70 run hours with a lathe mounted on the mill; remaining shell thickness is measured (a thin shell can break); the roller gap is measured by passing soft aluminium wire and reading it with a vernier, kept about 1.5–2.5 mm and adjusted above 2.5 | User, 16-10-2026 |
| Extruder wear parts (augers, mixer paddles, shredding knives, liners) are kept in stock and changed on inspection; 3–4 auger sets on site, refurbished in the plant's own workshop. A spare gearbox exists; a failed one is swapped out and sent for repair, coming back repaired or scrapped | User, 16-10-2026 |
| Extrusion-line operators read run hours and production counts off the PLC HMI into a notebook and enter them at the end of the day | User, 16-10-2026 |
| **Press availability** has fallen over the last year; at times only about 70 % of the presses are operable. Fault diagnosis depends on the project owner, who guides the engineers by phone test by test; some problems take months to resolve | User, 16-10-2026 |
| Press hydraulic oil is contaminated (air and particles). An offline filtration machine is connected to a press and run for days to weeks. No oil condition monitoring is done, on the view that every sample would fail | User, 16-10-2026 |
| Frequent press failures: output relay contacts **weld** (the PLC drives electromechanical relay boards) — a hard stop, the press misbehaves until the relay is replaced; the plan is to convert to solid-state relays. Also: pressure transducer failures; proportional-valve zero/span drift (PLC reads low, auto cycle fails; adjusted with a laptop on the PLC); pump radial piston elements; suction strainer clogging; return filters per press model; cracked pipelines welded in the workshop; cylinder seal failure, scoring or body cracks — cylinders go to the maker for 2–3 weeks; rarely a cracked press body, welded in place; safety-door magnetic sensor misalignment (intermittent, worst on some presses, sensor and cylinder guiding need redesign); pneumatic door cylinder seals | User, 16-10-2026 |
| Press PLC panels get dusty and need frequent cleaning; one press had oil ingress into the panel and PLC | User, 16-10-2026 |
| Many machines are run until they break with no preventive work, and some are forgotten: an electric wood cutting machine went unused for years and almost nobody remembered it existed | User, 16-10-2026 |
| The factory has conveyor belts, lifts and EOT cranes that are checked and certified periodically by a competent person, and pressure vessels examined periodically by a government official against a fee. Fire extinguishers of several types: some replaced every 5 years, some every 3, some refilled yearly. The owner wants each extinguisher QR-labelled and its check recorded by a technician on scanning | User, 17-10-2026 |
| Operators are not formally trained on a machine before using it; the owner wants step-by-step dos and don'ts in Tamil with pictures | User, 16-10-2026 |
| Many presses were designed, fabricated or redesigned in house. Hydraulic and electrical circuit diagrams exist for only some presses, and may be out of date, hand-drawn or missing; finding one during a breakdown is a hunt. Know-how (how to clean a press, change pump elements) is not written down anywhere | User, 16-10-2026 |
| Press supervisors will enter per press at the end of the day: strokes, run hours, energy meter reading, maximum power-pack oil temperature seen | User, 16-10-2026 |
| Gensets at several sites (e.g. 140 kVA at SSVT, 63 kVA at stockyard 1) and an EB incoming connection at every site. A turner-cum-fitter does a daily round of all gensets: visual check, fuel level, battery, running properly. The electrical department looks after some gensets and reads all EB incoming meters daily | User, 18-10-2026 |
| The electrical team head sends the owner a written report of each day's work. A typical day (09-10-2026): 7 packing machines cleaned with air; 2 SSVT stacker machines cleaned, batteries checked; 140 kVA genset battery check; stockyard 1 63 kVA genset battery maintenance and fuel level; portable vibrator carbon brushes replaced; SSVT press V201 photo guard cleaned, function restored; RO water purifier outlet cleaned; a new concrete vibrator's switchboard wired (commissioning); packing-machine AMC technician on site, trials of new packing machines | User, 18-10-2026 |
| The daily report will be printed from Yantra; odd jobs and new installations are written on the printout by hand (decided) | User, 18-10-2026 |
| **No calibration policy or SOP.** Measuring instruments in use: vernier calipers, digital multimeters, pressure transducers, temperature indicators, thermocouples, weigh scales, moisture analysers, energy meters, thermal imaging cameras, IR thermometers, a flexural strength testing machine. Owned by the **Quality lab and by production**; the lab's machines are to be in Yantra too | User, 20-10-2026 |
| A **weighbridge** and weigh scales are in use and need Legal Metrology stamping (verification by the state department) | User, 20-10-2026 |
| Calibration certificates come from agencies that are not NABL-accredited but state traceability; the Sartorius moisture analyser is calibrated by its vendor | User, 20-10-2026 |
| **Vehicle fleet**: SMTW and SSVT run about 40 vehicles between them. Repairs are done in house (the auto workshop, § 2) and at outside garages | User, 20-10-2026 |
| Fleet inspection today: now and then someone is asked to inspect every vehicle and submit a report; about once in six months, haphazard, when an inspector is available. The inspector is the head engineer or a visiting faculty member of the polytechnic's mechanical or automobile department. **Target: once a month** | User, 20-10-2026 |
| Each fleet inspection finds many small defects across many vehicles. Repairs are often deferred for a small reason (a part, a slot, the vehicle on the road) and then forgotten | User, 20-10-2026 |

TBD — which equipment is under AMC, with which vendors, and the contract terms (visits per year, response time, what is covered); how breakdowns are reported and recorded today; existing PM routines;
where the Mechanical and Electrical shops are and which sites they serve.

## 5. People and shifts

| Fact | Source |
|---|---|
| Shop-floor staff use phones on mobile data | Plan.MD, 11-10-2026 |
| Technicians are phone-first; engineers use phone and desktop | SRS draft, 12-10-2026 |
| Not all operators have a company mobile | User, 13-10-2026 |
| No RFID / badge cards in use for employees | User, 13-10-2026 |
| Raspberry Pi kiosks are planned on the shop floor for operators and supervisors to log on and enter things fast | User, 13-10-2026 |
| Kiosk locations are inside the plant, not accessible to the public | User, 13-10-2026 |
| Sorting line: a sorting supervisor with a phone and 5–6 automatic packing machines (APK01–06 or so) whose operators have no phone; they report CIL and faults to the supervisor orally or on a paper form | User, 16-10-2026 |
| Extrusion line: operators have a company mobile today and will get a shared kiosk or desktop, where they log in with their own account | User, 16-10-2026 |
| The fitter on the genset round has no phone; a supervisor or engineer will be assigned to record for him | User, 18-10-2026 |
| Drivers report to a drivers' supervisor; the head engineer is above him. Drivers have phones but get no Yantra access in this phase (a kiosk may come); the supervisor records for them | User, 20-10-2026 |
| Engineers and supervisors mostly carry **Samsung Galaxy** phones (Android); the project owner uses an **iPhone** | User, 21-10-2026 |

TBD — headcount per role per site; shift pattern; on-call arrangement; phones
company-issued or personal.

## 6. Stores and spares

| Fact | Source |
|---|---|
| One master store plus a few sub-stores (not necessarily one per site) | SRS draft, 12-10-2026 |
| Storekeepers issue parts; technicians only request | SRS draft, 12-10-2026 |
| No existing spares list or PM schedule to migrate | SRS draft, 12-10-2026 |
| Parts: Haendle (extruder) supplies drawings with part numbers usable for ordering. Many makers give no parts list; their service engineer visits, identifies the part and quotes. Generic spares (bearings, hydraulic valves, filters) are bought by standard designation, e.g. for the hydraulic presses | User, 17-10-2026 |

TBD — store names and locations; how issues are booked in OneERP today.

## 7. Systems

| Fact | Source |
|---|---|
| OneERP (ERPNext v16) holds purchasing, inventory, and production data | SRS draft / user, 12-10-2026 |
| Accounts are in Tally | SRS draft, 12-10-2026 |
| Single sign-on via Keycloak, realm `Office.smtw.in` | Plan.MD, 11-10-2026 |
| Keycloak accounts and password resets are handled by IT | User, 13-10-2026 |
| OneERP does not create users automatically on Keycloak login | User, 13-10-2026 |
| **plant-3i** — sister repo handling IIoT. Will provide telemetry to Yantra: production counts per day, oil temperature, run hours, PLC malfunction flags, etc. | User, 13-10-2026 |
| **VelKilnMaster** (vel-kiln) — sister app for the kiln. May flag kiln sensors as needing maintenance | User, 13-10-2026 |
| **VELVaahanMaster** (Frappe app `vaahan`) — vehicle fleet management: vehicle masters, drivers, trips, refuelling (odometer), tyres, legal compliance (insurance, permits, fitness certificate, road tax, PUC) and a maintenance-report doctype (vendor activities, invoices, attachments, cost). **Live and used daily** | Repo; user, 20-10-2026 |

## 8. Production data

TBD — what is recorded per equipment today (counts, run hours, cycle times), where,
and by whom.

## 9. History

Notable events in the factories' life that matter to maintenance (equipment
installations, major failures, rebuilds, layout changes). TBD.

## 10. Change log

| Date | Change |
|---|---|
| 13-10-2026 | File created from facts gathered in design sessions and the SRS draft |
| 13-10-2026 | Organisation and sites from the user. Replaces the SRS draft's "three sites: Main Plant, Ancillary Plant, Campus" with the six sites in § 2 |
| 13-10-2026 | Areas within SMTW from the user |
| 13-10-2026 | Stock yard 1 code set to **BRICKS** (was SMTW-KT; STOCKY1 also seen) — the name best known internally. VEL defined |
| 13-10-2026 | First unit code: `SMTW.FWMILL` |
| 13-10-2026 | Unit codes `SMTW.MCC1`, `SMTW.MCC2` (the new extrusion line) |
| 13-10-2026 | AMC practice recorded |
| 16-10-2026 | Sorting-line and extrusion-line use cases: MCC1 machines, AMC vendors, extruder and roller-mill practices, how operators record readings |
| 16-10-2026 | Pressing-shop use case: press counts and types, dies, availability, failure modes, oil condition, end-of-day readings |
| 16-10-2026 | Drawings and know-how; forgotten machines and operator onboarding |
| 17-10-2026 | Statutory inspections (lifts, cranes, pressure vessels, conveyors) and fire extinguishers |
| 17-10-2026 | Parts: makers' part lists, service-engineer quotes, generic spares |
| 20-10-2026 | ISO 9001 as a future goal; measuring instruments, their owners, weighbridge stamping, certificate sources |
| 18-10-2026 | Daily-report use case: genset round, EB meter readings, the electrical head's daily report, fitter without a phone |
| 21-10-2026 | Phones: mostly Samsung Galaxy; the project owner on iPhone |
| 20-10-2026 | Fleet use case: 40 vehicles, in-house and garage repairs, six-monthly inspection by the head engineer or polytechnic faculty with a monthly target, deferred-and-forgotten defects, drivers recorded for by their supervisor, the Vaahan app (live, used daily; forklifts in it) |
