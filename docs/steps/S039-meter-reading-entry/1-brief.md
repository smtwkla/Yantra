```
Step: S039 — Meter reading entry
Doc: brief
Author: Planner (Opus)
Date: 24-10-2026
Track: full
Status: Gate B (CR r2: 0 blocker, 0 major; r1–r2 findings fixed; CR2-01 to be re-checked by S040's review; card order and CR1-06 for the user)
Baseline: ff9ddb3 + snapshot refs/steps/S038 (S037, S038) + S043 (port, working tree); stale check s1 done 24-10-2026
```

# S039 — Meter reading entry

**The need (KLA, 24-10-2026).** "Meter reading entry." Third of the meter
steps. S037 builds meter types, S038 puts meters on models and nodes; this step
records **readings**, one meter at a time, from the equipment page. The
end-of-day sheet (every meter of a site on one screen, U3) is **S040**, built on
this step's rules (U2, BR1-07).

User answers (U1, 24-10-2026): readings are per equipment; both entry paths
(per equipment and an end-of-day sheet) are wanted.

User answers (U2, 24-10-2026, after round 1):
- the sheet is its own step, S040; this step is the per-equipment entry;
- **operator and up** log readings, not IT admin (§ 9.2 settled);
- a reading may be back-dated a **fixed 7 days**, for everyone, admin included:
  a stated departure from S028's `backdate_days` (decision 8).

Built on e451c33 plus S037 (v29) and S038 (v30), both approved and coded
before this step. This step's migration is **v32**.

## 1. What will be built

1. **A reading** is a value for one meter of one node (S038: identity = node +
   meter type), with the **time taken**, an optional **note** (up to 200
   characters), and for a counter a **Meter reset** mark. It stores who entered
   it and when, and its source `manual` (Plan.MD § 4.5: `pm`, `move`, `iiot`
   come later).
2. **The rules** (§ 5): a counter reading may not be lower than the reading
   before it in time, nor higher than the one after it, unless it is marked as a
   meter reset (Plan.MD § 4.5). A gauge reading outside its limits **is saved**
   and marked *High* or *Low*: the out-of-limit value is the point of measuring
   (EN 13306, condition monitoring). An **amount per period** (S037's third
   kind, e.g. *Shift production*; U3) is 0 or more, with no order check and no
   limits: each reading is the quantity of the period just ended, and totals
   are sums. A **Yes / No** reading (S037's fourth kind, e.g. *Oil level above
   min*; U3) is Yes or No; an answer other than the type's expected answer
   **is saved** and marked *Not OK*, as a gauge outside its limits. It has no
   order check, no reset and no sum.
3. **On the equipment page,** the *Meters* card of S038 gains, per meter:
   - **Last reading**: "12,345.6 h · 23-10-2026 18:00", and a *High* / *Low*
     badge on a gauge outside its limits. The line is the tap target for
     **History** (a chevron at its end; BR1-16), so a four-meter card carries
     one button per meter, not two. Before any reading, the line reads "No
     readings yet" and is not a tap target (BR2-08);
   - **Log reading** (`reading:log` holders): a dialog with *Value* (with the
     unit beside it, `inputmode="decimal"` for the phone keypad), *Time taken*
     (`views/tickets/EventFields.vue`, "Now · Change", `withRemark: false`,
     `timeLabel: "Time taken"`; "Now" sends no `taken_at`, so the server's
     clock decides and a phone a few minutes off is never refused; S040
     BR1-09) (default now), *Meter reset* (counters only, with the help "Tick this only
     when the meter was replaced or set back to zero"; BR1-19), *Note*. Above
     the value: "Last reading: 12,345.6 h on 23-10-2026 18:00", left out when
     the meter has no reading yet (BR2-08). After saving, an out-of-limit
     gauge shows "Saved. Above the limit of 60 °C." or "Saved. Below the
     limit of 10 °C." in the dialog's place on the card; a reading inside its
     limits (or a counter) closes the dialog and updates the card's last
     reading, with no message (BR2-09). For an amount meter the value's help
     reads "The amount for the period just ended, such as this shift." (U3).
     **For a Yes / No meter** (U3; U4, decision 11) the dialog shows the
     question (the type's name) as its heading and, in place of *Value*, two
     large toggle buttons side by side, **Yes** and **No** (full width between
     them, at least 48 px high); the picked one shows pressed. *Time taken* and
     *Note* follow, then the dialog's normal *Save* saves the reading, as on the
     S040 sheet (S040 decision 9). *Save* is disabled until an answer is picked
     (`saveDisabledReason` "Pick Yes or No"). So a note typed after the answer
     is kept, and a mis-tap is corrected before saving. *Yes* and *No* do not
     start with a verb: the heading is the question and the buttons are its
     answers, a stated departure from scope B's verb rule, as S038's *Remove* /
     *Keep* (BR3-07). An unexpected answer shows "Saved. Not OK: the expected
     answer is Yes." in the dialog's place on the card; an expected one closes
     the dialog. The card's last reading reads "Yes · 23-10-2026 18:00", with
     a *Not OK* badge when it was not the expected answer;
   - **History**: a dialog with the last 30 readings, newest first: time,
     value, *High* / *Low* / *Not OK* / *Reset* badges (BR3-06), who (the login, `created_by`, as
     the equipment page's *Created by* row in `EquipmentDetailView.vue`; no join
     to `people`; BR2-10), note; and *Show more* (the next page, § 6).
   - **Where the card sits** (BS1-04): the *Meters* card stays where S038
     put it, after the Details / Properties (S043) / Parts row and before
     Notes. On a phone *Log reading* is then about two screens down the page;
     the daily path for the press supervisors and the genset round is S040's
     sheet, so the order is kept. For the user at gate B: the alternative is
     the card above Details for `reading:log` holders.
4. **Remove a reading** (a typo blocks every later counter entry): from the
   *History* dialog, only by a holder of `equipment:edit` at the node's site
   (engineer, manager, IT admin; U3). The author who is not one asks an
   engineer. IT admin holds no `reading:log` but may remove: removal is a
   correction, not logging. The *Remove* button shows only on the readings
   the user may remove (`can_remove` in the GET, BR1-04). Removal hides the reading (who and when
   kept), as documents (S006); the counter rules then ignore it.
   Confirmation, inline in the history row with [*Remove*] [*Keep*], as
   S038's remove (S038 BR1-07; BR2-12): "Remove the reading of 23-10-2026
   18:00 (12,345.6 h)? It no longer counts. You cannot undo this." The
   bracket is `formatReading`'s text: "(No)" for a Yes / No reading, "(420
   pcs)" for an amount (BR3-06).
   - **A reset reading with an active later reading cannot be removed**
     (BR1-04): 409 "This reading marks a meter reset. Remove the later
     readings first." Removing it would leave the later, lower readings with
     no reset, and no back-dated reading could fit between them.
5. **What the sheet (S040) takes from this step:** the POST, the rules, the
   remove route, `can_remove`, and the refusal code `counter_lower` on the
   "Lower than …" 400 (BR2-02), by which the sheet shows its *Meter reset*
   tick. S040 adds the sheet's page, its read and the
   nav item.

### Out of scope

- The end-of-day sheet, its read route and the *Readings* nav item (S040).
- A ticket raised on an out-of-limit reading, and PM triggers (phase 4).
- Readings on a PM job or a ticket step (`source` `pm`, phase 4).
- Charts and reports of readings (phase 5).
- Readings older than 7 days: old notebooks cannot be loaded (U2, decision 8).
- Editing a reading in place: a wrong one is removed and entered again.

## 2. Standards and practice

- **EN 13306, condition monitoring and condition-based maintenance** (term
  numbers to verify): measuring a characteristic at intervals, and acting when
  it leaves its limits. A gauge reading outside its limits is the signal; this
  step records and flags it, phase 4 acts on it.
- **EN 13306, inspection** (term number to verify; BR3-08): a check for
  conformity by observation is an *inspection*. A Yes / No reading records an
  inspection's result, and *Not OK* is its nonconformity.
- **ISO 22400-2, production quantity per period** (U3; clause and element
  names to verify): the KPIs of manufacturing operations are built on the
  quantity produced in a period, such as a shift. An amount reading is that
  quantity; a day's or a month's total is the sum.
- **ISO 14224, operating time** (clause to verify): run hours and cycle counts
  per unit are the denominator of failure rates (MTBF per run hour), phase 5.
- **ISO 50001 § 6.6 (planning for collection of energy data)** (2018 edition;
  to verify against the user's copy): the daily kWh of each EB incomer and
  press, read at a fixed time, is the energy data plan's raw input (Plan.MD
  § 4.5).
- **TPM, autonomous maintenance** (Maintenance-Philosophy): operators and
  supervisors take the readings of their own machines, as in their notebook
  today (Plant-Facts line 120).
- **ISO 9001 § 7.5.3 (control of documented information)** (BR1-08): a record
  is protected from loss and unintended change. "Remove, never edit"
  (decision 5) keeps every value that was entered, with who and when. In plain
  terms: § 7.5.3 says "trust the record". Its neighbour § 7.1.5 (monitoring and
  measuring resources) says "trust the instrument": the energy meter or the
  temperature probe must be fit and, where it matters, calibrated. Readings
  depend on it; that is the queued *Calibration* item, not this step.
- **ISO 27001 A.8.15 (logging)** (BR1-08): who removed a reading and when is
  kept, as for documents and tickets.
- **ISO 55001 § 7.5**: the information the organisation decided to keep (the
  readings) is kept with its source.

## 3. Where

### Backend

- `backend/local_db.py`: migration v32 (§ 4).
- `backend/config_rbac.py`: `reading:log` → `("maint_operator",)` (the
  supervisor and the maintenance ladder inherit it, as `ticket:raise`); added to
  `SITE_SCOPED` (its comment: "every later … reading … key joins this list",
  line 159). Not IT admin (U2; Plan.MD § 3 matrix: no ✓ for it_admin).
- `backend/meters_core.py` (from S038): `_parse_limit` renamed `parse_number`
  and reused by `validate_reading` for every number row of § 5.1, with its
  messages from `_decimals_message` (BS1-01); `validate_reading(value, kind,
  decimals, reset, note)` (BR3-05: the kind decides the rules; for a Yes / No
  meter the value rule is "Pick Yes or No" alone, and the number rows of § 5.1
  do not apply; it returns `Decimal(1)` for `"yes"` and `Decimal(0)` for
  `"no"`, BR3-04), `reading_time_error(taken_at, now)`, `counter_error(value,
  is_reset, before, after)`, `limit_state(value, min, max)`,
  `answer_state(answer, expected)` (U3),
  `may_remove(reading, can_edit)` (U3: no author rule), `reset_removal_error(reading,
  has_later)`. Import direction (BR1-10): `meters_core` imports
  `parse_event_time`, `FUTURE_SKEW`, `EVENT_TIME_FORMAT`, `EVENT_TIME_FUTURE`
  from `tickets_core` (pure to pure, `tickets_core.py:52–92`); `tickets_core`
  never imports `meters_core`. The 7-day limit and its message are
  `meters_core`'s own: `READING_BACKDATE_DAYS = 7`,
  "When was it read? Up to 7 days back". `backdate_days` is not used
  (decision 8).
- `backend/meters.py` (from S038): `_lock_node` gains a `key` parameter
  (`reading:log` for a reading write, `equipment:edit` for a remove;
  today it hard-codes `equipment:edit`), not a second helper (BS1-06); the
  in-force check of § 5.2.1 is `_meters_of(cur, node_id, model_id)`, which
  calls `effective_meters` (BS1-10); its own docstring's *Locks* paragraph
  gains the reading line. The reading routes (§ 6), and one row
  builder, `reading_out(row, kind)`, that turns a Yes / No meter's stored 1 / 0
  back into `"yes"` / `"no"` for the history GET, the POST's answer and
  `last` (BR3-04): the word ↔ number mapping lives in these two places only.
- `backend/api_common.py`: `ApiError` gains an optional `code`, sent as
  `{error, field, code}` when set (BR2-02); `api.js:25` already reads
  `err.code` (the network gate's JSON, `access_control.py:152`). No other
  error changes shape.
- `backend/equipment.py`: the LOCK ORDER docstring's existing `meters.py`
  bullet gains the reading write under (1), with plain reads after it
  (§ 5.3); no new bullet (BS1-06).

### Frontend

- `frontend/src/views/equipment/ReadingFormModal.vue` (new; a plain
  `FormModal` with its usual *Save*, so `FormModal.vue` does not change),
  `frontend/src/views/equipment/ReadingHistoryModal.vue` (new).
- `frontend/src/views/equipment/MetersCard.vue` (S038): last reading, the
  *History* tap target, *Log reading*.
- `frontend/src/utils/meterLabels.js` (S038): `formatReading` (thousands
  separators, Indian grouping, `toLocaleString("en-IN")`, U4),
  the badge words.

### Tests

- `backend/tests/test_meters_core.py`, `backend/tests/test_readings_api.py`
  (new), `backend/tests/test_migration_v32.py` (new), `backend/tests/test_rbac.py`
  (the matrix gains `reading:log` for operator, supervisor, technician,
  engineer, manager), `backend/tests/conftest.py` (`meter_readings` in
  `_TABLES`, first).
- `frontend/tests/meterLabels.test.js`.
- `frontend/e2e/readings.spec.js` (new), `frontend/e2e/equipment.spec.js`,
  `frontend/e2e/support/meters.js` (S038's `meterMachine` moved there from
  `equipment.spec.js` and exported; `equipment.spec.js` imports it;
  `createEquipment` stays where it is, unchanged; § 8; BS1-03).
- `frontend/tests/navigation.test.js`: the role lists mirror `test_rbac.py`
  (its comment, line 4), so this step adds `reading:log` to OPERATOR
  (SUPERVISOR is `OPERATOR`, line 11), ENGINEER and MANAGER there, three
  edits (BS1-07); the `visible(...)` expectations
  do not change until S040 adds the nav item (S040 BR1-15).

### Docs (housekeeping, by the coder)

The docs pass (`.claude/CLAUDE.md` § Docs to keep current), in this step:

- `docs/schema.md` and `docs/schema.html`: `meter_readings` (v32), by hand
  from the migration text: the table row, the Mermaid overview, the Equipment
  tab, the links to `equipment` and `meter_types`, and the "migration v32"
  line. `docs/schema.md`'s planned `meter_readings` row ("result-row link …")
  is replaced by the built row; `schema.html`'s meta line becomes v32, 37
  tables, 53 links (BS1-09).
- `docs/Plan.MD` § 4.5 (the reading rules as built) and § 3 (the `reading:log`
  row, as built). The gate A decisions are already recorded there.
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 9.6 (accepted, U4).
- `docs/steps/device-checks.md`: the row of § 8 *On a real device*.

## 4. Data model (migration v32)

```sql
CREATE TABLE IF NOT EXISTS meter_readings (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id   INT NOT NULL,
    meter_type_id  INT NOT NULL,
    value          DECIMAL(14,3) NOT NULL,
    taken_at       DATETIME NOT NULL,          -- IST, to the minute, as ticket event times
    is_reset       TINYINT(1) NOT NULL DEFAULT 0,
    limit_state    ENUM('low','high','not_ok') NULL,  -- a gauge outside its limits, or a Yes / No answer other than the expected one (U3), when saved
    source         ENUM('manual','pm','move','iiot') NOT NULL DEFAULT 'manual',
    note           VARCHAR(200) NULL,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by     VARCHAR(100) NOT NULL,
    removed_at     DATETIME NULL,
    removed_by     VARCHAR(100) NULL,
    CONSTRAINT fk_meter_readings_node FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_meter_readings_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    INDEX ix_meter_readings_meter_time (equipment_id, meter_type_id, taken_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- No unique key on time: a removed reading may share its minute with its
  replacement. Two active readings at one minute are refused in code (§ 5.2).
- `limit_state` is stored, not computed: a later limit change must not re-judge
  old readings.
- A Yes / No reading stores `value` 1 for Yes and 0 for No (U3), so one value
  column serves every kind; the API reads and writes the words `"yes"` /
  `"no"` and never shows the numbers. Its `limit_state` is `not_ok` or NULL.
- No `_PRECONDITIONS` entry: a new table.
- Rollback: the previous release ignores the table.

## 5. Rules

### 5.1 Validation (pure)

| Input | Result |
|---|---|
| `value` missing, empty | 400 "Enter the reading" (`value`) |
| `value` a bool, a float, or a string that is not a decimal number | 400 "Enter a number with up to 1 decimal" / "… up to 2 decimals" / "… up to 3 decimals"; 0 decimals → "Enter a whole number" (`value`; S038's `parse_number` messages, BS1-01) |
| more decimals than the meter type's | the same message: "Enter a number with up to N decimal(s)" / "Enter a whole number" (BR1-11, BS1-01) |
| beyond ±99,999,999,999.999 | 400 "Enter a smaller number" (`value`) |
| a counter below 0 | 400 "A counter cannot be below zero" (`value`) |
| an amount below 0 (U3) | 400 "An amount cannot be below zero" (`value`) |
| a Yes / No meter's `value` not `"yes"` / `"no"` (U3) | 400 "Pick Yes or No" (`value`) |
| `is_reset` on a gauge, an amount or a Yes / No meter | 400 "Only a counter can be reset" (`is_reset`) |
| `is_reset` not a bool | 400 "Meter reset must be true or false" (`is_reset`) |
| `taken_at` absent | now (IST, to the minute) |
| `taken_at` not `YYYY-MM-DDTHH:MM` | 400 `EVENT_TIME_FORMAT` (`taken_at`), via `parse_event_time` |
| `taken_at` more than 5 minutes ahead (`FUTURE_SKEW`) | 400 "That time is in the future" (`taken_at`) |
| `taken_at` more than 7 days back, for every role (decision 8) | 400 "When was it read? Up to 7 days back" (`taken_at`) |
| `note` over 200 characters | 400 "Note must be at most 200 characters" (`note`); trimmed; empty → NULL |
| `meter_type_id` missing, not an id | 400 "Pick a meter" (`meter_type_id`) |
| Numbers | accepted as a decimal string or an integer; parsed by S038's `meters_core.parse_number(raw, decimals)` (today `_parse_limit`, made public in this step; `validate_limits` keeps using it), never `float`; returned as strings (`format_number`) (BS1-01) |

### 5.2 Checks against the database

1. The meter is **in force** on the node now (S038 `effective_meters`): else 409
   "This machine does not have this meter. Reload the page." (`meter_type_id`).
2. The node is not scrapped: else 409 `SCRAPPED_MESSAGE` (in `equipment.py`
   since S038).
3. **No active reading of this meter at the same minute:** 409 "A reading at
   this time exists. Pick another time, or remove that reading first."
   (`taken_at`).
4. **Counter order** (counters only; an amount has none, U3), against the nearest active readings before and after
   `taken_at` (`counter_error`, pure):
   - not a reset, and lower than the one before → 400 "Lower than the reading
     of 23-10-2026 18:00 (12,345.6 h). Check the value, or tick Meter reset if
     the meter was reset." (`value`), with `code: "counter_lower"` (BR2-02);
   - higher than the one after, unless that one is a reset → 400 "Higher than
     the later reading of 24-10-2026 08:00 (12,350.0 h). Check the value and the
     time." (`value`);
   - a reset **higher** than the one before → 400 "A reset reads lower than
     the reading before it. Untick Meter reset." (`is_reset`). A reset equal
     to the one before passes: a replaced meter that reads 0 after a reading
     of 0 (BR2-13);
   - a reset with no earlier reading passes;
   - equal values pass (a machine that did not run).
5. **Gauge limits**: the limits in force (S038 § 5.2) give `limit_state`; a
   counter or an amount stores NULL (U3). **A Yes / No meter**: the type's
   expected answer gives `not_ok` when the answer differs, else NULL
   (`answer_state(answer, expected)`, pure; U3).
6. **Remove**: the reading is active, and the actor holds `equipment:edit` at
   the node's site (the lock key, § 5.3): else 403 from `require_perm_at`,
   "You can't do this at <site>", as every site-scoped write (BR3-01; U3). An
   already removed reading → 409 "This reading was removed". A reset reading
   with an active later reading → 409 (§ 1.4). A reading on a scrapped node
   → 409 `SCRAPPED_MESSAGE`, decided from the locked node row, as every other
   write on a scrapped node (BR3-09). The 403 is the backend's guard; nobody
   sees it in the normal flow, because the screen hides *Remove* where
   `can_remove` is false.

### 5.3 Locks

- **Log a reading:** (1) the node row `FOR UPDATE` (`load_node_for_user`,
  `for_update`, key `reading:log` at the node's site) is the transaction's
  **first statement** → the meter's link rows, the meter type, the neighbour
  readings and the same-minute row are all read **plainly** → insert
  (BR1-01). Every reading write of a node waits on (1), so two writers on one
  node serialise. The snapshot is taken by the first plain read, after the
  lock was granted (the rule `equipment.py` already states for
  `_check_no_open_tickets`), so the second writer sees the first one's row.
  No locking range read: a `LOCK IN SHARE MODE` range on
  `ix_meter_readings_meter_time` would take gap locks, and two inserts on
  adjacent (node, meter) keys could then deadlock (1213).
- **Remove a reading:** (1) the node row (`load_node_for_user`, `for_update`,
  key **`equipment:edit`** at the node's site: 403 for anyone else,
  `load_node_for_user`'s `require_perm_at`; U3, which replaces BR2-01's `equipment:read` key, needed
  only while the author could remove) → the reading row `FOR UPDATE` → the
  later-reading check for a reset (plain, after (1)) → `may_remove(reading,
  can_edit=True)` → update. `reading:log` is not the key: IT admin lacks it and
  may remove.
- The insert takes shared locks on `equipment` (held already) and `meter_types`
  through its FKs. A meter type update (S038) holds its row and then counts
  links, not readings, so it never waits on a reading; a reading insert's FK lock
  waits for that update to commit. No cycle.
- Shared with tickets: a ticket raise also takes (1); both are short.
- The `meters.py` bullet of `equipment.py`'s LOCK ORDER docstring, and the
  *Locks* paragraph of `meters.py`'s own docstring, gain: "a reading write:
  (1), then plain reads; the node lock is the first statement" (BS1-06).

### 5.4 Reads

- A node's readings (last per meter, history) need `equipment:read` at the
  node's site, so an engineer and a storekeeper see them too.
- Removed readings are left out of every read and every rule, except the
  history dialog's *Show removed* switch for `equipment:edit` holders (as
  removed documents, S008). (Assumption; § 9.5.)
- `can_remove` per reading in the history GET, from `may_remove` and the
  reset rule, computed in the shell (BR1-04). "Has an active later reading"
  is true for every active reading but the newest, so one query for the
  meter's newest active id serves the whole page (BR2-11).

### 5.5 The database down and a lost network

Two failures, one true wording (BR1-05):
- a 503 (`DBUnavailable`: the server answered, its database did not), and
- a failed fetch (the phone has no network; `api.js`'s fallback gives `HTTP …` or the
  status text).

*Log reading* keeps the typed values on either failure and shows "Not saved.
Try again in a minute." in the dialog. The load failures follow the page's
built pattern (BS1-02): S038's card reads "Meters could not be loaded:
<message>" (`MetersCard.vue`, as the page's "Tickets could not be loaded:
…") and is not changed; the *History* dialog reads "Readings could not be
loaded: <message>" (the API's error text, or `api.js`'s `HTTP …`).

## 6. API

| Method | Path | Key | Body / query | Response |
|---|---|---|---|---|
| GET | `/api/equipment/<id>/readings?meter_type_id=&page=1&per_page=30&include_removed=0` | `equipment:read` at site; `include_removed=1` only for `equipment:edit` holders (else ignored) | — | `{items: [{id, value, taken_at, is_reset, limit_state, note, created_by, created_at, can_remove, removed_at?, removed_by?}], total, page, per_page}` (BR2-03: the house shape, `int_arg` and the bounds of `api_common.py:128–135`, as `tickets.py:606`; BR2-05). Without `meter_type_id`: 400 "Pick a meter" (BR2-06) |
| POST | `/api/equipment/<id>/readings` | `reading:log` at site | `meter_type_id, value, taken_at?, is_reset?, note?`; `value` is `"yes"` / `"no"` for a Yes / No meter (U3) | 201, the reading with `limit_state` |
| DELETE | `/api/equipment/<id>/readings/<reading_id>` | `equipment:edit` at site, the lock key (U3) | — | 204, as `documents.py:432` (BR1-12, BR2-07) |

History is ordered `taken_at DESC, id DESC`; *Show more* asks the next page.
S038's `GET /api/equipment/<id>/meters` gains `last` per meter:
`{value, taken_at, limit_state}`, or `null` before any reading (BR2-05).

## 7. Design decisions

1. **Per-equipment entry first; the sheet in S040** (U2, BR1-07). The rules and
   locks are one review, the 40-input phone page another; the sheet also gains
   from a first week of the dialog on the floor. Rejected: one step (a sheet
   layout finding would hold up the rules).
2. **Counter order checked against both neighbours.** A back-dated reading must
   fit between the readings around it. Rejected: checking only the latest (a
   back-dated typo would pass).
3. **An out-of-limit gauge is saved and marked.** Rejected: refusing it (the
   measurement is the evidence).
4. **`limit_state` stored at saving**, for gauges and Yes / No meters alike
   (`not_ok`, U3). Rejected: a separate column for Yes / No (two places to
   look for "not OK").
5. **Remove, not edit.** A correction is "remove and enter again", so history
   shows both. Rejected: editing in place (a silent change of evidence).
6. **The node row as the lock, plain reads after it** (BR1-01). Inherited
   meters have no row of their own (S038 decision 1); the node row is the one
   row every reading of the node shares. Rejected: a `GET_LOCK` per meter
   (server-wide names, CLAUDE.md), and locking range reads (gap-lock
   deadlocks, nothing gained).
7. **`reading:log` held by the operator and up, not by IT admin** (U2; Plan.MD
   § 3).
8. **Time taken to the minute, a fixed 7 days back, for everyone** (U2). The
   user chose it knowing S028's `backdate_days`, which gives everyone 3 years
   until 30-11-2026 (`BACKLOG_UNTIL`) and admin always. Rejected: following
   `backdate_days` (it would let the notebook backlog be typed in until
   30-11-2026). A **departure from S028** for readings only; tickets keep
   S028's window. Consequence: old notebook pages cannot be loaded.
9. **Offset paging for history** (BR1-03), in the house shape `page` /
   `per_page` (BR2-03). A meter has a few hundred readings a
   year. Rejected: an id cursor (wrong with back-dated readings) and a
   composite cursor (more code, no second user).
10. **A reset with later readings cannot be removed** (BR1-04). Rejected:
    allowing it and never re-checking the chain (a later back-dated reading
    could then never fit).
11. **Yes / No: pick, then *Save*** (U3; the orchestrator's answer to BR3-02,
    approved with the brief, U4). Two large toggles, then the dialog's normal
    *Save*, as on the S040 sheet. A note typed after the answer is kept, and a
    mis-tap is corrected before it is saved: once saved, only an engineer can
    remove a reading (U3). `FormModal` needs no change. Rejected: one tap that
    saves (it needs a `withSave` prop on the shared `FormModal`, loses a note
    typed after the tap, and turns a mis-tap into a reading only an engineer
    can take back); a select (small on a phone).

## 8. Tests and acceptance

### Backend (pytest)

- `test_meters_core.py`: every row of § 5.1; `reading_time_error` at 7 days
  exactly (allowed) and one minute more, and 5 minutes ahead; `counter_error`
  for before only, after only, both, equal values, reset with and without a
  later reading, a later reset, a reset with no earlier reading (BR1-18);
  `limit_state` with min only, max only, both, none, equal to a limit (inside);
  `may_remove` for an active and a removed reading (U3: no author rule);
  `reset_removal_error` with and without a later active reading; an amount:
  below zero refused, any order accepted, `limit_state` NULL, a reset refused
  (U3); `answer_state` for Yes and No against each expected answer; a Yes / No
  `value` of `"maybe"`, `1`, `true` refused (U3); `validate_reading` returns
  `Decimal(1)` / `Decimal(0)` for `"yes"` / `"no"`, and a number rule never
  fires on a Yes / No meter (BR3-04, BR3-05).
- `test_readings_api.py`: log as operator at its unit (201); at another site
  (403); storekeeper (403); IT admin (403); unknown node / outside the units
  (404); a meter not on the node (409); scrapped (409); same minute (409);
  counter lower (400, `code: "counter_lower"`) and with reset (201); a reset
  equal to the reading before (201, BR2-13); a back-dated reading between two;
  8 days back as admin (400, decision 8); gauge high → `limit_state: "high"`;
  history paging with a back-dated reading on the page boundary (it shows
  once, in time order); `can_remove` per role; remove by engineer, by manager
  and by IT admin (BR1-13); by the operator who logged it and by the supervisor
  (403, U3); twice (409); remove on a scrapped node (409, BR3-09); an amount
  lower than the reading before (201, U3); a Yes / No meter (BR3-04): `"no"`
  on an expected-*Yes* type → 201, `value: "no"`, `limit_state: "not_ok"`;
  `"yes"` → `limit_state: null`; `is_reset` on it → 400; `"1"` → 400 "Pick Yes
  or No"; the history and `last` carry the word; DELETE answers 204; the GET without
  `meter_type_id` (400); `include_removed=1` by an operator is ignored; a reset with
  a later reading (409); the removed reading no longer blocks a lower counter
  value; two concurrent counter inserts (two connections, the second waits on
  the node lock, then sees the first; the threading pattern of
  `test_ticket_work_api.py:814`).
- `test_rbac.py`: `reading:log` per role; in `SITE_SCOPED`.
- `test_migration_v32.py`: from v31 (S043 sits between), on the pattern of
  `test_migration_v31.py`; a re-run (BS1-08).

### Automated (e2e)

Set-up (BR1-09, BR2-04): the three projects share one database, so no test
reads or writes a seed node. `readings.spec.js`'s `beforeAll` creates its
**own machine per project** at **SMTW.MCC2** (the unit `e2e_operator` holds,
`seed_e2e.py:38`), through S038's `meterMachine(testInfo, tag, { unit:
"SMTW.MCC2", ownMeters })`, moved to `e2e/support/meters.js` (BS1-03). It makes
a model of its own, so no seed model is touched (`SMTW-HYP-01` stays free, as
the comments in `equipment.spec.js` and `masters.spec.js` keep it). The own
meters: a counter (Run hours), a gauge with a max (Oil temperature, up to
60 °C), an amount (Shift production) and a Yes / No meter of a type the
`beforeAll` first creates by S037's API (named with the project, expected
*Yes*; no Yes / No seed, S037 decision 8; U3), added by meter type name
through S038's API (`apiAs("engineer")`, the `screens.spec.js` pattern). Every S039
test, and `equipment.spec.js`'s last-reading check, uses that machine. No
change to `seed_e2e.py`.

- `readings.spec.js`:
  - **Important.** "S039: an operator logs a reading from the equipment page"
    (dialog fits a phone);
  - **Important.** "S039: a counter lower than the last reading is refused
    beside the value";
  - "S039: a gauge above its limit is saved and shows High";
  - "S039: an engineer removes a wrong reading and the operator enters it
    again" (U3);
  - "S039: the operator who logged a reading sees no Remove on it" (U3);
  - "S039: a shift's production lower than the last one is saved" (U3);
  - **Important.** "S039: a No on a Yes / No meter, then Save, shows Not OK"
    (the two buttons at least 48 px high and inside the viewport on Pixel 7
    and iPhone 14; *Save* disabled until an answer is picked; a note typed
    after the answer is saved with it; U3, decision 11).
- `equipment.spec.js`: the *Meters* card shows the last reading, and its tap
  opens *History*.

### On a real device

- **Important** — the decimal keypad on an Android phone and an iPhone in the
  *Log reading* dialog (`inputmode="decimal"`), and that the keyboard does not
  hide the dialog's message (S026); the *Yes* / *No* buttons are easy to hit
  with a thumb (U3). Account: a test login with the Operator
  role at SMTW; company Wi-Fi; production on the TEST machine, or the dev
  server. Row for `docs/steps/device-checks.md`. (S040 adds the same check for
  the sheet.)

### Acceptance

An operator logs the day's run hours and oil temperature of a press from its
page; a typo on the counter is refused with a plain message; a hot day's oil
temperature shows *High* on the press page; a shift's production is saved
whatever the last one was; a *No* on *Oil level above min*, then *Save*, shows
*Not OK* (BR3-10); an engineer removes a wrong reading and the operator enters
it again.

## 9. Open questions and assumptions

1. **Size**: settled. The sheet is S040 (U2). This step is about 16 files.
2. **Who logs readings**: settled (U2): operator and up, not IT admin.
3. **The genset round across sites**: moved to S040 § 9.
4. **7 days back**: settled (U2, decision 8): fixed, for everyone.
5. **Remove rights**: settled (U3): only `equipment:edit` holders (engineer,
   manager, IT admin); a removed reading visible to them only.
6. **A `/smtw-review` point**: settled (U4, D9): "every counter reading path
   takes the node lock first and checks both neighbours", added by the coder
   in the docs pass.
7. **Number format**: settled (U4, D8): Indian grouping (12,34,567.8),
   `toLocaleString("en-IN")`.
8. **Standards numbers** (to verify): EN 13306 terms, ISO 14224 operating time,
   ISO 50001 § 6.6, ISO 9001 § 7.5.3, ISO 22400-2 production quantity.
9. **Shifts** (assumption, U3): no shift master (A / B / C, shift times) in
   this step. An amount reading's *Time taken* places it; a report by shift
   comes with the shift definitions, later.

## 10. Amendments

None.

## Review log

### U1 — user answers, 24-10-2026 (before drafting)

- Meters defined on the model, every equipment of the model has them; an
  equipment may add its own; readings per equipment.
- Gauge limits on the model's meter, overridable per equipment.
- S039 builds per-equipment entry and an end-of-day sheet (changed by U2).

### U2 — user answers, 24-10-2026 (after round 1)

- Split: the end-of-day sheet is its own step, S040 (BR1-07 option a).
- Operator and up log readings, not IT admin.
- Back-dating: a fixed 7 days, for everyone, admin included. Asked with
  S028's `backdate_days` (3 years for everyone until 30-11-2026) as the other
  option (BR1-02); the user chose 7 days.
- Every level of the tree may carry meters (S038).

### U3 — user comments on the review page, 24-10-2026

- Removing a reading: only `equipment:edit` holders (engineer, manager, IT
  admin). The author's 24-hour right is dropped (§ 1.4, § 5.2.6, § 5.3, § 6,
  § 8). This replaces the BR2-01 answer's lock key (`equipment:read`), which
  existed only for the author's right.
- A third meter kind, `amount` (*Amount per period*, e.g. *Shift production*;
  S037): 0 or more, no order check, no reset, no `limit_state` (§ 1.2, § 5.1,
  § 5.2).
- The end-of-day sheet (S040) covers one site, not one unit.
- A fourth kind, `yes_no` (S037): Yes / No readings, *Not OK* when not the
  expected answer (`limit_state` `not_ok`) (§ 1.2, § 1.3, § 4, § 5.1, § 5.2,
  § 6, decisions 4 and 11, § 8). The entry was first written as two buttons
  that save at one tap; changed to pick, then *Save*, in the answer to BR3-02
  (decision 11).

### U4 — approval, 24-10-2026

- "I have reviewed the brief. Except what I changed above, it all is
  accepted. Implement." Approved by KLA.
- D8: Indian grouping (§ 9.7 settled). D9: the `/smtw-review` point (§ 9.6
  settled). D11: the words. D12: the clause numbers stay "to verify". D7 is
  replaced by U3: removal by `equipment:edit` only.

### Round 1 — `2-brief-review-r1.md` (Fable), answered 24-10-2026

3 major, 6 minor, 10 nits.

| Finding | Answer |
|---|---|
| BR1-01 major — locking neighbour reads: wrong syntax, gap-lock deadlock, not needed | Accepted (a): plain reads after (1), the node lock first; § 5.3, decision 6 |
| BR1-02 major — "the ticket rule" is not 7 days since S028 | Put to the user (U2): a fixed 7 days, for everyone, as a stated departure from S028; § 5.1, decision 8; § 9.4's wrong claim removed |
| BR1-03 major — `before_id` paging skips back-dated readings | Accepted (a): `limit` / `offset`, order `taken_at DESC, id DESC`; § 6, decision 9 |
| BR1-04 minor — removing a reset; the *Remove* button | Accepted: a reset with later readings cannot be removed (409); `can_remove` in the GET; § 1.4, § 5.2.6, decision 10 |
| BR1-05 minor — DB-down wording; the lost network; load failures | Accepted: "Not saved. Try again in a minute." for both; the load texts; § 5.5. The sheet's parts go to S040 |
| BR1-06 minor — the sheet on a phone | Moved to S040 with the sheet (Undo, the hidden *Reset* tick, no unit picker for one unit, Save disabled while saving) |
| BR1-07 minor — size | Accepted (a), U2: S039 and S040 |
| BR1-08 minor — ISO 9001 § 7.1.5 misattributed; A.8.15 missing | Accepted: § 7.5.3 for the record, § 7.1.5 explained and pointed to *Calibration*, ISO 27001 A.8.15; § 2 |
| BR1-09 minor — e2e meters set-up | Accepted: `beforeAll` through S038's API; § 8 |
| BR1-10…BR1-19 nits | Accepted, except where moved. BR1-10: import direction; the 7-day message is meters_core's own. BR1-11: "1 decimal" / "N decimals". BR1-12: `DELETE …/readings/<id>`. BR1-13: IT admin removes, tested. BR1-14, BR1-15, BR1-17: moved to S040 (the bottom bar, the nav unit test, the `localStorage` key). BR1-16: the last-reading line opens *History*. BR1-18: the two core cases. BR1-19: "Tick this only when …", one phrase (S040 uses it too). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 4 minor, 9 nits. Review loop complete.

| Finding | Answer |
|---|---|
| BR2-01 minor — the remove route's lock key | Accepted (a): lock with `equipment:read` at the site, then `may_remove` with `can_edit = has_perm_at("equipment:edit", site)`; § 5.3, § 6. Superseded by U3: the lock key is `equipment:edit` |
| BR2-02 minor — the sheet needs a refusal code | Accepted (a): `ApiError` gains an optional `code`; the counter-lower 400 sends `code: "counter_lower"`; `api_common.py` in § 3; § 1.5, § 5.2.4, § 6, § 8. S040 reads `err.code` |
| BR2-03 minor — a second paging shape | Accepted (a): `page` / `per_page` via `int_arg`, `{items, total, page, per_page}`; § 6, decision 9 |
| BR2-04 minor — e2e on a shared seed node | Accepted (a): an own machine per project at SMTW.MCC2, through a `createEquipment` with a unit argument in `e2e/support/`; "another operator" is the supervisor; § 8 |
| From S040's review | S040 BR1-09: *Time taken* is `EventFields.vue`. S040 BR1-15: this step adds `reading:log` to `navigation.test.js`'s role lists. |
| BR2-05…BR2-13 nits | All accepted. BR2-05: history row fields, `last`'s shape, `include_removed`. BR2-06: 400 "Pick a meter" without `meter_type_id`. BR2-07: DELETE 204. BR2-08: "No readings yet". BR2-09: the *Low* message; no message inside the limits. BR2-10: "who" is the login. BR2-11: one query for `can_remove`. BR2-12: the inline [*Remove*] [*Keep*]. BR2-13: only a reset **higher** than the one before is refused. |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 4 minor, 6 nits. Re-read the U3 sections only.

| Finding | Answer |
|---|---|
| BR3-01 minor — the 403 text cannot come from the lock | Accepted (a): the 403 is `require_perm_at`'s "You can't do this at <site>"; *Remove* hidden where `can_remove` is false; § 5.2.6 |
| BR3-02 minor — the one-tap dialog keeps an unused *Save*; a note after the tap is lost | Rejected as proposed (no `withSave` prop on the shared `FormModal`); answered by the orchestrator: pick *Yes* / *No*, then the normal *Save*, as on the S040 sheet; a note is kept, a mis-tap is corrected before saving; § 1.3, § 3, decision 11, § 8 |
| BR3-03 minor — the set-up machine's model | Accepted (a): `createEquipment(name, unit, model)` with `SMTW-HYP-01`; S038 § 8 keeps its tests off it; § 3, § 8 |
| BR3-04 minor — no owner of the word ↔ 1/0 mapping; no API test | Accepted (a): `validate_reading` returns `Decimal(1)` / `Decimal(0)`; `reading_out` gives the word back; five API cases; § 3, § 8 |
| BR3-05…BR3-10 nits | All accepted. BR3-05: `validate_reading` takes the kind; the Yes / No value rule alone. BR3-06: *Not OK* badge in history; the confirm bracket from `formatReading`. BR3-07: *Yes* / *No* as answers, a stated departure. BR3-08: EN 13306 inspection in § 2. BR3-09: remove on a scrapped node → 409. BR3-10: the Yes / No case in Acceptance. |

### U5 — renumbered, 24-10-2026

- The migration is **v32**, not v31: the user put the ported properties step S043 (v31) before this one. Every v31 in this brief was renamed v32.

### Staleness s1 — `2-brief-review-s1.md` (Fable), answered 24-10-2026

0 blocker, 0 major, 4 minor, 6 nits. Reviewed against ff9ddb3 + uncommitted S037, S038, S043 (S037 and S038 now coded, snapshot `refs/steps/S038`).

| Finding | Answer |
|---|---|
| BS1-01 minor — § 5.1 duplicates S038's number parser, with other words | Accepted (a): `_parse_limit` made public as `parse_number`, reused by `validate_reading`; § 5.1 takes the built words ("Enter a number with up to N decimal(s)", "Enter a whole number", "Enter a smaller number"); § 3 |
| BS1-02 minor — the card's load text was not built as the brief says | Accepted (a): the built pattern "… could not be loaded: <message>"; the History dialog follows it; `MetersCard.vue`'s text unchanged; § 5.5 |
| BS1-03 minor — S038's `meterMachine` already does the e2e set-up | Accepted (a): moved to `e2e/support/meters.js` and exported, called with `unit: "SMTW.MCC2"`; `createEquipment` unchanged; § 3, § 8 |
| BS1-04 minor — the Meters card's place below Properties (judgement call) | Accepted (a): the order kept and recorded in § 1.3 (S040's sheet is the daily path); for the user at gate B |
| BS1-05…BS1-10 nits | All accepted. BS1-05: moved line numbers replaced by names. BS1-06: the reading line in the existing `meters.py` LOCK ORDER bullet and `meters.py`'s *Locks* paragraph; `_lock_node` gains a `key` parameter. BS1-07: three `navigation.test.js` edits. BS1-08: `test_migration_v32.py` from v31. BS1-09: `schema.md`'s planned row replaced; `schema.html` v32, 37 tables, 53 links. BS1-10: `meters.py._meters_of` named as the in-force check. |
