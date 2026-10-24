```
Step: S040 — End-of-day readings sheet
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035 (`navigation.js`, `router/index.js`, `App.vue`, `navigation.test.js`), S036 (`TicketRow.vue`, `main.css`, `ticketLabels.js`, `TicketDetailView.vue`, `EquipmentDetailView.vue`) and S041 (`equipment.spec.js`); plus the S037 (v29), S038 (v30) and S039 (v31) briefs as the assumed baseline (none approved or coded). Facts file: `scratch/brief-facts-S040.md` (its "not found" rows for `backend/meters.py`, `effective_meters`, `formatReading`, `test_readings_api.py` and `readings.spec.js` are expected: S038 and S039 create them; its `yantra.readings.unit_id` row matched `unit_id`, not the key).

**Verdict: no `blocker` or `major` finding is open.** The sheet's design holds: one POST per row through S039's rules, Undo through its remove route, `reading:log` site-scoped at the unit, the nav item after *Tickets* behind S035's *Me*. Seven `minor` findings: a planned parallel units route where `my-units` already does the job, the *Reset* tick rule that hangs on a message text, a wrong "cannot occur" on the no-unit case, the sticky *Save readings* button over the fixed bottom bar, a reading already taken today, out-of-use machines on the sheet, and parts' cards without their machine. Then nits.

## Findings

### BR1-01 — minor — § 5.1, § 6: `GET /api/readings/units` duplicates `my-units` plus the masters' units list

**Problem.** Every unit picker today combines two existing reads: `GET /api/masters/units` (every unit, `masters:read`, cached in `stores/masters.js` `ensureUnits`) and `GET /api/equipment/my-units` (`equipment.py:565`), which returns `unit_ids` for `equipment:read` and `edit_unit_ids` for `equipment:edit`, cached in `stores/equipment.js` with `filterableUnits` / `pickableUnits` and the `noUnits` flag. `TicketsView.vue:61` builds its unit filter that way. The brief plans a third source: a new route that returns the units with code and name, and a new picker on it.

**Why it matters.** Two lists of "my units" can drift (one shows an inactive unit, the other not), and the sheet misses `noUnits` and its message for free (BR1-03). A planned duplicate of an existing helper.

**Options.**
- (a) **Recommended.** `my-units` gains `reading_unit_ids` (null = every unit, else the ids where `reading:log` is held), beside `edit_unit_ids`, one more `accessible_unit_ids(cur, "reading:log")` call. The sheet's picker is `filterableUnits`-style over `ensureUnits()` and `reading_unit_ids`; a one-line helper `readingUnits(allUnits, mine)` in `stores/equipment.js`. The `/api/readings/units` route and § 9.3 go. `equipment.py:286`'s comment ("only these helpers, the list, /my-units … touch accessible_unit_ids") stays true for it.
- (b) Keep the new route, and say why the existing pair does not serve (I found no reason: the user's units at a `reading:log` site are the same rows `my-units` reads).

### BR1-02 — minor — § 1.5: "shows only after that row was refused with 'Lower than the reading of …'" needs a machine-readable refusal, not a text match

**Problem.** S039's POST returns `{error, field}` (its § 5.2.4 names the texts, no code). The only way to show the *Reset* tick on exactly that refusal is to match the message text in the frontend, which breaks on the first re-wording and puts a backend rule's identity in a string compare. `api.js:24` already carries `err.code` ("machine-readable refusal kind, when the API sends one"), used by `network_denied`.

**Why it matters.** The coder would decide the mechanism alone, and the cheap choice is the fragile one.

**Options.**
- (a) **Recommended.** S039's "Lower than the reading of …" refusal sends `code: "counter_lower"` (one line in S039 § 5.2.4 and its API table; S039 is still in review). § 1.5 here says: "the row's *Reset* tick shows when the refusal's `code` is `counter_lower`".
- (b) Show the tick on every `value` refusal of a counter row. Simpler, no S039 change, a tick after a decimals refusal too.

### BR1-03 — minor — § 1.8: a user with `reading:log` at no unit can occur, and the brief's fallback is wrong

**Problem.** The permission list is the union over the person's site roles (`compute_permissions`); the units come from `person_units` filtered to active units (`auth_utils._unit_pools`, "the user's own active unit rows"). An operator whose only unit was deactivated keeps `reading:log` and has an empty unit set. The app already handles this state: `noUnits` (`stores/equipment.js:18`) and "You have no units assigned — ask IT admin for unit access." on Equipment, Tickets and Me (`TicketsView.vue:171`, `MeView.vue:154`). The brief says the case "cannot occur" and that "a 403 from the read shows the access message". With the brief's routes it would be an empty picker or a 400 "Pick a unit".

**Options.**
- **Recommended.** With BR1-01 (a), the sheet shows the same `noUnits` message when `reading_unit_ids` is empty; no picker, no *Save readings*. One line in § 1.8; the vitest or e2e check is optional.

### BR1-04 — minor — § 1.6: *Save readings* "stays at the bottom of the screen" on a phone — above the bottom bar, and the last row must stay reachable

**Problem.** On a phone the bottom bar is `position: fixed; bottom: 0; height: 56px; z-index: 1040` (`main.css:80`), and `.app-main` has `padding-bottom: 56px`. A sticky *Save readings* at `bottom: 0` sits under the bar. Nothing in `frontend/src` is sticky today except the bar and the sidebar, so there is no pattern to copy. The brief does not say where the button sits, nor that the content needs room below the last row so the sticky bar does not cover the last press's oil temperature.

**Why it matters.** The one button the supervisor needs forty times a week, hidden behind *Masters* and *Settings*. Playwright would refuse the obscured click in "Save readings is disabled while saving", so the coder would find it late rather than never.

**Options.**
- (a) **Recommended.** § 1.6: on a phone a sticky bar at the bottom of `main.app-content` (`position: sticky; bottom: 0` inside the scrolling main, so it sits above the fixed nav), holding *Save readings* and the count ("3 of 12 rows filled"); the sheet ends with padding of the bar's height. On desktop the button is at the end of the sheet. The e2e test asserts the button's box is inside the viewport and above the bottom bar on Pixel 7 and iPhone 14.
- (b) No sticky button; *Save readings* at the end of the sheet only. Simpler, one long scroll after the last row.

### BR1-05 — minor — § 1.4: a meter read earlier today looks like yesterday's

**Problem.** The row shows "last reading … 23-10-2026 18:00" for every meter. At 18:30 the supervisor cannot tell at a glance which presses the operator already logged at 17:50 today (S039's per-equipment entry is live from the first day). She types them again; equal counter values pass (S039 § 5.2.4), a gauge saves twice, and the "same minute" refusal appears only if both chose the same minute.

**Why it matters.** The sheet's job is "which of my meters still need today's reading"; the brief's row answers "what was the last value".

**Options.**
- (a) **Recommended.** A row whose last reading was taken today reads "Today 17:50 · 12,345.6 h" and its input is left empty but marked done (a tick, the row greyed); typing is still allowed. The sheet's header counts "9 of 48 read today". The API shape already has `last.taken_at`; the day comparison is in IST on the frontend (`utils/ticketLabels.js` has the IST helpers). One e2e assertion.
- (b) Keep the brief: the date tells it. Cheaper, the supervisor reads 48 dates.

### BR1-06 — minor — § 1.4: out-of-use machines on the sheet, every day

**Problem.** § 1.4 lists every node with meters that is not scrapped. S030's lifecycles are `in_service`, `standby`, `out_of_use`, `scrapped` (`equipment_core.py:17`). A press out of use for months (Plant-Facts: at times only 70 % of the presses are operable) shows its four empty rows on every end-of-day sheet, with nothing to type. The brief does not decide it, so the coder would.

**Why it matters.** Rows nobody can fill are what sends a supervisor back to the notebook; and a judgement call the user should make.

**Options.**
- (a) **Recommended.** The sheet lists `in_service` and `standby` nodes only; an `out_of_use` node is listed with a *Show out of use* link at the end (collapsed), so a reading on it is still possible (a filter run on an idle press, a battery check). One line in § 1.4 and § 5.1; a test row with an out-of-use node.
- (b) List every non-scrapped node, as written.

### BR1-07 — minor — § 1.4, § 6: a part's card does not say which machine it belongs to

**Problem.** "Each node is a card" and the nodes are `[{id, code, name, level, meters}]`, in tree order. A component-unit with its own hour meter (S038 § 1.2: the alternating pump) gets a card after its machine's card, with its own code and name only: no `parent_id`, no `full_path`. On a 12-press unit, "P-07 pump" after "P-07" is readable; "Hydraulic pump" after a card that scrolled off is not. The desktop layout is not described at all.

**Options.**
- (a) **Recommended.** The API nests parts: `nodes: [{id, code, name, level, meters, parts: [{id, code, name, level, meters}]}]` (two levels at most, as the subtree read, `equipment.py:258`), and the card shows the machine with its meters, then each part as a titled block inside the same card ("Hydraulic pump"). One layout, cards, on desktop too (the sheet is a phone screen first; a desktop table would be a second layout for one user, the manager).
- (b) Flat list with `parent_id`, the frontend indents parts.

## Nits

- **BR1-08** (nit) § 3 Backend: "One query for the unit's nodes and their meters in force and the last reading of each" over-promises: `effective_meters` takes model rows, node rows and types; the last reading per (node, meter type) is its own read. Say "a few queries for the whole unit, none per node".
- **BR1-09** (nit) § 1.3: name the control for *Time taken*: `views/tickets/EventFields.vue` ("Now · Change", `withRemark: false`, `timeLabel: "Time taken"`), as S039's dialog should too. Its "Now" sends no `taken_at` (S039 § 5.1: absent → now on the server), so a phone a few minutes off is never refused. Say also that switching the unit keeps the time.
- **BR1-10** (nit) § 1.6: while the save loop runs, Undo on the saved rows is disabled too, and the inputs of rows not yet posted stay editable (the value posted is the value at that row's turn). One line.
- **BR1-11** (nit) § 1.7: on a 503 or a failed fetch the loop stops: that row and every row after it read "Not saved. Try again in a minute." without 39 more failing calls. A 400 / 409 on a row does not stop the loop.
- **BR1-12** (nit) § 8 `screens.spec.js`: each lane has its own database, so `/readings` in `screens.spec.js` has no meters (they are added in `readings.spec.js`'s `beforeAll`). Pick a `shows` locator that holds in the empty state: the unit heading for the operator (MCC2), the unit picker for the supervisor (MCC1, MCC2). And say that the empty state hides *Time taken* and *Save readings*.
- **BR1-13** (nit) § 8 e2e: the seeds give both cases of § 1.2 for free (`e2e_operator` one unit, `e2e_supervisor` two): add "the operator sees no picker; the supervisor picks MCC1, reloads, and MCC1 is still chosen" (the `localStorage` key).
- **BR1-14** (nit) § 1.2: a remembered unit no longer offered (access changed, unit deactivated) falls back to the first unit. One line.
- **BR1-15** (nit) § 3 Tests: `navigation.test.js`'s role lists mirror `test_rbac.py` (its comment, line 4), so S039 adds `reading:log` to OPERATOR, SUPERVISOR, ENGINEER and MANAGER there; S040 changes the five `visible(...)` expectations. Say which step adds the key to the lists, so S039's coder does not leave it to S040 or the other way round.
- **BR1-16** (nit) § 2: add ISO 9001 § 7.5.3 for Undo (it removes a record and keeps it, S039 decision 5: the sheet never edits a value in place), and ISO 14224 operating time (run hours per day are the denominator of phase 5's failure rates), both as S039 § 2 words them. In plain terms: the sheet is TPM's daily check sheet, with the record protected as § 7.5.3 asks.
- **BR1-17** (nit) § 5.1: for admin `accessible_unit_ids` is `None`, so an inactive unit's sheet opens for admin alone (`user_unit_ids` keeps active units for everyone else). Either refuse an inactive unit (404, as outside the units) or accept the oddity in one line.
- **BR1-18** (nit) § 1.4: the meters of a node come in meter type name order (S038 § 5.2), so a press reads Energy, Oil temperature, Run hours, Strokes. Fine, but say it, so the order on the sheet and on the equipment card is the same.

## Checked and found consistent

- **The key and its scope.** `reading:log` is S039's: `("maint_operator",)`, so the supervisor and the ladder inherit it (`ROLE_INCLUDES`), not IT admin or the storekeeper; in `SITE_SCOPED` (`config_rbac.py:160`, whose comment asks for it). Plan.MD § 3's matrix agrees. `accessible_unit_ids(cur, "reading:log")` (`equipment.py:290` → `auth_utils.user_unit_ids`, which asserts the key is site-scoped) gives `None` for admin and a set otherwise; a unit outside → 404 matches `load_node_for_user`'s rule. `require_perm("reading:log")` on the union refuses the storekeeper and IT admin with 403, and the nav item hides first.
- **The nav.** S035's working tree has `me` first (`navigation.js:9`); `canOpenRoute` follows the item's `perm`, so a typed `/readings` by IT admin goes to the landing page (`router/index.js:112`, `App.vue:25`). The bottom bar renders every visible item with `flex: 1` at 0.65rem (`main.css:92`): six for the manager, five for IT admin (no *Readings*), four for the operator. `expectNoSidewaysScroll` (`e2e/support/dialogs.js:49`) is the right check and exists.
- **Row by row through S039.** One POST per row, one node lock each (S039 § 5.3), so a sheet never holds two; `DELETE /api/equipment/<id>/readings/<reading_id>` for Undo; the author is within 24 hours; a removed reading may share its minute with its replacement (S039 § 4), so Undo → save again at the same *Time taken* passes; S039's 409 on a reset with a later reading is shown on the row.
- **The DB-down rule.** A 503 (`DBUnavailable`) and a failed fetch (`api.js:20`) both end as a thrown error with `status`; the load text and the per-row text match S039 § 5.5's wording; `EquipmentDetailView.vue:197` is the load-failure pattern cited.
- **Scrapped.** A node is scrapped only after its parts are (`_check_parts_scrapped`, `equipment.py:427`), so "not scrapped" per node is enough.
- **The time field's rules.** S039 § 5.1: `FUTURE_SKEW` 5 minutes, 7 days back for everyone (U2, decision 8); the brief cites them right.
- **Decimal input.** `inputmode="decimal"` is the `PartsPanel.vue:295` pattern; S039 parses the string with `Decimal`, so no float rounding on the sheet.
- **`localStorage`.** First use in `frontend/src` (grep: none today); a named key in `try`/`catch` is the right size for it.
- **Track and checks.** Full track is right (two new GET routes, site scoping). The device check (keypad, keyboard over the message and the button) is one a browser cannot judge, with account, network and where; everything else is automated. The important e2e test asserts what the user sees (*Saved*, the message, the tick).
- **Standards named.** TPM autonomous maintenance (the operator's own daily check), ISO 50001 § 6.6 (2018: *planning for collection of energy data*; the daily kWh read at a fixed time is that plan in practice) and EN 13306 condition monitoring are apt; the two additions are BR1-16.
- **Scope A and B.** The brief's texts are short and plain; *Save readings*, *Undo*, *Try again* start with a verb; the empty state says what to do next.
