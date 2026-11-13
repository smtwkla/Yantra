```
Step: S096 — PM plans on a machine
Doc: impl-report
Author: Coder (Opus)
Date: 02-11-2026
```

# S096 — implementation report

**Result:** R03.2 is built as briefed: migration v51 (`pm_plans`, `pm_plan_items`), the pure core
`pm_plans_core.py`, the blueprint `pm_plans.py` at `/api/pm`, the key `pm_plan:edit`, the PM card on the
equipment page, the plan page and the item dialog. All unit suites, the schema docs check, the targeted
browser run and the whole browser suite at Normal are green (numbers in § Tests). No departure from the
brief changes behaviour; the small choices are under § 4. `pm_schedule_core.py` (S095) is unchanged: S096
imports only its constants.

The report follows the brief's work order (§ 9, BR1-07): backend, backend tests, frontend, browser tests.

## 1. What was built

### Backend
- **Migration v51** (`backend/local_db.py`): the two tables exactly as § 4.1, with their keys, foreign keys
  and CHECKs. No precondition (new tables only).
- **`backend/pm_plans_core.py`** (new, pure): the field rules of a plan (`validate_plan`, phase 1) and of
  the merged plan (`plan_rules_error`, phase 2), the items (`validate_item`, `validate_items`,
  `validate_item_check`), the meter rule (`meter_choice_error`, `find_choice`), the sync of a sent item
  list (`sync_items`), the changed plan columns (`plan_changes`), and the words (`trigger_text`,
  `meter_label`, `item_limits_text`, `interval_number`, `calendar_message`), with every message of § 5.1
  and § 5.4.
- **`backend/pm_plans.py`** (new): the six routes of § 6 (`GET/POST /api/pm/plans`,
  `GET/PUT /api/pm/plans/<id>`, `GET /api/pm/meter-choices`, `POST /api/pm/item-check`), the answer
  builders, the meter choices (`meter_choices`) and the LOCK ORDER note of § 5.7.
- **`backend/meters.py`**: `meters_with_last(cur, nodes)`, the reading sheet's inner `meters_of` lifted out
  as a public function; `readings_sheet` now calls it (one copy, no change of behaviour).
- **`backend/config_rbac.py`**: `pm_plan:edit` → `("maint_engineer",)` with the brief's comment; in
  `SITE_SCOPED`.
- **`backend/contracts_core.py`**: `iso_date = _iso_date` (BR1-06).
- **`backend/app.py`**: the blueprint at `/api/pm`, after contracts.
- **`backend/equipment.py`**: docstring only: (6e) in the numbered lock list, and the pm_plans.py bullet
  after the contracts.py bullet (the brief's text).

### Frontend
- **`PmPlansCard.vue`** (new): the PM card (§ 5.8), after *Open tickets* (`order-0`).
- **`PmPlanView.vue`** (new): the plan page (§ 5.9) for a new and an existing plan, editable or read-only.
- **`PmItemDialog.vue`** (new): the item dialog (§ 5.10) on `FormModal` / `useFormModal`.
- **`utils/pmLabels.js`** (new, pure): the labels, `kindFromTicks`, the request bodies (`planBody`,
  `itemBody`, `savedItemBody`), the forms (`newPlanForm`, `planForm`, `blankItemForm`, `itemForm`),
  `moveItem`, `meterKey` / `meterIds`, `personLabel`, `planSubline`, `refusedItemNumber`.
- **Router**: `pm-plan-new` (`/equipment/:id/pm/new`) and `pm-plan` (`/equipment/pm/:id`), title *PM plan*.
- **`EquipmentDetailView.vue`**: the card after *Open tickets*; the phone-order comment names it.

## 2. How it works

**A create** (`POST /api/pm/plans`): `clean_body(validate_plan)` judges each field alone (an absent
required field is parsed as `None`, so its own text shows: "Enter a title.", "Tick By calendar or By meter,
or both.", "Add at least one item."; defaults: performer *maintenance*, verification by performer). In one
transaction: the node `LOCK IN SHARE MODE` (404), then `load_node_for_user` with `pm_plan:edit` (404 / 403
naming the site), scrapped (409, from the locked row). Then the meter choices (the node, its parent, its
grandparent, through `meters_with_last`, counters and gauges only), the plan's meter against them (a
counter, else "Choose a counter meter, such as run hours."), the assignee (`person_at_site` with an
`ASSIGNABLE_ROLES` role at the node's site, else `ASSIGNEE_AT_SITE`), `plan_rules_error` on the merged row
(the trigger's null-ness, the unit's maximum, the type's decimals, `meter_every` > 0, *Last done* ≤ the IST
date, no assignee on an operator plan), the items (`validate_items`, "Item 3: …"). Then the plan insert
(`uq_pm_plans_title` → 409 on `title`) and the item inserts at positions 1..n; the answer is read in the
transaction.

**A change** (`PUT`): (6e) the plan row `FOR UPDATE` (404), then the node shared, the access checks and
scrapped (also for `{active}` alone). `equipment_id` different from the stored one: 400. The merged row is
the locked row with the clean body over it. The meter is checked against the choices whenever a meter id is
sent (D10); a stored meter not sent keeps its type from `meter_types`, so `{active: false}` works on a plan
whose meter has gone. The assignee is checked whenever it is sent and not `null`. With `items`: a plain
read of the active items (after (6e), so the newest rows), `sync_items` (inserts, updates of the changed
fields and the position, deactivations; an unknown or repeated id → 400 "Item N …"). `plan_changes` writes
only the plan columns that differ, so a save of nothing writes nothing (`updated_at` stays NULL), for the
items too.

**The reads**: the card list takes the node and its parts two levels down (one query per level), the
active and the inactive plans, own plans first, each group by title, with the assignee's role at the node's
site (one `memberships` join), the item count, the trigger text and the meter label. The detail carries the
node's path, the items with `limits_text`, the writers' names and `can_edit` (the key at the node's site
and not scrapped).

**The item check** writes nothing: it reads the node (404 / 403) and its choices, runs `validate_item`
and answers the clean item in the detail's item shape, `id` as sent, so the dialog shows "Min must not be
above Max" beside *Max* at once (D2).

**The page** loads the node or the plan, then (editors only) the meter choices and
`GET /api/tickets/people`. Its form is the two cards' fields with the two ticks; *Save plan* sends
`planBody` (every field; `null` for an unticked trigger's fields and for an operator plan's assignee; the
items in their order with their ids) and goes back to the equipment page. A refusal sets `{field,
message}`: beside its field, or above the items list for `items` with the named row outlined, or at the top
for any other field; `revealError` scrolls to it. Unsaved changes are a snapshot of the form and the items:
*Cancel* then asks in place, and `FORM_DIRTY` is provided, so `ActiveToggle` blocks *Deactivate*. A stored
meter or assignee no longer among the choices is shown as the first option with its warning, before the
engineer types.

**The dialog** keeps the meter as one select value `"<equipment_id>:<meter_type_id>"`; choosing a gauge
fills Min and Max from its limits in force; a counter hides them; no meter shows *Unit*. *Save item* always
posts to the check route (never `save()`), and `afterSave` emits `done({item, index})`; the page puts a new
item at the end. *Remove item* asks in place and emits `remove(index)`.

## 3. Files touched

Backend (8):
- `backend/local_db.py` — migration v51.
- `backend/pm_plans_core.py` — new, the pure rules.
- `backend/pm_plans.py` — new, the blueprint.
- `backend/meters.py` — `meters_with_last`; `readings_sheet` uses it.
- `backend/contracts_core.py` — `iso_date`.
- `backend/app.py` — registers `pm_plans_bp`.
- `backend/config_rbac.py` — `pm_plan:edit` and `SITE_SCOPED`.
- `backend/equipment.py` — the LOCK ORDER note (docstring).

Backend tests (7):
- `backend/tests/test_pm_plans_core.py` — new, 123 tests.
- `backend/tests/test_pm_plans_api.py` — new, 47 tests.
- `backend/tests/test_migration_v51.py` — new, 22 tests.
- `backend/tests/test_migration_v50.py` — `V50` filtered to `<= 50` (BR1-01).
- `backend/tests/test_migration_squash_v41.py` — the versions assert over the later migrations (BR1-01).
- `backend/tests/test_rbac.py` — `test_role_matrix` rows and comment, `test_pm_plan_keys`.
- `backend/tests/conftest.py` — `pm_plan_items`, `pm_plans` first in `_TABLES`.

Frontend (9):
- `frontend/src/views/PmPlanView.vue` — new, the plan page.
- `frontend/src/views/equipment/PmItemDialog.vue` — new, the item dialog.
- `frontend/src/views/equipment/PmPlansCard.vue` — new, the PM card.
- `frontend/src/views/EquipmentDetailView.vue` — the card, and its phone-order comment.
- `frontend/src/router/index.js` — two routes.
- `frontend/src/utils/pmLabels.js` — new, labels and bodies.
- `frontend/tests/pmLabels.test.js` — new, 17 tests.
- `frontend/e2e/pm-plans.spec.js` — new, 9 tests.
- `frontend/e2e/screens.spec.js` — the plan page and the new-plan page.

Docs: listed under § Docs updated.

## 4. Decisions taken

- **`validate_item_check` in the core** (an extra public function beside the brief's list): the check
  route's body is the item plus `equipment_id`, and the node must be read before the item can be judged, so
  the validator for `clean_body` parses only `equipment_id` and passes the item on. Keeps the route on
  `clean_body` (its "Request body must be a JSON object" 400) with no copy of it.
- **`plan_changes(stored, clean)` and `find_choice` in the core**: the field comparison by value (a stored
  `Decimal("250.000")` equals a sent `Decimal("250")`) is shared by the plan and `sync_items`, so it is one
  pure helper (`_same`) used by both.
- **`calendar_every` in phase 1**: refused when not a whole number ≥ 1 (a boolean, a string, 0); its message
  names the sent unit's maximum, or the month's (120) when a hand-made `PUT` sends no unit. The maximum
  itself is judged on the merged pair (§ 5.1). The screen always sends both.
- **Both meter ids refuse on `meter_type_id`**, also a bad `meter_equipment_id`: the screen has one meter
  select (the brief names `meter_type_id` as the field).
- **A meter sent on a calendar plan** (a hand-made request) is not looked up in the choices: the merged rule
  answers "Clear the meter fields for a calendar plan." instead of a choice error. The screen sends `null`.
- **Item ids on a create** are not used: every item of a new plan is inserted (a hand-made request with ids
  gets new rows, nothing else).
- **`item_limits_text(item, meter_type=None, meter_code=None)`**: the meter's node code is a third argument
  (the brief's two-argument signature cannot name "· HP003"). An item with a counter meter and no limits
  reads "logs Run hours · HP003".
- **`planBody(form, items, equipmentId)`**: a third argument, the node's id, since the form holds no
  equipment field. A `PUT` sends it too (equal to the stored one: no change, § 5.1).
- **The person label** follows the Raise ticket page: "Kannan (Technician)", the role from `roleLabel`; a
  contractor adds "· Atlas Copco". The brief's example writes the role in lower case; the app's one
  person-with-role label is kept (scope B: same words in the whole app).
- **The card's small line** is one line: "Run hours · HP003 · 7 items · Kannan (Technician)"; "1 item" in
  the singular. The header counts the active plans ("PM plans (0)" for an editor with only inactive ones).
- **The page's read-only view** shows the trigger text, the meter label and *Last done* ("02-10-2026 at
  1,840.0 h", or "Not known") instead of the two tick lines.
- **`equipment.py`'s numbered lock list** also gains a `(6e)` line, so the number the new bullet uses is
  defined there.
- **`docs/schema.md`**: its "All foreign keys are RESTRICT today (75 of 75)" was stale before S096 (81 at
  v50); it now reads "88 of 88, at v51".
- **The *Last done* meter field** is labelled *Meter then*, with the unit after it (the brief names no
  label).

No departure from the brief's rules, routes, keys or texts.

## 5. Not done, deferred or assumed

- Nothing of the brief is left out. Out of scope as briefed: jobs, the next-due line, templates, CIL,
  before-use plans on the screen, photos enforced.
- **Assumed:** the e2e seed's people names already carry their role ("Kannan (technician)"), so the
  assignee options read "Kannan (technician) (Technician)" in the browser tests only; real Team names
  carry no role.
- **Existing specs** (§ 8.3): no line of `equipment.spec.js`, `lessons.spec.js`, `contracts.spec.js` or
  `readings.spec.js` changed; the whole suite at Normal is green with the new card on every machine page
  for engineers and managers.
- **`pm_schedule_core.py`**: unchanged; S096 needed nothing more from it.

## Tests

Run name `YANTRA_TEST_RUN=s096c1`.

- **Core first, red then green:** `test_pm_plans_core.py` was written first and failed (ImportError: no
  module yet), then passed once the core was written: 123 passed.
- **Targeted while coding:** `test_pm_plans_api.py` 47 passed; `test_migration_v51.py` 22 passed; the
  v50, squash, rbac and modules tests 120 passed; readings, meters, modules, auth, contracts core and
  S095's core 415 passed; `pmLabels.test.js` 17 passed; `npx vite build` built (the usual chunk-size warning
  only).
- **All unit suites** (`tooling/run-tests.bat`): the first run was red on the tooling suite's line-width
  test (two lines over 120: `conftest.py:186` and `test_migration_v51.py:161`). After wrapping them and
  running the targeted tests again, the second full run was green: **backend 4801 passed, frontend 429
  passed, tooling 239 passed**. S092's known flaky test did not fail.
- **Schema docs:** `tooling\schema-docs.bat write` built v51 (4 passed); `check` exits 0 (4 passed).
- **Browser, the new spec alone** (`E2E_LANES=1`, `phone-chromium`, `-g S096`): the first run had 2
  failures. The two refusal tests had not allowed their expected 400. After adding
  `allowFailedRequest`, **9 passed**.
- **Browser, targeted** (`e2e/pm-plans.spec.js e2e/equipment.spec.js e2e/screens.spec.js`, Normal; the
  changed screens, the equipment page that holds the card, and the screens list): **80 passed, 2
  skipped**.
- **Browser, the whole suite at Normal** (`tooling/run-e2e-tests.bat`, once, at the end; the router is a
  shared file): **385 passed, 15 skipped, 0 failed**, all lanes done in 193 s. No change to `api.js` or
  `e2e/support/`, so no extra WebKit run.

## Manual checks

The brief's § 8.5 has no real-device check; every check is automated.

- [auto] **important** The engineer writes a PM plan and sees it on the PM card — `frontend/e2e/pm-plans.spec.js::S096: the engineer writes a PM plan and sees it on the PM card`
- [auto] **important** The plan page refuses an empty save beside the fields — `frontend/e2e/pm-plans.spec.js::S096: the plan page refuses an empty save beside the fields`
- [auto] **important** A reading with Min above Max is refused in the item dialog — `frontend/e2e/pm-plans.spec.js::S096: a reading with Min above Max is refused in the item dialog`
- [auto] The engineer edits a plan: moves an item up, removes one, and the card shows the new order and count — `frontend/e2e/pm-plans.spec.js::S096: the engineer edits a plan: moves an item up, removes one, and the card shows the new order and count`
- [auto] **important** A deactivated plan leaves the card and shows under Inactive plans — `frontend/e2e/pm-plans.spec.js::S096: a deactivated plan leaves the card and shows under Inactive plans`
- [auto] **important** The technician and IT admin read the plan but cannot change it — `frontend/e2e/pm-plans.spec.js::S096: the technician and IT admin read the plan but cannot change it`
- [auto] A machine with no counter meter says why By meter cannot be ticked — `frontend/e2e/pm-plans.spec.js::S096: a machine with no counter meter says why By meter cannot be ticked`
- [auto] A part's plan may count its machine's run hours — `frontend/e2e/pm-plans.spec.js::S096: a part's plan may count its machine's run hours`
- [auto] The plan page fits a phone with no sideways scroll (`@device`) — `frontend/e2e/pm-plans.spec.js::S096: the plan page fits a phone with no sideways scroll`
- [auto] The plan page and the new-plan page open for their roles — `frontend/e2e/screens.spec.js::every screen opens as <role>`

## Docs updated

- `docs/schema/notes.json` — the area *Preventive maintenance*; `pm_plans` and `pm_plan_items` moved from
  `planned` to `tables` (the `pm_plans` line without *kind (PM / CIL)* and *source template*, BR1-09).
- `docs/schema/schema.json`, `docs/schema/schema-data.js` — generated by `tooling\schema-docs.bat write`
  (v51; `git diff docs/schema/` read: the two tables, the area, the migration number).
- `docs/schema.md` — the foreign-key count (88 of 88).
- `docs/Plan.MD` — § 3: the `pm_plan:edit` paragraph; § 4.3: *Built (S096)* under *PM plan*, and the
  per-plan "Photo required" line marked superseded. The calendar's *years* was already in § 4.3 (S095).
- `.claude/CLAUDE.md` — § Step workflow, *Self-check, repo items* (2): `pm_plans.py` and (6e); § SMTW-Review:
  the *PM plans (S096)* point of § 8.6.
- `docs/steps/device-checks.md` — none: no real-device check (§ 8.5).
- `docs/Keycloak.md` — none: no Keycloak role changes.
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md` — none: no new rule or plant fact.

## Feedback

- waste: the full unit run went red only on two long lines, and the rule then asked for a second full
  run (about 2.5 min each). The line-width check could also run in the targeted tooling suite, but
  nothing said to run it before the full run (`scratch/s096-unit-all.txt`, first run).
- hindrance: the e2e console guard fails a test on an expected 400 unless `allowFailedRequest` is named.
  The *Browser tests* setting mentions "allowed 400s" but not the call, so I found it only from the
  failed run (`frontend/e2e/support/console.js`; 1 extra run, 1 min).
- idea: a backgrounded `run-tests.bat` cannot be awaited without a Monitor or an `until grep` loop. A
  `tooling` wrapper flag that blocks until the summary line exists would save tool calls (3 calls in this
  run).

## Fix round 1

### Round 1

- **CR1-01 (minor): Fixed.** On `/equipment/<id>/pm/new` a scrapped node now sets `forbidden` and stops the load, so the page shows the 403 text "You can't add PM plans here." with *Back to the equipment*. `canEdit` is then always true on a new plan. Test: `pm-plans.spec.js::S096 CR1-01: a new plan on a scrapped machine says it cannot be added`. Fails without the fix (the text is not found); passes with it.
- **CR1-02 (nit): Fixed.** `test_pm_plans_api.py::TestChange::test_a_meter_removed_from_the_node_is_refused_when_sent_again`: a plan's own meter is removed, a `PUT` that sends it gets 400 on `meter_type_id` (`METER_FROM_LIST`), and `{active: false}` alone still passes. The test only pins a rule the code already had, so no red run is possible; it passes.
- **CR1-03 (nit): Fixed.** The label *Meter then* is now *Meter reading then* (`PmPlanView.vue`). No test used the old label (they use *Last done* and the meter by role), so none changed.
- **CR1-04 (nit): Fixed.** `PmPlanView.vue` marks a reading item whose meter is no longer a choice when the page loads: an alert above the list ("Item 1: the meter is no longer on this machine. Open the item and choose another meter.", `data-testid="pm-lost-item-meter"`) and the row outlined, like a refused row. Only for editors. Test: `pm-plans.spec.js::S096 CR1-04: a reading item whose meter was removed is marked when the page loads`. Fails without the fix (alert not found); passes with it.

Tests (`YANTRA_TEST_RUN=s096f1`):

- Backend, the changed module: `test_pm_plans_api.py` 48 passed.
- Frontend unit suite: 429 passed. `npx vite build`: built.
- Browser, targeted (`pm-plans.spec.js`, `screens.spec.js`, Normal): 29 passed, 1 skipped, 0 failed.

Docs updated: none, because the round changes one page's texts and guards only.

### Feedback

- none

## Verify review r2 (02-11-2026)

- CR2-01 (nit): the CR1-04 browser test now closes its admin API connection (`api.dispose()` in a `finally`), fixed by the orchestrator after the gate B snapshot, so the fix lands in S097's snapshot (step skill § Async verify review). `E2E_LANES=1 tooling/run-e2e-tests.bat e2e/pm-plans.spec.js --project=phone-chromium -g CR1-04`: 1 passed.
