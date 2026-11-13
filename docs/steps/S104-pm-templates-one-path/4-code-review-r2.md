```
Step: S104 — PM templates: one path
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 12-11-2026
```

# S104 — code review, round 2

**Verdict: one `blocker` and one `major` finding are open.** The blocker is CR1-01, carried: the
database-backed tests, the schema docs and every browser run are still owed, because the dev database is
down. The major is new and comes from the CR1-05 fix: the plan page sends the stored *Last done* meter
value back on every save, so an assignee change now silently ties an unused seed to the new meter. The
fault follows the fix that round 1 suggested; that suggestion missed what the page sends.

This round verifies fix round 1 only (`step_snapshot.py diff S104 --from-round 1`, 18 files). The review
was static again, as the orchestrator asked: Docker Desktop is not running.

## Test runs (this review, `YANTRA_TEST_RUN=s104cr2`)

| Run | Result |
|---|---|
| `tooling\run-frontend-tests.bat` | PASSED, 462 passed |
| `tooling\run-tooling-tests.bat` (line width included) | PASSED, 258 passed |
| Pure backend cores, `pytest --noconftest` on `test_pm_links_core`, `test_pm_templates_core`, `test_pm_plans_core`, `test_pm_jobs_core`, `test_pm_work_core`, `test_pm_schedule_core`, `test_alerts_core` | 766 passed |
| `pytest --collect-only` on `test_pm_plans_api`, `test_pm_generate`, `test_pm_work_api`, `test_pm_templates_api`, `test_pm_jobs_api` | 125 collected, no import error |
| Backend API suite, `test_migration_v57.py`, `schema-docs.bat check`, browser runs | **not run**: the dev DB is down (CR1-01) |

## Findings of round 1

| ID | Status | Verified by |
|---|---|---|
| CR1-01 (blocker) | **Open, owed** | *Runs owed* is current and names the four new or changed DB tests first |
| CR1-02 (major) | Fixed (not run) | `make_equipment(unit=unit)` makes a fresh model (`conftest.py:491-506`), so `bare` has no Run hours; trigger None, `no_meter_here` answers 400 |
| CR1-03 (major) | Fixed (not run) | `_plan_out` puts `needs_verification` under `template` (`pm_plans.py:156-160`) |
| CR1-04 (minor) | Fixed | `meter_base_source` keeps `_meter_base`'s branches exactly; core tests green, red result stated; both API tests read sound (below) |
| CR1-05 (minor) | Fixed, **with a new fault** | see CR2-01 |
| CR1-06 (minor) | Fixed | `_PLAN_SELECT` = `PLAN_COLUMNS` + its columns + `PLAN_FROM` + its joins (the string concatenation is right); `meter_type_of_row` gone, no caller left; the docstring is true (`pm_work.py:160` uses it) |
| CR1-07 (minor) | Fixed | `.claude/CLAUDE.md` § Self-check item (2) |
| CR1-08 to CR1-14 (nit) | Fixed | as the report says; `resolve_on_paths` and `_types_by_node` still have callers |

## Major

### CR2-01 (major) — an assignee change on the plan page ties an unused seed to the new meter

- **Where:** `backend/pm_plans_core.py:130-141` (`plan_changes`, its new third argument), with
  `frontend/src/utils/pmLabels.js:287-306` (`planSettingsForm`, `planSettingsBody`).
- **Problem:** `planSettingsForm` fills the meter field with the stored `last_done_meter`, and
  `planSettingsBody` sends it on every save of a template with a meter type. Since round 1, `plan_changes`
  treats that unchanged value as a change whenever the stored seed was entered for another meter than
  the trigger resolves to now. `change_plan` then writes the seed columns for the new meter. The server
  cannot tell an engineer who typed the number again from a page that only sent it back. This breaks
  brief § 5.3 ("the seed is kept and unused") and Decision 6 ("a page that sends back a stored seed … is
  not refused for it", which assumed that sending it back changes nothing). It also sets
  `schedule_changed`, so an assignee-only save drops the open job's reschedule, against S101 D4.
- **Failure scenario:** a part's plan counts on the press's Run hours (parent tick), with *Last done* at
  1,000 h. The part gets its own hour meter, which reads 40. The plan page shows "Last done meter value
  was entered for HP002's Run hours. Enter it again …". The engineer only changes the assignee to Ravi and
  saves. The note disappears, and the plan now counts from 1,000 on the part's meter. Its next due moves
  from 290 h to 1,250 h, so the PM is about 960 h late, and nothing on the page says why. The CR1-05 API
  test does not catch it, because it sends `last_done_meter` alone.
- **Fix:** keep the server rule and make the page send the value only when the engineer enters it:
  1. In `planSettingsForm`, start the meter field empty when `plan.seed_note` is set. The note already
     names the meter the old value was for. Optionally show the old value as the field's placeholder.
  2. In `planSettingsBody`, leave `last_done_meter` out while that field is empty and `plan.seed_note` is
     set, so the stored seed stays as it is (kept and unused).
  3. Add `pmLabels.test.js` cases for both functions with a `seed_note`: the field starts empty, an
     assignee-only body has no `last_done_meter`, and a typed value is sent. Show each one red first.
  4. State the choice in the impl report's *Decisions taken*. It changes no approved rule: the brief
     defines the note, not the field's starting value. If the orchestrator judges an empty field a design
     change, it goes to the user at gate B.

## Nits

- **CR2-02** (nit) `backend/tests/test_pm_generate.py:294`: the inserted job's serial
  `PM-2098-01-{plan id:03d}` uses the same prefix as `test_equipment_api.py:395` (`PM-2098-01-{equipment
  id}`). Both modules can run in one worker database in one session, and from 100 up a plan id equal to
  an equipment id gives the same serial: `uq_pm_jobs_serial` then fails one of them at random. Use a
  month no other test uses, for example `PM-2097-02-`.

## Checked and found consistent

- **The four DB-backed tests, read against the code** (none has run):
  - `TestSettings.test_the_refusals` (CR1-02): the fresh node is in `unit`, the engineer's site; Attach
    answers 201 on a plan that does not apply; with no trigger, `plan_changes` sees a change from None, and
    `plan_settings_error` answers `no_meter_here`.
  - `TestPage.test_a_technician_reads_a_due_job_with_the_plan_s_items` (CR1-03): `plan_on` returns
    `plan_of`'s detail, which has `title` at the top and `template.needs_verification`.
  - `TestMeterMatch.test_the_seed_follows_the_meter` (CR1-04, CR1-05): attaching with the parent tick
    resolves to the press, with no press reading, so no job is made and the card has a `next_due`. Then:
    - after the part gets its own meter, the seed no longer matches. The reading of 40 (one minute back,
      before `linked_at` or first after it) is the base, so the card shows `format_number` "290".
    - The second save with the same 1,000 is a change under the new rule. The seed columns name the part,
      `_seed_note` is None, and the due is "1250".
  - `TestMeterMatch.test_a_base_job_of_the_parent_s_meter_is_not_the_base_of_the_part_s_own_meter`
    (CR1-04): the inserted skipped row passes every CHECK of v57's `pm_jobs` (`chk_pm_jobs_windows`: both
    meter columns set and no `due_meter`; `chk_pm_jobs_done`: `skipped` with `done_at` and `done_meter`).
    `_last_base_job` returns it, and `meter_base_source` gives `READING_BASE`. There is no reading before
    `done_at`, so the first reading after it (40) is the base. The due is 290, and the reading of 300 makes
    a `meter` job on the part.
- **The heredoc append to `backend/tests/test_pm_jobs_core.py`:** the content is whole and correct, the
  file is LF throughout (0 CRLF, as are the other changed files and the tracked backend files), it ends
  with one newline, and it has no tabs. Its 12 tests pass.
- **`plan_changes`'s pure rule** on its own: clearing (None) is still a change, and with no trigger or no
  value nothing is tied. The new core tests are green, with their red result stated. CR2-01 concerns only
  the values the page sends.
- **`_meter_base` against round 0:** the job / seed / readings branches and `start` are unchanged in
  effect; `tuple(meter)` is reached only with a meter (`schedule_inputs` checks it).
- **Frontend:** `deactivateQuestion`, `savedNoteText` and `machinesText` read in plain words, and no
  browser test asserts the old strings. The three confirmations' *Yes* and *No* have `tap-target`
  (`main.css:142`), and the renamed test's title says what it checks.
- **Red, then green:** CR1-04 and CR1-05 give their red results, and CR1-02 and CR1-03 give a reason
  (DB). The CR1-09 unit test checks three new functions, so it could only fail on import. I raise
  nothing for it.
- **Docs:** the round's only due doc is `.claude/CLAUDE.md` (CR1-07), and it is listed. The schema files
  stay owed under CR1-01.

**Files re-read in full or in the touched parts:** `backend/pm_plans.py` (`_common_out`, `_plan_out`,
`change_plan`), `backend/pm_plans_core.py` (`plan_settings_error`, `plan_changes`), `backend/pm_jobs.py`
(`_last_base_job`, `_meter_base`, `schedule_inputs`, `plan_schedules`, the imports),
`backend/pm_jobs_core.py`, `backend/pm_templates.py`, `backend/tests/pm_helpers.py`,
`backend/tests/conftest.py` (`make_equipment`, `_TABLES`), `backend/tests/test_pm_generate.py`
(helpers, `TestMeterMatch`), `backend/tests/test_pm_plans_api.py`, `backend/tests/test_pm_work_api.py`
(`TestPage`), `backend/local_db.py` (v57 `pm_jobs`), `frontend/src/views/PmPlanView.vue` (`save`, the
form), `frontend/src/utils/pmLabels.js`, `frontend/e2e/pm-templates.spec.js`.

## Still to check by hand in a browser

Unchanged from round 1: the browser runs owed under CR1-01 cover the brief's checks; none needs a real
device. After CR2-01's fix, also watch the plan page with an unused seed: the note shows, the meter field
starts empty, and an assignee change keeps the note.

## Feedback

- idea: a review finding that changes how the server treats a value "equal to the stored one" should name
  the client's body builder it checked. Round 1's CR1-05 suggestion missed that `planSettingsBody` sends
  the stored value back, and the fix carried the fault in (`pmLabels.js:299-306`, found only in round 2).
- hindrance: the second static round in a row: four new DB tests were checked only by tracing
  `next_due`, `_meter_base`, the v57 CHECKs and the fixtures (about 25 minutes that one targeted run would
  have settled).
