```
Step: S010 — Technicians and trades
Doc: impl-report
Author: Coder (Sonnet)
Date: 16-10-2026
Status: In code review
```

# S010 — Implementation report

## 1. What was built

- **Trades** master: create, rename, deactivate, reactivate.
- **Technicians** master: a record per maintenance person or contractor firm, with kind (in-house / contract), one or more trades, an optional Yantra login, and an active flag (never deleted).
- Two new sections on the Masters page, "Trades" and "Technicians", after "Equipment types". Every role reads them (`masters:read`). Engineers, managers and IT admin edit (`technicians:edit`). The login is returned and shown only to holders of `technicians:edit`.
- Migration **v7** (`trades`, `technicians`, `technician_trades`).

## 2. How it works

- **Pure core (`masters_core.py`).** `validate_trade` and `validate_technician` go through the existing `_validate` field table, so an absent field means "unchanged" on update.
  - Trade name: 1–50 characters (`TRADE_NAME_MAX`), through a shared `_parse_bounded_name`.
  - `kind` must be `in_house` or `contract` (required on create).
  - `trade_ids` is a non-empty list of ints; duplicates are removed; `[]` gives 400 "Choose at least one trade" on create and update. It is required on create.
  - `username`: `None` or `""` becomes `None` (clears it); otherwise `validate_username` (strip, lower-case, regex). An absent username is left out.
- **Shell (`masters.py`).**
  - Trades: `GET /trades` (inactive hidden unless `include_inactive=1`), `POST`, `PUT`. Writes need `technicians:edit`. A duplicate name is caught by the `uq_trades_name` index and becomes 409 on field `name`.
  - Technicians:
    - `GET /technicians` is ordered by name, id. Trades for all rows come from one query (`IN (…)`, ordered by trade name, inactive included with `active: bool`).
    - `username` is deleted from every row unless `has_perm("technicians:edit")`.
    - `POST` runs in one transaction: lock and check the trades, insert the technician, insert the links.
    - `PUT` locks the technician row first, then the trades (`_check_grantable`). It diffs the trade set, so kept trades keep their `granted_at/by`. When only the trades changed, it stamps `updated_at/by` by hand, because `update_row` does nothing for an empty change.
    - `PUT {active}` alone touches nothing else, so Deactivate keeps the trades and login.
    - A duplicate login becomes 409 on field `username` through `uq_technicians_username`.
  - `_check_grantable` is generalised to `(cur, table, ids, held, field, label)` and used for units and trades. Its messages for units are unchanged.
- **Frontend.**
  - `TradesPanel.vue` and `TechniciansPanel.vue` use `FormModal` and `useMasterForm`, so the S007 dialog guard applies.
  - The technician dialog has kind radios (the name label becomes "Contractor firm" for contract), trade checkboxes, and a login field with the help text.
  - Trade checkboxes show the active trades plus the inactive ones the technician already holds, fixed when the dialog opens and marked "(inactive)".
  - `trade_ids` is kept sorted so the dirty check compares by value.
  - The table shows a kind badge, trade chips (inactive ones dimmed), and a Login column only when `canEdit`.

## 3. Files touched (14 changed or new)

Backend:
- `backend/local_db.py`: migration v7, safe to run twice.
- `backend/masters_core.py`: validators and parsers.
- `backend/masters.py`: routes, `_check_grantable` generalised, `UNIQUE_KEY_ERRORS` entries, `has_perm` import.
- `backend/config_rbac.py`: `technicians:edit` = `("maint_engineer", "it_admin")`.
- `backend/tests/conftest.py`: `_TABLES`, `uniq.trade_name()`, `make_trade`, `make_technician`.
- `backend/tests/test_masters_core.py`: `TestTrade` and `TestTechnician`.
- `backend/tests/test_technicians_api.py` (new): trades, technicians, login masking and access.
- `backend/tests/test_rbac.py`: `test_role_matrix` rows for engineer, manager and IT admin.

Frontend:
- `frontend/src/views/masters/TradesPanel.vue` (new).
- `frontend/src/views/masters/TechniciansPanel.vue` (new).
- `frontend/src/views/masters/useMasterForm.js`: passes `toBody` through.
- `frontend/src/views/MastersView.vue`: two sections and panels.
- `frontend/src/stores/masters.js`: `trades`, `ensureTrades()`, cleared in `resetMasters()`.
- `frontend/tests/navigation.test.js`: the key in the engineer, manager and IT admin lists.

Docs:
- `docs/steps/S010-technicians/1-brief.md`: status line only.
- `docs/steps/README.md`: S010 index row only.
- `docs/steps/S010-technicians/3-impl-report.md`: this report.

## 4. Decisions taken

None departs from the design.

1. `useMasterForm` takes and passes `toBody` (a 2-line change). It was needed for the brief's "`toBody` sends `""` as `null`" and benefits any master. The backend also accepts `""` as "clear".
2. The technician form does **not** carry `active` (the brief's § 5.5 lists it in `{name, kind, username, trade_ids, active}`). `active` is changed only through `ActiveToggle` (`PUT {active}`), as in the other panels. Sending a stale `active` with every save could silently overwrite a concurrent activation change.
3. The technicians list is held in the panel (a local ref), not in the masters store. The brief asks only for `ensureTrades()` in the store.
4. The shared `_parse_bounded_name(raw, max_len)` backs both `parse_name` and the trade-name parser.
5. The test fixtures `make_trade` and `make_technician` create through the real API as IT admin.

## 5. Not done, deferred or assumed

- **Tests run:** `tooling/run-tests.bat`: backend 735 passed (including 132 in `test_masters_core.py`); frontend vitest 36 passed (6 files). `npx vite build` in `frontend/`: built clean in 1.94 s.
- **Not done:** nothing from the brief is skipped.
- **Plan.MD** already holds the S010 entries (§ 3 matrix, § 4.2, § 5), done at approval, and was not touched.
- **Manual browser check still needed** (the brief's "Manual checks (user)"):
  - As engineer: add trades Electrician, Fitter and Tool maker. Add an in-house technician with two trades and a login. Add a contract record named after a firm.
  - Deactivate a trade, then open that technician: the trade is greyed "(inactive)", kept on save, and not offered to others.
  - Deactivate a technician from its dialog: trades and login are kept.
  - As operator: both lists are visible, with no Login column and no Add or Edit buttons.
  - Edit a technician and close the dialog: the discard confirmation appears.
  - The rendered look of the badges and chips.
- Whitespace-only IDE changes were left as they are.

## Manual checks

**Superseded by amendment A1.** S010's own checks (technicians, kind, an
engineer typing a login) no longer match the code: A1 reworked the screen into
Team before any commit. The checklist to tick is A1's, under
"Amendment A1 — Team › Manual checks" below (A1 rule 6, which replaces brief
§ 8's checks). S010's checks that still apply unchanged are carried into it as
plain notes.

## Late change at gate B (user, 16-10-2026)

- `frontend/src/views/MastersView.vue`: the Masters tab labels "Equipment
  classes" and "Equipment types" shortened to "Equip Class" and "Equip Type"
  (the user asked). The panels' own headings are unchanged.
- `frontend/src/stores/auth.js`: a `userLogin` ref (the Keycloak username from
  `/api/auth/me`), next to `userName` (the display name).
  `frontend/src/views/masters/TechniciansPanel.vue`: under the Login field, a
  help line "Their Maintenance Team Login ID. Your own login, for ex:
  <username>" (wording by the user), so the person typing
  a login sees the format Keycloak uses (logins aren't checked against
  Keycloak; user, 16-10-2026). Frontend tests 36 passed; `npx vite build`
  clean.

## Amendment A1 — Team

Implemented 16-10-2026 by the coder (Opus), from brief § 10 A1, its "A1 rules
added after review" (rules 1–9, which win where they differ) and the gate-A
decision that the section is called **"Team"**. Nothing of S011 is built.

### 1. What was built

- **Technicians became the Team register** (Masters section "Team",
  `fa-solid fa-people-group`): one record per person, or per contractor firm,
  whichever the user enters.
- **Fields:** name; **employment** `direct` / `contractor` (replaces `kind`);
  **trades**, now optional (none, one or more); optional **login**; active.
- **Permission** `technicians:edit` → **`people:edit`** (engineer, IT admin;
  manager inherits). It covers the register and the trades list.
- **The login is IT admin's** (`masters:edit`): set, changed or cleared only by
  IT admin; nobody can set their own login; deactivating or reactivating a
  person who has a login is IT admin's too.
- **Who sees the login:** engineers and managers see only whether a person has
  one (`has_login`, a tick in the Login column); IT admin sees the username.
  Operators, technicians and storekeepers see neither.
- **API** moved to `/api/masters/people` (was `/technicians`), with
  `employment` in place of `kind`. Trades routes unchanged.
- **Migration v7 edited in place**: `people` and `person_trades` replace
  `technicians` and `technician_trades`.

### 2. How it works

- **Pure core (`masters_core.py`).** `EMPLOYMENT = ("direct", "contractor")`,
  `_parse_employment` ("Employment must be direct or contractor"),
  `validate_person` through `_validate`'s field table. `trade_ids` is now
  optional on create (absent = no trades) and `[]` is accepted on create and
  update; the "Choose at least one trade" rule is gone. The login parser is
  unchanged (`None` / `""` clears it, otherwise `validate_username`).
- **Shell (`masters.py`).**
  - `_check_login_change(clean)` runs in both `POST` and `PUT /people`, after
    `clean_body` and before the transaction. If the body carries `username`
    (set, changed or cleared): without `masters:edit` → 403 field `username`
    "Only IT admin can set the login"; a non-null login equal to
    `normalise_username(actor())` → 403 field `username` "You can't set your
    own login" (rules 2, 3).
  - `PUT /people/<id>` locks the person row (`_lock_row`), and if the body
    carries `active` while the **locked** row has a login and the user lacks
    `masters:edit` → 403 field `active` "Only IT admin can activate or
    deactivate a person with a login" (rule 1). The transaction rolls back, so
    nothing else in that body is written either.
  - `_people_out` adds `has_login` for `people:edit` holders and deletes
    `username` unless the user holds `masters:read_senior` (rule 7). Applied to
    the list and to the write responses.
  - Everything else is S010's logic re-pointed: lock order person → trades,
    the trade set diffed (kept trades keep `granted_at/by`), the audit stamp on
    a trades-only change, held inactive trades kept but not newly given, the
    duplicate login caught by `uq_people_username` → 409 "Another person
    already has this login (it may be an inactive one)".
- **Frontend.**
  - `PeoplePanel.vue` (title "Team"): columns name, employment badge
    ("Direct" / "Contractor"), trades, Login (editors only: the username for
    IT admin, a tick for engineers), status.
  - Dialog: Name (help "A person, or a contractor firm."), Employment radios
    ("Direct employee" / "Contractor"), trade checkboxes (none required),
    Login. With `masters:edit` the Login is a text field with the user's help
    line (rule 9: shown only when editable); without it, read-only text "Has a
    Yantra login: yes/no" and no help line.
  - `toBody` drops `username` for users without `masters:edit`, so an
    engineer's save never carries it (rule 3).
  - Deactivate / Reactivate is hidden for an engineer when the person has a
    login (rule 1); the server refuses it anyway.
  - `TradesPanel.vue`'s `canEdit` checks `people:edit` (rule 4).
  - Tab order: Sites, Units, Equip Class, Equip Type, Trades, Team, Unit
    access.

### 3. Files touched for A1 (19)

Backend:
- `backend/local_db.py`: v7 edited in place: description "Trades, people",
  `people` (`employment` ENUM, `uq_people_username`) and `person_trades`
  (`person_id`, `fk_person_trades_person`, `fk_person_trades_trade`); the
  comment records the in-place edit.
- `backend/masters_core.py`: `EMPLOYMENT`, `_parse_employment`,
  `_PERSON_FIELDS`, `validate_person`; `trade_ids` optional and may be empty.
- `backend/masters.py`: `/people` routes, `_people_out` (`has_login` /
  username masking), `_check_login_change`, the `active` check on the locked
  row, SQL on `people` / `person_trades`,
  `UNIQUE_KEY_ERRORS["uq_people_username"]`, trade writes on `people:edit`,
  docstrings.
- `backend/config_rbac.py`: `people:edit` and its comment.
- `backend/tests/conftest.py`: `_TABLES` (`person_trades`, `people`, `trades`),
  `make_person(trades=None, **overrides)`.
- `backend/tests/test_masters_core.py`: `TestPerson` replaces
  `TestTechnician`.
- `backend/tests/test_people_api.py` (new): replaces `test_technicians_api.py`.
- `backend/tests/test_technicians_api.py`: removed (untracked; replaced).
- `backend/tests/test_rbac.py`: `test_role_matrix` rows use `people:edit`.

Frontend:
- `frontend/src/views/masters/PeoplePanel.vue` (new): replaces
  `TechniciansPanel.vue`.
- `frontend/src/views/masters/TechniciansPanel.vue`: removed (untracked;
  replaced).
- `frontend/src/views/masters/TradesPanel.vue`: `canEdit` on `people:edit`;
  wording "technician" → "person / people".
- `frontend/src/views/MastersView.vue`: section `people`, label "Team", icon,
  import.
- `frontend/tests/navigation.test.js`: `people:edit` in the engineer, manager
  and IT admin lists.

Docs:
- `docs/Plan.MD`: § 3 matrix row `people:edit` and a short paragraph under the
  matrix on what it covers and the login rule; § 5 rows `people`,
  `person_trades`, and `breakdown_labour` "Person, …".
- `docs/Keycloak.md` § 5: "Team › login", a line that the login is IT admin's
  only, and the example line now says the Team dialog shows IT admin's own
  login.
- `docs/steps/README.md`: S010 row only (title "Team and trades", status).
- `docs/steps/S010-technicians/1-brief.md`: status line only.
- `docs/steps/S010-technicians/3-impl-report.md`: this section; the S010
  Manual checks boxes replaced by a pointer here.

### 4. Decisions taken

1. **Migration v7 edited in place** (rule 5), not a new v8. Why this is
   acceptable here, against the append-only rule: v7 is in no commit and in no
   deployed database; only the disposable dev container had it. Steps taken:
   edited v7; ran `tooling/dev/dev-db-reset.bat` (container and volume dropped
   and recreated, so both `vel_yantra_master` and `vel_yantra_test` lost
   `db_version` 7) **before any test**; then ran the tests, which re-applied
   v1–v7 to the test DB. The dev master DB is rebuilt by the backend on its
   next start. v8 is left to S011.
2. **`has_login` goes to every `people:edit` holder, IT admin included**; IT
   admin also gets `username`. One field the screen can always rely on for
   editors.
3. **The `active` rule fires on any `active` in the body**, not only on a
   changed value (rule 1 says "changing"). Stricter and simpler; the dialog
   sends `active` only through Deactivate / Reactivate.
4. **Order of the login checks:** `masters:edit` first, then the own-login
   check. An engineer typing their own login gets "Only IT admin can set the
   login"; both are 403 field `username`. Clearing (`null`) is never "own".
5. **The dialog sends `username` on an edit only when it changed** (IT admin
   only). Without this, IT admin could never save their own Team record (a
   rename, a trade): every save would carry their own login and rule 2 would
   refuse it. The server stays strict (any carried login equal to your own
   → 403).
6. **Read-only login on create** shows "Has a Yantra login: no" for engineers,
   so the field reads the same in both dialogs.
7. **Texts the brief does not set:** "Add person" / "Edit person", "No people
   yet.", and the 403 message for `active` ("Only IT admin can activate or
   deactivate a person with a login").
8. **`make_person` defaults to no trades** (trades are optional now); tests
   that need trades pass them.
9. **CR1-03 handled while rewriting the tests**: the login in the create test
   comes from `uniq` and is compared exactly (sent upper-case with spaces);
   the duplicate-login test also covers `PUT` → 409. CR1-02 (a shared id-list
   parser) is not done; it stays an optional nit.
10. **Plan § 3:** besides the matrix row, a four-line paragraph under it says
    what `people:edit` covers and that the login is IT admin's. Rule 4 named
    only the matrix; the paragraph follows how the other keys are explained
    there.

No departure from A1 or its rules.

### 5. Not done, deferred or assumed

- **Tests run** (after the dev DB reset):
  - `tooling/run-tests.bat`: exit 0; backend **763 passed** (54 s), frontend
    vitest **36 passed** (6 files).
  - `npx vite build` in `frontend/`: built clean in 2.08 s, no warnings.
- **Not built (S011's):** site roles, memberships, supervisor,
  `people:assign_technicians`, access from a person's login. The names
  `people`, `person_trades` and `people.username` are exactly as A1 states, for
  S011 A1 to build on.
- **S011's brief still names `technicians:edit`** (its § 5) and "technicians
  (S010)". Not edited: it is S011's brief.
- **Brief § 7 known limit** (rule 9: "a firm and a person are
  indistinguishable in the record") is the planner's text to add; the brief
  was not edited beyond its status. It holds for the code.
- **Plan § 4.2** still says "one or more technicians per ticket"; left as it
  is (phase-3 narrative; rule 4 names only § 3 and § 5).
- The dev master DB is empty after the reset; any masters entered there before
  are gone (dev data is disposable).

### Manual checks

From A1 rule 6 (replaces brief § 8's checks). The user ticks each important one
or skips it with a reason.

Important:
- [ ] As engineer: add a person (Direct employee, two trades, no login). The
  Login field is read-only ("Has a Yantra login: no") with no help line.
  Rename them and change their trades: it saves (no 403).
- [ ] As IT admin: set that person's login. Then as engineer: the dialog shows
  "Has a Yantra login: yes" read-only, and Deactivate / Reactivate isn't
  offered on that person.
- [ ] As engineer: add a contractor named as a firm and one named as a person;
  deactivate a person without a login: it works.

Also:
- As operator: Team and Trades are listed, with no Login column and no Add or
  Edit buttons.
- A changed Team dialog asks before discarding (S007 guard).
- The employment badges ("Direct" / "Contractor") and the trade chips look
  right.
- Carried from S010: deactivate a trade, then open a person holding it: the
  trade is greyed "(inactive)", kept on save, and not offered to others.
- As IT admin: the Login column shows usernames; the help line under the Login
  field shows your own login as the example; typing your own login is refused.

## Fix rounds

Added by the planner at gate B (CR2-01), answering round 1; round 2 left no
blocker or major finding.

### Round 1 (`4-code-review-r1.md`)

| Finding | Answer |
|---|---|
| CR1-01 No `## Manual checks` section | **Fixed.** Added at gate B, then superseded by A1's checklist. |
| CR1-02 `_parse_trade_ids` repeats `validate_unit_ids` | **Deferred** — a nit, left at the user's choice at gate B. |
| CR1-03 Two test gaps (fixed login, `PUT` duplicate login) | **Fixed** in the A1 rewrite: `uniq` login compared exactly; `PUT` duplicate login → 409. |
