```
Step: S011 — Roles per site, held in Yantra
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S011 — Brief review, round 2

**Verdict: not ready — two `major` findings are open** (BR2-01, BR2-02), both
in the access core's rules rather than the design. No blocker. All twelve
round-1 answers are reflected in the brief text (checked below). The new
findings come from reading the revised rules against the current code with
the security questions the orchestrator asked: a scope shortcut that fails
open once phase-3 keys exist, and where the per-site check lives so no write
route can skip it.

Read for this review: the brief as revised; `docs/steps/README.md`;
`docs/Plan.MD` § 1, § 3, § 5, § 9; `docs/Maintenance-Philosophy.md` § 11;
`.claude/CLAUDE.md`, `.claude/CLAUDE-COMMON.md` § RBAC Pattern,
`.claude/SMTW-WebApp-Base.md` § RBAC Pattern; S010's brief (v8, the S011
touchpoint); the working-tree code: `backend/auth_utils.py`, `config_rbac.py`,
`app.py`, `equipment.py`, `documents.py` (S008 and S009 routes), `masters.py`,
`masters_core.py`, `api_common.py`, `db_helpers.py`, `local_db.py`,
`settings.py`, `config.py`, `example_secrets_app.py`, `tests/conftest.py`,
`test_auth.py`, `test_rbac.py`, `test_equipment_api.py` (unit access,
permissions, my-units), `test_masters_api.py` (user units, permissions),
`test_removed_documents_api.py`; `frontend/src/stores/auth.js`,
`stores/equipment.js`, `stores/navigation.js`, `App.vue`,
`views/masters/UserUnitsPanel.vue`, `tests/navigation.test.js`; the devops
`docs/lob-apps/Yantra.MD` step 5. Whitespace-only differences were ignored
(`git diff -w --ignore-cr-at-eol`).

---

## Round-1 answers verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 lazy memberships, DB down | § 1.6, § 3 (`require_auth` DB-free; `g`-cached loader), § 5.2 "Database down", § 6 `/auth/me`, § 7, § 8 (`ensure_schema` monkeypatched) | yes |
| BR1-02 harness and broken tests | § 3 (`access_core` wildcard `site_id = None`), § 5.8 (header semantics, no `X-Test-Memberships`, fixtures), § 8 "Rewritten existing cases" | yes — see BR2-06 for two cases it still misses |
| BR1-03 senior lists scoped by key | § 3, § 5.2 "Lists gated by a key", § 6, § 8 "Scoped lists" | yes — the `None` shortcut needs tightening, BR2-01 |
| BR1-04 switch-over | § 5.7 Keycloak first → deploy → memberships → remove old roles; § 7 | yes |
| BR1-05 `maintenance_team`, `role`/`roles` | § 3 (`ROLES` unchanged, `LOGIN_ROLE ∉ ROLES`), § 5.1, § 5.2 (`('*',)` at a site), § 8 pure + RBAC cases | yes |
| BR1-06 legacy `user_units` rows | § 4, § 5.5 (`role: null`), § 5.6, § 8 | yes |
| BR1-07 lock order | § 5.5 rows → units, sites unlocked, docstring | yes — one implicit lock to name, BR2-05 |
| BR1-08 `VARCHAR` + `SITE_ROLES` | § 4, § 8 RBAC | yes |
| BR1-09 shell details | § 5.3, § 5.4, § 5.5, § 6 | yes |
| BR1-10 docs and standards | § 2 (ISO 55001:2024, A.8.3), § 3 docs list | yes |
| BR1-11 `NoAccessView` | § 1.4, § 3 (trigger, shell, two messages, 401 text, no `userSites`) | yes |
| BR1-12 small points | § 3 `_TABLES`, § 5.1 WARNING, realm or client, § 5.5 `units` shape, § 5.6, § 3 devops doc | yes — the WARNING placement has a side effect, BR2-04 |

---

## Major

### BR2-01 — `major` — `accessible_unit_ids(cur, key)`: the "every unit" shortcut must depend on the key, or it fails open for IT admin with a membership

**Problem.** § 5.3 and § 3 (`unit_ids_for`) say: "`admin` and holders of
`equipment:read_all_units` (IT admin): every unit" — for **any** key — and
"otherwise, per key, the union over the sites where the key is held". Today
that is harmless: the three keys in `SITE_SCOPED` (`equipment:read`, `:edit`,
`:purge_documents`) are all held by `it_admin` from the token, so an IT admin
listing by any of them may see every unit.

It stops being harmless with the first key that is site-scoped but **not** IT
admin's — every phase-3 key in Plan § 3's matrix (`breakdown:close`,
`pm_job:verify`, `report:read`, …). Nothing in the brief stops an IT admin
user from also holding a membership (IT gives themselves engineer at SMTW, or
a genuine dual-role person). Then a phase-3 list "tickets I may close":
`require_perm("breakdown:close")` passes (held at SMTW), and
`accessible_unit_ids(cur, "breakdown:close")` sees `equipment:read_all_units`
in the token and returns `None` → the tickets of **every** site, not SMTW's.
The brief says "phase-3 lists will do the same", so the rule being written now
is the one phase 3 inherits.

**Why it matters.** It is a latent fail-open in the access core, in a step whose
whole point is "rights follow the site" (ISO 27001 A.5.15: access on business
need; A.8.3: restrict information in line with the policy). A phase-3 coder
reading "read_all_units → every unit" will not question it.

**Options.**
1. **Make the shortcut key-aware (recommended).** `unit_ids_for` returns
   `None` only when the user is `admin`, or when the **token roles** grant
   both `key` and `equipment:read_all_units`. Otherwise the per-site union of
   § 5.3 applies, where "the key is held at the site" means
   `has_perm_at(key, site)` (token role or site role). With today's keys the
   result for IT admin is unchanged; for a future key IT admin does not hold,
   an IT admin with a membership gets exactly that membership's units. Add the
   pure test: token `it_admin` + membership engineer at A, a key granted to
   engineers but not to `it_admin` (use a key injected into `PERMISSIONS` by
   the test, as `test_removed_documents_api` already monkeypatches it) → A's
   units only, not `None`. State the rule in § 3 and § 5.3.
2. Forbid memberships for users who hold a token role. Not enforceable: Yantra
   cannot see a user's Keycloak roles at `PUT /user-access` time.

### BR2-02 — `major` — Where the per-site check lives: put it in the three choke points, so no write route can skip it

**Problem.** § 5.4 lists each write and its site, and says the coder lists every
route in the report. It does not say *where* in the code the check is made. Read
as written, the natural implementation is a `require_perm_at(...)` call added
inside each route — a dozen call sites in `equipment.py` and `documents.py`,
each of which can be forgotten. § 8's per-site cases cover edit, move, part
create, re-parent, document upload, purge; they do **not** cover title edit,
remove, restore, the status `PUT`, notes or type change at the other site. A
missed call on any of those is a silent cross-site escalation that the suite
would not catch.

The current code already funnels every node write through three helpers:
`load_node_for_user(cur, node_id, for_update=True)` (edit, status, notes,
type, document title/remove/restore via `_lock_node_for_change`, purge),
`_lock_target_unit` (equipment create, move) and `_load_target_node` (part
create, re-parent). Those are the choke points; the check belongs there.

**Options.**
1. **Check inside the helpers, keyed (recommended).**
   - `load_node_for_user(cur, node_id, for_update, key=None)`: when
     `for_update` is true a `key` is required (an assertion — a programming
     error, not a 4xx) and, after the existing 404, `require_perm_at(key,
     node["site_id"])` is applied. Callers pass `"equipment:edit"` or
     `"equipment:purge_documents"`; `_lock_node_for_change` gains the same
     parameter (upload/title/remove pass edit, restore passes purge).
   - `_lock_target_unit(cur, unit_id, key)` and `_load_target_node(cur,
     node_id, child_level, key)`: the check after the existing refusal order
     (unknown 400 / inactive 409 / access 403 / scrapped 409 / level 400), with
     the field (`unit_id`, `parent_id`) on the 403.
   - A route then cannot write a node or target a unit or parent without
     naming the key it holds there. § 8 needs one case per helper rather than
     one per route, plus the list the brief already has. The § 5.4 route list
     stays as documentation and the report still enumerates it.
   - Shell details this needs: `_NODE_COLUMNS` gains `s.id AS site_id`
     (`_read_node` returns only `site_code` today); `_LOCK_UNIT` gains
     `site_id` (it returns `id, code, active`). The 403 message wants the site
     **code**; the locking read must stay a single-table read (module
     docstring: never through the join fragment), so the code comes from a
     plain read of `sites` or from the memberships' site list, not from a join
     on the `FOR UPDATE`.
2. Per-route calls, with § 8 extended to **every** write route at the other
   site (status, notes, type, title, remove, restore included) and a
   `test_rbac` case that greps nothing — i.e. rely on the report list and the
   code review. Weaker; acceptable only if option 1 is refused.

---

## Minor

### BR2-03 — `minor` — IT admin can grant themselves maintenance rights; refuse edits to one's own access

**Problem.** § 2 says "nobody can make themselves IT admin through Yantra"
(true: it stays in Keycloak) and "the people who do maintenance don't grant
themselves rights". But the person who *does* grant rights can grant them to
**themselves**: `PUT /user-access/<own username>` with `maint_manager` at every
site. Today that adds little (IT admin already holds every site-scoped key);
from phase 3 it adds closing breakdowns, verifying PM jobs and reports, which
Plan § 3 deliberately keeps away from IT admin ("not maintenance work and not
all-powerful").

**Standard.** ISO 27001:2022 **A.5.3 (segregation of duties)** asks that
conflicting duties be separated so one person cannot both grant and use a
right unchecked; **A.8.2 (privileged access rights)** asks that privileged
rights be allocated through an authorisation process, not self-service. The
INFO log line (A.8.15) records the self-grant, which is a detective control;
refusing it is the preventive one and costs one comparison.

**Options.**
1. **Refuse (recommended).** `PUT /user-access/<username>` answers 403 "You
   can't change your own access" when `username == actor()` (normalised), for
   every role — `admin` gains nothing from a membership anyway. One test. State
   it in § 5.5 and § 7.
2. Allow and record in § 7 that the log is the control. Weaker, but a
   legitimate choice for a 50-user plant if the user prefers it.

### BR2-04 — `minor` — "WARNING on each login" is WARNING on every request: there is no login event in the backend

**Problem.** § 5.1: old `maint_*` roles are "logged at WARNING on each login
while present". The backend has no login hook — `validate_keycloak_token` runs
on **every** API request (`require_auth` is a `before_request`). A user who
still carries `maint_engineer` would write a WARNING line for every list,
detail, thumbnail and version-poll request: hundreds of lines per session, and
the signal IT needs for § 5.7 step 4 drowns in them.

**Options.**
1. **Log in `/api/auth/me` (recommended).** The frontend calls it once per page
   load after Keycloak login, so it is the de-facto login event. `auth_me`
   checks `g.user["stale_roles"]` (the `maint_*` names the token parser found
   and ignored) and logs one WARNING with username and roles. No state, no
   per-worker set.
2. A per-worker "seen usernames" set in `auth_utils`, as the round-1 nit
   offered. Works, but state in a module global for a log line.

### BR2-05 — `minor` — `PUT /user-access` rules the coder would otherwise decide alone

- **Unknown `site_id` → 400, not 500.** § 5.5 checks that units belong to the
  site but never that the site exists. An INSERT into `memberships` with a
  site id that is not in `sites` fails the FK with MariaDB error 1452;
  `api_common._integrity_error` re-raises anything but 1062, so the user gets
  a 500. Say: site ids are checked against `sites` (a plain read, per the lock
  rule) → 400 field `sites` "Unknown site". Add the test.
- **Inactive site: kept, not newly granted.** § 5.5 allows "a membership at a
  since-deactivated site" to exist. Say the mirror of `_check_grantable`: a
  site row may be kept at an inactive site, but a **new** membership at one is
  400, as an inactive unit. And say that a membership at an inactive site
  still counts for the **global** union (`has_perm("equipment:edit")`, which
  edits classes, types and technicians): deactivating a plant does not revoke
  its people; IT admin removes them (A.5.18 "leavers"), and `GET /user-access`
  should mark the site inactive so they can see it.
- **The implicit site lock.** The INSERT into `memberships` takes an implicit
  **shared** lock on the parent `sites` row through `fk_memberships_site`.
  That is fine — `update_unit` goes unit → site too — **provided the
  membership writes come after `_check_grantable` has locked the units**.
  If the coder inserts memberships before locking the units, the implicit
  order becomes site → unit against `update_unit`'s unit → site: the cycle
  BR1-07 removed, back through the FK. Say the order explicitly: lock the
  user's rows → `_check_grantable` (units) → then all deletes and inserts.
- **Body shape.** As `validate_unit_ids`: `sites` not a list, or an entry not
  an object, or `site_id` not a positive integer → 400 with the field
  (`sites`, `site_id`). `role` missing → 400 "Choose a role" (the legacy row
  case in the dialog, § 5.6).
- **Switching a site to all-units** deletes the user's `user_units` rows at
  that site (the PUT replaces everything) — implied, worth one sentence, since
  the diff is now two-level (memberships and rows).

### BR2-06 — `minor` — Harness and core edge rules

- **`user_with_units(role, units)` for a token role.** § 5.8 says the fixture
  PUTs `{sites: [{site_id, role, …}]}`; with `role = "it_admin"` or `"admin"`
  that PUT is a 400 (not in `SITE_ROLES`) and the fixture's assert fails.
  Callers today: `test_equipment_api.py::TestPermissions::test_writers`
  (`it_admin`), `TestUnitAccess::test_senior_roles_see_every_unit` (`it_admin`,
  `admin`, with `[]` — passes, nothing to validate), `TestMyUnits::test_senior_roles_get_all_units`
  (`it_admin`, with a unit). Rule: for a role not in `SITE_ROLES` the fixture
  writes nothing and returns the role client (the token role sees every unit
  anyway). Say it in § 5.8.
- **An unknown `X-Test-Role`.** `test_unknown_role_is_forbidden` (equipment and
  masters) sends `X-Test-Role: nobody` and expects 403. Say what the harness
  does with a name that is neither a token role nor a site role: a user with
  no token roles and no memberships (so `equipment:read` → a DB lookup for
  `test_nobody` → nothing → 403). Do not turn it into a wildcard membership.
- **Fail-closed on a bad role string.** `('*',)` at a site means "any site role
  at that site" (§ 5.2). Say the core checks `role in SITE_ROLES` for that —
  not `role in ROLES`, and not "any non-empty string" — so a row with a typo
  (edited by hand in the DB) or `it_admin` stored as a site role grants
  nothing. One pure test.
- **`permissions_at(…, site_id=None)`.** A wildcard membership matches when the
  *membership's* site is `None`; a query for site `None` (a node whose site
  could not be read, a programming slip) must match **no** real membership.
  Say it and test it; the cheap guard is an assertion that `site_id` is an
  int in the shell's `has_perm_at`.
- **`test_auth.py` rejection cases.** `test_wrong_client_is_rejected`,
  `test_expired_token_is_rejected`, `test_bad_signature_is_rejected` use
  `maint_operator` and would still pass — for the wrong reason (unrecognised
  role). Switch them to `maintenance_team` so each rejects for the reason in
  its name. § 8 names only the four that *change* outcome; add these three.

### BR2-07 — `minor` — Small rules of the lazy loader and `g.user`

- **The loader uses `get_db()`**, the request's pooled connection cached on
  `g`, not a connection of its own: inside a write transaction the membership
  read then shares the transaction, and the `ensure_schema` monkeypatch of
  § 8 reaches it (it patches `db_helpers.ensure_schema`, which `get_db` calls).
- **`g.user["role"]`** "the most privileged of token and site roles" needs the
  memberships, which `require_auth` no longer has. Say it is computed where
  memberships are loaded (`/auth/me`), and that `require_perm`'s 403 log line
  uses `g.user["roles"]` (the token roles) plus whatever is cached, never
  forcing a DB read for a log line. For a login-only user with no membership,
  `role` is `null` (nothing in the frontend displays `userRole` today).
- **`SITE_SCOPED` is a list nothing enforces.** As written it is documentation
  plus a `test_rbac` subset check. Either enforce it — `has_perm_at` and
  `unit_ids_for` assert `key in SITE_SCOPED`, so a global key checked at a site
  (or a new site-scoped key not added to the list) is a programming error seen
  in tests — or drop the constant. Enforcing is one line; recommended.
- **`unit_ids_for` needs every active unit** (`units` with `site_id`) only
  when some membership has `all_units`; the shell can skip that query
  otherwise. One `SELECT id, site_id FROM units WHERE active = 1` is cheap
  either way; say which the coder should do so it is not decided twice.

---

## Nit

### BR2-08 — `nit` — Small points

- **§ 5.7 and rollback.** Migration v9 only adds a table, so the previous
  release runs on the v9 schema; but the old code needs the old `maint_*`
  roles. Say: do step 4 (remove the old roles) only once a rollback is no
  longer wanted.
- **§ 5.6 "Add user" for an existing user.** Today's panel refuses to overwrite
  an existing user's set from "Add user" (it shows their current units and
  asks to review). With two levels (sites and units) the loss would be larger;
  say the guard is kept.
- **§ 6 `GET /user-access`**: `sites[].units` for an `all_units` site is `[]`;
  add `active` on the site entry (BR2-05).
- **§ 5.4 403 fields:** `unit_id` for a target unit, `parent_id` for a target
  parent, none for the node itself — as the existing access 403s.
- **§ 8 "Login and DB"**: the `ensure_schema` case should also cover a
  `maintenance_team`-only user: `/auth/me` → 200, `permissions: []`,
  `db_unavailable: true` (the frontend's "database unavailable" message, not
  "no access yet").

---

## Checked and found consistent

- **Lazy loading and DB down.** `require_auth` stays DB-free; `has_perm` for a
  token-granted key needs no query; a `DBUnavailable` raised inside
  `require_perm`'s wrapper reaches the app's error handler → 503, as the route
  would; `/auth/me` catching it keeps IT admin's shell and Settings › Database
  usable, and sends a `maintenance_team`-only user to the DB message rather
  than "no access yet". Matches `.claude/CLAUDE.md` "DB may not exist".
- **No cross-request cache**, so a membership change applies on the next
  request; the manual check ("after a page load") describes the UI, not the
  API, correctly.
- **The wildcard cannot come from production data**: `memberships.site_id` is
  `NOT NULL`, `validate_user_access` parses `site_id` as a positive integer
  (`_parse_id`), so `None` arises only from the dev stub and the test header.
  `X-Test-Role` stays behind `TESTING`.
- **Fail-closed paths hold**: no membership and no token role → `[]`
  permissions, `NoAccessView`, 403 on every data endpoint; a node at a site
  without membership is 404 (nothing revealed); an operator at B editing B's
  node gets 403 with the site code, which is fine — they can read the node.
- **The refusal order of § 5.4** keeps every existing answer: inactive unit
  409 before access 403 (a unit's state is public), access before scrapped
  (S002 BR3-02), site check last.
- **Lock order** (with BR2-05's sequencing): `PUT /user-access` user rows →
  units → implicit site (S); `update_unit` unit → site (X); `create_unit` site;
  `update_site` site only. No cycle; `equipment.py` never locks sites or
  user_units; `documents.py` takes one owner lock. Adding `memberships` to the
  module docstring is enough.
- **Switch-over order** is right: today's `validate_keycloak_token` matches
  only names in `ROLES`, so `maintenance_team` is ignored before the deploy; a
  user missed in step 1 gets the reworded 401, which points at Keycloak —
  correct for that case.
- **Standards.** The § 2 readings are accurate: A.5.15 (rules for who may
  access what, on business need), A.5.18 (rights granted, reviewed, changed and
  removed in a controlled way — joiners, movers, leavers), A.8.3 (information
  access restricted in line with the policy — what the per-site checks
  implement), A.5.3 (conflicting duties kept apart — doers do not grant;
  BR2-03 is the one gap), A.8.2 (privileged rights restricted and managed),
  A.8.15 (events logged), ISO 55001:2024 § 5.3 (roles, responsibilities and
  authorities assigned and communicated — here per plant). ISO 14224,
  EN 13306, SMRP and TPM do not bear on an access-control step and are rightly
  not cited. The departure from the base RBAC pattern (maintenance roles from
  the DB, per site) is named in § 2 and recorded in `.claude/CLAUDE.md`, as
  CLAUDE-COMMON allows.
- **Scope and size**: one migration, one pure module, one panel replaced; no
  supervisor role, no manager self-service, no role conversion — matching the
  user's decisions. `SITE_SCOPED`, `TOKEN_ROLES` and `LOGIN_ROLE` are the only
  new constants; not over-engineered.
- **S010 touchpoint**: `technicians:edit` stays a global key (§ 5.2, § 9.5),
  as S010's brief expects; `technicians.username` stays a plain string.
- **Migration numbering** v9 after S010's v8; `CREATE TABLE IF NOT EXISTS` per
  the "safe to run twice" convention; `memberships` in `_TABLES` between
  `user_units` and `units`/`sites` respects the FK on delete.
