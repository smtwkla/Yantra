```
Step: S010 — Technicians and trades
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S010 — Brief review, round 2

**Verdict: no `blocker` or `major` finding open. One `minor` (BR2-01) and four `nit`s.**

Reviewed the brief as revised after round 1 (header "revised 16-10-2026 after
brief-review r1"), against `docs/Plan.MD` § 3 / § 4.2 / § 5 / § 8,
`docs/Maintenance-Philosophy.md` § 2–3 and § 11, `docs/Plant-Facts.md` § 4,
the S001 and S004 briefs, `.claude/SMTW-WebApp-Base.md` § RBAC (field
masking, read hierarchy), and the working tree: `backend/masters.py`,
`masters_core.py`, `config_rbac.py`, `api_common.py`, `auth_utils.py`,
`db_helpers.py`, `local_db.py` (v1–v7; S009's v7 is uncommitted, so v8 is
right), `tests/conftest.py`, `tests/test_rbac.py`, `tests/test_masters_core.py`,
`tests/test_masters_api.py::TestPermissions`, `tests/test_auth.py`;
`frontend/src/views/MastersView.vue`, `masters/UserUnitsPanel.vue`,
`masters/EquipmentClassesPanel.vue`, `masters/EquipmentTypesPanel.vue`,
`masters/useMasterForm.js`, `composables/useFormModal.js`,
`utils/formSnapshot.js`, `stores/masters.js`, `stores/navigation.js`,
`tests/navigation.test.js`; and `tooling/dev/docker-compose.dev.yml`
(MariaDB 11.4, for the collation claim).

---

## Round 1 — each `Accepted` answer verified in the brief text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 `PUT` without `trade_ids` / `username` (major) | § 3: both fields in `validate_technician`'s field table through `_validate`, so absent = unchanged; `trade_ids` parser raises on `[]`. § 5.2 "Update semantics", "Trades", "Login" (empty handled before the regex; `null` / `""` clears). § 6 "absent fields unchanged on `PUT`". § 8: pure tests for absent-on-update and `[]` on create and update; API test `PUT {active: 0}` keeps both trades and the login. | Yes |
| BR1-02 Every role could read every login (major) | § 5.3 `username` only to holders of `technicians:edit` (inline `has_perm`); § 1.3 reworded; § 2 A.5.15 added; § 7 row "The login shown only to editors"; § 3 Login column only when rows carry `username`; § 8 masking test (operator no key; engineer and IT admin have it). | Yes |
| BR1-03 Labour by trade over-stated (minor) | § 2 ISO 14224: trades are the pick-list; the phase-3 labour row carries the trade worked, pre-filled when there is one; marked "pointer for the phase-3 brief". § 7 "Several trades" row matches. | Yes |
| BR1-04 Shell details (minor) | § 5.4 lock order (POST: trade rows; PUT: technician then trades), audit stamp on a trades-only change, one query for the trades per item ordered by name with inactive included; § 3 `UNIQUE_KEY_ERRORS` entries; § 4 collation; § 5.1 no `LOWER()` pre-check; § 5.2 `kind` editable, name kept as entered; § 6 `kind` via `enum_arg`, `trade_id` via `_int_filter`, 400s in § 8. | Yes |
| BR1-05 Frontend details (minor) | § 5.5 held inactive trades (`heldInactiveIds`), form shape, `toBody` `""` → `null`, kind radios on create and edit; § 3 `label: (r) => r.name` for both panels, kind badge, sections after "Equipment types" before "Unit access", `TradesPanel` modelled on `EquipmentClassesPanel` without the code field, `ensureTrades()` used by the technicians panel, Login column conditional; § 8 manual check for the greyed "(inactive)" trade. | Yes |
| BR1-06 Standards (minor) | § 2: Table 8 "Maintenance data" with the *maintenance resources* row group and the four-way split being coarser than Yantra's trades; EN 15628's three levels; ISO 55001 § 7.6 for documented information; the contract-labour departure under § 7.2 with the AMC reason and A.5.34; A.5.34 minimisation *and* retention, DPDP Act 2023; SMRP craft metrics. | Yes |
| BR1-07 Tests and fixtures (nit) | § 3 `_TABLES` child-first order, `make_trade` / `make_technician`, `uniq.trade_name()`, the three `test_role_matrix` rows, `navigation.test.js` lists; § 8 has every test the finding asked for. | Yes |
| BR1-08 Small points (nit) | § 7 "Names not unique" row carries the "ABC Engg" / "ABC Engineering" limit; § 1.3 reworded; trade order inside an item in § 5.4. | Yes |

Nothing accepted in the Review log is missing from the body.

## New since round 1

- **IT admin on `technicians:edit` (user, 16-10-2026).** Consistent in every
  place it must appear: the decisions list, § 1.3, § 3 (`config_rbac`, the
  three `test_role_matrix` rows, the three `navigation.test.js` lists), § 7,
  § 8 (writes, masking test), § 9.1, and the Plan.MD § 3 update in § 3 Docs.
  It does not contradict Plan.MD § 3: "master data housekeeping" is IT
  admin's, and `equipment:edit` already has the same pair
  `("maint_engineer", "it_admin")`. A separate key (not reusing
  `equipment:edit`) is still right: different module, and S011 will evaluate
  it per site.
- **S011 note.** "It will change how `technicians:edit` is *evaluated*, not
  this step's data or rules" — true as far as this brief goes; one touchpoint
  worth a sentence is in BR2-04.

---

## BR2-01 — `minor` — The `kind` and `trade_id` API filters have no consumer in this step

**Problem.** § 6 gives `GET /technicians` two filters, `kind` and `trade_id`,
with four tests in § 8 (two happy, two 400s). Nothing in § 3 or § 5.5 uses
them: the masters panels filter **client-side** from the shared store
(`EquipmentTypesPanel`'s `classFilter` is a `computed` over
`equipmentTypes`, not a `?class_id=` call), and the lists are "well under 200
people" (§ 6) and unpaginated. § 1 puts "routing work by trade" out of scope,
and the phase-3 pick-list (tickets) will state its own needs.

**Why it matters.** CLAUDE-COMMON "Nothing beyond the agreed scope": filters,
their validation and tests that no screen calls are code the reviewer and the
coder must still get right, and phase 3 may want something else (e.g. active
only, by unit after S011). Small, but it is the one piece of the brief with no
stated use.

**Options.**
1. *(Recommended)* Drop both filters and their four tests from § 6 / § 8; keep
   `include_inactive` only, as `GET /trades` and `GET /equipment-classes`
   have. Add one line in § 1 "Out of scope": "server-side filters on the
   technicians list (phase 3 decides what the pick-list needs)". If the panel
   wants a Kind or Trade filter in its header, it filters the loaded rows as
   the types panel does.
2. Keep them and say in § 3 that `TechniciansPanel` uses them (a Kind select
   and a Trade select in the card header calling the API). Heavier than the
   sibling panels, and the panel then has two loading paths.
3. Keep them as a stated forward-looking item for phase 3. Only if the user
   wants it; then say so in § 7.

---

## BR2-02 — `nit` — The duplicate-login 409 should hint that the holder may be inactive

**Problem.** § 5.2: a deactivated technician keeps its login (good — it
cannot be handed to someone else by mistake), and the list hides inactive
rows by default. So the one realistic duplicate — "I deactivated Raja by
mistake and now I'm adding him again" — gets "Another technician already has
this login" with no visible holder. § 7 rightly rejects a pre-check naming
the holder (S001 § 5, the SELECT-then-INSERT race).

**Options.**
1. *(Recommended)* Keep the static message but make it actionable:
   "Another technician already has this login — it may be an inactive record;
   tick Show inactive". Still a `UNIQUE_KEY_ERRORS` constant; no query.
2. Leave as is. The editor will work it out; acceptable.

---

## BR2-03 — `nit` — Generalise `_check_grantable`, don't copy it

**Problem.** § 5.2 and § 5.4 say the trade check and lock take
"`_check_grantable`'s shape". The function as it is (`masters.py` 416–427)
is unit-specific: SQL on `units`, field `unit_ids`, messages "Unknown unit
N" / "Unit N is inactive and cannot be newly granted". A copy for trades is
the DRY violation CLAUDE-COMMON forbids ("never copy-paste code blocks").

**Options.**
1. *(Recommended)* Say in § 3 that `_check_grantable` gains parameters
   (table, field name, label) and `replace_user_units` calls the generalised
   form; the technician routes call it with `trades` / `trade_ids` /
   "Trade". One function, two callers, messages unchanged for units.
2. Accept a copy. Not recommended.

---

## BR2-04 — `nit` — Small points

1. **Where the Plan.MD pointer goes.** § 3 Docs: "the § 2 pointer for phase
   3" — "§ 2" is the *brief's* § 2; say which Plan.MD section receives it.
   The natural homes are Plan.MD § 4.2 "Who worked" (append "and the trade
   worked, pre-filled when the person has one trade") and the § 5
   `breakdown_labour` row ("technician, trade worked, time spent").
2. **S011 touchpoint.** `technicians.username` is a plain `VARCHAR(100)` like
   `user_units.username`. If S011 brings a Yantra-side users table, both
   columns become candidates for a foreign key; one line in "Related" or
   § 9.2 saying S010 keeps the string and leaves that to S011 stops S011's
   planner wondering whether S010 pre-empted it.
3. **"Nothing else locks `trades`"** (§ 5.4): `PUT /trades/<id>` will lock a
   trade row through `_lock_row`, as every master does. Single-table, so no
   cycle; reword to "no other module locks `trades` or `technician_trades`".
4. **Login column switch.** § 3 "login column only when rows carry
   `username`". Simpler and always in step with the backend: show it when
   `canEdit` (`technicians:edit`), since that is exactly when the field is
   returned. Either works; say which, so the coder doesn't sniff rows.
5. **Boundary test.** § 8 `validate_trade`: "blank, 51 characters, trimmed" —
   add "50 accepted", as `test_name_of_100_characters_is_fine` does for types.
6. **README index row** says "In review — r1"; the planner moves it to r2.
   Nothing to do in the brief.

---

## Checked and found consistent

- **Plan.MD.** § 3 roles: engineer "owns the masters", IT admin "master data
  housekeeping" — `technicians:edit = (engineer, it_admin)` with the manager
  inheriting fits both; § 4.2 "who worked … with time spent" and § 5
  `breakdown_labour` match the technician record; § 1 / § 2 "no maintenance
  cost" matches the out-of-scope list; § 8 phase 3 ("labour") is where the
  pick-list is used. No contradiction.
- **Maintenance-Philosophy.** § 3 training pillar "later (skill matrix)" —
  levels deferred correctly; § 11 roles match.
- **Plant-Facts § 4.** AMC vendors do PM and breakdown calls — the "contract
  record per firm" decision and the ISO 55001 § 7.2 departure describe that
  reality.
- **Migration v8** after v7 (S009, uncommitted in this tree); audit columns
  per v2's convention; `uq_technicians_username` with many `NULL`s works as
  `uq_units_warehouse` does; `ENUM('in_house','contract')` matches the
  `equipment.level` style. MariaDB 11.4 (dev compose) keeps
  `utf8mb4_general_ci` as the utf8mb4 default, so § 4's "unique ignoring
  case" holds without code, as S004 relies on.
- **`masters_core._validate`** gives absent-means-unchanged for free once
  `trade_ids` and `username` are field-table entries; `optional_text_parser`
  shows the `None` / `""` → `None` shape; `normalise_username` and
  `USERNAME_RE` exist; `parse_name` is 1–100 and matches `VARCHAR(100)`.
- **Shell helpers** are in place: `_lock_row`, `_int_filter`, `enum_arg`,
  `insert_row` / `update_row` (the latter's empty-`clean` no-op is why the
  § 5.4 stamp is needed), `UNIQUE_KEY_ERRORS` mapping via `_integrity_error`.
- **Locking.** PUT: technician row → trade rows; POST: trade rows only; two
  PUTs on different technicians sharing trades lock `id IN (…)` in index
  order, as `_check_grantable` already does, so no deadlock.
- **RBAC.** `has_perm` is the base's field-masking tool; `ROLE_INCLUDES`
  gives the manager the key; no `admin` in tuples; no `*` mixed;
  `require_perm` directly after `@route`.
- **Existing tests.** `test_rbac.py::test_role_matrix` (three rows) and
  `navigation.test.js` (three lists) are the only ones that change;
  `test_auth.py`'s exact lists are storekeeper and operator (untouched);
  `test_masters_api.py::TestPermissions` names its routes and is unaffected;
  no test enumerates `url_map`.
- **Frontend.** `useMasterForm.changeActive` sends `{active}` only (the
  reason for BR1-01); `useFormModal` takes `label` and `toBody`;
  `formSnapshot` serialises arrays by value, so the S007 guard works on
  `trade_ids`; `MastersView.sections` is ordered, so "after Equipment types,
  before Unit access" is well-defined; `stores/masters.js` fetches with
  `include_inactive=1`, which the held-inactive-trade checkboxes need;
  `resetMasters()` must gain `trades = null` ("cleared like the others").
- **S009 interaction.** S010 touches none of the S009 files except
  `local_db.py` (v8 after v7) and `conftest._TABLES`; no rebase conflict.
- **Standards, for the project owner** (all cited correctly in § 2):
  - *ISO 14224:2016 Table 8 "Maintenance data"* — the record of a
    maintenance event; its *maintenance resources* rows ask for man-hours
    **per discipline** (mechanical, electrical, instrument, other) and in
    total. Trades are Yantra's finer version of "discipline"; the brief is
    honest that a mapping is needed later for an ISO-style report.
  - *EN 15628:2014* — what a maintenance **technician specialist**, a
    **supervisor / engineer** and a **manager** must know and be able to do.
    A trade is the kind of work; the level is deferred — correctly separated.
  - *ISO 55001:2014 § 7.2* — know and evidence the competence of everyone
    doing work on the assets, contractors included; the brief states the
    departure (contract labour by firm, evidence stays in the AMC) with its
    reason. *§ 7.6* — documented information is controlled: who changed what,
    when; no hard delete.
  - *SMRP* — calls a trade a **craft** and reports labour by craft; the brief
    keeps the local word and says so once.
  - *TPM education and training* — the skill matrix; trades are its first
    column, levels later.
  - *ISO 27001:2022 A.5.34* — meet the law on personal data (DPDP Act 2023):
    keep the minimum, keep it only for its purpose (here, the audit trail);
    *A.5.15* — show information only to the roles that need it (the login to
    editors). *A.5.18* (access rights) is not engaged: the login is a link,
    not a grant, as § 5.2 says.
  - *EN 13306* defines maintenance types and terms; nothing in a people
    master engages it, so its absence from § 2 is right.
