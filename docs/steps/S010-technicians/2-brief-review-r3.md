```
Step: S010 — Technicians and trades
Doc: brief-review r3
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S010 — Brief review, round 3 (amendment A1 only)

**Verdict: two `major` findings open (BR-A1-01, BR-A1-02), both on the same
question the orchestrator asked — can an engineer, or IT admin, gain or grant
access through the people record once S011 A1 hangs access off it. Five
`minor`, two `nit`.** This is the single round the user asked for per
amendment; README § Gates still wants no `major` open before the user sets
A1 to `Approved`, so the planner's answers to the two majors should be read by
the user at gate A.

Reviewed § 10 "A1 — Team: a register of people" of the S010 brief, against the
rest of the S010 brief (which A1 supersedes in parts), S011's brief and its
amendment A1 (interface only), `docs/Plan.MD` § 1–§ 3 / § 4.2 / § 5,
`docs/Maintenance-Philosophy.md` § 2 and § 11, `docs/Plant-Facts.md` § 4,
`docs/Keycloak.md` § 5, `.claude/CLAUDE-COMMON.md` (migrations, dev DBs, RBAC
pattern), `.claude/SMTW-WebApp-Base.md` § RBAC and § Local DB Migration
Pattern, `4-code-review-r1.md`, `3-impl-report.md`, and the working tree as it
stands after the S010 code review: `backend/local_db.py` (v7, uncommitted;
`git show HEAD:backend/local_db.py` ends at v6), `masters.py`,
`masters_core.py`, `config_rbac.py`, `api_common.py`, `auth_utils.py`,
`db_helpers.py`, `tests/conftest.py`, `tests/test_technicians_api.py`,
`tests/test_masters_core.py`, `tests/test_rbac.py`;
`frontend/src/views/masters/TechniciansPanel.vue`, `TradesPanel.vue`,
`MastersView.vue`, `useMasterForm.js`, `stores/auth.js`, `stores/masters.js`,
`tests/navigation.test.js`; `tooling/dev/dev-db-reset.bat`,
`docker-compose.dev.yml`. Only `git diff -w --ignore-cr-at-eol` was used, so
IDE re-padding is not reported.

---

## Findings

### BR-A1-01 — major — `active` stays under `people:edit`, so engineers revoke and, worse, re-grant access

**Where.** A1 point 2 ("active: as S010. Deactivating a person will also end
their access (S011 A1)") and point 4 (`people:edit` "covers people's name,
employment, trades, active").

**Problem.** A1 moves the login to IT admin (`masters:edit`) because "from
S011 a login turns the person's site roles into Yantra access", and S011 A1
point 4 reserves the site-role rows of a person **with** a login to IT admin
for the same reason. But A1 leaves `active` with `people:edit` (engineers,
managers, IT admin). After S011 A1 point 3 ("the token's username → the
*active* person with that login"), `active` on a person with a login *is*
access:

- an engineer sends `PUT /people/<id> {active: 0}` on the manager's record:
  the manager has no access on their next request. A revocation by someone
  who, by the user's decision (S011 § 9.6, A.5.3), may not touch access;
- IT admin deactivates a leaver (A.5.18, the case A1's standards paragraph
  describes). Any engineer sends `{active: 1}`: the leaver's login and every
  site role come back. That is a **grant** of access by an engineer, exactly
  what the login rule was added to prevent. The "Reactivate" button in the
  shared `ActiveToggle` makes it one click.

**Why it matters.** ISO 27001 A.5.18 asks that access rights be removed and
re-provisioned in a controlled way; A.5.3 (segregation of duties) and A.8.2
(privileged access) are the reasons S011 keeps granting with IT admin. A1
closes the front door (the login) and leaves the side door (`active`) open.
Nothing in S010 alone is exploitable (the login grants nothing before S011),
but the record shape is being fixed now so that S011 can "hang off it", and
S011 A1 is reviewed in parallel on the assumption that the person record is
safe to hang access on.

**Options.**
1. **On a person who has a login, `active` is IT admin's too.** In
   `PUT /people/<id>`, after `_lock_row` (so the check is on the locked row,
   the same shape S011 A1 point 4 prescribes for site roles), if the row's
   `username` is not `NULL` and the body carries `active` and the actor lacks
   `masters:edit` → 403 field `active`, "Only IT admin can deactivate or
   reactivate a person who has a login". A person without a login is
   unchanged (engineers deactivate helpers and contractor firms freely). The
   frontend hides the Deactivate / Reactivate button when the record has a
   login and the user lacks `masters:edit`. Tests: engineer `PUT {active: 0}`
   and `{active: 1}` on a person with a login → 403; on a person without one →
   200; IT admin → 200. *Recommended*: one rule, stated once ("on a person
   with a login, `username` and `active` are IT admin's"), checked where the
   row is already locked.
2. Allow deactivation by `people:edit` (a revocation fails safe) and reserve
   only *reactivation* of a person with a login to `masters:edit`. Fewer
   refusals, but two rules instead of one, and an engineer can still lock the
   manager out; S011's own-access rule (§ 5.5) was written to prevent even
   self-edits, so an asymmetric rule sits oddly beside it.
3. Accept, and rely on the log. The user rejected "the log as the only
   control" for S011 (§ 7, last row).

### BR-A1-02 — major — Nothing stops a login being set to the actor's own username, which walks around S011's own-access rule

**Where.** A1 point 2 (login) and point 4; S011 A1 point 4 ("nobody edits
**their own** person's login or site roles").

**Problem.** S011 defines "own person" by the login the record *already*
holds. A loginless person is nobody's. So, with the two amendments as written,
IT admin alone can do this:

1. `POST /people` `{name: "X", employment: "direct"}` — allowed
   (`people:edit`, which IT admin holds).
2. `PUT /people/<X>/sites` `{sites: [{SMTW, maint_manager, all_units}]}` —
   allowed: X has no login, so S011 A1 point 4 lets `people:edit` set the
   roles. (S011 A1's open point even asks whether a loginless person may hold
   manager; today's answer is yes.)
3. `PUT /people/<X>` `{username: "<IT admin's own username>"}` — allowed:
   `masters:edit`, and X is not yet "their own person".

Result: IT admin is manager at SMTW with every phase-3 right the Plan keeps
away from IT (§ 3: "**Not** maintenance work and not all-powerful"), in three
ordinary requests, each of which passes the rules of its amendment. The S011
brief rejected exactly this (BR2-03, user decision § 9.6, "nobody changes
their own access"). The step the rule has to live in is the **login write**,
which A1 owns.

**Why it matters.** A.5.3 / A.8.2: the one who grants must not be able to
grant to themselves. The user chose prevention over the log (S011 § 7).

**Options.**
1. **Refuse a login equal to the actor's.** In `POST /people` and
   `PUT /people/<id>`, when `clean["username"]` is not `None` and equals
   `normalise_username(actor())` → 403 field `username`, "You can't set your
   own login; another IT admin or admin does that" — the same shape and
   wording family as S011 § 5.5's own-access 403 (which normalises the actor,
   BR3-03). A pure helper is unnecessary; it is one comparison in the route.
   Tests: IT admin `POST` and `PUT` with their own username (case-varied) →
   403; with someone else's → 201 / 200. Add to A1's rules and tests.
   *Recommended.* Admin (`mspv-apps-admin`) bypasses, as everywhere; admin is
   you.
2. Also refuse `people:edit` from setting roles on a loginless person who
   has **no** login *and* was created by the actor. Over-engineered and still
   leaky (two IT admins).
3. Accept and log. Rejected for S011 already.

Note for the S011 A1 reviewer (interface): with option 1 here, S011 A1's
"nobody edits their own person's login" is complete: the person-with-login
case is S011's check, the loginless case is this one.

### BR-A1-03 — minor — The login-permission rule leaves the coder three decisions, and the current dialog would make every engineer save fail

**Where.** A1 point 4 ("a `PUT` or `POST` carrying `username` without it →
403 field `username`"), point 7 (dialog), tests.

**Problem.**
1. **The dialog always sends `username`.** `TechniciansPanel.vue`'s `toBody`
   is `({ ...f, username: f.username.trim() === "" ? null : f.username })`:
   the key is always present. Under A1's rule, every save by an engineer —
   renaming, ticking a trade — would answer 403 on `username`. A1's test "an
   engineer's update without `username` on a person who has a login keeps it"
   assumes the body omits the key, but nothing in A1 tells the frontend to.
   State it: when the user lacks `masters:edit`, `toBody` **omits**
   `username` (and the form's dirty check still includes it, harmlessly, since
   the field is read-only).
2. **"Carrying" must include clearing.** `username: null` / `""` from an
   engineer clears the login, which after S011 ends access (a revocation).
   A1 says "set and changed only by IT admin"; say "set, changed or cleared",
   and add the test: engineer `PUT {username: null}` → 403.
3. **Where the check sits and what it says.** Say: in the route, after
   `clean_body` (so `"username" in clean` is the test, after normalisation)
   and before the transaction; `ApiError("Only IT admin can set the login",
   403, "username")`, so the dialog shows it beside the field through
   `fieldError`. It is a static check on the body and `g.user`, so no lock is
   needed, unlike BR-A1-01's.
4. **`trade_ids` on create.** "Trades may be empty on create" — absent or
   `[]`? Say: `trade_ids` is optional on create; absent means no trades; `[]`
   is accepted on create and update (`_parse_trade_ids` loses its "at least
   one" rule and `_TECHNICIAN_FIELDS["trade_ids"]` becomes `(…, False)`); the
   pure tests for "`[]` → error" are inverted, and the fixture's default stays
   one trade.

**Why it matters.** Points 1–2 are a broken screen and a gap in the rule;
3–4 are decisions the coder would otherwise take alone (CLAUDE-COMMON "Nothing
beyond the agreed scope").

**Option.** State the four in A1 (points 4, 6, 7 and tests). One option only.

### BR-A1-04 — minor — "Where" is thin: the rename touches more than `PeoplePanel.vue`, and one miss would silently lock the Trades panel

**Where.** A1 points 3–7; S010 § 1 and § 2 (superseded text not named).

**Problem.** A1 names the tables, the key, the API path and the panel, and
"S010 § 8 re-pointed". The working tree shows what else carries the old name
or key; the coder can infer most of it, but two are easy to miss and one is a
real bug:

- `frontend/src/views/masters/TradesPanel.vue:14`: `canEdit` checks
  `technicians:edit`. After the key is renamed in `config_rbac.py`, no role
  holds that string, so **Trades becomes read-only for everyone**, with no
  test to catch it (`navigation.test.js` checks nav items, not panels). Name
  the file.
- Backend: `masters_core.py` (`TECHNICIAN_KINDS` → an `EMPLOYMENT` tuple
  `("direct", "contractor")`, `_parse_kind` → `_parse_employment` with the
  message "Employment must be direct or contractor", `_TECHNICIAN_FIELDS`,
  `validate_technician` → `validate_person`); `masters.py` (routes, helpers,
  the SQL on `people` / `person_trades` with `person_id`, the module and
  section docstrings, `UNIQUE_KEY_ERRORS` key `uq_people_username` with A1's
  message); `config_rbac.py` comment and key; `local_db.py` v7 comment and
  description.
- Tests: `tests/test_technicians_api.py` → `test_people_api.py`;
  `conftest.py` `_TABLES` (`person_trades`, `people`, `trades`) and
  `make_technician` → `make_person(trades=None, **overrides)` (S011 A1's
  `user_with_units` will build on it); `test_masters_core.py`
  (`TestTechnician` → `TestPerson`, the `kind` cases); `test_rbac.py`
  `test_role_matrix` and `navigation.test.js` (`people:edit`).
- Frontend: `MastersView.vue` section key `people`, label "Team", icon,
  import; the panel's `canEdit` (`people:edit`) and a new `canEditLogin`
  (`masters:edit`).
- Docs: `docs/Plan.MD` § 3 matrix row (`people:edit`), § 5 rows (`people`,
  `person_trades`, and `breakdown_labour`'s "Technician" → person);
  `docs/Keycloak.md` § 5 ("Technicians › login" → "Team › login"; "the
  Technicians dialog shows your own login" → Team, and now only IT admin);
  `docs/steps/README.md` index row title (the folder slug `S010-technicians`
  stays: README § Folder and files fixes it). The S011 brief body still says
  `technicians:edit` (§ 5.2, § 5.4, § 9.5): that is S011 A1's to note.
- **S010 text A1 supersedes but doesn't name:** § 1 out-of-scope "naming
  individual contract workers (user, 16-10-2026)" — now allowed, by the user's
  choice per entry; § 2's "Departure, deliberate" under ISO 55001 § 7.2
  (contract labour by firm only) — now partial; § 5.2 "Kind" and the dialog's
  "Contractor firm" label switch and the form-text "Contract labour is
  recorded by the contractor's firm, not by person" (`TechniciansPanel.vue:157,
  160`) — now wrong. A1 opens with "supersedes the parts of § 1, § 3–§ 8 named
  below"; name these too, or the brief contradicts itself.

**Option.** Add a "Where" list to A1 with the files above and the superseded
paragraphs. One option only.

### BR-A1-05 — minor — Editing migration v7 in place is acceptable; the brief must say the exact steps, or the tests fail on a stale `db_version`

**Where.** A1 point 3.

**The question the orchestrator asked.** CLAUDE-COMMON has two rules: "never
edit an applied migration; always add a new version" and "dev/test DBs are
disposable: on any schema drift, drop the schema and let migrations rebuild
it". They don't conflict here. "Applied" in the first rule is about databases
that must survive the change: v7 exists in no commit (`HEAD:backend/local_db.py`
ends at v6; the latest tag `v0.1.3` is on or before HEAD) and so on no
deployed database. The only databases holding v7 are the user's dev container
(`vel_yantra_master`, `vel_yantra_test`), which the second rule makes
disposable. The alternative, keeping v7 as is and adding a v8 that renames
`technicians` → `people`, would ship a create-then-rename for a table no
production database ever had, and would take S011's v8 number. **In place is
right.** It is the same call the brief already made when S009's v7 was
reverted (gate A note).

**What A1 leaves out, and what the coder must do**, in this order:
1. Edit v7 in `_MIGRATIONS`: description "Trades, people", comment, the three
   `CREATE TABLE IF NOT EXISTS` statements (`people` with `employment
   ENUM('direct','contractor')`, `uq_people_username`; `person_trades` with
   `person_id`, `fk_person_trades_person`, `fk_person_trades_trade`). v8 is
   not touched; it stays S011's.
2. **Reset the dev container before running anything:**
   `tooling/dev/dev-db-reset.bat` (`compose down -v` then `up -d`: both
   databases are rebuilt from `init-test-db.sql`, and `ensure_schema()`
   re-applies v1–v7 on first use). The reason to say it explicitly: both
   databases carry a `db_version` row `7`, so without the reset `init_db`
   skips the edited v7, the `people` table never appears, and every people
   test fails with "table doesn't exist" — a stale-schema symptom the coder
   must not debug (CLAUDE-COMMON). `conftest._clean_tables` only `DELETE`s
   rows; it never rebuilds a schema.
3. Then `tooling/run-tests.bat`.
4. The impl report's `Amendment A1` section records that v7 was edited in
   place and why (uncommitted, undeployed), so the next reader doesn't take it
   for a broken append-only rule.

**Option.** Write steps 1–4 into A1 point 3. One option only.

### BR-A1-06 — minor — The manual checks are not re-pointed, and the first one can no longer be done as written

**Where.** A1 "Tests" (re-points § 8's automated tests only); S010 § 8
"Manual checks (user)"; `3-impl-report.md` § Manual checks.

**Problem.** The impl report's first important box reads "As engineer: …
add an in-house technician with two trades and a login". Under A1 an engineer
can't set a login, so the box can't be ticked. The checks that matter for A1
are the ones only a person sees: the read-only login field for an engineer,
and the IT admin flow. README § Manual checks asks the brief to mark the
important ones.

**Option.** Replace the manual checks in A1 (the coder copies them into the
report's `## Manual checks` as boxes):
- **important** — as engineer: add a person (direct, two trades, no login);
  the Login field is read-only with no help line; rename them and change
  their trades: saves (no 403);
- **important** — as IT admin: set that person's login; as engineer: the login
  shows in the column and dialog, read-only; Deactivate / Reactivate on that
  person is not offered to the engineer (BR-A1-01 option 1);
- **important** — as engineer: add a contractor named as a firm, and one named
  as a person; deactivate a loginless person: works;
- plain — as operator: Team and Trades listed, no Login column, no buttons;
  the S007 guard on the Team dialog; the employment badges.

### BR-A1-07 — minor — Engineers still receive every login, though they no longer maintain it

**Where.** A1 point 5 ("The login masking of § 5.3 stays (shown to
`people:edit` holders)"), point 7.

**Problem.** S010 § 2 and § 7 justify sending `username` to editors with
"shown only to those who maintain the link" (A.5.15; a full login list is
the first half of a credential attack). A1 moves maintaining the link to IT
admin but keeps sending the list to engineers and managers, so the stated
reason no longer matches the rule. After S011 the list is, exactly, the set of
accounts that have access.

**Options.**
1. **Engineers get `has_login: true/false`; the username goes to
   `masters:read_senior` holders (IT admin) only.** `_people_out` sets
   `has_login` for `people:edit` holders and deletes `username` unless
   `has_perm("masters:read_senior")`. The Login column shows a tick for
   engineers and the username for IT admin. The dialog's read-only field
   becomes "Has a Yantra login: yes" for engineers. Tests: the parametrised
   masking test gains the `has_login` key. *Recommended*: the cheap,
   minimised shape, and the read hierarchy's natural fit (`read_senior` for
   the sensitive field, as S001's `user_units`).
2. Keep A1 as written and state the reason afresh: "engineers see the login
   so they can tell who can log in and who must be given a login". Acceptable
   if the user prefers; then § 2's A.5.15 sentence is reworded.

### BR-A1-08 — nit — Standards: name the two controls the split relies on, and restate A.5.34 for named contract persons

**Where.** A1 "Standards".

- The login split (engineers describe, IT admin grants) is **ISO 27001 A.5.3
  (segregation of duties)** and **A.8.2 (privileged access rights)**; S011 A1
  names them, A1 only says "because from S011 a login turns … into access".
  Name them here too, since the rule lives here.
- **A.5.16 (identity management)** — "the full life cycle of identities shall
  be managed": one identity per person, created, changed and retired in one
  place. The person record with `uq_people_username` (one login, one person)
  is where that now happens; a sentence makes the register's purpose plain
  to the owner.
- **A.5.34** was argued in S010 § 2 with "contract labour is recorded by firm,
  not by person". A1 lets a contractor be named as a person, so Yantra may now
  hold a contract worker's name. Minimisation still holds (name, employment,
  trades, maybe a login; nothing else), but say so, and mark S010 § 2's
  departure paragraph as superseded (BR-A1-04).
- The ISO 55001 § 7.2 and A.5.18 citations are correct: § 7.2 covers "persons
  doing work under its control that affects asset management performance",
  not only technicians, and A.5.18 is the joiner / mover / leaver control.

### BR-A1-09 — nit — Small points

- **"Team" vs `maintenance_team`.** Keycloak's login role is
  `maintenance_team` (Keycloak.md § 3.2), and the Team register also holds
  operators and supervisors who are not the maintenance team. "People" would
  avoid the clash; the user's call.
- **The help line** ("Their Maintenance Team Login ID. Your own login, for
  ex: …") is about typing a login; show it only when the field is editable
  (`masters:edit`).
- **Name label.** With "the user's choice per entry; no rule", the name label
  is "Name" for both employments, with a short help line "A person, or a
  contractor firm". The current label switch and form-text go (BR-A1-04).
- **Employment badge**: "Direct" / "Contractor" as A1's labels; the S010
  colours can stay.
- **Open point "Contractor with a login: allowed"** — fine; S010 § 5.2 already
  said so.
- **A firm and a person are indistinguishable** in the record (no "is a firm"
  flag). Phase 3's labour row will show "ABC Engg" beside "Ravi" without
  knowing one is a firm. The user decided "no rule"; note it as a known limit
  in § 7, next to the duplicate-name row, so phase 3 doesn't rediscover it.

---

## Interface with S011 A1 (checked; findings there are S011's)

- **Names agree:** `people` / `person_trades` (A1) and `memberships.person_id
  → people`, `person_units` (S011 A1); `employment direct` for the legacy
  rows S011's v8 creates; `people.username VARCHAR(100)` fits the usernames
  v8 moves from `user_units`.
- **Keys agree:** `people:edit` for name, employment, trades, active and the
  trades list; `masters:edit` for the login (A1) and for the site roles of a
  person with a login (S011 A1); `masters:read_senior` sees `sites` (S011 A1)
  — and, with BR-A1-07 option 1, the username.
- **The dialog:** one Team dialog; S011 A1 adds its "Sites and roles" section
  and the "Adding this login gives access as: …" line under A1's login field.
  A1's `PUT /people/<id>` locks the person row first, which is the lock S011
  A1 point 4 needs for its "has a login" check.
- **Gaps to raise on S011's side:** its body still says `technicians:edit`
  and "technicians" (§ 5.2, § 5.4, § 9.5); the supervisor decision replaces
  Plan § 2 (line "no production-supervisor role"), § 3 and
  Maintenance-Philosophy § 11 lines that S011 A1 doesn't list as doc edits;
  and S011 A1's own-person rule needs BR-A1-02's "not your own username" rule
  here to be complete.

## Checked and found consistent

- A1's record shape against the user's decisions of 16-10-2026: one register,
  with or without a login, any role, direct or contractor, a contractor named
  as a firm or a person; supervisor is S011 A1's.
- `employment ENUM('direct','contractor')` replacing `kind`; `trades`
  unchanged; `uq_people_username` keeping the many-`NULL`s rule; the S010
  rules that A1 keeps (absent = unchanged, lock order person → trades, the
  audit stamp on a trades-only change, held inactive trades, duplicates by
  index) all exist in the working tree today and survive a rename unchanged.
- The current code's masking helper (`_technicians_out`, `has_perm`) and the
  `UNIQUE_KEY_ERRORS` mapping are the right places for A1's changes; no new
  pattern is needed.
- `people:edit` = `("maint_engineer", "it_admin")`, manager by the ladder; no
  `admin`, no `*` mixing; reads stay `masters:read`.
- The 403-with-field shape for the login rule matches `ApiError` and the
  dialog's `fieldError`.
- Track: S010 is full track (no `Track` line, written before 16-10-2026); A1
  is reviewed in one round at the user's request.
- The S011 open point "a person without a login can hold any role" is S011's;
  with BR-A1-02 answered it is harmless.
