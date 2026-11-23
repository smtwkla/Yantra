---
name: read-prod-data
description: Query Yantra's production MariaDB read-only, to diagnose an issue or check live state — a failed background task, the schema version, a ticket's or PM job's state, what a user saw. Use whenever production data is needed for a diagnosis or a check.
---

# Read Yantra's production data

`tooling/run-prod-query.bat` (script `tooling/dev/prod_query.py`) runs SQL against the production database
`vel_yantra_master` on db-server as the read-only user `vel_yantra_ro`. Its credentials are the
`PROD_RO_DB_*` values in `backend/secrets_app.py` (dev laptop only).

Read-only is enforced three times: the database user holds only `SELECT`; the script reads `SHOW GRANTS`
first and refuses any user with more; the session is `READ ONLY`. The user also has
`MAX_STATEMENT_TIME 60` and `MAX_USER_CONNECTIONS 2`. Never try to get around any of these (another
user, the app's credentials, ccssh to db-server): a change to production data is KLA's to make.

## How to run

From Git Bash, in the repo root. Prefer `--file` for anything but a short query: cmd mangles `%`,
`"`, `<`, `>`, `|` and `&` in arguments.

```bash
cmd //c "tooling\\run-prod-query.bat SELECT MAX(version) FROM db_version"
# longer SQL: write it to scratch/, then
cmd //c "tooling\\run-prod-query.bat --file scratch\\q.sql"
cmd //c "tooling\\run-prod-query.bat --ddl"     # SHOW CREATE TABLE for every table it can see
cmd //c "tooling\\run-prod-query.bat" < /dev/null   # the probe: version, tables, approx rows
```

`tooling/run-dev-query.bat` takes the same arguments against the dev DB (port 3307), to try a query
first.

## Things to know

- Times read in IST (session `time_zone = '+05:30'`, as the app's own connections).
- **Personal data is not granted**: `people.email` and `push_subscriptions.endpoint`, `endpoint_hash`,
  `p256dh`, `auth`. `SELECT *` on those two tables fails; name the columns. Do not ask KLA to widen
  this for a diagnosis.
- A table added by a migration after the user was made is not granted until KLA runs its `GRANT`
  (`scratch/prod-ro-user.sql` has the pattern). The probe's table count shows what the user sees;
  `ERROR 1142 ... for table` on a new table means the grant is missing.
- Production may be behind the working tree: check `db_version` before reading a column a recent step
  added. Schema reference: `docs/schema/schema.json`.
- Output shows at most 200 rows; add `LIMIT` and filters. Keep scans small: it is a shared server.
- Write no person's name, username or a vendor's phone from these results into a repo file or
  memory (CLAUDE-COMMON: no staff names in a repo or in memory); refer to them by id or role.

## Common queries

```sql
-- Schema version (latest migrations)
SELECT version, description, applied_at FROM db_version ORDER BY version DESC LIMIT 5;

-- Background tasks that failed or wait (worker, S013)
SELECT id, task_type, status, attempts, max_attempts, scheduled_for, last_error
FROM task_queue WHERE status <> 'done' ORDER BY id DESC LIMIT 30;

-- Push sends that failed (no address columns)
SELECT id, person_id, label, last_sent_at, last_error
FROM push_subscriptions WHERE last_error IS NOT NULL;

-- A ticket and its timeline
SELECT id, serial, state, intensity, unit_id, equipment_id, occurred_at, updated_at
FROM tickets WHERE serial = 'TK-2026-11-001';
SELECT * FROM ticket_events WHERE ticket_id = ... ORDER BY id;

-- Open PM jobs (state is stored; the standing Due/Overdue is computed by pm_schedule_core)
SELECT id, serial, plan_id, equipment_id, state, due_on, due_meter, assignee_id
FROM pm_jobs WHERE state IN ('due', 'in_progress') ORDER BY due_on LIMIT 50;

-- Recent access-log rows (logins, refusals, network gate)
SELECT id, ts, username, role, outcome, method, path, is_internal, detail FROM access_log ORDER BY id DESC LIMIT 30;
```
