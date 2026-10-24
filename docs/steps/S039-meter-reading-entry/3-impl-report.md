```
Step: S039 — Meter reading entry
Doc: impl-report
Author: Coder (Opus)
Date: 24-10-2026
```

# S039 — Meter reading entry: implementation report

Meter readings are built as briefed: migration v32, the pure rules, the three reading routes, `last` on the meters list, the *Log reading* and *History* dialogs on the *Meters* card, and the docs pass. All four suites pass, and so does the full browser suite (counts in § 6). Nothing changes the approved design, and there is no open question. Fourteen small choices the brief did not cover are listed under *Decisions taken*; two of them change an S038 test, because the card now has buttons for the operator and the meters list has a new field.

## 1. What was built

- **Migration v32.** The table `meter_readings`, exactly as § 4 gives it. No `_PRECONDITIONS` entry: a new table.
- **The rules (`meters_core.py`).** Every row of § 5.1, the counter order against both neighbours, a gauge's *High* / *Low*, a Yes / No meter's *Not OK*, the 7-day window, and who may remove a reading.
- **The API (`meters.py`).**
  - `POST /api/equipment/<id>/readings` (`reading:log` at the node's site) logs one reading and answers 201 with it.
  - `GET /api/equipment/<id>/readings?meter_type_id=…&page=…&per_page=…&include_removed=…` (`equipment:read` at the site) gives one meter's history, newest first, with `can_remove` per row.
  - `DELETE /api/equipment/<id>/readings/<reading_id>` (`equipment:edit` at the site) hides a reading and answers 204.
  - `GET /api/equipment/<id>/meters` (and S038's two meter writes, which answer with the same list) gains `last` per meter: `{value, taken_at, limit_state}` or `null`.
  - The "Lower than …" refusal carries `code: "counter_lower"` (`ApiError` gains an optional `code`).
- **The key.** `reading:log` for the operator, so the supervisor and the maintenance ladder inherit it; not IT admin. It is in `SITE_SCOPED`.
- **The equipment page.** Per meter on the *Meters* card:
  - the last reading, "12,345.6 h · 23-10-2026 18:00", with a *High* / *Low* / *Not OK* badge, as a tap target with a chevron that opens *History*; "No readings yet" before any reading, not a tap target;
  - *Log reading* for `reading:log` holders (not on a scrapped node);
  - after a save outside what is good: "Saved. Above the limit of 60 °C.", "Saved. Below the limit of 10 °C." or "Saved. Not OK: the expected answer is Yes." on the meter's row.
- **Log reading dialog.**
  - Number meters: *Value* with the unit beside it and `inputmode="decimal"`; "Last reading: … on …" above it once there is one; for an amount the help "The amount for the period just ended, such as this shift."
  - *Time taken*: `EventFields.vue` ("Now · Change", no remark). "Now" sends no `taken_at`.
  - *Meter reset* on counters only, with the help "Tick this only when the meter was replaced or set back to zero".
  - *Note*, up to 200 characters.
  - A Yes / No meter: the question as the title, two large toggle buttons *Yes* and *No* (at least 48 px high, pressed state shown), then the normal *Save*, disabled with "Pick Yes or No" until an answer is picked.
  - With the database down (503) or no network: "Not saved. Try again in a minute." at the top of the dialog; the typed values stay.
- **History dialog.** The last 30 readings, newest first, and *Show more*: time, value, the badges *High* / *Low* / *Not OK* / *Reset*, the login that entered it, the note. *Remove* only where `can_remove` is true, asked first in the row ("Remove the reading of 23-10-2026 18:00 (12,345.6 h)? It no longer counts. You cannot undo this." with *Remove* / *Keep*). *Show removed* for `equipment:edit` holders. A load failure reads "Readings could not be loaded: <message>".

## 2. How it works

- **Pure core, `meters_core.py`.** No database, no clock, no Flask.
  - `parse_number` is S038's `_parse_limit`, made public. It serves the limits and the readings, with S038's messages.
  - `parse_reading_request(body, now)` reads what the POST names before its meter is known: `meter_type_id` ("Pick a meter") and `taken_at` (`parse_taken_at`).
  - `parse_taken_at(raw, now)`: absent is `now`; otherwise `tickets_core.parse_event_time`, cut to the minute, then `reading_time_error` (5 minutes ahead at most, 7 days back at most, exactly 7 days allowed).
  - `validate_reading(value, kind, decimals, reset, note)`: the kind decides. A Yes / No meter accepts only `"yes"` / `"no"` and returns `Decimal(1)` / `Decimal(0)`; every other kind goes through `parse_number`, then the below-zero rule of a counter and an amount. `is_reset` must be a bool, and only a counter may be reset. The note is trimmed (empty becomes NULL), 200 characters at most.
  - `counter_error(value, is_reset, before, after, meter_type)` returns `(field, message, code)` or None. Lower than the one before (not a reset) → `value`, `counter_lower`; a reset higher than the one before → `is_reset`; higher than the one after, unless that one is a reset → `value`. The messages show the neighbour's time and value as the screens do ("1,000.0 h", Indian grouping, the type's decimals: `grouped_number`, `reading_text`).
  - `limit_state(value, low, high)`, `answer_state(answer, expected)`, `may_remove(reading, can_edit)` (no author rule) and `reset_removal_error(reading, has_later)`.
- **Log a reading (the shell).**
  1. Validate the meter id and the time, before the transaction (`now` is the IST wall clock to the minute).
  2. (1) Lock the node through `load_node_for_user(…, "reading:log")`: 404 outside the user's units, 403 at another site, 409 when scrapped. This is the transaction's first statement.
  3. Plain reads: the node's meters in force (`_meters_of`, S038's `effective_meters`; 409 "This machine does not have this meter. Reload the page." when the type is not one of them), then `validate_reading` with the meter's kind.
  4. Plain reads: an active reading of this meter at the same minute (409), and for a counter the nearest active readings before and after (`counter_error`).
  5. `limit_state` from the limits in force (a gauge) or the expected answer (Yes / No); insert with `source` `manual`; answer with the row.
  - Two writers on one node wait on (1); the second's snapshot starts after the lock, so it sees the first one's row. No locking range read.
- **History.** One meter's active readings (or all, with `include_removed=1` from an `equipment:edit` holder; anyone else's ask is ignored), ordered `taken_at DESC, id DESC`, offset paging in the house shape. One query finds the meter's newest active reading: every other active reading has a later one, so it decides the reset rule for the whole page. `can_remove` is `may_remove` (with `equipment:edit` at the site, and not on a scrapped node) and no reset-with-later.
- **Remove.** (1) the node with `equipment:edit` at its site (so IT admin may remove) → the reading row `FOR UPDATE` (404 when it is not this node's) → 409 when already removed → 409 for a reset with a later active reading → `removed_at = NOW()`, `removed_by`.
- **`reading_out(row, kind)`** gives the API's shape: a Yes / No value back as `"yes"` / `"no"` (`answer_word`), any other value without trailing zeros, the times as `row_to_dict` gives them. With `validate_reading` it is the only place of the word ↔ number mapping.
- **Screens.**
  - `MetersCard.vue` keeps its own load. It opens `ReadingFormModal` and `ReadingHistoryModal` through template refs. After a save it stores the meter's message (`savedMessage`) and reloads the list, so `last` follows the server (a back-dated reading is not the last). After a removal in *History*, it reloads too.
  - `ReadingFormModal.vue` is a plain `FormModal` with `useFormModal().send`; a 503 or a failed fetch becomes "Not saved. Try again in a minute." with no field, so it shows at the top and the form stays.
  - `ReadingHistoryModal.vue` is a `FormModal` with `close-only`. *Show more* appends the next page and skips an id already shown.
  - `meterLabels.js` gains `formatReading` (`toLocaleString("en-IN")` with the type's decimals), `readingBadges`, `savedMessage` and the badge words.

## 3. Files touched

Backend:
- `backend/local_db.py`: migration v32.
- `backend/meters_core.py`: `parse_number` (renamed), `parse_meter_type_id` takes its message, and the reading rules and words.
- `backend/meters.py`: `_lock_node` takes the key; `_meters_out` adds `last`; `reading_out`; the three reading routes; the docstring's readings and *Locks* paragraphs.
- `backend/api_common.py`: `ApiError(…, code=None)`, sent as `code` when set.
- `backend/config_rbac.py`: `reading:log`, in `SITE_SCOPED`.
- `backend/equipment.py`: the LOCK ORDER docstring's `meters.py` bullet gains the reading write.

Backend tests:
- `backend/tests/test_meters_core.py`: the reading rules (70 new tests; 139 in the file).
- `backend/tests/test_readings_api.py` (new): 36 tests.
- `backend/tests/test_migration_v32.py` (new): 4 tests, from v31, a re-run.
- `backend/tests/test_rbac.py`: the role matrix gains `reading:log`; `test_reading_log_holders`.
- `backend/tests/conftest.py`: `meter_readings` first in `_TABLES`.
- `backend/tests/test_meters_api.py` (S038): the whole-dict list check gains `"last": None`.

Frontend:
- `frontend/src/views/equipment/ReadingFormModal.vue` (new), `frontend/src/views/equipment/ReadingHistoryModal.vue` (new).
- `frontend/src/views/equipment/MetersCard.vue`: the last reading, *Log reading*, the saved message, the two dialogs.
- `frontend/src/views/EquipmentDetailView.vue`: `canLogReading`, `canSeeRemovedReadings` passed to the card.
- `frontend/src/utils/meterLabels.js`: `formatReading`, `readingBadges`, `savedMessage`, `LIMIT_STATE_LABELS`, `RESET_LABEL`.
- `frontend/tests/meterLabels.test.js`: three tests. `frontend/tests/navigation.test.js`: `reading:log` in OPERATOR, ENGINEER and MANAGER.
- `frontend/e2e/support/meters.js` (new): S038's `meterMachine`, moved and exported, unchanged.
- `frontend/e2e/readings.spec.js` (new): seven tests. `frontend/e2e/equipment.spec.js`: imports `meterMachine`; one new S039 test; S038's operator test changed (*Decisions taken* 13).

Docs: see *Docs updated*; also this report and the brief's status.

## 4. Decisions taken

Fourteen small choices, all forced or local. None changes the approved design.

1. **`counter_error` takes a fifth argument, `meter_type`.** The brief names `counter_error(value, is_reset, before, after)`; its messages show the neighbour's value with the unit and the type's decimals ("12,345.6 h", "12,350.0 h"), so the function needs them.
2. **The server formats numbers in its messages with Indian grouping and the type's decimals** (`grouped_number`), as the screens do with `toLocaleString("en-IN")` (U4). The brief's examples ("12,345.6 h", "12,350.0 h") match both.
3. **`parse_reading_request` and `parse_taken_at` in the core.** The brief lists `reading_time_error(taken_at, now)`; the two small helpers read the body before the meter is known, so the route stays thin. `parse_meter_type_id` gained an optional message, so "Pick a meter" reuses it.
4. **A time with seconds keeps its minute** (`to_minute`), and "now" is the IST wall clock to the minute. § 4 says "to the minute"; the same-minute check needs it.
5. **"Note must be text"** for a note that is not a string: a new API text the screens never cause.
6. **`can_remove` is also false on a scrapped node.** A removal there is a 409 (BR3-09), so the screen does not offer it.
7. **History rows always carry `removed_at` and `removed_by`** (null on an active row), so the item shape is one shape. The POST answers with the same fields, without `can_remove`; S040's *Undo* needs only the id.
8. **`last` comes on every meters list**, also after S038's add and limits writes, through one helper `_meters_out`. The in-force check of the POST stays `_meters_of` (BS1-10) and reads no readings.
9. **The card reloads its list after a reading**, instead of computing `last` from the POST's answer: a back-dated reading is not the last one, and the rule then lives in the server only.
10. **"Removed" as a badge and "Removed <time> · <login>"** in *History* when *Show removed* is on: new screen words. The removed value is struck through.
11. **The *History* dialog is a `close-only` `FormModal`** (S043's prop), so `FormModal.vue` does not change. `expectDialogFits` needs a *Save* and a *Cancel*, which this dialog does not have; its tests check instead that *Close* is in the viewport.
12. **The e2e tests make a machine per test, not one per project in `beforeAll`.** Each test then starts from a known history (a counter test depends on the readings before it) and `-g` runs one test alone. The Yes / No meter type is still made once per project in `beforeAll`, as § 8 says. No seed node or model is touched.
13. **Two S038 tests changed.** `equipment.spec.js` "S038: an operator sees the Meters card without edit buttons" asserted no button at all on the card; the operator now has *Log reading*. It now asserts no *Add meter*, *Set limits* or *Remove*, and two *Log reading*. `test_meters_api.py::TestList::test_model_meters_own_meters_and_an_override` compares the whole meter dict, which now carries `"last": None`.
14. **The last-reading line names itself "History: …"** for screen readers (a visually hidden "History:" before the value), so the button says where it goes.

## 5. Not done, deferred or assumed

- **Out of scope, as briefed:** the end-of-day sheet, its read route and nav item (S040); tickets and PM from readings (phase 4); charts (phase 5).
- **The dev database was migrated.** An import check of `app` with `YANTRA_TESTING=1` used the example secrets, which name the dev database `vel_yantra_master`, and applied v31 and v32 to it. Both migrations are additive; the dev backend would apply them on its next start anyway.
- **The first core test run used the default run name** (`dev`), before I set `YANTRA_TEST_RUN=s039c1`; it only cleaned that run's own test database.
- **Assumed:** a reading may be logged on a meter whose type was set inactive in Masters, as long as the meter is in force on the node (S038's `effective_meters` does not look at the type's `active`). The brief does not say; S038's card also still shows such meters.
- **The standards clause numbers** stay "to verify" (U4 D12). No code or screen cites them.

## 6. Tests run

Final full run, `YANTRA_TEST_RUN=s039c1 tooling/run-tests.bat`:

| Suite | Result |
|---|---|
| backend | PASSED, 2948 passed, 109 s |
| frontend | PASSED, 157 passed, 28 s |
| deps | PASSED, 42 passed |
| tooling | PASSED, 115 passed, 12 s |

- `npx vite build` in `frontend/`: built in 4.40 s, the usual chunk-size warning only.
- **New e2e tests alone first** (`E2E_LANES=1`, `desktop-chromium`, `-g "S039"`): the first run had 2 failures, both mistakes in the new tests (a `toHaveText` that Vue's dropped space between two spans broke, so it now checks the accessible name; and the expected 400 needed `allowFailedRequest`). The second run: 8 passed.
- **Full e2e suite** (`tooling/run-e2e-tests.bat`, 6 lanes, three projects): **377 passed, 1 failed, 6 skipped** in 12.0 min. Every S039 test passed on all three projects. The one failure is `tickets-raise.spec.js:141` "S018 A1: Already fixed with a start time …" on phone-webkit: a timeout in `scrollIntoViewIfNeeded` ("waiting for element to be stable") on the raise screen, which this step does not touch. Run alone on phone-webkit it passed (1 passed). I take it as a WebKit flake under load, not a fault of this step; it is not the known flaky `masters.spec.js:62`. The full suite, because the step changes `e2e/support/` (the moved `meterMachine`) and the API's error shape (`ApiError` gains `code`), which every screen reads through `api.js`.

## Fix rounds

### Round 1

All eight findings of `4-code-review-r1.md` are answered. Final runs: `YANTRA_TEST_RUN=s039c2 tooling/run-tests.bat` PASSED (backend 2948, frontend 157, deps 42, tooling 115); `npx vite build` built in 4.16 s; e2e `readings.spec.js`, `equipment.spec.js` and `screens.spec.js`, 6 lanes, three projects: **111 passed** (5.5 min). The specs are the review's own set: the screens the round changes plus `screens`; `e2e/support/` gained only a helper that those two specs import.

- **CR1-01: Fixed.** Each test computes its time once (`const at = istLocal(30)`, `earlier`, `typed`), sends that string and expects `shownTime` of it. Red run: not possible, because the fault needs the clock to pass a minute between two calls; it cannot be forced without faking time. Green: the S039 tests pass.
- **CR1-02: Fixed.** One `logByApi(machine, name, value, takenAt, extra)` in `frontend/e2e/support/meters.js`, imported by `readings.spec.js` and `equipment.spec.js`. It takes the time string (CR1-01). The inline block in `equipment.spec.js` is gone.
- **CR1-03: Fixed.** *Log reading* is full size (no `btn-sm`) and the last-reading line has `py-2` and normal text; both carry `min-height: 44px` (class `touch-target`, scoped style). The engineer buttons stay small. `equipment.spec.js` "S039: the Meters card shows the last reading…" now asserts both are 44 px or more high. Fails without the fix: "a tap target of 44 px or more: Expected >= 44, Received 23" (the last-reading line); passes with it. Row 32 of `device-checks.md` now names the two controls.
- **CR1-04: Fixed.** `docs/schema.md`: "Readings are in `meter_readings` (S039, v32)".
- **CR1-05: Fixed.** `ReadingFormModal.vue` treats 502, 503 and 504 (and no status) as "Not saved. Try again in a minute." No new test: the component has no unit test and the e2e stack cannot make Nginx answer 502; the change is one list.
- **CR1-06: Fixed, with one reading of the instruction.** The POST answer carries no limits, and adding them would change the API shape, so I did not. Instead `MetersCard.readingSaved` now waits for the card's reload, then words the message from the reloaded meter's limits (falling back to the dialog's meter if it is gone). The gap shrinks from "since the card loaded" to "between the server's judgement and the reload". New test `readings.spec.js` "S039: the saved message names the limit in force at saving (CR1-06)": an engineer lowers the max from 60 to 50 while the dialog is open; the saved message must read 50. Fails without the fix: "Expected: Saved. Above the limit of 50 °C. Received: Saved. Above the limit of 60 °C."; passes with it. If you want the exact limit judged on the server, the POST answer must carry `min_value` and `max_value`: say so and I add it as an amendment.
- **CR1-07: Fixed.** `ReadingHistoryModal.vue` no longer sends `per_page`; the server's `HISTORY_PER_PAGE` is the only place of the page size. The header comment says "a page at a time".
- **CR1-08: Rejected as a code change, recorded.** The rule is as briefed and harmless today. A "Known gap" paragraph in the `counter_error` docstring (`meters_core.py`) names the two cases for the phase 5 usage sums. Deferred to phase 5 (usage totals across resets).

Files touched in this round: `frontend/e2e/support/meters.js`, `frontend/e2e/readings.spec.js`, `frontend/e2e/equipment.spec.js`, `frontend/src/views/equipment/MetersCard.vue`, `ReadingFormModal.vue`, `ReadingHistoryModal.vue`, `backend/meters_core.py` (comment only), `docs/schema.md`, `docs/steps/device-checks.md`, this report.

### Round 2

The one finding of `4-code-review-r2.md` is answered. Final run: `YANTRA_TEST_RUN=s039c3 tooling/run-tests.bat` PASSED (backend 2948, frontend 158, deps 42, tooling 115). The first full run had one backend failure, `test_alerts.py::TestSendOutcomes::test_a_redirect_is_never_followed` (a `ConnectionAbortedError` 10053 from the host's network, unrelated to this round); the second full run passed all of it. No e2e run: the change is a pure text helper with a unit test, and the review's e2e set passed in round 1.

- **CR2-01: Fixed.** `savedMessage` in `frontend/src/utils/meterLabels.js` returns "Saved. Above the limit." or "Saved. Below the limit." when the limit on that side is `null`, and names the value otherwise. New vitest case "does not name a limit the meter does not have (CR2-01)" in `frontend/tests/meterLabels.test.js`. Fails without the fix: "expected 'Saved. Above the limit of null °C.' to be 'Saved. Above the limit.'"; passes with it.

Files touched in this round: `frontend/src/utils/meterLabels.js`, `frontend/tests/meterLabels.test.js`, this report.

## Manual checks

- [auto] **Important.** An operator logs a reading from the equipment page; the dialog fits a phone — `frontend/e2e/readings.spec.js::S039: an operator logs a reading from the equipment page`
- [auto] **Important.** A counter lower than the last reading is refused beside the value; ticked as a reset, it is saved — `frontend/e2e/readings.spec.js::S039: a counter lower than the last reading is refused beside the value`
- [auto] A gauge above its limit is saved and shows High — `frontend/e2e/readings.spec.js::S039: a gauge above its limit is saved and shows High`
- [auto] An engineer removes a wrong reading and the operator enters it again — `frontend/e2e/readings.spec.js::S039: an engineer removes a wrong reading and the operator enters it again`
- [auto] The operator who logged a reading sees no Remove on it — `frontend/e2e/readings.spec.js::S039: the operator who logged a reading sees no Remove on it`
- [auto] A shift's production lower than the last one is saved — `frontend/e2e/readings.spec.js::S039: a shift's production lower than the last one is saved`
- [auto] **Important.** A No on a Yes / No meter, then Save, shows Not OK: both buttons at least 48 px high and inside the viewport on Pixel 7 and iPhone 14, *Save* disabled until an answer is picked, a note typed after the answer saved with it — `frontend/e2e/readings.spec.js::S039: a No on a Yes / No meter, then Save, shows Not OK`
- [auto] The *Meters* card shows the last reading, and its tap opens *History* — `frontend/e2e/equipment.spec.js::S039: the Meters card shows the last reading, and its tap opens History`

On a real device (row 32 of `docs/steps/device-checks.md`):

- [ ] **Important.** The decimal keypad on an Android phone and an iPhone in the *Log reading* dialog, the refusal under *Value* not hidden by the keyboard, and the *Yes* / *No* buttons easy to hit with a thumb. Account: a test login with the Operator role at SMTW; company Wi-Fi; production on the TEST machine, or the dev server.

## Docs updated

- `docs/schema.md`:
  - the header line (v32 by hand);
  - round 1 (CR1-04): the `meter_types` row now says readings are in `meter_readings` (S039, v32);
  - a built `meter_readings` row, in place of the planned one;
  - the Mermaid overview: the entity and its two links.
- `docs/schema.html`, by hand (there is no generator):
  - the meta line ("Migration v32 … 37 tables, 53 links");
  - the Overview tab: the entity with its keyed columns and the two links;
  - the Equipment tab: the table with every column, the two links, and its note names the readings.
- `docs/Plan.MD`:
  - § 3: a line under the matrix, `reading:log` as built (and why IT admin removes but does not log);
  - § 4.5: a "Built (S039, 24-10-2026)" bullet with the rules, routes and screens as built.
- `.claude/CLAUDE.md` § SMTW-Review:
  - the spec-to-step map gains `equipment` S039 and `readings` S039;
  - the § 9.6 point (U4): every counter reading path takes the node lock first and checks both neighbours.
- `docs/steps/device-checks.md`: row 32, the real-device check of § 8 (round 1: it names *Log reading* and the last-reading line as tap targets).
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`: none. The step adds no maintenance rule beyond Plan.MD § 4.5, no plant fact, no Keycloak role (`reading:log` is a Yantra key on existing roles) and no secret.
