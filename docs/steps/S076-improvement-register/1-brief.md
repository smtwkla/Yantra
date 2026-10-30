```
Step: S076 — Improvement register
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: 32eb122 + uncommitted S066–S070; S071–S075, S077 coded before S076
Status: Gate B 30-10-2026 (snapshot a1ed355; verify review r2 clean) — approved 30-10-2026 by KLA (delegated)
From: R05.10
```

# S076 — Improvement register

## 1. What will be built

R05.1–R05.4 give each improvement its problem, analysis, countermeasures and verified close
(S067–S073). Nothing yet shows **all of a site's improvements together**, so the monthly review
cannot see what was started, what is stuck, what is late and what worked. **R05.10 adds the
register** (Q10.1 a: build it in R05, printable): one page per site and period, on screen and on
A4 paper, for the management review (ISO 9001 § 9.3, § 10.3; § 2).

1. **A print page** `/tickets/improvements/register` (title "Improvement register"), opened in a
   new tab from a button `"Print register"` on the Improvements list (D1). Its controls: the site
   (`"Site"`, only when the user has more than one), the period (`"From"`, `"To"`, and the buttons
   `"Show this month"`, `"Show last month"`), and `"Print"`. The controls are left off the paper.
2. **Four sections**, two for the period and two for the day it is printed (D2):
   - **Started in the period**: every improvement started between *From* and *To*, with its state
     now; a follow-up of a *did not work* close says so.
   - **Open now, by state and age**: a count table (rows *Analysing*, *Actions open*, *Watching*,
     *Ready to verify*; columns by age 0–30, 31–90, 91–180, over 180 days) and the list of open
     improvements, oldest first, with their open and overdue countermeasures.
   - **Countermeasures overdue now**: every open countermeasure past its due date on an open
     improvement, most days late first, with its owner.
   - **Closed in the period**: the counts *Closed: it worked*, *Closed: did not work* and
     *Dropped*, the share that worked, and the list with who verified (", the lead" when the lead
     did, S072 § 2), the remark or reason, and the follow-up's serial.
3. **The header and footer on paper**: "Improvement register", the site, the period, the units
   when the reader does not see all of the site's units, "Printed on … by …", and the lines
   "Reviewed by", "Date" and "Decisions and actions" for the review's record (ISO 9001 § 9.3.3; D11).
4. **The key `report:read`** (Plan § 3): engineer, so the manager; site-scoped; not IT admin. It is
   new in `config_rbac.py` with this step, or with R03.14 if that step goes first (D3).
5. **The API** `GET /api/improvements/register?site_id=&from=&to=` (§ 6), all figures computed by a
   pure core (`backend/improvement_register_core.py`) from plain rows (CLAUDE-COMMON, *Pure core,
   thin shell*).

**After S076:** in the first week of November the manager opens Tickets › Improvements, presses
`"Print register"`, presses *Show last month* and prints October's register for SMTW: IM-2026-10-001 is
*Watching*, one countermeasure is 4 days late, nothing has closed yet.

### Out of scope

- Excel export and the dashboard (Plan § 4.6; R05.10 leaves them for later).
- A chart, trends across months, MTBF before and after (the verify card of S073 shows one
  improvement's figures; phase 5 reports).
- The state as it stood at the period's end (D2): the open and overdue sections are always "now".
- The loss (downtime) of each improvement on the register; the list page already shows it.
- A *Reports* menu item or page; R03.14 adds its own report on *PM* (D1).
- The *Suggested* list (R05.8, deferred), lessons (R05.6), who was shown a lesson (R05.7,
  deferred).
- A filter by unit, lead or state on the register (one site, one period).

## 2. Standards and practice

- **ISO 9001:2015 § 9.3 Management review.** In plain words: top management looks at how the
  quality system is doing at planned times, and keeps a record of what it decided. **§ 9.3.2 c) 4)**
  names "nonconformities and corrective actions" as an input to that review. The register is that
  input for maintenance: what was started, what is still open, what is late, what worked. **§ 9.3.3**
  asks to keep documented information as evidence of the review's results: the printed register
  with the "Reviewed by / Date / Decisions and actions" lines, signed, is that evidence (D11). Clause letters as
  the 2015 edition; the next edition's numbers are *to verify* (R05 § Standards).
- **ISO 9001 § 10.3 Continual improvement.** In plain words: the organisation keeps making things
  better, using its analysis and the review's outputs. The register shows whether improvements
  get finished and whether they work (the share *it worked*), so the review can decide where to
  push.
- **ISO 9001 § 10.2.1 d)** (as S072 § 2). In plain words: check whether the action worked. The
  register shows the result of each check (*it worked*, *did not work*), in ISO's terms *effective*
  and *not effective* in the API codes (`closed_effective`, `closed_not_effective`; S072 D13).
- **ISO 55001 § 9.3 Management review** (numbers differ between the 2014 and 2024 editions: *to
  verify*). In plain words: the same review for the asset-management system. The register serves
  both.
- **TPM — focused improvement** (*Kobetsu Kaizen*). In plain words: the team works through a list of
  chronic losses, and the list is visible: each theme, its stage and whether it worked (the
  "activity board"). The register is that list on paper. Ages show themes that have stalled.
- **SMRP.** No SMRP metric matches "share of improvements that worked". This register defines a
  local measure (§ 5.5) and does not call it an SMRP KPI. MTBF and MTTR stay for phase 5 (Plan
  § 4.6).
- **ISO 27001 A.5.15** (access control). In plain words: give each person only the rights their work
  needs. The register goes to engineers and managers of the site, who run the review (Plan § 3).
  **A.5.3** (segregation of duties): the closed list marks a close by the lead, the departure
  S072 § 2 recorded, so the review sees it.
- **ISO 9001 § 7.5.2** (creating and updating records). In plain words: a record says what it is,
  who made it and when. The paper names the site and period and says when and by whom it was
  printed. **§ 7.5.3** (control of records): records are kept and protected; the register is
  generated from those protected records, never typed a second time (as Plan § 4.6 asks of the
  daily log).

## 3. Where

S076 is coded after S074, and after S075 and S077 (in review) once they are approved.
`backend/improvements.py`, `backend/improvements_core.py` and `backend/config_rbac.py` are being
changed by S070–S075 now, so line numbers in them may move;
function and constant names are the anchors. Names new in S070–S075 are marked so.

### Backend

- `backend/config_rbac.py`: `"report:read": ("maint_engineer",)` in `PERMISSIONS`, with a comment
  (§ 5.7), after the improvement keys (`backend/config_rbac.py:132-133`), and in `SITE_SCOPED`
  (`backend/config_rbac.py:175-191`). **If R03.14 is coded first and has created it, this step
  only checks that it matches § 5.7.**
- `backend/improvement_register_core.py` (new, pure): `REPORT_KEY`, `default_period`,
  `parse_period`, `period_bounds`, `AGE_BANDS`, `age_days`, `age_band`, `open_summary`,
  `closed_summary`, `worked_share`, the messages (§ 5). It imports only `improvements_core`
  (`IMPROVEMENT_OPEN_STATES`, `CLOSED_STATES` and `READY_TO_VERIFY`, new in S072). The dates are
  parsed in the shell by `api_common.date_arg` (`backend/api_common.py:166`), as the access log
  does (`backend/settings.py:311`); the core takes dates (BR1-01).
- `backend/improvements.py`: the route `register` (`GET /api/improvements/register`) and its
  reads (§ 5.2–§ 5.6); it reuses `_now`, `_today`, `_in`, `_IMPROVEMENT_FROM` and
  `improvements_core.display_state` and `overdue_days` (`display_state` new in S072). The
  module docstring's *Reads* line of the LOCK ORDER names the register (plain, no lock).

### Frontend

- `frontend/src/views/ImprovementRegisterView.vue` (new): the print page (§ 5.8), on the pattern of
  `frontend/src/views/AssetListPrintView.vue` (the A4 `@page` rule added on mount and removed on
  unmount, `.no-print` controls, `window.print()`).
- `frontend/src/router/index.js`: the route `/tickets/improvements/register`, name
  `improvement-register`, `meta: { title: "Improvement register" }`, placed before the
  `improvement-detail` route (`frontend/src/router/index.js:73`).
- `frontend/src/views/ImprovementsView.vue`: the button `"Print register"` in the filter row, for
  `report:read` holders, from the `md` width up (D12); it opens the page in a new tab, as
  `printAssetList` does in `frontend/src/views/EquipmentView.vue:389`.
- `frontend/src/utils/improvementRegister.js` (new, pure): `monthPeriod(todayIso, monthsBack)`,
  `periodText(period)`, `AGE_BAND_LABELS`, `registerPath(query)`, `workedShareText(closed)`,
  `actionsText(item)`. `monthPeriod` works on the string's year, month and day only, never through
  `new Date()` and the browser's zone (as S073's `watchEndDate`), so a laptop west of UTC does not
  shift the month (BR1-13).
- Words reused, not added: `improvementStateLabel` (`frontend/src/utils/improvementLabels.js`, the
  state words of S072 D13), `actionKindLabel` (new in S071), `formatDate` (new in S073),
  `formatDateTime` (`frontend/src/utils/datetime.js:11`).

### Tests

- `backend/tests/test_improvement_register_core.py` (new): § 8.1.
- `backend/tests/test_improvement_register_api.py` (new): § 8.2.
- `backend/tests/test_rbac.py`: `test_role_matrix` (`backend/tests/test_rbac.py:219`) gains
  `report:read` for `maint_engineer` and `maint_manager`; a new `test_report_key` beside
  `test_improvement_keys` (`backend/tests/test_rbac.py:98`) (§ 8.3).
- `frontend/tests/improvementRegister.test.js` (new): § 8.4.
- `frontend/e2e/improvement-register.spec.js` (new) and `frontend/e2e/screens.spec.js` (one row):
  § 8.5. `frontend/e2e/support/improvements.js` gains a helper to add a countermeasure by API and
  one to drop an improvement by API, if S071 and S073 have not added them; `raiseFixed` gains an
  option `minutesAgo` (default 60) for the breakdown's `occurred_at`, with the restore 50 minutes
  after it, both inside the 7-day back-dating (BR1-05).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD`: § 3, a paragraph on `report:read` (§ 5.7) after the improvement keys' paragraph
  (the table row exists already); § 4.6, a bullet *Improvement register (S076)*; § 6, one sentence
  in the *Improvements* bullet; § 1's *Improvement (RCA)* row: "**Register:** printable, in R05
  (S076)" stays, with the step number.
- `docs/steps/device-checks.md`: one row for paper (§ 8.6).
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map gains `improvement-register` S076.
- `docs/schema.md` and `docs/schema.html`: no change (no migration).
- `docs/Maintenance-Philosophy.md` § 12 Glossary: a row *Management review* (one plain sentence),
  if the glossary does not have it.

**File count:** 13 code and test files (backend 3 code, 3 tests; frontend 4 code, 1 unit test,
2–3 e2e files), 4 docs.

## 4. Data model

**No migration.** Every figure is read from columns that exist after S067–S072:
`improvements.created_at`, `state`, `unit_id`, `equipment_id`, `lead_id`, `watch_from`,
`watch_days`, `closed_at`, `closed_by`, `close_remark`, `follow_up_of_id` (the last six new in
S072's v39), and `improvement_actions.state`, `kind`, `text`, `owner_id`, `due_date` (S070's v38).
Nothing is stored: the register is generated each time (Plan § 4.6: "generated from the records,
never written a second time"). Every `DATETIME` is IST (`backend/local_db.py:1353`,
`SET time_zone = '+05:30'`), so the period bounds compare directly.

**No new index.** The reads filter by site through `units` and by `created_at` or `closed_at`; a
site starts a few improvements a month (assumption: the plant's few engineers start them by hand,
R05 Q8.1 a), so a scan of `improvements` is small (CLAUDE-COMMON, *Right-sized*).

## 5. Rules

### 5.1 The period (`improvement_register_core`)

- **Query arguments** `from` and `to`, read by the shell with `date_arg("from")` and
  `date_arg("to")` (`backend/api_common.py:166-176`): DD-MM-YYYY or YYYY-MM-DD, trimmed, empty is
  absent, anything else 400 "from must be a date, DD-MM-YYYY or YYYY-MM-DD" with the field (BR1-01).
- **Defaults** (`default_period(from_date, to_date, today)`, BR1-02): both absent → today's IST
  month (the first to the last day); only `from` → `to` = the last day of `from`'s month; only
  `to` → `from` = the first day of `to`'s month. Today = `_today()` (IST,
  `backend/improvements.py`). So a page opened with no arguments shows the current month, as KLA's
  showcase asks ("for the monthly review"), and a one-sided link gives one month, not a refusal.
- **`parse_period(from_date, to_date, today)`** (dates or None) → `(period, None)` or
  `(None, {field, message})`, after the defaults:

| Case | Message (field) |
|---|---|
| `from` after `to` | "The start must be on or before the end" (`from`) |
| more than 366 days, both ends counted (`(to - from).days + 1 > 366`) | "Choose a period of up to one year" (`to`) |

  A future `to` is allowed (the default ends on the month's last day). A period entirely in the
  future gives empty period sections, not an error. The shell answers 400 with the message and
  field (`ApiError(message, 400, field)`).
- **`period_bounds(period)`** → `(start, end)` datetimes: `start` = `from` 00:00, `end` = the day
  after `to`, 00:00. A row is in the period when `start <= t < end`. Example: October 2026 is
  `2026-10-01 00:00 <= t < 2026-11-01 00:00`; a close at 31-10-2026 23:59 is in October.
- **"Now"** is `_now()` (IST, naive) and "today" its date, read once per request, for the age, the
  overdue days and the display state.

### 5.2 The site and the units (`report:read`)

- **The route** carries `@require_perm(REPORT_KEY)`: a user who holds `report:read` nowhere gets
  403 (and the access log's `denied_perm`).
- **The site choices**: the active sites that have at least one unit in
  `accessible_unit_ids(cur, REPORT_KEY)` (`backend/equipment.py:341`; it returns active units
  only). `None` (admin, or a token role that holds the key with `equipment:read_all_units`; today
  only admin) → every active site with an active unit. Ordered by site code.
- **`site_id`**: absent → the first choice. An integer not among the choices (no such site, a site
  where the user lacks the key, a site with none of their units) → **404 "Not found"**, as a record
  outside access (nothing revealed). Not an integer → `int_arg`'s 400. No choices at all (a key
  holder whose memberships have no active unit) → 200 with `sites: []`, `site: null` and empty
  sections; the page shows `NO_UNITS_TEXT` ("No units are given to you yet. Ask your engineer or IT.",
  `frontend/src/utils/messages.js:7`), as the improvements list does.
- **The predicate** of every section: the improvement is at the chosen site (`u.site_id = %s`,
  `u` the improvement's unit, fixed: S067 § 5.7) **and** visible under `report:read`:
  `unit_access_condition(cur, REPORT_KEY, "i.unit_id", "m.unit_id")`
  (`backend/equipment.py:349`), the same shape as the improvements list's
  `_visible_condition`. An engineer with chosen units sees the improvements of those units only.
- **`units`** in the answer: `null` when the reader's `report:read` units cover every active unit
  of the site; else the codes of their units at the site (the paper says "Units: SMTW.MCC1,
  SMTW.MCC2", so a partial register is never mistaken for the whole).
- **The register never shows more than the improvement list would.** Every `report:read` holder
  holds `improvement:read` at the same units today (engineer ⊇ operator, `ROLE_INCLUDES`); a role
  test pins it (§ 8.3), so a later grant that breaks it fails the build.

### 5.3 Started in the period

```sql
SELECT i.id, i.serial, i.title, i.state, i.watch_from, i.watch_days, i.created_at,
       m.code AS m_code, m.name AS m_name, u.code AS unit_code, l.name AS lead_name,
       fo.id AS fo_id, fo.serial AS fo_serial
  <_IMPROVEMENT_FROM>
  LEFT JOIN improvements fo ON fo.id = i.follow_up_of_id
 WHERE u.site_id = %s AND <visible> AND i.created_at >= %s AND i.created_at < %s
 ORDER BY i.created_at, i.id
```

- Each item: `{id, serial, title, machine{code, name}, unit_code, lead_name, started_at, state,
  follow_up_of{id, serial}|null}`; `state` is the display state now (§ 5.4).
- `count` = the number of items. Every improvement counts, whatever its state now (a dropped one
  too: it was started).

### 5.4 Open now, by state and age

```sql
SELECT i.id, i.serial, i.title, i.state, i.watch_from, i.watch_days, i.created_at,
       m.code AS m_code, m.name AS m_name, u.code AS unit_code, l.name AS lead_name
  <_IMPROVEMENT_FROM>
 WHERE u.site_id = %s AND <visible> AND i.state IN (<IMPROVEMENT_OPEN_STATES>)
 ORDER BY i.created_at, i.id
```

then one query for their countermeasures (no N+1):

```sql
SELECT improvement_id, SUM(state = 'open') AS open_n, SUM(state = 'open' AND due_date < %s) AS overdue_n
  FROM improvement_actions WHERE improvement_id IN (...) GROUP BY improvement_id
```

- **The stored state decides "open"** (`IMPROVEMENT_OPEN_STATES`, widened in S072: `analysing`,
  `actions_open`, `watching`), as the list's SQL filter does (S072 § 5.1, BR1-03). The **display
  state** decides the row: `display_state(state, watch_from, watch_days, now)` (new in S072)
  turns an ended watch into `ready_to_verify`. So the rows are `OPEN_DISPLAY_STATES =
  ("analysing", "actions_open", "watching", "ready_to_verify")`, in that order.
- **Age** `age_days(created_at, today)` = `(today - created_at.date()).days`: started today is 0.
- **Bands** `AGE_BANDS`: `0_30` (0–30 days), `31_90` (31–90), `91_180` (91–180), `over_180`
  (181 and more). `age_band(days)` returns the key; a negative age (a clock set back) counts as
  `0_30`.
- **`open_summary(rows)`** (pure; rows `{display_state, age_days}`) →
  `{count, by_state: [{state, bands: {0_30, 31_90, 91_180, over_180}, total}], band_totals:
  {…}}`, every state and band present with 0 when empty, so the table never loses a row.
- Each item: `{id, serial, title, machine{code, name}, unit_code, lead_name, state, age_days,
  actions_open, actions_overdue}`; the list is ordered oldest first (`created_at`, `id`).
- `due_date < today` is S070's *overdue* (`overdue_days` above 0; due today is not overdue).

### 5.5 Countermeasures overdue now

```sql
SELECT a.id, a.kind, a.text, a.due_date, p.name AS owner_name, i.id AS i_id, i.serial AS i_serial,
       i.title AS i_title
  FROM improvement_actions a
  JOIN improvements i ON i.id = a.improvement_id
  JOIN equipment m ON m.id = i.equipment_id
  JOIN units u ON u.id = i.unit_id
  JOIN people p ON p.id = a.owner_id
 WHERE u.site_id = %s AND <visible> AND a.state = 'open' AND a.due_date < %s
   AND i.state IN (<IMPROVEMENT_OPEN_STATES>)
 ORDER BY a.due_date, a.id
```

- **Only open improvements** (D8): S072 D10 cancels the open countermeasures of a dropped one;
  a closed improvement's late *Lesson* or *Spread* is no longer the review's open work. S074's
  daily scan uses the same rule (`i.state IN (<open states>)`, S074 § 5.2).
- Each item: `{id, kind, text, owner_name, due_date, overdue_days, improvement{id, serial,
  title}}`; `overdue_days` = `improvements_core.overdue_days(ACTION_OPEN, due_date, today)`.
  Most days late first (the order of `due_date`). `count` = the number of items.
- An owner who left the site still shows by name: the work is still late.

### 5.6 Closed in the period

```sql
SELECT i.id, i.serial, i.title, i.state, i.closed_at, i.close_remark, i.lead_id,
       m.code AS m_code, m.name AS m_name, u.code AS unit_code,
       vb.id AS vb_id, vb.name AS vb_name, i.closed_by, fu.id AS fu_id, fu.serial AS fu_serial
  <_IMPROVEMENT_FROM>
  LEFT JOIN people vb ON vb.username = i.closed_by
  LEFT JOIN improvements fu ON fu.follow_up_of_id = i.id
 WHERE u.site_id = %s AND <visible> AND i.state IN (<CLOSED_STATES>)
   AND i.closed_at >= %s AND i.closed_at < %s
 ORDER BY i.closed_at, i.id
```

- `CLOSED_STATES` (new in S072) = `closed_effective`, `closed_not_effective`, `dropped`.
- Each item: `{id, serial, title, machine{code, name}, unit_code, state, closed_at, closed_by_name,
  by_lead, remark, follow_up{id, serial}|null}`. `closed_by_name` = `vb_name`; only when no Team
  record has that login (admin) the login itself, as S067's `created_by_name` (BR1-11). `by_lead`
  = `vb_id == lead_id` for `closed_effective` and `closed_not_effective` (S072 § 5.8: admin, with
  no Team record, is never the lead); **`null` for `dropped`**: the person who dropped it is no
  verifier (D6, BR1-03). `remark` is the close remark or the drop reason (S072 § 4.1:
  `close_remark` holds both).
- **`closed_summary(rows)`** → `{it_worked, did_not_work, dropped, worked_share}`.
- **`worked_share(it_worked, did_not_work)`**: the share of the *verified* closes that worked, a
  whole percent, half rounded up (`floor(100 * w / (w + n) + 0.5)`); `None` when no improvement was
  verified in the period. Dropped ones are not verified, so they are not in it (D6). Example: 3
  worked, 1 did not → 75; 1 of 8 → 13.

### 5.7 Permissions

| Key | Holders | Site-scoped | Comment in `config_rbac.py` |
|---|---|---|---|
| `report:read` (new, or R03.14's) | `maint_engineer` (so manager) | yes | Plan § 3: the reports for the review (the improvement register, S076; PM compliance, R03.14). Engineers and managers of the site; not IT admin, who keeps the system but does not run the maintenance review (ISO 27001 A.5.15); not the supervisor yet (Plan § 3: "more reports later"). Every holder must also hold the records' read keys at the same units (test_report_key) |

- **The route:** `@require_perm("report:read")`, then the site choice of § 5.2 (404 outside it).
  No other check: the choices are built from the key's own units.
- **The button** `"Print register"` shows when `userPermissions` includes `report:read` (the global
  union, `/api/auth/me`), from `md` up. A user holding it at site A only sees the button and A's
  register.
- **Identity:** the page shows people's names (leads, owners, who closed), as the improvement page
  does to every reader; never a login, role or email. `printed_by` is the reader's own name
  (`g.user["name"]`, else the login, as `asset_list`, `backend/equipment.py:776-777`). A request
  with no identity gets `require_perm`'s 401.
- `improvement:read`, `improvement:edit`, `improvement:verify`, `improvement:note` are unchanged.

### 5.8 The page (`ImprovementRegisterView.vue`)

- **Load:** `GET /api/improvements/register` with the URL's `site_id`, `from`, `to` (only those
  present). The query lives in the URL (`router.replace`), so a reload and Back keep it, as the
  asset list's switches. **After the first load the page writes both `from` and `to`** (the
  answer's `period`) into the URL, and every preset or change of either field writes both, so a
  reload and a shared link carry a full period (BR1-02). A newer load wins (`loadSeq`, as
  `AssetListPrintView.vue`).
- **Controls** (`.no-print`, above the sheet): `"Site"` (a select, only when `sites.length > 1`);
  `"From"` and `"To"` (`type="date"`, applied on `change`); `"Show this month"` and `"Show last month"`
  (`monthPeriod(result.today, 0 | 1)`: the server's IST date, never the browser's clock); `"Print"`
  (`window.print()`, shown when the register has loaded). The help line "Print in portrait, at
  100 % ("Actual size")." as on the asset list.
- **The sheet** (A4 portrait, 12 mm margins, the `@page` rule only while the page is open):
  - header: `<h1>` "Improvement register", the site "SMTW — <name>", the period "01-10-2026 to
    31-10-2026" (`periodText`), "Units: …" when `units` is not null, "Printed on 30-10-2026 14:05
    by Arun (manager)";
  - `<h2>` "Started in the period (n)", a table: Serial, Started (the date only, `formatDate`),
    Machine, Title, Lead, State now; a follow-up row adds "Follow-up of IM-…";
  - `<h2>` "Open now (n)", the count table (rows: the four state words; columns: "0–30 days",
    "31–90 days", "91–180 days", "Over 180 days", "Total"), then the list: Serial, Age (days),
    Machine, Title, Lead, State, Countermeasures (`actionsText`: "2 open, 1 overdue", "2 open",
    or "None open" when none is open; BR1-12);
  - `<h2>` "Countermeasures overdue now (n)": Improvement, Kind, What will be done, Owner, Due,
    Days late;
  - `<h2>` "Closed in the period", the line "Closed: it worked 3 · Closed: did not work 1 ·
    Dropped 0 · it worked in 75 % of the verified closes" (`workedShareText`; without a verified
    close: "No improvement was verified in this period."), then the list: Serial, Closed (the date
    only, `formatDate`),
    Machine, Title, Result (the state word), Closed by (", the lead" only on the two verified
    results, never on *Dropped*; BR1-03), Remark, Follow-up;
  - footer lines "Reviewed by", "Date", "Decisions and actions", each with space to write (D11).
- **On screen** each serial links to the improvement page (`/tickets/improvements/<id>`); on
  paper the link is plain text. Tables repeat their header row on a new page (`thead {
  display: table-header-group }`), rows do not split (`break-inside: avoid`), as S015.
- **Empty sections** (one line each, the section heading stays): "No improvement was started in
  this period.", "No open improvements.", "No countermeasure is overdue.", "No improvement was
  closed in this period."
- **Answers that are not 200:**

| Answer | The page shows |
|---|---|
| 400 (a period message) | the message under the period fields, `role="alert"`; the controls stay; no Retry. **The last loaded register stays as it is**, not dimmed; its header shows its own `period` from the answer, never the URL's (BR1-04) |
| 403 | "You can't see the register." (no Retry), as the list's 403 line |
| 404 (a site no longer available) | "This site is not available." and a button `"Show my first site"` (drops `site_id` from the URL) |
| 503 or a network error | the message and `"Retry"` (as the asset list) |
| 200 with `site: null` | `NO_UNITS_TEXT` ("No units are given to you yet. Ask your engineer or IT.") |

- **Words for the floor:** the state words of S072 D13 ("Closed: it worked", "Closed: did not
  work"), never "effective". The page is for engineers and managers at a desk; the words stay plain.

### 5.9 Locks and the snapshot

- **No lock.** Every read is plain. The reads of one request run inside one `transaction(conn)`
  (`backend/db_helpers.py:42`), so they share one REPEATABLE READ snapshot (fixed by the first
  plain read): an improvement closed between two queries shows in one section only, never in both
  or neither (D10). The block writes nothing; its commit ends the read view. Pool connections are
  autocommit otherwise (`backend/local_db.py:1351`), which would give each query its own snapshot.
- The memberships and units read by `accessible_unit_ids` go through the same connection
  (`current_memberships`, `backend/auth_utils.py:338`); reading them inside the block is fine.

### 5.10 The database down

The route goes through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*); the page shows the message with `"Retry"`. No background task.

## 6. API

| Route | Key | Arguments | Answer |
|---|---|---|---|
| `GET /api/improvements/register` | `report:read` | `site_id?`, `from?`, `to?` | 200, below; 400 period (§ 5.1); 403 no key; 404 site (§ 5.2); 503 |

The answer (the items' fields are § 5.3–§ 5.6):

- `sites: [{id, code, name}]`, `site: {id, code, name} | null`, `units: [code] | null` (§ 5.2);
- `period: {from, to}` (`YYYY-MM-DD`), `today` (the IST date), `printed_at`, `printed_by`;
- `started: {count, items}`; `open: {count, by_state, band_totals, items}`;
  `overdue: {count, items}`; `closed: {it_worked, did_not_work, dropped, worked_share, items}`.


- Datetimes as `row_to_dict` gives them (ISO with `+05:30`, `backend/db_helpers.py:113`); dates
  `YYYY-MM-DD`. `printed_at` = `datetime.now(IST).isoformat(timespec="seconds")`, as `asset_list`
  (`backend/equipment.py:776`), so the header's `formatDateTime` gets the asset list's shape.
- Unknown arguments are ignored. The route is a `GET` and writes nothing.
- `/register` cannot clash with `/<int:improvement_id>` (an int converter).

## 7. Design decisions

- **D1. A print page opened from the Improvements list, in a new tab** (`"Print register"`), like
  the asset list from the equipment list (S015). The register is a document for the review, read
  at a desk and printed. Rejected: a third tab *Register* beside *Tickets* and *Improvements*
  (S068's tabs are lists to work from; a print page inside a tab shows the app's chrome around the
  sheet); a *Reports* nav item (no other report exists yet; R03.14 puts its report on *PM*; a
  reports page can gather them in phase 5).
- **D2. The period covers what was started and closed; "open" and "overdue" are as on the day it
  is printed.** The review needs the record's state now, to decide; and the past state at the
  period's end would need a replay of `improvement_events` (new in S072), with the edge cases of the
  backfill (S072 § 4.1: no lines for edits before v39). The paper says "now" in both headings
  and prints the date. Rejected: the state at `to` (complex, and a register printed on 3 November
  for October would hide what happened on 1–3 November).
- **D3. `report:read` = engineer (so manager), site-scoped, not IT admin, not the supervisor.**
  Plan § 3's table already gives it to engineer and manager; R03.14 names the same holders. IT admin
  reads improvements but does not run the review. The supervisor may get "more reports later"
  (Plan § 3), not now. Whichever of S076 and R03.14 is coded first creates the key; the second
  checks it. Rejected: `improvement:read` for the register (the operator and IT admin would get a
  management report); a new key `improvement:report` (Plan § 3 plans one key for all reports).
- **D4. The register's rows are chosen by `report:read` units, and every holder must also hold
  `improvement:read` there** (a role test). One predicate, the list's shape. Rejected: the
  intersection of the two keys' units in code (the same result today, more code); the whole site
  for any holder (an engineer with chosen units would see units their list hides).
- **D5. The current IST month by default; *Show this month* and *Show last month* from the server's date;
  any period up to 366 days.** The review is monthly; a quarterly or yearly review picks the dates.
  The presets use `today` from the answer, so a laptop with a wrong clock or zone still picks the
  plant's month. Rejected: last month by default (the screen would open on a finished month while
  most visits are mid-month checks); no upper bound (self-check 6).
- **D6. *Dropped* is counted beside the two closes, not in the share.** A drop is not a verified
  result; putting it in "did not work" would punish an improvement dropped as a duplicate.
  Rejected: leaving drops out (the review would not see abandoned work).
- **D7. Age bands 0–30, 31–90, 91–180, over 180 days.** The watch is 90 days by default (Q4.1 a), so
  an improvement that is fine can be 120 days old; over 180 is stalled. Rejected: bands of 30 days
  to a year (too many columns for A4 portrait).
- **D8. Overdue counts open countermeasures on open improvements only** (S070 `overdue_days`, S074's
  scan). Rejected: every open countermeasure (a closed improvement's late lesson would stay
  "overdue" for ever).
- **D9. A pure core of its own** (`improvement_register_core.py`). The figures are a separate
  concern from the record's rules, and `improvements_core.py` grows with every R05 step. Rejected:
  adding them to `improvements_core.py`; the route in a new blueprint module (one more
  `app.register_blueprint` in `backend/app.py`, a shared file, for one route).
- **D10. One read-only snapshot for the whole register** (§ 5.9). Rejected: autocommit reads (a
  close during the request could count one improvement twice or not at all).
- **D11. Sign-off lines on paper** ("Reviewed by", "Date", "Decisions and actions"). ISO 9001 § 9.3.3
  asks for evidence of the review's results, its decisions and actions; the plant records it on paper, as the asset list's checklist
  has signature lines (S015). Rejected: recording the review in Yantra (a review record, its
  decisions and actions: a module of its own, not in R05).
- **D12. The button from `md` up only**, as `"Print asset list"` (S064). A phone still opens the
  page by its link, and the page lays out at phone width (§ 8.5), but printing is a desk task.
  Rejected: the button on every width (a sheet of mm-wide tables is the wrong first view on a
  phone).
- **D13. No row cap.** A site's open improvements and their countermeasures are tens (ACTIONS_MAX
  30 per improvement; improvements are started by hand); a year's period the same. Rejected: a
  cap with a 400, as the asset list has for thousands of machines (it would refuse the very
  register a busy year needs).

## 8. Tests and acceptance

### 8.1 Pure core (`backend/tests/test_improvement_register_core.py`)

- `default_period`: both absent on 30-10-2026 → 01-10-2026 to 31-10-2026; on 15-02-2028 → to
  29-02-2028 (leap year); on 31-12-2026 → 01-12 to 31-12; only `from` 15-03-2026 → to 31-03-2026;
  only `to` 15-03-2026 → from 01-03-2026 (BR1-02).
- `parse_period`: `from` after `to` → the message on `from`; 366 days both counted (01-01-2028 to 31-12-2028) passes, 367 refused on `to`; `from ==
  to` passes; a future period passes.
- `period_bounds`: October → `2026-10-01 00:00`, `2026-11-01 00:00`.
- `age_days` and `age_band`: 0, 30, 31, 90, 91, 180, 181 days on the band edges; a negative age →
  `0_30`.
- `open_summary`: empty rows → every state and band 0; rows in several states and bands; the
  totals; `ready_to_verify` counted as its own row.
- `closed_summary` and `worked_share`: 3 / 1 → 75; 1 / 7 → 13 (12.5 rounded up); 0 / 0 → None;
  drops counted, never in the share.

### 8.2 API (`backend/tests/test_improvement_register_api.py`)

Each test makes its own site and units (`make_site`, `make_unit`, `uniq`), so counts are exact in
the shared session database. Improvements come from S067's start route (the fixtures of
`test_improvements_api.py`: `restored_ticket`, `started`, `eng`); states, `created_at`,
`watch_from`, `closed_at`, `closed_by`, `close_remark`, `follow_up_of_id` and countermeasure rows
are written straight to the rows with `db_rows` where a route would need weeks of watch, keeping
S072's CHECKs true (`chk_improvements_watch_from`, `chk_improvements_closed`,
`chk_improvements_close_remark`, all new in S072's v39) and S070's (`chk_improvement_actions_done`).

- **Started:** an improvement created on 30-09 23:59, one on 01-10 00:00, one on 31-10 23:59, one
  on 01-11 00:00 → October lists the middle two, oldest first; a follow-up shows `follow_up_of`.
- **Open:** one per stored open state; a `watching` row whose watch ended shows `ready_to_verify`
  in `by_state` and `items`; a closed and a dropped one are not open; ages on band edges;
  `actions_open` and `actions_overdue` per item; a due-today countermeasure is not overdue.
- **Overdue:** open + past due on an open improvement listed with `overdue_days`; done, cancelled,
  due today, and open on a closed improvement not listed; order by due date; the owner's name.
- **Closed:** in-period `closed_effective`, `closed_not_effective` (with its follow-up's serial)
  and `dropped` (with its reason as `remark`); one closed on 30-09 left out; `by_lead` true when
  `closed_by` is the lead's login, false for another engineer and for admin, `null` on a dropped
  row (also when the lead dropped it, BR1-03); the summary and the share.
- **Period errors:** bad text and `2026-02-30` → `date_arg`'s 400 with the field; `from=30-10-2026`
  (DD-MM-YYYY) accepted; `from` after `to` and 367 days → 400 with the message and field;
  `site_id=abc` → 400; only `to` given → one month.
- **Site and access:**
  - the engineer at site A only: `sites` = [A]; no `site_id` → A; `site_id` = B → 404; an
    improvement at B never appears;
  - the manager at A and B: both choices, ordered by code; `site_id` = B shows B's;
  - an engineer with chosen units (one of A's two): only that unit's improvements; `units` lists
    its code; a manager with all units: `units` null;
  - operator, technician, supervisor, storekeeper, IT admin: 403; admin: every active site;
  - an improvement whose machine moved to the engineer's unit from another unit of the site is
    visible (the predicate's second column);
  - a key holder with no active unit: 200, `sites` [] and `site` null.
- **Snapshot:** not tested by a race (a close between two queries cannot be timed in a test); the
  code review checks § 5.9 by reading the route.
- **Database down:** the `db_down` fixture → 503.
- **Printed by:** `printed_by` is the reader's name; `today` is the IST date (`_now` patched).

### 8.3 Existing tests that break or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` (`:219`) breaks for `maint_engineer` and
  `maint_manager` (one more key) and is updated; `it_admin` and the floor roles do not change. New
  `test_report_key`: holders are exactly `maint_engineer` and `maint_manager`; the key is in
  `SITE_SCOPED`; **every role holding `report:read` also holds `improvement:read`** (D4).
- `backend/tests/test_improvements_api.py`, `test_improvements_core.py`,
  `test_improvement_actions_api.py` (S070): run again, unchanged (the
  list and the core are not changed; `/register` must not shadow `/<int:improvement_id>`).
- `conftest.py` `_TABLES`: unchanged (no table). `test_migration_*`: none (no migration).
- `frontend/tests/improvementLabels.test.js`: runs again, unchanged.
- **The router is a shared frontend file** (§ Step workflow, *Shared code*): the coder runs the
  whole browser suite once at Normal when the coding is done.

### 8.4 Frontend unit (`frontend/tests/improvementRegister.test.js`)

- `monthPeriod("2026-10-30", 0)` → 2026-10-01 to 2026-10-31; `1` → September; `"2026-01-15", 1` →
  December 2025; `"2028-03-31", 1` → February 2028 (29 days).
- `monthPeriod` gives the same result with the test's time zone set west of UTC (BR1-13).
- `actionsText`: "2 open, 1 overdue", "2 open", "None open".
- `periodText` → "01-10-2026 to 31-10-2026" (DD-MM-YYYY); `AGE_BAND_LABELS` word for word;
  `workedShareText` with and without verified closes; `registerPath` drops empty values.

### 8.5 Automated (e2e, targeted: `improvement-register.spec.js`, `screens.spec.js`)

Set-up by API (`support/improvements.js`): a breakdown raised 3 days back and restored
(`raiseFixed(…, { breakdown: true, minutesAgo: 3 * 24 * 60 })`, within the 7-day back-dating), an improvement started from it, a countermeasure due
on the ticket's date (so 3 days overdue), and a second improvement dropped by API. The lane's
database holds other tests' improvements, so the tests find rows by serial, never by counts.
Closed *it worked* and *did not work* need a 30-day watch: the API tests cover them, not the
browser.

- `S076: the engineer sees the register of this month: the improvement started, open with its age, and its overdue countermeasure`
  (phone-chromium, opened by URL).
- `S076: the dropped improvement shows under Closed in the period with its reason`.
- `S076: the manager picks BRICKS and Show last month; the link and the period line change`.
- `S076: a start after the end is refused under the period fields, and the sheet stays`.
- `S076: the operator has no Print register button and the address shows a plain line, no Retry`.
- `S076: on paper the controls are left out and the sheet has the review lines` (`emulateMedia`
  print; untagged, as S015's).
- `S076: Print register on the Improvements list opens the register in a new tab`, tagged
  `@device` (it runs on `desktop-chromium`: the button shows only from `md` up, D12).
- `S076: the register fits a phone with no sideways scroll`, tagged `@device` (a layout check,
  `expectNoSidewaysScroll`).
- `screens.spec.js`: a row `/tickets/improvements/register`, title "Improvement register", shows
  the heading "Improvement register", `who: ["engineer", "manager"]`.

### 8.6 On a real device

- **important** Row for `docs/steps/device-checks.md`: Tickets › Improvements › **Print
  register**, print one month's register on A4 **portrait** at **100 %** ("Actual size"). On the
  paper: no column is cut at the right edge; the *Remark* and *What will be done* columns wrap
  inside their cells; on a second page the table's header row repeats; the "Reviewed by", "Date"
  and "Decisions and actions" lines are on the sheet with room to write. Account: dev server none; production
  a test login with the Engineer role at SMTW (ask KLA). Network: company Wi-Fi (the office
  printer). Where: either. Done by IT Admin.

### 8.7 Acceptance

1. An engineer prints this month's register for their site; the four sections show the right
   improvements and countermeasures, with the state words of S072.
2. A manager of two sites switches site and period; the link keeps the choice on reload.
3. Roles without `report:read` see no button and get a plain line at the address.
4. `tooling/run-tests.bat` green; the targeted e2e run green; the whole browser suite at Normal
   once (the router changed); the device check on paper done or listed.

## 9. Open questions and assumptions

- **No defining question.** Gate R answered Q10.1 (a); the key's holders are Plan § 3's table, as
  R03.14 reads it (D3).
- **Q1. Open and overdue "now", not at the period's end** (D2). Answered 30-10-2026: **now**, as
  proposed. (b) the state at `to`, from the timeline: more code, and the timeline is incomplete
  before v39. Not defining.
- **Q2. The share "it worked"** is a local measure, not an SMRP KPI (§ 2). Answered 30-10-2026:
  **show it**, as proposed. (b) counts only. Not defining.
- **A staleness check is due before coding** (the orchestrator, 30-10-2026). This brief was
  approved while S070 was being coded and S071–S075 and S077 were not. Check S072's
  `display_state`, `CLOSED_STATES`, `READY_TO_VERIFY` and the v39 columns, S071's
  `actionKindLabel`, S073's `formatDate` and `watchEndDate`, the e2e helpers of S071 and S073, and
  the line anchors of § 3 and § 5 against the code as written; and whether R03.14 has created
  `report:read` first.
- **Assumption:** a site starts a few improvements a month, so no index and no row cap are needed
  (§ 4, D13).
- **Assumption:** the clause numbers of the next ISO 9001 edition and ISO 55001 are *to verify*.
- **Length:** about 620 lines, just past the size rule's 600, as S069 (730) and S070 (696) were.
  It is one concern (a report and its print page), 13–14 code and test files, no table and one
  screen: no split. Most of the length is § 5's queries and § 8's cases.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 1 (items 1, 3, the example), § 2 (§ 7.5.2, § 9.3.3),
§ 3 (the intro, the core, `improvementRegister.js`, `raiseFixed`), § 5.1, § 5.2 (line anchors),
§ 5.6, § 5.7, § 5.8 (load, controls, columns, the 400 row), § 6, D5, D11, § 8.1, § 8.2, § 8.4,
§ 8.5, § 8.6, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): the shell reads `date_arg("from")`, `date_arg("to")` (DD-MM-YYYY or ISO, its 400); the core's `parse_period` takes dates and keeps the register's own rules; the bad-text row left § 5.1's table. § 3, § 5.1, § 8.1, § 8.2. |
| BR1-02 minor | Accepted (a): a missing end defaults from the given one (one month); both absent → today's month; the page writes both `from` and `to` to the URL after the first load and on every change. § 5.1, § 5.8, § 8.1, § 8.2. |
| BR1-03 minor | Accepted (a): the column is "Closed by"; `by_lead` is `null` on a dropped row, ", the lead" only on the two verified results. § 5.6, § 5.7, § 5.8, § 8.2. |
| BR1-04 minor | Accepted (a): on a 400 the last loaded register stays, not dimmed, its header from the answer's own `period`. § 5.8. |
| BR1-05 minor | Accepted (a): `raiseFixed` gains `minutesAgo` (default 60), the restore 50 minutes after it, inside the 7-day back-dating. § 3, § 8.5. |
| BR1-06…BR1-14 nits | Accepted: BR1-06 `"Show this month"` / `"Show last month"`; BR1-07 "Decisions and actions"; BR1-08 § 7.5.2 for the printed-by line, § 7.5.3 for protected records; BR1-09 `equipment.py:341` and `:349`; BR1-10 `printed_at` as `asset_list` (`equipment.py:776`); BR1-11 the login only when no Team record has it (admin); BR1-12 dates only, "None open"; BR1-13 `monthPeriod` on the string, never the browser's zone; BR1-14 the header and § 3 (S075 and S077 in review). § 9 Q1 and Q2 answered as proposed. |
