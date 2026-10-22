```
Step: S019 — Deferred work
Doc: impl-report
Author: Coder (Opus)
Date: 22-10-2026
```

# S019 — Implementation report

**Result: the brief is built as approved (Q1 option b, staleness check s1), and every suite is green.**
- Backend: 1915 passed.
- Frontend: 12 files, 103 unit tests passed; `vite build` passed with no new warnings.
- Dependency-audit tests: 42 passed. Tooling tests: 20 passed.
- Browser suite: 162 passed in 6.0 min (54 tests × 3 projects: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium); 0 failed, 0 skipped.

The code sits on top of S025's uncommitted code. The user commits S025, S019 and S020 together. Two places depart from the brief's wording; neither changes a rule (§ 4, decisions 6 and 9). No question is open for the user.

## Questions for the user

None.

## 1. What was built

1. **The scheduled state.** A ticket can wait between acknowledged and in progress, with a **planned date** and a **waiting reason**. On a defect the badge reads *Scheduled*; on a breakdown it reads *Waiting*; past the planned date it reads *Overdue* (red).
2. **Two new moves.**
   - **Schedule** from raised or acknowledged (`ticket:assign`: engineer and up) and from in progress (`ticket:work`: technician and up, U1). The page shows one *Schedule* button; only who may press it depends on the state.
   - **Change plan** from scheduled (`ticket:assign`), with a required remark. It must change the date or the reason ("Nothing to change").
   - Start, Back in service, Not a fault and Change severity now also start from scheduled.
3. **The planned date rules.** Today (IST) or later, at most 365 days ahead. The event's time plays no part. An overdue plan needs a new date, even when only the reason changes.
4. **Six waiting reasons**, each tied to EN 13306's logistic or administrative delay: parts, vendor, expert (logistic); slot, approval (administrative); other (neither; the remark is then required).
5. **"Is / Was the machine stopped for this work?"** on Start from scheduled on a defect, and on Back in service from scheduled on a defect when a start time is given. The answer is stored on the *started* event.
6. **New figures on the times card.**
   - *of which waiting*: the time a breakdown spent scheduled, per reason, with the logistic and administrative totals.
   - *Planned stop*: the time from a start marked "machine stopped" to back in service (or to a schedule, or to a change to critical).
   - Response now also counts the first *scheduled* event.
   - Times of 24 h or more read in days ("2 d 20 h", "3 d").
7. **The list.**
   - New filters *Scheduled* and *Overdue*, ordered by planned date.
   - In *Open*, scheduled rows come after the actionable ones of the same intensity.
   - A scheduled row shows its plan. An overdue row shows a red "Overdue since 25-10" badge.
8. **The timeline.** "Scheduled — for 25-10-2026 · waiting for parts", and "Plan changed — for 02-11-2026 · … (was 25-10-2026 · …)". A start from scheduled shows "Machine stopped for this work" or "Machine kept running".
9. **Migration v21.** It adds the plan columns to `tickets` and `ticket_events`, `machine_stopped` to `ticket_events`, appends `'scheduled'` to the state ENUM, and adds the CHECK `chk_tickets_plan`.

## 2. How it works

**One Schedule move with two keys.**
- `tickets_core.Move` gained a field `state_keys`: pairs of (state, key) that override the move's `key` from those states.
- `Move.key_at(state)` returns the key for one state. `Move.keys` returns every key the move can take.
- `MOVES["schedule"]` is `ASSIGN_KEY`, with `state_keys=((IN_PROGRESS, WORK_KEY),)`.
- `allowed_moves` checks `move.key_at(state)`, so the page sees one move named `schedule`.
- `make_move` refuses early (403) only when the user holds none of `spec.keys` anywhere. It then locks the ticket and checks `spec.key_at(<locked state>)` at the ticket's site. `_lock_ticket` accepts either a key or a function of the locked state for this.
- A technician on an acknowledged ticket therefore gets 403, and on an in-progress ticket gets 200.

**The plan on the ticket, the history on the events.**
- `_schedule` checks `planned_date_error(planned, now.date())` and returns the plan for both the event and the ticket.
- `_reschedule` runs the same date check first, then compares the plan with the **locked** row's plan (`_LOCK_TICKET` now selects `planned_date` and `waiting_reason`). An identical plan is a 400 "Nothing to change".
- `_apply_move` clears the two plan columns in one place, whenever the ticket leaves scheduled. The CHECK `chk_tickets_plan` guards the rule in the database and never fires in normal use.
- `_start` (new step) and `_restore` write the stopped answer on the *started* event. `_machine_stopped` asks for it only when `machine_stopped_needed(state, intensity)` is true. A value sent on a critical ticket is ignored.
- Body rules (date format, reason code, *Other* needs a remark) are in `validate_move`: a 400 before the transaction. `_optional_date` now parses both the planned date and the labour work date.

**The figures (`ticket_times`).**
- It walks the ordered events once.
- Each event closes the stretch since the previous one. The stretch counts by the state, intensity and reason that held during it:
  - in progress → repair, and planned stop when the start was marked "machine stopped";
  - critical in raised, acknowledged, scheduled or in progress → downtime;
  - critical in scheduled → waiting, under the reason in force.
- The last stretch runs to `now` on an open ticket.
- A back in service without in progress right before it makes repair unknown, as in S018. This now also covers a restore straight from scheduled (BR2-07).
- `waiting_minutes` and `waiting_by_reason` are both null when the ticket was never critical while scheduled. `planned_downtime_minutes` is null when no start was marked "machine stopped".
- All S018 cases give the same figures as before (their tests are unchanged).

**The list.** `state=scheduled` and `state=overdue` filter `t.state = 'scheduled'` (and `t.planned_date < today` for overdue). They order by `t.planned_date, t.id`. *Open* orders by `t.intensity, t.state = 'scheduled', t.occurred_at, t.id`. Each item carries `planned_date`, `waiting_reason` and `overdue` (`is_overdue`).

**The page.**
- `MoveDialog` shows `ScheduleFields` (date and reason) for the two plan moves.
- *Change plan* opens prefilled, with the remark open and required.
- *Other* makes the remark required, with the label "What does it wait for?".
- The stopped question shows from `asks_machine_stopped`. On *Back in service* it shows only once a start time is filled.
- `asksStart` includes scheduled.
- `TicketDetailView` puts *Schedule* and *Change plan* in outline beside *Change severity*.

**The e2e seed.**
- `seed_e2e.py` raises a defect on `E2E MCC1 mill` ("E2E seed: overdue for parts") as admin and schedules it for today through the API.
- One SQL `UPDATE` then moves the plan to yesterday on the ticket and its *scheduled* event, in one statement.
- The connection uses `config.DB_CONFIG` with the database name from `e2e_backend.E2E_DATABASE`. `e2e_backend.check_target` runs before any SQL.

**Lock order.**
- S019 adds no explicit lock. The note in `tickets.py` now says, in CR1-02's terms, that a state change re-checks the unit, machine and component foreign keys with shared locks.
- It lists four accepted deadlocks: S025's two, plus CR1-02's two (a repeat raise against a send-back; a unit edit against any move in that unit, which includes schedule and the start from scheduled).
- *Change plan* keeps the state, so its index entries and foreign-key checks do not change.
- The note's § 5.2 wording is corrected: the two "cannot both succeed", but when they overlap they can deadlock.

## 3. Files touched

Files marked **(S025 too)** also hold S025's uncommitted changes. Only S019's lines are described here.

**Backend**
- `backend/tickets_core.py` **(S025 too)**: `SCHEDULED`, the two events, `WAITING_REASONS`, `PLANNED_DATE_MAX_DAYS`, `Move.state_keys` / `key_at` / `keys`, the `schedule` and `reschedule` moves, scheduled in start / restore / not-a-fault / `REGRADE_STATES` / `_DOWN_STATES`, `validate_move` for the new fields, `_optional_date` and `_optional_bool`, `planned_date_error`, `machine_stopped_needed`, `is_overdue`, `ticket_times` rewritten as one walk over stretches with the three new figures, `STATE_FILTERS` and `PLAN_FILTERS`.
- `backend/tickets.py` **(S025 too)**: the lock-order note; the plan columns read and returned (`_TICKET_COLUMNS`, `_LOCK_TICKET`, `_event_rows`, `_ticket_out`); `asks_machine_stopped` in `_moves`; the list filters and order; `_add_event` takes the new columns; the steps `_start`, `_schedule`, `_reschedule` and `_machine_stopped`; the stopped answer in `_restore`; plan clearing in `_apply_move`; the per-state key in `make_move` and `_lock_ticket`.
- `backend/local_db.py` **(S025 too)**: migration v21, with its comment on why it needs no `_PRECONDITIONS` entry.

**Backend tests**
- `backend/tests/test_tickets_core.py` **(S025 too)**: the assertions that change by design (`OPEN_STATES`, `test_state_by_keys`, `test_the_table`, and two whole-`clean` comparisons that now hold `machine_stopped`); new classes `TestWaitingReasons`, `TestValidatePlanMoves`, `TestPlannedDate`, `TestMachineStoppedNeeded`, `TestTicketTimesS019`.
- `backend/tests/test_ticket_work_api.py` **(S025 too)**: `test_moves_listed_per_user` and five whole-`times` comparisons (`NOT_SCHEDULED`); new classes `TestSchedule`, `TestChangePlan`, `TestLeavingScheduled`, `TestPlanList`.
- `backend/tests/test_migration_v12.py` **(S025 too)**: `'scheduled'` appended to the state ENUM in `test_tables_and_indexes`.
- `backend/tests/test_migration_v20.py` (S025's new file): `V20` pinned to version 20 alone; the assertions are unchanged.
- `backend/tests/test_migration_v21.py` (new): a v20 database with a ticket gets v21. The row is unchanged, and the columns, ENUM, default and CHECK are checked. The reason ENUM is checked equal to `WAITING_REASONS`. A re-run changes nothing.

**Frontend**
- `frontend/src/utils/ticketLabels.js`: the scheduled state and the two filters; the two event labels; `PLAN_MOVES` and the move labels; `minutesText` with days (and `days: false`); `WAITING_REASON_LABELS`, `WAITING_REASON_DELAYS`, `waitingText`, `stateLabel`, `planText`, `planLine`, `overdueBadge`, `planChanges`, `waitingSplit`, `machineStoppedQuestion`, `MACHINE_STOPPED_CHOICES`, `PLANNED_DATE_MAX_DAYS`.
- `frontend/tests/ticketLabels.test.js`: the exact `STATE_LABELS` keys; `minutesText` with days; an S019 block (the six codes and their delays, the badge, the lines, the filters, the timeline, the split, the question).
- `frontend/src/views/tickets/ScheduleFields.vue` (new): the date input (today to a year ahead) and the reason select.
- `frontend/src/views/tickets/MoveDialog.vue`: the plan moves, the per-move remark labels and rules, the stopped question, `asksStart` with scheduled, and the new fields in `SHOWN_FIELDS`.
- `frontend/src/views/TicketDetailView.vue`: the badge (`state-badge`, red when overdue), the plan line, the plan buttons, the times-card lines, the timeline plan and stopped lines.
- `frontend/src/views/TicketsView.vue`: the plan on each row, the overdue badge, the filters (from `STATE_FILTERS`).
- `frontend/src/views/tickets/LabourPanel.vue`: labour stays in hours (`minutesText(…, { days: false })`).

**Browser tests and seed**
- `frontend/e2e/tickets-work.spec.js` **(S025 too)**: five S019 tests.
- `frontend/e2e/support/tickets.js` **(S025 too)**: `stateBadge` selects `.state-badge`; new `istDay` and `shownDay`.
- `tooling/e2e/seed_e2e.py`: the overdue ticket (`e2e_connection`, `seed_overdue_ticket`).

**Docs**
- `docs/steps/device-checks.md` **(S025 too)**: row 9 now says "the latest schema version" (BS1-06); new row 10 (S019).
- `docs/steps/S025-audit-fixes/3-impl-report.md`: its real-device check now says "the latest schema version", as the brief directs (BS1-06). Nothing else in S025's report changed.
- `docs/steps/S019-deferred-work/1-brief.md`: Status only.
- `docs/steps/README.md` **(S025 too)**: the S019 index row only.
- `docs/steps/S019-deferred-work/3-impl-report.md` (new): this report.

**The joint release (BS1-06).** S025, S019 and S020 ship together. The first release applies v20, v21 and v22 in one `init_db`: the preconditions of all pending versions are checked first (only v20 has one), then each version runs in order.

## 4. Decisions taken

1. **How `MOVES` holds a key that depends on the from-state** (the brief asked me to state it). I used one `schedule` entry with a `state_keys` override, not a second entry. The page then gets one move name with no de-duplication, and the route `/moves/schedule` maps to one entry. The brief's "one more entry" is met in effect: the table carries a second (state, key) row for Schedule. The early 403 in `make_move` uses `Move.keys` ("holds none of the move's keys anywhere"). The key that counts is decided from the locked state.
2. **`_lock_ticket(cur, id, key)` accepts a function of the locked state** as well as a key string. The alternative was a near-copy of the lock function for moves only.
3. **Change plan requires both `planned_date` and `waiting_reason` in the body.** The dialog always sends both (it opens prefilled). The server then compares a full plan with the locked row's plan.
4. **"Nothing to change" has no field** (a top-of-dialog message). It is about the whole plan, not one field. The e2e test reads it with `expectFieldMessage(dialog, …)`, as the brief says; that helper finds the text anywhere in the dialog.
5. **A bad date format reads "Enter the date as YYYY-MM-DD"**, the message labour already uses. The date input always sends that format, so only an API client sees it.
6. **The timeline wording** follows BR2-08 ("Plan changed" with "for <new> (was <old>)"). § 1.3 and the e2e line in § 8 show an older "old → new" form. The e2e test checks BR2-08's form, since BR2-08 is the later decision. *Departure from the § 8 wording only; the rule is BR2-08's.*
7. **The list row** reads "SMTW.MCC1 · Overdue · for 21-10-2026 · waiting for parts", with the red "Overdue since 21-10" badge on the top line. In a sentence, *Other* reads "other reason", not "other (remark required)".
8. **The times card shows the logistic and administrative totals** under the per-reason lines (only the kinds that were met). The brief says the totals are summed "where they are shown". Showing them names the EN 13306 split on the screen for the owner to learn from. They take two short lines.
9. **Labour stays in hours.** `minutesText` gained days from 24 h on (BR2-03). The labour panel also uses it, and labour is man-hours (ISO 14224), so a 26 h labour total stays "26 h", not "1 d 2 h". I added `{ days: false }` for the labour panel. *The brief did not mention the labour panel; this keeps its display unchanged.*
10. **The timeline shows the stopped answer** ("Machine stopped for this work" / "Machine kept running") under a *Work started* line that has one. The brief does not list this line. It shows a recorded fact, which the e2e test also uses. This is a small addition the user would see.
11. **The stopped question's choices** read "Yes, machine stopped" and "No, machine running", the same for both tenses. Only the legend changes tense (BR1-14).
12. **The state badge has the class `state-badge`**, because it turns red (`text-bg-danger`) when overdue. The e2e helper `stateBadge` now uses that class. The S018 and S025 tests that use it pass unchanged.
13. **v21 puts the new columns after `state` (tickets) and after `remark` (ticket_events)**, for readability. MariaDB adds them in place.
14. **The seed sets `FLASK_DEBUG=1` before importing `config`**, as `e2e_backend.py` does. There is no `secrets_app.py` in dev, and `config` falls back to the example secrets only in dev or test. It reads today's IST date with `SELECT CURDATE()` on the session's +05:30 time zone. The seed's single `UPDATE` is a two-table update (ticket and its *scheduled* event).
15. **`test_migration_v21.py` imports `_recreate`, `_migrate`, `_run` and `_schema` from `test_migration_v20.py`** rather than moving them into a new module (the brief allows either).

## 5. Not done, deferred, assumed

- **The docs of § 3 "at approval, by the planner"** (Plan.MD § 4.2 and § 5, Maintenance-Philosophy § 7 and § 10) are the planner's. I did not change them.
- **No SMTW-Review point** was added to `.claude/CLAUDE.md`; the brief proposes none.
- **The dev database** `vel_yantra_master` gets v21 the next time the dev backend starts. The test and e2e databases got it in these runs.
- **Assumption:** InnoDB rewrites the `*_state` index entries only when `state` changes, so *Change plan* (scheduled → scheduled) takes no foreign-key locks. This is said in the lock-order note. No test depends on it.
- **The e2e Overdue test** expects yesterday's date in IST. A run that crosses IST midnight between the seed and that test would fail once. This is the same exposure as the other date-based tests.

## 6. Tests

**Results** (real runs, 22-10-2026):

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` (exit 0) | backend 1915 passed; frontend 12 files, 103 tests passed; deps 42 passed; tooling 20 passed |
| `npx vite build` | built, no new warnings |
| `tooling/run-e2e-tests.bat` (exit 0) | 162 passed in 6.0 min (54 tests × 3 projects); 0 failed, 0 skipped; the five S019 tests pass in all three projects |

## Fix rounds

### Round 1

- **CR1-01 — Fixed.** `backend/tickets.py`: `make_move` passes a key function that gives `spec.key_at(state)` only when the locked state is a from-state of the move, and otherwise the set `spec.keys`. `_lock_ticket` accepts a key, a function, or a set of keys (any one held at the site is enough, else 403 on the first). A stale Schedule then reaches `_apply_move` and gets 409 "This ticket changed — reload". Test: `test_ticket_work_api.py::test_a_stale_schedule_by_a_technician_is_409_not_403`.
- **CR1-02 — Fixed.** `backend/tickets_core.py` `validate_move`: `waiting_reason` must be a string before the membership test; a list or object gives 400 on `waiting_reason`, "Choose why it waits". Tests: `test_tickets_core.py::TestValidatePlanMoves::test_a_list_or_object_reason` and `test_ticket_work_api.py::test_a_list_or_object_reason_is_400` (two cases each).
- **Files:** `backend/tickets.py`, `backend/tickets_core.py`, `backend/tests/test_ticket_work_api.py`, `backend/tests/test_tickets_core.py`, this report.
- Tests after the round: `tooling/run-tests.bat` exit 0 (backend 2003 passed, frontend 13 files / 110 tests, deps 42, tooling 22); `tooling/run-e2e-tests.bat e2e/tickets-parts.spec.js e2e/tickets-work.spec.js`: 66 passed (22 tests x 3 projects), 0 failed.
- Not touched: CR1-03 to CR1-05 (nits; not asked).

## Manual checks

**Automated** (passing run of 22-10-2026, all three projects):
- [auto] An engineer schedules a defect for a date and reason: the badge reads *Scheduled*, the line under the header "for <date> · <reason>", and the timeline shows the line — `frontend/e2e/tickets-work.spec.js`::`S019: engineer schedules a defect for a date and reason, then changes the plan with a remark`
- [auto] *Change plan* with a remark: the timeline shows "Plan changed" with the new plan and "(was …)" (decision 6) — `frontend/e2e/tickets-work.spec.js`::`S019: engineer schedules a defect for a date and reason, then changes the plan with a remark`
- [auto] A technician starts the scheduled defect and answers *Yes, machine stopped*, then back in service: the times card shows *Planned stop* — `frontend/e2e/tickets-work.spec.js`::`S019: technician starts a scheduled defect with the machine stopped; the times card shows the planned stop`
- [auto] A breakdown in progress is scheduled for parts: the badge reads *Waiting* with "for <date> · waiting for parts"; after start and back in service the times card shows the waiting per reason — `frontend/e2e/tickets-work.spec.js`::`S019: technician schedules a breakdown in progress for parts; the times card splits the waiting`
- [auto] The list's *Overdue* filter shows a ticket planned in the past (seeded on `E2E MCC1 mill`), with the red badge, as the engineer — `frontend/e2e/tickets-work.spec.js`::`S019: the Overdue filter shows a ticket planned in the past, with the red badge`
- [auto] The Schedule dialog, the *Change plan* dialog and the *Start* dialog with its Yes / No fit a phone (`expectDialogFits`, through `openAction`) on Pixel 7 and iPhone 14 — the three S019 flow tests above
- [auto] *Change plan* opens with the current date and reason; saving it unchanged shows "Nothing to change" — `frontend/e2e/tickets-work.spec.js`::`S019: engineer schedules a defect for a date and reason, then changes the plan with a remark`
- [auto] Choosing *Other* opens the remark as required — `frontend/e2e/tickets-work.spec.js`::`S019: engineer schedules a defect for a date and reason, then changes the plan with a remark`
- [auto] A technician sees no *Schedule* button on an acknowledged ticket — `frontend/e2e/tickets-work.spec.js`::`S019: a technician gets no Schedule button on an acknowledged ticket`; and sees it on a ticket in progress — `frontend/e2e/tickets-work.spec.js`::`S019: technician schedules a breakdown in progress for parts; the times card splits the waiting`

**On a real device** (row 10 of `docs/steps/device-checks.md`):
- [ ] **Important.** On a phone (Android and iPhone), as an engineer: the date field of the Schedule dialog opens the phone's own date picker, and after Save the page shows the chosen date as DD-MM-YYYY. Account: an engineer at SMTW; network: either; where: the dev server on KLA's laptop or production on the TEST machine.
