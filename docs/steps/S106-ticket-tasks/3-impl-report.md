```
Step: S106 — Tasks on a ticket
Doc: impl-report
Author: Coder (Opus 5.5)
Date: 22-11-2026
```

# S106 — Implementation report

**Outcome.** The backend of tasks on a ticket is built as the brief describes: migration v59
(`ticket_tasks`, `ticket_events.task_id`), the pure rules in the new `ticket_tasks_core.py`, and five
routes in `tickets.py` (add, change, mark done, cancel, *my open tasks*). The ticket detail sends the
tasks, their counts and flags, and the close moves say why they are blocked; *Close* and *Not a fault*
are refused while a task is open. No screen changes, so nothing shows to users yet. All three unit
suites are green (numbers in § Tests run); `tooling\schema-docs.bat check` exits 0. One departure from
the brief: one existing test (`test_tickets_api.py::TestDetailAndAccess::test_detail`) pins the
per-user detail fields and needed `can_add_task` added to its list (§ 4, D9).

## 1. What was built

- **The record** (`ticket_tasks`, v59): one piece of the ticket's corrective work, with its text (up to
  300 characters), owner, due date and state (`open`, `done`, `cancelled`). Done and cancelled are final
  and keep what was done, or why it was cancelled, with who and when. Nothing deletes a task.
- **The API** (§ 6 of the brief), all under `/api/tickets`:
  - `POST /<id>/tasks` — add (`ticket:assign` at the ticket's site; at most 30 per ticket);
  - `PUT /<id>/tasks/<task_id>` — change the text, owner or due date of an open task;
  - `POST /<id>/tasks/<task_id>/done` — mark done (the owner, or a `ticket:assign` holder at the site);
  - `POST /<id>/tasks/<task_id>/cancel` — cancel with a reason (`ticket:assign`);
  - `GET /tasks/mine` — the user's open tasks on tickets they can see, by due date.
- **The timeline**: every task write adds one line (`task_added`, `task_changed`, `task_done`,
  `task_cancelled`) naming its task (`ticket_events.task_id`), in the same transaction. None is an
  ordered event, so the ticket's times (response, repair, downtime) do not change.
- **The close block**: *Close* and *Not a fault* answer 409 "This ticket has N open task(s). Mark … done
  or cancel … first." while a task is open. *Back in service* is never blocked.
- **The ticket detail** gains `tasks`, `task_counts`, `can_add_task`; each event carries `task_id`; the
  `close` and `not-a-fault` move entries carry `blocked_reason`.

## 2. How it works

**Pure core** (`backend/ticket_tasks_core.py`). `validate_task(body, creating)` checks the add and
change bodies: on an add every field is required, on a change an absent field stays as it is and none
may be null (`improvements_core.required_field`). The text is trimmed, 1–300; the owner a positive
integer (not a boolean); the due date strictly `YYYY-MM-DD` (`contracts_core.iso_date`, which refuses
`20261122` and week dates). `task_state_error(operation, state)` gives the nine cells of § 5.5.
`task_line` writes the add's line; `task_change_line(old, new)` builds the change's "Label: old → new"
lines through `tickets_core.edit_lines` (the longest is 855 characters, inside the remark's 1000);
`close_block(n)` gives the close refusal or None. The rules a task shares with a countermeasure
(`validate_done`, `validate_cancel`, `due_date_error`, `done_time_error`, `overdue_days`,
`action_counts`, `action_flags`) are used from `improvements_core` unchanged (brief D8).

**Shell** (`backend/tickets.py`, section *Tasks (S106)*). Each write validates the body first (400),
then takes the ticket's row `FOR UPDATE` through `_lock_open_ticket` (404 outside the predicate, 403
without the key at the ticket's site, 409 when closed), then reads the task plain (404 for a task of
another ticket), checks the owner rule (mark done only, 403), the task's state (409), and the owner,
due date or done time against the database (400). It writes the `ticket_tasks` row, then the timeline
line, and answers with the whole detail read inside the transaction. A change writes only the fields
that differ from the stored ones; a change of nothing writes nothing (no `updated_*`, no line). The
owner and the due date are checked on a change only when they change, so an owner who has left the
site stays until someone picks another.

**The owner rule** (mark done): `has_perm_at("ticket:assign", site)` or the user's Team record
(`current_person_id`) is the task's owner. The route's key is `ticket:read`, checked at the ticket's
site under the lock, so an owner who sees the ticket only through its machine's current unit at
another site gets 403.

**The close block**: `_apply_move`, for a move whose `to_state` is `closed`, counts the ticket's open
tasks right after the from-state check, with a plain read under the ticket's lock (7), which every task
write holds; above 0 it raises 409 with `close_block`'s text. `_moves` puts the same text (or None) on
the closing moves as `blocked_reason`.

**The detail** (`_tasks`): one query reads the tasks with the owner's name, `active`, login
(`username IS NOT NULL`), `may_own` (active and a member of the ticket's site, an `EXISTS` on
`memberships`) and the names of who added, finished or cancelled each (a login's person, else the
login). One more query, only when some owner has a login, gives `owner.can_open` through
`alerts.people_at_unit` with `access_core.roles_holding("ticket:read")` over the ticket's site and unit
(the recipient query of the ticket alerts). The flags come from `improvements_core.action_flags` with
"may assign" = `ticket:assign` at the site and "is owner" = the user's Team record is the owner and the
user holds `ticket:read` at the ticket's site.

**Mine** (`GET /tasks/mine`): `owner_id` = the user's Team record, `state = 'open'`, the ticket not
closed and inside the ticket predicate, by `due_date, id`, `LIMIT 200` with `total`. Each item carries
`can_mark_done` computed per row with `has_perm_at`. A user with no Team record gets an empty list.

**Locks** (written into `tickets.py`'s LOCK ORDER note and one sentence in `equipment.py`'s line (7)):
no new lock level; a `ticket_tasks` row is written only under its ticket's lock (7) and never locked on
its own. The edges are the ones a labour or assignee insert already takes; the four accepted deadlocks
are unchanged.

**Migration v59**: `CREATE TABLE IF NOT EXISTS ticket_tasks` (two keys, two foreign keys, two CHECKs of
`improvement_actions`' shape) and `ALTER TABLE ticket_events ADD COLUMN IF NOT EXISTS task_id … ADD KEY
IF NOT EXISTS … ADD CONSTRAINT fk_ticket_events_task FOREIGN KEY IF NOT EXISTS`. No precondition. The
migration's comment says that the foreign key makes MariaDB copy `ticket_events` once.

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v59 after v58, with its comment (shapes, no precondition, the table copy). |
| `backend/ticket_tasks_core.py` | **New**, pure: states, events, bounds and messages, `validate_task`, `task_state_error`, `task_line`, `task_change_line`, `close_block`. |
| `backend/improvements_core.py` | One public name, `required_field = _required`; no behaviour change. |
| `backend/tickets.py` | Docstring (tasks, LOCK ORDER); imports; `_event_rows` reads `task_id`; `_add_event` gains `task_id`; `_moves` gains `blocked_reason`; `_detail` gains `tasks`, `task_counts`, `can_add_task`; `_apply_move` refuses a closing move while a task is open; the section *Tasks (S106)* with the five routes and their helpers (`_TASK_COLUMNS`, `_by_name`, `_owners_who_can_open`, `_tasks`, `_task_row`, `_refuse_task_state`, `_check_task_due`). |
| `backend/equipment.py` | Docstring only: line (7) of the LOCK ORDER names `ticket_tasks` rows. |
| `backend/config_rbac.py` | Comment only at `ticket:assign` / `ticket:close`: the close block relies on their holders. |
| `backend/tests/test_migration_v59.py` | **New**: fresh shape, CHECKs, unknown `task_id` refused, a v58 database with a ticket and its events, re-run and half-applied v59. |
| `backend/tests/test_ticket_tasks_core.py` | **New**: § 8.2. |
| `backend/tests/test_ticket_tasks_api.py` | **New**: § 8.3. |
| `backend/tests/conftest.py` | `"ticket_tasks"` joins `_TABLES` after `"ticket_events"`. |
| `backend/tests/test_tickets_api.py` | `test_detail`'s per-user field list gains `can_add_task` (departure, § 4 D9). |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | The `ticket_tasks` line, the `ticket_events` line's addition; the two generated files by `tooling\schema-docs.bat write`. |
| `docs/Plan.MD` | § 3 owner-by-data paragraph; § 4.2 the close rule and the S106 bullet extended. |
| `docs/Maintenance-Philosophy.md` | § 12 Glossary: *Task (on a ticket)*. |
| `.claude/CLAUDE.md` | § SMTW-Review point *Ticket tasks (S106)*; § Step workflow self-check (2) names the `ticket_tasks` lock rule. |
| `docs/steps/INDEX.md`, `docs/steps/S106-ticket-tasks/1-brief.md` | Status (Implementing, then In code review). |

## 4. Decisions taken

- **D1. `required_field` placed after `_required`, not beside `is_id` and `text_field`.** The brief
  anchored it at `improvements_core.py:170`, but `_required` is defined at the countermeasures section
  further down; an alias above its definition would be a `NameError`. It sits right after `_required`
  with a comment naming S106.
- **D2. `task_change_line(old, new)` in the core.** The brief names `edit_lines` over *What to do*,
  *Owner* and *Due*; the formatting of the due date (DD-MM-YYYY) and the label order live in one pure
  function, which the shell calls and § 8.2's length test checks (855 characters). The core also holds
  `TASK_EVENTS` (the four names) and `EDIT_LABELS`.
- **D3. The task read joins the owner's name.** `_task_row` reads `SELECT k.id, k.state, k.text,
  k.owner_id, k.due_date, o.name AS owner_name …` (the brief's query plus the join), so a change's line
  has the old owner's name without a second query.
- **D4. `_by_name` is a two-line copy in `tickets.py`.** It is `improvements.py`'s private helper;
  `tickets.py` may not import `improvements.py` (the import direction in its docstring), and moving it
  would change S070's module beyond the brief.
- **D5. An owner changed to a person of the same name.** `edit_lines` compares the names, so the line
  was empty. *Replaced in fix round 1 (CR1-03):* the line now shows each name with its person id.
- **D6. `_moves(cur, row, keys, open_tasks)`.** A fourth parameter (its only caller is `_detail`). The
  closing moves are found by `MOVES[name].to_state == CLOSED`, not by their names, as `_apply_move`
  decides the block.
- **D7. Who counts as owner in the detail flag.** `current_person_id` is read only when the user holds
  `ticket:read` at the ticket's site (§ 5.4), so no extra query for a reader from another site.
- **D8. *Mine*'s flags** are computed after the cursor closes, with `has_perm_at` per row, as
  `improvements.my_actions` does.
- **D9. Departure: one existing test changed.** Brief § 8.4 expected `test_tickets_api.py` green as
  it is. `TestDetailAndAccess::test_detail` compares an operator's detail with the raiser's, leaving
  out a list of per-user fields; `can_add_task` is per user (IT admin true, the operator false), so it
  joins that list. No assertion is weakened otherwise.
- **D10. Test set-up for the *scheduled* state** uses the real *Schedule* move, because
  `chk_tickets_plan` refuses a `scheduled` row without its plan when the state is written straight.
- **D11. An owner whose only membership is removed** gets 403 from the route's key (`ticket:read` held
  nowhere), which is the brief's 403.

## 5. Not done, deferred, assumed

- **Browser tests: none run**, on the orchestrator's instruction (no screen changes, brief § 8.5). The
  brief's § 8.5 and § 8.7 also ask for one whole-suite browser run at Normal at the end; that run was
  not made. No spec reads the detail's new fields.
  **Added by the orchestrator, 22-11-2026:** the orchestrator made that whole-suite run at Normal on
  round 1's tree (`tooling\run-e2e-tests.bat`, no flag, 6 lanes): 433 passed, 15 skipped, 0 failed,
  4.5 min ("All lanes done in 281 s"); log `scratch/s106-e2e-normal.log`.
- **The acceptance by API on a dev ticket** (§ 8.7) was not made against the dev server (no backend
  running in this session); the same flow is covered by the API tests (`TestClose`, `TestMarkDone`,
  `TestTimeline`): two tasks added, one marked done by its owner, the close refused while the other is
  open and accepted once it is done or cancelled, the four lines on the timeline.
- **Found while testing:** the reserved run name `dev` has stale test databases (a run with no
  `YANTRA_TEST_RUN` refused with "This database is at schema v33, older than v41"). My first core run
  used the default by mistake; nothing was dropped. KLA can drop them by the two-step command in
  `.claude/CLAUDE.md` § Backend tests in parallel.
- Production's `ticket_events` row count (the table copy of v59) is still the brief's assumption.

## Tests run

- Targeted while coding: `test_ticket_tasks_core.py` (38 passed), `test_migration_v59.py` (6 passed),
  `test_ticket_tasks_api.py` with the ticket, parts, my-tickets, improvements-core, countermeasure and
  RBAC tests (one red: `test_tickets_api.py::TestDetailAndAccess::test_detail`, fixed by D9; then green).
- Final full run, `YANTRA_TEST_RUN=s106c1 tooling\run-tests.bat`: ALL SUITES PASSED — backend 5477
  passed (149 s), frontend 472 passed (16 s), tooling 247 passed (2 s, the line-width test included).
- After the full run, one import line of `tickets.py` moved to keep the imports in order
  (`from access_core import roles_holding` above `api_common`); the ticket tests ran again on it:
  `test_ticket_tasks_api.py`, `test_tickets_api.py`, `test_ticket_work_api.py`, 237 passed.
- `YANTRA_TEST_RUN=s106c1 tooling\schema-docs.bat write`: PASSED (4 passed, at migration v59); `check`
  at the end: PASSED (4 passed, exit 0).
- Build check: not needed (no frontend change).

## Manual checks

None. The brief has no browser check (§ 8.5) and no real-device check (§ 8.6); the screens step holds
them. Nothing was added to `docs/steps/device-checks.md`.

## Fix rounds

### Round 1

Review: `4-code-review-r1.md` (0 blocker, 0 major, 1 minor, 3 nits). All four are fixed. Files changed:
`backend/tickets.py`, `backend/ticket_tasks_core.py`, `backend/tests/test_ticket_tasks_api.py`,
`backend/tests/test_ticket_tasks_core.py`.

- **CR1-01 (minor) — Fixed.** New class `TestSharedRefusals` in `test_ticket_tasks_api.py`:
  - `test_who_may_write`, parametrized over add, change, mark done and cancel: a technician gets 403 (on
    mark done through the owner rule), an engineer of another site 404, an operator here who is an
    engineer elsewhere 403; the task is unchanged after the three.
  - `test_a_closed_ticket_comes_before_the_task_state`: one task done and one cancelled, the ticket
    closed; change, mark done and cancel on both answer `(409, None, TICKET_CLOSED)`, not the task's own
    409.
  - Red, then green. The fix adds tests only, so I broke the code instead: `edit_task` locked with
    `READ_KEY` (the reviewer's failure scenario). `test_who_may_write[change]` fails ("assert 200 == 403"
    on the operator here); with the code restored it passes. I made no red run of the closed-ticket test (it
    pins an order the code already has, and a reorder is a larger edit; stated, not shown).
- **CR1-02 (nit) — Fixed, the swap is named here.** Brief § 8.3 says "`restore` carries no such key".
  The existing `test_an_open_task_blocks_close_until_done_or_cancelled` checks `send-back`, because
  *Back in service* is not offered on a ticket that is already back in service. `test_not_a_fault_is_blocked_too`
  now also asserts, on the raised ticket where *Back in service* and *Not a fault* are both offered, that
  the `restore` entry has no `blocked_reason`. So both the brief's `restore` and the `send-back` are checked.
  (The reviewer suggested starting the ticket first; a raised ticket already offers both, so I did not.)
- **CR1-03 (nit) — Fixed.** `task_change_line` takes `owner_id` in `old` and `new`; when the owner changes
  and the two names are equal, each name is shown with its person id: `Owner: Ravi K (person 12) → Ravi K
  (person 15)`. `edit_task` passes the ids and no longer writes `remark` NULL for that case (this replaces
  decision D5 of the report). The longest line with ids is at most 895 characters, inside the remark's
  1000 (a core test pins it). Tests: core `test_an_owner_of_the_same_name_is_told_apart_by_the_person_id` and
  `test_the_longest_change_line_with_ids_fits_the_remark`; API
  `TestChange::test_an_owner_of_the_same_name_keeps_both_in_the_line`. Red: with the same-name check turned
  off, both new tests of the line fail ("assert '' == 'Owner: … (person 12) → …'"); with the fix restored
  they pass.
- **CR1-04 (nit) — Fixed.** `_tasks`'s docstring now says "Two queries for any number, one for none, plus
  one for the user's Team record the first time `current_person_id` runs in the request". The LOCK ORDER
  paragraph's "A change of tickets.state also" is joined to its next line (line 54, 108 characters).
  No test: a docstring and a comment.

**Tests run** (`YANTRA_TEST_RUN=s106f1`): `test_ticket_tasks_api.py`, `test_ticket_tasks_core.py`,
`test_tickets_api.py`, `test_ticket_work_api.py`: 283 passed (12 s); the tooling suite (the line-width test
included): 247 passed. The full three-suite run was not repeated in this round (the changes are the new tests,
one pure function and one route's event call, all inside the files above). No browser run (no screen change).

**Docs updated in this round:** none, because no doc is made due: the change is a log line's text for one rare
case, and the docs name no such text.

## Docs updated

- `docs/schema/notes.json` — a line for `ticket_tasks` (area *Tickets*); the `ticket_events` line
  gains the task column and the four events.
- `docs/schema/schema.json`, `docs/schema/schema-data.js` — regenerated by `tooling\schema-docs.bat
  write` (v59: the new table, `task_id`, its key and foreign key).
- `docs/Plan.MD` — § 3: a paragraph after the countermeasure's (a task is marked done by data, its owner
  or a `ticket:assign` holder at the site); § 4.2: the close rule now names "no open task", and the
  orchestrator's *Ticket tasks (S106 …)* bullet is extended with what S106 built (not duplicated).
- `docs/Maintenance-Philosophy.md` — § 12 Glossary: the row *Task (on a ticket)* in the brief's words,
  after *Countermeasure*.
- `.claude/CLAUDE.md` — § SMTW-Review: the point *Ticket tasks (S106)* (brief § 9's text); § Step
  workflow, *Self-check, repo items* (2): the `ticket_tasks` lock rule beside the other lock notes.
- `docs/steps/device-checks.md`, `help/`: nothing (no screen in this step).

## Feedback

- hindrance: a backend run with no `YANTRA_TEST_RUN` uses the reserved name `dev`, whose test databases
  were at v33 here, so 38 pure tests "errored" at set-up with a schema message (one wasted run, about
  1 minute; `scratch/backend-tests.log`). The wrapper could refuse to start without the variable when
  the agent workflow is on, or name the run it used in its summary line.
- rule: the brief's § 8.4 said no existing test pins the detail's key set, but
  `test_tickets_api.py::TestDetailAndAccess::test_detail` pins every field outside a per-user list; a
  self-check line "grep the tests for a whole-detail equality when the detail gains a per-user field"
  would have found it (one red run, about 3 minutes).
- rule: the spawn prompt said "no browser tests in this step", while the brief's § 8.5 and § 8.7 ask
  for one whole-suite run at Normal; the prompt wins, but the brief and the prompt disagree on a gate
  item (`docs/steps/S106-ticket-tasks/1-brief.md` § 8.5).
- rule: a brief line "X carries no such key" was tested on a different move than named (send-back for restore) without a note; a test-plan line that names a move could say which state offers it (CR1-02, about 5 minutes).
