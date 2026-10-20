```
Step: S015 — Printable asset list
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 20-10-2026
```

# S015 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** Three nits, none of which needs to be fixed before commit.

Reviewed against: 90284ec + the uncommitted working tree. Only S015's files, as listed in
`3-impl-report.md` § 3. These are `backend/asset_list_core.py`,
`backend/equipment.py` (the `_list_filters` move and `GET /asset-list`),
`backend/tests/test_asset_list_core.py`, `backend/tests/test_asset_list_api.py`,
`frontend/src/utils/assetList.js`, `frontend/src/views/AssetListPrintView.vue`,
`frontend/src/router/index.js`, `frontend/src/views/EquipmentView.vue` and
`frontend/tests/assetList.test.js`. The S016 files in the tree (`conftest.py`, `masters*`,
`local_db.py`, `config_rbac.py`, `test_rbac.py`, the failure-code panels) and the docs outside
this step were not reviewed. Diffs were read with `git diff -w --ignore-cr-at-eol`.

## Test results (run by the reviewer)

- `tooling/run-tests.bat`: backend **1490 passed** (125.8 s); frontend vitest **70 passed**
  (11 files); tooling/deps **42 passed**. Exit 0.
- `npx vite build` in `frontend/`: clean, 166 modules, no warnings.

## Findings

### CR1-01 — nit — `backend/asset_list_core.py:24-26`: the depth docstring doesn't match the tree rule

**Problem.** The docstring says `depth` is "0 machine, 1 component-unit, 2 component". But
`equipment_core._ALLOWED_PARENTS` lets a component sit **directly** under an equipment
(`"component": ("component_unit", "equipment")`). Such a component is fetched by
`e.parent_id IN (...)` and gets depth 1. The code is right: depth is the position in the tree,
which is what the indentation needs. Only the docstring is wrong, and no test covers this case.

**Scenario.** A later reader trusts the docstring and maps `depth == 1` to "component unit"
on the page, for example to label the row. A motor fitted straight to a press would then be
called a component unit.

**Fix.** Word it as "depth: 0 for the machine, then +1 per level below it (a component-unit, or
a component fitted directly, is 1; a component in a component-unit is 2)". Add one API case to
`TestParts`: a component made with `parent=press, level="component"` comes at depth 1, right
after the press.

### CR1-02 — nit — `backend/equipment.py:574-577`: `_asset_list_row` converts the whole row to read three plain fields

**Problem.** `row_to_dict(node)` converts every column of the row (including `created_at` and
`updated_at`), only to read `parent_id`, `serial_no` and `year`. None of those three needs the
conversion. A reader then wonders which conversion was wanted.

**Scenario.** Nothing goes wrong. It is a moment of puzzling, against the "explicit over
clever" rule.

**Fix.** Read them straight from `node`: `node["parent_id"]`, `node["serial_no"]`,
`node["year"]`.

### CR1-03 — nit — `backend/equipment.py:593-598`: the unit-access block is now repeated a fourth time

**Problem.** These lines now appear in the list, in labels (`:549`), in documents
(`documents.py:461`) and in the asset list:
`accessible_unit_ids` → empty set → early return → `u.id IN (%s, …)`. The brief asked for
unit access "as the list does", so following the existing pattern was right for this step.
But CLAUDE-COMMON's DRY rule points to a small helper, for example
`unit_access_condition(cur) -> (sql, params) | None`.

**Scenario.** A future change to unit access, such as excluding inactive units in a new way,
is made in three places and missed in the fourth.

**Fix.** Nothing in S015. Queue a small tidy-up step to extract the helper, since it touches
code outside this brief.

## Earlier rounds

None; this is round 1.

## Checked and found consistent

- **Scope.** Everything in the brief's § 1 and § 3 is built:
  - the button beside *Print labels*, opening a new tab;
  - the `/asset-list` route, titled "Asset list";
  - the pure core, the endpoint and `utils/assetList.js`;
  - the two switches kept in the URL, and the A4 `@page` rule added on mount and removed on
    unmount;
  - one section per unit with `break-before: page`, and the `thead` repeated on each page;
  - the count line, and the checklist footer with both signature lines;
  - "Too many rows" shown with no sheet, and "Nothing to list for these filters".

  Nothing is built beyond the brief. Every departure is listed in the report's "Decisions
  taken":
  - the `include_scrapped` condition is inside `_list_filters`, and the order of validation
    changed (still the same 400 and `field`);
  - the "Crit." heading;
  - empty values are left out of the checklist's detail line;
  - both switches reload the data;
  - the stamp is shown on every section;
  - the `#<id>` fallback.

  `config_rbac.py` is unchanged, as the brief says.
- **Pure core.** `asset_list_core` has no DB, Flask or clock access:
  - units are ordered by (site code, unit code), and machines by code;
  - parts are depth-first and ordered by code within each group;
  - `number` counts machines only and restarts in each unit; parts carry `None`;
  - scrapped parts are dropped unless asked for. Their children go with them, which is safe
    because scrapping needs every part scrapped first (`_check_parts_scrapped`);
  - parts with no machine in the set are ignored;
  - the total cap reads the module global and returns `(None, TOO_MANY_ROWS)`.
- **Endpoint.**
  - It is gated with `@require_perm("equipment:read")`, the list's key.
  - Unit access goes through `accessible_unit_ids(cur)`. An empty set returns at once, with no
    `IN ()`; `None` means every unit.
  - The machine query runs with `LIMIT cap + 1` and reads the cap through the module, so the
    test patch reaches both checks.
  - With no machines, there is no parts query.
  - With parts, one parameterised query gets them (`e.parent_id IN … OR p.parent_id IN …`).
    The `IN` lists are built from `%s` placeholders only, so no SQL is built from values.
  - `printed_at` is `datetime.now(IST).isoformat(timespec="seconds")`.
  - `printed_by` is `g.user["name"]`, or `actor()` when the name is empty; the actor is never
    taken from the client.
  - It is read-only and writes no event.
- **The `_list_filters` move.** It reads the request with no argument and keeps the same
  `int_arg` / `enum_arg` 400s with their `field`. `TestListing` and `TestUnitAccess` pass
  unchanged.
- **DB unavailable / dead connections.** The route uses `get_db()`, so `DBUnavailable` → 503
  and reconnect-on-first-use work as for the list. The machine and parts reads are not in one
  transaction. A part moved between the two reads could at worst be missed on one printout.
  That is acceptable for a read-only report.
- **Frontend.**
  - `parseAssetListQuery` keeps only the list's keys, and sends `include_scrapped=1` for
    `scrapped=1` or `status=scrapped`. That is the list's own `showScrapped` rule
    (`EquipmentView.vue:52`).
  - `assetListPath` drops `level`, `q` and `page`.
  - `filtersLabel` uses the stores and `STATUS_LABELS`, and leaves site and unit out.
  - `formatDateTime` gives `DD-MM-YYYY HH:MM`.
  - A 400 shows the server's `error` text, through `apiGet` → `err.message`.
  - A sequence guard stops a stale response from overwriting a newer one.
  - The switches, the Print button and the notes are `.no-print`.
- **Tests.** They cover the brief's § Tests list:
  - core: ordering, depth, numbering, scrapped, orphan part, counts, cap, empty input;
  - API:
    - the filters;
    - parts of another class coming with their machine;
    - empty with parts on;
    - unit access: own units, no units without an SQL error, admin and `it_admin`;
    - both caps, patched;
    - the stamp's shape;
  - vitest: the three helpers.
- **Track.** Light, as set by the user at gate A. There is no migration, no RBAC change, no
  new dependency and no transaction, and 9 code files are touched. The new read endpoint was
  known at gate A and accepted for the light track.
- **Manual checks.** The impl report's `## Manual checks` carries all three **important**
  checks of the brief § 7 as unticked boxes, and the six plain ones as a list.

## Manual browser checks still needed (user)

Important (from the brief, unticked in the report):
- [ ] Print one unit with **Checklist columns** on the office printer, A4 portrait at 100 %.
  Check that no column is cut off, that Remarks is wide enough to write in, and that the
  signature footer is on the sheet.
- [ ] Print a unit long enough for two pages. Check that the header repeats on page 2 and
  that the next unit starts on a new page.
- [ ] With **Include parts**, check that a press shows its component-units and components
  indented under it, and that the count line reads "n equipment, m parts".

Also:
- The header shows site, unit, filters, printed on and printed by.
- The switches and the Print button do not print, and a reload keeps them.
- A one-unit user sees only that unit.
- Filters that match nothing show "Nothing to list for these filters".
- Ctrl+P on another screen afterwards is not forced to A4.
- On production, *Printed by* shows the person's name.
