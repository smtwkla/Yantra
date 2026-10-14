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
| Main factory and working head office: SMTW, 10/712, Surandai Road, Pavoorchatram | User, 13-10-2026 |
| Registered head office: 10/710, Surandai Road, Pavoorchatram — a formal office only, no operations | User, 13-10-2026 |
| **VEL** is the combined org unit (SMTW with its sites and SSVT) for which Yantra is implemented — hence deployment ID `vel_yantra_master` | User, 13-10-2026 |
| Products — TBD (tiles; full product range to be listed) | — |

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
| **SSVT** | Sister concern's job-work unit (§ 1) | Hydraulic presses | TBD |

Source: user, 13-10-2026.

### Areas within SMTW (main factory)

| Group | Areas |
|---|---|
| Raw material | Clay stock; clay blending plots |
| Forming | Old extrusion and pressing line; new extrusion and punching line (called **MCC**, in two parts MCC1 and MCC2); hydraulic presses |
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
| `SMTW.MCC1` | New extrusion and punching line — first part | TBD | User, 13-10-2026 |
| `SMTW.MCC2` | New extrusion and punching line — second part | New extruder (Haendle GmbH); puncher (Keller-HCW GmbH); Atlas Copco screw compressors (2); others | User, 13-10-2026 |

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

TBD — headcount per role per site; shift pattern; on-call arrangement; phones
company-issued or personal.

## 6. Stores and spares

| Fact | Source |
|---|---|
| One master store plus a few sub-stores (not necessarily one per site) | SRS draft, 12-10-2026 |
| Storekeepers issue parts; technicians only request | SRS draft, 12-10-2026 |
| No existing spares list or PM schedule to migrate | SRS draft, 12-10-2026 |

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
