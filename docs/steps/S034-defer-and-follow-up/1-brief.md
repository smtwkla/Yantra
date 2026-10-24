Step: S034 — Defer, hold and follow-up date
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026 (revised 24-10-2026: brief-review r1)
Track: light
Baseline: 7a5b726 (code as cbe8f02)
Status: Gate B (CR r1: 0 blocker, 0 major, 1 minor, 4 nits; approved 24-10-2026 by KLA)

# S034 — Defer, hold and follow-up date

**The request (KLA, 24-10-2026).** Three points about the ticket's *Schedule* button:

1. Shouldn't the button read *Defer*?
2. When a ticket waits for parts, how do we know the date?
3. Sometimes parts or a service take an indefinite time.

**Track: light.** No migration, no data change, no RBAC, no new endpoint, no new
dependency. The state, the moves, the keys and the figures of S019 stay the same. The step
changes words, the order of two fields and the meaning shown for the date. About 12 files.

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

Where both situations meet (BR1-04):

| Place | Was | Now |
|---|---|---|
| Ticket list filter (`STATE_FILTERS`) | Scheduled | **Deferred / Waiting**: the two badge words a user scans for on the rows |
| `STATE_LABELS.scheduled` (fallback only) | Scheduled | **On hold** |
| Timeline event `scheduled` (frontend `EVENT_LABELS`) | Scheduled | **On hold** |
| Backend `EVENT_LABELS[SCHEDULED_EVENT]` (named only in a refused time: "Must be at or after On hold, …") | Scheduled | **On hold** |

The timeline line is neutral because a ticket can be regraded later: a past line must not
say *Deferred* on what is now a breakdown (§ 6.5).

*Change plan* (`reschedule`) keeps its button word and its timeline line *Plan changed*.
Its dialog uses the same `ScheduleFields.vue`, so it gets the reason-first order, the date
label by reason, the help and the quick picks of § 1c too. Its reason is prefilled, so the
date label is right at once (BR1-10).

### 1b. The date means "planned" or "check again", by reason

The waiting reason decides what the date means. A pure helper `planDateKind(reason)` in
`ticketLabels.js` returns one of two kinds. It is a third grouping of the reasons, beside
the reason labels and EN 13306's delay kinds (`WAITING_REASON_DELAYS`): *approval* is an
administrative delay, but its date is a *check* date.

| Reason | Kind | Why |
|---|---|---|
| `slot` (production slot or shutdown) | **planned** | Maintenance and production choose the slot. The date is a commitment. |
| `parts`, `vendor`, `expert`, `approval`, `other` | **check** | Someone outside maintenance controls the end of the wait. The date is when someone must follow it up. |

What each kind shows:

| | planned | check |
|---|---|---|
| Date field label | **Planned for** | **Check again by** |
| Help under the date field | — | "When should someone follow this up? If the supplier gave a date, use it." |
| Header line (`planLine()`), before the date | for 25-10-2026 · waiting for a production slot (unchanged) | **check by** 25-10-2026 · waiting for parts |
| Header line (`planLine()`), past the date | Overdue since 25-10-2026 · … (unchanged) | Overdue since 25-10-2026 · … (unchanged, BR1-05) |
| List row (`planText()`, `TicketsView.vue` line 199) | … · for 25-10-2026 · waiting for a production slot (unchanged) | … · **check by** 25-10-2026 · waiting for parts |
| List row of an overdue ticket | Overdue · for 25-10-2026 · … (unchanged) | Overdue · **check by** 25-10-2026 · … |
| Timeline (`planChanges()`) | for 25-10-2026 · … (was …) (unchanged) | **check by** 25-10-2026 · … (was …) |

So only the words before the date change by kind ("for" / "check by"). Past the date, both
kinds read *Overdue*, in the badge, the filter and the header line (§ 4.4). The list row's
red badge (`overdueBadge()`) is unchanged.

### 1c. The dialog

- **The reason comes first, then the date** in `ScheduleFields.vue`, so the date's label
  and help are right before the user reaches the date. Was: date first.
- Before a reason is chosen, the date field reads **Date**.
- **Quick-pick buttons** under the date: **In 7 days**, **In 14 days**, **In 30 days**
  (BR1-08: they name the date they give). A tap fills the date with today plus that many
  days, in the phone's local date, as the date input's `min` already uses
  (`toLocalDateValue(new Date())`). The date still opens empty on *Defer* / *Put on hold*,
  so a choice is still needed (S019 decision 2 kept). The user can still type any date from
  today to a year ahead.

### 1d. Date messages

The date's refusals no longer say "planned date", because the field is not always called
that:

| Where | Was | Now |
|---|---|---|
| `tickets_core.PLANNED_DATE_NEEDED` | Choose the planned date | **Choose a date** |
| `tickets_core.PLANNED_DATE_PAST` | The planned date cannot be before today | **The date cannot be before today** |
| `tickets_core.PLANNED_DATE_TOO_FAR` | Plan within a year | **Choose a date within a year** |
| `MoveDialog.vue` `missingField()`, line 139 (the message shown first on an empty date, BR1-01) | Choose the planned date | **Choose a date** |

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
  So that case reads *Put on hold* and *Waiting*, not *Defer*. A defect that waits for parts
  is both: deferred by decision, then held by a logistic delay. Its waiting time already
  falls in the S019 split.
- **SMRP Best Practices — planned backlog and ready backlog**: *planned backlog* is work
  that has a plan; *ready backlog* is planned work whose materials are on hand. A ticket
  waiting for parts is in the planned backlog, but not in the ready backlog. SMRP practice
  is to review the not-ready work on a fixed cycle. The "check again by" date is that review
  per ticket. It turns an indefinite wait into a dated action, and each *Change plan*
  records the slip with its reason. In time, this shows which parts and suppliers cause the
  long waits.

## 3. Where

| File | Change |
|---|---|
| `frontend/src/utils/ticketLabels.js` | `MOVE_LABELS` / `SAVE_LABELS` and `moveLabel()` / `moveSaveLabel()`: `schedule` by intensity (§ 1a); `STATE_FILTERS`: *Deferred / Waiting*; `STATE_LABELS`, `EVENT_LABELS`: *On hold*; `stateLabel()`: *Deferred* on a defect; new `planDateKind(reason)`, `planDateLabel(reason)`, `PLAN_DATE_HELP`, `PLAN_QUICK_DAYS = [7, 14, 30]`; `planText()`, `planChanges()`: "check by" for the *check* kind; `planLine()`: the same before the date, unchanged past it (§ 1b) |
| `frontend/src/views/tickets/ScheduleFields.vue` | reason before date; the date's label and help from the reason; the three quick-pick buttons; the header comment |
| `frontend/src/views/tickets/MoveDialog.vue` | `missingField()` line 139: "Choose a date" (§ 1d); the header comment (lines 17–21, S019 wording). Its title and Save already call `moveLabel()` / `moveSaveLabel()` with the ticket's intensity (lines 184, 188), so they need no change |
| `frontend/src/views/TicketDetailView.vue` | the header comment (S019 wording); the code already calls `moveLabel(m.name, ticket.intensity)` and `stateLabel(ticket)` |
| `frontend/src/views/TicketsView.vue` | the header comment; `planText()` keeps its signature |
| `backend/tickets_core.py` | the three date messages (§ 1d); `EVENT_LABELS[SCHEDULED_EVENT]` = "On hold" |
| `backend/tests/test_ticket_work_api.py` | the literal messages at lines 1020, 1023, 1025 and 1079 (BR1-07) |
| `frontend/tests/ticketLabels.test.js` | new and changed label tests (§ 5), including the `STATE_LABELS` and `stateLabel` assertions |
| `frontend/e2e/tickets-work.spec.js` | the S019 tests use the new words (§ 5); new S034 tests |
| `docs/steps/device-checks.md` row 10 (S019, open) | the new words: press **Defer**, choose *Waiting for parts*, tap **Check again by**, press **Defer**; the page shows "check by DD-MM-YYYY · waiting for parts" (BR1-03) |
| `docs/Maintenance-Philosophy.md` § 7 *Deferred corrective maintenance* | the words *Deferred* / *Waiting* / *On hold* and the check date |
| `docs/Plan.MD` § 4.2 *Deferred work* | "shown as *Scheduled*" → the new words; a line for S034 |

No change: `backend/tests/test_tickets_core.py` (it imports the constants).

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
   no date drops out of *Overdue*, and nobody follows it up).
4. **One word past the date: *Overdue*, for both kinds** (BR1-05). *Overdue* means
   "someone owes an action now": do the work, or follow up and change the plan. The reason
   on the same line says which. Rejected: a second phrase *Check due since* (hard to read,
   and two words for one filter).
5. **The filter names the two badges** (BR1-04): *Deferred / Waiting*, so a user finds the
   words the rows show. *On hold* stays on the breakdown button and the neutral timeline
   line. Rejected: *On hold* on the filter too (a third word a user must map to the rows).
6. **Labels only in the frontend; backend names unchanged.** The state `scheduled` and the
   moves stay, so there is no migration and no API change. The backend changes only the
   texts a user sees (§ 1d).

## 5. Tests and acceptance

**Unit (vitest)**, `frontend/tests/ticketLabels.test.js`:

- `moveLabel("schedule", "degraded")` and `("schedule", "initial")` → *Defer*;
  `("schedule", "critical")` → *Put on hold*; the same for `moveSaveLabel`;
- `stateLabel`: scheduled defect → *Deferred*; scheduled breakdown → *Waiting*; overdue →
  *Overdue* (the existing test at line 181 changes from *Scheduled*);
- `planDateKind`: `slot` → planned; the five other codes → check; the test lists all six
  codes, so a new reason must pick a kind;
- `planText`, `planLine`, `planChanges` for one *planned* and one *check* reason; `planLine`
  past the date reads *Overdue since* for both;
- `STATE_FILTERS` holds *Deferred / Waiting*; `STATE_LABELS.scheduled` and
  `EVENT_LABELS.scheduled` are *On hold*.

**Backend**: the four changed message literals in `test_ticket_work_api.py`. No new backend
test.

**Automated (browser)**, `tickets-work.spec.js`, names `S034: …`; run targeted
`tickets-work.spec.js` + `screens.spec.js`. The dialog fit is checked by `openAction()`
(`expectDialogFits`).

- **important**: on a defect the button reads *Defer*; after saving, the badge reads
  *Deferred* and the timeline line *On hold*;
- **important**: on a breakdown in progress the button reads *Put on hold*; with *Waiting
  for parts* the date is labelled *Check again by* with the help; the header line reads
  "check by …";
- with *Waiting for a production slot* the date is labelled *Planned for*;
- **In 14 days** fills the date, and the save succeeds. The expected value is read the way
  the component makes it: the date input's `min` plus 14 days, not `istDay(14)` (BR1-09:
  the laptop's local date and IST can differ near midnight);
- the reason select is above the date in the dialog;
- the ticket list filter reads *Deferred / Waiting* and lists the held ticket.

S019 assertions that change by design (the coder updates them; they must pass):

- line 323 and 334 `Schedule` → *Defer*; line 336 and 368 badge `Scheduled` → *Deferred*;
  line 338 timeline `/^\s*Scheduled/` → *On hold* (the reason there is `slot`, so the text
  after it stays "for …");
- line 395 and 400 `Schedule` → *Put on hold* (a breakdown);
- line 402, the breakdown waiting for parts: the plan line "for … · waiting for parts"
  → "check by … · waiting for parts";
- line 426–428, the *Overdue* filter row: "Overdue · for … · waiting for parts" →
  "Overdue · check by … · waiting for parts" (the red badge "Overdue since …" unchanged);
- line 431 and 439, the technician test on an acknowledged **defect**: the button name
  `Schedule` → *Defer*. This assertion is `toHaveCount(0)`, so it would still pass, and
  check nothing, if the old word were left: the coder changes it, and the S034 defect test
  shows *Defer* is visible to the engineer, so the word is proven right.

**On a real device:** none new. S019's open row 10 gets the new words (§ 3).

## 6. Open questions and assumptions

1. **Question: the words.** *Defer* / *Deferred* for a defect; *Put on hold* / *Waiting*
   for a breakdown; filter *Deferred / Waiting*; timeline *On hold*. **Recommended:** as
   written. Options: *Hold* instead of *Put on hold* (shorter on a phone button, less
   clear); *On hold* on the filter instead of *Deferred / Waiting* (the first draft; one
   more word for the user to map).
2. **Question: is *approval* a "check" reason?** Waiting for a decision is outside
   maintenance's control, so the brief makes it *check*. Option: *planned*, if the plant
   treats approvals as booked dates. **Recommended:** check.
3. **Assumption** (§ 4.4): *Overdue* for both kinds past the date.
4. **Assumption**: the quick picks are 7, 14 and 30 days. Option: 3, 7 and 14, if the
   plant follows parts up more often.
5. **Assumption**: a regraded ticket (defect ↔ breakdown) shows the words of its current
   intensity. Past timeline lines use the neutral *On hold*, so history never contradicts
   itself.

## 7. Amendments

None.

## 8. Review log

| ID | Severity | Answer |
|---|---|---|
| BR1-01 | minor | Accepted: `MoveDialog.vue` `missingField()` line 139 → "Choose a date", and its header comment, in § 1d and § 3; `ScheduleFields.vue`'s header comment in § 3. |
| BR1-02 | minor | Accepted: § 1b now separates the header line (`planLine()`) and the list row (`planText()`), with the overdue list row's text; § 5 names the S019 assertions at lines 401 and 426–428, and the others that change. |
| BR1-03 | minor | Accepted: `device-checks.md` row 10 added to § 3 with its new words. |
| BR1-04 | minor | Accepted, option (b): the filter reads *Deferred / Waiting*; *On hold* stays on the button and the timeline (§ 1a, § 4.5). Put to the user in § 6.1. |
| BR1-05 | minor | Accepted, option (a): *Overdue since* for both kinds; only "for" / "check by" differs before the date (§ 1b, § 4.4). |
| BR1-06…BR1-10 | nit | Accepted: SMRP stated as planned and ready backlog, and the deferred-plus-logistic case (§ 2); line 1025 added (§ 3); buttons *In 7 / 14 / 30 days*; help text "follow this up", and the e2e date read from the input's `min` (§ 5); *Change plan* shares `ScheduleFields.vue` (§ 1a). |
