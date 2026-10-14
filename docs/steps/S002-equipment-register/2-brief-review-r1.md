```
Step: S002 — Equipment register
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 14-10-2026
```

# S002 — Brief review, round 1

Reviewed `1-brief.md` against `docs/Plan.MD` (§ 1, 3, 4.1, 5, 9), `docs/Maintenance-Philosophy.md`
(§ 2, 7, 9, 12), `docs/Plant-Facts.md` § 2–3, the S001 brief (with A1), impl report and code
reviews, `.claude/SMTW-WebApp-Base.md` (DB connection, migrations, API responses, serial numbers,
event-sourced modules, testing, table/list and form patterns), `CLAUDE-COMMON.md`, `CLAUDE.md`,
and the S001 code in the working tree (`masters.py`, `masters_core.py`, `db_helpers.py`,
`local_db.py`, `config_rbac.py`, `auth_utils.py`, `app.py`, `conftest.py`, `test_masters_api.py`,
`test_rbac.py`, `test_auth.py`, `router/index.js`, `App.vue`, `stores/navigation.js`,
`stores/masters.js`, `useMasterForm.js`, `FormModal.vue`, `UnitsPanel.vue`, `navigation.test.js`).

**Verdict: not yet approvable. Four `major` findings are open** (BR1-01 to BR1-04); the rest are
minor or nits. The decisions of 14-10-2026 (criticality A/B/C with default C and inheritance;
four statuses with scrapped final; fixed three levels with components allowed under equipment;
only equipment holds a unit; an event table now) are all carried into § 3, § 5 and § 6 correctly
and are not questioned here. The brief's claims about the S001 code are accurate except one
(the `/` redirect, BR1-05). The design is sound in outline; what is missing is mostly the
concurrency and unit-resolution detail that the coder would otherwise decide alone, and a
contradiction in the counter rule.

Severity: `blocker` / `major` / `minor` / `nit`. Findings are ordered by severity.

---

## Major

### BR1-01 — The counter rule contradicts itself: "same transaction" and "a number is never reused on rollback" cannot both hold — `major`

§ 6 Codes says three things:

1. the counter update "runs in the same `transaction()` as the INSERT";
2. "A number is **never reused**, even if the INSERT then fails and the transaction rolls back.
   A rolled-back number is simply skipped, as with base serials";
3. § 9 tests: "A failed create still uses up its number: the next create gets the next number."

(1) and (2) are incompatible. If the `INSERT … ON DUPLICATE KEY UPDATE` on `serial_counters`
is inside the transaction and the transaction rolls back, the counter bump rolls back too, and
the next create gets the **same** number. Test (3) would then fail against a correct
implementation of (1). The coder has to pick one, and whichever they pick, the brief or the
test is wrong.

The "as with base serials" claim is also inaccurate: the base pattern (§ Serial Number
Generation) runs `SELECT … FOR UPDATE; UPDATE; insert rows` **in one transaction**, so a
rollback there also returns the number. Its "never reuse a serial" rule is about *voiding a
committed entity*, not about a rolled-back transaction.

Why it matters: the code is the permanent identity on the QR label. The rule must be exact,
and the test must match the rule.

Options:

- **(a) Recommended — counter inside the transaction; a rolled-back create returns its
  number.** Simplest, atomic, and the base pattern. Gaps then arise only from scrapping
  (never from failures). State it as: "the counter bump and the INSERT are one transaction; a
  create that fails after the bump rolls the bump back, so no gap is left". Replace test (3)
  with: "a create refused by validation (400) or by a rule (409) consumes no number; the next
  successful create gets the next number". The only failures that can happen after the bump are
  a DB error or an impossible 1062, and both roll everything back — which is the right outcome.
- **(b) Never reuse, even on rollback.** Bump the counter in its own autocommit statement
  *before* the transaction, using
  `INSERT … ON DUPLICATE KEY UPDATE last_value = LAST_INSERT_ID(last_value + 1)` followed by
  `SELECT LAST_INSERT_ID()` (connection-scoped, so a concurrent bump can't be read back by
  mistake; a plain `SELECT last_value` after an autocommit IODKU *is* a race). More moving
  parts for no benefit; only pick this if gap-free numbering is explicitly unwanted.

Two smaller points to settle in the same paragraph:

- **Read-back.** With (a), after the IODKU the shell reads `SELECT last_value FROM
  serial_counters WHERE scope = %s` on the same connection; inside the transaction it sees its
  own write and the row is X-locked until commit. Say so, so the coder doesn't reach for
  `LAST_INSERT_ID()` or `MAX(code)`.
- **First number of a new scope.** The IODKU inserts `(scope, 1)` when the row is missing.
  Three creates racing on a *brand-new* prefix can hit InnoDB's duplicate-key shared-lock
  deadlock if the first one rolls back. That is rare enough at this scale to accept, but say
  "accepted" rather than leave it undiscovered in code review (S001 CR2-01 was the same kind of
  thing).

### BR1-02 — Row locking for create, move and scrap is not specified: which rows, in which order, and what is checked under the lock — `major`

§ 6 gives the counter lock and nothing else. S001's brief spelled out "lock the parent row with
`SELECT … FOR UPDATE` before references are counted", and S001's code review still found a
real isolation gap (CR1-01). S002 has more check-then-write paths than S001, and each is a
race if the check runs on an unlocked row:

| Path | Check | Race if unlocked |
|---|---|---|
| POST equipment | unit exists and is active; class exists and is active; **class code read for the prefix** | `update_equipment_class` changes `VBM`→`VBX` (its count sees 0 equipment, commits) while the create has already read `VBM` → equipment `VBM001` under class `VBX`. The class's X lock from `_lock_row` blocks the INSERT's FK share lock, but **not** a plain read of the prefix that happened earlier. |
| POST part | parent exists, is not scrapped, level rule; parent's root for unit access | `PUT parent {status: scrapped}` commits between the check and the INSERT → a live part is created under a scrapped node. The scrap's check of children (consistent read) does not see the uncommitted part either. |
| PUT move (`parent_id`) | target exists, not scrapped, level rule, unit access | same as above |
| PUT move (`unit_id`) | target unit active, unit access | `update_unit {active: 0}` races the same way (its count sees no equipment yet). |
| PUT `{status: scrapped}` | every child is scrapped | a concurrent create or move **into** this node must wait on the node's lock, else a live child appears under a scrapped parent. |
| `masters.update_unit` / `update_equipment_class` | count equipment under the locked row | fine *only if* the equipment create takes the unit/class row lock (FK share lock on INSERT is enough for the count, but not for the prefix read above). |

Why it matters: a wrong prefix or a live part under a scrapped node is a permanent identity /
integrity error, not a transient one. The fixed three-level tree removes any cycle risk (a
parent is always a strictly higher level, and `level` is immutable), so the only question is
the lock order.

Recommendation — add a "Locking" paragraph to § 6 with this order, and have the coder put it in
a comment at the top of `equipment.py`:

- **Create:** in one `transaction()`: (1) `SELECT … FOR UPDATE` the **class** row (exists,
  active; read the prefix *after* the lock); (2) `FOR UPDATE` the **unit** row (equipment:
  exists, active) or the **parent** row (parts: exists, not scrapped, level rule; its root
  equipment and unit are reached by plain reads for the access check); (3) the counter IODKU;
  (4) INSERT; (5) the `created` event.
- **Update / move / status:** (1) `FOR UPDATE` the **node** itself (exists, access → else 404;
  not scrapped → else 409); (2) `FOR UPDATE` the **target** unit or parent, when changing;
  (3) for `status: scrapped`, a consistent read of the children is enough once the node is
  locked, because anything that would add a live child must first lock this node; (4) UPDATE;
  (5) events.
- The order is "lower level before higher level" (node → parent → unit; class first on
  create). With `masters.py` locking only its own row and counting by consistent reads, there
  is no lock cycle between the two modules. Say this in one sentence so the code reviewer can
  check it instead of re-deriving it.
- `FOR UPDATE` everywhere, as in S001, is simpler than mixing in `LOCK IN SHARE MODE`; the
  serialisation it causes (all creates in one class queue up) is harmless at ~50 users.

### BR1-03 — A part's unit is not on its row; the brief must define the one place that resolves it, because every route depends on it — `major`

By decision, `unit_id` is set only on equipment. But the brief then uses "the equipment's
unit" in eight places without saying how it is found: the list filter for unit access, the
`site_id` / `unit_id` list filters, `GET /<id>` access, the PUT access check, the move
target's access check, `full_path`, `effective_criticality`, and `part_count`. With a fixed
tree this is a bounded two-step join (component → component-unit or equipment → equipment),
but the coder has to invent it, and if it is written four times it will drift (S001's DRY
rule, and the access rule is security).

Specific gaps:

- **List rows for parts.** `unit`, `full_path` and `effective_criticality` all need the root
  equipment. Define one SQL fragment — e.g. a `LEFT JOIN equipment p ON p.id = e.parent_id
  LEFT JOIN equipment gp ON gp.id = p.parent_id`, with the root being
  `COALESCE(gp.id, p.id, e.id)` and the unit `COALESCE(e.unit_id, p.unit_id, gp.unit_id)`
  — and say that the list, the detail, and the access check all use it.
- **The access check itself.** Name one helper, e.g. `_accessible_unit_ids(cur)` returning
  `None` for `read_all_units` holders (admin included via `has_perm`) or the user's **active**
  unit ids, and `_load_node_for_user(cur, id, for_update)` that applies it and raises 404.
  Every route goes through these two; nothing else touches `user_units`.
- **Target checks on writes.** The brief gives 403 for a move target outside the user's units
  but says nothing for a **POST** whose `unit_id` or `parent_id` is outside them. State that
  POST and PUT use the same rule (403 with `field`). Note the 403-vs-404 asymmetry is
  acceptable because `GET /api/masters/units` already lists every unit to every role, so a
  unit's existence is not a secret; a parent id is a weak leak at most. Say that, rather than
  leave it looking like an oversight.
- **Order of checks** on a PUT: permission (403 from `require_perm`) → load with access (404)
  → scrapped (409) → validation (400) → rules. Otherwise a 400 on a node the user may not see
  reveals it exists. One line in § 6.
- **Filters that intersect access.** `unit_id=<a unit the user may not access>` returns an
  empty page, not 403; `site_id` filters through `units.site_id`. One line.
- **`level` filter and search.** Default `equipment` means a search for `MOT017` finds nothing
  unless the user also switches level. Either accept `level=all` (and say the UI's Level
  dropdown offers it) or make `q` search all levels. Recommend `level` ∈
  `equipment | component_unit | component | all`, default `equipment`, and the UI defaults to
  `all` when `q` is typed.

### BR1-04 — The step is too large for one review sitting; split the screens off — `major`

README: "One step is one reviewable slice … A step too big to review in one sitting is split
into two steps." Counting the independent pieces: backend — counter, code format, tree rule,
re-parent, move-unit, criticality inheritance, status machine with the scrap rule, events,
unit-access enforcement on every route, pagination with seven filters, the `api_errors.py`
refactor, the two `masters.py` rule changes, two RBAC keys (12); frontend — nav + router +
landing, list with filters and paging, detail with path, tree and history, create/edit modal,
move modal, status modal (6); plus six test files. S001 (four flat masters) took two code-review
rounds; this is roughly twice S001 in rules and the same again in UI.

Options:

- **(a) Recommended — split the frontend into its own step.** S002 = migration, core,
  blueprint, unit access, `api_errors.py`, `masters.py` changes, RBAC keys, backend tests. A
  new step (say S003 "Equipment register — screens"; documents/QR and bulk import move down one
  number) = nav, router, the two views, the three modals, the navigation tests, the manual
  check. The backend step is fully reviewable through its API tests; the frontend step is
  reviewable against a working API. The README's rule is satisfied and nothing is redesigned.
- **(b) Keep one step**, with the code review explicitly done in two sittings (backend diff
  first, frontend second). Weaker, because one impl report then covers both and fix rounds
  interleave.
- **(c) Split by feature** (register + codes + access first; moves + events + status later).
  Rejected: `created` events, the scrap rule and the frozen-code count all touch the same
  routes, so the second step would reopen the first's code.

This is the user's call (the README leaves the split to the step owner); the planner may
reject with reasons. If (a) is taken, the frontend findings below (BR1-05, BR1-12) move with
the screens.

---

## Minor

### BR1-05 — `router/index.js` is missing from Where, and the "`/` redirects to the first visible item" claim is wrong — `minor`

`frontend/src/router/index.js` line 8 is `{ path: "/", redirect: "/masters" }` — a fixed
redirect. `landingPath()` is used only by the `beforeEach` guard and by `App.vue`'s watcher,
and only when the user **cannot** open the requested route. So adding an Equipment nav item
does not change where `/` goes. The coder must: add routes `/equipment` (name `equipment`) and
`/equipment/:id` (outside the nav, so `canOpenRoute` lets it through and the API's 404 does
the gating); and change the `/` redirect — either to `/equipment` or, better, to
`redirect: () => landingPath(userPermissions.value) ?? "/equipment"` so the landing rule lives
in one place. Add the file to § 4 and correct the sentence in Frontend. Also list
`navigation.test.js`'s three breaking tests by name (BR1-16).

### BR1-06 — Event snapshots: define the text form of each value and the one-vs-two-events rule for a cross-unit re-parent — `minor`

§ 5 gives examples but not rules, and `tracked_changes(before, after)` is pure, so the shell
must hand it display values. Decide and write down:

- `moved_unit`: old → new as unit full codes (`SMTW.FWMILL` → `SSVT.SHOP`), or as the
  equipment's full path before and after. Recommend **full paths** for both move events, so a
  reader sees the whole "where" without cross-referencing, and the ISO 14224 "where was it"
  question is answered by the event alone.
- `moved_parent`: the example `VBM001.DRV002` → `CNV004` is the parent's code path below the
  unit. A component-unit moved to an equipment at **another unit** changes both parent and
  unit — is that one `moved_parent` event or `moved_parent` + `moved_unit`? Recommend **one
  `moved_parent`** with full paths (`SMTW.FWMILL.VBM001.DRV002.MOT017` →
  `SSVT.SHOP.CNV004.MOT017`); the unit change is then visible in the text, and "unit" as a
  tracked field applies to equipment only.
- `criticality`: a NULL (inherit) side shown as `inherit`, e.g. `inherit` → `A`. A part whose
  *effective* grade changes because its equipment was regraded gets **no** event (its own
  value didn't change). Say so.
- `class`: class codes (`VBM` → `HP`).
- `status`: the enum values as stored, or labels? Recommend stored values; the UI labels them.
- `created`: `old_value` NULL, `new_value` = full path (as stated). ✓
- `tracked_changes` signature: takes two dicts of **display values** keyed by the five tracked
  names, returns `[(event, old, new)]`; the shell resolves names before and after the UPDATE.
  Then the pure test is trivial and the shell has no comparison logic.
- "Newest first" needs `ORDER BY created_at DESC, id DESC`: a PUT that changes status and class
  writes two rows with the same second.
- State plainly that `equipment_events` is a **history log**, not event-sourced state (the
  base § Event-Sourced Module Pattern replays events to derive state; here `equipment.status`
  stays the truth). That is the right choice at this size; just say it so the code reviewer
  doesn't ask for a projection.

### BR1-07 — Status-rule gaps the coder would decide alone — `minor`

- **`status` on POST.** Accepted? Recommend: accepted for `in_service`, `standby`,
  `out_of_use`; `scrapped` on create → 400 ("Create it, then scrap it" is pointless; a node is
  never born scrapped).
- **Moving into a scrapped parent** → 409. "No new parts under it" covers create; say it covers
  re-parenting too.
- **Any PUT on a scrapped node** → 409, even with no changed fields (simpler than diffing).
  Exception: none; a scrapped node's name is frozen too, which is what "read-only" means.
- **Scrapping with other changes in the same PUT** (`{status: scrapped, name: …}`): applied
  together, then read-only. Say so.
- **Reclassification to an inactive class** → 409 (field `class_id`), and a move to an inactive
  unit → 409 (field `unit_id`). § 6 "can't be chosen for new equipment, or as a move target"
  leaves reclassification open.
- **Messages and fields** for the new 409s, so the modal can show them beside a field:
  scrapped node → "This record is scrapped and cannot be changed" (no field); live parts →
  "Scrap or move its parts first" (field `status`); inactive target → field `unit_id` /
  `class_id` / `parent_id`. S001's impl report had to invent six of these; give them up front.
- **Equipment `criticality: null` on PUT** → 400 (required); on a part it means "inherit
  again". The masters_core pattern passes `None` through as a value, so this falls out
  naturally, but say it.

### BR1-08 — Pagination and filter details — `minor`

- `page` (≥ 1, default 1) and `per_page` (1–200, default 50); anything else → 400 with
  `field`. A page past the end returns `items: []` with the true `total`.
- `q`: `LIKE %q%` on `code` and `name`, with `%` and `_` escaped, trimmed, empty ignored.
- `status`, `criticality`, `level`: unknown values → 400, not silently ignored.
- `part_count`: define it — recommend **direct children that are not scrapped** (what the list
  needs to show "has parts"), with the subtree visible on the detail page.
- `unit` in list rows: the unit's full code (`SMTW.FWMILL`); add `unit_id` and `class_id` too,
  so the edit modal doesn't need a second fetch.
- `include_scrapped` applies to the list only; `GET /<id>` always returns scrapped children
  (stated) — fine, but say the children carry `status` so the UI can grey them.
- The base's "applying a filter resets to page 1" and "show total" belong in the Frontend
  bullet.

### BR1-09 — Shape of `api_errors.py` and its registry — `minor`

Verified: `ApiError`, `_error_response`, both `@masters_bp.errorhandler`s and
`_UNIQUE_KEY_ERRORS` are in `masters.py` lines 26–89. The brief says "move to a shared module"
but not how the handlers get registered, which decides the tests:

- Recommend **app-level** handlers: `api_errors.py` exports `ApiError`, `UNIQUE_KEY_ERRORS`
  (a dict), and `register_error_handlers(app)`; `app.py` calls it once. Each module adds its
  keys at import (`UNIQUE_KEY_ERRORS.update({...})`). Blueprint-level registration on two
  blueprints would mean two decorators calling one function — workable but pointless.
- `TestErrorMapping` monkeypatches `masters._insert` and `db_helpers.*`, not the handlers, so
  it survives either choice as long as the behaviour is unchanged; the "1062 on `PRIMARY` → generic
  409 without `field`" and "1452 re-raised" cases must still hold. Say they are the regression
  tests for the move.
- The `uq_equipment_code` entry: "Code collision — retry", no `field` (the user didn't type the
  code).

### BR1-10 — Frozen-code and activation rules in `masters.py`: precision and the lock they rely on — `minor`

- "A unit with equipment" / "a class with equipment": state **any** equipment, scrapped
  included, counts as a reference (as S001 did for inactive units; § 10.4 says it for inactive
  classes but not for scrapped equipment). Scrapped `VBM001` still carries the prefix and still
  appears in history snapshots.
- Deactivation: "not scrapped" is right, but note the consequence for the user: a unit whose
  equipment is `out_of_use` (laid up) cannot be closed; the equipment must be moved or
  scrapped first. If that is the intent, fine — put it in § 8 as a decision. (Alternative: treat
  `out_of_use` and `scrapped` both as "not live" for this rule.)
- The counts run under the unit's / class's existing `_lock_row`; they are only safe because
  the equipment create locks those rows (BR1-02). Cross-reference the two.
- `test_masters_api.py::TestUnitCodeFreeze` and `TestActivationRules` gain cases that need an
  equipment fixture; say the equipment-API test module exports a `make_equipment` fixture, or
  the masters tests get one via `conftest.py`, so the two files don't each build one.

### BR1-11 — Standards: three citations need tightening, three are missing — `minor`

What is right: the ISO 14224 level numbers (6 equipment unit, 7 subunit, 8 maintainable
item) match the standard's nine-level taxonomy; the boundary idea is ISO 14224's (each
equipment class in its Annex A has a boundary diagram saying what is inside the unit for
failure recording — utilities feeding it, such as the compressors feeding the extruder, are
outside, so they are their own equipment, exactly as § 2 says); ISO 55001 § 7.5–7.6 is the
same clause pair S001 settled on; "nothing hard-deleted" is the controlled-register rule.

To tighten:

- **EN 13306 states.** § 2 lists "disabled" among the *use* states. In EN 13306 the **up
  state** has the sub-states *operating*, *standby* and *idle*; *down* and *disabled* are
  the family of states where the item cannot perform its function (fault, or maintenance).
  So the split is: condition = up/down; use (within up) = operating/standby/idle. Yantra's
  `in_service` ≈ up (operating or idle), `standby` = EN 13306 standby, `out_of_use` has no EN
  13306 term (it is a life-cycle status: withdrawn, not maintained), `scrapped` is ISO 55000's
  end of life. Reword the two bullets that way; the conclusion ("down is derived from
  breakdowns, never typed") stands.
- **"ISO 14224 lets a maintainable item sit directly under the equipment unit."** The
  standard says the taxonomy levels used depend on the equipment and that lower levels may be
  omitted where they add nothing; it doesn't grant a specific permission. Say "ISO 14224's
  levels are applied as far as they are meaningful; a simple machine with no real subunit has
  its maintainable items directly under the equipment unit".
- **Criticality.** "After ISO 55001's risk-based planning" is loose; ISO 55001 § 6.1 (risks
  and opportunities) and § 6.2.2 (planning: decision-making criteria, which is where
  criticality lives) are the clauses. NORSOK Z-008 is "Risk based maintenance and consequence
  classification", an oil-and-gas standard that classifies the *consequence* of failure
  (High/Medium/Low across safety, environment and production, with redundancy lowering the
  class); A/B/C with "no standby / has standby" is that scheme in plain words — say "adopted
  for the idea, not its code lists", as Maintenance-Philosophy does for ISO 14224. And add
  **TPM**: the planned-maintenance pillar's first step is to *evaluate and rank equipment*
  (A/B/C by production, quality, safety and maintenance factors) so PM effort goes where it
  matters — that is where plant people will have met A/B/C, and the project is TPM-based.

Missing:

- **ISO 55001 § 8.2 (management of change)**: changes to assets that affect objectives are to
  be assessed and recorded. Moves, reclassification and scrapping are such changes; the event
  log is their record. Cite it beside § 7.5–7.6.
- **ISO 27001:2022 A.5.15 (access control) and A.8.3 (information access restriction)**: this
  is the step where unit access is *enforced*, and the 404-for-hidden-nodes rule is an access
  restriction decision. S001 cited A.5.15/A.5.18 for granting; S002 should cite the enforcing
  side.
- **ISO 55000 life cycle**: ISO 55000 doesn't fix four named stages; say "the usual stages
  (acquire, operate and maintain, dispose)". Small, but the owner is learning the vocabulary.

### BR1-12 — `useMasterForm.js` is masters-specific; say how the equipment modals reuse it — `minor`

Verified: `useMasterForm` calls `resetMasters()` after every save, exposes `changeActive`
(a `PUT {active}` that equipment has no use for), labels the deactivate confirm from
`record.full_code ?? record.code`, and lives in `views/masters/`. It can serve the
create/edit, move and status modals as three instances with partial forms (`fromRecord` →
`{unit_id}` or `{parent_id}`; `{status}`), since `save()` is just `apiPut(path/id, form)`. But
"reuse" as written leaves the coder to decide whether to (a) generalise it — move to
`composables/useFormModal.js`, make the after-save hook a parameter, drop `changeActive` into
the masters wrapper — or (b) copy it. Recommend (a), with the masters panels untouched except
the import path, and say so; otherwise S001's "DRY" reason for the composable is undone by its
first reuse. The Scrapped confirmation can reuse `ActiveToggle.vue`'s inline Yes/No shape
(rename or parametrise the label), not a browser `confirm()` (S001 A1.2).

### BR1-13 — Two small RBAC points — `minor`

- `equipment:read_all_units` is a **scope** key, not a sensitivity level; the base's read
  hierarchy is `read_basic / read / read_senior`. It is the right tool here (a role rule
  expressed as a permission), but § 8 should record it as a deliberate departure from the
  three-level naming, as S001 did for pagination.
- Order the new keys in `config_rbac.py` to match the new nav order (Equipment before Masters
  — the file's own rule), and note that `test_rbac.py::TestComputePermissions::test_role_matrix`
  (every row) and `test_auth.py::test_storekeeper_client_role_accepted` /
  `test_realm_role_maps_to_user` (which assert `permissions == ["masters:read"]` exactly)
  break. The brief lists the files; listing the tests saves the coder a run.

---

## Nits

### BR1-14 — Data-model nits — `nit`

- `serial_counters.last_value INT NOT NULL` — no default is right (the IODKU always supplies
  it). Add `created_at`? No: it is a counter, not a record. Fine as is.
- Consider `CHECK ((level = 'equipment') = (unit_id IS NOT NULL) AND (level = 'equipment') =
  (parent_id IS NULL))` on `equipment` — MariaDB enforces CHECK constraints — so the shell rule
  in § 5 is also a DB rule. Optional; if omitted, say "shell-enforced only" in § 5.
- Name the FKs (`fk_equipment_parent`, `fk_equipment_unit`, `fk_equipment_class`,
  `fk_equipment_events_equipment`), as v2 did.
- `old_value` / `new_value VARCHAR(200)`: the longest full path is about 80 characters; fine.
- A `remark VARCHAR(255) NULL` on `equipment_events` (reason for scrapping) is standard
  disposal practice (ISO 55001 § 8.2) but not asked for; defer and note it, since adding a
  column later is one migration.

### BR1-15 — Plan.MD and Philosophy updates the planner owes at approval — `nit`

- Plan § 4.1 Fields: status list is "in service / standby / scrapped" → add "out of use".
- Plan § 5: add `equipment_events`; note `serial_counters` is used from phase 2.
- Plan § 3 matrix: `equipment:read_all_units` row.
- Maintenance-Philosophy § 9: the A/B/C meanings are now **Decided** (currently "TBD … a
  common scheme (Proposed)").
- Plan § 4.1 or § 9: the "no standby relationship recorded" assumption (§ 10.3).

### BR1-16 — Tests: name the breaking tests and the fixture order — `nit`

- `conftest._MASTER_TABLES` becomes `("equipment_events", "equipment", "user_units", "units",
  "sites", "equipment_classes", "serial_counters")`. Whether `serial_counters` is cleared
  matters: if not, codes keep climbing across sessions and no test may assert an absolute
  number. Recommend clearing it and still asserting **relative** numbers (`n`, `n+1`) per
  fresh class from `uniq.class_code()`, which isolates counters per test anyway.
- `navigation.test.js`: "maint_operator sees Masters only", "manager and IT admin see Masters
  and Settings", "everyone with a role lands on Masters" all change; the four permission
  constants gain `equipment:read` (and `equipment:read_all_units` for manager / IT admin).
- The "forced rollback leaves no event" test: say how — monkeypatch the UPDATE step to raise
  after the events are written, as `TestErrorMapping` patches `_insert`.
- The pure `format_equipment_code` test "1 → `VBM001`" implies zero-padding to three digits
  (`f"{n:03d}"`); fine, but write the rule in § 6 as `prefix + str(n).zfill(3)` so 10000 →
  `VBM10000` is unambiguous.

---

## Checked and found consistent

- **Decisions of 14-10-2026** (§ 3) are reflected in § 5 (`criticality` NULL on parts =
  inherit; `status` enum of four; `level` enum of three; `parent_id`/`unit_id` exactly-one
  rule; `equipment_events`) and § 6 (parent table; scrapped final; one `moved_unit` event on
  the equipment).
- **Plan.MD § 4.1 and § 9.3:** permanent code = class prefix + 3 digits growing to 4, one
  counter per prefix across sites, derived full path, no code change on move or reclassify —
  all carried. The field list (code, name, class, make, model, serial, year, criticality,
  status, unit) is complete.
- **Plan § 3 unit access:** "every list and detail endpoint filters by the user's units on the
  server"; the manager sees all; lower-case username comparison (S001 BR1-11) carried.
- **S001 carry-overs** verified in code: `ApiError` and the 1062 map in `masters.py`;
  `get_db()` / `transaction()` in `db_helpers.py`; v3 is the last migration, so v4 is next;
  `defaultSiteId()` and the three `ensure*()` caches in `stores/masters.js`; `FormModal` with
  its `footer-left` slot; `equipment:edit = ("maint_engineer", "it_admin")` with the manager
  via `ROLE_INCLUDES`; `update_equipment_class` has no in-use check yet (the comment says S002
  adds it); `update_unit` counts only `user_units`.
- **Audit convention** (S001 § 4) reused unchanged; events carry `created_*` only — correct
  for an append-only log.
- **Pagination** is a stated return to the base pattern, with the reason (500 equipment plus
  parts); the `{items, total, page, per_page}` shape matches the base.
- **No DELETE** and "scrapped instead" follow the controlled-register rule.
- **Pure core / thin shell:** `equipment_core` takes `this_year` as an argument; no `now()`
  in the core.
- **Not over-engineered:** no stored path, no stored unit on parts, no rotable model, no
  standby relationship, no custom fields — each deferred with a reason.
- **Open question 1 (bulk import)** is correctly left to the user and sized as its own step.
