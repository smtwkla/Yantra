```
Step: S081 — Machines on the contract
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 31484e6 (refs/steps/S080; d216f48 + S079, S080), checked by staleness review s1
Status: Gate B 30-10-2026 (code review r1: 4 nits, fixed in fix round 1)
From: R02.2 (first half: the machines and their prices; the card and the list filter are S082)
```

# S081 — Machines on the contract

## 1. What will be built

S080 (R02.1) gives Yantra the contract record. **S081 says which machines each contract covers,
and what each costs.** It answers KLA's "what equipment" (R02 § The feature), and puts the **price
per machine** where D8 placed it. S082 (R02.2's second half) then shows the contract on each
machine: the *Under contract* card and the equipment list filter.

1. **The machines covered** (`contract_equipment`, migration **v44**, § 4): a contract names
   equipment nodes of **its own site**, at **any level** (Q2.1 a). One node may be on two contracts
   at once (Q2.2 a); the page warns when two contracts **of the same type** overlap in time on a
   node, its machine or its parts (§ 5.6).
2. **A price per machine, before GST** (D8): optional on each machine line. Read and written only
   with `contract:read_senior` at the contract's site (managers; admin by the bypass). The
   contract's **total is the sum** of its lines' prices, never typed. An editor without the key
   never sees a price, and never sends one (§ 5.4).
3. **The contract page** (`/contracts/:id`): the terms (S080's fields, each behind its key), the
   machines covered with *Add machine*, *Edit price* and *Remove*, and the total for senior
   holders. Masters › Contracts links each title to it, and gains the *Cost before GST* column for
   senior holders (S080 § 9 Q1 left it to R02.2).
4. **The machine's history**: each add and remove writes a line in `equipment_events` (new kinds
   `contract_added`, `contract_removed`), with the contract's title, type and period; never the
   price (ISO 9001 § 7.5).

**After S081:** the engineer records which machines each contract covers; the manager enters the
price per machine and sees the contract's cost; each machine's history shows when it came under
which contract.

### Out of scope

- The *Under contract* card on the equipment page and the equipment list filter (**S082**).
- Documents (R02.3: the contract becomes the **sixth** `file_store` owner there, not here),
  *Renew* (R02.4), reminders (R02.5), breakdown calls and the ticket's contract line (R02.6), PM
  visits (R02.7), the vendor report (R02.8); placeholder cards for them on the page (B8).
- *Edit* of the terms on the contract page (B9); a deep link to Masters' *Contracts* section
  (sections are local state, `frontend/src/views/MastersView.vue`).
- The contract on the printed asset list (R02.2 "leaves for later").
- Refusing a covered machine's move to another site (§ 9 Q5); a history of earlier prices.

## 2. Standards and practice

- **ISO 55001 § 8.3, outsourcing** (Plan.MD § 2 cites it; the clause number in the 2024 edition
  *to verify*). In plain words: work given to an outside firm stays the plant's responsibility;
  the plant decides what is outsourced, controls it and keeps the evidence. S081 records, per
  machine, which vendor maintains it, under which contract, until when and at what price.
- **ISO 14224, equipment hierarchy (taxonomy)** (the level numbers 6–8, equipment unit, subunit,
  maintainable item, *to verify*). In plain words: maintenance data is kept against a fixed tree of
  equipment, from the plant down to the part that is maintained. Yantra's tree is equipment →
  component-unit → component (S002). A contract may cover any level (Q2.1 a), so a motor warranty
  and a compressor AMC each sit on the node the maker or vendor named.
- **EN 13306, maintenance terminology: *item*** (the clause number *to verify*). In plain words:
  an *item* is any part, component, device, subsystem, equipment or system that can be described
  and considered on its own. A contract line names an item, so "covered" means the same thing at
  every level.
- **ISO 9001:2015 § 7.5.3, control of documented information.** In plain words: keep the records
  that show what was done, and protect them from loss and change. Each add and remove of a machine
  writes a line in the machine's history with who and when; the line keeps who changed its price
  last. **Departure (recorded):** a removed line is deleted (its history line stays), as
  `improvements.remove_ticket` deletes an `improvement_tickets` link (B5).
- **ISO/IEC 27001:2022 A.5.15, access control** and **A.8.3, information access restriction**
  (A.8.3 *to verify*). In plain words: each person sees only what the work needs, and the system,
  not the screen, enforces it. The price and the total leave the server only for
  `contract:read_senior` holders at the contract's site; the machine's history never holds a price
  (§ 5.4).

## 3. Where

S079 and S080 are coded before S081. In the files they change this brief anchors by name, not by
line (README § Anchors by name). Names marked **(from S079)** or **(from S080)** do not exist at
the baseline; they are as the two briefs state them (`docs/steps/S079-vendor-master/1-brief.md`,
`docs/steps/S080-contract-register/1-brief.md`), and the staleness review checks them:
- (from S079, in the working tree now): `vendors` (`name`, `active`); `make_vendor`
  (`backend/tests/conftest.py`).
- (from S080): `contracts` and its columns; `backend/contracts.py` (`contracts_bp`,
  `_contract_out(row, flags)`, `_fetch_contract`, `_sites_holding(cur, key)`, its LOCK ORDER note);
  `backend/contracts_core.py` (`CONTRACT_TYPES`, `contract_status(from_date, to_date, today)`); the
  four `contract:*` keys; the flags `can_edit`, `can_read_callout`, `can_read_cost`;
  `frontend/src/views/masters/ContractsPanel.vue`; `frontend/src/utils/contractLabels.js`
  (`contractTypeLabel`, `statusBadgeClass`) and its test; `frontend/e2e/contracts.spec.js` with its
  in-spec helpers; `backend/tests/test_contracts_api.py`, `backend/tests/test_migration_v43.py`.

**`_sites_holding` stays in `contracts.py`** in this step (S081's overlap read uses it there). S082
moves it to `auth_utils.sites_holding`, because S082's equipment list filter needs it outside
`contracts.py` (S082 B10).

### Backend

- `backend/local_db.py`: migration **v44** at the end of `_MIGRATIONS` (§ 4.1). No
  `_PRECONDITIONS` entry (§ 4.1).
- `backend/contracts_core.py` (from S080; S081 adds, pure): `validate_line(body, creating)`,
  `parse_price(raw)`, `PRICE_MAX`, `TYPE_SHORT`, `event_text(contract)` (§ 5).
- `backend/contracts.py` (from S080; S081 adds): the routes of § 6, the line locks (§ 5.5) in its
  LOCK ORDER note, `_machine_lines(cur, contract, flags)`, `_overlaps(cur, contract, lines, site_ids)` →
  `{equipment_id: [overlap, …]}`;
  `_contract_out` also drops `price_total` and `priced_count` without `can_read_cost`; the list and
  detail queries read `price_total` (a `SUM` subquery). Imports from `backend/equipment.py`: `IST`
  (already), `NODE_JOINS`, `node_path`, `accessible_unit_ids`, `write_events`.
- `backend/equipment.py`: docstring only. The LOCK ORDER's S080 `contracts.py` bullet is rewritten
  (§ 5.5).

### Frontend

- `frontend/src/views/ContractView.vue` (new): the contract page (§ 5.7).
- `frontend/src/views/contracts/ContractMachineDialog.vue` (new): *Add machine* and *Edit price*,
  one `FormModal.vue` through `useFormModal` (§ 5.7).
- `frontend/src/router/index.js`: the route `/contracts/:id(\\d+)`, name `contract`, meta title
  "Contract", no nav item (§ 5.7).
- `frontend/src/components/EquipmentPicker.vue`: optional props `siteId` (the search sends
  `site_id`) and `emptyText`; `pick` emits the item as a second argument (§ 5.7). No change for its two users today (`RaiseTicketView.vue`,
  `ReadingsRegister.vue`).
- `frontend/src/views/masters/ContractsPanel.vue` (from S080): the title links to `/contracts/<id>`;
  the *Cost before GST* column (§ 5.8).
- `frontend/src/utils/contractLabels.js` (from S080): `formatRupees`, `coverageLines`,
  `responseText` ("24 hours" / "1 hour" / `null`), `overlapText`, `lineBody` (§ 5.7). S082 reuses
  `coverageLines` and `responseText` on the card, with its own "Response time: " before the latter.
- `frontend/src/utils/equipmentLabels.js`: `describeEvent` cases `contract_added`,
  `contract_removed`.

### Tests

- `backend/tests/test_migration_v44.py` (new), on the pattern of `test_migration_v41.py`
  (`range(20, 45)`).
- `backend/tests/test_contracts_core.py` (from S080): the new core functions.
- `backend/tests/test_contract_equipment_api.py` (new): the line routes, the detail's machines, the
  gated price.
- `backend/tests/test_contracts_api.py` (from S080): § 8.3.
- `backend/tests/conftest.py`: `contract_equipment` joins `_TABLES`, first.
- `frontend/tests/contractLabels.test.js` (from S080), `frontend/tests/equipmentLabels.test.js`.
- `frontend/e2e/contracts.spec.js` (from S080): the S081 tests (§ 8.4), with S080's in-spec set-up
  helpers.

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: a `contract_equipment` line, area *Equipment*; the `equipment_events`
  line names the two new kinds; then `tooling\schema-docs.bat write`, read `git diff docs/schema/`,
  and `check` exits 0. `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 3, the contract keys' paragraph (from S080): the price per machine follows
  `contract:read_senior`, as the cost note. § 2 item 9 already says the rest (`docs/Plan.MD:48`).
- `.claude/CLAUDE.md` § SMTW-Review: S080's point *Contract fields by key* gains the price and the
  total (§ 8.6).
- `docs/steps/device-checks.md`: no row (§ 8.5).

**File count:** 19 code and test files (4 backend code; 5 backend tests; 7 frontend code; 2
frontend unit tests and the spec), 4 docs. One concern.

## 4. Data model

### 4.1 Migration v44

```sql
-- The machines a contract covers (S081, R02.2): one row per contract and node, any level (Q2.1 a),
-- a node of the contract's site when added.  A node may be on several contracts (Q2.2 a).  price:
-- the vendor's price for this machine for the contract period, in rupees before GST (D8), NULL =
-- not entered; read and written only with contract:read_senior.  The contract's total is the sum,
-- never stored.  A line removed by mistake is deleted; the machine's history keeps the add and the
-- remove (equipment_events, the two new kinds at the end of the ENUM, as v30 and v33 added theirs).
CREATE TABLE IF NOT EXISTS contract_equipment (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    contract_id   INT NOT NULL,
    equipment_id  INT NOT NULL,
    price         DECIMAL(10,2) NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by    VARCHAR(100) NOT NULL,
    updated_at    DATETIME NULL,
    updated_by    VARCHAR(100) NULL,
    CONSTRAINT uq_contract_equipment UNIQUE (contract_id, equipment_id),
    KEY ix_contract_equipment_equipment (equipment_id),
    CONSTRAINT fk_contract_equipment_contract FOREIGN KEY (contract_id) REFERENCES contracts (id),
    CONSTRAINT fk_contract_equipment_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT chk_contract_equipment_price CHECK (price IS NULL OR price >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE equipment_events MODIFY event
    ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model',
         'meter_added','meter_removed','meter_limits','property','contract_added','contract_removed')
    NOT NULL;
```

- **The ENUM list** is v33's (`backend/local_db.py`, the v33 entry, "Property values on equipment
  items (S044)"), the latest `MODIFY event` at the baseline, plus the two kinds at the end. The
  coder checks no later migration changed it before writing v44.
- **`uq_contract_equipment`** refuses a node twice on one contract; it joins `UNIQUE_KEY_ERRORS`
  (`backend/api_common.py`) as `("equipment_id", "This machine is already on the contract.")`.
  **`ix_contract_equipment_equipment`** serves the overlap read (by node), and S082's card and
  filter.
- **Foreign keys:** no `ON DELETE`, so `RESTRICT`; no contract or equipment row is ever deleted.
- **`price DECIMAL(10,2)`**: up to ₹9,99,99,999.99, paise kept; the quotes of R02 § D8 are whole
  rupees (₹9,000, ₹4,900, ₹18,040, ₹9,809, ₹28,028). 0 is allowed (a free warranty line); NULL is
  "not entered".
- **Re-run safety:** `CREATE TABLE IF NOT EXISTS`; the `MODIFY` to the same list is a no-op on a
  re-run, as v33.
- **No precondition** (`_PRECONDITIONS`): a new table, and an ENUM widened at its end, which
  converts no existing `equipment_events` row (v33's comment says the same). **Rollback:** a release
  before v44 never reads `contract_equipment`; a `contract_added` line shows as its raw name in the
  history (v33's note).

### 4.2 What is computed, never stored

- The total (`price_total`, `SUM(price)`), the count of priced lines, the count of lines.
- Each line's overlaps (§ 5.6), its `can_open`, its current site.

## 5. Rules

### 5.1 The line's fields

`validate_line(body, creating)` for `clean_body` (`backend/api_common.py`). Unknown fields are
ignored. The messages are scope B.

| Field | `POST` | `PUT` | Rule | Message (field) |
|---|---|---|---|---|
| `equipment_id` | required | ignored (the path names it) | integer ≥ 1, not a boolean | "Choose a machine." (`equipment_id`) |
| `price` | optional | optional | `parse_price`: `null` or `""` → NULL; an integer, or a string of digits with an optional `.` and 1–2 digits (`^\d+(\.\d{1,2})?$`, trimmed); 0 to `PRICE_MAX` = `Decimal("99999999.99")`; a float, a boolean, a negative, three decimals, "9,809" or "₹9809" refused | "Enter the price in rupees, before GST, e.g. 9809 or 9809.50." / "Price: at most 9,99,99,999.99." (`price`) |

- **A float is refused** (as `meters_core.parse_number`: a float is already rounded); the dialog
  sends a string.
- **A `PUT` without `price`** writes nothing and answers 200 with the contract as it is.
- `parse_price` is its own function, not `meters_core.parse_number`, which allows a minus sign and
  speaks of decimals of a meter type (B11).

### 5.2 Which node may be added

All decided inside the add's transaction (§ 5.5):

1. **The contract is active.** `active = 0` → 409 "This contract is inactive. Set it active in
   Masters › Contracts, then add machines." (no field). An ended contract takes adds (a
   correction; S080 § 5.1 lets an ended contract be changed). **A price change and a removal are
   allowed on an inactive contract** (BR1-03): a contract set inactive by mistake is still
   corrected, as S080 lets an inactive contract be edited.
2. **The node exists and the user may see it**: missing, or its root unit not in
   `accessible_unit_ids(cur)` (`equipment:read`) → 400 "Choose a machine." (`equipment_id`). The
   picker offers only those nodes, so only a hand-made request meets it.
3. **Not scrapped**, from the locked row: → 409 "A scrapped machine cannot be added to a contract."
   (`equipment_id`).
4. **At the contract's site**: the node's site is its root unit's site (`NODE_JOINS`:
   `units u ON u.id = COALESCE(gp.unit_id, p.unit_id, e.unit_id)`, then `sites s`). Another site →
   400 "Choose a machine of SMTW, the contract's site." (`equipment_id`; the contract's site code).
5. **Not on the contract already** → 409 through `uq_contract_equipment` (§ 4.1).

- **A node that moves later** to a unit of another site (equipment.py allows it: `_lock_target_unit`
  checks only `equipment:edit` at the new site) keeps its line: the rule holds when it is added.
  The contract page shows such a line with "Now at BRICKS." Refusing the move would put a contract
  check into equipment.py's move path (§ 9 Q5).
- **A node scrapped later** keeps its line (history); the page shows its lifecycle badge. A line of
  a scrapped node may be removed and its price edited.
- **A residual, accepted:** the site is read through the root's unit with a plain read after the
  node's shared lock (§ 5.5). A move of a part's **root** committed in the same instant is not
  blocked by that lock; the line then reads "Now at …" on the page. The same as S002's accepted
  display residual.

### 5.3 The history line

- On add: `write_events(cur, equipment_id, [("contract_added", None, event_text(contract))])`
  (`backend/equipment.py` `write_events`, actor from `actor()`), in the same transaction, after the
  insert.
- On remove: `("contract_removed", event_text(contract), None)`.
- `event_text(contract)` = `"<title> (<TYPE_SHORT>, DD-MM-YYYY to DD-MM-YYYY)"`, e.g. "Atlas Copco
  AMC 2026–27 (AMC, 01-04-2026 to 31-03-2027)"; `TYPE_SHORT` = `{"amc": "AMC", "cmc": "CMC",
  "warranty": "Warranty", "on_call": "On call"}`. At most 137 characters (100 + " (Warranty,
  DD-MM-YYYY to DD-MM-YYYY)"), inside
  `equipment_events.new_value VARCHAR(200)`. **Never the price** (the history is read with
  `equipment:read`).
- A price change writes no history line (it would carry the price); the line's `updated_at`,
  `updated_by` record it.
- `describeEvent`: "Added to contract: Atlas Copco AMC 2026–27 (AMC, 01-04-2026 to 31-03-2027)" and
  "Removed from contract: …".

### 5.4 The price: who reads and writes it

| What | Read | Written |
|---|---|---|
| `price` on a line, `price_total`, `priced_count` | only when `has_perm_at("contract:read_senior", site)` (`can_read_cost`, S080) | `POST` line: kept only then, else dropped; `PUT` price: only with `contract:edit` **and** `contract:read_senior` at the site, else 403 |
| the line itself (node, who/when, overlaps) | `contract:read_basic` at the site | `contract:edit` at the site |

- **Read:** every answer that holds a contract goes through `_contract_out` (S080 § 5.4), which now
  also deletes `price_total` and `priced_count` without `can_read_cost`; `_machine_lines` leaves the
  key `price` out of each line on the same flag. The key is **absent**, not `null` (S080 D4).
- **`POST` a line:** after `validate_line`, the shell drops `price` from the clean fields when the
  user lacks `contract:read_senior` at the contract's site, as S080 drops `cost_note`. IT admin and
  an engineer add machines without a price; the line's price is NULL.
- **`PUT` a price:** the route has no other field, so a non-holder gets **403** "You can't do this at
  SMTW" (`require_perm_at("contract:read_senior", site)`), not a silent no-op (B3). The page shows
  *Edit price* only when `can_edit` and `can_read_cost`.
- **Who:** a manager reads and writes prices; an engineer, IT admin and the floor never see one;
  admin both.
- **Removing a priced line** needs only `contract:edit`: an engineer may remove a line a manager
  priced, and the price goes with it (§ 9 Q3).
- **Identity:** no line field changes who can log in or what they see; a line names no person
  beyond the logins in `created_by` / `updated_by`.

### 5.5 Locks

The database runs REPEATABLE READ. A locking read sees the newest committed row; a plain read sees
the snapshot of the transaction's first plain read. **The contract lock is the first statement of
every line write**, so every plain read comes after it. contracts.py takes per write at most one
exclusive contract lock and one exclusive line lock, then only shared locks.

**Add** (`POST /api/contracts/<id>/equipment`), one `transaction`:

1. `SELECT * FROM contracts WHERE id = %s FOR UPDATE` → 404 when missing.
2. Plain: `contract:read_basic` at its site → 404; `require_perm_at("contract:edit", site)` → 403;
   `active` (§ 5.2 rule 1) from the locked row; the price rule (§ 5.4).
3. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` → missing: 400; scrapped
   (rule 3) from this row.
4. Plain: the node through `NODE_JOINS` (site, unit, root unit), `accessible_unit_ids` (rule 2),
   the site rule (rule 4).
5. `insert_row(cur, "contract_equipment", …, actor())` (`backend/db_helpers.py`): shared foreign-key
   locks on the contract (held exclusive) and the node (held shared); `uq_contract_equipment` gives
   the 409 of rule 5.
6. `write_events` (the insert share-locks the node, held).
7. The answer: the contract detail with its machines (§ 6.1), read inside the transaction.

**Change a price** (`PUT …/equipment/<equipment_id>`): (1) the contract `FOR UPDATE` → (2) plain:
404, 403 for `contract:edit`, 403 for `contract:read_senior` → (3) `SELECT id FROM contract_equipment
WHERE contract_id = %s AND equipment_id = %s FOR UPDATE` → 404 "This machine is not on the
contract." → (4) `update_row` (stamps `updated_at`, `updated_by`) → the answer.

**Remove** (`DELETE …/equipment/<equipment_id>`): (1) the contract `FOR UPDATE` → (2) plain: 404,
403 for `contract:edit` → (3) the line `FOR UPDATE` → 404 → (4) `DELETE` → (5) `write_events`
(`contract_removed`; a shared foreign-key lock on the node) → the answer.

**Reads** (the detail, the list): plain, no lock. S082's card and filter read plainly too.

**No deadlock cycle**, checked against the notes (`backend/equipment.py` LOCK ORDER,
`backend/masters.py`, `backend/tickets.py`, `backend/improvements.py`, `backend/procedures.py`, and
S080's `contracts.py` note):
- *The contract row* is locked only by contracts.py, always first in its transaction (S080's `PUT`,
  S081's three line writes). Nothing holds another lock and then waits on it.
- *The line row* is locked only by contracts.py, after its contract; no other module reads it with a
  lock.
- *The node (1)* is taken **shared** only, after the contract. equipment.py's writes (move, scrap,
  edit), meters.py, item_properties.py, documents.py and tickets.py's raise hold (1) exclusive and
  never wait on a contract or a line row, so an add waiting on (1) waits behind a writer that
  finishes. A scrap waiting for an add's shared lock gets it after the add commits, then its own
  checks run as today (a scrapped node keeps its line, § 5.2).
- *equipment_events* rows are inserted, never locked by anyone.
- *Two line writes on one contract* serialise on the contract row; two adds of one node to two
  contracts share the node's lock.

The coder rewrites S080's `contracts.py` bullet in equipment.py's LOCK ORDER: "contracts.py (S080,
S081) locks one contracts row FOR UPDATE first in its transaction; then a contract_equipment row FOR
UPDATE (a price change or a removal), the vendor row LOCK IN SHARE MODE (a vendor change), or the
node (1) LOCK IN SHARE MODE (a machine added), and the foreign-key shared locks of its inserts; a
contract create takes the site and the vendor LOCK IN SHARE MODE and locks no contract row; it
inserts equipment_events lines. Only contracts.py locks contracts and contract_equipment rows, and it
takes nothing exclusive outside them, so it adds no lock cycle." contracts.py's own note gives the
path-by-path check above.

### 5.6 Two contracts of one type on one node

Q2.2 a allows a node on two contracts, "with a warning when two contracts of the same type overlap".

- **Overlap of two lines:** another contract `c2` with `c2.active = 1`, `c2.id <> c.id`,
  `c2.contract_type = c.contract_type`, the periods meeting (`c2.from_date <= c.to_date AND
  c.from_date <= c2.to_date`), and a line of `c2` on **the same node, an ancestor of it, or a part of
  it** (an AMC on a compressor and an AMC on its motor overlap on the motor). `c2` only at a site in
  `_sites_holding(cur, "contract:read_basic")` (S080's, in `contracts.py`).
- **Where it shows:** under each line of the contract page, `text-warning-emphasis`: "Also in
  another AMC: Atlas Copco AMC 2025–26, 01-04-2025 to 31-03-2026." and, when the other line is on
  an ancestor or a part, " (on CMP001)". Type nouns: "AMC", "CMC", "warranty", "on-call contract".
  So the warning shows on both contracts' pages, at every visit, and after an add the page shows it
  at once (the `POST` answers with the detail).
- **Never a refusal.** A maker's warranty on a new motor inside a machine under AMC is normal; two
  AMCs on one machine is the case the warning is for (double payment).
- An inactive contract shows no overlaps and counts in none.
- One read per detail (`_overlaps`): the lines of the contract joined to the other contracts' lines
  through the nodes' `parent_id` columns (the tree has at most three levels, S002). Tens of rows.

### 5.7 The contract page

**Route** `/contracts/:id(\\d+)`, `ContractView.vue`, no nav item; the API's 404 is the gate (as the
lesson page, S077). Load: `GET /api/contracts/<id>`; 404 → "Contract not found, or not at your
sites." with a link to the equipment list. Reached from Masters › Contracts (§ 5.8) and, with S082,
from the machine's card.

- **Header:** the title (`h4`), badges: type (`contractTypeLabel`), status (`statusBadgeClass`),
  *Inactive* when so; under it "Atlas Copco · SMTW".
- **Terms** card (`dl`): Vendor ("(inactive)" when so), Vendor's contract number, Period "01-04-2026
  to 31-03-2027", Covered (`coverageLines` and `covered_text`), Not covered, PM visits per year,
  Response time (`responseText(hours)` → "24 hours", "1 hour", or `null`, shown "—"; S082's card
  writes "Response time: " before it), Only the vendor may repair ("Yes — the machines' pages warn:
  Do not repair."), Call-out number (only with `can_read_callout`), Cost note (only with
  `can_read_cost`); Notes; Updated (date · who). An empty optional field shows "—". The total shows
  once, under the machines (BR1-05).
- `coverageLines(contract)`: "Covered: labour, consumables, breakdown calls (4 a year)." and "Not
  covered: spare parts." from the four ticks (*Labour*, *Spare parts*, *Consumables*, *Breakdown
  calls*); a line with no item is left out.
- **Machines covered** card: header with the count and *Add machine* (when `can_edit` and the
  contract is active). One `list-group-item` per line, by code:
  - "CMP001 — Screw compressor 1", a link to `/equipment/<id>` when `can_open`, else plain text;
    under it the path (`full_path`) and the `LifecycleBadge` when not in service;
  - "Now at BRICKS." when the node's site is not the contract's (§ 5.2);
  - each overlap line (§ 5.6, `overlapText`);
  - the price (only with `can_read_cost`): `formatRupees` ("₹9,809", "₹9,809.50") or "No price";
  - *Edit price* (when `can_edit` and `can_read_cost`) and *Remove* (when `can_edit`). *Remove* asks
    in the row, as `MetersCard.vue`: "Remove CMP001 from this contract? Its history keeps the
    line." with *Keep* and *Remove*.
  - Under the list (only with `can_read_cost`, and only when the list has a line): "Total: ₹37,837
    before GST · 2 of 3 machines priced." or "No prices entered yet.".
  - Empty: "No machines on this contract yet." and, with `can_edit`, "Add the first one with Add
    machine." (no total line).
  - *Edit price* and *Remove* show on an inactive contract too (§ 5.2); only *Add machine* needs it
    active.
- **`ContractMachineDialog.vue`** (`FormModal.vue`, `useFormModal`, props `contract`,
  `canReadCost`): `useFormModal({ path: `/api/contracts/${id}/equipment`, blank, fromRecord,
  afterSave, toBody, label: (l) => l.code })`, with `toBody: (form) => lineBody(form, { creating:
  editingId.value === null, canReadCost: props.canReadCost })` — `editingId` from the composable's
  return, read at save time. `useFormModal` calls `toBody(form)` with one argument, so the dialog
  wraps the pure helper; no shared file changes (BR1-01).
  - `fromRecord(record)` → `{ equipment_id: record.equipment_id, price: record.price ?? "" }`.
  - `openCreate()` (no seed): `blank()` → `{ equipment_id: null, price: "" }`. Title *Add machine*.
    The `EquipmentPicker` with `site-id` = the contract's site and `empty-text` "No machine of SMTW
    matches."; a pick stores `{ equipment_id, code, name, full_path }` from the picker's second
    argument (no fetch) and shows "CMP001 — Screw compressor 1" with *Change* (back to the picker). **Price (₹, before GST)**, optional, only with
    `can_read_cost`, `inputmode="decimal"`, help "As in the quote, before GST. Only the managers of
    SMTW see it." Save *Add machine*, disabled until a machine is picked, with the reason "Choose a
    machine" in the footer (S064 UX-05).
  - `openEdit({ ...line, id: line.equipment_id })`: title *Edit price — CMP001*, the price field
    only; `PUT` path `…/equipment/<equipment_id>`.
  - `lineBody(form, { creating, canReadCost })`: create → `{ equipment_id, price }` with `price` left
    **out** unless `canReadCost` (`""` → `null`); edit → `{ price }`.
  - `afterSave(detail)`: the page takes the answered detail (no second fetch).
- **The one-tap path:** *Add machine* → type "CMP" → tap the machine → *Add machine*.
- **Disabled controls:** only the dialog's Save, with its reason. **Destructive:** *Remove* asks.
- **EquipmentPicker:** a new optional prop `siteId` (`Number`, default `null`); when set, the search
  adds `site_id` to `/api/equipment?level=all&q=` (the list's existing filter). A new optional prop
  `emptyText` (default the present "No equipment found at your units."). The `pick` event emits
  `("pick", e.id, e)`: the list item as a second argument (BR1-02). The two existing users,
  `RaiseTicketView.vue` (`chooseEquipment`) and `ReadingsRegister.vue` (`pick`), pass neither prop
  and ignore the second argument; `tickets-raise.spec.js` and `readings.spec.js` in the targeted run
  show them unchanged.

### 5.8 Masters › Contracts (S080's panel)

- The title cell is a `router-link` to `/contracts/<id>`.
- **Cost before GST**: a column from the `md` width, shown when any site in `sites` has
  `can_read_cost`; a row shows `formatRupees(price_total)`, or "—" when the key is absent or the
  total is NULL. This closes S080 § 9 Q1 as recommended there.

### 5.9 The database down

Every route goes through `get_db()`: 503 (§ Yantra Specifics, *DB may not exist*). The page shows the
error text. No background task, no alert.

## 6. API

All new routes on `contracts_bp` (`/api/contracts`), ids `<int:…>`. Each write answers with the
contract detail (§ 6.1), as `improvements.remove_ticket` answers with its improvement.

| Route | Decorator | Then | Answer |
|---|---|---|---|
| `GET /api/contracts/<id>` (S080, extended) | `contract:read_basic` | as S080 | 200, § 6.1 |
| `GET /api/contracts` (S080, extended) | `contract:read_basic` | as S080; each item gains `price_total` (gated) | 200 |
| `POST /api/contracts/<id>/equipment` | `contract:edit` | 404 (missing or `read_basic` not held at its site); 403 (`contract:edit` there); § 5.2 | 201; 400, 403, 404, 409 |
| `PUT /api/contracts/<id>/equipment/<equipment_id>` | `contract:edit` | 404; 403 (`contract:edit`); 403 (`contract:read_senior`); 404 line; an inactive contract is allowed | 200; 400, 403, 404 |
| `DELETE /api/contracts/<id>/equipment/<equipment_id>` | `contract:edit` | 404; 403; 404 line; an inactive contract is allowed | 200; 403, 404 |

A request with no identity is refused with 401 by `require_auth` before any route, never admin.

### 6.1 The detail

S080's item (§ 6.1 there) plus:
- `machine_count`; `price_total` and `priced_count` (only with `can_read_cost`);
- `machines`: `[{equipment_id, code, name, level, lifecycle, full_path, site_code, at_contract_site,
  can_open, price (only with can_read_cost), overlaps: [{contract_id, title, contract_type,
  from_date, to_date, on_code}], created_at, created_by, updated_at, updated_by}]`, by `code`.
  `on_code` is `null` when the other line is on the same node. `can_open` = the node's root unit in
  `accessible_unit_ids(cur)` (`None` = every unit).
- `price` is a string of the `DECIMAL` (`"9809.00"`), as Flask serialises a `Decimal`
  (`backend/db_helpers.py` `row_to_dict`); `formatRupees` shows it.

**Unit access on the page (B7):** every line is listed to a `contract:read_basic` holder at the
contract's site, whichever units they hold; only the link follows `can_open`.

## 7. Design decisions

This brief's decisions are numbered B1–B14 (with S082, which holds B2, B4, B10 and B12 since the
split); D1–D11 are the roadmap's (R02 § The feature), "S080 Dn" S080's.

- **B1. A link table with a price per line, not a list of node ids on the contract.** D8 puts the
  price on the machine line; S082's card and filter read by node through
  `ix_contract_equipment_equipment`. Rejected: a JSON list on `contracts` (no foreign key, no index,
  no price).
- **B3. The price route refuses a non-holder with 403; the add route drops the price.** The add has
  other fields and follows S080 D4 ("leaves it as it was"); a price change has no other field, so a
  silent 200 would tell the caller something false. The dialog never offers either to a non-holder.
  Rejected: drop on both (a no-op that answers 200); 403 on both (an add by IT admin that a stray
  field breaks).
- **B5. A removed line is deleted; the history keeps the add and the remove.** As
  `improvements.remove_ticket`. A line is usually removed because it was added by mistake. Rejected:
  a `removed_at` column (every reader filters it; R02.6 and R02.8 read the lines as they are).
- **B6. The overlap is a warning on the page, computed on read, never a refusal** (Q2.2 a). It stays
  visible on both contracts, not only once after a save. Rejected: a refusal (blocks the warranty
  inside an AMC); a one-time warning in the add's answer (lost on the next visit).
- **B7. The contract page lists every line, with a link only where the user has unit access.** A
  contract is a site record (S080 D8); its scope is part of its terms (D5: `read_basic` reads "the
  machines"), and the total must match the lines shown. Rejected: hiding lines outside the user's
  units (the scope would look incomplete and the total wrong).
- **B8. No placeholder cards** for documents, breakdown calls and PM visits. An empty greyed card
  raises questions nobody can answer yet. Rejected: the mock-up's greyed *PM visits*.
- **B9. No *Edit* of the terms on the contract page.** The dialog lives in `ContractsPanel.vue`
  (S080); moving it is a refactor of a step not yet coded. Engineers edit in Masters › Contracts.
  Rejected: extracting `ContractDialog.vue` now (one more file and a change to S080's panel; R02.4,
  which puts *Renew* on the page, can move it).
- **B11. `parse_price` is contracts_core's own.** Money is never negative and has at most two
  decimals; `meters_core.parse_number` allows a minus and speaks of a meter's decimals. Rejected:
  reuse with a wrapper (two messages for one field).
- **B13. The route `/contracts/:id`,** as the roadmap names it, beside `/api/contracts`. No nav item
  is lit on the page. Rejected: `/equipment/contracts/:id` (keeps *Equipment* lit, as the lesson
  page, but the engineers come from Masters; § 9 Q6).
- **B14. One machine per save.** The picker returns one node; the known contracts cover one to four
  machines (R02 § D8). Rejected: a multi-pick dialog (a new picker mode for a rare case). Departs
  from mock-up 03's *Add machines*.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v44.py`)

On the pattern of `test_migration_v41.py` (`_migrate`, `_recreate`, `_run`, `_schema` from
`test_migration_v20.py`):
- `test_a_fresh_database_gets_v44`: `contract_equipment` with `uq_contract_equipment`,
  `ix_contract_equipment_equipment`, both foreign keys and `chk_contract_equipment_price`; the
  `equipment_events.event` ENUM ends with `contract_added`, `contract_removed`.
- `test_a_v43_database_keeps_every_row`: a v43 database with a site, a vendor, a contract, a node
  and an `equipment_events` row of each existing kind migrates; the rows are kept.
- `test_the_price_check`: −0.01 refused (4025); 0 and 99999999.99 pass; a duplicate
  (contract, node) refused (1062); an unknown contract or node refused (1452).
- `test_a_rerun_changes_nothing`: `_schema()` equal.

### 8.2 Backend (`test_contracts_core.py`, `test_contract_equipment_api.py`)

**Core** (`test_contracts_core.py`): `validate_line` — `equipment_id` missing on create, `true`,
`"5"`, 0 refused; ignored on a `PUT`. `parse_price` — `None`, `""` → `None`; `9809`, `"9809"`,
`" 9809.5 "`, `"9809.50"`, `0`, `"99999999.99"` pass (`Decimal`); `9809.5` (float), `true`, `-1`,
`"-1"`, `"9809.505"`, `"9,809"`, `"₹9809"`, `"100000000"` refused with their messages.
`event_text` for each type, with the dates in DD-MM-YYYY and a 100-character title (≤ 200).

**API** (`test_contract_equipment_api.py`), each test with its own site, unit, vendor and contract
(`make_site`, `make_unit`, `make_vendor` (from S079), `make_equipment`, `user_at_sites`, `uniq`;
contracts by `POST /api/contracts`; the kept worker database gives the starting state):
- **Add:** the engineer adds a machine (201; the line in `machines`; no `price` key; an
  `equipment_events` row `contract_added` with `event_text`, read with `db_rows`); a component-unit
  and a component (201, any level); the manager adds with a price (201; `price` "9809.00",
  `price_total`, `priced_count` 1); the engineer and IT admin send a price (201; NULL stored); the
  same node twice (409 `equipment_id`); a node of another site (400, the message names the site); a
  scrapped node (409); an unknown node and a node outside the user's units (400 `equipment_id`); an
  inactive contract (409); the operator, technician, supervisor, storekeeper (403); an engineer of
  site B on a site-A contract (404 with no role at A; 403 naming A as operator there); a missing
  contract (404); a bad price (400 `price`).
- **Price:** the manager sets, changes and clears a price (200; `updated_by`); the engineer and IT
  admin (403 naming the site); a node not on the contract (404); a `PUT` without `price` (200,
  unchanged).
- **Remove:** the engineer removes a priced line (200; the row gone; `contract_removed` written with
  the old text); a node not on the contract (404); the operator (403).
- **Inactive contract:** `test_price_change_on_an_inactive_contract` (the manager, 200) and
  `test_removal_on_an_inactive_contract` (the engineer, 200; the history line written).
- **Detail:** `machines` by code; `price`, `price_total`, `priced_count` only for the manager;
  `can_open` false for a node in a unit the reader lacks; `at_contract_site` false after the node's
  machine moves to a unit of another site (by `PUT /api/equipment/<id>` as admin); overlaps: a
  second AMC overlapping on the same node (both contracts show it, `on_code` `null`), an AMC on the
  part of a covered machine (`on_code` the part's code), a warranty on the same node (none), an AMC
  that ended before the period began (none), an inactive second contract (none).
- **List:** `price_total` only on the manager's rows; absent for the engineer.
- **The database down** (`db_down`): `POST …/equipment` and `GET /api/contracts/<id>` answer 503.

### 8.3 Existing tests that break or run again

- `backend/tests/test_contracts_api.py` (from S080): any test that compares a whole contract item
  (detail or list) to a fixed key set breaks (new `machines`, `machine_count`, `price_total`,
  `priced_count`); the coder updates it.
- `backend/tests/test_modules.py` (`LATEST_VERSION`, now 44): green.
- `backend/tests/test_migration_v20.py` … `test_migration_v43.py`: each slices its own range; green.
- `backend/tests/test_schema_docs_shell.py`: green once `tooling\schema-docs.bat write` has run.
- `backend/tests/test_rbac.py`: no new key; `test_role_matrix` unchanged.
- `frontend/tests/equipmentLabels.test.js`: `describeEvent`'s default case for an unknown kind stays;
  two new cases.
- **Browser:** the router changes, a shared file (settings: *Shared code*), so the **whole browser
  suite runs again** at Normal at the end. `EquipmentPicker.vue` changes for its two users:
  `frontend/e2e/tickets-raise.spec.js` and `frontend/e2e/readings.spec.js` run in the targeted run.

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

All S081 tests live in S080's spec, which holds the vendor and contract set-up helpers. Each test
makes its own machine (`createEquipment`'s pattern, `frontend/e2e/equipment.spec.js`) and a part by
API where it needs one. Dates relative to today, far from the edges. Every flow test calls
`expectDialogFits` on the dialog it opens. Untagged unless marked.

- **important** `S081: the engineer adds a machine to a contract; the page lists it and the machine's
  history shows the line` — `"Add machine"`, the picker, the save; the row; the equipment page's
  History "Added to contract: …".
- **important** `S081: the manager enters a price per machine and sees the total; the engineer sees
  no price` — `"Edit price"`, "₹9,809", "Total: ₹9,809 before GST · 1 of 1 machines priced"; the
  engineer's page and *Add machine* dialog show no price field and no total.
- `S081: a machine of another site is not offered in Add machine` — a BRICKS machine by API: its
  name finds nothing in the picker.
- `S081: Remove asks first; the machine leaves the contract page and its history shows the line` —
  *Keep* keeps it; *Remove* removes it.
- `S081: a second AMC on the same machine shows the overlap line on both contract pages`.
- `S081: Masters › Contracts shows Cost before GST to the manager only, and the title opens the
  contract page`.
- `S081: the contract page with its machines fits a phone with no sideways scroll` (`@device`) —
  `expectNoSidewaysScroll` with three lines.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/masters.spec.js e2e/tickets-raise.spec.js e2e/readings.spec.js e2e/screens.spec.js`; the whole
suite at Normal once at the end (the router is shared code). No change to `api.js` or
`e2e/support/`, so no extra WebKit run.

### 8.5 On a real device

None. The page and the dialog are screens a browser engine judges.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal
  browser runs green.
- By screen: "Atlas Copco AMC 2026–27" on SMTW covers two compressors; the manager enters ₹9,809 and
  ₹28,028 and sees "Total: ₹37,837 before GST"; the engineer sees the machines and no price; each
  compressor's history shows "Added to contract: …".
- **§ SMTW-Review** (S080's point *Contract fields by key* gains): "… R02.2 (S081): `price`,
  `price_total` and `priced_count` follow `contract:read_senior` through `_contract_out` and
  `_machine_lines`; the machine's history (`contract_added`, `contract_removed`) never holds a price.
  A price change needs `contract:edit` and `contract:read_senior` at the site." S082 adds the card
  route to the point.

## 9. Open questions and assumptions

- **Q1. Split R02.2 in two.** Taken by the orchestrator under the delegation of 30-10-2026: this step
  is the machines and their prices; the *Under contract* card and the list filter are **S082**
  (`docs/steps/S082-under-contract-card/1-brief.md`). Q2 (the card's place) and Q4 (a part's
  contract on its machine's card) moved there with it.
- **Q3. May an engineer remove a line a manager priced?** (a) Yes; the price goes with the line and
  the manager re-enters it — recommended. (b) Refuse while a price is set: "This machine has a
  price. Ask a manager of SMTW to remove it." — tells a non-holder that a price exists. **Taken as
  recommended by the orchestrator under the delegation of 30-10-2026; KLA may override at gate B.**
- **Q5. A covered machine moved to another site:** (a) keep the line, marked "Now at BRICKS." —
  recommended. (b) Refuse the move while a contract in force covers it (a contract check in
  equipment.py's move path, and its lock). **Taken as recommended by the orchestrator under the
  delegation of 30-10-2026; KLA may override at gate B.**
- **Q6. The page's route:** (a) `/contracts/:id`, the roadmap's — recommended. (b)
  `/equipment/contracts/:id` (keeps *Equipment* lit, as the lesson page). **Taken as recommended by
  the orchestrator under the delegation of 30-10-2026; KLA may override at gate B.**
- **A1. The S079/S080 names** are as their briefs state them (§ 3); the staleness review before
  coding checks them, the migration numbers v42/v43, S080's `_contract_out`, `_sites_holding`, its
  flags, its LOCK ORDER note and its spec's helpers.
- **A2. Indian number grouping** (`₹9,99,99,999.99`) through `toLocaleString("en-IN")`, as
  `frontend/src/utils/meterLabels.js` uses.
- **Mock-ups and decisions (the decision wins):** mock-up 03 shows one contract cost "₹1,85,000" in
  *Terms*, where D8 puts a price per machine and a sum; its *Add machines* is one machine per save
  here (B14); its greyed *PM visits* card is left out (B8).
- **Roadmap text:** R02.2's item omits Q2.2 a's overlap warning (Plan.MD § 2 item 9 has it); this
  brief adds it (§ 5.6).
- **Standards *to verify*:** ISO 55001:2024's clause for outsourcing; ISO 14224's level numbers;
  EN 13306's clause for *item*; ISO 27001 A.8.3.
- **B3, flagged for KLA at gate B:** the price route answers 403 to a non-holder, where S080 D4
  ignores a gated field on write. The first place the two rules differ; kept (the route has no other
  field).
- **The picker's empty text** inside the dialog: "No machine of SMTW matches." (`emptyText`), so a
  machine of another site does not read as "not at your units" (BR1-10).
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer | What changed |
|---|---|---|
| BR1-01 (minor) | Accepted | § 5.7: the dialog wraps `lineBody` in its `toBody` with `creating` (from `editingId`) and `canReadCost`; `fromRecord` stated; no shared-file change. |
| BR1-02 (minor) | Accepted | § 3, § 5.7: `EquipmentPicker` emits `("pick", e.id, e)`; the dialog stores the item, no fetch; `RaiseTicketView.vue` and `ReadingsRegister.vue` ignore the second argument, shown by `tickets-raise.spec.js` and `readings.spec.js`. |
| BR1-03 (minor) | Accepted | § 5.2, § 5.7, § 6: *Edit price* and *Remove* allowed on an inactive contract; § 8.2: two tests. |
| BR1-04 (minor) | Accepted | § 3, § 5.7: `responseText` returns "24 hours" / "1 hour" / `null`; S082's card writes its own "Response time: " (S082 changed to match). |
| BR1-05…BR1-11 (nits) | Accepted as recommended; BR1-11 (the INDEX row) is the orchestrator's | The total shows once, under the machines; no total line on an empty list; `_overlaps(cur, contract, lines, site_ids)`; the equipment.py bullet keeps S080's create clause; "at most 137"; the picker's `emptyText` "No machine of SMTW matches."; B3 flagged for KLA at gate B in § 9. |

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 30-10-2026

These answers override the brief text above where they differ; the coder follows them.

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted: the code's names are `_contract_out(row, flags, today)`, `_contract_row(cur, contract_id)` (the joined read) and `_answer(cur, contract_id)` (a write's answer); § 6.1's detail (machines, total) is built in one helper that both `get_contract` and `_answer` call, so S080's `PUT` answer carries it too. |
| BS1-02 minor | Accepted: the price goes through S080's one gating mechanism — `contracts_core.LINE_GATED_FIELDS = {"price": "contract:read_senior"}`; `contracts._drop_gated(clean, site_id, fields=GATED_FIELDS)` gains the `fields` argument; the line write routes call it with `LINE_GATED_FIELDS` (the price-change route keeps its 403 by B3 before any drop); § 8.6's SMTW-Review text names `_drop_gated` for the line. |
| BS1-03…BS1-06 nits | Accepted as recommended: rewrite contracts.py's whole docstring (first paragraph, ACCESS, no-cycle list, LOCK ORDER); S080's API tests pin no whole key set, so they stay green; `test_migration_v43.py` is the pattern; the dialog uses `useFormModal` (not the panel's `useMasterForm` wiring). |
