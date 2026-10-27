```
Step: S063 — Equipment category above the class
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 27-10-2026
```

# S063 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the brief asks, with the
locks and refusal fields of § 5.2 and § 5.3 as written. I found no `minor` finding, and 5 nits.
One item is still open in the impl report: the whole-suite browser run (Normal) has no result yet
(§ Tests, "filled in when the run ends"). Gate B needs that result there, and green.

## Scope of this review

- **Diff read:** `git diff -w --ignore-cr-at-eol refs/steps/S063^ refs/steps/S063` (the snapshot
  against c9142b4), limited to the files in the impl report § 3. The roadmap, step-skill,
  README and feedback-tool changes in the snapshot are not S063's and are not reviewed.
- **Read in full:** `EquipmentCategoriesPanel.vue`, `equipmentFilters.js`, `test_migration_v35.py`;
  the class routes and `_lock_active_parent` in `masters.py`; `useMasterForm.js`; the filter and
  query code of `EquipmentView.vue`; `_integrity_error` in `api_common.py`.

## Tests

- **Unit suites** (`YANTRA_TEST_RUN=s063cr1 tooling\run-tests.bat`): **all PASSED**. Backend 3315
  passed, frontend 243 passed, tooling 185 passed. The counts match the impl report.
- **Build check** (`npx vite build` in `frontend/`): built. Only the known chunk-size warning.
- **Browser tests:** I ran none, because no finding of mine needs one. The coder's targeted run names
  the right specs: `masters`, `equipment` and `asset-list` (the screens changed) plus `screens`. The
  report gives 93 passed and 1 skipped (the existing desktop skip). The whole-suite run (Normal) was
  still running at review time; see the verdict.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `docs/steps/S063-equipment-category/3-impl-report.md:91`: The duplicate category
  name returns 409, not the 400 that brief § 8.2 names. 409 is the app's rule for every UNIQUE key
  (`api_common._integrity_error`), and the test asserts 409. Add one line to "Decisions taken" to
  record this.
- **CR1-02** (nit) `frontend/src/views/masters/EquipmentCategoriesPanel.vue:62-64`: The empty text
  "No equipment categories yet. Add one, …" also shows to a reader who cannot add. It also shows when
  every category is inactive and *Show inactive* is off. Show "Add one, …" only with `canEdit`, and
  say "No active categories. Turn on Show inactive to see the others." when inactive rows exist.
- **CR1-03** (nit) `backend/masters.py:425-444`: When a class is reactivated in an inactive category,
  the refusal "The category is inactive" (field `active`, top of the dialog) does not say what to do
  (CLAUDE-COMMON scope B). The brief § 5.2 fixed this text, so the change needs KLA at gate B, e.g.
  "This class's category is inactive. Pick another category or No category, then reactivate."
- **CR1-04** (nit) `backend/masters.py:557-558`: The `_lock_active_parent` docstring's second line is
  151 characters long. Re-wrap it to the module's width.
- **CR1-05** (nit) `frontend/src/views/EquipmentView.vue:90-93`: `categoryChoices` repeats the
  "active first, then by key" sort of `classChoicesFor`. A small `byActiveThen(key)` helper in
  `equipmentFilters.js` would serve both.

## Checked and found consistent

- **Migration v35** (`local_db.py`): the SQL is the brief's § 4.1, with `IF NOT EXISTS` on the table,
  the column and the key. `test_migration_v35.py` covers § 8.1: a fresh database, the key refusing an
  unknown id (1452), a v34 database with every row kept and `category_id` NULL, and a re-run with one
  key and an equal `_schema()`. `FOREIGN KEY IF NOT EXISTS` works on this MariaDB, so the fallback is
  not needed. No precondition is needed (new table, nullable column).
- **When the category is read (§ 5.2):** `_lock_category_of_class` reads it only in case (a), a new
  non-null id different from the stored one (field `category_id`), or case (b), a reactivation that
  keeps a category (field `active`). Otherwise it does not read it. The create always reads a given
  category, active or not. An unknown id is 400 on `category_id`, never a 500 from the key, also on
  an inactive class (tested).
- **Locks (§ 5.3):** a class update locks its row, then the category. A class create locks only the
  category, now inside `transaction(conn)` and re-read after the commit (BR1-02). A category update
  locks its row, then counts the active classes as the transaction's first plain read. No category
  write takes a class lock. `equipment.py` and `properties.py` lock classes but never a category. So
  the order is acyclic, and a concurrent move or reactivation into a category either waits and sees
  it inactive, or commits first and blocks the deactivation. The invariant "no active class in an
  inactive category" holds on every write path: create, update, reactivation and category deactivate.
- **Category rules (§ 5.1):** name 1–50 characters, trimmed, unique in any case. Rename is free.
  Deactivation is refused with the singular and plural texts of BR1-13 on field `active`, so the
  message shows at the top of the dialog. Inactive classes do not block it. `class_count` counts
  active classes only.
- **Permissions (§ 5.5):** `GET` uses `masters:read`, `POST` and `PUT` use `equipment:edit`, as the
  class routes. `config_rbac.py` is unchanged. The actor comes from `actor()`. All SQL uses
  parameters; `table` in `_lock_active_parent` is a code constant.
- **The database down (§ 5.6):** the new routes use `get_db()`; the 503 is tested.
- **The filter (§ 5.4):** `_list_filters` reads `category_id` with `int_arg(minimum=1)` against
  `c.category_id`, the node's own class, for the list and the asset list. In `EquipmentView.vue`, a
  chosen category narrows the class select. A URL class outside the category stays listed, last.
  Choosing a category clears a class outside it, with its type, and keeps a class inside it. Choosing
  a class leaves the category alone, and the level does not change (D9). `category_id` is in
  `listUrl()`, in `FILTER_KEYS` and in the header line "Category: <name>" or "Category: #<id>".
  The label selection resets on any query key, so it covers the category too.
- **The class dialog (§ 5.2 *The dialog*):** *No category* first, then the active categories by name,
  then the class's own inactive category marked "(inactive)". `fromRecord` carries `category_id`,
  and `toBody` sends `null` for *No category*. A name-only edit sends the stored id back unchanged,
  so nothing reads the category (tested: `test_reactivating_a_class_in_an_inactive_category`).
- **Tests against § 8:** § 8.2 is covered in full: names and their limits, the duplicate in another
  case, both deactivation cases, reactivate, the class cases (`true`, `"3"`, 0, -1, 1.5, unknown,
  inactive, inactive create, keep and clear), the 403s for floor roles, reading by every role,
  `class_count`, and the 503. § 8.3 is covered: the category with and without `class_id`, `abc`, `0`
  and `-1` as 400, an unknown id as empty, and parts kept with their machine. Unit tests cover the
  pure helpers and the header label.
- **Browser tests (§ 8.4):** each test asserts what the user sees: the Category column, the Classes
  count, the refusal text, the exact class options, the row count after a reload, and the section
  header. Each dialog opened calls `expectDialogFits`. No test is tagged `@device`, which is right:
  none checks a layout.
- **Manual checks:** the impl report has both important checks of § 8.4 as `[auto]` with their tests.
  § 8.5 has no real-device check, so `device-checks.md` needs no row.
- **Use on the floor:** the dialogs use the shared `FormModal`. Deactivation goes through the
  `ActiveToggle` confirm step. The new select joins the filter row's `flex-wrap`. The new table
  column sits in `table-responsive`. The no-permission state hides *Add category* and *Edit*.
  Screen text is plain and short; the buttons start with a verb ("Add category").
- **Design:** the rules live in `masters_core.py` (pure) and `equipmentFilters.js` (pure), and the
  routes stay a thin shell. The panel follows `TradesPanel.vue` and `useMasterForm`, as the brief
  asks. The shared test helpers (`make_category`, `categorySetup`) are reported in "Decisions taken".
- **Docs pass:** `docs/schema.md` has the table row, the class's column, the Mermaid table and link,
  and the "migration v35" line. `docs/schema.html` has the overview and *Equipment* tabs (all
  columns there) and the meta line (v35, 39 tables, 57 links). `Plan.MD` § 2 and § 4.1,
  `Maintenance-Philosophy.md` (glossary row) and `.claude/CLAUDE.md` (the spec-to-step map) are
  updated. No secret, role or device check changed.
- **Scope:** nothing is built beyond the brief. The out-of-scope items (category on the machine,
  labels, rows; "No category" in the list filter; property-dialog category) are absent.

## Manual browser check for the user

None required. Every important check is `[auto]`, and the brief has no real-device check.

## Feedback

- hindrance: `step_snapshot.py diff S063` takes no path filter, so reading only the step's files among the roadmap and tooling changes in the same snapshot needed a plain `git diff refs/steps/S063^ refs/steps/S063 -- <files>` (2 calls).
- waste: the one-line `TABS` JSON of `docs/schema.html` made a docs diff 52 KB and spilled to a file; a grep of the tables was needed instead (1 extra call).
- idea: let `step_snapshot.py diff` take `-- <paths>`, and have the orchestrator's spawn prompt give the list of non-step files in the snapshot as an exclude list.
