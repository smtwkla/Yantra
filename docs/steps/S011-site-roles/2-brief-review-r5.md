```
Step: S011 — Roles per site, held in Yantra
Doc: brief-review r5
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S011 — Brief review, round 5 (gate-A decision "Engineers assign technicians to sites")

**Verdict: no `blocker` or `major` finding is open.** Four `minor`, one `nit`.
One round, as the user asked. The delegation is sound: the engineer's grant is
bounded on three axes (one site, one role at the bottom of the ladder, never
their own person), is checked on the locked person row, and uses the per-site
route so an engineer never touches rows at a site they can't see. The findings
are about the text the coder would otherwise have to resolve alone (stale lines
of A1 that the decision silently supersedes, the dialog's save contract, which
units an engineer may give) and the tests the new key breaks.

Scope: the last two bullets of "Amendment A1 — user decisions at gate A" of
`1-brief.md`, read against § 3, § 5.2–5.5, § 5.8, § 8, A1 points 3–7, A1 rules
1–8, S010 A1 (points 2, 4; rules 1–3, 7), `docs/Plan.MD` § 1–§ 3,
`CLAUDE-COMMON.md` § RBAC, `SMTW-WebApp-Base.md` § RBAC, and the working tree:
`backend/config_rbac.py`, `auth_utils.py`, `masters.py` (`_lock_row`,
`replace_user_units`, `_check_grantable`, the technicians routes),
`tests/conftest.py` (`_inject_test_user`, `user_with_units`), `tests/test_rbac.py`
(`test_role_matrix`), `frontend/tests/navigation.test.js`.

---

## Escalation paths checked (the orchestrator's list)

All closed by the text as written, with one caveat each where noted:

| Path | Result |
|---|---|
| Engineer at A affecting rows at B | Closed: the route is per site; `has_perm_at("people:assign_technicians", B)` fails for a real membership at A only. Caveat: under `X-Test-Role: maint_engineer` the harness membership is a wildcard (§ 5.8), so the "at B → 403" test must go through `maintenance_team` + a real person (BR-A1G-04). |
| Turning a non-Technician row into Technician, or removing it | Closed: "both the stored and the new role are Technician (or absent)". A downgrade of a manager row would be a revocation (A.5.18) and is refused. |
| Rule 1's whole-set login save vs an engineer's per-site write | Both lock the person row first, so they serialise. An engineer row written *before* IT admin's save is replaced by the set IT admin confirmed (BR-A1-01's intent); one written *after* sees the login and is now **allowed** — that is the delegation. Losing a Technician row to the whole-set replace is the fail-safe direction. Consistent. |
| "Without a login only Technician" when IT admin clears a login | Gate bullet 1 makes the clearing save carry a Technician-only (or empty) set; the rows an engineer added are Technician by construction, so the two rules never fight. Consistent. |
| `all_units` on a Technician row as a widening | An engineer with chosen units may give a technician **every** unit of the site; the site, not the engineer's units, is the boundary the user chose. Not an escalation of rights (Technician is the lowest maintenance role) but the text should say it (BR-A1G-03). |
| A Technician row giving a login holder access at a site where they had none | Intended ("with a login this is real access, kept low"). It also lets an engineer give a Technician row to an **IT admin's** person; that is a two-person act (the segregation § 5.5 asks for), and another IT admin could already do it under the approved text. No new path. |
| Own person | Closed by rule 4 (stored login == `normalise_username(actor())` on the locked row). An engineer can't reach the other order (set a login to themselves): logins are IT admin's (S010 A1). |
| Concurrency with IT admin edits | Lock order person → membership row → units on both routes; same head as rule 1 and S010's person → trades; the tail unit → site (FK) matches `update_unit`. No cycle. |
| Per-site API vs the whole-set endpoint | Two write paths remain (per-site rows; the whole-set body inside the login save). Same pure validator per row keeps them one rule. The dialog's save contract is unspecified (BR-A1G-02). |
| Visibility | Per-site filter for persons with a login; `has_login`, never the username (S010 A1 rule 7). The PUT/DELETE responses must apply the same filter (BR-A1G-02). |
| `people:assign_technicians` as a `SITE_SCOPED` key | Fits § 5.2: `has_perm_at` = admin, or a token role grants it (`it_admin` is in the tuple, so IT admin passes at every site, as it does for `equipment:edit`), or the role at that site. `unit_ids_for` is never called with it. The `masters:edit` branch must be tested **first**, or IT admin falls under the Technician-only limit; the test "IT admin → any role" catches that. |

---

## Minor

### BR-A1G-01 — `minor` — The decision supersedes A1 point 4 and rule 5 without saying so; the coder has two rules for who writes a site row

**Problem.** The decision is self-contained ("each is allowed when the actor
holds `masters:edit`, or holds `people:assign_technicians` at that site and
…"), but three earlier lines still stand and contradict it:

- A1 point 4, first line: "a person **without** a login: `people:edit`
  (engineers, IT admin)" — under it an engineer at A writes Technician rows at
  **B** for a no-login person; under the decision ("an engineer at SMTW
  assigns technicians at SMTW only … for any person, with or without a login")
  they can't;
- A1 rule 5: "`PUT /people/<id>/sites` is decorated
  `@require_perm("people:edit")`; inside … a person with a login additionally
  needs `masters:edit`" — the route is gone and the inner rule is now the
  Technician-only rule, not `masters:edit`;
- § 1 out of scope, "managers granting roles at their own site (user: IT admin
  only)", and § 2 / § 7 "only IT admin edits memberships" — now partly untrue.

The "rules added after review" say they override the A1 text; the gate-A
bullets don't say the same about the rules, so precedence is implied, not
stated.

**Why it matters.** Whether an engineer may describe a no-login person at a
site other than their own is a product decision; coded one way or the other it
is a 403 the user didn't ask for, or a write the user didn't allow. Security
impact is nil either way (a no-login person's rows are not access, and rule 1
makes IT admin confirm the set when a login arrives), hence minor.

**Options.**
1. **State it (recommended).** One line under the decision: "Supersedes A1
   point 4's first line and rule 5's route and decorator. Both routes are
   `@require_perm("people:assign_technicians")` (the cheap 'holds it
   somewhere'; IT admin holds it from the token), then the rule above on the
   locked rows. `people:edit` no longer writes site rows anywhere; it keeps the
   person's name, employment, trades, and `active` for persons without a
   login." Visibility for persons **without** a login stays rule 5's (every
   site, to `people:edit` holders): engineers see where a technician works
   even where they can't edit it. Mark § 1's out-of-scope line and § 2's
   "only IT admin" sentences as refined by this decision.
2. Let `people:edit` holders keep writing no-login persons' rows at any site
   (the A1 point 4 reading), and apply the per-site key only to persons with a
   login. Closer to "it only describes them", but two rules for one route, and
   the user's bullet says "for any person".

### BR-A1G-02 — `minor` — The per-site API's contract and the dialog's save are unspecified

**Problem.** The whole-set `PUT` was one request, atomic, with the body rules
of § 5.5. Replacing it with per-site `PUT`/`DELETE` leaves these open:

1. **How the Team dialog saves.** Its "Sites and roles" section now needs one
   request per changed row. The brief doesn't say whether the dialog diffs
   against the loaded rows, in what order it sends, what happens when the
   second of three fails (the first is committed), or how the S007 guard
   treats a half-saved dialog.
2. **Who may edit which row** is a per-site rule the frontend can't compute
   without re-implementing RBAC (§ 7: "the frontend can't know the site
   rules"; node detail carries `permissions` for the same reason). `/auth/me`
   gives `sites` with roles, so the frontend *could* work it out, but that
   is the "frontend computing per-site rights" alternative § 7 rejected.
3. § 5.5's per-row rules need re-reading for a single row: "a site appears at
   most once" is moot; "an inactive site can be kept but not newly granted"
   becomes "a `PUT` on an inactive site is allowed only when the row already
   exists"; `DELETE` of a row that doesn't exist; whether `role` is required
   on `PUT` (the body is `{role, all_units, unit_ids}`; "absent" in the rule
   can only mean the stored side, or `DELETE`); `validate_user_access(body)`
   in `masters_core` (§ 3) becomes a one-row validator.
4. **Order of refusals** when an engineer sends `role: maint_operator` for a
   no-login person: gate bullet 1 says 400 field `role` ("Without a login, a
   person can only be a technician"); the decision says 403 ("Only IT admin
   can set this role"). Both apply; the coder picks one.
5. **Inactive person.** Nothing says whether the routes work on an inactive
   person. S010's `update_technician` edits an inactive record (trades), so
   the existing pattern is "allowed"; the rows are dormant until IT admin
   reactivates, which is IT admin's act on the same dialog (rule 2).

**Recommendation.** State, in this order:
- `PUT /people/<id>/sites/<site_id>`: `role` required, one of `SITE_ROLES`
  (400); the no-login rule (400 field `role`) **before** the engineer limit
  (403 "Only IT admin can set this role"), so IT admin and engineer get the
  same answer for the same mistake; `all_units` xor `unit_ids` (400); units of
  that site, inactive kept-not-granted (400), as `_check_grantable`; an
  inactive site: `PUT` allowed only on an existing row (400 "Unknown site" if
  none / "The site is inactive" if new), as § 5.5 "kept, not newly granted";
  `DELETE` on a missing row → 404; both allowed on an inactive person (rows
  dormant).
- Responses: the person's `sites` **after the same visibility filter as
  `GET /people`** for the actor, so an engineer's `PUT` at A never returns the
  person's rows at B.
- Editability from the backend: each site row in `GET /people` (and the
  responses) carries `editable: true|false` (true when the actor may `PUT` or
  `DELETE` it under the rule), and the list response carries
  `assignable_site_ids` (`null` for `masters:edit` = every site; otherwise the
  sites where the actor holds `people:assign_technicians`) so the dialog knows
  where "Add site" may offer. The role select offers every `SITE_ROLES` entry
  for `masters:edit` holders and only Technician otherwise (and only
  Technician for anyone while the person has no login, gate bullet 1).
- Dialog save: diff against the loaded rows; send `DELETE`s then `PUT`s,
  sequentially; stop at the first error, show it on that row, reload the
  person and keep the dialog open with the remaining changes; the S007 guard
  treats the reloaded state as the new baseline. Rule 1's login save (whole
  set in `PUT /people/<id>`) is unchanged and is the only whole-set path.
- `masters_core.validate_site_row(body)` (pure) replaces
  `validate_user_access`; rule 1's whole-set body is a list of such rows plus
  the "site at most once" check.

### BR-A1G-03 — `minor` — Which units an engineer may give is not stated

**Problem.** An engineer at SMTW with chosen units (`all_units = 0`, say
FWMILL only) may, as written, give a technician **all units** of SMTW or any
unit there. The grant is wider than the engineer's own breadth. It is not an
escalation of *rights* (Technician sits below engineer on the ladder), and the
user's bullet draws the boundary at the site, but the text doesn't say that
units are unrestricted within it, so a coder could narrow it to the engineer's
units and break the case where an engineer assigns a technician to a unit they
don't personally hold.

**Options.**
1. **Any active unit of the site, or all units (recommended).** The site is
   the boundary the user chose; the engineer's own unit rows are about what
   *they* see, not about who they may deploy. One sentence under "What".
2. Only the engineer's own units (or all units only if the engineer has
   `all_units`). Tighter, but a second rule, and it fails the engineer with a
   narrow unit list who is nonetheless responsible for assigning work at the
   site (Plan § 3: engineers "assign work").

### BR-A1G-04 — `minor` — Tests the key breaks, and cases the decision's test list misses

**Problem.** `test_rbac.py::test_role_matrix` (lines 85–92) and
`navigation.test.js` (lines 6–10) assert the **exact** permission set of
engineer, manager and IT admin; adding `people:assign_technicians` fails both
until they're updated. Rule 6 lists them only for the supervisor row. And the
decision's test bullet leaves out:

- the harness: "at B → 403" and "own person → 403" need a real membership
  (`maintenance_team` + `X-Test-User`, through `user_at_sites`, § 5.8); under
  `X-Test-Role: maint_engineer` the wildcard holds the key at every site and
  the test passes for the wrong reason;
- `DELETE`: an engineer at A removes a Technician row at A → 200; a manager
  row at A → 403; a Technician row at B → 403; a missing row → 404;
- the no-login person: engineer at A adds Technician at **B** → 403 (this
  refines gate bullet 1's "technician → 200", which must be at A);
- IT admin through the per-site route: Manager on a no-login person → 400
  (gate bullet 1 via the new route);
- visibility: `GET /people` for an engineer at A, a person with a login
  holding rows at A and B → only A's row, `has_login: true`, no `username`;
  the `PUT` response filtered the same way; `editable` false on a non-
  Technician row; for IT admin every row;
- the `masters:edit` branch first: IT admin (token key at every site) sets
  Operator at A → 200, proving the Technician-only limit doesn't bind IT
  admin;
- rule 1 still wins: an engineer's Technician row at A written after IT admin
  opened the dialog, then IT admin's login change with `sites` without it →
  the row is gone (BR-A1-01's test, now with a real second actor);
- `test_rbac` invariants: `people:assign_technicians ∈ SITE_SCOPED`; held by
  engineer, manager (inherited) and IT admin only; not by technician,
  operator, supervisor, storekeeper; BR3-04's "no site role holds
  `masters:edit`" still true;
- one INFO line per change (actor, person, site, before, after); none when a
  `PUT` repeats the stored row.

**Recommendation.** Add these to A1's test list and name `test_role_matrix`
and `navigation.test.js` under the decision's "where".

---

## Nit

### BR-A1G-05 — `nit` — Docs, config lists and the standards line

- **`SITE_SCOPED`** in § 3 lists three keys; add `people:assign_technicians`.
  `config_rbac.py` comment: "a grant key: engineers (and so managers) and IT
  admin may give the Technician role at a site; everything above is
  `masters:edit`".
- **Plan § 3**: first paragraph "granted only by IT admin" → "granted by IT
  admin; engineers add Technician rows at their own sites (S011 A1)"; a matrix
  row `people:assign_technicians` (engineer ✓, manager ✓, it_admin ✓); the
  sentence after the matrix on `masters:edit` covering "users' unit access".
  `.claude/CLAUDE.md`'s deviation note and `docs/Keycloak.md` § 7 ("ask IT")
  → "ask your engineer or IT"; the `NoAccessView` text likewise, if the user
  wants engineers to be the first port of call.
- **Standards, in plain terms**, for A1's Standards paragraph:
  - **ISO 27001:2022 A.5.18 (access rights)** allows access to be granted by
    the owner of the resource, not only by IT, as long as it is approved,
    recorded and reviewable. Here the site's engineer is that owner for the
    lowest maintenance role; the same INFO log and the same Team screen are
    the record and the review.
  - **A.8.2 (privileged access rights)**: privileged rights stay with IT
    admin; the delegated grant is the least-privileged maintenance role, and
    the engineer can neither raise it nor touch rows above it.
  - **A.5.3 (segregation of duties)** still holds in code: never one's own
    person, never above Technician, logins only by IT admin.
  - **ISO 55001:2024 § 5.3**: responsibilities assigned per plant — the
    plant's engineer decides who works on its assets; **EN 15628** places
    deploying and supervising technicians at the engineer level, which is what
    this key models.

---

## Checked and found consistent

- **The three bounds hold together.** Site (`has_perm_at` at the row's site),
  role (stored and new both Technician, or absent), person (rule 4 on the
  locked row). An engineer can't widen any of them by sequence: logins are
  IT admin's (S010 A1 rule 3), `active` of a login holder is IT admin's (rule
  2), and the whole-set login save (rule 1) replaces whatever an engineer
  wrote before it.
- **`it_admin` in the tuple** is right: it makes the cheap decorator pass for
  IT admin from the token, lists the key in IT admin's global union for the
  UI, and `has_perm_at` is true at every site, as for `equipment:edit`. The
  `masters:edit` branch keeps IT admin out of the Technician-only limit.
- **Manager inherits** through `ROLE_INCLUDES["maint_manager"] =
  ("maint_engineer",)`; the supervisor (`("maint_operator",)`) and the
  technician don't. A technician can't assign technicians.
- **No new path for a DB row to impersonate a token role**: `role` stays
  validated against `SITE_ROLES`; BR3-02's "ignored entirely" rule is
  untouched.
- **Lock order** person → membership row → units (→ site by FK) on both new
  routes; rule 1 and S010 lock the person first too; `update_unit`'s
  unit → site is the same tail. No cycle.
- **Rollback (§ 5.7, rule 3)** unaffected: no schema change; the previous
  release never reads `memberships`.
- **Logging** at INFO with actor, person, site, before, after matches § 5.5
  and A.8.15; the engineer's grant is traceable like IT admin's.
- **Scope.** One key, two per-site routes replacing one whole-set route, one
  dialog rule. Still one reviewable slice with A1.
