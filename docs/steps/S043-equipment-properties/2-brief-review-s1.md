Step: S043 — Equipment properties: master, classes and models
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 24-10-2026

Reviewed against: ff9ddb3 + uncommitted S037, S038

# S043 — Staleness review, round s1

**Verdict: one `major` finding is open (BS1-01).** The brief and the branch code assume every
equipment item has a model. Since S033 (v28, after the branch's base) a component-unit may have
none, and the Properties card and its *Edit model values* button have no defined behaviour for
it. Everything else that moved is wording, file names and line numbers: 3 `minor`, 8 nits.

**What I compared.** The brief (as renumbered S043 / v31), the branch's diff `06e16e4..ffb144c`
(the code the coder ports), its impl report and code review r1, against the working tree now:
`git diff 06e16e4` on every file of § 3 plus `api_common.py`, `config_rbac.py`, `test_auth.py`,
`test_access_control_api.py`, `test_health.py`, the `test_migration_*` tests, `seed_e2e.py`,
`e2e/support/`, `MetersCard.vue`, `meters.py`, `schema.md`, `.claude/CLAUDE.md`. The baseline
`06e16e4` is the branch-side S034 commit: S031 (v26), S032 (v27) and S033 (v28) are **not** in
it (`git merge-base --is-ancestor` says no), so all of main's steps since S031 count as changes
here. No facts file was given for S043 (`scratch/brief-facts-S043.md` does not exist); I
checked the names by hand.

## Findings

### BS1-01 — major — A component-unit without a model: the card and its button are undefined

- **What changed.** S033 (c9234ce, v28) made `equipment.model_id` NULL-able for component-units
  (`chk_equipment_model_level`). `equipment.py` now reads the model with `LEFT JOIN
  equipment_models` (line 139); at the baseline it was an inner `JOIN` (line 123 of
  `06e16e4:backend/equipment.py`), which is why code review r1 could say "every equipment row
  has a model, so `model_id` is never null". The detail now sends `model_id: null`,
  `model_label: null`, and the Details card shows "No model" (`EquipmentDetailView.vue` 231–235).
- **What in the brief is now wrong.** § 6.3 and § 7.4 describe the card only for an item with a
  model: "the model's value", "Values from model <model label>.", *Edit model values* "for
  `node.model_id`, titled with `node.model_label`". § 5.5 `property_view` and § 8.2 have no case
  for a node without a model. As the branch code stands, on a model-less component-unit whose
  class has properties: `_detail` calls `equipment_properties(cur, class_id, None)`,
  `_model_values` runs `WHERE model_id = NULL` (no rows), every row shows "—", the grey line
  reads "Values from model null.", and *Edit model values* (shown to every `equipment:edit`
  holder) calls `GET /api/masters/equipment-models/null/properties`, which Flask's `int`
  converter turns into a 404 shown in the card as "Not found".
- **Why it matters.** A real screen state with wrong text and a button that always fails. The
  user approved the card's content and button; what they do here is a design decision, not a
  wording fix. S033's own e2e test makes such a node (`S033: engineer adds a component-unit with
  No model`), so the state is reachable today.
- **Options.**
  - **(a) Recommended: show the card, no model line, no button.** On a node with `model_id`
    null the card lists the class's active properties with "—", the grey line reads "No model.
    This item's own values come later." (or is left out), and *Edit model values* is hidden.
    § 6.3: `properties` is built from the class alone; `source` stays `null`. The shell passes
    `model_id` explicitly: `values = _model_values(cur, model_id) if model_id is not None else
    {}`, as `meters.py` `_meters_of` does (line 62). S044 then fills the "—" with the item's own
    values, which is exactly the case these nodes need. Tests: § 8.2 adds "a component-unit
    without a model: every property `display: null`, `source: null`"; § 8.4 adds the card on a
    No model part (no *Edit model values*, no "Values from model").
  - **(b) Hide the card when `model_id` is null** until S044. Smaller now, but the engineer
    sees nothing of the class's properties on these parts, and S044 changes the rule again.
- Either way § 6.3, § 7.4, § 5.5 and § 8 gain the case.

### BS1-02 — minor — `_SEEDED_TABLES` is already a dict with a creator per table (S037)

- **What changed.** S037 (uncommitted, v29) made `conftest._SEEDED_TABLES` a dict
  `{table: creator}` (`"meter_types": "migration-v29"`, line 143) and `_clean_tables` already
  iterates `.items()`. `SEED_CREATOR = "migration-v11"` stays for `test_migration_v11.py`.
- **What in the brief is now wrong.** § 3.2 and § 8.2 say "`_SEEDED_TABLES` today takes one
  creator (`SEED_CREATOR`, line 146): it becomes a creator per table" and plan a **new**
  `_SEED_CREATORS`. The branch's diff renames the structure and adds `PROPERTY_SEED_CREATOR`;
  ported as is, it would conflict with S037's version or leave two structures.
- **Why it matters.** The coder would otherwise reinvent what S037 built, or lose S037's
  `meter_types` entry in the merge.
- **Fix.** § 3.2 and § 8.2: "add `"property_definitions": "migration-v31"` and
  `"property_options": "migration-v31"` to the existing `_SEEDED_TABLES` dict (S037); nothing
  is renamed". Drop `_SEED_CREATORS` and `PROPERTY_SEED_CREATOR` from the brief; the Review log
  entry for BR1-06 is history and stays. `_TABLES` now starts with `node_meters, model_meters`
  (line 138); the position rule for `model_property_values` and `class_properties` still holds.

### BS1-03 — minor — The docs pass: schema docs and the SMTW-Review mapping are missing, and § 11's edits are not on main

- **What changed.** ff9ddb3 made the docs pass a standing rule (`.claude/CLAUDE.md` § Docs to
  keep current; `docs/steps/README.md` § Folder and files): the **coder** updates the docs a
  step makes due, in the same step, and lists them in the impl report's `## Docs updated`.
  `docs/schema.md` and `docs/schema.html` must be edited by hand for every migration; a missing
  one is a gate B blocker. S038's impl report already has the section (line 144).
- **What in the brief is now wrong.**
  1. § 3.5 and § 11 list only `Plan.MD`, the glossary and the README index, "at approval, by
     the planner". `docs/schema.md` / `schema.html` (the four v31 tables) are not named; nor is
     `.claude/CLAUDE.md` § SMTW-Review, whose spec mapping now reads `masters` S016/S037/S038
     and `equipment` S003/S006/S012/S038 and should gain S043.
  2. The § 11 edits were made on the **branch** (`ffb144c`: Plan.MD lines 56 and 235, the
     glossary row), not on main: `docs/Plan.MD` line 57 still says "Per-class custom fields
     (e.g. press tonnage)" and line 237 "No class-specific custom fields in v1";
     `docs/Maintenance-Philosophy.md` § 12 has no *Property* row. The branch's text also says
     S035 / S036 where main says S043 / S044.
  3. The branch's impl report has no `## Docs updated`; the port's must.
- **Why it matters.** Gate B would block on the schema docs, and the plan would keep saying the
  feature is out of scope after it ships.
- **Fix.** § 3.5 becomes "Docs (the docs pass, by the coder)": `docs/schema.md` (four table rows
  in *Built tables*, the Mermaid overview, the "migration v31" line in the header note) and
  `docs/schema.html` (the Equipment tab: the four tables, links to `equipment_classes`,
  `equipment_models`); `docs/Plan.MD` § 1 and § 4.1 and the glossary as § 11 says, with S043 /
  S044; `.claude/CLAUDE.md` § SMTW-Review mapping. Say that the coder applies the branch's
  `Plan.MD` and glossary diff (it applies cleanly: those lines did not change on main) with the
  step IDs replaced. Alternative: the planner applies § 11 now, before coding; then § 3.5 still
  names the schema docs and the CLAUDE.md line for the coder.

### BS1-04 — minor — Who sees the *Properties* button: S038's *Meters* button on the same row follows the other rule

- **What changed.** S038 (uncommitted) added a *Meters* button to every model row in
  `ModelsPanel.vue` (line 234), shown to **every** reader; its view hides *Add meter*, *Set
  limits* and *Remove* without `equipment:edit`. *Documents* on the same row already worked so.
- **What in the brief is now wrong.** The brief says two things: § 3.3 and § 7.2 — the class's
  *Properties* button works "as `ModelsPanel.vue`'s *Documents* does", and "users without
  `equipment:edit` see the table without *Add property…* and *Remove*"; § 8.4 — "an operator
  sees … no *Properties* buttons on classes and models". The branch built § 8.4 (the button
  only inside `v-if="canEdit"`, `EquipmentClassesPanel.vue`) and its impl report asks the user
  (Q1). With S038, a class row and a model row now carry a read-for-all button (*Documents*,
  *Meters*) next to a keepers-only one (*Properties*) that opens a view with its own read-only
  state. The brief must say one thing.
- **Options.**
  - **(a) Recommended: the class button for everyone, the model button for keepers.** The
    class's table is read-only without the key (already built, § 7.2), as *Meters* and
    *Documents*; a technician can see what a class records. The model's dialog only edits
    values, and every reader sees the values on the equipment card, so its button stays
    `equipment:edit`. § 8.4's operator check becomes: "no *Properties* button on model rows;
    the class's table shows no *Add property…* and no *Remove*". The branch's e2e test changes
    one loop.
  - **(b) Keep the branch's build** (both buttons for keepers only) and strike the § 7.2
    sentence and the *Documents* comparison in § 3.3.
- A user decision, so not a nit.

## Nits

- **BS1-05** (nit) § 7.4 and § 3.3 `EquipmentDetailView.vue`: the page now has S038's
  `<MetersCard>` after the Details / Parts row (line 257) and the file is 294 lines. State the
  order: the Properties card is the second `col-lg-6` of the `row g-3` (Details, Properties,
  Parts — on a desktop Parts wraps to a second row when the class has properties), then the
  Meters card, Notes, History, Documents. `canEditModels` is at line 58, Parts at 249–254.
- **BS1-06** (nit) header: `Baseline: 437d993` is a branch commit (the branch's brief review
  r1). After this review it becomes `ff9ddb3 + uncommitted S037, S038`.
- **BS1-07** (nit) line numbers moved: `app.py` registers `masters_bp` at 186–187 (not 173),
  with `meters_bp` at 179–181; `equipment.py` `_detail()` at 282 (not 266); `masters.py`
  `UNIQUE_KEY_ERRORS` at 57–83 (not 48–69) and `equipment:edit` at 330, 339, … (not 317, 498);
  `conftest.py` `_TABLES` at 138, `SEED_CREATOR` at 144; `test_access_control_api.py` `db_down`
  at 41–46 and `test_auth.py` at 66–71 (the bodies are still identical, so the move holds);
  `local_db.py` line 541 (the S016 seed) is still right.
- **BS1-08** (nit) § 3.2 `test_migration_v31.py`: the pattern to follow is now
  `test_migration_v30.py` (version lists as `range(20, 31)`, `_fill_one_ticket`, a machine with
  every event kind), not `test_migration_v25.py`, which tests a precondition. Warn the coder
  that main already has S031's `test_migration_v26.py`: the branch's file is renamed, never
  copied over it; `V30` / `V31` lists; `SEED = "migration-v31"`.
- **BS1-09** (nit) § 5.6 last bullet and the `properties.py` docstring: `equipment.py`'s order
  now has `(4b)` the meter type row and `(5a)` the type row, and `masters.py`'s docstring
  records model meters as model → meter type → `model_meters` (S038). Add one line: no route in
  `properties.py` locks a meter type or a `model_meters` row, and a model's meters and its
  property values both take the model row first, so S038 joins no cycle. The `equipment.py`
  bullet the branch adds still holds.
- **BS1-10** (nit) § 3.3: `MastersView.vue` now has a *Meter types* section after *Models*
  (S037); say "between *Models* and *Meter types*". `ModelsPanel.vue` rows now hold
  *Documents*, *Meters*, *Edit*; the *Properties* button goes before *Edit*, and
  `<ModelPropertiesModal>` sits beside S038's `<ModelMeterFormModal>`. `stores/masters.js` has
  `meterTypes` on the same pattern; the brief's statement holds.
- **BS1-11** (nit) § 7.1: the branch headed the active column *Active* (impl decision 3);
  S037's `MeterTypesPanel.vue` does the same (line 95), while `EquipmentClassesPanel.vue` still
  says *Status*. Say "*Active*, as Meter types" so the port keeps it.
- **BS1-12** (nit) § 8.4: the step changes `FormModal.vue` (the `closeOnly` prop, impl decision
  1), so the rule is the **full** e2e suite, not "targeted, plus `screens.spec.js`". The test
  names become `S043: …` (the branch's read `S035: …`), and the `e2e/support/properties.js`
  header comment names S043. Also note for the port: the five code-review r1 findings of the
  branch (CR1-01 … CR1-03 minor, CR1-04, CR1-05 nit) stay open and are fixed in the port's
  first fix round (README gate 3); CR1-04's "v26 is not applied anywhere yet" reads v31 now.

## Checked and found consistent

- **Migration number and preconditions.** `_MIGRATIONS` ends at v30 (S038); v31 is free; S039
  holds v32 and S040 has no migration. `_PRECONDITIONS` is `{20, 25}`; v31 adds tables and
  seed rows only, so § 4.3 holds. `LATEST_VERSION = _MIGRATIONS[-1][0]`, so "follows" holds —
  as long as S043 is coded before S039 appends v32. The v29 seed uses the same `INSERT IGNORE`
  / `created_by 'migration-v29'` form the brief cites for v31.
- **The `db_down` move (BR1-16).** Both local fixtures still exist with the same two
  `monkeypatch` lines; `test_health.py` line 14 still says "as test_auth's db_down does";
  `conftest.py` imports `transaction` from `db_helpers` and still needs the branch's
  `import db_helpers`. `test_access_control_api.py` line 145 still uses `db_helpers` itself.
- **Fixtures the branch tests use.** `make_equipment(model=…)`, `make_model(cls=…)`,
  `make_class`, `admin`, `uniq` exist (`conftest.py` 380–419); `test_role_matrix` at
  `test_rbac.py` 198; `tickets_core.part_quantity` at 885; `ApiError` at `api_common.py` 32;
  `UNIQUE_KEY_ERRORS` at 25.
- **Permissions.** `equipment:edit` is in `SITE_SCOPED` (`config_rbac.py` 162) and
  `require_perm` checks it as the union, as the brief says; no new key.
- **Frontend wiring.** `useMasterForm.js` exports `send` (line 47–48, for a multi-request
  save); `useFormModal.js` `fieldError` / `modalError` at 51–54; `dialogs.js`
  `expectDialogFits` needs a submit and a *Cancel* button (33–35) — so the `closeOnly` state
  is still checked on a model with properties, as § 8.4 says. `FormModal.vue` and
  `EquipmentClassesPanel.vue` did not change since the baseline, so the branch's diffs apply.
- **e2e conventions.** The branch's `e2e/support/properties.js` makes its own class, maker,
  model and machine in `SMTW.MCC1` (the e2e seed's unit) — never `SMTW-HYP-01`, which S039's
  set-up keeps and S038's tests also avoid; `card` (`tickets.js` 114), `apiAs`, `asPerson`,
  `rows` and `openDialog` exist. `screens.spec.js` opens `/masters` by the *Sites* button
  only, so the new section needs no row there.
- **Design decisions.** Nothing in S031–S042 or S037–S038 touches `property_*`,
  `class_properties`, `model_property_values`, the model's fixed class (S012), or the `(1)
  class or model → (2) properties → (3) options` order. `meters.py` reads a model-less node's
  model meters as `[]` — the pattern BS1-01 (a) follows.
- **README index.** The S043 row and the S044 *Queued* row are already on main; the brief's
  Status line says "port pending — staleness review s1".
