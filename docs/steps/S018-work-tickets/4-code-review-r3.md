```
Step: S018 — Work the ticket
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S018 — Code review, round 3 (amendment A1)

**Verdict: no `blocker` and no `major` is open.** A1 is built as § 10 A1
says, with the s2 answers. The `_apply_move` extraction leaves the move route
as it was. Any refusal rolls the whole raise back, and the `restore.*`
refusals show beside the right fields. This round has one `minor` and three
`nit` findings, all on the raise screen. CR1-02 to CR1-08 are still deferred
to the user at gate B. The § 5.1 `ORDERED_EVENTS` question still waits for
the user.

Scope of this round:
- A1 in `1-brief.md` § 10, with the Staleness s2 answers in the Review log;
- `## Amendment A1` in `3-impl-report.md`;
- the files changed since round 2. By file time these are exactly the ones
  the report lists:
  - `tickets.py`, `tickets_core.py`;
  - their two test files;
  - `ticketLabels.js` and its test;
  - `RaiseTicketView.vue`, `EventFields.vue`, `MoveDialog.vue`, and the new
    `StartedAtFields.vue`.

  No other code file changed.

## Test run

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: 1820 passed (155 s).
  - Frontend (vitest): 93 passed in 12 files.
  - Dependency-audit tests: 42 passed.
- `npx vite build` in `frontend/`: built. The only warning is the existing
  chunk-size one (main chunk 534 kB).
- **Scratch mount check** (my own, in the session scratchpad under
  `mount-r3/`; nothing added to the repo). It mounts the real components in
  jsdom with `createApp`, with the api and auth store mocked, and counts every
  Vue error and warning as a failure. All 6 cases pass:
  - **StartedAtFields:**
    - the date follows the back-in-service date and returns to today with
      "Now";
    - a date the user picked is never overwritten, either by a later time or
      by "Now".
  - **MoveDialog, restore from raised:**
    - after a time typed on another day, opening the dialog again resets the
      start date to today, and the date follows a new typed time. So the
      old "reset on open" behaviour holds without the `startDateTouched`
      flag.
    - *acknowledge* and *close* then open cleanly.
  - **MoveDialog, restore from in progress:** no start pair.
  - **RaiseTicketView, unticked:**
    - the block is hidden;
    - Save reads *Save ticket*;
    - the POST has no `restore`.
  - **RaiseTicketView, ticked (breakdown, `ticket:work`):**
    - no remark field or *Add remark*;
    - "Back in service at" is shown;
    - the own person is pre-filled;
    - Save reads *Raise and mark back in service*.
    - Server refusals named `restore.occurred_at`, `restore.person_id` and
      `restore.started_at` each show inside the block, and none goes to the
      top alert. A refusal on the raise's own `occurred_at` stays outside the
      block.
    - A typed start time survives untick and re-tick, and the POST then
      carries `restore: {person_id, started_at}` and no `occurred_at`.
    - The photo step follows.
  - **RaiseTicketView, defect without `ticket:work`:**
    - "Fixed at" is shown and Save reads *Raise and mark fixed*;
    - nobody is pre-filled, and the own person is first in the picker;
    - Save is stopped on the client with "Who did the work? Pick a name"
      inside the block;
    - after a node change to a site without `ticket:restore`, there is no
      checkbox.

## Findings

### CR3-01 — minor — The raise screen's two times are easy to get wrong for a walk-in job, and the refusal names an event the screen does not show

**Where:**
- `frontend/src/views/RaiseTicketView.vue:437-448` (*When did it happen?*)
  and `464-495` (the A1 block);
- `backend/tickets_core.py:408-416` (`validate_event_time`'s "Must be at or
  after Raised, …").

**Problem.** A1 is for work that is already over, so both times are usually
in the past. But *When did it happen?* is pre-filled with the phone's now.
It looks filled in, and the server uses its own clock while it is untouched.
*Back in service at* defaults to "Now". Two outcomes follow:

1. **Both left alone on a breakdown.** The ticket records failure = back in
   service = now, so downtime is **0 min**. No error is shown. A1 § 4 says
   downtime "runs from the failure time to back in service, which is real".
   That is only true when the user set the failure time. A zero-minute
   breakdown also pulls down the plant's MTTR (EN 13306 time to restoration).
2. **Only the back-in-service time set.** For example, *Back in service at*
   is set to 11:00, but *When did it happen?* is left at now (15:00). The
   server refuses beside *Back in service at* with "Must be at or after
   Raised, 21-10-2026 15:00". Nothing on the raise screen is called
   "Raised". What the user must change is *When did it happen?*, a field
   above the block. The message says what is wrong but not what to do.

**Failure scenario.** A fitter brings in a portable vibrator with burnt
brushes. It stopped at 09:00 and was fixed at 10:30, and he records it at
15:00. He picks *Stopped*, ticks *Already fixed* and names himself. Then:
- if he taps Save at once, the ticket shows downtime 0;
- if he sets only *Back in service at* to 10:30, he gets the "Raised"
  refusal and does not know which field to fix.

**Suggested fix.** This is the user's call, because the brief did not cover
it. Options:
- (a) one line inside the block when it is ticked, e.g. "Set *When did it
  happen?* above to when it stopped";
- (b) on the raise path, name the field the user sees in the refusal: "Must
  be at or after the time it happened (21-10-2026 15:00)". This could be a
  label passed to `validate_event_time`, or the raise screen could map the
  message;
- (c) both.

Recommend (c). A hard rule, such as requiring *When did it happen?* to be
touched when *Already fixed* is ticked on a breakdown, would be stricter.
Its cost is that a breakdown which really was raised and fixed "now" would
need an extra tap.

### CR3-02 — nit — StartedAtFields reads "today" at the moment of the change, not the day it seeded

**Where:** `frontend/src/views/tickets/StartedAtFields.vue:23-30`

**Problem.** For a null back-in-service time, `dayOf(null)` is computed when
the watcher runs. If a screen stays open across midnight, the "followed day"
moves without the date moving. The first typed time then finds the date
(yesterday) unequal to `dayOf(null)` (today) and treats it as user-picked.
The old `startDateTouched` flag would have followed. This is a second corner
besides the one the report states ("set back to the followed day is followed
again"). The raise screen is more exposed than the dialog: `blankForm()` seeds
`startedDate` when the node loads, and the screen may stay open for a while
on a night shift.

**Failure scenario.** At 23:55 an operator opens the raise screen and ticks
*Already fixed*. At 00:05 he sets *Back in service at* to 00:05 and types a
start time of 00:01. The start date stays on the old day, so `started_at`
goes out as the previous day 00:01. Usually that lies before the raise time,
so the server refuses it with "Must be at or after Raised, …" beside a start
time the user typed correctly; he has to notice the date. When the failure
time was more than a day back (or, in `MoveDialog`, the last event was), the
server accepts it, and response and repair come out about 24 h wrong.

**Suggested fix.** Keep the day that was last followed in a local ref,
initialised from `props.date`, and compare the date with it rather than with
`dayOf(old)`. This also removes the stated corner. It changes only
`StartedAtFields`.

### CR3-03 — nit — The success line does not say the ticket is already back in service

**Where:** `frontend/src/views/RaiseTicketView.vue:303-305`

**Problem.** After *Raise and mark back in service*, the photo step still
reads "Ticket TK-… saved." and "Add photos of the problem". The user has no
confirmation that the second half, back in service, was done, and no hint
that the engineer still has to close it.

**Suggested fix.** When the saved ticket's `state` is `back_in_service`,
show "Ticket TK-… saved and marked back in service." (or "… marked fixed" on
a defect), using the same `moveSaveLabel` wording.

### CR3-04 — nit — The *Already fixed* checkbox is a default-size box on a screen of large controls

**Where:** `frontend/src/views/RaiseTicketView.vue:465-468`

**Problem.** Every other control on the raise screen is `-lg`: the
intensity buttons, the selects, the time input and Save. The new checkbox is
a plain `form-check`, about 1 rem. The label is tied to it with `for`, so
tapping the text works, and this is not a shrunk target. But on a floor
screen it is the one control that decides what Save does.

**Suggested fix.** Either a larger box (`form-check-input` scaled, as some
apps do with `style="transform: scale(1.4)"` or a CSS class), or a Bootstrap
toggle button (`btn-check` + `btn btn-outline-success btn-lg w-100`) labelled
"Already fixed — back in service". The second option also makes the ticked
state obvious at a glance.

## Earlier rounds

### CR1-02 … CR1-08: deferred to the user at gate B (open, not unaddressed)

| ID | Severity | Subject | State |
|---|---|---|---|
| CR1-02 | minor | `_check_repeat` does not check the earlier ticket's state | Open (deferred); code unchanged |
| CR1-03 | minor | "Now · Change" keeps a stale draft across openings | Open (deferred); now also on the raise screen, see below |
| CR1-04 | minor | `btn-sm` tap targets on the ticket page's floor controls | Open (deferred); files unchanged |
| CR1-05 | nit | Two definitions of "latest restoration" | Open (deferred); code unchanged |
| CR1-06 | nit | An edit to a same-label symptom is silently dropped | Open (deferred); code unchanged |
| CR1-07 | nit | The Times card is always shown to operators | Open (deferred); file unchanged |
| CR1-08 | nit | A 409 leaves the user to reload by hand | Open (deferred); unchanged |

**CR1-03 gains a third user.** `EventFields` changed only by `withRemark`,
so its watch still resets `changing` only when `time` *changes* to null. On
the raise screen:
1. the user taps *Change* in the A1 block without typing, so `restoreAt`
   stays null;
2. he changes the equipment, so `resetForm()` sets `restoreAt` to null again,
   which is not a change.

The block then still shows the time input with the old phone time, while the
raise sends no `restore.occurred_at`. If the user fixes CR1-03 at gate B, the
fix (e.g. a reset the parent calls, or a key on the component) should cover
this use too.

## Manual checks

`3-impl-report.md` § *Amendment A1 › Manual checks* has A1's one important
check as an unticked box, and its plain check as a plain line. Nothing is
missing. The S018 section's five important checks are still there, unticked.

The user's **manual browser check** for A1:
- **On a phone (the important check).** Raise a walk-in job with *Already
  fixed* ticked. Check that:
  - the block fits, including the start date and time side by side inside
    the indented block on a narrow phone;
  - the people picker scrolls inside its own box;
  - Save is reachable;
  - the ticket page then shows *back in service* with the right person.
- **With and without a start time.** The ticket page shows response and
  repair as typed, or "—".
- **CR3-01 in practice.** Try the walk-in case both ways:
  - leaving both times alone (downtime 0);
  - setting only *Back in service at* to an earlier time (the "Raised"
    refusal).

  Then decide on CR3-01.
- **An operator** (no `ticket:work`) sees the box. Nobody is pre-filled, and
  his own name is first in the picker.
- **The move dialog's back in service from raised still behaves as before.**
  The start date follows a changed back-in-service time and resets on the
  next opening.

## Checked and found consistent

- **`_apply_move` keeps the move route's behaviour.** Staleness s2 recorded
  `make_move`'s r2 tail, and the extracted body matches it step for step:
  1. the from-state check, 409 `TICKET_CHANGED`;
  2. `_last_ordered_event`;
  3. `_event_time(clean["occurred_at"], …, "occurred_at")`;
  4. the `_MOVE_STEPS` dispatch;
  5. `_add_event` of the move's event, with the remark;
  6. `update_row` of the state and the changes;
  7. auto-assign for acknowledge and start.

  More detail:
  - `make_move` still does the 404 for an unknown move, `check_perm`,
    `clean_body`, and `_lock_open_ticket` (lock, 404, 403 at the ticket's
    site, closed 409) before the call, and reads the detail after it.
  - `ticket["id"]` replaces the route's `ticket_id`. They are the same value,
    because the locked row's `id` is merged in.
  - The prefix defaults to `""`, so every field name on the move route is
    unchanged.
  - `_send_back`, `_close` and `_not_a_fault` take the extra argument through
    `*_args`.
  - The move tests from r1 and r2 all pass unchanged.
- **The raise with `restore`:**
  - `require_perm_at("ticket:restore", node site)` runs after the scrapped
    check and before any insert.
  - `_apply_move` gets `read_ticket(cur, ticket_id)`. That row has the `id`,
    `state` (raised) and `site_id` that `_apply_move` and `_restore` read.
    `restore` is not an auto-assign move, so nothing else is needed.
  - The row needs no lock because it is this transaction's own. No new lock
    is taken.
  - The FK shared lock on the named person falls under the module
    docstring's existing "a raise naming that person" deadlock note, and the
    docstring gained a line for A1.
- **One transaction.** `db_helpers.transaction` rolls back on any exception.
  The restore refusals come after `next_counter` and the insert, so the
  `nothing_written` fixture proves the rollback (no ticket, no event, no
  counter change) in the three cases that reach the database: a person at
  another site, back in service before the raise, and a start outside raise
  … back in service. The two cases refused in `validate_raise` never open
  the transaction.
- **Core:**
  - `_restore_block` reuses `validate_move("restore", …)`, with no second
    parser.
  - Its errors are prefixed `restore.`, and a non-object is refused on
    `restore`.
  - The raise's own `occurred_at` keeps its name, which a test checks.
  - `clean["restore"]` is None when the block is absent or null.
- **Shell field names:** `_event_time(…, f"{prefix}occurred_at")`,
  `_check_person(…, f"{prefix}person_id")`, and both `started_at` refusals
  carry the prefix. The API tests assert `restore.person_id` (both messages),
  `restore.occurred_at` (the "Raised" message) and `restore.started_at`
  (before the raise and after back in service).
- **The frontend's error routing:**
  - `fieldErrors[err.field]` keys on the full `restore.*` name, and the block
    reads exactly those three keys. `EventFields` shows `timeError` in "Now"
    mode too.
  - A `restore` or `restore.remark` refusal would have no place on the
    screen, but only a malformed client could cause one.
- **The pre-fill (BS2-04):** `userPersonId` is used only when
  `node.permissions` has `ticket:work` and the id is in the loaded site
  people. It is set after the people load, and the form reset happens before
  that. IT admin has no membership, so it is never pre-filled.
- **`blankForm()`** holds the checkbox and the four values, so a node change
  clears them (BS2-08). The scratch check confirms it.
- **The labels:**
  - `raiseSaveLabel` is built on `moveSaveLabel("restore", …)`, and
    `restoreTimeLabel` is shared with `MoveDialog`, so the wording is not
    copied.
  - Both labels default to the defect wording before an intensity is
    picked. The report says so.
  - Both have a test in `ticketLabels.test.js` (BS2-07).
- **StartedAtFields' following rule (the stated departure).** I judge it
  acceptable:
  - In `MoveDialog`, each `open()` replaces the form, and the watcher sees
    the new date when it runs, so the old "reset on open" behaviour holds.
    The scratch check confirms this.
  - The departure is listed in "Decisions taken", and it removes a flag that
    both parents would otherwise have to reset.
  - Its one real edge is CR3-02 (midnight), not the corner the report
    names.
- **EventFields `withRemark`:** the default is true, so every dialog is
  unchanged. On the raise screen it hides both the textarea and *Add remark*.
- **`v-show` on the block:** the reason is stated in the report and is
  sound, since the time control keeps its state. Hidden values are never
  sent, because `restoreBody()` runs only when the box is ticked.
- **Scope:**
  - Everything in A1's *Where* is built. Nothing else changed: no migration,
    no new route, no flag.
  - The departures are all in "Decisions taken": the prefix parameter, no
    second ordering check, the remark accepted, the date rule, the new label
    helper, the placement below *Found by*, and `v-show`.
  - The checkbox placement ("below the description and time") is stated and
    sensible.
- **Tests against A1's list:** all present:
  - 201 with and without a start, with the times;
  - "no time given is now";
  - the operator naming himself;
  - the storekeeper 403 with nothing written;
  - the four refusals, named;
  - the ordinary close, with labour required.

  The 403 test for a user without `ticket:restore` was dropped as approved
  (BS2-05). A1 with `repeat_of` has no test of its own, as stated; the repeat
  check runs before the insert, unchanged.
- **Security:**
  - The route stays `@require_perm("ticket:raise")`, and the restore key is
    checked at the node's site.
  - The actor comes from `actor()`, and the person is checked on the server.
  - No SQL is built from strings: the `IN` placeholders are generated, as
    before.
- **Layering:** the time and person rules stay in the core and the shared
  move step. The page holds only the default-person rule, which the brief
  places there (BS2-04).
- **No deprecated APIs, no swallowed exceptions.** `loadPhotoLimit`'s
  `catch` is S017's, commented.
- **The 503 / dead connection path** is unchanged: `get_db()` comes before
  the transaction, as in S017.
- **Track: full.** Nothing to check against the light criteria.
