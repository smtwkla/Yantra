```
Step: S084 — Contract reminders
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S084 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** S084 is built as the brief says. Round 1 has 0 blocker,
0 major, 0 minor and 3 nits. All unit suites pass (backend 4452, frontend 397, tooling 231), and the build passes.
The schema docs check exits 0
(`YANTRA_TEST_RUN=s084cr1 tooling\schema-docs.bat check`: "4 passed").

Reviewed: the step's diff on top of the S083 snapshot (`step_snapshot.py diff S084`, 26 files), read in
full for `alerts.py`, `alerts_core.py`, `task_handlers.py`, `email_core.py`, `contracts.py` (`_contract_out`, the
LOCK ORDER note), `local_db.py` v46, `test_contract_alerts.py` and `test_migration_v46.py`; the brief with its
Review log (r1, s1); the impl report.

## Nits

- **CR1-01** (nit) `backend/alerts.py:10-22`: the module docstring states the scan's locks twice (the coder's own
  sentence, then the brief's required sentence, which says the same); keep the brief's sentence and the reason
  for the plain renewal read, and drop the first description. `backend/equipment.py:73-78` repeats in the same
  way ("Only contracts.py's functions and the reminder scan … lock contracts rows", then "The daily
  contract_reminder_scan (S084) locks several contract rows …"); one sentence is enough there too.
- **CR1-02** (nit) `backend/email_core.py:419-420` and `backend/alerts_core.py` `_ends_words`: the same
  lower-casing of `status_label` is written twice (D-b). Put `ends_words` into `contract_facts` and read it in
  both texts, so a change to the label's form changes both at once.
- **CR1-03** (nit) `backend/tests/test_contract_alerts.py:340-345` `test_renewed_before_it_runs_sends_nothing`:
  it asserts only that no `push_send` is queued; also assert `email_sends(…) == []`, as
  `test_no_longer_true_sends_nothing` does.

## Points the orchestrator asked about

- **The scan's transaction and locks — consistent.** One worker transaction (`test_alerts.run`'s pattern is the
  worker's): `SELECT NOW()`, one plain read of the candidates, then per candidate in id order
  `lock_contract_for_scan` (one row per statement, `FOR UPDATE`), the renewal read plain, the decision from the
  locked row (`contract_reminder_due`), the marker `UPDATE` on the held row and the `task_queue` insert. A fault
  rolls back the markers and the tasks together (`TestAllOrNothing`), and the queue retries (a 1213 included).
  Every other lock of a contracts row (`contracts.py:425`, `:449`) is one row, taken first; no route holds a
  contract row and then waits on a second one, and the scan takes no vendor, node, line, ticket or person
  lock, so there is no cycle. The plain renewal read is explained (the gap lock R02.4's insert would meet), and
  the alert task re-reads the renewal before it sends.
- **LOCK ORDER notes — updated** in `contracts.py`, `equipment.py`, `documents.py` and `alerts.py`, with the
  brief's sentences (wording repeats: CR1-01).
- **Once per To date — consistent.** `contract_reminder_due` compares each marker with `!=` against the To date;
  the scan writes the To date it reminded for. The re-arm table of § 5.1 holds: a later To date gives the first
  again inside 60 days; an earlier one inside 15 days gives the second (`TestReArm`, 14 core cases).
- **Inactive and renewed — never reminded,** at the scan (`active = 1` in the candidates, `contract_reminder_due`)
  and again at send time (`should_send_contract`, `read_alert_contract`'s `renewed`). A renewal set inactive does
  not silence the old contract (`_RENEWED` checks `r.active = 1`; `test_an_inactive_renewal_does_not`).
- **Recipients — consistent.** Push to `roles_holding("contract:read")`, email to
  `roles_holding("contract:read_senior")` with an address, at the contract's site, with no unit condition
  (`people_with_role_at_site`). `people_at_unit` keeps its result: the early `[]` for no units moved in front of
  the shared `_people_with_role`. The manager with `all_units = 0` and no `person_units` gets both
  (`test_a_manager_with_no_units_gets_both`); the technician and the other site's manager get nothing.
- **No price, cost note or call-out number in any text.** `_ALERT_CONTRACT` selects none of them, and
  `contract_facts` builds its dict from named fields only (`test_no_callout_number_or_cost_note`).
- **Markers left out of the API.** `_contract_out` deletes both; the list, the detail and the card all go through
  it (`TestNotInTheApi`).
- **Payloads carry ids.** `contract_alert`'s payload is `{kind, contract_id, to_date}`; `email_send` gets the
  person id (`enqueue_email`); the test asserts no `@` in the email payload.
- **No real service, no real address.** The handler tests stop at the `push_send` and `email_send` rows; the
  worker test fakes `push_sender.send` and `mail_sender.send`. The only addresses are `@example.test`. The repo
  gains no SMTP value. The link base in tests is the public service URL, which the rule allows.
- **Push off, email off.** Each channel is skipped with a log line; the markers are written all the same (D7;
  `test_both_off_no_rows_and_the_scan_still_marks`).
- **Migration v46 and `_PRECONDITIONS`.** Two nullable `DATE` columns, `ADD COLUMN IF NOT EXISTS`, after `to_date`.
  No precondition is needed: no existing value changes, and production holds no contract before this release
  (v43 ships with it). `test_migration_v46.py` covers a fresh database, a v45 database with a contract, and a
  re-run. `schema-docs check` exits 0.
- **Departures.** D-a (`contract_scan_candidates(cur, today)` computes its bounds from the core's constants) and
  D-b (two lower-casings, CR1-02) are small, stated, and change no behaviour. D-c (`_RENEWED` shared) is DRY.
  D-d (the handler builds the facts, so `task_handlers` imports `settings.label_base_url`) follows the brief's
  step 5; `alerts.py` already imports the same module, so no new import direction appears. D-e and D-f are test
  set-ups that test the stated rules.
- **Scope-B texts.** "Contract ends in 60 days · SMTW", "… — ends on 31-03-2027. Renew it, or let it end.", the
  email's subject and body, "Contracts ending at SMTW", "Contracts ending at SMTW, by email" and the Background
  tasks label match the brief, use DD-MM-YYYY, and are short and plain. "Renew it" fits both push audiences:
  engineers and managers both hold `contract:edit`.

## Tests

- `YANTRA_TEST_RUN=s084cr1 tooling\run-tests.bat`: backend PASSED, 4452 passed (312 s, run beside the schema docs check); frontend PASSED, 397 passed; tooling PASSED, 231 passed.
- `npx vite build` in `frontend/`: built (the known chunk-size warning only).
- `YANTRA_TEST_RUN=s084cr1 tooling\schema-docs.bat check`: exit 0, "4 passed".
- Browser: not re-run; no finding of mine needs a browser run. The coder's targeted run names the right specs
  (`notifications.spec.js`, `settings.spec.js`, `screens.spec.js`: 36 passed, 4 skipped), and its whole run at
  Normal (349 passed, 15 skipped, 2 failed) fails only in `e2e/changelog.spec.js:14`, the known S048 changelog
  fault outside S084. The three *Automated* checks each have a test that asserts the text the user sees. The
  new test is untagged, which is right: it is a logic test.
- The brief's § 8 list is covered, including the failure modes (all-or-nothing, no longer true, channels off,
  bad tasks, the narrowed candidates).

## Manual checks

The impl report's `## Manual checks` carries every important check of the brief: three `[auto]` with their tests,
and device-check rows 61 and 62 as unticked boxes. The rows are in `docs/steps/device-checks.md`. Still for the
user (where they run is KLA's choice at gate B, BR1-02):

- [ ] Row 61: the engineer's phone shows *Contract ends in 29 days · SMTW* without sound, and the tap opens the
  contract; after the To date moves to 10 days, *Contract ends in 9 days · SMTW* replaces it.
- [ ] Row 62: KLA's Outlook holds the reminder email on both mornings, not in junk, with no price and no call-out
  number, and a working link.

Also for KLA at gate B: BR1-03 (the constants 60 and 15, and v46, against R02.5's text).

## Checked and found consistent

- The docs pass: `notes.json` names the two markers, and `schema.json` and `schema-data.js` are regenerated
  (check exit 0); `Plan.MD` § 4.7 has the row and the bullet; `.claude/CLAUDE.md` *Notifications* and
  § SMTW-Review carry the brief's point; device-check rows 61 and 62. No secret, role, key or Keycloak change,
  so `example_secrets_app.py` and `Keycloak.md` are not due.
- `KINDS`, `CHANNELS`, `HANDLERS`, `SCHEDULE` (after `improvement_alert_scan`), `CONTRACT_TTL_SECONDS` (24 hours,
  quiet, its own name) and `CONTRACT_PATH`.
- `you_get`: the contract lines use the site code, come before the `continue` for a membership without units,
  and `keys_with_place.update` stays after it (BR1-07).
- `_payload_time` takes the task name; both improvement callers pass `alerts.IMPROVEMENT_ALERT`.
- Pure core, thin shell: the rules (`contract_reminder_due`, `should_send_contract`) and the texts are pure; the
  handlers fetch, call and store. The marker column name in `mark_contract_reminded` comes from a fixed dict, not
  from input. No route changed, so no permission gate changed.
- The database down: the scan runs in the worker, and a missed day runs once when the database is back.
- Track: full, as the step's migration and locking need.

## Feedback

- none
