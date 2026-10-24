```
Step: S037 — Meters master
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 24-10-2026
```

# S037 — Meters master: code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the
brief asks, and nothing more. Two `minor` findings and four nits remain.
They go to one fix round with no question for the user.

## Test runs (this review, `YANTRA_TEST_RUN=s037cr1`)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | All four suites PASSED: backend 2593 passed (96 s), frontend 143, deps 42, tooling 106 |
| `npx vite build` in `frontend/` | Built in 3.86 s; only the usual chunk-size warning |
| `tooling/run-e2e-tests.bat e2e/masters.spec.js e2e/screens.spec.js` | **72 passed** (3.7 min, 6 lanes, all three projects) |

These are the targeted specs: `masters.spec.js` holds the S037 tests, and
`screens.spec.js` opens every route. S037 changes no shared frontend code.
`stores/masters.js` is not the auth store, so the full suite is not needed.
The router change in the tree belongs to S035, which was reviewed on its own.

## Findings

### CR1-01 (minor) — `_parse_meter_unit` repeats `optional_text_parser`

- **Where:** `backend/masters_core.py:335`.
- **Problem:** the function repeats the body of `optional_text_parser`
  (`masters_core.py:102`): the None check, "must be text", the length check
  and `text or None`. The one difference is that it collapses inner spaces
  where the existing helper only strips.
- **Failure scenario:** a later change to text parsing, such as a new
  "must be text" wording, is made in `optional_text_parser` and missed here.
  The unit field then answers differently from every other optional text
  field in the masters.
- **Fix:** give `optional_text_parser` a `collapse=False` option that uses
  `_collapsed`. Then write `_parse_meter_unit =
  optional_text_parser("Unit", METER_UNIT_MAX, collapse=True)`. The existing
  `TestMeterType` unit cases cover the change.

### CR1-02 (minor) — `docs/schema.md` gives one kind under its screen name, not its stored value

- **Where:** `docs/schema.md:39`, the `meter_types` row.
- **Problem:** the row lists the kinds as "counter / gauge / amount per period
  / yes_no". The ENUM value is `amount`, not "amount per period". The row
  writes three stored values and one screen label, so a reader cannot tell
  which form the column holds. All four kinds are named, so this is not a
  missing ENUM value, and the finding is `minor`.
- **Failure scenario:** someone who writes a report query from the schema doc
  writes `WHERE kind = 'amount per period'`. The query finds no rows, and
  gives no error.
- **Fix:** write the stored values, with the screen word in brackets once:
  "kind `counter` / `gauge` / `amount` (*Amount per period*) / `yes_no`",
  and "expected answer `yes` / `no`". In the same row, "unit (empty only for
  a Yes / No type)" reads better as "unit (NULL exactly when the kind is
  `yes_no`)". That is what the CHECK enforces.

## Nits

- **CR1-03** (nit) `backend/tests/conftest.py:168-170`: `SEED_CREATOR` and the
  dict both hold the text `"migration-v11"`. Use `SEED_CREATOR` for the three
  v11 entries of `_SEEDED_TABLES`, or say in the comment that `SEED_CREATOR`
  is v11's creator only, for `test_migration_v11.py`.
- **CR1-04** (nit) `docs/Maintenance-Philosophy.md:296`: the two new bullets
  sit between *Counter* and *Gauge*. Move them after *Gauge*, so the two
  original kinds stay together and the list follows the order of the kind
  radios.
- **CR1-05** (nit) `frontend/src/views/masters/MeterTypesPanel.vue:131`, `:164`:
  the new help lines use "e.g.", but the brief's kind lines use "such as".
  Use "such as" in both lines, so the dialog uses one style ("What is
  measured, such as Run hours. …").
- **CR1-06** (nit) `.claude/CLAUDE.md:50` (§ SMTW-Review): the spec-to-step map
  reads "`masters` S016". `masters.spec.js` now holds the S037 tests. Make it
  "`masters` S016/S037", so the audit maps a failing `S037: …` test to its step.

## The coder's choices in "Decisions taken"

All five are sound. None departs from the brief.

| Choice | Judgement |
|---|---|
| The expected answer starts empty in a new Yes / No dialog | Right. The answer is the meaning of the question, so a default would let a wrong one through. The refusal "Expected answer is required" shows beside the field, and the e2e test checks it. |
| Pass 2 is skipped when pass 1 has errors | Right. `clean_body` reports only `errors[0]`, and pass 2 needs a valid kind. |
| Help lines under *Name*, *Unit* and *Decimals* | Accepted. The lines are short, they give an example, and they are listed in the report. Only the "e.g." wording is a nit (CR1-05). |
| The `meters` planned row in `schema.md` points at `meter_types` | Right. "type (counter/gauge)" would give "type" a second meaning (BR1-11). |
| The sections-loop row uses the engineer and "Name is required" | Right. *Counter* is preselected, so the name is the first error of an empty save. |

## Checked and found consistent

- **Migration v29** (`local_db.py`):
  - The table matches brief § 4 column by column.
  - `chk_meter_types_decimals` holds 0–3.
  - `chk_meter_types_yes_no` covers both branches. No term can be NULL
    (`kind` is NOT NULL, and the others are `IS [NOT] NULL` tests or the NOT
    NULL `decimals`), so the CHECK never passes as "unknown".
  - The eight seed rows match § 1.3, with `created_by` `migration-v29`.
  - `CREATE TABLE IF NOT EXISTS` and `INSERT IGNORE` make a re-run safe.
  - There is no `_PRECONDITIONS` entry, which is right because the table is new.
  - The charset is `utf8mb4`, as every table, and "°C" reads back intact
    (API test).
- **`test_migration_v29.py`**: from v28 to v29; all eight seed rows read back;
  the unique name in another case; one refused insert per branch of the
  CHECK (five rows, error 4025, named constraint); the decimals CHECK; a
  re-run that keeps an edit and adds nothing.
- **`_SEEDED_TABLES` as a dict:** `_clean_tables` deletes each table's rows
  whose `created_by` is not that table's seed creator. `SEED_CREATOR` stays
  the string `"migration-v11"`. `test_migration_v11.py:10`, `:40`, `:44`,
  `:74`, `:80` and `:84` still bind it as one value, and the suite is green.
- **Validation** (`validate_meter_type`): every row of brief § 5.1 has its
  message and field. These cases are refused: a bool for decimals (checked
  first), floats, strings and out-of-range numbers. A list or dict for
  `kind` or `expected_answer` is refused, not a 500. "Sent" means not null
  and not empty, as BR2-02 says. On a PUT the merged row is defaults, then
  the stored row, then the body, so a kind change is judged as the row it
  would make.
- **Routes** (`masters.py`): GET is gated by `masters:read`; POST and PUT by
  `equipment:edit`, as models. The actor comes from `actor()`, never the
  body, and no SQL is built from client input. The PUT reads the body
  inside the transaction, after `_lock_row`, so the stored row it validates
  against cannot change before the update. The 409 on `uq_meter_types_name`
  comes on create and on rename. An unknown id gives 404, and a DB outage
  gives 503 through `get_db()`.
- **Design:** the rules are in the pure core, and the routes are a thin
  shell on the trades pattern. The panel only shapes the body (`toBody`, all
  five fields), and holds no business rule.
- **Frontend:** `MeterTypesPanel.vue` follows `TradesPanel.vue` and
  `useMasterForm`. `FormModal` is `modal-dialog-scrollable`, and
  `expectDialogFits` passes on both phone projects. The column is headed
  *Active*, with an *Active* / *Inactive* badge. A Yes / No row reads "—" for
  unit and decimals and "Yes / No, expects Yes" for kind. Deactivate goes
  through `ActiveToggle`'s confirm step. The empty and loading states are
  shown. The table is in `table-responsive`.
- **Store:** `meterTypes`, `ensureMeterTypes` and the reset in
  `resetMasters()` (BR1-08).
- **Tests against § 8:** every listed backend case is covered, the failure
  modes included. The four e2e tests assert what the user sees: the row
  text, the preselected *Counter*, the hidden fields, the refusal beside its
  field, and no *Add* or *Edit* button for the operator. Both add flows call
  `expectDialogFits`. `test_rbac.py` is unchanged, which is right because
  there is no new key.
- **Docs pass:**
  - `schema.md`: the table row, the Mermaid entry, the "v29 by hand" line
    and the planned `meters` row. The stored-value wording is CR1-02.
  - `schema.html`: "Migration v29 · 30 tables", the overview entry, and the
    full Equipment-tab table with every column and its "null" marks.
  - `Plan.MD` § 4.5 now says "kind", uses *meter type* for the catalogue
    entry, and has the "Built (S037)" bullet.
  - `Maintenance-Philosophy.md` § 8 and its glossary row name the four kinds.
  - No other doc in `.claude/CLAUDE.md` § Docs to keep current is due.
- **Scope:** nothing is missing and nothing extra is built. Every departure is
  in "Decisions taken". The step is on the full track, and its migration
  calls for it.
- **Manual checks:** the report's `## Manual checks` carries the brief's four
  automated checks as `[auto]`, each with its test, and all passed in this
  run. The brief has no real-device check, so `device-checks.md` gets no row.
- **Writing style:** the impl report keeps scope A. The screen text keeps
  scope B: the buttons start with a verb, the masters' messages are used,
  and there are no exclamation marks.

## Manual browser check for the user

None is required. The brief has no real-device check, and the four automated
checks passed on Pixel 7 Chromium, iPhone 14 WebKit and desktop Chromium. If
you want to look yourself, open Masters › Meter types on a phone. Check that
the four kind radios and their help lines scroll in the dialog, with *Save*
still in view.
