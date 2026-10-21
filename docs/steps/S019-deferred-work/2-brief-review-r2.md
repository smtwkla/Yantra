```
Step: S019 — Deferred work
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: no `blocker` or `major` finding is open.** Every round-1 answer
marked *Accepted* is in the brief text, not only in the Review log (checked one
by one below). What remains are three `minor` points the coder would otherwise
decide alone — two existing tests that v21 breaks and are not on the brief's
"change by design" list, the way the overdue e2e ticket is seeded (a serial
collision waits there), and a times helper that cannot show the days the card's
example shows — and nits on wording and placement. The brief can go to the user
once the minors are answered.

## Round 1 answers, verified in the text

| Finding | Where it now stands in the brief |
|---|---|
| BR1-01 | § 1.4 table: six reasons, `parts`/`vendor`/`expert` logistic, `slot`/`approval` administrative, `other` unclassified; § 4.1 ENUM; § 5.4; decision 3 |
| BR1-02 | § 2: Clause 7 entry after *corrective maintenance* (number flagged), Clause 9 + Annex A, the five parts of time to restoration with the two accepted simplifications, ISO 14224 reworded to down time and active maintenance time; § 9 Q7 |
| BR1-03 | § 2: planned/unplanned and reactive/proactive named, the proxy stated as a deliberate departure, backlog in crew-weeks vs the plant's backlog age, scheduled/unscheduled downtime, ISO 55001 § 8.1; MTTR number disagreement in § 3 Docs and § 9 Q7 |
| BR1-04 | § 1.6 order, § 3 list, decision 10, § 8 API tests |
| BR1-05 | § 1.8, § 3 `planned_date_error(planned, today)`, § 5.1, § 8 |
| BR1-06 | § 3 Frontend, § 6 "No new route", § 8 both suites assert the six codes |
| BR1-07 | § 1.5, § 5.4 `waiting_by_reason`, § 6 |
| BR1-08 | § 3 `_apply_move` clears on leaving scheduled; § 5.3 |
| BR1-09 | § 3 Tests: the four assertions and `seed_e2e.py` |
| BR1-10 | § 1.7: Change plan prefilled, *Other* opens the remark, the stopped question on restore once a start time is filled, `asksStart` gains scheduled; § 6 `asks_machine_stopped` |
| BR1-11 | § 4.1 "No new index" |
| BR1-12 | Order paragraph; S020's brief says the same |
| BR1-13 | § 1.1, § 1.7 one-word badge, the line under the header |
| BR1-14 | § 1.7 "Is …" / "Was …" |
| BR1-15 | § 8 device check reworded; the three dialog-fit checks |
| BR1-16 | § 3 `ScheduleFields.vue`, `_optional_date`; § 4.3 the `MODIFY` restates `NOT NULL DEFAULT`; § 5.1 / § 5.2 labels with "Add a remark"; old → new from the events |

## Findings

### BR2-01 · minor · Two more existing tests change by design: v12's exact `state` ENUM, and S025's v20 tests if they run the whole migration list

**Problem.** § 3 Tests lists four assertions that v21 breaks. Two more:

- `backend/tests/test_migration_v12.py:63` asserts the column type exactly:
  `tickets["state"] == ("enum('raised','acknowledged','in_progress','back_in_service','closed')", "NO")`.
  S025 keeps the v8–v13 shape tests "unchanged (they test today's schema,
  whichever migration built it)"; after v21, today's schema has `scheduled`
  in the ENUM, so this line must gain it.
- S025's `test_migration_v20.py` (being written now, after S024) builds "with
  v20" and compares it to the v1–v13 fixture, and its dev path asserts "a v13
  database gets v20 recorded with no table changed". If those tests run
  `local_db._MIGRATIONS` as a whole rather than `[v20]`, S019's v21 adds two
  columns and changes the ENUM, and both fail. The coder cannot know which
  shape S025 chose until S025 is committed.

**Why it matters.** The coder would otherwise meet a red test from another
step and decide alone whether to pin the list or loosen the assertion.

**Options.** Add both to the "change by design" list (recommended): the v12
line gains `'scheduled'`; and "S025's v20 tests must build and compare **v20
alone** (the fixture against `_MIGRATIONS[:1]`, or the version pinned) — if
they run the full list, S019 pins them, not the assertion". A one-line check
for the coder on reading S025's impl report.

### BR2-02 · minor · The overdue e2e ticket: `seed_e2e.py` has no database connection, and a ticket inserted by SQL collides with the serial counter

**Problem.** § 3 Tests says the overdue ticket is "written by SQL (a ticket
row, its `raised` and `scheduled` events, `planned_date` yesterday)". Two
things the coder would hit:

1. `seed_e2e.py` talks to the e2e backend only through its API
   (`seed_dev.call`); it holds no DB settings. The e2e database is
   `vel_yantra_e2e` on the dev container (`e2e_backend.py` sets
   `config.DB_CONFIG["database"]` and drops and recreates it); the seed needs
   that connection (pymysql, the same `config.DB_CONFIG` with the e2e name)
   or a way to get it.
2. A ticket row inserted by SQL needs a serial. `serial_counters` is not
   bumped by that insert, so the first spec that raises a ticket through the
   API in the same month gets `next_counter` = 1 → `TK-2026-10-001` →
   `uq_tickets_serial` → 500 "Serial collision — retry", and the suite fails
   on an unrelated test.

**Why it matters.** The e2e check "the *Overdue* filter shows a ticket planned
in the past" is marked important; as described it cannot be written without
a design choice, and the obvious one breaks other tests.

**Options.**
- (a) Recommended: the seed **raises and schedules the ticket through the
  API** as admin (today's date, reason `parts`, like every other seeded
  record), then runs **one SQL `UPDATE`** to move `planned_date` to yesterday
  on the ticket and on its `scheduled` event. The serial is real, the CHECK
  holds (the state is scheduled and both plan columns are set), and the SQL
  is two statements. The connection: pymysql with `config.DB_CONFIG` and the
  e2e database name, imported the way `e2e_backend.py` does, or the e2e
  backend passing the name in an environment variable the seed reads.
- (b) Insert everything by SQL and bump `serial_counters` too. More SQL to
  keep in step with the schema.
- (c) A test-only API hook that accepts a past date. Rejected: a rule
  bypass in the product for one test.

### BR2-03 · minor · The times card's example shows days; `minutesText` has no days

**Problem.** § 1.5's card reads "Downtime 3 d 4 h — of which waiting 2 d
20 h (parts 2 d 20 h)". `ticketLabels.minutesText` formats hours and minutes
only ("1 h 25 min", "2 h"), so a press three weeks at the maker shows
"504 h" on every line. The brief changes `ticketLabels.js` anyway but does
not say whether the helper gains days.

**Why it matters.** This step is the first where multi-day figures are the
normal case (waiting, overdue), and the coder would decide the format alone;
the same helper formats Response, Repair and Downtime, so a change touches
S018's e2e assertions ("1 h 30 min" stays as is only if days start at 24 h).

**Options.** (a) Recommended: `minutesText` gains days from 24 h ("2 d
20 h", "3 d"; minutes dropped once there are days, as `ageText` already does),
with its unit test; S018's assertions are all under a day and stay. (b) Keep
hours and drop the days from the example. (a) is what the floor reads.

### BR2-04 · nit · `_LOCK_TICKET` must carry `planned_date` and `waiting_reason`

*Change plan*'s "Nothing to change" compares the body with the ticket's
current plan, and S018 § 5.3's rule is that every refusal is decided from the
**locked** row. `_LOCK_TICKET` selects a fixed column list (`id, state,
intensity, …`); `planned_date` and `waiting_reason` have to be added there,
not only to `_TICKET_COLUMNS` (the plain read that `_lock_ticket` merges in).
One line in § 3 Backend.

### BR2-05 · nit · "Other needs a remark" belongs in `validate_move`, not the step

§ 5.1 says the `other` → remark rule is "checked in the step, since it depends
on the reason". It depends only on the body (reason and remark), not on any
row, so it is a pure check that fits `validate_move` beside the `requires`
loop: a 400 before the transaction and the lock, as every other body rule.
Only `planned_date_error` (needs `today`) and "Nothing to change" (needs the
row) belong in the step.

### BR2-06 · nit · The server's `machine_stopped` message has a tense

§ 5.3 gives one server message, "Was the machine stopped for this work? Choose
Yes or No", while § 1.7 words the question "Is …" at *Start* and "Was …" at
*Back in service*. The server has one constant for both moves. Make it
tense-free, e.g. "Choose Yes or No — was the machine stopped?", or simply
"Choose Yes or No" as the dialog's own check already says for send-back; the
question itself is the field's legend, chosen per move on the page.

### BR2-07 · nit · Three small § 5.4 / § 5.3 points to state, each one test

- **Back in service straight from scheduled, no start time, after an earlier
  in-progress stretch** (breakdown: started 10:00, scheduled for parts
  12:00, back in service 15:00 with no start time): by the existing loop
  `repair_from` is None at the restore, so `repair_known` is False and repair
  is **null**, though two hours were measured. § 5.3 implies it ("planned
  downtime is then unknown, as repair already is"); § 5.4 should say it, and
  the pure tests cover it — the alternative (keep the measured part) is the
  other defensible reading and the coder must not pick.
- **`waiting_by_reason` when waiting is null**: null too, or `{}`? Say
  (null, I'd suggest: both keys absent-or-null together).
- **Change plan on an overdue ticket**: the dialog is prefilled with the past
  date, so "The planned date cannot be before today" is refused even when
  only the reason changes. That is right (an overdue plan is no plan), but
  say it in § 5.2 and test it: "on an overdue ticket, Change plan must set a
  new date".

### BR2-08 · nit · The timeline line for a reason-only change, and the reason on the overdue header line

- § 5.2's line "Plan changed: 25-10-2026 → 02-11-2026 (parts) — remark"
  shows a date change with the new reason; a change of **reason only**
  ("parts" → "slot", same date) has no shape. Simplest: every *scheduled* /
  *rescheduled* line reads "for <date> · <reason>", and a *rescheduled* line
  adds "was <old date> · <old reason>" (from the previous event, as the brief
  already derives it). One format for both cases.
- § 1.7's header line for an overdue ticket reads "since 25-10-2026" and
  drops the reason — the one thing the engineer needs most when a date has
  slipped. "Overdue since 25-10-2026 · waiting for parts".

### BR2-09 · nit · Two small UX points on the ticket page and the Schedule dialog

- **Button weight.** On a raised ticket an engineer gets *Acknowledge*,
  *Start work*, *Back in service* and now *Schedule* as stacked `btn-primary`
  buttons; *Schedule* is planning, not the next step of the chain. Show it
  outline (`btn-outline-primary`, as *Change severity* is) so the chain's next
  tap stays the obvious one; *Change plan* the same. Where the brief says
  "sit with the chain moves" add "in outline".
- **The reason control.** Not stated. A `<select>` (as the cause picker in
  *Close*) keeps the dialog to date + reason + Save on a phone; six large
  choice buttons as in *Send back* would push Save below the fold with the
  time and remark rows. Say "a select".

### BR2-10 · nit · One SMRP term for the owner: overdue feeds *schedule compliance*

§ 2 ties *overdue* to backlog. The SMRP work-management metric it feeds more
directly is **schedule compliance** (the share of scheduled work completed in
the period it was scheduled for; cited by name, number to be checked as the
others). A scheduled ticket not back in service by its planned date is a
missed schedule; phase 5 can count them. One line in § 2's SMRP bullet.

## Checked and found consistent

- **Code claims.** `MOVES`, `_MOVE_STEPS`, `_apply_move` (the event, then
  `update_row` with state and changes in one statement — so `chk_tickets_plan`
  sees state and plan columns change together), `_restore` writing the
  *started* event with `from_state`, `started_at_error` (refuses only
  `IN_PROGRESS`, so a start time from scheduled is allowed), `REGRADE_STATES`,
  `_DOWN_STATES`, `ticket_times`' loop, `validate_labour`'s
  `date.fromisoformat`, `MoveDialog.asksStart`, `_moves` building per-move
  entries, `enum_arg` for the new state filters, `update_row` writing NULLs
  (so the clearing rule works as a plain update): all as the brief states.
- **Locks and transactions** (§ 5.6): the ticket row only, no new edge; 409
  `TICKET_CHANGED` from the from-state check for a stale page.
- **RBAC**: `ticket:assign` → `maint_engineer`, `it_admin` (the manager
  inherits) in `config_rbac.PERMISSIONS`, site-scoped; no new key; matches
  S018 § 5.7's table and Plan.MD "set by the engineer".
- **Migration shape**: `ADD COLUMN IF NOT EXISTS`, `ADD CONSTRAINT IF NOT
  EXISTS … CHECK` as v12/v13; the ENUM append is a comparison-only value
  (`t.state = 'scheduled'`), so position does not matter; `from_state` /
  `to_state` `VARCHAR(20)`; the CHECK holds on every existing row; a rollback
  to the previous image is safe (nullable columns, appended value).
- **Order with S025**: not-a-fault from in progress and `allowed_moves(…,
  has_repeat)` are S025's; the brief's table includes the first and the second
  does not touch the new moves. The v21 numbering agrees with S020's brief.
- **S021 / S023**: S021 § 1.5 treats *scheduled* as "left raised" (no
  escalation; a re-grade to critical while scheduled alerts without
  escalating), as the brief's Q6 assumes.
- **Plan.MD § 4.2** *Deferred work* and *Fleet defects*, Q13, Q25;
  **Maintenance-Philosophy** § 4 (planned downtime not a breakdown), § 7
  (*Deferred corrective maintenance*, Proposed), § 10 (MTTR cited as SMRP
  3.5.5 there; the brief flags the disagreement with S025's 3.5.2 for the
  copy check); **Plant-Facts** § 4 (diagnosis by one person, "some problems
  take months"; AMC vendors; garages). The brief settles what they propose,
  meter targets correctly deferred.
- **Standards.** EN 13306 deferred corrective maintenance and the delay split
  (now mapped correctly: specialists are a resource), ISO 14224 down time vs
  active maintenance time, SMRP planned/reactive as a stated proxy, backlog in
  crew-weeks, scheduled/unscheduled downtime, ISO 55001 § 8.1, OEE's planned
  stops, ISO 9001 § 10.2. Numbers withheld where unconfirmed — right. EN
  13306 also defines *scheduled maintenance* (carried out to an established
  time schedule), so the state's name is the standard's word.
- **Design and layers.** All rules in `tickets_core` (pure: `planned_date_error`
  takes `today`, `ticket_times` takes `now`); the route adds two steps on the
  existing pattern and one clearing line; the page shows the stopped question
  from `asks_machine_stopped`, not its own rule; the labels are plain copies
  as `STATE_LABELS` is; no new abstraction, endpoint or key. Right-sized.
- **UX.** Schedule is date + reason + Save; Change plan is prefilled and set
  apart by its required remark; *Other* opens the remark before the server
  refuses; the stopped question is one tap of Yes/No; the list keeps
  scheduled rows visible but after the actionable ones; the two filters order
  by planned date; the badge is one word; no control shown without the key.
  The one device check carries account, network and where; the dialog-fit
  checks are automated as they should be.
- **Edge cases covered**: back-dated schedule with a date before today
  (refused), the date on its own day (not overdue), 365/366 days, reason
  change mid-wait, re-grade to critical while scheduled (waiting from then),
  a planned stop cut by a re-grade, not a fault from scheduled (all null),
  the CHECK as a guard that never fires.
