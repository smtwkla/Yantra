```
Step: S018 — Work the ticket
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S018 — Code review, round 1

**Verdict: one `blocker` is open (CR1-01). No `major`.** None of the new
dialogs can open in the browser, so no move, re-grade, edit or labour can be
made from the ticket page. The backend is sound and well tested. The fix is
small, but the screens must then be tried in a browser before gate B.

Reviewed against the brief as approved (Baseline cfedc46, staleness s1) and
`3-impl-report.md`. Amendment A1 is approved but deliberately not coded yet,
so it is not reviewed here. The S017 post-commit fix in `RaiseTicketView.vue`
(`watch(nodeId, …, { immediate: true })`) and the uncommitted docs are not
S018 findings.

## Test run

- `tooling/run-tests.bat`: **green**.
  - Backend: 1801 passed (162 s).
  - Frontend (vitest): 92 passed in 12 files.
  - Dependency-audit tests: 42 passed.
- `npx vite build` in `frontend/`: built. The only warning is the existing
  chunk-size one (main chunk 530 kB).
- A scratch mount of the new dialogs: I mounted `MoveDialog`, `RegradeDialog`,
  `EditTicketDialog` and `LabourPanel` in jsdom, from the session scratchpad.
  Nothing was added to the repo. All four throw on render, and calling `open()`
  then throws (CR1-01). The repo has no component tests, so the green suite
  could not catch this.

## The question pending with the user (ORDERED_EVENTS)

The choice itself waits for the user. I only checked whether the code carries
it through consistently, and it does:

- **The order check.** `_last_ordered_event` filters on
  `tickets_core.ORDERED_EVENTS`. The order check (`_event_time` →
  `validate_event_time`) and the default time `max(now, last ordered event)`
  both use that same event.
- **The times.** `ticket_times` skips every event outside `ORDERED_EVENTS`, so
  bookkeeping lines never feed the figures.
- **Stamps on bookkeeping lines.** An auto-assign's *assigned* line takes the
  move's event time, and the *edited* line at close takes the close's time.
  Both are consistent with the timeline being in event-time order.
- **Tests.** `test_an_assignment_does_not_hold_back_a_typed_time` (API) and
  `test_bookkeeping_events_are_ignored` (core) cover the choice.

One correction to the report: the literal rule is not quite "a one-line
change". If the filter were dropped, `EVENT_LABELS` in `tickets_core.py` has no
entry for `edited`, `assigned` or `unassigned`. The refusal would then read
"Must be at or after assigned, …", with the raw event name. Those three labels
would have to be added as well.

## Findings

### CR1-01 — blocker — Every new dialog fails to render; none can be opened

**Where:**
- `frontend/src/views/tickets/MoveDialog.vue:52-56`
- `frontend/src/views/tickets/RegradeDialog.vue:28-32`
- `frontend/src/views/tickets/EditTicketDialog.vue:28-32`
- `frontend/src/views/tickets/LabourPanel.vue:38-46`

**Problem.** `useFormModal` creates the form at setup as `ref(blank())`
(`composables/useFormModal.js:22`). All four components pass
`blank: (seed) => seed`, so `form.value` starts as `undefined`. Each template
then reads a field of the form outside any `v-if`, and the read fails:

- MoveDialog: `EventFields v-model:time="form.occurred_at"`. Its
  `watch(() => form.value.occurred_at, …)` also fails at setup.
- RegradeDialog: `form.intensity` and `form.occurred_at`.
- EditTicketDialog: `v-model="form.component_id"`.
- LabourPanel: the `person` computed reads `form.value.person_id`, and the
  template reads `form.person_id`.

The first render of `FormModal`'s slot throws, so `FormModal` renders as a
comment. Its Bootstrap modal is then built on a missing element ("reading
'backdrop'"). Every later `open()` throws "Cannot read properties of null
(reading 'show')".

Reproduced by mounting each component in jsdom:
- the mount errors are `TypeError: Cannot read properties of undefined
  (reading 'occurred_at' | 'intensity' | 'component_id' | 'person_id')`;
- then `open()` throws.

`AssignDialog` returns a real object (`blank: () => ({ person_id: null })`)
and is not affected.

**Failure scenario.** A technician taps *Acknowledge* and nothing opens: the
console shows the TypeError. The same happens for:
- *Start*, *Back in service* / *Fixed*;
- *Send back*, *Close*, *Not a fault*;
- *Machine stopped*, *Change severity*;
- *Edit*, *Add labour* and the labour row's *Change*.

None of S018's work can be done from the page. All five important manual checks
would fail on the first tap.

**Fix.** Make `blank` return a full form object even when no seed is given.
Either:
- give each dialog its own default shape, e.g.
  `blank: (seed) => seed ?? { occurred_at: null, remark: "" }` (a labour row:
  `{ person_id: null, trade_id: "", work_date: "", hours: "", minutes: "" }`);
- or make `useFormModal` call `blank()` lazily.

The first keeps the shared composable unchanged. Then open every dialog once in
the dev server before handing back.

A small vitest mount test per dialog would stop this coming back: mount, call
`open(…)`, expect no error. That test is optional, since the repo has no
component tests yet. If you add one, say so in the report.

### CR1-02 — minor — The server's repeat check does not check the earlier ticket's state

**Where:** `backend/tickets.py:568-578` (`_check_repeat`)

**Problem.** § 5.5 says the earlier ticket's "state is back in service or
closed". `_check_repeat` checks only:
- that the earlier ticket is readable;
- that it is on the same machine;
- `not_a_fault`;
- the 0–7 day window from its latest `back_in_service`.

Only the detail's `can_raise_repeat` looks at the state (`REPEAT_FROM_STATES`).
A ticket sent back after a restoration is *in progress* again, yet still has a
`back_in_service` event inside the window. The server accepts it as a repeat
target.

**Failure scenario.**
1. TK-…-014 is back in service at 10:00.
2. The operator opens its page; *Not fixed — raise again* is shown.
3. At 10:20 the engineer sends it back (machine down). The work is not finished,
   and the open ticket is being worked again.
4. The operator, still on the old page, raises the repeat. It is accepted
   (201) and linked to a ticket whose repair is still going on.

The repeat count then counts a failure that is the same open job, and two open
tickets now track one fault. The same applies to any API client.

**Fix.**
1. In `_check_repeat`, refuse when `earlier["state"] not in REPEAT_FROM_STATES`
   (400 on `repeat_of_id`). Ideally put this in the core, e.g. pass the state to
   `is_repeat_candidate` or add a small core function, so the detail and the
   raise share one rule.
2. Give a not-a-fault ticket, and a ticket at the wrong state, a message that
   fits. Today a not-a-fault ticket gets "…was not back in service within 7
   days…", which is misleading. "That ticket can't be repeated: it is not back
   in service" would do.
3. Add an API test: send back, then raise with `repeat_of_id` → 400.

### CR1-03 — minor — "Now · Change" keeps a stale time across dialog openings

**Where:** `frontend/src/views/tickets/EventFields.vue:28-38`

**Problem.** `changing` and `remarkShown` are reset only when `props.time` or
`props.remark` *changes* to null or empty. *Change* fills `draft` but emits
nothing, so `time` stays null. The next `openCreate` sets `occurred_at: null`
again, which is no change, so the watch never fires.

`MoveDialog` and `RegradeDialog` are mounted once and reused for every move. A
later open therefore shows the time input with the old draft, while the dialog
still sends no `occurred_at` (server time).

**Failure scenario.**
1. At 10:04 a technician opens *Acknowledge*, taps *Change* (the input shows
   10:04) and cancels.
2. At 11:30 he opens *Start*. The dialog shows the input with "10:04", not
   "Now".
3. He leaves it and saves. The event is recorded at 11:30, while the screen
   told him 10:04.

A supervisor at shift end who reads the shown time as what will be stored gets
a different record than he saw.

**Fix.** Reset the two flags on every open. Either key `EventFields` on an
open counter (`:key="openCount"`), or expose a `reset()` that the dialogs call
in `open()`.

### CR1-04 — minor — Small tap targets on the ticket page's floor controls

**Where:**
- `frontend/src/views/TicketDetailView.vue:222, 234, 243-244, 280`
- `frontend/src/views/tickets/LabourPanel.vue:130, 145, 148, 155-156`

**Problem.** The ticket page is a floor screen, used on a phone by
technicians and engineers. Several of its controls use `btn-sm`:
- *Assign*, *Unassign* and the inline *Yes* / *No* of "Remove <name>?";
- *Edit*;
- *Add labour* in the panel header, the labour row's *Change* and *Remove*,
  and their *Yes* / *No*.

The UX checklist asks that tap targets on floor screens are not shrunk. The
confirm buttons matter most: a gloved thumb on a small *Yes* next to a small
*No* is where a mis-tap removes a labour row, which is a hard delete with no
timeline line.

**Failure scenario.** An engineer in the workshop means to tap *No* after
"Remove?", hits *Yes*, and the row is gone. It must be typed in again from
memory.

**Fix.** Use the default button size, not `btn-sm`, for these controls on the
ticket page. At least do it for the inline *Yes* / *No* confirms and the row
actions, and give them a little more gap. The card-header buttons may stay
compact if they keep a 44 px target.

### CR1-05 — nit — `_latest_back_in_service` and `_latest_restoration` compute the same thing two ways

**Where:** `backend/tickets.py:285-287` and `backend/tickets.py:562-565`

**Problem.** The detail takes the latest `back_in_service` from the loaded
events in Python, and the raise takes it with its own SQL `MAX`. That is two
definitions of "the latest restoration" for one rule (§ 5.5). If one is later
changed (for example, to ignore a restoration that was sent back, per CR1-02),
the button and the server can disagree.

**Fix.** Keep one. Either the raise reads `_event_rows` and uses the Python
helper, or both use the SQL helper. Better still, decide the whole "may this
ticket be repeated" rule in one core function (see CR1-02).

### CR1-06 — nit — An edit that changes the symptom to one with the same label is silently dropped

**Where:** `backend/tickets.py:854-857` (`edit_ticket`)

**Problem.** The save happens only when `edit_lines` returns text, and the
lines compare *labels*. Mode labels are unique only within one picker's scope
(`_check_mode_label`). After a machine's class changes, through a model change,
the ticket's old-class mode can share a label with a mode of the new class.
Choosing that mode then writes nothing and answers 200.

**Failure scenario.** This is rare. An engineer re-picks "Leakage" on a ticket
whose machine changed class. Nothing is stored, and the ticket keeps the old
class's mode. No error is shown.

**Fix.** Decide "something changed" from the ids (`clean` against the locked
row), and use the labels only for the text of the line.

### CR1-07 — nit — The Times card is always shown to operators

**Where:** `frontend/src/views/TicketDetailView.vue:74-75`

**Problem.** § 1 says the panels are "shown only to `ticket:work` holders or
when not empty". `ticket_times` always returns a number for `downtime_minutes`
(0 on a defect), so the "not empty" test is always true. An operator on a fresh
defect sees "Response —, Repair (hands on) —, Downtime 0 min".

**Fix.** Treat the card as empty when response and repair are null and
downtime is 0, or show it to everyone on purpose and say so in the report.

### CR1-08 — nit — A 409 "This ticket changed — reload" leaves the user to reload by hand

**Where:**
- `frontend/src/views/tickets/MoveDialog.vue:67`
- `frontend/src/views/tickets/RegradeDialog.vue:36`

**Problem.** On a stale state the dialog shows the 409 text at the top and
stays open on the stale page. On a phone, "reload" means closing the dialog
and pulling to refresh, which the user may not know to do.

**Fix.** On a 409 with no field, emit a reload, so the parent calls `load()`.
Or show a *Reload* button in the dialog's error line. The server's 409 is
unchanged.

## Earlier rounds

None: this is round 1.

## Manual checks

`3-impl-report.md` has a `## Manual checks` section. It carries all five
important checks of § 8 as unticked boxes and the plain ones as a list.
Nothing is missing.

What still needs the user's **manual browser check**, after CR1-01 is fixed:
- **Every dialog, once:**
  - acknowledge, start, back in service with and without the start time,
    send back (Yes / No), close, not a fault;
  - *Machine stopped* as an operator, *Change severity* as a technician;
  - Edit, Assign, Add / Change / Remove labour.

  For each, check that it opens, fills its defaults ("Recording as …", own
  name, today, the only trade, 5.1 on not a fault) and saves.
- **The five important checks of § 8,** above all the Android and iPhone check
  that *Close ticket* and *Cancel* stay on screen with the keyboard up (the
  `modal-dialog-scrollable` change applies to every dialog in the app). Also
  look at one existing dialog, e.g. the equipment edit, to see it still behaves.
- **"Now · Change" across two openings** (after the CR1-03 fix): the second
  dialog opens at "Now".
- **The action-bar order on a phone and on a wide screen:** the significant
  moves on the left in one row, after a gap when stacked.
- **The raise screen from *Not fixed — raise again*:** the intensity and
  symptom are pre-filled, the "Repeat of …" line shows, and Save links the two
  tickets.

## Checked and found consistent

- **Migration v13** is append-only:
  - every statement is safe to run twice;
  - the brief's named FKs, the CHECK `chk_ticket_labour_minutes` and the
    indexes are all there;
  - `ix_ticket_assignees_person` is reported (decision 12);
  - `test_migration_v13.py` covers the columns, the constraints and a re-run.
- **RBAC** (§ 5.7):
  - the four keys have the right holders through the ladder, and all four are
    in `SITE_SCOPED`;
  - `ASSIGNABLE_ROLES` lives in `config_rbac.py`, so route code names no role;
  - the supervisor stays off the ladder;
  - IT admin holds all four keys by token but has no site role, so it is
    never assigned, auto-assigned or offered as a default person (tested).
- **Every new route is permission-gated:**
  - each has a decorator, or `check_perm(spec.key)` for the move route;
  - each checks its key at the ticket's site (the site of `tickets.unit_id`),
    via `_lock_ticket` → `require_perm_at`;
  - the order is 404 (access predicate), then 403, then 409 closed, then 409
    stale state;
  - re-grade checks the lowering against `ticket:work` at the site.
  - The actor always comes from the server (`actor()`). Every person, role and
    trade is read from memberships, never from the client or the token.
- **SQL:**
  - every value is a placeholder;
  - the f-strings add only placeholder lists and code-constant column or table
    names (`_check_code_frozen`, `_check_active_code`).
- **Transactions and locks** (§ 5.3):
  - every write locks only the ticket row (7) and decides every refusal from
    the locked row;
  - a plain read after the lock takes a fresh snapshot;
  - `_assign`'s check and insert are serialised by the ticket lock;
  - the threaded concurrency test is kept and asserts a real wait.
  - The cause and action code freeze compares with the locked row and counts
    with `LOCK IN SHARE MODE`. It is shared with modes through
    `_check_code_frozen` (decision 8), and tested.
- **The pure core** (`tickets_core.py`):
  - no DB, no clock, no Flask;
  - the `MOVES` table matches § 1;
  - `send_back_intensity`, `regrade_options`, `validate_regrade`,
    `validate_close` and `validate_labour` follow § 1 and § 5.2;
  - `ticket_times` follows § 5.4: it reads intensity only from the events'
    column, clamps every interval at zero, and gives all null on not a fault.
  - The repair figure counting an open *in progress* up to now is reported.
- **The default event time** is the server's clock. It is raised to the last
  ordered event when that event lies up to `FUTURE_SKEW` ahead (decision 2,
  sound). The dialogs send `occurred_at` only when the input was edited.
- **Back in service after the fact:**
  - `started_at` is bounded by the last event and the restoration;
  - from *in progress* it is 400 (decision 7, reported);
  - the *started* event carries the same person;
  - the across-midnight case is tested.
- **Close:**
  - the order is symptom (400), labour (409), active cause and action, then the
    description rule;
  - a changed symptom writes an *edited* line before *closed*.
- **Not a fault:** it is reached from raised or acknowledged, needs a cause and
  a remark, keeps the labour, and is left out of the times.
- **Documents:**
  - `Owner.kinds` and the photos-only refusal are removed, and the comments are
    updated;
  - `can_add_documents` is sent by the server;
  - `DocumentsCards.canEditDocuments` and the upload modal's ticket line are
    done;
  - the S017 test is replaced by a 201 test.
- **The pickers:**
  - the `?ticket_id=` anchor for `/people` and `/modes` goes through one
    `_picker_anchor`, with 404, `ticket:read` at the ticket's site, and 400
    with no anchor;
  - the cross-site-move test is there.
- **`/api/auth/me` `person_id`** is filled, and is null when the database is
  down (tested).
- **The list:** *Assigned to me* is empty for a user with no person, and
  assignees are fetched for a page in one query (no N+1).
- **Layering:**
  - business rules are in `tickets_core`, and routes are a thin shell;
  - the Vue files only mirror rules for early feedback (zero minutes, the
    required remark, Close disabled without labour), and the server decides
    each again;
  - `groupPeople`, `intensityChanges` and `minutesText` are pure and tested in
    `ticketLabels.test.js`.
- **DRY:**
  - the shared test helpers moved to `tests/ticket_helpers.py` and
    `conftest.py`, not copied;
  - `EventFields` and `PersonPicker` are shared by the dialogs.
- **UX:**
  - `FormModal` is `modal-dialog-scrollable`, and the picker list has its own
    scroll (16 rem);
  - Close, Not a fault and Send back are set apart, outline style, with
    labelled Saves and the consequence line;
  - Close is disabled with visible text "Add the labour first" and an
    *Add labour* button;
  - "Recording as" / "Nobody will be assigned" is shown;
  - Send back's Yes / No is a selected-state choice;
  - the empty states read "No labour yet." and "Nobody assigned";
  - a user without a key sees no control.
- **Scope:** I found no feature beyond the brief that the report does not list.
  The extras (`assignable`, `can_raise_repeat`, `EventFields`,
  `_check_code_frozen`, Labour POST answering 201, edit "Nothing to change")
  are all under "Decisions taken".
- **Track: full.** Nothing to check against the light criteria.
