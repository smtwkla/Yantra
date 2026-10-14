```
Step: S002 — Equipment register
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 14-10-2026
```

# S002 — Brief review, round 3

Reviewed the revised `1-brief.md` (backend only) against `docs/Plan.MD` § 3, 4.1,
5, 9; `docs/Maintenance-Philosophy.md` § 7, 9, 12; `docs/Plant-Facts.md` § 2–3;
the S001 brief, impl report (CR1-01, CR2-01 decision) and code reviews;
`.claude/SMTW-WebApp-Base.md` (RBAC, DB connection, API responses, event-sourced
module, serial numbers, testing); `CLAUDE-COMMON.md`; `CLAUDE.md`; and the
current code: `masters.py`, `db_helpers.py`, `local_db.py`, `config_rbac.py`,
`auth_utils.py`, `app.py`, `conftest.py`, `test_masters_api.py`, `test_rbac.py`,
`test_auth.py`, `test_modules.py`, `tooling/dev/docker-compose.dev.yml`
(MariaDB 11.4).

**Verdict: one `major` finding is open** (BR3-01). It is a one-paragraph fix in
§ 6 Locking, not a redesign: the brief's REPEATABLE READ argument is right, but
the per-write table still lets a decision be made from a plain read taken after
an earlier plain read, which is the very trap BR2-02 closed for the scrap check.
Everything else is minor or a nit. The split (§ 10.1), the out-of-use question
(§ 10.2), bulk import (§ 10.3), the § 3 decisions and the accepted scrap-vs-re-parent
deadlock are not re-opened.

Severity: `blocker` / `major` / `minor` / `nit`. Findings are ordered by severity.

---

## Round 2 follow-up

Each `Accepted` finding was checked against the brief text, not the Review log:

| Finding | Where it now lives | Reflected? |
|---|---|---|
| BR2-01 lock order | § 6 Locking: global order node → target parent → unit → class → counter; single-row `FOR UPDATE`; never through the join; ancestors read plainly; `masters.py` table (unit → site; class; `user_units` → units); accepted deadlock named with an example | Yes — except the consequence BR2-01 asked to state (an edit by a user whose access lapsed during the lock wait finishes) is missing: BR3-04 |
| BR2-02 locking reads | § 6 "Locks first, then decisions"; the scrap check is a locking read of the subtree; masters' safety via `_lock_row` first | Yes as a rule — but the rule as worded is insufficient for the later locks in the table: BR3-01 |
| BR2-03 fragment | § 6 Resolving a node's unit: joins to `units` and `sites`; `root_criticality` as a `CASE`; filter on the effective grade; plain reads only | Yes (one nit on the reasoning: BR3-04) |
| BR2-04 truncate | § 4 Tests: `SET FOREIGN_KEY_CHECKS=0` on the truncate connection | Yes |
| BR2-05 test feasibility | § 9: event-writer wrapper; `OperationalError` 4025; fresh usernames via `role_client(role, username=…)` | Yes |
| BR2-06 unknown ids, immutable fields, validation order | § 6 Errors; § 6 Unit access check order | Yes |
| BR2-07 brand-new prefix | § 6 Codes: "the class row lock serialises creates per prefix" | Yes |
| BR2-08 ISO 55001 edition | § 2: "2014 numbering" | Yes |
| BR2-09 scrapped equipment in a deactivated unit | § 6 "Consequence of active units only" | Yes |

---

## Major

### BR3-01 — The deciding columns must come from the locking read itself; "a plain read made after the locks" is still stale when an earlier plain read fixed the snapshot — `major`

§ 6 Locking says (correctly): "The first plain read fixes the transaction's
snapshot. A plain read taken *before* a lock wait would hide rows committed while
the transaction waited." Then it says a check may be "a plain read made *after*
the locks". Those two sentences conflict for every write that takes more than one
lock, because the per-write table puts a plain read between the locks:

- `_load_node_for_user(…, for_update=True)` locks with
  **`SELECT id FROM equipment WHERE id = %s FOR UPDATE`** (only `id`), and "then
  reads the node through the fragment" — a plain read. That plain read is the
  transaction's first consistent read and **fixes the snapshot**.
- Every later lock in the same write — (2) target parent, (3) target unit,
  (4) target class — may then wait on a concurrent commit. After the wait, a
  plain read of the target's `status`, `level`, `active` or `code` shows the
  **pre-wait snapshot**, not what was just committed. InnoDB REPEATABLE READ:
  a locking read returns the latest committed row; it does not refresh the
  snapshot used by subsequent plain reads.

Concrete races the current wording lets the coder build:

| Write | Sequence | Result |
|---|---|---|
| Re-parent `X` → `T` | lock `X`; plain read `X` (snapshot S0); lock `T` — waits while *Scrap `T`* commits; plain read `T.status` → S0 → `in_service` | `X` live under scrapped `T`: the integrity error § 8 "nothing scrapped by accident" exists to prevent |
| Create part under `P`, class `C` | lock `P`; plain read `P` (S0); lock `C` — waits while `update_equipment_class` renames `VBM` → `VBX` and commits (its count saw no equipment); plain read of the prefix → S0 → `VBM` | `VBM001` under class `VBX`: BR1-02's prefix race, back again |
| Move equipment `E` → unit `U` | lock `E`; plain read `E` (S0); lock `U` — waits while `update_unit` deactivates `U`; plain read `U.active` → S0 → 1 | live equipment in an inactive unit, which § 4 says can't happen |
| Any PUT on `N` while *Scrap `N`* is in flight, if `_accessible_unit_ids` (a plain read of `user_units`) runs **before** the node lock | plain read (S0); lock `N` — waits for the scrap to commit; `N.status` via the fragment → S0 → `in_service` | the "any PUT on a scrapped node → 409" rule is bypassed for that one edit; a second scrap writes a duplicate `status` event |

Why it matters: the brief claims these races are closed ("no races on prefix,
scrap or deactivation", § 8), so the code reviewer would not look, and the
coder has been told explicitly to lock `SELECT id … FOR UPDATE` and read the rest
through the fragment. The windows are milliseconds, but the outcomes are permanent
(a wrong prefix is on the QR label for life).

Options:

- **(a) Recommended — every locking read returns the columns the decision
  needs, and every decision is made from that row.** Replace the "plain read made
  after the locks" clause with:
  - node and target parent: `SELECT id, level, status FROM equipment WHERE id = %s
    FOR UPDATE`;
  - target unit: `SELECT id, active FROM units WHERE id = %s FOR UPDATE`;
  - target class: `SELECT id, code, active FROM equipment_classes WHERE id = %s
    FOR UPDATE` (the prefix comes from **this** row);
  - the subtree check stays `SELECT id, status … FOR UPDATE` as written.

  The fragment is then used only for what it is good at — the root, the unit
  and site codes for access and `full_path`, and the display row — and its
  staleness is harmless (the access-lapse consequence BR2-01 already accepted).
  State the rule in one sentence: "A value that decides a refusal (`status`,
  `level`, `active`, the class `code`) is read from the locking `SELECT` that
  locks the row, never from a plain read." That rule is robust: it holds no
  matter what plain reads ran earlier, so the "next helper added before the lock"
  fragility BR2-02 warned about is gone.
- **(b) Keep single-column locks and guarantee no plain read precedes any lock
  wait.** Impossible as the table stands: the node must be loaded (a plain read
  for access) before the target is known to be lockable. Rejected.
- **(c) `READ COMMITTED`** for the session. Rejected in round 2; still a global
  change for a local problem.

One line also needed under `_load_node_for_user`: `_accessible_unit_ids` runs
**after** the node lock, so the lock is the transaction's first statement, as in
`masters.py`. (With option (a) this is belt-and-braces, but it keeps the S001
pattern recognisable.)

---

## Minor

### BR3-02 — `_load_node_for_user` gives 404, but a target parent outside the user's units must give 403 with a field, and an unknown one 400: say how the target is loaded — `minor`

§ 6 defines two helpers and says nothing else in `equipment.py` touches
`user_units`. `_load_node_for_user(cur, node_id, for_update)` returns **404** for
a node outside the user's units. But the targets rule says a POST or PUT whose
`parent_id` is outside the user's units gets **403** with field `parent_id`, and
§ 6 Errors says an unknown `parent_id` gets **400** with that field. The coder
cannot use `_load_node_for_user` for the target as written, and would have to
invent either a flag or a third helper that reads `user_units` — breaking the
"two helpers" rule.

Recommend naming it: `_load_target_node(cur, parent_id)` — the locking read of
BR3-01 (a) (`id, level, status`; no row → 400 `parent_id`), then the plain
fragment read for the target's root unit, checked against `_accessible_unit_ids`
→  403 `parent_id`; scrapped → 409 `parent_id`; level rule → 400 `parent_id`
(§ 9 says "wrong parent level → 400"). The same shape serves the unit and class
targets (`unit_id`: 400 unknown / 403 inaccessible / 409 inactive; `class_id`:
400 / 409 inactive). Amend the "two helpers" sentence to three, or say that
`_load_target_node` calls `_accessible_unit_ids` and is the only other caller.

Order of the three outcomes for one target: 400 (doesn't exist) → 403 (not
yours) → 409 (scrapped / inactive). § 6 Unit access already accepts that a
parent id's existence is a weak leak, so 400-before-403 is consistent.

### BR3-03 — Say where the generic shell helpers live, or the coder copies them — `minor`

`masters.py` has `_actor`, `_clean_body`, `_insert`, `_update`, `_count` and
`_fetch_one` — none masters-specific. The brief moves only the error code to
`api_errors.py`. `equipment.py` needs all six (the `_clean_body` shape with a
`(clean, errors)` validator; the audit-column `_insert`/`_update`). Left unsaid,
the coder either imports private `_` names across blueprints or copies ~40
lines, and CLAUDE-COMMON's DRY rule says neither.

Options:
- **(a) Recommended — promote them with the error move.** `insert_row`,
  `update_row`, `count`, `fetch_one` → `db_helpers.py` (they are cursor
  utilities); `actor()` and `clean_body(validator, creating)` → `api_errors.py`
  (both are request-shell utilities and `clean_body` raises `ApiError`).
  `masters.py` changes only its imports. `TestErrorMapping` monkeypatches
  `masters._insert`; after the move it patches `db_helpers.insert_row` (same
  five tests, one name change) — add that to the breaking-tests list in § 4.
- **(b) Leave them in `masters.py` and import them from `equipment.py`.**
  Works, but equipment then depends on masters for plumbing, and the `_`
  prefix becomes a lie. Rejected.

### BR3-04 — Small inaccuracies to correct in § 6 — `nit`

- **BR2-01's consequence is not stated.** Ancestors are read without a lock, so
  an equipment may be moved to another unit while a PUT on one of its parts is
  waiting; the user who had access at check time finishes the edit. The window
  is milliseconds and the edit is one that user was allowed to make a moment
  earlier. Accepted in round 2; write the two sentences.
- **`root_criticality` reasoning.** "`COALESCE(gp.criticality, p.criticality, …)`
  would wrongly skip to the component-unit's own grade" is true only when the
  equipment's grade is NULL, which the shell forbids. The `CASE` is still the
  right choice, for a better reason: if an equipment row ever has a NULL grade
  (the column allows it), `CASE` yields a NULL effective grade that shows the
  data error, whereas `COALESCE` would silently substitute the component-unit's.
  Reword, so the coder doesn't "fix" the CASE back to a COALESCE.
- **`create_unit` locks only the site** (`_lock_site_for_unit`); there is no unit
  row yet. The table row "`update_unit`, `create_unit` | the unit row, then the
  site row" should read `update_unit`: unit → site; `create_unit`: site. The
  conclusion (no cycle with equipment) is unchanged.
- **Empty subtree.** `WHERE parent_id IN (…)` with no ids is a syntax error; say
  the grandchildren read is skipped when there are no children (a component
  never has any).
- **`role_client(role, username=None)`** needs `_inject_test_user` in
  `conftest.py` to read a second header (say `X-Test-User`) and fall back to
  `test_<role>`. Implied; one clause makes it explicit.

---

## Checked and found consistent

- **The global lock order** node → target parent → unit → class → counter is
  acyclic across every row in the per-write table, including a PUT that changes
  `parent_id` and `class_id` together (1 → 2 → 4) or `unit_id` and `class_id`
  (1 → 3 → 4). Lower tree levels always precede higher ones; `level` is
  immutable and a parent is a strictly higher level, so no re-parent can create
  a cycle.
- **FK implicit locks don't add cycles.** An INSERT or UPDATE takes shared locks
  on the referenced parent, unit and class rows; every path already holds those
  rows `FOR UPDATE` before writing, so the shared lock is granted to itself. The
  `equipment_events` insert references the node, which is X-locked by the same
  transaction.
- **Masters interaction**, verified in `masters.py`: `update_unit` locks the unit
  (`_lock_row`, first statement) then the site (`_lock_site_for_unit`) on a site
  change or reactivation; `update_equipment_class` locks the class only;
  `replace_user_units` locks `user_units` rows then `units` rows
  (`_check_grantable`). `equipment.py` never locks `sites` or `user_units`, and
  masters never locks `equipment`, so no cycle spans the modules. Masters'
  counts are consistent reads taken after `_lock_row`, which is the first
  statement of those transactions, so their snapshot postdates the lock — the
  BR2-02 condition holds today. With the equipment create locking the unit and
  class rows before its INSERT, the counts in § 4 are safe.
- **The accepted deadlock** is exactly the one remaining reverse-order case.
  Checked the neighbours: scrap `N` vs create-part under `N`'s child (no cycle:
  the create never needs `N`); scrap `N` vs scrap of a child (no cycle); scrap
  `N` vs a re-parent **into** `N` from outside (no cycle: the scrap waits on the
  target child, then sees the live part and refuses). Only a re-parent *within*
  `N`'s subtree holds a grandchild the scrap wants while wanting a child the scrap
  holds. InnoDB reports 1213 → `OperationalError` → 500, which is the user's
  S001 CR2-01 decision; the cross-reference is now right.
- **The scrap subtree locking read** sees the latest committed children, and its
  next-key locks on `parent_id` also block a concurrent INSERT under those parents
  until commit. Combined with "a child is created or re-parented only by locking
  the target parent", nothing live can appear under a node after the check.
- **The fragment is for plain reads only** — right: MariaDB 11.4 has no
  `FOR UPDATE OF`, and `FOR UPDATE` on `e LEFT JOIN p LEFT JOIN gp` would lock
  the ancestors and reintroduce BR2-01's opposite-re-parent deadlock.
- **`root_criticality` CASE** gives the equipment's grade at every depth: `gp`
  when a component sits under a component-unit, `p` when a part sits directly
  under the equipment, `e` for the equipment itself. `COALESCE(e.criticality,
  root_criticality)` is the § 3.1 inheritance rule. The unit join
  `COALESCE(gp.unit_id, p.unit_id, e.unit_id)` is order-independent since only
  equipment has a unit. The `criticality` filter on the effective grade equals
  the own grade at the default `level=equipment`.
- **Counter**: IODKU then `SELECT last_value` on the same connection inside the
  transaction; creates of one class are serialised by the class lock taken
  earlier, so the first-insert duplicate-key deadlock cannot occur (BR2-07).
- **`conftest.py`**: `_clean_master_tables` uses a dedicated `get_local_db`
  connection, so `SET FOREIGN_KEY_CHECKS=0` there affects no pooled connection;
  the truncate list order is right; `test_modules.py` reads `LATEST_VERSION`
  dynamically so v4 doesn't break it.
- **Breaking tests** named correctly: `test_rbac.py::test_role_matrix` (every
  row gains `equipment:read`; manager and IT admin gain `read_all_units`;
  `test_every_role_gets_wildcard_permissions` passes unchanged) and the two
  `test_auth.py` tests asserting `permissions == ["masters:read"]`.
- **`api_errors.py` move**: `TestErrorMapping` patches `masters._insert` and
  `db_helpers.*`, not the handlers; an app-level handler that re-raises
  propagates in `TESTING` mode as a blueprint one does.
- **Check order and RBAC**: `require_perm` is a decorator (403 before any body
  parsing); `has_perm` returns True for admin, so `read_all_units` includes
  admin; `equipment:edit = ("maint_engineer", "it_admin")` with the manager via
  `ROLE_INCLUDES` matches Plan § 3.
- **Standards.** ISO 14224 levels 6–8 and the Annex A boundary idea; EN 13306
  up/down as condition and operating/standby/idle as use within up, with
  `out_of_use` correctly called a life-cycle status outside the standard;
  ISO 55000's "usual stages"; ISO 55001 (2014 numbering) § 6.1 and § 6.2.2
  (where a criticality ranking lives), § 7.5–7.6 (the controlled register),
  § 8.2 (management of change — the event log is the record); NORSOK Z-008
  scoped to "the idea, not the code lists"; TPM's planned-maintenance pillar
  ranking equipment A/B/C; ISO 27001:2022 A.5.15 and A.8.3 for the enforcing
  side of unit access. All correctly cited and explained.
- **Pure core / thin shell**: `validate_equipment` takes `this_year`; the other
  core functions take plain values; no `now()` or DB in the core.
- **Not over-engineered**: no stored path or unit on parts, no rotables, no
  standby relationship, no custom fields; `remark` deferred with a reason.
