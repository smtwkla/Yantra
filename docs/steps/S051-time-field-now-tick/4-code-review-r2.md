```
Step: S051 — The time field shows the time, with a Now tick
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. 0 minor, 1 nit.** Fix round 1 fixes CR1-01,
CR1-02, CR1-04, CR1-05 and CR1-06 as it says. The rejection of CR1-03 is sound. The fix round
brings in no new fault. One nit: the layout test's title still says the *Now box* is 44 px
high, but the test now measures the label.

Read from the snapshot `refs/steps/S051` (`ecbd1b7`), not the working tree. Re-read in full:
`frontend/src/views/tickets/EventFields.vue`. Re-read the fix round's hunks against
`refs/steps/S047`: `ReadingFormModal.vue`, `ReadingsView.vue`, `RaiseTicketView.vue`,
`frontend/e2e/readings.spec.js`, `docs/Plan.MD`, and the impl report's § 3 and § Fix rounds.
To judge CR1-03, read `openLog` (`readings.spec.js:40`), `openAction`
(`e2e/support/tickets.js:86`) and the S051 test in `tickets-work.spec.js`. The snapshot holds
the step as one commit, so the fix round's diff is read as the step's diff in those files.

## Tests

- **Unit suites, my run** (worktree of `refs/steps/S051`, `frontend/node_modules` linked by a
  junction, removed after): `YANTRA_TEST_RUN=s051cr2 tooling/run-tests.bat`: backend 3012
  passed (107 s), frontend 170 passed, deps 42 passed, tooling 168 passed; ALL SUITES: PASSED.
- **`npx vite build`** in the worktree's `frontend/`: built in 3.9 s, only the known chunk-size
  warning.
- **Browser tests:** not re-run. The coder ran the targeted specs at Normal: `readings`,
  `tickets-raise`, `tickets-work` and `screens`, 94 passed and 1 skipped. That is the right set
  for this fix round. It changed no shared frontend file, so no whole-suite run was due. None
  of my checks needs a browser run.
- **Red, then green:**
  - CR1-01: both new tests failed without the fix (`toBeChecked` got unchecked). This is
    plausible: before the fix, `time` was already `null` at the reset, so the old watch did
    nothing.
  - CR1-02: the label was about 24 px high without the fix.
  - CR1-04: the new test passes on the old code. The report gives the reason: it covers
    behaviour that was right but untested. That reason holds.
  - *Raise ticket* has no new test for its key. The report gives the reason: the form is
    reached again only through *Change*, which unmounts it already. That reason holds.

## Findings of round 1

| ID | Severity | Status | Check |
|---|---|---|---|
| CR1-01 | minor | Fixed | `EventFields` is keyed on `opens` (`ReadingFormModal.open()`), `rounds` (`ReadingsView.enterMore()`) and `restoreFieldKey` (`RaiseTicketView.resetForm()`). Each counter goes up after `time` is set back to `null`, so the new field mounts with `time` `null`, *Now* ticked and the time of now. `restoreFieldKey` is declared above the `immediate` node watch that first calls `resetForm()`, so no setup-order error. The `locked` watch now refreshes `shown` on unlock while unedited. |
| CR1-02 | minor | Fixed | `label.now-tick` holds the check box, is `d-flex`, `min-height: 44px`, side padding. The layout test measures `label[for=reading-now]` and taps its top-left corner, which unticks the box. |
| CR1-03 | nit | Rejected, sound | `openLog` and `openAction` call `expectDialogFits` on every opening. The new tests open their dialogs through these helpers. The sheet tests open no dialog. |
| CR1-04 | nit | Fixed | New test: `page.clock` moves 60 s, the shown time changes, the input stays editable, and the POST body has no `taken_at`. |
| CR1-05 | nit | Fixed | § 3 reads "12: 9 code and test files, 3 docs". |
| CR1-06 | nit | Fixed | The S039 line of `Plan.MD` now ends with a short pointer to the S040 line, which holds the description. |

## Nits

- **CR2-01** (nit) `frontend/e2e/readings.spec.js:870`: the title says "the Now box is 44 px
  high", but since CR1-02 the test measures the label around the box. Rename it to "the Now
  tap area is 44 px high", and change the matching line in the impl report's
  `## Manual checks`.

## Manual checks

The impl report's `## Manual checks` still carries every important check as `[auto]` with its
test. Still for the user, on a real device:

- [ ] Device-checks row 34: on an iPhone, the read-only time is greyed and no picker opens;
      unticked, the picker opens.
- [ ] With gloves, the *Now* tick is easy to hit on a phone (the 44 px label from CR1-02).

## Checked and found consistent

- **Remount timing:** in all three screens the counter goes up in the same function that sets
  `time` to `null`. The new `EventFields` mounts at the next render, so `lastEmitted` starts at
  `null` and the old reset watch does not fire twice.
- **Sheet lock and the key:** after *Enter more readings*, the new field can mount while
  `roundDone` is still true, until `loadSheet` returns. It then mounts locked, showing now. The
  unlock refreshes `shown` again. Both paths end ticked and editable-on-untick.
- **`locked` watch on lock:** it now also sets `shown` to now when the field locks unedited.
  The time sent is still `null`, so the shown time matches the save time the server records.
  An edited time is kept.
- **Timers:** each remount clears the old interval in `onBeforeUnmount`, so the keys leave no
  timer behind.
- **What the screens send:** unchanged by the fix round. `taken_at`, the sheet's `taken_at`
  and `restore.occurred_at` are left out for *Now*.
- **Scope B text:** the fix round adds no screen text.
- **Docs pass:** `Plan.MD` (CR1-06) is the only doc the fix round changed, and it lists it. No
  other listed doc is due.
- **Track:** still frontend only; `light` holds.
