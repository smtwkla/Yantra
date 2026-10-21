```
Step: S018 — Work the ticket
Doc: code-review r4
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S018 — Code review, round 4 (fix round 2: CR1-02…08, CR3-01…04)

**Verdict: no `blocker` and no `major` is open.** All eleven findings the
user sent back ("fix CR1, CR3") are fixed. This round raises four `nit`s.
One of them, CR4-01, is the CR3-02 midnight corner, which is still there in
`MoveDialog` and was reproduced in jsdom. The § 5.1 `ORDERED_EVENTS` question
still waits for the user; that code is unchanged.

Scope of this round:
- `3-impl-report.md` § *Fix rounds › Round 2*, with its "Decisions taken";
- the files changed since round 3. By file time these are:
  - `tickets.py`, `tickets_core.py` and their two test files;
  - `useFormModal.js`;
  - `RaiseTicketView.vue`, `TicketDetailView.vue`, `LabourPanel.vue`,
    `MoveDialog.vue`, `RegradeDialog.vue` and `StartedAtFields.vue`.

  This matches what the round describes. `EventFields.vue` and
  `ticketLabels.js` are unchanged, which is right: the key lives in the
  parents, and `moveSaveLabel` is reused.

## Test run

- `tooling/run-tests.bat`: **green**, exit 0. The log is complete, so the
  backend count did not need a separate run.
  - Backend: **1823 passed** (158 s).
  - Frontend (vitest): **93 passed** in 12 files.
  - Dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built. The only warning is the existing
  chunk-size one (534 kB).
- **Scratch mount check.** It lives in the session scratchpad under
  `mount-r3/`; nothing was added to the repo. I re-ran all four files: my
  r3 `a1.test.js`, the coder's `dialogs.test.js` and `fix.test.js`, and a new
  `r4.test.js`. Each case mounts the real components in jsdom, and any Vue
  error or warning counts as a failure. **21 of 22 pass.**
  - Still passing:
    - every r3 A1 case;
    - all six `MoveDialog` moves, both `RegradeDialog` modes,
      `EditTicketDialog`, `LabourPanel` add and change, and `AssignDialog`;
    - "Change, then reopen: back at *Now*";
    - a 409 with no field emits `reload` once, and a 400 with a field does not.
  - New in `r4.test.js`, passing:
    - **StartedAtFields mounted at 23:55** (`Date` faked) with a
      back-in-service time typed at 00:05 the next day: the date follows to
      the new day (CR3-02 on the raise screen).
    - **RaiseTicketView:**
      - a tap on the toggle's label ticks it;
      - the hint "Set *When did it happen?* above…" shows;
      - *Change* in the block, then a change of equipment, returns the block
        unticked and at "Now";
      - after Save with `state: back_in_service`, the line reads
        "… saved and marked back in service."
  - New, **failing** (CR4-01): `MoveDialog` *back in service* opened at
    23:50 and again at 00:10, both times left at "Now". A back-in-service
    time then typed for 23:58 the day before leaves the start date on the
    new day.

## Findings

### CR4-01 — nit — In `MoveDialog` the start date can still stop following after midnight (CR3-02 fixed on the raise screen only)

**Where:**
- `frontend/src/views/tickets/MoveDialog.vue:203-210`
- `frontend/src/views/tickets/StartedAtFields.vue:29-37`

**Problem.** `followedDay` is set once, when `StartedAtFields` mounts. On
the raise screen this is enough. The form sits under `v-else-if="node"`, so
every change of node remounts it, and the date is today when it mounts. The
r4 check confirms this.

`MoveDialog` is different. It is mounted once per ticket page, and
`StartedAtFields` stays mounted between two *back in service* openings of
the same ticket. On reopen, `open()` sets the date back to today. If
`occurred_at` was null both times (the user left "Now"), the watcher does not
run, so `followedDay` keeps the day of the first opening. After midnight the
date (the new today) no longer equals `followedDay`, so it is taken for a
date the user picked. A back-in-service time typed for the evening before
then leaves the start date on the new day.

**Failure scenario.**
1. At 23:50 a supervisor opens *Back in service* and cancels.
2. At 00:10 he opens it again and sets *Back in service at* to 23:58 the
   evening before.
3. He types the start time 23:40.
4. `started_at` goes out as today 23:40. The server refuses it beside the
   start field: "Work cannot start after the machine was back in service".
   He has to notice that the date is wrong and change it.

Nothing wrong is stored, but this is exactly the night-shift entry the
following rule exists for.

**Suggested fix.** Add `:key="opens"` to `<StartedAtFields>` in
`MoveDialog`, as `EventFields` already has. Each opening then mounts it
fresh, `followedDay` comes from the reseeded date, and the "re-syncs only"
branch is no longer needed for the dialog.

### CR4-02 — nit — The unticked toggle shows a filled square

**Where:** `frontend/src/views/RaiseTicketView.vue:475` (the `<i>` in the
*Already fixed* label)

**Problem.** Unticked, the icon is `fa-solid fa-square`, a solid green block
on the outline button. That reads more like a filled box than an empty one.
Ticked, it is `fa-solid fa-square-check`. The two states differ mainly by the
button's fill, not by the icon.

**Suggested fix.** Use `fa-regular fa-square` for the unticked state. The
regular set is loaded (`all.min.css`) and used elsewhere, e.g.
`fa-regular fa-clock`.

### CR4-03 — nit — The 409 reload can leave the page scroll-locked when the reload itself fails

**Where:**
- `frontend/src/views/TicketDetailView.vue:115-121` (`load()`'s `catch`)
- the `@reload="load"` on `MoveDialog` and `RegradeDialog`

**Problem.** CR1-08's reload runs while the dialog is open. If that `GET`
fails (a dropped mobile link, or a 503 while the DB restarts), `load()` sets
`ticket` to null. The `v-else-if="ticket"` block then unmounts both dialogs
while a Bootstrap modal is shown. `FormModal`'s `onBeforeUnmount` calls
`modal.dispose()`, which removes the backdrop. It does not undo the body's
`modal-open` class or its `overflow: hidden`.

**Failure scenario.**
1. On a weak signal a technician's *Start* gets 409 "This ticket changed —
   reload".
2. The automatic reload times out.
3. The page shows the load error and *Retry*, and the dialog vanishes.
4. After *Retry* the ticket shows again but the page will not scroll until
   he leaves it.

This is rare: it needs a 409 and a failed `GET` back to back.

**Suggested fix.** Either:
- in `load()`, keep the shown ticket when a reload fails, and clear it only
  on 404 or 403;
- or have `FormModal` hide the modal before `dispose()` when it is unmounted
  while shown.

The first change is smaller and stays in this step's file.

### CR4-04 — nit — `restoreFieldsKey` on the raise screen has no effect; my r3 note about a "third user" of CR1-03 was wrong

**Where:** `frontend/src/views/RaiseTicketView.vue:177-178, 190, 480`

**Problem.** In r3 I wrote that after *Change* in the *Already fixed*
block, a change of equipment would leave the time input showing. It does
not. Every node change runs `loadNode()`, which sets `node` to null before
its first `await`. The whole form, `EventFields` included, therefore unmounts
and mounts fresh. The new r4 check passes for that reason. `resetForm()` runs
only on a node change, so the counter adds nothing.

It is harmless, but it is a mechanism with no effect, and a later reader
will look for the case it guards.

**Suggested fix.** Either remove the `restoreFieldsKey` ref, its increment
and the `:key`, or keep it and say in its comment that it is a guard in case
the form stops unmounting on a node change. My preference is to remove it.
This one is my error, not the coder's: the round did what r3 asked.

## Earlier rounds

Each of the eleven findings the user sent back was checked in the code, and
in the tests or the scratch mount where they can show it.

| ID | Sev. | State | Checked |
|---|---|---|---|
| CR1-02 | minor | **Fixed** | `tickets_core.latest_restoration(state, not_a_fault, events)` returns None unless the state is in `REPEAT_FROM_STATES` and the ticket is not a not-a-fault. `_check_repeat` refuses None with `REPEAT_NOT_RESTORED` before the 7-day check, so the message now fits the case. Core test: `test_latest_restoration_needs_a_restored_state`. API test: `test_a_ticket_sent_back_cannot_be_repeated` (the detail says no, and the raise gets 400 with the exact text). |
| CR1-03 | minor | **Fixed** | `MoveDialog` and `RegradeDialog` key `EventFields` on `opens`, which is incremented before `openCreate`. The scratch check passes: *Change*, then reopen, is back at "Now". On the raise screen the key is redundant (CR4-04). |
| CR1-04 | minor | **Fixed** | `TicketDetailView.vue` and `LabourPanel.vue` no longer use `btn-sm`. Both inline Yes/No confirm rows use `gap-3`. |
| CR1-05 | nit | **Fixed** | The SQL `MAX` helper and `_latest_back_in_service` are gone. The detail and `_check_repeat` both pass event rows to `latest_restoration`. |
| CR1-06 | nit | **Fixed** | `edit_ticket` writes the row when any submitted field differs from the locked row. `component_id`, `failure_mode_id` and `description` are all in `_LOCK_TICKET`, so `ticket[field]` cannot raise a `KeyError`. The *edited* line still depends on the labels. If labels differ, the values differ too, so no line is ever written without a save. Test: `test_a_symptom_with_the_same_label_is_still_saved`. |
| CR1-07 | nit | **Fixed** | `showTimes` hides the card from a viewer without `ticket:work` when response and repair are null and downtime is 0. The not-a-fault rule is kept. |
| CR1-08 | nit | **Fixed** | `useFormModal` adds `status` to `error`. Both dialogs emit `reload` on a 409 with no field, and `TicketDetailView` calls `load()`. `loading && !ticket` keeps the dialogs mounted on success. A 409 from the close's labour rule also reloads, which is harmless and even useful. The failure path is CR4-03. |
| CR3-01 | minor | **Fixed** (a + b) | (a) The hint line sits inside the block. (b) `RAISE_SCREEN_LABELS` is in the core. `_event_time` picks it when the field starts with `restore.`, so both `restore.occurred_at` and `restore.started_at` refusals say "the time it happened". The ticket page's moves keep "Raised", which that page does show. The API test asserts the exact text. The hard rule was not built, as recommended. |
| CR3-02 | nit | **Fixed on the raise screen; still open in `MoveDialog`** | The `followedDay` variable fixes the case raised in r3. The dialog's reopen across midnight is CR4-01. |
| CR3-03 | nit | **Fixed** | "… saved and marked back in service." or "… marked fixed", built from `moveSaveLabel`, so no wording is copied. Confirmed in the scratch check. |
| CR3-04 | nit | **Fixed** | A `btn-check` checkbox with a full-width `btn-lg` label, outline green when unticked and solid green when ticked. A tap on the label ticks it (scratch check). The icon is CR4-02. |

**Other callers of the shared `useFormModal`.** The change only adds one
field, `status`, to the error object. Nothing else in the repo reads or
compares that object's shape. The dialogs that set `error.value` by hand
(equipment form and move, `AssignDialog`, `LabourPanel`, `MoveDialog`,
`RegradeDialog`) set `{field, message}`. With no `status` there, the 409
watcher stays quiet. The masters panels (`useMasterForm`), the equipment
modals and the document modals neither use `status` nor watch `error`, so
they are unaffected. The coder's `dialogs.test.js` still mounts and opens
every ticket dialog cleanly.

**§ 5.1 `ORDERED_EVENTS`:** still with the user, and the code is unchanged.

## Manual checks

`3-impl-report.md` `## Manual checks` still lists all five important S018
checks as unticked boxes. The A1 section still has its one important check.
Round 2 added three plain checks: "Now · Change" across openings, the
confirm tap sizes on a phone, and the toggle with its hint and success line.
Nothing is missing.

What the user should still check in the browser:
- **The five important S018 checks and the A1 phone check,** as listed in
  the report.
- **The toggle on a phone:**
  - it is the full width and clearly changes when ticked;
  - the hint line reads well;
  - the saved line says "marked back in service" on a breakdown and "marked
    fixed" on a defect.
- **A stale page.** Open the same ticket in two tabs, acknowledge it in one,
  then try *Acknowledge* in the other. The message shows, the page behind
  refreshes to *acknowledged*, and the dialog stays open until *Cancel*.
- **The Yes / No confirms on the ticket page and in labour** are comfortable
  to tap with a thumb.
- **An operator on a fresh defect** sees no Times card. After a *Machine
  stopped* the card appears.

## Checked and found consistent

- **Core and shell boundary:**
  - `latest_restoration` and `RAISE_SCREEN_LABELS` are pure, with no DB and
    no clock, and live in `tickets_core.py`;
  - the shell only fetches the rows and picks the label set.
- **The prefix choice.** Choosing the label set from the field-name prefix
  is a stated decision. It avoids threading a parameter through
  `_apply_move` and the move steps. It is sound because only the raise path
  passes the `restore.` prefix (`RESTORE_FIELD_PREFIX`).
- **`_check_repeat`'s order:**
  1. unknown → `REPEAT_UNKNOWN`;
  2. another machine;
  3. not restored, sent back or not a fault → `REPEAT_NOT_RESTORED`;
  4. outside the window → `REPEAT_NOT_RECENT`.

  The earlier ticket is still read plain, as § 5.5 says, and the extra
  `_event_rows` read is a few rows. The never-restored and not-a-fault tests
  still pass with the new message.
- **SQL and security:**
  - no new SQL built from strings;
  - no new route and no permission change;
  - the actor still comes from `actor()`.
- **The edit save rule.** A no-op edit (`test_no_change_writes_no_line`)
  still writes neither the row nor a line.
- **The re-sync branch in `StartedAtFields`.** It covers a reopen where
  `occurred_at` goes from a typed value back to null, which the r3 test
  confirms. Only the null-to-null case fails (CR4-01).
- **The reload on 409:**
  - it fires once per refused save, because the watcher runs on each new
    `error` object, so there is no loop;
  - a 400 with a field does not reload;
  - after the reload, `asksStart` and `choices` follow the fresh ticket.
- **No deprecated APIs and no swallowed exceptions** were added.
- **The DB-unavailable path (503)** is unchanged.
- **Scope.** Every change maps to a finding the user sent back, and the
  round's four "Decisions taken" cover the judgement calls. Nothing beyond
  them was built.
- **Track: full.** Nothing to check against the light criteria.
