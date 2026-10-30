```
Step: S081 — Machines on the contract
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: d216f48 + uncommitted S079

# S081 — Brief review, round 1

**Verdict: no blocker or major finding is open.** Four `minor` findings and seven nits. The brief
builds on S080's names, keys, `_contract_out`, flags, lock order and migration numbering as S080's
brief states them, and the cut with S082 is clean except one shared helper's output (BR1-04). Facts
file used: `scratch/brief-facts-S081.md`; the S080 names it reports as not found are expected.

**For KLA at gate B (not findings):** Q3, Q5 and Q6 are taken under the delegation, as the brief
marks. One more decision KLA should see: **B3** departs from S080 D4's rule ("a field the writer
may not see is ignored on write") for the price route alone (403 instead of a silent 200). The
reasoning holds (the route has no other field), but it is the first place the two rules differ.

## Findings

### BR1-01 — minor — § 5.7: `lineBody(form, { creating, canReadCost })` cannot be `useFormModal`'s `toBody`

**Problem.** `useFormModal` calls `toBody(form.value)` with one argument
(`frontend/src/composables/useFormModal.js`, `save()`), so `toBody: lineBody` never receives
`creating` or `canReadCost`; `price` would be sent by a non-holder's create, and the create and edit
bodies could not differ. The brief's call contract also names `fromRecord` without saying what it
returns (settings: *Self-check, repo items* (13)).

**Why it matters.** The coder would have to change the shared composable or invent the wrapper
alone; a change to `useFormModal.js` is shared code and runs the whole browser suite again.

**Options.**
- (a) **Recommended.** The dialog wraps it: `toBody: (form) => lineBody(form, { creating:
  editingId.value === null, canReadCost: props.canReadCost })`, with `editingId` taken from the
  composable's return (the closure reads it at save time). State `fromRecord(record)` →
  `{ equipment_id: record.equipment_id, price: record.price ?? "" }`. No shared file changes.
- (b) `useFormModal` passes `{ creating }` to `toBody`. Touches a shared file for one caller.

### BR1-02 — minor — § 3, § 5.7: the picker emits only the id; the dialog must show the picked machine's code and name

**Problem.** `EquipmentPicker.vue` emits `pick` with `e.id` only. The brief has the dialog show
"CMP001 — Screw compressor 1" with *Change* after a pick, and changes the picker only for `siteId`.
`RaiseTicketView.vue` gets the name by loading `/api/equipment/<id>` after the pick; the brief does
not say which way the dialog goes.

**Why it matters.** A rule the coder would decide alone: either a second request inside the dialog
(with its loading and error states) or a picker change the brief does not list.

**Options.**
- (a) **Recommended.** The picker emits the item too: `emit("pick", e.id, e)`. Its two users ignore
  the second argument, so they are unchanged; the dialog stores `{ equipment_id, code, name,
  full_path }` from it and needs no fetch. Add it to § 3's `EquipmentPicker.vue` line.
- (b) The dialog loads `GET /api/equipment/<id>` after a pick (one more request; a 404 case to
  show).

### BR1-03 — minor — § 5.2, § 6: *Edit price* and *Remove* on an inactive contract are not ruled

**Problem.** Rule 1 of § 5.2 refuses an **add** on an inactive contract (409). Nothing says what
`PUT …/equipment/<equipment_id>` and `DELETE …` do then. The page shows *Remove* and *Edit price*
for `can_edit` with no `active` condition, while *Add machine* needs the contract active.

**Why it matters.** The coder decides a business rule alone, and the tests of § 8.2 do not cover it.

**Options.**
- (a) **Recommended.** Allowed: a contract set inactive by mistake is still corrected (S080 § 5.1
  lets an inactive contract be edited). State it in § 5.2 and in § 6's rows, and add one test each
  (a price change and a removal on an inactive contract, 200).
- (b) Refuse both with the add's 409 and hide the two controls when the contract is inactive.

### BR1-04 — minor — § 5.7 vs S082 § 5.3: the two briefs give `responseText` different outputs

**Problem.** S081 § 5.7: Response time (`responseText`: "24 hours", "1 hour") as a `dl` value under
the label *Response time*. S082 § 5.3 item 4: `responseText`: "Response time: 24 hours". One helper,
two outputs; S082 reuses it from S081 (S082 § 3).

**Why it matters.** The second coder would break the first step's unit test or write a second
helper for one value.

**Options.**
- (a) **Recommended.** `responseText(hours)` → "24 hours" / "1 hour" / `null` (S081, coded first);
  S082's card writes "Response time: " before it. S082's brief needs the matching edit (for the
  orchestrator).
- (b) The helper returns the full "Response time: 24 hours", and S081's `dl` row shows it under a
  `dt` that repeats the words.

## Nits

- **BR1-05** (nit) § 5.7 *Terms* › Cost and *Machines covered* › Total: the same total shows twice on
  one page ("₹37,837 before GST · the sum of 2 of 3 machine prices" and "Total: ₹37,837 before GST ·
  2 of 3 machines priced."). Show it once, under the list where the prices are; keep the cost note in
  *Terms*.
- **BR1-06** (nit) § 5.7: with no machines, the page would show both "No machines on this contract
  yet." and "No prices entered yet.". Leave the total line out when the list is empty.
- **BR1-07** (nit) § 3: `_overlaps(cur, contract_ids, …)` has an ellipsis in its signature. Name the
  arguments (recommended: `_overlaps(cur, contract, lines, site_ids)` → `{equipment_id: [...]}`).
- **BR1-08** (nit) § 5.5: the rewritten equipment.py bullet drops S080's create path ("a create takes
  the site and the vendor LOCK IN SHARE MODE"). Keep that clause in the rewrite.
- **BR1-09** (nit) § 5.3: "at most 100 + 34 characters" — with `TYPE_SHORT` "Warranty" the suffix is
  37 (" (Warranty, DD-MM-YYYY to DD-MM-YYYY)"). Write "at most 137, inside VARCHAR(200)".
- **BR1-10** (nit) § 5.7: inside the site-filtered picker the empty state still reads "No equipment
  found at your units." (the picker's text). A BRICKS machine typed into an SMTW contract's dialog
  then names the wrong reason. Either accept it (state so) or give the picker an optional
  `emptyText` prop ("No machine of SMTW matches.").
- **BR1-11** (nit) `docs/steps/INDEX.md`: the S081 row says `Draft`; the brief says `In review`
  (the orchestrator's).

## Checked and found consistent

- **S080's names and shapes:** `contracts_bp`, `_contract_out(row, flags)`, `_fetch_contract`,
  `_sites_holding(cur, key)`, the flags `can_edit` / `can_read_callout` / `can_read_cost`, the four
  `contract:*` keys (all `SITE_SCOPED`), `contract_status`, `CONTRACT_TYPES`, `contractTypeLabel`,
  `statusBadgeClass`, the spec `contracts.spec.js` with in-spec helpers, `test_contracts_api.py`,
  `test_migration_v43.py` (`range(20, 44)`): all as S080's brief states them. v42 (S079) is in the
  working tree (`backend/local_db.py`, `test_migration_v42.py`, `conftest.py` `_TABLES` holds
  `vendors`, `make_vendor` at `conftest.py:451`); v43 is S080's; v44 follows.
- **The cut with S082:** S082 cites from S081 exactly `contract_equipment` (`contract_id`,
  `equipment_id`), `ix_contract_equipment_equipment`, `POST /api/contracts/<id>/equipment`,
  `/contracts/:id` (`ContractView.vue`), `coverageLines`, `responseText` and the spec's S081 tests;
  all are in S081 § 3–§ 6. Both say `_sites_holding` stays in `contracts.py` in S081 and moves in
  S082 (B10). B-numbers do not collide (S081: B1, B3, B5–B9, B11, B13, B14; S082: B2, B4, B10, B12,
  B15). Q2 and Q4 are in S082, Q1, Q3, Q5, Q6 in S081. `coverageLines` has the same text in both.
  Only `responseText` differs (BR1-04).
- **Current code the brief relies on:** `NODE_JOINS` resolves the unit as `COALESCE(gp.unit_id,
  p.unit_id, e.unit_id)` then `sites s` (`equipment.py:178`); `write_events(cur, equipment_id,
  changes)` with `actor()` (`:500`); `accessible_unit_ids(cur, key)` (`:354`); `node_path(node)`
  (`:267`); `_lock_target_unit` checks only `equipment:edit` at the new site (`:423`), so a covered
  node can move sites; the list's `site_id` filter is `u.site_id = %s` in `_list_filters`, so the
  picker's `site_id` works with `level=all&q=`; `insert_row` / `update_row` (`update_row` stamps
  `updated_at = NOW()`, `updated_by`); `row_to_dict` leaves `Decimal` to Flask (a string);
  `UNIQUE_KEY_ERRORS` entries are `(field, message)`; `require_perm_at` answers "You can't do this at
  <code>"; the manager inherits the engineer's keys (`ROLE_INCLUDES`); `canOpenRoute` allows a route
  with no nav item, so `/contracts/:id` opens and lights nothing (B13); `FormModal` has
  `saveDisabledReason`; `MetersCard.vue` asks *Remove* in the row with *Keep*; `LessonView.vue` is
  the 404-gate pattern; `describeEvent`'s default case shows an unknown kind by name, and its test
  exists.
- **Migration v44:** v33's `MODIFY event` (`local_db.py:1030`) is the latest ENUM list at the
  baseline; v34–v42 do not touch it; the two kinds go at its end. `equipment_events.new_value` is
  `VARCHAR(200)`. No `_PRECONDITIONS` entry is right (a new table, an ENUM widened at its end).
  `test_migration_v41.py`'s pattern (`_migrate`, `_recreate`, `_run`, `_schema`) and v33's ENUM
  assertion (`COLUMN_TYPE … endswith`) fit § 8.1.
- **Locks (§ 5.5):** the contract row is first in every line write; the node is taken shared only;
  no module that holds the node exclusive (equipment.py's move, scrap, edit; meters.py;
  item_properties.py; documents.py; tickets.py's raise) waits on a contract or a line row; the
  remove's `write_events` takes the node's shared FK lock while holding only contract and line rows,
  which nothing else locks. A parent-row update that keeps `id` takes no lock on child rows, so a
  scrap never waits on a `contract_equipment` row. No cycle.
- **Layers:** `validate_line`, `parse_price`, `event_text` and `TYPE_SHORT` in the pure core; the
  routes, the locks and the overlap query in the shell; the page presentational. `parse_price` as
  its own function is right: `meters_core._DECIMAL_RE` is `^-?\d+(\.\d+)?$` (a minus and any
  decimals), as B11 says.
- **Permissions:** `price`, `price_total`, `priced_count` leave the server only with
  `contract:read_senior` at the contract's site through `_contract_out` and `_machine_lines`; the
  add drops the price for a non-holder; the price route needs `contract:edit` and
  `contract:read_senior`; the history line never holds a price. IT admin adds machines, never a
  price. No new key; `test_role_matrix` unchanged.
- **Standards:** ISO 55001 § 8.3 (outsourced work stays the plant's responsibility: the record of
  which vendor maintains which machine, until when, at what price), ISO 14224's hierarchy (data kept
  against the equipment tree; a line may sit on any level), EN 13306 *item* (a line names an item,
  so "covered" means one thing at every level), ISO 9001 § 7.5.3 (the add and remove lines are the
  record; the delete is a stated departure, B5), ISO 27001 A.5.15 / A.8.3 (the price behind the
  senior key, enforced by the API). Named and explained in plain words; the *to verify* marks are
  honest.
- **Use on the floor:** one job per screen (the page lists the machines; the dialog picks one);
  the one-tap path *Add machine* → type → tap → *Add machine*; *Remove* asks in the row and names
  the consequence; the Save button's reason in the footer; controls hidden by key, no 403 from a
  button; "Contract not found, or not at your sites." as the lesson page's pattern; the `@device`
  no-sideways-scroll test. Messages are scope B.
- **Tests (§ 8):** the `[auto]` checks are browser-judgeable; no device check is right. The targeted
  run names the two picker users' specs and `screens.spec.js`; the router change runs the whole
  suite at Normal; no `api.js` or `e2e/support/` change, so no WebKit run.
- **Track full** is right (migration, locks, a new page and routes). 19 code and test files, one
  concern; already the half of a split item, no further cut asked.

## Feedback

- waste: the facts file's *Screen text in the tests* lists `"-1"` in 125 test lines because the
  brief names `"-1"` as a refused price value; a two-character literal is never a label
  (`scratch/brief-facts-S081.md` § Screen text; an idea: skip quoted values shorter than 3
  characters or purely numeric).
- hindrance: the facts file says `can_edit` is "defined at backend/meters.py:359" though the brief
  means S080's flag; a bare attribute name that several modules define is reported as if one place
  owned it (`scratch/brief-facts-S081.md` § Code names). Listing "defined in N files" for a
  common name would read truer.
- idea: for two briefs cut from one roadmap item and reviewed in parallel, a facts run that lists
  the names **both** briefs cite (`coverageLines`, `responseText`, `_sites_holding`) would have
  surfaced BR1-04 mechanically; today the reviewer reads both briefs end to end for it.
