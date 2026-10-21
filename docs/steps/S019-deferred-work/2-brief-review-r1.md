```
Step: S019 — Deferred work
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 28d3be3 + uncommitted S024

**Verdict: one `major` finding is open (BR1-01, the EN 13306 delay mapping of
the waiting reasons). No blocker.** The design — one `scheduled` state shown
as *Scheduled* or *Waiting* by intensity, the plan on the ticket with the
history on the events, the figures computed from the events as S018 does — is
sound, right-sized, and builds on the code as it stands (`tickets_core.MOVES`,
`_apply_move`, `_MOVE_STEPS`, `ticket_times`, `MoveDialog`). The planner asked
for the EN 13306 clause numbers and the SMRP metric names in particular:
BR1-01 to BR1-03 cover them, with what I could and could not confirm.

## Findings

### BR1-01 · major · `expert` is a logistic delay in EN 13306, not administrative; `other` fits neither

**Problem.** § 1.4 maps `expert` ("Waiting for an expert or a decision") and
`other` to *administrative delay*. EN 13306's definitions (Clause 9, time
related terms; the wording follows IEC 60050-192):

- **logistic delay** — the accumulated time during which a maintenance action
  cannot be performed because maintenance *resources* must be acquired,
  excluding administrative delay. Its note lists the resources: travelling to
  the site, **spare parts, specialists, test equipment, information**, and
  unsuitable environmental conditions.
- **administrative delay** — the accumulated time during which a maintenance
  action is not performed for *administrative reasons*: a decision, a
  priority, a permit, a budget, production not releasing the machine.

So a specialist — the project owner's diagnosis, the vendor's service engineer,
the polytechnic faculty — is a **logistic** delay in the standard's terms,
exactly like a spare part. "A decision" is administrative. The one reason mixes
the two kinds, and `other` is forced into administrative, which silently
inflates the administrative total with whatever did not fit.

**Why it matters.** Decision 3's own argument: the mapping is fixed in code so
the split "stays comparable over the years". A wrong mapping is then wrong for
years, and the figure the split exists for — "what maintenance controls versus
what we wait for" — would put the plant's biggest known wait (fault diagnosis
by one person, Plant-Facts § 4: "some problems take months") on the wrong side.

**Options.**
- (a) **Six reasons, honest buckets** — recommended:

  | Code | Shown as | EN 13306 delay |
  |---|---|---|
  | `parts` | Waiting for parts | logistic |
  | `vendor` | At or waiting for a vendor, garage or maker | logistic |
  | `expert` | Waiting for an expert | logistic |
  | `slot` | Waiting for a production slot or shutdown | administrative |
  | `approval` | Waiting for a decision or approval | administrative |
  | `other` | Other (remark required) | — (not classified) |

  `other` is reported as its own line ("other waiting"), inside the waiting
  total but in neither delay total. The reports then say exactly what was
  recorded.
- (b) Keep five: `expert` → logistic, worded "Waiting for an expert or
  specialist"; decisions go under `slot` reworded "Waiting for production or a
  decision"; `other` unclassified. Smaller list, but "slot or decision" is two
  things again.
- (c) Keep as written. Rejected: it misstates the standard it cites.

### BR1-02 · minor · EN 13306 and ISO 14224 citations: clause numbers and one claim to verify

**Problem.** § 2 cites "EN 13306:2017 § 7.5 — deferred corrective maintenance"
and "EN 13306 § 8, Figure 4" for the parts of time to restoration, and says
ISO 14224 Table 8 "lists *delay* … as a recorded time". What I can say:

- **Deferred corrective maintenance** is in Clause 7 (maintenance types and
  strategies), but not under 7.5: in the 2017 edition 7.5 is *corrective
  maintenance* and *deferred corrective maintenance* is its own entry right
  after it (7.6, with *immediate corrective maintenance* 7.7); in the 2010
  edition it was 7.8 *deferred maintenance*. The quoted definition is right in
  substance ("corrective maintenance which is not immediately carried out
  after a fault detection but is delayed in accordance with given rules").
  Please check the number against the copy held; I would not cite a
  sub-clause I cannot confirm.
- **The time terms are Clause 9** (*Time related terms*) in both editions,
  not Clause 8 (8 is *Maintenance activities*: inspection, repair, fault
  diagnosis …). The diagram of how the times nest is **Annex A**
  (informative, "time related terms" figures), not "Figure 4". Cite
  "Clause 9 and Annex A".
- The description of what makes up time to restoration is right as far as it
  goes, and worth completing for the owner's learning: EN 13306 splits it as
  **fault detection time** + **administrative delay** + **logistic delay** +
  (**technical delay**: cooling down, draining, isolating, before hands can
  go on) + **active corrective maintenance time**. In Yantra the fault
  detection time sits inside downtime when the operator enters an earlier
  "when it happened" than the raise, and technical delay sits inside *in
  progress*; both are accepted simplifications, and the brief could say so in
  one line.
- **ISO 14224 Table 8**: I could not confirm *delay* as a field of the
  maintenance record. What I recall under *maintenance times* is **active
  maintenance time** and **down time** (with man-hours per discipline under
  resources); the delays are implied as the difference between the two, and
  the time-line concepts of § 8 (up/down time) make that explicit. Unless the
  copy shows a delay field, reword to "ISO 14224 records down time and active
  maintenance time; the difference is the delay, which the waiting reasons
  now name".

**Why it matters.** The owner is learning the standards from these briefs and
Maintenance-Philosophy is updated from them (§ 3 Docs); a wrong clause number
propagates.

**Options.** Fix the three citations as above (recommended); or cite by term
without clause numbers where unsure.

### BR1-03 · minor · SMRP: name the metrics, and state the "scheduled = planned" proxy as a departure

**Problem.** § 2's SMRP bullet defers the metric numbers and treats "a ticket
that went through *scheduled* before work started" as SMRP *planned work*. In
SMRP's vocabulary **planning and scheduling are two different things**:
*planned work* (metric **5.1.3 Planned Work**, with **5.1.4 Unplanned Work**)
is work whose job plan — scope, labour, parts, tools, procedure — was prepared
before execution; *scheduling* is giving it a slot. *Reactive work*
(**5.1.5**, with **5.1.6 Proactive Work**) is work that breaks into the
schedule at short notice — the "planned-versus-reactive ratio"
Maintenance-Philosophy § 7 names is really 5.1.5/5.1.6. Yantra has no job plan
in v1, so "scheduled before started" is a **proxy** for planned work and
"started without ever being scheduled" a proxy for reactive work. That is a
fair proxy for this plant; the brief should say it is one (CLAUDE.md: "state
where and why it deliberately departs").

The other metrics the step records data for:
- **Backlog**: SMRP measures it in **weeks of crew capacity** — **5.3.1 Planned
  Backlog** (planned, not yet scheduled) and **5.3.2 Ready Backlog** (planned
  and materials on hand), each = backlog hours ÷ weekly crew hours. "Backlog
  age" per ticket is not an SMRP metric; it is Yantra's own, close to
  work-order aging. Fine to keep, named as the plant's own measure as
  *response time* was in S018.
- **Planned versus breakdown downtime**: SMRP has the pair directly —
  **3.2 Total Downtime = 3.3 Scheduled Downtime + 3.4 Unscheduled Downtime**
  (Yantra's "planned stop" is part of 3.3; breakdown downtime is 3.4). Cite
  them beside the OEE bullet.
- A doc inconsistency to fix while § 3 Docs touches Maintenance-Philosophy
  § 10: it and S018 § 2 cite **MTTR as SMRP 3.5.5**, while S025 § 2 (after its
  BR1-13) cites **3.5.2**. In the SMRP list 3.5.1 is MTBF, **3.5.2 is MTTR**
  (mean time to repair or replace), 3.5.3 MTBM, 3.5.4 MTTF and **3.5.5 is MDT**
  (mean downtime). Verify against the SMRP copy and make the three docs agree.

Numbers above are from memory of the SMRP Best Practice Metrics (5th ed.);
the brief's "to be checked against the current edition" stays right — but the
names can be checked now rather than in phase 5.

**Why it matters.** Phase 5's reports will be named after these; getting the
vocabulary right now costs one paragraph.

**Options.** Add the names and the proxy sentence (recommended). Also add
**ISO 55001 § 8.1** (operational planning and control: maintenance activities
are planned, with the criteria for doing them, and their risks managed) — the
planned date and reason are that plan for deferred corrective work.

### BR1-04 · minor · List order: scheduled tickets in the open list, and the Scheduled / Overdue filters

**Problem.** § 1.6 keeps the open list's order "critical first, oldest first".
A critical press *waiting for a cylinder at the maker* then sits at the top of
every technician's open list for three weeks, above a fresh breakdown that
needs someone now — the row that can do nothing leads. And the new
*Scheduled* and *Overdue* filters sort by raise time, where the person scanning
them (the engineer planning the week) wants them by **planned date**: what is
due next, what is most overdue.

**Why it matters.** The list's stated purpose is "what is down and waiting
longest leads" for people who act on it; scheduled rows are the ones nobody
can act on until the date.

**Options.**
- (a) Recommended: in `open`, order `t.intensity, t.state = 'scheduled',
  t.occurred_at, t.id` — scheduled rows stay in the open list (never hidden,
  so never forgotten) but after the actionable ones of the same intensity; in
  `scheduled` and `overdue`, order `t.planned_date, t.id`. Both are SQL
  changes in `list_tickets` only.
- (b) Keep the order, rely on the planned date shown on the row. Weaker on a
  phone where only the first rows show.

### BR1-05 · minor · Planned-date lower bound: "the event's date" and "today" contradict each other

**Problem.** § 1.8 and § 5.1 say the date must be "on or after the event's
date" with the message "The planned date cannot be before today", and § 1.8
also says "a past planned date cannot be set". A schedule move may be
back-dated up to 7 days (S018 § 5.1: every move's `occurred_at`). With the
event-date rule, an engineer who records on Friday a scheduling done on
Tuesday may set Wednesday as the plan: a ticket born overdue, and the message
would be wrong.

**Why it matters.** Two rules for one field; the coder has to pick.

**Options.** (a) Recommended: compare with **today** (IST date of `now`) only:
`planned_date_error(planned, today)` — "cannot be before today", "within a
year"; the message matches, "overdue only by waiting" holds, and the event
time plays no part. (b) Keep the event date and change the message. (a) is
simpler and what the brief's own § 1.8 promises.

### BR1-06 · minor · `GET /waiting-reasons` contradicts § 3 and the existing pattern

**Problem.** § 6 adds an endpoint "so the page holds no copy", while § 3
Frontend puts "the reasons" in `ticketLabels.js`. The existing pattern is the
latter: `ticketLabels.js` holds `STATE_LABELS`, `EVENT_LABELS`,
`INTENSITY_LABELS` as plain copies of `tickets_core`'s constants ("the backend
holds the rules; these only name the values"), the server validates the codes.
The reason labels are needed on list rows, the badge, the timeline and the
dialog — fetching them for a list page adds a request for five strings.

**Why it matters.** A parallel way of doing one thing (CLAUDE-COMMON DRY /
patterns), and one more endpoint to test and keep in step.

**Options.** (a) Recommended: no endpoint; `WAITING_REASON_LABELS` in
`ticketLabels.js` with a unit test that its keys equal the API's codes (the
e2e run would also catch a drift). (b) Keep the endpoint and drop the copy —
then say so in § 3 and load it once in the masters store, not per page.

### BR1-07 · minor · The times card example shows per-reason waiting; the API returns only the two delay totals

**Problem.** § 1.5's example reads "of which waiting 2 d 20 h (parts 2 d
20 h)", but § 5.4 / § 6 give `waiting_logistic_minutes` and
`waiting_administrative_minutes` only. On the floor "parts 2 d 20 h" is the
line people understand; "logistic 2 d 20 h" means nothing to a technician.

**Why it matters.** The card cannot show what the example shows from what the
API sends.

**Options.** (a) Recommended: `ticket_times` returns `waiting_minutes` and
`waiting_by_reason: {parts: n, …}` (the slices it already computes, keyed by
reason); the logistic / administrative totals are derived from
`WAITING_REASONS` where needed — on the card by the page (a sum over a fixed
map, no rule), in phase 5 by the report. (b) Return all three shapes. (c) Show
the two totals and drop the per-reason example. (a) keeps the per-ticket card
in the words the reasons use, which is what the standard's split is for.

### BR1-08 · minor · Clear the plan columns in one place, not in three handlers

**Problem.** § 3 says "the start and restore handlers … clear the plan columns
when leaving scheduled" and § 5.3 repeats it for not a fault. `start` has no
`_MOVE_STEPS` handler today (it needs none), so this adds one just to clear two
columns, and the rule lives three times. The new CHECK `chk_tickets_plan` turns
any missed path (a future move from scheduled) into an `IntegrityError` — a
500, not a refusal.

**Why it matters.** DRY, and the CHECK should be a guard that never fires, not
the way a missed path is found in production.

**Options.** Recommended: in `_apply_move`, after the step: `if ticket["state"]
== SCHEDULED and spec.to_state != SCHEDULED: changes.update(planned_date=None,
waiting_reason=None)` — one line, every present and future move covered. The
`start` handler is then needed only for `machine_stopped`, which fits
`_MOVE_STEPS`' shape (it returns the event's extra fields).

### BR1-09 · minor · Existing tests that will break, and the e2e seed, are not in § 3 / § 8

**Problem.** The brief lists the test files but not the assertions that change
by design, so a coder may "fix" them the wrong way round:
- `test_tickets_core.py:44` `test_open_states_are_every_state_but_closed`
  asserts the exact `OPEN_STATES` tuple;
- `TestAllowedMoves.test_state_by_keys` and `test_the_table` (lines 235–264)
  assert the full moves table — every ENGINEER row gains `schedule`, and
  `start`/`restore`/`not-a-fault` gain `scheduled`;
- `test_ticket_work_api.py:181` `test_moves_listed_per_user` asserts the
  engineer's exact move names;
- `frontend/tests/ticketLabels.test.js:16` asserts the exact `STATE_LABELS`
  keys.

And § 8's e2e check "the list's *Overdue* filter shows a ticket planned in the
past (seeded)": `tooling/e2e/seed_e2e.py` seeds no tickets today (the specs
raise them through the API, `support/tickets.js: raiseByApi`), and the API
refuses a past planned date by design, so the overdue ticket must be written
by SQL in the seed (a ticket row, its `raised` and `scheduled` events,
`planned_date` yesterday). `seed_e2e.py` belongs in § 3 Where.

**Why it matters.** The coder decides alone otherwise; the e2e check cannot be
written as described without the seed change.

**Options.** List the four assertions as "updated for the new state/moves"
and add `tooling/e2e/seed_e2e.py` to Where (recommended).

### BR1-10 · minor · Dialog details the coder would otherwise decide: Change plan prefill, *Other* opens the remark, the stopped question on back in service, `asksStart`

**Problem.** Four small gaps in § 1.7 / § 3 Frontend:
1. *Schedule* is "prefilled with nothing"; **Change plan** says nothing. It
   must open **prefilled with the current date and reason** so the engineer
   changes one thing and Save; the remark open and required (the S018 rule for
   required remarks). Without prefill "Nothing to change" could never be
   reached from the page, yet § 8 tests it.
2. Choosing **Other** must open the remark field and mark it required (as
   not a fault does), so the 400 "Say what it waits for" is the exception,
   not the normal path.
3. `asks_machine_stopped` on **restore** is conditional: the server requires
   it only when a start time is sent. The flag means "ask when the time is
   filled"; the dialog shows the Yes / No only then. Say so, or the page shows
   a question the server will ignore.
4. `MoveDialog.asksStart` is `["raised","acknowledged"].includes(state)`; it
   must gain `scheduled`, and `started_at_error` already passes `scheduled`
   (it refuses only `IN_PROGRESS`). One line, but name it.

**Why it matters.** Each is a rule the coder would set alone; 1 is a flow the
engineer uses every time a date slips.

**Options.** Add the four lines to § 1.7 (recommended).

### BR1-11 · nit · `ix_tickets_state_planned` is not needed

A few thousand tickets at most, the list already filtered by unit; `state =
'scheduled' AND planned_date < today` is a trivial scan, and
`ix_tickets_unit_state` exists. CLAUDE-COMMON: don't build for load that won't
come. Drop it (one less thing in v21 and its test).

### BR1-12 · nit · v21 is "the next free number"

S020's brief says "whichever S019 or S020 is coded first takes v21". Say the
same here ("v21, or the next after S020's if that is coded first") so the two
briefs agree and the coder does not collide.

### BR1-13 · nit · The state badge should not carry a sentence

"Scheduled for 25-10-2026 · waiting for a production slot" inside a badge
wraps badly at phone width beside the serial and intensity badges. Keep the
badge to one word (*Scheduled* / *Waiting* / **Overdue**) and put "for
25-10-2026 · waiting for parts" (or "since 25-10-2026") as the line under the
header, where the ticket page already has room.

### BR1-14 · nit · The stopped question's tense

At *Start* the technician is stopping the machine now: "Is the machine stopped
for this work?"; on *Back in service* after the fact it is "Was the machine
stopped for this work?". Two labels for one field (`machine_stopped`), chosen
by move, as `sendBackQuestion` is by intensity.

### BR1-15 · nit · Device check wording; two automated checks to add

The native `<input type="date">` shows its value in the **phone's** locale
format (DD/MM/YYYY on an Indian phone, otherwise whatever the phone is set to)
— Yantra does not control it, so "shows in DD-MM-YYYY" can fail for a reason
outside the app. Make the check: the phone's date picker opens from the field,
and **after Save the page shows the chosen date as DD-MM-YYYY**. Account /
network / where are given — good. Add to the **Automated** list: the *Change
plan* dialog and the *Start* dialog with the Yes / No fit a phone
(`expectDialogFits`), as the Schedule dialog does.

### BR1-16 · nit · Small implementation points to settle in the brief

- `ScheduleFields.vue` "if MoveDialog would otherwise grow past readable" —
  decide now: yes, a component for the date + reason pair (MoveDialog is 253
  lines and gains two fields and a Yes / No).
- The remark messages "Say why the plan changed" / "Say what it waits for":
  `_REQUIRED_MESSAGES` is per field, and S018's required remarks all say "Add a
  remark". Simplest: keep "Add a remark" from `requires`, and word the field's
  **label** per move ("Why did the plan change?", as not a fault's "Why is it
  not a fault?"); the *Other* case needs its own check in the handler anyway.
- Date parsing: `validate_labour` already parses a `YYYY-MM-DD` date
  (`date.fromisoformat`, `LABOUR_DATE_FORMAT`); extract `_optional_date` and
  use it for `planned_date` rather than a second copy.
- The ENUM `MODIFY` must restate `NOT NULL DEFAULT 'raised'` or the default is
  lost; MariaDB 11.4 (the dev image) appends an ENUM value in place.
- The "Plan changed: old → new" line: the old date is on the previous
  `scheduled` / `rescheduled` event, so the page derives old → new by walking
  the events, as `intensityChanges` does; say so.

## Notes on the open questions (for the user, not findings)

- **Q1 (who may schedule).** A middle option worth offering: technicians
  (`ticket:work`) may schedule **from in progress only** — "work stopped,
  waiting for …" is the technician's fact on the floor at 2 a.m., and leaving
  the ticket *in progress* till an engineer arrives is exactly the repair-time
  error the step exists to remove; scheduling from raised / acknowledged
  (committing a production slot) stays the engineer's (`ticket:assign`). The
  key check is per move in `MOVES`, so this is one table entry.
- **Q2.** *Waiting* for a critical ticket reads right on the floor; keep.
- **Q3 (workshop).** Agree with the brief: a part being worked on in the
  plant's own shop is active repair by our own people (in progress). If a
  part queues there for days, that is a `parts` wait in effect.
- **Q6.** Consistent with S021's draft (§ 1: "Acknowledged means the ticket
  has left raised"), so escalation already treats *scheduled* as a response.

## Checked and found consistent

- `tickets_core.MOVES`, `allowed_moves`, `validate_move` (`requires` →
  `_REQUIRED_MESSAGES`), `_apply_move` and `_MOVE_STEPS` are as the brief
  describes; `schedule` and `reschedule` fit the generic `make_move` route
  with no new route — the thin shell stays thin, the rules in the core.
- `ticket_times` as it stands (running state and intensity from the events,
  `_DOWN_STATES`, clamp at zero, not-a-fault all null): the brief's § 5.4
  changes (response counts `scheduled`, a `scheduled` event closes an
  in-progress interval, `scheduled` is a down state while critical) slot into
  the existing loop. The pure test list in § 8 covers the cases that matter,
  including the reason change mid-wait and the re-grade to critical.
- `REGRADE_STATES`, `started_at_error` (refuses only `IN_PROGRESS`),
  `_restore` writing the `started` event with the person: the brief's leaving-
  scheduled rules reuse them.
- The lock and transaction story (§ 5.6) is S018 § 5.3 unchanged: the ticket
  row (7) only, no new lock-order edge; 409 "This ticket changed — reload" for
  a stale page (`TICKET_CHANGED` exists).
- No RBAC change: `ticket:assign`, `ticket:work`, `ticket:restore`,
  `ticket:close` exist in `config_rbac.PERMISSIONS` and `SITE_SCOPED`;
  decision 4 is consistent with Plan.MD § 4.2 ("set by the engineer").
- Migration shape (v4.3): `ADD COLUMN IF NOT EXISTS`, `ADD CONSTRAINT IF NOT
  EXISTS … CHECK` are the forms v12 / v13 already use; `from_state` /
  `to_state` are `VARCHAR(20)`, so `scheduled` fits; the CHECK holds on every
  existing row.
- Plan.MD § 4.2 *Deferred work* and *Fleet defects*, Q13, and
  Maintenance-Philosophy § 4 and § 7 (*Deferred corrective maintenance*,
  *The vehicle fleet*): the brief settles what they propose, except meter
  targets (correctly deferred to the PM engine).
- Out of scope is right-sized: no planning board, no reports, no
  notifications, no meter targets; planned downtime only from a scheduled
  start (decision 5) is a defensible line and is stated.
- UX: Schedule is date + reason + Save on a phone (time and remark behind
  "Now · Change" / *Add remark*); *Change plan* is set apart by requiring a
  remark; the significant moves of S018 are untouched; no new control is
  shown to a user without the key (`moves` from the server); the Tickets list
  row gains the planned date, which the fleet case needs.
- Standards named: EN 13306 (deferred corrective maintenance, the delay
  split), ISO 14224, SMRP, OEE/TPM planned maintenance, ISO 9001 § 10.2 —
  the right set; the corrections are in BR1-01 to BR1-03.
- Manual checks are split Automated / On a real device with the important
  ones marked; the one device check carries account, network and where.
