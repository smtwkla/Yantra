```
Step: S086 — Breakdown calls on the contract
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: refs/steps/S084 (100cd87; d216f48 + S079–S084) and S085's approved brief, checked by staleness review s1
Status: Approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 4 minor; BR1-03, Q2 and C3 flagged for KLA at gate B)
From: R02.6
```

# S086 — Breakdown calls on the contract

## 1. What will be built

A vendor's breakdown call is already a ticket (D3): a Team record linked to the vendor (S079,
`people.vendor_id`) is assigned to it or logs labour on it. **S086 shows those tickets on the
contract, and shows the contract on the ticket.** Nothing is typed twice. No migration (§ 4).
It answers KLA's "breakdown visits if any" (R02 § The feature).

1. **A *Breakdown calls* card on the contract page** (`ContractView.vue`, from S081): every ticket
   on a covered node or its parts (the node and its descendants), happened within the contract's
   period, on which a Team record linked to the contract's vendor is an assignee or has a labour
   row (§ 5.1). Per call: serial (a link), machine and part, severity, when it happened, back in
   service, downtime, the wait on the vendor, state, the vendor's people. A total line ("3 calls ·
   down 5 h 20 min · waited on the vendor 2 h") and, when the contract agrees a number of calls
   per year (S080), "3 of 4 calls used this period." (§ 5.3).
2. **Two warnings** in the card, for an active contract not ended (§ 5.4): no Team record linked
   to the vendor; no linked record that can be assigned at the contract's site.
3. **The contract line on the ticket page** (`TicketContractLine.vue`, § 5.6): on an open ticket
   whose node is under a contract in force, "Under AMC with Atlas Copco until 31-03-2027 ·
   response 24 hours · breakdown calls included", a link to the contract, and S082's warning "Do
   not repair. Call the engineer; the vendor repairs this machine." when the contract has the D9
   tick. The engineer then assigns the vendor's people, not an in-house technician.
4. **The vendor in the people picker** (`PersonPicker.vue`, § 5.7): "Atlas Copco service ·
   Technician · Atlas Copco"; typing "atlas" finds the vendor's people.

**After S086:** the engineer sees on one page how often the vendor came, how long each machine
was down and how long the plant waited for the vendor; on the ticket, that the vendor must be
called.

### Out of scope

- The vendor's arrival time (Q6.2 a: not now).
- The report across contracts and vendors (R02.8, waits for PM).
- PM visits against the contract (R02.7, waits for PM).
- A history of a person's vendor link (Q9.5 a: the current link counts; S079 shows the warning in
  the Team dialog).
- The vendor beside an assignee on the ticket's *Assigned* card, or on a labour row (the picker
  only, as the roadmap says).
- The contract line on a closed ticket (§ 7 C6).
- The call-out number on the ticket line (§ 9 Q3).
- Any change to S082's card route or its *Under contract* card; the ticket line reuses S082's
  exported text and helpers (§ 3, BS1-01).

## 2. Standards and practice

- **EN 13306, corrective maintenance and logistic delay** (EN 13306:2017; clause numbers *to
  verify*). In plain words: corrective maintenance is the work after a failure; logistic delay is
  the time the repair waits for resources (parts, a vendor, an expert). A vendor's call is
  corrective maintenance, recorded as a ticket; *waited on the vendor* is the logistic delay with
  the reason *vendor* (S019, `tickets_core.WAITING_REASONS["vendor"]`), computed by
  `tickets_core.ticket_times`, the ticket page's function. No new kind of delay.
- **ISO 14224, maintenance data: maintenance resources** (§ 9; the table number *to verify*). In
  plain words: each maintenance event records who did the work, in-house staff or a contractor.
  Yantra records it already (the assignee and labour row name a Team record, *contractor*, and
  S079 names its firm); S086 only reads that link.
- **ISO 9001:2015 § 8.4, control of externally provided processes, products and services**
  (ISO 9001 is a future goal for the plant). In plain words: the plant checks how its outside
  providers perform and keeps the evidence (§ 8.4.1), with controls that fit the risk (§ 8.4.2).
  The card is that evidence for one contract; the per-vendor report is R02.8.
- **ISO 55001 § 8.3, outsourcing** (the 2024 edition's number *to verify*). In plain words: work
  given to an outside firm stays the plant's responsibility. The ticket line puts the contract in
  front of the engineer who assigns the work.
- **ISO/IEC 27001:2022 A.5.15 and A.8.3, access control and information access restriction.** In
  plain words: each person sees only what the work needs. The card lists only tickets the reader
  could open (§ 5.5) and sends no count of the others.

## 3. Where

S079 is coded in the working tree; S080–S085 are coded before S086. This brief anchors by name
(README § Anchors by name). Names marked **(from S0NN)** do not exist at the baseline; the
staleness review checks them:
- (from S079): `vendors`, `people.vendor_id`, `ix_people_vendor`, the fixture `make_vendor`.
- (from S080): `contracts` and its columns (`site_id`, `vendor_id`, `active`, `from_date`,
  `to_date`, `covers_breakdown_calls`, `breakdown_calls_per_year`, `response_hours`,
  `only_vendor_repairs`); in `backend/contracts.py`: `contracts_bp`, `READ_BASIC`,
  `_CONTRACT_SELECT` (with `vendor_name`, `site_code`), `_contract_row(cur, contract_id)`,
  `_contract_out(row, flags, today)`, `_today()` and `get_contract`'s 404 rule (missing, or
  `READ_BASIC` not held at the row's site). These are read from the working tree's
  `backend/contracts.py` (S080 being coded, 30-10-2026); S080's brief says `_fetch_contract` and
  `_contract_out(row, flags)`. Also `contracts_core.contract_status(from_date, to_date, today)`,
  `frontend/src/utils/contractLabels.js` and its test, `frontend/e2e/contracts.spec.js` with its
  in-spec helpers, `backend/tests/test_contracts_core.py`, `backend/tests/test_contracts_api.py`,
  and the § SMTW-Review point *Contract fields by key*.
- (from S081): `contract_equipment` (`contract_id`, `equipment_id`, `uq_contract_equipment`); the
  route `POST /api/contracts/<id>/equipment`; the page `frontend/src/views/ContractView.vue`;
  `responseText` and `coverageLines` in `contractLabels.js`.
- (from S082): `GET /api/contracts/for-equipment/<int:node_id>`, its items (§ 5.2 there),
  `auth_utils.sites_holding`, `cardHeadline` in `contractLabels.js`,
  `frontend/src/views/equipment/UnderContractCard.vue`.
- (from S083): the *Documents* card on `ContractView.vue` ("after the *Machines covered* card,
  before any later card").
- (from S085): the renewal chain line and *Renew* on `ContractView.vue`.

### Backend

- `backend/contracts.py` (from S080): the route `GET /api/contracts/<int:contract_id>/calls`
  (§ 6), with `_call_rows(cur, contract)`, `_vendor_people(cur, ticket_ids, vendor_id)` and
  `_vendor_reach(cur, vendor_id, site_id)`. The module docstring names S086 and its reads (no
  lock). It imports `events_by_ticket` from `tickets.py` and `unit_access_condition` from
  `equipment.py` (`accessible_unit_ids` and `IST` are already imported; BS1-03). No cycle (BR1-11,
  checked; s1 re-checked): `tickets.py` imports `alerts`, `equipment`, `improvements_core` and
  `tickets_core`, none of which imports `contracts.py`. Since S082 and S084, `equipment.py` and
  `alerts_core.py` import `contracts_core`, so `contracts_core` may import only pure modules
  (`tickets_core`, `masters_core`), never a shell module (BS1-04).
- `backend/contracts_core.py` (from S080, pure): `call_figures(state, not_a_fault, events, now)`,
  `calls_total(calls)`, `calls_used(count, per_year, from_date, to_date, complete)`,
  `vendor_warning(linked_count, assignable_count)`, `CALLS_USED_MAX_DAYS` (§ 5). It imports
  `ticket_times` and `latest_restoration` from `tickets_core` (pure → pure; no cycle:
  `tickets_core` imports only the standard library).
- `backend/tickets.py`: `events_by_ticket(cur, ticket_ids)` (moved from
  `improvements._events_by_ticket`, public, the same code); `people_at_site` adds `vendor_name`
  (§ 5.7). The docstring's *Import direction* paragraph adds "contracts.py (S086) imports
  events_by_ticket from here; this module never imports contracts.py".
- `backend/improvements.py`: `_events_by_ticket` removed; `_linked_tickets` and its other caller
  call `tickets.events_by_ticket` (added to its `from tickets import …` line). No behaviour
  changes.

### Frontend

- `frontend/src/views/contracts/BreakdownCallsCard.vue` (new): the card (§ 5.3, § 5.4).
- `frontend/src/views/ContractView.vue` (from S081): the card, after S083's *Documents* card, last
  on the page; the docstring names it.
- `frontend/src/views/tickets/TicketContractLine.vue` (new): the ticket's contract line (§ 5.6).
- `frontend/src/views/TicketDetailView.vue`: the line between the plan line and the action bar;
  the docstring gains an S086 paragraph.
- `frontend/src/views/tickets/PersonPicker.vue`: the vendor after the role, in the list and in
  the picked line (§ 5.7).
- `frontend/src/utils/ticketLabels.js`: `groupPeople`'s filter also matches `vendor_name`.
- `frontend/src/utils/contractLabels.js` (from S080): `callsTotalLine(total)`,
  `callsUsedLine(used)`, `ticketContractLine(item)`. The ticket line reuses S082's exported
  `DO_NOT_REPAIR`, `showsDoNotRepair` and `isEnded` (BS1-01); `UnderContractCard.vue` already
  imports `DO_NOT_REPAIR` and does not change.

### Tests

- `backend/tests/test_contracts_core.py` (from S080): the new core functions (§ 8.2).
- `backend/tests/test_contract_calls_api.py` (new): the route (§ 8.2).
- `backend/tests/test_tickets_api.py`: `TestPickers::test_people_of_the_site_with_trades_and_role`
  changes; one new test (§ 8.2, § 8.3).
- `frontend/tests/contractLabels.test.js` (from S080), `frontend/tests/ticketLabels.test.js`.
- `frontend/e2e/contracts.spec.js` (from S080): the S086 tests (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 2 item 9: after "derived, never re-entered", add "; listed on the contract page
  with downtime and the wait on the vendor, and the contract shows on the ticket (S086)". § 4.2:
  "An open ticket on a machine under contract shows the contract, and the people picker names a
  contractor's vendor (S086)."
- `.claude/CLAUDE.md` § SMTW-Review: the point *Breakdown calls (S086)* (§ 8.6).
- No change: `docs/schema/` (`tooling\schema-docs.bat check` exits 0), `docs/steps/device-checks.md`.

**File count:** 17 code and test files (4 backend code, 3 backend tests, 7 frontend code, 2
frontend unit tests, 1 spec), 2 docs. One concern: the
vendor's work on tickets, seen from the contract and from the ticket. A split is possible (§ 9
Q1); not recommended.

## 4. Data model

**No migration.** Every fact is stored: the covered nodes (`contract_equipment`, S081, v44); the
vendor, period, ticks and calls per year (`contracts`, S080, v43); who worked on a ticket
(`ticket_assignees`, `ticket_labour`, S018); a Team record's firm (`people.vendor_id`, S079, v42,
`ix_people_vendor`); downtime and waiting from `ticket_events` through `tickets_core.ticket_times`
(S018, S019). Q9.5 a (the current link counts) is why nothing is copied onto the ticket rows; its
option (b) needed a migration and a backfill. The calls, total, used line and warnings are
computed on read, never stored.

## 5. Rules

### 5.1 Which tickets are breakdown calls

For one contract `ct` (its row from `_contract_row`, after `get_contract`'s 404 rule):

1. **On a covered node or its parts.** The tree is at most three levels (machine →
   component-unit → component; `tickets_core.machine_and_component`). A ticket stores its machine
   (`tickets.equipment_id`, always the root) and its component (`tickets.component_id`, the node
   it was raised on below the machine, or `NULL`). The ticket counts when one of its line nodes
   `ce.equipment_id` is in `(t.equipment_id, t.component_id, c.parent_id)`, where `c` is the
   component's row:
   - a line on a machine: every ticket on the machine and on all its parts (`t.equipment_id`);
   - a line on a component-unit: tickets on it (`t.component_id`) and on its components
     (`c.parent_id`);
   - a line on a component: tickets on it (`t.component_id`).

   S082's relation read the other way (S082: the line on the node, its parent or grandparent). A
   ticket on a machine never counts for a contract on one of its parts (S082 B4). Which values
   count (BR1-03): `t.equipment_id` is the **machine at raise** (never rewritten; a part may move
   to another machine, `equipment_core` `moved_parent`); `t.component_id` is the ticket's
   component as it stands (an edit may change it, S018); `c.parent_id` is the component's
   **current** parent. So a covered part's tickets count wherever the part stood when raised
   (query 2's second `IN`), and a covered machine counts the tickets raised on it, also on a part
   that later left it.
2. **In the period.** `t.occurred_at` (the time it happened, IST, as stored) from `from_date
   00:00` up to, not including, `to_date + 1 day 00:00`: both end days count (S080 § 5.3, "the
   period is inclusive"). Raise time (`created_at`) is not used: a back-dated ticket counts on the
   day it happened.
3. **Worked by the vendor.** An assignee row or a labour row of the ticket names a person with
   `people.vendor_id = ct.vendor_id` **now** (Q9.5 a). An inactive person counts: the link is the
   history. A person unassigned later no longer counts as an assignee (the row is deleted, S018);
   a labour row stays.
4. **Every intensity and state counts**, the open ones too (Q6.1 a: "the vendor as assignee or on
   a labour row"). A ticket closed as *Not a fault* counts as a call (the vendor came); its times
   are `None` (`ticket_times`), shown "—".
5. **Inactive contract:** listed the same way (the page is read-only history).
6. **Order:** `t.occurred_at` descending, then `t.id` descending (newest first, as the ticket
   list). **No paging:** a contract's calls in one period are few (the plant's vendors: a handful
   a year each); all are listed.

**The queries** (`_call_rows`), all plain reads, no N+1:
1. The lines and their machines: `SELECT ce.equipment_id, e.level, COALESCE(gp.id, p.id, e.id) AS
   machine_id FROM contract_equipment ce JOIN equipment e ON e.id = ce.equipment_id LEFT JOIN
   equipment p ON p.id = e.parent_id LEFT JOIN equipment gp ON gp.id = p.parent_id WHERE
   ce.contract_id = %s` (`uq_contract_equipment`, then primary keys). The root of the tree is the
   machine (`NODE_JOINS` takes the root's unit the same way). From it: `<machines>` (the distinct
   `machine_id`s) and `<part lines>` (the line nodes whose `level` is not `equipment`), plus, for
   a line on a component-unit, its current components (`SELECT id FROM equipment WHERE parent_id
   IN (…)`, one more query only when such a line exists). No line → no calls, no further query.
2. The tickets, one query over `tickets t JOIN equipment m ON m.id = t.equipment_id LEFT JOIN
   equipment c ON c.id = t.component_id`: `(t.equipment_id IN (<machines>) OR t.component_id IN
   (<part lines and their components>))` (the second `IN` left out when empty), the period on
   `t.occurred_at`, `EXISTS` a line of the contract with `ce.equipment_id IN (t.equipment_id,
   t.component_id, c.parent_id)`, `EXISTS` an assignee or a labour row whose person has
   `p.vendor_id = ct.vendor_id`, and `<visible>` (§ 5.5). Indexes: `ix_tickets_equipment_state`
   and `ix_tickets_component_state` for the two `IN`s; the `ticket_assignees` primary key
   (`ticket_id`, `person_id`), `ix_ticket_labour_ticket` and `uq_contract_equipment` for the
   `EXISTS`. **Cost of the widening (BR1-03):** an `OR` over two indexes may become an index merge
   or a scan of the period's tickets; the coder checks with `EXPLAIN` (*to verify*) and, if it
   scans, writes the two `IN`s as a `UNION` of two selects (same result), noting which in the impl
   report.

   **What the widening still gets wrong (accepted, § 9):** a ticket on a component under a
   covered component-unit raised before that component **left** the component-unit (its current
   `c.parent_id` no longer names the line), and a ticket raised on a component **before** it moved
   into a covered component-unit (its current parent now names the line). Both follow from the
   tree being read as it is now (no history of `parent_id`); rare at the plant.
3. Their events: `tickets.events_by_ticket(cur, ids)` (one query, `ix_ticket_events_ticket`).
4. The vendor's people: `_vendor_people(cur, ids, vendor_id)`, one query over the `UNION` of the
   assignee and labour rows of those tickets joined to `people` with `p.vendor_id = %s`, by name →
   `{ticket_id: [{id, name}]}`, each person once per ticket.

Pool connections are autocommit (`backend/db_helpers.py`): each query reads its own snapshot. A
ticket changed between queries 2 and 4 can show one stale figure for one request; nothing is
written.

### 5.2 The figures of one call

`call_figures(state, not_a_fault, events, now)` (pure) → `{downtime_minutes,
vendor_waiting_minutes, back_in_service_at}`, from one call of `ticket_times(events, now)` and one
of `latest_restoration(state, not_a_fault, events)`:
- `downtime_minutes`: `ticket_times(…)["downtime_minutes"]` (EN 13306 time to restoration: while
  critical and not back in service; an open breakdown counts to `now`, as the ticket page does).
- `vendor_waiting_minutes`: `(ticket_times(…)["waiting_by_reason"] or {}).get("vendor")`, or `None`
  when the ticket never waited for the vendor while critical. A defect waiting for the vendor is
  backlog, not delay (S019's rule, kept: `ticket_times` docstring).
- `back_in_service_at`: `latest_restoration(…)`; `None` while open or sent back, and for *Not a
  fault*.

`now` is `datetime.now(IST).replace(tzinfo=None)`, as `tickets._now`.

### 5.3 The card

`BreakdownCallsCard.vue`, `props: { contract }`, loads `GET /api/contracts/<id>/calls` itself, as
S082's card loads its own list.

- **Shown** only when `userPermissions` (`frontend/src/stores/auth.js`) holds `ticket:read`
  (§ 5.5). Otherwise nothing is drawn: no empty card.
- **Header:** *Breakdown calls*, with the count as a badge.
- **The warning** (§ 5.4), first, as `alert alert-warning` with `fa-triangle-exclamation`.
- **One `list-group-item` per call:**
  1. the serial, a link to `/tickets/<id>`; the `IntensityBadge`; the state (`stateLabel` from
     `ticketLabels.js`, which needs `state`, `intensity` and `overdue`);
  2. "CMP001 — Screw compressor 1", and " › M001 — Motor" when the ticket is on a part;
  3. "Happened 12-04-2026 10:30 · back in service 12-04-2026 16:00" (`formatDateTime`); "· not back
     in service yet" while open; *Not a fault* as a badge instead, for such a ticket;
  4. "Down 5 h 30 min · waited on the vendor 2 h" (`minutesText`); a part that is `null` or 0 is
     left out, and the line too when both are (a defect never down);
  5. "By: Ravi, Atlas Copco service" — the vendor's people only, by name (BR1-05).
- **The total line** (`callsTotalLine(total)`), under the list: "3 calls · down 5 h 20 min ·
  waited on the vendor 2 h"; "1 call · no downtime"; the waiting part left out when 0.
- **The used line** (`callsUsedLine(used)`), under the total, only when the answer's `used` is not
  `null`: "3 of 4 calls used this period." (`text-secondary`); "5 of 4 calls used — more than
  agreed." (`text-danger`) when `over`; for a period longer than `CALLS_USED_MAX_DAYS`: "5 calls in
  this period · 4 a year agreed."
- **Not complete** (`complete` false, § 5.5), with calls listed: one line under the list, "Only
  the calls on machines of your units are listed." and no used line.
- **Not complete and no call listed** (BR1-02): only "No calls on machines of your units. Only
  those are listed here." (one line; no "yet", no used line).
- **Empty** (`complete` true, no call): "No breakdown calls on this contract yet. A call is a
  ticket that a Team record of Atlas Copco is assigned to or logs labour on." (scope B: says what
  makes a row appear).
- **Errors:** "Breakdown calls could not be loaded: <message>" in the card, as S082's card.
- **Place:** last on the page, after S083's *Documents* card (S083 § 5.7: "after the *Machines
  covered* card, before any later card").
- **Disabled controls:** none. **Destructive controls:** none.

`calls_used(count, per_year, from_date, to_date, complete)` (pure) → `None` when `complete` is
false, or `per_year` is `None` (no number agreed; S080: the tick off forces `NULL`); else
`{count, agreed: per_year, over: count > per_year, per_year_only: days > CALLS_USED_MAX_DAYS}` with
`days = (to_date − from_date).days + 1` and `CALLS_USED_MAX_DAYS = 366` (a leap year's contract
still compares). `per_year_only` true → the third text above.

`calls_total(calls)` (pure) → `{count, downtime_minutes, vendor_waiting_minutes}`: the sums of the
known values (`None` skipped), each 0 when none is known.

### 5.4 The two warnings

`_vendor_reach(cur, vendor_id, site_id)` → `(linked_count, assignable_count)`, one query:
`SELECT COUNT(DISTINCT p.id) AS linked, COUNT(DISTINCT CASE WHEN ms.role IN (…ASSIGNABLE_ROLES)
THEN p.id END) AS assignable FROM people p LEFT JOIN memberships ms ON ms.person_id = p.id AND
ms.site_id = %s WHERE p.vendor_id = %s AND p.active = 1` (`ix_people_vendor`; the memberships
primary key `(person_id, site_id)`). Active people only: an inactive person cannot be assigned or
named on a new labour row.

`vendor_warning(linked_count, assignable_count)` (pure) → `"no_linked"` when `linked_count` is 0;
`"no_assignable"` when `assignable_count` is 0; else `None`.

- **Computed only** for an active contract whose `contract_status(…).kind` is not `ended`
  (`upcoming`, `in_force`, `ending`); otherwise `warning` is `None`: an ended contract needs no
  more calls.
- **Texts** (scope B), with the vendor's name and the contract's site code:
  - `no_linked`: "No Team record is linked to Atlas Copco. Link the vendor's technician, or a
    record such as 'Atlas Copco service', in Masters › Team."
  - `no_assignable`: "No Team record of Atlas Copco can be assigned at SMTW. Give one a
    Technician role there in Masters › Team." (BR1-04: one text for everyone, naming the action;
    the floor knows whom to tell).
- **Fact** (`ASSIGNABLE_ROLES`, `ASSIGNEE_AT_SITE`, `tickets.person_at_site`): an assignee needs
  a Technician, Engineer or Manager role at the site; a labour row only a membership. So linked
  people with only an Operator row give the second warning, though their labour rows still count.
  An engineer gives the Technician role (`people:assign_technicians`, S011 A1).
- The warning shows above the list, also when the list has calls.

### 5.5 Who reads the calls, and which rows

| Route or control | Key | Where checked |
|---|---|---|
| `GET /api/contracts/<id>/calls` | `require_perm("contract:read_basic")` and `require_perm("ticket:read")` | 403 when either is held nowhere; then S080's rule: missing, or `contract:read_basic` not held at the contract's site (`has_perm_at`) → 404 "Not found" |
| each row | `ticket:read`, by the ticket predicate | `unit_access_condition(cur, "ticket:read", "t.unit_id", "m.unit_id")` (`backend/equipment.py`), the predicate `tickets._visible_condition` uses: the ticket's own unit or its machine's current unit is one where the user holds `ticket:read`. `None` (no such unit) → no rows, no ticket query |
| `complete` | `ticket:read` at every active unit of the contract's site | `accessible_unit_ids(cur, "ticket:read")` is `None`, or holds every id of `SELECT id FROM units WHERE site_id = %s AND active = 1` |
| the card | `ticket:read` held somewhere | `userPermissions` (screen only) |

- **The rule: the card never shows a ticket the reader could not open.** Each row passes the same
  predicate as `GET /api/tickets/<id>`, so every serial link opens. The total sums the rows shown.
- **No hidden count is sent.** The answer never says how many calls the reader cannot see, as
  the equipment list reads no ticket fact for a unit without `ticket:read`
  (`equipment._ticket_light_column`). So "3 of 4 calls used" is shown only when `complete` is true:
  the reader's units cover the whole site, so the count is the contract's count. A manager has
  "all units" of the site (S011); an engineer or a technician with some units sees the note
  instead (§ 5.3).
- **Holders** (`backend/config_rbac.py`): `ticket:read` is `("maint_operator", "it_admin")`, so the
  operator, the maintenance ladder, the supervisor and IT admin; the storekeeper holds
  `contract:read_basic` (`("*",)`) but no `ticket:read`, so the storekeeper sees the contract page
  without the card. Admin by the bypass.
- **A residual, accepted:** `complete` looks at the contract's site only. A ticket raised at
  another site after a covered machine moved there (S081: "Now at BRICKS.") is listed to a reader
  who can open it. Rare; the page shows the move. Also (BR1-10): `accessible_unit_ids` and the
  ticket predicate keep active units only, so a ticket on a unit deactivated later is listed to
  admin only and is missing from a "complete" count.
- **No new key** (`test_role_matrix` unchanged). No identity → 401 by `require_auth`, never admin.
  Nothing is written. The rows name Team records, as the ticket does; no login, email or phone.

### 5.6 The contract line on the ticket page

`TicketContractLine.vue`, `props: { ticket }`.

- **Fetched** when the ticket is open (`ticket.state !== "closed"`) and `ticket.permissions` (the
  keys at the ticket's site, `permissions_at_site`) holds `contract:read_basic`.
- **Source:** S082's `GET /api/contracts/for-equipment/<node_id>` with `node_id` =
  `ticket.component?.id ?? ticket.machine.id`. S082's route already gives exactly the contracts on
  the node, its parent or its grandparent, each kept only where the user holds
  `contract:read_basic` at the contract's site, built through `_contract_out` (no price, no cost
  note). The line keeps the items whose `status.kind` is not `ended` (the route also sends
  contracts ended in the last 90 days, for the machine's card). No new route.
- **Each item** (one `div` per contract), small text, `fa-file-signature`:
  - `ticketContractLine(item)`: S082's `cardHeadline(item)`, then " · response " and S081's
    `responseText(item.response_hours)` when not `null`, then " · breakdown calls included" when
    `covers_breakdown_calls`. Example: "Under AMC with Atlas Copco until 31-03-2027 · response 24
    hours · breakdown calls included". The headline is a link to `/contracts/<id>` (every item's
    reader holds `contract:read_basic` at its site, the page's gate).
  - **The D9 warning** (S082's rule, the same text): when `showsDoNotRepair(item)` (S082's helper),
    an `alert alert-warning py-2` with `fa-triangle-exclamation` and S082's `DO_NOT_REPAIR` = "Do not
    repair. Call the engineer; the vendor repairs this machine." Shown to every reader of the line,
    as on S082's card. Ended items are dropped with S082's `isEnded(item)` (BS1-01).
  - The item's id is `contract_id` (the card route's key; BS1-02), so the link is
    `/contracts/<contract_id>`.
- **Nothing to show** (no item, an error, a 403 or 404): nothing drawn; the ticket page works
  without the line. A 404 comes when the ticket is visible through its old unit but its machine
  now stands outside the user's `equipment:read` units; accepted.
- **Place:** between the plan line and the action bar, full width, on every width. The technician
  reads "Do not repair" before tapping *Start*; the engineer reads the vendor before *Assign*.
- **Reload:** the line loads once per ticket id (`watch` on `ticket.id` and the open state), not
  after every write that replaces the page's copy.

### 5.7 The vendor in the people picker

- **API:** `tickets.people_at_site` reads `LEFT JOIN vendors v ON v.id = p.vendor_id` and adds
  `vendor_name` (`null` when the person has no vendor) to each item of `GET /api/tickets/people`.
  An inactive vendor's name is still shown (the person still works for it until relinked).
  `improvements.py`'s two callers map the items to `{id, name}` and are unchanged.
- **Screen** (`PersonPicker.vue`): each button reads "Name · Role" as today, then " · Atlas Copco"
  when `vendor_name` is set; the picked line adds the vendor after the role the same way. Used by
  every picker on a ticket (assign, labour, back in service, the raise's *who did the work*): the
  vendor helps in each.
- **Filter:** `groupPeople`'s `filter` matches the name or `vendor_name`, without regard to case,
  so "atlas" finds Atlas Copco's people. A `vendor_name` that is `null` or absent (the existing
  test fixtures have none) matches nothing (BR1-06).
- No group changes: the vendor's people stay in *Maintenance* or *Others at the site* by their
  role, as today.

### 5.8 Locks

None. The calls route, the for-equipment route and the people picker read plainly; S086 writes
nothing. The LOCK ORDER notes (`tickets.py`, `masters.py`, `improvements.py`, `procedures.py`,
`contracts.py`, and the contract sentences in `equipment.py`, `documents.py` and `alerts.py`,
S083–S084; BS1-06) are unchanged; `contracts.py`'s docstring says the calls route takes no lock.

### 5.9 The database down

Each route goes through `get_db()`: 503 (`DBUnavailable`). The card shows its error text; the
ticket line draws nothing; the picker shows the ticket page's existing "The people or symptom lists
could not be loaded: …".

## 6. API

| Route | Decorator | Then | Answer |
|---|---|---|---|
| `GET /api/contracts/<int:contract_id>/calls` (new) | `contract:read_basic`, `ticket:read` | § 5.5 | 200 below; 403, 404, 503 |
| `GET /api/contracts/for-equipment/<int:node_id>` (S082) | unchanged | unchanged | unchanged; the ticket page is a second reader |
| `GET /api/tickets/people` (S017, S018) | unchanged | unchanged | each item adds `vendor_name` |

**The calls answer:**

```
{"calls": [{"id", "serial", "state", "intensity", "is_breakdown", "overdue", "not_a_fault",
            "occurred_at", "back_in_service_at", "machine": {"id", "code", "name"},
            "component": {"id", "code", "name"} | null, "downtime_minutes",
            "vendor_waiting_minutes", "vendor_people": [{"id", "name"}]}],
 "total": {"count", "downtime_minutes", "vendor_waiting_minutes"}, "complete": bool,
 "used": {"count", "agreed", "over", "per_year_only"} | null,
 "warning": "no_linked" | "no_assignable" | null, "vendor_name", "site_code"}
```

`overdue` by `tickets_core.is_overdue(state, planned_date, today)`, `is_breakdown` by
`tickets_core.is_breakdown(intensity)` (kept beside `intensity`, as the improvement page sends
both, for a later split of the total by breakdowns; the card draws `IntensityBadge` from
`intensity`, BR1-12), datetimes as `row_to_dict` gives them. No price, cost note
or call-out number: no contract field beyond the vendor's name and site code. `used.count` is
`total.count`.

## 7. Design decisions

C1–C9 are this step's; D1–D11 the roadmap's (R02 § The feature); "S08N Bn" those steps'.

- **C1. Its own route and card, not a part of the contract detail.** The calls need four queries
  and the ticket key; the detail is read by every reader, the storekeeper too. A card that loads
  itself fails alone, as S082's. Rejected: `calls` in `GET /api/contracts/<id>` (four queries on
  every load, also for readers the card skips).
- **C2. Rows only from tickets the reader can open; no hidden count.** The ticket predicate is the
  rule every ticket read uses (S017 § 5.3). Rejected: (a) every call listed to every
  `contract:read_basic` holder (shows tickets of units the reader may not see, against ISO 27001
  A.8.3 and S017's predicate); (b) the rows the reader can open plus "N more you cannot open" (a
  ticket fact for units without `ticket:read`, which `equipment._ticket_light_column` avoids).
- **C3. "3 of 4 calls used" only for a reader who sees the whole site.** A partial count next to
  the agreed number would look like a fact about the contract. Rejected: the partial count with a
  note (easy to misread on a phone; flagged for KLA at gate B); the full count from a
  second, unfiltered query (C2 (b)'s leak).
- **C4. The lines first, then the tickets by `equipment_id` or `component_id`.** It lets the
  ticket query use `ix_tickets_equipment_state` and `ix_tickets_component_state` (the second `IN`
  is BR1-03's widening, so a covered part's tickets count wherever the part stood when raised;
  flagged for KLA at gate B); matching on `contract_equipment` alone would scan the tickets of
  the period with no index on `occurred_at`. Rejected: one statement joining `contract_equipment`
  to `tickets` on the three columns (no usable index); a new index on `tickets.occurred_at` (a
  migration for a table of a few thousand rows a year).
- **C5. Downtime and waiting from `ticket_times`, through a moved `events_by_ticket`.** One rule
  for the figures, as the improvement page does (S069). Moving `improvements._events_by_ticket`
  to `tickets.py` lets contracts.py use it without importing improvements.py and without a copy.
  Rejected: a copy in contracts.py (DRY); importing improvements.py's private helper.
- **C6. The ticket line on open tickets only, from S082's route.** On a closed ticket the line
  would show today's contract, not the one in force then, and there is nothing left to assign.
  S082's route gives the same contracts, keys and D9 tick as the machine's card, so the two screens
  cannot disagree. Rejected: a new `for-ticket` route (a second copy of S082's rule); the line in
  the ticket detail (tickets.py would import contracts.py, which imports tickets.py after S086).
- **C7. The D9 warning on the ticket line for every reader,** as on S082's card; the ticket is
  where the repair starts. Rejected: technicians only (an engineer can start the work too).
- **C8. Warnings in the calls card, for active contracts not ended;** an ended contract needs no
  more calls. Rejected: in the terms card (one more query on the detail, C1).
- **C9. A *Not a fault* ticket counts as a call:** the vendor came. Rejected: leaving it out (the
  used count would miss a visit the vendor counts). § 9 Q2: flagged for KLA at gate B.

## 8. Tests and acceptance

### 8.1 Migration

None. `tooling\schema-docs.bat check` exits 0 unchanged.

### 8.2 Backend

**Core** (`backend/tests/test_contracts_core.py`, from S080), pure, fixed times:
- `test_call_figures_downtime_and_vendor_waiting`: events raised critical → scheduled with reason
  `vendor` for 120 min → started → back in service: `downtime_minutes` as `ticket_times` gives,
  `vendor_waiting_minutes` 120, `back_in_service_at` the restore time.
- `test_call_figures_open_breakdown_runs_to_now`; `test_call_figures_waiting_for_parts_is_not_vendor`
  (`vendor_waiting_minutes` `None`); `test_call_figures_defect_waiting_is_not_delay` (a defect
  scheduled with `vendor`: `None`); `test_call_figures_not_a_fault` (all `None`).
- `test_calls_total_sums_known_values` (`None` skipped; no call → zeros, count 0).
- `test_calls_used`: within a year (3 of 4, `over` false); 5 of 4 (`over` true); `per_year` `None`
  → `None`; `complete` false → `None`; a 366-day period still compares; a 367-day period
  `per_year_only` true; a one-day contract compares.
- `test_vendor_warning`: (0, 0) `no_linked`; (2, 0) `no_assignable`; (2, 1) `None`.

**Route** (`backend/tests/test_contract_calls_api.py`, new). Each test makes its own site, unit,
vendor, contract and machine (`make_site`, `make_unit`, `make_vendor`, `make_equipment`,
`make_person`, `give_site_role`, `user_at_sites`, `user_with_units`, `make_ticket`, `uniq`);
contracts by `POST /api/contracts`, lines by S081's `POST /api/contracts/<id>/equipment`, links by
`PUT /api/masters/people/<id>` with `{employment: "contractor", vendor_id}`, assignees and labour by
the ticket routes (S018). The session database gives no contract, so each test's state is its own.
- `test_an_assignee_of_the_vendor_makes_a_call` (the row's fields, `vendor_people`, `total.count`
  1); `test_a_labour_row_alone_makes_a_call` (a linked person with an Operator membership only);
  `test_an_in_house_ticket_is_not_a_call`; `test_another_vendors_person_is_not_a_call`.
- `test_one_row_for_assignee_and_labour_and_two_people` — no duplicate row; each person once.
- `test_tickets_on_parts_of_a_covered_machine_count` (component-unit and component);
  `test_a_line_on_a_component_unit_counts_its_components_not_the_machine`.
- `test_the_period_edges` — on a contract whose period ends yesterday (a raise refuses a future
  time, `tickets_core.EVENT_TIME_FUTURE`; BR1-07): 00:00 on From and 23:59 on To count; 23:59 the
  day before From and 00:00 today do not.
- `test_a_covered_part_moved_after_its_ticket_still_counts` (BR1-03) — a line on a component-unit
  of machine A; a vendor ticket on it; the component-unit moved to machine B (`PUT` with a new
  `parent_id`): the call is listed (by `component_id`); a ticket raised on it after the move counts
  too. `test_a_covered_machine_keeps_the_ticket_of_a_part_that_left` — a line on machine A; a
  ticket on its component-unit; the component-unit moved to B: still a call of A's contract.
  `test_a_component_that_left_a_covered_component_unit_drops_out` — the accepted residual (§ 5.1),
  asserted so a later change shows.
- `test_the_current_link_counts` (relinked to another vendor, the call moves; Q9.5 a);
  `test_an_inactive_linked_person_still_counts`; `test_an_unassigned_vendor_person_no_longer_counts`
  (no labour row); `test_newest_first`.
- `test_rows_follow_ticket_access` — a technician with one of two units: the call on the other
  unit is absent, `complete` false, `used` `null`; the manager (all units): both, `complete` true.
- `test_used_when_the_number_is_agreed` — `covers_breakdown_calls` and 4 a year: `used` `{count: 1,
  agreed: 4, over: false, per_year_only: false}`; without a number: `null`.
- `test_the_storekeeper_gets_403` (holds `contract:read_basic`, not `ticket:read`).
- `test_a_contract_of_another_site_is_404` (a user with roles at site A only); `test_unknown_is_404`.
- `test_warnings` — no linked person: `no_linked`; a linked person with an Operator row only:
  `no_assignable`; with a Technician row: `None`; an inactive linked person only: `no_linked`; an
  ended contract: `None`; an inactive contract: `None`.
- `test_no_machines_no_calls` — a contract with no line: empty `calls`, zeros.
- `test_no_price_or_callout_in_the_answer` — the keys of the answer as § 6, for the manager too.
- `test_database_down_is_503` (`db_down`).

**Picker** (`backend/tests/test_tickets_api.py`):
- `TestPickers::test_people_show_their_vendor` (new) — a contractor linked to a vendor has
  `vendor_name`; a direct employee `null`; an inactive vendor's name still shown.

**Frontend unit:**
- `frontend/tests/contractLabels.test.js`: `callsTotalLine` ("3 calls · down 5 h 20 min · waited
  on the vendor 2 h", "1 call · no downtime", the waiting part left out at 0); `callsUsedLine`
  (the three texts; `null` → `null`); `ticketContractLine` (with and without the response time,
  with and without the breakdown-calls part). `DO_NOT_REPAIR` is S082's and already tested.
- `frontend/tests/ticketLabels.test.js` `groupPeople`: "atlas" finds a person by `vendor_name`; a
  person with `vendor_name` `null` or absent is matched by name only.

### 8.3 Existing tests that break or run again

- `backend/tests/test_tickets_api.py::TestPickers::test_people_of_the_site_with_trades_and_role`
  asserts the whole item; it gains `"vendor_name": None`. Changed by the coder.
- Green, no change: `backend/tests/test_ticket_work_api.py::TestPickersByTicket::test_people_and_modes_after_a_cross_site_move`
  (reads `assignable` only); the improvement tests that read downtime through `_linked_tickets`
  (`backend/tests/test_improvement_close_api.py` and the other `test_improvement*_api.py`, after
  the move of `events_by_ticket`); `backend/tests/test_rbac.py` (`test_role_matrix`, no new key);
  `test_contracts_api.py` and every `test_contract*_api.py` of S080–S085 (routes unchanged; BR1-09).
- **Browser:** `frontend/e2e/tickets-work.spec.js`, `frontend/e2e/tickets-raise.spec.js`,
  `frontend/e2e/tickets-parts.spec.js`, `frontend/e2e/improvements.spec.js` use the picker or
  `/api/tickets/people`; the seed people have no vendor, so the text is unchanged; re-run.
  `frontend/e2e/contracts.spec.js` (S080–S085): the contract page gains a card at its end; S082's
  card is unchanged; re-run. No shared file changes (settings: *Shared code*: `FormModal.vue`,
  `useFormModal.js`, `api.js`, the router, the auth store and `e2e/support/` are untouched).

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

In S080's spec, with its helpers and S081's line set-up by API; tickets by `raiseByApi` and
`moveByApi` (`e2e/support/tickets.js`), assignees by the API as the engineer. Each test makes its
own machine and vendor; the period around today. The ticket-page tests sit here too, so
`e2e/support/` does not change. Untagged unless marked.

**Team records (BR1-01):** each S086 test creates its own Team records by API as IT admin
(`POST /api/masters/people` with `employment: "contractor"` and `vendor_id`, and a Technician or
Operator row at SMTW through `PUT /api/masters/people/<id>/sites/<site_id>` with `{role, all_units, unit_ids}`, the `give_site_role` call). No test links, relinks or changes a seed
person: other specs in the same lane read the seed people's picker text unchanged (§ 8.3).

- **important** `S086: the contract page lists the vendor's breakdown call with downtime and the
  total line` — a linked Team record (Technician at SMTW) assigned to a breakdown ticket on the
  covered machine, put on hold with the reason *vendor*, then back in service, with back-dated
  times (`istLocal`) so the minutes are not 0: the row shows the serial (a link that opens the
  ticket), the machine, "waited on the vendor", the person; the total line "1 call · down …".
- **important** `S086: a ticket worked only by in-house people is not a breakdown call` — the
  same machine, an in-house technician assigned: the card shows only the vendor's ticket.
- **important** `S086: a call on a part of the covered machine is listed with the part`.
- `S086: 1 of 2 calls used shows when the contract agrees a number` — and "2 of 1 calls used —
  more than agreed." on a second contract with 1.
- **important** `S086: the contract page warns when no Team record is linked to the vendor` — a
  new vendor with no people: the first warning; after linking one with an Operator row only, the
  second warning; with a Technician row, no warning.
- `S086: the storekeeper sees the contract page without the Breakdown calls card`.
- `S086: the operator sees only the calls of their units and no used line` — the seed operator
  holds MCC2 only (`tooling/e2e/seed_e2e.py`): a call on an MCC2 machine shows, one on an MCC1
  machine of the same contract does not, and the note "Only the calls on machines of your units
  are listed." shows instead of the used line. On a second contract whose only call is on an MCC1
  machine, the card shows only "No calls on machines of your units. Only those are listed here."
  (BR1-02, BR1-13).
- **important** `S086: an open ticket on a covered machine shows the contract line and Do not
  repair` — the line's text, the link to the contract, the warning; the line comes before the
  action bar in DOM order (`compareDocumentPosition`, not geometry; BR1-08); the same ticket
  closed (by API) shows no line.
- `S086: the assignee picker shows the vendor beside a linked person and finds them by the
  vendor's name` — *Assign*, type the vendor's name: the button "<name> · Technician · <vendor>".
  The dialog is checked with `expectDialogFits`.
- `S086: the Breakdown calls card fits a phone with no sideways scroll` (`@device`) —
  `expectNoSidewaysScroll` on a contract page with two calls and a warning.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/tickets-work.spec.js e2e/tickets-raise.spec.js e2e/screens.spec.js`; the whole suite at Normal
once at the end.

### 8.5 On a real device

None. Every check is a screen, a text or a flow that a browser engine judges. S082's device row
(the "Do not repair" warning read in the shop's light) covers the same warning on the ticket page.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; the targeted and the Normal browser runs green.
- By screen: on "Atlas Copco AMC 2026–27" the engineer sees each ticket Atlas Copco's people
  worked on the two compressors since 01-04-2026 and "3 of 4 calls used this period."; on a
  compressor's open ticket the technician sees the contract line and "Do not repair" above *Start*.
- **§ SMTW-Review**, a new point: "**Breakdown calls (S086)**: the calls route
  (`/api/contracts/<id>/calls`) filters its rows by the ticket predicate
  (`unit_access_condition(cur, "ticket:read", …)`), sends no count of tickets the reader cannot
  open, and shows *N of M calls used* only when the reader holds `ticket:read` at every unit of the
  contract's site. Its figures come from `tickets_core.ticket_times`; a calls or vendor report
  (R02.8) uses the same rule and the same function."

## 9. Open questions and assumptions

- **Q1. Split the step?** (a) One step — **recommended**: 18 files, read-only, one concern (the
  vendor's work on tickets, seen from both ends), no migration, no lock. (b) Two steps: S086 the
  calls card and warnings (backend route, core, the card, about 11 files); a later step the ticket
  line and the picker (about 8 files). The cut is clean (§ 5.6 and § 5.7 depend on nothing in
  § 5.1–§ 5.4), but each half is small.
- **Q2. A *Not a fault* ticket: a call?** (a) Yes, with "—" for its times — **recommended** (C9:
  the vendor came, and the vendor counts the visit). (b) No: only real faults count against the
  agreed number. **(a) taken under the delegation of 30-10-2026; flagged for KLA at gate B.**
- **C3, the used line for a partial reader:** hidden, with the note — **taken as recommended under
  the delegation; flagged for KLA at gate B.**
- **BR1-03, a covered part's tickets wherever the part stood when raised:** query 2 widened with
  `t.component_id IN (<part lines and their components>)` (§ 5.1) — **decided under the
  delegation; flagged for KLA at gate B.** Its cost: one more `IN`, a possible index merge or a
  `UNION` (§ 5.1). What it still gets wrong (accepted): a component's tickets follow its
  **current** parent, so a component that left a covered component-unit drops out, and one that
  moved in brings its earlier tickets.
- **Q3. The call-out number on the ticket line?** (a) No — **recommended**: the roadmap names the
  line's parts, and the machine's card (S082) has it. (b) Yes, for `contract:read` holders, as
  S082's `callLine`; one tap less at a breakdown.
- **A1.** "Raised within the period" reads `tickets.occurred_at` (the time it happened), not
  `created_at` (§ 5.1 rule 2). The ticket list and page show `occurred_at` as *When it happened*.
- **A2.** Every intensity counts (Q6.1 a names none); the severity badge shows which were
  breakdowns.
- **A3.** No paging (§ 5.1 rule 6). If a contract ever lists more than about a hundred calls, a
  later step adds it.
- **A4.** The S080–S085 names are as their briefs state them (§ 3); the staleness review checks
  them, in particular `_CONTRACT_SELECT`, `_contract_row`, S082's route path and item
  keys (`status.kind`, `only_vendor_repairs`, `covers_breakdown_calls`, `response_hours`),
  `cardHeadline`, and where S083 and S085 put their parts of `ContractView.vue`.
- **Roadmap points corrected here:** (1) R02.6's "a Technician row" to be assigned: the code
  accepts Technician, Engineer or Manager (`ASSIGNABLE_ROLES`); the second warning counts all
  three (§ 5.4). (2) R02.6's Team-dialog warning on a vendor change is S079's; S086 does not touch
  the Team dialog. (3) R02 § What exists cites `tickets_core.py:320` for `WAITING_REASONS`; it is
  at line 318 (cited here by name).
- **Standards *to verify*:** EN 13306's clause numbers; ISO 14224's table; ISO 55001:2024's clause
  for outsourcing. **No defining question** before review: Q1–Q3 have a recommended option.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer | What changed |
|---|---|---|
| BR1-01 (minor) | Accepted | § 8.4: each S086 test creates its own Team records by API as IT admin; no seed person is linked or changed. |
| BR1-02 (minor) | Accepted | § 5.3: a partial reader with no visible call sees only "No calls on machines of your units. Only those are listed here."; the *Empty* text is for `complete` true; § 8.4 operator test covers it. |
| BR1-03 (minor) | Accepted, option (b), decided under the delegation; flagged for KLA at gate B | § 5.1: "machine at raise" wording; query 1 gives the part lines and a component-unit line's components; query 2 adds `t.component_id IN (…)` (`ix_tickets_component_state`), with its cost (index merge or `UNION`) and the residual it still gets wrong; C4, § 9; § 8.2 three tests for moved parts. |
| BR1-04 (minor) | Accepted | § 5.4: `no_assignable` names the action: "… Give one a Technician role there in Masters › Team." |
| BR1-05…BR1-13 (nits) | Accepted as recommended | "By: Ravi, Atlas Copco service"; `vendor_name` `null` or absent; period edges on a contract ending yesterday; DOM order, not geometry, in the ticket-line test; every `test_contract*_api.py`; the inactive-unit residual in § 5.5; the import check in § 3; `is_breakdown` kept and why; the operator test asserts the one line shown. |

Q2 and C3 taken as recommended under the delegation; flagged for KLA at gate B (§ 9).

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 31-10-2026

Sections changed: header, § 1 Out of scope, § 3 (Backend, Frontend, file count), § 5.6, § 5.8, § 8.2, § 8.3, § 8.4.

| Finding | Answer |
|---|---|
| BS1-01 (minor) S082 already exports `DO_NOT_REPAIR` | Accepted: the ticket line reuses `DO_NOT_REPAIR`, `showsDoNotRepair` and `isEnded`; the `UnderContractCard.vue` bullet is dropped (17 code and test files); § 1, § 5.6, § 8.2, § 8.3 reworded. |
| BS1-02 … BS1-06 (nits) | Accepted: the item key `contract_id` (§ 5.6); only `unit_access_condition` is a new import (§ 3); the `contracts_core` import rule (§ 3); the site-row route named (§ 8.4); the LOCK ORDER notes in `equipment.py`, `documents.py` and `alerts.py` listed as unchanged (§ 5.8). The coder re-reads `_CONTRACT_COLUMNS` and `_detail` after S085 is coded. |
