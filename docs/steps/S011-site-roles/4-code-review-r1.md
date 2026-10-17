```
Step: S011 — Roles per site, held in Yantra
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S011 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 3 minor findings and 3 nits.

**Scope of this review.** This round reviews only what S011 changed on top of the
uncommitted S010 working tree. The S010 state was taken as git tree `15227de`, and the
diff was `git diff -w --ignore-cr-at-eol 15227de <working tree>`, built with a temporary
index. `docs/review/` is unrelated to this step and was left out. The review covers the
approved brief, amendment A1 and its two rule sets (after r4 and after r5), and the user's
gate-A decisions of 16-10-2026. Where A1 or those decisions differ from the base brief,
they win. `technicians:edit` in the brief body reads as `people:edit`.

**Tests, run by the reviewer:**
- `tooling/run-tests.bat`: **backend 891 passed**, frontend **38 passed** (7 files).
- `npx vite build` in `frontend/`: clean, no warnings.

## Findings

### CR1-01 — minor — The log line of a login save has no "before"

**Where:** `backend/masters.py:768-774` (`_log_login_save`) and `:657-658`.

**Problem.** A login save writes one INFO line. It names the actor, the person, the *new*
login and the sites *after* the save. It does not name:
- the previous login;
- the rows that `_replace_site_rows` deleted.

Brief § 2 (A.8.15) and § 5.5 ask that each access change be logged with before and after.
The per-site routes already do this (`site role changed: … before=[…] after=[…]`).

**Failure scenarios:**
- IT admin clears the login of a manager, whose manager row was changed to Technician
  first. The log reads `login=- sites=[SMTW:maint_technician:…]`. Nothing says which
  login lost access, or that a manager row existed.
- IT admin changes a login from `ravi` to `ravi.k`. The log never shows `ravi`.

An access review (A.5.18) that reads the log can't rebuild who held what.

**Fix:**
- Pass the stored login (`person["username"]`) and the stored rows to `_log_login_save`.
  The stored rows can come from `_lock_site_rows`, or from `_site_rows` read before
  `_replace_site_rows`.
- Log `login=<before>-><after> before=[…] after=[…]`, in the same format as the per-site
  line.
- Add a test that clears a login and asserts both halves of the line.

### CR1-02 — minor — The RBAC deviation is not yet in `.claude/CLAUDE.md`, but the docs say it is

**Where:**
- `.claude/CLAUDE.md`, which this step did not change;
- `docs/Plan.MD` § 3, the "Roles per site" paragraph: "… recorded in `.claude/CLAUDE.md`";
- the brief, § 2 and § 3 Docs.

**Problem.** The brief requires the role-source deviation to be recorded in
`.claude/CLAUDE.md`. The coder reported this as departure 4.3.1, with the proposed text,
because a subagent may not edit CLAUDE.md. That is a reported departure, not a defect.
But the step is not complete until the text is in, and Plan.MD already points to it.

**Failure scenario.** A later planner or coder reads only CLAUDE.md and CLAUDE-COMMON's
RBAC pattern ("roles from the token"). They add a role check from the token, or a new
site key without putting it in `SITE_SCOPED`. The new key then fails on an assertion, or
is checked globally.

**Fix.** The user adds the proposed text of report § 4.3.1 under "Yantra Specifics"
before Done. At gate B the planner shows it as a to-do.

### CR1-03 — minor — Two cases from the removed `TestUserUnits` were not carried over

**Where:**
- `backend/tests/test_masters_api.py`: `TestUserUnits` was removed, "covered by the
  site-role tests";
- `backend/tests/test_site_roles_api.py`.

**Problem.** A1 rule 6 asked for the `/user-units` tests to be re-pointed. Most of their
meaning now lives in `TestLoginSave` and `TestEngineerAssignsTechnicians`. Two are lost:
- **An unknown `unit_id` in a site row → 400** (field `unit_ids`), not the FK's 500. This
  is the old `test_unknown_unit_id_is_400_and_nothing_changes`. It is not tested for
  either the whole-set save or `PUT …/sites/<id>`. `_check_grantable` handles it, but
  only the trades path tests it.
- **Atomicity of a whole-set save with a valid first row and a failing second row.**
  Nothing may be written: not the login, the first row, or the deletions.
  `test_row_rules` sends one row per request, so the "checks before writes" order of
  `_replace_site_rows` has no test.

**Failure scenario.** Someone refactors `_replace_site_rows` to check and write row by
row. A bad second row then leaves the first written, and the login set, if the
transaction scope ever changes. No test fails.

**Fix.** Add two cases to `TestLoginSave`:
- `unit_ids: [99999999]` → 400 `unit_ids`, on both routes;
- `sites: [valid A row, B row with a unit of A]`, on a person who already has a row at
  C → 400, and afterwards the person's rows and login are unchanged.

### CR1-04 — nit — The same membership filter is written out in several places

**Where:**
- `backend/auth_utils.py:276` (`membership_sites`) and `:298` (`_unit_pools`) each repeat
  `[m for m in memberships if m.role in SITE_ROLES]`. This is `access_core._valid`.
- `backend/masters.py:799-800` calls `no_login_role_error([clean["role"]])` twice.

**Problem.** The "a non-site role grants nothing" rule (BR3-02) lives in three places. A
change to it in one place (for example, a role made dormant) would miss the others.

**Fix:**
- Make `access_core._valid` public, for example as `valid_memberships`, and use it in
  `auth_utils`.
- In `put_person_site`, keep the message in a local variable.

### CR1-05 — nit — A conftest helper is named `test_user`

**Where:** `backend/tests/conftest.py:46`.

**Problem.** Pytest doesn't collect tests from conftest.py, so nothing breaks today. But
if a test module ever does `from conftest import test_user`, pytest collects the helper
there as a test, and it fails on its missing arguments. The name also reads as a test.

**Fix.** Rename it, for example to `harness_user`.

### CR1-06 — nit — The devops doc lost the redirect URI

**Where:** `smtw_erp_devops/docs/lob-apps/Yantra.MD`, step 5. This file is outside the
repo; the user commits it.

**Problem.** The edit is within the brief's scope: the client roles and the § 5.7 order.
But it drops "redirect URI `https://vel-yantra.mspv.app/*`" from the step. That fact now
lives only in Yantra's `docs/Keycloak.md` § 1, which the step points to. Someone working
from the devops doc alone no longer sees it.

**Fix.** Keep the half-line "redirect URI `https://vel-yantra.mspv.app/*`" in step 5.

## Checked and found consistent

- **Pure core** (`access_core.py`):
  - no DB, Flask or clock;
  - a membership with a non-site role is ignored entirely;
  - a query for site `None` matches no real membership;
  - `unit_ids_for` returns `None` only for admin, or when the token grants both the key
    and `equipment:read_all_units` (BR2-01; the injected-key test is there);
  - there is a `SITE_SCOPED` assertion in `has_key_at`, `unit_ids_for` and the shell's
    `has_perm_at` / `user_unit_ids`;
  - `compute_permissions(["maintenance_team"]) == []`.
- **The `require_auth` handler stays DB-free:**
  - memberships, the person id and the unit pools are loaded lazily and cached in `g`,
    never in the shared dev-stub dict;
  - they are read through `get_db()`, so they share the request's transaction;
  - every active unit is read only when some membership has all units;
  - the inactive or unknown person → no access (A1 rule 3), with a test that
    deactivating the person ends access on the next request.
- **Token parsing:**
  - `admin` / `it_admin` / `maintenance_team` are accepted, as realm or client roles;
  - old `maint_*` roles alone → 401;
  - stale roles are logged once, from `/auth/me` only (tested).
- **DB down:**
  - `/auth/me` catches `DBUnavailable` and returns the token permissions, `sites: null`
    and `db_unavailable: true`;
  - a check that needs memberships → 503;
  - IT admin's routes and units need no membership query (`every_unit_by_token`). All
    three cases are tested.
- **Site checks inside the choke points, keyed:**
  - `load_node_for_user` (with an assertion that a write names its key),
    `_load_target_node` and `_lock_target_unit`;
  - `_lock_node_for_change` (upload, title and remove: `equipment:edit`; restore:
    `equipment:purge_documents`);
  - purge, on `load_node_for_user` with `purge_documents`.

  Every write route in report § 2.3 matches the code. Move checks both sites, and so does
  re-parent. The upload is checked on the early plain read, so no file is written
  (tested). The site code comes from a plain read of `sites`, never from a locking read.
  Decision 4.1.7 (403 before the route's scrapped 409 in `load_node_for_user`) changes
  no answer that existed before: the user who now gets it was refused by `require_perm`
  before S011.
- **Scoped reads:**
  - the equipment list, node detail, document list, files and thumbnails use the
    `equipment:read` units;
  - the removed-documents list uses the `equipment:purge_documents` units (tested: listed
    at A, hidden at B, restore and purge at B → 403);
  - `/my-units` gains `edit_unit_ids`; the site-wide manager gets `all_units: false` and
    their site's active units;
  - the node detail carries `permissions` from `permissions_at_site`.
- **Site rows** (`masters.py`):
  - lock order: person → memberships → person_units → units, with the FK lock on the
    site after that. This matches `update_unit`, and `update_site` locks no units;
  - every 400 comes before every 403;
  - the no-login → Technician-only rule holds on both routes and on clearing a login;
  - an engineer is limited to `people:assign_technicians` at the site, with Technician
    before and after;
  - `masters:edit` passes, and the own-person rule comes first, on the stored login,
    normalised (tested with a case-varied user);
  - the diff keeps `granted_at/by` (tested);
  - "all units" clears the site's unit rows (tested);
  - `DELETE` of a missing row → 404;
  - the response is filtered like `GET /people`.
- **Login save (A1 rule 1):**
  - set, change or clear requires `sites`;
  - `sites` without a login → 400;
  - the whole set is checked first, then written in the transaction that writes the
    login;
  - an engineer's earlier row is replaced (tested).
- **`active` of a person with a login:** IT admin only, on the locked row; one's own →
  403.
- **Visibility (rule 5, refined at gate A):**
  - IT admin sees every row;
  - an engineer sees every row of a person without a login, and of a person with one only
    the rows at their assigning sites, plus `has_login`;
  - floor roles see no `sites`.

  All tested. `editable` and `assignable_site_ids` come from the backend.
- **RBAC config:**
  - `maint_supervisor` sits in `ROLES` after storekeeper and is off the ladder;
  - `TOKEN_ROLES`, `LOGIN_ROLE` (not in `ROLES`), `SITE_ROLES`, `TECHNICIAN_ROLE` and
    `SITE_SCOPED` (with `people:assign_technicians`) are defined;
  - `equipment:read_all_units` = IT admin only;
  - no site role holds `masters:edit` (tested);
  - no `admin` in any permission tuple;
  - fail-closed holds for unknown keys.
- **Migration v8:**
  - SQL only, and additive: two `CREATE TABLE IF NOT EXISTS`;
  - people are created by `INSERT … SELECT … WHERE NOT EXISTS`, so an inactive holder of
    the login gets the rows and stays inactive;
  - `INSERT IGNORE` into `person_units` keeps the original `granted_at/by`;
  - there is no `DROP` of `user_units`, and no earlier migration was edited;
  - the PK and FK names match A1 rule 6;
  - `test_migration_v8` rewinds `db_version` and runs `init_db` twice (rule 7).
- **Security:**
  - every new route is gated (`people:assign_technicians` on both per-site routes);
  - the actor always comes from the token (`actor()`), never from the client;
  - every SQL value is a placeholder; the f-strings hold only placeholder lists and code
    constants.
- **No swallowed exceptions:** the only `except` added catches `DBUnavailable` in
  `/auth/me`, by design.
- **No deprecated APIs.** No new dependency.
- **Frontend:**
  - `NoAccessView` sits inside the shell with the top bar, and shows both messages
    (rule 5 text "ask IT or your engineer");
  - the new 401 text is in place;
  - the edit buttons on a node follow the node's `permissions`;
  - the create and move pickers use `edit_unit_ids`, and `filterableUnits` uses the read
    units;
  - the "Unit access" section is gone;
  - Team has "Sites and roles": rows saved one by one, stopping at the first refusal and
    reloading the person; the role select is Technician-only without a login; a login
    change sends the whole set and shows the "gives access as" line.

  `navigation.test.js` has the supervisor and `people:assign_technicians` rows.
- **Docs:**
  - Plan § 1, § 2, § 3, § 5 and § 9.11;
  - Maintenance-Philosophy § 11;
  - Keycloak.md § 3.2, § 4, § 5, § 6 and § 7;
  - the `DEV_STUB_ROLE` comment;
  - the README index row.

  All are within the brief. Departures 4.3.1–4.3.3 are reported. The class-document
  upload test was dropped with S009. The race test is sequential, as A1 phrases it ("run
  after the login is committed").
- **Accepted by the brief, noted only:**
  - sites are read without a lock (§ 5.5). An all-units grant can therefore land on a
    site that is deactivated at the same moment; the row counts as "kept", as § 5.5 lets
    it;
  - the brief's "400 before 403" order lets an engineer tell, through the
    inactive-site/unit "kept" rule, whether a person holds a row at a site they can't
    see. The impact is negligible.
- **Manual checks:** the report's `## Manual checks` has all four **important** checks
  of brief § 8 as unticked boxes, and the plain ones as a list.

## Manual browser checks still needed (user)

Important (unticked in `3-impl-report.md`):
- [ ] Only `maintenance_team`, no site role → the "no access yet" page, with the name and
  Sign out in the top bar.
- [ ] As IT admin in Team: give a test person Manager at SMTW (all units) and Engineer at
  VEL (one unit). As that person: all of SMTW, with edit; one VEL unit, with edit; the
  other VEL units invisible.
- [ ] Change the VEL role to Operator. After a page load, the edit buttons on VEL
  equipment are gone, and a direct edit is refused (403).
- [ ] The production switch-over (report § 5.1), in that order.

Also worth a look:
- the S007 guard on a change to a site row only;
- legacy rows shown as "No role";
- as an engineer: the Technician-only select, and an Operator row shown read-only;
- the "Adding this login gives access as" line;
- clearing a manager's login is refused;
- DB stopped: IT admin still sees Settings › Database, and a maintenance user gets the
  "database unavailable" message;
- `DEV_STUB_ROLE = "maintenance_team"`.
