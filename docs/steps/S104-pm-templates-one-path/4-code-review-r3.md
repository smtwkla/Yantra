```
Step: S104 — PM templates: one path
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 12-11-2026
```

# S104 — code review, round 3

**Verdict: one `blocker` is open, and no `major`.** The blocker is CR1-01, carried and owed: the
database-backed tests, the schema docs and every browser run still wait for the dev database. CR2-01 (major)
is fixed. An assignee-only save from the plan page now sends no `last_done_meter`. The server then writes no
seed column and counts no schedule change, so the open job keeps its reschedule (S101 D4). A typed value is
still sent. The fix brings in one smaller fault: while the seed note shows, the page can no longer clear the
unused value (CR3-01, minor).

This round verifies fix round 2 only (`step_snapshot.py diff S104 --from-round 2`, 4 files). The review was
static, as the orchestrator asked: Docker Desktop is not running, and I did not start it.

## Test runs (this review, `YANTRA_TEST_RUN=s104cr3`)

| Run | Result |
|---|---|
| `tooling\run-frontend-tests.bat` | PASSED, 465 passed |
| `pytest --collect-only` on `test_pm_plans_api.py`, `test_pm_generate.py` | 42 collected, no import error |
| Line width of the two changed `.py` files (`awk 'length>120'`) | no long line |
| Backend API suite, `test_migration_v57.py`, `schema-docs.bat check`, browser runs | **not run**: the dev DB is down (CR1-01) |

The round changed no backend code, so the pure core tests were not re-run.

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 (blocker) | **Open, owed** | *Runs owed (need Docker)* is current. It names `test_the_seed_follows_the_meter`, which this round touched, among the tests to run first. |
| CR1-02 to CR1-14 | Fixed (round 2) | not re-checked |
| CR2-01 (major) | **Fixed** | below |
| CR2-02 (nit) | Fixed | `git grep "PM-2097"` finds only `test_pm_generate.py:294`, so no other test uses that prefix |

**CR2-01, traced through the code:**
- **The page.** `planSettingsForm` (`pmLabels.js:291-297`) starts `last_done_meter` as `""` when
  `plan.seed_note` is set. `planSettingsBody` (`pmLabels.js:304-314`) sends the field only when it holds a
  value or no note shows. `PmPlanView.vue:91` fills the form from `planSettingsForm` on every load, and
  `:114` saves with `planSettingsBody`. The dirty snapshot is taken after the form is filled, so an empty
  field does not make the page dirty.
- **The server, assignee-only save.** `validate_plan_settings` → `masters_core._validate`
  (`masters_core.py:363-374`) skips a field the body does not hold, so `clean` has no `last_done_meter`.
  - `plan_changes` (`pm_plans_core.py:130-141`) calls `changes_of`, which looks only at fields in `clean`,
    and its CR1-05 branch needs `clean.get("last_done_meter")` to be a value. So no seed column is written
    (`pm_plans.py:444`).
  - The page also sends `last_done_on`. It equals the stored date, so it is no change. `schedule_changed`
    is therefore false, and `settle_plan_job` keeps the reschedule (`pm_plans.py:448-452`; S101 D4).
- **The server, typed value.** A typed `1000` is sent. The CR1-05 branch counts it as a change against a
  seed of another meter, and the seed columns name the meter the plan uses now. That is unchanged from
  round 2.
- **Tests.**
  - `pmLabels.test.js` has three new cases: the field starts empty, an assignee-only body has no
    `last_done_meter`, and a typed value is sent.
  - The report gives the red results: two cases failed without the fix, and the third passes both ways
    because it guards the other side. The suite is green here.
  - The API test gains `settings(engineer_a, plan, assignee_id=None)` and checks that `seed_note` stays.
    It has not run (DB).

## Minor

### CR3-01 (minor) — while the seed note shows, the plan page cannot clear the unused value

- **Where:** `frontend/src/utils/pmLabels.js:309-312` (`planSettingsBody`), with `PmPlanView.vue:262`
  (the hint "Leave it empty if you do not know.") and `:266` (the note).
- **Problem:** this round's fix makes an empty meter field mean "leave the stored value as it is" while the
  note shows. The page now has no way to send `null`. Brief § 5.5 says "null clears all three", and before
  this round an engineer cleared the value by emptying the field. Now, if the engineer does not know the
  reading, the warning "Enter it again for the meter this plan uses now" stays on the page for good. The
  hint below the field tells the same engineer to leave it empty. This also holds when the trigger meter no
  longer resolves on the machine (`seed_matches(row, None)` is false, so the note shows). There, typing a
  value is refused with `no_meter_here`, so the note cannot be cleared at all.
- **Failure scenario:** a part gets its own hour meter. The plan page shows the yellow note about HP002's
  Run hours. The engineer does not know the part's reading at the last service. As the hint says, the
  engineer leaves the field empty and saves. The page goes back to the machine. When the plan page is
  opened again, the same warning is there. Every later visitor reads it as work still to do. The schedule
  is not wrong, because the seed is unused, but the warning never goes away. The engineer cannot clear it
  without calling the person who manages the database.
- **Fix:** pick one of these and say so in *Decisions taken*:
  1. (recommended) Put a small button beside the note, outside the everyday Save, for example
     "Clear old value". It saves `{last_done_meter: null}` (or sets a flag that makes `planSettingsBody`
     send `null`). Add a `pmLabels.test.js` case for the cleared body. The API already accepts null and
     clears all three columns.
  2. Accept that the note stays until a value is entered. Record this at gate B for KLA, and change the
     note or the hint so that they do not contradict each other.

## Nits

- **CR3-02** (nit) `backend/tests/test_pm_plans_api.py:157`: `assignee_id=None` equals the stored
  assignee, so the PUT changes nothing, and the test does not show a real assignee change keeping the
  seed. Send an assignable person's id, as `TestSettings` does, so the save writes a row and still leaves
  `seed_note` and the seed columns unchanged.

## Checked and found consistent

- **The case without a note is unchanged.** The field shows the stored value, an emptied field sends
  `null` and clears the seed, and a template without a meter type sends no meter value. The three older
  `pmLabels.test.js` cases still pass.
- **Whitespace-only input** goes through `textOrNull`, becomes `null`, and is left out while the note shows,
  the same as an empty field.
- **After a save**, the page goes to the machine. When the plan page is opened again, the form is filled
  from the new detail: the field is empty if the note still shows, and holds the value if the seed now
  matches.
- **No browser test** reads `pm-last-meter` or `pm-seed-note`, so the empty starting value breaks no spec.
- **Docs:** the round names none as due. That is right: no schema, route, permission or flow a doc
  describes changed.
- **Decisions taken (round 2):** the empty field is stated and sent to KLA at gate B, as the round-2 review
  asked.

**Files re-read:** `frontend/src/utils/pmLabels.js` (`planSettingsForm`, `planSettingsBody`),
`frontend/tests/pmLabels.test.js` ("the plan settings"), `frontend/src/views/PmPlanView.vue` (load, save,
dirty, the meter field and the note), `backend/pm_plans.py` (`change_plan`, `_seed_note`, `_plan_out`,
`seed_not_used`), `backend/pm_plans_core.py` (`validate_plan_settings`, `plan_settings_error`,
`plan_changes`), `backend/pm_templates_core.py` (`changes_of`), `backend/masters_core.py` (`_validate`),
`backend/pm_jobs_core.py` (`seed_matches`), `backend/tests/test_pm_plans_api.py` (`settings`,
`TestMeterMatch`), `backend/tests/test_pm_generate.py:290-297`.

## Still to check by hand in a browser

The browser runs owed under CR1-01 still cover the brief's checks. None needs a real device. One check is
added for the plan page with an unused seed:
1. The note shows, and the meter field starts empty.
2. Change only the assignee and save. The note is still there when the page is opened again, and the next
   due has not moved.
3. Type a value and save. The note is gone.
4. After CR3-01's fix, the old value can be cleared.

## Feedback

- hindrance: the third static round in a row. One line in the API test (CR3-02) and the whole CR2-01 server
  path could only be traced by reading `_validate`, `changes_of`, `plan_changes` and `change_plan`. A
  targeted run of `test_the_seed_follows_the_meter` would have settled it in seconds.
- idea: when a fix gives an empty field a new meaning ("leave as stored" instead of "clear"), the review
  that proposes it should name the action the old meaning served. CR2-01's suggested fix, written in round
  2, did not, and CR3-01 follows from it.
