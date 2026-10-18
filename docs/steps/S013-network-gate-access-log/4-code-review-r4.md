```
Step: S013 — Network gate, access log and job queue
Doc: code-review r4
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S013 — Code review, round 4 (amendment A1)

**Verdict: no `blocker` or `major` finding is open.** Four nits, none of which blocks A1.

**Scope of this round.** Amendment A1 only: one row per sighting per day, enforced by the
database. That covers `network_core.sighting_hash` and the `SightingCache` docstring,
`access_control._insert` and `_record`, migration v10 (edited in place, which A1 allows) and the
four test files. The rest of S013 was reviewed in rounds 1–3. It is not re-reviewed here. I only
checked that A1 breaks nothing those rounds settled.

**Tests.** `cd backend && uv run pytest -q` → **`1283 passed in 184.57s (0:03:04)`**. This matches
the coder's figure. The frontend did not change in A1, so I did not run `vite build` again.

## Findings

### CR4-01 — nit — `backend/access_control.py:189`: `INSERT IGNORE` would silently store an unknown outcome as `''`

- **The problem.** `INSERT IGNORE` does more than skip a duplicate key. In MariaDB it also turns
  data errors into warnings and writes a coerced row:
  - an over-long string is cut;
  - a NULL in a NOT NULL column gets the column's implicit default;
  - a value outside an `ENUM` is stored as `''`.
- **Why nothing is hidden today.** The coder's argument holds for the current code:
  - every text value is truncated to its column width;
  - `client_ip` is never NULL. `client_ip()` returns `""` when `X-Real-IP` is missing, so the row
    carries an empty address with `is_internal = 0`, as § 5.1 wants;
  - `method` and `path` are always strings;
  - `is_internal` is an int;
  - the hash is always 40 characters.

  Also, `rowcount == 0` can only mean a duplicate. A coerced row is still inserted
  (`rowcount == 1`), so the "already seen" logic is sound.
- **Why it is still a risk.** `classify_outcome` passes `g.access_outcome` through unchecked
  (`network_core.py:88`). Before A1, a future gate that marks a new outcome without a new ENUM
  value would have failed loudly: a strict-mode error, a 30 s back-off and a warning. After A1:
- **Failure scenario.** A later step adds `g.access_outcome = "denied_site"` but forgets the
  migration. Every such row is stored with `outcome = ''`. The "denials only" filter misses it,
  and nothing is logged.
- **Suggested fix.** Either:
  - check `outcome` against the ENUM's values (one constant in `network_core`), and log or raise
    before the insert; or
  - after the insert, when `rowcount == 1` and the connection reports warnings, log them once.

  Either option is a few lines. A comment at the insert noting this IGNORE side effect would be
  the minimum.

### CR4-02 — nit — `backend/access_control.py:236`: the "address missing" warning has no test

- **The problem.** Coder decision 2 changes when the warning is logged: only when the row was
  actually written (`written == 1`). I think this is right (see "Checked" below). But no test
  covers the warning, before or after A1. A refactor could drop the `written and` condition, or
  the warning itself, and the suite would stay green.
- **Failure scenario.** A refactor drops the warning. Production then loses its only signal that
  Nginx stopped sending `X-Real-IP`, which is the trap that manual check 3 exists for.
- **Suggested fix.** Add one `caplog` test:
  1. Send a request with no `X-Real-IP`. `REMOTE_ADDR_FALLBACK` is already off in tests.
     Expect one warning.
  2. Call `reset_access_log_state()`, then send the same request again. The insert is ignored,
     so expect no second warning.

### CR4-03 — nit — `docs/steps/S013-network-gate-access-log/3-impl-report.md`: important check 3 now appears as two boxes

- **The problem.** The main `## Manual checks` list still has check 3 in its pre-A1 wording. The
  A1 section adds the tightened wording as a separate `- [ ]` box.
- **Failure scenario.** At gate B the user sees two boxes for one check. They may tick the old one
  and skip the new one, which is the box that matters ("carrier's address, not 10.24.0.18 …
  before the gate is trusted").
- **Suggested fix.** Replace the wording of check 3 in the main list with the brief's A1 wording
  (§ 8). In the A1 section, refer to that box instead of repeating it. The plain note about
  10 minutes of browsing can stay.

### CR4-04 — nit — `backend/tests/test_network_core.py:134`: a long run of spaces inside an `assert`

- **The problem.** The second assert in `test_none_and_empty_hash_alike` is a joined line:
  `== ` is followed by about 12 spaces before the second `sighting_hash(…)`. It is valid Python,
  so this is purely cosmetic.
- **Why it counts.** These are not IDE whitespace changes: the line was written this way.
- **Suggested fix.** Wrap it in parentheses across two lines, as the other long asserts do.

## Answers to the orchestrator's specific questions

- **What the hash covers.** `sighting_hash(*key)` is computed from the same `key` tuple that the
  cache checks and remembers (`access_control.py:206`, `:226`, `:235`), before truncation.
  Cache and database therefore agree on what one sighting is.

  My view: hashing the untruncated parts is right and acceptable, not merely tolerable.
  - The parts that get truncated never reach their limits in practice:
    - `detail` is a fixed code, a permission key, `key@site:<id>`, or a 403 message already cut
      to `DENIED_DETAIL_CHARS = 100`;
    - `who` is a Keycloak `sid` (a UUID) or a username;
    - `ip` is Nginx's `$remote_addr`.
  - The only effect of the choice would be two rows that look identical in the viewer, and only
    for parts over 255/100/45 characters. Hashing the truncated values instead would make the
    database merge sightings that the cache keeps apart, which is worse.
  - It also doesn't open a way to flood the log. Anyone who could forge an over-long
    `X-Real-IP` could equally vary its first 45 characters.
- **`INSERT IGNORE` and NOT NULL.** See CR4-01. Nothing can be masked with today's code. A missing
  address is stored as `client_ip = ''` and `is_internal = 0` (external), which matches § 5.1.
- **`CURDATE()`, `ts` and time zone.** Both are evaluated in the same statement on the same
  connection. MariaDB fixes the statement's time at its start, so `CURDATE()` and
  `DEFAULT CURRENT_TIMESTAMP` read the same instant, even at midnight. Both use the session time
  zone `+05:30`, which `_connect_kwargs.init_command` sets.
  - The pool is built from the same kwargs, and DBUtils reconnects with them after `ping=1`, so
    a reconnected connection keeps IST.
  - `test_one_row_per_day_across_workers` asserts `sighting_day == ts.date()`.
- **When the cache remembers.**
  - After the insert returns, whether 1 or 0: yes (`:235`).
  - On a connect or insert exception: no. The process backs off 30 s and returns before
    `remember` (`:230–233`).
  - When the schema is down: no. It returns before the insert (`:213`).

  So BR1-01/BR2-01 hold. `test_skipped_while_down_and_written_once_back` and
  `test_a_failed_write_backs_off` still pass.
- **Logging the warning only when the row was written (decision 2).** This is not a regression of
  § 5.1 ("a warning once per sighting"). With A1 a sighting is one key per day across all workers,
  and the warning now fires exactly once per such sighting. Before A1 it fired once per worker
  per 10 minutes. The only gap is the missing test (CR4-02).
- **Test coverage against A1's "Where".** All present:

  | A1 asks for | Test |
  |---|---|
  | two-worker simulation (cache cleared) → one row | `test_one_row_per_day_across_workers` |
  | a different address → a second row | `test_another_key_is_another_row` (address case) |
  | a different outcome and detail → a second row | `test_another_key_is_another_row` (`denied_perm` case) |
  | a different detail → a second row | `test_another_detail_is_another_row` |
  | a rejected insert is remembered | `test_a_rejected_insert_is_remembered` (`results == [0]`, one row) |
  | pure hash | `TestSightingHash`: pinned value, `None` equals `""`, each part counts, no run-together |
  | migration | `test_migration_v10.py`: column types, NOT NULL, unique key columns in order |

- **The `test_worker.py` seed change.** The purge test is not weakened. `_log_row` still sets `ts`
  by age, and the purge still deletes by `ts`. The new columns are filled with
  `CURDATE() - INTERVAL n DAY` and `SHA1(UUID())`, which never collide. Both purge tests assert
  the same survivors as before.
- **The log stays append-only.** The only write paths to `access_log` are the hook's
  `INSERT IGNORE` (`access_control.py:189`) and the purge's age-based `DELETE`
  (`task_handlers.py:36`). No UPDATE was added, and no upsert (`ON DUPLICATE KEY UPDATE`) was
  used.

## Checked and found consistent

- **Migration v10 edited in place.** A1 allows this explicitly: v10 has only ever been applied to
  the disposable dev and test databases, and S013 is uncommitted. The coder dropped and re-ran it
  in both dev DBs; the green suite confirms the test DB has the new shape. Nothing in production
  has v10.
- **The table matches A1.** `sighting_day DATE NOT NULL`, `sighting_hash CHAR(40) NOT NULL`, and
  `UNIQUE KEY ux_access_log_sighting (sighting_hash, sighting_day)` agree with the brief's
  revised § 4.
- **The pure core stays pure.**
  - `sighting_hash` uses `hashlib` only, with no clock and no I/O.
  - `\x1f` as the separator, with `None` written as `""`, is exactly A1 rule 2.
  - `test_parts_do_not_run_together` guards against parts running into each other.
  - The `SightingCache` code is unchanged; only its docstring was revised, as A1 rule 4 says.
- **Concurrency.**
  - Concurrent `INSERT IGNORE`s on one unique key are race-free in InnoDB: the loser sees the
    duplicate and is ignored.
  - The connections are autocommit, so the winner commits at once, and the deadlock pattern of
    a rolled-back first inserter cannot arise.
  - Any deadlock or other error would raise, back off and leave the request untouched. That is
    the round-1 behaviour.
  - Ignored inserts may use up `BIGINT` auto-increment ids. This is harmless.
- **No regressions to rounds 1–3.** The hook's outer try/except, the before-schema check, the
  30 s back-off, the "auth_failed carries no username" rule, truncation, the viewer and the purge
  are unchanged. The suite is green.
- **The base pattern.** smtw-common's `SMTW-WebApp-Base.md` § Access log describes exactly this
  design (key, `sighting_day`, `sighting_hash`, unique index, `INSERT IGNORE`, cache only as a
  saver). One gap, for the planner and outside this repo's code: the base's **Columns** bullet
  does not yet list `sighting_day` / `sighting_hash`. The Yantra copy is still to be synced, as
  A1's "Where" notes.
- **The report.** The coder's four decisions are all listed under "Decisions taken", and none is
  an unreported departure. Decision 4 (the migration test) is outside A1's "Where" but is listed
  and justified.
- **Manual checks.** Every **important** check is present as an unticked box. Check 3's tightened
  wording is in the A1 section; the duplication is CR4-03.
- **Track.** Full, as the brief says.

## For the user's manual browser check

These are the important boxes of the impl report, unchanged except that A1 tightens check 3:

- IT admin from the plant, from mobile data and over the VPN; a manager on mobile data.
- Settings › Network shows your address, and the lock-out guard refuses a list that would exclude
  it.
- **Check 3, as A1 words it.** From a phone on mobile data:
  - Settings › Access log shows the carrier's address, not 10.24.0.18;
  - Settings › Network says "external";
  - both before the gate is trusted.
- Production: MariaDB ≥ 10.6, the worker starts and takes its lock, and the 02:30 purge is done
  the next morning.

A plain check that A1 adds: browse on a phone for more than 10 minutes. The Access log should
show **one** row for that session and address today, not one per worker and not one per
10 minutes.
