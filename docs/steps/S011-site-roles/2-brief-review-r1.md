```
Step: S011 — Roles per site, held in Yantra
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S011 — Brief review, round 1

**Verdict: not ready — four `major` findings are open** (BR1-01 to BR1-04).
No blocker. The design itself (roles per site in Yantra, token roles for login
and IT admin, `require_perm` as the cheap check plus `require_perm_at` on the
record) is sound and follows the user's decisions. The majors are about things
the coder would otherwise have to decide alone: the DB-unavailable path, the
test harness, a read that is not site-scoped, and the production switch-over
text.

Read for this review: the brief; `docs/Plan.MD` § 1, § 3, § 5;
`docs/Maintenance-Philosophy.md` § 11; `docs/Plant-Facts.md` § 2;
`.claude/CLAUDE-COMMON.md` § RBAC Pattern; `.claude/SMTW-WebApp-Base.md` § RBAC
Pattern; `.claude/CLAUDE.md`; S010's brief; the working-tree code:
`backend/auth_utils.py`, `config_rbac.py`, `app.py`, `equipment.py`,
`documents.py` (S008 and S009 routes included), `masters.py`, `masters_core.py`,
`settings.py`, `local_db.py`, `db_helpers.py`, `api_common.py`, `config.py`,
`example_secrets_app.py`, `tests/conftest.py`, `test_rbac.py`, `test_auth.py`,
`test_equipment_api.py` (unit access, permissions, my-units), `test_masters_api.py`
(user units, permissions), `test_documents_api.py`, `test_removed_documents_api.py`;
`frontend/src/stores/auth.js`, `stores/equipment.js`, `stores/navigation.js`,
`router/index.js`, `App.vue`, `views/EquipmentView.vue`,
`views/EquipmentDetailView.vue`, `views/equipment/EquipmentFormModal.vue`,
`views/equipment/EquipmentMoveModal.vue`, `views/MastersView.vue`,
`views/SettingsView.vue`, `views/masters/UserUnitsPanel.vue`,
`components/documents/DocumentsCards.vue`, `tests/navigation.test.js`;
`smtw_erp_devops/docs/lob-apps/Yantra.MD`.

---

## Major

### BR1-01 — `major` — Memberships in `require_auth` break "the app must serve while the DB is unreachable"

**Problem.** § 3 puts the membership query in `require_auth` ("loads the user's
memberships once per request into `g.user`"). Today `require_auth` touches no
database: `get_db()` is called only inside routes, and `DBUnavailable` becomes a
503 for that route alone. `/api/auth/me` and `/api/settings/db-status` work
with the database down — `db_status()` never raises, and that card is how IT
sees "Not reachable". With the query in the before-request handler, every
authenticated request 503s while the DB is down, including `/api/auth/me`, so
`loadProfile()` fails, `authError` shows "Could not load your profile" and the
shell never renders. IT admin cannot reach Settings › Database to see why. That
contradicts `.claude/CLAUDE.md` ("the app must start and serve while the DB is
unreachable or not created"), which the orchestrator asked me to check, and the
brief does not mention it.

**Why it matters.** A fresh deploy or a DB outage turns into "Yantra is down"
for everyone, with no diagnostic page.

**Options.**
1. **Load memberships lazily (recommended).** `require_auth` stays DB-free and
   builds `g.user` from the token (token roles, `permissions` of the token
   roles). A cached loader `_memberships()` runs the one query on first need —
   from `has_perm`/`has_perm_at` when the token roles alone do not grant the
   key, from `accessible_unit_ids`, and from `/auth/me`. A `DBUnavailable` there
   is the same 503 the route would have raised anyway. `/api/auth/me` catches
   `DBUnavailable` and answers 200 with the token permissions, `sites: null`
   and `db_unavailable: true`; the frontend then shows the shell for token-role
   holders (IT admin reaches Settings › Database) and, for a
   `maintenance_team`-only user, a "The database is unavailable — try again
   shortly" message instead of the misleading "no access yet". Write a test
   with `ensure_schema` monkeypatched to return an error.
2. Keep the query in `require_auth`, but catch `DBUnavailable` there: token-role
   holders continue with no memberships and a flag; others get 503. Works, but
   puts a DB call in a before-request handler for every thumbnail request and
   needs the same `/auth/me` flag anyway.

Either way, § 3 (`auth_utils.py`), § 5.2 and § 8 need the rule and the test.

### BR1-02 — `major` — The test harness and the existing tests: the mechanism is not specified, and several suites break regardless

**Problem.** § 5.8 says `X-Test-Role: <site role>` "keeps today's meaning: that
role at every site", and § 8 says "existing suites pass". The brief does not
say how a role *at every site* is represented, and some existing tests change
meaning whatever the harness does.

(a) **Representation.** `access_core.permissions_at(site_id)` works from
memberships keyed by `site_id`. "That role at every site" (also `DEV_STUB_ROLE`
in § 5.8) needs either a wildcard membership or a query of the `sites` table at
inject time. The coder must not decide this alone: it shapes the core's input.

(b) **DB memberships vs the header.** `user_with_units(role, units)` in
`conftest.py` writes rows through `PUT /user-units`, which is removed (§ 6). The
replacement `PUT /user-access` needs a role per site, so the fixture now writes
*memberships* too. When a request then carries `X-Test-Role: maint_engineer`
and the DB holds a membership for the same user, which wins? And the new
`X-Test-Memberships` header puts memberships in `g.user` while the units still
come from `user_units` rows in the DB — two sources for one test user.

(c) **Tests that break regardless** (the brief says "existing suites pass"):
- `test_auth.py`: `test_storekeeper_client_role_accepted`,
  `test_realm_role_maps_to_user`, `test_multiple_roles_primary_is_most_privileged`,
  `test_valid_bearer_token_reaches_route` — tokens with only `maint_*` roles
  are now 401 (§ 5.1). § 3 lists `test_auth.py`, but § 8 should say these are
  rewritten, not kept.
- `test_rbac.py::test_role_matrix` — manager loses `equipment:read_all_units`.
- `test_equipment_api.py::TestMyUnits::test_senior_roles_get_all_units` — a
  manager with `all_units` at every site is no longer `{"all_units": true,
  "unit_ids": []}` unless the code special-cases "all units everywhere"; see
  BR1-09 for what `/my-units` should return.
- `test_masters_api.py`: `test_unit_with_access_rows_cannot_change_code_or_site`,
  `test_unchanged_code_or_site_is_accepted_when_in_use` (lines 248, 256),
  `test_only_it_admin_writes_sites_units_and_access` (line 617, expects 403 on
  a path that will 404) and `test_only_it_admin_reads_user_units` (line 641) all
  call `/user-units`. They are not "user-units cases" that move to
  `test_user_access_api.py`; they must be re-pointed.
- `frontend/tests/navigation.test.js`: `MANAGER` holds
  `equipment:read_all_units` (listed in § 3, fine — just naming it here).

**Options.**
1. **Wildcard in the core, memberships from the DB in tests (recommended).**
   - `access_core` takes memberships as `(site_id | None, role, all_units)`;
     `site_id = None` means every site. `DEV_STUB_ROLE` → `[(None, role, True)]`.
   - `X-Test-Role: <site role>` → `[(None, role, role == "maint_manager")]`;
     the user's `user_units` rows are read from the DB as in production (the
     wildcard covers every site, so every row counts). DB memberships are
     ignored under this header, so legacy tests mean exactly what they mean
     today.
   - `X-Test-Role: maintenance_team` (+ `X-Test-User`) → login only;
     memberships and units come from the DB, as in production. The new per-site
     cases set them with the real `PUT /user-access` — which is itself under
     test — and need no `X-Test-Memberships` header at all. Drop that header.
   - `user_with_units(role, units)` groups the units by site and PUTs
     `{sites: [{site_id, role, all_units: false, unit_ids}]}`; a new
     `user_at_sites(spec)` fixture serves the per-site cases.
   - § 8 lists the rewritten cases above.
2. Keep `X-Test-Memberships` and make the harness query `sites` for the
   "every site" expansion. More moving parts, and the per-site tests would then
   not exercise `PUT /user-access`.

### BR1-03 — `major` — Reads gated by a senior key must be scoped to the sites where the key is held: the removed-documents list

**Problem.** § 5.4 scopes the *writes* (purge, restore) to the document's
node's site. `GET /api/equipment/removed-documents` (`documents.py`
`list_removed_documents`) is a read guarded by `require_perm("equipment:purge_documents")`
("holds it somewhere") and filtered by `accessible_unit_ids` — which, after
S011, is the union of the user's units at *every* site. A manager at SMTW who
is operator at VEL would list VEL's removed documents (titles, who removed them,
when) while being refused the purge. S008 made that list senior-only on
purpose (ISO 27001 A.5.3 / A.8.2: disposition kept apart from everyday work).

The same shape recurs for `edit_unit_ids` in `/my-units` (§ 6) and will recur
for every phase-3 list ("tickets I may close").

**Options.**
1. **One function, keyed by permission (recommended).**
   `accessible_unit_ids(cur, key="equipment:read")` → `None` for admin and
   `equipment:read_all_units` holders, else the active units of the sites where
   `has_perm_at(key, site)` holds (all units of the site when `all_units`, else
   the user's rows). The removed-documents list calls it with
   `"equipment:purge_documents"`; `/my-units` computes `edit_unit_ids` with
   `"equipment:edit"`; the equipment list keeps `"equipment:read"`. State it in
   § 3 and § 5.3, and add the test: manager at A, operator at B, a removed
   document at B → not listed, purge → 403.
2. Leave the list as is and only block the write. Rejected: it leaks a senior
   view at a site where the user is not senior.

### BR1-04 — `major` — § 5.7 misstates what users see after step 1, and the order should be the other way round

**Problem.** § 5.7 step 1: "Deploy S011. Users with only old `maint_*` roles
now see `NoAccessView`." Not so: by § 5.1 a token with none of `admin`,
`it_admin`, `maintenance_team` is **401**, and `auth.js` then shows "You are
signed in, but your account has no Yantra role. Ask IT to assign one."
`NoAccessView` is for `maintenance_team` *without* a membership. Followed as
written, step 1 locks every maintenance user out with a message that points
IT at Keycloak roles, when the fix is a Yantra membership.

**Why it matters.** This is the plan the user will execute on production. It
should say exactly what happens at each step.

**Options.**
1. **Keycloak first (recommended).** (1) In Keycloak create client role
   `maintenance_team` on `vel-yantra-master` and give it to every maintenance
   user (a group); harmless before the deploy, since today's
   `validate_keycloak_token` ignores roles not in `ROLES`. (2) Deploy S011:
   users log in and see `NoAccessView` ("ask IT to add you") until (3) IT admin
   enters memberships in User access. (4) Remove the old `maint_*` client roles
   once every user has a membership (the INFO log line of § 5.1 shows who still
   carries them). State the gap between (2) and (3) and that it is short.
2. Keep the brief's order but correct the text: step 1 gives 401 "no Yantra
   role", not `NoAccessView`. Worse for users, so not recommended.

Also: "the brief's report gives the exact steps" presumably means the
implementation report; and the 401 message in `auth.js` should now say
"your account is not in the maintenance team" (see BR1-11).

---

## Minor

### BR1-05 — `minor` — `maintenance_team` and the `('*',)` wildcard; what `role` / `roles` mean now

**Problem.** `compute_permissions` grants every `('*',)` key to any role in
`ROLES`. If `maintenance_team` were added to `ROLES` (it is a recognised token
role), a login-only user would get `equipment:read` and `masters:read`,
contradicting § 8 ("no data permissions") and the fail-closed rule. The brief
names `TOKEN_ROLES`, `LOGIN_ROLE` and `SITE_ROLES` but does not say what
happens to `ROLES`, nor what `g.user["role"]` / `"roles"` (used by `/auth/me`,
the 403 log line in `require_perm`, `userRole` in `auth.js`) hold for a user
whose roles differ per site.

**Recommendation.** State: `ROLES` is unchanged (the six roles, for ordering
and the wildcard); `LOGIN_ROLE` is *not* in `ROLES` and grants nothing;
`compute_permissions(["maintenance_team"]) == []` (a `test_rbac` case).
`g.user["roles"]` = the token roles; `g.user["role"]` = the most privileged of
the token roles and site roles (by `ROLES` order), for display and logging
only; `/auth/me` keeps both. Note that `('*',)` at a site means "any site role
at that site" in `has_perm_at`.

### BR1-06 — `minor` — Legacy `user_units` rows after v9 are invisible, yet still freeze their units

**Problem.** Production already holds `user_units` rows (S001). § 4 keeps the
table and says a row "counts only when the user has a membership at that
unit's site with `all_units = 0`". After v9 no membership exists, so those rows
grant nothing — but `GET /user-access` (built from memberships, § 6) will not
show them, so IT admin re-enters the units from memory, and
`_unit_is_referenced` (`masters.py`) still counts the orphan rows, keeping the
units' codes frozen. The brief's "no data move" does not say either way.

**Options.**
1. **Show them (recommended).** `GET /user-access` lists users from
   `memberships ∪ user_units`; a site with unit rows and no membership appears
   with `role: null`, and the dialog asks for a role before saving. The PUT
   replaces everything, so orphan rows disappear on the first save.
2. Migration v9 deletes `user_units` rows (logged). Simpler, loses S001 data.
3. Leave as is and say so. The user re-enters a few users' units (few exist).

### BR1-07 — `minor` — Lock order of `PUT /user-access` can deadlock with `update_unit`

**Problem.** § 5.5: the user's rows `FOR UPDATE`, "then the sites and units".
`masters.py::update_unit` locks the **unit** row first (`_lock_row`) and then
the **site** (`_lock_site_for_unit`) on a site change or reactivation. Site →
unit in the new route against unit → site in `update_unit` is a lock cycle
(IT admin doing both at once; rare, but a 1213 error rather than a clean
answer). `equipment.py`'s module docstring records the cross-module lock order
and says masters "never locks equipment … takes a class before a type";
memberships/sites must be added to it.

**Recommendation.** Order: the user's `memberships` and `user_units` rows →
units (`_check_grantable`, as today) → sites; or read the sites' `active` flag
without a lock (a site cannot be deactivated while it has active units, and a
membership at an inactive site is allowed to exist, so the race is harmless).
State the order in § 5.5 and update the docstring in `equipment.py`.

### BR1-08 — `minor` — `role ENUM(...)` is a second source of truth for the role list

**Problem.** § 4 defines `memberships.role` as an `ENUM` of the five roles.
`config_rbac.py` is "the single source of truth for roles and permissions"
(CLAUDE-COMMON § RBAC Pattern). A sixth site role (the supervisor, if it ever
comes) would need both a code change and a migration, and the two can drift.

**Options.**
1. **`VARCHAR(30) NOT NULL`, validated against `SITE_ROLES` in
   `validate_user_access` (recommended).** One list; a `test_rbac` case that
   `SITE_ROLES ⊂ ROLES`.
2. Keep the ENUM and record in § 7 that adding a role is a migration.

### BR1-09 — `minor` — Shell details the coder should not decide alone

- **§ 5.4 list is incomplete.** Add: creating a *part* checks the parent's
  site (`_load_target_node`); re-parenting checks the **new parent's** site as
  well as the node's (the move rule says "both", but only for units); the
  status change is a `PUT`, same as edit. Say that the site check comes after
  the existing 400/409/403 order of `_lock_target_unit` and
  `_load_target_node`, i.e. an unknown or inactive target still answers as
  today, and the per-site 403 message carries the site code.
- **Node `permissions`** (§ 6): say it is the user's *full* effective key list
  at that site (token keys ∪ the site role's keys, or every key for admin), not
  only `SITE_SCOPED`, so phase 3 can read `breakdown:raise` from it.
- **`/my-units` for a site-wide manager.** With `equipment:read_all_units`
  gone from the manager, a manager at SMTW (all units) gets `all_units: false`
  and `unit_ids` = SMTW's active units. Say so (it changes
  `test_senior_roles_get_all_units`, BR1-02). `filterableUnits` in
  `stores/equipment.js` offers inactive units only to `all_units` users (a
  deactivated unit may still hold scrapped equipment); a site-wide manager
  loses that for their own site — accept it or return a `filter_unit_ids`
  that includes inactive units of `all_units` sites. Accepting it is fine;
  record it.
- **`PUT /user-access` body details:** `unit_ids` de-duplicated as
  `validate_unit_ids`; `all_units` through `_flag_parser`; the INFO log line's
  format (`site:role:all|unit,unit`), and that it is written only when
  something changed (as `replace_user_units`).
- **`X-Test-User` casing test** (`test_username_is_compared_lower_case`) and
  the `actor().lower()` call in `accessible_unit_ids`: say memberships are
  looked up by the normalised username, as `user_units`.

### BR1-10 — `minor` — Docs to update, and two standards notes

- **`docs/Maintenance-Philosophy.md` § 11** says "Everyone except the manager
  works only at the units they are given" and "Maintenance manager — all units,
  reports". After S011 the manager sees all units *of their site(s)* (§ 5.3,
  § 9.3). § 3 lists Plan.MD but not this file; add it.
- **Plan § 1 Login row** ("Keycloak supplies role membership") and **§ 3 first
  line** ("Roles come from Keycloak. A user may hold several") and **§ 9 Q1**
  (client roles `maint_operator` …) all change; § 3 lists "§ 1, § 3, § 5" —
  name Q1 too.
- **ISO 55001.** The brief cites ISO 55001:2014 § 5.3. ISO 55001 was reissued
  in 2024 (ISO 55001:2024); clause 5.3 keeps the same title, "Organizational
  roles, responsibilities and authorities". Cite the 2024 edition (S010 has the
  same note coming). The plain-terms reading — responsibilities for assets are
  assigned per plant, and the system should model that — is right.
- **ISO 27001:2022 A.8.3 (information access restriction)** is the control
  that says access to information is restricted *in line with the access
  policy* — it is the one the per-site check in code implements, and
  `documents.py` already cites it. Worth naming beside A.5.15 (the policy) and
  A.5.18 (the provisioning). The A.5.15 / A.5.18 / A.5.3 / A.8.2 / A.8.15
  readings in § 2 are accurate: A.5.15 = rules for who may access what, on
  business need; A.5.18 = rights are granted, reviewed, changed and removed in
  a controlled way (joiners, movers, leavers); A.5.3 = conflicting duties kept
  apart (doers do not grant); A.8.2 = privileged rights restricted and managed;
  A.8.15 = events logged and kept.

### BR1-11 — `minor` — `NoAccessView`: trigger, sign-out, and the two "no access" messages

**Problem.** § 3 says `NoAccessView` is "shown when the user has no membership
and no token role" but not how the frontend knows: today `landingPath([])` is
`null`, the `/` redirect falls back to `/equipment`, and the list would show a
403. Plan § 3 (shared-device login) requires every screen to show who is logged
in with a large logout button, so the page must not replace the shell silently.
Two messages now exist for two causes — 401 (not in `maintenance_team`: "ask IT
to add you to the maintenance team in Keycloak") and 200 with no permissions
(no membership: "ask IT to add you in Yantra › Masters › User access") — and
`auth.js`'s 401 text still says "has no Yantra role".

**Recommendation.** Trigger = `authenticated && userPermissions.length === 0`
(and not `db_unavailable`, BR1-01); `App.vue` renders `NoAccessView` inside
the shell (top bar with name and Sign out, no nav items); the 401 text in
`auth.js` is reworded; `userSites` — say what uses it (the view, a profile
line?) or drop it (CLAUDE-COMMON: nothing beyond the agreed scope).

---

## Nit

### BR1-12 — `nit` — Small points

- `conftest._TABLES`: add `memberships` (after `user_units`, before `sites`).
- "logged once per user at INFO" (§ 5.1): the set of seen usernames is per
  worker process; say "once per user per worker" or just log at WARNING on
  every login — the list is short.
- § 5.1: `maintenance_team` is accepted from realm *or* client roles, as all
  roles today (`all_roles = realm ∪ client`); say "client role (realm also
  accepted)" so the Keycloak doc and the code agree.
- § 6 `GET /user-access` `units`: give the shape (`[{id, full_code, name,
  active}]`, as today's `_unit_summary`).
- § 5.6: when "All units" is switched on, the dialog clears and disables the
  unit checkboxes (the API refuses `unit_ids` with `all_units`).
- § 3 says the devops doc edit "the coder edits that working tree, the devops
  team commits (as S007)" — the user commits that repo; "the user commits".

---

## Checked and found consistent

- The user decisions (two Keycloak client roles, five site roles, one role per
  site plus units with "all units", IT admin alone grants, no supervisor) are
  carried through §§ 1, 4, 5 and 7 without contradiction.
- `config_rbac.py` stays the single source of `PERMISSIONS`; route code names
  only keys; admin bypass, fail-closed and the `('*',)` rule are kept; the
  departure (maintenance roles from the DB, per site) is named in § 2 and
  recorded in `.claude/CLAUDE.md`, as CLAUDE-COMMON allows.
- `require_perm` first ("holds it somewhere"), then the existing unit-access
  check (404 outside the user's units), then `require_perm_at` at the record's
  site (403) — the order keeps S002's "nothing is revealed" rule.
- Class and type documents (S009) stay global: classes and types belong to no
  site; `masters.py` class/type writes keep the global `equipment:edit`;
  S010's `technicians:edit` stays global (§ 5.2, § 9.5), matching S010's note
  that S011 changes evaluation, not S010's rules.
- `it_admin` keeps every current key everywhere from the token, including
  `equipment:read_all_units` and `equipment:purge_documents`; `admin` bypasses.
- `user_units` kept as the within-site unit list; the existing unit-code freeze
  (`_unit_is_referenced`) still protects the "row counts at the unit's site"
  rule, since a unit with rows cannot change site.
- `PUT /user-access` replaces atomically with a diff, so kept rows keep
  `granted_at/by`; inactive sites and units kept but not newly granted,
  matching `_check_grantable`.
- Migration numbering (v9 after S010's v8) and the "each statement safe to run
  twice" convention are consistent with `local_db.py`.
- The pure/shell split: `access_core.py` and `validate_user_access` are plain
  data in and out; the shell fetches memberships and units.
- Plan § 3's permission matrix changes only in `equipment:read_all_units`
  (manager → IT admin only), and the brief says Plan § 3 is updated at
  approval.
