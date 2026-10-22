```
Step: S014 — QR labels
Doc: brief
Author: Planner (Opus)
Date: 18-10-2026 (revised 18-10-2026 after brief-reviews r1 and r2)
Track: full
Status: Committed dde0d68; checks left: 3 on a real device for IT Admin (device-checks rows 1, 2, D2, D3) (approved 18-10-2026 by KLA)
```

# S014 — QR labels

Plan.MD § 4.1: every node of the equipment tree has a permanent code, "printed on
the QR label". Scanning the label with a phone opens the equipment page, from
where an operator later raises a ticket (S017) or logs a reading (phase 4). The
labels are also what the asset list of S015 and the verification walk (Plan.MD
§ 4.1, *Proposed*) are checked against.

User decisions:
1. (17-10-2026) Labels **52 mm square**, printed **on paper** for now; a durable
   printer or label stock comes later.
2. (18-10-2026) The label also shows the **site** code.
3. (18-10-2026) `https://vel-yantra.mspv.app` is the address used everywhere,
   on the plant Wi-Fi and on mobile data.

**Track: full** — a new dependency (a QR encoder) and endpoints beyond plain
CRUD. No migration, no change to data, no RBAC change.

**Depends on:** S013 (committed first). No migration in this step.

## 1. What will be built

1. **A short, permanent link per node:** `https://vel-yantra.mspv.app/e/VBM001`
   — the node's code, nothing else. Opening it (phone camera, any browser) signs
   the user in if needed and shows that node's equipment page. A code that
   doesn't exist, or a node outside the user's units, shows the same "not
   found" page.
2. **The label (52 × 52 mm):** the QR code (38 mm, with its white margin); under
   it, on one line, the **code** in large bold type and the **site** code in
   small type at the right; on the next line the **name** in small type (cut
   short with "…" if long). Nothing else — no unit or path.
3. **Print labels from the equipment list:** tick nodes, or **select all on this
   page**; the ticks are kept while paging through the same filters, and the
   button shows the count: **Print labels (n)**.
4. **Print labels from the equipment page:** **Print label** for this node, with
   a choice "this node only" or "this node and all its parts" (component-units
   and components below it).
5. **The print page:** A4 sheets of **3 × 5 = 15 labels**, with thin grey cut
   lines, printed by the browser at 100 % scale. More nodes → more sheets. A note
   on the page says: print at 100 % ("Actual size"), no "Fit to page"; checked
   in Chrome and Edge; measure one square with a ruler.
6. **Settings › Labels** (IT admin): the **label link address**, default
   `https://vel-yantra.mspv.app`, so labels always carry the public address
   whoever prints them.

**Out of scope:**
- a scanner inside Yantra ("scan equipment" button, Plan.MD § 6) — phone camera
  apps open the link already;
- label-printer roll formats and adhesive A4 label sheets (start position, label
  pitch) — when the durable printer or stock is chosen;
- logos, colours, criticality, unit or path on the label;
- recording which nodes have a label (the verification walk will);
- the asset list for audit (S015).

## 2. Standards and practice

- **ISO 14224 § 8 (equipment data)** lists the **tag number** first: the
  permanent identity of a maintainable item, kept apart from its location and
  description. Yantra's code is that tag number (Plan.MD § 4.1, decided
  13-10-2026): it survives moves and re-classification, so the label stays true.
  Common asset-tagging practice is the same: tag the identity, not the facts
  that change. The **site** is printed by the user's choice (decision 2); it
  changes only when a machine moves between sites, which is rare — then the
  label is reprinted.
- **ISO 55001 § 7.5 (information)** asks the organisation to decide what asset
  information it needs and keep it accurate. A label that leads to the record
  keeps the record in use; a periodic physical check (the verification walk,
  and the accounting fixed-asset audit, which is the same walk; S015) is how its
  accuracy is kept.
- **ISO/IEC 18004 (QR code)** defines the symbol, four error-correction levels
  (L 7 %, M 15 %, Q 25 %, H 30 % of the code can be damaged and still read) and
  the **quiet zone** of 4 modules (the white margin phones need). Choices:
  - **level Q** — a paper label on a machine gets oil and scratches; M is the
    web default, H makes the code denser;
  - the link is short, so the code is **version 4 (33 × 33 modules; 41 with the
    quiet zone) → about 0.93 mm per module at 38 mm** (BR1-01). The standard sets
    no module size; in practice phones read modules of about 0.5 mm at close
    range, and a code reads at about ten times its width (≈ 30–40 cm here).
- **TPM visual management:** the label is the first visual on the machine;
  later the CIL sheet and the open-ticket count hang off the same code
  (`Maintenance-Philosophy.md` § 6).

## 3. Where

### Backend
- **Dependency:** `qrcode` (python-qrcode, lincolnloop; changed at gate A,
  18-10-2026, § 6), added with `uv add qrcode` so `backend/uv.lock` is updated
  (`Dockerfile.backend` uses `uv sync --frozen`). SVG output is pure Python
  (`qrcode.image.svg`); no Pillow. Its only other dependency is `colorama` on
  Windows (dev only).
- **`backend/labels_core.py`** (new, pure):
  - `label_url(base_url, code)` → `base_url + "/e/" + code`;
  - `qr_svg(text)` → `qrcode.QRCode(version=None, error_correction=
    ERROR_CORRECT_Q, border=4, image_factory=SvgPathImage)`, `make(fit=True)`;
    returned as one `<svg>` element with a `viewBox`, a single `<path>`, **no
    XML declaration and no fixed width/height** (stripped if the library writes
    them; its open issue #351), so it scales to the 38 mm box (BR2-06);
  - `expand_selection(selected_ids, rows, with_parts)` → the ordered,
    de-duplicated list (each selected node, then its parts level by level by
    code, scrapped parts left out), or a "too many" error above 300 (BR2-02);
  - `normalise_base_url(text)` → the cleaned URL or an error (§ 4);
  - `CODE_RE = ^[A-Z]{2,4}[0-9]{3,8}$` and the length limit 12 (the column).
- **`backend/equipment.py`:**
  - Both new routes carry `@require_perm("equipment:read")` before the unit
    check (BR2-08).
  - `GET /api/equipment/by-code/<code>` → `{id}`. A plain `<code>` route
    (Flask has no regex converter); in code the value is checked for length
    ≤ 12, upper-cased and matched against `CODE_RE` (404 at once if not). Access as the equipment page
    (BR1-02): the node's root unit must be in `accessible_unit_ids` (or `None`
    for admin / `equipment:read_all_units`); an unknown code and one outside the
    user's units give the **same 404**, as `load_node_for_user` does.
  - `POST /api/equipment/labels` `{ids, with_parts}` →
    `{labels: [{id, code, name, site_code, url, qr_svg}]}`.
    - `ids`: a non-empty list of distinct positive integers, at most
      `MAX_LABELS_PER_REQUEST = 300` (400 otherwise); `with_parts` boolean,
      default false.
    - An **empty** accessible-unit set → the 404 below at once, with no query
      (an empty `IN ()` is an SQL error; the list returns early the same way;
      BR2-01).
    - **One query**, joined through `NODE_JOINS`, filtered by
      `u.id IN (<accessible units>)` when the unit list is not `None`. Without
      parts it selects `e.id IN (ids)`; with parts `e.id IN (ids) OR
      e.parent_id IN (ids) OR p.parent_id IN (ids)` (the tree is at most three
      levels: equipment, component-unit, component; BR2-02). Fewer **selected**
      ids found than asked → **404 for the whole request**, "Some of the
      selected equipment was not found or is not at your units", naming none
      (BR1-02).
    - With parts: `expand_selection` puts each selected node first, then its
      parts level by level by code, **leaving out scrapped parts** (a scrapped
      part is gone; a scrapped node that was *selected* is printed). Parts
      inherit the root's unit, so they pass with it. The result is
      de-duplicated by id, keeping the first occurrence (a parent and its own
      part both ticked → one label each). Total after expansion capped at 300
      too (400, "Too many labels — print in smaller groups").
- **`backend/settings.py`:**
  - `get_setting_text(cur, key, default)` beside `get_setting_int`;
  - `label_base_url(cur)`: the stored value passed through
    `normalise_base_url`; a stored value that fails it (hand-edited) is logged
    as a warning and the default is used, as `get_setting_int` does (BR2-07);
  - code default `DEFAULT_LABEL_BASE_URL = "https://vel-yantra.mspv.app"`,
    **no migration row** (§ 6);
  - `GET/PUT /api/settings/labels` (`settings:read` / `settings:edit`), saved
    with the `SELECT … FOR UPDATE` + `INSERT … ON DUPLICATE KEY UPDATE` + log
    line "Setting … changed by …: old → new" shape of `put_app_settings`
    (ISO 27001 A.8.15).

### Frontend
- **Router:** `/e/:code` → `views/EquipmentByCodeView.vue` (new): calls
  `by-code` and **replaces** the route with `/equipment/:id` (so Back doesn't
  loop), or shows the not-found page. It needs sign-in like every page;
  keycloak-js returns to the same link after login. Nothing is added to
  `PUBLIC_PATHS` (BR1-11).
- **`EquipmentView.vue`:** a tick column; **select all on this page**; the
  selection (a set of ids) is kept across pages of the same filters and
  **cleared when a filter or the search changes**; at 300 further ticks are
  refused with a hint "300 labels at most — print this group first" (BR1-03);
  **Print labels (n)** opens `/labels?ids=…` in a **new tab** (base pattern
  § Print / Export Views), so the list and its ticks stay as they were
  (BR2-05).
- **`EquipmentDetailView.vue`:** **Print label** with the two choices; opens
  `/labels?ids=<id>&parts=1|0` in a new tab.
- **`views/LabelsPrintView.vue`** (new, route `/labels`): reads `ids` and
  `parts` from the **query** (survives reload and a new tab; BR1-05), calls
  `POST /labels`, and lays out:
  - one block per sheet, `width: 210mm; height: 297mm; break-after: page;
    overflow: hidden`, with `@page { size: A4; margin: 0 }`, the 3 × 5 grid
    centred (27 mm sides, 18.5 mm top and bottom);
  - cells `width: 52mm; height: 52mm; box-sizing: border-box` with a 0.2 mm
    grey border inside the box as the cut line, so the pitch stays 52 mm;
  - the QR SVG in a 38 mm box, inserted with `v-html` — safe because the SVG
    is path data only; the URL inside it is built from a validated setting and
    a validated code, and no database text is in it (BR1-10). The code, site and
    name are ordinary text bindings;
  - the print note and a **Print** button (`window.print()`), both `.no-print`;
  - on a 400 or 404 the page shows the server's message and no sheet
    (BR2-05).
  The existing print reset in `assets/main.css` (`.no-print`, `.app-shell
  { height: auto; overflow: visible }`, no sidebar margin or content padding)
  already keeps the app shell from clipping the sheets.
- **`frontend/src/utils/labelSheets.js`** (new, pure): `parseLabelQuery(query)`
  and `chunkSheets(labels, perSheet = 15)`.
- **`SettingsView.vue`:** a *Labels* card for the link address (form with
  `settings:edit`, read-only with `settings:read`), showing the default until
  the first save.

### Tests
- Pure (`test_labels_core.py`): `label_url` (no double slash);
  `normalise_base_url` (trailing slash removed, host lower-cased, path / query /
  fragment / user-info / other schemes refused, over 40 characters refused);
  `expand_selection` (order, de-duplication, scrapped parts, cap); `qr_svg` is
  level Q, border 4, has a `viewBox`, no width/height and no XML declaration,
  and the longest code (12 characters) at the default address is **version ≤
  4**, and at a 40-character address **≤ 5** (checked from the `QRCode`
  object's `version`; the library has no reader, so decoding is the manual scan
  check).
- API: by-code found / unknown → 404 / malformed → 404 / at a unit the user
  lacks → 404 (same body) / lower-case accepted; labels: in order with parts;
  without parts; parent and its part both selected → one each; scrapped part
  not expanded; scrapped node selected → printed; site code present; over 300
  (before and after expansion) → 400; empty, repeated or non-integer ids → 400;
  a node outside the user's units → 404 naming none; admin and
  `equipment:read_all_units` pass; a user with no accessible units → 404, no
  SQL error; settings read (default before any save) / save / bad URL → 400 /
  the change logged / a corrupt stored value → default. A fixture deletes the
  `label_base_url` row after each settings test, as for `upload_max_mb`
  (BR2-07).
- Frontend (vitest): `parseLabelQuery`, `chunkSheets` (15 per sheet, 16 → 2
  sheets, 0 → none).

## 4. Rules

- **The link holds the code, not the id:** ids are internal; codes are what the
  plant reads and what never changes. The `/e/` prefix keeps the link short.
- **Code check:** the route accepts `[A-Za-z0-9]{1,12}`; the code is
  upper-cased (codes are stored upper-case, S002) and must match `CODE_RE`, else
  404 with no query (BR1-08).
- **Link address** (BR1-04): `urllib.parse.urlsplit`; scheme `https` or `http`;
  a host (a port is allowed) with no user-info; empty path, query and fragment;
  host lower-cased; stored without a trailing slash; **at most 40 characters**.
  Worst case 40 + 3 + 12 = 55 bytes → version 5 at level Q (45 modules with the
  quiet zone → 0.84 mm per module at 38 mm), still well readable.
- **Scrapped and out-of-use nodes** still resolve by code (the page shows the
  status); a selected scrapped node is printed; scrapped *parts* are not added
  by "with its parts".
- **Long names and long site codes** are cut to one line in CSS
  (`text-overflow: ellipsis`). The code is never cut: its font size is set so
  12 characters fit; the site code takes the space left on that line and is
  cut if a site code is long (site codes may be 20 characters; BR2-04).
- **Site** is the node's current site (through its root unit), looked up when
  printing.
- **Who may print:** whoever may see the nodes — unit access, as the equipment
  page. Printing a label changes nothing.
- **S013 network gate** applies as on every page: an **IT admin** who scans a
  label on mobile data gets the "plant network only" card, by design
  (BR1-11).

## 5. API

| Method & path | Access |
|---|---|
| `GET /api/equipment/by-code/<code>` → `{id}` | unit access, as `GET /api/equipment/<id>`; unknown and no access are the same 404 |
| `POST /api/equipment/labels` `{ids, with_parts}` → `{labels}` | unit access for every node; any missing → 404 for all |
| `GET /api/settings/labels` → `{base_url}` | `settings:read` |
| `PUT /api/settings/labels` `{base_url}` | `settings:edit` |

## 6. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| QR made in the backend (SVG) | Backend heavy, frontend light; one encoder, tested in Python; SVG prints sharp at any size | A frontend QR library (logic in the browser) |
| `qrcode` (python-qrcode), not `segno` (gate A, 18-10-2026) | The user's rule: use a library whose bugs get fixed. `qrcode`: encoder bug fixes merged Jan–Mar 2026 (mask evaluation #388/#389, `glog(0)` #330, thread safety #421, Python 3.14), many PRs in 2026; last release 8.2 (01-05-2025), so those fixes are not released yet — none affects short URLs at level Q, and Gunicorn runs sync workers (no threads) | `segno`: only one build commit since 03-2025; an encoder padding bug open since 05-2023 (#123, #148) with an unmerged fix PR (#153, 08-2026) |
| Browser printing of an HTML sheet | Exact millimetre layout with CSS; no PDF library; any office printer | A PDF from the backend (heavier dependency; better for label printers — later) |
| Link address from a setting, default the public address | Labels carry the public address whoever printed them; a domain change affects only new labels | The address of the browser that prints |
| Setting default in code, no migration row | Nothing to migrate; the card shows the default until the first save. Departs on purpose from `upload_max_mb` and `internal_networks`, which also have a migration row (BR1-04) | A migration v11 inserting the default |
| `/e/<code>` link | Short link → coarser QR; codes never change | `/equipment/<id>` (internal number) |
| Level Q, version 4 (BR1-01) | Paper on machines gets dirty; 0.93 mm modules read well | Capitals-only link for version 3 (odd link); level M (less robust) |
| Unit access, one query, 404 for all (BR1-02) | The same rule and answer as the equipment page; no N+1; reveals no code | A site-scoped key check (weaker than unit access); 403 (reveals the code exists) |
| Selection kept across pages, cleared on filter change (BR1-03) | A unit of 120 presses prints in one run; a new filter is a new group | Per page only (several runs) |
| Code, site and name on the label | Identity, plus the site the user asked for | Unit or path (wrong after a move) |
| A4 sheet of 15 | Paper now (user); cut lines at 52 mm | One label per page; adhesive sheet formats (later) |

## 7. Tests and acceptance

See § 3 Tests.

### Manual checks
Important:
- [ ] Print a sheet on the office printer at 100 %: each cut square measures
  52 mm with a ruler.
- [ ] Scan a printed label with an Android phone's camera and with an iPhone's
  camera, on mobile data: the link opens Yantra, asks for login if needed, and
  shows that equipment's page.
- [ ] A crumpled or oil-marked label (rub a finger of grease across a corner)
  still scans.

Also:
- Equipment list: tick across two pages of a unit filter, print: all of them
  come out; changing the filter clears the ticks.
- The equipment page prints a node with its parts; a scrapped part is left out.
- A long name is cut with "…"; the code and site are whole.
- As IT admin on mobile data, a scanned label shows the "plant network only"
  card (S013, expected).

### Acceptance
- `tooling/run-tests.bat` green, the frontend build clean.

## 8. Open questions and assumptions

1. ~~**What goes under the QR.**~~ Decided 18-10-2026: code, site and name.
2. ~~**The public address.**~~ Decided 18-10-2026: `https://vel-yantra.mspv.app`
   everywhere.
3. **Assumption:** the paper is plain A4, cut by hand and fixed with clear tape
   or a pouch; no adhesive label stock yet.

## 9. Amendments

(none)

## Gate A — 18-10-2026 (KLA)

Approved. At the gate: the label shows the site code as text beside the code (the
code itself and the link hold no site); the QR library is `qrcode`, not `segno`
(the user's rule: use a library whose bugs get fixed; § 6).

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 18-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 QR geometry at level Q | major | **Accepted** (option 1): level Q, version 4, 0.93 mm per module with the quiet zone; test `version ≤ 4` (§ 2, § 3, § 6) |
| BR1-02 access check of the labels endpoint | major | **Accepted** (option 1): unit access in one query; missing or no access → the same 404 for the whole request, naming none; by-code the same (§ 3, § 4, § 5) |
| BR1-03 selection, pages and the cap | minor | **Accepted** (option 1): kept across pages, cleared on filter or search change, 300 at most (§ 1, § 3) |
| BR1-04 link-address validation | minor | **Accepted** (option 1): `urlsplit` rules, 40 characters at most, `get_setting_text`, the `put_app_settings` shape, the no-migration departure stated (§ 3, § 4, § 6) |
| BR1-05 print layout and the ids | minor | **Accepted**: per-sheet blocks with page breaks, border-box cut lines, `omitsize`, ids in the query, the existing print reset named (§ 3) |
| BR1-06 `with_parts` edge cases | minor | **Accepted**: id rules, default false, order by `_children`, scrapped parts left out, de-duplication, cap after expansion (§ 3, § 4) |
| BR1-07 dependency health | minor | **Accepted**; at gate A the user chose the library whose bugs get fixed: `qrcode` (§ 6); `uv.lock` updated (§ 3) |
| BR1-08 code check | nit | **Accepted**: route pattern, `CODE_RE`, 12 characters (§ 3, § 4) |
| BR1-09 standards wording | nit | **Accepted**: ISO 55001 § 7.5 instead of ISO 55002; ISO/IEC 18004 levels and no module size; ISO 14224 tag number; TPM visual line (§ 2) |
| BR1-10 how the SVG is inserted | nit | **Accepted**: `v-html`, with the reason it is safe (§ 3) |
| BR1-11 S013 interaction | nit | **Accepted**: no public path; IT admin on mobile data sees the card, in the plain checks (§ 4, § 7) |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 18-10-2026

No blocker or major finding; the loop ends here.

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 empty accessible-unit set | minor | **Accepted**: 404 at once, no query; test (§ 3) |
| BR2-02 parts expansion N+1 | minor | **Accepted**: one query over three levels; pure `expand_selection` (§ 3) |
| BR2-03 segno boosts Q to H | minor | **Accepted**, then moot: the library changed to `qrcode` at gate A, which keeps the level asked for; test `Q` (§ 3) |
| BR2-04 long site codes | minor | **Accepted**: the site code is cut, never the code (§ 4) |
| BR2-05 new tab; errors on the print page | minor | **Accepted**: print page opens in a new tab; shows the message on 400/404 (§ 3) |
| BR2-06 `svg_inline` | nit | **Accepted** in substance: one `<svg>`, no declaration, no fixed size (§ 3; `qrcode` at gate A) |
| BR2-07 corrupt stored address; test cleanup | nit | **Accepted**: `label_base_url(cur)` falls back with a warning; cleanup fixture (§ 3) |
| BR2-08 no regex converter; permission decorator | nit | **Accepted** (§ 3) |
