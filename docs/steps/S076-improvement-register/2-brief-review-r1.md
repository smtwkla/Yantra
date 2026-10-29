```
Step: S076 — Improvement register
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R05.10
```

Reviewed against: 32eb122 + uncommitted S066, S067, S068, S069, S070 (being coded). S071–S074 are approved briefs, not code: their names (`display_state`, `CLOSED_STATES`, `READY_TO_VERIFY`, the v39 columns, `actionKindLabel`, `formatDate`) were checked against the briefs' text.

**Verdict: no `blocker` or `major` finding is open.** Five `minor` findings and a list of nits. None needs KLA's decision; § 9 Q1 and Q2 are **not defining** (reasons under *Checked and found consistent*). Full track, round 1. Facts file: `scratch/brief-facts-S076.md`, used.

## Findings

### BR1-01 — minor — A second date parser beside `api_common.date_arg`

**Problem.** § 5.1 plans `parse_period` to parse `from` and `to` itself (`date.fromisoformat`, ISO only, the message `LABOUR_DATE_FORMAT` "Enter the date as YYYY-MM-DD"). The repo already has `api_common.date_arg(name)` (`backend/api_common.py:160-176`), which the access log uses for the same two arguments (`backend/settings.py:311`): it accepts DD-MM-YYYY (CLAUDE-COMMON: the preferred format) and ISO, trims, treats empty as absent, and answers 400 with the field. The access log also makes `to` inclusive the same way (`ts < to + 1 day`, `settings.py:319-322`).

**Why it matters.** Two parsers for one kind of argument drift (one takes DD-MM-YYYY, the other refuses it), and a planned duplicate is what the design check asks to avoid. The core stays pure either way: the rules that are the register's own (the defaults, `from` after `to`, the 366-day bound, the bounds as datetimes) are not in `date_arg`.

**Options.**
- (a) **Recommended.** The shell reads `date_arg("from")`, `date_arg("to")` (a 400 for text that is not a date, `date_arg`'s message); the core's `parse_period(from_date, to_date, today)` takes dates or None and keeps the three register rules and their messages. § 5.1's table loses its first row; § 8.1 and § 8.2 test the bad-text case through `date_arg` (one API test) and the rest in the core.
- (b) Keep the brief's parser, and accept DD-MM-YYYY in it too. Still two parsers.

### BR1-02 — minor — A one-sided period defaults against today's month

**Problem.** § 5.1: `from` absent → the first day of today's month; `to` absent → the last day of today's month. The two defaults are independent of each other, so `?to=2026-03-15` alone gives `from` = 01-10-2026 and the refusal "The start must be on or before the end"; `?from=2025-06-01` alone gives a period to 31-10-2026, 518 days, refused "Choose a period of up to one year". § 5.8 also does not say whether the page writes both dates into the URL once it has loaded, or only the one the user changed (`router.replace` with the URL's `site_id`, `from`, `to` "only those present").

**Why it matters.** The coder has to decide what a one-sided URL means; a user who types one date gets a refusal that names the other date.

**Options.**
- (a) **Recommended.** Default the missing end from the given one: `from` alone → `to` = the last day of `from`'s month; `to` alone → `from` = the first day of `to`'s month; both absent → today's month. And § 5.8 says the page always writes both `from` and `to` to the URL after the first load (the presets and a change of either field), so a reload and a shared link carry a full period. § 8.1 gains the two one-sided cases.
- (b) Keep the defaults and only add the "both dates always in the URL" rule; a one-sided URL is then only a hand-typed one.

### BR1-03 — minor — "Verified by" and ", the lead" on a dropped row

**Problem.** § 5.6 and § 5.8 put every closed state in one list with the columns *Verified by* (", the lead" when `by_lead`) and *Remark*. For a `dropped` row, `closed_by` is the engineer who dropped it (S072 § 5.7 *Drop*), not a verifier, and D6 says a drop is not a verified result; `by_lead` = `vb_id == lead_id` is computed for it too, so the paper can read "Verified by Priya, the lead" for a duplicate that was dropped.

**Why it matters.** The lead mark exists so the review sees a self-verification (S072 § 2, ISO 27001 A.5.3); on a drop it says nothing true. The column name tells the reader the wrong thing about a third of the rows.

**Options.**
- (a) **Recommended.** Head the column "Closed by"; `by_lead` is `null` for a `dropped` row and the mark ", the lead" shows only on `closed_effective` and `closed_not_effective`. The *Result* column already says "Dropped". § 8.2's closed test gains "a dropped row has `by_lead` null".
- (b) Keep "Verified by" and leave the cell blank on a dropped row (the dropper's name is then nowhere on the paper).

### BR1-04 — minor — What the page shows beside a period refusal

**Problem.** § 5.8's table says a 400 shows "the message under the period fields, `role="alert"`; the controls stay; no Retry". § 8.5's test title adds "and the sheet stays". The brief does not say whether the last good register stays on screen, is dimmed, or is cleared; the two places read differently.

**Why it matters.** The coder would decide alone, and the test already assumes an answer. A sheet left on screen under a URL with a bad period is still true to itself only if its header names its own period, not the URL's.

**Options.**
- (a) **Recommended.** The last loaded register stays as it is, not dimmed, with its own `period` in its header (the header is rendered from the answer, never from the URL); the message sits under the fields. Say so in § 5.8 and keep the test title.
- (b) Clear the sheet and show only the message (one fewer state; the user loses the register until the date is fixed).

### BR1-05 — minor — The e2e set-up needs a back-dated raise the helpers cannot make

**Problem.** § 8.5 sets up "a breakdown raised 3 days back (`istLocal(3 * 24 * 60)`) and restored", but `raiseFixed` (`frontend/e2e/support/improvements.js:12-22`) fixes `occurred_at: istLocal(60)` and the restore at `istLocal(10)`; § 3 lists only two new helpers (add a countermeasure, drop). The restore time must also lie after the back-dated `occurred_at`, and the countermeasure's due date must be on or after the problem's date (`due_date_error`, `backend/improvements_core.py:405`): the ticket's own date, as the brief says, passes.

**Why it matters.** Without a stated change the coder either widens `raiseFixed` or writes a third helper; the overdue test is the step's main browser check.

**Options.**
- (a) **Recommended.** `raiseFixed` gains an option `minutesAgo` (default 60) for `occurred_at`, with the restore at the same back-dated time plus the fix (both inside the 7-day back-dating); § 3 names it.
- (b) A new helper `raiseFixedDaysAgo(machineId, description, days)`.

## Nits

- **BR1-06** (nit) § 5.8 controls: `"This month"` and `"Last month"` are buttons that do not start with a verb (scope B). Either `"Show this month"` / `"Show last month"`, or make them a two-way choice (radio-style segmented buttons) and say so.
- **BR1-07** (nit) § 1 item 3, D11: ISO 9001 § 9.3.3 asks for decisions **and actions**; make the third line "Decisions and actions".
- **BR1-08** (nit) § 2 ISO 9001 § 7.5.3: "a record shows who made it and when" is § 7.5.2 (identification and description); § 7.5.3 is that the record is kept and protected. Cite § 7.5.2 for the "printed on … by …" line, or keep § 7.5.3 with its own plain words (the register is generated from protected records, not typed again).
- **BR1-09** (nit) § 5.2: `accessible_unit_ids` is at `backend/equipment.py:341` and `unit_access_condition` at `:349` (the brief says 338 and 346).
- **BR1-10** (nit) § 6: say how `printed_at` is made (as `asset_list`'s: `datetime.now(IST).isoformat(timespec="seconds")`, `backend/equipment.py:777`), so the header's `formatDateTime` gets the same shape as the asset list's.
- **BR1-11** (nit) § 5.6 `closed_by_name` "else the login" against § 5.7 "never a login": say the fallback shows only when no Team record has that login (admin), as S067's `created_by_name`.
- **BR1-12** (nit) § 5.8 tables: say the *Started* and *Closed* columns are dates only (`formatDate`), and what the *Countermeasures* cell shows with none open ("none", not "0 open, 0 overdue").
- **BR1-13** (nit) § 3 `monthPeriod(todayIso, monthsBack)`: say it works on the string's year and month, never through `new Date()` and the browser's zone (as S073's `watchEndDate`), so a laptop west of UTC does not shift the month.
- **BR1-14** (nit) header and § 3: "S071–S075 approved or in review" and "coded after S075" — S075 is `Draft` in `INDEX.md` and its folder holds no brief yet. Say "after S074, and S075 when it is approved".

## Checked and found consistent

- **`report:read` (D3, § 5.7).** Plan § 3's table gives it to engineer and manager only (`docs/Plan.MD:137`); R03.14 names the same holders and `SITE_SCOPED` (`docs/roadmap/R03-pm.md:342`); the supervisor's row says "more reports later" (`Plan.MD:82`). `("maint_engineer",)` with `ROLE_INCLUDES` gives the manager and nobody else; IT admin is not in the tuple. The key in `SITE_SCOPED` follows `config_rbac.py:173-174` ("every later … report key joins this list"). `require_perm` checks the union, then the site choice is built from `accessible_unit_ids(cur, REPORT_KEY)` (`user_unit_ids` asserts the key is in `SITE_SCOPED`, `auth_utils.py:478`): the RBAC deviation is followed. `test_role_matrix` (`test_rbac.py:219`) breaks for the two roles as the brief says.
- **The unit scoping (D4, § 5.2).** `unit_access_condition(cur, key, "i.unit_id", "m.unit_id")` is the improvements list's predicate (`improvements.py:192-193`); `accessible_unit_ids` returns active units or `None` for admin; an empty set is "no access", which the brief maps to `sites: []`. The 404 for a site outside the choices matches the readings sheet (`meters.py:452-465`, "Not found" for an unknown, inactive or unit-less site). The `units` line keeps a partial register honest.
- **The figures (D2, D5–D8).** Open = the stored state in `IMPROVEMENT_OPEN_STATES` (S072 § 5.1, BR1-03 there); the row = `display_state(state, watch_from, watch_days, now)` (S072 § 5.2). Overdue = `due_date < today`, S070's `overdue_days` (`improvements_core.py:433-438`) and S074's scan (`i.state IN` the open states, S074 § 5.2). Closed = `CLOSED_STATES` by `closed_at`; `follow_up` through the unique `follow_up_of_id` (one row at most, `uq_improvements_follow_up`); `by_lead` as S072 § 5.8. `worked_share` leaves drops out, with the counts beside it. The period bounds `start <= t < end` with `end` = the day after `to` match the access log. IST: every `DATETIME` is IST through `SET time_zone = '+05:30'` (`local_db.py:1353`); `_now()`/`_today()` are IST (`improvements.py:174-181`).
- **The snapshot (D10, § 5.9).** `transaction(conn)` begins a transaction on an autocommit pool connection (`db_helpers.py:42-55`); under REPEATABLE READ the four reads share the first read's snapshot; `current_memberships` reads through the same connection (`auth_utils.py:338-355`).
- **§ 9 Q1 ("as of now") — not defining.** Nothing is stored, so the choice can change later without a migration; the paper prints the date and says "now" in both headings; the past state would need an `improvement_events` replay that S072 § 4.1 says is incomplete before v39. The proposal is the simpler one.
- **§ 9 Q2 (the share) — not defining.** It is a display line with its counts beside it; the brief says it is a local measure, not an SMRP KPI, and MTBF/MTTR stay in phase 5. With small counts (1 of 1 = 100 %) the counts on the same line keep it honest.
- **Standards (§ 2).** ISO 9001 § 9.3.2 c) 4) ("nonconformities and corrective actions" as a review input), § 9.3.3 (evidence of the review's results), § 10.3, § 10.2.1 d), ISO 55001 § 9.3 (*to verify*), TPM focused improvement, ISO 27001 A.5.15 and A.5.3 are named and explained in plain words, and the register follows each as stated. SMRP: correctly not claimed. One nit on § 7.5.3 (BR1-08).
- **The print page (D1, D12, § 5.8).** `AssetListPrintView.vue` is the pattern: the `@page` rule added on mount and removed on unmount (`:80-87`), `.no-print` controls, `loadSeq`, `watch(route.fullPath)`, `thead { display: table-header-group }`, `tr { break-inside: avoid }`; the app's nav is `no-print` (`App.vue:60-71`). The button follows `"Print asset list"` (`EquipmentView.vue:389`, `d-none d-md-inline-block`, `window.open` of `router.resolve(...)`). The route `/tickets/improvements/register` cannot clash with `:id(\d+)`.
- **Use on the floor.** A desk task: list → one button → new tab → *Last month* → *Print*; the site select shows only to a two-site user, as the readings sheet; the no-Team-record state renders `NO_UNITS_TEXT`; the 403 is a plain line, not a 403 page; empty sections keep their heading with one line each; the 404 offers a way out (`"Show my first site"`). Nothing is asked that could be defaulted.
- **Tests (§ 8).** The e2e seed gives the manager SMTW and BRICKS and the engineer SMTW only (`tooling/e2e/seed_e2e.py:38-44`), so the site tests are possible; the operator (MCC2) has no `report:read`. The limit on closed results in e2e is real: the watch is 30 days at least and a `done_at` goes back only to the problem's time, which the 7-day back-dating bounds; the API tests cover them with `db_rows` writes that keep S072's CHECKs true. The `@device` tags are right: the button test runs where the button shows (desktop); the no-sideways-scroll test is a layout check; the print-media test is untagged as S015's. The `screens.spec.js` row is consistent with the key's holders.
- **The device check (§ 8.6).** Paper from a printer is a kind the settings name; marked **important**; account, network and where are given; IT Admin named. Nothing on the device list that a browser could judge.
- **Docs (§ 3).** Plan § 1's R05 row already says "**Register:** printable, in R05" (`Plan.MD:30`); `docs/Maintenance-Philosophy.md` has no *Management review* glossary row yet; no migration, so the schema docs are untouched.

## Feedback

- waste: the facts file matched `/api/improvements/register` to `test_readings_api.py` and `readings.spec.js` "by its last segment `/register`" (the readings register, S050); checking that it was a false match cost one read of `meters.py` (`scratch/brief-facts-S076.md:60`).
- hindrance: the S072 brief (909 lines) does not fit one Read; the sections S076 relies on (§ 5.1, § 5.2, § 5.8, D13, the Review log) needed a second pass with grep (about 3 minutes).
- idea: `brief_facts.py` could list the `api_common` argument helpers (`int_arg`, `enum_arg`, `date_arg`) whenever a brief's § 6 names query arguments; BR1-01 would have been visible in the facts file.
