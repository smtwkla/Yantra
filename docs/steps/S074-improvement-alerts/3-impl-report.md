```
Step: S074 — Improvement alerts
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
From: R05.5
```

# S074 — Implementation report

**Result:** the three improvement alerts are built as the brief says, push only, with the daily scan at
08:00 IST and migration v40. All unit suites are green (backend 3865, frontend 346, tooling 185); the targeted
browser run is green (35 passed, 4 skipped), and so is the whole browser suite at Normal (290 passed, 13 skipped). No departure from
the brief's design; the small choices are under § 4.

## 0. Stale brief check (§ 9)

The brief was written before S070–S073's code existed. I checked every name, route, column and lock note it
cites against the tree. **Nothing changes the design.** The differences are line numbers only; the code wins
where they differ:

| Brief says | The code now |
|---|---|
| `IMPROVEMENT_OPEN_STATES` at `improvements_core.py:26` | `:41`; the three open states `analysing`, `actions_open`, `watching` (S072 widened it, as the brief expects) |
| `ACTIONS_MAX` at `:91`, `overdue_days` at `:433` | `:107` and `:456` |
| `watch_until(watch_from, watch_days)` (new in S072) | exists, `improvements_core.py`, returns a datetime |
| `ACTION_OPEN`, `EDIT_KEY`, `READ_KEY`, `VERIFY_KEY`, `WATCHING`, `may_lead` | all exist with these names |
| LOCK ORDER note at `improvements.py:19` | starts at `:28` (the docstring grew in S069–S072) |
| S070's add and change routes `POST /api/improvements/<id>/actions`, `PUT …/actions/<action_id>` | `add_action` and `edit_action`; the change computes `changes` from the (6c) locked row, so `action["owner_id"]` is the old owner; the add ends with S072's line and `_settle_state`, as § 5.5 assumes |
| `current_person_id(cur)` at `auth_utils.py:314` | same |
| v39 column order: `watch_from` after `watch_days` | same; `closed_at` follows `watch_from`, so `ready_alert_for` sits between them |
| Migration number v40 | `_MIGRATIONS` ended at v39; S075 (approved, not coded) takes v41 |
| `equipment.py:9` global LOCK ORDER, (6b) and (6c) | same, `equipment.py:9-27` |
| `alerts_core`: `KINDS` `:26`, `CHANNELS` `:46`, `TICKET_PATH` `:68`, `ticket_facts` `:166`, `first_name` `:148`, `you_get` `:246` | about the same lines; all names as cited |
| `alerts.py`: `recipients` `:120`, `subscription_ids` `:154` | same |
| `task_handlers.py`: `_expect_no_payload` `:59`, `_ids` `:98`, `ticket_alert` `:108` with the kind check `:115`, `_push_fan_out` `:132`, `HANDLERS` `:289` | same |
| `push_core.py`: `ALERT_TTL_SECONDS` `:40`, `send_task_payload` `:167` | same |
| `access_core.py`: `expand_roles` `:28`, `compute_permissions` `:44` | same |
| `scheduled_tasks.SCHEDULE` `:12` | same |
| `test_alerts_core.py::TestYouGet`, `test_push_api.py:52-57`, `notifications.spec.js:203` and `:136`, `test_alerts.py:366`, `fake_send` `:443` | same; each breaks as § 8.3 says and was changed |
| S070 tests assert on `task_queue` (BR1-05) | none of `test_improvement*_api.py` reads `task_queue`; all stay green |
| `roles_holding("improvement:read")` = "operator, supervisor, technician, engineer, manager" | the same five roles; the function returns them in `SITE_ROLES` order (manager, engineer, supervisor, technician, operator), as § 5.6 says |
| `frontend/src/router/index.js:73` `/tickets/improvements/:id` | same |

## 1. What was built

- **Countermeasure for you.** When an engineer adds a countermeasure, or changes its owner, the owner gets a
  quiet push alert, unless they gave it to themselves. A change of only the kind, text or due date sends
  nothing.
- **Countermeasure overdue.** Every morning at 08:00 IST, the owner and the improvement's lead get one quiet
  alert for each open countermeasure past its due date, once per due date.
- **Ready to verify.** On the same morning run, the site's holders of `improvement:verify` (engineers and
  managers) covering the improvement's unit get one quiet alert when a watch has ended, once per watch end.
- **Who gets nothing:** a person who could not open the improvement (no `improvement:read`, or not covering
  its unit, such as a storekeeper owner), and a person without a device.
- ***What you will get*** on *My notifications* gains the lines of § 5.8, so the operator, the supervisor and
  the technician now see a countermeasure line, and the operator's bell shows its dot.
- **Settings › Background tasks** lists "Send the morning alerts: overdue countermeasures and improvements
  ready to verify — daily at 08:00".
- **Migration v40:** `improvement_actions.overdue_alert_for` (DATE NULL) and `improvements.ready_alert_for`
  (DATETIME NULL).

## 2. How it works

**Pure core (`alerts_core.py`, `access_core.py`).** The kinds are split per record: `TICKET_KINDS` (today's
five), `IMPROVEMENT_KINDS` (`action_given`, `action_overdue`, `verify_ready`), and `KINDS` as both. `CHANNELS`
gives the three new kinds push only. `IMPROVEMENT_AUDIENCE_KEY` names the key each improvement kind is about
(read, read, verify), as `AUDIENCE` names the ticket roles. The rules:

- `given_alert(owner, actor, old_owner)`: the owner is not the actor and changed.
- `overdue_alert_due(...)`: the improvement's stored state is open, the countermeasure is open, its due date is
  before today, and the marker differs from the due date (`!=`, BR1-01).
- `ready_alert_due(...)`: stored state `watching`, `watch_from` set, `now >= watch_until(...)`, and the marker
  differs from that end.
- `should_send_improvement(...)`: the row as it is when the task runs must still match what was queued
  (§ 5.3's change table).
- `improvement_facts`, `improvement_text`, `improvement_message`: the texts of § 5.4, the path
  `/tickets/improvements/<id>`, the tags `improvement-action-<id>` and `improvement-<id>`, quiet always.
- `you_get` reads `compute_permissions([role])` per membership: the verify line per membership with a place,
  then the two countermeasure lines once each after "Jobs assigned to you".
- `access_core.roles_holding(key)`: the site roles that hold a key, in `SITE_ROLES` order.

**Request side (`improvements.py`).** `_queue_given` runs at the end of `add_action`, and of `edit_action`
when `owner_id` changed. It calls `given_alert` with `current_person_id(cur)` and, when true,
`alerts.enqueue_improvement_alert(cur, ACTION_GIVEN, …, action_id, person_id, given_by=actor())`. The task
row is inserted in the route's transaction, so a refused write queues nothing. No new lock: `task_queue` has
no foreign key.

**The daily scan (`task_handlers.improvement_alert_scan`).** `scheduled_tasks.SCHEDULE` gains
`("improvement_alert_scan", "08:00")` after the purge. The handler takes no payload (BadTask otherwise). In
the worker's one transaction:

1. `SELECT NOW()` gives `now` and `today` (the session clock, IST).
2. `alerts.scan_candidates` makes one plain read per table with the brief's SQL (`<>` on the markers) and
   returns `{improvement_id: [action ids]}` in id order. It only narrows the work.
3. For each improvement in id order, `alerts.lock_for_scan` takes (6b) the improvement `FOR UPDATE`, then (6c)
   each candidate countermeasure `FOR UPDATE` in id order, one row per statement.
4. From the locked rows, `ready_alert_due` and `overdue_alert_due` decide. For each yes the handler writes the
   marker (`alerts.mark_ready_alerted` / `mark_overdue_alerted`, no `updated_*`) and queues an
   `improvement_alert` task with the end or the due date.
5. It logs "improvement_alert_scan: N overdue, M ready to verify".

A fault rolls the markers and the tasks back together; the queue retries (3 attempts), and a retry finds the
same candidates. The markers are written even when push is off (D8).

**The alert task (`task_handlers.improvement_alert`).** It validates the payload (kind in `IMPROVEMENT_KINDS`,
the integers, the date or time parsed with `PAYLOAD_DATE` / `PAYLOAD_TIME`; else BadTask). Then
`alerts.read_alert_improvement` reads plain: the improvement with its site, unit, machine and the machine's
current unit, the countermeasure of that improvement (BadTask when either is missing), and the giver's first
name from `given_by`. `should_send_improvement` decides from the rows as they are now; "not sent" is logged
with the states and the task is done. Push not set up: logged, done. Otherwise
`alerts.improvement_recipients` runs `people_at_unit` with the key's roles (`roles_holding`) at the
improvement's site, over the improvement's unit and the machine's current unit, limited to the owner
(*for you*), the owner and the lead (*overdue*, one id once), or every holder (*ready*). `_push_to_people`
queues one `push_send` per device with `IMPROVEMENT_TTL_SECONDS` (86400).

**Shared pieces (D1).** `alerts.people_at_unit` is today's `recipients` query widened to a list of units, an
`only_ids` filter and an exclude list; `recipients` now calls it with the ticket's site, `[unit_id]` and
`AUDIENCE[kind]`, so ticket alerts keep their result (`test_alerts.py` and `test_closed_email.py`, run
whole, are green). `task_handlers._push_to_people` is the device fan-out taken out of `_push_fan_out`, with
the TTL as a parameter, so tickets keep 3600. `ticket_alert` now checks `TICKET_KINDS`, so an improvement kind
sent to it is a BadTask.

**Locks.** As § 5.7: no new lock in the routes; the scan takes (6b) then (6c) in id order and updates only
held rows; the alert task reads plain. The LOCK ORDER notes say so in `improvements.py`, `alerts.py`'s
docstring and `equipment.py`'s (6b) bullet.

## 3. Files touched

**Code (10):**

- `backend/alerts_core.py` — the improvement kinds, `CHANNELS`, `IMPROVEMENT_AUDIENCE_KEY`, `IMPROVEMENT_PATH`,
  `PAYLOAD_DATE` / `PAYLOAD_TIME`, the rules, facts, texts and message; `you_get`'s new lines; docstring.
- `backend/access_core.py` — `roles_holding`.
- `backend/alerts.py` — `IMPROVEMENT_ALERT`, `IMPROVEMENT_SCAN`, `enqueue_improvement_alert`, `people_at_unit`
  (and `recipients` on it), `read_alert_improvement`, `improvement_recipients`, `scan_candidates`,
  `lock_for_scan`, the two marker updates; docstring with the scan's locks.
- `backend/task_handlers.py` — `_push_to_people`, `improvement_alert`, `improvement_alert_scan`, `TICKET_KINDS`
  in `ticket_alert`, `HANDLERS`.
- `backend/scheduled_tasks.py` — the 08:00 entry.
- `backend/push_core.py` — `IMPROVEMENT_TTL_SECONDS`.
- `backend/improvements.py` — `_queue_given` called by the add and the change of owner; LOCK ORDER bullet;
  import direction.
- `backend/local_db.py` — migration v40.
- `backend/equipment.py` — docstring: the (6b) bullet names the scan.
- `frontend/src/views/SettingsView.vue` — `TASK_LABELS` gains the scan's label.

**Tests (9):**

- `backend/tests/test_alerts_core.py` — `TestYouGet` updated (an operator test of its own), `TestChannels`
  gains the improvement kinds, new `TestGivenAlert`, `TestOverdueAlertDue`, `TestReadyAlertDue`,
  `TestShouldSendImprovement`, `TestImprovementTexts`.
- `backend/tests/test_access_core.py` — `TestRolesHolding`.
- `backend/tests/test_improvement_alerts.py` (new) — the request side, the handler, the scan, the transaction,
  the worker (sender faked; push off), bad tasks.
- `backend/tests/test_migration_v40.py` (new) — fresh, a v39 database with rows, a re-run.
- `backend/tests/test_alerts.py` — a `ticket_alert` with kind `action_given` is a BadTask.
- `backend/tests/test_scheduled_tasks.py` — the new entry after the purge.
- `backend/tests/test_push_api.py` — the engineer's `you_get`.
- `frontend/e2e/notifications.spec.js` — the technician's exact list, the engineer's verify line, the operator
  in the dot list.
- `frontend/e2e/settings.spec.js` — new test "S074: Background tasks lists the improvement alerts at 08:00".

**Docs:** see § Docs updated. **Step files:** this report; the brief's `Status`; the `INDEX.md` row.

## 4. Decisions taken

None changes the brief's design. Each is a small, forced choice:

1. **`should_send_improvement(kind, state, watch_end, action, expected)`** takes `expected`, the payload's
   fields already parsed (`person_id`, `due_date` as a date, `watch_until` as a datetime), not the raw payload,
   so the pure rule compares values and does no parsing. It returns a bool; the handler logs the states as
   the "reason", as `ticket_alert` logs the ticket's state.
2. **`read_alert_improvement(cur, improvement_id, action_id=None, given_by=None)` returns
   `(row, action, facts)`**, not `(row, facts)`: the handler needs the countermeasure's state, owner and due
   date for `should_send_improvement`. It takes `given_by` to read the giver's first name.
3. **`IMPROVEMENT_AUDIENCE_KEY`** in `alerts_core` (a pure table beside `AUDIENCE`) and
   **`alerts.improvement_recipients`** for § 5.6's three calls, so the handler holds no recipient rule. For
   *for you* it limits to the countermeasure's current owner, which `should_send_improvement` has just
   checked equals the payload's `person_id`.
4. **The marker updates** are `alerts.mark_overdue_alerted` and `alerts.mark_ready_alerted`, next to
   `lock_for_scan`, so the scan's SQL lives in one module.
5. **`PAYLOAD_DATE` / `PAYLOAD_TIME`** constants in `alerts_core`: `enqueue_improvement_alert` formats the
   dates with them and the handler parses with them, so the two cannot drift.
6. **`_queue_given`** in `improvements.py`: one helper for the add and the change of owner (DRY).
7. **`people_at_unit` returns `[]`** when `roles`, `unit_ids` or a given `only_ids` is empty, so no `IN ()`
   reaches MariaDB (an unknown key gives no roles: fail-closed).
8. **`alerts._marks(values)`** builds `%s, %s, …` for the new queries; `subscription_ids` keeps its own
   inline form (not touched).
9. **Tests share fixtures** by import: `aged`, `make_ready`, `add_action`, `cancel`, `set_watch`, `manager`,
   `modes` from `test_improvement_close_api.py`; `add_device`, `fake_send`, `run` from `test_alerts.py`.
   The scan reads the whole kept database, so each test asserts only on its own improvement's rows and tasks;
   the all-or-nothing test runs one scan first, so only its own two countermeasures are candidates. The
   worker tests empty `task_queue` before and after (as `test_worker.py`), so the worker drains only the
   scan's own tasks.
10. **The e2e settings test** asserts both task lines exactly (`.mb-3 > .fw-semibold`), so the new line's
    order after the purge is checked too.
11. **The brief's `test_nothing_for_other_roles`** was parametrised over operator and storekeeper; it now
    keeps the storekeeper only (not parametrised), and the operator has `test_operator_gets_the_countermeasure_line`.

## 5. Not done, deferred, assumed

- **Not done (out of scope, as the brief says):** email for these kinds, a reminder before the due date, PM
  alerts, any screen change, a setting for the scan's time.
- **Assumed (brief § 9):** v36–v40 ship in one release, so v40 has no `_PRECONDITIONS` entry.
- **Accepted gap (BR1-08):** a machine moved to a unit of another site: that site's readers see the
  improvement but get no alert.
- **To verify on the phones (device rows 53, 54):** how long Urgency `low` holds an alert on battery and
  mobile data (D7).
- `.claude/CLAUDE.md` is not edited (the orchestrator's rule); the text is under § Proposed CLAUDE.md changes.

## Tests

- **Pure core first:** `test_alerts_core.py` and `test_access_core.py`, 136 passed.
- **Shell, targeted:** `test_improvement_alerts.py`, `test_migration_v40.py`, `test_scheduled_tasks.py`,
  `test_push_api.py`, `test_alerts.py` and `test_closed_email.py` (whole, BR1-05), `test_worker.py`: 184
  passed. The improvement, RBAC, documents and modules suites (`test_improvement*_api.py`,
  `test_improvements_api.py`, `test_improvements_core.py`, `test_rbac.py`, `test_documents_api.py`,
  `test_modules.py`): 556 passed.
- **All unit suites once** (`YANTRA_TEST_RUN=s074c1 tooling/run-tests.bat`): backend 3865 passed, frontend
  346 passed, tooling 185 passed.
- **Build:** `npx vite build` in `frontend/`: built (the usual chunk-size warning only).
- **Browser, the new test alone** (`E2E_LANES=1`, `phone-chromium`, `-g S074`): 1 passed.
- **Browser, targeted** (`e2e/notifications.spec.js e2e/settings.spec.js e2e/screens.spec.js`, Normal: the
  screens and API this step changed, plus `screens.spec.js`): 35 passed, 4 skipped (the existing WebKit and
  Home Screen skips).
- **Browser, the whole suite at Normal** (`tooling/run-e2e-tests.bat`, once): 290 passed, 13 skipped
  (the existing skips), all six lanes exit 0, 179 s.

## Manual checks

- [auto] *What you will get*: the technician's exact list gains the countermeasure line; the engineer's card
  contains "Improvements ready to verify at SMTW" — `frontend/e2e/notifications.spec.js`::"S021 A1: What you
  will get — the engineer's breakdowns and defects, the technician's assigned jobs"
- [auto] The operator now sees the bell's dot — `frontend/e2e/notifications.spec.js`::"S021: the dot shows to
  people who would get alerts on a device that is off — not to IT admin or a storekeeper"
- [auto] Settings › Background tasks shows "Send the morning alerts: overdue countermeasures and improvements
  ready to verify — daily at 08:00" — `frontend/e2e/settings.spec.js`::"S074: Background tasks lists the
  improvement alerts at 08:00"

On a real device (rows 53 and 54 of `docs/steps/device-checks.md`):

- [ ] **Important.** The engineer gives a countermeasure to the technician; the technician's phone (charging
  or on Wi-Fi) shows *Countermeasure for you · SMTW.MCC2 · …* without sound, and a tap opens the improvement
  page (row 53).
- The engineer adds a countermeasure owned by the technician with a past due date; after 08:00 the next day
  both phones show *Countermeasure overdue · …*, and on the technician's phone it replaces the earlier alert
  (row 54).

## Docs updated

- `docs/schema.md` — the "migration v40" line; `improvements.ready_alert_for` and
  `improvement_actions.overdue_alert_for` in the two table rows. No Mermaid change (no new relation).
- `docs/schema.html` — the meta line (migration v40); the two columns in the Tickets tab, the only tab that
  lists these tables' columns (the Overview shows keyed columns only).
- `docs/Plan.MD` § 4.7 — three rows (*Countermeasure for you*, *Countermeasure overdue*, *Ready to verify*,
  push, with their recipients) and a bullet on the improvement alerts.
- `docs/steps/device-checks.md` — rows 53 and 54.
- `.claude/CLAUDE.md` — not edited, by the orchestrator's rule: the text is below.

## Proposed CLAUDE.md changes

1. In § Yantra Specifics, at the end of the **Notifications (S021)** bullet, add:

   > **Improvement alerts (S074)**: three push-only kinds per record beside the ticket kinds (`alerts_core.IMPROVEMENT_KINDS`: *Countermeasure for you* on a countermeasure add or change of owner, queued by `improvements.py`; *Countermeasure overdue* to the owner and the lead; *Ready to verify* to the site's holders of `improvement:verify`), quiet, TTL 24 hours (`push_core.IMPROVEMENT_TTL_SECONDS`), sent only to people who may open the improvement (`alerts.people_at_unit` with `access_core.roles_holding`, over the improvement's unit and its machine's current unit). The daily task `improvement_alert_scan` (08:00 IST, `scheduled_tasks.SCHEDULE`) queues the last two once per due date and once per watch end through the markers `improvement_actions.overdue_alert_for` and `improvements.ready_alert_for` (v40, `!=`, written even when push is off). The ticket and improvement alerts share `CHANNELS`, `task_handlers._push_to_people` and `alerts.people_at_unit`; PM (R03.7) adds its kinds on them.

2. In § SMTW-Review, a new point after **Meter readings (S039)**:

   > - **Improvement alerts (S074)**: the daily scan sends *overdue* once per due date and *ready to verify* once per watch end, through `overdue_alert_for` and `ready_alert_for`; a path that writes them takes (6b) then (6c), and an alert goes only to people who can open the improvement.

3. In § SMTW-Review, **Browser tests**, the spec-to-step map: `notifications` S021 → `notifications` S021/S074, and `settings` S064 → `settings` S064/S074.

## Feedback

- hindrance: the brief's line numbers (`improvements.py:19`, `improvements_core.py:26/:91/:433`) had moved
  because S069–S072 landed after it, so every citation had to be checked by name (stale check, about 10 min).
  A brief written ahead of its dependencies could cite names only, with `file:line` added at coding time.
- idea: the daily scan reads the whole kept test database, so a shell test of any scan-like task must run one
  scan first or assert only on its own rows (`test_improvement_alerts.py`). A shared fixture ("drain the
  scan") would help the next scheduled task (R03.7's PM scan).
- none other.

## Fix rounds

### Round 1

- **CR1-01 (minor) — Fixed.**
  - `test_worker.py::test_retaken_after_a_dropped_connection` patches `worker_module.SCHEDULE` to `[]`, so no daily task becomes due in it, whatever the hour.
  - New autouse fixture `no_real_push` in `backend/tests/conftest.py` wraps `push_sender.webpush`: it raises unless the endpoint host is `127.0.0.1`. Tests that fake `webpush` or `send` override it as before (the redirect test of `test_alerts.py` posts to a local server and still passes).
  - Red run: not done for the test patch, because without the patch the test fails only when the run is after 08:00 IST with an overdue candidate (time dependent). The guard was not shown red by a separate test; it is the line `raise AssertionError(...)`. Both are covered by the whole backend suite, green.
- **CR1-02 (nit) — Fixed.** One `marks(values)` in `backend/db_helpers.py`; `alerts._marks`, `improvements._in` and `meters._marks` are removed and import it (no cycle: `db_helpers` imports only config and `local_db`).
- **CR1-03 (nit) — Fixed.** The "not sent" line in `task_handlers.improvement_alert` now logs the improvement state, the countermeasure state, owner, due date, the watch end and the payload's expected values.
- **CR1-04 (nit) — Fixed.** `settings.spec.js` finds each task by its text inside the Background tasks card (`getByText`), with no Bootstrap classes.

Tests: whole backend suite `YANTRA_TEST_RUN=s074f1`: 3865 passed (169 s). `tooling/run-e2e-tests.bat e2e/settings.spec.js`: 5 passed. Frontend unit suites untouched.

Docs updated: none, because no behaviour, schema or setting changed.

Feedback (round 1):
- none
