```
Step: S052 — Meter readings on the ticket
Doc: brief
Author: Planner (Opus)
Date: 25-10-2026
Track: full
Baseline: refs/steps/S050 2e0e28f (staleness review s1, 25-10-2026, against S047, S051 and S050)
Status: Gate B (CR r1: 1 minor, 2 nits — all fixed in fix round 1; verify review r2: 2 nits CR2-01, CR2-02 — fixed in fix round 2; snapshot refs/steps/S052) (approved 25-10-2026 by KLA; coded after S050)
```

# S052 — Meter readings on the ticket

**The need (KLA, 25-10-2026).** "We need to be able to view the meter register of an equipment
(step is planned) from its ticket. Also maybe show the last meter reading on the ticket itself,
to give context." In the same conversation the planner proposed, and KLA asked for this brief:

- show each meter's reading **as it stood at the ticket's time** (*When it happened*), not the
  latest one: on a ticket three months old, today's run hours mean nothing;
- show how old that reading was ("2 d before"), because most meters are read once a day
  (S040's end-of-day sheet);
- warn when a gauge or a Yes / No check was marked in the 7 days before;
- work it out each time the ticket opens, with no migration.

In this brief, **the ticket's time** is the ticket's `occurred_at`, shown as *When it happened*.
It is the failure on a breakdown and the moment it was found on a defect.

Today the ticket page links the machine and part codes to the equipment page
(`TicketDetailView.vue` line 309 and 315). There the *Meters* card shows each meter's **latest**
reading (S039), and S050 (in review) adds the reading register.

**Built on** 4d89084 (S044) plus S046; S047 (e2e tooling) and S050 (register) are open. **This
step is coded after S050**: its *Open register* links open S050's register (§ 9 item 1). **No
migration, no new permission key, no write.**

## 1. What will be built

1. **A *Meters* card on the ticket page** (`TicketDetailView.vue`), after the row with
   *Details*, *Times* and *Assigned*, before *Parts used* (`PartsPanel`). Full width.
   - Under the header, one line: "Readings up to 23-10-2026 14:20, when it happened" (the
     ticket's time, the app's date-time format).
2. **The nodes shown.** The ticket's machine, then each node on the path down to the ticket's
   part (`component`), so at most three: machine → component-unit → component. A node shows
   only when it has at least one meter in force (S038). A heading per node: "code — name",
   with an *Open register* link on the right (§ 1.5).
   - Example: a ticket on a motor's bearing shows the press's strokes and oil temperature, then
     the motor's run hours. The bearing itself has no meter and is left out.
3. **One line per meter**, in the *Meters* card's order (S038):
   - the meter's name; the value as the equipment page shows it (`formatReading`, Indian
     grouping, the unit); the marks *High* / *Low* / *Not OK* / *Reset* (`readingBadges`),
     coloured with S050's `readingBadgeClass` from `meterLabels.js` (BS1-06);
   - the reading's time and its age before the ticket's time: "23-10-2026 06:00 · 8 h before"
     (§ 5.3 for the wording);
   - no reading at or before that time: "No reading before this time" in grey.
4. **The 7-day warning.** Under a meter whose readings in the 7 days up to the ticket's time
   carry a mark (a gauge *High* or *Low*, a Yes / No *Not OK*), one line with a warning icon:
   - gauge: "High or Low 3 times in the 7 days before";
   - Yes / No: "Not OK 2 times in the 7 days before";
   - "1 time" for one. Counters and amounts carry no mark, so never a warning.
   - The number of days comes from the answer's `mark_window_days` (§ 6), so the 7 lives only
     in `MARK_WINDOW_DAYS`.
   - The reading shown in item 3 counts too when it is inside the 7 days.
5. **The *Open register* link** per node (the label of S050's button on the equipment page,
   `MetersCard.vue:120`; one name for one thing, BS1-04) opens S050's register for that node:
   the link target is `{ path: '/readings', query: registerQuery(node.id) }`, S050's helper in
   `meterLabels.js` (as `MetersCard.vue:119` uses it), never a literal URL (BS1-01). Every role that sees the ticket may open it: every
   `ticket:read` holder has `equipment:read` (`*`), and S050 § 1.2 opens *Readings* to every
   `equipment:read` holder.
6. **The card is hidden** when no node of the path has a meter in force. Tickets on machines
   without meters stay as they are today.
7. **States** (scope B):
   - loading: **nothing** is drawn, so a ticket without meters never shows a card that then
     vanishes (BR1-05);
   - the answer has nodes: the card;
   - load failure (any error, 503 included): the card with "Meter readings could not be
     loaded. Try again in a minute." and a *Try again* button. The rest of the ticket page works
     as before;
   - the ticket's part is changed (*Edit*, S018): the card reloads. The ticket's time cannot be
     edited (`edit_ticket` changes the part, the symptom and the description only).

### Out of scope

- Saving the hours at the ticket's time on the ticket (for MTBF in run hours). That needs a
  column and belongs with the KPI work (§ 9 item 2).
- Meters **no longer on the node** (removed after the ticket's time). Only meters in force are
  shown (§ 7 decision 4).
- Readings **after** the ticket's time (§ 7 decision 3).
- Raising a ticket from a marked reading, or any write from this card.
- The card on the ticket list, the *Me* page or the raise screen.
- The parent machine's meters on an equipment page (S038 unchanged).
- The ticket page's own load-failure button, *Retry* (`TicketDetailView.vue:208`): this card
  and S050 use *Try again*; renaming *Retry* goes to the queued tidy-up (§ 9 item 5).

## 2. Standards and practice

- **ISO 14224:2016 (reliability and maintenance data):** the equipment data record holds the
  *operating time* (Table 5), and the failure rates of Annex C are counted per operating time,
  not calendar time. For equipment that does not run all the time (a standby press, a genset),
  the run hours or strokes at a failure are what reliability is measured in. This step
  **shows** that figure; storing it for analysis is out of scope. (Table and annex: checked by
  the brief reviewer, BR1-10; KLA may confirm against the standard.)
- **SMRP Best Practice metric 3.5.1, MTBF:** mean time between failures is operating time
  divided by the number of failures, so it is best counted in operating units (run hours,
  strokes, km) for machines whose duty varies. The figures shown here are the raw data for it
  later.
- **EN 13306, condition monitoring and fault diagnosis:** measurements of the actual state of an
  item, compared over time, help find the cause of a fault. A *High* oil temperature in the days
  before a hydraulic failure is a clue the technician should see at the machine.
- **TPM, autonomous maintenance (pillar 1):** the operators' daily readings are meant to be read.
  Showing them on the ticket makes the log useful to the person who repairs the machine.
- **Departure:** none. No KPI is computed and nothing is stored.

## 3. Where

### Backend

- `backend/meters_core.py`:
  - new constant `MARK_WINDOW_DAYS = 7`;
  - new pure function `mark_window(at)` → `since` (`at` − `MARK_WINDOW_DAYS` days); the window
    is (`since`, `at`];
  - new pure function `readings_at_ticket(meters, at_readings, mark_counts, node_id)` (§ 5.2):
    the node's meters in force, the readings the shell picked (already through `reading_out`),
    and the marked counts → the card's lines. It picks nothing and maps no words.
- `backend/meters.py`:
  - new route `GET /api/tickets/<ticket_id>/meters` (§ 6) on `meters_bp` (prefix `/api`),
    key `ticket:read` (§ 5.4);
  - `_last_readings(cur, node_ids)` gains an optional `until` (a naive IST datetime). With
    it, **both** the outer row and the `NOT EXISTS` neighbour are limited to
    `taken_at <= until`, so a reading after the ticket's time never hides an earlier one
    (BR1-02). Without it, the SQL is exactly as today (the S039 card, the S040 sheet);
  - new helper `_mark_counts(cur, node_ids, since, until)`: one query (§ 5.1 step 5);
  - imports `read_ticket` from `tickets.py` (no import cycle: `tickets.py` does not import
    `meters`; `meters.py` already imports `equipment`, which `tickets.py` also imports).
- `backend/equipment.py` — no change.

### Frontend

- `frontend/src/views/tickets/TicketMetersCard.vue` — new: the card (§ 1). Prop `ticket`
  (needs `id`, `occurred_at`, `component`). Loads on mount and when `ticket.component?.id`
  changes.
- `frontend/src/views/TicketDetailView.vue` — places the card after the *Details* row.
- `frontend/src/utils/meterLabels.js` — new pure helpers `beforeText(takenAt, at)` (§ 5.3,
  built on `ticketLabels.ageText`) and `markWarningText(kind, count, days)` (§ 1.4).

### Tests

- `backend/tests/test_meters_core.py` — `readings_at_ticket`, `mark_window` (§ 8.1).
- `backend/tests/test_readings_api.py` — the new route (§ 8.2). The existing
  `test_the_meters_list_carries_the_last_reading` (line 258) stays green unchanged: it guards
  `_last_readings` without `until`.
- `frontend/tests/meterLabels.test.js` — `beforeText`, `markWarningText` (§ 8.3).
- `frontend/e2e/tickets-work.spec.js` — new `S052:` tests (§ 8.4), set up by API
  (`raiseByApi`, `istLocal` in `e2e/support/tickets.js`; `meterMachine`, `logByApi` in
  `e2e/support/meters.js`).
- `frontend/e2e/screens.spec.js` — no change expected: the ticket route row already opens the
  page for every role that reads tickets. The coder checks it after the change.
- `backend/tests/test_rbac.py` — no change: no new key.

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` — § 4.5 *Meters and readings*: a "Built (S052)" line; § 4.2 tickets, one
  line that the ticket page shows the meters as they stood at the ticket's time.
- `.claude/CLAUDE.md` — § SMTW-Review, the spec-to-step map: `tickets-work` gains S052.
- No schema doc change (no migration). `docs/Keycloak.md`: no change.

## 4. Data model

No migration. The route reads `tickets` (through `read_ticket`), `equipment`, `node_meters`,
`model_meters`, `meter_types` (through `_meters_of`) and `meter_readings` (v32) through its index
`ix_meter_readings_meter_time (equipment_id, meter_type_id, taken_at)` (`local_db.py` line 995).

## 5. Rules

### 5.1 The route, step by step (the shell; plain reads, no locks)

1. `read_ticket(cur, ticket_id)`: 404 when the ticket is missing or not visible to the user
   (the ticket list's own visibility rule, `_visible_condition`). `at` = the ticket's
   `occurred_at`.
2. The machine: `load_node_for_user(cur, m_id, for_update=False, key="equipment:read")` (the
   ticket row's `m_id`).
3. The part, when the ticket has one (`c_id`): the same call, once. From that row (`gp_id`,
   `parent_id`), the nodes between the machine and the part, each read with the same call.
   The path is the ticket's machine first, then the part's ancestors below it, then the part;
   no node twice.
   - **A part moved to another machine since the ticket was raised** is left out, with its
     ancestors: the path is the machine only. Nothing stops such a move today (the scrap check
     `_check_no_open_tickets` is the only ticket guard on a node, `equipment.py:473`), and the
     part's meters now belong to another machine. The test: the part's machine as it is now
     (its `gp_id`, else its `parent_id`, as `tickets_core.machine_and_component` reads it) is not
     the ticket's `m_id`. This also keeps step 4 true: every node left is under the ticket's
     machine.
4. **Access is all-or-nothing** (BR1-01). Every node of the path is in the machine's unit:
   `_read_node`'s `root_unit_id` is `COALESCE(gp.unit_id, p.unit_id, e.unit_id)`
   (`equipment.py:150`, `:164`), and `load_node_for_user` checks it (`equipment.py:346`). A
   ticket is visible through its own unit *or* its machine's unit (`_visible_condition`), so a
   user may see a ticket whose machine is outside their units. Then the machine answers 404:
   the route catches that one `ApiError` (status 404), answers `nodes: []`, and the card is
   hidden; the ticket page is unaffected. The code comment says why. The 403 branch cannot
   happen today (`equipment:read` is `*`); it is not caught, so it would surface if the key
   ever narrows.
5. For each node: its meters in force, through `_meters_of(cur, node_id, node["model_id"])`
   (two queries per node; at most three nodes, so the sheet's bulk helpers are not needed,
   BR1-09). A node with no meter in force is dropped.
6. Two queries for all nodes left:
   - `_last_readings(cur, node_ids, until=at)`; each row through `reading_out(row, kind)`;
   - `_mark_counts(cur, node_ids, since, at)`, `since` from `mark_window(at)`:
     `SELECT equipment_id, meter_type_id, COUNT(*) FROM meter_readings WHERE equipment_id IN (…)
     AND removed_at IS NULL AND limit_state IS NOT NULL AND taken_at > %s AND taken_at <= %s
     GROUP BY equipment_id, meter_type_id`.
   None per meter.
7. `readings_at_ticket(…)` per node shapes the answer.

### 5.2 The core (`readings_at_ticket`)

1. Input: the node's meters in force (the order `_meters_of` gives, the equipment page's
   order); `{(node_id, meter_type_id): reading}` (the shell's pick, already through
   `reading_out`: value, `taken_at`, `limit_state`, `is_reset`); `{(node_id, meter_type_id):
   count}`.
2. One line per meter, in that order.
3. `at_ticket`: that meter's reading, or None when the shell found none.
4. `marked_count`: that meter's count, 0 when absent (a counter and an amount store no
   `limit_state`, so they are always 0).
5. The chosen reading is the active one with the greatest (`taken_at`, `id`) at or before the
   ticket's time; removed readings never count (S039 § 1.4). The shell's query decides this;
   the API tests prove it (§ 8.2).

### 5.3 The age text (`beforeText(takenAt, at)`, frontend)

- The same minute (the first 16 characters of the two times are equal): "at that time". The
  ticket's time may carry seconds (`parse_event_time` accepts `:SS`, `tickets_core.py:100`);
  readings are to the minute. A reading at 14:20 against a ticket at 14:20:30 reads "at that
  time".
- Otherwise: `${ageText(takenAt, new Date(at))} before`, the same words as the Details card's
  "(3 h ago)" on the same page: "12 min before", "8 h before", "2 d before". Whole units,
  rounded down (BR1-04).

### 5.4 Access

1. The route's key is `ticket:read`, checked by `require_perm` (a request without identity gets
   no access), then by `read_ticket`'s visibility (§ 5.1 step 1).
2. The path is then checked for `equipment:read` and the user's units (§ 5.1 step 4). The
   answer holds only readings the same user already sees on the equipment page's *Meters*
   card and *History*.
3. No `created_by`, note or reading id in the answer.
4. A scrapped node is shown like any other (read-only data).

### 5.5 Edge cases

- A ticket raised with a back-dated *When it happened* (S028): the ticket's time is that time,
  so readings logged later but **taken** before it count. Correct: the reading's time is when
  it was taken.
- A counter reset before the ticket's time: the reset reading shows with *Reset*, as on the
  card.
- Readings removed after the ticket was raised: they no longer count; the card shows the next
  older one. Accepted (§ 7 decision 1).
- A marked reading exactly 7 days before the ticket's time is outside the window (it is
  (`since`, `at`]); one a minute later is inside.
- The database down: `get_db()` raises `DBUnavailable` → 503; the card shows its load-failure
  message (§ 1.7) and the ticket page is unaffected.

## 6. API

`GET /api/tickets/<ticket_id>/meters` (`ticket:read`)

```json
{
  "at": "2026-10-23 14:20:00",
  "mark_window_days": 7,
  "nodes": [
    {"node": {"id": 12, "code": "MCC2-PR-04", "name": "Press 4", "level": "equipment"},
     "meters": [
       {"meter_type": {"id": 3, "name": "Run hours", "unit": "h", "kind": "counter", "decimals": 1},
        "at_ticket": {"value": "12345.6", "taken_at": "2026-10-23 06:00:00", "limit_state": null,
                      "is_reset": false},
        "marked_count": 0},
       {"meter_type": {"id": 9, "name": "Oil temperature", "unit": "°C", "kind": "gauge", "decimals": 0},
        "at_ticket": null,
        "marked_count": 0}
     ]}
  ]
}
```

- `nodes` is root first; a node with no meter in force is absent; `nodes: []` when none has
  one, or when the user cannot read the machine (§ 5.1 step 4). The screen then hides the card.
- `meter_type` is the shape `_meters_of` already gives (`meter_type_of`).
- Times in the API's usual format (`row_to_dict`); the sample is illustrative.
- Errors: 404 (ticket missing or not visible), 403 (no `ticket:read`), 503 (database down).

## 7. Design decisions

1. **Worked out on each view, not stored.** No migration; a reading entered late but taken
   before the ticket's time still counts. Rejected: saving each counter's value on the ticket
   when it is raised or closed. That is the right source for MTBF later, but it needs a
   column, a rule for which moment to freeze, and the KPI design first (§ 9 item 2).
2. **Its own route, loaded by the card.** The ticket detail (`GET /api/tickets/<id>`) is
   reloaded after every move; the meters do not change with moves. A failure of the meters
   query leaves the ticket page working. Rejected: adding `meters` to the ticket detail, which
   ties every ticket load to the meter tables.
3. **At or before the ticket's time, never after.** A reading after it may come from the repair
   or its test run, and would mislead. Rejected: the nearest reading on either side.
4. **Meters in force only.** The same list as the equipment page's *Meters* card. Rejected:
   also meters removed from the node since the ticket's time; rare, and S050's register shows
   them ("(removed)").
5. **The whole path, machine to part.** The machine's meters (strokes, oil temperature) matter
   for a fault on any of its parts, and a component-unit often has its own (a motor's run
   hours). Rejected: the ticket's node only (a part has meters less often than its machine).
6. **A machine the user cannot read gives an empty answer, not an error** (§ 5.1 step 4). The
   ticket stays readable, as `_visible_condition` allows; the meters are simply not shown.
   Rejected: a 404 for the route, which the card would show as a load failure.
7. **The route lives in `meters.py`**, which owns readings and their shaping, and reuses
   `read_ticket`. Rejected: in `tickets.py` (1418 lines), which would import the meter
   helpers.
8. **The 7-day window is a constant**, not a setting. Rejected: a setting in Settings; nobody
   has asked to change it, and the card states the window in its text.
9. **The age reuses `ageText`** (BR1-04), so the page says "2 d" in both places. Rejected: a
   third formatter with its own words ("2 days before") and an API field `minutes_before`.
10. **Nothing is drawn while loading** (BR1-05). Rejected: a "Loading…" line that appears and
    vanishes on every ticket without meters, moving the cards below it.

## 8. Tests and acceptance

### 8.1 Core (`test_meters_core.py`)

- `readings_at_ticket`: lines follow the meters' order; a meter without a reading →
  `at_ticket` None; the reading passes through unchanged; the count passes through and
  defaults to 0; an empty meter list → `[]`.
- `mark_window`: `at` − 7 days exactly.

### 8.2 API (`test_readings_api.py`)

- Happy path: a ticket on a machine with a counter and a gauge; readings before and after the
  ticket's time → the reading before (proves the `until` bound on the `NOT EXISTS`
  neighbour, BR1-02); a reading at exactly the ticket's minute counts.
- A ticket on a component under a component-unit under a machine: `nodes` root first; a node
  with no meter is absent.
- `marked_count`: three gauge readings marked *High* in the 7 days, one exactly 7 days before,
  one 8 days before, one after the ticket's time → 3. A removed marked reading does not count.
- A removed reading is never `at_ticket`; the older active one is.
- A Yes / No reading comes back as "yes" / "no".
- A machine with no meters → `nodes: []`.
- A ticket's part moved to another machine after the raise: only the ticket's machine is in
  `nodes`.
- 404 for an unknown ticket and for a ticket outside the user's units.
- A ticket visible through its own unit while its machine's unit is outside the user's units
  → 200, `nodes: []` (set up as `test_a_moved_machine_shows_to_the_old_and_the_new_unit`,
  `test_tickets_api.py:375`, with the conftest fixtures `make_ticket`, `node`, `at_unit`,
  `user_with_units`, `make_meter_type`).
- `db_down` fixture: 503.
- `test_the_meters_list_carries_the_last_reading` (line 258) unchanged and green.

### 8.3 Frontend unit (`meterLabels.test.js`)

- `beforeText`: the same minute, with and without seconds on the ticket's time → "at that
  time"; 12 min, 8 h and 2 d before.
- `markWarningText`: gauge and Yes / No, count 1 and 3, days 7.

### 8.4 Automated (e2e, `frontend/e2e/tickets-work.spec.js`, targeted; set-up by API)

- **important** — S052: a ticket on a press with a counter and a gauge, readings logged before
  and after the ticket's time: the ticket page's *Meters* card shows the reading before it with
  its age ("8 h before"), and *High* on the gauge.
- **important** — S052: a gauge marked *High* three times in the 7 days before shows "High or
  Low 3 times in the 7 days before".
- S052: *Open register* on the machine's heading opens S050's register for that node.
- S052: a ticket on a machine with no meters shows no *Meters* card. The test waits for the
  `/api/tickets/<id>/meters` response (`page.waitForResponse`) before it checks the card is
  absent, so it cannot pass during the load (BR1-05).
- S052: the ticket's *Meters* card fits the screen width, with no sideways scroll
  (`expectNoSidewaysScroll`, `e2e/support/dialogs.js:49`). A layout test: tagged `@device`
  (S047 § 1.3), so at Normal it runs on `phone-chromium` and `desktop-chromium` (BS1-03).
- The other four S052 tests are untagged logic tests; none is `@smoke`.

### 8.5 On a real device

None. Everything here is a layout or a flow a browser engine judges.

### 8.6 Acceptance

All suites green (`tooling/run-tests.bat`). Browser runs at the levels of S047 (BS1-02): the
targeted specs at Normal (`tickets-work.spec.js`, `screens.spec.js`) as often as needed; the
whole suite at Normal once when the coding is done (`tooling/run-e2e-tests.bat`, no `--level`
and no `--project`: a named `--project` turns the `@device` filter off); never `--level=full`.

## 9. Open questions and assumptions

1. **S050 comes first.** Assumed: S050 is approved and coded before this step, so the
   *Open register* link has a target. If S050 is dropped or delayed, the link opens the node's
   equipment page instead (`/equipment/<id>`), where the *Meters* card's *History* is. The
   stale-brief check at implement time covers S050's final URL.
2. **Storing the hours at the ticket's time** for MTBF in operating units. Proposed: a later
   step with the KPI work (Plan.MD § 8 phase 5, "History, reports": MTBF/MTTR). Not built here.
3. **The window of 7 days.** Decided by KLA, 25-10-2026: 7 days. It matches S039's
   back-dating window for readings (`READING_BACKDATE_DAYS = 7`, `meters_core.py:280`; BS1-05) and a
   week of daily rounds.
4. **Defects as well as breakdowns.** Decided by KLA, 25-10-2026: the card shows on every
   ticket, defects too; a defect's *When it happened* is when it was found.
5. ***Try again* or *Retry*.** Decided by KLA, 25-10-2026: *Try again* (a verb phrase, and it
   matches "Try again in a minute" everywhere else). This card and S050 say *Try again*; the
   ticket page's own *Retry* is renamed in the queued tidy-up.

## 10. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | minor | Accepted, option (a). § 5.1 step 4 now says access is all-or-nothing (every node is in the machine's unit); a 404 on the machine gives `nodes: []`; the 403 is not caught. Decision 6 and the § 8.2 test (`nodes: []`) changed. |
| BR1-02 | minor | Accepted, option (a). § 3: with `until`, both the outer row and the `NOT EXISTS` neighbour are bounded; without it the SQL is unchanged. § 8.2's happy path names it. |
| BR1-03 | minor | Accepted, option (a). The shell picks and runs `reading_out`; the core (`readings_at_ticket`) maps meters to lines and defaults counts. § 3, § 5.2, § 8.1 rewritten. |
| BR1-04 | minor | Accepted, option (a). `beforeText(takenAt, at)` on `ageText`; `minutes_before` dropped from the API and the core; § 5.3 rewritten; decision 9 added. |
| BR1-05 | minor | Accepted, option (a). Nothing drawn while loading; the "no card" e2e test waits for the response. § 1.7, § 8.4, decision 10. |
| BR1-06 | minor | Accepted, option (a). Header "Readings up to 23-10-2026 14:20, when it happened"; *Try again* kept, the page's *Retry* to the tidy-up (Out of scope, § 9 item 5). |
| BR1-07…BR1-14 | nit | Accepted: the `_mark_counts` predicate and `mark_window` in the core, the 7-day boundary test (07); the part read once, the path rule for a re-parented part (08); `_meters_of` per node, stated (09); ISO 14224 Table 5 / Annex C, SMRP 3.5.1 (10); seconds on the ticket's time (11); tests and fixtures named (12); "the ticket's time" instead of "the fault" (13); `markWarningText(kind, count, days)` from `mark_window_days` (14). |
| U1–U3 (gate A) | — | KLA approved on 25-10-2026: the window is 7 days (§ 9 item 3); the card shows on defects too (§ 9 item 4); *Try again*, the page's *Retry* renamed in the tidy-up (§ 9 item 5). |

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 25-10-2026

| Finding | Answer |
|---|---|
| BS1-01 minor — use S050's `registerQuery` | Accepted: the link target is `{ path: '/readings', query: registerQuery(node.id) }` (§ 1.5) |
| BS1-02 minor — the run instruction after S047 | Accepted: targeted Normal, the whole suite at Normal once with no `--project`, never Full (§ 8.6) |
| BS1-03 minor — the width test is `@device` | Accepted: tagged, `expectNoSidewaysScroll`, no device in the title; the other four untagged, none `@smoke` (§ 8.4) |
| BS1-04 minor — *Register* against S050's *Open register* | Accepted: *Open register* on the ticket card too, one name for one thing (CLAUDE-COMMON scope B) (§ 1.2, § 1.5, § 8.4) |
| BS1-05, BS1-06 nits | Accepted: `meters_core.py:280` (§ 9); badges coloured with `readingBadgeClass` (§ 1.3) |
