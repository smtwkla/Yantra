```
Step: S018 — Work the ticket
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 90284ec + uncommitted S016, S015 + the S017 brief (`docs/steps/S017-raise-tickets/1-brief.md`, revised after its r1, In review 20-10-2026; no S017 code exists yet)

# S018 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 answer
marked *Accepted* is in the brief text, not only in the Review log (the list is
under *Checked and found consistent*). The interfaces S018 takes from S017 are
all present in the revised S017 brief. What remains: one rule introduced in the
revision that the user should see (who may be named as the person who fixed a
defect, § 5.8), one place where S017's people picker and S018's role check
disagree after a cross-site move, one dialog contract that contradicts itself,
one claim about the documents owner that S017's shape does not support, and
nits. Full track; this is round 2 of up to 3.

Findings: 0 blocker, 0 major, 4 minor, 5 nit.

## Findings

### BR2-01 · minor · § 5.8 leaves no honest record for a defect the operator fixed himself

**Problem.** The revision narrowed who may be named on *back in service* and on
a labour row to "technician, engineer or manager at the site" (§ 5.8, decision
8, open question 4). Round 1 reviewed the wider rule ("a person with a
membership at the site") and found it consistent; the narrowing is new. It
leaves one floor case with no truthful record: an operator raises a defect
(loose guard, blocked nozzle), fixes it himself, and wants to clear the tag. He
holds `ticket:restore` but must name someone from the ladder, which is false; or
he leaves it raised and the engineer closes it as *not a fault* with a cause,
which is also false (it was a fault, and it was fixed). Open question 4 asks
only whether an operator who *helped* may be booked as labour.

**What the practice says.** TPM autonomous maintenance expects operators to
clear the abnormalities they can (the tag board separates operator tags from
maintenance tags; both are counted, because the operator-fixed share is the
measure of how far autonomous maintenance has come). Plan.MD § 4.2 calls the
ticket "the TPM tag an operator hangs". ISO 14224 Table 8's "man-hours per
discipline" is not threatened by naming an operator: he has no trade, so his row
falls out of any per-discipline sum by itself.

**Options.** (a) Any active person with a membership at the ticket's site may
be named on back in service and on a labour row (the round-1 rule); reports
that want maintenance man-hours sum by trade, which operators lack; open
question 4 then asks the user to confirm that operator-fixed tags are wanted on
the record — **recommended**; (b) keep the ladder rule for breakdowns and allow
anyone at the site on a **defect** (critical never, degraded / initial yes) —
honest, but two rules for one field; (c) keep the ladder rule and say in § 9
that an operator-fixed defect is closed as not a fault with cause *3.2
Operating error* — not acceptable, it miscounts a real fault. Whichever is
chosen, the user should decide it, not the coder: it changes what the repeat
and failure counts mean.

### BR2-02 · minor · The people picker is anchored on the node's current site; the server checks the ticket's site

**Problem.** § 3 and § 6: people for the technician, assignee and labour
pickers come from S017's `GET /api/tickets/people?equipment_id=<node>`, which
resolves "the node's site" (the machine's **current** unit) and checks
`ticket:raise` there. § 5.3 and § 5.8: the server checks the named person's role
"from memberships at the ticket's site", the site of `tickets.unit_id` (the
unit at raise). S017 § 5.3 keeps those two apart on purpose (a moved machine's
tickets stay with the old unit's team). After a cross-site move (Plan.MD § 4.1:
a press from SMTW to SSVT) the picker lists SSVT's people with their SSVT roles,
and every pick is refused at SMTW; and an engineer of the old site, who may act
on the ticket, gets 403 from the picker if he holds nothing at the new site.

**Why it matters.** Rare, but the brief's own rule produces a screen whose every
choice is refused, and the coder would otherwise pick which site the picker
should mean.

**Options.** (a) S018 adds a second anchor to the same endpoint:
`GET /api/tickets/people?ticket_id=<id>` — the ticket by S017's access
predicate (404 otherwise), the site of `tickets.unit_id`, roles at that site;
`equipment_id` stays for the raise screen; one `_people_at_site(cur, site_id)`
behind both (§ 3 already names it) — **recommended**; (b) state in § 5.8 that
the picker follows the machine's current site and a cross-site move is an
accepted mismatch — not recommended, the keys are checked elsewhere.

### BR2-03 · minor · The back-in-service dialog contract contradicts itself

**Problem.** Three statements do not fit together:
- § 3 `allowed_moves(...)`: `needs_person` is "true unless the user holds
  `ticket:work`", and the `MoveDialog` shows the technician picker "when
  `needs_person`";
- § 5.2: for a `ticket:work` holder the technician "defaults to
  `current_person_id(cur)` and **may name another**";
- § 5.2 and BR1-03: a `ticket:work` holder with no Team record (admin, IT admin
  never; an engineer entered in Keycloak before Team) "must name someone (400 on
  `person_id`)".

With the picker hidden for `ticket:work` holders, the second is impossible and
the third is a 400 on a field the user cannot see. The pure core cannot know
whether the user has a Team record, so `needs_person` as defined in the core
cannot carry that case.

**Options.** (a) The technician field is **always shown and required** on back
in service; the detail's `moves` entry for `restore` carries
`default_person: {id, name} | null` (computed in the route from
`current_person_id(cur)` when the user holds `ticket:work` at the site, else
null) and the dialog pre-fills it; `needs_person` is dropped from the core —
**recommended** (one field, one rule, the ladder check of § 5.8 still applies
to whoever is named); (b) keep `needs_person` but define it in the route as
"no default person", and still let the user change the default — works, but
the name then means something else than § 3 says.

### BR2-04 · minor · Open question 2, if answered yes: S017's `Owner` has one write key per owner, not per kind

**Problem.** § 3 `documents.py`: "if yes, the ticket owner's kinds gain
`document` and **its write key for documents is `ticket:work`**". S017 § 5.5
gives `Owner` one `read_key`, one `write_key` (`ticket:raise` for tickets),
one `purge_key` and a `kinds` list; nothing keys a kind to a different
permission. A per-kind key is a change to S017's generalisation, not "one line"
(S017 assumption 3).

**Options.** (a) If yes: `kinds` gains `document` and the write key stays
`ticket:raise`; the raise screen keeps `photosOnly`, the ticket page offers
*Add document* to `ticket:work` holders in the UI, and an operator uploading a
PDF through the API is accepted (he may already upload photos; the content is
the same class of information, ISO 27001 A.8.3 is met by the serving routes) —
**recommended** as the small option the brief intends; (b) a per-kind write key
in `Owner` — correct but a second change to S017's pattern for one
permission; (c) answer no, and leave vendor PDFs to S020 (parts and vendor
quotes land there anyway). Say which in § 3 so the coder does not design it.

### BR2-05 · nit · Repeat rule: which restoration, the lower bound, and the button's clock

- A ticket sent back and restored again has two `back_in_service` events; say
  the rule uses the **latest**.
- `is_repeat_candidate(back_in_service_at, new_occurred_at)` should refuse a
  new event time **before** the restoration (0 ≤ new − back ≤ 7 days): "it
  failed again at 09:00" on a ticket restored at 10:00 is not a repeat of that
  repair.
- § 1 shows the button "within the last 7 days" (against now) while § 5.5
  checks against the new ticket's `occurred_at`; both are right, say that the
  server rule governs and a back-dated raise can still fail the check.

### BR2-06 · nit · Assignment details the coder would otherwise choose

- Auto-assign on acknowledge / start: say it applies to **every** `ticket:work`
  holder who does it (an engineer who presses *Start* is working the ticket; he
  can unassign himself), not only to persons whose role at the site is
  technician.
- Say whether the auto-assign writes an `assigned` event (recommended: yes,
  the same line as a manual assignment, so the timeline is the one history
  § 4.2 says it is).
- `POST /assignees` for a person already assigned: 409 on the primary key, or
  200 and no change (recommended: 200, idempotent — two taps on a phone);
  `DELETE /assignees/<person_id>` of a person not assigned: 404.

### BR2-07 · nit · Small text gaps in § 3, § 5.2 and § 6

- **Close body `failure_mode_id`** when the ticket already has a mode: say
  whether a different value overwrites (the engineer corrects the operator's
  pick; recommended, same class rule) or is ignored. The close dialog's modes
  come from S017's `GET /api/tickets/modes?equipment_id=<machine>` — name it
  in § 3 *Frontend* beside the causes and actions.
- **`/regrade` key**: `require_perm` takes one key; write the route as
  `ticket:raise` at the route (both directions' holders have it) with the
  direction decided inside against `ticket:work` at the ticket's site.
- **§ 5.6**: `_update_plain_master(table, record_id, validator)` is generic
  (causes and actions share it), so the freeze needs the ticket column per
  table — a parameter such as `used_by=("tickets", "cause_id")` — before the
  `update_row`. The lock is there as the brief says.
- **`validate_event_time`** is a one-line alias of S017's
  `event_time_error(…, not_before)`; either call S017's directly or say it is a
  thin wrapper that names the last event in the message (which is the one thing
  it adds).
- **Edit by `ticket:work` only**: the operator who raised the ticket cannot
  correct his own description or symptom; say that this is accepted (he tells
  the technician) so it is not read as an omission.

### BR2-08 · nit · Header and a cross-brief claim

- `Baseline:` omits **uncommitted S015**, which changed `equipment.py` (named in
  § 3 *Where*); the planner copies this review's `Reviewed against:` at approval
  anyway.
- § 5.1: "S017's raise screen follows the same rule" (no `occurred_at` sent
  unless the user changed the time). The revised S017 brief does not say this
  (§ 3: "event time … default now"; § 5.1: "`occurred_at` optional, default
  `now`"), and its "Changes asked by the S018 review" list has no BR1-05 item.
  Either S017 § 3 says it (for the orchestrator to carry into S017's round 2:
  without it a phone 6 minutes fast is refused on every raise by `FUTURE_SKEW`),
  or S018 drops the claim.

### BR2-09 · nit · Standards: two clauses the brief should name

- **ISO 9001 § 10.2** (nonconformity and corrective action): Plan.MD's
  *Standards* decision (20-10-2026) says each brief names the ISO 9001 clause it
  serves, and lists "§ 10.2 … tickets with cause and action codes" — which is
  this step. One line in § 2: the closed ticket with cause, action and labour is
  the corrective-action record § 10.2 asks for (what happened, why, what was
  done, by whom), and the repeat link is its "review the effectiveness".
- **ISO 27001**: the four keys are least privilege per role and site (A.5.15),
  and the event log with `created_by` / `created_at`, immutable in S018, is the
  logging A.8.15 asks for — one line each, as S017 § 2 does.

## Checked and found consistent

- **Round-1 answers in the text**: BR1-01 (§ 1 send back, § 4.3 intensity on
  the move's own event, § 5.4, decision 4, `send_back_intensity` and its tests);
  BR1-02 (§ 1 both directions, § 5.2, § 6, decision 7, `validate_regrade`);
  BR1-03 (one key `ticket:restore`, § 5.2 no-Team-record rule, the `started`
  event's person — the dialog contract is BR2-03); BR1-04 (§ 8 *RBAC* names
  the rows, the holders tests, the supervisor test); BR1-05 (§ 5.1 default =
  server clock, refusal names the last event, the re-grade consequence,
  decision 9 — the S017 side is BR2-08); BR1-06 (Out of scope, § 5.1, README
  queue in § 3 *Docs*); BR1-07 (§ 2 names, § 3 *Docs* fixes Philosophy § 10
  and Plan § 4.2); BR1-08 (§ 1, decision 10, `validate_labour`); BR1-09
  (§ 5.5, open question 3, current intensity pre-filled); BR1-10 (no
  `/causes`, `/actions`, `/people` of its own); BR1-11 (`current_person_id`
  in § 3, empty *Assigned to me*); BR1-12 (§ 4.3 remark rule, events'
  `intensity`); BR1-13 (§ 8 concurrency test and fallback); BR1-14 (header,
  `ticket_times(events, now)`, clamping, one window rule); BR1-15 (migration
  idempotence, constraint names, `_TABLES`, lock-order note, the ticket's
  site); BR1-16 (description rule at edit and close, component under the
  machine, assign after back in service, labour on not-a-fault, hard delete
  accepted); BR1-17 (every wording item).
- **S017 interfaces S018 relies on**, all in the revised S017 brief: the people
  picker with trades and the role at the site (§ 6; the anchor is BR2-02);
  events' `intensity` in the detail (§ 6); `event_time_error(event_time, now,
  not_before=None)` with a `not_before` test (§ 3, § 8); the documents `Owner`
  with `read_key` / `write_key` / `purge_key` / `kinds` and the closed-ticket
  409 (§ 5.5; per-kind keys are BR2-04); scrapping refused with open tickets
  (§ 5.8); operators without a login (§ 5.9); the full `state` ENUM, `person_id`
  and `from_state` / `to_state` on events, `tickets.unit_id` kept at raise,
  `FUTURE_SKEW` / `MAX_BACKDATE_DAYS`; `current_person_id` explicitly left to
  S018 (§ 6); migration v12, so v13 is next (the tree is at v11).
- **Code claims verified**: `auth_utils._person_id(cur)` exists, cached on `g`,
  active person by normalised username — the thing `current_person_id` exposes;
  `permissions_at_site(site_id)` gives `allowed_moves` its keys;
  `accessible_unit_ids(cur, key)` lives in `equipment.py` and is what S017's
  predicate uses; `_update_plain_master` locks the row (`_lock_row`) before
  `update_row`, so the count fits where § 5.6 puts it (parameterisation is
  BR2-07); `ROLE_INCLUDES` makes a key granted to `maint_operator` reach the
  supervisor and the whole ladder, and nothing else reaches the supervisor, so
  `test_supervisor_is_off_the_maintenance_ladder` holds with `ticket:restore`;
  `test_role_matrix` asserts exact sets for seven roles, and the five rows § 8
  names are the ones that change (`it_admin` and `maint_storekeeper` do not);
  `_check_site_args` asserts a site-checked key is in `SITE_SCOPED`, so a
  forgotten entry fails in tests; `memberships` PK `(person_id, site_id)` =
  one role per person and site, which § 5.8's "role at the site" needs;
  `people.active`, `trades.active`, `person_trades (person_id, trade_id)` are as
  § 1 and § 4.2 assume; `conftest._TABLES` is the flat tuple § 3 extends;
  `ensureFailureCauses()` / `ensureMaintenanceActions()` exist in the masters
  store; `failure_causes` seeds include `3.2 Operating error` and `5.1 No cause
  found`.
- **State machine vs Plan.MD § 4.2 and Philosophy § 6**: unchanged from round 1
  and still right; not a fault from `in_progress` refused (a stop someone
  worked on is a failure, cause *5.1 No cause found* if nothing was found); a
  stop the operator clears himself is a minor stop, not a breakdown
  (Philosophy § 4) — the defect case is BR2-01.
- **Times (§ 5.4)**: with every intensity change on its own event, the three
  figures are computable from `ORDER BY occurred_at, id` alone; the `started`
  written with an after-the-fact restoration is bounded by the last event and
  the restoration, so order holds; a restoration with no start gives repair
  null, which is the honest answer; `now` passed in; not a fault → nulls.
- **Locking (§ 5.3)**: the ticket row (7) is last in the global order; moves,
  edits, labour and assignment lock nothing before it; the FK inserts take
  shared locks on `people`, `trades`, `failure_causes`, `maintenance_actions`,
  none of which masters.py locks after a ticket — no cycle. The cause / action
  freeze serialises as S017 § 5.7 describes (the masters X-lock waits for a
  committing close's S-lock; the count is the transaction's first consistent
  read, so it sees the commit).
- **Permissions (§ 5.7)**: match Plan.MD § 3 (`breakdown:work` → `ticket:work`
  on the technician, `breakdown:close` → `ticket:close` on the engineer,
  "assign work" → `ticket:assign`), `ticket:restore` on the operator per
  Plan § 4.2 ("whoever has operator rights at the unit"); no key to IT admin;
  all four site-scoped.
- **Data model (§ 4)**: FKs to S016's tables, `not_a_fault` as a flag,
  `ticket_assignees` keyed by the pair with the timeline as history,
  `ticket_labour` with `SMALLINT` minutes and a named CHECK, the person index
  for the daily work log, every statement idempotent as v5 / v9 / v11.
- **Standards (§ 2)**: EN 13460 work order; ISO 14224 activity (B.5), cause
  (B.3), man-hours per discipline (Table 8) through the trade worked; EN 13306
  down time / time to restoration and active corrective maintenance time named
  correctly, their difference as the waiting S019 splits; SMRP 3.5.5 MTTR to
  restoration, not-a-fault excluded; restoration vs CMMS sign-off; ISO 55001
  § 7.5 / § 9.1; TPM closing discipline and repeat failures; open question 1 as
  a recorded departure from segregation of duties. The two missing clauses are
  BR2-09.
- **Frontend**: one `MoveDialog` driven by `moves`, pure labels in
  `ticketLabels.js`, pre-fill by query on the raise screen, causes and actions
  from the store — proportionate; no over-engineering seen.
- **Track**: full, rightly. **Manual checks**: the four important ones are the
  right four (phone, after-the-fact by a supervisor naming the technician and
  start time, the engineer's close refused then accepted, the repeat link); the
  two plain ones are plain.
- **Out of scope**: nothing listed blocks S019–S021; the event-time correction
  is queued with its rule written down.
