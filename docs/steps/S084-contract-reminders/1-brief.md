```
Step: S084 — Contract reminders
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: d216f48 + uncommitted R02 docs; S079–S083 coded before S084
Status: Draft
From: R02.5
```

# S084 — Contract reminders

## 1. What will be built

R02.1 (S080) gives each vendor contract a To date and a status *Ends in N days*; R02.2 (S081) gives
it a page. Nothing tells anyone when a contract is about to end: the manager must open the list.
**R02.5 adds two reminders per contract** (gate R, Q5.1 (a); Plan.MD § 2 item 9: "Reminders 60 and
15 days before the end (push to engineers and managers, email to managers), not once renewed"):

1. **First reminder**, 60 days before the To date: the morning the contract enters the last 60 days.
2. **Second reminder**, 15 days before the To date: the morning it enters the last 15 days.

Each is sent **once per To date** (§ 5.1). Neither is sent for an inactive contract, nor once the
contract is renewed (§ 5.2).

How they travel:

- **Push** to the holders of `contract:read` (from S080) at the contract's site, that is its
  engineers and managers (D10). Quiet, kept 24 hours by the push service (D6). A tap opens the
  contract page `/contracts/<id>` (from S081).
- **Email** to the holders of `contract:read_senior` (from S080) at the site, that is its managers,
  with an address (S032 channel). One plain-text email per manager.
- **Neither text carries the price, the cost note or the call-out number** (§ 5.4). Every recipient
  can open the contract page: `contract:read_basic` (`("*",)`, from S080) is held by every
  engineer and manager.
- A daily task **`contract_reminder_scan`** at **08:00 IST** (`scheduled_tasks.SCHEDULE`) finds the
  contracts due a reminder and queues one **`contract_alert`** task each.
- Two columns on `contracts` remember the To date each reminder was sent for: migration **v46**
  (§ 4). A changed To date re-arms both reminders without any route clearing them.
- ***What you will get*** (`alerts_core.you_get`) gains a push line for engineers and managers and an
  email line for managers, so the page and the fan-out agree (S021 BR2-06).
- **Settings › Background tasks** lists the new daily task with a plain label.

**After S084:** on 30-01-2027 the SMTW engineers and managers get *Contract ends in 60 days · SMTW*
for "Atlas Copco AMC 2026–27", and each SMTW manager gets the email "Contract ends on 31-03-2027:
Atlas Copco AMC 2026–27 (SMTW)". On 16-03-2027 they get the 15-day reminder, unless a renewal was
entered by then.

### Out of scope

- *Renew* (R02.4). Until R02.4 lands, nothing sets `renewal_of_id`, so every active contract gets
  both reminders. S084's rule already reads `renewal_of_id` (§ 5.2).
- A setting for the lead days or the scan's time (§ 7 D2, § 9 Q1).
- A reminder after the end ("ended yesterday"), or a repeat while nobody acts.
- Reminders about PM visits due under the contract (R02.7) or a vendor report (R02.8).
- A dashboard tile (phase 5).
- Any change to the contract page, the list, the card or the service worker. The service worker
  caches nothing and never will (§ Yantra Specifics, *Notifications*).
- Telegram (parked, Plan.MD § 4.7).

## 2. Standards and practice

- **ISO 55001 § 8.3, outsourcing** (Plan.MD § 2; the 2024 edition's number *to verify*). In plain
  words: work given to an outside firm stays the plant's responsibility, and the plant controls it.
  A contract that lapses unnoticed leaves the machines without the agreed maintenance.
- **ISO 9001:2015 § 8.4, control of externally provided services** (sub-clauses *to verify*). In
  plain words: the plant decides on its outside providers and reviews them. The reminder gives the
  manager time to review the vendor before renewing.
- **ISO 9001 § 7.4 / ISO 55001 § 7.4, communication.** In plain words: decide what is told, when, to
  whom and how. `alerts_core`'s tables are that decision; *What you will get* shows each person theirs.
- **ISO/IEC 27001:2022 A.8.3** (*to verify*) **and A.5.34.** In plain words: each person sees only
  what the job needs; personal data is kept only where needed. The texts carry no price and no
  call-out number; a reminder reaches only people who may open the contract; a payload carries
  ids, never an address (CLAUDE-COMMON § Conventions).
- **TPM, planned maintenance pillar.** In plain words: planned maintenance covers all work on a
  machine, whoever does it. A vendor's PM visits stop when the contract ends.

## 3. Where

S080–S083 are coded before S084 and change `backend/local_db.py`, `backend/equipment.py`,
`backend/config_rbac.py` and add `backend/contracts.py` and `backend/contracts_core.py`. In those
files this brief anchors by name (README § Anchors by name). Names marked **(from S080)** or
**(from S081)** do not exist at the baseline: the table `contracts` and its columns
(`renewal_of_id`, `to_date`, `from_date`, `active`, `site_id`, `vendor_id`, `title`,
`contract_number`, `contract_type`), the keys `contract:read_basic`, `contract:read`,
`contract:read_senior`, `contract:edit`, `contracts_core.ENDING_SOON_DAYS`,
`contracts_core.contract_status`, `contracts_core.CONTRACT_TYPES`, the LOCK ORDER note of
`contracts.py`, and the page route `/contracts/:id(\\d+)` (from S081). The alert files below no
open step touches; they are cited by line.

### Backend

- `backend/alerts_core.py` — the pure rules (§ 5):
  - `CONTRACT_ENDING = "contract_ending"`, `CONTRACT_KINDS = (CONTRACT_ENDING,)`; `KINDS`
    (`backend/alerts_core.py:38`) becomes `TICKET_KINDS + IMPROVEMENT_KINDS + CONTRACT_KINDS`;
  - `CHANNELS` (`:58`) gains `CONTRACT_ENDING: (PUSH, EMAIL)`;
  - `CONTRACT_AUDIENCE_KEY = {PUSH: "contract:read", EMAIL: "contract:read_senior"}`;
  - `FIRST_REMINDER_DAYS = ENDING_SOON_DAYS` (60, from S080), `SECOND_REMINDER_DAYS = 15`,
    `FIRST = "first"`, `SECOND = "second"`;
  - `CONTRACT_PATH = "/contracts/{id}"` beside `IMPROVEMENT_PATH` (`:92`);
  - `contract_reminder_due`, `should_send_contract`, `contract_facts`, `contract_text`,
    `contract_message`;
  - `you_get` (`:368`) gains the lines of § 5.7; the module docstring names the third record.
- `backend/alerts.py` — the shell:
  - `CONTRACT_ALERT = "contract_alert"`, `CONTRACT_SCAN = "contract_reminder_scan"`;
  - `enqueue_contract_alert(cur, contract_id, to_date)`;
  - `people_at_site(cur, site_id, roles, with_email=False)`; `people_at_unit` (`:155`) and it
    share one private query builder (§ 5.6), so `people_at_unit` keeps its result;
  - `contract_scan_candidates`, `lock_contract_for_scan`, `contract_renewed`,
    `mark_contract_reminded`, `read_alert_contract`, `contract_recipients` (§ 5.2, § 5.3);
  - the module docstring: the contract path and the scan's locks.
- `backend/task_handlers.py` — `contract_alert` and `contract_reminder_scan`; `HANDLERS` (`:393`)
  gains both. The email branch of `contract_alert` uses `alerts.enqueue_email` (`backend/alerts.py:114`)
  as `_email_fan_out` (`backend/task_handlers.py:163`) does; `_push_to_people` (`:153`) is used as
  it is.
- `backend/scheduled_tasks.py` — `SCHEDULE` (`backend/scheduled_tasks.py:12`) gains
  `("contract_reminder_scan", "08:00")`, after `improvement_alert_scan`.
- `backend/push_core.py` — `CONTRACT_TTL_SECONDS = IMPROVEMENT_TTL_SECONDS` beside it
  (`backend/push_core.py:43`), with the reason (D6).
- `backend/email_core.py` — `contract_ending_email(facts)` → `(subject, body)` (§ 5.4), after
  `closed_email` (`backend/email_core.py:131`), with its `_field` helper (`:71`) and `one_line`
  (`:45`).
- `backend/contracts_core.py` (from S080) — `CONTRACT_TYPE_WORDS = {"warranty": "Warranty", "amc":
  "AMC", "cmc": "CMC", "on_call": "On call"}` beside `CONTRACT_TYPES`, for the email (the frontend
  keeps its own longer labels in `contractLabels.js`, from S080).
- `backend/local_db.py` — migration **v46** (§ 4.1). No `_PRECONDITIONS` entry.
- `backend/contracts.py` (from S080) — docstring only: its LOCK ORDER note says the daily scan
  locks contract rows too (§ 5.5).
- `backend/equipment.py` — docstring only: the global LOCK ORDER's `contracts.py` bullet (from S080,
  rewritten in S081) loses "Only contracts.py locks contracts … rows" and gains the scan (§ 5.5).

**Import direction:** `alerts_core` imports `contracts_core` (pure → pure: `ENDING_SOON_DAYS`,
`contract_status`, `CONTRACT_TYPE_WORDS`); `alerts.py` imports `alerts_core` and
`access_core.roles_holding`, never `contracts.py`; `email_core` takes its facts as a dict and
imports nothing new. No cycle: `contracts_core` imports only `masters_core` (S080 § 3).

### Frontend

- `frontend/src/views/SettingsView.vue` — `TASK_LABELS` (`frontend/src/views/SettingsView.vue:208`)
  gains `contract_reminder_scan: "Send the contract reminders: contracts ending in 60 or 15 days"`.

### Tests

- `backend/tests/test_alerts_core.py` — the new rules, the texts, `you_get` (§ 8.1, § 8.3).
- `backend/tests/test_email_core.py` — `contract_ending_email` (§ 8.1).
- `backend/tests/test_access_core.py` — `roles_holding` of the two contract keys (§ 8.1).
- `backend/tests/test_contract_alerts.py` (new) — the scan, the handler, the worker path (§ 8.2).
- `backend/tests/test_scheduled_tasks.py` — the new entry (§ 8.3).
- `backend/tests/test_push_api.py` — the engineer's `you_get` (§ 8.3).
- `backend/tests/test_migration_v46.py` (new), on the pattern of `test_migration_v41.py` (§ 8.1).
- `frontend/e2e/notifications.spec.js` — the two *What you will get* lines (§ 8.4).
- `frontend/e2e/settings.spec.js` — the Background tasks line (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `contracts` line gains "the To date each reminder was sent for
  (S084)"; then `tooling\schema-docs.bat write`, read `git diff docs/schema/`, and `check` exits 0.
  `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 4.7: one row *Contract ending* (§ 5.4's recipients), and one bullet like the
  *Improvement alerts* bullet.
- `.claude/CLAUDE.md` § Yantra Specifics, *Notifications (S021)*: the contract kind, its scan and
  its markers; § SMTW-Review: the point of § 9.
- `docs/steps/device-checks.md`: two rows (§ 8.5).

**File count:** 20 code and test files (11 code: 10 backend, 1 frontend; 9 tests), 4 docs. One
concern. No split.

## 4. Data model

### 4.1 Migration v46

```sql
-- Contract reminders (S084, R02.5): the To date each reminder was queued for, so the daily scan
-- sends each once per To date.  NULL = never sent.  A changed To date sends them again.
ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS first_reminder_for DATE NULL AFTER to_date,
    ADD COLUMN IF NOT EXISTS second_reminder_for DATE NULL AFTER first_reminder_for;
```

- **The number.** S083 (drafted in parallel) is planned to take v45; S084 takes **v46**. If S083
  ships without a migration, the coder takes the next free number and renames the test file; the
  staleness check before coding confirms it.
- **The value is the To date reminded for**, not a flag (as S074's v40, D3 there). A To date edited
  later (longer or shorter) differs from both markers, so the reminders due for the new date are
  sent again. No route of S080 or R02.4 has to clear them.
- **Why columns, not a table** (D3).
- **No index.** The scan reads `contracts` once a day; a plant holds tens of contracts. The
  candidate read can use `ix_contracts_site` (from S080) only with a site; a full read is cheaper
  than a key to keep.
- **No `_PRECONDITIONS` entry.** Two nullable columns; no existing row changes value. Production
  holds no contract: `contracts` is new in v43 (S080), and v42–v46 ship in one release (§ 9,
  assumption A1). On rows the change is safe anyway.
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS` on both, in one statement.
- **Rollback:** a release before v46 never reads the columns and has no scan, so nothing doubles.
- **A departure from the roadmap** (R02.5: "Migrations: none (settings in `app_settings`)"): D2, D3.

### 4.2 What is computed, never stored

- Days left: `to_date − today` (IST), as S080's `contract_status` (`days`).
- *Renewed*: another **active** contract whose `renewal_of_id` is this one (§ 5.2).
- Recipients, their devices and addresses, and every text: read when the alert task runs.

## 5. Rules

### 5.1 When a reminder is due

`alerts_core.contract_reminder_due(active, renewed, from_date, to_date, first_for, second_for,
today)` → `FIRST`, `SECOND` or `None`. In order, the first that holds:

| Case | Result |
|---|---|
| `active` false, or `renewed` true | `None` |
| `from_date > today` (not started; S080's `upcoming`) or `to_date < today` (ended) | `None` |
| `days = (to_date − today).days ≤ SECOND_REMINDER_DAYS` (15) | `SECOND` when `second_for != to_date`, else `None` |
| `days ≤ FIRST_REMINDER_DAYS` (60) | `FIRST` when `first_for != to_date`, else `None` |
| otherwise | `None` |

- **At most one per run.** A contract that enters the window late (added with 40 days left, or the
  worker down over day 60) gets the first reminder with the true days left ("ends in 40 days"). One
  added or found with 15 days or fewer gets only the second: two reminders at once would be noise.
- **Day 0 counts:** a contract ending today (`days` 0) that has had no second reminder gets one
  ("Contract ends today"). This happens only when the scan was late or the date was edited.
- **Once per reminder per To date** (`!=`, as S074 BR1-01). Edited To date:

| Edit after a reminder was sent | Result |
|---|---|
| Later, past 60 days left | nothing now; both reminders again at the new dates |
| Later, still 16–60 days left | the first again next morning, then the second at 15 days |
| Earlier, now 15 days or fewer | the second next morning (for the new date) |
| Into the past | nothing (ended) |
| `from_date`, the title or any other field | nothing (only `to_date` is compared) |

- **Inactive:** a contract set inactive gets nothing; set active again, it gets the reminder due
  then, unless that reminder was already sent for this To date.
- **A new contract** gets nothing at create; the next morning's scan decides. Rejected: a reminder
  at create (the creator is the one who knows).
- **`FIRST_REMINDER_DAYS` is S080's `ENDING_SOON_DAYS`** (one constant, imported), so the *Ends in N
  days* badge and the first reminder start the same day. This answers S080's assumption A3.

### 5.2 Renewed

- **The rule:** a contract counts as **renewed** when another contract with `active = 1` has
  `renewal_of_id` = its id. One query, `alerts.contract_renewed(cur, contract_id)`:
  `SELECT 1 FROM contracts WHERE renewal_of_id = %s AND active = 1 LIMIT 1` (served by
  `ix_contracts_renewal_of`, from S080).
- **Why active only:** a renewal entered by mistake is set inactive (S080: never deleted); it must
  not silence the old contract's reminders.
- **R02.4 sets `renewal_of_id`** (S080 § 1 item 7). Until then the rule finds nothing and every
  active contract is reminded. S084's tests insert the renewal row directly (§ 8.2). R02.4's brief
  must keep this meaning, or change `contract_renewed` with it.
- **A renewal entered after the first reminder** stops the second. A renewal whose own To date comes
  near gets its own reminders: it is a contract like any other.

### 5.3 The daily scan (`contract_reminder_scan`)

- **When:** daily at **08:00 IST** (`SCHEDULE`), after `improvement_alert_scan` at the same time.
  The worker's `enqueue_scheduled` (`backend/worker.py:114`) enqueues it once a day, and once on
  return after a worker that was down over the time (`scheduled_tasks.due_tasks`). Why 08:00: the
  engineers and managers start the day with the phone, and the morning alerts already come then
  (S074 § 9 Q1); one hour for every daily alert is easier to learn (§ 9 Q2).
- **No payload** (`_expect_no_payload`, `backend/task_handlers.py:66`): BadTask otherwise.
- **Steps, all in the worker's one transaction** (the handler commits nothing; the worker commits
  its writes with `mark_done`, `backend/task_handlers.py:3-7`):
  1. `SELECT NOW()` once (the session clock, IST, as `improvement_alert_scan` does); `today =
     now.date()`.
  2. **Candidates, one plain read** (`alerts.contract_scan_candidates(cur, today, until)`, `until
     = today + FIRST_REMINDER_DAYS`): `SELECT id FROM contracts WHERE active = 1 AND from_date <=
     %s AND to_date BETWEEN %s AND %s AND (second_reminder_for IS NULL OR second_reminder_for <>
     to_date) ORDER BY id`. It only narrows the work; nothing is decided from it.
  3. **Per candidate, in id order:** `alerts.lock_contract_for_scan(cur, contract_id)`: `SELECT
     id, active, from_date, to_date, first_reminder_for, second_reminder_for FROM contracts WHERE
     id = %s FOR UPDATE`, one row per statement. A row gone (never: nothing is deleted) is skipped.
  4. `alerts.contract_renewed(cur, contract_id)` (plain; see *Renewed during the scan* below).
  5. **Decide from the locked row** with `contract_reminder_due` (§ 5.1). For `FIRST`: `UPDATE
     contracts SET first_reminder_for = to_date WHERE id = %s`; for `SECOND`: the same on
     `second_reminder_for` (`alerts.mark_contract_reminded(cur, contract_id, which, to_date)`). Then
     `alerts.enqueue_contract_alert(cur, contract_id, to_date)`. Neither update stamps
     `updated_*`: a reminder is not a change of the contract (as S074's markers).
  6. Log one line: "contract_reminder_scan: N first, M second reminders".
- **Renewed during the scan.** The renewal read is plain, so under REPEATABLE READ it sees the
  snapshot of step 2. A renewal committed between step 2 and the scan's commit is missed here: the
  marker is written and the task queued. The `contract_alert` task runs later in its own
  transaction, reads the renewal and sends nothing (§ 5.4 step 4). A locking read of the renewal
  was rejected: its gap lock on `ix_contracts_renewal_of` could block R02.4's insert while the scan
  waits on that renewal's old contract, a deadlock cycle.
- **What a run stores:**
  - success: the markers and the `contract_alert` tasks, with `mark_done`, in one commit;
  - any exception (a lost connection, a deadlock 1213): everything rolls back, markers included;
    the queue retries after the back-off (internal and idempotent, `DEFAULT_MAX_ATTEMPTS` 3,
    `backend/task_queue.py:18`); a retry finds the same candidates;
  - three failures: the task is `failed`, counted on Settings › Background tasks; `due_tasks` sees
    it enqueued today and waits for tomorrow, whose run finds the same unmarked contracts with one
    day less. At worst a day late, with the true days left.
- **Push off, email off, or nobody to tell:** the markers are written all the same (D7).

### 5.4 The alert task (`contract_alert`) and its texts

**Enqueued** by `alerts.enqueue_contract_alert(cur, contract_id, to_date)`, in the scan's
transaction. Payload `{kind: "contract_ending", contract_id, to_date}`: `contract_id` an integer,
`to_date` as `YYYY-MM-DD` text (`PAYLOAD_DATE`, `backend/alerts_core.py:94`). No person id, no
address, no price.

**The handler**, in the worker's transaction, plain reads only (as `improvement_alert`,
`backend/task_handlers.py:229`):

1. Validate: `contract_id` by `_ids` (`:105`), `kind` in `CONTRACT_KINDS`, `to_date` parsed with
   `_payload_time` (`:202`); else BadTask (failed at once).
2. `SELECT NOW()`; `today = now.date()` (the text says the days left at send time).
3. `alerts.read_alert_contract(cur, contract_id)` → the row: `id`, `title`, `contract_number`,
   `contract_type`, `from_date`, `to_date`, `active`, `site_id`, `site_code`, `vendor_name`, and
   `renewed` (the § 5.2 rule as an `EXISTS` sub-query). None when missing → BadTask.
4. `should_send_contract(row["active"], row["renewed"], row["to_date"], expected_to_date, today)`
   (pure): active, not renewed, `to_date` still the payload's, and `to_date >= today`. False → log
   "contract_alert for contract <id>: not sent, <reason>" and return (done).
5. `facts = contract_facts(row, today, label_base_url(cur))`.
6. **Push** (`PUSH in CHANNELS[kind]`): `push_sender.enabled()` false → log "push is not set up",
   skip. Else `contract_recipients(cur, row, PUSH)` → `_push_to_people(cur, people,
   contract_message(facts), CONTRACT_TTL_SECONDS)`.
7. **Email** (`EMAIL in CHANNELS[kind]`): `mail_sender.enabled()` false → log "email is not set
   up", skip. Else `contract_recipients(cur, row, EMAIL)` (with an address); when any, `subject,
   body = contract_ending_email(facts)` and `alerts.enqueue_email(cur, person_id, subject, body)`
   per person.
8. Log "contract_alert for contract <id>: n people and m devices by push, k emails".

**What it stores:** success: the `push_send` and `email_send` rows and `done`, one commit (all or
nothing, so a retry never doubles them). An exception: rollback, retried with the back-off; failed
after 3. `push_send` and `email_send` are unchanged (S021, S032): each reads its device or the
person's address when it runs, and records its own failure.

**The facts** (`contract_facts(contract, today, base_url)`): `contract_id`, `title` (cut to 80,
`DESCRIPTION_CUT`), `contract_number`, `type_word` (`CONTRACT_TYPE_WORDS`), `vendor_name`,
`site_code`, `from_date`, `to_date`, `status_label` (`contract_status(from_date, to_date,
today)["label"]`, from S080: "Ends today", "Ends in 1 day", "Ends in 15 days"), `path`
(`CONTRACT_PATH`), `url` (`base_url + path`). **No `callout_number`, no `cost_note`, no price**:
`read_alert_contract` does not select them, so no text can show them.

**Push text** (`contract_text(facts)` → `(title, body)`; writing style B; dates DD-MM-YYYY):

| | Text |
|---|---|
| Title | `Contract ends in 60 days · SMTW` (`"Contract " + status_label` with its first letter lower case, then `" · "` and the site code); day 0: `Contract ends today · SMTW` |
| Body | `Atlas Copco AMC 2026–27 · Atlas Copco — ends on 31-03-2027. Renew it, or let it end.` |

`contract_message(facts)` → `{title, body, path: "/contracts/12", tag: "contract-12", quiet: True}`.
The tag makes the second reminder replace the first on the phone. `sw.js` opens any same-origin
path (`frontend/public/sw.js`, `targetUrl`), so it needs no change.

**Email** (`email_core.contract_ending_email(facts)`):

```
Subject: Contract ends on 31-03-2027: Atlas Copco AMC 2026–27 (SMTW)

Atlas Copco AMC 2026–27 ends in 60 days, on 31-03-2027.

Vendor:           Atlas Copco
Type:             AMC
Contract number:  ACI/AMC/2026/118
Site:             SMTW
Period:           01-04-2026 to 31-03-2027

Decide before the end date: renew it with the vendor, or let it end.

Open the contract: https://vel-yantra.mspv.app/contracts/12
```

- The subject goes through `one_line` (a title holds no line break, but the rule is the email's).
- *Contract number* is left out when empty (as `closed_email`'s `add`). Day 0: "ends today, on
  31-03-2027".
- **Never in the email:** the price, the cost note, the call-out number, the documents (behind
  `contract:read_senior` and `contract:read`); the email may be forwarded, so it holds only
  `contract:read_basic` fields.
- The sample contract number above is made up; tests use `TEST/AMC/0001`.

**When the contract changes before the task runs** (step 4 decides, from the rows as they are then):

| Change after the queueing | Result |
|---|---|
| Set inactive | not sent |
| A renewal entered (an active contract with `renewal_of_id` = it) | not sent |
| To date edited | not sent; the next scan decides on the new date |
| The task runs after the To date (worker down for days) | not sent |
| A recipient loses the key or becomes inactive | that person is left out (§ 5.6) |

### 5.5 Locks

The database runs REPEATABLE READ. The contract row is not numbered in the global order
(`backend/equipment.py` LOCK ORDER); S080's and S081's `contracts.py` bullet places it: every
contracts.py write locks **one** contract row `FOR UPDATE`, **first** in its transaction, then a
`contract_equipment` line row, the vendor or the node shared (from S080, S081). S083's document
writes lock the contract row as their one owner lock (*to verify* against S083's brief when it is
approved).

**The scan** (§ 5.3), one transaction: (1) plain read of the candidates; (2) per candidate in id
order, the contract row `FOR UPDATE`, one row per statement; (3) plain read of the renewal; (4) the
marker `UPDATE` on the row held; (5) `INSERT` into `task_queue` (no foreign key). Several contract
rows are held at once, always in id order. **The alert task:** plain reads only. **The routes:**
unchanged.

**No deadlock cycle**, checked against `backend/equipment.py` LOCK ORDER, the `contracts.py` note
(from S080, S081) and `backend/alerts.py`'s docstring:

- Every route holds **at most one** contract row, locked **first**; so no route waits for a second
  contract row, and the scan waiting on a route's row waits behind a writer that finishes.
- A route holding its contract then waits only for a line row, the vendor or the node (1), shared;
  the scan holds none of them. The scan takes no equipment, vendor, ticket, improvement or person
  lock.
- R02.4 (later) inserts a renewal while holding the old contract; the insert's foreign-key lock is
  on that held row. The scan's renewal read is plain, so it holds no gap lock R02.4 could wait on.
- A deadlock all the same (1213) rolls the scan back and retries it (§ 5.3).

The coder writes: in `contracts.py`'s LOCK ORDER note and in `equipment.py`'s `contracts.py` bullet,
"The daily `contract_reminder_scan` (S084, `alerts.lock_contract_for_scan`) locks several
contract rows FOR UPDATE in id order, then writes only their reminder columns and `task_queue`
rows; every route holds at most one contract row, taken first, so no cycle"; the same in
`alerts.py`'s docstring. The phrase "Only contracts.py locks contracts … rows" (S081 § 5.5) is
reworded to "Only contracts.py and the reminder scan lock contracts rows".

### 5.6 Recipients

`alerts.people_at_site(cur, site_id, roles, with_email=False)` → the ids of active people with a
membership at `site_id` whose role is in `roles`, in id order; with `with_email`, only those with
`people.email` set. **No unit condition:** a contract belongs to a site, and S080's keys are checked
at the site, whatever units the member works in (S080 § 5.5; `access_core.has_key_at`,
`backend/access_core.py:100`).

**DRY:** today's `people_at_unit` SQL (`backend/alerts.py:163-176`) moves into a private
`_people_with_role(cur, site_id, roles, unit_ids, only_ids, exclude_ids, with_email)`, where
`unit_ids=None` leaves out the unit condition. `people_at_unit` calls it with its list (an empty
list still returns `[]`, as today); `people_at_site` with `None`. The public functions stay
explicit; the `None` lives only inside the private one.

`alerts.contract_recipients(cur, contract, channel)` = `people_at_site(cur, contract["site_id"],
roles_holding(CONTRACT_AUDIENCE_KEY[channel]), with_email=(channel == EMAIL))`.

| Channel | Key (from S080) | `roles_holding` today | Who |
|---|---|---|---|
| Push | `contract:read` (`("maint_engineer",)`) | manager, engineer | the site's engineers and managers |
| Email | `contract:read_senior` (`("maint_manager",)`) | manager | the site's managers with an address |

- **By key, not by exact role** (as S074 D6): the roadmap's "engineers and managers" is exactly the
  holders of `contract:read` (D10), and "managers" the holders of `contract:read_senior` (D5). If
  KLA changes who holds a key in `config_rbac.py`, the reminders follow.
- **Why `contract:read` for push, not `contract:read_basic`:** `read_basic` is `("*",)`, every role
  (S080 § 5.5); a technician or operator does not renew contracts (Q5.1 a).
- **Why `contract:read_senior` for email:** the renewal is a buying decision, made by who reads the
  price. A manager gets both the push and the email.
- **Every recipient may open the contract:** `contract:read_basic` is held by every site role, so
  the tap never ends in S081's 404.
- **Nobody is left out as the actor:** the scan has none.
- **Admin and IT admin** have no membership: never recipients. IT admin holds `contract:edit` by
  its token but not `contract:read` (S080 § 5.5).
- **No login, no device, no address:** nothing for that person. An email address comes from the
  login token (S032); `email_send` reads it when it sends.

### 5.7 What you will get

`you_get(memberships)` (`backend/alerts_core.py:368`) gains, per membership, from the role's keys
(`compute_permissions`):

- when the role holds `contract:read`: `"Contracts ending at <site code>"`, after the membership's
  verify line;
- when the role holds `contract:read_senior`: `"Contracts ending at <site code>, by email"`, after
  its *Closed tickets* line.

The place is the **site code**, also for a membership with chosen units, and **also for a
membership without units**, whose other lines are skipped today (`if not place: continue`,
`:386`): the contract lines are computed before that `continue`, because `people_at_site` reaches
that person.

Examples: an engineer at all of SMTW: "Breakdowns and defects at SMTW, escalations", "Improvements
ready to verify at SMTW", "Contracts ending at SMTW", "Jobs assigned to you", the two countermeasure
lines. A manager at SMTW.MCC2: "Breakdowns at SMTW.MCC2, escalations", "Improvements ready to
verify at SMTW.MCC2", "Contracts ending at SMTW", "Closed tickets at SMTW.MCC2, by email",
"Contracts ending at SMTW, by email", "Jobs assigned to you", the two countermeasure lines. A
technician, operator, supervisor or storekeeper: no contract line.

The email line shows whether or not the person has an address, as the *Closed tickets* line does
today. **The dot** (`showDot`) does not change for anyone: engineers and managers already had lines.

### 5.8 The database down

- The scan and the alert task run in the worker, which reconnects on its own (S013). A scan due
  while the database was down runs once when it is back (`due_tasks`); the clock-based rule finds
  the same contracts, with the true days left, and the markers stop doubles.
- No route changes, so no request path is affected.
- Push or email not set up on the server: that channel is skipped with a log line; the markers stay
  written, so turning a channel on later does not send a backlog of old reminders (D7).

## 6. API

No new route and no changed answer, except:

- `GET /api/push/config` (`backend/push.py:79`): `you_get` gains § 5.7's lines.
- `GET /api/settings/tasks` (`backend/settings.py:348`): lists `contract_reminder_scan` after
  `improvement_alert_scan`.

## 7. Design decisions

- **D1. One kind, two channels, the audience per channel.** `CONTRACT_ENDING` has `CHANNELS` =
  `(PUSH, EMAIL)` and `CONTRACT_AUDIENCE_KEY` names the key per channel, because the push and email
  audiences differ (the ticket kinds have one audience for both). Its own task `contract_alert` (as
  S074 D1: each record its own alert task), sharing `_push_to_people`, `enqueue_email` and the
  recipient query. Rejected: two kinds `contract_ending_push` and `contract_ending_email` (a kind
  is an event, not a channel; `CHANNELS` would lie); `ticket_alert`'s email branch (its text is
  `closed_email`, ticket-shaped).
- **D2. The lead days are constants, a departure from the roadmap** (R02.5: "The lead days are
  settings (Settings › Notifications)"). Q5.1 (a) and Plan.MD name 60 and 15; Fuji's contract asks
  for renewal two months before expiry (R02 § Log). A setting adds a card, its bounds, and a rule
  for what a change does to reminders already sent; nobody has asked to change the days. Adding it
  later is one setting read in the scan. Rejected: settings now (CLAUDE-COMMON *Nothing beyond the
  agreed scope*). § 9 Q1 asks KLA.
- **D3. "Once" by two marker columns holding the To date reminded for (v46)**, a departure from
  the roadmap's "Migrations: none". It is explicit, survives the queue's 90-day purge
  (`DONE_TASK_RETENTION_DAYS`), and a changed To date re-arms both reminders with no route clearing
  anything (S074 D3's reasoning). Two columns, each naming one reminder, read more plainly than one
  column plus a stage number. Rejected: a table `contract_reminders(contract_id, which, to_date,
  sent_at)` (a new table and a join for two facts per contract; its only gain, a history of
  reminders, nobody asked for); the task queue as the memory (a JSON search in a table purged
  after 90 days); a window "exactly 60 days left" (misses the days the worker was down and a
  contract added late).
- **D4. The scan locks contract rows in id order and decides from them.** The markers are written
  on contract rows, so it takes them `FOR UPDATE` as the routes do (repo rule: decide from the
  locking read). Rejected: a conditional `UPDATE … WHERE second_reminder_for <> to_date` without a
  read (the decision needs `days`, the renewal and both markers; split between SQL and the core it
  drifts).
- **D5. Renewed = an active contract points at it** (§ 5.2), stated now so R02.4 builds on it.
  Rejected: "a contract of the same vendor at the same site starting after it" (guesses; a second
  contract with the vendor is not always a renewal, D7 of R02).
- **D6. Quiet push, kept 24 hours.** No machine is down: a contract ending in 60 days must not
  sound like a breakdown (S074 D7's rule for every quiet alert: no sound, Urgency `low`). The
  tickets' one-hour TTL would drop a reminder sent once to a phone off for an hour.
  `CONTRACT_TTL_SECONDS` equals `IMPROVEMENT_TTL_SECONDS` and says why, so neither changes by
  accident with the other. Rejected: loud (§ 9 Q3).
- **D7. The markers are written even when no channel is set up or nobody would get it.** "Once" is
  about the event, not the delivery: switching email on later must not send a month of old
  reminders. The task logs who it found (S074 D8).
- **D8. The texts carry only `contract:read_basic` fields** (title, vendor, type, number, site,
  period). The people who get them hold more keys, but an email is forwarded and a push shows on a
  locked phone. Rejected: the call-out number in the push (useful only at a breakdown, which the
  machine card serves, S082).
- **D9. No reminder at create; the scan decides.** One path for every reminder. Rejected: a reminder
  from S080's create route (a second path, a route change in a step that touches no route).

## 8. Tests and acceptance

### 8.1 Pure core and migration

`backend/tests/test_alerts_core.py`:

- `contract_reminder_due` (today fixed at 30-01-2027): to 31-03-2027 (60 days), never sent →
  `FIRST`; 61 days → `None`; first sent for this date → `None`; first sent for an older date →
  `FIRST`; 15 days, nothing sent → `SECOND`; 15 days, first sent → `SECOND`; 16 days, first sent →
  `None`; 0 days (ends today), second not sent → `SECOND`; ended yesterday → `None`; not started
  (`from_date` tomorrow, 30 days left) → `None`; inactive → `None`; renewed → `None`; second sent
  for this date at 10 days → `None`; second sent for an older date at 10 days → `SECOND`.
- `should_send_contract`: as queued → True; inactive, renewed, another `to_date`, `to_date` before
  today → False each; `to_date` today → True.
- `contract_text` / `contract_message`: the two texts of § 5.4 exactly; day 0 "Contract ends
  today · SMTW"; 1 day "Contract ends in 1 day · SMTW"; a title of 100 characters cut at 80; path
  `/contracts/12`, tag `contract-12`, quiet True; the facts hold no key `callout_number` or
  `cost_note`.
- `TestChannels`: `test_every_kind_has_channels_and_the_improvement_kinds_are_push_only`
  (`KINDS == TICKET_KINDS + IMPROVEMENT_KINDS`) becomes `KINDS == TICKET_KINDS + IMPROVEMENT_KINDS +
  CONTRACT_KINDS`; a new test: `CHANNELS[CONTRACT_ENDING] == ("push", "email")`, and
  `CONTRACT_AUDIENCE_KEY` names `contract:read` and `contract:read_senior`.
- `FIRST_REMINDER_DAYS == ENDING_SOON_DAYS == 60`, `SECOND_REMINDER_DAYS == 15`.

`backend/tests/test_email_core.py`: `contract_ending_email` gives § 5.4's subject and body exactly
(contract number `TEST/AMC/0001`, vendor "Test Vendor"); no *Contract number* line when it is
empty; day 0 "ends today, on …"; a title with a line break gives a one-line subject.

`backend/tests/test_access_core.py`: `roles_holding("contract:read")` = `("maint_manager",
"maint_engineer")`; `roles_holding("contract:read_senior")` = `("maint_manager",)`.

`backend/tests/test_migration_v46.py` (new; `V45 = … range(20, 46)`, `V46 = … range(20, 47)`, as
`test_migration_v41.py`): a fresh database has both columns, nullable, after `to_date`; a v45
database with one contract (inserted with S079's vendor and S080's columns) keeps it, both columns
NULL; a re-run changes nothing.

### 8.2 Shell (`backend/tests/test_contract_alerts.py`, new)

Fixtures: `make_site`, `make_vendor` (from S079), `user_at_sites` (an engineer, a manager with an
address `@example.test`, a manager without, a technician, a manager of another site), `db_rows`,
and S080's `POST /api/contracts` as `admin` for each contract; dates set relative to the database's
`CURDATE()` with `db_rows` (`UPDATE contracts SET to_date = CURDATE() + INTERVAL 60 DAY`). Devices
are inserted into `push_subscriptions` as `test_alerts.py` does (`add_device`). Each test its own
site, so the kept worker database gives the starting state. The handler is called with the worker's
pattern (`improvement_alert_scan(conn, None, …)` in `test_improvement_alerts.py`).

- **Scan, first:** 60 days left → one `contract_alert` task, payload `{kind, contract_id, to_date}`,
  `first_reminder_for` = the To date, `updated_at` unchanged; a second run → no new task.
- **Scan, second:** 15 days left after a first → one task, `second_reminder_for` set; 10 days left,
  nothing sent → one task (second only), `first_reminder_for` stays NULL.
- **Scan, nothing:** 61 days; ended yesterday; `from_date` tomorrow; inactive → no task, no marker.
- **Renewed** (D5): a second contract inserted with `renewal_of_id` = the first through `db_rows`
  (`active = 1`) → no task; the same with `active = 0` → a task.
- **Re-arm** (§ 5.1): first sent, then `to_date` moved 30 days later and set back to 60 days left
  → a new task; `to_date` moved to 10 days left → a second-reminder task.
- **All or nothing:** `enqueue_contract_alert` monkeypatched to raise on the second contract → the
  run raises, no marker and no task stay.
- **Handler, push:** the engineer's and the manager's devices get one `push_send` each with § 5.4's
  title, Urgency `low`, `ttl` 86400, path `/contracts/<id>`; the technician's device and the other
  site's manager get none.
- **Handler, email:** one `email_send` for the manager with an address, none for the one without,
  none for the engineer; payload `person_id`, the subject of § 5.4; the payload holds no `@`.
- **Handler, a manager with no units** (membership with `all_units = 0` and no `person_units`) →
  gets the push and the email.
- **Handler, no longer true:** set inactive, renewal inserted, `to_date` edited after queueing,
  `to_date` before today → done, no send rows.
- **Handler, push off** (`push_off`): email rows only; **email off** (`email_off`): push rows only;
  both off → done, no rows; the scan still writes the markers.
- **Through the worker:** `Worker.run_once` with `SCHEDULE` patched to `[("contract_reminder_scan",
  "00:00")]` (as `backend/tests/test_worker.py:131`), `push_sender.send` and `mail_sender.send`
  faked (as `fake_send` in `test_alerts.py` and `test_closed_email.py`): the scan `done`, the
  `contract_alert` `done`, the `push_send` and `email_send` rows `done`, the fakes called with the
  texts. No test reaches a real push service or mail server (`no_real_push`,
  `smtp_test_values`).
- **Bad tasks:** the scan with a payload; `contract_alert` with an unknown kind, a missing
  `contract_id`, `to_date` not a date, a contract that does not exist → BadTask.

### 8.3 Existing tests that break or run again

- `backend/tests/test_alerts_core.py` `TestYouGet`: `test_engineer_all_units`,
  `test_manager_at_two_sites`, `test_manager_at_one_unit` gain § 5.7's lines in place.
  `test_supervisor_at_two_units`, `test_technician_gets_assigned_jobs`,
  `test_operator_gets_the_countermeasure_line`, `test_nothing_for_other_roles`,
  `test_no_memberships_it_admin`, `test_a_membership_without_units` (a supervisor: no contract key)
  and `test_engineer_gets_no_email_line` stay green. New: a manager membership without units →
  `["Contracts ending at SMTW", "Contracts ending at SMTW, by email", "Jobs assigned to you"]`.
- `backend/tests/test_alerts_core.py` `TestChannels`: the `KINDS` assertion (§ 8.1).
- `backend/tests/test_scheduled_tasks.py` `test_the_improvement_alerts_at_eight_after_the_purge`
  (`SCHEDULE ==` two entries): gains the third entry; `test_the_schedule_has_the_purge` stays green.
- `backend/tests/test_push_api.py` `test_push_on_with_the_public_key_and_what_you_get`: the
  engineer's list gains `f"Contracts ending at {site['code']}"` after the verify line.
- `backend/tests/test_worker.py` `TestTasksCard`: reads `tasks[0]`, still `purge_access_log`: green.
- `backend/tests/test_alerts.py`, `backend/tests/test_closed_email.py`,
  `backend/tests/test_improvement_alerts.py`: run whole, as they pin the recipients that
  `people_at_unit` serves through the moved query (§ 5.6).
- `backend/tests/test_rbac.py` `test_role_matrix`: unchanged (no new key).
- `backend/tests/conftest.py` `_TABLES`: unchanged (no new table).
- S080's `test_migration_v43.py`, S081's `test_migration_v44.py` and S083's migration test, if any:
  unchanged (each slices its own range). S080's `test_contracts_api.py`: unchanged (no route
  changes; the new columns are not in `_contract_out`'s answer, which the coder checks: if
  `_contract_out` sends the whole row, it must leave the two columns out, § 6).

### 8.4 Automated (e2e)

- `frontend/e2e/notifications.spec.js` "S021 A1: What you will get — …": the engineer's card also
  contains "Contracts ending at SMTW" (`// S084`). The technician's exact list stays.
- `frontend/e2e/notifications.spec.js` "S032: the manager sees the closed-ticket email line …": the
  card also contains "Contracts ending at SMTW, by email" (`// S084`).
- `frontend/e2e/settings.spec.js`, new test "S084: Background tasks lists the contract reminders at
  08:00" (IT admin): the card shows "Send the contract reminders: contracts ending in 60 or 15 days
  — daily at 08:00". The S074 test stays green.
- Targeted run: `tooling/run-e2e-tests.bat e2e/notifications.spec.js e2e/settings.spec.js
  e2e/screens.spec.js`; the whole suite at Normal once at the end. `npx vite build` in `frontend/`.

### 8.5 On a real device (`docs/steps/device-checks.md`)

Push needs HTTPS and the VAPID keys, and email the production mail relay, so both rows run on
**production, the TEST machine's site SMTW**, after the deploy. *Network*: "Company Wi-Fi, or
mobile data with the phone charging" (the push is quiet, Urgency low, D6). Both rows use one test
contract: the **IT Admin** login adds it in Masters › Contracts at SMTW, title "TEST reminder check —
not a real contract", any active vendor, From today, **To 30 days from today**; afterwards she sets
it inactive. Every SMTW engineer and manager gets these reminders: KLA tells them first.

1. **Important.** The engineer test login's phone has notifications on (set up as rows 1 and 4 of
   § *Phone set-up for notifications (S021)*). After **08:00 the next day** it shows **Contract ends
   in 29 days · SMTW**, without sound; a tap opens the contract page. Then IT Admin changes the To
   date to **10 days from today**; after 08:00 the next day the phone shows **Contract ends in 9
   days · SMTW**, and it **replaces** the first reminder. Done by IT Admin.
2. **Important. KLA only** (a manager at SMTW with an address). The mornings of row 1, the email
   "Contract ends on <date>: TEST reminder check — not a real contract (SMTW)" is in KLA's Outlook,
   **not in junk**; it shows the vendor, type, site and period, **no price and no call-out
   number**, and its link opens the contract after the login.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs and the whole suite at Normal green once.
- `tooling\schema-docs.bat check` exits 0.
- By the worker (§ 8.2): each reminder reaches the right devices and addresses once per To date,
  never after a renewal, never for an inactive contract.

## 9. Open questions and assumptions

- **Q1. Lead days fixed or settings?** The roadmap said settings; this brief proposes constants
  (D2).
  - **(a) Constants 60 and 15 — recommended.** No new card; the badge and the first reminder share
    `ENDING_SOON_DAYS`. A later step adds a setting if the plant asks.
  - (b) Two settings in Settings › Notifications. One more card and its rules; a change re-times
    reminders not yet sent, never re-sends one sent.
- **Q2. The scan's time.** **08:00 IST — recommended**, with the improvement scan, so the daily
  alerts come at one hour. Another time is one string in `SCHEDULE`. Plant-Facts § 5 leaves the
  shift pattern TBD.
- **Q3. Quiet or loud push.** **Quiet — recommended** (D6). Loud would sound like a breakdown for a
  date two months away.
- **A1. Assumption:** v42–v46 ship in one release, so no contract exists in production before v46
  (no `_PRECONDITIONS` entry; the columns are nullable either way).
- **A2. Assumption:** a contract at a site set inactive is reminded like any other; the site's
  memberships decide who hears. Nothing in S080 stops a contract when its site is set inactive.
- **A3. Assumption:** S083 takes v45 and locks the contract row as its one document owner lock
  (§ 5.5); the staleness check before coding confirms both.
- **A4. Assumption:** S080's `_contract_out` builds the answer from named fields or drops unknown
  ones, so the two new columns do not appear in the API (§ 8.3). If it sends the whole row, the
  coder leaves them out there.
- **A staleness check is due before coding:** S080–S083 are coded after this brief. Check
  `contracts_core.ENDING_SOON_DAYS`, `contract_status`'s labels, `CONTRACT_TYPES`, the key names
  and holders in `config_rbac.py`, `renewal_of_id` and `ix_contracts_renewal_of`, the
  `contracts.py` LOCK ORDER note, S081's route `/contracts/:id(\\d+)`, and the migration number.
- **Proposed point for § SMTW-Review** (`.claude/CLAUDE.md`): "Contract reminders (S084): the daily
  `contract_reminder_scan` sends each reminder once per To date through `first_reminder_for` and
  `second_reminder_for`, never for an inactive or renewed contract (an active contract with
  `renewal_of_id` = it); it is the only path that holds several contract rows, in id order. A
  reminder goes by push to the holders of `contract:read` and by email to the holders of
  `contract:read_senior` at the contract's site, and its text carries no price, cost note or
  call-out number."
- **Roadmap corrections** (for the orchestrator to note in R02's log): R02.5's "Migrations: none"
  and "lead days are settings" (D2, D3); § Order's "R02.3 ∥ R02.5 … with no migration": both now
  add a migration, so they conflict in `local_db.py` and run one after the other; R02.5 also
  changes `alerts.py`, `email_core.py` and `push_core.py`, which § Order does not list.
- **No defining question.** Gate R answered Q5.1 (a); the choices above are inside it.

## 10. Amendments

None.

## Review log
