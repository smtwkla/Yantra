```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026: squashed schema U1, brief-reviews r1–r3, backup dropped U2)
Track: full
Status: Committed b6b8dfb (22-10-2026); important check pending: row 9 — the first release on production (Settings › Database shows schema 22, masters and Team intact)
Baseline: 3df667c
```

# S025 — Release safety and ticket integrity (audit fixes)

The user asked to "pull up important fixes as next step" from the audit
`docs/review/2026-10-21-smtw-review.md`. This step takes the findings that can
hurt production or the maintenance records: the next release (audit [1], [9],
[10]) and the integrity of tickets at the seams between modules ([2], [3], [4],
[6]). The rest of the audit is queued as two further steps (§ 1.8), so no
finding is left without a home step — the audit's recurring pattern.

**The user's facts and decisions (21-10-2026, U1):**
- Production is on v0.1.3 (schema v5) and has **no equipment rows**; it is the
  **only** Yantra database besides the disposable dev, test and e2e ones.
- "we can squish all migrations into one and use a higher version number" —
  "keep prod master tables that have data. i will drop the required tables
  manually … let the created masters remain."

So audit [1] is fixed at its root: the eight migrations v6–v13 that production
never ran are replaced, with v1–v5, by **one squashed migration v20** that
builds today's schema; production's master tables stay, the user drops the two
empty tables v9 would have changed, and v20 builds the rest.

**Track: full** — the migration engine and every table's definition, locking
rules on three write paths, the deploy script, RBAC-relevant unit rules.

**Depends on:** S018 committed (ae3841f) and S024 committed (3df667c); its
automated checks use S024's suite.

## 1. What will be built

1. **One squashed migration, v20, and a safe first release** (audit [1], U1):
   - **v20 "Full schema (squashed S001–S018)"** replaces v1–v13 in
     `local_db._MIGRATIONS`: every table of today's schema as `CREATE TABLE IF
     NOT EXISTS`, in today's exact shape (columns, keys, foreign keys, CHECKs,
     ENUMs), plus the idempotent data statements the old migrations carried
     (the `app_settings` defaults with `INSERT IGNORE`; S016's failure-code
     seed with `INSERT IGNORE`; S011's move of `user_units` rows into `people`
     and `person_units`, guarded by `NOT EXISTS` as v8 is). Later migrations
     continue from **v21**. The old migration texts are kept, frozen, as test
     fixtures only (§ 3 Tests).
   - **Why it is safe on each database:**
     - *a fresh database* (S024's e2e, a new install): v20 builds everything;
     - *production* (v1–v5, masters with data): v20's `CREATE … IF NOT EXISTS`
       skips the eight v1–v5 tables, all of which still have today's shape —
       no migration after v5 altered them except `equipment` and
       `equipment_events` — and creates the 19 missing ones. The two that v9
       changed are empty in production; the user drops them before the release (§ 5.1)
       and v20 recreates them in today's shape. `user_units` rows move into
       Team as v8 would have moved them. `db_version` keeps its rows 1–5
       (harmless; v20 is recorded beside them);
     - *dev and test* (at v13): every `CREATE` skips and every data statement
       is a no-op, so v20 is recorded and nothing changes — **no reset needed**.
   - **A guard (precondition) for v20.** Before applying v20, the engine checks
     that `equipment` and `equipment_events`, if they exist, already have
     today's shape (`equipment.model_id` present; the event ENUM holds v9's
     value). If either is in its v5 shape, **nothing is applied** and Settings
     › Database shows one line naming the old table(s), e.g. "Drop the old
     equipment and equipment_events tables first (they must be empty) — S025
     § 5.1" (BR3-05). The
     engine retries every 30 s as today, so once the tables are dropped it
     proceeds without a restart.
   - **Schema readiness on the health endpoint.** `/api/health` (public) calls
     `ensure_schema` itself and returns `{"status": "ok", "schema_ready":
     true|false}`, always HTTP 200 — no error text, no version numbers
     (BR1-01, BR1-16).
   - **The deploy checks it.** After the playbook, `tooling/deploy.py` polls
     `/api/health` at `DEPLOY_HEALTH_URL` every 10 s for up to 3 minutes until it
     answers 200 with `schema_ready: true` (a connection error is "not yet");
     otherwise it fails with the rollback lines (§ 5.4). Any non-200 (an
     nginx 502 while the backend starts) and any connection error count as "not
     yet"; at first boot the health call may wait on the migration lock while
     v20 runs, which the 3 minutes cover. `release.py` then stops
     before pushing the tag (its existing rule).
   - **No backup step in the deploy** (U2, 21-10-2026: "don't bother about
     backup"). db-server already dumps every database twice a day to the
     `ERP-DB-Backup` share (14 days, monitored, shipped to S3 — found by
     BR3-01 in the devops repo), and a backup step before each deploy, with
     migrations that could corrupt data, is queued for later (§ 1.8). For this
     release the user can trigger one dump by hand just before (§ 5.1).
   - **Tests that prove the squash** (§ 8): the schema v20 builds on an empty
     database is identical to the one v1–v13 build (columns, indexes, foreign
     keys, CHECKs, compared from `information_schema`); a v0.1.3 database with
     its masters filled, after the two drops, reaches today's schema with the
     masters intact; without the drops it is refused and unchanged.
2. **`build.bat` fails loudly** (audit [10]): every `docker build` and `docker
   push` is checked (`if errorlevel 1 exit /b 1`); it refuses to run with a
   dirty working tree or when HEAD is not the commit tagged `v%VERSION%`; it
   refuses to push a version tag that already exists in the registry
   (`docker manifest inspect`; a failed inspect counts as "absent" and the
   push's own check catches the rest); the refusal says "v<X> is already in the
   registry — nothing new to release; use the Deploy run config to redeploy"
   (`release.py` reuses the version when there is no new commit, BR1-12); it
   stops wiping `scratch\` (the dependency and e2e reports live there).
3. **JSON errors everywhere** (audit [9], BR1-04, BR1-05): an unknown `/api/*`
   path, a wrong method and any unhandled exception return `{"error": …}` with
   their status (404 "Not found", 405 "Not allowed", 500 "Something went wrong
   — try again"; the 500 handler logs the traceback itself, since Flask does
   not log what a handler answers); an `OperationalError` meaning a lost
   connection is a **503** "Database unavailable — try again shortly" like
   `DBUnavailable`. Other `OperationalError`s (1213 deadlock, 1205 lock wait —
   the accepted rare races) fall to the 500. Flask picks the most specific
   handler, so `ApiError`, `IntegrityError`, `RequestEntityTooLarge` keep
   theirs. The UI already shows `error`, so screens get a readable line
   instead of "INTERNAL SERVER ERROR".
4. **A unit used by tickets is frozen** (audit [2]): its code and site cannot
   change once any ticket names it, as already for equipment and access rows
   (S001 § 5: "frozen once used"); and a unit **cannot be deactivated while it
   has tickets not closed**: "Close its tickets first (N open)" — the same
   wording as the scrap refusal, which gains the count too (BR1-15).
   Deactivating a unit whose tickets are all closed stays allowed.
   What is frozen is the **unit record** (e.g. `SMTW.FWMILL` itself), not the
   machine: a machine with open tickets can still be moved to another unit,
   broken down or not, as today (S017 § 5.3: the ticket keeps the unit it was
   raised in, and is seen from both). If the move is the fix, the ticket is
   closed as usual (U3, 21-10-2026).
5. **No send-back after a repeat** (audit [3], BR1-07): a ticket that has been
   raised again as a repeat (another ticket's `repeat_of_id` points at it) can
   no longer be sent back: 409 "This ticket came back as TK-…; work on that
   one". The page does not offer *Send back* there (the server's `moves`
   leaves it out, from an unfiltered "has a repeat", so a user who cannot see
   the repeat is not offered it either). The raise re-reads the earlier
   ticket's state under the lock its foreign key already takes, so a raise and
   a send-back at the same moment cannot both succeed.
6. **Scrap vs ticket edit** (audit [4], BR1-06): the ticket edit checks the new
   component "not scrapped" from the **component row alone, locked** (`LOCK IN
   SHARE MODE`, the lock its foreign key takes anyway); its parent is read
   plain. So a scrap and an edit at the same moment cannot leave an open ticket
   on scrapped equipment, and no new lock-order edge appears. The lock-order
   notes in `tickets.py` and `equipment.py` list the two foreign-key locks
   they miss.
7. ***Machine stopped* shows its refusal** (audit [6]): when the server
   refuses (another operator already made it a breakdown), the dialog shows
   the message and the page reloads the ticket.
8. **The rest of the audit gets a home** — Queued rows in
   `docs/steps/README.md`:
   - **Auth hardening** (about a day): audit [7], [8], [11], [12], [16]–[20],
     and the auth test gaps of [28];
   - **Tidy-up** (about a day): audit [13], [14], [21]–[27] and the remaining
     test gaps of [28];
   - **Module and schema docs** (audit [15]) stays a separate queued item;
     v20 itself becomes the readable schema in the meantime;
   - **Safe migrations** (U2): a backup before every deploy through the devops
     repo's `erp_spanner.py backup` convention (BR3-01 option a), and guarding
     migrations that could corrupt existing data — "we will work on [MIGRATE
     causing data corruption] later on".
9. **A warning about migration SQL in the shared rules** (U2: "add to
   CLAUDE-COMMON or SMTW-WebApp-Base warning of being careful about migrate
   SQL"): both files are synced from smtw-common, so a local edit would be
   overwritten at the next sync. The impl report gives the text, ready to
   paste into smtw-common's `SMTW-WebApp-Base.md` § Local DB Migration Pattern
   (where the migration rules live; CLAUDE-COMMON keeps its one-line
   invariant) — what to check before a migration that touches existing rows
   (a `NOT NULL` column or a foreign key on a table with rows, a dropped
   column the previous image still reads, data that cannot be converted), the
   precondition pattern of § 3, a test from the production schema, and a
   backup before the deploy. The user applies it in smtw-common.
10. ***Not a fault* after *Start*** (audit [5], U4 — the user: allow): the
    move `not-a-fault` is allowed from **in progress** too
    (`tickets_core.MOVES`), so a technician who pressed *Start* on arrival,
    looked and found nothing can still close the ticket as not a fault. Its
    times are then blank like any not-a-fault ticket, so it stays out of MTBF
    and MTTR; labour already logged stays on the ticket. The page offers the
    button there (from the server's `moves`, no screen logic). Tests: the move
    from in progress, its times blank; the e2e flow Start → Not a fault.

### Out of scope

- Everything the queued steps take (§ 1.8).
- The audit's hindsight items (READ COMMITTED vs locking reads, intervals for
  KPIs, a global masters key, the deny-list default).
- Editing the devops repo or any production machine: the two `DROP TABLE`
  lines are delivered as text for the user (§ 5.1).
- A backup step in the deploy (U2): queued as *Safe migrations* (§ 1.8).
- Releasing or deploying: the user runs the release.
- A general precondition framework: v20's guard is the one precondition; the
  dict that holds it can take another when a later migration needs one.

## 2. Standards and practice

- **ISO 55001 § 8.1 (operational planning and control) and ITIL change
  management**: a change to a live system is planned, can be backed out, and
  is verified after it is made. The squashed schema with its guard plans the
  change for production's real state and the schema-ready check verifies the
  result; the way back is db-server's dumps for now (U2), with a backup step
  in the deploy queued.
- **ISO/IEC 27001:2022 A 8.32 (change management)** asks for the same.
  **A 8.13 (information backup)** asks for backups taken and tested: db-server
  takes them; testing a restore is part of the queued *Safe migrations* step.
- **ISO 14224:2016 § 7 (quality of data)**: failure records must be complete,
  consistent and traceable; a breakdown that moves to another site after the
  fact, or one stop counted twice, corrupts the history that MTBF, MTTR and
  availability (SMRP 3.5.1, 3.5.2, 2.1.1) are computed from. Findings [2]–[4]
  are data-quality fixes in that sense.
- **ISO 9001 § 10.2 (corrective action, effectiveness)**: the repeat link is
  how Yantra shows a repair did not hold; a send-back after a repeat would
  count one failure as both "not fixed" and "came back".
- **Migration squashing** (SMTW-WebApp-Base § Migration squashing): done after
  the user's explicit confirmation, with every instance considered (U1: one
  production, disposable dev/test/e2e). The base squashes into a v1; Yantra
  uses **v20** because production has v1–v5 recorded — a squashed v1 would be
  skipped there (a recorded departure, § 7.1); and the base's "dev databases
  must be recreated" does not apply, since v20 is a no-op on a v13 database
  (a second recorded departure, BR2-08).

## 3. Where

### Backend
- `backend/local_db.py`:
  - `_MIGRATIONS` = `[ (20, "Full schema (squashed S001–S018)", [...]) ]`; the
    comment above it says v1–v13 were squashed on 21-10-2026 (S025), that
    production had applied v1–v5 only, and that new migrations continue at
    v21; `LATEST_VERSION` follows.
  - `_PRECONDITIONS = {20: _v20_shape_check}` — a function of the cursor that
    returns `None` or the refusal message (it reads `information_schema` for
    the two tables, always with `TABLE_SCHEMA = DATABASE()`, since the dev
    server hosts four Yantra databases (BR2-03); a table that is absent passes,
    BR1-08; the message names which table is still old); `init_db` runs the
    preconditions of every pending version after `_get_applied_versions`,
    inside the migration lock, before applying any; a failure raises
    `MigrationBlocked` (a `DBUnavailable`), which `ensure_schema` keeps as
    `_last_error` (already shown in Settings › Database).
  - `is_connection_lost(code)` with the two code sets moved from `worker.py`
    (2000–2999, 1053, 1927) (BR1-05).
- `backend/worker.py`: uses `local_db.is_connection_lost`.
- `backend/app.py`: `/api/health` calls `ensure_schema(DB_CONFIG)` and adds
  `schema_ready`.
- `backend/api_common.py`: `register_error_handlers` gains `HTTPException` →
  `{error}` with a small code → text table (404, 405, 500 and the rest
  Werkzeug's name), `OperationalError` → 503 when `is_connection_lost`, else
  the 500, `Exception` → `logger.exception` + 500.
- `backend/masters.py`: `_unit_is_referenced` counts `tickets` (`LOCK IN SHARE
  MODE`, as `_check_code_frozen`); the unit deactivation guard refuses a unit
  with tickets not closed, and runs **before** the existing equipment guard,
  so the open-ticket count is the message the user sees first (BS1-04);
  docstrings fixed.
- `backend/equipment.py`: the scrap refusal message gains the count; the
  lock-order docstring (the ticket edit's FK lock).
- `backend/tickets.py`: `_send_back` refuses when a repeat exists; `_detail`
  computes `has_repeat` unfiltered (`EXISTS … repeat_of_id = %s`) for `moves`;
  the raise with `repeat_of_id` re-reads the earlier ticket `LOCK IN SHARE
  MODE` after the insert; `_check_component` locks the component row alone
  and reads the parent plain; the lock-order docstring.
- `backend/tickets_core.py`: `allowed_moves(state, held_keys, has_repeat=False)`
  and `send_back_error(has_repeat)` (pure), used by the route and the detail.

### Frontend
- `frontend/src/views/tickets/RegradeDialog.vue`: show a refusal on
  `intensity` in "stopped" mode; emit `reload` on a 400 or 409 it cannot show
  beside a field.

### Tooling
- `tooling/deploy.py`: after the playbook, the health poll
  (`DEPLOY_HEALTH_URL`, required for a deploy — missing → abort, like
  `DEPLOY_WS_SESSION`; not for `--check`, BR1-09); the poll takes its opener
  and clock as parameters, for the tests; it reads the current `YANTRA_VER`
  before stamping, and on **any** failure after the stamp (the playbook or the
  poll) prints the rollback lines (§ 5.4, BR3-04).
- `.idea/runConfigurations/Deploy.xml` and the three `Release__*.xml`: the new
  variable (the public URL of `/api/health`, from the user).
- `tooling/build/build.bat`: checks, refusals, no `scratch\` wipe (§ 1.2).
- `tooling/tests/test_deploy.py` (new) and `tooling/run-tooling-tests.bat`
  (new, on the `run-deps-tests.bat` pattern: `uv run --no-project --with pytest
  --with python-dotenv`), added to `tooling/run-tests.bat` (BR1-11).
- `tooling/dev/init-test-db.sql`: creates and grants `vel_yantra_upgrade`;
  `tooling/run-backend-tests.bat` creates it on an existing container as
  `run-e2e-tests.bat` creates `vel_yantra_e2e` (BR1-03).
- `.claude/CLAUDE.md`: the deploy bullet names `DEPLOY_HEALTH_URL`; the
  migrations note says v1–v13 are squashed into v20 and new
  ones start at v21, and that a migration that cannot run on existing data
  gets a precondition, never an edit. The `## SMTW-Review` section gains one
  point (BS1-01): "**Migrations**: `_MIGRATIONS` starts at v20 (squashed
  21-10-2026); v1–v13 live only in `backend/tests/fixtures/migrations_v13.py`
  and are never edited; a migration that touches rows that exist in
  production carries a `_PRECONDITIONS` entry and a test from the production
  schema. Check both on every migration after v20."

### Tests
- `backend/tests/fixtures/migrations_v13.py` (new): a frozen copy of v1–v13
  from `ae3841f`, never edited. v1–v5 there are byte-identical to `v0.1.3`'s,
  so the production-path test uses its first five entries. The tests run a
  fixture list by `monkeypatch.setattr(local_db, "_MIGRATIONS", …)`; the
  engine needs no change for it (BR2-04). The upgrade database is dropped and
  created by the test itself, as `e2e_backend.py` does.
- `backend/tests/test_migration_v20.py` (new), in `vel_yantra_upgrade`:
  - **equivalence**: build with the v1–v13 fixture, read the schema from
    `information_schema` (all filtered by `TABLE_SCHEMA = DATABASE()`); drop
    everything; build with v20; the two are equal (BR2-02). Compared:
    - tables with `ENGINE` and `TABLE_COLLATION`;
    - columns with `ORDINAL_POSITION`, `COLUMN_TYPE` (ENUM text included),
      `IS_NULLABLE`, `COLUMN_DEFAULT`, `EXTRA` (the `ON UPDATE` on
      `app_settings`) — v20 reproduces today's column order, e.g. `notes` last
      in `equipment`, `model_id` after `type_id`;
    - indexes by name, uniqueness and column order (`STATISTICS`), including
      the indexes MariaDB creates for foreign keys;
    - foreign keys by name: columns in order, referenced table and columns,
      `DELETE_RULE`/`UPDATE_RULE`;
    - `CHECK_CONSTRAINTS.CHECK_CLAUSE` by name;
  - **production path**: build with the v1–v5 fixture, fill v0.1.3-shaped
    masters (sites, units, classes, types, `user_units`, settings) and no
    equipment; run `init_db`: refused, `db_version` max still 5, nothing
    created; drop `equipment_events` and `equipment`; run again: v20 recorded,
    schema equal to the equivalence reference, the masters unchanged, the
    `user_units` rows moved into `people`/`person_units`;
  - **dev path**: a v13 database gets v20 recorded with no table changed;
  - **re-run**: v20 twice is a no-op.
- The old `test_migration_v8.py` … `v13.py` (BR2-07): tests of a table's
  shape or a constraint stay unchanged (they test today's schema, whichever
  migration built it); the data-movement re-runs (v8's `user_units` move,
  v11's seed) re-target `version = 20`; tests that only re-run a version are
  dropped (the v20 re-run test covers them). `test_modules.py`'s
  `LATEST_VERSION` asserts hold as they are. The report lists each file's
  fate. The `created_by` tags `'migration-v8'` and `'migration-v11'` are kept
  verbatim in v20's data statements (conftest's `SEED_CREATOR` and
  `test_failure_codes_api.py:241` depend on them).
- `backend/tests/test_health.py` (new): `schema_ready` true, and false with
  `ensure_schema` monkeypatched to return an error on the module the route
  imports it from (the `test_auth.py:66` pattern; `init_db` would not run,
  since the session's schema is already ready, BR2-06); HTTP 200 both ways.
- `backend/tests/test_errors.py` (new): 404, 405, 500 and an
  `OperationalError` 2013 → 503, all JSON; a 1213 → 500.
- The five tests that use `pytest.raises(RuntimeError)` through the client to
  prove a rollback (`test_tickets_api.py:94`, `test_equipment_api.py:101, 502`,
  `test_documents_api.py:288, 466`) assert the 500 JSON body instead; the
  side effect they test still holds (BR1-04).
- `test_masters_api.py`: unit code/site frozen by a ticket; deactivation
  refused with an open ticket, allowed with only closed ones.
- `test_ticket_work_api.py`: send-back refused after a repeat; `moves` without
  `send-back` (also for a user who cannot see the repeat); a raise against a
  ticket sent back in between is refused; the component edit's locked read (a
  scrapped component refused). `test_tickets_core.py`: `allowed_moves` with
  `has_repeat`.
- `tooling/tests/test_deploy.py`: the poll (ready, not yet, non-200,
  timeout, connection error), the required variable, the rollback lines.
- e2e (S024's suite): *Machine stopped* refused shows its message; no *Send
  back* on a ticket with a repeat; the unit deactivation refusal shows.
  Follow the suite's conventions (BS1-03):
  - declare each expected refusal with `consoleWatch.allowFailedRequest`:
    `("/regrade", 400)` for *Machine stopped* (a 400 on `intensity`) and
    `("/api/masters/units/", 409)` for the unit;
  - provoke the re-grade with a new `regradeByApi` beside `moveByApi` in
    `support/tickets.js` (`moveByApi` builds `/moves/<move>` only; fix its
    docstring);
  - check messages with `expectFieldMessage`;
  - build a repeat as the "Not fixed — raise again" test in
    `tickets-work.spec.js` does (`raiseByApi`, restore, `raiseByApi` with
    `repeat_of_id`);
  - the unit test raises a ticket on `E2E MCC1 mill`, deactivates
    `SMTW.MCC1` as `it_admin`, sees "Close its tickets first (1 open)", and
    closes its ticket at the end, since the three projects share one
    database.
- `frontend/e2e/masters.spec.js:10`: the comment "migration v11" becomes "v20
  (S016's seed)"; the constant stays 14 (BS1-05).

### Docs
- `docs/steps/README.md`: the Queued rows (§ 1.8).
- `docs/Plan.MD` § 4.1: units frozen by tickets; § 4.2: no send-back after a
  repeat; § 5: the schema is one migration v20 (squashed 21-10-2026), and the
  `user_units` row says it is legacy, moved into Team by v20 (BR2-08).

## 4. Data model

No table or column changes: v20 is today's schema. The migration list becomes
one entry; the old ones live on only as test fixtures.

## 5. Rules

### 5.1 Production's first release after the squash (the user's actions)

Ready-to-paste for the user, also in the impl report; run on production before
the release, in this order:
1. Optional (U2): trigger db-server's dump once just before, so the newest
   dump in `ERP-DB-Backup` is from this morning (BR3-06).
2. Check the two tables are empty:
   `SELECT COUNT(*) FROM equipment; SELECT COUNT(*) FROM equipment_events;`
   — both 0 (the user confirmed 21-10-2026 there is no equipment).
3. Drop them: `DROP TABLE equipment_events; DROP TABLE equipment;` (events
   first: they reference equipment).
4. Run the release. v20 builds the rest; the deploy waits for `schema_ready`.

If step 3 is forgotten, v20's guard refuses and changes nothing; the new image
serves 503 on every DB route until the tables are dropped, after which the
next retry (≤ 30 s) builds the schema — no redeploy needed.

### 5.2 Send-back and repeats

- A ticket with any repeat (`EXISTS tickets WHERE repeat_of_id = id`,
  unfiltered) cannot be sent back (409). It can still be closed: the repair it
  records did happen; the repeat ticket carries the failure that came back.
- Raise with `repeat_of_id`: after the insert, `SELECT state, not_a_fault FROM
  tickets WHERE id = %s LOCK IN SHARE MODE` and the existing
  `latest_restoration` rule; a refusal rolls the raise back (400 on
  `repeat_of_id`, the existing message).
- Order: a send-back holds the earlier ticket's row `FOR UPDATE`; the raise
  takes the shared lock after its own inserts. Whichever commits first wins;
  the other sees the committed state and is refused. No new lock-order edge:
  the raise already takes that shared lock through the foreign key. (Corrected,
  CR1-02: a state change also takes the machine's shared foreign-key lock, so
  when the two overlap they can deadlock; InnoDB rolls one side back, 1213, a
  retry gives the right answer. "Whichever commits first wins" holds only when
  they do not overlap.)

### 5.3 Units and tickets

- "Referenced" for a unit now means: an access row, any equipment row, or
  **any ticket** (`tickets.unit_id`), open or closed.
- Deactivation: refused while `tickets.unit_id = unit AND state <> 'closed'`
  has rows; "Close its tickets first (N open)". The count is a locking read
  under the unit's lock, as the equipment guard.

### 5.4 When a deploy fails

`deploy.py`'s failure message for a schema that is not ready ends with the
rollback the user runs on the Ansible workstation (production changes are the
user's), and so does any other failure after the stamp (BR3-04):
- before v20 has applied (the guard refused, or the database was down): stamp
  the previous version and redeploy. `deploy.py` reads the current
  `YANTRA_VER` line before it stamps (BR2-05) and prints the two lines built by
  the same helper `stamp()` uses, with that previous version filled in: the
  stamp command and `./erp_spanner.py deploy vel yantra master`;
- after v20 has applied: the old image does not run on the new schema, so a
  rollback is a restore of db-server's latest dump, then the same two lines.

Since production has no equipment and the masters tables are untouched by v20,
the second case is unlikely; the message names both.

## 6. API

No new endpoint. `/api/health` gains `schema_ready`. New error bodies for 404,
405, 500 and the connection-lost 503. `PUT /api/units/<id>` gains two refusals;
`POST /api/tickets/<id>/moves/send-back` one; the detail's `moves` drops
`send-back` when a repeat exists.

## 7. Design decisions

1. **Squash into v20, not v1** (U1, a departure from the base's "single v1"):
   production has v1–v5 recorded, so a squashed v1 would be skipped there and
   its tables never created. v20 is pending everywhere, and `CREATE … IF NOT
   EXISTS` makes it a no-op where tables already exist in today's shape. v20
   reproduces today's column order exactly (e.g. `notes` last in `equipment`),
   so a v20 database and a v13 one are indistinguishable (BR2-02, BR3-07).
   *Rejected:* squashing only v6–v13 into one ALTER-based migration (keeps five
   migrations nobody needs to read, and ALTERs written against v5 cannot run
   on dev/test at v13 without guards per statement); recreating production's
   database (loses its masters, which the user wants kept).
2. **The user drops the two empty tables; v20 does not alter them**: v20 stays
   pure `CREATE` + idempotent data, the same on every database; the one place
   production differs is handled by a guard that refuses and an explicit,
   reviewed manual step. *Rejected:* conditional `ALTER`s inside v20 for a v5
   `equipment` (code that runs once, on one database, and is untestable after).
3. **Refuse all on a failed guard**: the schema stays exactly as it was, so the
   previous image runs again after a stamp-and-redeploy, without a restore.
   The new image serves 503 meanwhile — a refused release is an outage until
   the drop or the rollback (BR1-02), which is why § 5.1 puts the drop before
   the release.
4. **No backup step in this step** (U2): db-server's twice-daily dumps are the
   way back for now; the deploy-time backup is designed with the queued *Safe
   migrations* step, on the devops repo's `erp_spanner.py backup` convention
   (BR3-01). *Rejected for now:* a playbook task the app VM cannot run (no
   dump tool, no backup share, BR3-01).
5. **`schema_ready` only, on the public health endpoint, and the route triggers
   the retry**: the deploy needs a yes/no from whichever worker answers;
   the reason stays behind `settings:read`. *Rejected:* reading a per-process
   flag (stays false on a worker that has not retried, BR1-01); a detailed
   public status (leaks versions and errors, audit [18]).
6. **Send-back refused after a repeat, close still allowed**. *Rejected:*
   auto-closing the earlier ticket when its repeat is raised (skips the
   engineer's coding).
7. **Locked reads at the two seams**, not READ COMMITTED: the smallest change
   that closes [3] and [4]; the isolation decision waits for the next write
   path.

## 8. Tests and acceptance

### Automated
- pytest: the v20 equivalence, production-path, dev-path and re-run tests;
  `schema_ready`; the JSON error handlers; unit freeze and deactivation;
  send-back after a repeat (refused, not offered); the raise re-check; the
  component's locked read; the five rollback tests on JSON bodies.
- tooling: `test_deploy.py` (poll, variable, rollback lines).
- e2e (S024's suite): *Machine stopped* refused shows its message (provoked by
  re-grading the defect through the API with the test headers while the
  operator's dialog is open, then saving it); no *Send back* on a ticket with a
  repeat; the unit deactivation refusal shows; every screen still opens on a
  database built by v20.
- `tooling/run-tests.bat` and `tooling/run-e2e-tests.bat` green. Dev and test
  databases are **not** reset (v20 records itself as a no-op there).

### On a real device
- **Important:** the first release after the squash, run by the user — § 5.1
  steps 1–3 on production; the release; the deploy waits for `schema_ready`
  and passes; Settings › Database shows schema 20; the masters are there
  (sites, units, classes, types; former unit-access users now in Team with
  their units). If refused or failed: § 5.4.
  Account: KLA (admin); network: plant; where: production.

### Acceptance
Green suites; the equivalence test passes; the production path is refused
without the drops and succeeds with them; the deploy poll works against a
fake; the Queued rows exist; the migration warning text is in the impl
report.

## 9. Open questions and assumptions

1. ~~The backup task~~ — dropped from this step by the user (U2); queued as
   *Safe migrations*.
2. ~~*Not a fault* after *Start*~~ — settled (U4): allowed, § 1.10.
3. ~~Production's state~~ — settled (U1): v0.1.3, no equipment, the only
   instance.
4. ~~**Order with S024**~~: settled; S024 committed as 3df667c.
5. **Assumption:** the registry check (`docker manifest inspect`) works with
   the credentials `build.bat` already uses for `docker push`.
6. ~~The run-config value~~ — settled (U5): `DEPLOY_HEALTH_URL` is
   `https://vel-yantra.mspv.app/api/health`.

## 10. Amendments

### A1 — Pillow 13 (security upgrade)

```
Requested by: KLA, 21-10-2026 ("yes to all three", to adding the upgrade)
Status: Approved 21-10-2026 by KLA
```

**Why.** The dependency check (S022, `tooling/run-deps-audit.bat`) exits 1:
Pillow 12.3.0, the image library behind photo thumbnails and QR labels, has
7 high and 2 moderate known vulnerabilities, all fixed in 13.0.0 (ISO/IEC
27001:2022 A 8.8, management of technical vulnerabilities).

**What changes.** `backend/pyproject.toml` requires `pillow>=13.0.0`;
`uv.lock` and `sbom/` regenerated (committed with it, per CLAUDE.md). The coder
reads Pillow 13's release notes for removed or changed APIs that Yantra uses
(thumbnails, EXIF orientation, label rendering) and lists them in the report;
a change beyond a version bump is stated there.

**Where.** `backend/pyproject.toml`, `backend/uv.lock`, `sbom/backend.cdx.json`
and any file a Pillow API change touches.

**Tests.** The backend suite (uploads, thumbnails, labels) green; the deps
audit exits 0 for Pillow; the e2e photo and label tests green.

**Open points.** None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

Answered together with the user's change U1 (squashed schema), which replaced
the v9 precondition design the round reviewed.

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 health must trigger the retry | major | **Accepted**: `/api/health` calls `ensure_schema` (§ 1.1, § 3, § 7.5) |
| BR1-02 decision 2's premise; no rollback | major | **Accepted**: decision 3 rewritten (the new image serves 503; the schema stays untouched so the old image can return); § 5.4 rollback lines in the deploy message; the important device check carries the branch; § 5.1 puts the drop before the release |
| BR1-03 no database for the upgrade test | major | **Accepted**: `vel_yantra_upgrade` on S024's e2e pattern (§ 3 Tooling, Tests) |
| BR1-04 the generic handler and five tests | minor | **Accepted**: the five points in § 1.3 / § 3; the five tests assert the 500 body |
| BR1-05 lost-connection codes in one place | minor | **Accepted**: `local_db.is_connection_lost`, used by the worker and the handler |
| BR1-06 the joined parent's lock | minor | **Accepted**: the component row alone is locked (§ 1.6) |
| BR1-07 unfiltered has-repeat | minor | **Accepted**: `has_repeat` unfiltered; `allowed_moves(…, has_repeat=False)` |
| BR1-08 precondition on an absent table | minor | **Accepted** in the new design: the v20 guard reads `information_schema`; an absent table passes; run after `_get_applied_versions` inside the lock |
| BR1-09 deploy.py gate scope, URL, run configs | minor | **Accepted** (§ 3 Tooling) |
| BR1-10 a set-once flag attests nothing | minor | **Accepted** (option b): `DEPLOY_BACKUP_TASK` and the playbook-output check |
| BR1-11 tooling test home | minor | **Accepted**: `tooling/tests/` + `run-tooling-tests.bat`, in `run-tests.bat` |
| BR1-12 build.bat vs release.py's reuse | minor | **Accepted**: the refusal message names the Deploy run config; a failed inspect counts as absent (§ 1.2) |
| BR1-13 citations | nit | **Accepted**: ISO 14224 § 7; SMRP 3.5.2 added |
| BR1-14 test file names | nit | **Accepted**: `test_health.py` (new) |
| BR1-15 two message wordings | nit | **Accepted**: one wording with the count for scrap and unit; the guard's message leads with the action |
| BR1-16 health stays 200 | nit | **Accepted** (§ 1.1) |

### U1 — user change, 21-10-2026 (during round 1)

"PROD has not migrated, is on v0.1.3"; "we can squish all migrations into one
and use a higher version number"; "No equipment rows in PROD yet"; "keep prod
master tables that have data. i will drop the required tables manually. we can
also reset the version number on PROD to 1. but let the created masters
remain"; "no other databases apart from the one instance of PROD". → § 1.1, § 3,
§ 5.1, § 5.4, § 7.1–7.3, § 8, § 9 Q3. Resetting production's `db_version` is not
needed: v20 is pending there whatever rows 1–5 say, and the guard checks the
tables' shape, not the version rows.

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 the backup check runs after the deploy | major | **Accepted**: a pre-check that the task is in the playbook, before stamping (abort, nothing changed); the post-check that it ran says "take a dump now", no rollback advice; role-prefixed task names matched; Q1 resolved to "add the task before this release" (§ 1.1, § 5.4, § 9 Q1) |
| BR2-02 what the equivalence test compares | minor | **Accepted**: the list in § 3 Tests; v20 reproduces today's column order |
| BR2-03 `TABLE_SCHEMA = DATABASE()` | minor | **Accepted** (guard and tests); the refusal names the old table |
| BR2-04 how fixtures run | minor | **Accepted**: `monkeypatch.setattr(local_db, "_MIGRATIONS", …)`; one fixture file (v1–v5 identical) |
| BR2-05 the previous version for the rollback | minor | **Accepted**: read before stamping; lines from `stamp()`'s helper |
| BR2-06 the health false case | minor | **Accepted**: monkeypatch `ensure_schema` |
| BR2-07 the old migration tests' fate | nit | **Accepted**: shape tests kept, data re-runs re-targeted to v20, pure re-runs dropped; `created_by` tags verbatim |
| BR2-08 departure from "recreate dev DBs"; Plan.MD `user_units` | nit | **Accepted** (§ 2, § 3 Docs) |
| BR2-09 non-200 as "not yet"; lock wait at first boot | nit | **Accepted** (§ 1.1) |
| BR2-10 restore into a fresh DB; the e2e provocation | nit | **Accepted** (§ 8) |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 the backup cannot run where the brief puts it | major | **Settled by the user (U2)**: no backup step in S025; db-server's twice-daily dumps stand; the deploy-time backup (option a) is queued as *Safe migrations* (§ 1.1, § 1.8, § 7.4) |
| BR3-02 leftover post-check wording | minor | **Moot** (U2): the backup checks are gone |
| BR3-03 `--stamp-only` skips the backup | minor | **Moot** (U2) |
| BR3-04 rollback lines on any failure after the stamp | minor | **Accepted** (§ 3 Tooling, § 5.4) |
| BR3-05 guard message wording; a garbled sentence | nit | **Accepted**: one message, naming the old table (§ 1.1, § 3) |
| BR3-06 § 5.1 step 1 stale; where the dump is | nit | **Accepted**: step 1 is the optional dump on db-server (U2) |
| BR3-07 column order in § 7 | nit | **Accepted**: decision 1 says v20 reproduces today's column order |

### U2 — user change, 21-10-2026 (at gate A)

"don't bother about backup. we will work on [MIGRATE causing data corruption]
later on. maybe we can just add to CLAUDE-COMMON or SMTW-WebApp-Base warning
of being careful about migrate SQL" → § 1.1 (no backup step), § 1.8 (*Safe
migrations* queued), § 1.9 (the warning, as text for smtw-common since both
files are synced), § 2, § 3, § 5.1, § 5.4, § 7.4, § 8, § 9 Q1, Q6.

### U3 — user question, 21-10-2026 (at gate A)

"A unit used by tickets is frozen — i doubt if it is correct. suppose a machine is down. it may still be relocated without executing a fix. may be relocating it is the fix." → no design change: the freeze is on the unit record, not the machine; moving a machine with open tickets stays allowed (S017 § 5.3). § 1.4 now says so.

### U4 — user decision, 21-10-2026 (at gate A)

Q2 "Allow Not a fault after Start? I propose yes" → allowed; folded into § 1.10 (the brief is not yet approved, so no amendment); removed from Out of scope.

### U5 — user answers, 21-10-2026 (gate A)

Q6 "yes, use that URL" → `DEPLOY_HEALTH_URL=https://vel-yantra.mspv.app/api/health` in the Deploy and Release run configs. "brief approved" → Approved 21-10-2026; Baseline from r3's *Reviewed against:*.

### Code review r1 — `4-code-review-r1.md`, CR1-02 answered 22-10-2026

**Accepted**, wording only: § 5.2 "Order" now says that overlapping raise and send-back can deadlock (1213, accepted, retry works), because a ticket state change takes shared foreign-key locks on the machine, unit and component rows. The lock-order notes in `tickets.py` and `equipment.py` list the two new accepted deadlocks (repeat raise against send-back; unit edit against a ticket move).

### Staleness check s1 — `2-brief-review-s1.md` (Fable), answered 21-10-2026

Against 3df667c (S024 committed). Verdict: no blocker or major.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 the new `## SMTW-Review` rule in CLAUDE.md | minor | **Accepted** (option a): one *Migrations* point (§ 3 Tooling) |
| BS1-02 S024 still described as in progress | nit | **Accepted**: intro, Status, § 9 Q4; `Baseline: 3df667c` |
| BS1-03 the e2e suite's conventions | nit | **Accepted**: listed under § 3 Tests; a `regradeByApi` helper |
| BS1-04 which deactivation guard runs first | nit | **Accepted** (option a): the ticket guard first; the e2e test closes its ticket |
| BS1-05 "migration v11" in `masters.spec.js` | nit | **Accepted** (§ 3 Tests) |
