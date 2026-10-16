```
Step: S010 — Technicians and trades
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 16-10-2026
```

# S010 — Brief review, round 1

**Verdict: two `major` findings open (BR1-01, BR1-02); no `blocker`.**

Reviewed against the brief as it stands, `docs/Plan.MD` § 3 / § 4.2 / § 5,
`docs/Maintenance-Philosophy.md` § 2–3 and § 11, `docs/Plant-Facts.md` § 4–5,
the S001 / S004 / S007 / S009 briefs, and the current working tree:
`backend/masters.py`, `masters_core.py`, `config_rbac.py`, `api_common.py`,
`db_helpers.py`, `local_db.py` (v1–v7, S009's v7 uncommitted), `tests/conftest.py`,
`tests/test_rbac.py`, `tests/test_masters_core.py`, `tests/test_masters_api.py`,
`tests/test_auth.py`; `frontend/src/views/MastersView.vue`, the masters panels,
`useMasterForm.js`, `useFormModal.js`, `FormModal.vue`, `ActiveToggle.vue`,
`stores/masters.js`, `stores/navigation.js`, `tests/navigation.test.js`; and
`.claude/SMTW-WebApp-Base.md` § RBAC, § Migrations, § API responses, § Testing,
§ Form / Modal.

The four user decisions at the top of the brief are taken as given. Findings
BR1-02 and BR1-03 flag consequences of them, not the decisions themselves.

---

## BR1-01 — `major` — A `PUT` without `trade_ids` (or without `username`) has no stated meaning; the Deactivate button would hit the "at least one trade" rule

**Problem.** § 5.2 says trades are "at least one (400 field `trade_ids`)" and
§ 6 gives the `PUT` body as `{name, kind, username, trade_ids, active}`. The
brief never says what a `PUT` that *omits* `trade_ids` or `username` means.
That matters because the masters dialogs' Deactivate / Reactivate button
(`useMasterForm.changeActive`) sends exactly `PUT {active}` and nothing else
— the S001 A1.2 pattern the brief adopts for `TechniciansPanel`. Read
literally, that request has no `trade_ids`, so it is "no trades → 400", and
the brief's own manual check ("deactivate … technician") cannot pass. The
same ambiguity applies to `username`: is an absent key "unchanged", and is
`null` / `""` "clear it"? (`optional_text_parser` already treats `None` and
`""` as `None`; `validate_username("")` returns an error, so the two cannot
simply be chained — the empty case has to be handled before the regex.)

**Why it matters.** This is the rule the coder would otherwise decide alone,
and whichever way they choose, either the Deactivate button breaks or the
"at least one trade" rule is silently weakened.

**Options.**
1. *(Recommended)* State the update semantics the way `masters_core._validate`
   already works for every other master: **an absent field means unchanged**.
   Make `trade_ids` and `username` fields of `validate_technician`'s field
   table (parsers raising `ValueError`), so `creating=True` requires `name`,
   `kind` and `trade_ids`, and `creating=False` leaves out whatever is absent.
   The shell then replaces the trade set only when `trade_ids` is in `clean`.
   For `username`: `None` or empty → `None` (clear), else
   `normalise_username` + the `USERNAME_RE` check; absent → unchanged. Add the
   pure tests: `trade_ids` absent on update is accepted; `[]` on create or
   update → error `trade_ids`; and an API test that `PUT {active: 0}` on a
   technician with two trades returns 200 with both trades intact.
2. Keep `validate_trade_ids` as a separate call like `replace_user_units` and
   make the dialog always send the full body (including on deactivate). That
   departs from `useMasterForm` and loses the shared Deactivate flow. Not
   recommended.

---

## BR1-02 — `major` — Every role can read every technician's Keycloak login; S001 put usernames behind `masters:read_senior`

**Problem.** § 6: `GET /technicians` is `masters:read` (`*`) and each item
carries `username`. So operators, storekeepers and technicians can list every
maintenance person's login. S001 decided the opposite for the only other
place usernames appear: `GET /user-units` needs `masters:read_senior` (IT
admin), "the read hierarchy's 'sensitive' level" (S001 § 3, BR1-07). The brief
cites ISO 27001 A.5.34 for keeping only what the work needs, but then shows
the one field that *is* an identifier to everyone. Plan.MD § 3 also makes
operator usernames employee numbers (`E1042`), so the list doubles as a
staff-number list. Nothing in phase 3–4 needs the login in a pick-list: a
ticket picks a technician by `id`, name, kind and trades; the login is used
server-side to answer "is this ticket mine".

This is the planner's choice ("visible to everyone", § 1.3), not one of the
four user decisions.

**Why it matters.** Data minimisation (A.5.34) and consistency with S001's
read hierarchy; and a complete login list is the first half of a credential
attack. ISO 27001 A.5.15 (access control) asks that access to information be
limited to what the role needs.

**Options.**
1. *(Recommended)* Keep the list under `masters:read` but **return `username`
   only to holders of `technicians:edit`** (inline `has_perm`, the base's
   "mask individual fields" pattern) — the people who maintain the link are
   the people who see it. The panel hides the Login column when the field is
   absent. Add an API test: operator's list rows have no `username` key;
   engineer's do. State it in § 2 (A.5.34, A.5.15) and § 7.
2. Gate the login behind `masters:read_senior` (IT admin + engineers added
   now). Heavier than needed; engineers already hold `technicians:edit`.
3. Accept visibility to all roles and say so as a deliberate departure in § 2.
   Only if the user wants the shop floor to see logins.

---

## BR1-03 — `minor` — "Trades per person let later steps add up labour by trade without asking again" is over-stated once a person has several trades

**Problem.** § 2 (ISO 14224) and § 7 ("Several trades per technician … ISO
14224 counts hours per discipline") claim that recording trades now is enough
to sum man-hours by discipline later. With *several* trades per person that
no longer follows: three hours by a fitter-electrician cannot be split by
trade from the person record alone. Phase 3's `breakdown_labour` (Plan § 5)
will need a `trade_id` per labour row — pre-filled when the person has one
trade, asked when they have more. Nothing to build now; the brief should not
promise what the model cannot deliver.

**Why it matters.** The project owner is learning the standard; the brief is
where the model's limits should be honest. It is also a consequence of the
"several trades" decision worth seeing now.

**Options.**
1. *(Recommended)* Reword § 2 and § 7: trades per person are the *pick-list*
   for the labour row's trade; the phase-3 labour row carries the trade worked
   (defaulting to the only trade when there is one). Add it as a pointer for
   the phase-3 brief, like S001's "pointer for S003".
2. Restrict each technician to one trade. Rejected by the user; not proposed.

---

## BR1-04 — `minor` — Shell details the coder would have to decide

Each of these is small, but together they are the body of `masters.py`'s new
routes; the brief should settle them as S001/S004 did.

1. **Locking.** `PUT /technicians/<id>` should lock the technician row first
   (`_lock_row`, as every master), then `SELECT … FOR UPDATE` the trade rows
   (`_check_grantable`'s shape). Lock order technician → trades; nothing else
   locks `trades` or `technician_trades`, so no cycle with `equipment.py` or
   `documents.py`. Say so, and that `POST` locks the trade rows only.
2. **`updated_at/by` when only the trades change.** `update_row` does nothing
   with an empty `clean`, so a `PUT {trade_ids: […]}` that changes the set
   would leave the technician's audit columns untouched. State that the
   technician row is stamped whenever its trade set changes (one
   `UPDATE … SET updated_at = NOW(), updated_by = %s`), so "who/when on every
   change" (§ 2, ISO 55001) holds. A removed trade otherwise leaves no trace at
   all; the stamp is the minimum.
3. **The duplicate-login 409.** "This login belongs to <name>" needs a
   `SELECT` before the write; S001 § 5 says duplicates are caught by the
   UNIQUE index, "a pre-check with a SELECT is not relied on, because a SELECT
   followed by an INSERT is a race". Choose: *(recommended)* a static message
   through `UNIQUE_KEY_ERRORS` (`uq_technicians_username` → field `username`,
   "Another technician already has this login"); or the friendly pre-check
   *plus* the index mapping as the backstop (two messages for one rule). Either
   way, add the `UNIQUE_KEY_ERRORS` entries for `uq_technicians_username` and
   `uq_trades_name` to § 3.
4. **"Unique ignoring case" for trade names.** Say where it comes from: the
   table's default collation (`utf8mb4_general_ci`) makes `uq_trades_name`
   case-insensitive, as S004 § 4 noted for types. No code needed; the brief
   should not leave the coder adding a `LOWER()` pre-check.
5. **Filters.** `kind` through `enum_arg("kind", ("in_house", "contract"))`
   → 400 on anything else; `trade_id` through `_int_filter` → 400 on a
   non-number (both exist in `api_common` / `masters.py`). Add the two 400
   cases to § 8.
6. **Trades inside each item.** Order (by name) and whether inactive trades are
   included (they must be, since a held inactive trade is "shown as inactive").
   One query: `… FROM technician_trades tt JOIN trades t … WHERE tt.technician_id IN (…)`.
7. **`kind` on update.** Nothing says whether `kind` may change after create.
   It should (a firm record made as "in-house" by mistake); say so, and that
   the name is kept as entered (the user re-labels it).

---

## BR1-05 — `minor` — Frontend details missing from § 3

1. **Held inactive trades in the dialog.** § 5.2 lets an inactive trade be
   *kept*; the dialog must therefore offer the active trades **plus the
   inactive ones the technician already holds**, fixed when the dialog opens
   (`UserUnitsPanel`'s `heldInactiveIds`), greyed and marked "(inactive)".
   Otherwise an engineer who opens the dialog and saves would silently drop a
   held inactive trade — or the save would fail. Add it, and a manual check.
2. **`label` for `ActiveToggle`.** `useFormModal`'s default label is
   `record.full_code ?? record.code`; trades and technicians have neither, so
   the deactivate confirmation would read "Deactivate **undefined**?". Pass
   `label: (r) => r.name` for both panels (S004 did this for types).
3. **Form shape.** `blank`/`fromRecord` for the technician: `{name, kind,
   username: "", trade_ids: [], active}`; `toBody` sends `username` as `""`
   → `null`. `formSnapshot` handles arrays, so the S007 guard works; a
   checkbox that toggles an id in `form.trade_ids` is enough.
4. **Name label follows kind** ("Name" / "Contractor firm") — stated in § 5.2,
   fine; add the kind as radio buttons or a select on create *and* edit (see
   BR1-04.7), and a Kind badge in the table.
5. **Where the sections go.** `MastersView.sections` is ordered; say "after
   Equipment types, before Unit access" (or at the end). Also: `TradesPanel`'s
   model is `EquipmentClassesPanel` minus the code field, not
   `EquipmentTypesPanel` (which has the class filter and the documents view).
6. **The store comment.** § 3: "`ensureTrades()` … (the ticket and PM steps
   pick from it)". Tickets pick *technicians*, not trades. Either drop the
   parenthesis or add `ensureTechnicians()` now (the technicians panel could
   use it like the types panel uses `ensureEquipmentTypes()`, instead of its
   own `apiGet`). Either is fine; say which.
7. **Login column.** If BR1-02 option 1 is taken, the column is shown only when
   rows carry `username`.

---

## BR1-06 — `minor` — Standards: four corrections and two departures to state

For the project owner, in plain terms, with what to change:

1. **ISO 14224 Table 8.** In ISO 14224:2016 Table 8 is **"Maintenance data"**;
   "maintenance resources" is a *row group* inside it, with the rows
   "maintenance man-hours, per discipline (mechanical, electrical, instrument,
   others)" and "maintenance man-hours, total". The brief's disciplines are
   right; the table title is not. Also worth one sentence: the standard's
   discipline split is four-way and coarse; Yantra's trades (tool maker,
   welder, …) are finer, so a report "per ISO 14224 discipline" would need a
   trade → discipline mapping later. Not now.
2. **EN 15628:2014** (Maintenance — Qualification of maintenance personnel)
   defines **three levels**: *maintenance technician specialist*,
   *maintenance supervisor / maintenance engineer*, and *maintenance manager*,
   each with required knowledge, skills and competences. The brief's "a
   maintenance technician, a specialist and a supervisor" mixes the first two
   levels. Plain terms: the standard says what a person at each level must
   know and be able to do; a trade is the kind of work, not the level.
3. **ISO 55001 clause numbers (2014 edition, the project's convention).**
   § 7.5 is *information requirements*; **§ 7.6 is documented information**
   (7.6.3 control of it). The last § 2 bullet should cite § 7.6, as S001 does
   ("§ 7.5–7.6"). § 7.2 (competence) is cited correctly: the organisation
   must know the competence of "persons doing work under its control" and
   keep evidence.
4. **Departure to state under ISO 55001 § 7.2 / § 8.3.** "Persons doing work
   under its control" includes contractors' people. Recording contract labour
   by firm (user decision) means Yantra holds **no competence evidence per
   contract person**; that evidence lives in the AMC / contract (Plant-Facts
   § 4: important equipment is under AMC). Say so in § 2 as a deliberate
   departure, with the reason (A.5.34, no personal data on contract workers).
5. **ISO 27001 A.5.34 — retention.** A.5.34 is about identifying and meeting
   the legal requirements on PII (in India, the Digital Personal Data
   Protection Act 2023). The brief covers *minimisation*; add one line on
   *retention*: a person's name is kept after they leave because tickets and
   jobs cite it (the audit trail is the lawful purpose), and nothing else about
   them is kept. That is the justification for "deactivated, never deleted".
6. **SMRP.** Fine as written ("craft", labour reported by craft). If a metric
   is wanted: SMRP Best Practice 5.5.x (work management) reports craft
   utilisation and wrench time by craft. Optional.

---

## BR1-07 — `nit` — Tests and fixtures

- `conftest._TABLES` order: `technician_trades`, `technicians`, `trades`
  (child first; FK checks are off there anyway, but the order documents it).
- Fixtures `make_trade` / `make_technician` beside `make_type`, and a
  `uniq.trade_name()` so trade names never collide across tests (case-
  insensitive uniqueness makes collisions likelier).
- `test_rbac.py::test_role_matrix` is an **exact set** per role: the engineer
  and manager rows gain `technicians:edit` (the brief names the file; say the
  rows). `test_auth.py` is unaffected (its exact lists are storekeeper and
  operator).
- `navigation.test.js`: `ENGINEER` and `MANAGER` gain the key; nothing asserts
  on it, but the comment there promises parity with `test_rbac`.
- Add: `PUT {active: 0}` keeps the trades (BR1-01); operator's rows have no
  `username` (BR1-02, if taken); bad `kind` / `trade_id` filter → 400
  (BR1-04.5); trades-only change stamps `updated_by` (BR1-04.2).

---

## BR1-08 — `nit` — Small points

- **Two records for one firm.** Names are not unique (user), so "ABC Engg" and
  "ABC Engineering" can both exist. Accept it (a merge would be over-
  engineering), but say it in § 7's "Names not unique" row so it is a known
  limit, not a surprise.
- **§ 6 `GET /technicians` order** `name, id`: fine; say the same for trades
  inside an item (BR1-04.6).
- **§ 1.3 "visible to everyone"** reads as a decision; it follows from
  `masters:read` = `*`. Reword after BR1-02.
- **Status header.** The brief says `In review`; the README index row says
  "In review — r1". Consistent; nothing to do.

---

## Checked and found consistent

- **Plan.MD.** § 3 roles (engineer "owns the masters", IT admin "not
  maintenance work") support `technicians:edit` = engineer; § 4.2 "who worked:
  one or more technicians per ticket, with time spent" and § 5
  `breakdown_labour` match the technician record; § 1 "no maintenance cost"
  matches the out-of-scope list. No contradiction.
- **Maintenance-Philosophy § 3.** Training & education pillar "later (skill
  matrix, one-point lessons)" — the brief defers levels correctly.
- **Migration v8** after S009's v7 (verified in the working tree); the
  `CREATE TABLE IF NOT EXISTS` statements are re-runnable; the audit columns
  match v2's convention; `uq_technicians_username` with many NULLs works as
  `uq_units_warehouse` does.
- **`validate_username`** accepts employee-number logins (`E1042` → `e1042`),
  matching Plan § 3's username scheme.
- **`_check_grantable` / `replace_user_units`** exist as the brief describes
  (diff, keep `granted_at/by`); `_int_filter`, `enum_arg`, `_lock_row`,
  `insert_row`/`update_row` are in place for the shell.
- **RBAC.** `ROLE_INCLUDES` gives the manager `technicians:edit` through the
  ladder; no `admin` in tuples; no `*` mixed; `require_perm` directly after
  `@route` per the base.
- **No pagination** on the two lists: consistent with S001's stated departure.
- **S007 guard.** `FormModal` + `useMasterForm` give `dirty` for free to both
  new dialogs; arrays snapshot correctly.
- **S009 interaction.** S010 adds panels and `MastersView` sections only; it
  doesn't touch `EquipmentClassesPanel` / `EquipmentTypesPanel`, so no rebase
  conflict beyond `local_db.py` (v8 after v7) and `conftest._TABLES`.
- **Existing tests.** Only `test_rbac.py::test_role_matrix` changes; the
  `test_masters_api.py::TestPermissions` cases name their routes and are
  unaffected.
