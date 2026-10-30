```
Step: S076 — Improvement register
Doc: impl-report
Author: Coder (Sonnet)
Date: 30-10-2026
Baseline: 32eb122 + uncommitted S066–S075, S077
```

# S076 — Implementation report

## 1. What was built

The printable improvement register (R05.10): one page per site and period, on screen and on A4 portrait, opened in a
new tab from a **Print register** button on the Improvements list.

- **Page** `/tickets/improvements/register` ("Improvement register"). Controls (left off paper): *Site* (only with more
  than one site), *From*, *To*, *Show this month*, *Show last month*, *Print*.
- **Four sections:** *Started in the period*; *Open now* (a count table of *Analysing*, *Actions open*, *Watching*,
  *Ready to verify* by age 0–30, 31–90, 91–180, over 180 days, then the list oldest first with open and overdue
  countermeasures); *Countermeasures overdue now*; *Closed in the period* (*Closed: it worked*, *Closed: did not work*,
  *Dropped*, the share that worked, the list with who closed it, ", the lead" on a verified close by the lead, the remark
  and the follow-up).
- **Paper:** header (site, period, units when the reader sees only some, "Printed on … by …") and the footer lines
  "Reviewed by", "Date", "Decisions and actions".
- **Key `report:read`** (engineer, so manager; site-scoped; not IT admin, not the supervisor), new in `config_rbac.py`.
- **API** `GET /api/improvements/register?site_id=&from=&to=`, figures from the pure core
  `backend/improvement_register_core.py`.
- No migration.

## 2. How it works

- **Core** (`improvement_register_core.py`, pure): `default_period` fills a missing end (both absent: today's month;
  one given: the rest or start of its month); `parse_period` refuses `from` after `to` (field `from`) and more than 366
  days (field `to`); `period_bounds` gives `start <= t < end`; `age_days`, `age_band` (0_30, 31_90, 91_180, over_180;
  a negative age is the youngest band); `open_summary` (every state and band present, `ready_to_verify` its own row);
  `worked_share` (whole percent, half up, `None` without a verified close; dropped ones stay out) and `closed_summary`.
- **Route** (`improvements.py`, `register`): `@require_perm("report:read")`; dates by `date_arg`; period from the core
  (400 with its field); then one `transaction(conn)` block, so the five reads share one REPEATABLE READ snapshot (D10).
  `_register_choices` lists the active sites with an active unit among `accessible_unit_ids(cur, "report:read")`;
  `site_id` absent gives the first, one outside the choices gives 404; no choices gives 200 with `sites: []`,
  `site: null`. Each section reads through `unit_access_condition(cur, REPORT_KEY, "i.unit_id", "m.unit_id")` and the
  existing `_IMPROVEMENT_FROM` joins. The open list asks for the countermeasure counts in one grouped query. Overdue
  and open use the stored state (`IMPROVEMENT_OPEN_STATES`); rows show `display_state`.
- **Page** (`ImprovementRegisterView.vue`): loads with the link's `site_id`, `from`, `to`; after the first load it
  writes both ends of the period into the link and does not load again for its own write (`writtenPath`). A 400 shows
  its message under the fields and keeps the register on screen with its own period. 403, 404, 503/no connection and
  `site: null` show the lines of § 5.8. `@page { size: A4 portrait }` is added on mount and removed on unmount, as
  the asset list does.
- **Words:** `improvementRegister.js` holds `monthPeriod` (string arithmetic only), `periodText`, `AGE_BAND_LABELS`,
  `registerPath`, `workedShareText`, `actionsText`; state words come from `improvementStateLabel`.

## 3. Stale brief check (brief § 9)

Every name the brief cites was checked against the tree. Differences, all followed from the code:

| Brief | Tree | What I did |
|---|---|---|
| § 5.5/5.6 add `LEFT JOIN people vb`, `fu`, `fo` | `_IMPROVEMENT_FROM` (S072) already joins `clp` (closed-by person, by username), `fo` and `fu` | No extra joins; the columns use `clp.id`, `clp.name`, `fo`, `fu`. `_machine` and `_ref` are reused. |
| `api_common.date_arg` at `:166` | at `:166` | none |
| `printAssetList` at `EquipmentView.vue:389` | function at `:313`, button at `:389` | pattern followed |
| `raiseFixed` gains `minutesAgo` | not there | added (default 60; restore 50 minutes after it) |
| helpers to add a countermeasure and to drop by API "if S071 and S073 have not added them" | `addActionByApi` (S071) exists; no drop helper | added `dropByApi` only |
| `formatDate` "new in S073", `actionKindLabel` "new in S071", `watchEndDate` | all exist in `utils/` | `formatDate`, `actionKindLabel` reused; `watchEndDate` not needed |
| `display_state`, `CLOSED_STATES`, `READY_TO_VERIFY`, `IMPROVEMENT_OPEN_STATES`, `overdue_days`, `by_lead`, v39 columns | all as the brief says (`overdue_days(state, due_date, today)` takes the state first) | used as written |
| `report:read` "if R03.14 created it first" | not in `config_rbac.py` (Plan § 3's table row only) | created here |
| `improvement_events` | exists (S072) | not used (D2: open and overdue are "now") |

No difference changes the design, so no question went back.

## 4. Files touched

Backend: `backend/config_rbac.py` (the key and its `SITE_SCOPED` entry), `backend/improvement_register_core.py` (new),
`backend/improvements.py` (the route, six helpers, imports, the LOCK ORDER *Reads* line),
`backend/tests/test_improvement_register_core.py` (new), `backend/tests/test_improvement_register_api.py` (new),
`backend/tests/test_rbac.py` (`test_report_key`, `test_role_matrix`).

Frontend: `frontend/src/views/ImprovementRegisterView.vue` (new), `frontend/src/utils/improvementRegister.js` (new),
`frontend/src/router/index.js` (the route), `frontend/src/views/ImprovementsView.vue` (the button),
`frontend/tests/improvementRegister.test.js` (new), `frontend/e2e/improvement-register.spec.js` (new),
`frontend/e2e/screens.spec.js` (one row), `frontend/e2e/support/improvements.js` (`raiseFixed` option, `dropByApi`).

Docs: see § 7. Status lines: the brief header and `docs/steps/INDEX.md` (In code review).

## 5. Decisions taken

- **`units` holds `SITE.UNIT` codes** ("SMTW.MCC1"), as the paper example in the brief shows, though § 5.2 says "the
  codes". The API test pins it.
- **`workedShareText` returns the whole line**: the three counts, then the share or, without a verified close, "No
  improvement was verified in this period." after the counts (the brief names the sentence only).
- **The period is parsed before the database is read**, so a bad period is a 400 before a site 404; `printed_by`,
  `today` and the empty sections are in the answer even when `sites` is empty.
- **The fields show the answer's period and site** after each load (the link is written asynchronously); on a 400 they
  keep what the user typed.
- **The *Show this month / last month* buttons are disabled until the first answer** (they use the server's `today`).
- **No extra count in the *Closed* heading**; the counts are in the line below it.
- **`_register_choices` uses active sites and active units only**, as `accessible_unit_ids` returns active units.
- **A `Total` row** closes the count table (the brief's `band_totals`); the print button shows only when a site loaded.
- **Tests make improvements through `world.make`** (start route, then raw `UPDATE`); a countermeasure's state is
  written last, because adding one settles the state from the data (no root cause gives *Analysing*).

## 6. Not done, deferred, assumed

- Not done (out of scope per the brief): Excel export, charts, trends, filters by unit, lead or state.
- The snapshot (D10) is not tested by a race; the code review checks it by reading `register()` (one
  `transaction(conn)` block around every read).
- Assumed: the clause numbers of the next ISO 9001 edition and ISO 55001 stay *to verify*, as the brief says.
- The e2e specs do not close an improvement as *it worked* or *did not work* (30-day watch): the API tests cover them.

## 7. Docs updated

- `docs/Plan.MD`: § 1 *Improvement (RCA)* row ("Register … (S076)"); § 3 a paragraph on `report:read` after the
  improvement keys' paragraph (the table row existed); § 4.6 the bullet *Improvement register (S076)*; § 6 one sentence
  in the *Improvements* bullet.
- `docs/steps/device-checks.md`: row 55 (paper, **important**).
- `docs/Maintenance-Philosophy.md` § 12: a row *Management review*.
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `.claude/CLAUDE.md`: not edited (instruction); the proposed text is below.
- `backend/example_secrets_app.py`, `docs/Keycloak.md`: none, because no secret, role, client or token claim changed
  (the key is a Yantra-side key; the roles are unchanged).

## Proposed CLAUDE.md changes

In `.claude/CLAUDE.md` § SMTW-Review, bullet *Browser tests*, the spec-to-step map: add `improvement-register` S076, after
`equipment …`/`readings …` as fits (for example: `…, \`readings\` S039/S040/S050/S051/S064, \`improvement-register\` S076,
\`asset-list\` …`). No other change.

## Shared docs

None (no worktree).

## Tests run

- Backend, first: `tests/test_improvement_register_core.py` 34 passed; `test_improvement_register_api.py` 32 passed;
  `test_rbac.py` 63 passed.
- Final full run, `YANTRA_TEST_RUN=s076c1 tooling/run-tests.bat`: backend 4050 passed, frontend 362 passed, tooling
  185 passed, all green.
- `npx vite build` in `frontend/`: built, only the existing chunk-size warning.
- Browser, new spec alone: `improvement-register.spec.js` on `phone-chromium` (7 passed, 1 skipped), then on
  `desktop-chromium` (7 passed, 1 skipped; the phone-only fit test skips there, the desktop button test skips on the phone).
- The whole suite at Normal once (the router and `e2e/support/improvements.js` changed): 298 passed, 15 skipped, 3.0
  minutes, no failure; it included `improvements.spec.js` and `screens.spec.js`, so no extra targeted run was needed.
- `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit` once (a file of `e2e/support/` changed): 9 passed.
- Failures met while writing the new spec, fixed in my own code: the page left the *To* field empty after the first load
  (the link is written asynchronously, so `readQuery` read the old link; the fields now come from the answer), and the
  expected 400 / 403 needed `allowFailedRequest`.

## Manual checks

- [auto] The engineer sees the register of this month: the improvement started, open with its age, and its overdue countermeasure — frontend/e2e/improvement-register.spec.js::S076: the engineer sees the register of this month: the improvement started, open with its age, and its overdue countermeasure
- [auto] The dropped improvement shows under Closed in the period with its reason (and no ", the lead") — frontend/e2e/improvement-register.spec.js::S076: the dropped improvement shows under Closed in the period with its reason
- [auto] The manager picks BRICKS and Show last month; the link and the period line change, a reload keeps them — frontend/e2e/improvement-register.spec.js::S076: the manager picks BRICKS and Show last month; the link and the period line change
- [auto] A start after the end is refused under the period fields, and the sheet stays — frontend/e2e/improvement-register.spec.js::S076: a start after the end is refused under the period fields, and the sheet stays
- [auto] The operator has no Print register button and the address shows a plain line, no Retry — frontend/e2e/improvement-register.spec.js::S076: the operator has no Print register button and the address shows a plain line, no Retry
- [auto] On paper the controls are left out and the sheet has the review lines — frontend/e2e/improvement-register.spec.js::S076: on paper the controls are left out and the sheet has the review lines
- [auto] Print register on the Improvements list opens the register in a new tab (desktop) — frontend/e2e/improvement-register.spec.js::S076: Print register on the Improvements list opens the register in a new tab
- [auto] The register fits a phone with no sideways scroll — frontend/e2e/improvement-register.spec.js::S076: the register fits a phone with no sideways scroll
- [auto] Every route opens: `/tickets/improvements/register` shows the heading for the engineer and the manager — frontend/e2e/screens.spec.js::every screen opens as engineer / as manager
- [ ] **Important** (device-checks row 55): Tickets › Improvements › **Print register**, print one month's register on A4 portrait at 100 % ("Actual size"). On the paper: no column is cut at the right edge; the *Remark* and *What will be done* columns wrap inside their cells; on a second page the table's header row repeats; the "Reviewed by", "Date" and "Decisions and actions" lines are on the sheet with room to write. Done by IT Admin.

## Feedback

- hindrance: a Bash heredoc holding a Python script with backslash escapes or a `'` in the text was mangled or refused (three
  scripts rewritten, about 5 min); the README's "Write the script to a file" rule is right but the failure was silent
  until the script ran (`scratch/s076_edit3.py`, `s076_docs.py`).
- hindrance: the working copies of the `.md` docs are CRLF while the index is LF, so an edit script must keep each file's
  line ending or it rewrites every line (found by `git ls-files --eol`; `docs/Plan.MD`, `device-checks.md`).
- idea: the brief's § 3 anchors by line number (`EquipmentView.vue:389`, `api_common.py:166`) were off by a few lines
  again after S070–S075; naming only the function would save the stale check a lookup.
- rule: the orchestrator's prompt names the run `s076c1` for the unit suites but the targeted backend runs also needed one;
  I reused it for all, which is safe only while no second window runs the same name.

## Fix rounds

### Round 1

All five findings are nits; all fixed.

- **CR1-01 Fixed.** `ImprovementRegisterView.vue`: the two month buttons no longer have `:disabled="!result"`. `showMonth` uses `result.today`, and with no register yet an IST date taken from the clock by plain UTC arithmetic (`istToday`, no browser zone). New test `S076: Show this month works on a page opened with a refused period` (a link with from after to; 400, no sheet; one click shows this month). Fails without the fix: the button is disabled, so the click never loads the sheet; passes with it.
- **CR1-02 Fixed.** The controls block (fields, month buttons, Print, help) shows only when `!forbidden && !noUnits`. The operator test now asserts no From field, no *Show this month* and no "Print in" help. Fails without the fix: `getByLabel("From")` count 1, expected 0; passes with it. (The 404 line keeps the controls: its *Show my first site* button sits in the alert and the site choice is still useful.)
- **CR1-03 Fixed.** `_register_closed` selects `clp.id AS closed_by_person_id, clp.name AS closed_by_name` (the names `_closed` reads) and calls `_closed(plain, row)` for `closed_at`, `closed_by_name`, `by_lead` and `remark`; only the Dropped rule (`by_lead` None, D6) stays in the register. Behaviour unchanged: the existing closed-section API tests pass (33 passed).
- **CR1-04 Fixed.** The test asserts `printed_by == "Test maintenance_team"`, the login's name from the test token (`world.person["name"]` is the Team record's name, which the route does not use). Fails with a wrong value (`"Nobody"`), passes with the right one.
- **CR1-05 Fixed.** `TestPeriod.test_a_bad_period_is_a_400_before_a_site_404`: from after to with `site_id=999999999` gives 400 on `from`. No red run possible: it pins behaviour already in the code (the period parses before `get_db()`); swapping the order would need an edit of the route only to see it fail.

Tests run: `YANTRA_TEST_RUN=s076f1` `test_improvement_register_api.py` and `test_improvement_register_core.py` 67 passed; `npx vite build` built (only the chunk-size warning); `tooling/run-e2e-tests.bat e2e/improvement-register.spec.js e2e/screens.spec.js` 26 passed, 3 skipped (the device skips). No frontend unit file changed. No docs touched, because the round changes no documented behaviour. The full suite was not re-run (fix round, targeted runs only).

#### Feedback

- none
