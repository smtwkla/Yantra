```
Step: S051 — The time field shows the time, with a Now tick
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026 (revised 25-10-2026: brief-review r1)
Track: light
Status: Gate B (CR r1: 2 minor, 4 nits — 5 fixed, CR1-03 rejected with reason, in fix round 1; verify review r2: 0 blocker, 0 major, 0 minor, 1 nit CR2-01 — fixed; snapshot refs/steps/S051) (approved 25-10-2026 by KLA)
Baseline: refs/steps/S047 39d9477 (staleness review s1, 25-10-2026: S047's tags and run levels; nothing in frontend/src changed)
```

# S051 — The time field shows the time, with a Now tick

**The need (KLA, 25-10-2026).** "If now is chosen, the exact time of record is not visible.
We have to still show the time of effective entry. Then a now checkbox '[ ] Now' to the
right. Enabling it must cause front end time to be set as readonly. This is a fix for another
step."

Today the shared time field (`EventFields.vue`, S018 § 1, BR3-09) shows only the word **Now**
and a *Change* link. The user cannot see which time will be recorded.

User answers (25-10-2026, before the draft):
- U1: every screen that uses the field gets the new form: the readings sheet (S040), *Log
  reading* (S039), *Raise ticket*'s *Already fixed* (S018 A1), every ticket move dialog and
  the re-grade dialog (S018).
- U2: with *Now* ticked, the server's clock still decides the saved time (S018 § 5.1, S039):
  no time is sent. The shown time is the phone's clock.

## 1. What will be built

1. **The field always shows a date and time.** It is the `datetime-local` input, labelled as
   today (*Time taken*, *When*, *Back in service at*, *Breakdown from*). To its right, a check
   box **Now** (`form-check`, id `${idPrefix}-now`, its label linked with `for`), with a tap
   area of at least 44 px high on a phone (`min-height: 44px` on the check's wrapper, the S040
   rule for floor screens; BR1-03).
2. **Now ticked** (the default whenever the field opens, as *Now* is today):
   - the input is read-only (the `readonly` attribute, Bootstrap's read-only look) and shows
     the phone's current time to the minute;
   - the shown time moves on by itself: it is refreshed every 30 seconds, so it is never more
     than one minute behind;
   - nothing is sent: `time` stays `null`, and the server's clock decides (U2).
3. **Untick Now:** the input becomes editable.
   - Until the user's first edit, the input **keeps following the clock** (the same 30-second
     refresh) and nothing is sent: an untouched save records the server's time, and the field
     shows that time, not a frozen one (BR1-02).
   - From the first edit on, the clock stops, and the field sends what the user typed (as
     after *Change* today, S018 § 5.1).
   - A cleared input (for example while the user deletes the hour to retype it; Chrome then
     reports an empty value) **stays unticked and editable**, and sends nothing, which means
     the server's clock, as today (BR1-01). *Now* is ticked again only by the user, or when
     the screen resets the field (`time` set back to `null`, as a dialog's reopening does).
4. **Tick Now again:** the input returns to read-only, shows the current time, and `time`
   goes back to `null`.
5. **Locked** (the readings sheet after a full save, S040 A1): the check box is disabled and
   the input read-only. With *Now* ticked, the clock stops at the time of the lock: the field
   shows the phone's time at that moment, not the saved time of each row (each row shows its
   own saved time, S040).
6. The "x days ago" hint (`daysAgoHint`) and the refusal under the field (`timeError`) stay as
   today; the hint shows only when *Now* is unticked.

### Out of scope

- Sending the phone's time with *Now* ticked (U2: rejected).
- Showing the server's time before saving (a request per minute for no gain).
- Any change to the back-dating rules (S028, S039) or to the remark half of the field.
- The saved messages: they already show the saved time where they show one.

## 2. Standards and practice

- **ISO 9001 § 7.5.3 (control of documented information):** records are kept so that they
  are correct and fit for use. A record's time that the person sees at entry is checked at
  entry; a hidden one is not. The field now shows it.
- **ISO 14224 § 9 (data quality):** maintenance data is only as good as its collection; the
  standard asks for checks at the point of entry. Showing the time to be recorded is such a
  check for event and reading times.
- **EN 13306 event times** (breakdown start, back in service) and the meter reading's time
  (ISO 17359 trending) keep their meaning; only how the entry screen shows them changes.

## 3. Where

- `frontend/src/views/tickets/EventFields.vue` — the new layout and states (§ 1); the
  30-second refresh with `setInterval`, cleared in `onBeforeUnmount`; its comment header.
  Props and events are unchanged (`time`, `locked`, `timeLabel`, `timeError`, `idPrefix`, …),
  so the five screens need no code change. (*MoveDialog* and *RegradeDialog* remount the field
  on every opening through `:key="opens"`, so each opens ticked.)
- Comment headers that describe "Now · Change": `ReadingFormModal.vue` (line 9),
  `RaiseTicketView.vue` (line 21), `MoveDialog.vue` (line 7), `RegradeDialog.vue` (line 5).
- `frontend/e2e/support/tickets.js` — `setEventTime` (its doc comment at line 92 and the
  *Change* click at line 94): untick *Now* instead.
- `frontend/e2e/tickets-raise.spec.js` (line 155) — the same.
- `frontend/e2e/readings.spec.js` — two S040 A1 tests (three assertions: lines 669, 683,
  756; BS1-03) assert the *Change* button; they
  assert the *Now* check box instead: "S040 A1: a full save makes the round read-only, and
  Enter more readings starts a fresh one" (disabled when locked, ticked and enabled after
  *Enter more readings*), and "S040 A1: emptying a refused row to retype it does not lock the
  round (CR4-01)" (enabled when not locked). Cited by test name, because S050 adds tests to
  the same file. New `S051:` tests (§ 5).
- **Docs (housekeeping, by the coder):** `docs/Plan.MD` § 4.5, the S039 line 723 ("Now" is
  the server's clock) and the S040 line 725 ("Now" sends no time): a note that the field shows
  the time with a *Now* tick (S051). The S018 ticket section names no "Now · Change": no
  change there.

About 9 files, frontend only. No backend change, no migration, no permission.

## 4. Design decisions

1. **One shared field changes, every screen follows** (U1). Rejected: a mode switch for the
   readings screens only — two behaviours for one control (scope B: same word, same control).
2. **The server's clock still decides with Now ticked** (U2). The shown time can differ from
   the saved one by the phone's clock error (usually under a minute). Rejected: sending the
   phone's time — a slow phone would record a time earlier than it is, and could land before
   the ticket's last event, so the save is refused for a time nobody typed (S018 BR1-05). (A
   fast phone is allowed up to 5 minutes ahead, `FUTURE_SKEW` in `tickets_core.py`.)
3. **Unticked and untouched still means the server's clock**, and the input keeps following
   the clock until the first edit, so the shown time matches what is saved (BR1-02).
   Rejected: sending the shown time as soon as *Now* is unticked — the same slow-phone risk
   as decision 2, for a time the user did not type; and a frozen start time — it would
   differ from the saved time by however long the user waits.
4. **A cleared input does not tick Now again** (BR1-01). Chrome reports an empty value while
   one part of the date is deleted, so auto-ticking would make the field read-only in the
   middle of retyping the hour.
5. **A check box, not a toggle switch or a link**, as the user asked ("[ ] Now"). Its label
   is *Now*.

## 5. Tests and acceptance

Automated (e2e, targeted: `readings.spec.js`, `tickets-raise.spec.js`, `tickets-work.spec.js`,
plus `screens.spec.js`, at the Normal level as often as needed; the whole suite at Normal once
when the coding is done; never the Full level, which only the release runs — BS1-01):
- **important** — S051: *Log reading* opens with *Now* ticked and the input read-only,
  showing the current date and time (the test accepts `istLocal(0)` or `istLocal(1)`, so a
  minute boundary during the test does not fail it; BR1-04); unticking makes it editable;
  ticking again makes it read-only.
- **important** — S051: on the readings sheet after a full save, the *Now* check box is
  disabled and the time is read-only (in the S040 A1 tests named in § 3).
- S051: deleting the hour in the unticked input and typing it again keeps the field editable
  and unticked (BR1-01).
- S051: a ticket move dialog (*Acknowledge*) shows a time with *Now* ticked; a back-dated
  time typed after unticking is saved and shows on the timeline (`setEventTime` in
  `support/tickets.js`).
- S051: the time field and the *Now* box fit on one line inside the dialog
  (`expectDialogFits`), and the *Now* box's tap area is at least 44 px high (bounding box, as
  the S040 A1 test checks *Enter more readings*; BR1-03). This is a layout test: tagged
  `@device` (S047 § 1.3), titled as a layout check ("… fit on one line …"), so at Normal it
  runs on `phone-chromium` and `desktop-chromium` (the 44 px rule has no media query, so it
  holds on both; BS1-02). The other four S051 tests are untagged logic tests.
- The existing tests that clicked *Change* pass with the new helper.

Unit (vitest): none expected; if the coder moves the "shown time" logic to a helper, it gets
a test in `frontend/tests/ticketLabels.test.js`.

On a real device (not important): the iPhone's `datetime-local` input shows read-only
correctly (WebKit greys it, no picker opens). Checked by the release's Full run
(`tooling/release-tests.bat`, `phone-webkit`; BS1-04).

## 6. Open questions and assumptions

1. **Refresh interval:** 30 seconds assumed. The phone's clock is shown, so this costs nothing.
2. **Read-only look:** Bootstrap's read-only input (`readonly` attribute). Assumed
   acceptable.
3. **Order with S050:** S050 moves the sheet's code to `ReadingsSheet.vue`; S051 does not
   change that file's code, only `EventFields.vue`. Both add tests to `readings.spec.js`, so
   they are coded one after the other, not in parallel.

## 7. Amendments

None.

## Review log

### U1–U2 — before the draft, 25-10-2026

Recorded above: every screen with the field; the server's clock decides with *Now* ticked.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor — a cleared input ticks Now mid-retype | Accepted: a cleared input stays unticked and editable; Now re-ticks only by the user or a reset; § 1.3, decision 4, a § 5 test. |
| BR1-02 minor — unticked, the frozen time differs from the saved one; decision 3's reason misstated | Accepted: the input follows the clock until the first edit; decisions 2 and 3 give the slow-phone reason (S018 BR1-05) and the 5-minute `FUTURE_SKEW`. Shown to the user at gate A as a judgement call. |
| BR1-03 minor — 44 px asserted, not specified | Accepted: `form-check`, `min-height: 44px`, id `${idPrefix}-now`, label `for`; e2e bounding-box check; § 1.1, § 5. |
| BR1-04 minor — minute-boundary flake | Accepted: the test accepts `istLocal(0)` or `istLocal(1)`; § 5. |
| Nits (5) | All accepted: Plan.MD lines 723 and 725 only, no S018 change; `support/tickets.js` line 92 doc comment; `readings.spec.js` cited by test name; ISO 9001 § 7.5.3 without "to verify", plus ISO 14224 § 9; the locked field shows the phone's time at the lock. |

### U3 — approval, 25-10-2026

KLA approved the brief as it stands after round 1, with BR1-02 as recommended: after
unticking *Now*, the input keeps following the clock until the user's first edit. Open
questions as proposed. Coded in another session (KLA: "code will be elsewhere").

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BS1-01 minor — "the full suite once" now means Full | Accepted: targeted Normal runs, the whole suite at Normal once at the end, never Full (§ 5) |
| BS1-02 minor — the layout test's tag | Accepted, as recommended: `@device`, titled as a layout check, no "on a phone (Pixel 7)"; the other four tests untagged (§ 5) |
| BS1-03, BS1-04 nits | Accepted: two tests, three assertions (§ 3); the iPhone check in the release's Full run (§ 5) |

### U4 — coding moved to this session, 25-10-2026

KLA: "S051 and S052 are approved. queue their coding when it's ready" — S051 is coded in the
orchestrating session after S047, not elsewhere (replaces the last line of U3).
