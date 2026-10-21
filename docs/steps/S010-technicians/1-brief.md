```
Step: S010 — Technicians and trades
Doc: brief
Author: Planner (Opus)
Date: 16-10-2026 (revised 16-10-2026 after brief-review r1)
Status: Committed c486a4a; manual checks pending (A1 approved 16-10-2026 by KLA)
```

# S010 — Technicians and trades

Keycloak says only that someone has the `maint_technician` role. The plant
needs to know more: who the maintenance people are, what each can do
(electrician, fitter, tool maker, …), and which of them are the plant's own
staff and which come from a contractor. Breakdown tickets (phase 3) and PM jobs
(phase 4) will record who worked and how long (Plan § 4.2, `breakdown_labour`).
This step makes the list of people they pick from.

**Depends on:** S008 committed. This step is migration **v7** (S009 was
dropped on 16-10-2026 and its v7 reverted, so v7 is free; corrected before
coding, no design change).

**Related:** S011 (planned next) moves roles from Keycloak into Yantra, per
site. It will change how `technicians:edit` is *evaluated*, not this step's
data or rules.

User decisions taken while planning (16-10-2026):
- a technician is a record of its own, **with or without** a Yantra login;
- a technician can have **several trades**;
- technicians and trades are maintained by **engineers** (and so managers)
  **and IT admin**;
- **in-house or contract** is recorded. For contract labour, no person is
  named: the record's name is the **contractor's firm** (one record per firm).

Background reading:
- `docs/Plan.MD` § 3 (roles), § 4.2 (who worked, time spent), § 5 (tables);
- `docs/Maintenance-Philosophy.md` § 2 (TPM pillars: training and education);
- `docs/steps/S001-basic-masters/1-brief.md` (masters pattern, unit access, the
  read hierarchy) and `docs/steps/S004-equipment-types-notes/1-brief.md`;
- `backend/masters.py`, `backend/masters_core.py`,
  `frontend/src/views/masters/UserUnitsPanel.vue` (a set replaced in one save,
  held inactive items), `frontend/src/views/masters/EquipmentClassesPanel.vue`.

## 1. What will be built

1. **Trades**: a short list, e.g. Electrician, Fitter, Tool maker, Welder,
   Instrumentation. Create, rename, deactivate, reactivate.
2. **Technicians**: one record per maintenance person, or per contractor firm:
   - **name**: the person's name; for contract labour, the firm's name;
   - **in-house or contract**;
   - **trades**: one or more;
   - **Yantra login** (optional): the person's Keycloak username, when they
     log in themselves. Later steps use it to know "this ticket is mine";
   - **active**: a person who left, or a firm no longer used, is deactivated,
     never deleted, so old tickets still name them.
3. Both are two new sections of the **Masters** page, "Trades" and
   "Technicians". Every role can read them (`masters:read`), as with the other
   masters; engineers, managers and IT admin edit them. The login is shown
   only to those who edit (§ 5.3).

**Out of scope:**
- picking technicians on tickets or PM jobs, or routing work by trade (phases
  3–4; they use this list);
- skill levels, certificates or a skill matrix (TPM training pillar, "later"
  in Maintenance-Philosophy § 2);
- a mapping from trades to ISO 14224's four disciplines (§ 2; later, for
  reports);
- shifts, availability, on-call;
- phone numbers, Telegram ids or any other personal data;
- labour rates or cost (Plan § 1: no maintenance cost, decided 13-10-2026);
- naming individual contract workers (user, 16-10-2026);
- checking that a login exists in Keycloak (Yantra can't list Keycloak users,
  as in S001), or creating one;
- a site or unit for a technician (§ 9.2).

## 2. Standards and practice

- **ISO 14224:2016, Table 8 "Maintenance data"**, row group *maintenance
  resources*: "maintenance man-hours, per discipline (mechanical, electrical,
  instrument, others)" and "total". In plain terms: not only how long a repair
  took, but how many hours of which kind of skill it used. A trade is that
  discipline, finer than the standard's four. Trades per person are the
  **pick-list** for the labour row: a person with several trades can't be split
  by trade from the person record, so the phase-3 labour row will carry the
  trade worked, pre-filled when the person has only one (**pointer for the
  phase-3 brief**). A trade → discipline mapping for ISO-style reports is later.
- **EN 15628:2014 (qualification of maintenance personnel)** defines three
  levels: *maintenance technician specialist*, *maintenance supervisor /
  maintenance engineer*, and *maintenance manager*, each with the knowledge,
  skills and competences required. In plain terms: the standard says what a
  person at each level must know and be able to do. A trade is the *kind* of
  work, not the level; levels are left for later.
- **ISO 55001:2014 § 7.2 (competence)** asks the organisation to know the
  competence of the persons doing work under its control that affects its
  assets, and to keep evidence of it. A technicians list with trades is the
  start of that register; certificates (e.g. an electrical licence) would be
  the evidence, later.
  **Departure, deliberate:** "persons under its control" includes contractors'
  people. Recording contract labour by firm (user decision) means Yantra holds
  no competence evidence per contract person; that evidence stays in the AMC /
  contract (Plant-Facts § 4). Reason: no personal data on contract workers
  (A.5.34).
- **SMRP** calls a trade a *craft* and reports labour by craft (e.g. craft
  utilisation and wrench time, in its work-management metrics). Yantra uses
  **trade**, the word used in Indian and British plants; the help text says
  "trade (craft)" once.
- **TPM, pillar "education and training"** keeps a **skill matrix**: people
  against skills, with a level in each. Trades per person are the matrix's
  first column. Levels come later (Maintenance-Philosophy § 2).
- **ISO 27001:2022 A.5.34 (privacy and protection of PII)** is about meeting
  the law on personal data; in India the Digital Personal Data Protection Act
  2023. Two parts:
  - **minimisation:** only what the maintenance work needs is kept: a name, the
    trades, the kind, an optional login. No phone, address or ID numbers.
    Contract labour is recorded by firm, not by person;
  - **retention:** a person's name is kept after they leave, because tickets
    and jobs will cite it (the audit trail is the purpose); nothing else about
    them is kept. That is why records are deactivated, never deleted.
- **ISO 27001:2022 A.5.15 (access control):** the login is an identifier, and a
  full login list is the first half of a credential attack, so it is shown only
  to those who maintain the link (§ 5.3), as S001 keeps usernames at the
  senior read level.
- **ISO 55001 § 7.6 (documented information)**, as for every master: no hard
  delete, `who/when` on every change (S001).

## 3. Where

### Backend

- **Migration v7** in `backend/local_db.py`, each statement safe to run twice
  (§ 4).
- **`backend/masters_core.py`:** `validate_trade(data, creating)` and
  `validate_technician(data, creating)` through `_validate`'s field table, so
  an absent field means **unchanged** on update (§ 5.2):
  - trade fields: `name` (1–50, `TRADE_NAME_MAX = 50`), `active`;
  - technician fields: `name` (`parse_name`), `kind` (required on create),
    `trade_ids` (required on create; a parser like `validate_unit_ids` that
    raises on `[]`), `username` (optional), `active`.
  Pure.
- **`backend/masters.py`:** the routes of § 6, with the locking of § 5.4.
- **`backend/api_common.py`:** `UNIQUE_KEY_ERRORS` entries
  `uq_trades_name` → field `name`, "A trade with this name exists", and
  `uq_technicians_username` → field `username`, "Another technician already has
  this login (it may be an inactive one)" (BR2-02).
- **`_check_grantable`** is generalised to (table, field, label) and used for
  both units and trades, not copied (BR2-03).
- **`backend/config_rbac.py`:** `technicians:edit` =
  `("maint_engineer", "it_admin")` (managers inherit it). Reads use
  `masters:read` (`*`).
- **`backend/tests/`:** cases in `test_masters_core.py`, a new
  `test_technicians_api.py`, and `test_rbac.py::test_role_matrix` (the
  engineer, manager and IT admin rows gain `technicians:edit`). `conftest.py`:
  `technician_trades`, `technicians`, `trades` in `_TABLES` (child first);
  fixtures `make_trade` / `make_technician` beside `make_type`, and
  `uniq.trade_name()`.

### Frontend

- **`frontend/src/views/masters/TradesPanel.vue`** (new): table + `FormModal`,
  modelled on `EquipmentClassesPanel` without the code field;
  `label: (r) => r.name` for `ActiveToggle`.
- **`frontend/src/views/masters/TechniciansPanel.vue`** (new): table (name,
  kind badge, trade chips, a Login column shown when the user holds
  `technicians:edit` (`canEdit`, the same rule as the server's masking),
  active) + dialog (§ 5.5); `label: (r) => r.name`.
- **`frontend/src/views/MastersView.vue`:** two sections after "Equipment
  types", before "Unit access": "Trades" (`fa-solid fa-screwdriver-wrench`) and
  "Technicians" (`fa-solid fa-helmet-safety`), `perm: "masters:read"`.
- **`frontend/src/stores/masters.js`:** `ensureTrades()`, cleared like the
  others after a save; the technicians panel uses it for its checkboxes.
- **`frontend/tests/navigation.test.js`:** the engineer, manager and IT admin
  lists gain the key.

### Docs

- `docs/Plan.MD`: § 3 matrix (`technicians:edit`), § 5 (`trades`,
  `technicians`, `technician_trades`), and the phase-3 pointer of § 2 in § 4.2
  and on the § 5 `breakdown_labour` row (the labour row carries the trade
  worked). Done at approval.
- **S011 touchpoint:** `technicians.username` stays a plain string, as
  `user_units.username`; whether S011 links logins to a users table is S011's
  call (BR2-04).

## 4. Data model (migration v7)

Audit columns as S001 (`created_at/by`, `updated_at/by`). Default collation
(`utf8mb4_general_ci`), so unique names compare ignoring case, as S004 § 4.

**`trades`**

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `name` | `VARCHAR(50) NOT NULL`, `uq_trades_name` |
| `active` | `TINYINT(1) NOT NULL DEFAULT 1` |
| audit | |

**`technicians`**

| Column | Type / rule |
|---|---|
| `id` | `INT AUTO_INCREMENT PRIMARY KEY` |
| `name` | `VARCHAR(100) NOT NULL` |
| `kind` | `ENUM('in_house','contract') NOT NULL` |
| `username` | `VARCHAR(100) NULL`, `uq_technicians_username` (many `NULL`s allowed) |
| `active` | `TINYINT(1) NOT NULL DEFAULT 1` |
| audit | |

**`technician_trades`**

| Column | Type / rule |
|---|---|
| `technician_id` | `INT NOT NULL`, FK `fk_technician_trades_technician` |
| `trade_id` | `INT NOT NULL`, FK `fk_technician_trades_trade` |
| `granted_at`, `granted_by` | as `user_units` |
| | `PRIMARY KEY (technician_id, trade_id)` |

- **No seed data** (S001 rule): the trades are entered in the UI.
- `name` is **not** unique among technicians: two people can share a name.

## 5. Rules

### 5.1 Trades
- Name: trimmed, 1–50 characters; a duplicate (any case, by the collation) →
  409 field `name` through `UNIQUE_KEY_ERRORS`. No `LOWER()` pre-check.
  Renaming is allowed (tickets will point at the id).
- Deactivating a trade needs no "in use" check: technicians keep it (shown as
  inactive), it just can't be newly given, as equipment types (S004).

### 5.2 Technicians: fields
- **Update semantics:** as every master, an **absent field means unchanged**.
  The Deactivate / Reactivate button sends `PUT {active}` only
  (`useMasterForm.changeActive`), and keeps the trades and login.
- **Name:** `parse_name` (trimmed, 1–100). Kept as entered.
- **Kind:** `in_house` or `contract`; required on create; may change on update
  (a firm entered as in-house by mistake). The dialog's name label follows it:
  "Name" / "Contractor firm".
- **Trades:** required on create; when present, at least one (400 field
  `trade_ids`, "Choose at least one trade"). Every id must be a trade (400);
  an inactive trade may be kept but not newly given (400), as
  `_check_grantable` does for units. The set is replaced by diffing, so kept
  trades keep their `granted_at/by`.
- **Login:** absent → unchanged; `null` or `""` → cleared (`NULL`); otherwise
  `normalise_username` and the `USERNAME_RE` check (the empty case is handled
  before the regex). A duplicate → 409 field `username` through
  `UNIQUE_KEY_ERRORS`, caught by the index, not by a pre-check (a SELECT then
  INSERT is a race, S001 § 5). The login is **not** checked against Keycloak
  or the role: it is a link, not a grant.
- **Contract with a login:** allowed (a contractor's supervisor may log in).
- **Active:** deactivate and reactivate freely. A deactivated technician keeps
  its login, so the login can't be given to someone else by mistake while the
  old record holds it; clearing it frees it.

### 5.3 Who sees what
- Lists: `masters:read` (every role).
- **`username` is returned only to holders of `technicians:edit`** (inline
  `has_perm`, the base's field-masking pattern). Other roles' rows have no
  `username` key. Nothing in phases 3–4 needs the login in a pick-list: a
  ticket picks by id, and "is this mine" is answered on the server.
- Writes: `technicians:edit`.

### 5.4 Writing safely
- **`POST /technicians`:** in one transaction, lock the given trade rows
  (`SELECT … FOR UPDATE`, `_check_grantable`'s shape), insert the technician,
  insert its trades.
- **`PUT /technicians/<id>`:** lock the technician row first (`_lock_row`),
  then the trade rows. Lock order technician → trades. Outside these routes
  only the trade `PUT` locks a trade row (one row, nothing else after it), and
  nothing in `equipment.py` or `documents.py` touches these tables, so no
  cycle.
- **Audit when only the trades change:** `update_row` does nothing with an
  empty `clean`, so when the trade set changes the technician row is stamped
  (`UPDATE technicians SET updated_at = NOW(), updated_by = %s`), and "who/when
  on every change" holds.
- **Trades inside each item:** one query for all rows
  (`… technician_trades tt JOIN trades t … WHERE tt.technician_id IN (…)`),
  ordered by trade name, inactive trades included with their `active` flag.

### 5.5 The technician dialog
- Form: `{name, kind, username: "", trade_ids: [], active}`; `toBody` sends
  `""` as `null`. The S007 guard works on it (arrays snapshot by value).
- **Kind:** radio buttons, on create and edit.
- **Trades:** checkboxes for the active trades **plus the inactive ones this
  technician already holds**, fixed when the dialog opens (`UserUnitsPanel`'s
  `heldInactiveIds`), greyed and marked "(inactive)", so saving never drops a
  held inactive trade.
- **Login:** a text field with the help line "Their Yantra login, if they have
  one. Access still comes from their role and unit access."

## 6. API (`/api/masters/…`)

| Method and path | Permission | Result |
|---|---|---|
| `GET /trades` | `masters:read` | `{items, total}`, `ORDER BY name`; inactive hidden unless `include_inactive=1` |
| `POST /trades`, `PUT /trades/<id>` | `technicians:edit` | the trade; 400 / 404 / 409 |
| `GET /technicians` | `masters:read` | `{items, total}`, `ORDER BY name, id`; each with `trades: [{id, name, active}]` (by name); `username` only for `technicians:edit` (§ 5.3); filter `include_inactive` only. Kind and trade filters are left to the phase-3 pick-list, which states its own needs (BR2-01) |
| `POST /technicians`, `PUT /technicians/<id>` `{name, kind, username, trade_ids, active}` | `technicians:edit` | the technician with its trades; absent fields unchanged on `PUT` |

- Lists are not paginated (S001 rule: small lists; well under 200 people).

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| A technician is its own record, login optional | Helpers and contract labour never log in, but their hours are recorded by someone else (user) | One row per Keycloak login |
| Trades as a list kept in the DB | Plants differ; a trade is added without a release | A fixed list in code |
| Several trades per technician | Multi-skilled people are common (user); the labour row will carry the trade worked (§ 2) | One trade |
| Contract labour recorded by firm, in the name field | No personal data on contract workers (user; A.5.34) | A person per contract worker plus a firm field |
| `technicians:edit` = engineer, IT admin (manager inherits) | The maintenance side knows who can do what; IT admin maintains masters (user) | `masters:edit` (IT admin only) |
| The login shown only to editors | Minimisation; S001 keeps usernames at the senior level (A.5.15, A.5.34) | Shown to every role |
| Absent field = unchanged on `PUT` | The shared Deactivate button sends `{active}` only; every master works so | Always the full body |
| Duplicates caught by the unique indexes | No SELECT-then-INSERT race (S001 § 5) | A friendly pre-check naming the holder |
| No site or unit on a technician | Unit access already says where a login works (S001; per site after S011) | A home site |
| The login is a link, not checked against Keycloak | Yantra can't list Keycloak users (S001) | A role check on save |
| Names not unique | Two people may share a name. A known limit: "ABC Engg" and "ABC Engineering" can both exist; no merge | Unique names |
| A firm and a person look alike (A1) | A contractor's name may be a firm or a person, the user's choice per entry; a known limit: nothing in the record tells them apart, so phase 3's labour lines can't either | An "is a firm" flag |

## 8. Tests and acceptance

### Pure (`test_masters_core.py`)
- `validate_trade`: blank, 50 characters accepted, 51 refused, trimmed.
- `validate_technician`: on create, `name`, `kind`, `trade_ids` required;
  kind unknown → error; `trade_ids` `[]` → error (create and update), absent on
  update → accepted and left out; non-integers, duplicates removed; login
  `None` / `""` → `None`, upper case → lower, invalid characters → error,
  absent on update → left out.

### API (`test_technicians_api.py`)
- Trades: create, list (inactive hidden / shown), rename, duplicate name in
  another case → 409 field `name`, deactivate, reactivate.
- Technicians:
  - create with two trades → 201 with both, ordered by name;
  - list with `trades`;
  - `PUT {active: 0}` on a technician with two trades → 200, both trades and
    the login kept;
  - update replacing the trades keeps the kept one's `granted_at`, and stamps
    `updated_by` even when only the trades changed;
  - `trade_ids: []` → 400; unknown trade → 400; an inactive trade newly given →
    400, kept → 200 and listed with `active: false`;
  - duplicate login → 409 field `username`; login cleared → `NULL`, and then
    reusable;
  - two technicians with the same name → both 201; `kind` changed on update →
    200.
- **Login masking:** an operator's list rows have no `username` key; an
  engineer's and IT admin's do.
- Audit columns set from the user.

### RBAC (`test_rbac.py`)
- `test_role_matrix`: the engineer, manager and IT admin rows gain
  `technicians:edit`.
- Engineer, manager, IT admin: 200/201 on writes. Technician, operator,
  storekeeper: 403 on writes. Every role: 200 on both lists.

### Frontend
- `navigation.test.js`: the new key in the engineer, manager and IT admin lists.

### Manual checks (user)
- As engineer: add the trades Electrician, Fitter, Tool maker; add an in-house
  technician with two trades and a login; add a contract record named after a
  firm; deactivate a trade, then open that technician: the trade is shown
  greyed "(inactive)" and kept on save, and isn't offered to others.
- Deactivate a technician from its dialog: its trades and login are kept.
- As operator: sees both lists, no Login column, no Add or Edit buttons.
- A changed technician dialog asks before discarding (S007 guard).

### Acceptance
- `tooling/run-tests.bat` green; `npx vite build` clean.

## 9. Open questions and assumptions

1. **Decided (user, 16-10-2026):** IT admin edits technicians and trades too.
2. **Confirmed (user, 16-10-2026):** no site or unit on a technician (§ 7). S011 will hold, per
   site, what each *login* may do; a non-login person's site adds nothing until
   tickets exist.
3. **Confirmed (user, 16-10-2026):** the trades list starts empty; it is entered in the UI.
4. **Confirmed (user, 16-10-2026):** contract records need no extra field: the firm's name is the
   name.

## 10. Amendments

### A1 — Team: a register of people, not only technicians

```
Requested by: KLA, 16-10-2026
Status: Approved 16-10-2026 by KLA
```

**Why.** The user wants one register of the people around the machines, with
or without a Yantra login, whatever their role, and S011's access attached to
the same person instead of a separately typed username (user, 16-10-2026). A
technician is then one kind of person. S011 amendment A1 adds the site roles;
this amendment reshapes S010's record so S011 can hang off it. Nothing of S010
is committed or deployed, so it is reworked in place.

**What changes** (supersedes the parts of § 1, § 3–§ 8 named below):

1. **"Technicians" becomes "Team"** (Masters section "Team",
   `fa-solid fa-people-group`): one record per **person**, or per contractor
   firm when the user chooses to record a firm.
2. **Fields of a person:**
   - **name**: a person's name, or a contractor firm's (the user's choice per
     entry; no rule);
   - **employment**: `direct` (direct employee) or `contractor`; replaces
     `kind` (`in_house` / `contract`). Labels "Direct employee", "Contractor";
   - **login** (optional): as S010's `username`. **Set and changed only by IT
     admin** (`masters:edit`), not by engineers, because from S011 a login
     turns the person's site roles into Yantra access (S011 A1). Engineers see
     it read-only;
   - **trades**: now **optional** (none, one or more). Engineers, operators
     and supervisors usually have none;
   - **active**: as S010. Deactivating a person will also end their access
     (S011 A1).
3. **Tables** (migration **v7**, edited in place: v7 is not committed or
   deployed anywhere; the dev databases are reset, per the CLAUDE-COMMON rule
   that dev databases are disposable):
   - `technicians` → **`people`**: `employment ENUM('direct','contractor')`
     instead of `kind`; `uq_people_username`;
   - `technician_trades` → **`person_trades`** (`person_id`, `trade_id`),
     FKs renamed accordingly;
   - `trades` unchanged.
4. **Permission key** `technicians:edit` → **`people:edit`** (engineer, IT
   admin; the manager inherits). It covers people's name, employment, trades,
   active, and the trades list. The login field needs `masters:edit` too
   (IT admin) on create and update; a `PUT` or `POST` carrying `username`
   without it → 403 field `username`.
5. **API** under `/api/masters/people` (was `/technicians`); same shapes with
   `employment` instead of `kind`. The login masking of § 5.3 stays (shown to
   `people:edit` holders). The trades routes are unchanged.
6. **Rules that change:** trades may be empty on create and update (the
   "at least one trade" 400 goes); the duplicate-login message becomes
   "Another person already has this login (it may be an inactive one)".
   Everything else in § 5 holds (absent field = unchanged; lock order person →
   trades; the audit stamp on a trades-only change; held inactive trades kept;
   duplicates caught by the unique indexes).
7. **Frontend:** `TechniciansPanel.vue` → `PeoplePanel.vue` (title "Team");
   columns name, employment badge, trades, login (editors only), active; the
   dialog's login field is editable only with `masters:edit`, read-only text
   otherwise. The help line under it stays as the user worded it.

**Standards.** As S010 § 2. Adds: ISO 55001 § 7.2 (competence) asks for the
competence of *all* persons doing work affecting the assets, not only
technicians; one register of people is closer to that. ISO 27001 A.5.18:
one record per person is where joiners and leavers are handled (with S011 A1).

**Tests.** S010 § 8 re-pointed to `/people` and `employment`; plus: a person
with no trades → 201; an engineer setting or changing a login → 403; IT admin
→ 201 / 200; an engineer's update without `username` on a person who has a
login keeps it.

**Open points.**
- Contractor with a login: allowed, no rule (the user can't think of a case,
  but it costs nothing to allow).
- The Masters tab order: Sites, Units, Equip Class, Equip Type, Trades, Team,
  User access (until S011 A1 merges User access into Team).

#### A1 rules added after review (`2-brief-review-r3.md`)

These override the A1 text above where they differ.

1. **Active of a person with a login is IT admin's** (BR-A1-01). On a person
   who has a login, changing `active` needs `masters:edit`, checked on the
   **locked** person row in `PUT /people/<id>` → 403 field `active`. An
   engineer can't deactivate a manager (revocation) or reactivate a leaver IT
   admin deactivated (restoring access). The frontend hides Deactivate /
   Reactivate in that case. Persons without a login: `people:edit`, as before.
2. **Not your own login** (BR-A1-02). In `POST` / `PUT /people`, a normalised
   `username` equal to `normalise_username(actor())` → 403 field `username`
   "You can't set your own login", for every role. Otherwise IT admin could
   give roles to a person without a login, then set the login to their own
   username and gain access S011 § 9.6 forbids.
3. **The login check, exactly** (BR-A1-03):
   - "carrying `username`" includes clearing it (`null` / `""`): set, changed
     or cleared all need `masters:edit`;
   - the check is in the route, after `clean_body` (`"username" in clean`),
     before the transaction: `ApiError("Only IT admin can set the login",
     403, "username")`;
   - the dialog's `toBody` **omits** `username` when the user lacks
     `masters:edit`, so an engineer's save never carries it;
   - `trade_ids` is optional on create (absent = no trades); `[]` is accepted
     on create and update; the "at least one" rule and its tests go.
4. **Where** (BR-A1-04), besides the files named in points 3–7:
   - `frontend/src/views/masters/TradesPanel.vue`: `canEdit` checks
     `people:edit` (it checks `technicians:edit` today and would become
     read-only for everyone);
   - `masters_core.py`: `EMPLOYMENT = ("direct", "contractor")`,
     `_parse_employment` ("Employment must be direct or contractor"),
     `validate_person`; `masters.py`: routes, helpers, SQL on `people` /
     `person_trades`, docstrings, `UNIQUE_KEY_ERRORS["uq_people_username"]`;
     `config_rbac.py` comment and key; `local_db.py` v7 description;
   - tests: `test_technicians_api.py` → `test_people_api.py`; `conftest.py`
     `_TABLES` (`person_trades`, `people`, `trades`) and `make_person(trades=None,
     **overrides)`; `test_masters_core.py` (`TestPerson`); `test_rbac.py`;
     `navigation.test.js`;
   - frontend: `MastersView.vue` (section key `people`, label, icon, import);
     the panel's `canEdit` (`people:edit`) and `canEditLogin` (`masters:edit`);
   - docs: Plan § 3 matrix (`people:edit`), § 5 (`people`, `person_trades`,
     `breakdown_labour` "person"); `docs/Keycloak.md` § 5 ("Team › login",
     IT admin only); the README index row title (the folder slug stays);
   - **S010 text superseded:** § 1 out of scope "naming individual contract
     workers" (now the user's choice per entry); § 2's ISO 55001 § 7.2
     "Departure, deliberate" (now partial: a contractor may be a firm or a
     person); § 5.2 "Kind" and the "Contractor firm" label switch; the dialog's
     form-text "Contract labour is recorded by the contractor's firm".
5. **Migration v7 in place, exactly** (BR-A1-05). Acceptable: v7 is in no
   commit and no deployed database; only the disposable dev container has it.
   The coder (1) edits v7 (description "Trades, people", the three `CREATE
   TABLE` statements; v8 is left to S011); (2) **runs
   `tooling/dev/dev-db-reset.bat` before any test**, because both dev
   databases hold `db_version` 7 and would skip the edited v7; (3) runs the
   tests; (4) records the in-place edit and its reason in the impl report's
   `Amendment A1` section.
6. **Manual checks for A1** (BR-A1-06), replacing S010 § 8's:
   - **important** — as engineer: add a person (direct, two trades, no
     login); the Login field is read-only with no help line; rename them and
     change their trades: saves (no 403);
   - **important** — as IT admin: set that person's login; then as engineer:
     the dialog shows "Has a Yantra login: yes" read-only; Deactivate /
     Reactivate isn't offered on that person;
   - **important** — as engineer: add a contractor named as a firm and one
     named as a person; deactivate a person without a login: works;
   - plain — as operator: Team and Trades listed, no Login column, no
     buttons; the S007 guard on the Team dialog; the employment badges.
7. **Who sees the login** (BR-A1-07, option 1): engineers and managers
   (`people:edit`) get `has_login: true/false`; the username itself only to
   `masters:read_senior` holders (IT admin). The Login column shows a tick for
   engineers and the username for IT admin. S010 § 2's A.5.15 reason then
   holds again: the login list goes only to those who maintain it.
8. **Standards** (BR-A1-08): the login split is ISO 27001 **A.5.3**
   (segregation of duties) and **A.8.2** (privileged access rights);
   **A.5.16 (identity management)**: the person record with one login per
   person is where an identity is created, changed and retired; **A.5.34**:
   a contract worker may now be named, still with nothing beyond name,
   employment, trades and maybe a login.
9. **Small points** (BR-A1-09): the name label is "Name" for both
   employments, with help "A person, or a contractor firm"; the login help
   line ("Their Maintenance Team Login ID. …") shows only when the field is
   editable; badges "Direct" / "Contractor"; known limit, added to § 7: a firm
   and a person are indistinguishable in the record. **The section name
   ("Team" or "People") is put to the user at gate A**, since Keycloak's login
   role is `maintenance_team` and the register also holds operators and
   supervisors.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 16-10-2026

| Finding | Severity | Response |
|---|---|---|
| BR1-01 A `PUT` without `trade_ids` / `username` | major | **Accepted, option 1.** Absent = unchanged through `_validate`'s field table; `null`/`""` clears the login; tests for `PUT {active}` (§ 3, § 5.2, § 8). |
| BR1-02 Every role can read every login | major | **Accepted, option 1.** `username` only for `technicians:edit`; Login column hidden otherwise; a masking test (§ 2, § 5.3, § 7, § 8). |
| BR1-03 Labour by trade over-stated | minor | **Accepted.** Trades are the pick-list; the phase-3 labour row carries the trade; pointer added (§ 2, § 7). |
| BR1-04 Shell details | minor | **Accepted.** Lock order, audit stamp on a trades-only change, `UNIQUE_KEY_ERRORS` messages, collation, filter 400s, trade order, `kind` editable (§ 3, § 4, § 5, § 6, § 8). |
| BR1-05 Frontend details | minor | **Accepted.** Held inactive trades, `label`, form shape, kind radios and badge, section placement, `ensureTrades` used by the panel, Login column (§ 3, § 5.5). |
| BR1-06 Standards | minor | **Accepted.** Table 8 title; EN 15628's three levels; ISO 55001 § 7.6; the contract departure under § 7.2; A.5.34 retention and the DPDP Act; SMRP metrics (§ 2). |
| BR1-07 Tests and fixtures | nit | **Accepted** (§ 3, § 8). |
| BR1-08 Small points | nit | **Accepted.** Duplicate firm names as a known limit; § 1.3 reworded (§ 1, § 7). |

IT admin added to `technicians:edit` (user, 16-10-2026), after the review.

### Round 2 — `2-brief-review-r2.md` (Fable), answered 16-10-2026

All eight round-1 answers verified in the text; the IT admin change is
consistent throughout. No blocker or major finding; the loop ends here, and the
answers below are not re-reviewed.

| Finding | Severity | Response |
|---|---|---|
| BR2-01 The `kind` and `trade_id` filters have no consumer | minor | **Accepted.** Dropped, with their tests; phase 3 states its own needs (§ 6, § 8). |
| BR2-02 The duplicate-login message | nit | **Accepted.** "(it may be an inactive one)", still a static constant (§ 3). |
| BR2-03 Generalise `_check_grantable` | nit | **Accepted** (§ 3). |
| BR2-04 Small points | nit | **Accepted.** Plan § 4.2 / § 5 named for the pointer; the S011 touchpoint; lock wording; Login column follows `canEdit`; 50-character boundary test (§ 3, § 5.4, § 8). |

### Gate A — user decisions, 16-10-2026

- Assumptions § 9.2–9.4 confirmed.
- Coder: Sonnet (master-data screens on the existing pattern).
- Approved by KLA. Coding starts after S009 is committed.
- 16-10-2026: S009 dropped; the migration is v7, not v8 (numbering only).

### Amendment A1 — `2-brief-review-r3.md` (Fable), answered 16-10-2026

One round, as the user asked; the answers are not re-reviewed. Both majors are
answered in A1's "rules added after review" and put to the user at gate A.

| Finding | Severity | Response |
|---|---|---|
| BR-A1-01 An engineer can (re)activate a person with a login | major | **Accepted.** `active` of a person with a login needs `masters:edit`, on the locked row (rule 1). |
| BR-A1-02 IT admin can set a login to their own username | major | **Accepted.** Own username → 403 for everyone (rule 2). |
| BR-A1-03 The login check leaves three decisions; the dialog always sends `username` | minor | **Accepted** (rule 3). |
| BR-A1-04 "Where" is thin; `TradesPanel.vue` would lock | minor | **Accepted** (rule 4). |
| BR-A1-05 Migration v7 in place | minor | **Accepted.** Acceptable; the exact steps incl. the dev DB reset (rule 5). |
| BR-A1-06 Manual checks not re-pointed | minor | **Accepted** (rule 6). |
| BR-A1-07 Engineers still get every login | minor | **Accepted, option 1.** `has_login` for engineers; the username for IT admin (rule 7). |
| BR-A1-08 Standards | nit | **Accepted** (rule 8). |
| BR-A1-09 Small points | nit | **Accepted**; "Team" or "People" to the user (rule 9). |

### Amendment A1 — user decisions at gate A, 16-10-2026

- The section is called **"Team"** (matches Keycloak's `maintenance_team`).
