```
Step: S004 — Equipment types and notes
Doc: impl-report
Author: Coder (Opus)
Date: 15-10-2026
```

# S004 — Implementation report

Implements `1-brief.md` as approved 15-10-2026 by KLA (both review rounds and the
Gate A note). No amendments exist.

**Tests:** `tooling/run-tests.bat` — backend **551 passed**, frontend **24 passed**
(4 files). `npx vite build` in `frontend/` — clean, no warnings.

## 1. What was built

- **Equipment types, per class** (ISO 14224 class → type). A new master list,
  *Masters → Equipment types*: each type belongs to one class for good, can be
  renamed, deactivated and reactivated; nobody deletes. Written by
  `equipment:edit` (engineer, manager, IT admin, admin), read by every role.
- **One type per equipment node**, optional at every level, always of the node's
  own class. The database guarantees the match (composite FK); the API checks it
  first so the user gets a plain 400/409. A class change on a typed node needs a
  type decision (a type of the new class, or none): the type is never cleared
  silently.
- **Type changes in history** (`type` event, "Type: None → Closed execution");
  the name `none` is reserved for "no type".
- **Notes** on every node: free text up to 2000 characters, line breaks kept,
  not in history (the audit columns still record who changed them). Shown on the
  equipment page as written; edited in the equipment dialog with the help text
  "Visible to everyone who can see this equipment — no passwords or prices".
- **List:** a Type filter; the Class cell shows `RPP · Closed execution`; the
  search also matches notes and the type name.

## 2. How it works

### Data (migration v5, `backend/local_db.py`)

The five statements of brief § 4.1, verbatim apart from line wrapping:
`equipment_types` (with `uq_equipment_types_class_name` and the
`uq_equipment_types_id_class` index the composite FK needs), `equipment.type_id`
and `equipment.notes` (`ADD COLUMN IF NOT EXISTS`), `fk_equipment_type
(type_id, class_id) → equipment_types (id, class_id)` (`FOREIGN KEY IF NOT
EXISTS`), and the events ENUM with `type` appended. I ran the five statements a
second time by hand against the **test** DB after it had migrated: no error, the
schema unchanged. The dev DB (`vel_yantra_master`) was not touched; its v4 → v5
check is the user's (§ 5 below).

### Pure core

- `masters_core.validate_equipment_type(data, creating)` — `_TYPE_FIELDS`
  (`class_id`, `name`, `active`) through the shared `_validate`. The name parser
  is `parse_name` plus a refusal of `none` in any case.
- `equipment_core`: `_fields` gains `type_id` (nullable id) and `notes`
  (`optional_text_parser("Notes", NOTES_MAX)`, `NOTES_MAX = 2000`); a null
  `type_id` is dropped on create, like a null `parent_id`. `_TRACKED` gains
  `("type_name", "type")`, and `_display` shows a missing type as `none`.
  `check_type_class(type_class_id, node_class_id)` returns "This type belongs to
  another class" or `None`.

### Shell

- **Masters (`masters.py`).** `GET /equipment-types` (`?class_id`,
  `?include_inactive=1`; ordered by class code, then name; each item carries
  `class_code`). `POST` locks the class (`_lock_class_for_type(cur, class_id,
  "class_id")`: unknown 400, inactive 409), then inserts; a duplicate name in the
  class is caught by the unique key → 409 on `name`. `PUT` follows § 5.1's order:
  plain read of the type's `class_id` (404 if none) → when `active: 1`, lock that
  class with field `active` → lock the type → a sent `class_id` that differs is
  400 "Class cannot be changed", the same one is dropped → update. The old
  `_site_filter` became `_int_filter(name)`, used for `site_id` and `class_id`.
- **Equipment (`equipment.py`).** The node fragment LEFT JOINs the type, so list
  rows and the detail carry `type_id`/`type_name`, and the detail `notes`.
  `_LOCK_EQUIPMENT` now also selects `type_id`. `_lock_type(cur, type_id,
  node_class_id, newly_chosen)` runs `_LOCK_TYPE` and refuses unknown (400),
  other class (400), and inactive (409, only when the type is newly chosen).
  - **Create:** after the class lock (4), a non-null `type_id` is locked (5),
    then the counter (6).
  - **PUT:** `_check_type_on_update` applies § 5.2 exactly: `sent_type` is taken
    before unchanged `parent_id/unit_id/class_id/type_id` are dropped; a class
    change on a typed node without `type_id` → 400 "Pick a type of the new class,
    or none"; the resulting type is locked only when the type or the class
    changes; the active check only when the type itself changes. So the PUT
    table of § 5.2 holds row by row (each row has a test).
  - `_written_state` takes the type name from the type lock, as it does for
    unit and class codes; events compare names.
  - **List:** `type_id` filter (positive integer, else 400); `q` matches
    `e.code`, `e.name`, `e.notes` and `t.name`, escaped as before.
  - Module docstring: lock order now node → parent → unit → class → **type** →
    counter (6); the note on `masters.py` says it locks class before type.

### Frontend

- `stores/masters.js`: `equipmentTypes` + `ensureEquipmentTypes()` (all, inactive
  included), cleared by `resetMasters()`.
- `useFormModal` takes an optional `label(record)` (default
  `full_code ?? code`); `useMasterForm` passes it through. The three existing
  panels are unchanged.
- `EquipmentTypesPanel.vue` (new, Masters section "Equipment types", icon
  `fa-solid fa-sitemap`, perm `masters:read`, after Equipment classes): class
  filter, Show inactive, table (Class, Type, Status). Create: class `<select>`
  of active classes with its field error, and the name. Edit: the class as plain
  text, the form holds and sends only `name`; Deactivate/Reactivate through
  `ActiveToggle`, labelled `RPP · Closed execution`.
- `EquipmentFormModal.vue`: Type after Class ("— none —" + the chosen class's
  active types, the node's current type kept and marked "(inactive)"); the class
  `<select>` resets Type with `@change`, not a watcher; Notes textarea (4 rows,
  `maxlength` 2000) at the end with the help text; `fromRecord`/`toBody` carry
  `type_id` (`""` → `null`) and `notes` (empty → `null`); both fields render
  `fieldError`; `ensureEquipmentTypes()` joins the dialog's loads.
- `EquipmentDetailView.vue`: Type in Details; a Notes card when notes exist,
  `white-space: pre-wrap`.
- `EquipmentView.vue`: Type filter shown when a class is chosen or `type_id` is
  in the URL (with a class: its types; with only `type_id`: all types as
  `RPP · Closed execution`; inactive marked); choosing a class always clears
  `type_id`; `listUrl()` sends `type_id`; `ensureEquipmentTypes()` in the
  `Promise.all`; the Class cell shows the type muted after the code.
- `equipmentLabels.js`: `describeEvent` for `type`, `none` shown as "None".

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v5 (five re-runnable statements) |
| `backend/masters_core.py` | `RESERVED_TYPE_NAME`, `_parse_type_name`, `_TYPE_FIELDS`, `validate_equipment_type` |
| `backend/masters.py` | Equipment-types endpoints, `_lock_class_for_type`, `_TYPE_SELECT`, unique-key message, `_site_filter` → `_int_filter(name)` |
| `backend/equipment_core.py` | `type_id`/`notes` fields, `NOTES_MAX`, `NO_TYPE`, `check_type_class`, type tracking |
| `backend/equipment.py` | Type join/columns, `_LOCK_EQUIPMENT` + `type_id`, `_LOCK_TYPE`, `_lock_type`, `_check_type_on_update`, create/PUT type rules, `_written_state` type name, list filter and search, docstring lock order |
| `backend/tests/conftest.py` | `equipment_types` in `_TABLES`; `Uniq.type_name()`; `make_type` fixture |
| `backend/tests/test_masters_core.py` | `TestEquipmentType` |
| `backend/tests/test_equipment_core.py` | `TestCheckTypeClass`, type/notes cases in `TestTrackedChanges`, `TestTypeAndNotes` |
| `backend/tests/test_masters_api.py` | `TestEquipmentTypes`; types added to the permission tests |
| `backend/tests/test_equipment_api.py` | `test_row_fields` (+ `type_id`, `type_name`, still exact); bad `type_id` params; `TestTypes`, `TestNotes`, `TestTypeFilterAndSearch` |
| `frontend/src/stores/masters.js` | `equipmentTypes`, `ensureEquipmentTypes()`, reset |
| `frontend/src/composables/useFormModal.js` | Optional `label(record)` |
| `frontend/src/views/masters/useMasterForm.js` | Passes `label` through |
| `frontend/src/views/masters/EquipmentTypesPanel.vue` | New panel |
| `frontend/src/views/MastersView.vue` | "Equipment types" section |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | Type select, class `@change` reset, Notes textarea, body/record mapping |
| `frontend/src/views/EquipmentDetailView.vue` | Type in Details, Notes card |
| `frontend/src/views/EquipmentView.vue` | Type filter, class clears type, Class cell with type, search placeholder |
| `frontend/src/utils/equipmentLabels.js` | `type` event text |
| `frontend/tests/equipmentLabels.test.js` | `type` event cases |
| `docs/steps/S004-equipment-types-notes/1-brief.md` | Status → In code review |
| `docs/steps/README.md` | S004 row → In code review |

22 files (20 code/test files, of which 1 new; 2 docs status edits).

## 4. Decisions taken

Small forced choices the brief left open; none changes the design.

1. **Message for the reserved name:** `The name "none" is reserved; history uses it
   for no type` (field `name`). The brief fixes the rule but not the text.
2. **`NO_TYPE` in `equipment_core` is `masters_core.RESERVED_TYPE_NAME`**, so the
   word history writes and the word masters refuses cannot drift apart.
   (`equipment_core` already imported from `masters_core`.)
3. **`_lock_class_for_type` messages:** "Unknown class" (400) and "The class is
   inactive" (409), with the field passed in. The brief gives the second text for
   reactivation; I used the same for create.
4. **`_lock_type(cur, type_id, node_class_id, newly_chosen)`** does the three
   refusals of § 5.2 itself, and the PUT's part of the algorithm lives in a small
   helper `_check_type_on_update` so `update_equipment` stays readable. Same logic
   as the brief's pseudo-code, step for step.
5. **`_int_filter` also requires ASCII digits** (`raw.isascii() and raw.isdigit()`),
   as `equipment._int_arg` already does: the old `_site_filter` let `?site_id=²`
   through to `int()` and a 500. A one-word hardening of the helper the brief asked
   me to generalise; tested with `²`. Flagging it as a slight extension of "as
   `_site_filter` does".
6. **Test helper `Uniq.type_name()`** in `conftest.py` beside the other unique-name
   helpers, used by `make_type`.
7. **Notes card placement:** a full-width card under the Details / Parts / History
   row rather than inside the Details column, so long notes are readable and the
   three cards keep equal heights. It still sits below Details.
8. **Search placeholder** on the list changed from "Search code or name…" to
   "Search code, name, notes…", since the search now covers notes (and type names).
9. **Type filter ordering:** active types first, then inactive (marked), the same
   pattern the list's class filter already uses.
10. **Create-type dialog preselects the class** when the panel's class filter
    is set to an active class, like the Units panel preselects the filtered site.
11. **Edit-type dialog shows the class as `RPP — Radial piston pump`** (code and
    name) from the classes cache, falling back to the code.

No departure from the brief.

## 5. Not done, deferred or assumed

- **Docs** (Plan § 2, § 4.1, § 5, glossary) are the planner's at approval, per
  brief § 3 Docs; not touched.
- **Migration check on the dev DB (user):** start the backend against
  `vel_yantra_master` (at v4 with S002/S003 rows): it should migrate to v5;
  existing rows get `type_id` and `notes` NULL; old events keep their values.
  Running the five v5 statements again by hand should give no error (I did this on
  the test DB only).
- **Manual browser checks (brief § 8):**
  - Masters → Equipment types: add *Closed execution* and *Open execution* under
    `RPP`; a duplicate (any case) is refused under Name; deactivate one — the
    confirmation names "RPP · Closed execution".
  - Equipment `RPP001`: pick a type; the inactive type isn't offered; change the
    class in the dialog and see Type reset to "— none —"; opening the edit dialog
    keeps the saved type selected (the `@change` reset must not fire on open);
    notes with several lines show as written on the page.
  - List: filter by class `RPP`, then type; change the class and see the type
    filter clear; open a URL with only `?type_id=…` and see the Type filter shown
    with `RPP · …` labels; search a word from the notes, and "closed".
  - History shows type changes ("Type: None → Closed execution") and no notes
    changes.
- **Assumed** (as the brief): every level may have a type; 2000 characters is
  enough for notes.
