```
Step: S102 — PM alerts: job due, job overdue
Doc: impl report
Author: coder (Opus)
Date: 02-11-2026
```

# S102 — Implementation report

**Result:** a due PM job now sends two quiet push alerts per due point: *PM job due* to its assignee the
morning it turns *Due*, and *PM job overdue* the morning after its on-time window, to the assignee and the
unit's `pm_job:verify` holders. A daily task `pm_job_alert_scan` (08:00 IST) queues them; migration v56 adds
four marker columns that hold the due point each alert was sent for. Every unit suite, the targeted browser
run and the Normal whole suite are green (numbers in § Tests). No departure from the brief's design; the
small forced choices are in § 4 (the one to read is D-1, a pure `pm_markers` helper).

## 1. What was built

- **Migration v56**: `pm_jobs.due_alert_on DATE`, `due_alert_meter DECIMAL(14,3)`, `overdue_alert_on DATE`,
  `overdue_alert_meter DECIMAL(14,3)`, all NULL, after `needs_verification`. No CHECK, no index, no
  `_PRECONDITIONS` entry (§ 4.1).
- **Two alert kinds** in `alerts_core`: `PM_JOB_DUE`, `PM_JOB_OVERDUE` (`PM_KINDS`), push only, path
  `/pm/jobs/<id>`, tag `pm-job-<id>` for both (so *overdue* replaces *due* on the phone), quiet, TTL 24 hours
  (`push_core.PM_TTL_SECONDS`).
- **The daily scan** `pm_job_alert_scan` at 08:00 IST (`scheduled_tasks.SCHEDULE`, last entry), handled by
  `task_handlers.pm_job_alert_scan` → `pm_jobs.alert_scan`, one transaction per job.
- **The alert task** `pm_job_alert` (`task_handlers.pm_job_alert`): checks the alert is still true, finds the
  recipients and queues one `push_send` per device.
- **What you will get** gains "Overdue PM jobs at <place>" (roles with `pm_job:verify`) and "PM jobs assigned
  to you, when due and when overdue" (once, for an assignable role in a membership with a place).
- **Settings › Background tasks** names the task: "Send the PM alerts: jobs due today and jobs overdue —
  daily at 08:00".

## 2. How it works

1. **The scan** (`pm_jobs.alert_scan`). One plain read of the candidates (`_ALERT_CANDIDATES`: state `due`,
   overdue not yet sent for this due point, and a meter due value or a due date reached), then `commit`, so
   each job's transaction starts fresh. Per candidate, in plan id order (`_alert_one`):
   (6e) `LOCK_PLAN` → (6f) `LOCK_JOB` → `_now(cur)` → plain reads of the node's lifecycle and the plan meter's
   latest reading → `pm_jobs_core.job_standing` → `alerts_core.pm_alert_due`. When an alert is due, the
   marker `UPDATE` (no `updated_*`) and `alerts.enqueue_pm_alert` run in that job's transaction. A job's
   failure (other than a lost connection) rolls back only that job and is counted in `failed`; the handler
   then raises `RuntimeError` naming the jobs, so the task retries; the jobs already marked are no
   candidates any more. `should_stop()` is checked between jobs (`RetryLater` 60 s).
2. **The decision** (`pm_alert_due`): nothing unless the job is `due`, its plan active and its node not
   scrapped; *Overdue* standing → `PM_JOB_OVERDUE` unless its marker equals the due point; *Due* standing →
   `PM_JOB_DUE` likewise; else nothing. `due_point_alerted` compares the marker with `(due_on, due_meter)`
   (Decimals by value). An *overdue* writes all four markers, so a standing that falls back sends no late
   *due*.
3. **Re-arm**: nothing clears a marker. A plan edit, a reschedule or a plan save that drops a reschedule
   writes a new `due_on` / `due_meter`; the markers then differ, so the alerts come again at their moments.
4. **The alert task** (`pm_job_alert`): validates `job_id` and `kind` (else `BadTask`), reads the job with
   `pm_jobs.job_row` (plain; missing → `BadTask`), then `should_send_pm` (still `due`, plan active, node not
   scrapped, the kind's marker still equals the due point). Push off → log and end. Else
   `alerts.pm_job_recipients` and `_push_to_people` with `pm_job_message(kind, pm_job_facts(...))`.
5. **Recipients** (`alerts.pm_job_recipients`): `people_at_unit` at the job's site covering the node's
   current root unit. *Due*: the assignee only, and only while they hold `pm_job:read` there. *Overdue*:
   that, plus every holder of `pm_job:verify` (engineers, managers). A contractor or anyone without a
   device gets nothing (no `push_subscriptions` row).
6. **The texts** (`pm_job_text`): "PM job due · SMTW.MCC2 · HP003" / "PM-2026-11-004 · Monthly press check
   — due on 20-11-2026, on time until 23-11-2026."; "PM job overdue · …" / "… — was due on 20-11-2026,
   assigned to Ravi." (or "not assigned"). The due words follow the values: "on <date>", "at 1500 h", or
   both joined by "or"; "on time until" is `due_on + grace_days` and / or `due_meter + meter_window`.
7. **One standing**: `pm_jobs_core.job_standing(job, latest_value, today)` adds the job's `meter_offset` and
   calls `job_state(due_from_job(job), …)`. `pm_jobs.jobs_out` (the list, the card, the job page) and the
   scan both call it.

## 3. Files touched

Code (11):

- `backend/local_db.py` — migration v56.
- `backend/alerts_core.py` — the PM kinds, `CHANNELS`, `PM_PATH`, `due_point_alerted`, `pm_alert_due`,
  `pm_markers`, `should_send_pm`, `pm_job_facts`, `pm_job_text`, `pm_job_message`, two `you_get` lines, the
  docstring.
- `backend/alerts.py` — `PM_JOB_ALERT`, `PM_JOB_SCAN`, `enqueue_pm_alert`, `pm_job_recipients`, the PM
  paragraph of the docstring.
- `backend/pm_jobs_core.py` — `READ_KEY` (one copy), `job_standing`.
- `backend/pm_jobs.py` — `import alerts`; `READ_KEY` from the core; `LOCK_JOB` and `job_row` moved here;
  `jobs_out` calls `job_standing`; `_ALERT_CANDIDATES`, `_mark_alerted`, `_alert_one`, `alert_scan`; the
  LOCK ORDER note's S102 bullet.
- `backend/pm_work.py` — `_LOCK_JOB = pm_jobs.LOCK_JOB`; `_job_row` calls `pm_jobs.job_row`.
- `backend/task_handlers.py` — `pm_job_alert_scan`, `pm_job_alert`, `HANDLERS`, the docstring's fourth
  commit exception.
- `backend/scheduled_tasks.py` — `("pm_job_alert_scan", "08:00")` last, with its comment.
- `backend/push_core.py` — `PM_TTL_SECONDS`.
- `backend/equipment.py` — LOCK ORDER docstring: (6f) and the (6e) bullet's S102 line.
- `frontend/src/views/SettingsView.vue` — `TASK_LABELS.pm_job_alert_scan`.

Tests (8):

- `backend/tests/test_alerts_core.py` — `TestChannels` (the `KINDS` assertion, a PM kinds test), the four
  `TestYouGet` lists, new `TestDuePointAlerted`, `TestPmAlertDue`, `TestShouldSendPm`, `TestPmTexts`.
- `backend/tests/test_pm_jobs_core.py` — `READ_KEY`, `job_standing` with the offset and with no reading.
- `backend/tests/test_migration_v56.py` (new) — the columns, a v55 database with a due job, a re-run.
- `backend/tests/test_pm_alerts.py` (new) — the scan, the recipients, no-longer-true, push off, the worker
  path, bad tasks (25 tests).
- `backend/tests/test_scheduled_tasks.py` — the fifth `SCHEDULE` entry.
- `backend/tests/test_push_api.py` — the engineer's two new lines.
- `frontend/e2e/notifications.spec.js` — the engineer's two lines, the technician's exact list.
- `frontend/e2e/settings.spec.js` — new test "S102: Background tasks lists the PM alerts at 08:00".

Docs (6): `docs/schema/notes.json`, `docs/schema/schema.json`, `docs/schema/schema-data.js` (generated),
`docs/Plan.MD`, `.claude/CLAUDE.md`, `docs/steps/device-checks.md` (§ Docs updated).

## 4. Decisions taken

- **D-1. A pure `alerts_core.pm_markers(kind, job)`** returns the columns and values the scan writes
  (*due*: two; *overdue*: four). The brief puts the marker `UPDATE` in `pm_jobs._mark_alerted`; it is
  there, and it builds its `SET` from this helper, so the rule "overdue marks both" sits in the pure core
  with a test. `_PM_MARKERS` (the kind → its two columns) is shared by `pm_alert_due`, `should_send_pm` and
  `pm_markers`.
- **D-2. `alerts_core` imports `SCRAPPED` from `equipment_core`** for `should_send_pm` (the job row's
  `e_lifecycle`); `equipment_core` was already imported there.
- **D-3. `alerts.py` imports `PM_READ_KEY` and `PM_VERIFY_KEY` from `alerts_core`** (where the brief
  imports them), not from `pm_jobs_core` / `pm_work_core` directly: one place names the PM keys for the
  alerts.
- **D-4. The meter value with no unit** (a meter type without `unit`) reads "at 1500", no trailing space.
- **D-5. The "no longer true" log** names the state, the plan's active flag, the lifecycle and the due
  point (as S074's and S084's logs name theirs).
- **D-6. Plan.MD § 4.7's row** became two rows (*due* and *overdue*), with the departure from the Telegram
  column named in the *overdue* row's push cell; the Telegram column is empty.
- **Line endings**: `backend/push_core.py` and `docs/steps/device-checks.md` keep their own (CRLF / mixed);
  every edit kept them.

## 5. Not done, deferred, assumed

- **Red, then green**: the core functions were written just before their tests, so the new core tests were
  not shown red against missing code. For the shell, two tests were shown red against a broken rule: with
  the scrapped condition taken out of `pm_alert_due` and `should_send_pm`,
  `TestNoAlert::test_a_scrapped_node` failed (`assert ['pm_job_overdue'] == []`) and
  `TestNoLongerTrue::test_node_scrapped` failed (a `push_send` was queued); with the rule restored both
  passed.
- **The re-arm test** moves the due date by a straight plan-row change and `pm_generate` (the run's
  refresh), not by a plan save through the API; both write the job through `settle_plan_job` → `_refresh`.
- **Not built** (out of scope): an alert on an assignee change (§ 9 Q4), on *Waiting for verification* or
  *Sent back*, a repeat while overdue, the daily summary email.
- **§ 9 Q1–Q4** stay for KLA at gate B; each is one constant or one line.

## Manual checks

- [auto] What you will get: the engineer's card has "Overdue PM jobs at SMTW" and "PM jobs assigned to you,
  when due and when overdue"; the technician's list is exactly the three lines —
  `frontend/e2e/notifications.spec.js`::"S021 A1: What you will get — the engineer's breakdowns and defects,
  the technician's assigned jobs"
- [auto] Background tasks lists "Send the PM alerts: jobs due today and jobs overdue — daily at 08:00" —
  `frontend/e2e/settings.spec.js`::"S102: Background tasks lists the PM alerts at 08:00"
- [ ] **Important.** *PM job due* on the technician's phone after 08:00 on the due date, quiet, tap opens the
  job page; the engineer's phone shows nothing (device-checks row 67; production, TEST machine at SMTW.MCC2).
- [ ] **Important.** *PM job overdue* on the technician's and the engineer's phones two days after the due
  date; on the technician's phone it replaces *due* (device-checks row 68).

## Tests

All with `YANTRA_TEST_RUN=s102c1`.

- While coding (targeted): `test_alerts_core.py` 170 passed; `test_pm_jobs_core.py` 111 passed;
  `test_migration_v56.py` + `test_migration_v55.py` 11 passed; `test_pm_alerts.py` 25 passed; the *run whole*
  set of brief § 8.3 (`test_scheduled_tasks.py`, `test_push_api.py`, `test_pm_jobs_api.py`,
  `test_pm_work_api.py`, `test_pm_verify_api.py`, `test_pm_reschedule_api.py`, `test_pm_generate.py`,
  `test_worker.py`, `test_settings_api.py`, `test_alerts.py`) 286 passed.
- **All unit suites once** (`toolingun-tests.bat`): backend **5309 passed** (179 s), frontend **458
  passed**, tooling **239 passed** (the line-width check included): ALL SUITES PASSED.
- Build check: `npx vite build` in `frontend/`, built (only the known chunk-size warning).
- **Browser, targeted** (`toolingun-e2e-tests.bat e2e/notifications.spec.js e2e/settings.spec.js
  e2e/screens.spec.js`: the two specs the step changed, plus `screens.spec.js` as the settings say):
  **37 passed, 4 skipped** (76 s). The new test was run inside this targeted run, not alone first: `-g` with
  `|` breaks under `cmd //c` (§ Feedback).
- **Browser, the whole suite at Normal once** (`toolingun-e2e-tests.bat`): **420 passed, 15 skipped**, 0
  failed (219 s, 6 lanes).
- `tooling\schema-docs.bat check`: exit **0** (migration v56, 4 passed).

## Docs updated

- `docs/schema/notes.json` — the `pm_jobs` line names the four markers (S102); then `tooling\schema-docs.bat
  write` regenerated `docs/schema/schema.json` and `docs/schema/schema-data.js` (`git diff refs/steps/S101 --
  docs/schema/`: the migration number 56 and the four columns only); `check` exit 0 (§ Tests).
- `docs/Plan.MD` § 4.7 — the *PM job due* and *PM job overdue* rows, and a *PM alerts* bullet beside
  *Contract reminders*.
- `.claude/CLAUDE.md` — § Yantra Specifics, *Notifications (S021)*: the *PM alerts (S102)* part; § SMTW-Review:
  the *PM alerts (S102)* point, word for word from the brief's § 9.
- `docs/steps/device-checks.md` — rows 67 and 68 (both important).
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`:
  none, because the step settles no new maintenance rule or plant fact, changes no role or token claim, and
  adds no secret.

## Feedback

- hindrance: `-g "S102|S021 A1"` under `cmd //c` split at the `|` ("'S021' is not recognized"), so the
  new test was not run alone first; the targeted run covered it (1 run lost, 1 min).
- hindrance: `docs/steps/device-checks.md` has mixed line endings and no CRLF at the end; three edit scripts
  failed on an endings check before a plain append worked (4 tool calls).
- waste: the first `tooling\schema-docs.bat write` ran without `YANTRA_TEST_RUN`, so it used the reserved
  name `dev`; the Unit tests entry names the variable, but the schema-docs bullet of § Docs to keep current
  does not repeat it for `write` (1 run).
- idea: a small shared edit helper in `tooling/` (exact replace, keeps the file's CRLF or LF) would replace the
  per-step scratch scripts that every coder writes for multi-file edits (6 scripts this step).

## Fix rounds

### Round 1

- **CR1-01** — fixed by the orchestrator before this round (the report's raw CR bytes and "Docs (6)").
- **CR1-02** — Fixed. New test `backend/tests/test_pm_alerts.py::TestDueByDate::test_a_reschedule_leaves_the_markers_and_alerts_again`: *due* is sent, then S101's `POST /api/pm/jobs/<id>/reschedule` moves the job 10 days on; the four markers are unchanged (the route never writes them); a scan before the new point sends nothing; at the new point the scan queues *due* again and `due_alert_on` becomes the new date. It is a coverage gap, not a code fault, so there is no fix to undo for a red run; the test passes on the unchanged code.
- **CR1-03** — Fixed. The `_point_words` docstring in `backend/alerts_core.py` opens with three quotes and a short sentence ("The words for a due point: ...").

- Tests: `YANTRA_TEST_RUN=s102f1 tooling/run-backend-tests.bat tests/test_pm_alerts.py tests/test_pm_reschedule_api.py`: 50 passed; `tooling/run-tooling-tests.bat` (line width): 239 passed.
- Docs updated: none, because the round adds one test and fixes one docstring.

### Feedback

- none
