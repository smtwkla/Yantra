```
Step: S028 — Back-dating window: admin and backlog entry
Doc: impl-report
Author: Coder (Sonnet)
Date: 22-10-2026
```

# S028 — Implementation report

## 1. What was built

- One rule for the oldest time a user may enter. Admin: 3 years (1095 days), always. Everyone else: 3 years until 30-11-2026 (IST date of entry, inclusive), 7 days from 01-12-2026.
- The rule covers every entered ticket time (the raise's *When did it happen?*, every move, regrade, and the raise's *Already fixed* times).
- The refusal names the limit that applies: `When did it happen? Up to 7 days back` or `When did it happen? Up to 3 years back`.
- Admin holds the new global key `ticket:backdate` through the admin bypass. No role holds it.
- Q1 (b): a muted hint `That was N days ago` under each time field, shown from 8 days back, for every user.
- Q2 (b): a raise whose entered time is more than 7 days before now queues no alert and no escalation.

## 2. How it works

- `tickets_core.backdate_days(now, may_backdate)` returns 1095 for a key holder, or for anyone while `now.date() <= BACKLOG_UNTIL`; else 7. `BACKLOG_UNTIL` is read at call time, so tests move it with `monkeypatch`.
- `event_time_error`, `validate_raise` and `validate_event_time` take a required `max_back_days`. The message comes from `too_old_message(max_back_days)`.
- `tickets._max_back_days(now)` asks `has_perm("ticket:backdate")`. `raise_ticket` computes it once; `_event_time` computes it per call (cached memberships, none for admin).
- `alerts_core.raise_alert(intensity, age)` returns `None` when `age > 7 days`. `raise_ticket` passes `now - clean["occurred_at"]`. Exactly 7 days still alerts.
- `daysAgoHint(entered, now)` in `ticketLabels.js` is pure. `RaiseTicketView.vue`, `EventFields.vue` and `StartedAtFields.vue` show it as a `form-text` line under the field, from the phone's clock.

## 3. Files touched (17 code and test, plus this report and the brief status)

Backend:
- `backend/tickets_core.py`: constants, `backdate_days`, `too_old_message`, new argument on the three validators.
- `backend/tickets.py`: `BACKDATE_KEY`, `_max_back_days`, passed in `raise_ticket` and `_event_time`; age passed to `raise_alert`.
- `backend/config_rbac.py`: `"ticket:backdate": ()` with comment.
- `backend/alerts_core.py`: `raise_alert(intensity, age)`.
- `backend/tests/conftest.py`: `keycloak_admin` fixture.
- `backend/tests/test_tickets_core.py`: existing calls get the argument; 1095/1096 case; `TestBackdateWindow`.
- `backend/tests/test_tickets_api.py`: `test_event_time_out_of_the_window_is_400` patched; new `TestBackdateWindow` (8 cases, one parametrized twice).
- `backend/tests/test_rbac.py`: key held by admin only, not in `SITE_SCOPED`.
- `backend/tests/test_alerts_core.py`: age cases.

Frontend:
- `frontend/src/utils/ticketLabels.js`: `MAX_BACKDATE_DAYS`, `daysAgoHint`.
- `frontend/tests/ticketLabels.test.js`: `daysAgoHint` cases.
- `frontend/src/views/RaiseTicketView.vue`, `frontend/src/views/tickets/EventFields.vue`, `frontend/src/views/tickets/StartedAtFields.vue`: the hint.
- `frontend/e2e/tickets-raise.spec.js`: the admin test.

Docs: `docs/steps/S028-backdating-window/1-brief.md` (Status set to *In code review*). Plan.MD, Maintenance-Philosophy.md and the README index row were not edited, as instructed. The index row still reads *Approved*; the orchestrator should update it.

## 4. Decisions taken

- The raise's *Already fixed* time uses `EventFields.vue`, so the hint there needs no separate code in `RaiseTicketView.vue`; that file shows it only under *When did it happen?*.
- `EventFields.vue` shows the hint only while the user has opened *Change* (`changing`). While it reads *Now*, there is no entered time.
- `StartedAtFields.vue` shows the hint only when both the date and the time are filled, as the parent sends `started_at` only then.
- API tests for *Already fixed* use a real engineer person at the unit's site (`user_at_sites`), because the restore person must belong to the ticket's site.
- No departure from the brief.

## 5. Not done, deferred, assumed

- Nothing deferred. A1 and A2 as in the brief.
- `README.md` index row not changed (instruction).
- Real-device checks: none, so no rows added to `docs/steps/device-checks.md`.

## 6. Tests

- Targeted while coding: `YANTRA_TEST_RUN=s028c1` on `test_tickets_core.py`, `test_alerts_core.py`, `test_rbac.py`, `test_tickets_api.py`.
- Final full run, `tooling/run-tests.bat` (`YANTRA_TEST_RUN=s028c1`): backend 2298 passed, frontend 117 passed, deps 42 passed, tooling 91 passed; all suites PASSED.
- `npx vite build` in `frontend/`: built.
- e2e, `tooling/run-e2e-tests.bat e2e/tickets-raise.spec.js e2e/screens.spec.js`: 54 passed (3 projects). Targeted because the step changed the raise screen and its two shared ticket components, and no shared frontend code (`api.js`, router, auth store, `FormModal`, `e2e/support/`); `screens.spec.js` covers every route.

## Manual checks

- [auto] Admin raises a ticket 30 days back; the timeline's first line shows that time — `frontend/e2e/tickets-raise.spec.js::S028: admin raises a ticket 30 days back; the timeline shows that time and the hint says how far`
- [auto] After filling 30 days back, `That was 30 days ago` shows under the field — same test.
- No real-device checks.
