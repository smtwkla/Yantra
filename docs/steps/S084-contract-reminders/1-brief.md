```
Step: S084 — Contract reminders
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: d216f48 + uncommitted R02 docs; S079–S083 coded before S084 (staleness check before coding)
Status: Approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 5 minor; BR1-02 and BR1-03 flagged for KLA at gate B)
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

- **Push** to the holders of `contract:read` (from S080) at the contract's site: its engineers and
  managers (R02 D10). Quiet, kept 24 hours (D6). A tap opens `/contracts/<id>` (from S081).
- **Email** to the holders of `contract:read_senior` (from S080) at the site with an address: its
  managers (S032 channel).
- **No text carries the price, the cost note or the call-out number** (§ 5.4). Every recipient may
  open the contract (`contract:read_basic` is `("*",)`, from S080).
- A daily task **`contract_reminder_scan`** at **08:00 IST** queues one **`contract_alert`** per
  reminder due. Two columns on `contracts` (migration **v46**) remember the To date each reminder
  was sent for, so a changed To date re-arms them.
- ***What you will get*** (`alerts_core.you_get`) gains a push line and an email line (S021 BR2-06);
  **Settings › Background tasks** lists the new task.

**After S084:** on 30-01-2027 the SMTW engineers and managers get *Contract ends in 60 days · SMTW*
for "Atlas Copco AMC 2026–27", and each SMTW manager gets the email "Contract ends on 31-03-2027:
Atlas Copco AMC 2026–27 (SMTW)". On 16-03-2027 they get the 15-day reminder, unless a renewal was
entered by then.

### Out of scope

- *Renew* (R02.4): until it lands nothing sets `renewal_of_id`, so every active contract gets both
  reminders; S084's rule already reads it (§ 5.2).
- A setting for the lead days or the scan's time (D2, § 9 Q1); a reminder after the end, or a
  repeat while nobody acts; PM-visit reminders (R02.7); a dashboard tile (phase 5); Telegram.
- Any change to the contract page, the list, the card or the service worker (which caches nothing
  and never will, § Yantra Specifics, *Notifications*).

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

S080–S083 are coded before S084; in the files they change (`backend/local_db.py`,
`backend/equipment.py`, `backend/config_rbac.py`, the new `backend/contracts.py` and
`backend/contracts_core.py`) this brief anchors by name. **From S080** (not at the baseline): the
table `contracts` and its columns (`renewal_of_id`, `to_date`, `from_date`, `active`, `site_id`,
`title`, `contract_number`, `contract_type`), `ix_contracts_renewal_of`, the four `contract:*` keys,
`contracts_core.ENDING_SOON_DAYS`, `contracts_core.contract_status`, `contracts_core.CONTRACT_TYPES`,
`contracts.py`'s LOCK ORDER note. **From S081:** the route `/contracts/:id(\\d+)`. The alert files
no open step touches; they are cited by line.

### Backend

- `backend/alerts_core.py` (pure, § 5): `CONTRACT_ENDING = "contract_ending"`, `CONTRACT_KINDS`;
  `KINDS` (`backend/alerts_core.py:38`) becomes `TICKET_KINDS + IMPROVEMENT_KINDS + CONTRACT_KINDS`;
  `CHANNELS` (`:58`) gains `CONTRACT_ENDING: (PUSH, EMAIL)`; `CONTRACT_AUDIENCE_KEY = {PUSH:
  "contract:read", EMAIL: "contract:read_senior"}`; `FIRST_REMINDER_DAYS = ENDING_SOON_DAYS`,
  `SECOND_REMINDER_DAYS = 15`, `FIRST`, `SECOND`; `CONTRACT_PATH = "/contracts/{id}"` beside
  `IMPROVEMENT_PATH` (`:92`); `contract_reminder_due`, `should_send_contract`, `contract_facts`,
  `contract_text`, `contract_message`; `you_get` (`:368`) gains § 5.7's lines; the docstring names
  the third record.
- `backend/alerts.py` (shell): `CONTRACT_ALERT = "contract_alert"`, `CONTRACT_SCAN =
  "contract_reminder_scan"`; `enqueue_contract_alert`; `people_with_role_at_site`, sharing a private query
  builder with `people_at_unit` (`:155`), which keeps its result (§ 5.6); `contract_scan_candidates`,
  `lock_contract_for_scan`, `contract_renewed`, `mark_contract_reminded`, `read_alert_contract`,
  `contract_recipients`; the docstring: the contract path and the scan's locks. The name
  `people_with_role_at_site` is new on purpose: `tickets.people_at_site` (`backend/tickets.py:748`)
  is the people picker, a different answer (BR1-05).
- `backend/task_handlers.py` also: `_payload_time` (`:202`) takes the task name as an argument, so a
  bad `contract_alert` payload is not logged as an improvement alert (BR1-06).
- `backend/task_handlers.py`: `contract_alert`, `contract_reminder_scan`; `HANDLERS` (`:393`) gains
  both. `_push_to_people` (`:153`) and `alerts.enqueue_email` (`backend/alerts.py:114`) as they are.
- `backend/scheduled_tasks.py`: `SCHEDULE` (`:12`) gains `("contract_reminder_scan", "08:00")`.
- `backend/push_core.py`: `CONTRACT_TTL_SECONDS = IMPROVEMENT_TTL_SECONDS` (`:43`), with D6's reason.
- `backend/email_core.py`: `contract_ending_email(facts)` after `closed_email` (`:131`), with
  `_field` (`:71`) and `one_line` (`:45`).
- `backend/local_db.py`: migration **v46** (§ 4.1); no `_PRECONDITIONS` entry.
- `backend/contracts.py` (from S080) and `backend/equipment.py`: docstrings only, the LOCK ORDER
  notes (§ 5.5).

**Import direction:** `alerts_core` imports `contracts_core` (pure → pure: `ENDING_SOON_DAYS`,
`contract_status`, and S081's `TYPE_SHORT` for the email's *Type* line, BR1-04); `alerts.py` imports `alerts_core` and
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

**File count:** 19 code and test files (10 code: 9 backend, 1 frontend; 9 tests), 4 docs. One
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

- **The number.** S083 takes v45 (its brief § 4.1, "S084 … takes v46"), so S084 takes **v46**; the
  staleness check confirms it before coding.
- **The value is the To date reminded for**, not a flag (as v40, S074 D3). A To date edited later
  differs from both markers, so the reminders due for the new date are sent again; no route clears
  them. Columns, not a table: D3.
- **No index:** tens of contracts, read once a day.
- **No `_PRECONDITIONS` entry:** two nullable columns, no existing value changes; production holds
  no contract (`contracts` is new in v43; § 9 A1).
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS`. **Rollback:** a release before v46 never reads
  the columns and has no scan.
- **A departure from the roadmap** (R02.5: "Migrations: none"): D3.

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

- **At most one per run.** A contract entering the window late (added with 40 days left, or the
  worker down over day 60) gets the first reminder with the true days ("ends in 40 days"); one found
  with 15 days or fewer gets only the second. **Day 0 counts** ("Contract ends today"): only after a
  late scan or an edited date.
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

- **The rule:** a contract is **renewed** when another contract with `active = 1` has
  `renewal_of_id` = its id: `alerts.contract_renewed(cur, contract_id)`, `SELECT 1 FROM contracts
  WHERE renewal_of_id = %s AND active = 1 LIMIT 1` (`ix_contracts_renewal_of`, from S080). Active
  only: a renewal entered by mistake is set inactive (never deleted) and must not silence the old
  contract.
- **R02.4 sets `renewal_of_id`** (S080 § 1 item 7); until then every active contract is reminded,
  and S084's tests insert the renewal row directly (§ 8.2). R02.4's brief keeps this meaning or
  changes `contract_renewed` with it. A renewal entered after the first reminder stops the second;
  the renewal gets its own reminders at its own end.

### 5.3 The daily scan (`contract_reminder_scan`)

- **When:** daily at **08:00 IST**, after `improvement_alert_scan` at the same time; the worker's
  `enqueue_scheduled` (`backend/worker.py:114`) enqueues it once a day, and once on return after a
  worker down over the time (`scheduled_tasks.due_tasks`). Why 08:00: the morning alerts already
  come then (S074 § 9 Q1), and one hour for every daily alert is easier to learn (§ 9 Q2).
- **No payload** (`_expect_no_payload`, `backend/task_handlers.py:66`): BadTask otherwise.
- **Steps, all in the worker's one transaction** (the claim was committed before it, in its own
  transaction, `claim_next`; this one ends with `mark_done`, `backend/task_handlers.py:3-7`;
  `contract_alert` runs the same way):
  1. `SELECT NOW()` (the session clock, IST, as `improvement_alert_scan`); `today = now.date()`.
  2. **Candidates, one plain read** (`alerts.contract_scan_candidates(cur, today, until)`, `until
     = today + FIRST_REMINDER_DAYS`): `SELECT id FROM contracts WHERE active = 1 AND from_date <=
     %s AND to_date BETWEEN %s AND %s AND (second_reminder_for IS NULL OR second_reminder_for <>
     to_date) AND (first_reminder_for IS NULL OR first_reminder_for <> to_date OR to_date <= %s)
     ORDER BY id`, the parameters `today`, `today`, `until`, `today + SECOND_REMINDER_DAYS` (BR1-12:
     a contract whose first reminder is sent for this To date and has 16–60 days left is no
     candidate, so it is not locked every morning for nothing). It only narrows the work; nothing is
     decided from it: every row it leaves out is one `contract_reminder_due` answers `None` for.
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
- **What a run stores:** on success, the markers and the `contract_alert` tasks with `mark_done`, in
  one commit. On any exception (a lost connection, a deadlock 1213) everything rolls back, markers
  included, and the queue retries after the back-off (`DEFAULT_MAX_ATTEMPTS` 3,
  `backend/task_queue.py:18`). After three failures the task is `failed` (counted on Settings ›
  Background tasks); `due_tasks` waits for tomorrow, whose run finds the same unmarked contracts:
  at worst a day late, with the true days left. Push off, email off, or nobody to tell: the markers
  are written all the same (D7).

### 5.4 The alert task (`contract_alert`) and its texts

**Enqueued** by `alerts.enqueue_contract_alert(cur, contract_id, to_date)`, in the scan's
transaction. Payload `{kind: "contract_ending", contract_id, to_date}`: `contract_id` an integer,
`to_date` as `YYYY-MM-DD` text (`PAYLOAD_DATE`, `backend/alerts_core.py:94`). No person id, no
address, no price.

**The handler**, in the worker's transaction, plain reads only (as `improvement_alert`,
`backend/task_handlers.py:229`):

1. Validate: `contract_id` by `_ids` (`:105`), `kind` in `CONTRACT_KINDS`, `to_date` parsed with
   `_payload_time` (`:202`, given the task name `contract_alert`, BR1-06); else BadTask (failed at
   once).
2. `SELECT NOW()`; `today = now.date()` (the text says the days left at send time).
3. `alerts.read_alert_contract(cur, contract_id)` → the row: `id`, `title`, `contract_number`,
   `contract_type`, `from_date`, `to_date`, `active`, `site_id`, `site_code`, `vendor_name`, and
   `renewed` (the § 5.2 rule as an `EXISTS` sub-query). None when missing → BadTask.
4. `should_send_contract(row["active"], row["renewed"], row["from_date"], row["to_date"],
   expected_to_date, today)` (pure): active, not renewed, started (`from_date <= today`, BR1-08: a
   From date moved into the future gives no "Contract starts on …" title), `to_date` still the
   payload's, and `to_date >= today`. False → log
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

**What it stores:** on success the `push_send` and `email_send` rows and `done`, one commit (so a
retry never doubles them); on an exception a rollback and a retry, failed after 3. `push_send` and
`email_send` are unchanged: each reads the device or the address when it runs (S021, S032).

**The facts** (`contract_facts(contract, today, base_url)`): `contract_id`, `title` (cut to 80,
`DESCRIPTION_CUT`), `contract_number`, `type_word` (`TYPE_SHORT[contract_type]`, from S081),
`vendor_name`,
`site_code`, `from_date`, `to_date`, `status_label` (`contract_status(from_date, to_date,
today)["label"]`, from S080: "Ends today", "Ends in 1 day", "Ends in 15 days"), `path`
(`CONTRACT_PATH`), `url` (`base_url + path`). **No `callout_number`, no `cost_note`, no price**:
`read_alert_contract` does not select them, so no text can show them.

**Push text** (`contract_text(facts)` → `(title, body)`; writing style B; dates DD-MM-YYYY):

| | Text |
|---|---|
| Title | `Contract ends in 60 days · SMTW` (`"Contract " + status_label` with its first letter lower case, then `" · "` and the site code); day 0: `Contract ends today · SMTW` |
| Body | `Atlas Copco AMC 2026–27 · Atlas Copco — ends on 31-03-2027. Renew it, or let it end.` |

The body names the vendor even when the title already does, as here (BR1-10): the title is free
text and need not name the firm, and one fixed form is simpler than a check for the name.

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

- The subject goes through `one_line`. *Contract number* is left out when empty (as `closed_email`'s
  `add`). Day 0: "ends today, on 31-03-2027". The sample number is made up; tests use
  `TEST/AMC/0001`.
- **Never in the email:** the price, the cost note, the call-out number, the documents; an email may
  be forwarded, so it holds only `contract:read_basic` fields (D8).

**When the contract changes before the task runs** (step 4 decides from the rows as they are then):
set inactive, renewed, To date edited (the next scan decides on the new date), or the To date passed
→ not sent. A recipient who lost the key or became inactive is left out (§ 5.6).

### 5.5 Locks

The database runs REPEATABLE READ. The contract row is not numbered in the global order
(`backend/equipment.py` LOCK ORDER); S080's and S081's `contracts.py` bullet places it: every
contracts.py write locks **one** contract row `FOR UPDATE`, **first** in its transaction, then a
`contract_equipment` line row, the vendor or the node shared (from S080, S081). S083's document
writes take "one owner lock, the contract row, first in its transaction, then only
`equipment_documents` rows" (S083 § 5.4, Draft).

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

The coder writes into `contracts.py`'s LOCK ORDER note, `equipment.py`'s `contracts.py` bullet and
`alerts.py`'s docstring: "The daily `contract_reminder_scan` (S084, `alerts.lock_contract_for_scan`)
locks several contract rows FOR UPDATE in id order, then writes only their reminder columns and
`task_queue` rows; every route holds at most one contract row, taken first, so no cycle." S081's
"Only contracts.py locks contracts … rows" becomes "Only contracts.py and the reminder scan …".

### 5.6 Recipients

`alerts.people_with_role_at_site(cur, site_id, roles, with_email=False)` → the ids of active people with a
membership at `site_id` whose role is in `roles`, in id order; with `with_email`, only those with
`people.email` set. **No unit condition:** a contract belongs to a site, and S080's keys are checked
at the site, whatever units the member works in (S080 § 5.5; `access_core.has_key_at`,
`backend/access_core.py:100`).

**DRY:** today's `people_at_unit` SQL (`backend/alerts.py:163-176`) moves into a private
`_people_with_role(cur, site_id, roles, unit_ids, only_ids, exclude_ids, with_email)`, where
`unit_ids=None` leaves out the unit condition. `people_at_unit` calls it with its list (an empty
list still returns `[]`, as today); `people_with_role_at_site` with `None`. The public functions stay
explicit; the `None` lives only inside the private one.

`alerts.contract_recipients(cur, contract, channel)` = `people_with_role_at_site(cur, contract["site_id"],
roles_holding(CONTRACT_AUDIENCE_KEY[channel]), with_email=(channel == EMAIL))`.

| Channel | Key (from S080) | `roles_holding` today | Who |
|---|---|---|---|
| Push | `contract:read` (`("maint_engineer",)`) | manager, engineer | the site's engineers and managers |
| Email | `contract:read_senior` (`("maint_manager",)`) | manager | the site's managers with an address |

- **By key, not by exact role** (as S074 D6): "engineers and managers" is exactly the holders of
  `contract:read` (R02 D10), "managers" those of `contract:read_senior` (R02 D5); if KLA changes a
  key's holders in `config_rbac.py`, the reminders follow. Not `contract:read_basic` for push: it
  is `("*",)`, and a technician does not renew contracts. Email by `read_senior`: renewing is a
  buying decision, made by who reads the price. A manager gets both.
- **Every recipient may open the contract** (`contract:read_basic` is held by every site role), so
  the tap never ends in S081's 404. **Nobody is left out as the actor:** the scan has none.
- **Admin and IT admin** have no membership: never recipients (IT admin holds `contract:edit` by its
  token, not `contract:read`). **No login, device or address:** nothing for that person;
  `email_send` reads the address (from the login token, S032) when it sends.

### 5.7 What you will get

`you_get(memberships)` (`backend/alerts_core.py:368`) gains, per membership, from the role's keys
(`compute_permissions`):

- when the role holds `contract:read`: `"Contracts ending at <site code>"`, after the membership's
  verify line;
- when the role holds `contract:read_senior`: `"Contracts ending at <site code>, by email"`, after
  its *Closed tickets* line.

The place is the **site code**, also for a membership with chosen units, and **also for a
membership without units**, whose other lines are skipped today (`if not place: continue`,
`:386`): the contract lines are computed before that `continue`, because `people_with_role_at_site`
reaches that person. Only `compute_permissions` moves before it; `keys_with_place.update(keys)`
(`:389`) stays after it, so a membership without units adds no countermeasure lines (BR1-07).

Example, a manager at SMTW.MCC2: "Breakdowns at SMTW.MCC2, escalations", "Improvements ready to
verify at SMTW.MCC2", "Contracts ending at SMTW", "Closed tickets at SMTW.MCC2, by email",
"Contracts ending at SMTW, by email", "Jobs assigned to you", the two countermeasure lines. A
technician, operator, supervisor or storekeeper: no contract line. The email line shows with or
without an address, as the *Closed tickets* line does. **The dot** (`showDot`) changes for nobody.

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
  `(PUSH, EMAIL)`; `CONTRACT_AUDIENCE_KEY` names the key per channel, because the push and email
  audiences differ. Its own task `contract_alert` (S074 D1: each record its own alert task),
  sharing `_push_to_people`, `enqueue_email` and the recipient query. Rejected: one kind per channel
  (a kind is an event, not a channel); `ticket_alert`'s email branch (ticket-shaped).
- **D2. The lead days are constants**, a departure from R02.5 ("settings (Settings ›
  Notifications)"). Q5.1 (a) and Plan.MD name 60 and 15; Fuji's contract asks for renewal two
  months before expiry (R02 § Log). A setting adds a card, its bounds and a rule for reminders
  already sent; nobody has asked to change the days; later it is one setting read in the scan.
  Constants stand for coding; the departure from R02.5's text is **flagged for KLA at gate B**
  (§ 9 Q1, BR1-03).
- **D3. "Once" by two marker columns holding the To date reminded for (v46)**, a departure from
  R02.5's "Migrations: none". Explicit, kept past the queue's 90-day purge
  (`DONE_TASK_RETENTION_DAYS`), and a changed To date re-arms the reminders with no route clearing
  anything (S074 D3). One column per reminder reads more plainly than a date plus a stage number.
  Rejected: a table `contract_reminders` (a table and a join for two facts; its gain, a reminder
  history, nobody asked for); the task queue as the memory (purged after 90 days); a window
  "exactly 60 days left" (misses a down worker and a contract added late). v46 stands for coding;
  the departure from R02.5's "Migrations: none" is **flagged for KLA at gate B** (BR1-03).
- **D4. The scan locks contract rows in id order and decides from them** (repo rule: decide from
  the locking read). Rejected: a conditional `UPDATE` without a read (the decision needs `days`, the
  renewal and both markers; split between SQL and the core, it drifts).
- **D5. Renewed = an active contract points at it** (§ 5.2), stated now so R02.4 builds on it.
  Rejected: "a later contract of the same vendor and site" (a guess; R02 D7 makes two contracts of
  one vendor normal).
- **D6. Quiet push, kept 24 hours.** No machine is down; S074 D7's rule for quiet alerts (no sound,
  Urgency `low`). The tickets' one-hour TTL would drop a once-only reminder to a phone off for an
  hour. `CONTRACT_TTL_SECONDS` is its own name, so it does not change by accident with the
  improvements'. Rejected: loud (§ 9 Q3).
- **D7. The markers are written even when no channel is set up or nobody would get it.** "Once" is
  about the event: switching email on later must not send old reminders (S074 D8).
- **D8. The texts carry only `contract:read_basic` fields.** An email is forwarded and a push shows
  on a locked phone. Rejected: the call-out number in the push (the machine card serves it, S082).
- **D9. No reminder at create; the scan decides.** One path for every reminder, and no route change.

## 8. Tests and acceptance

### 8.1 Pure core and migration

`backend/tests/test_alerts_core.py`:

- `contract_reminder_due` (today fixed at 30-01-2027): to 31-03-2027 (60 days), never sent →
  `FIRST`; 61 days → `None`; first sent for this date → `None`; first sent for an older date →
  `FIRST`; 15 days, nothing sent → `SECOND`; 15 days, first sent → `SECOND`; 16 days, first sent →
  `None`; 0 days (ends today), second not sent → `SECOND`; ended yesterday → `None`; not started
  (`from_date` tomorrow, 30 days left) → `None`; inactive → `None`; renewed → `None`; second sent
  for this date at 10 days → `None`; second sent for an older date at 10 days → `SECOND`.
- `should_send_contract`: as queued → True; inactive, renewed, `from_date` tomorrow, another
  `to_date`, `to_date` before today → False each; `to_date` today → True.
- `contract_scan_candidates` (in § 8.2, by the database): first sent for this To date at 30 days
  left → not a candidate; at 15 days → a candidate.
- `contract_text` / `contract_message`: the two texts of § 5.4 exactly; day 0 "Contract ends
  today · SMTW"; 1 day "Contract ends in 1 day · SMTW"; a title of 100 characters cut at 80; path
  `/contracts/12`, tag `contract-12`, quiet True; the facts hold no key `callout_number` or
  `cost_note`.
- `TestChannels`: `test_every_kind_has_channels_and_the_improvement_kinds_are_push_only` asserts
  `KINDS == TICKET_KINDS + IMPROVEMENT_KINDS + CONTRACT_KINDS`; new: `CHANNELS[CONTRACT_ENDING] ==
  ("push", "email")`, `CONTRACT_AUDIENCE_KEY` as § 3, `FIRST_REMINDER_DAYS == ENDING_SOON_DAYS ==
  60`, `SECOND_REMINDER_DAYS == 15`.

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

- **Scan:** 60 days left → one `contract_alert`, payload `{kind, contract_id, to_date}`,
  `first_reminder_for` = the To date, `updated_at` unchanged; a second run → none. 15 days after a
  first → one, `second_reminder_for` set. 10 days, nothing sent → one (second only),
  `first_reminder_for` stays NULL. 61 days, ended yesterday, `from_date` tomorrow, inactive → none.
- **Renewed** (D5): a second contract inserted through `db_rows` with `renewal_of_id` = the first
  and `active = 1` → no task; with `active = 0` → a task.
- **Re-arm** (§ 5.1): first sent, `to_date` moved 30 days later, then back to 60 days left → a new
  task; moved to 10 days left → a second-reminder task.
- **All or nothing:** `enqueue_contract_alert` monkeypatched to raise on the second contract → the
  run raises; no marker and no task stay.
- **Handler, push:** the engineer's and the manager's devices get one `push_send` each (§ 5.4's
  title, Urgency `low`, `ttl` 86400, path `/contracts/<id>`); the technician and the other site's
  manager get none. **Email:** one `email_send` for the manager with an address (payload
  `person_id`, § 5.4's subject, no `@` in it), none for the one without or for the engineer. **A
  manager with no units** (`all_units = 0`, no `person_units`) gets both.
- **Handler, no longer true:** inactive, renewed, `to_date` edited, `to_date` before today → done,
  no send rows. **Push off** (`push_off`): email rows only; **email off** (`email_off`): push rows
  only; both off → no rows, and the scan still writes the markers.
- **Through the worker:** `Worker.run_once` with `SCHEDULE` patched to `[("contract_reminder_scan",
  "00:00")]` (as `backend/tests/test_worker.py:131`), `push_sender.send` and `mail_sender.send`
  faked (as `fake_send` in `test_alerts.py` and `test_closed_email.py`): every row `done`, the fakes
  called with the texts. No test reaches a real service (`no_real_push`, `smtp_test_values`).
- **Bad tasks:** the scan with a payload; `contract_alert` with an unknown kind, no `contract_id`,
  a bad `to_date`, a missing contract → BadTask.

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
- Unchanged: `backend/tests/test_rbac.py` `test_role_matrix` (no new key); `backend/tests/conftest.py`
  `_TABLES` (no new table); S080's `test_migration_v43.py`, S081's `test_migration_v44.py`, S083's
  migration test (each slices its own range); S080's `test_contracts_api.py` (no route change; § 9
  A4).

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
contract: the **IT Admin** login (*Account*: IT admin; *Network*: the company network, as S013
refuses IT admin on mobile data, BR1-09) adds it in Masters › Contracts at SMTW, title "TEST
reminder check — not a real contract", any active vendor, From today, **To 30 days from today**.
KLA tells the SMTW engineers and managers the day before: every one of them gets these reminders.
IT Admin sets the contract inactive the day the second reminder arrives. *Where*: production, per
row. Where the rows finally run is KLA's choice at gate B (§ 9 Q4, BR1-02).

1. **Important.** The engineer test login's phone has notifications on (steps 1 and 4 of *Phone
   set-up for notifications (S021)*). After **08:00 the next day** it shows **Contract ends in 29
   days · SMTW**, without sound; a tap opens the contract page. That day IT Admin changes the To
   date to **10 days from today**; after 08:00 the following day the phone shows **Contract ends in
   9 days · SMTW**, and it **replaces** the first reminder. Done by IT Admin.
2. **Important. KLA only** (a manager at SMTW with an address). On both mornings of row 1, the email
   "Contract ends on <date>: TEST reminder check — not a real contract (SMTW)" is in KLA's Outlook,
   **not in junk**; it shows the vendor, type, site and period, **no price and no call-out
   number**, and its link opens the contract after the login.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs and the whole suite at Normal green once.
- `tooling\schema-docs.bat check` exits 0.
- By the worker (§ 8.2): each reminder reaches the right devices and addresses once per To date,
  never after a renewal, never for an inactive contract.

## 9. Open questions and assumptions

- **Q1. Lead days fixed or settings? Flagged for KLA at gate B** (BR1-03). Coding goes ahead with
  (a) and v46: Plan.MD § 2 item 9 and Q5.1 (a) already say 60 and 15 days; only R02.5's text says
  settings and "Migrations: none" (D2, D3).
  - **(a) Constants 60 and 15 — recommended.** No new card; the badge and the first reminder share
    `ENDING_SOON_DAYS`. A setting can follow if the plant asks.
  - (b) Two settings in Settings › Notifications: one more card and its rules.
- **Q4. Where the device checks run, and who gets the test reminder. For KLA at gate B** (BR1-02;
  the checks run after the commit, so coding does not wait).
  - **(a) Production at SMTW, everyone warned the day before — recommended** (§ 8.5 as written).
    The only end-to-end test of push; the reminders are quiet and the title says "TEST … not a real
    contract".
  - (b) A test site in production holding only the test logins. The repo names none:
    `docs/steps/device-checks.md` uses a TEST machine at SMTW.MCC2, never a TEST site. It would need
    a site row and a unit (visible in every site filter on production) and memberships for the
    engineer test login and KLA (manager) there; then nobody else is reached.
  - (c) The email row on the dev server, as S032 row 30 did (`DEV_STUB_EMAIL` and the local
    `SMTP_*` values, the scan enqueued by hand); the push row stays on production as (a), because
    push cannot run on the dev server (plain HTTP).
- **Q2. The scan's time: 08:00 IST — recommended**, with the improvement scan, so the daily alerts
  come at one hour (Plant-Facts § 5 leaves the shift pattern TBD). Another time is one string.
- **Q3. Quiet or loud push: quiet — recommended** (D6).
- **A1.** v42–v46 ship in one release, so production holds no contract before v46.
- **A2.** A contract at a site set inactive is reminded like any other; the memberships decide.
- **A3.** S083 keeps v45 and its one contract-row lock (S083 § 4.1, § 5.4, still Draft).
- **A4.** S080's `_contract_out` sends named fields only, so the new columns stay out of the API;
  otherwise the coder leaves them out there (§ 8.3).
- **A staleness check is due before coding** (S080–S083 coded after this brief): `ENDING_SOON_DAYS`,
  `contract_status`'s labels, `CONTRACT_TYPES`, the keys and holders, `renewal_of_id` and
  `ix_contracts_renewal_of`, the `contracts.py` LOCK ORDER note, S081's route, the migration number.
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
  changes `alerts.py`, `email_core.py` and `push_core.py`, which § Order does not list; R02.5's
  scope-B push text ("Contract ends in 15 days: Atlas Copco AMC 2026–27 (SMTW). Renew it or let it
  end.") becomes the app's title · place / body form of § 5.4 (BR1-11).
- **No defining question.** Gate R answered Q5.1 (a); the choices above are inside it.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header, § 3, § 5.3, § 5.4, § 5.7, § 7 D2 and D3, § 8.1, § 8.5, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): § 8.5 row 1 says "10 days from today", so the second reminder is due ("Contract ends in 9 days") and replaces the first. |
| BR1-02 minor | KLA's decision, pending: § 8.5's rows stay as written, with the warning the day before and the contract set inactive the day the second reminder arrives; § 9 Q4 gives the options (a) production at SMTW (recommended), (b) a test site (none exists; what it needs), (c) the email row on the dev server. The checks run after the commit, so coding does not wait. |
| BR1-03 minor | KLA's decision, pending: constants 60 and 15 and migration v46 stand for coding (Plan.MD § 2 item 9 and Q5.1 a say 60 and 15 days); the departure from R02.5's "settings" and "Migrations: none" is flagged for KLA at gate B (D2, D3, § 9 Q1). |
| BR1-04 minor | Accepted (a): `alerts_core` imports S081's `contracts_core.TYPE_SHORT` for `type_word`; `CONTRACT_TYPE_WORDS` and `contracts_core.py` leave § 3 (19 code and test files). |
| BR1-05 minor | Accepted (a): the function is `alerts.people_with_role_at_site` everywhere; § 3 says why (`tickets.people_at_site` is the people picker). |
| BR1-06 – BR1-12 nits | Accepted, as recommended: `_payload_time` takes the task name (§ 3, § 5.4); `keys_with_place.update` stays after the `continue` (§ 5.7); `should_send_contract` also checks `from_date <= today` (§ 5.4, § 8.1); IT Admin's account and network in § 8.5; the vendor stays in the push body, stated (§ 5.4); the push text restyle in § 9's roadmap corrections; the candidate query also leaves out a contract whose first reminder is sent for its To date with more than 15 days left, the rule stated exactly (§ 5.3, § 8.1). |
