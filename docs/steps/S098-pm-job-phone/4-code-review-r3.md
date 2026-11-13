```
Step: S098 — Do the PM job on the phone
Doc: code-review
Round: 3
Author: Code reviewer (Opus)
Date: 02-11-2026
Verdict: no blocker or major finding open; no new finding
```

# S098 — code review, round 3 (verification of CR2-01 … CR2-07)

**Verdict: no blocker or major finding is open.** All seven round-2 findings are fixed. The fix
round's diff brings in no new fault.

**One point for KLA at gate B (from CR2-02).** The offline text now reads "Not saved. No
connection. Check Wi-Fi or mobile data and try again." The brief words it as "Not saved: … Tap
again." in § 5.10, § 5.12 and § 8.5. The brief is not edited. The orchestrator decided the change,
and KLA approves it at gate B. Device-check row 64 already carries the new words.

**What I read.** I read the fix round's diff only (`step_snapshot.py diff S098 --from-round 2`,
7 files):

- `frontend/src/utils/pmLabels.js`
- `frontend/src/views/PmJobView.vue`
- `frontend/src/views/PmJobsView.vue`
- `frontend/tests/pmLabels.test.js`
- `frontend/e2e/pm-job.spec.js`
- `frontend/e2e/me.spec.js`
- `docs/steps/device-checks.md`

For the checks I also read `meterLabels.formatReading`, `pm_jobs.meter_type_out` (the shape of
`meter.meter_type`), `pm_jobs.py`'s `per_page` in the *Done* answer, and `utils/messages.js`. I
re-read no file in full.

**Tests (my run, `YANTRA_TEST_RUN=s098cr3`):**

- `tooling/run-frontend-tests.bat tests/pmLabels.test.js`: **PASSED**, 34 passed.
- No full-suite run. The round changes only frontend files and one docs row. The coder's build
  check passed (4.7 s).
- No browser run. No finding of mine needs one. The coder's targeted run covers what the round
  changed (`pm-job`, `pm-jobs`, `me`, `screens` at Normal): 49 passed, 1 skipped.
- No schema docs check. The diff does not touch `backend/local_db.py` or `docs/schema/`.

## Round 2 findings

| ID | Status | Evidence |
|---|---|---|
| CR2-01 (minor) | **Fixed** | `PmJobView.vue:386`: the line shows only when `item.logged` is true or this visit's save sent a `meter_note`. `load()` clears `itemStates`, so a reload falls back to `logged` from the API. The test asserts no "Also logged" before the 1,270 save. The red result is given. |
| CR2-02 (minor) | **Fixed** | `notSavedText` returns `` `Not saved. ${message}` ``. The callers pass it only for status 0 or 5xx, and `api.js` always sets the message then (`NO_CONNECTION_TEXT`, `NOT_ANSWERING_TEXT`). So the text never ends in "undefined". The unit test, the header comment, the spec and row 64 are updated. The red result is given. The brief's words go to gate B (above). |
| CR2-03 (minor) | **Fixed** | `changePerformer`'s `catch` sets `event.target.value` back to the saved performer. The spec changes *Performed by* offline, then asserts the "Not saved. No connection." line and the saved value. The report says why no red result exists: Vue re-patches `:value` when `disabled` flips. I accept that reason. The reset is a guard that does not depend on that re-render. |
| CR2-04 (nit) | **Fixed** | `resultText` calls `formatReading(item.value, item.meter.meter_type)`. `meter_type_out` sends `kind` and `decimals`, which `formatReading` needs. The unit test expects "1,270 h". The red result is given. |
| CR2-05 (nit) | **Fixed** | `DONE_PAGE_SIZE` is gone, and `PagerBar` gets `answer.per_page`. The *Done* answer always carries `per_page`, also when it is empty (`pm_jobs.py:400`). The pager shows only on that tab. |
| CR2-06 (nit) | **Fixed** | The test reads n from "PM jobs (n)" and asserts n `.job-row` rows. It also asserts that the PM heading sits above *Tickets* by `boundingBox().y`. |
| CR2-07 (nit) | **Fixed** | `load()` treats a 403 like a 404 and shows "PM job not found, or not at your units." with *Back to PM*. The report says why no test was added. For a one-condition nit, that reason is enough. |

## Checked and found consistent

- No new business rule on a screen. The "Also logged" condition reads the API's `logged` flag.
- The fix round's screen text follows scope B. It gives one instruction per case, in the house shape of
  `meterLabels.NOT_SAVED`.
- The fix round's red results follow the *Red, then green* rule, or give a reason (CR2-03, CR2-05,
  CR2-06 and CR2-07 are changes where a red run proves nothing new).
- `## Docs updated` for the round names row 64 only. That matches the diff. No other listed doc
  changes.
- No new `@device` tag. The spec edits stay inside tests that already exist.

## Manual checks

These are unchanged from round 2. Still for the user's (IT Admin's) **manual check** on a real device:

- [ ] **important** A gloved thumb on *OK*, *Not OK*, *NA* and *Done* (row 65).
- A real Wi-Fi drop: "Not saved. No connection. Check Wi-Fi or mobile data and try again.", then
  "Saved" back in range (row 64).
- The decimal keypad on the iPhone and Android, with *Save* not hidden (row 66).

## Feedback

- none
