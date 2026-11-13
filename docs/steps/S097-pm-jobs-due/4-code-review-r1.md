```
Step: S097 — PM jobs come due
Doc: code-review r1
Author: Code reviewer (Opus 5.5)
Date: 02-11-2026
```

# S097 — code review, round 1 (the backend round)

**Verdict: no `blocker` or `major` finding is open.** This round covers the backend only: snapshot round 1
(`refs/step-rounds/S097-1`), against `refs/steps/S096`. The screens (round 2) are not judged here; their
review is round 2. Findings: 0 blocker, 0 major, 1 minor, 3 nits.

**Scope of the read.** `git diff refs/steps/S096 refs/step-rounds/S097-1 -- backend docs .claude`, and these
files in full from the snapshot: `backend/pm_jobs.py`, `backend/pm_jobs_core.py`, the create, change and card
paths of `backend/pm_plans.py`, the v52 migration, `backend/tests/test_pm_generate.py`,
`backend/tests/test_pm_jobs_api.py`, and the test names of `test_migration_v52.py`. The working tree's backend
was checked against the snapshot before the test run: no backend file differs.

**Tests (my run).** `YANTRA_TEST_RUN=s097cr1 tooling\run-backend-tests.bat tests/test_pm_jobs_core.py
tests/test_pm_generate.py tests/test_pm_jobs_api.py tests/test_migration_v52.py tests/test_pm_plans_api.py`:
**PASSED, 199 passed in 18 s** (log `scratch/backend-tests-s097cr1.log`). The whole backend suite (4954
passed) and the tooling suite (239 passed) are the coder's runs; as asked, I did not repeat them. No browser
run and no schema docs check: no finding needs one, and the coder's `check` exited 0.

## Findings

### CR1-01 (minor) — a meter window with a fourth decimal is rewritten on every run

- **Where:** `backend/pm_jobs_core.py:101-108` (`due_copies`) and `:118-122` (`job_changes`); the window
  comes from `backend/pm_schedule_core.py:201` (`meter_window = meter_every / WINDOW_DIVISOR`).
- **Problem:** `meter_every` is `DECIMAL(14,3)`, and a meter type may have up to 3 decimals
  (`chk_meter_types_decimals`). So 10 % of it can have 4 decimals: 250.005 gives 25.0005. `pm_jobs.meter_window`
  is `DECIMAL(14,3)`, and MariaDB rounds the value on insert with only a note (checked on the dev container,
  a `TEMPORARY` table, nothing kept: `INSERT 25.0005` gives Note 1265 and stores 25.001). `job_changes` then
  compares the stored 25.001 with the new 25.0005, finds a change, and `update_row` writes it again.
- **Failure scenario:** a plan on a meter with 3 decimals, every 250.005, has an open job. Every daily run
  and every save of that plan rewrites `meter_window` with the same rounded value. Each time it stamps
  `updated_at` and `updated_by = pm_generate`, and the run's log counts the job as refreshed. The job's record
  then says the daily run changed it every morning, when nothing changed (ISO 9001 § 7.5.3: the record must
  show real changes). The save also judges the standing with 25.0005 while the list judges it with 25.001.
  The effect is small, and the case is rare (most meters have 0 or 1 decimal).
- **Fix:** round the copies to the column's scale before they are compared and stored. For example, in
  `due_copies`, quantize `meter_window` (and, for safety, `due_meter` and `meter_offset`) to
  `Decimal("0.001")`. Add a core test: a `Due` with `meter_window` 25.0005 copies as 25.001, and
  `job_changes` of a job that stores 25.001 is `{}`.

## Nits

- **CR1-02** (nit) `backend/pm_jobs.py:229-231`: `settle_plan_job` answers `REFRESH` also when `job_changes`
  is empty and nothing is written, so "N refreshed" in the run's log counts every open job every day. Answer
  `None` when there are no changes, so the log counts real writes (§ 5.5: "the action taken").
- **CR1-03** (nit) `backend/pm_jobs.py:238-243`: `_lost` repeats `worker.Worker._connection_lost`
  (`backend/worker.py:148-153`) with a small difference (it also requires `OperationalError`). Move one
  function, such as `connection_lost(conn, exc)`, into `local_db.py` beside `is_connection_lost`, and call it
  from both.
- **CR1-04** (nit) `backend/pm_jobs.py:301-303`: the `meter_type` dict from the `t_` columns repeats
  `pm_plans._meter_type` (`backend/pm_plans.py`, the same five keys). Keep one copy in `pm_jobs` and let
  `pm_plans` use it, as this round already did for `LOCK_PLAN` and `SHARE_NODE`.

## Checked and found consistent

- **v52** matches § 4.1 column for column: the two tables, `uq_pm_jobs_serial`, `uq_pm_jobs_open_plan` on the
  `PERSISTENT` generated `open_plan_id`, the three indexes, the five foreign keys and both CHECKs. Two new
  tables only, `CREATE TABLE IF NOT EXISTS`, so no `_PRECONDITIONS` entry is due. The migration tests cover
  § 8.1: the ENUMs against the core's constants, the generation expression's values as a tuple (BR1-07), the
  1062 cases, the CHECK refusals and passes, the v51 upgrade and the re-run.
- **One open job per plan under concurrency.** Every job write runs under its plan's row: the run's
  `_settle_one` takes `LOCK_PLAN` as the first statement after `BEGIN`; the change route does the same; the
  create route holds its new plan row. No plain read comes before the plan lock in either path, so the
  snapshot starts after the lock, and the second writer reads the first writer's committed job. Neither path
  reads a job `FOR UPDATE` by `open_plan_id`. The unique key is the backstop.
- **Lock sequences against the LOCK ORDER notes.** The run is (6e) → (1) shared → plain reads → (6) for a
  create only → the job and event writes → commit. The save is (6e) → (1) shared (change) or (1) shared → the
  plan insert (create), then the same tail. The (6)-after-(6e)-and-(1) departure is written in
  `pm_jobs.py`'s note and `equipment.py`'s (6e) bullet, with the reason, as BR1-04 asked. I also checked the
  gap locks: the unique check on `uq_pm_jobs_open_plan` at a create, a cancel's NULL entry, and the
  `serial_counters` insert-or-update beside the `TK:`, `IM:` and `OPL` rows. Every wait found goes one way,
  because a transaction that holds a counter waits only on shared foreign-key locks after it. So I found no
  cycle.
- **The per-plan commit and `RetryLater`.** `generate` reads the candidates, commits (BR1-01), then runs one
  `transaction(conn)` per plan. A failed plan is rolled back alone and logged with `logger.exception`, and the
  handler raises `RuntimeError` naming the plans: no exception is swallowed silently. A lost connection is
  re-raised at once. A stop raises `RetryLater(…, 60)` from the handler, because `task_handlers` owns
  `RetryLater` and `pm_jobs` may not import it. This is a reported decision and is right. The docstring names
  the third commit exception.
- **S095's core.** `next_due(plan_input, last_job, start_meter)` gets `created_on` from `created_at`, and the
  base table of § 5.3 is followed row by row in `_meter_base`. `start_meter` is given only for a base taken from
  a reading (S095 D9). N1: the copies are rewritten only when they differ. The reset rule (D8) is applied:
  `meter_offset` adds the value before each reset, `readings_across_reset` returns rows only when a reset
  follows the base (one query with `EXISTS`), and the list adds the stored offset to the latest reading.
- **`decide`** follows § 5.5's table, including the inactive plan on a scrapped node (the plan's remark) and
  the `before_use` plan with a `due` job. The schedule is computed only when a job may be made or refreshed.
- **Serials.** `next_counter(serial_scope(now.year, now.month, "PM"))` inside the plan's transaction: a
  rollback takes the number back. The tests fix `pm_jobs._now` to a month of its own (BR1-02).
- **`pm_job:read`.** It is granted to the operator and IT admin, so the supervisor and the maintenance ladder
  hold it too, and it is in `SITE_SCOPED`. The list gates on `require_perm` and filters by
  `accessible_unit_ids(cur, "pm_job:read")` over `NODE_JOINS`' root unit (D9). The card's `schedule` uses
  `has_perm_at` at the node's site, and the storekeeper gets null. The assignee is answered as `{id, name}`
  only. No actor comes from the client, and the SQL has no client strings (the `IN` lists come from code
  constants and `marks`).
- **The S096 save hook.** `settle_plan_job` is called last in both transactions, after the item writes and
  before `_detail`. A refused save raises before it. The answers are unchanged.
- **The shared lock statements** moved to `pm_jobs` with the same text, and `pm_plans` uses them through
  aliases. This is reported, and no behaviour changes.
- **The coder's small choices** (§ 4 of the impl report): `generate` returns its counts and the handler
  raises; `pm_plans` calls `pm_jobs._now`, as the brief names it; inactive card items carry `schedule: null`;
  a `before_use` plan gets an empty schedule; `decide` raises `TypeError` for a flag that is not a bool. All
  are in the brief's spirit and reported.
- **Database down:** `GET /api/pm/jobs` goes through `get_db()` and is tested with `db_down` (503).
- **`meters.py`:** the rename to `last_readings` covers all three callers. The two new reads use `_ACTIVE`
  (removed readings left out) and order by `(taken_at, id)`.
- **Docs pass:** the `## Docs updated` list matches the diff. `notes.json` moves `pm_jobs` and `pm_job_events`
  into the area and names the generated column. `schema.json` shows `open_plan_id` as a `UK`
  `stored generated` column (A4). `Plan.MD` gains § 3, § 4.3 *Built (S097)* and § 6. `.claude/CLAUDE.md`
  gains Self-check (2) and the SMTW-Review point of § 8.6. No secret, role or claim changes, so
  `docs/Keycloak.md` and `example_secrets_app.py` are rightly unchanged. The Plan.MD screen lines describe
  round 2's screens; round 2 builds them.
- **Tests against § 8.2 and § 8.3:** the run's cases (create, idempotent, meter, `both` with D9, the reset,
  cancel ×2, a started job left, the assignee who left, the failing plan, the stop, a payload, through the
  worker, the serials), the list's cases (scope by site, IT admin, the filters, *Assigned to me* without a
  Team record, the tabs and `counts`, the live standing after a logged reading, the offset), the save's cases
  and the card's cases are there. They also cover the failure modes, not only the happy path. The core tests
  were shown red first (`ImportError`). `test_role_matrix`, `test_pm_job_keys`, `_TABLES` and the schedule
  test are updated as briefed.
- **Track:** full, as it must be (a migration, RBAC, locking).

## Manual checks

None for the backend round. The brief's **important** checks are browser checks of the screens (§ 8.4); the
impl report's `## Manual checks` section, with each as `[auto]` and its test, is due in round 2 and is checked
there. The brief has no real-device check (§ 8.5).

## Feedback

- hindrance: the background test run's output file sat under the orchestrator's session folder, not this
  agent's scratchpad, so its path had to be copied from the notification (1 read).
- idea: `git diff --stat refs/step-rounds/S097-1 -- backend` lists every new untracked file as deleted, so the
  check that the working tree still equals the snapshot needs a second command (`git status --short`); a
  `step_snapshot.py` option such as `diff S097 --tree-vs-round 1` would answer it in one.
