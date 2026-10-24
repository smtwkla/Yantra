```
Step: S033 — Model optional on component-units
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: 6ab6af0 (S032 is committed as b100494; the schema docs as 6ab6af0; nothing of a step is uncommitted). The orchestrator named `33c3a4b + uncommitted S032`; the working tree has moved on since. Migration v28 is still right: v27 is `people.email`.

**Verdict: two `major` findings are open** (BR1-01, BR1-02). No blocker. Full track, round 1. Facts file `scratch/brief-facts-S033.md` used; every file, route and name it lists exists as the brief says. The U1 decisions (class picked directly, component-units only, data left as it is) are not reopened; BR1-01 and the nits on class deactivation are risks they create.

## Findings

### BR1-01 — major — A class change on a node without a model can leave a type of the old class: FK error 1452, answered as a 500

**Problem.** § 5.1 covers the body's `model_id`, `class_id` and `type_id`, but not the stored `type_id`. Three writes reach the database with a type of one class and a class of another:

1. a no-model component-unit of class A with type A1; the body sends `class_id: B` and no `type_id` (§ 5.1: "`class_id` and `type_id` may be sent alone"). The row would hold `(type_id A1, class_id B)`;
2. a node with a model (class A, type A1); the body sends `model_id: null, class_id: B` and no `type_id` (§ 5.1 "Update with `model_id: null`": only `class_id` must be sent);
3. the body sends `type_id` alone: § 5.2 says the type must be of "the class", but not which class — the stored one, or the one the same body sends.

`fk_equipment_type (type_id, class_id)` refuses cases 1 and 2 with error 1452. `api_common._integrity_error` re-raises every IntegrityError that is not a duplicate key (1062), so the user gets a 500, not a refusal.

**Why it matters.** The form will send both fields, so the normal path works; but the API rule is the contract (§ 7.4: "a client that sends both has a bug, and silence would hide which value won"). Left as it is, the coder decides the rule alone, and the unhappy path is a server error.

**Options.**
- **(a) Recommended.** Add a row to § 5.1: when the body's `class_id` differs from the stored class, `type_id` must be in the body too (`null` = no type); otherwise 400 `type_id` "Pick a type of the new class, or No type". A `type_id` sent alone is checked against the stored class. State once: "the type is checked against the class the row will hold after the write: the sent `class_id`, else the stored one". The form always sends both, so nothing changes for the user. Add the three cases to § 8's core tests.
- (b) A class change without `type_id` clears the type (event "type A1 → none"). Shorter body, but a silent change, against § 7.4.
- (c) Refuse every class change that does not restate the type, even when the class is unchanged. Over-strict: a type-only change would need the class too.

### BR1-02 — major — The form cannot tell "nothing picked" from "No model", and the refusal lands on a hidden field

**Problem.** Today `toBody` sends `model_id: null` for the placeholder (`form.model_id === ""`), and the backend answers "Pick a model" (`EquipmentFormModal.vue:53`). § 1.5 adds a *No model* option that also means `model_id: null`. For a component-unit the backend then cannot tell the two apart: both get "Pick a class" on `class_id` (§ 5.1 row 4). The Class field shows only after *No model* is picked (§ 1.5), so for a user who picked nothing the refusal names a field that is not on screen; `useFormModal` shows such an error at the top of the dialog (`modalError`, `useFormModal.js:7–10`), against S026 ("a refusal is always in view", the message beside its field).

§ 1.5 also leaves these form rules to the coder:
- the body: `class_id` / `type_id` must be left out when a model is picked (§ 5.1 refuses them beside a model) and sent when *No model* is picked, `type_id: null` for *No type*; `fromRecord` must load `class_id` / `type_id` on edit;
- the *Level* select of *Add part* can switch between component-unit and component after *No model* was picked: the option must follow `form.level`, and switching to component must clear it back to the placeholder;
- a class change must reset *Type* (BR1-01, the form side);
- on edit, an unchanged inactive class or type must stay listed and marked "(inactive)", as `modelChoices` does for the model (§ 1.3 "an unchanged inactive class is kept").

**Why it matters.** The form is the only screen of this step; its contract decides whether the e2e check in § 8 can be written, and a refusal out of view is the S026 bug class.

**Options.**
- **(a) Recommended.** State the form contract in § 1.5: a sentinel value for *No model* in `form.model_id` (for example `NO_MODEL = "none"`, a `modelPicker.js` constant); `toBody` leaves `model_id` out for `""` (create: the backend answers "Pick a model" on `model_id`, which is on screen — see BR1-06; edit: the placeholder is disabled, so `""` cannot occur), sends `model_id: null` plus `class_id` and `type_id` for the sentinel, and the id with no `class_id` / `type_id` otherwise; the Class and Type fields render whenever the sentinel is picked, so "Pick a class" lands beside its field; the level and class resets above; inactive unchanged class and type listed. Needs BR1-06 (a).
- (b) Keep `null` for `""` and refuse `""` in the form before sending ("Pick a model" on `model_id`), as `EquipmentMoveModal.vue:51` does for the unit. Works, but puts the rule in the frontend as well as the backend.

### BR1-03 — minor — The ISO 14224 citation says more than the standard does

**Problem.** § 2 says ISO 14224 "asks for the equipment class and type on every item and the manufacturer and model *where known*: maker and model are recommended data, not mandatory, for subunits and maintainable items". In ISO 14224:2016, the equipment data (clause 8, Table 5 "Equipment data (common data)": equipment class, type, manufacturer's name, manufacturer's model designation, …) describe the **equipment unit**, taxonomy level 6. Annex A's per-class tables (A.2.x) describe subunits (level 7) and maintainable items (level 8) **by name only** (their subdivision), with no maker or model attribute. So the standard neither asks for nor forbids a maker and model on a subunit; it asks for them on the equipment unit.

**Why it matters.** The project owner is learning the standard from these briefs. The honest reading supports the step better: S012's "model on every node" went beyond ISO 14224; this step brings the rule back to the standard's shape (model on the equipment unit; a subunit identified by its class and name). Still to verify against the user's copy, as § 9.2 says.

**Options.** (a) Recommended: rewrite the § 2 bullet as above, keep "to verify". (b) Keep the text and only soften "asks for … on every item".

### BR1-04 — minor — Planned duplicates of two existing lock helpers, and a third wording for "inactive"

**Problem.** § 3 and § 5.3 plan a new type lock in `equipment.py`: `SELECT id, class_id, active FROM equipment_types WHERE id = %s FOR UPDATE`, then `check_type_class`, then the active check. That is `masters._lock_type_for_model` (`masters.py:467–477`) line for line, with the same 400 "Unknown type" / "This type belongs to another class" and 409 "The type is inactive". For the class, `equipment._lock_class` (`equipment.py:369–379`) already exists: 400 "Unknown class", 409 "The class is inactive". § 5.2 instead specifies "This class is inactive" / "This type is inactive" — a third wording beside "The class is inactive" and "The type is inactive" (CLAUDE-COMMON: one term for one thing).

**Why it matters.** DRY; and three texts for one refusal in the same app.

**Options.** (a) Recommended: reuse `_lock_class` as it is; make `masters._lock_type_for_model` public (`lock_type_of_class(cur, type_id, class_id)`), import it in `equipment.py` (`masters.py` does not import `equipment.py`, so no cycle), and keep the existing messages. Note that `_lock_class`'s docstring ("of a newly picked model") and the "defence in depth" remark change: for a directly picked class the active check is now a real rule. (b) Keep a copy in `equipment.py` with the existing texts.

### BR1-05 — minor — The "No model" history text is placed in the shell; it belongs in the pure core

**Problem.** § 3 lists under `equipment.py`: "the tracked-change text: a missing model shows as 'No model'". The display rule for history values lives in `equipment_core._display` (`INHERIT` for a part's own grade, `NO_TYPE` for no type) and `tracked_changes`, which `test_equipment_core.TestTrackedChanges` tests. The frontend's `describeEvent` (`equipmentLabels.js:72–74`) passes the model values through as they are and carries the comment "Every node has a model (S012), so neither side is ever empty".

**Why it matters.** Pure core, thin shell: a rule in the shell has no unit test and a second place to look. `model_label(None, None) → None` (§ 3 `masters_core`) and the "No model" literal are two halves of one rule.

**Options.** (a) Recommended: a constant `NO_MODEL = "No model"` in `equipment_core`, used by `_display` for `model_label is None`; a `tracked_changes` case ("Atlas Copco GA37" → "No model", and back); `equipmentLabels.js` only updates its comment (add the file to § 3). (b) As the brief, in `equipment.py`.

### BR1-06 — minor — § 5.1 does not say what the validator gets, and leaves one input out

**Problem.** Three gaps in the table's inputs:
1. `model_id` **absent** (key not sent) on **create** of a component-unit. Row 3 covers it for equipment and components ("`null` or missing → Pick a model"); for a component-unit only `null` is in the table.
2. "The stored model decides" needs `validate_equipment` to know it: `update_equipment` passes `stored = {code, level}` (`equipment.py:738`); `model_id` must be added, and the test helper `_update` in `test_equipment_core.py:21` gains it.
3. "A newly picked class" (§ 1.3, § 5.2) is not defined, and § 5.3 (5) does not say whether an **unchanged** class is locked in a no-model write. The model's rule is "differs from `locked["model_id"]`" and no lock when unchanged.

**Why it matters.** Each is a rule the coder would set alone; 1 also decides BR1-02 (a).

**Options.** (a) Recommended: 1 — an absent `model_id` on create means "Pick a model" at every level; only an explicit `null` means no model (a client must say so). 2 — state `stored = {code, level, model_id}`. 3 — "newly picked" = differs from the locked row's `class_id` / `type_id`; the class is locked (5) on create always (the prefix) and on update only when newly picked; the type (5a) only when newly picked. (b) 1 — absent = `null` for a component-unit; simpler for the API, but a client that forgot the field gets "Pick a class".

### BR1-07 — minor — The tests this step breaks are not named; the facts run does not name them

**Problem.** § 3 and § 8 defer to "names from the facts run"; the facts file lists files, not tests. From the code:
- `test_equipment_core.py`: `TestValidateCreate.test_required_fields_per_level` (the `component_unit` row expects `model_id` among the missing fields — it stays only with BR1-06 (a)); `TestModelAndRefusedFields.test_a_model_may_be_left_out_on_update_but_not_cleared` (`_update(model_id=None)` → "Pick a model" holds for the equipment default; add a `stored_level="component_unit"` case); `test_old_fields_are_refused_even_as_null` (`class_id` / `type_id` rows: the message changes to "Class comes from the model" / "Type comes from the model", and the refusal now depends on the stored model);
- `test_equipment_api.py`: `TestModels.test_old_fields_are_refused_even_null_or_unchanged` (same two rows); `test_a_null_model_on_update_is_400` and `test_no_model_is_400` keep passing (equipment level) — say so;
- `frontend/tests/modelPicker.test.js`: `modelChoices` gains a level argument; the existing cases must keep passing with the default;
- `frontend/e2e/equipment.spec.js`: the three dialogs that pick "Atlas Copco GA37 — CMP / Screw compressor" are on level equipment, so *No model* must not appear there (your § 8 check covers it).

**Why it matters.** The coder otherwise finds them by running the suite; the brief should say which behaviour changes are intended.

**Options.** (a) Recommended: list them in § 8 with the intended new assertion each. (b) Leave to the coder.

### BR1-08 — minor — The important e2e check lacks the dialog-fit assertion and the list level

**Problem.** § 8 Automated: "the engineer adds a component-unit … with *No model*, class picked …; the list row shows '—'". Two gaps: the dialog grows by two selects when *No model* is picked, and nothing asserts `expectDialogFits` in that state (every other equipment dialog test does); and the equipment list opens at level *Equipment* by default (`list_equipment`: `level … or "equipment"`), so a component-unit row shows only with the level filter on *Component unit* or *All* plus `q=<name>`.

**Why it matters.** "A dialog fits a phone" is a browser check (README § Manual checks); without it the three-project run proves nothing about the phone width. The second gap makes the test fail on first write.

**Options.** (a) Recommended: `expectDialogFits(page)` after picking *No model* and after picking the class; open `/equipment?level=component_unit&q=<name>` for the "—" assertion. (b) Drop the list assertion and check "—" on the asset list print instead (`asset-list.spec.js` is in the targeted run anyway).

## Nits

- **BR1-09** (nit) § 3 `equipment.py`, the list search: `COALESCE` is not needed. `(FALSE OR NULL)` is NULL and `(TRUE OR NULL)` is TRUE in SQL, so a NULL model never drops a row that matches on another word. Drop the change or keep it with the right reason.
- **BR1-10** (nit) § 3 `documents.py`: `_inherited` already returns `[]` for a node without a model (`WHERE model_id = NULL` matches nothing). Keep the explicit skip, but say it is for clarity, not a fix.
- **BR1-11** (nit) § 5.2: say that deactivating a class is not blocked by model-less component-units of that class (`update_equipment_class` counts active models only, `masters.py:338`), as a type's deactivation is not blocked by its equipment; the nodes keep the inactive class, and the "unchanged inactive class is kept" rule covers their edits. A U1 consequence worth one line.
- **BR1-12** (nit) § 1 Out of scope: "A user can clear the model on a node by editing it" — only on a component-unit; equipment and components with a Generic model keep it.
- **BR1-13** (nit) § 1.6: the lead sentence says screens "show **No model**", then two bullets say "—". Say "show No model or —" there, or move § 7.5 up.
- **BR1-14** (nit) § 1.5, floor use: when the user has a class in the *Class filter* and then picks *No model*, prefill *Class* with it (the hint "This class has no model yet. Pick No model …" leads exactly there); one tap saved on a phone.
- **BR1-15** (nit) § 2: cite ISO 55001 § 7.5 (information requirements: the organisation decides which asset attributes it needs and at what quality) beside the "ISO 8000, plain practice" line; it is the clause Plan.MD already uses for "know what you have".
- **BR1-16** (nit) § 4 rollback: also say the previous release's edit of a model-less node fails with 409 (`_reread` finds no row through the inner join), not only that the node vanishes from lists.

## Checked and found consistent

- Every node read goes through `NODE_JOINS` / `_NODE_FROM`: list, detail, tree, by-code, labels, asset list (`equipment.py`), the documents owner read and the removed list (`documents.py:64, 448`). The two `LEFT JOIN`s cover all of them; `documents.py:454` joins a document's own model, as the brief says. No other backend query joins `equipment_models` or `manufacturers` for nodes: `tickets.py`, `alerts.py` and the S031 Me page join `equipment` and `equipment_classes` only; the ticket screens and `TicketRow` show code and name, never the model (frontend grep: `model_label` / `manufacturer_name` appear only in `EquipmentDetailView.vue`, `EquipmentView.vue`, `AssetListPrintView.vue`, `ModelsPanel.vue`).
- `asset_list_core.py` does not read the model; `assetList.js` reads `class_code` / `type_name` and `model_label` for display only.
- Lock order: class (5) then type (5a) after the equipment rows matches `masters.py` (class → type for types and failure modes; manufacturer → model → class → type for models); `masters.py` never locks equipment, so no cycle. A write with a model still never locks a type.
- Migration v28: `fk_equipment_model (model_id, class_id)` is skipped by InnoDB when `model_id` is NULL (MATCH SIMPLE), and still binds a model's class to the node's; `fk_equipment_type` is unchanged and checks a directly picked type; the CHECK holds for every existing row (the column was NOT NULL), so no `_PRECONDITIONS` entry is needed; `MODIFY … NULL` and `ADD CONSTRAINT IF NOT EXISTS` re-run without error. `test_migration_v26.py` is the right pattern (`_recreate`, `_migrate`, `_schema`, a v22 fill with an equipment row).
- `equipment_events.event` already has `model`, `class` and `type`; `_written_state` takes the class code from the lock and the type name from the re-read, as the brief relies on.
- Permissions unchanged: `equipment:edit` at the node's site through `load_node_for_user` / `_load_target_node`; no new key, nothing in `SITE_SCOPED`.
- `update_equipment`'s "same value sent back is no change" loop (`equipment.py:742`) treats `null == NULL` as unchanged, so clearing an already-clear model is a no-op, as § 5.1 implies.
- Plan.MD § 4.1 line 236 ("model (required on every node …)") is the one sentence to change; the S012 decision table stays as history. `docs/schema.md:35` names `model_id (required)` and is now committed (6ab6af0), so the planner's edit applies to a tracked file.
- Track full is right: a migration, locking and a rule change in the API.
- Scope B texts: "No model", "Select a class…", "No type", "Pick a class", "Without a model, the class sets the code prefix." are short and consistent with the existing dialog ("Select a model…", "Pick a model").
