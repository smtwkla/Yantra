```
Step: S040 — End-of-day readings sheet
Doc: code-review r4
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 4 (amendment A1: Enter more readings after a save)

**Verdict: one `major` finding is open (CR4-01).** A1 is built as the brief asks, and every test run is green. But the lock of the round is computed from the typed values. So a user who empties a refused or undone row to type it again locks the whole round mid-edit.

Scope of this round: amendment A1 only, as the orchestrator set it. The base S040 passed r1 to r3 and is not re-reviewed. The A1 code is committed in `5731712`; I reviewed `git diff 8c26411 5731712` for these files:
- `frontend/src/views/ReadingsView.vue` (read in full: `roundDone`, `enterMore`, `loadSheet`, `saveAll`, `undo`, the picker, the save bar);
- `frontend/src/views/readings/ReadingSheetRow.vue` (read in full);
- `frontend/src/views/tickets/EventFields.vue` (read in full);
- `frontend/e2e/readings.spec.js` (the three A1 tests);
- `docs/Plan.MD` § 4.5 (the S040 "Built" bullet).

Commit `5731712` also holds S045's paused changes and step-doc status edits. They are not part of this review.

## Test results (this review, run name `s040cr4`)

| Run | Result |
|---|---|
| `tooling/run-frontend-tests.bat` | **PASSED**, 168 passed, 18 s. |
| `npx vite build` | **PASSED**, built in 4.33 s. Only the usual chunk-size warning. |
| Backend suite | Not run: A1 changed no backend file. |
| E2E, the coder's run | Relied on (standing rule of 25-10-2026): `readings.spec.js` and `screens.spec.js` on desktop-chromium and phone-chromium, 73 passed, 1 skipped (the bottom-bar test skips itself on desktop), 0 failed. These are the right specs for the *Readings* screen. |
| E2E, my run: the screens that use `EventFields.vue` | **PASSED**, 128 of 128, 0 skipped, 0 failed, in 100 s. Command: `tooling/run-e2e-tests.bat e2e/tickets-raise.spec.js e2e/tickets-work.spec.js e2e/tickets-parts.spec.js e2e/tickets-notes.spec.js e2e/equipment.spec.js --project=desktop-chromium --project=phone-chromium`. |

Why these specs: `EventFields.vue` is used by `RaiseTicketView.vue` (`tickets-raise`), `MoveDialog.vue` and `RegradeDialog.vue` on the ticket page (`tickets-work`, `tickets-parts`, `tickets-notes`), and `ReadingFormModal.vue` (*Log reading*, `equipment`). Chromium projects only, because S045's guard fails every WebKit run on this PC while the display scale is above 100 %. Per spec: tickets-raise 20, tickets-work 44, tickets-parts 12, tickets-notes 10, equipment 42. The new `locked` prop defaults to false, and no ticket or *Log reading* test changed.

## Findings

### CR4-01 (major) — emptying a refused or undone row locks the round while the user types

**Where:** `frontend/src/views/ReadingsView.vue:91` and `:94`, with `frontend/src/views/readings/ReadingSheetRow.vue:88` and `:93`.

**The problem.** `roundDone` is `!saving && pending === 0 && some row saved`. `pending` counts the rows that are filled and not saved, and it is recomputed on every keystroke, because the row input is `v-model="state.value"`. So the lock follows the typed text, not the end of a save. When the last unsaved value becomes empty, `roundDone` turns true at once. Every input then becomes `readonly`, *Time taken* locks, and the *Meter reset* tick hides.

**Failure scenario 1 (a refused row, brief A1 item 3).**
1. Round at *Time taken* 18:00. *Oil temperature* 40 saves. *Run hours* 900 is refused: "Lower than …".
2. On a phone, the supervisor taps *Run hours* and presses backspace three times to type 1100.
3. After the third backspace the field is empty, so `pending` is 0 and one row is saved. The round locks.
4. The next keystroke does nothing. *Save readings* now reads *Saved*, disabled. The red refusal text stays on a locked, empty row.
5. The only way on is *Enter more readings*, which resets *Time taken* to Now. A back-dated round must be set up again, and the supervisor does not see why the field stopped taking input.

**Failure scenario 2 (Undo, the report's Decision 2).** An engineer saves three rows and sees one is wrong. *Undo* opens the round (the value is kept, so `pending` is 1). The engineer backspaces the wrong value to type the right one. At the empty field the round locks again, as above. Decision 2 says Undo "is how a wrong round is corrected", and this breaks that path whenever more than one row was saved.

Typing over a selection does not trigger it, because one input event replaces the text. Backspace is the usual way on a phone keypad, so the floor will meet it.

**Suggested fix.** Lock the round on an event, not on the typed text. For example:
- keep a `roundSaved` ref; set it at the end of `saveAll` when no filled row is left unsaved and a row is saved; clear it in `undo` and in `loadSheet` (and so in `enterMore`); use it in place of the computed `roundDone`; or
- count a row that holds an error (`state.error`) as still open in `roundDone`, so a refused or *Not saved* row keeps the round open even when emptied. This alone does not cover scenario 2.

The first is simpler and covers both scenarios. Add an e2e test, red first: a partial save, then `rowInput(hours).fill("")`, then fill a new value and save; assert the row is editable after the clear and is *Saved* after the second save. Add a second test for Undo with two saved rows, then clear and retype.

## Nits

- **CR4-02** (nit) `frontend/e2e/readings.spec.js:654-740`: brief A1 item 4 (leaving or switching the site after a saved round asks nothing) has no test. Add one step to the first A1 test: pick another site after the save and assert no discard question shows. Only users with several sites see the picker, so it can use the existing multi-site helper.

## The docs pass

- `## Docs updated` of A1 names `docs/Plan.MD` § 4.5. The new sentence in the S040 "Built" bullet matches what was built: the round read-only (rows and *Time taken*), *Saved* disabled, *Enter more readings* with rows empty, time Now and last readings reloaded, and refused rows kept editable after a partial save.
- `.claude/CLAUDE.md` § Docs to keep current asks for nothing else. A1 has no migration, secret, role, port, dev command, plant fact or maintenance rule. It adds no real-device check of its own (but see the manual check below on the locked time field on an iPhone).

## S039 CR2-01 — already verified, still holds

S039's header asks S040's review to re-check S039 CR2-01 (`savedMessage` must not print "the limit of null"). S040's review r1 already verified it (`4-code-review-r1.md`, § "S039 CR2-01 — verified"). I checked it again against the committed code:
- `frontend/src/utils/meterLabels.js:89-100`: `savedMessage` returns "Saved. Above the limit." when `max_value` is null, and "Saved. Below the limit." when `min_value` is null.
- `frontend/tests/meterLabels.test.js:74-79`: the case "does not name a limit the meter does not have (CR2-01)" asserts both, and passes in this round's frontend run.

**Result: fixed.** The S039 header line can close it.

## Open findings of earlier rounds

| ID | Severity | Status |
|---|---|---|
| CR1-10 | — | Open for the user, as the brief's header says. Not part of A1. |

## Manual checks for the user

- On an iPhone, after a full save that used a changed *Time taken*: tap the locked time field and check that no date picker opens. iOS Safari has opened the picker on `readonly` date inputs in some versions. If it opens and a time is picked, `takenAt` changes on a locked round (`EventFields.vue:75-76`). It does no harm until the round is opened by *Undo*, which would then save with the new time.
- On a phone (360 px wide), after a full save: check that *Saved* and *Enter more readings* sit side by side in the save bar without crowding the "x of y filled" count, and that *Enter more readings* is easy to hit with a thumb.

## Checked and found consistent

- **Brief A1, item 1.** After a full save every row is read-only, empty ones too (`readOnly = saved || locked`): the input is `readonly`, the Yes / No buttons are disabled, the reset tick is hidden. *Time taken* hides *Change* and *Now*, and its input is `readonly`. The save button reads *Saved* and is disabled.
- **Brief A1, item 2.** *Enter more readings* is `btn-primary` with `min-height: 44px`, beside *Saved*, and disabled while the sheet loads. `enterMore()` sets `takenAt` to null (EventFields' watch puts it back to "Now"), clears the time error and reloads the sheet. `loadSheet` rebuilds every row state, so the old round's *Undo* and *Saved* marks go, and each row's last reading and read-today mark come from the server.
- **Brief A1, item 3.** A partial save leaves the refused rows filled and unsaved, so `pending > 0`: *Save readings* stays enabled and *Enter more readings* does not show. (CR4-01 covers what happens when such a row is emptied.)
- **Brief A1, item 4.** The discard question counts only `pending`, so a saved round with nothing typed switches site with no question. The page has no leave guard, so leaving asks nothing either.
- **Brief A1, item 5.** The third test sets *Time taken* back to the first round's minute, gets the server's `SAME_MINUTE` text on the row, and the other meter of the round saves.
- **`EventFields.vue`.** The `locked` prop is additive with default false. No ticket or *Log reading* caller passes it, and my run of the five specs that open those screens is green. The report lists this departure from the brief's *Where* as Decision 1, and it avoids a near-copy of the time field.
- **Decisions 2 to 5** are reported and match the code: Undo stays on a locked round and opens it; a failed reload shows the usual load error with *Try again*; the test moves the first round back 30 minutes to avoid the same-minute refusal at Now; a round saved at Now still reads "Now" while locked.
- **Layer and design.** A1 is presentational only. The rules stay on the server (S039's POST), and no business rule moved into a Vue file. No new helper repeats an existing one.
- **Screen text (scope B).** *Enter more readings* starts with a verb and names the result. *Saved* is the word the brief sets for the disabled button, and the rows already use it.
- **Tests.** The three A1 tests assert what the user sees: the read-only inputs, the hidden *Change*, the disabled *Saved*, the 44 px height, no sideways scroll, the empty editable rows after *Enter more readings*, the reloaded last reading "100.0 h", and the same-minute refusal text. The report gives the red result: 3 failed before the change (the button was not found), 3 passed after. No dialog is opened, so `expectDialogFits` does not apply.
- **The report.** The A1 section has what was built, how it works, the files, the decisions, what was not done, the tests with their counts, and the `[auto]` manual checks, each with its test. It is written in scope A.
