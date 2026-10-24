```
Step: S044 — Property overrides on equipment items
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 967e888 + uncommitted S037, S038, S039, S040, S043 (and S045 in progress, test files only)

Facts file read: `scratch/brief-facts-S044.md` (re-run).

**Verdict: no `blocker` or `major` finding is open.** BR1-01 is resolved: `item_properties.py` breaks the cycle, and I checked every import direction (below). One `minor` finding: the `item_events` signature cannot produce the history texts it promises. Seven nits.

**Re-read this round** (the sections the Review log names as changed): the header; § 1.2–1.7; § 2; § 3 (`item_properties.py`, "Why a new module", the `PropertyInput` row, `equipmentLabels.js`, the tests rows); § 4 rollback; § 5.1 `item_changes`; § 5.2–5.5; § 7 decisions 7–9; § 8.1–8.4; § 9 items 1–6; the Review log. Every finding marked `Accepted` is in the brief's text, not only in the log. The unchanged sections were not re-reviewed.

## Findings

### BR2-01 — minor — `item_events` cannot format the values it must write

**Problem.** § 3 gives `item_events(properties, changes, before, model_displays, has_model)`. § 5.4 says each side is "<name>: <display>" with `display` from `format_value(data_type, value, unit, option_label)`. Two inputs of `format_value` are missing:
- the **unit**: the write's property read in § 5.2 follows `set_model_properties`, whose `SELECT id, name, data_type, active FROM property_definitions` (properties.py:347) has no `unit`, and `check_model_values`' `properties` dict (`{id, name, data_type, active, linked}`) carries none. "Rated power: 5.5 kW" needs it;
- the **option labels**: `before` (the stored own row) and `changes` (the new columns) hold an `option_id`, not a label. "Shaft orientation: Horizontal" needs `{option_id: label}`, as `property_view(..., option_labels)` takes it.

`model_displays` is built in the shell and is fine, but it needs the same two inputs.

**Why it matters.** The coder would widen the signature alone, in the pure core that § 8.1 tests. The brief is otherwise exact about the core's signatures.

**Options.**
- (a) **Add `unit` to the property read and `option_labels` to the signature** (recommended): § 5.2's locking read becomes `SELECT id, name, data_type, unit, active … FOR UPDATE`; `item_events(properties, changes, before, model_displays, option_labels, has_model)`, with `option_labels` built from the share-read options (`_options_by_property` already returns `label`), as `_card_rows` does. § 3 and § 8.1 follow.
- (b) Pass pre-formatted displays for both sides in from the shell. Rejected: the formatting rule then lives in the shell, and the core test would test strings it did not make.

## Nits

- **BR2-02** (nit) § 3 `item_properties.py`: it imports three underscore names from `properties.py` (`_options_by_property`, `_linked_properties`, `_item_values`). Every other cross-module import in `backend/` is a public name (`meters.py` ← `masters.py`: `checked_limits`, `lock_meter_type`, `read_model_meters`; `documents.py` ← `equipment.py`: `NODE_JOINS`, `load_node_for_user`); the one exception is `config.py` ← `auth_utils._make_internal_url`. Drop the underscore on the three (the new `item_values` is born public), or say the underscore is kept on purpose.
- **BR2-03** (nit) § 5.5 the dialog's `GET`, "`equipment:read`, the node's access as the detail": the detail (`get_equipment`, equipment.py:609) calls `load_node_for_user(cur, node_id, for_update=False)` with no key; `list_node_meters` (meters.py:142) passes `key="equipment:read"`, which also checks the key at the node's site. Name the form to copy; `list_node_meters`' is the one for a stand-alone route on a node.
- **BR2-04** (nit) § 5.2 last bullet: the model's values are read plainly after the locks. Under REPEATABLE READ the plain read uses the snapshot taken by `load_node_for_user`'s `_read_node`, so a model save that committed while this write waited on a property row (2) is not seen, and the "(model)" side records the value before it. A `LOCK IN SHARE MODE` read of the `model_property_values` rows gives the committed value, and adds no cycle: the model save takes the model, then (2), then those rows, and this write never takes the model. Say which read is meant; the share read fits "the value in force at write time".
- **BR2-05** (nit) § 5.4 length: "a number with a unit ≤ 20" is wrong. `DECIMAL(16,4)` gives up to 18 characters (`-999999999999.9999`), plus a space and a unit ≤ 20: 39. The bound 190 still holds, since text ≤ 100 is the longest display. Write "≤ 39 (text ≤ 100 is the longest)".
- **BR2-06** (nit) § 3 `PropertyInput` `hint`: say where it sits against the error line. Recommended: the `invalid-feedback` directly after the input (as today), the `form-text` hint after it, so a refusal stays beside its field and the hint does not push it down.
- **BR2-07** (nit) § 1.4 the two card buttons: say the order. Recommended *Edit this machine's values* first, *Edit model values* second: the engineer on the floor edits this machine's nameplate far more often, and the model button changes every machine of the model, so it stands apart (the review brief's rule for actions with wide reach).
- **BR2-08** (nit) `docs/steps/README.md` index: the S044 row still says `Draft`; the header says `In review`. README § Gates: whoever changes a step's status updates its row.

## BR1-01 verified: every import direction

Fact, from the working tree:

| Module | Imports from (project modules) | Imported by |
|---|---|---|
| `item_properties.py` (new) | `equipment.py`, `properties.py`, base modules | `app.py` only (the brief) |
| `equipment.py` | `properties.py` (line 116), `masters.py`, `settings.py`, `equipment_core`, `masters_core`, `tickets_core`, `labels_core`, `asset_list_core`, base modules | `app.py`, `documents.py`, `meters.py`, `tickets.py` |
| `properties.py` | `properties_core` (stdlib only), `api_common`, `auth_utils`, `db_helpers` | `app.py`, `equipment.py` |
| `masters.py` | the cores (`equipment_core`, `meters_core`, `tickets_core`, `masters_core`), base modules | `equipment.py`, `meters.py` |
| `settings.py` | `local_db`, `access_control`, `network_core`, senders, `labels_core`, base modules | `equipment.py` |

Neither `equipment.py` nor `properties.py` imports `item_properties.py`, and no module on `equipment.py`'s import path (`masters.py`, `settings.py`, the cores) imports `equipment.py` or `properties.py` back. Whichever loads first (`app.py` loads `equipment` at line 171, then `item_properties` beside `meters` at 179; a test may import `item_properties` first), each module is fully loaded before the next needs it. The brief's statement "imports from both and is imported by neither" holds. Route shape: `/api` + `/equipment/<int:node_id>/properties` sits beside `meters_bp`'s `/equipment/<int:node_id>/meters`; `equipment_bp`'s `/<int:node_id>` cannot match a path with a slash, so no clash.

## Checked and found consistent

- **Accepted findings in the text.** BR1-02 (§ 1.3, § 5.1, decision 9), BR1-03 (§ 1.5, § 2, § 5.4, decision 7, § 9.4), BR1-04 (§ 1.5, § 3, § 5.4, § 8.4), BR1-05 (§ 1.3, § 3), BR1-06 (§ 1.2, § 8.4), BR1-07 (§ 1.3, § 3, § 8.4, § 9.5), BR1-08…BR1-15 each where the log says.
- **`item_changes` equality.** PyMySQL returns `Decimal` for `DECIMAL(16,4)` and `parse_value` returns `Decimal`, so `Decimal("5.5") == Decimal("5.5000")` holds as § 5.1 says; `parse_value` strips text and the stored text was stripped at its save; yes/no is stored 0/1 and parsed to `int(bool)`; a choice is an option id on both sides.
- **`secondSide`.** `limitsOnly` is used only in `equipmentLabels.js`; `equipmentLabels.test.js` asserts the meter-limits text, which the rename keeps. "Rated power: 7.5 kW (model)" / "Rated power: 5.5 kW" share the prefix "Rated power: ", so the line reads as § 5.4 says.
- **The freeze texts.** `DATA_TYPE_FIXED` and `UNIT_FIXED` are asserted by constant name only (`test_properties_api.py`, `test_properties_core.py`); no e2e or frontend file holds the old wording.
- **v33.** The columns match `model_property_values` (v31); the composite FK has its target `uq_property_options_id_property (id, property_id)`; the ENUM `MODIFY` and the "Rollback:" comment line follow v30's form (v27–v32 each carry one).
- **The `hint` prop.** `ModelPropertiesModal.vue` passes `property` and `error` only, so a prop with a default leaves it unchanged; `PropertyInput.vue`'s one `div.mb-3` wrapper is where the hint goes.
- **The card.** `node.model_id`, `node.model_label`, `canEdit` (site-based, false when scrapped or loading) and `canEditModels` (union) exist in `EquipmentDetailView.vue`; the existing model button is `btn-sm`; the "Values from model …" line is shown only with a model.
- **e2e set-up.** `propertySetup(tag, {properties, link, values})` sets model values by index; `noModelPart(parent, cls, name)` and `propertyTag(testInfo)` exist in `frontend/e2e/support/properties.js`.
- **Standards.** ISO 55001 § 7.5 (information requirements) and ISO 9001 § 7.5.3 (control of documented information) are the right clauses. The ISO 14224 reading (maker and model as attributes of the equipment unit; Annex A data class-specific) is the standard's; its clause and table numbers stay marked "to verify" in § 9.6, which is right until checked against the user's copy.
- **`_TABLES`.** `equipment_property_values` before `equipment` is enough: the clean-up runs with `FOREIGN_KEY_CHECKS = 0`, and `property_definitions` is in `_SEEDED_TABLES`.
