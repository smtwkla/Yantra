```
Step: S084 — Contract reminders
Doc: impl report
Author: Coder (Opus)
Date: 31-10-2026
```

# S084 — implementation report

**S084 is built as the brief says, with two small departures in a signature and a helper (Decisions D-a, D-b).**
The unit suites are green: backend 4452, frontend 397, tooling 231. The schema docs check exits 0 and the build
passes. The whole browser suite at Normal has 349 passed, 15 skipped and 2 failed; the 2 failures are the known
S048 changelog fault outside this step (`e2e/changelog.spec.js:14`, desktop-chromium, the empty 0.1.14 section in
`CHANGELOG.md`). BR1-02 (where the device checks run) and BR1-03 (constants 60/15 and v46 against R02.5's text)
are coded with the brief's recommended options and stay KLA's decisions at gate B.

## 1. What was built

- **Two reminders per vendor contract:** the first when the contract has 60 days or fewer left, the second at 15
  days or fewer, each once per To date. None for an inactive contract, one not started, one ended, or one renewed
  (another active contract names it in `renewal_of_id`).
- **Push**, quiet and kept 24 hours, to the holders of `contract:read` at the contract's site (engineers and
  managers, whatever their units). Title "Contract ends in 60 days · SMTW", body "<title> · <vendor> — ends on
  31-03-2027. Renew it, or let it end."; the tap opens `/contracts/<id>`; tag `contract-<id>`, so the second
  replaces the first.
- **Email** to the holders of `contract:read_senior` at the site with an address (managers): subject "Contract
  ends on 31-03-2027: <title> (SMTW)", body with vendor, type, contract number (left out when empty), site,
  period and the link. No price, cost note or call-out number in any text.
- **Daily task** `contract_reminder_scan` at 08:00 IST, listed in Settings › Background tasks as "Send the
  contract reminders: contracts ending in 60 or 15 days — daily at 08:00".
- **Migration v46:** `contracts.first_reminder_for`, `second_reminder_for` (DATE NULL, after `to_date`).
- ***What you will get*** gains "Contracts ending at <site>" (holders of `contract:read`) and "Contracts ending
  at <site>, by email" (holders of `contract:read_senior`), also for a membership without units.

## 2. How it works

- **Pure core (`alerts_core`):** `contract_reminder_due` decides FIRST, SECOND or None from the row (§ 5.1's table,
  `!=` against the markers). `should_send_contract` re-checks at send time (active, not renewed, started, To date
  still the payload's, not ended). `contract_facts` builds the facts from `contract:read_basic` fields only;
  `contract_text` / `contract_message` make the push. `FIRST_REMINDER_DAYS` is `contracts_core.ENDING_SOON_DAYS`.
- **Scan (`task_handlers.contract_reminder_scan`),** one worker transaction: `SELECT NOW()`; one plain read of the
  candidates (`alerts.contract_scan_candidates`, § 5.3's query with the BR1-12 narrowing); per candidate in id
  order the row `FOR UPDATE` (`lock_contract_for_scan`), the renewal read plain (`contract_renewed`), the decision
  from the locked row, the marker `UPDATE` (no `updated_*`) and one `contract_alert` task. A fault rolls back
  markers and tasks together; the queue retries.
- **Alert (`task_handlers.contract_alert`):** validates the payload (`_ids`, kind in `CONTRACT_KINDS`, `to_date`
  through `_payload_time`, which now names the task), reads the contract plain with its `renewed` flag
  (`read_alert_contract`), checks `should_send_contract`, then per channel in `CHANNELS`: push through
  `_push_to_people` with `CONTRACT_TTL_SECONDS`; email through `contract_ending_email` and `alerts.enqueue_email`
  per person. A channel not set up is skipped with a log line.
- **Recipients:** `people_at_unit`'s SQL moved into a private `_people_with_role(…, unit_ids, …)`; `unit_ids=None`
  leaves out the unit condition. `people_at_unit` (unchanged result) and the new `people_with_role_at_site` call
  it. `contract_recipients` picks the key by channel (`CONTRACT_AUDIENCE_KEY`) through `roles_holding`.
- **API:** `contracts._contract_out` deletes the two markers, so no answer changes.

## 3. Files touched

Code (10):
- `backend/alerts_core.py` — the contract kind, channels, audience keys, reminder days, path, the five functions,
  `you_get`'s two lines, the docstring.
- `backend/alerts.py` — `CONTRACT_ALERT`, `CONTRACT_SCAN`, the shared private recipient query,
  `people_with_role_at_site`, the six contract functions, the docstring (scan locks).
- `backend/task_handlers.py` — `contract_reminder_scan`, `contract_alert`, `HANDLERS`; `_payload_time` takes the
  task name.
- `backend/scheduled_tasks.py` — the 08:00 entry.
- `backend/push_core.py` — `CONTRACT_TTL_SECONDS`.
- `backend/email_core.py` — `contract_ending_email`.
- `backend/local_db.py` — migration v46.
- `backend/contracts.py` — `_contract_out` drops the markers; the LOCK ORDER note.
- `backend/equipment.py`, `backend/documents.py` — LOCK ORDER docstrings only.
- `frontend/src/views/SettingsView.vue` — `TASK_LABELS` entry.

Tests (9):
- `backend/tests/test_alerts_core.py` — channels, days, `contract_reminder_due` (14 cases), `should_send_contract`,
  texts and message, `you_get` updates and the manager-without-units case.
- `backend/tests/test_email_core.py` — `contract_ending_email` (exact text, no number line, day 0, one-line subject).
- `backend/tests/test_access_core.py` — `roles_holding` of the two contract keys.
- `backend/tests/test_contract_alerts.py` (new) — not in the API, scan, renewed, re-arm, all-or-nothing, handler
  push/email/no-units/no-longer-true/channels off, through the worker, bad tasks.
- `backend/tests/test_migration_v46.py` (new) — fresh, a v45 database with a contract, re-run.
- `backend/tests/test_scheduled_tasks.py`, `backend/tests/test_push_api.py` — the new entry and line.
- `frontend/e2e/notifications.spec.js`, `frontend/e2e/settings.spec.js` — the two lines and the new task test.

Docs: see § Docs updated.

## 4. Decisions taken

- **D-a. `contract_scan_candidates(cur, today)`** computes `until` and the 15-day bound itself, instead of the
  brief's `(cur, today, until)`. One caller; the bounds are the core's constants, so passing them in only splits
  the rule.
- **D-b. The email's "ends in 60 days" words** are made in `email_core` from `status_label` (one line), as the brief
  says `email_core` imports nothing new; `alerts_core` has its own private `_ends_words` for the push title. Two
  one-line lower-casings instead of a new import or a new facts key.
- **D-c. `_RENEWED`**, one SQL fragment shared by `contract_renewed` and `read_alert_contract`, so the rule of
  § 5.2 is written once.
- **D-d.** `task_handlers` imports `settings.label_base_url` for `contract_facts`, as the brief's step 5 reads;
  `alerts.read_alert_improvement` builds its facts inside `alerts`, but the brief puts the facts in the handler.
- **D-e. Test set-up:** the API refuses a membership with no units, so the no-units manager is made with all units
  and then set `all_units = 0` through `db_rows` (§ 8.2's "all_units = 0, no person_units").
- **D-f. Re-arm test:** the clock cannot move, so "30 days on" is shown by setting the To date back to 60 days left
  and the marker to the old To date (30 days before it). It tests the same `!=` rule.

## 5. Not done, deferred or assumed

- Nothing of the brief left out.
- **Assumed:** BR1-02 and BR1-03 as recommended (production at SMTW for rows 61–62; constants and v46). KLA decides
  at gate B.
- The scan reads every contract of the kept test database; the tests assert only on their own contracts, and the
  all-or-nothing test runs one scan first, as `test_improvement_alerts.py` does.

## Tests run

- While coding: `tests/test_alerts_core.py`, `test_email_core.py`, `test_access_core.py`, `test_scheduled_tasks.py`,
  `test_push_api.py`, `test_contract_alerts.py`, `test_migration_v46.py`, then with `test_alerts.py`,
  `test_closed_email.py`, `test_improvement_alerts.py`, `test_contracts_api.py`, `test_worker.py`,
  `test_settings_api.py` (239 passed).
- Final: `YANTRA_TEST_RUN=s084c1 tooling/run-tests.bat`: backend 4452 passed, frontend 397 passed, tooling 231
  passed.
- `npx vite build`: built (the known chunk-size warning only).
- `tooling\schema-docs.bat write`, then `check`: exit 0, "Schema docs at migration v46: 4 passed".
- Browser: the new test alone (`e2e/settings.spec.js -g S084`, phone-chromium, 1 lane): 1 passed. Targeted
  `e2e/notifications.spec.js e2e/settings.spec.js e2e/screens.spec.js` (the screens the step changed, plus
  screens): 36 passed, 4 skipped. Whole suite at Normal once, at the end: 349 passed, 15 skipped, 2 failed (the
  known S048 changelog tests on desktop-chromium, `e2e/changelog.spec.js:14`, it_admin and admin).

## Manual checks

- [auto] The engineer's *What you will get* shows "Contracts ending at SMTW" — `frontend/e2e/notifications.spec.js`::"S021 A1: What you will get — the engineer's breakdowns and defects, the technician's assigned jobs"
- [auto] The manager's *What you will get* shows "Contracts ending at SMTW, by email" — `frontend/e2e/notifications.spec.js`::"S032: the manager sees the closed-ticket email line and their address; Send test email says it is on its way"
- [auto] Background tasks lists "Send the contract reminders: contracts ending in 60 or 15 days — daily at 08:00" — `frontend/e2e/settings.spec.js`::"S084: Background tasks lists the contract reminders at 08:00"
- [ ] **Important.** Device-check row 61: the engineer's phone shows *Contract ends in 29 days · SMTW* without sound after 08:00, a tap opens the contract; after the To date is moved to 10 days, *Contract ends in 9 days · SMTW* replaces it (production at SMTW, IT Admin; where it runs is KLA's choice at gate B).
- [ ] **Important.** Device-check row 62: KLA's Outlook holds the reminder email on both mornings, not in junk, with vendor, type, site and period, no price and no call-out number, and a working link (KLA only).

## Docs updated

- `docs/schema/notes.json` — the `contracts` line names the two markers (S084, v46); then `schema-docs.bat write`
  regenerated `docs/schema/schema.json` and `docs/schema/schema-data.js` (migration 46); `check` exits 0.
- `docs/Plan.MD` § 4.7 — the *Contract ending* row and the *Contract reminders* bullet.
- `.claude/CLAUDE.md` § Yantra Specifics, *Notifications (S021)* — the contract kind, its scan, markers and the
  shared recipient query; *Email* names the contract kind's email; § SMTW-Review — the *Contract reminders (S084)*
  point of brief § 9.
- `docs/steps/device-checks.md` — rows 61 and 62.

## Feedback

- hindrance: the Edit tool refuses a file read only through `cat` in Bash, so several edits needed an extra Read
  call first (about 8 calls; `alerts_core.py`, `contracts.py`, `local_db.py`, `1-brief.md`).
- waste: the unit suites ran while the whole browser suite held the CPU, so the backend took 321 s instead of
  about 40 s (`scratch/backend-tests-s084c1.log`); running them one after the other would have been faster.

## Fix rounds

### Round 1

- **CR1-01** (nit) — Fixed. `alerts.py` docstring: the scan's locks are now described once (the brief's sentence,
  with the plain candidate read and the reason for the plain renewal read). `equipment.py` LOCK ORDER bullet: the
  second description is cut to one short sentence on the scan. No test: comments only.
- **CR1-02** (nit) — Fixed. `alerts_core.contract_facts` now holds `ends_words` (the status label with its first
  letter lower-cased); `contract_text` and `email_core.contract_ending_email` both read `facts["ends_words"]`.
  `_ends_words` and the second lower-casing are gone. `email_core` imports nothing new. The existing text tests
  (`test_alerts_core.py`, `test_email_core.py`, `test_contract_alerts.py`) cover the output and pass unchanged.
  No red run: a refactor with the same output.
- **CR1-03** (nit) — Fixed. `test_renewed_before_it_runs_sends_nothing` also asserts
  `email_sends(…) == []`. Red run not possible: the code already behaves so (the renewal check is in
  `should_send_contract`); the assertion only closes a gap in the test.

Tests: `YANTRA_TEST_RUN=s084c2 tooling/run-backend-tests.bat tests/test_alerts_core.py tests/test_email_core.py
tests/test_contract_alerts.py tests/test_closed_email.py` — 250 passed. No frontend or screen change, no browser run.

Docs updated: none, because only comments, one facts key and a test changed; no migration, key, secret or screen.

#### Feedback

- none
