```
Step: S062 — Filter the equipment list by property
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 27-10-2026
```

Reviewed against: d6431f1 + uncommitted S061 (the working tree equals `refs/steps/S061`, fb6a025)

**Verdict: no blocker or major finding. The brief's design holds against S061 as coded.** Two
minor findings (a constant the brief names wrongly, and a test clean-up S061 made necessary) and
four nits. The coder can start once the brief text is fixed.

Staleness mode: I read the diff `d6431f1..refs/steps/S061` of the files the orchestrator named,
and the code S062 names explicitly (`linked_properties`, `on_level`, `lock_value_properties`,
`_class_properties`, `list_properties`, `VALUE_COLUMNS`, `GEO_COLUMNS`, `parse_value`,
`parse_property_ids`, `like_pattern`, `_list_filters`, `Uniq`, the `make_property` / `link`
fixtures, `propertySetup` / `noModelPart`, the line numbers). I did not re-review the rest of
the brief.

## Findings

### BS1-01 — minor — `VALUE_COLUMNS` has no Location column

**Problem.** § 5.4 says: "`col` the value column of its data type (`properties_core.VALUE_COLUMNS`;
for Location after S061, `value_lat`)". As built, `VALUE_COLUMNS` holds number, text, yes_no and
choice only (`properties_core.py:94`). The Location columns are a separate constant,
`GEO_COLUMNS = ("value_lat", "value_lng")` (line 96); `ALL_VALUE_COLUMNS` joins the two.
`VALUE_COLUMNS[GEO]` raises `KeyError`.

**Why it matters.** The brief names the wrong table for the one type whose column it must
special-case. A coder who follows the text builds the column lookup from `VALUE_COLUMNS` and
finds the gap only in the Location test.

**Options.**
- (a) **Recommended.** § 5.4 reads: "`col` from `properties_core.VALUE_COLUMNS`, and for Location
  `properties_core.GEO_COLUMNS[0]` (`value_lat`); the core builds its own column table from the
  two". § 8.1's Location case then checks `value_lat` in the SQL.
- (b) Add `GEO` to `VALUE_COLUMNS` in `properties_core`. Rejected: S061's `check_values`,
  `_stored_raw` and `_DECIMAL_COLUMNS` treat the Location pair apart from the one-column types on
  purpose; a change there widens this step into S061's code.

### BS1-02 — minor — a test that makes an every-class property must turn the flag off

**Problem.** § 8.2 plans "an every-class property matches a machine of a class without links",
and § 8.4 may need one. S061 found that such a property shows on every later test's machine in
the worker's shared database, and on every machine of a lane in the browser tests (S061 impl
report D-10). Its tests turn the flag off in a fixture teardown: `every_class` in
`test_item_properties_api.py:355` and `test_properties_api.py:424`, and a `finally` in the e2e
tests. The brief's § 3 Tests and § 8.2 do not say so, and `every_class` is now a second fixture
pair that lives in two modules (the BR1-06 class).

**Why it matters.** A leaked flag changes other tests' cards and `none` matches in the same run,
a failure that comes and goes with test order.

**Options.**
- (a) **Recommended.** Move `every_class` to `conftest.py` with `make_property` and `link` (§ 3
  Tests), and let `test_item_properties_api.py` use the shared one (`test_properties_api.py`
  keeps its own by `engineer`, as the brief says for the other two). § 8.2 says the every-class
  test uses `every_class`. § 8.4: an e2e test that sets `all_classes` turns it off in a `finally`.
- (b) Use the seeded "GPS location" (v34: `geo`, `all_classes = 1`, `per_item_only = 1`) for
  both the every-class and the Location cases, and make no every-class property. Simpler, but
  the number and choice cases of an every-class property then go untested; take it only in
  addition to (a) for the Location `has` test.

## Nits

- **BS1-03** (nit) § 3 Tests: line numbers moved in S061. `class Uniq` is at `conftest.py:284`;
  `make_property` is at `test_item_properties_api.py:65-74`, `link` at `77-81`, `_numbers` at
  line 18. `EquipmentView.vue:68` and `:142` still hold.
- **BS1-04** (nit) § 3 Tests: the `make_property` to move now takes `**overrides` (`data_type`,
  `options`, `all_classes`, `per_item_only`) and drops `unit` for a non-number; it is used 19
  times in its module. Say the move keeps that body, with `uniq.property_name(prefix)` for the
  name only.
- **BS1-05** (nit) § 5.3 Property select: `GET /api/masters/equipment-classes/<id>/properties`
  now returns the inactive properties too (`_class_properties`, "inactive ones included"), each
  with `all_classes`. Say the dialog keeps only the ids that are also in the active list from
  `ensureProperties`.
- **BS1-06** (nit) § 5.4 BR1-11 comment and § 8.1: the "applies" rule is now in two S061 places,
  not one: `properties.linked_properties` (active, linked or `all_classes`) and
  `properties_core.on_level` (a `geo` property only at `GEO_LEVEL`); `lock_value_properties`
  repeats it for saves. The cross-comment names `linked_properties` and `on_level`, and the core
  uses `GEO_LEVEL`, not the literal `'equipment'`. Also: `properties_core.MOBILITY = "Mobility"`
  is the hint's property name and `uq_property_definitions_name` compares without case, so a
  test's choice property is not named "Mobility" (S061's hint test renames its own afterwards);
  the brief's examples may keep the word.

## Checked and found consistent

- `linked_properties(cur, class_id, level)` exists (`properties.py:285`): active AND
  (`all_classes = 1` OR a `class_properties` row), then `on_level` drops `geo` unless `level ==
  GEO_LEVEL` (`"equipment"`). The brief's *applies* SQL (§ 5.4) states the same rule.
- `_class_properties` (`properties.py:219`) returns the linked and every-class rows together
  with `all_classes`, as § 5.3 says; it carries no options.
- `list_properties` takes `include_inactive=1` and returns each row with its options and the
  S061 flags (`p.*`); `ensureProperties` (`stores/masters.js:84`) calls it so.
- `parse_value(data_type, raw, options=(), stored_option_id=None)` and the messages
  `ENTER_NUMBER`, `TOO_MANY_DECIMALS`, `NUMBER_TOO_BIG`, `ENTER_TEXT`, `TEXT_TOO_LONG`,
  `CHOOSE_YES_NO`, `CHOOSE_OPTION` read as § 5.2 quotes them. `parse_property_ids` keeps the
  boolean guard (`properties_core.py:433`).
- v34 adds `value_lat` / `value_lng` to both value tables; `chk_*_property_one_value` counts
  `value_lat` as the fifth slot and `chk_*_property_geo_pair` ties `value_lng` to it. So § 5.4's
  "own row's column is filled whenever the own row exists" holds with `value_lat` as the
  Location column, and `COALESCE` on it gives "own row wins". A `per_item_only` property has no
  model row, so the model subquery is NULL: no rule change.
- `_list_filters()` (`equipment.py:521`) is still called before the cursor block in
  `list_equipment` (550 / 567) and `asset_list` (723 / 728); the brief's `_list_filters(cur)`
  change is as planned. `like_pattern` (`api_common.py:157`) escapes `\`, `%` and `_`.
- `propertySetup(tag, {properties, link, values})` and `noModelPart(parent, cls, name)` exist in
  `frontend/e2e/support/properties.js` with the behaviour § 8.4 relies on (link on by default,
  no model value unless `values`).
- `assetList.js` has `FILTER_KEYS`, `assetListPath`, `parseAssetListQuery`, `filtersLabel`;
  `frontend/e2e/asset-list.spec.js` and `frontend/tests/assetList.test.js` exist.
- The S061 impl report records no departure from S061's brief, so the S062 reviews' reading of
  S061's rules stands.

## Feedback

- waste: the two `git diff` calls returned 36 KB each and were saved to files I did not read; grepping the current code for the names the brief cites answered every question faster (2 calls, about 70 KB of output unused).
- idea: the staleness prompt could carry the list of names to check as a facts file (`tooling/step-brief-facts.bat S062` against the working tree), so the line numbers and signatures come in one run instead of six greps.
