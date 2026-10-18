```
Step: S012 — Equipment models
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 17-10-2026
```

# S012 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There is one `minor` (DRY) and two `nit`s.

Reviewed: the working-tree diff against HEAD `c486a4a`, read with `git diff -w --ignore-cr-at-eol`, plus
the new untracked files. I set aside the unrelated changes the orchestrator named: the criticality
badge colours in `equipmentLabels.js` (only `case "model"` is S012), `docs/Plan.MD`,
`docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md` and `docs/review/`. I read `documents.py`,
`ModelsPanel.vue`, `DocumentsCards.vue` and the new tests in full, and the other touched files
around their hunks.

## Test result (run by the reviewer)

- `tooling/run-tests.bat`: **backend 986 passed** (72 s), **frontend 51 passed** (9 files). Exit 0.
- `npx vite build` in `frontend/`: built in about 2 s, with no errors or warnings.

This matches the impl report.

## Findings

### CR1-01 — minor — `backend/masters.py:441` (`_lock_active_parent`) duplicates `_lock_class_for_type` (`masters.py:322`)

- **Problem.** `_lock_active_parent(cur, "equipment_classes", id, field, "class")` does the same
  thing as `_lock_class_for_type(cur, id, field)`:
  - the same `SELECT id, active … FOR UPDATE`;
  - the same "Unknown class" 400;
  - the same "The class is inactive" 409, on the same `field`.

  S012 added the general helper but kept the old one, so the module now has two copies of one
  rule. CLAUDE-COMMON says: "DRY: never copy-paste code blocks".
- **Failure scenario.** Someone later changes the class-lock rule, for example the message, or
  the lock order of § 5.5. They change one copy and not the other, so model create and type
  create start to answer differently for the same inactive class.
- **Fix.** Delete `_lock_class_for_type` and call
  `_lock_active_parent(cur, "equipment_classes", class_id, field, "class")` from
  `create_equipment_type` and `update_equipment_type`. Or keep the name as a one-line wrapper
  around it. No test changes: the messages and fields are the same.

### CR1-02 — nit — `backend/documents.py:467`: the removed-list `q` on a model row does not match the full label

- **Problem.** The equipment list's search uses `CONCAT(mf.name, ' ', m.designation) LIKE …`
  (Decision 2), so "Atlas Copco GA37" finds the machine. The model branch of the removed list
  matches `m.designation` and `mf.name` separately. The row reads "Model *Atlas Copco GA37*",
  but typing that same text finds nothing. Only "GA37" or "Atlas" finds it.
- **Failure scenario.** A manager copies the label from the equipment page into Settings ›
  Removed documents. The list comes back empty.
- **Fix.** Use the same expression as the equipment list:
  `(CONCAT(mf.name, ' ', m.designation) LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s)`,
  and add a line in `test_q_matches_designation_manufacturer_title_and_file_name`. The brief only
  asks for the designation and the manufacturer name, so this is optional.

### CR1-03 — nit — `frontend/src/views/masters/ManufacturersPanel.vue:22` (`reload`): a rename leaves the cached models' labels stale

- **Problem.** A manufacturer rename refreshes only `manufacturers`. The shared `equipmentModels`
  cache still holds labels built from the old name. The equipment form's picker reads that cache
  (`ensureModels()` without `refresh`), so it shows "Atlas copco GA37" until the page is
  reloaded or the Models panel is opened, because `ModelsPanel` refreshes the cache when it
  mounts. The backend is right throughout: node rows and events build the label live.
- **Failure scenario.** An engineer fixes a typo in a maker's name, then goes to Equipment ›
  Add equipment in the same tab. The picker still shows the typo.
- **Fix.** In `ManufacturersPanel.reload`, also refresh models:
  `await Promise.all([ensureManufacturers({ refresh: true }), ensureModels({ refresh: true })])`.
  Or accept it: the masters store's header already says a picker list a few minutes old is
  harmless.

## Earlier rounds

None. This is round 1.

## Checked and found consistent

**Migration v9** (`local_db.py`)
- The SQL matches § 4 exactly, in the order given, and each statement is safe to re-run:
  - both tables, with the composite `(type_id, class_id)` FK and `uq_equipment_models_id_class`;
  - `equipment.model_id INT NOT NULL`, with its index added before the composite FK;
  - `make` and `model` dropped;
  - `MODIFY equipment_id INT NULL` (no fallback needed on 11.4), then `model_id`, its index, its
    FK and the one-owner CHECK;
  - the events ENUM with the seven old values in their order and `model` appended.
- The append-only rule holds: no earlier migration was edited.
- The comment states the half-applied failure mode on a table with equipment rows (BR3-01).
- `test_migration_v9.py` covers what § 8 asks for:
  - the re-run twice;
  - make and model gone;
  - a NULL `model_id` refused (1048);
  - the CHECK refusing a document with two owners and one with none (4025).

**Validation** (`masters_core`, `equipment_core`)
- Manufacturer and model validators:
  - trimmed, with runs of spaces collapsed (`str.split` also collapses NBSP and tabs);
  - limits of 100 and 80 characters, tested at 100/101 and 80/81;
  - `model_label` is the one place a label is built.
- `derive_from_model` is pure and returns a message; the shell maps it to 409 (BR3-07.3).
  - A newly picked inactive model is refused; an unchanged inactive one is kept.
  - The type is never checked for active.
  - A model without a type gives `type_id = None`, which is always written (BR3-07.4).
- `validate_equipment`:
  - refuses `make`, `model`, `class_id` and `type_id` on key presence, so also when sent as
    null or unchanged, with the § 5.4 messages;
  - gives `model_id` its own "Pick a model" when missing or null, on create and on update.
- `_TRACKED` has `model_label` → "model", ahead of class and type. The longest event value is
  100 + 1 + 80 = 181 characters, which fits the events' VARCHAR(200).

**Equipment shell** (`equipment.py`)
- The lock order is node (1) → parent (2) → unit (3) → model (4) → class (5) → serial (6).
- The model is locked only when newly picked: an unchanged `model_id` is dropped first.
- `_pick_model` writes both `class_id` and `type_id` from the locked model row.
- The type lock and `_check_type_on_update` are gone, as the brief says.
- `NODE_JOINS` uses inner joins to `equipment_models` and `manufacturers` (BR3-04). The
  invisible-model race gives the existing `_reread` 409, and it is tested.
- `_written_state` patches `model_designation` from the lock. The stale-re-read test asserts it.
- `LOCK_EQUIPMENT` carries `model_id`.
- Search uses one `CONCAT` expression, also in the count query: both use `_NODE_FROM`.
- A reclassification by model keeps the code and writes the model, class and type events.
- The detail and list views no longer carry make or model. No reference to the old columns is
  left in app code or the seed.

**Masters shell** (`masters.py`)
- The routes and permissions match § 6: reads under `masters:read`, writes under
  `equipment:edit` through `require_perm` (the global union).
- Lock orders follow § 5.5:
  - **model create:** manufacturer → class → type → insert;
  - **reactivate:** a plain read of the fixed ids, then manufacturer → model → class;
  - **designation edit or deactivate:** the model row alone;
  - **manufacturer and class deactivation:** row lock, then a plain count.
- The plain counts come after the lock in their transactions. So they are the transaction's
  first consistent read, and they see a model created or reactivated by a writer that held the
  lock first. The three-way race (class deactivate vs model create/reactivate vs equipment pick)
  has no cycle and no stale decision.
- Manufacturer, class and type are fixed after create (400); the designation stays editable.
- `UNIQUE_KEY_ERRORS` has both new keys, with the § 5.1/§ 5.2 texts.
- The class-deactivation rule (§ 5.2) is in place and tested both ways.

**Cross-module locks**
- `equipment.py` never locks manufacturers or types. `masters.py` never locks equipment.
- `documents.py` takes exactly one owner lock (the node row or the model row), then only
  `equipment_documents`.
- The FK checks on insert take shared locks on rows the same transaction already holds (model,
  class), or on the type row after the class lock, the same class-first order as masters.
- No cycle across the three modules. The docstrings of all four modules state the order and the
  owners.

**Documents** (`documents.py`, `file_store.py`, `app.py`)
- Two owners, as S009's `OWNERS` design, with stacked route decorators. The owner comes only
  from the route `defaults`, never from the client.
- The blueprint is mounted at `/api`. The node URLs are unchanged, and
  `/api/equipment/removed-documents` keeps its URL.
- **S011 keyed checks kept** on every node path, the same as HEAD:
  - list and serve: plain `load_node_for_user`;
  - upload: early keyed read, then a keyed lock with the scrapped check;
  - title and remove: keyed lock with the scrapped check;
  - restore: keyed lock with the scrapped check (S008);
  - purge: keyed lock without the scrapped check (S008 § 5.3).
- Model owners have no site, by design (§ 2, A.8.3), and are gated by the routes'
  `require_perm`. An outsider at another site gets 404 on the node and 200 on its model's
  documents, as tested.
- **Files under DATA_DIR:**
  - model files live in `DATA_DIR/equipment-models/<id>/`;
  - the path is built from the owner map, the integer id and the stored name from the DB;
  - files are served only through the checked routes, with `nosniff` and private caching;
  - a doc id fetched under the wrong owner is 404, tested in all three directions.
- **The `inherited` group:**
  - one model group, left out when the model has no live documents;
  - it follows a model change at once;
  - a part shows its own model's documents, not its parent's.
- **The removed list:**
  - a `UNION ALL` of the S008 node branch, whose unit scope is unchanged and which alone is left
    out for an empty unit set, and a model branch with no unit condition;
  - `code` is null on a model row, and `name` is its label;
  - ordering and paging run over the union, and ids are unique across owners because both
    branches come from one table.
- Restore and purge are generalised by owner. Purge deletes the row first, then the files.
- Node rows gaining `owner` and `path` is reported as Decision 7.

**Frontend**
- The document components moved to `components/documents/` and take a `basePath`:
  - inherited items are read-only (`own` is checked in the cards and in `PhotoViewer`);
  - "Managed in Masters › Models" follows the global `userPermissions`, and the node's own
    `canEdit` follows `node.permissions` (S011);
  - the upload line reads "Visible at every site" for a model.
- The equipment form:
  - an optional class filter (not sent) and a required Model picker;
  - the current inactive model stays listed and marked;
  - the picked model stays listed under another class filter;
  - class and type shown read-only below the picker;
  - the no-model hint;
  - models loaded with `include_inactive=1` through the store.
- The equipment page shows Manufacturer and Model, and reloads the documents after an edit.
- The list has a Model column, and the search placeholder is updated.
- `RemovedDocuments.vue` builds the action URLs from `path` and shows model rows.
- `describeEvent` has `case "model"`, with a test.
- `modelPicker.js` is pure, with vitest tests covering § 8 Frontend.
- `ModelsPanel` refreshes the shared cache, so a new model reaches the equipment form at once.

**Seed**
- The manufacturers and models of § 3 Tooling are seeded: a Generic model per class without a
  maker, the GBX gearbox and `SMTW-HYP-01`.
- All equipment, and the component unit, are created by `model_id`.

**Tests against § 8**
- **Pure:** every bullet is covered.
- **API:**
  - manufacturers, models, class deactivation and the equipment model rules, including the
    shell-bypassed inactive class (BR3-02) and every refused field;
  - the two database 1452 cases;
  - documents, inherited group, access and failures (insert failure, storage 503) on the model
    owner;
  - removed list, restore and purge of model rows; refusals for engineer and operator; `q`;
  - RBAC: an operator reads but cannot write; an engineer at one site writes models and model
    documents; an engineer cannot purge.
- The BR3-03 cases are fixed as the brief names them, and `TestRow.test_row_fields` has the
  four new fields.
- The dropped and rewritten cases are each listed with a reason in the report (§ 5).

**Rules from CLAUDE-COMMON**
- Pure core and thin shell. Only CR1-01 breaks DRY.
- No swallowed exceptions: the upload failure path removes the files and re-raises, and
  `_remove_stored_files` logs every outcome.
- No deprecated APIs.
- No SQL built from client input: the f-string parts are code constants.
- The actor always comes from `actor()`.
- A DB outage gives 503 through `get_db()`.
- Comments say why.

**Scope**
- Everything in § 1 is built, and nothing beyond it.
- Each choice the brief left open is listed in the report's "Decisions taken" (1–12). None
  departs from the brief: Decision 6, always locking the class of a newly picked model, is what
  § 5.5 says.
- `check_type_class` staying in `equipment_core` and being imported by `masters.py` is
  reported (Decision 1). It is acceptable.

**Manual checks**
- The report's `## Manual checks` has all four important checks of § 8 as unticked boxes, and
  the phone check as a plain note.

**Track**
- Full. No track issue.

## Still for the user's manual browser check

From the impl report, not yet ticked:
- [ ] As engineer: add "Atlas Copco" / "GA37" (CMP, Screw compressor), create a compressor by
  picking it. Class and type should show from the model, and the page should show Manufacturer
  and Model.
- [ ] Add "SMTW (in-house)" / `SMTW-HYP-01` (press) and a Generic model; create a press and a
  component with them.
- [ ] Upload a manual on the model in Masters › Models. It should appear "From model", read-only,
  on every compressor of that model. Remove it in Masters, then restore it from Settings ›
  Removed documents.
- [ ] **Production, at the release:** check the MariaDB version is ≥ 10.5. Then confirm there is
  no equipment: as admin or IT admin, with Show scrapped ticked and Level = All levels, the total
  must be 0.

Also (plain): pick a model on a phone (long labels).

There is one naming question for the user, not a code finding (Decision 12). The brief's rule
"Generic models are named by what they are" gives labels like "Generic Generic gearbox". If that
reads badly, the fix is the designation text, for example "Gearbox". The seed and any real
records change; the code does not.
