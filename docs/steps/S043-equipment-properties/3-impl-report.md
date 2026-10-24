Step: S043 — Equipment properties: master, classes and models
Doc: impl-report
Author: Coder (Opus)
Date: 24-10-2026 (port to main); the branch report below is S035's, kept as history

# S043 — Implementation report

## Port to main (24-10-2026)

**Result:** the branch's S035 code (`git diff 06e16e4 ffb144c`) is on the working tree as
S043, migration **v31**, on top of S037 and S038 (v29, v30), which stay intact. U8 (BS1-01,
BS1-04) is built, and the branch's five code-review findings CR1-01…CR1-05 are fixed. Backend,
frontend, deps and tooling suites pass (2837 / 154 / 42 / 115). The full e2e suite:
354 passed, 6 skipped, 0 failed, on all three projects.

The sections after this one (*1. What was built* … *Fix rounds*) are the branch's report,
unchanged. Where they say S035, S036 or v26, read S043, S044 and v31. Later fix rounds go
under the `## Fix rounds` at the end of the file.

### What was built in the port

- **The branch's step, renumbered.** Migration v26 → **v31**, `migration-v26` →
  `migration-v31`, S035 → S043, S036 → S044 in code, comments and e2e test names. Main's own
  S035 (Me first in the nav) and S036 (ticket tint) references are untouched.
- **A new `backend/tests/test_migration_v31.py`**, on the `test_migration_v30.py` pattern:
  `V30` / `V31` as `range(20, 31)` / `range(20, 32)`, `SEED = "migration-v31"`; the upgrade
  from v30 also keeps a `model_meters` row and `meter_types`. S031's `test_migration_v26.py`
  is not touched.
- **U8, BS1-01 — a component-unit with no model.** The card lists the class's active
  properties with "—". It has no "Values from model …" line and no **Edit model values**.
  The shell decides it explicitly: `values = _model_values(cur, model_id) if model_id is not
  None else {}` (`properties._card_rows`), so no query runs `model_id = NULL`.
- **U8, BS1-04 — who sees the *Properties* buttons.** The class row's button shows to every
  reader; `ClassPropertiesView` already hid *Add property…* and *Remove* without
  `equipment:edit`. The model row's button stays for `equipment:edit` holders only, before
  *Edit* and after S038's *Meters*.
- **CR1-01…CR1-05** fixed (answers below).
- **BS1-09:** the `properties.py` LOCK ORDER docstring has the S038 line (no meter type or
  `model_meters` lock here; both take the model row first).

### Conflicts and how they were resolved

The branch's 18 changed files were merged with `git merge-file` (base `06e16e4`, ours the
working tree, theirs `ffb144c`); no `git merge` or `cherry-pick`, nothing staged. The 12 new
files were copied from `ffb144c` and renumbered.

| File | Conflict | Resolution |
|---|---|---|
| `backend/local_db.py` | the branch's v26 sat where main has v26–v30 | v20–v30 kept as they are; the branch's block appended as **v31** after S038's v30, renumbered; one "Rollback:" line added, as v27–v30 have |
| `backend/equipment.py` | LOCK ORDER note: S038's meters bullet against the branch's properties bullet | both bullets |
| `backend/tests/conftest.py` | the branch's `_SEED_CREATORS` / `PROPERTY_SEED_CREATOR` against S037's `_SEEDED_TABLES` dict | S037's dict kept; two entries added (`"property_definitions": "migration-v31"`, `"property_options": "migration-v31"`); nothing renamed (BS1-02). The `_TABLES` and `db_down` changes merged clean |
| `backend/tests/test_auth.py` | imports | `db_helpers` dropped with the moved fixture; `get_local_db` kept (main uses it) |
| `backend/tests/test_equipment_api.py` | S033's `TestNoModel` against the branch's `TestProperties`, both at the file end | both classes |
| `frontend/src/stores/masters.js` | header comment | one comment naming meter types and properties |
| `frontend/src/views/MastersView.vue` | sections and panels lists | *Properties* between *Models* and *Meter types* (BS1-10) |
| `frontend/src/views/masters/ModelsPanel.vue` | comment, imports, refs, the row buttons, the modals | all of both: *Documents*, *Meters*, *Properties*, *Edit*; `<ModelPropertiesModal>` beside `<ModelMeterFormModal>` |
| `frontend/src/views/EquipmentDetailView.vue` | comment, imports | both; `ticketRowClass` (S036, main) kept |
| `frontend/e2e/equipment.spec.js`, `masters.spec.js` | imports; new tests appended at the end of both | both sets of tests |
| `docs/Plan.MD` | the *Fields* line (S033 on main) next to the *Equipment class* line | main's *Fields* line; the branch's *Equipment class* line with S043 / S044 |

Merged clean: `app.py` (after S038's `meters_bp`), `FormModal.vue`,
`EquipmentClassesPanel.vue`, `test_access_control_api.py`, `test_health.py`,
`Maintenance-Philosophy.md`. The merge ran on LF text; files that were CRLF were written
back as CRLF.

### Code review r1 of the branch: answers

| Finding | Answer |
|---|---|
| CR1-01 (minor) Enter in the picker's search box adds the ticked properties | **Fixed.** `@keydown.enter.prevent` on the search input (`AddPropertiesModal.vue`), with a comment. Test: `S043: engineer adds a choice property …` presses Enter in the search box after one tick and expects the dialog open and the box still ticked. Fails without the fix: the dialog closes, and the next `check()` of the second property times out (60 s); passes with it. |
| CR1-02 (minor) A refused option save leaves half an edit saved and the list stale | **Fixed.** `saveEdit` (`PropertiesPanel.vue`) sends option requests only when the form's type is *Choice*. When an option request is refused after the property's PUT succeeded, the panel calls `resetMasters()` and `reload()` and refreshes the dialog's stored record, then shows the refusal. New test `S043: an option refused on Save leaves the list showing the property's saved name`. Fails without the fix: `Expected substring: "Choice · 1 option"`, element not found (the list still shows the old name); passes with it. |
| CR1-03 (minor) A new option row cannot be taken away again | **Fixed**, the reviewer's option 1: a ✕ button (title "Remove option", label "Remove option N") on a row not saved yet; a saved option keeps only its *Active* switch. Test: `S043: engineer adds …` adds a third row and removes it. Fails without the fix: `getByRole("button", { name: "Remove option 3" })` times out; passes with it. |
| CR1-04 (nit) two seed descriptions lack a full stop | **Fixed** in v31 (*Degree of protection*, *Mounting*). `test_migration_v31.py` checks both texts, and that every seed description ends with a full stop. |
| CR1-05 (nit) unknown, inactive or unlinked properties are refused in key order | **Fixed** in the core, not only noted. `check_model_values` refuses an unknown id first (the lowest; it has no name), then checks every known property in name order, an inactive or unlinked one in its name's place. New test `test_an_unlinked_property_is_refused_in_its_name_s_place`. Fails without the fix: `assert (None, ('values.1', 'This property is not on the class')) == (None, ('values.2', 'Enter a number'))`; passes with it. |

### Decisions taken in the port

1. **CR1-05 fixed in code** (the reviewer asked only for a report line). Brief § 5.3 says
   "checked in the order of the property names"; an unknown id has no name, so it comes
   first. The screens never send such keys, so no user sees a change.
2. **CR1-03: a remove button**, not a silent drop of blank rows on save. A silent drop would
   hide a row the user meant to fill.
3. **CR1-02: refresh after a partial save**, not one atomic request: the brief keeps separate
   option routes (§ 6.1).
4. **Screen texts added** (scope B): the option row button's tooltip "Remove option" and its
   label "Remove option N".
5. **`aria-label="Properties"`** on the class and model row buttons, as S038's *Meters*
   button has. Tests still find them by title.
6. **e2e helper `noModelPart(parent, cls, name)`** in `e2e/support/properties.js`, for the
   BS1-01 test: a component-unit with `model_id: null`, made as admin.
7. **The operator e2e test makes its own class with a property**, so it can open the class's
   table read-only (U8) without depending on another test's data.

### Not done, deferred or assumed

- **S044** (an item's own values, logged) is not built, as the brief says.
- **The API test of BS1-01 passes on the branch's code too**: `WHERE model_id = NULL` also
  returns no rows. The BS1-01 fault was on the card (the model line and the button); the
  e2e test covers that.
- **The seed's ISO 14224 names and option lists** are still "to verify against the text"
  (brief § 2).
- **One backend test failed once** in the first full run:
  `test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed`, a
  `ConnectionAbortedError` (WinError 10053) from the local test server. It is unrelated to
  S043, passed alone, and the next full backend run passed (2837).

### Tests run (port, `YANTRA_TEST_RUN=s043c1`)

- Backend, full suite: **2837 passed** (123 s), after the one flaky failure above.
- Frontend (vitest): **154 passed**. Deps: **42 passed**. Tooling: **115 passed**.
- `npx vite build`: built; only the old chunk-size warning.
- e2e, the S043 tests alone (`E2E_LANES=1`, desktop-chromium, `-g S043`): **9 passed**.
- e2e, **full suite** (no arguments: all specs, three projects, lanes), because the step
  changes the shared `FormModal.vue` and adds `e2e/support/properties.js`: **354 passed, 6 skipped, 0 failed** (360 tests = 120 per project on desktop-chromium, phone-chromium and phone-webkit; 6 lanes, 623 s). The 27 S043 tests (9 per project) all passed. The known flaky `masters.spec.js:62` on Pixel 7 did not fail. The 6 skipped are the existing marked ones.

### Files touched (port)

Backend (13): `app.py` (registers `properties_bp`), `equipment.py` (`properties` on the
detail; LOCK ORDER bullet), `local_db.py` (v31), `properties.py` (new; the no-model branch,
the S038 LOCK ORDER line), `properties_core.py` (new; CR1-05), `tests/conftest.py` (`_TABLES`,
two `_SEEDED_TABLES` entries, the shared `db_down`), `tests/test_access_control_api.py` and
`tests/test_auth.py` (their `db_down` removed), `tests/test_health.py` (comment),
`tests/test_equipment_api.py` (`TestProperties`, with the no-model case),
`tests/test_migration_v31.py` (new), `tests/test_properties_api.py` (new),
`tests/test_properties_core.py` (new; the CR1-05 and no-model cases).

Frontend (16): `components/FormModal.vue` (`closeOnly`), `components/PropertyInput.vue` (new),
`stores/masters.js`, `utils/propertyFormat.js` (new), `views/EquipmentDetailView.vue` (the
card; the no-model case), `views/MastersView.vue`, `views/masters/AddPropertiesModal.vue`
(new; CR1-01), `ClassPropertiesView.vue` (new), `EquipmentClassesPanel.vue` (the button for
every reader), `ModelPropertiesModal.vue` (new), `ModelsPanel.vue`, `PropertiesPanel.vue`
(new; CR1-02, CR1-03), `tests/propertyFormat.test.js` (new), `e2e/masters.spec.js`,
`e2e/equipment.spec.js`, `e2e/support/properties.js` (new; `noModelPart`).

Docs (7): `docs/schema.md`, `docs/schema.html`, `docs/Plan.MD`,
`docs/Maintenance-Philosophy.md`, `.claude/CLAUDE.md`, the brief's Status line, this report.

## Manual checks

The brief has no real-device checks (§ 8.5), so `device-checks.md` gains no row.

- [auto] **important** An engineer adds a choice property with two options, adds it to a class through *Add property…* (two ticked at once, both rows appear), sets it on a model, and the equipment page shows the value — `frontend/e2e/masters.spec.js`::`S043: engineer adds a choice property, adds two properties to a class at once and sets one on a model; the equipment page shows it`
- [auto] **Remove** on the class table takes the row away, and the picker lists the property again — `frontend/e2e/masters.spec.js`::`S043: Remove on a class's table takes the row away, and the picker lists the property again`
- [auto] **important** A number value with its unit shows as "62.5 kVA" on the card — `frontend/e2e/equipment.spec.js`::`S043: a number value with its unit shows as 62.5 kVA on the card`
- [auto] A refused number ("abc") shows "Enter a number" under its input — `frontend/e2e/masters.spec.js`::`S043: a refused number shows Enter a number under its input`
- [auto] An operator sees the *Properties* section read-only, no *Properties* button on model rows, and the class's table without *Add property…* and *Remove* (U8, BS1-04) — `frontend/e2e/masters.spec.js`::`S043: an operator sees the Properties section and a class's properties read-only, and no Properties button on models`
- [auto] A component-unit with **No model** whose class has properties shows the card with "—", no "Values from model" line and no *Edit model values* (U8, BS1-01) — `frontend/e2e/equipment.spec.js`::`S043: a component-unit with No model shows its class's properties with —, no model line and no Edit model values`
- [auto] **Edit model values** on the card opens the model dialog; after a save the card shows the new value — `frontend/e2e/equipment.spec.js`::`S043: Edit model values on the card opens the model dialog; after a save the card shows the new value`
- [auto] The property dialog, the picker and the model dialog (on a model whose class has properties) fit a phone — `expectDialogFits` in `frontend/e2e/masters.spec.js`::`S043: engineer adds a choice property, …` (all three dialogs), `S043: a refused number …` and `frontend/e2e/equipment.spec.js`::`S043: Edit model values …`; passed on all three projects, phone-webkit included
- Extra (not brief checks): the card is hidden when the class has no property — `equipment.spec.js`::`S043: the card is hidden when the class has no property`; CR1-02 — `masters.spec.js`::`S043: an option refused on Save leaves the list showing the property's saved name`

## Docs updated

- `docs/schema.md`: the four v31 tables in *Built tables*; the Mermaid overview (four tables,
  six links); the header note names migration v31.
- `docs/schema.html`: the Overview and Equipment tabs (the four tables and their links to
  `equipment_classes` and `equipment_models`), the Equipment tab's note, and the meta line
  (migration v31, 36 tables, 51 links). By hand from the migration text.
- `docs/Plan.MD`: § 1 *Not in v1* loses "Per-class custom fields"; § 4.1 *Equipment class*
  says a class carries properties (S043), overridden on an item in S044.
- `docs/Maintenance-Philosophy.md`: the glossary row *Property* (S043, S044).
- `.claude/CLAUDE.md` § SMTW-Review: the spec map has S043 for `masters` and `equipment`.
- `docs/steps/README.md`: not edited (the orchestrator's).

---

## Branch report (S035, 24-10-2026, history)

### S035 — Implementation report

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

### Manual checks (branch, as S035)

The brief has no real-device checks (§ 8.5), so no rows were added to `device-checks.md`.

- [auto] **important** An engineer adds a choice property with two options, adds it to a class through *Add property…* (two ticked at once, both rows appear), sets it on a model, and the equipment page shows the value — `frontend/e2e/masters.spec.js`::`S035: engineer adds a choice property, adds two properties to a class at once and sets one on a model; the equipment page shows it`
- [auto] **Remove** on the class table takes the row away, and the picker lists the property again — `frontend/e2e/masters.spec.js`::`S035: Remove on a class's table takes the row away, and the picker lists the property again`
- [auto] **important** A number value with its unit shows as "62.5 kVA" on the card — `frontend/e2e/equipment.spec.js`::`S035: a number value with its unit shows as 62.5 kVA on the card`
- [auto] A refused number ("abc") shows "Enter a number" under its input — `frontend/e2e/masters.spec.js`::`S035: a refused number shows Enter a number under its input`
- [auto] An operator sees the *Properties* section read-only (no *Add property*, no *Properties* buttons on classes and models) — `frontend/e2e/masters.spec.js`::`S035: an operator sees the Properties section read-only, and no Properties buttons on classes and models`
- [auto] **Edit model values** on the card opens the model dialog; after a save the card shows the new value — `frontend/e2e/equipment.spec.js`::`S035: Edit model values on the card opens the model dialog; after a save the card shows the new value`
- [auto] The property dialog, the picker and the model dialog (on a model whose class has properties) fit a phone — `expectDialogFits` in `frontend/e2e/masters.spec.js`::`S035: engineer adds a choice property, …` (all three dialogs) and in `S035: a refused number …` and `frontend/e2e/equipment.spec.js`::`S035: Edit model values …`; passed on phone-chromium and desktop-chromium, not on phone-webkit (not available here)
- Extra (not a brief check): the card is hidden when the class has no property — `frontend/e2e/equipment.spec.js`::`S035: the card is hidden when the class has no property`

### Questions for the user (branch; answered by U8, BS1-04)

1. **Who sees a class's properties table?** As built, the *Properties* buttons on Equip Class
   and Models show only to `equipment:edit` (§ 8.4); others see properties only on the
   equipment card. Options: (a) keep it so — **recommended**, it matches § 8.4; (b) show the
   class button to everyone with the read-only table of § 7.2 (then the § 8.4 check changes
   for classes).

## Fix rounds

### Round 2

Review: `4-code-review-r2.md`. No `blocker` or `major` finding was open. All three findings are answered.

- **CR2-01 (minor): Fixed.** This is CR1-04's red result. No code changed.
  - I removed the full stop from the two seed texts in v31 (`backend/local_db.py`: *Degree of protection*, "...for example IP55"; *Mounting*, "...for example B3").
  - `YANTRA_TEST_RUN=s043c2red tooling/run-backend-tests.bat tests/test_migration_v31.py -k fresh_database -n 0` **fails without the fix**: `test_migration_v31.py:75`, `AssertionError ... 'The IP code on the nameplate, for example IP55' != 'The IP code on the nameplate, for example IP55.'`.
  - I restored `local_db.py` exactly (byte-compared with the copy taken before). The same run **passes with it** (1 passed).
  - Note: the exact-text asserts at lines 75 and 76 catch these two texts before the `endswith(".")` assert at line 78 runs. That last assert guards the other descriptions and any future seed text. I did not make it fail on its own, because the reviewer said not to change the code.
- **CR2-02 (nit): Fixed.** `backend/tests/test_equipment_api.py`: two blank lines now stand before `class TestProperties:`.
- **CR2-03 (nit): Fixed.** `frontend/e2e/masters.spec.js`, test `S043: an option refused on Save leaves the list showing the property's saved name`: `toContainText` became `expectFieldMessage(dialog, "An option with this label exists")`. The test passes on all three projects.
- **Tests (final run).** `YANTRA_TEST_RUN=s043c2 tooling/run-tests.bat`: backend 2837 passed, frontend 154 passed, deps 42 passed, tooling 115 passed. e2e `masters.spec.js` and `screens.spec.js`, three projects, 6 lanes: 90 passed, 0 failed (260 s).
- **Docs updated:** none, because the round changes two test files and a report only.
- **Files touched:** 3 (`test_equipment_api.py`, `masters.spec.js`, this report).
