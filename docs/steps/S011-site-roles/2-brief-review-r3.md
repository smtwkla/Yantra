```
Step: S011 — Roles per site, held in Yantra
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S011 — Brief review, round 3

**Verdict: one `major` finding is open** (BR3-01), and it is a text defect, not
a design one: the rules section § 5.3 still carries the pre-BR2-01 "every
unit" shortcut, contradicting § 3, § 7 and § 8. One sentence fixes it. No
blocker. All eight round-2 answers are otherwise reflected in the brief text
(table below). The three minors are small rules that close the last
fail-open and skip paths I could find in the access core and the own-access
check; the nits are stale wording after two revisions.

Read for this review: the brief as revised after round 2; my round-1 and
round-2 reviews; `docs/steps/README.md`; `docs/Plan.MD` § 1, § 3, § 5, § 9;
`docs/Maintenance-Philosophy.md` § 11; `.claude/CLAUDE.md`,
`.claude/CLAUDE-COMMON.md` § RBAC Pattern, `.claude/SMTW-WebApp-Base.md`
§ RBAC Pattern; S010's brief (v8, the S011 touchpoint); the working-tree code
(S009 uncommitted, `git diff -w --ignore-cr-at-eol`): `backend/auth_utils.py`,
`config_rbac.py`, `app.py`, `equipment.py`, `documents.py`, `masters.py`,
`masters_core.py`, `api_common.py`, `db_helpers.py`, `local_db.py`,
`settings.py`, `config.py`, `example_secrets_app.py`, `tests/conftest.py`,
`test_auth.py`, `test_rbac.py`, `test_equipment_api.py` (unit access,
permissions, my-units), `test_masters_api.py` (user units),
`test_removed_documents_api.py`; `frontend/src/stores/auth.js`,
`stores/equipment.js`, `stores/navigation.js`, `router/index.js`, `App.vue`,
`components/layout/AppTopbar.vue`, `views/masters/UserUnitsPanel.vue`,
`tests/navigation.test.js`; the devops `docs/lob-apps/Yantra.MD`.

---

## Round-2 answers verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR2-01 key-aware "every unit" shortcut | § 3 `unit_ids_for` (`None` only for admin, or token grants both `key` and `equipment:read_all_units`), § 7 row, § 8 pure fail-open guard with an injected key | **partly** — § 5.3's first bullet still states the old rule; BR3-01 |
| BR2-02 check inside the three choke points | § 5.4 (`load_node_for_user` keyed, assertion when `for_update`; `_lock_node_for_change`; `_lock_target_unit`, `_load_target_node`; `site_id` on `_NODE_COLUMNS` and `_LOCK_UNIT`; site code from a plain read), § 7 row, § 8 one case per choke point plus the remaining routes at B | yes |
| BR2-03 own access refused | § 5.5 "Not your own access" (403 for every role), § 5.6 (the dialog does not offer it), § 7 row, § 8 "Own access", § 9.6 for the user | yes — one normalisation rule to state, BR3-03 |
| BR2-04 WARNING from `/auth/me` | § 3 `stale_roles`, § 5.1 (once per page load, not per request), § 8 (one WARNING from `/auth/me`, none elsewhere) | yes |
| BR2-05 `PUT /user-access` rules | § 5.5 (unknown site 400 field `sites`; inactive site kept, not granted, still counts; body-shape 400s; all-units deletes unit rows; lock order rows → units → deletes and inserts, the implicit FK lock named), § 6 `active`, § 8 "User access body" | yes |
| BR2-06 harness and core edges | § 5.8 (token-role fixture writes nothing; `nobody` never a wildcard), § 3 rules of the core (`('*',)` only for `SITE_ROLES`; site `None` matches nothing; the shell asserts an int), § 8 (three `test_auth` rejection cases switched) | yes — the `SITE_ROLES` guard needs to cover every key, BR3-02 |
| BR2-07 lazy loader and `g.user` | § 3 (`get_db()`; `role` computed in `/auth/me`, `null` for login-only; `SITE_SCOPED` asserted; the units query only when some membership has `all_units`) | yes — one signature slip, BR3-05 |
| BR2-08 small points | § 5.7 step 4 after rollback is unwanted; § 5.6 "Add user" guard kept; § 6 `units: []` and `active`; § 5.4 403 fields; § 8 DB-down case for a login-only user | yes |

---

## Major

### BR3-01 — `major` — § 5.3 still states the pre-BR2-01 rule: "holders of `equipment:read_all_units`: every unit", for any key

**Problem.** § 5.3 "Where (accessible units)", first bullet:

> `admin` and holders of `equipment:read_all_units` (IT admin): every unit.

That is the rule BR2-01 replaced. § 3 (`unit_ids_for` → `None` **only** when
the user is admin, or the token roles grant both `key` and
`equipment:read_all_units`), § 7 ("Every unit" only when the token grants
both …) and § 8 (the injected-key test) all carry the new rule; § 5.3, the
rules section the coder works from, carries the old one. The round-2 log
entry lists "§ 3, § 7, § 8" as the places changed, so § 5.3 was simply not
revisited.

**Why it matters.** It is the one fail-open rule found in two rounds, now
stated both ways in the same brief. A coder following § 5 as "the rules"
writes the shortcut as `has_perm("equipment:read_all_units") → None` — which
is exactly today's code — and only the pure test of § 8 catches it, after
which the coder has to decide which section wins. The brief should not leave
a security rule to be settled by a failing test.

**Options.**
1. **Replace the bullet (recommended).** "`admin`, or a user whose **token
   roles** grant both `key` and `equipment:read_all_units` (IT admin, for the
   keys it holds): every unit (`None`). For any other key, IT admin is scoped
   like everyone else, by its memberships (BR2-01)." Nothing else changes.
2. Delete the bullet and point at § 3. Weaker: § 5.3 is where the coder looks.

---

## Minor

### BR3-02 — `minor` — A membership whose role is not in `SITE_ROLES` must grant nothing at all, not only no `('*',)` keys

**Problem.** § 3: "`('*',)` at a site is granted only when the membership's
role is in `SITE_ROLES`, so a bad role string in the DB grants nothing." The
first half does not give the second. For a non-wildcard key the natural core
is `any(r in PERMISSIONS[key] for r in expand_roles([role]))`; with a
membership row whose `role` is `it_admin` (written straight into the table —
the API refuses it, § 5.5) that matches `masters:edit`, `masters:read_senior`,
`settings:edit`, `equipment:read_all_units`: the token-only keys. § 2 says
"nobody can make themselves IT admin through Yantra's database or screens";
through the database they could, by one row. § 8's test checks only that
such a row yields "no `('*',)` keys", so it would pass.

**Why it matters.** Someone with write access to the DB can do worse things,
so this is defence in depth rather than an exploit — but the brief makes the
claim, and the rule that makes it true costs one `if`. ISO 27001 A.8.2
(privileged access rights) is the control: IT admin's rights come from one
place (Keycloak), and the core should not have a second door.

**Options.**
1. **Skip the membership (recommended).** In `access_core`, a membership
   whose `role ∉ SITE_ROLES` is ignored for every key: it contributes nothing
   to `global_permissions`, `permissions_at` or `unit_ids_for`. Reword § 3,
   and change the § 8 case to "a membership with role `it_admin` or a typo →
   **no keys at all** (`permissions_at` = the token roles' keys only;
   `unit_ids_for` ignores its site)".
2. Validate at load time and log a WARNING. More code for the same effect.

### BR3-03 — `minor` — The own-access check must compare normalised names on both sides, or a mixed-case `preferred_username` skips it

**Problem.** § 5.5: 403 "when `username` is the actor's (normalised)". The
path username is normalised by `validate_username`; `actor()` returns
`g.user["username"]` as the token gave it (`preferred_username`). The code
already treats the two as different: `accessible_unit_ids` compares
`actor().lower()`, and `test_username_is_compared_lower_case` exists because
of it. If the coder writes `username == actor()`, an IT admin whose token says
`JDoe` sends `PUT /user-access/jdoe` → `"jdoe" != "JDoe"` → the check passes
→ the membership is written for `jdoe` → read back by `actor().lower()` →
effective. The preventive control of BR2-03 is then skippable by the one
person it targets. Keycloak lower-cases usernames by default, so this is
unlikely in production; it is still a rule the coder would decide alone.

**Options.**
1. **State it (recommended).** "403 when `username ==
   normalise_username(actor())`" (`masters_core.normalise_username`), and the
   § 8 own-access case sends the IT admin's username in a different case
   (`X-Test-User: Test_It_Admin` against `PUT /user-access/test_it_admin`).
2. Normalise `g.user["username"]` once in the token parser. Cleaner, but it
   changes `actor()` for every log line and `created_by` column; out of this
   step's scope.

### BR3-04 — `minor` — "Only IT admin grants memberships" rests on `masters:edit` never reaching a site role; nothing tests that

**Problem.** § 1 (user decision), § 2 (A.5.3) and § 7 say only IT admin edits
memberships. In code that is `PUT /user-access` under `masters:edit`, and
`masters:edit = ("it_admin",)`. A site role is granted through
`global_permissions` (§ 5.2: the union drives the global keys), so the day
someone adds `maint_manager` to `masters:edit` — Plan § 3 already pencils
engineers into `masters:read_senior` for phase 3, and the two keys sit
together — a manager at any site can grant themselves manager everywhere,
and the segregation the user asked for is gone with no test failing. § 8's
RBAC list checks `equipment:read_all_units` and `it_admin ∉ SITE_ROLES`, not
this.

**Recommendation.** Add to § 8 RBAC: "no key in `("masters:edit",)` is granted
to any role in `SITE_ROLES` (directly or through `ROLE_INCLUDES`)", with a
comment in `config_rbac.py` beside `masters:edit` saying why (S011 § 2,
A.5.3). One assertion; it makes the user's decision a tested invariant
rather than a convention.

---

## Nit

### BR3-05 — `nit` — Stale or imprecise wording after two revisions

- **§ 3 `access_core`:** "`permissions_at` and `unit_ids_for` assert `key in
  SITE_SCOPED`" — `permissions_at(token_roles, memberships, site_id)` has no
  `key`; it returns the full list the node detail needs (§ 6). The assertion
  belongs in `has_perm_at(key, site_id)` (shell) and `unit_ids_for` (core).
  § 8's "a non-`SITE_SCOPED` key → assertion" then names `unit_ids_for`.
- **§ 5.4:** "`_lock_node_for_change` gains the same parameter (upload, title,
  remove pass `equipment:edit`; restore and purge `equipment:purge_documents`)"
  — purge calls `load_node_for_user` directly (no scrapped check, by design,
  `documents.py` line 515) and passes the key there; only restore goes
  through `_lock_node_for_change`.
- **§ 3 `unit_ids_for(…, user_unit_ids)`:** the core must drop rows at sites
  where the user has no membership (§ 4, § 8), so the rows need their site:
  `user_units` as `(unit_id, site_id)` from `user_units JOIN units … WHERE
  u.active = 1`, not bare ids.
- **§ 5.8 `DEV_STUB_ROLE`:** say what `"maintenance_team"` or an unknown
  string does for the stub (login only, no membership → `NoAccessView`), as
  the test header's `nobody` is specified.
- **§ 3 frontend:** `pickableUnits` / `filterableUnits` in `stores/equipment.js`
  read `mine.all_units` and `mine.unit_ids`; with `edit_unit_ids: null` for
  every-unit users the pickers need the `null` case, one line.
- **Header:** `Date: 16-10-2026 (revised … after brief-review r1)` — r2 was
  answered too.

---

## Standards, in plain terms

The § 2 citations are accurate and complete for an access-control step; the
reading of each, for the record:

- **ISO 27001:2022 A.5.15 (access control)** — write down who may access what,
  based on what the business needs; here "role at the site you work at".
- **A.5.18 (access rights)** — grant, review, change and remove rights in a
  controlled way as people join, move and leave; the User access screen is
  the one place that happens, and § 5.5 keeps a membership at a deactivated
  site until IT removes it (leavers are removed, not forgotten).
- **A.8.3 (information access restriction)** — the code enforces the policy:
  the per-site checks of § 5.4 and the key-scoped lists of § 5.3.
- **A.5.3 (segregation of duties)** — the people who grant rights do not use
  them and vice versa: IT admin grants, cannot grant to themselves (BR2-03),
  and no site role can grant (BR3-04 makes that a tested fact).
- **A.8.2 (privileged access rights)** — privileged rights come through one
  authorisation path; IT admin and admin stay in Keycloak, and the core must
  not let a DB row impersonate a token role (BR3-02).
- **A.8.15 (logging)** — every membership change is logged with actor, user,
  before and after.
- **ISO 55001:2024 § 5.3** — asset-management responsibilities are assigned
  and communicated; per plant here, which a role per site models directly.

ISO 14224, EN 13306, SMRP and TPM do not bear on access control and are
rightly not cited. The departure from the base RBAC pattern (maintenance
roles from the DB, per site; token roles for login and IT admin) is named in
§ 2 and recorded in `.claude/CLAUDE.md`, as CLAUDE-COMMON allows.

---

## Checked and found consistent

- **Fail-closed paths.** No token role and no membership → `[]` permissions
  (`maintenance_team ∉ ROLES`, so `('*',)` keys are not granted), `NoAccessView`
  with name and Sign out in `AppTopbar`, 403 on every data endpoint. A node at
  a site without membership is 404 (nothing revealed); a write at a site where
  the role is too low is 403 after the existing refusal order, so no existing
  answer changes.
- **No check can be skipped.** Every node write passes `load_node_for_user`
  with `for_update=True` (edit, status, notes, type, title, remove, restore,
  purge), every target unit `_lock_target_unit` (create, move), every target
  parent `_load_target_node` (part create, re-parent); the keyed parameter
  with the assertion means a route cannot write without naming its key. Class
  and type documents (S009) and technicians (S010) are site-less and keep the
  global key, as § 5.4 and § 9.5 say.
- **No privilege escalation through the token.** `maintenance_team` grants
  nothing; `it_admin` and `admin` cannot be stored as a site role by the API
  (`SITE_ROLES` validation); the wildcard `site_id = None` cannot come from
  production data (`NOT NULL`, `_parse_id`). With BR3-02 the core also ignores
  a hand-written row.
- **DB unavailable.** `require_auth` stays DB-free; token-granted keys need no
  query; a membership query raising `DBUnavailable` becomes the same 503 the
  route would give; `/auth/me` catches it so IT admin reaches Settings ›
  Database (`settings:read` from the token, `db_status()` never raises) and a
  login-only user sees the DB message rather than "no access yet". Matches
  `.claude/CLAUDE.md` "DB may not exist".
- **No cross-request cache**, so a membership change applies on the next
  request; the manual check "after a page load" describes the UI correctly.
- **Lock order** holds: `PUT /user-access` user rows → units (`_check_grantable`)
  → implicit shared site lock (FK), which is unit → site as `update_unit`;
  sites are read without a lock elsewhere. A site cannot be deactivated while
  it has active units (`update_site`), so a membership at an inactive site
  yields no active units and the "still counts for the global union" rule is
  harmless. `equipment.py` never locks sites, user_units or memberships.
- **Switch-over order** is right: today's `validate_keycloak_token` ignores
  names not in `ROLES`, so `maintenance_team` is harmless before the deploy;
  v9 only adds a table, so the previous release runs on the new schema.
- **Harness.** `X-Test-Role: <site role>` as a wildcard membership keeps every
  listed legacy case's meaning; the three senior-role cases parametrised over
  `maint_manager, it_admin, admin` (`test_senior_roles_see_every_unit`,
  `test_senior_roles_get_all_units`) are handled by § 5.8 (token-role fixture
  writes nothing) and § 8 (`/my-units` for the manager rewritten).
  `test_removed_documents_api` already monkeypatches `PERMISSIONS`, so the
  injected-key test of § 8 has a precedent.
- **S009 and S010 touchpoints.** The uncommitted S009 diff changes only the
  documents blueprint prefix, the `documents.py` owner structure (one owner
  lock per write, `_lock_node_for_change` for node writes) and migration v7;
  the brief's description of `documents.py` matches the working tree. S010's
  v8 and `technicians:edit` (global) are as the brief assumes; `conftest._TABLES`
  will carry S010's tables by the time S011 is coded.
- **Scope.** Still one migration, one pure module, one panel replaced; no
  supervisor role, no manager self-service, no role conversion; the only new
  constants are `TOKEN_ROLES`, `LOGIN_ROLE`, `SITE_ROLES`, `SITE_SCOPED`. Not
  over-engineered.
- **Docs to update at approval** (Plan § 1, § 3 first line and matrix, § 5,
  § 9 Q1; Maintenance-Philosophy § 11; `.claude/CLAUDE.md`; the devops doc
  step 5; `example_secrets_app.py`) match what the text changes.
