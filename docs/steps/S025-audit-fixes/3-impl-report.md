```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: impl-report
Author: Coder (Opus)
Date: 21-10-2026
```

# S025 — Implementation report

**Result: the brief, A1 (Pillow 13) and U1–U5 are built, and every suite is green.**
- Backend: 1855 passed.
- Frontend: 93 unit tests passed; `vite build` passed.
- Dependency audit: 42 tests passed; the audit exits 0 with 0 vulnerabilities.
- Tooling: 20 tests passed.
- Browser suite: 147 passed in 5.2 min (49 tests × 3 projects: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium); 0 failed, 0 skipped.

The step departs from the brief in one place: the e2e unit test expects the real number of open tickets at `SMTW.MCC1`, not "(1 open)" (§ 4, decision 9). No question is open for the user.

## Questions for the user

None.

## 1. What was built

1. **Squashed migration v20 with a guard** (audit [1], U1).
   - `local_db._MIGRATIONS` now holds one entry: v20, "Full schema (squashed S001–S018)".
   - It creates all 27 tables in today's exact shape, with `CREATE TABLE IF NOT EXISTS`.
   - It then runs the idempotent data statements: the two setting defaults, the move of `user_units` rows into Team (was v8), and the failure-code seed (was v11).
   - A precondition (`_PRECONDITIONS = {20: _v20_shape_check}`) stops v20 while `equipment` or `equipment_events` still has its v5 shape. The refusal names the old table(s), and nothing is applied.
   - v1–v13 survive only as a frozen test fixture.
2. **Schema readiness on `/api/health`.** The endpoint answers `{"status": "ok", "schema_ready": true|false}`, always with HTTP 200. It calls `ensure_schema`, so the answer is fresh, and a call retries the migrations at most every 30 s.
3. **The deploy waits for the schema.**
   - After the playbook, `tooling/deploy.py` polls `DEPLOY_HEALTH_URL` every 10 s for up to 3 minutes.
   - `DEPLOY_HEALTH_URL` is required for a deploy, but not for `--check` or `--stamp-only`.
   - The script reads the current `YANTRA_VER` before it stamps. On any failure after the stamp (the playbook or the poll), it prints the rollback lines (§ 5.4).
4. **`build.bat` fails loudly.** Every `docker push` is now checked. The script refuses three cases:
   - a working tree with changes;
   - a HEAD that is not the commit tagged `v%VERSION%`, or no such tag;
   - a version already in the registry. The message is "v<X> is already in the registry … use the Deploy run config to redeploy".

   It no longer wipes `scratch\`.
5. **JSON errors everywhere** (audit [9]):
   - an unknown path answers 404 "Not found";
   - a wrong method answers 405 "Not allowed";
   - an unhandled exception answers 500 "Something went wrong — try again", and the traceback is logged;
   - a lost connection (`OperationalError` 2000–2999, 1053, 1927) answers 503 "Database unavailable — try again shortly";
   - any other `OperationalError`, such as a 1213 deadlock, answers the plain 500.
6. **A unit used by tickets is frozen** (audit [2]):
   - Any ticket, open or closed, freezes a unit's code and site.
   - A unit with tickets not closed cannot be deactivated: "Close its tickets first (N open)". This check runs before the equipment check (BS1-04).
   - The scrap refusal now gives the count too, with the same wording.
   - A machine with open tickets can still move to another unit (U3).
7. **No send-back after a repeat** (audit [3]):
   - A ticket that came back as a repeat answers 409 "This ticket came back as TK-…; work on that one".
   - `moves` leaves out `send-back` even when the user cannot see the repeat.
   - The raise re-reads the earlier ticket under its shared lock after the insert, so a raise and a send-back at the same moment cannot both succeed.
8. **Scrap against a ticket edit** (audit [4]). The edit reads the new component `LOCK IN SHARE MODE`, the component row alone, and decides "not scrapped" from that row. Both lock-order notes now list the two foreign-key locks.
9. ***Machine stopped* shows its refusal** (audit [6]). In "stopped" mode, an `intensity` refusal shows at the top of the dialog. Any 400 or 409 that no visible field shows also makes the page reload the ticket.
10. ***Not a fault* after *Start*** (U4). The move is allowed from *in progress*. Its times stay blank, and its labour stays on the ticket.
11. **The rest of the audit has a home.** Four Queued rows are added to `docs/steps/README.md`: Auth hardening, Tidy-up, Module and schema docs, Safe migrations.
12. **A1, Pillow 13.0.0.**
    - `pyproject.toml` now requires `pillow>=13.0.0`.
    - `uv.lock` and `sbom/backend.cdx.json` are regenerated.
    - The deps audit exits 0 with 0 vulnerabilities.

## 2. How it works

**The engine.**
- `init_db` takes the migration lock and reads the applied versions, as before.
- It then builds the list of pending versions and runs the precondition of each one first.
- If any precondition answers with a message, it raises `MigrationBlocked`, a subclass of `DBUnavailable`, before any statement runs.
- `ensure_schema` already catches `DBUnavailable` and keeps the message as `_last_error`, which Settings › Database shows. Every later call retries after 30 s, so once the tables are dropped the next retry applies v20 without a restart.
- `_v20_shape_check` reads `information_schema` with `TABLE_SCHEMA = DATABASE()`:
  - `equipment` without `model_id` is old;
  - `equipment_events` whose `event` ENUM lacks `'model'` is old;
  - a table that is absent passes.

**v20 on each database.**

| Database | What v20 does |
|---|---|
| Empty | Builds everything. |
| Production (v1–v5) | Skips the eight existing tables, which already have today's shape. The guard covers the two tables v9 changed. Creates the 19 missing tables and moves `user_units` into Team. |
| v13 (dev, test, e2e) | Every `CREATE` skips, and every data statement keeps what is there. Only the `db_version` row 20 is added. |

The test database here and the dev database `vel_yantra_master` both got v20 recorded this way, with no reset.

**Health and deploy.**
- `/api/health` returns `schema_ready: ensure_schema(DB_CONFIG) is None`.
- `deploy.wait_for_schema(url, opener, clock, sleep)` loops: one GET; true only for a 200 whose JSON has `schema_ready` true; otherwise it sleeps 10 s, until the deadline.
- `OSError` covers `URLError`, `HTTPError` and connection resets. `ValueError` covers a body that is not JSON. All of these count as "not yet".
- `stamp_command(version)` builds the stamp command. `stamp()` runs it, and the rollback lines print it, so the two never differ.

**Error handlers.**
- `api_common.register_error_handlers` adds `OperationalError`, `HTTPException` and `Exception` handlers next to the existing three.
- Flask picks the handler by the most specific class, so `ApiError`, `IntegrityError`, `RequestEntityTooLarge` and `app.py`'s `DBUnavailable` handler keep theirs.
- The connection-lost codes moved from `worker.py` to `local_db.is_connection_lost`. The worker and the API both use it.

**Units.**
- `_unit_is_referenced` adds `SELECT COUNT(*) FROM tickets WHERE unit_id = %s LOCK IN SHARE MODE`.
- `update_unit` counts the unit's tickets not closed, also as a locking read under the unit's lock, before the equipment guard runs.
- The message comes from `tickets_core.close_tickets_first(n)`. The scrap refusal uses the same function.

**Send-back and repeats.**
- `tickets_core.allowed_moves(state, keys, has_repeat=False)` drops `send-back` when `send_back_error(has_repeat)` returns a refusal. Both functions are pure.
- In `tickets.py`, `_latest_repeat_serial` reads the latest repeat without the visibility filter. `_moves` uses it, and `_send_back` uses it under the ticket's `FOR UPDATE` lock.
- After its own inserts, the raise calls `_recheck_repeat`: `SELECT state, not_a_fault … LOCK IN SHARE MODE`, then the `latest_restoration` rule again. A send-back committed meanwhile is seen, and the whole raise rolls back (400 on `repeat_of_id`).

**Component edit.** `_check_component` locks only the component row (shared) and reads the parent with a plain query, to find the grandparent.

**Why the scrap race is closed.**
- When the edited component itself is scrapped, the scrap locks that row first (lock (1)). Its snapshot is taken after that, so it counts the edit's ticket.
- The edit, for its part, waits on the scrap's row lock and then sees "scrapped".
- A scrap higher up the tree needs the component scrapped already ("Scrap or move its parts first"). A machine scrap counts the ticket through `equipment_id`.

**RegradeDialog.** In "stopped" mode, the fields shown are only `occurred_at` and `remark`, so an `intensity` error goes to the top message. The `reload` watch fires for 400 or 409 when the error's field is not shown. Client-side errors have no status, so they never trigger it.

## 3. Files touched

**Backend**
- `backend/local_db.py`: the v20 squash, `_PRECONDITIONS` with `_v20_shape_check`, `MigrationBlocked`, `is_connection_lost`, the preconditions run in `init_db`, the docstring.
- `backend/worker.py`: uses `local_db.is_connection_lost`; its two code constants are removed.
- `backend/app.py`: `/api/health` adds `schema_ready`.
- `backend/api_common.py`: the `HTTPException`, `OperationalError` and `Exception` handlers, and the text table.
- `backend/masters.py`: tickets freeze a unit; the deactivation guard for open tickets, placed first; the docstring.
- `backend/equipment.py`: the scrap refusal with the count; the lock-order note.
- `backend/tickets.py`: the send-back refusal, `_latest_repeat_serial`, `_recheck_repeat`, the locked component read, the lock-order notes.
- `backend/tickets_core.py`: not-a-fault from in progress, `allowed_moves(…, has_repeat)`, `send_back_error`, `close_tickets_first`.
- `backend/pyproject.toml`, `backend/uv.lock`: Pillow 13.0.0 (A1).

**Backend tests**
- `backend/tests/fixtures/__init__.py`, `backend/tests/fixtures/migrations_v13.py` (new): v1–v13, frozen, from ae3841f. v1–v5 are checked equal to v0.1.3's.
- `backend/tests/test_migration_v20.py` (new): equivalence, production path, one old table named alone, dev path with re-run.
- `backend/tests/test_health.py`, `backend/tests/test_errors.py` (new).
- `backend/tests/conftest.py`: `SERVER_ERROR` and `server_error()`.
- `backend/tests/test_tickets_api.py`, `test_equipment_api.py`, `test_documents_api.py`: the five rollback tests assert the JSON 500; the scrap message has the count.
- `backend/tests/test_masters_api.py`: unit frozen by a closed ticket; a machine with an open ticket moves; deactivation refused with the count; the ticket refusal comes first.
- `backend/tests/test_ticket_work_api.py`: no send-back after a repeat, also for a user who cannot see it; the raise race; a scrapped component; the edit race; not-a-fault from in progress.
- `backend/tests/test_tickets_core.py`: `allowed_moves` with `has_repeat`; the MOVES table.
- `backend/tests/test_migration_v8.py` … `test_migration_v13.py`: see § 6.

**Frontend**
- `frontend/src/views/tickets/RegradeDialog.vue`: the refusal shows in "stopped" mode; reload on a 400 or 409 that no visible field shows.
- `frontend/e2e/support/tickets.js`: `regradeByApi` and `causeId`; `moveByApi` docstring fixed; a shared `postAs`.
- `frontend/e2e/tickets-work.spec.js`: three S025 tests.
- `frontend/e2e/masters.spec.js`: the S025 unit test; the "v20 (S016's seed)" comment.

**Tooling**
- `tooling/deploy.py`: the health poll, `DEPLOY_HEALTH_URL`, the version read before the stamp, the rollback lines, `stamp_command`, `deploy_command`.
- `tooling/tests/conftest.py`, `tooling/tests/test_deploy.py` (new): 20 tests.
- `tooling/run-tooling-tests.bat` (new); `tooling/run-tests.bat` calls it.
- `tooling/build/build.bat`: the clean-tree, tag and registry checks; checked pushes; no `scratch\` wipe; login before the registry check.
- `tooling/dev/init-test-db.sql`: `vel_yantra_upgrade`.
- `tooling/run-backend-tests.bat`: creates `vel_yantra_upgrade` and its grant on an existing container (dev root password, as `run-e2e-tests.bat`); `setlocal`.
- `.idea/runConfigurations/Release__patch_.xml`, `Release__minor_.xml`, `Release__major_.xml`: `DEPLOY_HEALTH_URL=https://vel-yantra.mspv.app/api/health`. `Deploy.xml` already had it from the user. **These files are not tracked by git** (`.gitignore`: `.idea/`), so the commit will not carry them.

**Generated**
- `sbom/backend.cdx.json`: regenerated by the deps audit; Pillow 12.3.0 → 13.0.0.

**Docs**
- `.claude/CLAUDE.md`: the deploy bullet (health poll, rollback, `build.bat` refusals); a new *Migrations (S025)* bullet; a *Migrations* point under `## SMTW-Review` (BS1-01).
- `docs/Plan.MD`: § 4.1 units frozen by tickets and the deactivation rule; § 4.2 not a fault after Start, no send-back after a repeat; § 5 the `user_units` row. The § 1 schema row was already there.
- `docs/steps/README.md`: four Queued rows; the S025 index row.
- `docs/steps/device-checks.md`: row 9.
- `docs/steps/S025-audit-fixes/1-brief.md`: Status only.

**Not mine.** The working tree also shows status edits in the briefs and reports of S010–S018, S022 and S024 (e.g. "Done (committed …)"), and changes in `docs/steps/README.md` index rows other than S025. Someone else made them while I worked. I left them as they are.

## 4. Decisions taken

1. **Readable comments in v20.** The comments of the old migrations are kept, merged per section. The two `created_by` tags `'migration-v8'` and `'migration-v11'` are kept verbatim.
2. **FK indexes are not declared.** v20 leaves out the indexes MariaDB creates for foreign keys (`fk_*`), as the old migrations did. MariaDB names them after the constraint, so they come out the same. The equivalence test checks this, and a mutation run (moving `notes`) showed that the test catches a difference.
3. **The guard message has two forms.** One old table: "Drop the old equipment table first (it must be empty) — S025 § 5.1". Both: "Drop the old equipment and equipment_events tables first (they must be empty) — S025 § 5.1".
4. **The send-back message names the latest repeat's serial,** even to a user who cannot see that ticket (the brief's wording). The serial reveals only that a ticket exists on the same machine.
5. **`close_tickets_first(n)` lives in `tickets_core`,** next to `CLOSED`. Masters and equipment both import it, so the wording is defined once.
6. **`SERVER_ERROR` and `server_error()` live in `tests/conftest.py`.** The five rollback tests compare `(status, body)` with them, so the body text is not repeated five times.
7. **The race tests write from a second connection with `FOREIGN_KEY_CHECKS = 0`.** The raise test writes the send-back's state change this way. With FK checks on, the change to `state` (a column of `fk_tickets_equipment`'s index) makes InnoDB check the FK. That check waits for the machine row the raise holds, and the test hangs (1205). The test covers only the order where the send-back commits first; if the two overlap, a real send-back waits for the machine's shared foreign-key lock while the raise waits for the ticket, and they deadlock (1213, accepted, retry works; CR1-02). Both race tests fail when their fix is removed; I checked each by hand.
8. **The `build.bat` order changed.** The registry login now runs before the build, because `docker manifest inspect` needs it. Both version tags (backend and frontend) are checked. If either is present, nothing is built. *Consequence:* if a push failed half way, the backend tag may be in the registry without the frontend's. A rerun then refuses, and the user must delete that tag or bump the version. I chose "refuse" over "skip the existing one", because the brief says never overwrite a tag.
9. **Departure from the brief: the e2e unit test expects the real count.** The brief says the test sees "Close its tickets first (1 open)". But `tickets-raise.spec.js` leaves open tickets on `E2E MCC1 mill` in each project, and all three projects share one database. The test therefore reads the unit's open-ticket count through the API first and expects that number. It still closes its own ticket at the end.
10. **A failed stamp prints no rollback lines.** The brief asks for them on any failure after the stamp. A failed stamp still returns 1 without them, as before: the stamp command checks its own result, and a failure there most likely changed nothing.
11. **Pillow 13: no code change.** I read the 13.0.0 release notes. None of the APIs Yantra uses is removed or changed (`Image.open(formats=…)`, `DecompressionBombError`, `Image.new`, `paste` with a mask, `getchannel`, `thumbnail`, `ImageOps.exif_transpose`, `convert`, JPEG `save(quality=…)`). One change applies: `thumbnail()` now uses its `reducing_gap` on RGBA and LA images too. Thumbnails of transparent PNG or WebP photos may differ slightly in quality, with no change in size or behaviour. Labels do not use Pillow (`qrcode`'s SVG image). Python 3.10 support was dropped; Yantra runs 3.12.
12. **`run-tooling-tests.bat` follows `run-deps-tests.bat`,** with `--with python-dotenv` added because `deploy.py` imports it. `tooling/tests/conftest.py` puts `tooling/` on the path.

## 5. Not done, deferred, assumed

- **Production is the user's.** Nothing here touched production, the devops repo or the synced files (`CLAUDE-COMMON.md`, `SMTW-WebApp-Base.md`, `.claude/skills/smtw-review`).
- **Not tested on a real registry.** `build.bat` was not run, because it builds and pushes. Its git checks were run from a copy in my scratch folder: the dirty-tree refusal, "HEAD is not v0.1.3", and "there is no tag v9.9.9". Its registry loop was run against Docker Hub: `hello-world:latest` was refused, and absent images passed. The positive path (clean tree at the tag) runs at the next release. **Assumption** (brief § 9.5): `docker manifest inspect` works with the credentials `build.bat` logs in with.
- **The health URL was not polled.** `deploy.py` was tested with fakes only. `DEPLOY_HEALTH_URL` itself is first polled at the release.
- **Two stale dependencies** are reported, not gating and not new: `bootstrap` 5.3.8 (421 days since a release) and `qrcode` 8.2 (538 days).
- **A data move on v13 databases.** v20's `user_units` → Team statement also runs there. It is a no-op only while `user_units` has no rows that IT admin removed from `person_units` since. The dev and test databases have 0 `user_units` rows (checked), so nothing changed.

### § 5.1 hand-over: the first release after the squash (for the user)

1. Optional: trigger db-server's dump once just before, so the newest dump in `ERP-DB-Backup` is from today.
2. **Done by the user on 21-10-2026.** Check that the two tables are empty:
   ```sql
   SELECT COUNT(*) FROM equipment; SELECT COUNT(*) FROM equipment_events;
   ```
3. **Done by the user on 21-10-2026.** Drop them, events first (they reference equipment):
   ```sql
   DROP TABLE equipment_events; DROP TABLE equipment;
   ```
4. Run the Release. v20 builds the rest, and the deploy waits for `schema_ready`.

If step 3 had been missed, v20's guard would refuse and change nothing. The new image would answer 503 on every database route until the tables were dropped, and the next retry (within 30 s) would build the schema.

### Migration warning for smtw-common (U2): text to paste

Paste this into smtw-common's `SMTW-WebApp-Base.md`, § Local DB Migration Pattern. CLAUDE-COMMON keeps its one-line invariant.

> **Careful with migrations that touch existing rows.** A migration that only creates new
> tables is safe anywhere. One that changes a table which holds data in production can fail
> half way or corrupt data. MariaDB DDL is not transactional, so a failed migration is half
> applied and fails again on every retry. Before writing one, check:
> - **a `NOT NULL` column or a foreign key added to a table with rows**: existing rows get
>   0 or `''`, and the foreign key then fails (1452). Add the column `NULL`, fill it, then
>   tighten it in a later migration, or refuse until the rows are gone;
> - **a dropped or renamed column** that the previous image still reads: a rollback to that
>   image then fails. Drop it one release later;
> - **data that cannot be converted** (an ENUM value removed, a narrower type, a new UNIQUE
>   key over duplicates): find the offending rows first.
>
> **Guard it, do not hope.** Give such a migration a precondition: a function run before any
> pending migration is applied, which reads the real state (`information_schema` with
> `TABLE_SCHEMA = DATABASE()`, a `COUNT(*)`). It returns why the migration cannot run yet,
> and then nothing is applied: the schema stays as it was, so the previous image runs again
> after a redeploy. The engine keeps the message for the database status screen and retries
> as usual (Yantra: `local_db._PRECONDITIONS`, S025).
>
> **Test it from the production schema.** Build a test database with the migrations
> production has actually applied (a frozen copy of their text), fill it with production-like
> rows, and run the new migration on it: once refused, once after the fix-up, checking that
> the rows are intact.
>
> **Back up before the deploy, and verify after it.** Take a dump just before a release that
> touches existing rows. Make the deploy wait for the health endpoint's `schema_ready` and
> fail with the rollback steps if it does not come. After a migration has applied, the old
> image may not run on the new schema: the rollback is then a restore of the dump.

## 6. Tests

**Results** (real runs, 21-10-2026):

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` (exit 0) | backend 1855 passed; frontend 12 files, 93 tests passed; deps 42 passed; tooling 20 passed |
| `npx vite build` | built, no new warnings |
| `tooling/run-deps-audit.bat` | exit 0: 3 SBOMs, 181 libraries, 0 vulnerabilities, 2 stale direct dependencies (not gating) |
| `tooling/run-e2e-tests.bat` | 147 passed in 5.2 min (49 tests × 3 projects: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium); 0 failed, 0 skipped |

**Fate of the old migration tests** (BR2-07):

| File | Kept (today's schema) | Retargeted to v20 | Dropped (pure re-runs; `test_migration_v20` covers them) |
|---|---|---|---|
| `test_migration_v8.py` | — | the `user_units` move and re-run | — |
| `test_migration_v9.py` | the shape assertions (now `test_the_shape_holds`); NULL model refused; owner CHECK | — | the v9 re-run |
| `test_migration_v10.py` | tables and the default | stored value kept; missing setting written | — |
| `test_migration_v11.py` | tables and unique keys; seed rows | an edited seed row kept | — |
| `test_migration_v12.py` | tables and indexes; owner CHECK name; single owner accepted; none or two refused | — | v12 re-run and v9-after-v12 |
| `test_migration_v13.py` | columns and constraints; assignees; labour; minutes range | — | v13 re-run |

`test_modules.py`'s `LATEST_VERSION` assertions hold unchanged.

## Fix rounds

### Round 1

- **CR1-01 — Fixed.** `tooling/deploy.py` `_schema_ready_once` also catches `http.client.HTTPException` ("not yet"), so a cut answer keeps the poll going until the timeout and then the rollback lines print. `tooling/tests/test_deploy.py`: two more cases in `test_anything_else_is_not_yet` (`RemoteDisconnected`, `IncompleteRead`). The safety-net `try/except` around `main()` that the finding also mentions was not added (the user asked for the catch only).
- **CR1-02 — Fixed (wording only).** `backend/tickets.py` note: already updated by S019 (state change takes the FK shared locks; four accepted deadlocks); nothing missing. `backend/equipment.py` note: "nothing else locked" replaced by the FK shared locks and the two new accepted deadlocks (repeat raise against send-back; unit edit against a ticket move). Brief § 5.2 "Order" corrected, with the answer recorded in the brief's Review log. Decision 7 in § 4 and the comment in `test_a_send_back_committed_during_the_raise_refuses_the_repeat` now say the test covers only the order where the send-back commits first.
- **Files:** `tooling/deploy.py`, `tooling/tests/test_deploy.py`, `backend/equipment.py`, `backend/tests/test_ticket_work_api.py` (comment), `docs/steps/S025-audit-fixes/1-brief.md`, this report.
- Tests after the round: `tooling/run-tests.bat` exit 0 (backend 2003 passed, frontend 13 files / 110 tests, deps 42, tooling 22); `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js`: 66 passed (22 tests x 3 projects), 0 failed.
- Not touched: CR1-03 to CR1-05 (nits; not asked).

## Manual checks

From the brief's § 8.

**Automated** (browser suite):
- [auto] *Machine stopped* refused shows its message — `frontend/e2e/tickets-work.spec.js`::`S025: Machine stopped, when someone else made it a breakdown first, shows why and reloads the ticket`
- [auto] No *Send back* on a ticket with a repeat — `frontend/e2e/tickets-work.spec.js`::`S025: a ticket that came back as a repeat offers no Send back; Close stays`
- [auto] The unit deactivation refusal shows — `frontend/e2e/masters.spec.js`::`S025: IT admin cannot deactivate a unit while it has open tickets; the refusal gives the count`
- [auto] *Start* → *Not a fault* (U4) — `frontend/e2e/tickets-work.spec.js`::`S025: Start, then Not a fault: the ticket closes as not a fault and shows no times`
- [auto] Every screen still opens on a database built by v20 — `frontend/e2e/screens.spec.js` (all tests; the e2e database is rebuilt from empty by v20 at every run)

**On a real device** (also row 9 of `docs/steps/device-checks.md`):
- [x] — by KLA, 23-10-2026 (release v0.1.7: deploy passed with the schema ready; Settings › Database shows v25; masters and Team intact). **Important.** The first release after the squash, run by KLA (admin, plant network, production). § 5.1 steps 2–3 were done by the user on 21-10-2026. Then: the release; the deploy waits for `schema_ready` and passes; Settings › Database shows the latest schema version (the release applies v20 with S019's v21 and S020's v22, S019 BS1-06); the masters are there (sites, units, classes, types); the people who had unit access are in Team with their units. If it is refused or fails: § 5.4, i.e. the rollback lines `deploy.py` prints.
