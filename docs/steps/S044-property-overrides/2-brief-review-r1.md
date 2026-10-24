```
Step: S044 — Property overrides on equipment items
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: ff9ddb3 + uncommitted S037, S038, S039, S040, S043 (and S045 in progress, test files only)

Facts file read: `scratch/brief-facts-S044.md`.

**Verdict: one `major` finding is open (BR1-01, a circular import in the module plan). No blocker.** The lock order, the site check, the freeze, the S033 case and the three proposed answers to the open questions hold. Six minor findings ask for rules the coder would otherwise decide alone and for two screen details.

## Findings

### BR1-01 — major — `properties.py` cannot import from `equipment.py`

**Problem.** § 3 puts the item write (`PUT /equipment/<id>/properties`) in `properties.py` and § 5.2 has it call `load_node_for_user` and use `SCRAPPED_MESSAGE`; § 5.4 needs `write_events`. All three live in `equipment.py`. But `equipment.py` line 116 already does `from properties import equipment_properties`. Adding `from equipment import load_node_for_user, SCRAPPED_MESSAGE, write_events` to `properties.py` makes a cycle: whichever module Python loads first stops at its import line, the other finds a half-loaded module, and the app fails to start with `ImportError`. `meters.py` avoids this because `equipment.py` imports nothing from it.

**Why it matters.** The brief's module plan does not run as written. The coder would have to pick a fix alone, and the obvious quick ones (a lazy import inside `_detail`) hide the cycle instead of removing it.

**Options.**
- (a) **A new module `item_properties.py`** (recommended): holds `item_properties_bp`, the dialog's `GET`, the `PUT`, `_item_properties`, and the LOCK ORDER note of the item write. It imports from `equipment.py` (node lock, scrapped text, `write_events`) and from `properties.py` (`_options_by_property`, `_linked_properties`, `_item_values`). The read helpers the detail needs (`_item_values`, `equipment_properties` with the item's values) stay in `properties.py`, which still imports nothing from `equipment.py`. `app.py` registers it at `/api` as `meters_bp`. Same shape as `meters.py` beside `masters.py`.
- (b) Move `equipment_properties` and `_item_values` into `equipment.py`, so `equipment.py` stops importing `properties.py`. Rejected: the card's query belongs with the property code.
- (c) A lazy `from properties import equipment_properties` inside `_detail`. Rejected: an import in a function to dodge a cycle is the kind of hidden coupling CLAUDE-COMMON forbids.

Under (a), § 3, § 5.3's last line ("Both LOCK ORDER notes") and § 8.2's file name stay; `properties.py`'s docstring gets one line pointing at the new module, and `equipment.py`'s properties bullet names it.

### BR1-02 — minor — "no change" is not fully defined, and neither is what the dialog sends

**Problem.** § 5.1 says "A value equal to the item's stored own value is no change: no write, no event." Two cases are not stated:
- a clear (`""` or `null`) of a property that has **no own row**. `check_model_values` returns `(id, None)` for every blank; the model route deletes blindly, which is harmless there because it writes no history. The item route would write "Rated power: model value → Rated power: model value" for every untouched row if it follows the same path;
- what the dialog sends. § 1.3 says "*Save* saves every changed row in one request", but `ModelPropertiesModal.vue` sends **every** row (`items.value.map(...)`), and the API can be called with every row anyway, so the rule must live in the backend.

Also unstated: how equal is judged (a number as `Decimal` against the stored `DECIMAL(16,4)`, so `5.5` equals `5.5000`; text exact; yes/no as 0/1; a choice by option id).

**Why it matters.** Without the rule the coder decides it, and the history card fills with lines that record nothing.

**Options.**
- (a) **One pure function decides the effective changes** (recommended): `item_changes(changes, stored)` in `properties_core.py` drops a clear with no stored row and a value equal to the stored one; both the write (insert / update / delete) and `item_events` take its output. The dialog sends every row, as the model dialog does; the backend filters. State the equality rule per data type in § 5.1.
- (b) The dialog sends only dirty rows. Rejected: the API is still open to a full body, so the backend rule is needed anyway.

### BR1-03 — minor — the history side "model value" records nothing of what was in force (decision 7)

**Problem.** § 5.4 writes "Rated power: model value → Rated power: 5.5 kW". Decision 7 argues that naming the model's number would record "a value that was never this item's". But at the moment of the write the model's value **was** this item's value in force: the card showed it, and any reliability comparison used it. A reader of the history a year later cannot tell whether the rewind took the motor from 7.5 kW to 5.5 kW or from 11 kW. If the model's value is corrected later, the history line still says truthfully what the item showed on that day.

**Why it matters.** This is a judgement call for the user, not the coder. The practice behind it: a change record (ISO 9001 § 7.5.3, control of documented information, and the TPM equipment history card the brief cites) records the state before and after a change, not a pointer to where the old state came from. ISO 14224 § 9 (data quality) asks that recorded data stay interpretable without looking elsewhere.

**Options.**
- (a) **Record the model's display at write time, marked as the model's** (recommended): old side "Rated power: 7.5 kW (model)", and "Rated power: no value (model)" when the model has none; "Rated power: no value" on a model-less item. Length: 80 + 2 + 120 + 8 fits `VARCHAR(200)` only if `display` is capped: text values are ≤ 100, so 80 + 2 + 100 + 8 = 190. Fine.
- (b) Keep "model value" (the brief). Simpler, loses the old rating.
- (c) Both: "Rated power: model value 7.5 kW". Longer, no clearer than (a).

### BR1-04 — minor — the history line names the property twice

**Problem.** `change("Property", oldValue, newValue)` gives "Property: Rated power: model value → Rated power: 5.5 kW". The repeat is the same problem S038 solved for `meter_limits` with `limitsOnly`, which cuts the repeated "<name>: " prefix from the new side ("Meter limits: Oil temperature: 10–60 °C → up to 55 °C").

**Why it matters.** Scope B: shorter lines on a phone-width history card; and a helper already exists for exactly this (CLAUDE-COMMON DRY).

**Options.**
- (a) **Reuse `limitsOnly`** (recommended), renamed to something general (`secondSide`), so the line reads "Property: Rated power: model value → 5.5 kW" (or "… 7.5 kW (model) → 5.5 kW" under BR1-03). § 1.5, § 5.4 and the e2e assertion in § 8.4 follow.
- (b) Keep the repeat. Rejected: no reason to differ from the meter line.

### BR1-05 — minor — "PropertyInput.vue is reused unchanged" conflicts with the "Model: 7.5 kW" hint

**Problem.** § 1.3 puts "small grey text" under each input. `PropertyInput.vue` renders its label, input and error inside one `div.mb-3`. Text placed after the component sits below that margin, detached from its input, and above the next input's label — the reader cannot tell which input it belongs to. § 3 says the component is reused unchanged.

**Why it matters.** The hint is the one thing that tells the engineer what the model says while typing; detached, it misleads.

**Options.**
- (a) **A `hint` prop on `PropertyInput`** (recommended): one `div.form-text` after the input, inside the `mb-3`; `ModelPropertiesModal.vue` passes none. § 3 lists the component as changed.
- (b) Wrap each `PropertyInput` in the item dialog and override the margin. Rejected: CSS against the component's own layout.

### BR1-06 — minor — "· this machine" on a model-less component-unit marks every row

**Problem.** § 1.2 marks the item's own value "· this machine" whenever it has one. On a component-unit without a model (S033) every value is its own, so every row carries the mark, with no line under the rows to explain it. The mark exists to tell an own value from the model's; with no model there is nothing to tell apart.

**Why it matters.** Noise on the card the floor reads; and the e2e in § 8.4 ("a saved value shows") would pin the noisy form.

**Options.**
- (a) **Show the mark only when the node has a model** (recommended): `node.model_id !== null && p.source === "item"`; the API's `source` stays `"item"` so nothing else changes. Say so in § 1.2 and § 8.4.
- (b) Keep the mark everywhere. Rejected as above.

### BR1-07 — minor — the item dialog needs a title that says its reach

**Problem.** The brief specifies no title for `ItemPropertiesModal.vue`. The model dialog is titled "Properties of <model>" and changes every machine of the model; the new one, opened from the same card header, changes one machine. Two dialogs with the same inputs, the same "Save values" button and no visible difference in reach is how a nameplate value lands on the model, or a model fix on one machine.

**Why it matters.** The shared-kiosk and floor rule in the review brief: who or what is acted on must be visible. A wrong choice here is silent.

**Options.**
- (a) **Title "This machine's values — <code>"** (recommended), and nothing else added; the "Model: 7.5 kW" hints already show the other side. `useFormModal`'s `label` gives the code.
- (b) Title "Properties of <code>". Rejected: too close to "Properties of <model>".

## Nits

- **BR1-08** (nit) § 1.6, `DATA_TYPE_FIXED` / `UNIT_FIXED`: "the property has options or models or equipment items hold values of it" is a noun pile (scope B). Use "The data type cannot be changed: the property has options or values. Make a new property instead." and "The unit cannot be changed: the property has values. Make a new property instead." No e2e asserts the old text (`frontend/e2e/` has no "cannot be changed").
- **BR1-09** (nit) § 4 rollback: "Stated in the impl report's release notes, as S038 did for v30" — S038 and S043 put a "Rollback:" line in the migration's comment in `local_db.py` (v27–v31). Say "a Rollback: line in the v33 comment, as v27–v31 have".
- **BR1-10** (nit) § 3 `check_values`: its docstring says "The changes a model save makes"; generalise it to "a values save (a model's or an item's)".
- **BR1-11** (nit) § 3 tests, `conftest.py`: `property_definitions` is in `_SEEDED_TABLES`, not `_TABLES`, and the seeded tables are emptied first with FK checks off. Say only "in `_TABLES`, before `equipment`".
- **BR1-12** (nit) § 1.4 "each is a full-size button": the existing button is `btn-sm`. Say what is meant: the two `btn-sm` buttons wrap onto their own lines at phone width, or drop the sentence.
- **BR1-13** (nit) § 5.5 `has_model` in the dialog's `GET` repeats `node.model_id`, which the page already holds. Keep it (the route stands alone) or drop it; say which.
- **BR1-14** (nit) § 1.7: a model change can change the class too (a model of another class). Say in one sentence that the two bullets then both apply: the values stay, and those of properties the new class lacks are hidden.
- **BR1-15** (nit) § 3 Frontend: `equipmentLabels.js`'s header comment lists the steps that added events; add S044.

## The three open questions (§ 9)

What ISO 14224 says, in plain terms: the standard's taxonomy (§ 8.2, Figure 3) goes plant → unit → **equipment unit** → subunit → component. The manufacturer's name and model designation are **attributes of the equipment unit** (Table 5, equipment data), not a level of their own; the design and nameplate data (Annex A, equipment-class-specific data) belong to the unit too. Yantra's model (S012, S043) is a convenience that stores a value once for many units. So the item's own value is the ISO-native place; the model's is the default. That reading supports all three proposals.

1. **Model change — kept (agree).** Correcting which model a unit was filed under changes an attribute of the unit; the unit's recorded nameplate data stay true. A "wrong model, start again" case clears values one by one in the dialog, each with a history line. Note: under decision 3 an own value equal to the new model's keeps its mark; harmless, and the history says when it was typed.
2. **Equal to the model's value — kept as the item's own (agree).** A nameplate reading is a verified attribute of this unit (ISO 14224 § 9.4 data quality: the data's source is known). S038's "equal = no override" fits a limit, which is a setting that should follow the model when nobody chose otherwise; a rating is a fact. The one cost: an engineer who types the model's number by habit pins it to the machine; the clear path and the "Model: …" hint make that visible.
3. **Class change — hidden, kept (agree).** Annex A data are class-specific, so a property the new class lacks has no row on the card; deleting the value would lose a fact on a filing fix, the same reasoning as S043 § 5.4 for models. The hidden value still freezes the property's type and unit and counts in `value_count`, as a model's hidden value does; say so in § 1.6 so nobody is surprised.

## Checked and found consistent

- **Lock order.** The item write takes (1) the node, then (2) properties ascending, then share-reads links and options, then its own value rows and events. No path in `properties.py`, `masters.py`, `meters.py`, `documents.py` or `tickets.py` takes a `property_definitions` row and then an equipment row; `update_property` holds only (2) and share-reads value tables; `add_class_properties` and `set_model_properties` take a class or a model, never equipment. `remove_class_property`'s delete waits on the item write's share lock of the link row and holds only the class, which the item write never takes. The item value insert takes shared FK locks on the node (held, (1)), the property (held, (2)) and the option (share-read already). `LOCK_EQUIPMENT` returns `class_id` and `model_id`, so § 5.3's "read from the locked row" holds. The FK on `property_id` gives the index the `has_values` share-read and `value_count` need, as on `model_property_values`.
- **`equipment:edit` at the item's site.** `load_node_for_user(cur, id, for_update=True, key="equipment:edit")` locks, 404s on no access, then `require_perm_at` 403s, as `meters.py:126`; `canEdit` on the page is site-based and already false on a scrapped or loading node. The model button keeps `canEditModels` (union), as S043 § 7.4 decided.
- **The `property` event.** v33 appends one ENUM value as v30 did; `test_migration_v9.py::test_the_shape_holds` is the only test asserting the full ENUM on the current schema (`test_migration_v30.py` asserts it on its own v30 database); `describeEvent`'s `default` would show a raw `property` until the case is added; lengths fit `VARCHAR(200)`.
- **`check_model_values` → `check_values`.** Callers: `properties.py:40, 355` and nine uses in `test_properties_core.py`; the brief lists both. Same signature; `stored` serves the item's rows for the inactive-option rule.
- **The freeze.** `property_changes(stored, clean, has_options, has_values)` is pure and unchanged; only `update_property`'s `has_values` and `_PROPERTY_SELECT`'s `value_count` gain the second table. `value_count` is not shown as a column in `PropertiesPanel.vue`; it only drives `typeFixed` / `unitFixed`, so counting items in it is right.
- **S033 no-model case.** `_card_rows` already passes `{}` for `model_id` None; the card's "Values from model" line and the model button are already hidden; `noModelPart` exists in `frontend/e2e/support/properties.js`; `test_equipment_api.py:1564` covers the detail's empty values and keeps passing (no key changes).
- **Existing tests.** The three S043 e2e tests assert "Values from model <label>." on machines with no own value, which § 1.2 keeps; `test_properties_api.py` imports no renamed name.
- **Track and checks.** Full track is right (migration, locking write, new endpoint). § 8.4 checks are all browser-judgeable and marked; § 8.5 none is right. Docs list matches `.claude/CLAUDE.md` § Docs to keep current.
- **Standards.** ISO 14224 (equipment-unit data vs class data), ISO 55001 § 7.5, ISO 9001 § 7.5.3 are the right ones and are marked to verify; no `_PRECONDITIONS` entry is right for a new table and an appended ENUM value.
