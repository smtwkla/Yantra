Step: S030 — Equipment lifecycle
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 23-10-2026

Reviewed against: 4a13de5 (the working tree adds only `docs/steps/README.md`'s index row and this step's folder; no code is uncommitted)

# S030 — Brief review, round 2

**Verdict: no `blocker` or `major` open.** No `minor`. Three nits. Every round-1 finding marked `Accepted` is in the brief's text, not only in the Review log. The brief can go to the user at gate A; the BR1-03 choice (how the release takes its backup, § 8 item 3) is the user's and is not re-raised here.

**What I re-read** (round 2 checks only what changed): § 1 (out-of-scope line on the alias), § 2 (ISO 55000, EN 13306, ISO 55001 citations), § 3.1 (`equipment_core` row), § 3.2 (`test_site_checks_api.py`), § 3.3 (comments to update), § 4.1 (step-1 comment, MariaDB version line, rollback paragraph), § 4.2 (the whole section), § 4.3 (*Any lifecycle*), § 4.4 and D4, § 5 (empty database), § 6, § 7.1 (test 1, `test_the_old_status_field_is_refused`), § 7.2, § 8 items 2 and 3, and the Review log. The brief is uncommitted, so there is no git diff of it; I worked from the Review log's answers and the orchestrator's list of changed sections. Sections not named here were not re-reviewed.

Facts file: `scratch/brief-facts-S030.md` was given and used. The two `smtw_erp_devops` files it reports missing exist in the sibling repo (`C:\Users\KLA\PycharmProjects\smtw_erp_devops`); I read them there.

## Findings

None at `blocker`, `major` or `minor`.

## Nits

- **BR2-01** (nit) § 3.4, `equipment.spec.js:74`: the S003 test's title says "changes its status". § 3.4 renames the button, the label and the header comment but not the title. Add the title ("changes its lifecycle"), so the spec uses one word for one thing.
- **BR2-02** (nit) § 6, steps 1 and 2: name the folder and the wait. The unit is `Type=oneshot` (`db_server/resources/mariadb-dump.service.j2`), so `systemctl start` returns only when every dump is written; the script dumps every database on the server, so the command can take minutes. The folder is `backup_mount_point` in `db_server/vars/settings_db_server_vars.yaml` (`/db-dump` in the example vars; the App-FS NFS share, the "ERP-DB-Backup share" of `rollback_lines`). One sentence each saves the user a search on release day.
- **BR2-03** (nit) § 7.1, "The same for a `POST`": say the body is otherwise complete (`level`, `unit_id`, `model_id`, `name`) plus `"status": "standby"`, so the only error asserted is `field: "status"`; a body of `status` alone also fails on the required fields and would not prove the refusal.

## Checked and found consistent

- **BR1-01 (§ 4.2).** The table's first row (no `equipment` table → go) and the reason under it match the code: `init_db` checks the precondition of every pending version before any is applied (`local_db.py:855-861`), and `_old_tables_for_v20` reads `information_schema.TABLES` with `TABLE_SCHEMA = DATABASE()` first and lets an absent table pass (`local_db.py:722, 725-731`). § 5 ("An empty database") and § 7.1 test 1 now agree with § 4.2. The two refusal rows can come only from a hand edit; the refusal shows in Settings › Database through `MigrationBlocked`, as the brief says.
- **BR1-02 (§ 4.4, D4, § 3.1, § 7.1).** `_REFUSED_FIELDS` (`equipment_core.py:203-208`) is checked first in `validate_equipment` for create and update alike (`:277-279`), each key as `{field, message}`; `clean_body` turns the errors into a 400 before any write, so "no history event is written" holds (`equipment.py:739-758`). The old `EquipmentStatusModal.vue` and `EquipmentFormModal.vue` both show `fieldError('status')` beside their select, so an old tab sees the message. The message "This field is now called Lifecycle. Reload the page." meets scope B: what happened, what to do, no field name or code. § 1's out-of-scope line and D4 say the same thing.
- **BR1-03 (§ 4.1, § 6, § 8 item 3).** `rollback_lines` (`tooling/deploy.py:141-151`) says what the brief says: the previous image does not run on the new schema; restore db-server's latest dump first. The unit name `mariadb-dump.service` is the one `build_mariadb_backup.yaml:56-59` deploys; `db_dump.sh.j2:82-83` lists every database with `SHOW DATABASES` and `:89` writes `mariadb_dump_${db}_${TIMESTAMP}.sql.gz` (`YYYYMMDD_HHMM`), so the file name in step 2 is right. "What a rollback loses" is stated. The choice between options a, b and c is left to the user, as it should be.
- **BR1-04 (§ 3.2).** `test_site_checks_api.py:54-56` is the parametrised `test_status_notes_model_at_b` with `{"status": "standby"}`; with `{"lifecycle": "standby"}` and the new name it keeps testing a lifecycle write at the wrong site. (The 403 comes from `load_node_for_user` before `validate_equipment`, `equipment.py:734-739`, so the order question in BR1-04 does not arise either way.)
- **BR1-05, BR1-11 (§ 2).** ISO 55000:2014 § 3.2 *life cycle* is cited by its definition ("stages involved in the management of an asset"), with the stages left to the organisation, *asset life* beside it, and the 2024 revision named; EN 13306:2017 § 6 item states (up / down; operating, idle, standby); ISO 55001 § 7.6 *Documented information* and ISO 9001 § 7.5. The *condition* paragraph is unchanged and right.
- **BR1-06, BR1-07 (§ 4.1).** The step-1 comment now says "safe to re-run; values kept by name". `RENAME COLUMN IF EXISTS` ≥ 10.5.2; `task_queue.py:36` already requires MariaDB ≥ 10.6 for `SKIP LOCKED`, as the brief says.
- **BR1-08 (§ 4.3).** *Any lifecycle* with the reason, beside *Any criticality* and *Any ticket status* (`equipment.spec.js:139` uses that label today).
- **BR1-09 (§ 7.2).** The test makes its own node with `createEquipment` (`equipment.spec.js:164-176`, as the S029 tests at 111-117 do) and scopes the "no *Status*" check to the dialog and the list's `thead`. The Tickets filter's "Any ticket status" stays outside the check.
- **BR1-10 (§ 3.3).** The four comment lines exist and say *status* for this field: `equipmentLabels.js:13`, `test_equipment_api.py:1`, `equipment.py:470` (`_list_filters` docstring), `equipment_core.py:180` (`tracked_changes` docstring); `DocumentsCards.vue:36` is in the § 3.3 table.
- **§ 3.1 claims re-checked.** `check_status_change` at `equipment_core.py:118` with the message "Scrapped is final; the status cannot change" (`:126`); `_TRACKED` holds `("status", "status")` (`:164`); the parser entry `"status": (_enum_parser("Status", STATUSES), False)` (`:229`); the create check at `:311-314`.
- **§ 7.1 test 2.** `equipment_events` has `id`, `equipment_id`, `event`, `old_value`, `new_value`, `created_at`, `created_by` (`local_db.py:345-356`), the columns the test asserts unchanged.
- **§ 8 item 2.** A grep of `smtw_erp_devops` for `equipment` finds nothing, as the brief says.
- **Design and layers, UX, manual checks, track.** Unchanged from round 1: the rule stays in the pure core, no new abstraction; no new screen or step for the floor; one important e2e check, no device check; full track, Opus (D6).
