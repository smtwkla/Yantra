```
Step: S033 — Model optional on component-units
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 23-10-2026
```

Reviewed against: 6ab6af0 (nothing of a step is uncommitted; only this step's folder and the README row).

**Verdict: no `blocker` or `major` finding is open.** Two `minor` findings and two nits. Full track, round 3 (the last round). Facts file `scratch/brief-facts-S033.md` (re-run) used; the three "not found" names (`NO_MODEL`, `lock_type_of_class`, `PICK_A_TYPE`, `test_migration_v28.py`) are the new ones.

Sections re-read, as changed by the round 2 answers: § 1.5 (the body, form keys, hint, help, refusals); § 3 the messages list; § 5.1 (the new row 8 and the non-id paragraph); § 6; § 8 (core cases, `_update`, the API cases); the Review log. Every round 2 finding marked `Accepted` is in the brief's text, not only in the log: BR2-01 § 5.1 row 8 and § 8; BR2-02 § 5.1 last paragraph, § 3 `PICK_A_TYPE`, § 1.5 `toBody`, § 8; BR2-03 § 1.5 *Form keys*; BR2-04 § 1.5 *Hint*; BR2-05 § 1.5 help text; BR2-06 § 8 `_update` default `2`; BR2-07 § 8 core "accepted" and the API case. Sections not changed were not re-read.

## Findings

### BR3-01 — minor — `toBody` with nothing picked (`""`) may still send `class_id` / `type_id`, and § 5.1 has no row for them when `model_id` is absent on create

**Problem.** Since BR2-03, `class_id` and `type_id` are keys of the form object in every state. § 1.5 says `toBody` "drops them when a model is picked" and, for `""`, only that "`model_id` is left out". A literal coder sends `class_id` and `type_id` (as `""` or `null`) with an absent `model_id`. § 5.1 then has no row: "with a model" needs a model sent or stored; "without a model" needs `model_id: null` sent or stored NULL. On create with `model_id` absent neither holds, so what the validator does with `class_id` is the coder's choice.

The order of the errors matters too: `clean_body` answers `errors[0]` only (`api_common.py:124`), and `validate_equipment` runs the refused-fields loop before the field loop (`equipment_core.py:281–305`). If the first error lands on `class_id` while the *Class* field is hidden (it shows only under *No model*), the user sees nothing: `class_id` is a form key, so `modalError` is empty (`useFormModal.js:52–54`), and `fieldError('class_id')` renders only inside the hidden block. A tap on *Save* then does nothing visible. § 1.5 *Refusals* claims "Pick a class lands on the *Class* field, which is on screen whenever it can be sent"; that claim holds only if the form sends `class_id` under *No model* alone.

**Why it matters.** Two rules the coder would set alone (what `toBody` sends for `""`, and the validator's answer to a stray `class_id`), and one path where a refusal can show nowhere, which S026 set out to end.

**Options.**
- **(a) Recommended.** § 1.5 *The body*: `class_id` and `type_id` are sent only when `form.model_id` is `NO_MODEL`; for `""` and for a model id `toBody` drops them. § 5.1: add a row "Create, `model_id` absent, `class_id` or `type_id` in the body → 400 'Pick a model' (`model_id`): the model is checked first, so `errors[0]` is on `model_id`; the class and type keys are not reported". One core test: `_create(level="component_unit", parent_id=5, name="x", class_id=None)` → the one error is on `model_id`.
- (b) Refuse the stray keys as "Class comes from the model" / "Type comes from the model" after the model error. The text is wrong when there is no model, and the order rule is still needed.

### BR3-02 — minor — § 5.1 row 8 does not say the restated type is an id, so a cleared type on a class change can be read as "equals the stored type"

**Problem.** Row 8: "Update: the class after the write differs from the stored one, and the sent `type_id` equals the stored type → 400 'This type belongs to another class'". When the stored type is NULL and the body sends `class_id: B, type_id: null`, `None == None` is true, so a coder who writes the row as given refuses the save. Row 6 ("`type_id: null` → no type") says the opposite for the same body; the table does not say which row wins. The form produces exactly this body: a class change resets *Type* to "No type" (§ 1.5 *Resets*), on a node whose type was already none.

**Why it matters.** The form's everyday path (change the class of a no-model component-unit that has no type) can end in a wrong 400, and the coder has two rows that contradict for one body. BR2-01 (a) said "(not `null`)"; the brief dropped it.

**Options.**
- **(a) Recommended.** Row 8: "… and the sent `type_id` is an id equal to the stored type …". Add the core case: stored type `None`, `class_id: B, type_id: None` → accepted, no type.
- (b) State that the rows are read in order and the first match wins. Weaker: the order is implicit and the test does not pin it.

## Nits

- **BR3-03** (nit) § 8 `_update`: name the defaults of the new `stored_class_id` and `stored_type_id` (for example `3` and `None`). The new "accepted" cases depend on them: `model_id: null` with a `class_id` is accepted only when that `class_id` equals the stored default or a `type_id` is sent (row 4), and the BR2-01 case needs a stored type.
- **BR3-04** (nit) § 1.5 help text under *No model*: "Without a model, the class sets the code prefix." drops the second half of the line it replaces ("A model of another class later keeps the code."). § 1.3 keeps that rule for a direct class change too. Suggest "Without a model, the class sets the code prefix. A class change later keeps the code." so the user who edits a class is not surprised that the code stays.

## Checked and found consistent

- § 5.1 row 8 (BR2-01) is pure and right for a non-null type: `fk_equipment_type (type_id, class_id)` (`local_db.py`) holds that the stored type is of the stored class, so a restated type with a changed class can never fit; no lock is needed, and § 5.3 (5a) ("only when a write without a model newly picks a type") stays as written.
- § 5.1 ↔ § 1.5 ↔ § 6 on the body, apart from BR3-01: `""` leaves `model_id` out (create → "Pick a model" on a field on screen; `""` cannot occur on edit, the placeholder is disabled); `NO_MODEL` sends `model_id: null` with `class_id` (`null` for the placeholder, so "Pick a class" is the one text) and `type_id` (`null` for "No type"); a model id sends `model_id` only. § 6 says the same for `POST` and `PUT`.
- § 1.5 *Form keys* ↔ `useFormModal.js:52–54`: with `class_id` and `type_id` in `COMMON_BLANK` and `fromRecord`, "Pick a class" shows beside the field and not at the top. Node responses carry `class_id` and `type_id` (`equipment.py:129`), so `fromRecord` can load them.
- § 1.5 *Hint* and help: `showNoModelHint` reads `classFilter` (`EquipmentFormModal.vue:98`), which keeps its value while the filter is hidden, so the brief's "hides once *No model* is picked" is the needed extra condition; the help line at `EquipmentFormModal.vue:237` is the one replaced.
- § 3 messages list ↔ § 5.1 ↔ § 8: `PICK_A_CLASS`, `CLASS_FROM_MODEL`, `TYPE_FROM_MODEL`, `PICK_A_TYPE_OF_CLASS`, `PICK_A_TYPE` each appear in a § 5.1 rule and a § 8 case; the texts are the same in all three sections. The non-id rule ("Pick a class" / "Pick a type") means `_id_parser`'s "… must be a record id" never reaches the user.
- § 8 `_update` default stored model `2` (BR2-06): the update half of `test_old_fields_are_refused_even_as_null` (`test_equipment_core.py:299–302`) and the create half (`EQUIPMENT` has `model_id: 2`) both keep a model, so the two rows still assert the refusal with the new texts. `test_a_model_may_be_left_out_on_update_but_not_cleared` stays on level equipment; the new `stored_level="component_unit"` case is separate.
- § 8 API: `TestModels.test_old_fields_are_refused_even_null_or_unchanged` (`test_equipment_api.py:1172`) uses `make_equipment()` and a create with a model, so only its two texts change; `test_no_model_is_400` (1136) and `test_a_null_model_on_update_is_400` (1162) are on level equipment and keep passing.
- § 8 core "`type_id` alone → accepted" and the API case "a `type_id` of another class → 400 'This type belongs to another class'" (BR2-07) split the one check between the pure and the database layer correctly: class membership of a *newly picked* type is `lock_type_of_class`'s check; the pure row 8 covers only the restated stored type.
- § 1.4 "model → no model: the form keeps the class and type" ↔ § 5.1: the body `model_id: null, class_id: <stored>, type_id: <stored>` has an unchanged class, so row 8 does not fire, nothing is newly picked, no lock runs, and the row keeps its class and type. § 1.5 *Defaults* prefill exactly that body.
- Scope B texts changed this round ("Pick a class", "Pick a type") are short and start with a verb.
