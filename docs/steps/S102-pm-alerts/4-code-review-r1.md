```
Step: S102 — PM alerts: job due, job overdue
Doc: code-review r1
Author: code reviewer (Opus)
Date: 02-11-2026
```

# S102 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the brief asks, in the layers it
names, and every rule checked holds in the code. All unit suites and the schema docs check are green. The
findings are three nits.

## Tests run

- `YANTRA_TEST_RUN=s102cr1 tooling/run-tests.bat`: backend PASSED, 5309 passed (157 s); frontend PASSED, 458
  passed; tooling PASSED, 239 passed (the line-width test included). ALL SUITES PASSED.
- `YANTRA_TEST_RUN=s102cr1 tooling\schema-docs.bat check`: PASSED, "Schema docs at migration v56: 4 passed". It
  ran after the unit suites, not beside them.
- Browser: none re-run. No finding of mine needs a browser run. The coder's runs name the right specs: the two
  specs the step changed (`notifications.spec.js`, `settings.spec.js`) plus `screens.spec.js`, 37 passed and 4
  skipped; then the Normal whole suite once, 420 passed, 15 skipped, 0 failed. No other spec asserts the *What
  you will get* lines (`git grep` over `frontend/e2e`, `src`, `tests`). The step changes no shared frontend
  file, so no WebKit run is due. The build check (`npx vite build`) is reported as built.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `docs/steps/S102-pm-alerts/3-impl-report.md` § Tests: three CR bytes (0x0D) stand in place of
  `\r` in `tooling\run-tests.bat` and `tooling\run-e2e-tests.bat` (twice), so the report reads
  `toolingun-tests.bat`; write the backslash and `r` back. § 3 also says "Docs (5)" before a list of six files.
- **CR1-02** (nit) `backend/tests/test_pm_alerts.py:151`: the re-arm test moves the due date through
  `pm_generate` only; one more test through S101's reschedule route (`POST /api/pm/jobs/<id>/reschedule`, then
  *due* again at the new date, the markers untouched by the route) would pin the § SMTW-Review point that a
  due-point move writes `due_on` / `due_meter` and never the markers.
- **CR1-03** (nit) `backend/alerts_core.py:219`: the docstring of `_point_words` opens with four quotes
  (`""""on 20-11-2026", …`); start it with a word, e.g. `"""The due point in words: "on 20-11-2026", …`.

## The impl report's decisions

- **D-1** (`pm_markers` in the pure core): sound. The rule "*overdue* writes all four markers" now sits in the
  core with its own test (`TestPmAlertDue::test_the_markers`); `_mark_alerted` builds its `SET` from the
  constant column names of `_PM_MARKERS`, never from input, so it is no SQL built from strings.
- **D-2** (`SCRAPPED` from `equipment_core`): consistent; `pm_jobs.py` already uses the same constant.
- **D-3** (`alerts.py` takes the PM keys from `alerts_core`): one place names them for the alerts; no cycle.
- **D-4**, **D-5**, **D-6**: small and stated; D-6's Plan.MD rows match the code.
- **Red, then green.** The core tests were not shown red against missing code. The coder's rule
  (`.claude/agents/coder.md`, *Red, then green*) applies to a fix round's `Fixed` findings, not to round 1, so
  this is no finding. The two red runs the coder made (the scrapped rule taken out) show the shell tests do
  catch that rule.
- **The re-arm test** moves the due date through `pm_generate`, not a plan save through the API. Both reach
  `settle_plan_job` → `_refresh`, so the coverage is the same; CR1-02 asks only for the reschedule route.

## Checked and found consistent

- **Migration v56** (`backend/local_db.py:1504`): four nullable columns, `DATE` / `DECIMAL(14,3)` as `due_on` /
  `due_meter`, `ADD COLUMN IF NOT EXISTS`, after `needs_verification`, appended last. No `_PRECONDITIONS` entry is
  right: `pm_jobs` (v52) was never released. `test_migration_v56.py` checks the order, the types, a v55 database
  with a due job (all other columns unchanged, schema equal to a fresh build) and a re-run.
- **Schema docs**: `notes.json`'s `pm_jobs` line names the markers; `schema.json` and `schema-data.js` carry
  migration 56 and the four columns; the check exits 0.
- **The markers keyed on the due point**: `due_point_alerted` compares both values (`Decimal` by value; both
  NULL = never sent). A plan edit (`_refresh`), S101's reschedule (`job_changes` writes only the copies and
  `assignee_id`) and a save that drops a reschedule write `due_on` / `due_meter`, never the markers, so the alerts
  re-arm. A skip's next job is a new row with NULL markers. A changed window or offset alone moves nothing. A
  job with neither a date nor a meter value stands *Not yet* (`job_state`), so it never alerts daily on its NULL
  markers.
- **The candidates** (`pm_jobs._ALERT_CANDIDATES`): a superset of the jobs `pm_alert_due` can answer for: state
  `due`, *overdue* not sent for this point (`<=>` covers the NULL halves), and a meter due value or a date
  reached; `job_state` reaches *Due* by date only from `due_on`, and by meter only with `due_meter` set.
- **The scan's locks** (`pm_jobs._alert_one`): one transaction per job; (6e) `LOCK_PLAN` the first statement,
  (6f) `LOCK_JOB` next, then `SELECT NOW()` (no table) and the plain reads (lifecycle, `last_readings`), so the
  snapshot starts after both locks. The decision uses the locked plan and job rows. This matches the LOCK ORDER
  notes of `equipment.py` ((6e), (6f)) and `pm_jobs.py`, which both gain the S102 line. The scan takes no node,
  counter, meter or person lock, so no cycle with the routes or `pm_generate`.
- **Failures** (`alert_scan`): a job's exception rolls that job back alone (no marker, no task), is logged with
  `logger.exception` and counted; the handler then raises `RuntimeError` naming the jobs, so the task retries
  and the marked jobs are no candidates (`TestAllOrNothingPerJob`). A lost connection is raised at once; a stop
  gives `RetryLater` with `PM_STOPPED_RETRY_SECONDS`. No exception is swallowed.
- **The task `pm_job_alert`**: `_ids` and the kind are checked first (`BadTask`); a missing job is `BadTask`;
  `should_send_pm` re-checks the state, the plan's `active`, the node's lifecycle and the kind's marker against
  the due point now; push off logs and ends; else the `push_send` rows go in the worker's transaction with
  `done` (one commit, so a retry never doubles them). `push_send` is unchanged, so a send task still records
  its failure on its own row (CLAUDE.md § Notifications). The payload holds `{kind, job_id}` only: no person,
  no address.
- **Recipients** (`alerts.pm_job_recipients`): `people_at_unit` at the job's site covering the node's current
  root unit (`JOB_FROM`'s `unit_id` / `site_id` through `NODE_JOINS`), as the list's predicate. *Due*: the
  assignee among the `pm_job:read` holders, so an assignee who left the unit or is inactive is left out
  (tested). *Overdue*: that plus the `pm_job:verify` holders (engineer; manager through `ROLE_INCLUDES`),
  merged and sorted. Every verify holder holds `pm_job:read`. A contractor has no `push_subscriptions` row, so
  no device; admin and IT admin hold no membership, so they are never recipients. The test's `people` fixture
  gives an engineer of another unit, a supervisor and an operator a device each, and the exact device lists
  leave them out.
- **The texts**: § 5.6's two texts exactly, the meter and *both* forms, "not assigned", the 80-character cut
  (`TestPmTexts`). They hold the serial, the plan title, the site, unit and machine codes, the due point, the
  window end and the assignee's first name: all of them visible to a `pm_job:read` holder at the unit. No
  result, remark or reading. The due meter is the counted value, as the list shows it (`job_item`'s
  `due_meter`).
- **Quiet, TTL, tag, path**: `quiet: True` (Urgency `low`), `PM_TTL_SECONDS` = 86400, tag `pm-job-<id>` for both
  kinds, path `/pm/jobs/<id>`; asserted on the `push_send` payload and through the worker (`fake_send`).
- **No alert** for a started, done, skipped, verified or cancelled job, an inactive plan or a scrapped node:
  `pm_alert_due` and `should_send_pm` both check all three, with core tests for each state and shell tests for
  started, done, cancelled, inactive and scrapped.
- **The moves change no behaviour**: `pm_work._LOCK_JOB = pm_jobs.LOCK_JOB` is the same statement;
  `pm_work._job_row` calls `pm_jobs.job_row`, the same query; `jobs_out` calls `job_standing`, which adds
  `meter_offset` exactly as the two lines it replaces; `READ_KEY` has one copy in `pm_jobs_core`, re-used by
  `pm_jobs.py` and `pm_work.py`. The *run whole* tests of brief § 8.3 pass in the full backend run.
- **Schedule and Settings**: `("pm_job_alert_scan", "08:00")` last in `SCHEDULE`, with its comment; the
  `HANDLERS` entries; the task label "Send the PM alerts: jobs due today and jobs overdue" (scope B: starts with
  a verb, plain words), asserted in `settings.spec.js`.
- **What you will get**: "Overdue PM jobs at <place>" after the verify line for a `pm_job:verify` role, and
  "PM jobs assigned to you, when due and when overdue" once after "Jobs assigned to you" for an assignable role
  in a membership with a place. A manager without units gets no PM line. The four `TestYouGet` lists,
  `test_push_api.py` and `notifications.spec.js` (the technician's exact list) assert them.
- **Pure core, thin shell**: every rule (`due_point_alerted`, `pm_alert_due`, `pm_markers`, `should_send_pm`,
  the facts and texts, `job_standing`) is pure, in `alerts_core` and `pm_jobs_core`; the shell reads, locks and
  stores. The imports go pure → pure; `alerts.py` never imports `pm_jobs.py`.
- **Security**: no route is added or changed; no actor is taken from anywhere; SQL is parameterised (the two
  f-strings hold only constants).
- **The database down**: the scan and the task run only in the worker, which reconnects; a lost connection
  is re-raised. No request path changes.
- **Docs**: `.claude/CLAUDE.md` § Notifications (the PM part) and § SMTW-Review (the point from brief § 9, word
  for word); `docs/Plan.MD` § 4.7 (two rows and the *PM alerts* bullet); `docs/steps/device-checks.md` rows 67 and
  68, as brief § 8.5 (set-up, account, network, where; both important). `docs/Maintenance-Philosophy.md`,
  `docs/Plant-Facts.md`, `docs/Keycloak.md` and `example_secrets_app.py` need no change, as the report says.
- **Manual checks**: the report's section has both important device checks as unticked boxes and the two
  automated checks as `[auto]` with their passing tests.
- **Scope**: nothing built beyond the brief; no change to the PM list, the job page, the card or the service
  worker. Track `full` is right.

## Manual browser checks for the user

None in a browser. The two device checks stay open, on production on the TEST machine at SMTW.MCC2 after the
deploy:

- [ ] Row 67: *PM job due* on the technician's phone after 08:00 on the due date, quiet; the tap opens the job
  page; the engineer's phone shows nothing.
- [ ] Row 68: *PM job overdue* on the technician's and the engineer's phones two days after the due date; on the
  technician's phone it replaces *PM job due*.

## Feedback

- idea: the impl report carried three raw CR bytes where a Python string turned `\r` in `tooling\run-…` into a
  carriage return; `tooling/step-check.bat` could flag a lone CR byte in a step file (found only by a byte
  check, 2 tool calls).
- hindrance: `cmd //c "tooling\schema-docs.bat check" | tail` hides the wrapper's exit code (the `$?` after the
  pipe is `tail`'s), so the PASSED line is the only evidence; a note in README § Shell on Windows would help
  (1 call).
