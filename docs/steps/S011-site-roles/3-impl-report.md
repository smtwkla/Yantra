```
Step: S011 — Roles per site, held in Yantra
Doc: impl-report
Author: Coder (Opus)
Date: 16-10-2026
```

# S011 — Implementation report

Built per the approved brief **including amendment A1** (§ 10), the A1 rules added
after `2-brief-review-r4.md`, the user decisions at gate A (16-10-2026) and the rules
added after `2-brief-review-r5.md`. Where A1 or those decisions differ from the brief
body, A1 / the decisions were followed; `technicians:edit` in the body is read as
`people:edit` (A1 rule 6).

Built **on top of the uncommitted S010** working tree (baseline tree `15227de`). Every
change to S010 behaviour is listed under § 4.2.

Tests: **backend 891 passed** (`tooling/run-tests.bat`, was 763 before S011);
**frontend 38 passed** (vitest, 7 files); `npx vite build` clean (no warnings).

## 1. What was built

1. **Roles per site, on the person.** A person in Team has, per site, one role out of
   `maint_manager`, `maint_engineer`, `maint_supervisor` (new), `maint_technician`,
   `maint_operator`, `maint_storekeeper`, and either all units of the site or chosen
   units. For a person with a login, these rows are their Yantra access.
2. **Rights follow the record's site.** At a piece of equipment the user has the keys
   of their role at that equipment's site (plus their token roles). Lists gated by a
   key are scoped by it: the equipment list by `equipment:read`, the removed-documents
   list by `equipment:purge_documents`, the write pickers by `equipment:edit`.
3. **Who grants.** IT admin (`masters:edit`) sets any role at any site. An engineer
   (new key `people:assign_technicians`, held per site; managers inherit) adds, changes
   or removes **Technician** rows at their own site, for any person. A person without
   a login can only be a Technician. Nobody changes their own access.
4. **Login save.** Setting, changing or clearing a login (IT admin) carries the
   person's whole set of sites in the same request and transaction.
5. **Keycloak becomes simpler.** Tokens are accepted with `maintenance_team` (login
   only, no permission), `it_admin`, or admin (`mspv-apps-admin` / `admin`). Old
   `maint_*` roles are ignored and logged once per page load by `/api/auth/me`.
6. **No access yet / DB down.** A signed-in user with no permission sees the normal top
   bar (name, Sign out), no nav, and "You have no access yet — ask IT or your engineer
   to add you in Team", or "The database is unavailable — try again shortly" when
   `/auth/me` says the database is down. IT admin keeps its token permissions while the
   DB is down (Settings › Database works).
7. **Masters › "Unit access" is gone**; the **Team** dialog has a "Sites and roles"
   section.
8. **Migration v8**: tables `memberships` and `person_units`; legacy `user_units` rows
   copied (people created for unknown usernames); `user_units` kept.

## 2. How it works

### 2.1 The pure core — `backend/access_core.py`
A membership is `Membership(site_id | None, role, all_units)`; `site_id = None` means
every site (only the dev stub and the test harness make one). Functions:
`global_permissions(token_roles, memberships)` (union), `permissions_at(…, site_id)`,
`has_key_at(key, …)`, `every_unit_by_token(key, token_roles)`,
`unit_ids_for(key, token_roles, memberships, units, user_unit_ids)` and
`display_role`. Rules: a membership whose role is not in `SITE_ROLES` is ignored
entirely (no key, wildcard or not, no units); a query for site `None` matches no real
membership; `unit_ids_for` returns `None` (every unit) only for admin or when the
token roles grant both the key and `equipment:read_all_units`, so a future key IT
admin does not hold fails closed; `has_key_at` / `unit_ids_for` assert the key is in
`SITE_SCOPED`. `compute_permissions` and `expand_roles` moved here (pure) and are
re-exported by `auth_utils`.

### 2.2 The shell — `backend/auth_utils.py`
- `require_auth` stays DB-free. `g.user` = `make_user(username, name, token_roles,
  memberships=None, stale_roles)`; `memberships` is `None` in production (read from the
  DB) or a fixed list (dev stub, tests).
- `current_memberships()` reads lazily, once per request (cached in `g`, never in the
  shared dev-stub dict): token username (normalised) → **active** person with that
  login → `memberships`. Units (`_unit_pools`) are read separately and only when a
  unit question is asked: the person's `person_units` on active units, and every active
  unit only when some membership has all units. Everything goes through `get_db()`, so
  it shares the request's transaction; a down DB raises `DBUnavailable` → 503.
- `has_perm(key)` = admin, or a token key (no query), or held at any site.
  `has_perm_at(key, site_id)`, `require_perm_at(key, site_id, field)` (403 "You can't
  do this at <site code>", the code from a plain read of `sites`),
  `permissions_at_site(site_id)`, `user_unit_ids(key)`, `membership_sites()`.
- `require_perm`'s 403 log line uses the token roles plus whatever memberships are
  already cached; it never forces a query.
- Dev stub: `DEV_STUB_ROLE` = a site role → that role at every site, all units;
  `admin` / `it_admin` / `maintenance_team` → token roles; anything else → nothing.

### 2.3 Site checks on writes (§ 5.4) — every write route
The checks live in the three choke points, after their existing refusals:
`load_node_for_user(cur, node_id, for_update, key=None)` (a write must name its key:
assertion), `_load_target_node(…, key)` and `_lock_target_unit(…, key)`.
`_NODE_COLUMNS` gained `s.id AS site_id`; `_LOCK_UNIT` gained `site_id`.

| Route | Check |
|---|---|
| `POST /api/equipment` (equipment) | `equipment:edit` at the target unit's site (`_lock_target_unit`, field `unit_id`) |
| `POST /api/equipment` (part) | `equipment:edit` at the parent's site (`_load_target_node`, field `parent_id`) |
| `PUT /api/equipment/<id>` (edit, status, notes, type, class, criticality) | `equipment:edit` at the node's site (`load_node_for_user`) |
| `PUT /api/equipment/<id>` with `unit_id` (move) | the node's current site **and** the target unit's site |
| `PUT /api/equipment/<id>` with `parent_id` (re-parent) | the node's site **and** the new parent's site |
| `POST …/<id>/documents` (upload) | `equipment:edit` at the node's site — on the early plain read (so no file is written) and again under the lock |
| `PUT …/documents/<doc>` (title) | `equipment:edit` at the node's site (`_lock_node_for_change`) |
| `DELETE …/documents/<doc>` (remove) | `equipment:edit` at the node's site |
| `POST …/documents/<doc>/restore` | `equipment:purge_documents` at the node's site |
| `POST …/documents/<doc>/purge` | `equipment:purge_documents` at the node's site (`load_node_for_user`) |
| `PUT / DELETE /api/masters/people/<id>/sites/<site_id>` | `people:assign_technicians` at that site (Technician rows only), or `masters:edit` |
| Equipment classes and types (`equipment:edit`), trades and people (`people:edit`), sites and units (`masters:edit`), settings | no site: the global key (held somewhere) |

Reads: the equipment list, `/my-units`, the node detail and the document list/files
use the `equipment:read` units (404 outside them, as before); the removed-documents
list uses the `equipment:purge_documents` units. The node detail now carries
`permissions` (the user's full key list at the node's site); `/my-units` adds
`edit_unit_ids` (`null` = every unit).

### 2.4 Site roles in Team — `backend/masters.py`, `masters_core.py`
- `GET /api/masters/people`: per person `sites` = `[{site_id, site_code, active, role,
  all_units, units, editable}]` and `assignable_site_ids`, for `people:edit` holders:
  IT admin (`masters:read_senior`) sees every row; an engineer sees every row of a person
  without a login, and of a person with a login only the rows at sites where they hold
  `people:assign_technicians`. `editable` and `assignable_site_ids` come from the
  backend. Floor roles get neither key. Unit rows with no membership (legacy, from
  migration v8) show as a row with `role: null`.
- `PUT /api/masters/people/<id>/sites/<site_id>` `{role, all_units, unit_ids}` and
  `DELETE …`: lock the person row → lock their `memberships` and `person_units` rows →
  400s (body; unknown site; inactive site or unit kept-not-granted; units of that site;
  no login → Technician only) → 403s (own person; then `masters:edit` passes; else
  `people:assign_technicians` at the site and Technician before and after) → write
  (diff, so kept rows keep `granted_at/by`; all units clears the site's unit rows).
  `DELETE` of a missing row → 404. One INFO line per real change: `site role changed:
  actor=… person=… site=… before=[SITE:role:UNITS] after=[…]`. The response is the
  person, filtered like `GET /people`.
- `POST / PUT /api/masters/people` with `username` set, changed or cleared must carry
  `sites` (400 field `sites`); they are written in the same transaction, replacing the
  set; clearing a login needs Technician-only rows. One INFO line `login saved:
  actor=… person=… '<name>' login=… sites=[…]`.
- `PUT /people/<id>` on one's own person: changing the login, `active` or sending
  `sites` → 403 "You can't change your own access". Setting a login to one's own →
  403 "You can't give yourself a login".
- Lock order: person → trades → the person's membership and unit rows → units; the
  membership insert then takes the site row through its FK (unit → site, as
  `update_unit`). `equipment.py`'s lock-order docstring and `masters.py`'s docstring
  say so. `_unit_is_referenced` counts `person_units`.

### 2.5 `/api/auth/me` — `backend/app.py`
Returns `username, name, roles` (token roles), `role` (most privileged of token and
site roles; `null` for login-only), `permissions` (global union), `sites:
[{site_id, site_code, role, all_units}]`, `db_unavailable: false`. On `DBUnavailable`:
the token permissions, `sites: null`, `db_unavailable: true`. Logs one WARNING when the
token still carries old `maint_*` roles.

### 2.6 Migration v8 — `backend/local_db.py`
SQL only, every statement safe to re-run: `CREATE TABLE IF NOT EXISTS memberships`
(`person_id`, `site_id`, `role VARCHAR(30)`, `all_units`, granted/updated who and when,
PK `(person_id, site_id)`, `fk_memberships_person`, `fk_memberships_site`), `CREATE
TABLE IF NOT EXISTS person_units` (PK `(person_id, unit_id)`, `fk_person_units_person`,
`fk_person_units_unit`), `INSERT INTO people … SELECT DISTINCT … FROM user_units WHERE
NOT EXISTS …` (name = login = username, direct, `created_by = 'migration-v8'`; a
username held by an inactive person attaches to it), `INSERT IGNORE INTO person_units
… SELECT …` keeping `granted_at/by`. **No drop of `user_units`**; S011's code no longer
reads or writes it.

### 2.7 Frontend
- `stores/auth.js`: `dbUnavailable`; the 401 text "Your account is not in the
  maintenance team. Ask IT to add you in Keycloak."
- `App.vue` + `views/NoAccessView.vue`: with no permission, the shell renders with the
  top bar and no nav, and `NoAccessView` instead of the route.
- `PeoplePanel.vue` (Team): a "Sites and roles" column and a dialog section — one block
  per site (role select, All units switch, the site's unit checkboxes, remove), read-only
  text for rows the user may not change, "Add a site…" from `assignable_site_ids`. The
  role select offers only Technician unless IT admin edits a person who has (or is
  given) a login. Saving: the person first, then each changed row one by one (PUT or
  DELETE); the first refusal stops the save, shows on its row, and the person is reloaded
  so a retry compares with the server. An IT admin login change sends the whole set in
  one request, and the dialog shows "Adding this login gives access as: …".
- Equipment page: edit buttons follow the node's `permissions`; the create / move unit
  pickers use `edit_unit_ids`.
- `MastersView.vue`: the "Unit access" section and `UserUnitsPanel.vue` are removed.

## 3. Files touched (relative to the S010 baseline)

Backend:
- `backend/access_core.py` — **new**, the pure rules (§ 2.1); `compute_permissions`/`expand_roles` moved here.
- `backend/auth_utils.py` — token roles, `make_user`, lazy memberships/units, `has_perm`, `has_perm_at`, `require_perm_at`, `permissions_at_site`, `user_unit_ids`, `membership_sites`, dev stub.
- `backend/config_rbac.py` — `maint_supervisor`, `TOKEN_ROLES`, `LOGIN_ROLE`, `SITE_ROLES`, `TECHNICIAN_ROLE`, `SITE_SCOPED`, `people:assign_technicians`, `equipment:read_all_units` = IT admin only, docstring on role sources.
- `backend/app.py` — `/api/auth/me` (§ 2.5).
- `backend/equipment.py` — keyed choke points, `site_id` in node and unit reads, `accessible_unit_ids(cur, key)`, node `permissions`, `edit_unit_ids`, lock-order docstring.
- `backend/documents.py` — keyed `_lock_node_for_change`, upload early check, purge key, removed list scoped by `equipment:purge_documents`.
- `backend/masters.py` — user-units routes removed; site rows (§ 2.4); login save with sites; own-person rules; `_check_grantable` returns the locked rows; `_unit_is_referenced` on `person_units`.
- `backend/masters_core.py` — `validate_site_row`, `validate_site_rows`, `no_login_role_error`, `technician_only`.
- `backend/local_db.py` — migration v8.
- `backend/example_secrets_app.py` — `DEV_STUB_ROLE` comment.

Backend tests:
- `tests/conftest.py` — `test_user` harness (§ 5.8), `_TABLES` (`person_units`, `memberships` first), `make_person` adds `sites: []` with a login, `user_with_units` creates a person with the login, new `user_at_sites`.
- `tests/access_helpers.py` — **new**, `site_rows()` shared helper.
- `tests/test_access_core.py` — **new**, pure tests (§ 8 Pure).
- `tests/test_site_roles_api.py` — **new**, site rows, login save, no-login rule, engineer limits, own access, visibility, legacy rows, logging.
- `tests/test_site_checks_api.py` — **new**, per-site writes, node permissions, removed documents by site.
- `tests/test_migration_v8.py` — **new**, v8 run twice on legacy rows.
- `tests/test_auth.py` — rewritten token cases (`maintenance_team`, 401 for old roles), login-only, inactive person, stale-role warning, DB down.
- `tests/test_rbac.py` — role matrix (supervisor, manager without `read_all_units`, `assign_technicians`), role-source invariants, `has_perm_at`, dev stub.
- `tests/test_equipment_api.py` — `/my-units` (`edit_unit_ids`, token roles only for every unit, manager all-units-of-site case), lower-case login case.
- `tests/test_masters_api.py` — `TestUserUnits` removed (covered by the site-role tests); unit freeze cases on `person_units`; a "user-units routes are gone" case.
- `tests/test_masters_core.py` — site-row validators.
- `tests/test_people_api.py` — login saves carry `sites: []`; the own-login message.

Frontend:
- `src/stores/auth.js`, `src/App.vue`, `src/views/NoAccessView.vue` (**new**), `src/views/masters/PeoplePanel.vue`, `src/views/masters/useMasterForm.js` (exposes `send`), `src/views/MastersView.vue`, `src/views/masters/UserUnitsPanel.vue` (**deleted**), `src/views/EquipmentDetailView.vue`, `src/stores/equipment.js`, `src/utils/siteRoles.js` (**new**, labels), `tests/navigation.test.js`, `tests/siteRoles.test.js` (**new**).

Docs:
- `docs/Plan.MD` — § 1 Shop-floor access, § 2 (supervisor line removed from "Not in v1"), § 3 (roles paragraph, Supervisor row, the "no special role" sentence, unit access, matrix with a supervisor column and `people:assign_technicians`, `SITE_SCOPED` and key notes), § 5 (`memberships` by person, `person_units`, `user_units` legacy), § 9.11.
- `docs/Maintenance-Philosophy.md` § 11 — supervisor; roles on the person in Team.
- `docs/Keycloak.md` § 3.2, § 4, § 5 (one line), § 6, § 7 — "User access" → Team.
- `docs/steps/README.md` index row; `docs/steps/S011-site-roles/1-brief.md` status.
- Outside the repo: `smtw_erp_devops/docs/lob-apps/Yantra.MD` step 5 (client roles and switch-over). The user commits it.

## 4. Decisions taken

### 4.1 Choices the brief did not settle
1. **`compute_permissions` and `expand_roles` moved into `access_core`** (pure), re-exported by `auth_utils` so callers are unchanged. The core needs them and must not import Flask.
2. **Lazy imports in `auth_utils`** of `db_helpers` and `api_common`: `config.py` imports `auth_utils`, and both modules import `config`, so a top-level import is a cycle.
3. **`g.user["roles"]` lists `maintenance_team` too** (e.g. `["it_admin", "maintenance_team"]`); `g.user["role"]` is the token-only display role (for logs); `/auth/me` computes the combined one.
4. **Stale roles** = the token's roles that are site-role names (`maint_*`).
5. **`/auth/me` shows a wildcard membership** (dev stub, tests) as `site_id: null, site_code: null`.
6. **`load_node_for_user` takes `key` on plain reads too**; the upload's early read uses it, so a refused upload writes no file. Writes still check again under the lock.
7. **The site check in `load_node_for_user` comes before the route's scrapped 409** (brief § 5.4: "after the existing 404"): a user without edit at that site gets 403 for a scrapped node too. In `_load_target_node` / `_lock_target_unit` the check is last, after 409 and level 400, as the brief says.
8. **`sites` in `POST`/`PUT /people` is accepted only together with `username`**: required when the login is set, changed or cleared; `sites` without `username` → 400 field `sites` ("saved one site at a time"). A `POST` with `username: null` may carry Technician-only rows.
9. **Error fields**: whole-set unknown/inactive site, duplicate site, bad shape → `sites`; bad `site_id` → `site_id`; per-site route unknown/inactive site → `site_id`; role rules → `role`; units → `unit_ids`; own-person → the field being changed (`username`, `active`, `sites`).
10. **An engineer may delete a legacy (role-less) row at their site** (`technician_only(None, None)` holds); it grants nothing anyway.
11. **`assignable_site_ids`** = active sites where the actor may add a row, minus sites the person already has a row at; IT admin gets every active site; `[]` for one's own person. `editable` is false on one's own person.
12. **No-login rule order**: after the unit checks (all 400s, before any 403).
13. **Frontend: site rows are edited on an existing person only.** "Add person" shows "Save the person first, then add their sites and roles"; an IT admin creating a person with a login sends `sites: []` (no access) and adds roles on edit. Avoids guessing an engineer's assignable sites for a record that does not exist yet.
14. **Frontend role labels** (`utils/siteRoles.js`) are display-only; the backend validates every role.
15. **Frontend: choosing Manager on a row without units switches All units on** (§ 5.3 "ticks it by default when the role is manager").
16. **After a row refusal the form is kept** (the user's other edits stay) and the person is reloaded as the baseline, so a retry sends only what is still different.
17. **`_check_grantable` reads `SELECT *` and returns the locked rows**, so the unit check can test the unit's site without a second query (trades use it unchanged).
18. **`useMasterForm` exposes `send`** for the Team dialog's multi-request save.
19. **Test harness**: `X-Test-Role: <site role>` → token roles `["maintenance_team"]` + wildcard; `it_admin`/`admin`/`maintenance_team` → token roles + DB memberships; anything else → no role and no membership. `user_with_units` creates a person named `User <login>` with that login and the role at the units' sites. Shared `site_rows()` lives in `tests/access_helpers.py` (pytest advises against importing from conftest).
20. **The Equipment list's "Add equipment" button and Settings' removed-documents section stay on the global key** (held somewhere); the pickers and the list are scoped. As the brief's § 3 Frontend.

### 4.2 Changes to S010 behaviour (all required by S011 A1)
1. A login set, changed or cleared now requires `sites` (A1 rule 1; gate A for clearing). S010's tests that set logins now send `sites: []`; `make_person(username=…)` does so too.
2. The own-login refusal now reads "You can't give yourself a login" (A1 rule 4; was "You can't set your own login").
3. On one's own person, changing the login or `active` → 403 "You can't change your own access" (A1 rules 2, 4).
4. `GET /people` and every people response carry `sites` and `assignable_site_ids` for `people:edit` holders.
5. `_check_grantable` returns the locked rows (no behaviour change for trades).
6. `useMasterForm` returns `send`; `PeoplePanel.vue` gained the site-row UI and a custom save; the Masters "Unit access" section (S001's `UserUnitsPanel.vue`) is removed (A1 point 6).

### 4.3 Departures from the brief
1. **`.claude/CLAUDE.md` not edited.** The brief asks to record the RBAC deviation there, but as a subagent I may not change CLAUDE.md on an agent's instruction. Proposed text for the user to add under "Yantra Specifics":
   > - **RBAC deviation (S011)**: roles do not all come from the token. Keycloak gives only `maintenance_team` (may log in, grants nothing), `it_admin` and admin (`mspv-apps-admin`). The maintenance roles (`config_rbac.SITE_ROLES`) are held in Yantra per person and site (`memberships`, `person_units`; Team in Masters) and are read lazily per request. Keys in `config_rbac.SITE_SCOPED` are checked at the record's site (`has_perm_at`, `accessible_unit_ids(cur, key)`); others use the union. `config_rbac.py` stays the single source of roles and keys; fail-closed and the admin bypass are unchanged. New site-scoped keys must be added to `SITE_SCOPED`.
2. **"Class document upload → 200 (global)"** (§ 8) is not tested: class documents were S009, which was dropped.
3. **The "locked check" race** (A1 tests: engineer's write after IT admin's committed login save) is tested sequentially (IT admin's save committed, then the engineer's write refused on the stored row); no two-connection concurrency test.

## 5. Not done, deferred or assumed
- `user_units` is not dropped (A1 rule 3; queued in the README).
- Plan.MD § 4.1, § 6, § 8 still say "users' unit access" in passing; left as general wording.
- I did not run the app in a browser; the dialog and NoAccessView are checked by build only. See the manual checks.
- The test DB keeps the person created by the migration test (`created_by = 'migration-v8'`); harmless, the session start empties the tables.
- New files are written with LF line endings; git's `autocrlf` normalises them.

### 5.1 Production switch-over (§ 5.7), with the Keycloak screens
1. **Keycloak first** (admin console, realm `Office.smtw.in`):
   - Clients › `vel-yantra-master` › **Roles** › *Create role* › name `maintenance_team` › Save.
   - Groups › *Create group* `Yantra maintenance` › open it › **Role mapping** › *Assign role* › filter *by clients* › tick `vel-yantra-master maintenance_team` › Assign.
   - Users › each maintenance user › **Groups** › *Join group* › `Yantra maintenance`. (Operators who are local users too.) Harmless before the deploy: today's release ignores the role.
2. **Deploy S011** (migration v8 runs at startup). Maintenance users see "You have no access yet" until step 3; IT admin works as before.
3. **IT admin enters roles** in Yantra › Masters › **Team**: every old unit-access username already has a person (named after the username, `created_by = migration-v8`) with its units shown and no role; open it, give each site a role, save; rename the person. People with no Team record are added with their login. Engineers can then add Technicians at their own sites.
4. **Remove the old roles** once every user has access **and** a rollback is no longer wanted: Clients › `vel-yantra-master` › Roles › tick `maint_operator`, `maint_technician`, `maint_engineer`, `maint_manager`, `maint_storekeeper` › Delete. The backend's WARNING lines ("still carries old Keycloak roles") show who still has them.

## Manual checks

Important (to be ticked or explicitly skipped by the user before Done):
- [ ] Only `maintenance_team`, no site role → the "no access yet" page, with name and Sign out in the top bar.
- [ ] As IT admin, in Team: give a test person with a login Manager at SMTW (all units) and Engineer at VEL (one unit); as them: SMTW all units, edit everywhere there; VEL one unit, edit there; other VEL units invisible.
- [ ] Change the VEL role to Operator: edit buttons on VEL equipment gone after a page load; a direct edit refused (403).
- [ ] The production switch-over of § 5.1 above, in that order.

Also (plain):
- The Team dialog asks before discarding changes (S007), including after a site-row change only.
- Legacy unit rows (migration v8) show with "No role"; the first save gives them a role.
- As an engineer at SMTW: add a Technician row at SMTW for a person with and without a login; the role select offers only Technician; VEL rows of a person with a login are not shown; an Operator row at SMTW is read-only.
- As IT admin: set a login on a person with site rows — the "Adding this login gives access as: …" line lists them; clearing a Manager's login is refused until only Technician rows remain.
- With the DB stopped: IT admin sees the normal app and Settings › Database; a maintenance user sees "The database is unavailable — try again shortly".
- `DEV_STUB_ROLE = "maintenance_team"` shows the no-access page; `"maint_engineer"` gives engineer everywhere.

## Fix rounds

### Round 1

Tests after the round: backend 894 passed (was 891; three new cases), frontend 38 passed; `npx vite build` clean.

- **CR1-01 — Fixed.** The login-save line now reads `login saved: actor=… person=… 'name' login=<before>-><after> before=[…] after=[…]`, same row format as the per-site line. `update_person` reads the stored rows in the transaction just before `_replace_site_rows` and takes the old login from the locked row; `create_person` logs `-` and no rows as the before side. Tests: the "logged once" test updated; new `test_login_change_and_clear_log_both_sides` (change `a->b`, then clear `b->-`, both halves asserted). Files: `backend/masters.py`, `backend/tests/test_site_roles_api.py`.
- **CR1-02 — Fixed by the orchestrator in .claude/CLAUDE.md.**
- **CR1-03 — Fixed.** Two cases added to `TestLoginSave`: `test_unknown_unit_id_is_400_on_both_routes` (whole-set save and `PUT …/sites/<id>` give 400 `unit_ids`, nothing written) and `test_whole_set_with_a_failing_second_row_writes_nothing` (valid first row, second row with a unit of another site, on a person who already has a row: 400, login and rows unchanged). Both passed without code changes.
- **CR1-04 — Fixed.** `access_core._valid` is now public `valid_memberships`; `auth_utils.membership_sites` and `_unit_pools` use it. `put_person_site` calls `no_login_role_error` once.
- **CR1-05 — Fixed.** conftest helper renamed `harness_user`; its one caller (`_inject_test_user`) updated.
- **CR1-06 — Fixed.** `smtw_erp_devops/docs/lob-apps/Yantra.MD` step 5 again says "PKCE; redirect URI `https://vel-yantra.mspv.app/*`". Outside the repo; the user commits it.

### Round 2

Tests after the round: backend 895 passed, frontend 38 passed.

- **CR2-01 — Fixed.** The `login saved` line is now written whenever the site rows are replaced (`sites is not None`), in both `update_person` and `create_person`, not only when the login changes. Same format: `login=<old>-><new> before=[…] after=[…]`; an unchanged login shows as `ravi->ravi`, a POST without a login as `-->-`. The API is unchanged (no new 400); a POST with `sites` still needs `"username"` in the body (`null` for none). New test `test_rows_replaced_with_the_login_unchanged_or_absent_are_logged` (PUT with the same login plus sites; POST with `username: null` and Technician rows). Files: `backend/masters.py`, `backend/tests/test_site_roles_api.py`.
