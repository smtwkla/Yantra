```
Step: S074 — Improvement alerts
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066–S069 (gate B), S070 (being coded); S071–S073 coded before S074
Status: Approved 30-10-2026 by KLA (delegated: R05 gate R, "start coding unless a defining question")
From: R05.5
```

# S074 — Improvement alerts

## 1. What will be built

R05.3 gives each countermeasure an owner and a due date (S070, S071); R05.4 gives the improvement
a watch that ends on a date and a verified close (S072, S073). Nothing tells the owner, the lead or
the verifiers when it is their turn: they must open the list. **R05.5 adds three push alerts**
(gate R, Q5.1 (a)), so that no countermeasure and no ended watch waits unseen:

1. ***Countermeasure for you*** — to the owner, when an engineer adds a countermeasure with them as
   owner, or changes its owner to them. Not when the owner gave it to themselves.
2. ***Countermeasure overdue*** — once per due date, to the owner and the improvement's lead, the
   morning after the due date passes while the countermeasure is still open.
3. ***Ready to verify*** — once per watch end, to the site's verifiers (holders of
   `improvement:verify` at the improvement's site who can open it), the morning after the watch
   ends.

How they travel:

- **Push only**, through the S021 machinery: a task per alert fans out one `push_send` per
  device; the service worker opens the improvement page on a tap (`frontend/public/sw.js:38-63`,
  unchanged). Email stays off for these kinds (Q5.1 (a)); § 7 D9 says what adding it later costs.
- **Who gets nothing:** a person without a login (they have no device); a person who could not
  open the improvement (no `improvement:read` at its site, or not covering its unit, e.g. the
  storekeeper owner, S070 § 5.3). The lead still gets the overdue alert of such an owner's work.
- **One daily task**, `improvement_alert_scan` at **08:00 IST** in `scheduled_tasks.SCHEDULE`,
  finds the overdue countermeasures and the ended watches (S072 D1 left it to this step). Two new
  columns remember which due date and which watch end were alerted, so each is sent once
  (migration **v40**, § 4).
- **The widening for PM (R03.7):** `alerts_core` and the task handlers are ticket-shaped today.
  This step splits the ticket part from the shared part: kinds per record, one shared push fan-out
  (`_push_to_people`), and one shared recipient query (`alerts.people_at_unit`). R03.7 adds its
  PM kinds, its own alert task and its own daily scan on the same three pieces (§ 7 D1).
- ***What you will get*** on *My notifications* (`alerts_core.you_get`) gains the three lines, so
  the page and the fan-out agree (S021 BR2-06). The operator and the technician now get a line,
  so the bell's dot now shows for them on a device that is off (§ 5.8).
- **Settings › Background tasks** lists the new daily task with a plain label.

**After S074:** when the engineer gives the panel-cleaning countermeasure of IM-2026-10-001 to
Kannan, his phone shows *Countermeasure for you*. If it is still open the day after its due date,
Kannan and the lead get *Countermeasure overdue*. When the 90-day watch ends, the site's engineers
and manager get *Ready to verify*.

### Out of scope

- **Email** for these kinds (Q5.1 (b) was not chosen), and a daily summary email (Plan § 4.7,
  phase 5).
- A reminder before the due date ("due tomorrow"), or a repeat alert while it stays overdue.
- PM alerts (R03.7): this step only prepares the shared pieces.
- Any change to the improvement screens, *Me*, or the service worker. The service worker caches
  nothing and never will (§ Yantra Specifics, *Notifications*).
- A setting for the scan's time or for which kinds are on.
- Alerts about lessons (R05.6) or the register (R05.10).

## 2. Standards and practice

- **ISO 9001:2015 § 10.2.1 (c) and (d)** (nonconformity and corrective action). In plain words:
  (c) carry out the action needed; (d) review whether the action worked. The overdue alert pushes
  (c) to happen; *Ready to verify* starts (d) on time. "On time" is the roadmap's reading of
  § 10.2; the clause itself says "take action" and "review the effectiveness". Clause letters as
  Plan § 1 cites them; the next edition's numbers are *to verify* (R05 § Standards).
- **ISO 9001 § 7.4 and ISO 55001 § 7.4** (communication). In plain words: decide what is told, when,
  to whom and how. `alerts_core`'s tables are that decision (its docstring,
  `backend/alerts_core.py:6-9`), and *What you will get* shows each person their part.
- **TPM — focused improvement.** In plain words: a small team removes one chronic loss and checks
  that it stays away. The team loses the thread when actions slip unseen; the alerts keep the
  owner and the lead on it.
- **ISO 27001 A.5.34** (privacy of personal data). In plain words: keep personal data only where it
  is needed. A task's payload carries person ids and the giver's login, never an address
  (CLAUDE-COMMON § Conventions, *Mail relay values and personal addresses*); push addresses stay
  in `push_subscriptions`, read at send time.
- **ISO 27001 A.8.3** (information access restriction). In plain words: show each person only
  what their role allows. An alert goes only to a person who can open the improvement, so the text
  (serial, machine, countermeasure) never reaches someone the page would refuse (§ 5.6).

## 3. Where

S074 is coded after S073. Files marked **(S067)** are in the working tree; S069–S073 change some of
them first, so line numbers in `backend/improvements.py` and `backend/local_db.py` may move;
function and constant names are the anchors. Names new in S070–S073 are marked so. On 30-10-2026
S070 is being coded: its v38 (`backend/local_db.py:1186`, table `improvement_actions`) and its core
(`ACTIONS_MAX`, `backend/improvements_core.py:91`; `overdue_days`, `:433`) are in the tree, its
routes are not yet. S072's names (`watch_from`, `watch_days`, `watch_until`, the state
`watching`, the display state `ready_to_verify`, key `improvement:verify`) are new in S072.

### Backend

- `backend/alerts_core.py` — the pure rules (§ 5):
  - kinds per record: `TICKET_KINDS` (today's `KINDS`, `backend/alerts_core.py:26`),
    `IMPROVEMENT_KINDS = (ACTION_GIVEN, ACTION_OVERDUE, VERIFY_READY)`, `KINDS` = both;
  - `CHANNELS` (`:46`) gains the three kinds, push only;
  - `IMPROVEMENT_PATH = "/tickets/improvements/{id}"` beside `TICKET_PATH` (`:68`);
  - `given_alert`, `overdue_alert_due`, `ready_alert_due`, `should_send_improvement`,
    `improvement_facts`, `improvement_text`, `improvement_message`;
  - `you_get` (`:246`) gains the lines of § 5.8; the module docstring names both records.
- `backend/alerts.py` — the shell:
  - `IMPROVEMENT_ALERT = "improvement_alert"`, `IMPROVEMENT_SCAN = "improvement_alert_scan"`;
  - `enqueue_improvement_alert` (request side);
  - `people_at_unit` (the shared recipient query; `recipients` at `backend/alerts.py:120` becomes a
    thin call to it, same result);
  - `read_alert_improvement`, `scan_candidates`, `lock_for_scan` (worker side);
  - the module docstring: the improvement path and the scan's locks.
- `backend/task_handlers.py` — `improvement_alert`, `improvement_alert_scan`; the shared
  `_push_to_people` (taken out of `_push_fan_out`, `backend/task_handlers.py:132`);
  `ticket_alert` checks `TICKET_KINDS` (`:115`); `HANDLERS` (`:289`) gains the two.
- `backend/scheduled_tasks.py` — `SCHEDULE` (`backend/scheduled_tasks.py:12`) gains
  `("improvement_alert_scan", "08:00")`, after the purge.
- `backend/push_core.py` — `IMPROVEMENT_TTL_SECONDS = 86400` beside `ALERT_TTL_SECONDS`
  (`backend/push_core.py:40`).
- `backend/access_core.py` — `roles_holding(perm_key)` (pure; next to `expand_roles`,
  `backend/access_core.py:28`).
- `backend/improvements.py` **(S067)** — the countermeasure add and change routes (new in S070:
  `POST /api/improvements/<id>/actions`, `PUT /api/improvements/<id>/actions/<action_id>`) call
  `enqueue_improvement_alert` for *Countermeasure for you*; the LOCK ORDER note
  (`backend/improvements.py:19`) gains the scan.
- `backend/local_db.py` — migration **v40** (§ 4). No `_PRECONDITIONS` entry.
- `backend/equipment.py` — docstring only: the improvements bullet of the global LOCK ORDER
  (`backend/equipment.py:9`) gains the scan (several improvements in id order, each (6b) then its
  (6c) rows).

**Import direction** (BR1-06, as S067 states its own): `alerts_core` imports `improvements_core`
(pure → pure: `IMPROVEMENT_OPEN_STATES`, `ACTION_OPEN`, `watch_until`) and `access_core`;
`alerts.py` imports `access_core.roles_holding` and `improvements_core`, never `improvements.py`;
`improvements.py` imports `alerts`, as `tickets.py` does (`backend/tickets.py:101`). No cycle:
`alerts.py` imports `settings`, `task_queue` and `tickets_core` besides, none of which imports
`alerts` or `improvements`.

### Frontend

- `frontend/src/views/SettingsView.vue` — `TASK_LABELS` (`frontend/src/views/SettingsView.vue:208`)
  gains `improvement_alert_scan: "Send the morning alerts: overdue countermeasures and
  improvements ready to verify"` (BR1-10).

### Tests

- `backend/tests/test_alerts_core.py` — the new pure rules, the texts, `you_get` (§ 8.1, § 8.3).
- `backend/tests/test_access_core.py` — `roles_holding`.
- `backend/tests/test_improvement_alerts.py` (new) — the route enqueue, the scan, the handler
  (§ 8.2).
- `backend/tests/test_alerts.py` — one case in `test_a_malformed_task_is_a_bad_task`.
- `backend/tests/test_scheduled_tasks.py` — the new entry.
- `backend/tests/test_push_api.py` — `you_get` of the engineer (§ 8.3).
- `backend/tests/test_migration_v40.py` (new), on the pattern of `test_migration_v36.py`.
- `frontend/e2e/notifications.spec.js` — *What you will get* and the dot (§ 8.4).
- `frontend/e2e/settings.spec.js` — the Background tasks line (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema.md` and `docs/schema.html`: the columns `improvement_actions.overdue_alert_for` and
  `improvements.ready_alert_for`; the "migration v40" line. No Mermaid change (no new relation).
- `docs/Plan.MD` § 4.7: three rows (*Countermeasure for you*, *Countermeasure overdue*, *Ready to
  verify*), push, with their recipients.
- `.claude/CLAUDE.md` § Yantra Specifics, *Notifications (S021)*: the improvement kinds, the
  daily scan and its markers; § SMTW-Review: the point of § 9 and S074 in the spec map
  (`notifications`, `settings`).
- `docs/steps/device-checks.md`: two rows (§ 8.5).

**File count:** 19 code and test files (10 code: 9 backend, 1 frontend; 9 tests), 5 docs.

## 4. Data model

### 4.1 Migration v40

```sql
-- Improvement alerts (S074, R05.5): which due date and which watch end were alerted, so the daily
-- scan sends each once.  NULL = never alerted.  Another due date or another watch end alerts again.
ALTER TABLE improvement_actions
    ADD COLUMN IF NOT EXISTS overdue_alert_for DATE NULL AFTER due_date;
ALTER TABLE improvements
    ADD COLUMN IF NOT EXISTS ready_alert_for DATETIME NULL AFTER watch_from;
```

- **Why columns** (D3): "once" needs a memory of what was sent that lives as long as the record.
  The task queue drops done rows after 90 days (`DONE_TASK_RETENTION_DAYS`,
  `backend/company_settings.py:14`), and a window ("due yesterday") misses the days the worker was
  down and a due date moved into the past.
- **The value is the thing alerted for**, not a flag: `overdue_alert_for` holds the due date the
  overdue alert was queued for; `ready_alert_for` the watch end (`watch_until`, new in S072). A
  countermeasure whose due date moves (later or earlier) and is past is alerted again; an
  improvement whose watch end moves (extended, cut, or restarted, S072 D3 and D11) is alerted again
  at its new end. The rule is `!=`, literally once per due date and once per watch end (BR1-01).
  Nothing in S070's or S072's routes has to clear them.
- **No index.** The scan reads `improvement_actions` by `state` and `due_date` and `improvements`
  by `state`, once a day; both tables hold tens of rows (30 countermeasures per improvement at
  most, `ACTIONS_MAX`, `backend/improvements_core.py:91`). A full read is cheaper than a key to keep.
- **No `_PRECONDITIONS` entry.** Production holds no improvement row: v0.1.12 (`1baae21`) stops at
  v35 (S072 § 4.1), and v36–v40 ship together (S072 § 9's assumption, extended to this step). On
  rows the change is safe anyway: two nullable columns, nothing converted.
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS` on both.
- **Rollback:** a release before v40 never reads the columns. Run again on v40, it would not
  alert at all (it has no scan), so nothing doubles.
- **A departure from the roadmap** (R05.5 said "Migrations: none"): stated in D3.

### 4.2 What is computed, never stored

- Overdue: `due_date < today` (IST), as S070's `overdue_days` above 0
  (`backend/improvements_core.py:433`).
- The watch end: `watch_until(watch_from, watch_days)` (new in S072); ended when `now >= until`.
- Recipients, their devices, and every text: read and built when the alert task runs.

## 5. Rules

### 5.1 The three kinds

`alerts_core`: `ACTION_GIVEN = "action_given"`, `ACTION_OVERDUE = "action_overdue"`,
`VERIFY_READY = "verify_ready"`. The codes do not reuse S072's state name `ready_to_verify`, so a
grep for one never finds the other.

| Kind | Trigger (the line that queues it) | Recipients at send time | Once |
|---|---|---|---|
| `action_given` | S070's add route after its insert, and S070's change route after its update when `owner_id` changed: `given_alert(owner_id, actor_person_id, old_owner_id)` is true | the owner, when they may open it (§ 5.6) | per add or owner change |
| `action_overdue` | the daily scan: `overdue_alert_due(...)` is true for a locked countermeasure | the owner and the lead, each when they may open it; one person once | per due date (`overdue_alert_for`) |
| `verify_ready` | the daily scan: `ready_alert_due(...)` is true for a locked improvement | every verifier of the site who may open it | per watch end (`ready_alert_for`) |

- `given_alert(owner_id, actor_person_id, old_owner_id=None)`: true when `owner_id !=
  actor_person_id` and `owner_id != old_owner_id`. On an add `old_owner_id` is None. The actor
  is `current_person_id(cur)` (`backend/auth_utils.py:314`); a user with no Team record (admin)
  is None, so the owner is always told. A `PUT` that changes only the kind, the text or the due
  date sends nothing (D5).
- `overdue_alert_due(action_state, due_date, alerted_for, improvement_state, today)`: true when
  the improvement's stored state is open (`IMPROVEMENT_OPEN_STATES`,
  `backend/improvements_core.py:26`, widened by S072), the countermeasure is `open`, `due_date < today`, and
  `alerted_for` is None or differs from `due_date` (BR1-01: once per due date).
- `ready_alert_due(state, watch_from, watch_days, alerted_for, now)`: true when `state ==
  "watching"` (new in S072), `watch_from` (new in S072) is set, `now >= watch_until(watch_from, watch_days)`, and
  `alerted_for` is None or differs from that end (BR1-01: once per watch end). The stored state, never the display state: S072
  computes `ready_to_verify` only for output (S072 § 5.1, BR1-03 there).
- A countermeasure added with a due date already past (allowed, S070 D7) and still open the next
  morning is overdue and alerts then. That is true: it is open past its date.

### 5.2 The daily scan (`improvement_alert_scan`)

- **When:** daily at **08:00 IST** (`SCHEDULE`). The worker's `enqueue_scheduled`
  (`backend/worker.py:114`) enqueues it once a day, and once on return after a worker that was
  down over the time (`scheduled_tasks.due_tasks`). Why 08:00: the alerts are about planned work,
  so they arrive at the start of the day, not at night (§ 9 Q1).
- **No payload** (`_expect_no_payload`, `backend/task_handlers.py:59`): BadTask otherwise.
- **Steps, all in the worker's one transaction** (the handler commits nothing itself; the worker
  commits its writes with `mark_done`, `backend/task_handlers.py:3-7`):
  1. `SELECT NOW()` once: `now` (IST, the session clock, as `settings.get_tasks` reads it) and
     `today = now.date()`.
  2. **Candidates, one plain read each** (the transaction's first reads of a table: step 1's
     `SELECT NOW()` reads no table and opens no InnoDB snapshot, so the order stays; BR1-07):
     - countermeasures: `SELECT a.id, a.improvement_id FROM improvement_actions a JOIN improvements
       i ON i.id = a.improvement_id WHERE a.state = 'open' AND a.due_date < %s AND
       (a.overdue_alert_for IS NULL OR a.overdue_alert_for <> a.due_date) AND i.state IN (<open
       states>)`;
     - improvements: `SELECT id FROM improvements WHERE state = 'watching' AND watch_from IS NOT NULL
       AND watch_from + INTERVAL watch_days DAY <= %s AND (ready_alert_for IS NULL OR
       ready_alert_for <> watch_from + INTERVAL watch_days DAY)` (S072 § 9's assumption: this schema
       serves it).
     The plain read only narrows the work; nothing is decided from it.
  3. **Per improvement, in id order** (the union of both lists): (6b) `SELECT id, state,
     watch_from, watch_days, ready_alert_for, lead_id FROM improvements WHERE id = %s FOR UPDATE`;
     then its candidate countermeasures, in id order, (6c) `SELECT id, state, due_date,
     overdue_alert_for, owner_id FROM improvement_actions WHERE id = %s AND improvement_id = %s FOR
     UPDATE`. A row gone (never: nothing is deleted) is skipped.
  4. **Decide from the locked rows** with `overdue_alert_due` and `ready_alert_due` (§ 5.1). For each
     yes: `UPDATE improvement_actions SET overdue_alert_for = due_date WHERE id = %s`, or `UPDATE
     improvements SET ready_alert_for = %s WHERE id = %s` (the end just computed); then
     `enqueue_improvement_alert` (§ 5.3). Neither update stamps `updated_*`: an alert is not a
     change of the record (as S072 D16's settle).
  5. Log one line: "improvement_alert_scan: N overdue, M ready to verify".
- **What a run stores:**
  - success: the markers and the `improvement_alert` tasks, with `mark_done`, in one commit;
  - any exception (a lost connection, a deadlock 1213): everything rolls back, markers included;
    the queue retries after the back-off (internal and idempotent, `DEFAULT_MAX_ATTEMPTS` 3,
    `backend/task_queue.py:18`); a retry finds the same candidates;
  - three failures: the task is `failed`, counted on Settings › Background tasks; `due_tasks` sees
    it enqueued today and waits for tomorrow, whose run finds the same unmarked candidates.
    Nothing is lost; at worst a day late.
- **No bound needed on the candidates** (self-check 6): each improvement holds at most 30
  countermeasures (`ACTIONS_MAX`), and a plant has a handful of open improvements.

### 5.3 The alert task (`improvement_alert`)

**Enqueued** by `alerts.enqueue_improvement_alert(cur, kind, improvement_id, **fields)`, in the
caller's transaction (the route's or the scan's), so it commits or rolls back with the change that
caused it (`backend/alerts.py:1-8`'s rule). Payloads, all integers except where named:

| Kind | Payload |
|---|---|
| `action_given` | `{kind, improvement_id, action_id, person_id, given_by}`: `person_id` the new owner; `given_by` the actor's login (`actor()`), text |
| `action_overdue` | `{kind, improvement_id, action_id, due_date}`: `due_date` as `YYYY-MM-DD` text |
| `verify_ready` | `{kind, improvement_id, watch_until}`: `watch_until` as `YYYY-MM-DD HH:MM:SS` text |

**The handler**, in the worker's transaction, plain reads only (as `ticket_alert`,
`backend/task_handlers.py:108`):

1. Validate: `kind` in `IMPROVEMENT_KINDS`, the integers by `_ids` (`:98`), the dates parsed;
   else BadTask (failed at once).
2. `alerts.read_alert_improvement(cur, improvement_id, action_id)` → `(row, facts)`: the
   improvement (serial, title, stored state, `watch_from`, `watch_days`, `lead_id`, `unit_id`, its
   site, unit and machine codes, the machine's current `unit_id`) and, when `action_id` is given,
   the countermeasure of that improvement (kind, text, state, owner, due date, the owner's name).
   None when either is missing → BadTask.
3. `should_send_improvement(kind, improvement_state, watch_end, action, payload)` (pure):
   - `action_given`: the improvement open, the countermeasure `open`, and its `owner_id` still the
     payload's `person_id`;
   - `action_overdue`: the improvement open, the countermeasure `open`, and its `due_date` still the
     payload's `due_date`;
   - `verify_ready`: the stored state `watching` and `watch_until(…)` still the payload's
     `watch_until`.
   False → log "improvement_alert <kind> for IM-…: not sent, <reason>" and return (done).
4. Push not set up (`push_sender.enabled()` false) → log and return (done), as `_push_fan_out`
   does (`backend/task_handlers.py:134-136`).
5. Recipients (§ 5.6), the message (§ 5.4), then `_push_to_people(cur, people, message,
   IMPROVEMENT_TTL_SECONDS)`: one `push_send` per device (`alerts.subscription_ids`,
   `backend/alerts.py:154`), `max_attempts=PUSH_SEND_ATTEMPTS`. Log "improvement_alert <kind> for
   IM-…: n people, m devices".

**What it stores:** success: the `push_send` rows and `done`, one commit (all or nothing, so a
retry never doubles them). An exception: rollback, retried with the back-off; failed after 3.
`push_send` itself is unchanged (S021: it records its own failure and commits before raising).

**When the record changes before the task runs** (step 3 decides, from the rows as they are then):

| Change after the queueing | Result |
|---|---|
| The countermeasure is marked done or cancelled; the improvement is dropped or closed | not sent |
| The owner is changed again before the given alert runs | the first is not sent; the second change queued its own |
| The due date is moved after the overdue alert was queued | not sent; the next morning's scan decides on the new date |
| The watch is extended or restarted after the ready alert was queued | not sent; the scan alerts at the new end |
| The owner or the lead loses access, or becomes inactive | that person is left out (§ 5.6) |

### 5.4 The texts (writing style B)

`improvement_facts(improvement, action, giver_name, base_url)` builds one dict, as `ticket_facts`
(`backend/alerts_core.py:166`): `improvement_id`, `serial`, `title` (cut to 80), `site_code`,
`unit_code`, `machine_code`, `action_id`, `action_text` (cut to 80, `DESCRIPTION_CUT`), `due_date`,
`owner_name` (first name), `giver_name` (first name), `watch_until`, `path`, `url`.
`improvement_text(kind, facts)` → `(title, body)`; `place` = `"{site}.{unit} · {machine}"`, as for
tickets. Dates are DD-MM-YYYY.

| Kind | Title | Body |
|---|---|---|
| `action_given` | `Countermeasure for you · SMTW.MCC2 · HP003` | `IM-2026-10-001 · Clean the panel contactors — due 08-11-2026, from Ravi` (no giver name: `… — due 08-11-2026`) |
| `action_overdue` | `Countermeasure overdue · SMTW.MCC2 · HP003` | `IM-2026-10-001 · Clean the panel contactors — was due 08-11-2026, owner Kannan` |
| `verify_ready` | `Ready to verify · SMTW.MCC2 · HP003` | `IM-2026-10-001 · Press does not start — the watch ended on 18-02-2027. Check if the fix worked.` |

- "Countermeasure" is the app's word (S070 § 2, the S071 card); "Ready to verify" is S072's state
  word. The overdue body names the owner, because the lead gets the same text.
- `giver_name`: the first name of the person whose login is `given_by`, else the login
  (`first_name`, `backend/alerts_core.py:148`), as the *assigned* alert names its assigner.

`improvement_message(kind, facts)` → `{title, body, path, tag, quiet}`:

- **path** `IMPROVEMENT_PATH.format(id=…)` = `/tickets/improvements/12` (the route,
  `frontend/src/router/index.js:73`). `sw.js` opens any same-origin path (`targetUrl`,
  `frontend/public/sw.js:38`), so it needs no change. A tap opens the top of the page; the
  countermeasure card is below the problem and the why-why (S071). Accepted for this step; an
  anchor on S071's card could be named in the path later (`sw.js` keeps a fragment, `new URL(path,
  origin)`) (BR1-11).
- **tag** `improvement-action-<action id>` for the two countermeasure kinds (an overdue alert
  replaces the given one on the phone), `improvement-<id>` for *Ready to verify*.
- **quiet** true for all three (D7): Urgency `low` and no sound, as a defect
  (`push_core.send_task_payload`, `backend/push_core.py:167`).
- **TTL** `IMPROVEMENT_TTL_SECONDS` = 86400 (24 hours), not the tickets' 3600 (D7).

### 5.5 Request side: the given alert in S070's routes

- **Add** (S070 § 5.6 *Add*): after the insert (and S072's line and settle), when
  `given_alert(owner_id, current_person_id(cur), None)`: `enqueue_improvement_alert(cur,
  ACTION_GIVEN, improvement_id, action_id=<new id>, person_id=owner_id, given_by=actor())`.
- **Change** (S070 § 5.6 *Change*): when the body changed `owner_id`, after the update, with
  `old_owner_id` from the (6c) locked row: the same call.
- **Locks:** none new. The task insert touches only `task_queue`, which has no foreign key. The
  route's sequence is S070's and S072's, unchanged.
- **A refused add or change** rolls back, the task too: no alert for a countermeasure that does not
  exist.
- **No other route queues an alert.** Mark done, cancel, drop, notes, verify and every S067–S069
  write send nothing (D5).

### 5.6 Recipients: who may open it

`alerts.people_at_unit(cur, site_id, unit_ids, roles, only_ids=None, exclude_ids=(),
with_email=False)` → the ids of active people with a membership at `site_id` whose role is in
`roles`, covering one of `unit_ids` (all units of the site, or a `person_units` row), optionally
only among `only_ids`, less `exclude_ids`, in id order. It is today's `recipients` query
(`backend/alerts.py:120-137`) with a list of units and an `only_ids` filter. `recipients` calls it
with the ticket's site, `[unit_id]` and `AUDIENCE[kind]`, so ticket alerts keep their result.

`access_core.roles_holding(perm_key)` (pure) → the site roles that hold the key through
`ROLE_INCLUDES`, in `SITE_ROLES` order; a wildcard key gives every site role. Today:
`roles_holding("improvement:read")` = operator, supervisor, technician, engineer, manager;
`roles_holding("improvement:verify")` = engineer, manager (new key in S072).

| Kind | Call |
|---|---|
| `action_given` | `people_at_unit(cur, site, units, roles_holding("improvement:read"), only_ids=[person_id])` |
| `action_overdue` | the same with `only_ids=[owner_id, lead_id]` (one id once when they are the same person) |
| `verify_ready` | `people_at_unit(cur, site, units, roles_holding("improvement:verify"))` |

- `units` = `[improvement.unit_id, the machine's current unit_id]`, the two units S067's access
  predicate accepts (`backend/improvements.py:12-14`, `_visible_condition`). So a recipient can
  open what the alert names; a person who would get 404 gets no alert (A.8.3).
- **Exactly by key, not by exact role:** ticket alerts match roles exactly (S021 § 7 decision 6:
  "engineers" means engineers). These alerts follow the key the action needs (Q5.1 (a): "holders
  of `improvement:verify`"), so the manager gets *Ready to verify* too (D6).
- **Nobody is left out** of the scan's alerts (no actor). The given alert's actor is left out at
  the queueing (`given_alert`), so its payload has no exclude list.
- **No login, no device:** `push_subscriptions` rows exist only for people who logged in and
  turned notifications on. A person without a login gets nothing; the lead still gets the overdue
  alert (Q3.2 (a)).
- **Admin and IT admin** have no membership and no Team record: never recipients.
- **Accepted gap (BR1-08):** `people_at_unit` reads memberships at the improvement's site only. A
  machine moved to a unit of another site is visible to that site's readers through `m.unit_id`
  (`unit_access_condition`); they get no alert. Rare: the improvement's site is fixed (S067).

### 5.7 Locks

The database runs REPEATABLE READ. The global order (`backend/equipment.py:9`): … (6b) the
improvement row → (6c) the countermeasure row (new in S070) → (7) the ticket row.

- **The routes** (§ 5.5): no new lock.
- **The scan** (§ 5.2): per improvement in id order, (6b) `FOR UPDATE`, then its candidate (6c)
  rows `FOR UPDATE` in id order; the two marker `UPDATE`s are on rows already held. Several (6b)
  rows are held at once, always in id order.
- **The alert task:** plain reads only, as `ticket_alert`.

**No new deadlock cycle, checked against the notes:**

- Every route holds at most one (6b) row while it waits for anything (S070 § 5.6, S072 § 5.7).
  *Not effective* holds (6) and the old (6b), then inserts a new improvement row: an insert takes
  no lock on an existing row the scan holds or waits for. So no route holds a (6b) row the scan
  wants while waiting for a (6b) row the scan holds.
- (6b) → (6c): the scan takes them in the same order as every route and the documents path (S070
  § 5.6). S072's drop locks its countermeasures in id order after (6b); the scan does the same.
- The scan takes no ticket, person, unit or cause lock, and inserts only into `task_queue`.
- A deadlock all the same (1213) rolls the scan back and retries it (§ 5.2).

The coder writes the scan into `improvements.py`'s LOCK ORDER note, `alerts.py`'s docstring and
`equipment.py`'s improvements bullet.

### 5.8 What you will get

`you_get(memberships)` (`backend/alerts_core.py:246`) gains, from the role's keys
(`compute_permissions`, `backend/access_core.py:44`), so the page follows `config_rbac.py`:

- per membership with a place (all units, or chosen units), when its role holds
  `improvement:verify`: `"Improvements ready to verify at <place>"`, after that membership's ticket
  line and before its email line;
- once, after "Jobs assigned to you", when any membership with a place holds `improvement:read`:
  `"Countermeasures given to you, and when they are overdue"`;
- once, after it, when any membership with a place holds `improvement:edit` (who may lead,
  `improvements_core.may_lead`): `"Overdue countermeasures of improvements you lead"`.

Examples: an engineer at all of SMTW: "Breakdowns and defects at SMTW, escalations", "Improvements
ready to verify at SMTW", "Jobs assigned to you", "Countermeasures given to you, and when they are
overdue", "Overdue countermeasures of improvements you lead". A technician: "Jobs assigned to you",
"Countermeasures given to you, and when they are overdue". An operator: the countermeasure line
only. A storekeeper: nothing (no `improvement:read`).

**The dot** (`showDot`, `frontend/src/stores/notifications.js:46`) shows when `you_get` is not
empty and the device is off. The operator now has a line, so the operator now sees the dot: right,
because an operator can own a countermeasure (S070 D3) and would get its alerts. No frontend
change: the store reads the server's list.

### 5.9 The database down

- The routes go through `get_db()`: 503 while the database is down (S070 § 5.9), so no alert is
  queued for a write that did not happen.
- The worker reconnects on its own (S013). A scan due while the database was down runs once when
  it is back (`due_tasks`); the clock-based rules find the same overdue countermeasures and ended
  watches, and the markers stop doubles.
- Push not set up on the server: the alert task logs and is done (§ 5.3 step 4); the markers stay
  written, so turning push on later does not send a backlog of old alerts (D8).

## 6. API

No new route and no changed answer. `POST` and `PUT` of S070's countermeasure routes answer as
before; they also queue a task. `GET /api/push/config` (`backend/push.py:70`) answers more
`you_get` lines (§ 5.8). `GET /api/settings/tasks` (`backend/settings.py:347`) lists the new
scheduled task after `purge_access_log`.

## 7. Design decisions

- **D1. Widen by record, share the push fan-out and the recipient query.** `alerts_core` keeps the
  rules and the texts per record (`TICKET_KINDS`, `IMPROVEMENT_KINDS`); each record has its own
  alert task (`ticket_alert`, `improvement_alert`), because what "still worth sending" means and
  which facts the text needs differ per record. The shared pieces are `CHANNELS`,
  `_push_to_people` (devices → `push_send`) and `alerts.people_at_unit`. R03.7 adds `pm_alert` and
  its scan on these. Rejected: one generic `record_alert` task with a record type in its payload
  (one handler with a branch per record; a PM change would touch the ticket path); copying
  `_push_fan_out` for improvements (two fan-outs drift, DRY).
- **D2. A daily scan, as the roadmap says, not a task timed at the watch end.** One run at 08:00
  finds both kinds. *Ready to verify* is at most a day late on a watch of 30 to 365 days. Rejected:
  queueing a `verify_ready` task with `scheduled_for` = the watch end whenever S072 settles a watch
  (exact, but every watch change in S072's routes must queue or cancel one; a missed path loses
  the alert). Rejected: a scan every hour (wakes nobody sooner who would act sooner).
- **D3. "Once" by a marker column holding what was alerted for (v40), a departure from the
  roadmap's "Migrations: none".** It is explicit, survives the queue's 90-day purge, and another
  due date or watch end alerts again without any route clearing it. S072 D1 suggested the other
  road: R05.5 "may store a line then", a `watch_ended` line in `improvement_events` (BR1-02). The
  columns still win, for three reasons: (1) a stored `watch_ended` line would double S072's
  computed `watch_ended` line (S072 § 5.6) unless that line is removed; (2) "once per due date"
  needs a value to compare, the due date alerted for, which a line holds only in its text; (3) the
  scan's candidate query would join `improvement_events` per countermeasure. One nullable column
  per table is the smaller change. Rejected: lines as the markers (S072 D1's suggestion, for the
  reasons above); the task queue as the memory (a JSON search in an operations table that the
  purge empties after 90 days, so a countermeasure overdue for 91 days alerts again); a window
  "due date = yesterday" (misses the days the worker was down and a due date moved into the
  past).
- **D4. The scan locks in the global order and decides from the locked rows.** The markers are
  written on (6b) and (6c) rows, so it takes them as every route does. Rejected: a conditional
  `UPDATE … JOIN improvements` without (6b) (takes (6c) first and the improvement shared after it,
  the reverse order).
- **D5. *Countermeasure for you* on an add and on a change of owner; nothing on other edits.** The
  new owner learns of the work either way (the orchestrator's open point, answered yes). A new
  due date or text is the owner's to see on *Me*; an alert per edit is noise. The old owner gets
  nothing: the countermeasure leaves their list. Rejected: alert on every change (noise); add only
  (a reassigned job reaches nobody).
- **D6. Recipients by the key the alert is about, and only people who can open the record.** The
  verifiers are the holders of `improvement:verify`; owner and lead are kept only when they hold
  `improvement:read` covering the unit. Rejected: exact roles as the ticket alerts (Q5.1 names
  the key's holders); sending to an owner who cannot open it (the tap ends in 404, and the text
  reaches someone the page refuses).
- **D7. Quiet, with a 24-hour TTL.** No machine is down: the alert must not sound like a
  breakdown, which the floor learns to answer at once. "Quiet" is the existing rule for every quiet
  alert (`push_core.send_task_payload`, `backend/push_core.py:176`): no sound **and** Urgency
  `low`, kept as it is (BR1-03). RFC 8030 § 5.3's table delivers `low` when the device is on
  power or on Wi-Fi, so a technician on battery and mobile data may get *Countermeasure for you*
  only later in the day (how FCM and Apple's service apply it is *to verify*); a 24-hour TTL keeps
  it on the push service until then, where the tickets' one hour would drop it. The device check
  says so (§ 8.5). Rejected: silent with Urgency `normal` (a second rule for quiet alerts, in
  `push_core`; can follow if the device check shows long delays). Rejected: loud (breakdown sound for planned work); the tickets' 3600 s (an
  alert sent once a day is lost when the phone is off for an hour).
- **D8. The markers are written even when push is off or nobody has a device.** "Once" is about
  the event, not the delivery: switching push on later must not fire a backlog. The task logs who
  it found. Rejected: write the marker only after a send (a person who turns notifications on a
  month later gets a month of old overdue alerts at once).
- **D9. Push only; email is one `CHANNELS` entry plus its text later.** `improvement_alert` sends
  push only. Adding email needs a `CHANNELS` entry, an email text per kind and the email branch
  of the handler, with `people_at_unit(…, with_email=True)` (it already supports it). Stated
  plainly, as the roadmap's "one entry" understates it.

## 8. Tests and acceptance

### 8.1 Pure core (`test_alerts_core.py`, `test_access_core.py`)

- `KINDS` = `TICKET_KINDS + IMPROVEMENT_KINDS`; every kind has a `CHANNELS` entry; the three
  improvement kinds are push only.
- `given_alert`: owner = actor → False; actor None → True; change to the same owner → False;
  change to another → True.
- `overdue_alert_due`: due yesterday, open, never alerted → True; due today → False; done,
  cancelled → False; improvement closed or dropped → False; alerted for this due date → False;
  alerted for an earlier date, due date moved later and passed → True; alerted for a later date
  (moved earlier, still past) → True (BR1-01).
- `ready_alert_due`: watching, a minute before the end → False, at the end → True; alerted for
  this end → False; extended (end later than the marker) and passed → True; cut (end earlier than
  the marker) and passed → True (BR1-01); `actions_open` with an
  old `watch_from` → False; a closed state → False.
- `should_send_improvement`: each row of § 5.3's change table.
- `improvement_text`: the three texts of § 5.4 exactly; the given text without a giver; the action
  text and the title cut at 80; dates DD-MM-YYYY.
- `improvement_message`: path `/tickets/improvements/12`, tags `improvement-action-5` and
  `improvement-12`, quiet True.
- `roles_holding`: `improvement:read`, `improvement:verify`, a wildcard key (every site role), an
  unknown key (none: fail-closed).

### 8.2 Shell (`test_improvement_alerts.py`, new)

Fixtures as `test_alerts.py` (`plant`, `add_device`, `db_rows`, `backend/tests/test_alerts.py:66-101`)
and S070's improvement set-up through `ticket_helpers.py`; each test its own ticket and improvement,
so the kept worker database gives the starting state. Push on through the same fake as
`test_alerts.py`.

- **Given, request side:** an engineer adds a countermeasure owned by a technician → one
  `improvement_alert` task with `action_given`, `person_id`, `given_by`; owned by the engineer
  themselves → none; a `PUT` of the due date only → none; a `PUT` to another owner → one; a refused
  add (400) → none.
- **Given, handler:** the owner's two devices get two `push_send`; the owner without a login → none;
  a storekeeper owner → none (no `improvement:read`); the owner changed again before the run →
  not sent; the countermeasure cancelled before the run → not sent; push off → done, none.
- **Scan, overdue:** the test moves `due_date` back with `db_rows` (as S070 § 8.2); one run → one
  task, `overdue_alert_for` = the due date; a second run → no new task; the due date moved later
  and back past → a new task; a done one → none; the owner and the lead each get their devices, the
  same person once; an owner without a login → only the lead's devices.
- **Scan, ready:** `watch_from` set 91 days back with `db_rows` on a `watching` row → one task,
  `ready_alert_for` = the end; a second run → none; `watch_days` raised so the end is later and
  passed → a new task; the handler reaches the site's engineer and manager covering the unit, not
  an engineer of another unit, not the technician.
- **Scan, all or nothing:** a handler fault after the first marker (monkeypatched
  `enqueue_improvement_alert` raising on the second call) → the run raises, no marker and no task
  stay.
- **Through the worker** (BR1-04): `Worker.run_once` with `SCHEDULE` patched to
  `("improvement_alert_scan", "00:00")` (as `backend/tests/test_worker.py:129`) drains every due
  task, `push_send` too, so the sender is faked: `monkeypatch.setattr(push_sender, "send",
  fake_send(201))` (`fake_send` at `backend/tests/test_alerts.py:443`, used so at `:559`). Assert the scan `done`, each
  `improvement_alert` `done`, the `push_send` rows `done`, and the fake's calls. No test reaches
  the real push service.
- **Through the worker, push off** (D8, BR1-04): the same with `push_off`: the scan writes the
  markers and queues the alert tasks; each alert task logs "push is not set up" and is done; assert
  the markers and the task rows, and that a second run queues nothing.
- **Bad tasks:** the scan with a payload; `improvement_alert` with an unknown kind, a missing
  `action_id`, an action of another improvement → BadTask.

### 8.3 Existing tests that break or run again

- `backend/tests/test_alerts_core.py` `TestYouGet`: the expected lists gain § 5.8's lines in
  `test_engineer_all_units`, `test_supervisor_at_two_units`, `test_manager_at_two_sites`,
  `test_manager_at_one_unit`, `test_technician_gets_assigned_jobs`; `test_nothing_for_other_roles`
  keeps the storekeeper and moves the operator to a test of its own (the countermeasure line).
  `test_a_membership_without_units` and `test_no_memberships_it_admin` stay green.
- `backend/tests/test_alerts_core.py` `TestChannels`: green; gains the improvement kinds.
- `backend/tests/test_push_api.py`
  `test_push_on_with_the_public_key_and_what_you_get` (`:52-57`): the engineer's list gains the
  three lines.
- `backend/tests/test_alerts.py` `test_a_malformed_task_is_a_bad_task` (`:366`): gains a
  `ticket_alert` with kind `action_given` → BadTask. `TestFanOut` stays green (`recipients` keeps
  its result through `people_at_unit`).
- `backend/tests/test_scheduled_tasks.py` `:17`: green; gains the new entry.
- `backend/tests/test_worker.py` `TestTasksCard` (`:194-212`): reads `tasks[0]`, still
  `purge_access_log` (the new entry comes after it): green.
- `backend/tests/test_rbac.py` `test_role_matrix`: unchanged (no new key).
- `backend/tests/conftest.py` `_TABLES` (`:162`): unchanged (no new table; the new columns are on
  tables already in it).
- `test_migration_v36.py`, `test_migration_v37.py`, and S070's and S072's `test_migration_v38.py`
  and `test_migration_v39.py` (new in S070, S072): unchanged (each slices its own range).
- S070's countermeasure tests (`backend/tests/test_improvement_actions_api.py`, new in S070 and in
  the tree since 30-10-2026; S070 is still being coded): the coder checks them, and any other S070
  test, for a
  `task_queue` assertion, as the add and change routes now insert a task (BR1-05).
- `backend/tests/test_alerts.py` and `backend/tests/test_closed_email.py`: run whole, as they pin
  the ticket recipients that `people_at_unit` now serves (`TestFanOut`, `TestEscalation`, the
  assigned tests, `test_closed_email.py::TestFanOut`).

### 8.4 Automated (e2e)

- `frontend/e2e/notifications.spec.js` "S021 A1: What you will get — …" (`:196-205`): the
  technician's exact list (`:203`) becomes `["Jobs assigned to you", "Countermeasures given to
  you, and when they are overdue"]`; a new step: the engineer's card contains "Improvements ready
  to verify at SMTW".
- `frontend/e2e/notifications.spec.js` "S021: the dot shows to people who would get alerts …"
  (`:136`): `operator` joins the dot list (S074: the operator now gets countermeasure alerts).
- `frontend/e2e/settings.spec.js`, new test "S074: Background tasks lists the improvement alerts at
  08:00" (IT admin): the card shows "Send the morning alerts: overdue countermeasures and
  improvements ready to verify".
- Targeted run: `tooling/run-e2e-tests.bat e2e/notifications.spec.js e2e/settings.spec.js
  e2e/screens.spec.js`; the whole suite at Normal once at the end. `npx vite build` in
  `frontend/`.

### 8.5 On a real device (`docs/steps/device-checks.md`)

Push needs HTTPS and the VAPID keys, so both rows run on production, on the TEST machine's
improvement, with a phone set up as § *Phone set-up for notifications (S021)* says. In the
device-check table: *Network* "Company Wi-Fi, or mobile data with the phone charging"; *Where*
"Production, the TEST machine" (BR1-09).

1. **Important.** The engineer test login gives a countermeasure to the technician test login
   (whose phone has notifications on). The phone shows *Countermeasure for you · …*, quietly; a tap
   opens the improvement page. Keep the phone charging or on Wi-Fi: the alert is sent with Urgency
   low, which may otherwise hold it until then (D7, BR1-03).
2. The engineer adds a countermeasure owned by the technician, due on an earlier day (back to the
   ticket's date). Wait until after 08:00 the next day. Then the technician's phone and the
   engineer's (the lead) show *Countermeasure overdue*; on the technician's phone it replaces the
   earlier alert. Phones charging or on Wi-Fi, as row 1.

*Ready to verify* needs a watch of at least 30 days: tested automatically only.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs and the whole suite at Normal green once.
- By API and the worker: the three alerts reach the right devices once each, as § 8.2 shows.
- `docs/schema.md` and `docs/schema.html` show v40.

## 9. Open questions and assumptions

- **Q1. The scan's time.** Answered 30-10-2026: **08:00 IST**, as proposed. Plant-Facts § 5 leaves
  the shift pattern TBD; another time is one string in `SCHEDULE`.
- **Q2. A given alert on a change of owner.** Answered 30-10-2026: **yes**, the new owner only, as
  proposed (D5).
- **Q3. Quiet or loud.** Answered 30-10-2026: **quiet**, as a defect, as proposed (D7, BR1-03).
- **A staleness check is due before coding.** This brief was approved while S070 was being coded
  and before S071–S073 were. Check S070's add and change routes (their names, the owner-change
  path, `current_person_id`), S072's `watch_until`, `IMPROVEMENT_OPEN_STATES` and v39's column
  order (`watch_from`), the migration number v40, and the lock notes in `improvements.py` and
  `equipment.py` against the code as written.
- **The migration** (D3) departs from the roadmap's "Migrations: none". It adds two nullable
  columns and no table; it is the cost of "once".
- **Assumption:** v36–v40 ship in one release (S072 § 9, extended), so no `_PRECONDITIONS` entry.
- **Assumption:** the clause wording of the next ISO 9001 edition and RFC 8030's urgency in FCM and
  Apple's service are *to verify*.
- **Proposed point for § SMTW-Review** (`.claude/CLAUDE.md`): "Improvement alerts (S074): the
  daily scan sends *overdue* once per due date and *ready to verify* once per watch end, through
  `overdue_alert_for` and `ready_alert_for`; a path that writes them takes (6b) then (6c), and an
  alert goes only to people who can open the improvement."
- **Length:** about 720 lines, past the size rule's 600, as S070 (696) and S072 (about 830) were.
  It is one concern (the alerts and their daily scan), with 19 code and test files, under the
  25-file rule; most of the length is § 5's rules, the change table and the lock check. No split.
- **No defining question.** Gate R answered Q5.1 (a); the choices above are inside it.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 3 (import direction, the task label), § 4.1, § 5.1,
§ 5.2 (step 2 and the candidate SQL), § 5.4 (path), § 5.6, § 7 D3 and D7, § 8.1, § 8.2, § 8.3,
§ 8.4, § 8.5, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): both rules use `!=`, literally once per due date and once per watch end; a due date or watch end moved earlier, still past, alerts again. § 4.1, § 5.1, § 5.2's SQL (`<>`); § 8.1's "moved earlier" case flipped to True, and a "watch cut" case added. |
| BR1-02 minor | Accepted (a): the columns stay; D3 cites S072 D1's suggestion of a line and gives the three reasons the columns win (a doubled `watch_ended` line, a value to compare, a join per countermeasure). |
| BR1-03 minor | Accepted (a): quiet stays silent with Urgency `low`, one rule for every quiet alert; D7 says so, and § 8.5 row 1 asks for the phone charging or on Wi-Fi. |
| BR1-04 minor | Accepted (a) and (b): the worker test fakes the sender (`fake_send(201)`), and a second worker test with `push_off` proves D8. § 8.2. |
| BR1-05…BR1-11 nits | Accepted: BR1-05 S070's countermeasure tests checked wherever they land, and `test_alerts.py` and `test_closed_email.py` run whole (§ 8.3); BR1-06 the import direction (§ 3); BR1-07 `SELECT NOW()` opens no snapshot (§ 5.2); BR1-08 the other-site machine gap accepted (§ 5.6); BR1-09 the device rows' *Network* and *Where*, and "wait until after 08:00 the next day" (§ 8.5); BR1-10 the label "Send the morning alerts: overdue countermeasures and improvements ready to verify" (§ 3, § 8.4); BR1-11 the tap opens the page's top, an anchor later (§ 5.4). § 9 Q1–Q3 answered as proposed. |
