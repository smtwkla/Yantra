# S051 — Implementation report

Date: 25-10-2026. Coder: Sonnet. Track: light. Frontend only; no backend, migration or permission change.

## 1. What was built

The shared time field (`EventFields.vue`) always shows a date and time. A check box **Now** sits to its right. It serves the readings sheet, *Log reading*, *Raise ticket*'s *Already fixed*, every ticket move dialog and the re-grade dialog.

## 2. How it works

- **Now ticked** (the default): the input is read-only and shows the phone's time to the minute. A 30-second timer moves it on. `time` stays `null`, so the server's clock decides.
- **Unticked:** the input is editable. Until the first edit it keeps following the clock and sends nothing. From the first edit on, the clock stops and the typed value is sent.
- **Cleared input** (Chrome reports "" while one part of the date is retyped): stays unticked and editable, and sends `null`. A parent reset of `time` to `null` ticks Now again. The component remembers its last emitted value, so its own `null` is not read as a reset.
- **Tick again:** read-only, current time, `time` back to `null`.
- **Locked:** the check box is disabled and the input read-only. The clock stops at the time of the lock.
- The "x days ago" hint shows only with Now unticked.
- The tap area is the label itself (`.now-tick`, `min-height: 44px`; round 1), with the check box inside it, id `${idPrefix}-now`.

## 3. Files touched (12: 9 code and test files, 3 docs; see Round 1 for the later changes)

- `frontend/src/views/tickets/EventFields.vue` — new layout, states, timer cleared in `onBeforeUnmount`, header comment, scoped style.
- `frontend/src/views/equipment/ReadingFormModal.vue`, `frontend/src/views/RaiseTicketView.vue`, `frontend/src/views/tickets/MoveDialog.vue`, `frontend/src/views/tickets/RegradeDialog.vue` — comment headers only.
- `frontend/e2e/support/tickets.js` — `setEventTime` unticks Now.
- `frontend/e2e/tickets-raise.spec.js` — unticks `#raise-restore-now`.
- `frontend/e2e/readings.spec.js` — the two S040 A1 tests assert the Now box (disabled when locked; enabled and ticked after *Enter more readings*; enabled when not locked); three new S051 tests.
- `frontend/e2e/tickets-work.spec.js` — one new S051 test.
- Docs: see below.

## 4. Decisions taken

- A `lastEmitted` value in the component tells the component's own `null` (cleared input) from a parent reset. Without it, a cleared input would tick Now again (BR1-01).
- One `shown` value serves both the clock and the typed text. No helper moved, so no vitest test.
- `setEventTime` untick uses `uncheck()`, which is safe when Now is already unticked.
- Not departing from the brief.

## 5. Not done, deferred or assumed

- Red-then-green: the new tests assert a check box that the old field did not have, so they fail on the old code by construction. I did not restore the old code to show the failure.
- With the sheet locked and Now unticked and untouched, the field shows the time at the lock (same rule as ticked).
- The shown time is the phone's clock; the saved one is the server's (U2).

## 6. Tests

- Targeted e2e at Normal: `readings`, `tickets-raise`, `tickets-work`, `screens`: 91 passed, 1 skipped.
- Whole e2e suite at Normal (once, `support/tickets.js` is shared): 187 passed, 4 skipped.
- `tooling/run-tests.bat` (`YANTRA_TEST_RUN=s051c1`): backend 3012, frontend 170, deps 42, tooling 168, all passed.
- `npx vite build`: built.

## Docs updated

- `docs/Plan.MD` — a note on the S039 line (about 723) and the S040 line (about 725).
- `docs/steps/device-checks.md` — row 34 (S051, iPhone).
- `docs/steps/README.md` — S051 row set to *In code review*.
- None for `schema.md`, `CLAUDE.md`, secrets or Keycloak, because nothing in them changed.

## Manual checks

- [auto] Log reading opens with Now ticked, input read-only showing the time; unticking makes it editable; ticking again read-only — `readings.spec.js::S051: Log reading opens with Now ticked and the time read-only; unticking makes it editable, ticking again read-only`
- [auto] After a full save on the readings sheet, the Now box is disabled and the time read-only — `readings.spec.js::S040 A1: a full save makes the round read-only, and Enter more readings starts a fresh one`
- [auto] Emptying the time to retype it keeps the field unticked and editable — `readings.spec.js::S051: emptying the time to retype it keeps the field unticked and editable (BR1-01)`
- [auto] A move dialog shows the time with Now ticked; a back-dated time is saved and shows on the timeline — `tickets-work.spec.js::S051: a move dialog shows the time with Now ticked; a back-dated time typed after unticking is saved`
- [auto] The time field and the Now box fit on one line; the Now label is a 44 px tap target (`@device`) — `readings.spec.js::S051: the time field and the Now box fit on one line, and the Now label is a 44 px tap target`
- [auto] Existing tests that clicked *Change* pass with the new helper — `tickets-raise.spec.js::S018 A1: Already fixed with a start time; the fields fit and the ticket is back in service`
- On an iPhone, the read-only time looks greyed and no picker opens (device-checks row 34; also covered by the release's Full run).

## Fix rounds

### Round 1 (code review r1)

Test run name `s051c2`. Targeted e2e at Normal (`readings`, `tickets-raise`, `tickets-work`, `screens`): 94 passed, 1 skipped. No whole-suite run: no shared frontend file changed. `tooling/run-tests.bat`: backend 3012, frontend 170, deps 42, tooling 168, all passed. `npx vite build`: built.

- **CR1-01 Fixed.** `ReadingFormModal` keys `EventFields` on an `opens` counter (raised in `open()`), `ReadingsView` on a `rounds` counter (raised in `enterMore()`), `RaiseTicketView` on `restoreFieldKey` (raised in `resetForm()`), as `MoveDialog` does. Every opening, round or new form starts with Now ticked and the time of now, also when `time` was already `null`. `EventFields` also refreshes the shown time on unlock (the `locked` watch now runs on both changes while the field is unedited). Two new tests in `readings.spec.js`: *Log reading opens again with Now ticked* (untick, type, clear, cancel, open another meter) and *Enter more readings starts the next round with Now ticked*. Fails without the fix: `toBeChecked` got unchecked in both; passes with it. Raise ticket has no new test: its form is reached again only through *Change*, which already unmounts it, so a direct test cannot tell the key from the old code; the key covers a node change that keeps the page mounted.
- **CR1-02 Fixed.** The label is now the 44 px target (`label.now-tick`, flex, `min-height: 44px`, side padding) with the check box inside. The layout test measures `label[for=reading-now]` and taps its top edge, which must toggle the box. Fails without the fix: the label was about 24 px high; passes with it.
- **CR1-03 Rejected.** The dialogs of the new tests already pass `expectDialogFits`: `openLog` (`readings.spec.js`) and `openAction` (`support/tickets.js`) call it on opening. The sheet tests open no dialog.
- **CR1-04 Fixed.** New test *untouched and unticked, the time follows the clock and the save sends no taken_at* (`page.clock` moves 60 s; the shown time changes, the input stays editable; the request body has no `taken_at`). It passes on the old code too, because it covers behaviour that was already right and untested; no red run applies.
- **CR1-05 Fixed.** The count in § 3 is now "12: 9 code and test files, 3 docs".
- **CR1-06 Fixed.** The S039 line of `docs/Plan.MD` now says only that *Time taken* shows the time with a *Now* tick and points to the S040 line, which holds the description.

### Files touched in round 1

`frontend/src/views/tickets/EventFields.vue`, `frontend/src/views/equipment/ReadingFormModal.vue`, `frontend/src/views/ReadingsView.vue`, `frontend/src/views/RaiseTicketView.vue`, `frontend/e2e/readings.spec.js`, `docs/Plan.MD`, this report.

### Docs updated in round 1

`docs/Plan.MD` (CR1-06). Others: none, because nothing else they describe changed.

### Round 2 (code review r2, async)

- **CR2-01 (nit) — Fixed** by the orchestrator, 25-10-2026: the layout test's title and its Manual checks line now say "the Now label is a 44 px tap target" (the test measures `label[for=reading-now]` since CR1-02). Title only; no assertion changed, so no new run is needed.
