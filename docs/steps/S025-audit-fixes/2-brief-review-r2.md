```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: one `major` finding open** (BR2-01: the backup gate fires after the
deploy, so its "roll back" advice is wrong for the case it names, and Q1's
second option cannot pass the gate). No blocker. The squashed schema (U1) is
sound: I verified against `git show v0.1.3:backend/local_db.py` and today's
`local_db.py` that v6–v13 alter no v1–v5 table except `equipment` and
`equipment_events`, that the guard tells a v5 table from today's exactly, that
v20 is a no-op on a v13 database, and that the production drop order is forced
by the only foreign key involved. The remaining findings are the details the
coder would otherwise settle alone — mostly what the equivalence test must
compare to mean anything.

Every round-1 finding marked `Accepted` is in the brief text, not only in the
log (checked one by one; list at the end).

## Findings

### BR2-01 (major) — The backup gate runs after the deploy; its failure advice is wrong, and Q1's "manual dump this once" cannot pass it

**Problem.** § 1.1 and § 7.4: `deploy.py` runs the playbook, then looks for
`TASK [<name>]` with `ok`/`changed` in the output and "fails a deploy whose
playbook output does not show" it, "with the rollback lines (§ 5.4)". By then
the playbook has recreated the containers and v20 has (very likely) applied.
Three things follow:

- The advice is wrong for that case. § 5.4 says a rollback *after* v20 "is the
  backup's restore, then the two lines" — but the failure is precisely that no
  backup was taken. Rolling back a working deploy because a dump is missing
  makes things worse (the old image does not run on the new schema; there is
  nothing to restore). The right response is "take a dump now, fix the task",
  not "roll back".
- What the check buys is only that the *next* release fails if the task is
  still missing. ISO 27001 A 8.13's point (a backup *before* the change) is
  not met by a check that runs after the change.
- Q1's second option — "take a manual dump this once and add the task after" —
  cannot pass: § 3 makes `DEPLOY_BACKUP_TASK` required, the task is absent, so
  the first release fails its check *after* deploying. `release.py` then stops
  before `git push --follow-tags`, leaving a deployed version whose release
  commit and tag are only local. The user would approve an option that does
  not work.

**Fix (recommended).** Two checks, cheap and in `deploy.py`'s own style:

1. **Before stamping**: confirm the task exists on ansible-ws —
   `grep -rq 'name: <task>' <ERP_SERVER_DIR>/yantra/` over plink, exactly as
   `stamp()` already does `grep -q '^YANTRA_VER:'`. Missing → abort before
   anything changes: "The backup task <name> is not in the playbook — add it
   (impl report) before releasing".
2. **After the playbook**: confirm it ran (`ok`/`changed`, as now). Not run or
   skipped → the deploy is *not* rolled back; the message says: "Deployed, but
   the task <name> did not run — take a dump now
   (`mariadb-dump --single-transaction …`) and find out why it was skipped",
   and `deploy.py` still exits non-zero so the tag is not pushed until the
   user has looked.

Then § 5.4 keeps its rollback lines for the schema-not-ready case only; § 7.4
says the gate is before the deploy; and Q1 resolves itself: the task is added
before this release (the impl report gives it; the user pastes it into
`smtw_erp_devops`; the pre-check proves it is there). Drop Q1's second option.

Two details for the post-check, whichever option: Ansible prefixes a role's
tasks (`TASK [yantra : Back up the Yantra database] ****`), so match the name
inside the brackets, not `TASK [<name>]` literally; and the status is on the
next line (`changed: [host]` / `ok: [host]` / `skipping: [host]`), so the
check reads the line after the header.

*Alternative:* keep the post-hoc check only and say plainly in § 7.4 that it
protects the next release, not this one — honest, but the user asked for a
backup gate, and the pre-check is one plink line.

### BR2-02 (minor) — What the equivalence test must compare, and whether column order counts

**Problem.** § 3 Tests: "tables, columns with type/null/default, indexes,
foreign keys, CHECKs". Left as is, the coder decides what makes two schemas
"equal", and the test can pass while v20 differs from v1–v13 in ways that
matter. The things the old path produces that a hand-written v20 can miss:

- **Column order.** v5 added `equipment.notes` with no `AFTER`, so on every
  v13 database `notes` is the *last* column, after `updated_by`; `type_id`,
  `model_id` sit after `class_id`; `sites.is_default` after `active`;
  `equipment_documents.model_id`, `ticket_id` after `equipment_id`;
  `tickets.cause_id … repeat_of_id` after `failure_mode_id`. A coder writing
  "today's shape" will put `notes` beside `name`. Nothing in the code depends
  on order (`DictCursor`, named columns), so either decision is fine — but the
  brief must take it: compare `ORDINAL_POSITION` and have v20 reproduce the
  v13 order (a comment on `notes` says why), or exclude it and say so. I
  recommend comparing it: the test is then a plain "equal", and v20 is a
  faithful record of the schema production will have.
- **`EXTRA`** (`auto_increment`; `on update current_timestamp()` on
  `app_settings.updated_at` — the one `ON UPDATE` in the schema) and
  `COLUMN_DEFAULT`.
- **Indexes**: name, `NON_UNIQUE`, columns in `SEQ_IN_INDEX` order — the
  existing migration tests already read `STATISTICS` this way. InnoDB
  auto-creates an index named after a foreign key that has none
  (`fk_equipment_parent`, `fk_tickets_reported_by`, …) and reuses a declared
  one whose prefix fits (`ix_equipment_model`, `ix_equipment_documents_model`,
  `ix_tickets_repeat_of`, `uq_units_site_code`); both paths give the same set
  only if v20 declares the same `KEY`s, which the comparison must see.
- **Foreign keys**: name, columns in order, referenced table and columns
  (`KEY_COLUMN_USAGE` with `ORDINAL_POSITION`; the three composite FKs
  `(type_id, class_id)`, `(model_id, class_id)`, `(type_id, class_id)` on
  models), and `REFERENTIAL_CONSTRAINTS.DELETE_RULE/UPDATE_RULE`.
- **CHECKs**: `CHECK_CONSTRAINTS.CONSTRAINT_NAME` and `CHECK_CLAUSE` (the
  server normalises the text, so equal definitions compare equal; MariaDB
  11.4 has the table, as `test_migration_v12._owner_checks` already uses).
  ENUM text is in `COLUMN_TYPE` and so covered by "type".
- **Table**: `TABLES.ENGINE`, `TABLE_COLLATION` — `db_version` and
  `app_settings` have no `ENGINE`/`CHARSET` clause in v1 and take the
  database default; v20 should keep them as they are, not "fix" them.
- Exclude `AUTO_INCREMENT`, `CREATE_TIME`, `UPDATE_TIME`, row counts.
- **Every query filtered by `TABLE_SCHEMA = DATABASE()`** (the existing
  migration tests do) — see BR2-03 for why it matters here especially.

**Fix.** Put this list in § 3 Tests (one bullet each), and the column-order
decision in § 7 with its reason.

### BR2-03 (minor) — The v20 guard must read `information_schema` for the current database only

**Problem.** § 3: the guard "reads `information_schema` for the two tables".
The dev MariaDB serves `vel_yantra_master`, `vel_yantra_test`, `vel_yantra_e2e`
and, after S025, `vel_yantra_upgrade` — and the production-path test builds a
v5 `equipment` in `vel_yantra_upgrade` while `vel_yantra_test` beside it is at
v13. A `COLUMNS` query without `TABLE_SCHEMA = DATABASE()` sees test's
`model_id` and passes the guard; v20 then "succeeds" on the v5 table
(`CREATE … IF NOT EXISTS equipment` skips it) and records itself. The test
would catch it (the schema would not equal the reference), but the same
query on production — one database, so no false match — would look right in
review and be wrong by construction.

**Fix.** Say the guard's two queries carry `TABLE_SCHEMA = DATABASE()`
(`COLUMNS … COLUMN_NAME = 'model_id'` for `equipment`; `COLUMNS … COLUMN_NAME
= 'event'` and `'model'` in `COLUMN_TYPE` for `equipment_events`), as every
existing migration test does. Also let the refusal name the table that is
still old ("equipment is still in its old shape") — after a partial drop
(`equipment_events` alone can be dropped; the reverse cannot, its FK stops
it), the user then knows which one remains.

### BR2-04 (minor) — How the test runs the frozen fixtures is not said

**Problem.** `init_db(config)` reads the module-level `_MIGRATIONS`; the
equivalence and production-path tests must run a *different* list (the
frozen v1–v13 / v1–v5) against `vel_yantra_upgrade`, then today's. The brief
names the fixtures but not the mechanism, so the coder chooses between a new
parameter on the engine and a monkeypatch — a design choice the user should
see. Two smaller points in the same area:

- `git show v0.1.3:backend/local_db.py` v1–v5 is byte-identical to today's
  v1–v5 (checked), so `fixtures/migrations_v0_1_3.py` is the first five
  entries of `fixtures/migrations_v13.py`. One fixture file, sliced `[:5]`,
  is enough (DRY); the docstring records both provenances.
- The preconditions dict is keyed by version, so running the fixture never
  trips v20's guard; worth one line so the coder does not add a switch.

**Fix (recommended).** `monkeypatch.setattr(local_db, "_MIGRATIONS",
fixture)` in the test, no production-code change; `init_db`'s signature
stays. *Alternative:* `init_db(config, migrations=_MIGRATIONS)` — a parameter
used only by tests; not needed.

### BR2-05 (minor) — § 5.4's rollback lines: where the previous version comes from, and one command text, not two

**Problem.** § 5.4 says the message gives
`sed -i 's/^YANTRA_VER: .*/YANTRA_VER: "<previous>"/' <vars file>` "with the
previous version filled in by `deploy.py`". `deploy.py` has no previous
version: it reads `VERSION` (the new one) and `stamp()` overwrites the vars
line with `grep -q` first, discarding what was there. And the brief's sed
(`'^YANTRA_VER: .*'`, `/` delimiters) is a second spelling of `stamp()`'s
(`'^YANTRA_VER:.*'`, `|` delimiters, relative to `cd ERP_SERVER_DIR`) — two
texts for one command drift.

**Fix.** `stamp()` captures the current `YANTRA_VER` line before the sed (the
`grep -q` becomes a `grep` whose output is parsed; `--check` already prints
that line) and keeps the previous version for the message; the message is
built from the same helper that builds the stamp command, with the previous
version substituted, plus `cd <ERP_SERVER_DIR> && ./erp_spanner.py deploy vel
yantra master`. The vars file is the right source (it is what is deployed,
even after a `--stamp-only`), not the local git tags.

### BR2-06 (minor) — `test_health.py`'s "false" case: reuse the existing pattern instead of poking module state

**Problem.** § 3 Tests: "`schema_ready` … false when `init_db` raises
`MigrationBlocked` (monkeypatched)". That does not work as written: conftest's
session fixture already called `ensure_schema` for the process, so
`local_db._schema_ready` is `True` and `ensure_schema` returns `None` without
calling `init_db`; the test would have to reset `_schema_ready` and
`_last_attempt` and restore them after — private state, easy to leave dirty
for the rest of the session.

**Fix.** Do what every existing "database down" test does
(`test_auth.py:66`, `test_access_control_api.py:45`, `test_worker.py:92`):
`monkeypatch.setattr(app_module, "ensure_schema", lambda _c: "blocked")`
on the module the route imports it into, and assert `{"status": "ok",
"schema_ready": false}` with 200. The engine's own `MigrationBlocked` path
is covered by the production-path test (refused, `db_version` max 5).

### BR2-07 (nit) — Which old migration tests change, concretely

The brief leaves it to the report. The rule is mechanical and worth three
lines so the coder does not re-derive it: the **shape** tests
(`test_migration_v10.test_tables_and_the_default`, `v11.test_tables…`,
`v11.test_seed_rows`, `v12.test_tables_and_indexes`, `v12.test_the_owner_check…`,
`v12/v13` single-owner and minutes-range tests, `v13.test_ticket_columns…`,
`test_assignees_table`, `test_labour_table`, `v9.test_an_equipment_row_with_a_null_model…`,
`v9.test_the_owner_check…`) read the live schema and need no change; the
three **data-movement** re-runs (`v8.test_legacy_rows_move_once…`,
`v10.test_a_missing_setting_is_written_on_rerun`,
`v11.test_rerun…keeps_an_edited_seed_row`) become `DELETE FROM db_version
WHERE version = 20` + `init_db` and keep their asserts; the pure re-run tests
(`v9`, `v10`, `v12`, `v13` `test_rerun_changes_nothing…`, including v12's
"v9 after it") are replaced by the one re-run test. `test_modules.py`'s
`LATEST_VERSION` asserts hold unchanged (`db_status` reads `MAX(version)`,
which is 20 beside 1–13).

### BR2-08 (nit) — Two departures from the base to record

- SMTW-WebApp-Base § Migration squashing: "Dev databases must be recreated
  (drop + recreate)". § 1.1 and § 8 keep dev/test as they are (v20 is a
  no-op there) — right, and the e2e database is rebuilt by v20 at every run,
  so v20 still builds a database the suite exercises — but say in § 2 or
  § 7.1 that this is a deliberate departure and why, beside the v1→v20 one.
- The base squashes into v1; the brief's v20 departure is recorded (§ 7.1).

### BR2-09 (nit) — Small wording and edge points

- v20 keeps the `created_by` tags verbatim: `'migration-v8'` (the moved
  people; `masters.py:835` and S011 refer to it) and `'migration-v11'` (the
  seed rows; `conftest.SEED_CREATOR` and `test_failure_codes_api.py:241` rely
  on it). Say so, or a tidy coder renames them to `migration-v20` and the
  seed-row filter stops matching.
- Plan.MD § 5's `user_units` row says "Copied to `person_units` by migration
  v8"; § 3 Docs edits § 5 for v20 — include that row.
- The health poll: a non-200 (nginx's 502 while the containers are being
  recreated) is "not yet", like a connection error — the brief says only
  "a connection error is not yet".
- `/api/health` calling `ensure_schema` can wait up to 60 s on
  `GET_LOCK(LOCK_MIGRATIONS)` while another process migrates, so the first
  poll after a deploy may be slow rather than "not yet". Acceptable; one
  line in § 7.5 so nobody adds a timeout later.
- The upgrade test can rebuild its database the way `e2e_backend.py` does
  (`DROP DATABASE IF EXISTS` + `CREATE DATABASE` on a connection with no
  database selected; the `GRANT ALL ON vel_yantra_upgrade.*` covers both),
  rather than dropping 27 tables with `FOREIGN_KEY_CHECKS = 0`.

### BR2-10 (nit) — Device and e2e checks

- The second device check restores a production dump "into the dev
  database": that replaces `vel_yantra_master`'s dev data. Say "into a fresh
  database" (e.g. `vel_yantra_restore`, created and dropped by hand) or
  accept the replacement explicitly.
- e2e "*Machine stopped* refused shows its message": say how the refusal is
  provoked — the test re-grades the ticket to critical through the API
  (`page.request` with the harness headers) after opening the dialog and
  before pressing the button. A reader of § 8 otherwise wonders how a
  browser test makes two operators collide.

## Verified claims of U1 (the squashed schema)

- **Only `equipment` and `equipment_events` were altered after v5.** Every
  `ALTER` in v6–v13: v9 on `equipment` (add `model_id`, index, FK; drop
  `make`, `model`), on `equipment_documents` (a v6 table) and on
  `equipment_events` (`MODIFY event`); v12 and v13 on `equipment_documents`
  and `tickets` (v12 tables). Data statements on v1–v5 tables: `INSERT
  IGNORE` into `app_settings` (v6, v10) and v8's `INSERT … SELECT FROM
  user_units` (reads only). So the eight others (`db_version`, `app_settings`,
  `sites`, `units`, `equipment_classes`, `user_units`, `serial_counters`,
  `equipment_types`) are in today's shape on production and `CREATE TABLE IF
  NOT EXISTS` may skip them. 27 tables in all; 8 skipped + 19 created (17
  new + the 2 dropped) matches § 1.1.
- **The guard detects v5 exactly.** v5's `equipment` has `type_id` and
  `notes` but no `model_id` (v9 adds it); v5's `equipment_events.event` ENUM
  is the seven values ending `'type'` (line 177); v9 appends `'model'` (line
  336). "`model_id` present" and "`'model'` in the ENUM" are each false on a
  v5 table and true on today's.
- **Drop order is forced.** In v1–v5 only `equipment_events` references
  `equipment` (plus the self-reference); `DROP TABLE equipment` first fails
  on that FK, so § 5.1's order (events, then equipment) is the only one that
  works and a mistake cannot half-drop the wrong way.
- **FK order inside v20 works.** The dependency graph has no cycle:
  `equipment_documents` → `tickets` → `equipment` → `equipment_models` →
  `equipment_types` → `equipment_classes`; `tickets` also → `failure_modes`,
  `failure_causes`, `maintenance_actions`, `people`, `units`; the
  self-references (`equipment.parent_id`, `tickets.repeat_of_id`) and the
  composite FKs are valid inline in `CREATE TABLE` once the referenced
  unique index is declared in the same or an earlier statement (v9 and v13
  already rely on that). One order that works: `db_version`, `app_settings`,
  `sites`, `units`, `equipment_classes`, `user_units`, `serial_counters`,
  `equipment_types`, `manufacturers`, `equipment_models`, `equipment`,
  `equipment_events`, `trades`, `people`, `person_trades`, `memberships`,
  `person_units`, `failure_modes`, `failure_causes`, `maintenance_actions`,
  `tickets`, `ticket_events`, `ticket_assignees`, `ticket_labour`,
  `equipment_documents`, `access_log`, `task_queue`; then the data.
- **v20 is a no-op on a v13 database.** Every `CREATE` skips; `INSERT
  IGNORE` into `app_settings` is keyed on the primary key and both rows
  exist; the S016 seed's `INSERT IGNORE` is keyed on the unique `code` (and
  `label` for causes and actions), all present; v8's `people` insert is
  guarded by `NOT EXISTS (username)` and its `person_units` insert by the
  primary key, and the dev seed writes no `user_units` rows
  (`seed_dev.py` does not name the table). On the test database conftest
  empties `user_units` at session start. So nothing is inserted and
  `db_version` gains the one row.
- **`vel_yantra_upgrade` on S024's grant pattern is enough**: `GRANT ALL ON
  <db>.*` lets the app user create, drop and read `information_schema` for
  that database (`e2e_backend._recreate_database` already does the
  drop/create with the same user); `init_db(config)` takes the config.
- **`deploy.py`**: `stamp()`'s command text and `VARS_FILE`/`VER_KEY` are as
  § 5.4 assumes (BR2-05 for the previous version); `release.py` aborts
  before `git push --follow-tags` when the deploy script exits non-zero.

## Checked and found consistent

- Round-1 findings, each in the text: BR1-01 (§ 1.1, § 3 `app.py`, § 7.5);
  BR1-02 (§ 7.3, § 5.4, § 5.1 order, the device check's "if refused");
  BR1-03 (§ 3 Tooling and Tests); BR1-04 (§ 1.3's five points, the five
  tests in § 3); BR1-05 (`local_db.is_connection_lost`, worker); BR1-06
  (§ 1.6); BR1-07 (§ 1.5, `allowed_moves(…, has_repeat=False)`); BR1-08 (the
  new guard: `information_schema`, absent passes, after
  `_get_applied_versions` under the lock); BR1-09 (§ 3 Tooling); BR1-10
  (`DEPLOY_BACKUP_TASK` + output check — now BR2-01); BR1-11
  (`tooling/tests`, `run-tooling-tests.bat`, `run-tests.bat`, opener/clock
  parameters); BR1-12 (message names the Deploy run config; failed inspect =
  absent); BR1-13 (ISO 14224 § 7, SMRP 3.5.2); BR1-14 (`test_health.py`
  (new)); BR1-15 (one wording with the count; the guard leads with the
  action); BR1-16 (200 both ways).
- § 1.4 against `masters.update_unit`: the unit is locked `FOR UPDATE` first;
  today's deactivation guard refuses on unscrapped equipment, so the new
  open-ticket refusal matters for the case audit [2] names — a machine moved
  out after the ticket was raised (`tickets.unit_id` is the unit at raise).
  `_unit_is_referenced` counts `person_units` and `equipment` only, as the
  brief says.
- `LATEST_VERSION = _MIGRATIONS[-1][0]` becomes 20 with no other change;
  `db_status` reports `MAX(version)`.
- The engine: a `MigrationBlocked` raised inside `init_db`'s loop releases the
  named lock in `finally`; `ensure_schema` catches `DBUnavailable` subclasses
  and keeps `describe_error(exc)` (`str(exc)` for a non-pymysql error) as
  `_last_error`, which `db_status` and Settings › Database already show.
- Standards: ISO 55001 § 8.1, ISO/IEC 27001:2022 A 8.32 and A 8.13, ISO 14224
  § 7, SMRP 2.1.1 / 3.5.1 / 3.5.2, ISO 9001 § 10.2 are the right clauses and
  the plain-terms explanations are good; the base's squashing rule is cited
  and the v20 departure recorded (BR2-08 for the second one).
- Layering: the send-back rule in `tickets_core`; the guard beside
  `_MIGRATIONS` as one dict and one exception subclass; no new abstraction.
  Right-sized.
- UX: the new refusals are one plain line each ("Close its tickets first (N
  open)", "This ticket came back as TK-…; work on that one"); *Send back*
  hidden server-side rather than refused; the guard's message tells IT admin
  what to do. The important device check carries account, network and where;
  nothing on the device list a browser could judge.
- Track: full is right (migration engine, locking rules, deploy script).
- S024 in the working tree: the brief's dependence on it (e2e suite,
  `vel_yantra_e2e` pattern, `harness.py`) matches what is there; Q4's order
  (S025 after S024 is committed) stands.
