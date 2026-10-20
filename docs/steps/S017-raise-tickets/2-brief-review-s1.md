```
Step: S017 — Raise and see tickets
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 20-10-2026
```

Reviewed against: 6c771e1 (no uncommitted step code; the working tree's
changes are docs only — README index, the S015/S016 briefs, the S017/S018
folders)

# S017 — staleness review, round s1

**Verdict: the brief still holds. No `blocker` or `major` finding; three nits
on code comments the brief's named edits should also touch.**

Baseline of the brief: `90284ec + uncommitted S016, S015` (r2). Since then
S015 and S016 were committed as **6c771e1**, with their fix rounds (S016
CR1-01/02, S015 CR1-01/02). The question here is only whether each statement
the brief makes about that code still holds. I checked the diff
`git diff 90284ec 6c771e1` of the nine files named by the orchestrator, and the
code as it stands at HEAD.

## Claims verified (still true at 6c771e1)

| Brief says | Code at 6c771e1 |
|---|---|
| Migration v11 is the latest, so S017 is **v12** (§ 3, § 4) | `local_db._MIGRATIONS` ends with `(11, "Failure modes, causes, maintenance actions", …)`; `LATEST_VERSION` is taken from the last entry. v11's statements are `CREATE TABLE IF NOT EXISTS` / `INSERT IGNORE`, so a v12 on top changes nothing of v11's re-run |
| `PUT /api/masters/failure-modes/<id>` locks the mode row, then the code-change check (§ 5.7) | `update_failure_mode`: plain read of `class_id` → class lock only on reactivation → `_lock_row(cur, "failure_modes", mode_id)` → label check → `update_row`. The ticket count slots in after the lock as § 5.7 says. `_update_plain_master` (causes, actions) is untouched by S017; S018 freezes those |
| `failure_codes:edit` exists; `SITE_SCOPED` is the set S017 adds its two keys to (§ 3, § 5.6) | `PERMISSIONS["failure_codes:edit"] = ("maint_engineer", "it_admin")`, global. `SITE_SCOPED = {equipment:read, equipment:edit, equipment:purge_documents, people:assign_technicians}`; `test_rbac` asserts only `SITE_SCOPED <= set(PERMISSIONS)` and `"failure_codes:edit" not in SITE_SCOPED`, so adding `ticket:read` / `ticket:raise` breaks no existing assertion |
| IT admin holds `ticket:*` at every unit through `every_unit_by_token` (user decision 7, § 5.6) | `access_core.every_unit_by_token(key, roles)` is true when the token roles grant **both** the key and `equipment:read_all_units`; `it_admin` holds `read_all_units`, so once `ticket:read` / `ticket:raise` list `it_admin`, `user_unit_ids` returns `None` (every unit) for it. No conflict with code |
| `_next_code` is `INSERT … ON DUPLICATE KEY UPDATE` + read-back on the caller's connection, scope `EQ:<prefix>` (§ 3, `next_counter`) | Unchanged at lines 342–349; the extraction to `db_helpers.next_counter(cur, scope)` is a straight lift |
| Scrap path: node lock (1) then `_check_parts_scrapped` locks children and grandchildren `FOR UPDATE` (§ 5.8) | `update_equipment`: `load_node_for_user(… for_update=True, key="equipment:edit")` → … → `if clean.get("status") == SCRAPPED: _check_parts_scrapped(cur, node_id)` → `update_row`. The ticket count goes after `_check_parts_scrapped`, with every descendant locked, as § 5.8 says |
| `load_node_for_user(cur, id, for_update=True, key="ticket:raise")` gives 404 / 403 and the locked row (§ 5.4) | Signature `load_node_for_user(cur, node_id, for_update, key=None)`; the locked read is `LOCK_EQUIPMENT` (1), then `_read_node` + unit access → 404, then `require_perm_at(key, node["site_id"])` → 403 |
| `machine_and_component(node)` from `level`, `parent_id`, `gp_id` (§ 5.2) | `_NODE_COLUMNS` carries `gp_id`, `gp_level`, `parent_id`; `_ancestors` is still private |
| The node detail's `permissions` (`permissions_at_site`) drives the equipment page's section and button (§ 3, BR2-04) | `get_equipment` returns `{**_detail(cur, node), "permissions": permissions_at_site(node["site_id"])}` |
| The equipment picker uses the existing list endpoint (§ 3) | `list_equipment` now takes its filters from `_list_filters()` (S015 refactor); scrapped still excluded by default; the response shape is unchanged |
| `conftest._TABLES` gains tickets, their events and documents (§ 3) | `_TABLES` is the same tuple plus nothing; S016 added `_SEEDED_TABLES` (`failure_modes`, `failure_causes`, `maintenance_actions`), cleaned by `created_by <> 'migration-v11'` **before** `_TABLES`, all under `FOREIGN_KEY_CHECKS = 0`. So tickets pointing at test-made modes are deleted in the same sweep, whatever the order; `tickets` and `ticket_events` just join `_TABLES` (before `equipment`, by the "child tables first" convention). `Uniq.failure_code()` / `failure_label()` are there for the mode-freeze test |
| `test_rbac` role matrix (§ 8) | `TestComputePermissions.test_role_matrix`, parametrised per role, is where the two keys go: operator, technician, supervisor, engineer, manager, it_admin gain both; storekeeper's row unchanged. `test_it_admin_stands_apart` asserts only `expand_roles`, unaffected |
| `no_login_role_error` compares against `TECHNICIAN_ROLE`; `NO_LOGIN_ROLE_MESSAGE` is "Without a login, a person can only be a technician"; `technician_only` separate (§ 5.9) | Exactly so at `masters_core.py:360, 410–419`. `TECHNICIAN_ROLE`'s comment still says "and the one a person without a login may hold" — the brief's BR2-06 edit removes that half |
| The 400 → 403 flip for engineer + Operator (§ 5.9, § 8) | `put_person_site`: `_check_site_row` (400) → `no_login_role_error` (400) → `_check_site_write` (403, `technician_only`). With Operator in `NO_LOGIN_ROLES` the second check passes and the third answers 403 "Only IT admin can set this role"; admin passes on `masters:edit` → 200; engineer / manager / supervisor still stop at the second check → 400. The brief's split of `TestNoLoginTechnicianOnly.test_other_roles_are_400` (`test_site_roles_api.py:243`, parametrised over engineer / operator / manager / supervisor, both clients) is the right one |
| `test_masters_core.TestEngineerLimits.test_no_login_only_technician` asserts operator → message (§ 3) | Line 414: `no_login_role_error(["maint_technician", "maint_operator"]) == NO_LOGIN_ROLE_MESSAGE` — this is the assertion that flips, as the brief says |
| `GET /api/masters/failure-modes?class_id=N` gives the class's modes plus General, by label (§ 6) | `list_failure_modes` does exactly that; `/api/tickets/modes` is kept for the node → machine resolution, as the brief argues |
| `documents.py`, `file_store.py`, `test_migration_v9.py`, `test_documents_api.py` | Not in the diff; `Owner`, `OWNERS`, `_OWNER_FOLDERS`, the v9 CHECK name and the `test_documents_api.py:498` assertion on `chk_equipment_documents_owner` are as r2 read them |
| Docs "at approval" (§ 3) | Already in 6c771e1: Plan.MD § 3 (`ticket:read` / `ticket:raise` rows, IT admin's full access, Operator without a login by IT admin), § 4.1 (scrap refused), § 4.2 (`TK-`), § 5 (`tickets`, `serial_counters`); the S011 brief's note under A1 |

## Findings

### BS1-01 (nit) — comments in `masters.py` that S017's § 5.7 edit must bring along

**Problem.** The S016 commit added, in `masters.py`, (a) the section comment
"Nothing references them yet: S017 and S018 add *code frozen once in use* when
tickets point at them", and (b) `update_failure_mode`, whose plain pre-read is
`SELECT class_id FROM failure_modes WHERE id = %s` and whose docstring says
"Edit code, label, description". § 5.7's "if the code changes" needs the
stored code to compare against, so the pre-read gains `code` (or the locked
row returns it); the two comments become wrong the moment S017 lands.

**Why it matters.** Only accuracy of comments; the rule in § 5.7 is right.

**Options.** (1) Add one line to § 3's `masters.py` bullet: "the stored read
gains `code`; the section comment and the docstring say the freeze is in". (2)
Leave it to the coder. **Recommend (1)**, so the code reviewer has it to check.

### BS1-02 (nit) — `config_rbac.py`'s "it_admin stands apart … not maintenance work" after user decision 7

**Problem.** Decision 7 (IT admin holds `ticket:read` and `ticket:raise`) came
after r2 and was approved at gate A, so it was never read against the code.
The code it touches is fine (BS table above), but the comment over
`ROLE_INCLUDES` — "it_admin stands apart: housekeeping and settings, not
maintenance work" — and § 3's `config_rbac.py` bullet, which names only the two
keys and `NO_LOGIN_ROLES`, leave the departure unrecorded in the one file that
is "the single source of roles and keys". Plan.MD § 3 records it; the file
doesn't.

**Why it matters.** The next reader of `config_rbac.py` sees IT admin in a
maintenance key with no reason, against the comment two screens up.

**Options.** (1) The comment on the new keys names decision 7 and the reason,
as `failure_codes:edit`'s does ("IT admin too, as masters housekeeping"), and
the `ROLE_INCLUDES` comment gets "(tickets: full access, S017 user decision)".
(2) Leave the comments. **Recommend (1)**: one line in § 3.

### BS1-03 (nit) — the "one owner lock, node or model" paragraphs

**Problem.** § 3 says the `equipment.py` docstring gains the ticket row (7)
and the two accepted deadlocks. Two more paragraphs state the same rule and
would go stale with it: the last paragraph of `equipment.py`'s docstring
("documents.py … takes exactly one owner lock per write … the node (1) … or a
model row (4), never two") and `documents.py`'s own docstring (line 9 "exactly
one node or one model (the v9 CHECK)"; lines 23–28 "Locks: a document write
takes exactly one owner lock — the node row … or the model row (4)").

**Why it matters.** The lock-order notes are what the next step's planner
reads; a third owner missing from them is how a cycle gets in later.

**Options.** (1) Name both paragraphs in § 3 (`equipment.py` docstring's
documents paragraph; `documents.py` module docstring: three owners, the v12
CHECK, the ticket row (7) as the third single owner lock). (2) Leave to the
coder. **Recommend (1)**.

## Checked and found consistent

- v12 is the next migration; v11's statements are all safe to re-run under it.
- `update_failure_mode`'s lock order (class on reactivation → mode) is where
  § 5.7's count goes; no lock added, no order changed.
- `failure_codes:edit` is global and stays out of `SITE_SCOPED`; the two
  `ticket:*` keys join a four-key `SITE_SCOPED` whose tests only check subset
  membership.
- IT admin's "every unit" for `ticket:*` follows from `every_unit_by_token`
  with no code beyond listing `it_admin` in the two tuples.
- `_next_code`'s shape, the scrap path and its locks, `load_node_for_user`'s
  signature and refusal order, `gp_id` in the node fragment, `permissions` in
  the node detail — all as the brief reads them.
- `conftest`: S016's seeded-table clean-up runs with FK checks off before
  `_TABLES`, so adding `tickets` / `ticket_events` to `_TABLES` needs no
  special ordering against `failure_modes`.
- `test_rbac.test_role_matrix`, `test_masters_core` line 414,
  `test_site_roles_api.TestNoLoginTechnicianOnly.test_other_roles_are_400` are
  the tests the brief names, and the 400 / 403 / 200 split it predicts follows
  from `put_person_site`'s check order.
- `documents.py`, `file_store.py`, the v9 CHECK and its tests are unchanged
  since r2.
- Plan.MD and the S011 brief already carry the S017 decisions, including
  decision 7.
- Whitespace-only differences in the step files (IDE re-padding) are not
  findings.
