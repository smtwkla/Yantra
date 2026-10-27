Step: S061 — Properties for every class, and a GPS location
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 27-10-2026

Reviewed against: d6431f1 (no uncommitted step code; only `docs/steps/INDEX.md` is modified)

# S061 — Brief review, round 1

**Verdict: two `major` findings are open.** The precondition as written fails on every fresh
database (BR1-01), and the list of existing tests the change breaks is far short (BR1-02). The
design itself (two DECIMAL columns, the two flags, the seed, no Mobility seed) holds; the findings
below are about the rules the coder would otherwise decide alone, and about claims that do not
match the code. Facts file used: `scratch/brief-facts-S061.md`.

## Findings

### BR1-01 — major — The precondition breaks every fresh database

**Problem.** `_PRECONDITIONS[34]` queries `property_definitions` for a row named "GPS location".
`init_db` runs the precondition of **every pending version before any is applied**
(`local_db.py:1206-1212`). On an empty database (a new `vel_yantra_test_<run>_<worker>`, every
e2e lane database, a fresh install, and the upgrade tests that start from the frozen v13 fixture)
the table does not exist yet: the query raises pymysql error 1146, not `MigrationBlocked`, and
`ensure_schema` reports a database error instead of a refusal. The v20 and v25 checks guard this
case explicitly ("An absent table passes", `local_db.py:1049`, `1081`).

**Why it matters.** Every test run and every new install would fail at schema creation. The coder
would find it at once, but the rule is the brief's to state, and § 8.3 has no test for it.

**Options.**
- (a) **Recommended:** the check first reads `information_schema.TABLES` with
  `TABLE_SCHEMA = DATABASE()` (as `_old_tables_for_v20` does) and passes when
  `property_definitions` is absent. Add to § 8.3: "an empty database passes the check", and a
  case in `test_migration_v34.py` that migrates from empty.
- (b) Drop the precondition and let `INSERT IGNORE` skip a hand-made row quietly. Rejected by
  D8 for a good reason: nothing would say so.

### BR1-02 — major — The existing tests that break are under-listed

**Problem.** The seed "GPS location" is active and `all_classes = 1`, so after v34 it is on the
card, in the item dialog and in every class's property table, on every top-level node, in the
backend test database and in every e2e lane database. § 8.2 and § 8.4 name one e2e test
(`equipment.spec.js:398`) and "tests that assert an exact card list … will change". I checked
the tests; these break too:

| File | Line | What breaks |
|---|---|---|
| `backend/tests/test_equipment_api.py` | 1552 | `detail["properties"] == [...]` on a top-level node: the GPS row is added (sorted last, "g" after "e") and every row gains `data_type`, `per_item_only`, `map_url` |
| `backend/tests/test_equipment_api.py` | 1562 | `properties == []` on a top-level node with no links: now one row |
| `backend/tests/test_item_properties_api.py` | 116, 119 | the ids list of the dialog gains the GPS row; the full-dict compare of `power` gains `per_item_only` |
| `backend/tests/test_item_properties_api.py` | 139 | `len(items) == 4` → 5 (`motor` is a top-level node: `conftest.node` → `make_equipment`) |
| `backend/tests/test_properties_api.py` | 252 | the class list `== []` → the GPS row is listed on every class |
| `frontend/e2e/equipment.spec.js` | 372–373, 387, 395, 449, 461, 473, 481, 520 | `dt` / `dd` `toHaveText([...])` exact lists on top-level machines |
| `frontend/e2e/masters.spec.js` | 360, 374, 388–389 | "No properties on this class yet." never shows on a class now; `rows` count 2 → 3; the card's `dt` list |

`test_a_model_less_component_unit` (line 134) reads a component-unit, so it keeps 4 and stays
green. `journeys.spec.js` and `screens.spec.js` assert nothing on the card (checked).

**Why it matters.** The coder must choose one convention for a dozen tests; the brief should
choose it, so the tests stay readable and the next step that adds a seed does not repeat this.

**Options.**
- (a) **Recommended:** the brief lists the files above and fixes the convention: backend tests
  compare the card and the dialog **without the seed rows** through one helper per test module
  (`_made(rows)`: the rows whose `property_id` is in the ids the test made), and e2e tests
  assert `dt` lists that include "GPS location" as the last row (the by-name order puts "E2E …"
  before "GPS …"). `masters.spec.js:360` asserts the GPS row marked *Every class* instead of the
  empty state; `374` expects 3.
- (b) Make every test build its own class *and* expect the seed row inline. More edits, and the
  next every-class seed breaks them again.

### BR1-03 — minor — D1 says the database checks the range; § 4 has no range CHECK

**Problem.** D1: "They check range and pairing in the database." § 4 adds only the pair CHECK.
`DECIMAL(8,6)` holds up to 99.999999 and `DECIMAL(9,6)` up to 999.999999, so a latitude of 95
fits the column. Only `parse_value` refuses it.

**Why it matters.** The reason given for D1 over text is a database rule that the migration does
not make; a later writer (a PM feed, an import) would store 95.

**Options.**
- (a) **Recommended:** add the range to the pair constraint or a third one, e.g.
  `chk_<table>_geo_range CHECK (value_lat IS NULL OR (value_lat BETWEEN -90 AND 90 AND value_lng
  BETWEEN -180 AND 180))`, in the same re-runnable `ALTER`; § 8.3 then checks a 91 refused (4025).
- (b) Keep § 4 and change D1 to "pairing in the database, range in `parse_value`".

### BR1-04 — minor — The rollback paragraph does not match the old code

**Problem.** § 4 Rollback: "Its value columns are not read, so the card shows '—' for it." In the
previous release `linked_properties` lists only class-linked properties, so "GPS location" never
reaches a card (the flag is ignored). If an engineer links it in the old Masters (the old picker
lists it: active, type "geo"), `stored_value` and `value_display` do `VALUE_COLUMNS["geo"]` →
`KeyError` → 500 on every equipment page of that class and on the model dialog.

**Why it matters.** The user reads this paragraph to judge the release's risk.

**Fix.** State the real behaviour: the row is invisible on cards in the old release; linking it
there breaks that class's pages until the link is removed; the data is unharmed. Recommended:
keep the text as a known risk (a rollback is rare, the fix is one *Remove*).

### BR1-05 — minor — The shape of a geo value in the core is left to the coder, and `_same_value` is not named

**Problem.** § 3 says "the columns of a value" change, but `VALUE_COLUMNS` maps one type to one
column, and five functions read it: `check_values` (builds the columns), `stored_value`,
`value_display`, `_same_value` and `write_values`. `_same_value` is named nowhere in the brief.
Without a Decimal compare of both new columns there, every re-save of the item dialog (it sends
every row, unchanged ones too) writes a row and a history line for an unchanged location, which
S044's `item_changes` exists to prevent.

**Why it matters.** The history would fill with "GPS location: 11.016823, 76.955812 → 11.016823,
76.955812" lines after every unrelated save on the dialog.

**Options.**
- (a) **Recommended:** state in § 5.2: `parse_value` for `geo` returns `(lat, lng)` as Decimals;
  the columns of a value are `GEO_COLUMNS = ("value_lat", "value_lng")` beside `VALUE_COLUMNS`;
  `_same_value` compares both as Decimal (as it does `value_number`). Add to § 8.2: "a re-save
  with the same location writes no row and no event" (the pattern of
  `test_a_clear_of_a_row_with_no_own_value_writes_nothing`).
- (b) Leave it to the coder. The code reviewer would catch it, one round later.

### BR1-06 — minor — The model line and *Edit model values* on a card that holds only per-machine rows

**Problem.** After v34 every top-level machine of a class with no links shows a Properties card
with one row, "GPS location —", and under it "Values from model <label>." (the line shows whenever
`model_id` is set, `EquipmentDetailView.vue:319`). *Edit model values* is shown too and opens a
dialog that says "The class X has no properties yet. Add them in Equip Class."
(`ModelPropertiesModal.vue:62`) — the class has one, but it is per-machine.

**Why it matters.** The two texts are wrong on the floor for every machine of every class that has
no links today, which is most of the plant on release day.

**Options.**
- (a) **Recommended:** show the model line and *Edit model values* only when the card has a row
  that is not `per_item_only`. One computed in `EquipmentDetailView.vue`; the brief's § 3 names
  the file already. Add an e2e assertion to the per-machine test of § 8.4.
- (b) Keep the line and reword the empty dialog: "Every property of this class is set on each
  machine." Less work, the line "Values from model" still misleads.

### BR1-07 — minor — Two UI texts (scope B)

**Problem.**
1. D3: "Location is blocked for this site. …" — in Yantra a *site* is a plant site (Sites master,
   `SITE_SCOPED`). The sentence reads as "blocked at SSVT".
2. § 5.1: the 409 for turning `per_item_only` on names no `field`, so the dialog shows it as a
   top error, not beside the tick box the user ticked.

**Fix.**
1. "Location is blocked for Yantra in this browser. Allow it in the browser's settings, or type
   the location."
2. The refusal carries `field: "per_item_only"`; the dialog shows it under that tick box.

### BR1-08 — minor — A property both linked and every-class: one row or two, and may it be linked?

**Problem.** § 1 item 8 and § 6 say the class list "also lists every-class properties". The API
still accepts a link of an every-class property (`add_class_properties`; only the picker hides
it), and a link made before the flag was turned on stays (§ 5.1). The brief does not say whether
`list_class_properties` returns such a property once or twice, and which mark it carries.

**Why it matters.** Two rows for one property, or a *Remove* on a row that would not remove it
from the class, is the kind of oddity a reviewer of the class table reports.

**Options.**
- (a) **Recommended:** one row per property (the UNION is distinct); an every-class row is marked
  *Every class* and has no *Remove*, linked or not; the API keeps accepting the link (harmless, it
  takes effect when the flag is turned off). State it in § 5.3 and test it in § 8.2.
- (b) Refuse the link of an every-class property in `add_class_properties`. One more rule for no
  need.

### BR1-09 — minor — The device checks name no account and no network

**Problem.** § 8.5 says "Done by IT Admin, after the deploy, on production" and lists three
checks. The rows need the account (which login, holding `equipment:edit` at the genset's site —
the `it_admin` token role alone grants nothing in Yantra, § RBAC deviation), the network (mobile
data outdoors; the phone's location service on; the plant Wi-Fi is not needed for the position
but is for the save), and where (production on the phone). The iPhone check should say that a
standalone PWA on iOS asks for the location on each use, so "the prompt shows" is expected every
time, not a fault.

**Fix.** Give each row account, network and where (settings: *Device checks*), and the note on
iOS.

### BR1-10 — minor — The standards' clause numbers are "to verify", by nobody

**Problem.** § 2 marks the ISO 14224 table and clause and the IEC 60050-826 term numbers "to
verify". The coder cannot verify a standard; the text goes into `docs/Plan.MD` at gate A as it
stands.

What I can say:
- Fact: ISO/IEC 27001:2022 Annex A control **5.34** is "Privacy and protection of PII". Correct
  as cited.
- Assumption: ISO 14224:2016 § 8 (equipment data) and Table 4 give the data categories; the split
  the brief describes is *equipment attributes (design data)* against *operation and installation
  data*. The brief should cite § 8 / Table 4 only if the orchestrator confirms it, else cite
  "ISO 14224 § 8, equipment data categories" without a table number.
- Assumption: IEC 60050-826 section 826-16 (equipment) defines fixed, stationary, portable,
  hand-held and mobile equipment; the term numbers are 826-16-0x but I cannot confirm which digit
  is which. Cite "IEV 826-16" without the last digits.
- Idea (nit-level): ISO 55001 § 7.5 asks for the information an asset register holds; a location
  is a standard attribute of an asset. One line would tie the GPS property to the asset
  management standard the project names.

**Fix.** The orchestrator verifies or removes the numbers before gate A; nothing "to verify" is
left for the coder.

## Nits

- **BR1-11** (nit) § 1 item 1 vs § 5.2: "6 decimals each" and "11.016823, 76.955812" in § 1, but
  the display drops trailing zeros ("11.0168, 76.9558"). Say in § 1 that the display trims zeros,
  so the tester does not report it.
- **BR1-12** (nit) § 8.4, the hidden-card test: recommend the component option, not deactivating
  the seed. `playwright.config.js` runs one worker per lane, but a test that fails after
  deactivating leaves the lane's seed inactive for every later test in that lane.
- **BR1-13** (nit) § 3 Tests and § 8.4 name `e2e/equipment.spec.js` without `frontend/`; the
  facts file reports them as "no such file". Write `frontend/e2e/…` once in § 3.
- **BR1-14** (nit) D3: name the check, `window.isSecureContext && navigator.geolocation`; and in
  § 8.4 say the test calls `page.context().grantPermissions(["geolocation"])` and
  `page.context().setGeolocation(...)` before `asPerson` opens the page.
- **BR1-15** (nit) § 5.3: the model dialog of a model whose machines are all component-units (a
  motor model inside a press) offers a non-per-machine Location property that none of its machines
  shows. The brief says "almost always"; say it is a known gap, accepted.
- **BR1-16** (nit) § 4 item 1: say the ENUM widening is `ALTER TABLE property_definitions MODIFY
  data_type ENUM(...)` in the same statement as the two `ADD COLUMN IF NOT EXISTS`, so the coder
  does not split it.

## Checked and found consistent

- All six routes of § 6 exist; keys unchanged (`masters:read`, `equipment:read`,
  `equipment:edit`); no new `SITE_SCOPED` key, so `test_role_matrix` needs no change.
- § 5.7 locks: the flags are read at step (2) (`lock_value_properties`, `_lock_property`, both
  `FOR UPDATE`); `update_property` already share-reads both value tables (`properties.py:153-155`);
  splitting the model-rows read out is a one-line change. No new lock, no new order; the
  `item_properties.py` note's "no cycle" reasoning still holds.
- `_parse_active` accepts true / false / 0 / 1 and refuses "yes" (`properties_core.py:108`).
- `equipment.py:312` is the only caller of `equipment_properties`; `node["level"]` is on the row.
- `_SEEDED_TABLES` keeps `created_by = 'migration-v31'` only (`conftest.py:173-175`);
  `SEED_CREATOR` is used by `test_migration_v11.py` only. A tuple of creators and `NOT IN` is the
  right change.
- `test_migration_v33.py` is a sound pattern for v34: fresh database, the frozen-fixture upgrade,
  a re-run, the 4025 checks.
- The CHECK names `chk_model_property_one_value` / `chk_equipment_property_one_value` match
  `local_db.py:916`, `1026`.
- The Google Maps URL form `https://www.google.com/maps/search/?api=1&query=<lat>,<lng>` is the
  documented key-less form; built from stored numbers only.
- `typeLabel` shows an unknown type as sent, so the rollback's "raw type `geo`" claim is right.
- `AddPropertiesModal.available` already filters by `active` and `linkedIds`; one more filter on
  `all_classes` is the whole change.
- `ItemPropertiesModal.modelHint` and `EquipmentDetailView.markedOwn` are the two places the
  per-machine rule touches; `anyMarkedOwn` follows `markedOwn`, so the "except those marked"
  line stays right.
- Secure context: `localhost` and `127.0.0.1` count as secure, so the e2e stack (Vite on
  127.0.0.1) can run the geolocation test; a phone on the dev server over LAN (`http://192.168…`)
  hides the button, which is why the device checks are on production (HTTPS).
- Standards: ISO 27001 A.5.34 cited correctly; the privacy statement (one reading, on a tap, stored
  as the machine's datum, the actor in the history) is accurate for the design.
- UX: one job per dialog; the location field needs one tap plus Save; paste for entry after the
  fact; no new destructive action; errors one line each; the no-permission case hides the button
  (`canEdit`), as today.
- Scope A: the brief's text is clear and consistent in its terms (property, flag, value, card,
  dialog).

## Feedback

- idea: `brief_facts.py` reported `e2e/equipment.spec.js` as "no such file" though
  `frontend/e2e/equipment.spec.js` exists; resolving a bare path under each code folder would save
  the reader a check (3 lines of the facts file).
- waste: the facts file lists test-file users for routes but not which tests assert exact lists,
  so BR1-02 needed four greps and three file reads (~10 minutes); a per-route "asserts on the
  response shape" hint is out of scope, so this is a note only.
