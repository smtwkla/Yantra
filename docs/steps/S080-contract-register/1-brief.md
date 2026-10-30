```
Step: S080 — Contract register
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: d216f48 + S079 (staleness check before coding)
Status: Approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 5 minor accepted)
From: R02.1
```

# S080 — Contract register

## 1. What will be built

R02.9 (S079) gives Yantra one list of the outside firms, `vendors`. **R02.1 is the register of
their contracts**: one record per vendor contract, with its site, vendor, type, period, what is
covered, the PM visits agreed, the response time, the call-out number, the *Only the vendor may
repair* tick and a cost note, listed in **Masters › Contracts** with a status computed from the
dates. It answers KLA's "from, to, … what is covered, number of pm visits agreed, cost" (R02 § The
feature); the equipment covered and the price per machine are R02.2's (D8).

1. **The record** (`contracts`, migration **v43**, § 4): one site (Q1.5 a); a `vendors` row (from
   S079, D11), active for a new contract or a vendor change, kept when it later becomes inactive;
   a type from Warranty, AMC, CMC, On call (Q1.1 a); title, vendor's contract number, From, To.
2. **What is covered** (Q1.4 b): ticks *Labour*, *Spare parts*, *Consumables*, *Breakdown calls*
   (with calls per year, empty = no limit), and free text *Covered* / *Not covered*; **PM visits
   per year** (0–52, the field PM reads later, D2); **Response time** in hours; the tick **Only the
   vendor may repair** (D9; the machine card's warning is R02.2's); notes.
3. **Call-out number** (D10), read and written only with `contract:read` (engineers and managers of
   the site); **Cost note** (D5, D8), only with `contract:read_senior` (managers of the site). Admin
   has both by the bypass. An editor without the key never sees the field, and a save by them
   leaves it as it was (§ 5.4).
4. **Status from the dates, never stored** (§ 5.3): *Starts on 01-05-2027*, *In force*, *Ends in 19
   days*, *Ended*. Never deleted; a contract entered by mistake is set **inactive**.
5. **Four new keys**, all site-scoped (§ 5.5): `contract:read_basic`, `contract:read`,
   `contract:read_senior`, `contract:edit`.
6. **Masters › Contracts** (Q1.8 a): a table with filters (site, type, status, vendor, *Show
   inactive*), *Add contract* and *Edit* in one dialog (`FormModal.vue`, `useMasterForm`).
7. **The column `renewal_of_id`** (*Renewal of*): created here, always NULL; R02.4 fills it without
   a migration.

**After S080:** the manager sees every contract at the site, its vendor, its type and its end date;
the engineer adds a contract in one dialog.

### Out of scope

- The machines covered, the price per machine and its total, the contract page, the *Under
  contract* card, the equipment-list filter (R02.2). So **no cost column** in the list (§ 9, Q1).
- Documents on the contract (R02.3); *Renew* (R02.4); reminders (R02.5); breakdown calls (R02.6);
  PM visits against the contract (R02.7); the vendor report (R02.8).
- A read-only view of one contract's terms for a reader who may not edit it: the list row only
  until R02.2's contract page (§ 9, assumption A2).
- A history of earlier values of a contract (only the last change's who and when, § 2).
- Contract counts on the *Vendors* tab (R02.9 "leaves for later").

## 2. Standards and practice

- **ISO 55001 § 8.3, outsourcing** (Plan.MD § 2 cites it; the number in the 2024 edition *to
  verify*). In plain words: work given to an outside firm stays the plant's responsibility; the
  plant decides what is outsourced, how it is controlled, and keeps the evidence. S080 records, per
  contract, which firm, for which site, under which terms and until when.
- **ISO 9001:2015 § 8.4, control of externally provided processes and services** (sub-clause
  8.4.3 *to verify*). In plain words: choose outside providers on criteria, check their work, and
  state in the agreement what is required. The record holds what was agreed: coverage, PM visits,
  response time, breakdown calls. Checking the vendor's performance is R02.8.
- **ISO 9001:2015 § 7.5, documented information.** In plain words: keep the records that show what
  was agreed and who changed them. A contract is never deleted (inactive instead), and each row
  keeps who created it and when, and who changed it last and when. **Departure (recorded):** no
  history of earlier values, as every master (`manufacturers`, `equipment_models`); the signed
  contract itself is R02.3's document.
- **EN 13269, guideline on the preparation of maintenance contracts** (edition and content *to
  verify*). In plain words: a maintenance contract states its scope, the equipment, the services,
  response times and what is excluded. The fields follow that list: coverage ticks and text,
  *Not covered*, response time, PM visits; the equipment is R02.2.
- **ISO/IEC 27001:2022 A.5.15, access control** and **A.8.3, information access restriction**
  (A.8.3 *to verify*). In plain words: each person sees only what the work needs, and the system,
  not the screen, enforces it. Three read levels (CLAUDE-COMMON § RBAC Pattern): the terms for
  everyone at the site, the call-out number for engineers and managers, the cost note for
  managers. The API leaves a field out of the answer for a reader without its key and ignores it
  in a write by an editor without it (§ 5.4).

## 3. Where

S079 is coded before S080 and changes `backend/local_db.py`, `backend/masters.py`,
`backend/masters_core.py`, `backend/tests/conftest.py`, `frontend/src/views/MastersView.vue` and
`frontend/src/stores/masters.js`. In those files this brief anchors by name (function, constant),
not by line (README § Anchors by name). Names marked **(from S079)** do not exist at the baseline:
`vendors`, `people.vendor_id`, the route `GET /api/masters/vendors` (`include_inactive=1` for
all), the store's `vendors` and `ensureVendors` in `frontend/src/stores/masters.js`, the phone
factory `phone_parser(label)` (`_parse_phone = phone_parser("Phone")`) with `PHONE_MAX`, `PHONE_DIGITS_MIN`, `PHONE_DIGITS_MAX` in
`backend/masters_core.py`, and the fixture `make_vendor` in `backend/tests/conftest.py`
(`docs/steps/S079-vendor-master/1-brief.md` § 3).

### Backend

- `backend/local_db.py`: migration **v43** at the end of `_MIGRATIONS` (§ 4.1), after S079's v42.
  No `_PRECONDITIONS` entry (§ 4.1).
- `backend/contracts_core.py` (new, pure): `CONTRACT_TYPES`, the bounds and messages,
  `validate_contract(body, creating)`, `period_error(from_date, to_date)`,
  `breakdown_calls_error(...)`, `contract_status(from_date, to_date, today)`,
  `status_bounds(status, today)`, `ENDING_SOON_DAYS`, `STATUS_FILTERS` (§ 5). From
  `backend/masters_core.py` it imports only public names: `optional_text_parser`, S079's
  `phone_parser`, and the four new aliases `collapsed`, `flag_parser`, `validate_fields`,
  `id_parser` (D9). It holds its own 7-line `_iso_date(value)`, a stated copy of
  `improvements_core._iso_date` (`backend/improvements_core.py:394`): two cores do not import each
  other's private helpers, and the date bounds of § 5.1 are added on top (D9).
- `backend/contracts.py` (new): the blueprint `contracts_bp` (§ 6), the locks (§ 5.6) with a LOCK
  ORDER note, the answer builder `_contract_out` that leaves out the gated fields (§ 5.4), the
  site helper `_sites_holding(cur, key)` (§ 5.5). Imports: `has_perm_at`, `require_perm`,
  `require_perm_at` (`backend/auth_utils.py`); `clean_body`, `actor`, `ApiError`, `enum_arg`,
  `int_arg`, `MAX_PER_PAGE` (`backend/api_common.py`); `fetch_one`, `insert_row`, `update_row`,
  `rows_to_list`, `transaction`, `get_db` (`backend/db_helpers.py`); `IST` (`backend/equipment.py`).
- `backend/app.py`: registers `contracts_bp` at `/api/contracts`, beside `procedures_bp`
  (`app.register_blueprint(procedures_bp, url_prefix="/api/procedures")`, `backend/app.py:196`).
- `backend/config_rbac.py`: the four keys after `procedure:edit` (`backend/config_rbac.py:150`),
  with their comment; all four in `SITE_SCOPED` (§ 5.5).
- `backend/equipment.py`: docstring only. The global LOCK ORDER note gains a `contracts.py` bullet,
  as the `procedures.py` and `meters.py` bullets (§ 5.6).
- `backend/masters_core.py`: four public aliases with a comment (D9): `collapsed = _collapsed`,
  `flag_parser = _flag_parser`, `validate_fields = _validate`, `id_parser = _parse_id`. S079's
  `phone_parser` is used as it is (D11); nothing of S079's code is renamed.

### Tests

- `backend/tests/test_migration_v43.py` (new), on the pattern of `test_migration_v41.py`
  (`V41 = … range(20, 42)`; v43 slices `range(20, 44)`) (§ 8.1).
- `backend/tests/test_contracts_core.py` (new) (§ 8.2).
- `backend/tests/test_contracts_api.py` (new) (§ 8.2).
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and a new `test_contract_keys` (§ 8.3).
- `backend/tests/conftest.py`: `contracts` joins `_TABLES`, first in the tuple (the fixture deletes
  with `FOREIGN_KEY_CHECKS = 0`; the order is for reading only). The tests use S079's `make_vendor`
  as it is (an inactive vendor: a `PUT {active: false}` as the engineer).

### Frontend

- `frontend/src/views/masters/ContractsPanel.vue` (new): the table, the filters, the dialog
  (§ 5.7).
- `frontend/src/views/MastersView.vue`: a section `{ key: "contracts", label: "Contracts", perm:
  "contract:read_basic", icon: "fa-solid fa-file-signature" }`, **last**, after *Team* (mock-up
  01), and `contracts: ContractsPanel` in `panels`.
- `frontend/src/utils/contractLabels.js` (new, pure): `CONTRACT_TYPES` (value, label, help),
  `contractTypeLabel`, `statusBadgeClass(kind)`, `contractBody(form, site)` (the dialog's
  `toBody`, § 5.7).
- `frontend/tests/contractLabels.test.js` (new).
- `frontend/e2e/contracts.spec.js` (new; § 8.4). Its set-up helpers live in the spec file, not in
  `frontend/e2e/support/`, so the shared support files stay unchanged (settings: *Shared code*).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: a `contracts` line, area *Equipment* (the area note gains "and vendor
  contracts (S080)"); then `tooling\schema-docs.bat write`, read `git diff docs/schema/`, and
  `check` exits 0. `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 3: the key table gains the four rows, and one paragraph (as for
  `procedure:edit`, `docs/Plan.MD:218`): who holds each key, site-scoped, the field rule of § 5.4.
  § 2 item 9 already says the rest (`docs/Plan.MD:48`); no change there unless the coding departs.
- `.claude/CLAUDE.md`: § Step workflow, *Self-check, repo items* (2): the LOCK ORDER note of
  `contracts.py` joins those of `tickets.py`, `masters.py`, `improvements.py` and `procedures.py`;
  § SMTW-Review gains the point of § 8.6.
- `docs/Keycloak.md`: no change (no role changes).

**File count:** 17 code and test files (7 code: `local_db.py`, `contracts_core.py`, `contracts.py`,
`app.py`, `config_rbac.py`, `equipment.py`, `masters_core.py`; 5 backend tests; 5 frontend:
`ContractsPanel.vue`, `MastersView.vue`, `contractLabels.js`, its test, `contracts.spec.js`), 5 docs.
One concern. No split (§ 9).

## 4. Data model

### 4.1 Migration v43

```sql
-- Vendor contracts (S080, R02.1): one row per contract, at one site (Q1.5 a), with a vendor
-- from the vendors master (S079, v42).  Status is computed from the dates, never stored.  Never
-- deleted: one entered by mistake is set inactive (ISO 9001 § 7.5).  The price is per machine and
-- lands with R02.2 (D8); this table holds only the cost note.  renewal_of_id is filled by R02.4.
CREATE TABLE IF NOT EXISTS contracts (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    site_id                   INT NOT NULL,
    vendor_id                 INT NOT NULL,
    contract_type             ENUM('warranty', 'amc', 'cmc', 'on_call') NOT NULL,
    title                     VARCHAR(100) NOT NULL,
    contract_number           VARCHAR(60) NULL,
    from_date                 DATE NOT NULL,
    to_date                   DATE NOT NULL,
    covers_labour             TINYINT(1) NOT NULL DEFAULT 0,
    covers_parts              TINYINT(1) NOT NULL DEFAULT 0,
    covers_consumables        TINYINT(1) NOT NULL DEFAULT 0,
    covers_breakdown_calls    TINYINT(1) NOT NULL DEFAULT 0,
    breakdown_calls_per_year  SMALLINT NULL,
    covered_text              VARCHAR(1000) NULL,
    not_covered_text          VARCHAR(1000) NULL,
    pm_visits_per_year        TINYINT NULL,
    response_hours            SMALLINT NULL,
    only_vendor_repairs       TINYINT(1) NOT NULL DEFAULT 0,
    callout_number            VARCHAR(20) NULL,
    cost_note                 VARCHAR(255) NULL,
    notes                     VARCHAR(1000) NULL,
    renewal_of_id             INT NULL,
    active                    TINYINT(1) NOT NULL DEFAULT 1,
    created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by                VARCHAR(100) NOT NULL,
    updated_at                DATETIME NULL,
    updated_by                VARCHAR(100) NULL,
    KEY ix_contracts_site (site_id, active, to_date),
    KEY ix_contracts_vendor (vendor_id),
    KEY ix_contracts_renewal_of (renewal_of_id),
    CONSTRAINT fk_contracts_site FOREIGN KEY (site_id) REFERENCES sites (id),
    CONSTRAINT fk_contracts_vendor FOREIGN KEY (vendor_id) REFERENCES vendors (id),
    CONSTRAINT fk_contracts_renewal_of FOREIGN KEY (renewal_of_id) REFERENCES contracts (id),
    CONSTRAINT chk_contracts_period CHECK (to_date >= from_date),
    CONSTRAINT chk_contracts_pm_visits CHECK (pm_visits_per_year IS NULL OR pm_visits_per_year BETWEEN 0 AND 52),
    CONSTRAINT chk_contracts_response CHECK (response_hours IS NULL OR response_hours BETWEEN 1 AND 720),
    CONSTRAINT chk_contracts_breakdown_calls CHECK (breakdown_calls_per_year IS NULL
        OR (covers_breakdown_calls = 1 AND breakdown_calls_per_year BETWEEN 1 AND 365))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **Foreign keys:** no `ON DELETE` clause, so `RESTRICT`, as every foreign key in the schema; no
  site, vendor or contract row is deleted (sites and vendors are set inactive).
- **No unique key.** The vendor's contract number repeats on purpose: a mixed quote is entered as
  two contracts with the same vendor and number (D7, Fuji `AMC14082369550-R`). Titles may repeat
  (two sites: "Toyota MH — SMTW", "Toyota MH — SSVT", Q1.5). `renewal_of_id` is not unique here:
  whether a contract may have two renewals is R02.4's decision (§ 9, A4).
- **`ix_contracts_site`** serves the list (site, active, ordered by `to_date`); `ix_contracts_vendor`
  and `ix_contracts_renewal_of` back their foreign keys (and the vendor filter).
- **No amount column** (D8): the price per machine is `contract_equipment.price` in R02.2.
- **Re-run safety:** `CREATE TABLE IF NOT EXISTS`; one statement, so v43 is never half-applied.
- **No precondition** (`_PRECONDITIONS`, `backend/local_db.py` `_PRECONDITIONS`): a new table; no
  existing row changes. The foreign key to `vendors` needs v42 (S079), which runs first in the same
  upgrade. Rollback: a release before v43 never reads `contracts`.
- **Text:** utf8mb4; MariaDB's `VARCHAR(n)` and Python's `len` both count code points, so the
  bounds agree (S075 § 4.1).

### 4.2 What is computed, never stored

- The status, its label and the number of days (§ 5.3).
- The flags `can_edit`, `can_read_callout`, `can_read_cost` per row, and the `sites` list (§ 6.2).
- The site's code and the vendor's name and active flag (joins).

## 5. Rules

### 5.1 The fields

`validate_contract(body, creating)` for `clean_body` (`backend/api_common.py:121`). On a `POST` a
required field missing is refused; on a `PUT` an absent field stays as it is. `null` is allowed only
where the table says "or `null`". Unknown fields are ignored, `renewal_of_id` included (R02.4 writes
it). The messages are scope B; the field in brackets is where the dialog shows it.

**Message style** (BR1-01): a *missing or empty* required field says what to do, as a sentence with
a period: "Enter a title.", "Choose a site." (`_choose_text`'s form). A *too long* or *wrong type*
value uses the reused masters parsers' own form, without a period: "Title must be at most 100
characters", "Notes must be text". The call-out number keeps S079's phone messages. **Missing on a
`POST`:** `validate_contract` gives each required field that is absent the value `None` before
calling `validate_fields`, whose table marks every field optional; so the field's own parser gives
its "Enter …" / "Choose …" text, never `_missing_text`'s "Title is required".

| Field | `POST` | Rule | Message (field) |
|---|---|---|---|
| `site_id` | required | `id_parser("Site")`: integer ≥ 1, not a boolean | "Choose a site." (`site_id`) |
| `vendor_id` | required | integer ≥ 1, not a boolean (a parser of its own for the longer text) | "Choose a vendor. The list holds the active vendors of Masters › Vendors." (`vendor_id`) |
| `contract_type` | required | one of `warranty`, `amc`, `cmc`, `on_call` | "Choose a type." (`contract_type`) |
| `title` | required | text; `collapsed` (inner runs of spaces and line breaks become one space; trimmed); 1–100 | "Enter a title." / "Title must be at most 100 characters" / "Title must be text" (`title`) |
| `contract_number` | optional | `optional_text_parser("Contract number", 60, collapse=True)`: text or `null`; empty → `null` | "Contract number must be at most 60 characters" / "Contract number must be text" |
| `from_date`, `to_date` | required | `_iso_date`: `YYYY-MM-DD` (what `<input type="date">` sends), from 2000-01-01 to 2099-12-31 | "Enter a From date." / "Enter a To date." (each field, also for a wrong format or a date out of range) |
| `covers_labour`, `covers_parts`, `covers_consumables`, `covers_breakdown_calls`, `only_vendor_repairs` | optional, default false | `flag_parser(label)`: `true`/`false`/`1`/`0` | "<Label> must be true or false" |
| `breakdown_calls_per_year` | optional | integer 1–365 or `null` (no limit); not a boolean or a string | "Calls per year: a whole number from 1 to 365, or empty for no limit." |
| `pm_visits_per_year` | optional | integer 0–52 or `null` | "PM visits per year: a whole number from 0 to 52, or empty." |
| `response_hours` | optional | integer 1–720 or `null` | "Response time: a whole number of hours from 1 to 720, or empty." |
| `covered_text`, `not_covered_text` | optional | `optional_text_parser(label, 1000)`: text or `null`; trimmed, line breaks kept; empty → `null` | "Covered must be at most 1000 characters" / "Not covered must be …" / "… must be text" |
| `notes` | optional | as above, ≤ 1000 | "Notes must be at most 1000 characters" / "Notes must be text" |
| `callout_number` | optional | `phone_parser("Call-out number")`, S079 § 5.1's rule as revised: `null` or `""` clears it; trimmed; ≤ 20 (`PHONE_MAX`); digits, spaces, `-`, `.`, `(` `)`, a `+` only first; 6–15 digits | "Call-out number must be text" / "Call-out number must be at most 20 characters" / "Enter 6 to 15 digits. Spaces, hyphens, dots and brackets are allowed." (S079's wording) |
| `cost_note` | optional | `optional_text_parser("Cost note", 255)` | "Cost note must be at most 255 characters" / "Cost note must be text" |
| `active` | ignored on `POST` (a new contract is active) | `flag_parser("Active")` | "Active must be true or false" |

- **The period** (`period_error`, on the merged values of a `PUT`): `to_date < from_date` →
  "Enter a To date on or after the From date." (`to_date`) when `to_date` was sent, else "Enter a
  From date on or before the To date." (`from_date`). No upper bound on the length: a warranty may
  run five years.
- **Breakdown calls** (`breakdown_calls_error`, merged): a number sent (not `null`) while the merged
  tick is false → 400 "Tick Breakdown calls to enter calls per year." (`breakdown_calls_per_year`).
  The tick set to false with no number in the body clears a stored number (the shell writes
  `breakdown_calls_per_year = NULL`): the number has no meaning without the tick. The CHECK holds
  it in the database.
- **The site is fixed after create.** A `PUT` with `site_id` equal to the stored one is no change;
  a different one → 400 "A contract keeps its site. Deactivate it, then add the contract at the
  other site." (`site_id`), as `update_equipment_model` refuses a changed class
  (`backend/masters.py` `update_equipment_model`). R02.2's machines are of the contract's site, so
  a site change would leave them behind.
- **The vendor may change** (a typo of the firm), to an active vendor. `vendor_id` equal to the
  stored one is no change and is not checked, so a contract with an inactive vendor still saves
  (the dialog sends the whole form).
- **A `PUT` writes every field it was sent** and stamps `updated_at`, `updated_by` (`update_row`,
  `backend/db_helpers.py:68`), as every master; a `PUT` with nothing to write writes nothing.
- **An ended contract may be changed** (a correction). R02.4 may make a renewed one read-only.
- **The call-out number is a firm's service line.** No real number goes into the repo: tests and
  examples use `+91 00000 00000` (D10, CLAUDE-COMMON § Conventions).

### 5.2 The vendor

- On create, and on a `PUT` whose `vendor_id` differs from the stored one, the vendor row is read
  `LOCK IN SHARE MODE` (§ 5.6): missing or `active = 0` → 400 "Choose a vendor. The list holds the
  active vendors of Masters › Vendors." (`vendor_id`).
- A vendor set inactive later (S079) keeps its contracts; the list shows "Atlas Copco (inactive)".
  Deactivating a vendor is not refused by its contracts (R02.9: "a contract keeps its vendor").

### 5.3 Status from the dates (IST)

`contract_status(from_date, to_date, today)` → `{kind, label, days}`; `today` is the IST date
(`datetime.now(IST).date()`, `IST` from `backend/equipment.py:163`), passed in by the shell. The
period is inclusive: a contract is in force on its From and its To day.

| Case (first that holds) | `kind` | `label` | `days` |
|---|---|---|---|
| `from_date > today` | `upcoming` | "Starts on 01-05-2027" (DD-MM-YYYY) | `null` |
| `to_date < today` | `ended` | "Ended" | `null` |
| `to_date − today ≤ ENDING_SOON_DAYS` (60) | `ending` | "Ends today" (0), "Ends in 1 day", "Ends in 19 days" | 0–60 |
| otherwise | `in_force` | "In force" | `null` |

- `ENDING_SOON_DAYS = 60` is the first reminder of Q5.1 a (R02.5). R02.5 makes the lead days
  settings; it decides then whether the badge follows them (§ 9, A3).
- An inactive contract keeps its computed status; the list adds an *Inactive* badge.
- **The list filter** `status` (`STATUS_FILTERS`, `enum_arg`): `not_ended` (the default:
  `to_date >= today`), `in_force` (`from_date <= today <= to_date`, ending ones included),
  `ending` (`from_date <= today` and `to_date` from today to today + 60), `upcoming`
  (`from_date > today`), `ended` (`to_date < today`), `all`. `status_bounds(status, today)` gives
  the dates; the shell writes the SQL with them as parameters. Each filter matches exactly the
  rows whose `kind` it names (`in_force` also `ending`; `not_ended` all but `ended`).
- **Order:** `to_date, id` ascending (the soonest end first); with `status=ended`, `to_date`
  descending (the latest ended first). With `status=all` the ended contracts come first (ascending
  `to_date`); accepted, because the default view is `not_ended` and *All* is for looking back
  (BR1-11).

### 5.4 The gated fields

| Field | Read (in the answer) | Written (on `POST` / `PUT`) |
|---|---|---|
| `callout_number` | only when `has_perm_at("contract:read", site)` | only then |
| `cost_note` | only when `has_perm_at("contract:read_senior", site)` | only then |
| every other field | `contract:read_basic` at the site | `contract:edit` at the site |

- **Read:** `_contract_out(row, flags)` builds the answer from the row and deletes the key
  `callout_number` when `can_read_callout` is false, and `cost_note` when `can_read_cost` is false:
  the key is **absent**, not `null`, so a test can tell "not allowed" from "empty". Every route that
  answers with a contract (list, detail, `POST`, `PUT`) goes through `_contract_out`; no route
  answers with a raw row.
- **Write:** after `validate_contract`, the shell removes `callout_number` and `cost_note` from the
  clean fields when the user lacks the key at the contract's site (the body's `site_id` on a
  `POST`, the locked row's on a `PUT`). So an editor without `read_senior` who sends a `cost_note`
  leaves the stored one as it was, and a new contract they create has `cost_note` NULL (the
  roadmap's rule: "an editor's save without `read_senior` leaves it as it was"). The dialog never
  sends the fields to such a user (`contractBody`, § 5.7); a malformed value is still refused by
  the validator (400), which only a hand-made request can meet.
- **Who:** an engineer reads and writes the call-out number, not the cost note; a manager both; IT
  admin neither (D5); admin both (the bypass).

### 5.5 Permissions

Four keys in `PERMISSIONS`, all in `SITE_SCOPED` (`backend/config_rbac.py:197`):

| Key | Holders | Comment line |
|---|---|---|
| `contract:read_basic` | `("*",)`, as `equipment:read` | the terms: every field but the call-out number and the cost note (D5) |
| `contract:read` | `("maint_engineer",)` (so the manager) | adds the call-out number (D10) |
| `contract:read_senior` | `("maint_manager",)` | adds the cost note (D5); later the prices and documents (R02.2, R02.3) |
| `contract:edit` | `("maint_engineer", "it_admin")` | add and edit (Q1.3 a) |

- `("*",)` reaches every role in `ROLES`, IT admin and the storekeeper included, and not the bare
  login role `maintenance_team` (`backend/config_rbac.py` `LOGIN_ROLE`). Through IT admin's token
  role, IT admin holds `contract:read_basic` and `contract:edit` at every site (`has_key_at`,
  `backend/access_core.py:100`).
- **The sites where a key is held:** `_sites_holding(cur, key)` reads `SELECT id, code, name, active
  FROM sites ORDER BY code` (plain) and keeps the sites where `has_perm_at(key, site_id)`
  (`backend/auth_utils.py:439`), as the Team viewer's method `grantable_site_ids` does (`backend/masters.py:1143`). A contract
  belongs to a site, not a unit, so unit rows (`person_units`) play no part: a member of the site
  with a key reads the site's contracts, whichever units they work in.
- **Per route** (each also decorated with `require_perm(key)`, `backend/auth_utils.py:495`: 403
  when the key is held nowhere; a request with no identity is refused with 401 by `require_auth`
  before any route, never admin):

| Route | Decorator | Then |
|---|---|---|
| `GET /api/contracts` | `contract:read_basic` | rows of `_sites_holding(cur, "contract:read_basic")` only; `site_id` filter outside them → an empty list, not a 403 |
| `GET /api/contracts/<id>` | `contract:read_basic` | missing, or the key not held at its site → 404 "Not found" (existence not shown) |
| `POST /api/contracts` | `contract:edit` | `require_perm_at("contract:edit", site_id, "site_id")` → 403 "You can't do this at BRICKS" (`backend/auth_utils.py:451`) |
| `PUT /api/contracts/<id>` | `contract:edit` | missing or `contract:read_basic` not held at its site → 404; `contract:edit` not held there → 403 naming the site |

- **Buttons:** *Add contract* shows when any site in `sites` has `can_add`; *Edit* on a row when its
  `can_edit`. So no button ends in a 403 (S070 D10).
- **Masters nav:** the *Masters* item shows only to holders of an edit key on masters data
  (`frontend/src/stores/navigation.js`, `perms: ["masters:edit", "equipment:edit", "people:edit",
  "failure_codes:edit"]`): engineers, managers, IT admin. The floor roles hold
  `contract:read_basic` but reach contracts on the machine card (R02.2), not here.
- **Identity:** no field changes who can log in. `site_id` decides who reads the contract and is
  fixed; `active` hides the row from the default list only. The answer names no person beyond the
  logins in `created_by` / `updated_by`, as every master.

### 5.6 Locks

The database runs REPEATABLE READ. Each write decides from its locking reads; access checks are
plain reads, as every predicate. contracts.py takes per write **at most one exclusive row lock, the
contract's own**, then only shared locks.

**Create** (`POST /api/contracts`), one `transaction`:

1. `SELECT id, active FROM sites WHERE id = %s LOCK IN SHARE MODE` → missing: 400 "Choose a site."
   (`site_id`); `active = 0`: 400 "Choose an active site." (`site_id`).
2. `require_perm_at("contract:edit", site_id, "site_id")` (plain) → 403. The gated fields (§ 5.4).
3. `SELECT id, active FROM vendors WHERE id = %s LOCK IN SHARE MODE` → 400 (§ 5.2).
4. `insert_row(cur, "contracts", clean, actor())` (`backend/db_helpers.py:57`): shared foreign-key
   locks on the site and the vendor, already held.
5. The answer, read inside the transaction (`_fetch_contract`), through `_contract_out`.

**Change** (`PUT /api/contracts/<id>`), one `transaction`:

1. `SELECT * FROM contracts WHERE id = %s FOR UPDATE` → 404 when missing.
2. Plain: `contract:read_basic` at the row's site → 404; `require_perm_at("contract:edit", …)` →
   403. The site rule (§ 5.1), the gated fields (§ 5.4), the period and breakdown calls on the
   merged values.
3. When `vendor_id` differs: the vendor `LOCK IN SHARE MODE` → 400 (§ 5.2).
4. `update_row` (a new vendor takes its shared FK lock, already held).
5. The answer (as create).

**Reads:** plain, no lock.

**No deadlock cycle**, against the notes (`backend/equipment.py` LOCK ORDER, `backend/masters.py`
docstring, S079's vendor note):
- *The contract row:* only contracts.py's `PUT` locks it, first in its transaction; no other module
  touches contracts in S080.
- *The vendor row:* S079's vendor update locks only its own row and waits on nothing after it
  (S079 § 5.3); S079's person write takes the person, then the vendor shared. Neither ever waits on
  a contract or a site lock a contract write holds, so a contract write waiting on the vendor waits
  behind a writer that finishes.
- *The site row:* masters.py's site update locks site rows (`_clear_default_site` a second one),
  never a vendor or contract row; it may wait for a contract create's shared lock, never the
  reverse. People writes take the site through the membership FK, shared, which is compatible.
- *Two contract writes:* creates share the site and vendor locks; two `PUT`s on one contract
  serialise on its row.

The coder writes this into contracts.py's LOCK ORDER note and adds a contracts.py bullet to
equipment.py's order: "contracts.py (S080) locks at most one contracts row FOR UPDATE (`PUT`), first
in its transaction, then the vendor row LOCK IN SHARE MODE when the vendor changes; a create takes
the site and the vendor LOCK IN SHARE MODE. It locks no equipment, unit, ticket, improvement or
procedures row, and no other module locks a contracts row, so it adds no lock cycle."

### 5.7 The screen: Masters › Contracts

**Place:** the last section of Masters, after *Team* (mock-up 01), shown with `contract:read_basic`.

**The card** (as `ManufacturersPanel.vue`): header *Contracts* with the switch *Show inactive* and
the button *Add contract* (when `can_add` somewhere). Under the header, one row of filters that
wraps on a phone: **Site** (*All sites*, then `sites`; preselected when `sites` has one), **Type**
(*All types*, the four), **Status** (*Not ended* default, *In force*, *Ending within 60 days*,
*Starts later*, *Ended*, *All*), **Vendor** (*All vendors*, then the vendors from S079's list, the
inactive ones marked "(inactive)"). Each change reloads `GET /api/contracts` with the filters.

**The table** (`table-responsive`, `table table-sm`):

| Column | From the `md` width | On a phone |
|---|---|---|
| Type | `contractTypeLabel` | in the small line under the title |
| Contract | title; the contract number under it, small | title; under it one small line "AMC · Atlas Copco · SMTW" (type, vendor, site code), for every user (BR1-05) |
| Vendor | name, "(inactive)" when so | in the small line under the title |
| Site | code | in the small line under the title; the column hidden (`d-none d-md-table-cell`) |
| From, To | DD-MM-YYYY (`formatDate`, `frontend/src/utils/datetime.js:21`) | To only, under the status |
| Status | badge: *In force* `text-bg-success`, *Ends in N days* `text-bg-warning`, *Ended* `text-bg-secondary`, *Starts on …* `text-bg-info`; *Inactive* `text-bg-light` beside it | same |
| (action) | *Edit* (when `can_edit`) | same |

Under the table: "N contracts." and, with the default status, "Ended contracts: choose Ended in
Status." When `total` exceeds the rows sent: "200 of N shown. Narrow the filters." Empty states:
no contracts at all → "No contracts yet. Add the first one with *Add contract*." (the second
sentence only for a user with `can_add`); filters that match none → "No contracts match these
filters."

**The dialog** (`FormModal.vue` through `useMasterForm`, `frontend/src/views/masters/useMasterForm.js`),
title *Add contract* / *Edit contract*, one column on a phone and two from `md`, in this order:

1. **Site** — a select of the `sites` with `can_add`; on edit, the site's code as read-only text.
2. **Type** — *AMC — labour and visits*, *CMC — parts included*, *Warranty — the maker's guarantee*,
   *On call — paid per call*; default *AMC*.
3. **Vendor** — the active vendors; on edit, a stored inactive vendor is the first option,
   "Atlas Copco (inactive)". Help "Choose a vendor from Vendors."
4. **Title** — help "e.g. Atlas Copco AMC 2026–27".
5. **Vendor's contract number** (optional).
6. **From**, **To** — `<input type="date">`.
7. **PM visits per year**, **Response time** (hours) — number inputs, optional.
8. **Covered by the contract** — ticks *Labour*, *Spare parts*, *Consumables (oil, filters)*,
   *Breakdown calls*; with the last ticked, **Calls per year** (help "Leave empty when the calls have
   no limit.").
9. **Covered**, **Not covered** — text areas.
10. **Only the vendor may repair** — tick, help "Tick when the contract is void if anyone else repairs
    the machine. The machine's page will then warn: Do not repair."
11. **Call-out number** — shown when the chosen site's `can_read_callout`; help "The vendor's
    breakdown line. Engineers and managers see it."
12. **Cost note** — shown when the chosen site's `can_read_cost`, under a small heading *Managers
    only*; help "Only the managers of this site see this note."
13. **Notes** — help "Do not enter prices here: every reader of the contract sees the notes." (R02
    § Risks).
14. On edit, `ActiveToggle.vue` as it is: *Deactivate* / *Reactivate*, with its own confirmation
    ("Deactivate **<title>**?" Yes / No).

- **Call contract** (settings: *Self-check, repo items* (13)): `useMasterForm({ path:
  "/api/contracts", blank, fromRecord, label: (c) => c.title, toBody, reload })`. `blank()` returns
  every field empty, `contract_type: "amc"`, the ticks false, and `site_id` the one `can_add` site
  when there is exactly one, else `null`; it takes no seed (`openCreate()` is called without one).
  `fromRecord(c)` copies the row's fields (the absent gated keys become `""`). `toBody(form)` is
  `contractBody(form, site)`: empty strings of the optional fields become `null`, number fields
  become integers, `breakdown_calls_per_year` is `null` when its tick is off, and `callout_number` /
  `cost_note` are **left out** unless the chosen site's flag allows them; on edit `site_id` is the
  stored one.
- `changeActive` sends `PUT {active}` (`useMasterForm`), so other unsaved edits are not sent, as in
  every master.
- **The one-tap path:** one site and the default type: the engineer picks the vendor, types the
  title and the two dates, saves.
- **Disabled controls:** none; a control the user may not use is not shown.
- **Destructive control:** *Deactivate* asks first, with `ActiveToggle`'s own confirmation
  ("Deactivate **Atlas Copco AMC 2026–27**?" Yes / No); *Show inactive* brings the row back.

### 5.8 The database down

Every route goes through `get_db()`: 503 while the database is down or missing (§ Yantra Specifics,
*DB may not exist*). No background task, no alert.

## 6. API

All under `contracts_bp` (`/api/contracts`), ids `<int:…>`. The list and create routes are
`contracts_bp.route("/", strict_slashes=False)`, as procedures.py's, so `GET /api/contracts` is not a
308.

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/contracts` | `contract:read_basic` | `site_id`, `contract_type`, `status`, `vendor_id`, `include_inactive=1` | 200, § 6.2 |
| `GET /api/contracts/<id>` | `contract:read_basic` | — | 200, the item (§ 6.1); 404 |
| `POST /api/contracts` | `contract:edit` | § 5.1 | 201, the item; 400, 403 |
| `PUT /api/contracts/<id>` | `contract:edit` | § 5.1, any subset | 200, the item; 400, 403, 404 |

### 6.1 The item

`{id, site_id, site_code, vendor_id, vendor_name, vendor_active, contract_type, title,
contract_number, from_date, to_date, covers_labour, covers_parts, covers_consumables,
covers_breakdown_calls, breakdown_calls_per_year, covered_text, not_covered_text,
pm_visits_per_year, response_hours, only_vendor_repairs, notes, active, created_at, created_by,
updated_at, updated_by, status: {kind, label, days}, can_edit, can_read_callout, can_read_cost}`,
plus **`callout_number`** when `can_read_callout` and **`cost_note`** when `can_read_cost`
(§ 5.4). Dates as `YYYY-MM-DD` (`row_to_dict`, `backend/db_helpers.py:100`); ticks and `active` as
1 / 0, as every master. `renewal_of_id` is not sent (R02.4).

### 6.2 The list

`{items, total, sites}`:
- `items`: the matching rows (§ 5.3 order), at most `MAX_PER_PAGE` (200,
  `backend/api_common.py:133`); inactive ones only with `include_inactive=1` (any other value:
  active only, as the masters' `_include_inactive`).
- `total`: the count of matching rows (one `COUNT(*)` with the same conditions).
- `sites`: `[{id, code, name, active, can_add, can_read_callout, can_read_cost}]` for every site in
  `_sites_holding(cur, "contract:read_basic")`; `can_add` = active and `contract:edit` held there.
  The filter's site list and the dialog's site list and its two field flags come from here.
- Query errors: `site_id` or `vendor_id` not a whole number ≥ 1 → 400 (`int_arg(name, None, 1)`,
  `backend/api_common.py:139`: "site_id must be a whole number at least 1"); `status` or
  `contract_type` outside its list → 400 (`enum_arg`, `backend/api_common.py:150`). An empty
  `status` is the default `not_ended`.
- The flags per item come from `has_perm_at` per site, computed once per site in the request.

## 7. Design decisions

- **D1. A module of its own, `contracts.py` / `contracts_core.py`, not masters.py.** R02.2–R02.6
  grow it (the page, the machines, renewal, breakdown calls), and the roadmap names `contracts.py`
  for R02.4 and R02.6. Rejected: routes in masters.py (already 1,500 lines; masters are site-less
  pick-lists, a contract is a site record with three read levels).
- **D2. The API at `/api/contracts`, the screen a Masters tab** (Q1.8 a). The URL names the record,
  so R02.2's page `/contracts/:id` pairs with it. Rejected: `/api/masters/contracts` (would tie a
  site record to the masters blueprint).
- **D3. No amount in S080; the cost note only** (D8). The price per machine and the total come with
  R02.2's machine rows. Rejected: a period amount on the contract now (D8 superseded Q1.7 a; a
  second source of the cost to keep equal with the machine prices).
- **D4. A field the reader may not see is absent from the answer, and a field the writer may not
  see is ignored on write.** One builder (`_contract_out`) for every answer, one filter for every
  write; the roadmap's own rule ("leaves it as it was"). Rejected: a 403 when a non-holder sends the
  field (their own dialog never sends it, so only a hand-made request would meet it, and the
  roadmap asked for "leaves it"); `null` for a hidden field (a reader could not tell hidden from
  empty, and a client might save `null` back).
- **D5. IT admin edits but reads neither gated field.** D10 names "engineers, managers and admin"
  for the call-out number, and D4 "IT admin does not see the cost". So IT admin's dialog has neither
  field, and its save never touches them. Rejected: `contract:read` for IT admin (departs from D10).
- **D6. The site is fixed after create; the vendor may change.** R02.2's machines and their prices
  belong to the site; a moved contract would leave them behind or move a cost to another site's
  managers. A vendor typo is a plain correction. Rejected: a free site change (a site rule for each
  machine row); a fixed vendor (a typo needs a new contract).
- **D7. Status computed in the core from the IST date, the badge window 60 days.** Never stored, so
  nothing goes stale overnight; one function serves the list, the filter and later the card and the
  reminders. 60 is Q5.1 a's first reminder. Rejected: a stored state updated by a daily task (a job
  for a value the dates already give).
- **D8. The sites where a key is held, not the units.** A contract is a site record; reading it
  needs a role at the site, as `has_perm_at` decides. Rejected: `accessible_unit_ids`
  (`backend/equipment.py:354`), which would hide a site's contracts from a member with no unit row
  there.
- **D9. contracts_core reuses masters_core's rules through public names** (`collapsed`,
  `flag_parser`, `validate_fields`, `id_parser`, and the existing public `optional_text_parser`).
  One copy of each rule, no private import (S075 D10's reason). The one stated copy is the 7-line
  `_iso_date` from `improvements_core` (two cores do not import each other's private helpers).
  Rejected: a private import (a rename breaks it silently); a field loop and id parser of its own,
  as the newer cores have (two copies of the create/update rule).
- **D10. Contract number and title are not unique** (D7: one quote, two contracts). Rejected: a
  unique `(vendor_id, contract_number)` (refuses D7's case).
- **D11. The call-out number uses S079's phone rule through S079's factory.** S079 writes
  `phone_parser(label)` and `_parse_phone = phone_parser("Phone")`; S080 calls
  `phone_parser("Call-out number")` and renames nothing. The vendor's office number and the
  contract's breakdown line accept the same shapes (6–15 digits; spaces, hyphens, dots and brackets;
  a `+` only first; 20 characters), and each message names its own field. Rejected: a second rule in
  contracts_core (two rules for one kind of value); free text (a typed note in the number field).
- **D12. The last section of Masters, after *Team*,** as mock-up 01 places it. Rejected: beside
  *Vendors* before *Team* (S079 puts *Vendors* there; either works, the mock-up decides).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v43.py`)

On the pattern of `test_migration_v41.py` (`_migrate`, `_recreate`, `_run`, `_schema` from
`test_migration_v20.py`):
- A fresh database: `contracts` with its keys (`ix_contracts_site`, `ix_contracts_vendor`,
  `ix_contracts_renewal_of`) and foreign keys (`fk_contracts_site`, `fk_contracts_vendor`,
  `fk_contracts_renewal_of`).
- **A v42 database with a site and a vendor** (S079's table) migrates to v43, the rows kept.
- The CHECKs refuse (4025): `to_date` before `from_date`; `pm_visits_per_year` 53; `response_hours`
  0 and 721; `breakdown_calls_per_year` 4 with `covers_breakdown_calls` 0; and 366 with it 1. The
  boundaries pass: the same day for From and To, 0 and 52 visits, 1 and 720 hours, 1 and 365 calls.
- A `vendor_id` that does not exist is refused (1452).
- Two contracts with the same vendor and contract number are accepted (D7).
- A re-run of v43 changes nothing (`_schema()` equal).

### 8.2 Backend (`test_contracts_core.py`, `test_contracts_api.py`)

**Core:** `validate_contract` — each message of § 5.1: every required field missing on a `POST`;
nothing required on a `PUT`; the title collapsed ("Atlas  Copco\nAMC" → "Atlas Copco AMC"); 100 /
101 characters; a number title; `contract_type` "AMC" (case) and "lease" refused; a boolean
`site_id` ("Choose a site."); every required field absent on a `POST` gives its "Enter …" /
"Choose …" text, not "… is required"; the too-long texts in the parsers' form ("Title must be at
most 100 characters"); dates "31-03-2027" (wrong format), "2027-02-30", "1999-12-31", "2100-01-01" refused,
"2000-01-01" and "2099-12-31" pass; ticks "yes" refused; `breakdown_calls_per_year` 0, 366, "4",
`true` refused, `null` and 1 pass; `pm_visits_per_year` −1, 53 refused, 0 and 52 pass;
`response_hours` 0, 721 refused; texts of 1000 / 1001 and 255 / 256; `callout_number` "+91 00000
00000" passes, "call 000000" and "00000" (5 digits) refused with the messages naming *Call-out
number*, "(044) 0000-0000" passes, 21 characters refused, "" → `None`;
`active` ignored on a `POST`. `period_error` (equal dates pass; To before From → the To message, or
the From message when only From was sent). `breakdown_calls_error` (number with the tick off;
the tick off clears). `contract_status` with a fixed `today`: from tomorrow → `upcoming` "Starts on
DD-MM-YYYY"; from today → in force; to = today → `ending` "Ends today", days 0; to = today + 1 →
"Ends in 1 day"; + 60 → "Ends in 60 days"; + 61 → `in_force`; to = yesterday → `ended`.
`status_bounds` for each filter, and a check that each filter matches the rows of its kinds over a
set of dates around the boundaries.

**API**, each test with its own sites and vendors (`make_site`, `make_vendor`, `user_at_sites`
for the per-site cases; the kept worker database gives the starting state; titles carry `uniq`):
- **Create:** an engineer at site A (201; `status`, `can_edit` true, `can_read_callout` true,
  `can_read_cost` false; `callout_number` stored and answered; `cost_note` absent from the answer);
  a manager (201, both fields answered); IT admin (201; both keys absent; a `cost_note` and a
  `callout_number` sent are not stored: NULL in the row, read with `db_rows`); an engineer who sends
  `cost_note` (201, NULL stored); an operator, a technician, a supervisor, a storekeeper (403); an
  engineer of site A creating at site B where they are operator (403 naming B); an unknown site
  (400 `site_id`), an inactive site (400 "Choose an active site."); an unknown vendor and an
  inactive vendor (400 `vendor_id`, the message of § 5.2); To before From (400 `to_date`); calls
  per year with the tick off (400).
- **Change:** each field; only `to_date` before the stored From (400 `to_date`); only `from_date`
  after the stored To (400 `from_date`); the tick off clears a stored number; `site_id` equal (200)
  and different (400 `site_id`); a vendor change to an active vendor (200) and to an inactive one
  (400); a contract whose vendor was set inactive, saved with the same `vendor_id` and a new title
  (200); `active` false then true; **an engineer's `PUT` with `cost_note` leaves the manager's note
  unchanged** (`db_rows`); IT admin's `PUT` with `callout_number` leaves it unchanged; an engineer
  of site B on a site-A contract (404 when they hold no role at A; 403 naming A when they are
  operator at A); a missing id (404).
- **Read:** the list holds only the sites where `contract:read_basic` is held (a user at A sees no
  B contract; IT admin sees both; the manager of A and B both); `site_id` of an unheld site → empty
  list; the filters `contract_type`, `vendor_id`, each `status` (rows dated around today), the
  default `not_ended`, `include_inactive`; the order (`to_date` ascending; `ended` descending);
  `total` and the 200 cap (a test that patches `contracts.MAX_PER_PAGE`, the name contracts.py imports, to 2); `sites` with the flags per
  role (engineer: `can_add` true, `can_read_cost` false; IT admin: `can_add` true, both read flags
  false; operator: `can_add` false); a non-integer `site_id` and an unknown `status` (400). The
  detail: 200 for a reader at the site, 404 for a user of another site; the gated keys per role
  (operator: neither; engineer: `callout_number`; manager: both).
- **The database down** (`db_down`, `backend/tests/conftest.py`): `GET /api/contracts` and `POST
  /api/contracts` answer 503.

### 8.3 Existing tests that break or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` — `contract:read_basic` joins every row (operator,
  technician, supervisor, engineer, manager, IT admin, storekeeper); `contract:read` and
  `contract:edit` join the engineer and manager rows; `contract:read_senior` the manager row;
  `contract:edit` the IT admin row; the comment above the rows gains an S080 line. New
  `test_contract_keys`: the holders per key as § 5.5 (`compute_permissions` over `ROLES`), all four
  in `SITE_SCOPED`, and `contract:read_senior` ⊂ `contract:read` ⊂ `contract:read_basic` holders.
  `test_site_scoped_keys_exist` and `test_every_role_gets_wildcard_permissions` stay green.
- `backend/tests/test_modules.py` (`LATEST_VERSION`, now 43): green.
- `backend/tests/test_migration_v20.py` … `test_migration_v42.py`: each slices its own range;
  green.
- `backend/tests/test_schema_docs_shell.py`: reads `LATEST_VERSION`; green once
  `tooling\schema-docs.bat write` has run.
- `backend/tests/test_auth.py`: compares `/api/auth/me`'s `permissions` with `compute_permissions`,
  not a fixed list; green.
- `frontend/e2e/masters.spec.js`, `frontend/e2e/floor.spec.js`, `frontend/e2e/tickets-raise.spec.js`:
  click Masters sections by exact name (`"Team"`, `"Meter types"`); a new last section changes no
  name; green. `frontend/e2e/screens.spec.js` opens `/masters` and waits for `"Sites"`; green.

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

Set-up by API in the spec (`apiAs`, `frontend/e2e/support/people.js`): a vendor per test with a
name from the test's title, through S079's vendors route as the engineer; contracts by `POST
/api/contracts`; dates relative to today, far from the 60-day edge (ended: To 10 days ago;
ending: To in 20 days, asserted as `/Ends in \d+ days/`; upcoming: From in 100 days). Every flow
test calls `expectDialogFits` on the dialog it opens; refusals with `expectFieldMessage`. Untagged
unless marked.

- **important** `S080: the engineer adds a contract and sees it In force in Masters › Contracts`
  — `"Add contract"`; an empty save shows "Enter a title." beside *Title*; the filled dialog saves;
  the row shows the title, the vendor and *In force*.
- **important** `S080: a To date before the From date is refused beside the To field` — "Enter a To
  date on or after the From date."
- **important** `S080: the engineer sees the call-out number field and no cost note; the manager
  sees both` — the two dialogs (`"Call-out number"`, `"Cost note"`, `"Managers only"`).
- `S080: IT admin adds a contract without the call-out number or the cost note` — neither field in
  the dialog; the row appears.
- **important** `S080: the status badges and the Status filter` — an ending, an upcoming and an
  ended contract by API: the default list shows *Ends in N days* and *Starts on DD-MM-YYYY*, not
  the ended one; *Ended* in Status shows it with *Ended*.
- `S080: an inactive vendor is not offered for a new contract, and its contract shows it as
  inactive` — the vendor set inactive by API: missing from *Vendor* in *Add contract*; the existing
  contract's row and edit dialog show "(inactive)"; the edit saves.
- `S080: a deactivated contract leaves the list, and Show inactive brings it back` —
  `"Deactivate"` with `ActiveToggle`'s confirmation; the row goes; the switch shows it with *Inactive*.
- `S080: the engineer does not see another site's contract; the manager sees Edit on both` — a BRICKS contract by API as the
  manager (who holds BRICKS): the engineer (SMTW only) does not see it; the manager sees *Edit* on
  both.
- `S080: the Contracts list fits a phone with no sideways scroll` (`@device`) —
  `expectNoSidewaysScroll` with three rows; Site and From columns hidden below `md`; the small
  line under the title shows the site code ("· SMTW"), BR1-05.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/masters.spec.js e2e/screens.spec.js`, and the whole suite at Normal once at the end. No shared
file changes (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store,
`e2e/support/`), so no extra WebKit run.

### 8.5 On a real device

None. The screen is a desktop and phone table and dialog that a browser engine judges.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal
  browser runs green.
- By API and screen: "Atlas Copco AMC 2026–27", AMC, SMTW, 01-04-2026 to 31-03-2027, labour and
  breakdown calls ticked, 4 PM visits, 24 hours; the engineer sees the call-out number
  `+91 00000 00000`, the manager also the cost note, IT admin neither.
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**Contract fields by key (S080):** every
  answer with a contract goes through `contracts._contract_out`, which leaves out `callout_number`
  without `contract:read` and `cost_note` without `contract:read_senior` at the contract's site;
  every write drops them for a writer without the key. A route that answers with a raw contracts
  row, or writes them unfiltered, leaks the call-out number or the cost (ISO 27001 A.5.15). R02.2's
  prices and R02.3's documents join this rule."

## 9. Open questions and assumptions

- **Q1. No cost column in the list (recommended), or the cost note as a column for managers?** The
  roadmap's R02.1 *Screens* line says "cost for senior holders", and mock-up 01 shows *Cost (₹)*,
  but D8 moves the price to R02.2's machine rows, and R02.1 "holds the cost note only". **This brief
  follows D8:** no cost column until R02.2 adds the total (sum of machine prices). (b) Show the cost
  note in a column for `read_senior` holders now: a free-text note in a narrow column reads badly,
  and R02.2 replaces it. *Roadmap inconsistency, reported.* Not defining. **Taken as recommended by
  the orchestrator under the delegation of 30-10-2026; KLA may override at gate B.**
- **Q2. IT admin edits contracts but sees neither the call-out number nor the cost note** (D5). It
  follows D4 and D10 as written; named for KLA at gate A because IT admin then cannot enter the
  call-out number. Not defining. **Taken as recommended by the orchestrator under the delegation of
  30-10-2026; KLA may override at gate B.**
- **A1. The vendors route and store from S079.** The dialog's and the filter's vendor lists come
  from `ensureVendors()` (S079: `/api/masters/vendors?include_inactive=1`, all vendors; the panel
  keeps the active ones for a new pick). Names as in S079's brief; checked at the staleness review.
- **A2. No read-only contract view for a reader who cannot edit** (e.g. an engineer of SMTW who is
  operator at BRICKS sees BRICKS rows without *Edit*): the row shows type, title, vendor, dates and
  status; the full terms come with R02.2's contract page. Every Masters user (engineer, manager, IT
  admin) edits at the sites where they hold their main role.
- **A3. The 60-day badge window is a constant** (`ENDING_SOON_DAYS`); R02.5 decides whether it
  follows the reminder settings.
- **A4. `renewal_of_id` without a unique key.** R02.4 decides whether one contract may have two
  renewals (a mixed quote split later); a unique key then needs its own migration and a check of
  production's rows.
- **A5. The phone rule** is S079's (its § 5.1 as revised after its review), through S079's
  `phone_parser`; the staleness review checks the code against § 5.1 here (D11).
- **A6. Dates in the JSON body are `YYYY-MM-DD` only**, by a stated copy of `improvements_core._iso_date`
  (`backend/improvements_core.py:394`): the date input sends that; the screen shows DD-MM-YYYY.
- **The size rule:** one table, one screen, 17 code and test files, one concern: no split.
  **Length** about 780 lines, past the ~650 asked, as S075 (774): most of it is § 5's field table,
  the gated-field rule and the lock sequences, and § 8's tests by name. No further cut proposed.
- **Staleness check due before coding.** The brief is drafted while S079 is briefed. Before S080 is
  coded, a staleness review checks v42/v43, S079's `vendors` columns and route, its vendor lock
  note, its test fixture, the Masters section order, and `masters_core.py`'s parsers.
- **Standards *to verify*:** ISO 55001:2024's clause number for outsourcing; ISO 9001 § 8.4.3;
  ISO 27001 A.8.3; EN 13269's edition and content.
- **No defining question.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

Sections changed: header (Status, Baseline), § 3 (backend, tests, file count), § 5.1, § 5.3, § 5.5,
§ 5.7, D9, D11, § 8.2, § 8.4, § 9.

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): the reused parsers' "… must be at most N characters" / "… must be text" for too long and wrong type; "Enter a …" / "Choose a …." for missing or empty, as sentences with a period; absent required fields are parsed as `None`, so the field's own text shows. § 5.1 table and style note, § 8.2. |
| BR1-02 minor | Accepted (a): `ActiveToggle.vue` as it is, *Deactivate* / *Reactivate* with its own confirmation; the site message and the e2e test title say *Deactivate*. § 5.1, § 5.7, § 8.4. |
| BR1-03 minor | Accepted (a): public aliases `validate_fields` and `id_parser` beside `collapsed`, `flag_parser`; `_iso_date` is a stated 7-line copy in `contracts_core` (no import of a private helper of another core). § 3, § 5.1, D9, § 9 A6. |
| BR1-04 minor | Accepted (a): S079 provides `phone_parser(label)`; S080 calls `phone_parser("Call-out number")` and renames nothing; the phone rule follows S079's revised § 5.1 (digits, spaces, `-`, `.`, brackets, `+` first, 6–15 digits, 20 characters); `test_masters_core.py` leaves the file list (17 files). § 3, § 5.1, D11, § 8.2, § 9 A5. |
| BR1-05 minor | Accepted (a): on a phone the small line under the title shows type, vendor and site code for every user; the `@device` test asserts the site code. § 5.7, § 8.4. |
| BR1-06…BR1-12 nits | Accepted: BR1-06 the test patches `contracts.MAX_PER_PAGE` (§ 8.2); BR1-07 the Team viewer's method `grantable_site_ids` (§ 5.5); BR1-08 "is void" (§ 5.7); BR1-09 "the maker's guarantee" (§ 5.7); BR1-10 the test title (§ 8.4); BR1-11 the `all` order stated and accepted (§ 5.3); BR1-12 is the orchestrator's (the INDEX row). § 9 Q1 and Q2 taken as recommended under the delegation of 30-10-2026. |
