```
Step: S014 — QR labels
Doc: impl-report
Author: Coder (Opus)
Date: 18-10-2026
```

# S014 — QR labels: implementation report

Built on the working tree as it stands: uncommitted S013 (migration v10) on top of
`c2c45d2`. S014 has no migration.

## 1. What was built

- **A permanent link per node**, `<label address>/e/<code>` (e.g.
  `https://vel-yantra.mspv.app/e/VBM001`). Opening it signs the user in if needed and
  replaces the address with that node's equipment page. An unknown code, a malformed code
  and a node outside the user's units all show the same "Page not found".
- **The label sheet** (`/labels?ids=…&parts=0|1`): A4 sheets of 3 × 5 labels of 52 mm, with
  thin grey cut lines. Each label: the QR code (38 mm box, quiet zone included), then the
  **code** in large bold type and the **site** code small at the right, then the **name**
  small, cut with "…" when long. A note on screen says how to print (100 %, "Actual size",
  no "Fit to page", headers and footers off, Chrome and Edge, measure with a ruler) and a
  **Print** button; neither prints.
- **Equipment list:** a tick column, **Select all on this page** in the header, and a
  **Print labels (n)** button that opens the sheet in a new tab. The ticks are kept while
  paging through the same filters and cleared when any filter or the search changes; at
  300, further ticks are refused with "300 labels at most — print this group first".
- **Equipment page:** a **Print label** menu with "This node only" and "This node and all
  its parts", opening the sheet in a new tab. Shown to everyone who can see the node,
  scrapped nodes included.
- **Settings › Labels:** the label link address, default `https://vel-yantra.mspv.app`;
  a form for `settings:edit` (IT admin), read-only for `settings:read`.

## 2. How it works

**Pure core — `backend/labels_core.py`.**
- `parse_code(text)`: at most 12 characters, upper-cased, must match
  `CODE_RE = ^[A-Z]{2,4}[0-9]{3,8}$`; otherwise None, so the route answers 404 without a
  query.
- `label_url(base, code)` → `base + "/e/" + code`.
- `normalise_base_url(text)` → `(url, None)` or `(None, message)`. It uses `urlsplit` and
  checks:
  - the scheme is `https` or `http`;
  - there is no user-info (`@`), and no `?` or `#`;
  - the path is empty or a lone `/` (which is dropped);
  - the host is made of letters, digits, dots and hyphens, lower-cased;
  - an optional numeric port;
  - the result is at most 40 characters.
- `make_qr(text)` builds a `qrcode.QRCode` at level Q, border 4, version chosen to fit.
  `qr_svg(text)` renders it with `SvgPathImage` and takes the element with the public
  `get_image()`. It removes `width`, `height` and the library's `id="qr-path"` (300 labels
  on one page would repeat that id), then serialises with `ET.tostring(…, "unicode")`. The
  result is one `<svg viewBox=…>` with a single `<path>` and no XML declaration.
- `expand_selection(selected_ids, rows, with_parts)` returns the nodes in print order:
  - each selected node in the order sent, then (with parts) its live children by code,
    then their live children by code;
  - scrapped parts are left out, and so is anything under them; a scrapped node that was
    selected is printed;
  - de-duplicated by id, first occurrence kept;
  - more than 300 → `(None, "Too many labels …")`.

**Shell — `backend/equipment.py`.**
- `GET /api/equipment/by-code/<code>` (`equipment:read`) parses the code, finds its id, then
  goes through the existing `load_node_for_user`. Access is therefore exactly the equipment
  page's, and a node outside the user's units gives the same 404 as an unknown code.
- `POST /api/equipment/labels` (`equipment:read`):
  1. Validates the body: `ids` must be a non-empty list of distinct positive integers
     (booleans refused), at most 300; `with_parts` is a boolean, default false. Anything
     else → 400.
  2. Takes `accessible_unit_ids`. An empty set → 404 at once, with no query.
  3. Runs **one query** through `NODE_JOINS`. Without parts it reads `e.id IN (ids)`; with
     parts `e.id IN … OR e.parent_id IN … OR p.parent_id IN …`. When the user does not see
     every unit, it adds `AND u.id IN (<units>)`. Parts resolve to their root's unit
     through the join, so they pass with it.
  4. If any selected id is not in the rows → 404 for the whole request: "Some of the
     selected equipment was not found or is not at your units".
  5. `expand_selection` orders the rows; over 300 → 400.
  6. Each label is `{id, code, name, site_code, url, qr_svg}`, with the address from
     `label_base_url(cur)`.

**Shell — `backend/settings.py`.**
- `get_setting_text(cur, key, default)` returns the stored text, or the default when there
  is no row.
- `label_base_url(cur)` passes the stored text through `normalise_base_url`:
  - no row → the default, with no warning;
  - a stored value that fails the check → a warning in the log and the default.
- `DEFAULT_LABEL_BASE_URL` lives in code; there is no migration row.
- `GET /api/settings/labels` (`settings:read`) returns `{base_url}`.
- `PUT /api/settings/labels` (`settings:edit`) is saved like `put_app_settings`: `SELECT …
  FOR UPDATE`, then `INSERT … ON DUPLICATE KEY UPDATE`, then the log line
  `Setting label_base_url changed by <user>: old -> new`.

**Frontend.**
- **Router:**
  - `/e/:code([A-Za-z0-9]{1,12})` → `EquipmentByCodeView`, which calls `by-code` and runs
    `router.replace('/equipment/<id>')`. A 404 renders `NotFoundView`; any other error
    shows a Retry.
  - `/labels` → `LabelsPrintView`.
  - Nothing is added to the public paths: both routes need sign-in like every page.
- **`utils/labelSheets.js`:**
  - `parseLabelQuery(query)` → `{ids, withParts}`, or null for a link without a clean
    list;
  - `chunkSheets(labels, 15)`;
  - `labelsPath(ids, withParts)` → the print page's address.
- **`LabelsPrintView`** reads the query and POSTs `/api/equipment/labels`.
  - It lays out one 210 × 297 mm block per sheet: `break-after: page` (not on the last
    sheet), `overflow: hidden`, padding 18.5 mm top and bottom and 27 mm at the sides, and
    a 3-column grid of 52 mm cells.
  - Each cell is `box-sizing: border-box` with a 0.2 mm `#bbb` border, so the pitch stays
    52 mm.
  - The SVG goes into a 38 mm box with `v-html`; the code, site and name are text
    bindings.
  - `@page { size: A4; margin: 0 }` is added to `<head>` only while this view is mounted
    (see § 4).
  - On a 400 or 404 the page shows the server's message and no sheet.
  - The existing print reset in `main.css` (`.no-print`, the app shell's height and
    overflow, no sidebar margin or content padding) does the rest.

## 3. Files touched

| File | Change |
|---|---|
| `backend/labels_core.py` | **new** — pure label rules (code check, link, address check, QR SVG, selection expansion, cap) |
| `backend/equipment.py` | `GET /by-code/<code>`, `POST /labels`, the request validator; docstring lines |
| `backend/settings.py` | `get_setting_text`, `DEFAULT_LABEL_BASE_URL`, `label_base_url`, `GET/PUT /labels`; module docstring |
| `backend/pyproject.toml` | `qrcode>=8.2` (via `uv add qrcode`) |
| `backend/uv.lock` | `qrcode 8.2` (and `colorama` on Windows) locked |
| `backend/tests/test_labels_core.py` | **new** — 49 pure tests |
| `backend/tests/test_labels_api.py` | **new** — 52 API tests (by-code, labels, setting) with a `label_address` fixture that deletes the row before and after |
| `frontend/src/utils/labelSheets.js` | **new** — `parseLabelQuery`, `chunkSheets`, `labelsPath` |
| `frontend/tests/labelSheets.test.js` | **new** — vitest for the three helpers |
| `frontend/src/views/EquipmentByCodeView.vue` | **new** — `/e/:code` lookup and replace |
| `frontend/src/views/LabelsPrintView.vue` | **new** — the A4 sheets, print note, Print button |
| `frontend/src/router/index.js` | the two routes |
| `frontend/src/views/EquipmentView.vue` | tick column, select all on this page, cap hint, Print labels (n) |
| `frontend/src/views/EquipmentDetailView.vue` | Print label menu (this node / with its parts) |
| `frontend/src/views/SettingsView.vue` | Labels card |
| `docs/steps/S014-qr-labels/1-brief.md` | Status line |
| `docs/steps/README.md` | S014 index row |

17 files: 8 new, 9 changed.

### Files shared with uncommitted S013

S013 is in the working tree and not committed (snapshot
`scratch/snapshot-s013-20261018-1445/`). These files hold changes from **both** steps, so
the commit split must take S014's hunks out of them:

- `backend/settings.py` — S013: network and access-log and tasks routes, the imports.
  S014: `get_setting_text`, the label-address block (from `# Label link address (S014 § 3)`
  down to just before `# Internal networks (S013 § 5.2)`), the `labels_core` import and the
  module docstring sentence about the label address. Since fix round 1 also
  `_save_setting`, `get_setting_int` reading through `get_setting_text`, and the
  `put_app_settings` and `put_network` calls to `_save_setting` (CR2-01). Split 18-10-2026
  by the planner: S013 was committed (ae0f183) with these two files as in the snapshot, so
  all of the above is in the S014 commit.
- `frontend/src/views/SettingsView.vue` — S013: Network, Background tasks and Access log
  cards. S014: the "Labels card" docstring bullet, the `// Labels` script block,
  `loadLabels()` in `onMounted`, the Labels card in the template, the `.label-address`
  style.
- `docs/steps/README.md` — S013 rows and wording; S014: its own index row only.
- `docs/steps/S014-qr-labels/1-brief.md` — the snapshot's `untracked.tgz` already holds
  the brief (as approved); S014 changed only its Status line.

None of the other S014 files is touched by S013. `backend/tests/conftest.py` was **not**
changed by S014: the settings-row fixture lives in `test_labels_api.py`.

## 4. Decisions taken

These are small, forced choices the brief does not spell out. None changes the design.

1. **`@page` rule injected only while the print view is mounted.** The brief has
   `@page { size: A4; margin: 0 }`. As a rule in the bundle's CSS it would apply to every
   page the user prints (all views are in one bundle), and would take the margins off them
   too. So `LabelsPrintView` adds a `<style>` with that rule on mount and removes it on
   unmount. I rejected CSS named pages (`page: labels`): they are less certain to apply to
   the first sheet across browsers.
2. **The library's path `id="qr-path"` is stripped**, as well as width and height: up to
   300 identical ids on one page would be invalid HTML.
3. **Extra helpers:**
   - `parse_code` (pure) holds the code check, so it is tested without Flask;
   - `make_qr` is public, so the tests can read `version`, `error_correction` and `border`
     from the `QRCode` object, as the brief asks;
   - `labelsPath` builds the `/labels?…` address shared by the list and the page;
   - `TOO_MANY_LABELS` is one message for both caps.
4. **Host check.** `normalise_base_url` also requires the host to be letters, digits, dots
   and hyphens. The brief's `urlsplit` rules alone would let spaces or `<>` through into
   the link. An IPv6 literal (`[::1]`) is therefore refused. A plain IPv4 address with a
   port is accepted.
5. **Error messages.**
   - The cap before expansion uses the same text as the cap after: "Too many labels —
     print in smaller groups (at most 300)".
   - A bad `ids` list gets "Choose the equipment to print (a list of distinct ids)".
6. **Selection order.**
   - From the list, the ids are sent in the order they were ticked; the server keeps that
     order.
   - "Select all on this page" is refused as a whole when it would pass 300: no partial
     page is ticked. It shows the cap hint.
   - The selection clears when any query key other than `page` changes: the filters, the
     search, the level and "show scrapped".
7. **"This node and all its parts"** is greyed out when the node has no parts at all.
8. **The `/e/` route pattern is `[A-Za-z0-9]{1,12}`** (brief § 4). Anything else falls to
   the existing catch-all not-found route.
9. **The test for the cap after expansion** lowers `labels_core.MAX_LABELS_PER_REQUEST` to
   2 with `monkeypatch`, rather than creating 301 nodes. The pure test covers the real 300.

No departure from the brief.

## 5. Not done, deferred or assumed

- **Response size.** One QR SVG is about 9 KB (one `<path>` with a square per module), so
  300 labels are about 2.7 MB of JSON. That is acceptable on the plant network.
  `SvgPathImage` cannot merge the squares; a leaner path would need a hand-written
  encoder, which is not worth it.
- **The QR is never decoded in the tests:** the library has no reader. The manual scan
  check below covers it.
- **Physical size depends on the browser honouring 100 % and no margins.** That is the
  first manual check.
- **The print page sits in the app shell on screen,** with the sidebar and top bar. Both
  are hidden in print.

## Manual checks

Important:
- [ ] Print a sheet on the office printer at 100 %: each cut square measures 52 mm with a
  ruler.
- [ ] Scan a printed label with an Android phone's camera and with an iPhone's camera, on
  mobile data: the link opens Yantra, asks for login if needed, and shows that equipment's
  page.
- [ ] A crumpled or oil-marked label (rub a finger of grease across a corner) still scans.

Also:
- Equipment list: tick across two pages of a unit filter, print: all of them come out;
  changing the filter clears the ticks.
- The equipment page prints a node with its parts; a scrapped part is left out.
- A long name is cut with "…"; the code and site are whole.
- Print preview of 16 labels shows exactly 2 pages; if not, set the sheet height to
  296.8mm (CR1-03).
- As IT admin on mobile data, a scanned label shows the "plant network only" card (S013,
  expected).

## Tests

- `tooling/run-tests.bat`:
  - backend **1271 passed**, including the new `test_labels_core.py` (49) and
    `test_labels_api.py` (52);
  - frontend **57 passed** in 10 files, including `labelSheets.test.js`.
- `tooling/run-frontend-build.bat` (`vite build`): built clean, no warnings.

## Fix rounds

### Round 1

- **CR1-01 Fixed.** `_save_setting(cur, key, text)` in `backend/settings.py` does the locking
  read, the upsert and the A.8.15 log line. `put_app_settings` and `put_labels` call it.
  `get_setting_int` now reads through `get_setting_text(cur, key, None)`. S013's
  `put_network` held the same block, so it calls the helper too: the SQL and the log line
  are identical, so its behaviour is unchanged (the helper is the only change to S013 code).
- **CR1-02 Fixed.** `test_no_units_at_all_is_the_same_404` in `test_labels_api.py`:
  `user_with_units("maint_engineer", [])` gets 404 with the same body as for an unknown code.
- **CR1-03 Fixed (manual check).** Added the plain check "print preview of 16 labels shows
  exactly 2 pages; if not, set the sheet height to 296.8mm". CSS unchanged.
- **CR1-04 Fixed.** `normalise_base_url` refuses port 0; one message for both port errors,
  "The port must be a number from 1 to 65535". `https://x.in:0` added to `test_refused`.
- **CR1-05 Fixed.** `expand_selection` builds `children` from `rows` unsorted, with a comment
  that `live_parts` does the sorting.

Tests after this round: backend 1287 passed, frontend 57 passed (10 files).
