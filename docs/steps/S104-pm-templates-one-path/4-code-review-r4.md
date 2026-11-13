```
Step: S104 — PM templates: one path
Doc: code-review r4
Author: Code reviewer (Opus)
Date: 12-11-2026
```

# S104 — code review, round 4

**Verdict: one `blocker` is open, and no `major`.** The blocker is CR1-01, carried and owed: the
database-backed tests, the schema docs and every browser run still wait for the dev database. CR3-01 (minor)
and CR3-02 (nit) are fixed. The new *Clear old value* button is shown to the right people, sends a body the
server accepts, and keeps the page's unsaved assignee and date. It brings in two smaller faults. A clear drops
the open job's reschedule although the base of the next due does not change (CR4-01, minor). A meter value
the engineer has typed is emptied by the clear (CR4-02, minor).

This round verifies fix round 3 only (`step_snapshot.py diff S104 --from-round 3`, 5 files). The review was
static, as the orchestrator asked: Docker Desktop is not running, and I did not start it.

## Test runs (this review, `YANTRA_TEST_RUN=s104cr4`)

| Run | Result |
|---|---|
| `tooling\run-frontend-tests.bat` | PASSED, 467 passed (465 + 2 new) |
| `pytest --collect-only` on `test_pm_plans_api.py` | 23 collected, no import error |
| Line width of `test_pm_plans_api.py` (`awk 'length>120'`) | no long line |
| Backend API suite, `schema-docs.bat check`, browser runs | **not run**: the dev DB is down (CR1-01) |

The round changed no backend code, so the pure core tests were not re-run.

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 (blocker) | **Open, owed** | *Runs owed (need Docker)* is current. Step 1 names both changed API tests, step 4 the new browser test, and step 1 also lists the manual watch of the plan page. |
| CR1-02 to CR1-14 | Fixed (round 2) | not re-checked |
| CR2-01 (major), CR2-02 (nit) | Fixed (round 3) | not re-checked |
| CR3-01 (minor) | **Fixed** | below |
| CR3-02 (nit) | **Fixed** | `test_pm_plans_api.py:159-163`: the save sends `technician["id"]`, checks the answered assignee and `seed_note`, and compares the three `SEED_COLUMNS` of the row before and after. `technician` (`pm_helpers.py:108`) is a `maint_technician` at the machine's site, so `_check_assignee` passes, and `meter_template` makes a maintenance template, so `OPERATOR_NO_ASSIGNEE` does not apply. |

**CR3-01, traced through the code:**
- **Who sees the button.** It sits inside the note, under `v-if="plan.can_edit"` (`PmPlanView.vue:286`).
  `can_edit` is `_can_write(node)` (`pm_plan:edit` at the node's site, the node not scrapped) and the plan
  linked (`pm_plans.py:162, 172`). A reader sees the note without the button. The PUT route has the same gate
  (`require_perm(EDIT_KEY)`, then `_share_lock_node`), so the button and the route agree.
- **The server accepts the null-only PUT** (brief § 5.5). `validate_plan_settings` takes any subset.
  `plan_settings_error` judges `last_done_meter` only when it is not None (`pm_plans_core.py:118-126`), so a
  null is never refused, also with no meter trigger or a trigger meter that no longer resolves.
  `plan_changes` sees `1000 → None` as a change, and `change_plan` writes all three seed columns as None
  (`pm_plans.py:444-447`). `_seed_note` returns None for a null value, so the answer has no note.
- **The page after the clear** (`PmPlanView.vue:129-141`). `plan.value` takes the PUT's answer, which is the
  full detail (`_detail`), so `can_edit`, `meters` and `template` stay. The form is not reloaded and no
  snapshot is taken, so an unsaved assignee or date stays, and the page stays dirty. Cancel still asks. One
  field is reset (CR4-02). A refusal goes to `error` as on Save: a 403, 404 or 409 has no field and shows at
  the top.
- **Wording** (CLAUDE-COMMON § Writing style B). The button starts with a verb, and the question states a
  consequence. *Yes* and *No* follow this page's *Remove from this machine* question, so they are consistent
  in the page. The stated consequence is not accurate (CR4-01), and the terms vary a little (CR4-04).
- **The reschedule.** `last_done_meter` is in `SCHEDULE_FIELDS`, so a clear sets `keep_reschedule=False`
  (`pm_plans.py:448-452`), as the impl report's decision (3) says. See CR4-01.
- **Tests.**
  - `pmLabels.test.js`: two new cases for `clearSeedBody` and `lastDoneHint`, with their red result (both
    functions missing, 2 failed). Green here.
  - `test_clear_old_value_removes_the_unused_seed`: the fixtures and the shapes match the neighbouring
    `test_the_seed_follows_the_meter` and `TestSettings` (`settings(..., last_done_meter=None)` sends JSON
    null; the detail has `last_done_meter` through `format_number`, None for null). I see no fault a first
    run would hit. Not run (DB).
  - The browser test (`pm-plans.spec.js:163`): `pmPlanByApi` turns `meter_equipment_id: machine.id` into
    the parent tick, and the seed PUT runs while the trigger still resolves to the machine's model meter. The
    own meter is then added as admin with the body `readings.spec.js:971` and `tickets-work.spec.js:693`
    already use. `_model_meter` returns None for a part with no model, so the POST gives 201. The locators
    (`getByLabel("Meter reading then")`, the button by exact name, *Yes* inside the note, apart from
    *Remove*'s *Yes*) match the page. The test finds its own plan and opens no dialog. It is a logic test, so
    it is right that it has no `@device` tag. It uses no `page.route`. I see no fault a first run would hit.
    Not run (DB).

## Minor

### CR4-01 (minor) — *Clear old value* drops the open job's reschedule, and the question says something else

- **Where:** `backend/pm_plans.py:448-452` (`schedule_changed`), with the question in
  `frontend/src/views/PmPlanView.vue:288`.
- **Problem:** the button shows only while the seed note shows, so the stored value is always one the plan
  does not use (`seed_matches` is false). The base of the next due comes from the meter's readings or a base
  job, before and after the clear (`pm_jobs_core.meter_base_source`). The date part uses `last_done_on`,
  which the clear does not send. So the clear never moves the next due. Its only effect on the schedule is
  this: `last_done_meter` is in `SCHEDULE_FIELDS`, so `keep_reschedule` is False, and a due job's
  `rescheduled_on` / `rescheduled_meter` are dropped. The question says "The next due is worked out again
  without it." The engineer reads that the due may change. The engineer cannot see that a supervisor's move
  is undone. S101 D4 drops a move because the base changed. Here the base does not change. CR2-01 fixed the
  same effect for an assignee-only save.
- **Failure scenario:** a part's job is due at 1,250 h. The supervisor (`pm_job:verify`) moves it to 1,400 h
  with the reason "Part arrives on Friday". Later the engineer opens the plan page, sees the yellow note, and
  presses *Clear old value*, then *Yes*. The job is due at 1,250 h again. At 1,260 h it shows *Overdue*, and
  the next morning the overdue alert goes to the assignee and the verifiers. The timeline still shows the
  move, and nobody knows why it no longer holds.
- **Fix:** pick one of these and say so in *Decisions taken*:
  1. (recommended) Keep the reschedule when the clear removes a seed the plan does not use. Put the rule in
     the pure core, for example `pm_plans_core.schedule_changed(stored, changes, trigger)`: a
     `last_done_meter` change to None counts only when `pm_jobs_core.seed_matches(stored, trigger)` was true.
     Call it from `change_plan` in place of the `any(...)` line. Add a core test, and an API test with a due
     job moved by `pm_job:verify`, then cleared: `rescheduled_meter` stays. Then change the question to
     "Clear the old meter value? The next due does not change."
  2. Keep the drop. Record it for KLA at gate B, and say it in the question, for example "Clear the old meter
     value? A moved due date goes back to the plan's date."

### CR4-02 (minor) — *Clear old value* empties a meter value the engineer typed

- **Where:** `frontend/src/views/PmPlanView.vue:135` (`form.value.last_done_meter = ""`).
- **Problem:** since round 2 the meter field starts empty while the note shows (`planSettingsForm`). So any
  value in the field at the time of the clear is one the engineer typed, never the old value. The clear
  empties it with no word. After the clear the note is gone, the field is empty, and the snapshot also holds
  `""`, so the page is not dirty for that field and Cancel does not ask.
- **Failure scenario:** the engineer types 1,000, the part's reading at the last service. The engineer then
  reads the hint "To remove it, use Clear old value" and thinks the old value must go first. The engineer
  presses *Clear old value*, then *Yes*, then *Save plan*. The page goes back to the machine. The plan has no
  *Last done* meter value, and the next due counts from the part's readings, not from 1,000. The engineer
  believes it was saved.
- **Fix:** remove the line, so the typed value stays. After the clear the note is gone, so
  `planSettingsBody` sends the field, and *Save plan* ties the value to the meter the plan uses now. The page
  stays dirty, so Cancel asks. Add the case to the browser test: type a value, clear, and the field still
  holds it.

## Nits

- **CR4-03** (nit) `frontend/src/utils/pmLabels.js:327-328`: "Leave the meter reading empty to keep the old
  value unused" asks a floor user to keep something unused, and it also shows when the template has no meter
  trigger and the page has no meter field (`triggerMeter` is null; `_seed_note` shows the note when the
  trigger does not resolve). Write it as what to do, for example "If you do not know the reading, leave it
  empty. To remove the old value, use Clear old value.", and leave out the first sentence where
  `plan.template.meter_type` is null.
- **CR4-04** (nit) `frontend/src/views/PmPlanView.vue:288, 293`: the button says "old value" and the question
  says "old meter value". Use one term in the button, the question and the hint, for example "Clear old meter
  value".

## Checked and found consistent

- **The case without a note is unchanged.** `lastDoneHint` returns the old sentence word for word (a unit
  test pins it), and no other spec or screen reads the hint or the new test ids.
- **The button's place and style.** It sits in the warning, apart from *Save plan* and *Cancel*. It is
  outlined and asks first, and its *Yes* is red. `btn-sm` comes with `tap-target`, as the page's *Remove*
  question has it. `:disabled="saving"` stops a clear while a save runs.
- **`confirmingClear` is reset on every load**, so a stale question does not stay after a navigation.
- **Decisions taken (round 3)** state the confirm step, the save at once, the kept form and the reschedule
  drop. The last one is CR4-01.
- **Docs:** the round names none as due. That is right: the route already took the null, and no schema,
  permission or flow a doc describes changed.
- **Red, then green:** given for the two frontend cases. For the two API tests and the browser test it was not
  possible (DB), and the report says so.

**Files re-read:** `frontend/src/views/PmPlanView.vue` (whole), `frontend/src/utils/pmLabels.js:286-331`,
`frontend/tests/pmLabels.test.js:160-197`, `frontend/e2e/pm-plans.spec.js:1-40, 130-190`,
`frontend/e2e/support/pm.js`, `frontend/e2e/support/properties.js` (`noModelPart`),
`backend/tests/test_pm_plans_api.py:1-60, 120-245`, `backend/tests/pm_helpers.py` (fixtures), `backend/pm_plans.py`
(`seed_not_used`, `_seed_note`, `_plan_out`, `change_plan`), `backend/pm_plans_core.py`
(`validate_plan_settings`, `plan_settings_error`, `plan_changes`, `SCHEDULE_FIELDS`), `backend/pm_jobs.py`
(`settle_plan_job`, `plan_resolutions`, `meter_type_out`), `backend/pm_jobs_core.py` (`seed_matches`),
`backend/meters.py` (`add_node_meter`, `_model_meter`), the impl report § Runs owed and § Fix rounds › Round 3.

## Still to check by hand in a browser

The browser runs owed under CR1-01 still cover the brief's checks. None needs a real device. The plan page with
an unused seed, after the DB runs:
1. The note shows, the meter field starts empty, and an assignee-only save keeps the note.
2. *Clear old value* asks first. *Yes* removes the note, and the hint goes back to "Leave it empty if you do not
   know".
3. After CR4-01's fix: a due job moved by the supervisor keeps its move after the clear.
4. After CR4-02's fix: a value typed before the clear is still in the field, and *Save plan* stores it.

## Feedback

- hindrance: the fourth static round in a row. Two new DB-backed tests and one browser test could only be
  checked by tracing fixtures and routes by hand. A single targeted run would settle more than this whole
  review.
- rule: when a fix adds an action that writes a schedule field (here `last_done_meter`), the coder should say
  in *Decisions taken* whether the base of the next due really changes, not only that the field is in
  `SCHEDULE_FIELDS`. Round 3's decision (3) stated the drop but not that the due stays the same, and CR4-01
  follows from that gap.
