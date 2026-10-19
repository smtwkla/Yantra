```
Step: S015 — Printable asset list
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

Reviewed against: a2190f3 + uncommitted S022 (tooling/deps and docs only; nothing the brief touches)

# S015 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** The four user decisions
(checklist columns as a switch, no fixed-asset number, parts as a switch, print
page only) are each implemented where they belong, the access check is the
register's own, and the shape — a capped read endpoint, grouping in a pure core,
one print route in a new tab — follows the base and S014. The findings below are
rules the coder would otherwise have to decide alone (the running number, the
filter line, the query keys), one layout sum that does not add up (the Remarks
column with the checklist on), a test that would not reach the cap as written,
and three corrections to the standards section.

Reviewed: the brief; `docs/Plan.MD` § 2, § 3, § 4.1, § 4.6, § 5, § 8;
`docs/Maintenance-Philosophy.md`; `docs/Plant-Facts.md`;
`.claude/SMTW-WebApp-Base.md` (print / export views, timezone policy, design
tone); `CLAUDE-COMMON.md`; `CLAUDE.md`; `docs/steps/README.md`; the code at
a2190f3: `backend/equipment.py`, `labels_core.py`, `auth_utils.py`,
`config_rbac.py`, `api_common.py`, `masters_core.py`, `equipment_core.py`,
`tests/conftest.py`, `tests/test_equipment_api.py`, `tests/test_labels_api.py`;
`frontend/src/router/index.js`, `stores/navigation.js`, `views/EquipmentView.vue`,
`views/LabelsPrintView.vue`, `utils/labelSheets.js`, `utils/datetime.js`,
`utils/equipmentLabels.js`, `assets/main.css`, `tests/labelSheets.test.js`;
the S014 brief review r1 (for the house pattern).

---

## Findings

### BR1-01 — `minor` — With the checklist on, the Remarks column cannot be "wide enough to write in" as laid out

**Problem.** § 1 and § 6 say nine data columns plus **Found** and **Remarks**
fit across 186 mm at 9 pt (§ 6 says "the ten columns"; it is nine plain, eleven
with the checklist). At 9 pt a character is about 1.6 mm. Realistic widths:
`#` 6, Code 16 (12-character codes), Name 32, Class · Type 28, Model 28
("Atlas Copco GA37"), Serial 20, Year 9, Crit. 7, Status 16 ("Out of use") =
162 mm, plus cell padding ≈ 180 mm. That leaves about 6 mm for a Found box and
Remarks together. Handwriting needs 40 mm or more. The first important manual
check ("the Remarks column is wide enough to write in") would fail on the
first print, and the coder would then pick a layout alone.

**Why it matters.** The checklist sheet is the accounts' evidence; if Remarks is
unusable the walker writes on the back and the discrepancy never reaches
Yantra.

**Options.**
1. **Two-line rows when the checklist is on.** Line 1: `#`, Code, Name, Found,
   Remarks (Remarks ≥ 60 mm). Line 2, small grey text under the name: Class ·
   Type · Model · Serial · Year · Crit. · Status. Nine columns stay on one line
   when the checklist is off. Rows are about twice as tall in checklist mode; a
   50-machine unit is still two pages.
2. **Landscape in checklist mode only** (277 mm usable). Rejected by § 6 for the
   clipboard, and two `@page` sizes on one route complicate BR1-05.
3. Drop Model and Class · Type in checklist mode. Rejected: § 2's point is that
   the auditor tells two similar machines apart by their plates.

**Recommendation.** Option 1; say it in § 1 (2), § 3 (the view) and § 6, and
correct the column count. Assumption 4 (§ 8) already leans this way.

---

### BR1-02 — `minor` — Does the running number count parts?

**Problem.** § 1 gives "**#** (a running number within the unit)" and the core
"a running `number` within the unit" on **each row**, parts included. The count
line says "42 equipment, 118 parts". If parts are numbered, the last `#` is 160
and the auditor, who counts machines, has to subtract. If they are not, the
brief must say what a part's `#` cell shows.

**Options.**
1. **Machines only**: `number` is set on depth-0 rows and `None` on parts; parts
   print an empty `#` cell and are indented. The last `#` of a section equals its
   machine count, which matches the count line and the accounts' count.
2. Number every row (as written) — simplest to code, and the mismatch above.
3. Dotted numbers (`12.1`, `12.1.2`) — pretty, more code, nobody asked.

**Recommendation.** Option 1; state it in § 1, § 3 (core) and the pure tests
("the running number per unit counts machines; parts carry none").

---

### BR1-03 — `minor` — Who resolves the filter names for the header line?

**Problem.** § 3 puts `filters_label(names)` in the pure core, fed with "the
resolved names (e.g. `[("Class", "RPP"), ("Status", "in service")]`)", and the
endpoint returns `filters` — but nothing says who resolves `class_id` → `RPP`,
`type_id` → the type name, or `in_service` → "In service". The backend holds
only the enum value (`equipment_core.STATUSES`); the display words live in the
frontend (`utils/equipmentLabels.js` `STATUS_LABELS`), as do the masters stores
the list already loads (`equipmentClasses`, `equipmentTypes`). As written, the
coder must either add two lookup queries and a status-label table to the
backend, or leave `filters` unused. Also undefined: the shape of `filters` in
the response, and whether the site and unit filters are repeated on the line
(the section header already names the unit).

**Options.**
1. **The frontend builds the line.** `filtersLabel(params, lookups)` moves to
   `utils/assetList.js` (pure, vitest), using the stores and `STATUS_LABELS`;
   the print view calls `ensureEquipmentClasses()` / `ensureEquipmentTypes()`
   beside the fetch. The endpoint returns no `filters` key; the core loses
   `filters_label` and its test. The line names Class, Type, Status,
   Criticality and "scrapped included"; site and unit are not repeated;
   nothing filtered → "All equipment".
2. **The backend resolves**: two single-row lookups (`equipment_classes`,
   `equipment_types`), `filters` returned as `[["Class", "RPP"], ["Status",
   "in_service"], …]` with the raw status for the frontend to map. Keeps "the
   sheet's header comes from the server" but duplicates the status words.

**Recommendation.** Option 1: the words are already there, one source
(`STATUS_LABELS`) keeps the sheet and the screen saying the same thing, and the
core stays one function. Note in § 6 that the header's filter words come from
the same vocabulary as the list.

---

### BR1-04 — `minor` — The cap test cannot reach the cap as the check is placed

**Problem.** § 3 puts the two cap checks (machines alone; total after parts) in
the **route**, and § 3 Tests says "over 3000 → 400, tested by patching the cap
down", on the S014 pattern (`monkeypatch.setattr(labels_core,
"MAX_LABELS_PER_REQUEST", 2)`). That works in S014 only because the check runs
**inside** `labels_core.expand_selection`, which reads the module global at
call time. If `equipment.py` does `from asset_list_core import
MAX_ASSET_LIST_ROWS` and compares in the route, patching `asset_list_core`
changes nothing the route sees, and the test fails (or the coder patches
`equipment.MAX_ASSET_LIST_ROWS`, which couples the test to an import detail).

Two neighbouring edges are also unstated: with **no machines** the parts query
must be skipped (an empty `IN ()` is the same SQL error the brief guards
against for units), and the machines query has no `LIMIT`, so a runaway table
is read in full before the cap refuses it.

**Options.**
1. **The final check lives in the core**: `build_asset_list(...)` returns
   `(result, None)` or `(None, TOO_MANY_ROWS)` as `expand_selection` does; the
   route's early check (machines alone) compares against
   `asset_list_core.MAX_ASSET_LIST_ROWS` through the module, so one monkeypatch
   reaches both. The machines query takes `LIMIT MAX + 1`, so the early refusal
   never reads more than it needs.
2. Keep both checks in the route and patch `equipment`. Works; brittle.

**Recommendation.** Option 1. Add to § 3 step 3: "no machines → no parts query,
`{units: [], total_rows: 0}`", and to the API tests: "no machines with parts
on → 200, empty".

---

### BR1-05 — `minor` — A static `@page` rule leaks to every page; follow S014's mechanism

**Problem.** § 3 gives `@page { size: A4 portrait; margin: 12mm }` for the view.
Vue cannot scope an `@page` rule (it has no selector), and the router imports
every view statically, so the rule is in the bundle on every page: any screen
the user prints with Ctrl+P becomes A4 portrait with 12 mm margins.
`LabelsPrintView.vue` meets this by creating a `<style>` element on mount and
removing it on unmount, with a comment saying why ("a global @page rule in the
bundle would also take the margins off every other page"). The label sheet
itself survives (its runtime style is appended after the bundle, so it wins
while mounted), but the brief should not introduce the thing S014 avoided.

**Recommendation.** In § 3: "the `@page` rule is injected on mount and removed
on unmount, as `LabelsPrintView` does". Keep the 12 mm margin — it is also
what leaves room for the browser's own header and footer, which is the answer
to open question 1: with `margin: 0` the browser's page numbers would not
print at all.

---

### BR1-06 — `minor` — Name the query keys of the print link, and the scrapped mapping

**Problem.** `assetListPath(filters, withParts, checklist)` and
`parseAssetListQuery(query)` "with the filter keys whitelisted" are specified
without the keys. Two details the coder would decide alone:
- the list's URL says `scrapped=1`, while the API wants `include_scrapped=1`;
  and the list treats `status=scrapped` as "show scrapped" too
  (`showScrapped` in `EquipmentView.vue`), because `_list_filters` adds
  `e.status <> 'scrapped'` otherwise and `status=scrapped` alone would return
  nothing. The print link must carry the same rule or a bookmarked
  `status=scrapped` prints an empty sheet;
- the switch keys (`parts`, `check`) and how the backend parses `with_parts`.

**Recommendation.** In § 3 (`utils/assetList.js`) and § 5:
- the print page's query uses the list's own keys — `site_id`, `unit_id`,
  `class_id`, `type_id`, `status`, `criticality`, `scrapped=1` — plus
  `parts=1` and `check=1` (as `/labels?parts=1`); `assetListPath` takes the
  list's `route.query` and drops everything else (`level`, `q`, `page`);
- `parseAssetListQuery` sends `include_scrapped=1` when `scrapped=1` **or**
  `status=scrapped`, the list's rule;
- the backend reads `with_parts` as `request.args.get("with_parts") == "1"`,
  exactly as `include_scrapped`;
- vitest: `status=scrapped` alone → `include_scrapped=1`; `level` and `q`
  dropped.

---

### BR1-07 — `minor` — Standards: three corrections, so the owner learns the right clause and the right law

**Problem and fix.**
1. **ISO 55001 § 7.5 is "Information requirements", not "documented
   information"** (that is § 7.6). § 7.5 is the better citation for this step:
   it asks the organisation to decide what information it needs about its
   assets and to specify the **quality** of that information — accuracy,
   completeness, timeliness — and to keep processes that maintain it. A
   register that is never checked against the floor has no stated accuracy;
   the walk is that process. Rename the clause in § 2.
2. **ISO 55002 does not prescribe a verification walk.** It is guidance on
   applying 55001; its § 7.5 guidance talks about data quality and assurance.
   Say "ISO 55002's guidance on § 7.5 — asset data should be checked for
   accuracy — is met in practice by periodic physical verification, the same
   walk the accounts call fixed-asset verification" (as the S014 review r1
   BR1-09 already asked for the same sentence in that brief).
3. **CARO 2020 applies to companies, and SMTW is a partnership firm**
   (`Plant-Facts.md` § 1). So CARO cannot apply to SMTW; it may apply to
   **SSVT** (a private limited company), unless SSVT is a *small company* under
   the Companies Act, which CARO exempts — and that is what "for the accounts
   to say" (§ 8, assumption 3) should actually ask. The practice is the same
   for the firm: a partnership's tax audit (Income-tax Act § 44AB, Form 3CD)
   needs a fixed-asset register, and its auditor will ask how it was verified.
   Rewrite the § 2 bullet and assumption 3 with those facts; para 3(i)(b) is
   quoted correctly ("physically verified by the management at reasonable
   intervals; material discrepancies … properly dealt with").
4. One line worth adding: **ISO 27001 A.5.9** (inventory of information and
   other associated assets) — the equipment register is Yantra's asset
   inventory, and a periodic check is the control that keeps it true; the
   printout carries no personal data and is read-only, so no handling rule is
   needed beyond unit access.

The rest is right: ISO 14224 § 8 does list tag number, class and type,
manufacturer, model, serial number and year among the recommended equipment
attributes; EN 13306 does define *item* as anything that can be individually
described and considered, at any level; the levels 6–8 mapping matches
Plan.MD § 4.1; the TPM point (a machine not in the register gets no PM) is the
forgotten-machine case in `Maintenance-Philosophy.md` § 7.

---

### BR1-08 — `nit` — `_list_filters(args)` versus how the argument helpers work

`int_arg` and `enum_arg` (`api_common.py`) read `request.args` themselves and
raise the 400 with the parameter name as `field`; `TestListing.
test_bad_parameters_are_400` asserts those field names. Write the helper as
`_list_filters()` (no argument, reads the request as the helpers do) — or pass
`args` and change the helpers, which is more than this step needs — and say
"the 400 messages and `field` are unchanged". The brief's test "the equipment
list still filters as before" is already `TestListing` and `TestUnitAccess`;
say "the existing list tests pass unchanged" rather than promising a new one.

---

### BR1-09 — `nit` — `printed_at` pre-formatted departs from the API's datetime shape; `printed_by` falls back on empty, not missing

- Every other datetime leaves the API as `YYYY-MM-DDTHH:MM:SS+05:30`
  (`row_to_dict`) and the frontend formats it with `formatDateTime`
  (`utils/datetime.js`); the base's timezone policy says the same. The brief
  sends `DD-MM-YYYY HH:MM` ready-made. Either is fine — the point of § 6 (the
  server's clock, not the browser's) holds either way — but say which and
  why. Simplest: send `datetime.now(IST).strftime(...)` in the API shape and
  format with the existing helper (DRY).
- `make_user` always sets `name` (possibly `""`, since Keycloak local users may
  have no name): the fallback to `actor()` is on an empty string, not a missing
  key.

---

### BR1-10 — `nit` — "Printing … is not logged" is half true since S013

The access log (S013) records every API request as a sighting of the session
from that address, this one included. What the brief means is "no equipment
event is written". Say that; the owner reading § 4 should not think the print
is invisible to the access log.

---

### BR1-11 — `nit` — Small corrections to § 3

- `serial_no` and `year` are already in `_NODE_COLUMNS`; only `s.name AS
  site_name, u.name AS unit_name` are new columns.
- Say how nulls print: no type → the class alone in "Class · Type" (as the
  list does); serial and year blank.
- "a part whose machine is not in `machines` is ignored" cannot happen through
  the route (the parts query is by machine id); keep it as the core's guard,
  and say so, so nobody looks for the API test.

---

### BR1-12 — `nit` — One plain manual check for production

Add to the plain list: "On production, *Printed by* shows the person's name
(the token's `name` claim), not the username." In dev the stub prints
"Dev User" and the tests "Test maint_engineer", so nothing before production
exercises the real claim.

---

## Checked and found consistent

- **User decisions**: checklist columns are one switch on the print page with
  the signature footer tied to it (1); no new field anywhere, the code and
  serial identify the item (2); parts are a switch, indented, scrapped ones
  following *show scrapped* (3); no CSV/Excel, Excel stays with Plan.MD § 4.6 /
  phase 5 (4).
- **Track: full** is right — a new read endpoint beyond plain CRUD that applies
  unit access; no migration, no RBAC change, no dependency.
- **Access**: the same rule as the list and `POST /labels` —
  `accessible_unit_ids(cur)`; `None` = every unit (admin, `it_admin` via
  `equipment:read_all_units`), empty set = empty result with no query;
  `equipment:read` is in `SITE_SCOPED`; `config_rbac.py` untouched.
- **Parts and units**: `NODE_JOINS` resolves a part's unit from its root
  (`COALESCE(gp.unit_id, p.unit_id, e.unit_id)`), so the parts query needs no
  access filter of its own, and `e.parent_id IN (…) OR p.parent_id IN (…)`
  covers both lower levels of the three-level tree (S002).
- **`_list_filters` extraction**: the criticality condition
  (`COALESCE(e.criticality, root)`) is right at equipment level; the search and
  level conditions stay in `list_equipment`; `TestListing` and `TestUnitAccess`
  cover the behaviour the move must keep.
- **Route plumbing**: `canOpenRoute` allows routes that are not nav items, so
  `/asset-list` opens like `/labels`; it cannot collide with
  `/equipment/:id(\d+)` in the router or with `/<int:node_id>` in Flask; the
  API enforces access.
- **Print reset** in `assets/main.css` (`.no-print`, `.app-shell` unclipped,
  `.app-main` without the sidebar margin) exists as the brief says; the base's
  § Print / Export Views pattern (separate route, new tab) is followed.
- **Pure core**: grouping and ordering with no DB or clock, per CLAUDE-COMMON;
  the row shape reuses `_summary`.
- **Plan.MD**: § 4.1 *Verification rounds* (proposed) is the scan-based
  successor the brief names as out of scope; nothing here contradicts a
  decision; § 5 *Data model* unchanged.
- **Cap**: 3000 rows against about 500 machines (Plant-Facts § 3) is a runaway
  stop, not a working limit.
- **Test fixtures** the brief relies on exist: `user_with_units`, `at_unit`,
  `make_site`, `make_unit`, `make_equipment(parent=…)`, `monkeypatch`.
- **Time**: `IST` and `datetime.now(IST)` already exist in `equipment.py`.
- **Manual checks**: the three important ones (checklist fit, two-page unit with
  repeated header and page break, parts indented with the count line) are the
  right ones; the plain ones are rightly plain.
- **Out of scope** is sensible and complete: scan-based round, fixed-asset
  number, export, cross-level class filter, page numbers, per-model list.
