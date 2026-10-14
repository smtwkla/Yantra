```
Step: S001 — Basic masters
Doc: code-review r2
Author: Code reviewer (Opus)
Date: 14-10-2026
```

# S001 — Code review, round 2

**Verdict: no `blocker` or `major` finding is open.** There is 1 `minor` finding and no `nit`.

Scope: the round-1 fixes (CR1-01 to CR1-08) in `backend/masters.py`,
`backend/db_helpers.py`, `backend/tests/test_masters_api.py` and
`frontend/src/views/masters/UserUnitsPanel.vue`, checked against
`3-impl-report.md` § Fix rounds / Round 1. I also made a light pass over the
rest of S001. CR1-09 was rejected by the user (v3 is applied; migrations are
append-only), so it is not raised again.

## Test result (run by the reviewer)

- `tooling/run-tests.bat`: **green**, exit 0.
  - Backend: 237 passed in 6.1 s. That is 231 plus the 6 new tests, as the report says.
  - Frontend (vitest): 3 files, 15 tests passed.
- `npx vite build` in `frontend/`: **built** in 1.62 s, with no errors and no warnings.

## Round-1 findings: verification

| ID | Claimed | Verified | Notes |
|---|---|---|---|
| CR1-01 | Fixed | **Yes** | `masters.py:378-380`: `SELECT unit_id … WHERE username = %s FOR UPDATE` is the first statement in the transaction, and a comment says why. `transaction()` sends a plain `BEGIN`, not `WITH CONSISTENT SNAPSHOT`. InnoDB therefore creates the read view at the first consistent read, which is `_user_units` on line 381, after the lock is held. So `before` is current. Lock order is `user_units` then `units` (`_check_grantable`). `update_unit` takes only `units` and reads `user_units` without a lock, so there is no cycle. The remaining deadlock on first-time grants is discussed under CR2-01. |
| CR1-02 | Fixed (minimal) | **Partly** | The cold-pool path now gives 503. The warm-pool path, which is the usual one in production, still gives 500: **CR2-01**. |
| CR1-03 | Fixed | **Yes** | `UserUnitsPanel.vue:62-74`; regression check below. |
| CR1-04 | Fixed | **Yes** | `TestErrorMapping` (`test_masters_api.py:610-658`) has five tests: a 1452 error is re-raised; a 1062 on `PRIMARY` gives the generic 409 with no `field`; the end-anchored regex is pinned; `ensure_schema` returning "down" gives 503; a 2003 from `get_pooled_db` gives 503 with "Database unavailable". The comment about `TESTING` re-raising is accurate. |
| CR1-05 | Fixed | **Yes** | `masters.py:231-237`: the default-site refusal now tests the stored `site["is_default"]`. `test_deactivating_a_non_default_site_while_ticking_default` asserts 409 with field `is_default` and the "cannot be the default" wording. |
| CR1-06 | Fixed | **Yes** | `masters.py:38`: the pattern is anchored with `$`, and a comment says why. The test message `… for key 'uq_sites_code' for key 'PRIMARY'` resolves to `PRIMARY`, so it gives the generic 409. |
| CR1-07 | Fixed | **Yes** | `UserUnitsPanel.vue:27-30, 46`: `heldInactiveIds` is filled once in `load()`, and `choices` filters on it. An unticked inactive unit stays listed and can be ticked again. A new user gets an empty set, so no inactive unit is offered, which matches "may be kept but not newly granted". |
| CR1-08 | Fixed | **Yes** | `test_masters_api.py:572-583` uses two fresh `make_site` rows, clears the default only `WHERE is_default = 1`, and asserts `pymysql.err.IntegrityError` matching `uq_sites_default`. |

### CR1-03 regression check (Add user with an existing username)

- **Name match.** The name is normalised with `trim().toLowerCase()` before the
  lookup. That matches the backend's `normalise_username`, so `" JDoe "` finds `jdoe`.
- **No PUT.** On a match, `save()` returns before any PUT. `load(existing.username,
  existing.units, false)` then does three things:
  - it ticks the held set, including held inactive units, through `heldInactiveIds`;
  - it makes the username read-only;
  - it switches the title to "Unit access — jdoe".
- **Ticks discarded.** The ticks made in the Add dialog are dropped. The message
  says "their current units are shown. Review and save.", so nothing is lost
  silently. This is the coder's reported decision, and it is the safe choice.
- **Second Save.** `isNewUser` is now false, so the guard is skipped and the PUT
  replaces the reviewed set. `error` is cleared first (line 76).
- **Residual gaps.** Both are acceptable, and neither is a new finding:
  - The guard is client-side and uses the list loaded when the panel opened.
    Another admin adding the same user in the meantime is not caught. With one
    IT admin, this is the same low-likelihood race as CR1-01.
  - If the list failed to load (`items === null`), the guard does nothing. The
    panel then shows the load error in place of the table.
- **Styling.** The notice is shown with Bootstrap's `is-invalid` red styling on a
  read-only field. It reads as an error rather than as information. This is
  cosmetic and acceptable, because the user does have to act.

## Findings

### CR2-01 — minor — With a warm pool, a DB outage still gives 500; the CR1-02 fix covers only an empty pool

`backend/db_helpers.py:27-32` (`get_db`), with DBUtils `steady_db.py:441-449` and `pooled_db.py:339-343` (dbutils 3.2.0, the installed version)

**Problem.**
- The fix relies on `get_pooled_db()` raising `OperationalError` when the server
  cannot be reached. It does so only when the pool has **no idle connection**
  and `PooledDB.connection()` must create one (`steady_connection()`).
- Once the app has served a request, the pool holds idle connections. On
  checkout it calls `con._ping_check()`:
  - `ping(False)` fails, so `alive = False`;
  - DBUtils tries `self._create()`;
  - that fails too, and the failure is **swallowed**
    (`except Exception: pass`, line 444);
  - `PooledDB.connection()` ignores the return value, so the dead connection is
    handed back with no exception.
- The error then surfaces on first use, as `InterfaceError(0, '')` or
  `OperationalError` 2006/2013. In a write route this is in `conn.begin()`, and
  in a read route it is in `cur.execute`.
- Nothing maps either error, so the response is 500.
- The new test, `test_no_connection_is_503_not_500`, monkeypatches
  `get_pooled_db` to raise, so it covers only the cold-pool path.
- The comment on lines 28-29 ("an error means the server itself cannot be
  reached") suggests that every outage is caught there. It is not.

**Failure scenario.**
- The app has been serving all morning, and the MariaDB container restarts for
  two minutes.
- Every masters call in that window takes an idle pooled connection and gets no
  error from `get_db()`. It then fails on `BEGIN` or `SELECT` and returns 500
  "INTERNAL SERVER ERROR" instead of 503 "Database unavailable".
- That is the scenario CR1-02 described, so in practice CR1-02 is still open.
- Only the first requests after a cold start, or a burst that empties the idle
  cache, get the 503.

**On the coder's reasoning (deadlock 1213 left as 500).** The reasoning is right
on the point it makes: a deadlock is not "Database unavailable", so a blanket
`OperationalError` → 503 handler would give the wrong message. But a deadlock is
not an internal error either. Since CR1-01, a deadlock is a realistic outcome:
- the `FOR UPDATE` on a username with no rows takes a **gap** lock;
- gap locks do not conflict with each other;
- so two concurrent first-time grants deadlock when they then INSERT.

This happens for the same new user. It also happens for two **different** new
users whose names fall in the same gap of the `(username, unit_id)` index, for
example `jdoe` and `jeff` when no username sorts between them. The loser gets a
500. This is rare with one IT admin, but the fix is cheap, and the error code
says which case applies.

**Suggested fix.** Add one app-level handler that branches on the error code. Do
not add a blanket `OperationalError` handler.
- `pymysql.err.InterfaceError`, and `OperationalError` with code 2003, 2006 or
  2013 (cannot connect, gone away, lost connection) → 503,
  `"Database unavailable: …"`. This matches `_db_unavailable`.
- `OperationalError` 1213 (deadlock) or 1205 (lock wait timeout) → 409, with
  "Another change was saved at the same time; reload and try again". This
  matches the wording of the existing generic 409.
- Re-raise anything else, so it is still a logged 500.

The handler belongs in `app.py` next to `_db_unavailable`, because the problem
is app-wide, not specific to masters.

Tests:
- Monkeypatch a route helper to raise `InterfaceError(0, '')` and assert 503.
- Monkeypatch one to raise `OperationalError(1213, 'Deadlock found…')` and
  assert 409.

Correct the `get_db` comment so it says the pool can hand back a dead connection
when reconnecting fails.

This is again app-wide behaviour, so **the user decides** whether it goes into
S001 or into a later step. The 1213 → 409 half belongs to S001, because S001
introduced the gap-lock deadlock.

## Light pass over the rest of S001

I found nothing new beyond CR2-01. Points I checked:
- **Combined request on the default site.** `PUT {active:false, is_default:false}`
  on the default site is refused with "This is the default site; untick Default
  first", although the same request unticks it. That follows the A1 rule
  ("deactivating the default site → 409"), and the UI never sends both, so it is
  not a finding.
- **`transaction()` with a dead connection.** If `rollback()` on a dead
  connection raises, the original exception is replaced but stays chained as
  `__context__`. It is still a logged 500, nothing is swallowed, and CR2-01's
  handler would map either error the same way.
- **Rows left by `test_the_database_allows_only_one_default`.** The test leaves
  the test DB with no default site. No other test assumes there is one: they
  all set the default they need.

## Checked and found consistent

- **CR1-01 lock semantics.** These were verified by reading the code; see the
  table above:
  - the locking read comes first, then the consistent read;
  - the snapshot is taken after the lock;
  - the diff and the log line are unchanged;
  - an unchanged set is still not logged.
- **CR1-02, cold-pool path.** `DBUnavailable(describe_error(exc)) from exc`
  keeps the cause chained, and the app handler gives 503 with the driver's
  message.
- **CR1-04 tests.** They exercise the real blueprint handler through the API,
  not the regex alone. The 1452 test correctly expects propagation under
  `TESTING`.
- **CR1-05 / CR1-06.** The order of the checks in `update_site` is unchanged for
  every other combination. The existing A1 tests still pass.
- **CR1-07 / CR1-03.** `load()` and `open()` are split cleanly, with no
  duplicated state reset. `toggle()` still replaces the `Set`, so reactivity holds.
- **Scope.** Only the four files named in the report changed for this round. The
  two decisions taken are reported:
  - the CR1-03 variant;
  - no blanket `OperationalError` handler.

  The `.claude/CLAUDE.md` diff (step workflow, standards) is not S001 code.
- **Rules.**
  - No SQL is built from client input.
  - No exception is swallowed in S001 code. The swallowing in CR2-01 is inside
    DBUtils.
  - No deprecated APIs are used.
  - The new comments say why.
  - No migration was touched.

## Still needs the user's manual browser check

These are carried over from round 1; nothing here is covered by an automated test.

1. **Each panel (Sites, Units, Equipment classes):**
   - create and edit;
   - an inline field error, such as a duplicate code shown beside Code;
   - the "cannot be changed once in use" hint;
   - a 409 for a code in use.
2. **Deactivate and Reactivate in each of the three edit dialogs:**
   - the inline confirm row, including **No**;
   - a successful deactivate and reactivate;
   - a refusal shown inside the dialog: a site with active units, the default
     site, and a unit reactivated under an inactive site.
3. **Default site:**
   - the badge;
   - moving the default from A to B;
   - Add-unit preselecting the default when the filter is "All sites", and the
     filtered site otherwise.
4. **Unit access:**
   - inactive units greyed in the list and in the dialog;
   - an inactive held unit revoked by unticking it;
   - a brand-new user added by typing a username.
   - **CR1-03:** click Add user, type an existing username such as ` JDoe ` with
     mixed case and spaces, tick something and Save. Expect:
     - no save;
     - the dialog switches to "Unit access — jdoe" with their current units
       ticked and the username read-only;
     - the notice under the username.

     A second Save then stores the reviewed set.
   - **CR1-07:** in a user who holds an inactive unit, untick it, then tick it
     again. It must stay listed. Save and confirm it is still held.
5. **Role hiding:**
   - `DEV_STUB_ROLE=maint_engineer`: the Sites and Units edit buttons and Unit
     access are hidden, and class editing works;
   - `maint_operator`: every edit button is hidden.
6. **Acceptance (§ 8):**
   - enter the six Plant-Facts § 2 sites, the units `SMTW.FWMILL`, `SMTW.MCC1`
     and `SMTW.MCC2`, and a user's grant, as IT admin;
   - then add `VBM` as an engineer.
7. **Optional, for CR2-01:** stop the dev DB (`tooling/dev/dev-db-down.bat`)
   while the backend is running and has already served a page. Reload a masters
   panel. Today this shows a 500, not "Database unavailable".
