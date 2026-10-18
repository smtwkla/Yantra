```
Step: S014 — QR labels
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 18-10-2026
```

# S014 — Brief review, round 1

**Verdict: two `major` findings are open (BR1-01, BR1-02); no `blocker`.** The
shape of the step is right — a code-only link, backend SVG, an A4 sheet printed by
the browser, the address as a setting — but the QR geometry the brief states (and
tests for) is wrong at level Q, and the labels endpoint's access check is specified
differently from how every other equipment read works.

Reviewed against: the brief; `docs/Plan.MD` § 4.1, § 6, § 8; `docs/Maintenance-
Philosophy.md`; `docs/Plant-Facts.md`; `.claude/SMTW-WebApp-Base.md` (frontend
auth, internet exposure, print views, testing, pitfalls); `CLAUDE-COMMON.md`;
`CLAUDE.md`; the working-tree code (S013 included): `backend/equipment.py`,
`equipment_core.py`, `settings.py`, `auth_utils.py`, `config_rbac.py`,
`access_control.py`, `network_core.py`, `app.py`, `local_db.py`,
`masters_core.py`, `tests/`; `frontend/src/router/index.js`, `stores/auth.js`,
`stores/navigation.js`, `App.vue`, `api.js`, `main.js`, `assets/main.css`,
`views/EquipmentView.vue`, `EquipmentDetailView.vue`, `SettingsView.vue`;
`tooling/build/nginx.conf`, `Dockerfile.backend`; `docs/Keycloak.md`; PyPI and
GitHub for `segno` and `qrcode`.

---

## Findings

### BR1-01 — `major` — The QR geometry is wrong at level Q: version 4, not 3; the stated test would fail

**Problem.** § 2 and § 6 say "version 3, 29 × 29 modules → about 1.3 mm per module
at 38 mm", and § 3 Tests asks the coder to assert that the longest code at the
default address "fits in version ≤ 3". Checked against the ISO/IEC 18004 capacity
table:

- The link `https://vel-yantra.mspv.app/e/ABCD1234` is 38 characters. It contains
  lower-case letters, so it is encoded in **byte mode** (alphanumeric mode knows
  only digits, capitals and ` $%*+-./:`).
- Byte-mode capacity at level **Q**: version 3 = 32 characters, version 4 = 46.
  Even `VBM001` (36 characters) needs **version 4 (33 × 33 modules)**. In bits:
  version 3-Q holds 34 data codewords = 272 bits; 38 bytes need 4 + 8 + 38 × 8 =
  316 bits. Splitting the code part into an alphanumeric segment does not help
  (309 bits).
- Version 3 at level **M** (42 characters) is where "version 3" comes from — the
  brief has level Q's robustness with level M's size.
- "1.3 mm per module" is 38 ÷ 29: it leaves out the quiet zone the brief itself
  requires. With the quiet zone of 4 on each side, version 3 is 37 modules
  (1.03 mm at 38 mm) and version 4 is 41 modules (**0.93 mm**).

**Why it matters.** The pure test as written cannot pass, so the coder must either
change the level, the host or the assertion on their own — exactly the decision a
brief exists to take. The label is still perfectly readable at 0.93 mm per module
(phone cameras read modules of about 0.5 mm at close range; the usual rule of thumb
is a scanning distance of about ten times the symbol's width, so about 30 cm here),
but the brief must say the true numbers, because the whole § 2 argument "short link
→ coarse code" rests on them.

**Options.**
1. **Keep level Q and the lower-case link; state version 4.** Text: "version 4,
   33 × 33 modules, 41 with the quiet zone → about 0.93 mm per module at 38 mm".
   Test: `qr.version <= 4` and `qr.error == "Q"`. Simplest; nothing else changes.
2. **Encode the link in capitals** — `HTTPS://VEL-YANTRA.MSPV.APP/E/VBM001`. The
   whole string is then alphanumeric mode: 38 characters = 222 bits, which fits
   **version 3 at level Q** (1.03 mm per module). Scheme and host are
   case-insensitive by definition; vue-router 4 matches paths case-insensitively by
   default, and the lookup already upper-cases the code. Every phone camera opens
   an upper-case URL. This is a standard trick for small QR codes, and gives the
   coarser code the brief wants — at the price of an odd-looking link on the
   label and a `/E/` the frontend must accept (it does, unless a route sets
   `sensitive: true`).
3. **Drop to level M** to get version 3. Rejected: the brief's reason for Q (oil,
   scratches) is sound; losing 10 % of damage tolerance to save 4 modules is the
   wrong trade on a paper label.

**Recommendation.** Option 1, unless the user prefers the coarser code of option 2.
Either way, fix § 2, § 6 and the test, and bound the host length so the statement
stays true (BR1-04).

---

### BR1-02 — `major` — The labels endpoint's access check is not the one the register uses

**Problem.** § 3 says every node of `POST /labels` "must be readable by the user at
its site (`equipment:read`, site-scoped); any that isn't → 403". But in the code,
*reading* equipment is decided by **unit access**, not by a site key:
`load_node_for_user` → `_can_access(cur, node["root_unit_id"])` →
`accessible_unit_ids(cur)` (`user_unit_ids("equipment:read")`), and the list
filters `u.id IN (<accessible units>)`. `has_perm_at("equipment:read", site_id)` is
a weaker test: a technician with a membership at SMTW for units `KILN` only
*holds* `equipment:read` at site SMTW, yet may not see `SMTW.FWMILL` equipment. As
written, the labels endpoint would print labels the equipment page refuses to
show.

Also, the register answers "missing" and "outside your units" with the **same 404**
("nothing is revealed", `load_node_for_user`), while the brief gives by-code "404 /
the usual unit-access refusal" (which is that same 404 — § 3 Tests then says "other
site (refused)", ambiguous) and the labels endpoint a 403.

**Why it matters.** Access checks are the one place a brief must be exact: the
coder cannot be left to reconcile two rules, and a label is a durable artefact —
printing a code the user may not see is a leak on paper.

**Options.**
1. **Use the unit filter, as the list does.** One query: the selected ids (and,
   with `with_parts`, their subtree — parts inherit the root's unit, so they pass
   or fail with it) joined through `NODE_JOINS`, with `u.id IN (<accessible units>)`
   when `accessible_unit_ids` is not `None`. If fewer rows come back than distinct
   ids requested → refuse the whole request, naming none. Status: **404**, the same
   as `GET /equipment/<id>`, message "Some of the selected equipment was not found
   or is not at your units".
2. Same check, but 403. Rejected: it tells the caller the code exists.
3. Call `load_node_for_user` per id (up to 300 reads). Correct but N+1; rejected
   for a 300-row request.

**Recommendation.** Option 1. Rewrite § 3, § 4 "Who may print" and § 5 to say
"unit access, as the equipment page (`accessible_unit_ids`); a missing id and one
outside the user's units are the same 404, naming none", and the by-code tests to
"unknown code → 404; code at a unit the user lacks → 404 (same message)". Admin and
`equipment:read_all_units` holders pass as today (`unit_ids is None`).

---

### BR1-03 — `minor` — "Select all shown", pages and the 300 cap are not defined together

**Problem.** The list is paged at 50 (`PAGE_SIZE`). The brief says "select all
shown (which follows the current site / unit / class filters)", a cap of 300 ids
and "the selection is cleared when filters change" — but `EquipmentView` treats
the page number as part of the same URL query (`watch(route.fullPath, load)`), so
"when filters change" either clears the selection on every page turn (then 50 is
the real cap, and a unit of 120 presses needs three print runs) or it doesn't (then
the brief must say the selection survives paging and how the user sees it).

**Options.**
1. Selection = the ticked ids, kept across **pages** of the same filters, cleared on
   any change to a filter or the search; "select all shown" ticks the current
   page; the button shows the count; at 300 further ticks are refused with a hint.
2. Selection per page only; "Print labels" prints that page. Simplest; the user
   prints a big unit in several runs.

**Recommendation.** Option 1 — the manual check "select all shown with a unit
filter prints that unit's labels" implies it. State it in § 1.3 and § 3.

---

### BR1-04 — `minor` — The base-URL setting needs a length cap and a sharper validation rule

**Problem.** The QR version bound (BR1-01) holds only for the *default* host. The
setting is free text: a 70-character address makes a version 7 code (45 + 8
modules at 38 mm → 0.7 mm) with no warning. The brief's validation ("`https://` or
`http://`, a host, no path, query or trailing slash") also leaves out: user-info
(`https://a@b`), a fragment, a port (allow or not?), host case, and a maximum.

**Options.**
1. Validate with `urllib.parse.urlsplit`: scheme in `{http, https}`, `netloc` non-
   empty with no `@`, empty path/query/fragment, host lower-cased, stored without
   a trailing slash, and a **maximum of 40 characters** for the whole base URL.
   The worst case is then 40 + 3 + 8 = 51 bytes → version 5 at Q (capacity 60),
   45 modules with the quiet zone → 0.84 mm at 38 mm; say so in § 4.
2. No cap, compute the version per label and warn in the UI. Over-engineering.

**Recommendation.** Option 1. Two pattern notes for § 3: (a) add a
`get_setting_text(cur, key, default)` beside `get_setting_int` rather than a one-
off read, and keep the `SELECT … FOR UPDATE` + `INSERT … ON DUPLICATE KEY UPDATE` +
`logger.info("Setting %s changed by %s: %s -> %s")` shape of `put_app_settings`
(ISO 27001 A.8.15: who changed what, when); (b) the two existing settings each have
**both** a migration `INSERT IGNORE` default row and a code default (`upload_max_mb`
v6, `internal_networks` v10). Reading with a default alone works and the brief's
"no migration" is acceptable, but say in § 6 that it departs from that pairing on
purpose (the row appears on the first save; the Settings card shows the default
until then).

---

### BR1-05 — `minor` — Print reliability: say how the sheet is built, and pass the ids in the query

**Problem.** § 3 gives `@page { size: A4; margin: 0 }` and "a grid of 52 mm cells"
but not the parts that decide whether sheet 2 starts where it should: a per-sheet
container, explicit page breaks, and how cut lines are drawn without widening the
cell. Also "ids passed in the router state or a short query" leaves the choice to
the coder; router state is lost when the print page is opened in a new tab (the
base pattern's way for print routes) and is awkward to test.

**What exists already.** `assets/main.css` has a print reset (`.no-print`, and
`.app-shell { height: auto; overflow: visible }`, `.app-main { margin-left: 0 }`,
`.app-content { padding: 0 }`) — so the shell's `height: 100vh; overflow: hidden`
will **not** clip the sheets. Good; the brief should name it rather than "the
navbar is hidden".

**Recommendation.** Add to § 3:
- each sheet is its own block, `width: 210mm; height: 297mm; break-after: page;
  overflow: hidden`, with the 3 × 5 grid centred by the margins the brief computes
  (27 mm / 18.5 mm);
- cells `width: 52mm; height: 52mm; box-sizing: border-box` with the cut line as a
  thin (0.2 mm) grey border inside the box, so the pitch stays exactly 52 mm;
- the QR as the SVG scaled to a `38mm` box (segno: `omitsize=True`, so the SVG has
  only a `viewBox`), the code and name below;
- ids in the **query**, `/labels?ids=1,2,3&parts=1` (300 ids ≈ 1.5 KB, well under
  any limit), which survives reload and a new tab and gives the vitest helper a
  pure input to parse;
- the note on the page names Chrome/Edge as the browsers the sheet is checked in;
  the ruler check is the control.

---

### BR1-06 — `minor` — `with_parts` edge cases: duplicates, scrapped parts, order, bad ids

**Problem.** Not stated:
- a parent and its own part both ticked (level filter "All levels") with
  `with_parts` → the part appears twice;
- whether the expansion includes **scrapped** parts (§ 4 allows printing a
  scrapped node that was *selected*; a scrapped motor under a live press is a
  different case — it is gone);
- "tree order" — which order among siblings;
- a non-integer or repeated id, `with_parts` missing → 400 or default?

**Recommendation.** In § 3/§ 4: ids must be a non-empty list of distinct positive
integers (400 otherwise); `with_parts` defaults to false; the expansion follows
`_children` (direct parts, then their parts, each level by code) and **leaves out
scrapped parts**; the result is de-duplicated by id keeping the first occurrence.
Tests: parent + its part both selected → one label each; a scrapped part is not
expanded; a scrapped node selected is printed.

---

### BR1-07 — `minor` — The dependency check is the planner's to make, and segno trips the 12-month rule by the letter

**Problem.** § 3 tells the coder to "check it is maintained". CLAUDE-COMMON
(Dependency health) says to *flag* a library with no release in 12+ months and
suggest an alternative — that is a decision for the brief, not for the coder.
Checked today: `segno` 1.6.6 was released **12-03-2025** (19 months ago); the
repository (`heuer/segno`) is not archived, last pushed **23-07-2026**, 22 open
issues, 814 stars; pure Python, no dependencies, supports Python ≥ 3.5, writes SVG
with `border` and `error` parameters, follows ISO/IEC 18004:2015. The alternative
`qrcode` is at 8.2 (**01-05-2025**) — equally quiet — and pulls `colorama` on
Windows plus Pillow or pypng for raster output.

**Recommendation.** Keep `segno`, and record in § 6 *why* the quiet release
history is acceptable here: QR encoding is a finished specification (ISO/IEC
18004:2015), the library has no dependencies to rot, and the repository is active.
Note for the coder: `uv add segno` must update `backend/uv.lock`, which
`Dockerfile.backend` installs with `uv sync --frozen`.

---

### BR1-08 — `nit` — Validate the code in `/by-code/<code>` before the query; "4 + 4" is not a hard maximum

Codes are `CLASS_CODE_RE = ^[A-Z]{2,4}$` + `str(number).zfill(3)` — the number
"simply grows" past 999 (`format_equipment_code`), and the column is
`VARCHAR(12)`. So: match the route on `[A-Za-z0-9]{1,12}`, upper-case, check
`^[A-Z]{2,4}[0-9]{3,8}$`, and answer 404 without a query when it fails. In § 4
say "the longest code the column allows (12 characters)" rather than "4 letters +
4 digits"; the label font size should be set for 12 characters.

---

### BR1-09 — `nit` — Standards: tighten two citations and add the plain-language notes the owner is learning from

- **ISO 55002 "physical verification"**: ISO 55002 is guidance on applying ISO
  55001; it does not prescribe verification walks. Cite instead **ISO 55001 § 7.5**
  (the organisation decides what asset information it needs and keeps it
  accurate — a periodic physical check is how accuracy is kept) and name the
  fixed-asset audit as the accounting practice that does the same walk.
- **ISO/IEC 18004** does not prescribe a module size (the "X dimension"); it defines
  the symbol, the error-correction levels (L 7 %, M 15 %, Q 25 %, H 30 % of
  codewords recoverable) and the 4-module quiet zone. The readable module size is
  practice: say "about 0.9 mm per module, well above the ~0.5 mm phone cameras
  read at close range" once BR1-01 is settled.
- **ISO 14224 § 8** is fine (clause 8, recommended equipment data, has the tag /
  identification number as the first item). For the owner: ISO 14224 calls the
  code a **tag number** — the permanent identity of a maintainable item, kept
  separate from its location and description, which is exactly why the label
  carries nothing else.
- Worth one line: **TPM visual management** — the label is the first "visual" on
  the machine; later the CIL sheet and the red-tag (ticket) count hang off the
  same code (`Maintenance-Philosophy.md` § 6).

---

### BR1-10 — `nit` — Say how the SVG reaches the page

The frontend will put backend markup into the DOM. State the method and why it is
safe: `v-html` of the SVG returned by `/labels` is acceptable because segno's SVG
is path data only — no text from the database is inside it, and the encoded URL is
built from a validated setting and a validated code. (Alternative: an `<img>` with
a `data:image/svg+xml` URL, slightly safer, slower to lay out for 300 labels.)

---

### BR1-11 — `nit` — Record the S013 interaction explicitly

The brief is right not to add anything to `PUBLIC_PATHS`: `/e/<code>` is a frontend
route (nginx `try_files … /index.html` serves it), the browser calls
`/api/equipment/by-code/<code>` with a token like any page, and the network gate
applies as usual. Say so in § 4, with its consequence: an **IT admin** who scans a
label on mobile data gets the S013 "plant network only" card, by design
(`INTERNAL_ONLY_ROLES`). Add it to the plain manual checks so nobody files it as a
bug.

---

## Checked and found consistent

- **Plan.MD**: § 4.1 "code = permanent identity, printed on the QR label"; § 6 phone
  screen "equipment page (from QR)"; § 8 phase 2 includes QR labels; open question 3
  (code scheme) matches `format_equipment_code`. The label carries only the code and
  name — nothing that a move changes.
- **Track: full** is right: a new dependency (`segno`) and a new endpoint beyond
  plain CRUD; no migration, no RBAC key change.
- **RBAC**: no new permission key; `equipment:read` (`('*',)`, in `SITE_SCOPED`),
  `settings:read` / `settings:edit` as the other settings. No change to
  `config_rbac.py`; `test_rbac.py` policy tests unaffected.
- **Codes stored upper-case**: class codes are `^[A-Z]{2,4}$`, the number is
  digits; `uq_equipment_code` makes the by-code lookup single-valued.
- **Route plumbing for `/e/<code>` and `/labels`**: `canOpenRoute` allows routes
  that are not nav items, so neither the router guard nor App.vue's permissions
  watch redirects them; `App.vue` renders `<router-view>` only once
  `authenticated`, so the by-code view calls the API after login; keycloak-js
  `login-required` returns to the full `window.location.href` and strips the
  callback fragment; Keycloak's redirect URI `https://vel-yantra.mspv.app/*` covers
  `/e/*`; nginx's SPA fallback serves it; `/e/:code` cannot collide with
  `/equipment/:id(\d+)`, nor `/by-code/<code>` and `/labels` with `/<int:node_id>`.
- **A4 arithmetic**: 3 × 52 = 156 mm and 5 × 52 = 260 mm leave 27 mm and 18.5 mm
  margins, inside any office printer's unprintable edge; `@page { margin: 0 }` is
  honoured by Chrome/Edge.
- **Existing tests**: no current test enumerates equipment or settings routes
  (`test_access_log_api.py` enumerates only `/api/settings/access-log`), and the
  frontend tests cover pure helpers only; nothing the brief adds breaks them.
- **Settings UI**: a *Labels* card beside Uploads / Network follows
  `SettingsView.vue`'s pattern (form with `settings:edit`, read-only `<dl>` with
  `settings:read`).
- **Manual checks**: the ruler, the two-platform scan on mobile data and the grease
  test are the right ones to mark important; the list/page checks are rightly
  plain.
- **Out of scope** is sensible: no in-app scanner (phone cameras do it), no roll
  formats until the printer is chosen, no record of which nodes carry a label
  (the verification walk will).
