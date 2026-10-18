```
Step: S012 — Equipment models
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S012 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 answer marked
`Accepted` is in the brief text, not only in the Review log (checked one by one,
list at the end). The four user decisions are not reopened. What is left is three
`minor` points where the brief still says two things or leaves a rule to the
coder, and two `nit`s.

Reviewed against: the brief as revised; `2-brief-review-r1.md`; `docs/steps/README.md`;
Plan.MD § 4.1 and § 5; Maintenance-Philosophy; Plant-Facts; `.claude/CLAUDE.md`,
`CLAUDE-COMMON.md`; SMTW-WebApp-Base § migrations; the S009 brief (§ 4, § 5, A1, A2)
and `s009-code.patch`; the **working tree** after S010/S011: `local_db.py` v1–v8,
`equipment.py`, `equipment_core.py`, `masters.py`, `masters_core.py`, `documents.py`,
`file_store.py`, `api_common.py`, `auth_utils.py`, `app.py`, `tests/conftest.py`,
`test_migration_v8.py`, `test_equipment_api.py`, `test_equipment_core.py`, `test_rbac.py`,
`test_modules.py`, `documents_helpers.py`; the frontend form, detail view and file
tree; `tooling/dev/seed_dev.py`.

Counts: minor 3 · nit 2.

---

## Findings

### BR2-01 (minor) — When the model row is locked: § 5.5 and § 5.3 rule 5 give two different sources for the unchanged model

**Problem.** § 5.5 says the model is locked "only when a resulting model exists".
§ 5.3 rule 5 says, for an unchanged model, "the stored model's type comes from the
join of `_NODE_COLUMNS`", and § 3 says the plain join is safe because a model's
class and type are immutable. The signature in § 5.3 says `model` is "the locked
model row". So on a PUT that only edits the notes of a machine with a model, the
coder must choose: lock the model row anyway (the § 5.5 reading, where the lock's
only purpose, "gives the type for rule 5", is already served by the join), or read
it from the join (the rule-5 reading) and not lock. Today the type follows the
second pattern: `_check_type_on_update` takes no type lock when the type is kept
and the class does not change ("keeping a type without a class change takes no
lock at all").

**Why it matters.** Not a deadlock risk — the order (4) class → (5) model → (6)
type holds either way, and I re-checked the pairs with `masters.py` and
`documents.py` below. But it is a rule the coder would settle alone, and the
over-locking reading makes every notes edit on a machine with a model wait behind
a designation edit or a model-document upload holding that row, for nothing.

**Options.**
1. **Recommended.** Lock the model only when it is **newly picked** (resulting
   `model_id` differs from the stored one), as the type is locked only when chosen
   or when the class changes. Then: rule 2 (unknown) and rule 7 (inactive) are
   decided from that locking read; rules 4 and 5 for an unchanged model are
   decided from the node's joined model columns (`class_id`, `type_id` — immutable,
   so the plain read is as good as a lock, which § 3 already argues). Write the
   `model` input as "the locked model row when newly picked, else the node's joined
   model columns `{id, class_id, type_id, active}`", and note that `LOCK_EQUIPMENT`
   gains `model_id` (it is the `stored` input).
2. Keep "lock whenever a resulting model exists" and delete the rule-5
   parenthetical. Works, costs the needless wait. Not recommended.

### BR2-02 (minor) — Rule 4's message needs class codes that `check_model`'s inputs don't carry

**Problem.** § 5.3 rule 4 refuses with "This model is a <class code>; pick a model
of <class code> or none". The pure function gets `model = {id, class_id, type_id,
active}` and `stored = {class_id, type_id, model_id}`: ids, no codes. The model's
class code is not in any read the shell makes (the locking read is single-table by
the module rule); the equipment's resulting class code is in `equipment_class["code"]`
only when the class is locked (a class change), else in `node["class_code"]`. The
coder has to either widen the inputs or add a read, and the brief says neither.

**Options.**
1. **Recommended.** Use a plain message without codes — "This model belongs to
   another class" — the shape of S004's "This type belongs to another class" (the
   form never offers a model of another class, so this message is for an old tab or
   an API client, and the field `model_id` says where). § 8's tests are unchanged.
2. Keep the codes: add `class_code` to the `model` input (a plain read of
   `equipment_classes` by the model's `class_id`, allowed for display values) and
   pass the equipment's class code in. More plumbing for a message nobody should see.

### BR2-03 (minor) — § 3 "Where" misses three things the working tree makes necessary, and one claim about the S009 patch misleads

**Problem.**
1. **`backend/app.py`** is not listed. `documents_bp` is registered at
   `url_prefix="/api/equipment"` (app.py line 147). The model document routes of
   § 6 live under `/api/masters/equipment-models/<id>/documents`, which that prefix
   cannot serve. The S009 patch's first hunk moves the blueprint to
   `url_prefix="/api"` and gives every route its full path (`/equipment/<id>/documents`,
   `/equipment/removed-documents`, `/masters/…`), so the node and removed-list URLs
   stay what the frontend and the S006/S008 tests use. Say so, and list `app.py`.
2. **`test_equipment_api.py::TestList::test_row_fields`** asserts the list row's key
   set *exactly* (line 637: "Exact, so it also guards that the list has no notes").
   § 3 adds `model_id`, `model_designation`, `manufacturer_name` and `model_label`
   to the list row, so this case breaks too; BR1-07 named only the events case.
   Name it (the new exact set), so "existing tests keep their behaviour" is read
   correctly.
3. **`backend/tests/documents_helpers.py`** (`docs_url`, `folder_files` take a node
   today) is changed by the patch to take an owner; it belongs in the test list.
4. **S009 A1 is a design, not code.** § 3 says the removed list reuses "S009's
   design … and its A1 for the removed list, and its code in … `s009-code.patch`".
   The patch's removed list is node-only — its docstring and `_REMOVED_FROM` comment
   still say "class and type documents not yet (S009 § 10.3)"; A1 was dropped
   before it was coded. The `UNION ALL`, the item builder and restore/purge by owner
   are **new code** written from A1's text (§ 5.6 is complete enough for it). One
   sentence saves the coder a search.

**Why it matters.** Each is a file the coder would otherwise discover while
coding, which CLAUDE-COMMON says should not happen; the `test_row_fields` one is a
red test the brief says won't be there.

**Options.** Add the four to § 3 (recommended; nothing to choose).

### BR2-04 (nit) — Small gaps

- **`model_id` parsing.** State that `validate_equipment` adds `model_id` as
  `_id_parser("Model", nullable=True)`; on create a `null` is dropped like
  `type_id` (the "absent keys are not written" filter, `equipment_core.py` line 264,
  gains `model_id`); on update `null` is kept and clears the model (rule 3 then
  applies: the type stays, the form unlocks it). The update's "sending back the
  current value is not a change" loop (`equipment.py` line 505) gains `model_id`,
  and `sent` for `check_model` is captured **before** that loop, as `sent_type` is.
  Also say that `type_id: null` with a model that carries a type is "different"
  under rule 5 (→ 400), since the new form sends the locked type.
- **`<now>` in § 4.3 is not SQL** ("SQL only" is the migration's rule). Migration
  v8's `people` insert omits `created_at` and takes the column default
  (`CURRENT_TIMESTAMP`, IST by the session setting); say "omit `created_at`" or
  write `NOW()`.
- **Model create with an inactive type:** § 5.2 says the type "must be an active
  type of that class (else 400 'This type belongs to another class')" — the status
  for *inactive* is not stated. Say 409 "The type is inactive", as `_lock_type`.
- **Models list order:** unstated; `ORDER BY m.name, em.designation` is the
  natural one (types are `c.code, t.name`).
- **The form's current inactive model** (§ 1.4) needs the store to fetch with
  `include_inactive=1` (or a one-off read), as types do; one line.

### BR2-05 (nit) — The "model" event's value when the model row was committed after the transaction's snapshot

`_written_state` patches `class_code` and `type_name` from the locking reads
because the plain re-read may miss a class or type committed after this
transaction's snapshot (its LEFT JOIN then shows none). The same hole exists for
`model_label`: a model created by one user and picked by another within the same
window gives a "model" event with `"none"` as the new value. The locked model row
(single-table) carries the designation but not the manufacturer name. Either pass
the label through `_written_state` (designation from the locked row; the
manufacturer name by a plain read of `manufacturers` by `manufacturer_id` — a
display value, which the module rule allows), or state the edge is accepted. The
first is a few lines; recommended.

---

## Checked and found consistent

- **Round-1 answers are in the text.** BR1-01: § 5.3 signature, rule order, § 5.5
  orders for both modules, rule 8's "not newly chosen". BR1-02: the ENUM statement in
  § 4.2. BR1-03: § 4.3 SQL with `ORDER BY e.id`, `N()`, scrapped and inactive-class
  notes, the v8-style harness in § 8, `conftest._TABLES` in § 3. BR1-04: composite
  FKs in § 4.1/§ 4.2 and the bypassed-shell tests in § 8. BR1-05: 80, `"none"`, the
  "type" event too. BR1-06: rules 2, 7, 8, "Levels", `_NODE_COLUMNS` join. BR1-07:
  the named cases, the seed in § 1.10/§ 3, "stays unsearched", `legacy_*` detail only,
  `null` refused. BR1-08: § 8's production check (important) and the phone note
  (plain). BR1-09: ISO 55001:2014 § 7.6/7.6.3, ISO 14224 softened, A.5.12. BR1-10:
  folder, `q`/`code`/`name`, inactive current model, navigation claim gone, docstrings,
  `UNIQUE_KEY_ERRORS`, renamed detail keys.
- **Migration v9 against MariaDB 11.4 and the working tree.**
  - The events ENUM lists exactly v4's six values plus v5's `'type'`, in order,
    with `'model'` appended: `ENUM('created','moved_unit','moved_parent','status',
    'criticality','class','type','model')` — matches `local_db.py` lines 142 and 176.
  - `uq_equipment_types_id_class UNIQUE (id, class_id)` exists (v5 line 167), so
    `fk_equipment_models_type (type_id, class_id)` has its referenced index;
    `fk_equipment_type` on `equipment` (v5 line 172) is the precedent, and
    `uq_equipment_models_id_class` is the referenced index for `fk_equipment_model`.
    InnoDB auto-creates the child indexes the CREATE TABLE FKs need, as v5 did.
  - Index before FK on `equipment` and `equipment_documents`, `ADD COLUMN IF NOT
    EXISTS`, `ADD INDEX IF NOT EXISTS`, `FOREIGN KEY IF NOT EXISTS` (the v5 form) and
    `ADD CONSTRAINT IF NOT EXISTS … CHECK` (the S009 patch's v7 form, line 569) are
    each safe to run twice; `MODIFY` twice is a no-op; the 1832 fallback is carried
    from S009 § 4. Fresh tables and `CREATE TABLE IF NOT EXISTS` idempotent.
  - `MATCH SIMPLE`: a NULL `model_id` skips the composite FK, so every existing row
    passes; the CHECK holds on existing data (every v6 row has `equipment_id`).
  - § 4.3: `INSERT IGNORE … SELECT … ORDER BY e.id` with no `DISTINCT` inserts
    row by row, so the lowest-id spelling wins and later case/space variants hit the
    unique key and are skipped — deterministic. `REGEXP_REPLACE(TRIM(x),
    '[[:space:]]+', ' ')` is valid PCRE on 11.4; in the joins it sits on the
    `equipment` side, so `m.name = N(e.make)` can still use `uq_manufacturers_name`,
    and the tables are small anyway. `GROUP BY N(make), N(model) HAVING
    COUNT(DISTINCT class_id) = 1` is fine under `ONLY_FULL_GROUP_BY`. Step 3's join
    includes `em.class_id = e.class_id`, so the composite FK is satisfied; `WHERE
    e.model_id IS NULL` makes it re-runnable; a model text over 80 has no model row
    and so is never linked. `equipment` has no `ON UPDATE` column (v4 line 128), as
    the brief asks the coder to confirm. `CHAR_LENGTH(N(e.model)) <= 80` keeps
    strict mode quiet; make ≤ 100 fits `name`.
- **`check_model` vs `_check_type_on_update`.** Rule 4 (class mismatch) runs before
  S004's "Pick a type of the new class, or none" (line 329), so a class change that
  keeps the model is refused on `model_id`, and a class change with the model cleared
  and no type sent still gets S004's refusal — the right outcome. A type set by the
  model passes `_lock_type(…, newly_chosen=False)` (class checked, active not), which
  is exactly rule 8. `sent` as "what the request had" matches how `sent_type` is
  captured before unchanged fields are dropped.
- **Lock order, pairwise.** `equipment.py` node → parent → unit → class → model →
  type → counter; `masters.py` model create manufacturer → class → type → insert
  (the insert's FK checks take S-locks on rows it already holds X), reactivate
  manufacturer → class → model (plain read of the immutable manufacturer/class ids
  first, the `update_equipment_type` pattern), designation edit / deactivate the
  model row alone, manufacturer deactivate the manufacturer row then a plain count
  (a concurrent model create or reactivate locks the manufacturer first, so it
  waits); `documents.py` the model row alone then `equipment_documents`. Every
  path that takes both class and model takes the class first; nothing holds a type
  while waiting for a model; `equipment.py` never locks manufacturers and
  `masters.py` never locks equipment. No cycle.
- **Frontend claims.** The form always sends both `make` and `model`
  (`EquipmentFormModal.vue` line 50, `optionalText` → `null`), so refusing `null` is
  needed; the detail reads `node.make`/`node.model` (lines 129–130), so the rename
  must be done in the view — both stated in § 5.4. The patch moves the cards to
  `components/documents/DocumentsCards.vue` with a `basePath`, as § 3 says.
- **Permissions.** `require_perm` = held somewhere (`has_perm`), so `equipment:edit`
  "at any site" for manufacturer/model writes is the class/type pattern;
  `user_unit_ids("equipment:purge_documents")` is what the removed list keys on
  today. No new keys: `test_rbac.py` tests the matrix, not routes; `test_modules.py`
  tests version and DB status only. The stated consequence (a manager at one site
  may purge a model document used elsewhere) is in § 5.5.
- **Test harness.** `test_migration_v8.py` deletes the version row and calls
  `init_db` twice; § 8 copies that. `_TABLES` order given in § 3 is right (with
  `FOREIGN_KEY_CHECKS = 0` it is tidiness, not necessity).
- **Standards.** ISO 14224 lists the manufacturer's name and model designation as
  equipment-unit data (the pooling argument is the standard's own reason); EN 13460
  separates documents delivered with the product from those made in use; ISO
  55001:2014 § 7.6 / § 7.6.3 (documented information and its control) is the 2014
  numbering, used consistently; ISO 27001:2022 A.8.3 (access restriction) and A.5.12
  (classification) are the right controls for "visible at every site" and the
  upload-dialog line; ISO 8000 for one record, one spelling. Each is explained in
  plain terms in § 2.
- **Plan.MD.** § 4.1's "make, model" fields and § 5's table are to be updated at
  approval (§ 3 Docs); § 4.1's documents line already says manufacturer
  documentation belongs on a model master. No decision contradicted.
- **Track and manual checks.** Full is right (migration with data conversion,
  access-checked routes, locking). The production step is **important**; the phone
  note is plain; the three UI flows are important and are flows only a person can
  judge.
