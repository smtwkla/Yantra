```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: three `major` findings open** (BR1-01 the health route must trigger
the schema retry itself; BR1-02 decision 2 rests on a wrong claim and the
recovery path after a refused migration is missing; BR1-03 the upgrade test has
no database to build the v5 schema in). No blocker. The audit's findings are
read correctly and the fixes are the right size; the findings below are about
making the release path actually work on the day.

## Findings

### BR1-01 (major) — `/api/health` must call `ensure_schema`, not read a flag

**Problem.** § 3 plans "a public `schema_ready()` for the health route".
`local_db._schema_ready` is **per process**: gunicorn runs 3 sync workers with
no `preload_app` (`tooling/build/gunicorn.conf.py`), so each worker has its own
flag, set only by its own `ensure_schema` call. Today the retry every 30 s
happens only when something calls `ensure_schema`: `get_db()` (a DB route),
`db_status` (Settings › Database) or the worker process (its own flag). A
request to `/api/health` is public and touches none of these. So after a deploy
where the database was not reachable at boot (the same playbook recreates the
DB container, or MariaDB takes longer than the backend to come up), every
worker's first attempt fails and **nothing retries until a user hits a DB
route**. The deploy poll would read `schema_ready: false` for 3 minutes and
fail the release although nothing is wrong. The reverse also holds: the worker
that answers the poll may be the one that never tried.

**Fix (recommended).** The route calls `ensure_schema(DB_CONFIG)` itself and
reports `schema_ready: error is None`. It is cheap: a flag read once ready, and
rate-limited to one attempt per 30 s per process otherwise, so a public caller
cannot make it hammer the database. Drop the `schema_ready()` getter. The poll
then self-heals: each hit lets the answering worker retry. *Alternative:* keep
the getter and make the poll also hit a DB route — needs a token; no.

Note for § 8: the "false" test then monkeypatches `ensure_schema` (or
`init_db`) to return an error, rather than poking the flag.

### BR1-02 (major) — Decision 2's premise is wrong, and there is no recovery path after a refusal

**Problem.** § 7 decision 2 says refusing everything "keeps the old image
working against the old schema until the data is fixed". It does not: by the
time the engine refuses, the playbook has already recreated the containers with
the **new** image, whose `get_db()` raises `DBUnavailable` while
`ensure_schema` returns the block — **every DB route answers 503** until the
data is fixed or the old version is put back. What "refuse all" really buys is
that the schema is untouched, so the v0.1.3 image *can* be put back without a
database restore (the audit's [1] rollback problem). The user approves the
decision on that premise, so the text must say what happens on the floor: a
refused release is a plant-wide outage of Yantra until the rollback.

The brief also gives no rollback step. `deploy.py` deploys only the `VERSION`
file's version; on a refusal the user is left with a 503 production and a
message pointing at § 5.1, which says "the release waits".

**Fix (recommended).** (a) Rewrite decision 2 and § 5.1: the refusal keeps the
schema at v5 so the previous image runs again unchanged; the new image serves
503 until then. (b) The deploy failure message names the rollback: on
ansible-ws, stamp the previous `YANTRA_VER` and run
`./erp_spanner.py deploy vel yantra master` — the user's action per CLAUDE-COMMON
(production changes are the user's), so the message gives the two ready-to-paste
lines and the impl report repeats them. (c) The **important** device check in
§ 8 gets the branch: "refused → roll back → Yantra answers again → the
follow-up step". (d) Say in § 1.1 that Q3 (read production's equipment count
before the release) is the real gate and the precondition is the safety net.
*Alternative:* `deploy.py --version 0.1.3` to redeploy a given version from the
laptop — more code for a path the user runs by hand once; only if the user
wants it.

### BR1-03 (major) — The upgrade test has no database to build the v5 schema in

**Problem.** § 3 Tests: the new `test_migration_upgrade.py` "builds the v1–v5
schema from a frozen copy of v0.1.3's five migrations". It cannot do that in
`vel_yantra_test`: that database is at v13 and shared by the whole session
(`conftest._clean_tables` empties it once, every other test runs against it);
dropping its tables mid-session breaks whatever runs after. And the test user
cannot make its own database: `tooling/dev/init-test-db.sql` grants
`vel_yantra_master` privileges on `vel_yantra_test.*` and `vel_yantra_e2e.*`
only, not `CREATE DATABASE`. The coder would have to invent the dev-tooling
change alone.

**Fix (recommended).** A third test database, `vel_yantra_upgrade`, on the
pattern S024 just set for `vel_yantra_e2e`: a `CREATE DATABASE` + `GRANT` pair
in `init-test-db.sql` (fresh volumes), and `run-backend-tests.bat` creating it
on an existing container the way `run-e2e-tests.bat` does (so nobody needs a
`dev-db-reset`). The test drops every table there at its start, applies the
frozen v1–v5, inserts the v0.1.3-shaped rows (a site, unit, class and one
equipment row with `make`/`model` text), then runs today's `init_db` with a
config whose `database` is `vel_yantra_upgrade` (`init_db(config)` already
takes the config). Asserts: with the row, `db_version` max is 5, no
`manufacturers` table, `make` still present; empty, `LATEST_VERSION` reached.
Add the two tooling files to § 3 Where. *Alternative:* skip the test when the
database is absent — no: the test exists to be run before the release.

The frozen copy is sound: `git show v0.1.3:backend/local_db.py` has exactly
v1–v5, 421 lines shorter than today's file, and v5's statements are already
re-run-safe.

### BR1-04 (minor) — A handler for `Exception` changes how Flask treats errors; five existing tests break

**Problem.** Once `register_error_handlers` registers a handler for `Exception`:

- Flask's test client no longer propagates route exceptions (`TESTING`'s
  `PROPAGATE_EXCEPTIONS` applies to *unhandled* ones). Five tests use
  `pytest.raises(RuntimeError)` through the client to prove a rollback:
  `test_tickets_api.py:94` (the serial counter), `test_equipment_api.py:101,
  502`, `test_documents_api.py:288, 466`. They will fail; they should assert
  the 500 JSON body instead — the side effect they test still holds.
- Flask does **not** log an exception that a registered handler answers; the
  brief says the traceback is logged, so the handler must do it
  (`logger.exception`). Say it belongs to the handler.
- `_integrity_error` re-raises a non-duplicate `IntegrityError` from inside a
  handler; Flask then takes `handle_exception` → `InternalServerError` → the
  `HTTPException` handler. So the `HTTPException` handler must also produce the
  plain 500 text ("Something went wrong — try again"), not Werkzeug's
  description; and 404/405 their plain lines. One small table of code → text.
- Handler choice is by MRO (most specific class wins), so `ApiError`,
  `IntegrityError`, `OperationalError` and `RequestEntityTooLarge` keep theirs
  under the generic one — worth one line so the coder does not reorder them.
- An `OperationalError` that is *not* a lost connection (1213 deadlock, 1205
  lock wait) falls to the generic 500 — say so, it is the accepted-deadlock
  path of S017 § 5.4.

**Fix.** Add these five points to § 5 or § 3, and the five test edits to § 3
Tests.

### BR1-05 (minor) — The lost-connection codes already exist in `worker.py`; reuse them

**Problem.** § 1.3 lists "2006, 2013 and the 2xxx client errors" (2006 and 2013
are 2xxx) and misses the two server-side codes the worker already treats as a
lost session: 1053 (server shutdown) and 1927 (connection killed) —
`worker.py:47-49`, `Worker._connection_lost`. Two definitions of "connection
lost" will drift.

**Fix.** Move `CLIENT_ERROR_CODES`, `SERVER_DROPPED_CONNECTION_CODES` and a
pure `is_connection_lost(code)` to `local_db.py`; the worker and the new
handler both use it. Name it in § 3 under `local_db.py` and `worker.py`.

### BR1-06 (minor) — `_check_component`'s locked read also locks the parent: a new deadlock edge

**Problem.** `_check_component` (`tickets.py:833`) reads the component **joined
to its parent** (`LEFT JOIN equipment p`). `LOCK IN SHARE MODE` on that
statement takes S locks on both rows, component first, then its parent. The
scrap path locks the machine `FOR UPDATE`, then its parts
(`equipment.py:371-376`): the opposite order. Edit holds S(component) and waits
for S(machine); scrap holds X(machine) and waits for X(component) → 1213. The
brief's "no new lock-order edge" holds only for the component row, which is the
one the FK takes.

**Fix.** Lock the component row alone (one `SELECT … FROM equipment WHERE id =
%s LOCK IN SHARE MODE`), then read the parent plain for `gp_id`; `status` is
decided from the locked row. Write that in § 1.6 and the lock-order note.

### BR1-07 (minor) — `moves` must use an unfiltered "has a repeat", not the visible `repeats` list

**Problem.** § 3 says the detail's `moves` leaves out `send-back` "while
`repeats` is not empty". `_repeats` (`tickets.py:240`) is **access-filtered**
(`_visible_condition`). A repeat is raised on the same machine with the
machine's unit at that moment; a user whose access covers the earlier ticket's
unit but not the unit the machine moved to afterwards sees the earlier ticket
and not its repeat. He would be offered *Send back* and get the 409.

**Fix.** In `_detail`, `has_repeat = EXISTS (SELECT 1 FROM tickets WHERE
repeat_of_id = %s)` unfiltered, used for `moves` and still the route's check.
`allowed_moves(state, held_keys)` is pure and tested (`test_tickets_core.py`);
name its new signature (`has_repeat=False`) so the coder changes the three
callers and the tests knowingly. The 409 naming a serial the user cannot open
is acceptable (it is the record's truth).

### BR1-08 (minor) — Where the "only while the `equipment` table exists" rule lives

**Problem.** § 3 gives `_PRECONDITIONS = {9: (sql, message)}`; § 5.1 says the
count runs "only while the `equipment` table exists". The tuple cannot express
that. On a fresh database every version is pending, so the up-front check would
run `SELECT COUNT(*) FROM equipment` before v4 created it → error 1146 and a
fresh deploy never comes up.

**Fix.** `{9: ("equipment", "SELECT COUNT(*) AS n FROM equipment", "Migration
v9 needs an empty equipment table: {n} machines exist …")}`: the engine skips a
precondition whose table is absent (`SHOW TABLES LIKE %s`, as
`_get_applied_versions` already does for `db_version`), runs the rest in
version order under the lock, and formats `{n}` into the message. Also say the
preconditions are read after `_get_applied_versions` inside the lock, so a
worker that waited on the lock sees what the first one applied.

### BR1-09 (minor) — `deploy.py`: scope of the gate, the URL's absence, and the run configs

**Problem.** Three things the coder would otherwise decide:
- whether `--check` (read-only) and `--stamp-only` (no deploy) need
  `DEPLOY_BACKUP_CONFIRMED` — they should not;
- whether a missing `DEPLOY_HEALTH_URL` aborts or skips the poll — abort, like
  `DEPLOY_WS_SESSION` (a forgotten variable must not silently skip the one
  check this step adds); what counts as ready (HTTP 200 **and**
  `schema_ready: true`); and that a connection error during the poll is "not
  yet", not a failure;
- the env vars live in committed run configs: `.idea/runConfigurations/Deploy.xml`
  and the three `Release__*.xml` hold `DEPLOY_WS_SESSION` and
  `DEPLOY_ERP_SERVER_DIR`. The two new variables go there too — four files for
  § 3 Where.

### BR1-10 (minor) — `DEPLOY_BACKUP_CONFIRMED` attests that a task exists, not that a backup was taken

**Problem.** A run-config variable is set once and stays set. The gate as
written means "the Ansible backup task exists", which is what § 1.1 says, but
the name reads as a per-release confirmation, and nothing checks the task ran.
ISO 27001 A 8.13 asks for backups *taken*; the pipeline can see it.

**Options.** (a) Keep the flag, rename it to what it means
(`DEPLOY_BACKUP_TASK=<task name>`). (b) **Recommended:** (a) plus `deploy.py`
verifying in the playbook output — which it already parses for the PLAY RECAP —
that `TASK [<name>]` appears with `ok`/`changed` before the containers are
recreated; otherwise it fails with "Deployed without a backup — the task
<name> did not run". Then the first release after the user adds the task proves
the task is wired, every later one proves it ran. Both options keep the devops
repo the user's (decision 3).

### BR1-11 (minor) — Where the `deploy.py` tests live is left open

**Problem.** § 3 hedges: "`tooling/tests/`, run by `run-common-tests.bat` if
that is where tooling tests live, else beside `deploy.py`". Neither exists.
Tooling tests today are `tooling/deps/tests/` with their own `pytest.ini` and
`tooling/run-deps-tests.bat` (`uv run --no-project --with pytest`), listed in
`run-tests.bat`.

**Fix.** Decide: `tooling/tests/test_deploy.py` and a
`tooling/run-tooling-tests.bat` on the deps pattern (`--with python-dotenv`
too: `deploy.py` imports it), added to `run-tests.bat` so the release runs it.
`deploy.py`'s poll takes its opener and clock as parameters (the module-level
env reads stay), which § 3 should say — "against a fake URL opener" implies it.

### BR1-12 (minor) — `build.bat`'s "tag already in the registry" meets `release.py`'s "reusing version" path

**Problem.** `release.py` lines 127-129: with no commit since the last release
it reuses the version and still runs `BUILD_SCRIPT`. With § 1.2's refusal that
release now aborts at the build. Right (nothing to release; a redeploy is the
"Deploy" run config), but the refusal message should say so, and § 1.2 should
record it as intended. Also `docker manifest inspect` exits non-zero both for
"no such manifest" and for a network or login failure; distinguish on its
output, or state that a failed inspect is treated as "absent" and the push's
own check catches the rest.

### BR1-13 (nit) — Standards citations

- **ISO 14224:2016**: "Quality of data" is clause **7** (what makes a failure
  record usable: complete, consistent, traceable); clause 9 is "Equipment,
  failure and maintenance data" — the record itself. Either supports § 2's
  point; cite the one meant. The 2016 numbering should be checked against the
  copy the plant holds.
- **SMRP metrics**: 2.1.1 is availability and 3.5.1 MTBF, as cited; MTTR is
  **3.5.2** — add it, since § 2 names MTTR.
- ISO 55001 § 8.1, ISO 27001 A 8.32 / A 8.13 and ISO 9001 § 10.2 are cited
  correctly; the plain-terms explanations are good.

### BR1-14 (nit) — Test file names

`test_health.py` and `test_app.py` do not exist; the health route is covered
today only as a public path (`test_auth.py:124`, `test_access_control_api.py:77`).
Say "`test_health.py` (new)".

### BR1-15 (nit) — Two message wordings

- Unit deactivation: "Close its open tickets first (N)" beside the scrap's
  existing "Close its tickets first" (`equipment.py:394`). One wording for the
  same rule; the count is useful, so change both or neither.
- The precondition message puts a docs path in a UI line. Fine for IT admin on
  Settings › Database, but lead with the action: "Migration v9 needs an empty
  equipment table: 3 machines exist. The release waits until every machine has
  a model (S025 § 5.1)."

### BR1-16 (nit) — `/api/health` stays HTTP 200 when the schema is blocked

Say it: `status: "ok"` with `schema_ready: false` and 200, so nginx and any
uptime check keep reading the process as alive; the deploy reads the field.

## Checked and found consistent

- Audit [1]–[4], [6], [9], [10] are read correctly; [5] rightly left to the
  user (Q2); the hindsight items rightly out of scope.
- `local_db.py`: `init_db` serialises gunicorn workers and the worker process on
  `GET_LOCK(LOCK_MIGRATIONS, 60)` and releases it in `finally`, so a
  `MigrationBlocked` raised inside the loop releases the lock; `ensure_schema`
  catches `DBUnavailable` subclasses, keeps `describe_error(exc)` as
  `_last_error`, retries every 30 s; `db_status` surfaces it and
  `SettingsView.vue:246` shows `status.error` — the message reaches Settings ›
  Database with no frontend change. The worker calls `ensure_schema` every loop
  (`worker.py:174`) and does no work until it passes.
- `git show v0.1.3:backend/local_db.py` is v1–v5 exactly; the fixture can be
  frozen from it.
- `/api/health` and `/api/version` are public (`auth_utils.PUBLIC_PATHS`) and
  exempt from the network gate; `/api/version` touches no DB, as the audit says.
- `release.py` steps 6–7: a non-zero `DEPLOY_SCRIPT` aborts before
  `git push --follow-tags` — the brief's claim holds. (The release commit and
  tag exist locally and the images are already in the registry at that point;
  the "Deploy" run config is the retry.)
- `build.bat`: the four `docker push` calls are unchecked and `scratch\*` is
  wiped (lines 72-81); `scratch/` now holds the dependency report, the e2e
  report and the e2e backend log.
- `api_common.register_error_handlers` registers only `ApiError`,
  `IntegrityError`, `RequestEntityTooLarge`; `app.py:64` maps `DBUnavailable`
  → 503; `db_helpers.get_db` maps only the checkout `OperationalError`, so a
  connection that dies mid-request is unmapped, as the audit says.
- `masters._unit_is_referenced` counts `person_units` and `equipment` only, and
  its docstring is stale since v12; `update_unit` locks the unit `FOR UPDATE`
  first, so the plain counts after it see every committed raise and the
  `LOCK IN SHARE MODE` count matches `_check_code_frozen`'s pattern.
- `tickets.py`: `_send_back` ignores repeats; `MOVES["send-back"]` is from
  `back_in_service` only; `_check_repeat` reads the earlier ticket plain before
  the insert, so the post-insert locked re-read is needed and sufficient (the
  insert's FK S lock waits behind an in-flight send-back's X lock; a send-back
  that arrives later locks the row, then its first plain read sees the committed
  repeat). No lock cycle: the send-back holds (7) only.
- `_check_component` reads plain; the fix is the FK's own row (BR1-06 aside).
- `RegradeDialog.vue`: in "stopped" mode the intensity fieldset is `v-if`'d out
  and `SHOWN_FIELDS` keeps `intensity` out of `topError`, so a 400 on
  `intensity` shows nothing; `useFormModal` stores `status`, so the reload
  watch can cover it. `TicketDetailView.vue` draws its buttons from
  `ticket.moves` (`significantMoves`), so dropping `send-back` server-side needs
  no page rule.
- Layering: the send-back rule as a pure `tickets_core` function, the route a
  thin check; the precondition data beside `_MIGRATIONS`; no new abstraction
  beyond one dict and one exception subclass. Right-sized.
- UX: the three new refusals are one plain line each, shown beside a field or
  as a 409 that reloads; *Send back* hidden rather than refused; the deploy
  messages say what to do. The device checks carry account, network and where;
  nothing on the device list that a browser could judge.
- Standards named are the relevant ones; the backup design keeps the devops
  repo and production the user's (CLAUDE-COMMON production rules).
- Track: full is right (migration engine, locking rules, deploy script).
