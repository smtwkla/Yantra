```
Step: S004 — Equipment types and notes
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 15-10-2026
```

# S004 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 finding
marked `Accepted` is in the brief text, not only in the Review log. The PUT
algorithm of § 5.2 closes BR1-01 in every case I could construct, and the
migration of § 4.1 is valid MariaDB 11.4 syntax, re-runnable statement by
statement. What remains is three `minor` points the revisions introduced (a
validator field set that would make Deactivate a silent no-op, a helper whose
error field the brief states two ways, and the S003 rule that every sent field
renders its error) and a few nits.

Reviewed against: the brief (revised 15-10-2026); round 1; the committed code at
6d58ce5 — `backend/equipment.py`, `equipment_core.py`, `masters.py`,
`masters_core.py`, `local_db.py` (v1–v4), `db_helpers.py`, `api_common.py`,
`config_rbac.py`, `tests/conftest.py`, `test_equipment_api.py`,
`test_equipment_core.py`, `test_masters_api.py`, `test_masters_core.py`;
`frontend/src` (`EquipmentFormModal.vue`, `EquipmentView.vue`,
`EquipmentDetailView.vue`, `EquipmentHistory.vue`, `stores/masters.js`,
`composables/useFormModal.js`, `views/masters/useMasterForm.js`, `UnitsPanel.vue`,
`EquipmentClassesPanel.vue`, `MastersView.vue`, `components/ActiveToggle.vue`,
`utils/equipmentLabels.js`, `tests/equipmentLabels.test.js`); the S002 and S003
briefs; `Plan.MD`, `Maintenance-Philosophy.md`, `Plant-Facts.md`;
`SMTW-WebApp-Base.md` § Local DB Migration Pattern. The dev DB is `mariadb:11.4`
(`tooling/dev/docker-compose.dev.yml`).

---

## Round-1 findings: are they in the brief text?

| Finding | Where it now lives | Verified |
|---|---|---|
| BR1-01 class-change path to a 500 | § 5.2 algorithm and case table; § 3 `_LOCK_EQUIPMENT` gains `type_id`; create rule in § 5.2; § 8 "old type sent back → 400 (not a 500)" | Yes — see the case walk below |
| BR1-02 migration pinned, re-runnable | § 4.1 five statements verbatim with `IF NOT EXISTS` on the create, both columns and the FK; `NOT NULL` restated on the ENUM; § 8 migration check is manual | Yes — see the migration walk below |
| BR1-03 breaking tests named | § 3 Backend tests: `test_row_fields` (exact key set, gains `type_id`/`type_name`), `conftest._TABLES`, `equipment.py` docstring | Yes |
| BR1-04 `useFormModal` label; edit form and `class_id` | § 3 Frontend: optional `label(record)`, default `(r) => r.full_code ?? r.code`, passed through by `useMasterForm`; the types edit form shows the class as text and does not send `class_id` | Yes |
| BR1-05 validator vs shell; masters locks; reactivation; unique key | § 3 (`validate_equipment_type` parses, the shell compares); § 5.1 (POST locks the class first; reactivation needs an active class; `class_id` filter 400); § 5.3 masters class → type; § 3 `UNIQUE_KEY_ERRORS` entry | Yes, with BR2-01/BR2-02 below on two details |
| BR1-06 events compare names; `none` reserved | § 5.2 "Events compare type names" with the same-name miss stated and accepted; § 5.1 and § 3 reject the name `none` | Yes |
| BR1-07 frontend specifics | § 3 Frontend: `@change` reset (not a watch), `toBody`/`fromRecord`, `ensureEquipmentTypes()` in `open()` and the list's `Promise.all`, `listUrl()` keys, Type filter shown when a class is chosen or `type_id` is in the URL, "(inactive)", `pre-wrap`, no empty state for a class without types | Yes |
| BR1-08 standards | § 2: Annex A types per class; plant-specific types allowed; ISO 55001 "2014 numbering"; § 7.5 information requirements; ISO 27001:2022 A.5.12 with the help text in § 3; § 1 "equipment-specific data"; Table 5 remarks | Yes (one clause number, BR2-06) |
| BR1-09 backend nits | § 3 `optional_text_parser("Notes", NOTES_MAX)`; § 5.2 message texts; before-name from the snapshot; `type_id: null` dropped on create | Yes |
| BR1-10 docs at approval | § 3 Docs: Plan § 2, § 4.1, § 5; Philosophy § 12 | Yes |

---

## Findings

### BR2-01 — minor — `validate_equipment_type` as described in § 3 has no `active` field, so Deactivate/Reactivate would be a silent no-op

**Problem.** § 3 says the validator "parses `class_id` as an id and `name`".
§ 6.1 says `PUT /equipment-types/<id>` takes `{name?, active?}`, and § 5.1's
reactivation rule and the panel's `ActiveToggle` depend on `active` reaching
the shell. A validator built from § 3 drops `active` as an unknown field; the
PUT `{active: false}` from `useMasterForm.changeActive` then reaches
`update_row` with an empty `clean`, which returns without writing, and the API
answers 200 with the record unchanged. The § 8 deactivate/reactivate tests would
catch it, but the brief should not make the coder find it that way.

**Why it matters.** The three existing masters validators all carry `active`
through `_parse_active`; the types one must too, or the reactivation locking
logic of § 5.3 is never reached.

**Options.** (a) Recommended: state the field table in § 3 as
`_TYPE_FIELDS = {class_id: (_parse_id("Class"), required on create), name: (parse_name + the "none" rule), active: (_parse_active, optional)}`
in the shape of `_CLASS_FIELDS`. (b) Leave `active` to the coder "by pattern" —
no, § 3 reads as exhaustive.

---

### BR2-02 — minor — `_lock_class_for_type` is given two different error fields; make it take the field

**Problem.** § 3 and § 5.1 define `_lock_class_for_type` "in the shape of
`_lock_site_for_unit`": missing → 400, inactive → 409, **both field `class_id`**.
§ 5.1 then says reactivating a type under an inactive class is 409 **field
`active`**, "The class is inactive", and § 5.3 says reactivation uses the same
helper. `_lock_site_for_unit` has a fixed field (`site_id`) and a fixed message,
so one helper cannot give both answers without a parameter; the coder would have
to choose. (The S001 precedent is actually the other way: reactivating a unit
under an inactive site answers field `site_id`, and
`test_unit_cannot_be_reactivated_under_an_inactive_site` checks the status only.)

Two smaller points on the same path:
- The plain read of the type's `class_id` before the class lock must give the
  **404** for an unknown type; say so, since `_lock_row` (which normally gives
  the 404) now runs after the class lock.
- A PUT that both reactivates and sends `class_id`: the class to lock is the
  **stored** one from the plain read; the sent value is compared afterwards
  against the locked type row (400 "Class cannot be changed" if different).
  Worth one sentence so the two checks are not reordered.

**Options.** (a) Recommended: `_lock_class_for_type(cur, class_id, field)`,
called with `"class_id"` on create and `"active"` on reactivation, messages
"Unknown class" / "The class is inactive"; the 404 from the plain read stated.
(b) Keep field `class_id` for both, as S001 does for units — simpler, and the
edit dialog shows either at the top (neither `class_id` nor `active` is in the
edit form), so the user sees the same thing. Either is fine; the brief must
pick one and the helper must match.

---

### BR2-03 — minor — The equipment dialog must render `fieldError("type_id")` and `fieldError("notes")`

**Problem.** `useFormModal.modalError` shows a refusal at the top of the dialog
**only when its field is not in the form**. Once `type_id` and `notes` are in
`form` (§ 3 `fromRecord`/`blank`), a 400/409 on either is shown nowhere unless
the template renders `fieldError` for it. This is S003 § 5.7's rule, written
after S003 BR2-03 for exactly this reason. The brief describes the Type select
and the Notes textarea but does not say they carry their `invalid-feedback`.

One of these refusals is reachable from the dialog: the edit dialog lists a
type that is active when it opens; if someone deactivates it meanwhile and the
user picks it, the save answers 409 `type_id` "The type is inactive" — and the
dialog would just sit there. "Pick a type of the new class, or none" is not
reachable (the dialog resets the type on a class change), and `notes` over
2000 is stopped by `maxlength`, but the rule is per field, not per path.

**Options.** (a) Recommended: say in § 3 that the Type select and the Notes
textarea get `:class="{ 'is-invalid': fieldError(...) }"` and an
`invalid-feedback`, like the other fields of `EquipmentFormModal.vue`. (b)
Rely on the S003 rule being read — the coder reads S003 § 4–5 as background,
so this is a one-line insurance.

---

### BR2-04 — nit — Four small backend placements

- **`UNIQUE_KEY_ERRORS` entry.** § 3 puts `uq_equipment_types_class_name` in
  `backend/api_common.py`. The pattern since S002 BR1-09 is that
  `api_common.UNIQUE_KEY_ERRORS` is an empty registry and **each module adds its
  own keys at import** (`masters.py` and `equipment.py` both do
  `UNIQUE_KEY_ERRORS.update({...})`; the `api_common` docstring says so). The
  entry belongs in `masters.py`'s `update(...)`, next to
  `uq_equipment_classes_code`.
- **`_site_filter`.** § 5.1 asks for the same 400 on a non-numeric `class_id`.
  Rather than a second copy, generalise to `_int_filter(name)` and call it with
  `"site_id"` and `"class_id"` (DRY; `test_bad_site_filter_is_400` keeps
  passing).
- **A `make_type` fixture** in `conftest.py` (`make_type(cls=None, **overrides)`
  through the real API, like `make_class`), since both `test_masters_api.py` and
  `test_equipment_api.py` need types. Not a decision, just a line in § 3.
- **Docstring numbering.** With the type at (5), the counter becomes (6) in
  `equipment.py`'s LOCK ORDER list and in the `# (5)` comment on `_next_code`.
  § 3 says the docstring is updated; the inline comment on `_next_code` is the
  one easy to miss.

---

### BR2-05 — nit — The list's Type filter: options when `type_id` is in the URL but no class is chosen

§ 3 shows the Type select "when a class is chosen **or** `type_id` is in the
URL" (good: a bookmarked type is never applied invisibly), and says it "lists
the class's types". With no class chosen there is no class to list, so the
options are undefined. Recommend: with a class chosen, that class's types;
without one, **all** types labelled `RPP · Closed execution` (the same label
as the masters panel), so the bookmarked value is visible and selectable. And
state whether `chooseClass` clears `type_id` always or only when the type is
of another class (`chooseSite` clears the unit only when it is outside the
site; the analogous rule is fine, but say which).

---

### BR2-06 — nit — ISO 14224 clause number for data quality

§ 2 cites "ISO 14224 § 7" for the warning that free text cannot be counted or
compared. In ISO 14224:2016 the clauses are: **6 Quality of data** (6.1
obtaining quality data, 6.2 data quality assurance), **7 Equipment boundary,
taxonomy and time definitions** (the class/type taxonomy the brief uses
elsewhere), 8 Equipment, failure and maintenance data (where Table 5, the
common equipment data with its free-text remarks, sits), 9 KPIs and
benchmarking. So the data-quality point is **clause 6**; clause 7 is the right
citation for the class/type hierarchy. For the user's learning: clause 6 is the
part of the standard that says collected data is only worth having if it is
*comparable* — the same thing recorded the same way everywhere — which is the
whole argument for the structured type over a note.

---

## Checked and found consistent

### The § 5.2 PUT algorithm, case by case (BR1-01)

Walked against the real `update_equipment` (the drop loop on line 454 gains
`type_id`; `sent_type` is `"type_id" in clean` taken **before** that loop,
which is the same as "in the body as sent" because the validator only puts the
key in `clean` when it was sent and valid). Lock (4) class is taken before lock
(5) type when both are needed, as today for class before counter.

| Case | Locks | Shell answer | Reaches the FK? |
|---|---|---|---|
| nothing about type or class | node | 200 | no change written |
| same `class_id` and same `type_id` sent back | node | 200 (both dropped) | no change written |
| new type, class unchanged | node, type | class checked against the **locked node's** class; inactive → 409 | type/class pair verified first |
| type of another class, class unchanged | node, type | 400 "belongs to another class" | refused before UPDATE |
| class changed, `type_id: null`, node typed | node, class | 200; `class` and `type` (X → none) events | UPDATE writes NULL `type_id` — FK not checked |
| class changed, `type_id: null`, node untyped | node, class | 200 (`type_id` dropped as equal to NULL) | FK not checked |
| class changed, type of the new class | node, class, type | class checked against the **new** class; inactive → 409 | pair verified first |
| class changed, **old** type sent back | node, class, type | `type_id` dropped as equal, but `class_changes` forces the lock → 400 "belongs to another class" | refused before UPDATE (the BR1-01 path, now closed) |
| class changed, another type of the old class | node, class, type | 400 "belongs to another class" | refused |
| class changed, nothing about type, node typed | node | 400 "Pick a type of the new class, or none" (from `locked["type_id"]`) | refused |
| class changed, nothing about type, node untyped | node, class | 200, `class` event only | FK not checked |
| other fields only, type deactivated since | node | 200 (no `type_id` in `clean` → no active check) | no change written |
| unknown `class_id` plus any type | node, class | 400 "Unknown class" first (lock 4 before 5) | refused |
| **create** with a type | parent/unit, class, type, counter | unknown 400 / other class 400 / inactive 409, after the class lock | pair verified first |
| **create** with `type_id: null` | as today | dropped like a NULL `parent_id` | column default NULL |

Every decision is from a locking read: the node's `type_id` and `class_id` from
`_LOCK_EQUIPMENT`; the type's existence, `class_id` and `active` from
`_LOCK_TYPE`. The type's `class_id` is immutable (400 in masters), and the node
row is locked, so neither side of the pair can move under the check. The FK is
therefore a backstop only, as § 4 claims — now true.

Also checked: `_written_state` takes `type_name` from the type lock when taken
(a type created after this transaction's snapshot would otherwise read as
`none` through the LEFT JOIN — the BR1-09 point, handled); the LEFT JOIN (not
JOIN) on `equipment_types` is right, so an untyped node is never a 409 re-read;
`tracked_changes` with `("type_name", "type")` and `_display` None → `none`
follows the `inherit` precedent; `old_value`/`new_value` `VARCHAR(200)` hold a
100-character name; the Move and Status dialogs send neither `class_id` nor
`type_id`, so they never meet the "Pick a type" 400; the edit dialog always
sends both and resets the type on `@change`, so the 400s are API-only as § 5.2
says.

### Locking, masters side (§ 5.3)

- Masters: POST locks the class only; PUT-reactivate reads the type's
  `class_id` plainly (safe: immutable), locks the class, then the type; other
  PUTs lock the type only. Equipment: node → parent → unit → class → type →
  counter. Both modules take class before type; masters never locks equipment;
  equipment never locks sites or `user_units`. No cycle spans the modules.
- The reverse order (type → class) in masters *would* deadlock against an
  equipment PUT holding the class lock while waiting for the type; the brief's
  plain-read-first construction avoids it correctly.
- A type deactivated while an equipment write waits for its lock is seen as
  inactive by that write (locking read); a rename while waiting lands in the
  event text through the lock, as for class codes (S002 CR1-01).
- The S001 counts in `masters.py` are unaffected: no new count depends on an
  equipment lock.

### Migration v5 (§ 4.1), statement by statement on MariaDB 11.4

1. `CREATE TABLE IF NOT EXISTS equipment_types (…)` — same audit columns as v2;
   `uq_equipment_types_class_name (class_id, name)` and
   `uq_equipment_types_id_class (id, class_id)` named; FK to
   `equipment_classes (id)` named. Re-run: skipped.
2. `ALTER TABLE equipment ADD COLUMN IF NOT EXISTS type_id INT NULL AFTER class_id`
   — supported since MariaDB 10.0.2; re-run gives a note, not an error.
3. `… ADD COLUMN IF NOT EXISTS notes TEXT NULL` — same.
4. `… ADD CONSTRAINT fk_equipment_type FOREIGN KEY IF NOT EXISTS (type_id, class_id) REFERENCES equipment_types (id, class_id)`
   — the grammar is `ADD [CONSTRAINT [symbol]] FOREIGN KEY [IF NOT EXISTS] [index_name] (cols) reference_definition`,
   so this form is valid. Prerequisites: the referenced side needs an index whose
   leftmost columns are `(id, class_id)` in that order — the PK on `id` alone
   does not qualify, `uq_equipment_types_id_class` does and is created in
   statement 1; the referencing side gets an index on `(type_id, class_id)`
   from InnoDB (the existing `class_id` index does not qualify, `type_id` is
   not its first column); both pairs are signed `INT`; existing rows pass
   because `type_id` is NULL and a composite FK with any NULL column is not
   checked (MATCH SIMPLE). Re-run: skipped by name.
5. `ALTER TABLE equipment_events MODIFY event ENUM(… six in order …,'type') NOT NULL`
   — restates `NOT NULL`, keeps the order, appends; appending at the end is
   `ALGORITHM=INSTANT` in MariaDB ≥ 10.3.7, so old rows are untouched. Re-run:
   idempotent.

Half-applied scenario: if any statement fails, the earlier ones stay applied
and `db_version` is not written; on the 30-second retry every earlier statement
is skipped or a no-op, so `ensure_schema()` can recover without hand edits —
the BR1-02 goal. `conftest._clean_tables` runs with `FOREIGN_KEY_CHECKS = 0`,
so the new FK does not change the truncate; `equipment_types` in `_TABLES`
keeps the test DB free of orphans.

### Data model and rules

- **Collation.** Tables are `utf8mb4` with the server default; on
  `mariadb:11.4` that is `utf8mb4_general_ci`, case-insensitive, so the
  § 4 claim holds and "Closed execution" / "closed execution" clash on
  `uq_equipment_types_class_name` → 409 via `_integrity_error` (the regex
  handles the `table.key` form).
- **Type's class fixed; rename free; deactivate free, no in-use check** —
  consistent with the composite FK and with S002's "existing equipment keeps a
  deactivated unit or class".
- **The `none` reservation** is checked on the trimmed, lower-cased name, so
  "None " is caught; "No type" is allowed.
- **Notes.** `optional_text_parser("Notes", 2000)` already strips both ends,
  keeps inner line breaks and turns empty into `None`; `TEXT NULL` in the DB
  with the 2000 limit in the shell; the textarea's `maxlength` 2000 counts
  UTF-16 units, which is never looser than Python's code points, so the dialog
  cannot produce a 400 on length. CRLF from a textarea arrives as LF through
  `v-model`.
- **Search.** `(e.code LIKE %s OR e.name LIKE %s OR e.notes LIKE %s OR t.name LIKE %s)`
  with four copies of the escaped pattern; the LEFT JOIN NULLs out for untyped
  rows and `NULL LIKE` is NULL, which is falsy inside the OR — correct. COUNT
  and page share `_NODE_FROM`. Full-scan `LIKE` on 500 rows is within
  "right-sized".
- **`type_id` list filter** joins the `_int_arg` loop as `("type_id", "e.type_id")`.
- **API shapes.** `_summary` gains `type_id`/`type_name`; `_detail`'s field
  loop gains `notes`; `test_row_fields` stays exact and so guards "no notes in
  the list". `_child_rows` and `_ancestors` are untouched.
- **Scrapped nodes** refuse any PUT before validation (line 447), types and
  notes included.
- **Events.** `created` only on create (as for class); `type` with name
  snapshots and `none`; no event for notes (user decision); the same-name miss
  across classes accepted and stated.

### Frontend

- `useFormModal`'s `label` parameter with the default `(r) => r.full_code ?? r.code`
  covers Sites (`code`), Units (`full_code`) and Classes (`code`) unchanged;
  `useMasterForm` destructures and passes it through.
- The types edit form `{name}` only: a 400 on `class_id` or a 409 on `active`
  has no field in the form and shows at the top — the S003 § 5.7 behaviour.
- `@change` on the class `<select>` (as the site select does for the unit) does
  not fire when `fromRecord` fills the form, so the edit dialog opens with the
  node's type intact.
- `ensureEquipmentTypes()` in `open()` and in the list's `Promise.all`;
  `resetMasters()` clears it, so a renamed type shows its new name in the next
  dialog; the detail page needs no cache (`type_name` is in the response).
- `describeEvent("type")` with `none` → "None" is safe against the existing
  vitest "unknown event" case (`mystery`); `navigation.test.js` is untouched
  (no new nav item; the Masters section is local state).
- The existing pure tests that assert `clean == {...}` exactly
  (`test_equipment_happy_path_defaults_criticality_c`, `test_part_happy_path_inherits`)
  still pass: `type_id` and `notes` are optional and absent from those bodies.

### RBAC and scope

- Reads `masters:read` (`*`), writes `equipment:edit` (engineer, IT admin;
  manager by inheritance; admin bypass) — the same keys as classes; no new
  keys, so `test_rbac.py` and `test_auth.py` are untouched; the masters
  `TestPermissions` read loop can simply gain `"equipment-types"`.
- Scope: no attributes per class/type, no bulk import, no reporting, no
  cross-class properties — in line with Plan § 2 and "nothing beyond the
  agreed scope".

### Standards

- **ISO 14224 class and type** (clause 7 and Annex A): a type is a subdivision
  of a class by construction (pump → centrifugal, reciprocating, rotary); a
  type always belongs to one class; the lists are typical, so *closed / open
  execution* under a plant-specific class is allowed. The brief's per-class
  design and the composite FK are the data-model form of that rule.
- **ISO 14224 Table 5 (common equipment data)** carries a free-text remarks
  item — notes are not a departure. **Clause 6 (quality of data)** is the
  argument for the type being structured (BR2-06 fixes the clause number).
- **ISO 55001:2014 § 7.5** (information requirements: asset information of
  defined quality) and **§ 8.2** (management of change: a reclassification is a
  recorded change) — cited correctly with "2014 numbering" as S001–S003 do.
- **ISO 27001:2022 A.5.12** (classification of information): notes are
  readable by every `equipment:read` holder at the unit; the help text on the
  field says what not to put there. Correct control, plainly stated.
- TPM, SMRP and EN 13306 have nothing specific to say about a type master or a
  notes field; not citing them is right.
