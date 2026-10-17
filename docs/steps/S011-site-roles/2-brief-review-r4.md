```
Step: S011 — Roles per site, held in Yantra
Doc: brief-review r4
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S011 — Brief review, round 4 (amendment A1 only)

**Verdict: three `major` findings are open** (BR-A1-01, BR-A1-02, BR-A1-03).
No blocker. This is the one round the user asked for on the amendment, so the
answers are not re-reviewed unless the user asks. The amendment's shape is
right: one register of people, roles hanging off the person, the same choke
points, lazy loading and fail-closed rules as the approved brief. The majors
are the three places where "roles become access" happens without IT admin
holding the pen, and where the migration as written cannot be run by the
engine or rolled back.

Scope: § 10 A1 of the brief, read against the approved § 1–§ 9, S010's
amendment A1 (reviewed in parallel; the interface between the two is checked
below), `docs/Plan.MD` § 1–§ 3, § 5, § 9, `docs/Maintenance-Philosophy.md`
§ 11, `docs/Keycloak.md`, `.claude/CLAUDE.md`, `CLAUDE-COMMON.md` § RBAC,
`SMTW-WebApp-Base.md` § RBAC, and the working tree (S010 uncommitted):
`backend/local_db.py` (the migration engine), `auth_utils.py`,
`config_rbac.py`, `masters.py`, `masters_core.py`, `equipment.py`
(`accessible_unit_ids`, `/my-units`), `api_common.py`, `db_helpers.py`,
`app.py`, `tests/conftest.py`, `test_masters_api.py` (the `/user-units`
cases), S010's `3-impl-report.md` and `4-code-review-r1.md`.

---

## Major

### BR-A1-01 — `major` — "Adding this login gives access as …" is a snapshot in a dialog, not a server-side control; the grant must carry the roles IT admin confirmed, in one transaction

**Problem.** Point 4 lets engineers write any role at any site on a person
without a login ("it only describes them"), and makes IT admin's *add login*
the moment those rows become access. The only control named at that moment is
the dialog text "Adding this login gives access as: SMTW Technician (FWMILL,
MCC1)…". Three gaps:

1. **The text is stale by design.** It shows the roles loaded when the dialog
   opened. An engineer's `PUT /people/<id>/sites` between dialog open and
   IT admin's save changes what is granted, and the locked "has a login" check
   of point 4 does not catch it: the engineer's write comes *before* the login
   is committed, so it passes. The test in A1 covers only the other order.
2. **Changing a login is a grant too.** Moving `username` from `a` to `b`
   moves every role of that person to `b` and revokes `a`; A1 speaks only of
   "adding".
3. **Nothing on the server says what IT admin agreed to.** The log line of
   § 5.5 records the engineer's role write (actor = engineer) and S010's
   update of `username` (actor = IT admin); no record ties the grant to the
   roles in force at that moment.

**Why it matters.** This is the one place A1 weakens the approved design,
where only IT admin ever wrote a membership (§ 2: A.5.3 segregation of duties,
A.8.2 privileged access). The amendment's own argument — "turning roles into
access is a visible, deliberate act" — holds only if the act carries the roles
with it. Otherwise an engineer who can set "manager, all units" at every site
on a no-login person has drafted an account that IT admin activates by typing
a username, and can even change the draft after IT admin read it.

**Options.**
1. **The login write carries the sites (recommended).** When a `PUT /people/<id>`
   (or `POST /people`) sets or changes `username`, the body must also carry
   `sites` in the § 5.5 shape; the server writes login and memberships in
   **one transaction** (person row locked, then the membership and unit rows,
   then units — the order of point 4), replacing whatever was there. A missing
   `sites` on such a write → 400 "Confirm the sites and roles this login gets".
   The Team dialog already shows both sections, so IT admin's save sends what
   is on screen; a concurrent engineer edit is simply overwritten by the
   roles IT admin confirmed. One INFO line records actor, person, login and
   the roles granted. Clearing a login needs no `sites`. Add the test: an
   engineer's role change committed *after* IT admin opened the dialog and
   *before* the save → the saved roles are IT admin's, not the engineer's.
2. Optimistic check: the login write carries the memberships' latest
   `updated_at`/`granted_at` and gets 409 if they moved. Works, but it is a
   second mechanism and still leaves the grant implicit.
3. Clear the person's roles when a login is set, so IT admin sets them in a
   second save. Race-free but throws away the engineer's description and
   doubles the work.

Whichever option: say that *changing* a login is the same act as adding one.

### BR-A1-02 — `major` — `active` on a person with a login is an access switch; an engineer can reactivate a leaver and restore their access, and anyone can reactivate their own person

**Problem.** Point 3 makes "active person with that login" the access
condition (good: A.5.18 leavers). But S010 A1 keeps `active` under
`people:edit` (engineers), and A1 restricts engineers only on *site roles* and
*login*. So:

- an engineer reactivating a deactivated person who still carries a login
  (S010 § 5.2 keeps the login on deactivation, by design) switches that login
  back on with every role it had — access restored by a non-IT role, the
  mirror of the "no-login → login" grant that A1 reserves for IT admin;
- an engineer deactivating a person with a login (say the manager's record)
  revokes their access; revocation is also a controlled act under A.5.18, and
  here it is open to every engineer at every site;
- the own-person rule names "login or site roles", not `active`: an IT admin
  whose own person was deactivated keeps token rights and can reactivate it,
  regaining whatever site roles another IT admin had given before.

**Why it matters.** The amendment's leaver story ("deactivate the person:
access ends") is only as strong as the rule on who may undo it. Reactivation
is the fail-open path; it costs one line of rule.

**Options.**
1. **Same rule as the login (recommended).** On a person **with** a login,
   changing `active` needs `masters:edit`, checked on the locked person row
   like the login and the roles (a `PUT` carrying `active` on such a person
   without it → 403 field `active`). Engineers deactivate and reactivate
   persons without a login freely. The own-person rule becomes "login, active
   flag or site roles". S010 A1 point 2/4 is amended to match ("covers name,
   employment, trades, and `active` for persons without a login"). Tests: an
   engineer's `PUT {active: 1}` on an inactive person with a login → 403;
   IT admin → 200 and access returns on the next request; own person → 403.
2. Restrict only reactivation (deactivation by an engineer stays allowed as
   the fail-safe direction). Fewer 403s, but an asymmetric rule to explain,
   and deactivation of a colleague's access by an engineer is still open.

### BR-A1-03 — `major` — The legacy migration cannot be run by the engine as written, is not re-runnable once `user_units` is dropped, and silently breaks § 5.7's rollback claim

**Problem.** Point 2 describes v8 as: create a person per unknown username,
move the `user_units` rows, **drop `user_units`**, and **log each created
person**. Against the working tree:

- `local_db.init_db` runs a list of SQL strings on an autocommit connection,
  commits each statement as it goes, logs once per migration and records the
  version only after the last statement (`local_db.py` lines 329–339). There
  is no Python step and no per-row logging. "Each created person is logged in
  the migration's output" therefore needs an engine change (a callable in
  `_MIGRATIONS`), which A1 does not list under "Where", or has to be dropped.
- Idempotency: with `DROP TABLE user_units` in v8, a re-run after a failure
  between the drop and the `db_version` insert (a lost connection, the
  GET_LOCK timeout) executes `INSERT … SELECT … FROM user_units` → error
  1146, every 30 s, for ever. The engine's rule since v5 is "every statement
  safe to run twice"; this one isn't.
- § 5.7 step 4 still says "v8 only adds a table, so the old release runs on
  the new schema", and the old `maint_*` roles are kept until "a rollback is no
  longer wanted". After A1's v8 the previous release reads a dropped table in
  `accessible_unit_ids` → every equipment request 500s. The rollback the
  switch-over relies on is gone and the text doesn't say so.

**Options.**
1. **SQL-only, additive v8 (recommended).**
   - `INSERT INTO people (name, employment, username, created_by)
     SELECT DISTINCT uu.username, 'direct', uu.username, 'migration-v8' FROM
     user_units uu WHERE NOT EXISTS (SELECT 1 FROM people p WHERE p.username =
     uu.username)` — safe twice;
   - `INSERT IGNORE INTO person_units (person_id, unit_id, granted_at,
     granted_by) SELECT p.id, uu.unit_id, uu.granted_at, uu.granted_by FROM
     user_units uu JOIN people p ON p.username = uu.username` — safe twice,
     and keeps the original grant trail (A.8.15), which "moves" should say;
   - **no drop in v8.** `user_units` stays, unread by the new code, and is
     dropped by a later step's migration once the release is settled (as
     § 5.7 step 4 is for the Keycloak roles). § 5.7 step 4 then stays true,
     with one sentence: "a rollback after v8 sees the unit rows as they were
     at the deploy; access given since is in `person_units` only";
   - the created persons are found in Team by `created_by = 'migration-v8'`
     (the name is the username; the open point stands). Drop the per-person
     log line; log the count if the engine is given a row-count hook, or not
     at all.
   - State the two edge cases: a username whose person **exists but is
     inactive** attaches to it (no access until IT admin reactivates — the
     A.5.18 leaver stays out); and `created_by` / `created_at` for the created
     rows.
2. Add a Python step to the engine and keep the drop, with the drop in its own
   later version (v9) so v8 is re-runnable. More engine code for a one-off.

Either way the "idempotent on a re-run" test needs a harness: see BR-A1-07.

---

## Minor

### BR-A1-04 — `minor` — The own-person rule must also stop giving yourself a login, and compare normalised names on the locked row

**Problem.** "Nobody edits their own person's login or site roles" reads as
"the person whose login is mine". That misses the path where no such person
exists yet: an IT admin (no person record, or an inactive one) creates a
person, sets roles (`people:edit`, no login yet), then sets `username` to
their own Keycloak name — the § 5.5 self-grant BR2-03 closed, reopened by two
saves. The reverse order (login first, then roles) is caught by the rule as
written; this order is not.

**Recommendation.** State three checks, all on the **locked** person row and
all with `normalise_username(actor())` (BR3-03; `people.username` is stored
normalised by `_parse_login`):
- `POST /people` or `PUT /people/<id>` with `username ==
  normalise_username(actor())` → 403 field `username` "You can't give yourself
  a login";
- `PUT /people/<id>/sites`, and `active` (BR-A1-02), on a person whose stored
  `username == normalise_username(actor())` → 403 "You can't change your own
  access";
- the test sends a case-varied `X-Test-User`, as § 8's own-access case does.

### BR-A1-05 — `minor` — Engineers now see everyone's access; and the two-key rule of `PUT /people/<id>/sites` should be spelled out

**Problem.**
1. Point 5 returns `sites` on `GET /people` to `people:edit` holders. With
   the login already unmasked for them (S010 § 5.3), every engineer at any
   site sees the full access list of every plant: login, role, units. The
   approved brief and Plan § 3 keep that view at `masters:read_senior`
   ("needed to view users' unit access; engineers may be added in phase 3").
   The widening may well be wanted (engineers must see roles to describe
   people), but it is a change to Plan § 3 and to A.5.15's "on business need"
   that A1 doesn't name. Options: accept and record it in Plan § 3 at approval
   (recommended: `sites` for `people:edit`, the login as today), or return
   `sites` to engineers only for persons **without** a login (the ones they
   may edit) and the rest to `masters:read_senior`.
2. The route is gated by two keys depending on the record. Say it the way the
   coder must write it: `@require_perm("people:edit")` on the route (the cheap
   check), then inside the transaction, after `_lock_row("people")`, `if
   person["username"] is not None and not has_perm("masters:edit")` → 403
   "Only IT admin changes the access of someone with a login". Decorating with
   `masters:edit` locks engineers out; decorating with `people:edit` and
   forgetting the inner check fails open.
3. `GET /people` `sites` shape: say it is § 6's `[{site_id, site_code, active,
   role, all_units, units}]`, with `role: null` for the legacy unit rows and
   `units: []` for an all-units site, so the Team dialog and the old panel
   logic carry over.

### BR-A1-06 — `minor` — Files, docs and tests A1 changes but doesn't list

The coder would otherwise find these one by one:

- **Plan.MD:** § 2 "Not in v1" still lists "A production-supervisor role — none
  planned … no maintenance-supervisor role either"; § 3 the role table (a
  `maint_supervisor` row: who, can do) and the matrix (a column), and the
  sentence under the table "Production supervisors have no special role"; § 3
  "Roles per site" paragraph (now by person); § 5 rows `user_units`,
  `memberships` (by person), `technicians`, `technician_trades` →
  `people`, `person_trades`, `person_units`; § 9.11 ("no supervisor role");
  § 1 "Shop-floor access" (user → units becomes person → units).
- **Maintenance-Philosophy § 11:** "Production supervisors are left out for
  now" → the supervisor's place (CIL, readings, raising tickets at their
  units; audits later).
- **Keycloak.md:** § 3.2 and § 4 ("Yantra › Masters › User access" → Team),
  § 6 leavers ("remove their access in Yantra › User access" → deactivate the
  person in Team, by IT admin), § 7 ("No membership in Yantra › User access").
- **Frontend text:** § 1.4 / `NoAccessView` "ask IT to add you in User
  access" → "in Team"; the 403 texts above.
- **Tests:** `test_rbac.py::test_role_matrix` and `navigation.test.js` gain a
  supervisor row (operator's keys exactly; no `equipment:edit`, no
  `people:edit`); `conftest._TABLES` (`user_units` → `person_units`,
  `memberships`, `people`, `person_trades`, child first); § 8's "four
  `test_masters_api.py` cases calling `/user-units`" is about nine (lines
  248–549), all re-pointed to `/people/<id>/sites` with a person per
  username.
- **Data model details:** `person_units` `PRIMARY KEY (person_id, unit_id)`,
  FK names (`fk_person_units_person`, `fk_person_units_unit`,
  `fk_memberships_person`); `ROLES` order with the supervisor between
  storekeeper and technician is display-only (`g.user["role"]`) — say so, or
  put it after technician, where its rights sit.
- **`.claude/CLAUDE.md`** and the devops `Yantra.MD` step 5: "User access" →
  Team.

### BR-A1-07 — `minor` — How the migration test runs against a v7 state is unspecified

**Problem.** A1 lists "migration v8 on a DB with legacy `user_units` rows …
idempotent on a re-run". The test DB is brought to the latest version once per
session (`conftest._clean_tables` → `ensure_schema`, with the process-global
`_schema_ready`), and no test today re-runs a migration. The coder has to
invent the harness.

**Recommendation.** One of: (a) a test that, on its own connection, deletes
the `db_version` row 8, drops the v8 tables, recreates `user_units` with the v2
DDL and two rows (one username with an existing person, one without, one
inactive person), calls `init_db` twice and asserts the rows, persons and
`db_version`; it must restore the schema for the tests that follow, so mark
it to run last or in its own module with a teardown; or (b) a throwaway
database created and dropped by the test (`vel_yantra_migtest`, the test
user needs CREATE rights — check `tooling/dev/init-test-db.sql`). (a) needs no
new rights; recommend it, with the test asserting idempotency by the second
`init_db` changing nothing.

---

## Nit

### BR-A1-08 — `nit` — Standards: name the TPM basis of the supervisor, flag the EN 15628 term clash, cite A.5.16, point Plan § 9.10 at it

- **TPM, autonomous-maintenance pillar.** In TPM the production supervisor
  (line or shift leader) owns the line's autonomous maintenance: operators do
  CIL; the supervisor checks it is done, audits the standards and raises what
  operators can't fix. That is exactly A1's supervisor (operator's rights now,
  "more reports later" = CIL compliance of their units). Say so in A1's
  Standards; it also answers Plan § 9.10 ("does an engineer verify CIL jobs?")
  — a pointer there: "candidate: the supervisor, phase 4".
- **EN 15628** (cited in S010 § 2) uses *maintenance supervisor* for a
  **maintenance-side** level, between technician and manager — in Yantra that
  is the engineer. A1's `maint_supervisor` is the production supervisor. One
  sentence avoids the next reader mapping the key to the standard's level.
  (The `maint_` prefix is the app's namespace, as `maint_operator` already
  shows; no rename needed.)
- **ISO 27001:2022 A.5.16 (identity management):** one identity per person,
  assigned, changed and removed through a lifecycle. A1 implements it: the
  login lives on the person, is unique (`uq_people_username`), and dies with
  the person's `active`. Worth citing next to A.5.18, since it is the control
  BR-A1-01 and BR-A1-02 serve.
- "`SITE_ROLES`" in point 1 lists six roles; § 3's "`ROLES` unchanged (the six
  roles)" becomes seven. Update the count.

---

## S010 A1 ⇄ S011 A1 interface

Checked both texts side by side:

| S010 A1 says | S011 A1 says | Fit |
|---|---|---|
| `people`, `person_trades`, `uq_people_username`; v7 edited in place | memberships FK `people`; `person_units` | yes (v7 has never been deployed; production is at v6) |
| login set only with `masters:edit`; engineers see it read-only | adding a login is IT admin's; the dialog warns | yes — BR-A1-01 asks the write to carry the roles |
| `people:edit` covers `active` | deactivating ends access | **gap** — BR-A1-02 |
| deactivated person keeps the login | the active person with that login | yes; an inactive person's login stays taken and grants nothing |
| lock order person → trades | person → memberships/unit rows → units (→ site by FK) | yes; both lock the person first; `update_unit` is unit → site, same as the units → site tail here, so no cycle |
| `GET /people` masks `username` unless `people:edit` | adds `sites` for `people:edit` / `masters:read_senior` | yes — BR-A1-05.1 records the widening |
| Masters tab order ends "User access (until S011 A1 merges it)" | "User access" section goes | yes |
| duplicate-login message "Another person already has this login" | — | yes |

---

## Standards, in plain terms (what A1 adds to § 2)

- **ISO 27001:2022 A.5.18 (access rights)** — grant, change and remove rights
  as people join, move and leave. A1 gives it one place: the person. Joiner =
  create the person, IT admin adds login and roles; leaver = deactivate the
  person. BR-A1-02 is about who may flip that switch.
- **A.5.16 (identity management)** — one identity per person, through a
  lifecycle; see BR-A1-08.
- **A.5.3 (segregation of duties) / A.8.2 (privileged access rights)** — the
  people who describe where someone works (engineers) are not the people who
  grant access (IT admin). A1 keeps that in words; BR-A1-01 makes the grant
  carry the roles so it holds in code.
- **A.8.15 (logging)** — the moved unit rows should keep their `granted_at/by`
  (BR-A1-03), and the grant at login-add should be logged with its roles.
- **ISO 55001:2024 § 5.3 and § 7.2** — responsibilities per plant, and the
  competence of *all* people doing work on the assets: roles on a no-login
  person are the "responsibilities" part of that register.
- **TPM autonomous maintenance** — the supervisor role's basis (BR-A1-08).

---

## Checked and found consistent

- **The § 5 security design is unchanged where A1 says it is.** Token roles
  from Keycloak; `maintenance_team` grants nothing; memberships loaded lazily
  on the request's connection; the three choke points keyed; `unit_ids_for`'s
  key-aware "every unit" rule; fail-closed when no person, an inactive person,
  or no membership; `DBUnavailable` → 503 and `/auth/me`'s `db_unavailable`.
  Looking up the person by `people.username = normalise(token name) AND
  active = 1` is one join on the existing membership query, no new path.
- **No DB row can impersonate a token role.** `role` is still validated
  against `SITE_ROLES`, and BR3-02's "ignored entirely" rule still covers a
  hand-written `it_admin` row. `it_admin` and `admin` remain token-only.
- **Duplicate logins** are impossible by `uq_people_username` (general_ci, so
  case-insensitive) and `_parse_login` normalises; the token lookup compares
  the same normalised value. A deactivated person's login stays taken (S010
  § 5.2), so a leaver's name can't be quietly given to someone else.
- **The engineer-after-login race is closed** in the direction A1 tests: both
  `PUT /people/<id>` and `PUT /people/<id>/sites` lock the person row first,
  so an engineer's role write that starts after IT admin's login commit sees
  the login and gets 403. The other direction is BR-A1-01.
- **Lock order** (point 4) person → membership/unit rows → units → site (FK,
  implicit shared) is the same tail as the approved § 5.5 and `update_unit`'s
  unit → site; `_unit_is_referenced` reading `person_units` is a plain read.
  No cycle with S010 A1's person → trades.
- **Harness (§ 5.8) carries over:** `X-Test-Role: <site role>` stays a
  wildcard membership with units from the DB (now via a person with that
  login, created by `user_with_units`); `maintenance_team` + `X-Test-User`
  goes through the person and the real `PUT /people/<id>/sites`; `nobody`
  stays nothing. Supervisor under the header behaves like operator with the
  wildcard, as any site role.
- **Supervisor in the policy:** `ROLE_INCLUDES["maint_supervisor"] =
  ("maint_operator",)` gives exactly the operator's keys today (`equipment:read`,
  `masters:read` via `('*',)`), no `equipment:edit`, no `people:edit`, no
  `masters:*`; nothing in the ladder points at it, so no maintenance role
  inherits it. `SITE_ROLES ⊂ ROLES`, `it_admin ∉ SITE_ROLES`, and BR3-04's
  "no site role holds `masters:edit`" all still hold.
- **Legacy rows stay visible** (BR1-06's intent): migrated persons carry unit
  rows and no membership, so Team shows them with `role: null` until IT admin
  adds a role; the first save replaces them.
- **Scope.** One new role, two renamed tables, one endpoint replacing one,
  one dialog section replacing one panel. Not over-engineered; the amendment
  is still one reviewable slice with the approved step.
