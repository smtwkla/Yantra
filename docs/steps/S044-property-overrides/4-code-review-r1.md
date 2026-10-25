```
Step: S044 — Property overrides on equipment items
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding (a Masters help line still says only models hold values) and one nit.

Reviewed: the working tree against `refs/steps/S046` plus the untracked S044 files. I ignored `tooling/e2e/run_lanes.py` and `tooling/tests/test_run_lanes.py`, as the orchestrator asked. I read `item_properties.py`, `ItemPropertiesModal.vue`, `test_item_properties_api.py` and `test_migration_v33.py` in full. I read every hunk of `properties.py`, `properties_core.py`, `local_db.py`, `equipment.py`, `app.py`, `PropertyInput.vue`, `EquipmentDetailView.vue`, `equipmentLabels.js`, the tests and the docs, and the code around each hunk.

## Tests run

- **Backend** (`YANTRA_TEST_RUN=s044cr1 tooling/run-backend-tests.bat`): **PASSED, 3012 passed** in 77 s. Migration v33 applied in the run. The run finished before another agent's `taskkill`: its log `scratch/backend-tests-s044cr1.log` ends with the summary line.
- **Frontend** (`tooling/run-frontend-tests.bat`): **PASSED, 169 passed**.
- **Build** (`npx vite build` in `frontend/`): built, with only the existing chunk-size warning.
- **Deps and tooling suites:** not run, as the orchestrator asked, because another coder was editing `run_lanes.py`. The coder's run had them green (42 and 129).
- **Browser tests:** not repeated (standing rule 25-10-2026). The coder's run is the right target set: `equipment.spec.js` (the changed screen), `masters.spec.js` (the freeze and `PropertyInput` with no `hint`) and `screens.spec.js`. No shared frontend code changed (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store and `e2e/support/` are untouched), so the full suite is not due. Result: 170 passed, 1 skipped (the desktop skip of the S040 bottom-bar test), 0 failed, on the three projects. None of my findings needs a re-run.

## Findings

### CR1-01 — minor — the Masters property dialog still says only models hold values

**Where.** `frontend/src/views/masters/PropertiesPanel.vue:220`:
`<div v-if="unitFixed" class="form-text">Models hold values of this property, so its unit is fixed.</div>`

**Problem.** `unitFixed` reads `value_count`, which now counts the items' own values too (`properties.py:57-61`, S044 § 1.6). The backend refusal was reworded to "the property has values" (BR1-08). This help line was not reworded.

**Failure scenario.**
1. An engineer types 5.5 kW on one motor's *Edit this machine's values*. No model holds a value of *Rated power*.
2. The keeper opens the property in *Masters › Properties*.
3. The unit field is greyed out with "Models hold values of this property". The keeper checks the models and finds none, so the screen points the keeper to the wrong place.

The data-type line above it (line 213, "has options or values") is already right.

**Fix.** Reword line 220 to match `UNIT_FIXED`, e.g. "This property has values, so its unit is fixed." The masters e2e spec does not assert this text, so no test changes.

## Nits

- **CR1-02** (nit) `frontend/src/utils/equipmentLabels.js:56` (`secondSide`): the function cuts at the old side's first ": ". A property named with ": " in it (for example "Power: rated") loses part of its name on the new side. If names may hold a colon, cut by the name length instead, or refuse ": " in property names. This is cosmetic: the stored event texts are complete.

## Specific checks the orchestrator asked for

- **Migration v33.**
  - It is append-only: a new entry at the end of `_MIGRATIONS`, and `LATEST_VERSION` follows it.
  - It creates `equipment_property_values` with the v31 value columns, the CHECK, the composite option FK and the PK `(equipment_id, property_id)`. It adds `'property'` at the end of the `equipment_events.event` ENUM.
  - No `_PRECONDITIONS` entry is needed. A new table and an ENUM widened at its end change no existing row. `test_a_v32_database_with_equipment_keeps_every_row` proves this: every old table's rows are equal before and after, and every column except `event` is unchanged.
  - The re-run test deletes the version row and migrates again. The schema and the rows stay the same.
  - The CHECK, both FKs and the ENUM refusal are each tested (`test_the_database_keeps_one_value_and_the_option_s_property`).
- **Schema docs.**
  - `schema.md` has the table row, the `property` event, the Mermaid overview with its three links, and the line "migration v33".
  - `schema.html` has the header (v33, 38 tables, 56 links). The Overview tab shows the keyed columns. The Equipment tab shows every column, the three links and the tab note. I parsed the `TABS` JSON to check this.
- **The v33 "Rollback:" comment** (departure 1). The coder's text is right and the brief's was not. A rolled-back backend reads the ENUM value as a string. The old `describeEvent` then falls through to `String(event.event)` and shows "property", as v30's comment says of the meter events. The departure is justified and reported.
- **Locks.**
  - The item write takes (1) the node, `FOR UPDATE`, through `load_node_for_user` with `equipment:edit`. It refuses a scrapped item from the locked row.
  - It then takes (2) the named properties, ascending, `FOR UPDATE`. Then (3): the links for the locked row's class, the options, and the model's value rows for the found ids, all `LOCK IN SHARE MODE`. Last come (4) the own rows and the events.
  - I traced the cycle cases: the model save, `update_property` (the share reads of both value tables, next-key on the `property_id` index), `update_option`, the class-link remove, and node edits. None of them takes a property row and then an equipment row. No path waits on the item write while it holds something that the item write then needs. The notes in `item_properties.py`, `equipment.py` and `properties.py` agree with the code.
  - The plain read of the own rows after (1) is safe. Every writer of those rows holds the node lock, and the read view is made at `_read_node`, after the lock.
- **Shared helpers and the model write** (departure 3).
  - `set_model_properties` calls `values_from_body`, `lock_value_properties`, `checked_changes` and `write_values`.
  - The SQL, its order and the refusals are the same as before. The one change is the extra `unit` column in the locking read.
  - The S043 model tests are green in my run.
  - The table and owner-column names in the f-strings come only from code constants. Every value is a bound parameter.
- **`model_values` made public with `property_ids` and `lock`** (departure 2). It avoids a second copy of the query. The detail and the GET call it with no lock.
- **Permissions.**
  - `equipment:read` and `equipment:edit` are both in `SITE_SCOPED`.
  - The GET checks `equipment:read` at the node's site, the same form as `list_node_meters`. The PUT checks `equipment:edit` at the node's site through `require_perm_at`.
  - A node the user cannot see is a 404. An operator and an engineer of another site get 403. All of these are tested.
  - The actor comes from `actor()`, never from the body. The 503 path is tested.
- **The `property` event** (BR2-01).
  - `item_events(properties, changes, before, model_displays, option_labels, has_model)` gets the unit from the locking read. It gets the option labels from the options it share-read, and the model's displays from the share-read value rows.
  - The API tests assert the texts exactly: "7.5 kW (model)", "no value (model)", "no value", an option label, a change and a clear.
  - `describeEvent` gives "Property: <name>: 7.5 kW (model) → 5.5 kW". The vitest test and the e2e test both assert this line.
- **`item_changes`.**
  - Number equality uses `Decimal` ("7.50" equals 7.5000). Text, yes/no and the option id are compared exactly.
  - The full-body test shows that the dialog's unchanged rows write nothing.
  - A value equal to the model's is stored as the item's own (decision 3) and is tested.
- **The other departures.**
  - Item 4, the 400 on a non-object body, is S043's behaviour.
  - Item 5, the `value_display` and `option_labels` helpers, is DRY.
  - Item 6, `has_model` on each row, is listed in § 5.5.
  - Item 7, the empty-state text "The class has no properties now. Reload the page.", is scope B and shows only after a race.
  - Item 8, the PUT answer from the node read after the lock, is correct.
  - Each departure is reported with its reason, and none goes beyond the brief.
- **UI.**
  - The dialog is a `FormModal` (`modal-dialog-scrollable`, fixed footer), and every S044 e2e test calls `expectDialogFits` on it.
  - The two `btn-sm` buttons sit in a `d-flex flex-wrap gap-2` group, with *Edit this machine's values* first (BR2-07).
  - The "· this machine" mark appears only with a model (BR1-06).
  - The hint comes after `invalid-feedback`, so a refusal stays beside its field (BR2-06). `ModelPropertiesModal.vue` passes no hint.
  - The screen texts follow scope B, and the button starts with a verb.
- **Docs pass.**
  - `Plan.MD` § 4.1 says S044 is built.
  - The `Maintenance-Philosophy.md` glossary entry *Property* is extended.
  - The spec map in `.claude/CLAUDE.md` § SMTW-Review now has `equipment` … S044.
  - The schema docs are covered above.
  - `device-checks.md`, `example_secrets_app.py` and `Keycloak.md` need no change, and the report says why for each.
  - The one gap is the frontend help line in CR1-01, which is screen text, not a listed doc.

## Manual checks

- The impl report's `## Manual checks` carries all five automated checks of § 8.4 as `[auto]`, each with its test. The important one is first.
- I read each test. Each asserts what the user sees: the title, the hint, the card's value with its mark, the line under the rows, the history line, the absent buttons, and the refusal beside its field. None only opens a page.
- The brief has no real-device check (§ 8.5), and none is due from the code. **Nothing is left for the user's manual browser check.**

## Checked and found consistent

- Scope: everything in brief § 1 and § 3 is built, and nothing outside it. The model and class change rules (§ 1.7) are tested in all three forms, including a model of another class.
- Edge cases:
  - An empty `values` object answers 200 and saves nothing.
  - A clear with no own row writes nothing.
  - Unknown, inactive and unlinked ids each get `NOT_ON_CLASS`. The first refusal is by name, and nothing is saved.
  - An inactive stored option may stay.
  - A scrapped item answers 409 on PUT and is still readable on GET.
  - A property with only a hidden item value still freezes its type and unit and counts in `value_count`.
- Layering: the rules are in the pure `properties_core.py` (`check_values`, `item_changes`, `item_events`, `value_display`, `property_view`). The routes are a thin shell. The Vue code only shows what the API returns; the mark and the line under the rows depend only on `source` and `model_id`.
- Import direction: `item_properties.py` imports from `equipment.py` and `properties.py`, and neither of them imports it. `properties.py` imports nothing from `equipment.py`.
- `conftest._TABLES` has `equipment_property_values` before `equipment`, and `test_migration_v9` expects `property` at the end of the ENUM.
- Length: the longest event side is 80 + 2 + 100 + 8 = 190, within `VARCHAR(200)`. An option label (≤ 60) and a number with its unit (≤ 39) are shorter.
- The impl report follows scope A, and its tests section gives the red runs for the core and the history line.
- The README index row reads "In code review".
