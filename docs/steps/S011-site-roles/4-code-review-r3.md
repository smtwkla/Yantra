```
Step: S011 — Roles per site, held in Yantra
Doc: code-review r3
Author: Code reviewer (Opus)
Date: 16-10-2026
```

# S011 — Code review, round 3

**Verdict: no `blocker` or `major` finding is open.** CR2-01 is fixed as claimed. This
round raises 1 minor finding and 2 nits. None is a regression of the fix round.

**Scope of this review.**
- **What was reviewed.** Fix round 2 only: CR2-01 and the coder's "Round 2" entry under
  `## Fix rounds` in `3-impl-report.md`.
- **How the delta was built.** The working tree was written as tree `2a6b457`, using a
  temporary `GIT_INDEX_FILE`, so `.git/index` was not touched. It was compared with the
  round-2 tree `5e19fc7` (`git diff -w --ignore-cr-at-eol`).
- **Left out.** `docs/review/`, `tooling/dev/` and `docs/steps/S012-*`.
- **What the delta holds.**
  - `backend/masters.py`: 2 hunks, the two log guards.
  - `backend/tests/test_site_roles_api.py`: 1 new test.
  - `3-impl-report.md`: the Round 2 entry.
  - `docs/steps/README.md`: the S012 row (orchestrator's, outside S011).
  - `4-code-review-r2.md` itself.
  - Nothing else changed. The full S011 delta against the S010 baseline `15227de` is
    43 files.

**Tests, run by the reviewer:**
- `tooling/run-backend-tests.bat`: **895 passed** in 58.5 s. Exit code **0**. The count
  matches the report: 894, plus 1 new test.
- `tooling/run-frontend-tests.bat`: **38 passed** (7 files). Exit code **0**.
- `npx vite build` in `frontend/`: clean, exit code **0**, no warnings. The frontend did
  not change in this round.

## Findings

### CR3-01 — minor — A whole-set save reads the database after the commit and before it logs, so a DB failure there drops the log line

**Where:**
- `backend/masters.py:605-608` (`create_person`) and `:656-659` (`update_person`). After
  the `transaction` block commits, both call `_fetch_person`, and only then
  `_log_login_save`.
- `_log_login_save` (`:773-780`) reads the "after" rows itself, on a new cursor.
- Compare the per-site routes: `put_person_site` reads `after` inside the transaction
  (`:811`). `_site_row_response` then logs before it touches the database again.

**Problem.**
- On the whole-set path, the rows are already committed when two more reads run.
- If either read fails, the request ends in an error before `logger.info` is reached.
  That covers a dead connection, the DB restarting, or `DBUnavailable` (a 503).
- The access change is then in the database, but no line records it. That breaks brief
  § 2 (ISO 27001 A.8.15) and § 5.5 on the very path CR2-01 was about.
- The per-site routes cannot skip their line this way.
- Round 2 said that `_log_login_save` reads the "after" rows "the same way the per-site
  `_site_row_response` does". That was wrong: the per-site route reads them inside the
  transaction. This finding corrects round 2. It is not a regression of this fix round.

**Failure scenario.**
1. IT admin saves Ravi's login with Manager at SMTW. The transaction commits.
2. MariaDB restarts at that moment, or the pooled connection drops, before
   `_fetch_person` runs.
3. The client gets a 503 (or a 500). Ravi is Manager at SMTW, and the log holds no
   `login saved` line.
4. IT admin retries the save. The rows are already in place, so the retry's line shows
   `before` = `after` (see CR3-02). It does not show who made the change, or when.

The window is a few milliseconds, and only IT admin can open it. That is why this is
`minor`.

**Fix.**
1. Inside the transaction, after `_replace_site_rows`, read the "after" rows with
   `_site_rows(cur, …)`, the same way `put_person_site` does. Pass them to
   `_log_login_save` instead of reading them there.
2. Call `_log_login_save` straight after the `with transaction(...)` block, before
   `_fetch_person`.

The line must still be written after the commit, so a rolled-back save never logs.

**Test.** Patch `_fetch_person` to raise `DBUnavailable` on a whole-set PUT. Assert that
the response is 503 and that one `login saved` line was written anyway.

### CR3-02 — nit — A whole-set save that changes nothing still logs a line

**Where:** `backend/masters.py:658` and `:607`, the guard `if sites is not None:`.

**Problem.**
- Brief § 5.5 says: "Logged at INFO only when something changed".
- The per-site routes follow it: `_site_row_response` compares `_describe(before)` with
  `_describe(after)`.
- A whole-set PUT now logs even when nothing changed. That is a PUT that sends the
  stored login and the stored rows. Its line reads `login=ravi->ravi before=[X] after=[X]`.
- Round 2 suggested this exact guard, and the fix follows that suggestion. The miss is
  round 2's, not the coder's.
- Logging too much is the safe way round. The Team dialog sends `sites` only with a
  login change, so a no-op line can come only from the API.

**Fix (optional).** Log when the login changed, or when
`_describe_rows(before) != _describe_rows(after)`, as the per-site path does. This fits
naturally with the in-transaction "after" read of CR3-01. A POST always logs, because
there was no person before it. If the guard is kept as it is, record this as a decision
in the report.

### CR3-03 — nit — The new test does not assert the PUT's status code

**Where:** `backend/tests/test_site_roles_api.py:198-214`
(`test_rows_replaced_with_the_login_unchanged_or_absent_are_logged`).

**Problem.**
- The test asserts the POST's 201, but not the PUT's 200.
- It also drops the first `login saved` line with `[1:]`, assuming that line came from
  the `make_person` fixture.
- The asserted lines would catch a failed PUT, so nothing is wrong today. But the test
  depends on how the fixture logs.

**Fix.** Assert `status_code == 200` on the PUT. Optionally, call `caplog.clear()` after
`make_person` instead of slicing with `[1:]`.

## Earlier rounds — CR2 finding verified

| Finding | Claimed | Verified |
|---|---|---|
| CR2-01 | Fixed | **Fixed.** Both guards are now `if sites is not None:`. Details below the table. |

**CR2-01 in detail.**
- **Where the rows are replaced.** `sites` is non-None exactly when `_replace_site_rows`
  runs:
  - `create_person` at `:603`;
  - `update_person` at `:642-644`;
  - the `before_rows` of `update_person` is bound on the same branch.
- **The two cases from round 2 are logged now.**
  - A PUT with the same login and `sites` logs `login=ravi->ravi`, because
    `clean.get("username", person["username"])` gives the stored login.
  - A POST with `username: null` and Technician rows logs `-->-` and `before=[]`.
- **The API is unchanged.** The coder took option 1 of CR2-01.
- **Decision 4.1.8 still holds.**
- **The test covers both cases.** It checks both halves of each line, as CR2-01 asked.
- **Every writer of the site rows logs.**
  - `memberships` and `person_units` are written only from `_write_site_row` and
    `_delete_site_row`.
  - Those two are called only from `_replace_site_rows` (whole set) and from
    `put_person_site` and `delete_person_site` (per site).
  - The only other write is `local_db.py:276`, the v8 migration copy of legacy rows.
  - The per-site PUT logs when a row really changes. The per-site DELETE always logs,
    because `before` is non-None there and a missing row is a 404.
  - On the paths that commit normally, no line is skipped now. The one exception left is
    a DB failure after the commit (CR3-01).

## Checked and found consistent

- **The fix round changed nothing else.**
  - The masters.py hunks change only the two `if` guards and one argument
    (`clean["username"]` became `clean.get("username", …)`). The new argument cannot
    raise a KeyError on the new paths.
  - No lock, transaction order or refusal order changed.
  - Apart from the impl report, the r2 file and the orchestrator's S012 README row,
    nothing outside the two named files moved.
- **No exception is swallowed, and no SQL is built from strings.** The new logging path
  passes values through `%s` logger arguments.
- **The impl report.**
  - The Round 2 entry matches the code and lists the files touched.
  - Its test count (895 backend, 38 frontend) matches this run.
  - `## Manual checks` still holds all four **important** checks of brief § 8 as unticked
    boxes.
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

Also worth a look (unchanged from round 2):
- the S007 guard on a change to a site row only;
- legacy rows shown as "No role";
- as an engineer: the select offers only Technician, and an Operator row shows read-only;
- the "Adding this login gives access as" line;
- clearing a manager's login is refused;
- with the DB stopped: IT admin still sees Settings › Database, and a maintenance user
  gets the "database unavailable" message;
- `DEV_STUB_ROLE = "maintenance_team"`;
- the backend log after a login change and after a login clear: one `login saved` line
  each, with the old and new login and the rows before and after.
