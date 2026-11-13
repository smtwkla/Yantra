```
Step: S104 — PM templates: one path
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 12-11-2026
```

# S104 — code review, round 1

**Verdict: one `blocker` and two `major` findings are open.** The blocker is the owed runs: no
database-backed test, migration test, schema docs check or browser run has been made, because the dev
database (Docker Desktop) was down for the coding and for this review. The two majors are tests that a
first database run will certainly turn red. The production code reads well against the brief: I found
no wrong column name, no lock-order fault and no permission gap in the shell. Without a database run,
that is a reading, not a proof.

This round was static, as the orchestrator asked. I reviewed S104's change against the held S095–S102
code (`step_snapshot.py diff S104 --base refs/steps/S102`), not against HEAD; the S103 files in that diff
(`help/`, `tooling/help/`, `AppTopbar.vue`, `help.js`, `floor.spec.js`, `test_help_pages.py`) are
committed already and are left out.

## Test runs (this review, `YANTRA_TEST_RUN=s104cr1`)

| Run | Result |
|---|---|
| `tooling\run-frontend-tests.bat` | PASSED, 461 passed |
| `tooling\run-tooling-tests.bat` (line width included) | PASSED, 258 passed |
| Pure backend cores, `pytest --noconftest` on `test_pm_links_core`, `test_pm_templates_core`, `test_pm_plans_core`, `test_pm_jobs_core`, `test_pm_work_core`, `test_pm_schedule_core`, `test_alerts_core` | 750 passed |
| `npx vite build` | built; only the known chunk-size warning |
| `tooling\run-tests.bat` (backend suite), `test_migration_v57.py`, `tooling\schema-docs.bat check` | **not run**: the dev DB is down |
| Browser runs (targeted, whole suite, WebKit `screens.spec.js`) | **not run** by the coder or by me: the dev DB is down |

## Blocker

### CR1-01 (blocker) — the database-backed tests, the schema docs and every browser run are owed

- **Where:** `3-impl-report.md` § *Runs owed (need Docker)*; `docs/schema/schema.json`, `docs/schema/schema-data.js`.
- **Problem:** about 2,000 lines of shell code (`pm_templates.py`, `pm_plans.py`, the reworked `pm_jobs.py`
  and `pm_work.py`), the v57 migration and every API and browser test of the step have never run. The
  generated schema docs still show v56's tables (`pm_plan_items`, no `pm_templates`), so
  `tooling\schema-docs.bat check` is red, and `docs/schema/` misses v57's tables, columns and keys.
  `e2e/support/pm.js` is a new shared file, so the settings require the whole browser suite and the WebKit
  `screens.spec.js` run once.
- **Failure scenario:** the step is committed with a suite that is red on its first run (CR1-02 and CR1-03
  are two such faults found by reading; more are likely), and the release's `release-tests.bat` finds them
  in the maintenance window.
- **Fix:** with the dev DB up, run the impl report's *Runs owed* list in its order: the targeted backend
  files, `schema-docs.bat write` then `check` (exit 0), `run-tests.bat`, the new S104 tests alone, the
  targeted browser run, the whole suite at Normal, and `screens.spec.js --project=phone-webkit`. Fix what
  is red, record the counts, and mark each *Automated* check `[auto]` only after its passing run.

## Major

### CR1-02 (major) — `test_the_refusals` attaches the "lacking" template to the press, which has the meter

- **Where:** `backend/tests/test_pm_plans_api.py:173-190` (`TestSettings.test_the_refusals`).
- **Problem:** the test takes both the `press` and the `machine` fixtures. `press` (`pm_helpers.py:99-104`)
  adds the model meters to `machine` and returns the same node, so `machine` is the press. Line 188
  attaches a Run hours template to it; the press has Run hours from its model, so the trigger resolves,
  `plan_settings_error` finds no fault, and the `PUT` answers 200.
- **Failure scenario:** the first DB run fails here: `refused()` reads `body["error"]` from a 200 answer
  (a `KeyError`), and the "This machine has no Run hours meter" refusal is never tested.
- **Fix:** use a node without the meter, for example `make_equipment(unit=unit)` (a fresh model, no meters),
  or a part of the press without the parent tick, in place of `machine`.

### CR1-03 (major) — the job-page test reads `plan["needs_verification"]`, which the plan detail no longer has

- **Where:** `backend/tests/test_pm_work_api.py:107-109` (`TestPage.test_a_technician_reads_a_due_job_with_the_plan_s_items`).
- **Problem:** `plan` comes from `pm_helpers.plan_on` → `GET /api/pm/plans/<id>`. Since S104 that detail
  holds `needs_verification` only under `template` (`pm_plans._plan_out`, `pm_plans.py:159-162`), not at
  the top level, so `plan["needs_verification"]` raises `KeyError`.
- **Failure scenario:** the first DB run fails on this test before it checks the job page.
- **Fix:** read `plan["template"]["needs_verification"]`.

## Minor

### CR1-04 (minor) — the "meter base follows the meter" rule (BR1-01) has no test

- **Where:** `backend/pm_jobs.py:318-343` (`seed_matches`, `_meter_base`), `backend/pm_plans.py:148-151`
  (`_seed_note`); no test in `test_pm_generate.py`, `test_pm_plans_api.py` or `test_pm_templates_api.py`.
- **Problem:** brief § 5.3 makes the base follow the resolved meter: a done job's `done_meter` counts only
  when the job's copied meter equals the meter used now, and the seed only when its `seed_meter_*` match;
  otherwise the reading rule applies, and the plan page shows the seed note. These are new branches with
  no test. The tests cover only the case where everything matches.
- **Failure scenario:** a later change compares only the type, or only the node. A part that gains its own
  hour meter then counts from the parent's value. Its next job is due hundreds of hours early or late,
  and no test turns red.
- **Fix:** add API tests for these cases:
  - a meter-trigger plan with a done job on the parent's meter (parent tick), then an own meter added to
    the part: the next due counts from the part's own reading, not from the job's `done_meter`;
  - a seed entered for the parent's meter, then an own meter: the seed is not used, and the plan detail's
    `seed_note` names the parent's meter.

### CR1-05 (minor) — entering the same *Last done* meter value again does not tie it to the new meter

- **Where:** `backend/pm_plans.py:443-451` (`change_plan`).
- **Problem:** only fields whose value changes are written (`plan_changes`). The seed note (`seed_not_used`)
  tells the engineer "Enter it again for the meter this plan uses now." If the engineer types the same
  number, `last_done_meter` is not a change, so `seed_meter_equipment_id` and `seed_meter_type_id` keep
  the old meter. The seed stays unused, and the note stays on the page.
- **Failure scenario:** the template's trigger moves from the press's Run hours to the part's own hour
  meter, and both read 1,840 at the switch. The engineer re-enters 1,840 and saves. The plan still counts
  without the seed, and the note asks again, with no visible reason.
- **Fix:** in `change_plan`, also treat `last_done_meter` as changed when the body sends a non-null value
  and the stored seed meter differs from `resolution["trigger"]`. Then judge it with
  `plan_settings_error` and write the seed columns. Add a test.

### CR1-06 (minor) — two near-copies of the plan and meter-type readers

- **Where:** `backend/pm_templates.py:93-98` (`meter_type_of_row`) and `backend/pm_jobs.py:600-606`
  (`meter_type_out`); `backend/pm_plans.py:89-95` (`_PLAN_SELECT`'s column list) and
  `backend/pm_jobs.py:120-125` (`PLAN_SELECT`).
- **Problem:** `meter_type_of_row` repeats `pm_jobs.meter_type_out`, and `pm_jobs.py:601-602` still says
  "One copy: pm_plans.py's plans and items use it too", which is no longer true. `pm_plans._PLAN_SELECT`
  copies `PLAN_SELECT`'s template columns and its two joins word for word, then adds its own joins.
  `pm_templates.py` already imports `pm_jobs`, so the shared copies can be used without a new import
  cycle.
- **Failure scenario:** R03.19 adds a template column that the stop remark or the schedule needs to
  `PLAN_SELECT`. The card and the plan page (`_PLAN_SELECT`) do not get it. `plan_resolutions` then
  raises a `KeyError` on the card while the daily run works.
- **Fix:** build `_PLAN_SELECT` from `pm_jobs.PLAN_SELECT` and its extra joins. Use
  `pm_jobs.meter_type_out` (add an id-column argument if the template rows need one), delete
  `meter_type_of_row`, and keep the comment true.

### CR1-07 (minor) — CLAUDE.md's self-check list of lock notes misses the template lock (6g)

- **Where:** `.claude/CLAUDE.md:56` (§ Step workflow, *Self-check, repo items*, item (2)).
- **Problem:** item (2) lists the modules whose LOCK ORDER notes a brief must check, and the PM lock
  numbers (6e). S104 adds `pm_templates.py` with its own LOCK ORDER note and the new lock (6g): the
  template row, FOR UPDATE by a template save, LOCK IN SHARE MODE by *Attach* after the node (1).
  Neither is named there.
- **Failure scenario:** R03.19's brief, which adds class, type and model links that also touch templates,
  runs the self-check from this list. It misses (6g) and the rule that nothing holding a plan waits on
  (6g) exclusive, and a lock cycle reaches the code.
- **Fix:** add `pm_templates.py` to item (2), and add "S104: (6g) the PM template row, FOR UPDATE only by
  a template save, first in its transaction; LOCK IN SHARE MODE by Attach after the node (1); plans
  settled only after its commit".

## Nits

- **CR1-08** (nit) `frontend/src/views/PmPlanView.vue:276-277`, `PmTemplateView.vue:409-410`,
  `pm/PmItemDialog.vue:97-98`: the confirmation *Yes* / *No* buttons are `btn-sm` without `tap-target`.
  Add `tap-target` (or drop `btn-sm`) so a phone keeps a 44 px target, as the other buttons on these
  pages have.
- **CR1-09** (nit) `frontend/src/views/PmTemplateView.vue:148-149, 408`: "Saved. 1 machines will update…"
  and "Its 0 machines stop getting jobs." Use the singular for 1, as `usedOnText` does. For 0 machines,
  say "No machine uses it yet" in the deactivation question.
- **CR1-10** (nit) `backend/pm_jobs_core.py:38-46`: the two new functions sit between the constants, and
  `TAB_DUE…` follows the second one with no blank lines. Move the functions below the constants.
- **CR1-11** (nit) `backend/pm_plans_core.py:116`: the code compares with the literal `"maintenance"`.
  Use `pm_templates_core.MAINTENANCE`, as `pm_jobs._job_assignee` does.
- **CR1-12** (nit) `backend/pm_jobs.py:246-251`: `resolve_meters(cur, node_id, needs)` is never called,
  because every path uses `plan_resolutions`. Remove it, and fix the `meters.py:541` docstring that names it.
- **CR1-13** (nit) `frontend/e2e/pm-templates.spec.js:61`: the title "a Meter reading item with its own
  limits is refused in the dialog" tests the reading-kind and meter-type refusals; the dialog cannot
  send limits for a Meter reading. Rename the test to what it checks.
- **CR1-14** (nit) `backend/pm_plans.py:284-285`: `_settle` only passes its arguments on to
  `pm_jobs.settle_plan_job`. Call `settle_plan_job` directly. The plan detail also has no
  `template.summary` (brief § 6), because the page builds it with `templateSummary`. Say so in the impl
  report's *Decisions taken*.

## Checked and found consistent

- **v57** (`local_db.py:1257-1547`) against brief § 4.1:
  - every table, key, generated column and CHECK is there;
  - the DROP list goes children first;
  - `_PRECONDITIONS` is unchanged (none is needed);
  - `migrations_v56.py` holds the frozen texts and is exempt in `test_line_width.py`;
  - `conftest._TABLES` puts children before parents (`pm_template_links`, `pm_template_items`,
    `pm_templates` after `pm_plans`);
  - the migration tests run under `--dist loadscope`, so the module fixture's order holds.
- **Column names:** no remaining SQL names `pm_plan_items`, `plan_item_id`, `pl.active`, `pl.title` or a
  plan's meter columns (grep of `backend/`, `frontend/src`, `frontend/e2e`, `tooling/` except
  `tooling/help/`, which gate A left broken).
- **Locks:**
  - the template save takes (6g) FOR UPDATE first and settles its plans only after its commit, one
    transaction per plan, through `settle_one`: (6e), then (1) shared;
  - Attach takes (1) shared, then (6g) shared;
  - Remove takes (6e), then (1) shared, then the link UPDATE;
  - `sync_node`'s make rolls back on 1062 and takes the relink path with (6e) first;
  - Start, *Mark job done*, reschedule and skip read the template plainly after (6e) and (6f);
  - the equipment.py LOCK ORDER entry (6g) is written;
  - I found no wait cycle: the foreign-key shared locks on the template and its items are taken only
    after (1) or (6e), and the template save never waits on them.
- **Permissions:**
  - template reads use `equipment:read`; template writes use `pm_plan:edit` held anywhere;
  - attach, preview, settings and remove check `pm_plan:edit` at the node's site through
    `load_node_for_user(..., key=EDIT_KEY)` (403 naming the site), with 404 outside the units;
  - no key was added, and `test_rbac` needs no change;
  - every route has `require_perm`, the actor comes from `actor()`, and no SQL is built from values.
- **The meter match:**
  - `needed_meters`: the stricter tick wins (D11);
  - `resolve_meters` and `applies`, with the remarks in the brief's order;
  - `plan_resolutions` reads in a fixed number of queries; the card test counts `meters_in_force` calls;
  - the job copies `meter_equipment_id` and `meter_type_id`;
  - *Mark job done*, skip, reschedule and the alert scan read the job's copy;
  - Start returns 409 with the brief's text for a missing meter and copies the name, `reading_kind`, the
    resolved node and the meter's limits in force (Decision 4, stated).
- **Pure cores:** `pm_links_core` and `pm_templates_core` import no DB, Flask or clock. Their tests are
  green, and the remarks live in `pm_jobs_core` (Decision 1, stated).
- **Frontend:**
  - the routes `pm-template-new` and `pm-template` exist, and `pm-plan-new` is gone;
  - Masters has the section `pm_templates` (`equipment:read`);
  - the item dialog shows the reading kinds with the brief's words;
  - the attach dialog's preview comes from the server;
  - the card has *Not in use (n)*, and the header counts only the linked plans;
  - the schedule-change confirmation shows when `plan_count` > 1;
  - a 503 after a save shows "The template may be saved. Reload the page to see it.";
  - every dialog is `FormModal`, and the flows call `expectDialogFits`.
- **Browser tests:**
  - each *Automated* check of brief § 8.4 has a test that asserts what the user sees;
  - two layout tests carry `@device` with a title that names the fit; the others are untagged;
  - the new specs set up through the API and look for their own records (machine codes in the names).
- **Docs:** CLAUDE.md § SMTW-Review (*PM templates and plan rows (S104)*, *PM jobs*, *PM job results*),
  Plan.MD § 4.3, Maintenance-Philosophy § 8 and `notes.json` are updated as brief § 3 asks. The
  generated schema files are not (CR1-01).
- **Scope:** nothing outside the brief was built; the decisions in the impl report cover the departures
  I found, except the small ones in CR1-14.

## Still to check by hand in a browser (after CR1-01's runs)

None of these checks needs a real device (brief § 8.5). The browser runs owed in CR1-01 cover them. The
important ones to watch in those runs:

1. An engineer adds a template with a Check, a Measurement and a Meter reading.
2. *Attach PM template* on a press: the card shows "This machine" and the next due, and the plan page
   shows "HP…'s own Run hours".
3. "Does not apply: no … meter on …" shows in the attach dialog and on the card.

## Feedback

- hindrance: the review ran with the dev DB down, so the backend API suite, the migration test and the
  schema docs check could not run, and two certain failures had to be found by reading fixtures
  (`pm_helpers.press` returns the `machine` node itself; `test_pm_plans_api.py:173`) (about 20 minutes of
  tracing that one test run would have shown).
- idea: `pytest --noconftest` fails to collect the API test files without `secrets_app.py` (9 collection
  errors), so a DB-free import check of the shell modules is not possible from the reviewer's side. A
  wrapper that imports the backend modules with a stub secrets file would catch name errors in shell code
  without Docker (`uv run pytest --noconftest --collect-only tests/test_pm_*_api.py`).
