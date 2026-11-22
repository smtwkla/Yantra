```
Step: S106 — Tasks on a ticket
Doc: code-review r1
Author: Code reviewer (Opus 5.5)
Date: 22-11-2026
```

# S106 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds the brief's backend as
approved: v59, the pure rules, the five routes, the close block and the detail fields. All unit
suites are green on my own run, and the schema docs check exits 0. The round has 1 `minor`
finding (missing refusal tests on three of the four task writes) and 3 nits.

Reviewed: `uv run --no-project python tooling/steps/step_snapshot.py diff S106` (17 files; the
working tree equals `refs/steps/S106`, checked with `--worktree`), the brief with its gate A
answers and Review log, and `3-impl-report.md`. I read these in full or around the hunks:
`backend/ticket_tasks_core.py`, the new section *Tasks (S106)* of `backend/tickets.py` and its
changed `_event_rows`, `_events_out`, `_tasks`, `_moves`, `_detail`, `_add_event` and
`_apply_move`, plus `_lock_ticket`, `_lock_open_ticket`, `_check_person`, `person_at_site`,
`_ticket_response`, `make_move`, `list_activity` and `events_by_ticket`; `improvements_core`
(`_required`, `_text`, `validate_done`, `validate_cancel`, `due_date_error`, `done_time_error`,
`overdue_days`, `action_counts`, `action_flags`); `contracts_core._iso_date`;
`alerts.people_at_unit`, `_people_with_role` and `read_closed_facts`;
`auth_utils.current_person_id`, `has_perm_at` and `permissions_at_site`; the locking reads of
`masters.py`, `improvements.py`, `equipment.py` and `task_handlers.py`; the v59 migration; the
three new test files; and the docs diffs.

## Tests

- **`tooling/run-tests.bat`**, `YANTRA_TEST_RUN=s106cr1`: **ALL SUITES PASSED.** The line-width
  check is green. Backend: 5477 passed (134 s). Frontend: 472 passed (8 s). Tooling: 247 passed
  (2 s). The counts match the coder's run.
- **`tooling\schema-docs.bat check`**, `YANTRA_TEST_RUN=s106cr1`, run after the unit suites:
  PASSED, 4 passed, exit 0, at migration v59 (log `scratch/schema-docs-s106cr1.log`).
- **Build check:** not needed, because no frontend file changed.
- **Browser tests:** the orchestrator's whole-suite run at Normal on this tree is recorded in the
  impl report § 5 and in `scratch/s106-e2e-normal.log` ("433 passed (4.5m)", "All lanes done in
  281 s"). No screen changed, and no spec reads the detail's new fields, so no finding of mine
  needs a re-run. The brief has no *Automated* or *On a real device* check (§ 8.5, § 8.6).

## Findings

### CR1-01 (minor) — Change, mark done and cancel have no test of the shared refusals

`backend/tests/test_ticket_tasks_api.py:225` (`TestAdd::test_who_may_add`) and `:246`
(`test_a_closed_ticket_takes_no_task`) test § 5.1 steps 1–5 (the key anywhere, the predicate
404, the key at the ticket's site 403, closed 409) on **add** only. The **change** route
(`PUT …/tasks/<task_id>`) has no permission test at all: no 403 for a technician, none for "an
operator here who is engineer elsewhere", and no 404 outside the predicate. Mark done and cancel
have their 403s, but none of change, mark done or cancel is tested on a closed ticket. On a closed
ticket the ticket's 409 "This ticket is closed" must come before the task's own 409 (§ 5.1 step
5 before step 8). A closed ticket can only hold done or cancelled tasks, so the order decides
which message the user sees.

**Failure scenario:** a later edit copies `mark_task_done`'s lock into `edit_task`
(`_lock_open_ticket(cur, ticket_id, READ_KEY)`). The route's decorator still asks for
`ticket:assign`, but only at some site. An operator at this site who is an engineer at another
site then passes the decorator and the lock, and can rewrite any task's text, owner and due date
here. No test turns red. In the same way, a reorder that reads the task before
`_lock_open_ticket` would answer "Only an open task can be changed" on a closed ticket, and no
test would catch it.

**Suggested fix:** parametrize a test over the four writes (add, change, mark done, cancel) with
the three users of `test_who_may_add`: a technician gets 403, except on mark done where the owner
rule decides; an engineer of another site gets 404; the operator here who is engineer elsewhere
gets 403. Add one test that sets the ticket to `closed` after one task is done and one is
cancelled. It then asserts `(409, None, TICKET_CLOSED)` for change, mark done and cancel.

## Nits

- **CR1-02** (nit) `backend/tests/test_ticket_tasks_api.py:468`: brief § 8.3 says "`restore`
  carries no such key", but the test checks `send-back`, because *restore* is not offered on a
  back-in-service ticket. In `test_not_a_fault_is_blocked_too`, start the ticket first (so
  *restore* and *Not a fault* are both offered), assert that *restore*'s entry has no
  `blocked_reason`, and name the substitution in the report.
- **CR1-03** (nit) `backend/tickets.py:1689`: when an owner is changed to a person with the same
  name (impl report D5), the line drops the owner change, and the old owner is then recorded
  nowhere: `ticket_tasks` keeps only the current owner. When the two names are equal, pass each
  name with its person id to `task_change_line`, so that the line still keeps the old and the new
  owner (brief § 2, ISO 9001 § 7.5.3).
- **CR1-04** (nit) `backend/tickets.py:400` and `:54`: `_tasks`'s docstring says "Two queries for
  any number, one for none". `current_person_id` can add a third query the first time it runs in
  a request (a detail GET), so say so. The LOCK ORDER paragraph also leaves "A change of
  tickets.state also" alone on line 54; re-wrap it into the next line.

## Checked and found consistent

- **The lock order** (brief § 5.6). In every task write the ticket's `FOR UPDATE` (`_LOCK_TICKET`
  in `_lock_ticket`) is the transaction's first statement. Its first plain read is
  `read_ticket` after the lock. The count of 30, `_task_row`, `_check_person`,
  `current_person_id` and the insert or `UPDATE` all come after it. `clean_body` touches no
  database. No path locks a `ticket_tasks` row on its own. The new edges are (7) then a `people`
  row shared, and (7) then the transaction's own task row. I checked these edges against every
  other locking read of `tickets` (`masters.py:305` locks the unit then tickets shared;
  `masters.py:820` failure codes; `improvements.py` shared only; `task_handlers.py:196` (7)
  alone; `tickets.py:951` the repeat, shared). None of them holds a `people` row or a
  `ticket_tasks` row first, so there is no new cycle. The `tickets.py` and `equipment.py` notes
  say the same.
- **The close block.** `_apply_move` refuses every move whose `to_state` is `closed`, right after
  the from-state check and before the event time. `MOVES` has exactly two such moves (`close`,
  `not-a-fault`). Every path that closes a ticket goes through `make_move` → `_apply_move`: the
  raise's *Already fixed* uses `_apply_move` only for `restore`, and no backend code writes
  `tickets.state` in any other place. The count is a plain read under (7), and its snapshot
  starts after the lock, so a task added just before is seen. `blocked_reason` comes from the
  same `close_block` text.
- **Owner by data and fail-closed RBAC.** Add, change and cancel use `require_perm(ASSIGN_KEY)`
  and then `ticket:assign` at the ticket's site under the lock. Mark done uses `ticket:read` at
  the site, then `has_perm_at(ASSIGN_KEY, site)` or `current_person_id == owner_id`. A user with
  no Team record owns nothing, and IT admin passes through its token key. The detail's
  `can_mark_done` asks for `ticket:read` at the site too (§ 5.4). In *Mine*, each row's flag uses
  `has_perm_at(READ_KEY, site)`, so the moved-machine owner gets no button that ends in a 403.
  The tests cover this (`TestOwnerRuleEdges`). No new key, `test_role_matrix` unchanged, the
  actor always comes from `actor()`, and no SQL holds a client value outside its parameters.
- **The timeline.** Each of the four writes adds exactly one `ticket_events` row with its
  `task_id`, after the change, in the same transaction, through `_add_event`. A change of nothing
  writes no row and stamps no `updated_*`. None of the four events is in `ORDERED_EVENTS`, so
  `_last_ordered_event`, `ticket_times`, `latest_restoration`, `events_by_ticket` and the
  closed-ticket email are unchanged.
- **v59.** It comes after v58, and no earlier migration or frozen fixture changed. It matches
  brief § 4.1 column for column, with both CHECKs, both keys and the `ALTER` in v50's
  `IF NOT EXISTS` form. No `_PRECONDITIONS` entry is needed: a new table and a nullable column
  touch no existing row. The comment says that MariaDB copies `ticket_events`. The upgrade test
  runs on a v58 database with a ticket and two events. The re-run and the half-applied run are
  covered. Under `--dist loadscope` the module keeps its order on one worker. `conftest._TABLES`
  gains `ticket_tasks`.
- **The fields and the messages** (§ 5.2–§ 5.5, § 6). `validate_task`, the nine state cells,
  `close_block`, `task_line` and the 855-character change line all match the brief. The detail's
  `tasks` item and the *Mine* item carry exactly the brief's keys. `_by_name` resolves through
  `uq_people_username`, so a join cannot double a row.
- **The two stated departures.** D1: `required_field = _required` has to come after `_required`
  (line 354), because an alias at line 170 would raise `NameError` at import. The core test pins
  it as the same function. D9: `test_detail` compares an operator's detail with IT admin's, and
  `can_add_task` really differs per user. Adding it to the per-user set weakens no other
  assertion. D2–D8, D10 and D11 are inside the brief or name a choice it left open.
- **The docs pass.** `notes.json` (the `ticket_tasks` line and the `ticket_events` addition) and
  the two generated files match v59, and `check` exits 0. `Plan.MD` § 3 and § 4.2, the glossary
  row in `Maintenance-Philosophy.md` § 12 (the brief's words) and the SMTW-Review point in
  `.claude/CLAUDE.md` (the brief's text) are all present. The self-check line (2) in
  `## Step workflow` is an extra the brief did not list. It is accurate and is listed under
  *Docs updated*. `device-checks.md` and `help/` correctly have nothing.
- **Scope and track.** The step has no screen, no alert and no new key. It is on the full track
  (it has a migration, RBAC and locks).
- **Use on the floor.** The step has no screen. The user-facing strings (the close block,
  `TASKS_FULL`, `OWNER_OR_ASSIGNER`, the shared countermeasure messages) are each one short line
  that says what is wrong and what to do.
- **The database down.** `test_the_database_down_is_503` covers the add. The other routes use the
  same `get_db()`.

## For the user's check

- No browser or device check in this step (brief § 8.5, § 8.6).
- Brief § 8.7's acceptance "by API on a dev ticket" (the VCB case) was not made against the dev
  server. The coder covers the same flow with `TestClose`, `TestMarkDone` and `TestTimeline` (impl
  report § 5). At gate B, decide whether that is enough or whether the screens step makes the
  acceptance on TK-2026-11-008.

## Feedback

- hindrance: `step_snapshot.py diff S106 -- <11 paths>` printed one 56 KB block, which the tool
  output put into a file, so I read the diff again in smaller groups (about 2 minutes;
  `tool-results/bg1plqzj0.txt`). A `--per-file` or size-capped mode would avoid the second read.
