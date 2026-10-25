```
Step: S051 — The time field shows the time, with a Now tick
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

**Verdict: no blocker or major finding is open. 2 minor, 4 nits.** The step builds what the
approved brief asks for. `EventFields.vue` shows the date and time with a *Now* check box. Ticked,
the input is read-only, follows the clock and sends no time. Unticked, it follows the clock until
the first edit. A cleared input stays unticked (BR1-01). The field locks on the sheet. All five
screens still send `null` (no `taken_at` / `occurred_at`) for *Now*, as the backend expects. The
first minor finding is a reset case. The field ticks *Now* again only when `time` goes from a
value to `null`. So a screen that keeps the field mounted (*Log reading*, the readings sheet,
*Raise ticket*) can open a new round or dialog unticked, and even with an empty time.

Reviewed: `git diff -w --ignore-cr-at-eol refs/steps/S047 --` for the files the impl report
names. Read in full: `EventFields.vue`. Read the parts that use the field: `ReadingsView.vue`
(`enterMore`, `roundDone`, the save body), `ReadingFormModal.vue` (`open`, `save`, `blank`),
`RaiseTicketView.vue` (`resetForm`, the restore body), `MoveDialog.vue` / `RegradeDialog.vue`
(`:key="opens"`), and `FormModal.vue` (the slot is always mounted). Not this step's, so not
reviewed: the S047, S050 and S052 files and rows.

## Tests

- **Unit suites, my run:** `YANTRA_TEST_RUN=s051cr1 tooling/run-tests.bat`: backend 3012
  passed (99 s), frontend 170 passed, deps 42 passed, tooling 168 passed; ALL SUITES: PASSED.
- **`npx vite build`** in `frontend/`: built in 3.6 s, only the known chunk-size warning.
- **Browser tests:** not re-run (standing rule, 25-10-2026). The coder's runs are the right
  set: targeted Normal of `readings`, `tickets-raise`, `tickets-work` and `screens` (91 passed,
  1 skipped), and the whole suite at Normal once (187 passed, 4 skipped). The whole-suite run
  has its reason: `e2e/support/tickets.js` is shared. My findings come from reading the code.
  None needs a browser run to confirm it: the watch rule in `EventFields.vue:61` is plain.
- **Tags:** only the layout test has `@device`. Its title names the layout check and no device
  (S047 § 1.3, BS1-02). The other three new tests and the one in `tickets-work.spec.js` are
  untagged.
- **Red, then green:** the report says the new tests assert a check box the old field did not
  have, so they fail on the old code. That reason holds for a first round.

## Findings

### CR1-01 (minor) — a reset with `time` already `null` does not tick *Now* again

`frontend/src/views/tickets/EventFields.vue:61`

**Problem.** The field resets (ticks *Now*, clears `edited`, shows the clock) only when `time`
changes from a value to `null`. A screen that resets a field whose `time` is already `null`
changes nothing. `time` is `null` in two unticked states: unticked and untouched (BR1-02), and
cleared (BR1-01). Three screens keep the field mounted between openings or rounds:

- *Log reading*: `FormModal` always mounts its slot, and `open()` sets `taken_at` back to `null`.
- The readings sheet: `enterMore()` sets `takenAt` to `null` (`ReadingsView.vue:287`).
- *Raise ticket*: `resetForm()` sets `restoreAt` to `null` on every node change.

Only *MoveDialog* and *RegradeDialog* remount the field (`:key="opens"`). Brief § 1.2 says *Now*
is the default "whenever the field opens". § 1.3 says a reset ticks it again.

**Failure scenario.**
1. On *Log reading*, the operator unticks *Now*, types a time, deletes it, and closes the dialog.
2. He opens *Log reading* on the next meter.
3. The time field is empty, editable and unticked. The save records the server's time, but the
   screen shows no time. This is the problem S051 is meant to fix.

The same happens after *Enter more readings* on the sheet. A related case: after a long lock,
*Enter more readings* unlocks a ticked field, but the shown time stays at the time of the lock.
It moves on only at the next 30-second tick (`EventFields.vue:54`, `:73`).

**Fix.** Key the field per opening on the three screens, as *MoveDialog* does: an open counter in
`ReadingFormModal.open()`, a round counter in `enterMore()`, and the node change in
`RaiseTicketView`. Or give `EventFields` a `reset()` through `defineExpose`. Also refresh `shown`
in the `locked` watch when the field is unlocked and not edited. Add an e2e test: untick, type,
clear, close *Log reading*, and open it again. *Now* is ticked and the time shows.

### CR1-02 (minor) — the 44 px *Now* area is not tappable

`frontend/src/views/tickets/EventFields.vue:107`, `:116`, `:146`

**Problem.** `min-height: 44px` is on the wrapper `div`, but a tap on the wrapper does nothing.
Only the 16 px check box and the one-line label *Now* toggle the tick. The real tap target is
about 24 px high. The layout test measures the wrapper (`readings.spec.js:870`), so it passes
anyway. The brief asks for a tap area of at least 44 px (BR1-03, the S040 rule for floor
screens).

**Failure scenario.** An operator with gloves taps just above or below the word *Now*. The tap
lands on the wrapper, and *Now* stays ticked. He cannot type the time he read off the HMI, and
he taps again.

**Fix.** Make the label the 44 px target. For example, give the label `d-flex align-items-center`,
`min-height: 44px` and some horizontal padding, and put the check box inside it. Then measure the
label's box in the layout test, not the wrapper's.

## Nits

- **CR1-03** (nit) `frontend/e2e/tickets-work.spec.js:559`: the new test opens the *Acknowledge*
  dialog but does not call `expectDialogFits`; add it, as the flow-test rule asks. The same applies
  to the first two new tests in `readings.spec.js` (lines 836 and 856).
- **CR1-04** (nit) `frontend/e2e/readings.spec.js:836`: no test covers BR1-02 (unticked and
  untouched, the field follows the clock and the save sends no `taken_at`). Use `page.clock` to
  move 60 s and check the value, and check that the request body has no `taken_at`.
- **CR1-05** (nit) `docs/steps/S051-time-field-now-tick/3-impl-report.md` § 3: the heading says
  "Files touched (11)"; the list has 9 code and test files plus 3 docs. Give the true count, or
  drop the number.
- **CR1-06** (nit) `docs/Plan.MD:723`: the S039 line still says *Time taken* ("Now" is the
  server's clock) just before the new S051 note. Both are correct, but the note repeats it; one
  mention is enough.

## Manual checks

The impl report's `## Manual checks` carries both **important** checks as `[auto]`, each with a
test, and the other § 5 checks. The iPhone check (not important) is device-checks row 34 and is
part of the release's Full run. Still for the user, on a real device:

- [ ] Row 34: on an iPhone, the read-only time is greyed and no picker opens; unticked, the
      picker opens.
- [ ] After CR1-02: with gloves, the *Now* tick is easy to hit on a phone.

## Checked and found consistent

- **States against § 1:** ticked = `readonly`, `time` `null`, refreshed every 30 s
  (`CLOCK_REFRESH_MS`); untick emits nothing, so an untouched save sends no time; the first
  edit sets `edited` and stops the clock; ticking again emits `null` and shows the clock; the
  "x days ago" hint shows only when unticked.
- **`lastEmitted`:** it tells the field's own `null` (a cleared input) from a parent's reset.
  Typed → parent `null` resets; typed → cleared does not. Its only gap is CR1-01, where the
  parent's `null` meets a `null` that was already there.
- **Timer:** one `setInterval` per mount, cleared in `onBeforeUnmount`. *MoveDialog* and
  *RegradeDialog* remount on every opening, so no timer is left behind.
- **Locked:** check box `disabled`, input `readonly`, and the clock stops at the lock (the
  interval skips while `locked`). The S040 A1 tests assert the disabled box, then enabled and
  ticked after *Enter more readings*.
- **What the screens send:** `ReadingFormModal` and `ReadingsView` add `taken_at` only when
  set; `RaiseTicketView` adds `restore.occurred_at` only when set; *MoveDialog* and
  *RegradeDialog* are unchanged. The backend contract is unchanged; no backend file changed.
- **Ids and labels:** the time input keeps `${idPrefix}-time` with its label; the box is
  `${idPrefix}-now` with `for`; `#raise-restore-now` in `tickets-raise.spec.js` matches.
- **`setEventTime`:** `uncheck()` is safe when *Now* is already unticked; every caller still
  passes.
- **Layout:** the input and the box sit in one `d-flex` row; `flex: none` keeps the box from
  shrinking; the dialog body still scrolls (`modal-dialog-scrollable`, unchanged).
- **Writing style, scope B:** the only new screen text is the label *Now*, the word the brief
  and the user chose.
- **Docs pass:** `Plan.MD` notes on the S039 and S040 lines as the brief names; device-checks
  row 34 added; README row set to *In code review*. No migration, secret, role or `CLAUDE.md`
  point, so no other doc is due.
- **Track:** frontend only, no migration, permission or new dependency; `light` holds.
- **Scope:** nothing built beyond the brief. "Decisions taken" lists `lastEmitted`, the single
  `shown` value and the `uncheck()` helper; none departs from the brief.
