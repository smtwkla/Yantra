```
Step: S011 — Roles per site, held in Yantra
Doc: brief
Author: Planner (Opus)
Date: 16-10-2026 (revised 16-10-2026 after brief-reviews r1, r2 and r3)
Status: Approved 16-10-2026 by KLA
```

# S011 — Roles per site, held in Yantra

Today Keycloak holds each user's maintenance role (`maint_engineer`, …) as a
client role of `vel-yantra-master`, and the role applies at every site. Yantra
holds only *where* (unit access, S001). The plant needs roles **per site**:
someone can be manager at SMTW and engineer at VEL. Keycloak client roles are
global and can't say that, and every role change today needs the Keycloak
administrator.

This step moves the maintenance roles into Yantra, per site, next to unit
access. Keycloak keeps only who may log in at all, and IT admin.

**Depends on:** S010 committed (migration v8); this step is migration **v9**.
It changes the RBAC core, so it is coded on **Opus** and is best done before
phase 3 (breakdowns), while only masters and equipment use roles.

User decisions taken while planning (16-10-2026):
- **Keycloak** keeps two client roles: `maintenance_team` (may log in) and
  `it_admin`. The org-wide realm role `mspv-apps-admin` still maps to `admin`
  (bypass), as today.
- **In Yantra**, per user and site: one role out of `maint_manager`,
  `maint_engineer`, `maint_technician`, `maint_operator`, `maint_storekeeper`.
- **A role per site, plus units within the site** (as unit access today), with
  an "all units of the site" option.
- **Only IT admin** grants and changes memberships.
- **No supervisor role** until it is defined (Plan § 3, decided 13-10-2026,
  stands).

Background reading:
- `docs/Plan.MD` § 1 (Login, Shop-floor access), § 3 (roles, unit access,
  shared-device login, the permission matrix), § 9 Q1;
- `docs/Maintenance-Philosophy.md` § 11 (who works where);
- `.claude/CLAUDE.md` ("DB may not exist": the app serves while the DB is
  unreachable); `.claude/CLAUDE-COMMON.md` § RBAC Pattern;
  `.claude/SMTW-WebApp-Base.md` § RBAC;
- `backend/auth_utils.py`, `backend/config_rbac.py`, `backend/equipment.py`
  (`accessible_unit_ids`, `load_node_for_user`, `_load_target_node`,
  `_lock_target_unit`, `/my-units`, the lock-order docstring),
  `backend/documents.py` (incl. S008's removed-documents routes and S009's
  class/type documents), `backend/masters.py` (user units, `update_unit`),
  `backend/app.py` (`/api/auth/me`), `backend/tests/conftest.py`
  (`X-Test-Role`, `user_with_units`);
- `frontend/src/stores/auth.js`, `frontend/src/App.vue`,
  `frontend/src/stores/equipment.js`, `frontend/src/views/masters/UserUnitsPanel.vue`.

## 1. What will be built

1. **Memberships.** For each user: a list of sites, each with **one role** and
   either **all units of the site** or a chosen set of its units.
2. **Permissions follow the site.** At a piece of equipment, a user's rights
   are those of their role **at that equipment's site**. An engineer at VEL
   who is an operator at SMTW can edit VEL equipment and only view SMTW's.
   Lists that need a senior key (removed documents) show only the sites where
   the user holds that key.
3. **The "Unit access" section becomes "User access"** (Masters, IT admin): per
   user, their sites with role, all-units or units; saved in one go, every
   change logged.
4. **Keycloak becomes simpler.** A user needs `maintenance_team` (or `it_admin`)
   to log in. A user with `maintenance_team` but no membership logs in and sees
   "You have no access yet — ask IT to add you in User access", inside the
   normal top bar (name, Sign out).
5. **IT admin and admin stay global**, from Keycloak, as today: IT admin keeps
   its current rights at every site.
6. **The app still serves while the database is down**: IT admin can still
   open Settings › Database; a maintenance user sees "The database is
   unavailable — try again shortly".

**Out of scope:**
- a supervisor role (above);
- managers granting roles at their own site (user: IT admin only);
- reading the old Keycloak client roles, or converting them: IT admin enters
  memberships (§ 5.7);
- several roles at one site for one user (§ 9.1);
- an access-review report or periodic review reminders (A.5.18 asks for
  reviews; the User access screen is what the review looks at);
- breakdown, PM and report permissions: their keys arrive with phases 3–5 and
  are site-scoped from the start (§ 5.2).

## 2. Standards and practice

- **ISO 27001:2022 A.5.15 (access control)**: rules for who may access what,
  on business need, and **A.5.18 (access rights)**: rights are granted,
  reviewed, changed and removed in a controlled way (joiners, movers,
  leavers). In plain terms: someone who works at one plant gets rights at
  that plant only, and the place where rights are granted is also where they
  are reviewed. Moving roles next to unit access puts *who*, *what* and
  *where* on one screen, with a log of every change.
- **ISO 27001:2022 A.8.3 (information access restriction)**: access to
  information is restricted in line with that policy. It is the control the
  per-site checks in code implement (§ 5.2–5.4), as `documents.py` already
  cites it.
- **ISO 27001:2022 A.5.3 (segregation of duties) and A.8.2 (privileged access
  rights).** The people who do maintenance don't grant themselves rights: only
  IT admin edits memberships. IT admin itself and admin are **not** grantable
  in Yantra; they stay in Keycloak, so nobody can make themselves IT admin
  through Yantra's database or screens.
- **ISO 27001:2022 A.8.15 (logging).** Each membership change is logged with
  actor, user, before and after, as unit access is today (S001).
- **ISO 55001:2024 § 5.3 (organizational roles, responsibilities and
  authorities)** asks that responsibilities and authorities for asset
  management be assigned and communicated. In a group with several plants they
  are assigned per plant: the SMTW manager answers for SMTW's assets. A role
  per site models that directly. (The 2014 edition has the same clause.)
- **Departure from the base RBAC pattern** (`CLAUDE-COMMON.md` § RBAC Pattern):
  the pattern takes roles from the identity provider's token. Here only
  `it_admin` and `admin` come from the token; the maintenance roles come from
  Yantra's database, per site. `config_rbac.py` stays the single source of
  roles and `PERMISSIONS` (the DB stores the role as text, validated against
  it); route code still names only permission keys; fail-closed, admin bypass
  and the role ladder are unchanged. Recorded in `.claude/CLAUDE.md`.

## 3. Where

### Backend
- **Migration v9** in `backend/local_db.py` (§ 4).
- **`backend/config_rbac.py`:**
  - `ROLES` unchanged (the six roles: order and the `('*',)` wildcard);
  - `TOKEN_ROLES = ("it_admin",)`; `LOGIN_ROLE = "maintenance_team"`, **not**
    in `ROLES`, grants nothing (§ 5.1); `SITE_ROLES` = the five maintenance
    roles (ladder unchanged);
  - `SITE_SCOPED` = the keys checked per site: `equipment:read`,
    `equipment:edit`, `equipment:purge_documents`. Every later breakdown, PM,
    reading and report key joins it;
  - `equipment:read_all_units` = `("it_admin",)`: managers get breadth from
    "all units of the site" (§ 5.3).
- **`backend/access_core.py`** (new, pure; plain data in and out). A
  membership is `(site_id | None, role, all_units)`; `site_id = None` means
  **every site** (the dev stub and the test harness, § 5.8). Functions:
  `global_permissions(token_roles, memberships)` (the union),
  `permissions_at(token_roles, memberships, site_id)`, and
  `unit_ids_for(key, token_roles, memberships, units, user_unit_ids)` → `None`
  (every unit) **only** when the user is admin, or the **token roles** grant
  both `key` and `equipment:read_all_units` (BR2-01); otherwise the active
  units of the sites where `key` is held there (all the site's units when
  `all_units`, else the user's rows). Rules of the core (BR2-06, BR2-07):
  - a membership whose role is not in `SITE_ROLES` (a typo, or `it_admin`
    written straight into the DB) is **ignored entirely**: it grants no key,
    wildcard or not, and no units (BR3-02);
  - a wildcard membership matches when *its* site is `None`; a query for site
    `None` matches no real membership (the shell asserts `site_id` is an int);
  - `user_unit_ids` are `(unit_id, site_id)` pairs;
  - `has_perm_at` (shell) and `unit_ids_for` assert `key in SITE_SCOPED`, so a
    global key checked at a site, or a new site key not added to the list, is
    a programming error seen in tests.
- **`backend/auth_utils.py`:**
  - token parsing accepts `admin`, `it_admin`, `maintenance_team` (realm or
    client roles, as all roles today); none → 401;
  - **`require_auth` stays DB-free**: `g.user` is built from the token (token
    roles and their permissions). Memberships are loaded **lazily**, once per
    request and cached in `g`, on first need: from `has_perm` / `has_perm_at`
    when the token roles alone don't grant the key, from
    `accessible_unit_ids`, and from `/auth/me` (BR1-01). The loader uses
    `get_db()` (the request's connection, so it shares a write transaction).
    Every active unit with its site is read (`SELECT id, site_id FROM units
    WHERE active = 1`) only when some membership has `all_units`;
  - the token parser keeps the ignored `maint_*` names in
    `g.user["stale_roles"]`;
  - `has_perm(key)` = "holds it somewhere"; new `has_perm_at(key, site_id)`
    and `require_perm_at(key, site_id)` (raises `ApiError` 403 "You can't do
    this at <site code>");
  - `g.user["roles"]` = the token roles; `g.user["role"]` = the most privileged
    of token and site roles (by `ROLES` order), for display only, computed
    where memberships are loaded (`/auth/me`); `null` for a login-only user
    with no membership. `require_perm`'s 403 log line uses the token roles
    plus whatever is cached, never forcing a DB read.
- **`backend/equipment.py`:** `accessible_unit_ids(cur, key="equipment:read")`
  through `access_core.unit_ids_for` (one function, keyed by permission;
  BR1-03); the site checks of § 5.4; the node detail returns `permissions`;
  `/my-units` adds `edit_unit_ids`; the module docstring's lock order gains
  memberships (§ 5.5).
- **`backend/documents.py`:** the site checks of § 5.4; the removed-documents
  list calls `accessible_unit_ids(cur, "equipment:purge_documents")`.
- **`backend/masters.py`:** `GET /user-access`, `PUT /user-access/<username>`
  replace `GET/PUT /user-units` (§ 5.5, § 6).
- **`backend/masters_core.py`:** `validate_user_access(body)` (pure; roles
  checked against `SITE_ROLES`, `unit_ids` as `validate_unit_ids`,
  `all_units` through `_flag_parser`).
- **`backend/app.py`:** `/api/auth/me` (§ 6), catching `DBUnavailable`.
- **`backend/tests/`:** `test_access_core.py` (new, pure),
  `test_user_access_api.py` (new); site-scoped cases in the equipment,
  documents and removed-documents API tests; the rewritten cases of § 8;
  `conftest.py` (§ 5.8; `memberships` in `_TABLES` after `user_units`, before
  `sites`).

### Frontend
- **`frontend/src/stores/auth.js`:** keeps `userPermissions` (global union);
  stores `dbUnavailable`; the 401 text becomes "Your account is not in the
  maintenance team. Ask IT to add you in Keycloak."
- **`frontend/src/App.vue`** + **`frontend/src/views/NoAccessView.vue`**
  (new): when `authenticated && userPermissions.length === 0`, the shell
  renders with the top bar (name, Sign out, per Plan § 3 shared-device rule)
  and no nav items, and the content is `NoAccessView`: "You have no access
  yet — ask IT to add you in User access", or, when `dbUnavailable`, "The
  database is unavailable — try again shortly".
- **`frontend/src/views/masters/UserAccessPanel.vue`** (replaces
  `UserUnitsPanel.vue`; § 5.6).
- **Equipment screens:** edit buttons on a node follow the node's
  `permissions`, not the global list; unit pickers for writes use
  `edit_unit_ids`.
- `navigation.test.js` (the manager loses `equipment:read_all_units`).
- No `userSites` store: nothing in this step needs the site list on the
  client beyond the panels, which read it from their own API.

### Docs and config
- `.claude/CLAUDE.md`: the RBAC deviation (§ 2) and the role sources.
- `docs/Plan.MD` § 1 (Login row), § 3 (first line "Roles come from Keycloak",
  roles, unit access, the matrix), § 5 (`memberships`), § 9 Q1; at approval.
- `docs/Maintenance-Philosophy.md` § 11: the manager sees all units *of their
  site(s)*; at approval.
- `smtw_erp_devops/docs/lob-apps/Yantra.MD` step 5: client roles
  `maintenance_team`, `it_admin`, and the switch-over of § 5.7. The coder edits
  that working tree; the user commits it.
- `backend/example_secrets_app.py`: the `DEV_STUB_ROLE` comment (§ 5.8).

## 4. Data model (migration v9)

**`memberships`**

| Column | Type / rule |
|---|---|
| `username` | `VARCHAR(100) NOT NULL` (normalised, as `user_units`) |
| `site_id` | `INT NOT NULL`, FK `fk_memberships_site` |
| `role` | `VARCHAR(30) NOT NULL`, validated against `config_rbac.SITE_ROLES` (one source of truth; BR1-08) |
| `all_units` | `TINYINT(1) NOT NULL DEFAULT 0` |
| `granted_at`, `granted_by` | first grant |
| `updated_at`, `updated_by` | last change of role or all-units |
| | `PRIMARY KEY (username, site_id)` |

- **`user_units` stays** as the units within a site. A row counts only when the
  user has a membership at that unit's site with `all_units = 0`.
- **No data migration:** the old roles live in Keycloak, which Yantra can't
  read; guessing them would grant wrong rights. Existing `user_units` rows are
  kept and **shown** in User access with no role, so IT admin only adds the
  role (§ 5.5).

## 5. Rules

### 5.1 Who may log in
- Token roles recognised: `admin` (via `mspv-apps-admin` or `admin`),
  `it_admin`, `maintenance_team`; realm or client roles, as today. None → 401.
- `maintenance_team` grants **no** permission by itself
  (`compute_permissions(["maintenance_team"]) == []`): access comes from
  memberships.
- Old `maint_*` client roles in a token are ignored. `/api/auth/me` (called
  once per page load, the de-facto login) logs one WARNING with the username
  and the stale roles while present, to show who still carries them (§ 5.7).
  Not per request: tokens are checked on every request (BR2-04).

### 5.2 Permissions
- **Site roles** are the five maintenance roles, one per (user, site), with the
  ladder of `ROLE_INCLUDES` applied at that site. `('*',)` at a site means "any
  site role at that site".
- **Global permissions** = token roles' permissions ∪ every site role's
  permissions. They drive navigation, `/auth/me`, and the keys that aren't
  site-scoped (`masters:*`, `technicians:edit`, `settings:*`).
- **Site-scoped keys** (`SITE_SCOPED`) on a record are checked **at the
  record's site**: `has_perm_at(key, site_id)` = admin, or a token role grants
  it, or the role at that site grants it. `require_perm(key)` stays on routes
  as the cheap first check ("holds it somewhere").
- **Lists gated by a key are scoped by that key**: `accessible_unit_ids(cur,
  key)` returns the units of the sites where the key is held (BR1-03). The
  equipment list uses `equipment:read`, the removed-documents list
  `equipment:purge_documents`, `edit_unit_ids` `equipment:edit`; phase-3 lists
  will do the same.
- **Fail-closed:** no membership at a site → no site-scoped right there; no
  membership anywhere and no token role → no permissions, `NoAccessView`, and
  every data endpoint answers 403.
- `it_admin` keeps its current permissions everywhere (token role), including
  `equipment:edit`, `equipment:read_all_units` and `equipment:purge_documents`.
- **Database down:** a check the token roles answer needs no query. One that
  needs memberships raises `DBUnavailable` → 503, as the route would anyway.
  `/api/auth/me` catches it and answers 200 with the token permissions,
  `sites: null`, `db_unavailable: true`.

### 5.3 Where (accessible units)
- Every unit only when the user is `admin`, or the **token roles** grant both
  the key and `equipment:read_all_units` (IT admin, for today's keys). For any
  other key, IT admin too is scoped by its memberships (BR2-01, BR3-01).
- Otherwise, per key, the union over the sites where the key is held: all
  active units of the site when `all_units = 1`, else the user's `user_units`
  rows at that site. Memberships and rows are looked up by the normalised
  username, as today.
- The manager's "sees all units" (Plan § 3) becomes `all_units = 1` at their
  site(s); the User access dialog ticks it by default when the role is
  manager.
- `/my-units` for a manager with all units of SMTW: `all_units: false` and
  `unit_ids` = SMTW's active units. **Accepted consequence:** the equipment
  filter offers inactive units only to every-unit users (`stores/equipment.js`
  `filterableUnits`), so a site-wide manager no longer sees their site's
  inactive units in the filter; scrapped equipment there is still found by
  search.

### 5.4 Site checks on writes
Each write checks its key at the site of the record it changes. **The check
lives in the three existing choke points**, keyed, so no write route can skip
it (BR2-02):
- `load_node_for_user(cur, node_id, for_update, key=None)`: with
  `for_update` true a `key` is required (an assertion: a programming error),
  and after the existing 404, `require_perm_at(key, node["site_id"])`.
  `_lock_node_for_change` gains the same parameter (upload, title, remove pass
  `equipment:edit`; restore `equipment:purge_documents`); purge calls
  `load_node_for_user` directly with `equipment:purge_documents`;
- `_lock_target_unit(cur, unit_id, key)` (equipment create, move) and
  `_load_target_node(cur, node_id, child_level, key)` (part create,
  re-parent): the check after the existing refusal order, with the field
  (`unit_id`, `parent_id`) on the 403; none for the node itself.
- Shell details: `_NODE_COLUMNS` gains `s.id AS site_id`; `_LOCK_UNIT` gains
  `site_id`. The 403's site **code** comes from a plain read of `sites` (or the
  memberships' site list), never from a join on the locking read (the module
  rule: locking reads are single-table).

The check comes **after** the existing order (unknown / inactive 400, outside
the user's units 404 or 403, scrapped 409, wrong level 400), so those answers
don't change. Per route:
- equipment create: the target unit's site;
- part create: the parent's site;
- edit, status (`PUT`), notes, type: the node's site;
- move to another unit: **both** the current and the target unit's site;
  re-parent: the node's site **and** the new parent's site;
- documents upload, title edit, remove: the node's site; purge, restore: the
  document's node's site;
- class and type documents (S009), equipment classes and types, technicians
  (S010): no site; the **global** key applies.
The coder lists every write route with its check in the report.

### 5.5 User access (memberships)
- `PUT /user-access/<username>` `{sites: [{site_id, role, all_units, unit_ids}]}`
  replaces the user's memberships and units **atomically**, diffing so
  unchanged rows keep `granted_at/by`.
- **Not your own access** (BR2-03): `PUT /user-access/<username>` answers 403
  "You can't change your own access" when the normalised path username equals
  `normalise_username(actor())` (`actor()` is the raw token name; BR3-03), for
  every role. IT admin could otherwise give themselves
  maintenance rights that Plan § 3 keeps away from it (from phase 3: closing
  breakdowns, verifying PM); A.5.3 and A.8.2 ask for prevention, not only the
  log. A second IT admin, or admin, changes an IT admin's own access.
- **Body shape:** `sites` not a list, an entry not an object, or `site_id` not
  a positive integer → 400 (fields `sites`, `site_id`); `role` missing → 400
  "Choose a role" (the legacy-row case).
- Per site: the site must exist (a plain read → 400 field `sites` "Unknown
  site", not the FK's 500); an inactive site can be kept but not newly granted
  (400), as an inactive unit; `role` one of `SITE_ROLES` (400); `all_units`
  true → `unit_ids` must be empty (400); otherwise at least one unit (400
  "Choose units or all units"); `unit_ids` de-duplicated; every unit must
  belong to that site (400); an inactive unit can be kept but not newly
  granted (400), as `_check_grantable`.
- A site appears at most once (400). An empty list removes all access.
  Switching a site to all units deletes the user's unit rows at that site.
- A membership at a since-deactivated site still counts, also for the global
  union: deactivating a plant doesn't revoke its people; IT admin removes them
  (A.5.18 leavers). `GET /user-access` marks such sites inactive.
- **Lock order** (BR1-07, BR2-05): (1) the user's `memberships` and
  `user_units` rows `FOR UPDATE`; (2) the units (`_check_grantable`, as today);
  (3) only then every delete and insert. The insert into `memberships` takes an
  implicit shared lock on the parent `sites` row through the FK; coming after
  the units, that is unit → site, the same order as `update_unit`, so no
  cycle. Sites are otherwise read without a lock. The `equipment.py`
  docstring's lock order is updated.
- Logged at INFO only when something changed: actor, user, before and after,
  as `site:role:all` or `site:role:UNIT,UNIT`.
- `GET /user-access` lists users from memberships **and** `user_units`: a site
  with unit rows but no membership appears with `role: null`, so legacy rows
  are visible and the first save replaces them (BR1-06). `units` as today's
  `_unit_summary`: `[{id, full_code, name, active}]`.
- View: `masters:read_senior`; change: `masters:edit` (IT admin).

### 5.6 The User access panel
- A list of users with their sites, roles and units; a dialog per user: one row
  per site (site picker, role select, "All units" switch, unit checkboxes of
  that site), add or remove a site row. When "All units" is on, the unit
  checkboxes are cleared and disabled. A row with no role (legacy) must get one
  before saving. The S007 guard applies. Today's guard is kept: "Add user"
  with the name of someone who already has access shows their current access
  to review instead of overwriting it. The dialog doesn't offer the signed-in
  user's own row for editing (§ 5.5).
- New users are added by typing the username (Yantra can't list Keycloak
  users), as today.

### 5.7 Switching over (production)
1. **Keycloak first:** create client role `maintenance_team` on
   `vel-yantra-master` and give it to every maintenance user (a group is
   easiest). Harmless before the deploy: today's code ignores roles it doesn't
   know.
2. **Deploy S011.** Maintenance users log in and see "You have no access yet"
   until step 3. IT admin works as before.
3. **IT admin enters memberships** in User access; legacy unit rows are already
   shown, so mostly only the role is added. The gap between 2 and 3 is short:
   few users exist in production.
4. **Remove the old `maint_*` client roles** once every user has a membership
   **and** a rollback to the previous release is no longer wanted (the old
   code needs them; v9 only adds a table, so the old release runs on the new
   schema). The WARNING log line (§ 5.1) shows who still carries them.
The implementation report repeats these steps with the exact Keycloak screens.

### 5.8 Dev and tests (BR1-02)
- **Dev bypass:** `DEV_STUB_ROLE` set to a site role gives the stub user the
  membership `(None, role, True)`: that role at every site, all units.
  `it_admin` stays a token role; `maintenance_team` gives a login-only stub
  (no access, to see `NoAccessView`).
- **`X-Test-Role: <site role>`** → membership `(None, role, role ==
  "maint_manager")`, i.e. that role at every site, all units only for the
  manager (today's "manager sees all units"). The user's `user_units` rows
  come from the DB as in production (the wildcard covers every site). DB
  memberships are **ignored** under this header, so legacy tests keep their
  meaning.
- **`X-Test-Role: maintenance_team`** (+ `X-Test-User`) → login only;
  memberships and units come from the DB, as in production. The per-site cases
  set them through the real `PUT /user-access`, which is itself under test.
  No `X-Test-Memberships` header.
- **An unknown `X-Test-Role`** (`nobody`): a user with no token role and no
  membership, so data endpoints answer 403, as today. Never a wildcard.
- **Fixtures:** `user_with_units(role, units)` groups the units by site and
  PUTs `{sites: [{site_id, role, all_units: false, unit_ids}]}`; for a role not
  in `SITE_ROLES` (`it_admin`, `admin`) it writes nothing and returns the role
  client (a token role sees every unit anyway). A new `user_at_sites(spec)`
  serves the per-site cases.

## 6. API

| Method and path | Permission | Result |
|---|---|---|
| `GET /api/auth/me` | logged in | as now (`role` per § 3, `roles` = token roles, `permissions` = global union), plus `sites: [{site_id, site_code, role, all_units}]`; on `DBUnavailable`: token permissions, `sites: null`, `db_unavailable: true` |
| `GET /api/equipment/<id>` | `equipment:read` | as now, plus `permissions`: the user's **full** effective key list at the node's site (token keys ∪ the site role's keys; every key for admin) |
| `GET /api/equipment/my-units` | `equipment:read` | as now, plus `edit_unit_ids` (`null` = every unit; the write pickers then offer every active unit, as `all_units` today) |
| `GET /api/equipment/removed-documents` | `equipment:purge_documents` | as now, scoped to the sites where that key is held |
| `GET /api/masters/user-access` | `masters:read_senior` | `{items, total}`: `{username, sites: [{site_id, site_code, active, role, all_units, units}]}`; `units` is `[]` for an all-units site |
| `PUT /api/masters/user-access/<username>` | `masters:edit` | the user's new access |
| `GET/PUT /api/masters/user-units…` | — | removed |

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| Maintenance roles in Yantra, per site | Roles differ per plant (user); Keycloak client roles are global | Keycloak client roles per site (`smtw_engineer`, …): explodes with sites, still needs the Keycloak admin |
| One role per (user, site) | The ladder covers the combinations (an engineer is also a technician) | Several roles per site (§ 9.1) |
| Units within the site kept in `user_units` | No data move; "all units" as a flag covers managers and new units | Role per unit (user chose per site) |
| `it_admin` and `admin` stay in Keycloak | Nobody can grant themselves IT admin through Yantra (A.5.3, A.8.2) | All roles in Yantra |
| IT admin alone edits memberships | Segregation of duties (user) | Managers granting at their site |
| Memberships loaded lazily, not in `require_auth` | The app serves while the DB is down (CLAUDE.md); token-role checks need no query | A query in every request's before-handler |
| `require_perm` "somewhere" + `require_perm_at` on the record | Cheap 403 for no-hopers; the real check where the site is known | Only per-site checks |
| `accessible_unit_ids` keyed by permission | One rule for every list a key gates (removed documents now, tickets later) | Scoping only the writes (leaks senior lists) |
| A wildcard membership (`site_id = None`) for dev and tests | Legacy tests keep their meaning without querying sites; one representation in the core | A per-request expansion over the `sites` table |
| Role stored as text, validated against `SITE_ROLES` | One source of truth for the role list | A DB `ENUM` (a second list to keep in step) |
| Node detail carries `permissions` | The frontend can't know the site rules; backend-heavy | Frontend computing per-site rights |
| No conversion of old roles; legacy unit rows shown | Yantra can't read Keycloak roles; a guess grants wrong rights | Defaulting everyone to operator; deleting the rows |
| Keycloak role first, then deploy | Users see "no access yet" rather than a Keycloak error during the switch | Deploy first (users get 401) |
| Site checks inside the three choke points, keyed | A write can't reach a node, unit or parent without naming its key; one test per helper covers every route | A `require_perm_at` call per route (each can be forgotten) |
| "Every unit" only when the token grants both the key and all-units | No fail-open for a future key IT admin doesn't hold (BR2-01) | `read_all_units` → every unit for any key |
| Nobody changes their own access | Prevents IT admin self-granting maintenance rights (A.5.3, A.8.2) | Allow, with the log as the only control |

## 8. Tests and acceptance

### Pure (`test_access_core.py`)
- Global union over two sites with different roles; token role `it_admin`
  adds its keys; no memberships and no token role → nothing;
  `maintenance_team` alone → nothing.
- `permissions_at`: engineer at A, operator at B → `equipment:edit` at A only;
  the ladder applies per site; an unknown site → token roles only; a wildcard
  membership applies at every site.
- `unit_ids_for`: all-units site + chosen units at another; `user_units` rows
  at a site without membership are ignored; inactive units excluded; per key
  (manager at A, operator at B → `equipment:purge_documents` covers A only);
  `equipment:read_all_units` → `None`.
- Fail-open guards (BR2-01, BR2-06): token `it_admin` + membership engineer at
  A, with a test key granted to engineers but not to `it_admin` (injected into
  `PERMISSIONS`) → A's units, not `None`; a membership with role `it_admin` or
  a typo → no keys at all (neither `('*',)` nor `masters:edit`,
  `settings:edit`) and no units; `permissions_at(site_id=None)` with a real
  membership → token roles only; a non-`SITE_SCOPED` key → assertion.

### API
- **Login and DB:** a token with only `maintenance_team` and no membership →
  `/auth/me` 200 with `sites: []` and `permissions: []`; `/api/equipment` →
  403. A token with only old `maint_*` roles → 401. With `ensure_schema`
  monkeypatched to fail: `/auth/me` for `it_admin` → 200 with its token
  permissions and `db_unavailable: true`; for a `maintenance_team`-only user →
  200, `permissions: []`, `db_unavailable: true`; a membership-needing route →
  503. A token with stale `maint_*` roles → one WARNING from `/auth/me`, none
  from other routes.
- **Per-site writes:** engineer at A, operator at B (units at both): edit at A
  → 200, at B → 403; read at B → 200; move from A to B → 403; part under a B
  parent → 403; re-parent to a B parent → 403; document upload at B → 403;
  class document upload → 200 (global). One case per choke point is the
  minimum; also at B: status, notes, type, document title edit and remove →
  403; restore at B for a manager at A → 403.
- **Own access:** IT admin `PUT /user-access/<own username>` → 403; another IT
  admin → 200.
- **User access body:** unknown `site_id` → 400 (not 500); `sites` not a list
  → 400; inactive site newly granted → 400, kept → 200 and listed
  `active: false`; switching to all units removes the site's unit rows.
- **Scoped lists:** manager at A, operator at B, a removed document at B → not
  listed, purge → 403; one at A → listed, purge → 200.
- **Node `permissions`:** differ between an A node and a B node.
- **`/my-units`:** `edit_unit_ids` is A's units only; a manager with all units
  of A → `all_units: false`, `unit_ids` = A's active units.
- **User access:** replace with two sites; all-units with `unit_ids` → 400;
  a unit of another site → 400; a duplicate site → 400; an unknown role →
  400; an inactive unit newly granted → 400, kept → 200; empty list removes
  all; diff keeps `granted_at`; INFO log line only on change; legacy unit rows
  listed with `role: null`; engineer → 403 on `PUT`, IT admin → 200.
- **Rewritten existing cases:** `test_auth.py` (the four token tests with
  `maint_*` roles now use `maintenance_team` / expect 401; the three rejection
  cases — wrong client, expired, bad signature — switch to `maintenance_team`
  so each fails for the reason in its name),
  `test_rbac.py::test_role_matrix` (manager without
  `equipment:read_all_units`), `test_equipment_api.py::TestMyUnits::test_senior_roles_get_all_units`
  (IT admin only), and the four `test_masters_api.py` cases calling
  `/user-units` (re-pointed to `/user-access`).

### RBAC (`test_rbac.py`)
- No site role holds `masters:edit` (the grant power stays IT admin's; BR3-04).
- Own access: `PUT /user-access/<Own-Name>` with a case-varied token name →
  403 (BR3-03).
- `SITE_SCOPED ⊂ PERMISSIONS`; `SITE_ROLES ⊂ ROLES`; `LOGIN_ROLE ∉ ROLES`;
  `equipment:read_all_units` is IT admin only; `it_admin ∉ SITE_ROLES`; no
  `admin` in tuples.

### Frontend
- `navigation.test.js`: the manager's list.

### Manual checks (user)
- **Important** (must be done or explicitly skipped before Done):
  - only `maintenance_team`, no membership → the "no access yet" page, with
    name and Sign out in the top bar;
  - as IT admin: give a test user manager at SMTW (all units) and engineer at
    VEL (one unit); as them: SMTW all units, edit everywhere; VEL one unit,
    edit there; other VEL units invisible;
  - change the VEL role to operator: edit buttons on VEL equipment gone after a
    page load; a direct edit refused (403);
  - the production switch-over of § 5.7, in that order.
- Also: the User access dialog asks before discarding changes (S007); legacy
  unit rows show with no role.

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean.

## 9. Open questions and assumptions

1. **Confirmed (user, 16-10-2026):** one role per user per site. A storekeeper who is also a
   technician at the same site can't be both; say if that case exists.
2. **Confirmed (user, 16-10-2026):** IT admin keeps all its current rights at every site
   (equipment edit, all units, purge), from the Keycloak role.
3. **Confirmed (user, 16-10-2026):** a manager at one site sees only that site; reports across
   sites (phase 5) go to someone who is manager at each, or to IT admin.
4. **Confirmed (user, 16-10-2026):** `masters:read` (`*`) stays global: anyone with a membership
   anywhere reads all masters (sites, units, classes), as pick-lists.
5. **Confirmed (user, 16-10-2026):** global keys are the union: an engineer at any site edits the
   (site-less) equipment classes, types and technicians.
6. **Decided (user, 16-10-2026) — nobody changes their own access** (§ 5.5, BR2-03). An IT
   admin's own memberships are then changed by another IT admin or by admin
   (you, via `mspv-apps-admin`). Confirm, or allow self-edits with the log as
   the only control.

## 10. Amendments

(none)

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 Memberships in `require_auth` break serving while the DB is down | major | **Accepted, option 1.** Lazy, `g`-cached loading; `/auth/me` catches `DBUnavailable` with `db_unavailable: true`; a test (§ 1, § 3, § 5.2, § 6, § 8). |
| BR1-02 Test harness unspecified; tests that break | major | **Accepted, option 1.** Wildcard membership in the core; `X-Test-Role` semantics; `maintenance_team` + DB for per-site cases; no `X-Test-Memberships`; the rewritten cases listed (§ 3, § 5.8, § 8). |
| BR1-03 Removed-documents list not site-scoped | major | **Accepted, option 1.** `accessible_unit_ids(cur, key)`; a test (§ 3, § 5.2, § 6, § 8). |
| BR1-04 Switch-over misstated | major | **Accepted, option 1.** Keycloak first, then deploy, memberships, then remove old roles (§ 5.7). |
| BR1-05 `maintenance_team` and the wildcard; `role`/`roles` | minor | **Accepted.** Not in `ROLES`, grants nothing; `role`/`roles` defined; a test (§ 3, § 5.1, § 5.2, § 8). |
| BR1-06 Legacy `user_units` rows invisible | minor | **Accepted, option 1.** Shown with `role: null`; replaced on first save (§ 4, § 5.5, § 5.6). |
| BR1-07 Lock order vs `update_unit` | minor | **Accepted.** Rows → units; sites read without a lock; docstring updated (§ 5.5). |
| BR1-08 `ENUM` duplicates the role list | minor | **Accepted, option 1.** `VARCHAR(30)` validated against `SITE_ROLES` (§ 4). |
| BR1-09 Shell details | minor | **Accepted.** Part create and re-parent checks, the existing refusal order, full `permissions`, `/my-units` for a site-wide manager (inactive-unit filter consequence accepted), body and log details, normalised usernames (§ 5.3, § 5.4, § 5.5, § 6). |
| BR1-10 Docs and standards | minor | **Accepted.** Maintenance-Philosophy § 11, Plan § 1 / § 3 / § 9 Q1; ISO 55001:2024; A.8.3 added (§ 2, § 3). |
| BR1-11 `NoAccessView` trigger, sign-out, messages | minor | **Accepted.** Trigger and shell, two messages, 401 text, `userSites` dropped (§ 1, § 3). |
| BR1-12 Small points | nit | **Accepted.** `_TABLES`, WARNING per login, realm or client role, `units` shape, all-units disables checkboxes, the user commits the devops doc (§ 3, § 5). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

All twelve round-1 answers verified in the text.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 "Every unit" shortcut fails open for a future key | major | **Accepted, option 1.** `None` only for admin or when the token grants both keys; a pure test with an injected key (§ 3, § 7, § 8). |
| BR2-02 Where the per-site check lives | major | **Accepted, option 1.** Inside `load_node_for_user`, `_lock_target_unit`, `_load_target_node` (and `_lock_node_for_change`), keyed; `site_id` added to the node and unit reads; the site code from a plain read; tests per helper and for the remaining routes (§ 5.4, § 7, § 8). |
| BR2-03 IT admin can grant themselves maintenance rights | minor | **Accepted, option 1.** `PUT` on one's own access → 403; the dialog doesn't offer it; a test. **For the user to confirm at gate A** (§ 5.5, § 5.6, § 7, § 9.6). |
| BR2-04 WARNING per request | minor | **Accepted, option 1.** Logged from `/auth/me`, from `stale_roles` (§ 3, § 5.1, § 8). |
| BR2-05 `PUT /user-access` rules | minor | **Accepted.** Unknown site 400; inactive site kept-not-granted and still counting; the implicit FK lock after the units; body-shape 400s; all-units deletes unit rows (§ 5.5, § 6, § 8). |
| BR2-06 Harness and core edges | minor | **Accepted.** Fixture for token roles; unknown `X-Test-Role`; `('*',)` only for `SITE_ROLES`; `site_id None` matches nothing; three `test_auth` cases switched (§ 3, § 5.8, § 8). |
| BR2-07 Lazy loader and `g.user` rules | minor | **Accepted.** `get_db()`; `role` computed in `/auth/me`, `null` for login-only; `SITE_SCOPED` enforced by assertion; the all-units unit query only when needed (§ 3). |
| BR2-08 Small points | nit | **Accepted.** Step 4 after rollback is unwanted; the "Add user" guard kept; `active` on site entries; 403 fields; the DB-down case for a login-only user (§ 5.4, § 5.6, § 5.7, § 6, § 8). |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 16-10-2026

The last round under the 3-round cap; the answers below are not re-reviewed.
BR2-02 to BR2-08 verified in the text; BR2-01 was missing from § 5.3.

| Finding | Severity | Response |
|---|---|---|
| BR3-01 § 5.3 still had the old "every unit" shortcut | major | **Accepted.** § 5.3 now states the key-aware rule of § 3 (§ 5.3). |
| BR3-02 A non-site role in the DB must grant nothing at all | minor | **Accepted.** Such a membership is ignored entirely; the test covers `masters:edit` and `settings:edit` (§ 3, § 8). |
| BR3-03 Own-access check must normalise the actor | minor | **Accepted.** `normalise_username(actor())`; a case-varied test (§ 5.5, § 8). |
| BR3-04 No site role may hold `masters:edit` | minor | **Accepted.** A `test_rbac` invariant (§ 8). |
| BR3-05 Stale wording | nit | **Accepted.** Assertion in `has_perm_at`; purge via `load_node_for_user`; `(unit_id, site_id)` pairs; `DEV_STUB_ROLE = maintenance_team`; `edit_unit_ids: null` in the pickers; header date (§ 3, § 5.4, § 5.8, § 6). |

### Gate A — user decisions, 16-10-2026

- Assumptions § 9.1–9.5 confirmed; § 9.6: nobody changes their own access.
- Coder: Opus (RBAC core, security-sensitive).
- Approved by KLA. Coding starts after S010 is committed.
