```
Step: S040 — End-of-day readings sheet
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 24-10-2026
```

Reviewed against: ff9ddb3 + uncommitted S037, S038, S039, S043

# S040 — Staleness review, round s1

**Verdict: no blocker or major finding. The approved design holds; 2 minor findings and 8 nits update the brief's wording.**

The brief was written against the S037–S039 briefs. All three are now coded (S037 and S038 in `refs/steps/S038`, S043 in `refs/steps/S043`, S039 in the working tree). I read the brief against the code as it stands: `meters.py`, `meters_core.py`, `equipment.py`, `auth_utils.py`, `config_rbac.py`, `api_common.py`, `api.js`, `navigation.js`, the router, `App.vue`, `main.css`, `stores/equipment.js`, `stores/masters.js`, `TicketsView.vue`, `EventFields.vue`, `MetersCard.vue`, `ReadingFormModal.vue`, `meterLabels.js`, `ticketLabels.js`, `datetime.js`, `e2e/support/meters.js`, `readings.spec.js`, `screens.spec.js`, `navigation.test.js`, `test_equipment_api.py`, `test_readings_api.py`, `seed_e2e.py`, Plan.MD § 4.5 and § 6, `.claude/CLAUDE.md`, and the S037, S038, S039 and S043 impl reports (*Decisions taken*, *Fix rounds*). The facts file `scratch/brief-facts-S040.md` was given; its "no such file" for `utils/ticketLabels.js` is a path artefact (the file is `frontend/src/utils/ticketLabels.js`).

Every statement the orchestrator asked about holds, except the two below and the nits.

## Minor

### BS1-01 — minor — § 8 Automated (e2e): the set-up it inherits from S039 is not what S039 built

**What changed.** S039's impl report, *Decisions taken* 12 and S039 BR3-03, CR1-02:
- each S039 test makes **its own machine per test**, not one per project in `beforeAll`; only the Yes / No meter type is made once per project in `beforeAll`;
- `meterMachine(testInfo, tag, { unit, modelMeters, ownMeters })` makes a **press model of its own** for every machine (`e2e/support/meters.js:7–9`); the seed model `SMTW-HYP-01` is never used. Its default unit is `SMTW.MCC1`;
- readings are logged with `logByApi(machine, name, value, takenAt, extra)`, which posts **as the operator** (`e2e_operator`, unit MCC2 only).

**What in the brief is now wrong.** § 8: "Set-up as S039 (S039 § 8, BR2-04, BR3-03): an own machine per project at SMTW.MCC2 on the `SMTW-HYP-01` model … S040's `beforeAll` adds a second machine per project at SMTW.MCC1 … its own readings through S039's POST". Three points: per project vs per test; the model; and `logByApi` cannot log on the MCC1 machine (404 for the operator).

**Why it matters.** The sheet lists every machine at SMTW with meters in force. On the shared e2e database that is every machine every S038, S039 and S040 test of all three projects has made in that lane. A per-project set-up would also make the S040 tests depend on each other's readings (the Undo test removes a reading; the *Today* test counts one), which is what S039 D12 moved away from.

**Options.**
- (a) **Recommended.** Follow S039 as coded: each S040 test makes its own machine(s) with `meterMachine` (`unit: "SMTW.MCC2"` for the operator's cases, a second one at `SMTW.MCC1` for the supervisor's two-units case) and its own readings with `logByApi` on the MCC2 machine; the Yes / No type per project in `beforeAll`, as `readings.spec.js:20–31`. Every assertion is scoped to the test's own card (found by the machine's name, `S038 press <tag> <project>`); the header counts ("9 of 48 read today", "3 of 48 filled") are asserted as a pattern or a difference, never as literal numbers, since other tests' machines are on the same sheet.
- (b) Keep a per-project `beforeAll` for the MCC1 machine only (it needs no readings), the rest as (a).

Fix the text of § 8 either way, and drop "on the `SMTW-HYP-01` model".

### BS1-02 — minor — § 1.7 and § 5.3: the failure set is 502, 503, 504 or no status, not "503 or a failed fetch"

**What changed.** S039 CR1-05: `ReadingFormModal.vue` treats a 502, 503 or 504, and a request with no status (no network), as "Not saved. Try again in a minute." (`UNAVAILABLE = [502, 503, 504]`, `notSavedOr`).

**What in the brief is now wrong.** § 1.7 "a row's save fails with a 503 or a failed fetch: the loop **stops**", § 5.3 "The page shows the load message on a 503 or a failed fetch", and the BR1-11 line of the Review log.

**Why it matters.** A 502 or 504 comes from Nginx while the backend restarts or hangs. With the brief's rule the sheet would show it as a per-row refusal and go on posting the next 30 rows into a server that is down. The sheet's rule and the dialog's must be one rule.

**Options.**
- (a) **Recommended.** Write "a 502, 503 or 504, or no answer at all (no network)" in § 1.7 and § 5.3; the coder lifts `notSavedOr` (or its list) out of `ReadingFormModal.vue` into `meterLabels.js` or `api.js`, so both screens share it rather than copy the list.
- (b) Keep the words and let the coder read S039's dialog. Rejected: the brief then states a rule that differs from the code it says it follows.

## Nits

- **BS1-03** (nit) § 3 Tests, `test_equipment_api.py`: three `my-units` assertions compare the whole dict and break when `reading_unit_ids` is added (`:958` two units, `:970–971` token roles, `:993–994` no rows). Name them, so the coder extends them with `reading_unit_ids` rather than only adding the new per-role test.
- **BS1-04** (nit) line numbers moved; cite names: `equipment.py:565` → `my_units` at 589; `:286` → the "only these helpers … touch accessible_unit_ids" comment at 310–311; `:290` → `accessible_unit_ids` at 314; `:258` (the subtree read) → `_children` at 278; `masters.py:78` → `_UNIT_SELECT` at 90 (`u.*` carries `site_id`, plus `full_code`). `main.css:80` still falls in the bottom-nav block (74–86). `TicketsView.vue:61`, `:144`, `:171` and `seed_e2e.py:39`, `:43` hold.
- **BS1-05** (nit) header `Baseline:` names S037 (v29), S038 (v30) and S039 (v32) but not **S043 (v31)**, which is in the tree (`refs/steps/S043`: the Properties card on the equipment page, `closeOnly` on `FormModal`). The sheet touches neither; add it so the baseline line is complete and v31 is accounted for.
- **BS1-06** (nit) § 3 `meterLabels.js` and § 6: S039 built `formatReading`, `readingBadges`, `savedMessage` and `LIMIT_STATE_LABELS`. The sheet's "Saved. Not OK: the expected answer is Yes." is `savedMessage(meter, reading)`, which also words a gauge's "Saved. Above the limit of 60 °C." and reads `meter.min_value` / `meter.max_value`. Say that a gauge row saved outside its limits reads as the card does, and give each sheet meter `_meters_out`'s dict (`effective_meters`' fields plus `last`), not only `{meter_type, last}`, so the helper is reused as it is.
- **BS1-07** (nit) § 1.4 *Read today*: "the IST helpers of `utils/ticketLabels.js`" — that file has none for a day test (`toLocalInputValue` and `daysAgoHint` use the phone's clock; `datetime.js`'s `formatDateTime` only reformats the API string). Say what the coder builds: a small tested `isToday(takenAt, now)` in `meterLabels.js` that compares the API's IST date (`taken_at.slice(0, 10)`, sent as `+05:30`) with the phone's date, as the rest of the frontend treats the phone as IST.
- **BS1-08** (nit) § 3 Docs: the docs pass also updates `.claude/CLAUDE.md` § SMTW-Review's spec-to-step map (`readings` S039 → S039/S040), as S038, S039 and S043 each did. Add it to the list.
- **BS1-09** (nit) § 3 and § 8 vitest: `navigation.test.js` has no technician list (`SUPERVISOR = OPERATOR`; the lists are OPERATOR, STOREKEEPER, ENGINEER, MANAGER, IT_ADMIN). The five `visible(...)` lines cover operator (= supervisor), engineer, manager, IT admin and the storekeeper. Drop "technician" from § 8, or add a TECHNICIAN list.
- **BS1-10** (nit) § 8 Backend (pytest) names the e2e seed's MCC1 / MCC2 and "the storekeeper"; the backend tests build their own sites and units (`user_at_sites`, `make_site`, `make_unit`, `role_client`, as `test_equipment_api.py:973–994` and the `test_readings_api.py` fixtures). Word the cases as "a supervisor at two units of one site; an operator at one of them; a storekeeper role (no `reading:log`)".

## Checked and found consistent

- **S039's routes and shapes.** `POST /api/equipment/<id>/readings` (`reading:log`, 201, the reading row with its `id`); `DELETE …/readings/<reading_id>` (`equipment:edit`, 204; 404; 409 "This reading was removed"; 409 "This reading marks a meter reset. Remove the later readings first."; 409 scrapped). The "Lower than the reading of … Check the value, or tick Meter reset if the meter was reset." refusal carries `code: "counter_lower"` (`meters_core.COUNTER_LOWER`, `ApiError(…, code)`), and `api.js:25` puts it on `err.code`. `last` is `{value, taken_at, limit_state}` or `null` on every meters list (`_meters_out`). `can_remove` is on history rows only; the POST answer has no `can_remove` (S039 D7), and the sheet's Undo needs only the id. History paging (`HISTORY_PER_PAGE = 30`, offset) is untouched by the sheet.
- **Time taken.** `parse_taken_at`: absent → the server's minute; `FUTURE_SKEW` 5 minutes; `READING_BACKDATE_DAYS` 7. `EventFields.vue` takes `withRemark`, `timeLabel`, `timeError`, `idPrefix`, `v-model:time`; "Now · Change" as the brief says.
- **`parse_number` and the words.** S038's parser is public as `parse_number`; "Enter a whole number" / "Enter a number with up to N decimal(s)" / "Enter a smaller number" / "Enter the reading" / "A counter cannot be below zero". The brief quotes none, so nothing to update. `inputmode="decimal"`, the amount help sentence and the reset help sentence are as the dialog shows them.
- **Yes / No.** The dialog's two `btn-lg` toggles with `aria-pressed` and `min-height: 48px` (`.answer-button`) pick, then *Save* saves (S039 decision 11); `savedMessage` gives "Saved. Not OK: the expected answer is Yes.". Decision 9 and § 1.4 hold.
- **`e2e/support/meters.js`.** `meterMachine` and `logByApi` exist with the signatures above; `readings.spec.js` imports both (BS1-01 covers the set-up wording).
- **`my-units`.** `{all_units, unit_ids, edit_unit_ids}`; `accessible_unit_ids(cur, key)` → `user_unit_ids(key)`; `_unit_pools` (`auth_utils.py:336`) reads active units only, so the no-unit case of § 1.8 can occur. `reading_unit_ids` does not exist yet, as planned. `reading:log` is `("maint_operator",)` and in `SITE_SCOPED`; IT admin does not hold it.
- **The nav.** `navItems` is me, equipment, tickets, masters, settings; *Me* first (S035); `landingNavItem` is the first visible item, so a *Readings* item after `tickets` changes no landing page. `AppBottomNav` renders every visible item without a cap: six for the manager. The router guard uses `canOpenRoute(to.name)`, so the route's `name` must be `readings`, the nav item's name. Font Awesome 7.3.1 has `fa-gauge`.
- **`navigation.test.js`.** `reading:log` is in OPERATOR (= SUPERVISOR), ENGINEER and MANAGER, not IT_ADMIN or STOREKEEPER; five `visible(...)` expectations, as § 3 says.
- **The sticky bar.** `main.app-content` is the scrolling element (`App.vue`: `.app-shell` 100vh with `overflow: hidden`, `.app-content` `overflow-y: auto`); on a phone `.app-main` has `padding-bottom: 56px` (`main.css:76–79`) under the fixed 56 px `.app-bottom-nav` (z-index 1040), so a `position: sticky; bottom: 0` bar inside main sits above the nav, as § 1.6 says.
- **The pickers' sources.** `ensureUnits()` rows carry `site_id`, `active` and `full_code` (`_UNIT_SELECT`); `ensureSites()` rows carry `code`, `name`, `active`; `TicketsView.vue:61` (`unitChoices`), `:144` (the site select shows `s.code`), `:171` (the `noUnits` text) hold. `filterableUnits` / `pickableUnits` are in `stores/equipment.js`; `localStorage` is unused in `frontend/src`.
- **The seeds.** `e2e_operator` MCC2; `e2e_supervisor` MCC1 and MCC2 (`seed_e2e.py:39`); `e2e_manager` SMTW and BRICKS (`:43–44`); no seed model or machine has meters (the meter types come from v29), so the sheet's empty state is what `screens.spec.js` sees until a test adds a machine.
- **The docs pass.** Plan.MD § 4.5 already holds the S040 gate A line (`:724`) and S039's *Built* bullet; § 6 names *Me* first (S035). `device-checks.md` ends at row 32 (S039). `.claude/CLAUDE.md` § Docs to keep current exists as the brief cites it (BS1-08 adds one row).
- **S043.** Its changes (Properties card, `closeOnly`, `properties.py`, the LOCK ORDER bullet) touch nothing the sheet reads or writes.
