Step: S030 — Equipment lifecycle (rename of the register's "status")
Doc: brief
Author: Planner (Opus)
Date: 23-10-2026
Track: full
Baseline: 4a13de5
Status: Gate B (CR r1: 0 blocker, 0 major, 0 minor, 4 nits; approved 23-10-2026 by KLA; backup before release: not needed)

# S030 — Equipment lifecycle

**The request (KLA, 23-10-2026).** The add-equipment form has a field *Status* (in service,
standby, out of use, scrapped). The word *status* fits better for whether a machine is down,
working, degraded or needs PM. Rename the field now, or find a new word for the maintenance
meaning ("condition"?).

**Decided with the user before this brief (23-10-2026):**

- **U1.** The register field becomes **Lifecycle**. *Status* is kept free for the machine's
  maintenance status (down, working, degraded, PM due), which Yantra derives and never takes
  as typed input. *Condition* was not used: in EN 13306 and in Yantra it already means measured
  health (condition monitoring, condition-based maintenance, "fit with conditions").
- **U2.** **Full rename now**: the screens, the API, the code, the database column and the
  history event all say *lifecycle*, so one thing has one name (CLAUDE-COMMON writing rule 4).

**Track: full.** The step has a migration that renames a column and rewrites existing history
rows (light-track criterion 1), and it touches about 45 files.

**No split proposed** (skill § Size, more than 25 files). The rename cannot ship in halves: the
column, the API field and the screens must change together, or the app breaks between the two
halves. Almost every change is the same mechanical substitution.

## 1. What will be built

- **The field is called *Lifecycle* everywhere a user sees it.** The values stay as they are:
  *In service*, *Standby*, *Out of use*, *Scrapped*.

  | Place | Today | After S030 |
  |---|---|---|
  | Add / edit equipment dialog (`EquipmentFormModal.vue`) | label *Status* | label *Lifecycle* |
  | Equipment page button | *Change status* | *Change lifecycle* |
  | Change dialog (`EquipmentStatusModal.vue` → `EquipmentLifecycleModal.vue`) | title "Change status of {code}", label *Status* | title "Change lifecycle of {code}", label *Lifecycle* |
  | Equipment list (`/equipment`) column | *Status* | *Lifecycle* |
  | Equipment list filter | first choice *All statuses*, `aria-label` *Status* | *Any lifecycle*, `aria-label` *Lifecycle* |
  | Equipment history line | "Status: In service → Standby" | "Lifecycle: In service → Standby" |
  | Printed asset list column and filter line | *Status*, "Status: In service" | *Lifecycle*, "Lifecycle: In service" |
  | Help under the choice (`STATUS_HELP`) | "… (Yantra life-cycle status)." | "… (Yantra lifecycle stage)." |
  | Refusal (`check_status_change`) | "Scrapped is final; the status cannot change" | "Scrapped is final. The lifecycle cannot change." |

- **The API says `lifecycle`.** `GET /api/equipment`, `GET /api/equipment/<id>`,
  `GET /api/equipment/by-code/<code>`, the parts tree, the asset list and the documents lists
  return `lifecycle` instead of `status`. `POST /api/equipment` and
  `PUT /api/equipment/<id>` take `lifecycle`. The list and asset-list filter is
  `?lifecycle=<value>`. A refusal about the field names `field: "lifecycle"`.
- **The database says `lifecycle`.** Migration **v25** renames `equipment.status` to
  `equipment.lifecycle` and the history event `status` to `lifecycle` on every existing row
  (§ 4.1).
- **The glossary reserves *Status*.** `docs/Maintenance-Philosophy.md` § 12 gains two rows:
  *Lifecycle* and *Status* (§ 9).

**Out of scope:**

- Building the maintenance status itself (down / working / degraded / PM due). S029's ticket
  light is its first form; PM due comes with phase 4. A later step may rename the S029
  *Tickets* column to *Status*.
- New lifecycle values (for example *commissioning* or *spare in store*).
- Accepting the old `status` field or `?status=` query as an alias (§ 4.4, D4).
- Old step briefs, reviews and reports: they are the record of their time and keep *status*.
- Ticket `state` and every HTTP `status` in the code: they are different things and stay.

## 2. Standards and practice

- **ISO 55000 — asset life cycle.** ISO 55000:2014 § 3.2 defines *life cycle* as the
  "stages involved in the management of an asset". It leaves the names and number of the
  stages to the organisation (*asset life*, beside it, is the period from creation to end of
  life). So Yantra's four stages, in service, standby, out of use and scrapped, are within
  the standard, not a departure from it. (ISO 55000 was revised in 2024; the 2014 text is the
  one cited.) S003 § 2 already called these values "Yantra's life-cycle statuses"; S030 makes
  that the field's name.
- **EN 13306 — states.** EN 13306:2017 § 6 (item states) separates whether an item *can* do
  its job (**up state** / **down state**) from how it is used while up (**operating**,
  **idle**, **standby** state). *In service* is Yantra's word for operating or idle. The
  machine's maintenance status that U1 reserves is the up / down side. It comes from tickets (S029) and later from PM, never from a field typed by hand (S003
  BR1-04). The lifecycle field holds the use side plus the two Yantra stages *out of use* and
  *scrapped*.
- **Why not *condition*.** EN 13306 uses *condition* for the measured health of an item:
  *condition monitoring*, *condition-based maintenance*. Yantra uses it the same way (oil
  analysis and gauge limits, Maintenance-Philosophy § 7; the inspection outcome "fit with
  conditions"). Using it for down / working would give one word two meanings.
- **ISO 55001 § 7.6, ISO 9001 § 7.5 — documented information.** The equipment history
  must stay complete and traceable. v25 renames the *kind* of each history row from `status`
  to `lifecycle`; its old value, new value, time and author stay as recorded. The meaning of
  every row is unchanged, so this is a rename of a label, not a change of the record (D3).
- **CLAUDE-COMMON writing rule 4 — one term for one thing.** One word per meaning, in the
  screens and in the code.

## 3. Where

About 45 files. Most changes replace `status` with `lifecycle` (or `STATUSES` with
`LIFECYCLES`, and so on) where the name means the equipment field.

### 3.1 Backend

| File | Change |
|---|---|
| `backend/local_db.py` | migration v25 (§ 4.1) and its precondition `_v25_shape_check` in `_PRECONDITIONS` (§ 4.2). v20's text is not edited. |
| `backend/equipment_core.py` | `"status"` added to `_REFUSED_FIELDS` (§ 4.4); `STATUSES` → `LIFECYCLES`; `check_status_change` → `check_lifecycle_change` with the new message (§ 1); `_TRACKED` entry `("status", "status")` → `("lifecycle", "lifecycle")`; the parser entry `"status": (_enum_parser("Status", STATUSES), False)` → `"lifecycle": (_enum_parser("Lifecycle", LIFECYCLES), False)`; the create check at line 311–314 uses `lifecycle` and `field: "lifecycle"`. Docstrings that say status say lifecycle. |
| `backend/equipment.py` | every `e.status`, `ch.status`, `status` in the SELECT lists, `LOCK_EQUIPMENT`, the row dict at line 228, `_list_filters` (`enum_arg("lifecycle", LIFECYCLES)`, `e.lifecycle = %s`, `e.lifecycle <> 'scrapped'`), the parts checks at lines 411–419 and the `ApiError(…, 409, "lifecycle")` fields at lines 419 and 435, lines 331, 632, 735, 753. |
| `backend/documents.py` | lines 116, 125 (`node["lifecycle"]`, `locked["lifecycle"]`), the documents union at lines 446, 452, 459 (`e.lifecycle`, `NULL AS lifecycle`). |
| `backend/tickets.py` | lines 741, 752–754, 1069–1072: `lifecycle` in the SELECT and the scrapped checks. |
| `backend/masters.py` | line 293: `lifecycle <> 'scrapped'`; the comment at line 291. |
| `backend/labels_core.py` | line 114 docstring and line 127 (`c["lifecycle"]`). |
| `backend/asset_list_core.py` | lines 23 and 31. |

### 3.2 Backend tests

| File | Change |
|---|---|
| `backend/tests/test_migration_v25.py` | new (§ 7.1). |
| `backend/tests/test_equipment_core.py` | `TestCheckStatusChange` → `TestCheckLifecycleChange`; `test_born_status`, `test_scrapped_is_a_valid_target_status_on_update` and every `"status"` field use `lifecycle`. |
| `backend/tests/test_equipment_api.py` | `TestStatus` → `TestLifecycle`, `test_a_part_has_its_own_status`, `TestListing::test_site_unit_class_and_status_filters` (`?lifecycle=`), `TestListing::test_row_fields`, and every body or row with `status` (about 50 lines). |
| `backend/tests/test_asset_list_api.py` | `test_class_status_criticality` and the `status=` queries. |
| `backend/tests/test_site_checks_api.py` | lines 54–56: `{"lifecycle": "standby"}`; `test_status_notes_model_at_b` → `test_lifecycle_notes_model_at_b` (BR1-04). |
| `backend/tests/test_asset_list_core.py`, `test_labels_api.py`, `test_labels_core.py`, `test_masters_api.py`, `test_removed_documents_api.py`, `test_tickets_api.py`, `test_ticket_parts_api.py`, `test_ticket_work_api.py`, `documents_helpers.py` | the equipment `status` uses only (to verify per line: these files also hold HTTP `status` and ticket `state`, which stay). |

`conftest.py` `_TABLES` does not change (no new table). The `test_migration_v20` … `v24`
tests select their own versions from `_MIGRATIONS` (`test_migration_v24.py:12-13`), so v25
does not change them. `test_role_matrix` does not change (no new key or route).

### 3.3 Frontend

| File | Change |
|---|---|
| `frontend/src/utils/equipmentLabels.js` | `STATUS_LABELS` / `STATUS_HELP` / `STATUS_BADGE_CLASS` → `LIFECYCLE_LABELS` / `LIFECYCLE_HELP` / `LIFECYCLE_BADGE_CLASS`; the help texts (§ 1); `describeEvent` case `"lifecycle"` with the word *Lifecycle* (§ 4.3). |
| `frontend/src/components/StatusBadge.vue` | renamed `LifecycleBadge.vue` (`git mv`), prop `lifecycle`. |
| `frontend/src/views/equipment/EquipmentStatusModal.vue` | renamed `EquipmentLifecycleModal.vue` (`git mv`); `form.lifecycle`, `fieldError('lifecycle')`, `id="lifecycle-choice"`, title and label (§ 1). |
| `frontend/src/views/equipment/EquipmentFormModal.vue` | `CREATE_LIFECYCLES`, `lifecycle: "in_service"` in both blanks, label and `id="eq-lifecycle"`, `fieldError('lifecycle')`; comment at line 8. |
| `frontend/src/views/EquipmentDetailView.vue` | badge, `lifecycleModal`, the button *Change lifecycle*, `node.lifecycle`. |
| `frontend/src/views/EquipmentView.vue` | filter (`lifecycleModel`, `chooseLifecycle`, `lifecycleChoices`), `?lifecycle=` in the URL keys (line 157), column header, badge, `e.lifecycle` (lines 340, 353, 362), the comments at lines 56 and 115. |
| `frontend/src/views/equipment/PartsTree.vue` | badge and `part.lifecycle`. |
| `frontend/src/views/AssetListPrintView.vue` | `lifecycleText`, column *Lifecycle*. |
| `frontend/src/utils/assetList.js` | `FILTER_KEYS` `lifecycle`; `params.lifecycle === "scrapped"`; filter line "Lifecycle: …". |
| `frontend/src/utils/machineParts.js` | `child.lifecycle`. |
| `frontend/src/views/RaiseTicketView.vue` | lines 74 and 91: `lifecycle`. |
| `frontend/src/views/settings/RemovedDocuments.vue` | lines 84 and 194: `item.lifecycle`. |
| `frontend/src/components/documents/DocumentsCards.vue` | comment at line 36 only ("whatever the node's lifecycle"). |

Comments to update besides those above (BR1-10): `equipmentLabels.js:13`,
`test_equipment_api.py:1`, `equipment.py:470`, the `tracked_changes` docstring
(`equipment_core.py:180`).

### 3.4 Frontend tests, e2e and seed

| File | Change |
|---|---|
| `frontend/tests/equipmentLabels.test.js` | the renamed maps; the event test "Lifecycle: In service → Standby". |
| `frontend/tests/assetList.test.js` | `lifecycle` params and "Lifecycle: …" lines. |
| `frontend/tests/machineParts.test.js` | `lifecycle` in the fixture rows. |
| `frontend/e2e/equipment.spec.js` | S003 test (line 74–87): button *Change lifecycle*, label *Lifecycle*; the header comment; a new S030 test (§ 7.2). |
| `frontend/e2e/asset-list.spec.js` | line 68: `/asset-list?lifecycle=out_of_use`. |
| `tooling/e2e/seed_e2e.py` | line 126: `{"lifecycle": "scrapped"}`. |

### 3.5 Docs

Done by the planner at approval (23-10-2026); the coder does not change them.

| File | Change |
|---|---|
| `docs/Plan.MD` | line 235 (equipment fields: *lifecycle*), line 773 (`equipment_events`: change of lifecycle), at approval. |
| `docs/Maintenance-Philosophy.md` | § 12 glossary: rows *Lifecycle* and *Status* (§ 9). |

## 4. Design

### 4.1 Migration v25

```python
(25, "Equipment lifecycle: status renamed (S030)", [
    "ALTER TABLE equipment RENAME COLUMN IF EXISTS status TO lifecycle",
    # 1. Allow both names, so existing rows stay valid (safe to re-run; values kept by name)
    """ALTER TABLE equipment_events MODIFY event
        ENUM('created','moved_unit','moved_parent','status','criticality','class','type','model','lifecycle')
        NOT NULL""",
    # 2. Rename the event on every existing row
    "UPDATE equipment_events SET event = 'lifecycle' WHERE event = 'status'",
    # 3. Drop the old name; no row holds it now
    """ALTER TABLE equipment_events MODIFY event
        ENUM('created','moved_unit','moved_parent','lifecycle','criticality','class','type','model')
        NOT NULL""",
]),
```

- **The column keeps its type, default and place**:
  `ENUM('in_service','standby','out_of_use','scrapped') NOT NULL DEFAULT 'in_service'`.
  `RENAME COLUMN` changes only the name. Run result (dev MariaDB 11.4, scratch database,
  23-10-2026): after `RENAME COLUMN IF EXISTS status TO lifecycle`, `SHOW CREATE TABLE` shows
  `lifecycle enum('a','b') NOT NULL DEFAULT 'a'` with the row's value kept; a second run of the
  same statement is a no-op, not an error. `RENAME COLUMN IF EXISTS` needs MariaDB 10.5.2 or
  later; production already needs 10.6 for S013's `SKIP LOCKED`, so it holds (BR1-07).
- **The order of the three event statements protects the history.** Run result (same scratch
  database): with `sql_mode = ''`, a `MODIFY` that drops an ENUM value in use silently turns
  the rows' value into `''`. In strict mode (dev's `@@sql_mode` is
  `STRICT_TRANS_TABLES,…`) the `MODIFY` fails instead. Step 2 runs before step 3, so no row
  holds `'status'` when step 3 drops it, in either mode. Production's `sql_mode` is to verify;
  the order makes it not matter.
- **Every statement is safe to run twice** (the `local_db` convention at lines 72–74: DDL is
  not transactional, and the version is recorded after the last statement). A half-applied
  v25 re-runs: the rename skips, step 1 re-adds `'status'` to the list, step 2 updates no row,
  step 3 drops it again.
- **Step 3 rebuilds `equipment_events`** (a value is removed from the middle of the list).
  The table is small (one row per change; hundreds today, to verify on production), so the
  copy takes well under a second.
- **v25 cannot run under the previous release, and the previous release cannot run on v25.**
  The previous image (v0.1.5) reads `e.status` and would return 500 on every equipment
  screen. This is the first release since v20 that is not backward compatible. Rollback
  after v25 is applied needs a database dump: `deploy.py`'s `rollback_lines`
  (`tooling/deploy.py:141-151`) says to restore db-server's latest dump first. That dump is the
  nightly one unless the user takes a fresh one before the deploy (§ 6, BR1-03).

### 4.2 Precondition `_v25_shape_check`

CLAUDE.md § SMTW-Review: a migration that touches rows existing in production carries a
`_PRECONDITIONS` entry and a test from the production schema. v25 refuses, and nothing is
applied, when the `equipment` table does not have exactly one of the two columns:

| `status` column | `lifecycle` column | Result |
|---|---|---|
| — (no `equipment` table) | — | go: an empty database; v20 creates the table with `status` and v25 renames it in the same run (BR1-01) |
| yes | no | go (the normal case) |
| no | yes | go (a half-applied v25: the rename ran, the events did not) |
| yes | yes | refuse: "equipment has both status and lifecycle columns; drop the one that is not in use first — S030 § 4.2" |
| no | no | refuse: "equipment has neither a status nor a lifecycle column — S030 § 4.2" |

Why: with both columns, the `RENAME` fails half-way; with neither, it is skipped and the app
fails on every equipment read. Both states come only from a hand edit, but the refusal shows
in Settings › Database instead of a crash loop. `init_db` checks the precondition of every
pending version before it applies any (`local_db.py:855-861`), so on an empty database the
check runs before v20 has created `equipment`: an absent table must pass, as in
`_old_tables_for_v20` ("A table that is absent passes", `local_db.py:721-722`). The check
reads `information_schema.TABLES` first, then `information_schema.COLUMNS`, both with
`TABLE_SCHEMA = DATABASE()`, as `_old_tables_for_v20` does (`local_db.py:715-732`). The
messages are developer text (Settings › Database, IT admin), so scope B does not apply.

### 4.3 Names in the code and the screens

| Thing | Name |
|---|---|
| Column, API field, event, query key, error field | `lifecycle` |
| Python constant and check | `LIFECYCLES`, `check_lifecycle_change` |
| JS maps | `LIFECYCLE_LABELS`, `LIFECYCLE_HELP`, `LIFECYCLE_BADGE_CLASS` |
| Components | `LifecycleBadge.vue`, `EquipmentLifecycleModal.vue` |
| UI word | *Lifecycle* (one word, as CMMS screens write it; ISO 55000 writes *life cycle*) |
| List filter's first choice | *Any lifecycle*, like *Any criticality* and *Any ticket status* beside it; "All lifecycles" reads oddly (BR1-08) |
| Values | unchanged: `in_service`, `standby`, `out_of_use`, `scrapped` |

### 4.4 Old clients and old links

- An open tab with the old bundle reads `status` and gets `undefined`. The stale-bundle check
  (SMTW-WebApp-Base § Stale bundle detection) already asks the user to reload after a deploy.
- A bookmarked `/equipment?status=standby` or `/asset-list?status=…` shows the list
  unfiltered after S030 (the unknown key is ignored, as today). The release notes say so (§ 6).
- A `POST` or `PUT` from an old tab with `status` in the body is **refused** (400,
  `field: "status"`): "This field is now called Lifecycle. Reload the page." The key joins
  `_REFUSED_FIELDS` (`equipment_core.py:200-208`), which S012 § 5.4 made for exactly this
  case: an old tab fails loudly instead of having its change ignored. Without it,
  `validate_equipment` would skip the unknown key (it parses only `_fields(…)`,
  `equipment_core.py:291-294`): the save would answer 200, the dialog would close, and the
  value would not change (BR1-02). The old tab shows the message beside its select
  (`fieldError('status')`).

### 4.5 Design decisions

| # | Decision | Why | Rejected alternative |
|---|---|---|---|
| D1 | The word *Lifecycle* (U1) | ISO 55000's term for the stages in the management of an asset, whose names it leaves to the organisation (§ 2); reads well with every value, also *Scrapped*; S003 already called the values life-cycle statuses | *Duty* (plant word for duty / standby pumps; "Duty: Scrapped" reads oddly); *Service state* (two words, and *state* is the ticket's word); *Condition* for the other meaning (EN 13306 uses it for measured health) |
| D2 | Full rename, database included (U2) | One name for one thing in screens and code; cheapest now, before PM plans, dashboards and KPIs read the field | Screen text only (no migration, light track): the code keeps `status`, which then means two things inside Yantra |
| D3 | Rewrite the history event name on old rows | One event name, one `describeEvent` case; the row's values, time and author are untouched, so the record keeps its meaning | Keep `status` on old rows and map both names in the UI: two names for one thing for good, and every later report must know both |
| D4 | No alias for the old `status` field or `?status=` query. The body field `status` is refused with a message, as S012 refuses `make` (§ 4.4); the query key is ignored, as every unknown key is | Only Yantra's own screens call the API; a stale tab must not lose a change silently; an alias would keep the old word alive in the code | Accept both names for a release: more code and tests for a few bookmarks. Ignore the old body field: a silent no-op on a save (BR1-02) |
| D5 | Plain rename migration, no expand-and-contract | ~50 users, one container, a few seconds of downtime at deploy; the dump covers rollback | Add `lifecycle`, keep `status` in step for a release, drop it later: three releases and sync code for a rename |
| D6 | Coder: **Opus** | The skill's rule: a migration that changes existing data (the history rows) | Sonnet: the rest is mechanical, but the migration and its precondition are the risk |

## 5. Edge cases

- **An empty database**: v20 creates `status`, v25 renames it at once. The tests and the e2e
  database take this path on every fresh run.
- **No history rows with `status`**: step 2 updates nothing; step 3 still runs.
- **A history row's `old_value` / `new_value`** hold the values (`in_service`, …), never the
  word *status*, so they stay as they are.
- **Equipment rows**: no value changes; only the column's name.
- **A node created in the same second as the deploy**: the migration runs under the
  migration lock before any request is served (`ensure_schema`), so no write sees a half
  state.
- **The DB unreachable at start**: unchanged; `ensure_schema` retries every 30 s, and a
  refusal by `_v25_shape_check` shows in Settings › Database (S025).

## 6. Notes for users (for the release notes, not built)

- "The equipment field *Status* is now called *Lifecycle*. Its values do not change. The word
  *status* is kept for whether a machine is down or working."
- "Bookmarks that filter the equipment list or the asset list by status show the full list
  now. Set the *Lifecycle* filter again and bookmark the page again."
- **For the release (user): no extra backup** (BR1-03, decided by the user at gate A,
  23-10-2026: "backup not needed"). The nightly dump on db-server covers a rollback. The
  previous release cannot run on the new schema, so a rollback restores the latest nightly
  dump (`deploy.py`'s `rollback_lines`) and loses every row written since it ran: tickets,
  notes and equipment changes (§ 4.1). If ever wanted, a fresh dump is
  `sudo systemctl start mariadb-dump.service` on db-server (a one-shot unit that returns when
  every database is dumped, `smtw_erp_devops/db_server/build_mariadb_backup.yaml:56-59`; the
  file `mariadb_dump_vel_yantra_master_<timestamp>.sql.gz` lands in `backup_mount_point`).

## 7. Tests

### 7.1 Backend

- **`test_migration_v25.py`** (new; upgrade database `UPGRADE_DB`, helpers `_recreate`,
  `_migrate`, `_run` from `test_migration_v20`, as `test_migration_v23.py` does):
  1. `test_a_fresh_database_gets_v25`: v20–v25 on an empty database, with no refusal by the
     precondition (BR1-01); `equipment` has
     `lifecycle` with type `enum('in_service','standby','out_of_use','scrapped')`, NOT NULL,
     default `'in_service'`, and no `status`; the event ENUM is the final list of § 4.1.
  2. `test_a_v24_database_with_equipment_and_history_gets_v25` (the production path): v20–v24,
     then one equipment row with `status = 'standby'` and events `created` and `status`
     (`in_service` → `standby`) inserted by SQL; after v25 the row's `lifecycle` is
     `standby`, the event row is `lifecycle` with the same `old_value`, `new_value`,
     `created_at`, `created_by` and `id`; the `created` row is unchanged.
  3. `test_a_rerun_changes_nothing`: running v25's statements a second time (a half-applied
     re-run) leaves the schema and rows as in test 2.
  4. `test_both_columns_are_refused_unchanged` and `test_neither_column_is_refused`: the
     precondition's two refusals (§ 4.2); nothing is applied and `db_version` has no 25.
- **Renamed tests** (§ 3.2) keep their assertions with the new names. One added test in
  `TestLifecycle`: `test_the_old_status_field_is_refused` — a `PUT` with
  `{"status": "standby"}` answers 400 with `field: "status"` and the message of § 4.4; the
  node's lifecycle stays `in_service` and no history event is written. The same for a `POST`
  whose body is otherwise complete and valid, plus `status`, so `field: "status"` is the only
  error (BR2-03).
- **History**: an existing test in `test_equipment_api.py` that changes the status and reads
  the events asserts the event name `lifecycle`.
- The full backend suite runs green (`tooling/run-backend-tests.bat`).

### 7.2 Frontend and e2e

- Vitest: the renamed maps, `describeEvent` for `lifecycle`, the asset-list filter line.
- **e2e: the full suite**, because the rename touches the seed (`seed_e2e.py`, every lane's
  data) and screens in several specs (`equipment`, `asset-list`, `labels`, `tickets-raise`,
  `screens`).
- New test in `equipment.spec.js`, **important**, `[auto]`:
  `S030: the lifecycle is named Lifecycle on the form, the page, the list and the history` —
  as engineer: open *Add equipment*, see the label *Lifecycle* with *In service* chosen;
  on the page of a node the test makes itself (`createEquipment`, as the S029 tests do; the
  three projects share one database) click *Change lifecycle*, choose *Standby*, save; see
  the badge *Standby* and the history line "Lifecycle: In service → Standby"; on `/equipment`
  see the column header *Lifecycle* and the filter choice *Any lifecycle*. No text *Status*
  in the dialog or in the list's `thead` (the check is scoped to those two: the Tickets
  filter rightly says "Any ticket status") (BR1-09).
- The S003 test in `equipment.spec.js` (line 74) keeps its flow with the new button and label;
  its title says "changes its lifecycle" (BR2-01).

### 7.3 Manual checks

- **Automated**: the S030 e2e test above (important).
- **On a real device**: none. Every check is on screen text a browser can read.

### 7.4 Acceptance

- `grep -rn "status" backend/equipment*.py` finds no use that means the equipment field,
  except the `_REFUSED_FIELDS` entry for old tabs (§ 4.4).
- No screen shows the word *Status* for the equipment field (the S030 e2e test).
- The backend, frontend and full e2e suites pass.

## 8. Open questions and assumptions

1. **Assumption:** production's `equipment_events` is small enough that the rebuild in step
   3 is instant (to verify: a count on production before the release, through `ccssh`).
2. **Fact (checked 23-10-2026):** nothing outside Yantra reads `equipment.status` or the API
   field. A grep of `smtw_erp_devops` and `aibots` for `equipment` with `status` finds
   nothing; the devops files that name Yantra are its deploy, compose, secrets and nginx.
3. **Decided (BR1-03, user at gate A, 23-10-2026):** no extra backup before the release;
   the nightly dump covers a rollback, with the loss window of § 6.
4. **Assumption:** the docstring of `tracked_changes` (`equipment_core.py:180`) and other
   comments that say *status* for this field are updated with the code; comments about ticket
   states and HTTP statuses stay.

## 9. Docs (at approval)

- `docs/Plan.MD` line 235: "lifecycle (in service / standby / out of use / scrapped — …)";
  line 773: "change of lifecycle, criticality or class". A line in the decisions list:
  *Lifecycle* for the register field, *Status* reserved (decided 23-10-2026, S030).
- `docs/Maintenance-Philosophy.md` § 12, two rows:
  - *Lifecycle* — "Where a piece of equipment is in its life: in service, standby, out of use,
    scrapped (ISO 55000 life cycle). Set by hand on the equipment page."
  - *Status* — "Whether a machine can run now: working, degraded, down, PM due (EN 13306 up /
    down state). Derived from tickets and PM, never typed by hand. S029's ticket light is its
    first form."
- `CLAUDE.md` § SMTW-Review gains no point: the migration rule there already covers v25.

## 10. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | blocker | **Accepted.** An absent `equipment` table passes (§ 4.2 table, first row; the reason under it); § 7.1 test 1 asserts no refusal on an empty database. |
| BR1-02 | minor | **Accepted, option a.** `status` joins `_REFUSED_FIELDS` with "This field is now called Lifecycle. Reload the page." (§ 4.4, D4, § 3.1); the test is `test_the_old_status_field_is_refused` (§ 7.1). It follows S012 § 5.4's precedent, so it is no new design; shown to the user at gate A. |
| BR1-03 | minor | **Decided by the user at gate A (23-10-2026): no extra backup; the nightly dump covers a rollback** (§ 6, § 8 item 3). Earlier answer: **Accepted, option a proposed; the user decides at gate A.** § 6 names the hand-run `mariadb-dump.service` (verified in `smtw_erp_devops/db_server/build_mariadb_backup.yaml:56-59`), the file check, and what a rollback loses; § 4.1 cites `rollback_lines`; § 8 item 3 holds the decision. |
| BR1-04 | minor | **Accepted.** `test_site_checks_api.py` added to § 3.2. |
| BR1-05 | minor | **Accepted.** § 2 cites ISO 55000:2014 § 3.2 *life cycle* by its definition, says the stages are the organisation's, and names the 2024 revision; EN 13306:2017 § 6 item states. |
| BR2-01…BR2-03 | nit | All accepted: S003 e2e title (§ 7.2); backup folder and one-shot wait in § 6; complete POST body in § 7.1. |
| BR1-06…BR1-11 | nit | All accepted: step-1 comment says "safe to re-run" (06); MariaDB ≥ 10.5.2 line in § 4.1 (07); *Any lifecycle* reason in § 4.3 (08); e2e test scoped to the dialog and `thead`, own node (09); the comments named in § 3.3 (10); ISO 55001 § 7.6 (11). |
