```
Step: S086 — Breakdown calls on the contract
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080 (partial: `backend/contracts.py`, `contracts_core.py`, `contractLabels.js`, `contracts.spec.js` as coded so far; S081–S085 not yet in the tree)

**Verdict: no blocker or major finding is open.** 0 blocker, 0 major, 4 minor, 9 nits. Facts file
`scratch/brief-facts-S086.md` read first; the code opened only where it left a question (the
role ladder, the ticket predicate, the picker, the ticket page, the seed, part moves).

**For KLA at gate B** (gate A is delegated tonight): the brief's Q2 (a *Not a fault* ticket
counts against the agreed number of calls) and C3 (the "N of M calls used" line only for a reader
who holds `ticket:read` at every unit of the site) are business judgements the brief takes as
recommended; neither of my findings changes them. BR1-03 below adds one residual KLA should know.

## Findings

### BR1-01 — minor — The browser tests must make their own Team records, never relink a seed person

**Problem.** § 8.4 says "a linked Team record (Technician at SMTW)" and "*Assign*, type the
vendor's name: the button `<name> · Technician · <vendor>`", without saying where that record comes
from. The seed people (`tooling/e2e/seed_e2e.py`, `Kannan (technician)`, `Ravi (technician)`) are
the obvious shortcut.

**Why it matters.** Lanes group spec files on one database (`vel_yantra_lane<n>_e2e`). If
`contracts.spec.js` links a seed technician to a vendor, every picker button for that person in
`tickets-work.spec.js`, `tickets-parts.spec.js` and `improvements.spec.js` in the same lane reads
"Kannan (technician) · Technician · <vendor>" for the rest of the run; § 8.3's "the seed people have
no vendor, so the text is unchanged" then no longer holds. S079's own warning on a link change says
why relinking is the wrong habit.

**Options.** (a) **Recommended:** § 8.4 states that each S086 test creates its own Team record by
API as IT admin (`POST /api/masters/people` with `employment: "contractor"`, `vendor_id`, and a
Technician row at SMTW through the site-roles route), and never changes a seed person. (b) Keep the
text and rely on the coder noticing. Not recommended.

### BR1-02 — minor — A partial reader with no visible call reads "No breakdown calls on this contract yet"

**Problem.** § 5.3 gives two states that can hold at once: *Empty* ("No breakdown calls on this
contract yet. A call is a ticket …") and *Not complete* ("Only the calls on machines of your units
are listed."). An operator of MCC2 opening a contract whose calls are all on MCC1 machines gets
`calls: []`, `complete: false`, and by the brief's text sees both lines.

**Why it matters.** "No breakdown calls on this contract yet" is then false, and the two sentences
contradict each other on one card. Scope B asks that a message say what the user sees.

**Options.** (a) **Recommended:** when `complete` is false and the list is empty, show only "No
calls on machines of your units. Only those are listed here." (one line, no "yet"); the *Empty*
text is for `complete` true. State it in § 5.3 and add it to the operator's e2e test (§ 8.4): a
contract with calls on MCC1 only. (b) Hide the card for a partial reader with no row. Hides the
fact that the card exists; not recommended.

### BR1-03 — minor — A covered part that moved to another machine loses its earlier calls

**Problem.** § 5.1 says "The ticket's current machine and component count", but `tickets.equipment_id`
is the machine at raise and is never rewritten (`backend/equipment.py` has no `UPDATE tickets`; a
part may change its parent, `equipment_core.py:199` `moved_parent`). Query 1 maps a line on a part
to its **current** root; query 2 then keeps only `t.equipment_id IN (<current machines>)`. A ticket
raised on a covered motor while it sat in CMP001, before the motor moved to CMP002, has
`equipment_id` = CMP001 and is dropped, though `ce.equipment_id = t.component_id` holds.

**Why it matters.** The contract page then under-counts the vendor's calls on exactly the item the
contract names, and "3 of 4 calls used" is wrong for that contract. Rare at the plant (a spare
motor swapped between compressors), but silent.

**Options.** (a) **Recommended:** accept and state it in § 9 as a residual beside S081 § 9 Q5
(the part's history shows the move), and correct § 5.1's wording to "the ticket's machine at raise
and its current component". (b) Widen query 2 to `(t.equipment_id IN (<machines>) OR
t.component_id IN (<line nodes below machine level>))`, both indexed (`ix_tickets_equipment_state`,
`ix_tickets_component_state`); the EXISTS on the line stays. Exact for a moved part; one more
`IN`, and a component under a moved component-unit still needs `c.parent_id`. KLA's call.

### BR1-04 — minor — The assignable-roles warning tells an engineer to ask an engineer

**Problem.** § 5.4's `no_assignable` text is "No Team record of Atlas Copco can be assigned at SMTW.
Ask an engineer to give one a Technician role there in Masters › Team." The card shows to every
`ticket:read` holder, so the engineer and the manager, who hold `people:assign_technicians`
themselves, read "Ask an engineer".

**Why it matters.** The reader who can fix it is told to ask someone else; a small thing, but it is
the one action the warning exists for.

**Options.** (a) **Recommended:** one text for everyone that names the action, not the person:
"No Team record of Atlas Copco can be assigned at SMTW. Give one a Technician role there in
Masters › Team." The floor cannot do it, but knows whom to tell. (b) Two texts by
`people:assign_technicians` in `userPermissions`. A second branch for one sentence; not recommended.

## Nits

- **BR1-05** (nit) § 5.3 item 5: "By: Ravi (Atlas Copco), Atlas Copco service" — every name listed
  is the vendor's, so "(Atlas Copco)" after Ravi says nothing; write "By: Ravi, Atlas Copco service".
- **BR1-06** (nit) § 5.7 and § 8.2: `groupPeople`'s filter must treat a missing `vendor_name`
  (undefined, the existing fixtures in `frontend/tests/ticketLabels.test.js:291`) as `null`; say
  "`null` or absent".
- **BR1-07** (nit) § 8.2 `test_the_period_edges`: a raise refuses a future time
  (`tickets_core.EVENT_TIME_FUTURE`), so "23:59 on To" needs a To date of yesterday or earlier; say
  the period ends yesterday (rule 5 lists an ended contract the same way).
- **BR1-08** (nit) § 8.4, the ticket-line test: "the warning above the action bar" is a geometry
  assertion in an untagged test; assert DOM order, or move the geometry into the `@device` test.
- **BR1-09** (nit) § 8.3: "S080–S085's `test_contracts_api.py`, `test_contract_equipment_api.py` and
  `test_contract_card_api.py`" leaves out S083–S085's test files; write "every `test_contract*_api.py`
  and `test_contracts_api.py`".
- **BR1-10** (nit) § 5.5 `complete`: `accessible_unit_ids` returns **active** units only, and the
  ticket predicate too, so a ticket on a unit deactivated later is invisible to everyone but admin
  and still absent from a "complete" count. State it as a residual (one line) beside the moved-machine one.
- **BR1-11** (nit) § 3 Backend: `contracts.py` "imports `events_by_ticket` from `tickets.py`" —
  also say that `tickets.py` imports `alerts`, `equipment`, `improvements_core` and `tickets_core`,
  none of which imports `contracts.py` (checked), so the coder need not re-trace it.
- **BR1-12** (nit) § 6 answer: `"intensity"` and `"is_breakdown"` both sent; the card draws only
  `IntensityBadge` from `intensity`. Keep both (the improvement page does), but say `is_breakdown` is
  for the total's future split, or drop it.
- **BR1-13** (nit) § 8.4 operator test: the note's text must match whatever BR1-02 decides;
  the test asserts the one line shown.

## Checked and found consistent

- **Names from S079 and S080 as coded:** `vendors`, `people.vendor_id`, `ix_people_vendor` (v42),
  `make_vendor` (`conftest.py:451`); `contracts_bp`, `READ_BASIC`, `_CONTRACT_SELECT` with
  `vendor_name` and `site_code`, `_contract_row(cur, contract_id)`, `_contract_out(row, flags,
  today)`, `_today()`, `get_contract`'s 404 rule; `contracts_core.contract_status` returns `{kind,
  label, days}` with kinds `upcoming`, `in_force`, `ending`, `ended`; `breakdown_calls_per_year` is
  forced `NULL` when the tick is off (`validate_contract`). The brief's note that S080's brief said
  `_fetch_contract` and `_contract_out(row, flags)` is right; the code is as the brief cites.
- **Names from S081–S085 as their briefs state them:** `contract_equipment` (`contract_id`,
  `equipment_id`, `uq_contract_equipment`), `POST /api/contracts/<id>/equipment`, `ContractView.vue`,
  `responseText`, `coverageLines` (S081); `GET /api/contracts/for-equipment/<int:node_id>`, its item
  keys (`status`, `only_vendor_repairs`, `covers_breakdown_calls`, `response_hours`, `contract_id`),
  `cardHeadline`, `UnderContractCard.vue`, the D9 text word for word (S082 § 5.3); the *Documents*
  card "after the *Machines covered* card, before any later card" (S083 § 5.7); the chain lines
  under the header and the *Renew contract* button (S085 § 5.7). Last on the page is free.
- **The reader rule.** `unit_access_condition(cur, "ticket:read", "t.unit_id", "m.unit_id")` is the
  predicate `tickets._visible_condition` uses (`tickets.py:191`, `equipment.py:366`); `None` when no
  unit. `accessible_unit_ids(cur, key)` is `None` for admin and for a token role with
  `equipment:read_all_units` (IT admin), else the set of active unit ids (`auth_utils.user_unit_ids`).
  Every row passes the same predicate as `GET /api/tickets/<id>`, so every serial link opens; the
  answer carries no count of hidden tickets; `used` only when `complete`.
- **Holders.** `ROLE_INCLUDES`: manager ⊇ engineer ⊇ technician ⊇ operator, supervisor ⊇ operator;
  `ticket:read` is `("maint_operator", "it_admin")`, so the storekeeper holds it nowhere and gets 403
  on the calls route while reading the contract page (`contract:read_basic` is `("*",)`). Both keys
  are in `SITE_SCOPED`. No new key.
- **"Its parts".** The tree is three levels (`machine_and_component`); `ce.equipment_id IN
  (t.equipment_id, t.component_id, c.parent_id)` is S082's `IN (e.id, e.parent_id, p.parent_id)`
  read from the ticket's side; query 1's `COALESCE(gp.id, p.id, e.id)` is `NODE_JOINS`' root. A
  ticket on the machine never counts for a line on a part (S082 B4). Apart from BR1-03, correct.
- **`tickets_core` reuse.** `ticket_times(events, now)` returns `downtime_minutes`,
  `waiting_by_reason` (`None` when never critical while scheduled) and all `None` on *Not a fault*;
  `latest_restoration(state, not_a_fault, events)` is `None` while open, sent back or not a fault;
  `WAITING_REASONS["vendor"]` is logistic delay (`tickets_core.py:318`). `tickets_core` imports only
  the standard library, so `contracts_core` → `tickets_core` is pure → pure; S084's `alerts_core` →
  `contracts_core` → `tickets_core` adds no cycle.
- **The move of `_events_by_ticket`.** Two callers in `improvements.py` (`_linked_tickets`, line 403,
  and the watch figures, line 602); the select has the columns `ticket_times` and
  `latest_restoration` need; `improvements.py` already imports from `tickets` (line 198) and its
  docstring says `tickets.py` never imports it.
- **The one existing test that breaks.** `test_tickets_api.py::TestPickers::test_people_of_the_site_with_trades_and_role`
  compares the whole item (line 434); it gains `"vendor_name": None`. `test_ticket_work_api.py:765`
  reads `assignable` only; `improvements.py` maps the picker items to `{id, name}` (lines 954,
  1489); `improvements.spec.js:187` and `tickets-parts.spec.js:69` read ids. No frontend unit test
  renders `PersonPicker.vue`. No other breakage found.
- **The picker.** `PersonPicker.vue` shows "Name · Role" per button and a picked line with name
  and role; `groupPeople` filters on `p.name` only today (`ticketLabels.js:296`). `people_at_site`
  (`tickets.py:748`) is one query plus the trades; a `LEFT JOIN vendors` adds no query.
- **The ticket page.** `TicketDetailView.vue:234` plan line, `:239` action bar (stacked on a phone);
  the detail sends `permissions` (`permissions_at_site`), `machine` and `component` (`tickets.py:216,
  427`). `ticket.state !== "closed"` is the open test.
- **Query cost.** Four plain reads, each on an index: `uq_contract_equipment`,
  `ix_tickets_equipment_state`, the `ticket_assignees` primary key and `ix_ticket_labour_ticket`
  inside the EXISTS, `ix_ticket_events_ticket`, `ix_people_vendor` with the memberships primary key
  `(person_id, site_id)`. No N+1. Pool connections are autocommit (`db_helpers.py:45`).
- **Layers.** The figures, totals, used line and warning choice are pure (`contracts_core`); the
  SQL and access checks are the shell; the card and line are presentational. Reuse of
  `ticket_times`, `events_by_ticket`, S082's route, `cardHeadline`, `responseText`, `IntensityBadge`,
  `stateLabel`, `minutesText`, `formatDateTime`. No new abstraction.
- **Standards.** EN 13306 (corrective maintenance, logistic delay), ISO 14224 § 9 resources,
  ISO 9001 § 8.4, ISO 55001 § 8.3, ISO 27001 A.5.15 / A.8.3: named, explained in plain words, and
  tied to the rules; the *to verify* marks are right.
- **Track:** full, as it should be (access checks, two permission keys on one route, 20 files).
- **Manual checks:** every check is a screen, text or flow a browser judges; S082's device row
  covers the warning's legibility. None missing.
- **Plan.MD.** § 2 item 9 (`docs/Plan.MD:48`) holds "derived, never re-entered" and the vendor-link
  wording; § 4.2 exists (line 385). The housekeeping lines fit.
- **Seed.** `e2e_operator` holds MCC2 only; `e2e_storekeeper` exists (`seed_e2e.py:38, 45`).

## Feedback

- waste: the facts file lists `ix_people_vendor`, `_CONTRACT_SELECT`, `make_vendor` and the S080 names as found, but the brief's "(from S0NN)" names planned by S081–S085 appear only in the "not found … (planned in …)" line, with the step numbers in a mixed order ("planned in S082, S081, S080, S085, S083, S085"); a per-step grouping would save re-reading the five briefs to know which one defines each name (about 10 minutes).
- hindrance: `grep -n "moved_parent" backend/equipment.py` found nothing because the kind is set in `equipment_core.py`; a module docstring line in `equipment.py` naming where the move kinds are decided would have saved one search.
- none otherwise.
