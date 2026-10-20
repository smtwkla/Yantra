```
Step: S016 — Failure codes
Doc: impl-report
Author: Coder (Opus)
Date: 20-10-2026
```

# S016 — Implementation report

## 1. What was built

- **Masters › Failure codes**: a new Masters section (after *Models*) with a
  **Modes / Causes / Actions** switch. Everyone with `masters:read` sees the
  three lists; holders of the new key `failure_codes:edit` (engineer, manager by
  inheritance, IT admin) add, edit, deactivate and reactivate.
- **Failure modes (symptoms)**: code, label, optional description, and one
  equipment class or **General**. Filter *All* / *General* / one class; *Show
  inactive*. The class is fixed once created.
- **Failure causes**: code, label, optional description and one of ISO 14224's
  five cause groups; filter by group. The group stays editable.
- **Maintenance actions**: code, label, optional description.
- **Migration v11**: the three tables and the seed rows from ISO 14224 Annex B:
  14 general modes, 15 causes and 12 actions, `created_by = 'migration-v11'`.
- **API** under `/api/masters`: list / create / update for each list, as in
  brief § 6, including `GET /failure-modes?class_id=N` (class N's modes plus the
  General ones: the list S017's raise screen will use).

## 2. How it works

**Data (v11).** `failure_modes` (`class_id` NULL = General, FK to
`equipment_classes`, index `ix_failure_modes_class (class_id, active)`),
`failure_causes` (`cause_group` ENUM in ISO's group order) and
`maintenance_actions`, all with the usual audit columns. Unique keys:
`uq_failure_modes_code`, `uq_failure_causes_code`, `uq_failure_causes_label`,
`uq_maintenance_actions_code`, `uq_maintenance_actions_label`. Each statement is
safe to run twice: `CREATE TABLE IF NOT EXISTS`, and the seeds are
`INSERT IGNORE`, keyed on the unique code, so a re-run keeps an engineer's edit
of a seed row.

**Validation (pure, `masters_core.py`).** `validate_failure_mode`,
`validate_failure_cause` and `validate_maintenance_action` use the existing
`_validate` pattern:
- **Code**: trimmed and upper-cased, then checked against `FAILURE_CODE_RE`
  (`^[A-Z0-9]+(\.[A-Z0-9]+)*$`) and the 8-character limit. So `3.4`, `NOI` and
  `12` pass, and `3.`, `.4`, `1..2`, `N OI`, `N-OI` and `1/2` fail.
- **Label**: trimmed, inner spaces collapsed, 1–60 characters.
- **Description**: optional; trimmed; empty becomes NULL; up to 255 characters.
- **Cause group**: required on create, one of `CAUSE_GROUPS`.
- **Mode `class_id`**: optional; `null` means General.

**Routes (`masters.py`).**
- *Modes* follow the equipment-types pattern:
  - **Create** locks the class with `_lock_active_parent`. An unknown class is a
    400 `Unknown class`; an inactive class is a 409 on `class_id`.
  - **Update** reads the stored class without a lock first. A different
    `class_id` is a 400 `Class cannot be changed`. Reactivating a mode of an
    inactive class is a 409 on `active`; the class is locked before the mode
    (class → mode order).
  - **Label check** (`_check_mode_label`), on create and whenever a PUT sends
    `label`. It compares with a plain `=` on `label`, so the case-insensitive
    collation applies, and counts inactive rows. A class mode is checked
    against its own class and the General modes; a General mode against every
    mode. A clash is a 409 on `label`, and the message names the clashing code
    and its class, e.g. `(NOI, General)`.
- *Causes and actions* have no rule beyond their unique keys. Their create and
  update share two small helpers, `_create_plain_master` and
  `_update_plain_master` (update locks the row; an unknown id is a 404). A
  duplicate code or label is a 409 with field `code` or `label`, through the
  five entries added to `UNIQUE_KEY_ERRORS`.
- *Ordering*:
  - modes with `class_id=N`: by label;
  - modes without a filter: General first, then class code, then label;
  - causes: `cause_group, code` (ENUM order);
  - actions: `CHAR_LENGTH(code), code`.

**Frontend.** `FailureCodesPanel.vue` is a three-button group that swaps
between `FailureModesPanel`, `FailureCausesPanel` and `MaintenanceActionsPanel`.
Each panel follows the existing masters panels: a table, *Show inactive*,
`FormModal` with `useMasterForm`, and `ActiveToggle` in the edit dialog. Edit
controls show only with `failure_codes:edit`. When a mode is edited, its class
is shown as plain text and never sent. A new mode starts under the class being
filtered on, when that class is active. The store has `failureModes`,
`failureCauses` and `maintenanceActions` with `ensureX()`, all cleared by
`resetMasters()`.

**Test isolation.** The three tables are not in `conftest._TABLES`. The
session clean-up deletes their rows whose `created_by` is not
`'migration-v11'`, so the seeds survive and a second run starts clean.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v11: three tables, five unique keys, picker index, seed rows |
| `backend/config_rbac.py` | New global key `failure_codes:edit` = (`maint_engineer`, `it_admin`) |
| `backend/masters_core.py` | `FAILURE_CODE_RE`, `FAILURE_CODE_MAX`, `FAILURE_LABEL_MAX`, `FAILURE_DESCRIPTION_MAX`, `CAUSE_GROUPS`; the three validators |
| `backend/masters.py` | Routes for the three lists, `_check_mode_label`, `_create_plain_master` / `_update_plain_master`, five `UNIQUE_KEY_ERRORS` entries, module docstring |
| `backend/tests/conftest.py` | Session clean-up of non-seed rows (`_SEEDED_TABLES`, `SEED_CREATOR`); `Uniq.failure_code()`, `Uniq.failure_label()` |
| `backend/tests/test_masters_core.py` | Tests of the three validators |
| `backend/tests/test_rbac.py` | `test_role_matrix` rows for engineer, manager, IT admin; `test_failure_codes_edit_holders` |
| `backend/tests/test_failure_codes_api.py` (new) | API tests (§ 8) |
| `backend/tests/test_migration_v11.py` (new) | Tables, keys, seeds, re-run |
| `frontend/src/views/MastersView.vue` | New section `failure_codes` after *Models* |
| `frontend/src/views/masters/FailureCodesPanel.vue` (new) | Modes / Causes / Actions switch |
| `frontend/src/views/masters/FailureModesPanel.vue` (new) | Modes list, class filter, add/edit |
| `frontend/src/views/masters/FailureCausesPanel.vue` (new) | Causes list, group filter, add/edit |
| `frontend/src/views/masters/MaintenanceActionsPanel.vue` (new) | Actions list, add/edit |
| `frontend/src/stores/masters.js` | Three new lists and `ensureX()`; `resetMasters()` clears them |
| `frontend/tests/masters.test.js` | The new store lists: paths, cache, reset |
| `docs/steps/S016-failure-codes/1-brief.md`, `docs/steps/README.md` | Status only |

## 4. Decisions taken

1. **Shared helpers for causes and actions** (`_create_plain_master`,
   `_update_plain_master`). The four routes would otherwise be copy-paste.
   Existing masters (trades, manufacturers) were not refactored onto them: out
   of scope.
2. **The label-clash message names the clashing row**, e.g. *"A failure mode
   with this label exists (NOI, General)"*, so the engineer sees which row to
   rename. The brief asks only for 409 on `label`.
3. **The label check runs only when a PUT sends `label`**, not on
   reactivation. Inactive rows are part of the check, so a reactivation cannot
   bring a clash back (brief § 5.1). The one gap is the accepted race: two
   saves at the same moment.
4. **`Uniq.failure_label()`** was added next to the brief's
   `Uniq.failure_code()`, because cause and action labels are unique too.
5. **Seed causes have no description** (NULL): brief § 4.3 gives none. The
   labels already are ISO's names.
6. **The `ELU` description is in plain text**, without the brief's backticks:
   *"External leakage (ISO ELU utility medium / ELP process medium; one entry
   here)"*.
7. **`class_id=N` for an unknown or inactive class** is not refused: it returns
   the General modes plus any modes of N. The brief does not say; S017 will
   pass a real equipment's class. A non-number is a 400 (the existing
   `_int_filter`).
8. **The deactivation guard on equipment classes is unchanged**, as § 5.2 says:
   a class can be deactivated while it has active modes (tested).
9. **The switch in `FailureCodesPanel` is a Bootstrap button group**, not a
   second `ModuleToolbar`, so it reads as a sub-switch inside the section.
10. **ISO check (brief § 4.3).** I checked the seed codes and names against
    ISO 14224:2016 Annex B **from memory**; I had no copy of the standard. The
    mode codes (Tables B.6–B.15), cause numbers and names (Table B.3) and the
    activity numbers 1–12 (Table B.5) all match what I recall, so I made no
    corrections. A check against the printed standard is still worth doing.

There are no departures from the brief.

## 5. Not done, deferred or assumed

- **"Code frozen once in use"** and **S017's class check for a ticket's mode**
  are for S017 and S018, as brief § 5.4 says. Nothing references the codes yet.
- **A v11 re-run after an engineer changed a seed mode's code** (e.g. `NOI` to
  `NOISE`) would insert `NOI` again, because `INSERT IGNORE` is keyed on code.
  For modes that gives a duplicate label: there is no label index, and the
  API's label check does not run in a migration. This happens only if v11 is
  re-run after such an edit, i.e. a half-applied v11. In practice a re-run
  happens only straight after a failed first run, before anyone edits. Causes
  and actions are protected by their label unique keys.
- **Press modes (§ 4.4)** are not seeded: an engineer enters them during the
  manual checks.
- **No browser check was done.** The UI was built and compiled, but not looked
  at on a phone or desktop; that is the manual checks.

## Manual checks

Important:
- [ ] As an engineer, open Masters › Failure codes: the pre-filled modes,
  causes and actions are there; enter the press modes of § 4.4 under the press
  class; filter by the press class shows them; *General* shows the 14 general
  ones.
- [ ] As an operator, the section is read-only (no Add, no edit, no toggle).
- [ ] On a phone, the switch and the lists are usable (no sideways scroll).

Also:
- Deactivate a seed mode; it disappears unless *Show inactive*; reactivate it.
- Try to add a press mode labelled "Abnormal noise": refused, it is already a
  general mode.

## Test results

- `tooling/run-tests.bat`:
  - backend: **1460 passed**;
  - frontend (vitest): **59 passed**;
  - dependency-audit tests: **42 passed**.
- A second run of the new and changed backend test files after the full run
  (403 passed) confirms that the session clean-up leaves a repeat run clean.
- `npx vite build` in `frontend/`: built with no errors and no warnings.

## Fix rounds

### Round 1

Review: `4-code-review-r1.md`. The user asked for CR1-02 only.

- **CR1-01: Fixed.** The over-long docstring line in `backend/masters.py`
  (line 12) is re-wrapped to the file's usual width; the words are unchanged.
- **CR1-02: Fixed.** Two tests added to `TestModeClass` in
  `backend/tests/test_failure_codes_api.py`, pinning decision 7:
  - `test_unknown_class_filter_gives_the_general_modes`: `class_id=999999`
    returns 200 with only General modes (a fresh General mode is in the list).
  - `test_inactive_class_filter_gives_general_and_its_own_modes`: after the
    class is deactivated, `class_id=N` returns 200 with the General mode and
    the class's own mode.

  Both passed against the existing code; no production code changed.

Tests: see the run below.
