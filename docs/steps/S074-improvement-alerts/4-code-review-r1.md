```
Step: S074 — Improvement alerts
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S074 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The three alerts, the daily scan, v40 and the
D1 widening follow the brief. Ticket alerts behave as before. One minor finding (a worker test can
now reach the real push service) and three nits remain.

## Test results (my runs)

- All unit suites, `YANTRA_TEST_RUN=s074cr1 tooling/run-tests.bat`: backend 3865 passed (148 s),
  frontend 346 passed, tooling 185 passed. ALL SUITES: PASSED.
- `npx vite build` in `frontend/`: built in 4 s, only the known chunk-size warning.
- Browser tests: none re-run, because no finding of mine needs a run. The coder's runs are the
  right ones:
  - the new test alone (1 passed);
  - targeted `notifications.spec.js`, `settings.spec.js` and `screens.spec.js` (35 passed,
    4 skipped). These are the screens and the API this step changed (`/api/push/config`'s
    `you_get`, Settings › Background tasks), plus `screens.spec.js`;
  - the whole suite at Normal once (290 passed, 13 skipped).
  No shared frontend file changed, so no WebKit run was due.

## Findings

### CR1-01 (minor) — a worker test now runs the improvement scan with the real push sender

`backend/tests/test_worker.py:82-88` (`test_retaken_after_a_dropped_connection`), together with
`backend/scheduled_tasks.py:12-16`.

- **Problem.** This test calls `Worker.run_once()` with the real `SCHEDULE` and the real clock
  (`now_ist`). Push is on for the session (`conftest.vapid_pair`), and `push_sender.send` is not
  faked. Before S074, the only scheduled task was the purge, which sends nothing. Now, when the test
  runs after 08:00 IST, `improvement_alert_scan` is due too. `run_once` drains every due task, so
  the run does three things:
  1. the scan reads the whole worker database;
  2. the alert tasks run;
  3. the `push_send` tasks run through pywebpush.
  `add_device` stores a valid p256dh key and an `https://fcm.googleapis.com/fcm/send/test-…`
  endpoint. So any `push_send` this test drains posts to FCM.
- **Failure scenario.** Today every test that makes a countermeasure overdue for an owner with a
  device also scans in the same test, so no candidate with a device is left over. The guard is
  luck, not design:
  - a later test (R03.7's PM scan, or an S074 test edited later) leaves an overdue countermeasure
    whose owner has a device on the same xdist worker;
  - a test run that crosses midnight IST makes `test_the_owners_devices_get_it_quietly`'s
    countermeasure, due "today", overdue.
  In both cases a run after 08:00 sends a real push to Google. What the test does also depends on
  the time of day. The brief (§ 8.2) and the orchestrator ask that no test reaches a push service.
- **Fix.** In `test_retaken_after_a_dropped_connection`, patch `worker_module.SCHEDULE` to `[]`. The
  test checks the reconnect, not the schedule. Or patch it to the purge alone, as
  `TestSchedule.test_due_task_enqueued_once_and_run` does at `:129`. For a guard on every test,
  also add an autouse session fixture in `conftest.py` that makes `push_sender.send` raise unless a
  test patches it. The SMTP fixture beside it sets reserved values for the same reason.

## Nits

- **CR1-02** (nit) `backend/alerts.py:154`: `_marks` is the third private copy of the same
  placeholder helper (`improvements._in` at `improvements.py:251`, `meters._marks` at
  `meters.py:468`). Leave it for this step, or move one shared helper next to the DB code in a
  later clean-up.
- **CR1-03** (nit) `backend/task_handlers.py:241`: the "not sent" log names only the two states. It
  is misleading when the reason is a changed owner, due date or watch end ("the improvement is
  actions_open and the countermeasure open"). Add the payload's expected value, or say "no longer
  true" when both states are still open.
- **CR1-04** (nit) `frontend/e2e/settings.spec.js:82`: `.mb-3 > .fw-semibold` ties the test to
  Bootstrap spacing classes. A test id or a role-based locator on the task's title would survive a
  restyle of the card.

## Checked against the orchestrator's points

- **D1 widening, behaviour-neutral for tickets.**
  - `recipients` is now a thin call to `people_at_unit` with the ticket's site, `[unit_id]`,
    `AUDIENCE[kind]`, the same exclude list and `with_email`. The SQL is the same: `pu.unit_id IN
    (%s)` with one value equals the old `= %s`.
  - The only new behaviour is `[]` for empty roles, where the old code would have built `IN ()`.
    No ticket kind has an empty audience today.
  - `_push_fan_out` keeps its recipients, its message and `ALERT_TTL_SECONDS`, through
    `_push_to_people`, and keeps its log line.
  - `ticket_alert` now refuses improvement kinds (`test_alerts.py:369`).
  - Proof: `test_alerts.py` (`TestFanOut`, `TestEscalation`, the assigned tests) and
    `test_closed_email.py` run whole and unchanged in their expectations: green in my run.
- **The scan's transaction.** `SELECT NOW()` comes first. Then one plain read per table, which
  only narrows the work. Then, per improvement in id order: (6b) `FOR UPDATE`, then its candidate
  (6c) rows `FOR UPDATE` in id order, one statement each. The decision comes from the locked rows,
  which are current reads under REPEATABLE READ. The marker `UPDATE`s touch only rows the scan
  holds, and the only other write is the `task_queue` inserts.
  - Success: the markers, the alert tasks and `done` are committed together by the worker.
  - Any exception: everything rolls back, and the queue retries with the back-off. The scan raises
    no `RetryLater` or `NoRetry`, and `BadTask` only for a payload.
  - Proof: `TestScanTransaction` (a fault after the first marker leaves no marker and no task).
- **Locks against the LOCK ORDER notes.**
  - The scan takes no lock before (6b), and no ticket, person or unit lock.
  - Each route holds at most one (6b) while it waits, and always takes (6b) before (6c)
    (`_lock_for_actions`).
  - *Not effective* only inserts a new `improvements` row. A unique equality `FOR UPDATE` takes no
    gap lock, so that insert never waits on the scan.
  - `improvements.updated_at` has no `ON UPDATE`, so the markers stamp nothing.
  - The notes in `improvements.py`, `alerts.py` and `equipment.py` say all this.
- **Once-only markers (v40).**
  - `overdue_alert_due` and `ready_alert_due` use `!=`, and the candidate SQL uses `<>`.
  - The pure tests cover a date moved later and a date moved earlier (overdue), and a watch
    extended and a watch cut (ready).
  - The shell tests cover a second scan and a due date moved later.
  - When push is off, the markers and the tasks are still written, and each task logs and is done:
    `test_push_off_still_marks_and_queues_once`, through the worker.
- **Recipients by key.**
  - `roles_holding` derives the roles from `compute_permissions`. An unknown key gives `()`, so
    `people_at_unit` returns `[]` (fail-closed).
  - The units are the improvement's own and its machine's current unit. These are the two columns
    of `_visible_condition` (`unit_access_condition(cur, READ_KEY, "i.unit_id", "m.unit_id")`),
    read at the improvement's site. The other-site gap (BR1-08) is accepted.
  - *For you* goes only to the current owner, *overdue* only to the owner and the lead
    (`lead_id` is NOT NULL, so `sorted({…})` is safe), *ready* to every verify holder.
  - Tested:
    - a storekeeper owner gets nothing;
    - an owner with no login gets nothing, and the lead still gets the overdue alert;
    - the lead as owner gets one alert;
    - *ready* reaches the site's manager and the all-units engineer, not a technician or an
      engineer of another unit.
  - IT admin and admin have no membership, so they are never recipients.
- **The send-time recheck.**
  - `should_send_improvement` reads the rows as they are when the task runs, and covers every row
    of § 5.3's change table (pure tests).
  - The shell tests cover an owner changed again and a countermeasure cancelled.
  - A countermeasure of another improvement, an unknown improvement, a bad date, a missing
    `action_id` and an unknown kind are each a `BadTask`.
- **Quiet push.** `improvement_message` sets `quiet` True, so `send_task_payload` sends Urgency
  `low` and `silent`, with TTL 86400 (`IMPROVEMENT_TTL_SECONDS`). Asserted on the queued
  `push_send` payloads and on the faked sender's call (`"low", 86400`).
- ***What you will get*.**
  - The verify line comes per membership with a place, between the ticket line and the email line.
  - The countermeasure line comes once for an `improvement:read` holder, and the lead line once
    for an `improvement:edit` holder (`may_lead`'s key).
  - The changed tests:
    - `TestYouGet`: five lists extended, and a new operator test;
    - `test_push_api.py`: the engineer's list;
    - `notifications.spec.js`: the technician's exact list, the engineer's verify line, and the
      operator added to the dot test.
  - The storekeeper and IT admin still get nothing.
- **sw.js** is not in the diff: no caching, no `fetch` handler, unchanged.
- **Schema docs for v40.** `docs/schema.md` names both columns, their types and positions, and
  "migration v40". `docs/schema.html` has the meta line and both columns in the tab that lists
  these tables. No Mermaid change is needed (no new link).

## Manual checks still for the user (real device)

- [ ] **Important** (device row 53): *Countermeasure for you* reaches the technician's phone quietly
  (charging or on Wi-Fi), and a tap opens the improvement page.
- Row 54: *Countermeasure overdue* after 08:00 the next day on both phones; on the technician's
  phone it replaces the earlier alert.

The impl report's `## Manual checks` has both device rows and the three `[auto]` checks of § 8.4,
each with a passing run behind it.

## Checked and found consistent

- Scope: everything in § 3 is built. Nothing outside the brief is built. The impl report's § 4
  lists every small choice (`IMPROVEMENT_AUDIENCE_KEY`, `improvement_recipients`,
  `PAYLOAD_DATE`/`PAYLOAD_TIME`, the `mark_*` helpers, the `read_alert_improvement` signature).
- Import direction as § 3 states: `alerts_core` imports `improvements_core` and `access_core`, and
  `alerts` never imports `improvements`. No cycle.
- The request side:
  - `_queue_given` runs after the insert and `_settle_state` (add), and only when `owner_id` is in
    `changes` (change), with the old owner from the (6c) locked row;
  - the task is inserted in the route's transaction, so a refused add queues nothing (tested);
  - a due-date-only `PUT` and an owner who gives it to themselves send nothing (tested).
- Payloads carry person ids and a login, never an address (A.5.34).
- The migration:
  - v40 is append-only, with `ADD COLUMN IF NOT EXISTS` and no `_PRECONDITIONS` entry (the
    brief's assumption);
  - `test_migration_v40.py` covers a fresh database, a v39 database with rows, and a re-run.
- `SCHEDULE` order: the purge stays first (`TestTasksCard` reads `tasks[0]`). The Settings label
  is plain text (scope B).
- The texts match § 5.4 exactly, DD-MM-YYYY. The tags let the overdue alert replace the given one.
- The docs pass: `Plan.MD` § 4.7 (three rows and a bullet), `device-checks.md` rows 53 and 54, and
  the schema docs. `.claude/CLAUDE.md` was left unedited by the orchestrator's instruction, and
  its text is proposed in the report.
- The database down: the routes go through `get_db()` (503), and the worker reconnects. A scan
  missed while the database was down runs once on return (`due_tasks`).
- The track is full, as the step needs (a migration, locks, recipients by permission).

## Feedback

- hindrance: the step diff (`step_snapshot.py diff S074 --stat`) also lists S073's gate-B files
  (`S073-…/1-brief.md`, `4-code-review-r2.md`, the S073 row of `INDEX.md`), so I had to sort the
  orchestrator's edits from the coder's by hand (2 min).
- idea: an autouse test guard that makes `push_sender.send` raise unless faked would turn "no test
  reaches a push service" from a review question into a failing test (CR1-01; finding the path took
  about 10 min of reading `test_worker.py`, `conftest.py` and `add_device`).
