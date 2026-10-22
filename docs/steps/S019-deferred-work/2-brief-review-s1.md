```
Step: S019 — Deferred work
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 22-10-2026
```

Reviewed against: 3df667c + uncommitted S025

# S019 — Staleness review, round s1

**Verdict: no `blocker` or `major` finding is open.** The design and every user
decision still hold. Three `minor` findings and four `nit`s need wording in the
brief before the coder starts.

**What I compared.** The brief's *Where* files and the modules they call,
between `28d3be3` and the working tree now: S024 as committed (`3df667c`), and
S025's uncommitted code (`git diff 28d3be3`, plus the untracked files
`backend/tests/fixtures/`, `test_migration_v20.py`, `test_errors.py`,
`test_health.py`). I read S025's brief, impl report and code review r1.

**What changed that touches S019:**
- `tickets_core.MOVES`: *not a fault* from in progress; `allowed_moves(state,
  held_keys, has_repeat=False)`; `send_back_error`; `close_tickets_first`.
- `tickets.py`: the send-back refusal under the ticket's lock;
  `_latest_repeat_serial`; `_recheck_repeat` after the raise's insert; the
  component edit's `LOCK IN SHARE MODE`; the lock-order note rewritten.
- `local_db.py`: one migration v20; `_PRECONDITIONS`; `MigrationBlocked`;
  `LATEST_VERSION = _MIGRATIONS[-1][0]`.
- `masters.py`: a unit with tickets `state <> 'closed'` cannot be deactivated.
- `api_common.py`: JSON bodies for 404, 405, 500 and the lost-connection 503.
- `RegradeDialog.vue`: reload on a 400 or 409 no visible field shows.
- Tests: `test_migration_v20.py` (new, in `vel_yantra_upgrade`),
  `tests/fixtures/migrations_v13.py` (frozen), the old migration tests
  retargeted to v20, `test_migration_v12.py` trimmed.
- e2e: `regradeByApi`, `causeId`, `postAs` in `support/tickets.js`; three S025
  tests in `tickets-work.spec.js`; the unit test in `masters.spec.js`.
- `.claude/CLAUDE.md`: a *Migrations (S025)* bullet and an SMTW-Review point:
  "a migration that touches rows that exist in production carries a
  `_PRECONDITIONS` entry and a test from the production schema. Check both on
  every migration after v20."

## Findings

### BS1-01 — `minor` — § 5.6 says no new lock, but every move takes three shared locks

**What changed.** S025's code review (CR1-02, open) found that a ticket state
change re-checks the foreign keys `fk_tickets_equipment`, `fk_tickets_unit`
and `fk_tickets_component`: `state` is the second column of their indexes, so
every `UPDATE tickets SET state` takes a shared lock on the machine row, the
unit row and the component row. S025's own race test only passes with
`FOREIGN_KEY_CHECKS = 0` (impl report decision 7). CR1-02 asks for the
lock-order note in `tickets.py` to say so and to list two accepted deadlocks:
a repeat raised against a send-back, and a unit edit against a move in that
unit (S025's new deactivation guard counts tickets under the unit's lock).

**What is now wrong.** § 5.6: "No new table is locked, and no new lock-order
edge appears." That is true of explicit locks only. S019's new state changes
(`schedule`, `reschedule`, start from scheduled) take the same three shared
locks as every move, so they also fall under the unit-edit deadlock. A coder
who follows § 5.6 as written would add "nothing else locked" to the note that
CR1-02 is correcting.

**Fix.** Reword § 5.6, for example: "Each move locks the ticket row `FOR
UPDATE`, and its state change takes the shared foreign-key locks on the
machine, unit and component rows that every move takes (S025 CR1-02). No
explicit lock is added, and no new lock-order edge appears; the two accepted
deadlocks CR1-02 lists cover the new moves too." Tell the coder to add the new
moves to the lock-order note in the words CR1-02 asks for, once S025's fix is
in the tree. Design unchanged.

- (a) Reword § 5.6 as above — **recommended**.
- (b) Leave it: the next reader of the note gets a false statement.

### BS1-02 — `minor` — v21 must answer S025's new migration rule, and the "row from before" test needs S025's pattern

**What changed.** S025 set three conventions: a migration that cannot run on
existing data gets a `_PRECONDITIONS` entry, checked for every pending version
before any is applied (`local_db.py` header, CLAUDE.md); the old migrations
live only in the frozen fixture; an upgrade is tested in `vel_yantra_upgrade`
by building an older schema with `_MIGRATIONS` monkeypatched, then running the
new list (`test_migration_v20.py`: `_recreate`, `_migrate`, `_schema`). The
SMTW-Review audit now checks every migration after v20 for a precondition and
a test from the production schema.

**What is now wrong or missing.**
1. § 4.3: "This is the kind of migration S025 § 1.9's warning is about." It
   is not. S025's warning text (impl report § 5) names a `NOT NULL` column or
   a foreign key on a table with rows, a dropped column the old image reads,
   and data that cannot be converted. v21 adds nullable columns, appends an
   ENUM value and adds a CHECK that every existing row satisfies (state is
   never `scheduled`, both plan columns NULL). The brief should say plainly:
   **v21 carries no `_PRECONDITIONS` entry**, and why, and that the comment
   above v21 in `local_db.py` says so, so the audit does not flag it.
2. § 8 Migration: "a ticket row from before the migration unchanged". On the
   shared test database v21 is already applied when the tests start
   (`conftest` runs `init_db`), so a "row from before" cannot be made there.
   The test must follow S025's pattern: recreate `vel_yantra_upgrade`, run
   `_MIGRATIONS` pinned to v20 alone, insert the shortest chain a ticket needs
   (site, unit, equipment class, equipment, ticket, its raised event), run
   v20 + v21, and check the row, the columns, the ENUM with its `NOT NULL
   DEFAULT 'raised'`, and `chk_tickets_plan`; then delete `db_version` 21 and
   run again. Reuse `test_migration_v20.py`'s helpers (import them, or move
   `_recreate`, `_migrate`, `_schema` into one small `tests/upgrade_db.py`)
   rather than copy them. `pytest` runs the files one after another, so the two
   files sharing `vel_yantra_upgrade` do not collide.
3. § 4.3: "safe to run twice, as since v5" — the convention now lives in v20's
   header comment ("every statement is safe to run twice"). Cite that.

**Fix.** The three wording changes above in § 4.3 and § 8. No design change.

- (a) State "no precondition, because …" and the upgrade-database test —
  **recommended**.
- (b) Add a `_PRECONDITIONS` entry for v21 anyway: it would have nothing to
  check, and the rule is for migrations that can fail on data.

### BS1-03 — `minor` — The e2e checks must name S024's conventions, and the seed must name its node and database

**What changed.** S025's brief (BS1-03) listed the suite's conventions and the
code now has them: `consoleWatch.allowFailedRequest(urlPart, status)` for every
refusal a test provokes (the console watch fails the test on any other failed
request); `expectFieldMessage(scope, text)`; `moveByApi` and `regradeByApi`
for setup (`postAs` expects 200); the three projects share one database, so a
test that changes a count reads it first (`masters.spec.js`, `openTicketsAt`).
`e2e_backend.py` sets `config.DB_CONFIG["database"] = E2E_DATABASE` in its own
process and guards the name with `check_target`.

**What is now wrong or missing.**
1. § 8 Plain: "saving *Change plan* unchanged shows 'Nothing to change'" is a
   400 from `/moves/reschedule`. The test must declare
   `consoleWatch.allowFailedRequest("/moves/reschedule", 400)` and check the
   message with `expectFieldMessage(dialog, "Nothing to change")`. The brief
   does not say so; the test fails on the console watch otherwise.
2. § 3 Tests, the seed: "pymysql with `config.DB_CONFIG` and the e2e database
   name `vel_yantra_e2e`, as `e2e_backend.py` sets it." `seed_e2e.py` runs in
   its own process (`global-setup.js`) and does not import `config`. It must
   put `backend/` on the path, import `config`, set the database name from
   `e2e_backend.E2E_DATABASE` (same folder) and run `e2e_backend.check_target`
   before any SQL, so a mistyped setting can never write to the dev database.
3. The seed does not say which node the overdue ticket is raised on. Name it:
   **`E2E MCC1 mill`** (SMTW.MCC1). The engineer sees every SMTW unit, so the
   *Overdue* test can run as the engineer; the one test that counts tickets at
   MCC1 (`masters.spec.js`, S025) reads the count through the API first, so
   one more open ticket there is harmless. The raise spec's "Already reported
   on this machine" check is on the extruder and would list a seeded ticket
   there; the mill keeps it out. Give the ticket a fixed description ("E2E
   seed: overdue for parts") so the test finds its row by text.
4. Setup for the other flows is by `moveByApi("engineer", id, "schedule",
   {planned_date, waiting_reason})` and `moveByApi("technician", id,
   "acknowledge")` (the "technician sees no *Schedule*" check). Say so, so the
   coder does not drive setup through the screens.

**Fix.** Add the four points to § 3 Tests and § 8. No design change.

### BS1-04 — `nit` — The v20 tests do run the whole `_MIGRATIONS` list: the pin is now a fact, not a condition

§ 3 Tests: "If S025 wrote them to run the whole `_MIGRATIONS` list, S019 pins
them to v20 … The coder checks this in S025's impl report first." The report
is silent; the code answers: `test_migration_v20.py:25` has `V20 =
list(local_db._MIGRATIONS)`, and `reference`, the production path and the dev
path all build with it. Once v21 exists, `test_v20_builds_the_schema_v1_to_v13_built`
compares a v20 + v21 schema against the v1–v13 reference and fails.

**Fix.** Replace the condition with the fact: S019 sets `V20 = [m for m in
local_db._MIGRATIONS if m[0] == 20]` and leaves every assertion as it is
(`_versions() == [20]`, 27 tables, `[*range(1, 14), 20]`). `test_modules.py`
reads `LATEST_VERSION` from the module, so it does not break.

### BS1-05 — `nit` — The Order paragraph and the Status line describe an order that no longer holds

"S019 is coded **after S025** is committed" and Status "(coded after S025)".
S025 is not committed: it is in the working tree, the user will commit S025,
S019 and S020 together, and S019 is coded on top of S025's uncommitted code.

**Fix.** Say that in the Order paragraph and the Status line, and set
`Baseline: 3df667c + uncommitted S025` after this round.

### BS1-06 — `nit` — The first release applies v20, v21 and v22 together; S025's check says "schema 20"

§ 4.3 is right that production has no tickets. But with the three steps
committed together, the first release after the squash runs v20, v21 (and
S020's v22) in one `init_db`: the preconditions of all pending versions are
checked first (only v20 has one), then each is applied in order. S025's
device-check row 9 and its impl report say "Settings › Database shows schema
**20**"; at that release it will show the latest version.

**Fix.** One sentence in § 4.3: the release applies v20–v22 together, v21 has
no precondition, and the planner changes S025's row 9 and impl-report check to
"the latest schema version" when the steps are committed. Cross-step; wording
only.

### BS1-07 — `nit` — `test_migration_v12.py:63` moved

S025 trimmed the file; the `state` ENUM assertion is now line 57, in
`test_tables_and_indexes`. Cite the test by name, not by line.

## Checked and found consistent

- **Not a fault from in progress (S025 U4).** § 1.2's table already lists it;
  § 3's "`start`, `restore`, `not-a-fault` gain `SCHEDULED`" and the
  `test_the_table` / `test_moves_listed_per_user` notes still describe the
  right changes (the engineer's list on a raised ticket is now
  `["acknowledge", "start", "restore", "not-a-fault"]` and gains `schedule`).
  `test_a_wrong_state_is_409`'s pairs involve no state S019 changes.
- **`allowed_moves(state, held_keys, has_repeat=False)`.** The new signature
  passes S019's moves through unchanged; `_moves` already builds one entry per
  name with `recording_as`, where `asks_machine_stopped` fits.
- **Send-back and repeats.** `latest_restoration` returns None unless the
  state is back in service or closed, so a ticket scheduled after a send-back
  is no repeat candidate; `_recheck_repeat` and `_send_back` never see
  `scheduled`. § 1.2 "send back and close are unchanged" holds.
- **Units frozen by tickets.** The deactivation guard counts `state <>
  'closed'`, so a scheduled ticket keeps its unit active, as `OPEN_STATES`
  will say.
- **Change severity while scheduled.** `regrade` checks `REGRADE_STATES`
  under the lock; `RegradeDialog`'s reload on a 400/409 is unaffected by a
  new state.
- **JSON errors.** The 409 "This ticket changed — reload" and every 400 on a
  field stay `ApiError`s; S025's handlers only cover what was unhandled. A
  `chk_tickets_plan` violation would be an `OperationalError` 4025 → the 500
  body, which is the right answer for a guard that never fires.
- **v20's `tickets` and `ticket_events`.** `state ENUM(...) NOT NULL DEFAULT
  'raised'`; `from_state` / `to_state` `VARCHAR(20)`; `ix_tickets_unit_state`
  present. § 4's `MODIFY` restating `NOT NULL DEFAULT 'raised'` is right.
- **`_apply_move` and `_MOVE_STEPS`.** Still `(cur, ticket, clean,
  occurred_at, last, now, prefix) -> (event fields, ticket changes)`, with
  `update_row(... {"state": spec.to_state, **changes})` after the step: the
  one-place clearing of the plan columns (§ 5.3) fits. `_LOCK_TICKET` and the
  list's `ORDER BY` (`t.intensity, t.occurred_at, t.id`) are as the brief
  quotes. `validate_labour` still parses `work_date` inline, so `_optional_date`
  is still an extraction, not a duplicate.
- **e2e helpers the brief names.** `expectDialogFits`, `expectFieldMessage`,
  `moveByApi`, `stateBadge`, `timeValue`, `timeline`, `card` exist with the
  described shapes.
- **Standards, UX, permissions, decisions 1–10, § 9.** Not re-reviewed; nothing
  in the diff touches them.

## Summary for the orchestrator

- File: `docs/steps/S019-deferred-work/2-brief-review-s1.md`.
- Findings: 0 blocker, 0 major, 3 minor (BS1-01 … BS1-03), 4 nit (BS1-04 …
  BS1-07).
- No blocker or major is open: the planner fixes the wording and the coder
  starts, with `Baseline: 3df667c + uncommitted S025`.
