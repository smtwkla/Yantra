```
Step: S014 — QR labels
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

# S014 — Brief review, round 2

**Verdict: no `blocker` or `major` finding is open.** Every round-1 finding marked
`Accepted` is reflected in the brief text (checked section by section, not only in
the Review log), and the two user decisions new since r1 — the site code on the
label, `https://vel-yantra.mspv.app` everywhere — are carried through § 1, § 2, § 3,
§ 4, § 6 and the tests consistently. What remains are five `minor` findings (rules
the coder would otherwise decide alone, and two edge cases) and three `nit`s.

Reviewed against: the brief as revised; `2-brief-review-r1.md`; `docs/Plan.MD`
§ 1 (URL), § 4.1, § 6, § 8; `docs/Maintenance-Philosophy.md`; `docs/Plant-Facts.md`;
`.claude/SMTW-WebApp-Base.md` (frontend auth, internet exposure, print views);
`CLAUDE-COMMON.md`; `CLAUDE.md`; the working-tree code: `backend/equipment.py`
(`NODE_JOINS`, `_NODE_COLUMNS`, `accessible_unit_ids`, `_can_access`,
`load_node_for_user`, `_children`, `list_equipment`), `equipment_core.py`,
`settings.py`, `auth_utils.py` (`PUBLIC_PATHS`, `user_unit_ids`), `access_control.py`,
`network_core.py`, `config_rbac.py`, `masters_core.py`, `local_db.py` (the `code`
column), `tests/test_settings_api.py`, `tests/test_equipment_api.py`,
`tests/conftest.py`; `frontend/src/router/index.js`, `stores/navigation.js`,
`App.vue`, `api.js`, `assets/main.css`, `views/EquipmentView.vue`,
`EquipmentDetailView.vue`, `SettingsView.vue`; `tooling/build/nginx.conf`,
`Dockerfile.backend`. The QR numbers were checked by running segno 1.6.6 itself (in a
scratch directory, nothing added to the repo).

---

## Round-1 answers, verified in the text

| Finding | Where it now stands in the brief | OK |
|---|---|---|
| BR1-01 level Q, version 4 | § 2 (33 × 33, 41 with quiet zone, 0.93 mm), § 6, § 3 Tests `version ≤ 4` | yes — see the segno check below |
| BR1-02 unit access, one query, same 404 | § 3 by-code and labels, § 4 "Who may print", § 5 table, tests | yes (one gap: BR2-01) |
| BR1-03 selection across pages, cleared on filter change, 300 cap | § 1.3, § 3 `EquipmentView.vue` | yes |
| BR1-04 `urlsplit` rules, 40 characters, `get_setting_text`, `put_app_settings` shape, no-migration departure stated | § 3 settings, § 4 Link address, § 6 | yes |
| BR1-05 per-sheet blocks, border-box cut lines, `omitsize`, ids in the query, print reset named | § 3 `LabelsPrintView.vue` | yes |
| BR1-06 id rules, default false, `_children` order, scrapped parts out, de-dup, cap after expansion | § 3 labels, § 4 | yes (query shape: BR2-02) |
| BR1-07 keep segno, reason in § 6, `uv.lock` | § 3 Dependency, § 6 | yes |
| BR1-08 route pattern, `CODE_RE`, 12 characters | § 3, § 4 | yes (wording: BR2-08) |
| BR1-09 ISO 55001 § 7.5, ISO/IEC 18004 levels, ISO 14224 tag number, TPM line | § 2 | yes |
| BR1-10 `v-html` with the reason | § 3 | yes |
| BR1-11 no public path; IT admin card in the plain checks | § 4, § 7 | yes |

**The QR numbers, checked with segno 1.6.6** (`segno.make(text, error="q")`,
`symbol_size(border=4)`):

| Link | Bytes | Version | Level | Modules with quiet zone | mm per module at 38 mm |
|---|---|---|---|---|---|
| `https://vel-yantra.mspv.app/e/VBM001` | 36 | 4 | Q | 41 | 0.93 |
| `https://vel-yantra.mspv.app/e/ABCD12345678` (longest code) | 42 | 4 | Q | 41 | 0.93 |
| 40-character address `/e/ABCD12345678` | 55 | 5 | Q | 45 | 0.84 |
| `http://a.b/e/AB123` (shortest possible) | 18 | 2 | Q | 33 | 1.15 |

So § 2, § 4 and the two test bounds (`≤ 4` at the default address, `≤ 5` at 40
characters) are exactly right. The same run found one thing the brief does not
decide (BR2-03).

---

## Findings

### BR2-01 — `minor` — The labels query with an **empty** accessible-unit set

**Problem.** § 3 says the labels query is "filtered by `u.id IN (<accessible units>)`
when the unit list is not `None`". `accessible_unit_ids` returns three shapes: `None`
(every unit), a non-empty set, and an **empty set** (a user with a membership but no
unit rows, or none at all — "no access at all, not an error", per its docstring). An
empty set makes `u.id IN ()`, a SQL syntax error → 500. `list_equipment` handles it
explicitly (`if not unit_ids: return jsonify(empty)`); `_can_access` handles it
implicitly (`unit_id in set()` is false). The brief covers neither for the labels
endpoint. by-code is safe if it reuses `_can_access`.

**Why it matters.** A user with no units cannot reach the list, but can send the
request (an old tab, a typed URL); a 500 on a reachable endpoint is a bug, and the
coder would have to notice the third shape alone.

**Options.**
1. State it: "an empty set → the same 404 as a missing node, **without a query**",
   mirroring the list's early return.
2. Treat the empty set as `IN (NULL)`. Works but hides the case.

**Recommendation.** Option 1; one line in § 3, and a test "a user with no units →
404" beside "a node outside the user's units → 404".

---

### BR2-02 — `minor` — How the parts are fetched is not decided, and the ordering belongs in the pure core

**Problem.** § 3 says "**One query**, joined through `NODE_JOINS`" for the selected
ids, then "with parts: each selected node is followed by its parts, level by level
**as `_children` orders them**". Read literally, `_children(cur, node)` is two
queries per selected node — up to 600 for a 300-id request — which is the N+1 that
BR1-02 option 3 rejected. r1 proposed the subtree in the same query ("parts inherit
the root's unit, so they pass or fail with it"); the brief kept the access
argument but not the query shape.

Also, "selected order → direct parts by code → their parts by code, scrapped parts
left out, de-duplicated by id keeping the first occurrence, cap after expansion" is
business logic on plain rows. By CLAUDE-COMMON *Pure core, thin shell* it belongs in
`labels_core.py` with unit tests, not inline in the route.

**Options.**
1. **One query**, `NODE_JOINS` plus the unit filter, with
   `e.id IN (ids) OR e.parent_id IN (ids) OR p.parent_id IN (ids)` when `with_parts`
   (the fragment already joins `p` and `gp`, so a part's root unit is resolved in the
   same row); then a pure `expand_selection(ids, rows, with_parts)` in `labels_core`
   returns the ordered, de-duplicated list and the shell checks the access count on
   the **selected** ids only (the extra rows are parts) and the cap on the result.
2. Three set queries: the selected rows; `parent_id IN (ids)`; `parent_id IN (those)`.
   Also fine; slightly more code.
3. `_children` per node. Rejected: N+1.

**Recommendation.** Option 1. Add `expand_selection` to the § 3 list of pure
functions and move the ordering/de-dup/cap tests to `test_labels_core.py` (the API
tests keep one end-to-end case each). State that the "fewer rows than ids → 404"
count is taken on the selected ids, not on the whole result.

---

### BR2-03 — `minor` — "Level Q" is not what segno does by default: decide `boost_error`

**Problem.** `segno.make(..., error="q")` has `boost_error=True` by default: when a
higher level fits in the same version, segno **raises it to H**. Checked: byte
lengths 21–24 and 33–34 come out as level H, not Q. With the default address the
links are 35–42 bytes, so the tests the brief lists pass — but with a 26-character
address (`https://vel-yantra.mspv.in`) a 5-character code gives 34 bytes → H, and an
8-character code → Q. The rule "level Q" in § 2 and § 6 and the test "`qr_svg` is
level Q" are then true only for some inputs, and the coder would discover this from a
failing test and pick a fix alone.

A related default: `micro=None` lets segno make a Micro QR for very short content.
No label can be that short (the minimum link is 18 bytes; Micro M4 holds 15), but a
test with a toy string would get `version == "M1"` and `<=` would raise `TypeError`.

**Options.**
1. **Keep the boost and say so**: "level Q, raised to H by the encoder when it costs
   no size" — more damage tolerance for free, no change to the geometry statements
   (the version is chosen before the boost). Test `qr.error in ("Q", "H")` and
   `qr.error == "Q"` for the default-address cases in the table above.
2. `boost_error=False`: exactly Q always. Deterministic; forgoes the free gain.

**Recommendation.** Option 1; and pass `micro=False` so `version` is always an int.
Put the three keyword arguments (`error="q"`, `boost_error=True`, `micro=False`) in
the `qr_svg` description in § 3.

**For the owner:** ISO/IEC 18004 defines the four levels as how many codewords can
be lost and still recovered (L 7 %, M 15 %, Q 25 %, H 30 %). A higher level needs
more modules for the same text — unless the text is short enough that the next
version up is not needed, which is when segno's boost applies: the same square,
more tolerance.

---

### BR2-04 — `minor` — Site codes may be 20 characters; the label's code line needs a rule for them

**Problem.** § 1.2 puts the code and the site code on **one line**, and § 4 says "the
code is never cut: its font size is set so 12 characters fit beside the site code".
`SITE_CODE_RE` is `^[A-Z][A-Z0-9-]{1,19}$` — a site code may be **20 characters**.
A 12-character code in large bold plus a 20-character site code do not fit in
≈ 50 mm at any size an operator can read. Today's sites (`SMTW`, `BRICKS`, `SSVT`,
the farms) are short, so this is an edge, not the common case — but the brief
should say which text yields.

**Options.**
1. The **site code is the one cut** (`text-overflow: ellipsis`, as the name is); the
   code is never cut. One CSS rule; the layout stays.
2. The site code moves to the name line (`SMTW · Vertical blade mill`). Changes the
   user's agreed layout.
3. Cap the font so both always fit. Rejected: unreadable for a 20-character site.

**Recommendation.** Option 1; a half-sentence in § 4 "Long names", and the manual
check "the code and site are whole" becomes "the code is whole; a long site code is
cut".

---

### BR2-05 — `minor` — Where the print page opens: a new tab, and why

**Problem.** § 3 says "**Print labels (n)** opens `/labels?ids=…`" and "**Print
label** … opens `/labels?ids=<id>&parts=1|0`", without saying in the same tab or a
new one. The base pattern (`SMTW-WebApp-Base.md` § Print / Export Views) is
"triggered by a button that opens the print route in a new tab". It matters here
more than usual: the selection lives in `EquipmentView`'s component state, so a
same-tab navigation to `/labels` and Back **loses the ticks** — the user who printed
a 120-press unit cannot adjust and reprint without ticking again. The brief's
"ids in the query (survives a new tab; BR1-05)" assumes a new tab without saying it.

**Recommendation.** Say in § 3: both buttons open `/labels?…` in a **new tab**
(`window.open` or `<a target="_blank">`); the list keeps its ticks. Also say what the
print page shows on a 400/404 from `POST /labels` (the usual `alert-danger` with the
message; no sheets) — one line.

---

### BR2-06 — `nit` — Use `svg_inline`, not `save(kind="svg")`, for markup that goes into `v-html`

`qr.save(out, kind="svg", border=4, omitsize=True)` emits `<?xml version="1.0"
encoding="utf-8"?>` and the SVG namespace. Inside `v-html` the XML declaration is
parsed by HTML as a bogus comment — harmless, but sloppy. segno has
`qr.svg_inline(border=4, omitsize=True)` for exactly this: no declaration, no
namespace, a `viewBox` only. Checked output:
`<svg viewBox="0 0 41 41" class="segno"><path class="qrline" stroke="#000" d="M4 4.5h7m1 …">`
— path data only, which also confirms the BR1-10 safety argument. Name it in § 3.

---

### BR2-07 — `nit` — Reading the stored address, and keeping the tests independent

- `settings.py`'s pattern (module docstring, `get_setting_int`, `read_stored_networks`)
  is: a stored value that no longer validates **falls back to the default with a
  warning**, so a hand-edit cannot break the feature. The brief's `get_setting_text`
  returns the text or the default; say that the labels read goes through a
  `label_base_url(cur)` wrapper (like `upload_max_mb(cur)`) that applies
  `normalise_base_url` and falls back on failure. Test: a stored `not a url` → labels
  carry the default, and a warning is logged.
- The test "settings read (default before any save)" depends on no earlier test
  having saved a row. `conftest.py`'s `upload_limit_mb` fixture writes the row and
  puts the seed back afterwards; the brief should ask for the same shape for
  `label_base_url` (remove the row afterwards, since there is no seeded row).

---

### BR2-08 — `nit` — Two wording fixes on the by-code route

- "The route accepts `[A-Za-z0-9]{1,12}`": Flask has no regex converter; keep the
  default `<code>` converter and do the check in code (upper-case, `CODE_RE`, else 404
  before any query), which § 3 already describes. Drop the pattern or mark it as the
  check, not the route.
- Name `@require_perm("equipment:read")` on both new equipment routes explicitly, as
  every route in `equipment.py` has it (base pattern: immediately after the route,
  always). § 5's "unit access, as `GET /api/equipment/<id>`" implies it; one word
  removes the doubt.

---

## Checked and found consistent

- **User decisions since r1.** The site code: § 1.2 (small type, right of the code),
  § 2 (why it is printed and when it goes stale), § 3 (`site_code` in the response,
  from `s.code AS site_code` already in `_NODE_COLUMNS`), § 4 (current site through
  the root unit), § 6, tests ("site code present"). The address: § 1.1, § 1.6, § 3
  `DEFAULT_LABEL_BASE_URL`, § 8; it matches Plan.MD § 1 ("URL `vel-yantra.mspv.app`")
  and Keycloak's redirect URI `https://vel-yantra.mspv.app/*`.
- **Unit-access rule.** `load_node_for_user` → `_can_access(cur, root_unit_id)` →
  `user_unit_ids("equipment:read")`; the list filters `u.id IN (...)`. The brief's
  labels check is the same predicate in SQL, and parts inherit the root unit through
  `NODE_JOINS`'s `COALESCE(gp.unit_id, p.unit_id, e.unit_id)`, so the "parts pass with
  their root" claim is true. Admin and `equipment:read_all_units` give `None`, as
  stated. "Same 404, naming none" matches `load_node_for_user` and the existing test
  `test_engineer_sees_only_their_units` (404 for a node elsewhere).
- **Scrapped parts.** `_check_parts_scrapped` means a scrapped component-unit has only
  scrapped components, so "leave out scrapped parts" never orphans a live grandchild.
- **Codes.** `format_equipment_code` = `^[A-Z]{2,4}$` prefix + `zfill(3)` digits that
  grow; `code VARCHAR(12)`; `uq_equipment_code` makes by-code single-valued; codes are
  stored upper-case. `CODE_RE` and the 12-character limit are right.
- **Routes.** `/e/:code` cannot collide with `/equipment/:id(\d+)`; `/by-code/<code>`
  and `/labels` cannot collide with `/<int:node_id>`; `canOpenRoute` returns true for
  any route that is not a nav item, so neither the router guard nor `App.vue` redirects
  `/e/…` or `/labels`; `App.vue` renders `<router-view>` only once `authenticated`, so
  the by-code view calls the API after login; nginx `try_files … /index.html` serves
  both; `PUBLIC_PATHS` unchanged; the S013 gate (`INTERNAL_ONLY_ROLES = ("it_admin",)`,
  `gate_refuses`) applies to `/api/equipment/by-code/...` like any API path, so the
  IT-admin-on-mobile-data note in § 4 and § 7 is accurate. `apiPost` exists in
  `api.js`.
- **Settings.** `/api/settings/labels` is its own route, like `/network`, so
  `test_settings_api.py`'s exact-body assertions on `/app` are untouched;
  `test_access_log_api.py` enumerates only `/api/settings/access-log`. The
  `SELECT … FOR UPDATE` + `INSERT … ON DUPLICATE KEY UPDATE` + `logger.info("Setting
  %s changed by %s: %s -> %s")` shape is exactly `put_app_settings` / `put_network`.
  The *Labels* card follows `SettingsView.vue` (form with `settings:edit`, read-only
  with `settings:read`).
- **Print layout.** `main.css` has the print reset the brief names (`.no-print`,
  `.app-shell { height: auto; overflow: visible }`, `.app-main { margin-left: 0 }`,
  `.app-content { padding: 0 }`). 3 × 52 = 156 mm and 5 × 52 = 260 mm leave the
  27 mm / 18.5 mm margins stated. The 38 mm QR leaves 14 mm for the two text lines
  inside a 52 mm cell: enough for a ≈ 4 mm bold code line and a ≈ 3 mm name line.
- **Dependency.** `segno` 1.6.6 installs cleanly on Python 3.12 with no dependencies;
  `uv add segno` updates `pyproject.toml` and `uv.lock`, which `Dockerfile.backend`
  installs with `uv sync --frozen`. § 6 records the 12-month-rule departure as
  CLAUDE-COMMON asks.
- **Standards.** Cited correctly and explained: ISO 14224 § 8 (the tag number as the
  permanent identity, separate from location and description — why the label carries
  the code and not the path); ISO 55001 § 7.5 (decide what asset information is
  needed and keep it accurate — the verification walk and S015 are how); ISO/IEC 18004
  (symbol, four error-correction levels, 4-module quiet zone, no prescribed module
  size); ISO 27001 A.8.15 (logging who changed the setting); TPM visual management
  (`Maintenance-Philosophy.md` § 5–6: the label is the first visual on the machine,
  the CIL sheet and the red tag hang off the same code). No new RBAC key; nothing in
  `config_rbac.py` or `test_rbac.py` changes.
- **Track: full** stays right (new dependency, endpoints beyond CRUD). No migration,
  no transaction beyond the settings write's existing shape, no concurrency rules.
- **Manual checks.** The ruler, the two-platform scan on mobile data and the grease
  test are rightly **important**; the list, parts, long-name and IT-admin-card checks
  are rightly plain.
- **Existing tests.** Nothing the brief adds changes an existing route's body or
  status; the frontend tests (`frontend/tests/*.test.js`) cover pure helpers only, and
  `labelSheets.js` joins them in the same shape.
