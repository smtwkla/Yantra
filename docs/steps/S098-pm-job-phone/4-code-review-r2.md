```
Step: S098 — Do the PM job on the phone
Doc: code-review
Round: 2
Author: Code reviewer (Opus)
Date: 02-11-2026
Verdict: no blocker or major finding open; 3 minor, 4 nits
```

# S098 — code review, round 2 (CR1 verified; the screens reviewed in full)

**Verdict: no blocker or major finding is open.** CR1-01 to CR1-04 are fixed in the backend.
The screens follow the brief. Three minor findings:

- the job page says "Also logged as …" on items that are not logged;
- the offline text reads "… try again. Tap again.", which says retry twice (D-c15);
- the in-progress *Performed by* select keeps showing a person whose save failed.

This round has two parts, as the orchestrator asked:

1. **A verification of CR1-01 to CR1-04.** It covers the fix round's backend diff
   (`step_snapshot.py diff S098 --from-round 1 -- backend`).
2. **A first review of the screens**, which round 1 did not judge. It covers `PmJobView.vue`,
   `pm/PmJobDoneDialog.vue`, `components/PmJobRow.vue`, the router entry, `PmJobsView.vue`,
   `PmPlansCard.vue`, `MeView.vue`, `pmLabels.js` with `pmLabels.test.js`, and the specs
   `pm-job`, `pm-jobs`, `me` and `screens`.

**Files I re-read in full:** `frontend/src/views/PmJobView.vue`,
`frontend/src/views/pm/PmJobDoneDialog.vue`, `frontend/src/components/PmJobRow.vue`,
`frontend/e2e/pm-job.spec.js`, `backend/pm_work.py` `save_result` and `start_job`. I read the rest
as the round's hunks (`pmLabels.js`, `PmJobsView.vue`, `MeView.vue`, `PmPlansCard.vue`, the
router, the three changed specs, `pmLabels.test.js`, `docs/Plan.MD`, `docs/steps/device-checks.md`).
I also read `frontend/src/api.js` and `frontend/src/utils/meterLabels.js` for the reuse checks.

**Tests (my run, `YANTRA_TEST_RUN=s098cr2`):**

- `tooling/run-tests.bat`: **ALL SUITES PASSED**: backend 5085 passed (153 s), frontend 447
  passed, tooling 239 passed.
- Build check, `npx vite build` (output to `scratch/s098cr2-dist`): built in 5 s. It printed the
  old chunk-size warning only.
- **No browser run.** I made each finding by reading the code, and none needs a run. The coder's
  runs are recorded in R2.5:
  - the new spec alone: 10 passed;
  - the targeted run (`pm-job`, `pm-jobs`, `me`, `pm-plans`, `readings`, `screens`): 113 passed,
    1 skipped;
  - the whole suite at Normal, once: 408 passed, 15 skipped, 1 failed (see below).

  Those are the brief's § 8.4 targeted specs. The whole-suite run was due because the router is a
  shared file.
- **No schema docs check.** The fix round's diff does not touch `backend/local_db.py` or
  `docs/schema/`.

**The `labels.spec.js:57` failure (desktop-chromium) was not caused by S098.** S098 only shifted
the lane order. The test ticks `seed.extruder` (EXT001) on page 1 of the equipment list. Every
machine S098's specs make comes from `meterMachine`, whose model is class `HP`. Their codes sort
after `EXT`, so they cannot push EXT001 to page 2. The CMP machines of other specs in lane 1 did
that. S098's new spec changed the lane plan (`E2E_LANE_PLAN`, the timings), and so it changed
which specs share lane 1 with `labels.spec.js`. The coder's re-run of `labels.spec.js` alone passed
6 of 6. The fault is an order-dependent test that existed before S098; it belongs to a later step.

## Round 1 findings

| ID | Status | Evidence |
|---|---|---|
| CR1-01 (minor) | **Fixed** | `_log_reading` (`backend/pm_work.py:326-341`) removes the job's own `pm` reading first, then checks the meter in force. A gone meter returns `(None, not_logged(…))`. `save_result` writes `reading_id` NULL because it differs from the stored one. The new test `test_a_meter_removed_after_a_logged_value_lets_go_of_the_reading` covers *NA* (200, link NULL, reading removed, row kept), then a new value (`logged` false, the note). The report gives the red result: `assert 500 == 200` without the fix. The stated change to § 5.5 step 1 is in the fix table. |
| CR1-02 (nit) | **Fixed** | `save_result:377-380`: when `state_error` refuses, `_work_access` runs and always raises (404 / 403, else the state's 409) before `meters.lock_node`. The LOCK ORDER note says so. The new test gives `JOB_DONE` on a done job whose machine was scrapped since. The red result is given. |
| CR1-03 (nit) | **Fixed** | `JOB_FROM` gains `result_count`. `job_item` sends it as `plan.item_count` when `started_at` is set (started or done), else the plan's active items. The new test `test_a_started_job_counts_its_own_items` gives 2, not 3. The red result is given (`assert 3 == 2`). |
| CR1-04 (nit) | **Fixed** | `pm_jobs.add_event` is public. No caller of `_add_event` is left (`grep` over `backend/pm_*.py`). It is a rename, so no test is needed. |
| CR1-05 (nit) | Closed | Accepted in round 1. |

## Findings

### CR2-01 (minor) — "Also logged as …" shows on every item with a meter, also when nothing is logged

`frontend/src/views/PmJobView.vue:385-387` (with `loggedLine` at `:178`).

**Problem.** The line shows for every result that names a meter: `item.id && item.meter`. It does
not read the item's `logged` flag, which the API sends for this purpose (§ 6.2: "true when
`reading_id` is set and that reading is active"). The `meter_note` that replaces the line lives
only in the page's memory, so a reload loses it. The page then states a false fact in four
cases:

- a reading answered *NA* ("Why is there no reading?"), which logs nothing;
- a value saved after the meter left the machine (D9, and now CR1-01), once the page reloads;
- a linked reading that an engineer removed later on the Meters card (report § 5);
- an item not yet filled, where "Also logged" reads as done already.

The done job is the record (ISO 9001 § 7.5.3). There the line also shows on the read-only rows.

**Failure scenario.**

1. A technician answers *NA* on "Run hours" with the remark "Meter glass broken".
2. He marks the job done.
3. The engineer opens the done job. The item reads *NA*, "Meter glass broken", and under it "Also
   logged as a Run hours reading of HP003."
4. The engineer looks for the reading in the Meters card's history and finds none.

**Suggested fix.**

- Show `loggedLine(item)` only when `item.logged` is true.
- Show `stateOf(item).note` when the last save in this visit sent one.
- Show nothing else: `limits_text` already says "· logs Run hours · HP003" before the item is filled.

Add one line to the browser test `S098: a reading that logs a meter is refused …`: before the
1,270 save, the row does not contain "Also logged".

### CR2-02 (minor) — the offline text says retry twice: "… try again. Tap again." (D-c15)

`frontend/src/utils/pmLabels.js:364-367` (`notSavedText`), used at
`frontend/src/views/PmJobView.vue:123` and `:143`.

**Problem.** The two texts the page can show break scope B rule 2 (one idea per sentence) and
the error rule (what happened, why, what to do: once each):

- the network case: "Not saved: No connection. Check Wi-Fi or mobile data and try again. Tap
  again.";
- a 5xx: "Not saved: Yantra is not answering. Try again in a minute. Tap again." The two retry
  instructions contradict each other ("in a minute", then "again" now).

A low-literacy or Tamil-speaking technician reads three instructions where one is needed. The
house already has the shape "Not saved. <what to do>.": `meterLabels.NOT_SAVED` = "Not saved. Try
again in a minute." (the readings screens).

**Failure scenario.** At a dead spot on the plant Wi-Fi, a technician taps *Done* on a task. The
row reads "Not saved: No connection. Check Wi-Fi or mobile data and try again. Tap again." He reads
"try again" and "tap again" as two separate steps. He taps twice in a row while still offline,
and the line comes back unchanged.

**Suggested fix (the words).** `notSavedText(message)` returns `` `Not saved. ${message}` ``, so
`api.js`'s own message (which already says what to do) comes after "Not saved.":

- no connection: **"Not saved. No connection. Check Wi-Fi or mobile data and try again."**
- a 5xx: **"Not saved. Yantra is not answering. Try again in a minute."**

This answers the three questions, with one instruction each. "Try again" is the app's word for
it elsewhere. The brief words this text in § 5.10, § 5.12 and § 8.5, and the device-check row 64
quotes it, so the orchestrator should record the change as an amendment or a gate B decision for
KLA. Then update row 64 ("it reads 'Not saved. No connection …' and keeps the last saved
choice"), the `notSavedText` unit test and the comments in `PmJobView.vue:10`. The browser test
asserts only "Not saved" and stays as it is.

### CR2-03 (minor) — after a failed *Performed by* change, the select keeps showing the person not saved

`frontend/src/views/PmJobView.vue:114-127` (`changePerformer`) and `:259-267` (the select bound
with `:value`, not `v-model`).

**Problem.** The select takes its value from `job.performed_by?.id` one way. On a failed `PUT`
the job does not change, so Vue does not set the DOM value again. The select keeps the person the
user picked, and the line under it says the change was not saved. Two faults follow:

1. **The retry does not work.** The error says "… Tap again." But picking the same person again
   fires no `change` event, because that person is already selected. The user has to pick another
   person, then the wanted one, and that saves a wrong performer between the two picks (an extra
   `performer_changed` event in the history).
2. **The record looks changed.** After the user leaves the error line behind (scrolls to the
   items), the card shows a performer that the job does not hold. *Mark job done* then records the
   old performer.

`PmJobsView.vue`'s own comment names the same trap: "v-model on a select re-syncs … a plain
:value would not".

**Failure scenario.**

1. Kannan started the job for Ravi.
2. On a weak signal he changes *Performed by* to himself. The save fails and the line reads
   "Not saved: …".
3. Back in range, he picks "Kannan (Technician)" again. Nothing happens, and the select still
   shows Kannan.
4. He fills the items and marks the job done. The job records Ravi as the performer.

**Suggested fix.** In `changePerformer`'s `catch`, set the select back to the saved person:
`event.target.value = String(job.value.performed_by?.id ?? "")`. Then the select shows the truth,
and a pick of the same person fires `change` again. With CR2-02's words the line reads "Not saved.
No connection. Check Wi-Fi or mobile data and try again."

## Nits

- **CR2-04** (nit) `frontend/src/utils/pmLabels.js` (`resultText`): a reading item with a meter
  shows its value raw ("1270 h"), while the Meters card shows "1,270 h". Use
  `meterLabels.formatReading(item.value, item.meter.meter_type)` when the item has a meter (the
  house's Indian grouping, U4), and keep the raw value with `item.unit` for a free reading.
- **CR2-05** (nit) `frontend/src/views/PmJobsView.vue` (`DONE_PAGE_SIZE = 50`): this repeats the
  backend's `DEFAULT_PER_PAGE`. Pass `answer.per_page`, which the *Done* answer carries, to
  `PagerBar`.
- **CR2-06** (nit) `frontend/e2e/me.spec.js` (S098 test, D-c13): I accept the pattern, because the
  lane's other specs assign PM jobs to the same technician. Make it still prove the count: assert
  that the number in "PM jobs (n)" equals the count of `.job-row` under the heading. The test also
  checks only that *Tickets* is visible. Assert that the PM heading comes before it (the brief's
  "above the tickets").
- **CR2-07** (nit) `frontend/src/views/PmJobView.vue:192-195`: a user without `pm_job:read` who
  types `/pm/jobs/<id>` (the storekeeper) gets a 403. The page shows "PM job could not be loaded:
  …" with a *Retry* that cannot help. Treat a 403 as the 404 state ("PM job not found, or not at
  your units." with *Back to PM*), as the API's 404 already hides other units' jobs.

## The departures D-c11 … D-c18

| ID | Judgement |
|---|---|
| D-c11 the started job's own count | Accepted. It is CR1-03's fix: one row shape for every state. |
| D-c12 `countText(tab, counts, total)` | Accepted. `counts` holds only the open jobs (D-c2), so the *Done* total has to come in separately. The unit test covers it. |
| D-c13 Me's count by pattern | Accepted, with CR2-06. A fixed "(1)" would fail whenever lane order changes. Asserting that the heading's number equals the rows shown keeps the check. |
| D-c14 the item state in one reactive map | Accepted. One page uses it, and a row component would add props and events with no second use (right-sized). |
| D-c15 "Not saved: … Tap again." | **Not accepted as worded:** CR2-02 proposes "Not saved. <api.js message>". Flag it for KLA at gate B, because it changes the brief's text and device-check row 64. |
| D-c16 *Done* handed over on `closed` | Accepted. It is the brief's S077 rule. `onClosed` emits only after a save, and the dialog unmounts after its fade because `working` turns false only then. |
| D-c17 a refused save opens nothing | Accepted. A 409 on an item shows its message under the item. A *Start* 409 without a field reloads the page, and the reload shows the reason (started, cancelled, scrapped). The message itself is cleared by `load()`. That is harmless here: `ALREADY_STARTED`'s "Reload the page." is done by the page, and `NO_ITEMS` cannot be reached. |
| D-c18 expected 400s and the offline error named | Accepted. These are the S024 console-watch conventions. |

## Against the brief (§ 5.9–§ 5.11, § 8.4)

- **The big buttons.** A check shows *OK* / *Not OK* / *NA* in a `btn-group w-100`, `tap-target`
  plus `min-height: 48px`, the outline style until chosen, `aria-pressed` on the chosen one. A task
  shows *Done* / *Not done*. *OK*, *Done* and a check's *NA* save at once. *Not OK*, *Not done* and
  a reading's *NA* open the remark field with its prompt (`REMARK_PROMPTS`) and *Save* beside it.
  The remark goes only with the answer it explains (BR1-02, `resultBody`, unit-tested). No `btn-sm`
  is used.
- **High / Low as typed.** `limitFlag` runs on the typed text against the copied limits. The badge
  is `text-bg-danger` and the input gets a red border. After the save, the stored `limit_state`
  keeps the badge and the red row (`isMarked`). The browser test asserts "High" before *Save*,
  after it, and gone at 45.
- **Each item saved as it is filled.** There is one `PUT` per item, with "Saving…" on the tapped
  control and the row's controls disabled, then "Saved". A refusal shows under the item with the
  typed value kept. `counter_lower` shows the *Meter reset* tick. A failure with no answer keeps
  the last saved choice. The offline test proves the rule: "Not saved", the button not pressed,
  "1 of 3 filled", then a tap online saves, and a reload keeps both items.
- **Performed by and the times.** *Start* has the select through `personLabel`, me first when I
  am in the list, else "Choose who did the work.". *Started* is `EventFields` (`pm-start`,
  `withRemark: false`) with its *Now* tick. *Start job* is full width at 48 px, and reads
  "Starting…" while it runs. Refusals show beside their fields. The test of recording on behalf
  covers another person, a time two days back, and the *Done*-before-*Started* refusal in the
  dialog.
- ***Mark job done*** sits after the items, not fixed (D13). It is disabled with "Fill all n items
  first. Your entries are saved as you go.". The dialog has the line "Started … · n of n filled",
  the consequence "The job can no longer be changed.", and the save button *Mark job done*. The
  call contract matches § 5.10 (`blank()` without a seed, `openCreate()` without one, `send(() =>
  apiPost(…))`).
- **The read-only states.** A done job shows the card "Performed by … · Started … · Done …" and
  each result as a badge or a value with "Filled by …". A reader or IT admin sees no buttons. A
  scrapped machine shows the scrapped line. A cancelled job shows its badge and remark. *History*
  shows in every state, with "by the daily PM run".
- **The list, the card, Me.** The *Done* tab is paged in the URL, with "No PM jobs are done yet.",
  and a new filter or tab starts at page 1. Rows go through `PmJobRow` (keeping `job-row` and
  `data-equipment`) and open `/pm/jobs/<id>`. *In progress* comes before the standing badge, and
  the small line reads "In progress · <name>". The card uses `jobBadges`. *Me* shows "PM jobs (n)"
  above the countermeasures, on page 1 of *Open work* only, for `pm_job:read` holders with a Team
  record, inside the one `Promise.all`. The *Tickets* heading shows when either section above has
  rows.
- **`expectDialogFits`** is called on the one dialog the flows open (*Mark job done*), in both
  tests that open it.
- **The `@device` rule.** Only `S098: the job page fits a phone with large item buttons` is tagged
  (its purpose is a geometry check). Every other new test is untagged.
- **The `[auto]` checks.** Each *Automated* check of § 8.4 has a test that asserts what the user
  sees, not only that a page opened. The `screens()` entry checks the heading for the ticket roles.

## Docs pass

`## Docs updated` matches the diff:

- `docs/Plan.MD` § 2 (8) and § 6 carry the *Me* wording of § 3's docs list.
- `docs/steps/device-checks.md` gains rows 64–66 (§ 8.5). The gloved thumb is marked important.
- Round 1's schema docs, CLAUDE.md and Plan.MD changes stand as reviewed.
- `docs/Keycloak.md` needs no change.

CR2-02 would change row 64's quoted text.

## Manual checks

`## Manual checks` carries every important check of § 8.4 as `[auto]` with its test, and the
`screens()` entry. The important device check (the gloved thumb, row 65) is an unticked box, and
rows 64 and 66 are plain notes. Nothing is missing.

Still for the user's (IT Admin's) **manual check** on a real device:

- [ ] **important** A gloved thumb on *OK*, *Not OK*, *NA* and *Done* (row 65).
- A real Wi-Fi drop: the "Not saved …" line, then "Saved" back in range (row 64; the words change
  if CR2-02 is taken).
- The decimal keypad on the iPhone and Android, with *Save* not hidden (row 66).

## Checked and found consistent

- No screen holds a business rule:
  - the server judges what is filled, the limit state stored, the time window and the state rules;
  - `limitFlag` is the brief's display helper while typing, and the server stores `limit_state`;
  - `allFilled` only enables the button, and the server refuses with `not_all_filled`.
- No actor comes from the client: `performed_by_id` is the chosen person, which the server checks
  at the site.
- Reuse:
  - `PmJobRow` replaces S097's inline row (DRY), and the list and *Me* share it;
  - `jobBadges` serves the page, the row and the card;
  - `EventFields`, `FormModal` / `useFormModal`, `PagerBar` and `personLabel` are the house parts;
  - the open findings on reuse are CR2-02 (`NOT_SAVED`'s shape), CR2-04 (`formatReading`) and
    CR2-05.
- Phone layout:
  - no fixed widths;
  - `overflow-wrap: anywhere` on the page and the row;
  - the buttons fit one row (the `@device` test);
  - *Mark job done* is not a fixed bar.
- Load races: `loadSeq` guards both `PmJobView.load` and the list. A stale answer never overwrites
  a newer one.
- The router: `/pm/jobs/:id(\\d+)` sits after `pm`, under `/pm/` so the nav item stays lit, and
  the API's 404 is the gate.
- The backend fix round adds no new lock path. CR1-02's early branch takes no node lock. CR1-01
  calls `remove_reading_row` under the meter node's lock, as before. All lines are at most 120
  characters (the tooling suite is green).
- `Track: full`, as the step needs.

## Feedback

- idea: `step_snapshot.py diff … --from-round 1 -- backend docs` printed 61 KB, because
  `docs/Plan.MD` lines are whole paragraphs and the hunks carry them. A `--stat` per path group,
  or `-U1` as an option, would have let me skip the docs hunks (1 extra call).
- rule: the round-2 rule "verify, don't re-review" and this round's "review the screens in full as
  a first review" both apply to a split step. The spawn prompt settled it. A line in the
  code-reviewer agent for split-round steps ("round 2 of a two-part step reviews the second part
  as round 1") would make it explicit (this run).
- hindrance: no house helper says when a failed save counts as "no answer". `meterLabels.isUnavailable`
  (0 and 502–504) and the PM page's `status === 0 || status >= 500` differ. I had to read both to
  judge CR2-02 (2 files, about 3 min).
