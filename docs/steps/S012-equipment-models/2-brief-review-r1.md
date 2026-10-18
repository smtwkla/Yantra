```
Step: S012 — Equipment models
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S012 — Brief review, round 1

**Verdict: two `major` findings are open (BR1-01 lock order and type derivation,
BR1-02 migration misses the events ENUM). Not ready for approval.** No blocker.
The four user decisions stand; nothing below asks to reopen them.

Reviewed against: the brief; `docs/steps/README.md`; Plan.MD; Maintenance-Philosophy;
Plant-Facts; `.claude/CLAUDE.md`, `CLAUDE-COMMON.md`; SMTW-WebApp-Base § Local DB
Migration, § File Upload; the S009 brief, its A1/A2 and `s009-code.patch`; the S011
brief; the **working-tree** code after S010 and S011 (`documents.py`, `equipment.py`,
`equipment_core.py`, `file_store.py`, `auth_utils.py`, `access_core.py` via its callers,
`config_rbac.py`, `local_db.py` v1–v8, `masters.py`, `masters_core.py`, `api_common.py`,
`tests/conftest.py`, `test_migration_v8.py`, `test_rbac.py`, `test_equipment_api.py`,
`test_equipment_core.py`, `test_removed_documents_api.py`), the frontend form, detail
view, Masters view, stores and `navigation.test.js`, and `tooling/dev/seed_dev.py`.

Counts: major 2 · minor 6 · nit 2.

---

## Findings

### BR1-01 (major) — § 5.5's lock order cannot derive the type from the model; the order and the decision sources must be restated

**Problem.** § 5.5 says an equipment write "locks its model row after the class and
type locks (S002's order, extended at the end), only when the model is newly picked".
But § 5.3 says the model *decides* the type: "a model with a type: the equipment's
type is set to the model's type". In `equipment.py` the type is locked and checked
by `_check_type_on_update` → `_lock_type(cur, resulting_type, …)`, which needs the
resulting `type_id` as input. With the model locked *after* the type, the shell does
not yet know the model's `type_id` (from its locking read) when it must lock the
type. The coder would have to choose between: a plain read of the model before the
type lock (against the module rule "every refusal about a row is decided from the
row its locking read returned"), locking the model first (against the order the
brief states), or locking the type twice. Three further gaps sit in the same
section:

- `masters.py`'s order for the new writes is not stated. Model create needs the
  manufacturer (active), the class (active) and, when given, the type (active, of
  that class); model reactivate needs the manufacturer and class; manufacturer
  deactivate must count active models under the manufacturer's lock so a
  concurrent reactivate cannot slip in. Today's docstrings say "class → type" and
  "person → … → units"; manufacturers are new.
- The pure function's inputs are under-specified: "from the equipment's resulting
  class and type and the model (or none)". Two of its branches ("newly picked",
  "a class change on an equipment that has a model, without a new model") need
  the **stored** `model_id`/`type_id`/`class_id` and what the request **sent**, not
  only the resulting values.
- The interplay with S004's existing rule is not stated: `_check_type_on_update`
  refuses a class change with a stored type and no `type_id` sent ("Pick a type of
  the new class, or none"). If the same request picks a model that carries a type,
  that refusal must not fire (the type is derived). The order "model rule first,
  then the S004 type rule on the result" has to be written down.

**Why it matters.** Lock order is exactly what the full track exists to settle
(README § Tracks), and a wrong choice here is either a deadlock risk or a silent
break of the module's own rule; the coder would be deciding it alone.

**Options.**
1. **Recommended.** Insert the model between the class and the type: (1) node,
   (2) parent, (3) unit, (4) class, **(5) model**, (6) type, (7) serial counter.
   Masters: manufacturer → class → type → *insert model* (create); manufacturer →
   class → model row (reactivate); manufacturer row then a plain count of active
   models (deactivate); model row alone (designation edit, deactivate). I checked
   the pairs: no transaction holds a type while waiting for a model, and every
   path that takes both class and model takes the class first, so no cycle joins
   `equipment.py`, `masters.py` or `documents.py` (which takes the model row
   alone). State this order in both module docstrings, as S002/S004/S011 did.
   Then write the pure rule's signature, e.g.
   `check_model(sent, stored, model)` where `sent` = `{class_id?, type_id?, model_id?}`
   as the request had them, `stored` = the locked node's `{class_id, type_id,
   model_id}`, `model` = the locked model row `{id, class_id, type_id, active}` or
   `None`; it returns the resulting `type_id` (or the 400/409 refusal), and the
   S004 type check runs on that result with `newly_chosen` = "the type changed by
   this request" (see BR1-06 for the inactive-type edge).
2. Keep the model at the end and let the type lock come from a plain read of the
   model: acceptable only because the model's class and type are immutable
   (§ 5.2), but it contradicts the module rule and needs a written exception.
   Not recommended.

### BR1-02 (major) — Migration v9 misses the `equipment_events.event` ENUM change, so the "model" event cannot be written

**Problem.** § 1.9, § 3 and § 7 add a tracked event `"model"`, but § 4 (which
claims to list the whole migration) has no statement for it. `equipment_events.event`
is `ENUM('created','moved_unit','moved_parent','status','criticality','class','type')`
(v4, extended in v5). An `INSERT … 'model'` fails under strict SQL mode
(error 1265 "Data truncated") or stores `''` under a lax one; either way the
"model" event test fails and, if the coder patches it ad hoc, migrations being
append-only means a forgotten statement costs a v10.

**Why it matters.** The migration is presented as complete ("SQL only, each
statement safe to run twice"); the coder would copy it.

**Options.**
1. **Recommended.** Add to § 4.2, after the equipment and documents changes, the
   v5 form: `ALTER TABLE equipment_events MODIFY event ENUM('created','moved_unit',
   'moved_parent','status','criticality','class','type','model') NOT NULL` — the
   existing values in their order, `'model'` appended (metadata-only, safe to
   re-run). Write the whole v9 out as S009 § 4 did (BR1-03 of that step), so
   nothing else is left to memory.
2. Drop the event (§ 7's rejected alternative). Not recommended: a model change
   alters what the machine is recorded as, as the brief argues.

### BR1-03 (minor) — § 4.3's conversion needs its SQL spelled out; three details decide what the engineer sees afterwards

**Problem.** The rules are right in outline and idempotent in principle
(`INSERT IGNORE` on the unique keys; step 3 only where `model_id IS NULL`), and
MariaDB 11.4's `INSERT … SELECT`, `GROUP BY … HAVING COUNT(DISTINCT …) = 1`,
`UPDATE … JOIN` and `REGEXP_REPLACE` all cover it. But three points are left to
the coder, and each changes data in production:

1. **Which spelling wins.** "Keeping the first spelling met (by the lowest
   equipment id)" is not what `INSERT IGNORE … SELECT DISTINCT TRIM(make)` gives:
   under a case-insensitive collation `DISTINCT` merges "Atlas Copco" and "ATLAS
   COPCO" and returns whichever the scan met first, with no order guaranteed.
   The deterministic form is no `DISTINCT` and an `ORDER BY e.id` on the
   `INSERT IGNORE … SELECT`, so the first inserted row wins and later duplicates
   hit the unique key and are ignored. The same holds for the model designation's
   spelling in step 2 (a non-aggregated column under `GROUP BY`).
2. **Inner spaces.** The validator collapses "Atlas  Copco" to "Atlas Copco"
   (§ 4.1), but `TRIM` does not; the migration would create two manufacturers that
   the API would later refuse as duplicates. Use `REGEXP_REPLACE(TRIM(make),
   '[[:space:]]+', ' ')` in every step (the join in steps 2–3 must use the same
   expression), or state that such pairs stay as old text.
3. **Scrapped equipment and inactive classes.** Scrapped rows carry make/model too:
   they take part in "every equipment with that pair has the same class" and get
   linked in step 3 (fine, but say so). A model may be created under a class that
   is now inactive, which § 5.2 forbids through the API; harmless (its equipment
   already has that class; the picker never offers an inactive class), but state
   it.

The migration test (§ 8) also has no harness note: after S012 the API refuses
`make`/`model`, so the test seeds them with an SQL `UPDATE` on API-created
equipment, deletes `db_version` 9 and calls `init_db` twice — as
`test_migration_v8.py` does for `user_units`. Note that a re-run rescans every
equipment row in the shared test DB (others have `NULL` make, so no effect).
`conftest._TABLES` must gain `equipment_models` and `manufacturers` (after
`equipment`, before `equipment_types` and `equipment_classes`).

**Why it matters.** The conversion runs once on production data; "which spelling
survives" and "how many pairs convert" are what the user will check (§ 9.1).

**Options.**
1. **Recommended.** Write the four statements out in § 4.3 with the `ORDER BY
   e.id`, the whitespace expression and `created_by = 'migration-v9'`, and add
   the scrapped/inactive-class sentence and the test-harness note.
2. Keep the prose and let the coder write the SQL, reviewed in code review. Costs
   a round.

### BR1-04 (minor) — The composite-FK pattern of v5 is not followed, and the departure is not stated

**Problem.** Migration v5 made "the type belongs to the equipment's class" a
database rule with `fk_equipment_type (type_id, class_id) REFERENCES
equipment_types (id, class_id)` over `uq_equipment_types_id_class`. S012 has the
same shape twice and uses plain FKs both times:

- `equipment.model_id` → the model's class must equal the equipment's class
  (§ 5.3);
- `equipment_models.type_id` → the type must be of the model's class (§ 5.2).

Because a model's class and type are fixed after creation (§ 5.2), the composite
form is safe: `UNIQUE (id, class_id)` on `equipment_models`, then
`FOREIGN KEY fk_equipment_model (model_id, class_id) REFERENCES equipment_models
(id, class_id)` on `equipment`, and `FOREIGN KEY (type_id, class_id) REFERENCES
equipment_types (id, class_id)` on `equipment_models`. A class change that keeps
the model then fails at the database too, as the S002/S004 CHECK and FK tests
expect ("holds when the shell is bypassed"). The API-level 400 of § 5.3 stays the
answer the user sees; the FK is defence in depth.

**Why it matters.** CLAUDE-COMMON: a departure from the pattern of the area being
worked on is pointed out, not taken silently.

**Options.**
1. **Recommended.** Use the composite FKs; add the two "bypassed shell" tests
   (a model of another class on an equipment row; a type of another class on a
   model row → `IntegrityError` 1452).
2. Keep plain FKs and say in § 7 why (e.g. to keep the model's class editable
   later). Then the row above in § 7 needs a reason.

### BR1-05 (minor) — The "model" event's value can exceed `VARCHAR(200)`, and the no-model word is unstated

**Problem.** `equipment_events.old_value`/`new_value` are `VARCHAR(200)`. The
event value is the label "Atlas Copco GA37" = manufacturer name (≤ 100) + space +
designation (≤ 100) = up to **201** characters, one over. Strict mode refuses the
insert (1406), so a legitimately long pair would make the equipment save 500.
Also unstated: the display word for "no model" in events (`type` uses `"none"`,
`NO_TYPE`, and `masters_core` reserves that type name for the reason); and that
picking a model with a type writes a `"type"` event next to the `"model"` event
(`tracked_changes` compares `type_name`), which the test "writes 'model' on a
model change only" would otherwise contradict.

**Options.**
1. **Recommended.** Cap the designation at 80 (nameplate designations are short;
   100 + 1 + 80 = 181), state `"none"` as the no-model display, and reword the
   test: "model" on a model change; "type" too when the model sets a type.
2. Widen the two event columns in v9 (`MODIFY … VARCHAR(255)`). Also fine; one
   more statement.

### BR1-06 (minor) — Edge cases of § 5.3 the coder would have to decide

**Problem.**
1. **Model whose type has since been deactivated.** Picking the model is allowed
   (the model is active) but the derived type goes through `_lock_type(…,
   newly_chosen=True)` → 409 "The type is inactive", which the user never chose.
   Decide: either a type set by the model is not "newly chosen" for the active
   check (it is kept, only its class is verified — recommended, since the model's
   own `active` governs what can be picked), or a model whose type is inactive
   is refused with a message naming the model.
2. **Unknown `model_id`** → 400 field `model_id` "Unknown model" (as `_lock_type`
   does), not a 500 from the FK; state it.
3. **A part under a model-less parent** and **the same model on parent and
   child** are both fine (§ 5.3 "Levels"); say so in one line so nobody adds a
   rule.
4. **Model unchanged, type sent.** On an update that keeps a model with a type
   and sends a *different* `type_id` → 400 "The type comes from the model"
   (stated); it needs the stored model's `type_id`, so `_NODE_COLUMNS` must join
   `equipment_models` (plain read is fine here: the model's type is immutable).
   That join also serves § 5.4's detail fields and § 1.8's search.

**Options.** State the four in § 5.3 (recommended as above) and add the first and
second to § 8.

### BR1-07 (minor) — Existing tests and the dev seed that break, and two wrong claims about today's code

**Problem.**
- `test_equipment_api.py::TestEvents::test_untracked_edits_write_no_event` sends
  `make="Make", model="M1"` and asserts them back; under § 5.4 it becomes a 400.
  `test_equipment_core.py` uses `make` in the tracked-state fixture (line 90),
  in `test_optional_text_is_trimmed…` (171–174) and in the invalid-field table
  (212). The brief lists the files but not these cases; name them so "the S002
  tests keep their behaviour" is not read as "unchanged".
- `tooling/dev/seed_dev.py` (S010/S011, uncommitted) posts `make` for the Haendle
  extruder and the two Atlas Copco compressors; after S012 it dies on the first
  400. It is not in § 3. It should instead seed manufacturers and models (Atlas
  Copco GA37, class CMP, type Screw compressor — the brief's own example) and
  pick them, which also gives the manual checks their data.
- § 5.4 "The old text is not searched any more": it never was — today's search
  covers code, name, notes and type name (`list_equipment`). Say "stays
  unsearched".
- § 3 says the **list** carries `legacy_make`/`legacy_model`; § 5.4 says the
  detail. The list needs `model_id`, `model_designation`, `manufacturer_name`
  (for a column, if any) but not the legacy text. Pick one.
- `validate_equipment` today ignores unknown keys ("a `code` in the body is
  ignored like any other unknown field"), so refusing `make`/`model` is a new,
  explicit rule in the validator, including when sent as `null` (the old form
  always sends both keys). State that `null` is refused too, with field `make`.

**Options.** Add the cases and the seed script to § 3 and § 8; fix the two
sentences. (Recommended; no alternative worth listing.)

### BR1-08 (minor) — Manual checks: the production steps are missing; one check belongs on a phone

**Problem.** The three checks are UI flows and are rightly important. Missing:

- **Production, before and after the release** (important): count the equipment
  with make/model text before deploying (§ 9.1 says the user can); after the
  migration, confirm the manufacturers and models with `created_by =
  'migration-v9'` and the equipment left as "(old text)" match what was
  expected, and sort the leftovers. S009 § 10.5 also asked for the **production
  MariaDB version** (Settings › Database) to be recorded before release, since
  the CHECK needs ≥ 10.2.1 and `ADD CONSTRAINT IF NOT EXISTS` needs ≥ 10.5; the
  brief should carry that over (the S009 patch ran v7's statements on 11.4
  without the `MODIFY` fallback, which is worth saying in § 4.2).
- **Phone** (plain note): the Model picker is a `<select>` with long labels; open
  the equipment form on Android and iPhone and pick a model.

**Options.** Add both; mark the production one important. (Recommended.)

### BR1-09 (nit) — Standards: edition and clause of ISO 55001; one over-claim of ISO 14224

- **ISO 55001.** § 2 cites "§ 7.6 (control of documented information)" and § 2's
  last bullet "§ 7.5". In the 2014 edition, documented information is 7.6 (its
  control 7.6.3) and 7.5 is "Information requirements"; the 2024 edition
  renumbered. S009 settled on "§ 7.6.3 (2014 numbering)" after its BR1-04, and
  S011 cites 2024. Name the edition once and use its numbers for both bullets.
  In plain terms the clause says: information the organisation relies on must be
  identified, kept correct, available where needed and protected from
  uncontrolled change — one controlled copy of a manual is the simplest way to
  satisfy it.
- **ISO 14224.** "A model therefore sits under one class and at most one type"
  reads as if the standard said so. It lists *manufacturer's name* and
  *manufacturer's model designation* as attributes of each equipment unit and
  places the unit in a class and type; it does not say a model is scoped to a
  class. The scoping is Yantra's design (user decision 2), justified by the
  reliability argument the bullet makes. Soften "therefore" as S009 did.
- **ISO 27001 A.5.12** (classification) is what the "No confidential documents
  / Visible at every site" line implements, as S009 § 2 said; A.8.3 covers the
  access rule. Add the reference.
- **EN 13460** and **ISO 8000** are cited correctly: EN 13460 splits the documents
  maintenance needs into those that come *with* the product (manuals, drawings,
  parts lists) and those the plant produces while using it; ISO 8000 is the
  data-quality family whose master-data parts say one record per real thing,
  with one spelling.

### BR1-10 (nit) — Small specification gaps

- `file_store` folder for the model owner: name it (`equipment-models/<id>/`,
  next to `equipment/<id>/`).
- Removed list, model branch: what `q` matches (designation, manufacturer name,
  title, original name — the S009 A1 analogue), and that `code` is `null` and
  `name` the label.
- Model picker on edit: the node's current model stays listed when inactive,
  "(inactive)", as classes and types do; a model's label in lists carries no
  class since the list is already filtered by it.
- § 8 "`navigation.test.js`: the two new sections": that test covers `navItems`
  in `stores/navigation.js`; Masters sections are local to `MastersView.vue` and
  have no test today (S010's Trades/Team added none). Drop the claim or say how
  the sections would be tested.
- Docstrings of `equipment.py`, `documents.py`, `masters.py` and `file_store.py`
  follow the new order and owner; `UNIQUE_KEY_ERRORS` gains `uq_manufacturers_name`
  and `uq_equipment_models_maker_designation` with the two 409 texts of § 5.
- `equipment.py` detail: `legacy_*` are `null` when a model is set — the detail
  today exposes `make`/`model` by those names; say the keys are renamed (the old
  frontend's Make/Model rows read `node.make`).

---

## Checked and found consistent

- **The four user decisions** against code and standards: no conflict found. A
  model under one class at any tree level matches Plan § 4.1's "a class is a
  kind, not a container".
- **Permissions under S011.** `equipment:edit` for model and manufacturer writes
  and model-document writes through `require_perm` (the global union) matches
  classes and types (S011 § 9.5) and `has_perm`'s "held somewhere"; model reads
  and documents on `equipment:read` anywhere match the A.8.3 departure confirmed
  at S009 gate A; restore/purge on `equipment:purge_documents` anywhere is the
  S009 A1 rule (a manager at one site can erase a model document used
  elsewhere — accepted there; worth one line in § 5.5 so it is a stated
  consequence). `has_perm` on a `SITE_SCOPED` key is allowed (only `has_perm_at`
  asserts). No new keys, so `test_rbac` and `navigation.test.js` matrices stand.
- **Removed list.** The `UNION ALL` with the node branch keyed by
  `accessible_unit_ids(cur, "equipment:purge_documents")` (already in the
  working tree) and an unscoped model branch; "empty set → node branch left out,
  not the whole list" is the right reading of S011 (the user passed
  `require_perm`, so they hold the key at some site with no active units).
- **Reuse of the S009 patch.** The owner table, stacked route decorators,
  `file_store` owner signatures, `inherited` groups with `path`, the
  `DocumentsCards` move and the in-panel Masters view all carry over with
  `class`/`type` → `model`. The patch's `_lock_node_for_change(cur, node_id)` is
  superseded by the working tree's keyed version, as § 3 says; the patch's
  `canEditEquipment` from the global `userPermissions` is right for the
  "Managed in Masters" hint (model documents are global), while `canEdit` for the
  node's own documents must keep S011's `node.permissions`.
- **CHECK and `MODIFY`.** `chk_equipment_documents_owner` with two owners, the
  index-before-FK order and `MODIFY equipment_id INT NULL` were run by the S009
  code on MariaDB 11.4 (its migration-v7 statements, no fallback needed), and
  its "bypassed shell" test expects `OperationalError` 4025 — the brief's test
  wording "the CHECK refuses" is consistent with it.
- **Collation.** Tables are `utf8mb4` with the server default; the Trades test
  "duplicate name in another case is 409" shows the dev server is
  case-insensitive, so `UNIQUE(name)` and `UNIQUE(manufacturer_id, designation)`
  give the 409s of § 5 through `UNIQUE_KEY_ERRORS`.
- **Documents lock discipline.** One owner lock per document write (the model
  row), then `equipment_documents` only; no cycle with either module.
- **Track.** Full, correctly: a migration with data conversion, access-checked
  routes, locking.
- **Out-of-scope list** matches Plan § 2 (no per-class custom fields; design
  data later) and keeps the step one reviewable slice.
