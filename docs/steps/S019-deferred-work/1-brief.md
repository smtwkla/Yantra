```
Step: S019 — Deferred work
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026 after brief-reviews r1 and r2)
Track: full
Status: Committed b6b8dfb (22-10-2026); important check pending: row 10 — the phone date picker and DD-MM-YYYY (IT Admin)
Baseline: 3df667c + uncommitted S025
```

# S019 — Deferred work

S017 and S018 handle a ticket as if the work starts as soon as someone can get
there. Much of the plant's work does not: a worn scraper, a touchscreen, a
liner "good for another 1,000 hours" or a filter the AMC vendor asked for is
**requested now and done later**, once parts are bought and production gives
a slot. A stopped press may also wait three weeks for a cylinder at the maker,
and a vehicle may sit at a garage. Today such a ticket either looks *in
progress* the whole time or sits *acknowledged* with nothing to say why, and
its downtime cannot tell repair from waiting.

This step adds a **scheduled** state with a **planned date** and a **waiting
reason**, and three figures that follow from it:
- **waiting time** on a breakdown, split into logistic and administrative
  delay (EN 13306);
- **planned downtime**, the stop taken for a scheduled job, kept apart from
  breakdown downtime;
- a ticket past its planned date shows as **overdue**, so deferred work cannot
  be forgotten (SMRP backlog).

It settles Plan.MD Q13 (except meter-value targets) and the *Deferred work*
and *Fleet defects* notes of Plan.MD § 4.2.

**Order.** S019 is coded **on top of S025's code**, which is not committed
yet. The user commits S025, S019 and S020 together (22-10-2026, BS1-05):
- S025 changes `tickets_core.MOVES`: *not a fault* is allowed from in progress,
  and there is no send-back after a repeat. S019 builds on that table;
- S025 squashes the migrations into v20, so S019's migration is **the next
  free version after v20**: S019 and S020 take v21 and v22 in coding order
  (BR1-12). The text below says "v21" for short.

## 1. What will be built

1. **A new state, `scheduled`**, between acknowledged and in progress:

   ```
   raised ──► acknowledged ──► in progress ──► back in service ──► closed
     │             │      ▲  │       ▲
     │             ▼      │  ▼       │
     └──────► scheduled ──┘ (work stops: waiting)
                 │ ▲
                 └─┘ change plan
   ```

   One state serves both cases from the use cases:
   - **Deferred work** on a running machine (a defect, *degraded* or
     *initial*): the badge reads **Scheduled**, with the line "for 25-10-2026 ·
     waiting for a production slot" under the header;
   - **A stopped machine waiting** (a *critical* ticket): the badge reads
     **Waiting**, with "for parts · expected 25-10-2026". The machine is down,
     so the time counts as downtime, but not as active repair.

2. **Two new moves**, and existing moves that now also start from scheduled:

   | Move | From | To | Key | Needs |
   |---|---|---|---|---|
   | **Schedule** (new) | raised, acknowledged | scheduled | `ticket:assign` | planned date, waiting reason; remark optional (required for *Other*) |
   | **Schedule** (new) | in progress | scheduled | `ticket:work` (technician and up, U1) | the same |
   | **Change plan** (new) | scheduled | scheduled | `ticket:assign` | new planned date and/or reason, **remark required** (why it slipped) |
   | Start work | raised, acknowledged, **scheduled** | in progress | `ticket:work` | from scheduled, on a ticket that is not critical: **"Was the machine stopped for this work?"** yes / no |
   | Back in service | raised, acknowledged, in progress, **scheduled** | back in service | `ticket:restore` | as S018; with a start time from scheduled on a non-critical ticket, the same stopped question |
   | Not a fault | raised, acknowledged, in progress (S025), **scheduled** | closed | `ticket:close` | as S018 |
   | Change severity | raised, acknowledged, in progress, **scheduled** | — | as S018 | as S018 |

   Acknowledge, send back and close are unchanged. Schedule from *in progress*
   is "work stops, we are waiting": the technician started, found the part
   missing, and records the wait at once, so the wait is not counted as
   repair (U1, § 9 Q1). Committing a slot (Schedule from raised or
   acknowledged) and *Change plan* stay the engineer's. Both rows are one
   *Schedule* button; only who may press it depends on the state.

3. **The planned date and waiting reason** live on the ticket as its
   **current** plan (`tickets.planned_date`, `tickets.waiting_reason`). Each
   *scheduled* and *rescheduled* event keeps its own copy, so the timeline
   shows every slip ("Plan changed: 25-10 → 02-11, parts not arrived").
   Leaving the scheduled state (start, back in service, not a fault) clears
   the two columns. The events keep the history.

4. **Waiting reasons**: a fixed list in code (§ 7 decision 3). Each reason
   belongs to one of EN 13306's two delay kinds, or to neither (BR1-01).
   EN 13306 counts as **logistic delay** the wait for maintenance *resources*
   (spare parts, **specialists**, test equipment, information, travel), and as
   **administrative delay** the wait for *administrative reasons* (a decision,
   a permit, a budget, production releasing the machine):

   | Code | Shown as | EN 13306 delay |
   |---|---|---|
   | `parts` | Waiting for parts | logistic |
   | `vendor` | At or waiting for a vendor, garage or maker | logistic |
   | `expert` | Waiting for an expert | logistic |
   | `slot` | Waiting for a production slot or shutdown | administrative |
   | `approval` | Waiting for a decision or approval | administrative |
   | `other` | Other (remark required) | not classified |

   An expert is a resource, like a spare part: the plant's longest known
   waits, fault diagnosis by one person (Plant-Facts § 4), are logistic delay.
   `other` is reported as its own line, "other waiting", inside the waiting
   total but in neither delay total, so the reports say exactly what was
   recorded.

5. **The figures** (S018's times card), all computed from the events:
   - **Response**: the first *acknowledged*, *started* **or *scheduled***
     minus *raised*. Scheduling is a response: someone looked and planned it.
   - **Repair** (active corrective maintenance time): unchanged. It is the
     time in progress, so a stretch of waiting in the middle is left out by
     itself. A *scheduled* event now ends an in-progress interval, as *back in
     service* does.
   - **Downtime** (time to restoration): unchanged in definition. It is the
     time while critical and not back in service, and that now includes
     *scheduled*.
   - **Waiting** (new), on a ticket that was critical while scheduled: the
     time in scheduled while critical, **per reason**. Each slice takes the
     reason in force at that moment. The logistic and administrative totals
     are sums over the fixed reason map (§ 1.4), done where they are shown.
   - **Planned downtime** (new): the time from a *started* event marked
     *machine stopped for this work* to the next back in service, while the
     ticket is not critical. A ticket that turns critical during the job
     counts from then as downtime, a breakdown, and no longer as planned
     downtime.

   The card shows, for example: "Downtime 3 d 4 h — of which waiting 2 d 20 h
   (parts 2 d 20 h)", in the reasons' own words, which is what the floor reads.
   "Planned stop 3 h 10 min" shows only when there is one. To show days,
   `minutesText` gains them from 24 h on ("2 d 20 h", "3 d"), and drops the
   minutes once there are days, as `ageText` already does (BR2-03). Response,
   repair and downtime use the same helper, so a long breakdown reads in days
   too; S018's figures under a day read as before.

6. **The tickets list**:
   - the state filter gains **Scheduled** and **Overdue** (scheduled, with a
     planned date before today, IST);
   - a scheduled row shows its planned date and reason. An overdue row shows
     a red **Overdue** badge with the date ("Overdue since 25-10");
   - **the order** (BR1-04): in the open list, critical first as today, but
     within an intensity the **scheduled rows come after the actionable ones**
     (`ORDER BY t.intensity, t.state = 'scheduled', t.occurred_at, t.id`), so
     a press waiting three weeks for a cylinder does not lead every
     technician's list above a fresh breakdown. Scheduled rows stay in the
     open list, never hidden. The *Scheduled* and *Overdue* filters order by
     **planned date** (`t.planned_date, t.id`): what is due next, what is most
     overdue.

7. **The ticket page**:
   - the state badge is one word, *Scheduled*, *Waiting* or **Overdue**
     (BR1-13); the line under the header carries the date and reason ("for
     25-10-2026 · waiting for parts", or "Overdue since 25-10-2026 · waiting for
     parts" when overdue, BR2-08), where a phone has room;
   - *Schedule* and *Change plan* buttons sit with the chain moves for those
     who may make them (§ 1.2), **in outline** (`btn-outline-primary`, as
     *Change severity*), so the chain's next step stays the obvious tap
     (BR2-09);
   - the dialogs follow S018's short-dialog rules (the time as "Now · Change",
     the remark behind *Add remark* where optional). The date and reason are
     one component, `ScheduleFields.vue` (BR1-16). The reason is a
     **select**, as the cause picker in *Close*, so the dialog stays date,
     reason and Save on a phone (BR2-09);
   - *Schedule* opens with the planned date empty, so the engineer must choose
     one;
   - *Change plan* opens **prefilled with the current date and reason**, the
     remark open and required, so the engineer changes one thing and saves
     (BR1-10);
   - choosing **Other** opens the remark and marks it required, as *Not a
     fault* does, so the server's refusal is the exception (BR1-10);
   - the stopped question reads **"Is the machine stopped for this work?"** at
     *Start* and **"Was the machine stopped for this work?"** at *Back in
     service* (BR1-14). On *Back in service* it shows only once a start time
     is filled, since the server asks for it only then (BR1-10);
   - `MoveDialog`'s start-time rule (`asksStart`) gains `scheduled` (BR1-10).

8. **Rules on the planned date**:
   - it is required;
   - it is **today or later** (the IST date of now), and at most **365 days**
     after today (`PLANNED_DATE_MAX_DAYS`). The event's time plays no part, so
     a back-dated *Schedule* cannot create a ticket that is overdue at birth
     (BR1-05);
   - a past planned date cannot be set; it is reached only by waiting.
   - *Change plan* must change the date or the reason ("Nothing to change"
     otherwise), and a remark is required.

### Out of scope

- **Meter-value targets** ("at 1,000 run hours from now"): phase 4, with the PM
  engine's meter triggers (Plan.MD § 4.3). The planned date is the only
  target here.
- **A planning board or calendar**, and the engineer's dashboard: the list's
  *Scheduled* and *Overdue* filters stand in until the dashboard step.
- **Backlog reports** (backlog age, planned-versus-reactive ratio, planned
  downtime per unit): the data is recorded here; the reports are phase 5
  (Plan.MD § 4.6). § 2 says how each will be computed.
- **Notifications** for overdue tickets: S021's or S023's concern (web push;
  Telegram and the end-of-shift list), noted for them.
- **PM jobs**: they have their own planned dates (phase 4).
- **Planned downtime on a ticket that was never scheduled**: a defect fixed
  on the spot with the machine stopped is reactive work. Its stop is not
  recorded as planned downtime (§ 7 decision 5).
- **The in-house workshop** as a waiting reason: see § 9 Q3.
- Correcting an event time (queued).

## 2. Standards and practice

- **EN 13306:2017 — deferred corrective maintenance** (Clause 7, maintenance
  types: the entry right after *corrective maintenance*; its sub-clause
  number to be checked against the copy held, BR1-02): corrective
  maintenance "not carried out immediately after a fault detection but
  delayed in accordance with given maintenance rules". It stands against
  *immediate* corrective maintenance (the door sensor, fixed now). The
  scheduled state is that delay made visible, with its reason.
- **EN 13306 — the parts of time to restoration** (the time-related terms,
  Clause 9, and their diagram in Annex A; to be checked against the copy):
  after a failure, the item's time to restoration is made up of **fault
  detection time**, **administrative delay** (waiting for a decision, a
  permit, production), **logistic delay** (waiting for resources: spares,
  specialists, test equipment, information, travel), **technical delay**
  (cooling, draining, isolating before hands go on) and **active corrective
  maintenance time** (someone working on it). Yantra already measures active
  repair as the time in progress (S018). The waiting reasons now name the two
  delays, so MTTR can be split into "what maintenance controls" and "what we
  wait for", the split Maintenance-Philosophy § 10 points at ("MTTR minus it
  is waiting"). **Accepted simplifications**: fault detection time sits inside
  downtime when the operator enters an earlier "when it happened" than the
  raise, and technical delay sits inside *in progress*.
- **SMRP Best Practice Metrics, work management** (BR1-03; the metric names
  are SMRP's, their numbers are to be checked against the SMRP copy when the
  reports are built, so none is cited here):
  - **Planned work** and **unplanned work**: SMRP separates *planning* (a job
    plan, meaning scope, labour, parts and tools, prepared before the work)
    from *scheduling* (giving it a slot). **Reactive work** and **proactive
    work** are a second pair: work that breaks into the schedule at short
    notice, against work done ahead of failure. The "planned-versus-reactive
    ratio" of Maintenance-Philosophy § 7 is that second pair. A rising share
    of planned, proactive hours is the sign of a plant moving from
    firefighting to planned maintenance (TPM's *planned maintenance* pillar).
    **Deliberate departure:** Yantra has no job plan in v1, so a ticket that
    went through *scheduled* before work started is a **proxy** for planned
    work, and one started without ever being scheduled a proxy for reactive
    work. The labour booked on each, against the labour on all tickets, gives
    the ratio.
  - **Backlog**: SMRP measures it in **weeks of crew capacity** (planned
    backlog, and ready backlog, which is planned with materials on hand:
    backlog hours divided by weekly crew hours). **Backlog age** per ticket
    ("today minus the date raised") is **the plant's own measure**, close to
    work-order ageing, as *response time* was in S018. The planned date adds
    **overdue**: work past the date the plant committed to. The fleet case
    (Plan.MD § 4.2) is exactly this: small defects "deferred and forgotten".
    Overdue also feeds SMRP's **schedule compliance**: the share of scheduled
    work done in the period it was scheduled for. A scheduled ticket not back
    in service by its planned date is a missed schedule, which phase 5 can
    count (BR2-10; named, number to check as the others).
  - **Scheduled and unscheduled downtime**: SMRP's total downtime is the sum
    of the two. Yantra's *planned stop* is part of scheduled downtime;
    breakdown downtime is unscheduled.

  The report formulas come in phase 5; S019 records what they need.
- **ISO 55001 § 8.1 — operational planning and control**: maintenance
  activities are planned, with the criteria for doing them. The planned date
  and the waiting reason are that plan for deferred corrective work, and each
  slip is recorded.
- **OEE — planned versus unplanned stops**: OEE's *availability* counts
  unplanned stops against planned production time, while planned stops reduce
  the planned time itself. A stop taken for a scheduled job is planned
  downtime, so it must not be counted as a breakdown
  (Maintenance-Philosophy § 4: "A stop taken for scheduled work … is planned
  downtime, not a breakdown").
- **ISO 14224:2016 — maintenance times** (the maintenance record's data,
  BR1-02): ISO 14224 records the **down time** and the **active maintenance
  time**; the difference between them is the delay, which the waiting reasons
  now name.
- **ISO 9001 § 10.2 — nonconformity and corrective action**: a defect deferred
  must still be acted on, and the planned date with its slips is the
  traceable record that it was.

## 3. Where

### Backend

- `backend/tickets_core.py`:
  - `SCHEDULED` state, added to `STATES` after `ACKNOWLEDGED` (workflow
    order), so `OPEN_STATES` includes it;
  - events `SCHEDULED_EVENT = "scheduled"` and
    `RESCHEDULED_EVENT = "rescheduled"`, both in `ORDERED_EVENTS` and
    `EVENT_LABELS` ("Scheduled", "Plan changed");
  - `WAITING_REASONS`, mapping code → (label, delay kind, or `None` for
    `other`); `PLANNED_DATE_MAX_DAYS = 365`;
  - `MOVES` gains `schedule` and `reschedule`, and **one more entry** for
    *Schedule* from in progress under `ticket:work` (U1). Both schedule
    entries reach the page as one move named `schedule`, so the page shows one
    button; the coder states in the report how `MOVES` holds a move whose key
    depends on its from-state. `start`, `restore`,
    `not-a-fault` and `REGRADE_STATES` gain `SCHEDULED`;
    `_DOWN_STATES` gains `SCHEDULED`;
  - `validate_move` parses `planned_date`, `waiting_reason`, `machine_stopped`;
    the `YYYY-MM-DD` parsing `validate_labour` does today is extracted into
    one `_optional_date` used by both (BR1-16);
  - `planned_date_error(planned, today)` (BR1-05);
  - `machine_stopped_needed(from_state, intensity)`: the stopped question is
    asked only from scheduled on a ticket that is not critical;
  - `ticket_times` gains `waiting_minutes`, `waiting_by_reason` (minutes per
    reason code) and `planned_downtime_minutes` (§ 5.4, BR1-07). The response
    counts *scheduled*;
  - `is_overdue(state, planned_date, today)`.
- `backend/tickets.py`:
  - `_schedule` and `_reschedule` steps in `_MOVE_STEPS`, on `_apply_move`'s
    pattern (lock the ticket row, decide from it, write the ticket and the
    event);
  - `_LOCK_TICKET` selects `planned_date` and `waiting_reason` too, not only
    `_TICKET_COLUMNS`, so *Change plan*'s "Nothing to change" is decided from
    the locked row (S018 § 5.3, BR2-04);
  - **the plan columns are cleared in one place** (BR1-08): `_apply_move`,
    after the step, sets `planned_date` and `waiting_reason` to NULL whenever
    the ticket leaves scheduled (`ticket["state"] == SCHEDULED and
    spec.to_state != SCHEDULED`), so every present and future move is covered
    and `chk_tickets_plan` stays a guard that never fires. A `start` step is
    added only to return `machine_stopped` for the event (the shape
    `_MOVE_STEPS` already has); `_restore` does the same for the *started*
    event it writes;
  - `_event_rows` selects the new event columns;
  - the list gains the `state=scheduled` and `state=overdue` filters and the
    order of § 1.6, and returns `planned_date`, `waiting_reason`, `overdue`
    per row; the detail returns them too. No new route (BR1-06).
- `backend/local_db.py`: migration **v21** (§ 4).
- No change to `config_rbac.py`: the moves use the existing
  `ticket:assign`, `ticket:work`, `ticket:restore` and `ticket:close` keys
  (§ 7 decision 4).

### Frontend

- `frontend/src/utils/ticketLabels.js` (+ its test): the state labels
  (*Scheduled* / *Waiting* by intensity, *Overdue*), `WAITING_REASON_LABELS`
  and the reasons' delay kinds (plain copies of `tickets_core`, as
  `STATE_LABELS` is; the server validates the codes, BR1-06), the new event
  lines, and the figures' wording. `ticketLabels.test.js` and
  `test_tickets_core.py` both assert the same six codes, so a drift fails a
  test.
- `frontend/src/views/tickets/MoveDialog.vue`: the "Is / Was the machine
  stopped for this work?" yes / no for *Start* and *Back in service* when the
  move says so; `asksStart` gains `scheduled`; the per-move remark labels
  (§ 5.2).
- `frontend/src/views/tickets/ScheduleFields.vue` (new, BR1-16): the planned
  date and reason pair for *Schedule* and *Change plan* (MoveDialog is 253
  lines already).
- `frontend/src/views/TicketDetailView.vue`: the badge, the line under the
  header, the buttons, the times card lines; the timeline's "Plan changed:
  old → new" is derived by walking the events (the old plan is on the
  previous *scheduled* / *rescheduled* event), as `intensityChanges` does
  (BR1-16).
- `frontend/src/views/TicketsView.vue`: the two filters, the row's date and
  badge.

### Tests

- `backend/tests/test_tickets_core.py`, `test_ticket_work_api.py`, a new
  `test_migration_v21.py`;
- `frontend/e2e/tickets-work.spec.js`: the S019 flows (§ 8);
- `ticketLabels.test.js`, including `minutesText` with days ("2 d 20 h",
  "3 d"; S018's sub-day cases unchanged, BR2-03);
- `tooling/e2e/seed_e2e.py` (BR1-09, BR2-02): the overdue ticket for the e2e
  check. The seed **raises and schedules it through the API** as admin
  (today's date, reason `parts`, like every other seeded record), then runs
  **one SQL `UPDATE`** that moves `planned_date` to yesterday on the ticket and
  on its *scheduled* event. The serial is then a real one from
  `serial_counters`, so no later raise collides on `uq_tickets_serial`, and
  `chk_tickets_plan` holds. `seed_e2e.py` runs in its own process and does
  not import `config` today (BS1-03). It puts `backend/` on the path, imports
  `config`, sets the database name from `e2e_backend.E2E_DATABASE`, and runs
  `e2e_backend.check_target` before any SQL. A mistyped setting then never
  writes to the dev database. The ticket is raised on **`E2E MCC1 mill`**
  (SMTW.MCC1) with the fixed description "E2E seed: overdue for parts", so
  the test finds its row by text:
  - the engineer sees every SMTW unit, so the *Overdue* test runs as the
    engineer;
  - S025's unit test in `masters.spec.js` reads the open count at MCC1
    through the API first, so one more open ticket there is harmless;
  - the raise spec's "Already reported on this machine" check uses the
    extruder, so the mill keeps the seeded ticket out of it.
  The API refuses a past planned date by design; a test-only API hook that
  accepts one is rejected (a rule bypass in the product for one test).
- **Existing assertions that change by design** (BR1-09); update them for the
  new state and moves, don't work around them:
  - `test_tickets_core.py` `test_open_states_are_every_state_but_closed` (the
    exact `OPEN_STATES` tuple);
  - `TestAllowedMoves.test_state_by_keys` and `test_the_table` (every
    `ticket:assign` row gains `schedule`, and every `ticket:work` row gains
    `schedule` from in progress; `start`, `restore`, `not-a-fault`
    gain `scheduled`);
  - `test_ticket_work_api.py` `test_moves_listed_per_user` (the engineer's
    move names);
  - `ticketLabels.test.js`'s exact `STATE_LABELS` keys;
  - `test_migration_v12.py` `test_tables_and_indexes`, the exact `state`
    ENUM type: it gains `'scheduled'` at the end (BR2-01, BS1-07);
  - S025's `test_migration_v20.py` builds with `V20 =
    list(local_db._MIGRATIONS)`, so once v21 exists its equivalence test
    would compare v20 + v21 against the v1–v13 reference. S019 sets `V20 =
    [m for m in local_db._MIGRATIONS if m[0] == 20]` and leaves every
    assertion as it is (`_versions() == [20]`, 27 tables, `[*range(1, 14),
    20]`). `test_modules.py` reads `LATEST_VERSION` from the module and does
    not break (BR2-01, BS1-04).

### Docs (at approval, by the planner)

- `docs/Plan.MD` § 4.2: *Deferred work* from *Proposed* to decided; Q13
  settled except meter targets. § 5: the new columns.
- `docs/Maintenance-Philosophy.md` § 7: *Deferred corrective maintenance* from
  Proposed to decided; § 10: the waiting split, and planned downtime as a
  measure. SMRP metrics are cited by name there; the docs disagree on MTTR's
  SMRP number (Maintenance-Philosophy and S018 say 3.5.5, S025 says 3.5.2,
  BR1-03), so the number is checked against the SMRP copy before any doc
  cites it again (§ 9 Q7).

## 4. Data model (migration v21, or the next free version; see Order)

### 4.1 `tickets`

- `state` ENUM gains `'scheduled'`, **appended at the end** of the list. An
  append is an in-place change on MariaDB, with no table rebuild; the list's
  order is by intensity, not by state, so the position does not matter.
- `planned_date DATE NULL`: the current plan. Set only while the state is
  scheduled.
- `waiting_reason ENUM('parts','vendor','expert','slot','approval','other')
  NULL`: set only while the state is scheduled.
- CHECK `chk_tickets_plan`: `(state = 'scheduled') = (planned_date IS NOT NULL
  AND waiting_reason IS NOT NULL)`. The database itself guarantees that a
  scheduled ticket has a plan and no other ticket does.
- No new index (BR1-11): a few thousand tickets at most, already filtered by
  unit with `ix_tickets_unit_state`.

### 4.2 `ticket_events`

- `planned_date DATE NULL`, `waiting_reason` (the same ENUM) `NULL`: set on
  *scheduled* and *rescheduled*;
- `machine_stopped TINYINT(1) NULL`: set on a *started* event written from
  scheduled on a ticket that was not critical; NULL elsewhere.

`from_state` / `to_state` are `VARCHAR(20)`; `scheduled` fits.

### 4.3 The migration

- Every statement is safe to run twice, as v20's header comment requires: `ADD COLUMN IF NOT
  EXISTS`, `ADD CONSTRAINT IF NOT EXISTS`, and a `MODIFY` of the ENUM that
  lists the same values when re-run. The `MODIFY` restates `NOT NULL DEFAULT
  'raised'`, or the column would lose them (BR1-16).
- **Existing rows**: no ticket is scheduled, so the CHECK holds on every
  existing row (planned_date and waiting_reason are NULL, state is not
  scheduled). Production has no tickets yet (S025 U1: no equipment), dev and
  test have some; none is touched.
- **v21 has no `_PRECONDITIONS` entry** (BS1-02). S025's rule is for a
  migration that can fail on existing data: a `NOT NULL` column or a foreign
  key on a table with rows, a dropped column the old image reads, or data
  that cannot be converted. v21 adds nullable columns, appends an ENUM value,
  and adds a CHECK that every existing row satisfies. The comment above v21
  in `local_db.py` says so, so the SMTW-Review audit of migrations after v20
  sees the answer.
- The previous image ignores the new columns, so a rollback is safe.
- **The first release applies v20, v21 and v22 together** in one `init_db`
  (BS1-06). The preconditions of every pending version are checked first
  (only v20 has one), then each version runs in order. S025's device-check
  row 9 and its impl report say "schema **20**"; the coder changes both to
  "the latest schema version", and S019's impl report notes the joint
  release.

## 5. Rules

### 5.1 Schedule

- From raised or acknowledged: key `ticket:assign` at the ticket's site
  (engineer, manager, IT admin).
- From in progress: key `ticket:work` at the ticket's site (technician and
  up; U1). A technician refused from raised or acknowledged gets 403.
- `planned_date`:
  - required (400 on `planned_date` "Choose the planned date");
  - today or later, the IST date of now ("The planned date cannot be before
    today"); the event's time plays no part (BR1-05);
  - at most 365 days after today ("Plan within a year").
- `waiting_reason`: required, one of the list (400 "Choose why it waits").
  For `other`, the remark is required: the field's label reads "What does it
  wait for?" and the message is S018's "Add a remark" (BR1-16). The rule
  depends on the body alone, so `validate_move` checks it, beside the
  `requires` loop: a 400 before the transaction, as every other body rule
  (BR2-05). Only `planned_date_error` (it needs today) and "Nothing to change"
  (it needs the locked row) are checked in the step.
- Writes the *scheduled* event (with the date and reason) and sets the
  ticket's state and plan columns.
- **No auto-assign**: scheduling is planning, not taking the work.
- From in progress, the in-progress interval ends at the event (repair stops
  counting).

### 5.2 Change plan

- Key `ticket:assign`; from scheduled only.
- The same date and reason rules. At least one of the two must differ from the
  ticket's current plan (400 "Nothing to change"). The remark is required
  through the move's `requires`, with S018's message "Add a remark"; the
  field's label reads "Why did the plan change?" (BR1-16).
- The *rescheduled* event keeps the new date and reason.
- **Timeline lines** (BR2-08), one format for a date change, a reason change
  or both:
  - *scheduled*: "Scheduled for 25-10-2026 · waiting for parts — <remark>";
  - *rescheduled*: "Plan changed: for 02-11-2026 · waiting for a production
    slot (was 25-10-2026 · waiting for parts) — <remark>". The old plan is
    read from the previous *scheduled* / *rescheduled* event.
- **On an overdue ticket, Change plan must set a new date** (BR2-07): the
  dialog opens with the past date, and the date rule refuses it ("The planned
  date cannot be before today") even when only the reason changes. That is
  intended: an overdue plan is no longer a plan.

### 5.3 Leaving scheduled

Whatever the move, `_apply_move` clears the plan columns when the ticket
leaves scheduled (§ 3, BR1-08).

- **Start** (`ticket:work`): the state goes to in progress.
  - On a ticket that is **not critical**, `machine_stopped` is required (400
    on `machine_stopped`: "Choose Yes or No"). The message has no tense, since
    one server message serves *Start* and *Back in service*; the question
    itself is the field's legend, worded per move on the page (§ 1.7, BR2-06).
    It is written on the *started* event.
  - On a critical ticket the question is not asked (the machine is already
    down), and a value sent is ignored.
  - Auto-assign as S018.
- **Back in service** from scheduled:
  - as S018, including the optional start time;
  - with a start time on a non-critical ticket, `machine_stopped` is required
    and goes on the *started* event written with it;
  - without a start time it is not asked: planned downtime is then unknown,
    as repair already is in that case (§ 5.4).
- **Not a fault** from scheduled: as S018.
- **Change severity** while scheduled: allowed (§ 1).
  - Raising to critical keeps the ticket scheduled: the machine stopped before
    its slot, and from that moment the stretch counts as downtime and waiting.
  - Lowering from critical ends the downtime as S018.

### 5.4 The times (`ticket_times(events, now)`)

S018 § 5.4 with these changes. The running state now includes `scheduled`,
and the reason in force is taken from the last *scheduled* / *rescheduled*
event.

- **response**: the first `acknowledged`, `started` or `scheduled`, minus
  `raised`.
- **repair**: an in-progress interval also ends at a `scheduled` event.
  `started` from scheduled opens a new one. **Back in service straight from
  scheduled with no start time makes repair `null`**, even when an earlier
  in-progress stretch was measured (started 10:00, scheduled for parts 12:00,
  back in service 15:00 with no start time): the last stretch of work is
  unknown, so the total is unknown, as S018 treats a restore with no start
  time (BR2-07).
- **downtime**: the critical intervals in raised, acknowledged, in progress or
  **scheduled**, to back in service. An open ticket counts to `now`.
- **waiting** (new): the sum of intervals while the state is scheduled **and**
  the intensity is critical (`waiting_minutes`), each attributed to the reason
  in force (`waiting_by_reason`, e.g. `{"parts": 4080}`; reasons not met are
  left out). The logistic and administrative totals are sums over
  `WAITING_REASONS`' delay kinds where they are shown; `other` is in neither.
  The waiting time is part of the downtime, never added to it. On a ticket that was never critical while
  scheduled it is `null`: a defect waiting for its slot is backlog, not
  delay. `waiting_by_reason` is `null` whenever `waiting_minutes` is `null`;
  the two are set or unset together (BR2-07).
- **planned downtime** (new): from a `started` event with `machine_stopped =
  1`, to the next `back_in_service`, a `scheduled` event or a change to
  critical, whichever comes first. An open interval counts to `now`. It is
  `null` when no such start exists.
- Not a fault: all null, as S018.
- Every interval is clamped at zero (S018 BR1-14).

### 5.5 Overdue

`is_overdue`: the state is scheduled and the planned date is before today (IST
date of `now`). A ticket is never overdue on its planned date itself. The list
filter puts the same rule in SQL: `t.state = 'scheduled' AND t.planned_date <
%s`, with today passed in.

### 5.6 Transactions and locks

As S018 § 5.3: each move is one transaction that locks the ticket row `FOR
UPDATE`, decides from the locked row, and writes the ticket and its event.

- The state change also takes the shared foreign-key locks on the machine,
  unit and component rows, as every move does (S025 CR1-02): `state` is in
  those foreign keys' indexes.
- S019 adds no explicit lock and no new lock-order edge. The two accepted
  deadlocks CR1-02 lists (a repeat raised against a send-back; a unit edit
  against a move in that unit) cover `schedule`, `reschedule` and the start
  from scheduled too.
- The coder adds the new moves to the lock-order note in `tickets.py`, in
  CR1-02's words, not "nothing else is locked" (BS1-01).

A *Change plan* on a ticket another user just started sees the new state and
gets 409 "This ticket changed — reload".

### 5.7 Permissions

No new key. The table of S018 § 5.7 is unchanged; the moves map to it as in
§ 1.2. A technician who finds the part missing schedules from in progress
(`ticket:work`); committing a slot from raised or acknowledged, and *Change
plan*, stay under `ticket:assign` (U1).

## 6. API

- `POST /api/tickets/<id>/moves/schedule`: `{planned_date, waiting_reason,
  occurred_at?, remark?}`.
- `POST /api/tickets/<id>/moves/reschedule`: the same body, with the remark
  required.
- `POST /moves/start` and `/moves/restore` take `machine_stopped?` (boolean).
  The move entry in the detail's `moves` carries `asks_machine_stopped: true`
  when the server will require it, so the page shows the question from data,
  not its own logic. On `restore` it means "ask once a start time is filled",
  since the server requires the answer only with a start time (BR1-10).
- The detail and list items gain `planned_date` (ISO date), `waiting_reason`
  and `overdue`. The detail's `times` gains `waiting_minutes`,
  `waiting_by_reason` and `planned_downtime_minutes` (BR1-07). Its events gain
  `planned_date`, `waiting_reason` and `machine_stopped`.
- `GET /api/tickets?state=scheduled|overdue`, beside `open`, `closed` and
  `all`, ordered as § 1.6.
- No new route: the reason labels live in `ticketLabels.js` (BR1-06).

## 7. Design decisions

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| 1 | **One `scheduled` state for deferred work and for waiting**, shown as *Scheduled* or *Waiting* by intensity | Both are "work held, with a reason and a date"; the intensity already says whether the machine is down, so the figures follow without a second state. One move set, one filter | Two states, `scheduled` and `waiting` (two sets of moves and labels for one idea; a defect that turns critical while scheduled would have to change state); a waiting *flag* while in progress (repair time would count the waiting, and that is the error EN 13306's split exists to avoid) |
| 2 | **Planned date required** | The point is that deferred work cannot be forgotten (the fleet case). A date makes *Overdue* possible, and *Change plan* records each slip with its reason | Optional date (a waiting-for-parts ticket with no date is exactly the forgotten one) |
| 3 | **Waiting reasons as a fixed list in code**, each mapped to EN 13306's logistic or administrative delay, `other` to neither | The split must stay comparable over the years. Six reasons cover the use cases (an expert is a resource, so logistic; a decision is administrative; BR1-01), and `other` with a remark catches the rest without inflating either total. A master would let the list drift and lose the mapping | A Masters list (engineers could add reasons, but each needs a delay kind and the reports would break on renames); free text (no split possible) |
| 4 | **Schedule from raised or acknowledged, and Change plan, under `ticket:assign`; Schedule from in progress under `ticket:work`** (U1); no new key | Committing a production slot is the engineer's call (Plan.MD § 4.2: "set by the engineer"). "Work stopped, waiting for parts" is the technician's fact on the floor, often at night; if only the engineer could record it, the wait would count as repair until the engineer arrives, the error this step removes. No RBAC change | (a) `ticket:assign` only (the wait counts as repair until the engineer comes); (c) technicians from any state (technicians would commit production slots); a new `ticket:schedule` key (the same holders, one more key to keep in step) |
| 5 | **Planned downtime only for a start from scheduled, by the technician's answer** | SMRP's planned work is work planned *before* it starts; the stop is planned only if the job was. Asking at start records the fact when it is known, without guessing. "Went through scheduled" stands in for SMRP's job plan, a stated proxy (§ 2, BR1-03) | Every stop on a non-critical ticket counts as planned (an on-the-spot fix with the machine stopped is reactive); planned downtime typed as a duration at close (a second, unchecked source beside the events) |
| 6 | **The plan on the ticket, the history on the events** | The list's filter and badge read one column with an index; the timeline shows every slip. The times read only the events, as in S018 | Plan only on events (the list would need the latest event per ticket, a subquery per row); plan only on the ticket (slips lost) |
| 7 | **Raising to critical keeps the ticket scheduled** | The part is still awaited; only the machine's state changed. The waiting split starts there by itself | Forcing it back to acknowledged (the reason and date are lost at the moment they matter most) |
| 8 | **Response counts *scheduled*** | Someone looked at it and decided; a ticket scheduled at once has been responded to | Only acknowledge / start (an engineer who schedules from raised would leave the response blank) |
| 9 | **The ENUM value appended, not inserted** | In-place change on MariaDB; nothing sorts by the ENUM's position (the list's `t.state = 'scheduled'` is a comparison) | Inserted after `acknowledged` (a table rebuild for no gain) |
| 10 | **Scheduled rows after the actionable ones within an intensity; the two filters by planned date** (BR1-04) | The open list is for people who act now; a waiting row can do nothing until its date. The planner of the week reads by date | Unchanged order (a waiting critical ticket leads every list for weeks); hiding scheduled rows from *open* (the forgotten-ticket problem again) |

## 8. Tests and acceptance

### Pure (`test_tickets_core.py`)

- `allowed_moves` for the new state and moves, by key set;
- `validate_move` for schedule and reschedule: missing date or reason,
  `other` without a remark, unknown reason;
- `planned_date_error`: yesterday refused, today accepted, 365 days accepted,
  366 refused;
- `machine_stopped_needed`: from scheduled and not critical → yes; critical →
  no; from acknowledged → no;
- `ticket_times`:
  - a defect scheduled, then started with *machine stopped*, then back in
    service: planned downtime set, downtime 0, waiting null;
  - the same with *not stopped*: planned downtime null;
  - a breakdown in progress, scheduled for parts, started again, back in
    service: repair excludes the waiting, downtime includes it, waiting
    logistic equals the scheduled stretch;
  - a reason changed by *Change plan* from `parts` to `slot`: the split
    follows the reason in force; an `other` stretch lands in
    `waiting_by_reason["other"]` only;
  - a defect scheduled, then raised to critical while scheduled: waiting from
    the re-grade;
  - a planned stop interrupted by a raise to critical: planned downtime ends,
    downtime starts;
  - response from a *scheduled* event; an open scheduled breakdown against
    `now`;
  - a breakdown started, scheduled for parts, then back in service from
    scheduled with no start time: repair `null` (BR2-07);
  - a ticket never critical while scheduled: `waiting_minutes` and
    `waiting_by_reason` both `null` (BR2-07);
- `is_overdue`: the day before, the day itself, the day after;
- `WAITING_REASONS` holds exactly the six codes with their delay kinds.

### API (`test_ticket_work_api.py`)

- schedule by an engineer from raised, acknowledged and in progress → 200,
  plan columns set, event written; **by a technician from in progress → 200,
  from acknowledged → 403** (U1); change plan by a technician 403; from back
  in service 409;
- change plan: date changed → 200 with the event; reason changed only → 200;
  nothing changed 400; without remark 400; from in progress 409; on an
  overdue ticket with only the reason changed → 400 on `planned_date`
  (BR2-07);
- start from scheduled on a defect: without `machine_stopped` 400, with it 200,
  the plan columns cleared, the event carries the answer; on a breakdown the
  answer is not required;
- back in service from scheduled, with and without a start time;
- not a fault from scheduled;
- the CHECK: a direct `UPDATE` setting scheduled without a date fails (the
  database's guard);
- schedule with a back-dated `occurred_at` and a planned date before today:
  400 (BR1-05);
- the list: `state=scheduled` and `state=overdue` (a ticket planned yesterday
  is in, today's is not), ordered by planned date; in `open`, a scheduled
  critical ticket after an acknowledged critical one; `planned_date` and
  `overdue` in the items;
- the detail: `asks_machine_stopped` on the start move only when needed;
  `times` with the new keys;
- access: the moves 404 outside the user's units, the keys checked at the
  ticket's site (as S018).

### Migration (`test_migration_v21.py`)

- In `vel_yantra_upgrade`, as S025's `test_migration_v20.py` does (BS1-02):
  1. Recreate the database and run `_MIGRATIONS` pinned to v20 alone.
  2. Insert the shortest chain a ticket needs: site, unit, equipment class,
     equipment, ticket and its raised event.
  3. Run v20 + v21.
  4. Check the row is unchanged, the columns, the ENUM with `scheduled`
     (still `NOT NULL DEFAULT 'raised'`) and `chk_tickets_plan`.
  5. Delete `db_version` 21 and run again: the re-run is harmless.
- Reuse `test_migration_v20.py`'s `_recreate`, `_migrate` and `_schema`:
  import them, or move them into one small `tests/upgrade_db.py`. Do not copy
  them. pytest runs the files one after another, so the two files share
  `vel_yantra_upgrade` without colliding.

### Automated (e2e, `tickets-work.spec.js`)

Important:
- an engineer schedules a defect for a date and reason: the badge reads
  *Scheduled*, the line under the header "for <date> · <reason>", and the
  timeline shows the line;
- **Change plan** with a remark: the timeline shows "Plan changed: … → …";
- a technician starts the scheduled defect and answers *Yes, machine
  stopped*, then back in service: the times card shows *Planned stop*;
- a breakdown in progress is scheduled for parts: the badge reads *Waiting*
  with "for parts"; after start and back in service the times card shows the
  waiting per reason;
- the list's *Overdue* filter shows a ticket planned in the past (seeded by
  SQL in `seed_e2e.py` on `E2E MCC1 mill`), with the red badge; the test runs
  as the engineer;
- the Schedule dialog, the *Change plan* dialog and the *Start* dialog with
  its Yes / No fit a phone (`expectDialogFits`) on the Pixel 7 and iPhone 14
  projects (BR1-15).

Plain:
- *Change plan* opens with the current date and reason; saving it unchanged
  shows "Nothing to change". This is a 400 from `/moves/reschedule`: the test
  declares `consoleWatch.allowFailedRequest("/moves/reschedule", 400)` and
  checks the message with `expectFieldMessage(dialog, "Nothing to change")`
  (BS1-03);
- choosing *Other* opens the remark as required;
- a technician sees no *Schedule* button on an acknowledged ticket, and sees
  it on a ticket in progress (U1).

Set-up for these tests goes through the API, not the screens (BS1-03):
`moveByApi("engineer", id, "schedule", {planned_date, waiting_reason})`, and
`moveByApi("technician", id, "acknowledge")` for the technician check. The
three projects share one database, so a test that counts tickets reads the
count first.

### On a real device

Important:
- [ ] On a phone (Android and iPhone), as an engineer: the date field of the
  Schedule dialog opens the phone's own date picker, and **after Save the
  page shows the chosen date as DD-MM-YYYY** (inside the picker the phone
  uses its own format, which Yantra does not control; BR1-15). Account: an
  engineer at SMTW; network: either; where: dev on KLA's laptop or production
  on the TEST machine.

### Acceptance

`tooling/run-tests.bat` green; `tooling/run-e2e-tests.bat` green; `npx vite
build` with no new errors.

## 9. Open questions and assumptions

Q1–Q4 and Q7 settled by the user at gate A (U1, 21-10-2026).

1. ~~Who may schedule?~~ Option (b): technicians (`ticket:work`) schedule
   **from in progress only**; Schedule from raised or acknowledged, and
   *Change plan*, stay `ticket:assign` (§ 1.2, § 5.1, § 7 decision 4).
2. ~~The screen word~~: **Waiting** on a critical ticket, *Scheduled* on a
   defect.
3. ~~The in-house workshop~~: not a waiting reason. Time in the workshop is
   active repair; a part queuing there for days is a `parts` wait.
4. ~~The planned-date limit~~: 365 days.
5. **Assumption:** an AMC vendor's visit (Atlas Copco asking for a filter
   change) is scheduled as `vendor` or `parts`, as the engineer judges; no
   special handling.
6. **Assumption:** escalation of unacknowledged breakdowns (S021) treats
   *scheduled* as acknowledged, since someone has decided. S021's draft
   already says "acknowledged" means the ticket has left raised, so the two
   agree.
7. ~~Standard numbers to check~~: the user has no copies of EN 13306 or
   SMRP's metrics (U1). This brief and the docs it changes cite them **by
   name only**. The MTTR number disagreement (3.5.5 in Maintenance-Philosophy
   and S018, 3.5.2 in S025) stays recorded here until a copy is checked.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 `expert` is a logistic delay; `other` fits neither | major | **Accepted** (option a): six reasons; `parts`, `vendor`, `expert` logistic; `slot`, `approval` administrative; `other` not classified, its own line in the reports (§ 1.4, § 4.1, § 5.4, § 7 decision 3) |
| BR1-02 EN 13306 and ISO 14224 citations | minor | **Accepted**: deferred corrective maintenance cited as Clause 7's entry and the time terms as Clause 9 / Annex A, both flagged to check against the copy; the five parts of time to restoration listed with Yantra's two accepted simplifications; the ISO 14224 claim reworded to down time and active maintenance time (§ 2, § 9 Q7) |
| BR1-03 SMRP names and the "scheduled = planned" proxy | minor | **Accepted**: planned/unplanned and reactive/proactive work named, the proxy stated as a deliberate departure, backlog in crew-weeks with backlog age as the plant's own measure, scheduled/unscheduled downtime, ISO 55001 § 8.1 added. Metric **numbers** are not cited (given from memory, unconfirmed); the MTTR number disagreement across the docs goes to § 3 Docs and § 9 Q7 (§ 2, § 7 decision 5) |
| BR1-04 list order | minor | **Accepted** (option a): scheduled rows after the actionable ones within an intensity; the two filters by planned date (§ 1.6, § 3, § 7 decision 10, § 8) |
| BR1-05 planned-date lower bound | minor | **Accepted** (option a): today only, `planned_date_error(planned, today)` (§ 1.8, § 3, § 5.1, § 8) |
| BR1-06 `GET /waiting-reasons` | minor | **Accepted** (option a): no endpoint; `WAITING_REASON_LABELS` in `ticketLabels.js`, the six codes asserted in both test suites (§ 3, § 6, § 8) |
| BR1-07 times card per reason | minor | **Accepted** (option a): `waiting_by_reason`; the delay totals summed from the fixed map where shown (§ 1.5, § 3, § 5.4, § 6) |
| BR1-08 clear the plan columns in one place | minor | **Accepted**: in `_apply_move` when leaving scheduled; the `start` step only returns `machine_stopped` (§ 3, § 5.3) |
| BR1-09 existing tests that break; the e2e seed | minor | **Accepted**: the four assertions listed as "change by design"; `seed_e2e.py` writes the overdue ticket by SQL (§ 3 Tests, § 8) |
| BR1-10 dialog details | minor | **Accepted**: *Change plan* prefilled; *Other* opens the remark; the stopped question on *Back in service* only once a start time is filled, and `asks_machine_stopped` says so; `asksStart` gains `scheduled` (§ 1.7, § 3, § 6, § 8) |
| BR1-11 index not needed | nit | **Accepted**: dropped (§ 4.1, § 8) |
| BR1-12 v21 is the next free number | nit | **Accepted**: S019 and S020 take v21 and v22 in coding order, as S020 says (Order, § 4) |
| BR1-13 one-word badge | nit | **Accepted**: *Scheduled* / *Waiting* / *Overdue*, date and reason on the line under the header (§ 1.1, § 1.7, § 8) |
| BR1-14 the stopped question's tense | nit | **Accepted**: "Is …" at *Start*, "Was …" at *Back in service* (§ 1.7) |
| BR1-15 device check wording; two dialog-fit checks | nit | **Accepted** (§ 8) |
| BR1-16 small implementation points | nit | **Accepted**: `ScheduleFields.vue` decided; S018's "Add a remark" with per-move labels; `_optional_date` shared with `validate_labour`; the ENUM `MODIFY` restates `NOT NULL DEFAULT`; old → new derived from the events (§ 1.7, § 3, § 4.3, § 5.1, § 5.2) |

Reviewer's notes on the open questions: Q1's middle option added to § 9 Q1 for
the user; Q2, Q3 and Q6 agreed, noted in § 9.

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 two more tests change by design | minor | **Accepted**: `test_migration_v12.py:63` gains `'scheduled'`; S025's v20 tests must build v20 alone, and S019 pins them if they run the full list, without loosening the assertions (§ 3 Tests) |
| BR2-02 the overdue e2e ticket | minor | **Accepted** (option a): raised and scheduled through the API, then one SQL `UPDATE` of `planned_date` to yesterday on the ticket and its event; pymysql with `config.DB_CONFIG` and `vel_yantra_e2e`; the test-only API hook rejected (§ 3 Tests) |
| BR2-03 `minutesText` has no days | minor | **Accepted** (option a): days from 24 h, minutes dropped once there are days, with its unit test; S018's sub-day assertions unchanged (§ 1.5, § 3 Tests) |
| BR2-04 `_LOCK_TICKET` columns | nit | **Accepted** (§ 3 Backend) |
| BR2-05 *Other* needs a remark: a body rule | nit | **Accepted**: checked in `validate_move` (§ 5.1) |
| BR2-06 tense in the server message | nit | **Accepted**: "Choose Yes or No"; the question is the field's legend per move (§ 5.3) |
| BR2-07 three points to state and test | nit | **Accepted**: repair `null` on a restore from scheduled with no start time; `waiting_by_reason` `null` with `waiting_minutes`; Change plan on an overdue ticket must set a new date (§ 5.2, § 5.4, § 8) |
| BR2-08 timeline shape; reason on the overdue line | nit | **Accepted**: "for <date> · <reason>" with "(was …)" on a change; "Overdue since <date> · <reason>" (§ 1.7, § 5.2) |
| BR2-09 button weight; the reason control | nit | **Accepted**: *Schedule* and *Change plan* in outline; the reason as a select (§ 1.7) |
| BR2-10 schedule compliance | nit | **Accepted**: named in § 2's SMRP bullet, number to check |

### U1 — user answers, 21-10-2026 (gate A)

"deffered work brief ok", "decisions as per suggested", "i dont have clause numbers" → approved 21-10-2026. Q1 option (b), the planner's gate recommendation: technicians schedule from in progress only (§ 1.2, § 3, § 5.1, § 5.7, § 7 decision 4, § 8). Q2 *Waiting* / *Scheduled*; Q3 no workshop reason; Q4 365 days; Q7 numbers by name only. Baseline from r2's *Reviewed against:*.

### Staleness check s1 — `2-brief-review-s1.md` (Fable), answered 22-10-2026

Against 3df667c + uncommitted S025. Verdict: no blocker or major.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 every move takes three shared FK locks | minor | **Accepted** (option a): § 5.6 reworded in CR1-02's words; the coder adds the new moves to the lock-order note |
| BS1-02 v21 and S025's migration rule; the "row from before" test | minor | **Accepted** (option a): v21 has no `_PRECONDITIONS` entry, said in § 4.3 and v21's comment; the test uses `vel_yantra_upgrade` with `test_migration_v20.py`'s helpers (§ 8); v20's header comment cited |
| BS1-03 e2e conventions; the seed's node and database | minor | **Accepted**: `allowFailedRequest` and `expectFieldMessage` for "Nothing to change"; the seed sets its database from `E2E_DATABASE` and runs `check_target`; the overdue ticket on `E2E MCC1 mill`, "E2E seed: overdue for parts"; set-up by `moveByApi` (§ 3 Tests, § 8) |
| BS1-04 the v20 pin is a fact | nit | **Accepted**: `V20 = [m for m in local_db._MIGRATIONS if m[0] == 20]`, assertions unchanged (§ 3 Tests) |
| BS1-05 the Order and Status lines | nit | **Accepted**: coded on top of uncommitted S025; the three steps committed together; `Baseline: 3df667c + uncommitted S025` |
| BS1-06 the first release applies v20–v22 | nit | **Accepted**: § 4.3; the coder changes S025's row 9 and impl-report check to "the latest schema version" |
| BS1-07 `test_migration_v12.py:63` moved | nit | **Accepted**: cited as `test_tables_and_indexes` |

