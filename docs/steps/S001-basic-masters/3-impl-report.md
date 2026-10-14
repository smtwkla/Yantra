```
Step: S001 — Basic masters
Doc: impl-report
Author: Coder (Sonnet 5.5)
Date: 13-10-2026
```

# S001 — Implementation report

Implemented per the approved brief (`1-brief.md`, approved 13-10-2026). Nothing is committed; the working tree holds the change for review.

Test result: `tooling/run-tests.bat` is green: 211 backend tests and 15 frontend tests. `vite build` completes with no errors. I also ran the UI once in a browser against the test DB (see "Not done / to verify").

## 1. What was built

- **Four masters** with list, create and edit, plus deactivate and reactivate: sites, units, equipment classes, and users' unit access. No master record is hard-deleted.
- **Rules from § 5 of the brief:**
  - code formats, with codes stripped and upper-cased;
  - codes frozen once in use (a site's code once it has any unit; a unit's code and `site_id` once it has any access row);
  - a site with active units cannot be deactivated;
  - a unit cannot be created or reactivated under an inactive site;
  - duplicates are caught by the database and returned as 409 with a `field`;
  - `full_code` (`SITE.UNIT`) is derived, not stored;
  - `oneerp_warehouse` is unique, stripped, and not upper-cased.
- **Unit access** is replaced per user in one transaction. Only active units can be newly granted; a held inactive unit may stay. Each real change writes one `user_units changed: actor=… user=… before=[…] after=[…]` log line.
- **RBAC:** `masters:edit` is now IT admin only. New keys: `masters:read_senior` (IT admin) and `equipment:edit` (engineer, IT admin; the manager inherits it).
- **Masters page** with a reusable level-2 toolbar (Sites | Units | Equipment classes | Unit access) and one panel per section. The Unit access section needs `masters:read_senior`.

## 2. How it works

**Backend (thin shell over a pure core).**
- `masters_core.py` has no DB or Flask. Each validator returns `(clean, errors)` with `errors` as `{field, message}`. On create the required fields must be present; on update an absent field means "unchanged" and is left out of `clean`. The routes return only the first error.
- `masters.py` raises a small `ApiError(message, status, field)`, which a blueprint error handler turns into `{error, field?}`. A second handler turns `IntegrityError` 1062 into 409. It reads the named unique key from the message (both the `'uq_x'` and the `'table.uq_x'` forms) and maps it to a field and message: `uq_units_warehouse` gives `oneerp_warehouse`, and so on.
- Anything that checks and then writes runs in `transaction(conn)`.
  - The parent row is locked first with `SELECT … FOR UPDATE`, then references are counted. A concurrent child insert waits on the parent's lock through the foreign key.
  - A unit's create, move and reactivate also lock the target site row. That serialises them against a site deactivation.
- `GET` lists are not paginated, are ordered by code, and hide inactive records unless `?include_inactive=1`.
- `get_db()` and the teardown moved from `app.py` to `db_helpers.py`. `app.py` registers `close_db`. `transaction()` is also in `db_helpers.py`: it calls `conn.begin()`, then commits, or rolls back on any exception.
- Migration v2 creates the four tables. Audit columns follow § 4 (`updated_*` stay NULL until the first edit, and the shell sets both with `NOW()`). Unique indexes are named as in § 4.

**Frontend.**
- `api.js` copies `field` onto the thrown error.
- `useMasterForm` (a composable) holds the modal state, save, and deactivate/reactivate. A refusal that names a form field shows beside that field; any other refusal shows at the top of the modal.
- The panels are a table plus a modal. Edit buttons show only with the matching permission (`masters:edit`, or `equipment:edit` for classes). Code fields carry the "cannot be changed once in use" hint.
- `stores/masters.js` caches the three lists, including inactive records. Every save calls `resetMasters()` and the panel reloads, because a renamed site changes the full codes of its units.
- The Unit access modal lists the active units, plus any inactive units the user holds, greyed out and still tickable so they can be revoked. Unticking everything removes the user.

## 3. Files touched

**Backend**
- `backend/local_db.py`: migration v2 (the four tables).
- `backend/masters_core.py` (new): pure validators.
- `backend/masters.py`: replaced the placeholder with the routes, the error handlers and the DB rules.
- `backend/db_helpers.py`: added `get_db`, `close_db` and `transaction`.
- `backend/app.py`: `get_db()` removed; registers `close_db`.
- `backend/config_rbac.py`: `masters:edit` is IT admin only; added `masters:read_senior` and `equipment:edit`. The file already carried an uncommitted storekeeper change that I left alone.

**Backend tests**
- `backend/tests/test_masters_core.py` (new): the pure tests.
- `backend/tests/test_masters_api.py` (new): the API tests, including the two tests taken over from `test_modules.py`.
- `backend/tests/test_modules.py`: removed `TestMasters` and updated the docstring.
- `backend/tests/test_auth.py`: the engineer is now asserted to hold `equipment:edit`.
- `backend/tests/test_rbac.py`: role matrix updated.
- `backend/tests/conftest.py`: session-scoped truncate of the master tables, and a `uniq` fixture that hands out unique codes and warehouse names.

**Frontend**
- `frontend/src/api.js`: copies `field`.
- `frontend/src/stores/masters.js` (new): the cache.
- `frontend/src/components/layout/ModuleToolbar.vue` (new): the level-2 toolbar.
- `frontend/src/components/FormModal.vue` (new): see "Decisions".
- `frontend/src/views/MastersView.vue`: toolbar plus the four panels.
- `frontend/src/views/masters/` (new): `SitesPanel.vue`, `UnitsPanel.vue`, `EquipmentClassesPanel.vue`, `UserUnitsPanel.vue`, and `useMasterForm.js`.
- `frontend/tests/navigation.test.js`: per-role permission lists updated, and an engineer case added.

**Docs.** None, per the brief. This report is the only doc I wrote.

## 4. Decisions taken

Anything not covered by the brief is listed here.

1. **A shared `FormModal.vue` and a `useMasterForm.js` composable.**
   - The brief lists only the four panels, the toolbar and the store. Four panels with their own modal and save logic would have been copy-paste, which the DRY rule forbids.
   - The alternative was inline code in every panel. These two files are not in the brief's file list.
2. **Unit access saves by diff, not delete-all then insert.**
   - The brief says "delete, then insert". I delete only the removed units and insert only the new ones, in the same transaction.
   - The outcome is the same set, but units that stay keep their original `granted_at` and `granted_by`, so grant provenance is not reset by an unrelated edit. A test covers this.
3. **Unchanged set means no log line.** If a PUT leaves the set the same, nothing is logged, because there was no change to trace.
4. **A PUT with no recognised fields** does nothing and returns the record. There is no 400. A PUT body must still be a JSON object.
5. **`active` is accepted on POST and PUT,** as `true`, `false`, `1` or `0`. It defaults to 1 on create.
6. **Messages and fields for the 409s.** The brief gives only part of the wording.
   - Code or site changes on a record in use: `Code is in use and cannot be changed` (field `code`); `Unit is in use and cannot be moved to another site` (field `site_id`).
   - A site with active units that is being deactivated: field `active`.
   - An inactive target site: field `site_id`.
   - An unknown `site_id` on a unit is a 400 on `site_id`.
7. **The frontend lists include inactive records** and filter on `active` in the panel. The inactive toggle therefore needs no refetch.
8. **Unit access for a username that exists in no list is accepted** (a new user), as the brief says.
9. **Equipment class PUT** locks the row but has no in-use check, because nothing references a class in S001. S002 adds the check.
10. **The test-DB truncate uses `DELETE`, not `TRUNCATE`,** in FK order. `TRUNCATE` is blocked on tables that foreign keys reference. It runs once per session. The fixture fails the session with a clear message if the schema is not ready.

## 5. Not done / deferred / assumed

- **Browser check was partial.** I ran the app with the dev auth bypass against `vel_yantra_test`, not the real dev DB.
  - Confirmed: the Masters page loads with the toolbar; the Sites panel lists records; the Add-site modal opens; an empty submit shows the code error beside the field; the Unit access panel lists users and their units; the browser console showed no errors.
  - Not looked at in the browser: edit, deactivate, the Units and Equipment classes panels, the Unit access modal, and the role-based hiding of edit buttons. The brief's manual check of each panel is still open, for you or the reviewer. The dev stub user is `admin`; set `DEV_STUB_ROLE` to check other roles.
  - The test DB now holds leftover rows from the suite and my smoke run. The next test session clears them.
- **Acceptance through the UI** (entering the six real sites, the three SMTW units and a `VBM` class) was not done, to keep real data out of the dev DB. The API tests cover the same flows.
- **No-JS-test for `ModuleToolbar`.** There is no component-test library in the repo; the filtering is `canSeeNavItem`, which `navigation.test.js` covers.
- **Concurrency.** The locking follows the brief, but there is no test that races two requests; the tests are sequential.
- **Environment.** `backend/secrets_app.py` does not exist on this machine, so a plain `python app.py` fails outside dev mode. This is existing behaviour, not a change.
- **Status.** I set the brief's Status and the README index row to `In code review`.

## Amendment A1 — default site; deactivate inside the edit dialog

Implemented per `1-brief.md` § 10 (approved 13-10-2026). Test result: `tooling/run-tests.bat` is green, 231 backend tests (20 new) and 15 frontend tests. `vite build` has no errors.

### What was built

- **Default site.**
  - A **Default** checkbox on the site form, and a "Default" badge beside the code in the sites list.
  - At most one site is the default; there may be none.
  - Ticking Default on site B moves it from site A: A is cleared and B is set in one transaction, and both rows get `updated_at` / `updated_by`.
  - Unticking leaves no default.
  - The Add-unit dialog preselects the default site.
- **Deactivate / reactivate in the edit dialog** of all three masters (sites, units, equipment classes). The row buttons are gone, and the create dialog has no such button.

### How it works

- **Migration v3** adds `sites.is_default TINYINT(1) NULL` and `UNIQUE uq_sites_default (is_default)`. The value is 1 for the default site and NULL for the rest, never 0. MariaDB allows many NULLs under a UNIQUE index, so the database itself refuses a second default. The API shows the column as a boolean.
- **`masters.py`.**
  - The site queries use an explicit column list (`_SITE_SELECT`) that turns `is_default` into a boolean, and `_site_out` casts it to a Python bool.
  - Creating or updating with Default ticked runs `_clear_default_site`, one `UPDATE … WHERE is_default = 1 AND id <> <new>`, inside the same `transaction()`.
  - The rules return 409 with a `field`:
    - Default on an inactive site: field `is_default`.
    - Deactivating the default site: "This is the default site; untick Default first", field `active`.
  - A 1062 on `uq_sites_default` maps to the "made the default at the same time" message.
  - A single PUT that unticks Default and deactivates together is allowed, because the site will no longer be the default.
- **`masters_core.py`** validates `is_default` as true/false/1/0, with the same parser factory as `active`.
- **Frontend.**
  - `FormModal` has a `footer-left` slot, pushed to the left of the footer.
  - `ActiveToggle.vue` fills the slot: a Deactivate button, which becomes an inline "Deactivate X? Yes / No" row; or a Reactivate button for an inactive record.
  - `useMasterForm.js` now has `changeActive(active)`. It sends its own `PUT {active}` at once and does not send other unsaved edits. On success the dialog closes and the list reloads; a refusal shows inside the dialog. The old `setActive` and `pageError` are removed.
  - `defaultSiteId()` in `stores/masters.js` returns the active default site's id, or null. It is for S002 to reuse.

### Files touched

- `backend/local_db.py`: migration v3.
- `backend/masters_core.py`: `is_default` field; `_flag_parser` replaces `_parse_active`.
- `backend/masters.py`: default-site rules, `_SITE_SELECT`, `_site_out`, `_clear_default_site`, the `uq_sites_default` message; the sites routes rewritten.
- `backend/tests/test_masters_core.py`: `TestIsDefault`.
- `backend/tests/test_masters_api.py`: `TestDefaultSite`.
- `frontend/src/components/FormModal.vue`: the `footer-left` slot.
- `frontend/src/components/ActiveToggle.vue` (new): see "Decisions".
- `frontend/src/views/masters/useMasterForm.js`: `changeActive`, `editingActive`, `editingLabel`, `confirmingDeactivate`.
- `frontend/src/views/masters/SitesPanel.vue`: Default checkbox and badge; row button removed; toggle in the dialog.
- `frontend/src/views/masters/UnitsPanel.vue`: default preselected; row button removed; toggle in the dialog.
- `frontend/src/views/masters/EquipmentClassesPanel.vue`: row button removed; toggle in the dialog.
- `frontend/src/stores/masters.js`: `defaultSiteId()`.

### Decisions taken

1. **A new `ActiveToggle.vue`.** The brief lists the footer slot and `useMasterForm.js` but no component. The button and its inline confirmation are identical in three dialogs, so I put them in one component rather than copy them. The alternative was to repeat the markup in each panel.
2. **The Add-unit preselection is the site filter first, then the default site.** If the Units panel is filtered to one site, a new unit is preselected into that site, as before A1; otherwise the default site is preselected. A1.5 says filters themselves stay on "All sites", and they do. If you want the default site to win over the filter, it is a one-word change in `UnitsPanel.vue`.
3. **The default can be moved by a PUT that does not name the old default.** `_clear_default_site` is one `UPDATE … WHERE is_default = 1`, not a lock-then-clear of a row read earlier. The brief says "A's row is locked and cleared"; the single UPDATE locks that row while it clears it, with the same result.
4. **`is_default` is accepted on POST as well** and moves the default there too (the brief's tests include this).
5. **Deactivating the default site is refused even when it is the only site.** That follows the brief's rule as written.

### Not done / to verify

- **Browser check was partial.** I ran the app against the test DB and confirmed:
  - the Default badge shows in the list;
  - the row Deactivate buttons are gone;
  - the edit dialog has Deactivate on the left and a Default checkbox on the form;
  - clicking Deactivate shows the inline "Deactivate T0001? Yes / No";
  - Yes on the default site shows "This is the default site; untick Default first" inside the dialog;
  - the Add-unit dialog preselects the default site and has no Deactivate button.
- **Not checked in the browser:** a successful deactivate and reactivate in each of the three dialogs, and the "No" button. They are covered by the API tests for the rules, but the UI path is untried.
- **Race test.** The 1062 mapping is tested by stubbing out the clearing step, not by running two real concurrent requests.
- **Test DB.** It still holds rows from the suite and my browser check, which the next test session clears. Because of my browser clicks, one site there may be flagged as the default.

## Fix rounds

### Round 1

Tests: `tooling/run-tests.bat` green, 237 backend (was 231; +6 new tests) and 15 frontend; `npx vite build` built with no errors.

- **CR1-01 Fixed.** `replace_user_units` now starts with `SELECT unit_id FROM user_units WHERE username = %s FOR UPDATE`, with a comment saying why. A second replace for the same user waits, then reads current data. The diff logic is unchanged. A deadlock on two racing first-time grants stays possible (see CR1-02). `backend/masters.py`. No test: it needs two real concurrent transactions.
- **CR1-02 Fixed (minimal).** `get_db()` wraps `get_pooled_db()` in `try/except pymysql.err.OperationalError` and raises `DBUnavailable(describe_error(exc))`, so a DB that is down gives 503. Dead idle connections are still replaced by the pool's `ping=1` on checkout (no change). I did not add an app-level `OperationalError` handler: a mid-request deadlock (1213) is also an OperationalError and "Database unavailable" would be the wrong message for it. That stays a 500. `backend/db_helpers.py`.
- **CR1-03 Fixed (opens the existing set).** In "Add user", Save for a username already in the list does not PUT. It switches the same dialog to that user's edit state, with their held units ticked and the username read-only, and shows "This user already has unit access; their current units are shown. Review and save." under the username. `UserUnitsPanel.vue` (`load()` split from `open()`).
- **CR1-04 Fixed.** New `TestErrorMapping` in `test_masters_api.py`: non-1062 IntegrityError (1452) re-raised, not 409 (TESTING mode propagates it; production gives a logged 500); 1062 on `PRIMARY` gives the generic 409 with no `field`; the end-anchored key regex (CR1-06) is pinned; `ensure_schema` returning "down" gives 503 on `GET /sites`; a refused connection (OperationalError 2003) gives 503 (covers CR1-02).
- **CR1-05 Fixed.** The "This is the default site" refusal now tests `site["is_default"]` (the stored state). `{active:false, is_default:true}` on a non-default site falls through to "An inactive site cannot be the default" (field `is_default`). New test. `backend/masters.py`.
- **CR1-06 Fixed.** `_DUPLICATE_KEY_RE` is anchored with `$`. `backend/masters.py`.
- **CR1-07 Fixed.** `UserUnitsPanel.vue` keeps a `heldInactiveIds` set, filled in `load()` from the user's held inactive units. `choices` filters on it instead of on `selected`, so an unticked inactive unit stays listed and can be re-ticked.
- **CR1-08 Fixed.** `test_the_database_allows_only_one_default` takes two fresh sites from `make_site`, clears the default only where `is_default = 1`, and asserts `pymysql.err.IntegrityError`. `test_masters_api.py`.
- **CR1-09 Rejected** - user decision 14-10-2026: v3 already applied; migrations are append-only.

Decisions taken: the CR1-03 variant (switch to the existing user's set, not refuse); no app-level OperationalError handler (CR1-02). Files touched: `backend/masters.py`, `backend/db_helpers.py`, `backend/tests/test_masters_api.py`, `frontend/src/views/masters/UserUnitsPanel.vue`, this report.

Still for the browser check: CR1-03 (Add user with an existing username shows their set) and CR1-07 (untick then re-tick an inactive unit).

### Round 2

Answering `4-code-review-r2.md`. No code changed: the user decided not to fix the open finding.

- **CR2-01 Rejected** — user decision 14-10-2026, both halves:
  - *Deadlock on concurrent first-time unit-access grants → 500.* It is rare with one IT admin; nothing is corrupted; the save can be repeated.
  - *DB restart during the day → 500 instead of 503.* The pool's `ping=1` already handles the overnight dead connection that CLAUDE-COMMON's rule targets. A mid-day restart is rare and short.
