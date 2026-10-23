Step: S029 — Ticket light on the equipment list
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 23-10-2026

Reviewed against: d686fcd + uncommitted S028

# S029 — Brief review, round 1

**Verdict: one `major` is open (BR1-01, the track).** The design itself is sound: the SQL
semantics, the unit gate and the tests are right or need only small additions. The brief was
reviewed against the light template. By `docs/steps/README.md` § Tracks a `major` finding
switches the step to full, so this is not the only round unless the user overrides the track.

Code read: `backend/equipment.py` (`list_equipment`, `_summary`, `_list_filters`,
`accessible_unit_ids`), `backend/tickets_core.py`, `backend/alerts_core.py`,
`backend/tickets.py` (`_visible_condition`, `_equipment_filter`, `list_tickets`),
`backend/auth_utils.py` (`user_unit_ids`), `backend/access_core.py`, `backend/config_rbac.py`,
`backend/app.py` (`auth_me`), `backend/local_db.py` (the `tickets` table and its indexes),
`backend/tests/test_equipment_api.py`, `backend/tests/test_rbac.py`, `backend/tests/conftest.py`,
`frontend/src/views/EquipmentView.vue`, `frontend/src/utils/assetList.js`,
`frontend/src/utils/ticketLabels.js`, `frontend/src/components/StatusBadge.vue`,
`frontend/e2e/equipment.spec.js`, `screens.spec.js`, `support/people.js`, `support/tickets.js`,
`tooling/e2e/seed_e2e.py`.

## Findings

### BR1-01 — major — Belongs on the full track: the step adds an access check

**Problem.** The light criteria (README § Tracks) exclude "auth, RBAC or security-sensitive
code (… access checks)". § 3a adds one: per row, whether this user may see ticket facts at the
row's site (`accessible_unit_ids(cur, "ticket:read")`, a `SITE_SCOPED` key), and a filter
(`tickets=`) that must not reveal tickets of a unit the user holds no `ticket:read` in. Today
only the storekeeper holds `equipment:read` without `ticket:read` (`config_rbac.py`,
`test_role_matrix`), and the data is low-value, but it is an access rule all the same.

**Why it matters.** The track decides who codes it, how many review rounds the brief gets,
and what the user approves at gate A. The brief itself says the step switches if the review
finds otherwise.

**Options.**
- (a) **Switch to full** (recommended, the README's rule). The brief's text can stay as it
  is: its § 3a already states the rule and § 5 tests both sides. Only the header, the index
  row and the review rounds change.
- (b) The user overrides and keeps light, recorded in the Review log. Grounds: the check
  reuses the existing helper and pattern (`tickets._visible_condition`,
  `list_equipment`'s own `IN` clause) and adds no key.

### BR1-02 — minor — `_DOWN_STATES` already exists in `tickets_core`

**Problem.** § 3 says a *new* constant `DOWN_STATES` in `tickets_core.py`. The module already
has `_DOWN_STATES = (RAISED, ACKNOWLEDGED, SCHEDULED, IN_PROGRESS)` (line 334), used by
`ticket_times` for downtime. A coder following the brief adds a second definition of the same
tuple in one module.

**Why it matters.** Decision 6 is "one definition of down". `alerts_core._OPEN_STATES`
(line 42) also duplicates `tickets_core.OPEN_STATES`.

**Options.**
- (a) **Rename the existing `_DOWN_STATES` to `DOWN_STATES`** (recommended), use it in
  `ticket_times` and in `alerts_core` instead of its private copy; and let `alerts_core`
  import `OPEN_STATES` too, dropping `_OPEN_STATES`. `test_alerts_core.py` and
  `test_tickets_core.py` need no change unless they name the private constants (I found no
  such use).
- (b) Add the public constant and leave the private ones: two definitions, against the
  decision.

### BR1-03 — minor — `test_row_fields` breaks: it asserts the exact key set of a list row

**Problem.** § 5 says "check none compares whole items". One does:
`test_equipment_api.py::TestListing::test_row_fields` (line 708) asserts
`set(item) == {…, "status", "part_count"}`, on purpose, so the list gains no field unnoticed
(S004 § 5.5). Adding `ticket_light` fails it.

**Why it matters.** The coder must know to extend that set, and to send `ticket_light` on
every row (`null` included), so the exact-set test stays meaningful.

**Options.**
- (a) **Say in § 5: add `ticket_light` to `test_row_fields`'s set; the key is present on
  every row** (recommended).
- (b) Leave it to the coder to find at the first test run.

Also: add `ticket_light` to `_summary` only if the asset list should carry it too; the brief
says the printed list is unchanged, so compute it in `list_equipment` beside `part_count`
(`items = [{**_summary(row), "part_count": …, "ticket_light": …}]`). `test_asset_list_api.py`
asserts no exact row shape, so either way passes there; the brief should name the place.

### BR1-04 — minor — Levels: a component-unit's bulb does not cover its components

**Problem.** § 3a: a row counts tickets with its id in `equipment_id` (machine) or
`component_id` (part). A ticket raised on a component under a component-unit stores
`component_id = the component's id` and `equipment_id = the machine's id`
(`tickets_core.machine_and_component`). So at level *component-unit* the row between is
green while its component is red; only the machine aggregates. The brief does not say this.

**Why it matters.** The coder, or later the user, would see a green component-unit above a
red component and call it a bug.

**Options.**
- (a) **State it** (recommended): "A component-unit's bulb covers tickets raised on it, not
  on its components, as the ticket list on its page does (`tickets._equipment_filter`,
  S017 § 6). The machine's row covers the whole subtree." Add the case to the § 5 test
  (component-unit row `none`, component row `down`, machine row `down`).
- (b) Cover the components too: `OR t.component_id IN (SELECT id FROM equipment WHERE
  parent_id = e.id)`. More SQL for a level the floor rarely lists.

### BR1-05 — minor — A planned stop shows amber; say so (user's call)

**Problem.** S019 records a machine stopped for scheduled work (`started` event with
`machine_stopped`, planned downtime). Such a ticket is a defect in progress, so its bulb is
amber and *Down now* does not list it, although the machine is stopped.

**Why it matters.** The request says "down because of a breakdown ticket", so amber is right
by the request; but a supervisor reading *Down now* as "which machines are stopped" would miss
it. This is a judgement call for the user, not for the coder.

**Options.**
- (a) **Keep amber and write it down** (recommended): one line in § 1 ("a machine stopped
  for planned work shows amber; red is a breakdown only") and in *Out of scope*.
- (b) Red for a planned stop too: needs the latest `started` event's `machine_stopped`
  with no restore after it, a join on `ticket_events`; bigger query, defer to a later step.

### BR1-06 — minor (UX) — Put the bulb beside the code, not after Status

**Problem.** § 1 places the column after *Status*, the eighth column. On a phone the table
scrolls sideways (`table-responsive`), so the bulb is off-screen until the user scrolls right;
an at-a-glance light that needs a scroll is not at a glance.

**Why it matters.** Supervisors and engineers are phone-first (Plant-Facts § phones). The
request is a light to scan the list by.

**Options.**
- (a) **First data column, before or beside Code** (recommended): a 2 rem cell like the
  tick cell, no header text needed beyond a screen-reader label.
- (b) Keep it after Status for the desktop reading order.

### BR1-07 — minor (UX) — Scrapped rows should show no bulb

**Problem.** With *Show scrapped* on, a scrapped row gets green, "No open ticket", because
§ 3a leaves scrapped rows unchanged. Green reads as "this machine is fine".

**Why it matters.** The colour makes a claim about a machine that no longer exists.

**Options.**
- (a) **No bulb on a scrapped row** (recommended): the frontend renders the light only when
  `e.status !== "scrapped"`; the API value stays `none`. One `v-if`.
- (b) Grey dash with the text "Scrapped": a second meaning for the dash.

### BR1-08 — minor — The e2e tests must use their own machines and judge within a search

**Problem.** § 5's browser checks name "a breakdown on a machine", "a clean machine → green",
"*Down now* shows only the red row". The three Playwright projects share one database
(`equipment.spec.js` header), `screens.spec.js` raises a degraded ticket on `seed.extruder`
in `beforeAll`, and `tickets-raise.spec.js` raises on seed machines. A seed machine is never
reliably green, and the whole list holds other projects' red rows at the same time.

**Why it matters.** Tests written on seed machines pass alone and fail in the full run.

**Options.**
- (a) **Say it in § 5** (recommended): each test creates its machines through
  `createEquipment` (already in `equipment.spec.js`; names carry `testInfo.project.name`),
  raises through `raiseByApi("operator" or "engineer", …)` from `support/tickets.js`, opens
  `/equipment?q=<name prefix>` and judges the rows inside that search; the filter test
  checks the red row is listed and the amber and green ones are not, and the URL carries
  `tickets=down`.
- (b) Add dedicated seed machines in `seed_e2e.py` that no other spec touches: works, but
  a later spec can break it silently.

## Nits

- **BR1-09** (nit) § 5, the per-site test: with `X-Test-Role` a site role holds at every
  site, so "no `ticket:read` at the unit" needs `user_at_sites` (real memberships): one
  person, engineer at site A and storekeeper at site B → rows at A coloured, at B `null`,
  and `tickets=down` lists A's rows only. The "no `ticket:read` anywhere" case is
  `user_with_units("maint_storekeeper", [unit])` → every row `null`, `tickets=down` → empty.
- **BR1-10** (nit) § 1: the grey dash has no accessible text; give it one (e.g. "Tickets not
  shown") so the e2e tests and screen readers can tell it from an empty cell.
- **BR1-11** (nit) § 1, the filter's first choice: the other selects name what they cover
  ("All sites", "All statuses"); "All" alone does not. Use "All equipment", then *Down now*,
  *Any open ticket*.
- **BR1-12** (nit) § 2: drop "(EN 13306 clause numbers: to verify)" and cite the terms by
  name: EN 13306 *down state* (the item cannot perform because of a fault or because of
  maintenance) and *failure*; ISO 14224 *failure impact* (critical / degraded / incipient).
  Say in one line that red is the fault-caused down state only (see BR1-05). A wrong clause
  number is worse than none.
- **BR1-13** (nit) § 3: keep the three bulb texts in `ticketLabels.js`
  (`TICKET_LIGHT_LABELS`), as `StatusBadge` and `IntensityBadge` take theirs from the utils,
  so `ticketLabels.test.js` can assert them; `TicketLight.vue` then only renders.
- **BR1-14** (nit) § 1 *Out of scope*: say that *Print asset list* ignores the Tickets filter
  (`assetList.js` `FILTER_KEYS` passes only the shared filters), so nobody expects a "down
  now" printout.
- **BR1-15** (nit) § 3a *Permission*: the frontend's `userPermissions` is the union over the
  user's sites (`app.py auth_me` → `global_permissions()`), so a user with `ticket:read` at
  one site sees the column with dashes at the others. Correct; say it so the coder does not
  look for a per-site check in the view.

## Checked and found consistent

- **SQL semantics.** `EXISTS` over `tickets` with `t.equipment_id = e.id OR t.component_id
  = e.id`, red = `intensity = 'critical' AND state IN DOWN_STATES`, amber = any other
  `state <> 'closed'`, red before amber in a `CASE`; `ix_tickets_equipment_state` and
  `ix_tickets_component_state` exist in v20. A scrapped node cannot hold an open ticket
  through the API (S017 § 5.8, `_check_no_open_tickets`). The count query shares the
  conditions, so the pager is right. `scheduled` red matches `ticket_times`' downtime.
- **Unit access.** `user_unit_ids("ticket:read")` is valid (`ticket:read` is in
  `SITE_SCOPED`); IT admin and admin get `None` (`every_unit_by_token`: it_admin holds
  `ticket:read` and `equipment:read_all_units`); a manager with all units gets the site's
  active units; the storekeeper gets an empty set. The gate by the row's root unit matches
  `tickets._visible_condition`'s `m.unit_id` arm. Nothing new in `config_rbac.py`, so
  `test_role_matrix` is untouched.
- **Inputs.** `enum_arg("tickets", ("down", "open"))` refuses an empty value too
  (`api_common.py:146`), as the brief says; `tickets` is not in `_list_filters`, so
  `/asset-list` is unchanged.
- **Tests.** `conftest._TABLES` already clears `tickets` and `ticket_events`; `make_ticket`
  and `set_ticket_state` exist and work on parts (`TestScrapWithOpenTickets`); the existing
  `TestListing` and `TestUnitAccess` tests do not filter on `tickets` and keep passing.
- **Frontend.** `listUrl()` and `filterKey` take the new key with one line each; `hasFilters`
  and the empty state ("No equipment matches these filters.") follow; the label ticks clear
  on a filter change as today.
- **e2e conventions (S024).** Targeted spec `equipment.spec.js` plus `screens.spec.js`; test
  names start with `S029:`; `screens.spec.js` opens `/equipment` for every role, so the
  storekeeper's column-less list is covered there.
- **Manual checks.** None need a device; the three automated checks are things a browser can
  judge, so the split is right.
- **Standards.** TPM visual management (the andon reading) and ISO 14224 failure impact are
  the right references and are read correctly; EN 13306 as in BR1-12.
- **Out of scope and assumptions** are consistent with Plan.MD § 4.2 and § 6 ("equipment down
  now" is a dashboard item later; this is its first form on the list).
