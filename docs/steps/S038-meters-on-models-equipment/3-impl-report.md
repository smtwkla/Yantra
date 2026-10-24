```
Step: S038 — Meters on models and equipment
Doc: impl-report
Author: Coder (Opus)
Date: 24-10-2026
```

# S038 — Meters on models and equipment: implementation report

Meters on models and on nodes are built as briefed: migration v30, the pure core, the model and node routes, the meter type freeze, the two screens, and the docs pass. All four suites pass, and so do the targeted browser tests (123 passed). Nothing departs from the approved design, and there is no open question. Eleven small choices the brief did not cover are listed under *Decisions taken*.

## 1. What was built

- **Migration v30.** It adds `model_meters` and `node_meters`, as § 4 gives them, and appends `meter_added`, `meter_removed` and `meter_limits` to `equipment_events.event`.
- **A model's meters (Masters › Models).** Each model row, active or not, has a *Meters* button. It shows the model's meters in the panel, in place of the table, with "← Models" to go back.
  - Each meter shows its name, unit and kind, and what a good reading is ("Limits: 10–60 °C", "Expected: Yes").
  - Editors get *Add meter*, *Set limits* (gauges) and *Remove*. *Remove* asks first, with *Remove* / *Keep*.
- **A node's meters (the equipment page).** A *Meters* card sits after Details / Parts and before Notes. It lists the model's active meters ("From the model") and the node's own ("This machine only"), each with the limits in force.
  - Editors at the node's site get *Add meter*, *Set limits* on gauges, and *Remove* on own meters (asked first).
  - *Use the model's limits* is in the dialog's footer while an override exists.
- **History.** Each node write records one `equipment_events` line. The page shows "Meter added: …", "Meter removed: …" and "Meter limits: Oil temperature: 10–60 °C → up to 55 °C".
- **The freeze.** A meter type's kind, unit, decimals and expected answer cannot change once any model meter or node meter uses it, active or not (409). Name and active stay editable.
- **API.** The six routes of § 6.

## 2. How it works

- **Pure core, `meters_core.py`.** No database, no Flask.
  - `validate_limits(body, kind, decimals, stored)` works in this order:
    1. On a non-gauge, any non-null limit is refused with the kind's message. An explicit null passes.
    2. For a gauge, the body is merged over `stored`: an absent field keeps its value, and `null` clears it.
    3. Each limit is parsed: `None`, an int, or a decimal string through `Decimal`. A bool and a float are refused. Trailing zeros do not count as decimals. Anything beyond ±99,999,999,999.999 is refused.
    4. The merged pair is checked: Min must not be above Max (the message is on `max_value`).
  - `effective_meters(model_meters, node_rows)` gives the § 5.2 list:
    - an active model meter, with the node's override when there is one;
    - an active own meter whose type is not an active model meter;
    - nothing else.
    - `override_of` decides what overrides. An `own = 0` row is an override for as long as it exists. A row whose limits are both NULL then means "no limits on this machine". An `own = 1` row of a type the model gained later, active or not, overrides only while it holds a limit.
  - `limits_text` and `tracked_meter_change` are the one source of the wording. Numbers are shown without trailing zeros ("10", "62.5").
  - `parse_meter_type_id` and `parse_change_action` read the request body. A `PUT` with `active: false` removes, `use_model_limits: true` clears the override, and anything else sets limits.
- **Model meters, `masters.py`.**
  - Add: lock (4) the model with `_lock_row` (404; an inactive model is allowed) → (4b) the meter type (unknown 400, inactive 409) → the `model_meters` row by its unique key, `FOR UPDATE`. An active row is a 409. An inactive row comes back with the sent limits.
  - `PUT`: a plain read of the row's model id and type id (they never change), then the same order of locks. A removed row answers 404.
  - The freeze, `_check_meter_type_frozen`: under the meter type's lock, it runs only when a frozen field differs from the stored value. It counts `model_meters`, then `node_meters`, `LOCK IN SHARE MODE`.
- **Node meters, `meters.py`** (a new blueprint under `/api`, as `documents_bp`).
  - Every write takes (1) the node through `load_node_for_user(…, "equipment:edit")`, which gives 404 outside the user's units and 403 at another site. A scrapped node gets 409 `SCRAPPED_MESSAGE`, decided from the locked row.
  - Then (4b) the meter type, then the `node_meters` row `FOR UPDATE`. The model's meters are read plainly, with the model id from the locked node row.
  - *Set limits* on a model meter: `stored` is the pair in force. When the result equals the model's pair, an `own = 0` row is deleted, and an `own = 1` row keeps its place with both limits NULL. Otherwise the row is updated, or an `own = 0` row is inserted. A limits write never changes `active`.
  - *Remove* on an own meter sets `active = 0` and both limits to NULL. On a model meter it is a 409 with the brief's text.
  - The read needs `equipment:read` at the node's site.
- **Screens.**
  - `MeterFormFields.vue` holds the fields both dialogs share: the type select on add, with "Oil temperature (°C, Gauge)" options, and Min / Max with the unit for a gauge. When nothing is left to add, the select is replaced by the "Every meter type is on … already" text, and *Save* is disabled.
  - `ModelMeterFormModal.vue` and `NodeMeterFormModal.vue` each send their own request through `useFormModal().send`.
  - `MetersCard.vue` loads `/api/equipment/<id>/meters` itself. It reloads when the node or its model changes, and emits `changed` after a write so the page reloads the history.

## 3. Files touched

Backend:
- `backend/local_db.py`: migration v30.
- `backend/meters_core.py` (new): the pure rules and the wording.
- `backend/meters.py` (new): the node meter routes and the `uq_node_meters` message.
- `backend/masters.py`: the model meter routes, `read_model_meters`, `lock_meter_type`, `checked_limits`, the freeze, the `uq_model_meters` message, and the lock note in the docstring.
- `backend/equipment.py`: LOCK ORDER gains (4b) and a meters paragraph; `SCRAPPED_MESSAGE` is defined here and used by `update_equipment`; `_write_events` is renamed `write_events` (see *Decisions taken*).
- `backend/documents.py`: imports `SCRAPPED_MESSAGE` from `equipment.py`.
- `backend/app.py`: registers `meters_bp`.

Backend tests:
- `backend/tests/test_meters_core.py` (new): 69 tests.
- `backend/tests/test_meters_api.py` (new): the node routes.
- `backend/tests/test_models_api.py`: `TestModelMeters`.
- `backend/tests/test_meter_types_api.py`: `TestFrozenOnceUsed`.
- `backend/tests/test_migration_v30.py` (new): from v29, the event rows kept, the unique keys, the CHECKs, a re-run.
- `backend/tests/test_migration_v9.py`: the expected ENUM of the latest schema gains the three values, as v25 and v28 did before.
- `backend/tests/test_equipment_api.py`: the two monkeypatches follow the `write_events` rename.
- `backend/tests/conftest.py`: `node_meters` and `model_meters` lead `_TABLES`; a new `make_meter_type` fixture.

Frontend:
- `frontend/src/utils/meterLabels.js` (new): the kind labels, the source words, `expectedAnswerText`, `goodReadingText`, `meterTypeOption`, `unitAndKind`, `limitsBody`.
- `frontend/src/components/MeterFormFields.vue` (new): the shared dialog fields.
- `frontend/src/views/masters/ModelMeterFormModal.vue` (new).
- `frontend/src/views/masters/ModelsPanel.vue`: the *Meters* button and the in-panel meters view.
- `frontend/src/views/masters/MeterTypesPanel.vue` (S037): the kind labels come from `meterLabels.js`.
- `frontend/src/views/equipment/MetersCard.vue` (new) and `NodeMeterFormModal.vue` (new).
- `frontend/src/views/EquipmentDetailView.vue`: the card, before Notes.
- `frontend/src/utils/equipmentLabels.js`: `describeEvent` for the three events.
- `frontend/tests/meterLabels.test.js` (new) and `frontend/tests/equipmentLabels.test.js`.
- `frontend/e2e/masters.spec.js`: one test. `frontend/e2e/equipment.spec.js`: four tests and the `meterMachine` set-up helper.

Docs: see *Docs updated*.

## 4. Decisions taken

Eleven small choices, all forced. None changes the approved design.

1. **Numbers are shown without trailing zeros.** The API sends "10", not the column's "10.000", and the card reads "10–60 °C" as § 1.2 shows. A dialog fills the same strings, so a re-save never trips the decimals rule. For the same reason, "62.50" counts as 1 decimal.
2. **The decimals message names one decimal in the singular**: "Enter a number with up to 1 decimal". The brief's "up to N decimals" reads wrong for N = 1. The words are otherwise the brief's.
3. **An own meter added over a stale override.** Suppose a node holds an `own = 0` override of a type its current model no longer has, and the engineer adds that type as an own meter. The unique key allows one row, so the override row is deleted and an `own = 1` row is inserted. This keeps "own never changes after insert" (BR1-04). The case is not in the brief.
4. **`stored` for a node override is the pair in force**: the override if there is one, else the model's. This is § 5.1's own definition. It differs from "the row's own limits" only for an `own = 1` row with NULL limits under a model meter, where the model's limits are the ones in force.
5. **A removed model meter answers 404 to `PUT`**, and *Remove* of a meter that is neither from the model nor an active own meter answers 404. An add brings a removed meter back (BR1-18).
6. **The API texts for a wrong `PUT` mix** ("Add the meter again to bring it back", "Send the removal alone", "Only true is accepted here", "Send the model's limits alone") are not in the brief. The screens never send these mixes.
7. **A model meter has no *Remove* on the node card; the brief's help shows as a small line under it** (changed in fix round 1, CR1-03): "Comes from the model Atlas Copco GA37. Remove it in Masters › Models, or change this machine's model." Editors see the line. The brief gives the words but not where they show. The server's 409 for a direct call keeps the same text, as an API guard. The text uses the model's label (maker and designation).
8. **The card marks an override with "· set on this machine"**, and the node's *Set limits* dialog shows "Model default — Limits: 10–60 °C". These are new screen words, so the engineer sees the model's numbers before changing or clearing them.
9. **`MeterFormFields.vue`, a shared component.** The model and node dialogs have the same select and Min / Max fields. One component avoids a near-copy; the two named dialogs stay as the brief lists them. `limitsBody` (an empty box is sent as `null`) lives in `meterLabels.js` with the other meter helpers and has a unit test.
10. **`_write_events` is renamed `write_events`.** `meters.py` uses it, and the rule is not to import a private name across modules. The two test monkeypatches follow.
11. **`read_model_meters`, `lock_meter_type` and `checked_limits` live in `masters.py`.** `meters.py` imports them from there. `masters.py` cannot import `meters.py`, because `meters.py` imports `equipment.py`, which imports `masters.py`.

## 5. Not done, deferred or assumed

- **Out of scope:** readings and the last reading on the card (S039).
- **`test_rbac.py` is unchanged**: no new key.
- **No real-device checks** (§ 8: "None"), so `device-checks.md` has no new row.
- **Assumed:** an `own = 1` row that the model gained later cannot hold "no limits here" while the model has limits. Both NULL on such a row means "use the model's" (BR1-04), so the engineer gets the model's limits. A rare case (an own meter the model later gains, then set to no limits); not raised as a design gap.
- **A rename race:** a meter type renamed while a node write waits writes the name from the locked row, so the history is current. The card shows the new name on its next load.
- **The standards clause numbers** stay "to verify" (U4). No code or screen cites them.

## 6. Tests run

Final full run, `YANTRA_TEST_RUN=s038c1 tooling/run-tests.bat`:

| Suite | Result |
|---|---|
| backend | PASSED, 2713 passed, 119 s |
| frontend | PASSED, 149 passed, 25 s |
| deps | PASSED, 42 passed |
| tooling | PASSED, 115 passed |

- The first full run had one failure, `test_migration_v9.py::test_the_shape_holds`, which checks the latest ENUM. It was fixed (§ 3), and the second run above is green.
- `npx vite build` in `frontend/`: built in 4.13 s (the usual chunk-size warning only).
- **Targeted e2e**, 6 lanes, all three projects: `e2e/masters.spec.js`, `e2e/equipment.spec.js` and `e2e/screens.spec.js`, **123 passed** in 4.6 minutes.
  - masters and equipment are the screens this step changed; screens covers every route.
  - No shared frontend code changed (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store and `e2e/support/` are untouched), so the full suite was not run.
- Each new e2e test was first run alone on `desktop-chromium`, one lane: 5 passed at the first run.

## Manual checks

- [auto] **Important.** The engineer adds Oil temperature with limits 10–60 to a model: the in-panel view opens with "No meters.", the dialog fits, the row reads "Limits: 10–60 °C", and "← Models" brings the table back — `frontend/e2e/masters.spec.js::S038: engineer adds Oil temperature with limits to a model`
- [auto] The press page shows its model's meter ("From the model", "Limits: 10–60 °C") and an own counter ("This machine only", no limits line, no *Set limits*) — `frontend/e2e/equipment.spec.js::S038: the press page shows its model's meters and an own meter`
- [auto] **Important.** The engineer overrides Max to 55: the dialog fits, the card reads "Limits: 10–55 °C · set on this machine", and the history reads "Meter limits: Oil temperature: 10–60 °C → 10–55 °C". *Use the model's limits* then puts back 10–60, with the reverse history line — `frontend/e2e/equipment.spec.js::S038: engineer overrides a limit and the history shows it`
- [auto] Removing an own meter asks first (*Keep* cancels, *Remove* removes, and the history reads "Meter removed: Run hours"). A model meter's *Remove* shows where to remove it instead — `frontend/e2e/equipment.spec.js::S038: removing an own meter asks first`
- [auto] An operator sees the Meters card with its meters and no buttons — `frontend/e2e/equipment.spec.js::S038: an operator sees the Meters card without edit buttons`
- [auto] The Yes / No label "Expected: Yes" / "Expected: No" — `frontend/tests/meterLabels.test.js::a Yes / No meter's expected answer (BR3-01)` (vitest)

On a real device: none.

## Docs updated

- `docs/schema.md`:
  - the header line (v28–v30 by hand);
  - the `meter_types` row (the freeze);
  - new `model_meters` and `node_meters` rows;
  - the `equipment_events` row (the three events);
  - the planned `meters` row removed (built now);
  - the Mermaid overview: both entities and their four links.
- `docs/schema.html`, by hand (there is no generator):
  - the meta line ("Migration v30 … 32 tables, 45 links");
  - the Overview tab: both entities with their keyed columns, and the four links;
  - the Equipment tab: both tables with every column, the four links, and a note naming the meters.
- `docs/Plan.MD`: § 4.5 gains a "Built (S038)" bullet; § 4.1 gains "Meters on the equipment page".
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map reads "`masters` S016/S037/S038, `equipment` S003/S006/S012/S038".
- Fix round 1: none, because the changes touch only a watch, one button and one message text; no listed doc names them.
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`, `docs/steps/device-checks.md`: none. The step adds no maintenance rule, plant fact, role, secret or real-device check beyond what the brief and § 8 already record.

## Fix rounds

### Round 1

Fixes for `4-code-review-r1.md`. Run name `s038c2`.

- **CR1-01: held for the user (gate B).** Delete behaviour and its docs are unchanged.
- **CR1-02: Fixed.** `MetersCard.vue` now watches `[() => props.node.id, () => props.node.model_id]` as a multi-source watch, which compares each value. A page reload that replaces `node` no longer blanks the card or fetches the list again. New check in `equipment.spec.js::S038: engineer overrides a limit and the history shows it`: after the save, no extra `GET /api/equipment/<id>/meters`. Fails without the fix: `Expected length: 0, Received length: 1` (the extra GET); passes with it.
- **CR1-03: Fixed.** A model meter (`source === 'model'`) has no *Remove* button on the card. Editors see the help line under it, in small grey text. The inline "Close" variant and its branch are gone. The words live in the card; `backend/meters.py` keeps its 409 text for a direct API call (its test is unchanged). `equipment.spec.js::S038: removing an own meter asks first` now asserts no *Remove* button and the help line on the model meter. Decision 7 above is reworded.
- **CR1-04: Fixed.** `masters.py` now answers "This meter type is inactive. Pick another meter type." Tests updated in `test_meters_api.py::test_refusals` and `test_models_api.py` (the model meter refusal line).

Tests of round 1:

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s038c2 tooling/run-tests.bat` | ALL SUITES PASSED: backend 2713 passed (119 s), frontend 149, deps 42, tooling 115 |
| `npx vite build` | built in 3.96 s; the usual chunk-size warning only |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/masters.spec.js` (6 lanes) | 99 passed in 2.3 min |

Why these specs: only `MetersCard.vue` and the equipment and masters screens' tests changed; `screens.spec.js` was not needed (no route or shared code touched).

### Round 2

Fixes for `4-code-review-r2.md`. Run name `s038c3`.

- **CR2-01: no fix.** The reviewer's own run covered `screens.spec.js` and it passed. This round also runs it (below). Later rounds add `e2e/screens.spec.js` to every targeted run.
- **CR2-02: Fixed (red results given).**
  - CR1-03, `equipment.spec.js::S038: removing an own meter asks first`. I made the *Remove* button show for every source (removed `v-if="meter.source === 'node'"` at `MetersCard.vue:96`) and ran the test alone (desktop-chromium, one lane). It fails without the fix: `expect(locator).toHaveCount(expected) failed, Expected: 0, Received: 1` (the *Remove* button on the model meter). I restored the line exactly (the file was copied before the edit) and the test passes (1 passed). The old button was a real "Remove" button, so the `toHaveCount(0)` check does match what it must.
  - CR1-04, `test_meters_api.py::TestAddOwn::test_refusals` and `test_models_api.py::TestModelMeters::test_refusals`. I changed the message at `masters.py:890` to "Meter type is inactive" (a stand-in for the old words, which are not in git) and ran both. They fail without the fix: `At index 2 diff: 'Meter type is inactive' != 'This meter type is inactive. Pick another meter type.'`. I restored the line and both pass (11 passed with their neighbours).
- **CR2-03: Fixed.** The comment at `MetersCard.vue:24` now reads "the meter type whose Remove asks first".
- **CR2-04: Fixed.** The repeated History assertion in `equipment.spec.js` (after `expect(listCalls).toHaveLength(0)`) is deleted.
- **CR1-01: held for the user (gate B).** Unchanged.

Tests of round 2:

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s038c3 tooling/run-tests.bat` | ALL SUITES PASSED: backend 2713 passed (131 s), frontend 149, deps 42, tooling 115 |
| `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/screens.spec.js` (6 lanes) | 72 passed in 3.8 min |

Why these specs: `equipment.spec.js` is the spec I edited and the screen of `MetersCard.vue`; `screens.spec.js` runs with every targeted run. No shared frontend code changed, so the full suite is not needed. No frontend build was run: the only source change is a comment.

Docs updated: none, because this round changes a comment and a test only.
