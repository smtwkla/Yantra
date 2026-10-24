```
Step: S033 — Model optional on component-units
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S033 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the brief asks for, the
rules of § 5.1 and § 5.2 hold in the code, and all four suites are green. There is 1 `minor`
finding (a test gap in the form's default rules) and 2 nits.

## Test runs (this review)

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s033cr1 tooling/run-tests.bat` | backend 2519 passed, frontend 130 passed, deps 42 passed, tooling 106 passed — ALL SUITES PASSED |
| `npx vite build` (frontend) | built; only the existing chunk-size warning |
| E2E | Not re-run. The coder's targeted run (`equipment.spec.js`, `asset-list.spec.js`, `screens.spec.js`) passed 69 of 69 on all three projects. No finding of this review needs a browser run. The specs chosen are the right ones: no shared frontend code changed. |

## Findings

### CR1-01 (minor) — the form's default and reset rules have no test

- **Where:** `frontend/src/views/equipment/EquipmentFormModal.vue:127-142` (`onModelChange`,
  `onClassChange`, `onLevelChange`).
- **Problem:** the brief's § 1.5 *Defaults* and *Resets*, and Decision 4 of the impl report, live
  only in these three handlers. No unit test or e2e test covers them. The new e2e test covers
  only the create path with no class filter, and that path never takes the Decision 4 branch.
  Decision 4 exists to stop a save that always fails, so a regression there is the likely one.
- **Failure scenario:** a later edit drops the `form.class_id === currentClassId` condition. An
  engineer edits a component-unit that has a model, sets the class filter to another class, and
  picks *No model*. *Type* then keeps the node's old type, and every save answers "This type
  belongs to another class". No test fails.
- **Fix:** move the prefill into a pure helper in `modelPicker.js`, beside
  `noModelClassChoices`. For example, `noModelDefaults({ classFilter, currentClassId,
  currentTypeId })` → `{ class_id, type_id }`. Give it vitest cases for these four inputs: a
  filter set, no filter on edit, no filter on create, and a filter equal to the node's class.
  The handler then only assigns the result. Another way: add one e2e test that edits a
  component-unit with a model to *No model* and saves.

## Nits

- **CR1-02** (nit) `backend/tests/test_equipment_api.py` (`TestNoModel`): add an
  "unchanged inactive **type** is kept" case beside `test_an_unchanged_inactive_class_is_kept`.
  Brief § 1.3 states the same rule for the type, and today only the class is tested.
- **CR1-03** (nit) `backend/equipment_core.py:321` (`_check_class_and_type`):
  `check_type_class(stored_class, clean["class_id"])` always returns the message on this path.
  Add a short comment that it is called for its one wording (Decision 10), so a reader does not
  look for a `None` branch.

## Departures and choices the coder reported

| Choice | Judgement |
|---|---|
| `test_migration_v9.py` changed (not in brief § 8) | Accepted. Both tests asserted the NOT NULL rule that v28 removes. The second test keeps its intent: the same insert is refused, now by `chk_equipment_model_level` (4025). The change is reported in Decisions 1. |
| New `_pick_class_and_type` helper in `equipment.py` | Accepted. It sits beside `_pick_model`, adds no lock code of its own, and reuses `_lock_class` and `lock_type_of_class` (brief decision 10). It is right-sized. |
| An unchanged `class_id` / `type_id` is dropped in the update loop | Accepted and correct. This is how "newly picked" (§ 5.2) reaches the locks, so an unchanged inactive class or type is never locked or refused. I checked that no case drops a value the validator still needs. The validator refuses "class changed + stored type restated" before the drop runs. A `null` type that equals a stored `NULL` is a no-op either way. |
| Type kept on *No model* only when the prefilled class is the node's own | Accepted. It resolves a gap in the brief: with a class filter of another class, the brief's literal rule would make every save fail. It is reported as Decision 4. Its only gap is the missing test (CR1-01). |
| `@change` handlers instead of watchers | Accepted. Watchers would fire while `fromRecord` loads a record, which would change the form and mark the dialog as edited. A handler runs only on a user's pick. |
| Two pure helpers in `modelPicker.js` | Accepted. They share one filter (`activeOrCurrent`, `inactiveMark`) with `modelChoices`. No existing helper lists "active, plus the current one marked (inactive)" for classes or types. The inline marks in `EquipmentView.vue` list every record, which is a different rule. Unit-tested. |

## Checked and found consistent

- **Validation (§ 5.1):** every row of both tables is in `_check_class_and_type`, including these:
  - an absent `model_id` on create gives "Pick a model" alone (BR3-01);
  - `class_id` / `type_id` beside a sent or stored model are refused, even as `null`;
  - a class is required on create and when the write clears a model;
  - a class change without `type_id` gives "Pick a type of the new class, or No type";
  - a class change that restates the stored type is refused (BR2-01), but not when that type is `null` (BR3-02);
  - a value that is not an id gives "Pick a class" / "Pick a type".

  The `stored` dict is read only on update paths. On create every branch short-circuits before it.
- **Shell (§ 5.2, § 5.3):**
  - on create, the class is always locked, because its code is the prefix;
  - on update, the class and the type are locked only when newly picked;
  - the type is checked against the class the row will hold;
  - the order is class (5) before type (5a), the order `masters.py` takes too;
  - `masters.py` does not import `equipment.py`, so there is no import cycle;
  - a write with a model still never locks a type.
- **Database (v28):**
  - `MODIFY model_id INT NULL` matches the v20 column definition, with no lost attribute;
  - the CHECK has `IF NOT EXISTS`, and the re-run test passes;
  - `fk_equipment_model` stays, and the migration test confirms that a model must still match the node's class;
  - no `_PRECONDITIONS` entry is needed, because every existing row has a model.
- **Reads (§ 5.5):**
  - `NODE_JOINS` left-joins the model and the manufacturer;
  - `model_label(None, None)` is `None`;
  - no other backend query joins `equipment_models` for nodes (grep);
  - `documents._inherited` skips a node without a model.
- **History (§ 5.4):** `_display` maps a `None` model label to "No model", so the history shows
  "… → No model" and back. Both directions are tested in the core tests and in the API tests.
- **Security:** no route and no permission changed. Writes stay on `equipment:edit` at the
  node's site. The actor comes from the session. Every SQL statement is parameterised.
- **Form (§ 1.5):**
  - the `NO_MODEL` sentinel is used;
  - `class_id` and `type_id` are form keys in every state;
  - `toBody` gives the three bodies of the brief: `""` leaves all three keys out;
  - `fromRecord` loads a node without a model as `NO_MODEL`;
  - the class filter is hidden and the help line is replaced while *No model* is picked;
  - the hint text reads as approved and hides on *No model*;
  - an unchanged inactive class or type stays listed and is marked "(inactive)".
- **Screens (§ 1.6):** the equipment page shows *Model* "No model" and no *Manufacturer* line.
  The list and the printed asset list show "—". The asset list's phone line already leaves out
  empty values.
- **Use on the floor (UX):**
  - the two new selects are in `col-sm-6` columns, so they stack on a phone;
  - the selects are full size (not `form-select-sm`), so the tap targets are not shrunk;
  - the dialog is the existing `FormModal`, and the e2e test checks the fit after *No model* and after *Class*;
  - every new user-facing text is one short line that says what to do ("Pick a class", "Pick a type", "Pick a type of the new class, or No type"), as approved in § 9.1;
  - no new irreversible action.
- **Scope:** everything in § 1 and § 3 is built, and nothing outside it. `schema.html` and the
  overview of `schema.md` are left for the planner at gate B, as the brief allows. The
  rollback note is in the impl report and in the migration comment.
- **Tests:** the § 8 core, API, migration and vitest lists are covered. The important automated
  check is a real e2e test with two `expectDialogFits` calls. It asserts what the user sees:
  "No model", no *Manufacturer* line, the class, and "—" in the list.
- **Impl report:** the `## Manual checks` section carries the important check as `[auto]`, with
  its test and a passing run. The brief has no real-device checks, so `device-checks.md`
  correctly has no new rows. The report follows scope A.

## Manual browser check for the user

None required by the brief. Optional: on a phone, add a part to a machine with *No model*,
then edit it and pick a model again. Check that the history shows the *model*, *class* and
*type* lines.
