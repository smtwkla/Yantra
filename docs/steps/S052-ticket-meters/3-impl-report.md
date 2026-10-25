```
Step: S052 — Meter readings on the ticket
Doc: impl-report
Author: Coder (Opus)
Date: 25-10-2026
```

# S052 — Meter readings on the ticket: implementation report

The *Meters* card on the ticket page is built as briefed. It has one read-only route, two pure core functions and two frontend helpers. There is no migration, no new permission key and no write. All four suites pass, the build passes, and the targeted and whole browser suites at Normal pass (§ 6). There is no open question. Two small choices the brief does not settle are listed under *Decisions taken* (items 1 and 2).

## 1. What was built

- **A *Meters* card on the ticket page**, full width, after the row with *Details*, *Times* and *Assigned*, before *Parts used*.
  - Under the header: "Readings up to 23-10-2026 14:20, when it happened".
  - One heading per node of the path that has a meter in force: "code — name", with *Open register* on the right. The path is the ticket's machine, then the component-unit, then the component, root first.
  - One line per meter, in the equipment page's *Meters* card order:
    - the name, the value (`formatReading`: Indian grouping and the unit), and the *High* / *Low* / *Not OK* / *Reset* badges (`readingBadges`, coloured by `readingBadgeClass`);
    - under it "23-10-2026 06:00 · 8 h before" ("at that time" in the same minute), or "No reading before this time" in grey;
    - a warning line with a warning icon when the meter was marked in the 7 days before: "High or Low 3 times in the 7 days before", "Not OK 1 time in the 7 days before".
  - *Open register* goes to `{ path: '/readings', query: registerQuery(node.id) }`, S050's register for that node.
  - States: nothing is drawn while loading; nothing when no node has a meter; on any failure (503 too) the card shows "Meter readings could not be loaded. Try again in a minute." and *Try again*. The rest of the page works as before.
  - The card reloads when the ticket's part changes (*Edit*).
- **The route** `GET /api/tickets/<ticket_id>/meters` (`ticket:read`), in the brief's § 6 shape: `at`, `mark_window_days`, `nodes` (each `node` {id, code, name, level} and `meters` [{meter_type, at_ticket, marked_count}]).

## 2. How it works

- **Pure core (`meters_core.py`).**
  - `MARK_WINDOW_DAYS = 7`.
  - `mark_window(at)` returns `at − 7 days`. The window is (`since`, `at`], so a reading exactly 7 days before is outside it.
  - `readings_at_ticket(meters, at_readings, mark_counts, node_id)` maps the node's meters in force to lines, in their order. Each line is `{meter_type, at_ticket, marked_count}`: the shell's reading for that (node, meter type) or None, and the count or 0. It picks nothing and words nothing.
- **Shell (`meters.py`).**
  - `ticket_meters`: `read_ticket` first (404 for a missing or invisible ticket, the ticket list's own rule). `at` is the ticket's `occurred_at`.
  - `_ticket_path(cur, ticket)` builds the path:
    1. The machine, through `load_node_for_user(…, key="equipment:read")`. A 404 means the user sees the ticket through its own unit but the machine is now outside their units. The path is then empty, so the card is hidden (§ 5.1 step 4). A 403 is not caught.
    2. With a part (`c_id`): the part, read once with the same call. If its machine now (`tickets_core.machine_and_component`, from its `gp_id` / `parent_id`) is not the ticket's machine, the part was moved since the raise: the path is the machine only. If the part answers 404, it can only have left the machine's unit, so it is treated the same way (decision 1).
    3. A part under a component-unit (`gp_id` set): that component-unit, then the part.
  - For each node: `_meters_of(cur, node_id, model_id)` (two queries per node, at most three nodes). A node with no meter in force is dropped.
  - Two queries for all nodes left:
    - `_last_readings(cur, node_ids, until=at)`. With `until`, both the outer row and the `NOT EXISTS` neighbour are limited to `taken_at <= until`, so a reading after the ticket's time never hides an earlier one (BR1-02). Without `until`, the SQL text and parameters are exactly as before (the S039 card, the S040 sheet).
    - `_mark_counts(cur, node_ids, since, at)`: active rows with `limit_state IS NOT NULL` and `taken_at > since AND taken_at <= at`, grouped by node and meter type.
  - Each picked row goes through `reading_out(row, kind)` (a Yes / No value as "yes" / "no"), then `readings_at_ticket` shapes the node's lines. The answer carries no reading id, no `created_by` and no note: `_last_readings` does not select them.
- **Frontend.**
  - `meterLabels.js`:
    - `beforeText(takenAt, at)` returns "at that time" when the first 16 characters match (the same minute; the ticket's time may carry seconds). Else it returns `${ageText(takenAt, new Date(at))} before`, the Details card's words (whole units, rounded down).
    - `markWarningText(kind, count, days)` returns the warning for a gauge or a Yes / No meter, or null for no mark or for another kind. `days` comes from the answer's `mark_window_days`.
  - `TicketMetersCard.vue` (prop `ticket`) loads on mount. A two-source watch on `ticket.id` and `ticket.component?.id` compares values, so the page's reload after every move does not load the card again. A sequence number drops a late answer.

## 3. Files touched

| File | Change |
|---|---|
| `backend/meters_core.py` | `MARK_WINDOW_DAYS`, `mark_window`, `readings_at_ticket`; module docstring line |
| `backend/meters.py` | `_last_readings(…, until=None)`; `_mark_counts`; `_node_or_none`, `_ticket_path`; route `ticket_meters`; imports `read_ticket`, `machine_and_component`; docstring paragraph |
| `backend/tests/test_meters_core.py` | `TestReadingsAtTicket` (6 tests), `TestMarkWindow` (1) |
| `backend/tests/test_readings_api.py` | `TestTicketMeters` (14 tests) |
| `frontend/src/utils/meterLabels.js` | `beforeText`, `markWarningText`; imports `ageText` from `ticketLabels.js` |
| `frontend/tests/meterLabels.test.js` | four S052 tests |
| `frontend/src/views/tickets/TicketMetersCard.vue` | new: the card |
| `frontend/src/views/TicketDetailView.vue` | places the card; the page's layout comment |
| `frontend/e2e/tickets-work.spec.js` | five S052 tests and a set-up helper `pressTicket` |
| `docs/Plan.MD` | § 4.5 "Decided (S052)" line replaced by "Built (S052)"; § 4.2 one line |
| `.claude/CLAUDE.md` | § SMTW-Review spec map: `tickets-work` S018/S052 |
| `docs/steps/S052-ticket-meters/1-brief.md` | Status: In code review |
| `docs/steps/README.md` | S052 row: In code review; "*Register* link" now "*Open register* link" (BS1-04) |

13 files (1 new source file, plus this report).

## 4. Decisions taken

1. **A 404 on the part is treated as "moved away" (forced; the brief names the 404 only for the machine).** The machine has passed the access check, and every node under it shares its unit. So a 404 on the part can only mean it left the machine's unit since the raise, which § 5.1 step 3 already leaves out. Without the catch, the route would answer 404 and the card would show its load-failure message on a ticket the user reads. The test `test_a_part_moved_out_of_the_user_s_units_is_left_out` covers it. The component-unit between them is not caught: once the part is still under the machine, the component-unit is too.
2. **On a part change the card keeps the previous answer until the new one arrives.** It clears only when the ticket id changes. The brief says "the card reloads" and does not say what shows meanwhile. Clearing would make the card vanish and come back, the jump § 7 decision 10 avoids.
3. **`meterLabels.js` now imports `ageText` from `ticketLabels.js`.** The brief asks for `beforeText` built on `ageText`, so the module is no longer import-free; its header comment says so. `ticketLabels.js` imports only `datetime.js`, so there is no cycle.
4. **Small helpers:** `_node_or_none` (one 404 catch for the machine and the part) and `_ticket_path` in `meters.py`; `pressTicket` in the e2e spec. In the API tests: `_ticket_at` and `_taken_at` write the ticket's and a reading's time straight to the row, for times the API refuses (more than 7 days back) or that must be exact against each other.
5. **The answer's `meter_type` carries `expected_answer`**, as `_meters_of` gives it (§ 6: "the shape `_meters_of` already gives"). The § 6 sample shows five keys; the sample is illustrative.
6. **Reuse:** `read_ticket`, `load_node_for_user`, `_meters_of`, `_last_readings`, `reading_out`, `_marks`, `machine_and_component`, `formatReading`, `readingBadges`, `readingBadgeClass`, `registerQuery`, `ageText` and `formatDateTime`. No new query helper repeats an existing one.

No departure from the brief.

## 5. Not done, deferred or assumed

- Out of scope as briefed: storing the hours at the ticket's time (MTBF), meters removed from the node, readings after the ticket's time, the card elsewhere, and renaming the page's *Retry* (queued tidy-up).
- `screens.spec.js`: no change needed. The ticket route row passed in the targeted and the Normal runs.
- `test_rbac.py`: no change (no new key). The new route's 403 for a role without `ticket:read` (the storekeeper) is in `test_the_storekeeper_is_403`.
- No `device-checks.md` row: § 8.5 has none.

## 6. Tests

- **Core, red then green:** the core tests ran green before the shell was written (`test_meters_core.py`, 173 passed).
- **BR1-02, red then green:** I removed the bound on the `NOT EXISTS` neighbour only and ran `test_the_reading_at_or_before_the_ticket_s_time_with_its_marks` alone. It fails without the bound (`assert None == {'value': '105', …}`) and passes with it.
- **Targeted while coding:** `test_meters_core.py`, `test_readings_api.py`, `test_rbac.py` (312 passed); `meterLabels.test.js` (23 passed).
- **Browser:**
  - the five new tests alone, `E2E_LANES=1`, `--project=phone-chromium -g S052`: 5 passed;
  - targeted Normal, `e2e/tickets-work.spec.js e2e/screens.spec.js` (the ticket page's spec and every route): 48 passed, 1 skipped (S040's phone bottom bar on `desktop-chromium`, by design);
  - the whole suite at Normal once (`tooling/run-e2e-tests.bat`, no flag): 209 passed, 4 skipped (the S021 iPhone and blocked-notification checks and the S040 bottom bar, project-specific skips that existed before).
- **Final full run** (`YANTRA_TEST_RUN=s052c1 tooling/run-tests.bat`): backend 3075 passed, frontend 179 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- `npx vite build`: built, with the usual chunk-size warning only.

## Manual checks

All the brief's checks are automated (§ 8.4); § 8.5 has no real-device check.

- [auto] **important** — a ticket on a press with a counter and a gauge, readings before and after the ticket's time: the card shows the reading before it with its age ("8 h before"), and *High* on the gauge — `frontend/e2e/tickets-work.spec.js`::"S052: the ticket's Meters card shows the reading before the ticket's time with its age, and High on the gauge"
- [auto] **important** — a gauge marked *High* three times in the 7 days before shows "High or Low 3 times in the 7 days before" — `frontend/e2e/tickets-work.spec.js`::"S052: a gauge marked High three times in the 7 days before shows the warning"
- [auto] *Open register* on the machine's heading opens S050's register for that node — `frontend/e2e/tickets-work.spec.js`::"S052: Open register on the machine's heading opens the register for that machine"
- [auto] a ticket on a machine with no meters shows no *Meters* card, checked after the meters answer arrives — `frontend/e2e/tickets-work.spec.js`::"S052: a ticket on a machine with no meters shows no Meters card"
- [auto] the ticket page with the card has no sideways scroll (`@device`: `phone-chromium` and `desktop-chromium` at Normal) — `frontend/e2e/tickets-work.spec.js`::"S052: the ticket page with the Meters card has no sideways scroll"

- [auto] when the Meters card cannot load it says so, and *Try again* keeps the card in place until the answer arrives — `frontend/e2e/tickets-work.spec.js`::"S052: when the Meters card cannot load it says so; Try again keeps the card in place until the answer arrives"
- [auto] changing the ticket's part reloads the Meters card with the part's node — `frontend/e2e/tickets-work.spec.js`::"S052: changing the ticket's part reloads the Meters card with the part's node"

## Docs updated

- `docs/Plan.MD`: § 4.5, the "Decided (S052)" line became "Built (S052, 25-10-2026)" with what was built (path, at-or-before rule, age, warning window, hidden states, the route and its keys); § 4.2, one line "Meters on the ticket".
- `.claude/CLAUDE.md`: § SMTW-Review, the spec-to-step map now reads `tickets-work` S018/S052.
- `docs/schema.md`, `docs/schema.html`: none, because there is no migration.
- `docs/Keycloak.md`, `backend/example_secrets_app.py`: none, because no role, claim or secret changed.
- `docs/steps/device-checks.md`: none, because § 8.5 has no real-device check.

## Fix rounds

### Round 1 (code review r1)

- **CR1-01 (minor): Fixed.** `TicketMetersCard.vue` clears `loadError` only when an answer arrives, so the card keeps its text and the cards below do not jump during *Try again*. A `loading` ref disables *Try again* while a load runs. One related change: a new ticket id also clears `loadError`, so an error of one ticket never shows on the next.
  - Test: `frontend/e2e/tickets-work.spec.js`::"S052: when the Meters card cannot load it says so; Try again keeps the card in place until the answer arrives". It routes the meters call to a 503, then holds the retry in flight and checks the card, its text and the disabled button, then lets the answer through and checks the reading.
  - Red then green: fails without the fix (`expect(meters).toContainText("Meter readings could not be loaded.")`, element not found, the card has vanished); passes with it.
  - There are no component tests in the frontend suite (no mount utility), so the check is an e2e test.
- **CR1-02 (nit): Fixed.** The header comment of `frontend/src/utils/meterLabels.js` is re-wrapped to the file's width.
- **CR1-03 (nit): Fixed.** Two new e2e tests: the load-failure state with *Try again* (above, a routed 503 then success), and "S052: changing the ticket's part reloads the Meters card with the part's node" (Edit the ticket's part to a component-unit with a meter; the card shows a second node). Neither is a fix to code, so no red run applies to the second (it passes on the unchanged reload code).
- **Tests:** targeted Normal `e2e/tickets-work.spec.js e2e/screens.spec.js`: 50 passed, 1 skipped (S040's bottom bar on desktop, by design). `YANTRA_TEST_RUN=s052c2 tooling/run-tests.bat`: backend 3075, frontend 179, deps 42, tooling 168, all passed. `npx vite build`: built, usual chunk warning only. No whole-suite browser run (no shared frontend code changed).
- **Docs:** none due, because the fixes change no behaviour a doc describes.
- **Manual checks:** two more `[auto]` checks, the two tests named above.

### Round 2 (code review r2, async)

- **CR2-01 (nit): Fixed.** In "S052: changing the ticket's part reloads the Meters card with the part's node", the click on *Edit* is now followed by `openDialog(page)` and `expectDialogFits(page)` (both already imported from `support/dialogs.js`). The field is set only after the dialog is open and has focus. No red run: this is a test-hygiene change, not a fault fix.
- **CR2-02 (nit): Fixed.** `## Manual checks` now lists the two `[auto]` checks of round 1: the load-failure state with *Try again*, and the part change reloading the card.
- **Tests:** `YANTRA_TEST_RUN=s052c3 tooling/run-e2e-tests.bat e2e/tickets-work.spec.js -g "S052"` at Normal: 8 passed (7 S052 tests on `phone-chromium`; the `@device` test also on `desktop-chromium`). No other runs.
- **Docs:** none due.
