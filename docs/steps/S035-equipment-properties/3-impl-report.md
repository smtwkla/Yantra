Step: S035 — Equipment properties: master, classes and models
Doc: impl-report
Author: Coder (Opus)
Date: 24-10-2026

# S035 — Implementation report

**Result:** the property master, the class links, the model values, the 22-row seed (v26) and
the Properties card on the equipment page are built as the brief says. Backend, frontend, deps
and tooling suites pass (2446 / 127 / 42 / 106). The targeted S035 e2e tests pass on desktop and
phone Chromium. The full e2e suite on the two Chromium projects: 189 passed, 3 skipped, 0 failed. WebKit (phone-webkit)
could not run in this sandbox (§ 6).

## 1. What was built

- **Migration v26** (`local_db.py`): the four tables of brief § 4.1, exactly as given, with
  `chk_property_unit`, `chk_model_property_one_value` and the option's composite FK. Then the
  seed of § 4.6: 22 properties and the options of the five choice properties, `created_by =
  'migration-v26'`, `INSERT IGNORE` on the name. No class links. No `_PRECONDITIONS` entry (new
  tables and rows only, § 4.3).
- **Masters › Properties** (new section after *Models*): a table *Name*, *Type* ("Number · kW",
  "Choice · 2 options", "Text", "Yes / No"), *Classes*, *Active*, *Show inactive*; **Add
  property** and **Edit** for `equipment:edit`. The dialog has name, data type, unit (number
  only), options (choice only: one input per option, **Add option**, an *Active* switch on a
  saved option), description, and the deactivate / reactivate toggle. The two "fixed" rules and
  their help lines of § 7.1 are there.
- **Class properties** (U6): on *Masters › Equip Class*, a row's **Properties** button replaces
  the class table with the class's table (*Name*, *Type*, *Unit*, **Remove**), the heading, the
  help line, the grey note and **Back**. **Add property…** opens the picker: a search box, tick
  boxes of the active properties not yet on the class, a choice with no active option disabled
  with "(no options yet)", **Add properties** (disabled until one is ticked).
- **Model values**: on *Masters › Models*, a row's **Properties** button opens the dialog
  "Properties of <model label>" with one `PropertyInput` per active property of the class
  (number with `inputmode="decimal"` and its unit, choice select with "—", text, Yes / No / Not
  set) and **Save values**. A class with no properties shows "The class <code> has no
  properties yet. Add them in Equip Class." and only **Close**.
- **Properties card** on the equipment page, beside *Details*: name and value ("62.5 kVA" or
  "—"), "Values from model <model label>.", and **Edit model values** for `equipment:edit` at
  any site (`canEditModels`), on every lifecycle. It opens the same model dialog; a save reloads
  the page. The card is hidden when the class has no active property.
- **API** (`properties.py`, blueprint at `/api/masters`): every route of brief § 6.1 and § 6.2,
  and `properties` on `GET /api/equipment/<id>` (§ 6.3).

## 2. How it works

- **Pure core** (`properties_core.py`), plain data in and out:
  - `validate_property` / `validate_option`: the field rules and messages of § 5.1; on create,
    `options` is a list of labels.
  - `property_changes(stored, clean, has_options, has_values)`: checks the record as it will
    be (BR1-03). A unit on a non-number is a 400; a type leaving *number* adds `unit = None`
    to the same write; a type change with options or values, and a unit change with values,
    are 409.
  - `parse_value(data_type, raw, options, stored_option_id)`: the value rules of § 5.2.
    Blank means clear. A number string must be plain digits (`-?digits(.digits)?`); the
    decimals are then counted on the value, so "0.00001" gets "Use up to 4 decimals". A
    number goes through `Decimal(str(...))`, never through a float.
  - `number_text` / `format_value` / `stored_value`: "62.5" and "62.5 kVA", never "62.5000"
    or "1E+2" (`format(value.normalize(), "f")`).
  - `parse_property_ids`, `can_link`: the class add's list (read as a set, ascending) and its
    rule (active; a choice has an active option).
  - `parse_value_keys`, `check_model_values`: the model save (§ 5.3). Keys must be positive
    whole numbers. An unknown, inactive or unlinked property is refused first. Then the values
    are checked by property name, and the first refusal answers with `field: "values.<id>"`.
  - `property_view`: the card rows, by name, with `source` "model" or None.
- **Shell** (`properties.py`): fetches, locks and stores in the LOCK ORDER of its docstring:
  (1) the class or the model row, (2) the property rows by id ascending `FOR UPDATE`, (3) the
  option rows. The "options or values exist" checks of a property edit are locking reads (`LOCK
  IN SHARE MODE`), as § 5.6 says. A model save upserts with `INSERT … ON DUPLICATE KEY UPDATE`
  and clears with `DELETE`. Duplicate names and labels are caught by the UNIQUE indexes through
  `api_common.UNIQUE_KEY_ERRORS` (409). `equipment.py`'s LOCK ORDER note has one more bullet
  for `properties.py`.
- **Equipment detail**: `equipment._detail` calls `properties.equipment_properties(cur,
  class_id, model_id)`, a plain read.
- **Frontend**: the dialogs use `useFormModal` (`useMasterForm` for the property dialog) and
  `send(request)` where a save is more than one request or not a plain POST/PUT:
  - the model dialog fetches `GET …/properties` first and opens with the answer as its seed
    (BR2-03). Its form is keyed `"values.<id>"`, so a refusal shows under its input (BR1-07);
  - the picker's form is `{property_ids: []}`, so a refusal shows under the list;
  - an edit of a property is a `PUT` of the property, then a `PUT` per changed option and a
    `POST` per new one. A new option's id is kept at once, so a second **Save** after a
    refusal does not add it twice. An option's refusal shows under the options list.

## 3. Files touched

Backend:

| File | Change |
|---|---|
| `backend/local_db.py` | migration v26: four tables, the seed and its options |
| `backend/properties_core.py` (new) | the pure rules (§ 5) |
| `backend/properties.py` (new) | `properties_bp`: the routes of § 6.1–6.2, LOCK ORDER note, `equipment_properties` |
| `backend/app.py` | registers `properties_bp` at `/api/masters`, after `masters_bp` |
| `backend/equipment.py` | `_detail()` adds `properties`; one LOCK ORDER bullet for `properties.py` |
| `backend/tests/test_properties_core.py` (new) | 74 tests of the pure rules |
| `backend/tests/test_properties_api.py` (new) | the routes, refusals, links, values, permissions, database down |
| `backend/tests/test_migration_v26.py` (new) | fresh database with the seed, the CHECKs and FK, upgrade from v25, re-run |
| `backend/tests/test_equipment_api.py` | `TestProperties`: the detail's `properties` |
| `backend/tests/conftest.py` | the two link and value tables in `_TABLES`; `_SEED_CREATORS` (a creator per seeded table, `SEED_CREATOR` kept); the shared `db_down` fixture |
| `backend/tests/test_access_control_api.py` | its own `db_down` removed |
| `backend/tests/test_auth.py` | its own `db_down` removed, and the two imports only it used |
| `backend/tests/test_health.py` | the comment names `conftest`'s `db_down` |

Frontend:

| File | Change |
|---|---|
| `frontend/src/views/MastersView.vue` | the *Properties* section after *Models* |
| `frontend/src/views/masters/PropertiesPanel.vue` (new) | the list and the property dialog |
| `frontend/src/views/masters/ClassPropertiesView.vue` (new) | a class's table, *Add property…*, *Remove*, *Back* |
| `frontend/src/views/masters/AddPropertiesModal.vue` (new) | the picker |
| `frontend/src/views/masters/ModelPropertiesModal.vue` (new) | the model values dialog |
| `frontend/src/views/masters/EquipmentClassesPanel.vue` | the row's *Properties* button and the view switch |
| `frontend/src/views/masters/ModelsPanel.vue` | the row's *Properties* button and the dialog |
| `frontend/src/views/EquipmentDetailView.vue` | the *Properties* card and *Edit model values* |
| `frontend/src/components/PropertyInput.vue` (new) | one input per data type |
| `frontend/src/components/FormModal.vue` | new prop `closeOnly`: the footer shows only **Close** (decision 1) |
| `frontend/src/utils/propertyFormat.js` (new) | data-type labels, the type summary, "—" for no value |
| `frontend/src/stores/masters.js` | `properties`, `ensureProperties()`, reset in `resetMasters()` |
| `frontend/tests/propertyFormat.test.js` (new) | the display rules |
| `frontend/e2e/support/properties.js` (new) | the S035 setup by API: a class, model and machine of its own, properties, links, values |
| `frontend/e2e/masters.spec.js` | four S035 tests |
| `frontend/e2e/equipment.spec.js` | three S035 tests |

Docs: this report. The brief's § 11 doc edits were done by the planner and are untouched.

## 4. Decisions taken

1. **FormModal got a `closeOnly` prop** (shared code). The brief wants two dialog states with
   "only **Close**" (§ 7.2 picker, § 7.3 model dialog), and `FormModal` always shows *Cancel*
   and *Save*. A default-off prop is the smallest change and keeps one dialog component. The
   rejected option was a second hand-written Bootstrap modal (a near-copy). Because
   `FormModal.vue` changed, the full e2e suite was run (§ 6).
2. **Properties buttons only for `equipment:edit`.** § 8.4 says an operator sees no
   *Properties* buttons on classes and models; § 7.2 also says users without `equipment:edit`
   see the class table without *Add property…* and *Remove*. Both hold as built: the buttons
   are hidden for non-keepers, and `ClassPropertiesView` hides its edit controls for them too.
   So today a non-keeper sees a class's properties only through the equipment card. **Please
   confirm** (question 1 below).
3. **The Masters list column is headed *Active*, not *Status*** (the glossary reserves
   *Status* since S030, and the queued tidy-up renames the other panels' column the same way).
4. **Option order**: options are listed in the order they were made (by id), so the seed shows
   "Mechanical seal, Packed gland, Lip seal, Seal-less" as the brief lists them. The brief does
   not say.
5. **The seed's options** are one `INSERT IGNORE … SELECT` per option, generated in `local_db.py`
   from a constant table, so the ids keep the listed order (the brief's statement form, § 4.6).
6. **A label twice in a new choice's `options`** (case-insensitive) is refused by the core with
   "An option with this label exists" on `options`, before the UNIQUE index would refuse it on
   `label`, a field the create dialog does not show.
7. **Messages the brief does not give** (API clients only; the screens never send these):
   - `active` not a flag: "Active must be true or false" (as `masters_core`);
   - a text value that is not a string: "Enter text";
   - a unit or description that is not a string: the field's own length message, as § 5.1's
     "a wrong type is a 400 with the field's message".
8. **Screen texts the brief does not give** (scope B):
   - the picker's search placeholder "Search by name" and its empty result "No property
     matches the search.";
   - the *Add properties* tooltip while nothing is ticked: "Tick at least one property";
   - the description's help line "What the property means and where to read it. Optional.";
   - the empty Masters list "No properties yet.";
   - the dialog field label *Data type* with the placeholder "Select a data type…".
9. **The Back link** of the class view reads **Back**, as § 7.2 says (the Models documents
   view reads *Models*).
10. **Shared e2e setup** in a new `e2e/support/properties.js`: both specs need a class, a model
    and a machine of their own, so the setup is not copied.
11. **`POST …/options` answers the option** (`{id, property_id, label, active}`), not the
    whole property; the brief gives only the status (201).

## 5. Not done, deferred or assumed

- **S036** (overrides on an equipment item, logged): not built, as the brief says.
- **WebKit not run**: the sandbox has no WebKit build, so `phone-webkit` was not run. The user's
  full run before the release covers it.
- **Assumed**: the README index row and the brief's `Status` are set by the orchestrator (asked
  not to edit the Status line).
- **Not verified**: the seed's ISO 14224 Annex A names and option lists are as the brief gives
  them; the brief marks them "to verify against the text".

## 6. Tests run

- Backend, full suite (`YANTRA_TEST_RUN=s035c1`, 8 workers): **2446 passed**.
- Frontend (vitest): **127 passed** (15 files). `npx vite build`: built; only the old chunk-size
  warning.
- Deps tests: **42 passed**. Tooling tests: **106 passed**.
- e2e, new tests alone (`E2E_LANES=1`, desktop-chromium, `-g S035`): **7 passed**.
- e2e, full suite on phone-chromium and desktop-chromium (lanes): **189 passed, 3 skipped, 0 failed** (2.9 min); the 14 S035 tests (7 per project) are among the passed. Why the full suite:
  the step changes `FormModal.vue` and adds a file under `e2e/support/` (CLAUDE.md § Browser
  tests). It covers the targeted specs (`masters.spec.js`, `equipment.spec.js`) and
  `screens.spec.js`.

## Manual checks

The brief has no real-device checks (§ 8.5), so no rows were added to `device-checks.md`.

- [auto] **important** An engineer adds a choice property with two options, adds it to a class through *Add property…* (two ticked at once, both rows appear), sets it on a model, and the equipment page shows the value — `frontend/e2e/masters.spec.js`::`S035: engineer adds a choice property, adds two properties to a class at once and sets one on a model; the equipment page shows it`
- [auto] **Remove** on the class table takes the row away, and the picker lists the property again — `frontend/e2e/masters.spec.js`::`S035: Remove on a class's table takes the row away, and the picker lists the property again`
- [auto] **important** A number value with its unit shows as "62.5 kVA" on the card — `frontend/e2e/equipment.spec.js`::`S035: a number value with its unit shows as 62.5 kVA on the card`
- [auto] A refused number ("abc") shows "Enter a number" under its input — `frontend/e2e/masters.spec.js`::`S035: a refused number shows Enter a number under its input`
- [auto] An operator sees the *Properties* section read-only (no *Add property*, no *Properties* buttons on classes and models) — `frontend/e2e/masters.spec.js`::`S035: an operator sees the Properties section read-only, and no Properties buttons on classes and models`
- [auto] **Edit model values** on the card opens the model dialog; after a save the card shows the new value — `frontend/e2e/equipment.spec.js`::`S035: Edit model values on the card opens the model dialog; after a save the card shows the new value`
- [auto] The property dialog, the picker and the model dialog (on a model whose class has properties) fit a phone — `expectDialogFits` in `frontend/e2e/masters.spec.js`::`S035: engineer adds a choice property, …` (all three dialogs) and in `S035: a refused number …` and `frontend/e2e/equipment.spec.js`::`S035: Edit model values …`; passed on phone-chromium and desktop-chromium, not on phone-webkit (not available here)
- Extra (not a brief check): the card is hidden when the class has no property — `frontend/e2e/equipment.spec.js`::`S035: the card is hidden when the class has no property`

## Questions for the user

1. **Who sees a class's properties table?** As built, the *Properties* buttons on Equip Class
   and Models show only to `equipment:edit` (§ 8.4); others see properties only on the
   equipment card. Options: (a) keep it so — **recommended**, it matches § 8.4; (b) show the
   class button to everyone with the read-only table of § 7.2 (then the § 8.4 check changes
   for classes).

## Fix rounds

None yet.
