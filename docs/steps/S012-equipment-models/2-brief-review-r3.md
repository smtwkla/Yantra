```
Step: S012 — Equipment models
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 17-10-2026
```

# S012 — Brief review, round 3

**Verdict: no `blocker` or `major` finding is open.** This is the third and last
review round on the full track; what is left is six `minor` points and a set of
`nit`s, none of which reopens a design decision. Approval is the user's.

Reviewed: the brief as rewritten on 17-10-2026 after gate A, including the
mid-review change to `equipment.model_id NOT NULL` (§ 4.2, § 5.3, § 7, § 8, § 9.4,
Review log item 5); `2-brief-review-r1.md`, `-r2.md`; `docs/steps/README.md`;
Plan.MD (committed and the uncommitted working copy); Maintenance-Philosophy;
Plant-Facts; `.claude/CLAUDE.md`, `CLAUDE-COMMON.md`; SMTW-WebApp-Base § Local DB
Migration, § File Upload; the S004 brief § 5; the S009 brief and `s009-code.patch`;
the **working tree** after S010/S011: `local_db.py` v1–v8, `equipment.py`,
`equipment_core.py`, `masters.py`, `masters_core.py`, `documents.py`,
`file_store.py`, `api_common.py`, `app.py`, `tests/conftest.py`,
`test_equipment_api.py`, `test_equipment_core.py`, `test_masters_api.py`,
`test_site_checks_api.py`, `test_migration_v8.py`, `documents_helpers.py`; the
frontend form, list, detail view, Masters view, stores, `equipmentLabels.js` and
its test; `tooling/dev/seed_dev.py`, `dev-db-reset.bat`.

The user's four gate-A decisions (model under one class; make/model dropped,
no conversion; a model on every node with Generic / in-house records; class and
type derived from the model) and the fifth (`NOT NULL`) are taken as settled.
Nothing below asks to reopen them; the findings are about what they cause.

Counts: minor 6 · nit 1 (seven small points under one ID).

---

## Earlier rounds — Accepted answers verified in the text

Every round-1 and round-2 answer marked `Accepted` is in the brief text, not only
in the Review log, or is correctly marked superseded by the rewrite:

- **BR1-01** § 5.3 signature and rules, § 5.5 orders for all three modules;
  **BR1-02** the ENUM statement in § 4.2; **BR1-04** composite FKs (§ 4.1, § 4.2)
  and the bypassed-shell tests (§ 8); **BR1-05** 80 characters, the "type" event
  next to the "model" event (§ 1.9, § 8); **BR1-06** rules 2, 5, 7, the
  `_NODE_COLUMNS` join (§ 3); **BR1-08** the production check important, phone
  plain (§ 8); **BR1-09** ISO 55001:2014 numbering, ISO 14224 now an explicit
  departure, A.5.12 (§ 2); **BR1-10** folder, `q`/`code`/`name`, inactive current
  model, docstrings, `UNIQUE_KEY_ERRORS`.
- **BR2-01** model locked only when newly picked, `LOCK_EQUIPMENT` gains `model_id`
  (§ 3, § 5.5); **BR2-03** `app.py`, `test_row_fields`, `documents_helpers.py`,
  removed list as new code (§ 3); **BR2-04** inactive type on model create → 409,
  list order (§ 5.2), `include_inactive=1` (§ 1.4); **BR2-05** label from the
  locked row (§ 3) — but see BR3-04 on what that now means.
- **Superseded correctly:** BR1-03 (conversion), BR1-07's `legacy_*` and "stays
  unsearched", BR2-02 (class mismatch message), BR2-04's `<now>`: the columns are
  dropped and the class comes from the model, so none of these has a place.
- The "no-model display word" of BR1-05 is rightly gone: with `NOT NULL` a model
  event never has a "none" side.

---

## Findings

### BR3-01 (minor) — § 4.2 misstates which statement fails on a populated table, and what state that leaves; the test DB is affected on the coder's first run

**Problem.** § 4.2 says "On a table that already has equipment the `ADD COLUMN`
fails (0 is no model id, so the FK refuses it)". That is not how MariaDB behaves:
`ALTER TABLE … ADD COLUMN model_id INT NOT NULL` **succeeds** on a populated
InnoDB table and fills every existing row with the implicit default `0` (strict
mode governs INSERT/UPDATE, not an ALTER's fill value). The statement that fails
is the third one, `ADD CONSTRAINT fk_equipment_model FOREIGN KEY …` (error 1452:
no `equipment_models` row `(0, class_id)`). Three consequences the brief should
state, because the coder and the user will each meet one:

1. **Half-applied v9.** v9 is then applied up to the index, with no `db_version`
   row. "Each statement safe to re-run" holds, but a re-run fails at the FK again
   for as long as the rows exist: the database is **stuck, not merely retried**,
   until the equipment rows are deleted or the DB is reset. The brief's own
   sentence in the old § 4.2 ("a failing migration keeps the app retrying every
   30 s") described exactly this; it should stay, now as the accepted cost.
2. **The test DB on the coder's first run.** `conftest._clean_tables` calls
   `ensure_schema()` *before* it deletes the tables (lines 78–91). The
   `vel_yantra_test` DB holds equipment rows from the previous session, so the
   first `run-backend-tests.bat` after v9 is added fails with "Test database not
   ready" and leaves the test DB half-applied as in (1). The coder must run
   `tooling/dev/dev-db-reset.bat` (it drops the volume: both `vel_yantra_master`
   and `vel_yantra_test`) **before** the first test run, and the impl report
   should say so, since the same happens on any other machine that still has a
   pre-v9 test DB.
3. **Production, if assumption § 9.4 is wrong.** The release check (§ 8) is the
   guard; the brief should state what happens if it is skipped or misread: v9
   stops at the FK, the app serves 503 for every DB route and retries every 30 s,
   and recovery is manual SQL on production by the user (delete the equipment
   rows, or drop the half-added column and index, then restart). This is the
   trade the `NOT NULL` decision makes and it belongs in § 7's row as its cost,
   not only in § 4.2.

**Why it matters.** The one sentence the coder would copy into the migration
comment is wrong, and the recovery path is the kind of thing the impl report and
the release checklist need written down before the release, not after.

**Options.**
1. **Recommended.** Reword § 4.2: "the `ADD COLUMN` fills existing rows with 0 and
   the `ADD CONSTRAINT … FOREIGN KEY` then fails (1452); v9 is left half-applied
   and keeps failing on retry until the equipment rows are gone — dev and test
   DBs are reset with `dev-db-reset.bat` before the first run; on production the
   § 8 check prevents it, and the recovery would be manual." Add "the test DB too,
   before the first test run" to § 3 Tests, and the cost to § 7's `NOT NULL` row.
2. Reorder v9 so a population check fails first and cleanly. Not possible in
   SQL-only migrations without a conditional; not recommended.

### BR3-02 (minor) — The API cannot produce "a model of an inactive class", so § 8's case and § 5.3 rule 5 need a stated construction

**Problem.** § 5.2 makes an invariant: a class with an active model can't be
deactivated; a model can't be created or reactivated under an inactive class. So
through the API an **active** model always has an active class. § 8 (Equipment)
lists "model of an inactive class → 409", and § 5.3 rule 5 says the shell's
`_lock_class` refuses "The class is inactive" when the model is newly picked.
Through the API the only model under an inactive class is an **inactive** one,
which rule 3 refuses first (409 `model_id` "This model is inactive"), so rule 5's
message is unreachable and the test as written can't be set up. The coder would
either write a test that can't pass as specified or reach for SQL without the
brief saying so.

**Why it matters.** A test case the coder can't construct, and a rule that
looks like a decision but is defence in depth, should each say what they are.

**Options.**
1. **Recommended.** Keep rule 5 as defence in depth (one line: "unreachable
   through the API because of § 5.2; kept because the class lock is needed for the
   code prefix on create anyway") and rewrite the § 8 case as a bypassed-shell
   test: deactivate the class by SQL (`UPDATE equipment_classes SET active = 0`,
   as `_db(...)` does in `test_equipment_api.py` for other bypass cases), then
   pick its still-active model → 409 `class_id` "The class is inactive".
2. Drop rule 5 and the case, and lock the class only on create (for the prefix).
   Less code, but a class deactivated by a future route that forgets § 5.2's
   count would go unnoticed. Not recommended.

### BR3-03 (minor) — Existing cases that the class-deactivation rule breaks are not named; the general "rewritten as model changes or dropped" does not cover them

**Problem.** § 3 names the S004 type-rule cases as the ones to rewrite or drop.
The new § 5.2 rule "class deactivation refused while it has active models"
breaks a different set, because every `make_equipment(cls=cls)` will now also
create an **active model** under `cls`:

- `test_masters_api.py::TestEquipmentClasses::test_deactivated_class_with_equipment_stays_frozen`
  (line 376): deactivates a class that has equipment → now 409. It needs "deactivate
  the model first, then the class", and still asserts the frozen code.
- `test_equipment_api.py::TestReclassify::test_existing_equipment_keeps_a_deactivated_class`
  (line 248): same shape, same fix; its `class_id=cls["id"]` sent back is also a
  § 5.4 refusal now.
- `test_masters_api.py::TestEquipmentTypes::test_deactivating_a_type_in_use_is_allowed`
  (line 475): `make_equipment(cls={"id": …}, type_id=…)` → `type_id` refused; it
  needs a model carrying that type.
- `test_site_checks_api.py::TestEquipmentWrites::test_status_notes_type_at_b`
  (line 52): the `{"type_id": None}` parameter still gets its 403 (the site check
  at line 496 of `equipment.py` runs before `clean_body`), so it passes while
  testing nothing; it should become `{"model_id": <a model of another class>}`.
- `TestReclassify::test_to_an_inactive_class_is_409` and
  `test_create_with_an_inactive_class_is_409` are the unreachable case of BR3-02.

Also the whole of `TestReclassify` and the class-change half of `TestTypes`
(lines 994–1039) become "a new model of another class" cases; the brief's rule
"the report lists each dropped case and why" covers them, which is fine.

**Options.** Name the four cases above in § 3 Tests with their fix (recommended;
nothing to choose). It saves the coder a run of red tests and makes "the S004
rules on equipment go" a complete list.

### BR3-04 (minor) — `_NODE_COLUMNS`: inner or `LEFT JOIN` on the model, and what BR2-05's "label from the locked row" then does

**Problem.** § 3 says `_NODE_COLUMNS` joins `equipment_models` and
`manufacturers`, and (BR2-05) the "model" event's value is "built from the locked
model row plus a plain read of its manufacturer, as `_written_state` already does
for class and type". Two readings, with different outcomes:

- **Inner `JOIN`** (the class's pattern, natural now that `model_id` is `NOT
  NULL`): a model committed after this transaction's snapshot is invisible to the
  re-read, which then finds no row → `_reread`'s 409 "This record changed while
  saving — try again" — the same accepted race the class has today (`_reread`
  docstring). BR2-05's patch is then only for a **stale designation** (renamed
  while this write waited), as the class-code patch is; a plain read of
  `manufacturers` adds nothing (it reads the same snapshot).
- **`LEFT JOIN`** (the type's pattern): the re-read succeeds with NULL model
  columns and BR2-05's patch fills the label; the manufacturer plain read is then
  what finds the name. But a `LEFT JOIN` on a `NOT NULL` FK column misleads the
  next reader, and the detail/list would have to tolerate NULL model fields that
  the schema says cannot exist.

The brief doesn't say which; the coder would choose, and the choice decides the
behaviour of a test the brief doesn't have (a model the snapshot can't see, as
`test_class_and_unit_codes_in_events_come_from_the_locks`).

**Options.**
1. **Recommended.** Inner `JOIN` for both tables, as the class; state that a
   model invisible to the snapshot is the existing `_reread` 409 (retryable);
   `_written_state` patches `model_designation` from the locked model row (stale
   rename) and `manufacturer_name` from the re-read (a display-only residual,
   accepted as S002 accepted site codes). Delete the "plain read of its
   manufacturer" clause from § 3. One `stale_reread` test as for the class code.
2. `LEFT JOIN` and keep BR2-05 as written. Works; carries the misleading join.

### BR3-05 (minor) — The "model" event has no label in the frontend; `utils/equipmentLabels.js` and its test are missing from § 3

**Problem.** § 1.9 adds the event `"model"`. `describeEvent` in
`frontend/src/utils/equipmentLabels.js` has cases for `created`, `moved_*`,
`status`, `criticality`, `class`, `type` and `default: String(event.event)`, so a
model change would show in History as the bare word "model".
`frontend/tests/equipmentLabels.test.js` tests each case and "an unknown event is
shown by name". Neither file is in § 3 Frontend.

**Options.** Add both to § 3: a `case "model": return change("Model", oldValue,
newValue)` and its vitest line ("Model: Atlas Copco GA37 → Atlas Copco GA55").
No "none" branch is needed (BR1-05's word is gone with `NOT NULL`). Recommended;
nothing to choose.

### BR3-06 (minor) — The production check "the equipment list is empty" can pass with rows still in the table

**Problem.** § 8's important production check says "confirm that the equipment
list is empty". The equipment list **defaults** hide scrapped rows
(`include_scrapped != "1"`, `equipment.py` line 415) and show the equipment level
only (`level` default `"equipment"`, line 406), and a user without
`equipment:read_all_units` sees only their units. A scrapped machine, or one
entered then scrapped as a trial, is still a row in `equipment` and makes v9 fail
exactly as BR3-01 describes. The check as written could be ticked while the
migration would still fail.

**Options.**
1. **Recommended.** Word the check as: "as IT admin or admin (sees every unit),
   Equipment list with **Show scrapped** ticked and **Level = All levels**: total
   0." Optionally also "and Masters shows no equipment classes with a frozen code"
   as a cross-check, since a class with equipment refuses a code change.
2. Have Settings › Database show the row count of `equipment`. More code for a
   one-off; not recommended.

### BR3-07 (nit) — Small gaps

1. **Test wording for the `NOT NULL` rule** (§ 8 Migration): "an equipment row
   without `model_id` is refused by the database" — an INSERT that *omits* the
   column fails with 1364 (no default), which PyMySQL does not map to a specific
   class; an INSERT with an explicit `NULL` fails with 1048 (`BAD_NULL_ERROR`) →
   `IntegrityError`. Say "with `model_id` NULL → `IntegrityError` 1048", so the
   test's `pytest.raises` is deterministic, as the 4025 and 1452 cases are.
2. **Messages:** § 5.3 rule 1 and rule 6 want "Pick a model", but
   `validate_equipment`'s generic required-field text gives "Model id is required"
   and `_id_parser("Model", nullable=False)` gives "Model must be a record id" for
   a `null`. Either accept the generic texts (and change the brief) or say
   `model_id` gets its own required/null message.
3. **`derive_from_model` returning `errors` with a 409:** every pure validator in
   this codebase returns messages (`{field, message}` or a plain string) and the
   shell picks the status (`_lock_type`, `check_type_class`). Returning statuses
   from the core would be a new shape. Say: the function returns `(class_id,
   type_id, message)` and the shell maps "This model is inactive" to 409 — or
   keep the inactive check in the shell like `_lock_class` and let the pure
   function only derive (two lines; the pure test then covers the derivation
   only).
4. **Type cleared by the new model:** rule 4 "set to the model's" should say
   explicitly that `type_id` is written as `NULL` when the new model has no type
   (not left out of the UPDATE), so the "type X → none" event is written; the
   coder's `clean` dict must carry the key with `None`.
5. **List screen:** § 3 adds `model_id`, `model_designation`, `manufacturer_name`
   and `model_label` to every list row, and § 1.8 makes the search match the
   model, but no screen shows the model in the list; a row found by "GA37" would
   not say why. Either add a Model column to `EquipmentView.vue` (recommended;
   `model_label` after Class) and widen the search placeholder ("Search code,
   name, model, notes…"), or keep the four fields for the detail only.
6. **Seed and `Uniq`:** `conftest.Uniq` needs `manufacturer_name()` and
   `designation()` (or the shared helper uses `type_name()`-style counters), and
   `seed_dev.py`'s `EQUIPMENT` tuples replace `make, model` by a model key; the
   component unit (`GBX` gearbox) needs a Generic gearbox model. One line in § 3.
7. **Standards, for the owner:** § 2's ISO 8000 line ("one record per real
   thing") and the ISO 14224 pooling argument both sit awkwardly with the Generic
   models the same section defends: "Generic screw compressor" is not a product,
   and reliability pooled by that model would mix unlike machines. Worth one
   sentence: Generic rows mean "maker unknown" and are excluded from (or flagged
   in) any later per-model reliability comparison; the manufacturer name
   "Generic" makes them easy to find. The standards are otherwise cited
   correctly: ISO 14224 Table 5 lists manufacturer's name and model designation
   among the common equipment data (both high-priority items), and its reason is
   pooling of comparable units; EN 13460 separates documents delivered with the
   product from those made in use; ISO 55001:2014 § 7.6/§ 7.6.3 is the documented
   information clause and its control; ISO 27001:2022 A.8.3 restricts access to
   information, A.5.12 classifies it; ISO 8000 is the data-quality family.

---

## Checked and found consistent

- **The five user decisions against the code.** Nothing in the working tree
  contradicts them. `equipment.class_id` and `type_id` stay (filters, codes, the
  S004 composite FK) and are written only from the model, as § 4.2 says.
- **§ 1 / § 3 / § 4 / § 5 / § 6 / § 8 agree with each other** after the rewrite:
  the form has a model picker only (§ 1.4, § 5.4, § 6); class and type derived
  (§ 1, § 5.3 rule 4, § 7); `NOT NULL` (§ 4.2, § 5.3 rule 6, § 7, § 8, § 9.4);
  make/model dropped (§ 1.4, § 3, § 4.2, § 7). One leftover found: none — the
  "No model" wording and rule 6's pre-v9 clause are gone everywhere.
- **Lock order, pairwise, against the working tree.** `equipment.py` node →
  parent → unit → **model** → class → counter; `masters.py` model create
  manufacturer → class → type → insert (the insert's FK checks S-lock rows already
  X-held), model reactivate manufacturer → model → class (a plain read of the
  immutable ids first, the `update_equipment_type` pattern), designation edit /
  deactivate the model row alone, manufacturer deactivate the row then a plain
  count, class deactivate the class row then a plain count (a concurrent model
  reactivate waits at the class lock and then finds it inactive → 409; a
  concurrent create waits likewise), class → type unchanged; `documents.py` the
  model row alone then `equipment_documents`. Every path that takes both model and
  class takes the model first; nothing holds a class while waiting for a model;
  nothing holds a type while waiting for anything new; `equipment.py` never locks
  manufacturers and `masters.py` never locks equipment. The equipment write's FK
  check on `fk_equipment_type` takes an S-lock on the type row without an X-lock
  first: a type rename/deactivate holds the type alone and waits on nothing, a
  type reactivate takes the class first — no cycle either way. No deadlock found.
- **Removing `class_id`/`type_id` from the equipment API.** `_check_type_on_update`,
  `_lock_type`, `check_type_class` on equipment writes and `_LOCK_TYPE` go (§ 3);
  the list's `class_id`/`type_id` **filters** stay and need no change (they read
  `e.class_id`/`e.type_id`); `EquipmentView.vue`'s class and type filters stay as
  they are; `EquipmentDetailView.classLabel` still works from `node.class_id`.
  The move and status dialogs send neither key. The old form always sends
  `make`, `model`, `class_id`, `type_id` (lines 22, 50–51), so refusing them even
  as `null` is needed for an old tab to fail loudly, as § 5.4 says.
- **Migration v9 against MariaDB 11.4 and v1–v8** (apart from BR3-01's wording):
  `ADD COLUMN IF NOT EXISTS`, `ADD INDEX IF NOT EXISTS`, `FOREIGN KEY IF NOT
  EXISTS`, `DROP COLUMN IF EXISTS`, `ADD CONSTRAINT IF NOT EXISTS … CHECK` and the
  two `MODIFY`s are each a no-op on re-run; index before FK on both tables;
  `uq_equipment_types_id_class` (v5) is the referenced index for
  `fk_equipment_models_type`, `uq_equipment_models_id_class` for
  `fk_equipment_model`; the ENUM lists v4's six values plus v5's `'type'` in order
  with `'model'` appended; no index or FK references `make` or `model`, so the
  two `DROP COLUMN`s are clean; the CHECK with two owners holds on every v6 row.
  `test_migration_v9`'s delete-and-rerun on the already-migrated test DB is
  sound (all no-ops; equipment rows there already carry `model_id`).
- **Permissions under S011.** `equipment:edit` via `require_perm` (held anywhere)
  for manufacturer, model and model-document writes matches classes and types;
  `equipment:read` anywhere for model documents is the A.8.3 departure confirmed
  at S009 gate A; `equipment:purge_documents` anywhere for restore/purge is S009
  A1's rule, with its consequence stated in § 5.5. No new keys, so `test_rbac.py`
  and `navigation.test.js` stand. The node's own documents keep S011's keyed
  checks (`load_node_for_user(…, key)`, `_lock_node_for_change(…, key)`), which
  the S009 patch's `Owner` dataclass lacks — § 3 says so.
- **Reuse of the S009 patch.** `OWNERS`, the stacked route decorators,
  `file_store.owner_folder/file_path/write_file`, the `inherited` groups with
  `path`, the `DocumentsCards` move with `basePath`, the in-panel Masters view all
  carry over with `class`/`type` → `model`; the removed list, restore and purge by
  owner are new code (§ 3, BR2-03). `app.py` moves `documents_bp` to `/api`
  (line 147 today) and node URLs don't change.
- **Composite FKs.** `(model_id, class_id)` on `equipment` and `(type_id,
  class_id)` on `equipment_models` are safe because the model's class and type
  are immutable (§ 5.2); a model change writes `model_id`, `class_id` and
  `type_id` in one UPDATE from the same model row, so both of `equipment`'s
  composite FKs see consistent values.
- **Events.** `_TRACKED` gains `("model_label", "model")`; "Atlas Copco GA37" is
  at most 100 + 1 + 80 = 181 characters, inside `VARCHAR(200)`.
- **`conftest._TABLES` order** given in § 3 is right (`equipment_documents`
  already comes first; with `FOREIGN_KEY_CHECKS = 0` it is tidiness).
- **Track and manual checks.** Full is right: a migration that drops columns and
  adds a `NOT NULL` one, access-checked routes, locking. The three UI flows and
  the production step are **important** (BR3-06 only tightens the production
  step's wording); the phone note is plain.
- **Plan.MD.** Plan § 4.1 still lists `make, model` as fields and its documents
  note says in-house presses keep their drawings on the equipment; § 2's EN 13460
  bullet moves design drawings of in-house models onto the in-house model. Both
  are listed in § 3 Docs for the planner to update at approval, so this is a
  planned, visible change rather than a contradiction. Plan § 2 (bill of
  materials per model, makers' parts lists as model documents, "S012") already
  points at this step.
- **Out of scope** matches Plan § 2 and § 4.1 (design data, AMC contacts, spares)
  and keeps the step one reviewable slice.
