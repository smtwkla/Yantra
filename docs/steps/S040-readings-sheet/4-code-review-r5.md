```
Step: S040 — End-of-day readings sheet
Doc: code-review r5
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 5 (A1 fix round for CR r4)

**Verdict: no `blocker` or `major` finding is open.** CR4-01 and CR4-02 are fixed. One new `minor` finding (CR5-01) remains: the side effect that the report names leaves no way to start a new round in one path, against brief A1 item 3.

Scope: this round verifies the fix round only (round-2+ rule). I re-read these files:
- `frontend/src/views/ReadingsView.vue`: the script in full from `resetStates` to `undo` (lines 60–310), and the save bar in the template (lines 395–402);
- `frontend/e2e/readings.spec.js`: the three new tests (lines 740–804);
- `docs/steps/S040-readings-sheet/3-impl-report.md`: § "A1 fix round (CR r4)";
- `docs/steps/S040-readings-sheet/1-brief.md`: § 10 A1.

The diff is the working tree against `5731712` for those three files. The other uncommitted changes belong to S045 and to step docs, and are not in scope.

## Test results

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s040cr5 tooling/run-tests.bat` (my run) | **PASSED**: backend 2964 passed, frontend 168 passed, deps 42 passed, tooling 115 passed. |
| `npx vite build` | Relied on the coder's run: built in 4.30 s, usual chunk-size warning only. |
| E2E, the coder's run | Relied on (standing rule of 25-10-2026): `readings.spec.js` and `screens.spec.js`, all three projects, 79 passed, 0 failed, 41 skipped. The skips are phone-webkit (S045's display-scale guard on this PC) and the bottom-bar test that skips itself on desktop. These are the right specs: the fix changed only the *Readings* screen, and `EventFields.vue` is unchanged. |
| E2E, my run | Not run. My finding is about a path no test covers, and it needs no run to confirm it. |

## Verification of the r4 findings

### CR4-01 (major) — fixed

`roundDone` is now `ref(false)` (`ReadingsView.vue:96`). It is no longer computed from the typed text. I checked every write to it:

| Where | What it does | Correct? |
|---|---|---|
| `saveAll`, line 276 | After the `finally` (so `saving` is false), sets `roundDone` to `pending === 0 && some row saved`. A full save locks; a partial save, a network stop or a `taken_at` stop leaves it false. | Yes. |
| `undo`, line 298 | Sets false only after the DELETE succeeds. A failed Undo leaves the round as it was. | Yes. |
| `resetStates`, line 86 | Sets false. `resetStates` is called only from `loadSheet` on a successful load (line 144), so a site switch, *Enter more readings* and *Try again* all clear it. | Yes. |

No other code writes `roundDone`. Typing, clearing a row, or the `watch(pending)` that clears the discard question do not touch it. Both failure scenarios of r4 are gone:
- Scenario 1 (a refused row emptied by backspace): the round stays open, because only `saveAll` can lock it.
- Scenario 2 (Undo, then clear and retype): `undo` opens the round, and clearing the row does not close it again.

A failed sheet load (`loadError` or the 404 path) does not reset `roundDone`, but the sheet and its save bar are not shown then. The next successful load resets it. This is correct.

**Red results.** The report gives them: on the old code, `-g "S040 A1"` on desktop-chromium had 2 failed and 4 passed, and the two new CR4-01 tests were the failing ones. The coder read the failure message of the Undo test (`not.toHaveAttribute("readonly")` failed after `fill("")`). For the first test the coder read only the failure list, and says so. This meets the *Red, then green* rule.

**The tests assert what the user sees.** They check that the input is not `readonly` after `fill("")`, that *Change* stays visible, that the retyped value is in the field, that *Save readings* is enabled, and that the row then reads *Saved* and *Enter more readings* shows. `fill("")` gives one input event with an empty value, which is the state that locked the round before. No dialog opens, so `expectDialogFits` does not apply.

### CR4-02 (nit) — fixed

New test "S040 A1: switching the site after a saved round asks nothing" (`readings.spec.js:789`). The manager saves a row at SMTW, picks BRICKS, and the test asserts that the heading changes to BRICKS and that `discard-confirm` is not shown. This covers brief A1 item 4 for the site switch. The test is new coverage, not a fault fix, so no red result is needed.

## Findings

### CR5-01 (minor) — after a partial save, an emptied refused row leaves no way to start a new round

**Where:** `frontend/src/views/ReadingsView.vue:401` (the `v-if` of *Enter more readings*), with line 276. The report names the effect at `3-impl-report.md:286`.

**The problem.** *Enter more readings* shows only when `roundDone` is true, and `roundDone` is set only by a full save. Brief A1 item 3 says *Enter more readings* "shows only once nothing is left to retry". After a partial save, the user can leave nothing to retry by emptying the refused row. Then *Save readings* is disabled (nothing pending), and *Enter more readings* does not show. The saved rows stay read-only with their *Saved* mark. To read those meters again at another time, the user must leave the page and come back. That is the fault A1 was made to remove.

**Failure scenario.**
1. The supervisor saves the 18:00 round. *Oil temperature* saves. *Run hours* 900 is refused: "Lower than …".
2. The supervisor checks the meter and finds it is broken, so the reading is skipped. The supervisor clears *Run hours*.
3. *Save readings* is now disabled, and no *Enter more readings* shows.
4. At 20:00 the supervisor wants the next round. *Oil temperature* is still read-only with *Saved*. The only way on is to leave the *Readings* page and open it again.

**The report.** The report calls this a side effect "as the review accepts". Review r4 did not discuss this state. Its suggested fix leads to it, but the report states an acceptance that r4 does not give.

**Suggested fix.** Keep the lock as it is now, and show the button on a weaker condition. Show *Enter more readings* when `!saving && pending === 0` and a row is saved, whether or not `roundDone` is true. Keep the *Saved* text and the read-only rows tied to `roundDone` only. While the round is open, *Save readings* stays as it is (disabled when nothing is pending). The button then appears for a moment while a refused row is backspaced to empty. This does no harm: it locks nothing, and a tap on it loses no typed value. Add one e2e test, red first: partial save, `fill("")` on the refused row, assert *Enter more readings* shows and the row is still editable.

The other way out is to leave the code as built and record the departure from item 3 as accepted by the user. That decision is the user's.

## Nits

None.

## The docs pass

`## Docs updated` of the fix round says none. This is correct. The A1 sentence in `docs/Plan.MD` § 4.5 still describes the behaviour: a full save locks the round, and a partial save keeps the refused rows editable. `.claude/CLAUDE.md` § Docs to keep current asks for nothing else: no migration, secret, role, port, dev command or real-device check.

## Open findings of earlier rounds

| ID | Severity | Status |
|---|---|---|
| CR4-01 | major | Fixed (verified above). |
| CR4-02 | nit | Fixed (verified above). |
| CR1-10 | — | Open for the user, as the brief's header says. Not part of A1. |

## Manual checks for the user

The two manual checks of r4 still apply. The fix round does not change them:
- On an iPhone, after a full save that used a changed *Time taken*: tap the locked time field. Check that no date picker opens.
- On a phone (360 px wide), after a full save: check that *Saved* and *Enter more readings* sit side by side without crowding the "x of y filled" count, and that *Enter more readings* is easy to hit with a thumb.

## Checked and found consistent

- **The lock is set only at the end of a save.** It is set after `saving` turns false, so it never shows during a save. A save that stops on a network failure or on a *Time taken* refusal leaves rows pending, so the round stays open.
- **The partial-save path keeps refused rows editable.** `roundDone` stays false, the row's `phase` stays `idle`, and `readOnly = saved || locked` is false for it. The existing test "a partial save keeps the refused row editable" still passes in the coder's run.
- **Undo** opens the round only on success. Undo still shows on a locked round (Decision 2 of A1).
- **Every sheet load clears the lock**, through `resetStates`. Both the site switch and *Enter more readings* go through `loadSheet`.
- **The comment** at `ReadingsView.vue:93-95` says why the lock is a ref and not computed. It names CR4-01.
- **Scope.** The fix changed one Vue file and one spec file. No backend file, no `EventFields.vue`, no `ReadingSheetRow.vue` change. No new helper, prop or flag.
- **The report section** has the fix per finding, the tests with their red results, the files, the test counts, the docs pass and three `[auto]` manual checks, each with its test. It is written in scope A, apart from the claim CR5-01 names.
- **Screen text.** The fix adds no screen text.
