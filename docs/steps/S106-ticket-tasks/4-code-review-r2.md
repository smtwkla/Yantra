```
Step: S106 — Tasks on a ticket
Doc: code-review r2
Author: Code reviewer (Opus 5.5)
Date: 22-11-2026
```

# S106 — code review, round 2

**Verdict: no `blocker` or `major` finding is open.** Fix round 1 fixes all four findings of round 1
(CR1-01 to CR1-04). Its diff brings in no new fault. All unit suites are green on my own run. This
round has no new finding.

Reviewed: `uv run --no-project python tooling/steps/step_snapshot.py diff S106 --from-round 1`
(4 files, 83 insertions, 10 deletions), `3-impl-report.md` § Fix rounds › Round 1 and its D5, and
`4-code-review-r1.md`. I re-read these files: `backend/tickets.py` `edit_task` (lines 1664–1692) and
the LOCK ORDER paragraph (lines 49–60); `backend/ticket_tasks_core.py` `task_change_line`;
`backend/tickets_core.py` `edit_lines`; the new and changed tests in
`backend/tests/test_ticket_tasks_api.py` and `backend/tests/test_ticket_tasks_core.py`; the
fixtures `make_person`, `user_at_sites`, `set_ticket_state` and `give_site_role` in
`backend/tests/conftest.py`; brief § 5.5 (the *task_changed* row and the 855-character limit).

## Tests

- **`tooling/run-tests.bat`**, `YANTRA_TEST_RUN=s106cr2`: **ALL SUITES PASSED.** The line-width
  check is green. Backend: 5485 passed (129 s); that is round 1's 5477 plus the 8 new tests (4
  parametrized cases of `test_who_may_write`, the closed-ticket test, the API same-name test and
  the two core tests). Frontend: 472 passed (8 s). Tooling: 247 passed (2 s).
- **Schema docs check:** not run. The round's diff does not touch `backend/local_db.py` or
  `docs/schema/`.
- **Browser tests:** none needed. The round changes no screen and no API field a spec reads; the
  only behaviour change is the text of one timeline line in a rare case.

## Findings of round 1

| ID | Severity | Status | Note |
|---|---|---|---|
| CR1-01 | minor | Fixed | `TestSharedRefusals` |
| CR1-02 | nit | Fixed | `restore` asserted on the raised ticket |
| CR1-03 | nit | Fixed | ids shown only when the names are equal |
| CR1-04 | nit | Fixed | docstring and comment |

- **CR1-01.** `test_who_may_write` runs add, change, mark done and cancel with the three users. A
  technician gets 403 (mark done through the owner rule, because `fitter` owns the task). An
  engineer of another site gets 404. The operator here who is an engineer elsewhere gets 403, so
  the decorator's "key anywhere" is not enough. The test then checks that the task is unchanged.
  `test_a_closed_ticket_comes_before_the_task_state` closes a ticket with one done and one
  cancelled task. It asserts `(409, None, TICKET_CLOSED)` for change, mark done and cancel on both
  tasks, so the ticket's 409 comes before the task's own 409. Red result: the coder made my failure
  scenario (`edit_task` locked with `READ_KEY`), and `test_who_may_write[change]` went red. The
  closed-ticket test has no red run. The report gives the reason: the order is already right, and
  only a reorder of the code would turn it red. A reason is given, so this is no finding.
- **CR1-02.** `test_not_a_fault_is_blocked_too` now asserts that *Back in service* (`restore`) has
  no `blocked_reason` while a task is open. The coder kept the raised ticket instead of starting it
  first, because a raised ticket already offers both moves. The tuple unpack
  `(restore,) = […]` fails if the move is not offered, and the test passes, so that is true. The
  report names the substitution.
- **CR1-03.** `task_change_line` shows each name with its person id only when the owner changed
  and the two names are equal (`same_name`). `edit_task` now builds `old` with `owner_id` before
  the changes and puts `owner_id` into `new` only when the owner changes. The `or None` on the
  remark is gone. That is safe: a change is written only when `changes` is not empty, and every
  changed field now gives a line (text and due date differ in their text; owners differ by name or,
  with the same name, by id). The longest line with ids is 855 + 2 × 20 = 895 characters, and a
  core test pins it at most 1000. Core tests cover the same name (ids shown), different names (no
  ids) and a text-only change (no owner line). The API test goes through the route. Red result
  given. D5 in the report is marked as replaced, and the brief's *task_changed* row ("Owner
  (names)") still describes every other case.
- **CR1-04.** The `_tasks` docstring names the extra query of `current_person_id`. The LOCK ORDER
  paragraph's stray line is joined; the line-width check is green.

## Nits

None.

## Checked and found consistent

- **The fix round's own diff.** No lock, permission or query changed. `edit_task` still takes the
  ticket lock first and reads nothing plain before it; the only moved statement is the build of
  `old`, which reads the already-fetched `task` row. `task_change_line` stays pure.
- **The new tests follow the file's pattern.** They use the module's helpers (`added`, `change`,
  `done`, `cancel`, `refusal`, `stored`) and the shared fixtures. Each test makes its own ticket,
  task and users, so no test depends on shared rows.
- **Docs.** The round makes no doc due: the brief and Plan.MD do not name the text of the
  same-name line, and no schema changed.

## For the user's check

- The same-name owner line shows the person's internal id, for example
  `Owner: Ravi K (person 12) → Ravi K (person 15)`. It appears only when an owner is changed to
  another person with exactly the same name, which is rare. The id tells the two people apart in
  the record, but a floor user cannot read it as a name. If you want something else there (for
  example the login name), say so for the screens step.
- Round 1's open point remains: decide at gate B whether the API tests stand in for brief § 8.7's
  acceptance on a dev ticket, or whether the screens step makes it on TK-2026-11-008.

## Feedback

- None this round. The round's diff was small (4 files), and the fix-round section of the impl
  report listed each finding with its tests and red result, so verification took one read of each.
