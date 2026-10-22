```
Step: S025 — Release safety and ticket integrity (audit fixes)
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S025 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 `minor` findings and 3 `nit`s.
The step builds what the brief, A1 and U1–U5 ask for, and every suite is green in my own runs.

Reviewed: the working-tree diff against `3df667c` (S025's files only; the status edits in
other step folders and in other README index rows are not S025's and are not reviewed).

## Test results (my runs, 21-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0 — backend 1855 passed; frontend 12 files, 93 tests passed; deps 42 passed; tooling 20 passed |
| `npx vite build` (frontend) | built, no new warnings |
| `tooling/run-deps-audit.bat` | exit 0 — 3 SBOMs, 181 libraries, 0 vulnerabilities, 2 stale direct dependencies (not gating); `sbom/` regenerated identical to the working tree (Pillow 13.0.0) |
| `tooling/run-e2e-tests.bat` | exit 0 — 147 passed in 5.2 min (49 tests × 3 projects); 0 failed, 0 skipped; the four S025 tests pass in all three projects |

## Findings

### CR1-01 — `minor` — A malformed HTTP answer during the poll crashes the deploy with no rollback lines

`tooling/deploy.py:188`

- **Problem.** `_schema_ready_once` catches `OSError`, `ValueError` and `AttributeError`.
  `urllib.request.urlopen` passes some `http.client` errors through unwrapped:
  `BadStatusLine`, `IncompleteRead` and `LineTooLong` are subclasses of
  `http.client.HTTPException`, not of `OSError` (checked: `issubclass(...)` is false for all
  three; `do_open` wraps only the `h.request` call in `URLError`, not `getresponse()`).
- **Failure scenario.** During the release, nginx or the container closes a connection in the
  middle of a response (a container restart while the poll reads the body). `IncompleteRead`
  escapes, `main()` ends with a traceback, and the rollback lines (§ 5.4, BR3-04: "any failure
  after the stamp") are never printed. The stamp has already been changed on ansible-ws.
- **Fix.** Add `http.client.HTTPException` to the caught tuple ("not yet"), with one more case
  in `TestPoll.test_anything_else_is_not_yet`. As a safety net, wrap the part of `main()` after
  the stamp in `try … except Exception` that calls `_fail_after_stamp`, so no unexpected
  error can skip the rollback lines.

### CR1-02 — `minor` — The lock-order notes miss the foreign-key checks a ticket state change makes

`backend/tickets.py:24-33`, `backend/equipment.py:58-64`, `backend/masters.py:255, 288`,
`3-impl-report.md` § 4 decision 7, `backend/tests/test_ticket_work_api.py:688-695`

- **Problem.** The notes say that working a ticket "locks (7) only; nothing else locked".
  This is not true. `state` is the second column of `ix_tickets_equipment_state`,
  `ix_tickets_unit_state` and `ix_tickets_component_state`. These indexes serve the foreign keys
  `fk_tickets_equipment`, `fk_tickets_unit` and `fk_tickets_component`. InnoDB re-checks a
  foreign key when it rewrites an entry of that key's index. So every move takes a shared lock
  on the machine row, the unit row and (when set) the component row. The coder saw this
  (decision 7: with foreign-key checks on, the test's state change waited for the machine
  row). This behaviour is older than S025, but two S025 statements depend on it:
  1. **Raise of a repeat against a send-back** (§ 5.2). Sequence:
     - the send-back locks the earlier ticket FOR UPDATE;
     - the raise locks the machine (1) and inserts, then waits on the earlier ticket's
       shared lock;
     - the send-back's `UPDATE tickets SET state` then waits on the machine's shared lock.

     This is a deadlock (1213), not "the other is refused". InnoDB rolls one side back, and
     that user sees the 500 "Something went wrong — try again". Integrity still holds: the two
     cannot both succeed. Decision 7's "a real send-back would have committed before the raise
     took the machine lock" is not guaranteed. The race test turns `FOREIGN_KEY_CHECKS` off,
     so it covers only the order where the send-back commits first.
  2. **A new edge from the unit guards** (§ 5.3). `update_unit` locks the unit FOR UPDATE and
     then counts the unit's tickets `LOCK IN SHARE MODE`. A ticket move in that unit
     delete-marks its old `ix_tickets_unit_state` entry, then waits on the unit's shared
     foreign-key lock. If the move's update falls between the unit lock and the count, each
     side waits on the other: 1213. Before S025 the unit edit never waited on ticket rows.
     The window is milliseconds, and the edit is a rare IT admin action.
- **Failure scenario.** A technician sends back TK-0042 while an operator raises its repeat
  on the same machine. One of them gets "Something went wrong — try again" instead of the
  409 or 400 refusal. A retry gives the right answer. The next engineer who reads the notes
  trusts "nothing else locked" and adds a lock that turns this rare deadlock into a regular
  one.
- **Fix.** Documentation only; no code change is needed:
  - in the `tickets.py` and `equipment.py` notes, say that a state change re-checks the
    machine, unit and component foreign keys (shared locks);
  - list the two cases above as accepted rare deadlocks, beside the two the notes already
    accept (1213 → JSON 500, retry works);
  - correct the § 5.2 wording in the `tickets.py` note and decision 7, and say in the
    race test's comment which order it covers.

### CR1-03 — `nit` — After a half-finished push, the refusal sends the user to a Deploy that will fail

`tooling/build/build.bat:84-90`

- **Problem.** The pushes run in this order: backend version, backend latest, frontend
  version, frontend latest. If a push fails half way, a rerun finds the backend tag and
  refuses with "nothing new to release; use the Deploy run config to redeploy". That Deploy
  pulls a frontend tag that does not exist, so the playbook fails.
- **Fix.** Inspect both tags first. If only one is present, say so: "Only <image>:<X> is in the
  registry — the last push stopped half way. Delete that tag in the registry, then run the
  release again." Keep the current message for the case where both are present. Refusing
  stays right (see the view on departure 3 below).

### CR1-04 — `nit` — A failed stamp does not print the version it replaced

`tooling/deploy.py:247-248`

- **Problem.** `stamp()` can fail after the `sed` has run. For example, plink loses the
  connection after the remote command has completed, or the check of the output fails. The
  script then exits 1 and does not say what the version was before.
- **Fix.** On a failed stamp, print one line: "If `YANTRA_VER` now shows <version>, stamp it
  back with: `<stamp_command(previous)>`". `previous` is already known at this point.

### CR1-05 — `nit` — The poll cannot tell the new image from the old one

`tooling/deploy.py:180-205`

- **Problem.** `schema_ready: true` is also what the **old** container answers. Suppose the
  playbook reports success but does not recreate the backend (for example, the compose kept
  the running container). The poll then passes at once, and the deploy prints "Deployed Yantra
  <X>; schema ready" for a version that is not running.
- **Fix (proposal, beyond the brief).** Also read `/api/version` and require the version just
  stamped. This is one more GET on the URL next to `/api/health`. Raise it as a queued item if
  you do not want it in this step.

## View on the coder's three departures

1. **The e2e unit test expects the real open count (decision 9). Accept.** Fact: Playwright
   runs with `workers: 1` and `fullyParallel: false`, so nothing changes the count between the
   API read and the refusal. The list query (`state=open`) and the guard (`state <> 'closed'`)
   are separate code paths, so the test still checks the guard's count. The test closes its
   own ticket at the end.
2. **No rollback lines after a failed stamp (decision 10). Accept.** A stamp failure is
   before the change in the normal case: `set -e` stops at the `grep -q` when the key is
   missing, and `sed -i` writes the file in one step. Printing the full rollback would claim
   that a deploy happened. The one leftover case is covered by the nit CR1-04.
3. **`build.bat` refuses when either tag exists (decision 8). Accept.** Overwriting a
   version tag would break "one version, one commit", which the brief asks for. Skipping the
   image that is already present would be safe only for images built after S025's clean-tree
   and tag checks, and the script cannot tell those images from older ones. The recovery
   message needs the fix in CR1-03.

## Points the orchestrator asked about

- **v20's equivalence to v1–v13.** Verified independently:
  - `tests/fixtures/migrations_v13.py` equals `_MIGRATIONS` at `ae3841f` and at `3df667c`
    (compared as Python data);
  - its v1–v5 equal the five migrations of `v0.1.3`. `v0.1.1` and `v0.1.2` hold the same five
    texts, so no earlier release ran different text;
  - after v5, only `equipment` and `equipment_events` of the ten v1–v5 tables are altered
    (v9: `model_id`, the ENUM value `'model'`, dropped `make`/`model`), so the guard checks
    the right two tables.

  The equivalence test compares tables (engine, collation), columns (position, type, nullability,
  default, extra, charset, collation), index entries, foreign keys with their columns, and
  CHECK clauses, all filtered by `TABLE_SCHEMA = DATABASE()`. It passes for an empty database,
  for the production path after the two drops, and for a v13 database with a re-run.
- **The guard.** It runs inside `GET_LOCK` after `_get_applied_versions`, for every pending
  version, before any statement. An absent table passes. A refusal raises `MigrationBlocked`
  (a `DBUnavailable`). `ensure_schema` keeps the message, and the lock is released in
  `finally`. The production-path test shows the database unchanged after a refusal (schema,
  masters, `db_version` 1–5). The single-table message is tested too. Production's state
  (both tables dropped by the user on 21-10-2026) passes the guard. v20 then creates them in
  today's shape.
- **Lock order of the component check.** The edit locks the ticket (7) first, then the
  component LOCK IN SHARE MODE. The foreign key on `component_id` would take that same shared
  lock at the UPDATE, so the order of locks is unchanged. A scrap of that component holds it
  FOR UPDATE and never waits on a ticket row: `_check_no_open_tickets` is a plain count, with
  its snapshot taken after the node lock. So the two serialise without a deadlock. The parent
  is read plain. The race test (a scrap committed after the edit's snapshot) fails without
  the fix. The notes elsewhere need CR1-02.
- **`deploy.py`.**
  - The poll: every 10 s up to 180 s, with a 10 s request timeout. Non-200, `URLError`,
    `HTTPError`, a reset, and a body that is not JSON are all "not yet". The gap is CR1-01.
  - The previous version is read before the stamp; if it cannot be read, the script aborts
    and nothing changes.
  - The rollback lines reuse `stamp_command()`, the command the stamp itself runs, and cover
    both cases of § 5.4 (schema applied or not).
  - `DEPLOY_HEALTH_URL` is required only for a real deploy.
- **`build.bat`.**
  - The clean-tree check uses the same `git status --porcelain` as `release.py`, so the two
    agree. Test output is gitignored (`scratch/`, caches).
  - HEAD must equal `rev-list -n 1 v%VERSION%`. Login runs before the registry check. The
    check is inside a `for` block, where `if not errorlevel 1` is evaluated at run time (correct).
  - Every build and push is checked, and `scratch\` is no longer wiped.
- **JSON error handlers.**
  - Flask picks the handler by the exception's class (MRO), so `ApiError`, `IntegrityError`,
    `RequestEntityTooLarge` and `app.py`'s `DBUnavailable` keep their own handlers.
  - Flask returns `RequestRedirect` (a routing exception) before any handler runs, so
    trailing-slash redirects still work. The code has no `abort(<Response>)` whose body the
    `HTTPException` handler would replace.
  - The `Exception` handler logs the traceback itself. `OperationalError` is a 503 only for
    the lost-connection codes, which now live in one place (`local_db.is_connection_lost`)
    and are shared with the worker.

## Checked and found consistent

- **Brief § 1.4, units frozen by tickets.**
  - `_unit_is_referenced` counts any ticket.
  - The open-ticket deactivation guard runs before the equipment guard (BS1-04), with
    `close_tickets_first(n)` defined once in `tickets_core` and used by the unit refusal and
    the scrap refusal.
  - A machine with open tickets still moves (U3, tested).
- **Brief § 1.5, no send-back after a repeat.**
  - `allowed_moves(…, has_repeat)` and `send_back_error` are pure.
  - `has_repeat` is unfiltered: tested for a user who cannot see the repeat.
  - The send-back refusal is checked under the ticket's lock, and its plain read sees a raise
    committed before the lock was granted, because the first plain read comes after the
    `FOR UPDATE`.
  - The raise re-checks the earlier ticket with `LOCK IN SHARE MODE`; a refusal rolls back
    the whole raise (tested: no repeat row left).
- **Brief § 1.7, RegradeDialog.** In "stopped" mode an `intensity` refusal shows at the top.
  A 400 or 409 that no visible field shows emits `reload`. Client-side errors have no status,
  so they never reload. The e2e test shows both the message and the reloaded timeline.
- **Brief § 1.10 (U4), Not a fault after Start.**
  - `MOVES` allows the move from `in_progress`.
  - Times stay blank and labour stays (API test).
  - The screen follows the server's `moves` (e2e test).
  - The 409 list in `test_a_wrong_state_is_409` drops that case.
- **Brief § 1.1, `/api/health`.** It calls `ensure_schema` and always answers 200 with no
  error text. The false case is tested through the module's own reference (BR2-06).
- **A1, Pillow 13.0.0.** The `pyproject.toml`, `uv.lock` and SBOM changes match. The deps
  audit exits 0. The report lists the APIs that Yantra uses and the one behaviour change.
- **Old migration tests (BR2-07).** Their fate is as the report's table says. The re-targeted
  tests re-run v20 on the shared test database, which is idempotent.
- **Layers and security.** No business rule is in a route or a Vue file. No new route, so no
  new permission key. No actor is taken from the client. The new SQL uses parameters only;
  the `IN (…)` placeholders are built from code constants.
- **Docs.**
  - `.claude/CLAUDE.md`: the migrations bullet, the deploy bullet and the SMTW-Review
    *Migrations* point (BS1-01).
  - `docs/Plan.MD`: § 4.1, § 4.2, the § 1 schema row and the `user_units` row.
  - `docs/steps/README.md`: four Queued rows.
  - `device-checks.md`: row 9.
  - The impl report: the migration warning text for smtw-common, and the § 5.1 hand-over
    (steps 2–3 marked done by the user).
- **Manual checks.** The impl report has `## Manual checks`:
  - four `[auto]` checks backed by passing tests, plus "every screen opens on a v20
    database" through `screens.spec.js`;
  - the important real-device check (the first release) as an unticked box and as row 9.

  The flow tests call `expectDialogFits` on the dialogs they open.
- **Screen text (scope B).** The new texts are short and say what to do:
  - "Close its tickets first (N open)";
  - "This ticket came back as TK-…; work on that one";
  - "Not found", "Not allowed", "Something went wrong — try again";
  - "Database unavailable — try again shortly".
- **Impl report (scope A).** It is written in scope A; no finding.
- **Track.** The step is on the full track, as the brief says.

## Manual checks still needed (the user's)

- [ ] **Important.** The first release after the squash (row 9 of `device-checks.md`), run by
  KLA on production:
  1. Run the release.
  2. Check that the deploy waits for `schema_ready` and passes.
  3. Check that Settings › Database shows schema 20.
  4. Check that the sites, units, classes and types are still there.
  5. Check that the people who had unit access are in Team with their units.

  If the deploy is refused or fails, follow the rollback lines that `deploy.py` prints.
- The `build.bat` positive path (clean tree at the tag, both tags absent, pushes checked) is
  first run at that release, and so is the assumption that `docker manifest inspect` works
  with the registry login (brief § 9.5).
