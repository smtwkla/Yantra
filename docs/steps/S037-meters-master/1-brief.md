```
Step: S037 — Meters master
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: full
Status: Gate B (CR r2: 0 findings; r1: 2 minor, 4 nits — all fixed)
Baseline: e451c33 + uncommitted S035, S036, S041, S042
```

# S037 — Meters master

**The need (KLA, 24-10-2026).** "Meters master, meter link to equipment model /
equipment, meter reading entry" — planned and briefed ahead. The work is split
into steps: S037 (this one, the catalogue of meter types), S038 (meters on
models and equipment), S039 (reading entry) and S040 (the end-of-day sheet,
U2) (BR2-11). Plan.MD § 4.5 and Maintenance-Philosophy § 8 describe meters: a tracked quantity on a piece of equipment, of kind **counter**
(only goes up: run hours, strokes, kWh) or **gauge** (a level: oil temperature,
wear in mm).

This step builds only the **catalogue**: the meter types a model or a machine can
later carry, each with a name, a unit of measure and a kind. Nothing uses it until
S038.

Built on e451c33 (S035 in the working tree, which touches no file named here).
This step's migration is **v29**. S038 (v30) and S039 (v31) depend on it.

User answers (U1, 24-10-2026), for the three steps: meters are defined on the
model, and every equipment of the model has them; an equipment may add its own;
readings are per equipment; gauge limits live on the model's meter and may be
overridden per equipment; S039 builds both per-equipment entry and an end-of-day
sheet. User answers U2 (24-10-2026) settle S038–S040 points (every level may
carry meters; operator and up log readings; a fixed 7-day back-date window; the
end-of-day sheet in its own step, S040); none changes this step.

## 1. What will be built

1. **A new master, *Meter types*,** in Masters, after *Models*. Each meter type
   has:
   - **Name**, required, unique (case-insensitive, by the database's collation,
     as manufacturers; BR1-12), up to 60 characters: "Run hours", "Strokes",
     "Energy", "Oil temperature";
   - **Unit**, required (none for a *Yes / No* type), up to 20 characters,
     kept in the case typed ("kWh", "°C"; BR1-09): "h", "strokes", "kWh",
     "°C", "mm", "%", "km";
   - **Kind**: *Counter*, *Gauge*, *Amount per period* or *Yes / No*,
     required (U3);
   - **Expected answer** (*Yes / No* types only, required there): *Yes* or
     *No*, the answer that means all is well. The name is the question, e.g.
     *Oil level above min*, expected *Yes* (U3);
   - **Decimals**: 0 to 3, optional, default 0 (BR1-05); none for a *Yes / No*
     type. It says how many decimals a
     reading of this type may carry (S039), e.g. 1 for "Oil temperature" (62.5),
     0 for "Strokes". Which reading of the day is taken (the day's maximum) is
     a rule of the reading round, not of the type (BR1-06);
   - **Active**, as every master: a deactivated type stays on what uses it and
     is not offered for new links (S038).
2. **Edit rights:** the engineer and up, and IT admin (`equipment:edit`), the
   key that edits manufacturers and models today (`masters.py:500`, `:515`,
   S012). Everyone with `masters:read` sees the list.
3. **Seed rows** in the migration, so the first presses and gensets can be set
   up without typing the obvious ones (from Plan.MD § 4.5 and Plant-Facts lines
   120, 129, 130):

   | Name | Unit | Kind | Decimals |
   |---|---|---|---|
   | Run hours | h | Counter | 1 |
   | Strokes | strokes | Counter | 0 |
   | Production counter | pcs | Counter | 0 |
   | Energy | kWh | Counter | 1 |
   | Odometer | km | Counter | 0 |
   | Oil temperature | °C | Gauge | 1 |
   | Fuel level | % | Gauge | 0 |
   | Shift production | pcs | Amount per period | 0 |

   `created_by` is `migration-v29`, as the failure-code seeds are
   `migration-v11` (`conftest.py:168`).
4. **The panel** (`MeterTypesPanel.vue`, on the `TradesPanel.vue` pattern with
   `useMasterForm`): a table *Name*, *Unit*, *Kind*, *Decimals*, *Active*
   (headed *Active*, not *Status*: the user's decision of 23-10-2026, S030
   CR1-04; the badge reads *Active* / *Inactive*; BR1-04), the *Show inactive*
   switch, *Add meter type*, and an edit dialog with the fields and the
   active toggle. Controls (BR1-07): *Name* and *Unit* text inputs; *Kind* four
   radios, as *Employment* in `PeoplePanel.vue:348`, *Counter* selected in a
   new dialog (the common case; `blank()` as `PeoplePanel.vue:173`; BR2-08);
   for *Yes / No*, *Unit* and *Decimals* hide and an *Expected answer* pair of
   radios (*Yes* / *No*) shows; *Decimals* a select 0 / 1 / 2 / 3 (a number
   input would open a keypad and accept 7). Help text (U3; BR2-09), one
   `form-text` line under each radio:
   - *Counter*: "A running total that only goes up, such as run hours or
     strokes."
   - *Gauge*: "A level that goes up and down, such as a temperature."
   - *Amount per period*: "How much in the period just ended, such as a
     shift's production."
   - *Yes / No*: "A check with two answers, such as Oil level above min."

   Under *Expected answer*: "The answer that means all is well."
   - **What the panel sends** (BR2-02): always all five fields. For *Yes / No*
     it sends `unit: null` and `decimals: 0`; for the other kinds
     `expected_answer: null`. So a kind change never trips over a value hidden
     from the screen.
   - **A *Yes / No* row in the table** (BR2-07): *Unit* and *Decimals* read
     "—"; the *Kind* cell reads "Yes / No, expects Yes" (or "No"), so the
     catalogue shows which answer is good.
5. **Kind and unit are editable in this step.** Nothing uses a type yet. S038
   freezes kind, unit, decimals and the expected answer once a model or an equipment uses the type
   (S038 § 5).

### Out of scope

- Meters on models and equipment (S038); readings (S039).
- Limits: they belong to the meter on a model or a machine, not to the type
  (U1).
- ISO 4406 cleanliness codes: with the oil-sampling plan (phase 4) (U3).
- Shifts as such (shift names, shift times): a reading's *Time taken* places an
  amount (U3; S039 § 9).
- PM triggers on a counter (phase 4).

## 2. Standards and practice

- **Counter and gauge** (Maintenance-Philosophy § 8, Plan.MD § 4.5). A counter
  measures use (operating time, cycles); a gauge measures condition. ISO 14224
  asks for operating time and the number of demands as reliability data of an
  equipment unit, so failure rates can be stated per running hour or per cycle
  (clause and table numbers to verify against the user's copy). EN 13306
  defines condition-based maintenance as maintenance that includes assessing a
  physical condition, by measurement or observation (term number to verify);
  gauges are its measurements.
- **Amount per period** (U3). A quantity for the period just ended, such as a
  shift's production. It is not a counter (it does not run on from the last
  value) and not a gauge (it has no limits). ISO 22400-2 (KPIs for
  manufacturing operations management) uses produced quantity per period as a
  base element of its KPIs (clause and element names to verify). Totals over a
  day or a month are the sum of the amounts.
- **Yes / No: an attribute check** (U3). EN 13306 counts *inspection* as a
  check for conformity of a characteristic, by measurement or observation
  (term number to verify). A Yes / No meter records an observation with two
  outcomes, such as an oil level seen against the sight glass mark. The CIL
  checklists of Plan.MD § 4.4 and Maintenance-Philosophy use OK / Not OK /
  NA; a Yes / No reading with an expected answer is the same OK / Not OK
  judgement, kept as a meter (decision 6).
- **ISO 50001 § 6.4 and § 6.5 (energy performance indicators and the energy
  baseline)** (to verify against the user's copy). The kWh counter of each EB
  incomer and press is the raw data an energy indicator needs (Plan.MD § 4.5).
- **ISO 9001 § 7.1.5 (monitoring and measuring resources).** A reading is only
  as good as the instrument behind it. The unit and the decimals state what is
  measured and how finely. Calibration of the instruments stays a queued idea
  (README › Queued, *Calibration*).
- **One term for one thing** (CLAUDE-COMMON scope B). *Meter type* is the
  catalogue entry; *meter* is a meter type on a model or a machine (S038), the
  glossary's "a tracked quantity on a piece of equipment"
  (Maintenance-Philosophy, glossary).

## 3. Where

### Backend

- `backend/local_db.py`: migration v29 (§ 4).
- `backend/masters_core.py`: `validate_meter_type(data, creating,
  stored=None)` (pure; BR2-01), in two passes. First `_validate` on a field
  table, as `validate_trade`, where `unit`, `expected_answer` and `decimals`
  are not required on create (the kind decides). Then the kind rules of § 5.1
  on the merged row `{**defaults, **stored, **clean}` (`defaults`: `unit`
  None, `expected_answer` None, `decimals` 0), each error with its field. The
  route passes `_lock_row`'s row as `stored` on PUT, nothing on POST.
  `METER_KINDS = ("counter", "gauge", "amount", "yes_no")`, `MAX_DECIMALS = 3`.
- `backend/masters.py`: `GET /api/masters/meter-types`,
  `POST /api/masters/meter-types`, `PUT /api/masters/meter-types/<id>`; the
  module docstring names the new table; no new lock order (one row).

### Frontend

- `frontend/src/views/masters/MeterTypesPanel.vue` (new).
- `frontend/src/views/MastersView.vue`: the tab `{ key: "meter_types", icon:
  "fa-solid fa-gauge", label: "Meter types", perm: "masters:read" }` after
  *Models* (line 28), and the panel in the map (line 39).
- `frontend/src/stores/masters.js`: `meterTypes` and `ensureMeterTypes`, on the
  `ensureTrades` pattern (line 62); `resetMasters()` (line 85) also nulls
  `meterTypes` (BR1-08).

### Tests

- `backend/tests/test_masters_core.py`: `validate_meter_type` cases (§ 8).
- `backend/tests/test_meter_types_api.py` (new): the routes (§ 8).
- `backend/tests/test_migration_v29.py` (new): v29 on a v28 database; the seed
  rows; a re-run.
- `backend/tests/conftest.py`: `_SEEDED_TABLES` (line 167) becomes a dict of
  table → creator, with `"meter_types": "migration-v29"` beside the v11
  tables; `SEED_CREATOR` stays a string, because `test_migration_v11.py` binds
  it as one value (`:40`, `:44`, `:74`, `:80`, `:84`; BR2-05). Seeds survive
  the clean and test rows go.
- `frontend/e2e/masters.spec.js`: the panel (§ 8).

### Docs (housekeeping, by the coder)

The docs pass (`.claude/CLAUDE.md` § Docs to keep current), in this step:

- `docs/schema.md` and `docs/schema.html`: `meter_types` (v29), by hand from
  the migration text: the table row, the Mermaid overview, the Equipment tab
  and the "migration v29" line.
- `docs/Plan.MD` § 4.5: what was built. Its "a unit of measure and a
  **type**: counter or gauge" becomes "a **kind**: counter, gauge, amount per
  period or yes / no", and *meter type* names the catalogue entry, so "type"
  means one thing (BR1-11). The gate A decisions are already recorded there.
- `docs/Maintenance-Philosophy.md` § 8 (lines 295–296) and its glossary row
  *Meter* (line 441, "counter or gauge"): the four kinds (BR2-10).

## 4. Data model (migration v29)

```sql
CREATE TABLE IF NOT EXISTS meter_types (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(60) NOT NULL,
    unit        VARCHAR(20) NULL,            -- NULL only for kind 'yes_no' (U3)
    kind        ENUM('counter','gauge','amount','yes_no') NOT NULL,
    expected_answer ENUM('yes','no') NULL,   -- set only for kind 'yes_no' (U3)
    decimals    TINYINT NOT NULL DEFAULT 0,
    active      TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  VARCHAR(100) NOT NULL,
    updated_at  DATETIME NULL,
    updated_by  VARCHAR(100) NULL,
    CONSTRAINT uq_meter_types_name UNIQUE (name),
    CONSTRAINT chk_meter_types_decimals CHECK (decimals BETWEEN 0 AND 3),
    CONSTRAINT chk_meter_types_yes_no CHECK (
        (kind = 'yes_no' AND unit IS NULL AND expected_answer IS NOT NULL AND decimals = 0)
        OR (kind <> 'yes_no' AND unit IS NOT NULL AND expected_answer IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- the eight seed rows of § 1.3, INSERT IGNORE (name is unique), created_by 'migration-v29'
```

- `INSERT IGNORE` makes a half-applied v29 re-runnable, as the v11 seeds
  (`local_db.py:524`: "every statement keeps what is there"; the failure-code
  seed at `:541`).
- No `_PRECONDITIONS` entry: a new table touches no existing row.
- The `yes_no` CHECK keeps a Yes / No type's shape in the database as well
  (U3); the code rules of § 5.1 report it first, with a field, so the CHECK is
  a guard, never the user's message.
- Rollback: the previous release ignores the table.

## 5. Rules

### 5.1 Validation (`validate_meter_type`, pure)

| Input | Result |
|---|---|
| `name` missing on create | 400 "Name is required" (`name`), from `_validate` (`masters_core.py:290`) |
| `name` empty or only spaces | 400 "Name is required" (`name`) |
| `name` over 60 characters after trimming | 400 "Name must be at most 60 characters" (`name`), `_parse_bounded_name(…, 60)` (`masters_core.py:51`) |
| `unit` missing on create, empty, for a kind other than Yes / No | 400 "Unit is required" (`unit`) |
| `unit` sent for a Yes / No type (U3) | 400 "A Yes / No meter type has no unit" (`unit`) |
| `unit` over 20 characters | 400 "Unit must be at most 20 characters" (`unit`) |
| `kind` missing on create | 400 "Kind is required" (`kind`) |
| `kind` not `counter` / `gauge` / `amount` / `yes_no` | 400 "Kind must be one of: counter, gauge, amount, yes_no" (`kind`), on the `_parse_cause_group` shape (U3; BR2-04: an API caller needs the values) |
| `expected_answer` missing for a Yes / No type (U3) | 400 "Expected answer is required" (`expected_answer`; BR2-04, the masters' wording) |
| `expected_answer` not `yes` / `no` | 400 "Expected answer must be one of: yes, no" (`expected_answer`) |
| `expected_answer` sent for another kind (U3) | 400 "Only a Yes / No meter type has an expected answer" (`expected_answer`) |
| `decimals` other than 0 for a Yes / No type (U3) | 400 "A Yes / No meter type has no decimals" (`decimals`) |
| a `PUT` that changes `kind` to or from Yes / No | the rules above apply to the merged row (body over the stored row, the second pass of `validate_meter_type`; BR2-01), so the unit or the expected answer comes in the same `PUT`; the panel always sends all five fields (§ 1.4) |
| `decimals` absent on create | 0 |
| `decimals` a bool (checked first, `isinstance(raw, bool)`, as `_parse_id`, `masters_core.py:132`), a float, a string, or outside 0–3 | 400 "Decimals must be a whole number from 0 to 3" (`decimals`), a new `_parse_decimals` |
| `active` not a bool | 400, as the other masters |
| A `PUT` without a field | the field is unchanged |
| Unknown keys | ignored, as the other masters (`clean_body`) |

**"Sent"** (BR2-02) means present, not `null` and not empty after trimming.
`null` or `""` for `unit` or `expected_answer` stores NULL. The kind rules
run after the field parsers, on the merged row.

The wording is the masters' own (BR1-01: scope B, one wording across the
Masters tabs; re-wording every master in the "Enter a …" style is the queued
*Tidy-up*'s job). Names and units are trimmed, and inner runs of spaces become
one (`_collapsed`, `masters_core.py:63`). Neither is upper-cased: no
`_code_parser` (BR1-09).

### 5.2 Checks against the database

- A duplicate name → 409 "A meter type with this name exists" (`name`), from the
  unique key (`UNIQUE_KEY_ERRORS`, as trades).

### 5.3 Locks

- Create: no lock (the unique key decides).
- Update: the row alone, `FOR UPDATE` (`_lock_row`, as trades). S038 adds a
  count of its uses under this lock.

### 5.4 Reads

- `GET /api/masters/meter-types`: active only by default; `include_inactive=1`
  for all (`_include_inactive`, as the other masters); by name.

### 5.5 The database down

Every route raises `DBUnavailable` → 503, as every master route. Migration v29
runs under `ensure_schema()`'s retry.

## 6. API

| Method | Path | Key | Body | Response |
|---|---|---|---|---|
| GET | `/api/masters/meter-types` | `masters:read` | — | `{items: [{id, name, unit (null for Yes / No), kind, expected_answer (null unless Yes / No), decimals, active}], total}`, via `_list_response` (`masters.py:136`), as trades (BR1-02; BR2-03) |
| POST | `/api/masters/meter-types` | `equipment:edit` | `name, kind, unit?, expected_answer?, decimals?`, with the kind rules of § 5.1 | 201, the row |
| PUT | `/api/masters/meter-types/<id>` | `equipment:edit` | any of the fields, `active` | 200, the row; 404 unknown id |

`equipment:edit` is site-scoped, and `require_perm` checks it on the union of
sites, as for models: a meter type is not at a site.

## 7. Design decisions

1. **A catalogue of meter types, separate from the meters on machines** (U1:
   "meters master"). Ten presses share "Strokes" with one meaning. Rejected:
   free-text meter names per machine (Plan's first schema line, `meters` "per
   equipment: name, unit…"), which makes "kWh per site" a text match.
2. **`equipment:edit` as the edit key.** Meter types sit beside models, which
   engineers keep. Rejected: `masters:edit` (IT admin only; the engineers know
   the meters) and a new key (no role would differ).
3. **Decimals on the type.** A reading's precision is a property of what is
   measured. Rejected: free precision (62.4999 °C from a typo).
4. **Seed eight types** (U3: *Shift production* added). Rejected: an empty list (every site types "Run hours"
   in its own spelling).
5. **No limits on the type** (U1: limits on the model's meter).
6. **Yes / No as a meter, not a checklist item** (U3: "A Boolean meter type
   will be needed. Oil Level Above Min Y/N."). A checklist item belongs to a
   PM or CIL job (phase 4, Plan.MD § 4.3–4.4); a meter can be read on any
   round today, on the sheet (S040), and its readings are a history to look
   back on. A later CIL item may write the same meter, as a PM reading item
   writes a meter reading (Plan.MD § 4.3). Rejected: waiting for the CIL
   checklists (the daily round starts now).
7. **The expected answer on the type** (U3). The question's wording fixes which
   answer is good ("above min" → Yes). Rejected: on the model's meter, as
   limits (the same question cannot be good-when-No on another machine).
8. **No Yes / No seed row** (U3). The wording of a check depends on the
   machine (sight glass, dipstick, float switch), so the engineers name their
   own. Rejected: seeding *Oil level above min*.

## 8. Tests and acceptance

### Backend (pytest)

- `test_masters_core.py`: every row of § 5.1, `amount` and `yes_no` accepted as kinds; a Yes / No type with a unit, without an expected answer, with decimals 1; an expected answer on a gauge; a `PUT` from gauge to Yes / No without the expected answer (U3), including `decimals` `True`,
  `1.0`, `"1"`, `-1`, `4`; trimming and inner spaces.
- `test_meter_types_api.py`. **Seed rows are read, never changed; test rows
  take names from the `uniq` fixture** (the rule of
  `test_failure_codes_api.py:3`; `_clean_tables` keeps seed rows between runs,
  `conftest.py:188`; BR1-03):
  - list: the eight seed names present and active, *Shift production* of kind `amount`; `include_inactive=1`;
  - create as engineer: 201; as operator and storekeeper: 403; as IT admin:
    201;
  - duplicate name, other case → 409 on `name`;
  - on a row the test creates first: update kind, unit, decimals; deactivate;
    reactivate;
  - a Yes / No type: created with an expected answer and no unit (201,
    `unit: null`); its row read back (U3);
  - 404 unknown id.
- `test_migration_v29.py`: from the v28 shape, the table and the eight rows;
  a second run adds nothing. One refused insert per branch of
  `chk_meter_types_yes_no` (BR2-06): a `yes_no` row with a unit, with
  decimals 1, without an expected answer; a `counter` row without a unit, with
  an expected answer. Each fails with 4025.
- `test_rbac.py`: no new key, nothing changes (checked: no role row grows).

### Automated (e2e)

- `masters.spec.js`: "S037: engineer adds a meter type and sees it in the
  list": opens Masters › Meter types, *Add meter type*, fills name (carrying
  the project name, as the three projects share one database,
  `masters.spec.js:28`; BR1-10), unit, kind *Gauge*, decimals 1, saves; the
  row shows; the dialog fits a phone (`expectDialogFits`).
- `masters.spec.js`: a *Meter types* row in the "Masters sections" loop
  (`masters.spec.js:115`), for the empty-save refusal "Name is required".
- `masters.spec.js`: "S037: an operator sees meter types but no Add button".
- `masters.spec.js`: "S037: a Yes / No type hides Unit and Decimals and asks
  for the expected answer" (U3).
- `screens.spec.js`: no new route (a Masters tab).

### On a real device

None.

### Acceptance

The eight seeds show in Masters › Meter types; an engineer adds, edits and
deactivates a type; an operator only reads.

## 9. Open questions and assumptions

1. **The words** (assumption): tab *Meter types*, button *Add meter type*,
   kinds *Counter* / *Gauge* / *Amount per period* / *Yes / No*, *Expected
   answer*, the help line of § 1.4.
2. **The seed list** (assumption): § 1.3. Add or drop names before coding.
3. **Standards clause numbers** (to verify): ISO 14224 operating time, EN 13306
   condition-based maintenance, ISO 50001 § 6.4 / § 6.5, ISO 22400-2 produced
   quantity.

## 10. Amendments

None.

## Review log

### U1 — user answers, 24-10-2026 (before drafting)

- Meters defined on the model, every equipment of the model has them; an
  equipment may add its own; readings per equipment.
- Gauge limits on the model's meter, overridable per equipment.
- S039 builds per-equipment entry and an end-of-day sheet.

### U2 — user answers, 24-10-2026 (after round 1, for S038–S040)

- Every level of the tree may carry meters (S038).
- Operator and up log readings, not IT admin (S039).
- Back-dating a reading: a fixed 7 days, for everyone (S039).
- The end-of-day sheet is its own step, S040.

None of these changes S037.

### U3 — user comments on the review page, 24-10-2026

- ISO 4406 was raised too early: removed from this step (Out of scope; with the
  oil-sampling plan, phase 4).
- A reading is removed only by `equipment:edit` holders (S039, S040).
- "Production counter is cumulative. Period. 'Day's production' is a different
  meter, with daily reading. Or better, Shift Production." So a third kind,
  `amount` (*Amount per period*): a quantity for the period just ended, 0 or
  more; *Production count* stays a counter; *Shift production* is seeded.
  Rejected: a gauge for it (a gauge has limits and High / Low marks meant for
  levels).
- "A Boolean meter type will be needed. Oil Level Above Min Y/N." So a fourth
  kind, `yes_no` (*Yes / No*), with the expected answer on the type, no unit
  and no decimals (§ 1.1, § 4, § 5.1, decisions 6–8). Not seeded.

### U4 — approval, 24-10-2026

- "I have reviewed the brief. Except what I changed above, it all is
  accepted. Implement." Approved by KLA.
- Every proposed default of the review page is accepted: D5 the eight seed
  types; D11 the words; D12 the clause numbers stay "to verify"; for the other
  steps D1–D3, D6, D8–D10.
- D4 dropped: ISO 4406 is out (U3). D7 replaced by U3 (removal by
  `equipment:edit` only).

### Round 1 — `2-brief-review-r1.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 4 minor, 9 nits. No blocker or major open: review loop
complete.

| Finding | Answer |
|---|---|
| BR1-01 minor — the messages break the masters' wording | Accepted (a): the masters' messages, `_parse_bounded_name`, a new `_parse_decimals`; § 5.1 |
| BR1-02 minor — GET shape | Accepted: `{items, total}` via `_list_response`; § 6 |
| BR1-03 minor — tests that change a seed row | Accepted: seeds read only, test rows by `uniq`; § 8 |
| BR1-04 minor — *Status* column header | Accepted: headed *Active*; § 1.4 |
| BR1-05…BR1-13 nits | All accepted. BR1-05: decimals optional. BR1-06: one name "Oil temperature". BR1-07: radios for *Kind*, a select for *Decimals*. BR1-08: `resetMasters()` nulls `meterTypes`. BR1-09: unit keeps its case; the bool guard. BR1-10: project name in the e2e name; a sections-loop row. BR1-11: Plan.MD "kind". BR1-12: the database's collation. BR1-13: S038's `_TABLES` text fixed in S038. |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 4 minor, 7 nits. Re-read the U3 sections only.

| Finding | Answer |
|---|---|
| BR2-01 minor — where the kind rules run | Accepted (a): `validate_meter_type(data, creating, stored=None)`, two pure passes, the merged row; § 3, § 5.1 |
| BR2-02 minor — what the panel sends for hidden fields | Accepted (a): always five fields (`unit: null`, `decimals: 0` for Yes / No; `expected_answer: null` otherwise); "sent" defined; § 1.4, § 5.1 |
| BR2-03 minor — § 6 lacks `expected_answer` | Accepted: GET item and POST body updated; § 6 |
| BR2-04 minor — three messages | Accepted: "Expected answer is required", "… meter type …", "Kind must be one of: counter, gauge, amount, yes_no"; § 5.1 |
| BR2-05…BR2-11 nits | All accepted. BR2-05: `_SEEDED_TABLES` a dict, `SEED_CREATOR` a string. BR2-06: refused inserts per CHECK branch. BR2-07: a Yes / No row shows "—" and "expects Yes". BR2-08: *Counter* preselected. BR2-09: one help line per radio, a line under *Expected answer*. BR2-10: Maintenance-Philosophy § 8 and glossary in the docs pass. BR2-11: the 45-word sentence split. |

### U6 — seed renamed, 25-10-2026

- The user, on the dev instance: "Production count" must be "Production counter", to tell it from *Shift production*. The v29 seed is edited in place (`local_db.py`, `test_meter_types_api.py`, `test_migration_v29.py`, § 1.3), by the user's choice: a one-time exception to "never edit an applied migration", because v29 has run only on this laptop and was never deployed. The local dev database and the 246 local test databases holding `meter_types` were renamed by hand (`UPDATE … WHERE name = 'Production count' AND created_by = 'migration-v29'`); the e2e databases are rebuilt each run. The snapshot `refs/steps/S038` still holds the old name; the fix rides in the next snapshot.
