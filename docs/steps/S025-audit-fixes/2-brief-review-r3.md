```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: one `major` finding open** (BR3-01: the backup task as described
cannot be written — production's database is not in the Yantra stack, and
db-server already has the dump machinery the task should use). No blocker.
Every round-2 finding marked `Accepted` is in the brief text, not only in the
log (checked one by one; list at the end). The two revisions left three small
inconsistencies (BR3-02, BR3-03, BR3-06) and no contradiction on what a
missing backup does (§ 1.1 and § 5.4 agree) or on the v9 wording.

Round 3 read, besides the brief and the code: the devops repo at
`C:\Users\KLA\PycharmProjects\smtw_erp_devops` (read-only) — `erp_server/
yantra/deploy.yaml`, `compose.yml.j2`, `erp_spanner.py`, `oneerp/backup.yaml`,
`db_server/resources/db_dump.sh.j2`, `docs/lob-apps/Yantra.MD` and
`db_server.MD` — because BR2-01's pre- and post-check are only as good as the
task they look for.

## Findings

### BR3-01 (major) — The backup task cannot run where the brief puts it; db-server already takes the dumps

**Problem.** § 1.1 says the impl report delivers "a ready-to-paste Ansible
task for `smtw_erp_devops` named `Back up the Yantra database` that dumps it
(`mariadb-dump --single-transaction`) to the backup share before the containers
are recreated, keeping the last 10", and § 5.1 step 1 asks for "one manual
`mariadb-dump`". Four facts from the devops repo:

- **The database is not in the stack.** `yantra/compose.yml.j2`: "Database:
  MariaDB on db-server (not in this stack)". `deploy.yaml` plays
  `target_servers` = the app VM (customer7). A task in that play would have to
  reach `db-server.apps.smtw.in` from the app VM: no `mariadb-dump` client is
  there, and the only credential the play holds is the Yantra app user, which
  `Yantra.MD` § First deployment creates as `'vel_yantra_master'@'10.24.0.112'`
  — it can connect only from the app VM.
- **The app VM mounts no backup share.** Its one NFS mount is the documents
  export `/Vel-Yantra-Master` → `/app/data` (`DATA_DIR`, served through
  permission-checked routes). A dump written there would sit beside the
  equipment photos, outside every retention and shipping job.
- **db-server already dumps every database** (`db_server.MD` § Backup
  Configuration, `db_dump.sh.j2`): `mariadb-dump --single-transaction
  --routines --events --triggers --databases <db>` via `docker exec` on the
  MariaDB container, **twice a day (05:30 and 17:30 IST)**, one gzip per
  database (`mariadb_dump_vel_yantra_master_<UTC ts>.sql.gz`) into `/db-dump`
  (the App-FS export `ERP-DB-Backup`, shipped to S3 from the other side),
  14-day retention, and a `BACKUP_RESULT` logfmt line per artifact on the
  unit's journal for monitoring. `Yantra.MD` records that "the existing
  db-server dumps cover it".
- **The devops repo has a backup convention** the brief does not use:
  `./erp_spanner.py backup <org> <app> <instance>` runs `<app>/backup.yaml`
  "before deploy" (`oneerp/backup.yaml` is the model), exits 1 when the
  playbook is missing and non-zero when it fails — unlike `deploy`, which
  exits 0.

So the task as described has nowhere to run and would be a second, unmonitored
backup mechanism with its own retention ("keeping the last 10") beside one
that already works. ISO/IEC 27001 A 8.13 asks for backups that are *taken,
retained and tested* — one mechanism, watched, is how that is met; a second
copy nobody monitors is how one of them quietly stops.

**Why it matters for gate A.** § 7.4 ("the backup lives in the devops
playbook; `deploy.py` checks it ran") and § 9 Q1 are decisions the user
approves, and they rest on the task being pasteable. Where the dump runs, with
which credentials and onto which share is infrastructure — the user's call.

**Options.**

(a) **Recommended — `yantra/backup.yaml`, run by `deploy.py` before the
stamp, delegated to db-server, reusing the dump script's conventions.**
- The playbook (ready-to-paste in the impl report, on `oneerp/backup.yaml`'s
  shape) has one task delegated to db-server
  (`delegate_to: db-server.apps.smtw.in`; db-server is managed by the same
  repo, `vars/hosts/db_servers.ini`, so the Ansible user and host key are
  there) that runs `docker exec {{ backup_mariadb_container_name }}
  mariadb-dump -u… --single-transaction --routines --events --triggers
  {{ yantra_db_name }} | gzip > /db-dump/mariadb_dump_{{ yantra_db_name }}_<ts>_predeploy.sql.gz`,
  writing to a `.part_` name and renaming on success as the script does. The
  credentials are the backup user from `db_server/vars/settings_db_server_vars.yaml`
  (`vars_files`), not the app user. Keeping the `mariadb_dump_` prefix puts
  the file under the existing 14-day retention and the S3 shipper's glob, so
  "keep the last 10" is not needed.
- `deploy.py`'s order becomes: pre-check (`test -f yantra/backup.yaml` over
  plink — simpler than a grep for a task name) → `./erp_spanner.py backup vel
  yantra master` (abort on non-zero; its own PLAY RECAP is checked as
  `deploy()` does) → stamp → deploy → health poll. The backup is then taken
  **before anything changes** and fails closed; BR2-01's "Deployed without a
  backup — take a dump now" post-check and the `TASK [<role> : <name>]`
  parsing disappear, and `DEPLOY_BACKUP_TASK` is not needed (the playbook's
  path is fixed by the convention). `--stamp-only` runs the backup too
  (BR3-03).
- § 5.1 step 1 becomes "nothing by hand: the deploy's backup step runs first"
  — or, if the user wants a second copy for this first release, "on db-server,
  the same `docker exec … mariadb-dump` line"; § 8's device check says the
  file is in `/db-dump` on db-server; the restore check (BR3-06) names the
  file pattern.
- Cost: one small playbook, one less check in `deploy.py`, and the tests
  cover "backup.yaml missing → abort before stamp" and "backup failed →
  abort before stamp" instead of the output scan.

(b) *Zero new dump code:* the delegated task runs `systemctl start
mariadb-dump.service` (a oneshot, so it blocks until done) and asserts a
`mariadb_dump_vel_yantra_master_*.sql.gz` newer than the task's start. Every
database on db-server is dumped before each Yantra release — minutes for
OneERP's size — but nothing new to maintain.

(c) *Rejected:* a task in `deploy.yaml` on the app VM running `docker run
--rm mariadb:11.8 mariadb-dump -h db-server …` with the app user (the one
credential that can connect from there) onto the documents share — dumps
beside uploads, no retention, no monitoring, a second mechanism.

Whichever option: § 1.1, § 3 Tooling, § 5.1, § 5.4, § 7.4, § 8, § 9 Q1 and
Q6 and `test_deploy.py`'s list change together; the health poll, the v20
design and everything else stand.

### BR3-02 (minor) — § 3 Tooling and § 7.4 still describe only the post-check (BR2-01 leftover)

**Problem.** § 1.1 has BR2-01's two checks (before stamping; after the
playbook). § 3 Tooling says "`tooling/deploy.py`: **after the playbook**, the
backup-task check (`DEPLOY_BACKUP_TASK`) and the health poll", and § 7.4 is
"the backup lives in the devops playbook; `deploy.py` checks it **ran**". A
coder working from § 3 Where builds the post-check only. Also, one detail of
the pre-check as written: `grep -rq 'name: <task>'` should be `grep -rqF`
(the name is matched as text, not a pattern).

**Fix.** Under BR3-01 (a) both sections are rewritten anyway: § 3 Tooling
"before stamping: the backup playbook exists and is run; after the playbook:
the health poll"; § 7.4 "the backup runs from `deploy.py` before the stamp,
through the repo's `erp_spanner.py backup` convention". If the user keeps the
task-in-`deploy.yaml` design instead, § 3 and § 7.4 get the pre-check in the
same words as § 1.1.

### BR3-03 (minor) — `--stamp-only` and the backup gate

**Problem.** § 3 Tooling keeps BR1-09's rule: the two variables are "not
[required] for `--check` or `--stamp-only`". That was settled for a flag
checked after the deploy. With BR2-01 the gate moved to "before anything
changes — before stamping", and `--stamp-only` stamps: it changes the vars
file so that a person then runs `erp_spanner.py deploy` by hand, with no
`deploy.py` check after it. As written, `--stamp-only` is the one path that
skips the backup gate entirely. Not a re-open of BR1-09 — the interaction of
two accepted findings that the revision did not settle.

**Fix (recommended).** The backup step (or the pre-check) runs in every mode
that stamps, i.e. all but `--check`; only `DEPLOY_HEALTH_URL` stays unneeded
for `--stamp-only` (no deploy, nothing to poll). One line in § 3 Tooling and
one test case. *Alternative:* keep `--stamp-only` bare and say in its message
"no backup was taken — run `erp_spanner.py backup` first"; weaker, since that
mode exists for the hand-run deploy.

### BR3-04 (minor) — The rollback lines print on every failure after the stamp, not only the poll

**Problem.** § 5.4 gives the rollback lines "for a schema that is not ready".
`deploy()` also fails when the playbook itself reports failures (`failed=`,
`unreachable=`, or the `uri` wait on `/api/version` runs out after 24 × 5 s)
— after the stamp, with the containers possibly half-recreated and
`YANTRA_VER` at the new version. Today's message there is "the Ansible
playbook reported failures" and nothing else. Since BR2-05 puts the previous
version in hand before the stamp, the same two lines cost one call.

**Fix.** § 5.4: "any failure after the stamp — the playbook, or the schema
poll — ends with the two rollback lines"; the before/after-v20 branches stay
as they are. One test case for the playbook-failed path.

### BR3-05 (nit) — The guard's message: § 1.1 and § 3 disagree on its text

§ 1.1 gives one fixed line naming both tables ("Drop the old equipment and
equipment_events tables first (they are empty), then the schema is built — see
S025 § 5.1"); § 3 `local_db.py` says "the message names which table is still
old" (BR2-03, for the half-dropped case). Put the per-table text in § 1.1,
e.g. "equipment is still in its old shape — drop equipment_events, then
equipment (both are empty); the schema is then built within 30 s (S025 §
5.1)", with the table name filled in. Same section: "The two v9 changed are
empty in production" has lost a word — "The two tables v9 changed …".

### BR3-06 (nit) — § 5.1 and § 8 wording after Q1; the restore check's file

- § 5.1 step 1 still says "until the playbook task exists: one manual
  `mariadb-dump`", but § 9 Q1 now has the task in place *before* this release
  (the pre-check refuses otherwise), and the step list has no "step 0: add
  the backup task/playbook to `smtw_erp_devops` on ansible-ws" — § 8's
  important check points at "§ 5.1 steps 1–3", so the one prerequisite that
  makes the deploy start is not on the list. Add step 0; reword step 1 per
  BR3-01's outcome (nothing by hand, or "a second copy, on db-server").
- § 8's "the backup file exists" should say where (`/db-dump` on db-server,
  `mariadb_dump_vel_yantra_master_*.sql.gz`).
- The restore device check (`vel_yantra_restore` on the dev server): db-
  server's dumps are taken with `--databases <db>`, so the file carries
  `CREATE DATABASE … USE vel_yantra_master` and restores into that name — on
  the dev server that is the dev database. Say how: the pre-deploy dump is
  taken without `--databases` (then `mariadb vel_yantra_restore < file`
  works), or the check pipes the file through `sed '/^USE /d;/^CREATE
  DATABASE/d'`. Under BR3-01 (a) the first is one word in the playbook.

### BR3-07 (nit) — BR2-02's column-order decision is not in § 7

The comparison list is in § 3 Tests, with "v20 reproduces today's column
order" as a parenthesis. BR2-02's fix put the *decision and its reason* in
§ 7; it is not there. One line under § 7.1 or 7.2: "v20 reproduces the
column order v1–v13 left (`equipment.notes` last, `model_id` after
`type_id`), so the equivalence test is a plain equal and v20 is a faithful
record of production's schema; nothing in the code depends on order".

## Round-2 findings verified in the text

- **BR2-01**: § 1.1 has both checks — the pre-check "before stamping, over the
  same plink session as `stamp()`", the abort text, "nothing deployed"; the
  post-check with the role-prefixed `TASK [<role> : <name>]` match and the
  status on a following line; "Deployed without a backup — take a dump now",
  no rollback advice. § 5.4 points at § 1.1 for the missing-backup case and
  keeps the rollback lines for the schema case only. § 9 Q1 resolves to "add
  the task before this release" and drops the manual-dump option. (The
  leftovers are BR3-02 and BR3-03; BR3-01 changes the task itself.) Checked
  against `deploy.py`: `stamp()` is a `grep -q` + `sed -i` + `grep` over one
  `run_remote`, so a grep before it is the same mechanism; `yantra/deploy.yaml`
  is inline tasks, no roles, so Ansible prints `TASK [<name>]` there and the
  bracket match covers both forms.
- **BR2-02**: § 3 Tests lists tables (`ENGINE`, `TABLE_COLLATION`), columns
  (`ORDINAL_POSITION`, `COLUMN_TYPE`, `IS_NULLABLE`, `COLUMN_DEFAULT`,
  `EXTRA`), indexes from `STATISTICS` with the FK-created ones, foreign keys
  with rules, `CHECK_CONSTRAINTS` by name; column order compared and
  reproduced (BR3-07 for the § 7 line).
- **BR2-03**: § 3 `local_db.py` "always with `TABLE_SCHEMA = DATABASE()`" with
  the four-databases reason; § 3 Tests "all filtered by `TABLE_SCHEMA =
  DATABASE()`"; the refusal names the old table (BR3-05 for § 1.1's text).
- **BR2-04**: `monkeypatch.setattr(local_db, "_MIGRATIONS", …)`, engine
  unchanged; one fixture file, first five entries for the production path;
  the database dropped and created by the test as `e2e_backend.py` does.
- **BR2-05**: § 5.4 — the current `YANTRA_VER` line read before the stamp; the
  two lines from `stamp()`'s helper.
- **BR2-06**: `test_health.py` monkeypatches `ensure_schema` on the module the
  route imports it from — `app.py:20` does `from local_db import …
  ensure_schema`, so that is `app`; the `test_auth.py:66` `db_down` pattern
  exists as cited.
- **BR2-07**: shape tests kept, the three data re-runs re-targeted to 20, pure
  re-runs dropped, `LATEST_VERSION` asserts hold, `created_by` tags verbatim.
- **BR2-08**: § 2 records both departures (v20 not v1; dev DBs not
  recreated); § 3 Docs edits Plan.MD § 5's `user_units` row (line 742 today
  says "by migration v8").
- **BR2-09**: non-200 as "not yet"; the lock wait at first boot inside the 3
  minutes; the tags; the Plan.MD row; the database rebuilt by the test.
- **BR2-10**: `vel_yantra_restore`; the e2e provocation through the API with
  the test headers.

## Checked and found consistent

- § 5.4 vs § 1.1 on a missing backup: both say no rollback advice; the
  rollback lines are for the schema case. § 7.3 and § 5.1's "if step 3 is
  forgotten" agree (503 until the drop; ≤ 30 s retry; no redeploy).
- No v9-precondition wording survives: every "v9" left is historical (which
  tables it changed, the ENUM value the guard looks for, the Review log).
  BR1-15's "lead with the action" holds for the guard message.
- § 1.2 against `build.bat` and `release.py`: `release.py` commits and tags
  before `BUILD_SCRIPT`, so "HEAD is the commit tagged `v%VERSION%`" is true
  on a normal release and on the reuse path (the last release commit), where
  the registry check then refuses as BR1-12 intends; the four pushes are
  unchecked and `scratch\*` is wiped today, as § 1.2 says.
- § 3 Tooling against `run-tests.bat` (three calls today), `run-deps-tests.bat`
  (the `uv run --no-project --with pytest` pattern), `run-e2e-tests.bat`
  (creates `vel_yantra_e2e` on an existing container), `init-test-db.sql`
  (S024's uncommitted version has `vel_yantra_test` and `vel_yantra_e2e`;
  `vel_yantra_upgrade` goes beside them). The four run-config files exist and
  hold the two deploy variables today.
- `/api/health` today returns `{"status": "ok"}` with no DB touch; § 1.1's
  change is one call plus one field. `init_db` loops `_MIGRATIONS` after
  `_get_applied_versions` under `GET_LOCK`, releasing in `finally`, so the
  precondition slot § 3 describes has its place.
- The deploy playbook already waits up to 2 min for `/api/version` 200 (24 ×
  5 s), which is public and touches no DB, so a guard-refused schema reaches
  `deploy.py`'s poll (the backend is up, `schema_ready` false) — the branch
  § 5.4 describes is reachable.
- Standards: ISO 55001 § 8.1, ISO/IEC 27001:2022 A 8.32 and A 8.13 (BR3-01
  is about meeting A 8.13 with the mechanism that exists), ISO 14224 § 7,
  SMRP 2.1.1 / 3.5.1 / 3.5.2, ISO 9001 § 10.2 — cited correctly; the
  squashing section of the base is quoted as it reads.
- Layering, UX and the device list: unchanged since round 2 and still right
  (pure `tickets_core` rule; one-line refusals; *Send back* hidden
  server-side; the important device check carries account, network and
  where; nothing on it a browser could judge).
- S024 in the working tree: still uncommitted; Q4's order (S025 after S024 is
  committed) stands and nothing in S024's files contradicts the brief.
