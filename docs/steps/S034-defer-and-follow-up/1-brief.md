Step: S034 — Defer, hold and follow-up date
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: light
Baseline: cbe8f02
Status: In review

# S034 — Defer, hold and follow-up date

**The request (KLA, 24-10-2026).** Three points about the ticket's *Schedule* button:

1. Shouldn't the button read *Defer*?
2. When a ticket waits for parts, how do we know the date?
3. Sometimes parts or a service take an indefinite time.

**Track: light.** No migration, no data change, no RBAC, no new endpoint, no new
dependency. The state, the moves, the keys and the figures of S019 stay the same. The step
changes words, the order of two fields and the meaning shown for the date. About 10 files.

## 1. What will be built

### 1a. Words by situation

The one `schedule` move of S019 covers two different situations. The words follow the
ticket's intensity, as *Back in service* already reads *Fixed* on a defect
(`moveLabel()`):

| | Defect (degraded, initial) | Breakdown (critical) |
|---|---|---|
| Button and dialog Save (`schedule`) | **Defer** (was *Schedule*) | **Put on hold** (was *Schedule*) |
| State badge | **Deferred** (was *Scheduled*) | **Waiting** (unchanged) |
| Badge past the date | **Overdue** (unchanged) | **Overdue** (unchanged) |

Words that cover both situations use **On hold**:

| Place | Was | Now |
|---|---|---|
| Ticket list filter (`STATE_FILTERS`) | Scheduled | **On hold** |
| `STATE_LABELS.scheduled` (any fallback use) | Scheduled | **On hold** |
| Timeline event `scheduled` (frontend `EVENT_LABELS`) | Scheduled | **On hold** |
| Backend `EVENT_LABELS[SCHEDULED_EVENT]` (named in a refused time: "must be after …") | Scheduled | **On hold** |

*Change plan* (`reschedule`) and its timeline line *Plan changed* stay as they are.

### 1b. The date means "planned" or "check again", by reason

The waiting reason decides what the date means. A pure helper `planDateKind(reason)` in
`ticketLabels.js` returns one of two kinds:

| Reason | Kind | Why |
|---|---|---|
| `slot` (production slot or shutdown) | **planned** | Maintenance and production choose the slot. The date is a commitment. |
| `parts`, `vendor`, `expert`, `approval`, `other` | **check** | Someone outside maintenance controls the end of the wait. The date is when someone must chase it. |

What each kind shows:

| | planned | check |
|---|---|---|
| Date field label | **Planned for** | **Check again by** |
| Help under the date field | — | "When should someone chase this? Use the supplier's date if you have one." |
| Plan line (ticket header, list row) | for 25-10-2026 · waiting for a production slot (unchanged) | **check by** 25-10-2026 · waiting for parts |
| Plan line past the date | Overdue since 25-10-2026 · … (unchanged) | **Check due since** 25-10-2026 · … |
| Timeline (`planChanges`) | for 25-10-2026 · … (was …) (unchanged) | **check by** 25-10-2026 · … (was …) |

The badge and the *Overdue* filter stay one word for both kinds (§ 4.4).

### 1c. The dialog

- **The reason comes first, then the date** in `ScheduleFields.vue`, so the date's label
  and help are right before the user reaches the date. Was: date first.
- Before a reason is chosen, the date field reads **Date**.
- **Quick-pick buttons** under the date: **+7 days**, **+14 days**, **+30 days**. A tap
  fills the date with today plus that many days (the phone's local date, as the date
  input's `min` already uses). The date still opens empty, so a choice is still needed (S019
  decision 2 kept). The user can still type any date from today to a year ahead.

### 1d. Backend messages

The date's refusals no longer say "planned date", because the field is not always called
that:

| Constant | Was | Now |
|---|---|---|
| `PLANNED_DATE_NEEDED` | Choose the planned date | **Choose a date** |
| `PLANNED_DATE_PAST` | The planned date cannot be before today | **The date cannot be before today** |
| `PLANNED_DATE_TOO_FAR` | Plan within a year | **Choose a date within a year** |

**Out of scope:**

- an optional date or an "unknown" choice (§ 4.3);
- a link to OneERP purchase or material requests, so the date comes from the order (the
  spares phase; until then the PO or indent number goes in the remark);
- an automatic reminder or push when a check date passes (the *Overdue* filter and the red
  badge stay the signal; S021 alerts are unchanged);
- marking equipment out of service when a breakdown waits for months (S030 *Lifecycle*,
  by hand as today);
- the database names (`scheduled` state, `planned_date`, `schedule` / `reschedule` moves)
  and the API, which stay as they are.

## 2. Standards and practice

- **EN 13306:2017 — deferred corrective maintenance**: corrective maintenance that is not
  done at once after the fault is found, but delayed by a maintenance decision. *Defer* is
  the standard's word for the defect case. A breakdown waiting for parts is not a decision
  to delay: EN 13306 calls that time a **logistic delay** (or an **administrative delay**).
  So that case reads *Put on hold* and *Waiting*, not *Defer*.
- **SMRP backlog management**: work waiting for materials is still backlog, and the plant
  reviews it on a fixed cycle. Many CMMSs show it as a *waiting for materials* status. The
  "check again by" date is that review cycle per ticket. It turns an indefinite wait into a
  dated action, and each *Change plan* records the slip with its reason. In time, this
  shows which parts and suppliers cause the long waits.

## 3. Where

| File | Change |
|---|---|
| `frontend/src/utils/ticketLabels.js` | `MOVE_LABELS` / `SAVE_LABELS` and `moveLabel()` / `moveSaveLabel()`: `schedule` by intensity (§ 1a); `STATE_LABELS`, `STATE_FILTERS`, `EVENT_LABELS`: *On hold*; `stateLabel()`: *Deferred* on a defect; new `planDateKind(reason)`, `planDateLabel(reason)`, `PLAN_DATE_HELP`, `PLAN_QUICK_DAYS = [7, 14, 30]`; `planText()`, `planLine()`, `planChanges()`: the *check* wording (§ 1b) |
| `frontend/src/views/tickets/ScheduleFields.vue` | reason before date; the date's label and help from the reason; the three quick-pick buttons |
| `frontend/src/views/TicketDetailView.vue` | the header comment (S019 wording); the code already calls `moveLabel(m.name, ticket.intensity)` and `stateLabel(ticket)` |
| `frontend/src/views/TicketsView.vue` | the header comment; `planText()` keeps its signature |
| `backend/tickets_core.py` | the three date messages (§ 1d); `EVENT_LABELS[SCHEDULED_EVENT]` = "On hold" |
| `backend/tests/test_ticket_work_api.py` | the literal messages at lines 1020, 1023, 1079 |
| `frontend/tests/ticketLabels.test.js` | new and changed label tests (§ 5) |
| `frontend/e2e/tickets-work.spec.js` | the S019 tests use the new button, badge and line texts; new S034 tests (§ 5) |
| `docs/Maintenance-Philosophy.md` § 7 *Deferred corrective maintenance* | the words *Deferred* / *Waiting* / *On hold* and the check date |
| `docs/Plan.MD` § 4.2 *Deferred work* | "shown as *Scheduled*" → the new words; a line for S034 |

No change: `MoveDialog.vue` (its title and Save already call `moveLabel()` / `moveSaveLabel()` with the ticket's intensity, lines 184 and 188) and `backend/tests/test_tickets_core.py` (it imports the constants). `frontend/tests/ticketLabels.test.js` also tests `STATE_LABELS`; those assertions change with § 1a.

## 4. Design decisions

1. **Words by intensity, not one new word.** *Defer* is the EN 13306 word for a defect, but
   wrong for a stopped machine waiting for parts. The badge already splits the two cases
   (*Scheduled* / *Waiting*). Rejected: *Defer* everywhere (it hides that a breakdown wait
   is not a choice); *Put on hold* everywhere (it loses the standard term for the defect
   case).
2. **The date's meaning comes from the reason.** Only a production slot is a date that
   maintenance commits to. Every other reason waits on someone else, so its date is a
   follow-up. Rejected: a separate "date kind" choice in the dialog (one more question on a
   phone, and users would pick it at random); a second date column (a migration for the
   same information).
3. **The date stays required.** An indefinite wait is the case where a date matters most.
   Without one, the ticket is forgotten, which is the problem S019 decision 2 exists to
   prevent. The quick picks make it cheap to give a follow-up date without inventing a
   delivery promise. Rejected: an optional date or an "unknown" choice (a parts wait with
   no date drops out of *Overdue*, and nobody chases it).
4. **The badge stays *Overdue* for both kinds** (assumption, § 6): one word, one filter.
   *Overdue* still means "someone owes an action now": do the work, or chase and change the
   plan. The plan line says which (*Overdue since* / *Check due since*). Rejected: a second
   badge word *Check due* (two words for one filter).
5. **Labels only in the frontend; backend names unchanged.** The state `scheduled` and the
   moves stay, so there is no migration and no API change. The backend changes only the
   texts a user sees (§ 1d).

## 5. Tests and acceptance

**Unit (vitest)**, `frontend/tests/ticketLabels.test.js`:

- `moveLabel("schedule", "degraded")` and `("schedule", "initial")` → *Defer*;
  `("schedule", "critical")` → *Put on hold*; the same for `moveSaveLabel`;
- `stateLabel`: scheduled defect → *Deferred*; scheduled breakdown → *Waiting*; overdue →
  *Overdue* (the existing test changes from *Scheduled*);
- `planDateKind`: `slot` → planned; the five other codes → check; the test lists all six
  codes, so a new reason must pick a kind;
- `planText`, `planLine`, `planChanges` for one *planned* and one *check* reason, also past
  the date;
- `STATE_FILTERS` holds *On hold*.

**Backend**: the three changed messages in `test_ticket_work_api.py`. No new backend test.

**Automated (browser)**, `tickets-work.spec.js`, names `S034: …`; run targeted
`tickets-work.spec.js` + `screens.spec.js`:

- **important**: on a defect the button reads *Defer*; after saving, the badge reads
  *Deferred* and the timeline line *On hold*;
- **important**: on a breakdown in progress the button reads *Put on hold*; with *Waiting
  for parts* the date is labelled *Check again by* with the help; the plan line reads
  "check by …";
- with *Waiting for a production slot* the date is labelled *Planned for*;
- **+14 days** fills the date with today plus 14 days, and the save succeeds;
- the reason select is above the date in the dialog;
- the ticket list filter reads *On hold* and lists the held ticket;
- the S019 tests that look up *Schedule* / *Scheduled* now use the new words, and still
  pass.

**On a real device:** none. The date input itself is S019's open row 10.

## 6. Open questions and assumptions

1. **Question: the words.** *Defer* / *Deferred* for a defect and *Put on hold* /
   *Waiting* for a breakdown, with *On hold* where both meet. **Recommended:** as written.
   Option: *Hold* instead of *Put on hold*, which is shorter on a phone button but less
   clear.
2. **Question: is *approval* a "check" reason?** Waiting for a decision is outside
   maintenance's control, so the brief makes it *check*. Option: *planned*, if the plant
   treats approvals as booked dates. **Recommended:** check.
3. **Assumption** (§ 4.4): the badge stays *Overdue* for both kinds.
4. **Assumption**: the quick picks are 7, 14 and 30 days. Option: 3, 7 and 14, if the
   plant chases parts more often.
5. **Assumption**: a regraded ticket (defect ↔ breakdown) simply shows the words of its
   current intensity. Past timeline lines use the neutral *On hold*, so history never
   contradicts itself.

## 7. Amendments

None.

## 8. Review log

None yet.
