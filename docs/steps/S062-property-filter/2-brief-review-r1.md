```
Step: S062 — Filter the equipment list by property
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 27-10-2026
```

Reviewed against: d6431f1 (no uncommitted code; S061 is approved and not coded, so its rules were read from `docs/steps/S061-global-properties-gps/1-brief.md`)

**Verdict: one `major` finding is open (BR1-01: the filter at the default level never finds a motor).** No blocker. The SQL of § 5.4 is sound: "own value wins" through COALESCE holds, the NULL rules are stated right, and no request text reaches the SQL. Five `minor` findings and seven nits. Facts file used: `scratch/brief-facts-S062.md`.

## Findings

### BR1-01 — major — The brief's first example, "which motors are above 15 kW?", gives "No equipment matches these filters" on the default screen

**Problem.** The list opens at level *Equipment* (`DEFAULT_LEVEL`, `EquipmentView.vue:29`). A motor is a component (Plan.MD § 4.1: component = motor, gearbox). A user who applies "Rated power more than 15" on the default screen sees no motor and reads "No equipment matches these filters." The brief says nothing about the level. The search already solves this for codes: `applySearch` widens the level to *All levels* on the first search ("A motor is found by its code, so the first search widens the level; the user can narrow it again", `EquipmentView.vue:141`).

**Why it matters.** The person on the floor does not know that *Level* hides the motors. The answer looks like "no such motor", which is wrong. It is the flow the brief was asked for, and it fails silently.

**Options.**
- (a) **Recommended:** the search's rule. When *Apply filter* sets a property filter and the level is the default, the URL change also sets `level=all`. The user can narrow it again. State it in § 1.5 and § 5.3, and add the case to § 8.4 (the first automated check: the motor of the test's machine shows).
- (b) Keep the level. Show a hint under the filter line when the level is *Equipment*: "Parts are not shown. Choose All levels to include them." One more thing to read, every time.
- (c) Keep the level, say nothing. The headline use case then needs a second step the user must guess.

### BR1-02 — minor — The core's call contract is missing a step: the shell cannot load the properties before it knows their ids

**Problem.** § 5.2 gives `parse_property_filter(raw, properties, options)`: the core gets the raw text and the property rows. § 3 says `_list_filters` "reads `props`, loads the named properties and their options, calls the core". To load the named properties the shell must first read the ids out of the raw JSON. So either the shell parses the JSON itself (checks 1–3 twice, once in each layer) or the core is called twice. The brief does not say which.

**Why it matters.** The coder decides the layering alone, and the likely result is a JSON parse in `equipment.py` beside the one in the core.

**Options.**
- (a) **Recommended:** two pure functions. `read_property_filter(raw)` → `(parsed, None)` or `(None, (field, message))`: checks 1–3, and `parsed["property_ids"]` as a sorted set. Then `check_property_filter(parsed, properties, options)` → `(filter, None)` or the refusal: checks 4–6. The shell calls the first, loads by the ids, calls the second. Both are tested in § 8.1.
- (b) One core function that takes a loader callback. Not pure; rejected.

### BR1-03 — minor — A bookmarked `props` that cannot be read leaves the user with an error and no way to clear it

**Problem.** § 8.3: "a broken `props` decodes to null". § 1.3: the filter line and *Clear property filter* show "while a property filter is set", which reads as "decoded to a filter". So a hand-edited or truncated bookmark gives: the list's error box "The property filter cannot be read. Clear it and make it again." with a *Retry* button (`EquipmentView.vue:303`), no filter line and no *Clear property filter*. Retry gives the same 400. The user must edit the URL.

**Why it matters.** The message tells the user to clear a filter the screen gives no button for.

**Options.**
- (a) **Recommended:** the filter line shows whenever `props` is in the URL. With a null decode its text reads "Properties: cannot be read" and *Clear property filter* removes the key. A tap on the text opens an empty dialog. State it in § 1.3 and add the case to § 8.4 or § 8.3.
- (b) The list drops an unreadable `props` from the URL on load, silently. Hides the fault; rejected.

### BR1-04 — minor — "or" inside a choice line clashes with "or" between lines under *Any condition* (scope B)

**Problem.** § 1.3 and § 8.3 give "Mobility is Portable or Mobile" for a choice line and "or" as the join under *Any*. Two lines under *Any* then read "Rated power more than 7.5 kW or Mobility is Portable or Mobile". The reader cannot tell the line break from the option list. With ten lines the sentence is unreadable on a phone and on the printed header.

**Options.**
- (a) **Recommended:** say the match once and separate the lines with " · ", the asset list's own separator: "Properties (all of): Rated power more than 7.5 kW · Mobility is Portable or Mobile"; "(any of)" for *Any*. One line reads "Properties: Rated power more than 7.5 kW" (no match word). `describeFilter` and `filtersLabel` use the same text.
- (b) Keep the sentence, list options with commas: "Mobility is Portable, Mobile". The ambiguity moves, it does not go.

### BR1-05 — minor — The value inputs of § 5.3 repeat `PropertyInput.vue` without saying so

**Problem.** `frontend/src/components/PropertyInput.vue` already renders the number input with `inputmode="decimal"` and the unit beside it, the text input with `maxlength="100"`, and a yes/no choice. § 5.3 plans the same inputs again in `PropertyFilterModal.vue` and does not name `PropertyInput`. The filter does need more: two inputs for `between`, tick boxes for a choice (several options), and no label. So full reuse does not fit.

**Options.**
- (a) **Recommended:** state the departure in § 5.3 or D-list: the dialog has its own inputs because a line has no label, `between` has two inputs and a choice is a multi-pick; keep the same attributes (`inputmode="decimal"`, the unit as `input-group-text`, `maxlength="100"`) so the two look the same.
- (b) Reuse `PropertyInput` for number and text with a prop that hides the label and the margin. More coupling for two inputs.

### BR1-06 — minor — The test set-up the brief leans on is not shared

**Problem.** § 8.2: "the property set-up used by `test_item_properties_api.py`". `make_property` and `link` are fixtures local to that module (`backend/tests/test_item_properties_api.py:58-74`), with their own name counter. A fixture in another test module is not reachable from `test_property_filter_api.py`. The coder will copy them.

**Options.**
- (a) **Recommended:** move `make_property` and `link` (and the counter) to `conftest.py`, beside the other `make_*` fixtures; `test_item_properties_api.py` keeps working. Name it in § 3 Tests; `conftest.py` is shared code (settings: *Shared code*).
- (b) Copy them. A duplicate in the tests.

## Nits

- **BR1-07** (nit) § 1.2: a disabled *Add condition* with a tooltip reason is not readable on a phone (no hover). Hide the button at ten lines, or show "10 conditions at most" as text under it, as the Apply reason is shown.
- **BR1-08** (nit) § 1.2 / § 5.3: say where the *Match* radios sit (above the lines, so the reader meets "All / Any" before the conditions, or under them).
- **BR1-09** (nit) § 5.3 Apply: while the check request runs, pass `saving` to `FormModal`, so *Apply filter* shows the spinner and a second tap does nothing.
- **BR1-10** (nit) § 5.2 checks 3 and 6: say that a boolean is refused where a whole number is expected (`True` is an `int` in Python; `parse_property_ids` guards it), and that a duplicate option id is refused with `CHOOSE_OPTION` or dropped.
- **BR1-11** (nit) § 5.4 *applies*: the rule "which properties a node shows" then lives twice, in S061's `properties.linked_properties` and in the filter SQL. Ask the coder for a cross-reference comment in both, naming the other.
- **BR1-12** (nit) § 3 `AssetListPrintView.vue`: load `ensureProperties` only when the query has `props`; a plain print needs no fourth request.
- **BR1-13** (nit) § 8.1: add one test that, for a filter with every operator, the count of `%s` in the SQL equals the count of parameters; a misordered rule then fails in the core, not in the database.

## Checked and found consistent

- **§ 5.4 "own value wins".** A value row holds exactly one non-NULL value column (`chk_*_one_value`, `local_db.py:916`, `:1027`), and the data type is fixed once any value exists in either table (`properties.py:151-158`, `DATA_TYPE_FIXED`). So an own row always fills the column of the property's type, and `COALESCE(own, model)` reads the own row whenever it exists. A node without a model (`e.model_id` NULL) gets NULL from the model subquery. After S061 `value_lat` joins the one-value CHECK, so `has` / `none` on a Location hold too.
- **§ 5.4 NULL rules.** `<>`, `NOT IN`, `<`, `>`, `BETWEEN` on a NULL value give NULL, so the row drops: D4 states it. Option ids are never NULL, so `NOT IN (…)` has no NULL in its list. *applies* AND `IS NULL` makes *has no value* the data-gap list (D3).
- **§ 5.4 injection.** Column names from `VALUE_COLUMNS` and the operator table; `IN (%s, …)` sized from the list; the `like` pattern is `api_common.like_pattern` (escapes `\`, `%`, `_`, as the search does, `equipment.py:559`). The `e.level = 'equipment'` literal is from the fixed table.
- **§ 5.4 collation.** The tables are `DEFAULT CHARSET=utf8mb4` with the database's collation; dev and test use `utf8mb4_unicode_ci` (`conftest.py:53`), and `uq_property_definitions_name` relies on the same. Text `eq` is case-insensitive there. Assumption: production's database collation is a `_ci` one too (it is, for every utf8mb4 default).
- **§ 5.5 order.** Today `_list_filters()` runs before the cursor, and its 400s (`int_arg`, `enum_arg`) come before the unit check. Moving it inside the cursor block keeps that order; a user with no units still gets 400 on a bad filter and an empty page on a good one.
- **Existing tests.** `_list_filters` is called only in `equipment.py` (facts file). `test_asset_list_api.py::test_a_bad_filter_is_400_with_its_field` and `test_a_user_with_no_units_gets_an_empty_result` still hold. `frontend/tests/assetList.test.js` passes no `props`, so adding it to `FILTER_KEYS` breaks nothing. The `filterKey` watch clears the ticks on a `props` change; `hasFilters` gives "No equipment matches these filters."
- **§ 5.3 sources.** `ensureProperties` fetches `/api/masters/properties?include_inactive=1` with options (`stores/masters.js:30-31`, `properties.py:99-107`). `GET /api/masters/equipment-classes/<id>/properties` carries no options (`_class_properties`, `properties.py:211`); after S061 it lists the every-class rows (S061 § 5.3, BR1-08 there).
- **§ 5.6 permissions.** `equipment:read` on both routes; `masters:read` is `("*",)` (`config_rbac.py:133`). No new key; `test_role_matrix` unchanged.
- **§ 5.3 dialog.** `FormModal` has `error`, `dirty`, `saveDisabledReason` and `saveLabel` (`FormModal.vue:23-35`); the body scrolls and the footer stays (`modal-dialog-scrollable`). `apiGet` carries `field` and `status` on the error (`api.js:24-26`), so the dialog can map `props.rules.<i>.…` to a line.
- **D9, S015 § 4.** "Filters choose machines; parts come only with their machine" is S015's rule as written (`S015-asset-list/1-brief.md:252`); `asset_list` already appends `e.level = 'equipment'`.
- **Standards.** ISO 14224 Annex A (equipment-specific data: the fields to record per class), ISO 55001 § 7.5 (information requirements), TPM focused improvement, and ISO 27001 A.8.28 (secure coding, the 2022 numbering) are named and explained in plain words; the unverified clause numbers are marked so. No ISO 9001 clause applies to a read-only filter.
- **Track and checks.** Full track is right (a new core that builds SQL from user input). § 8.5 is empty with a reason; every check in § 8.4 is one a browser can judge, and the `@device` tag is on the one layout check only.
- **Facts file.** Every "not found" name is one the brief says is new, or one S061 adds (`all_classes`, `value_lat`).

## Feedback

- idea: the facts file lists `PropertyFilterModal.open` and `_` as code names with 64 and 26 code files each (`scratch/brief-facts-S062.md:126-136`); a backticked `X.open` or a lone `_` should be skipped, the noise cost a minute of reading.
- waste: `docs/steps/S044-item-properties/1-brief.md` does not exist under that slug; I looked up S044 § 5.5 by its rule in `properties_core.property_view` instead (one failed Grep).
