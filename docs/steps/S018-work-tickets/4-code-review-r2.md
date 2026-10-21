```
Step: S018 — Work the ticket
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S018 — Code review, round 2

**Verdict: no `blocker` and no `major` is open.** CR1-01 is fixed: all four
dialogs now mount and open. CR1-02 to CR1-08 (three `minor`, four `nit`) stay
open. They were deferred to the user at gate B on purpose, so they are not
counted as unanswered. This round finds nothing new.

Scope of this round:
- fix round 1 in `3-impl-report.md` (`### Round 1`);
- the code that changed since round 1.

By file time, only these four files changed after `4-code-review-r1.md` was
written: `MoveDialog.vue`, `RegradeDialog.vue`, `EditTicketDialog.vue` and
`LabourPanel.vue`, all in `frontend/src/views/tickets/`. No backend file, test
or composable changed. Two things are not reviewed here:
- Amendment A1 is approved but not coded yet.
- The § 5.1 `ORDERED_EVENTS` question still waits for the user. Round 1's note
  on it stands: if the filter were dropped, `EVENT_LABELS` would also need
  entries for `edited`, `assigned` and `unassigned`.

## Test run

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: 1801 passed (152 s).
  - Frontend (vitest): 92 passed in 12 files.
  - Dependency-audit tests: 42 passed.
- `npx vite build` in `frontend/`: built. The only warning is the existing
  chunk-size one (main chunk 530 kB).
- **Scratch mount check** (in the session scratchpad; nothing added to the
  repo). I mounted each dialog in jsdom with Vue's `createApp`, with `api.js`
  mocked and a Vue error handler that collects every error. Then:
  - `MoveDialog`: `open()` with each of *acknowledge*, *start*, *restore*,
    *send-back*, *close* and *not-a-fault*;
  - `RegradeDialog`: `open("stopped")` and `open("change")`;
  - `EditTicketDialog`: `open()`;
  - `LabourPanel`: *Add labour* clicked, then the row's *Change*;
  - `AssignDialog`: mounted.

  All 11 cases pass. None has a mount or render error, each renders the
  `.modal` with a title, and no rendered text contains "undefined".
- **Control.** I put a copy of `RegradeDialog` with the old
  `blank: (seed) => seed` in the scratchpad. Mounting it still gives a render
  error, so the check does catch the round 1 fault.

## Findings

None new in this round.

## Earlier rounds

### CR1-01 (blocker): verified fixed

Each of the four dialogs now passes a `blank` that returns the full default
shape, with the seed spread over it:

| File | Line | Defaults |
|---|---|---|
| `MoveDialog.vue` | 54 | `occurred_at: null, remark: ""` |
| `RegradeDialog.vue` | 30 | `intensity: "", occurred_at: null, remark: ""` |
| `EditTicketDialog.vue` | 30 | `component_id: "", failure_mode_id: "", description: ""` |
| `LabourPanel.vue` | 40 | `person_id: null, trade_id: "", work_date: "", hours: "", minutes: ""` |

Why the fix is sound:
- `useFormModal`'s `ref(blank())` at setup now gets an object, so the first
  render and `MoveDialog`'s `watch(() => form.value.occurred_at, …)` are safe.
- Each `open()` still passes a full seed. What the user sees and sends is
  unchanged from what round 1 reviewed.
- `LabourPanel`'s *Change* goes through `fromRecord` and is not affected.
- `useFormModal` is unchanged, and the fix follows the pattern of the repo's
  other dialogs (`AssignDialog`, the equipment dialogs). The report says this.
- The extra keys do not change where a refusal is shown. All four dialogs
  route errors through their own `SHOWN_FIELDS`, not `modalError`.

### Deferred to gate B by the user's call (open, not unaddressed)

| ID | Severity | Subject | State |
|---|---|---|---|
| CR1-02 | minor | `_check_repeat` does not check the earlier ticket's state | Open (deferred to gate B) |
| CR1-03 | minor | "Now · Change" keeps a stale draft across openings | Open (deferred to gate B) |
| CR1-04 | minor | `btn-sm` tap targets on the ticket page's floor controls | Open (deferred to gate B) |
| CR1-05 | nit | Two definitions of "latest restoration" | Open (deferred to gate B) |
| CR1-06 | nit | An edit to a same-label symptom is silently dropped | Open (deferred to gate B) |
| CR1-07 | nit | The Times card is always shown to operators | Open (deferred to gate B) |
| CR1-08 | nit | A 409 leaves the user to reload by hand | Open (deferred to gate B) |

I checked the current code: none of the seven was touched, so each still holds
as written in round 1.

Gate B note: CR1-03 sits in the same dialogs that the manual check below
exercises. If the user wants it fixed, it is best done before that check, so
the check need not be repeated.

## Manual checks

`3-impl-report.md` still has its `## Manual checks` section. It carries all
five important checks of § 8 as unticked boxes. Nothing is missing.

The user's **manual browser check**, now possible since CR1-01 is fixed:
- **Every dialog, once:**
  - acknowledge, start, back in service with and without the start time,
    send back (Yes / No), close, not a fault;
  - *Machine stopped* as an operator, *Change severity* as a technician;
  - Edit, Assign, Add / Change / Remove labour.

  For each, check that it opens, fills its defaults ("Recording as …", own
  name, today, the only trade, 5.1 on not a fault) and saves. jsdom showed that
  each one opens. Only a browser shows Bootstrap's modal, the layout and the
  save.
- **The five important checks of § 8.** Above all, on Android and on iPhone,
  check that *Close ticket* and *Cancel* stay on screen with the keyboard up.
  Also open one existing dialog (e.g. the equipment edit) to see that
  `modal-dialog-scrollable` did not change it.
- **The action-bar order** on a phone and on a wide screen.
- **The raise screen from *Not fixed — raise again*:** check the pre-fill, the
  "Repeat of …" line, and that Save links the two tickets.
- **CR1-03:** if it is fixed at gate B, open a move dialog twice; the second
  opening shows "Now".

## Checked and found consistent

- **Scope of fix round 1:** it changed only the four `blank` lines named in
  the report.
  - No backend, test or composable file changed after round 1.
  - Nothing beyond the fix was added.
  - The report's Round 1 lists every finding with an answer: one `Fixed` and
    seven `Deferred` to gate B.
- **The scratch verification** described in the report matches what I
  reproduced independently, including the control case.
- **One small redundancy, not a finding:** `MoveDialog.open()` still seeds
  `occurred_at: null, remark: ""`, which `blank` now defaults as well. It is
  harmless and keeps each `open()` explicit about what it resets.
- **Everything checked in round 1** still holds, since nothing else changed:
  - migration v13, RBAC and route gating, SQL, transactions and locks;
  - the pure core and the event-time rules;
  - documents, pickers, `/api/auth/me`, the list;
  - layering, DRY and UX.
- **Track: full.** Nothing to check against the light criteria.
