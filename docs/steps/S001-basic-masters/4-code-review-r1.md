```
Step: S001 — Basic masters
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 14-10-2026
```

# S001 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There are 4 `minor` and 5 `nit` findings.

Scope: the whole S001 implementation, plus approved amendment A1 (default site;
deactivate and reactivate inside the edit dialog). I reviewed the uncommitted
working tree against `1-brief.md` (with § 10 A1) and `3-impl-report.md`
(including A1 and its "Decisions taken"). I left out the unrelated doc changes
(`docs/Plan.MD`, `Maintenance-Philosophy.md`, `Plant-Facts.md`, `.claude/*`).
The storekeeper role in `config_rbac.py` and `test_auth.py` is an earlier
uncommitted change, not S001, and the report says so.

## Test result (run by the reviewer)

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: 231 passed in 6.0 s.
  - Frontend (vitest): 3 files, 15 tests passed.
- `npx vite build` in `frontend/`: **built** in 1.65 s, with no errors and no warnings.

## Findings

### CR1-01 — minor — Unit-access replace is not serialised against a concurrent replace of the same user

`backend/masters.py:376-386` (`replace_user_units`)

**Problem.**
- `before = _user_units(cur, username)` is a plain `SELECT`, so it is a
  consistent (snapshot) read under REPEATABLE READ. It takes no lock on the
  user's `user_units` rows.
- `_check_grantable` locks only the **units** named in the new list.
- Two concurrent PUTs for the same user with disjoint lists therefore never
  conflict. Each computes its diff from a stale `held` set, and both commit.
- The brief's delete-then-insert would at least have taken locks on the user's
  key range: the DELETE is a locking read on current data.

Each request is still atomic on its own: everything happens in one
`transaction()`, and a 400 rolls back cleanly. With the requests run one after
the other, the outcome, the kept `granted_at`/`granted_by` and the log line are
all correct (impl decision 2 holds). The gap is isolation, not atomicity.

**Failure scenario.**
- User `jdoe` holds nothing. Two IT-admin tabs save `{unit_ids:[1]}` and
  `{unit_ids:[2]}` at the same moment.
- Both read `before = []`, and both insert. The end state is `{1, 2}`, which
  neither admin asked for.
- A "replace" with the same race can also revive a unit that the other request
  just revoked.
- The log lines then do not add up. Each `after` is read after commit and may
  include the other request's change, which is attributed to this actor.

Likelihood is low, since there is one IT admin today. But this is access
control (ISO 27001 A.5.18), where the trail should be exact.

**Suggested fix.**
- Make the first statement in the transaction
  `SELECT unit_id FROM user_units WHERE username = %s FOR UPDATE`.
- That next-key-locks the user's key range, so a second replace for the same
  user waits. Its snapshot is then taken after the lock, so `before` is current.
- Keep the diff (decision 2) as it is.
- For a brand-new user, two racing inserts can still deadlock (MariaDB 1213).
  That is acceptable at this scale, but see CR1-02 for how such an
  `OperationalError` surfaces.
- Add a one-line comment saying why the lock is there.

### CR1-02 — minor — DB outage after start-up gives 500, not 503 (pre-existing; first exercised by S001)

`backend/db_helpers.py:21-26` (`get_db`)

**Problem.**
- `get_db()` raises `DBUnavailable` (→ 503) only while `ensure_schema()` has not
  yet succeeded.
- Once `_schema_ready` is True it is cached for the life of the process. A
  later outage makes `get_pooled_db()` raise `pymysql.err.OperationalError`
  (2003 / 2013), which no handler maps, so the response is a 500.
- An `OperationalError` mid-request (lost connection, or a deadlock 1213 per
  CR1-01) is also a 500.
- The code moved verbatim from `app.py`, so this is not a regression. But S001
  adds the first routes that actually use `get_db()`.
- `.claude/CLAUDE.md` says "`get_db()` raises `DBUnavailable` → 503" when the DB
  is unreachable.

**Failure scenario.** The MariaDB container restarts in the day. Every masters
call returns HTTP 500, which the frontend shows as "INTERNAL SERVER ERROR",
instead of the 503 "Database unavailable" the app is meant to give.

`ping=1` on the pool does cover the overnight-idle case (CLAUDE-COMMON "Idle
connections"). This finding is about a DB that is actually down.

**Suggested fix.** This touches app-wide behaviour, so the user decides whether
it belongs in S001 or is deferred.
- In `get_db()`, wrap `get_pooled_db()` in
  `try/except pymysql.err.OperationalError as exc: raise DBUnavailable(describe_error(exc))`.
- Optionally add an app-level `errorhandler(pymysql.err.OperationalError)` that
  returns 503.

The teardown part of the question is fine; see "Checked and found consistent".

### CR1-03 — minor — "Add user" in Unit access silently overwrites an existing user's units

`frontend/src/views/masters/UserUnitsPanel.vue:78` (button), `:40-46` (`open`), `:55-60` (`save`)

**Problem.**
- "Add user" opens the dialog with an empty selection, whatever username is then
  typed.
- If the username already has access rows, Save PUTs the new ticks as the whole
  set. The backend correctly treats a PUT as a replace.
- Any inactive unit the user held is not even offered, because it is not in
  `selected`, so it is revoked too.

**Failure scenario.**
- `jdoe` holds `SMTW.FWMILL`, `SMTW.MCC1` and an inactive `SMTW.OLD`.
- IT admin clicks **Add user**, types `jdoe`, ticks `SMTW.MCC2` and saves.
- `jdoe` now holds only `SMTW.MCC2`. Three grants are gone, with no warning.
- The log line records the change, but nobody meant it.

**Suggested fix.**
- In `save()` (or on blur of the username field), if `isNewUser` and the
  normalised name is already in `items`, do not save. Either switch to that
  user's edit dialog with their held units preselected, or show "This user
  already has unit access; edit them from the list".
- This is frontend-only. The API semantics stay as in the brief.

### CR1-04 — minor — Missing tests for the error mapping's failure branches and for 503 on a masters route

`backend/tests/test_masters_api.py`

**Problem.** The brief's § 8 list is covered, but the tests stop at the happy
path of the error mapping, and three failure modes in the review checklist have
no test:
1. A **non-1062** `IntegrityError` (for example 1452 FK, or 1048 NOT NULL) must
   **not** become a 409. The handler re-raises it (`masters.py:81-82`), so it is
   a 500 and is logged. That is the right behaviour, but no test pins it.
2. A 1062 on an **unmapped key** (`PRIMARY` of `user_units`) must give the
   generic 409 with no `field`.
3. A masters route must return **503** when `get_db()` raises `DBUnavailable`.

**Failure scenario.** A later change replaces the `raise exc` with a catch-all
409, or drops the generic fallback. Nothing goes red, and an FK bug starts
showing as "Conflicts with an existing record".

**Suggested fix.** Add three small API tests:
- monkeypatch a route helper (for example `masters._insert`) to raise
  `pymysql.err.IntegrityError(1452, "...")` and assert 500, or
  `pytest.raises` under `PROPAGATE_EXCEPTIONS`;
- raise `IntegrityError(1062, "Duplicate entry 'x' for key 'PRIMARY'")` and
  assert 409 with no `field`;
- monkeypatch `db_helpers.ensure_schema` to return `"down"` and assert
  `GET /api/masters/sites` gives 503.

### CR1-05 — nit — Misleading message when deactivating a non-default site while ticking Default

`backend/masters.py:228-232`

**Problem.** `PUT {active:false, is_default:true}` on a site that is **not** the
default makes `will_be_default` True. It returns "This is the default site;
untick Default first", but the site is not the default.

**Failure scenario.** This is API-only: the UI never sends both, because
`changeActive` sends `{active}` alone. A client that does gets a confusing
message.

**Suggested fix.** Branch on `site["is_default"]` for the "This is the default
site" message. Let the combined request fall through to the existing "An
inactive site cannot be the default" check (field `is_default`).

### CR1-06 — nit — The duplicate-key regex can match inside the duplicated value

`backend/masters.py:37`, `:83`

**Problem.**
- `re.search(r"for key '(?:\w+\.)?(\w+)'")` takes the **first** match.
- MariaDB's message is `Duplicate entry '<value>' for key '<key>'`, and
  `<value>` can be user text: `oneerp_warehouse` is free text up to 140
  characters.

**Failure scenario.**
- A warehouse named `x' for key 'uq_sites_code` that collides would be reported
  as a site-code duplicate on `field: code`.
- The effect is cosmetic only. It is still a correct 409, and there is no
  security impact.

**Suggested fix.** Anchor the pattern to the end of the message:
`r"for key '(?:\w+\.)?(\w+)'$"`.

### CR1-07 — nit — A held inactive unit vanishes from the dialog once unticked

`frontend/src/views/masters/UserUnitsPanel.vue:26-28`

**Problem.** `choices` keeps inactive units only while
`selected.value.has(u.id)`. Unticking one by mistake removes it from the list,
and the only way back is Cancel and reopen. The impl report says these units are
"still tickable so they can be revoked". They are, but only one way.

**Suggested fix.** Build the set of held inactive ids once, in `open()` from
`heldUnits`, and filter `choices` on that set rather than on `selected`.

### CR1-08 — nit — `test_the_database_allows_only_one_default` depends on leftover rows and catches `Exception`

`backend/tests/test_masters_api.py:571-583`

**Problem.**
- The test picks two existing sites with `is_default IS NULL LIMIT 2`. With
  fewer than two such rows, for example when run alone with `-k` on a freshly
  truncated DB, the unpacking `first, second = ...` fails.
- It also runs `UPDATE sites SET is_default = NULL` on the whole table, and
  `pytest.raises(Exception, ...)` is broader than needed.

**Suggested fix.**
- Take `make_site` twice to get two fresh sites.
- Clear the default only where `is_default = 1`.
- Assert `pymysql.err.IntegrityError`.

### CR1-09 — nit — Migration v3 DDL is not defensive

`backend/local_db.py:100-101`

**Problem.**
- `SMTW-WebApp-Base.md` § Local DB Migration Pattern says to use
  `ADD COLUMN IF NOT EXISTS` for defensive migrations.
- v3 runs two DDL statements, which autocommit one by one. If the process dies
  between them, the first is applied and `db_version` has no v3 row. Every retry
  then fails on "Duplicate column name", so the app is stuck at 503.

**Failure scenario.** This is very unlikely: it needs a crash in the
milliseconds between the two ALTERs on the production deploy.

**Suggested fix.** Use
`ALTER TABLE sites ADD COLUMN IF NOT EXISTS is_default TINYINT(1) NULL AFTER active`
and `ALTER TABLE sites ADD UNIQUE INDEX IF NOT EXISTS uq_sites_default (is_default)`.

v3 is unreleased but already applied to the dev and test DBs. The edit is
textually a change to an applied migration, though it is a no-op on those DBs.
CLAUDE-COMMON says applied migrations are never edited, so **the user decides**
whether to change v3 now, before first release, or to leave it.

## Answers to the orchestrator's focus points

1. **Unit access saved as a diff (impl decision 2).**
   - It is **atomic**: one `transaction()`, and every 400 is raised before any
     write, with a rollback in any case.
   - It **preserves `granted_at`/`granted_by`**, and a test covers this.
   - `unit_ids` are de-duplicated in `validate_unit_ids`, so a repeated id
     cannot hit the PK.
   - The log line is right in sequential use:
     - `before` is read inside the transaction before any change;
     - `after` is read after commit;
     - the line is logged only after commit and only when the id set changed;
     - inactive units are included in both lists.
   - It is not serialised against a concurrent replace of the same user, and
     the log can then misattribute: **CR1-01**.
2. **IntegrityError 1062 → 409.** Each named key maps to the right field and
   message, and five of the six are tested through the API:
   - `uq_sites_code` → `code`, tested;
   - `uq_units_site_code` → `code`, tested, including a unit **move** that
     collides, which also maps to `code`;
   - `uq_units_warehouse` → `oneerp_warehouse`, tested;
   - `uq_equipment_classes_code` → `code`, tested;
   - `uq_sites_default` → `is_default`, "…at the same time…", tested by
     stubbing the clear step;
   - the `user_units` PK → `PRIMARY`, not in the map, so the generic 409 "Conflicts
     with an existing record; reload and try again" with no `field`. That is the
     sane answer for the only way to reach it, a race.

   Both the `'uq_x'` and the `'table.uq_x'` message forms are handled. A
   non-1062 `IntegrityError` is **re-raised** from the blueprint handler, so
   Flask's `handle_exception` logs it and returns 500. It is not swallowed and
   not turned into a 409. The transaction has already rolled back by then,
   because `transaction()` exits before the handler runs. Untested branches:
   CR1-04. Regex nit: CR1-06.
3. **`get_db()` in `db_helpers.py`.**
   - It still raises `DBUnavailable` when the schema is not ready, and the
     app-level handler turns that into 503. That covers both a DB that is
     unreachable and one that is not created, since `init_db` fails on connect.
   - The teardown is registered with `app.teardown_appcontext(close_db)`, which
     runs on every request, including after an unhandled exception.
   - `transaction()` rolls back on any `BaseException` before re-raising.
   - DBUtils `PooledDB` (default `reset=True`) also rolls back when the
     connection is returned. A connection cannot go back to the pool mid-transaction.
   - Gap: an outage after the schema is ready gives 500, not 503 (**CR1-02**,
     pre-existing).
4. **Frozen codes and concurrency.**
   - **Site code.** `_lock_row(sites)` is `FOR UPDATE`, then the units are
     counted. A concurrent unit create or move into the site locks the same site
     row (`_lock_site_for_unit`), and the FK check needs it too, so it waits.
   - **Unit code and `site_id`.** `_lock_row(units)`, then `user_units` is
     counted. A concurrent grant locks the unit row in `_check_grantable` and
     the FK needs it, so it waits.
   - The counts are consistent reads. InnoDB creates the read view at the
     first consistent read, which here is after the parent lock is held, so a
     child committed just before is visible. Lock order is always
     child → parent or parent-only, so there is no cycle.
   - **Site deactivation and unit reactivation/create** both serialise on the
     site row. I checked both orders and each gives the right 409.
   - **Default move (A1 decision 3).** `UPDATE sites SET is_default=NULL … WHERE
     is_default=1 AND id<>B` is a locking read on current data: it X-locks A's
     row and index entry while clearing it.
     - Two racing "make default" saves serialise on that lock, or the second hits
       `uq_sites_default` and gets the mapped 409.
     - A concurrent "deactivate A" locks A first and re-reads `is_default` under
       the lock, so it sees the cleared value.
     - The result equals the brief's "lock A then clear". The **database still
       guarantees one default** through `uq_sites_default` on a 1/NULL column.
       The migration and `_as_column_value` keep 0 out, and a test asserts the
       NULL.
     - The departure is reported, and I find it sound.
5. **RBAC.** Every route has the brief's key, and `require_perm` is on all 11
   routes:

   | Route | Key |
   |---|---|
   | `GET /sites`, `GET /units`, `GET /equipment-classes` | `masters:read` |
   | `POST/PUT /sites`, `POST/PUT /units`, `PUT /user-units/<u>` | `masters:edit` |
   | `POST/PUT /equipment-classes` | `equipment:edit` |
   | `GET /user-units` | `masters:read_senior` |

   - The actor is always `g.user["username"]` (`_actor()`). A body
     `created_by` is ignored, and a test covers it.
   - `config_rbac.py` matches § 3: `masters:edit=("it_admin",)`,
     `masters:read_senior=("it_admin",)`,
     `equipment:edit=("maint_engineer","it_admin")`. The manager inherits it.
   - `admin` is in no tuple.

## Checked and found consistent

- **Migration v2.**
  - The tables, column types and audit columns match § 4.
  - The unique indexes are named as in § 4.
  - The FKs are in place and the tables are InnoDB/utf8mb4.
  - Each table is a separate `CREATE TABLE IF NOT EXISTS`.
  - There is no `ON UPDATE CURRENT_TIMESTAMP`.
  - Migrations are append-only: v1 is untouched, and v3 is appended rather than
    v2 edited.
- **Pure core.**
  - `masters_core.py` has no DB, no Flask and no clock.
  - The code regexes match § 5 exactly: site `^[A-Z][A-Z0-9-]{1,19}$`, unit
    `^[A-Z0-9][A-Z0-9-]{1,19}$`, class `^[A-Z]{2,4}$`, username per § 5.
  - Codes are stripped and upper-cased.
  - Names that are only whitespace are rejected.
  - `oneerp_warehouse` is stripped, not upper-cased, and empty becomes None.
  - Booleans are rejected as ids.
  - `is_default`/`active` accept true, false, 1 and 0 only. `"1"` is rejected,
    and a test covers it.
  - The pure tests cover the § 8 boundaries.
- **SQL safety.**
  - Every value is passed as a `%s` parameter.
  - The f-strings interpolate only code constants: table names, the column names
    of the validated `clean` dict (keys come from the `_FIELDS` maps, never the
    client) and placeholder lists.
- **Activation rules.**
  - A site with active units is refused deactivation (409 `active`), and one
    with only inactive units may deactivate.
  - A unit cannot be created, moved or reactivated under an inactive site (409
    `site_id`).
  - An unknown `site_id` is a 400.
- **A1 rules.**
  - Default on an inactive site → 409 `is_default`, on POST as well.
  - Deactivating the default site → 409 `active` with the brief's wording.
  - Unticking leaves no default.
  - A move audits both rows, and a test covers it.
  - `is_default` is a boolean in every site response (`_SITE_SELECT` and
    `_site_out`).
  - An engineer gets 403.
- **API shapes.**
  - Lists are `{items, total}`, ordered by code, and filtered by
    `include_inactive=1`. `GET /units` without `site_id` returns all units, and
    a bad `site_id` is a 400.
  - Unit rows carry `site_code` and `full_code`.
  - POST returns 201 and PUT returns 200 with the record. An unknown id is a 404.
  - Errors are `{error, field?}`, with the first validation error only.
  - The `/user-units` shapes match § 6. An emptied set gives `units: []` and
    removes the user from the list.
- **Audit columns.** `updated_*` stay NULL until the first edit, then both are
  set in the same `UPDATE` with `NOW()`. The IST session time zone is unchanged.
- **Decisions in the impl report.** I checked all ten base decisions and the
  five A1 decisions against the diff:
  - `FormModal`, `useMasterForm` and `ActiveToggle` are reported (DRY), as are
    the diff save, the PUT with no fields, and the frontend lists that include
    inactive records.
  - The Add-unit preselection takes the filter first, then the default
    (A1 decision 2, consistent with A1.5.1).
  - Nothing unreported was found in the S001 files. The only extra is the removal
    of an unused `Decimal` import in `db_helpers.py`, which is harmless.
- **Frontend.**
  - `api.js` copies `field`.
  - A refusal naming a form field shows beside it, and any other refusal shows
    in the modal (`modalError`).
  - The edit buttons are gated on `masters:edit`, or `equipment:edit` for
    classes.
  - The Unit access section is gated on `masters:read_senior` in the toolbar
    and in `MastersView`'s fallback.
  - `ModuleToolbar` is data-driven, hides itself with one section or fewer, and
    reuses `canSeeNavItem`.
  - Every save calls `resetMasters()`.
  - The A1 toggle sends `PUT {active}` alone, asks inline before deactivating
    and closes and reloads on success. The create dialog has no toggle.
  - `defaultSiteId()` returns only an **active** default.
- **Tests.**
  - The § 8 API, RBAC and hygiene list is covered:
    - the session-scoped delete runs in FK order, after `ensure_schema`;
    - the `uniq` fixture supplies codes and warehouses;
    - the `caplog` log-line test asserts exact text, and an unchanged set is
      not logged;
    - atomicity on an unknown or inactive unit is covered.
  - `test_modules.py` dropped `TestMasters`, and the tests were taken over.
  - `test_auth.py` asserts `equipment:edit` for the engineer.
  - `navigation.test.js` matches `config_rbac`.
- **Not deprecated:** no deprecated API is used, and no exception is swallowed.
  Comments explain why.

## Still needs the user's manual browser check

These are from § 8 and A1.4. They are not covered by tests, and the coder tried
them only partly.

1. **Each panel (Sites, Units, Equipment classes):** create, edit, and an inline
   field error (for example a duplicate code shown beside Code); the "cannot be
   changed once in use" hint; a 409 code-in-use shown beside Code.
2. **The Deactivate and Reactivate buttons in each of the three edit dialogs:**
   - the inline "Deactivate X? Yes / No" row, including **No**;
   - a **successful** deactivate and reactivate (the dialog closes and the list
     reloads);
   - a refusal shown inside the dialog: a site with active units, the default
     site, and a unit reactivated under an inactive site.
3. **Default site:** the badge; moving the default from A to B, so the badge
   moves; and Add-unit preselecting the default when the filter is "All sites"
   and the filtered site otherwise.
4. **Unit access:**
   - inactive units shown greyed in the list and in the dialog;
   - an inactive held unit revoked by unticking it;
   - a new user added by typing a username;
   - the CR1-03 overwrite, to confirm the behaviour before or after the fix.
5. **Role hiding:** with `DEV_STUB_ROLE=maint_engineer`, the Sites and Units edit
   buttons and the Unit access section are hidden, and class editing works. With
   `maint_operator`, every edit button is hidden.
6. **Acceptance (§ 8):** enter the six Plant-Facts § 2 sites, the units
   `SMTW.FWMILL`, `SMTW.MCC1` and `SMTW.MCC2`, and a user's grant as IT admin.
   Then add `VBM` as an engineer.
