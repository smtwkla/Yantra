```
Step: S082 — Under contract on the machine
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 7b8da9f+ (refs/steps/S081 at gate B; d216f48 + S079, S080, S081), checked by staleness review s1
Status: Committed 185d524 (adopted 31-10-2026); important checks pending: row 59 pending of device-checks.md (IT Admin); was: Gate B 31-10-2026 (code review r1: 1 minor, 1 nit, fixed in fix round 1; verify review r2: no finding; implemented by a resumed coder, paused 30-10-2026 for a reboot); approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 6 minor accepted)
From: R02.2 (second half)
```

# S082 — Under contract on the machine

## 1. What will be built

S081 records which machines each contract covers (`contract_equipment`). **S082 shows it where the
work starts: on the machine.** A technician who scans a machine's QR label sees at once that a
vendor looks after it, what is covered, and whether they may open it (R02 § Showcase). No
migration.

1. **The *Under contract* card** on the equipment page, after *Lessons* and **before *Open
   tickets***: per contract in force on the node or on its machine (its ancestors), "Under AMC with
   Atlas Copco until 31-03-2027", the response time, what is covered and not; the warning **"Do not
   repair. Call the engineer; the vendor repairs this machine."** in a warning colour when the
   contract has the D9 tick; the **call-out number**, a tap-to-call link, for `contract:read`
   holders, "To call the vendor, ask the engineer." for others (D10's rule); a link
   *Open contract* to S081's page. A contract ended in the last 90 days shows as "AMC with Atlas
   Copco ended on 31-03-2026." (§ 5.1–§ 5.3).
2. **A list filter** on the equipment list: *Contract: Any contract / Under contract / Not under
   contract* (§ 5.4).
3. **`auth_utils.sites_holding(cur, key)`**: S080's `contracts._sites_holding` moves to
   `auth_utils.py`, public and unchanged, so the equipment list can use it (§ 5.5, B10).

**After S082:** the floor sees a vendor's contract on every covered machine and part; the engineer
finds the machines under contract, or not, in one filter.

### Out of scope

- The machines, prices, contract page and history lines (S081).
- A part's contract on its machine's card (§ 9 Q4); upcoming contracts on the card (the contract
  page shows them).
- The contract on the printed asset list, as a column or a filter (B12).
- A tap-to-call link for S079's vendor office phone (stays text in Masters).
- A badge or column for "under contract" in the equipment list itself (the filter only).

## 2. Standards and practice

- **ISO 55001 § 8.3, outsourcing** (the clause number in the 2024 edition *to verify*). In plain
  words: work given to an outside firm stays the plant's responsibility, and the plant controls it.
  Control starts with the people at the machine knowing that a vendor maintains it and what that
  allows.
- **TPM, autonomous maintenance.** In plain words: operators and technicians care for their
  machines, within rules they are shown at the machine. Fuji's and Toyota's terms void the contract
  if anyone else repairs the machine (D9); the card says so where the work starts.
- **ISO 14224, equipment hierarchy** (the level numbers *to verify*). In plain words: maintenance
  data is kept against a tree from the plant down to the maintained part. A contract on a machine
  covers its parts, so the card shows it on every part of the machine (B4).
- **ISO/IEC 27001:2022 A.5.15, access control** and **A.8.3, information access restriction**
  (A.8.3 *to verify*). In plain words: each person sees only what the work needs, enforced by the
  system. The card sends the call-out number only to `contract:read` holders and never a price or a
  cost note; the filter counts only contracts the user may read.

## 3. Where

S079, S080 and S081 are coded before S082; this brief anchors by name in the files they change
(README § Anchors by name). Names marked **(from S080)** or **(from S081)** do not exist at the
baseline; they are as their briefs state them, and the staleness review checks them:
- (from S080): `contracts` and its columns; `backend/contracts.py` (`contracts_bp`,
  `_contract_out(row, flags)`, `_sites_holding(cur, key)`); `backend/contracts_core.py`
  (`contract_status(from_date, to_date, today)`); the four `contract:*` keys; the flag
  `can_read_callout`; `frontend/src/utils/contractLabels.js` (`statusBadgeClass`) and its test;
  `frontend/e2e/contracts.spec.js` with its in-spec helpers; `backend/tests/test_contracts_api.py`.
- (from S081): `contract_equipment` (`contract_id`, `equipment_id`) and
  `ix_contract_equipment_equipment`; the route `POST /api/contracts/<id>/equipment`; the page
  `/contracts/:id` (`frontend/src/views/ContractView.vue`); `coverageLines` and `responseText` in
  `contractLabels.js`; S081's tests in `contracts.spec.js`.

### Backend

- `backend/auth_utils.py`: `sites_holding(cur, key)` — S080's `_sites_holding`, moved here, public,
  same behaviour (`SELECT id, code, name, active FROM sites ORDER BY code`, kept where
  `has_perm_at(key, id)`) (§ 5.5).
- `backend/contracts.py` (from S080/S081): `_sites_holding` removed; its callers (S080's list and
  `sites`, S081's `_overlaps`) call `auth_utils.sites_holding`. The card route (§ 6).
- `backend/contracts_core.py` (from S080; S082 adds, pure): `CARD_ENDED_DAYS`,
  `card_items(rows, node, today)`, `COVERAGE_FILTERS`, `covered_sql(filter, site_ids, today)` (§ 5).
- `backend/equipment.py`: the `contract` filter in `list_equipment`, next to the `tickets` filter
  (§ 5.4).

### Frontend

- `frontend/src/views/equipment/UnderContractCard.vue` (new): the card (§ 5.3).
- `frontend/src/views/EquipmentDetailView.vue`: the card after *Lessons*, before *Open tickets*;
  the docstring line names the reason (BR1-01).
- `frontend/src/views/EquipmentView.vue`: the *Contract* select, `contract` in `FILTER_KEYS` and in
  `listUrl` (§ 5.4).
- `frontend/src/utils/contractLabels.js` (from S080/S081): `cardHeadline`, `callLine`, `telHref`
  (§ 5.3).
- `frontend/src/utils/equipmentFilters.js`: `CONTRACT_FILTER_CHOICES`.

### Tests

- `backend/tests/test_contracts_core.py` (from S080): the new core functions.
- `backend/tests/test_contract_card_api.py` (new): the card route.
- `backend/tests/test_equipment_api.py`: the `contract` filter.
- `frontend/tests/contractLabels.test.js` (from S080), `frontend/tests/equipmentFilters.test.js`.
- `frontend/e2e/contracts.spec.js` (from S080): the S082 tests (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 4.1 (equipment register): one line on the *Under contract* card and the list
  filter.
- `.claude/CLAUDE.md` § SMTW-Review: the point *Contract fields by key* (S080, S081) gains the card
  route (§ 8.6).
- `docs/schema/`: no change (no migration); `tooling\schema-docs.bat check` still exits 0.
- `docs/steps/device-checks.md`: one row (§ 8.5).

**File count:** 15 code and test files (4 backend code; 3 backend tests; 5 frontend code; 2
frontend unit tests and the spec), 3 docs. One concern.

## 4. Data model

No migration. S082 reads `contract_equipment` (S081, v44) by node through
`ix_contract_equipment_equipment`, and `contracts` (S080, v43). Computed on read, never stored: the
card's items (§ 5.1) and the filter (§ 5.4), from the dates in IST (`datetime.now(IST).date()`,
`IST` from `backend/equipment.py`).

## 5. Rules

### 5.1 Which contracts the card shows

Route `GET /api/contracts/for-equipment/<node_id>` (§ 6), on the node read by
`load_node_for_user(cur, node_id, for_update=False)` (404 outside the user's units; its row gives
`parent_id` and `gp_id`):

- a line on the node, its parent or its grandparent;
- the contract `active = 1`; `from_date <= today`; and `to_date >= today − CARD_ENDED_DAYS` (90, the
  roadmap's window). A contract that starts later is not shown (B15);
- at a site where the user holds `contract:read_basic` (`has_perm_at`, per site, once per request);
- one item per contract: the line nearest the node wins (the node, then the parent, then the
  grandparent).
- **Order** (`card_items`): not ended first, by `to_date, id` ascending; then ended, by `to_date`
  descending, then `id`.
- **The query** (BR1-02): one plain read, S080's contract select fragment (the one its list and
  `_fetch_contract` use, so the row has the shape `_contract_out` expects; its name is checked at the
  staleness review) joined to `contract_equipment ce` with `ce.equipment_id IN (…)` over the node,
  its parent and its grandparent (the NULLs dropped), `ct.active = 1` and the two dates as
  parameters; each row also carries `ce.equipment_id`.
- `card_items(rows, node, today)` takes those rows and `{id, parent_id, gp_id}` of the node and
  returns `[{row, via_id}]` in order, one per contract, the nearest line kept (`via_id` `None` on
  the node itself). The shell keeps the rows whose site passes `has_perm_at`, builds each through
  `_contract_out`, cuts it to § 5.2's keys, and sets `via` from the node row's columns (`parent_id`,
  `p_code`, `p_name`, or `gp_id`, `gp_code`, `gp_name`, `_NODE_COLUMNS` in `backend/equipment.py`),
  with no further query.

### 5.2 The item

Built by `_contract_out(row, flags)` (S080), so the gated-field rule stays in one place, then cut
to: `contract_id`, `title`, `contract_type`, `vendor_name`, `from_date`, `to_date`, `status`
(`contract_status`), `response_hours`, `covers_labour`, `covers_parts`, `covers_consumables`,
`covers_breakdown_calls`, `breakdown_calls_per_year`, `only_vendor_repairs`, `can_read_callout`,
`callout_number` (only with `can_read_callout`, at the contract's site), `via` (`null` on the node
itself, else `{id, code, name}` of the ancestor). **Never** `price`, `price_total`,
`priced_count` or `cost_note`, for any user (§ 5.6). Answer `{items}`.

### 5.3 The card

`UnderContractCard.vue`, `props: { node }`, loads its own list, as `LessonsCard.vue` does (B2).

- **Fetched** only when `node.permissions` (the node's site, `permissions_at_site`) holds
  `contract:read_basic`. **Hidden** when it has no items, **except** for a holder of
  `contract:edit` in `node.permissions`, who sees the card with "No contract on this machine."
  (R02.2: "shown only to editors, so others see no empty card").
- Header *Under contract*. One `list-group-item` per item:
  1. **The D9 warning**, first, for a contract not ended with `only_vendor_repairs`: `alert
     alert-warning` with `fa-triangle-exclamation`, "Do not repair. Call the engineer; the vendor
     repairs this machine."
  2. **The headline** (`cardHeadline`), bold: "Under AMC with Atlas Copco until 31-03-2027", "Under
     CMC with …", "Under warranty with …", "On-call contract with … until …"; ended: "AMC with Atlas
     Copco ended on 31-03-2026.", "CMC with … ended on …", "Warranty with … ended on …", "On-call
     contract with … ended on …". An *Ends in N days* badge (`statusBadgeClass`) when `status.kind`
     is `ending`.
  3. `via`: "Through CMP001 — Screw compressor 1, this part's machine."
  4. "Response time: " followed by S081's `responseText(hours)` ("24 hours", "1 hour"); the line is
     left out when it returns `null`.
  5. `coverageLines` (S081): "Covered: labour, consumables, breakdown calls (4 a year)." and "Not
     covered: spare parts."; a line with no item is left out.
  6. **The call line** (`callLine`), only for a contract not ended: a `contract:read` holder sees
     "Call-out number: +91 00000 00000", the number a **tap-to-call link** (BR1-04) shown as stored,
     its `href` from `telHref(number)` = `"tel:"` plus the number with every character but the
     digits and a leading `+` removed (`tel:+910000000000`); or "No call-out number on the
     contract." when it is empty. Anyone else sees "To call the vendor, ask the engineer." (BR1-05,
     a wording of D10's "Call the engineer"; § 9) — left out when the D9 warning already says to
     call the engineer.
  7. *Open contract*, a link to `/contracts/<id>`: every viewer of the card holds
     `contract:read_basic` at the contract's site, which is the page's gate.
  An ended item is in `text-secondary`, with no warning and no call line.
- **Place:** after *Lessons*, **before *Open tickets***, `order-0`, on every width: so on a phone
  *Lessons*, *Under contract*, *Open tickets*, then *Documents* (the S064 UX-07 order otherwise
  kept). The technician who has just scanned the label sees "Do not repair" before a long list of
  tickets, the reason S077 put *Lessons* first (§ 9 Q2, BR1-01).
- **A scrapped node** shows the card as any other node (S081 keeps its lines; the page is
  read-only); the card adds no lifecycle rule.
- **Errors:** "Contracts could not be loaded: <message>" in the card, as *Lessons*.
- **Disabled controls:** none. **Destructive controls:** none. The card has one link.

### 5.4 The equipment list filter

- **API:** `GET /api/equipment?contract=under|not_under` (`enum_arg("contract",
  COVERAGE_FILTERS)`; empty or absent = no filter; another value → 400). **Under contract** = the
  row's node, its parent or its grandparent is on a line of an **active contract in force today**
  (`from_date <= today <= to_date`) at a site in `sites_holding(cur, "contract:read_basic")`
  (admin: every site). **Not under contract** = not that. No such site → `under` is false for every
  row (no SQL with an empty `IN ()`), and `not_under` lists every row.
- `COVERAGE_FILTERS = ("under", "not_under")`. `covered_sql(filter, site_ids, today) -> (sql,
  params)` (pure, BR1-03): `sql` is `EXISTS (SELECT 1 FROM contract_equipment ce JOIN contracts ct
  ON ct.id = ce.contract_id WHERE ce.equipment_id IN (e.id, e.parent_id, p.parent_id) AND
  ct.active = 1 AND ct.from_date <= %s AND ct.to_date >= %s AND ct.site_id IN (%s, …))`, `NOT
  EXISTS (…)` for `not_under`; `params = [today, today, *site_ids]`, in the order the SQL names
  them. An empty `site_ids` returns `("0 = 1", [])` for `under` and `("1 = 1", [])` for
  `not_under` (no `IN ()`). The shell passes `datetime.now(IST).date()`. `p` is `NODE_JOINS`'
  parent alias; a NULL in the `IN` list never matches. equipment.py imports `contracts_core`
  (pure), never `contracts.py`.
- **Where:** in `list_equipment` beside the `tickets` filter, **not** in `_list_filters`: the
  printed asset list ignores it, as it ignores *Tickets* (`frontend/src/utils/assetList.js`
  `FILTER_KEYS` has neither) (B12).
- **Screen** (`EquipmentView.vue`): a select `aria-label="Contract"` after *Tickets*, from
  `CONTRACT_FILTER_CHOICES` = `["", "Any contract status"]`, `["under", "Under contract"]`,
  `["not_under", "Not under contract"]`, shown when `userPermissions` holds `contract:read_basic`;
  `contract` joins `FILTER_KEYS` (the phone's *Filters (n)* count) and `listUrl`, skipped for a user
  without the key, as `tickets`.
- With the default level *Equipment*, "Under contract" lists machines covered themselves; a machine
  with only a covered part is *Not under contract*. The filter and the card answer the same question
  about contracts in force for the same node (the card also shows those ended in the last 90 days).

### 5.5 `sites_holding`

- S082 moves it (decided once, here; S081 § 3 says the same): S081 still uses S080's
  `contracts._sites_holding` inside `contracts.py`; S082 is the first step that needs the rule
  outside `contracts.py`, and `equipment.py` cannot import `contracts.py`, which imports
  `equipment.py` (B10).
- Signature `sites_holding(cur, key) -> [{id, code, name, active}]`, the sites ordered by code where
  `has_perm_at(key, site_id)`. `key` must be in `SITE_SCOPED` (`has_perm_at`'s own assert).
- No behaviour changes in S080's and S081's routes; their tests prove it (§ 8.3).

### 5.6 Permissions

| Route or control | Key | Where checked |
|---|---|---|
| `GET /api/contracts/for-equipment/<node_id>` | `require_perm("contract:read_basic")`; `equipment:read` on the node's unit | 403 when held nowhere; 404 outside the user's units (`load_node_for_user`); each contract kept only where `contract:read_basic` is held at its site |
| the call-out number in an item | `contract:read` at the contract's site | `_contract_out` |
| the card's empty state | `contract:edit` at the node's site | `node.permissions` (screen only) |
| `GET /api/equipment?contract=` | `equipment:read` (as today) | each contract counted only at `sites_holding(cur, "contract:read_basic")` |
| the *Contract* select | `contract:read_basic` held somewhere | `userPermissions` |

- No new key; `test_role_matrix` unchanged. A request with no identity is refused with 401 by
  `require_auth`, never admin.
- `contract:read_basic` is `("*",)` and site-scoped (S080), so in practice everyone who sees the
  machine sees its contracts; the checks hold if the key narrows later.
- **Identity:** nothing here is written.

### 5.7 Locks

None. The card route and the list read plainly; S082 writes nothing.

### 5.8 The database down

Both routes go through `get_db()`: 503. The card shows its error text; the list shows its own, as
today.

## 6. API

| Route | Decorator | Then | Answer |
|---|---|---|---|
| `GET /api/contracts/for-equipment/<int:node_id>` | `contract:read_basic` | § 5.1, § 5.6 | 200 `{items}`; 403, 404 |
| `GET /api/equipment?contract=` | `equipment:read` | § 5.4 | 200 as today; 400 |

## 7. Design decisions

The B-numbers continue S081's (the split of 30-10-2026 kept them): B2, B4, B10 and B12 are this
step's, B15 is new; D1–D11 are the roadmap's.

- **B2. The card loads itself from a contracts route** (`/api/contracts/for-equipment/<node_id>`), as
  `LessonsCard.vue` loads `/api/procedures?equipment_id=`. equipment.py's node detail stays as it is,
  and equipment.py never imports contracts.py (which imports it). Rejected: contracts in
  `_detail` (an import cycle, and one more query on every node page for users the card skips).
- **B4. A contract on a machine shows on its parts' cards; a contract on a part does not show on the
  machine's card.** The roadmap's rule ("per contract in force on the node or its ancestors"; Q2.1 a
  "the card shows on the node and its parts"). The list filter answers the same. Rejected for now:
  the machine's card also listing its parts' contracts (§ 9 Q4).
- **B10. `sites_holding` moves to `auth_utils.py`, in this step.** equipment.py's filter needs the
  sites where `contract:read_basic` is held, and cannot import contracts.py. One copy of the rule.
  Rejected: a second copy in equipment.py (DRY); a lazy import (hides the cycle); the move in S081
  (S081 needs it only inside contracts.py).
- **B12. The filter sits in `list_equipment`, not `_list_filters`,** so the print ignores it as it
  ignores *Tickets*; the roadmap leaves the print's contract column for later. Rejected: in
  `_list_filters` (the print would filter by a fact it does not show).
- **B15. The card shows contracts in force and those ended in the last 90 days; not those that start
  later** (the roadmap's rule). A technician needs what holds today; a renewal that starts next month
  is on the contract page. Rejected: upcoming contracts on the card (two lines for one machine
  before the old one ends).

## 8. Tests and acceptance

### 8.1 Migration

None. `tooling\schema-docs.bat check` exits 0 unchanged.

### 8.2 Backend

**Core** (`test_contracts_core.py`): `card_items` with a fixed `today`: a line on the node and the
same contract on its parent → one item, `via` `null`; on the grandparent only → `via` the
grandparent; ended 90 days ago kept, 91 dropped; starting tomorrow dropped; the order (in force by
`to_date, id`, then ended by `to_date` descending; two ending the same day by `id`). `covered_sql` —
for `under` and `not_under` with one and three sites: the SQL, and `params == [today, today,
*site_ids]`; with no site, `("0 = 1", [])` and `("1 = 1", [])`.

**Frontend unit** (`contractLabels.test.js`): `cardHeadline` for each type, in force and ended;
`callLine` for a holder with a number, a holder without, and a non-holder ("To call the vendor, ask
the engineer."); `telHref("+91 00000 00000")` → `"tel:+910000000000"`, `telHref("0422-000 000")` →
`"tel:0422000000"`. `equipmentFilters.test.js`: `CONTRACT_FILTER_CHOICES`.

**Card API** (`test_contract_card_api.py`), each test with its own site, unit, vendor, contract and
machine (`make_site`, `make_unit`, `make_vendor`, `make_equipment`, `user_at_sites`, `uniq`;
contracts by `POST /api/contracts`, lines by S081's `POST /api/contracts/<id>/equipment`):
- a technician of the site: the contract in force, `callout_number` absent, `can_read_callout`
  false; the engineer: `callout_number` present;
- no item has `price`, `price_total`, `priced_count` or `cost_note`, for the manager too (a priced
  line, a cost note set);
- the machine's contract on its component-unit and on its component (`via`);
- ended 10 days ago (in, `status.kind` `ended`), 100 days ago (out); starting tomorrow (out); an
  inactive contract (out);
- the same contract on the node and its parent → one item;
- a node outside the user's units (404); a role with no `contract:read_basic` anywhere is not
  possible with `("*",)` — the test patches `PERMISSIONS["contract:read_basic"]` to
  `("maint_engineer",)` with `monkeypatch.setitem(config_rbac.PERMISSIONS, …)`, as `test_improvements_api.py` does, and the operator gets 403;
- a user with a role at site A only, on a machine of A whose contract is at B after a move: the item
  is not shown;
- **the database down** (`db_down`): 503.

**Equipment list** (`test_equipment_api.py`): `contract=under` lists a machine on a contract in force
and, at `level=all`, its parts; not a machine whose only covered node is its part; `not_under` the
reverse; an ended, an upcoming and an inactive contract do not count; a contract at a site where the
user holds no `contract:read_basic` (the patched key) does not count; `contract=maybe` → 400; `total`
matches the rows.

### 8.3 Existing tests that break or run again

- `backend/tests/test_contracts_api.py` (S080) and `backend/tests/test_contract_equipment_api.py`
  (S081): the `sites` list and the overlaps now run through `auth_utils.sites_holding`; green, no
  change.
- `backend/tests/test_equipment_api.py`: the list's answer keeps its keys; green.
- `backend/tests/test_rbac.py`: no new key; `test_role_matrix` unchanged.
- **Browser** (`frontend/e2e/equipment.spec.js`, `frontend/e2e/lessons.spec.js`):
  `S064: on a phone the Documents and Photos cards come before Details on the equipment page` and the
  Lessons test (the Lessons card above *Open tickets*) stay green: the new card comes after
  *Lessons* and before *Open tickets*, only when it shows, and *Documents* stays below both. The
  new S082 order test (§ 8.4) asserts *Lessons* < *Under contract* < *Open tickets*. `S064: on a phone the equipment list shows search first,
  Filters (n) with its count, …` asserts `"Filters (2)"` for a URL with no `contract`; green.
  `S029: the bulb is in view without scrolling and the Tickets filter fits the screen` — one more
  select on the desktop's filter row; re-run. No shared file changes (settings: *Shared code*).

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

In S080's spec, with its vendor and contract helpers and S081's line set-up by API. Each test makes
its own machine (and a part by API where it needs one), so other tests' contracts never show. Dates
relative to today, far from the edges. Untagged unless marked.

- **important** `S082: a technician sees the Under contract card with Do not repair and no number;
  the engineer sees the call-out number as a call link` — a contract with the D9 tick and
  `+91 00000 00000`: the technician sees the warning and no number; on a contract without the tick,
  "To call the vendor, ask the engineer."; the engineer's number is a link whose `href` is
  `tel:+910000000000`; *Open contract* opens the contract page.
- **important** `S082: the Under contract card comes before Open tickets` — a covered machine with
  an open ticket (raised by API): the card's header is above *Open tickets* and below *Lessons*
  when a lesson exists.
- **important** `S082: a contract on a machine shows on its part's card, naming the machine`.
- `S082: an ended contract shows on the card as ended, with no warning` — To 10 days ago.
- `S082: the engineer sees No contract on this machine; the operator sees no card`.
- `S082: a machine removed from its contract loses the card` — S081's *Remove* by API.
- **important** `S082: Under contract and Not under contract filter the equipment list` — the test's
  machine found by its name in each case.
- `S082: the Under contract card with its warning fits a phone with no sideways scroll` (`@device`)
  — `expectNoSidewaysScroll` on the equipment page of a covered machine.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/equipment.spec.js e2e/lessons.spec.js e2e/screens.spec.js`; the whole suite at Normal once at
the end.

### 8.5 On a real device

- **important** On a phone, the *Under contract* card's yellow "Do not repair" warning is readable
  at arm's length in the shop's light. **Set-up (in the row):** KLA adds a vendor *Test vendor* and
  a contract with *Only the vendor may repair* ticked on the TEST machine, on the **dev server only**
  (never production: a contract is never deleted). Account: a technician of SMTW; network: the
  plant's or home Wi-Fi; where: the dev server on KLA's laptop. Open the machine from its QR label
  (S014's path) and read the warning. A browser cannot judge the reading in real light; the row
  goes to `docs/steps/device-checks.md`, for IT Admin.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; the targeted and the Normal browser runs green.
- By screen: the technician scanning a compressor of "Atlas Copco AMC 2026–27" sees "Under AMC with
  Atlas Copco until 31-03-2027" and the warning, above *Open tickets*; the engineer taps the call-out
  number to call; *Under contract* in the list shows both compressors.
- **§ SMTW-Review** (the point *Contract fields by key* gains): "… S082: the card route
  (`/api/contracts/for-equipment/…`) builds its items through `_contract_out` and sends no price,
  total or cost note to anyone; the list filter counts only contracts at `sites_holding(cur,
  "contract:read_basic")`."

## 9. Open questions and assumptions

- **Q2. The card after *Open tickets* (the roadmap), or before it?** The *Do not repair* warning
  matters most before work starts; on a busy machine *Open tickets* can be long. (a) After, as the
  roadmap says. (b) Before *Open tickets*, after *Lessons*. **(b): decided by the orchestrator under
  the delegation of 30-10-2026 on the review's reasoning (BR1-01: the S077 precedent, the warning
  seen first); flagged for KLA at gate B.** A departure from the roadmap's "after *Open tickets*".
- **The call line for readers without `contract:read`:** "To call the vendor, ask the engineer."
  (BR1-05), a wording of D10's "Call the engineer" that says what the call is for. **Flagged for KLA
  at gate B.** The call-out number as a `tel:` link (BR1-04) departs from S079 D12's text-only phone;
  S079's vendor phone stays text.
- **A residual, accepted (from S081 § 9 Q5):** a machine moved to another site keeps its line, but
  the new site's technicians hold no `contract:read_basic` at the contract's site, so its card (and a
  D9 warning) does not show there. The contract page's "Now at BRICKS." is the engineer's cue to
  remove the line or move the contract. § 8.2 tests it.
- **Q4. A contract on a part: show it on the machine's card too?** (a) No, as the roadmap —
  recommended. (b) Yes, as "On M001 Motor: Warranty with ABB until …". **Taken as recommended by the
  orchestrator under the delegation of 30-10-2026; KLA may override at gate B.**
- **A1. The S080/S081 names** are as their briefs state them (§ 3); the staleness review checks
  them, `_sites_holding`'s callers, and `contractLabels.js`'s helpers.
- **A2. The 90-day window** (`CARD_ENDED_DAYS`) is a constant, from the roadmap.
- **Mock-ups and decisions (the decision wins):** mock-up 04's note "Every role with contract:read …
  sees the card" — D5 gives it to `contract:read_basic`; its line "For a breakdown, raise a ticket.
  The engineer calls the vendor." predates D10's "Call the engineer" and the D9 warning; its card
  stands after *Open tickets*, where Q2 now puts it before.
- **Standards *to verify*:** ISO 55001:2024's clause for outsourcing; ISO 14224's level numbers;
  ISO 27001 A.8.3.
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer | What changed |
|---|---|---|
| BR1-01 (minor) | Accepted | § 1, § 3, § 5.3: the card after *Lessons*, before *Open tickets*, on every width; § 8.3, § 8.4: the order test; § 9 Q2 decided under the delegation, flagged for KLA at gate B. |
| BR1-02 (minor) | Accepted | § 5.1: one query on S080's contract select fragment joined to `contract_equipment` over the node, parent and grandparent; `card_items` returns `[{row, via_id}]`; `via` from the node row's `p_code` / `gp_code` columns, no further query. |
| BR1-03 (minor) | Accepted | § 3, § 5.4: `COVERAGE_FILTERS = ("under", "not_under")`; `covered_sql(filter, site_ids, today) -> (sql, params)`, `params = [today, today, *site_ids]`, `0 = 1` / `1 = 1` with no site; § 8.2 tests as proposed. |
| BR1-04 (minor) | Accepted | § 1, § 5.3: the call-out number is a `tel:` link, `href` from `telHref` (digits and a leading `+` only); § 8.2 unit cases, § 8.4 e2e asserts the `href`; out of scope now names only S079's vendor phone. |
| BR1-05 (minor) | Accepted | § 1, § 5.3: "To call the vendor, ask the engineer."; § 9 flags it for KLA at gate B. |
| BR1-06 (minor) | Accepted | § 8.5: the device check on the dev server only, with its set-up in the row. |
| BR1-07…BR1-12 (nits) | Accepted as recommended | "about contracts in force"; order `to_date, id`; `via` "Through CMP001 — Screw compressor 1, this part's machine."; "Any contract status"; the moved-machine residual in § 9; a scrapped node shows the card as any other (§ 5.3). Also: S081's `responseText` returns "24 hours" / `null`, so the card writes "Response time: " itself (S081 BR1-04). |

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 30-10-2026

These answers override the brief text above where they differ; the coder follows them.

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted: the card query builds on `_CONTRACT_SELECT` (used by `list_contracts` and `_contract_row`; there is no `_fetch_contract`) and joins the lines as `contract_equipment cl` (reading `cl.equipment_id`), because `ce` is already taken inside `_CONTRACT_SELECT`. The row now also carries `machine_count`, `priced_count`, `price_total`; the card's key whitelist keeps them out (§ 5.2). |
| BS1-02 minor | Accepted: the technician, engineer and manager of the card and list tests are `user_at_sites` clients at the test's site (the conftest `engineer` holds no unit, so `load_node_for_user` answers 404 for it). |
| BS1-03…BS1-07 nits | Accepted: `_contract_out(row, flags, today)` takes three arguments; `_sites_holding`'s callers are `list_contracts` and `_detail`; an empty `?contract=` is refused with 400 by `enum_arg`, as the other enum filters — only an absent parameter means no filter; `CONTRACT_FILTER_CHOICES` goes in `contractLabels.js` (one file fewer); the SMTW-Review point to extend is *Contract fields by key (S080)*. |
