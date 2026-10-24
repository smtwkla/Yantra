Step: S035 — Equipment properties: master, classes and models
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026

# S035 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The build matches the brief, and every suite is green. There are 3 `minor` findings and 2 nits. All three minors are friction in the Masters dialogs.

Reviewed: the working-tree diff against HEAD `0f3afdb` and the untracked files. I read every new file in full. I ignored the Status-line and index-row edits in `1-brief.md` and `docs/steps/README.md` (they are the orchestrator's). The open user question (§ 7.2 or § 8.4: who sees a class's properties table) is not a finding here. I reviewed the code as built, which follows § 8.4.

## Test runs (this review, `YANTRA_TEST_RUN=s035cr1`)

| Suite | Result |
|---|---|
| Backend (pytest, 8 workers) | **2446 passed** (25.7 s) |
| Frontend (vitest) | **127 passed** (15 files) |
| `npx vite build` | built; only the old chunk-size warning |
| Deps tests | **42 passed** |
| Tooling tests | **106 passed** |
| e2e, **full** suite, phone-chromium and desktop-chromium, 6 lanes | **189 passed, 3 skipped, 0 failed** (3.0 min) |

- **Why the full e2e suite:** the step changes shared frontend code (`FormModal.vue`) and adds a file under `e2e/support/` (CLAUDE.md § Browser tests). The run covers the targeted specs (`masters.spec.js`, `equipment.spec.js`) and `screens.spec.js`. All 14 S035 tests passed (7 per project).
- **WebKit (phone-webkit) was not run.** This sandbox has no WebKit build. The user's full run before the release covers it.
- **The 3 skipped tests** are the existing ones, marked before this step.

## Findings

### CR1-01 (minor) — Enter in the picker's search box adds the ticked properties

- **Where:** `frontend/src/views/masters/AddPropertiesModal.vue:176-183`.
- **Problem:** the search box sits inside FormModal's `<form>`. When a box is ticked, the submit button is enabled, so Enter in the search box submits the form (HTML implicit submission). A phone keyboard's *Search* or *Go* key does the same.
- **Failure scenario:**
  1. An engineer ticks *Power – design*.
  2. The engineer types "speed" in the search box to find the next property, and taps the keyboard's Search key.
  3. The dialog sends `POST …/properties` with *Power – design* only and closes before *Speed* is ticked.
- **Fix:** stop Enter on the search input, for example `@keydown.enter.prevent`. The search filters as the user types, so Enter has no job there.

### CR1-02 (minor) — A refused option save leaves half an edit saved and the list stale

- **Where:** `frontend/src/views/masters/PropertiesPanel.vue:99-119` (`saveEdit`).
- **Problem 1:** the edit first sends `PUT /properties/<id>`, then one request per option. If an option request is refused, the property's own changes are already saved. But `afterSave` (`resetMasters()` and `reload()`) does not run. If the user then presses *Cancel* and *Discard*, the Masters table still shows the old name, description or data type.
- **Problem 2:** the option loop does not check the data type the form now has. New option rows are still posted after the user changes the type away from *Choice*.
- **Failure scenarios:**
  1. Rename "Drain" to "Drain type" and add an option "internal" when "Internal" exists. The rename is saved, and the option gets 409 "An option with this label exists". After *Cancel* and *Discard*, the list still reads "Drain" until the panel reloads.
  2. A choice property has no options yet. Click *Add option*, then change the data type to *Number* and enter a unit. *Save* stores the type change, then the POST of the leftover row gets 400 "Only a choice has options". The line shows under the hidden options section, and the dialog stays open and dirty.
- **Fix:**
  1. Post or put options only when `form.data_type === "choice"`.
  2. After a refusal that comes after the property PUT succeeded, refresh the list (`resetMasters()` and `reload()`), or refresh it when the dialog closes.
- The brief has separate option routes, so one atomic request is not expected. The list must not lie after a partial save.

### CR1-03 (minor) — A new option row cannot be taken away again

- **Where:** `frontend/src/views/masters/PropertiesPanel.vue:205-218`.
- **Problem:** *Add option* appends a row, and nothing removes an unsaved row. A blank row is refused with "Enter a label", in the create and in the edit dialog.
- **Failure scenario:** an engineer clicks *Add option* once too often while making "Drain" with "Internal" and "External". *Save* answers "Enter a label". The only ways out are to type a label the engineer does not want, or to cancel and lose the whole dialog.
- **Fix:** take one of these two:
  1. A remove (✕) button on rows with `id === null`.
  2. Drop blank new rows in `toBody` and `saveEdit` before sending.
- Saved options keep their *Active* switch only, as the brief says (no delete).

## Nits

- **CR1-04** (nit) `backend/local_db.py:825,827`: the seed descriptions of *Degree of protection* and *Mounting* end without a full stop. Every other seed description ends with one. Add the full stop: v26 is not applied anywhere yet.
- **CR1-05** (nit) `backend/properties_core.py:362-365`: a property that is unknown, inactive or not on the class is refused in the body's key order, before the by-name check of § 5.3. The screens never send such a key, so this is acceptable. Add one line about it under *Decisions taken* in the impl report.

## Departures declared by the coder

| # | Decision | Judgement |
|---|---|---|
| 1 | `FormModal` `closeOnly` prop | **Sound and minimal.** The default is `false`. The new footer branch is `v-else-if` after `confirming`. `onSubmit` only gains `&& !props.closeOnly`. The 27 other callers pass no `closeOnly`, so their footer and submit work as before; the full e2e run confirms it. The rejected option (a hand-written modal) would copy the S007 guard and the S026 reveal. |
| 2 | *Properties* buttons only for `equipment:edit` | It follows § 8.4. The conflict with § 7.2 is with the user (not a finding). `ClassPropertiesView` also hides *Add property…* and *Remove* without the key, so option (b) would need only the button moved out of `v-if="canEdit"`. |
| 3 | Column headed *Active* | **Sound.** It follows the user's decision of 23-10-2026 (the README's queued tidy-up row). The other panels keep *Status* until that tidy-up. |
| 4 | Options in the order they were made | **Sound.** The brief does not say. Order by id keeps the seed's listed order. |
| 5 | One `INSERT IGNORE … SELECT` per seed option | **Sound.** This is the brief's statement form (§ 4.6). The f-string takes only code constants (no quotes in any label), so no client text reaches the SQL. |
| 6 | Duplicate labels refused on `options` | **Sound.** Without it, the UNIQUE index answers on `label`, a field the create dialog does not show. The message would then land in the top bar instead of under the options. |
| 7 | Extra API-only messages | **Sound.** "Active must be true or false" matches `masters_core`'s form, and the screens never send these bodies. |
| 8 | Extra screen texts | **Scope B is met.** Each text is one short line. The tooltip "Tick at least one property" starts with a verb and names what to do. |
| 9 | *Back* link | It follows § 7.2. |
| 10 | `e2e/support/properties.js` | **Sound.** Both specs share one setup. It adds a file and changes no existing support file. |
| 11 | `POST …/options` answers the option | **Sound.** The brief gives only 201. The dialog needs the new id (the second-save guard). |

## Checked and found consistent

- **Migration v26** (`local_db.py`):
  - the four tables match § 4.1 column for column;
  - `chk_property_unit` and `chk_model_property_one_value` are there;
  - the composite FK `(option_id, property_id)` → `uq_property_options_id_property` is there;
  - InnoDB, utf8mb4, `IF NOT EXISTS`;
  - the 22 seed rows have the types, units and descriptions of § 4.6, and no type rows;
  - the U7 examples are absent, and no class link is made;
  - it touches no existing row, so no `_PRECONDITIONS` entry is needed;
  - `test_migration_v26.py` covers a fresh database, an upgrade from v25 that keeps every row and the old columns, the CHECKs and the FK refusing at the database, and a re-run that keeps an edited row (the renamed name comes back as a 23rd row, as § 9.4 states).
- **Pure core** (`properties_core.py`, no DB, Flask or clock):
  - the § 5.1 field rules and messages;
  - the combined record (`property_changes`: a unit on a non-number is a 400; a type leaving *number* clears the unit in the same write; type and unit fixed with 409);
  - the number form `-?digits(.digits)?`, then decimals counted on the value;
  - `Decimal(str(...))`, never a float;
  - bools refused, and the limit of ±10¹²;
  - `number_text` uses `format(normalize(), "f")`, so 100 shows as "100", not "1E+2";
  - an inactive option is accepted only as the stored value;
  - `property_view` lists by name, with `source` "model" or `None`.
- **LOCK ORDER** (`properties.py` docstring against § 5.6):
  - every write takes (1) class or model, then (2) properties by id ascending `FOR UPDATE`, then (3) options;
  - the "options or values exist" checks are `LOCK IN SHARE MODE`;
  - an option edit reads its property plainly (it never changes), then locks (2) → (3);
  - a model save locks the model, the properties, then the links `LOCK IN SHARE MODE` and the options;
  - every pair of writers meets first on the property row, so they wait in turn and cannot deadlock;
  - no route here holds a property lock and then takes a model, class or equipment row;
  - `equipment.py`'s LOCK ORDER note records the module.
- **UNIQUE_KEY_ERRORS:** `uq_property_definitions_name` → `name` and `uq_property_options_label` → `label`, both 409. They are registered at import, and `app.py` imports the module. The tests cover a duplicate name by case and a duplicate label.
- **Permissions (§ 6):**
  - the three GETs use `masters:read`; the seven writes use `equipment:edit`;
  - the actor always comes from `actor()`, never from the client;
  - every query uses placeholders, and table and column names are constants;
  - the tests cover an operator (200 on reads, 403 on all seven writes) and an engineer at one site (the union);
  - `test_role_matrix` is unchanged (no new key).
- **Class-link routes (U6):**
  - the POST reads the ids as a set and skips ids already on the class;
  - an inactive or unknown property, or a choice without an active option, gets "Choose active properties";
  - `[]`, a non-list, bools or strings get "Choose at least one property";
  - an inactive class is allowed, and an unknown class is 404;
  - the DELETE answers 404 when the link is missing, and the values stay;
  - both answer with the GET's shape.
- **The single-field error:** `values` not an object, or `{}` (200, no change); bad keys answer on `values.<key>`; the first refusal by property name answers and nothing is saved (tested with three values). `ModelPropertiesModal` keys its form `"values.<id>"`, so `fieldError` shows the message under the input. The e2e test checks the message and the focus (S026).
- **conftest:**
  - `_TABLES` has `model_property_values` before `equipment_models` and `class_properties` before `equipment_classes`;
  - `_SEED_CREATORS` gives one creator per table, and `SEED_CREATOR` is kept for `test_migration_v11.py`;
  - the moved `db_down` has the same two `monkeypatch` lines as the removed copies;
  - `test_access_control_api.py` still uses `db_helpers` (line 137), so its import stays;
  - `test_auth.py` dropped the two imports only its fixture used;
  - the comment in `test_health.py` is updated.
- **The database down:** a read and a write answer 503 (`TestDatabaseDown`). Every route goes through `get_db()`.
- **Equipment detail:** `_detail` adds `properties` through `equipment_properties` with a plain read. Every equipment row has a model (inner JOIN), so `model_id` is never null. Unlinked and inactive properties are absent, and an empty class gives `[]`. Both cases are tested.
- **Screens (§ 7):**
  - **Masters › Properties:** the type summary, the two "fixed" rules with their help lines, the type help line, *Show inactive*, and the deactivate toggle.
  - **The class table:** it replaces the class table in the panel, with the heading, help line, grey note, "(inactive)", *Remove* without a confirm (§ 7.2), and the empty state.
  - **The picker:**
    - it uses `useFormModal` + `send`, with its form keyed `property_ids`;
    - a choice without options is disabled with "(no options yet)";
    - *Add properties* is disabled until a box is ticked;
    - when every property is on the class, the dialog shows its message and only *Close*.
  - **The model dialog:**
    - it fetches first, then `openEdit`, so an untouched *Cancel* closes without the guard;
    - a failed fetch shows its message in the panel or card and the dialog stays closed;
    - a class with no properties shows its message and only *Close*.
  - **The card:** beside *Details*, it shows "—" for no value and the "Values from model" line. *Edit model values* follows `canEditModels` on every lifecycle, and `saved` calls `load()`.
  - **Phone fit:** all three dialogs use `modal-dialog-scrollable`, so the footer stays in view and the picker's list scrolls inside the body. `expectDialogFits` passed on phone-chromium.
- **UI text (scope B):** the brief's strings are used verbatim. Error lines are short and plain, and buttons start with a verb.
- **Tests against § 8:**
  - every listed case of § 8.1–8.3 has a test;
  - each `[auto]` row of the impl report's `## Manual checks` names a test that passed in this run;
  - the tests assert what the user sees (the "62.5 kVA" text, the row counts, the message under the input, the focus);
  - § 8.5 has no real-device check, so `device-checks.md` correctly gains no row.
- **Scope:** everything in § 1 is built. S036 is not started, and nothing outside the brief was added beyond the declared decisions.

## Manual browser checks for the user

- None from the brief (§ 8.5: none on a real device).
- **Before the release:** run the full e2e suite once on **WebKit** (phone-webkit). This sandbox could not run it, so the S035 dialogs' phone fit on iPhone WebKit is unchecked.
