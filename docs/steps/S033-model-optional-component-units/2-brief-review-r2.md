```
Step: S033 — Model optional on component-units
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: 6ab6af0 (nothing of a step is uncommitted; only this step's folder and the README row).

**Verdict: one `major` finding is open** (BR2-01). No blocker. Full track, round 2. Facts file `scratch/brief-facts-S033.md` (re-run) used; every file, test, route and name it lists exists where the brief says, and the three "not found" names (`NO_MODEL`, `lock_type_of_class`, `test_migration_v28.py`) are the new ones.

Sections re-read, as changed by the round 1 answers: § 1.5–1.8 and Out of scope; § 2; § 3 (backend, frontend, tests); § 4 rollback; § 5.1–5.4; § 6; § 7 decisions 7–10; § 8; the Review log. Every round 1 finding marked `Accepted` is in the brief's text, not only in the log (checked one by one: BR1-01 § 5.1 row 4 and decision 7; BR1-02 § 1.5 and decision 9; BR1-03 § 2; BR1-04 § 3 and § 5.2; BR1-05 § 3 and § 5.4; BR1-06 § 5.1–5.3 and decision 8; BR1-07 and BR1-08 § 8; BR1-09–BR1-16 at the places the log names). Sections not changed were not re-read.

## Findings

### BR2-01 — major — A class change that restates the *old* type escapes the type check: FK error 1452, answered as a 500

**Problem.** § 5.1 says a `type_id` is "checked against the class the row will hold after the write". § 5.2 and § 5.3 (5a) say the type row is locked and checked "only when a write without a model **newly picks** a type", newly picked = "differs from the locked row's `type_id`". The two rules leave one case open:

- a no-model component-unit of class A with type A1; the body sends `class_id: B, type_id: A1` (decision 7 asks the client to restate the type, and it restates the old one);
- the same on a node with a model (class A, type A1): `model_id: null, class_id: B, type_id: A1`.

A1 equals the stored `type_id`, so it is not newly picked, so (5a) does not run and nothing checks it against B. The row `(type_id A1, class_id B)` reaches `fk_equipment_type` → 1452 → `api_common._integrity_error` re-raises → 500. The form cannot produce it (§ 1.5: a class change resets *Type* to "No type"); the API can, and the API rule is the contract (decision 4).

**Why it matters.** It is the residue of BR1-01: a coder who follows § 5.3 literally leaves a 500 path. The fix is pure and one line, because the stored type is always of the stored class (`fk_equipment_type` guarantees the pair).

**Options.**
- **(a) Recommended.** Add a row to § 5.1's second table: "update, the class after the write differs from the stored one, and `type_id` equals the stored `type_id` (not `null`) → 400 'This type belongs to another class' (`type_id`)" — decided in `validate_equipment` from `stored`, no lock. § 5.3 (5a) stays as written. Add the two cases above to § 8's core tests. Then "`type_id` alone → checked against the stored class" (§ 8) also has a pure case: `type_id` = stored, class unchanged → accepted and dropped.
- (b) Lock and check the type (5a) whenever the class after the write differs from the stored one, newly picked or not. Works, but a lock for a decision the stored row already answers.

### BR2-02 — minor — The refusal text for a `class_id` or `type_id` that is not an id is undecided, and the form's class placeholder would trigger it

**Problem.** § 5.1: "Wrong types (`class_id: "x"`, a bool, a negative number) → 400, as the other id fields (`_parse_model_id`'s rule)". Two readings: `_id_parser("Class", …)` answers "Class must be a record id"; `_parse_model_id`'s rule answers the missing-field text, here "Pick a class". The coder picks one alone, and the user can see it: § 1.5 renders *Class* with the disabled placeholder "Select a class…" (value `""`), and the `toBody` bullet for `NO_MODEL` says "`class_id`, and `type_id` (`null` for 'No type')" — it does not say `""` → `null` for the class. A user who picks *No model* and saves without a class then sends `class_id: ""`, and sees whichever text the coder chose, "Class must be a record id" being a Scope B failure (a field name, no action).

**Why it matters.** A text the user sees on the floor, and a rule set in two places (validator and `toBody`) by the coder alone.

**Options.**
- **(a) Recommended.** § 5.1: a `class_id` or `type_id` that is neither `null` nor an id → the same text as missing, "Pick a class" / "Pick a type of the new class, or No type" is wrong here, so for the type use the existing `_id_parser` text or state a short one ("Pick a type"). Simplest: "Pick a class" for the class; "Pick a type" for the type (a new constant). § 1.5 `toBody`: `class_id: null` for the placeholder `""`, so the backend's "Pick a class" is the one text, as for the model today (`model_id: null` for `""` on create is not possible any more, but the class works the same way).
- (b) Keep `_id_parser`'s "… must be a record id" and refuse `""` in the form before sending. Puts the rule in the frontend as well (rejected for the model in decision 9).

## Nits

- **BR2-03** (nit) § 1.5 the form: keep `class_id` and `type_id` as keys of the form object at every state (in `COMMON_BLANK` and `fromRecord`), and let `toBody` drop them when a model is picked. `useFormModal.modalError` shows a refusal at the top when `error.field in form.value` is false (`useFormModal.js:52–54`); without the keys "Pick a class" shows twice, at the top and beside the field.
- **BR2-04** (nit) § 1.5 hint: hide "This class has no model yet. Pick No model, or add a model …" once *No model* is picked. The class filter is hidden then but `classFilter` keeps its value, so `showNoModelHint` stays true and tells the user to do what they just did.
- **BR2-05** (nit) § 1.5 help: say that the existing line under *Model* ("The model's class sets the code prefix. A model of another class later keeps the code.", `EquipmentFormModal.vue:237`) is replaced by "Without a model, the class sets the code prefix." while *No model* is picked, else two prefix lines show, one about a model that is not there.
- **BR2-06** (nit) § 8 `_update` (test helper): give its new `stored_model_id` a non-None default (for example `2`), so the update half of `test_old_fields_are_refused_even_as_null` keeps asserting the refusal for `class_id` / `type_id`; name the default in § 8.
- **BR2-07** (nit) § 8 "`type_id` alone → checked against the stored class": the class membership of a type is a database check (`lock_type_of_class`), so in `test_equipment_core.py` this case can only assert "accepted"; put the 400 "This type belongs to another class" case in `test_equipment_api.py`'s new tests (BR2-01 (a) adds the one pure case).

## Checked and found consistent

- § 5.1 ↔ § 1.5 ↔ § 6 ↔ § 8 on the body: an absent `model_id` on create is "Pick a model" at every level (`_fields` keeps `model_id` required; `test_required_fields_per_level`'s `component_unit` row stays); `""` in the form leaves the key out; `NO_MODEL` sends `model_id: null` plus class and type; a model id sends neither. `test_no_model_is_400` and `test_a_null_model_on_update_is_400` are on level equipment and keep passing (`test_equipment_api.py:1136, 1162`).
- § 5.1 "with a model (sent, or stored and not cleared)": the stored model is available once `stored` gains `model_id` (`update_equipment` reads it through `LOCK_EQUIPMENT`, `equipment.py:172, 738`); `_REFUSED_FIELDS`' two rows become conditional, the three other rows stay.
- § 5.2 "newly picked" fits `update_equipment`'s "same value sent back is no change" loop (`equipment.py:742`): adding `class_id` and `type_id` to it drops an unchanged pair before any lock, so an unchanged inactive class or type is kept, as the model is.
- § 3 `_lock_class` (`equipment.py:369–379`) and `_lock_type_for_model` (`masters.py:467–477`) are as cited; the messages in § 5.2 are their existing texts; `masters.py` imports nothing from `equipment.py`, so the import runs one way. `update_equipment_class` counts active models only (`masters.py:338`), as § 5.2 says.
- § 5.4: `_display` / `tracked_changes` in `equipment_core` are the one place for "No model" beside `INHERIT` and `NO_TYPE`; `_tracked_state` and `_summary` both call `model_label`, so `model_label(None, None) → None` covers the history and the responses; `describeEvent` passes model values through (`equipmentLabels.js:72–74`).
- § 5.5: `NODE_JOINS` (`equipment.py:115–125`) is the one fragment for list, detail, tree, by-code, labels, asset list and the documents owner read; `documents._inherited` (`documents.py:217`) returns `[]` for `model_id` NULL (`WHERE model_id = NULL` matches nothing), so the skip is for clarity, as § 3 says.
- § 4: `fk_equipment_model (model_id, class_id)` and `fk_equipment_type (type_id, class_id)` are as cited (`local_db.py:339–340`); the CHECK holds for every existing row; `ADD CONSTRAINT IF NOT EXISTS` is the pattern v22 used for `chk_tickets_plan` (`local_db.py:613`). Rollback stated with both effects (vanishes from lists, 409 on edit).
- § 8 e2e: the e2e extruder exists at SMTW.MCC2 (`seed_e2e.py:56`), the engineer holds `maint_engineer` on every SMTW unit (`seed_e2e.py:42`), *Add part* is on the equipment page for levels other than component (`EquipmentDetailView.vue:181`), the list reads `level` and `q` from the URL and offers `component_unit` (`EquipmentView.vue:30–35, 53–54, 134`), the *Model* column is `e.model_label` (`EquipmentView.vue:359`), and `expectDialogFits` is in `e2e/support/dialogs.js`. The three existing dialogs pick "Atlas Copco GA37 — CMP / Screw compressor" on level equipment (`equipment.spec.js:51, 67, 202`), so the "not offered" check covers them.
- § 2: ISO 14224 now reads as the standard does (equipment data on the equipment unit, taxonomy level 6; subunits named by subdivision in Annex A); ISO 55001 § 7.5 is the right clause; "to verify against the user's copy" kept. Plan.MD § 4.1 line 236 is the one sentence to change.
- Decisions 7–10 each name the rejected alternative; none adds an abstraction.
- Scope B texts added this round ("Pick a type of the new class, or No type", "Without a model, the class sets the code prefix.", "This class has no model yet. Pick No model, or add a model in Masters › Models.") are short, say what to do, and use the dialog's existing words.
- No real-device check is right: two more selects in an existing dialog, the fit checked by the e2e test on the three projects.
