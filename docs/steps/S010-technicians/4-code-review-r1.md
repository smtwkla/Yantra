```
Step: S010 — Technicians and trades
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S010 — Code review, round 1

**Verdict:** no `blocker` or `major` finding is open. There are three `nit`
findings. The backend follows the brief rule by rule. Absent fields are left
unchanged, the login is masked, the locks are taken in the brief's order, and
the trades-only change gets its audit stamp. The frontend uses the existing
masters pattern, so the S007 guard applies to both new dialogs.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: 735 passed in 40.8 s, including every case in the new
    `test_technicians_api.py`.
  - Frontend: vitest, 6 files, 36 tests passed.
- `npx vite build` in `frontend/`: **clean**, 148 modules, built in 1.98 s, no
  warnings.

## Scope reviewed

- I read the diff with `git diff -w --ignore-cr-at-eol` and read the new files
  in full.
- Backend: `local_db.py` (v7), `masters_core.py`, `masters.py`,
  `config_rbac.py`.
- Tests: `conftest.py`, `test_masters_core.py`, `test_rbac.py`,
  `test_technicians_api.py` (new).
- Frontend: `TradesPanel.vue` (new), `TechniciansPanel.vue` (new),
  `useMasterForm.js`, `MastersView.vue`, `stores/masters.js`,
  `tests/navigation.test.js`. For context only: `useFormModal.js`.
- Not reviewed, as out of scope: the S009 drop (`Plan.MD`, the S009 folder,
  `s009-code.patch`), the step-workflow changes (`.claude/skills`,
  `.claude/agents`, README § Tracks and § Manual checks) and the S011 brief.

## Findings

### CR1-01 — nit — The report has no `## Manual checks` checklist

`docs/steps/S010-technicians/3-impl-report.md:82-88`

- **Problem.** README § Manual checks now asks for the brief's manual checks as
  `- [ ]` boxes under `## Manual checks`. The report has them as a plain list
  inside § 5 "Not done, deferred or assumed". S010 was written before that
  rule, so this is only a nit (orchestrator's instruction).
- **Failure scenario.** At gate B the planner has no boxes to show, and nothing
  records which checks the user ticked or skipped before `Done`.
- **Suggested fix.** Move the four checks of brief § 8 "Manual checks (user)"
  into a `## Manual checks` section as unticked boxes. Keep "the rendered look
  of the badges and chips" as a plain note.

### CR1-02 — nit — The list-of-ids check is written twice

`backend/masters_core.py:130-136` (`_parse_trade_ids`) and `:214-218`
(`validate_unit_ids`)

- **Problem.** Both functions repeat the same check: a list of non-bool ints
  ≥ 1, de-duplicated with order kept. Only the label and the extra "not empty"
  rule differ. The brief asked for "a parser **like** `validate_unit_ids`", so
  this is allowed. Still, CLAUDE-COMMON's DRY rule would favour one shared
  helper.
- **Failure scenario.** A later change to id parsing gets made in one copy and
  not the other, for example rejecting ids above the INT range. Units and
  trades then accept different input.
- **Suggested fix (optional).** Add a private `_parse_id_list(raw, label)` that
  returns the de-duplicated list or raises `ValueError`. Have
  `validate_unit_ids` wrap it in its `(ids, errors)` shape, and have
  `_parse_trade_ids` call it and then add its empty-list rule. This can wait
  for the next step that touches this code.

### CR1-03 — nit — Two small test gaps

`backend/tests/test_technicians_api.py:59` and `:131-142`

1. **A loose assertion and a fixed login.**
   `test_create_with_two_trades_ordered_by_name` sends the literal login
   `"Ravi.K"` and checks `tech["username"].startswith("ravi.k")`.
   - The value is known exactly, so `startswith` would also pass for
     `"ravi.kxyz"`.
   - The literal login doesn't come from `uniq`, unlike every other test here.
     If another test ever uses `ravi.k`, the two collide on
     `uq_technicians_username`.
2. **The duplicate-login 409 is tested on `POST` only.** The `PUT` path, which
   gives an existing technician a login that someone else holds, goes through
   the same handler but is not exercised.

- **Failure scenario.** A regression in the `PUT` error mapping, or a login
  that is normalised wrongly, still passes the suite.
- **Suggested fix.** Use `uniq.username()` with a mixed-case variant and assert
  equality with the lower-cased value. Add one `PUT {username: <taken>}` → 409
  field `username` case to the duplicate-login test.

## Checked and found consistent

- **Migration v7** (`local_db.py:204-239`):
  - append-only, numbered after v6, and each statement uses `IF NOT EXISTS`;
  - the tables, columns, ENUM, the nullable unique `username`, the composite
    PK and the named FKs match brief § 4;
  - default charset, so the general_ci collation gives case-insensitive unique
    names;
  - no seed data.
- **Absent field means unchanged** (brief § 5.2):
  - `_TECHNICIAN_FIELDS` goes through `_validate`, which skips absent keys on
    update;
  - `update_technician` pops `trade_ids` with a `None` default and touches the
    trade set only when it was sent;
  - `PUT {active}` therefore keeps the trades and the login.
    `test_put_active_only_keeps_trades_and_login` proves it with two trades and
    a login.
  - The validator refuses an explicit `trade_ids: null` (the pure test lists
    `None` as bad), so `None` can't be confused with "absent".
- **Login rules:**
  - `_parse_login` maps `None` / `""` to `NULL` before the regex, otherwise
    `validate_username` (strip, lower-case, `USERNAME_RE`);
  - duplicates are caught by `uq_technicians_username` with no pre-check;
  - clearing frees the login (tested).
  - `"   "` from an API caller is refused rather than cleared, which follows the
    brief's wording ("`null` or `""`"). The dialog trims before deciding, so
    the UI never sends it.
- **`UNIQUE_KEY_ERRORS`** (`masters.py:37-39`):
  - `uq_trades_name` → `name` and `uq_technicians_username` → `username`, with
    the brief's texts, including BR2-02's "(it may be an inactive one)";
  - registered in `masters.py` beside the S001/S004 keys, which is what
    `api_common.py:6` prescribes ("each module adds the names of its UNIQUE
    keys");
  - the 409 on a different-case trade name and on a duplicate login are both
    tested.
- **Login masking** (`masters.py:495-501`):
  - `_technicians_out` deletes `username` unless
    `has_perm("technicians:edit")`, on the list and on the write responses;
  - the parametrised test covers all six roles (key absent for operator,
    technician and storekeeper; present for engineer, manager and IT admin);
  - the frontend's Login column follows the same `canEdit` rule.
- **Lock order and audit** (brief § 5.4):
  - `POST /technicians` runs in one transaction: it locks the trade rows
    through `_check_grantable` (`FOR UPDATE`), then inserts the technician and
    its links. An unknown trade rolls everything back (tested: no row left).
  - `PUT` takes `_lock_row("technicians")` first, then the trades. The trade
    `PUT` locks one trade row only. Nothing else touches these tables, so there
    is no lock cycle.
  - `_held_trade_ids` is a plain read after the technician lock. Every writer of
    a technician's trade set holds that lock, so the read is current.
  - The trade set is diffed, so kept trades keep `granted_at/by` (tested).
  - When only the trades change, the technician row is stamped `updated_at/by`
    with `NOW()`, the same clock as `update_row`. An unchanged set doesn't stamp
    (both tested).
- **`_check_grantable` generalised** (`masters.py:419-432`):
  - the units path now calls it with `("units", …, "unit_ids", "unit")`;
  - its messages come out exactly as before ("Unknown unit N", "Unit N is
    inactive and cannot be newly granted");
  - the existing unit-access tests
    (`test_masters_api.py:540`, `:547`, `:588`) still pass;
  - the table name is a code constant, documented as such. No SQL is built from
    client input: every id goes in as a `%s` parameter.
- **Inactive trades:**
  - an inactive trade can be kept but not newly given, on both create and
    update (tested);
  - it is listed with `active: false`;
  - the list's trades come from one `IN (…)` query, ordered by trade name, with
    inactive trades included.
- **RBAC:**
  - `technicians:edit = ("maint_engineer", "it_admin")`, and managers inherit
    it;
  - no `admin` and no `*` mixing;
  - reads use `masters:read`;
  - writes are 403 for the technician, operator and storekeeper and 201/200 for
    the three editors (tested);
  - `test_role_matrix` and `navigation.test.js` are updated in step.
- **Actor and DB:**
  - the actor always comes from `actor()`, never from the body;
  - `get_db()` covers a dead connection and an unavailable DB (503), as in the
    other masters.
- **Pure core:** the validators are pure, with no DB, clock or framework.
  `_parse_bounded_name` is shared by `parse_name` and the trade-name parser, so
  the name rule is written once.
- **Frontend:**
  - `TradesPanel` follows `EquipmentClassesPanel` without the code field.
  - `TechniciansPanel` has:
    - kind radios with the "Contractor firm" label switch;
    - the trade checkboxes: active trades plus the held inactive ones, fixed in
      `heldInactiveIds` when the dialog opens and marked "(inactive)";
    - the login field with the brief's help line;
    - a `toBody` that sends `""` as `null`.
  - `trade_ids` is kept sorted in both `fromRecord` and `toggleTrade`, so the
    S007 dirty check compares by value. Both dialogs pass `:dirty` to
    `FormModal`.
  - Every field the dialog sends shows its `fieldError`.
  - `useMasterForm`'s `toBody` passthrough falls back to `useFormModal`'s
    default when it is not given, so the other panels are unchanged.
  - The sections are placed after "Equipment types" with the brief's icons.
    `ensureTrades()` is cleared by `resetMasters()`.
- **Reported decisions:**
  - the form leaves out `active` (decision 2): `active` goes through
    `ActiveToggle`, as in every other masters panel;
  - the `toBody` passthrough;
  - the technicians list held locally;
  - the shared name parser;
  - the fixtures created through the API.

  All are listed in "Decisions taken", and none changes behaviour against the
  brief. I found no unreported departure and nothing built beyond scope.

## Manual browser checks still needed (user)

- **Trades and technicians as engineer:**
  - add the trades Electrician, Fitter and Tool maker;
  - add an in-house technician with two trades and a login;
  - add a contract record named after a firm.
- **An inactive trade:** deactivate a trade, then open that technician. The
  trade shows greyed "(inactive)" and is kept on save, and other technicians
  are not offered it.
- **Deactivating a technician:** do it from its dialog. Its trades and login
  stay.
- **As operator:** both lists show, with no Login column and no Add or Edit
  buttons.
- **The S007 guard:** change a technician dialog (tick a trade, then untick it
  again, as well as a real change) and close it. It asks before discarding only
  when something really changed.
- **The look:** the kind badges, and the trade chips with the inactive ones
  dimmed.
