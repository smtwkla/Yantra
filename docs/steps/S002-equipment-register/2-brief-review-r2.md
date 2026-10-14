```
Step: S002 — Equipment register
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 14-10-2026
```

# S002 — Brief review, round 2

Reviewed the revised `1-brief.md` (backend-only, screens in the *Handover to S003*
appendix) against `docs/Plan.MD` § 3, 4.1, 5, 9; `docs/Maintenance-Philosophy.md`
§ 7, 9, 12; `docs/Plant-Facts.md` § 2–3; the S001 brief, impl report and code
reviews; `.claude/SMTW-WebApp-Base.md` (RBAC, DB connection, API responses,
event-sourced module, serial numbers, testing); `CLAUDE-COMMON.md`; `CLAUDE.md`;
and the current code: `masters.py`, `masters_core.py`, `db_helpers.py`,
`local_db.py`, `config_rbac.py`, `auth_utils.py`, `app.py`, `conftest.py`,
`test_masters_api.py`, `test_rbac.py`, `test_auth.py`, `test_modules.py`,
`frontend/tests/navigation.test.js`, and `tooling/dev/docker-compose.dev.yml`
(MariaDB 11.4).

**Verdict: not yet approvable. Two `major` findings are open** (BR2-01, BR2-02),
both in § 6 Locking, which round 1 asked for and which is new text. Both are
small to fix: one global lock order, and locking reads where a read decides a
refusal. Everything else is minor or a nit. The split (BR1-04), the
out-of-use question and bulk import are the user's (§ 10) and are not raised.
The 14-10-2026 decisions (§ 3) are not re-opened.

Severity: `blocker` / `major` / `minor` / `nit`. Findings are ordered by severity.

---

## Round 1 follow-up

Each `Accepted` finding was checked against the brief text, not the Review log:

| Finding | Where it now lives | Reflected? |
|---|---|---|
| BR1-01 counter | § 6 Codes: one transaction, read-back on the same connection, no `LAST_INSERT_ID()`/`MAX`; § 9 test replaced ("uses no number") | Yes |
| BR1-02 locking | § 6 Locking: create and update order, prefix after the class lock, scrap check under the node lock, no-cycle sentence, comment required in `equipment.py` | Yes — but the order itself has a cycle (BR2-01) and the scrap read is not safe as written (BR2-02) |
| BR1-03 unit resolution | § 6 Resolving a node's unit: the fragment, `_accessible_unit_ids`, `_load_node_for_user`, POST/PUT target rule with 403, check order, filters intersect access, `level=all` | Yes |
| BR1-04 split | § 0 and § 10.1; appendix | Yes (pending the user) |
| BR1-05 router / redirect | Appendix: `router/index.js`, `landingPath` redirect, three tests named | Yes |
| BR1-06 events | § 6 Events: full paths on both moves, one `moved_parent` cross-unit, `inherit`, no event on inherited grade, display-value signature, `created_at DESC, id DESC`, "history log, not event-sourced" | Yes |
| BR1-07 status gaps | § 6 Status and Classes-and-units-as-targets tables, messages and fields, `criticality: null` rules | Yes |
| BR1-08 paging / filters | § 7 `GET /`: bounds, escaping, unknown enums → 400, `part_count`, `unit_id`/`class_id` in rows, children carry `status`; UI bullets moved to the appendix | Yes |
| BR1-09 `api_errors.py` | § 4: app-level `register_error_handlers(app)`, dict registry, `TestErrorMapping` as regression, `uq_equipment_code` message | Yes |
| BR1-10 frozen / activation | § 4 `masters.py`: scrapped counts, lock cross-reference, shared `make_equipment` fixture; out_of_use to the user | Yes |
| BR1-11 standards | § 2 rewritten | Yes (see BR2-08 for one nit) |
| BR1-12 `useMasterForm.js` | Appendix | Yes |
| BR1-13 RBAC | § 8 departure row; § 4 key order; breaking tests named | Yes |
| BR1-14 data model | § 5: CHECK named, FKs named; `remark` deferred § 10.6 | Yes |
| BR1-15 docs owed | § 4 Docs | Yes |
| BR1-16 tests | § 4 Tests and § 9: truncate order, relative codes, rollback method, `zfill(3)` | Yes — but the rollback method contradicts the step order (BR2-05) |

---

## Major

### BR2-01 — The lock order as written can deadlock: create locks the class first, a reclassify locks the node first; and `FOR UPDATE` on the join would lock ancestors — `major`

§ 6 Locking says: *create* locks **class → parent/unit → counter**; *update*
locks **node → target (unit, parent or class)**; and "Class first on create, then
node → parent → unit … so no cycle is possible". Two cycles exist:

1. **Create vs. reclassify.** Transaction A creates a part under equipment `E`
   with class `C`: locks `C`, then waits for `E` (the parent). Transaction B
   reclassifies `E` to class `C`: locks `E`, then waits for `C`. Deadlock (1213 →
   500). The same pair arises between a create and a single PUT that changes both
   `unit_id` and `class_id`, because the brief doesn't order the targets among
   themselves. Round 1 recommended "class first on create"; with reclassification
   locking the node first, that recommendation was wrong, and this finding
   corrects it.
2. **`FOR UPDATE` on the three-way join.** If `_load_node_for_user(…,
   for_update=True)` puts `FOR UPDATE` on the fragment's
   `e LEFT JOIN p LEFT JOIN gp`, InnoDB locks the rows read from **every** joined
   table; MariaDB has no `FOR UPDATE OF e`. A PUT on a component then also locks
   its component-unit and its equipment. Two re-parents in opposite directions
   deadlock: moving `C1` (under `E`) to `E2` locks `C1 → E → E2`; moving `C3`
   (under `E2`) to `E` locks `C3 → E2 → E`.
3. The sentence "`masters.py` locks only its own row and counts by plain reads" is
   inaccurate: `update_unit` and `create_unit` lock the **site**
   (`_lock_site_for_unit`), and `replace_user_units` locks `user_units` then
   **units** (`_check_grantable`). It is harmless, because `equipment.py` never
   locks `sites` or `user_units`, but the code reviewer should not have to
   discover it.

Why it matters: a deadlock is a 500 that the user retries, which is tolerable, but
the brief claims the order is cycle-free, so the code reviewer would not look. A
stated order that is actually wrong is worse than none.

Options:

- **(a) Recommended — one global order, every write follows it and skips the rows
  it doesn't need:**
  1. the **node's own row**, by `SELECT … FROM equipment WHERE id = %s FOR UPDATE`
     — never the join; the ancestors (root, unit) for the access check are
     reached by a **plain read** of the fragment afterwards;
  2. the **target parent** row (re-parent);
  3. the **unit** row (equipment create; move to a unit);
  4. the **class** row (create; reclassify) — the prefix is read after this lock,
     as now;
  5. the `serial_counters` row (create).

  So a create locks parent-or-unit → class → counter, and an update locks node →
  parent → unit → class. Lower levels still precede higher ones; the class moves to
  after the equipment and unit rows on both paths, and the counter is last. The
  masters module's orders (unit → site; class alone; `user_units` → units) cross
  none of these, because `equipment.py` never locks sites or `user_units`. State
  the five-step list and that sentence in § 6 and in the comment at the top of
  `equipment.py`. "All creates in one class queue up on the class row" stays
  true.
- **(b) Lock the class first on update as well** (before the node). Rejected: the
  node must be loaded first for the 404-before-anything order of § 6, and the
  class isn't known until the body is read, which the check order puts after the
  node load.

One consequence to state: with the node's ancestors read without a lock, an
equipment may be moved to another unit while a PUT on one of its parts is in
flight; the user who had access at check time finishes the edit. The window is
milliseconds and the result is a correct edit by someone who had access a moment
earlier — acceptable, say so.

### BR2-02 — "A plain read of the subtree is enough once the node is locked" is wrong under REPEATABLE READ when any consistent read came earlier in the transaction — `major`

InnoDB's default isolation (REPEATABLE READ, which the app doesn't change) gives
every *plain* `SELECT` in a transaction the snapshot taken at the transaction's
**first** plain read. A `SELECT … FOR UPDATE` is a locking read: it returns the
latest committed row but does **not** refresh that snapshot.

§ 6 says the PUT path first calls `_accessible_unit_ids(cur)` — a plain read of
`user_units` — then locks the node, then reads the subtree with a plain read. That
sequence fails:

1. Scrap-`E` request: `BEGIN`; plain read of `user_units` → snapshot at T0.
2. Create-part request: locks `E` (parent), inserts the part, commits at T2.
3. Scrap-`E`: `SELECT … WHERE id = E FOR UPDATE` waits until T2, then proceeds.
4. Scrap-`E`: plain `SELECT … WHERE parent_id = E AND status <> 'scrapped'` reads
   the **T0 snapshot** — the part committed at T2 is invisible.
5. `E` is scrapped with a live part under it: exactly the state the lock was meant
   to prevent, and a permanent integrity error.

The brief's reasoning ("anything that would add a live child must first lock this
node") is right about the *lock* and wrong about the *read*.

Why it matters: the scrap rule is the brief's own "nothing scrapped by accident"
decision (§ 8), and the same trap applies to every read whose result decides a
refusal.

Options:

- **(a) Recommended — make every decision-read a locking read.** The subtree
  check becomes `SELECT id FROM equipment WHERE parent_id IN (…) AND status <>
  'scrapped' FOR UPDATE` (two levels: direct children, then their children).
  Locking reads always see current data. State the rule in § 6 as: "A read whose
  result decides a refusal is a locking read (`FOR UPDATE`), never a plain
  `SELECT`, because a plain `SELECT` shows the snapshot of the transaction's first
  read, which may predate the lock." This is the one place a higher row is locked
  before lower ones; it is deadlock-free because, under BR2-01 (a), a write on a
  part never locks its ancestors.
- **(b) Guarantee the node lock is the first statement** of every write
  transaction (move `_accessible_unit_ids` after it). Works, but fragile: the
  next helper added before the lock silently reopens the bug.
- **(c) `READ COMMITTED`** for the session. A global change for one case; no.

Cross-reference for `masters.py`: its counts (`update_unit`, the new class
count) are safe today only because `_lock_row` is the **first** statement of the
transaction, so the count's snapshot is taken after the lock. § 4 "These counts are
safe only because the equipment create locks the unit and class rows" should add
that second condition, or the coder should make those counts locking reads too
(`SELECT COUNT(*) … FOR UPDATE` is fine at this scale).

---

## Minor

### BR2-03 — The fragment is incomplete for what the routes need from it: the units/sites join and the root's criticality, with the `COALESCE` order spelled out — `minor`

The fragment resolves root and unit ids. The list and detail also need the unit's
full code (`SMTW.FWMILL`), the site (for the `site_id` filter and the path), the
codes root-to-node, and the root's criticality. Left unsaid, the coder writes a
second join somewhere.

- Add to the fragment: `JOIN units u ON u.id = COALESCE(e.unit_id, p.unit_id,
  gp.unit_id) JOIN sites s ON s.id = u.site_id`, and the selected expressions
  `u.id AS unit_id`, `CONCAT(s.code, '.', u.code) AS unit`, `s.id AS site_id`,
  `gp.code, p.code, e.code` (for `full_path`), and **`COALESCE(gp.criticality,
  p.criticality, e.criticality) AS root_criticality`**. The order `gp, p, e`
  matters: a component under a graded component-unit must inherit the
  **equipment's** grade (§ 3.1 "inherit their equipment's grade"), not the
  component-unit's. Written `e, p, gp` it would be wrong. It works because the
  root is always the outermost non-NULL row and its grade is never NULL (shell
  rule).
- Then the shell calls the pure `effective_criticality(e.criticality,
  root_criticality)` and `full_path(...)` for both list rows and the detail — one
  computation, not SQL in the list and Python in the detail.
- Say which value the list's `criticality` filter matches: recommend the
  **effective** grade ("show every A-critical item" is the use), which is the same
  as the own grade at the default `level=equipment`.

### BR2-04 — `DELETE FROM equipment` in the session truncate will fail on the self-referential FK — `minor`

`conftest._clean_master_tables` runs `DELETE FROM {table}` per table. With
`fk_equipment_parent` → `equipment(id)`, InnoDB checks the constraint per row as it
deletes in primary-key order; a parent (lower id) is visited before its child and
the statement fails with 1451. The brief's new truncate list would break the
suite at the first session after any test creates a part.

Options:
- **(a) Recommended — `DELETE FROM equipment ORDER BY id DESC`.** A child is
  always created after its parent, and a move needs an existing parent, so a
  child's id is always higher than its parent's. One special case in the loop.
- **(b) `SET FOREIGN_KEY_CHECKS = 0` around the loop**, which the S001 brief
  already allowed (§ 8 Test-DB hygiene). Simpler, and also covers any future
  self-reference.

Either is fine; say which.

### BR2-05 — Three test descriptions are not feasible as written — `minor`

1. **The rollback test.** § 9 says "monkeypatch the UPDATE step to raise after the
   events are written", but § 6 Locking puts the UPDATE at step 4 and the events at
   step 5. Raising in the UPDATE means no event was written yet, and the test
   proves nothing. Say instead: wrap the event-writing helper (e.g.
   `_write_events`) so it calls the original and **then** raises; assert no event
   rows and the node unchanged. In `TESTING` mode the exception propagates, so the
   test uses `pytest.raises`, like `test_a_foreign_key_error_is_not_a_409`.
2. **The CHECK-constraint test.** MariaDB reports a CHECK violation as error 4025
   ("CONSTRAINT `chk_equipment_level_place` failed"). pymysql maps 4025 to
   `pymysql.err.OperationalError`, not `IntegrityError`. The test must assert
   `OperationalError` with `match="chk_equipment_level_place"`, or it fails for the
   wrong reason. (In production the shell never lets it happen, so a 500 there is
   correct; no mapping needed.)
3. **"A user with no rows → an empty list."** Role clients have fixed usernames
   (`test_maint_engineer`, …) and `user_units` rows persist for the whole session,
   so a test that grants the engineer a unit earlier makes a later "no rows" test
   order-dependent. Use a role no test ever grants (say `maint_technician`), or
   start the test with `PUT /api/masters/user-units/<name> {unit_ids: []}`.

### BR2-06 — Write-path answers the coder would otherwise choose alone — `minor`

- **Unknown target ids.** The targets table covers *inactive* and *scrapped*
  targets but not a `unit_id`, `parent_id` or `class_id` that doesn't exist.
  Masters returns 400 "Unknown site" with the field. Say: unknown target → **400**
  with the field, on POST and PUT. (A user can then tell "doesn't exist" from
  "not mine" (403); § 6 already accepts that a unit or parent id is a weak leak.)
- **Immutable fields in a PUT body.** `level` and `code` "can't be changed", but
  is a body containing them a 400 or silently ignored? `masters_core` ignores
  unknown keys (`created_by` in a body is dropped). Recommend **400 "level cannot
  be changed"** (field `level`; same for `code`): explicit over silent, and it
  catches a UI bug early. Likewise `unit_id` on a part or `parent_id` on
  equipment in a PUT → 400, as the brief already says for POST.
- **Where `_clean_body` runs.** To keep the § 6 order (404 before 400), the PUT
  must load the node *before* validating the body — the opposite of masters,
  where `_clean_body` is the first line. One sentence so the coder doesn't copy
  the masters shape. (A non-JSON body → 400 before the load is harmless: it
  doesn't depend on the id.)

---

## Nits

### BR2-07 — The "accepted rare case" can't happen, and the cross-reference is wrong — `nit`

§ 6 Codes keeps "Several creates racing on a brand-new prefix can hit InnoDB's
duplicate-key deadlock … accepted at this scale, like S001's CR2-01". With every
create locking the class row before it reaches the counter (both in the brief's
order and in BR2-01 (a)), creates in one class — and so on one `EQ:<class>` scope
— are serialised; two transactions never reach the counter's IODKU together, so
the duplicate-key deadlock can't arise. Replace the paragraph with that sentence.
Also, S001's CR2-01 was the warm-pool 503 finding; the deadlock remark the brief
means is the CR1-01 fix note in the S001 impl report.

### BR2-08 — ISO 55001 clause numbers: say which edition — `nit`

§ 2 cites ISO 55001 § 6.1, § 6.2.2, § 7.5–7.6 and § 8.2. ISO 55001:2024 has
replaced the 2014 edition; the harmonised-structure clause numbers are the same
for these four, but S001 § 2 said "clause numbers as in the 2014 edition" and S002
should say the same, so the two briefs read alike. The citations themselves are
right: § 6.1 (actions to address risks and opportunities — where the plant decides
which assets matter most), § 6.2.2 (planning for the asset management system —
the decision-making criteria, which is where a criticality ranking lives),
§ 7.5–7.6 (information requirements; documented information — the controlled
register), § 8.2 (management of change — assess and record changes to assets,
which the event log does).

### BR2-09 — State one consequence of "active unit ids only" — `nit`

`_accessible_unit_ids` returns the user's **active** units. A unit can be
deactivated only when all its equipment is scrapped (§ 4), so after that an
engineer with access to that unit can no longer open the scrapped equipment or
its history; only `read_all_units` holders can. That is consistent with S001
("S002's queries only see active units") and fine for a closed area, but write it
in § 6 so the code reviewer doesn't file it as a bug.

---

## Checked and found consistent

- **§ 3 decisions** are carried unchanged into § 5 and § 6: criticality required
  on equipment with default C and NULL-means-inherit on parts; four statuses with
  scrapped final; three fixed levels with components allowed under equipment;
  only equipment holds `unit_id`; an event table now.
- **The counter read-back.** After the IODKU on the same connection inside the
  transaction, `SELECT last_value … WHERE scope = %s` sees the transaction's own
  write (own changes are always visible to a consistent read) and the row stays
  X-locked until commit. Correct; no `LAST_INSERT_ID()` needed.
- **The CHECK constraint.** `level` is `NOT NULL`, and `IS NULL` / `IS NOT NULL`
  always yield 0 or 1, so the expression is never NULL (a NULL CHECK would pass
  silently). `=` binds tighter than `AND`, so it parses as intended. MariaDB
  enforces CHECK constraints since 10.2; the dev compose pins `mariadb:11.4`.
  `code VARCHAR(12)` holds a 4-letter prefix plus 5 digits; `scope VARCHAR(40)`
  holds `EQ:XXXX` and later `BD:…`.
- **No tree cycles are possible.** A part's parent must be a strictly higher
  level and `level` is immutable, so a node can never become its own ancestor;
  `check_parent` is the whole rule.
- **Check order.** `require_perm` is a decorator, so the 403 precedes any body
  parsing; `has_perm` returns True for admin, so `read_all_units` includes admin
  as stated.
- **`api_errors.py` move.** `TestErrorMapping` monkeypatches `masters._insert`
  and `db_helpers.*`, not the handlers; a `raise` inside an app-level error
  handler propagates in `TESTING` mode exactly as it does from a blueprint
  handler, so the five tests are valid regression tests for the move.
- **Breaking tests** are named correctly: `test_rbac.py::test_role_matrix` (every
  row gains `equipment:read`; manager and IT admin also `equipment:read_all_units`)
  and the two `test_auth.py` tests asserting `permissions == ["masters:read"]`.
  `test_modules.py::test_test_db_is_reachable_and_migrated` reads
  `LATEST_VERSION` dynamically, so migration v4 doesn't break it.
  `navigation.test.js` uses its own permission constants and no nav item changes
  in S002, so the frontend suite stays green until S003.
- **`masters.py` changes** match the code: `update_equipment_class` has no in-use
  check today (comment says S002 adds it); `update_unit` counts only `user_units`;
  both lock their row first; the unit deactivation count needs only
  equipment-level rows, because parts of scrapped equipment are already scrapped.
- **RBAC**: `equipment:read = ("*",)` and `equipment:edit` match Plan § 3;
  `read_all_units` is recorded as a scope-key departure in § 8; order to match
  the nav as `config_rbac.py`'s own rule says.
- **Standards.** EN 13306's split is now right: *up* vs *down* is the condition;
  *operating / standby / idle* are the use states within *up*; `out_of_use` is
  correctly called a life-cycle status with no EN 13306 term. ISO 14224 levels
  6–8 and the boundary idea (Annex A boundary diagrams: utilities feeding a unit
  are outside it, so the compressors are their own equipment) are right. The
  criticality lineage — TPM's planned-maintenance pillar (rank equipment A/B/C
  so PM effort goes where it matters), ISO 55001 § 6.1/§ 6.2.2, and NORSOK
  Z-008's consequence classes with redundancy lowering the class — is correctly
  scoped as "the idea, not the code lists". ISO 27001:2022 A.5.15 (access
  control) and A.8.3 (information access restriction) are the right controls for
  the enforcing side. ISO 55000's stages are given as "the usual stages", as
  asked.
- **Pure core / thin shell:** `validate_equipment` takes `this_year`; `full_path`,
  `tracked_changes` and `check_status_change` take plain values; no `now()` or DB
  in the core.
- **Pagination** is a stated return to the base shape with the reason (about 500
  equipment plus parts). **No DELETE**; scrapped instead.
- **Acceptance scenario** (`VBM001` with a drive, motor and gearbox; two breakers
  each with a motor; moving a motor between breakers) matches Plant-Facts § 2
  `SMTW.FWMILL` and exercises create at each level, re-parent and the event
  snapshot.
- **Not over-engineered:** no stored path or unit on parts, no rotables, no
  standby relationship, no custom fields, `remark` deferred with a reason.
