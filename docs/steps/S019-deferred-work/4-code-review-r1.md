```
Step: S019 — Deferred work
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 22-10-2026
```

# S019 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 `minor` findings and 3 `nit`s.
The step builds what the approved brief asks for (Q1 option b, staleness check s1), and every
suite is green in my own runs.

Reviewed: the working-tree diff against `3df667c`, S019's part only. S025's uncommitted code
was reviewed in `S025-audit-fixes/4-code-review-r1.md`. In the shared files (`tickets_core.py`,
`tickets.py`, `local_db.py`, the ticket tests, `tickets-work.spec.js`, `support/tickets.js`,
`device-checks.md`, `README.md`), I separated S019's lines with the S025 report and review.
`RegradeDialog.vue`, the S025 e2e tests, `regradeByApi` and `causeId` are S025's.

## Test results (my runs, 22-10-2026)

| Suite | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0 — backend 1915 passed; frontend 12 files, 103 tests passed; deps 42 passed; tooling 20 passed |
| `npx vite build` (frontend) | built, no new warnings |
| `tooling/run-e2e-tests.bat` | exit 0 — 162 passed in 6.0 min (54 tests × 3 projects); 0 failed, 0 skipped; the five S019 tests pass on Pixel 7 Chromium, iPhone 14 WebKit and desktop Chromium |

## Findings

### CR1-01 — `minor` — A stale *Schedule* gets 403 "You can't do this at SMTW" instead of 409 "This ticket changed — reload"

`backend/tickets_core.py:349-351`, `backend/tickets.py:397`, `backend/tickets.py:908`

- **Problem.** `make_move` passes `spec.key_at` to `_lock_ticket`. The key is checked from the
  locked state **before** `_apply_move` checks the from-state. For a state outside
  `schedule`'s from-states, `key_at` returns the default key, `ticket:assign`. A technician
  then fails the key check, and gets 403 instead of the 409 that brief § 5.6 promises for a
  stale page. `MoveDialog` reloads the page only on a 409 (`MoveDialog.vue:89-91`).
- **Failure scenario.** Two technicians work on a stopped press in progress. Kannan presses
  *Back in service*. Ravi's page still shows *In progress*; he presses *Schedule* (waiting for
  parts) and saves. The dialog shows "You can't do this at SMTW" at the top, and the page
  does not reload. Ravi thinks that he lost his rights. The same happens when an engineer has
  just scheduled the ticket. Before S019, every move had one key, so a stale page always got
  the 409.
- **Fix.** Check the per-state key only when the locked state is a from-state of the move.
  Outside the from-states, check only that the user holds one of `spec.keys` at the site,
  and let `_apply_move` answer 409. One way: `key_at(state)` returns `None` outside
  `from_states`, and `_lock_ticket` then checks `any(has_perm_at(k, site) for k in
  spec.keys)`. Add an API test: a technician schedules a ticket that is back in service and
  gets `(409, None, "This ticket changed — reload")`.

### CR1-02 — `minor` — A list or an object as `waiting_reason` answers 500

`backend/tickets_core.py:507-511`

- **Problem.** `reason in WAITING_REASONS` tests membership in a dict. For an unhashable
  value it raises `TypeError` (checked: `['parts']` and `{'a': 1}` both raise "unhashable
  type"). The route turns that into a 500 "Something went wrong — try again" with a
  traceback in the log. The other enum checks test a tuple (`intensity in INTENSITIES`), so
  they do not have this problem.
- **Failure scenario.** An API client or a fuzzing scan sends
  `{"planned_date": "2026-11-01", "waiting_reason": ["parts"]}` to `/moves/schedule`. It
  gets a 500 and a logged traceback, instead of 400 on `waiting_reason`, "Choose why it
  waits". The screen always sends a string, so the floor never sees this.
- **Fix.** `if reason is None or (isinstance(reason, str) and reason in WAITING_REASONS)`.
  Add the two cases to `TestValidatePlanMoves.test_an_unknown_reason`.

### CR1-03 — `nit` — Two wordings for one answer: "No, machine running" and "Machine kept running"

`frontend/src/utils/ticketLabels.js` (`MACHINE_STOPPED_CHOICES`),
`frontend/src/views/TicketDetailView.vue:381`

- **Problem.** The dialog's choices read "Yes, machine stopped" / "No, machine running". The
  timeline line reads "Machine stopped for this work" / "Machine kept running". CLAUDE-COMMON
  scope B asks for the same words for the same thing.
- **Fix.** Use one pair. For example, the timeline reads "Machine stopped for this work" /
  "Machine running during this work", or the choice reads "No, machine kept running".

### CR1-04 — `nit` — No test for the per-state key at the ticket's site

`backend/tests/test_ticket_work_api.py` (`TestSchedule`)

- **Problem.** The early 403 in `make_move` uses the union of keys (`has_perm`). The key that
  counts is checked at the ticket's site from the locked state. This path is new in S019, and
  no test covers a user whose keys differ per site.
- **Failure scenario.** A later change replaces `require_perm_at(key(locked["state"]), …)`
  with a check against the union. A person who is an engineer at another site and a
  technician here could then commit a production slot here. No test fails.
- **Fix.** Add one case. Give a user the technician role at the ticket's site and the
  engineer role at a second site. *Schedule* from acknowledged is then 403, and from in
  progress it is 200.

### CR1-05 — `nit` — An overdue row says "Overdue" twice

`frontend/src/views/TicketsView.vue:189, 199`

- **Problem.** The overdue row shows the red badge "Overdue since 21-10" on the top line.
  The second line reads "SMTW.MCC1 · Overdue · for 21-10-2026 · waiting for parts". The row
  shows the date twice and "Overdue" twice, on a phone-width list.
- **Fix (optional).** On an overdue row, leave the state word and the date out of the
  second line ("SMTW.MCC1 · waiting for parts"). The badge already carries both.

## View on the coder's departures

The brief asked for this view on each departure, and in particular on the additions that the
user sees. CLAUDE-COMMON says: nothing beyond the agreed scope. Every departure below is listed
in the report's "Decisions taken", so none is unreported.

| # | Departure | View |
|---|---|---|
| 1 | One `schedule` entry with `state_keys`, not a second `MOVES` entry | **Accept.** The brief asked the coder to state how `MOVES` holds a key that depends on the state. One entry gives one move name, one route and one button with no de-duplication. The gap is CR1-01. |
| 2 | `_lock_ticket` takes a key or a function of the locked state | **Accept.** The other choice was a near-copy of the lock function. |
| 3 | *Change plan* needs both the date and the reason in the body | **Accept.** The dialog always sends both (it opens prefilled), and a full plan makes "Nothing to change" a plain comparison. |
| 4 | "Nothing to change" has no field (top of the dialog) | **Accept.** It is about the whole plan. `expectFieldMessage` finds it in the dialog, as the brief says. |
| 5 | A bad date reads "Enter the date as YYYY-MM-DD" | **Accept.** It is labour's message, and only an API client can see it. |
| 6 | The timeline follows BR2-08 ("for … (was …)"), not the older "old → new" of § 1.3 and § 8 | **Accept.** BR2-08 is the later decision, and the e2e test checks it. |
| 7 | List row wording | **Accept.** See the nit CR1-05. |
| 8 | **The times card shows *Logistic delay* and *Administrative delay* totals** | **Within the brief's intent.** § 3 asks `ticketLabels.js` for "the reasons' delay kinds". The only use of the kinds on the screen is to sum them, and § 1.5 and § 5.4 say that the totals are summed "where they are shown". The brief's card example shows only the per-reason line, so the user has not seen these two lines. They are EN 13306's own terms, which `.claude/CLAUDE.md` prefers. The cost: with one reason, the card shows the same figure three times ("of which waiting 1 h", "Waiting for parts 1 h", "Logistic delay 1 h"). Show this to the user at gate B. Dropping them is a two-line change. |
| 9 | **The labour panel keeps hours (`minutesText(…, { days: false })`)** | **Within the brief's intent.** BR2-03 changed the shared helper for response, repair and downtime. Labour is man-hours (ISO 14224), and without the option "26 h" of labour would read "1 d 2 h". The option keeps an S018 display as it was, so it is not new scope. |
| 10 | **The timeline shows "Machine stopped for this work" / "Machine kept running"** | **Within the brief's intent.** The brief stores the answer on the *started* event (§ 4.2), and the timeline is where a ticket's events are read. Without the line, the answer that decides *Planned stop* would be on no screen. See the nit CR1-03 on the wording. |
| 11 | The choices read "Yes, machine stopped" / "No, machine running", and only the legend changes tense | **Accept.** BR1-14 asks for the tense in the question only. |
| 12 | The state badge gets the class `state-badge` | **Accept.** It turns red when overdue. The S018 and S025 tests that use `stateBadge` pass. |
| 13 | v21 places the new columns after `state` and after `remark` | **Accept.** MariaDB adds them in place; nothing reads columns by position. |
| 14 | The seed sets `FLASK_DEBUG=1` and reads `CURDATE()` on the +05:30 session | **Accept.** It matches `e2e_backend.py`. The connection is autocommit (`_connect_kwargs`), so the single `UPDATE` is committed. |
| 15 | `test_migration_v21.py` imports the helpers from `test_migration_v20.py` | **Accept.** The brief allows either way, and nothing is copied. |

## Points the orchestrator asked about

- **v21: no precondition is justified.** Fact: v21 adds five nullable columns, appends one
  ENUM value and adds one CHECK. On every existing row the state is not `scheduled` and the
  new columns are NULL, so `(FALSE) = (FALSE)` holds. Nothing is converted or dropped. The
  comment above v21 says this, as BS1-02 asks. The migration test builds a v20 database with
  a ticket and its event, applies v21, and checks the following:
  - the rows are unchanged;
  - the new columns are NULL;
  - the ENUM keeps `NOT NULL DEFAULT 'raised'`;
  - the reason ENUM equals `WAITING_REASONS`;
  - `chk_tickets_plan` exists.
- **v21 re-run.** Every statement is idempotent: the `MODIFY` lists the same values, and
  `ADD COLUMN IF NOT EXISTS` and `ADD CONSTRAINT IF NOT EXISTS` skip what exists. The test
  deletes `db_version` 21, runs v21 again, and compares the whole schema: unchanged. MariaDB
  commits each DDL statement on its own, so a run that stops half way can also be re-run.
- **The move rules and RBAC per state.** `MOVES` matches § 1.2:
  - *Schedule* from raised or acknowledged takes `ticket:assign`, and from in progress
    `ticket:work`;
  - *Change plan* from scheduled takes `ticket:assign`;
  - start, restore, not a fault and `REGRADE_STATES` gain scheduled.

  `allowed_moves` uses `key_at`, so a technician sees *Schedule* only on a ticket in
  progress. This is tested in the API and in the e2e suite. The key is checked at the
  ticket's site (`require_perm_at`) from the locked state. The gaps are CR1-01 and CR1-04.
  No new key is added, and `config_rbac.py` is unchanged.
- **Locking (S025 CR1-02).** S019 adds no explicit lock. *Schedule* and the start from
  scheduled change `state`, so they take the same shared foreign-key locks on the unit,
  machine and component as every move. The lock-order note in `tickets.py` now says this in
  CR1-02's words. It lists the four accepted deadlocks and names the S019 moves. *Change
  plan* writes `state` with its unchanged value. InnoDB builds the update from the columns
  that differ, so the secondary indexes are not rewritten and no foreign key is re-checked.
  The note's claim holds.
- **IST dates.** Every server-side "today" is the IST date of `_now()`:
  - `_schedule` uses `now.date()`, and the event's time plays no part (BR1-05, tested with a
    back-dated schedule);
  - the list's overdue filter passes `_today()` into `t.planned_date < %s`;
  - `_ticket_out` decides `overdue` with the same date.

  The seed reads `CURDATE()` on a +05:30 session. In `ScheduleFields.vue`, the date input's
  `min` and `max` come from the phone's own clock. A phone set to another time zone could
  offer a day that the server then refuses. The server's rule decides, so this is acceptable.
- **The EN 13306 delay mapping.** `parts`, `vendor` and `expert` are logistic delay: the
  wait for maintenance resources (spares, an outside repairer, a specialist). `slot` and
  `approval` are administrative delay: the wait for a decision or for production to release
  the machine. `other` is in neither total. The waiting time is counted only while the ticket
  is critical and scheduled. That is correct: in EN 13306 both delays are parts of the time
  to restoration, which runs only after a failure. A defect waiting for its slot is backlog,
  and it gets null. Both test suites assert the six codes and their kinds.

## Checked and found consistent

- **Brief § 1.4 and § 7 decision 3.** `WAITING_REASONS` and `WAITING_REASON_LABELS` /
  `WAITING_REASON_DELAYS` hold the six codes with the same labels and kinds, asserted in
  both test suites.
- **Brief § 5.1–5.3, the body rules.** The following are checked in `validate_move`, a 400
  before the transaction:
  - the date format;
  - the reason code;
  - *Other* needs a remark;
  - the remark is required on *Change plan*;
  - `machine_stopped` is a boolean.

  `planned_date_error` (today to 365 days) runs in the step. "Nothing to change" is decided
  from the locked row: `_LOCK_TICKET` selects the plan. On an overdue ticket, *Change plan*
  must set a new date (BR2-07, tested).
- **Brief § 3 and BR1-08, clearing the plan.** `_apply_move` clears the plan columns in one
  place, whenever the ticket leaves scheduled. `chk_tickets_plan` refuses a direct
  `UPDATE` that breaks the rule (tested both ways). No other code writes `tickets.state`.
- **The stopped question.** `machine_stopped_needed` asks it only from scheduled on a
  non-critical ticket. On a critical ticket a value sent is ignored and stored as NULL
  (tested). *Back in service* asks it only with a start time, and `asks_machine_stopped`
  carries the rule to the page.
- **`ticket_times`.** One pass over the events. I checked the following against § 5.4:
  - response counts the first *scheduled*;
  - a *scheduled* event ends the repair stretch;
  - a restore from scheduled with no start makes repair null;
  - downtime includes scheduled while critical;
  - waiting follows the reason in force, and `waiting_by_reason` is null with
    `waiting_minutes`;
  - the planned stop ends at back in service, at *scheduled* or at a change to critical.

  Every case of § 8 has a unit test, and the S018 figures are unchanged.
- **Brief § 1.6, the list.** The *Scheduled* and *Overdue* filters order by planned date. In
  *Open*, scheduled rows come after the actionable ones within an intensity (tested). The
  `ORDER BY` uses a code constant only, and all values are parameters.
- **Brief § 1.7, the page.**
  - The badge reads Scheduled, Waiting or Overdue (red), with the plan line under the header.
  - *Schedule* and *Change plan* are outline buttons, apart from the chain.
  - `ScheduleFields.vue` holds the date and the reason select.
  - *Schedule* opens with the date empty. *Change plan* opens prefilled, with the remark
    required.
  - *Other* opens the remark with "What does it wait for?".
  - `asksStart` includes scheduled.
- **Layers.** Every rule and figure is in `tickets_core` (pure). The route and the Vue files
  only shape and show. `waitingSplit` sums the kinds for display, as § 5.4 allows.
- **Reuse.** `_optional_date` is shared with `validate_labour` (BR1-16), and the
  `minutesText` change is one helper. The test helpers `postAs`, `istDay` and `shownDay`
  replace near-copies.
- **Security.** No new route. No actor is taken from the client. The new SQL uses
  parameters only.
- **The e2e checks.** Each important automated check has a test that asserts what the user
  sees: the badge, the plan line, the timeline text, the times-card values and the red
  badge. `openAction` calls `expectDialogFits` on every dialog that it opens, so the Schedule,
  *Change plan* and *Start* dialogs are checked on the two phone projects. The "Nothing to
  change" 400 is declared with `allowFailedRequest`. The seed checks the target database
  before its single `UPDATE`.
- **Existing assertions changed by design (BR1-09, BR2-01, BS1-04).**
  - `OPEN_STATES`, the move tables, `test_moves_listed_per_user` and the `STATE_LABELS` keys
    are updated.
  - `test_migration_v12.py` appends `'scheduled'`.
  - `test_migration_v20.py` pins `V20` to version 20 alone, with its assertions unchanged.
- **BS1-06.** Row 9 of `device-checks.md` and S025's impl report now say "the latest schema
  version". S019's report notes the joint release of v20–v22.
- **Manual checks.** The impl report has `## Manual checks`. Every important check of § 8
  is listed: the automated ones as `[auto]` with the test name, backed by my passing run, and
  the real-device date-picker check as an unticked box and as row 10 of `device-checks.md`.
- **Screen text (scope B).** The new texts are short and say what to do:
  - "Choose the planned date";
  - "The planned date cannot be before today";
  - "Plan within a year";
  - "Choose why it waits";
  - "Choose Yes or No";
  - "Why did the plan change?".

  The only gap is the nit CR1-03.
- **The UX checklist.**
  - The dialogs reuse `FormModal`, whose body scrolls with a fixed footer.
  - The reason is a select, so the dialog stays short on a phone.
  - The buttons are `btn-lg`.
  - The list's state filter is a select, so two more options do not widen it.
- **The impl report (scope A).** It is written in scope A; no finding.
- **Track.** The step is on the full track, as the brief says.

## Manual checks still needed (the user's)

- [ ] **Important.** Row 10 of `device-checks.md`, on an Android phone and an iPhone, as an
  engineer:
  1. Open a defect ticket and press **Schedule**.
  2. Tap **Planned date**: the phone's own date picker opens.
  3. Pick a date a few days ahead, choose *Waiting for parts*, and press **Schedule**.
  4. Check that the line under the ticket number shows the date as DD-MM-YYYY.
- **At gate B, for the user to decide:** keep or drop the *Logistic delay* and
  *Administrative delay* lines on the times card (departure 8).
