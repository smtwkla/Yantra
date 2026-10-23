Step: S030 — Equipment lifecycle (rename of the register's "status")
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 23-10-2026

# S030 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The rename is complete and correct, v25 is safe at
every crash point, and every suite I ran is green, the targeted e2e specs included. Four nits.

Reviewed: the working-tree diff against `4a13de5` (`git diff -w --ignore-cr-at-eol`), the new
`backend/tests/test_migration_v25.py`, and in full where the hunks were not enough:
`local_db.py` (v25, `_v25_shape_check`, `init_db`), `equipment_core.py`, `EquipmentFormModal.vue`
(the body it sends), `stores/notifications.js`, `App.vue`, `NotificationsView.vue` and
`e2e/support/console.js` (for the WebKit failure).

## Tests run

- **`YANTRA_TEST_RUN=s030cr1 tooling/run-tests.bat`: all four suites pass.** Backend 2325 passed,
  frontend 119, deps 42, tooling 106.
- **e2e, targeted**: `tooling/run-e2e-tests.bat e2e/equipment.spec.js e2e/asset-list.spec.js
  e2e/screens.spec.js`. Why these: `equipment` and `asset-list` are the specs of the screens S030
  changed; `screens` is always run. S030 changes no shared frontend code (`FormModal.vue`,
  `useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`), so the full suite is not
  needed for this review. Result: **63 passed, 0 failed** (82 s; phone Chromium, phone WebKit and
  desktop Chromium). The new S030 test, the changed S003 test and the changed asset-list test pass
  on all three projects.
- The coder ran the full e2e suite (brief § 7.2 asks for it, because the seed changes). That run
  covers `labels` and `tickets-raise`, which read the renamed field.

## The WebKit failure in the coder's full run

**Judgement: a flake, not an S030 fault.** Reasons:

- The failing request is `GET /api/push/subscriptions` (S021). `App.vue:33-35` starts it after
  login. S030 does not touch it, the notifications store, or the push API.
- Both callers catch the error: `App.vue:34` (`.catch(() => {})`) and `NotificationsView.vue:31-35`.
  "… due to access control checks" is WebKit's own text for a fetch cut off when the page changes.
  `screens.spec.js` changes the page quickly, so the request is sometimes still open.
- The coder's rerun of `screens.spec.js` passed 24 of 24. My run passed all 8 `screens.spec.js`
  tests on phone WebKit, "every screen opens as manager" included.

It is outside S030's scope. If it comes back, it belongs to a tidy-up of S021 or S024: for example,
`watchConsole` could allow this one WebKit line for the push calls, as `allowBrowserError` already
does for Chrome's incognito push line.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `docs/steps/S030-equipment-lifecycle/3-impl-report.md:132`: "No departure from
  the brief." contradicts items 1, 2 and 4 above it, which are small departures from brief § 3.2 and
  § 7.1. Write "Items 1, 2 and 4 depart from the brief's file list and test list; nothing departs
  from its design."
- **CR1-02** (nit) `backend/tests/test_migration_v25.py:102-111`: the half-applied case covers a
  crash after the `RENAME` only. A crash after step 1 or step 2 is also safe by reading the SQL;
  one parametrised case per crash point (run the first *n* statements, then v25) would prove it.
- **CR1-03** (nit) `backend/tests/test_migration_v25.py:108-111`: the half-applied re-run checks the
  event names only. Compare the rows with `events_before` (with the event renamed), as
  `test_a_v24_database_with_equipment_and_history_gets_v25` does, so a lost `old_value` would show.
- **CR1-04** (nit, outside S030's scope; for the planner) `frontend/src/views/masters/*Panel.vue`
  (e.g. `SitesPanel.vue:60`, `ModelsPanel.vue:136`): the masters tables still head their
  active / inactive column *Status*. The glossary now reserves *Status* for the machine's
  maintenance status (`Maintenance-Philosophy.md` § 12). Consider *Active* there, in the queued
  tidy-up.

## The coder's departures

1. **`test_migration_v9.py` changed: correct.** `test_the_shape_holds` asserts today's schema (its
   docstring says so), so it must follow v25. The frozen `fixtures/migrations_v13.py` and v20's
   text are unchanged (checked).
2. **`machineParts.test.js` fixture values: correct.** `"active"` was never a lifecycle value. The
   test's meaning is the same: only `scrapped` rows are left out.
3. **Extra half-applied re-run case: welcome.** It is the case § 4.1 describes, and it also proves
   that the precondition passes with `lifecycle` alone. See CR1-02 and CR1-03 for two small gaps.

Items 3, 5 and 6 of "Decisions taken" are choices inside the brief, not departures.

## Manual checks

The impl report's `## Manual checks` carries the brief's one important check as `[auto]`, with the
test `equipment.spec.js`::`S030: the lifecycle is named Lifecycle on the form, the page, the list
and the history`. The test asserts what the user sees: the header *Lifecycle*, *Any lifecycle*,
*In service* chosen, the dialog title, the badge *Standby*, the history line, and no *Status* in the
two dialogs and the list's `thead`. It calls `expectDialogFits` on both dialogs. The brief has no
real-device checks, so no rows go to `device-checks.md`.

**For the user's manual browser check:** nothing is required. Optionally, open an equipment page on
a phone and check that *Change lifecycle* still fits beside *Move* on one line.

## Checked and found consistent

- **v25 statement order.** `RENAME COLUMN IF EXISTS`, then the `MODIFY` that allows both names, the
  `UPDATE`, and the `MODIFY` that drops `'status'` (`local_db.py:719-731`). No row holds `'status'`
  when it is dropped, in strict or non-strict mode. The final ENUM keeps `'lifecycle'` where
  `'status'` was.
- **Re-run safety at every crash point** (DDL is not transactional; the version is recorded last):
  - after the rename: the rename skips on the re-run, and the rest runs;
  - after step 1: step 1 is a no-op, and the rest runs;
  - after step 2: steps 1 and 2 are no-ops, and step 3 runs;
  - after step 3: step 1 re-adds `'status'`, step 2 updates no row, and step 3 drops it again.
- **`_v25_shape_check`** (`local_db.py:774-795`). An absent table passes, so a fresh database runs
  v20-v25 in one go. `status` alone or `lifecycle` alone passes. Both, or neither, is refused with
  the brief's texts. It reads `information_schema` with `TABLE_SCHEMA = DATABASE()`, as
  `_old_tables_for_v20` does. It is registered in `_PRECONDITIONS` (`local_db.py:799`), which
  `init_db` checks for every pending version before it applies any.
- **`test_migration_v25.py`** covers brief § 7.1 tests 1-4. The tests go through `init_db`
  (`_migrate`), so the precondition really runs. The production-path test compares every
  equipment column and every event row before and after, not only the renamed ones. The refusal
  tests assert that the schema and the rows are unchanged and that `db_version` has no 25.
- **Completeness.** A grep of `backend`, `tooling`, `frontend/src`, `frontend/tests` and
  `frontend/e2e` finds no equipment `status` left. What remains is correct:
  - the `_REFUSED_FIELDS` entry and its docstring;
  - `equipment_core.py:150` (an HTTP status);
  - ticket `state`, `task_queue.status`, push and HTTP statuses, and Settings' DB status;
  - the frozen `fixtures/migrations_v13.py` and v20's own text.
  The dev seed sends no `status`; the e2e seed sends `lifecycle`.
- **`_REFUSED_FIELDS`.** `status` is refused with "This field is now called Lifecycle. Reload the
  page." (`equipment_core.py:210`). The core test adds it to the refused-fields table (null, a
  number and a text). The API test refuses it on a `PUT` (the node stays `in_service`, no event) and
  on an otherwise valid `POST` (`field: "status"` is the only error, no row).
- **The current bundle never sends `status`.** The edit form's `fromRecord` holds no lifecycle,
  the create form and the change dialog send `lifecycle`, and the e2e helpers send neither.
- **API.** Every SELECT, `LOCK_EQUIPMENT`, `_summary`, `_child_rows`, the labels query, the
  removed-documents union, the raise checks and `_locked_node_of_machine` read `lifecycle`. The
  409 refusals name `field: "lifecycle"`. `?lifecycle=` uses `enum_arg` with `LIFECYCLES`; an old
  `?status=` is ignored, as D4 decides.
- **Pure core and thin shell.** The rule (`check_lifecycle_change`) and the refusals stay in
  `equipment_core.py`. The routes are unchanged apart from the names. The SQL still takes every
  value as a parameter; the only text built into it is the list of `%s` placeholders, as before.
- **Screen texts against brief § 1 and § 4.3**: the label *Lifecycle* (add dialog and change dialog),
  the button *Change lifecycle*, the title "Change lifecycle of {code}", the column *Lifecycle* (list
  and print), the filter *Any lifecycle* with `aria-label` *Lifecycle*, the history line
  "Lifecycle: …", the print filter line "Lifecycle: …", the help "(Yantra lifecycle stage)", and the
  refusal "Scrapped is final. The lifecycle cannot change." All match, and all follow scope B.
- **Renamed components.** `LifecycleBadge.vue` and `EquipmentLifecycleModal.vue` are moved with git
  (`RM` in `git status`); every import is updated. The change dialog keeps its Yes / No confirm for
  scrapping and its `btn-danger` Yes.
- **Docs** (§ 3.5, § 9). `Plan.MD` and the glossary rows in `Maintenance-Philosophy.md` § 12 match
  the brief. The README index row is present.
- **Track.** Full, as the brief says.
