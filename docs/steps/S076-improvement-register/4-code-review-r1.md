```
Step: S076 — Improvement register
Doc: code-review
Round: 1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S076 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The register is built as the brief asks; the findings are 5 nits.

## Test runs

- Unit suites, `YANTRA_TEST_RUN=s076cr1 tooling/run-tests.bat`: all green: backend 4050 passed (187 s), frontend 362 passed, tooling 185 passed.
- `npx vite build` in `frontend/`: built; only the existing chunk-size warning.
- Browser: not re-run. No finding of mine needs a run. The coder's runs are the right ones and are recorded with
  their counts: the new spec on `phone-chromium` and `desktop-chromium` (7 passed, 1 skipped each), the whole
  Normal suite once (298 passed, 15 skipped; the router and `e2e/support/` changed), and
  `e2e/screens.spec.js --project=phone-webkit` once (9 passed; `e2e/support/` changed, the *Shared code* rule).

## Nits

- **CR1-01** (nit) `frontend/src/views/ImprovementRegisterView.vue:173-174`: a page opened from a link or a reload
  with a refused period (a 400 and no register yet) shows *Show this month* and *Show last month* disabled, so the
  user must retype both dates. Enable them when `periodError` is set and fall back to the URL's dates, or load
  once without `from` and `to` to get `today`.
- **CR1-02** (nit) `frontend/src/views/ImprovementRegisterView.vue:157-183`: on a 403 (and on the no-units line) the
  page still shows the From and To fields, the disabled month buttons and the help "Print in portrait, at 100 %".
  Hide the controls block when `forbidden` or `noUnits` is true, so the user sees only the plain line.
- **CR1-03** (nit) `backend/improvements.py:892-893`: `closed_by_name` and `by_lead` repeat the expression of
  `_closed` (`backend/improvements.py:656-664`). Reuse it (after the DROPPED check) or extract the "closed by the
  lead" test into one helper, so the two cannot drift.
- **CR1-04** (nit) `backend/tests/test_improvement_register_api.py:361-364`: the test named "printed_by is the
  reader's name" only checks a non-empty string. Assert it equals `world.person["name"]` (or the identity's name),
  as § 8.2 asks.
- **CR1-05** (nit) `backend/tests/test_improvement_register_api.py` (class `TestPeriod`): impl report § 5 decides
  "a bad period is a 400 before a site 404", but no test pins it. Add one case: `from` after `to` with `site_id`
  of another site → 400 on `from`.

## Checks against the orchestrator's list

- **`report:read`** (`backend/config_rbac.py:143-148`, `:216-217`): `("maint_engineer",)`, so the manager through
  `ROLE_INCLUDES`; not IT admin, not the supervisor; in `SITE_SCOPED`; the comment gives the reason (§ 5.7).
  `test_role_matrix` gains the key for engineer and manager only; `test_report_key` pins the holders, the
  `SITE_SCOPED` entry, and that every holder also holds `improvement:read` (D4). The API tests give 403 to
  operator, technician, supervisor, storekeeper and IT admin, and every active site to admin.
- **Unit scoping**: the site choices come from `accessible_unit_ids(cur, REPORT_KEY)` (active units of active
  sites, ordered by site code); every section reads with `u.site_id = %s AND unit_access_condition(cur,
  REPORT_KEY, "i.unit_id", "m.unit_id")`, the list's shape. A `site_id` outside the choices is 404 "Not found".
  The `units` line compares the reader's active units at the site with the site's active units; `None` covers
  admin. Tested: chosen units, a machine moved into the engineer's unit, a key holder with no active unit.
- **Figures against the brief and S070 / S072**:
  - the period: `date_arg` (DD-MM-YYYY or ISO, its 400), then `parse_period` with the defaults; bounds
    `from 00:00 <= t < to + 1 day 00:00`, compared with IST `DATETIME`s (§ 5.1);
  - started: by `created_at` in the period, every state, the display state now, the follow-up's serial;
  - open: the stored state decides open (`IMPROVEMENT_OPEN_STATES`), `display_state` the row, so an ended watch
    counts as *Ready to verify*; age from `created_at.date()` to IST today; bands at 30 / 90 / 180; a negative age
    is the first band; open and overdue counts in one grouped query (no N+1); `due_date < today` matches
    `overdue_days` (due today is not overdue);
  - overdue: open countermeasures on open improvements only (D8), `overdue_days(ACTION_OPEN, due, today)`, oldest
    due first; `owner_id` is `NOT NULL`, so the inner join to `people` drops no row;
  - closed: `CLOSED_STATES` by `closed_at` in the period; `by_lead` is `null` on *Dropped*, false for admin (no
    Team record); `closed_by_name` falls back to the login; `remark` is `close_remark` (both the remark and the
    drop reason); the follow-up through `_IMPROVEMENT_FROM`'s `fu` join (at most one row:
    `uq_improvements_follow_up`);
  - the share: `(200 w + v) // (2 v)` is `floor(100 w / v + 0.5)` in integers, so no float rounding; `None` with no
    verified close; drops stay out (D6).
- **One snapshot (D10)**: `register()` reads everything inside one `with transaction(conn), conn.cursor()` block:
  the choices, the unit count and the four sections. `transaction` calls `conn.begin()`, so the first plain read
  fixes one REPEATABLE READ view; the early return for no sites and the 404 inside the block commit or roll back
  cleanly. No lock, no write; the LOCK ORDER *Reads* line names the register.
- **400 before 404**: `date_arg`, `int_arg` and `parse_period` run before `get_db()`; `require_perm` gives 401/403
  first. The DB down gives 503 (`db_down` test).
- **The print page**: the `@page { size: A4 portrait; margin: 12mm }` rule is added on mount and removed on
  unmount, the controls are `.no-print`, `window.print()`, `loadSeq` makes the newest load win, `thead` repeats on
  paper and rows do not split, as `AssetListPrintView.vue`. The link carries both ends after the first load
  without a second load (`writtenPath`). The 400 keeps the last register with its own period; 403, 404 with
  *Show my first site*, 503 with *Retry* and the no-units line follow § 5.8.
- **The md-up button**: `ImprovementsView.vue` shows *Print register* for `report:read` holders with
  `d-none d-md-inline-block`, and opens `registerPath()` in a new tab as `printAssetList` does.
- **Words**: the state words come from `improvementStateLabel` (*Closed: it worked*, never "effective"); the
  headings, empty lines, column names, the share line and the refusals are the brief's text, short and plain
  (scope B). The age bands are tested word for word.
- **The router**: one route `/tickets/improvements/register`, name `improvement-register`, placed before
  `improvement-detail` (whose `:id(\d+)` would not match it anyway). It is no nav item, so `canOpenRoute` lets it
  open and the API's 403 is the gate, as for the other print pages.
- **e2e helpers**: `raiseFixed` gains `minutesAgo` (default 60, restore 50 minutes later, so the old callers are
  unchanged); `dropByApi` is new and no other helper drops by API. The whole suite and the WebKit screens run
  cover the change to `e2e/support/`.
- **Tests**: the core tests cover every § 8.1 case; the API tests cover § 8.2 (edges of the period, every open
  state, due today, cancelled and done countermeasures, the closed results and the share, the refusals, the site
  access); each § 8.5 check has a test that asserts what the user sees. The two `@device` tags follow the rule (a
  desktop-only button, a fit check); the paper test is untagged.
- **Docs**: Plan.MD § 1, § 3, § 4.6 and § 6, the glossary row in `Maintenance-Philosophy.md`, device-checks row 55;
  no schema change (no migration). `.claude/CLAUDE.md` is left by instruction, with the proposed text in the report.
- **Manual checks**: every § 8.5 check is `[auto]` with its test; the important paper check is an unticked box and
  device-checks row 55.

## Manual browser check for the user

- Device-checks row 55 (important, IT Admin): print one month's register on A4 portrait at 100 % and check the
  columns, the wrapping, the repeated header row and the review lines on paper.

## Checked and found consistent

Scope (everything in § 1 built, nothing beyond it; the § 5 decisions are listed), the stale-check table of the
report, security (the route is gated with the right key, no actor from the client, SQL only with placeholders and
code constants), the pure core (no DB, no clock, only `improvements_core` imported), the DB-down path, and the
writing style of the report (scope A).

## Feedback

- waste: the diff of the step's existing files came out at 66 KB because the `docs` path also pulled in the
  step's own impl report; I re-read it in pieces (`step_snapshot.py diff S076 -- … docs`, 2 reads).
- none other.
