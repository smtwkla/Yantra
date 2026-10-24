```
Step: S039 — Meter reading entry
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: ff9ddb3 + uncommitted S037, S038, S043

# S039 — staleness review s1

**Verdict: no blocker or major finding is open.** The design and every decision the user approved still hold. Four `minor` findings: the number parser S038 built (the brief plans a near-copy with other words), the load-failure wording S038 built (the brief claims a text that was not built), an e2e helper S038 built that does the brief's set-up already, and the Meters card's place on the page now that Properties sits above it (a judgement call). Six nits are moved line numbers and doc details.

**Scope.** The brief's `Baseline:` is e451c33 plus S035, S036, S041 and S042; it was written against the S037 and S038 **briefs**. Since then S037 (v29) and S038 (v30) were coded (snapshot `refs/steps/S038`, 95b400d), and S043 (v31) was ported. I read the brief, the facts file `scratch/brief-facts-S039.md`, both impl reports' *Decisions taken*, and the working tree: `meters.py`, `meters_core.py`, `meterLabels.js`, `MetersCard.vue`, `EquipmentDetailView.vue`, `equipment.py` (LOCK ORDER, `SCRAPPED_MESSAGE`, `load_node_for_user`, `write_events`, `my_units`), `conftest.py`, `local_db.py` (v29–v31), `config_rbac.py`, `api_common.py`, `tickets_core.py`, `EventFields.vue`, the e2e helpers and seeds, `test_rbac.py`, `navigation.test.js`, `schema.md` and `schema.html`. The one question: does each statement of the brief about that code still hold?

## Findings

### BS1-01 — minor — § 5.1: the number rows duplicate S038's parser, with other words

**What changed.** S038 built the number parsing the brief describes, in `meters_core.py`: `_parse_limit(raw, decimals)` (lines 51–68) refuses a bool and a float, parses with `Decimal(text)`, counts decimals without trailing zeros, and refuses beyond `LIMIT_MAX` (`99999999999.999`) with `TOO_LARGE` = "Enter a smaller number". Its messages come from `_decimals_message(decimals)`: "Enter a whole number" for 0, else "Enter a number with up to 1 decimal" / "… up to 2 decimals" (S038 impl report, decision 2). A string that is not a number gets the same decimals message.

**What in the brief is now wrong.** § 5.1 gives a second parser with other words for the same rule: "Enter a number" for a non-number, "Use up to 1 decimal" / "Use up to 2 decimals" / "Use up to 3 decimals" for too many decimals. "Enter a whole number" and "Enter a smaller number" match. The brief's `validate_reading` would be a near-copy of `_parse_limit` (DRY), and the app would say "Use up to 1 decimal" in the reading dialog and "Enter a number with up to 1 decimal" in the limits dialog for one rule (scope B: one word for one thing).

**Why it matters.** The coder would write the copy as briefed. A later change to the number rule would then have two places.

**Options.**
- (a) **Recommended.** `validate_reading` calls the S038 parser. Make `_parse_limit` public as `parse_number(raw, decimals)` (one rename; `validate_limits` uses it too). § 5.1 takes the built words: "Enter a number with up to 1 decimal" / "… 2 decimals" / "… 3 decimals"; a non-number string gets the same message. Rows "Enter a whole number", "Enter a smaller number", "Enter the reading" (missing, empty) stay. The core tests in § 8 follow.
- (b) Reuse the parser but pass the brief's messages in. Two wordings for one rule stay in the app.

### BS1-02 — minor — § 5.5: the load-failure text the brief attributes to S038 was not built

**What changed.** The brief says the card's load failure reads "Meters could not be loaded. Try again in a minute." and calls it "S038, the equipment page's pattern, `EquipmentDetailView.vue:197`". As built, `MetersCard.vue:83` reads `Meters could not be loaded: {{ loadError }}`, which is the page's pattern: `EquipmentDetailView.vue:218` reads `Tickets could not be loaded: {{ ticketsError }}`. Line 197 is now the *Raise ticket* button.

**What in the brief is now wrong.** § 5.5's two load texts ("Meters could not be loaded. Try again in a minute.", "Readings could not be loaded. Try again in a minute."). The first describes a change to S038's card that the brief does not list in § 3; the second would be a third form of one message on one page.

**Options.**
- (a) **Recommended.** Follow the built pattern: the *History* dialog reads "Readings could not be loaded: <message>" (the API's error text, or `HTTP …` from `api.js:22` when the network is gone), and the card keeps its text. § 5.5 is reworded; `MetersCard.vue` is not changed for this.
- (b) Change the card to the brief's text in this step. That edits an S038 screen at gate B, and leaves *Open tickets* on the same page in the other form.

The dialog's own save failure, "Not saved. Try again in a minute." (BR1-05), is unchanged by this: no built code says otherwise.

### BS1-03 — minor — § 8 set-up: S038 built a helper that does what the brief plans

**What changed.** `equipment.spec.js:257` now has `meterMachine(testInfo, tag, { unit = "SMTW.MCC1", modelMeters = [], ownMeters = [] })` (S038): as admin it makes a model of its own (Generic, class `HP`, a unique designation), a machine of it at `unit`, adds the model's meters and the machine's own meters by meter type **name** (`typeId(name)` from `GET /api/masters/meter-types`), and returns the machine. `createEquipment(name)` (line 239) is unchanged: MCC1, GA37, as the brief says.

**What in the brief is now wrong.** § 3 and § 8 plan to move `createEquipment` to `e2e/support/` with a `unit` and a `model` argument, create the machine on `SMTW-HYP-01`, and then add four meters "through S038's API". `meterMachine` does all of that in one call, and because it makes its own model, no test needs the seed's `SMTW-HYP-01` at all (BR3-03's reason falls away). The brief's plan is a parallel helper (a second machine-maker with meters).

**Options.**
- (a) **Recommended.** Move `meterMachine` to `e2e/support/meters.js` and export it (one move; `equipment.spec.js` imports it). `readings.spec.js`'s `beforeAll` calls it with `unit: "SMTW.MCC2"` and `ownMeters: [["Run hours", {}], ["Oil temperature", { max_value: "60" }], ["Shift production", {}], [<the Yes / No type the test made>, {}]]`, after creating the Yes / No type by S037's API. `createEquipment` stays where it is, unchanged. § 3 (Tests) and § 8 (Set-up) are reworded; the `SMTW-HYP-01` sentence goes, or stays as a courtesy (the comments at `equipment.spec.js:255` and `masters.spec.js:271` keep it free either way).
- (b) Keep the brief's plan. Two helpers then make machines with meters.

### BS1-04 — minor — § 1.3: where the Meters card sits now that Properties is above it (judgement call)

**What changed.** The brief states no place for the card. S038 put it after the Details / Parts row and before Notes (`EquipmentDetailView.vue:296`). S043 added a *Properties* card in that row beside Details (line 268; shown when the class has properties). On a phone the page now reads, top to bottom: header, *Open tickets*, *Raise ticket*, the edit buttons (editors only), Details (about ten rows), Properties, Parts, **Meters**, Notes, History, Documents.

**Why it matters.** The brief's main job for this screen is "an operator logs the day's run hours and oil temperature of a press from its page" (Acceptance), often from a QR scan. *Log reading* is now about two phone screens down. Nothing the brief states is wrong, and the daily path for the press supervisors and the genset round is the S040 sheet. The user should decide knowingly.

**Options.**
- (a) **Recommended.** Keep the order; add one line to § 1.3 recording it ("the card stays after Details / Properties / Parts, as S038 placed it; the daily path is S040's sheet"). No code.
- (b) In this step, show the Meters card above the Details row for holders of `reading:log` (one `v-if` and a moved tag in `EquipmentDetailView.vue`). Operators reach *Log reading* first; engineers keep S038's order.
- (c) Defer the question to S040's review, where the daily path is designed.

## Nits

- **BS1-05** (nit) line numbers moved: § 5.3 `equipment.py:317` → `load_node_for_user` is at 321 (its `require_perm_at` at 336); § 5.3 `equipment.py:447` → `_check_no_open_tickets`'s snapshot rule is at 460–466; § 1.3 `EquipmentDetailView.vue:239` → the "Created" row with `node.created_by` is at 262; § 8 `equipment.spec.js:238` → 239; § 5.5 `api.js:20` → the `HTTP …` fallback is at 22–23. Cite the names, not the lines.
- **BS1-06** (nit) § 3 and § 5.3: the LOCK ORDER docstring now has a `meters.py` bullet (`equipment.py:52–59`) and a `properties.py` bullet (60–62); the reading line belongs in the `meters.py` bullet, not as a new one. `meters.py`'s own docstring has a "Locks" paragraph (lines 15–19) that needs the same line. And `meters.py._lock_node` hard-codes `key="equipment:edit"`: give it a `key` parameter for the reading write (`reading:log`) and the remove (`equipment:edit`), rather than a second helper.
- **BS1-07** (nit) § 3 Tests: `navigation.test.js:11` has `const SUPERVISOR = OPERATOR;`, so adding `reading:log` to `OPERATOR` covers the supervisor. "OPERATOR, SUPERVISOR, ENGINEER and MANAGER" reads as four edits; it is three.
- **BS1-08** (nit) § 8: `test_migration_v32.py` "from v30" → from **v31** (S043 sits between), in the pattern of `test_migration_v31.py` (`_migrate`, `_recreate` from `test_migration_v20`).
- **BS1-09** (nit) § 3 Docs: `docs/schema.md:83` still carries the **planned** `meter_readings` row ("result-row link when taken on a job or ticket step"); the docs pass replaces it with the built row (no result-row column in v32), as S038 removed the planned `meters` row. `docs/schema.html`'s meta line ("Migration v31 … 36 tables, 51 links") becomes v32, 37 tables, 53 links.
- **BS1-10** (nit) § 3 `meters.py`: the in-force check of § 5.2.1 is `meters.py._meters_of(cur, node_id, model_id)` (it calls `effective_meters` with the model's and the node's rows); name it, so the coder does not rebuild the list.

## Checked and found consistent

- **`meters_core.py` names** the brief relies on: `effective_meters` (line 203) with each row's `meter_type` = `{id, name, unit, kind, decimals, expected_answer}` (`meter_type_of`, line 252), so `answer_state(answer, expected)` has its input; `format_number` gives strings without trailing zeros; `LIMIT_MAX` and `TOO_LARGE` match § 5.1's "beyond ±99,999,999,999.999 → Enter a smaller number". None of the brief's new names (`validate_reading`, `reading_time_error`, `counter_error`, `limit_state`, `answer_state`, `may_remove`, `reset_removal_error`, `reading_out`, `READING_BACKDATE_DAYS`) exists yet (facts file): no collision. `meters_core` imports nothing from `tickets_core` today; the planned direction (pure to pure) is open. `tickets_core.py` still exports `FUTURE_SKEW` (52), `EVENT_TIME_FORMAT` (73), `EVENT_TIME_FUTURE` (74), `parse_event_time` (92); `backdate_days` (108) is not used, as decision 8 says.
- **`meters.py`** is the blueprint `meters_bp` under `/api`, registered in `app.py`; the reading routes fit beside the node-meter routes. It imports `SCRAPPED_MESSAGE, load_node_for_user, write_events` from `equipment.py`. `GET /api/equipment/<id>/meters` returns a bare list, so "gains `last` per meter" means one key per item.
- **`SCRAPPED_MESSAGE`** is defined in `equipment.py:123` ("since S038" holds); `documents.py` and `meters.py` import it.
- **`write_events`** (S038 decision 10 renamed `_write_events`): the brief does not cite either name, and plans no equipment event for a reading. Nothing to update.
- **`load_node_for_user(cur, node_id, for_update, key=None)`** (321): `for_update=True` with `key="reading:log"` is the lock § 5.3 describes; the 404 for a node outside the user's units and the 403 from `require_perm_at` at the node's site hold. `permissions_at_site` is in the node detail's `permissions`, which `EquipmentDetailView.vue` reads for `canEdit` / `canRaiseTicket` (63–72): `reading:log` fits the same way.
- **LOCK ORDER** (S038 and S043 changes): (4b) the meter type row exists; the meter type freeze counts `model_meters` then `node_meters` in share mode under (4b), never readings, so § 5.3's "no cycle" reasoning holds. `properties.py` locks a class (5) or a model (4), never equipment, so it adds nothing a reading write meets.
- **`config_rbac.py`**: `SITE_SCOPED` at 160, its comment at 158–159 ("every later ticket, PM, reading and report key joins this list"); `ticket:raise` is `("maint_operator", "it_admin")` (106), so `reading:log → ("maint_operator",)` without IT admin is the stated difference. `test_rbac.py`'s role matrix (176–181) and the site-scoped tests (98–126) take the new key as § 8 says.
- **`conftest.py`**: `_TABLES` (162) leads with `node_meters`, `model_meters`; `meter_readings` goes first, before them. `_SEEDED_TABLES` keeps `meter_types` by creator `migration-v29`, so test-made Yes / No types are cleaned; `make_meter_type` (456) exists for the API tests.
- **Migration v32 after v31**: `_MIGRATIONS` ends with (31, S043); `meter_types` (v29) has `kind ENUM('counter','gauge','amount','yes_no')`, `expected_answer`, `decimals` with CHECK 0–3, as § 4 and § 5 assume. No `_PRECONDITIONS` entry needed (a new table) holds.
- **`api_common.py`**: `ApiError(message, status, field=None)` (32) and `_error_response` (44) have no `code` yet; `int_arg` (135) with `DEFAULT_PER_PAGE`, `MAX_PER_PAGE`, `MAX_PAGE` (128–132) and the `{items, total, page, per_page}` shape (`tickets.py:606–609`) hold. `api.js:25` reads `err.code`; `access_control.py:152` sends `code: "network_denied"`.
- **`EventFields.vue`**: props `withRemark` (default true), `timeLabel` (default "When"); `time` stays null until *Change* is used, so "Now" sends no `taken_at` holds.
- **`MetersCard.vue`** as built: one `li` per meter (`data-testid="node-meter"`), name, `unitAndKind`, source badge, *Set limits* / *Remove* on the right, the `goodReadingText` line, the model help line, the inline [*Remove*] [*Keep*] confirm. The brief's last-reading line, chevron and *Log reading* fit in it. `meterLabels.js` has no `formatReading` yet (new), and `KIND_LABELS` / `SOURCE_LABELS` are the words to keep.
- **e2e**: `seed_e2e.py:38` is the operator with `MCC2`; `SMTW-HYP-01` is in `seed_dev.MODELS` and `create_masters` seeds it; no e2e seed equipment is on it, and `equipment.spec.js:255`, `masters.spec.js:271` and `support/properties.js` (own model, MCC1) keep off it. `apiAs("engineer")` and the `screens.spec.js` `beforeAll` pattern hold. `documents.py:431` answers 204; `test_ticket_work_api.py:805–822` is the two-connection pattern.
- **For S040 (not this brief):** `GET /api/equipment/my-units` is at `equipment.py:583` (S040's brief says 565) and returns `all_units`, `unit_ids`, `edit_unit_ids`; S040's planned `reading_unit_ids` still fits beside them. S039 does not cite the route.
