```
Step: S106 — Tasks on a ticket
Doc: brief
Author: Brief writer (Fable)
Date: 22-11-2026
Track: full
Baseline: 8644720
Status: Gate B 22-11-2026 (code review r1: 1 minor, 3 nits, fixed in fix round 1; verify review r2: no finding; open for KLA: the person id in a same-name owner line, § 8.7 acceptance by API tests); was approved 22-11-2026 by KLA (Q1 a, Q2 a, the split: three steps, Q3–Q7 as recommended; review r1: 1 major, 2 minor, 6 nits; r2: 5 nits; all accepted)
```

# S106 — Tasks on a ticket

## 1. What will be built

**The request** (KLA, 22-11-2026). Ticket TK-2026-11-008 is a defect on a VCB: an HT cable
termination failed and was re-terminated, and moisture is the suspected cause. The follow-up work
has several parts, each for one person: a technician gets *Check the space heater circuit diagram
and find any fuse*, an engineer gets *Schedule a PM visit from the VCB supplier*. Today the ticket
holds assignees and work notes, but no list of who does what by when.

**How the two tasks are read** (KLA, 22-11-2026). Both are diagnosis of this fault. The supplier's
visit is **one inspection** of the panel, to find why moisture gets in: a task (*Get the VCB
supplier to inspect the panel*). A **standing** supplier PM for the VCBs is a different thing: new
regular work that stops the fault from coming back. That is a *Preventive* countermeasure on the
improvement, not a task (§ 2, *The rule of thumb*).

**A task** is one piece of work on a ticket, given to one person, with a due date. It is open,
then done (with what was done) or cancelled (with a reason). Tasks live on the ticket, not on the
improvement (decided 22-11-2026, § 7 D1): finding and fixing this fault is the ticket's work. A
task is one-off work that is needed before the engineer can state the cause and close the ticket.
Work that stops the fault from coming back for good stays a countermeasure on the improvement,
which tracks it after the ticket is closed.

The feature is larger than one step (§ 9, *The split*). **This step builds the record, the rules
and the API.** The screens and the alerts are the next two steps and build on § 6 as written here.
Nothing is visible to users after this step alone.

1. **Add a task** (`POST /api/tickets/<id>/tasks`): what to do, the owner (any active person of
   the ticket's site, with or without a login) and a due date. By a `ticket:assign` holder at the
   ticket's site (engineer, manager, IT admin), while the ticket is not closed.
2. **Change** an open task: the text, the owner, the due date (`PUT`).
3. **Cancel** an open task with a reason (`POST …/cancel`). The row stays; nothing is deleted.
4. **Mark done** (`POST …/done`): what was done and when (no time sent means now). The **owner**
   marks their own task; a `ticket:assign` holder at the site marks any, also for an owner without
   a login. Who may mark a task is decided **by data** (the owner), not by a new key.
5. **Overdue**: an open task whose due date is before today (IST) carries `overdue_days`,
   computed, never stored.
6. **A line on the ticket's timeline** for every change (added, changed, done, cancelled), written
   in the same transaction as the change.
7. **A ticket with an open task cannot be closed** (*Close* and *Not a fault*): the engineer marks
   each task done or cancels it first. *Back in service* is never blocked (§ 7 D4). What this
   does to a follow-up that runs for days or weeks: § 9 Q2.
8. **My open tasks** for *Me › Open work* (`GET /api/tickets/tasks/mine`).
9. **The ticket detail** gains `tasks`, `task_counts` and `can_add_task`; its *Close* and *Not a
   fault* moves carry `blocked_reason`.

**After this step and the screens step:** on TK-2026-11-008 the engineer adds the two tasks; the
technician sees his on *Me › Open work* and marks it done with what he found; the engineer marks
the inspection done with what the supplier found; the ticket's timeline shows each step, and the
ticket closes once no task is open. If the plant then wants a regular supplier PM, the engineer
adds it to the improvement as a *Preventive* countermeasure.

### What the next two steps add (for orientation, not built here)

- **Screens**: a *Tasks* card on the ticket page ("Tasks (1 of 3 done)", each row with the text,
  the owner, the due date, *Overdue 2 days* in red); `"Add task"`; the dialogs *Add / Change task*
  (*What to do*, *Owner*, *Due date* with *Today / Tomorrow / In 7 days*), *Mark done* (*What did
  you do?*, *Done on*, and a photo that goes to the ticket's photos, § 7 D7) and *Cancel task*
  (the reason); the timeline's four lines; *Me › Open work* lists my open tasks; *Close* shows
  why it is blocked; a mark on a task whose owner cannot open the ticket (`owner.can_open`,
  § 4.2).
- **Alerts**: *Task for you* (push, to the new owner) and *Task overdue* (push, once per due date,
  from a daily scan), on the pieces S074 built (§ 9 Q6).

### Out of scope

- Every screen and browser test, and both alerts (the next two steps).
- A kind on a task (§ 7 D6), a photo owned by a task (§ 7 D7), a task without a due date.
- Reopening a done task, and deleting one. A wrong *done* stays on the record; the engineer adds a
  new task (as a countermeasure, S070 D5).
- Copying a task's done note into a linked improvement (§ 9 Q3).
- A count of open tasks on the ticket list.
- Diagnostic procedures per symptom (Plan § 4.2, *Proposed*): a written test sequence with
  readings. A task is one line of work for one person and does not replace them.
- A new permission key: none (§ 7 D2).

## 2. Standards and practice

- **EN 13306** (maintenance terms; term numbers *to verify*). In plain words: *corrective
  maintenance* is the work done after a fault is found, to bring the item back to working order.
  It has steps: *fault diagnosis* (recognise the fault, localise it and identify its cause),
  *fault correction* and the *function check-out*. The standard says "cause" and no more. The
  line inside it is Yantra's own (§ 7 D1): a task finds the *immediate* cause (why the part
  failed), and the improvement's why-why finds the root cause (ISO 9001 § 10.2.1 b, below).
  *Deferred* corrective maintenance is corrective work that waits for a slot, a part or a vendor.
  A task is one such step of this ticket's corrective work, given to a person. So tasks belong on
  the ticket (the work order), not on the improvement.
- **ISO 9001:2015 § 10.2.1** (nonconformity and corrective action). In plain words: (a) react to
  the problem: control it and correct it; (b) decide whether action is needed so it does not come
  back, by analysing the problem and **finding its causes**; (c) carry out that action. The
  ticket and its tasks are (a), the *correction* of this occurrence: a task finds where this
  fault is and its immediate cause, or fixes it. Finding the **root cause** is (b), the
  improvement's why-why (S069), and removing it is (c), the countermeasures; both stay on the
  improvement. On the VCB, for example: "the termination failed because of moisture; the space
  heater's fuse was blown" is what tasks can find; "why does nobody check the heater" is a line
  of the why-why. Clause letters as Plan § 1 cites them.
- **The rule of thumb for the plant** (KLA's line of 22-11-2026; the glossary row of § 3 uses the
  same words). **A task** is one-off work that finds or fixes **this** fault: a check, a test,
  one inspection visit, a trial fix. It is the work needed before the engineer can state the
  cause and close the ticket. **A countermeasure** is work that stops the fault from coming back
  for good: new regular work (a standing supplier PM, a new PM item), a change to the machine, a
  lesson. It lives on the improvement, which tracks it after the ticket is closed. (A watch over
  weeks is neither: it is the improvement's *Watch period*, which starts after its
  countermeasures are done and counts whether the fault comes back.) One supplier visit to
  inspect the panel is a task; a regular supplier PM is a *Preventive* countermeasure
  (Maintenance-Philosophy § 12: "adds regular work that stops the failure before it happens").
- **ISO 9001 § 7.5.3** (control of records). In plain words: records are kept, protected from
  change, and show who did what and when. A task is never deleted; done and cancelled are final;
  every change writes a timeline line that keeps the old and the new value.
- **ISO 14224** (reliability and maintenance data; table numbers *to verify*). In plain words: one
  record per maintenance event, holding the activity, who worked and when. The tasks stay inside
  the ticket, the one record of the event; the times that feed MTTR and downtime still come only
  from the ticket's own events, never from a task.
- **TPM — the abnormality tag** (*fuguai*, autonomous maintenance). In plain words: every defect
  found gets a tag, and the tag stays on the machine until someone has fixed it; each tag names
  who acts and by when. A defect ticket is that tag (Plan § 4.2); its tasks are the "who, what,
  by when" of removing it, and the ticket closes only when they are finished.
- **ISO 27001 A.5.15** (access control). In plain words: give each person only what their work
  needs. The owner records their own work without the engineer's key; nobody gets a new right.
- **SMRP KPIs**: none changes. Response, repair time and downtime are computed from the ticket's
  ordered events (`tickets_core.ticket_times`), which skips every other event.

## 3. Where

No other step is open on these files (S105 is done), so `file:line` anchors are given; names are
the anchors that count.

### Backend

- `backend/local_db.py`: migration **v59** after v58 (`backend/local_db.py:1561`), § 4.1. No
  `_PRECONDITIONS` entry (§ 4.1).
- `backend/ticket_tasks_core.py` (**new**, pure): the bounds and messages, `validate_task`,
  `task_state_error`, `task_line`, `close_block`, the four event names (§ 5). It imports from
  `improvements_core` the rules a task shares with a countermeasure (§ 7 D8).
- `backend/improvements_core.py`: one public name beside `is_id` and `text_field`
  (`backend/improvements_core.py:170`): `required_field = _required`, so the new module imports no
  private name (as S075 D10 did). No behaviour changes. The date parser is the existing public
  `contracts_core.iso_date` (`backend/contracts_core.py:61`), which `pm_plans_core` already
  imports.
- `backend/tickets.py`: a section *Tasks (S106)* with the routes of § 6, on the pattern of its
  labour, parts and notes sections; `_add_event` gains `task_id`; `_event_rows` and `_events_out`
  carry it; `_detail` gains `tasks`, `task_counts`, `can_add_task`; `_moves` gains
  `blocked_reason`; `_apply_move` refuses a closing move while a task is open; the docstring's
  LOCK ORDER gains the task writes (§ 5.6). Each task's `owner.can_open` comes from
  `alerts.people_at_unit` (`alerts` is imported already, `backend/tickets.py:104`) with
  `access_core.roles_holding`, a new import of a pure module (§ 4.2). **Wording:** the notes and
  comments say "`ticket_tasks` rows", never "task rows": in this module "task rows" already means
  `task_queue` rows (the raise's comment at `backend/tickets.py:922`, the docstring's alerts
  sentence).
- `backend/equipment.py`: docstring only. The global LOCK ORDER's line (7)
  (`backend/equipment.py:43`) gains: `ticket_tasks` rows are written only under their ticket's
  lock (7).
- `backend/config_rbac.py`: a comment only, at `ticket:assign` and `ticket:close`
  (`backend/config_rbac.py:119`): the close block (S106) relies on a closer being able to cancel
  the blocking task, so a change to either key's holders reconsiders it (§ 7 D4). No key, role or
  holder changes.

### Tests

- `backend/tests/test_migration_v59.py` (**new**), on the pattern of `test_migration_v58.py`.
- `backend/tests/test_ticket_tasks_core.py` (**new**).
- `backend/tests/test_ticket_tasks_api.py` (**new**).
- `backend/tests/conftest.py`: `"ticket_tasks"` joins `_TABLES` after `"ticket_events"` (the
  fixture deletes with `FOREIGN_KEY_CHECKS = 0`, so the order is for reading only).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: a line for `ticket_tasks` (area *Tickets*); the line of
  `ticket_events` gains "the task the line is about (S106, v59)". Then
  `tooling\schema-docs.bat write` (it rewrites `docs/schema/schema.json` and
  `docs/schema/schema-data.js`); `check` exits 0.
- `docs/Plan.MD`: § 4.2, one bullet *Tasks on a ticket* (what § 1 says, and that closing now also
  needs no open task, beside "Closing needs cause, action, symptom and at least one labour row");
  § 3, one paragraph after the countermeasure's (`docs/Plan.MD:284`): a task is marked done by
  data, its owner or a `ticket:assign` holder at the site.
- `docs/Maintenance-Philosophy.md` § 12 Glossary: a row *Task (on a ticket)*, in the words of § 2:
  "One piece of one-off work on a ticket, for one person, with a due date, marked done with what
  was done (S106): a check, a test, one inspection visit, a trial fix. It is part of the ticket's
  corrective work (EN 13306 fault diagnosis and correction; ISO 9001 § 10.2.1 a): it finds where
  this fault is and its immediate cause, or fixes it, and is needed before the ticket can be
  closed. Finding the root cause (the
  why-why) and work that stops the fault from coming back for good (regular work, a change to the
  machine, a lesson) are not tasks: they are the improvement's, as *Countermeasures*. One
  supplier visit to inspect a panel is a task; a regular supplier PM is a *Preventive*
  countermeasure."
- `.claude/CLAUDE.md` § SMTW-Review: the point **Ticket tasks (S106)** (§ 9, *SMTW-Review point*).
- `docs/steps/device-checks.md`: nothing (no screen in this step). `help/`: nothing.

**File count:** 10 code and test files (6 code, two of them a docstring or a comment only:
`equipment.py` and `config_rbac.py`; 4 tests), 6 docs.

## 4. Data model

### 4.1 Migration v59

```sql
-- Tasks on a ticket (S106): one piece of the ticket's corrective work, given to one person with a
-- due date (EN 13306 fault diagnosis and correction).  Never deleted: a cancel keeps the row with
-- its reason (ISO 9001 § 7.5.3).
CREATE TABLE IF NOT EXISTS ticket_tasks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id       INT NOT NULL,
    text            VARCHAR(300) NOT NULL,
    owner_id        INT NOT NULL,
    due_date        DATE NOT NULL,
    state           ENUM('open','done','cancelled') NOT NULL DEFAULT 'open',
    done_text       VARCHAR(1000) NULL,
    done_at         DATETIME NULL,
    done_by         VARCHAR(100) NULL,
    cancel_reason   VARCHAR(500) NULL,
    cancelled_at    DATETIME NULL,
    cancelled_by    VARCHAR(100) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    updated_at      DATETIME NULL,
    updated_by      VARCHAR(100) NULL,
    KEY ix_ticket_tasks_ticket (ticket_id, id),
    KEY ix_ticket_tasks_owner_state (owner_id, state, due_date),
    CONSTRAINT fk_ticket_tasks_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id),
    CONSTRAINT fk_ticket_tasks_owner FOREIGN KEY (owner_id) REFERENCES people (id),
    CONSTRAINT chk_ticket_tasks_done
        CHECK ((state = 'done') = (done_text IS NOT NULL AND done_at IS NOT NULL AND done_by IS NOT NULL)),
    CONSTRAINT chk_ticket_tasks_cancelled
        CHECK ((state = 'cancelled') = (cancel_reason IS NOT NULL AND cancelled_at IS NOT NULL
                                        AND cancelled_by IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The timeline line of a task change names its task.
ALTER TABLE ticket_events
    ADD COLUMN IF NOT EXISTS task_id INT NULL AFTER machine_stopped,
    ADD KEY IF NOT EXISTS ix_ticket_events_task (task_id),
    ADD CONSTRAINT fk_ticket_events_task
        FOREIGN KEY IF NOT EXISTS (task_id) REFERENCES ticket_tasks (id);
```

- **The table** is `improvement_actions` (v38, now in v41) without `kind`, on a ticket; the two
  CHECKs have the same shape. `text` is 300 characters, not 500: a change's timeline line holds the
  old and the new text and must fit `ticket_events.remark`, `VARCHAR(1000)`
  (`backend/local_db.py:467`; § 5.5, § 7 D11).
- **`ix_ticket_tasks_owner_state`** serves *my open tasks* (`owner_id = ? AND state = 'open' ORDER
  BY due_date`).
- **`ticket_events.event`** is `VARCHAR(30)` (`backend/local_db.py:461`), so the four new event
  names need no column change.
- **The `ALTER`** has the form of v50's on `people` (`backend/local_db.py:1171`: `ADD COLUMN IF NOT
  EXISTS … AFTER`, `ADD KEY IF NOT EXISTS`, `ADD CONSTRAINT … FOREIGN KEY IF NOT EXISTS`), which
  production has applied.
- **v59 copies `ticket_events`.** Adding a foreign key with `foreign_key_checks` on is not an
  in-place change in MariaDB: the server rebuilds the table by a copy. Probe on the dev database
  (MariaDB 11.4.13, `scratch/s106_br1_alter_probe.sql`, 22-11-2026): the column and its key with
  `ALGORITHM=INPLACE` pass; a `VARCHAR(1000)` widened to `VARCHAR(2000)` with `ALGORITHM=INPLACE`
  passes (§ 7 D11); the foreign key with `ALGORITHM=INPLACE` is refused with 1846 "Adding
  foreign keys needs foreign_key_checks=OFF. Try ALGORITHM=COPY". The migration runner leaves
  `foreign_key_checks` on (no statement in `backend/local_db.py` sets it), and v59 does not turn
  it off: the check is wanted, and v50 added its foreign keys the same way. The copy reads every
  row of `ticket_events` once and blocks writes to it meanwhile. It runs once, when the new
  release starts (`ensure_schema`), in the maintenance window. Assumption: the table is small (a
  few lines per ticket), so the copy takes about a second; production's row count was not read.
  The migration's comment says that the table is copied.
- **Re-run safety:** every statement carries `IF NOT EXISTS`; a half-applied v59 (the table made,
  the `ALTER` not) runs again to the same shape (§ 8.1).
- **No precondition** (base § Preconditions: a new table and a nullable column touch no existing
  row). Production holds tickets and their events; every existing `ticket_events` row gets
  `task_id` NULL and nothing is converted, refused or dropped. The migration's comment says so.
  § 8.1 runs v59 on a v58 database with a ticket and its events.
- **Rollback:** a release before v59 never reads `ticket_tasks`. Its `ticket_events` reads name
  their columns (`_event_rows`, `backend/tickets.py:259`) and its inserts name theirs
  (`db_helpers.insert_row`), so the new column is invisible to it.
- **Text:** utf8mb4; MariaDB counts characters in `VARCHAR(n)`, so Tamil fits.
- Release v0.1.16 holds v58 (`git show d80399d:backend/local_db.py`). Whether production runs
  v0.1.16 today is *to verify* with KLA; v59 runs after v57 and v58 either way.

### 4.2 What is computed, never stored

- `overdue_days`, `task_counts`, each task's `can_change` and `can_mark_done`, the ticket's
  `can_add_task` and the moves' `blocked_reason`.
- `owner.has_login` (`people.username IS NOT NULL`), `owner.active`, `owner.may_own` (an active
  member of the ticket's site today), and the names of `created_by`, `done_by` and `cancelled_by`
  (the person whose login it is, else the login). All read with the tasks in **one** query (joins
  to `people` and an `EXISTS` on `memberships`), no query per task.
- `owner.can_open`: whether the owner will see the task and get its alerts. True when the owner
  has a login **and** is among `alerts.people_at_unit(cur, <the ticket's site>, [<the ticket's
  unit>], access_core.roles_holding(READ_KEY), only_ids=<the tasks' owner ids>)`: an active
  person whose role at the ticket's site holds `ticket:read` and who covers the ticket's unit
  (all units of the site, or a `person_units` row). **One** more query per detail, none when the
  ticket has no task (`_people_with_role` returns at once on an empty `only_ids`,
  `backend/alerts.py:206`). It is the recipient query of the ticket alerts (`alerts.recipients`
  calls `people_at_unit` with the ticket's site and unit), and the alerts step's *Task for you*
  makes the same call (§ 9 Q6), so the flag and the alert's audience do not differ. The login is
  checked apart because `people_at_unit` does not ask for one, and a role row of a person without
  a login grants nothing (`config_rbac.NO_LOGIN_ROLES`).
  **It is a hint for the engineer; no rule reads it.** It can be wrong in rare cases. False for
  an owner who can open: one who sees the ticket only through its machine's current unit (the
  machine moved after the raise), and one whose right comes from a token role (an IT admin with
  a Team record; another person's token roles are not in the database). True for an owner who
  cannot: one whose Keycloak login does not work (`has_login` reads `people.username` only; the
  account may lack `maintenance_team` or was never set up).

## 5. Rules

### 5.1 Order of the refusals

Every write, in this order: (1) the route's key held at some site, else 403 (`require_perm`); (2)
the body, else 400 (`clean_body`, before the transaction, as `add_assignee` and `add_note`); (3) the ticket
inside the ticket predicate, else 404; (4) the route's key at the ticket's site, else 403; (5) the
ticket not closed, else 409 "This ticket is closed" (`TICKET_CLOSED`); (6) the task a row of this
ticket, else 404 "Not found"; (7) for *Mark done*, the owner rule, else 403 (§ 5.7); (8) the
task's own state, else 409 (§ 5.5); (9) the checks that need the database (owner, due date, done
time), else 400. Steps 3–5 are `_lock_open_ticket` (`backend/tickets.py:536`), unchanged.

### 5.2 The fields

**Add and change** (`validate_task(body, creating)` for `clean_body`):

| Field | `POST` | `PUT` | Rule and message (field) |
|---|---|---|---|
| `text` | required | optional, not `null` | text, trimmed, 1–300: "Enter what to do" / "What to do: up to 300 characters" / "What to do must be text" (`text`) |
| `owner_id` | required | optional, not `null` | integer ≥ 1, not a boolean: "Choose the owner" (`owner_id`, `improvements_core.OWNER_NEEDED`); then the shell, § 5.3 |
| `due_date` | required | optional, not `null` | `YYYY-MM-DD` after trim, by `contracts_core.iso_date` (it refuses `20261122` and week dates, which `date.fromisoformat` takes): "Enter the date as YYYY-MM-DD" (`due_date`, `tickets_core.LABOUR_DATE_FORMAT`); then § 5.3 |

- A missing required field on a `POST`, or a `null` on either, gives the field's first message
  ("Enter what to do", "Choose the owner", "Enter the date as YYYY-MM-DD").
- An absent field on a `PUT` stays as it is. A field equal to the stored value is not written. A
  `PUT` that changes nothing (an empty body too) answers 200, writes nothing, stamps no
  `updated_*` and adds no timeline line. Unknown fields, `state` and the done and cancel fields
  are ignored.
- **At most 30 tasks** per ticket, cancelled ones counted (`TASKS_MAX`): a `POST` on a ticket with
  30 is 409 "A ticket holds up to 30 tasks. Change an open one instead." (no field).

**Mark done**: `improvements_core.validate_done`, unchanged: `done_text` required, trimmed, 1–1000
("Say what you did" / "What you did: up to 1000 characters" / "What you did must be text");
`done_at` optional, absent or `null` means the server's IST now, else `parse_event_time` ("Enter
the time as YYYY-MM-DD HH:MM"), then § 5.3.

**Cancel**: `improvements_core.validate_cancel`, unchanged: `reason` required, trimmed, 1–500 ("Say
why it is cancelled" / "Reason: up to 500 characters" / "Reason must be text").

### 5.3 Owner, due date, done time

- **The owner**: an active person with a membership at the ticket's site, any role, a person
  without a login too (a contractor's technician, an operator without a phone). Checked with
  `_check_person(cur, owner_id, site_id, "owner_id")` (`backend/tickets.py:812`): 400 "Choose a
  person from this site" (`PERSON_AT_SITE`). On a `PUT` only when `owner_id` changes, so an owner
  who has since left the site stays until someone picks another; `owner.active` and
  `owner.may_own` tell the screens to mark them.
- **An owner who cannot act on it**: an owner without a login, an owner whose role holds no
  `ticket:read` (the storekeeper), and an owner whose units do not cover the ticket never see the
  task. A `ticket:assign` holder marks the work done for them. The detail tells the engineer
  which owners these are: `owner.can_open` is false (§ 4.2), and `owner.has_login` says whether
  the reason is a missing login. The screens step shows it on the task's row; this step only
  sends the field. The owner picker (`list_people`) is unchanged.
- **The due date**: `improvements_core.due_date_error(due, ticket occurred date, today)`: from the
  day the problem happened ("Choose a date from 20-11-2026, the day the problem happened") to
  today + 365 days ("Choose a date within a year"). A date in the past, back to that day, is
  allowed: a step already done is recorded with its true dates. On a `PUT` only when it changes.
  The ticket's `occurred_at` comes from the locked row (`_LOCK_TICKET`,
  `backend/tickets.py:510`); today is `_today()` (IST).
- **The done time**: `improvements_core.done_time_error(done_at, now, ticket occurred_at)`: not
  more than 5 minutes ahead of now ("That time is in the future"), not before the minute the
  problem happened ("Not before the problem happened, 20-11-2026 15:15"). No 7-day limit: a task's
  done time is not an ordered event, and no figure is computed from it.

### 5.4 Overdue, counts, flags (pure, shared with countermeasures)

- `improvements_core.overdue_days(state, due_date, today)`: the days an open task is past its due
  date; 0 when due today or later, done or cancelled.
- `improvements_core.action_counts(tasks)` gives `task_counts`: `{open, done, cancelled, overdue}`.
- `improvements_core.action_flags(ticket_open, state, may_assign, is_owner)` gives `can_change`
  (ticket not closed, task open, `ticket:assign` at the site) and `can_mark_done` (ticket not
  closed, task open, and `ticket:assign` at the site or the owner rule). The shell passes
  `is_owner` as "the user's Team record is the owner **and** the user holds `ticket:read` at the
  ticket's site": a reader who sees the ticket only through its machine's current unit at another
  site cannot mark done (§ 5.7), so the flag never offers a button that ends in a 403. The third
  flag, `can_add_photo`, is not sent.
- `can_add_task`: the ticket not closed and `ticket:assign` at its site.
- `close_block(open_count)` → None when 0; else "This ticket has 1 open task. Mark it done or
  cancel it first." / "This ticket has 3 open tasks. Mark them done or cancel them first."

### 5.5 States, the close and the timeline

Task states: `open`, `done`, `cancelled` (the same values as a countermeasure's; `TASK_OPEN` and
the others are `improvements_core`'s constants under their own names). Done and cancelled are
final.

| Action | Who (§ 5.7) | from `open` | from `done` | from `cancelled` |
|---|---|---|---|---|
| Change (`PUT`) | `ticket:assign` at the site | 200 | 409 "Only an open task can be changed" | the same 409 |
| Mark done | the owner, or `ticket:assign` at the site | 200, `done` | 409 "This task is already done" | 409 "This task was cancelled" |
| Cancel | `ticket:assign` at the site | 200, `cancelled` | 409 "A done task cannot be cancelled" | 409 "This task is already cancelled" |

- **The ticket's state** comes first (§ 5.1 step 5). Add, change, done and cancel work in every
  state but *closed*: raised, acknowledged, scheduled, in progress, back in service (§ 7 D5).
- **Mark done writes** `state = 'done'`, `done_text`, `done_at` (sent, or now), `done_by =
  actor()`. **Cancel writes** `state = 'cancelled'`, `cancel_reason`, `cancelled_at = now`,
  `cancelled_by = actor()`. Neither stamps `updated_*`: those record the last change of the text,
  the owner and the due date. When `done_by` is not the owner (the engineer for a fitter without
  a phone), the detail shows both (`done_by_name`, `owner.name`).
- **The close is blocked.** `_apply_move` (`backend/tickets.py:1132`), for a move whose
  `to_state` is `closed` (*Close*, *Not a fault*), counts the ticket's open tasks right after the
  from-state check and before the event time and the move's own step; above 0 it raises 409 with
  `close_block`'s text (no field). So **a closed ticket never has an open task**. The count is a
  plain read under the ticket's lock (7), which every task write holds (§ 5.6). No other move
  reads tasks.
- **`blocked_reason`**: `_moves` adds it to the entries of the moves that close (`close`,
  `not-a-fault`): `close_block`'s text, or `null`. The screens show the button disabled with it.

**The timeline.** Every task write adds one `ticket_events` row after its change, in the same
transaction, through `_add_event(…, task_id=…)`. The four events are not in
`tickets_core.ORDERED_EVENTS`, so they set no bound for a later move's time and `ticket_times`
skips them (it skips every event outside that tuple, `backend/tickets_core.py:762`).

| Write | `event` | `occurred_at` | `remark` |
|---|---|---|---|
| Add | `task_added` | now | `task_line(text, owner name, due)`: the text, a line break, "Owner: \<name\>. Due DD-MM-YYYY." |
| Change, when a field changed | `task_changed` | now | `tickets_core.edit_lines` over *What to do*, *Owner* (names), *Due* (DD-MM-YYYY): one "Label: old → new" line per changed field |
| Mark done | `task_done` | `done_at` | `done_text` |
| Cancel | `task_cancelled` | now | the reason |

- The longest line is a change of all three fields: 12 + 300 + 3 + 300 for the text, 7 + 100 + 3 +
  100 for the owner (`people.name` is `VARCHAR(100)`), 28 for the due date and two line breaks:
  855 characters, inside the remark's 1000.
- `person_id`, the states, the intensity and the plan columns stay NULL. `created_by` is the
  actor, so the line shows on that user's *Me › Activity* (`list_activity` reads by `created_by`),
  under the raw event name until the screens step labels it (`EVENT_LABELS[e.event] ?? e.event`,
  `frontend/src/views/TicketDetailView.vue:456`). No such line exists before the screens step,
  because only the API can add a task until then.
- Each event row in the detail carries `task_id` (NULL on every other event).

### 5.6 Locks

The database runs REPEATABLE READ. Pool connections are autocommit and `transaction()` begins
with `conn.begin()` (`backend/db_helpers.py:44`), so in each route below the locking read of the
ticket is the transaction's first statement, and its first plain read (`read_ticket`, inside
`_lock_ticket`) starts the snapshot **after** the lock is granted. Every plain read that follows
sees what earlier holders of the lock committed.

**No new lock level.** A `ticket_tasks` row is written only by a transaction that holds its
ticket's row `FOR UPDATE` (7), as a labour row and a parts line are. `ticket_tasks` rows are never
locked on their own (the `UPDATE` takes its row lock under (7)); the worker and `documents.py`
take (7) alone, as today.

**One word for one thing.** In `tickets.py`, "task rows" already means `task_queue` rows (§ 3).
The LOCK ORDER notes and the code comments of this step write "`ticket_tasks` rows" for a
ticket's tasks, here and in `equipment.py`.

**Add** (`POST /api/tickets/<id>/tasks`), one `transaction`:
1. (7) the ticket `FOR UPDATE` (`_lock_open_ticket(cur, ticket_id, ASSIGN_KEY)`): 404, the
   predicate 404, `ticket:assign` at the site 403, closed 409 from the locked row.
2. Plain reads: the count of the ticket's tasks (409 at 30), the owner (400), the due date against
   the locked row's `occurred_at` (400).
3. The `ticket_tasks` insert (shared foreign-key locks on the ticket, held, and on the owner's
   `people` row).
4. The `ticket_events` insert (shared foreign-key locks on the ticket, held, and on the task this
   transaction inserted).
5. The detail, read inside the transaction (`_ticket_response`).

**Change** (`PUT …/tasks/<task_id>`): 1 as above; 2. a plain read of the task (`SELECT id, state,
text, owner_id, due_date FROM ticket_tasks WHERE id = %s AND ticket_id = %s`; 404), its state 409,
the owner and the due date when they change (400); 3. `update_row` with the changed fields (a new
owner takes a shared lock on that person); 4. the event, when a field changed; 5. the detail.

**Mark done** (`POST …/tasks/<task_id>/done`): 1. (7) with `READ_KEY` (`ticket:read` at the site
403); 2. the task (404), the owner rule 403 (§ 5.7), its state 409, the done time 400; 3. the
`UPDATE`; 4. the event; 5. the detail.

**Cancel** (`POST …/tasks/<task_id>/cancel`): 1. (7) with `ASSIGN_KEY`; 2. the task (404), its
state 409; 3. the `UPDATE`; 4. the event; 5. the detail.

**Close and Not a fault** (`make_move`): (7) as today, then the plain count of open tasks.

**Reads** (the detail, `mine`): plain, no lock. The detail's `owner.can_open` query (§ 4.2) reads
`people`, `memberships` and `person_units` plain, also when a write answers with the detail
inside its transaction (step 5): it takes no lock and adds no edge.

**A rollback**: each write is one transaction with no counter. A refusal after the task insert
(none is planned after step 3) or a database error rolls back the task, its line and nothing else.

**No new deadlock cycle, checked against the notes** (`tickets.py`, `masters.py`,
`improvements.py`, `equipment.py` LOCK ORDER):
- (7) → the owner's `people` row, shared: the edge a labour insert and an assignee insert already
  take under (7) (`add_labour`, `_assign`). A person's edit in `masters.py` (the person `FOR
  UPDATE`, then memberships, person_units, units) never waits on a ticket or a `ticket_tasks`
  row.
- (7) → `ticket_tasks` rows: nothing takes a `ticket_tasks` row and then a ticket.
  `improvements.py` takes ticket rows only `LOCK IN SHARE MODE` and never a `ticket_tasks` row; a
  task write that holds (7) waits only on a `people` row, which `improvements.py` holds only
  shared.
- A task write changes no `tickets` column, so it rewrites no ticket index and takes none of the
  unit, machine or component foreign-key locks a state change takes.
- The four accepted deadlocks of `tickets.py`'s note are unchanged; this step adds none.

The coder writes this into `tickets.py`'s LOCK ORDER note and the one sentence into
`equipment.py`'s line (7).

### 5.7 Permissions (owner by data)

No new key (§ 7 D2). The ticket keys, site-scoped (`config_rbac.SITE_SCOPED`), checked at the
ticket's site (the site of `tickets.unit_id`):

| Action | Route decorator | Then, under the ticket's lock |
|---|---|---|
| Read the tasks (the ticket detail) | `ticket:read` | the predicate 404 (unchanged) |
| Add, change, cancel | `ticket:assign` | predicate 404, `ticket:assign` at the site 403 |
| Mark done | `ticket:read` | predicate 404, `ticket:read` at the site 403; then **`has_perm_at(ASSIGN_KEY, site)` or `current_person_id(cur) == owner_id`**, else 403 "Only the owner, or an engineer or manager of this site, can mark this task done" |
| My open tasks | `ticket:read` | the predicate, as a filter |
| The owner choices | — | the existing `GET /api/tickets/people?ticket_id=` (`list_people`: `ticket:raise`, then `ticket:read` at the ticket's site); no new route |

- **Who holds `ticket:assign`** (`backend/config_rbac.py:119`): the engineer, so the manager, and
  IT admin. IT admin adds, changes, cancels and marks tasks done, as it assigns tickets today
  (S017 user decision 7, Plan § 3). An IT admin without a Team record owns no task. A person can
  hold IT admin and a site role at once (the comment at `config_rbac.INTERNAL_ONLY_ROLES`); such
  a person has a Team record and can own tasks like any member of the site.
- **The close block and the two keys.** The block (§ 5.5) assumes that whoever may close a ticket
  may also cancel the task that blocks it. `ticket:close` and `ticket:assign` have the same
  holders today (`backend/config_rbac.py:119` and the line after it). They are two keys and can
  drift, as the comment at `ticket:edit_notes` says of that key. If they do, a closer without
  `ticket:assign` meets a block that only someone else can lift. The step adds a comment at the
  two keys (§ 3), so that a later change to either reconsiders the block (§ 7 D4).
- **Owner by data** (as a countermeasure, Plan § 3): the user is the owner when their own Team
  record (`current_person_id`, `backend/auth_utils.py:314`) is the task's `owner_id`. A user with
  no Team record owns nothing.
- **Identity paths.** No field here changes who can log in or what anyone sees. Actor = owner: an
  engineer may give himself a task and mark it done (tickets already allow self-close, Plan § 3).
  An inactive owner stays the owner on the record and cannot log in; an owner whose membership at
  the site was removed fails `ticket:read` at the site (403) and no longer marks it done. The
  owner's name and `has_login` (a yes or no, never the login) go to every reader of the ticket, as
  on a countermeasure; no role, login or email. `can_open` goes to every reader too, in one shape
  for all: it is a yes or no, and the people picker already gives every `ticket:raise` holder
  each person's role at the site (`people_at_site`), which says more. A request with no identity
  gets `require_perm`'s 401, never admin.

### 5.8 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing, and the same
503 when the connection is lost mid-request (S105). No background task, no alert, no file.

## 6. API

All under `tickets_bp` (`/api/tickets`), ids `<int:…>`. `tasks` is not an integer, so
`/tasks/mine` cannot meet `/<int:ticket_id>` (as `/activity` and `/people`). Every write answers
with the whole ticket detail (as every ticket write).

| Route | Key | Body | Answer |
|---|---|---|---|
| `POST /api/tickets/<id>/tasks` | `ticket:assign` | `{text, owner_id, due_date}` | 201, the detail; 400, 403, 404, 409 per § 5 |
| `PUT /api/tickets/<id>/tasks/<task_id>` | `ticket:assign` | `{text?, owner_id?, due_date?}` | 200, the detail |
| `POST /api/tickets/<id>/tasks/<task_id>/done` | `ticket:read` + owner by data | `{done_text, done_at?}` | 200, the detail |
| `POST /api/tickets/<id>/tasks/<task_id>/cancel` | `ticket:assign` | `{reason}` | 200, the detail |
| `GET /api/tickets/tasks/mine` | `ticket:read` | — | `{items, total}` (below) |
| `GET /api/tickets/<id>` (S017) | `ticket:read` | — | gains `tasks`, `task_counts`, `can_add_task`; `events[].task_id`; `moves[].blocked_reason` on `close` and `not-a-fault` |

**`tasks`** (by `id`, the order they were added): `[{id, text, owner{id, name, active, has_login,
may_own, can_open}, due_date, state, overdue_days, done_text, done_at, done_by_name,
cancel_reason, cancelled_at, cancelled_by_name, created_at, created_by_name, updated_at,
can_change, can_mark_done}]`. Every reader of the ticket gets every task in full. `can_open`
(§ 4.2) is a yes or no about the owner, as `has_login` is; it names no role and no unit.

**`task_counts`**: `{open, done, cancelled, overdue}`. **`can_add_task`**: § 5.4.

**`mine`**: the user's open tasks (`owner_id = current_person_id`, `state = 'open'`) on tickets
that are not closed and inside the ticket predicate (`_visible_condition`), by `due_date, id`;
`LIMIT 200` (`MAX_PER_PAGE`) with `total`. Item: `{id, text, due_date, overdue_days,
can_mark_done, ticket{id, serial, state, intensity, machine{id, code, name}}}`. A user with no
Team record, or who may see no ticket, gets `{items: [], total: 0}`. `can_mark_done` is the
detail's flag for that task (§ 5.4), computed per row with `has_perm_at`. The "not closed" condition
can never exclude a row while the close block holds; it keeps the list right if that rule is ever
relaxed.

## 7. Design decisions

- **D1. Tasks on the ticket, not as countermeasures** (KLA and the orchestrator, 22-11-2026).
  EN 13306 counts fault diagnosis and correction as the ticket's corrective work. A countermeasure
  marked done can move its improvement to *Watching* and start the 90-day watch before the cause
  is known (`improvements_core.working_state`, `WATCH_KINDS`). Rejected: countermeasures of
  IM-2026-11-001 for this work.
- **D2. No new key; `ticket:assign` plans, the owner records** (§ 9 Q1). Handing out work on a
  ticket is what `ticket:assign` already means, and Plan § 3 decides "who marks it done" by data
  for PM jobs and countermeasures. Rejected: a `ticket_task:*` key set (three more rows in the
  matrix for the same holders); `ticket:work` for adding (every technician could hand work to
  anyone at the site).
- **D3. The owner is any active member of the site**, as a countermeasure's (S070 D3), not only
  the roles a ticket may be assigned to (`ASSIGNABLE_ROLES`). A task such as "check at the start
  of the next shift that the panel's space heater is warm" may truthfully belong to an operator.
  (A watch over weeks is not a task: it is the improvement's watch period, § 2.) Rejected:
  assignable roles only.
- **D4. An open task blocks the close, not *Back in service*** (§ 9 Q2). *Back in service* is the
  time production got its machine back; it ends downtime and must never wait for paperwork (EN
  13306 time to restoration). The close states the cause, and an open diagnosis task means the
  cause is not yet known; the block is of the kind "Add the labour before closing".
  **What it costs:** a ticket stays in *Back in service* for as long as a task on it is open.
  TPM practice is to close within the shift (Plan § 9 Q12, *Closing discipline*, *Proposed*). A
  diagnosis is a fair reason to wait: the cause is not known yet. Long follow-up work that stops
  a recurrence is not: as a task it either holds the ticket open for weeks, or is cancelled to
  close and so loses its owner and due date. Such work is not a task by the rule of thumb (§ 2);
  the engineer puts it on the improvement as a countermeasure, which tracks it after the ticket
  is closed, and cancels the task with that reason (§ 9 Q2, with the border case).
  **What it relies on:** whoever may close can also cancel the blocking task. `ticket:close` and
  `ticket:assign` have the same holders today and can drift; a change to either key's holders
  must reconsider the block (§ 5.7; the comment in `config_rbac.py`, § 3).
  Rejected: a warning only (tasks would be left open on closed tickets, with nobody to finish
  them); blocking *Back in service* (it would falsify downtime).
- **D5. Tasks work in every state but closed** (§ 9 Q4). The VCB ticket is back in service and
  still under investigation; a raised ticket may get its tasks before anyone acknowledges it.
  Closed is final and read-only, as for every ticket write. Rejected: only from *in progress* on.
- **D6. No kind on a task** (§ 9 Q5). A countermeasure's kind is read by a rule (the watch). No
  rule or report would read a task's kind, and no standard asks for one at this level. Rejected:
  *Investigation / Trial fix / Vendor / Other* (a fourth field on a phone dialog, for nothing).
- **D7. A task has no photo of its own; the photo goes on the ticket** (§ 9 Q7). The ticket is the
  documents store's owner already (`DATA_DIR/tickets/<id>/`), every owner with a login holds its
  write key (`ticket:raise`), and the ticket is open whenever a task is. Rejected for now: the
  task as a seventh owner (a column and a wider CHECK on `equipment_documents`, eight more route
  stacks, a branch of the removed list and its screen: about six more files) to show the photo
  inside the task's row.
- **D8. One copy of the rules a task shares with a countermeasure.** `validate_done`,
  `validate_cancel`, `due_date_error`, `done_time_error`, `overdue_days`, `action_counts` and
  `action_flags` are imported from `improvements_core`, whose messages fit a task word for word;
  the date parser is `contracts_core.iso_date`, the stricter public one (S080 CR1-02).
  `tickets.py` already imports `improvements_core`, and `improvements_core` imports
  `tickets_core`, so the direction is `ticket_tasks_core` → `improvements_core` →
  `tickets_core`, with no cycle. Rejected: copying them (two copies drift); moving them to a
  shared module now (a refactor of S070's code outside this request; a candidate for the queued
  tidy-up).
- **D9. The rules in a module of their own, the shell in `tickets.py`.** `ticket_tasks_core.py`
  keeps `tickets_core.py` (958 lines) from growing and can import `improvements_core`, which
  `tickets_core` cannot (the cycle above). The routes stay in `tickets.py`, beside labour, parts
  and notes: they need its private lock, event and detail functions, and `_detail` and
  `_apply_move` need the tasks. Rejected: a shell module `ticket_tasks.py` (it and `tickets.py`
  would have to import each other).
- **D10. The timeline line names its task by a column** (`ticket_events.task_id`), as
  `improvement_events.action_id`. The screens can show "Task done" with the task's text without
  parsing a remark. Rejected: the task's text copied into every remark (a 1000-character done note
  would not fit beside it).
- **D11. The text is 300 characters, not a countermeasure's 500.** A task is one line of work
  for one person; 300 characters hold it, and a change's "old → new" line then fits the
  timeline's 1000 characters, so the history stays complete (ISO 9001 § 7.5.3). Rejected: 500
  with a line that drops the old text; 500 with a wider `ticket_events.remark`. The wider column
  would cost little: `VARCHAR(1000)` to `VARCHAR(2000)` is an in-place change (probe of § 4.1:
  `ALGORITHM=INPLACE` passes), and v59 copies the table anyway. It is left out because a task
  does not need the longer text, and because the remark's width is the open point of ticket
  descriptions (§ 9, *Found while checking*), which a step of its own should settle for every
  line of the timeline at once.
- **D12. The word *Task*.** KLA's word. A PM item of kind *Task* uses the same word in the same
  sense: one piece of work that is done or not done. *Background tasks* (Settings, IT admin only)
  is a different thing on a screen the floor never sees. Rejected: *Action* (the app's word for
  the ISO 14224 maintenance action code picked at close); *Job* (a PM job).
- **D13. *Mine* is its own route** (as S070 D9): it answers tasks across tickets with each
  ticket's serial and machine, in one query. Rejected: a filter of the ticket list (it answers
  tickets).
- **D14. Flags from the server** (`can_change`, `can_mark_done`, `can_add_task`,
  `blocked_reason`), as S070 D10: the owner rule and the close rule need data the page does not
  hold.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v59.py`)

In the upgrade database, with the helpers of `tests/migration_helpers.py`:
- A fresh build: `ticket_tasks` with its two keys, two foreign keys and two CHECKs;
  `ticket_events.task_id`, `ix_ticket_events_task`, `fk_ticket_events_task`.
- **A v58 database with a ticket and its events** (`_fill_one_ticket`, as `test_migration_v58.py`
  builds its v57 one; v58's text is in `local_db._MIGRATIONS`, never edited, so no frozen fixture):
  v59 keeps every row, `task_id` is NULL on each, `db_version` gains 59.
- The CHECKs (4025): `done` without `done_text`; `open` with all three done fields; `cancelled`
  without a reason; `open` with all three cancel fields. An event with an unknown `task_id` is
  refused (1452).
- A re-run changes nothing (`_schema()` equal); a half-applied v59 (the table made, the `ALTER`
  not run) runs again to the fresh shape.

### 8.2 Core (`backend/tests/test_ticket_tasks_core.py`)

`validate_task`: each message of § 5.2 (missing, `null`, empty after trim, 300 / 301 characters, a
number as text, a boolean and 0 as `owner_id`, `due_date` "22-11-2026" and "2026-02-30"); a `PUT`
with no field gives an empty clean and no error; unknown fields ignored. `task_state_error`: the
nine cells of § 5.5. `close_block`: 0, 1, 3. `task_line`. The longest change line through
`edit_lines` is at most 1000 characters. The task states equal `improvements_core.ACTION_STATES`,
and `required_field` is the function behind `_required`. A `due_date` of "20261122" is refused.

### 8.3 API (`backend/tests/test_ticket_tasks_api.py`)

Each test makes its own machine and ticket (`make_ticket`, the fixtures of
`test_ticket_work_api.py`), so the kept worker database gives the starting state; a task is always
found by its id or text, never by position in a shared list.
- **Add:** 201 with the task open and `created_by_name`; an owner without a login (`has_login`
  false); an operator as owner; an inactive person and a person of another site (400 on
  `owner_id`); the due date the day before the ticket happened (400 with the date) and today + 366
  (400); the 31st task (409); a technician (403); an engineer of another site (404); an operator
  here who is engineer elsewhere (403 at the site); IT admin (201); on each of the five open
  states (201); on a closed ticket (409 "This ticket is closed").
- **Change:** each field alone; nothing changed writes nothing (`updated_at` stays NULL, no new
  event); an owner who left the site kept when unchanged, refused when sent anew; a done and a
  cancelled task (409); a task of another ticket (404).
- **Mark done:** the owner, a technician (200, `done_by` their login, `updated_at` unchanged); a
  technician who is not the owner (403 with the message); the engineer for an owner without a
  login (200, `done_by_name` the engineer, `owner.name` the fitter); `done_at` an hour ago
  (stored, and the line's `occurred_at`); in the future (400); before the ticket's time (400 with
  the time); already done, cancelled (409); no `done_text` (400); an owner whose membership at the
  site was removed (403); IT admin (200).
- **Mark done, the owner rule's edges** (§ 5.3, § 5.4; real memberships through `user_at_sites`,
  `backend/tests/conftest.py`, because the `X-Test-Role` wildcard holds at every site):
  - **An owner of the site whose units do not cover the ticket**: a technician at the ticket's
    site with one other unit of that site (`make_unit(site=…)`). *Mark done* is 404 and writes
    nothing; the task is not in that owner's *Mine*; in the engineer's detail the owner has
    `can_open` false and `may_own` true.
  - **An owner who sees the ticket only through its machine's current unit at another site**: a
    storekeeper at the ticket's site and a technician at a second site with one unit there. The
    task is added first; then IT admin (the `admin` fixture) moves the machine to that unit
    (`PUT /api/equipment/<id>` with `unit_id`; the existing test named below makes the same move,
    with an open ticket, to a unit of another site, and gets 200). The owner opens the ticket
    (200); *Mine* lists the task with `can_mark_done` false; *Mark done* is 403 (`ticket:read` at
    the ticket's site, § 5.1 step 4) and writes nothing. The existing test:
    `test_tickets_api.py::TestDetailAndAccess::test_a_moved_machine_shows_to_the_old_and_the_new_unit`.
- **Cancel:** with a reason (200); no reason (400); done (409); already cancelled (409); the owner
  technician (403).
- **The close:** *Close* and *Not a fault* with an open task are 409 with `close_block`'s text and
  change nothing; after the task is done, and after another is cancelled, the same close is 200;
  *Back in service* with an open task is 200; the detail's `close` move carries `blocked_reason`,
  `null` once no task is open; `restore` carries no such key.
- **Timeline:** each write adds exactly one event with its `task_id`, name and remark of § 5.5; a
  change of all three fields gives three lines; the ticket's `times` are equal before and after a
  task is added and done.
- **Detail:** `tasks` by id; `overdue_days` 2 after the test moves the task's `due_date` two days
  back with `db_rows`; `task_counts`; the flags for the engineer, the owner and an operator who
  owns nothing; `can_add_task` false for a technician and on a closed ticket; `owner.may_own`
  false after the owner's membership is removed. `owner.can_open`: true for a technician with a
  login whose units cover the ticket's unit; false for a technician without a login
  (`make_person`, then `give_site_role` with `maint_technician`); false for a storekeeper of the
  site with a login (`user_at_sites`); a ticket with no task answers `tasks: []`.
- **Mine:** the owner's open tasks by due date; not the done or cancelled ones; not another
  person's; an IT admin without a Team record gets an empty list; an operator moved off the unit
  no longer sees theirs.
- **The database down** (`db_down`, `backend/tests/conftest.py:244`): `POST …/tasks` answers 503.

### 8.4 Existing tests that break or run again

- `backend/tests/test_rbac.py::TestComputePermissions::test_role_matrix`: unchanged (no new key).
- `backend/tests/conftest.py` `_TABLES`: gains `"ticket_tasks"` (§ 3).
- `backend/tests/test_ticket_work_api.py`, `test_tickets_api.py`, `test_ticket_parts_api.py`,
  `test_my_tickets_api.py`: green as they are. None pins the detail's or a move entry's whole key
  set (`test_ticket_parts_api.py:244` checks only that `parts_hint_actions` is absent from the
  other moves); their closes run on tickets with no task.
- `backend/tests/test_ticket_work_api.py:479` and `test_ticket_parts_api.py:155` replace
  `tickets._lock_open_ticket` with a wrapper (`monkeypatch.setattr`); the function keeps its name
  and signature, so both stay green. `_add_event` gains only a keyword with a default.
- `backend/tests/test_improvements_core.py`, `test_improvement_actions_api.py`: green; the new
  public name changes no behaviour.
- The browser specs that read `GET /api/tickets/<id>` (`frontend/e2e/support/tickets.js` and the
  ticket specs) read named fields; the new fields change none of them.
- `backend/tests/test_migration_v58.py` and earlier: unchanged (each slices its own range).
  `test_modules.py` reads `LATEST_VERSION`, not a number.
- The schema docs check (`tooling\schema-docs.bat check`) is red until the coder runs `write`.

### 8.5 Automated (browser)

None in this step: no screen changes and no spec reads the detail's new fields. The coder runs
the whole browser suite at Normal once at the end, as the step workflow asks.

### 8.6 On a real device

None. The screens step holds them.

### 8.7 Acceptance

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the browser suite at Normal
  green once at the end.
- By API on a dev ticket: the two tasks of the VCB case are added; the technician marks his done;
  the ticket refuses the close while the other is open and closes once it is done or cancelled;
  the timeline shows the four lines.

## 9. Open questions and assumptions

**The split** (the size rule). The whole feature is about 30 code and test files and three
concerns that ship apart: the record and its API, the screens, the alerts. It is cut as S070, S071
and S074 were: **this step** the backend (10 code and test files); then **the screens**; then **the
alerts**. Alternative: fold the alerts into this step (about 8 more files and 130 more brief
lines: two kinds in `alerts_core.CHANNELS`, a handler, a daily scan and a marker column).
Recommended: three steps, the screens right after this one, because the screens are what the
VCB ticket waits for.

**Length:** about 940 lines after the two review rounds (730 before them), past the size rule's
600, as S070 (696) was. It is one concern (the backend) after the cut above; § 5.6's lock
sequences, § 9's questions and the rounds' answers (Q2's consequence, `owner.can_open`, the edge
tests) are most of
the excess. The code is unchanged in size but for one query and one comment.

**Questions for gate A.** The brief is written on the recommended answer of each; a different
answer changes the sections named.

- **Q1. Who adds, changes and cancels tasks, and who marks one done?**
  (a) **Recommended:** `ticket:assign` adds, changes and cancels (engineer, manager, IT admin);
  the owner marks their own done, and a `ticket:assign` holder marks any. No new key (D2).
  (b) Technicians add tasks too (`ticket:work`): a technician can split his own job, and can hand
  work to anyone at the site. Changes § 5.7 and the add route's key.
  (c) New keys `ticket_task:edit` and `ticket_task:work`: the holders could differ from the
  ticket keys later; three more rows in the matrix today for the same people.
- **Q2. Do open tasks block closing the ticket?**
  (a) **Recommended:** they block *Close* and *Not a fault*, never *Back in service* (D4). The
  engineer cancels a task with a reason to close early.
  **The consequence of (a):** a ticket stays in *Back in service* until its last task is done or
  cancelled. It is an open ticket for that time (`tickets_core.OPEN_STATES`), so it also blocks
  scrapping its machine and deactivating its unit ("Close its tickets first (1 open)",
  `tickets_core.close_tickets_first`): before either, the engineer finishes or cancels the task
  and closes the ticket. For a diagnosis of a day or two the wait is the point: the cause is not
  known yet. For
  a follow-up that runs for weeks (a watch on a trial fix, the first round of a new supplier
  PM), the ticket has two outcomes, and neither is good:
  - it stays in *Back in service* for those weeks, against the closing discipline of Plan § 9
    Q12 (TPM closes within the shift; its *Proposed* dashboard flag, once built, would list such
    a ticket to the engineer);
  - or the engineer cancels the task to close the ticket, and the follow-up loses its owner and
    its due date (a cancelled task is final, § 5.5).

  **The remedy**, which keeps (a) recommended: long follow-up work is not a task (§ 2, *The rule
  of thumb*). The engineer puts it on the improvement as a countermeasure, which has an owner and
  a due date and lives on after the ticket is closed, then cancels the task with the reason
  "Moved to improvement IM-…" and closes the ticket. A trial fix that needs weeks of watching
  goes the same way: the fix is the countermeasure, and the improvement's watch period does the
  watching (90 days by default, `improvements_core.WATCH_DAYS_DEFAULT`). An improvement can be
  started while the
  ticket is still in *Back in service* (`improvements_core.START_FROM_STATES`), so the analysis
  does not wait for the close. The plant has to learn this line; the glossary row carries it
  (§ 3).
  **The border case is the request's own:** the supplier's one inspection is diagnosis, so by
  the rule it is a task. If the visit is weeks away, TK-2026-11-008 waits for it in *Back in
  service* under (a). The recommendation accepts that wait: the ticket's cause is not known
  until the supplier has looked. Under (b) nothing would stop a close now, with a cause that is
  still a guess.
  (b) A warning only: the ticket closes with tasks open, so no ticket waits for a task and
  nothing is cancelled to close. Then open tasks live on closed tickets, and the brief needs
  rules for them (mark done on a closed ticket, *Me › Open work* on closed tickets, the overdue
  alert), and a closed ticket's cause can be coded before its diagnosis is finished. Changes
  § 5.5, § 5.6 and § 6.
  (c) They also block *Back in service*: rejected in D4, it would stretch downtime.
- **Q3. May a done task's note be copied into a linked improvement's why-why?** Recommended:
  **not in this feature.** The improvement page already links its tickets, and the task lines are
  on the ticket's timeline one tap away; the why-why's evidence is written by the engineer who
  leads the analysis. A later small step can show a ticket's tasks on the improvement page if the
  team misses them there.
- **Q4. In which ticket states can tasks be added?** Recommended: **every state but closed** (D5).
- **Q5. Does a task need a kind?** Recommended: **no, the text only** (D6).
- **Q6. Alerts** (the alerts step; decided here so the three steps fit together). Recommended:
  (a) *Task for you*: push to the new owner on an add and on a change of owner, not when the owner
  gave it to themselves; (b) *Task overdue*: push once per due date, from a daily scan at 08:00
  IST, to the owner and to the `ticket:assign` holders covering the ticket's unit (as *PM job
  overdue* goes to the assignee and the verifiers). Both quiet, kept 24 hours, only to people who
  may open the ticket, through `alerts_core.CHANNELS` and `task_handlers._push_to_people`. That
  step adds a marker column on `ticket_tasks` in its own migration, as S074's v40 did. Alternative:
  *Task for you* only, and *Overdue* shown on the screens alone.
  **Names, so that "task" never means two things** (BR1-05): the queue's own rows are *tasks*
  already (`task_queue`, `task_handlers.py`, Settings › *Background tasks*). The alerts step names
  its queue kinds after the ticket, as `ticket_alert` and `pm_job_alert` are: proposed
  `ticket_task_alert` and `ticket_task_alert_scan` (not in the code today). Its comments write
  "`ticket_tasks` rows" for a ticket's tasks and "`task_queue` rows" for the queue's.
- **Q7. Photos.** Recommended: **on the ticket** (D7); the *Mark done* dialog of the screens step
  offers *Add photo* into the ticket's photos. Alternative: the task as a seventh owner of the
  documents store, in a step of its own after the screens.

**SMTW-Review point** (proposed for `.claude/CLAUDE.md`): "**Ticket tasks (S106):** a task
(`ticket_tasks`) is written only by `tickets.py`'s task routes, under its ticket's lock (7), on a
ticket that is not closed, and each write adds its timeline line (`ticket_events.task_id`) in the
same transaction; done and cancelled are final and nothing deletes a task. A ticket with an open
task cannot be closed (`ticket_tasks_core.close_block`, both closing moves), so a closed ticket
has no open task. Who marks a task done is decided by data: its owner, or a `ticket:assign`
holder at the ticket's site. The block relies on a closer being able to cancel a task
(`ticket:close` and `ticket:assign`, the same holders today). A path that writes a
`ticket_tasks` row without (7) or without its timeline line, closes a ticket past the block, or
lets someone other than the owner or a `ticket:assign` holder mark a task done breaks S106."

**Assumptions**
- The request's *Schedule a PM visit from the VCB supplier* means one inspection visit, which is
  diagnosis and a task; a standing supplier PM would be a *Preventive* countermeasure (KLA,
  22-11-2026, in conversation with the orchestrator; § 1, § 2).
- Production's `ticket_events` is small enough for v59's table copy to take about a second
  (§ 4.1); the row count was not read.
- The due date is required. The screens step offers *Today / Tomorrow / In 7 days*, so it costs
  one tap; *Overdue* and the overdue alert need it.
- The term numbers of EN 13306 and the table numbers of ISO 14224 are *to verify*.
- No architecture doc: the repo's step settings have no *Architecture* entry, so there is nothing
  to depart from.

**Found while checking, not part of this step:** a ticket edit that replaces a long description
writes "Description: old → new" through `edit_lines` into `ticket_events.remark`
(`VARCHAR(1000)`), and `tickets_core.DESCRIPTION_MAX` is 1000, so two descriptions of over about
490 characters each cannot fit. What the database then answers (a refusal or a cut) is *to verify*;
no run was made. A candidate for a small fix step: a wider `remark` would settle it, and the
widening is an in-place change (§ 4.1's probe, § 7 D11).

**Gate A answers** (KLA, 22-11-2026): Q1 (a) `ticket:assign` adds, changes and cancels, the owner marks their own done; Q2 (a) open tasks block *Close* and *Not a fault*, never *Back in service*; the split: three steps (this backend, then the screens, then the alerts); Q3–Q7 as recommended (no copy into the why-why; every state but closed; no kind; both alerts; photos on the ticket). The brief is unchanged by the answers.

## 10. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | major | Accepted, option (a), on KLA's line of 22-11-2026 (one supplier inspection is diagnosis and a task; a standing supplier PM is a *Preventive* countermeasure). § 1 gains *How the two tasks are read* and says what a task is not. § 2 gains *The rule of thumb* as a bullet of its own (one-off work that finds or fixes this fault on the ticket; work that stops it for good on the improvement); § 3's glossary row uses the same words. § 7 D4 gains *What it costs*; D3's example is now a short check, with the note that a watch over weeks is the improvement's. § 9 Q2 (a) shows the consequence (the ticket waits in *Back in service*, against Plan § 9 Q12, or the task is cancelled and loses its owner and due date), the remedy (the work moves to the improvement as a countermeasure) and the border case of the request's own inspection. Q2's recommendation stays (a); **the choice is KLA's at gate A**, not decided here. § 9 *Assumptions* records the reading of the request. |
| BR1-02 | minor | Accepted, option (a). § 2: EN 13306's fault diagnosis is recognition, localisation and the *immediate* cause; ISO 9001 § 10.2.1 (b) names "finding its causes", the root cause is the improvement's why-why (b) and its removal (c), with the VCB as the example. The glossary row (§ 3) says "its immediate cause" and names the root cause as not a task's. |
| BR1-03 | minor | Accepted, option (a), with one addition. `owner.can_open` (§ 4.2, § 5.3, § 6): `alerts.people_at_unit` with `access_core.roles_holding(READ_KEY)` and `only_ids`, one query per detail, none without tasks. Added: the flag also needs a login, because `people_at_unit` does not ask for one and a role row without a login grants nothing. § 4.2 states that it is a hint, and the two cases where it is false for an owner who can open (a moved machine, a token role). § 5.6 says the query is a plain read. § 5.7 says why every reader gets it. Tests: § 8.3 *Detail* and the first of the two edge tests. The picker is unchanged (the recommendation did not ask for it). |
| BR1-04…BR1-09 | nit | Accepted, all six. 04: § 4.1 says v59 copies `ticket_events`, with a probe on the dev database (the foreign key refuses `ALGORITHM=INPLACE` with 1846; a `VARCHAR(1000)` widened to 2000 passes it); D11's reason is corrected, 300 stays; § 9 *Found while checking* notes that a wider `remark` would settle the description issue. 05: "`ticket_tasks` rows" in § 3, § 5.6 and the coder's notes; § 9 Q6 proposes the alerts step's queue kinds. 06: "an IT admin without a Team record" in § 5.7 and the *Mine* test. 07: the two edge tests in § 8.3, with their fixtures. 08: § 7 D4 *What it relies on* and § 5.7; beyond the recommendation, a comment at the two keys in `backend/config_rbac.py` (§ 3, comment only), because a later change to a key is made in that file, not in this brief. 09: the audit point drops "or adds a key for tasks" and lists the invariants. |
| BR2-01…BR2-05 | nit | Accepted, all five. 01: § 2 gives EN 13306's fault diagnosis in the standard's words (recognise, localise, identify the cause) and names "immediate cause for a task, root cause for the improvement" as Yantra's own line (§ 7 D1); the glossary row (§ 3) cites the standard for the corrective work, not for "immediate". This corrects the wording of the BR1-02 row above. 02: § 2 *The rule of thumb* drops the watch from the countermeasures and says that a watch over weeks is the improvement's *Watch period*; § 9 Q2's remedy says a trial fix that needs watching becomes a countermeasure. 03: § 9 Q2 (a)'s consequence says a ticket held open by a task also blocks scrapping its machine and deactivating its unit (`tickets_core.close_tickets_first`; checked at `backend/equipment.py:616` and `backend/masters.py:340`). Q2 stays KLA's choice at gate A. 04: § 3 *File count* says two files change in a docstring or a comment only. 05: § 4.2 says `owner.can_open` can be wrong both ways: also true for an owner whose Keycloak login does not work. |

## Feedback

- hindrance: `uv run --no-project python tooling/steps/brief_facts.py --help` ends in a
  `FileNotFoundError` traceback (it reads `--help` as a step id), so the tool's arguments had to
  be read from its source (one failed call, 22-11-2026).
- rule: the brief writer's size rule says "propose a split in one line of your final message; the
  user decides", while S070 made the cut inside the brief and the spawn prompt asked for one
  brief. Whether to draft the whole feature or the first half was not clear; this brief drafts the
  first half and records the cut in § 9 (about 15 minutes weighing the two).
- rule: the agent file says to read the architecture doc (settings: *Architecture*), and this
  repo's `## Step workflow` has no such entry; the README says a missing entry means none, but a
  line `- **Architecture**: none` would say so without a search (`.claude/CLAUDE.md`).

Review round 1 answers (22-11-2026):

- idea: self-check item 10 (migrations) could ask "does each `ALTER` copy the table, and how big
  is it in production?"; BR1-04 came from that gap, and a 17-line probe with `ALGORITHM=INPLACE`
  answered it in one run (`scratch/s106_br1_alter_probe.sql`, about 5 minutes).
- rule: the brief had a rule of thumb that its own example broke (BR1-01, the round's major). A
  self-check line "test every rule of thumb and glossary row against the request's own examples"
  would have caught it before review (self-check item 9 checks numbers and phrases, not
  examples).
- hindrance: the answers took the brief from 736 to about 900 lines, and the size rule gives no
  way back below 600 once the questions for gate A carry their consequences; whether a long § 9
  counts against the rule is not said (`.claude/agents/brief-writer.md`, *Size*).

Review round 2 answers (22-11-2026):

- idea: BR2-03 (a ticket held open by a task also blocks scrapping its machine and deactivating
  its unit) came from the callers of `tickets_core.close_tickets_first`. Self-check item 7 asks
  for actor × state per state change; a line "when a rule keeps a record longer in a state, grep
  what else reads that state" would have found it before review (one grep, about 2 minutes).
