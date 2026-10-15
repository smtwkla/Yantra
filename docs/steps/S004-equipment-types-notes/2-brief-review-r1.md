```
Step: S004 — Equipment types and notes
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S004 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01). No blocker.** The brief is
well shaped and sits cleanly on S002/S003 as committed (6d58ce5); the type rules
need one hole closed before a coder can follow them, and the migration needs its
statements pinned down.

Reviewed against: the brief; `backend/equipment.py`, `equipment_core.py`,
`masters.py`, `masters_core.py`, `local_db.py` (v1–v4), `db_helpers.py`,
`api_common.py`, `config_rbac.py`, `tests/conftest.py`, `test_equipment_api.py`,
`test_equipment_core.py`, `test_masters_core.py`; `frontend/src` (the form modal,
list, detail, labels, masters store, `useFormModal`, `useMasterForm`,
`ActiveToggle`, the masters panels); the S002 and S003 briefs and impl reports;
`Plan.MD`, `Maintenance-Philosophy.md`, `Plant-Facts.md`; `SMTW-WebApp-Base.md`
§ DB Connection, § Local DB Migration, § API Response Conventions. The dev DB is
`mariadb:11.4` (`tooling/dev/docker-compose.dev.yml`).

---

## Findings

### BR1-01 — major — The class-change rule leaves a path where the composite FK, not the shell, refuses the write (→ 500)

**Problem.** § 5.3 says the type row is locked "only when `type_id` is sent with
a value and differs from the stored one", and § 5.2 says a PUT that changes
`class_id` while the node has a type "must also send `type_id`". Put together,
these leave one combination undecided and one wrong:

1. **The client sends the current `type_id` back together with a new `class_id`.**
   The type is "sent" (so the § 5.2 400 doesn't fire) but doesn't "differ" (so
   no lock, no class check). The UPDATE then sets `class_id` while `type_id`
   points at a type of the old class, the composite FK `fk_equipment_type`
   refuses it with MariaDB error 1452, `api_common._integrity_error` re-raises
   anything that isn't 1062, and the user gets a **500**. The brief's § 4 claim
   "the shell still validates first, so this is a backstop" is not true on this
   path. It is also the path the S003 update code invites: `update_equipment`
   drops `parent_id`/`unit_id`/`class_id` when they equal the locked row, and a
   coder will naturally add `type_id` to that tuple — after which "sent but
   unchanged" and "not sent" are indistinguishable to the rest of the function.
2. **"The node has a type" is a decision, and must come from the locking read**
   (S002 BR3-01). `_LOCK_EQUIPMENT` today selects
   `id, level, status, parent_id, unit_id, class_id`; the brief doesn't say it
   gains `type_id`. Without that, the "has a type" and "differs from stored"
   decisions would be taken from the plain fragment read, i.e. from the
   snapshot, which is exactly what BR3-01 forbids.

**Why it matters.** A 500 on a legal API request is the kind of defect S002
spent three rounds removing; and the rule is the one piece of S004 a coder cannot
infer from the existing code.

**Options.**

- (a) **Recommended — state the rule as an algorithm on the locked row, with the
  type lock taken whenever the type must be checked, not only when it changes:**

  ```
  locked = _LOCK_EQUIPMENT row, now also selecting type_id
  clean  = validated body; drop parent_id/unit_id/class_id/type_id when equal to locked
  sent_type = "type_id" in body as sent (before the drop)
  class_changes = "class_id" in clean
  new_class = clean.get("class_id", locked["class_id"])
  resulting_type = clean.get("type_id", locked["type_id"])

  if class_changes and locked["type_id"] is not None and not sent_type:
      400 type_id "Pick a type of the new class, or none"
  if resulting_type is not None and (("type_id" in clean) or class_changes):
      t = _lock_type(resulting_type)                 # (5) in the lock order
      if t is None: 400 type_id "Unknown type"
      if t["class_id"] != new_class: 400 type_id "This type belongs to another class"
      if "type_id" in clean and not t["active"]: 409 type_id "The type is inactive"
  ```

  This covers: type unchanged and class unchanged (no lock); type changed (lock,
  active + class); class changed with `type_id: null` (no lock, `type` event
  `X → none`); class changed with a type of the new class (lock, class check);
  class changed with the old type sent back (lock, "belongs to another class");
  class changed with nothing sent (400 "Pick…"). The FK can then never fire on a
  normal path, and every decision is from a locking read. Keeping a deactivated
  type is still allowed (no `type_id` in `clean` → no active check).
- (b) Treat "same `type_id` sent back with a new class" as the § 5.2 400 ("Pick a
  type of the new class, or none"). Simpler message, but it still needs the
  `_LOCK_EQUIPMENT` change and the "sent vs dropped" bookkeeping, so it saves
  nothing.
- (c) Clear the type automatically on a class change. Rejected by the brief's own
  § 7 decision (no silent side effect); agree.

Also fold in: on **create**, the class is `clean["class_id"]` and the type lock
is taken whenever `type_id` is present and not null (exists 400, class 400,
active 409) — the brief's create text already implies this; say it.

---

### BR1-02 — minor — Migration v5: pin the statements, and make them safe to re-run

**Problem.** § 3 lists v5 in prose. Four things a coder would otherwise decide,
two of which can leave a database half-migrated:

1. **Re-run safety.** `init_db` runs the statements one by one on an autocommit
   connection and writes `db_version` only after the last one. MariaDB DDL is not
   transactional, so if statement 3 fails, statements 1–2 stay applied. On the
   next `ensure_schema()` retry (every 30 s), `CREATE TABLE equipment_types`
   fails with 1050 and `ADD COLUMN type_id` with 1060 — **forever**, and the app
   stays at 503 until someone edits the schema by hand. The base pattern
   (§ Local DB Migration) says to use `IF NOT EXISTS` for this reason; v1–v4's
   `CREATE TABLE`s do, v3's `ALTER` doesn't. MariaDB 11.4 supports all three
   forms needed:
   - `CREATE TABLE IF NOT EXISTS equipment_types (…)`;
   - `ALTER TABLE equipment ADD COLUMN IF NOT EXISTS type_id INT NULL AFTER class_id`,
     and the same for `notes`;
   - `ALTER TABLE equipment ADD CONSTRAINT fk_equipment_type FOREIGN KEY IF NOT EXISTS (type_id, class_id) REFERENCES equipment_types (id, class_id)`.
2. **The ENUM change.** `MODIFY` replaces the whole column definition: the
   statement must restate `NOT NULL`, keep the six existing values **in their
   present order** and append `'type'` at the end. Appending at the end is a
   metadata-only change in MariaDB (no table rebuild, old rows untouched);
   reordering or dropping a value would rewrite the table. `MODIFY` is
   idempotent by nature, so it needs no guard.
3. **FK prerequisites, stated so the coder doesn't discover them.** InnoDB needs
   an index whose leftmost columns are the referenced ones — that is what
   `uq_equipment_types_id_class (id, class_id)` is for, so it must be in the
   `CREATE TABLE`, which runs before the `ADD CONSTRAINT`. On the referencing
   side InnoDB creates an index on `(type_id, class_id)` itself. Existing rows
   pass because `type_id` is NULL and a composite FK is not checked when any of
   its columns is NULL (MATCH SIMPLE). Column types must match exactly (`INT`
   both sides — `equipment_classes.id` and `equipment_types.id` are `INT`).
4. The § 8 migration test ("v5 applies to a database at v4 holding equipment and
   events") is not something the suite can run: `conftest` brings the test DB to
   the latest version once per session and never holds it at v4. Either state
   it as a **manual check** on the dev DB (which is at v4 now and will carry
   S002/S003 rows), or drop it.

**Options.** (a) Recommended: write the five statements out in § 4 (the brief
already gives the table; add the `ALTER`s verbatim), with `IF NOT EXISTS` on the
create, the two columns and the FK, and `NOT NULL` restated on the ENUM. (b)
Leave the form to the coder — then at least state "every v5 statement must be
safe to run twice" and "restate NOT NULL".

---

### BR1-03 — minor — Existing tests and fixtures the change breaks are not named

- `test_equipment_api.py::TestListing::test_row_fields` asserts the **exact**
  key set of a list row; it fails as soon as `type_id`/`type_name` are added.
  Update it to the new set (and keep it exact — it is what guards "the list has
  no `notes`").
- `conftest.py::_TABLES` (the per-session truncate) must gain `equipment_types`,
  between `equipment` and `equipment_classes`. Not fatal (checks are off during
  the truncate), but otherwise types from earlier sessions pile up as orphans.
- The S002 docstring at the top of `equipment.py` lists the lock order (1)–(5)
  and the `masters.py` interaction; both sentences change (type between class
  and counter; masters now also locks `equipment_types` rows and, on type
  create, the class row — see BR1-05). Name it as a required edit.

Nothing else pins shapes: `test_detail_has_ancestors_children_and_paths` checks
ancestor keys only; the vitest "unknown event" case uses `mystery`, so adding
`type` to `describeEvent` is safe.

---

### BR1-04 — minor — `useFormModal` labels a record by its code; types have none

**Problem.** `useFormModal.openEdit` sets
`editingLabel = record.full_code ?? record.code`. `useMasterForm` passes that to
`ActiveToggle`, whose confirmation reads "Deactivate **{{ label }}**?". An
equipment type has neither field, so the new panel would show
"Deactivate **undefined**?". The brief says the panel follows the Units pattern
with `ActiveToggle`, so this is on its path.

**Options.** (a) Recommended: `useFormModal` takes an optional
`label(record)` parameter, default `(r) => r.full_code ?? r.code`, passed through
by `useMasterForm`; the types panel gives `(t) => t.name` (or
`${t.class_code} · ${t.name}`). The three existing panels don't change. (b) The
API returns a `label`-like field on type items — no; it is a display concern.

Also decide the edit form's handling of the fixed class: recommend the edit
dialog shows the class as plain text and **does not send `class_id`** (then no
`fieldError('class_id')` is needed on edit, and a stray 400 on it falls to the
top of the dialog, per S003 § 5.7); the create dialog has the class `<select>`
with its `invalid-feedback`.

---

### BR1-05 — minor — `validate_equipment_type(data, creating)` cannot do what § 8 asks of it; the masters locks are half-stated

1. § 8 (pure tests) says `class_id` is "rejected-if-changed on update, accepted
   if unchanged" by the validator — but a pure validator with signature
   `(data, creating)` has no stored value to compare with. Either give it a
   `stored` argument as `validate_equipment(…, stored)` has, or (recommended,
   simpler and the S001 pattern for `units.site_id`) let the validator accept
   `class_id` as an id on update and have the **shell** compare it with the
   locked row: `clean.get("class_id", row["class_id"]) != row["class_id"]` →
   400 "Class cannot be changed". Move that test to the API tests.
2. § 5.3 says what the **PUT** locks but not the **POST**. "The class must be
   active (409)" is a decision, so on create the shell must lock the class row
   first (exactly `_lock_site_for_unit` in `masters.py`: missing → 400
   `class_id`, inactive → 409 `class_id`), then insert. That is class → type in
   the masters module too, the same order as `equipment.py`, so still no cycle —
   say so in § 5.3.
3. **Reactivation.** Units can't be reactivated under an inactive site. State
   the same for types (recommended: on `active: 1`, lock the class and require
   it active; § 9.5 "a class can't get new types while inactive" reads as
   intending this), or state that reactivation is free.
4. Register `uq_equipment_types_class_name` in `UNIQUE_KEY_ERRORS` with field
   `name` and a plain message — that is the mechanism behind the § 5.1 409.
   `uq_equipment_types_id_class` can never collide (`id` is the PK) and needs
   no entry. `GET /equipment-types?class_id=x` → 400 `class_id`, as
   `_site_filter` does.

---

### BR1-06 — minor — Type events compare names, so some changes leave no `type` event

**Problem.** `_TRACKED` gains `("type_name", "type")`, so `tracked_changes`
compares the **names**. Names are unique only within a class. Reclassifying
`RPP` / *Standard* to `HP` / *Standard* in one PUT (class changed, type changed to
the other class's *Standard*) writes a `class` event and **no `type` event**,
because the display value didn't change. Also, a type literally named "none" is
indistinguishable in history from "no type".

**Options.** (a) Recommended: accept the first (the `class` event is there, the
pair of names is identical, and this is the same compromise S002 made for
codes) and **state it** in § 5.2 so the code reviewer doesn't raise it; reject
the reserved word in the validator (`name.lower() == "none"` → 400) rather than
living with the ambiguity, since it costs one line. (b) Compare on `type_id`
and display the name: `tracked_changes` would need a separate compare key, a
small change to the core and its tests. Not worth it for this case.

---

### BR1-07 — minor — Frontend fit: a handful of concrete rules the coder would otherwise choose

Each is small; together they decide whether the dialogs behave as § 3 promises.

- **Type reset on class change must use `@change` on the `<select>`** (as the
  site select does `@change="form.unit_id = ''"`), not a `watch` on
  `form.class_id`: a watcher fires when `fromRecord` fills the form on
  `openEdit`, and would clear the node's current type the moment the edit
  dialog opens.
- **`toBody`** gains `type_id: "" → null` (the "— none —" option) and
  `notes: optionalText(form.notes)`; `fromRecord` gains `type_id: node.type_id ?? ""`
  and `notes: node.notes ?? ""`. S003 § 5.3's "Edit sends …" list is thereby
  extended with `type_id` and `notes` — record that in § 3 so the two briefs
  agree.
- **`ensureEquipmentTypes()`** is awaited in `EquipmentFormModal.open()` and in
  the list's `load()` `Promise.all`; the detail page doesn't need it
  (`type_name` is in the response).
- **List filter:** `listUrl()`'s key list gains `type_id`; `chooseClass` clears
  `type_id` the way `chooseSite` clears `unit_id`. Show inactive types in the
  filter marked "(inactive)", as classes are, because equipment can still carry
  them. A bookmarked `type_id` without `class_id` would apply silently while the
  control is hidden: show the Type select whenever a class is chosen **or**
  `type_id` is set.
- **Notes display:** `white-space: pre-line` collapses runs of spaces; notes
  may hold aligned text (ratings, a small table). Recommend `pre-wrap`.
- **Type options when the chosen class has no types:** the select shows only
  "— none —"; fine, but say it so nobody adds a "no types yet" state.

---

### BR1-08 — minor — Standards: three corrections, for the user's learning as much as for accuracy

- **ISO 14224 class and type — correct, and worth one more sentence.** In ISO
  14224:2016 Annex A each equipment class (pumps, compressors, electric motors,
  …) has a short list of *equipment types* — for pumps: centrifugal,
  reciprocating, rotary. The standard's point is that reliability figures are
  only comparable within a class/type pair. Yantra's per-class list follows
  that; *closed execution / open execution* is a plant-specific type under a
  plant-specific class, which the standard allows (its lists are "typical", not
  closed). Say that explicitly, as S001 did for codes.
- **"Equipment data sheets" is not the standard's term.** ISO 14224 calls the
  attributes per class (kW, rated pressure, speed) *equipment-specific data*
  (Annex A tables, e.g. "Equipment-specific data for pumps"), and the common
  fields *equipment data* (Table 5). Table 5 also has a free-text **remarks**
  item — that is where the standard puts what Yantra calls notes. Cite it: it
  shows notes are not a departure.
- **ISO 55001 clause numbers:** write "2014 numbering" as S001–S003 do (S002
  BR2-08); § 7.5 is "information requirements", which includes the quality
  attributes of asset information — a good citation for "structured where you
  want to count".
- **ISO 27001 — one sentence missing.** Notes are readable by every role with
  `equipment:read` at that unit (operators included). Say that nothing
  sensitive belongs there — no control-panel passwords, no AMC prices
  (Plant-Facts § 4 mentions AMC contracts) — which is ISO 27001:2022 **A.5.12
  (classification of information)** in plain words.

TPM, SMRP and EN 13306 have nothing specific to add here; not citing them is
right.

---

### BR1-09 — nit — Small backend points

- Reuse `optional_text_parser("Notes", NOTES_MAX)` from `masters_core` for
  `notes`: it already strips both ends, keeps inner line breaks and turns empty
  into `None`. Say so (DRY) rather than describing the behaviour afresh.
- `_LOCK_TYPE` selecting `name` is right: `_written_state` needs it for the
  event text, like unit and class codes today. Note that the **before** name
  comes from the snapshot (display only) — the same accepted residual S002
  CR1-01 recorded for site codes.
- Message texts to fix now, since S002 fixed its own at this stage: "Unknown
  type" (400), "The type is inactive" (409), "This type belongs to another
  class" (400), "Pick a type of the new class, or none" (400), "Class cannot be
  changed" (400), "A type with this name already exists in this class" (409).
- `type_id` on **create** with `null`: harmless (writes NULL), but for symmetry
  with `parent_id`/`unit_id` the create path may drop a `None` `type_id`
  rather than write it.

---

### BR1-10 — nit — Docs owed at approval

- **Plan § 2 "Not in v1: per-class custom fields"** will sit next to a per-class
  *types* master. Add a clause there (or in § 4.1) that a type is a pick-list
  value within a class, not a custom attribute, so the two don't read as a
  contradiction.
- Plan § 5 gains the `equipment_types` row; § 4.1 gains `type` and `notes` in
  the field list and the class/type rule (the brief already says this).
- Maintenance-Philosophy § 12 glossary gains "Equipment type".

---

## Checked and found consistent

- **Lock order.** node → target parent → unit → class → **type** → counter is a
  strict extension of S002's order; single-row `FOR UPDATE`; `_LOCK_TYPE`
  returns the decision columns (`class_id`, `active`) plus `name` for display.
  Masters never locks equipment; with BR1-05's note that type-create locks the
  class first, both modules take class before type, so no cycle spans them.
- **Composite FK as a backstop** mirrors S002's `CHECK`; MariaDB 11.4 enforces
  it; NULL `type_id` rows are not checked; a violation would be a logged 500 —
  true once BR1-01 is fixed.
- **Type's class is fixed; renaming always allowed; deactivation needs no
  in-use check** — all consistent with the composite FK and with S002's
  "existing equipment keeps a unit or class that is later deactivated".
- **Events:** `type` with name snapshots and `none`; no event for notes; one
  `created` event on create — consistent with S002 § 6 Events and with the
  user's decision on notes.
- **Search:** `q` on code, name, notes and `t.name` through the existing
  `_like_pattern`; a LEFT JOIN on `equipment_types` NULLs out for untyped rows;
  the COUNT and the page share `_NODE_FROM`, so totals stay right. Full-scan
  `LIKE` on 500 rows is within "right-sized".
- **API shapes:** list rows gain `type_id`/`type_name`, the detail also
  `notes`; `_summary` and `_detail` are the two places to touch.
- **RBAC:** reads `masters:read`, writes `equipment:edit`, the same as classes;
  no new keys, so `test_rbac.py`, `test_auth.py` and `navigation.test.js` are
  untouched.
- **Masters list conventions:** `{items, total}`, unpaginated, inactive hidden
  unless `include_inactive=1`, ordered — S001 § 6.
- **Collation claim:** tables are `utf8mb4` with the server default collation
  (`utf8mb4_general_ci` on MariaDB), so `uq_equipment_types_class_name` is
  case-insensitive as stated.
- **`resetMasters()`** clearing the new cache fits `useMasterForm`'s after-save;
  a renamed type then shows its new name in the equipment dialogs.
- **Scope:** no attributes per type, no bulk import, no reporting — in line
  with Plan § 2's deferrals and "nothing beyond the agreed scope".
- **Standards:** the ISO 14224 class/type account and the "structured for
  counting, free text for reading" line are right (BR1-08 only sharpens terms).
