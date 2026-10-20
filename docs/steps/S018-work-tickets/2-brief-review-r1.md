```
Step: S018 — Work the ticket
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016 + the S017 brief (`docs/steps/S017-raise-tickets/1-brief.md`, In review 20-10-2026; no S017 code exists yet)

# S018 — Brief review, round 1

**Verdict: one `major` finding is open (BR1-01, the send-back intensity rule and
its event).** The shape of the step holds: the moves as data in the pure core,
one locked transaction per move on the ticket row (7) last in the global order,
times computed from the events and never stored, the four `ticket:*` keys in
`SITE_SCOPED` with the grantees Plan.MD § 3 gives, labour required at close and
not at back in service, "not fixed" as a linked new ticket. The findings are:
one gap in the rules that feed the downtime figure; a handful of rules the coder
would otherwise settle alone (re-grade direction, trade on a labour row, the
repeat window, who is "me"); two things S017 does not provide; two pieces of
over-engineering; and standards wording, including a conflict between
`Maintenance-Philosophy.md` § 10 and Plan.MD Q4 on what MTTR means. Full track.

**Where S018 leans on S017** (the orchestrator asked). S017 provides what S018
assumes: `FUTURE_SKEW` and `MAX_BACKDATE_DAYS`, the full `state` ENUM, `tickets.unit_id`
kept at raise, `ticket_events.intensity` and `person_id`, the closed rule in
documents.py, the mode-code freeze pattern. S018 itself extends S017's raise
route (`repeat_of_id`) and detail, and says so. What neither brief provides:
the event `intensity` in S017's event shape (BR1-12), a public "the user's own
person" helper (BR1-11), and a one-place people picker (BR1-10). If open
question 2 is answered yes, `documents.py` does change (the lock function
checks `ticket:raise`; S018 would want `ticket:work`), so § 3's "no change"
is conditional.

## Findings

### BR1-01 · major · Send back: the intensity rule is incomplete, and the event that carries it is written only in the "down" case

**Problem.** § 1 *Send back*: "yes keeps or sets the intensity critical …; no
sets it degraded". § 4.3: "A send-back with the machine down writes `sent_back`
and, when the intensity changes, a `regraded` at the same time." Two gaps:

1. **"No" on an `initial` ticket re-grades it to `degraded`.** The intensity is
   the operator's failure-impact grade (ISO 14224: critical / degraded /
   incipient; Plan.MD § 4.2, decided 15-10-2026). A send-back with the machine
   running says nothing about how bad the fault is; turning an early sign into
   "running with reduced function" invents a grade nobody gave. The rule should
   be: *yes* → critical (a change when it was not); *no* → degraded **only
   when it was critical**, else unchanged.
2. **The event is stated only for the "down" case.** § 5.4 computes downtime
   from the events' `intensity` column alone ("each event's `intensity`: set on
   `raised` and on every `regraded`, NULL when unchanged"). If a coder follows
   § 4.3 literally and, for "no" on a critical ticket, updates
   `tickets.intensity` to degraded without an event carrying it, `ticket_times`
   keeps counting downtime through the second repair, and the first figure of
   phase 3 is wrong on exactly the tickets an engineer sent back.

**Why it matters.** The orchestrator asked for the time computations to be
checked; this is the one place the stored state and the event log can drift.
Decision 5's whole reason ("one source of truth") depends on every intensity
change reaching the events.

**Options.** (a) State the rule in § 1 and § 5.2 as in point 1, and in § 4.3:
"every change of intensity, whichever move causes it, is written to the
`intensity` column of the event of that move; `ticket_times` reads nothing
else" — and put it on the `sent_back` event itself rather than a paired
`regraded` (S017 § 4.1 designed the column as "the intensity set by this event,
NULL when unchanged"; one timeline line reads better than "Sent back" plus
"Breakdown → Defect" at the same minute) — **recommended**; (b) keep the paired
`regraded` but write it for both directions — acceptable; (c) keep the text —
not acceptable, the computation is under-specified.

### BR1-02 · minor · Re-grade: direction, actor and the no-change case are not settled

**Problem.** § 1 *Re-grade* describes the upward case only ("a defect that gets
worse becomes critical"); § 6 `POST /regrade {intensity, …}` accepts any value;
§ 5.3 keys it to `ticket:raise`. Not said: may an operator lower a ticket from
critical to degraded (which **ends downtime**); is re-grading to the same
intensity a 400; must a remark be given.

**Why it matters.** A wrongly ticked "critical" (the machine never stopped)
counts downtime until back in service unless someone can lower it; but
lowering is a maintenance judgement, and an operator lowering his own breakdown
to "running" silently removes downtime from the record. Each is a rule the
coder would otherwise pick.

**Options.** (a) Both directions, with the event time rule; raising by
`ticket:raise` (the operator sees the machine stop); **lowering by
`ticket:work`** with a remark required (it is the technician who says the
machine runs); same intensity → 400 — **recommended**; (b) upward only in
S018, a wrong critical corrected by the engineer at close via a later
"correct an event" step — simpler but leaves wrong downtime on the record for
weeks; (c) any direction by `ticket:raise` with remark — simplest, accepts the
risk.

### BR1-03 · minor · Back in service: write the key rule the way `MOVES` will hold it, and say what happens with no Team record

**Problem.** The § 1 table says `ticket:work`, "or `ticket:restore` naming the
technician". But `ticket:restore` is granted to `maint_operator` and the ladder
inherits it (§ 5.7, `ROLE_INCLUDES`), so **every `ticket:work` holder also holds
`ticket:restore`**; the move has one key. The actual rule (§ 5.2) is: key
`ticket:restore`; `person_id` required unless the user holds `ticket:work` at
the site, in which case it defaults to the user's own person. `allowed_moves`
and the detail's `moves` must also tell the page whether the dialog needs a
person (a supervisor's dialog shows the picker, a technician's shows himself).

Two edge cases: a `ticket:work` holder with no Team record (admin, IT admin
never has the key; in tests the harness users have no `people` row unless the
test creates one) — is `person_id` then NULL or required? And the `started`
event written with `started_at` — it should carry the same `person_id` as the
`back_in_service` event, so the timeline says who started.

**Options.** (a) Rewrite the table row as "`ticket:restore`; names the
technician (`person_id`), defaulting to the user's own person for `ticket:work`
holders"; `moves` entries carry `needs_person`; a holder with no Team record
must name someone (never a NULL technician on a restoration — ISO 14224 records
who did the work); the `started` event carries the same person —
**recommended**.

### BR1-04 · minor · `test_rbac.py::test_role_matrix` breaks; name the rows (S016 BR1-04 precedent)

**Problem.** § 3 says "`test_rbac.py` — the four keys". The existing
`TestComputePermissions.test_role_matrix` (`backend/tests/test_rbac.py`
lines 134–151) asserts each role's **exact** set. The four keys change the rows
of operator, supervisor, technician, engineer and manager (`ticket:restore`
reaches all five; `ticket:work` three; `ticket:assign` and `ticket:close` two).
S017's `ticket:read` / `ticket:raise` change the same five rows first, so S018's
edit stacks on S017's.

`test_supervisor_is_off_the_maintenance_ladder` still holds (the supervisor's
set equals the operator's, since `ticket:restore` is granted to the operator
and nothing to the supervisor alone) — worth saying, since it is the test that
guards the "supervisor does not work tickets" decision.

**Options.** (a) Name the test and the five rows in § 8 *RBAC*, and add a
holders test per key on the `test_failure_codes_edit_holders` pattern, with
`in SITE_SCOPED` — **recommended**.

### BR1-05 · minor · Default event time and phone clocks: say the dialog sends no time when the user left "now"

**Problem.** § 5.1 refuses an event time before the ticket's latest event.
S017's raise dialog fills the time input with the phone's clock and sends it
(S017 § 3, "date-time input, default now"); `FUTURE_SKEW` of 5 minutes exists
because phones drift. So: a technician whose phone runs 4 minutes fast
acknowledges at "10:04" (really 10:00); the engineer presses *Start* at
10:02 real time, his dialog sends 10:02 → "before the last event", on a
ticket nobody back-dated. The floor will hit this.

**Why it matters.** The event-order rule is right (the times must be
computable); the default should not fight it.

**Options.** (a) The move dialogs (and S017's raise dialog, by the same rule)
send **no `occurred_at`** when the user did not touch the time, so the server's
clock is the default; a typed time is validated as § 5.1 says, and the refusal
names the last event and its time ("must be at or after *Acknowledged*,
20-10-2026 10:04") — **recommended**; (b) accept a default up to `FUTURE_SKEW`
before the last event by clamping it to the last event's time — hides the
skew, but a clamped time is a guess. Also say plainly, as an accepted
consequence: an operator who re-grades at "09:30" after the technician
acknowledged at 09:40 must enter 09:40 or later (downtime starts there).

### BR1-06 · minor · Decision 5 relies on correcting event times, which the brief gives no way to do

**Problem.** Decision 5's reason: "a corrected event time fixes every figure".
No route edits an event's `occurred_at`; § 1 *Edit* covers component, symptom
and description only; closed is read-only. So a supervisor who types 14:00 for
13:00 has no correction path short of a database edit, and the downtime of
that ticket is wrong for good.

**Why it matters.** ISO 14224 § 9 (data quality) and ISO 55001 § 7.5 expect
recorded asset information to be controlled *and correctable*; a record nobody
can fix is one people stop trusting. The decision itself is right — computing
from events is what makes a correction cheap — but the brief should say
whether S018 provides it.

**Options.** (a) State in *Out of scope* that event times are immutable in
S018, and queue "correct an event time — engineer, reason required, a timeline
line old → new, order rule re-checked" in the README's queued list —
**recommended** (keeps S018's size); (b) add it here as one more move-like
route on the locked ticket — small, but one more dialog in a step that already
has five.

### BR1-07 · minor · MTTR: `Maintenance-Philosophy.md` § 10 contradicts Plan.MD Q4; the brief should name its two figures by their EN 13306 names

**Problem.** Philosophy § 10 (Proposed) defines *MTTR* as "total repair time
(in progress → back in service) ÷ breakdowns". Plan.MD Q4 (decided 15-10-2026)
and the brief's § 2 say SMRP's MTTR "runs to restoration", i.e. from the
failure to back in service — the brief's **downtime**, not its **repair
time**. § 3 *Docs* updates the Philosophy glossary but not § 10, so the
contradiction survives approval.

**What the standard says, in plain terms.** EN 13306 keeps the two apart:
*time to restoration* (from failure to the item being able to perform again;
its mean is MTTR, "mean time to restoration") includes the time spent
finding a technician, waiting for parts and administration; *active corrective
maintenance time* is only the time hands are on the machine. SMRP's metric
3.5.5 MTTR follows the first (failure to restoration). So the brief's **repair
time** is EN 13306's *active corrective maintenance time*, and its
**downtime** on a breakdown is the *time to restoration* (= *down time*, the
time in the down state). Both are worth having: downtime is what production
loses, active time is what maintenance controls; their difference is the
waiting S019 will split out (logistic and administrative delay). "Response
time" has no SMRP or EN 13306 definition; it is the plant's own measure
(Philosophy § 10, Proposed) — the brief should not attribute it to SMRP.

**Options.** (a) § 2: name repair time = active corrective maintenance time,
downtime = down time / time to restoration, response time = local; § 3 *Docs*:
fix Philosophy § 10 so MTTR is the mean time to restoration (downtime ÷
breakdowns) and add "mean active repair time" as a second line; Plan.MD § 4.2
*Timestamps* likewise — **recommended**.

### BR1-08 · minor · The trade on a labour row: required or not, and must it be one of the person's trades?

**Problem.** § 4.2 `trade_id INT NULL`, § 1 "trade worked (pre-filled when the
person has one trade)". Not said: whether it may be left empty for a person
who has trades, and whether it must be one of that person's trades.

**Why it matters.** S010 § 2 set this row up for ISO 14224 Table 8
("maintenance man-hours, per discipline"): hours with no trade cannot be
summed by discipline, which is the point of recording the trade at all. A
contractor firm in Team may have no trades, so NULL must stay possible.

**Options.** (a) Required when the person has at least one trade (pre-filled
when exactly one), optional otherwise; any **active** trade is accepted, the
person's are offered first (a fitter who did electrical work books it as
electrical — the trade *worked*, not the trade held) — **recommended**;
(b) always optional — simplest, loses Table 8; (c) restricted to the person's
trades — wrong for multi-skilled people doing something else that day.

### BR1-09 · minor · Define the repeat window exactly; pre-fill the old ticket's intensity

**Problem.** § 5.5: "back in service or closed within 7 days". Within 7 days of
what (now, or the new ticket's event time), measured from which event (back in
service, close)? § 1 says "on a ticket back in service, or closed in the last
7 days", which reads as: any age if still back in service, 7 days from the
close otherwise — so a ticket back in service for a month qualifies but one
closed eight days ago does not, though the fault returned at the same time.
And § 1 pre-fills the new ticket "intensity critical": a defect that was not
fixed is still a defect.

**Why it matters.** The repeat count is the TPM focused-improvement signal
(§ 2); what counts as a repeat must be one rule, and the user should see it.

**Options.** (a) The old ticket's **`back_in_service` event time** lies within
`REPEAT_WINDOW_DAYS` before the new ticket's `occurred_at` (state back in
service or closed, either way); a not-a-fault close has no restoration and so
cannot be repeated — say whether that is wanted or whether "it is back" on a
not-a-fault ticket should link too; pre-fill the **old ticket's current
intensity**, the user may raise it — **recommended**; (b) keep "7 days from
now" against `updated_at` — simpler, but then the window depends on when the
operator types, not when the fault came back.

### BR1-10 · minor · Two endpoints that exist already: drop `/causes` and `/actions`; fold `/people` into S017's reporters picker

**Problem.** § 6 adds `GET /api/tickets/causes` and `/actions` (`ticket:close`)
"active rows for the close dialog". `GET /api/masters/failure-causes` and
`/maintenance-actions` (S016, `masters:read`, active by default, in ISO order)
return exactly that, and `frontend/src/stores/masters.js` already has
`ensureFailureCauses()` and `ensureMaintenanceActions()`. Likewise
`GET /api/tickets/<id>/people` (people at the ticket's site, with trades)
duplicates S017's `GET /api/tickets/reporters?equipment_id=` (people at the
node's site) with a different anchor.

**Why it matters.** Nothing beyond the agreed scope; DRY. Two routes, two
tests and two permission rows for lists everyone may read anyway.

**Options.** (a) Drop `/causes` and `/actions`, the dialog uses the store;
one people helper in `tickets.py` (`_people_at_site(cur, site_id, with_trades)`)
behind both pickers, S017's and S018's — **recommended**; (b) keep them —
only if the close dialog needs something the masters list lacks (it does not).

### BR1-11 · minor · "The person whose login is the user's" is needed three times and only a private helper exists

**Problem.** § 5.2 (default person on restore), § 5.8 (auto-assign) and § 6
(`assigned=me`) all need the user's own `people.id`. `auth_utils._person_id(cur)`
does that (cached on `g`), but it is private; neither S017 nor S018 names a
public one, so the coder either imports a private function or writes the query
again.

**Options.** (a) § 3 `auth_utils.py`: expose `current_person_id(cur)` (the
existing `_person_id`, renamed or wrapped), used by tickets.py; `assigned=me`
for a user without a person returns an empty list — **recommended**.

### BR1-12 · minor · The `regraded` event puts a computed text in the remark the user may also fill; expose the event's intensity instead

**Problem.** § 4.3: `regraded` has remark "Defect → Breakdown"; § 6
`POST /regrade {…, remark?}` takes the user's remark too. One column, two texts.
S017's event shape in the detail (`{event, from_state, to_state, occurred_at,
person, remark, …}`) has no `intensity`, so the page cannot render the change
from the column that holds it.

**Options.** (a) The detail's events gain `intensity`; the frontend's timeline
renders "Defect → Breakdown" (or "Breakdown → Defect") from the previous and
new intensity, the remark stays the user's; same for a `sent_back` that
changes the intensity (BR1-01) — **recommended**. The `edited` event's "old →
new" in the remark is fine: an edit has no user remark.

### BR1-13 · minor · The two-connection concurrency test has no precedent in the suite; say how it is done

**Problem.** § 8 *API*: "two concurrent moves on one ticket … (two
connections)". No backend test uses threads today; the Flask test client runs
one request at a time and the pooled connection is per request, so the coder
has to invent the mechanism.

**Options.** (a) One raw `get_local_db()` connection opens a transaction and
holds the ticket row `FOR UPDATE`; a thread fires the second move through the
test client and blocks on the lock; the first connection applies a move and
commits; the thread's response is asserted 409 (state changed) — this proves
"decided from the locked row"; plus a plain test that a move from a stale
state is 409 — **recommended**; (b) drop the two-connection test and keep only
the stale-state 409 — weaker, acceptable if (a) proves flaky on the dev DB.

### BR1-14 · nit · Small inconsistencies in the core's signatures and the header

- Header: the S017 brief is *In review*, not *Draft*.
- § 3 `ticket_times(events)` vs § 5.4 "`now` is passed in": `ticket_times(events, now)`.
- Intervals ending at `now` must be clamped at zero: the last event may lie up
  to `FUTURE_SKEW` after `now`.
- `validate_event_time` is the rule S017's `validate_raise` already applies;
  say S018 refactors `validate_raise` onto it (DRY) rather than keeping two
  copies of the skew and back-date checks.

### BR1-15 · nit · Migration v13 and test housekeeping, on the v9/v11 conventions

- Say "every statement safe to run twice": `ADD COLUMN IF NOT EXISTS`,
  `FOREIGN KEY IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS` (v5, v9, v11).
- Name the constraints so `test_migration_v13.py` can assert them:
  `fk_tickets_cause`, `fk_tickets_action`, `fk_tickets_repeat_of`,
  `fk_ticket_labour_ticket/_person/_trade`, `fk_ticket_assignees_ticket/_person`,
  `chk_ticket_labour_minutes`.
- `conftest._TABLES` gains `ticket_labour` and `ticket_assignees` before
  `tickets` (which S017 adds with `ticket_events`); child tables first.
- The lock-order note S017 puts in `tickets.py` and `equipment.py` gains the
  moves, edits, labour and assignment writes: "(7) only; nothing else locked".
- § 5.3 "the ticket's site" = the site of `tickets.unit_id` (the unit at raise),
  not the machine's current site; S017 § 5.3 opens the page by either unit, so
  say which one the keys are checked at.

### BR1-16 · nit · Rules S017 set that apply to edit and close too

- S017 § 5.1: description required when no mode or the mode is `OTH`. A PUT
  that clears the mode, or a close that sets `OTH`, with an empty description
  should be 400 on the same rule.
- Edit's `component_id`: a non-scrapped node under the ticket's machine
  (walk up as S017 § 5.2), or null to clear.
- Assigning after back in service: allowed (the engineer assigns who completes
  the job) — say so.
- Labour rows stay on a not-a-fault close (someone did go and look; the
  man-hours are real, the ticket is still no failure). Labour removal is a hard
  delete with no timeline line, while unassign writes one — say that this is
  accepted (rows have audit columns and the ticket is open), or write a
  `labour_removed` event for symmetry.

### BR1-17 · nit · Standards wording

- "Requester sign-off (EN 13306)": EN 13306 defines *restoration*; the
  sign-off by the requester is CMMS practice, not the standard's term. Say
  "(EN 13306 restoration; requester sign-off is common CMMS practice)".
- ISO 55001 § 7.5 / § 9.1 deserve the one line S016 added: the closed work
  order is the asset information the management system evaluates performance
  from.
- Open question 1 (an engineer closes his own ticket) is a deliberate
  departure from segregation of duties (ISO 27001 A.5.3; ISO 55001 § 9.2 has
  the plant audit itself) — say so, with the reason (few engineers) recorded,
  so the choice is visible later.
- Plan.MD § 4.2's *Proposed* "the same person may record 'technician arrived'"
  is settled here by `started_at` on back in service; § 3 *Docs* should close
  it.
- "Not a fault" with a cause: the right reading, worth a sentence for the user —
  the cause code on a not-a-fault ticket says *why it was raised* (`3.2
  Operating error` for a mis-operation, `5.1 No cause found` for "looked,
  nothing wrong"), while the `not_a_fault` flag keeps it out of failure counts.

## Checked and found consistent

- **State machine vs Plan.MD § 4.2 and Philosophy § 6**: the five states and
  the frivolous close from raised / acknowledged match; start from raised and
  back in service from raised / acknowledged (decision 2) are refinements the
  plan's "event time is entered" decision allows; send back only from back in
  service by the engineer matches "only an engineer closes, and can send it
  back"; closed is final (base § Multi-step approval: terminal states are not
  resubmitted; "not fixed" is a new entity).
- **Keys vs Plan.MD § 3 and `config_rbac.py`**: `ticket:work` =
  `("maint_technician",)` (engineer, manager inherit) is the plan's
  `breakdown:work`; `ticket:close` and `ticket:assign` = `("maint_engineer",)`
  are its `breakdown:close` and "assign work"; `ticket:restore` =
  `("maint_operator",)` reaches the supervisor through `ROLE_INCLUDES` and
  nobody else gains anything, so `test_supervisor_is_off_the_maintenance_ladder`
  still passes; no key to `it_admin` (Plan § 3: not maintenance work); all four
  in `SITE_SCOPED`, as `_check_site_args` asserts and the docstring demands.
  `permissions_at_site(site_id)` gives `allowed_moves` its `held_keys`.
- **Locking (§ 5.3)**: the ticket row (7) is last in equipment.py's order, these
  transactions lock nothing before it, FK inserts take only shared locks on
  people, trades, causes and actions; masters.py locks people → memberships →
  units and causes/actions rows but never tickets, so no cycle. The code-freeze
  race is closed the way S017 § 5.7 describes: the masters PUT's X-lock on the
  cause row waits for a committing close's S-lock, and its count then sees the
  row. "Decided from the locked row" follows the S002 BR3-01 rule
  (`LOCK_EQUIPMENT` returns the decision columns).
- **Times (§ 5.4)**, given BR1-01's rule: response from the first `acknowledged`
  or `started`; repair as the sum of `started`/`sent_back` → `back_in_service`
  intervals, null when a restoration has no start; downtime while critical and
  not yet restored, resuming after a "down" send-back, to `now` on an open
  ticket; not a fault → all null. The `started_at` written by an after-the-fact
  restoration keeps the order (last event ≤ `started_at` ≤ restoration), so
  `ORDER BY occurred_at, id` on the S017 index is enough.
- **Event-time rule (§ 5.1)**: events kept in order is the right trade-off; the
  S017 constants are reused.
- **Data model (§ 4)**: `cause_id` / `action_id` as plain FKs to S016's tables
  (the kind is guaranteed, S016 decision 1); `not_a_fault` as a flag rather
  than a sixth state (reports filter on it, the state stays `closed`);
  `ticket_assignees` keyed `(ticket_id, person_id)` with the timeline as
  history; `ticket_labour` with `SMALLINT` minutes and a CHECK; the person
  index for the daily work log. `ticket_events.event` as text matches
  `equipment_events`.
- **Codes frozen once in use (§ 5.6)**: matches S016 § 5.4 (cause group stays
  editable, BR1-12 of S016) and the S017 mode pattern; `_update_plain_master`
  locks the row already, so the count goes in before `update_row`.
- **Assignees and labour from people with a membership at the site (decision
  8)**: consistent with S011 A1 (people without a login hold memberships too)
  and with S017's reporter rule; contractor firms included, as Plan § 4.3
  wants for AMC vendors.
- **Standards**: EN 13460's work-order content (who, what, when, result,
  sign-off) is what labour rows, action code, timeline and close record;
  ISO 14224 Table B.3 / B.5 as cause and activity, Table 8 man-hours per
  discipline via the trade worked (S010 § 2); TPM closing discipline (Plan
  Q12) and repeat failures as focused-improvement input; SMRP's exclusion of
  not-a-fault tickets from MTBF/MTTR (Plan § 4.6, Proposed). The MTTR naming is
  BR1-07.
- **Frontend**: one `MoveDialog` driven by `moves` from the detail (base
  § Mutually exclusive action buttons: the page offers only what applies);
  `ticketLabels.js` as the pure home for labels and "1 h 25 min" (Vitest layer);
  `RaiseTicketView` pre-fill by query, as `equipment=<id>` in S017.
- **Track**: full is right (migration, four keys, locking, a calculation core).
- **Manual checks**: the four important ones are the right four (technician on
  a phone end to end, supervisor after the fact with the technician's name and
  start time, engineer's close refused then accepted, the repeat link); the two
  plain ones are plain.
- **Out of scope**: nothing listed is needed before S019–S021; S019's waiting
  split and S020's parts line both fit on this record without a schema change
  to what S018 adds.
