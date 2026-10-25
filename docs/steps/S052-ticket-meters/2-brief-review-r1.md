```
Step: S052 — Meter readings on the ticket
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 25-10-2026
```

Reviewed against: 4d89084 (no step's code is uncommitted; the working tree holds doc changes only)

**Verdict: no `blocker` or `major` is open.** Six `minor` findings and eight nits. The design (computed at view time, its own route, at or before the ticket's time, the path machine → part) holds against the code and Plan.MD. The minors are: a wrong reason in the access rule (the whole path shares one unit, so the skip is all-or-nothing), the `until` bound that must reach into the `NOT EXISTS` neighbour, an unsettled core input shape, a third age formatter where `ageText` already exists on the same page, a card that flashes and vanishes on every ticket without meters, and two UI texts. Facts file used: `scratch/brief-facts-S052.md`.

## Findings

### BR1-01 — minor — § 5.1 step 3, § 7 decision 6, § 8.2: the per-node skip is all-or-nothing, and the reason given is wrong

**Problem.** The brief says a node that answers 404 is left out "and the others are still shown", and decision 6 rejects a 404 "which would hide the machine's meters too". Every node of the path shares one unit: `_read_node`'s `root_unit_id` is `COALESCE(gp.unit_id, p.unit_id, e.unit_id)` (`equipment.py:150`, `:164`), and `load_node_for_user` checks that column (`equipment.py:346`). So the machine, the component-unit and the component all pass or all fail. When the machine's unit is outside the user's units, the card shows nothing (`nodes: []`), not "less". The 403 branch is dead too: `equipment:read` is `("*",)` (`config_rbac.py:91`), and `has_perm_at` passes on the token's permission list before the site check (`auth_utils.py:396`).

**Why it matters.** The coder would write a comment that is false, and the § 8.2 test "that machine absent" reads as if a part could still show. A later reader would hunt for the case where the part shows and the machine does not; it cannot happen.

**Options.**
- (a) Keep the per-node `load_node_for_user` call (it also gives the row with `model_id`), and fix the text: "every node of the path is in the machine's unit, so the check answers the same for all; a 404 means `nodes: []` and the card is hidden; the ticket page is unaffected". Drop the 403 from the skip, or keep it as "cannot happen today". Change the § 8.2 test to "→ 200, `nodes: []`". **Recommended.**
- (b) Check the machine once with `load_node_for_user`, and read the parts with a plain `_read_node`. Saves nothing worth having at three nodes.

### BR1-02 — minor — § 3 `_last_readings(until)`: the bound must apply to the `NOT EXISTS` neighbour too

**Problem.** `_last_readings` (`meters.py:266`) finds the newest reading as the one with no later active reading (`NOT EXISTS … n.taken_at > r.taken_at`). The brief says only that "newest means newest at or before `until`". If the coder adds `r.taken_at <= until` to the outer row and leaves the subquery as it is, a reading logged after the fault is a "later one" for every pre-fault reading, so the query returns no row and `at_fault` is None for every meter that was read after the fault — exactly the common case the step is for.

**Why it matters.** The § 8.2 happy path (readings before and after the fault) would catch it, but the brief should say the rule, not leave it to the test.

**Options.**
- (a) State in § 3: with `until`, both the outer row and the `NOT EXISTS` neighbour are limited to `taken_at <= until`; without it both are unbounded, so the SQL for the S039 card and the S040 sheet is byte-for-byte unchanged. **Recommended.**
- (b) A separate helper `_readings_at(cur, node_ids, at)`. Two copies of one query; not worth it.

### BR1-03 — minor — § 3, § 5.2, § 8.1: what the core receives is not settled, and § 5.2.5 names a shell function

**Problem.** § 3 says the core gets "its reading at or before `at` per meter type" (one row per meter, from `_last_readings(until=at)`), while § 8.1 tests `readings_at_fault` on "readings before and after `at` → the newest at or before `at` per meter", which means the core picks among several. § 5.2.5 says "the value goes out as `reading_out` gives it", but `reading_out` lives in `meters.py` (the shell, `:257`) and uses `row_to_dict`; `meters_core` cannot import it.

**Why it matters.** The coder must choose the core's input shape and where the Yes / No word mapping happens; S039 BR3-04 put that mapping in one place (`answer_word`, through `reading_out`).

**Options.**
- (a) The shell does the picking (one query) and runs `reading_out(row, kind)` on each row before calling the core; the core's input is `{(node_id, meter_type_id): reading_dict}` and `{(node_id, meter_type_id): count}`; the core maps meters to lines, computes `minutes_before` (if it stays, BR1-04) and `marked_count` (0 when absent), and returns plain dicts. § 8.1 then tests: order follows the meters, a meter without a row → `at_fault` None, the count passes through and defaults to 0, `minutes_before` cases. "Newest at or before `at`" is the API test's (§ 8.2 happy path). **Recommended.**
- (b) The core receives every active reading of the nodes and picks. There is no window for `at_fault` (the last reading may be months back), so the shell would fetch whole histories.

### BR1-04 — minor — § 3, § 5.3: `beforeText` is a third age formatter; the same page already uses `ageText`

**Problem.** `ticketLabels.ageText` (`ticketLabels.js:106`) gives "N min" / "N h" / "N d" and is shown in the Details card right above the new card ("(3 h ago)", `TicketDetailView.vue:331`); `minutesText` (`:262`) gives "2 d 3 h". The brief adds `beforeText` with its own thresholds (days from 48 h, not 24 h) and its own words ("2 days before"). One ticket page would then say "2 d ago" and "2 days before" for the same kind of thing.

**Why it matters.** One term for one thing, and no parallel helper (CLAUDE-COMMON). It also makes the API's `minutes_before` and the core's `minutes_before` unnecessary: both time strings are IST ISO strings that `ageText` already parses.

**Options.**
- (a) In `meterLabels.js`: `beforeText(takenAt, at)` → "at that time" when the two are the same minute, else `${ageText(takenAt, new Date(at))} before` ("8 h before", "2 d before"). Drop `minutes_before` from the API and the core, and § 5.3's table; § 8.3 tests the same-minute case and one of each unit. **Recommended.**
- (b) Keep `minutes_before` in the API and build `beforeText` on `minutesText(minutes)` ("8 h 20 min before"). More precise than the card needs, but no new thresholds.

### BR1-05 — minor — § 1.6, § 1.7: the card shows "Loading…" on every ticket, then vanishes on a machine without meters

**Problem.** The card is hidden when `nodes` is empty, but it shows a spinner line while loading. Early on most tickets are on machines without meters, so on every such ticket a card appears under the Details row and disappears a moment later, pushing *Parts used* and the timeline down and up again, on a phone most of all.

**Why it matters.** A layout jump on the page's most-used part, for no information.

**Options.**
- (a) Render nothing while loading; render the card when the answer has nodes, or when the load failed (the failure message and *Try again*). The § 8.4 "no *Meters* card" test must then wait for the meters response (`page.waitForResponse` on `/api/tickets/<id>/meters`) before asserting absence, or it passes trivially during the load. **Recommended.**
- (b) Keep the spinner line but reserve no card frame around it (a plain grey line). Still a jump.

### BR1-06 — minor — scope B: the card's header line, and *Try again* against the page's *Retry*

**Problem.** "Last reading at or before 23-10-2026 14:20, when it happened." carries two ideas and a trailing clause; "at or before" is the rule, not what the user needs. And the failure state's button is *Try again* while the ticket page's own load-failure button two cards up says *Retry* (`TicketDetailView.vue:208`); S050 also uses *Try again*.

**Why it matters.** One word for one action across the app; a short header a low-literacy user follows.

**Options.**
- (a) Header: "Readings up to 23-10-2026 14:20, when it happened". Button: settle one word for S050 and S052 (*Try again* reads as the verb form the base asks for), and queue the ticket page's *Retry* for the tidy-up step. **Recommended.**
- (b) Match the page: *Retry* here and in S050. Fewer edits, but *Retry* is the odd one out against "Try again in a minute" everywhere else.

## Nits

- **BR1-07** (nit) § 5.1 step 5, § 5.2.4: write the `_mark_counts` predicate (`removed_at IS NULL AND limit_state IS NOT NULL AND taken_at > %s AND taken_at <= %s`, `GROUP BY equipment_id, meter_type_id`), and let the core give the window (`mark_window(at)` → `since`) so the 7-day boundary is tested in `test_meters_core`; add "exactly 7 days before: not counted" to § 8.2.
- **BR1-08** (nit) § 5.1 steps 2–3: the part is read twice (its `_read_node` row for the path, then `load_node_for_user`); read it once with `load_node_for_user` and take `gp_id` / `parent_id` from that row (`_read_node` is private to `equipment.py`). Say what happens when the part's ancestors are not the ticket's machine (re-parented since the raise): the ticket's machine first, then the part's ancestors, no node twice.
- **BR1-09** (nit) § 5.1 step 4: `_meters_of` is two queries per node; the sheet's `read_models_meters` + `_nodes_rows` + `effective_meters` (`meters.py:469–476`) do every node in two. Either is fine at three nodes; say which.
- **BR1-10** (nit) § 2: ISO 14224:2016 keeps *operating time* in Table 5 (equipment data) and computes failure rates per operating time in Annex C; a Table 6 (failure data) field "operating time at failure" I cannot confirm. Cite Table 5 / Annex C, or leave "to verify" for KLA. SMRP 3.5.1 as MTBF is consistent with Maintenance-Philosophy § 10's SMRP 3.5.5 numbering, and SMRP's MTBF is operating time ÷ failures, so that claim holds.
- **BR1-11** (nit) § 1.4, § 5.5: `occurred_at` may carry seconds (`parse_event_time` accepts `:SS`, `tickets_core.py:100`; tickets do not truncate), readings are to the minute. Say the age rounds down and that a reading at 14:20 against a fault at 14:20:30 reads "at that time".
- **BR1-12** (nit) § 3, § 8.2: name the tests: the S039 `last` test is `test_the_meters_list_carries_the_last_reading` (`test_readings_api.py:258`); the S017 unit-move test is `test_a_moved_machine_shows_to_the_old_and_the_new_unit` (`test_tickets_api.py:375`); `make_ticket`, `node`, `at_unit`, `user_with_units` and `make_meter_type` are in `conftest.py`.
- **BR1-13** (nit) scope A: the brief says "the fault" for the ticket's time in § 1, § 5 and § 7, while the glossary keeps *failure* for the event and *fault* for the state after it, and a defect is neither. Use "when it happened" or "the ticket's time" in the brief; the UI texts already do.
- **BR1-14** (nit) § 1.4, § 6: the screen's "in the 7 days before" should take the number from the answer's `mark_window_days`, so the constant lives once (`MARK_WINDOW_DAYS`); say so in § 3 (`markWarningText(kind, count, days)`).

## Checked and found consistent

- No migration, no new key, no write: the route reads through `read_ticket` (`tickets.py:241`, exported, used by `documents.py`), `load_node_for_user`, `_meters_of`, `_last_readings`; index `ix_meter_readings_meter_time` at `local_db.py:995`.
- Import direction: `tickets.py` imports `equipment`, `alerts`, `tickets_core`, never `meters`; `masters.py` imports only `meters_core`; `meters_bp` is registered under `/api` (`app.py:181`). No cycle.
- `_visible_condition` is `t.unit_id IN (…) OR m.unit_id IN (…)` (`tickets.py:190`); `ticket:read` and `equipment:read` are in `SITE_SCOPED`; every `ticket:read` holder has `equipment:read` (`*`), so the *Register* link to S050's register (`equipment:read`) never lands on a 403.
- The ticket's time cannot be edited: `edit_ticket` changes the component, the symptom and the description only (`tickets.py:1151`), so reloading on `ticket.component?.id` is enough; `occurred_at` is the ticket's own column.
- `formatReading`, `readingBadges` (`meterLabels.js:71`, `:79`), `formatDateTime` exist; `scrollWidth` phone-fit checks exist in `screens.spec.js`; the e2e set-up helpers exist (`meterMachine`, `logByApi` in `e2e/support/meters.js`; `raiseByApi`, `istLocal` in `e2e/support/tickets.js`).
- The 7-day window matches `READING_BACKDATE_DAYS = 7` (`meters_core.py:276`).
- Plan.MD: § 4.2 lists a reading as a ticket source and § 4.6 keeps MTBF for phase 5; nothing there contradicts "shown, not stored". Maintenance-Philosophy § 10 leaves "available operating time" TBD, which matches § 9 item 2.
- EN 13306's *condition monitoring* and *fault diagnosis* are paraphrased correctly; TPM pillar 1 is the right home for "the operators' readings are read".
- Track full, round 1; § 8.4 is all automated with the two important checks marked; § 8.5 none is right (nothing here needs a camera, a printer or a real login).
- `TicketDetailView.vue` lines 309 and 315 are the machine and part links; `tickets.py` is 1418 lines; the `PartsPanel` placement (`:406`) is where the brief puts the card before.
