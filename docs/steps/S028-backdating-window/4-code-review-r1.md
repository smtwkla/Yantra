```
Step: S028 — Back-dating window: admin and backlog entry
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S028 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the
approved brief asks for, all suites are green, and the targeted e2e run passes.
This round has 5 nits and nothing else.

## Test results (run by the reviewer)

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s028cr1 tooling/run-tests.bat` | ALL SUITES PASSED: backend 2298, frontend 117, deps 42, tooling 91 |
| `npx vite build` in `frontend/` | built, no new warnings |
| `tooling/run-e2e-tests.bat e2e/tickets-raise.spec.js e2e/screens.spec.js` | 54 passed (3 projects, 6 lanes, 100 s) |

**Why these e2e specs.** The step changes the raise screen and two shared
ticket components (`EventFields.vue`, `StartedAtFields.vue`). It changes no
shared frontend code (`FormModal.vue`, `useFormModal.js`, `api.js`, the router,
the auth store, `e2e/support/`), so the full suite is not needed.
`tickets-raise.spec.js` holds the step's e2e test. `screens.spec.js` opens
every route. The two components are also used by the move dialogs in
`tickets-work.spec.js`. Their change there is one `form-text` line that shows
only after 8 days back, so a run of that spec is not required.

## Findings

No `blocker`, `major` or `minor` findings.

## Nits

- **CR1-01** (nit) `backend/tickets_core.py:50-51`: the comment above
  `FUTURE_SKEW` still says older history "is out of scope". Add that S028 lifts
  the limit for admin and for the backlog window until `BACKLOG_UNTIL`.
- **CR1-02** (nit) `backend/tests/test_tickets_api.py:264`:
  `test_a_raise_for_history_queues_no_alert` does not patch `BACKLOG_UNTIL` to
  the past, as brief § 7 *Alerts* asks. The result is the same because the test
  uses `keycloak_admin`. Add the patch so that the test matches the brief.
- **CR1-03** (nit) `frontend/src/views/RaiseTicketView.vue:457`: the template
  calls `daysAgoHint(form.occurredAt, new Date())` twice, in `v-if` and in the
  body. Use one `computed`, as `StartedAtFields.vue` does.
- **CR1-04** (nit) `backend/tickets_core.py:76`: the new refusal
  `When did it happen? Up to 3 years back` follows the brief's text. It does not
  say what to do (scope B), and it also shows under move times such as *Back in
  service*, where "When did it happen?" does not fit. The 7-day text has the
  same fault since S017. A later tidy-up could use one form for both, for
  example `Enter a time up to 3 years back`.
- **CR1-05** (nit) `docs/steps/S028-backdating-window/3-impl-report.md:27`:
  the heading says "17 code and test" files, but the list names 15 (9 backend,
  6 frontend). Correct the count.

## Checked and found consistent

- **Rule (§ 1, § 4.1).** `backdate_days` returns 1095 for a key holder, and for
  everyone while `now.date() <= BACKLOG_UNTIL` (2026-11-30, inclusive).
  Otherwise it returns 7. `now` is the IST server clock (`tickets._now`).
  `BACKLOG_UNTIL` is read at call time, so tests can move it.
- **Every entered time (U1, D5).** The only callers are `raise_ticket`
  (`validate_raise`) and `_event_time` (`validate_event_time`). `_event_time`
  serves start, every move, regrade, the *Already fixed* block and its
  `started_at`. `max_back_days` is a required argument everywhere, so no caller
  can fall back to 7 days without passing it.
- **Boundaries.** Exactly 7 or 1095 days back is accepted (`<`), and 1096 days
  is refused with the 3-year message. 30-11 23:59 is inside the window and
  01-12 00:00 is outside; unit tests cover both. `too_old_message` asserts that
  the limit is 7 or 1095, as § 4.1 says.
- **RBAC (§ 4.3, D1, D2).** `ticket:backdate` is `()`, not in `SITE_SCOPED`, and
  never named as a role in route code. `has_perm` gives it to admin through the
  bypass. `it_admin` does not hold it: the token role's permissions lack it, and
  the IT-admin API test is refused at 8 days after the window. A request with no
  identity gets `False`. No actor is taken from the client.
- **No alerts for history (§ 4.6).** `raise_alert(intensity, age)` returns
  `None` when `age > 7 days`. Exactly 7 days still alerts. `age` is 0 when no
  time was entered. *Already fixed* still sends nothing, because that branch
  never calls `raise_alert`. Regrade, send-back and assignment alerts are
  unchanged. The API test checks that no `ticket_alert` or `ticket_escalate`
  row is written for 30 days back, and that both rows are written for 1 day
  back.
- **Pure core and thin shell.** The rule and the alert decision live in
  `tickets_core` and `alerts_core`, with no clock and no DB. The shell only asks
  `has_perm` and passes `now`. The frontend hint is display only, and the
  server decides.
- **DB unavailable.** `_max_back_days` runs after `require_perm`, which has
  already loaded the memberships into `g`, so it adds no query. With the DB
  down, the request gives a 503 as before.
- **Hint (§ 4.5).** `daysAgoHint` is pure and shows only from 8 whole days back.
  It gives `""` for an empty, unparsable or future value. It appears under
  *When did it happen?*, under the move time once *Change* is open, and under
  *Started* once both its date and time are filled; the impl report lists these
  conditions in "Decisions taken". Playwright runs at `Asia/Kolkata`, so the
  e2e hint check does not depend on the machine's time zone.
- **Tests against § 7.** The unit, API, RBAC, alert and vitest cases in the
  brief are all present. The existing tests got the new argument, and
  `test_event_time_out_of_the_window_is_400` now patches the window and stands
  as the IT-admin case. The e2e test asserts what the user sees: the hint text
  and the timeline time. It runs as admin, so it holds after 30-11-2026. The
  raise screen is a page, not a dialog, so `expectDialogFits` does not apply.
- **Scope.** Nothing is built beyond the brief. There is no migration and no API
  shape change. The departures the coder took are in "Decisions taken", and
  none changes the brief.
- **Docs (§ 9).** The Plan.MD § 2, § 3 and § 4.2 texts and the
  Maintenance-Philosophy § 1 text match the brief. The README index row reads
  *In code review*.
- **Manual checks.** The impl report's `## Manual checks` lists both important
  checks as `[auto]` with the test name. My run confirms that the test passes.
  The brief has no real-device check, and `device-checks.md` correctly has no
  new row.
- **Track.** Full track, as the RBAC key requires.

## Manual browser check for the user

None required. If you want to look yourself, check these on a phone:

- In a move dialog, tap *Change* and pick a date 30 days back. The muted line
  "That was 30 days ago" shows under the time.
- On the raise screen, tick *Already fixed* and fill a start date and time more
  than 7 days back. The same line shows under *Started*.
