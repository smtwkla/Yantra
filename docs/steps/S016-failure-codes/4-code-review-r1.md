```
Step: S016 — Failure codes
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S016 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 0 minor, 2 nit.

## Test run

- `tooling/run-tests.bat`: exit 0.
  - backend (pytest): **1460 passed** (118.9 s);
  - frontend (vitest): **59 passed** (10 files);
  - dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built in 2.2 s, no errors and no warnings.

This matches the counts in the impl report.

## Scope reviewed

S016 files from the working tree (`git diff -w --ignore-cr-at-eol` plus the untracked files):
`backend/local_db.py`, `config_rbac.py`, `masters_core.py`, `masters.py`,
`tests/conftest.py`, `tests/test_masters_core.py`, `tests/test_rbac.py`,
`tests/test_failure_codes_api.py` (new), `tests/test_migration_v11.py` (new),
`frontend/src/views/MastersView.vue`, `views/masters/FailureCodesPanel.vue`,
`FailureModesPanel.vue`, `FailureCausesPanel.vue`, `MaintenanceActionsPanel.vue` (new),
`stores/masters.js`, `tests/masters.test.js`, and the status lines in `docs/steps/README.md`
and the brief. I also read the helpers these call in full (`_lock_active_parent`, `_lock_row`,
`_int_filter`, `_list_response`, `clean_body`, `insert_row`, `update_row`, `transaction`,
`useMasterForm`). I ignored `docs/steps/S017-raise-tickets/` and the S022 brief and index row,
as instructed.

## Findings

### CR1-01 — nit — `backend/masters.py:12`

**Problem.** The module docstring line edited by this step ("Equipment types, and failure modes of
a class, lock class → type (mode).  Manufacturers and models lock manufacturer → model →") is
132 characters long. It is the only line over 120 in the touched backend files, and the
rest of the docstring wraps at about 95.

**Scenario.** It is only a matter of how the file reads: the line scrolls off the editor and
breaks the docstring's wrap.

**Fix.** Re-wrap the paragraph, e.g. "Equipment types and failure modes of a class lock
class → type (or mode)." on its own line, then the existing manufacturer sentence.

### CR1-02 — nit — `backend/masters.py:565`, `backend/tests/test_failure_codes_api.py`

**Problem.** Decision 7 of the report says that `GET /failure-modes?class_id=N` for an unknown
or inactive class returns the General modes and is not refused. That is a reasonable choice,
and it is reported, but no test pins it. Only the non-number 400 case is tested
(`test_bad_class_filter_is_400`).

**Scenario.** S017's raise screen will rely on this list. A later change could make an
unknown class a 400 or an empty list. The operator would then see no symptoms at all for
equipment whose class was deactivated: § 5.2 says such equipment still raises tickets.
No test would fail.

**Fix.** Add one test to `TestModeClass`: deactivate a class that has an active mode. Then
`?class_id=<it>` still lists that mode plus the General ones, and `?class_id=999999` lists
the General ones.

## Earlier rounds

None. This is round 1.

## Manual checks (user, in the browser)

The impl report's `## Manual checks` has all three **important** checks of brief § 8 as
unticked boxes, and the two plain notes. Still to do:

- [ ] As an engineer, open Masters › Failure codes. The pre-filled modes, causes and actions are
  there. Enter the § 4.4 press modes under the press class. The press-class filter shows them,
  and *General* shows the 14 general modes.
- [ ] As an operator, the section is read-only: no Add, no edit, no toggle.
- [ ] On a phone, the Modes / Causes / Actions switch and the lists are usable, with no
  sideways scroll. Also check that the Masters toolbar, which now has nine sections, still fits.
- Also: deactivate a seed mode, see that it disappears unless *Show inactive* is on, then
  reactivate it. Add a press mode labelled "Abnormal noise": it should be refused with
  "(NOI, General)".
- Also: brief § 4.3 asks for the seed codes and names to be checked against the printed
  ISO 14224:2016 Annex B. The coder checked them from memory. I compared them with my own
  recollection of Tables B.3, B.5 and B.6–B.15 and found no difference:
  - causes: 1.1, 1.2, 2.1, 2.2, 3.1–3.4, 4.1, 4.2, 5.1, 5.3–5.6;
  - activities: 1–12 (Replace … Other);
  - modes: BRD, FTS, STP, UST, ELU, NOI, VIB, OHE, LOO, ERO, PDE, STD, SER, OTH.

  A check against a copy of the standard is still open.

## Checked and found consistent

**Migration v11** (`local_db.py`):
- It is a new version appended after v10; no applied migration was edited.
- The three tables have the brief's columns, types and audit columns: InnoDB, utf8mb4, the
  same default collation as the other masters, so `=` on `label` is case-insensitive.
- It has the five named unique keys, `ix_failure_modes_class (class_id, active)`, and an FK
  from `failure_modes.class_id` to `equipment_classes`.
- The `cause_group` ENUM is in ISO order.
- Every statement can run twice: `CREATE TABLE IF NOT EXISTS`, and `INSERT IGNORE` keyed on
  the unique code.
- It seeds 14 / 15 / 12 rows with `created_by = 'migration-v11'`. The text matches § 4.3
  word for word, apart from the backticks dropped from the `ELU` description, which the
  report lists as decision 6.

**RBAC:**
- `failure_codes:edit` = (`maint_engineer`, `it_admin`); the manager inherits it.
- The key is not in `SITE_SCOPED`, so it is global, as § 5.5 asks.
- Every new route is gated: GETs on `masters:read`; POST and PUT on `failure_codes:edit`.
- `test_role_matrix` has exact sets for the engineer, manager and IT admin rows, and
  `test_failure_codes_edit_holders` was added.

**Validation** (pure, `masters_core.py`):
- Code: trimmed and upper-cased; `^[A-Z0-9]+(\.[A-Z0-9]+)*$` plus at most 8 characters;
  `.4`, `3.`, `1..2`, an inner space, `-`, `/` and non-strings are refused.
- Label: collapsed, 1–60 characters.
- Description: optional; empty becomes NULL; at most 255 characters.
- Cause group: required on create, one of five.
- Mode `class_id`: optional, null means General, and must be a positive int (not a bool).
- The validators have no DB access, no clock and no framework imports.

**Mode routes:**
- Create:
  - locks an active class with `_lock_active_parent`: unknown class → 400
    `Unknown class` / `class_id`; inactive class → 409;
  - runs the label check inside the transaction.
- Update:
  - reads the stored class without a lock;
  - refuses a different `class_id`, or `null` on a class mode, with 400;
  - on reactivation, locks the class before the mode (class → mode, as for types), and
    refuses an inactive class with 409 on `active`;
  - unknown id → 404;
  - other edits of a mode of an inactive class go through (tested).
- Label check:
  - plain `=`, inactive rows included, own row excluded;
  - a class mode is checked against its class and General; a General mode against every mode;
  - all values are bound as parameters, and only the fixed `scope` fragment is built into
    the SQL string.
- Ordering:
  - with `class_id`: by label;
  - without: `class_id IS NOT NULL, c.code, f.label`;
  - each row carries `class_code`, NULL for General.

**Causes and actions:**
- `_create_plain_master` / `_update_plain_master` take the table name from code constants
  only.
- A duplicate code or label goes to the global IntegrityError → 409 `{error, field}` through
  the five `UNIQUE_KEY_ERRORS` entries.
- The update is locked; unknown id → 404.
- Ordering:
  - causes: `cause_group, code` (ENUM order);
  - actions: `CHAR_LENGTH(code), code`.
- The cause group stays editable (§ 5.3).

**Concurrency:**
- The mode-label race is the one the brief accepts (§ 7 decision 8).
- Lock order is class → mode everywhere, with no cycle against class deactivation: that
  path does not touch modes, as § 5.2 says.
- The causes' and actions' uniqueness is enforced by the database.

**DB down and dead connections:** all routes use `get_db()`, so `DBUnavailable` → 503 and the
pool's reconnect apply. There is no new connection handling.

**Actor:** `actor()` from the session on every write. Nothing is taken from the client.

**Exceptions:** no `try`/`except` added, so nothing is swallowed. No deprecated APIs.

**Frontend:**
- The section `failure_codes` sits after *Models* on `masters:read`.
- The button-group switch remounts the chosen panel (`:key`).
- Each panel follows the existing masters pattern: `FormModal` + `useMasterForm`,
  `ActiveToggle`, *Show inactive*, and edit controls only with `failure_codes:edit`.
- The mode's class is shown as text on edit and never sent. A new mode starts under the
  filtered class only when that class is active.
- The cause group is a required select, and the group filter works.
- The store adds three refs, `ensureX()` and the `resetMasters()` clearing, with vitest
  coverage of paths, cache and reset.
- No business logic in the frontend.

**Tests against brief § 8:**
- pure:
  - code accept and refuse lists;
  - label and description boundaries;
  - the five groups;
  - class optional or null.
- API:
  - each editor role creates, edits, deactivates and reactivates in each list;
  - operator, technician, supervisor and storekeeper read and get 403;
  - the class filter, `include_inactive`, class fixed (400), inactive class at create and at
    reactivation (409), unknown class (400);
  - all four mode-label cases plus the inactive-row and rename cases;
  - duplicate code on POST and PUT in each list, duplicate cause and action label, seed
    codes taken;
  - the orderings.
- Migration: tables, keys, FK, seed counts and groups, and a double re-run that keeps an
  edited seed row, restored in `finally`.
- Isolation:
  - the session clean-up deletes only non-seed rows;
  - `Uniq.failure_code()` gives `T0001`-style codes that fit the code rule, and
    `Uniq.failure_label()` gives unique labels.

**Report:**
- Every file touched is listed.
- The ten decisions cover the real choices: the shared helpers, the clash message naming
  the row, the label check only when `label` is sent, the unfiltered unknown class, the
  seed descriptions, and the ISO check done from memory.
- The re-run-after-code-edit gap is stated honestly under "Not done". It is acceptable: it
  needs a half-applied v11 plus an edit in between.
- I found no unreported departure.

**Docs:** the planner's Plan.MD § 3 / § 4.2 / § 5 and the Maintenance-Philosophy glossary
entries for this step are already in the tree.

**Track:** full, so no track finding applies.
