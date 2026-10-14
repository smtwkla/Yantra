```
Step: S002 — Equipment register
Doc: code-review r1
Author: Code reviewer (Opus 5.5)
Date: 14-10-2026
```

# S002 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 2 `minor` and 2
`nit` findings. BR3-01 (decisions come from the locking reads), which Gate A asked
this review to check, **holds** in `backend/equipment.py`.

**Scope of the review:**
- the working-tree diff against `817844c`: `backend/` plus the new untracked files;
- `1-brief.md` (approved; Review log up to Gate A; § 10 holds no amendments);
- `3-impl-report.md`.

`docs/steps/S003-equipment-screens/` and the README/status edits are excluded, as
the orchestrator asked.

**Test result (run by the reviewer):** `tooling/run-tests.bat` is **green**.
- Backend: **436 passed** in 18.2 s.
- Frontend (vitest): **15 passed**.
- The frontend was not touched, so `vite build` was not run.

## BR3-01 verification (Gate A)

Each refusal in a write path, and the row it is decided from:

| Write path | Refusal | Decided from | OK |
|---|---|---|---|
| PUT | missing node → 404 | `_LOCK_EQUIPMENT` row (`equipment.py:198-201`) | yes |
| PUT | outside the user's units → 404 | fragment read, **after** the node lock (`:202-203`). Access is a plain read by design | yes |
| PUT | scrapped → 409 | `locked["status"]` (`:405`) | yes |
| PUT | level rules / `level` immutable / criticality null on equipment | `locked["level"]` (`:408`) | yes |
| PUT | `code` immutable | `node["code"]`, a plain read. The node row is already locked when the snapshot is taken, so this read equals the locked row; and `code` never changes. The brief's lock column list has no `code` either | yes |
| PUT | "same parent/unit/class is not a move" | `locked[field]` (`:412-414`) | yes |
| create / PUT | target parent unknown → 400; scrapped → 409; level → 400 | `_LOCK_EQUIPMENT` row of the target (`:211-226`) | yes |
| create / PUT | target parent outside the user's units → 403 | fragment read (allowed: "access to the target's root, plain fragment read") | yes |
| create / PUT | unit unknown → 400; inactive → 409 | `_LOCK_UNIT` row `id, active` (`:233-238`) | yes |
| create / PUT | class unknown → 400; inactive → 409 | `_LOCK_CLASS` row `id, code, active` (`:245-250`) | yes |
| create | code prefix | `equipment_class["code"]` from the class lock (`:391-392`) | yes |
| PUT scrap | live child or grandchild → 409 | `SELECT id, status … WHERE parent_id = %s FOR UPDATE`, then `… parent_id IN (…) FOR UPDATE`. The second read is skipped when there are no children (`:274-285`) | yes |

**Lock order.**
- PUT: node (1) → parent (2) → unit (3) → class (4) → the subtree.
- Create: parent (2) **or** unit (3) → class (4) → counter (5).
- Every lock is a single-row `FOR UPDATE` on a constant SQL string. The fragment
  `_NODE_FROM` is never used with `FOR UPDATE`.

**`_accessible_unit_ids` timing.**
- It always runs after the node lock (PUT), or after the target lock (create).
- On a PUT, `transaction()` sends `BEGIN`, and InnoDB creates the read view at the
  first plain read. The first plain read is `_read_node` at `:202`, which comes
  after the node lock. So the snapshot is taken after (1).

**Scrap subtree.** The scrap subtree check is a locking read of the children and
grandchildren, as the brief specifies.
- A concurrent create under the node waits on the node lock: it locks the node as
  its target parent, and the FK check also needs it. It then sees `scrapped` → 409.
- A concurrent re-parent *into* a child is serialised on that child's row.
- The reverse-order deadlock is the one the brief accepted.

**Masters interaction.**
- `update_unit` and `update_equipment_class` count equipment after their own
  `_lock_row`, the first statement of the transaction.
- Every way equipment can become "live in unit X" or "of class Y" locks that unit
  or class row first: create, and a move or reclassify into it. Leaving a unit or
  class does not lock it, which can only make masters refuse more.
- No lock cycle exists: equipment never locks `sites` or `user_units`, and masters
  locks no equipment rows.

The one weak spot in this area is the **display/event re-read after the write**.
It goes through the same snapshot, and BR3-01 does not govern it (it is display
data). See CR1-01.

## Findings

### CR1-01 — minor — The post-write re-read uses the old snapshot: a 500 or stale event text in a narrow race

**Where:**
- `backend/equipment.py:394` (create: the `created` event path);
- `:423-425` (PUT: `_tracked_state(_read_node(...))`);
- `:216-219` (the guard in `_load_target_node`).

**Problem.**
- After the write, the node is re-read through `_NODE_FROM` with plain reads, under
  REPEATABLE READ. The snapshot was fixed at the first plain read, often *before*
  a later target lock waited on a concurrent commit.
- **(a) A 500.** The fragment `JOIN`s `units` and `equipment_classes`. If the
  target unit (move) or target class (reclassify, or a part create) was **committed
  after the snapshot**, the re-read returns `None`.
  - The PUT then fails with `TypeError` in `_tracked_state(None)`: a 500, rolled
    back.
  - The create fails in `_path(None)`: a 500 too.
  - The report lists the unit case as "accepted race, untested". That acceptance
    is the coder's own; the brief accepts only the scrap deadlock. The class case is
    not mentioned.
- **(b) Stale event text.** If a target unit or class was **renamed** while the
  write waited for its lock, the event records the old code.
  - This needs an unreferenced unit or class (otherwise its code is frozen), so it
    is admin-only and rare.
  - Example: a `class` event saying `VBM → XX` when the class is now `YY`.
  - The brief names "a renamed class prefix" as the reason for BR3-01. The prefix
    used for the *code* is correct here; only the event text is stale.
- **(c) Inconsistency.** The target-parent case already has a guard (409 "The parent
  changed while saving; try again"). The unit and class cases do not, and its
  comment is misleading: "created during this very request" should read
  "committed by another request after this transaction's snapshot".

**Failure scenario.**
1. An admin creates unit `FWMILL2`.
2. Within milliseconds, a manager's PUT moving `VBM001` into it, already past its
   node read, takes the unit lock.
3. `_lock_target_unit` sees the unit (a locking read), the UPDATE succeeds, then
   `_read_node` → `None` → 500.
4. The user retries and it works.

**Suggested fix.** Take the smallest one that the user accepts:
1. One helper, for example `_reread(cur, node_id)`, that raises
   `ApiError("The record changed while saving; try again", 409)` on `None`. Use it
   at `:394`, `:425` and `:427`, and in `_load_target_node` (so the guard is not
   duplicated).
2. Take the `class` event's new value from the `_lock_class` row (it is already
   returned), so the event is never stale.

Or, as a design change for the user and planner rather than the coder, run
`equipment.py`'s write transactions at `READ COMMITTED`. Every plain read after a
lock then sees the latest committed rows. This removes (a), (b) and the guard
altogether. Either way, fix the guard's comment.

### CR1-02 — minor — Some list query values give a 500 instead of a 400

**Where:** `backend/equipment.py:300-307` (`_int_arg`).

**Problem.** Brief § 7 says that paging values outside the rules give "400 with
`field`". Two inputs escape this:
- **Non-ASCII digits.** `str.isdigit()` accepts characters such as `²`, which
  `int()` rejects. `GET /api/equipment?page=²` raises `ValueError` → 500.
  (Checked: `'²'.isdigit()` is `True`; `int('²')` raises `ValueError`.)
- **A huge page.** `page` has no upper bound. `?page=10000000000000000000000000`
  builds an `OFFSET` that MariaDB rejects with **1064** (checked read-only against
  the test DB) → a logged 500.
- The same `_int_arg` parses `site_id`, `unit_id` and `class_id`. Huge values there
  only match nothing, so they are harmless.

**Failure scenario.** A mistyped or crafted URL gives a 500 with a stack trace in
the log, instead of the documented 400 with `field: page`.

**Suggested fix.**
- Accept only `raw.isascii() and raw.isdigit()`, or `re.fullmatch(r"[0-9]+", raw)`.
- Give `page` a sane named maximum (e.g. `MAX_PAGE = 100_000`) or clamp it.
- Add the two cases to `test_bad_parameters_are_400`.

### CR1-03 — nit — `status=scrapped` without `include_scrapped=1` is a silent empty list, and no test pins it

**Where:** `backend/equipment.py:333-336`, `:349-350`; report, Decision 9.

**Problem.**
- The behaviour follows the brief's literal text: scrapped drops out unless
  `include_scrapped=1`. So it fits the brief.
- But the API accepts `status=scrapped` as a valid enum, and it can never match
  anything on its own. That is a trap for S003's status filter.
- No test covers the combination.

**Suggested fix.** Keep the behaviour, which is the brief's. Add a test for
`status=scrapped` → `[]` and `status=scrapped&include_scrapped=1` → the node, so
that a later change is deliberate. Note it in the S003 brief: the status filter
must send `include_scrapped=1` when it selects Scrapped.

### CR1-04 — nit — The order of the target checks is not pinned by tests

**Where:** `backend/tests/test_equipment_api.py` (`TestUnitAccess`).

**Problem.** The orders are implemented as stated, but no test asserts them:
- **BR3-02 for a target parent:** 403 (no access) comes before 409 (scrapped), so
  that a parent's scrapped state in another unit isn't revealed.
- **Decision 4 for a target unit:** 409 (inactive) comes before 403.

A refactor could swap either order unnoticed.

**Suggested fix.** Add two tests:
- An engineer of unit A creates a part under a **scrapped** equipment of unit B →
  `(403, "parent_id")`.
- The same engineer creates equipment in an **inactive** unit B → `(409, "unit_id")`.

## The coder's departures and choices

| Item | Judgement |
|---|---|
| `validate_equipment(..., stored=None)` | **Fits.** An update needs the stored level and code, and this keeps one body's validation in one pure call. The brief's signature didn't foresee the PUT immutables. |
| `_load_target_node(cur, node_id, child_level)` instead of `field` | **Fits.** The field is always `parent_id`; the level rule needs the child's level. |
| An extra `_can_access(cur, unit_id)` helper (and `_lock_target_unit` / `_lock_class`) | **Fits** the brief's intent: `_accessible_unit_ids` is still the only reader of `user_units`. It is called from `_can_access` and the list. The brief's "three helpers" didn't name the target-unit check, which needs one. |
| `insert_row` / `update_row` take `actor` | **Fits.** It keeps `db_helpers` free of request state, and behaviour is unchanged (`TestErrorMapping` is green with the renamed target). |
| `parse_name` / `optional_text_parser` made public | **Fits.** DRY over copying; `equipment_core` stays pure. |
| Target unit order 400 → 409 → 403 | **Fits.** The brief's create table lists "unit active … access to the unit" in that order, and a unit's state is public (the masters list). Test it (CR1-04). |
| A POST `code` is ignored | **Fits.** The code is shell-issued, and unknown body fields are ignored as in masters. It is tested. |
| `status=scrapped` filter needs `include_scrapped=1` | **Fits** the literal brief; see CR1-03. |
| 409 for a parent not visible in the snapshot | **Fits**, as a retry signal rather than a 500. Its comment is wrong, and the unit and class cases lack the same treatment (CR1-01). |
| Explicit `criticality: null` on POST equipment → 400 | **Fits** "required, default C". |
| `_inject_test_user` gated on `TESTING` | **Fits** BR3-04. |
| IST as a fixed `UTC+05:30` | **Fits.** IST has no DST; no `tzdata` is needed on Windows. |

Every departure from the brief's text is in "Decisions taken". I found nothing
built that the brief doesn't ask for.

## Checked and found consistent

- **Migration v4** (`local_db.py`):
  - The three tables, named UKs/FKs, and the CHECK `chk_equipment_level_place`
    exactly as § 5.
  - The index `ix_equipment_events_equipment (equipment_id, created_at)`.
  - `serial_counters` has no audit columns.
  - It is a new version; no applied migration was edited.
- **Counter:**
  - `INSERT … ON DUPLICATE KEY UPDATE`, then a `SELECT` read-back on the same
    connection inside the transaction. It is taken after the class lock, so creates
    are serialised per prefix.
  - Refusals come before the bump. The rollback after the bump is tested
    (`test_a_failure_after_the_counter_bump_rolls_it_back`, `test_refused_creates_use_no_number`).
  - `zfill(3)` is used.
- **`uq_equipment_code` 1062 → 409** "Code collision — retry" with no field. It is
  tested by forcing the counter back. App-level handlers are registered once in
  `app.py`, and the blueprint-level handlers are gone from `masters.py`.
- **Fragment:**
  - one module constant;
  - `COALESCE(gp.unit_id, p.unit_id, e.unit_id)` for the unit;
  - `root_criticality` is the brief's `CASE`;
  - the criticality filter uses the effective grade (tested, including the
    component-under-graded-component-unit case).
- **Tree:**
  - The level table is in the core.
  - The place rules are checked against the stored level on update.
  - A `null` for the absent place field is accepted and dropped.
  - Self-re-parenting is impossible by the level rule.
  - The CHECK holds when the shell is bypassed (`OperationalError` 4025, tested).
- **Status:**
  - The create statuses.
  - Any PUT on scrapped → 409 with no field (including `{}`).
  - Scrapping with live parts → 409 `status`, including a live grandchild under a
    scrapped child.
  - Scrapping plus a name change applies both.
  - Scrapped children are shown in the detail.
- **Events:**
  - Written in the same transaction, after the UPDATE; comparison in the core
    (`tracked_changes`).
  - `moved_unit` vs `moved_parent` by level, with one event on a cross-unit
    re-parent.
  - `inherit` is shown for a NULL own grade; no event on an inherited-grade change.
  - The order is `created_at DESC, id DESC`.
  - The forced-rollback test wraps the writer and calls through, as BR2-05
    requires.
- **Unit access:**
  - A 404 for nodes outside the user's units, including with a 400-worthy body and a
    non-object body.
  - A 403 with `field` for inaccessible targets (POST unit, POST parent, move,
    re-parent).
  - Filters intersect with access; a user with no rows gets an empty page without a
    query.
  - The username is compared lower-case.
  - The manager, IT admin and admin see all units.
  - Each test uses a fresh username via `X-Test-User`.
- **RBAC:**
  - `equipment:read` = `*`; `equipment:read_all_units` = manager and IT admin (a
    scope key, commented); `equipment:edit` unchanged.
  - The role matrix and the two exact-list auth tests are updated.
  - Every route is gated: GETs on `equipment:read`, POST/PUT on `equipment:edit`.
- **Security:**
  - The actor always comes from `g.user` (`api_common.actor`), never from the body.
  - No SQL is built from client input: f-strings interpolate only module constants
    and `%s` placeholder counts.
  - `q` escapes `\`, `%` and `_`.
- **DB availability:**
  - Every route reaches the DB only through `get_db()` (→ 503 `DBUnavailable`).
  - The pool pings on checkout (idle connections).
  - A transaction rolls back on any exception.
- **Masters:**
  - Any equipment, scrapped included, freezes a unit's code and site and a class's
    code.
  - Non-scrapped equipment (including `out_of_use`) blocks deactivating its unit
    (409 `active`).
  - All of these are tested, including a deactivated class staying frozen.
- **`conftest.py`:**
  - the truncate list in the brief's order, with `FOREIGN_KEY_CHECKS=0` on its own
    connection, restored in `finally`;
  - `role_client(role, username=None)`;
  - shared fixtures, including `make_equipment`.
- **Test coverage against brief § 9:**
  - every listed pure and API case is present, plus the § 9 acceptance scenario
    (the firewood mill, and a motor moved between breakers with both full paths).
  - The gaps are CR1-03 and CR1-04, and real concurrency, which no test exercises
    (the report says so; this review checked it by reading, above).
- **CLAUDE-COMMON:**
  - The core is pure (no DB, Flask or clock; `this_year` is passed in).
  - The shared shell code moved rather than being copied (DRY).
  - No exception is swallowed.
  - No deprecated APIs.
  - Comments explain *why*: the lock-order docstring and the CASE-vs-COALESCE note.

**Not for the coder; outside this review.** The planner still owes the doc edits of
brief § 4 Docs:
- Plan § 3, § 4.1 and § 5;
- Maintenance-Philosophy § 9.

`docs/Plan.MD` and `docs/Maintenance-Philosophy.md` are not in the diff.

## Manual check for the user

- **No browser check:** S002 has no UI. The screens come in S003.
- **Optional:** an API smoke run against the dev backend (`DEV_AUTH_BYPASS=1`):
  create an equipment, a component-unit and a component, then a re-parent, and look
  at `GET /api/equipment/<id>` events. It repeats what `TestAcceptance` already
  proves against the test DB.
