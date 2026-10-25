```
Step: S044 — Property overrides on equipment items
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S044 — Implementation report

**Result.** S044 is built as the approved brief says, with the review answers BR1 and BR2 applied (BR2-01's `item_events` signature included). An equipment item can now hold its own value of a property. Its own value wins over its model's on that item only, and each set, change and clear writes a `property` line in the item's history. Migration **v33** adds `equipment_property_values`. All four suites are green, and so are the targeted browser specs on the three projects (numbers in § 6). The brief needs no new decision. One wording departure, the v33 "Rollback:" comment, is explained in § 4 item 1.

## 1. What was built

- **An item's own value** of each active property of its class: one row per item and property in `equipment_property_values` (v33). The values are checked by the same rules as a model's (`check_values`, renamed from `check_model_values`).
- **The Properties card** on the equipment page shows the value in force: the item's own value, else the model's, else "—".
  - On an item with a model, an own value carries "· this machine" in small grey text. On a model-less component-unit every value is its own, so no mark shows (BR1-06).
  - The line under the rows reads "Values from model <model>." as before. When at least one row is marked, it reads "Values from model <model>, except those marked this machine.". A model-less item has no line.
- **Edit this machine's values**: a button on the card for `equipment:edit` at the item's site (`canEdit`), hidden on a scrapped item and while the page loads. It comes first; *Edit model values* stays second (BR2-07). The two `btn-sm` buttons sit in a `flex-wrap` group, so on a phone they wrap.
- **The dialog** `ItemPropertiesModal.vue`, titled "This machine's values — <code>". It holds one `PropertyInput` per row of the card. Each input starts at the item's own value, or empty. Under each input a grey hint gives the model's value: "Model: 7.5 kW" or "Model: no value". A model-less item gets no hint. *Save values* sends every row; emptying an input clears the own value.
- **History**: one `property` event per real change, by property name. Example: "Property: Rated power: 7.5 kW (model) → 5.5 kW". The side with no own value shows the model's value then in force, marked "(model)". It reads "no value (model)" when the model has none, and "no value" on a model-less item.
- **The Masters freeze** counts item values too. A property with any item value (even a hidden one) keeps its data type and unit, and `value_count` counts item values. The two refusal texts are reworded (BR1-08).
- **Model and class changes** leave own values alone. A value of a property the new class lacks is hidden, not deleted, and shows again when the property is linked again.

## 2. How it works

### Backend

- **`properties_core.py` (pure).**
  - `check_values` is `check_model_values` renamed, with the same checks in the same order. Its docstring now covers a model's or an item's save (BR1-10).
  - `value_display(prop, row, option_labels)` formats a stored value row for reading, by `format_value`. `property_view`, `item_events` and the write's model displays all use it.
  - `property_view(..., item_values=None)`: the item's row wins (`source` "item"), else the model's ("model"), else None. An own value of a property not on the class is not given, so it is not shown.
  - `item_changes(changes, stored)` drops two kinds of entry: a clear of a property with no own row, and a value equal to the own one. Equality is checked per column: a number as `Decimal` (5.5 equals 5.5000), text exactly, yes/no as 0/1, a choice by option id (BR1-02).
  - `item_events(properties, changes, before, model_displays, option_labels, has_model)` writes the triples of § 5.4 (BR2-01).
  - The freeze texts are reworded. The name order of the checks, the card's rows and the history lines is one helper, `_by_name`.
- **`properties.py` (shell, shared).**
  - Three names are now public (BR2-02): `options_by_property`, `linked_properties` and `model_values` (the last was `_model_values`; see § 4). `model_values` takes optional `property_ids` and `lock`.
  - New public helpers: `item_values(cur, node_id)` and `option_labels(options)`.
  - The values-save steps that the model route and the item route share are four public helpers: `values_from_body()`, `lock_value_properties()`, `checked_changes()` and `write_values()`. `set_model_properties` now calls them, and its behaviour is unchanged.
  - `equipment_properties(cur, class_id, model_id, node_id)` adds the item's own values: one extra query (`item_values`), not one per row.
  - `update_property`'s `has_values` also share-reads `equipment_property_values`, and `_PROPERTY_SELECT`'s `value_count` adds the item rows.
  - The docstring points at `item_properties.py`. The module still imports nothing from `equipment.py`.
- **`item_properties.py` (new, BR1-01).**
  - `GET /api/equipment/<id>/properties` checks `load_node_for_user(..., key="equipment:read")` (BR2-03) and works on a scrapped item. It returns the dialog's rows: `property_id`, `name`, `data_type`, `unit`, `options` (active ones plus the stored inactive one), `value` (the item's own or null), `model_display` and `has_model` (BR1-13).
  - `PUT` takes the locks in order:
    1. the node (1), `FOR UPDATE`; 404, then 403 without `equipment:edit` at its site, then 409 if scrapped (decided from the locked row);
    2. the named properties (2), ascending, `FOR UPDATE`, reading `unit` too;
    3. the class links for the locked row's class and the options, `LOCK IN SHARE MODE`; then the model's value rows for those ids, `LOCK IN SHARE MODE` (BR2-04).

    Then it reads the item's own rows plainly (every writer of them holds (1)). The changes go through `check_values`, then `item_changes`. The kept changes are upserted or deleted, then written as events through equipment.py's `write_events`.
  - The module docstring holds the LOCK ORDER note and says why no cycle forms. `equipment.py`'s properties bullet names this write.
- **`app.py`** registers `item_properties_bp` at `/api`, beside `meters_bp`.
- **`equipment.py`**: the detail passes the node's id to `equipment_properties`; the LOCK ORDER note gains the item write.
- **`local_db.py`**: v33 creates `equipment_property_values` (the v31 value columns, CHECK and composite option FK, keyed `(equipment_id, property_id)`). It also widens `equipment_events.event` with `'property'` at the end. It has no `_PRECONDITIONS` entry, because no existing row changes. `CREATE TABLE IF NOT EXISTS` and the identical `MODIFY` make a re-run safe. The comment has a "Rollback:" line (BR1-09).

### Frontend

- `PropertyInput.vue` gains a `hint` prop: a `div.form-text` after the `invalid-feedback` line, so a refusal stays beside its field (BR1-05, BR2-06). `ModelPropertiesModal.vue` passes none, so it is unchanged.
- `ItemPropertiesModal.vue` follows `ModelPropertiesModal.vue`: it is built on `useFormModal` and `FormModal`, keyed `values.<property_id>`, and fetches before it opens. A failed fetch rejects, and the card shows the message in `propertiesError` (§ 5.6).
- `EquipmentDetailView.vue` adds the mark, the line, the button and the dialog. Both dialog openers share one error wrapper, `openPropertiesDialog`.
- `equipmentLabels.js` renames `limitsOnly` to `secondSide`. It is used by the meter-limits line (same text) and by the new `property` line (BR1-04). The header names S044 (BR1-15).

## 3. Files touched

Backend (10):
- `backend/properties_core.py`: `check_values` (renamed), `value_display`, `property_view` with item values, `item_changes`, `item_events`, `_by_name`, the reworded freeze texts.
- `backend/properties.py`: public `options_by_property`, `linked_properties`, `model_values`; new `item_values`, `option_labels`; the shared values-save helpers; `equipment_properties` with `node_id`; the freeze and `value_count` count item values; the docstring.
- `backend/item_properties.py` (new): the GET and PUT routes, `_item_properties`, the LOCK ORDER note.
- `backend/app.py`: registers `item_properties_bp`.
- `backend/equipment.py`: the detail passes `node["id"]`; the LOCK ORDER bullet.
- `backend/local_db.py`: migration v33.
- `backend/tests/test_properties_core.py`: the rename; clear by null; `item_changes`, `property_view` with item values, `item_events`.
- `backend/tests/test_item_properties_api.py` (new): 29 tests of the two routes (§ 8.2).
- `backend/tests/test_properties_api.py`: the freeze with an item value (hidden too), `value_count`, the new texts.
- `backend/tests/test_migration_v33.py` (new): fresh database, CHECK and FKs, upgrade from v32, re-run.
- `backend/tests/test_migration_v9.py`: the ENUM ends with `property`.
- `backend/tests/conftest.py`: `equipment_property_values` in `_TABLES`, before `equipment` (BR1-11).

Frontend (6):
- `frontend/src/views/equipment/ItemPropertiesModal.vue` (new): the dialog.
- `frontend/src/components/PropertyInput.vue`: the `hint` prop.
- `frontend/src/views/EquipmentDetailView.vue`: the mark, the line, the button, the dialog.
- `frontend/src/utils/equipmentLabels.js`: `secondSide`, the `property` line, the header.
- `frontend/tests/equipmentLabels.test.js`: the `property` line.
- `frontend/e2e/equipment.spec.js`: five S044 tests, added at the end; no existing line changed.

Docs (6): `docs/schema.md`, `docs/schema.html`, `docs/Plan.MD`, `docs/Maintenance-Philosophy.md`, `.claude/CLAUDE.md`, and the step files (`1-brief.md` status, the README index row, this report).

## 4. Decisions taken

1. **The v33 "Rollback:" line differs from the brief's wording (flagged).** Brief § 4 says the previous release "cannot show a `property` event (an unknown ENUM value fails its history read)". That is not what happens. A rollback leaves the database at v33, so the column still holds the value and the old backend reads it as a plain string. The old frontend's `describeEvent` then shows an unknown event by its raw name ("property"), as v30's comment already says of the meter events. The comment says so: the previous release ignores the table, so items show their models' values again, and a `property` event shows as its raw name. The behaviour is unchanged; only the comment text differs.
2. **`_model_values` made public too, as `model_values`.** BR2-02 named three public names. The dialog's GET needs the model's values, and the write needs them share-locked for the named ids. So `model_values` takes optional `property_ids` and `lock`, as `options_by_property` takes `lock`. Rejected: a second, near-copy query in `item_properties.py`.
3. **Four shared values-save helpers in `properties.py`** (`values_from_body`, `lock_value_properties`, `checked_changes`, `write_values`). The item write repeats the model write's body parsing, locks (2)–(3), refusal and upsert/delete. Without the helpers it would be a near-copy of `set_model_properties`, which the DRY rule forbids. `set_model_properties` now uses them, with the same SQL and order. One difference: its locking property read now also selects `unit`, which is harmless. The table and owner-column names passed to `write_values` are code constants, never user input.
4. **A non-object request body answers like the model route.** `values_from_body` reuses `_body()`, so a body that is not a JSON object answers 400 "Request body must be a JSON object". A missing or non-object `values` answers 400 "Send the values as an object" on field `values`, as § 5.1 says.
5. **`value_display` and `option_labels` helpers.** The display of a stored row (`format_value` on the data type's column) was inline in `property_view`. Three places need it now (the card, the history, the write's model displays), so it is one pure function. `option_labels` replaces the inline `{id: label}` comprehension of `_card_rows`, now used in three places.
6. **`has_model` on each dialog row**, as § 5.5 lists it among the row fields. The dialog reads it per row for the hint.
7. **The dialog's empty state** (no active property; the card hides the button then, so it shows only after a race) reads "The class has no properties now. Reload the page.", and the dialog is close-only. The model dialog's text points at Masters, which does not fit an item.
8. **The PUT's answer** is built from the node read after the lock. That read is the transaction's first plain read, taken after (1), so its class and model are the locked row's.

## 5. Not done, deferred or assumed

- Nothing in the brief is left out.
- Assumption: the e2e "operator" test moves its machine to SMTW.MCC2 by API (`PUT unit_id` as IT admin), because `propertySetup` places machines at MCC1 and the operator holds only MCC2. Changing `propertySetup` would touch `e2e/support/` (shared code, a full-suite trigger).
- The brief's standards numbers (§ 9.6) stay "to verify", as the brief says.

## 6. Tests run

Run name `YANTRA_TEST_RUN=s044c1`.

**Red first.**
- `test_properties_core.py` failed at collection (`ImportError: item_changes`, `check_values`) before the core was written; green after.
- `equipmentLabels.test.js` "the property event names the property once (S044)" failed (the line read "property") before `equipmentLabels.js` changed; green after.
- The new API tests ran against the finished routes. Their first run failed only on test set-up mistakes (the shared `engineer` fixture holds no unit; a class change needs `type_id`).

**Targeted while coding:** `test_properties_core.py`, `test_properties_api.py`, `test_item_properties_api.py` (29 passed), `test_migration_v33.py` (4 passed), `test_migration_v9.py`; `equipmentLabels.test.js` (11 passed).

**Full suite** (`tooling/run-tests.bat`): `ALL SUITES: PASSED`.
- backend: 3012 passed (67 s);
- frontend: 169 passed;
- deps: 42 passed;
- tooling: 129 passed.

**Frontend build** (`npx vite build`): built, with only the existing chunk-size warning.

**Browser tests.** The new S044 tests were first run alone on `desktop-chromium` with `E2E_LANES=1`: 5 passed. Then the targeted set `e2e/equipment.spec.js e2e/masters.spec.js e2e/screens.spec.js` on the three projects. `equipment.spec.js` holds the changed screen. `masters.spec.js` covers the freeze and the model dialog with `PropertyInput`'s new prop unset (brief § 8.4). `screens.spec.js` opens every route. No shared frontend code changed (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store and `e2e/support/` are untouched), so the full suite was not run.

Result (6 lanes, 2.9 min): **170 passed, 1 skipped, 0 failed** of 171.

| Project | Tests | S044 tests |
|---|---|---|
| phone-chromium | 57 passed | 5 passed |
| phone-webkit (Docker WebKit, S046) | 57 passed | 5 passed |
| desktop-chromium | 56 passed, 1 skipped | 5 passed |

The skip is `screens.spec.js` "S040: the manager's bottom bar …", which skips itself on desktop (no bottom bar). The S045 flakes did not show: `tickets-*` specs were not in this run.

## Manual checks

Automated (brief § 8.4):

- [auto] **Important.** The engineer sets this machine's rated power over the model's 7.5 kW: the dialog fits, its title is "This machine's values — <code>" and it shows "Model: 7.5 kW"; after Save the card shows "5.5 kW · this machine" and "Values from model …, except those marked this machine.", and History shows "Property: <name>: 7.5 kW (model) → 5.5 kW" — `frontend/e2e/equipment.spec.js`::"S044: engineer sets this machine's rated power; the card marks it and the history shows the model's value before"
- [auto] The engineer clears it: the card shows 7.5 kW again with no mark — `frontend/e2e/equipment.spec.js`::"S044: engineer clears this machine's value; the card shows the model's again with no mark"
- [auto] A model-less component-unit: only *Edit this machine's values* shows; a saved value shows with no mark — `frontend/e2e/equipment.spec.js`::"S044: a component-unit with No model has only Edit this machine's values; its value shows with no mark"
- [auto] The operator sees no *Edit this machine's values*, nor does anyone on a scrapped machine — `frontend/e2e/equipment.spec.js`::"S044: the operator sees no Edit this machine's values, nor does anyone on a scrapped machine"
- [auto] A refusal (a number with five decimals) shows under its input — `frontend/e2e/equipment.spec.js`::"S044: a number with five decimals is refused under its input"

On a real device: none (brief § 8.5). No row was added to `device-checks.md`.

## Docs updated

- `docs/schema.md`: the `equipment_property_values` row, the `property` event in the `equipment_events` row, the `model_property_values` row's pointer to it, the Mermaid overview (entity and three links), and the version line (now "migration v33").
- `docs/schema.html`: the header line (v33, 38 tables, 56 links); the table in the Overview tab (keyed columns) and the Equipment tab (every column); its three links in both tabs; the Equipment tab's note. Edited by hand, as no generator exists.
- `docs/Plan.MD` § 4.1 (equipment class, properties): S044 built, and what it does.
- `docs/Maintenance-Philosophy.md` glossary *Property*: "shown as this machine's and logged in its history".
- `.claude/CLAUDE.md` § SMTW-Review spec map: `equipment` gains S044.
- `docs/steps/device-checks.md`: none, because the brief has no real-device check (§ 8.5).
- `backend/example_secrets_app.py`, `docs/Keycloak.md`: none, because the step adds no secret and changes no role or claim.

## Fix rounds

### Round 1

- **CR1-01 (minor): Fixed.** `PropertiesPanel.vue` unit help line now reads "This property has values, so its unit is fixed." (it matches the backend `UNIT_FIXED` message and covers items' own values). No test asserted the old text (grep of `frontend/e2e` and `frontend/tests`); no assertion added, because the unit-fixed state needs a seeded value and the change is text only.
- **CR1-02 (nit): Fixed.** `secondSide` in `equipmentLabels.js` now takes the start shared by both sides and cuts it back to its last ": ", so "Power: rated: 7.5 kW" to "Power: rated: 5.5 kW" shows "Property: Power: rated: 7.5 kW → 5.5 kW". New vitest case "a property name with a colon keeps its whole name (S044 CR1-02)". Fails without the fix: the received text was cut at the first ": " (expected `Property: Power: rated: 7.5 kW → 5.5 kW`, the new side lost "Power: "); passes with it. The existing meter-limit and property cases still pass.
- **Tests:** frontend 170 passed; `npx vite build` built (chunk-size warning only); targeted e2e `masters.spec.js` and `equipment.spec.js` on all three projects (phone-webkit in Docker): 144 passed, 0 failed. No backend change, so no backend run.
- **Docs updated:** none, because the round changes one help text and one display helper; no migration, secret, role or module behaviour.
