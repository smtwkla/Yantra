```
Step: S039 — Meter reading entry
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: e451c33 + uncommitted S035 (`navigation.js`, `router/index.js`, both named in § 3), plus the S037 (v29) and S038 (v30) briefs as the assumed baseline (neither approved nor coded). Facts file: `scratch/brief-facts-S039.md`.

**Verdict: three `major` findings are open** (the locking reads of § 5.3, the back-date window against S028, and the history paging). No blocker. The brief is otherwise sound: the key, the site scope, the table and the per-row sheet save hold up. On the size question (§ 9.1): I would split the sheet off (BR1-07).

## Findings

### BR1-01 — major — § 5.3: the locking neighbour reads add a deadlock the brief does not name, and the node lock already does their job

**Problem.** § 5.3 reads the neighbour readings and the same-minute row with `SELECT … FOR SHARE` on `ix_meter_readings_meter_time`. Three things are wrong with that:

1. **Syntax.** MariaDB (11.4 in `tooling/dev/docker-compose.dev.yml`) and this codebase use `LOCK IN SHARE MODE` (`masters.py:255`, `tickets.py:39`). `FOR SHARE` is MySQL 8 wording.
2. **A new deadlock.** A locking range read on `(equipment_id, meter_type_id, taken_at)` takes gap locks. The gap between node A's last entry and node B's first entry is one gap in the index. Two supervisors saving the newest reading of two adjacent (node, meter) keys each take a shared lock on that gap (the "after" scan finds no later row and runs to the end of its range), then each inserts into it. Both inserts wait for the other's gap lock → InnoDB rolls one back (1213). The sheet makes this common: every row of a unit's presses is saved within seconds.
3. **Not needed.** Every reading write of a node takes (1) first, so two writers on one node serialise. `equipment.py:447` (`_check_no_open_tickets`) states the existing rule: the transaction's snapshot is taken by `load_node_for_user`'s plain read, after the node lock was granted, so a plain read sees every row committed before the grant. Plain reads give the second writer the first writer's row.

**Why it matters.** The brief's own goal ("two people saving the same counter at once serialise") is already met by (1); the locking reads buy nothing and add a failure the user would see as a random "could not save" on the sheet.

**Options.**
- (a) **Recommended.** Plain reads after (1). § 5.3 says: "the neighbour readings and the same-minute row are read plainly after (1); the node lock is the transaction's first statement, so the snapshot is taken after the lock (`equipment.py:447`)". The LOCK ORDER docstring gains the same line. The two-connection test of § 8 then proves it.
- (b) Keep locking reads as `LOCK IN SHARE MODE`, and name the accepted deadlock (adjacent keys) and a retry in § 5.3 and in the `equipment.py` docstring, as the ticket deadlocks are named.

### BR1-02 — major — § 5.1, § 7.8, § 9.4: "7 days back, the ticket rule" is not the ticket rule since S028

**Problem.** The ticket rule today is `backdate_days(now, has_perm("ticket:backdate"))` (`tickets_core.py:111`, `tickets.py:168`): 3 years back for admin always, **and for everyone until 30-11-2026** (`BACKLOG_UNTIL`), 7 days after that. § 9.4 describes the long window as "admin only", which is wrong until 30-11-2026.

**Why it matters.** S028's window exists for the notebook backlog. Plant-Facts line 120: the extrusion operators keep run hours and production counts in a notebook. Loading that notebook into Yantra is the same backlog case, and it is what the user will want first when meters go live. With the brief as written, tickets accept October's notebook and readings refuse it. The counter order rule (decision 2, both neighbours) is what makes back-dated loading safe, so the brief has already paid for it.

**Options.**
- (a) **Recommended.** Readings use `backdate_days` exactly as tickets do: 3 years for `ticket:backdate` holders (admin) and for everyone until `BACKLOG_UNTIL`, 7 days after. § 5.1's row becomes "more than the window back → 400, the ticket wording with 'When was it read?'". § 9.4 states the consequence: the window closes on 30-11-2026 for everyone. The key stays `ticket:backdate`; a nit in the key's comment says it now covers readings too. `too_old_message` asserts the limit is one of the two constants, so the reuse is one call.
- (b) 7 days flat, no backlog window. Then § 9.4 must say that the notebook cannot be loaded, and the user decides that knowingly.

### BR1-03 — major — § 6 / § 1.3: the history page cursor `before_id` with a newest-first order by `taken_at` skips and repeats readings

**Problem.** The history dialog orders by `taken_at` (newest first) and pages by `before_id`. A back-dated reading has a higher `id` than readings taken after it, so the second page (`before_id` = the last id shown) leaves out every back-dated reading older than the page boundary with a higher id, and the order of ids disagrees with the order shown. The sheet and decision 2 make back-dating normal.

**Why it matters.** After a month of daily readings (30 rows) *Show more* shows the wrong rows. The coder would build it as written.

**Options.**
- (a) **Recommended.** `limit` and `offset`, as the activity list does (`tickets.py:623`, S031). A meter has a few hundred readings a year; offset paging is enough and is the existing pattern.
- (b) A composite cursor `before_taken_at` + `before_id` on `ORDER BY taken_at DESC, id DESC`. Correct, more code, no second user.

### BR1-04 — minor — § 1.5, § 5.2.6, § 5.4: removing a reset reading, and who sees the *Remove* button

**Problem.** Two rules are missing.

1. **Removing a reset.** "The counter rules then ignore it" is a rule for the next insert, not for the readings already there. Remove the reset reading 50 (reset) between 12,000 and 60, and the chain reads 12,000 → 60 with no reset. A later back-dated reading between them cannot be saved: it is lower than 12,000 (refused) or higher than 60 (refused). Nothing warns.
2. **The control.** § 5.2.6 gives a 403 for "another operator". The agents' rule is "no permission: the control hidden, not a 403". The brief does not say the *Remove* button is shown only when the rule allows it.

**Why it matters.** 1: a corner case the coder would otherwise decide alone. 2: an operator reading history sees a button that fails.

**Options.**
- 1 (a) **Recommended.** A reset reading with an active later reading cannot be removed: 409 "This reading marks a meter reset. Remove the later readings first." Simple, keeps the chain whole. (b) Allow it and state in § 5.2.6 that existing readings are never re-checked.
- 2 **Recommended.** The GET returns `can_remove` per reading from `may_remove` (the pure rule, computed once in the shell); the dialog shows *Remove* only when true. The 403 stays as the backend's guard.

### BR1-05 — minor — § 5.5: the DB-down wording says the wrong thing, and the network case is not covered

**Problem.** A 503 from `DBUnavailable` means the server answered and its database did not. "Not saved. The server is not reachable." is false for that case. The case where the phone has no network (fetch throws, `api.js:20` gives `HTTP …` or `statusText`) is the one where "not reachable" is true, and the brief does not mention it. Also § 5.5 says nothing about the sheet's **load** failing (DB down when the page opens).

**Options.**
- **Recommended.** One wording for both failures, true for both: "Not saved. Try again in a minute." per row; the typed values stay. On load: "Readings could not be loaded. Try again in a minute." (the equipment page's pattern, `EquipmentDetailView.vue:197`). The brief states both cases: a 503 and a failed fetch.

### BR1-06 — minor — § 1.4: the sheet on a phone — a typo once saved, the *Reset* tick on every counter row, and the unit picker

**Problem.** Judged as the press supervisor at 18:30 with 10 presses × 4 meters on a Pixel:

1. **A saved typo.** A saved row turns read-only. The supervisor sees "1234" where she meant "12345" the moment it reads *Saved*. The brief's only way back is the equipment page → *History* → *Remove* → back to the sheet. Four screens for the commonest correction, on the screen built for speed.
2. **Reset on every counter row.** 30 counter rows each carry a *Reset* tick. A reset happens a few times a year; the tick is clutter, and a stray tap on it saves a wrong reset silently (a reset lower than before is accepted).
3. **The unit picker.** Most supervisors hold one unit. The brief asks them to pick it ("nothing asked that could be defaulted").
4. **Double tap.** "A second press saves only the rows not yet saved" — rows in flight must not be posted twice.

**Why it matters.** 1 and 2 are the friction that sends a supervisor back to the notebook.

**Options.**
- 1 **Recommended.** A saved row shows *Saved* and an *Undo* link that calls the remove route (the author is within 24 hours, so it always passes), then the row is editable again. Undo is the pattern the agents' rules ask for on a significant action, and it reuses the route.
- 2 **Recommended.** Hide the *Reset* tick until a row is refused with "Lower than the reading of …"; the refusal already tells the user to tick it. On the *Log reading* dialog the tick stays (one meter, room for it).
- 3 **Recommended.** One unit: no picker, the unit's name as the heading. Several: the picker, the last choice remembered.
- 4 The button is disabled while a save runs. One line in § 1.4.

### BR1-07 — minor — § 9.1: the size. I would split the sheet off

**Problem.** 22 files, a table, a key, the lock reasoning of § 5.3, two dialogs, a new page with its own save loop and phone layout, and the first nav item since S031. README § Step ID: "a step too big to review in one sitting is split". The per-equipment path and the sheet are two reviews: one on rules and locks (code review), one on a 40-input phone page (UX, e2e on two phones).

**Why it matters.** The code review runs up to 3 rounds on the whole diff. A finding on the sheet's layout holds up the rules, and the other way round. The sheet also gains from the floor's first week with the dialog (which labels, how the refusal reads).

**Options.**
- (a) **Recommended.** S039: the table, the key, the rules, the routes (the sheet read included, it is one query), the card, the two dialogs, remove. S040: `ReadingsView.vue`, the nav item, the route, `readings.spec.js`'s sheet test, `navigation.test.js`. About 16 and 7 files. S040's brief is a page: it adds no rule.
- (b) Keep one step (U1 chose both). Then the code reviewer should be told to review the backend and the sheet in two sittings.

### BR1-08 — minor — § 2: the standards named for the audit trail are the wrong clauses, and one that applies is missing

**Problem.** § 2 cites **ISO 9001 § 7.1.5** for "who entered which value and when is kept". § 7.1.5 is *monitoring and measuring resources*: the instrument behind the reading must be fit and, where traceability matters, calibrated. It is the right clause for *meters* (the energy meter, the temperature probe), not for the record of who typed what. The record is **§ 7.5 documented information** (§ 7.5.3, control: a record is protected from loss and unintended change — the "remove, never edit" decision 5 is exactly that). The missing one: **ISO 27001 A.8.15 (logging)** for who removed a reading and when, as the ticket briefs cite it.

For the user, learning the standards: § 7.1.5 says "trust the instrument"; § 7.5.3 says "trust the record". S039 serves the second; the first is the queued Calibration item.

**Options.**
- **Recommended.** Replace § 7.1.5 with § 7.5.3 for the audit trail; add A.8.15 for removal; keep ISO 55001 § 7.5. One line that readings depend on § 7.1.5 (instruments) and point to the Calibration queue item.

### BR1-09 — minor — § 3, § 8: the e2e tests need meters on the seed nodes, and the brief does not say where they come from

**Problem.** `readings.spec.js` needs a counter and a gauge with a limit on a seed node. `tooling/e2e/seed_e2e.py` seeds none (S038 adds its meters through its own tests). The brief names neither `seed_e2e.py` nor an API set-up in `beforeAll` (`apiAs("engineer")`, the pattern of `screens.spec.js`).

**Options.**
- **Recommended.** `beforeAll` adds the two meters through S038's API, as `screens.spec.js` raises its ticket. No seed change; one line in § 8.
- Or `seed_e2e.py` joins § 3 Where.

## Nits

- **BR1-10** (nit) § 3 Backend: say the import direction: `meters_core` imports `parse_event_time`, `event_time_error`, `FUTURE_SKEW`, `backdate_days` from `tickets_core` (pure to pure); `tickets_core` never imports `meters_core`. The "When was it read?" wording is meters_core's own (`too_old_message` returns the ticket text).
- **BR1-11** (nit) § 5.1: "Use up to N decimals" reads "Use up to 1 decimals" for N = 1. Use "Use up to 1 decimal" / "Use up to 2 decimals", or "Enter at most 1 decimal place".
- **BR1-12** (nit) § 6: `PUT /api/readings/<id>/remove` departs from the soft-remove verb in use: documents remove with `DELETE …/<id>` (`documents.py:418`) and restore with `POST …/restore`. Use `DELETE /api/equipment/<id>/readings/<reading_id>`, which also keeps every reading route under its node.
- **BR1-13** (nit) § 5.2.6, § 8: IT admin holds `equipment:edit`, so it may remove any reading; the 403 text "or an engineer" and the test list ("remove by author, by engineer, by another operator") leave it out. Add "IT admin removes" to the tests; the text can stay.
- **BR1-14** (nit) § 1.4: 6 items in the bottom bar for the manager and IT admin (Me, Equipment, Tickets, Readings, Masters, Settings; `AppBottomNav.vue` shows every visible item). Add to `screens.spec.js` or `readings.spec.js`: the bottom bar shows all six without sideways scroll on Pixel 7.
- **BR1-15** (nit) § 8 Automated: "`navigation`: the storekeeper and IT admin have no *Readings* item" is a vitest case (`navigation.test.js`), not an e2e test. Move it under the frontend unit tests.
- **BR1-16** (nit) § 1.3: two full buttons per meter (*Log reading*, *History*) make eight on a four-meter card at phone width. Make the last-reading line the tap target for *History* (a chevron), and keep one button, *Log reading*.
- **BR1-17** (nit) § 1.4: "remembered in the browser" is the first `localStorage` use in `frontend/src`. Name the key (`yantra.readings.unit_id`).
- **BR1-18** (nit) § 8 Backend: add `counter_error` with a reset and no earlier reading (passes), and `may_remove` for an IT admin.
- **BR1-19** (nit) § 1.3: the dialog's help "Tick only if the meter was replaced or set back to zero" — scope B prefers "Tick this only when …"; fine as is, but keep one phrase for the same thing on the sheet (BR1-06 item 2).

## Checked and found consistent

- **`reading:log` and `SITE_SCOPED`.** Plan.MD § 3 matrix has `reading:log` ✓ for operator, supervisor, technician, engineer, manager and blank for it_admin; `ROLE_INCLUDES` gives the supervisor and the ladder the operator's keys; `SITE_SCOPED`'s comment (`config_rbac.py:159`) asks for the key; `test_rbac.py:66` checks every site-scoped key exists; the role matrix at `:176–193` and `navigation.test.js`'s lists must both grow, as § 3 says. The storekeeper reads readings through `equipment:read` and sees no *Readings* item: right.
- **The node row as the lock (decision 6).** `load_node_for_user(cur, id, for_update=True, key=…)` (`equipment.py:303`) locks (1), 404 outside the units, 403 without the key at the site; the scrapped check from the locked row is the documents pattern (S038 § 5.3). The FK shared locks on `equipment` and `meter_types` and the S038 type update's order give no cycle, as § 5.3 says. A `GET_LOCK` per meter was rightly rejected (server-wide names, `local_db.named_lock`).
- **Per-row sheet save (decision 1).** One transaction per row, never two node locks: holds. Rows of one node serialise on (1), which is fine.
- **Time to the minute, 5 minutes ahead.** `FUTURE_SKEW`, `_EVENT_TIME_RE`, `EVENT_TIME_FORMAT` (`tickets_core.py:55–75`) are as cited; `created_at DEFAULT CURRENT_TIMESTAMP` is IST (`local_db.py:869`, `SET time_zone = '+05:30'`), so the 24-hour `may_remove` window compares like with like.
- **Table v31.** Column names and widths match the house style (`created_by VARCHAR(100)`, `removed_at` / `removed_by` as `equipment_documents`); `DECIMAL(14,3)` matches S038; no `_PRECONDITIONS` entry for a new table is right; `source` values match Plan.MD § 4.5 and line 225 (`move`). `meter_readings` first in `_TABLES` for the FK order: right.
- **Decimals as strings, parsed with `Decimal`.** `db_helpers.py:105` leaves `Decimal` to jsonify (a string); `tickets_core` already parses quantities with `Decimal`.
- **Two-connection test.** `test_ticket_work_api.py:814` has the threading pattern the concurrent-insert test can copy.
- **Device check.** The decimal keypad and the keyboard over the row's message are things a browser cannot judge; account, network and where are given. The dialog-fits and sheet-fits checks are rightly automated (`expectDialogFits`, `e2e/support/dialogs.js`).
- **Pure core, thin shell.** `validate_reading`, `counter_error`, `limit_state`, `may_remove` in `meters_core`; the routes in `meters.py`; the frontend formats and shows. The `limit_state` stored at save (decision 4) is the right call: a later limit change must not re-judge evidence.
- **Standards otherwise.** EN 13306 condition monitoring, ISO 14224 operating time as the denominator, ISO 50001 § 6.6 (planning for collection of energy data: 2018 edition, right clause), TPM autonomous maintenance: all apt and correctly placed.
