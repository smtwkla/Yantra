```
Step: S079 — Vendor master
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: d216f48
Status: Done (committed 73f0bc5, adopted 31-10-2026); was: Gate B 30-10-2026 (code review r1: 2 nits, fixed by the orchestrator)
From: R02.9
```

# S079 — Vendor master

## 1. What will be built

A **vendor** is an outside firm the plant buys maintenance from: Atlas Copco for the screw
compressors, Fuji Electric for the UPS. Today a vendor is only a contractor Team record, and
nothing says which firm a contractor works for. This step lists each firm once, so the contract
register (S080, R02.1), the breakdown calls (R02.6) and the vendor report (R02.8) all point at
the same row (D11, KLA 30-10-2026).

1. **A vendor master.** A new table `vendors`, shared by all sites like `manufacturers`: name,
   phone (optional), note (optional), active, who and when (Q9.1 a, Q9.2 a plus a phone).
2. **A *Vendors* tab in Masters**, placed before *Team* (mock-up
   `docs/roadmap/R02-mockups/06-vendors-tab.png`). The table shows Name (with the phone and
   the note under it), People (the active Team records linked to the vendor), Status and
   *Edit*. *Show inactive*, *Add vendor* and one dialog, on the pattern of
   `ManufacturersPanel.vue` (`FormModal.vue`, `useMasterForm`).
3. **An optional vendor on a contractor's Team record.** A new column `people.vendor_id`. The
   Team dialog gets *Vendor (optional)*, shown only for *Contractor*. The Team list shows the
   vendor beside the badge: "Contractor · Atlas Copco". A firm that sends a different
   technician each time is one Team record such as "Atlas Copco service", contractor, linked
   to the vendor (Q9.3 a).
4. **A warning before a link changes.** Editing a linked person, a change of vendor (or
   *Direct employee*) shows that the person's earlier tickets go with the new link, because
   the link counts as it is now (Q9.5 a).
5. **Rules in the API and the database.** Only a contractor may have a vendor (a CHECK and an
   API refusal); only an active vendor can be newly linked; a vendor is never deleted, and
   deactivating one keeps its links.

**After the deploy:** an engineer adds the five known vendors in *Masters › Vendors*, then
links today's contractor records in *Team* by hand. The migration links nothing (no guess from
a name).

### Out of scope

- Contracts, their vendor and the call-out number (S080, R02.1). The call-out number stays on
  the contract (D10); the vendor's phone is the office number.
- Email, address, GSTIN or other tax numbers on a vendor (Q9.2), and any link to the ERP's
  supplier list.
- An approved-vendor status or a vendor rating (roadmap § Out; ISO 9001 § 8.4.1 evidence comes
  from R02.8).
- A history of a person's vendor links (Q9.5 a: the current link counts).
- Assigning a vendor itself to a ticket (Q9.3 b). Tickets keep naming Team records.
- The vendor on ticket screens, labour rows or reports (R02.6, R02.8).
- Linking existing contractor records by a migration or a bulk screen.
- The People count as a link to a filtered Team list; a Team search or filter by vendor; a
  contract count on the Vendors tab (R02.1 may add it).
- A tap-to-call link on the phone (shown as text).
- Merging vendors with manufacturers (Q9.1 b, rejected).

## 2. Standards and practice

- **ISO 9001:2015 § 8.4 Control of externally provided processes, products and services**
  (§ 8.4.1 general, § 8.4.3 information for external providers; sub-clause numbers *to
  verify*). It says: choose outside providers on stated criteria, check how they perform, and
  keep records of it. A list of providers, one record each, is where that starts. This step
  builds the list; the performance evidence comes with R02.8. ISO 9001 is a future goal for the
  plant (memory: *Teach maintenance standards*).
- **ISO 55001 § 8.3 Outsourcing** (the 2014 edition's number; the 2024 edition's *to verify*).
  It says: work given to an outside firm stays the plant's responsibility; the plant decides
  what it outsources, controls it, and keeps the evidence. One row per firm, and each
  contractor record linked to its firm, lets later steps show which firm did which work.
- **ISO 14224 maintenance resources** (§ 9, the maintenance data, Table 8 *to verify*). It
  says: a maintenance record names who did the work, including whether it was done in-house or
  by a contractor. Yantra already records the person and their *employment*; this step adds
  which contractor firm.
- **ISO 8000 (data quality): one spelling per real thing.** The vendor name is unique without
  regard to case or repeated spaces, as S012 did for manufacturers.
- **ISO/IEC 27001:2022 A.5.15 Access control** (and A.8.3 information access restriction, *to
  verify*). It says: people see only what their job needs. The vendor's phone goes only to
  the people who maintain the master (§ 5.4, D3).
- **Deliberate departure from the manufacturer pattern:** a manufacturer cannot be deactivated
  while it has active models; a vendor can be deactivated with linked people, because its
  people may still work on open tickets and their links are the history R02.6 and R02.8 read.

## 3. Where

### Backend

- `backend/local_db.py`: migration **v42** (§ 4), with its comment (no precondition, why, the
  rollback).
- `backend/masters_core.py`:
  - `PHONE_MAX = 20`, `PHONE_DIGITS_MIN = 6`, `PHONE_DIGITS_MAX = 15`, `VENDOR_NOTE_MAX = 255`;
    `_parse_phone`; `_VENDOR_FIELDS`; `validate_vendor(data, creating)`.
  - `_PERSON_FIELDS` gains `"vendor_id": (_parse_optional_id("Vendor"), False)`.
  - `vendor_link_error(employment, vendor_id, vendor_sent)` (pure, § 5.2): `(field, message)`
    or `None`, next
    to `no_login_role_error`.
- `backend/masters.py`:
  - three vendor routes (§ 6), after the manufacturers block; `_VENDOR_SELECT`, `_vendor_out`;
  - `UNIQUE_KEY_ERRORS` entry `uq_vendors_name`;
  - the people routes: `_PERSON_SELECT` (the vendor's name and active flag, § 5.2) used by
    `list_people` and `_fetch_person`; the link check and `_check_new_vendor` in
    `create_person` and `update_person`;
  - the module docstring's lock notes and the Team block's comment gain the vendor (§ 5.3).

### Frontend

- `frontend/src/stores/masters.js`: `vendors`, `ensureVendors`, cleared in `resetMasters`.
- `frontend/src/views/masters/VendorsPanel.vue` (new), on the pattern of
  `ManufacturersPanel.vue`.
- `frontend/src/views/MastersView.vue`: the section `{ key: "vendors", icon:
  "fa-solid fa-handshake", label: "Vendors", perm: "masters:read" }`, placed after *Trades*
  and before *Team*.
- `frontend/src/views/masters/PeoplePanel.vue`: the *Vendor (optional)* select, its clearing on
  *Direct employee*, the change warning, `vendor_id` in `blank`, `fromRecord` and `toBody`,
  the vendor beside the badge in the list (§ 5.5).

### Tests

- `backend/tests/test_migration_v42.py` (new), on the pattern of `test_migration_v41.py`.
- `backend/tests/test_vendors_api.py` (new): the vendor routes, the phone's readers, the
  permissions, the database down (§ 8.2).
- `backend/tests/test_people_api.py`: a class `TestVendorLink` (§ 8.2).
- `backend/tests/test_masters_core.py`: classes `TestVendor` and `TestVendorLink`.
- `backend/tests/conftest.py`: `"vendors"` joins `_TABLES` right after `"people"` (children
  before parents, as the rest of the tuple; no seed rows); `Uniq.vendor_name()`
  (`"Vendor 0001"`); fixture `make_vendor(admin, uniq)` on the shape of `make_manufacturer`.
- `frontend/tests/masters.test.js`: `ensureVendors` in the "each list from its own path" and
  `resetMasters` cases.
- `frontend/e2e/masters.spec.js` (§ 8.4).
- Unchanged, checked: `backend/tests/test_migration_v41.py` slices `range(20, 42)` (line 20–21),
  so v42 does not touch it; `backend/tests/test_rbac.py::TestComputePermissions::test_role_matrix`
  has no new key; `backend/tests/test_migration_v27.py` compares `SELECT * FROM people` before
  and after v27 only.

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: a `vendors` line (area *Team and access*); the `people` line names
  `vendor_id` and its CHECK; the *Team and access* area note adds "vendors". Then
  `tooling\schema-docs.bat write`, read `git diff docs/schema/`, and `check` exits 0. Never edit
  `docs/schema/schema.json` or `docs/schema/schema-data.js` by hand.
- `docs/Plant-Facts.md` § 4: the five vendors, names and what they maintain only (Atlas Copco:
  the two screw compressors; Toyota Material Handling: pallet trucks and stackers, for each
  company; Sartorius: the moisture analyser, on call; Fuji Electric: UPS and harmonic filter;
  VP Power Systems: servo stabiliser and UPS); source "User, 16-10-2026 and the contracts read
  27-10-2026". No phone number or address. A § 10 change-log line.
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 9 Q3 (taken as recommended).
- `docs/Plan.MD`: no change. § 2 item 9 and § 3's Team paragraph already say what this
  step builds (re-plan of 30-10-2026, uncommitted). Changed only if the step departs.

## 4. Data model

### 4.1 Migration v42

```sql
CREATE TABLE IF NOT EXISTS vendors (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    phone       VARCHAR(20) NULL,
    note        VARCHAR(255) NULL,
    active      TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by  VARCHAR(100) NOT NULL,
    updated_at  DATETIME NULL,
    updated_by  VARCHAR(100) NULL,
    CONSTRAINT uq_vendors_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE people
    ADD COLUMN IF NOT EXISTS vendor_id INT NULL AFTER employment,
    ADD KEY IF NOT EXISTS ix_people_vendor (vendor_id),
    ADD CONSTRAINT fk_people_vendor
        FOREIGN KEY IF NOT EXISTS (vendor_id) REFERENCES vendors (id);

ALTER TABLE people ADD CONSTRAINT IF NOT EXISTS chk_people_vendor
    CHECK (vendor_id IS NULL OR employment = 'contractor');
```

- Three statements in the v42 list, the `IF NOT EXISTS` forms v38 and v41 already use
  (`local_db.py`, v38: `FOREIGN KEY IF NOT EXISTS`, `ADD CONSTRAINT IF NOT EXISTS chk_…`), so
  a half-applied v42 runs again.
- **Unique name without regard to case or repeated spaces**, as `manufacturers`
  (`uq_manufacturers_name`, v20): the parser collapses runs of spaces (`_collapsed`,
  `masters_core.py`), and the unique key compares in the table's default utf8mb4 collation,
  which ignores case (fact: `test_models_api.py::TestManufacturers::test_duplicate_by_case_or_by_repeated_spaces_is_409`
  passes on the same set-up).
- **The `people` table holds production rows.** The ALTER is safe on them: the new column is
  NULL on every row; a NULL foreign key is not checked; the CHECK is true for every row where
  `vendor_id IS NULL`. No row changes.
- **No `_PRECONDITIONS` entry.** `_PRECONDITIONS` guards v20, v25 and v34 only
  (`local_db.py`, `_PRECONDITIONS = {20: …, 25: …, 34: …}`): a squash, a rename and a seed that
  existing rows could block. v42 adds a table, a NULL column and a CHECK that every existing row
  meets; nothing is converted or dropped (as v35 and v41 say in their comments).
- **No seed rows.** The engineer adds the vendors (§ 1).
- **Rollback:** a release before v42 reads `people` with `SELECT *` (`masters.py`
  `list_people`, `_fetch_person`) and returns `vendor_id` as one more key, unused; it never reads
  `vendors`. One limit: on the old release a PUT `{employment: "direct"}` on a linked person
  breaks the CHECK and answers 500. Before a rollback, unlink such people or accept it.

## 5. Rules

### 5.1 The vendor

Validated by `validate_vendor` (`masters_core.py`), field by field; the first error is the 400
(`clean_body`). On a `PUT` an absent field stays as it is.

| Field | Required on create | Rule | Refusal (400, field) |
|---|---|---|---|
| `name` | yes | text; trimmed; inner runs of spaces become one (`_parse_manufacturer_name`, the same rule); 1–100 characters after that | missing, empty, only spaces or not text: "Name is required"; 101 or more: "Name must be at most 100 characters" |
| `phone` | no | `null` or `""` (after trimming) clears it; text; trimmed, inner runs of spaces become one; at most 20 characters; every character a digit, a space, a hyphen, a dot or a bracket `(` `)`, with `+` allowed only as the first character (`^\+?[0-9 ().-]*$`); 6 to 15 digits in all (`PHONE_DIGITS_MIN`, `PHONE_DIGITS_MAX`; 15 is the E.164 maximum). No grouping rule (BR1-01) | not text (a number, a list, `true`): "Phone must be text"; 21 or more characters: "Phone must be at most 20 characters"; another character or the digit count: "Enter 6 to 15 digits. Spaces, hyphens, dots and brackets are allowed." |
| `note` | no | `optional_text_parser("Note", 255)`: `null` or `""` clears it; trimmed | not text: "Note must be text"; 256 or more: "Note must be at most 255 characters" |
| `active` | no (default 1) | `_parse_active` | "Active must be true or false" |

- **Phone examples** (unit tests; obviously fake, never a real number): `"+91 00000 00000"`
  is stored as given; `"000-000-0000"`, `"(000) 0000 0000"`, `"000.0000.0000"` and
  `"-000000"` pass; `"00000"` (5 digits), `"0000000000000000"` (16 digits), `"00 00+"` (a `+`
  not first), `"0000 0000 ext"` and `"call 000000"` are refused.
- **Shared with S080:** the contract's call-out number reuses `_parse_phone` (S080's brief),
  so both numbers follow one rule.
- **Duplicate name:** 409 `{"error": "A vendor with this name exists. Use that one, or enter a
  different name.", "field": "name"}` (`UNIQUE_KEY_ERRORS["uq_vendors_name"]`), also for "atlas
  copco" or "Atlas   Copco" against "Atlas Copco".
- **Rename:** always allowed. Links are by id; a rename shows at once in Team.
- **Deactivate:** always allowed, links stay (§ 2, the departure). An inactive vendor is not
  offered for a new link (§ 5.2). **Reactivate:** always allowed.
- **Never deleted.** No `DELETE` route.
- **Extra fields** in the body (`people_count`, `id`, `email`) are ignored, as in every master
  (`_validate` reads only its own fields).
- **No body or not a JSON object:** 400 "Request body must be a JSON object" (`clean_body`).
- `PUT` with `{}`: 200, nothing changes, no who/when stamp (`update_row` does nothing).

### 5.2 The link on a person

`vendor_id` is optional on `POST` and `PUT /api/masters/people…`. Parsed by
`_parse_optional_id("Vendor")`: `null` means no vendor; `true`, `"3"`, `0`, `-1` or `1.5` → 400
"Vendor must be a record id" on `vendor_id`.

**The effective values** of a save: the employment and vendor sent, or else the stored ones (a
`POST` has no stored ones: absent `vendor_id` is `NULL`).

1. **Only a contractor has a vendor.** When the effective employment is `direct` and the
   effective vendor is not `NULL`: 400 "A direct employee works for no vendor. Clear the vendor,
   then save." `vendor_link_error(employment, vendor_id, vendor_sent)` returns `(field,
   message)` or `None`, so the whole rule is in the core (BR1-04): the field is `vendor_id`
   when the body sends a non-null `vendor_id` (`vendor_sent`), else `employment`. Each `PUT`
   shape:

   | Stored | Body | Answer |
   |---|---|---|
   | contractor, vendor 5 | `{employment: "direct"}` | 400 on `employment`; nothing changes |
   | contractor, vendor 5 | `{employment: "direct", vendor_id: null}` | 200, unlinked, direct |
   | contractor, vendor 5 | `{vendor_id: null}` | 200, unlinked, still contractor |
   | direct, no vendor | `{vendor_id: 5}` | 400 on `vendor_id` |
   | direct, no vendor | `{employment: "contractor", vendor_id: 5}` | 200 (rule 2 applies) |
   | contractor, vendor 5 | `{active: 0}`, `{name: …}` or `{trade_ids: …}` | 200, the link stays |

   A `POST` with `employment: "direct"` and a vendor: 400 on `vendor_id`. The check runs on the
   locked row (§ 5.3), so a concurrent save cannot slip past it; the CHECK `chk_people_vendor`
   holds it in the database too.
2. **A new link needs an existing, active vendor.** A link is *new* when the body sends a
   non-null `vendor_id` that differs from the stored one (on a `POST`, any non-null one). Then
   the vendor row is read `LOCK IN SHARE MODE` (`_check_new_vendor`):
   - no such row: 400 "That vendor no longer exists. Reload and try again." on `vendor_id`;
   - inactive: 400 "Vendor <name> is inactive. Choose another vendor or reactivate it." on
     `vendor_id`.
   The texts and the 400 follow the Team dialog's own refusals for a trade
   (`_check_grantable`). Re-sending the stored vendor reads nothing, so a person linked to a
   vendor deactivated later can still be saved with it.
3. **Reactivating a person** linked to an inactive vendor is allowed; the link is history.
4. **Who may link:** the link is part of the person and uses `people:edit`, as the rest of the
   Team record (Q9.4 a). Nothing about it is IT admin's only.
5. **Identity:** the vendor changes neither the login, the roles nor what the person may see.
   The own-person rule (`_is_own`: login, active, sites) does not cover it; a person with
   `people:edit` may set their own vendor, as their own trades.
6. **Who/when:** the link change is stamped on the person (`update_row`: `updated_at`,
   `updated_by`). No separate history (Q9.5 a).
7. **The answer** of `GET /api/masters/people` and of the person `POST` / `PUT` carries
   `vendor_id`, `vendor_name` and `vendor_active` (a boolean, or `null` with no vendor), from
   `_PERSON_SELECT`: `SELECT p.*, v.name AS vendor_name, v.active AS vendor_active FROM people p
   LEFT JOIN vendors v ON v.id = p.vendor_id`. `list_people`'s filter becomes `WHERE p.active =
   1` (with the join, a bare `active` is ambiguous) and its order `ORDER BY p.name, p.id`;
   `_people_out` turns `vendor_active` into a boolean (`None` with no vendor). Every
   reader of the people list sees them (`masters:read`); the link is not personal data.

### 5.3 Locks

The Team module's order is person → trades → site rows → units (`masters.py`, the Team block's
comment). The vendor comes **after the person and before the trades**. The REPEATABLE READ
rule: each check reads with a locking read, never from an earlier plain read.

- **`POST /vendors`:** (1) the insert, autocommit, no transaction (as
  `create_manufacturer`).
- **`PUT /vendors/<id>`** (transaction): (1) the vendor row `FOR UPDATE` (`_lock_row`, 404 when
  missing); (2) the update. It counts nothing and locks no person.
- **`GET /vendors`:** plain read; `people_count` is a subquery (`_VENDOR_SELECT`).
- **`POST /people`** (transaction, as today): (1) the link check of § 5.2 rule 1 (pure); (2) the
  vendor row `LOCK IN SHARE MODE` when rule 2 says the link is new; (3) the trades `FOR UPDATE`
  (`_check_grantable`); (4) the person insert (its foreign key takes a shared lock on the vendor
  row, already held); (5) `person_trades`; (6) the site rows with a login, as today.
- **`PUT /people/<id>`** (transaction): (1) the person row `FOR UPDATE` (`_lock_row`); (2) the
  login save's sites, the own-person 403s and the "Only IT admin can activate or deactivate a
  person with a login" 403, as today; (3) the link check of rule 1 on the locked row and the
  body; (4) the vendor row `LOCK IN SHARE MODE` when the link is new; (5) the trades
  (`_check_grantable`), the site rows, as today; (6) the person update. The vendor checks sit
  with the trades, after the 403s (BR1-03): the vendor is a grant like a trade. The lock order
  (person → vendor → trades) is unchanged.
- **Why share mode:** two engineers linking people to one vendor do not wait for each other,
  and a vendor deactivation (`FOR UPDATE` on the vendor) waits for both. If the deactivation
  commits first, the link check sees `active = 0` (a locking read sees the newest row) and
  refuses. If the link commits first, the deactivation follows and the link stays, which
  § 5.1 allows.
- **No cycle:** no vendor write takes a person lock; a person write takes the vendor after the
  person. The people site-row routes (`put_person_site`, `delete_person_site`) take no vendor.
- **Rollback:** a refusal raises inside `transaction()`, so nothing of the save is kept (the
  trades and site rows included), as today.
- `masters.py`'s docstring gains: "Vendors (S079 § 5.3): a vendor update locks its row alone and
  counts nothing.  A person write that newly links a vendor locks the person, then reads the
  vendor LOCK IN SHARE MODE (person → vendor → trades); no vendor write takes a person, so no
  cycle."

### 5.4 Permissions

| Route or control | Key | Where checked |
|---|---|---|
| `GET /api/masters/vendors` | `masters:read` (every role) | `require_perm` |
| the `phone` field in that answer | `equipment:edit` held at any site (engineer, manager, IT admin; admin by the bypass) | `_vendor_out`: `has_perm("equipment:edit")`; without it the key is absent, as `username` is for non-IT-admin readers |
| `POST`, `PUT /api/masters/vendors…` | `equipment:edit` | `require_perm` (site-scoped key; a vendor is at no site, so the union, as manufacturers) |
| *Add vendor*, *Edit*, the dialog | `equipment:edit` | `VendorsPanel.vue` `canEdit`, as `ManufacturersPanel.vue` |
| the *Vendors* tab | `masters:read` | `MastersView.vue`; Masters itself shows to the holders of `masters:edit`, `equipment:edit`, `people:edit` or `failure_codes:edit` (`stores/navigation.js`) |
| `vendor_id` on a person | `people:edit` | `require_perm` on the people routes |

No new key: `config_rbac.py` and `test_role_matrix` are unchanged. Every role that sees Masters
today also holds `equipment:edit`, so on screen every Vendors reader sees the phone; the mask
matters for the API and for later screens (contracts, R02.1).

### 5.5 Screens

**The Vendors tab** (`VendorsPanel.vue`, mock-up 06):

- Header: "Vendors" with `fa-handshake`; the *Show inactive* switch (off at first); *Add
  vendor* (`canEdit`).
- Table: **Name** (bold) and under it, small and grey, the phone then the note joined by " · "
  (only what is set); **People** right-aligned, the number, or "None" in grey for 0; **Status**
  (Active / Inactive badge); *Edit* (pen, title "Edit", `canEdit`). Ordered by name. Inactive
  rows grey, shown only with *Show inactive*.
- Under the table: "People: the active Team records linked to the vendor. A vendor with no
  people cannot be assigned to tickets. Link one in Team."
- Empty: "No vendors yet. Add the first one with *Add vendor*." (Loading: "Loading…"; a load
  error: the alert with its message, as the manufacturers panel.)
- **The dialog** (`FormModal`, title *Add vendor* / *Edit vendor*, save button as the other
  masters dialogs; `useMasterForm` with `path: "/api/masters/vendors"`, `blank: () => ({ name:
  "", phone: "", note: "" })`, `fromRecord: (v) => ({ name: v.name, phone: v.phone ?? "",
  note: v.note ?? "" })`, `toBody` sending `phone` and `note` as `null` when empty, `label:
  (v) => v.name`):
  - *Name* (`maxlength="100"`), help "The firm, as it should always be spelled, e.g. Atlas
    Copco."
  - *Phone (optional)* (`type="tel"`, `inputmode="tel"`, `maxlength="20"`), help "The firm's
    office number. The breakdown number goes on the contract (Masters › Contracts)." S080
    builds that tab and ships in the same release (BR1-10).
  - *Note (optional)* (`maxlength="255"`), help "What the firm maintains, e.g. Screw
    compressors, MCC2. Do not enter prices here."
  - Each field's refusal beside it (`fieldError`). *Deactivate* / *Reactivate* in the footer
    (`ActiveToggle`, Edit only), as manufacturers. The confirm is `ActiveToggle`'s plain
    "Deactivate <name>? Yes / No", as in every master; no text is added (BR1-02). The action
    is reversible (*Reactivate*), the linked people stay linked, and no refusal follows.
  - After a save: `resetMasters()` and the panel's reload (the composable's `afterSave`).
- The panel loads with `ensureVendors({ refresh: true })`, so the People count is fresh each
  time the tab opens.

**The Team dialog** (`PeoplePanel.vue`):

- *Vendor (optional)*, a select below *Employment*, rendered only while *Contractor* is
  chosen (`v-if`). Options: "No vendor" (value `""`), the active vendors by name, then the
  person's stored vendor when it is inactive, as "<name> (inactive)". Help: "The firm this
  contractor works for. Their tickets then count as the vendor's breakdown calls on its
  contracts." With no vendor rows at all: "No vendors yet; add one under Vendors." The refusal
  of `vendor_id` shows beside it.
- Choosing *Direct employee* sets the vendor to "No vendor" (a `watch` on the employment).
  Choosing *Contractor* again does not bring the old choice back.
- `blank` adds `vendor_id: ""`; `fromRecord` adds `vendor_id: p.vendor_id ?? ""`; `toBody`
  always sends `vendor_id`: the number while *Contractor* and a vendor are chosen, else
  `null`. So a dialog save never meets rule 1's refusal.
- **The change warning** (Q9.5 a), on *Edit person* only, while the stored vendor is set and
  the vendor to be sent differs, below the Employment and Vendor fields, as `alert
  alert-warning py-2 small`:
  - to another vendor: "Their earlier tickets will count for <new> instead of <old>. If the
    person changed firm or employer, add a new Team record for them instead."
  - to none (*No vendor* or *Direct employee*): "Their earlier tickets will no longer count for
    <old>. If the person changed firm or employer, add a new Team record for them instead."
  No extra confirm step; *Save person* saves.
- `reload()` adds `ensureVendors(refresh)` to its `Promise.all`, so a vendor added a minute ago
  is offered.
- **The list:** the Employment cell keeps its badge; for a linked contractor it adds " · <vendor
  name>", and " (inactive)" when `vendor_active` is false.

### 5.6 The database down

The vendor routes use `get_db()` like the other masters: 503 when the database is down. The
Vendors panel shows the load error. The Team panel's `reload` fails as a whole and shows its
load error, as today when the trades fail.

## 6. API

| Route | Key | Body / query | Answer |
|---|---|---|---|
| `GET /api/masters/vendors` | `masters:read` | `include_inactive=1` (else active only) | 200 `{items: [{id, name, phone?, note, active, people_count, created_at, created_by, updated_at, updated_by}], total}`, by name; `phone` only for `equipment:edit` holders; `people_count` = active people with this `vendor_id` |
| `POST /api/masters/vendors` | `equipment:edit` | `{name, phone?, note?, active?}` | 201, the row as in the list (with `phone`); 400 § 5.1; 409 duplicate name |
| `PUT /api/masters/vendors/<id>` | `equipment:edit` | `{name?, phone?, note?, active?}` | 200, the row; 400 § 5.1; 404 `{"error": "Not found"}`; 409 duplicate name |
| `POST /api/masters/people` | `people:edit` | adds `vendor_id?` | 201, the person with `vendor_id`, `vendor_name`, `vendor_active`; 400 § 5.2 |
| `PUT /api/masters/people/<id>` | `people:edit` | adds `vendor_id?` | 200, as above; 400 § 5.2 |
| `GET /api/masters/people` | `masters:read` | unchanged | each item adds `vendor_id`, `vendor_name`, `vendor_active` |

Errors have the shape `{"error": <text>, "field": <field>}` (`ApiError`). A 403 is the app's
`FORBIDDEN_TEXT`; a 503 the database-down answer.

## 7. Design decisions

- **D1. A separate `vendors` table** (Q9.1 a). A maker describes a model; a vendor holds a
  contract and sends people. Rejected: one `firms` table with roles, which renames S012's
  production table.
- **D2. Name, phone, note, active** (Q9.2 a plus a phone, KLA). Rejected: email, address and
  GSTIN (accounts keep them).
- **D3. The phone goes to the holders of `equipment:edit` only** (as D10's rule for the
  call-out number: the people who deal with the vendor). Recommended because Yantra's rule is
  that the engineer calls the vendor: a technician who reads a firm's number calls it
  directly, and D10 keeps the breakdown line from technicians for the same reason. It costs
  nothing on screen today (every Masters user holds `equipment:edit`). Rejected: every reader
  (`masters:read`), which is simpler and an office number is not sensitive, but it lets the
  number reach technicians and operators through the API and later screens. KLA may choose it
  (§ 9 Q1).
- **D4. Edit with `equipment:edit`, read with `masters:read`, link with `people:edit`; no new
  key** (Q9.4 a). Rejected: a `vendor:edit` key with the same holders.
- **D5. Deactivation allowed with links, links kept.** Rejected: the manufacturer's refusal
  while people are linked; it would force unlinking, which erases the history R02.6 reads.
- **D6. The API refuses a direct employee with a vendor; it does not clear the vendor
  silently.** No link is lost without the user seeing it; the dialog clears it in view.
  Rejected: the API dropping `vendor_id` on *direct*.
- **D7. The link is new only when it differs from the stored one**, so only a new link must
  be to an active vendor (the S063 class-category rule). Rejected: checking the vendor on every
  save, which would block editing the name of a person whose firm was deactivated.
- **D8. Refusals in the Team dialog's own form** (400, "That vendor no longer exists. Reload
  and try again."; "Vendor <name> is inactive. Choose another vendor or reactivate it."), as a
  trade. Rejected: the model's 409 "The vendor is inactive", a second style in one dialog.
- **D9. Share lock on the vendor.** Rejected: `FOR UPDATE` (`_lock_active_parent`), which
  makes two person saves for one vendor wait for each other for no gain.
- **D10. The vendor tab after *Trades*, before *Team*** (mock-up 06), next to the people it
  groups.
- **D11. A warning, not a confirm, when a link changes** (Q9.5 a asked for a warning). Rejected:
  a second confirm button; the warning shows before *Save person* in the same view.
- **D12. The phone as text, not a `tel:` link.** Out of scope; one line to add later.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v42.py`)

Helpers from `tests.test_migration_v20` (`_migrate`, `_recreate`, `_run`, `_schema`) and
`tests.test_migration_v36` (`_keys`, `_foreign_keys`); `V41` = `range(20, 42)`, `V42` =
`range(20, 43)`, `VERSIONS = list(range(20, 43))`.

- `test_a_fresh_database_gets_v42`: `vendors` empty, its columns and `uq_vendors_name`;
  `people.vendor_id` nullable, `ix_people_vendor`, `fk_people_vendor` → `vendors`,
  `chk_people_vendor` present.
- `test_a_v41_database_keeps_every_person`: a direct person with a login, a contractor and an
  inactive person; after v42 every column of before is equal and `vendor_id` is NULL.
- `test_the_check_keeps_a_vendor_to_a_contractor`: a direct person with a vendor → error
  4025; a contractor with one → stored; setting a linked contractor to direct → 4025.
- `test_an_unknown_vendor_is_refused`: error 1452.
- `test_the_name_is_unique_in_any_case`: "Atlas Copco" then "atlas copco" → 1062.
- `test_a_rerun_changes_nothing` (`_schema()` equal) and
  `test_a_half_applied_v42_adds_the_check` (the CHECK dropped, v42 again → present).

### 8.2 Backend API

Each test makes its own vendors (`make_vendor`, names from `uniq`), so runs do not clash in the
kept worker database. Phone values are fake (`"+91 00000 00000"`).

`backend/tests/test_vendors_api.py`:
- `TestVendors::test_create_list_and_edit` (name, phone, note, who/when, `people_count` 0).
- `TestVendors::test_duplicate_by_case_or_by_repeated_spaces_is_409` (the § 5.1 text).
- `TestVendors::test_listed_by_name_and_inactive_on_request`.
- `TestVendors::test_bad_input_is_400` (parametrized: name missing, `""`, 101 characters, `5`;
  phone `5`, 21 characters, the refused examples of § 5.1; note 256 characters, `[]`; active
  `"yes"`; body `[]`), each with its field and text.
- `TestVendors::test_put_without_a_field_keeps_it_and_null_or_empty_clears_phone_and_note`.
- `TestVendors::test_unknown_is_404`.
- `TestVendors::test_deactivating_with_linked_people_is_allowed_and_links_stay`.
- `TestVendors::test_people_count_counts_active_linked_people_only` (one active, one inactive
  linked person → 1).
- `TestPhoneReaders::test_phone_only_for_equipment_edit_holders` (parametrized: operator,
  technician, supervisor, storekeeper → no `phone` key; engineer, manager, IT admin → present).
- `TestPermissions::test_every_role_reads_the_list`;
  `TestPermissions::test_only_equipment_edit_holders_write` (operator, technician, supervisor,
  storekeeper → 403 on `POST` and `PUT`; engineer, manager → 201).
- `TestPermissions::test_the_list_is_503_while_the_database_is_down` (`db_down`).

`backend/tests/test_people_api.py`, class `TestVendorLink`:
- `test_a_contractor_linked_on_create_shows_the_vendor` (`vendor_id`, `vendor_name`,
  `vendor_active` true; in the list too).
- `test_direct_with_a_vendor_is_400_on_create`.
- `test_each_put_shape` (parametrized over the six rows of § 5.2 rule 1, with status, field and
  the stored row afterwards).
- `test_bad_vendor_id_is_400` (`true`, `"3"`, `0`).
- `test_unknown_vendor_is_400`.
- `test_inactive_vendor_refused_for_a_new_link_kept_for_an_existing_one` (re-sending it: 200;
  a direct `{name}` save of that person: 200; the list shows `vendor_active` false).
- `test_reactivating_a_person_linked_to_an_inactive_vendor_is_allowed`.
- `test_a_refused_link_writes_nothing_else` (the trades sent in the same body are not saved).
- `test_a_technician_cannot_link` (403, `people:edit`).

`backend/tests/test_masters_core.py`: `TestVendor` (the name's trimming and collapsing, its
bounds; each phone example of § 5.1; the note's bounds; required on create only) and
`TestVendorLink` (`vendor_link_error` for direct/contractor × `None`/an id × sent/not sent:
the `(field, message)` pair or `None`).

Existing tests: none breaks by the facts run and `git grep` (no test asserts the people
item's whole key set; `test_site_roles_api.py:66` checks a unit summary only). The coder runs
`test_people_api.py`, `test_site_roles_api.py`, `test_models_api.py`, `test_masters_api.py`,
`test_masters_core.py`, `test_rbac.py` and the migration tests.

### 8.3 Frontend unit

`frontend/tests/masters.test.js`: the "fetches each list from its own path, inactive included"
case adds `ensureVendors` (`/api/masters/vendors?include_inactive=1`); a `resetMasters` case
clears `vendors`.

### 8.4 Automated (e2e, targeted: `masters.spec.js`, `floor.spec.js`, `tickets-raise.spec.js`, `screens.spec.js`)

The e2e seed has no vendors; each test makes its own, named with the test's tag
(`propertyTag(testInfo)`), and looks for its own rows only. Every dialog opened calls
`expectDialogFits`. No test is `@device`: none checks a layout.

- The section loop ("the … section opens, and an empty … is refused beside its field") gains
  `{ button: "Vendors", add: "Add vendor", api: "/api/masters/vendors", person: "engineer",
  message: "Name is required", before: … }`, the `before` making one vendor by API.
- **important** `S079: engineer adds a vendor with a phone and a note; the list shows them and
  People None; the same name in another case is refused beside Name` (the § 5.1 text;
  `consoleWatch.allowFailedRequest("/api/masters/vendors", 409)`). The section-loop entry gets
  its 400 allowance from the loop itself.
- **important** `S079: engineer links a contractor to a vendor in Team; the list shows
  Contractor · the vendor, and Vendors counts 1 person` (a contractor made by API; *Edit*;
  select the vendor; save; Team row text; *Vendors* row People "1").
- **important** `S079: changing a linked person's vendor warns; Direct employee hides and clears
  the vendor and the save unlinks` (the warning texts of § 5.5; the select gone after *Direct
  employee*; the row shows "Direct" alone; *Vendors* People "None").
- `S079: a deactivated vendor is not offered for a new link; a person linked to it keeps it as
  (inactive)` (made by API: two vendors, one person linked to the first; the first
  deactivated in the dialog; Team dialog of a new contractor lacks it; the linked person's
  select shows "<name> (inactive)"; the list shows " (inactive)").
- Lines that use the Team dialog and stay as they are, checked by the targeted run:
  `tickets-raise.spec.js` (S017 test: `getByRole("button", { name: "Team" })`,
  `getByLabel("Name")`), `floor.spec.js` (S064 full-screen dialog), `masters.spec.js`
  (`openTeam`, `openPersonDialog`, the S064 Team tests). None reads the employment badge. The
  new tab adds a button `"Vendors"`; no test counts the Masters toolbar's buttons.

The coder runs the targeted specs while coding and the whole suite (Normal) once at the end.
No shared frontend file (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth
store, `e2e/support/`) changes.

### 8.5 On a real device

None. Every check here is one a browser engine can judge; the phone field's keyboard is a
browser `inputmode`, and no call is placed.

### 8.6 Acceptance

`tooling\run-tests.bat` green (run name from the orchestrator); `npx vite build` green; the
targeted browser specs green, then the whole suite at Normal once; `tooling\schema-docs.bat
check` exits 0; `docs/Plant-Facts.md` § 4 lists the five vendors with no number.

## 9. Open questions and assumptions

Q1–Q3: **taken as recommended by the orchestrator under the delegation of 30-10-2026; KLA may
override at gate B.**

- **Q1. Who reads the vendor's phone?** Taken: (a).
  - **(a) The holders of `equipment:edit`: engineers, managers, IT admin — recommended (D3).**
    Technicians go through the engineer, as for the call-out number (D10). No change on screen
    today.
  - (b) Every reader (`masters:read`). Simpler; the number may reach technicians and operators
    once vendors show outside Masters (contracts, R02.1).
- **Q2. Toyota Material Handling for two companies:** one vendor row, or one per company? The
  brief assumes **one row** (one firm; the contracts, one per company and site, come in S080).
  Taken: one row.
- **Q3. A § SMTW-Review point** for `.claude/CLAUDE.md`, proposed: "**Vendor link (S079):** a
  person has a vendor only as a contractor (`chk_people_vendor`, and the API's refusal through
  `vendor_link_error`); a person write that newly links a vendor reads it `LOCK IN SHARE MODE`
  after the person lock; the vendor's phone goes only to `equipment:edit` holders
  (`_vendor_out`). A new person write path must keep all three." Taken: the coder adds it
  (§ 3 Docs).
- **Assumption:** about five to ten vendors, so no search on the tab.
- **Assumption:** the plant's numbers fit 6–15 digits (landline with STD code, mobile, or
  toll-free); a number with an extension goes in the note.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): § 5.1 keeps 6–15 digits and 20 characters; allows digits, spaces, `-`, `.`, `(` `)` and a first `+`; the grouping regex is dropped; new message and examples; S080 reuses `_parse_phone`. |
| BR1-02 minor | Accepted (a): § 5.5 says the confirm is `ActiveToggle`'s plain "Deactivate <name>?"; no text added. |
| BR1-03 minor | Accepted (a): § 5.3 *PUT /people*: the vendor checks come after the own-person and active 403s, before `_check_grantable`; the lock order is unchanged. |
| BR1-04…BR1-10 | Nits accepted: `vendor_link_error` returns `(field, message)` (§ 3, § 5.2, § 8.2); one warning sentence "changed firm or employer" (§ 5.5); the mock-up "Fact" bullet dropped (§ 9); Plan.MD anchored by name (§ 3); the 409 `allowFailedRequest` named (§ 8.4); `"vendors"` after `"people"` in `_TABLES` (§ 3); the phone help names *Masters › Contracts*, S080 in the same release (§ 5.5). |

Q1–Q3 (§ 9) taken as recommended by the orchestrator under KLA's delegation of 30-10-2026.
