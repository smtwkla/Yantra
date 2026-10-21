```
Step: S018 — Work the ticket
Doc: code-review r5
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S018 — Code review, round 5 (fix round 3: CR4-01…04)

**Verdict: no `blocker` and no `major` is open.** CR4-01…CR4-04 are all
fixed. This round raises two `nit`s, both on the edges of the CR4-03 change
in `TicketDetailView`. The § 5.1 `ORDERED_EVENTS` question is answered (kept
as built) and is not reopened.

Scope, kept short as asked: `3-impl-report.md` § *Fix rounds › Round 3* and
the three files changed since r4 (by file time: `TicketDetailView.vue`,
`RaiseTicketView.vue`, `tickets/MoveDialog.vue`). This matches what the
round describes. No backend file changed.

## Test run

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: **1823 passed** (144 s).
  - Frontend (vitest): **93 passed** in 12 files.
  - Dependency-audit tests: **42 passed**.
- `npx vite build` in `frontend/`: built. The only warning is the existing
  chunk-size one.
- **Scratch mount check.** It lives in the session scratchpad under
  `mount-r3/`; nothing was added to the repo. **25 of 25 pass** in 5 files:
  - the four earlier files (`a1`, `dialogs`, `fix`, `r4`), 22 cases. This
    includes the r4 case that failed before: `MoveDialog` *back in service*
    opened at 23:50 and again at 00:10. It now passes (CR4-01);
  - new `r5.test.js` mounts the real `TicketDetailView` with a stubbed API:
    1. **409, then a failing reload (503).** The ticket header stays, the
       open `MoveDialog` stays mounted and still shows its own 409 line, and
       the page alert shows the load error with *Retry*. *Retry* with a
       working GET clears the alert. The ticket and the dialog stay. No Vue
       error or warning.
    2. **Route change 7 → 8, and 8's GET fails.** Ticket 7 is dropped, and
       only the error and *Retry* show (no "Loading…" left over). While 8's
       GET was still pending, though, the page showed ticket 7's header
       (CR5-02).
    3. **409, then a 404 on the reload.** "Ticket not found" shows and the
       dialogs unmount. Afterwards `body` still has `modal-open`,
       `overflow: hidden` and one `.modal-backdrop` (CR5-01).

## Findings

### CR5-01 — nit — A 404 or 403 on the 409 reload still leaves the page scroll-locked

**Where:**
- `frontend/src/views/TicketDetailView.vue:119-120` (the 404 and 403
  branches of `load()`'s `catch`)
- `frontend/src/components/FormModal.vue:92-95` (`onBeforeUnmount`:
  `dispose()` without `hide()`)

**Problem.** CR4-03 was fixed with the first of r4's two suggestions: keep
the ticket on a failed reload. That covers a dropped link and a 503. On a
404 or 403, `load()` still sets `ticket` to null by design. The ticket block
then unmounts the dialogs while a modal is shown. `dispose()` does not undo
Bootstrap's body state. Scratch case 3 shows `modal-open`, `overflow:
hidden` and a backdrop left on `body`. The backdrop may be a jsdom
transition effect; the body class and the overflow are not.

**Failure scenario.**
1. A supervisor's *Start* gets 409 because, in the same minute, an admin
   took his unit away or moved the machine to another site.
2. The reload gets 403 or 404.
3. The page shows "You can't see this ticket" or "Ticket not found", and
   the dialog is gone.
4. He taps *Back to the list*. The SPA keeps the same `body`, so the list
   does not scroll until a full reload.

This is rarer than CR4-03 was: it needs a 409 and a loss of access
together.

**Suggested fix.** Use r4's second option in `FormModal`: in
`onBeforeUnmount`, if the modal is shown, take off `modal-open` and the
inline body style (or call `hide()` without the transition) before
`dispose()`. That covers every parent, not only this page. The rarity also
makes "leave as is" a fair call for the user.

### CR5-02 — nit — On a route change, the old ticket stays on screen and live while the new one loads

**Where:** `frontend/src/views/TicketDetailView.vue:102-113` and `:152`,
`:163`

**Problem.** The round's decision says "one ticket's data never sits under
another's URL". That holds when the new GET fails (line 122). While the GET
is still pending, `load()` keeps `ticket` as it is. Because of
`v-if="loading && !ticket"`, the page shows no "Loading…": it shows the old
ticket, with its action buttons, under the new URL. The *Repeat of* and
*Came back as* links are the normal way to get there. Scratch case 2 shows
ticket 7's header while ticket 8 loads.

This was not introduced by this round; the keep-while-loading behaviour was
there before. The round's comment and decision now claim more than the code
does, though.

**Failure scenario.** On a slow link an engineer taps *Came back as
TK-…-042* on ticket 041. For a few seconds the URL says 042, but 041 is
shown. He taps *Start*, and 041 is started. Then 042's data replaces it,
and he believes he started 042. A move on the wrong ticket stays in its
timeline.

**Suggested fix.** At the top of `load()`, drop a held ticket whose id
differs from the route id (`if (String(ticket.value?.id) !== String(id))
ticket.value = null;`). Then "Loading…" shows during the change, and the
id check in the `catch` (line 122) is no longer needed. A reload of the
same ticket keeps the page as now.

## Earlier rounds

| ID | Sev. | State | Checked |
|---|---|---|---|
| CR4-01 | nit | **Fixed** | `MoveDialog.vue:205` keys `<StartedAtFields>` on `opens`, as `EventFields` already is (`:178`). `opens` is incremented in `open()` before the seed, so each opening mounts it fresh and `followedDay` is the reseeded date. The r4 midnight case passes. |
| CR4-02 | nit | **Fixed** | `RaiseTicketView.vue:471`: `fa-regular fa-square` unticked, `fa-solid fa-square-check` ticked. |
| CR4-03 | nit | **Fixed** for a failed reload (scratch case 1). The load-error alert is its own `v-if` (`:158`), and the ticket block shows when `ticket && !notFound && !forbidden` (`:163`). The 404 and 403 corner is left; see CR5-01. |
| CR4-04 | nit | **Fixed** | No `restoreFieldsKey` is left anywhere in `frontend/src`. The raise screen's `EventFields` and `StartedAtFields` have no `:key`; they rely on the form remounting on a node change, as r4 found. |

## The round's two decisions

1. **The load-error alert as its own `v-if` above the ticket block.** This
   is sound. The `v-if`/`v-else-if` chain at `:152-157` stays exclusive:
   Loading, not found, forbidden. `load()` sets at most one of
   `notFound`, `forbidden` and `loadError`, and clears all three at its
   start, so two alerts never show together. "Loading…" never shows beside a
   kept ticket. On a first load that fails, the page shows only the alert
   and *Retry* (scratch case 2 covers the same path). While the ticket is
   kept, the dialogs stay mounted (case 1). The alert sits behind the open
   modal and is seen after the dialog is closed, which is what the round's
   manual check describes.
2. **Dropping the held ticket when its id differs from the route id.** This
   is right for a failed load. It does not cover the pending load before
   that; see CR5-02.

## Manual checks

The round's new check is in its text, not as a box in `## Manual checks`.
The brief does not mark it important, so this is not a finding. Still to
check in a browser:
- [ ] On a ticket page, cause a 409 on a move, then drop the network so the
  reload fails: the dialog stays, the error shows with *Retry*, and the page
  still scrolls after closing.
- [ ] *Back in service* opened before midnight, cancelled, and reopened
  after it, with a back-in-service time set to the evening before: the
  start date follows to that evening.
- [ ] The *Already fixed* toggle: an empty square unticked, a checked
  square ticked, both readable on the green outline and fill.

The brief's earlier manual checks (r4's list) are unchanged.

## Checked and found consistent

- `TicketDetailView.load()`:
  - `loadSeq` still guards every write, the `catch` included;
  - `loading` is cleared only by the latest call;
  - the `id === undefined` early return is kept.
- The 404 and 403 branches still clear the ticket. The forbidden text is
  still the page's own plain line, not the API's key-naming message.
- `pickersError` and `loadPickers` are unchanged; a kept ticket keeps its
  people and symptom lists.
- `MoveDialog`: the 409-then-`reload` watcher is unchanged; a 400 with a
  field still does not reload (scratch `fix.test.js`).
- `RaiseTicketView`: removing the key changed nothing else; the r3 A1 and
  r4 raise cases all pass.
- No backend change, so no new security or permission surface.
