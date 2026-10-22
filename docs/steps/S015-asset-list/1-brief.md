```
Step: S015 — Printable asset list
Doc: brief
Author: Planner (Opus)
Date: 18-10-2026 (revised 18-10-2026 after brief-review r1; gate A 20-10-2026)
Track: light (full at review; set light by the user at gate A, 20-10-2026)
Baseline: 90284ec + uncommitted S016 (stale brief check s1, 20-10-2026)
Status: Committed 6c771e1; checks: 1 auto; left: 2 print checks for IT Admin (device-checks rows 3, 4) (approved 20-10-2026 by KLA)
```

# S015 — Printable asset list

A printed list of the equipment at a site or unit, for two uses on the floor:
the maintenance team's physical check that the register matches what stands
there, and the accounts' fixed-asset verification, which is the same walk
(Plan.MD § 4.1, *Verification rounds*). It is the paper form of that walk until
the scan-based verification round exists.

User decisions (18-10-2026, before the brief):
1. **Both uses, as a choice:** a plain register, or the same list with
   **checklist columns** to fill by hand. One switch on the print page.
2. **No fixed-asset number from the accounts books:** the Yantra code is enough;
   no new field.
3. **Rows:** equipment by default; a switch adds its **parts** (component-units
   and components), indented under each machine.
4. **Print page only:** no CSV or Excel. Export to Excel stays with the phase 5
   reports (Plan.MD § 5).

**Track: light** (the user's choice at gate A, 20-10-2026). It was reviewed on
the full track because it adds a report endpoint beyond plain CRUD that applies
unit access. The access check itself is reused, not new. No migration, no change
to data, no RBAC change, no new dependency.

**Depends on:** no other step's code. S016 is uncommitted in the working tree
(it edits no file of this brief); the S015 diff is its impl report's file list (BS1-01).

## 1. What will be built

1. **Print asset list** button on the equipment list. It opens the print page in
   a **new tab** with the list's current **site, unit, class, type, status,
   criticality** filters and the **show scrapped** switch. The search text and
   the level picker are not passed (§ 4).
2. **The print page** (`/asset-list`), A4 portrait:
   - **one section per unit**, each starting on a new page, ordered by site
     code, then unit code. A unit with no matching equipment is left out;
   - a **section header**: site code and name, unit code (`SITE.UNIT`) and
     name, a **filter line** (e.g. "Class: RPP · Status: In service", or "All
     equipment" when nothing is filtered; site and unit are not repeated on
     it), **printed on** (IST, `DD-MM-YYYY HH:MM`) and **printed by** (the
     user's name);
   - **one row per item**, ordered by code. **#** is a running number of the
     **machines** within the unit; parts have no number, so the last # equals
     the machine count (BR1-02);
   - **plain register** (checklist off): one line per item, **nine columns**:
     **#**, **Code**, **Name**, **Class · Type**, **Model** (manufacturer and
     designation), **Serial no.**, **Year**, **Criticality**, **Status**;
   - **checklist** (switch on): **two lines per item** (BR1-01). Line 1: **#**,
     **Code**, **Name**, **Found** (an empty box to tick), **Remarks** (empty,
     at least 60 mm wide). Line 2, in small grey type under the name: Class ·
     Type · Model · Serial no. · Year · Criticality · Status. Under the table,
     a footer: *Checked by ____ Date ____ Signature ____* and *Verified by
     (accounts) ____ Date ____ Signature ____*;
   - **empty values:** no type → the class alone (as the list shows it); no
     serial number or year → blank;
   - **with parts**: each machine's parts follow it, indented one step per
     level (component-unit, then its components), each group ordered by code.
     Scrapped parts are left out unless *show scrapped* is on;
   - **a count line** at the end of each section: "42 equipment, 118 parts"
     (the parts count only when parts are shown);
   - the table header repeats on every printed page of a long unit;
   - two switches on the screen (not printed): **Include parts** and
     **Checklist columns**, and a **Print** button. Changing a switch updates
     the page's link, so a reload keeps them;
   - a note on the screen: print in portrait, at 100 %.
3. **Too many rows:** above **3000 rows** (after parts are added), the page shows
   "Too many rows — narrow the list by site or unit" and no sheet. The plant has
   about 500 machines (Plant-Facts), so the cap only stops a runaway print.

**Out of scope:**
- the scan-based verification round (recording found / not found in Yantra);
- a fixed-asset number field (decision 2);
- CSV or Excel export (decision 4);
- a class filter that finds parts of that class inside other machines. The
  filters choose machines; parts come only with their machine (§ 4);
- page numbers printed by Yantra (not needed, user 20-10-2026). The browser's
  own header and footer can print them;
- a printed list per model or manufacturer.

## 2. Standards and practice

- **ISO 55001 § 7.5 (information requirements)** asks the organisation to
  decide what information it needs about its assets, and to set and keep its
  **quality**: accuracy, completeness and timeliness. A register that is never
  checked against the floor has no known accuracy. **ISO 55002**, the guidance
  to 55001, says on § 7.5 that asset data should be checked for accuracy. In
  practice that means periodic physical verification, the same walk the
  accounts call fixed-asset verification. This list is that check in paper
  form: the register is printed, someone walks the unit, differences are
  written on the sheet and then corrected in Yantra (BR1-07).
- **The accounts' physical verification** (BR1-07). **CARO 2020 does not apply**
  to any of the businesses (user, 20-10-2026). The tax audit (Income-tax Act
  § 44AB, Form 3CD) works from a fixed-asset register, and the auditor may ask
  how that register was verified. The signed checklist is the evidence of the
  walk.
- **ISO 14224 § 8 (equipment data)** names the attributes that identify an item:
  tag number, equipment class and type, manufacturer, model designation, serial
  number, and year. The list prints exactly those, plus criticality and status,
  so an auditor can tell two similar machines apart by their plates.
- **ISO 27001 A.5.9 (inventory of information and other associated assets):**
  the equipment register is the asset inventory, and a periodic check is the
  control that keeps it true. The printout holds no personal data apart from
  the printer's name, and it is read-only, so unit access is all the handling
  it needs.
- **EN 13306** calls everything on the list an *item*. The tree's levels
  (equipment, component-unit, component) are ISO 14224's taxonomy levels 6–8.
  The same words are used on the page.
- **TPM** (`Maintenance-Philosophy.md`): knowing exactly what is on the floor
  comes before planned maintenance can cover it. A machine that is on the floor
  but not in the register gets no PM, which is the forgotten-machine case
  (Plan.MD § 4.1, *Maintenance strategy*).

## 3. Where

### Backend
- **`backend/asset_list_core.py`** (new, pure):
  - `build_asset_list(machines, parts, include_scrapped)`. It takes the machine
    rows and the part rows (plain dicts) and returns `(result, None)` or
    `(None, TOO_MANY_ROWS)`, as `labels_core.expand_selection` does (BR1-04).
    `result` is `{units: [{site_code, site_name, unit_code, unit_name, rows,
    machine_count, part_count}], total_rows}`:
    - units ordered by site code, then unit code;
    - in each unit, machines by code, each followed by its parts depth-first;
    - each row carries `depth` (0 for the machine, 1 for a component-unit,
      2 for a component), and `number`, the running machine number within the
      unit. Parts carry `number: None`;
    - scrapped parts are dropped unless `include_scrapped` is on;
    - a part whose machine is not in `machines` is ignored. This guards the
      core only; the route cannot produce such a part, since it asks for parts
      by machine id, so no API test is needed (BR1-11);
    - the total after parts is checked against `MAX_ASSET_LIST_ROWS`;
  - `MAX_ASSET_LIST_ROWS = 3000` and `TOO_MANY_ROWS` (the message).
- **`backend/equipment.py`:**
  - **`_list_filters()`** (new; no argument): the site, unit, class, type,
    status, criticality and scrapped conditions, **moved out of
    `list_equipment`**, which now calls it. It reads `request.args` through
    `int_arg` / `enum_arg` as now, so the 400 messages and their `field` are
    unchanged (BR1-08). `list_equipment` keeps its search and level
    conditions. The list and the print then use one filter code (DRY), not two
    copies.
  - **`GET /api/equipment/asset-list`**, `@require_perm("equipment:read")`.
    Query: the filters of `_list_filters`, plus `with_parts`, read as
    `request.args.get("with_parts") == "1"`, as `include_scrapped` is
    (BR1-06). It:
    1. applies unit access as the list does: `accessible_unit_ids(cur)`; an
       empty set gives an empty result at once, with no query (an empty `IN ()`
       is an SQL error); `None` (admin, `equipment:read_all_units`) means all
       units;
    2. selects the **machines**: `e.level = 'equipment'` with the filters,
       through `NODE_JOINS`, with `LIMIT MAX_ASSET_LIST_ROWS + 1`. Above the cap
       it refuses with **400 `TOO_MANY_ROWS`** at once. The constant is read
       through the module (`asset_list_core.MAX_ASSET_LIST_ROWS`), so a test
       that patches it reaches both checks (BR1-04). The columns are
       `_NODE_COLUMNS` (which already hold `serial_no` and `year`) plus `s.name
       AS site_name, u.name AS unit_name`;
    3. **no machines** → `{units: [], total_rows: 0}` and no parts query;
    4. with parts, selects the parts **in one query**: `e.parent_id IN
       (machine ids) OR p.parent_id IN (machine ids)`. Only status is
       filtered, in the core; the other filters apply to the machine (§ 4);
    5. calls `build_asset_list`; its `TOO_MANY_ROWS` → 400;
    6. returns `{units, total_rows, printed_at, printed_by}`:
       - `printed_at` is `datetime.now(IST).isoformat(timespec="seconds")`, the
         API's usual datetime shape (`YYYY-MM-DDTHH:MM:SS+05:30`; `jsonify` alone
         would give an RFC 822 date, BS1-02). The page formats it with the existing
         `formatDateTime`, so it uses the same helper as every other date
         (BR1-09);
       - `printed_by` is `g.user["name"]`, or `actor()` (the username) when the
         name is empty. Keycloak local users may have no name (BR1-09).
  - Rows use the existing `_summary` shape (code, name, class code, type name,
    model label, effective criticality, status), plus `serial_no`, `year`,
    `depth` and `number`.
- No change to `config_rbac.py`.

### Frontend
- **Router:** `/asset-list` → `views/AssetListPrintView.vue` (new), title
  "Asset list".
- **`views/AssetListPrintView.vue`** (new):
  - reads the filters and the two switches from the query, calls the endpoint,
    and loads `ensureEquipmentClasses()` / `ensureEquipmentTypes()` for the
    filter line;
  - one `<section>` per unit (`break-before: page` on all but the first), with
    a `<table>` and its `<thead>` (Chrome and Edge repeat it on each printed
    page), then the count line and, with the checklist, the footer;
  - 9 pt type;
  - the `@page { size: A4 portrait; margin: 12mm }` rule is **added on mount
    and removed on unmount**, as `LabelsPrintView` does. A static rule would be
    in the bundle and set the paper of every page the user prints (BR1-05).
    The 12 mm margin also leaves room for the browser's own header and footer;
  - the switches and the Print button are `.no-print`;
  - a 400 shows the server's message, an empty result "Nothing to list for
    these filters", and both show no sheet.
- **`frontend/src/utils/assetList.js`** (new, pure; BR1-03, BR1-06):
  - **The print link uses the list's own query keys:** `site_id`, `unit_id`,
    `class_id`, `type_id`, `status`, `criticality`, `scrapped=1`, plus
    `parts=1` and `check=1` for the switches (as `/labels?parts=1`).
  - `assetListPath(listQuery, withParts, checklist)` takes the list's
    `route.query` and keeps only those keys, dropping `level`, `q` and `page`.
  - `parseAssetListQuery(query)` → `{params, withParts, checklist}`. It drops
    unknown keys; the switches default to off. It sends `include_scrapped=1`
    when `scrapped=1` **or** `status=scrapped`, which is the list's own rule.
    Otherwise a bookmarked `status=scrapped` would print an empty sheet.
  - `filtersLabel(params, lookups)`: the filter line, from the class and type
    stores and `STATUS_LABELS` (`utils/equipmentLabels.js`). It names Class,
    Type, Status, Criticality and "scrapped included"; with no filter it reads
    "All equipment".
- **`views/EquipmentView.vue`:** the **Print asset list** button beside *Print
  labels*. It opens `assetListPath(...)` in a new tab (base pattern
  § Print / Export Views), and the list keeps its state.
- The existing print reset in `assets/main.css` (`.no-print`, app shell
  unclipped, no sidebar margin) is used as it is.

### Tests
- Pure (`backend/tests/test_asset_list_core.py`):
  - units ordered by site, then unit; machines by code; parts depth-first under
    their machine, by code;
  - depth 0 / 1 / 2; the running number counts machines, and parts carry none;
  - scrapped parts dropped, or kept with `include_scrapped`;
  - a part with no machine in the set is ignored;
  - counts per unit;
  - the total cap → `TOO_MANY_ROWS`;
  - empty input → no units.
- API (`backend/tests/test_asset_list_api.py`):
  - filters (site, unit, class, status, criticality, scrapped) select the
    machines;
  - with parts: the parts of the chosen machines come, whatever their class;
  - no machines, with parts on → 200, empty;
  - a user sees only their units; a user with no units gets an empty result
    with no SQL error; admin and `equipment:read_all_units` see all;
  - over the cap → 400, by patching `asset_list_core.MAX_ASSET_LIST_ROWS` down,
    once for the machines alone and once for the total after parts;
  - `printed_by` and `printed_at` are present; `printed_at` matches
    `YYYY-MM-DDTHH:MM:SS+05:30` (BS1-02).
- The existing list tests (`TestListing`, `TestUnitAccess`) pass unchanged,
  which covers the `_list_filters` move (BR1-08).
- Frontend (vitest, `assetList.test.js`):
  - `parseAssetListQuery`: unknown keys dropped; switches default off;
    `status=scrapped` alone → `include_scrapped=1`;
  - `assetListPath`: `level`, `q` and `page` dropped;
  - `filtersLabel`: the words, and "All equipment".

## 4. Rules

- **The filters choose machines.** Site, unit, class, type, status and
  criticality apply to the equipment level. *Include parts* adds every part of
  each chosen machine, whatever the part's own class or grade. An auditor counts
  machines; the parts are there so the walker can check that a press still has
  its power pack. Finding all compressors at every level is a different
  question (§ 1, Out of scope).
- **Scrapped:** with *show scrapped* off (the default), scrapped machines and
  scrapped parts are left out. Out-of-use and standby items are listed: they
  are still on the floor and in the books.
- **Search and level are not passed.** A search narrows the list by words in a
  name or notes, which does not belong on an audit sheet. The page's header
  shows the filters that were applied, so the sheet says what it covers.
- **Who may print:** whoever may see the equipment, by unit access, as the
  list. Printing changes nothing and writes **no equipment event**. Like every
  API request, it is a sighting in the S013 access log (BR1-10).
- **The unit is the machine's unit.** Parts have none of their own (S002), so a
  part is always printed under its machine's unit.
- **Dates** are IST, `DD-MM-YYYY HH:MM`.

## 5. API

| Method & path | Access |
|---|---|
| `GET /api/equipment/asset-list?site_id&unit_id&class_id&type_id&status&criticality&include_scrapped=1&with_parts=1` → `{units, total_rows, printed_at, printed_by}` | `equipment:read`, rows limited to the user's units, as `GET /api/equipment/` |

The print page's own link is `/asset-list?site_id&unit_id&class_id&type_id&status&criticality&scrapped=1&parts=1&check=1`
(the list's keys; § 3, `utils/assetList.js`).

## 6. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| A new read endpoint with no paging, capped at 3000 rows | The print needs every row of a unit at once; one call, one query per level | Looping over the paged list from the browser (logic in the frontend, many calls) |
| The filter code moved to `_list_filters`, shared by the list and the print | One place decides what a filter means; the print can never disagree with the list (DRY) | A second copy of the filter code in the new route |
| Filters choose machines; parts follow their machine | Matches what an audit counts, and keeps the query simple and readable | Applying each filter at every level (a part could appear without its machine) |
| Grouping, ordering and the total cap in a pure core | Testable without a DB (CLAUDE-COMMON *Pure core, thin shell*) | Ordering in SQL with a recursive sort key (harder to read and test) |
| One page with two switches (parts, checklist) | Both uses from one screen, as decided; the switches live in the link, so reload and Back work | Two separate print pages |
| A4 portrait, 9 pt; nine columns on one line for the plain register, **two lines per item with the checklist** (BR1-01) | A clipboard sheet is portrait. Nine columns fill the 186 mm width, so Found and a 60 mm Remarks column only fit if the details move to a second line | Landscape for the checklist (awkward on a clipboard, two paper sizes on one page); dropping Class and Model from the checklist (the auditor needs them to tell machines apart) |
| # counts machines only (BR1-02) | The last # is the machine count the accounts compare | Numbering every row (the last # mixes machines and parts) |
| A page per unit, with a signature footer per unit | One unit is one walk and one signature; a sheet can be handed to the unit's supervisor | One continuous list for the site (one signature covers areas nobody walked) |
| `printed_at` and `printed_by` from the backend; the time in the API's usual shape, formatted by the page | The sheet is evidence, so the time is the server's IST time, not the browser's clock. The usual shape keeps one date helper (BR1-09) | Formatting the time in the browser from its own clock; a pre-formatted string (a second date format in the API) |
| The filter line built in the frontend from the masters stores and `STATUS_LABELS` (BR1-03) | The words already live there; the sheet and the screen use the same vocabulary | Backend lookups plus a second copy of the status words |
| Search text not passed | An audit sheet covers a set defined by filters, not by words | Passing `q` (an odd-looking subset, hard to state on the header) |

## 7. Tests and acceptance

See § 3 Tests.

### Manual checks
Important:
- [ ] Print one unit with **Checklist columns** on the office printer, A4
  portrait at 100 %. No column is cut off at the right, the Remarks column is
  wide enough to write in, and the signature footer is on the sheet.
- [ ] Print a unit long enough for two pages. The table header repeats on page
  2, and the next unit starts on a new page.
- [ ] With **Include parts**, a press shows its component-units and components
  indented under it, and the count line reads "n equipment, m parts".

Also:
- The header shows the site, unit, filters, printed on (IST) and printed by.
- Switches and the Print button do not print; reload keeps the switches.
- A user limited to one unit sees only that unit's sections.
- Filters that match nothing show "Nothing to list for these filters".
- After the print page, printing another screen with Ctrl+P is not forced to
  A4 portrait (the `@page` rule is removed).
- On production, *Printed by* shows the person's name (the token's `name`
  claim), not the username (BR1-12).

### Acceptance
- `tooling/run-tests.bat` green, the frontend build clean.

## 8. Open questions and assumptions

1. ~~**Page numbers.**~~ Decided 20-10-2026: not needed; Yantra prints none.
2. **Assumption:** the accounts' verification accepts the Yantra code and the
   serial number as the item's identity (decision 2). If the accounts later
   need their own asset number on the sheet, that is a new field and a new
   step.
3. ~~**CARO 2020.**~~ Decided 20-10-2026: not applicable.
4. **Assumption:** 9 pt type is readable on the floor. If not, the print goes
   to 10 pt; the checklist's two-line rows already leave room for that.

## 9. Amendments

(none)

## Gate A — 20-10-2026 (KLA)

Approved. At the gate: CARO 2020 is not applicable (§ 2 rewritten); track set to
light; page numbers not needed. Not to be built until the user asks.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 18-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 Remarks cannot fit with the checklist on | minor | **Accepted** (option 1): two lines per item in checklist mode, Remarks ≥ 60 mm; nine columns stated (§ 1, § 3, § 6) |
| BR1-02 does # count parts | minor | **Accepted** (option 1): machines only, parts `None` (§ 1, § 3, § 6, tests) |
| BR1-03 who resolves the filter names | minor | **Accepted** (option 1): `filtersLabel` in `utils/assetList.js` from the stores and `STATUS_LABELS`; no `filters` in the API; core loses `filters_label` (§ 1, § 3, § 5, § 6) |
| BR1-04 cap test cannot reach the cap | minor | **Accepted** (option 1): total check in the core returning `(None, TOO_MANY_ROWS)`; early check reads the constant through the module; `LIMIT MAX + 1`; no machines → no parts query; tests added (§ 3) |
| BR1-05 static `@page` leaks | minor | **Accepted**: added on mount, removed on unmount, as `LabelsPrintView`; 12 mm margin kept for the browser footer; plain check added (§ 3, § 7, § 8) |
| BR1-06 query keys and scrapped mapping | minor | **Accepted**: the list's keys plus `parts` / `check`; `scrapped=1` or `status=scrapped` → `include_scrapped=1`; `with_parts == "1"`; vitest cases (§ 3, § 5) |
| BR1-07 standards corrections | minor | **Accepted**: ISO 55001 § 7.5 information requirements; ISO 55002 wording; SMTW partnership → § 44AB, SSVT → CARO unless small; ISO 27001 A.5.9 added (§ 2, § 8) |
| BR1-08 `_list_filters()` reads the request | nit | **Accepted**: no argument; 400s unchanged; existing list tests cover the move (§ 3) |
| BR1-09 `printed_at` shape, `printed_by` fallback | nit | **Accepted**: API datetime shape, formatted with `formatDateTime`; fallback on an empty name (§ 3, § 6) |
| BR1-10 "not logged" | nit | **Accepted**: "no equipment event"; the access log still records the request (§ 4) |
| BR1-11 small § 3 corrections | nit | **Accepted**: only site and unit names are new columns; nulls stated; the orphan-part guard is core-only (§ 1, § 3) |
| BR1-12 production check of *Printed by* | nit | **Accepted**: plain manual check added (§ 7) |

### Stale brief check s1 — `2-brief-review-s1.md` (Fable), answered 20-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BS1-01 "Depends on" stale; S016 uncommitted in the tree | nit | **Accepted**: Depends on reworded; `Baseline:` 90284ec + uncommitted S016 |
| BS1-02 `printed_at` shape comes from `isoformat`, not `jsonify` | nit | **Accepted**: `isoformat(timespec="seconds")` stated; API test asserts the shape (§ 3, tests) |
