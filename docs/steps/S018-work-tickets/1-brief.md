```
Step: S018 — Work the ticket
Doc: brief
Author: Planner (Opus)
Date: 20-10-2026 (revised 20-10-2026 after brief-reviews r1–r4)
Track: full
Baseline: cfedc46 (s1)
Status: Committed ae3841f; checks: 5 auto; left: 1 phone-keyboard check for IT Admin (device-checks rows 6, 7) (approved 20-10-2026 by KLA; A1 approved 20-10-2026)
```

# S018 — Work the ticket

S017 raises tickets; this step lets maintenance **work** them to the end:
acknowledge, start, back in service, close with cause and action codes, with
the labour of each technician, assignment by the engineer, send back,
closing a ticket that was no fault, re-grading the intensity, and the
**response time, active repair time and downtime** of every ticket. With it the
ticket is the **work order** of EN 13460, and phase 3's first figures
(time to restoration, active repair time) exist per ticket.

User decisions taken before this brief (20-10-2026):
1. **"Not fixed" after back in service is a new ticket**, linked to the old one
   (`repeat of`); the operator does not reopen a ticket.
2. **Assignment is in this step**: the engineer may assign one or more
   technicians; a technician who acknowledges or starts takes the ticket
   himself.
3. The symptom is optional at raise (S017), so it is **required at close**.

Decisions taken in S017's review that this step relies on (user, 20-10-2026):
- a person without a login may hold **Technician or Operator** rows (IT admin
  sets an Operator row), so the people at a site include phone-less operators
  (§ 5.8 says who may be picked for what);
- scrapping a machine with open tickets is **refused**, so a ticket never has
  to be worked or closed on scrapped equipment; S018 needs no rule for it;
- **IT admin gets full access to tickets** (S017 user decision 7): all four
  keys below; the storekeeper none for now.

User decisions at gate A (20-10-2026):
4. **Self-close allowed** (open question 1): the engineer, manager or IT admin
   may close a ticket he worked himself — a recorded departure from ISO 27001
   A.5.3 (segregation of duties).
5. **Vendor documents on tickets** (open question 2): the ticket owner's
   `kinds` gains `document`; the write key stays `ticket:raise`; *Add
   document* shown to `ticket:work` holders. Files under
   `DATA_DIR/tickets/<id>/` with the photos (one folder per record type, then
   per record — the existing layout, accepted).
6. **Repeat window 7 days** (open question 3): `REPEAT_WINDOW_DAYS = 7`.
7. **Back-in-service person and labour: anyone at the site** (open question 4,
   option (a)): any active person with a membership at the ticket's site,
   operators included; assignees technician, engineer or manager.
8. **No *Time spent* on the back-in-service dialog** (open question 6):
   labour is added on its own; the labour defaults of § 1 are enough.
9. **The `FormModal` scroll fix stays in S018** (§ 7 decision 12).

**Track: full** — a migration, four permission keys, a state machine with
locked transitions, a calculation core, more than 10 files.
**Depends on:** S017 (tickets, events, the raise screen, the people picker)
and S016 (causes, actions). Coded after S017 is committed.

## 1. What will be built

- **States and moves** (Plan.MD § 4.2), each recorded with an **event time**
  (default now: the dialog sends no time unless the user changed it, so the
  server's clock is the default — § 5.1) and an optional remark:

  ```
  raised ──► acknowledged ──► in progress ──► back in service ──► closed
     └──────────── start ───────►│                 │  (engineer)
     └── back in service (after the fact) ────────►│
                                 ◄── send back ────┘  (engineer)
  raised / acknowledged ──► closed — "not a fault" (engineer: cause + remark)
  ```

  | Move | From | To | Key | Needs |
  |---|---|---|---|---|
  | Acknowledge | raised | acknowledged | `ticket:work` | — |
  | Start work | raised, acknowledged | in progress | `ticket:work` | — |
  | Back in service | raised, acknowledged, in progress | back in service | `ticket:restore` | the person who did the work (`person_id`), always asked; pre-filled with the user's own person when he may be named there (§ 5.2) |
  | Send back | back in service | in progress | `ticket:close` | machine down again (yes / no), remark |
  | Close | back in service | closed | `ticket:close` | cause, action, symptom if empty, ≥ 1 labour row |
  | Close — not a fault | raised, acknowledged | closed | `ticket:close` | cause, remark |

  `ticket:restore` is granted to the operator and inherited up the ladder
  (§ 5.7), so every `ticket:work` holder holds it too; the back-in-service
  move has that one key. The person field is always shown and required; the
  page pre-fills it from the move's `default_person` (BR1-03, BR2-03).
  - **Every move dialog is short** (BR3-09): the time shows as **"Now ·
    Change"**; pressing *Change* shows the input filled with the phone's now,
    so the user edits a time rather than typing one (S017's raise-screen rule,
    BR4-08). Save is the one action, so the common case is button → Save.
    **The remark**: behind *Add remark* where it is optional (acknowledge,
    start, back in service, close, a raising re-grade); **open and required**
    where § 5.2 requires it (send back, not a fault, *Change severity* when
    the chosen grade is lower) (BR4-01).
    *Acknowledge* and *Start* open with the line **"Recording as <name>"** —
    `recording_as`, the person this move will auto-assign (§ 5.8), else
    **"Nobody will be assigned"** — so a kiosk left logged in shows whose
    name goes on the ticket (BR4-04).
  - **Significant moves are never one tap** (BR3-02): *Close*, *Not a fault*
    and *Send back* are set apart from the chain buttons (placement in *The
    ticket page on a phone*, below), outline style, and their Save is
    labelled for what it does — *Close ticket*, *Close as not a fault*, *Send
    back* — under one line saying the consequence ("TK-2026-10-014 becomes
    read-only"; for send back, the consequence of the answer, below).
    While the ticket has no labour row, *Close* is disabled with **visible
    text** under it, "Add the labour first", and an **Add labour** button
    beside it that opens the labour dialog, so the engineer need not scroll to
    the panel (BR3-05, BR4-02); the server's 409 stays.
  - **Back in service by production** (Plan.MD § 4.2, decided 16-10-2026): a
    supervisor, or anyone with operator rights at the unit, records it and
    **names the technician** from Team who did the work. A technician recording
    it names himself by default; a user with no Team record must name someone
    (a restoration never has an empty technician — ISO 14224 records who did
    the work).
  - **Back in service after the fact** from raised or acknowledged (a
    technician with no phone fixed it, the supervisor types it at shift end):
    the dialog also asks, optionally, **when work started**; given, a *started*
    event is written with that time and the same technician, so the repair
    time is known. This settles Plan.MD § 4.2's *Proposed* "technician arrived".
    The *started* field shows only when the ticket is raised or acknowledged.
    It is a **date** input pre-filled with the back-in-service date and an
    **empty time** input; the pair is sent as `started_at` only when the time
    is filled. The supervisor types one time in the common case and changes
    the date for a night shift (started 23:40, restored 00:30). The
    back-in-service time stays "Now · Change" (BR3-11, BR4-06).
    On a defect the button reads **Fixed** (the machine never stopped); the
    state is the same.
  - **Send back** (engineer): the work is not finished. The engineer says
    whether the machine is **down again**:
    - *yes* → the intensity becomes critical (a change only when it was not),
      so downtime runs again from the send-back time;
    - *no* → the intensity becomes degraded **only when it was critical**
      (the machine runs, work still to do); a degraded or initial ticket keeps
      its grade — a send-back says nothing about how bad the fault is (BR1-01).
    The change, if any, is written on the `sent_back` event itself (§ 4.3).
    The dialog asks "Machine down again?" on a breakdown and "Has the machine
    stopped?" on a defect, as two large Yes / No buttons, each with its
    consequence: "Yes — it becomes a breakdown; downtime runs from now" / "No —
    the machine runs; downtime stops" (the second only on a breakdown)
    (BR3-10). Yes / No is a **choice with a selected state** (like the raise
    screen's intensity buttons), not a submit; *Send back* is the one submit,
    after the required remark (BR4-07). **Send back or raise again?** Send back when the work is not
    finished or not accepted (the machine has not run as repaired); *Not fixed
    — raise again* when the machine ran and the same fault came back. The help
    text of the remark says so (BR3-10).
  - **Close**: the engineer gives the **cause** and the **action** (S016 lists)
    and, if still empty, the **symptom**; at least one **labour row** must
    exist. Closed is final and read-only.
  - **Not a fault** (Plan.MD § 4.2 *frivolous*): from raised or acknowledged,
    the engineer closes with a **cause** and a required remark. No action, no
    labour needed (labour already booked stays: someone did go and look). The
    cause says **why it was raised** — *3.2 Operating error* for a
    mis-operation, *5.1 No cause found* for "looked, nothing wrong" (the
    suggested default) — while the `not_a_fault` flag keeps the ticket out of
    failure counts.
- **Re-grade** the intensity (Plan.MD § 4.2: a defect that gets worse becomes
  critical with the event time; downtime starts then). Any open state before
  back in service. Both directions (BR1-02):
  - **raising** (towards critical) by `ticket:raise` holders: the operator who
    sees the leaking machine stop re-grades it. For him it is one large button
    **"Machine stopped"** on a defect ticket (critical, the same `/regrade`
    call) — no choice of grades: its dialog shows only "Breakdown from: Now ·
    Change", the optional remark and Save *Machine stopped* (BR3-08, BR4-07).
    `regrade_options` lets an operator on an *initial* ticket set degraded as
    well; the page offers him critical only — accepted, the API may allow more
    than the page shows;
  - **lowering** by `ticket:work` holders with a **required remark**: it is the
    technician who says the machine runs, and lowering from critical ends
    downtime. `ticket:work` holders get **Change severity** — and only that,
    not *Machine stopped*, though they hold `ticket:raise` too (BR4-05): the
    raise screen's three large intensity buttons, only the grades they may
    set, the remark open and required when the chosen grade is lower;
  - the same intensity → 400 "Already a breakdown" / "Already a defect"; a
    lowering without remark → 400 "Say why the machine runs" (BR3-11).
  The page shows each control only when the detail's `regrade_to` (the
  grades this user may set now) is not empty, so an operator on a critical
  ticket sees no re-grade control (BR3-04).
- **Edit** while open: component (a non-scrapped node under the ticket's
  machine, or none), symptom (the class rule of S016 § 5.4), description
  (S017's rule: required when no symptom or the symptom is *Other*). Each change
  is a timeline line with old → new. By `ticket:work`. The operator who raised
  the ticket cannot edit it: he tells the technician (accepted, BR2-07).
- **Assign** (engineer): add or remove technicians at the ticket's site
  (§ 5.8), in any state before closed, including back in service (the engineer
  names who completes the job). Every `ticket:work` holder who acknowledges or
  starts is added automatically when he has a Team record (an engineer who
  presses *Start* is working it; he can unassign himself), with an *assigned*
  line in the timeline like a manual assignment (BR2-06). The Tickets list
  gains **Assigned to me** (shown only to a user with a Team record, BR3-04;
  for an IT admin with a Team record it shows and stays empty, since he is
  never assigned — accepted, BR4-08) and the assignees' first names on each
  row (BR3-11). *Unassign* asks inline
  "Remove <name>? Yes / No" on the row (BR3-02).
- **Labour** (Plan.MD § 4.2, S010): rows of person, **trade worked**, date and
  time spent (hours and minutes). The trade is required when the person has at
  least one trade (pre-filled when exactly one), optional otherwise (a
  contractor firm may have none); any active trade is accepted, the person's
  own offered first — the trade *worked*, not the trade held (BR1-08). Added,
  changed and removed by `ticket:work` until the ticket closes. A new row
  defaults to the user's own person **when he qualifies for the labour field
  at the ticket's site** (his `person_id` is in the picker's list for the
  ticket — the same check the server makes on save, § 5.8), else empty;
  today; and that person's only trade (BR4-03); hours and minutes are two number inputs, and a
  zero total is refused in the dialog (BR3-06). *Remove* asks inline "Remove?
  Yes / No" on the row (BR3-02).
- **"Not fixed — raise again"**: on a ticket whose latest **back-in-service
  time** lies within the last 7 days (back in service or closed), a button opens S017's
  raise screen pre-filled with the same machine, component and symptom, the
  old ticket's **current intensity** (the user may raise it), and **repeat of**
  this ticket. The new ticket's page links to the old one and the old one lists
  it (§ 5.5).
- **Times on the ticket page** (computed, never stored):
  - **response time** — raised → first acknowledged or started;
  - **repair time** — EN 13306 *active corrective maintenance time*: the time
    spent in *in progress* (summed over send-backs);
  - **downtime** — EN 13306 *down time*, the *time to restoration* of a
    breakdown: the time while the intensity was critical and the state was not
    yet back in service (or after a send-back with the machine down).
  An unknown part (no started event) shows "—", not a guess. On a ticket
  closed as not a fault the times row is hidden (BR3-11).
- **The ticket page on a phone** (BR3-03, BR4-05): the action bar comes
  **first, under the header**, as full-width stacked buttons, in this order:
  1. the next move in the chain (*Acknowledge*, *Start*, *Back in service* /
     *Fixed*);
  2. **Machine stopped** (an operator on a defect) or **Change severity**
     (`ticket:work` holders, this one only);
  3. **Not fixed — raise again**, when it applies;
  4. after a gap, *Close* / *Not a fault* / *Send back*, outline style (the
     "apart" of BR3-02 is vertical on a phone).

  On a wider screen the same buttons sit in one row, the significant ones on
  the left. Then the times, assignees and labour, **shown only to
  `ticket:work` holders or when not empty**; *Edit* and *Assign* sit with
  these panels, not in the action bar. Then repeats (hidden when none), photos
  and the timeline. Empty panels say so: "No labour yet", "Nobody assigned".
- **Codes frozen once in use**: cause and action codes, like the mode in S017.

### Out of scope

- Scheduled state, planned date, waiting reasons and the waiting / repair
  split of downtime — **S019**.
- Parts used, raise-and-close in one screen — **S020**.
- Notifications on assignment and escalation; "not closed by end of shift"
  list — **S021**.
- **Correcting a recorded event time.** In S018 an event's time is final once
  written; a mistyped time stays (BR1-06). A correction route — engineer,
  reason required, a timeline line old → new, the order rule re-checked — is
  **queued** (README Queued). Computing the times from the events (decision 5)
  is what will make that correction cheap.
- Reports over many tickets (MTBF, MTTR per unit, downtime by cause) —
  phase 5. This step shows each ticket's own figures.
- Labour cost (Plan.MD § 2, not in v1).
- **An operator linking a repeat after the old ticket is closed** (BR3-01;
  user, 20-10-2026: not a priority). The *Not fixed — raise again* button is
  only on the old ticket's page; an operator who raises afresh from the
  equipment page makes an unlinked ticket, so the repeat count understates
  repeats. A raise-screen "fixed recently — it's this again?" list or a
  *Raised by me* view can come later.

## 2. Standards and practice

- **EN 13460**: the **work order** records who did what, when, with what
  result, and who signed it off. Here: labour rows, the action code, the
  timeline, and the engineer's close.
- **ISO 14224** maintenance record: **maintenance activity** (our action
  code, Table B.5), **failure cause** (Table B.3), **man-hours per discipline**
  (our labour rows with trade worked, Table 8 — why the trade is required when
  the person has one), **active maintenance time** and **down time**. It
  counts a failure from its event time to restoration.
- **EN 13306** time terms, which name our two figures:
  - **down time** — the item is not able to perform; for a breakdown it runs
    from the failure to **restoration** and is the **time to restoration**.
    Its mean over breakdowns is **MTTR** (mean time to restoration). Our
    **downtime**;
  - **active corrective maintenance time** — the time hands are on the
    machine. Our **repair time**.
  The difference between the two is waiting (logistic and administrative
  delay), which S019 splits out. Both matter: downtime is what production
  loses, active time is what maintenance controls.
- **SMRP Best Practice metrics**: MTTR (metric 3.5.5) runs from failure to
  restoration (Plan.MD Q4, decided 15-10-2026: downtime ends at back in
  service) — our downtime, not our repair time. Tickets closed as not a fault
  are left out of MTBF/MTTR (Plan.MD § 4.6). **Response time** has no SMRP or
  EN 13306 definition: it is the plant's own work-management measure
  (Maintenance-Philosophy § 10).
- **Restoration confirmed by production**: EN 13306 defines *restoration*;
  having the requester confirm it (our back in service by the supervisor) is
  common CMMS practice, not the standard's term.
- **ISO 55001 § 7.5 / § 9.1**: the closed work order is the asset information
  the management system evaluates performance from — which is why close
  requires cause, action, symptom and labour.
- **ISO 9001 § 10.2** (nonconformity and corrective action; Plan.MD's
  *Standards* decision asks each brief to name its clause): the closed ticket
  with cause, action and labour is the corrective-action record § 10.2 asks
  for — what happened, why, what was done, by whom — and the repeat link is its
  "review the effectiveness of the corrective action" (BR2-09).
- **ISO 27001**: the four keys give each role only what it needs, per site
  (A.5.15 access control, least privilege); the timeline with `created_by` /
  `created_at`, immutable in S018, is the activity log A.8.15 asks for
  (BR2-09).
- **TPM**: the engineer closes the tag with cause and action the same shift
  (Plan.MD Q12, closing discipline); a fault that comes back is a **repeat**,
  counted, which is what focused improvement works on. That is why "not fixed"
  is a linked new ticket (user decision): each failure is counted once, the
  repeat is visible.

## 3. Where

### Backend
- **`backend/local_db.py`** — migration **v13** "Ticket work": columns on
  `tickets` and two tables (§ 4). Every statement safe to run twice (`ADD
  COLUMN IF NOT EXISTS`, `FOREIGN KEY IF NOT EXISTS`, `CREATE TABLE IF NOT
  EXISTS`, as v5, v9, v11).
- **`backend/config_rbac.py`** — keys **`ticket:work`**, **`ticket:restore`**,
  **`ticket:assign`**, **`ticket:close`** (§ 5.7), all in `SITE_SCOPED`.
- **`backend/auth_utils.py`** — a public **`current_person_id(cur)`**: the
  existing private `_person_id` (cached on `g`) exposed under that name; the
  person whose login is the user's, or None (BR1-11). Used for the default
  technician, auto-assign, the labour default and *Assigned to me*.
- **`backend/app.py`** — `/api/auth/me` gains `person_id` (or null), so the
  page shows *Assigned to me* and the labour default only to a user with a
  Team record (BR3-04, BR3-06). In the `DBUnavailable` branch (token
  permissions only) `person_id` is null (BR4-08).
- **`backend/tickets_core.py`** (S017's, extended; pure):
  - `MOVES` — the table of § 1 as data: move → allowed from-states, to-state,
    key, required fields;
  - `allowed_moves(state, intensity, held_keys)` → the moves the user may make
    now — the page shows only these buttons. No `needs_person`: the core cannot
    know whether the user has a Team record, so the route adds
    `default_person` to the `restore` entry and `recording_as` to
    `acknowledge` and `start` (BR2-03, BR4-04);
  - `validate_event_time(event_time, last_event_time, now)` — S017's
    `event_time_error(event_time, now, not_before=last_event_time)`: not before
    the ticket's last event, not in the future beyond `FUTURE_SKEW`, not older
    than `MAX_BACKDATE_DAYS` (S017's constants). The window rule exists once, in
    S017 (BR1-14); the wrapper only adds the last event's name and time to the
    message (BR2-07);
  - `send_back_intensity(current, machine_down)` → the new intensity or None
    (§ 1);
  - `validate_regrade(current, new, lowering_allowed, remark)`;
  - `regrade_options(current, lowering_allowed)` → the intensities this user
    may set now (higher ones always, lower ones with `ticket:work`); the
    detail's `regrade_to` (BR3-04);
  - `validate_close(ticket, body, labour_count)`,
    `validate_not_a_fault(body)`, `validate_labour(body, person_has_trades)`
    (minutes 1–1440 per row, date not in the future nor before the ticket's
    event time);
  - `ticket_times(events, now)` → `{response_minutes, repair_minutes,
    downtime_minutes}` (§ 5.4);
  - `is_repeat_candidate(back_in_service_at, new_occurred_at)` — 0 ≤ new −
    restoration ≤ `REPEAT_WINDOW_DAYS`, the old ticket's **latest**
    `back_in_service` (§ 5.5, BR2-05);
  - `edit_lines(old, new, labels)` → the timeline remark for an edit.
- **`backend/tickets.py`** — the routes of § 6; each move in one transaction
  (§ 5.3). S017's people picker gains a second anchor, **`?ticket_id=<id>`**:
  the ticket by S017's access predicate (404 otherwise), `ticket:read` checked
  at the **ticket's site** (the site of `tickets.unit_id`), the people and their
  roles at that site. `equipment_id` stays for the raise screen; one helper
  `_people_at_site(cur, site_id)` behind both (BR2-02). The rows carry each
  person's **role at the site**, so the page lists only who qualifies (§ 5.8);
  S017's `_people_at_site` already returns `role`, so only the anchor is new
  (BS1-04). The route keeps `@require_perm("ticket:raise")`; with `ticket_id`
  it reads the ticket by the access predicate (404), then
  `require_perm_at("ticket:read", <ticket's site>)`. One of `equipment_id` /
  `ticket_id` is required (400 otherwise). **`GET /api/tickets/modes`** gains
  the same `?ticket_id=` anchor: the class from the ticket's machine,
  `ticket:read` at the ticket's site, so the close and edit dialogs still get
  their symptoms after the machine moved to a unit the user cannot see
  (BS1-08).
  The moves, edit, re-grade, labour and assignment routes **extend S017's
  `_lock_ticket(cur, ticket_id, key)`** (lock `FOR UPDATE` → 404 by the access
  predicate → 403 at the ticket's site): its locked SELECT gains `intensity`,
  `failure_mode_id`, `equipment_id`, `occurred_at`, and every refusal is
  decided from that row; no parallel helper. S017's `TICKET_CLOSED` 409 ("This
  ticket is closed") answers a write on a closed ticket; "This ticket changed —
  reload" a stale state (BS1-05).
  The detail gains `permissions` (the user's
  keys at the ticket's site, `permissions_at_site`, as S017's node detail)
  and `regrade_to` (BR3-04).
- **`backend/masters.py`** — cause and action code frozen once a ticket uses
  them (§ 5.6); `_update_plain_master` gains a `used_by` parameter
  (`("tickets", "cause_id")`, `("tickets", "action_id")`), since causes and
  actions share it (BR2-07); it keeps the row `_lock_row` returns and compares
  the code to it, as `update_failure_mode` does (BS1-03).
- **`backend/equipment.py`** and **`backend/tickets.py`** docstrings — the
  lock-order note gains the moves, edits, labour and assignment writes:
  "(7) only; nothing else locked" (BR1-15).
- **`backend/documents.py`** — tickets take documents as well as photos (user
  decision 5). No owner restricts kinds any more, so S017's `Owner.kinds`
  field and its photos-only refusal (400 "Only photos can be added here") are
  removed rather than left as a one-use setting; the three photos-only
  comments (`OWNERS["ticket"]`, the module docstring, `file_store.py`) are
  updated (BS1-01). The write key stays
  `ticket:raise` (S017's `Owner` has one write key per owner, and a per-kind key
  would be a second change to its pattern). The ticket page offers *Add
  document* to `ticket:work` holders only (UI); the raise screen stays
  photos-only; an operator posting a PDF through the API is accepted — the
  same class of information as his photos, served only through the checked
  routes (ISO 27001 A.8.3) (BR2-04).

### Frontend
- **`components/FormModal.vue`** (shared) — the dialog gains
  `modal-dialog-scrollable`: the body scrolls, the header and the footer with
  Save stay on screen, so a long dialog never pushes its buttons below a
  phone's fold (BR3-03). One class; **every existing dialog in the app
  inherits it**, which is wanted.
- **`views/TicketDetailView.vue`** — the layout of § 1 *The ticket page on a
  phone*: action bar first, in its stated order (the moves from `moves`,
  *Machine stopped* or *Change severity*, *Not fixed — raise again*, then the
  significant moves after a gap; BR4-05); the disabled *Close* with its
  visible reason and *Add labour* (BR4-02); then times, assignees,
  labour panel, repeat links, photos and documents (*Add document* for
  `ticket:work` holders, user decision 5: the page drops `photos-only`, keeps
  `large-add`, passes `:can-edit="ticket.can_add_photos"` and
  `:can-edit-documents="ticket.can_add_documents"`, BS1-02), timeline; controls other than moves
  shown from the detail's `permissions` and `regrade_to`, so a user without
  the key sees no button, never a 403 (BR3-03, BR3-04). The timeline renders
  an intensity change ("Defect → Breakdown") from the events' `intensity`
  column, the remark stays the user's (BR1-12).
- **`components/documents/DocumentsCards.vue`** — gains a `canEditDocuments`
  prop (default: `canEdit`) for the Documents card's *Add document*, edit and
  remove; equipment and model pages are unchanged (BS1-02).
- **`components/documents/DocumentUploadModal.vue`** — the "Everyone who can
  see this ticket can see it." line is keyed on the owner being a ticket, not
  on `photosOnly`, so it shows for a document too (BS1-02).
- **`views/tickets/MoveDialog.vue`** (new) — one dialog for every move: time
  as "Now · Change" (*Change* fills the phone's now; sent only when changed),
  the remark behind *Add remark* where optional and open where required
  (send back, not a fault; BR4-01), "Recording as <name>" / "Nobody will be
  assigned" on acknowledge and start (BR4-04), and the fields the move needs
  (on back in service the person, always shown and required, pre-filled from
  `default_person`; started-at only from raised or acknowledged, as a date
  input plus an empty time input, sent only when the time is filled (BR4-06);
  down again as two choice buttons with a selected state for send back
  (BR4-07); symptom, cause, action for close; cause for not a fault). Save
  labelled per move, with the consequence line for close, not a fault and
  send back (BR3-02, BR3-09, BR3-10).
- **`views/tickets/PersonPicker.vue`** (new) — the people list **grouped and
  ordered**: **the user's own person first** when he is in the list (BR4-03),
  then the ticket's assignees, then technicians, engineers and managers at the
  site (contractor firms included), then everyone else the field allows; a
  type-to-filter box on top. Used by back in service, labour and assign; in
  the Assign dialog the people already assigned are left out and the ladder
  leads (BR3-07, BR4-08).
- **`views/tickets/LabourPanel.vue`** (new) — rows, add / edit / remove; the
  defaults of § 1; remove confirmed inline (BR3-02, BR3-06).
- **`views/tickets/AssignDialog.vue`** (new), **`EditTicketDialog.vue`** (new;
  the component list from the machine's `GET /api/equipment/<id>` detail —
  its `children`, two levels, non-scrapped ones offered, BR3-11),
  **`RegradeDialog.vue`** (new; *Change severity*, the remark open and
  required when lowering; opened from *Machine stopped* it hides the grade
  buttons and shows "Breakdown from: Now · Change" and Save *Machine stopped*;
  BR3-08, BR4-01, BR4-07).
- **`stores/auth.js`** — `loadProfile` keeps `/auth/me`'s `person_id` in a
  `userPersonId` ref, for `TicketsView` and the labour default (BR4-08).
- **`views/TicketsView.vue`** — *Assigned to me* filter (shown when
  `userPersonId` is set); assignees' first names on each row; closed tickets
  show *Not a fault* when so.
- **`views/RaiseTicketView.vue`** — opened as
  `/tickets/new?equipment=<component or machine id>&repeat_of=<id>`. After the
  node loads (and after `resetForm()`, which runs on every node change), the
  screen reads `GET /api/tickets/<id>` and pre-fills the symptom
  (`failure_mode.id`) and the intensity; Save sends `repeat_of_id`. S017's
  `validate_raise` gains `repeat_of_id` through `_optional_id`, as
  `reported_by_id` (BS1-07).
- Causes and actions for the close dialog come from the masters store
  (`ensureFailureCauses()`, `ensureMaintenanceActions()`, S016); symptoms from
  S017's `GET /api/tickets/modes`, anchored on the ticket (`?ticket_id=`,
  BS1-08); people from S017's picker anchored on the ticket (`?ticket_id=`)
  (BR1-10, BR2-02, BR2-07).
- **`utils/ticketLabels.js`** — move labels ("Fixed" for a defect's back in
  service), Save labels per move, the send-back question per intensity,
  intensity change text, minutes as "1 h 25 min".

### Tests
- `backend/tests/test_tickets_core.py` — § 8.
- `backend/tests/test_ticket_work_api.py` (new) — § 8. It imports S017's
  helpers, or moves them to `conftest.py`, rather than copying them:
  `TICKETS`, `make_mode`, `make_ticket`, `set_ticket_state` (its docstring
  "S017 never changes a state" updated), and `test_tickets_api.py`'s
  `_now_ist`, `_local`, `_api_time`, `_refusal`, `give_site_role`, `operator`,
  `machine` (BS1-06).
- `backend/tests/test_documents_api.py` — S017's
  `test_a_document_kind_is_400_before_the_file_is_read` becomes: a `document`
  on a ticket → 201, stored under `tickets/<id>/`, listed (BS1-01).
- `backend/tests/test_migration_v13.py` (new).
- `backend/tests/test_rbac.py` — `TestComputePermissions.test_role_matrix`
  rows and per-key holders tests (§ 8).
- `backend/tests/test_failure_codes_api.py` — cause and action code freeze.
- `backend/tests/conftest.py` — `_TABLES` gains `ticket_labour` and
  `ticket_assignees` before `tickets` (child tables first).
- `frontend/tests/ticketLabels.test.js` — the new labels.

### Docs (at approval, by the planner)
- `docs/Plan.MD` § 3 (the four keys replace `breakdown:work`,
  `breakdown:close`), § 4.2 (moves, not a fault, send back with "down
  again", repeat; *Timestamps* named as in § 2 here; the *Proposed*
  "technician arrived" settled by `started_at`), § 5 (`ticket_labour`,
  `ticket_assignees`), § 9 Q4 closed.
- `docs/Maintenance-Philosophy.md` § 10: **MTTR** = mean time to restoration
  (downtime ÷ breakdowns), plus a second line *mean active repair time* (repair
  time ÷ breakdowns); response time marked as the plant's own measure.
  Glossary: response time, repair time (active corrective maintenance time),
  downtime (time to restoration), repeat failure, not a fault.
- `docs/steps/README.md` Queued: "Correct an event time on a ticket" (BR1-06).

## 4. Data model (migration v13)

### 4.1 `tickets` gains

| Column | Type | Notes |
|---|---|---|
| `cause_id` | INT NULL | FK `fk_tickets_cause` → `failure_causes`; set at close |
| `action_id` | INT NULL | FK `fk_tickets_action` → `maintenance_actions`; set at close (NULL when not a fault) |
| `not_a_fault` | TINYINT(1) NOT NULL DEFAULT 0 | closed as not a fault |
| `repeat_of_id` | INT NULL | FK `fk_tickets_repeat_of` → `tickets`; same machine (§ 5.5) |

Index `ix_tickets_repeat_of (repeat_of_id)`.

### 4.2 New tables

**`ticket_assignees`**: `ticket_id` (FK `fk_ticket_assignees_ticket`),
`person_id` (FK `fk_ticket_assignees_person` → `people`), `assigned_at`,
`assigned_by`; PK `(ticket_id, person_id)`. Removing an assignee deletes the
row and writes an *unassigned* event (the timeline is the history).

**`ticket_labour`**:

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | |
| `ticket_id` | INT NOT NULL | FK `fk_ticket_labour_ticket` |
| `person_id` | INT NOT NULL | FK `fk_ticket_labour_person` → `people` |
| `trade_id` | INT NULL | FK `fk_ticket_labour_trade` → `trades`; the trade worked (S010) |
| `work_date` | DATE NOT NULL | |
| `minutes` | SMALLINT NOT NULL | 1–1440, CHECK `chk_ticket_labour_minutes` |
| `created_at`, `created_by`, `updated_at`, `updated_by` | | |

Index `ix_ticket_labour_ticket (ticket_id)`, `ix_ticket_labour_person
(person_id, work_date)` for the daily work log later (Plan.MD § 4.6).

Removing a labour row is a hard delete with no timeline line: the ticket is
open, the rows carry their audit columns, and labour is not part of the
failure's story (accepted, BR1-16).

### 4.3 `ticket_events`

`event` values: `raised` (S017), `acknowledged`, `started`,
`back_in_service`, `sent_back`, `closed`, `closed_not_a_fault`, `regraded`,
`edited`, `assigned`, `unassigned`.

- **Every change of intensity, whichever move causes it, is written to the
  `intensity` column of that move's own event** — `raised`, `regraded`, and a
  `sent_back` that changes it; NULL when unchanged. `ticket_times` reads
  nothing else (BR1-01). A send-back that changes the intensity is one
  timeline line, not a `sent_back` plus a `regraded`.
- `person_id` holds the technician named on `back_in_service` and on the
  `started` written with it, and the person assigned or unassigned.
- `remark` is always the user's text, except on `edited`, where it holds the
  generated old → new lines (an edit takes no user remark). The page renders an
  intensity change from the column (S017's detail exposes the events'
  `intensity`).

## 5. Rules

### 5.1 Event times

Every move, re-grade and back-in-service-after-the-fact `started` time passes
`validate_event_time`: not before the ticket's latest event (events stay in
order, so the times can be computed), at most `FUTURE_SKEW` ahead, at most
`MAX_BACKDATE_DAYS` back. The `started` time given with back in service must
lie between the last event and the back-in-service time.

- **Default = the server's clock.** The dialogs send no `occurred_at` unless
  the user changed the time field, so a phone running a few minutes fast or
  slow cannot put a move "before the last event" on a ticket nobody back-dated
  (BR1-05). S017's raise screen follows the same rule.
- A refused time names the last event and its time: "Must be at or after
  *Acknowledged*, 20-10-2026 10:04".
- Accepted consequence: an operator who re-grades at "09:30" after the
  technician acknowledged at 09:40 must enter 09:40 or later; downtime starts
  there.
- Event times are immutable once written (Out of scope; correction queued).
- **"The latest event" means the latest event that moves the state or the
  intensity** (`tickets_core.ORDERED_EVENTS`); *assigned*, *unassigned* and *edited*
  lines are bookkeeping, stamped with the server's clock, and hold no typed time
  back. Decided by the user at gate B, 21-10-2026 ("Keep the typed-times rule").

### 5.2 Fields each move needs

- **Back in service**: `person_id` **always required**, an active person who
  may be named (§ 5.8). The dialog always shows the field, pre-filled from the
  `restore` move's `default_person` — `current_person_id(cur)` when the user
  holds `ticket:work` at the ticket's site **and his person qualifies for this
  field at the ticket's site** (the § 5.8 role check the server makes on save,
  as auto-assign does), else none — and the user may change it. A
  `ticket:work` holder with no Team record, or one who does not qualify there
  (IT admin), sees it empty and must name someone (400 on `person_id` "Who did
  the work? Pick a name") (BR2-03, BR3-11, BR4-03). **One rule for every
  default of the user's own person** (back in service, labour): offered only
  when he qualifies for that field at the ticket's site, else empty (BR4-03).
- **Send back**: `machine_down` (yes / no) and a remark, both required.
- **Close**: `cause_id`, `action_id` (active), `failure_mode_id` when the
  ticket has none (the S016 class rule). A `failure_mode_id` given on a ticket
  that has one **overwrites** it (the engineer corrects the operator's pick;
  same class rule), written as an *edited* line before the *closed* line
  (BR2-07); the description rule of S017 § 5.1
  (a close that sets *Other* with an empty description is 400 on
  `description`); at least one labour row (409 "Add the labour before
  closing").
- **Not a fault**: `cause_id` and remark required.
- **Re-grade**: a different intensity; lowering needs `ticket:work` and a
  remark. The route is `@require_perm("ticket:raise")` (every holder of either
  direction has it); the direction is decided inside, lowering checked against
  `ticket:work` at the ticket's site (BR2-07).

### 5.3 Transactions and locks

Each move, edit, re-grade, assignment and labour change is one transaction:
lock the **ticket row (7)** `FOR UPDATE`, decide every refusal from the locked
row (state, intensity: a stale page that offers a move gets 409 "This ticket
changed — reload"), check the key at **the ticket's site — the site of
`tickets.unit_id`**, the unit at raise, not the machine's current site
(S017 § 5.3 opens the page by either unit; the keys are checked at the
ticket's own, BR1-15), write the ticket, the event, and the labour / assignee
rows. Codes and people are read plain; the FK inserts take their shared locks,
which serialise with masters' code freeze (§ 5.6). Ticket rows are always
locked last in the global order (S017 § 5.4), and these transactions lock
nothing else, so no cycle. Two moves on the same ticket queue on its row; the
second sees the first's state.

### 5.4 The times (`ticket_times(events, now)`)

From the events, oldest first (`ORDER BY occurred_at, id`), keeping a running
state and intensity (each event's `intensity` column, § 4.3: set on `raised`,
on every `regraded` and on a `sent_back` that changes it, NULL when
unchanged; `now` is passed in):
- **response** = first `acknowledged` or `started` − `raised`; none yet → null;
- **repair** (active corrective maintenance time) = sum of intervals from
  `started` (or `sent_back`) to the next `back_in_service`; a back in service
  with no `started` before it → null (unknown, shown "—");
- **downtime** (time to restoration) = sum of intervals while intensity is
  critical and the state is raised, acknowledged or in progress, ending at back
  in service; an open ticket counts up to `now`;
- every interval is clamped at zero: the last event may lie up to
  `FUTURE_SKEW` after `now` (BR1-14);
- not-a-fault tickets return all three as null: they are no failure.

### 5.5 Repeat

`repeat_of_id` on raise (S017's route gains the field): the earlier ticket
must be on the **same machine**, readable by the user, and its **latest
`back_in_service` event time** must lie at most `REPEAT_WINDOW_DAYS` (7)
before the new ticket's `occurred_at` and **not after it** (0 ≤ new −
restoration ≤ 7 days: a failure timed before the restoration is not a repeat
of that repair); its state is back in service or closed, either way (BR1-09,
BR2-05). The button on the old ticket is shown against *now*; the server's rule
governs, so a back-dated raise can still be refused (400). A ticket closed as not a fault has no restoration and so
cannot be repeated: "it is back" on a not-a-fault ticket is an ordinary new
ticket. The old ticket is not locked (only read): the new ticket points at it;
nothing on the old one changes. The old ticket's page lists its repeats by a
query, not a stored list.

### 5.6 Cause and action codes frozen once in use

As S017's code does for modes (`masters.update_failure_mode`; the code
departed from the S017 brief's § 5.7): a code change on a cause or action used
by a ticket → 409 on `code`, with the same message ("This code is used by
tickets and can no longer change"); label, description, active and (for a
cause) the group stay editable (S016 § 5.4: the group stays editable once in
use). `_update_plain_master` keeps the row `_lock_row` returns, compares
`clean["code"]` with **the locked row's** code, and counts `tickets WHERE
<used_by column> = %s LOCK IN SHARE MODE` before `update_row`: a plain count
against an earlier snapshot would miss a close that holds the cause's or
action's FK lock and commits in between (BS1-03). It is generic, so it takes
the ticket column per table as a `used_by` parameter (BR2-07).

### 5.7 Permissions

| Key | operator | supervisor | technician | engineer | manager | it_admin |
|---|---|---|---|---|---|---|
| `ticket:work` | | | ✓ | ✓ | ✓ | ✓ |
| `ticket:restore` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket:assign` | | | | ✓ | ✓ | ✓ |
| `ticket:close` | | | | ✓ | ✓ | ✓ |

`ticket:restore` is granted to `maint_operator` (the supervisor inherits it;
Plan.MD § 4.2: "whoever has operator rights at the unit"). The supervisor stays
off the maintenance ladder: no `ticket:work`. IT admin holds all four (S017
user decision 7) at every site as a token role. It holds no role at a site,
so it is never assignable and never auto-assigned, Team record or not, is
never offered as a default person, and must name the person on back in
service and labour (§ 5.2, § 5.8, BR3-12, BR4-03). All four site-scoped. They replace Plan.MD's `breakdown:work` and
`breakdown:close`.

### 5.8 Who may be picked

All pickers draw on S017's people picker anchored on the ticket
(`?ticket_id=`, § 3): active people with a membership at the ticket's site,
now including phone-less operators (user decision, 20-10-2026).

**Decided at gate A (user decision 7, open question 4 option (a); BR2-01):**
- **Assignee**: a person whose role at the ticket's site is **technician,
  engineer or manager** — assignment hands out maintenance work. Contractor
  firms hold a technician row (S011 A1), so AMC vendors qualify.
- **The person named on back in service, and a labour person**: **any active
  person with a membership at the ticket's site, operators included**. So a
  defect the operator fixed himself (a loose guard, a blocked nozzle) is
  recorded truthfully — TPM autonomous maintenance expects operators to clear
  what they can, and the operator-fixed share is a measure of its progress. An
  operator row carries no trade, so it falls out of every per-discipline sum by
  itself: ISO 14224 Table 8 stays maintenance man-hours.
- **Reported by** (S017) stays any person at the site.

The server checks the role from memberships at the ticket's site; the picker
returns each person's role so the page lists only those who qualify for each
field. On the page, `PersonPicker.vue` groups and orders them — the user's
own person first when he is in the list, then the ticket's assignees, then
technicians, engineers and managers, then everyone else the field allows —
with a type-to-filter box, so a site-wide list of a hundred names stays
usable on a supervisor's phone, and an operator who fixed his own defect finds
himself at the top. In the Assign dialog the people already assigned are left
out and the ladder leads (BR3-07, BR4-03, BR4-08).

Auto-assign on acknowledge / start applies the **same role check as a manual
assignment**: the user's person (`current_person_id(cur)`) is added only when
his role at the ticket's site is technician, engineer or manager, and it
writes an *assigned* event like a manual assignment. A user with no Team
record, or whose person is not assignable there (IT admin), is simply not
added (BR3-12). The move's `recording_as` is exactly this person — the one
this move will auto-assign — else null (BR4-04). Assigning a person already assigned → 200 with no change
(idempotent: two taps on a phone); removing a person who is not assigned → 404
(BR2-06). *Assigned to me* for a user with no person returns an empty list.

## 6. API

All under `/api/tickets/<id>`:

| Method | URL | Key | Body |
|---|---|---|---|
| POST | `/moves/<move>` | per § 1 | `{occurred_at?, remark?, person_id?, started_at?, machine_down?, failure_mode_id?, cause_id?, action_id?}` → the ticket |
| POST | `/regrade` | `ticket:raise` at the route; lowering also `ticket:work` at the ticket's site, checked inside | `{intensity, occurred_at?, remark?}` |
| PUT | `/` (the ticket) | `ticket:work` | `{component_id?, failure_mode_id?, description?}` |
| POST / DELETE | `/assignees`, `/assignees/<person_id>` | `ticket:assign` | `{person_id}` |
| POST / PUT / DELETE | `/labour`, `/labour/<row_id>` | `ticket:work` | `{person_id, trade_id?, work_date, minutes}` |

`<move>` is one of `acknowledge`, `start`, `restore`, `send-back`, `close`,
`not-a-fault`. The detail (S017's `GET /api/tickets/<id>`) gains `cause`,
`action`, `not_a_fault`, `repeat_of`, `repeats`, `assignees`, `labour`,
`times`, `moves` (= `allowed_moves` for this user; the `restore` entry
carries `default_person: {id, name} | null`, BR2-03, BR4-03; on
`acknowledge` and `start` a `recording_as: {id, name} | null` — the person
this move will auto-assign, else null — for the dialog's line, BR3-09,
BR4-04),
`permissions` (the user's keys at the ticket's site) and `regrade_to` (the
intensities this user may set now; empty → no re-grade control) (BR3-04), and
`can_add_documents` beside S017's `can_add_photos` (not closed and
`ticket:work` at the ticket's site; sent by the server, since the keys are
site-scoped and the page does not work out permissions, BS1-02); its
events already carry `intensity` (S017). The list gains `assigned=me` and the
assignees' first names per row. `/api/auth/me` gains `person_id` (BR3-04). People come from S017's
`GET /api/tickets/people?ticket_id=<id>` — the anchor S018 adds, people and
roles at the ticket's site (§ 3, BR2-02); symptoms from S017's
`GET /api/tickets/modes?ticket_id=<id>` (BS1-08); causes and actions from the masters endpoints
(S016) — no ticket-specific copies (BR1-10).

## 7. Design decisions

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| 1 | **Moves as data** (`MOVES`) in the pure core; one move route | One place says who moves what; the page shows exactly the allowed buttons; tests run without the DB | One route and one hand-written check per move |
| 2 | **Start straight from raised; back in service from raised / acknowledged** | Matches the floor: a technician who walks up and fixes it doesn't press three buttons; the supervisor's after-the-fact record works | Strict chain (forces fake intermediate events with invented times) |
| 3 | **"Not fixed" is a new linked ticket** (user decision) | Each failure counted once; repeats visible for focused improvement | Operator reopens (one failure's record would hold two events; MTTR understated) |
| 4 | **Send back asks "machine down again?"**; "no" lowers only a critical ticket; the change rides on the `sent_back` event | Downtime follows a fact the engineer states; no invented grade; one source for the times | Always resume downtime; "no" always to degraded (turns an early sign into a partial failure) |
| 5 | **Times computed from events, not stored** | One source of truth; a later correction route fixes every figure at once | Columns `acknowledged_at`, … (two copies to keep in step) |
| 6 | **Labour required at close, not at back in service** | Production may record back in service without knowing hours; the engineer completes the record before closing (Plan.MD Q12) | Required at back in service (blocks the supervisor) |
| 7 | **Raise the grade by `ticket:raise`, lower it by `ticket:work` with a remark** | The operator sees the machine stop first; lowering ends downtime and is a maintenance judgement | Any direction by anyone (a breakdown's downtime could vanish unexplained); engineers only (delays the downtime start) |
| 8 | **Assignees from the maintenance ladder; the back-in-service person and labour from anyone at the site** (user, gate A) | Assignment hands out maintenance work; an operator who fixed a defect is recorded truthfully, and his rows carry no trade, so Table 8 sums stay maintenance man-hours | Ladder only for all three (no honest record of an operator-fixed defect, BR2-01); anyone for all three (operators assigned maintenance work) |
| 9 | **Default event time = the server's clock** | Phone clock skew cannot break the event order | Send the phone's time always (spurious "before the last event" refusals) |
| 10 | **Trade worked required when the person has trades** | Man-hours per discipline (ISO 14224 Table 8) need it; any active trade, as people work outside their main trade | Always optional (loses Table 8); only the person's trades (wrong for multi-skilled work) |
| 11 | **Significant moves labelled and set apart; row removals confirmed inline** (BR3-02) | Close, not a fault and send back are final or undo production's word; a gloved thumb must not hit them by mistake; the S003 scrap confirm is the pattern | An undo toast (no toast pattern in the app; labour removal is a hard delete) |
| 12 | **`FormModal` scrolls inside, footer fixed** (BR3-03) | Save stays on a phone screen with the keyboard up, for every dialog in the app | Close as its own page (a page for three selects) |
| 13 | **Controls from the detail's `permissions` and `regrade_to`** (BR3-04) | Keys at the ticket's site: no button that ends in a 403, no empty re-grade dialog | The global `/auth/me` list (wrong after a cross-site membership); a `can_*` flag per control (the same with more names) |

## 8. Tests and acceptance

### Pure (`test_tickets_core.py`)
- `allowed_moves` for every state × key set (the table of § 1);
- `validate_event_time`: before the last event refused, equal accepted,
  future and back-dating limits; `validate_raise` still passes S017's cases on
  top of it;
- `send_back_intensity`: yes on degraded/initial → critical, yes on critical →
  None; no on critical → degraded, no on degraded/initial → None;
- `validate_regrade`: same intensity refused; lowering without `ticket:work`
  or without remark refused;
- `regrade_options`: operator on critical → empty; operator on initial →
  degraded, critical; technician on degraded → initial, critical;
- `ticket_times`: straight path; start from raised; back in service after the
  fact with and without started time (repair null without); send back with
  machine down (downtime resumes) and running from critical (downtime stops,
  the `sent_back` event's intensity); defect re-graded critical (downtime from
  the re-grade); lowered from critical (downtime stops); open ticket against
  `now`; last event after `now` (clamped at zero); not a fault → all null;
- close validation: missing cause, action, mode when empty, *Other* without
  description, no labour;
- labour validation: minutes 0 and 1441 refused, date limits, trade required
  when the person has trades;
- `is_repeat_candidate`: 7 days accepted, 8 refused, measured from the
  back-in-service time to the new event time; a new time before the
  restoration refused; the latest of two back-in-service times used.

### API (`test_ticket_work_api.py`)
- every move by an allowed key; each refused by a missing key (403) and from
  a wrong state (409);
- back in service without `person_id` 400 for every user; with it 200; the
  `restore` move's `default_person` is the technician himself, null for a
  supervisor and for a `ticket:work` user with no person; the `started` event
  carries the same person;
- an operator or supervisor named as assignee 400; as the back-in-service
  person and as labour, an operator or supervisor at the site 200, a person
  without a membership at the site 400 (user decision 7, § 5.8);
- the people picker by `ticket_id` after a cross-site move of the machine:
  people and roles of the ticket's site; 404 outside access (BR2-02); neither
  `equipment_id` nor `ticket_id` 400 (BS1-04); the modes list by `ticket_id`
  likewise after the move (BS1-08);
- documents: `can_add_documents` true for a technician, false for an operator
  and on a closed ticket (BS1-02);
- close without labour 409; with it → closed, read-only (edit, labour,
  photo, move all 409);
- not a fault from raised; from in progress 409; labour already booked stays;
- send back with and without machine down: ticket intensity and the
  `sent_back` event's `intensity` as § 1;
- re-grade up by an operator, down by an operator 403, down by a technician
  without remark 400, with remark 200;
- concurrency (BR1-13): one raw connection opens a transaction and holds the
  ticket row `FOR UPDATE`; a thread fires a second move through the test
  client and blocks on the lock; the first connection applies a move and
  commits; the thread's response is 409 (state changed). Plus a plain test: a
  move from a stale state is 409. If the threaded test proves flaky on the dev
  DB, the coder keeps only the plain one and says so;
- assignment: add, remove, events written; after back in service allowed;
  assigning someone already assigned 200 and no second event; removing a
  non-assignee 404; auto-assign on start by a technician and by an engineer
  with a Team record, with its *assigned* event; IT admin with a Team record
  starts → not assigned (BR3-12); *assigned to me* list, empty for a user with
  no person; `/api/auth/me` `person_id` set and null;
- detail: `permissions` are the keys at the ticket's site (a user holding
  operator at the ticket's site and engineer elsewhere gets no
  `ticket:assign`); `regrade_to` empty for an operator on a critical ticket;
  `recording_as` is the person the move will auto-assign: a technician's own
  person; null for a user with no Team record and for an IT admin with one
  (BR3-04, BR3-09, BR4-04);
- `default_person` on `restore`: null for an IT admin with a Team record
  (does not qualify at the site) (BR4-03);
- `/api/auth/me` `person_id` null when the database is down (BR4-08);
- back in service with `started_at` the evening before and the restoration
  after midnight accepted; `started_at` after the restoration 400 (BR4-06);
- close with a different `failure_mode_id` overwrites the ticket's, with an
  *edited* line before *closed*;
- repeat: same machine within 7 days of its back in service accepted; other
  machine, too old, or a not-a-fault ticket 400; repeats listed on the old
  ticket;
- edit: component outside the machine 400; mode of another class 400;
  clearing the mode with an empty description 400; the timeline line;
- event time: a move without `occurred_at` gets the server's time; a typed
  time before the last event 400 naming it;
- times in the detail match the core;
- access: all routes 404 outside the user's units, keys checked at the
  ticket's site (the unit at raise).

### Migration (`test_migration_v13.py`)
- v13 columns, tables and the named constraints (`fk_tickets_cause`,
  `fk_tickets_action`, `fk_tickets_repeat_of`, `fk_ticket_labour_*`,
  `fk_ticket_assignees_*`, `chk_ticket_labour_minutes`); re-run harmless.

### RBAC (`test_rbac.py`)
- `TestComputePermissions.test_role_matrix` asserts exact sets: the rows of
  operator and supervisor gain `ticket:restore`; technician gains
  `ticket:work`, `ticket:restore`; engineer, manager and it_admin gain all
  four (on top of S017's `ticket:read` / `ticket:raise`, BR1-04); the
  storekeeper none;
- `ticket:restore` joins S017's parametrized `test_ticket_keys` (every role
  but the storekeeper, `in SITE_SCOPED`); `ticket:work`, `ticket:assign` and
  `ticket:close` get their own holders test, each `in SITE_SCOPED` (BS1-06);
- `test_supervisor_is_off_the_maintenance_ladder` still passes unchanged (the
  supervisor's set equals the operator's).

### Masters (`test_failure_codes_api.py`)
- cause / action used by a ticket: code change 409; label and group change
  accepted; a re-save with the code unchanged accepted (compared with the
  locked row, BS1-03).

### Manual checks
Important:
- [ ] On a phone as a technician: acknowledge → start → back in service on a
  breakdown; the page shows response, repair and downtime.
- [ ] On a phone as a supervisor: record back in service on an acknowledged
  ticket, finding the technician in the picker by typing, and entering the
  start time; the timeline shows both events with the entered times.
- [ ] On a phone as an engineer: *Close* is disabled with the visible text
  "Add the labour first"; *Add labour* beside it opens the labour dialog
  (own name and today pre-filled); close with cause and action; the Save reads
  *Close ticket*; the ticket is read-only.
- [ ] "Not fixed — raise again" on a ticket back in service: the new ticket
  links to the old one and the old one lists it.
- [ ] On an **Android phone and an iPhone**: the close dialog with the
  keyboard up keeps *Close ticket* and *Cancel* on screen (iOS Safari lays the
  keyboard over the page, so the footer may sit under it there); the ticket
  page shows the action buttons first, in the stated order.

Plain:
- Send back with the machine down: downtime grows again.
- *Machine stopped* on a defect as an operator: downtime starts at that time.
- Acknowledge shows "Recording as <name>" ("Nobody will be assigned" for a
  user with no Team record); remove a labour row asks first.
- Send back and not a fault show the remark open; Save without it is refused
  on the field.

### Acceptance
`tooling/run-tests.bat` green; `npx vite build` with no new errors.

## 9. Open questions and assumptions

1. ~~May an engineer close a ticket he worked himself?~~ **Decided (user,
   gate A, 20-10-2026): yes** — engineer, manager and IT admin; a recorded
   departure from segregation of duties (ISO 27001 A.5.3): the plant has few
   engineers, and a second sign-off would leave tickets open for days.
2. ~~Vendor reports and quotes (PDF) on a ticket?~~ **Decided: yes** — the
   ticket owner's `kinds` gains `document`, write key `ticket:raise`, *Add
   document* for `ticket:work` holders (§ 3, BR2-04).
3. ~~The repeat window~~ **Decided: 7 days** (`REPEAT_WINDOW_DAYS = 7`).
4. ~~Who may be named as the person who fixed it, and booked as labour?~~
   **Decided: (a)** — anyone with a membership at the ticket's site, operators
   included; assignees technician, engineer or manager (§ 5.8).
5. ~~How does the operator link a repeat after the old ticket is closed?~~
   **Decided (user, 20-10-2026): left out of S018** — not a priority. The link
   stays the *Not fixed — raise again* button on the old ticket's page; no
   raise-screen list, no *Raised by me* view (Out of scope, BR3-01).
6. ~~An optional *Time spent* on the back-in-service dialog?~~ **Decided:
   no** — labour is added on its own; the labour defaults of § 1 are enough
   (BR3-06 (b) dropped).
7. **Assumption:** response time is measured from the event time of the
   *raised* event (when it happened), not from when it was typed: for a
   breakdown, the clock starts when the machine stopped.
8. **Assumption:** labour rows are kept when a ticket is sent back; time spent
   before the send-back still counts.

## 10. Amendments

### A1 — Already fixed: raise and mark back in service in one go

```
Requested by: KLA, 20-10-2026 ("in raise ticket screen, can we have a fast track check box, that just skips acknowledge, start? just enter the details, mark back in service")
Status: Approved 20-10-2026 by KLA ("execute A1 after the S018 is done"; open points 1 and 2 as proposed: the checkbox for every `ticket:restore` holder, no labour on the raise screen; coded after S018's code-review loop, before gate B)
Baseline: 6c58b7a + uncommitted S018 (code-review r2) (s2)
```

HEAD is 6c58b7a, the committed S017 raise-screen watcher fix; S018's code is
uncommitted on top of it (BS2-06).

**Why.** Work that walks into the workshop (a portable vibrator needing carbon
brushes), or a defect the operator cleared himself, is finished before anyone
records it. With S018 alone that takes a raise and then a back-in-service
dialog on the ticket page: two screens for a job that is already over, which
is where after-the-fact records get skipped. ISO 14224 wants every
maintenance event recorded, whoever asked for it (Plan.MD § 4.2, "the record
matters more than the workflow"). A1 lets the raise screen record it in one
save. It replaces the raise-and-close half of queued S020; S020 keeps *Parts
used* only.

**What changes.**

1. **The raise screen gains a checkbox, "Already fixed — back in service"**,
   below the description and time, for a user who holds `ticket:restore` at
   the node's site (the back-in-service move's own key, § 5.7: operator and
   up, IT admin; the node detail's `permissions` already carries the keys at
   its site). Today `ticket:raise` and `ticket:restore` have the same
   holders, so everyone who sees the form sees the checkbox; the condition
   stays in case the keys diverge (BS2-05). Ticked, it shows the fields of
   S018's **back in service after the fact** (§ 1, § 5.2), and nothing else:
   - **Back in service at** (on a defect: **Fixed at**, the dialog's label by
     intensity): "Now · Change", as every move dialog;
   - **Who did the work**: `PersonPicker`, required. **Pre-filled** with the
     user's own person (`userPersonId`, `stores/auth.js`) only when **both**
     hold: `node.permissions` includes `ticket:work`, **and** that id is in
     the `people` list the screen already loads
     (`/api/tickets/people?equipment_id=`, the same `_people_at_site` rows
     `PersonPicker` takes) — the page-side form of § 5.2's one rule that the
     ticket page gets from `moves[restore].default_person`. Else empty. An
     operator who fixed his own defect is not pre-filled but is first in the
     picker (`ownPersonId`), one tap (BS2-04);
   - **When work started** (optional): a date pre-filled with the
     back-in-service date and an empty time, sent only when the time is
     filled (§ 1).

   Save reads **"Raise and mark back in service"** (on a defect: **"Raise and
   mark fixed"**), built on `ticketLabels.moveSaveLabel("restore",
   intensity)` or one new entry in `ticketLabels.js` with a line in
   `ticketLabels.test.js` (BS2-07). Unticking hides the fields and keeps what
   was typed until the screen is left. The checkbox and the three fields
   belong in `blankForm()`, so a node change (`watch(nodeId)` →
   `resetForm()`) unticks and clears them with the rest (BS2-08).

   Accepted: the screen then has two styles of the same control — a
   pre-filled `datetime-local` for *When did it happen?* beside "Now ·
   Change", and a `<select>` for *Found by* beside `PersonPicker` — because
   A1 reuses the move dialog's controls; putting the raise screen's own two
   fields on the same controls is a later tidy-up, not A1 (BS2-10).
2. **The server does it in one transaction.** `POST /api/tickets` gains an
   optional `restore: {occurred_at?, person_id, started_at?}`. The route
   raises the ticket as S017 does, then applies the **same back-in-service
   code** the `restore` move uses on the new ticket — no copy (BS2-01):
   - the body of `make_move` after the lock is extracted into
     `_apply_move(cur, ticket, move, clean, now)` (from-state check →
     `_last_ordered_event` → `_event_time` → the move's step, here
     `_restore` → `_add_event` of the move's own event → `update_row` of the
     state → auto-assign for acknowledge / start). `make_move` calls it after
     `_lock_open_ticket`; `raise_ticket` calls it after its insert and
     `raised` event, with `ticket = read_ticket(cur, ticket_id)` (the row
     carries the `id`, `state` and `site_id` `_restore` reads);
   - `raise_ticket` does the key check itself, `require_perm_at(RESTORE_KEY,
     node["site_id"])`, **before** the insert, only when `restore` is given;
     the fresh row is in its own transaction and needs no `_lock_ticket`;
   - so the person rule of § 5.8, § 5.1's time rules (back in service at or
     after the raise time; `started_at` between the raise time and the
     back-in-service time), the `back_in_service` event and, with
     `started_at`, the `started` event, both naming the person, are the
     move's own code.

   Any refusal rolls the whole raise back (row, events and serial counter,
   all inside the one `transaction(conn)`), so there is never a raised ticket
   left half-done. No `acknowledged` event is written: S018 already allows
   back in service straight from raised.

   **Refusals land beside the right field** (BS2-02): the block's own
   `occurred_at` shares its name with the raise's, so every refusal on the
   block is named with a `restore.` prefix — `restore.occurred_at`,
   `restore.person_id`, `restore.started_at` — in the core (below) and in the
   `ApiError`s the shared code raises (`_event_time(…, field)` already takes
   the field name; `_restore`'s two `ApiError`s take it too). The raise
   screen shows `restore.*` refusals beside the three new fields.
3. **The ticket then stands at back in service**, like any other: the
   engineer closes it with cause, action and labour (§ 5.2), or sends it
   back. A1 never closes a ticket — the ISO 14224 coding stays with the
   engineer.
4. **The times come out honest without a mark on the ticket** (§ 5.4):
   - no *started* time → no `started` event → response time and repair time
     are null ("—"); downtime (a breakdown) runs from the failure time to back
     in service, which is real;
   - with a *started* time → response = started − failure time, repair =
     back in service − started: real waits and real work, as typed.

   So no fast-track flag and no migration: the after-the-fact path S018 already
   has gives the right figures, and A1 only shortens how it is entered.
5. **After Save** the screen goes on to the photo step as today (S017), then
   *Done* opens the ticket page.
6. Works with `repeat_of` (§ 5.5): the repeat rule is checked at the raise, as
   without A1.

**Where.**
- `backend/tickets.py`: `raise_ticket` takes `restore`, checks
  `ticket:restore` at the node's site before the insert, and calls
  `_apply_move`, extracted from `make_move`'s post-lock body (BS2-01);
  `_restore`'s `ApiError`s take the field-name prefix (BS2-02).
- `backend/tickets_core.py`: `validate_raise` calls the existing
  `validate_move("restore", body["restore"])` when `restore` is given (a
  non-object → 400 on `restore`) — no second parser — and prefixes its
  errors `restore.` (BS2-02); the ordering checks reuse
  `validate_event_time`.
- `frontend/src/views/tickets/EventFields.vue`: a prop that hides the remark
  (e.g. `withRemark: false`; default shows it as today), so the raise screen
  gets "Now · Change" alone (BS2-03).
- `frontend/src/views/tickets/StartedAtFields.vue` (new): the *When work
  started* pair extracted from `MoveDialog.vue` — props: the back-in-service
  time; v-model date and time; the follow-the-date watcher inside — used by
  `MoveDialog` and the raise screen, two real uses (BS2-03).
- `frontend/src/views/tickets/MoveDialog.vue`: uses `StartedAtFields`
  instead of its inline pair; no change in behaviour.
- `frontend/src/views/RaiseTicketView.vue`: the checkbox and its three fields,
  using `EventFields` (remark hidden), `StartedAtFields` and
  `PersonPicker.vue` (no copies); `restore.*` refusals beside them.
- `frontend/src/utils/ticketLabels.js` (+ test): the Save label, if not
  built from `moveSaveLabel` (BS2-07).
- Docs: **done at approval** — Plan.MD § 4.2 (*Work done without a ticket*)
  and Q23, README Queued S020 retitled *Parts used* (BS2-09).

**Tests** (in `test_ticket_work_api.py`, `test_tickets_core.py`):
- raise with `restore` → 201, state back in service, events `raised`,
  `back_in_service` (person named); with `started_at` also `started`;
  `ticket_times` gives response and repair from the typed times, and null
  without `started_at`;
- refusals roll back (no ticket row, no event, no counter use beyond what
  S017's serial already accepts): `person_id` missing (400), a person who may
  not be named (400), back in service before the raise time (400),
  `started_at` outside raise … back in service (400), each named
  `restore.<field>`. No 403 test for a user without `ticket:restore`: today
  it has the same holders as `ticket:raise`, so no such user can reach the
  raise; the server check stays (BS2-05);
- an operator (holds `ticket:restore`) can do it; the storekeeper cannot raise
  at all (S017);
- a ticket raised this way closes through the ordinary close (labour still
  required).

**Manual checks.**
- **Important:** on a phone, raise a walk-in job with *Already fixed* ticked:
  the extra fields fit, Save stays visible, and the ticket page shows it at
  back in service with the right technician.
- With and without a *started* time: the ticket page shows response and repair
  as typed, or "—".

**Open points.**
1. **Who sees the checkbox** — proposed: every `ticket:restore` holder
   (operator and up), so an operator who cleared his own defect records it
   in one go (TPM autonomous maintenance). Alternative: `ticket:work` holders
   only (technician and up).
2. **Labour** — proposed: not asked here; the engineer adds it before
   closing, as for any ticket (Close shows "Add the labour first").
   Alternative: an optional *Time spent* field that writes one labour row.
3. **Coding order** — A1 is coded after S018's code-review loop, before gate
   B, so S018 and A1 come to the user together.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 send back: intensity rule incomplete; event only in the "down" case | major | **Accepted** (option a): yes → critical; no → degraded only when it was critical, else unchanged; every intensity change on its own move's event `intensity` column, on `sent_back` itself, `ticket_times` reads nothing else; `send_back_intensity` in the core with tests (§ 1, § 3, § 4.3, § 5.4, § 7 decision 4, § 8) |
| BR1-02 re-grade direction, actor, no-change | minor | **Accepted** (option a): raising by `ticket:raise`; lowering by `ticket:work` with a required remark; same intensity 400; `validate_regrade` (§ 1, § 5.2, § 6, § 7 decision 7, § 8) |
| BR1-03 back-in-service key as `MOVES` holds it; no Team record | minor | **Accepted**: one key `ticket:restore`; `needs_person` in `moves`; a `ticket:work` holder with no Team record must name someone; the `started` event carries the same person (§ 1 table, § 4.3, § 5.2, § 8) |
| BR1-04 `test_role_matrix` breaks | minor | **Accepted**: the five rows named, stacking on S017; holders test per key; supervisor-off-ladder test still passes (§ 8 RBAC) |
| BR1-05 phone clock skew vs event order | minor | **Accepted** (option a): dialogs send no time unless changed (S017's raise too); the refusal names the last event; the re-grade consequence stated (§ 1, § 5.1, § 7 decision 9, § 8) |
| BR1-06 no way to correct an event time | minor | **Accepted** (option a): immutable in S018, stated in Out of scope and § 5.1; correction route queued in the README at approval (§ 3 Docs) |
| BR1-07 MTTR naming; Philosophy § 10 vs Plan Q4 | minor | **Accepted**: repair time = EN 13306 active corrective maintenance time, downtime = down time / time to restoration (its mean is MTTR), response time = the plant's own measure; Philosophy § 10 and Plan.MD § 4.2 fixed at approval (§ 1, § 2, § 3 Docs) |
| BR1-08 trade on a labour row | minor | **Accepted** (option a): required when the person has trades (pre-filled when one), optional otherwise; any active trade (§ 1, § 3, § 7 decision 10, § 8) |
| BR1-09 repeat window undefined; pre-fill intensity | minor | **Accepted** (option a): the old ticket's back-in-service time within 7 days before the new event time; not-a-fault tickets cannot be repeated; pre-fill the old ticket's current intensity; the 7-vs-30 choice is open question 3 (§ 1, § 5.5, § 8, § 9) |
| BR1-10 duplicate endpoints | minor | **Accepted** (option a): `/causes`, `/actions`, `/people` dropped; the close dialog uses the masters store; people from S017's `GET /api/tickets/people`, which gains each person's role at the site (§ 3, § 6) |
| BR1-11 no public own-person helper | minor | **Accepted**: `auth_utils.current_person_id(cur)`, owned by S018; *assigned to me* empty without a person (§ 3, § 5.8) |
| BR1-12 `regraded` remark collides with the user's | minor | **Accepted**: S017's detail exposes the events' `intensity`; the page renders the change, the remark stays the user's; `edited` keeps generated lines (§ 3, § 4.3) |
| BR1-13 concurrency test mechanism | minor | **Accepted** (option a, b as fallback): raw connection holding the row, a thread through the test client, 409 asserted; plain stale-state test kept (§ 8) |
| BR1-14 signatures and header | nit | **Accepted**: header updated; `ticket_times(events, now)`; intervals clamped at zero; the window rule lives once in S017's `event_time_error(…, not_before)`, which `validate_event_time` calls (§ 3, § 5.4) |
| BR1-15 migration and test housekeeping | nit | **Accepted**: statements safe twice; constraint names; `conftest._TABLES`; lock-order note; "the ticket's site" = site of `tickets.unit_id` (§ 3, § 4, § 5.3, § 8) |
| BR1-16 S017 rules at edit and close | nit | **Accepted**: description rule at edit and close; component under the machine; assign after back in service allowed; labour kept on not-a-fault; labour removal a hard delete without a timeline line, accepted (§ 1, § 4.2, § 5.2, § 8) |
| BR1-17 standards wording | nit | **Accepted**: EN 13306 restoration vs CMMS sign-off; ISO 55001 § 7.5 / § 9.1 line; open question 1 named as a segregation-of-duties departure; "technician arrived" settled; the cause on a not-a-fault ticket explained (§ 1, § 2, § 3 Docs, § 9) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 § 5.8 leaves no honest record for an operator-fixed defect | minor | **Deferred to the user at gate A**: the proposed default is now option (a) — back-in-service person and labour from anyone at the ticket's site, operators included; assignees stay technician or above; open question 4 rewritten as the choice (a) / (b) (§ 5.8, § 7 decision 8, § 8, § 9) |
| BR2-02 picker anchored on the node's current site | minor | **Accepted** (option a): S018 adds `GET /api/tickets/people?ticket_id=<id>` — S017's access predicate, `ticket:read` at the ticket's site (site of `tickets.unit_id`), people and roles there; `equipment_id` stays for the raise screen; one `_people_at_site` helper (§ 3, § 5.8, § 6, § 8) |
| BR2-03 back-in-service dialog contract | minor | **Accepted** (option a): the person field always shown and required; `moves`' `restore` entry carries `default_person`, computed in the route; `needs_person` dropped from the core (§ 1, § 3, § 5.2, § 6, § 8) |
| BR2-04 per-kind write key for documents | minor | **Accepted** (option a), tied to open question 2: if yes, only `kinds` gains `document`, write key stays `ticket:raise`, *Add document* shown to `ticket:work` holders; S017's `Owner` needs only the kinds change (§ 3, § 9) |
| BR2-05 repeat rule details | nit | **Accepted**: the latest `back_in_service`; 0 ≤ new − restoration ≤ 7 days; the server rule governs over the button (§ 1, § 3, § 5.5, § 8) |
| BR2-06 assignment details | nit | **Accepted**: auto-assign for every `ticket:work` holder with a Team record, with an *assigned* event; assigning twice 200 idempotent; removing a non-assignee 404 (§ 1, § 5.8, § 8) |
| BR2-07 small gaps in § 3, § 5.2, § 6 | nit | **Accepted**: close overwrites the mode with an *edited* line; modes from S017's endpoint; `/regrade` route key `ticket:raise`, lowering checked inside; `_update_plain_master` `used_by` parameter; `validate_event_time` a thin wrapper adding the last event to the message; the raiser cannot edit his ticket (accepted) (§ 1, § 3, § 5.2, § 5.6, § 6) |
| BR2-08 Baseline; S017's occurred_at claim | nit | **Accepted**: Baseline names uncommitted S015; § 5.1's claim kept — S017 is revised in the same round to say its raise screen sends `occurred_at` only when changed (header, § 5.1) |
| BR2-09 ISO 9001 § 10.2, ISO 27001 A.5.15 / A.8.15 | nit | **Accepted**: one line each in § 2 |

### Round 3 — `2-brief-review-r3.md` (Fable, UX checklist), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 repeat link only on the old ticket's page | major | **Rejected by the user** (20-10-2026): operator re-raising of a closed ticket is not a priority; left out. The repeat button stays on the old ticket's page; the gap (unlinked repeats understate the count) stated in Out of scope; open question 5 marked decided (§ 9) |
| BR3-02 significant actions single-tap among everyday buttons | minor | **Accepted** (option a): Close / Not a fault / Send back set apart (left, outline), Save labelled per move with a consequence line; remove labour and unassign confirmed inline (§ 1, § 3, § 7 decision 11, § 8) |
| BR3-03 dialogs that may not fit a phone; page shows everything | minor | **Accepted** (option a): `FormModal` gains `modal-dialog-scrollable` (every dialog inherits it, wanted); ticket page with the action bar first, panels only for `ticket:work` or when not empty, Edit / Assign with the panels (§ 1, § 3, § 7 decision 12, § 8) |
| BR3-04 how the page knows which controls to show | minor | **Accepted** (option a): detail carries `permissions` (keys at the ticket's site) and `regrade_to`; `regrade_options` in the core; `/api/auth/me` gains `person_id` (§ 1, § 3 incl. `app.py`, § 6, § 7 decision 13, § 8) |
| BR3-05 "add the labour first" learnt only after the close dialog | minor | **Accepted** (option a): *Close* disabled with "Add the labour first" while no labour; the 409 stays (§ 1, § 8) |
| BR3-06 labour row fields that can be defaulted | minor | **Accepted** (option a): own person, today, only trade; hours and minutes inputs; zero refused in the dialog (§ 1, § 3). Option (b), *Time spent* on the restore dialog: **Deferred to the user at gate A**, open question 6 (§ 9) |
| BR3-07 whole-site person picker | minor | **Accepted** (option a): `PersonPicker.vue` grouped (assignees, ladder, others) with a filter, works under either answer to open question 4; said in OQ4 (§ 3, § 5.8, § 9) |
| BR3-08 the operator's re-grade as one button | minor | **Accepted** (option a): *Machine stopped* on a defect for `ticket:raise` holders; *Change severity* with the three large buttons for `ticket:work` holders, remark only when lowering (§ 1, § 3, § 8) |
| BR3-09 Acknowledge / Start dialogs with nothing required; silent auto-assign | minor | **Accepted** (option a): time as "Now · Change", remark behind *Add remark*; "Recording as <name>" from `recording_as` in `moves` (§ 1, § 3, § 6, § 8) |
| BR3-10 send-back wording and consequences; send back vs repeat | nit | **Accepted**: question per intensity, two large buttons with their consequences, one line on send back vs raise again, in the remark help text (§ 1, § 3) |
| BR3-11 small floor-use items | nit | **Accepted**: started-at only from raised / acknowledged, dates default to today; supervisor check "on a phone"; empty states and times row hidden on not a fault; component list from the machine's detail `children`; messages quoted ("Who did the work? Pick a name", "Say why the machine runs", "Already a breakdown / defect"); assignees' first names on list rows. The S017 reported-by picker note is S017's, not changed here (§ 1, § 3, § 5.2, § 6, § 8) |
| BR3-12 IT admin with a Team record; OQ1 wording | nit | **Accepted**: auto-assign applies the manual assignment's role check, so IT admin is never auto-assigned; OQ1 names IT admin; the r2 statement on `test_role_matrix` noted as superseded (§ 5.7, § 5.8, § 8, § 9) |

### Round 4 — `2-brief-review-r4.md` (Fable, UX), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR4-01 remark behind *Add remark* though three moves require it | minor | **Accepted** (option a): open and required on send back, not a fault and a lowering *Change severity*; behind *Add remark* only where optional (§ 1, § 3 `MoveDialog`, `RegradeDialog`, § 8) |
| BR4-02 "Add the labour first" invisible as a tooltip on a phone | minor | **Accepted** (option a): visible text under the disabled *Close* plus an *Add labour* button that opens the labour dialog; no tooltip reliance (§ 1, § 3 `TicketDetailView`, § 8 manual check) |
| BR4-03 a default person the server would refuse | minor | **Accepted** (option a): one rule — the user's own person is a default only when he qualifies for that field at the ticket's site, the § 5.8 check as auto-assign; IT admin never pre-filled; `PersonPicker` shows the user's own person first (§ 1, § 3, § 5.2, § 5.7, § 5.8, § 8) |
| BR4-04 `recording_as` defined two ways; wrong null text | minor | **Accepted** (option a): one definition — the person this move will auto-assign, else null; the null line "Nobody will be assigned" (§ 1, § 3, § 5.8, § 6, § 8) |
| BR4-05 controls without a place; "left" once stacked; technician gets both re-grade controls | minor | **Accepted** (option a): the stacked phone order stated (chain move; *Machine stopped* or *Change severity*; *Not fixed — raise again*; after a gap the significant moves, outline); one row on a wider screen; `ticket:work` holders see *Change severity* only (§ 1, § 3) |
| BR4-06 "date pre-filled, time empty" impossible in one `datetime-local` | minor | **Accepted** (option a): a date input pre-filled with the back-in-service date and an empty time input, sent as `started_at` only when the time is filled; night shift by changing the date; API test across midnight (§ 1, § 3, § 8) |
| BR4-07 send back's Yes / No; *Machine stopped* dialog | nit | **Accepted**: Yes / No a choice with a selected state, *Send back* the one submit; *Machine stopped* hides the grade buttons ("Breakdown from: Now · Change", Save *Machine stopped*); `regrade_options` allowing degraded for an operator on initial while the page offers critical only — accepted (§ 1, § 3) |
| BR4-08 small gaps in files and checks | nit | **Accepted**: `stores/auth.js` `userPersonId` in § 3; `/auth/me` `person_id` null when the DB is down (§ 3, § 8); *Assigned to me* empty for an IT admin with a Team record, accepted (§ 1); Assign dialog leaves out the assigned, ladder first (§ 3, § 5.8); the scrollable-dialog check on an Android phone and an iPhone (§ 8); *Change* fills the phone's now (§ 1, § 3) |

### Gate A (20-10-2026) — approved by KLA

Answers: open question 1 self-close **yes**; 2 vendor documents on tickets
**yes**; 3 repeat window **7 days**; 4 **(a)** anyone at the site for the
back-in-service person and labour; 5 left out (decided earlier); 6 *Time spent*
on back in service **no**; the `FormModal` scroll fix **stays in S018**
(decision 12). Recorded as user decisions 4–9 in the header and in § 9.

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 20-10-2026

Against S017's code as committed (cfedc46). No `blocker` or `major`, so the
approval stands; `Baseline:` set to cfedc46.

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 an S017 test breaks when tickets take documents | minor | **Accepted**: `test_documents_api.py` in § 3 Tests (a document on a ticket → 201, under `tickets/<id>/`, listed); `Owner.kinds` and the photos-only refusal removed, since no owner restricts kinds; the three photos-only comments updated (§ 3) |
| BS1-02 one `canEdit` cannot split photos and documents | minor | **Accepted** (option a): `DocumentsCards` `canEditDocuments` prop; the detail sends `can_add_documents` (`ticket:work` at the ticket's site, not closed); the ticket page drops `photos-only`; the modal's visibility line keyed on a ticket owner (§ 3, § 6, § 8) |
| BS1-03 the code-freeze pattern is the code's, not S017's brief | minor | **Accepted**: compare with the locked row, count `LOCK IN SHARE MODE`, same 409 message, citing `update_failure_mode` (§ 3, § 5.6, § 8) |
| BS1-04 people picker already returns role; route key | nit | **Accepted**: route stays `ticket:raise`; `ticket_id` → 404, then `ticket:read` at the ticket's site; one anchor required, 400 otherwise (§ 3, § 8) |
| BS1-05 reuse `_lock_ticket` | nit | **Accepted**: the writes extend its locked SELECT; `TICKET_CLOSED` for a closed ticket, "changed — reload" for a stale state (§ 3) |
| BS1-06 test helpers that now exist | nit | **Accepted**: imported or moved to `conftest.py`, named; `set_ticket_state` docstring; `ticket:restore` in `test_ticket_keys`, own holders tests for the other three (§ 3, § 8) |
| BS1-07 raise screen query and repeat pre-fill | nit | **Accepted**: `?equipment=…&repeat_of=…`; pre-fill from the old ticket's detail after the node loads and `resetForm()`; `repeat_of_id` via `_optional_id` (§ 3) |
| BS1-08 symptom list anchored on the node's current site | nit | **Accepted** (add the anchor): `GET /api/tickets/modes?ticket_id=`, class via the ticket's machine, `ticket:read` at the ticket's site (§ 3, § 6, § 8) |

### Staleness s2 (A1) — `2-brief-review-s2.md` (Fable), answered 20-10-2026

A1 only, against S018's code as built (uncommitted on 6c58b7a). No `blocker`
or `major`, so A1's approval stands; A1's `Baseline:` set to 6c58b7a +
uncommitted S018 (code-review r2).

| Finding | Severity | Answer |
|---|---|---|
| BS2-01 no single back-in-service function to call | minor | **Accepted** (option a): `make_move`'s post-lock body extracted into `_apply_move`, called by `make_move` and `raise_ticket`; `raise_ticket` checks `ticket:restore` at the node's site before the insert (A1 *What changes* 2, *Where*) |
| BS2-02 `validate_move` exists; `occurred_at` collides with the raise's | minor | **Accepted** (option a): `validate_raise` reuses `validate_move("restore", …)`; the block's refusals prefixed `restore.` in core and in the shared code's `ApiError`s, shown beside the new fields (A1 *What changes* 2, *Where*, *Tests*) |
| BS2-03 the time control is `EventFields` (time and remark); the started pair is inline | minor | **Accepted** (option a): `EventFields` gains a hide-remark prop; the started pair extracted into `StartedAtFields.vue`, used by `MoveDialog` and the raise screen (A1 *Where*) |
| BS2-04 the default person: source and full rule | minor | **Accepted** (option a): page-side — `userPersonId` when `node.permissions` has `ticket:work` and the id is in the loaded `people` list; else empty (A1 *What changes* 1) |
| BS2-05 the 403 test has no subject | minor | **Accepted** (option a): the test line dropped with the reason; the server check kept (A1 *What changes* 1, *Tests*) |
| BS2-06 HEAD is 6c58b7a | nit | **Accepted**: noted under A1's header; `Baseline:` set to 6c58b7a + uncommitted S018 |
| BS2-07 existing labels; "Fixed at" on a defect | nit | **Accepted**: time label by intensity as the dialog's; Save label built on `moveSaveLabel` or one new `ticketLabels.js` entry with a test (A1 *What changes* 1, *Where*) |
| BS2-08 a node change resets the restore fields | nit | **Accepted**: the checkbox and three fields live in `blankForm()`, cleared on a node change (A1 *What changes* 1) |
| BS2-09 A1's Docs already done | nit | **Accepted**: the Docs line marked done at approval (A1 *Where*) |
| BS2-10 two control styles on one screen | nit | **Accepted** as is: stated in A1; aligning the raise screen's own fields is a later tidy-up (A1 *What changes* 1) |
