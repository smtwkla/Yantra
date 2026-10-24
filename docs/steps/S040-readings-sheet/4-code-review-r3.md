```
Step: S040 — End-of-day readings sheet
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 3 (async verify)

**Verdict: no `blocker` or `major` finding is open.** Fix round 2 fixes CR2-01, CR2-02 and CR2-03 as its report says. Each fix has a test with a red result. The fix round brings in no new finding.

Files re-read, from the snapshot `refs/steps/S040` (commit `156b29b`):
- `frontend/src/views/ReadingsView.vue`: the picker, the `pending` watch, `discardAndSwitch`, `saveAll`'s start, and the question bar.
- `frontend/src/utils/meterLabels.js`: `isToday` and the readings block.
- `frontend/tests/meterLabels.test.js`: the two `isToday` cases.
- `frontend/e2e/readings.spec.js`: the three picker tests (CR1-02, CR2-02).
- `frontend/src/components/FormModal.vue:173-177`, to compare the bar.
- `docs/Plan.MD` § 4.5, the S040 line.

The working tree has moved on (S045). I checked that the round-2 files in the working tree are the same as in the snapshot: `ReadingsView.vue`, `ReadingSheetRow.vue`, `meterLabels.js`, `meterLabels.test.js`, `readings.spec.js` and `backend/meters.py` are identical, apart from line endings. So my runs below test the round-2 code.

## Test results (this review, run name `s040cr3`)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | **PASSED**. Backend 2964 passed, frontend 168, deps 42, tooling 115. |
| `npx vite build` | **PASSED**, built in 4.34 s. Only the usual chunk-size warning. |
| `npx vitest run tests/meterLabels.test.js` with `TZ=UTC`, then with `TZ=America/New_York` | **PASSED**, 14 of 14 both times. This confirms CR2-03 outside IST. |
| E2E | **Not re-run.** Under the standing rule of 25-10-2026, I rely on the coder's run: `e2e/readings.spec.js` and `e2e/screens.spec.js` on desktop-chromium and phone-chromium, 67 passed, 1 skipped, 0 failed. Those are the right specs: the round changed only the *Readings* screen, `meterLabels.js` and their tests, and no shared frontend code. No finding of mine needs a browser run. |

**phone-webkit:** the coder's one phone-webkit run had 24 passed and 1 failed. The failure is the known `readings.spec.js:189` (S039 Yes / No, "Yes is off screen"). It comes from the host's display scale, as shown in round 2. Every S040 test passed there, the new CR2-02 test too. I do not count it as red for this step.

## Round-2 findings

| ID | Severity | Status | Checked |
|---|---|---|---|
| CR2-01 | minor | **Fixed** | `ReadingsView.vue:313-317`: *Keep editing* first as `btn-primary`, *Discard* second as `btn-outline-danger`. This is the same order, classes and words as FormModal's bar (`FormModal.vue:174-176`). The question ends "You cannot undo this." The CR1-02 test asserts the button order, both classes and the new text, and clicks *Keep editing*. The red result is given (old bar: the text check fails). |
| CR2-02 | nit | **Fixed** | The bar shows only while `wantedSite !== null && pending > 0`. `watch(pending)` clears `wantedSite` at 0, so typing again does not bring back the old question. The new test clears the input and checks that the question is gone and the sheet is still SMTW. The red result is given. |
| CR2-03 | nit | **Fixed** | `isToday` compares the API's IST date with `IST_DATE.format(now)` (`en-CA`, `Asia/Kolkata`, `YYYY-MM-DD`). Both callers (`ReadingsView.vue:94`, `ReadingSheetRow.vue:36`) pass `now` and get the new rule. The new vitest case (01:30 IST on 25-10 is still 24-10 in UTC) passes in my runs under UTC and New York. The red result under `TZ=UTC` is given. |

Earlier rounds: CR1-01 to CR1-09 are **Fixed** (round 2). CR1-10 (nit, design question) stays **Open, held for the user at gate B**.

## Findings

None.

## Checked and found consistent

- **The question and the save loop:** `saveAll` still clears `wantedSite` first, and the picker stays `disabled` while saving. The new `pending` watch cannot reopen the question during a save. After a save that leaves nothing pending, the watch would clear it anyway.
- **The `v-if` guard and the watch together** (round 2, Decision 2): the guard hides the bar in the same render, and the watch resets the state. Neither duplicates a rule kept elsewhere. Both are reported.
- **Screen text (scope B):** "Discard 1 typed reading? Switching site removes them. You cannot undo this." states the consequence. *Keep editing* and *Discard* are the app's existing words for the same choice. The safe button is the first one and the main one.
- **Layers:** `isToday` stays a pure helper in `meterLabels.js`. It takes `now` as an argument, so the tests do not depend on the clock or the machine's time zone.
- **Docs pass:** the round lists "None". That is right: `docs/Plan.MD` § 4.5 quotes only "Discard 3 typed readings?", which is still true, and names no buttons. No other doc in § Docs to keep current names the changed words. No migration, route or permission changed.
- **Manual checks:** the round's two `[auto]` rows name tests that exist and that passed in the coder's run. Row 33 of `docs/steps/device-checks.md` is still the open real-device check.
- **Impl report writing (scope A):** each answer leads with the status, then the change and the red-then-green result.
- **Track:** full. The round changes nothing that affects it.

## For the user's manual browser check

- Row 33 of `docs/steps/device-checks.md`, on an Android phone and an iPhone: the decimal keypad, the keyboard not hiding a row's message or *Save readings*, and *Yes* / *No* easy to hit with a thumb.
- On a phone: type a reading, pick another site, and check that *Keep editing* is the easy button to hit.
- On this PC: confirm the phone-webkit failure of `readings.spec.js:189` (display scale, see round 2) before the release's full run.
- CR1-10: the design question held for you at gate B.
