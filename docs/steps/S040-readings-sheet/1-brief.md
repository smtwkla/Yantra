```
Step: S040 — End-of-day readings sheet
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: full
Status: Committed c6e74a1 (base, 25-10-2026); checks: 19 auto; important check pending: row 33 of device-checks.md; open for the user: CR1-10; A1 committed in 5731712 (partial); A1 CR r4: 1 major (CR4-01), 1 nit — fix round queued after S045's
Baseline: ff9ddb3 + snapshots refs/steps/S038, refs/steps/S043 + S039 (working tree, at gate B); stale check s1 done 24-10-2026
```

# S040 — End-of-day readings sheet

**The need (KLA, 24-10-2026).** "Meter reading entry", the second half. The
press supervisors enter strokes, run hours, kWh and the day's maximum oil
temperature for every press at the end of the day (Plant-Facts line 129); the
turner-cum-fitter's genset round reads run hours and fuel level (line 130). One
screen with every meter of a **site**, grouped by unit, instead of one dialog
per meter (U3: "One sheet one site").

Split from S039 on the user's choice (U2, S039 BR1-07). This step adds **no
rule and no migration**: every reading goes through S039's POST, with S039's
checks and locks. It adds the page, the sheet's read and the nav item.

User answers:
- U1 (24-10-2026): readings per equipment; an end-of-day sheet per unit.
- U2 (24-10-2026): the sheet is its own step; operator and up log readings,
  not IT admin; a fixed 7-day back-date window, for everyone (S039 decision 8).
- U3 (24-10-2026): one sheet per **site**; a reading is removed only by
  `equipment:edit` holders (S039), so *Undo* is theirs; a third meter kind,
  *Amount per period* (S037), e.g. *Shift production*.

Built on e451c33 plus S037 (v29), S038 (v30) and S039 (v32), all approved and
coded before this step.

## 1. What will be built

1. **A new page, *Readings*** (`/readings`), and a nav item after *Tickets*
   (icon `fa-solid fa-gauge`, permission `reading:log`). The nav order becomes
   *Me*, *Equipment*, *Tickets*, *Readings*, *Masters*, *Settings* (S035 put
   *Me* first). The storekeeper and IT admin do not see it (no `reading:log`).
2. **The site** (U3: "One sheet one site"; `reading:log` is site-scoped, so a
   site is its natural scope). The sites offered are the **active** sites
   that have an active unit in `GET /api/equipment/my-units`' new
   `reading_unit_ids` (every active site with an active unit when it is
   `null`), built by `readingSites(allUnits, allSites, mine)` over the
   masters' units list (`ensureUnits()`, rows with `site_id`,
   `_UNIT_SELECT` in `masters.py`) and the sites list (`ensureSites()`, with the site's name
   and `active`), as the Tickets filters are built (`TicketsView.vue:61`,
   `:144`; BR1-01, BR2-01). The picker shows the site **code**, as the Tickets
   site filter; the sheet's heading shows "SMTW — Main factory,
   Pavoorchatram", code first, from the sheet GET's `site` (BR2-01):
   - a user with `reading:log` at **one** site: no picker; the heading names
     the site;
   - several sites: a picker, the last choice remembered in the browser under
     the key `yantra.readings.site_id` (S039 BR1-17; the first `localStorage`
     use in `frontend/src`; read and written in `try`/`catch`, so a private
     window falls back to the first site). A remembered site no longer
     offered (access changed, site deactivated) falls back to the first site
     (BR1-14);
   - switching the site keeps the sheet's *Time taken* (BR1-09);
   - a 404 on the sheet read (access changed, or the site deactivated after
     the lists were cached) forgets the remembered site and shows the picker
     again with "This site is no longer available. Pick another site."; it is
     not a "Try again in a minute" case (BR2-07).
3. **One *Time taken* for the sheet,** default now, the same field and rules
   as S039 (§ 5.1 there: 5 minutes ahead, 7 days back): `EventFields.vue`
   ("Now · Change", `withRemark: false`, `timeLabel: "Time taken"`); "Now"
   sends no `taken_at`, so the server's clock decides (BR1-09).
4. **The rows:** the site's machines that have meters in force (on the
   machine or its parts), at the units of that site where the user holds
   `reading:log`, **grouped by unit** (a unit heading, units in code order),
   machines in tree order within a unit, not scrapped (U3). A unit with no
   machine with meters in force is not listed (BR2-02). On a phone the unit
   headings stay in view while their rows scroll (`position: sticky; top: 0`
   inside the scrolling main; BR2-09). **Which lifecycles** (BR1-06; settled,
   U4 D2): `in_service` and `standby` machines are listed; `out_of_use`
   machines sit behind a *Show out of use* link at the end of each unit's
   group, collapsed, so an idle press stays under its unit and a reading on it
   is still possible (BR2-04).
   - **One card per machine**, on a phone and on desktop alike (BR1-07; the
     sheet is a phone screen first). The card shows the machine's meters,
     then each part that has meters as a titled block inside the same card
     ("Hydraulic pump"), so a part never stands apart from its machine.
   - Each meter row: name, unit, last reading ("12,345.6 h · 23-10-2026
     18:00"), and an input (`inputmode="decimal"`, the unit beside it).
     Meters come in meter type name order, as on the equipment card (S038
     § 5.2; BR1-18).
   - **An amount meter** (U3, e.g. *Shift production*): under the row's label,
     S039's help "The amount for the period just ended, such as this shift."
     (one sentence for both screens; BR2-06), and its last reading reads
     "420 pcs · 23-10-2026 14:00" as the others. Its input takes the amount,
     not a running total; it never shows the *Meter reset* tick.
   - **A Yes / No meter** (U3, e.g. *Oil level above min*): the row shows the
     question (the type's name) and, in place of the input, two large toggle
     buttons, **Yes** and **No** (at least 48 px high, side by side). A tap
     picks the answer and a second tap on the same button clears it; the row
     is then saved with the others by *Save readings*. S039's dialog works
     the same way (pick, then *Save*; S039 decision 11), so a Yes / No reading
     is entered alike on both screens. Its last reading reads "Yes · 23-10-2026 18:00", with a *Not
     OK* badge when it was not the expected answer. A saved *Not OK* row reads
     "Saved. Not OK: the expected answer is Yes." It never shows the *Meter
     reset* tick.
   - **Read today** (BR1-05; settled, U4 D3): a meter whose last reading was
     taken today (IST) reads "Today 17:50 · 12,345.6 h", its row is greyed
     with a tick, and its input stays empty but can still be typed in. The
     header counts "9 of 48 read today" (the same 48 meter rows as the save
     bar's count; BR2-05). The day test is on
     the frontend: a small tested `isToday(takenAt, now)` in `meterLabels.js`
     compares the API's IST date (`taken_at.slice(0, 10)`, sent as `+05:30`)
     with the phone's date, as the rest of the frontend treats the phone as
     IST (BS1-07).
5. **The *Meter reset* tick is hidden** (S039 BR1-06 item 2): it shows on a
   counter row only after that row's refusal carries `code:
   "counter_lower"` (S039 § 5.2.4, S039 BR2-02; BR1-02), the "Lower than
   the reading of …" refusal, whose text already tells the user to tick it.
   No text is matched. Its help is S039's:
   "Tick this only when the meter was replaced or set back to zero".
6. ***Save readings*** saves each filled row in turn, one POST per row
   (S039's POST). **Where it sits** (BR1-04): on a phone, in a sticky bar
   at the bottom of `main.app-content` (`position: sticky; bottom: 0`
   inside the scrolling main, so it sits above the fixed 56 px bottom nav,
   `main.css:80`), with the count "3 of 48 filled" (one noun and one
   denominator, the sheet's meter rows; BR2-05); the sheet ends
   with padding of the bar's height, so the last row stays reachable. On
   desktop the button is at the end of the sheet.
   - The button is **disabled while a save runs** (S039 BR1-06 item 4), so a
     row in flight is never posted twice. Undo on the saved rows is disabled
     too; the inputs of rows not yet posted stay editable, and the value
     posted is the value at that row's turn (BR1-10).
   - Each row then shows *Saved* or its refusal in plain words beside the
     input (S026: the refusal in view).
   - A saved row turns read-only. For a holder of `equipment:edit` at the
     site (engineer, manager; U3) it shows **Undo** (S039 BR1-06 item 1),
     which calls S039's remove route and makes the row editable again, with
     the value kept. Undo of a reset row that has a later reading gets S039's
     409, shown on the row. For anyone else a saved row reads *Saved* and has
     no Undo (U3: only `equipment:edit` holders remove a reading, S039 § 1.4).
     One line for the whole sheet, shown once after the first save, under
     the sticky bar on a phone and under the button on desktop: "A wrong
     reading is removed by an engineer. Ask one." (BR2-03). Whether to show
     Undo comes from `my-units`' `edit_unit_ids` (the units where
     `equipment:edit` is held), the field the equipment form already reads.
   - Empty rows are skipped. A second press saves only the rows not yet
     saved.
7. **Failures** (S039 BR1-05, the sheet's parts):
   - a row's save fails with a 502, 503 or 504, or gets no answer at all
     (no network): the loop **stops** (BS1-02, the same set as S039's dialog,
     S039 CR1-05);
     that row and every row after it read "Not saved. Try again in a
     minute.", with their typed values kept (BR1-11). A 400 or 409 on a row
     does not stop the loop: that row shows its refusal and the others go
     on;
   - the sheet's load fails: "Readings could not be loaded. Try again in a
     minute.", with *Try again*.
   - The "not saved" set (502, 503, 504, no status) lives in one place: the
     coder lifts S039's `notSavedOr` (or its list) out of
     `ReadingFormModal.vue` into `meterLabels.js` or `api.js`, and both
     screens use it (BS1-02).
8. **Empty states:** a site with no meters in force: "No machine at this site
   has meters. Engineers add meters in Masters › Models or on a machine's
   page.", with *Time taken* and *Save readings* hidden (BR1-12); the site
   picker stays, so another site can be picked (BR2-10). A user
   with `reading:log` and no unit (so no site) **can** occur (their only unit was
   deactivated: `auth_utils._unit_pools` keeps active units only; BR1-03):
   the page shows the app's `noUnits` message, "You have no units assigned
   — ask IT admin for unit access." (`TicketsView.vue:171`), with no picker
   and no *Save readings*.

### Out of scope

- A sheet across sites (the genset round that crosses sites, Plant-Facts line
  130; § 9.1). Within a site, the one sheet covers every unit (U3).
- Shifts as such (shift names, times): an amount's *Time taken* places it
  (S039 § 9).
- New rules: every rule is S039's.
- Offline entry (the app is online-only, S021: the service worker caches
  nothing).

## 2. Standards and practice

- **TPM, autonomous maintenance** (Maintenance-Philosophy): the operator's
  daily check on their own machines. The sheet replaces the notebook
  (Plant-Facts line 120), so the reading is recorded where the PM engine
  (phase 4) can use it.
- **ISO 50001 § 6.6 (planning for collection of energy data)** (to verify): the
  daily kWh read at a fixed time on one screen is the data plan in practice.
- **EN 13306, condition monitoring** (term number to verify): readings at a
  regular interval are what makes a trend.
- **ISO 9001 § 7.5.3 (control of documented information)** (BR1-16): Undo
  removes a reading and keeps it, with who and when (S039 decision 5); the
  sheet never edits a value in place. In plain terms: the record is
  protected from loss and unintended change.
- **ISO 14224, operating time** (BR1-16): the run hours read each day are
  the denominator of phase 5's failure rates (MTBF).

## 3. Where

### Backend

- `backend/meters.py`: `GET /api/readings/sheet?site_id=` (§ 6). A few
  queries for the whole site, none per node (BR1-08): the unit's nodes, the
  model and node meter rows with their types (`effective_meters` per node,
  S038), and the last reading per (node, meter type). Placed here, not in
  S039, because only the sheet uses it.
- `backend/equipment.py`: `GET /api/equipment/my-units` (`my_units`) gains
  `reading_unit_ids` (`null` = every unit, else the ids where `reading:log`
  is held), one more `accessible_unit_ids(cur, "reading:log")` call beside
  `edit_unit_ids` (BR1-01). The comment above `accessible_unit_ids` ("only
  these helpers, the list, /my-units … touch accessible_unit_ids") stays
  true.

### Frontend

- `frontend/src/stores/navigation.js`: the *Readings* item after `tickets`.
- `frontend/src/router/index.js`: the route `/readings`, title *Readings*.
- `frontend/src/views/ReadingsView.vue` (new): the sheet.
- `frontend/src/stores/equipment.js`: `readingSites(allUnits, allSites,
  mine)`, the sites the sheet offers as `{id, code, name}` (the active sites
  with an active unit in `reading_unit_ids`, or every active site with an
  active unit when it is `null`), beside `filterableUnits` / `pickableUnits`
  (BR1-01, BR2-01, U3); `noUnits` reused.
- `frontend/src/utils/meterLabels.js` (S038/S039): reused as built:
  `formatReading`, `readingBadges`, `savedMessage` and `LIMIT_STATE_LABELS`
  (BS1-06). A row saved outside its limits reads as the card does, e.g.
  "Saved. Above the limit of 60 °C."; a Yes / No row "Saved. Not OK: the
  expected answer is Yes." Gains `isToday` (BS1-07) and the shared "not
  saved" check (BS1-02).

### Tests

- `backend/tests/test_readings_api.py` (S039): the sheet read.
- `frontend/tests/navigation.test.js`: the five `visible(...)` expectations
  gain *Readings* for the reading roles; the storekeeper and IT admin do not
  see it (S039 BR1-15). S039 has already added `reading:log` to the role
  lists (BR1-15).
- `backend/tests/test_equipment_api.py` (the file that tests
  `my-units`): `reading_unit_ids` per role (BR1-01). Three existing
  assertions compare the whole `my-units` dict (two units; token roles; no
  rows) and are extended with `reading_unit_ids`, not only joined by a new
  test (BS1-03).
- `frontend/e2e/readings.spec.js` (S039): the sheet tests (§ 8).
- `frontend/e2e/screens.spec.js`: `/readings` for the reading roles; the
  bottom bar (S039 BR1-14).

### Docs (housekeeping, by the coder)

The docs pass (`.claude/CLAUDE.md` § Docs to keep current), in this step:

- `docs/Plan.MD` § 4.5 (the sheet as built) and § 6 (the *Readings* screen and
  the nav order). The gate A decisions are already recorded there.
- `docs/steps/device-checks.md`: the row of § 8 *On a real device*.
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map, `readings` S039 →
  S039/S040 (BS1-08).
- No migration, so no schema doc change.

## 4. Data model

None. No migration.

## 5. Rules

### 5.1 The sheet read

- `GET /api/readings/sheet?site_id=` (U3) lists the site's **active** units
  that are in `accessible_unit_ids(cur, "reading:log")` (`accessible_unit_ids` in `equipment.py`;
  `None` for admin = every active unit of the site). `reading:log` is
  site-scoped, so that set holds the units of the sites where the person may
  log.
- A site with no such unit (outside the user's sites, unknown, inactive, or
  every unit inactive) → 404, for admin too (admin's set is `None`, so the
  route checks `active` on the site and its units itself; BR1-17).
- `site_id` missing or not an id → 400 "Pick a site" (`site_id`).
- The sites offered to the picker: built in the frontend from `my-units`'
  `reading_unit_ids` over `ensureUnits()` (the masters' units list, with
  `site_id`), as § 1.2 (BR1-01). No new route.

### 5.2 Saving

- Every row is S039's `POST /api/equipment/<id>/readings`, one transaction per
  row, so a sheet never holds two node locks (S039 § 5.3).
- The sheet sends the sheet's *Time taken* with each row.
- Undo is S039's `DELETE /api/equipment/<id>/readings/<reading_id>`.

### 5.3 The database down

The page shows the load message (§ 1.7) on a 502, 503 or 504, or no answer
at all (BS1-02); the rows' failures are per row (§ 1.7), and the same set
stops the save loop.

## 6. API

| Method | Path | Key | Query | Response |
|---|---|---|---|---|
| GET | `/api/equipment/my-units` (existing) | `equipment:read` | — | gains `reading_unit_ids` (BR1-01) |
| GET | `/api/readings/sheet` | `reading:log` at the site (its units in `accessible_unit_ids`) | `site_id` | `{site: {id, code, name}, units: [{id, code, name, machines: [{id, code, name, lifecycle, meters: [the `_meters_out` dict: `effective_meters`' fields plus `last` (BS1-06)], parts: [{id, code, name, level, meters: [...]}]}]}]}` (U3: grouped by unit; `units` holds only units with at least one machine with meters in force, BR2-02; `meter_type` carries `kind`; BR1-07: parts nested, two levels at most, as the subtree read, `equipment.py:258`; `last` as S039: `{value, taken_at, limit_state}` or `null`) |

## 7. Design decisions

1. **The sheet saves row by row** (one POST per row). A bad row does not block
   the others; on a weak phone network the saved rows are safe. Rejected: one
   transaction for the sheet (one typo blocks twenty readings, and a new
   per-row error shape in the API).
2. **Undo on a saved row, for `equipment:edit` holders only** (S039 BR1-06,
   U3). An engineer's correction stays on the sheet. An operator or a
   supervisor sees *Saved* on each row and one line for the sheet: "A wrong
   reading is removed by an engineer. Ask one." (BR2-03). Rejected: the
   sentence on every saved row (40 copies of a sentence about a mistake
   nobody made), and an Undo for the author during the sheet's
   session (a second removal rule beside S039's, which the user ruled out),
   and the equipment page's *History* → *Remove* for engineers (four
   screens).
3. **The *Reset* tick hidden until a "Lower than" refusal.** A reset happens a
   few times a year; a tick on 30 rows is clutter and a stray tap saves a wrong
   reset. Rejected: a tick on every counter row.
4. **No site picker for a one-site user.** Nothing asked that can be defaulted.
5. **The sheet read in S040, not S039.** Only the sheet uses it.
6. **The units from `my-units`, not a new route** (BR1-01). Rejected: a
   `GET /api/readings/units` route (a second "my units" that could drift,
   and the `noUnits` handling written again).
7. **Parts inside their machine's card** (BR1-07). Rejected: a flat list
   with `parent_id` and indentation (a part's card can scroll away from its
   machine), and a desktop table (a second layout for one user).
8. **One sheet per site, grouped by unit** (U3: "One sheet one site").
   `reading:log` is site-scoped, and a supervisor of two units or a fitter on
   the round of one site reads one sheet. Rejected: one sheet per unit (U1's
   first shape: two sheets for one walk).
9. **Yes / No on the sheet picks; *Save readings* saves** (U3). The two
   buttons only choose: a sheet has one save action for every row, and a
   stray tap on a 40-row page must be undoable before saving. S039's dialog
   does the same (pick, then *Save*; S039 decision 11), so both screens enter
   a Yes / No reading alike. Rejected: saving at the tap (two save rules on
   one page).

## 8. Tests and acceptance

### Backend (pytest)

- `test_readings_api.py`: the sheet lists the site's units where the user
  logs, each with its machines with meters in force (on the machine or a
  part), in tree order, parts nested, without scrapped ones, with the last
  reading, the lifecycle and the meter's kind; a supervisor at two units of
  one site gets both, an operator at one of them only that one; another site
  (404); an inactive site, and a site whose units are all inactive, admin
  too (404); a storekeeper role (no `reading:log`: 404); `site_id` missing
  (400) (U3). The cases build their own sites and units (`user_at_sites`,
  `make_site`, `make_unit`, `role_client`), as `test_equipment_api.py` and
  `test_readings_api.py` do, not the e2e seed (BS1-10).
- `my-units`: `reading_unit_ids` is the units where the user holds
  `reading:log`, `null` for admin, empty for a user whose only unit was
  deactivated.

### Frontend (vitest)

- `navigation.test.js`: *Readings* after *Tickets* for operator (=
  supervisor), engineer, manager; not for the storekeeper or IT admin. The
  file has no technician list (BS1-09).

### Automated (e2e)

Set-up as S039 coded it (S039 *Decisions taken* 12, CR1-02; BS1-01):
- each S040 test makes **its own machine(s)** with `meterMachine(testInfo,
  tag, {unit, modelMeters, ownMeters})` from `e2e/support/meters.js`, which
  makes a press model of its own (never `SMTW-HYP-01`): `unit: "SMTW.MCC2"`
  for the operator's cases, and a second machine at `SMTW.MCC1` for the
  supervisor's two-units case;
- its **own readings** with `logByApi(machine, name, value, takenAt,
  extra)`, which posts as the operator, so only on an MCC2 machine (a
  counter reading for the too-low case, one taken today for *Today*);
  `--grep S040` passes alone, without S039's tests first;
- the Yes / No meter type made once per project in `beforeAll`, as
  `readings.spec.js` does;
- the sheet lists every machine at SMTW with meters, from every test and
  project in the lane: each assertion is **scoped to the test's own card**
  (found by its machine's name, `S038 press <tag> <project>`), and the header
  counts ("9 of 48 read today", "3 of 48 filled") are asserted as a pattern
  or a difference, never as literal numbers. No test touches a seed node.

- `readings.spec.js`:
  - **Important.** "S040: the end-of-day sheet saves the filled rows and shows
    each refusal" (one good row, one too-low counter row: the good row reads
    *Saved*, the other shows its message and its *Reset* tick; no sideways
    scroll on Pixel 7 and iPhone 14);
  - "S040: Undo on a saved row makes it editable again", as the engineer
    (U3);
  - "S040: the operator's saved row reads Saved, the sheet shows the Ask an
    engineer line once, and there is no Undo" (U3, BR2-03); the operator's
    sheet shows MCC2 only, the "some units of a site" case (BR2-02);
  - "S040: a shift production row takes an amount lower than the last one"
    (U3);
  - **Important.** "S040: a Yes / No row answered No saves and shows Not OK"
    (the two buttons at least 48 px high and inside the viewport on Pixel 7
    and iPhone 14; a second tap clears the answer; U3);
  - "S040: Save readings is disabled while saving" (the POST held back by a
    delayed `page.route`; BR2-08), and on Pixel 7 and iPhone 14 its box is
    inside the viewport and above the bottom bar (BR1-04);
  - "S040: the supervisor sees no site picker and both MCC1 and MCC2 on one
    sheet; the manager picks BRICKS, reloads, and BRICKS is still chosen"
    (the seeds give both cases: `e2e_supervisor` one site with two units,
    `e2e_manager` two sites, `seed_e2e.py:39`, `:43`; BR1-13, U3);
  - "S040: a meter read today shows Today and its tick" (BR1-05, U4 D3).
- `screens.spec.js`: `/readings` opens for the reading roles, title
  *Readings*, with a `shows` locator that holds in the empty state (each
  lane's database has no meters there): the site heading with the code
  (SMTW) for the operator and the supervisor, the site picker for the manager
  (BR1-12, BR2-01,
  U3); the bottom bar shows all six items for the manager without
  sideways scroll on Pixel 7 (S039 BR1-14).

### On a real device

- **Important** — the decimal keypad on an Android phone and an iPhone on the
  sheet, and that the keyboard does not hide a row's message or the *Save
  readings* button (S026); the *Yes* / *No* buttons are easy to hit with a
  thumb on a row (U3). Account: a test login with the Supervisor role at
  SMTW; company Wi-Fi; production on the TEST machine, or the dev server. Row
  for `docs/steps/device-checks.md`.

### Acceptance

A press supervisor enters the day's strokes, run hours, kWh and oil
temperature for all presses of the site, unit by unit, on one screen; a typo on one counter is
refused with a plain message and does not block the others; Undo fixes a saved
typo on the spot for an engineer, and an operator's sheet names who can
remove a wrong reading.

## 9. Open questions and assumptions

1. **The genset round across sites** (Plant-Facts line 130): settled within a
   site by U3 (one sheet per site covers every unit). A round that crosses
   sites reads one sheet per site; a cross-site sheet is a later step.
2. **The words** (assumption): *Readings*, *Save readings*, *Saved*, *Undo*,
   the failure texts and the empty state of § 1.
3. **The units list**: settled by BR1-01: `my-units`' `reading_unit_ids`, no
   new route.
4. **Which lifecycles appear on the sheet**: settled (U4, D2): `in_service`
   and `standby` listed, `out_of_use` behind *Show out of use*, collapsed.
5. **Mark meters read today**: settled (U4, D3): "Today 17:50 · …", the row
   greyed with a tick, a header count "9 of 48 read today".
6. **Standards numbers** (to verify): ISO 50001 § 6.6, EN 13306 terms,
   ISO 9001 § 7.5.3.

## 10. Amendments

### A1 — Enter more readings after a save

```
Requested: KLA, 25-10-2026 (testing S040 on the dev instance)
Status: Approved 25-10-2026 by KLA (the user's own design, given in answer to the orchestrator's question)
```

**The fault seen.** After *Save readings* the rows show *Saved*, and the sheet
offers no way to enter another round at another time: the user must leave the
page and come back.

**What changes (the user's design):**
1. After a save that leaves no row to retry, the whole round is **read-only**:
   every row, and the sheet's *Time taken*. The save button stays where it is,
   **disabled, and reads *Saved***.
2. Beside it, a separate button **Enter more readings** (`btn-primary`, at
   least 44 px tall) starts a new round: every row empty and editable again,
   *Time taken* back to now, each row's last reading and read-today mark taken
   from a reload of the sheet (so the round just saved shows as the last
   reading), the saved round's *Undo* gone.
3. A partial save (some rows refused or not saved) keeps today's behaviour:
   the refused rows stay editable, *Save readings* stays enabled for them, and
   *Enter more readings* shows only once nothing is left to retry.
4. Leaving the page, or switching the site, with a saved round and nothing
   typed asks nothing (nothing would be lost).
5. **Same meter, same minute** (the user's question): the server already
   refuses a second reading of one meter on one machine at one minute
   (`meters.py`, `SAME_MINUTE`, 409 on `taken_at`). A1 adds the browser test
   that proves it on the sheet: save a round at time T, *Enter more readings*,
   set *Time taken* back to T, type the same meter, save, and see the row's
   "A reading at this time exists. Pick another time, or remove that reading
   first." Other meters of the same round are not blocked by it.

**Where:** `frontend/src/views/ReadingsView.vue`,
`frontend/src/views/readings/ReadingSheetRow.vue` (read-only state),
`frontend/e2e/readings.spec.js` (the new round; the same-minute refusal; the
read-only state and the disabled *Saved* button). No backend change; no
migration. Docs: none expected (Plan.MD § 4.5 says "saved row by row", which
still holds).

**Tests:** red first where a test covers the fault (today *Enter more
readings* is missing); targeted e2e `readings.spec.js` and `screens.spec.js`.

**Out of scope:** S045's open iPhone-browser guard question (the user decides
later).

## Review log

### U1 — user answers, 24-10-2026 (before drafting S039)

- Readings per equipment; an end-of-day sheet per unit.

### U2 — user answers, 24-10-2026 (after S039 round 1)

- The sheet is its own step (this one).
- Operator and up log readings, not IT admin.
- A fixed 7-day back-date window, for everyone.

### U3 — user comments on the review page, 24-10-2026

- "One sheet one site": the sheet covers one site, grouped by unit; a site
  picker only for a user who logs at several sites (§ 1.2, § 1.4, § 3, § 5.1,
  § 6, decisions 4 and 8, § 8, § 9.1).
- A reading is removed only by `equipment:edit` holders (S039): *Undo* is
  theirs; others see that an engineer removes a wrong reading (§ 1.6,
  decision 2; the wording settled in round 2, BR2-03).
- The third meter kind, *Amount per period*: its row label and no reset tick
  (§ 1.4).
- The fourth kind, *Yes / No*: the row shows the question and two toggle
  buttons; *Save readings* saves it; *Not OK* when not the expected answer
  (§ 1.4, decision 9, § 8).

### U4 — approval, 24-10-2026

- "I have reviewed the brief. Except what I changed above, it all is
  accepted. Implement." Approved by KLA.
- D2: out-of-use machines folded away (§ 9.4 settled). D3: read-today marks
  (§ 9.5 settled). D10: one sheet per site (U3) settles the genset round
  within a site. D11: the words. D12: the clause numbers stay "to verify".

### Carried from S039's review round 1

S039 BR1-05 (the sheet's failure texts), BR1-06 (Undo, the hidden *Reset* tick,
no picker for one unit, Save disabled while saving), BR1-14 (the six-item
bottom bar), BR1-15 (the nav check as a vitest case) and BR1-17 (the
`localStorage` key) are answered in this brief (§ 1, § 8).

### Round 1 — `2-brief-review-r1.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 7 minor, 11 nits. No blocker or major; review loop complete.

| Finding | Answer |
|---|---|
| BR1-01 minor — a new units route duplicates `my-units` | Accepted (a): `my-units` gains `reading_unit_ids`; `readingUnits` in `stores/equipment.js`; the route and § 9.3 go; § 1.2, § 3, § 5.1, § 6, decision 6. S038 and S039 unchanged by it |
| BR1-02 minor — the *Reset* tick on a message text | Accepted (a): S039's counter-lower 400 sends `code: "counter_lower"` (S039 BR2-02, added there); the tick reads `err.code`; § 1.5 |
| BR1-03 minor — "no unit cannot occur" is wrong | Accepted: the `noUnits` message, no picker, no *Save readings*; § 1.8 |
| BR1-04 minor — the sticky button under the bottom bar | Accepted (a): a sticky bar inside `main.app-content`, above the nav, with the filled count; end padding; an e2e box check; § 1.6, § 8 |
| BR1-05 minor — a meter read today looks like yesterday's | Deferred to gate A — user. Proposed default (the reviewer's (a)) written into § 1.4 and § 9.5 |
| BR1-06 minor — out-of-use machines on the sheet | Deferred to gate A — user. Proposed default (in service and standby; out of use collapsed) written into § 1.4 and § 9.4 |
| BR1-07 minor — a part's card does not name its machine | Accepted (a): parts nested in the API and inside the machine's card; cards on desktop too; § 1.4, § 6, decision 7 |
| BR1-08…BR1-18 nits | All accepted. BR1-08: "a few queries, none per node". BR1-09: *Time taken* is `EventFields.vue`; switching units keeps it (also in S039 § 1.3). BR1-10: Undo disabled while saving; later rows editable. BR1-11: a 503 stops the loop. BR1-12: the empty-state locator in `screens.spec.js`; the empty state hides *Time taken* and *Save readings*. BR1-13: the one-unit and remembered-unit e2e case. BR1-14: a stale remembered unit falls back. BR1-15: S039 adds `reading:log` to the role lists, S040 the `visible(...)` lines (also in S039 § 3). BR1-16: ISO 9001 § 7.5.3 and ISO 14224 operating time in § 2. BR1-17: an inactive unit → 404 for admin too. BR1-18: meters in type name order. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 3 minor, 7 nits. Re-read the U3 sections only.

| Finding | Answer |
|---|---|
| BR2-01 minor — the site's name and active flag are not on the units list | Accepted (a): `readingSites(allUnits, allSites, mine)` over `ensureSites()` too, active sites only; the picker shows the code; the heading "SMTW — name" from the sheet GET; § 1.2, § 3, § 8 |
| BR2-02 minor — empty units; the supervisor's e2e case | Accepted (a): units with no machine with meters are not listed; a second machine per project at MCC1; the operator sees MCC2 only; § 1.4, § 6, § 8 |
| BR2-03 minor — "Ask an engineer" on every saved row | Accepted (a), the orchestrator's call for the user (who accepted every proposed default, U4): rows read *Saved*; one line per sheet, shown once after the first save; § 1.6, decision 2, § 8 |
| BR2-04…BR2-10 nits | All accepted. BR2-04: *Show out of use* at the end of each unit's group. BR2-05: "3 of 48 filled", one denominator. BR2-06: S039's amount help sentence. BR2-07: a 404 on the sheet forgets the site and shows the picker. BR2-08: S040's own readings in `beforeAll`; a delayed `page.route`. BR2-09: sticky unit headings. BR2-10: the picker stays in the empty state. |

From S039's review round 3: S039's Yes / No dialog now picks, then saves (S039
decision 11), so decision 9 and § 1.4 compare the two screens as alike.

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 2 minor, 8 nits, against ff9ddb3 + S037, S038, S039, S043. The design holds; all accepted.

| Finding | Answer |
|---|---|
| BS1-01 minor — the e2e set-up is not what S039 built | Accepted (a): a machine per test with `meterMachine` (own press model, `SMTW.MCC2`; a second at `SMTW.MCC1` for the supervisor), readings by `logByApi` on the MCC2 machine, the Yes / No type per project in `beforeAll`, assertions scoped to the test's own card and counts as a pattern; `SMTW-HYP-01` dropped; § 8 |
| BS1-02 minor — the failure set is 502, 503, 504 or no status | Accepted (a): § 1.7 and § 5.3 name the set; S039's `notSavedOr` lifted into one shared helper used by both screens |
| BS1-03…BS1-10 nits | All accepted. BS1-03: the three whole-dict `my-units` assertions extended. BS1-04: line numbers replaced by names (`my_units`, `accessible_unit_ids`, `_UNIT_SELECT`). BS1-05: Baseline names S043 (v31). BS1-06: `savedMessage` and the rest reused; sheet meters carry the `_meters_out` dict. BS1-07: `isToday` in `meterLabels.js`. BS1-08: the CLAUDE.md spec map in the docs pass. BS1-09: no technician list in `navigation.test.js`. BS1-10: pytest cases build their own sites and units. |
