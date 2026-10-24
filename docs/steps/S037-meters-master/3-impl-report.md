```
Step: S037 — Meters master
Doc: impl-report
Author: Coder (Sonnet)
Date: 24-10-2026
```

# S037 — Meters master: implementation report

The Meter types master is built as briefed: migration v29, three routes, the panel, and the docs pass. All suites pass, and so do the targeted browser tests. No departure from the brief and no open question.

## 1. What was built

- **Migration v29** creates `meter_types` (name, unit, kind, expected answer, decimals, active, audit columns) and eight seed rows with `created_by` `migration-v29`.
- **API** `GET / POST /api/masters/meter-types` and `PUT /api/masters/meter-types/<id>`. Read needs `masters:read`; write needs `equipment:edit`.
- **Validation** `validate_meter_type(data, creating, stored=None)` in `masters_core.py`, the pure core with the kind rules of § 5.1.
- **Panel** `MeterTypesPanel.vue`: a *Meter types* tab in Masters after *Models*, with the table, *Show inactive*, *Add meter type* and the edit dialog.

## 2. How it works

- **Validation in two passes.**
  - Pass 1, `_validate` on a field table, parses each field alone: trimmed names and units with inner spaces collapsed, unit case kept, `_parse_decimals` (bool refused first), kind and expected answer against their lists. `unit`, `expected_answer` and `decimals` are not required on create.
  - If pass 1 finds an error, it is returned. Otherwise pass 2 applies the kind rules to the merged row `{defaults, stored, body}`, each error with its field:
    - a Yes / No type: no unit, an expected answer, decimals 0;
    - any other kind: a unit, no expected answer.
- **PUT.** The route locks the row (`_lock_row`, `FOR UPDATE`), passes it as `stored`, and updates. A `PUT {active: false}` on a valid stored row passes, whatever its kind.
- **POST.** No lock; the unique key `uq_meter_types_name` gives the 409 "A meter type with this name exists" on `name`.
- **The database CHECK** `chk_meter_types_yes_no` is a guard behind the code rules; the user sees the code's message.
- **The panel** always sends all five fields. For Yes / No it sends `unit: null`, `decimals: 0`; for other kinds `expected_answer: null`. *Counter* is preselected on a new type.
  - *Kind* is four radios, each with its help line. *Decimals* is a select 0–3.
  - *Yes / No* hides *Unit* and *Decimals* and shows the *Expected answer* radios.
  - A Yes / No row in the table reads "Yes / No, expects Yes" in *Kind* and "—" in *Unit* and *Decimals*.

## 3. Files touched

Backend:
- `backend/local_db.py`: migration v29.
- `backend/masters_core.py`: `validate_meter_type`, its parsers, `METER_KINDS`, `MAX_DECIMALS`.
- `backend/masters.py`: the three routes, the 409 message for `uq_meter_types_name`, the docstring.
- `backend/tests/conftest.py`: `_SEEDED_TABLES` is a dict table → creator, with `meter_types: migration-v29`; `SEED_CREATOR` stays a string; `Uniq.meter_type_name()`.
- `backend/tests/test_masters_core.py`: `TestMeterType`.
- `backend/tests/test_meter_types_api.py` (new): the routes.
- `backend/tests/test_migration_v29.py` (new): the table and seeds from a v28 database, the unique name, one refused insert per CHECK branch (error 4025) and the decimals CHECK, a re-run.

Frontend:
- `frontend/src/views/masters/MeterTypesPanel.vue` (new).
- `frontend/src/views/MastersView.vue`: the tab and the panel in the map.
- `frontend/src/stores/masters.js`: `meterTypes`, `ensureMeterTypes`, `resetMasters()` nulls it.
- `frontend/e2e/masters.spec.js`: four tests (below).

Docs: see *Docs updated*.

## 4. Decisions taken

Five small choices, all forced; none departs from the brief.

- **The expected answer starts empty** in a new Yes / No dialog. The brief gives no default, and the server refuses a missing answer ("Expected answer is required", shown beside the field), so the engineer picks it on purpose. The e2e test checks that refusal.
- **Pass 2 does not run when pass 1 has errors.** The first error reached the user either way (`clean_body` reports `errors[0]`), and the kind may be missing or invalid.
- **Help texts under *Name*, *Unit* and *Decimals*** (the brief words only the kind lines and the *Expected answer* line):
  - Name: "What is measured, such as Run hours. For a Yes / No type, the question, such as Oil level above min."
  - Unit: "The unit of measure, as written on the meter, such as h, kWh, °C."
  - Decimals: "How many decimals a reading may have: 1 for 62.5 °C, 0 for strokes."
- **`docs/schema.md` "planned" row for `meters`** reworded to point at `meter_types` instead of repeating "type (counter/gauge)", so "type" means one thing. Nothing else in the planned list changed.
- **The e2e "Meter types" row in the sections loop** uses the engineer and the message "Name is required" (a blank Add dialog: *Counter* preselected, empty name and unit; the first error is the name).

## 5. Not done, deferred or assumed

- Nothing deferred. S038 freezes kind, unit, decimals and the expected answer once a meter uses the type; S037 leaves them editable (brief § 1.5).
- `test_rbac.py` is unchanged on purpose: no new key, no role row grows.
- The standards clause numbers in the brief stay "to verify" (U4); nothing in code or screens cites them.
- No real-device checks (brief § 8: "None"), so `device-checks.md` has no new row.

## 6. Tests run

Final full run, `YANTRA_TEST_RUN=s037c1 tooling/run-tests.bat`:

| Suite | Result |
|---|---|
| backend | PASSED, 2593 passed, 92 s |
| frontend | PASSED, 143 passed, 28 s |
| deps | PASSED, 42 passed |
| tooling | PASSED, 106 passed |

- `npx vite build` in `frontend/`: built in 4.24 s (the usual chunk-size warning only).
- Targeted e2e, 6 lanes, all three projects: `e2e/masters.spec.js` and `e2e/screens.spec.js`, **72 passed** in 3.8 minutes. `masters.spec.js` holds the S037 tests; `screens.spec.js` for every route. No shared frontend code changed (the router and `api.js` untouched), so the full suite was not run.
- Each new e2e test was first run alone on `desktop-chromium`, one lane, and passed.

## Fix rounds

### Round 1

Code review `4-code-review-r1.md`: six findings, all fixed.

- **CR1-01 Fixed.** `optional_text_parser` has a `collapse=False` option that uses `_collapsed`. `_parse_meter_unit` is now `optional_text_parser("Unit", METER_UNIT_MAX, collapse=True)`; the old copy is gone. The other callers are unchanged. New `TestOptionalTextParser` (3 tests) covers the option. Fails without the fix (collapse branch reduced to `strip()`): `assert 'a   b' == 'a b'`, and the length test fails on the same input; passes with it. The existing `TestMeterType` unit cases pass too.
- **CR1-02 Fixed.** `docs/schema.md` `meter_types` row: kind `counter` / `gauge` / `amount` (*Amount per period*) / `yes_no`; expected answer `yes` / `no`; unit "NULL exactly when the kind is `yes_no`".
- **CR1-03 Fixed.** `conftest.py`: `SEED_CREATOR` is defined first, with a comment that it is the failure-code seeds' creator for `test_migration_v11.py`; the three v11 entries of `_SEEDED_TABLES` use it.
- **CR1-04 Fixed.** `Maintenance-Philosophy.md` § 8: *Amount per period* and *Yes / No* now follow *Gauge*, in the order of the kind radios.
- **CR1-05 Fixed.** `MeterTypesPanel.vue`: "such as" replaces "e.g." in the Name and Unit help lines. The quotes in "Decisions taken" are updated.
- **CR1-06 Fixed.** `.claude/CLAUDE.md` § SMTW-Review: "`masters` S016/S037".
- **Report count.** "Decisions taken" now says "Five small choices", the number it lists.

Tests of this round (`YANTRA_TEST_RUN=s037c2`):
- Full `tooling/run-tests.bat`: backend 2596 passed (111 s), frontend 143, deps 42, tooling 106; `npx vite build` built in 4.04 s (chunk-size warning only).
- e2e `masters.spec.js` (help text changed), 6 lanes, three projects: 48 passed in 1.8 minutes. `screens.spec.js` not rerun: no route or shared code changed.

## Manual checks

- [auto] Engineer adds a meter type (name with the project name, unit, kind *Gauge*, decimals 1), the row shows, and the dialog fits a phone — `frontend/e2e/masters.spec.js::S037: engineer adds a meter type and sees it in the list`
- [auto] The empty save in the Meter types section is refused beside *Name* with "Name is required" — `frontend/e2e/masters.spec.js::engineer: the Meter types section opens, and an empty add meter type is refused beside its field`
- [auto] An operator sees the meter types but no *Add meter type* button and no edit buttons — `frontend/e2e/masters.spec.js::S037: an operator sees meter types but no Add button`
- [auto] A Yes / No type hides *Unit* and *Decimals*, asks for the expected answer (refused beside its field when missing), and the row reads "Yes / No, expects Yes" with "—" for unit and decimals — `frontend/e2e/masters.spec.js::S037: a Yes / No type hides Unit and Decimals and asks for the expected answer`

On a real device: none.

## Docs updated

- `docs/schema.md`: the `meter_types` row in *Built tables*, the Mermaid overview entry, the "generated at v27, v28 and v29 by hand" line, and the `meters` planned row (see *Decisions taken*); round 1: the stored ENUM values (CR1-02).
- `docs/schema.html`: the "Migration v29 · 30 tables" line, the `meter_types` entry in the Overview tab, and the full table in the Equipment tab (its note names meter types). Both by hand, as there is no generator.
- `docs/Plan.MD` § 4.5: "a type" became "a **kind**", with *meter type* as the catalogue entry and the four kinds; a "Built (S037)" bullet.
- `docs/Maintenance-Philosophy.md` § 8: bullets for *Amount per period* and *Yes / No*; the glossary row *Meter* names the four kinds and the meter type. Round 1: the bullets follow *Gauge* (CR1-04).
- `.claude/CLAUDE.md` (round 1, CR1-06): the § SMTW-Review spec-to-step map reads "`masters` S016/S037".
- `docs/Plant-Facts.md`, `docs/Keycloak.md`, `backend/example_secrets_app.py`: none, because the step adds no invariant, dev command, port, secret, role or plant fact.
