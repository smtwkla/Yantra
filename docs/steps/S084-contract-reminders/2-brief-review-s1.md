```
Step: S084 — Contract reminders
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080, S081, S082, S083 (S083 in code review; its code may still change)

**Verdict: no blocker or major finding is open.** Two minor findings and four nits. The brief's design holds
against the code as it stands: the names, the migration number (v46), the keys and their holders, the lock
notes, the alert pattern and the tests it relies on all match. The one real change is in `contracts.py`:
`_contract_out` sends `c.*`, so the brief's assumption A4 (named fields only) no longer holds and the coder
must leave the two new columns out there (BS1-01). The new device-check rows of S082 and S083 add a fact to
KLA's pending decision BR1-02 (BS1-02); the decision itself is not re-made here.

Facts file read: `scratch/brief-facts-S084.md` (re-run today). Diff read: `git diff --stat d216f48` (55 files)
plus the untracked S079–S083 files. The alert files (`alerts.py`, `alerts_core.py`, `task_handlers.py`,
`scheduled_tasks.py`, `push_core.py`, `email_core.py`, `worker.py`, `task_queue.py`) and their tests are
unchanged since the baseline, so every `file:line` the brief cites in them still holds.

Where a finding depends on S083's code: BS1-03 quotes the LOCK ORDER text S083 wrote in `contracts.py` and
`equipment.py`; S083's code review may reword it. Nothing else below depends on S083.

## Findings

### BS1-01 — minor — § 3, § 6, § 9 A4: `_contract_out` sends every column, so v46's columns would reach the API

**Problem.** The brief assumes (A4) that "S080's `_contract_out` sends named fields only, so the new columns
stay out of the API; otherwise the coder leaves them out there". The code does the opposite:
`_contract_row` selects `c.*` (`_CONTRACT_SELECT`, `backend/contracts.py:102-113`), and `_contract_out`
(`:157`) does `row_to_dict(row)` and then deletes named fields (`renewal_of_id`, and the gated ones). After
v46, `first_reminder_for` and `second_reminder_for` would appear in every list row, the detail, and every
write's answer (`_answer`). The card (`_CARD_KEYS`) and the removed-documents branch name their keys, so they
are not affected. No existing test pins the answer's key set (`test_contracts_api.py` has no `set(item)` or
`body ==` assertion), so nothing would turn red.

**Why it matters.** § 6 says "No new route and no changed answer"; without a change in `contracts.py` that
is false, and § 3 says `contracts.py` changes "docstrings only". The coder would have to decide alone.
S085's brief (approved, § 3) already describes `_contract_out` as "it deletes `renewal_of_id` from the
answer", so the pattern for a column kept out of the API exists.

**Options.**
- **(a) Recommended.** `_contract_out` also deletes `first_reminder_for` and `second_reminder_for`, beside
  `del item["renewal_of_id"]`, with a one-line comment (the markers are the scan's, S084). Update § 3
  (`contracts.py`: the two `del`s and the docstring; the file count stays 19 code and test files, as
  `contracts.py` is already listed), § 6 (unchanged answers, because `_contract_out` drops them) and A4
  (state the fact, not the assumption). Add one assertion to `test_contracts_api.py` (the GET detail and a
  list row hold neither key) or to `test_contract_alerts.py` after a scan has set a marker.
- (b) Leave the columns in the API. Harmless dates, but the brief's "no changed answer" and the
  frontend's typed fields say otherwise, and a later step would wonder whether they are meant to be there.

### BS1-02 — minor — § 8.5, § 9 Q4 (BR1-02, KLA's decision): two newer device-check rows set a precedent for the test contract

**Problem.** Since the brief was approved, S082 and S083 added rows 59 and 60 to
`docs/steps/device-checks.md`. Both put the test contract on the **dev server only**: row 59 says "never
production: a contract cannot be deleted", row 60 "never production" (its quote holds a real price). § 8.5
and Q4 (a), the recommended option, add a TEST contract in **production** at SMTW and set it inactive
afterwards. The brief's reasoning still holds (push needs HTTPS and the VAPID keys, which the dev server has
not; the title says "TEST … not a real contract"; it is set inactive), but the two rows now state the
opposite practice for contracts, and KLA decides BR1-02 at gate B without seeing them unless the brief says
so.

**Why it matters.** This is a fact for the decision the user owns, not a new finding on the design: an
inactive TEST contract stays in production's register for good (visible under *Include inactive* in
Masters › Contracts, and in the vendor's contracts), which is exactly what rows 59 and 60 avoided.

**Options** (for KLA at gate B; the brief's Q4 already lists them):
- (a) Production at SMTW, as § 8.5 is written: the only end-to-end push check; one inactive TEST contract
  remains in production. Add a sentence to Q4 (a) naming rows 59 and 60 and the leftover row, so the choice
  is made knowingly. **Recommended as the brief's text change**, whatever KLA chooses.
- (c) The email row on the dev server (as S032 row 30), the push row in production: the same leftover
  contract, since push cannot run on the dev server.
- (b) A test site: unchanged from the brief (none exists).

## Nits

- **BS1-03** (nit) § 5.5, last paragraph: the phrase to change is not "Only contracts.py locks contracts …
  rows". `equipment.py:73-75` reads "Only contracts.py's functions lock contracts and contract_equipment
  rows (documents.py calls lock_contract_for_change, S083), and they take nothing exclusive outside them,
  so they add no lock cycle", and `contracts.py:53-55` reads "The contract row: only this module's
  functions lock it, always first in their transaction (the PUT, the three line writes, and documents.py's
  writes through lock_contract_for_change); nothing holds another lock and then waits on it." Quote these
  two sentences as the ones the coder extends with the scan. (Depends on S083's code review, which may
  reword them.)
- **BS1-04** (nit) § 3 Backend, § 5.5: `documents.py`'s LOCK ORDER note (`backend/documents.py:54-60`)
  says a document write "waits on the contract row only, behind a writer that finishes". Still true with
  the scan (it finishes too), but the note names who else holds that row; add `documents.py` to the
  docstring-only list, with "or the reminder scan (S084)" in that sentence.
- **BS1-05** (nit) § 8.2, Fixtures: `test_improvement_alerts.py` calls the handler through its `run`
  helper, `run(improvement_alert_scan, None)` (`:111`), not `improvement_alert_scan(conn, None, …)`; name
  the helper so the coder copies the right pattern.
- **BS1-06** (nit) § 9 A3 and § 5.5: S083 is coded, no longer "Draft": v45 is its migration
  (`local_db.py:1506`), its document writes lock the contract row first through `lock_contract_for_change`
  → `_lock_contract(cur, contract_id, key)` (`contracts.py:570-575`), then only `equipment_documents` rows.
  Replace "(S083 § 5.4, Draft)" and "still Draft" with the file names.

## Checked and found consistent

- **Migration number:** `_MIGRATIONS` ends at v45 (S083, `local_db.py:1506`); v46 is free. S085's brief
  (approved) takes v47 and names v46's two columns, `alerts.contract_renewed` and the renewed rule as S084
  states them (S085 § 5.6: "S084's rule stays"), and sets both markers NULL on a renewal. `_PRECONDITIONS`
  has no entry past v34.
- **The `contracts` table (v43):** `from_date` and `to_date` are `DATE NOT NULL` (so § 5.1's arithmetic
  never meets NULL), `active TINYINT(1)`, `renewal_of_id INT NULL` with `ix_contracts_renewal_of` and
  `fk_contracts_renewal_of`, `title VARCHAR(100)`, `contract_number VARCHAR(60) NULL`, `contract_type`
  ENUM of the four types, `site_id`, `vendor_id`, `updated_at` / `updated_by`. `vendors.name` and
  `vendors.active` exist (`_CONTRACT_SELECT` joins them).
- **`contracts_core`:** `ENDING_SOON_DAYS = 60` (`:29`, with the comment "R02.5 may make it a setting,
  § 9 A3"); `contract_status(from_date, to_date, today)` → `{kind, label, days}` with the labels "Ends
  today", "Ends in 1 day", "Ends in N days", `days <= ENDING_SOON_DAYS` (`:182-191`); `CONTRACT_TYPES`
  (`:16`); `TYPE_SHORT` (`:225`) with "AMC"; imports only `masters_core` → no cycle when `alerts_core`
  imports it.
- **Keys and holders:** `contract:read_basic ("*",)`, `contract:read ("maint_engineer",)`,
  `contract:read_senior ("maint_manager",)`, `contract:edit ("maint_engineer", "it_admin")`; all four in
  `SITE_SCOPED`. `roles_holding` (`access_core.py:65`) expands `ROLE_INCLUDES` and returns `SITE_ROLES`
  order, so `("maint_manager", "maint_engineer")` and `("maint_manager",)` as § 8.1 expects. IT admin holds
  `contract:edit` by token, not `contract:read`, as § 5.6 says.
- **`contracts.py`'s real names:** `_contract_row(cur, contract_id)`, `_lock_contract(cur, contract_id,
  key=EDIT)`, `_contract_out(row, flags, today)`, `_SiteFlags.at(site_id)`, `auth_utils.has_perm_at` /
  `sites_holding`; the brief cites none of them wrongly (it cites `_contract_out` only in A4, BS1-01).
  `validate_contract` ignores unknown fields, so a PUT that echoes the new columns is harmless.
- **LOCK ORDER:** `contracts.py` takes at most one contract row FOR UPDATE, first in every write on an
  existing contract (`:29-32`); a create locks the site and the vendor shared and no contract row; the
  vendor and site writers in `masters.py` wait on no contract row. `documents.py`'s contract path holds the
  contract row and no node (`contracts.py:60`). `equipment.py:59` lists the contract row unnumbered, as
  § 5.5 says. The scan's rows in id order, then markers and `task_queue` only, add no cycle.
- **Alert pattern (S074):** `KINDS = TICKET_KINDS + IMPROVEMENT_KINDS` (`alerts_core.py:38`), `CHANNELS`
  (`:58`), `IMPROVEMENT_AUDIENCE_KEY`, `IMPROVEMENT_PATH` (`:92`), `PAYLOAD_DATE` (`:94`), `you_get`
  (`:368`) with `if not place: continue` (`:386`) and `keys_with_place.update(keys)` (`:389`);
  `people_at_unit` SQL at `alerts.py:163-176`; `_push_to_people(cur, people, text, ttl)`
  (`task_handlers.py:153`); `improvement_alert` (`:229`) checks `push_sender.enabled()` after the
  should-send rule, as § 5.4 copies; `IMPROVEMENT_TTL_SECONDS = 86400` (`push_core.py:43`); `closed_email`'s
  `add` (`email_core.py:131`); `SCHEDULE` with two entries (`scheduled_tasks.py:12`) and the test that pins
  it (`test_scheduled_tasks.py:20`); `TASK_LABELS` (`SettingsView.vue:208`); `sw.js`'s `targetUrl` opens
  any same-origin path.
- **Tests named:** the `TestYouGet` tests, `TestChannels`, `test_push_on_with_the_public_key_and_what_you_get`,
  `TestTasksCard`, `add_device`, `fake_send`, `push_off`, `email_off`, `no_real_push`, `smtp_test_values`,
  `make_vendor`, `user_at_sites`, `db_rows` all exist; `conftest._TABLES` already lists `contracts` and
  `contract_equipment`; `test_migration_v45.py` uses the `V44 … range(20, 45)` / `V45 … range(20, 46)` pattern
  § 8.1 copies. The e2e titles "S021 A1: What you will get — …", "S032: the manager sees the closed-ticket
  email line …" and "S074: Background tasks lists the improvement alerts at 08:00" match.
- **Route:** `/contracts/:id(\\d+)` (`router/index.js:131`).
- **Docs:** `notes.json`'s `contracts` line exists; Plan.MD § 4.7's table has one row per kind and an
  *Improvement alerts* bullet (`:919`); `.claude/CLAUDE.md` gained S079 and S080 points in § SMTW-Review
  with no overlap with § 9's proposed point; the roadmap's R02.5 still says "lead days are settings" and
  "Migrations: none", so § 9's roadmap corrections remain due.
- **BR1-03** (constants and v46): nothing in the code changes its options; `ENDING_SOON_DAYS` is still a
  constant and S085 builds on v46.

## Feedback

- idea: `brief_facts.py` reported `targetUrl` as "not found" although `frontend/public/sw.js` defines it
  (`:38`); the *Code folders* setting leaves `frontend/public` out, so a brief citing the service worker
  gets a false miss. Add `frontend/public` to the setting, or have the tool look a file-qualified name up
  in the file the brief names (1 grep to check).
- hindrance: `git diff --stat d216f48` printed 38 CRLF warnings before the stat, and `git status --porcelain`
  truncates nothing but the diff did; the warnings double the output to read (one run, about 40 lines of
  noise).
