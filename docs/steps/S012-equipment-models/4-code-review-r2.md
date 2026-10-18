```
Step: S012 — Equipment models
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 17-10-2026
```

# S012 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All three round-1 findings are fixed. There
is one new `nit`, a docstring the fix left out of date.

This round covers only the fix-round changes listed in `3-impl-report.md` § Fix rounds › Round 1:
- `backend/masters.py`;
- `backend/documents.py`;
- `backend/tests/test_removed_documents_api.py`;
- `frontend/src/views/masters/ManufacturersPanel.vue`.

The rest of the diff was reviewed in round 1. As in round 1, I set aside the unrelated changes:
- the criticality badge colours in `equipmentLabels.js` (only `case "model"` is S012);
- `docs/Plan.MD`, `docs/Maintenance-Philosophy.md` and `docs/Plant-Facts.md`;
- `docs/review/`.

## Test result (run by the reviewer)

- `tooling/run-tests.bat`: **backend 986 passed** (68 s), **frontend 51 passed** (9 files). Exit 0.
- `npx vite build` in `frontend/`: built in about 2 s, with no errors.

## Findings

### CR2-01 — nit — `backend/masters.py:430`: the `_lock_active_parent` docstring still says it is for models only

- **Problem.** The docstring reads "Lock the manufacturer or class a model is created or
  reactivated under". After the CR1-01 fix, `create_equipment_type` (`masters.py:349`) and
  `update_equipment_type` (`masters.py:369`) also call it, for the class of a type. The helper is
  also defined in the models section (line 429), below its first use in the types section. That
  works in Python, but it is not where a reader would look.
- **Failure scenario.** Someone changes the model rule, for example by adding a check that only
  models need. They trust the docstring, change the shared helper, and type create and type
  reactivation change with it.
- **Fix.** Reword the docstring to "Lock the parent row (manufacturer or class) that a model or
  type is created or reactivated under: …". Optionally, move the helper up beside `_lock_row`,
  ahead of the types section. Behaviour does not change either way.

## Earlier rounds

- **CR1-01 (minor): Fixed, verified.**
  - `_lock_class_for_type` is gone. `grep` finds no reference to it left in `backend/`.
  - `create_equipment_type` calls
    `_lock_active_parent(cur, "equipment_classes", clean["class_id"], "class_id", "class")`.
  - `update_equipment_type` makes the same call with `stored["class_id"]` and `"active"`.
  - The old and new helpers run the same `SELECT id, active … FOR UPDATE`. They return the same
    messages, "Unknown class" (400) and "The class is inactive" (409), on the same fields.
  - The reactivation path keeps the class → type lock order: the plain read of `class_id`, then
    the class lock, then `_lock_row` on the type.
  - The type tests in `test_masters_api.py` still pass unchanged, as the report says.
- **CR1-02 (nit): Fixed, verified.**
  - The model branch of `_removed_branches` (`documents.py:467`) now matches
    `CONCAT(mf.name, ' ', m.designation) LIKE %s OR d.title LIKE %s OR d.original_name LIKE %s`,
    with the pattern bound three times.
  - The concatenation equals `masters_core.model_label` (`f"{manufacturer_name} {designation}"`),
    so the text shown on the row is now searchable.
  - The designation alone and the manufacturer name alone still match, because both are
    substrings of the concatenation. No case the brief asks for is lost.
  - `_REMOVED_MODEL_BRANCH` inner-joins `manufacturers`, so `mf.name` is never NULL and the
    `CONCAT` never becomes NULL.
  - `test_q_matches_designation_manufacturer_title_and_file_name` now also searches by
    `model["label"]`.
  - The parameters are still bound, not formatted into the SQL.
- **CR1-03 (nit): Fixed, verified.**
  - `ManufacturersPanel.reload` runs
    `Promise.all([ensureManufacturers({ refresh: true }), ensureModels({ refresh: true })])`.
  - `ensureModels` fetches `equipment-models?include_inactive=1`, the same list the equipment
    form's picker reads, so a rename reaches the picker.
  - A failure in either request still shows in `loadError`; it is not swallowed.
  - Both reads need `masters:read`. Anyone who can open the panel can read the models, so the
    extra request adds no new 403 path.
  - The comment says why.

## Checked and found consistent

- The fix round touched only the four files named in the report. Each change does only what its
  finding asked for, with no change in scope.
- No regression:
  - the full backend and frontend suites are green;
  - the build is clean;
  - the type create and reactivate tests and the removed-list tests pass unchanged, apart from
    the one added `q` value.
- The report's Fix rounds section records each finding with its status and what changed.
- The `## Manual checks` section still carries the four important checks of § 8 as unticked
  boxes, and the phone check as a plain note.
- Track: full. No track issue.

## Still for the user's manual browser check

Unchanged from round 1, not yet ticked:
- [ ] As engineer: add "Atlas Copco" / "GA37" (CMP, Screw compressor), then create a compressor by
  picking it. Class and type should show from the model, and the page should show Manufacturer
  and Model.
- [ ] Add "SMTW (in-house)" / `SMTW-HYP-01` (press) and a Generic model. Create a press and a
  component with them.
- [ ] Upload a manual on the model in Masters › Models. It should appear as "From model",
  read-only, on every compressor of that model. Remove it in Masters, then restore it from
  Settings › Removed documents.
- [ ] **Production, at the release:** check that the MariaDB version is ≥ 10.5. Then confirm there
  is no equipment: as admin or IT admin, with Show scrapped ticked and Level = All levels, the
  total must be 0.

Two more, for this round's fixes:
- Rename a manufacturer in Masters, then open Equipment › Add equipment in the same tab. The
  picker should show the new name.
- In Settings › Removed documents, search by a model's full label, for example "Atlas Copco GA37".
  The removed model document should be listed.

Also (plain): pick a model on a phone (long labels).
