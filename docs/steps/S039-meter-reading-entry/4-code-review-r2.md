```
Step: S039 — Meter reading entry
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S039 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** The fix round fixes CR1-01 to CR1-07 as it says. It rejects CR1-08 as a code change, which is correct, and records it. This round adds one nit. All four suites and the targeted browser specs pass.

This round verifies the fix round ("### Round 1" in `3-impl-report.md`). It does not re-review the step. There is no snapshot of the round 1 state, so I read each file the fix round touched in full:
- `frontend/e2e/support/meters.js`
- `frontend/e2e/readings.spec.js`
- the S038 and S039 tests of `frontend/e2e/equipment.spec.js`
- `frontend/src/views/equipment/MetersCard.vue`
- `ReadingFormModal.vue`
- `ReadingHistoryModal.vue` (the script part)
- the `counter_error` docstring in `backend/meters_core.py`
- the `meter_types` row of `docs/schema.md`
- row 32 of `docs/steps/device-checks.md`

I also re-read `frontend/src/utils/meterLabels.js` `savedMessage`, because CR1-06 depends on it.

## Tests run

| Run | Result |
|---|---|
| `YANTRA_TEST_RUN=s039cr2 tooling/run-tests.bat` | backend PASSED 2948 (168 s), frontend PASSED 157, deps PASSED 42, tooling PASSED 115 |
| `npx vite build` (`frontend/`) | built in 4.98 s, the usual chunk-size warning only |
| `tooling/run-e2e-tests.bat e2e/readings.spec.js e2e/equipment.spec.js e2e/screens.spec.js` | **111 passed** (5.7 min, 6 lanes, three projects) |

- **Why these specs.** The fix round changed `readings.spec.js`, `equipment.spec.js` and the Meters card. `screens` is required every time.
- **No full suite.** In `e2e/support/`, the fix round only added `logByApi` to `meters.js`, and only these two specs import it.
- **The count.** It went up from 108 to 111. The new CR1-06 test runs on three projects.

## Findings of round 1

| ID | Severity | Status | Verified |
|---|---|---|---|
| CR1-01 | minor | Fixed | Each test computes its time once (`at`, `earlier`, `typed`), sends that string through `logByApi` and expects `shownTime` of the same string. There is no red result. The reason given holds: you cannot force a minute tick without faking the clock. |
| CR1-02 | minor | Fixed | One `logByApi(machine, name, value, takenAt, extra)` in `e2e/support/meters.js`, imported by both specs. The inline block in `equipment.spec.js` is gone. |
| CR1-03 | minor | Fixed | *Log reading* has no `btn-sm`. The last-reading line has `py-2`, normal text and the full row width. Both carry `touch-target` (`min-height: 44px`). `expectTouchTarget` checks both on three projects. The red result is given ("Received 23"). Row 32 names both controls. |
| CR1-04 | minor | Fixed | The `meter_types` row of `docs/schema.md` ends "Readings are in `meter_readings` (S039, v32)". |
| CR1-05 | nit | Fixed | `UNAVAILABLE = [502, 503, 504]`, and a missing status is treated the same way: all of them show "Not saved. Try again in a minute.". There is no test, and the reason given holds: the e2e stack has no Nginx. |
| CR1-06 | nit | Fixed (another way) | See below. The fix is sound. The red result is given. |
| CR1-07 | nit | Fixed | `per_page` is no longer sent. `meters.HISTORY_PER_PAGE` (30) is the only place of the page size. |
| CR1-08 | nit | Rejected as a code change, recorded | The "Known gap" paragraph in the `counter_error` docstring names both cases and phase 5. This is what the finding asked for. |

### CR1-06: the coder's fix is sound

**Recommendation: keep this fix. Do not open an amendment to put the limits in the POST answer.**

- **What changed.** `MetersCard.readingSaved` waits for the card's `load()`. It then words the message from the reloaded meter's limits. If the meter is gone, or the reload failed, it uses the dialog's meter.
- **Why it works.** The server judges `limit_state` against the limits at the moment of saving. Before the fix, the message named the limits of the list loaded before the dialog opened. That list can be minutes old. Now it names the limits of a list read right after the commit. The case the finding described is now covered: an engineer changes a limit while the operator types.
- **What is left.** A wrong limit now needs an engineer to change it between the commit and the next GET. That is a window of well under a second. On a plant with about 50 users, this risk is too small to justify changing the API.
- **The test.** "S039: the saved message names the limit in force at saving (CR1-06)" lowers the max from 60 to 50 while the dialog is open, then expects "Saved. Above the limit of 50 °C.". The test runs the exact scenario of the finding, and the fix round gives the red result.
- **The other side effects.**
  - The message shows one GET later than before, and the card was reloading anyway.
  - `load()` has its sequence guard, so another reload at the same time cannot leave a mixed list.
- **The amendment option.** Putting `min_value` and `max_value` in the POST answer would make the message exact. It would also change the API shape for a sub-second window. That is not worth a gate for the user.

## Nits

- **CR2-01** (nit) `frontend/src/utils/meterLabels.js:92-93`: `savedMessage` prints "Above the limit of null °C." when `limit_state` is `high` or `low` but the meter in hand has no limit on that side. That can happen if an engineer clears the limit in the sub-second window, or if the reload fails and the fallback meter is the old list after a limit was added. Return "Saved. Above the limit." (or "Below the limit.") when the side is `null`.

## Checked and found consistent

- **The fix round's diff brings in no new fault** apart from CR2-01, and that edge case was already there before the fix.
- **`MetersCard.vue`:**
  - The last-reading line is now `w-100 d-flex`, with the chevron at the right. Its accessible name is still "History: …", and the e2e test checks it.
  - The engineer-only buttons (*Set limits*, *Remove*, the confirm pair) stay `btn-sm`, as the finding allowed.
  - The scoped `.touch-target` style is local to the card.
- **`ReadingFormModal.vue`:** `notSavedOr` keeps every other error as it was. A 400 with a field still shows beside its field, and the e2e refusal test passes.
- **`ReadingHistoryModal.vue`:** the query now sends only `meter_type_id`, `page` and `include_removed`. *Show more* still works through the server's `per_page` in the answer (`total` against `items.length`).
- **`logByApi`:** it logs as the operator and expects 201, with the body text as the failure message. It cleans up its request context in `finally`.
- **The writing style of the report.** The fix round section is in scope A: each finding has a status and a reason, the red results are given, and the files are listed.
- **Screen text.** The new text has no wording change. The 502–504 message is the existing "Not saved. Try again in a minute.".
- **Docs pass.** The fix round's doc edits (`schema.md`, row 32) are listed under `## Docs updated`.
- **Manual checks.** `## Manual checks` is unchanged. It holds every important check: three `[auto]` with this round's passing run behind them, and the real-device check as an open box matching row 32.

## Manual browser checks for the user

- Row 32 of `docs/steps/device-checks.md` (important). On an Android phone and an iPhone, check four things:
  - *Log reading* and the last-reading line are easy to hit with a thumb;
  - the keypad has digits and a decimal point;
  - the refusal under *Value* is not hidden by the keyboard;
  - *Yes* and *No* are easy to hit with a thumb.
- Gate B, carried from round 1 (brief § 1.3, BS1-04): the *Meters* card stays below Details / Properties. On a phone, *Log reading* is about two screens down.
