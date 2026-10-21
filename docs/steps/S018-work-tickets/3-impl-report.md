```
Step: S018 — Work the ticket
Doc: impl-report
Author: Coder (Opus)
Date: 20-10-2026
```

# S018 — Implementation report

Built on cfedc46 (S017) plus the uncommitted S017 post-commit fix in
`RaiseTicketView.vue` (the `watch(nodeId, …, { immediate: true })` below
`resetForm()`), which is kept; the repeat pre-fill builds on it.

## Question for the user — answered 21-10-2026

**Answer (KLA, gate B):** "Keep the typed-times rule" — as built; recorded in the brief § 5.1.


**The event-order rule counts only the events that move the state or the
intensity.** § 5.1 says a typed time may not be "before the ticket's latest
event". Read literally, that includes *assigned*, *unassigned* and *edited*
lines, which are stamped with the server's clock when they are recorded. Then a
supervisor typing "back in service at 10:30" at shift end would be refused with
"Must be at or after *Assigned*, 11:00" because the engineer assigned someone at
11:00. Section 5.1 gives the reason for the rule: the times are computed from the
events. Only the events that move the state or the intensity feed the times, so I
applied the rule to those events only (`tickets_core.ORDERED_EVENTS`: raised,
acknowledged, started, back in service, sent back, closed, closed as not a
fault, regraded). Bookkeeping lines are not limited by it. The test
`test_an_assignment_does_not_hold_back_a_typed_time` covers it. If you want the
literal rule, it is a one-line change: drop the `event IN (…)` filter in
`tickets._last_ordered_event`.

## 1. What was built

- **Moves**: acknowledge, start, back in service (with an optional start time
  after the fact), send back (asks whether the machine is down again), close
  (cause, action, symptom, at least one labour row), and close as not a fault
  (cause and remark). Each move has an event time that defaults to the server's
  clock, an optional or required remark, and an event in the timeline.
- **Re-grade**: the operator can only raise the intensity (*Machine stopped* on
  a defect). `ticket:work` holders can lower it too, with a remark (*Change
  severity*).
- **Edit** of the component, symptom and description while the ticket is open.
  Each save writes one *edited* line with every change as old → new.
- **Assignment** by the engineer: add or remove, and assigning the same person
  twice does nothing. Acknowledge and start auto-assign the user's own person
  when his role at the ticket's site is technician, engineer or manager. The
  list gets *Assigned to me* and shows the assignees' first names on each row.
- **Labour rows**: person, trade worked, date and minutes. You can add, change
  and remove them; removing asks first.
- **Repeat**: *Not fixed — raise again* opens the raise screen pre-filled, with
  `repeat_of_id`. The server checks that the repeat is on the same machine and
  within 0–7 days of the old ticket's latest back in service. The new ticket
  links to the old one, and the old one lists its repeats.
- **Times** on the ticket page, computed from the events: response, repair
  (hands on) and downtime. They are hidden on a ticket closed as not a fault.
- **Cause and action codes are frozen once a ticket uses them**, the same rule
  as failure modes.
- **Documents on tickets**: the server accepts every file kind (the photos-only
  rule and `Owner.kinds` are removed). *Add document* is shown to `ticket:work`
  holders only.
- **Every `FormModal` scrolls inside**, so the footer with Save stays on screen.
- `/api/auth/me` returns `person_id`.

## 2. How it works

**Pure core (`tickets_core.py`)**
- `MOVES` is the move table of § 1 as data: from-states, to-state, key, event
  name and required fields. `allowed_moves(state, keys)` filters that table for
  the user.
- `validate_move(name, body)` parses the body: the common time and remark, the
  move's own fields, and the required ones.
- `validate_event_time` wraps S017's `event_time_error` and names the last event
  in the refusal ("Must be at or after Acknowledged, 20-10-2026 10:04").
- The other rules each have one function: `started_at_error`,
  `send_back_intensity`, `regrade_options`, `validate_regrade`,
  `validate_close`, `validate_labour` with `trade_error`, `validate_edit` with
  `edit_lines`, `validate_assignee` and `is_repeat_candidate`.
- `ticket_times(events, now)` walks the ordered events oldest first. It keeps a
  running state and intensity (read only from each event's `intensity` column)
  and sums three figures:
  - **repair**: the time from each *started* or *sent back* to the next back in
    service. It is null if a back in service had no start before it, or if work
    never started.
  - **downtime**: the time while the intensity is critical and the state is
    raised, acknowledged or in progress. An open ticket counts up to `now`.
  - **response**: raised → the first acknowledged or started.

  Every interval is clamped at zero, and a not-a-fault ticket gets null for all
  three.

**Shell (`tickets.py`)**
- `POST /api/tickets/<id>/moves/<move>` is the single move route. It looks up
  `MOVES[move]`, runs `check_perm(key)`, validates the body, then in one
  transaction:
  - `_lock_open_ticket` locks the ticket row (7) `FOR UPDATE`. A missing ticket
    gives 404, the key missing at the ticket's site gives 403, a closed ticket
    gives 409 "This ticket is closed". Every decision is taken from the locked
    row.
  - A move not allowed from the current state gives 409 "This ticket changed —
    reload".
  - The event time is resolved.
  - A per-move step runs (`_restore`, `_send_back`, `_close`, `_not_a_fault`)
    and returns the event's fields and the ticket's changes.
  - The event is written, the ticket is updated, and acknowledge or start runs
    the auto-assign.
  - The answer is the ticket detail, read inside the transaction.
- `/regrade`, `PUT /<id>`, `/assignees`, `/labour` follow the same pattern:
  lock (7) only, then refusals from the locked row.
- `_lock_ticket` is S017's function, extended. Its locked SELECT now also reads
  intensity, mode, machine, component, description, occurred_at and
  not_a_fault, and it returns the plain row merged with the locked one.
- **The detail adds**:
  - `cause`, `action`, `not_a_fault`, `repeat_of`, `repeats`, `assignees`,
    `labour`, `times`;
  - `moves`, where restore carries `default_person` and acknowledge / start
    carry `recording_as`;
  - `permissions` (from `permissions_at_site` at the ticket's site),
    `regrade_to`, `can_add_documents` and `can_raise_repeat`.
- **The pickers** (`/people`, `/modes`) share `_picker_anchor`: either
  `?ticket_id=` (the access predicate, then `ticket:read` at the ticket's site)
  or `?equipment_id=` as in S017. If neither is given, the answer is 400 on
  `equipment_id`.
- **Who may be named** is read from `memberships` at the ticket's site
  (`_person_at_site`), never from the token:
  - assignees and auto-assign need a role in `config_rbac.ASSIGNABLE_ROLES`;
  - the back-in-service person and the labour person may be anyone with a
    membership there.

**Frontend**
- **`TicketDetailView.vue`** follows the layout of § 1:
  - the action bar comes first, stacked full-width on a phone; on `md` and wider
    it is one row with the significant moves first (`order-md-first`);
  - while there is no labour, a disabled *Close* shows "Add the labour first"
    with *Add labour* beside it;
  - next come the times, assignees (unassign asks inline) and labour, then
    repeats, details (*Edit*), description, photos and documents, and the
    timeline;
  - the timeline shows each intensity change ("Defect → Breakdown"), computed
    from the events' own `intensity` column.
- **The dialogs**:
  - `MoveDialog` handles every move: send back's Yes / No as choice buttons,
    the start date and time for a back in service after the fact, and close or
    not a fault with cause and action from the masters store;
  - `RegradeDialog` has two forms: *Machine stopped* and *Change severity*;
  - `AssignDialog`, `EditTicketDialog` and `LabourPanel`, with its add / change
    dialog;
  - every dialog shares `EventFields` ("Now · Change" and the remark) and
    `PersonPicker` (people grouped with a filter box).
- **The raise screen** reads `?repeat_of=` after the node loads, pre-fills the
  earlier ticket's symptom and intensity, and sends `repeat_of_id`.

## 3. Files touched

Backend:
- `backend/local_db.py`: migration v13 (ticket columns, FKs, `ticket_assignees`, `ticket_labour`, CHECK).
- `backend/config_rbac.py`: the four keys, in `SITE_SCOPED`; `ASSIGNABLE_ROLES`.
- `backend/auth_utils.py`: `_person_id` renamed to the public `current_person_id`.
- `backend/app.py`: `/api/auth/me` returns `person_id` (null when the DB is down).
- `backend/tickets_core.py`: the S018 rules (moves, validation, times, repeat); `validate_raise` gains `repeat_of_id`.
- `backend/tickets.py`: the move, regrade, edit, assignee and labour routes; detail and list extended; picker anchor `ticket_id`; repeat check on raise; docstring and lock-order note.
- `backend/masters.py`: `_check_code_frozen` shared by modes, causes and actions; `_update_plain_master(…, used_by)`.
- `backend/documents.py`: `Owner.kinds` and the photos-only refusal removed; comments updated.
- `backend/file_store.py`: comment (ticket documents).
- `backend/equipment.py`: lock-order note gains S018.

Backend tests:
- `backend/tests/test_tickets_core.py`: S018 core tests; `repeat_of_id` in the S017 raise cases.
- `backend/tests/test_ticket_work_api.py` (new): the API tests of § 8, the threaded concurrency test included.
- `backend/tests/test_migration_v13.py` (new).
- `backend/tests/ticket_helpers.py` (new): `now_ist`, `local`, `api_time`, `refusal`, moved out of `test_tickets_api.py`.
- `backend/tests/conftest.py`:
  - `_TABLES` gains `ticket_labour` and `ticket_assignees`;
  - the `machine`, `operator` and `give_site_role` fixtures moved here;
  - the `set_ticket_state` docstring is updated.
- `backend/tests/test_tickets_api.py`:
  - imports the moved helpers;
  - the detail test compares the per-user fields separately;
  - the picker row expects `assignable`.
- `backend/tests/test_documents_api.py`: a document on a ticket → 201, stored and listed (replaces the S017 400 test).
- `backend/tests/test_failure_codes_api.py`: cause and action code freeze.
- `backend/tests/test_rbac.py`: role matrix; `ticket:restore` in `test_ticket_keys`; holder tests for work, assign and close.
- `backend/tests/test_auth.py`: `person_id` null while the DB is down.

Frontend:
- `frontend/src/components/FormModal.vue`: `modal-dialog-scrollable`.
- `frontend/src/components/documents/DocumentsCards.vue`: `canEditDocuments` prop; the `photosOnly` prop removed (no user left).
- `frontend/src/components/documents/DocumentUploadModal.vue`: the ticket visibility line keyed on a ticket URL; `photosOnly` now means "this user may add photos only".
- `frontend/src/stores/auth.js`: `userPersonId`.
- `frontend/src/utils/ticketLabels.js`:
  - the event labels;
  - move and Save labels, the consequence line, the send-back question and choices;
  - `intensityChanges`, `minutesText`, `firstName`, `groupPeople`, `isLowering`, `toLocalDateValue`.
- `frontend/src/views/TicketDetailView.vue`: the page of § 1.
- `frontend/src/views/TicketsView.vue`: *Assigned to me*, assignees' first names, *Not a fault*.
- `frontend/src/views/RaiseTicketView.vue`: repeat pre-fill and `repeat_of_id`.
- New in `frontend/src/views/tickets/`:
  - `MoveDialog.vue`, `RegradeDialog.vue`, `AssignDialog.vue`, `EditTicketDialog.vue`;
  - `LabourPanel.vue`, `PersonPicker.vue`, `EventFields.vue`.
- `frontend/tests/ticketLabels.test.js`: the new labels and helpers.

Docs:
- `docs/steps/S018-work-tickets/1-brief.md` and `docs/steps/README.md`: status only.
- This report.

## 4. Decisions taken

1. **The event-order rule counts only `ORDERED_EVENTS`.** See the question at
   the top. This is a narrower reading of § 5.1.
2. **The default event time is `max(server now, last ordered event)`.** The last
   event may lie up to `FUTURE_SKEW` ahead of the clock (a typed time). A plain
   "now" would then put the new event before it and break the order the times
   rely on.
3. **`allowed_moves(state, held_keys)` takes no intensity.** The brief lists
   `intensity` in the signature, but nothing in the move table depends on it.
   The only use, "Fixed" on a defect, is a label, so it lives in
   `ticketLabels.moveLabel`.
4. **The rules that need the ticket return a refusal tuple.** `validate_close`
   and `validate_regrade` return `(status, field, message)` or None, because the
   core cannot raise an HTTP error and these rules give 400, 403 or 409.
   - `validate_close(ticket_mode_id, clean, labour_count)` takes the ticket's
     mode, not the whole ticket.
   - The description rule at close stays S017's `description_error`, called in
     the shell, because it needs the mode's code.
   - There is no separate `validate_not_a_fault`: `MOVES["not-a-fault"].requires`
     (`cause_id`, `remark`) covers it through `validate_move`.
5. **Labour validation is split into `validate_labour(body, today, earliest)`
   and `trade_error(trade_id, person_has_trades)`.** The person's trades can
   only be read after `person_id` is parsed.
6. **Small core functions added:** `validate_regrade_body`, `validate_assignee`
   and `started_at_error` keep body parsing and the rules out of the shell.
7. **`started_at` on a back in service from *in progress* is 400** ("Work has
   already started on this ticket"). The dialog only offers the field from
   raised or acknowledged, so the server refuses it too rather than ignoring it.
8. **`_update_plain_master(…, used_by)` takes the ticket column only** (for
   example `"cause_id"`). The brief's example was a tuple
   `("tickets", "cause_id")`, but the table is always `tickets`. The count and
   the 409 moved into one helper, `_check_code_frozen`, which
   `update_failure_mode` uses too, so the S017 check is no longer pasted twice.
9. **`ASSIGNABLE_ROLES` lives in `config_rbac.py`**, as `NO_LOGIN_ROLES` does,
   so role names stay in the RBAC file.
10. **The people picker returns `assignable: bool` per person** (extra field).
    The page then needs no copy of the role rule to tell who may be assigned.
11. **The detail returns `can_raise_repeat`** (extra field): `ticket:raise` at
    the site, back in service or closed, not a fault excluded, latest
    restoration within 7 days of now. The server works it out, like
    `can_add_documents`; the brief left this to the page.
12. **Index `ix_ticket_assignees_person (person_id)` is named in v13.** InnoDB
    would create an unnamed one for the FK anyway; it also serves *Assigned to
    me*.
13. **Labour POST answers 201; every other work route answers 200.** All of
    them return the ticket's detail.
14. **Edit:**
    - a save that changes nothing writes no line (200 with the detail);
    - a body with no field is 400 "Nothing to change";
    - the edited line's time is the server clock.
15. **Removing an assignee who is not assigned is 404 "Not assigned".**
16. **Close checks run in this order:** symptom missing (400) → no labour (409)
    → cause or action inactive (400) → description rule (400). The 400/409 split
    is the brief's; the order is my choice.
17. **New shared frontend pieces (DRY):**
    - `views/tickets/EventFields.vue` holds "Now · Change" and the remark,
      shared by `MoveDialog` and `RegradeDialog`;
    - `groupPeople` (in `ticketLabels.js`) holds the picker's grouping, so it
      can be tested.
18. **Documents frontend:**
    - `DocumentsCards.photosOnly` is removed, since the ticket page was its only
      user (as on the backend with `Owner.kinds`);
    - the upload modal's `photosOnly` is now bound to "this user may not add
      documents", so an operator's *Add photo* shows no Kind choice;
    - the visibility line is keyed on a `/api/tickets/` base path.
19. **Test helpers moved:** the shared ticket helpers live in
    `tests/ticket_helpers.py`, and the fixtures in `conftest.py`, so the S017
    and S018 test files import rather than copy them (BS1-06).
20. **Edit dialog:** the ticket's current part is always listed in the Part
    select, even if it is now scrapped or the machine's detail cannot be read.
    An untouched field therefore never clears it.
21. **Not a fault:** the cause defaults to *5.1 No cause found* when the cause
    list has it.

## 5. Not done / deferred / assumed

- **Not done (planner's job):** the docs updates of § 3 "Docs" (Plan.MD,
  Maintenance-Philosophy, README Queued).
- **Concurrency test:** the threaded test (BR1-13) was kept. It ran green three
  times in this session, and it asserts that the move really waited on the lock.
- **Defect downtime:** shown as "0 min" on a defect that never stopped, not "—".
  The machine did not stop, so 0 is the measured figure.
- **Repair time on an open ticket in progress** counts up to now, like downtime.
- **Cross-site machines:** on a ticket whose machine moved to a unit the user
  cannot see, the Edit dialog cannot list the machine's parts. It shows a
  message and keeps the current part.
- **Bundle size:** `npx vite build` passes. The chunk-size warning (main chunk
  530 kB) is the existing one.

## Manual checks

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

## Tests run

- `tooling/run-tests.bat`, all green:
  - backend: **1801 passed** (165 s);
  - frontend (vitest): **92 passed** in 12 files;
  - dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built, with only the existing chunk-size
  warning.

## Fix rounds

### Round 1

Answers to `4-code-review-r1.md`.

- **CR1-01 (blocker): Fixed.** `useFormModal` builds the form at setup with
  `ref(blank())`, so `blank: (seed) => seed` left `form.value` undefined until
  the first `open()`. The other dialogs in the repo (equipment status / move,
  `AssignDialog`, `DocumentUploadModal`) all make `blank` return the full
  default shape, so I did the same and left the composable unchanged. Each of
  the four now has `blank: (seed) => ({ <defaults>, ...seed })`: the defaults
  make the first render safe, and the seed each `open()` passes still decides
  the real values.
  - `MoveDialog.vue`: `occurred_at: null, remark: ""`.
  - `RegradeDialog.vue`: `intensity: "", occurred_at: null, remark: ""`.
  - `EditTicketDialog.vue`: `component_id: "", failure_mode_id: "", description: ""`.
  - `LabourPanel.vue`: `person_id: null, trade_id: "", work_date: "", hours: "", minutes: ""`.

  No other `useFormModal` caller in the S018 files has the pattern
  (`AssignDialog` already returned an object; `DocumentUploadModal`'s
  `blank` was written in S017/S006 style and is fine).
  - Verification (scratch only, nothing added to the repo): a vitest file and
    config in the session scratchpad mount each component in jsdom with Vue's
    `createApp` (api and masters store mocked), then call `open()` (MoveDialog
    with *acknowledge* and *close*, RegradeDialog *stopped*, EditTicketDialog,
    LabourPanel `openAdd`). All 5 cases pass: no mount error, no throw from
    `open()`. With the old `blank` put back in RegradeDialog the same check
    failed, so the check does catch the fault (file restored afterwards).
    This was jsdom only; the browser check is still the user's.
- **CR1-02 (minor): Deferred** to gate B, the user's call.
- **CR1-03 (minor): Deferred** to gate B, the user's call.
- **CR1-04 (minor): Deferred** to gate B, the user's call.
- **CR1-05 (nit): Deferred** to gate B, the user's call.
- **CR1-06 (nit): Deferred** to gate B, the user's call.
- **CR1-07 (nit): Deferred** to gate B, the user's call.
- **CR1-08 (nit): Deferred** to gate B, the user's call.

Tests after the round: `tooling/run-tests.bat` green (backend 1801 passed,
frontend 92 passed in 12 files, dependency-audit 42 passed); `npx vite build`
built with only the existing chunk-size warning. A1 is not part of this round.

### Round 2 (CR1-02…08, CR3-01…04)

The user said "fix CR1, CR3". CR1-01 was fixed in round 1. The § 5.1 `ORDERED_EVENTS`
question is still with the user; that code is untouched.

- **CR1-02 — Fixed.** One core function, `tickets_core.latest_restoration(state, not_a_fault,
  events)`: the latest back in service, but only while the ticket is back in service or closed
  and not a not-a-fault (else None). The detail's `can_raise_repeat` and `_check_repeat` both
  use it, then `is_repeat_candidate`. A ticket sent back is refused with 400 on `repeat_of_id`.
  New messages: a ticket that is not back in service or was a not-a-fault now reads "That
  ticket can't be repeated: it is not back in service" (`REPEAT_NOT_RESTORED`); the 7-day
  message stays for a too-old restoration only. Tests: core `test_latest_restoration_needs_a_restored_state`;
  API `test_a_ticket_sent_back_cannot_be_repeated` (send back, detail says no, raise 400).
- **CR1-03 — Fixed**, on the move and re-grade dialogs and the raise screen's block. `EventFields`
  is keyed on a counter that each `open()` (MoveDialog, RegradeDialog) and each `resetForm()`
  (RaiseTicketView) increments, so it remounts at "Now" with the remark folded. Untick/re-tick
  on the raise screen does not touch the counter, so a typed time still survives there.
- **CR1-04 — Fixed.** No `btn-sm` left on `TicketDetailView.vue` or `LabourPanel.vue` (Assign,
  Unassign, Yes/No confirms, Edit, Add labour, row Change/Remove). The inline confirm rows use
  `gap-3`.
- **CR1-05 — Fixed**, by the same change as CR1-02: `_latest_back_in_service` and the SQL
  `_latest_restoration` are gone; both paths read the events through `latest_restoration`.
- **CR1-06 — Fixed.** `edit_ticket` writes the row when any submitted id/text differs from the
  locked row, and only the timeline line depends on the labels. If the ids change but the
  labels read the same, the row is saved and no *edited* line is written (nothing readable to
  say). Test `test_a_symptom_with_the_same_label_is_still_saved` (ticket holding a mode of
  another class, re-picked to the same-label mode of the machine's class).
- **CR1-07 — Fixed.** The Times card is hidden for a viewer without `ticket:work` when response
  and repair are null and downtime is 0.
- **CR1-08 — Fixed.** `useFormModal` now keeps `status` in its `error`; MoveDialog and
  RegradeDialog emit `reload` on a 409 with no field, and `TicketDetailView` calls `load()`
  (`loading && !ticket` keeps the dialogs mounted). The dialog stays open with the message.
- **CR3-01 — Fixed, both parts.** (a) A hint line inside the *Already fixed* block: "Set *When
  did it happen?* above to when the machine stopped." (b) Refusals on the `restore.*` times
  name the raise time as "the time it happened" instead of "Raised": `RAISE_SCREEN_LABELS`
  in the core, `validate_event_time(…, labels=)`, chosen in `_event_time` when the field starts
  with `restore.`. The existing API test now expects "Must be at or after the time it happened, …".
  Not done: the hard rule (force the failure time to be touched) the reviewer did not recommend.
- **CR3-02 — Fixed.** `StartedAtFields` remembers the last followed day in a local variable
  (initialised from `props.date`) and compares the date with it. When the parent has already
  put the new day there (a dialog opened again) it only re-syncs the remembered day.
- **CR3-03 — Fixed.** The saved line reads "Ticket TK-… saved and marked back in service."
  (or "… marked fixed" on a defect, from `moveSaveLabel`) when the returned state is
  `back_in_service`.
- **CR3-04 — Fixed.** The checkbox is a `btn-check` toggle: a full-width large button, outline
  green, solid green when ticked, labelled "Already fixed — back in service".

Decisions taken in this round:
- `latest_restoration` takes the events as rows with `event` and `occurred_at`, so the detail
  (already loaded) and the raise (`_event_rows`) share it; the raise now reads the events
  instead of a `MAX` query (one extra small read, a few rows).
- `_event_time` picks `RAISE_SCREEN_LABELS` from the field-name prefix rather than a new
  parameter threaded through `_apply_move` and the move steps.
- `useFormModal` gained `status` in its error (shared composable, one field).
- CR1-03 by `:key`, not a `reset()` method: no new API on `EventFields`.

Tests: `tooling/run-tests.bat` green. Backend 1823 passed, frontend (vitest) 93 passed in 12
files, dependency-audit tests 42 passed. `npx vite build` built, only the existing chunk-size
warning. Scratch jsdom checks (not in the repo; session scratchpad `mount-r3/`), 19 cases pass:
- all six MoveDialog moves, both RegradeDialog modes, EditTicketDialog, LabourPanel add and
  change, AssignDialog: mount and open without error;
- MoveDialog and RegradeDialog: "Change", then reopen: back at "Now"; a 409 without a field
  emits `reload` once; a 400 with a field does not;
- StartedAtFields, MoveDialog restore, and RaiseTicketView (unticked, ticked, a defect without
  `ticket:work`, refusals beside the right fields, no checkbox without `ticket:restore`): as in round 3.

This was jsdom only; the layout (the toggle button, the tap sizes) on a phone is still the
user's check.

Manual checks added by this round (plain; the important ones are unchanged above):
- "Now · Change" then cancel, then open another move: it starts at "Now".
- On a phone: the ticket page's Yes/No confirms and the row buttons are comfortable to tap.
- Raise a walk-in job with *Already fixed*: the toggle looks right, the hint line shows, and the
  saved line says "marked back in service".

### Round 3 (CR4-01…04)

The user said "fix the 4 nits". The § 5.1 `ORDERED_EVENTS` question is answered: keep as built.

- **CR4-01 — Fixed.** `MoveDialog` keys `<StartedAtFields>` on `opens`, as `EventFields` already is, so each
  opening mounts it fresh and `followedDay` comes from the reseeded date. The reviewer's `r4.test.js`
  (back in service reopened across midnight) now passes.
- **CR4-02 — Fixed.** The icon in the *Already fixed* label is `fa-regular fa-square` unticked and
  `fa-solid fa-square-check` ticked.
- **CR4-03 — Fixed.** `TicketDetailView.load()` keeps the shown ticket when a reload fails and clears it
  only on 404 or 403. To make that visible, the load-error alert is now its own `v-if` above the ticket
  block (it was an exclusive `v-else-if` branch, which would have hidden the kept ticket and unmounted the
  dialogs anyway), and the ticket block shows when `ticket && !notFound && !forbidden`. Decision: if the
  failed load was for a different ticket id than the one held (route change), the old ticket is dropped,
  so one ticket's data never sits under another's URL.
- **CR4-04 — Fixed.** `restoreFieldsKey` (ref, increment, `:key`, comment) removed from `RaiseTicketView`.

Checks: jsdom mount checks (MoveDialog, RaiseTicketView, earlier scratch files; scratch only, not in the
repo) 22 passed in 4 files. `tooling/run-tests.bat`: backend 1823 passed, frontend 93 passed in 12 files,
dependency-audit 42 passed. `npx vite build` built with only the existing chunk-size warning. The CR4-03
failure path (409 then a failing GET) has no automated test; it is a manual check below.

Manual check added (plain): on a ticket page, cause a 409 on a move, then drop the network so the reload
fails: the dialog stays, the error shows with *Retry*, and the page still scrolls after closing.

### Round 4 (CR5-01, CR5-02)

The user said "fix CR5-02, leave CR5-01".

- **CR5-01 — Deferred — left by the user.** A 404 or 403 on the reload after a 409 still leaves the page
  scroll-locked (`modal-open` on `body`); not changed.
- **CR5-02 — Fixed.** At the start of `TicketDetailView.load()`, a held ticket whose id differs from the
  route id is dropped, so the old ticket's buttons are never live under the new URL while the next one
  loads ("Loading..." shows instead). The same ticket is still kept on a failed reload (r3 behaviour:
  the 409 dialog stays).

Checks: the reviewer's scratch mount check (`r5.test.js` and the rest of `mount-r3/`, scratch only) with
the route-change case extended to assert that, while ticket 8 is pending, no header and no *Start* button
show and "Loading" does: 25 passed in 5 files. `tooling/run-tests.bat`: backend 1823 passed, frontend 93
passed in 12 files, dependency-audit 42 passed. `npx vite build` built with only the existing chunk-size
warning.

## Amendment A1 — Already fixed: raise and mark back in service in one go

Built from brief § 10 A1 (approved 20-10-2026 by KLA), on 6c58b7a + the
uncommitted S018 as it stood after code review r2. CR1-02 … CR1-08 and the
§ 5.1 `ORDERED_EVENTS` question were left as they are.

### What was built

- **The raise screen** has a checkbox, *Already fixed — back in service*, for a
  user who holds `ticket:restore` at the node's site. Ticked, it shows three
  fields:
  - *Back in service at* ("Fixed at" on a defect), as "Now · Change";
  - *Who did the work?* (`PersonPicker`, required);
  - *When did work start? (if known)*: a date and an empty time.

  Save then reads *Raise and mark back in service* (on a defect *Raise and
  mark fixed*). After Save the photo step and *Done* work as before.
- **The server** takes an optional `restore: {occurred_at?, person_id,
  started_at?}` on `POST /api/tickets`. It raises the ticket and applies the
  ordinary back-in-service move to it in the same transaction. The ticket then
  stands at *back in service*, and the engineer closes it as usual (labour,
  cause, action).
- **Refusals** on the block are named `restore.occurred_at`,
  `restore.person_id` and `restore.started_at`, and the screen shows them
  beside the new fields. Any refusal rolls the whole raise back: no ticket
  row, no event, no serial number used.

### How it works

- **Core (`tickets_core.validate_raise`).** When the body has `restore`, it
  is passed to the existing `validate_move("restore", …)`, so there is no
  second parser. Its errors come back prefixed `restore.`. If `restore` is not
  an object, the refusal is 400 on `restore`. `clean["restore"]` holds the
  move's clean body, or None when the block is not given.
- **Shell (`tickets.py`).** `make_move` keeps everything up to the lock. The
  rest of its old body is now `_apply_move(cur, ticket, move, clean, now,
  prefix="")`, in this order:
  1. the from-state check (409);
  2. `_last_ordered_event` and `_event_time`;
  3. the move's step (`_restore` for back in service);
  4. the move's event;
  5. `update_row` of the state;
  6. auto-assign for acknowledge / start.

  `raise_ticket` does three things for A1:
  - when `restore` is given, it checks `require_perm_at("ticket:restore",
    node site)` before the insert;
  - after the insert and the `raised` event, it calls `_apply_move(cur,
    read_ticket(cur, id), "restore", clean["restore"], now, "restore.")`;
  - the ticket row needs no lock, because it is this transaction's own row.

  The time and person rules (§ 5.1, § 5.8) are therefore the move's own code:
  - the back-in-service time is at or after the raise time, or the server's
    clock when none is typed;
  - `started_at` lies between the raise and the back-in-service time;
  - the person is anyone active at the site;
  - a `started` event is written, naming the same person, when a start time
    is given.
- **The times** come out of `ticket_times` unchanged, and there is no flag or
  migration:
  - with no start time, response and repair are null and downtime runs from
    the failure to back in service;
  - with a start time, all three come from the typed times.
- **Frontend.**
  - `EventFields` gained `withRemark` (default true).
  - The *When did work start?* pair moved from `MoveDialog` into a new
    `StartedAtFields.vue`, which `MoveDialog` and the raise screen both use.
  - The raise screen keeps the checkbox and the three fields in
    `blankForm()`, so a node change clears them.
  - It pre-fills the person with `userPersonId` only when `node.permissions`
    has `ticket:work` and that id is in the site's people list it already
    loads. The pre-fill is set once those people have loaded.
  - It sends `restore` only when the box is ticked. Inside it, `occurred_at`
    goes only when changed, and `started_at` only when the time is filled.

### Files touched

- `backend/tickets_core.py`: `RESTORE_BLOCK`, `RESTORE_FIELD_PREFIX`,
  `RESTORE_BLOCK_NOT_OBJECT`, and `_restore_block`, called at the end of
  `validate_raise`.
- `backend/tickets.py`:
  - `_apply_move` extracted from `make_move`;
  - `_restore` and the step signature take `prefix`;
  - `raise_ticket` checks `ticket:restore` and calls `_apply_move`;
  - one lock-order line added to the module docstring.
- `backend/tests/test_tickets_core.py`:
  - `test_each_intensity` now expects `"restore": None` in `clean`, the only
    edit to an existing test;
  - new `TestValidateRaiseRestore` (5 tests, 8 cases).
- `backend/tests/test_ticket_work_api.py`: new `TestAlreadyFixed` (11 cases).
- `frontend/src/views/tickets/StartedAtFields.vue` (new): the start date and
  time pair.
- `frontend/src/views/tickets/EventFields.vue`: the `withRemark` prop.
- `frontend/src/views/tickets/MoveDialog.vue`:
  - uses `StartedAtFields`, so its own date-follow watcher and
    `startDateTouched` are gone;
  - takes the time label from `restoreTimeLabel`.
- `frontend/src/views/RaiseTicketView.vue`: the checkbox, the three fields,
  the person default, the `restore` body, and the Save label.
- `frontend/src/utils/ticketLabels.js`: `restoreTimeLabel(intensity)` and
  `raiseSaveLabel(alreadyFixed, intensity)`, the latter built on
  `moveSaveLabel("restore", …)`.
- `frontend/tests/ticketLabels.test.js`: one test for the two labels.

### Decisions taken

- **The prefix is a parameter.** `_apply_move` and the move steps take a
  trailing `prefix` (default `""`), and only `_restore` uses it. This is the
  smallest way to name the refusals as the brief asks.
- **No ordering check in the core.** The brief says "the ordering checks
  reuse `validate_event_time`". They do, through `_event_time` inside
  `_apply_move`, against the `raised` event just written. I added no second
  ordering check in `validate_raise`, which would only repeat it.
- **A `remark` inside the block is accepted.** `validate_move("restore")`
  parses a remark, as it does for the move, and it would go on the
  `back_in_service` event. The screen never sends one. Filtering it out would
  mean a second parser.
- **The start date follows without a "touched" flag (small departure).**
  `StartedAtFields` follows the back-in-service date while the date still
  equals the day it last followed. The old `MoveDialog` instead used a
  `startDateTouched` flag, reset on every `open()`. The new rule needs no reset
  from either parent, and gives the same result except in one corner: a user
  who sets the date back to the followed day is followed again.
- **`restoreTimeLabel` is a new helper.** The raise screen would otherwise
  copy `MoveDialog`'s `isBreakdown ? 'Back in service at' : 'Fixed at'`.
  Before an intensity is picked, both labels use the defect wording ("Fixed
  at", "Raise and mark fixed"), as `moveSaveLabel` does today.
- **Placement and hiding.**
  - The checkbox sits below *Found by*, after all of the raise's own fields
    and above the open-tickets warning and Save. That is "below the description
    and time" without splitting the raise's fields.
  - The block is hidden with `v-show`, not `v-if`, so the "Now · Change"
    control keeps its state when the box is unticked and ticked again. With
    `v-if` it would show "Now" over a typed time.

### Not done / deferred / assumed

- No 403 test for a user who holds `ticket:raise` but not `ticket:restore`
  (BS2-05). No such user exists today. The server check is in place.
- A1 together with `repeat_of` is not tested on its own. The repeat check runs
  before the insert, as without A1.
- No labour on the raise screen (open point 2 as approved).

### Checks of the mounted screens (scratch only)

Nothing was added to the repo. In the session scratchpad I updated
`mount.test.js`, `vitest.scratch.config.mjs`, and a `vue-router` stub aliased
in that config. They mount the real components in jsdom with `createApp`, with
the api, auth and masters stores mocked. Vue warnings count as failures.
All 12 cases pass:

- **StartedAtFields:**
  - mounts;
  - the date follows a back-in-service time on another day, and follows it
    back to today when the time returns to "Now";
  - it stops following once the user picks a date;
  - the time input emits.
- **MoveDialog**, opened as restore from raised (start pair shown; the date
  follows a changed time), restore from in progress (no start pair),
  acknowledge, and close: no mount or open error.
- **RaiseTicketView, unticked:**
  - the block is hidden;
  - Save reads *Save ticket*;
  - the POST has no `restore`.
- **RaiseTicketView, ticked:**
  - the fields show, with "Now", no remark, and today's date;
  - the own person is pre-filled;
  - Save reads *Raise and mark back in service*;
  - a typed start time survives untick and re-tick;
  - the POST carries `restore: {person_id, started_at}`;
  - the photo step follows.
- **RaiseTicketView, other cases:**
  - *Change*: the typed time is sent as `restore.occurred_at`, and the start
    date follows it;
  - a defect, without `ticket:work`: Save reads *Raise and mark fixed*,
    nobody is pre-filled, and Save stops with "Who did the work? Pick a name";
  - a server refusal on `restore.started_at` shows beside the start field;
  - without `ticket:restore` there is no checkbox;
  - a node change unticks and clears the typed time.

This was jsdom only; how the screen looks on a phone is still the user's
check.

### Tests run

- `tooling/run-tests.bat`, all green:
  - backend: **1820 passed** (160 s);
  - frontend (vitest): **93 passed** in 12 files;
  - dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built, with only the existing chunk-size
  warning.

### Manual checks

Important:
- [ ] On a phone, raise a walk-in job with *Already fixed* ticked: the extra
  fields fit, Save stays visible, and the ticket page shows it at back in
  service with the right technician.

Plain:
- With and without a *started* time: the ticket page shows response and repair
  as typed, or "—".
