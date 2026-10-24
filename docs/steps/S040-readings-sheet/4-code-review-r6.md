```
Step: S040 — End-of-day readings sheet
Doc: code-review r6
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S040 — code review, round 6 (A1 fix round for CR r5)

**Verdict: no `blocker` or `major` finding is open.** CR5-01 is fixed. The fix round brings in no new finding.

Scope: this round verifies the CR5 fix round only (round-2+ rule). The step is at gate B and snapshotted, so I read the snapshot, not the working tree (S046's coder writes there now). The diff is `refs/steps/S045..refs/steps/S040` for these files:
- `frontend/src/views/ReadingsView.vue`: the state block (lines 83–104), `saveAll`'s end (line 279), `enterMore` and `undo` (lines 286–305), the discard watcher (lines 184–194), and the save bar (lines 399–406);
- `frontend/e2e/readings.spec.js`: the CR5-01 test ("after a partial save, giving up the refused row offers Enter more readings");
- `docs/Plan.MD` § 4.5: the changed A1 sentence;
- `docs/steps/S040-readings-sheet/3-impl-report.md`: § "A1 fix round (CR r5)".

The same diff holds the CR4 fix round, which r5 verified. I checked only that the CR5 change leaves it intact.

## Test results

| Run | Result |
|---|---|
| Frontend unit tests, the coder's run (`s040c6`) | Relied on: PASSED, 168 passed. The fix changes no unit-tested module, so I did not re-run. |
| `npx vite build`, the coder's run | Relied on: built in 4.34 s, usual chunk-size warning only. |
| E2E, the coder's run | Relied on (standing rule of 25-10-2026): `readings.spec.js` and `screens.spec.js`, all three projects, 81 passed, 0 failed, 42 skipped. The skips are phone-webkit (S045's display-scale guard on this PC) and the bottom-bar test that skips itself on desktop. These are the right specs: the fix changed only the *Readings* screen and no shared frontend code. |
| E2E, my run | Not run, as the orchestrator asked: S046's coder may be changing the e2e tooling in the tree. No finding of mine needs a run. |
| Backend | Not run: no backend change. |

## Verification of the r5 findings

### CR5-01 (minor) — fixed

**When the button shows.** `canEnterMore` (`ReadingsView.vue:99`) is `!saving && pending === 0 && some row saved`. That is exactly the condition the orchestrator named: no save runs, no filled row is pending, and a row is saved. The button's `v-if` (line 404) uses it, and nothing else does.

**The lock is unchanged.** `roundDone` is still a `ref(false)` (line 96), written only in `saveAll` (line 279), `undo` (line 301) and `resetStates` (line 86). The read-only rows (lines 369 and 385), the locked *Time taken* (line 348) and the *Saved* button (line 402) all read `roundDone`, not `canEnterMore`. So the CR4-01 fix holds: emptying a refused row does not lock the round.

**The two states line up.** I checked each path:

| State | `roundDone` | `canEnterMore` | Save bar |
|---|---|---|---|
| Full save | true | true (no row pending, rows saved; *Saved* blocks a new save) | *Saved* (disabled) + *Enter more readings* |
| Partial save, refused row still holds a value | false | false (one pending) | *Save readings* |
| Partial save, refused row emptied (CR5-01) | false | true | *Save readings* (disabled) + *Enter more readings*; rows editable |
| Same, then a value typed again | false | false | *Save readings* (enabled) |
| Full save, then *Undo* on a row | false | false (the undone row keeps its value, so it is pending) | *Save readings* |
| Same, then the undone row emptied | false | true | as in the CR5-01 row |
| Save stopped by a network failure or a *Time taken* refusal | false | false (rows pending) | *Save readings* |
| During a save | unchanged | false | *Save readings* (disabled) |

`roundDone` true implies `canEnterMore` true, because a locked round cannot gain a pending row (rows read-only) and only `undo` reopens it. So the lock never shows without its way out.

**Save readings and Enter more readings side by side.** In the CR5-01 state the bar shows a disabled *Save readings* next to *Enter more readings*. This makes sense: nothing is left to save, the rows stay open in case the user types the skipped reading after all, and *Enter more readings* starts the next round. It is the same layout as after a full save (*Saved* disabled + *Enter more readings*), so the phone-width manual check of r4 covers it. A tap on *Enter more readings* loses no typed value, because no filled row is pending; only an empty row and a changed *Time taken* are dropped, as after a full save. The discard question cannot be open in this state: the `watch(pending)` (line 186) clears it once nothing is pending.

**The test asserts what the user sees.** It makes a partial save, asserts that *Enter more readings* is absent while the refused row holds 900, empties the row, and asserts that the button shows, the emptied row is not `readonly` and the saved row is. A tap then gives two empty, editable rows. No dialog opens, so `expectDialogFits` does not apply.

**Red result.** The report gives it: without the fix (desktop-chromium, `E2E_LANES=1`, `-g "CR5-01"`) the test failed at `expect(enterMore(page)).toBeVisible()`, because the button was absent. This meets the *Red, then green* rule.

**The report's claim.** The fix round corrects the r4 section's line that the side effect was "as the review accepts". This closes the scope-A point CR5-01 raised about the report.

## Findings

None.

## Nits

None.

## The docs pass

`## Docs updated` names `docs/Plan.MD` § 4.5. The A1 sentence now says that *Enter more readings* also shows after a partial save once no filled row is left to retry. This matches the code. `.claude/CLAUDE.md` § Docs to keep current asks for nothing else: no migration, secret, role, port, dev command or real-device check.

## Open findings of earlier rounds

| ID | Severity | Status |
|---|---|---|
| CR5-01 | minor | Fixed (verified above). |
| CR4-01 | major | Fixed (r5); the CR5 fix keeps it fixed. |
| CR4-02 | nit | Fixed (r5). |
| CR1-10 | — | Open for the user, as the brief's header says. Not part of A1. |

## Manual checks for the user

The two manual checks of r4 still apply. The fix round adds no new one:
- On an iPhone, after a full save that used a changed *Time taken*: tap the locked time field. Check that no date picker opens.
- On a phone (360 px wide), after a full save: check that *Saved* and *Enter more readings* sit side by side without crowding the "x of y filled" count, and that *Enter more readings* is easy to hit with a thumb. The CR5-01 state (*Save readings* disabled + *Enter more readings*) has the same layout, with a slightly longer first button; check it too if convenient.

## Checked and found consistent

- **One condition per job.** `canEnterMore` decides only the button; `roundDone` decides only the lock. The comment at lines 97–98 says why the button may show while the round is open, and names CR5-01.
- **No duplicated rule.** `canEnterMore` is the old computed `roundDone` expression under a new name, so no near-copy was added.
- **Scope.** The fix changed one Vue file, one spec file, the Plan sentence and the report. No backend file, no `EventFields.vue`, no `ReadingSheetRow.vue` change, no new prop or flag.
- **The earlier tests still hold.** "a partial save keeps the refused row editable" asserts the button is absent while the refused row holds a value, which `canEnterMore` keeps false. Both CR4-01 tests end with *Enter more readings* visible after a full save, which still holds. The coder's run passed them all.
- **The report section** has the fix, the test with its red result, the files, the test counts, the docs pass and one `[auto]` manual check with its test. It is written in scope A.
- **Screen text.** The fix adds no screen text.
