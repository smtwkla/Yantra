```
Step: S001 — Basic masters
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 13-10-2026
```

# S001 — Brief review, round 1

Reviewed `1-brief.md` against `docs/Plan.MD` (§ 1, 3, 4.1, 5, 9), `docs/Plant-Facts.md` § 2,
`docs/Maintenance-Philosophy.md`, `.claude/SMTW-WebApp-Base.md` (RBAC, DB connection, migrations,
API responses, testing, frontend design) and the current code (`app.py`, `local_db.py`,
`config_rbac.py`, `masters.py`, `auth_utils.py`, `db_helpers.py`, the tests, `MastersView.vue`,
`api.js`, `stores/`).

**Verdict: not yet approvable.** Two `major` findings (BR1-01, BR1-02) need an answer; the rest are
minor or nits. The brief is otherwise well shaped: the slice is the right size, the table design
matches Plan.MD § 5, the pure-core split is correct, the RBAC change follows the 13-10-2026 decision,
and the departures from the base pattern (no pagination, 409) are stated rather than hidden.

Severity: `blocker` / `major` / `minor` / `nit`. Findings are ordered by severity.

---

## Major

### BR1-01 — Immutable site and unit codes go beyond what Plan.MD decided — `major`

§ 5 makes all three codes immutable, justified as "permanent identity, as equipment codes will be".
Plan.MD § 4.1 reserves *permanent identity* for nodes of the **equipment tree** (the code on the QR
label). Sites and units are places; their codes appear only in the **derived** full path, which the
Plan already says changes when things move. Nothing references a site or unit by code — `units` and
`user_units` reference by id.

The rule has a real cost:

- Plant-Facts § 10 shows a site code already renamed once (`SMTW-KT` → `BRICKS`) before any software
  existed. Under this rule, a typo in a site code at first entry means deactivating the site and all
  its units, recreating them, and re-granting every user's unit access.
- Deactivated typo rows stay in the DB and in `include_inactive` lists for ever.

**Standards.** ISO 14224 wants stable identifiers so history can be compared; ISO 55001 wants changes
to the register *controlled* (who, when, why). Neither forbids correcting a code — control is not
prohibition. Immutability is the strictest possible reading, and it is the right one for the
equipment code (printed on labels, embedded in history). For places it is stricter than needed.

The class code is a different case: once S002 creates `VBM001`, the prefix is baked into equipment
codes, so from then on the class code must not change.

Options:

- **(a)** Keep as proposed, and say in § 7 that this is stricter than Plan.MD and why.
- **(b) Recommended — "frozen once referenced".** One rule for all three masters: the code may be
  changed (by the edit-permission holder, audit columns updated) while **nothing references the
  record**; once referenced it is frozen and PUT with a changed code → 409 "code is in use". In S001,
  "referenced" means: site → has units; unit → has `user_units` rows; class → nothing yet. S002 adds
  "has equipment" to unit and class. This covers the data-load phase (where typos happen), needs one
  COUNT per PUT, and gives the equipment code the full immutability the Plan requires because an
  equipment code is referenced the moment it exists.
- **(c)** Always editable with audit — too loose for class codes after S002.

If (b) is taken: § 5 "Codes are immutable", the PUT rule, § 7 row 4, and the test "A code change on
PUT → 400" change accordingly. Pointer for S003: whichever option, ticket and job history should
snapshot the full path at event time, so a later rename or move does not rewrite old records.

### BR1-02 — Unit-access changes leave no trail, contradicting § 2 — `major`

§ 2 says, under ISO 55001: "every change records who made it and when; records are deactivated
instead of deleted, so history never points at a missing record". § 5 then replaces a user's whole
unit set by delete-and-insert. A revoked grant vanishes with its `granted_by` / `granted_at`; after a
re-save nothing shows who had what before. The brief's own standard is not met for exactly the
record an auditor asks about first.

Also worth stating plainly: the audit columns on the masters hold the **last** change only (a
renamed site loses its old name). That is fine for v1 masters, but say so, rather than implying a
full history.

**Standards.** ISO 27001:2022 A.5.18 (access rights) expects access to be provisioned, reviewed and
revoked in a traceable way. A.5.3 (segregation of duties) is the control behind "only IT admin
grants it".

Options:

- **(a) Recommended.** Keep delete-and-insert (it is the simplest correct replace), and write one
  structured log line per PUT: actor, username, units before, units after. Logs are shipped
  centrally, so the trail exists with zero schema. State in § 2 that master audit columns record the
  last change, and the access-grant trail lives in the application log.
- **(b)** A `user_unit_changes` table — more than v1 needs.

---

## Minor

### BR1-03 — Existing tests that the change breaks are not listed — `minor`

§ 3 "Tests" lists `test_rbac.py` and `navigation.test.js`, but two more files break and must be in
the brief so the coder does not decide their fate alone:

- `backend/tests/test_auth.py` — `test_valid_bearer_token_reaches_route` asserts an engineer holds
  `masters:edit`; after the change the engineer holds `equipment:edit`.
- `backend/tests/test_modules.py` — `TestMasters` calls `GET /api/masters/` and expects
  `{"items": []}`; the brief removes that placeholder route. Its two tests (every role can read,
  unknown role → 403) should move to `test_masters_api.py` against `GET /sites`.

### BR1-04 — Access rows on a unit that is later deactivated — `minor`

§ 5 says only active units can be granted, and a site cannot be deactivated with active units, but
nothing says what happens to `user_units` rows when a **unit** is deactivated. The trap: IT admin
opens a user who holds a now-inactive unit, adds another unit, saves → 400 "inactive unit", with no
hint why.

Specify, for example: rows are kept (reactivating the unit restores access); `GET /user-units`
returns `active` per unit; the panel shows held-inactive units greyed out and drops them on save,
saying so. Or: deactivating a unit deletes its access rows (with the BR1-02 log line). Either is
fine; the brief must pick one.

### BR1-05 — Duplicate code → 409 must come from the UNIQUE index, not a pre-check — `minor`

§ 6 promises 409 for a duplicate code but not how. A SELECT-then-INSERT pre-check has a race; the
UNIQUE index then raises `pymysql.err.IntegrityError` (1062) and the API returns 500. Say: catch
`IntegrityError` on INSERT/UPDATE and map it to 409 (a pre-check for a friendlier message is
optional). Same for `UNIQUE(site_id, code)` and `PK(username, unit_id)`.

### BR1-06 — Where `get_db()` lives, and how it finds the config — `minor`

`local_db.py` is deliberately framework-free (only `pymysql`) and takes `config` as an argument
everywhere. Moving `get_db()` there means importing Flask's `g` into the pool/migration module, and
`get_db()` needs `DB_CONFIG` for `ensure_schema()`, which the brief does not say how it gets.

Options: (a) recommended — put `get_db()` and the teardown in `db_helpers.py` ("shared database
utilities", already imported by modules); it imports `get_pooled_db`/`ensure_schema` from
`local_db` and `DB_CONFIG` from `config`, and `local_db` stays Flask-free; (b) keep the move to
`local_db.py` and have `init_pool(config)` remember the config for `get_db()`. State which, and
that `app.py` registers the teardown either way.

### BR1-07 — A GET gated by an edit key — `minor`

`GET /user-units` is gated by `masters:edit`. The RBAC pattern (CLAUDE-COMMON) keeps reads and
writes apart with the read hierarchy (`read_basic` / `read` / `read_senior`). Reusing an edit key
for a read is a departure and should be listed in § 7 — or avoided by adding
`masters:read_senior = ("it_admin",)` now (one line). Looking ahead: in phase 3 engineers assign
work (Plan § 4.2) and will want to see which technicians hold a unit; a read key will be needed then
anyway, and `read_senior` is where the manager/engineer would be added. Recommend the key.

### BR1-08 — Standards citations: two corrections and one term to teach — `minor`

- **ISO 27001:2022.** A.5.15 (access control) is right. **A.8.2 is "privileged access rights"**
  (admin accounts), not the control for granting a user access to a resource — that is **A.5.18
  "access rights"** (provision, review, remove). "Granting is separate from doing the work" is
  **A.5.3 segregation of duties**. Cite A.5.15 + A.5.18 + A.5.3.
- **ISO 55001.** In the 2014 edition § 7.5 is *Information requirements* and § 7.6 is *Documented
  information* (7.6.3: control of documented information). The brief's point — a controlled register
  with traceable changes — rests on both; cite "§ 7.5–7.6" (check the clause numbers against the
  edition in use).
- **Term.** What the brief calls sites and units is what CMMS practice (ISO 14224's installation /
  plant-unit levels; SAP PM; most CMMS products) calls **functional locations**: fixed places where
  equipment is installed, as opposed to the equipment itself, which moves. One sentence in § 2
  saying "sites and units are Yantra's functional locations" gives the project owner the standard
  name without changing the UI words.
- The ISO 14224 citations (levels 3–5, Annex A class codes such as `PU`, `EM`, `CO`) are correct.

### BR1-09 — `oneerp_warehouse` uniqueness — `minor`

Plan § 1: "OneERP warehouses become equipment units" — one warehouse, one unit. Either add
`UNIQUE(oneerp_warehouse)` (MariaDB allows many NULLs under a UNIQUE index) with 409 on a
duplicate, or say many-to-one is allowed. Also strip the value; do not upper-case it (OneERP names
are case-sensitive).

### BR1-10 — API details the coder would otherwise decide — `minor`

- `{error, field?}`: `api.js` copies only `error` and `code` onto the thrown error; add `field` so
  the panels can show the message inline (base: "validation errors inline next to the field").
- Response bodies: POST → 201 with the created record; PUT → 200 with the updated record (the
  base's flat single object). `PUT /user-units/<username>` → 200 with the user's new item, or 204.
- `masters_core` returns `(clean_data, errors)`: define `errors` as a list of `{field, message}`;
  the API returns the first one as `{error, field}` (one problem at a time, shown inline).
- `GET /units` without `site_id` returns all units (the Unit access panel needs that).

### BR1-11 — Username rules — `minor`

- Validate the normalised username (e.g. `^[a-z0-9][a-z0-9._@-]{0,99}$`); reject empty. A typed
  username that matches no Keycloak user is accepted knowingly (the brief says why); a format check
  at least stops garbage rows.
- State for S002: the unit filter compares `g.user["username"].lower()` to `user_units.username`,
  so the stored lower-case form and the token's form cannot drift (Keycloak lower-cases usernames,
  but make the rule explicit on both sides).

### BR1-12 — The level-2 toolbar is new shared UI — `minor`

No module toolbar component exists yet (`components/layout/` has sidebar, topbar, bottom nav,
toast); `MastersView` would be the first to build one, and every later module has one (Plan § 6).
Decide in § 3: a reusable `components/layout/ModuleToolbar.vue`, data-driven like `navItems`
(`{key, icon, label, perm}`), permission-filtered, hidden when one section remains (base rule) — or
inline in `MastersView` and extract later. Recommend reusable now; it is small and avoids a
refactor in S002.

---

## Nits

### BR1-13 — Warn before a code is frozen — `nit`

Whichever BR1-01 option is taken, the create modal should say under the code field that the code
cannot be changed later (or, under option (b), cannot be changed once used).

### BR1-14 — Test-DB hygiene — `nit`

- The session truncate must run after `ensure_schema()` (importing `app` triggers it) and in FK
  order (`user_units`, `units`, `sites`, `equipment_classes`) or with `SET FOREIGN_KEY_CHECKS=0`.
- With one truncate per session, tests that create `SMTW` twice collide. Tell the coder to use
  per-test unique codes (a counter fixture), per the base's "fix the test, not the fixture".

### BR1-15 — Small unspecified points — `nit`

- `id` columns: `INT AUTO_INCREMENT PRIMARY KEY`.
- `created_at`/`updated_at`: set by the shell with `NOW()` in the same statement as the actor;
  `updated_*` NULL until the first edit. (Or `DEFAULT CURRENT_TIMESTAMP` like `app_settings` — pick
  one convention for all Yantra tables now.)
- List order: by `code`.
- Unit code minimum length is 1, site code minimum is 2 — make both 2 unless a one-letter unit is
  wanted.

### BR1-16 — Step status — `nit`

The brief still says `Draft`; README gate 1 moves it to `In review` when review starts. Set it and
the index row in `docs/steps/README.md` when answering this round.

---

## Checked and found consistent

- Table design matches Plan.MD § 5 (units store the part after the dot; full code derived).
- Site regex admits every code in Plant-Facts § 2 (`SMTW-KP`, `AGRI-VKM`); the class regex matches
  the 13-10-2026 decision (2–4 letters); 3-digit numbering and the per-prefix counter correctly
  deferred to S002.
- RBAC: `masters:edit` → IT admin only and `equipment:edit` for engineer/manager/IT admin match
  Plan § 3; the manager inherits via the ladder; `masters:read` stays `*`; admin is not in tuples.
- Site/unit activation rules are coherent (no active unit under an inactive site).
- Manager's "all units" as a role rule (no rows) is right and avoids a maintenance chore.
- No seed data in the migration — correct; production data belongs in the DB.
- No pagination, 409, `{items, total}` — stated departures, proportionate to list sizes.
- Pure core / thin shell split and the test layers follow the base pattern.
