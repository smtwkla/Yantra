```
Step: S002 — Equipment register
Doc: impl-report
Author: Coder (Opus 5.5)
Date: 14-10-2026
```

# S002 — Implementation report

Implemented per the approved brief (`1-brief.md`, approved 14-10-2026 by KLA),
backend only. The appendix "Handover to S003" was not implemented. Nothing is
committed; the working tree holds the change for review.

**Test result.** `tooling/run-tests.bat` is green:
- **436 backend tests** pass, up from 237 before this step. The new and changed tests:
  - `test_equipment_core.py`: 97 new tests;
  - `test_equipment_api.py`: 93 new tests;
  - `test_masters_api.py`: 9 new cases;
  - the RBAC and auth tests listed in the brief, updated.
- **15 frontend tests** pass. The frontend was not touched, so `vite build` was not run.

Migration v4 was applied to the test DB by `ensure_schema()`. No drop was needed.

## What was built

- **Migration v4:**
  - `serial_counters`;
  - `equipment`, with the named CHECK `chk_equipment_level_place`;
  - `equipment_events`.
- **The equipment register API** at `/api/equipment`:
  - list, with paging, filters and search;
  - read one node, with its ancestors, its subtree to two levels and its event history;
  - create a node at any level;
  - change a node: fields, class, criticality, status, a move to another unit
    (equipment) or to another parent (parts).
- **Automatic codes,** from the class prefix and a per-prefix counter (`VBM001`).
  Codes never change.
- **The event history.** One event is written for each:
  - create;
  - unit move;
  - parent move;
  - status change;
  - change of the node's own criticality;
  - class change.
- **Unit access is enforced:**
  - Engineers, technicians, operators and storekeepers see and edit only equipment
    in their active units.
  - `equipment:read_all_units` (manager, IT admin; admin bypasses) sees every unit.
- **Masters rules extended:**
  - Any equipment, even scrapped, freezes a unit's code and site, and a class's code.
  - A unit can't be deactivated while it holds equipment that is not scrapped.
    Laid-up (`out_of_use`) equipment blocks it too.
- **Shared shell code moved out of `masters.py`** into `api_common.py` and
  `db_helpers.py`. The behaviour is unchanged.

## How it works

### Pure core (`equipment_core.py`)

- `validate_equipment(data, creating, this_year, stored=None)` returns
  `(clean, errors)` in the masters shape.
  - **On create:**
    - `level` is required, and so are `class_id` and `name`.
    - Equipment needs `unit_id` and no parent; parts need `parent_id` and no unit.
    - Equipment without a `criticality` gets `C`. An explicit `null` on equipment
      is a 400.
    - `status: scrapped` is a 400, through `check_status_change(None, …)`.
  - **On update,** `stored = {code, level}` comes from the node:
    - `code` (after strip and upper-case) and `level` may be sent back unchanged, and
      are then dropped. A changed value is a 400.
    - The place rules are checked against the stored level, for the fields sent.
  - The year must be between 1900 and `this_year + 1`.
  - A field that already failed its own parsing isn't reported twice.
- **The other rules:**
  - `format_equipment_code` uses `zfill(3)`;
  - `check_parent` holds the level × parent-level table;
  - `effective_criticality`, `full_path`, `check_status_change`.
- `tracked_changes(before, after)` compares these display values:
  - `full_path`: a change gives `moved_unit` for equipment and `moved_parent` for a
    part;
  - `class_code` gives `class`;
  - `criticality` gives `criticality`, with an own value of `None` shown as
    `inherit`;
  - `status` gives `status`.

  Any other key, such as name or make, is ignored.

### Shell (`equipment.py`)

- **One SQL fragment** (`_NODE_FROM`) resolves every node's root unit.
  - It joins `units` on `COALESCE(gp.unit_id, p.unit_id, e.unit_id)`.
  - `root_criticality` is the brief's CASE.
  - It is used only for plain reads.
- **The access helpers:**
  - `_accessible_unit_ids` gives `None` with `read_all_units`. Otherwise it gives
    the user's active unit ids, with the username lower-cased.
  - `_load_node_for_user` gives a 404 when the node is missing or outside the
    user's units.
  - `_load_target_node` checks a target parent in this order: 400 unknown, 403
    outside the user's units, 409 scrapped, 400 wrong level.
  - `_lock_target_unit` checks a target unit in this order: 400 unknown, 409
    inactive, 403 no access.
  - `_lock_class` gives 400 unknown or 409 inactive.
- **Locking** is commented at the top of the module.
  - The order is node → target parent → unit → class → counter.
  - Each lock is a single-row `FOR UPDATE` that returns the brief's decision
    columns:
    - equipment: `id, level, status, parent_id, unit_id, class_id`;
    - units: `id, active`;
    - classes: `id, code, active`.
  - **Every refusal is decided from those locked rows:** scrapped, level rule,
    active, and the class prefix used for the code. The fragment supplies only the
    access check and the display values.
  - `_accessible_unit_ids` runs after the node lock.
  - The scrap check is a locking read of the children, then of the grandchildren.
    The second read is skipped when there are no children.
- **Create:**
  1. Lock the unit, for equipment, or the parent, for a part.
  2. Lock the class.
  3. Bump the counter: `INSERT … ON DUPLICATE KEY UPDATE`, then a `SELECT` read
     back on the same connection.
  4. INSERT the node.
  5. Write the `created` event.

  All of this is one transaction. A refusal comes before the bump, and a failure
  after the bump rolls it back.
- **PUT:**
  1. Load the node with its lock (404).
  2. Scrapped → 409.
  3. Validate the body (400).
  4. A `parent_id`, `unit_id` or `class_id` equal to the stored value is dropped,
     so it is not a move.
  5. Take the target locks in order.
  6. The scrap check.
  7. Take the display values before.
  8. UPDATE.
  9. Re-read the node and write the events from `tracked_changes`.
- **List:**
  - The access filter is `u.id IN (…)`. A user with no units gets an empty page
    without a query.
  - The criticality filter works on `COALESCE(e.criticality, <root CASE>)`.
  - `q` escapes `\`, `%` and `_`.
  - `part_count` is a correlated count of the direct children that aren't
    scrapped.
- **The 409 for `uq_equipment_code`,** "Code collision — retry" with no field, is
  registered in `UNIQUE_KEY_ERRORS`.

### Shared code

- `api_common.py` holds:
  - `ApiError`;
  - `UNIQUE_KEY_ERRORS`, to which each module adds its keys;
  - `register_error_handlers(app)`, the app-level handlers for `ApiError` and
    `IntegrityError`, called once in `app.py`;
  - `actor()`;
  - `clean_body()`.
- `db_helpers.py` gains `insert_row`, `update_row`, `count` and `fetch_one`.

## Files touched

| File | Change |
|---|---|
| `backend/equipment_core.py` | **New.** Pure rules: validation, code format, level table, effective criticality, path, status rule, tracked changes |
| `backend/equipment.py` | **New.** Blueprint `/api/equipment`: the fragment, access helpers, locking, codes, events, list/detail/create/update |
| `backend/api_common.py` | **New.** `ApiError`, `UNIQUE_KEY_ERRORS`, `register_error_handlers`, `actor`, `clean_body` (moved from `masters.py`) |
| `backend/db_helpers.py` | Adds `insert_row`, `update_row`, `count`, `fetch_one` (moved from `masters.py`; `actor` is now a parameter) |
| `backend/masters.py` | Uses the shared helpers. A unit or class with equipment has frozen codes; a unit with equipment not scrapped can't be deactivated |
| `backend/masters_core.py` | `_parse_name` → `parse_name` and `_optional_text_parser` → `optional_text_parser` (made public, for reuse by `equipment_core`) |
| `backend/local_db.py` | Migration v4 |
| `backend/config_rbac.py` | New `equipment:read` and `equipment:read_all_units`; the Equipment block now comes before Masters |
| `backend/app.py` | Calls `register_error_handlers(app)`; registers `equipment_bp` before `masters_bp` |
| `backend/tests/conftest.py` | The truncate list and `FOREIGN_KEY_CHECKS=0`; `role_client(role, username=None)` with `X-Test-User` (TESTING only); `uniq.username()`; shared fixtures `admin`, `engineer`, `make_site`, `make_unit`, `make_class`, `make_equipment` |
| `backend/tests/test_equipment_core.py` | **New.** Pure tests |
| `backend/tests/test_equipment_api.py` | **New.** API tests, including the § 9 acceptance scenario |
| `backend/tests/test_masters_api.py` | Fixtures moved to `conftest`; equipment cases added to unit freeze, activation and class freeze; the `TestErrorMapping` monkeypatch target is now `masters.insert_row` |
| `backend/tests/test_rbac.py` | Role matrix rows updated |
| `backend/tests/test_auth.py` | Two exact permission lists updated |
| `docs/steps/S002-equipment-register/1-brief.md` | Status → In code review |
| `docs/steps/README.md` | S002 row → In code review |

## Decisions taken

Departures from the brief's literal text are marked **[departure]**.

1. **[departure] `validate_equipment` gains a fourth, optional parameter,
   `stored`.**
   - The brief's signature is `(data, creating, this_year)`.
   - An update needs the stored `level`, for the place rules and for criticality
     null on equipment, and the stored `code`, to compare it with what was sent.
   - The other option was a second core function that the shell would call after
     validation. That would split one body's validation across two calls.
2. **[departure] `_load_target_node(cur, node_id, child_level)`.**
   - The brief's signature is `(cur, node_id, field)`.
   - The field is always `parent_id`, and the level rule needs the child's level.
3. **[departure] A fourth access helper, `_can_access(cur, unit_id)`.**
   - It wraps `_accessible_unit_ids` for a single unit.
   - `_lock_target_unit` also checks access to the unit.
   - So `_accessible_unit_ids` is called from `_can_access` and from the list. No
     other code touches `user_units`.
4. **Target-unit check order: 400 unknown → 409 inactive → 403 no access.**
   - The brief fixes the order only for a target *parent*, where 403 comes before
     409 so that a scrapped state isn't revealed.
   - A unit's existence and active state are public, since the masters list shows
     every unit to every role. An engineer whose own unit was deactivated is
     therefore told "inactive" (409), not "no access".
5. **A small guard in `_load_target_node`.** The parent's lock can succeed while
   the plain read of it returns nothing. This happens only when the parent was
   committed after this transaction's snapshot was taken, that is, created during
   this very request. The guard answers 409 `parent_id` "The parent changed while
   saving; try again" instead of a 500.
6. **`unit_id` in the list and the detail is the root's unit, for parts too.** The
   brief says so for list rows. The detail uses the same row shape. A part's own
   column is always NULL, so nothing is lost.
7. **A `code` in a POST body is ignored,** like any unknown field, because the shell
   issues the code. The brief covers `code` only on PUT.
8. **On create, an explicit `criticality: null` on equipment → 400.** An absent one
   defaults to `C`. The brief states the 400 for a PUT and "required, default C" for
   equipment, and I applied the same rule to the POST.
9. **`status=scrapped` without `include_scrapped=1` returns no rows.** The filters
   intersect: scrapped stays hidden unless asked for. S003 may want the status
   filter to imply `include_scrapped`; that is a one-line change.
10. **[departure] `insert_row` and `update_row` take `actor` as an explicit
    parameter,** rather than reading `g.user` inside `db_helpers`.
    - This keeps the SQL helpers free of request state.
    - The `TestErrorMapping` fakes gain an `actor` parameter, as well as the brief's
      target rename.
11. **`masters_core` helpers made public** (`parse_name`, `optional_text_parser`).
    `equipment_core` reuses them rather than copying them, for DRY.
12. **Shared test fixtures moved to `conftest.py`:** `admin`, `engineer`,
    `make_site` and `make_unit`, from `test_masters_api.py`. `make_class` and
    `make_equipment` are new. The brief asked for `make_equipment` in `conftest`, and
    it needs the other fixtures.
13. **`_inject_test_user` now returns early unless `TESTING` is on.** This is the
    brief's BR3-04 point: `X-Test-User`, like `X-Test-Role`, works only under
    TESTING.
14. **The `IST` year** comes from a fixed `UTC+05:30` `timezone`, not `zoneinfo`.
    This needs no `tzdata` package on Windows, and IST has no DST.
15. **List and detail paths** use `strict_slashes=False`, so both `/api/equipment`
    and `/api/equipment/` work without a redirect.
16. **Event order within one PUT.** Several events from one PUT are written in this
    order: move, class, criticality, status.
17. **Message texts:**
    - "Scrap or move its parts first";
    - "This record is scrapped and cannot be changed";
    - "Code collision — retry";
    - "Code cannot be changed" / "Level cannot be changed";
    - "The unit holds equipment that is not scrapped; move or scrap it first".

## Not done / deferred / assumed

- **Not done, by the brief's design:**
  - the screens (S003) and the appendix *Handover to S003*;
  - bulk import;
  - a `remark` on events (§ 10.6).
- **Docs:** the brief gives the coder no doc changes. Its § 4 Docs items (Plan § 3,
  § 4.1, § 5 and Maintenance-Philosophy § 9) are the planner's.
- **Not tested: real concurrency.** The lock order and the "decisions from the
  locking reads" rule (BR3-01) are written as the brief specifies, but no test runs
  two transactions at once. The code reviewer should check BR3-01 against
  `equipment.py`, as gate A asked.
- **Race fixed in fix round 1 (CR1-01).** If a unit is created and a PUT moves
  equipment into it within the same instant, so that the new unit was committed
  after the PUT's snapshot, the re-read after the UPDATE could find no row and give
  a 500. It now gives a 409 "try again"; see Fix rounds, Round 1.
- **Assumed:** a scrapped node can't be a move target either. A move into a scrapped
  parent gives 409 `parent_id`, as the brief says. There is no "scrapped unit".
- **No browser check needed.** There is no UI in this step. The API can be tried by
  hand against the dev backend once S003 exists, or with curl under
  `DEV_AUTH_BYPASS`.

## Fix rounds

### Round 1

Answers `4-code-review-r1.md`. Scope approved by the user on 15-10-2026: fix CR1-01,
CR1-02 and CR1-04; no change for CR1-03; the transaction isolation level stays
REPEATABLE READ.

**Tests:** `tooling/run-tests.bat` is green — backend **448 passed** (436 before,
12 new), frontend (vitest) **15 passed**. The frontend was not touched, so
`vite build` was not run.

#### CR1-01 — minor — Accepted

The post-write re-read could return `None` (a unit, class or parent committed by
another request after this transaction's snapshot) and then crash with a 500, or
carry a stale unit/class code into the event text.

What changed in `backend/equipment.py`:
- **One re-read helper, `_reread(cur, node_id, message, field)`.** It reads the
  node through the fragment and raises **409 "This record changed while saving —
  try again"** with no `field` when the row is not visible. The transaction rolls
  back, so nothing is written (no row, no counter bump, no event). It is used:
  - after the INSERT (create) and after the UPDATE (PUT), through `_written_state`;
  - for the response read after commit (create and PUT). That read runs in
    autocommit and always sees the row, so this is only the uniform path;
  - in `_load_target_node` for the target parent, with its own message "The parent
    changed while saving — try again" and `field: parent_id`. The 409 and the field
    are unchanged from before; only the message punctuation now matches.
- **Event codes from the locking reads.** New `_written_state(cur, node_id, unit,
  equipment_class)` re-reads the node and, when this write locked a target unit or
  class, overrides `unit_code` / `class_code` with the code from that lock before
  building `full_path`. So a `class` event, a `moved_unit` path and a `created`
  path never show a code renamed while the write waited for its lock.
  - `_LOCK_UNIT` now also selects `code`; `_lock_target_unit` returns the row
    (`_lock_class` already did).
  - The PUT and the create keep those rows and pass them in.
- **Comment fixed** on the target-parent guard: the parent was "committed by another
  request after this transaction's snapshot", not "created during this very
  request". The full explanation now lives once, in `_reread`'s docstring.
- **Isolation level unchanged** (REPEATABLE READ), as the user decided.

Residuals, display-only and rarer than the fixed cases (no change, noted for the
record):
- The **site** code in a path still comes from the snapshot. Taking it from a lock
  would mean locking `sites`, which this module deliberately never does (the lock
  cycle argument in the module docstring). A site renamed in the same instant as a
  move into one of its empty units would show the old site code in that one event.
- On a re-parent, the **grandparent** in the new path comes from the snapshot. Codes
  are immutable, so the text can only be stale if the target parent was itself
  re-parented in the same instant.

Tests (new class `TestRereadAfterWrite` and fixture `stale_reread` in
`backend/tests/test_equipment_api.py`; the fixture wraps `insert_row`/`update_row`
so that every plain node read after the write returns a changed row, or `None`):
- a create that cannot read back → 409 with the exact body; no row; the next code
  is still n+1 (the counter bump rolled back);
- a PUT that cannot read back → 409; unit and status unchanged; no event;
- a target parent invisible to the snapshot → 409 `parent_id`;
- a stale class and unit code in the re-read → the `class` and `moved_unit` events
  carry the locked codes;
- a stale unit code on create → the `created` path carries the locked unit code.

#### CR1-02 — minor — Accepted

`_int_arg` now accepts only ASCII digits (`raw.isascii() and raw.isdigit()`), so
`²` or `١` gives 400 with the parameter's `field` instead of a `ValueError` → 500.
This covers `page`, `per_page`, `site_id`, `unit_id` and `class_id`.

`page` has a new named upper bound, **`MAX_PAGE = 100_000`**. Above it: 400 with
`field: page` ("page must be a whole number between 1 and 100000").
- Why that number: 100 000 pages × `MAX_PER_PAGE` 200 = 20 million rows, far past
  any real register, and the largest OFFSET (about 20 million) is well inside what
  MariaDB accepts. An unbounded page built an OFFSET MariaDB rejects (1064).
- Huge `site_id` / `unit_id` / `class_id` values were already harmless (they match
  nothing) and keep no upper bound.

Tests: `test_bad_parameters_are_400` gains `page=²`, `per_page=²`, `unit_id=١`,
`page=MAX_PAGE+1` and `page=10000000000000000000000000`; `test_defaults_and_bounds`
checks that `page=MAX_PAGE&per_page=200` is accepted (an empty page).

#### CR1-03 — nit — Deferred to S003

No change in S002, as the user decided: the behaviour is the brief's literal text.
S003's screens handle it (the status filter sends `include_scrapped=1` when it
selects Scrapped).

#### CR1-04 — nit — Accepted

Two tests in `TestUnitAccess` pin the orders:
- `test_a_scrapped_parent_elsewhere_is_403_not_409`: an engineer of unit A creating
  a part under a **scrapped** equipment of unit B gets **403 `parent_id`** (BR3-02).
- `test_an_inactive_unit_elsewhere_is_409_not_403`: the same engineer creating
  equipment in an **inactive** unit outside their units gets **409 `unit_id`**
  (Decision 4). It uses a fresh unit with no equipment, since a unit with live
  equipment cannot be deactivated.

#### Files touched in round 1

| File | Change |
|---|---|
| `backend/equipment.py` | `_reread`, `_written_state`, `MAX_PAGE`; `_LOCK_UNIT` selects `code`; `_lock_target_unit` returns the row; ASCII-only `_int_arg`; target-parent guard comment |
| `backend/tests/test_equipment_api.py` | `stale_reread` fixture, `TestRereadAfterWrite` (5 tests), 5 new bad-parameter cases, a `MAX_PAGE` bound check, 2 order tests in `TestUnitAccess` |
| `docs/steps/S002-equipment-register/3-impl-report.md` | This section; the "accepted race" note marked fixed |
| `docs/steps/README.md` | S002 index row status |

#### Decisions taken in round 1

- `MAX_PAGE = 100_000` (the user asked me to choose and state a bound).
- The target-parent message changed from "The parent changed while saving; try
  again" to "The parent changed while saving — try again", to match the new
  record-level message. The status (409) and field (`parent_id`) are unchanged.
- The response read after commit also goes through `_reread`, as the reviewer
  suggested, so no path can turn a missing row into a TypeError.
