```
Step: S011 — Roles per site, held in Yantra
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S011 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** All six CR1 findings are fixed as
claimed. This round raises 1 new minor finding.

**Scope of this review.**
- **What was compared.** The S011 delta is `git diff -w --ignore-cr-at-eol 15227de
  <working tree>`. The S010 baseline is tree `15227de`. The working tree was written as
  tree `5e19fc7`, using a temporary `GIT_INDEX_FILE`, so `.git/index` was not touched.
- **Left out.** `docs/review/`, `tooling/dev/seed_dev.py` and `tooling/dev/dev-seed.bat`.
  They are not part of S011.
- **Checked against.** The approved brief, amendment A1 and its rule sets, and the gate-A
  decisions of 16-10-2026.
- **Also checked.** The round-1 fixes, and whether they changed anything else.

**Tests, run by the reviewer:**
- `tooling/run-backend-tests.bat`: **894 passed** in 54 s. Exit code **0**.
- `tooling/run-frontend-tests.bat`: **38 passed** (7 files). Exit code **0**.
- `tooling/run-tests.bat`, run once more to check the coder's remark: 894 + 38 passed.
  Exit code **0**.
- **The coder's nonzero exit code does not happen here.** pytest, vitest and the wrapper
  all return 0. It most likely came from the coder's shell wrapper (for example, the exit
  status of a `| tail` pipe), not from the suite.
- `npx vite build` in `frontend/`: clean, exit code 0, no warnings.

## Findings

### CR2-01 — minor — A whole-set save that keeps the login writes site rows with no log line

**Where:**
- `backend/masters.py:658-659` (`update_person`): `if login_changes: _log_login_save(…)`;
- `backend/masters.py:607-608` (`create_person`): `if clean.get("username") is not None`;
- `_login_save_sites` (`:555-571`) accepts `sites` whenever `username` is in the body,
  whether or not the login changes.

**Problem.**
- **The API accepts `sites` without a login change.** `_login_save_sites` takes the field
  whenever `username` is in the body. `_replace_site_rows` then deletes, inserts and
  updates the person's memberships and unit rows.
- **But a line is logged only when the login changes.** Two saves change the rows and log
  nothing:
  - `PUT /people/<id>` with `username` equal to the stored login, plus `sites`;
  - `POST /people` with `username: null` and Technician rows (decision 4.1.8 allows it).
- **That breaks a brief rule.** Brief § 2 (ISO 27001 A.8.15) and § 5.5 ask that every
  access change be logged with its before and after state.
- **The per-site routes already meet it.** They log every real change.
- **This is not a fix-round regression.** The guard was there in round 1, and CR1-01 did
  not touch it. Round 1 missed it.

**Failure scenario.**
1. IT admin, or a script, sends `PUT /people/42 {"username": "ravi", "sites": [{SMTW
   manager, all units}]}`. Ravi already has the login `ravi` and is a Technician at
   SMTW.
2. Ravi is now Manager at SMTW. No log line records the change.
3. An access review (A.5.18) that reads the log cannot see when Ravi became Manager, or
   who made him one.

The Team dialog sends `sites` only on a login change (`PeoplePanel.vue:160`). The gap is
therefore open through the API only, and only to IT admin.

**Fix.** Choose one of these:
- **Log whenever rows were replaced.** Log when `sites is not None`, not only when
  `login_changes` (in `update_person`, and the same in `create_person`). For an
  unchanged login, the line shows `login=ravi->ravi`, or log only the rows.
- **Or narrow the API.** Refuse `sites` when the login does not change: 400 on field
  `sites`, the same as `sites` without `username`. Then a login save is the only path
  that replaces the whole set.

The first option keeps decision 4.1.8 as it is. Either way, add a test: a PUT with the
same login and a changed set writes exactly one line, with both halves.

## Earlier rounds — CR1 findings verified

| Finding | Claimed | Verified |
|---|---|---|
| CR1-01 | Fixed | **Fixed.** `update_person` reads `before_rows` with `_site_rows`. It does so after the person row is locked, and before `_replace_site_rows`. Every writer of `memberships` and `person_units` locks the person row first, so the read cannot miss a change committed by another request. The old login comes from the locked row. `_log_login_save` logs `login=<old>-><new> before=[…] after=[…]`, in the same row format as the per-site line. `create_person` logs `-` and `[]` as the before side. `before_rows` is always bound when it is used: a login change without `sites` is a 400 earlier. New test: `test_login_change_and_clear_log_both_sides` (change, then clear). It asserts both halves of both lines. The "logged once" test was updated. |
| CR1-02 | Fixed by the orchestrator | **Fixed.** `.claude/CLAUDE.md:12` has the bullet "RBAC deviation (S011)". It is the proposed text of report § 4.3.1, plus a pointer to `docs/Keycloak.md`. The text matches the code: `SITE_ROLES`, `SITE_SCOPED`, `has_perm_at`, `accessible_unit_ids(cur, key)`, fail-closed and the admin bypass. Plan.MD § 3 now points to something that exists. |
| CR1-03 | Fixed | **Fixed.** `test_unknown_unit_id_is_400_on_both_routes` covers the whole-set save and `PUT …/sites/<id>`. Both give 400 on field `unit_ids`, and neither writes a login or a row. `test_whole_set_with_a_failing_second_row_writes_nothing` sends a valid first row, then a second row with a unit of another site, to a person who already has a row. It gets 400 on `unit_ids`, and the login and the rows are unchanged afterwards. |
| CR1-04 | Fixed | **Fixed.** `access_core.valid_memberships` is public. It is used in `access_core` itself (4 places) and in `auth_utils.membership_sites` and `_unit_pools`. The copy of the filter is gone. `put_person_site` calls `no_login_role_error` once (`masters.py:805`). |
| CR1-05 | Fixed | **Fixed.** The conftest helper is `harness_user` (`conftest.py:46`), and its one caller, `_inject_test_user`, was updated. No `test_user` name is left in `backend/tests/`. |
| CR1-06 | Fixed | **Fixed.** In `smtw_erp_devops/docs/lob-apps/Yantra.MD`, step 5 again reads "PKCE; redirect URI `https://vel-yantra.mspv.app/*`". The S011 client-role and switch-over text is kept. The user commits this file in the devops repo. |

## Checked and found consistent

- **The fixes changed nothing else.**
  - The new `_site_rows` read in `update_person` runs only when `sites` is sent. It takes
    no lock, so the lock order is unchanged: person, then trades, then memberships and
    `person_units`, then units.
  - `_log_login_save` reads the "after" rows on a fresh cursor once the commit is done,
    the same way the per-site `_site_row_response` does.
  - The rename and the extracted helper change no behaviour. All 891 tests from round 1
    still pass. The 3 new ones pass too.
- **The atomicity order of `_replace_site_rows` is unchanged.**
  1. The no-login rule.
  2. Every row's checks.
  3. The deletions.
  4. The writes.

  All of it runs in the same transaction as the login write.
- **Everything else that round 1 listed under "Checked and found consistent" still
  holds.** The touched code was re-read, and none of it changed apart from the items
  above.
- **The impl report.** `## Fix rounds` § Round 1 answers every CR1 finding, and each
  answer matches the code. `## Manual checks` still has all four **important** checks of
  brief § 8 as unticked boxes, and the plain checks as a list.
- **Track: full.** Not applicable.

## Manual browser checks still needed (user)

Important (unticked in `3-impl-report.md`):
- [ ] Only `maintenance_team`, no site role → the "no access yet" page, with the name and
  Sign out in the top bar.
- [ ] As IT admin in Team: give a test person Manager at SMTW (all units) and Engineer at
  VEL (one unit). Then, as that person: all of SMTW, with edit; one VEL unit, with edit;
  the other VEL units invisible.
- [ ] Change the VEL role to Operator. After a page load, the edit buttons on VEL
  equipment are gone, and a direct edit is refused (403).
- [ ] The production switch-over (report § 5.1), in that order.

Also worth a look:
- the S007 guard on a change to a site row only;
- legacy rows shown as "No role";
- as an engineer: the select offers only Technician, and an Operator row shows read-only;
- the "Adding this login gives access as" line;
- clearing a manager's login is refused;
- with the DB stopped: IT admin still sees Settings › Database, and a maintenance user
  gets the "database unavailable" message;
- `DEV_STUB_ROLE = "maintenance_team"`;
- the backend log after a login change and after a login clear: one `login saved` line
  each, with the old and new login and the rows before and after (CR1-01).
