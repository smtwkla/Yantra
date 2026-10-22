```
Step: S015 — Printable asset list
Doc: impl-report
Author: Coder (Sonnet)
Date: 20-10-2026
```

# S015 — Implementation report

## 1. What was built

- A **Print asset list** button on the equipment list. It opens `/asset-list` in a
  new tab with the list's site, unit, class, type, status, criticality filters and
  *show scrapped* (not the search or the level).
- The **print page**: A4 portrait, one section per unit (site then unit order, a new
  page for each), a header (site, `SITE.UNIT`, filter line, printed on / by), then a
  plain nine-column register or, with *Checklist columns*, two lines per item with a
  Found box, a 62 mm Remarks column and the two signature lines. *Include parts* adds
  component-units and components, indented. A count line ends each section
  ("42 equipment, 118 parts").
- `GET /api/equipment/asset-list`, a read-only endpoint, 400 above 3000 rows.

## 2. How it works

- **Pure core** `asset_list_core.build_asset_list(machines, parts, include_scrapped)`:
  groups machines by (site code, unit code), orders machines by code, puts each
  machine's parts after it depth-first by code, sets `depth` (0/1/2) and `number`
  (running machine number per unit, `None` for parts), drops scrapped parts unless
  asked, ignores parts whose machine is absent, and returns `(None, TOO_MANY_ROWS)`
  when the total passes the cap.
- **Route**: `_list_filters()` (moved out of `list_equipment`, which calls it) gives
  the conditions; the route adds `e.level = 'equipment'` and unit access
  (`accessible_unit_ids`; an empty set returns an empty result without a query),
  selects machines with `LIMIT cap + 1` (400 at once above the cap), returns early
  when there are none, with `with_parts=1` selects the parts in one query
  (`e.parent_id IN (...) OR p.parent_id IN (...)`), calls the core, and returns
  `{units, total_rows, printed_at, printed_by}`. `printed_at` is IST,
  `isoformat(timespec="seconds")`; `printed_by` is the token name or the username.
- **Frontend**: `utils/assetList.js` builds the link (`assetListPath`), reads it
  (`parseAssetListQuery`, which sends `include_scrapped=1` for `scrapped=1` or
  `status=scrapped`) and words the filter line (`filtersLabel`). The view calls the
  endpoint, formats `printed_at` with `formatDateTime`, adds the `@page` rule on mount
  and removes it on unmount. The two switches write to the URL query (`router.replace`),
  so a reload keeps them; changing either reloads the data (simple, one fetch).

## 3. Files touched (S015 only)

New:
- `backend/asset_list_core.py`: the pure core.
- `backend/tests/test_asset_list_core.py`: 11 core tests.
- `backend/tests/test_asset_list_api.py`: 17 API tests.
- `frontend/src/utils/assetList.js`: link, query and filter-line helpers.
- `frontend/tests/assetList.test.js`: 11 vitest cases.
- `frontend/src/views/AssetListPrintView.vue`: the print page.

Changed:
- `backend/equipment.py`: `_list_filters()` extracted; `GET /asset-list` added; imports
  `g`, `asset_list_core`, `build_asset_list`.
- `frontend/src/router/index.js`: `/asset-list` route.
- `frontend/src/views/EquipmentView.vue`: the Print asset list button and `printAssetList`.
- `docs/steps/S015-asset-list/1-brief.md`, `docs/steps/README.md`: status rows.
- This report.

No S016 file was touched; `conftest.py` needed no new fixture.

## 4. Decisions taken

- `_list_filters()` also holds the `include_scrapped` condition (the brief lists
  "scrapped" among its conditions). In `list_equipment` the scrapped condition now
  comes before the level and search conditions in the WHERE; the order is irrelevant.
  One side effect: a bad filter value and a bad `page` are checked in a different order
  (still 400 with the same message and field).
- `filtersLabel` writes "scrapped included" only when scrapped are included and the
  status filter is not already `scrapped` (which says it), and shows `#<id>` for a class
  or type not yet loaded.
- Parts are indented on the Name cell (4 mm per level); in the checklist the detail line
  is indented the same way. The Code cell keeps its width.
- The criticality column is headed "Crit." and the detail line leaves out empty values
  (no serial number, no year) rather than printing blanks.
- Both switches reload the data; only *Include parts* needs it, but one code path is
  simpler.
- The sheet's `printed_at` is shown per unit section (the same stamp on every section).

## 5. Not done, deferred or assumed

- Not looked at on a printer; layout widths (9 pt, 186 mm) are from calculation, so the
  manual checks below matter. In particular the checklist columns sum to 7+22+14+62 mm
  plus the flexible Name column (about 81 mm).
- The cap for the machine query and the total reads `asset_list_core.MAX_ASSET_LIST_ROWS`
  through the module, as the brief says; the core's own check reads it as a module global.

## 6. Tests

- `tooling/run-tests.bat`: backend 1490 passed (2 min 17 s); frontend vitest 70 passed
  (11 files); tooling/deps 42 passed.
- `npx vite build` in `frontend/`: clean (166 modules).
- The existing list tests (`TestListing`, `TestUnitAccess`) pass unchanged.

## Manual checks

- [ ] Print one unit with **Checklist columns** on the office printer, A4 portrait at
  100 %. No column is cut off at the right, the Remarks column is wide enough to write
  in, and the signature footer is on the sheet.
- [ ] Print a unit long enough for two pages. The table header repeats on page 2, and
  the next unit starts on a new page.
- [auto] (S024 browser test, see *Browser tests* below; accepted by KLA, 21-10-2026) With **Include parts**, a press shows its component-units and components indented
  under it, and the count line reads "n equipment, m parts".

Also:
- The header shows the site, unit, filters, printed on (IST) and printed by.
- Switches and the Print button do not print; reload keeps the switches.
- A user limited to one unit sees only that unit's sections.
- Filters that match nothing show "Nothing to list for these filters".
- After the print page, printing another screen with Ctrl+P is not forced to A4 portrait
  (the `@page` rule is removed).
- On production, *Printed by* shows the person's name (the token's `name` claim), not
  the username (BR1-12).

### Browser tests (S024), 21-10-2026

From the passing e2e runs of 21-10-2026 (`tooling/run-e2e-tests.bat`, three set-ups: Pixel 7 Chromium, iPhone 14 WebKit, desktop Chromium; 135 passed, 0 skipped, 0 failed, 5.1 min, exit 0). The boxes above are left as they are: the user decides at gate B.

- [auto] With **Include parts**, the part is indented under its machine and the count line reads "n equipment, m parts" (matching the rows) — S024 e2e/asset-list.spec.js::manager: a section per unit with its header; parts indented with the count line; checklist with signatures
- [auto] The header shows the site, unit, printed on and printed by; switches and Print are left off paper; reload keeps the switches; the `@page` rule goes when leaving — same test
- [auto] A user limited to one unit sees only that unit's section — S024 e2e/asset-list.spec.js::operator of one unit: only that unit's section
- [auto] Filters that match nothing show "Nothing to list for these filters" — S024 e2e/asset-list.spec.js::filters that match nothing say so
- On a real device: `docs/steps/device-checks.md` rows 3 (checklist on paper) and 4 (two pages). "Printed by" on production stays a plain check.

## Fix rounds

### Round 1

Review: `4-code-review-r1.md` (three nits).

- **CR1-01 — Fixed.** The `depth` wording in `backend/asset_list_core.py` now reads "0 for the
  machine, then +1 per level below it: a component-unit, or a component fitted directly to the
  machine, is 1; a component in a component-unit is 2". New API test
  `TestParts::test_a_component_fitted_directly_to_the_machine_is_depth_1` in
  `backend/tests/test_asset_list_api.py` (a component with `parent=press` comes at depth 1,
  right after the press at depth 0).
- **CR1-02 — Fixed.** `_asset_list_row` in `backend/equipment.py` reads `parent_id`,
  `serial_no` and `year` straight from `node`; the `row_to_dict` call is gone from that
  function (the import stays, it is used elsewhere in the file).
- **CR1-03 — Deferred.** Queued by the user as a small tidy-up step (a shared
  unit-access helper); not touched here.

Tests after the round: `tooling/run-tests.bat` backend 1491 passed (2 min 22 s, one more than
before: the new test); frontend vitest 70 passed; tooling/deps 42 passed. No frontend change,
so no `vite build` this round.
