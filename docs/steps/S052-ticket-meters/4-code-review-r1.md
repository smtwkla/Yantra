```
Step: S052 — Meter readings on the ticket
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 25-10-2026
```

# S052 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** There is one `minor` finding (the *Try again* button makes the card vanish while it reloads) and two nits. The route, the core and the card match the brief and its staleness answers. All four suites pass, and the build passes.

Diff reviewed: the working tree against `refs/steps/S050`, limited to the 13 files the impl report names, plus the new `frontend/src/views/tickets/TicketMetersCard.vue` (read in full). I also read `equipment.load_node_for_user`, `tickets.read_ticket` / `_find_ticket` / `_visible_condition` / `_TICKET_COLUMNS`, `tickets_core.machine_and_component`, `meters._meters_of` / `reading_out`, `ticketLabels.ageText`, and the parts of `TicketDetailView.vue` that set `ticket`.

## Tests run

- `YANTRA_TEST_RUN=s052cr1 tooling/run-tests.bat`: backend 3075 passed, frontend 179 passed, deps 42 passed, tooling 168 passed. ALL SUITES: PASSED.
- `npx vite build` in `frontend/`: built in 3.8 s, with the usual chunk-size warning only.
- Browser: not re-run (standing rule, 25-10-2026). The coder ran the right specs: targeted Normal `tickets-work.spec.js` + `screens.spec.js` (48 passed, 1 skipped), and the whole suite at Normal once (209 passed, 4 skipped). The skips are the known project-specific ones. None of my findings needs a browser run.

## Findings

### CR1-01 (minor) — *Try again* makes the card vanish until the answer arrives

- **Where:** `frontend/src/views/tickets/TicketMetersCard.vue:34` with `:56`.
- **Problem:** `load()` sets `loadError` to false before the request. After a failed first load, `answer` is still null. While the retry runs, the root `v-if` (`loadError || answer?.nodes.length`) is false, so the whole card disappears.
- **Failure scenario:**
  1. A technician opens a ticket while the database is down. The card shows "Meter readings could not be loaded. Try again in a minute."
  2. The technician taps *Try again* on a slow plant Wi-Fi.
  3. The card vanishes, and *Parts used* and the timeline jump up under the thumb.
  4. If the retry fails again, the card comes back with the same text, and the cards jump down again. A second tap may land on whatever moved under the finger.
  This is the jump that § 7 decision 10 (BR1-05) rejects for the first load.
- **Suggested fix:** keep the error text on the card until the new answer arrives. For example, clear `loadError` only when an answer succeeds (`if (seq === loadSeq) { answer.value = result; loadError.value = false; }`), and disable *Try again* while a load runs (a `loading` ref). A unit or e2e check is optional; the code change is small.

## Nits

- **CR1-02** (nit) `frontend/src/utils/meterLabels.js:5`: the edited header line runs to about 150 characters. Re-wrap it to the file's width.
- **CR1-03** (nit) `frontend/e2e/tickets-work.spec.js` (S052 block): no test covers the card's load-failure state (§ 1.7) or the reload after a part change (decision 2). Consider one e2e test that routes `/api/tickets/<id>/meters` to a 503 (`page.route`) and checks the message and *Try again*. Neither is in the brief's § 8 list, so this is optional.

## Checked and found consistent

- **Access (§ 5.4).**
  - The route is `require_perm("ticket:read")`, the same key as the ticket detail. A request without identity gets no access (the decorator). The storekeeper's 403 is tested.
  - `read_ticket` gives a 404 for a missing or invisible ticket (`_visible_condition`, site-scoped through `accessible_unit_ids(cur, READ_KEY)`). Both 404s are tested.
  - Every node goes through `load_node_for_user(…, for_update=False, key="equipment:read")`, so it checks the user's units and the key at the node's site (`SITE_SCOPED`).
  - `_node_or_none` catches only `status == 404` and re-raises anything else, so a future 403 surfaces as the brief asks.
  - The machine's 404 gives `nodes: []`. This is tested in `test_a_ticket_seen_through_its_unit_with_its_machine_moved_away_gives_no_nodes`, which also checks that the new unit's reader sees the node.
  - The part's 404 counts as "moved away" (decision 1). The reasoning holds: the machine passed the check, and every node under it shares its root unit (`COALESCE(gp.unit_id, p.unit_id, e.unit_id)`). It is tested, and the report lists it under *Decisions taken*.
  - The component-unit read is not caught. That is right, because once the part's machine equals the ticket's machine, its parent is under that machine.
  - The answer carries no reading id, `created_by` or note: `_last_readings` selects none of them, and `reading_out` copies only the fields present.
- **`_last_readings(…, until=at)`.** With `until`, both the outer row and the `NOT EXISTS` neighbour are bounded (`r.taken_at <= %s`, `n.taken_at <= %s`), with the parameters in order. Without `until`, the SQL text and parameters are byte-for-byte the old ones (the S039 card, the S040 sheet). The red-then-green for BR1-02 is recorded.
- **`_mark_counts`.** One grouped query for all nodes, `removed_at IS NULL AND limit_state IS NOT NULL AND taken_at > since AND taken_at <= until`, so the window is (`at` − 7 d, `at`]. The tests cover exactly 7 days (outside), 7 days less a minute (inside), 8 days, after the ticket's time, a removed reading, an unmarked reading and a counter. The route makes two reading queries in total, none per meter. `_meters_of` runs per node, for at most three nodes (BR1-09).
- **Pure core.** `MARK_WINDOW_DAYS = 7`, `mark_window` and `readings_at_ticket` have no DB access, no clock and no framework. They follow the meters' order, default the count to 0, ignore another node's keys and give `[]` for no meters. The core tests ran green before the shell was written.
- **Edge cases.**
  - A reading at the ticket's minute while the ticket's time has seconds: tested in the API and in `beforeText`.
  - A removed reading is never `at_ticket`; the older active one is: tested.
  - A Yes / No reading comes back as "no" with `not_ok`: tested.
  - A reset shows through `readingBadges` (`is_reset` from `reading_out`), the same path as the equipment card.
  - DB down: 503, tested.
- **Path rule (§ 5.1 step 3).** A part moved to another machine, and one moved out of the user's units, both leave only the machine: tested. Root first, and a node with no meter absent: tested with machine → component-unit → component.
- **Imports.** `meters.py` imports `tickets.read_ticket` and `tickets_core.machine_and_component`. Only `app.py` imports `meters`, so there is no cycle. `meterLabels.js` imports `ageText` from `ticketLabels.js`, which imports only `datetime.js`: no cycle (decision 3).
- **The card.**
  - Nothing is drawn while loading, and nothing when `nodes` is empty.
  - The two-source watch compares values, so the page's reload after a move does not reload the card. A part change keeps the old answer until the new one arrives, and a new ticket id clears it (decision 2). The sequence number drops a late answer.
  - Reuse: `formatReading`, `readingBadges`, `readingBadgeClass`, `registerQuery`, `formatDateTime` and `ageText`. No near-copy of an existing helper.
  - *Open register* is a link to `{ path: '/readings', query: registerQuery(node.id) }`, at least 44 px high, not `btn-sm`.
  - Long codes and names wrap (`text-break`, `flex-wrap`). The `@device` no-sideways-scroll test passed on both Normal devices.
- **Writing style, scope B.** "Readings up to …, when it happened", "No reading before this time", "High or Low 3 times in the 7 days before", "Meter readings could not be loaded. Try again in a minute." and *Try again* are short and plain, and match the brief. *Open register* matches S050's button (BS1-04).
- **e2e.**
  - Each of the five § 8.4 checks has a test that asserts what the user sees: the values, the age line, the badge, the warning text, the register's node heading, and the card's absence after the response (BR1-05).
  - Only the layout test is tagged `@device`, with the reason in the brief. None is `@smoke`.
  - No dialog is opened, so `expectDialogFits` does not apply.
- **Docs pass.** `docs/Plan.MD` § 4.5 has the "Built (S052)" line and § 4.2 has one line. `.claude/CLAUDE.md` maps `tickets-work` to S018/S052. No migration, so no schema doc change is due. No secret, role or real-device check, so the other docs are not due. The README index row is updated.
- **Scope.** Everything in § 1 is built. Nothing outside the brief is built. The departures (decisions 1–5) are in the report.
- **Manual checks.** The impl report's `## Manual checks` carries both **important** checks and the three others as `[auto]`, each with its test. § 8.5 has no real-device check.

## Manual browser check for the user

None required. If you want to look by eye, open a ticket on a press with meters, on a phone, and check that the *Meters* card reads well under *Details*.
