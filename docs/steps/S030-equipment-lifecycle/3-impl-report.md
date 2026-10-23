Step: S030 — Equipment lifecycle (rename of the register's "status")
Doc: impl-report
Author: Coder (Opus)
Date: 23-10-2026

# S030 — Implementation report

**Result:** the equipment register field *Status* is now *Lifecycle* in the database (v25), the
API, the code and the screens. Backend, frontend, deps and tooling suites pass (2325 / 119 / 42 /
106). The full e2e suite: 248 passed, 6 skipped, 1 failed. The one failure is a WebKit flake in the S021 push call. The rerun of its spec passed (§ 6).

## 1. What was built

- **Migration v25** renames `equipment.status` to `equipment.lifecycle` and the history event
  `status` to `lifecycle` on every existing row, exactly as brief § 4.1 gives it. Its
  precondition `_v25_shape_check` refuses a hand-edited `equipment` table with both columns or
  neither; an absent table passes (§ 4.2).
- **The API says `lifecycle`**: the list, the node, the parts tree, the asset list, the labels
  query, the removed-documents list, and the `?lifecycle=` filter. Refusals about the field name
  `field: "lifecycle"` (scrapping with live parts, scrapping with open tickets, a create as
  scrapped).
- **An old tab is refused loudly.** A `POST` or `PUT` body with `status` answers 400,
  `field: "status"`, "This field is now called Lifecycle. Reload the page." (§ 4.4).
- **The screens say *Lifecycle*** in the places of brief § 1: the add / edit dialog, the button
  *Change lifecycle*, the dialog title "Change lifecycle of {code}", the list column and its
  filter (*Any lifecycle*, `aria-label` *Lifecycle*), the history line "Lifecycle: In service →
  Standby", the printed asset list column and filter line, the help texts "(Yantra lifecycle
  stage)", and the refusal "Scrapped is final. The lifecycle cannot change."

## 2. How it works

- **v25** (`local_db.py`) runs four statements: `RENAME COLUMN IF EXISTS`, then a `MODIFY` that
  allows both event names, an `UPDATE` of the rows, and a `MODIFY` that drops `status`. The
  order means no row holds `status` when it is dropped, in strict and non-strict SQL mode. Each
  statement is safe to run twice.
- **`_v25_shape_check`** reads `information_schema.TABLES`, then `COLUMNS`, with
  `TABLE_SCHEMA = DATABASE()`, as `_old_tables_for_v20` does. `init_db` checks it with every
  pending version before it applies any, so a refusal changes nothing and shows in
  Settings › Database.
- **Pure core** (`equipment_core.py`): `LIFECYCLES`, `check_lifecycle_change`, the `_TRACKED`
  entry `("lifecycle", "lifecycle")`, the parser entry, and `status` in `_REFUSED_FIELDS`.
  `validate_equipment` checks the refused fields first, so for a body that is otherwise valid
  the 400 names `status`.
- **Shell**: every SQL read of the column and every dict key is renamed (`equipment.py`,
  `documents.py`, `tickets.py`, `masters.py`; `labels_core.py` and `asset_list_core.py` read
  the key). `enum_arg("lifecycle", LIFECYCLES)` reads the filter; an old `?status=` is an
  unknown key and is ignored, as brief D4 says.
- **Frontend**: the maps are `LIFECYCLE_LABELS` / `LIFECYCLE_HELP` / `LIFECYCLE_BADGE_CLASS`;
  `describeEvent` has the case `lifecycle`. `StatusBadge.vue` and `EquipmentStatusModal.vue`
  were moved with `git mv` to `LifecycleBadge.vue` (prop `lifecycle`) and
  `EquipmentLifecycleModal.vue`.

## 3. Files touched

Backend (8):

| File | Change |
|---|---|
| `backend/local_db.py` | migration v25 with its comment; `_v25_shape_check`; `_PRECONDITIONS` gains 25 |
| `backend/equipment_core.py` | `LIFECYCLES`, `check_lifecycle_change` and its new message, `_TRACKED`, parser, create check, `status` in `_REFUSED_FIELDS`, docstrings |
| `backend/equipment.py` | the SELECT lists, `LOCK_EQUIPMENT`, `_summary`, `_child_rows`, `_list_filters`, the parts and ticket checks (`field "lifecycle"`), labels query, update's scrapped checks |
| `backend/documents.py` | scrapped checks; the removed-documents union (`e.lifecycle`, `NULL AS lifecycle`) |
| `backend/tickets.py` | raise's scrapped checks; the locked node read |
| `backend/masters.py` | unit deactivation count |
| `backend/labels_core.py` | `lifecycle` key and docstring |
| `backend/asset_list_core.py` | `lifecycle` key and docstring |

Backend tests (15):

| File | Change |
|---|---|
| `backend/tests/test_migration_v25.py` | new: fresh database, v24 with history, re-run (full and half-applied), the two refusals |
| `backend/tests/test_equipment_core.py` | `TestCheckLifecycleChange`, `test_born_lifecycle`, `test_scrapped_is_a_valid_target_lifecycle_on_update`, tracked-changes rows; `status` added to the refused-fields table |
| `backend/tests/test_equipment_api.py` | `TestLifecycle` with the new `test_the_old_status_field_is_refused`; every body, row, event name and filter; docstring |
| `backend/tests/test_asset_list_api.py` | `test_class_lifecycle_criticality`, `lifecycle=` queries, bad value names `lifecycle` |
| `backend/tests/test_site_checks_api.py` | `{"lifecycle": "standby"}`; `test_lifecycle_notes_model_at_b` |
| `backend/tests/test_migration_v9.py` | today's event ENUM says `lifecycle` (see § 4, item 1) |
| `backend/tests/test_asset_list_core.py`, `test_labels_core.py` | the fixture rows' key |
| `backend/tests/test_labels_api.py`, `test_masters_api.py`, `test_tickets_api.py`, `test_ticket_parts_api.py`, `test_ticket_work_api.py`, `test_removed_documents_api.py`, `documents_helpers.py` | the equipment field only; HTTP statuses, ticket `state` and `task_queue.status` unchanged |

Frontend (13):

| File | Change |
|---|---|
| `frontend/src/utils/equipmentLabels.js` | renamed maps, help texts, `describeEvent` case, comment |
| `frontend/src/components/LifecycleBadge.vue` | `git mv` from `StatusBadge.vue`; prop `lifecycle` |
| `frontend/src/views/equipment/EquipmentLifecycleModal.vue` | `git mv` from `EquipmentStatusModal.vue`; `form.lifecycle`, `fieldError('lifecycle')`, `id="lifecycle-choice"`, title, label |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | `CREATE_LIFECYCLES`, both blanks, label and `id="eq-lifecycle"`, `fieldError('lifecycle')`, header comment |
| `frontend/src/views/EquipmentDetailView.vue` | badge, `lifecycleModal`, button *Change lifecycle*, `node.lifecycle` |
| `frontend/src/views/EquipmentView.vue` | filter (`lifecycleModel`, `chooseLifecycle`, `lifecycleChoices`, *Any lifecycle*), URL keys, column, badge, row checks, comments |
| `frontend/src/views/equipment/PartsTree.vue` | badge and `part.lifecycle` |
| `frontend/src/views/AssetListPrintView.vue` | `lifecycleText`, column *Lifecycle* |
| `frontend/src/utils/assetList.js` | `FILTER_KEYS`, `params.lifecycle`, filter line "Lifecycle: …" |
| `frontend/src/utils/machineParts.js` | `child.lifecycle` |
| `frontend/src/views/RaiseTicketView.vue` | `lifecycle` (two lines) |
| `frontend/src/views/settings/RemovedDocuments.vue` | `item.lifecycle` (two lines) |
| `frontend/src/components/documents/DocumentsCards.vue` | comment only |

Frontend tests, e2e and seed (6):

| File | Change |
|---|---|
| `frontend/tests/equipmentLabels.test.js` | renamed maps; "Lifecycle: In service → Standby" |
| `frontend/tests/assetList.test.js` | `lifecycle` params and "Lifecycle: …" lines |
| `frontend/tests/machineParts.test.js` | `lifecycle` in the fixture rows |
| `frontend/e2e/equipment.spec.js` | S003 test: *Change lifecycle*, label *Lifecycle*, title; header comment; new S030 test |
| `frontend/e2e/asset-list.spec.js` | `/asset-list?lifecycle=out_of_use` |
| `tooling/e2e/seed_e2e.py` | `{"lifecycle": "scrapped"}` |

Step files: `1-brief.md` (status only), `docs/steps/README.md` (index row), this report. The docs
of brief § 3.5 were not touched.

## 4. Decisions taken

1. **`test_migration_v9.py` changed (not in brief § 3.2).** Its `test_the_shape_holds` checks
   *today's* schema (its docstring says so), and asserted the event ENUM with `status`. The full
   run failed on it; it now expects `lifecycle`. This is a test of the current schema, not a
   frozen fixture, so it follows v25. The frozen `fixtures/migrations_v13.py` and v20's text
   are unchanged.
2. **`machineParts.test.js` fixture values.** The rows had `status: "active"`, which is not a
   lifecycle value. They now say `lifecycle: "in_service"` (and `"scrapped"` where they were).
   The test's meaning is unchanged: only `scrapped` is left out.
3. **The two refusal tests share a helper** (`_refused_unchanged` in `test_migration_v25.py`);
   the test names are the brief's.
4. **The re-run test also covers a half-applied v25**: only the `RENAME` run, then v25 in full.
   The brief's test 3 asks for a re-run; the half-applied case is the one § 4.1 describes.
5. **`validate_equipment`'s docstring and the `_REFUSED_FIELDS` comment** name S030 § 4.4,
   beside S012 § 5.4.
6. **The S030 e2e test checks "no *Status*"** with the case-sensitive whole word `\bStatus\b`
   inside the two dialogs and the list's `thead`, as BR1-09 scopes it.

No departure from the brief.

## 5. Not done, deferred or assumed

- **Docs** (§ 3.5) and old step briefs: not touched, as instructed.
- **Assumption (brief § 8 item 1):** production's `equipment_events` is small, so the rebuild in
  v25's last statement is instant. To check with a count on production before the release.
- **Release note (brief § 6):** v25 is not backward compatible; a rollback restores the nightly
  dump. Bookmarks with `?status=` show the list unfiltered.
- `equipment_core.py:150` keeps "the shell picks the status (409)": that is an HTTP status. It is
  the only other `status` in `backend/equipment*.py` besides the `_REFUSED_FIELDS` entry and its
  docstring (acceptance § 7.4).

## 6. Tests run

- Targeted while coding: `test_migration_v25.py`, `test_equipment_core.py` (142 passed), the
  twelve API test files (744 passed), frontend unit tests (119 passed), the S030 e2e test alone
  on desktop-chromium (1 passed).
- Final full run, `YANTRA_TEST_RUN=s030c1 tooling/run-tests.bat`: backend 2325 passed, frontend
  119 passed, deps 42 passed, tooling 106 passed. (The first full run had 1 failure,
  `test_migration_v9.py::test_the_shape_holds`, fixed as § 4 item 1 says.)
- `npx vite build`: built, no new warnings.
- **e2e, full suite** (brief § 7.2: the seed and several specs change): `tooling/run-e2e-tests.bat`, 6 lanes, 255 tests in 222 s:
  248 passed, 6 skipped (the suite's existing skips), 1 failed.
  - The failure: `[phone-webkit] screens.spec.js` "every screen opens as manager". The console
    watch caught "uncaught error: /127.0.0.1:5183/api/push/subscriptions due to access control
    checks". This is WebKit's text for a request cut off by a page change; the request is the
    S021 push-subscription check, which S030 does not touch. **Fact:** a rerun of
    `e2e/screens.spec.js` on all three projects passed, 24 of 24. **Assumption:** the failure is
    a flake of S021's push call under WebKit, not an S030 fault. The code reviewer may want to
    note it as a flaky test.
  - The new S030 test and the changed S003 and asset-list tests passed on all three projects.

## Manual checks

- [auto] **important** The lifecycle is named *Lifecycle* on the add dialog (with *In service*
  chosen), the change dialog and its title, the equipment page badge, the history line
  "Lifecycle: In service → Standby", the list column and the filter's *Any lifecycle*; no
  *Status* in the two dialogs or the list's header — `frontend/e2e/equipment.spec.js`::`S030: the
  lifecycle is named Lifecycle on the form, the page, the list and the history` (passed on
  phone-chromium, phone-webkit and desktop-chromium in the full run).

No real-device checks (brief § 7.3); no rows added to `device-checks.md`.

## Fix rounds
