```
Step: S051 — The time field shows the time, with a Now tick
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (the working tree has uncommitted step docs only — S040, S044, S045, S046 briefs and reports — no uncommitted code)

**Verdict: no `blocker` or `major` finding. Four `minor` findings and five nits. Light track: this is the only round; the brief meets every light criterion (no migration, no auth or locking, an existing shared component changed, 9 files, frontend only).**

Facts file read: `scratch/brief-facts-S051.md`. Every file, line and code name the brief cites exists where it says (the one "no such file", `support/tickets.js`, is the short form of `frontend/e2e/support/tickets.js`). U1 and U2 are taken as decided; nothing below reopens them.

## Findings

### BR1-01 — minor — "a cleared input ticks *Now* again" snaps the field away while the user edits it

**Problem.** § 1.3 says a cleared input means the server's clock *and ticks Now again*. In Chrome a `datetime-local` input reports its value as `""` whenever one segment is empty. A user who backspaces the hour to retype it (the common way to back-date on a phone keypad, S040 CR4-01 saw the same with the reading rows) therefore fires `input` with `""`. Under § 1.3 the field then ticks *Now*, goes read-only and jumps to the current time. The user loses the edit and must untick again. Today's code has the same seam (`EventFields.vue:37` sets `changing = false` when `time` becomes `null`, so the input vanishes back to "Now · Change"), but today the input is hidden, so it was barely noticed; with the input always shown the snap is in the user's face.

**Why it matters.** The supervisor typing several records at shift end is the main back-dating user (S018 § 1). A field that snaps away on Backspace is a trap on that flow.

**Options.**
- (a) **Recommended.** A cleared input stays unticked and editable; `time` is `null` (the server's clock, as today) and the hint is hidden. *Now* is ticked again only when the **parent** resets `time` to `null` (a dialog opened again, *Enter more readings*). The coder tells the two apart with a flag set in `onInput` and read by the `props.time` watch, or by comparing the emitted value with the prop.
- (b) Keep § 1.3 as drafted. Document that Backspace in a segment re-ticks *Now*.

### BR1-02 — minor — after unticking *Now*, the shown time is not the time that is saved; and decision 3's reason is misstated

**Problem.** § 1.3 and design decision 3: untick → the input freezes at the untick moment (say 14:32); if the user does not edit it, the save sends no time and the server stamps the save moment (say 14:40). The screen showed 14:32 and *Now* unticked; the record says 14:40. That is the gap this step exists to close ("the exact time of record is not visible").

Design decision 3 rejects sending the shown time because "a phone ahead of the server would be refused". The server allows `FUTURE_SKEW` = 5 minutes ahead (`tickets_core.py:52`, used by `validate_event_time` and `meters_core.reading_time_error`), so that refusal needs a phone more than 5 minutes fast. The real risk, recorded in S018 BR1-05 and § 5.1, is a **slow** phone: a time a few minutes *behind* the server lands before the last event ("Must be at or after *Acknowledged*, …") or behind another reading of the same meter, for a time nobody typed. The reason should say that.

**Why it matters.** The user approved U2 for *Now ticked*. The unticked-untouched case is the planner's choice (decision 3); the user should see the trade-off stated correctly before approving it.

**Options.**
- (a) **Recommended.** Keep decision 3 (server's clock until the user edits), with the correct reason (slow phone, S018 BR1-05). Make the untouched state honest: after unticking, the input keeps following the clock (the 30-second refresh) until the user's first `input` event or focus; from then it is the user's value. So what the user sees is always either the live clock (≈ the server's) or the typed time.
- (b) Keep decision 3 and the frozen value as drafted; correct the reason only. Accept that an unticked, untouched save records a later minute than shown.
- (c) Send the shown time as soon as *Now* is unticked. Simplest rule for the user ("what you see is saved") but brings back the slow-phone refusal S018 BR1-05 removed, on a time the user did not type. Not recommended.

### BR1-03 — minor — the 44 px tap target is asserted, not specified

**Problem.** Design decision 4 says the *Now* box "is a 44 px tap target". Bootstrap's `.form-check-input` is 1 em (about 16 px) with a label of normal line height; nothing in the brief makes it 44 px. The brief does not name the check box's `id` either; the label's `for` and the tests (`getByLabel("Now")` / `getByRole("checkbox", { name: "Now" })`) need it.

**Why it matters.** The coder would decide the layout rule alone, and the e2e check "fits on one line" does not test the target size.

**Options.**
- (a) **Recommended.** State it: a `form-check` wrapper with `min-height: 44px`, `d-flex align-items-center`, the label `for`-linked so the whole row (box + word) is the target, as `.enter-more` and `.show-idle` do in `ReadingsView.vue` (`min-height: 44px`); `id` = `` `${idPrefix}-now` ``; the e2e test asserts the label's bounding box height ≥ 44 as the S040 A1 test does for *Enter more readings* (`readings.spec.js:673`).
- (b) Make the read-only input itself a second way in: a tap on the read-only time unticks *Now* and focuses the input. One more rule; only if the user wants it.

### BR1-04 — minor — the "shows today's date and time" test needs a minute-boundary rule

**Problem.** § 5's first test asserts the input shows the current date and time. The browser runs in `Asia/Kolkata` (`playwright.config.js:30`), so `istLocal(0)` is the right expected value; but the page renders, then the test reads, and the minute can turn in between (the S045 #4 class of flake, which cost a step).

**Why it matters.** S045 just spent a step on flaky tests; a new one should not be written in.

**Options.**
- (a) **Recommended.** The brief says: the test accepts `istLocal(0)` or `istLocal(1)` (the minute before), computed after the page has rendered; or asserts the date part and the hour only.
- (b) Leave it to the coder.

## Nits

- **BR1-05** (nit) § 3 Docs: Plan.MD has "Now" only on lines 723 (S039) and 725 (S040); the S018 ticket section does not describe "Now · Change". Drop the "if it describes" clause and name the two lines.
- **BR1-06** (nit) § 3: `frontend/e2e/support/tickets.js:92`, the doc comment of `setEventTime` ("Now · Change" in a dialog), changes too; the brief lists only line 94.
- **BR1-07** (nit) § 3: cite the three `readings.spec.js` places by test name (the S040 A1 "full save" test, lines 669 and 683; the "emptying a refused row" test, line 756) rather than line number, since S050 adds tests to the same file and the numbers will move.
- **BR1-08** (nit) § 2: ISO 9001:2015 § 7.5.3 is right ("Control of documented information"; 7.5.3.1 b: documented information protected from loss of integrity) — drop "clause number to verify". One line on ISO 14224 fits better for the plant: its § 9 (data quality) treats the event time as a core data field whose quality comes from capture at the event; showing the time at entry serves that.
- **BR1-09** (nit) § 1.5: say what the locked field shows — the phone's time at the lock, not the saved (server) time, which the rows show on the next round ("Today 17:50 · …"). One sentence stops a coder "fixing" it.

## Checked and found consistent

- `EventFields.vue` props and events (`time`, `remark`, `withRemark`, `timeLabel`, `remarkRequired`, `remarkLabel`, `remarkHelp`, `timeError`, `remarkError`, `idPrefix`, `locked`): unchanged by the brief; the five mounting screens (`ReadingsView.vue:348`, `ReadingFormModal.vue:128`, `RaiseTicketView.vue:485`, `MoveDialog.vue:225`, `RegradeDialog.vue:103`) need no code change. `MoveDialog` and `RegradeDialog` key the component on `opens`, so each opening remounts it: the interval is cleared in `onBeforeUnmount` and made anew. `ReadingsView` keeps it mounted and resets `takenAt` to `null` on *Enter more readings* (test at `readings.spec.js:683`), which re-ticks *Now* through the `props.time` watch.
- The four comment headers ("Now · Change") are at the lines the brief cites. `StartedAtFields.vue` (start date + time, no *Now*) is rightly untouched.
- Every e2e use of *Change* is covered: `support/tickets.js:94`, `tickets-raise.spec.js:155`, `readings.spec.js:669/683/756`; `tickets-work.spec.js` and `readings.spec.js` call the helper only. Playwright's `fill()` refuses a read-only input, so the helper must untick first, as the brief says.
- Independence from S050: S051 changes `EventFields.vue` and test lines inside S040 A1 tests; S050 moves the sheet to `ReadingsSheet.vue` "unchanged", `EventFields` line included, and `ReadingsView.vue` has no "Now · Change" comment. Neither layout matters; § 6.3's "one after the other" (both add to `readings.spec.js`) is right.
- U2 holds throughout: `time` is `null` with *Now* ticked; the shown time is `toLocalInputValue(new Date())`, the phone's clock; the hint shows only when unticked.
- Tests section: automated vs device split is right; the iPhone read-only check is a true device check (WebKit's picker on a read-only input), marked not important, with its place (phone-webkit before a release). The full suite once at the end matches README § Manual checks (`e2e/support/` changes).
- Scope B: the only UI text is the user's own label *Now* (quoted, exempt); no new messages.
- Standards: EN 13306 event times and ISO 17359 reading times keep their meaning; the brief claims no departure.
