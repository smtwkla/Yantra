```
Step: S004 — Equipment types and notes
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 15-10-2026
```

# S004 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Two `nit`s.

Reviewed: the working-tree diff against 6d58ce5 (20 code and test files, plus the new
`EquipmentTypesPanel.vue`), checked against `1-brief.md` as approved, with its Review
log (r1, r2) and the Gate A note, and against `3-impl-report.md`. I left out the
planner's doc edits (`docs/Plan.MD`, `docs/Maintenance-Philosophy.md`, the S002/S003
status lines, README).

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **551 passed** (23.7 s), frontend **24 passed**
  (4 files), exit 0.
- `npx vite build` in `frontend/`: clean, 135 modules, no warnings.

Both match the impl report.

## Findings

### CR1-01 — nit — `backend/equipment.py:277-278`

**Problem.** The `_lock_type` docstring says "An inactive type may be kept (a class
change keeping it) but not newly chosen". Under § 5.2, a class change can never keep
the type: the kept type belongs to the old class, so the lock always ends in 400 "This
type belongs to another class".

Keeping a deactivated type happens on the **no-lock** path ("other fields only"), which
never reaches `_lock_type`. So `newly_chosen=False` is only reached in the old-type case
(class changed, type unchanged), which is always refused on class before `active` is
looked at.

**Failure scenario.** None at run time. A later reader may trust the comment and think
a class change can carry an inactive type, then "fix" the wrong branch.

**Fix.** Reword it, e.g. "The active check applies only when the write chooses the
type; a type kept from before is checked for its class only."

### CR1-02 — nit — `frontend/src/views/EquipmentView.vue:79-83`

**Problem.** With both `class_id` and `type_id` in the URL, `typeChoices` lists only
that class's types. If the URL's `type_id` belongs to another class, the select has no
matching option and shows blank, while the list still sends `type_id`.

**Failure scenario.** Someone edits a URL by hand, or a link built elsewhere has
`?class_id=3&type_id=9` where type 9 is of class 4. The list comes back empty, and the
Type filter shows nothing chosen, not "All types". This is the "filter applied
invisibly" case that BR2-05 meant to avoid. The UI can't produce it, because choosing a
class clears `type_id`.

**Fix (optional).** When the URL's type isn't in `typeChoices`, also list it, labelled
`CLS · Name`, as the class filter does for inactive classes. Or leave it as is: only a
hand-made URL reaches this.

## Earlier rounds

None: this is round 1.

## Checked and found consistent

- **Migration v5 (§ 4.1).**
  - The five statements match the brief character for character, apart from
    indentation. The only addition is a Python comment between statements.
  - Each statement is safe to run twice: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF
    NOT EXISTS` (×2), `ADD CONSTRAINT … FOREIGN KEY IF NOT EXISTS`, and `MODIFY`.
  - The ENUM keeps the six old values in order, appends `type` and restates `NOT NULL`.
  - `uq_equipment_types_id_class` is created before the FK that references it.
  - The audit columns match v2's.
  - The migration is append-only: v1 to v4 are untouched.
- **§ 5.2 PUT algorithm** (`_check_type_on_update`, `update_equipment`). I walked every
  row of the table:
  - **Type and class unchanged:** the equal `type_id`/`class_id` are dropped, so no
    lock.
  - **A new type:** locked; class checked against the locked node's class; `active`
    checked.
  - **Class changed, `type_id: null`:** on a typed node, `type_id=None` stays in
    `clean` and nothing is locked. On an untyped node it is dropped as equal, and
    nothing is locked. Events are `class` plus `type X → none`.
  - **Class changed, a type of the new class:** locked; class matches; active
    checked.
  - **Class changed, the old type sent back:** `sent_type` is true, so there is no
    "Pick" error. `type_id` is dropped as equal; the lock happens because the class
    changes, and the result is a 400 "belongs to another class", not the FK.
  - **Class changed, nothing about the type, node typed:** 400 "Pick a type of the new
    class, or none", and the class is unchanged in the DB (tested).
  - **Other fields only, type deactivated since:** no lock, 200 (tested, with and
    without the edit dialog's sent-back `type_id`/`class_id`).
  - **Class change of an untyped node:** no lock, 200.
  - **Create:** the class is locked (4), then a non-null type (5) with all three
    refusals, then the counter (6). A null `type_id` is dropped by the validator.
- **Where the decisions come from (S002 BR3-01).**
  - "Node has a type" comes from `_LOCK_EQUIPMENT`, which now selects `type_id`.
  - The type's existence, class and `active` come from `_LOCK_TYPE`.
  - `sent_type` is taken before the unchanged fields are dropped.
- **The composite FK as a 500.**
  - Every path that writes a non-null `type_id`, or changes `class_id` on a typed node,
    goes through the type lock with a class match first, or is refused.
  - A type's `class_id` can't change (masters PUT), so a concurrent edit can't undo the
    match.
  - The FK backstop is tested with a direct `UPDATE`.
- **Lock order.**
  - `equipment.py` locks node (1) → parent (2) → unit (3) → class (4) → type (5) →
    counter (6), on both create and PUT. The docstring and the `_next_code` comment
    are renumbered.
  - `masters.py` POST locks class → insert. PUT does a plain read of `class_id` →
    class lock (reactivation only, field `active`) → type lock. Rename and deactivate
    lock the type only.
  - Neither module's type path locks equipment, so no cycle spans the two.
  - The FK S-locks on insert/update fall on rows already X-locked by the same
    transaction.
  - The scrap check still runs after the higher-order locks. This is the existing,
    accepted deadlock shape (S002 § 6); the type lock adds nothing new to it.
- **Masters types.**
  - `_TYPE_FIELDS` includes `active` (BR2-01).
  - The name `none` is refused in any case, on create and rename.
  - The unique key maps to 409 on `name` (case-insensitive, tested).
  - Class rules:
    - a changed `class_id` is a 400 and the same one is accepted;
    - an unknown class is 400 and an inactive one 409 on create;
    - reactivating under an inactive class is 409 on `active`;
    - deactivating a type in use is allowed.
  - Unknown type is 404. List order is class code, then name.
  - `_int_filter` replaces `_site_filter`, with the ASCII hardening (tested with `²`).
- **Permissions.** GET is `masters:read` (`('*',)`); POST and PUT are `equipment:edit`.
  The RBAC tests now include types: engineer writes, operator 403, every role reads.
  No actor is taken from the client (`actor()`). All SQL is parameterised; the only
  f-strings are fixed fragments and placeholder lists.
- **Events.**
  - Names are compared, missing shows as `none`, and notes are not tracked.
  - A same-name reclassification gives a class event only (core and API tests).
  - The after-name is taken from the type lock (tested with `stale_reread`).
- **Search and list.**
  - `q` matches `e.code`, `e.name`, `e.notes` and `t.name`, escaped, through the same
    `_NODE_FROM` (LEFT JOIN) for both the count and the page.
  - The `type_id` filter is a positive integer, else 400 (`x`, `0` tested).
  - List rows carry `type_id`/`type_name` and no `notes`: `test_row_fields` is still
    exact.
- **Notes.** `optional_text_parser("Notes", 2000)` trims, keeps inner line breaks, and
  turns empty into `NULL`. 2000 passes and 2001 is a 400 on `notes`. `updated_by` is
  set and no event is written. A scrapped node refuses type and notes (409).
- **Pure core and `NO_TYPE`.**
  - `check_type_class`, `validate_equipment_type` and `tracked_changes` stay pure.
  - `equipment_core` already imported `parse_name` and `optional_text_parser` from
    `masters_core`. Importing `RESERVED_TYPE_NAME` keeps the existing direction
    (equipment depends on masters, never the reverse) and is pure → pure. No boundary
    issue, and the two uses can't drift.
  - The frontend repeats the literal `"none"`, as it already does for `"inherit"`. A
    language boundary makes that unavoidable.
- **Frontend.**
  - `useFormModal` has `label` with the `full_code ?? code` default, and
    `useMasterForm` passes it through. The other three panels are unchanged.
  - Types panel:
    - create offers a class select of active classes, with its field error;
    - edit shows the class as text, and `fromRecord` holds only `name`, so `class_id`
      is never sent;
    - `ActiveToggle` is labelled `RPP · Closed execution`.
  - Equipment dialog:
    - the class resets the Type through `@change`, not a watcher, so `fromRecord`'s
      `type_id` survives opening the edit dialog;
    - Type lists the chosen class's active types, plus the current type marked
      "(inactive)";
    - Type and Notes render `fieldError`;
    - `toBody` maps `""` to `null` for both;
    - `ensureEquipmentTypes()` runs in the dialog's load;
    - `openEdit` is only called from the detail page, whose node carries `notes`, so
      saving can't blank notes from a list row.
  - Detail page: Type in Details; a Notes card with `pre-wrap`, shown only when notes
    exist.
  - List page:
    - the Type filter shows when there is a class or `type_id` in the URL;
    - choosing a class always clears `type_id`;
    - inactive types are marked, and labelled `CLS · Name` when no class is chosen;
    - `listUrl` sends `type_id`;
    - `ensureEquipmentTypes()` joins the `Promise.all`;
    - the Class cell shows the type muted after the class code.
  - `resetMasters()` clears the types cache.
- **The coder's small choices.** All are reported in "Decisions taken", none departs
  from the brief, and I accept each:
  - the reserved-name message;
  - the shared "Unknown class" / "The class is inactive" texts;
  - the stricter ASCII-digit `_int_filter`, a real fix for a latent 500;
  - the full-width Notes card under the Details row, which is still "below Details";
  - the search placeholder "Search code, name, notes…";
  - in the Type filter, active types first, then by the server's class/name order (a
    stable sort), as the class filter does;
  - the class preselected in the create-type dialog from the panel filter;
  - the class shown as `CODE — Name` in the edit-type dialog;
  - `NO_TYPE` taken from `RESERVED_TYPE_NAME`.
- **Scope.** Everything in § 3 is built. I found nothing beyond it: no new endpoint,
  dependency or config, and `Uniq.type_name()` and `make_type` are test helpers the
  brief named.
- **Infrastructure.** New routes use `get_db()`, so they get the existing 503 and
  dead-connection handling. There is no deprecated API and no silent exception
  swallowing, and comments say why.

## Manual browser checks for the user

1. **Dev DB migration.** Start the backend against `vel_yantra_master` (at v4, with
   S002/S003 rows).
   - It migrates to v5.
   - Existing equipment has no type and no notes.
   - Old history entries read as before.
   - Optional: run the five v5 statements again by hand. They should give no error.
2. **Masters → Equipment types.**
   - Add *Closed execution* and *Open execution* under `RPP`.
   - Add "closed execution" again: it is refused under Name.
   - Name a type `none`: it is refused.
   - Deactivate one: the confirmation names "RPP · Closed execution".
   - Deactivate class `RPP`, then try to reactivate the type: the dialog shows "The
     class is inactive". Reactivate `RPP` afterwards.
3. **Equipment `RPP001`, edit dialog.**
   - Pick *Closed execution* and save.
   - Reopen the dialog: Type still shows *Closed execution*.
   - Change the class: Type resets to "— none —".
   - Cancel. Deactivate *Closed execution* in Masters, then edit another field of
     `RPP001`: it saves, and Type shows "Closed execution (inactive)".
   - The inactive type is not offered on another `RPP` node.
4. **Notes.** Enter several lines, including an indented line. The equipment page shows
   them exactly as written, in the Notes card. Clear them: the card disappears.
5. **History.** It shows "Type: None → Closed execution" and similar entries, and
   nothing for notes changes.
6. **List.**
   - Filter by class `RPP`, then by type: the type filter appears and narrows the list.
   - Change the class: the type filter clears.
   - Open a URL with only `?type_id=<id>`: the Type filter is shown, with
     `RPP · Closed execution` labels.
   - Search a word from the notes, then "closed": both find `RPP001`.
   - The Class column shows `RPP · Closed execution`.
