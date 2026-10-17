```
Step: S010 — Technicians and trades
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S010 — Code review, round 2 (amendment A1: Team)

**Verdict:** no `blocker` or `major` finding is open. There is one `minor`
finding and three `nit` findings. The security rules of A1 (rules 1, 2, 3 and
7) are in the code as the brief states them, they are enforced on the server,
and each one has a test. The frontend follows the same rules.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: **763 passed** in 41.6 s, including every case in the new
    `test_people_api.py`.
  - Frontend: vitest, 6 files, **36 passed**.
- `npx vite build` in `frontend/`: **clean**. 148 modules, built in 2.05 s, no
  warnings.
- I did not reset the dev DB. The suite ran on the schema the coder rebuilt and
  showed no stale-schema symptom.

## Scope reviewed

- Spec:
  - brief § 1–§ 9 as superseded by § 10 A1;
  - "A1 rules added after review" 1–9, which win where they differ;
  - the gate-A decision: the section is called "Team".
- Report: `3-impl-report.md` § "Amendment A1 — Team", its 10 decisions, and its
  Manual checks.
- How I read the diff: `git diff -w --ignore-cr-at-eol`, plus the new files in
  full.
- Backend: `config_rbac.py`, `local_db.py` (v7), `masters_core.py`,
  `masters.py` (the trades and people routes, and the generalised
  `_check_grantable`).
- Backend tests: `conftest.py`, `test_masters_core.py`, `test_rbac.py`,
  `test_people_api.py` (new).
- Frontend: `PeoplePanel.vue` and `TradesPanel.vue` (both new),
  `MastersView.vue`, `stores/masters.js`, `stores/auth.js`, `useMasterForm.js`,
  `tests/navigation.test.js`. For context only: `useFormModal.js`.
- Docs, A1's share only: `Plan.MD` § 3 and § 5, `docs/Keycloak.md` § 5, the
  README S010 row.
- Not reviewed, as unrelated:
  - the S011 brief and its reviews;
  - the `Plan.MD` / `Keycloak.md` move of the shared-device text;
  - the README queued row about `user_units`;
  - `docs/review/`.

## Findings

### CR2-01 — minor — The round-1 findings are not answered in a Fix rounds section

`docs/steps/S010-technicians/3-impl-report.md` (no `Fix rounds` section; A1
decision 9 at `:263-266`)

- **Problem.** README § Findings asks the coder to answer every code-review
  finding in the report's **Fix rounds** section, each with `Accepted`,
  `Rejected` or `Deferred`. The report has no such section. The round-1
  outcomes are only mentioned in passing:
  - CR1-03 is handled inside A1 decision 9;
  - CR1-02 is "not done; it stays an optional nit", which is none of the three
    answers;
  - CR1-01 is not mentioned at all, although the report now has a
    `## Manual checks` section.
- **Failure scenario.**
  - At gate B the planner can't show which round-1 findings were accepted,
    rejected or deferred.
  - If the step is reopened later, CR1-02 has no recorded decision: nobody can
    tell whether it was rejected or simply forgotten.
- **Suggested fix.** Add `## Fix rounds` → `### Round 1 (4-code-review-r1.md)`
  with one row per finding:
  - CR1-01: `Accepted` (the `## Manual checks` section);
  - CR1-02: `Deferred` to a named step, or `Rejected` with the reason;
  - CR1-03: `Accepted` (the `uniq` login with an exact compare, and the `PUT`
    409).

### CR2-02 — nit — Clearing a login on create, by an engineer, is not tested

`backend/tests/test_people_api.py:183-191` (`test_editor_cannot_create_with_a_login`)

- **Problem.** Rule 3 says "carrying `username`" includes clearing it
  (`null` / `""`). The code covers this on both routes: `_check_login_change`
  (`masters.py:511`) tests `"username" in clean`.
  - The `PUT` test is parametrised over a new value, `None` and `""`.
  - The `POST` test sends only a real login.
- **Failure scenario.** A later change scopes the `POST` check to non-null
  logins, for example `if clean.get("username")`. An engineer's
  `POST {username: null}` then passes. That is harmless today, but the suite
  would not notice that rule 3 had been loosened on one of the two routes.
- **Suggested fix.** Parametrise the create test over `uniq.username()`,
  `None` and `""`, as the `PUT` test is.

### CR2-03 — nit — The manual-check boxes live under a sub-heading, not under `## Manual checks`

`docs/steps/S010-technicians/3-impl-report.md:91-98` and `:294-318`

- **Problem.** The top-level `## Manual checks` section holds only a pointer.
  The boxes themselves are under `### Manual checks` inside
  `## Amendment A1 — Team`.
- **What is right.** All three important checks of A1 rule 6 are there as
  unticked `- [ ]` boxes, with the right wording. The plain ones are a plain
  list, and S010's still-valid checks are carried over as notes.
- **Why it is only a nit.** Nothing is missing. But a planner or tool looking
  for boxes under `## Manual checks` finds none.
- **Suggested fix.** Move the A1 boxes into `## Manual checks` and leave the
  pointer in the A1 section, or the other way round.

### CR2-04 — nit — A stale line in the report about brief § 7

`docs/steps/S010-technicians/3-impl-report.md:286-288`

- **Problem.** The report says the § 7 known limit of rule 9 ("a firm and a
  person are indistinguishable") "is the planner's text to add". The brief
  already has that row: `1-brief.md:315`, "A firm and a person look alike
  (A1)".
- **Failure scenario.** At gate B the user reads that something is still to be
  done, when it is already done.
- **Suggested fix.** Reword the line to "already in brief § 7", or drop it.

## Earlier rounds

- **CR1-01** (the `## Manual checks` checklist): **resolved**. The section now
  exists, and its placement is covered by CR2-03.
- **CR1-02** (the list-of-ids check written twice): **still open**, `nit`. A1
  makes the case stronger. `_parse_trade_ids` (`masters_core.py:131`) lost its
  "at least one" rule, so its body is now the same check as
  `validate_unit_ids` (`:214`), word for word, apart from the label. The
  suggested `_parse_id_list(raw, label)` would now be a pure extraction with no
  special case. It still needs a recorded answer (CR2-01).
- **CR1-03** (two test gaps): **fixed**, verified in
  `test_people_api.py`:
  - `test_create_with_two_trades_ordered_by_name` takes its login from
    `uniq.username()`, sends it upper-case with spaces, and asserts exact
    equality with the normalised value;
  - `test_duplicate_login_is_409_and_cleared_login_is_reusable` now also
    covers `PUT {username: <taken>}` → 409 field `username`.

## Checked and found consistent

- **Login set, change or clear needs `masters:edit`** (rule 3):
  - `_check_login_change` runs in both `POST` and `PUT /people`, right after
    `clean_body`. It runs before `get_db()` and the transaction, so a refused
    request touches nothing.
  - It fires on `"username" in clean`, so it covers set, change and clear
    (`null` and `""` both reach `clean` as `None`).
  - The error is `ApiError("Only IT admin can set the login", 403,
    "username")`.
  - Tested for the engineer and the manager, on create, and on update over a
    new value / `None` / `""` × a person with and without a login. The DB is
    checked unchanged afterwards.
- **Own login → 403 for every role** (rule 2):
  - The check compares the already-normalised `clean["username"]` with
    `normalise_username(actor())`, and `actor()` comes from the token.
  - It applies to every holder of `masters:edit`, including the `admin` bypass.
  - An engineer is refused first by the `masters:edit` check (decision 4). Both
    answers are 403 field `username`, so "for every role" holds.
  - Clearing (`None`) is never "own", which is right: clearing grants nothing.
  - Tested on `POST` and `PUT`, with `" TEST_IT_ADMIN "` (case and spaces) and
    with a second IT admin's UPN-style login.
  - The frontend's decision 5 (send the login on an edit only when it changed)
    lets IT admin save their own record without weakening the server.
- **`active` of a person with a login** (rule 1):
  - In `update_person` (`masters.py:556-567`) the check reads `username` from
    the row returned by `_lock_row(cur, "people", …)`, inside the transaction,
    so it runs on the locked row.
  - A concurrent IT admin `PUT` that sets a login waits on the same row lock.
    The engineer therefore sees either the old state (no login, so allowed) or
    the new one (so 403), never a mix.
  - The 403 is raised inside `transaction(conn)`, before any trade or row
    write, so the whole request rolls back.
    `test_refused_change_writes_nothing_else` proves it: `{active: 0, name}`
    leaves the name unchanged.
  - Deactivate and reactivate are both refused for the engineer and the
    manager. IT admin may do both. Editors may do both on a person without a
    login.
  - Decision 3 (the rule fires on any `active` in the body, not only on a
    changed value) is stricter than the rule. It is reported and has no UI
    effect.
- **Who sees the login** (rule 7):
  - `_people_out` (`masters.py:493`) adds `has_login` for `people:edit` and
    deletes `username` unless the user has `masters:read_senior`.
  - It is used by the list and by `_fetch_person`, so `POST` and `PUT`
    responses are masked too.
  - The parametrised test covers all six roles:
    - operator, technician, storekeeper: neither key;
    - engineer, manager: `has_login` only;
    - IT admin: both.
  - `test_write_responses_are_masked_too` covers the engineer's `PUT` response.
    The engineer's `POST` response shows `has_login: false` with no username
    (`test_person_with_no_trades`).
  - IT admin also gets `has_login` (decision 2). That is reported and harmless.
- **Frontend rules:**
  - `TradesPanel.canEdit` checks `people:edit` (rule 4).
  - `PeoplePanel` has `canEdit` = `people:edit` and `canEditLogin` =
    `masters:edit`.
  - `toBody` deletes `username` whenever `canEditLogin` is false, so an
    engineer's save never carries it (rule 3).
  - The form has no `active` key, so a normal save never sends it. Deactivate
    goes through `changeActive`'s own `PUT {active}`, which doesn't pass
    through `toBody`.
  - `canChangeActive` (`PeoplePanel.vue:39`) hides `ActiveToggle` for a user
    without `masters:edit` when the row opened has `has_login`. If the row is
    stale, the server's 403 shows in the modal error.
  - Without `masters:edit` the Login field is read-only text, "Has a Yantra
    login: yes/no", with no help line. With it, the field is editable and shows
    the user's help line (rule 9).
  - The Login column shows the username for IT admin, a tick for engineers, and
    is absent for other roles.
  - Labels and badges:
    - name label "Name", help "A person, or a contractor firm.";
    - radios "Direct employee" / "Contractor";
    - badges "Direct" / "Contractor";
    - title "Team", icon `fa-people-group`;
    - tab order Sites, Units, Equip Class, Equip Type, Trades, Team, Unit
      access.
- **Pure core:**
  - `EMPLOYMENT`, `_parse_employment` (with the brief's message) and
    `validate_person` go through `_validate`.
  - `trade_ids` is optional on create, and `[]` is accepted on create and
    update.
  - The "at least one trade" rule and its tests are gone.
  - The login parser is unchanged.
  - No DB, clock or framework imports.
- **Shell, as in S010:**
  - Absent field means unchanged. `PUT {active}` keeps the trades and the
    login (tested).
  - Lock order is person → trades. The trade set is diffed, so kept rows keep
    their `granted_at/by` (tested).
  - The audit stamp is set on a trades-only change, including removing every
    trade (tested), and not on an unchanged set (tested).
  - Held inactive trades are kept but not newly given, on create and update
    (tested).
  - Duplicate logins are caught by `uq_people_username`, with A1's message, on
    `POST` and `PUT` (tested).
  - `_check_grantable` (`masters.py:419`) interpolates only a code-constant
    table name. Every id goes in as a `%s` parameter, so no SQL is built from
    client input.
  - `get_db()` gives the dead-connection retry and a 503 when the DB is down,
    as in the other masters.
  - The actor always comes from `actor()`.
- **RBAC:**
  - `people:edit = ("maint_engineer", "it_admin")`, and the manager inherits
    it.
  - No `admin` and no `*` in the tuple. No `technicians:edit` is left anywhere
    in the code.
  - `test_role_matrix` and `navigation.test.js` are updated in step.
  - The other roles get 403 on every write and 200 on both lists (tested).
- **Migration v7, edited in place** (rule 5):
  - `git log --all -S` finds no commit with v7 in it, so the in-place edit is
    within what the brief allows.
  - The description is "Trades, people".
  - `people` has `employment ENUM('direct','contractor')` and
    `uq_people_username` on a nullable column.
  - `person_trades` has `(person_id, trade_id)` as the PK, with
    `fk_person_trades_person` and `fk_person_trades_trade`.
  - Every statement uses `IF NOT EXISTS`, and there is no seed data.
  - The comment records the in-place edit, and the report records the
    dev-DB reset before the tests (decision 1).
  - `conftest._TABLES` empties `person_trades`, `people`, `trades`, child
    first.
- **Nothing of S011 is built.** There are no memberships, no supervisor, no
  site roles, no `people:assign_technicians`, and no access derived from a
  person's login. A grep for these over `backend/*.py` and `frontend/src`
  finds nothing.
- **Docs:**
  - `Plan.MD` § 3: the `people:edit` row, plus a short paragraph on what it
    covers (decision 10, reported).
  - `Plan.MD` § 5: the rows `people`, `person_trades` and `breakdown_labour`
    "Person".
  - `Keycloak.md` § 5: "Team › login is IT admin's only".
  - README: the S010 row's title and status.
- **Decisions taken** (A1 § 4, items 1–10): each one is either inside the rules
  or stricter than them, and each is listed. I found no unreported departure
  and nothing built beyond A1.

## Manual browser checks still needed (user)

The important ones are those in the report's A1 Manual checks:

- **As engineer, a person without a login:**
  - add a person: Direct employee, two trades, no login;
  - the Login field is read-only ("Has a Yantra login: no") with no help line;
  - rename them and change their trades: it saves, with no 403.
- **IT admin sets a login, then the engineer looks:**
  - as IT admin, set that person's login;
  - then, as engineer, the dialog shows "Has a Yantra login: yes" read-only;
  - Deactivate / Reactivate is not offered on that person.
- **As engineer, contractors and deactivation:**
  - add a contractor named as a firm, and one named as a person;
  - deactivate a person who has no login: it works.

Also worth a look:

- **As operator:** Team and Trades are listed, with no Login column and no
  buttons.
- **The S007 guard:** a changed Team dialog asks before discarding. Ticking a
  trade and unticking it again is not a change.
- **The look:** the badges ("Direct" / "Contractor") and the trade chips, with
  the inactive ones dimmed.
- **An inactive trade:** after deactivating a trade, it shows greyed
  "(inactive)" on a person who holds it, is kept on save, and is not offered
  to others.
- **As IT admin:**
  - the Login column shows usernames;
  - the help line shows your own login as the example;
  - typing your own login is refused under the field.
