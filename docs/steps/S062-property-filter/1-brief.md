```
Step: S062 — Filter the equipment list by property
Doc: brief
Author: Orchestrator (Opus)
Date: 27-10-2026
Track: full
Status: Done (committed 24556c4, adopted 27-10-2026; checks: 8 auto; D-1 decided by KLA 27-10-2026: keep `router.push`) (approved 27-10-2026 by KLA: D11 widen the level; Q1 a; A1–A4 as written)
Baseline: d6431f1 (brief reviews); staleness check s1 done against refs/steps/S061 fb6a025 (no blocker or major)
```

# S062 — Filter the equipment list by property

**The need (KLA, 27-10-2026).** The equipment list filters by site, unit, class, type,
lifecycle, criticality and tickets, and searches code, name, model and notes. It cannot answer
"which motors are above 15 kW?", "which machines are Portable?" or "which machines have no GPS
location yet?". Those answers sit in the properties (S043 on the model, S044 on the item, S061
every-class and per-machine). KLA asked for a dialog that builds such a filter: lines of
*property, operator, value*, as many as needed, joined by AND or OR. The printable asset list
(S015) uses the same filter.

**Decided before this brief (KLA, 27-10-2026):**
- one *All / Any* switch for every line; no nested groups;
- the property list shows every active property, narrowed to the class's properties when the
  list has a class filter;
- the printed asset list takes the property filter too.

**Built on S061.** S061 (approved, not coded) changes which properties a node shows: the
every-class flag, the per-machine flag and the Location type. This step is coded **after
S061**, and its rules follow S061 § 5.3 (which properties a node shows) and § 5.4. The brief
says "after S061" where a rule depends on it. Track: full — a new pure core that builds SQL from
user input, two list routes changed, about 19 files (with the shared test fixtures, BR1-06).

## 1. What will be built

1. **A button *Filter by property*** on the equipment list, in the filter row, before the
   print buttons. With a property filter set, it reads *Properties (2)* (the number of
   conditions) and is filled (`btn-primary`) instead of outlined.
2. **The dialog *Filter by property*** (`PropertyFilterModal.vue`, in a `FormModal`):
   - one line per condition: **Property** (select), **Operator** (select), **Value** (an input
     by the property's data type, § 5.3), and a bin button *Remove condition*;
   - *Add condition* under the lines; at most 10 lines. At 10 lines the button is hidden and
     the text "10 conditions at most" shows in its place (BR1-07: a tooltip cannot be read on a
     phone);
   - **Match** (shown from two lines), **above the lines**, so the reader meets it before the
     conditions (BR1-08): two radio buttons, *All conditions* (AND, the default) and *Any
     condition* (OR);
   - the footer: *Cancel* and *Apply filter*. *Apply filter* with no line left clears the
     property filter;
   - a new dialog opens with one empty line; an open with a filter set shows its lines.
3. **The filter line** under the filter row, whenever the URL has `props` (BR1-03), with a
   button *Clear property filter* (an ✕ with that label). The text says the match once and
   separates the conditions with " · ", the asset list's own separator (BR1-04):
   - one condition: "Properties: Rated power more than 7.5 kW";
   - two or more under *All conditions*: "Properties (all of): Rated power more than 7.5 kW ·
     Mobility is Portable or Mobile"; under *Any condition*: "Properties (any of): …";
   - a `props` that cannot be read (a hand-edited or cut bookmark): "Properties: cannot be
     read". *Clear property filter* removes the key, as for any filter. The screen then sends
     no list request (it would only be refused) and shows, in place of the table, one message:
     "The property filter cannot be read. Clear it and make it again." So the refusal shows
     once, not in the error box with *Retry* as well (BR2-03).
   A tap on the text opens the dialog; with an unreadable `props`, it opens with one empty line.
4. **The list** shows only the nodes that match. The property filter joins the other filters
   and the search with AND.
4a. **The level widens on the first property filter** (BR1-01). A motor or gearbox is a
   component (Plan.MD § 4.1), and the list opens at level *Equipment*. So when *Apply filter*
   sets a property filter where there was none, and the URL has no `level`, the same URL
   change sets `level=all`: the motors show. The user can narrow the level again. This is the
   search's rule (`applySearch`, `EquipmentView.vue:142`: the first search widens the level).
   A change to an existing property filter, or any `level` in the URL, leaves the level as it
   is. The rule reads the URL, as the search's does: *Equipment* chosen by hand leaves no
   `level` in the URL (`update()` drops the default, `EquipmentView.vue:68`), so it counts as
   the default (BR2-02).
5. **The URL** holds the filter in one query key `props` (§ 5.1), so Back, a reload and a
   bookmark keep it, as for the other filters. A filter change goes back to page 1 and clears
   the label ticks (the existing `filterKey` rule, `EquipmentView.vue`).
6. **The printed asset list** (*Print asset list*) carries `props` to the print page. The API
   `GET /api/equipment/asset-list` applies it to the machines. Parts come with their machine,
   whatever their own values (S015 § 4, unchanged). The section header names it:
   "Class: RPP · Properties: Rated power more than 7.5 kW".

### Out of scope

- Nested groups, such as (A and B) or C (KLA, 27-10-2026).
- Saved or named filters.
- A search by distance from a Location value (S061 out of scope); Location takes only *has a
  value* and *has no value*.
- Property columns in the list table or on the printed sheet.
- Sorting by a property's value.
- A count of matches inside the dialog before *Apply filter*.
- Filters by a property on the readings, tickets or labels screens.

## 2. Standards and practice

- **ISO 14224 (collection of reliability and maintenance data for equipment), Annex A
  (equipment-specific data).** It lists, per equipment class, the technical data to record,
  for example a motor's rated power and speed. In plain words: record the data in fields, the
  same field for every unit of a class, so units can be compared and picked out. This step is
  the "picked out" part: a filter on those fields. (S043 cited the annex; no table number here,
  not verified.)
- **ISO 55001 § 7.5 (information requirements; to verify).** An organisation decides what
  information about its assets it needs, and makes it available to the people who need it. A
  register that answers "which units have X" makes the information usable, not only stored.
- **Data quality, ISO 14224 (data quality).** *Has no value* lists the machines whose data is
  missing, so the register can be completed. (The clause number is not cited: not verified.)
- **TPM, focused improvement and spare parts.** Finding every machine with the same motor
  size or the same gearbox ratio shows which spares fit more than one machine.
- **ISO 27001 A.8.28 (secure coding).** In plain words: write code so that input cannot change
  what the program does. The filter is user input that becomes SQL. Every value goes in as a
  parameter. Every column name and operator comes from a fixed table in the code, never from the
  request (§ 5.4).

## 3. Where

### Backend

- `backend/property_filter_core.py` (new, pure): read and check the `props` value in two
  functions, `read_property_filter` and `check_property_filter` (§ 5.2, BR1-02); build the SQL
  condition and its parameters (§ 5.4). No Flask, no database.
- `backend/equipment.py`:
  - `_list_filters` takes the cursor (`_list_filters(cur)`): it reads `props` with
    `read_property_filter`, loads the properties named by `parsed["property_ids"]` and their
    options, calls `check_property_filter`, then `filter_condition`, and appends the condition;
  - `list_equipment` and `asset_list` call it inside their `with get_db().cursor()` block,
    before the unit-access check, so a bad filter is refused first (§ 5.5).
- `backend/properties.py`: one read helper, `filter_properties(cur, property_ids)`: the rows
  of `property_definitions` (id, name, data_type, unit, active, and `all_classes` after S061)
  for the ids named, with their options by `options_by_property`.

### Frontend

- `frontend/src/utils/propertyFilter.js` (new, pure): the operators by data type, encode and
  decode `props`, a line's completeness, the words of the filter line (`describeFilter`), and
  the level rule of § 1 item 4a.
- `frontend/src/views/equipment/PropertyFilterModal.vue` (new): the dialog (§ 5.3).
- `frontend/src/views/EquipmentView.vue`: the button, the filter line (also for an unreadable
  `props`), `props` in `listUrl`, the level rule on apply, and the dialog.
- `frontend/src/utils/assetList.js`: `props` in `FILTER_KEYS`; `filtersLabel` names the
  property filter, given the properties in `lookups`.
- `frontend/src/views/AssetListPrintView.vue`: loads the properties (`ensureProperties`) for the
  header line, only when the query has `props`; a plain print makes no extra request (BR1-12).

### Tests

- `backend/tests/test_property_filter_core.py` (new).
- `backend/tests/test_property_filter_api.py` (new): the list and the asset list with `props`.
- `backend/tests/conftest.py` (shared test fixtures, BR1-06): the fixtures `make_property` and
  `link` move here from `backend/tests/test_item_properties_api.py` (`make_property` lines
  65-74, `link` 77-81, `_numbers` line 18; BS1-03), beside the other
  `make_*` fixtures; that module then uses the shared ones and drops its `_numbers` counter.
  The names come from a new method `Uniq.property_name(prefix)` on the existing `Uniq` class
  (`conftest.py:284`), so the moved fixture is `make_property(admin, uniq)` and no second
  counter is added (BR2-01). It keeps S061's body: `**overrides`, and `unit` dropped for a
  type that is not a number (BS1-04).
  The `every_class` fixture moves to `conftest.py` too (now in both
  `test_item_properties_api.py:355` and `test_properties_api.py:424`): a test that makes an
  every-class property turns the flag off afterwards, or the property leaks onto every later
  test's machine in the shared database (S061 impl report D-10; BS1-02). The two modules then
  use the shared one.
  `backend/tests/test_properties_api.py` keeps its own `make_property` and `link` (another
  signature, by `engineer`): pytest's module fixture overrides the conftest one of the same
  name, so that module is unchanged.
- `backend/tests/test_equipment_api.py`, `backend/tests/test_asset_list_api.py`: unchanged;
  they must stay green after the `_list_filters(cur)` change.
- `frontend/tests/propertyFilter.test.js` (new), `frontend/tests/assetList.test.js` (new cases).
- `frontend/e2e/equipment.spec.js`, `frontend/e2e/asset-list.spec.js` (new tests, § 8.4).

### Docs (housekeeping, by the coder)

- `docs/Plan.MD` § 4.1 *Equipment register*: the property filter on the list and the asset
  list.
- `.claude/CLAUDE.md` § SMTW-Review: the spec-to-step map gains S062 under `equipment` and
  `asset-list`.
- No migration, so no schema doc change.

## 4. Data model

No migration. The filter reads:

- `property_definitions` (S043 v31; `all_classes` from S061 v34);
- `property_options`;
- `class_properties` (primary key `(class_id, property_id)`);
- `model_property_values` (primary key `(model_id, property_id)`);
- `equipment_property_values` (primary key `(equipment_id, property_id)`, S044 v33).

Every lookup the filter makes is by a full primary key, so no index is added.

## 5. Rules

### 5.1 The `props` value

One JSON object, URL-encoded, the same in the screen's URL and in the API's query:

```json
{"match": "all", "rules": [
  {"property_id": 12, "op": "gt", "value": "7.5"},
  {"property_id": 15, "op": "in", "value": [31, 33]}
]}
```

- `match`: `"all"` (AND) or `"any"` (OR). Missing: `"all"`.
- `rules`: a list of 0 to 10 rules (`MAX_RULES = 10`). An empty list is no property filter.
- Each rule: `property_id` (a positive whole number), `op`, and `value` as the operator needs
  (§ 5.2). The frontend writes the keys in this order and no others.
- The raw text is at most 4000 characters (`MAX_PROPS_LENGTH`), so a URL stays a URL.

### 5.2 Operators, values and checks (pure, `property_filter_core`)

Two pure functions, so the shell can load the properties between them (BR1-02):

1. `read_property_filter(raw)` → `(parsed, None)` or `(None, (field, message))`: checks 1–3
   below. `parsed` holds `match`, the raw rules, and `property_ids`, the sorted set of the ids
   the rules name.
2. `check_property_filter(parsed, properties, options)` → `(filter, None)` or `(None, (field,
   message))`: checks 4–6. `properties` is `{id: {id, name, data_type, unit, active,
   all_classes}}` for the ids found; `options` is `{property_id: [{id, label, active}]}`.

The shell calls the first, loads the properties by `property_ids`, then calls the second. A
missing or empty `props` gives no filter and no load. The first refusal answers.

| Data type | Operators (`op`) | `value` |
|---|---|---|
| number | `eq` equals, `ne` not equal to, `lt` less than, `le` at most, `gt` more than, `ge` at least | a number as text, parsed by `properties_core.parse_value(NUMBER, …)` |
| number | `between` | a list of two numbers as text, low then high, both ends included |
| choice | `in` is, `not_in` is not | a list of 1 or more distinct option ids of this property (inactive options allowed: values may hold them) |
| text | `contains`, `eq` is | text, 1 to 100 characters after trimming |
| yes_no | `eq` is | `true` or `false` |
| geo (after S061) | — | — |
| every type | `has` has a value, `none` has no value | none; a value sent is ignored |

The checks, in order, with the field and the message (scope B):

1. Not JSON, not an object, `rules` not a list, `match` not `all`/`any`, or longer than
   `MAX_PROPS_LENGTH`: field `props`, "The property filter cannot be read. Clear it and make it
   again."
2. More than 10 rules: field `props`, "Use 10 conditions or fewer".
3. A rule that is not an object, or a `property_id` that is not a positive whole number:
   field `props.rules.<i>`, the message of check 1. A boolean is not a whole number here
   (`True` is an `int` in Python; the guard of `properties_core.parse_property_ids`), and the
   same holds for option ids in check 6 (BR1-10).
4. A property not found, or inactive: field `props.rules.<i>.property_id`, "This property is no
   longer in use. Remove its condition."
5. An `op` not in the table for the property's data type: field `props.rules.<i>.op`, "Choose
   an operator from the list".
6. The value, field `props.rules.<i>.value`:
   - a number: the messages of `parse_value` ("Enter a number", "Use up to 4 decimals",
     "Enter a smaller number"); a blank number: "Enter a number";
   - `between`: not a list of two: "Enter two numbers"; low above high: "Enter the smaller
     number first";
   - a choice: no option, or not a list: "Choose at least one option"; an id not of this
     property, a boolean, or the same id twice: "Choose an option from the list"
     (`CHOOSE_OPTION`; the frontend never sends a duplicate, so a duplicate is a hand-made
     request and is refused, not dropped, BR1-10);
   - text: blank: "Enter text" (`ENTER_TEXT`); too long: "Use 100 characters or fewer"
     (`TEXT_TOO_LONG`);
   - yes/no: not a boolean: "Choose Yes or No" (`CHOOSE_YES_NO`).
   The messages are `properties_core`'s constants where one exists, so one rule has one wording.

### 5.3 The dialog

- **Composable.** The dialog uses `FormModal` directly, not `useFormModal`: it saves nothing to
  the server. `PropertyFilterModal.open(filter)` takes the decoded filter (or null) and copies
  it into the dialog's lines; `apply` emits the new filter (or null when no line is left).
  `dirty` compares the lines with the copy made at open, so the usual "Discard your changes?"
  guard applies (S007).
- **Property select.** The active properties by name, from `ensureProperties`
  (`GET /api/masters/properties?include_inactive=1`, each with its options). With a class
  filter on the list, only the active ids that class shows (the class route lists inactive
  rows too since S061, so the dialog intersects it with the active list; BS1-05)
  (`GET /api/masters/equipment-classes/<id>/properties`, which after S061 includes the
  every-class ones; it carries no options, so the details come from the first list). A line whose property is not in that
  list (a bookmark, a class changed afterwards) still shows its property, listed last, so the
  applied filter is visible (the rule of the type filter's foreign type, `EquipmentView.vue`).
  A number property's option reads "Rated power (kW)".
- **Operator select.** The operators of § 5.2 for the property's data type, in that order,
  in words. Choosing another property resets the operator to the first one of its type and
  clears the value.
- **Value input.** The dialog has its own inputs, not `PropertyInput.vue` (BR1-05): a line has
  no label, `between` needs two inputs, and a choice is a pick of several options, where
  `PropertyInput` takes one. The inputs keep `PropertyInput`'s attributes, so the two look the
  same: `inputmode="decimal"`, the unit as an `input-group-text`, `maxlength="100"`.
  - number: a text input with `inputmode="decimal"` and the unit beside it;
  - `between`: two such inputs, "and" between them;
  - choice: a list of tick boxes, one per option, the active ones first, an inactive one
    marked "(inactive)";
  - text: a text input, `maxlength="100"`;
  - yes/no: a select *Yes* / *No*;
  - `has`, `none`, and Location: no input.
- **Completeness (presentational).** *Apply filter* is disabled while a line has no property
  or misses its value. The reason shows as the button's tooltip and, on a phone, as a line
  above the footer: "Complete or remove the empty condition". The value checks themselves are
  the backend's.
- **Apply.** *Apply filter* sends one check request: `GET /api/equipment?props=<filter>&level=
  all&per_page=1`. While it runs, the dialog passes `saving` to `FormModal`, so the button shows
  its spinner and a second tap does nothing (BR1-09). A 400 with a field `props.rules.<i>.…`
  shows its message under line *i* (beside the operator or the value); a 400 with field `props`
  shows at the top of the dialog (`FormModal`'s `error`). The dialog stays open. On 200 the
  dialog closes, and the list writes `props` to the URL, with `level=all` on the first property
  filter at the default level (§ 1 item 4a). Any other failure (503, network) shows its message
  at the top and the dialog stays open.
- **Phone layout.** Each line is a bordered block: the property select on its own row, the
  operator and the value on the next, the bin at the block's top right. The dialog scrolls
  inside itself (the `FormModal` pattern), and its buttons stay in the footer.
- **Remove condition** needs no confirmation: a line is cheap to make again, and *Cancel*
  brings the old filter back.

### 5.4 The SQL (pure, `property_filter_core.filter_condition`)

`filter_condition(filter, like)` → `(sql, params)`, one condition for the whole property
filter, or `(None, [])` for an empty one. `like` is `api_common.like_pattern`, passed in by the
shell, so the core imports no Flask (it escapes `%`, `_` and `\`).

For each rule, with `P` the property id and `col` the value column of its data type
(`properties_core.VALUE_COLUMNS` for number, text, yes/no and choice; for Location,
`properties_core.GEO_COLUMNS[0]`, `value_lat`: `VALUE_COLUMNS` has no `geo` key as S061 built it,
so the core builds its own column table from both, BS1-01):

- **applies** — the node shows the property (S061 § 5.3):
  - the property has `all_classes`: no class condition; otherwise
    `EXISTS (SELECT 1 FROM class_properties cp WHERE cp.class_id = e.class_id AND
    cp.property_id = %s)`;
  - a Location property: also `e.level = %s` with `properties_core.GEO_LEVEL` (BS1-06).
  - This rule then lives in two places: S061's `properties.linked_properties` and this SQL.
    As built, S061's rule lives in `properties.linked_properties`, `properties_core.on_level`
    and `properties.lock_value_properties`. Each of them and this SQL carries a comment naming
    the others, so a change to one is made in all (BR1-11, BS1-06).
- **value** — the value in force, the item's own first (S044 § 5.5):
  `COALESCE((SELECT iv.col FROM equipment_property_values iv WHERE iv.equipment_id = e.id AND
  iv.property_id = %s), (SELECT mv.col FROM model_property_values mv WHERE mv.model_id =
  e.model_id AND mv.property_id = %s))`.
  - Each value row holds one value in the column of its property's data type (the CHECK
    `chk_*_one_value`, and the data type is fixed once a value exists, S043 § 5.1). So the
    own row's column is filled whenever the own row exists, and COALESCE gives "own row wins".
  - A node without a model (S033): the model subquery is NULL; only its own value counts.
- **the rule** = applies AND:

| `op` | SQL |
|---|---|
| `eq`, `ne`, `lt`, `le`, `gt`, `ge` | value `=`, `<>`, `<`, `<=`, `>`, `>=` `%s` |
| `between` | value `BETWEEN %s AND %s` |
| `in`, `not_in` | value `IN (%s, …)`, `NOT IN (%s, …)` |
| `contains` | value `LIKE %s` (the `like` pattern) |
| `has`, `none` | value `IS NOT NULL`, `IS NULL` |

- **The whole filter** = `(rule1 AND rule2 …)` for `all`, `(rule1 OR rule2 …)` for `any`,
  appended to the list's conditions, which are joined with AND.
- The operator SQL and the column names come only from the two fixed tables above. The
  request gives only the parameters.
- Numbers are passed as `Decimal`; yes/no as 1 or 0; option ids as ints.
- Text compares by the column's collation, without regard to case, as the property names do
  (`uq_property_definitions_name`, S043).

**What matches, in plain words:**

- **A node matches a rule only when its class shows the property.** A machine whose class
  lacks "Rated power" matches neither "Rated power more than 5" nor "Rated power has no value".
  *Has no value* thus lists the gaps to fill, not every machine of other classes.
- **"not equal to" and "is not" need a value.** A machine with no Mobility value is not
  "Mobility is not Fixed". To include it, add the line "Mobility has no value" and choose *Any
  condition*. The dialog says so under an `ne` or `not_in` line: "Machines with no value are
  not included."
- **A hidden own value does not count** (S044: a value of a property the class no longer has is
  hidden), because *applies* fails.
- **An inactive property** is refused (§ 5.2 check 4): its values show nowhere (S043), so a
  filter by it would match what the user cannot see.

### 5.5 The routes

- `GET /api/equipment` and `GET /api/equipment/asset-list` take `props`. No other change to
  their answers.
- **Order** in each route: `_list_filters(cur)` (the property rows are read, the filter is
  checked, 400 on a refusal), then the unit-access check, as today. A user with no units still
  gets the 400 for a bad filter, so the dialog's check request answers the same for everyone.
- **The asset list** applies the condition to the machines (`e.level = 'equipment'`, already
  in the route). Its 400 shows in the print page's error line, as for a bad filter today
  (`AssetListPrintView.vue`).
- **Reads only.** No transaction and no lock. The property rows and the list are plain reads
  in the same request; a property changed between them (a flag, an option) changes at most
  which rows match in that one answer.

### 5.6 Permissions

- No new key. Both routes keep `equipment:read`, and the list's unit scoping
  (`accessible_unit_ids`, `SITE_SCOPED`) is unchanged: the filter only narrows rows the user
  may already see.
- The dialog's property list reads `GET /api/masters/properties` and the class's properties,
  both `masters:read` (`*`, everyone).
- The values a user can filter by are the ones the equipment page already shows them, at the
  same units. A filter reveals nothing new.

### 5.7 The database down

As today: `get_db()` raises `DBUnavailable` → 503. The dialog's check request then shows the
503 message at the top of the dialog; the list shows its error box.

## 6. API

| Route | Key | Change |
|---|---|---|
| `GET /api/equipment` | `equipment:read` | Takes `props` (§ 5.1); 400 with the fields of § 5.2 |
| `GET /api/equipment/asset-list` | `equipment:read` | The same |

## 7. Design decisions

- **D1. One *All / Any* switch, no groups** (KLA). Nested groups are hard to build and read on a
  phone. One switch covers "all of these" and "any of these". Rejected: groups.
- **D2. The value in force: own first, then the model's** — the value the Properties card shows
  (S044 § 5.5). Rejected: the model's value only, which would miss a rewound motor.
- **D3. A node matches only where its class shows the property** (§ 5.4). This keeps *has no
  value* useful for data gaps. Rejected: treat every node as "no value" for a property it does
  not have, which would list every pump under "Rated power has no value".
- **D4. "not equal to" and "is not" exclude nodes with no value** (the SQL rule for NULL). The
  dialog says so, and *has no value* with *Any* adds them. Rejected: include them silently,
  which reads as "is not Fixed" listing machines nobody has classified.
- **D5. One JSON key `props`** in the URL and the API. One key keeps the list's `update()` and
  `filterKey` rules as they are, and the API reads it in one place. Rejected: one key per line
  (`p1_id`, `p1_op`, …), which needs its own parse and limits in both places.
- **D6. The filter is checked by the server before the dialog closes** (§ 5.3, one `GET` with
  `per_page=1`). The refusal shows under its line. Rejected: apply at once and show the refusal
  in the list's error box, which cannot point at a line; and a separate check route, which adds
  an endpoint for what the list route already does.
- **D7. The SQL is built in a pure core from fixed tables.** The core is tested without a
  database for every operator and type, and no request text reaches the SQL but as a
  parameter (ISO 27001 A.8.28). Rejected: build it in `equipment.py`, which mixes the rule
  with the shell.
- **D8. Correlated subqueries, not joins.** `_list_filters` returns conditions only, and the
  list and the asset list share it; a subquery keeps that shape. Every subquery is a primary-key
  lookup. Rejected: a `LEFT JOIN` per rule, which changes `_NODE_FROM` for both routes.
- **D9. The asset list filters machines only** (S015 § 4): parts come with their machine.
  Rejected: filter parts by their own values on the sheet, which would split a machine from its
  parts on a verification walk.
- **D10. An inactive property is refused, not ignored.** Ignoring it would widen a bookmarked
  list without saying so.
- **D11. The first property filter widens the level to *All levels*** (§ 1 item 4a, BR1-01),
  as the first search does. Most technical data sits on components (motors, gearboxes), which
  the default level hides. Rejected: keep the level and show a hint, one more line to read
  every time; keep the level silently, so "which motors are above 15 kW?" answers "No
  equipment matches these filters".
- **D12. An unreadable `props` still shows the filter line** (BR1-03), so the user can clear
  it. Rejected: drop it from the URL silently on load, which hides the fault. The list request
  is skipped then (BR2-03): it could only be refused.

## 8. Tests and acceptance

### 8.1 Core (`backend/tests/test_property_filter_core.py`)

- `read_property_filter`: checks 1–3 with field and message (not JSON, `match` wrong, 11 rules,
  a long `props`, a bad `property_id`, a boolean `property_id`); `property_ids` is the sorted
  set (two rules on one property give one id).
- `check_property_filter`: checks 4–6 with field and message (an unknown and an inactive
  property, an operator of another type, each value refusal, `between` low above high, an
  option of another property, a boolean or duplicate option id, blank text).
- `between` with equal ends passes; an inactive option passes; `has` with a value sent passes
  and ignores it; an empty `rules` list gives no condition.
- `filter_condition`: for each operator, the SQL text and the parameters (numbers as
  `Decimal`, yes/no as 1/0); `all` joins with AND, `any` with OR; an every-class property has no
  `class_properties` subquery; a Location property (after S061) has `e.level = 'equipment'`.
- No request text appears in the SQL: a text value `x' OR 1=1 --` is only in the parameters.
- For a filter with every operator, the count of `%s` in the SQL equals the count of
  parameters, so a misordered rule fails here, not in the database (BR1-13).

### 8.2 API (`backend/tests/test_property_filter_api.py`)

Fixtures: the `make_*` fixtures of `conftest.py`, with `make_property`, `link` and
`every_class` moved there (an every-class property is turned off after its test, BS1-02)
(§ 3 Tests, BR1-06).

- A number property on a model, 7.5 and 15: `gt 10` lists the 15 machine only; `between 5 10`
  the 7.5 one.
- An item's own value wins: the model says 7.5, the item says 15; `gt 10` lists the item.
- A choice: `in [Portable, Mobile]`; `not_in [Fixed]` leaves out a machine with no value.
- `none` lists a machine of a linked class with no value, and not a machine of an unlinked
  class.
- A hidden own value (class changed, S044) does not match.
- A component-unit without a model, with its own value, matches at `level=all`.
- `all` and `any` with two rules.
- The property filter with a class filter and the search: AND.
- Text `contains` with `%` and `_` in the value matches literally.
- A user of one unit gets only that unit's matches.
- A user with no units and a bad filter: 400, not an empty page.
- The asset list: `props` chooses machines; with `with_parts=1` a matching machine's parts
  come too, whatever their values; a bad filter is 400.
- After S061: an every-class property matches a machine of a class without links; a Location
  `has` matches top-level machines only.

### 8.3 Frontend unit (`frontend/tests/propertyFilter.test.js`, `frontend/tests/assetList.test.js`)

- encode and decode round trip; a broken `props` decodes to null.
- The operators per data type.
- `describeFilter`: one condition "Properties: Rated power more than 7.5 kW"; two under *All*
  "Properties (all of): Rated power more than 7.5 kW · Mobility is Portable or Mobile"; under
  *Any* "Properties (any of): …"; `between`, `has`, `none`; an unknown property reads "#12";
  a null (unreadable) filter "Properties: cannot be read".
- The level rule (§ 1 item 4a), as a pure helper: the first property filter at the default
  level (no `level` in the URL) adds `level=all`; a change to an existing one, or any `level`
  in the URL, does not (BR2-02).
- `assetListPath` and `parseAssetListQuery` carry `props`; `filtersLabel` uses the same words
  as `describeFilter`.

### 8.4 Automated (e2e, targeted: `frontend/e2e/equipment.spec.js`, `frontend/e2e/asset-list.spec.js`, `frontend/e2e/screens.spec.js`)

Each test starts with "S062:". A test's choice property is never named "Mobility"
(`properties_core.MOBILITY` exists; names are unique without regard to case; BS1-06). An
every-class property made by a test has its flag turned off in a `finally` (BS1-02); the
Location `has` test may use the seeded "GPS location". Set-up by API with `propertySetup`
(`frontend/e2e/support/properties.js`). Untagged unless said.

- **important** An engineer opens *Filter by property* on the default list (level
  *Equipment*), chooses a number property linked to a component class, *more than*, types a
  value, applies. The level turns to *All levels* and the matching motor shows; the filter
  line reads the condition; the URL has `props` and `level=all`; *Clear property filter*
  brings the full list back (BR1-01). Set-up (BR2-04): `propertySetup` makes the machine and
  the number property (linked to the machine's class, no model value); `noModelPart` makes the
  "motor" under that machine, of the same class; a `PUT /api/equipment/<id>/properties` gives
  the motor alone its own value. So only the part matches, and the machine does not.
- A hand-broken `props` in the URL: the filter line reads "Properties: cannot be read", the
  message "The property filter cannot be read. Clear it and make it again." shows once, with
  no *Retry* box, and *Clear property filter* brings the list back (BR1-03, BR2-03).
- **important** Two lines with *Any condition*: both machines show; with *All conditions*:
  none.
- A value "7,5" is refused under its line with "Enter a number", and the dialog stays open.
- A choice line *is not*: the note "Machines with no value are not included." shows.
- Reload keeps the filter; Back after *Clear property filter* brings it back.
- *Print asset list* with a property filter: the print page lists only the matching machine,
  and its header reads "Properties: …". (`asset-list.spec.js`)
- `@device`: the dialog with three lines fits the phone, and its buttons are in view
  (`expectDialogFits`).

### 8.5 On a real device

None. Every check here is a screen a browser engine judges.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs green; the whole-suite run once at the end.
- S061 is coded and committed (or snapshotted) before this step's coder starts.

## 9. Open questions and assumptions

- **A1 (assumption).** "not equal to" and "is not" leave out nodes with no value (D4).
- **A2 (assumption).** A node matches only where its class shows the property (D3).
- **A3 (assumption).** The dialog's operators are words ("more than", "at least"), not
  symbols, for readers who do not use symbols every day; the filter line uses the same words.
- **A4 (assumption).** The 10-line cap is enough. Each line adds three primary-key lookups per
  row.
- **Q1. The dialog's check request** (D6). (a) **Recommended:** one `GET` of the list route
  with `per_page=1` before the dialog closes, so the refusal shows under its line. (b) Close at
  once and show a refusal in the list's error box; simpler, but the user must find the line.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 27-10-2026

| Finding | Answer |
|---|---|
| BR1-01 major — the default level hides the motors | Accepted, option (a): the first property filter at the default level sets `level=all`, the search's rule (§ 1 item 4a, § 5.3 Apply, D11; tests § 8.3, § 8.4). Shown at gate A as a decision. |
| BR1-02 minor — the core's call contract | Accepted, option (a): `read_property_filter` (checks 1–3, `property_ids`) and `check_property_filter` (checks 4–6) (§ 3, § 5.2, § 8.1). |
| BR1-03 minor — an unreadable `props` cannot be cleared | Accepted, option (a): the filter line shows whenever `props` is in the URL, "Properties: cannot be read" (§ 1 item 3, D12; tests § 8.3, § 8.4). |
| BR1-04 minor — "or" in a choice line and between lines | Accepted, option (a): the match said once, conditions joined by " · " (§ 1 item 3, § 8.3). |
| BR1-05 minor — inputs repeat `PropertyInput.vue` | Accepted, option (a): the departure and the shared attributes stated in § 5.3. |
| BR1-06 minor — test fixtures not shared | Accepted, option (a): `make_property` and `link` move to `conftest.py`; `test_properties_api.py` keeps its own, which override by name (§ 3 Tests, § 8.2). |
| BR1-07…BR1-13 nits | All accepted: § 1 item 2 (BR1-07, BR1-08), § 5.3 Apply (BR1-09), § 5.2 checks 3 and 6 (BR1-10: a duplicate option id is refused, not dropped), § 5.4 (BR1-11), § 3 Frontend (BR1-12), § 8.1 (BR1-13). |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 27-10-2026

| Finding | Answer |
|---|---|
| BR2-01 minor — a second name counter in `conftest.py` | Accepted: `Uniq.property_name(prefix)` on the existing `Uniq`; the moved fixture is `make_property(admin, uniq)` (§ 3 Tests). |
| BR2-02…BR2-04 nits | All accepted: the level rule reads "no `level` in the URL" (§ 1 item 4a, § 8.3); an unreadable `props` skips the list request and shows one message (§ 1 item 3, D12, § 8.4); the e2e set-up named: `propertySetup`, `noModelPart`, the part's own value (§ 8.4). |

### Staleness check s1 — `2-brief-review-s1.md` (Fable), answered 27-10-2026

Against S061 as coded (`refs/steps/S061` fb6a025). No blocker or major, so the approval stands.

| Finding | Answer |
|---|---|
| BS1-01 minor — Location column is `GEO_COLUMNS`, not in `VALUE_COLUMNS` | Accepted: § 5.4 names both; the core builds its own column table. |
| BS1-02 minor — an every-class test property leaks | Accepted: `every_class` moves to `conftest.py`; tests turn the flag off; § 3 Tests, § 8.2, § 8.4. |
| BS1-03…BS1-06 nits | All accepted: line numbers updated (§ 3 Tests); the moved fixture keeps S061's body; the dialog intersects the class list with the active list (§ 5.3); the cross-comment names `linked_properties`, `on_level` and `lock_value_properties`, the core uses `GEO_LEVEL`, and no test property is named "Mobility" (§ 5.4, § 8.4). |

### Approval — gate A, 27-10-2026

KLA approved the brief with every recommended option: D11 (the first property filter widens
the level to *All levels*), Q1 (a) (one check request before the dialog closes), and A1–A4 as
written.
