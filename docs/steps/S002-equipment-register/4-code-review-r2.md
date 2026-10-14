```
Step: S002 — Equipment register
Doc: code-review r2
Author: Code reviewer (Opus 5.5)
Date: 15-10-2026
```

# S002 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** There are 2 `nit` findings,
both about wording; neither needs a code change. The approved fixes (CR1-01,
CR1-02 and CR1-04) are correct and complete. BR3-01 still holds, and the lock
order has not changed.

**Scope of the review:**
- the full S002 working-tree diff against `817844c`;
- `1-brief.md` (approved; § 10 holds no amendments);
- `3-impl-report.md`, including "Fix rounds" → "Round 1";
- `4-code-review-r1.md`.

`docs/steps/S003-equipment-screens/` and the README status edits are excluded.

**The user's decisions for round 1:**
- fix CR1-01, CR1-02 and CR1-04;
- defer CR1-03 to S003;
- keep REPEATABLE READ.

**Test result (run by the reviewer):** `tooling/run-tests.bat` is **green** (exit 0).
- Backend: **448 passed** in 20.6 s. That is 436 in r1 plus the 12 new tests.
- Frontend (vitest): **15 passed**.
- The frontend was not touched, so `vite build` was not run.

**Did anything change beyond the approved fixes?** No.
- Only two files changed after r1 was written (23:44, 14-10): `backend/equipment.py`
  and `backend/tests/test_equipment_api.py`. The report and the README changed
  too. I compared the file modification times.
- Every other S002 file is as r1 reviewed it.
- In `equipment.py`, the only changes are the ones listed under "Files touched in
  round 1":
  - `_reread` and `_written_state`;
  - `MAX_PAGE`;
  - `_LOCK_UNIT` now also selects `code`;
  - `_lock_target_unit` now returns the row;
  - `_int_arg` accepts ASCII digits only;
  - the guard comment.
- The isolation level is unchanged: no `SET TRANSACTION`, and `transaction()` is
  untouched.
- CR1-03 is left alone, as the user decided.

## Verification of the round-1 fixes

### CR1-01 — Fixed

- **(a) The 500 is gone.**
  - `_reread` (`equipment.py:107-116`) raises 409 "This record changed while
    saving — try again", with no field, when the fragment read finds no row.
  - It is used in four places:
    - after the INSERT, through `_written_state` (`:423`);
    - after the UPDATE, through `_written_state` (`:456`);
    - in `_load_target_node` (`:232`);
    - in both response reads after commit (`:426`, `:459`).
  - So no path reaches `_path(None)` or `_tracked_state(None)`.
  - The 409 is raised inside `transaction()`, so it rolls back the row, the counter
    bump and the events. Two tests prove this:
    - `test_create_that_cannot_read_back_is_409_and_rolls_back` (no row; the next
      number is n+1);
    - `test_update_that_cannot_read_back_is_409_and_rolls_back` (the unit and
      status are unchanged; no event).
- **(b) Stale event text.**
  - `_written_state` (`:306-316`) puts the locked unit's code and the locked
    class's code over the snapshot values, before it builds `full_path`.
  - The override is right for every caller:
    - **A unit lock** is taken only for `level = equipment`. The core's place rules
      reject `unit_id` on parts. For equipment, `e.unit_id` is the root unit, so
      the locked unit *is* the node's unit.
    - **A class lock** is always the node's own new class (`e.class_id`), which is
      where `class_code` comes from.
    - **When this write took no lock**, the snapshot code is current. A unit that
      holds equipment has a frozen code, and so does a class.
  - Tests:
    - `test_class_and_unit_codes_in_events_come_from_the_locks`;
    - `test_created_path_takes_the_unit_code_from_the_lock`.
- **(c) The guard.**
  - The guard is now the shared `_reread`, with its own message and
    `field: parent_id`, so it is not duplicated.
  - Its comment is corrected, and the full explanation now lives once, in the
    `_reread` docstring.
  - Test: `test_a_target_parent_the_snapshot_cannot_see_is_409_parent_id`.
- **The test fixture.** `stale_reread` is a sound simulation:
  - It turns on only after the real `insert_row` / `update_row` has run.
  - So the "before" read and the target reads stay real, and only the post-write
    re-read is faked.
  - Real concurrency is still untested. This is the same gap as in r1, and the
    report states it.

### CR1-02 — Fixed

- **Digits.** `_int_arg` (`:327-335`) now requires `raw.isascii() and raw.isdigit()`.
  - `²` used to be a 500; it is now a 400.
  - `١` is also a 400 now. Before, `int('١')` quietly read it as `1`; refusing it
    is stricter and correct.
  - An empty string, a space or a sign is still a 400.
- **The page bound.** `MAX_PAGE = 100_000` is named, and a comment gives the
  reason.
  - The largest OFFSET, about 20 million, is well within MariaDB's range.
  - `page = MAX_PAGE + 1` and a 26-digit page give 400 `page`.
  - `MAX_PAGE` with `per_page = 200` is accepted and returns an empty page.
- **`site_id` / `unit_id` / `class_id`** keep no upper bound. As r1 noted, a huge
  value there only matches nothing.
- **Tests:** the five new cases are in `test_bad_parameters_are_400`, and the bound
  check is in `test_defaults_and_bounds`.

### CR1-04 — Fixed

Both tests pin a real order: swapping the checks in the code would turn each test
red.
- `test_a_scrapped_parent_elsewhere_is_403_not_409` (`test_equipment_api.py:727`).
  The parent is scrapped *and* outside the engineer's units, so swapping the two
  checks would give a 409.
- `test_an_inactive_unit_elsewhere_is_409_not_403` (`:736`). The unit is inactive
  *and* inaccessible, so swapping would give a 403.

### CR1-03 — Deferred to S003 (by the user)

There is no code change, which is correct.

## BR3-01 and the lock order after the changes

**Decisions still come from the locking reads.**
- In `_load_target_node`, the decisions are taken from `locked`:
  - scrapped → 409 from `locked["status"]`;
  - the level rule from `locked["level"]`.
- The `_reread` there supplies only `root_unit_id` for the access check. That is a
  plain fragment read, which the brief allows.
- `_lock_target_unit` still decides unknown and inactive from the locked `units`
  row, and now returns that row.
- `_lock_class` is unchanged; the code prefix still comes from the class lock
  (`:421`).
- `_written_state` changes only display values, and no refusal reads from it.
- Its 409 is a retry signal, not a business decision. It can fire only when the
  snapshot misses a row that the locking reads proved exists. At worst it refuses
  a valid write, which the user then retries; it never lets an invalid write
  through.

**The lock order is unchanged.**
- Create: (3) unit **or** (2) parent → (4) class → (5) counter.
- PUT: (1) node → (2) parent → (3) unit → (4) class → the subtree.
- Adding `code` to `_LOCK_UNIT` keeps it a single-row `FOR UPDATE` on a constant
  string.
- `_reread` and `_written_state` are plain reads, which take no locks.
- No new table is locked, and `sites` is still never locked.

## The coder's two left-alone cases

**Judgement: both are acceptable to leave in code.**
- Both are display-only: only the event text can be wrong.
- Both need two writes on the same rows within milliseconds.
- Fixing them would mean extra reads, or locking `sites`, which this module
  rightly avoids.

But the report describes the first case wrongly, and the second one only in
part. See CR2-01.

- **Site code.**
  - **The case as reported cannot happen.** The report says "a site renamed in the
    same instant as a move into one of its empty units".
    - `update_site` refuses a code change once the site has any unit
      (`masters.py:143-145`).
    - The target unit is in that site.
    - So the site cannot be renamed.
  - **The real case is a re-site of the unit.** `update_unit` allows an admin to
    change an empty unit's `site_id`.
    1. An admin re-sites the empty unit U while a move into U (or a create in it)
       waits for U's lock.
    2. The path then joins the locked unit code with the *old* site code from the
       snapshot.
  - **Acceptable:** it is admin-only, needs an empty unit, and is a one-event,
    display-only race.
- **Grandparent code.**
  - **The race exists as described:**
    1. A component re-parent waits on the target component-unit's lock.
    2. Meanwhile another request re-parents that component-unit.
    3. Codes are immutable, but which equipment is the grandparent has changed.
  - **More of the path is stale than reported.** The new grandparent may be in
    another unit, so the root unit and site codes can be stale as well, not only
    the grandparent's code.
  - **The access check uses the same snapshot.** `_can_access(target["root_unit_id"])`
    is a plain fragment read, and the brief explicitly allows that. So in this
    race, the 403 check is also judged against the target's *old* unit. This is
    not new in round 1, and it is within the brief.
  - **Acceptable:** the race needs two concurrent moves of nodes in the same small
    subtree. Equipment is moved rarely and by few users.

## Findings

### CR2-01 — nit — The report's account of the left-alone cases is inaccurate

**Where:** `3-impl-report.md`, Fix rounds → Round 1 → CR1-01 → "Residuals".

**Problem.**
- **The site case** names a site *rename*, which `update_site` forbids once the
  site has a unit. The case that is really left open is a *re-site of an empty
  target unit*.
- **The grandparent case** leaves out that the root unit and site codes in the path
  can be stale in the same race.

**Failure scenario.**
1. A later reader, or S003's planner, trusts the report.
2. They believe that site codes cannot go stale, since a rename is blocked.
3. Or they believe only the grandparent segment of a path can be wrong.
4. Then they misjudge an odd event text that they find in the history.

**Suggested fix.** Correct the two bullets in the report. Make no code change; both
cases stay accepted as display-only races.

### CR2-02 — nit — The post-commit response read tells the user to "try again" after a successful write

**Where:**
- `backend/equipment.py:426` (create);
- `:459` (PUT).

**Problem.**
- After `transaction()` commits, the response read goes through `_reread`. On
  `None`, that would answer 409 "This record changed while saving — try again".
- But the write has committed by then. Retrying a create would make a **second**
  node with the next code.
- **The path cannot be reached today:**
  - the connection is back in autocommit, so the read uses a fresh view;
  - nothing deletes equipment;
  - the fragment's joins follow FKs.
- So this is a wording trap for the future, not a live bug. Report Decision
  "round 1 / 3" chose this path on purpose, for uniformity.

**Failure scenario.**
1. A later step adds hard delete, or a join that can miss.
2. A create commits, and then the response read finds nothing.
3. The user sees "try again", retries, and gets a duplicate equipment.

**Suggested fix.** This is optional. Either:
- give the post-commit reads a message that does not invite a retry (for example
  "Saved, but the record could not be read back — reload"); or
- keep it, and add one line to the `_reread` docstring saying that after commit
  the `None` branch is unreachable.

## Checked and found consistent

- **Every finding from round 1 has an answer in the report:**
  - `Accepted`: CR1-01, CR1-02 and CR1-04;
  - `Deferred`: CR1-03, to S003, by the user.
  - The scope matches the user's approval.
- **Round 1's decisions are listed in the report:**
  - the `MAX_PAGE` value;
  - the change of message punctuation;
  - `_reread` used for the post-commit read.
- **The tests:**
  - 12 new tests, all green. They cover both failure modes of CR1-01: a missing
    row, and stale codes.
  - The rollback of the counter and the events after a late 409 is tested.
- **Security:** no route, permission key, actor source or SQL construction changed.
  The `IN (…)` lists are still placeholder counts only.
- **CLAUDE-COMMON:**
  - The core is untouched.
  - One re-read helper replaces the duplicated guard (DRY).
  - Comments explain *why*: the snapshot docstring and the `MAX_PAGE` reason.
  - No exception is swallowed.
  - No migration changed.
- **Everything r1 recorded as consistent still holds:** migration v4, the counter,
  the fragment, the tree rules, status, events, unit access, RBAC, masters, DB
  availability and `conftest.py`. None of these were touched in round 1.

**Not for the coder.** The planner still owes the doc edits of brief § 4 Docs:
- Plan § 3, § 4.1 and § 5;
- Maintenance-Philosophy § 9.

## Manual check for the user

- **No browser check:** S002 has no UI.
- **Optional:** an API smoke run against the dev backend (`DEV_AUTH_BYPASS=1`):
  1. Create an equipment, a component-unit and a component.
  2. Move the equipment to another unit.
  3. Check that `GET /api/equipment/<id>` shows the `created` and `moved_unit`
     events with the right paths.
  4. Try `GET /api/equipment?page=100001`: it should give 400 `page`.
