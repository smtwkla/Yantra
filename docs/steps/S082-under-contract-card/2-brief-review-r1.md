```
Step: S082 — Under contract on the machine
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.2
```

Reviewed against: d216f48 + uncommitted S079 (S080 and S081 are not coded: every name marked "from S080"
or "from S081" was checked against `docs/steps/S080-contract-register/1-brief.md` and
`docs/steps/S081-contract-equipment/1-brief.md`, not code. The staleness review before coding must
re-check them, as the brief's A1 says.)

# S082 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** Six `minor` findings and six nits. The design is
right-sized: the card's rules (nearest line, the 90-day window, the order) sit in `contracts_core`,
the shell builds items through S080's `_contract_out` and then a whitelist, `equipment.py` imports
only the pure core, and the filter stays out of `_list_filters` so the print is unchanged. The cut
between S081 and S082 is clean, and the two briefs agree on every shared name (`contract_equipment`,
`ix_contract_equipment_equipment`, `_contract_out(row, flags)`, `coverageLines`, `responseText`,
`statusBadgeClass`, the four keys, `/contracts/:id`, who moves `_sites_holding`). The facts file
`scratch/brief-facts-S082.md` was given and used; every name it lists as existing is where the brief
says, and every "not found" is a planned S080/S081 name or a new S082 one.

**Points that need KLA's own decision** (gate A is delegated tonight):

- **KLA — BR1-01, where the card sits.** The brief takes the roadmap's "after *Open tickets*". I
  recommend before it: S077 put *Lessons* above *Open tickets* for the very reason that applies more
  strongly to "Do not repair" (see the finding).
- **KLA — BR1-04, the call-out number as a tap-to-call link.** The brief sends it as text, as S079's
  vendor phone. The engineer reads it standing at a stopped machine with the phone in hand.
- **KLA — BR1-05, the wording of the line everyone else sees** ("Call the engineer.", D10). The
  finding proposes a line that says what the number is for.
- **KLA — § 9 Q4, a part's contract on the machine's card.** I agree with the brief's (a) for now:
  every contract in Plant-Facts § 4 sits on a machine, so no card loses anything today. Fact to
  weigh: a technician scans the machine's label, not the motor's, so a later motor warranty with the
  D9 tick would not warn them on the machine's page. (b) is a later change of one query and one line.

## Findings

### BR1-01 — minor — § 5.3, § 9 Q2: the card below *Open tickets* hides "Do not repair" on a busy machine (KLA)

- **Problem.** On a phone the order is *Raise ticket*, *Lessons*, *Open tickets*, then *Under
  contract*. A machine under a D9 contract that has three open tickets puts the warning a screen
  below the fold. The person who must see it is the technician who has just scanned the label and is
  about to open the machine.
- **Why it matters.** Fuji's and Toyota's terms void the contract if anyone else repairs the machine
  (D9). `EquipmentDetailView.vue`'s own docstring gives the precedent: "the Lessons card … comes
  first, before Open tickets … an operator who scans the QR label wants what to do, and a busy press
  has open tickets" (S077). The same reasoning puts a contract warning above the tickets list.
- **Options.** (a) After *Open tickets*, as the roadmap and the brief. (b) **Recommended:** after
  *Lessons*, before *Open tickets*, on every width; the docstring line names the reason. (c) The card
  after *Open tickets* but the D9 warning alone as an alert next to *Raise ticket* — two places for
  one fact, rejected.
- The brief already says the orchestrator will ask KLA at gate B; this finding asks for it at gate A,
  so the e2e test `S082: a technician sees the Under contract card …` asserts the right order from the
  start.

### BR1-02 — minor — § 5.1, § 5.2: the card route's query and how `via` is built are left to the coder

- **Problem.** The brief says the items are "built by `_contract_out(row, flags)`" and that `via` is
  `{id, code, name}` of the ancestor, but not which query gives the rows. `_contract_out` expects
  S080's row shape (`vendor_name`, `vendor_active`, `site_code`, the dates, the ticks): the card's
  query must select the same columns, or reuse S080's select fragment. It also does not say where the
  ancestor's code and name come from, nor what `card_items(rows, node, today)` receives (the
  contract row plus the line's `equipment_id`, so the core can pick the nearest line).
- **Why it matters.** A second hand-written select of the contract columns is a second copy of S080's
  row shape, and the next contract column (R02.4's renewal) then shows on the page and not on the
  card. The ancestor needs no query: `load_node_for_user` returns the node row with `parent_id`,
  `p_code`, `p_name`, `gp_id`, `gp_code`, `gp_name` (`_NODE_COLUMNS`, `backend/equipment.py`), which
  `_ancestors(node)` already turns into `[{id, code, level, name}]`.
- **Options.** (a) **Recommended:** state it: one query, S080's contract select fragment (the one the
  list and `_fetch_contract` use, named at the staleness review) joined to `contract_equipment` with
  `ce.equipment_id IN (%s, %s, %s)` over the node, its parent and its grandparent (NULLs dropped),
  `ct.active = 1`, the date window as parameters; each row carries `ce.equipment_id`;
  `card_items(rows, node, today)` takes those rows and `{id, parent_id, gp_id}` of the node and
  returns `[{row, via_id}]` in order; the shell keeps the rows whose site passes `has_perm_at`,
  builds each through `_contract_out`, cuts to the § 5.2 keys and sets `via` from the node row's
  parent or grandparent columns. (b) Load each contract with `_fetch_contract` (one query per
  contract) — simpler code, two to three queries on a page; acceptable too, but say which.

### BR1-03 — minor — § 5.4, § 8.2: `covered_sql(site_ids)` cannot give what its tests ask of it

- **Problem.** The signature takes only `site_ids`, yet § 5.4 says it returns the `EXISTS (…)` "and
  its parameter order", `NOT EXISTS` for `not_under`, and § 8.2 tests "the SQL and parameter order for
  one and three sites, `under` and `not_under`". The SQL has two date placeholders
  (`ct.from_date <= %s AND ct.to_date >= %s`) and N site placeholders; who supplies the dates and in
  which position is not said. `COVERAGE_FILTERS`' values are not written out either.
- **Why it matters.** The coder has to invent the contract between the core and `list_equipment`; a
  wrong parameter order is a silent wrong filter (a date compared to a site id), which only a test
  that fixes the order catches.
- **Options.** (a) **Recommended:** `COVERAGE_FILTERS = ("under", "not_under")`;
  `covered_sql(filter, site_ids, today) -> (sql, params)` with `params = [today, today, *site_ids]`
  in the order the SQL names them, `EXISTS` or `NOT EXISTS` by `filter`; an empty `site_ids` returns
  `("0 = 1", [])` for `under` and `("1 = 1", [])` for `not_under` (no `IN ()`), which is the rule
  § 5.4 states. The shell passes `datetime.now(IST).date()`. (b) The core returns the SQL only and
  the shell appends `[today, today, *site_ids]` — two places must agree on the order; rejected.

### BR1-04 — minor — § 1 Out of scope, § 5.3: the call-out number is text, where a tap would make the call (KLA)

- **Problem.** The card is read on a phone at the machine (§ 8.5, the QR scan). The engineer who sees
  "Call-out number: +91 00000 00000" wants to call it now; as text they must select it or retype it.
  The brief puts a tap-to-call link out of scope "as S079's vendor phone", where S079 D12 said "one
  line to add later".
- **Why it matters.** It is the one moment in Yantra where a phone number is read with a phone in
  hand at a stopped machine; the vendor's office phone (S079) is read in Masters at a desk. One
  attribute (`<a :href="`tel:${digits}`">`) finishes the main job in one tap.
- **Options.** (a) Text, as the brief and S079. (b) **Recommended:** a `tel:` link on the card, the
  number shown as stored; the e2e test asserts the link's `href` starts with `tel:`. S079's vendor
  phone stays text until a step needs it. KLA decides, since it departs from S079 D12.

### BR1-05 — minor — § 5.3 item 6: "Call the engineer." does not say what it is about (KLA)

- **Problem.** For a reader without `contract:read`, the call line is the bare sentence "Call the
  engineer." in the place of the call-out number. On a plain AMC with labour covered it reads as an
  instruction to call the engineer for anything about the machine; the card does not say that a
  vendor number exists or that the engineer holds it. (With the D9 tick the warning already says it,
  and the brief rightly drops the line.)
- **Why it matters.** Scope B: a line says what the user sees and what to do next. A technician who
  may do first-line work on an AMC machine should not read "call the engineer" as a rule of the
  contract. D10's words are KLA's ("Everyone else sees 'Call the engineer'"), so the change is KLA's.
- **Options.** (a) Keep "Call the engineer." (D10 verbatim). (b) **Recommended:** "To call the
  vendor, ask the engineer." — the same instruction, with what it is for. (c) "Vendor's breakdown
  line: ask the engineer." Either (b) or (c) is one string in `callLine`.

### BR1-06 — minor — § 8.5: the device row needs its set-up, and what it checks that a browser cannot

- **Problem.** The row says "scan the QR label of a machine under a contract with *Only the vendor may
  repair* ticked" on "production on the TEST machine, or the dev server". On production that needs a
  vendor and a contract with the D9 tick on the TEST machine — real rows in the register, never
  deleted (S080: inactive instead), which the row does not mention. The QR scan itself (camera →
  `/e/<code>` → the equipment page) is S014's path and is already on the device list; the only part a
  browser cannot judge here is whether the yellow warning is readable in the shop's light on a real
  phone.
- **Why it matters.** `docs/steps/device-checks.md` rows are done by IT Admin from the row's words
  alone; a row without its set-up is skipped or done wrong, and a test contract left active in
  production would show on the TEST machine's card and in Masters › Contracts for everyone.
- **Options.** (a) **Recommended:** the dev server only, with the set-up in the row ("KLA adds a
  vendor *Test vendor* and a contract with *Only the vendor may repair* ticked on the TEST machine
  before the check"), the account "a technician of SMTW", the network "the plant's or home Wi-Fi",
  and the check "the yellow Do not repair warning is readable at arm's length in the shop's light".
  (b) Production too, with "set the contract inactive afterwards" in the row.

## Nits

- **BR1-07** (nit) § 5.4 last bullet: "The filter and the card answer the same question for the same
  node" is not exact: the card also shows contracts ended in the last 90 days, which the filter does
  not count. Say "… the same question about contracts in force".
- **BR1-08** (nit) § 5.1 Order: add `id` as the tiebreaker (`to_date, id`), as S080 § 5.3 orders the
  list, so two contracts ending the same day have a fixed order in the tests.
- **BR1-09** (nit) § 5.3 item 3, scope B: "On CMP001 — Screw compressor 1, which this part belongs
  to." is a relative clause a low-literacy reader will not follow. Simpler: "Through CMP001 — Screw
  compressor 1, this part's machine."
- **BR1-10** (nit) § 5.4 Screen, scope B: "Any contract" as the no-filter option reads as "under any
  contract". Use "Any contract status", the form of "Any ticket status" (`TICKET_FILTER_CHOICES`).
- **BR1-11** (nit) § 9: state the accepted residual that follows from S081 § 9 Q5: a machine moved to
  another site keeps its line, but the new site's technicians hold no `contract:read_basic` at the
  contract's site, so its card (and a D9 warning) does not show there; the contract page's "Now at
  BRICKS." is the engineer's cue. § 8.2 tests it; § 9 should own it.
- **BR1-12** (nit) § 5.3: say that the card shows on a scrapped node as on any other (S081 keeps the
  line; the page is read-only), so the coder does not add a lifecycle rule of its own.

## Checked and found consistent

- **Current code.** `load_node_for_user(cur, node_id, for_update=False)` returns the node row with
  `parent_id` and `gp_id` (`_NODE_COLUMNS`); `NODE_JOINS`' parent alias is `p`, so
  `IN (e.id, e.parent_id, p.parent_id)` is right; `_list_filters` and `list_equipment` are separate,
  the `tickets` filter sits in the latter as the brief says; `frontend/src/utils/assetList.js`
  `FILTER_KEYS` has neither `tickets` nor `contract`; `EquipmentView.vue` `FILTER_KEYS` and
  `listUrl` skip `tickets` for a user without `ticket:read`, the pattern `contract` copies;
  `IST` is at `backend/equipment.py:163`; `enum_arg` answers 400 for a value outside its list;
  `permissions_at_site` carries the `("*",)` keys of the role held at the site, so
  `node.permissions` holds `contract:read_basic` for every reader; `monkeypatch.setitem(
  config_rbac.PERMISSIONS, …)` is the pattern of `test_improvements_api.py:654`.
- **Existing tests.** `S064: … Filters (n) with its count …` asserts `Filters (2)` for
  `criticality=A&scrapped=1`, no `contract` key: green. `S064: … Documents and Photos cards come
  before Details` compares Documents with Details only: unaffected by a new `order-0` card. The
  Lessons order test (`lessons.spec.js:256`) compares *Lessons* with *Open tickets* only: unaffected.
  `S029: the bulb is in view …` measures the *Tickets* select from `md` up: re-run, as the brief says.
- **Layers.** Nearest line, window, order: `contracts_core` (pure). Permission filter, `_contract_out`,
  the whitelist: the shell. `cardHeadline`, `callLine`: presentational, from the item's flags.
  `equipment.py` → `contracts_core` only; `contracts.py` → `equipment.py` as S081 already does; no
  cycle. `sites_holding` in `auth_utils.py` beside `has_perm_at` is the one copy; S081 § 3 and S082
  § 5.5 agree on who moves it.
- **Permissions.** `require_perm("contract:read_basic")`, then `equipment:read` on the node's unit
  through `load_node_for_user` (404), then `has_perm_at` at each contract's site; the call-out number
  only through `_contract_out`'s flag; never `price`, `price_total`, `priced_count`, `cost_note`
  (whitelist). No new key; `test_role_matrix` unchanged. The filter counts only contracts at
  `sites_holding(cur, "contract:read_basic")`; no `IN ()` on an empty list.
- **Edge cases.** A contract on the node and its parent → one item; upcoming excluded (B15); inactive
  excluded; ended at 90 days kept, 91 dropped; a move across sites (§ 8.2); the database down → 503.
- **Standards.** ISO 55001 § 8.3, TPM autonomous maintenance, ISO 14224 hierarchy and ISO 27001
  A.5.15 / A.8.3 named and explained in plain words; the *to verify* marks match the roadmap's.
- **Track.** Full is right: a new endpoint with access checks.
- **Manual checks.** The automated list covers each screen claim with what the user sees; the
  `@device` test is a geometry check and tagged.
- **Roadmap and Plan.** D5, D9, D10 followed as written; Plan.MD § 2 item 9's card text ("the card
  then warns 'Do not repair'") matches; the mock-up's "contract:read" note is correctly overridden by
  D5 (§ 9).

## Feedback

- idea: checking the S081–S082 cut meant reading S081's 650 lines in full; a short "shared with
  S08N" list at the top of each half (the names and who moves what) would let the reviewer of one
  half verify the seam without the whole other brief (about 10 minutes).
- rule: a brief planned ahead of two uncoded steps can only be checked against briefs, so the facts
  file reports some 40 names as "not found (planned in S080/S081)" and the real check moves to the
  staleness review; README § Stale brief check could say that for such a brief the staleness review
  is required, not "only when something changed", since the baseline code for those names is empty.
